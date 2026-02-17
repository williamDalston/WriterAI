"""Replacement loop guard — prevents replacement feedback loops.

Checks that no replacement string from one quality module is itself a
target pattern in another module. If a collision is found, the
offending replacement is removed from the bank before the pass runs.
"""

import logging
import re
from typing import Any, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


def _collect_detection_patterns(
    cliche_config: Dict[str, Any],
    phrase_suppressor_bank: Dict[str, List[str]],
    emotion_phrases: Dict[str, Dict[str, Any]],
) -> List[Tuple[str, re.Pattern]]:
    """Collect all detection patterns from all quality modules.

    Returns:
        List of (source_label, compiled_regex) tuples.
    """
    patterns = []

    # Cliche cluster patterns
    for cluster_name, cluster_def in cliche_config.get("clusters", {}).items():
        for p in cluster_def.get("patterns", []):
            regex_str = p.get("regex", "") if isinstance(p, dict) else p
            if regex_str:
                try:
                    patterns.append((
                        f"cliche:{cluster_name}",
                        re.compile(regex_str, re.IGNORECASE),
                    ))
                except re.error:
                    pass

    # Phrase suppressor — exact phrase matching
    for phrase in phrase_suppressor_bank:
        try:
            patterns.append((
                f"phrase:{phrase}",
                re.compile(re.escape(phrase), re.IGNORECASE),
            ))
        except re.error:
            pass

    # Emotion diversifier — exact phrase matching
    for phrase in emotion_phrases:
        try:
            patterns.append((
                f"emotion:{phrase}",
                re.compile(re.escape(phrase), re.IGNORECASE),
            ))
        except re.error:
            pass

    return patterns


def check_replacement_loops(
    cliche_config: Dict[str, Any],
    phrase_suppressor_bank: Dict[str, List[str]],
    emotion_phrases: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Check all replacement banks for feedback loops.

    A feedback loop occurs when a replacement string R for pattern A
    would itself be detected by pattern B (in any module).

    Returns:
        Report dict with collisions found and cleaned replacement banks.
    """
    all_patterns = _collect_detection_patterns(
        cliche_config, phrase_suppressor_bank, emotion_phrases,
    )

    collisions: List[Dict[str, str]] = []

    # Check cliche cluster replacements
    for cluster_name, cluster_def in cliche_config.get("clusters", {}).items():
        for p in cluster_def.get("patterns", []):
            if not isinstance(p, dict):
                continue
            clean_replacements = []
            for repl in p.get("replacements", []):
                hit = _check_against_patterns(repl, all_patterns, f"cliche:{cluster_name}")
                if hit:
                    collisions.append({
                        "replacement": repl,
                        "source": f"cliche:{cluster_name}",
                        "collides_with": hit,
                    })
                    logger.warning(
                        "Loop guard: cliche replacement '%s' collides with %s — removed",
                        repl, hit,
                    )
                else:
                    clean_replacements.append(repl)
            p["replacements"] = clean_replacements

    # Check phrase suppressor replacements
    for phrase, replacements in list(phrase_suppressor_bank.items()):
        clean = []
        for repl in replacements:
            hit = _check_against_patterns(repl, all_patterns, f"phrase:{phrase}")
            if hit:
                collisions.append({
                    "replacement": repl,
                    "source": f"phrase:{phrase}",
                    "collides_with": hit,
                })
                logger.warning(
                    "Loop guard: phrase replacement '%s' collides with %s — removed",
                    repl, hit,
                )
            else:
                clean.append(repl)
        phrase_suppressor_bank[phrase] = clean

    # Check emotion diversifier replacements
    for phrase, config in emotion_phrases.items():
        clean = []
        for repl in config.get("replacements", []):
            hit = _check_against_patterns(repl, all_patterns, f"emotion:{phrase}")
            if hit:
                collisions.append({
                    "replacement": repl,
                    "source": f"emotion:{phrase}",
                    "collides_with": hit,
                })
                logger.warning(
                    "Loop guard: emotion replacement '%s' collides with %s — removed",
                    repl, hit,
                )
            else:
                clean.append(repl)
        config["replacements"] = clean

    return {
        "collisions_found": len(collisions),
        "collisions": collisions[:20],  # Cap detail at 20
    }


def _check_against_patterns(
    replacement: str,
    patterns: List[Tuple[str, re.Pattern]],
    own_source: str,
) -> str:
    """Check if a replacement string matches any detection pattern.

    Skips patterns from the same source (replacing phrase A with a
    variant of A is intentional, not a loop).

    Returns:
        The source label of the colliding pattern, or "" if clean.
    """
    for source_label, regex in patterns:
        # Don't flag self-collisions (same module + same pattern family)
        if source_label == own_source:
            continue
        # Same module but different pattern is still a loop
        if regex.search(replacement):
            return source_label
    return ""
