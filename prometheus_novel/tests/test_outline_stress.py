"""
Outline Stress Test (Confidence Ladder - Test A)

Generates the full outline for The Glass Registry 3 times and measures
scene name deduplication quality across runs. This is the cheapest test
in the ladder -- it reveals recycling before you invest in prose.

Pass threshold:
  - Exact duplicates <= 1 per run (strict) or <= 2 (lenient)
  - Near-duplicates (Jaccard >= 0.6) <= 2 per run
  - Dedup guard fires <= 3 times per run (i.e., model self-corrects)

Usage:
    python -m tests.test_outline_stress
    python -m tests.test_outline_stress --runs 1   (single run, faster)
"""

import sys
import asyncio
import logging
import argparse
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from prometheus_lib.llm.clients import OllamaClient
from stages.pipeline import PipelineOrchestrator
from stages.quality_meters import scene_name_dedup_meter, print_meter_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("outline_stress")

PLANNING_STAGES = [
    "high_concept",
    "world_building",
    "beat_sheet",
    "emotional_architecture",
    "character_profiles",
    "motif_embedding",
    "master_outline",
    "trope_integration",
]


async def run_single(run_id: int) -> dict:
    """Run full planning + outline and return dedup metrics."""
    project_path = ROOT / "data" / "projects" / "the-glass-registry"
    if not (project_path / "config.yaml").exists():
        logger.error(f"Glass Registry project not found at {project_path}")
        return {"error": "Project not found"}

    ollama = OllamaClient("qwen2.5:14b")
    pipeline = PipelineOrchestrator(
        project_path=project_path,
        llm_client=ollama,
        llm_clients={"gpt": ollama, "claude": ollama, "gemini": ollama},
    )

    await pipeline.initialize()

    print(f"\n{'=' * 60}")
    print(f"  RUN {run_id}: Planning + Outline Generation")
    print(f"{'=' * 60}")

    t0 = time.time()
    total_tokens = 0
    failed_stages = []

    for stage in PLANNING_STAGES:
        st = time.time()
        try:
            handler = getattr(pipeline, f"_stage_{stage}")
            result = await handler()
            elapsed = time.time() - st

            if isinstance(result, tuple) and len(result) == 2:
                _, tokens = result
            else:
                tokens = 0
            total_tokens += tokens

            status = "OK"
            print(f"    {stage:30s} {status}  {elapsed:6.1f}s  {tokens:5d} tok")

        except Exception as e:
            elapsed = time.time() - st
            failed_stages.append(stage)
            print(f"    {stage:30s} FAILED  {elapsed:6.1f}s  {e}")
            if stage in ("high_concept", "master_outline"):
                return {
                    "error": f"Critical stage {stage} failed: {e}",
                    "elapsed": time.time() - t0,
                    "tokens": total_tokens,
                }

    total_elapsed = time.time() - t0

    # Run scene name dedup meter
    outline = pipeline.state.master_outline or []
    dedup = scene_name_dedup_meter(outline)

    # Collect all scene names for display
    all_names = []
    for ch in outline:
        if not isinstance(ch, dict):
            continue
        ch_num = ch.get("chapter", "?")
        for sc in ch.get("scenes", []):
            if isinstance(sc, dict):
                sc_num = sc.get("scene", sc.get("scene_number", "?"))
                name = sc.get("scene_name", "?")
                all_names.append(f"  Ch{ch_num}-S{sc_num}: {name}")

    # Summary
    total_chapters = len([c for c in outline if isinstance(c, dict)])
    total_scenes = sum(
        len(c.get("scenes", []))
        for c in outline if isinstance(c, dict)
    )

    result = {
        "run_id": run_id,
        "elapsed": round(total_elapsed, 1),
        "tokens": total_tokens,
        "chapters": total_chapters,
        "scenes": total_scenes,
        "failed_stages": failed_stages,
        "dedup": dedup,
        "all_names": all_names,
    }

    print(f"\n  Run {run_id} complete: {total_elapsed:.1f}s, {total_tokens} tokens")
    print(f"  Outline: {total_chapters} chapters, {total_scenes} scenes")
    print(f"  Dedup: {dedup['duplicate_count']} exact, {dedup['near_duplicate_count']} near")
    print(f"  Dedup pass: {'YES' if dedup['pass'] else 'NO'}")

    return result


