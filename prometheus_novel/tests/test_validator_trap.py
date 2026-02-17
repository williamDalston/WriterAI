"""
Validator Trap Test — runs the bad seed through high_concept stage
and verifies the defense layer catches it.

Usage:
    python -m tests.test_validator_trap
"""

import sys
import asyncio
import logging
from pathlib import Path

# Project root
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from prometheus_lib.llm.clients import OllamaClient
from stages.pipeline import PipelineOrchestrator

# ── Logging ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("validator_trap")


async def run_trap():
    project_path = ROOT / "data" / "projects" / "the-last-truth"
    if not (project_path / "config.yaml").exists():
        logger.error(f"Bad seed project not found at {project_path}")
        logger.error("Run: python -m interfaces.cli.seed --file data/seeds/bad_seed_validator_trap.txt --no-expand")
        return

    # Wire up Ollama client as fallback for all stages
    ollama = OllamaClient("qwen2.5:14b")

    pipeline = PipelineOrchestrator(
        project_path=project_path,
        llm_client=ollama,
        llm_clients={
            "gpt": ollama,
            "claude": ollama,
            "gemini": ollama,
        },
    )

    # Initialize state (loads config, validates)
    await pipeline.initialize()

    logger.info("=" * 70)
    logger.info("RUNNING HIGH_CONCEPT STAGE WITH BAD SEED (VALIDATOR TRAP)")
    logger.info("=" * 70)

    # Run just high_concept
    try:
        result = await pipeline._stage_high_concept()
        high_concept_text, tokens_used = result
    except RuntimeError as e:
        logger.error(f"Stage raised RuntimeError (expected for total failure): {e}")
        return

    # ── Report ────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("VALIDATOR TRAP RESULTS")
    print("=" * 70)

    # All candidates
    candidates = pipeline.state.high_concept_candidates or []
    print(f"\nCandidates generated: {len(candidates)}")
    for i, c in enumerate(candidates, 1):
        print(f"\n--- Candidate {i} ({c['angle']}) ---")
        print(f"  Score:  {c['score']}")
        print(f"  Pass:   {c.get('pass', 'N/A')}")
        print(f"  Issues: {c['issues']}")
        text_preview = c['text'][:120] + "..." if len(c['text']) > 120 else c['text']
        print(f"  Text:   {text_preview}")

    # Selected concept
    print(f"\n{'=' * 70}")
    print("SELECTED HIGH CONCEPT:")
    print(f"  {pipeline.state.high_concept}")

    # Fingerprint
    fp = pipeline.state.high_concept_fingerprint
    if fp:
        print(f"\nFINGERPRINT:")
        print(f"  Hash:     {fp.get('hash', 'N/A')}")
        print(f"  Keywords: {fp.get('keywords', [])}")
        print(f"  Entities: {fp.get('entities', [])}")

    # Verdict
    print(f"\n{'=' * 70}")
    passing = [c for c in candidates if c.get("pass") or c.get("score", 0) >= 50]
    all_scores = [c["score"] for c in candidates]
    best_score = max(all_scores) if all_scores else 0

    if not passing and best_score < 50:
        print("VERDICT: DEFENSE HELD — All candidates failed validation (expected)")
        print(f"  Best score: {best_score} (threshold: 50)")
        print("  The fallback path selected the least-bad candidate.")
    elif passing:
        print(f"VERDICT: DEFENSE BREACHED — {len(passing)} candidate(s) passed!")
        print("  This means the validator needs tightening.")
        for c in passing:
            print(f"    {c['angle']}: score={c['score']}, issues={c['issues']}")
    else:
        print(f"VERDICT: AMBIGUOUS — best_score={best_score}")

    print(f"\nTokens used: {tokens_used}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_trap())
