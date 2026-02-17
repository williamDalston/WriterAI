"""Emotional beat diversification pass.

Detects formulaic physical reaction phrases across a manuscript and
diversifies them using category-based replacement banks (gesture,
environment, cognition, posture).
"""

import logging
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Formulaic physical reactions grouped by body system
_REACTION_PHRASES: Dict[str, Dict[str, Any]] = {
    # Cardiac
    "my heart races": {
        "category": "cardiac",
        "replacements": [
            "my pulse kicks sideways",
            "something slams behind my sternum",
            "I feel the thud in my throat",
            "adrenaline floods my arms",
            "my blood hums",
        ],
    },
    "my heart pounds": {
        "category": "cardiac",
        "replacements": [
            "my chest feels like a drum",
            "I count the beats in my temples",
            "the pressure in my ears rises",
            "something hammers once, then settles",
        ],
    },
    "heart skips a beat": {
        "category": "cardiac",
        "replacements": [
            "the world hitches for a second",
            "everything pauses mid-frame",
            "the ground tilts slightly",
        ],
    },
    # Respiratory
    "my breath catches": {
        "category": "respiratory",
        "replacements": [
            "my lungs stall",
            "air locks in my throat",
            "I forget how breathing works",
            "something catches behind my ribs",
            "the air just—stops",
        ],
    },
    "i hold my breath": {
        "category": "respiratory",
        "replacements": [
            "I go still",
            "everything in me pauses",
            "I press my lips together",
            "my body locks up",
        ],
    },
    "let out a breath": {
        "category": "respiratory",
        "replacements": [
            "deflate slightly",
            "release the tension in my shoulders",
            "feel my chest unlock",
            "exhale through my teeth",
        ],
    },
    # Gastric
    "my stomach churns": {
        "category": "gastric",
        "replacements": [
            "something sinks in my belly",
            "nausea prickles at my throat",
            "my gut twists sideways",
            "a cold weight settles low",
        ],
    },
    "my stomach drops": {
        "category": "gastric",
        "replacements": [
            "the floor tilts under me",
            "gravity does something wrong",
            "everything inside me plummets",
            "the world lurches",
        ],
    },
    "stomach flips": {
        "category": "gastric",
        "replacements": [
            "something turns over inside me",
            "my insides do a slow roll",
            "vertigo brushes the back of my neck",
        ],
    },
    # Throat / Swallowing
    "i swallow hard": {
        "category": "throat",
        "replacements": [
            "my throat clicks",
            "I push past the knot",
            "my mouth goes dry",
            "I work my jaw",
        ],
    },
    "swallow hard": {
        "category": "throat",
        "replacements": [
            "throat tightening",
            "forcing down the knot in my throat",
            "dry swallow",
            "clench my jaw",
        ],
    },
    "lump in my throat": {
        "category": "throat",
        "replacements": [
            "something wedged behind my tongue",
            "pressure building below my voice",
            "my throat narrowing",
            "words stuck sideways",
        ],
    },
    # Trembling / Shaking
    "my hands tremble": {
        "category": "tremor",
        "replacements": [
            "my fingers won't stay still",
            "I press my palms flat against my thighs",
            "I curl my hands into fists",
            "I grip the edge of the table",
        ],
    },
    "hands shaking": {
        "category": "tremor",
        "replacements": [
            "fingers unsteady",
            "I jam my hands into my pockets",
            "I lace my fingers together to hold them still",
        ],
    },
    # Eyes / Vision
    "eyes widen": {
        "category": "ocular",
        "replacements": [
            "I blink twice, fast",
            "my focus sharpens",
            "the room snaps into clarity",
            "I look at him—really look",
        ],
    },
    "tears prick": {
        "category": "ocular",
        "replacements": [
            "heat builds behind my eyes",
            "my vision goes soft at the edges",
            "I blink against the sting",
            "my eyelashes feel wet",
        ],
    },
}

# Maximum allowed density: reactions per 1000 words before we start removing
_DEFAULT_DENSITY_THRESHOLD = 5.0
_DEFAULT_KEEP_FIRST = 2


