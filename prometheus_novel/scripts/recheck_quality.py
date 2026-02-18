"""Re-run quality_contract on fixed manuscript and compare warning counts.

Usage:
    python -m prometheus_novel.scripts.recheck_quality [project_path]
    python -m prometheus_novel.scripts.recheck_quality data/projects/burning-vows-30k
"""

import argparse
import json
import sys
import os
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from quality.quality_contract import run_quality_contract
from quality.quiet_killers import classify_scene_function

PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_PROJECT = PROJECT_ROOT / "data" / "projects" / "burning-vows-30k"


def count_warnings(contracts):
    totals = defaultdict(int)
    for c in contracts:
        for w in c.get("warnings", []):
            prefix = w.split(":")[0] if ":" in w else "OTHER"
            totals[prefix] += 1
    return dict(totals)


def main():
    parser = argparse.ArgumentParser(description="Re-run quality_contract and compare warning counts")
    parser.add_argument("project_path", nargs="?", default=str(DEFAULT_PROJECT), help="Project path (default: burning-vows-30k)")
    args = parser.parse_args()

    project = Path(args.project_path)
    if not project.is_absolute():
        project = PROJECT_ROOT / project
    if not project.exists():
        print(f"[ERROR] Project not found: {project}")
        return 1

    state_file = project / "pipeline_state.json"
    old_contract = project / "output" / "quality_contract.json"
    new_contract = project / "output" / "quality_contract_post_fix.json"

    with open(state_file, encoding="utf-8") as f:
        state = json.load(f)

    scenes = [s for s in state.get("scenes", []) if isinstance(s, dict)]
    outline = state.get("master_outline", [])

    result = run_quality_contract(scenes, outline)
    contracts = result.get("contracts", [])

    new_contract.parent.mkdir(parents=True, exist_ok=True)
    with open(new_contract, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    new_counts = count_warnings(contracts)
    new_total = sum(new_counts.values())

    old_counts = {}
    old_total = 0
    old_contracts = []
    if old_contract.exists():
        with open(old_contract, encoding="utf-8") as f:
            old_data = json.load(f)
        old_contracts = old_data.get("contracts", [])
        old_counts = count_warnings(old_contracts)
        old_total = sum(old_counts.values())

    print("=" * 60)
    print("QUALITY CONTRACT COMPARISON")
    print("=" * 60)
    print(f"Project: {project}")
    print(f"\n{'Warning Type':<30} {'Before':>8} {'After':>8} {'Delta':>8}")
    print("-" * 56)
    all_types = sorted(set(list(old_counts.keys()) + list(new_counts.keys())))
    for wtype in all_types:
        old = old_counts.get(wtype, 0)
        new = new_counts.get(wtype, 0)
        delta = new - old
        sign = "+" if delta > 0 else ""
        print(f"{wtype:<30} {old:>8} {new:>8} {sign}{delta:>7}")
    print("-" * 56)
    print(f"{'TOTAL':<30} {old_total:>8} {new_total:>8} {new_total - old_total:>+8}")

    clean_before = sum(1 for c in old_contracts if not c.get("warnings"))
    clean_after = sum(1 for c in contracts if not c.get("warnings"))
    print(f"\nClean scenes (0 warnings):     {clean_before} -> {clean_after}")
    print(f"Saved to: {new_contract}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
