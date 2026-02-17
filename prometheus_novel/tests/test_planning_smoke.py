"""
Planning Smoke Test -- runs the Glass Registry through all 8 planning stages
and reports JSON stability, drift warnings, and output cohesion.

Usage:
    python -m tests.test_planning_smoke
"""

import sys
import asyncio
import logging
import json
import time
from pathlib import Path

import pytest

# Fix Windows cp1252 encoding issues with Unicode scene content
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from prometheus_lib.llm.clients import OllamaClient
from stages.pipeline import PipelineOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("planning_smoke")

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


def truncate(obj, max_len=200):
    """Truncate object representation for display."""
    s = str(obj)
    return s[:max_len] + "..." if len(s) > max_len else s


def check_json_structure(name, obj, expected_type):
    """Validate JSON output structure and return issues."""
    issues = []
    if obj is None:
        issues.append(f"{name}: output is None")
        return issues
    if not isinstance(obj, expected_type):
        issues.append(f"{name}: expected {expected_type.__name__}, got {type(obj).__name__}")
        return issues
    if isinstance(obj, list) and len(obj) == 0:
        issues.append(f"{name}: empty list")
    if isinstance(obj, dict) and len(obj) == 0:
        issues.append(f"{name}: empty dict")
    return issues


async def run_planning_smoke(project_path: Path = None, model: str = "qwen2.5:14b"):
    """Run planning stages smoke test. project_path defaults to the-glass-registry."""
    if project_path is None:
        project_path = ROOT / "data" / "projects" / "the-glass-registry"
    if not (project_path / "config.yaml").exists():
        logger.error(f"Project not found at {project_path}")
        return

    ollama = OllamaClient(model)
    pipeline = PipelineOrchestrator(
        project_path=project_path,
        llm_client=ollama,
        llm_clients={"gpt": ollama, "claude": ollama, "gemini": ollama},
    )

    await pipeline.initialize()

    results = {}
    total_tokens = 0
    total_time = 0.0

    print("\n" + "=" * 70)
    print("PLANNING SMOKE TEST -- The Glass Registry")
    print("Model: qwen2.5:14b (Q4_K_M, 32k context)")
    print("=" * 70)

    for stage in PLANNING_STAGES:
        print(f"\n{'-' * 70}")
        print(f"STAGE: {stage}")
        print(f"{'-' * 70}")

        t0 = time.time()
        try:
            handler = getattr(pipeline, f"_stage_{stage}")
            result = await handler()
            elapsed = time.time() - t0

            if isinstance(result, tuple) and len(result) == 2:
                output, tokens = result
            else:
                output, tokens = result, 0

            total_tokens += tokens
            total_time += elapsed

            results[stage] = {
                "status": "OK",
                "tokens": tokens,
                "time": round(elapsed, 1),
                "output_type": type(output).__name__,
            }

            print(f"  Status:  OK ({elapsed:.1f}s, {tokens} tokens)")
            print(f"  Type:    {type(output).__name__}")
            print(f"  Preview: {truncate(output)}")

        except Exception as e:
            elapsed = time.time() - t0
            total_time += elapsed
            results[stage] = {"status": "FAILED", "error": str(e), "time": round(elapsed, 1)}
            print(f"  Status:  FAILED ({elapsed:.1f}s)")
            print(f"  Error:   {e}")
            # Don't break -- try remaining stages to see cascade effects

    # -- Post-run analysis ---------------------------------------------
    print("\n" + "=" * 70)
    print("POST-RUN ANALYSIS")
    print("=" * 70)

    state = pipeline.state
    json_issues = []

    # 1. High concept quality
    print(f"\n--- High Concept ---")
    if state.high_concept:
        print(f"  Text: {state.high_concept}")
        if state.high_concept_candidates:
            for c in state.high_concept_candidates:
                print(f"  Candidate ({c['angle']}): score={c['score']}, issues={c.get('issues', {})}")
        if state.high_concept_fingerprint:
            fp = state.high_concept_fingerprint
            print(f"  Fingerprint: {fp.get('keywords', [])[:10]}")
            print(f"  Entities: {fp.get('entities', [])}")

    # 2. World bible JSON
    print(f"\n--- World Bible ---")
    json_issues += check_json_structure("world_bible", state.world_bible, dict)
    if state.world_bible:
        keys = list(state.world_bible.keys())
        print(f"  Keys: {keys}")
        for k in ["setting", "rules", "locations"]:
            if k in state.world_bible:
                print(f"  {k}: {truncate(state.world_bible[k], 100)}")

    # 3. Beat sheet JSON
    print(f"\n--- Beat Sheet ---")
    json_issues += check_json_structure("beat_sheet", state.beat_sheet, list)
    if state.beat_sheet:
        print(f"  Beats: {len(state.beat_sheet)}")
        for b in state.beat_sheet[:3]:
            name = b.get("name", b.get("beat_name", "?"))
            pct = b.get("percentage", "?")
            print(f"    {name} ({pct}%): {truncate(b.get('scene_description', b.get('description', '')), 80)}")
        if len(state.beat_sheet) > 3:
            print(f"    ... and {len(state.beat_sheet) - 3} more beats")

    # 4. Emotional architecture
    print(f"\n--- Emotional Architecture ---")
    json_issues += check_json_structure("emotional_arc", state.emotional_arc, dict)
    if state.emotional_arc:
        keys = list(state.emotional_arc.keys())
        print(f"  Keys: {keys}")
        peaks = state.emotional_arc.get("peaks", [])
        troughs = state.emotional_arc.get("troughs", [])
        print(f"  Peaks: {len(peaks)}, Troughs: {len(troughs)}")

    # 5. Characters
    print(f"\n--- Characters ---")
    json_issues += check_json_structure("characters", state.characters, list)
    if state.characters:
        print(f"  Count: {len(state.characters)}")
        for ch in state.characters:
            name = ch.get("name", "?")
            role = ch.get("role", "?")
            voice = truncate(ch.get("voice", ch.get("speech_patterns", "")), 60)
            print(f"    {name} ({role}): voice={voice}")

    # 6. Motif map
    print(f"\n--- Motif Map ---")
    json_issues += check_json_structure("motif_map", state.motif_map, dict)
    if state.motif_map:
        motifs = state.motif_map.get("motifs", state.motif_map)
        if isinstance(motifs, list):
            print(f"  Motifs: {len(motifs)}")
            for m in motifs[:4]:
                if isinstance(m, dict):
                    print(f"    {m.get('name', '?')}: {truncate(m.get('meaning', ''), 60)}")
        elif isinstance(motifs, dict):
            print(f"  Keys: {list(motifs.keys())[:6]}")

    # 7. Master outline
    print(f"\n--- Master Outline ---")
    json_issues += check_json_structure("master_outline", state.master_outline, list)
    if state.master_outline:
        print(f"  Chapters: {len(state.master_outline)}")
        total_scenes = 0
        for ch in state.master_outline:
            scenes = ch.get("scenes", [])
            total_scenes += len(scenes)
            ch_num = ch.get("chapter", ch.get("chapter_number", "?"))
            print(f"    Ch {ch_num}: {len(scenes)} scenes")
            for s in scenes[:2]:
                sname = s.get("scene_name", s.get("scene", "?"))
                purpose = truncate(s.get("purpose", ""), 50)
                diff = s.get("differentiator", "MISSING")
                print(f"      - {sname}: {purpose} [diff: {truncate(diff, 40)}]")
            if len(scenes) > 2:
                print(f"      ... +{len(scenes) - 2} more scenes")
        print(f"  Total scenes: {total_scenes}")

    # -- Summary -------------------------------------------------------
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")

    passed = sum(1 for r in results.values() if r["status"] == "OK")
    failed = sum(1 for r in results.values() if r["status"] == "FAILED")
    print(f"\n  Stages:     {passed}/{len(PLANNING_STAGES)} passed, {failed} failed")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Tokens:     {total_tokens}")

    if json_issues:
        print(f"\n  JSON Issues ({len(json_issues)}):")
        for issue in json_issues:
            print(f"    - {issue}")
    else:
        print(f"\n  JSON Issues: None")

    # Check for drift warnings in the log
    print(f"\n  Stage Results:")
    for stage, info in results.items():
        status = info["status"]
        t = info.get("time", 0)
        tok = info.get("tokens", 0)
        err = info.get("error", "")
        line = f"    {stage:25s} {status:8s} {t:6.1f}s  {tok:5d} tok"
        if err:
            line += f"  ERROR: {err[:50]}"
        print(line)

    print(f"\n{'=' * 70}")

    failed_stages = [s for s, info in results.items() if info["status"] == "FAILED"]
    return {
        "completed_stages": len([s for s, info in results.items() if info["status"] == "COMPLETED"]),
        "failed_stages": failed_stages,
        "json_issues": json_issues,
    }


# Pytest entry point (run with: pytest -m smoke)
@pytest.mark.smoke
@pytest.mark.slow
def test_planning_smoke(smoke_project):
    """Pytest wrapper for planning smoke test. Uses temp project from fixtures."""
    import asyncio
    result = asyncio.run(run_planning_smoke(project_path=smoke_project, model="qwen2.5:7b"))
    assert result["completed_stages"] >= 6, f"Only {result['completed_stages']} stages completed"
    assert len(result["failed_stages"]) == 0, f"Stages failed: {result['failed_stages']}"
    assert len(result["json_issues"]) == 0, f"JSON issues: {result['json_issues']}"


if __name__ == "__main__":
    asyncio.run(run_planning_smoke())
