"""Overnight runner: runs full novel generation pipeline for a given project."""
import asyncio
import sys
import os
import logging
import time
from pathlib import Path
from datetime import datetime

# Get project name from args
project_name = sys.argv[1] if len(sys.argv) > 1 else "seat-27b"

# Setup logging to file
log_file = Path(__file__).parent / f"{project_name}_run.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(str(log_file), mode='w', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("overnight")

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def run_novel():
    """Run the full Burning Vows pipeline and export."""
    import yaml
    from prometheus_novel.stages.pipeline import PipelineOrchestrator
    from prometheus_novel.prometheus_lib.llm.clients import get_client

    project_path = project_root / "prometheus_novel" / "data" / "projects" / project_name

    # Load config
    config_file = project_path / "config.yaml"
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f) or {}

    model_defaults = config.get("model_defaults", {})
    api_model = model_defaults.get("api_model", "qwen2.5:14b")
    structure_gate_model = model_defaults.get("structure_gate_model")

    logger.info(f"{'='*60}")
    logger.info(f"OVERNIGHT NOVEL GENERATION")
    logger.info(f"Title: {config.get('title', 'Untitled')}")
    logger.info(f"Target: {config.get('target_length', 'standard (60k)')}")
    logger.info(f"Model: {api_model}")
    if structure_gate_model:
        logger.info(f"Structure gate: {structure_gate_model}")
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'='*60}")

    # Create client - same model for all stages (local Ollama)
    default_client = get_client(api_model)
    llm_clients = {
        "gpt": default_client,
        "claude": default_client,
        "gemini": default_client,
    }
    if structure_gate_model:
        llm_clients["structure"] = get_client(structure_gate_model)

    # Create orchestrator
    orchestrator = PipelineOrchestrator(
        project_path,
        llm_client=default_client,
        llm_clients=llm_clients
    )

    # Register progress callbacks
    stage_start_times = {}

    async def on_stage_start(stage_name, index):
        stage_start_times[stage_name] = time.time()
        logger.info(f">>> STAGE {index+1}: {stage_name} started")

    async def on_stage_complete(stage_name, result):
        elapsed = time.time() - stage_start_times.get(stage_name, time.time())
        status = result.status.value if hasattr(result, 'status') else 'unknown'
        tokens = result.tokens_used if hasattr(result, 'tokens_used') else 0
        logger.info(f"<<< STAGE {stage_name}: {status} ({elapsed:.1f}s, {tokens} tokens)")
        if hasattr(result, 'error') and result.error:
            logger.error(f"    ERROR: {result.error}")

    async def on_pipeline_complete(state):
        logger.info(f"{'='*60}")
        logger.info(f"PIPELINE COMPLETE!")
        logger.info(f"Total tokens: {state.total_tokens}")
        logger.info(f"Total cost: ${state.total_cost_usd:.4f}")
        logger.info(f"Scenes generated: {len(state.scenes or [])}")
        total_words = sum(
            len(s.get('content', '').split())
            for s in (state.scenes or [])
            if isinstance(s, dict)
        )
        logger.info(f"Total words: {total_words}")
        logger.info(f"{'='*60}")

    orchestrator.on("on_stage_start", on_stage_start)
    orchestrator.on("on_stage_complete", on_stage_complete)
    orchestrator.on("on_pipeline_complete", on_pipeline_complete)

    # Run the full pipeline
    start_time = time.time()
    try:
        final_state = await orchestrator.run()
        elapsed_total = time.time() - start_time
        logger.info(f"Pipeline finished in {elapsed_total/3600:.1f} hours ({elapsed_total/60:.0f} minutes)")

        # Export to Word document
        logger.info("Exporting to .docx...")
        from prometheus_novel.export.docx_exporter import KDPExporter
        exporter = KDPExporter(project_path)
        output_path = exporter.export()
        logger.info(f"Novel exported to: {output_path}")

        # Update config status
        config["status"] = "completed"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

        logger.info(f"\nSUCCESS! Check: {output_path}")

    except Exception as e:
        elapsed_total = time.time() - start_time
        logger.error(f"PIPELINE FAILED after {elapsed_total/60:.0f} minutes: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    print(f"Starting overnight generation... Logging to: {log_file}")
    print(f"You can check progress with: tail -f overnight_run.log")
    print(f"Or: type overnight_run.log  (on Windows)")
    asyncio.run(run_novel())
