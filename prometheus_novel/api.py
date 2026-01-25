# FastAPI or Flask entrypoint for external interaction
import asyncio
from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

# Setup logging for the API
from prometheus_lib.utils.logging_config import setup_logging
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import core components needed by the API
from prometheus_lib.models.novel_state import PrometheusState
from prometheus_lib.models.outline_schemas import NovelOutline
from prometheus_lib.llm.model_router import LLMModelRouter
from prometheus_lib.llm.cost_tracker import CostTracker
from prometheus_lib.memory.vector_store import VectorStore
from prometheus_lib.memory.state_manager import StateManager
from prometheus_lib.utils.error_handling import PrometheusError, BudgetExceededError, handle_exception
from prometheus_lib.utils.metrics import get_metrics_snapshot, gauge, increment_counter, observe_latency

# Import config loader
from configs.env_config import load_config

# --- API Specific Models ---
class GenerateRequest(BaseModel):
    novel_id: str
    stage_name: str
    prompt_override: Optional[str] = None
    # Add other parameters needed for specific stage generation

class NovelStateResponse(BaseModel):
    novel_id: str
    current_chapter: int
    current_scene: int
    total_cost_usd: float
    # Add more fields as needed for API response

class HealthCheckResponse(BaseModel):
    status: str = "ok"
    uptime_seconds: float
    metrics: Dict[str, Any]

# --- FastAPI App Initialization ---
app = FastAPI(
    title="PROMETHEUS-NOVEL API",
    description="API for agentic novel generation pipeline.",
    version="1.0.0",
)

# --- Global Services (initialized once) ---
# In a real production setup, these might be managed by a dependency injection container
# or loaded more robustly. For scaffolding, a simple global setup.
_app_services: Optional[Any] = None # Will hold AppServices instance

async def get_app_services() -> Any:
    global _app_services
    if _app_services is None:
        logger.info("Initializing API services...")
        try:
            config = load_config(os.getenv("PROMETHEUS_ENV"))
            _app_services = AppServices(config) # Use the AppServices class from run_prometheus.py
            await _app_services.initialize()
            logger.info("API services initialized successfully.")
        except Exception as e:
            logger.critical(f"Failed to initialize API services: {e}", exc_info=True)
            raise RuntimeError(f"API startup failed: {e}")
    return _app_services

# --- API Endpoints ---

@app.on_event("startup")
async def startup_event():
    await get_app_services() # Ensure services are initialized on startup

@app.get("/health", response_model=HealthCheckResponse, summary="Health Check")
async def health_check():
    '''Returns the health status of the API and current metrics.'''
    start_time = app.state.start_time if hasattr(app.state, 'start_time') else time.time()
    uptime = time.time() - start_time
    metrics_snapshot = get_metrics_snapshot()
    return HealthCheckResponse(status="ok", uptime_seconds=uptime, metrics=metrics_snapshot)

