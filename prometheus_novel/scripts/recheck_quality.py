"""Re-run quality_contract on fixed manuscript and compare warning counts."""

import json
import sys
import os
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from quality.quality_contract import run_quality_contract
from quality.quiet_killers import classify_scene_function

PROJECT = Path(__file__).parent.parent / "data" / "projects" / "burning-vows-30k"
STATE_FILE = PROJECT / "pipeline_state.json"
OLD_CONTRACT = PROJECT / "output" / "quality_contract.json"
NEW_CONTRACT = PROJECT / "output" / "quality_contract_post_fix.json"


def count_warnings(contracts):
    totals = defaultdict(int)
    for c in contracts:
        for w in c.get("warnings", []):
            prefix = w.split(":")[0] if ":" in w else "OTHER"
            totals[prefix] += 1
    return dict(totals)


def main():
    with open(STATE_FILE, encoding="utf-8") as f:
        state = json.load(f)

    scenes = [s for s in state.get("scenes", []) if isinstance(s, dict)]
    outline = state.get("master_outline", [])

    # Run quality contract on all scenes
    result = run_quality_contract(scenes, outline)
    contracts = result.get("contracts", [])

    # Save new contract
    output = result
    with open(NEW_CONTRACT, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Compare with old
    new_counts = count_warnings(contracts)
    new_total = sum(new_counts.values())

    old_counts = {}
    old_total = 0
    if OLD_CONTRACT.exists():
        with open(OLD_CONTRACT, encoding="utf-8") as f:
            old_data = json.load(f)
        old_counts = count_warnings(old_data.get("contracts", []))
        old_total = sum(old_counts.values())

    print("=" * 60)
    print("QUALITY CONTRACT COMPARISON")
    print("=" * 60)
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

    # Clean scenes
    clean_before = sum(1 for c in old_data.get("contracts", []) if not c.get("warnings"))
    clean_after = sum(1 for c in contracts if not c.get("warnings"))
    print(f"\nClean scenes (0 warnings):     {clean_before} -> {clean_after}")
    print(f"Saved to: {NEW_CONTRACT}")


if __name__ == "__main__":
    main()
