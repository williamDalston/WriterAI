"""
Regression Snapshot — per-run craft scorecard + diff vs previous.

Stores:
- output/runs/<run_id>/craft_scorecard.json
- output/scorecard_diff.json (current vs previous)
- output/runs/latest_run.json (pointer to current run_id)

Config: enhancements.regression_snapshot.enabled (default True).
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("regression_snapshot")

# Metric keys to diff (scalar or nested)
_SCALAR_METRICS = ["phrase_entropy", "emotional_mode_count", "verb_specificity_index", "health_score"]
_DIALOGUE_KEYS = ["mean", "std"]
_ENDING_KEYS = ["ACTION", "DIALOGUE", "SUMMARY", "ATMOSPHERE", "UNKNOWN"]

# Simple pass thresholds (placeholder until config-driven)
_PASS_THRESHOLDS = {
    "phrase_entropy": 0.25,
    "verb_specificity_index": 0.75,
    "health_score": 50,
}


def _run_id() -> str:
    return datetime.utcnow().strftime("run_%Y%m%d_%H%M%S")


def _extract_comparable(scorecard: Dict) -> Dict[str, float]:
    """Flatten scorecard to comparable numeric values for diff."""
    out = {}
    for k in _SCALAR_METRICS:
        if k in scorecard and isinstance(scorecard[k], (int, float)):
            out[k] = float(scorecard[k])
    dd = scorecard.get("dialogue_density", {}) or {}
    if isinstance(dd, dict):
        out["dialogue_mean"] = float(dd.get("mean", 0))
        out["dialogue_std"] = float(dd.get("std", 0))
    ed = scorecard.get("ending_distribution", {}) or {}
    if isinstance(ed, dict):
        for ek in _ENDING_KEYS:
            out[f"ending_{ek}"] = float(ed.get(ek, 0))
    return out


def _compute_diff(prev: Dict[str, float], curr: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
    """Compute per-metric diff with status_change, pass flags."""
    metrics = {}
    all_keys = set(prev.keys()) | set(curr.keys())
    for k in sorted(all_keys):
        p = prev.get(k, 0)
        c = curr.get(k, 0)
        delta = c - p if isinstance(p, (int, float)) and isinstance(c, (int, float)) else 0
        if abs(delta) < 1e-6:
            status = "unchanged"
        elif delta > 0:
            status = "improved"
        else:
            status = "regressed"
        thresh = _PASS_THRESHOLDS.get(k)
        pass_prev = (p >= thresh) if thresh is not None else True
        pass_curr = (c >= thresh) if thresh is not None else True
        metrics[k] = {
            "prev": p,
            "current": c,
            "delta": round(delta, 4),
            "status_change": status,
            "pass_prev": pass_prev,
            "pass_current": pass_curr,
            "action_on_fail": "warn",
            "weight": 0.2,
        }
    return metrics


def save_regression_snapshot(
    craft_data: Dict[str, Any],
    output_dir: Path,
    config: Optional[Dict] = None,
) -> Optional[Dict[str, Any]]:
    """Save run snapshot + compute diff. Returns scorecard_diff dict or None."""
    cfg = (config or {}).get("enhancements", {}).get("regression_snapshot", {})
    if cfg.get("enabled", True) is False:
        return None
    if "skipped" in craft_data:
        return None

    output_dir = Path(output_dir)
    runs_dir = output_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    run_id = _run_id()
    run_path = runs_dir / run_id
    run_path.mkdir(parents=True, exist_ok=True)

    # Save craft_scorecard into this run
    craft_path = run_path / "craft_scorecard.json"
    with open(craft_path, "w", encoding="utf-8") as f:
        json.dump(craft_data, f, indent=2, ensure_ascii=False)
    logger.info("Regression snapshot: %s", craft_path)

    # Find previous run (deterministic: list dirs, sort, pick newest that isn't current)
    prev_run_id = None
    prev_craft = None
    run_dirs = [d.name for d in runs_dir.iterdir() if d.is_dir() and d.name.startswith("run_")]
    run_dirs.sort(reverse=True)  # newest first
    for rid in run_dirs:
        if rid == run_id:
            continue  # skip current run
        prev_path = runs_dir / rid / "craft_scorecard.json"
        if prev_path.exists():
            try:
                prev_craft = json.loads(prev_path.read_text(encoding="utf-8"))
                prev_run_id = rid
                break
            except Exception as e:
                logger.debug("Could not load %s: %s", prev_path, e)

    # Build diff
    curr_comp = _extract_comparable(craft_data)
    prev_comp = _extract_comparable(prev_craft) if prev_craft else {}
    metrics = _compute_diff(prev_comp, curr_comp)

    score_prev = craft_data.get("health_score", 0) if prev_craft else None
    score_curr = craft_data.get("health_score", 0)
    score_delta = (score_curr - score_prev) if score_prev is not None else None
    regression = score_delta is not None and score_delta < 0

    diff_output = {
        "run_id": run_id,
        "compare_to": {
            "run_id": prev_run_id,
            "mode": "previous",
            "available": prev_craft is not None,
        },
        "overall": {
            "score_prev": score_prev,
            "score_current": score_curr,
            "score_delta": score_delta,
            "regression": regression,
        },
        "metrics": metrics,
        "top_contributors": [],
    }

    # Top contributors by abs(delta)
    rows = [(k, v["delta"]) for k, v in metrics.items() if v["delta"] != 0]
    rows.sort(key=lambda r: abs(r[1]), reverse=True)
    diff_output["top_contributors"] = [{"metric": k, "delta": d} for k, d in rows[:5]]

    # Write scorecard_diff.json to output root
    diff_path = output_dir / "scorecard_diff.json"
    with open(diff_path, "w", encoding="utf-8") as f:
        json.dump(diff_output, f, indent=2, ensure_ascii=False)
    logger.info("Scorecard diff written to %s", diff_path)

    # Update latest pointer
    latest_file = runs_dir / "latest_run.json"
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump({"run_id": run_id, "timestamp": datetime.utcnow().isoformat()}, f, indent=2)

    return diff_output
