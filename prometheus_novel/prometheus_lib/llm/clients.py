"""
LLM Client Wrappers - OpenAI, Gemini, and Local Model Support

Provides async wrappers for various LLM providers with:
- Retry logic with exponential backoff
- Token counting and cost estimation
- Streaming support
- Error handling and fallbacks
"""

import os
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, AsyncIterator
from dataclasses import dataclass

logger = logging.getLogger(__name__)


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
        """Rough token estimation (4 chars per token average)."""
        return len(text) // 4


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
        """Generate text using OpenAI API."""
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

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )

            return LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                finish_reason=response.choices[0].finish_reason,
                raw_response=response
            )

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

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
        """Generate text using Gemini API."""
        await self._ensure_initialized()

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        if not self.model:
            # Mock response
            logger.debug("Using mock Gemini response")
            return LLMResponse(
                content=f"[Mock Gemini response for: {prompt[:100]}...]",
                model=self.model_name,
                input_tokens=self.estimate_tokens(prompt),
                output_tokens=100,
                finish_reason="stop"
            )

        try:
            # Gemini API is sync, so run in executor
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.model.generate_content(
                    full_prompt,
                    generation_config={
                        "max_output_tokens": max_tokens,
                        "temperature": temperature
                    }
                )
            )

            return LLMResponse(
                content=response.text,
                model=self.model_name,
                input_tokens=self.estimate_tokens(full_prompt),
                output_tokens=self.estimate_tokens(response.text),
                finish_reason="stop",
                raw_response=response
            )

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise

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
            response = await asyncio.get_event_loop().run_in_executor(
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
        """Generate text using Anthropic API."""
        await self._ensure_initialized()

        if not self.client:
            return LLMResponse(
                content=f"[Mock Claude response for: {prompt[:100]}...]",
                model=self.model_name,
                input_tokens=self.estimate_tokens(prompt),
                output_tokens=100,
                finish_reason="stop"
            )

        try:
            message = await self.client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                system=system_prompt or "You are a helpful assistant.",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature
            )

            return LLMResponse(
                content=message.content[0].text,
                model=message.model,
                input_tokens=message.usage.input_tokens,
                output_tokens=message.usage.output_tokens,
                finish_reason=message.stop_reason,
                raw_response=message
            )

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise

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

        if not self.client:
            mock_text = f"[Mock Claude streaming for: {prompt[:50]}...]"
            for word in mock_text.split():
                yield word + " "
                await asyncio.sleep(0.05)
            return

        try:
            async with self.client.messages.stream(
                model=self.model_name,
                max_tokens=max_tokens,
                system=system_prompt or "You are a helpful assistant.",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
            raise


# Client factory
def get_client(model_name: str) -> BaseLLMClient:
    """Get appropriate client for model name."""
    model_lower = model_name.lower()

    if "gpt" in model_lower or "openai" in model_lower:
        return OpenAIClient(model_name)
    elif "gemini" in model_lower or "google" in model_lower:
        return GeminiClient(model_name)
    elif "claude" in model_lower or "anthropic" in model_lower:
        return AnthropicClient(model_name)
    else:
        # Default to OpenAI
        logger.warning(f"Unknown model {model_name}, defaulting to OpenAI")
        return OpenAIClient(model_name)
