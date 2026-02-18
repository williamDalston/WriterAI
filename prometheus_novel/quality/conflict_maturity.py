"""Conflict Maturity — ensures high-stakes conflicts have resolution latency.

Solution-First Bias: conflicts (accusation, secret revealed, external threat) are
often resolved immediately, collapsing narrative tension. This validator flags
outlines where a Resolution beat appears before the conflict has "breathed"
(configured latency period, e.g. +2 chapters).

Config: enhancements.conflict_maturity.enabled, resolution_latency_chapters (default 2).
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("conflict_maturity")

# Scene purpose/central_conflict patterns that indicate HIGH-STAKES conflict intro
CONFLICT_INTRO = re.compile(
    r"\b(accusation|accuse|accused|secret\s+revealed|reveal\s+the\s+(truth|secret)|"
    r"external\s+threat|threat\s+emerges|file\s+surfaces|truth\s+comes\s+out|"
    r"confrontation|confronts|exposed|betrayal\s+revealed|"
    r"legal\s+file|divorce\s+papers|evidence\s+dropped)\b",
    re.IGNORECASE,
)

# Scene purpose/outcome patterns that indicate premature resolution
RESOLUTION_CUE = re.compile(
    r"\b(resolved|resolves|resolving|forgiven|forgiveness|reconciled|"
    r"cleared\s+the\s+air|buried\s+the\s+hatchet|moved\s+past|put\s+behind|"
    r"everything\s+(?:is|was)\s+ok|made\s+peace|settled\s+it|"
    r"understanding\s+(?:passed|spread)|apologized\s+and|"
    r"all\s+was\s+(?:forgiven|well))\b",
    re.IGNORECASE,
)


def _get_scene_text(scene: Dict) -> str:
    """Concat purpose, central_conflict, outcome for classification."""
    parts = [
        scene.get("purpose", ""),
        scene.get("central_conflict", ""),
        scene.get("outcome", ""),
        scene.get("emotional_arc", ""),
    ]
    return " ".join(p for p in parts if p)


def check_conflict_maturity(
    outline: List[Dict],
    config: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Flag outlines where resolution beats appear before conflict latency expires.

    Args:
        outline: Master outline (list of chapter dicts with scenes).
        config: Optional. enhancements.conflict_maturity.resolution_latency_chapters (default 2).

    Returns:
        {
            "pass": bool,
            "violations": [{scene_id, conflict_chapter, resolution_chapter, message}],
            "conflict_scenes": [{chapter, scene_id, conflict_intro}],
        }
    """
    cfg = (config or {}).get("enhancements", {}).get("conflict_maturity", {})
    if cfg.get("enabled", True) is False:
        return {"pass": True, "violations": [], "skipped": "disabled"}

    latency = int(cfg.get("resolution_latency_chapters", 2))
    violations = []
    conflict_scenes: List[Dict[str, Any]] = []

    for ch_data in (outline or []):
        if not isinstance(ch_data, dict):
            continue
        ch_num = int(ch_data.get("chapter", 0))
        for sc in ch_data.get("scenes", []):
            if not isinstance(sc, dict):
                continue
            text = _get_scene_text(sc)
            sc_num = int(sc.get("scene", sc.get("scene_number", 0)))
            sid = sc.get("scene_id") or f"ch{ch_num:02d}_s{sc_num:02d}"

            if CONFLICT_INTRO.search(text):
                conflict_scenes.append({
                    "chapter": ch_num,
                    "scene_id": sid,
                    "conflict_intro": True,
                })

            if conflict_scenes:
                last_conflict_ch = conflict_scenes[-1]["chapter"]
                min_resolution_ch = last_conflict_ch + latency
                if RESOLUTION_CUE.search(text) and ch_num < min_resolution_ch:
                    violations.append({
                        "scene_id": sid,
                        "chapter": ch_num,
                        "conflict_chapter": last_conflict_ch,
                        "min_resolution_chapter": min_resolution_ch,
                        "message": (
                            f"{sid}: Resolution language in Ch{ch_num} but conflict introduced in Ch{last_conflict_ch}. "
                            f"Resolution should wait until at least Ch{min_resolution_ch}."
                        ),
                    })

    passed = len(violations) == 0
    if violations:
        for v in violations[:3]:
            logger.warning("Conflict maturity: %s", v.get("message", v))

    return {
        "pass": passed,
        "violations": violations,
        "conflict_scenes": conflict_scenes,
        "resolution_latency_chapters": latency,
    }
