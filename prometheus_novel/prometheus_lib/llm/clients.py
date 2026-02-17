"""
LLM Client Wrappers - OpenAI, Gemini, and Local Model Support

Provides async wrappers for various LLM providers with:
- Retry logic with exponential backoff
- Token counting and cost estimation
- Streaming support
- Error handling and fallbacks
- Rate limiting protection
- Timeout enforcement
"""

import os
import asyncio
import logging
import random
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, AsyncIterator, Callable
from dataclasses import dataclass, field
from functools import wraps

logger = logging.getLogger(__name__)


# ============================================================================
# ACCURATE TOKEN COUNTING
# ============================================================================
_tiktoken_encoders = {}


def count_tokens(text: str, model_name: str = "gpt-4o-mini") -> int:
    """Count tokens accurately using tiktoken for OpenAI models, with fallbacks.

    Uses tiktoken (BPE tokenizer) for OpenAI models which gives exact counts.
    For non-OpenAI models, uses a calibrated heuristic (3.3 chars/token for
    English prose, which is more accurate than the naive 4 chars/token).
    """
    if not text:
        return 0

    model_lower = model_name.lower()

    # Try tiktoken for OpenAI models
    if any(prefix in model_lower for prefix in ("gpt", "o1", "o3", "openai")):
        try:
            import tiktoken

            # Cache encoders to avoid repeated initialization
            encoding_name = "cl100k_base"  # Works for gpt-4o, gpt-4, gpt-3.5
            if encoding_name not in _tiktoken_encoders:
                _tiktoken_encoders[encoding_name] = tiktoken.get_encoding(encoding_name)

            return len(_tiktoken_encoders[encoding_name].encode(text))
        except ImportError:
            pass  # Fall through to heuristic
        except Exception as e:
            logger.debug(f"tiktoken encoding failed: {e}")

    # Calibrated heuristic for non-OpenAI models
    # English prose averages ~3.3 chars per token across most BPE tokenizers
    # This is significantly more accurate than the naive 4 chars/token estimate
    return max(1, int(len(text) / 3.3))


# ============================================================================
# RETRY AND TIMEOUT CONFIGURATION
# ============================================================================
DEFAULT_TIMEOUT_SECONDS = 120  # 2 minutes per request
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1.0  # seconds
MAX_RETRY_DELAY = 30.0  # seconds
RETRY_MULTIPLIER = 2.0

# Rate limiting: simple token bucket
REQUESTS_PER_MINUTE = 50
_request_timestamps: Dict[str, List[float]] = {}


async def rate_limit_check(provider: str):
    """Simple rate limiting - wait if too many recent requests."""
    import time
    now = time.time()
    window = 60  # 1 minute window

    if provider not in _request_timestamps:
        _request_timestamps[provider] = []

    # Clean old timestamps
    _request_timestamps[provider] = [
        ts for ts in _request_timestamps[provider] if now - ts < window
    ]

    # Check if we need to wait
    if len(_request_timestamps[provider]) >= REQUESTS_PER_MINUTE:
        oldest = _request_timestamps[provider][0]
        wait_time = window - (now - oldest) + 0.1
        if wait_time > 0:
            logger.warning(f"Rate limit: waiting {wait_time:.1f}s for {provider}")
            await asyncio.sleep(wait_time)

    _request_timestamps[provider].append(now)


class LLMError(Exception):
    """Base exception for LLM errors."""
    pass


class RateLimitError(LLMError):
    """Rate limit exceeded."""
    pass


class TimeoutError(LLMError):
    """Request timed out."""
    pass


class AuthenticationError(LLMError):
    """Invalid API key."""
    pass


