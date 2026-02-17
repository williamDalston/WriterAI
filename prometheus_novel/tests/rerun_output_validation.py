"""Re-run just the output_validation stage from saved pipeline state.

Usage:
    cd prometheus_novel
    python -u -m tests.rerun_output_validation
"""
import sys
import asyncio
import logging
import json
import traceback
from pathlib import Path

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
logger = logging.getLogger("rerun_ov")

MODEL = "qwen2.5:14b"


async def main():
    project_path = ROOT / "data" / "projects" / "burning-vows"
    state_file = project_path / "pipeline_state.json"

    if not state_file.exists():
        print(f"ERROR: No saved state at {state_file}")
        return

    ollama = OllamaClient(MODEL)
    pipeline = PipelineOrchestrator(
        project_path=project_path,
        llm_client=ollama,
        llm_clients={"gpt": ollama, "claude": ollama, "gemini": ollama},
    )
    await pipeline.initialize()

    # Load saved state — PipelineState is defined inside pipeline.py
    from stages.pipeline import PipelineState
    loaded = PipelineState.load(project_path)
    if loaded is None:
        print("ERROR: Failed to load pipeline state")
        return

    pipeline.state = loaded
    pipeline.state.project_path = project_path

    print(f"Loaded state: {len(pipeline.state.scenes)} scenes, "
          f"{len(pipeline.state.completed_stages)} stages completed")
    print(f"Completed: {pipeline.state.completed_stages}")

    # Run just output_validation
    print("\n--- Running output_validation ---")
    try:
        result = await pipeline._run_stage("output_validation")
        print(f"\nResult: status={result.status}, tokens={result.tokens_used}")
        if result.error:
            print(f"Error: {result.error}")
        if result.output and isinstance(result.output, dict):
            print(f"Output file: {result.output.get('output_file', 'N/A')}")
            print(f"Total words: {result.output.get('total_words', 'N/A')}")
            print(f"Quality score: {result.output.get('quality_score', 'N/A')}")
            print(f"Passed: {result.output.get('passed', 'N/A')}")
            print(f"Word percentage: {result.output.get('word_percentage', 'N/A')}%")
    except Exception as e:
        print(f"\nFAILED: {e}")
        traceback.print_exc()

    # Check if output files were generated
    output_dir = project_path / "output"
    md_file = output_dir / "burning-vows.md"
    report_file = output_dir / "run_report.json"

    print(f"\nOutput files:")
    print(f"  Markdown: {'EXISTS' if md_file.exists() else 'MISSING'} ({md_file})")
    print(f"  Report:   {'EXISTS' if report_file.exists() else 'MISSING'} ({report_file})")

    if md_file.exists():
        content = md_file.read_text(encoding='utf-8')
        words = len(content.split())
        print(f"  Markdown words: ~{words}")

    if report_file.exists():
        with open(report_file, 'r', encoding='utf-8') as f:
            report = json.load(f)
        print(f"  Report keys: {sorted(report.keys())}")


if __name__ == "__main__":
    asyncio.run(main())
