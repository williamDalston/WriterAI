"""Dialogue realism pass — deterministic tag trimming.

Detects and trims overwrought dialogue tags, redundant qualifiers,
and expository dialogue. No LLM needed for the deterministic portion.
"""

import logging
import re
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

# Redundant adverb qualifiers that weaken dialogue tags
_REDUNDANT_QUALIFIERS = [
    "softly", "gently", "quietly", "slowly", "briefly", "carefully",
    "delicately", "tenderly", "hesitantly", "reluctantly", "nervously",
    "anxiously", "wearily", "tiredly", "sadly", "simply", "merely",
]

# Expository clause starters that bloat dialogue tags
_EXPOSITORY_PATTERNS = [
    r"once\s+(?:he|she|they|I)\s+\w+",  # "once he paused"
    r"as\s+(?:he|she|they|I)\s+\w+",    # "as she looked"
    r"while\s+(?:he|she|they|I)\s+\w+",  # "while they sat"
    r"before\s+(?:he|she|they|I)\s+\w+",  # "before I could"
    r"after\s+(?:he|she|they|I)\s+\w+",   # "after she turned"
    r"in\s+order\s+to\b",
    r"so\s+that\s+(?:he|she|they|I)\b",
    r"because\s+(?:he|she|they|I)\s+\w+",
]

# Compiled patterns
_EXPOSITORY_RE = [re.compile(p, re.IGNORECASE) for p in _EXPOSITORY_PATTERNS]

# Dialogue line regex: captures quoted speech + tag
# Matches: "dialogue," tag  or  "dialogue." tag
_DIALOGUE_LINE_RE = re.compile(
    r'(["\u201c\u201d])(.+?)\1'           # quoted speech
    r'[,.]?\s*'                             # optional comma/period + space
    r'((?:I|he|she|they|we)\s+'             # pronoun start
    r'(?:say|said|ask|asked|whisper|whispered|murmur|murmured|'
    r'reply|replied|answer|answered|call|called|shout|shouted|'
    r'snap|snapped|grumble|grumbled|sigh|sighed|mutter|muttered|'
    r'declare|declared|admit|admitted|concede|conceded|'
    r'interrupt|interrupted|start|started|begin|began|'
    r'add|added|continue|continued|finish|finished|'
    r'offer|offered|suggest|suggested|demand|demanded|'
    r'plead|pleaded|beg|begged|insist|insisted)'
    r'(?:s|ed|ing)?'                        # verb conjugation
    r'[^.!?\n]*[.!?])',                     # rest of tag until sentence end
    re.IGNORECASE | re.DOTALL
)

# Simpler pattern for tags after em-dash dialogue
_EMDASH_DIALOGUE_RE = re.compile(
    r'(\u2014|---?)\s*'
    r'((?:I|he|she|they|we)\s+'
    r'(?:say|said|ask|asked|whisper|whispered|murmur|murmured|'
    r'reply|replied|answer|answered|call|called|snap|snapped|'
    r'grumble|grumbled|mutter|muttered|'
    r'declare|declared|admit|admitted|concede|conceded|'
    r'interrupt|interrupted|start|started|'
    r'add|added|continue|continued)'
    r'(?:s|ed|ing)?'
    r'[^.!?\n]*[.!?])',
    re.IGNORECASE
)


def _count_tag_words(tag: str) -> int:
    """Count words in a dialogue tag."""
    return len(tag.split())


def _trim_qualifiers(tag: str) -> str:
    """Remove redundant adverb qualifiers from a dialogue tag.

    Keeps at most one qualifier if multiple are stacked.
    """
    words = tag.split()
    qualifier_count = 0
    result = []
    for word in words:
        clean = word.strip(",.;:").lower()
        if clean in _REDUNDANT_QUALIFIERS:
            qualifier_count += 1
            if qualifier_count <= 1:
                result.append(word)  # Keep the first one
            # Skip subsequent qualifiers
        else:
            result.append(word)
    return " ".join(result)


def _trim_expository_clauses(tag: str) -> str:
    """Remove expository clauses from dialogue tags."""
    trimmed = tag
    for pattern in _EXPOSITORY_RE:
        # Remove the clause but keep the core tag
        match = pattern.search(trimmed)
        if match:
            # Remove everything from the expository clause to the next comma or end
            start = match.start()
            # Find the end of the clause (next comma or period)
            remaining = trimmed[match.end():]
            comma_match = re.match(r'[^,]*,\s*', remaining)
            if comma_match:
                end = match.end() + comma_match.end()
            else:
                end = match.end()
            trimmed = trimmed[:start].rstrip(", ") + " " + trimmed[end:].lstrip(", ")
            trimmed = " ".join(trimmed.split())  # Collapse whitespace
    return trimmed


def trim_dialogue_tags(
    text: str,
    max_tag_words: int = 12,
) -> Tuple[str, Dict[str, Any]]:
    """Trim overwrought dialogue tags in a scene.

    Args:
        text: Scene text.
        max_tag_words: Flag tags longer than this.

    Returns:
        Tuple of (modified_text, report).
    """
    report = {
        "tags_found": 0,
        "tags_trimmed": 0,
        "qualifiers_removed": 0,
        "expository_removed": 0,
    }

    def _process_tag(match: re.Match) -> str:
        full = match.group(0)
        tag_part = match.group(3) if match.lastindex >= 3 else match.group(2)
        original_tag = tag_part
        report["tags_found"] += 1

        tag_words = _count_tag_words(tag_part)
        if tag_words <= max_tag_words:
            # Still check for stacked qualifiers
            trimmed = _trim_qualifiers(tag_part)
            if trimmed != tag_part:
                report["qualifiers_removed"] += 1
                report["tags_trimmed"] += 1
                return full.replace(original_tag, trimmed)
            return full

        # Long tag — apply both trims
        trimmed = _trim_qualifiers(tag_part)
        if trimmed != tag_part:
            report["qualifiers_removed"] += 1

        trimmed = _trim_expository_clauses(trimmed)
        if trimmed != tag_part:
            report["expository_removed"] += 1

        if trimmed != tag_part:
            report["tags_trimmed"] += 1
            return full.replace(original_tag, trimmed)
        return full

    modified = _DIALOGUE_LINE_RE.sub(_process_tag, text)

    return modified, report


def process_scenes(
    scenes: List[str],
    max_tag_words: int = 12,
) -> Tuple[List[str], Dict[str, Any]]:
    """Run dialogue trimming across all scenes.

    Returns:
        Tuple of (modified_scenes, aggregate_report).
    """
    modified = []
    totals = {
        "tags_found": 0,
        "tags_trimmed": 0,
        "qualifiers_removed": 0,
        "expository_removed": 0,
        "scenes_modified": 0,
    }

    for scene in scenes:
        result, report = trim_dialogue_tags(scene, max_tag_words)
        modified.append(result)
        for key in ["tags_found", "tags_trimmed", "qualifiers_removed", "expository_removed"]:
            totals[key] += report[key]
        if report["tags_trimmed"] > 0:
            totals["scenes_modified"] += 1

    logger.info(
        "Dialogue trimming: %d tags found, %d trimmed (%d qualifiers, %d expository) across %d scenes",
        totals["tags_found"], totals["tags_trimmed"],
        totals["qualifiers_removed"], totals["expository_removed"],
        totals["scenes_modified"],
    )

    return modified, totals