def with_retry(func: Callable):
    """Decorator to add retry logic with exponential backoff."""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        last_error = None
        delay = INITIAL_RETRY_DELAY

        for attempt in range(MAX_RETRIES + 1):
            try:
                # Apply rate limiting
                provider = self.__class__.__name__.replace("Client", "").lower()
                await rate_limit_check(provider)

                # Apply timeout
                timeout = kwargs.pop('timeout', DEFAULT_TIMEOUT_SECONDS)
                result = await asyncio.wait_for(
                    func(self, *args, **kwargs),
                    timeout=timeout
                )
                return result

            except asyncio.TimeoutError:
                last_error = TimeoutError(f"Request timed out after {timeout}s")
                logger.warning(f"Timeout on attempt {attempt + 1}/{MAX_RETRIES + 1}")

            except Exception as e:
                error_str = str(e).lower()
                last_error = e

                # Don't retry auth errors
                if "401" in error_str or "unauthorized" in error_str or "invalid api key" in error_str:
                    raise AuthenticationError(f"Authentication failed: {e}")

                # Rate limit - longer backoff
                if "429" in error_str or "rate limit" in error_str:
                    delay = min(delay * 3, MAX_RETRY_DELAY)
                    logger.warning(f"Rate limited, waiting {delay}s")

                # Server error - standard backoff
                elif "500" in error_str or "502" in error_str or "503" in error_str:
                    logger.warning(f"Server error on attempt {attempt + 1}")

                else:
                    # Unknown error - log and retry
                    logger.warning(f"Error on attempt {attempt + 1}: {e}")

            if attempt < MAX_RETRIES:
                # Add jitter to prevent thundering herd
                jitter = random.uniform(0, delay * 0.1)
                await asyncio.sleep(delay + jitter)
                delay = min(delay * RETRY_MULTIPLIER, MAX_RETRY_DELAY)

        # All retries exhausted
        raise last_error or LLMError("Max retries exceeded")

    return wrapper


@dataclass
class LLMResponse:
    """Standardized LLM response."""
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    finish_reason: str = "stop"
    raw_response: Any = None


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._initialized = False

    def _normalize_generate_kwargs(self, **kwargs) -> dict:
        """Normalize kwargs - map max_output_tokens to max_tokens."""
        if "max_output_tokens" in kwargs and "max_tokens" not in kwargs:
            kwargs["max_tokens"] = kwargs.pop("max_output_tokens")
        return kwargs

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Generate text from the LLM."""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream text generation from the LLM."""
        pass

    def estimate_tokens(self, text: str) -> int:
        """Accurate token estimation using tiktoken when available, with fallback."""
        return count_tokens(text, self.model_name)


