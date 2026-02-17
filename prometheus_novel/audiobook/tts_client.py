"""Google Cloud Text-to-Speech client with rate limiting and retry.

Wraps the google-cloud-texttospeech SDK to synthesize SSML into audio bytes.
Uses the same retry/rate-limiting patterns as the LLM clients in clients.py.
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retry configuration (mirrors clients.py)
# ---------------------------------------------------------------------------

MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1.0      # seconds
MAX_RETRY_DELAY = 30.0          # seconds
RETRY_MULTIPLIER = 2.0
REQUESTS_PER_MINUTE = 250       # Google TTS allows ~300/min for Neural2


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class TTSError(Exception):
    """Base exception for TTS errors."""
    pass


class TTSAuthError(TTSError):
    """Authentication / credentials error."""
    pass


class TTSRateLimitError(TTSError):
    """Rate limit exceeded."""
    pass


# ---------------------------------------------------------------------------
# Rate limiting (same pattern as clients.py)
# ---------------------------------------------------------------------------

_request_timestamps: List[float] = []


async def _rate_limit_wait():
    """Token bucket rate limiter: 250 requests/minute."""
    now = time.time()
    window = 60  # 1 minute

    # Clean old timestamps
    global _request_timestamps
    _request_timestamps = [ts for ts in _request_timestamps if now - ts < window]

    if len(_request_timestamps) >= REQUESTS_PER_MINUTE:
        oldest = _request_timestamps[0]
        wait_time = window - (now - oldest) + 0.1
        if wait_time > 0:
            logger.warning(f"TTS rate limit: waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)

    _request_timestamps.append(time.time())


# ---------------------------------------------------------------------------
# TTS Client
# ---------------------------------------------------------------------------

@dataclass
class TTSClient:
    """Google Cloud Text-to-Speech client with retry and rate limiting.

    Requires either:
    - GOOGLE_APPLICATION_CREDENTIALS env var pointing to a service account JSON
    - Application Default Credentials (gcloud auth application-default login)
    """

    _client: Any = None
    _texttospeech: Any = None  # Module reference

    @classmethod
    def create(cls) -> "TTSClient":
        """Factory: initialize the Google Cloud TTS client.

        Raises:
            TTSAuthError: If credentials are not configured.
            ImportError: If google-cloud-texttospeech is not installed.
        """
        try:
            from google.cloud import texttospeech
        except ImportError:
            raise ImportError(
                "google-cloud-texttospeech is required for audiobook generation.\n"
                "Install: pip install google-cloud-texttospeech"
            )

        try:
            client = texttospeech.TextToSpeechClient()
        except Exception as e:
            raise TTSAuthError(
                f"Failed to initialize Google Cloud TTS client: {e}\n"
                "Ensure credentials are configured:\n"
                "  Option 1: Set GOOGLE_APPLICATION_CREDENTIALS env var\n"
                "  Option 2: Run 'gcloud auth application-default login'\n"
                "  Docs: https://cloud.google.com/text-to-speech/docs/before-you-begin"
            )

        instance = cls(_client=client, _texttospeech=texttospeech)
        logger.info("Google Cloud TTS client initialized")
        return instance

    async def synthesize(
        self,
        ssml: str,
        voice_name: str = "en-US-Neural2-D",
        speaking_rate: float = 0.95,
        pitch: float = 0.0,
    ) -> bytes:
        """Synthesize SSML to MP3 audio bytes.

        Args:
            ssml: Complete SSML string (must include <speak> root).
            voice_name: Google voice ID (e.g., en-US-Neural2-D).
            speaking_rate: 0.25 to 4.0 (0.95 = slightly slow for narration).
            pitch: -20.0 to +20.0 semitones.

        Returns:
            Raw MP3 audio bytes.

        Raises:
            TTSError: On all failures after retries.
            TTSAuthError: On authentication errors (no retry).
        """
        tts = self._texttospeech

        # Parse language code from voice name (e.g., "en-US-Neural2-D" → "en-US")
        parts = voice_name.split("-")
        language_code = f"{parts[0]}-{parts[1]}" if len(parts) >= 2 else "en-US"

        synthesis_input = tts.SynthesisInput(ssml=ssml)

        voice_params = tts.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name,
        )

        audio_config = tts.AudioConfig(
            audio_encoding=tts.AudioEncoding.MP3,
            speaking_rate=speaking_rate,
            pitch=pitch,
            sample_rate_hertz=44100,
        )

        return await self._synthesize_with_retry(
            synthesis_input, voice_params, audio_config
        )

    async def _synthesize_with_retry(
        self,
        synthesis_input: Any,
        voice_params: Any,
        audio_config: Any,
    ) -> bytes:
        """Retry with exponential backoff on transient errors."""
        last_error: Optional[Exception] = None
        delay = INITIAL_RETRY_DELAY

        for attempt in range(MAX_RETRIES + 1):
            try:
                await _rate_limit_wait()

                # Google TTS Python SDK is synchronous — run in thread
                response = await asyncio.to_thread(
                    self._client.synthesize_speech,
                    input=synthesis_input,
                    voice=voice_params,
                    audio_config=audio_config,
                )

                return response.audio_content

            except Exception as e:
                error_str = str(e).lower()
                last_error = e

                # Auth errors — don't retry
                if "403" in error_str or "permission" in error_str:
                    raise TTSAuthError(f"TTS authentication failed: {e}")

                if "401" in error_str or "unauthorized" in error_str:
                    raise TTSAuthError(f"TTS authentication failed: {e}")

                # Rate limit — longer backoff
                if "429" in error_str or "rate" in error_str:
                    delay = min(delay * 3, MAX_RETRY_DELAY)
                    logger.warning(
                        f"TTS rate limited, attempt {attempt + 1}/{MAX_RETRIES + 1}, "
                        f"waiting {delay}s"
                    )

                # Server errors — standard backoff
                elif "500" in error_str or "503" in error_str:
                    logger.warning(
                        f"TTS server error, attempt {attempt + 1}/{MAX_RETRIES + 1}"
                    )

                else:
                    logger.warning(
                        f"TTS error on attempt {attempt + 1}/{MAX_RETRIES + 1}: {e}"
                    )

            if attempt < MAX_RETRIES:
                jitter = random.uniform(0, delay * 0.1)
                await asyncio.sleep(delay + jitter)
                delay = min(delay * RETRY_MULTIPLIER, MAX_RETRY_DELAY)

        raise TTSError(
            f"TTS synthesis failed after {MAX_RETRIES + 1} attempts: {last_error}"
        )
