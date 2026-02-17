"""
Scorecard Regression — run-to-run comparison for quality trend tracking.

Writes immutable run snapshots to output/runs/<run_id>/ and computes
diffs against a comparison target (last_successful, previous, baseline).

All operations are deterministic, zero-cost, filesystem-only.
"""

import json
import hashlib
import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("scorecard_diff")

# Metric keys in quality_scorecard.json → display name + value extractor
_METRIC_EXTRACTORS = {
    "lexical_diversity": {
        "display": "Lexical Diversity",
        "value_key": "manuscript_avg",
    },
    "dialogue_density_variance": {
        "display": "Dialogue Density Variance",
        "value_key": "variance",
    },
    "emotional_mode_diversity": {
        "display": "Emotional Mode Diversity",
        "value_key": "entropy",
    },
    "verb_specificity_index": {
        "display": "Verb Specificity Index",
        "value_key": "manuscript_avg",
    },
    "scene_ending_distribution": {
        "display": "Scene Ending Distribution",
        "value_key": "evenness_score",
    },
}


def generate_run_id() -> str:
    """Timestamp + short random token."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    token = secrets.token_hex(3)
    return f"{ts}_{token}"


def _extract_metric_value(scorecard: Dict, metric_key: str) -> Optional[float]:
    """Extract the primary numeric value from a scorecard metric section."""
    section = scorecard.get(metric_key, {})
    if not isinstance(section, dict):
        return None
    extractor = _METRIC_EXTRACTORS.get(metric_key)
    if not extractor:
        return None
    return section.get(extractor["value_key"])


def _extract_metric_pass(scorecard: Dict, metric_key: str) -> Optional[bool]:
    """Extract pass/fail from a scorecard metric section."""
    section = scorecard.get(metric_key, {})
    if not isinstance(section, dict):
        return None
    return section.get("pass")


def _compute_status_change(
    pass_current: Optional[bool],
    pass_prev: Optional[bool],
    delta: Optional[float],
) -> str:
    """Determine status change label."""
    if pass_prev is None:
        return "no_compare"
    if pass_current and not pass_prev:
        return "improved"
    if not pass_current and pass_prev:
        return "regressed"
    if delta is not None and delta > 0.001:
        return "improved"
    if delta is not None and delta < -0.001:
        return "regressed"
    return "unchanged"


def build_run_manifest(
    run_id: str,
    scorecard: Dict,
    policy_hash: str = "",
    model: str = "",
    scene_count: int = 0,
) -> Dict:
    """Build run manifest for immutable storage."""
    overall_pass = scorecard.get("pass", False)
    weighted = scorecard.get("weighted", {})

    return {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": overall_pass,
        "weighted_score": weighted.get("score") if weighted else None,
        "hard_fail": weighted.get("hard_fail", False) if weighted else False,
        "scene_count": scene_count,
        "policy_fingerprint": policy_hash,
        "model": model,
    }


def compute_diff(
    current_scorecard: Dict,
    prev_scorecard: Optional[Dict],
    current_run_id: str,
    prev_run_id: str = "",
    compare_mode: str = "last_successful",
    regression_threshold: float = 0.05,
    weights_cfg: Optional[Dict] = None,
) -> Dict:
    """Compute scorecard diff between current and previous run.

    Args:
        current_scorecard: Current run's quality_scorecard.json data.
        prev_scorecard: Previous run's data (None if no comparison available).
        current_run_id: ID of current run.
        prev_run_id: ID of comparison run.
        compare_mode: "last_successful", "previous", or "baseline".
        regression_threshold: Score drop magnitude to flag regression.
        weights_cfg: Scorecard weights config (for weight info in diff).

    Returns:
        Dict suitable for JSON serialization as scorecard_diff.json.
    """
    available = prev_scorecard is not None and bool(prev_scorecard)
    wcfg = weights_cfg or {}

    # Overall scores
    current_weighted = current_scorecard.get("weighted", {})
    score_current = current_weighted.get("score") if current_weighted else None
    pass_current = current_scorecard.get("pass", False)

    score_prev = None
    pass_prev = None
    if available:
        prev_weighted = prev_scorecard.get("weighted", {})
        score_prev = prev_weighted.get("score") if prev_weighted else None
        pass_prev = prev_scorecard.get("pass", False)

    score_delta = None
    if score_current is not None and score_prev is not None:
        score_delta = round(score_current - score_prev, 4)

    regression = False
    if score_delta is not None and score_delta < -regression_threshold:
        regression = True

    # Per-metric diffs
    # Weight config key → result key mapping
    weight_key_map = {
        "lexical_diversity": "lexical_diversity",
        "dialogue_density": "dialogue_density_variance",
        "emotional_diversity": "emotional_mode_diversity",
        "verb_specificity": "verb_specificity_index",
        "scene_endings": "scene_ending_distribution",
    }

    metrics = {}
    improvements = []
    regressions = []

    for cfg_key, result_key in weight_key_map.items():
        val_current = _extract_metric_value(current_scorecard, result_key)
        pass_c = _extract_metric_pass(current_scorecard, result_key)

        val_prev = None
        pass_p = None
        if available:
            val_prev = _extract_metric_value(prev_scorecard, result_key)
            pass_p = _extract_metric_pass(prev_scorecard, result_key)

        delta = None
        if val_current is not None and val_prev is not None:
            delta = round(val_current - val_prev, 4)

        status = _compute_status_change(pass_c, pass_p, delta)

        # Get weight info from config
        metric_wcfg = wcfg.get(cfg_key, {})
        weight = metric_wcfg.get("weight", 0.20) if isinstance(metric_wcfg, dict) else 0.20
        action = metric_wcfg.get("action_on_fail", "warn") if isinstance(metric_wcfg, dict) else "warn"

        metrics[cfg_key] = {
            "result_key": result_key,
            "value_current": val_current,
            "value_prev": val_prev,
            "delta": delta,
            "pass_current": pass_c,
            "pass_prev": pass_p,
            "status_change": status,
            "weight": weight,
            "action_on_fail": action,
        }

        if status == "improved":
            improvements.append(cfg_key)
        elif status == "regressed":
            regressions.append(cfg_key)

    return {
        "run_id": current_run_id,
        "compare_to": {
            "mode": compare_mode,
            "run_id": prev_run_id,
            "available": available,
        },
        "overall": {
            "score_current": score_current,
            "score_prev": score_prev,
            "score_delta": score_delta,
            "passed_current": pass_current,
            "passed_prev": pass_prev,
            "regression": regression,
            "threshold": regression_threshold,
        },
        "metrics": metrics,
        "top_contributors": {
            "improvements": improvements,
            "regressions": regressions,
        },
    }


def _read_pointer(runs_dir: Path, pointer_name: str) -> Optional[str]:
    """Read a run ID from a pointer file (latest.json, last_successful.json, etc.)."""
    pointer_path = runs_dir / pointer_name
    if not pointer_path.exists():
        return None
    try:
        data = json.loads(pointer_path.read_text(encoding="utf-8"))
        return data.get("run_id")
    except (json.JSONDecodeError, OSError):
        return None


def _write_pointer(runs_dir: Path, pointer_name: str, run_id: str) -> None:
    """Write a run ID to a pointer file."""
    pointer_path = runs_dir / pointer_name
    pointer_path.write_text(
        json.dumps({"run_id": run_id}, indent=2),
        encoding="utf-8",
    )


def _load_run_scorecard(runs_dir: Path, run_id: str) -> Optional[Dict]:
    """Load quality_scorecard.json from a run directory."""
    sc_path = runs_dir / run_id / "quality_scorecard.json"
    if not sc_path.exists():
        return None
    try:
        return json.loads(sc_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _prune_old_runs(runs_dir: Path, max_history: int) -> None:
    """Remove oldest run directories beyond max_history."""
    run_dirs = sorted(
        [d for d in runs_dir.iterdir() if d.is_dir()],
        key=lambda d: d.name,
    )
    if len(run_dirs) <= max_history:
        return
    for d in run_dirs[: len(run_dirs) - max_history]:
        try:
            for f in d.iterdir():
                f.unlink()
            d.rmdir()
        except OSError as e:
            logger.debug("Failed to prune run dir %s: %s", d, e)


def store_and_diff(
    output_dir: Path,
    scorecard: Dict,
    regression_cfg: Optional[Dict] = None,
    weights_cfg: Optional[Dict] = None,
    policy_hash: str = "",
    model: str = "",
    scene_count: int = 0,
) -> Dict:
    """Store current run snapshot and compute diff against comparison target.

    This is the main entry point called from the pipeline.

    Args:
        output_dir: Project output directory (output/).
        scorecard: Current quality_scorecard.json data.
        regression_cfg: ScorecardRegressionConfig as dict.
        weights_cfg: ScorecardWeightsConfig as dict.
        policy_hash: Policy fingerprint for manifest.
        model: Model identifier for manifest.
        scene_count: Number of scenes scored.

    Returns:
        Dict with diff data (also written to disk).
    """
    cfg = regression_cfg or {}
    if not cfg.get("enabled", False):
        return {"enabled": False}

    compare_to = cfg.get("compare_to", "last_successful")
    threshold = cfg.get("regression_threshold", 0.05)
    max_history = cfg.get("max_history", 50)

    runs_dir = output_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    # Generate run ID and create run directory
    run_id = generate_run_id()
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Write scorecard snapshot
    sc_path = run_dir / "quality_scorecard.json"
    sc_path.write_text(
        json.dumps(scorecard, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Write manifest
    manifest = build_run_manifest(
        run_id=run_id,
        scorecard=scorecard,
        policy_hash=policy_hash,
        model=model,
        scene_count=scene_count,
    )
    manifest_path = run_dir / "run_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Resolve comparison target
    prev_run_id = ""
    prev_scorecard = None

    if compare_to == "last_successful":
        prev_run_id = _read_pointer(runs_dir, "last_successful.json") or ""
    elif compare_to == "previous":
        prev_run_id = _read_pointer(runs_dir, "latest.json") or ""
    elif compare_to == "baseline":
        baseline_id = cfg.get("baseline_run_id", "")
        if baseline_id:
            prev_run_id = baseline_id
        else:
            prev_run_id = _read_pointer(runs_dir, "baseline.json") or ""

    if prev_run_id and prev_run_id != run_id:
        prev_scorecard = _load_run_scorecard(runs_dir, prev_run_id)

    # Compute diff
    diff = compute_diff(
        current_scorecard=scorecard,
        prev_scorecard=prev_scorecard,
        current_run_id=run_id,
        prev_run_id=prev_run_id,
        compare_mode=compare_to,
        regression_threshold=threshold,
        weights_cfg=weights_cfg,
    )

    # Write diff to run dir and output root
    diff_json = json.dumps(diff, indent=2, ensure_ascii=False)
    (run_dir / "scorecard_diff.json").write_text(diff_json, encoding="utf-8")
    (output_dir / "scorecard_diff.json").write_text(diff_json, encoding="utf-8")

    # Update pointers
    _write_pointer(runs_dir, "latest.json", run_id)
    if manifest["passed"]:
        _write_pointer(runs_dir, "last_successful.json", run_id)

    # Prune old runs
    _prune_old_runs(runs_dir, max_history)

    logger.info(
        "Scorecard regression: run=%s compare=%s score_delta=%s regression=%s",
        run_id,
        prev_run_id or "none",
        diff["overall"].get("score_delta"),
        diff["overall"].get("regression"),
    )

    return diff