class OpenAIClient(BaseLLMClient):
    """OpenAI API client wrapper."""

    def __init__(self, model_name: str = "gpt-4o-mini"):
        super().__init__(model_name)
        self.client = None
        self.api_key = os.getenv("OPENAI_API_KEY")

    async def _ensure_initialized(self):
        """Lazy initialization of the OpenAI client."""
        if self._initialized:
            return

        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set. Using mock responses.")
            self._initialized = True
            return

        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=self.api_key)
            self._initialized = True
            logger.info(f"OpenAI client initialized for model: {self.model_name}")
        except ImportError:
            logger.warning("openai package not installed. Using mock responses.")
            self._initialized = True

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Generate text using OpenAI API with retry logic."""
        await self._ensure_initialized()

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        if not self.client:
            # Mock response when API not available
            logger.debug("Using mock OpenAI response")
            return LLMResponse(
                content=f"[Mock response for: {prompt[:100]}...]",
                model=self.model_name,
                input_tokens=self.estimate_tokens(prompt),
                output_tokens=100,
                finish_reason="stop"
            )

        # Apply rate limiting
        await rate_limit_check("openai")

        # Retry loop with exponential backoff
        last_error = None
        delay = INITIAL_RETRY_DELAY
        timeout = kwargs.pop('timeout', DEFAULT_TIMEOUT_SECONDS)

        # Handle json_mode parameter
        json_mode = kwargs.pop('json_mode', False)
        if json_mode:
            kwargs['response_format'] = {"type": "json_object"}

        # Handle stop sequences explicitly
        stop = kwargs.pop('stop', None)

        for attempt in range(MAX_RETRIES + 1):
            try:
                create_kwargs = {
                    "model": self.model_name,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    **kwargs
                }
                if stop:
                    create_kwargs["stop"] = stop

                response = await asyncio.wait_for(
                    self.client.chat.completions.create(**create_kwargs),
                    timeout=timeout
                )

                if not response.choices:
                    raise LLMError("OpenAI returned empty choices array")
                return LLMResponse(
                    content=response.choices[0].message.content or "",
                    model=response.model,
                    input_tokens=getattr(response.usage, "prompt_tokens", 0),
                    output_tokens=getattr(response.usage, "completion_tokens", 0),
                    finish_reason=response.choices[0].finish_reason,
                    raw_response=response
                )

            except asyncio.TimeoutError:
                last_error = TimeoutError(f"OpenAI request timed out after {timeout}s")
                logger.warning(f"Timeout on attempt {attempt + 1}/{MAX_RETRIES + 1}")

            except Exception as e:
                error_str = str(e).lower()
                last_error = e

                # Don't retry auth errors
                if "401" in error_str or "invalid api key" in error_str:
                    raise AuthenticationError(f"OpenAI authentication failed: {e}")

                # Rate limit - longer backoff
                if "429" in error_str or "rate limit" in error_str:
                    delay = min(delay * 3, MAX_RETRY_DELAY)
                    logger.warning(f"Rate limited by OpenAI, waiting {delay}s")
                else:
                    logger.warning(f"OpenAI error on attempt {attempt + 1}: {e}")

            if attempt < MAX_RETRIES:
                jitter = random.uniform(0, delay * 0.1)
                await asyncio.sleep(delay + jitter)
                delay = min(delay * RETRY_MULTIPLIER, MAX_RETRY_DELAY)

        # All retries exhausted
        logger.error(f"OpenAI API failed after {MAX_RETRIES + 1} attempts: {last_error}")
        raise last_error or LLMError("OpenAI max retries exceeded")

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream text generation from OpenAI."""
        await self._ensure_initialized()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        if not self.client:
            # Mock streaming
            mock_text = f"[Mock streaming response for: {prompt[:50]}...]"
            for word in mock_text.split():
                yield word + " "
                await asyncio.sleep(0.05)
            return

        try:
            stream = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                **kwargs
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise


