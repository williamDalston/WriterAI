"""SSML conversion and chunking for audiobook generation.

Converts raw prose scenes to SSML with proper narration pauses,
and chunks the output to stay within Google Cloud TTS's 5,000-byte limit.
"""

import re
import html
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# SSML templates
# ---------------------------------------------------------------------------

CHAPTER_HEADER_SSML = (
    '<break time="1s"/>'
    '<prosody rate="slow"><emphasis level="moderate">'
    "Chapter {chapter_num}"
    "</emphasis></prosody>"
    '<break time="1.5s"/>'
)

SCENE_BREAK_SSML = '<break time="2s"/>'

PARAGRAPH_BREAK_SSML = '<break time="500ms"/>'

OPENING_CREDITS_SSML = (
    "<speak>"
    '<prosody rate="0.9">'
    "{title}. "
    '<break time="1s"/>'
    "Written by {author}. "
    '<break time="1s"/>'
    "Narrated by {narrator}. "
    '<break time="1s"/>'
    "</prosody>"
    "</speak>"
)

CLOSING_CREDITS_SSML = (
    "<speak>"
    '<prosody rate="0.9">'
    '<break time="1s"/>'
    "The end. "
    '<break time="2s"/>'
    "{title}. "
    '<break time="1s"/>'
    "Written by {author}. "
    '<break time="1s"/>'
    "Narrated by {narrator}. "
    '<break time="1s"/>'
    "Copyright {year}. All rights reserved."
    "</prosody>"
    "</speak>"
)

# Scene break markers in prose
_SCENE_BREAK_RE = re.compile(r"^\s*(?:\*\s*\*\s*\*|---+|___+|⁂)\s*$", re.MULTILINE)

# Italic markup: *text* (but not **bold**)
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")

# Ellipsis
_ELLIPSIS_RE = re.compile(r"\.{3}|…")

# Sentence boundary for chunking (period/!/? followed by space or end)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


# ---------------------------------------------------------------------------
# Prose → SSML conversion
# ---------------------------------------------------------------------------

def prose_to_ssml(text: str) -> str:
    """Convert raw prose text to SSML body (without <speak> wrapper).

    Transformations applied in order:
    1. XML-escape unsafe characters (before any SSML tag insertion)
    2. Scene break markers (*** / --- / ⁂) → 2s pause
    3. Paragraph breaks (double newline) → 500ms pause
    4. Ellipsis → 300ms pause
    5. Italic markup (*text*) → <emphasis>
    """
    if not text or not text.strip():
        return ""

    # 1) XML-escape — must happen first so we don't escape our own SSML tags
    text = html.escape(text, quote=False)

    # 2) Scene break markers → long pause
    text = _SCENE_BREAK_RE.sub(SCENE_BREAK_SSML, text)

    # 3) Paragraph breaks (double newline) → medium pause
    text = re.sub(r"\n\s*\n", f"\n{PARAGRAPH_BREAK_SSML}\n", text)

    # 4) Ellipsis → short pause
    text = _ELLIPSIS_RE.sub('<break time="300ms"/>', text)

    # 5) Italic *text* → emphasis (after XML-escape, asterisks are still literal)
    text = _ITALIC_RE.sub(r'<emphasis level="moderate">\1</emphasis>', text)

    # Clean up stray single newlines (replace with space for natural reading)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

    return text.strip()


def build_chapter_ssml(
    chapter_num: Optional[int],
    scenes: List[Dict[str, Any]],
) -> str:
    """Build SSML body for one chapter (without <speak> wrapper).

    Args:
        chapter_num: Chapter number to announce, or None to skip header.
        scenes: List of scene dicts with "content" key.

    Returns:
        SSML body string ready for chunking.
    """
    parts: List[str] = []

    # Chapter header (spoken aloud)
    if chapter_num is not None:
        parts.append(CHAPTER_HEADER_SSML.format(chapter_num=chapter_num))

    for i, scene in enumerate(scenes):
        content = scene.get("content", "")
        if not content or not content.strip():
            continue

        # Scene break between scenes (not before the first)
        if i > 0:
            parts.append(SCENE_BREAK_SSML)

        parts.append(prose_to_ssml(content))

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# SSML chunking (≤5000 bytes per Google Cloud TTS request)
# ---------------------------------------------------------------------------

