"""Quality delta report — before/after forensics for each polish pass.

Captures counts before and after every quality pass so regressions are
visible at a glance. Output is a JSON-serializable dict suitable for
quality_delta.json.
"""

import re
from typing import Any, Dict, List, Tuple


def _count_sentences(text: str) -> int:
    """Count sentences (split on .!?)."""
    return len([s for s in re.split(r'[.!?]+', text) if s.strip()])


def _sentence_set(text: str) -> set:
    """Return a set of normalized sentences for diff comparison."""
    return {s.strip().lower() for s in re.split(r'[.!?]+', text) if s.strip()}


def compute_scene_delta(before: str, after: str) -> Dict[str, Any]:
    """Compare a single scene before/after a pass."""
    if before == after:
        return {"changed": False}

    b_sents = _sentence_set(before)
    a_sents = _sentence_set(after)

    removed = b_sents - a_sents
    added = a_sents - b_sents

    return {
        "changed": True,
        "chars_before": len(before),
        "chars_after": len(after),
        "chars_delta": len(after) - len(before),
        "sentences_before": len(b_sents),
        "sentences_removed": len(removed),
        "sentences_added": len(added),
        "pct_sentences_changed": round(
            len(removed) / max(len(b_sents), 1) * 100, 1
        ),
    }


def compute_pass_delta(
    before_texts: List[str],
    after_texts: List[str],
    pass_name: str,
    pass_report: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute delta for one quality pass across all scenes.

    Args:
        before_texts: Scene texts before the pass.
        after_texts: Scene texts after the pass.
        pass_name: Name of the pass (e.g. 'phrase_suppression').
        pass_report: The pass's own report dict.

    Returns:
        Delta summary for this pass.
    """
    scenes_changed = 0
    total_sentences_before = 0
    total_sentences_changed = 0
    total_chars_delta = 0
    hottest_scenes: List[Dict[str, Any]] = []

    for i, (b, a) in enumerate(zip(before_texts, after_texts)):
        delta = compute_scene_delta(b, a)
        if delta["changed"]:
            scenes_changed += 1
            total_sentences_before += delta["sentences_before"]
            total_sentences_changed += delta["sentences_removed"]
            total_chars_delta += delta["chars_delta"]
            if delta["pct_sentences_changed"] > 10:
                hottest_scenes.append({
                    "scene_index": i,
                    "pct_changed": delta["pct_sentences_changed"],
                    "sentences_removed": delta["sentences_removed"],
                })

    # Sort hottest scenes by % changed, keep top 5
    hottest_scenes.sort(key=lambda x: x["pct_changed"], reverse=True)

    return {
        "pass": pass_name,
        "scenes_changed": scenes_changed,
        "scenes_total": len(before_texts),
        "pct_scenes_changed": round(
            scenes_changed / max(len(before_texts), 1) * 100, 1
        ),
        "total_sentences_changed": total_sentences_changed,
        "pct_sentences_changed": round(
            total_sentences_changed / max(total_sentences_before, 1) * 100, 1
        ),
        "chars_delta": total_chars_delta,
        "hottest_scenes": hottest_scenes[:5],
        "pass_report_summary": _summarize_pass_report(pass_name, pass_report),
    }


def _summarize_pass_report(pass_name: str, report: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the most useful metrics from a pass's own report."""
    summary: Dict[str, Any] = {}
    if "error" in report:
        summary["error"] = report["error"]
        return summary

    if pass_name == "phrase_suppression":
        summary["total_replacements"] = report.get("total_replacements", 0)
        summary["phrases_processed"] = report.get("phrases_processed", 0)
        # Top 5 most-replaced phrases
        per_phrase = report.get("per_phrase", {})
        top = sorted(per_phrase.items(), key=lambda x: x[1].get("replaced", 0), reverse=True)[:5]
        summary["top_replaced"] = [
            {"phrase": k, "replaced": v.get("replaced", 0)} for k, v in top
        ]
    elif pass_name == "dialogue_trimming":
        summary["tags_trimmed"] = report.get("tags_trimmed", 0)
        summary["qualifiers_removed"] = report.get("qualifiers_removed", 0)
    elif pass_name == "emotion_diversification":
        summary["total_replaced"] = report.get("total_replaced", 0)
        summary["total_found"] = report.get("total_found", 0)
    elif pass_name == "cliche_cluster_repair":
        summary["total_replaced"] = report.get("total_replaced", 0)
        summary["clusters_repaired"] = report.get("clusters_repaired", 0)
        per_cluster = report.get("per_cluster", {})
        summary["per_cluster"] = {
            k: {"found": v.get("found", 0), "replaced": v.get("replaced", 0)}
            for k, v in per_cluster.items()
        }
    elif pass_name == "cliche_clusters":
        summary["flagged"] = report.get("flagged", 0)
    elif pass_name == "quiet_killers":
        summary["filter_removal_scenes"] = report.get("filter_removal_scenes", 0)
        summary["weak_verb_substitution_scenes"] = report.get("weak_verb_substitution_scenes", 0)
        summary["final_line_rewrite_scenes"] = report.get("final_line_rewrite_scenes", 0)
    elif pass_name == "bridge_and_grounding":
        summary["bridge_insert_scenes"] = report.get("bridge_insert_scenes", 0)
        summary["deflection_grounding_scenes"] = report.get("deflection_grounding_scenes", 0)

    return summary


def _normalize_pass_delta(d: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure every pass delta has scenes_changed to prevent KeyError downstream."""
    out = dict(d)
    if "scenes_changed" not in out:
        out["scenes_changed"] = 0
    if "scenes_total" not in out:
        out["scenes_total"] = 0
    return out


def build_delta_report(
    pass_deltas: List[Dict[str, Any]],
    unresolved: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the final quality_delta.json content.

    Args:
        pass_deltas: List of per-pass delta dicts from compute_pass_delta().
        unresolved: Issues detected but not fixed (residual cliche clusters, etc.)

    Returns:
        Full delta report dict.
    """
    total_scenes_changed = 0
    total_replacements = 0

    normalized = [_normalize_pass_delta(d) for d in pass_deltas]

    for d in normalized:
        total_scenes_changed = max(total_scenes_changed, d.get("scenes_changed", 0))
        summary = d.get("pass_report_summary", {})
        total_replacements += summary.get("total_replacements", 0)
        total_replacements += summary.get("total_replaced", 0)
        total_replacements += summary.get("tags_trimmed", 0)

    return {
        "version": 1,
        "summary": {
            "total_passes": len(normalized),
            "max_scenes_changed": total_scenes_changed,
            "total_replacements": total_replacements,
        },
        "passes": normalized,
        "unresolved": unresolved,
    }