class GeminiClient(BaseLLMClient):
    """Google Gemini API client wrapper."""

    def __init__(self, model_name: str = "gemini-2.0-flash"):
        super().__init__(model_name)
        self.model = None
        self.api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

    async def _ensure_initialized(self):
        """Lazy initialization of the Gemini client."""
        if self._initialized:
            return

        if not self.api_key:
            logger.warning("GOOGLE_API_KEY not set. Using mock responses.")
            self._initialized = True
            return

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            self._initialized = True
            logger.info(f"Gemini client initialized for model: {self.model_name}")
        except ImportError:
            logger.warning("google-generativeai package not installed. Using mock responses.")
            self._initialized = True

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Generate text using Gemini API with retry logic."""
        await self._ensure_initialized()
        kwargs.pop('json_mode', None)
        stop = kwargs.pop('stop', None)

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        if not self.model:
            logger.debug("Using mock Gemini response")
            return LLMResponse(
                content=f"[Mock Gemini response for: {prompt[:100]}...]",
                model=self.model_name,
                input_tokens=self.estimate_tokens(prompt),
                output_tokens=100,
                finish_reason="stop"
            )

        # Retry loop with exponential backoff (matching OpenAI pattern)
        last_error = None
        delay = INITIAL_RETRY_DELAY
        timeout = kwargs.pop('timeout', DEFAULT_TIMEOUT_SECONDS)

        for attempt in range(MAX_RETRIES + 1):
            try:
                await rate_limit_check("gemini")

                gen_config = {
                    "max_output_tokens": max_tokens,
                    "temperature": temperature,
                }
                if stop:
                    gen_config["stop_sequences"] = stop

                # Gemini API is sync, so run in executor
                response = await asyncio.wait_for(
                    asyncio.get_running_loop().run_in_executor(
                        None,
                        lambda: self.model.generate_content(
                            full_prompt,
                            generation_config=gen_config
                        )
                    ),
                    timeout=timeout
                )

                # Validate response before accessing .text
                if not response.candidates:
                    raise LLMError(f"Gemini returned no candidates (safety filter or empty response)")

                content = response.text
                # Apply stop sequence clamp (post-generation safety net)
                if stop and content:
                    for s in stop:
                        idx = content.find(s)
                        if idx != -1:
                            content = content[:idx]

                return LLMResponse(
                    content=content,
                    model=self.model_name,
                    input_tokens=self.estimate_tokens(full_prompt),
                    output_tokens=self.estimate_tokens(content),
                    finish_reason="stop",
                    raw_response=response
                )

            except asyncio.TimeoutError:
                last_error = TimeoutError(f"Gemini request timed out after {timeout}s")
                logger.warning(f"Gemini timeout on attempt {attempt + 1}/{MAX_RETRIES + 1}")

            except Exception as e:
                error_str = str(e).lower()
                last_error = e

                if "401" in error_str or "invalid api key" in error_str:
                    raise AuthenticationError(f"Gemini authentication failed: {e}")

                if "429" in error_str or "rate limit" in error_str or "quota" in error_str:
                    delay = min(delay * 3, MAX_RETRY_DELAY)
                    logger.warning(f"Rate limited by Gemini, waiting {delay}s")
                else:
                    logger.warning(f"Gemini error on attempt {attempt + 1}: {e}")

            if attempt < MAX_RETRIES:
                jitter = random.uniform(0, delay * 0.1)
                await asyncio.sleep(delay + jitter)
                delay = min(delay * RETRY_MULTIPLIER, MAX_RETRY_DELAY)

        logger.error(f"Gemini API failed after {MAX_RETRIES + 1} attempts: {last_error}")
        raise last_error or LLMError("Gemini max retries exceeded")

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream text generation from Gemini."""
        await self._ensure_initialized()

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        if not self.model:
            # Mock streaming
            mock_text = f"[Mock Gemini streaming for: {prompt[:50]}...]"
            for word in mock_text.split():
                yield word + " "
                await asyncio.sleep(0.05)
            return

        try:
            response = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: self.model.generate_content(
                    full_prompt,
                    generation_config={
                        "max_output_tokens": max_tokens,
                        "temperature": temperature
                    },
                    stream=True
                )
            )

            for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Gemini streaming error: {e}")
            raise