@app.post("/generate", response_model=NovelStateResponse, status_code=status.HTTP_202_ACCEPTED, summary="Trigger Novel Generation Stage")
async def trigger_generation(request: GenerateRequest, services: Any = Depends(get_app_services)):
    '''
    Triggers a specific stage of novel generation for a given novel ID.
    This endpoint is asynchronous and returns immediately, with generation happening in the background.
    '''
    logger.info(f"Received generation request for novel '{request.novel_id}', stage '{request.stage_name}'")
    increment_counter(f"api_requests_generate_{request.stage_name}")

    # Load novel state (or create new if not exists)
    project_data_path = Path(f"data/{request.novel_id}/state_snapshots")
    latest_state_file = project_data_path / "latest_state.json"
    current_state = await PrometheusState.load_from_disk(latest_state_file)

    if current_state is None:
        # For a new novel, create a basic outline or load from a default
        logger.info(f"No existing state for novel '{request.novel_id}'. Initializing new outline.")
        initial_outline = NovelOutline(metadata=NovelMetadata(project_name=request.novel_id, title=f"New Novel: {request.novel_id}", genre="Unknown"))
        current_state = PrometheusState(novel_outline=initial_outline)
        await services.state_manager.update_ltm(initial_outline) # Initialize LTM

    # Find the stage function (conceptual)
    # In a real LangGraph setup, you'd trigger the graph execution.
    # For scaffold, we'll simulate triggering a stage.
    # stage_func = getattr(stages_module, f"stage_{request.stage_name}_node", None) # Example dynamic load
    # if not stage_func:
    #     raise HTTPException(status_code=400, detail=f"Unknown stage: {request.stage_name}")

    async def _run_stage_in_background(state: PrometheusState):
        try:
            # Simulate running the stage
            logger.info(f"Background task: Running stage '{request.stage_name}' for novel '{request.novel_id}'")
            # This is where the actual stage logic would be called, e.g.:
            # updated_state = await stage_func(state, services.llm_router, services.state_manager)
            
            # For scaffold, simulate update
            await asyncio.sleep(2) # Simulate work
            state.total_cost_usd += 0.5 # Simulate cost
            state.current_scene += 1 # Simulate progress
            state.generated_novel_text.setdefault(state.current_chapter, {})[state.current_scene] = f"API-generated content for {request.novel_id}."
            await state.persist_to_disk(latest_state_file)
            logger.info(f"Background task: Stage '{request.stage_name}' completed for novel '{request.novel_id}'.")
            gauge(f"novel_{request.novel_id}_cost", state.total_cost_usd)
            increment_counter(f"novel_{request.novel_id}_scenes_completed")

        except BudgetExceededError as e:
            logger.error(f"Budget exceeded for novel '{request.novel_id}': {e}")
            # Notify user via some mechanism (e.g., webhook, internal message)
        except PrometheusError as e:
            logger.error(f"Prometheus Novel Error in background task for '{request.novel_id}': {e}")
        except Exception as e:
            handle_exception(e) # Catch all unexpected errors

    # Run the stage in a background task so the API call returns immediately
    asyncio.create_task(_run_stage_in_background(current_state))

    return NovelStateResponse(
        novel_id=request.novel_id,
        current_chapter=current_state.current_chapter,
        current_scene=current_state.current_scene,
        total_cost_usd=current_state.total_cost_usd
    )

@app.get("/novel/{novel_id}/state", response_model=NovelStateResponse, summary="Get Novel State")
async def get_novel_state(novel_id: str):
    '''Retrieves the current state of a novel.'''
    project_data_path = Path(f"data/{novel_id}/state_snapshots")
    latest_state_file = project_data_path / "latest_state.json"
    state = await PrometheusState.load_from_disk(latest_state_file)

    if state is None:
        raise HTTPException(status_code=404, detail=f"Novel '{novel_id}' not found or no state available.")

    return NovelStateResponse(
        novel_id=novel_id,
        current_chapter=state.current_chapter,
        current_scene=state.current_scene,
        total_cost_usd=state.total_cost_usd
    )

@app.get("/novel/{novel_id}/output", summary="Get Generated Novel Output")
async def get_novel_output(novel_id: str, chapter: Optional[int] = None, scene: Optional[int] = None):
    '''Retrieves generated novel text. Can specify chapter and scene.'''
    project_data_path = Path(f"data/{novel_id}/state_snapshots")
    latest_state_file = project_data_path / "latest_state.json"
    state = await PrometheusState.load_from_disk(latest_state_file)

    if state is None:
        raise HTTPException(status_code=404, detail=f"Novel '{novel_id}' not found or no state available.")

    if chapter is None:
        return state.generated_novel_text # Return all text
    
    if chapter not in state.generated_novel_text:
        raise HTTPException(status_code=404, detail=f"Chapter {chapter} not found for novel '{novel_id}'.")
    
    if scene is None:
        return state.generated_novel_text[chapter] # Return all scenes in chapter
    
    if scene not in state.generated_novel_text[chapter]:
        raise HTTPException(status_code=404, detail=f"Scene {scene} not found in Chapter {chapter} for novel '{novel_id}'.")
    
    return state.generated_novel_text[chapter][scene]

# --- Security (Placeholder) ---
# In a real app, implement:
# - API Key authentication (e.g., FastAPI Depends with APIKeyHeader)
# - OAuth2/JWT for user authentication
# - Role-based access control
# - Input validation (already started with Pydantic models)
# - Output sanitization (already started with output_validator)
# - Rate limiting (already in model_router, but also apply at API gateway/FastAPI level)
# - CORS configuration
# - HTTPS enforcement
# - Secure secret management (e.g., HashiCorp Vault, AWS Secrets Manager)

# To run this API:
# uvicorn api:app --reload --port 8000
