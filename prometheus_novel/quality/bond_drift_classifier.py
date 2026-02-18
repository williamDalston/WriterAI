"""Bond scene drift classifier (ROADMAP_V2 #8).

After scene_drafting, classify each scene: PLOT | FRICTION | BOND | CRISIS.
If actual != intended (from outline), flag for rewrite or re-draft.

Config: enhancements.bond_drift_classifier.enabled
"""

from typing import Dict, List, Any, Optional

# Map quiet_killers taxonomy to roadmap taxonomy
# quiet_killers: REVEAL, BOND, CONFLICT, DECISION, AFTERMATH, PURSUIT, MIXED
# roadmap: PLOT, FRICTION, BOND, CRISIS
_FUNC_TO_ROADMAP = {
    "REVEAL": "PLOT",
    "BOND": "BOND",
    "CONFLICT": "FRICTION",
    "DECISION": "PLOT",
    "AFTERMATH": "PLOT",
    "PURSUIT": "CRISIS",
    "MIXED": "PLOT",  # MIXED defaults to PLOT for drift comparison
}


def _get_intended_from_outline(scene: Dict, outline: List[Dict]) -> Optional[str]:
    """Extract intended function from outline for this scene."""
    ch = scene.get("chapter", 0)
    sn = scene.get("scene_number", scene.get("scene", 0))
    for chap in (outline or []):
        if int(chap.get("chapter", 0)) != int(ch):
            continue
        for sc in chap.get("scenes", []):
            outline_sn = sc.get("scene", sc.get("scene_number"))
            if outline_sn == sn or int(outline_sn or 0) == int(sn or 0):
                func = (sc.get("function") or sc.get("scene_function") or "").upper().strip()
                return _FUNC_TO_ROADMAP.get(func, func or None) if func else None
    return None


def _classify_actual(content: str, purpose: str = "") -> str:
    """Classify actual scene function from content."""
    try:
        from quality.quiet_killers import classify_scene_function
        raw = classify_scene_function(content, purpose)
        return _FUNC_TO_ROADMAP.get(raw, raw)
    except Exception:
        return "PLOT"


def _get_purpose_from_outline(scene: Dict, outline: List[Dict]) -> str:
    """Extract purpose string from outline."""
    ch = scene.get("chapter", 0)
    for chap in (outline or []):
        if int(chap.get("chapter", 0)) != int(ch):
            continue
        for sc in chap.get("scenes", []):
            outline_sn = sc.get("scene", sc.get("scene_number"))
            pip_sn = scene.get("scene_number", scene.get("scene", 0))
            if outline_sn == pip_sn or int(outline_sn or 0) == int(pip_sn or 0):
                return sc.get("purpose") or ""
    return ""


def check_bond_drift(
    scenes: List[Dict],
    outline: List[Dict],
) -> List[Dict[str, Any]]:
    """Compare intended vs actual scene function. Flag drifts.

    Args:
        scenes: Drafted scenes with "content", "chapter", "scene_number"
        outline: Master outline with chapters.scenes[].function

    Returns:
        List of {"scene_id", "intended", "actual", "drifted": bool}
    """
    reports = []
    for scene in (scenes or []):
        if not isinstance(scene, dict):
            continue
        content = scene.get("content", "") or ""
        scene_id = scene.get("scene_id") or f"ch{scene.get('chapter', 0)}_s{scene.get('scene_number', scene.get('scene', 0))}"

        intended = _get_intended_from_outline(scene, outline)
        purpose = _get_purpose_from_outline(scene, outline)
        actual = _classify_actual(content, purpose)

        # If no intended from outline, use scene_profile/function from scene itself if available
        if intended is None:
            profile = scene.get("scene_profile", {})
            intended_raw = profile.get("function") or scene.get("scene_function")
            if intended_raw:
                intended = _FUNC_TO_ROADMAP.get(str(intended_raw).upper(), str(intended_raw))

        drifted = intended is not None and intended != actual
        reports.append({
            "scene_id": scene_id,
            "intended": intended or "UNKNOWN",
            "actual": actual,
            "drifted": drifted,
        })
    return reports