class OllamaClient(BaseLLMClient):
    """Local Ollama client - free, no API keys, runs models on your machine."""

    def __init__(self, model_name: str = "qwen2.5:7b"):
        super().__init__(model_name)
        self.client = None
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")

    async def _ensure_initialized(self):
        """Lazy initialization of the Ollama client (OpenAI-compatible API)."""
        if self._initialized:
            return

        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(
                base_url=self.base_url,
                api_key="ollama"  # Required by SDK but not used by Ollama
            )
            self._initialized = True
            logger.info(f"Ollama client initialized for model: {self.model_name} at {self.base_url}")
        except ImportError:
            logger.warning("openai package not installed. Cannot use Ollama.")
            self._initialized = True

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Generate text using local Ollama."""
        await self._ensure_initialized()
        kwargs = self._normalize_generate_kwargs(**kwargs)
        max_tokens = kwargs.pop("max_tokens", max_tokens)
        temperature = kwargs.pop("temperature", temperature)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        if not self.client:
            logger.debug("Using mock Ollama response")
            return LLMResponse(
                content=f"[Ollama not available - ensure Ollama is running: ollama run {self.model_name}]",
                model=self.model_name,
                input_tokens=self.estimate_tokens(prompt),
                output_tokens=100,
                finish_reason="stop"
            )

        # Build create kwargs
        json_mode = kwargs.pop("json_mode", False)
        stop = kwargs.pop("stop", None)
        timeout_val = kwargs.pop("timeout", 300)

        create_kwargs = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if json_mode:
            create_kwargs["response_format"] = {"type": "json_object"}
        if stop:
            create_kwargs["stop"] = stop
        create_kwargs.update({k: v for k, v in kwargs.items()})

        # Retry loop with exponential backoff
        last_error = None
        delay = INITIAL_RETRY_DELAY

        for attempt in range(MAX_RETRIES + 1):
            try:
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(**create_kwargs),
                    timeout=timeout_val
                )

                if not response.choices:
                    raise LLMError(f"Ollama ({self.model_name}) returned empty choices array")
                content = response.choices[0].message.content or ""
                return LLMResponse(
                    content=content,
                    model=response.model or self.model_name,
                    input_tokens=getattr(response.usage, "prompt_tokens", self.estimate_tokens(prompt)),
                    output_tokens=getattr(response.usage, "completion_tokens", self.estimate_tokens(content)),
                    finish_reason=response.choices[0].finish_reason or "stop",
                    raw_response=response
                )

            except asyncio.TimeoutError:
                last_error = TimeoutError(f"Ollama request timed out after {timeout_val}s")
                logger.warning(f"Ollama timeout on attempt {attempt + 1}/{MAX_RETRIES + 1}")

            except Exception as e:
                error_str = str(e).lower()
                last_error = e

                # Connection errors are not retryable — Ollama is down
                if "connection" in error_str or "refused" in error_str:
                    raise LLMError(
                        f"Ollama not reachable at {self.base_url}. "
                        f"Start Ollama (ollama serve) and run: ollama run {self.model_name}"
                    )

                logger.warning(f"Ollama error on attempt {attempt + 1}: {e}")

            if attempt < MAX_RETRIES:
                jitter = random.uniform(0, delay * 0.1)
                await asyncio.sleep(delay + jitter)
                delay = min(delay * RETRY_MULTIPLIER, MAX_RETRY_DELAY)

        logger.error(f"Ollama failed after {MAX_RETRIES + 1} attempts: {last_error}")
        raise last_error or LLMError("Ollama max retries exceeded")

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream text generation from Ollama."""
        await self._ensure_initialized()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        if not self.client:
            mock_text = f"[Ollama not available - run: ollama run {self.model_name}]"
            for word in mock_text.split():
                yield word + " "
                await asyncio.sleep(0.05)
            return

        try:
            stream = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                **{k: v for k, v in kwargs.items() if k != "timeout"}
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")
            raise


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude API client wrapper."""

    def __init__(self, model_name: str = "claude-sonnet-4-20250514"):
        super().__init__(model_name)
        self.client = None
        self.api_key = os.getenv("ANTHROPIC_API_KEY")

    async def _ensure_initialized(self):
        """Lazy initialization of the Anthropic client."""
        if self._initialized:
            return

        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not set. Using mock responses.")
            self._initialized = True
            return

        try:
            from anthropic import AsyncAnthropic
            self.client = AsyncAnthropic(api_key=self.api_key)
            self._initialized = True
            logger.info(f"Anthropic client initialized for model: {self.model_name}")
        except ImportError:
            logger.warning("anthropic package not installed. Using mock responses.")
            self._initialized = True

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Generate text using Anthropic API with retry logic."""
        await self._ensure_initialized()
        kwargs.pop('json_mode', None)  # Anthropic doesn't support this parameter
        stop = kwargs.pop('stop', None)  # Map to Anthropic's stop_sequences

        if not self.client:
            return LLMResponse(
                content=f"[Mock Claude response for: {prompt[:100]}...]",
                model=self.model_name,
                input_tokens=self.estimate_tokens(prompt),
                output_tokens=100,
                finish_reason="stop"
            )

        # Retry loop with exponential backoff (matching OpenAI pattern)
        last_error = None
        delay = INITIAL_RETRY_DELAY
        timeout = kwargs.pop('timeout', DEFAULT_TIMEOUT_SECONDS)

        for attempt in range(MAX_RETRIES + 1):
            try:
                await rate_limit_check("anthropic")

                create_kwargs = {
                    "model": self.model_name,
                    "max_tokens": max_tokens,
                    "system": system_prompt or "You are a helpful assistant.",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                }
                if stop:
                    create_kwargs["stop_sequences"] = stop

                message = await asyncio.wait_for(
                    self.client.messages.create(**create_kwargs),
                    timeout=timeout
                )

                content = message.content[0].text if message.content else ""
                if not content:
                    logger.warning("Anthropic returned empty content")
                return LLMResponse(
                    content=content,
                    model=message.model,
                    input_tokens=getattr(message.usage, "input_tokens", 0),
                    output_tokens=getattr(message.usage, "output_tokens", 0),
                    finish_reason=message.stop_reason,
                    raw_response=message
                )

            except asyncio.TimeoutError:
                last_error = TimeoutError(f"Anthropic request timed out after {timeout}s")
                logger.warning(f"Anthropic timeout on attempt {attempt + 1}/{MAX_RETRIES + 1}")

            except Exception as e:
                error_str = str(e).lower()
                last_error = e

                if "401" in error_str or "invalid" in error_str and "key" in error_str:
                    raise AuthenticationError(f"Anthropic authentication failed: {e}")

                if "429" in error_str or "rate limit" in error_str:
                    delay = min(delay * 3, MAX_RETRY_DELAY)
                    logger.warning(f"Rate limited by Anthropic, waiting {delay}s")
                elif "overloaded" in error_str or "529" in error_str:
                    delay = min(delay * 2, MAX_RETRY_DELAY)
                    logger.warning(f"Anthropic overloaded on attempt {attempt + 1}")
                else:
                    logger.warning(f"Anthropic error on attempt {attempt + 1}: {e}")

            if attempt < MAX_RETRIES:
                jitter = random.uniform(0, delay * 0.1)
                await asyncio.sleep(delay + jitter)
                delay = min(delay * RETRY_MULTIPLIER, MAX_RETRY_DELAY)

        logger.error(f"Anthropic API failed after {MAX_RETRIES + 1} attempts: {last_error}")
        raise last_error or LLMError("Anthropic max retries exceeded")

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream text generation from Anthropic."""
        await self._ensure_initialized()
        stop = kwargs.pop('stop', None)  # Map to Anthropic's stop_sequences

        if not self.client:
            mock_text = f"[Mock Claude streaming for: {prompt[:50]}...]"
            for word in mock_text.split():
                yield word + " "
                await asyncio.sleep(0.05)
            return

        try:
            stream_kwargs = {
                "model": self.model_name,
                "max_tokens": max_tokens,
                "system": system_prompt or "You are a helpful assistant.",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
            }
            if stop:
                stream_kwargs["stop_sequences"] = stop

            async with self.client.messages.stream(**stream_kwargs) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
            raise


# Ollama/local model names - no API cost
OLLAMA_MODEL_PREFIXES = ("ollama:", "llama", "mistral", "qwen", "phi", "gemma", "codellama", "dolphin", "neural", "openhermes", "nous", "deepseek", "yi-")


def is_ollama_model(model_name: str) -> bool:
    """Check if model name indicates a local Ollama model."""
    lower = model_name.lower()
    # Use prefix-only matching to avoid false positives (e.g. "phi" in "sophie")
    return any(lower.startswith(p) for p in OLLAMA_MODEL_PREFIXES)


# Client factory
def get_client(model_name: str) -> BaseLLMClient:
    """Get appropriate client for model name. Prefers Ollama for local/no-cost."""
    model_lower = model_name.lower()

    if is_ollama_model(model_name):
        # Strip "ollama:" prefix only if present (keep tags like qwen2.5:7b)
        actual_model = model_name[7:].strip() if model_name.lower().startswith("ollama:") else model_name
        return OllamaClient(actual_model)
    if "gpt" in model_lower or "openai" in model_lower:
        return OpenAIClient(model_name)
    elif "gemini" in model_lower or "google" in model_lower:
        return GeminiClient(model_name)
    elif "claude" in model_lower or "anthropic" in model_lower:
        return AnthropicClient(model_name)
    else:
        logger.warning(f"Unknown model {model_name}, defaulting to local Ollama")
        return OllamaClient(model_name)
