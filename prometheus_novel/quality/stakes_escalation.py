"""Cross-scene stakes escalation tracker.

Catches investigation-energy-without-irreversible-turns syndrome:
  - Stakes repeat without escalating
  - High-tension scenes lack concrete consequences
  - Progression is symbolic (finds clue, finds clue) not causal (action → cost)

Complements check_stakes_articulation() (per-scene existence check).
"""

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stakes category patterns (expanded from quiet_killers)
# ---------------------------------------------------------------------------

_STAKES_CATEGORIES: Dict[str, re.Pattern] = {
    "REPUTATION": re.compile(r"\b(?:reputation|reputational|credibility|standing|name|image|career|fired|demoted)\b", re.IGNORECASE),
    "SAFETY": re.compile(r"\b(?:safety|danger|threat|risk|attacked|ambush|weapon|gun|bomb|trap)\b", re.IGNORECASE),
    "FREEDOM": re.compile(r"\b(?:freedom|prison|trapped|escape|arrest|custody|confined|locked|detained|captured)\b", re.IGNORECASE),
    "MONEY": re.compile(r"\b(?:money|cost|owe|debt|payment|bankrupt|fortune|wealth|bribe|ransom|deal)\b", re.IGNORECASE),
    "RELATIONSHIP": re.compile(r"\b(?:relationship|marriage|divorce|family|partner|lover|friend|betray|abandon|trust)\b", re.IGNORECASE),
    "IDENTITY": re.compile(r"\b(?:identity|who\s+(?:i|she|he)\s+(?:am|is|was|really)|truth\s+about|secret|past|real\s+name)\b", re.IGNORECASE),
    "LIFE_DEATH": re.compile(r"\b(?:die|dying|dead|death|kill|murder|fatal|lethal|survive|life\s+or\s+death|last\s+breath)\b", re.IGNORECASE),
    "POWER": re.compile(r"\b(?:power|control|authority|dominance|empire|throne|rule|command|overthrow|coup)\b", re.IGNORECASE),
    "TRUTH": re.compile(r"\b(?:truth|lie|cover.?up|conspiracy|expose|reveal|evidence|proof|witness|testimony)\b", re.IGNORECASE),
    "TRUST": re.compile(r"\b(?:trust|betray|loyalty|traitor|double.?cross|informant|mole|spy|allegiance)\b", re.IGNORECASE),
}

# ---------------------------------------------------------------------------
# Consequence markers — something irreversible happened
# ---------------------------------------------------------------------------

