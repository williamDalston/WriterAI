"""Bond scene drift classifier: compare draft content vs intended outline type.

After scene_drafting, classify each scene as PLOT | FRICTION | BOND | CRISIS.
If actual != intended (from outline), flag for rewrite or re-draft.

Uses quality.quiet_killers.classify_scene_function (REVEAL/BOND/CONFLICT/DECISION/
AFTERMATH/PURSUIT/MIXED). Maps to ROADMAP buckets: PLOT (external), FRICTION
(CONFLICT), BOND, CRISIS (AFTERMATH, high-tension DECISION).

Config: enhancements.bond_drift.enabled
"""

from typing import Dict, List, Optional, Tuple

# Map quiet_killers function -> ROADMAP bucket
_FUNC_TO_BUCKET = {
    "REVEAL": "PLOT",
    "BOND": "BOND",
    "CONFLICT": "FRICTION",
    "DECISION": "PLOT",  # Could be CRISIS if high tension; we refine below
    "AFTERMATH": "CRISIS",
    "PURSUIT": "PLOT",
    "MIXED": "MIXED",
}


def _get_intended_function(scene: Dict, outline: List[Dict]) -> Optional[str]:
    """Extract intended scene function from outline. Returns PLOT|FRICTION|BOND|CRISIS|MIXED."""
    ch = scene.get("chapter", 0)
    sc_num = scene.get("scene_number") or scene.get("scene") or 0
    for chap in (outline or []):
        if not isinstance(chap, dict):
            continue
        if int(chap.get("chapter", 0)) != int(ch):
            continue
        for osc in (chap.get("scenes") or []):
            if not isinstance(osc, dict):
                continue
            osc_num = osc.get("scene", osc.get("scene_number"))
            if int(osc_num or 0) != int(sc_num or 0):
                continue
            func = (osc.get("function") or osc.get("scene_function") or osc.get("purpose_type") or "").upper()
            if not func:
                # Infer from purpose keywords (same logic as pipeline scene_drafting)
                purpose = (osc.get("purpose") or "").lower()
                if any(w in purpose for w in ("confront", "fight", "chase", "escape", "battle", "attack", "clash", "argument")):
                    return "FRICTION"
                if any(w in purpose for w in ("reveal", "discover", "learn", "uncover", "find out", "secret")):
                    return "PLOT"
                if any(w in purpose for w in ("bond", "connect", "romance", "intimate", "together", "chemistry", "kiss")):
                    return "BOND"
                if any(w in purpose for w in ("aftermath", "recover", "process", "grieve", "heal", "crisis", "dark night")):
                    return "CRISIS"
                return None
            # Normalize: BOND, PLOT, FRICTION, CRISIS, REVEAL, CONFLICT, etc.
            if "BOND" in func or "INTIMACY" in func:
                return "BOND"
            if "PLOT" in func or "EXTERNAL" in func or "REVEAL" in func or "PURSUIT" in func:
                return "PLOT"
            if "FRICTION" in func or "CONFLICT" in func:
                return "FRICTION"
            if "CRISIS" in func or "DARK" in func or "AFTERMATH" in func:
                return "CRISIS"
            return func.split()[0] if func else None
    return None


def _classify_draft_to_bucket(content: str, purpose: str, tension_level: int) -> str:
    """Classify drafted content into PLOT|FRICTION|BOND|CRISIS|MIXED."""
    from quality.quiet_killers import classify_scene_function

    func = classify_scene_function(content, purpose)
    bucket = _FUNC_TO_BUCKET.get(func, "MIXED")
    # DECISION at high tension -> CRISIS
    if func == "DECISION" and tension_level >= 7:
        bucket = "CRISIS"
    return bucket


def classify_bond_drift(
    scenes: List[Dict],
    outline: List[Dict],
    config: Optional[Dict] = None,
) -> List[Dict]:
    """Classify each scene; flag when actual != intended.

    Returns list of drift reports:
        [{"scene_id": str, "intended": str, "actual": str, "drift": bool, "message": str}, ...]
    """
    cfg = (config or {}).get("enhancements", {}).get("bond_drift", {})
    if not cfg.get("enabled", True):
        return []

    reports: List[Dict] = []
    for scene in (scenes or []):
        if not isinstance(scene, dict):
            continue
        sid = scene.get("scene_id") or scene.get("id") or f"ch{scene.get('chapter', 0)}_s{scene.get('scene_number', 0)}"
        content = scene.get("content", "")
        purpose = scene.get("purpose", "") or _get_purpose_from_outline(scene, outline)
        tension = int(scene.get("tension_level", 5))

        intended = _get_intended_function(scene, outline)
        actual = _classify_draft_to_bucket(content, purpose, tension)

        drift = intended is not None and actual != intended and actual != "MIXED"
        message = ""
        if intended is None:
            message = "No intended function in outline"
        elif drift:
            message = f"Drift: intended {intended}, actual {actual}"

        reports.append({
            "scene_id": sid,
            "intended": intended or "UNKNOWN",
            "actual": actual,
            "drift": drift,
            "message": message,
        })

    return reports


def _get_purpose_from_outline(scene: Dict, outline: List[Dict]) -> str:
    """Extract purpose string from outline for scene."""
    from quality.quiet_killers import _get_purpose_from_outline as _qk_get_purpose
    return _qk_get_purpose(scene, outline)


def get_drifted_scene_ids(scenes: List[Dict], outline: List[Dict], config: Optional[Dict] = None) -> List[str]:
    """Convenience: return scene IDs with drift."""
    reports = classify_bond_drift(scenes, outline, config)
    return [r["scene_id"] for r in reports if r.get("drift")]


def scan_all_scenes_for_drift(scenes: List[Dict], outline: List[Dict], config: Optional[Dict] = None) -> List[Dict]:
    """Alias for pipeline: returns list of {scene_id, warning} for drifted scenes only."""
    reports = classify_bond_drift(scenes, outline, config)
    return [
        {"scene_id": r["scene_id"], "warning": r["message"]}
        for r in reports if r.get("drift")
    ]
