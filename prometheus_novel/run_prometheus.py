# Main orchestration script for novel generation pipeline
import asyncio
import os
from pathlib import Path
import logging

# Setup logging first
from prometheus_lib.utils.logging_config import setup_logging
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import core components
from prometheus_lib.models.novel_state import PrometheusState
from prometheus_lib.models.outline_schemas import NovelOutline # For initial outline loading
from prometheus_lib.llm.model_router import LLMModelRouter
from prometheus_lib.llm.cost_tracker import CostTracker
from prometheus_lib.memory.vector_store import VectorStore
from prometheus_lib.memory.state_manager import StateManager
from prometheus_lib.memory.cleanup import MemoryCleanup
from prometheus_lib.critics.continuity_auditor import ContinuityAuditor
from prometheus_lib.critics.style_critic import StyleCritic
from prometheus_lib.critics.output_validator import OutputValidator
from prometheus_lib.utils.error_handling import handle_exception, PrometheusError, BudgetExceededError
from prometheus_lib.utils.metrics import get_metrics_snapshot, reset_metrics, gauge, increment_counter

# Import config loader
from configs.env_config import load_config

# --- Dependency Injection Setup ---
class AppServices:
    def __init__(self, config):
        self.config = config
        self.cost_tracker = CostTracker()
        self.llm_router = LLMModelRouter(config, self.cost_tracker)
        self.vector_store = VectorStore()
        self.state_manager = StateManager(self.vector_store, self.llm_router)
        self.memory_cleanup = MemoryCleanup(self.vector_store) # Pass vector store instance
        self.continuity_auditor = ContinuityAuditor(self.llm_router, self.state_manager)
        self.style_critic = StyleCritic(self.llm_router)
        self.output_validator = OutputValidator(self.llm_router)

    async def initialize(self):
        '''Initializes asynchronous services.'''
        await self.vector_store.initialize_vector_db(Path(f"data/{self.config.project_name}/memory/vector_db"))
        # Add other async initializations here

# --- Main Execution Function ---
async def main():
    logger.info("Starting PROMETHEUS-NOVEL 1.0 generation pipeline.")

    # 1. Load Configuration
    try:
        config = load_config(os.getenv("PROMETHEUS_ENV"))
        gauge("budget_usd_configured", config.budget_usd)
    except Exception as e:
        handle_exception(e)
        return

    # 2. Initialize Services
    services = AppServices(config)
    try:
        await services.initialize()
    except Exception as e:
        handle_exception(e)
        return

    # 3. Load or Initialize Novel State
    project_data_path = Path(f"data/{config.project_name}/state_snapshots")
    latest_state_file = project_data_path / "latest_state.json" # Or find the latest versioned file
    
    initial_state = await PrometheusState.load_from_disk(latest_state_file)
    if initial_state is None:
        logger.info("No existing state found. Initializing new novel outline.")
        # Placeholder: In a real app, you'd load the initial outline from a file or user input
        # For now, create a dummy outline or load from outline_schemas example
        from prometheus_lib.models.outline_schemas import NovelOutline, NovelMetadata
        initial_outline = NovelOutline(metadata=NovelMetadata(project_name=config.project_name, title="The Empathy Clause", genre="Sci-Fi"))
        initial_state = PrometheusState(novel_outline=initial_outline)
        await services.state_manager.update_ltm(initial_outline) # Initialize LTM

    # Update initial state with current services (e.g., LLM router, state manager) if needed
    # This is where LangGraph's state management and node arguments come into play.
    # For a simple sequential run:
    current_state = initial_state
    
    # 4. Execute Stages (Conceptual Sequential Run for Scaffold)
    logger.info("Starting conceptual sequential stage execution...")
    try:
        # Example: Run high concept stage
        # current_state = await high_concept_node(current_state, services.llm_router, services.state_manager)
        # logger.info("High concept stage completed.")

        # Example: Simulate writing a scene
        # To run write_scene_node, current_state needs an active_plot_point_id
        # For testing, manually set one:
        if not current_state.active_plot_point_id and current_state.novel_outline.plot_points:
            current_state.active_plot_point_id = current_state.novel_outline.plot_points[0].id
            logger.info(f"Set active plot point to: {current_state.active_plot_point_id}")
        
        # current_state = await write_scene_node(current_state, services.llm_router, services.state_manager)
        # logger.info("Write scene stage completed.")

        # Simulate a loop for a few scenes/chapters
        for chapter in range(current_state.current_chapter, current_state.current_chapter + 2): # Generate 2 chapters
            current_state.current_chapter = chapter
            for scene in range(current_state.current_scene, current_state.current_scene + 3): # Generate 3 scenes per chapter
                current_state.current_scene = scene
                logger.info(f"Generating Chapter {chapter}, Scene {scene}...")
                # In a real LangGraph, this would be handled by node execution
                # For scaffold, simulate direct calls or a simplified loop
                
                # Simulate LLM call and state update
                # This is where you would call your actual stage functions
                # For example:
                # current_state = await write_scene_node(current_state, services.llm_router, services.state_manager)
                
                # Simulate cost and state update for demonstration
                await asyncio.sleep(0.5) # Simulate work
                services.cost_tracker.add_cost(f"stage_write_scene_{chapter}_{scene}", "gpt-4o-mini", 500, 1000, current_state)
                current_state.generated_novel_text.setdefault(chapter, {})[scene] = f"Content for Chapter {chapter}, Scene {scene}."
                await current_state.persist_to_disk(project_data_path / "latest_state.json")
                
                # Simulate memory cleanup periodically
                if scene % 2 == 0: # Every 2 scenes
                    await services.memory_cleanup.prune_old_stm(current_state, retention_policy=1)

        logger.info("Conceptual novel generation finished.")

    except BudgetExceededError as e:
        logger.critical(f"Generation halted: {e}")
    except PrometheusError as e:
        logger.error(f"Pipeline error: {e}")
        handle_exception(e) # Centralized error handling
    except Exception as e:
        logger.exception("An unexpected critical error occurred during pipeline execution.")
        handle_exception(e)

    # 5. Final Metrics and Cleanup
    final_metrics = get_metrics_snapshot()
    logger.info(f"Final Metrics:\n{json.dumps(final_metrics, indent=2)}")
    reset_metrics()

    # Optional: Archive data after completion
    # await services.memory_cleanup.archive_novel_data(config.project_name, Path("data"))

if __name__ == "__main__":
    import json # Import json here for main
    asyncio.run(main())
