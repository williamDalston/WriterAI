"""Full book production runner for Burning Vows.

Runs the ENTIRE pipeline (all 27 stages) using the pipeline's own run() method
which handles state saving, checkpoint resume, parallel groups, circuit breakers,
and all defense infrastructure.

Usage:
    python -u -m tests.run_full_production
    python -u -m tests.run_full_production --resume   # Resume from checkpoint
"""

import sys
import asyncio
import logging
import time
import argparse
from pathlib import Path

# Fix Windows cp1252 encoding issues
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
logger = logging.getLogger("full_production")

MODEL = "qwen2.5:14b"
PROJECT = "burning-vows"


async def run_production(resume: bool = False):
    project_path = ROOT / "data" / "projects" / PROJECT
    if not (project_path / "config.yaml").exists():
        logger.error(f"Project not found at {project_path}")
        return

    print(f"\n{'=' * 70}")
    print(f"FULL BOOK PRODUCTION — {PROJECT}")
    print(f"Model: {MODEL}")
    print(f"Resume: {resume}")
    print(f"{'=' * 70}\n", flush=True)

    ollama = OllamaClient(MODEL)
    pipeline = PipelineOrchestrator(
        project_path=project_path,
        llm_client=ollama,
        llm_clients={"gpt": ollama, "claude": ollama, "gemini": ollama},
    )

    t0 = time.time()

    try:
        result = await pipeline.run(resume=resume)
        elapsed = time.time() - t0
        print(f"\n{'=' * 70}")
        print(f"PRODUCTION COMPLETE")
        print(f"Time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
        print(f"Completed stages: {pipeline.state.completed_stages}")
        print(f"Scenes: {len(pipeline.state.scenes)}")
        if hasattr(pipeline.state, 'total_cost_usd'):
            print(f"Total cost: ${pipeline.state.total_cost_usd:.4f}")
        print(f"{'=' * 70}", flush=True)
    except Exception as e:
        elapsed = time.time() - t0
        print(f"\n{'=' * 70}")
        print(f"PRODUCTION FAILED after {elapsed:.1f}s ({elapsed/60:.1f} min)")
        print(f"Error: {e}")
        if pipeline.state:
            print(f"Completed stages: {pipeline.state.completed_stages}")
            print(f"Scenes: {len(pipeline.state.scenes)}")
        print(f"{'=' * 70}", flush=True)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    args = parser.parse_args()
    asyncio.run(run_production(resume=args.resume))
