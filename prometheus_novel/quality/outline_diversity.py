"""Outline diversity validator — detects repetitive beat structures at the outline stage.

Computes a lightweight "signature" for each scene from outline data and flags:
1. Adjacent duplicates (scenes i and i+1 too similar)
2. Window duplicates (same signature repeats within last N scenes)
3. Monotony (too many scenes share the same narrative function)

Runs AFTER master_outline is generated, BEFORE scene drafting begins.
Config-driven via policy (warn / strict / off).
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("outline_diversity")

# Interaction type classification keywords
_INTERACTION_TYPES = {
    "confrontation": re.compile(
        r"\b(confront|argue|fight|clash|accuse|demand|shout|yell|attack|defend)\b",
        re.IGNORECASE,
    ),
    "intimacy": re.compile(
        r"\b(kiss|touch|hold|embrace|intimate|bedroom|passion|desire|sensual|sex)\b",
        re.IGNORECASE,
    ),
    "discovery": re.compile(
        r"\b(discover|find out|reveal|secret|learn|uncover|realize|truth)\b",
        re.IGNORECASE,
    ),
    "planning": re.compile(
        r"\b(plan|arrange|organize|prepare|strategy|discuss how|figure out)\b",
        re.IGNORECASE,
    ),
    "bonding": re.compile(
        r"\b(bond|connect|share|open up|vulnerable|trust|comfort|forgive)\b",
        re.IGNORECASE,
    ),
    "escape": re.compile(
        r"\b(flee|escape|run|chase|hide|avoid|evade)\b",
        re.IGNORECASE,
    ),
    "reflection": re.compile(
        r"\b(reflect|think|process|contemplate|alone|journal|remember)\b",
        re.IGNORECASE,
    ),
    "social": re.compile(
        r"\b(party|dinner|gathering|event|ceremony|celebration|reception|wedding)\b",
        re.IGNORECASE,
    ),
}

# Emotional mode classification
_EMOTIONAL_MODES = {
    "longing": re.compile(r"\b(longing|desire|want|miss|yearn|ache)\b", re.IGNORECASE),
    "conflict": re.compile(r"\b(tension|conflict|anger|frustrate|rage|bitter)\b", re.IGNORECASE),
    "tenderness": re.compile(r"\b(tender|gentle|soft|warm|caring|sweet)\b", re.IGNORECASE),
    "dread": re.compile(r"\b(dread|fear|anxious|panic|worry|terrif)\b", re.IGNORECASE),
    "joy": re.compile(r"\b(joy|happy|laugh|delight|elat|excit)\b", re.IGNORECASE),
    "grief": re.compile(r"\b(grief|mourn|loss|sorrow|pain|hurt)\b", re.IGNORECASE),
    "defiance": re.compile(r"\b(defy|rebel|refuse|resist|stand up|challenge)\b", re.IGNORECASE),
    "vulnerability": re.compile(r"\b(vulnerab|exposed|raw|unguard|open up|break down)\b", re.IGNORECASE),
}

# Scene function classification (mirrors quiet_killers but works on outline text)
_SCENE_FUNCTIONS = {
    "REVEAL": re.compile(r"\b(secret|truth|discover|confession|reveal|hidden|admit)\b", re.IGNORECASE),
    "BOND": re.compile(r"\b(connect|trust|together|closer|bond|vulnerable|comfort)\b", re.IGNORECASE),
    "CONFLICT": re.compile(r"\b(confront|argument|fight|clash|resist|betray|refuse)\b", re.IGNORECASE),
    "DECISION": re.compile(r"\b(choice|decide|commit|resolve|vow|choose|turning point)\b", re.IGNORECASE),
    "AFTERMATH": re.compile(r"\b(aftermath|consequence|damage|fallout|process|reckon)\b", re.IGNORECASE),
    "PURSUIT": re.compile(r"\b(chase|search|hunt|follow|escape|race|flee)\b", re.IGNORECASE),
}


def _classify(text: str, patterns: Dict[str, re.Pattern]) -> str:
    """Classify text against a set of keyword patterns. Returns top match or 'MIXED'."""
    scores = {}
    text_lower = text.lower()
    for label, pattern in patterns.items():
        scores[label] = len(pattern.findall(text_lower))
    if not any(scores.values()):
        return "MIXED"
    top = max(scores, key=scores.get)
    return top if scores[top] > 0 else "MIXED"


def _normalize_location(location: str) -> str:
    """Normalize a location string for comparison."""
    loc = location.lower().strip()
    # Remove articles and prepositions
    loc = re.sub(r"\b(the|a|an|at|in|on|by|near)\b", "", loc)
    loc = re.sub(r"\s+", " ", loc).strip()
    return loc


def _extract_participants(scene: dict) -> str:
    """Extract a normalized participant signature from scene data."""
    parts = []
    pov = (scene.get("pov") or "").strip().lower().split()[0] if scene.get("pov") else ""
    if pov:
        parts.append(pov)
    # Extract character names from purpose/conflict text
    purpose = scene.get("purpose", "") + " " + scene.get("central_conflict", "")
    names = re.findall(r"\b([A-Z][a-z]{2,})\b", purpose)
    for n in names[:3]:
        nl = n.lower()
        if nl not in parts:
            parts.append(nl)
    return "+".join(sorted(parts)) if parts else "unknown"


def compute_scene_signature(scene: dict) -> Dict[str, str]:
    """Compute a lightweight signature for an outline scene.

    Returns dict with: function, emotional_mode, location, participants,
    interaction_type, has_plot_delta.
    """
    # Combine all text fields for classification
    all_text = " ".join(str(scene.get(k, "")) for k in [
        "purpose", "central_conflict", "character_scene_goal",
        "outcome", "emotional_arc", "opening_hook", "differentiator",
    ])

    return {
        "function": _classify(all_text, _SCENE_FUNCTIONS),
        "emotional_mode": _classify(all_text, _EMOTIONAL_MODES),
        "location": _normalize_location(scene.get("location", "")),
        "participants": _extract_participants(scene),
        "interaction_type": _classify(all_text, _INTERACTION_TYPES),
        "has_plot_delta": "yes" if scene.get("outcome", "").strip() else "no",
    }


def _signature_similarity(sig_a: Dict[str, str], sig_b: Dict[str, str]) -> float:
    """Compute similarity score between two scene signatures (0.0 - 1.0)."""
    fields = ["function", "emotional_mode", "location", "participants", "interaction_type"]
    matches = sum(1 for f in fields if sig_a.get(f) == sig_b.get(f) and sig_a.get(f) != "MIXED")
    # Don't count MIXED matches as similarity
    non_mixed = sum(1 for f in fields if sig_a.get(f) != "MIXED" or sig_b.get(f) != "MIXED")
    return matches / max(non_mixed, 1)


def validate_outline_diversity(
    outline: List[Dict[str, Any]],
    window: int = 5,
    adjacent_threshold: float = 0.80,
    window_threshold: float = 0.70,
    max_same_function_ratio: float = 0.45,
) -> Dict[str, Any]:
    """Validate outline for diversity issues.

    Args:
        outline: Master outline (list of chapter dicts with scenes).
        window: Number of previous scenes to check for window duplicates.
        adjacent_threshold: Similarity threshold for adjacent scenes.
        window_threshold: Similarity threshold for window duplicates.
        max_same_function_ratio: Max % of scenes sharing same function.

    Returns:
        Report dict with violations, suggestions, and overall pass/fail.
    """
    # Flatten all scenes with chapter context
    all_scenes: List[Tuple[int, int, dict, Dict[str, str]]] = []
    for chapter in (outline or []):
        if not isinstance(chapter, dict):
            continue
        ch_num = int(chapter.get("chapter", 0))
        for scene in chapter.get("scenes", []):
            if not isinstance(scene, dict):
                continue
            sc_num = int(scene.get("scene", scene.get("scene_number", 0)))
            sig = compute_scene_signature(scene)
            all_scenes.append((ch_num, sc_num, scene, sig))

    if len(all_scenes) < 3:
        return {"pass": True, "violations": [], "total_scenes": len(all_scenes)}

    violations: List[Dict[str, Any]] = []

    # --- Check 1: Adjacent duplicates ---
    for i in range(1, len(all_scenes)):
        ch_a, sc_a, scene_a, sig_a = all_scenes[i - 1]
        ch_b, sc_b, scene_b, sig_b = all_scenes[i]
        sim = _signature_similarity(sig_a, sig_b)
        if sim >= adjacent_threshold:
            violations.append({
                "type": "ADJACENT_DUPLICATE",
                "severity": "high",
                "scene_a": f"ch{ch_a}_s{sc_a}",
                "scene_b": f"ch{ch_b}_s{sc_b}",
                "similarity": round(sim, 2),
                "shared_axes": [
                    f for f in ["function", "emotional_mode", "location", "interaction_type"]
                    if sig_a.get(f) == sig_b.get(f) and sig_a.get(f) != "MIXED"
                ],
                "suggestion": _suggest_fix(sig_a, sig_b, scene_a, scene_b),
            })

    # --- Check 2: Window duplicates ---
    for i in range(2, len(all_scenes)):
        ch_i, sc_i, scene_i, sig_i = all_scenes[i]
        for j in range(max(0, i - window), i - 1):  # Skip adjacent (already checked)
            ch_j, sc_j, scene_j, sig_j = all_scenes[j]
            sim = _signature_similarity(sig_i, sig_j)
            if sim >= window_threshold:
                violations.append({
                    "type": "WINDOW_DUPLICATE",
                    "severity": "medium",
                    "scene_a": f"ch{ch_j}_s{sc_j}",
                    "scene_b": f"ch{ch_i}_s{sc_i}",
                    "distance": i - j,
                    "similarity": round(sim, 2),
                    "shared_axes": [
                        f for f in ["function", "emotional_mode", "location", "interaction_type"]
                        if sig_i.get(f) == sig_j.get(f) and sig_i.get(f) != "MIXED"
                    ],
                    "suggestion": _suggest_fix(sig_j, sig_i, scene_j, scene_i),
                })

    # --- Check 3: Function monotony ---
    function_counts: Dict[str, int] = {}
    for _, _, _, sig in all_scenes:
        func = sig["function"]
        if func != "MIXED":
            function_counts[func] = function_counts.get(func, 0) + 1

    total = len(all_scenes)
    for func, count in function_counts.items():
        ratio = count / total
        if ratio > max_same_function_ratio:
            violations.append({
                "type": "FUNCTION_MONOTONY",
                "severity": "high",
                "function": func,
                "count": count,
                "total": total,
                "ratio": round(ratio, 2),
                "suggestion": f"Too many {func} scenes ({count}/{total} = {ratio:.0%}). "
                              f"Convert some to CONFLICT, REVEAL, DECISION, or AFTERMATH.",
            })

    # --- Check 4: Emotional mode monotony ---
    mode_counts: Dict[str, int] = {}
    for _, _, _, sig in all_scenes:
        mode = sig["emotional_mode"]
        if mode != "MIXED":
            mode_counts[mode] = mode_counts.get(mode, 0) + 1

    for mode, count in mode_counts.items():
        ratio = count / total
        if ratio > max_same_function_ratio:
            violations.append({
                "type": "EMOTIONAL_MONOTONY",
                "severity": "medium",
                "mode": mode,
                "count": count,
                "total": total,
                "ratio": round(ratio, 2),
                "suggestion": f"Too many '{mode}' scenes ({count}/{total}). "
                              f"Vary emotional modes: add dread, defiance, joy, or grief.",
            })

    # --- Check 5: Location clustering ---
    location_counts: Dict[str, int] = {}
    for _, _, _, sig in all_scenes:
        loc = sig["location"]
        if loc:
            location_counts[loc] = location_counts.get(loc, 0) + 1

    for loc, count in location_counts.items():
        if count > max(5, total * 0.25):  # More than 25% of scenes in one location
            violations.append({
                "type": "LOCATION_CLUSTERING",
                "severity": "low",
                "location": loc,
                "count": count,
                "total": total,
                "suggestion": f"Too many scenes at '{loc}' ({count}/{total}). "
                              f"Move some scenes to different locations for variety.",
            })

    # Build report
    high_count = sum(1 for v in violations if v["severity"] == "high")
    passed = high_count == 0

    return {
        "pass": passed,
        "total_scenes": total,
        "violations": violations,
        "high_severity": high_count,
        "medium_severity": sum(1 for v in violations if v["severity"] == "medium"),
        "low_severity": sum(1 for v in violations if v["severity"] == "low"),
        "function_distribution": function_counts,
        "emotional_distribution": mode_counts,
        "location_distribution": location_counts,
    }


def _suggest_fix(sig_a: Dict[str, str], sig_b: Dict[str, str],
                 scene_a: dict, scene_b: dict) -> str:
    """Generate a concrete fix suggestion for similar scenes."""
    shared = []
    for f in ["function", "emotional_mode", "location", "interaction_type"]:
        if sig_a.get(f) == sig_b.get(f) and sig_a.get(f) != "MIXED":
            shared.append(f)

    suggestions = []
    if "location" in shared:
        suggestions.append("move to a different location")
    if "interaction_type" in shared:
        alt_types = {"confrontation", "discovery", "intimacy", "social", "escape", "reflection"} - {sig_a.get("interaction_type", "")}
        suggestions.append(f"change interaction type (try: {', '.join(list(alt_types)[:3])})")
    if "emotional_mode" in shared:
        alt_modes = {"dread", "defiance", "joy", "grief", "vulnerability"} - {sig_a.get("emotional_mode", "")}
        suggestions.append(f"shift emotional mode (try: {', '.join(list(alt_modes)[:3])})")
    if "function" in shared:
        suggestions.append("add external event, new information, or third-party pressure")

    return "; ".join(suggestions) if suggestions else "differentiate scene purpose or outcome"


def format_diversity_report(report: Dict[str, Any]) -> str:
    """Format a diversity report as human-readable text."""
    lines = [
        f"=== OUTLINE DIVERSITY REPORT ===",
        f"Total scenes: {report['total_scenes']}",
        f"Pass: {'YES' if report['pass'] else 'NO'}",
        f"Violations: {report['high_severity']} high, {report['medium_severity']} medium, {report['low_severity']} low",
    ]

    if report.get("function_distribution"):
        lines.append(f"\nFunction distribution: {report['function_distribution']}")
    if report.get("emotional_distribution"):
        lines.append(f"Emotional distribution: {report['emotional_distribution']}")

    for v in report.get("violations", []):
        lines.append(f"\n  [{v['severity'].upper()}] {v['type']}")
        if "scene_a" in v:
            lines.append(f"    Scenes: {v['scene_a']} ↔ {v['scene_b']} (similarity: {v.get('similarity', '?')})")
        if "shared_axes" in v:
            lines.append(f"    Shared: {', '.join(v['shared_axes'])}")
        lines.append(f"    Fix: {v['suggestion']}")

    return "\n".join(lines)