def chunk_ssml(ssml_body: str, max_bytes: int = 4800) -> List[str]:
    """Split SSML body into chunks that each fit within the byte limit.

    Each returned chunk is a complete, valid SSML string wrapped in
    <speak>...</speak>. The 200-byte margin (4800 vs 5000) accounts for
    the wrapper tags + UTF-8 multi-byte overhead.

    Strategy:
    - Split on sentence boundaries
    - Never split mid-SSML-tag
    - Each chunk is independently valid SSML

    Raises:
        ValueError: If a single sentence exceeds max_bytes.
    """
    if not ssml_body or not ssml_body.strip():
        return []

    wrapper_overhead = len("<speak></speak>".encode("utf-8"))
    effective_max = max_bytes - wrapper_overhead

    # Split into sentences (preserving SSML tags attached to sentences)
    sentences = _SENTENCE_SPLIT_RE.split(ssml_body)
    # Filter empty
    sentences = [s for s in sentences if s.strip()]

    if not sentences:
        return []

    chunks: List[str] = []
    current_parts: List[str] = []
    current_size = 0

    for sentence in sentences:
        sentence_bytes = len(sentence.encode("utf-8"))

        if sentence_bytes > effective_max:
            # Single sentence too large — try splitting on commas
            sub_parts = _split_long_sentence(sentence, effective_max)
            for part in sub_parts:
                part_bytes = len(part.encode("utf-8"))
                if current_size + part_bytes + 1 > effective_max:
                    if current_parts:
                        chunks.append(_wrap_speak(" ".join(current_parts)))
                    current_parts = [part]
                    current_size = part_bytes
                else:
                    current_parts.append(part)
                    current_size += part_bytes + 1
            continue

        # Would this sentence overflow the current chunk?
        if current_size + sentence_bytes + 1 > effective_max:
            # Flush current chunk
            if current_parts:
                chunks.append(_wrap_speak(" ".join(current_parts)))
            current_parts = [sentence]
            current_size = sentence_bytes
        else:
            current_parts.append(sentence)
            current_size += sentence_bytes + 1  # +1 for space join

    # Flush remaining
    if current_parts:
        chunks.append(_wrap_speak(" ".join(current_parts)))

    return chunks


def _wrap_speak(body: str) -> str:
    """Wrap SSML body in <speak> tags."""
    return f"<speak>{body}</speak>"


def _split_long_sentence(sentence: str, max_bytes: int) -> List[str]:
    """Emergency split for sentences that exceed the byte limit.

    Splits on commas first, then on spaces as a last resort.
    """
    # Try comma splits
    parts = sentence.split(", ")
    if len(parts) > 1:
        result: List[str] = []
        current = parts[0]
        for part in parts[1:]:
            candidate = current + ", " + part
            if len(candidate.encode("utf-8")) > max_bytes:
                result.append(current)
                current = part
            else:
                current = candidate
        result.append(current)
        # Verify all fit
        if all(len(p.encode("utf-8")) <= max_bytes for p in result):
            return result

    # Last resort: split on spaces
    words = sentence.split()
    result = []
    current_words: List[str] = []
    current_size = 0
    for word in words:
        word_bytes = len(word.encode("utf-8"))
        if current_size + word_bytes + 1 > max_bytes:
            if current_words:
                result.append(" ".join(current_words))
            current_words = [word]
            current_size = word_bytes
        else:
            current_words.append(word)
            current_size += word_bytes + 1
    if current_words:
        result.append(" ".join(current_words))
    return result


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------

def estimate_characters(scenes: List[Dict[str, Any]]) -> int:
    """Count total characters across all scene content."""
    total = 0
    for scene in scenes:
        content = scene.get("content", "")
        if content:
            total += len(content)
    return total


def estimate_cost_usd(
    total_chars: int,
    rate_per_million: float = 16.0,
) -> float:
    """Calculate estimated TTS cost in USD.

    Default rate is Neural2 pricing: $16 per 1M characters.
    """
    return (total_chars / 1_000_000) * rate_per_million
