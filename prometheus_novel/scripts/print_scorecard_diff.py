#!/usr/bin/env python3
"""Print scorecard diff in a human-readable format.

Usage:
  python -m prometheus_novel.scripts.print_scorecard_diff
  python -m prometheus_novel.scripts.print_scorecard_diff data/projects/burning-vows/output/scorecard_diff.json
"""

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Print scorecard diff summary")
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Path to scorecard_diff.json (default: data/projects/burning-vows/output/scorecard_diff.json)",
    )
    args = parser.parse_args()

    if args.path:
        p = Path(args.path)
    else:
        # Default: prometheus_novel/data/projects/burning-vows/output/scorecard_diff.json
        base = Path(__file__).resolve().parent.parent
        p = base / "data" / "projects" / "burning-vows" / "output" / "scorecard_diff.json"

    if not p.exists():
        print(f"File not found: {p}", file=sys.stderr)
        print("Run a pipeline first (quality_meters stage) to generate scorecard_diff.json", file=sys.stderr)
        sys.exit(1)

    d = json.loads(p.read_text(encoding="utf-8"))

    ov = d.get("overall", {})
    cmp = d.get("compare_to", {})
    print("\nRun:", d.get("run_id", "?"))
    print("Compare:", cmp.get("mode", "?"), "->", cmp.get("run_id") or "None", "(available=%s)" % cmp.get("available"))
    sp = ov.get("score_prev")
    sc = ov.get("score_current")
    sd = ov.get("score_delta")
    reg = ov.get("regression")
    if sp is not None or sc is not None:
        delta_str = "d %+.1f" % sd if sd is not None else "d N/A"
        print("Score: %s -> %s (%s) | regression=%s" % (sp if sp is not None else "?", sc if sc is not None else "?", delta_str, reg))

    metrics = d.get("metrics", {})
    rows = []
    for k, v in metrics.items():
        rows.append((
            k,
            v.get("status_change", "?"),
            v.get("delta"),
            v.get("pass_prev"),
            v.get("pass_current"),
            v.get("action_on_fail", ""),
            v.get("weight"),
        ))
    rows.sort(key=lambda r: (abs(r[2] or 0), r[0]), reverse=True)

    print("\nMetric changes (largest delta first):")
    metrics = d.get("metrics", {})
    for k, status, delta, pp, pc, action, w in rows:
        m = metrics.get(k, {})
        prev_val, curr_val = m.get("prev"), m.get("current")
        dstr = "%+.4f" % delta if delta is not None else "N/A"
        ppstr = str(pp) if pp is not None else "?"
        pcstr = str(pc) if pc is not None else "?"
        wstr = "w=%s" % w if w is not None else ""
        # Show prev -> current for scalar metrics (health_score 0-100, etc.)
        val_str = ""
        if prev_val is not None and curr_val is not None:
            val_str = " | %s -> %s" % (prev_val, curr_val)
        print("  %-26s %-10s d %8s | %s->%s | %s %s%s" % (k, status, dstr, ppstr, pcstr, action, wstr, val_str))


if __name__ == "__main__":
    main()
