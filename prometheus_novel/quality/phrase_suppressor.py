"""Hot phrase suppression pass.

Reads a hot phrases config (auto-generated or manual) and reduces repeated
phrases across a manuscript by replacing excess occurrences with rotating
alternatives.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Default replacement banks for common AI-heavy phrases.
# These are used when no explicit replacements are provided in config.
_DEFAULT_REPLACEMENTS: Dict[str, List[str]] = {
    "barely above a whisper": [
        "so quiet I almost missed it",
        "in a low voice",
        "under his breath",
        "almost inaudible",
        "half-swallowed",
    ],
    "voice barely above a": [
        "voice so low it was nearly",
        "voice dropping to",
        "voice reduced to",
        "voice thinned to",
        "voice trailing into",
    ],
    "the air between us": [
        "the space between us",
        "the silence between us",
        "the gap separating us",
        "what hung unspoken",
        "the charged stillness",
    ],
    "we need to talk": [
        "there's something I need to say",
        "can we—just, sit for a minute",
        "don't walk away yet",
        "hold on",
        "wait",
    ],
    "take a deep breath": [
        "draw in air slowly",
        "steady myself",
        "fill my lungs",
        "pause to breathe",
        "let the air settle in my chest",
    ],
    "a deep breath": [
        "a slow breath",
        "a measured inhale",
        "a steadying breath",
        "a long exhale",
    ],
    "heart races": [
        "pulse kicks",
        "chest tightens",
        "blood rushes",
        "heart hammers once, hard",
    ],
    "breath catches": [
        "lungs stall",
        "air locks in my throat",
        "I forget to breathe",
        "something catches behind my ribs",
    ],
    "stomach churns": [
        "gut twists",
        "nausea prickles",
        "something sinks in my belly",
        "my insides clench",
    ],
    "i swallow hard": [
        "my throat clicks",
        "I force down the lump",
        "I try to swallow",
        "my mouth goes dry",
    ],
    "swallow hard": [
        "throat tightening",
        "forcing down the knot",
        "pushing past the lump",
        "dry swallow",
    ],
}


def suppress_phrases(
    scenes: List[str],
    phrase_configs: List[Dict[str, Any]],
    replacement_bank: Optional[Dict[str, List[str]]] = None,
) -> Tuple[List[str], Dict[str, Any]]:
    """Suppress repeated phrases across a manuscript.

    Args:
        scenes: List of scene texts in order.
        phrase_configs: List of dicts with at least 'phrase' and 'keep_first'.
            Optional 'replacements' list per phrase.
        replacement_bank: Global replacement bank (phrase -> alternatives).
            Merged with _DEFAULT_REPLACEMENTS.

    Returns:
        Tuple of (modified_scenes, report_dict).
    """
    bank = dict(_DEFAULT_REPLACEMENTS)
    if replacement_bank:
        bank.update(replacement_bank)

    report: Dict[str, Dict[str, int]] = {}
    modified = list(scenes)

    for config in phrase_configs:
        phrase = config["phrase"]
        keep_first = config.get("keep_first", 2)
        replacements = config.get("replacements") or bank.get(phrase, [])

        if not replacements:
            # No replacements available — skip (just report)
            logger.debug("No replacements for '%s', skipping suppression", phrase)
            continue

        # Build case-insensitive pattern
        escaped = re.escape(phrase)
        pattern = re.compile(escaped, re.IGNORECASE)

        occurrence = 0
        replaced = 0
        replacement_idx = 0

        for scene_idx in range(len(modified)):
            text = modified[scene_idx]
            matches = list(pattern.finditer(text))
            if not matches:
                continue

            new_text = text
            # Process matches in reverse order to preserve offsets
            for match in reversed(matches):
                occurrence += 1
                if occurrence <= keep_first:
                    continue  # Keep this one

                # Get replacement (cycle through bank)
                repl = replacements[replacement_idx % len(replacements)]
                replacement_idx += 1

                # Preserve capitalization of first character
                original = match.group()
                if original[0].isupper():
                    repl = repl[0].upper() + repl[1:]

                new_text = new_text[: match.start()] + repl + new_text[match.end() :]
                replaced += 1

            modified[scene_idx] = new_text

        report[phrase] = {
            "total_found": occurrence,
            "kept": min(keep_first, occurrence),
            "replaced": replaced,
        }

        if replaced > 0:
            logger.info(
                "Phrase '%s': %d found, %d kept, %d replaced",
                phrase, occurrence, min(keep_first, occurrence), replaced,
            )

    summary = {
        "phrases_processed": len(phrase_configs),
        "total_replacements": sum(r["replaced"] for r in report.values()),
        "per_phrase": report,
    }

    return modified, summary