async def run_outline_stress(num_runs: int = 3):
    print("\n" + "=" * 60)
    print("OUTLINE STRESS TEST -- The Glass Registry")
    print(f"Model: qwen2.5:14b (Q4_K_M, 32k context)")
    print(f"Runs: {num_runs}")
    print("=" * 60)

    results = []
    for i in range(1, num_runs + 1):
        result = await run_single(i)
        results.append(result)

    # -- Cross-run analysis --
    print("\n" + "=" * 60)
    print("CROSS-RUN ANALYSIS")
    print("=" * 60)

    for r in results:
        if "error" in r:
            print(f"\n  Run {r.get('run_id', '?')}: ERROR - {r['error']}")
            continue

        run_id = r["run_id"]
        dedup = r["dedup"]
        print(f"\n  Run {run_id}: {r['chapters']}ch/{r['scenes']}sc, "
              f"{r['elapsed']}s, {r['tokens']} tok")
        print(f"    Exact duplicates:  {dedup['duplicate_count']}")
        print(f"    Near duplicates:   {dedup['near_duplicate_count']}")
        print(f"    Unique/Total:      {dedup['unique_names']}/{dedup['total_names']}")

        if dedup["exact_duplicates"]:
            print(f"    Exact dupes:")
            for name, count, locs in dedup["exact_duplicates"]:
                print(f"      \"{name}\" x{count} at {', '.join(locs)}")

        if dedup["near_duplicates"]:
            print(f"    Near dupes:")
            for a, b, jac, loc_a, loc_b in dedup["near_duplicates"][:5]:
                print(f"      \"{a}\" ~ \"{b}\" (j={jac}) [{loc_a} vs {loc_b}]")

    # -- Go/No-Go verdict --
    print(f"\n{'=' * 60}")
    print("VERDICT")
    print(f"{'=' * 60}")

    valid_runs = [r for r in results if "error" not in r]
    if not valid_runs:
        print("\n  All runs failed. Cannot evaluate.")
        return

    avg_exact = sum(r["dedup"]["duplicate_count"] for r in valid_runs) / len(valid_runs)
    avg_near = sum(r["dedup"]["near_duplicate_count"] for r in valid_runs) / len(valid_runs)
    all_pass = all(r["dedup"]["pass"] for r in valid_runs)
    worst_exact = max(r["dedup"]["duplicate_count"] for r in valid_runs)
    worst_near = max(r["dedup"]["near_duplicate_count"] for r in valid_runs)

    print(f"\n  Avg exact duplicates:  {avg_exact:.1f}")
    print(f"  Avg near duplicates:   {avg_near:.1f}")
    print(f"  Worst exact:           {worst_exact}")
    print(f"  Worst near:            {worst_near}")
    print(f"  All runs pass dedup:   {'YES' if all_pass else 'NO'}")

    # Go/No-Go
    if worst_exact <= 1 and worst_near <= 2:
        verdict = "GO (strict)"
    elif worst_exact <= 2 and worst_near <= 3:
        verdict = "GO (lenient)"
    elif avg_exact <= 2:
        verdict = "MARGINAL -- dedup guard helping but model still recycling"
    else:
        verdict = "NO-GO -- outline repeats are systemic"

    print(f"\n  OUTLINE STRESS TEST: {verdict}")

    # Show all scene names from last valid run
    last_valid = valid_runs[-1]
    print(f"\n  Scene names (Run {last_valid['run_id']}):")
    for name_line in last_valid.get("all_names", []):
        print(f"    {name_line}")

    print(f"\n{'=' * 60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Outline stress test")
    parser.add_argument("--runs", type=int, default=1,
                        help="Number of runs (default: 1 for speed)")
    args = parser.parse_args()
    asyncio.run(run_outline_stress(args.runs))
