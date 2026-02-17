"""GPT Image 1 wrapper for cover artwork generation."""

import asyncio
import base64
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Approximate cost per image (USD) by quality tier
_COST_ESTIMATES = {
    ("1024x1024", "low"): 0.011,
    ("1024x1024", "medium"): 0.042,
    ("1024x1024", "high"): 0.167,
    ("1024x1536", "low"): 0.016,
    ("1024x1536", "medium"): 0.063,
    ("1024x1536", "high"): 0.250,
    ("1536x1024", "low"): 0.016,
    ("1536x1024", "medium"): 0.063,
    ("1536x1024", "high"): 0.250,
}


@dataclass
class ImageGenResult:
    """Result from GPT Image 1 generation."""
    image_bytes: bytes
    format: str          # "png" | "jpeg" | "webp"
    size: str            # e.g. "1024x1536"
    cost_usd: float


async def generate_cover_image(
    prompt: str,
    orientation: str = "portrait",
    quality: str = "high",
    output_format: str = "png",
    max_retries: int = 3,
    api_key: Optional[str] = None,
) -> ImageGenResult:
    """Generate cover artwork using GPT Image 1.

    Args:
        prompt: Art direction prompt (should describe imagery only, no text).
        orientation: "portrait" (1024x1536), "landscape" (1536x1024), or "square" (1024x1024).
        quality: "low", "medium", or "high".
        output_format: "png", "jpeg", or "webp".
        max_retries: Number of retry attempts on failure.
        api_key: OpenAI API key (defaults to OPENAI_API_KEY env var).

    Returns:
        ImageGenResult with raw image bytes and metadata.

    Raises:
        RuntimeError: If all retries exhausted.
    """
    from openai import AsyncOpenAI

    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY not set. Set it as an environment variable or pass api_key."
        )

    client = AsyncOpenAI(api_key=key)

    size_map = {
        "portrait": "1024x1536",
        "landscape": "1536x1024",
        "square": "1024x1024",
    }
    size = size_map.get(orientation, "1024x1536")

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                "Generating cover artwork (attempt %d/%d, size=%s, quality=%s)",
                attempt, max_retries, size, quality,
            )
            response = await client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                n=1,
                size=size,
                quality=quality,
                output_format=output_format,
            )

            if not response.data:
                raise RuntimeError("GPT Image 1 returned empty response")

            image_data = response.data[0]

            # Decode base64 image
            if hasattr(image_data, "b64_json") and image_data.b64_json:
                image_bytes = base64.b64decode(image_data.b64_json)
            elif hasattr(image_data, "url") and image_data.url:
                # Fallback: download from URL
                import httpx
                async with httpx.AsyncClient() as http:
                    dl = await http.get(image_data.url)
                    dl.raise_for_status()
                    image_bytes = dl.content
            else:
                raise RuntimeError("No image data in response (no b64_json or url)")

            cost = _COST_ESTIMATES.get((size, quality), 0.10)
            logger.info(
                "Cover artwork generated: %d bytes, est. $%.4f", len(image_bytes), cost
            )

            return ImageGenResult(
                image_bytes=image_bytes,
                format=output_format,
                size=size,
                cost_usd=cost,
            )

        except Exception as e:
            last_error = e
            logger.warning("Image generation attempt %d failed: %s", attempt, e)
            if attempt < max_retries:
                wait = 2 ** attempt
                logger.info("Retrying in %d seconds...", wait)
                await asyncio.sleep(wait)

    raise RuntimeError(
        f"Cover image generation failed after {max_retries} attempts: {last_error}"
    )