_CONSEQUENCE_PATTERNS = [
    re.compile(r"\b(?:lost|destroyed|ruined|broken|shattered|wrecked)\b", re.IGNORECASE),
    re.compile(r"\b(?:dead|killed|shot|stabbed|murdered|executed)\b", re.IGNORECASE),
    re.compile(r"\b(?:fired|arrested|expelled|exiled|banished|disowned)\b", re.IGNORECASE),
    re.compile(r"\b(?:betrayed|abandoned|left\s+(?:him|her|them|me|us))\b", re.IGNORECASE),
    re.compile(r"\b(?:cost\s+(?:him|her|them|me|us)|paid\s+the\s+price|too\s+late)\b", re.IGNORECASE),
    re.compile(r"\b(?:couldn'?t\s+take\s+(?:it\s+)?back|no\s+going\s+back|irreversible|point\s+of\s+no\s+return)\b", re.IGNORECASE),
    re.compile(r"\b(?:because\s+(?:of|I)\s+(?:failed|chose|didn'?t|hesitated))\b", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# Cost markers — personal price paid
# ---------------------------------------------------------------------------

_COST_PATTERNS = [
    re.compile(r"\b(?:gave\s+up|sacrificed|surrendered|abandoned|walked\s+away\s+from)\b", re.IGNORECASE),
    re.compile(r"\b(?:wound|scar|injury|damage|harm|bleeding|broken\s+(?:arm|leg|rib|bone))\b", re.IGNORECASE),
    re.compile(r"\b(?:alone|isolated|cut\s+off|exiled|rejected|dismissed|outcast)\b", re.IGNORECASE),
    re.compile(r"\b(?:grief|mourn|loss|empty|hollow|numb)\b", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# Discovery-only markers (symbolic advancement, not causal)
# ---------------------------------------------------------------------------

_DISCOVERY_PATTERNS = [
    re.compile(r"\b(?:found|discovered|noticed|spotted|recognized|identified|saw|read|overheard|intercepted)\b", re.IGNORECASE),
    re.compile(r"\b(?:symbol|clue|pattern|connection|link|file|document|message|recording|photo|log)\b", re.IGNORECASE),
]


def _detect_stakes(content: str) -> List[str]:
    """Detect which stakes categories are present in content."""
    categories = []
    for cat_name, pat in _STAKES_CATEGORIES.items():
        if pat.search(content):
            categories.append(cat_name)
    return categories


def _has_consequence(content: str) -> bool:
    """Check if content contains irreversible consequence markers."""
    return any(pat.search(content) for pat in _CONSEQUENCE_PATTERNS)


def _has_cost(content: str) -> bool:
    """Check if content contains personal cost markers."""
    return any(pat.search(content) for pat in _COST_PATTERNS)


def _is_discovery_only(content: str) -> bool:
    """Check if scene only adds information without causing change."""
    has_discovery = any(pat.search(content) for pat in _DISCOVERY_PATTERNS)
    has_consequence = _has_consequence(content)
    has_cost_marker = _has_cost(content)
    return has_discovery and not has_consequence and not has_cost_marker


def track_stakes_progression(
    scenes: List[Dict],
    plateau_window: int = 3,
    consequence_deficit_threshold: float = 0.50,
) -> Dict[str, Any]:
    """Track stakes categories and consequences across scenes.

    Args:
        scenes: List of scene dicts with "content" and "tension_level" fields.
        plateau_window: Number of consecutive high-tension scenes with same
            stakes before flagging STAKES_PLATEAU.
        consequence_deficit_threshold: Max ratio of high-tension scenes
            without consequences before flagging.

    Returns:
        {
            "pass": bool,
            "violations": [{type, severity, scene_range, message}],
            "progression": [{scene_id, tension_level, stakes_categories, ...}],
            "escalation_score": float,
        }
    """
    if not scenes:
        return {
            "pass": True,
            "violations": [],
            "progression": [],
            "escalation_score": 1.0,
        }

    # Build progression timeline
    progression: List[Dict[str, Any]] = []
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        content = scene.get("content", "")
        if not content:
            continue

        tension = scene.get("tension_level", 5)
        if isinstance(tension, str):
            try:
                tension = int(tension)
            except (ValueError, TypeError):
                tension = 5

        entry = {
            "scene_id": scene.get("scene_id", ""),
            "tension_level": tension,
            "stakes_categories": _detect_stakes(content),
            "has_consequence": _has_consequence(content),
            "has_cost": _has_cost(content),
            "is_discovery_only": _is_discovery_only(content),
        }
        progression.append(entry)

    violations: List[Dict[str, Any]] = []

    # --- Check 1: STAKES_PLATEAU ---
    # N+ consecutive high-tension scenes with same dominant category, no new category
    high_tension = [p for p in progression if p["tension_level"] >= 6]
    if len(high_tension) >= plateau_window:
        for i in range(len(high_tension) - plateau_window + 1):
            window = high_tension[i:i + plateau_window]
            # Get all categories in first scene
            first_cats = set(window[0]["stakes_categories"])
            if not first_cats:
                continue
            # Check if all scenes in window have ONLY the same categories
            all_same = True
            new_introduced = False
            for entry in window[1:]:
                entry_cats = set(entry["stakes_categories"])
                if entry_cats - first_cats:
                    new_introduced = True
                if entry_cats != first_cats:
                    all_same = False

            if all_same and not new_introduced and first_cats:
                scene_range = f"{window[0]['scene_id']}..{window[-1]['scene_id']}"
                violations.append({
                    "type": "STAKES_PLATEAU",
                    "severity": "medium",
                    "scene_range": scene_range,
                    "message": (
                        f"Stakes plateau: {plateau_window} consecutive high-tension "
                        f"scenes with only [{', '.join(sorted(first_cats))}] — "
                        f"no new stakes introduced"
                    ),
                })

    # --- Check 2: CONSEQUENCE_DEFICIT ---
    if high_tension:
        without_consequence = sum(
            1 for p in high_tension if not p["has_consequence"]
        )
        deficit_ratio = without_consequence / len(high_tension)
        if deficit_ratio > consequence_deficit_threshold and len(high_tension) >= 4:
            violations.append({
                "type": "CONSEQUENCE_DEFICIT",
                "severity": "high",
                "scene_range": "manuscript-wide",
                "message": (
                    f"{deficit_ratio:.0%} of high-tension scenes "
                    f"({without_consequence}/{len(high_tension)}) lack concrete "
                    f"consequences — investigation energy without irreversible turns"
                ),
            })

    # --- Check 3: SYMBOLIC_ONLY ---
    discovery_only_count = sum(1 for p in progression if p["is_discovery_only"])
    if discovery_only_count >= 4 and len(progression) >= 8:
        ratio = discovery_only_count / len(progression)
        if ratio > 0.40:
            violations.append({
                "type": "SYMBOLIC_ONLY",
                "severity": "medium",
                "scene_range": "manuscript-wide",
                "message": (
                    f"{discovery_only_count}/{len(progression)} scenes ({ratio:.0%}) are "
                    f"discovery-only (finds clue/reads file) without consequences — "
                    f"progression feels symbolic, not causal"
                ),
            })

    # --- Escalation score ---
    # Simple heuristic: ratio of scenes with consequences + costs
    if progression:
        weighted = sum(
            (1 if p["has_consequence"] else 0) +
            (0.5 if p["has_cost"] else 0)
            for p in progression
        )
        escalation_score = min(1.0, weighted / (len(progression) * 0.6))
    else:
        escalation_score = 1.0

    return {
        "pass": all(v["severity"] != "high" for v in violations),
        "violations": violations,
        "progression": progression,
        "escalation_score": round(escalation_score, 3),
    }


def format_stakes_report(report: Dict[str, Any]) -> str:
    """Human-readable stakes escalation report."""
    lines = ["=== STAKES ESCALATION REPORT ==="]
    lines.append(f"Pass: {'YES' if report.get('pass') else 'NO'}")
    lines.append(f"Escalation score: {report.get('escalation_score', 0):.2f}")

    prog = report.get("progression", [])
    if prog:
        high = [p for p in prog if p["tension_level"] >= 6]
        lines.append(f"High-tension scenes: {len(high)}/{len(prog)}")
        with_consequence = sum(1 for p in high if p["has_consequence"])
        lines.append(f"  With consequences: {with_consequence}")
        discovery_only = sum(1 for p in prog if p["is_discovery_only"])
        lines.append(f"  Discovery-only: {discovery_only}")

    for v in report.get("violations", []):
        lines.append(f"\n  [{v['severity'].upper()}] {v['type']}: {v['message']}")

    return "\n".join(lines)
