"""Quick terminal dashboard for a completed pipeline run.

Usage:
    python -m scripts.print_run_results [project_dir]

Default project_dir: data/projects/burning-vows-30k
"""

import json
import sys
from pathlib import Path

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def load(p: Path):
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def pick(d, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else "data/projects/burning-vows-30k"
    base = Path(project) / "output"

    files = {
        "run_status": Path(project) / "run_status.json",
        "run_report": base / "run_report.json",
        "quality_scorecard": base / "quality_scorecard.json",
        "craft_scorecard": base / "craft_scorecard.json",
        "quality_contract": base / "quality_contract.json",
        "facts_ledger": base / "facts_ledger.json",
        "scorecard_diff": base / "scorecard_diff.json",
    }

    data = {k: load(p) for k, p in files.items()}

    rs = data["run_status"] or {}
    rr = data["run_report"] or {}
    qs = data["quality_scorecard"] or {}
    cs = data["craft_scorecard"] or {}
    qc = data["quality_contract"] or {}
    fl = data["facts_ledger"] or {}
    sd = data["scorecard_diff"] or {}

    # ── Run Status ──
    print("\n" + "=" * 60)
    print("  RUN STATUS")
    print("=" * 60)
    print(f"  Last stage:    {rs.get('last_stage', '?')}")
    print(f"  Status:        {rs.get('last_status', '?')}")
    print(f"  Stages:        {rs.get('total_stages', '?')}")
    print(f"  Tokens:        {rs.get('total_tokens', 0):,}")
    print(f"  Cost:          ${rs.get('total_cost_usd', 0):.2f}")
    print(f"  Scenes:        {rs.get('scene_count', '?')}")
    print(f"  Incidents:     {rs.get('incidents', '?')}")

    # ── Validation from run_report ──
    val = pick(rr, "validation", default={})
    if val:
        print(f"\n  Words:         {val.get('total_words', '?'):,}")
        print(f"  Target:        {val.get('target_words', '?'):,}")
        print(f"  Hit:           {val.get('word_percentage', '?')}%")
        print(f"  Chapters:      {val.get('total_chapters', '?')}")
        print(f"  Avg/chapter:   {val.get('avg_words_per_chapter', '?')}")
        print(f"  Avg/scene:     {val.get('avg_words_per_scene', '?')}")

    # ── Quality Scores ──
    qd = pick(val, "quality_details", default={})
    scores = pick(qd, "scores", default={})
    if scores:
        print(f"\n{'=' * 60}")
        print("  QUALITY SCORES")
        print("=" * 60)
        for k, v in scores.items():
            print(f"  {k:<14} {v}/10")
        print(f"  {'overall':<14} {qd.get('overall', '?')}/10")

    # ── Strengths / Improvements ──
    strengths = pick(qd, "strengths", default=[])
    improvements = pick(qd, "areas_for_improvement", default=[])
    if strengths:
        print(f"\n  Strengths:")
        for s in strengths:
            print(f"    + {s[:120]}")
    if improvements:
        print(f"\n  Areas for improvement:")
        for s in improvements:
            print(f"    - {s[:120]}")

    # ── Craft Scorecard ──
    if cs:
        print(f"\n{'=' * 60}")
        print("  CRAFT SCORECARD")
        print("=" * 60)
        print(f"  Health score:     {cs.get('health_score', '?')}")
        print(f"  Phrase entropy:   {cs.get('phrase_entropy', '?')}")
        print(f"  Verb specificity: {cs.get('verb_specificity_index', '?')}")
        print(f"  Emotional modes:  {cs.get('emotional_mode_count', '?')}")
        dd = cs.get("dialogue_density", {})
        print(f"  Dialogue density: mean={dd.get('mean', '?')}, std={dd.get('std', '?')}")
        ed = cs.get("ending_distribution", {})
        print(f"  Ending dist:      {', '.join(f'{k}={v:.0%}' for k, v in ed.items() if v > 0)}")

        # Editorial craft (motif saturation, gestures, similes, etc.)
        ec = cs.get("editorial_craft", {})
        if ec and "skipped" not in ec:
            ec_pass = ec.get("pass", True)
            print(f"\n  Editorial craft:   {'PASS' if ec_pass else 'FAIL'} ({len(ec.get('violations', []))} issues)")
            sim = ec.get("simile_density", {})
            if sim.get("similes_per_1k") is not None:
                print(f"  Similes/1k words:  {sim.get('similes_per_1k', '?')}")
            ch_len = ec.get("chapter_length", {})
            if ch_len.get("mean"):
                print(f"  Avg ch length:     {ch_len.get('mean', '?'):.0f} words")
            for v in ec.get("violations", [])[:5]:
                msg = v.get("message", str(v))
                print(f"    ! {msg[:100]}{'...' if len(msg) > 100 else ''}")

    # ── Quality Scorecard (pass/fail) ──
    if qs:
        print(f"\n{'=' * 60}")
        print("  QUALITY SCORECARD (meter pass/fail)")
        print("=" * 60)
        for k, v in qs.items():
            if isinstance(v, dict) and "pass" in v:
                status = "PASS" if v["pass"] else "FAIL"
                print(f"  {k:<30} {status}")
        overall = qs.get("pass")
        if overall is not None:
            print(f"  {'OVERALL':<30} {'PASS' if overall else 'FAIL'}")

    # ── Quality Contract Warnings ──
    contracts = pick(qc, "contracts", default=[])
    if contracts:
        total_warnings = sum(len(c.get("warnings", [])) for c in contracts)
        scenes_with_warnings = sum(1 for c in contracts if c.get("warnings"))
        clean_scenes = sum(1 for c in contracts if not c.get("warnings"))
        print(f"\n{'=' * 60}")
        print("  QUALITY CONTRACT")
        print("=" * 60)
        print(f"  Total warnings:       {total_warnings}")
        print(f"  Scenes with warnings: {scenes_with_warnings}")
        print(f"  Clean scenes:         {clean_scenes}")

        # Warning type breakdown
        from collections import Counter
        types = Counter()
        for c in contracts:
            for w in c.get("warnings", []):
                tag = w.split(":")[0] if ":" in w else w[:30]
                types[tag] += 1
        print(f"\n  Warning types:")
        for tag, count in types.most_common(10):
            print(f"    {tag:<40} x{count}")

    # ── Artifact Metrics ──
    am = pick(rr, "artifact_metrics", default={})
    if am:
        print(f"\n{'=' * 60}")
        print("  ARTIFACT METRICS")
        print("=" * 60)
        print(f"  Total scenes generated: {am.get('total_scenes_generated', '?')}")
        print(f"  Meta-text:              {am.get('scenes_with_meta_text', '?')}")
        print(f"  Preamble:               {am.get('scenes_with_preamble', '?')}")
        print(f"  POV drift:              {am.get('scenes_with_pov_drift', '?')}")
        print(f"  Retried:                {am.get('scenes_retried', '?')}")

    # ── Cost Breakdown ──
    costs = pick(rr, "cost", "stage_costs", default=[])
    if costs:
        print(f"\n{'=' * 60}")
        print("  COST BREAKDOWN")
        print("=" * 60)
        for c in costs:
            stage = c.get("stage", "?")
            tokens = c.get("tokens", 0)
            cost = c.get("cost", 0)
            if tokens > 0:
                print(f"  {stage:<22} {tokens:>10,} tokens  ${cost:.2f}")
        total = pick(rr, "cost", "total_cost_usd", default=0)
        total_tokens = pick(rr, "cost", "total_tokens", default=0)
        print(f"  {'TOTAL':<22} {total_tokens:>10,} tokens  ${total:.2f}")

    # ── Facts Ledger ──
    if fl:
        print(f"\n{'=' * 60}")
        print("  FACTS LEDGER")
        print("=" * 60)
        entries = fl.get("entries", [])
        print(f"  Entries: {len(entries)}")

    # ── Scorecard Diff ──
    if sd:
        print(f"\n{'=' * 60}")
        print("  SCORECARD DIFF")
        print("=" * 60)
        overall = pick(sd, "overall", default={})
        print(f"  Current score: {overall.get('score_current', '?')}")
        print(f"  Regression:    {overall.get('regression', '?')}")

    print(f"\n{'=' * 60}")
    print("  Output: " + str(base))
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