def _find_all_occurrences(
    text: str,
    phrases: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Find all reaction phrase occurrences in text."""
    occurrences = []
    for phrase, config in phrases.items():
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        for match in pattern.finditer(text):
            occurrences.append({
                "phrase": phrase,
                "category": config["category"],
                "replacements": config["replacements"],
                "start": match.start(),
                "end": match.end(),
                "original": match.group(),
            })
    # Sort by position (reverse for safe replacement)
    occurrences.sort(key=lambda x: x["start"])
    return occurrences


def diversify_scene(
    text: str,
    phrase_bank: Optional[Dict[str, Dict[str, Any]]] = None,
    density_threshold: float = _DEFAULT_DENSITY_THRESHOLD,
    keep_first_per_phrase: int = _DEFAULT_KEEP_FIRST,
    global_counts: Optional[Counter] = None,
    global_keep: Optional[Dict[str, int]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Diversify emotional beats in a single scene.

    Args:
        text: Scene text.
        phrase_bank: Phrase -> {category, replacements}. Defaults to built-in.
        density_threshold: Max reactions per 1000 words before removing some.
        keep_first_per_phrase: How many of each phrase to keep globally.
        global_counts: Running count of each phrase across scenes.
        global_keep: Running count of how many have been kept per phrase.

    Returns:
        Tuple of (modified_text, scene_report).
    """
    bank = phrase_bank or _REACTION_PHRASES
    if global_counts is None:
        global_counts = Counter()
    if global_keep is None:
        global_keep = Counter()

    occurrences = _find_all_occurrences(text, bank)
    if not occurrences:
        return text, {"found": 0, "replaced": 0, "removed": 0}

    word_count = len(text.split())
    density = (len(occurrences) / max(word_count, 1)) * 1000

    replaced = 0
    removed = 0
    replacement_idx: Dict[str, int] = {}

    # Process in reverse order to preserve string offsets
    for occ in reversed(occurrences):
        phrase = occ["phrase"]
        global_counts[phrase] += 1
        count = global_counts[phrase]

        if count <= keep_first_per_phrase:
            global_keep[phrase] += 1
            continue  # Keep this one as-is

        replacements = occ["replacements"]
        if replacements:
            # Cycle through replacements
            idx = replacement_idx.get(phrase, 0)
            repl = replacements[idx % len(replacements)]
            replacement_idx[phrase] = idx + 1

            # Preserve capitalization
            original = occ["original"]
            if original[0].isupper():
                repl = repl[0].upper() + repl[1:]

            text = text[: occ["start"]] + repl + text[occ["end"] :]
            replaced += 1
        elif density > density_threshold:
            # No replacements and over density — remove the sentence
            # (risky, so only do it for extreme density)
            removed += 1

    return text, {"found": len(occurrences), "replaced": replaced, "removed": removed}


def process_scenes(
    scenes: List[str],
    phrase_bank: Optional[Dict[str, Dict[str, Any]]] = None,
    density_threshold: float = _DEFAULT_DENSITY_THRESHOLD,
    keep_first_per_phrase: int = _DEFAULT_KEEP_FIRST,
) -> Tuple[List[str], Dict[str, Any]]:
    """Run emotion diversification across all scenes.

    Returns:
        Tuple of (modified_scenes, aggregate_report).
    """
    bank = phrase_bank or _REACTION_PHRASES
    global_counts: Counter = Counter()
    global_keep: Dict[str, int] = Counter()

    modified = []
    total_found = 0
    total_replaced = 0
    total_removed = 0
    scenes_modified = 0

    for scene in scenes:
        result, report = diversify_scene(
            scene, bank, density_threshold, keep_first_per_phrase,
            global_counts, global_keep,
        )
        modified.append(result)
        total_found += report["found"]
        total_replaced += report["replaced"]
        total_removed += report["removed"]
        if report["replaced"] > 0 or report["removed"] > 0:
            scenes_modified += 1

    summary = {
        "total_found": total_found,
        "total_replaced": total_replaced,
        "total_removed": total_removed,
        "scenes_modified": scenes_modified,
        "per_phrase_counts": dict(global_counts.most_common()),
    }

    logger.info(
        "Emotion diversification: %d found, %d replaced, %d removed across %d scenes",
        total_found, total_replaced, total_removed, scenes_modified,
    )

    return modified, summary
