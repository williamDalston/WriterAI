"""Quality Triage — priority scoring for selective polish.

Scores each scene based on quality_contract warnings to determine which
scenes need heavy polish (expensive LLM passes) vs light touch.

Used by targeted_refinement to route only bottom ~40% of scenes through
expensive passes (voice, premium, line_sharpen).
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Warning type → base score contribution
_WARNING_SCORES: Dict[str, int] = {
    "STAKELESS": 20,
    "DIALOGUE_TIDY": 15,
    "DEFLECTION": 12,
    "CONTINUITY": 10,
    "FINAL_LINE": 8,
    "RHYTHM": 5,
    "TENSION_COLLAPSE": 10,
    "CAUSALITY": 8,
    "WALLPAPER_RISK": 6,
    "DIALOGUE_EXPOSITORY": 7,
    "CH1_HOOK_WEAK": 15,
    "CONFLICT_DEFLATION": 12,
    "TRUNCATION": 18,
    "FILTER_OVERUSE": 5,
    "GENERIC_VERBS": 5,
    "PRONOUN_CLARITY": 4,
    "POV_PARAGRAPH_DRIFT": 10,
    "ATMOSPHERE_OVERUSE": 8,
    "THESIS_DIALOGUE": 6,
    "SENTENCE_OPENING_REPETITION": 5,
    "ABSTRACT_NOUN_DENSITY": 6,
}

# Warning type → recommended editor_studio pass
_WARNING_TO_ACTION: Dict[str, str] = {
    "STAKELESS": "stakes",
    "DIALOGUE_TIDY": "dialogue_friction",
    "DEFLECTION": "deflection",
    "CONTINUITY": "continuity",
    "FINAL_LINE": "final_line",
    "RHYTHM": "rhythm",
    "TENSION_COLLAPSE": "tension_collapse",
    "CAUSALITY": "causality",
    "TRUNCATION": "truncation_complete",
    "FILTER_OVERUSE": "line_sharpen",
    "GENERIC_VERBS": "line_sharpen",
    "ABSTRACT_NOUN_DENSITY": "line_sharpen",
    "ATMOSPHERE_OVERUSE": "line_sharpen",
    "DIALOGUE_EXPOSITORY": "dialogue_friction",
    "THESIS_DIALOGUE": "dialogue_friction",
}


def compute_triage(
    contracts: List[Dict[str, Any]],
    scenes: Optional[List[Dict[str, Any]]] = None,
    heavy_polish_percentile: float = 0.40,
) -> List[Dict[str, Any]]:
    """Score scenes by quality issues and flag bottom N% for heavy polish.

    Args:
        contracts: Per-scene contracts from run_quality_contract().
        scenes: Optional scene dicts (used for supplementary data).
        heavy_polish_percentile: Fraction of scenes to flag for heavy polish.

    Returns:
        List of triage dicts:
        [{"scene_id", "priority_score", "tension_level",
          "warning_count", "recommended_actions", "needs_heavy_polish"}, ...]
    """
    if not contracts:
        return []

    results: List[Dict[str, Any]] = []

    for contract in contracts:
        scene_id = contract.get("scene_id", "unknown")
        tension = contract.get("tension_level", 5)
        warnings = contract.get("warnings", [])

        # Compute raw score from warnings
        raw_score = 0
        actions = set()
        for warning in warnings:
            warning_upper = warning.upper() if isinstance(warning, str) else ""
            for prefix, score in _WARNING_SCORES.items():
                if prefix in warning_upper:
                    raw_score += score
                    action = _WARNING_TO_ACTION.get(prefix)
                    if action:
                        actions.add(action)
                    break  # Only count first match per warning

        # Tension multiplier: higher tension scenes with issues are more critical
        tension_mult = max(0.5, tension / 5.0)
        priority_score = min(100, int(raw_score * tension_mult))

        results.append({
            "scene_id": scene_id,
            "priority_score": priority_score,
            "tension_level": tension,
            "warning_count": len(warnings),
            "recommended_actions": sorted(actions),
            "needs_heavy_polish": False,  # Set below
        })

    # Flag bottom N% (highest priority scores) for heavy polish
    if results:
        sorted_by_score = sorted(results, key=lambda r: r["priority_score"], reverse=True)
        cutoff_idx = max(1, int(len(sorted_by_score) * heavy_polish_percentile))
        if cutoff_idx < len(sorted_by_score):
            threshold = sorted_by_score[cutoff_idx - 1]["priority_score"]
        else:
            threshold = 0

        for r in results:
            r["needs_heavy_polish"] = r["priority_score"] >= threshold and r["priority_score"] > 0

    heavy_count = sum(1 for r in results if r["needs_heavy_polish"])
    logger.info(
        "Quality triage: %d/%d scenes flagged for heavy polish (threshold: top %.0f%%)",
        heavy_count, len(results), heavy_polish_percentile * 100,
    )

    return results
