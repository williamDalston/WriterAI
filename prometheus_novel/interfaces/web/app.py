"""
WriterAI Web Dashboard - FastAPI Application

Main entry point for the web interface, providing:
- Dashboard for project management
- Real-time generation progress via WebSocket
- Ideas management
- Settings configuration
- API endpoints for novel generation
"""

import os
import re
import sys
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from prometheus_lib.utils.logging_config import setup_logging
import logging

# Setup logging
setup_logging()
logger = logging.getLogger("writerai.web")

# ============================================================================
# WebSocket Connection Manager
# ============================================================================

class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

    async def send_personal(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message to specific client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")


manager = ConnectionManager()

# ============================================================================
# Application State
# ============================================================================

class AppState:
    """Global application state."""

    def __init__(self):
        self.projects: Dict[str, Dict[str, Any]] = {}
        self.ideas: List[Dict[str, Any]] = []
        self.active_generations: Dict[str, Dict[str, Any]] = {}
        self.settings: Dict[str, Any] = {
            "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
            "google_api_key": os.getenv("GOOGLE_API_KEY", ""),
            "default_model": os.getenv("WRITERAI_DEFAULT_MODEL", "qwen2.5:7b"),  # Local Ollama by default
            "budget_usd": 100.0,
            "theme": "dark"
        }

    def load_projects(self):
        """Load existing projects from disk."""
        import yaml
        projects_dir = PROJECT_ROOT / "data" / "projects"
        if projects_dir.exists():
            for project_path in projects_dir.iterdir():
                if project_path.is_dir():
                    config_file = project_path / "config.yaml"
                    if config_file.exists():
                        # Read status from config file
                        try:
                            with open(config_file, 'r', encoding='utf-8') as f:
                                config = yaml.safe_load(f) or {}
                            status = config.get("status", "ready")
                        except Exception:
                            status = "ready"

                        self.projects[project_path.name] = {
                            "name": project_path.name,
                            "path": str(project_path),
                            "status": status
                        }
        logger.info(f"Loaded {len(self.projects)} projects")


app_state = AppState()

# ============================================================================
# Lifespan Management
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("Starting WriterAI Web Dashboard...")
    app_state.load_projects()
    yield
    logger.info("Shutting down WriterAI Web Dashboard...")

# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="WriterAI Dashboard",
    description="AI-Powered Novel Generation System",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - restrict origins for security
# In production, replace with specific origins; localhost is safe for local dev
ALLOWED_ORIGINS = os.getenv("WRITERAI_CORS_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
STATIC_DIR = Path(__file__).parent / "static"
TEMPLATES_DIR = Path(__file__).parent / "templates"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR)) if TEMPLATES_DIR.exists() else None

# ============================================================================
# Web Routes
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page."""
    if templates:
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "projects": list(app_state.projects.values()),
            "settings": app_state.settings
        })

    # Inline HTML if no template exists
    return HTMLResponse(content=get_dashboard_html())


@app.get("/projects", response_class=HTMLResponse)
async def projects_page(request: Request):
    """Projects management page."""
    return HTMLResponse(content=get_projects_html())


@app.get("/ideas", response_class=HTMLResponse)
async def ideas_page(request: Request):
    """Ideas management page."""
    return HTMLResponse(content=get_ideas_html())


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page."""
    return HTMLResponse(content=get_settings_html())


@app.get("/seed", response_class=HTMLResponse)
async def seed_page(request: Request):
    """Story seed input page."""
    return HTMLResponse(content=get_seed_html())

# ============================================================================
# API Routes (v2)
# ============================================================================

@app.get("/api/v2/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "writerai"
    }


@app.get("/api/v2/projects")
async def list_projects():
    """List all projects."""
    return {"projects": list(app_state.projects.values())}


@app.post("/api/v2/projects")
async def create_project(request: Request):
    """Create a new project."""
    data = await request.json()
    project_name = data.get("name", "").strip()
    project_name = re.sub(r'[^a-zA-Z0-9_-]', '', project_name.lower().replace(' ', '-'))

    if not project_name:
        raise HTTPException(status_code=400, detail="Project name required")

    # Path traversal guard
    project_dir = PROJECT_ROOT / "data" / "projects" / project_name
    if not str(project_dir.resolve()).startswith(str((PROJECT_ROOT / "data" / "projects").resolve())):
        raise HTTPException(status_code=400, detail="Invalid project name")
    project_dir.mkdir(parents=True, exist_ok=True)

    # Create project config
    config = {
        "name": project_name,
        "title": data.get("title", project_name),
        "genre": data.get("genre", "general"),
        "synopsis": data.get("synopsis", ""),
        "status": "created"
    }

    config_file = project_dir / "config.yaml"
    import yaml
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config, f)

    app_state.projects[project_name] = {
        "name": project_name,
        "path": str(project_dir),
        "status": "created"
    }

    logger.info(f"Created project: {project_name}")
    return {"status": "created", "project": config}


@app.get("/api/v2/projects/{project_name}")
async def get_project(project_name: str):
    """Get project details."""
    if project_name not in app_state.projects:
        raise HTTPException(status_code=404, detail="Project not found")
    return app_state.projects[project_name]


@app.post("/api/v2/projects/{project_name}/generate")
async def start_generation(project_name: str, background_tasks: BackgroundTasks):
    """Start novel generation for a project."""
    if project_name not in app_state.projects:
        raise HTTPException(status_code=404, detail="Project not found")

    # Start generation in background
    generation_id = f"{project_name}_{asyncio.get_event_loop().time()}"
    app_state.active_generations[generation_id] = {
        "project": project_name,
        "status": "running",
        "progress": 0,
        "current_stage": "initializing"
    }

    background_tasks.add_task(run_generation, project_name, generation_id)

    return {"status": "started", "generation_id": generation_id}


@app.get("/api/v2/projects/{project_name}/export")
async def export_project(project_name: str, sample: bool = True):
    """Export project to Word document for Kindle."""
    from fastapi.responses import FileResponse

    if project_name not in app_state.projects:
        raise HTTPException(status_code=404, detail="Project not found")

    project_path = Path(app_state.projects[project_name]["path"])

    try:
        from prometheus_novel.export.docx_exporter import KDPExporter
        exporter = KDPExporter(project_path)

        if sample:
            output_path = exporter.export_sample()
        else:
            output_path = exporter.export()

        logger.info(f"Exported project {project_name} to {output_path}")

        return FileResponse(
            path=str(output_path),
            filename=output_path.name,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail="Export failed. Check server logs for details.")


@app.get("/api/v2/ideas")
async def list_ideas():
    """List all saved ideas."""
    return {"ideas": app_state.ideas}


@app.post("/api/v2/ideas")
async def save_idea(request: Request):
    """Save a new idea."""
    data = await request.json()
    idea = {
        "id": len(app_state.ideas) + 1,
        "content": data.get("content", ""),
        "source": data.get("source", "web"),
        "tags": data.get("tags", []),
        "created_at": str(asyncio.get_event_loop().time())
    }
    app_state.ideas.append(idea)
    logger.info(f"Saved idea #{idea['id']}")
    return {"status": "saved", "idea": idea}


@app.get("/api/v2/settings")
async def get_settings():
    """Get current settings."""
    # Mask API keys — only show last 4 chars if key is long enough
    safe_settings = {**app_state.settings}
    for key_name in ("openai_api_key", "google_api_key", "anthropic_api_key"):
        val = safe_settings.get(key_name, "")
        if val and len(val) > 8:
            safe_settings[key_name] = "***..." + val[-4:]
        elif val:
            safe_settings[key_name] = "***"
    return safe_settings


@app.post("/api/v2/settings")
async def update_settings(request: Request):
    """Update settings."""
    data = await request.json()
    for key, value in data.items():
        if key in app_state.settings:
            app_state.settings[key] = value
    logger.info("Settings updated")
    return {"status": "updated"}


@app.post("/api/v2/seed")
async def create_project_from_seed(request: Request, background_tasks: BackgroundTasks):
    """Create a project from seed data with AI expansion."""
    import yaml
    import re

    data = await request.json()
    seed_data = data.get("seed", {})
    expand_with_ai = data.get("expand", True)

    # Validate minimum data
    if not seed_data.get("idea"):
        raise HTTPException(status_code=400, detail="Story idea is required")

    # Generate project name
    title = seed_data.get("title") or seed_data.get("idea", "untitled")[:30]
    project_name = title.lower().replace(" ", "-").replace("'", "")
    project_name = re.sub(r'[^a-z0-9-]', '', project_name)

    # Create project directory
    project_dir = PROJECT_ROOT / "data" / "projects" / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "drafts").mkdir(exist_ok=True)
    (project_dir / "output").mkdir(exist_ok=True)
    (project_dir / "memory").mkdir(exist_ok=True)

    # Map seed data to config
    config = {
        "project_name": project_name,
        "title": seed_data.get("title", title),
        "genre": seed_data.get("genre", "literary"),
        "tone": seed_data.get("tone", ""),
        "target_length": seed_data.get("target_length", "standard (60k)"),
        "synopsis": seed_data.get("idea", ""),
        "setting": seed_data.get("setting", ""),
        "world_rules": seed_data.get("world_rules", ""),
        "key_locations": seed_data.get("key_locations", ""),
        "protagonist": seed_data.get("protagonist", ""),
        "antagonist": seed_data.get("antagonist", ""),
        "other_characters": seed_data.get("other_characters", ""),
        "premise": seed_data.get("premise", ""),
        "central_conflict": seed_data.get("central_conflict", ""),
        "key_plot_points": seed_data.get("key_plot_points", ""),
        "subplots": seed_data.get("subplots", ""),
        "themes": seed_data.get("themes", ""),
        "central_question": seed_data.get("central_question", ""),
        "motifs": seed_data.get("motifs", ""),
        "writing_style": seed_data.get("writing_style", ""),
        "influences": seed_data.get("influences", ""),
        "avoid": seed_data.get("avoid", ""),
        "budget_usd": 0,
        "model_defaults": {
            "local_model": "qwen2.5:7b",
            "api_model": "qwen2.5:7b",
            "critic_model": "qwen2.5:7b",
            "fallback_model": "qwen2.5:7b"
        },
        "status": "seeded",

        # Strategic guidance - passed to pipeline for context
        "strategic_guidance": {
            "market_positioning": seed_data.get("market_positioning", ""),
            "beat_sheet": seed_data.get("beat_sheet", ""),
            "aesthetic_guide": seed_data.get("aesthetic_guide", ""),
            "tropes": seed_data.get("tropes", ""),
            "dialogue_bank": seed_data.get("dialogue_bank", ""),
            "cultural_notes": seed_data.get("cultural_notes", ""),
            "pacing_notes": seed_data.get("pacing_notes", ""),
            "commercial_notes": seed_data.get("commercial_notes", "")
        }
    }

    # Save config
    config_file = project_dir / "config.yaml"
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    # Save raw seed
    seed_file = project_dir / "seed_data.yaml"
    with open(seed_file, "w", encoding="utf-8") as f:
        yaml.dump(seed_data, f, default_flow_style=False, allow_unicode=True)

    # Update app state
    app_state.projects[project_name] = {
        "name": project_name,
        "path": str(project_dir),
        "status": "seeded"
    }

    # Count what was provided vs will be generated
    provided = [k for k, v in seed_data.items() if v and v.strip()]
    total_fields = 21  # Total possible fields

    logger.info(f"Created seeded project: {project_name} ({len(provided)}/{total_fields} fields provided)")

    return {
        "status": "created",
        "project_name": project_name,
        "project_path": str(project_dir),
        "fields_provided": len(provided),
        "fields_total": total_fields
    }

# ============================================================================
# WebSocket Endpoints
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "ping":
                await manager.send_personal(websocket, {"type": "pong"})

            elif message_type == "subscribe":
                # Subscribe to project updates
                project = data.get("project")
                await manager.send_personal(websocket, {
                    "type": "subscribed",
                    "project": project
                })

            elif message_type == "request_suggestions":
                # Handle suggestion requests from browser plugin
                text = data.get("text", "")
                suggestions = await generate_suggestions(text)
                await manager.send_personal(websocket, {
                    "type": "suggestions",
                    "suggestions": suggestions
                })

            elif message_type == "save_idea":
                # Save idea from browser plugin
                idea = {
                    "id": len(app_state.ideas) + 1,
                    "content": data.get("content", ""),
                    "source": "browser_plugin",
                    "tags": data.get("tags", [])
                }
                app_state.ideas.append(idea)
                await manager.send_personal(websocket, {
                    "type": "idea_saved",
                    "idea": idea
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ============================================================================
# Background Tasks
# ============================================================================

async def run_generation(project_name: str, generation_id: str):
    """Run novel generation in background using the real 12-stage pipeline."""
    import yaml

    try:
        # Get project path
        project_info = app_state.projects.get(project_name)
        if not project_info:
            raise ValueError(f"Project not found: {project_name}")

        project_path = Path(project_info["path"])

        # Load project config to get model preference
        config_file = project_path / "config.yaml"
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

        # Get model defaults from config - default to local Ollama (no API cost)
        model_defaults = config.get("model_defaults", {})
        api_model = model_defaults.get("api_model", "qwen2.5:7b")
        critic_model = model_defaults.get("critic_model", api_model)
        fallback_model = model_defaults.get("fallback_model", api_model)

        # Create LLM clients - use get_client for smart routing (Ollama vs API)
        from prometheus_novel.prometheus_lib.llm.clients import get_client, is_ollama_model

        llm_clients = {}
        default_client = get_client(api_model)

        # Use same client for all stages when local (Ollama) - no API keys needed
        llm_clients["gpt"] = default_client
        llm_clients["claude"] = get_client(critic_model)
        llm_clients["gemini"] = get_client(fallback_model)
        logger.info(f"Using model: {api_model} (local={'Ollama' if is_ollama_model(api_model) else 'API'})")

        # Import and run the pipeline with multi-model support
        from prometheus_novel.stages.pipeline import PipelineOrchestrator

        orchestrator = PipelineOrchestrator(
            project_path,
            llm_client=default_client,
            llm_clients=llm_clients
        )

        # Register callbacks for progress updates
        async def on_stage_start(stage_name, index):
            progress = int((index / 12) * 100)
            app_state.active_generations[generation_id].update({
                "current_stage": stage_name,
                "progress": progress
            })
            await manager.broadcast({
                "type": "generation_progress",
                "generation_id": generation_id,
                "project": project_name,
                "stage": stage_name,
                "progress": progress
            })

        async def on_stage_complete(stage_name, result):
            logger.info(f"Stage {stage_name} complete: {result.status.value}")

        async def on_pipeline_complete(state):
            logger.info(f"Pipeline complete! Total tokens: {state.total_tokens}, Cost: ${state.total_cost_usd:.4f}")

        orchestrator.on("on_stage_start", on_stage_start)
        orchestrator.on("on_stage_complete", on_stage_complete)
        orchestrator.on("on_pipeline_complete", on_pipeline_complete)

        # Run the pipeline
        logger.info(f"Starting generation for {project_name} with model {api_model}")
        final_state = await orchestrator.run()

        # Update config with completed status
        config["status"] = "completed"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

        # Export to Word document
        from prometheus_novel.export.docx_exporter import KDPExporter
        exporter = KDPExporter(project_path)
        output_path = exporter.export()
        logger.info(f"Novel exported to: {output_path}")

        # Update project status in memory
        app_state.projects[project_name]["status"] = "completed"

        app_state.active_generations[generation_id].update({
            "status": "completed",
            "progress": 100,
            "output_file": str(output_path)
        })

        await manager.broadcast({
            "type": "generation_complete",
            "generation_id": generation_id,
            "project": project_name,
            "output_file": str(output_path)
        })

    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        app_state.active_generations[generation_id].update({
            "status": "failed",
            "error": str(e)
        })
        await manager.broadcast({
            "type": "generation_error",
            "generation_id": generation_id,
            "project": project_name,
            "error": str(e)
        })


async def stream_stage_output(stage_name: str, project_name: str, client, prompt: str, generation_id: str):
    """Stream LLM output for a stage through WebSocket for real-time display."""
    try:
        buffer = ""
        async for chunk in client.generate_stream(prompt):
            buffer += chunk
            # Broadcast chunks to connected clients
            await manager.broadcast({
                "type": "generation_stream",
                "generation_id": generation_id,
                "project": project_name,
                "stage": stage_name,
                "chunk": chunk,
                "buffer_length": len(buffer)
            })
        return buffer
    except Exception as e:
        logger.error(f"Streaming failed for {stage_name}: {e}")
        # Fall back to non-streaming
        response = await client.generate(prompt)
        return response.content if hasattr(response, "content") else str(response)


async def generate_suggestions(text: str) -> List[Dict[str, str]]:
    """Generate writing suggestions for text."""
    # Placeholder - would use LLM in production
    return [
        {"type": "style", "suggestion": "Consider varying sentence length for better rhythm."},
        {"type": "clarity", "suggestion": "This passage could be more concise."}
    ]

# ============================================================================
# HTML Templates (Inline)
# ============================================================================

def get_dashboard_html() -> str:
    """Generate dashboard HTML."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WriterAI Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e4e4e7;
            min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header {
            display: flex; justify-content: space-between; align-items: center;
            padding: 20px 0; border-bottom: 1px solid #374151;
        }
        h1 { font-size: 1.8rem; color: #a78bfa; }
        nav a {
            color: #9ca3af; text-decoration: none; margin-left: 20px;
            transition: color 0.2s;
        }
        nav a:hover { color: #a78bfa; }
        .hero {
            text-align: center; padding: 60px 0;
        }
        .hero h2 { font-size: 2.5rem; margin-bottom: 10px; }
        .hero p { color: #9ca3af; font-size: 1.2rem; }
        .cards {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px; margin-top: 40px;
        }
        .card {
            background: rgba(255,255,255,0.05); border-radius: 12px;
            padding: 24px; border: 1px solid #374151;
            transition: transform 0.2s, border-color 0.2s;
        }
        .card:hover { transform: translateY(-4px); border-color: #a78bfa; }
        .card h3 { color: #a78bfa; margin-bottom: 12px; }
        .card p { color: #9ca3af; line-height: 1.6; }
        .btn {
            display: inline-block; background: #a78bfa; color: #1a1a2e;
            padding: 12px 24px; border-radius: 8px; text-decoration: none;
            font-weight: 600; margin-top: 20px; transition: background 0.2s;
        }
        .btn:hover { background: #8b5cf6; }
        .status-bar {
            position: fixed; bottom: 0; left: 0; right: 0;
            background: rgba(26,26,46,0.95); padding: 12px 20px;
            border-top: 1px solid #374151; display: flex;
            justify-content: space-between; align-items: center;
        }
        .status-dot { width: 8px; height: 8px; border-radius: 50%; background: #10b981; }
        .status-text { color: #9ca3af; margin-left: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>WriterAI</h1>
            <nav>
                <a href="/">Dashboard</a>
                <a href="/seed">Seed Story</a>
                <a href="/projects">Projects</a>
                <a href="/ideas">Ideas</a>
                <a href="/settings">Settings</a>
            </nav>
        </header>

        <section class="hero">
            <h2>AI-Powered Novel Generation</h2>
            <p>Transform your ideas into publication-ready novels</p>
            <a href="/seed" class="btn">Seed Your Story</a>
        </section>

        <section class="cards">
            <div class="card">
                <h3>Quick Start</h3>
                <p>Create a new project from a single sentence prompt and let the AI generate a complete novel outline.</p>
            </div>
            <div class="card">
                <h3>12-Stage Pipeline</h3>
                <p>From high concept to final polish, every novel goes through our proven quality pipeline.</p>
            </div>
            <div class="card">
                <h3>Quality Guaranteed</h3>
                <p>15+ quality dimensions ensure your novel meets publication standards.</p>
            </div>
        </section>
    </div>

    <div class="status-bar">
        <div style="display: flex; align-items: center;">
            <span class="status-dot"></span>
            <span class="status-text">System Ready</span>
        </div>
        <span class="status-text">WriterAI v1.0.0</span>
    </div>

    <script>
        // WebSocket connection for real-time updates
        const ws = new WebSocket('ws://' + window.location.host + '/ws');
        ws.onopen = () => console.log('Connected to WriterAI');
        ws.onmessage = (e) => {
            const data = JSON.parse(e.data);
            console.log('Received:', data);
        };
    </script>
</body>
</html>
"""


def get_projects_html() -> str:
    """Generate projects page HTML."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Projects - WriterAI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e4e4e7; min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header {
            display: flex; justify-content: space-between; align-items: center;
            padding: 20px 0; border-bottom: 1px solid #374151;
        }
        h1 { font-size: 1.8rem; color: #a78bfa; }
        nav a { color: #9ca3af; text-decoration: none; margin-left: 20px; }
        nav a:hover { color: #a78bfa; }
        h2 { margin: 40px 0 20px; }
        .project-form {
            background: rgba(255,255,255,0.05); border-radius: 12px;
            padding: 24px; border: 1px solid #374151; margin-bottom: 30px;
        }
        .form-group { margin-bottom: 16px; }
        label { display: block; margin-bottom: 8px; color: #9ca3af; }
        input, textarea, select {
            width: 100%; padding: 12px; border-radius: 8px;
            border: 1px solid #374151; background: rgba(0,0,0,0.3);
            color: #e4e4e7; font-size: 1rem;
        }
        textarea { min-height: 100px; resize: vertical; }
        .btn {
            background: #a78bfa; color: #1a1a2e; padding: 12px 24px;
            border-radius: 8px; border: none; font-weight: 600;
            cursor: pointer; font-size: 1rem;
        }
        .btn:hover { background: #8b5cf6; }
        .projects-grid { display: grid; gap: 20px; }
        .project-card {
            background: rgba(255,255,255,0.05); border-radius: 12px;
            padding: 20px; border: 1px solid #374151;
            display: flex; justify-content: space-between; align-items: center;
        }
        .project-status {
            padding: 4px 12px; border-radius: 20px; font-size: 0.85rem;
        }
        .status-ready { background: #10b981; color: #fff; }
        .status-seeded { background: #3b82f6; color: #fff; }
        .status-generating { background: #f59e0b; color: #fff; }
        .status-completed { background: #10b981; color: #fff; }
        .project-actions { display: flex; gap: 10px; align-items: center; }
        .btn-generate {
            background: #10b981; color: #fff; border: none;
            padding: 8px 16px; border-radius: 6px; cursor: pointer;
            font-weight: 600; font-size: 0.9rem; transition: background 0.2s;
        }
        .btn-generate:hover { background: #059669; }
        .btn-generate:disabled { background: #374151; cursor: not-allowed; }
        .btn-download {
            background: #3b82f6; color: #fff; border: none;
            padding: 8px 16px; border-radius: 6px; cursor: pointer;
            font-weight: 600; font-size: 0.9rem; transition: background 0.2s;
            text-decoration: none; display: inline-block;
        }
        .btn-download:hover { background: #2563eb; }
        .progress-indicator {
            display: none; color: #f59e0b; font-size: 0.85rem;
        }
        .progress-indicator.active { display: block; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>WriterAI</h1>
            <nav>
                <a href="/">Dashboard</a>
                <a href="/seed">Seed Story</a>
                <a href="/projects">Projects</a>
                <a href="/ideas">Ideas</a>
                <a href="/settings">Settings</a>
            </nav>
        </header>

        <h2>Create New Project</h2>
        <div class="project-form">
            <form id="newProjectForm">
                <div class="form-group">
                    <label>Project Name</label>
                    <input type="text" id="projectName" required placeholder="my-novel">
                </div>
                <div class="form-group">
                    <label>Title</label>
                    <input type="text" id="projectTitle" placeholder="The Great Adventure">
                </div>
                <div class="form-group">
                    <label>Genre</label>
                    <select id="projectGenre">
                        <option value="sci-fi">Science Fiction</option>
                        <option value="fantasy">Fantasy</option>
                        <option value="mystery">Mystery</option>
                        <option value="thriller">Thriller</option>
                        <option value="romance">Romance</option>
                        <option value="literary">Literary Fiction</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Synopsis</label>
                    <textarea id="projectSynopsis" placeholder="A brief description of your novel idea..."></textarea>
                </div>
                <button type="submit" class="btn">Create Project</button>
            </form>
        </div>

        <h2>Your Projects</h2>
        <div id="projectsList" class="projects-grid">
            <p style="color: #9ca3af;">No projects yet. Create one above!</p>
        </div>
    </div>

    <script>
        function esc(s){return String(s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}

        const form = document.getElementById('newProjectForm');
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = {
                name: document.getElementById('projectName').value,
                title: document.getElementById('projectTitle').value,
                genre: document.getElementById('projectGenre').value,
                synopsis: document.getElementById('projectSynopsis').value
            };

            const response = await fetch('/api/v2/projects', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                alert('Project created!');
                loadProjects();
                form.reset();
            }
        });

        async function loadProjects() {
            const response = await fetch('/api/v2/projects');
            const data = await response.json();
            const list = document.getElementById('projectsList');

            if (data.projects.length === 0) {
                list.innerHTML = '<p style="color: #9ca3af;">No projects yet.</p>';
                return;
            }

            list.innerHTML = data.projects.map(p => `
                <div class="project-card" id="project-${esc(p.name)}">
                    <div>
                        <h3>${esc(p.name)}</h3>
                        <p style="color: #9ca3af;">${esc(p.path)}</p>
                        <p class="progress-indicator" id="progress-${esc(p.name)}"></p>
                    </div>
                    <div class="project-actions">
                        <span class="project-status status-${esc(p.status)}" id="status-${esc(p.name)}">${esc(p.status)}</span>
                        <a href="/api/v2/projects/${encodeURIComponent(p.name)}/export?sample=${p.status !== 'completed'}"
                           class="btn-download" id="download-${esc(p.name)}" download>
                            ${p.status === 'completed' ? 'Download Novel' : 'Download Seed'}
                        </a>
                        <button class="btn-generate" id="btn-${esc(p.name)}" onclick="startGeneration('${esc(p.name)}')"
                            ${p.status === 'generating' ? 'disabled' : ''}>
                            ${p.status === 'generating' ? 'Generating...' : 'Generate'}
                        </button>
                    </div>
                </div>
            `).join('');
        }

        loadProjects();

        // WebSocket for real-time progress updates
        const ws = new WebSocket('ws://' + window.location.host + '/ws');
        ws.onopen = () => console.log('Connected to WriterAI');
        ws.onmessage = (e) => {
            const data = JSON.parse(e.data);
            console.log('WS message:', data);

            if (data.type === 'generation_progress') {
                const progress = document.getElementById('progress-' + data.project);
                const status = document.getElementById('status-' + data.project);
                if (progress) {
                    progress.classList.add('active');
                    progress.textContent = 'Stage: ' + data.stage + ' (' + data.progress + '%)';
                }
                if (status) {
                    status.className = 'project-status status-generating';
                    status.textContent = 'generating';
                }
            } else if (data.type === 'generation_complete') {
                const progress = document.getElementById('progress-' + data.project);
                const status = document.getElementById('status-' + data.project);
                const btn = document.getElementById('btn-' + data.project);
                const downloadBtn = document.getElementById('download-' + data.project);
                if (progress) {
                    progress.classList.remove('active');
                }
                if (status) {
                    status.className = 'project-status status-completed';
                    status.textContent = 'completed';
                }
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = 'Generate';
                }
                if (downloadBtn) {
                    downloadBtn.href = '/api/v2/projects/' + data.project + '/export?sample=false';
                    downloadBtn.textContent = 'Download Novel';
                }
                alert('Generation complete! Click "Download Novel" to get your book.');
            } else if (data.type === 'generation_error') {
                const progress = document.getElementById('progress-' + data.project);
                const status = document.getElementById('status-' + data.project);
                const btn = document.getElementById('btn-' + data.project);
                if (progress) {
                    progress.classList.remove('active');
                    progress.textContent = 'Error: ' + data.error;
                    progress.classList.add('active');
                }
                if (status) {
                    status.className = 'project-status status-seeded';
                    status.textContent = 'failed';
                }
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = 'Retry';
                }
                alert('Generation failed: ' + data.error);
            }
        };

        async function startGeneration(projectName) {
            const btn = document.getElementById('btn-' + projectName);
            const status = document.getElementById('status-' + projectName);
            const progress = document.getElementById('progress-' + projectName);

            if (!confirm('Start novel generation for "' + projectName + '"? This will use API credits.')) {
                return;
            }

            btn.disabled = true;
            btn.textContent = 'Starting...';
            status.className = 'project-status status-generating';
            status.textContent = 'generating';
            progress.classList.add('active');
            progress.textContent = 'Initializing...';

            try {
                const response = await fetch('/api/v2/projects/' + projectName + '/generate', {
                    method: 'POST'
                });

                if (response.ok) {
                    const result = await response.json();
                    console.log('Generation started:', result);
                    btn.textContent = 'Generating...';
                } else {
                    const error = await response.json();
                    alert('Failed to start generation: ' + (error.detail || 'Unknown error'));
                    btn.disabled = false;
                    btn.textContent = 'Generate';
                    status.className = 'project-status status-seeded';
                    status.textContent = 'seeded';
                    progress.classList.remove('active');
                }
            } catch (error) {
                alert('Error: ' + error.message);
                btn.disabled = false;
                btn.textContent = 'Generate';
                progress.classList.remove('active');
            }
        }
    </script>
</body>
</html>
"""


def get_ideas_html() -> str:
    """Generate ideas page HTML."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ideas - WriterAI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e4e4e7; min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header {
            display: flex; justify-content: space-between; align-items: center;
            padding: 20px 0; border-bottom: 1px solid #374151;
        }
        h1 { font-size: 1.8rem; color: #a78bfa; }
        nav a { color: #9ca3af; text-decoration: none; margin-left: 20px; }
        nav a:hover { color: #a78bfa; }
        h2 { margin: 40px 0 20px; }
        .idea-form {
            background: rgba(255,255,255,0.05); border-radius: 12px;
            padding: 24px; border: 1px solid #374151; margin-bottom: 30px;
        }
        textarea {
            width: 100%; padding: 12px; border-radius: 8px;
            border: 1px solid #374151; background: rgba(0,0,0,0.3);
            color: #e4e4e7; min-height: 100px; resize: vertical;
            margin-bottom: 16px; font-size: 1rem;
        }
        .btn {
            background: #a78bfa; color: #1a1a2e; padding: 12px 24px;
            border-radius: 8px; border: none; font-weight: 600;
            cursor: pointer;
        }
        .ideas-list { display: grid; gap: 16px; }
        .idea-card {
            background: rgba(255,255,255,0.05); border-radius: 12px;
            padding: 20px; border: 1px solid #374151;
        }
        .idea-meta { color: #9ca3af; font-size: 0.85rem; margin-top: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>WriterAI</h1>
            <nav>
                <a href="/">Dashboard</a>
                <a href="/seed">Seed Story</a>
                <a href="/projects">Projects</a>
                <a href="/ideas">Ideas</a>
                <a href="/settings">Settings</a>
            </nav>
        </header>

        <h2>Capture Ideas</h2>
        <div class="idea-form">
            <textarea id="ideaContent" placeholder="Write your idea here..."></textarea>
            <button class="btn" onclick="saveIdea()">Save Idea</button>
        </div>

        <h2>Your Ideas</h2>
        <div id="ideasList" class="ideas-list">
            <p style="color: #9ca3af;">No ideas yet. Start capturing!</p>
        </div>
    </div>

    <script>
        function esc(s){return String(s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}

        async function saveIdea() {
            const content = document.getElementById('ideaContent').value;
            if (!content.trim()) return;

            await fetch('/api/v2/ideas', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });

            document.getElementById('ideaContent').value = '';
            loadIdeas();
        }

        async function loadIdeas() {
            const response = await fetch('/api/v2/ideas');
            const data = await response.json();
            const list = document.getElementById('ideasList');

            if (data.ideas.length === 0) {
                list.innerHTML = '<p style="color: #9ca3af;">No ideas yet.</p>';
                return;
            }

            list.innerHTML = data.ideas.map(idea => `
                <div class="idea-card">
                    <p>${esc(idea.content)}</p>
                    <div class="idea-meta">Source: ${esc(idea.source)}</div>
                </div>
            `).join('');
        }

        loadIdeas();
    </script>
</body>
</html>
"""


def get_settings_html() -> str:
    """Generate settings page HTML."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Settings - WriterAI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e4e4e7; min-height: 100vh;
        }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        header {
            display: flex; justify-content: space-between; align-items: center;
            padding: 20px 0; border-bottom: 1px solid #374151;
        }
        h1 { font-size: 1.8rem; color: #a78bfa; }
        nav a { color: #9ca3af; text-decoration: none; margin-left: 20px; }
        nav a:hover { color: #a78bfa; }
        h2 { margin: 40px 0 20px; }
        .settings-form {
            background: rgba(255,255,255,0.05); border-radius: 12px;
            padding: 24px; border: 1px solid #374151;
        }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; color: #9ca3af; }
        input, select {
            width: 100%; padding: 12px; border-radius: 8px;
            border: 1px solid #374151; background: rgba(0,0,0,0.3);
            color: #e4e4e7; font-size: 1rem;
        }
        .btn {
            background: #a78bfa; color: #1a1a2e; padding: 12px 24px;
            border-radius: 8px; border: none; font-weight: 600;
            cursor: pointer; margin-top: 20px;
        }
        .btn:hover { background: #8b5cf6; }
        .hint { font-size: 0.85rem; color: #6b7280; margin-top: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>WriterAI</h1>
            <nav>
                <a href="/">Dashboard</a>
                <a href="/seed">Seed Story</a>
                <a href="/projects">Projects</a>
                <a href="/ideas">Ideas</a>
                <a href="/settings">Settings</a>
            </nav>
        </header>

        <h2>Settings</h2>
        <div class="settings-form">
            <div class="form-group">
                <label>OpenAI API Key</label>
                <input type="password" id="openaiKey" placeholder="sk-...">
                <p class="hint">Required for GPT-4 based generation</p>
            </div>
            <div class="form-group">
                <label>Google API Key</label>
                <input type="password" id="googleKey" placeholder="...">
                <p class="hint">Optional - for Gemini models</p>
            </div>
            <div class="form-group">
                <label>Default Model</label>
                <select id="defaultModel">
                    <option value="qwen2.5:7b" selected>Local: Qwen 2.5 (Recommended, Free)</option>
                    <option value="llama3.2:3b">Local: Llama 3.2 3B</option>
                    <option value="llama3.1:8b">Local: Llama 3.1 8B</option>
                    <option value="mistral:7b">Local: Mistral 7B</option>
                    <option value="phi3:mini">Local: Phi-3 Mini</option>
                    <option value="gemma2:2b">Local: Gemma 2 2B</option>
                    <option value="gpt-4o-mini">GPT-4o Mini (API, Paid)</option>
                    <option value="gpt-4o">GPT-4o (API, Paid)</option>
                    <option value="gemini-2.0-flash">Gemini 2.0 Flash (API, Paid)</option>
                </select>
                <p class="hint">Local models need Ollama installed. Run: ollama run qwen2.5:7b</p>
            </div>
            <div class="form-group">
                <label>Budget (USD)</label>
                <input type="number" id="budgetUsd" value="100" min="1" max="10000">
                <p class="hint">Maximum spending limit per project</p>
            </div>
            <button class="btn" onclick="saveSettings()">Save Settings</button>
        </div>
    </div>

    <script>
        async function loadSettings() {
            const response = await fetch('/api/v2/settings');
            const settings = await response.json();
            document.getElementById('defaultModel').value = settings.default_model || 'gpt-4o-mini';
            document.getElementById('budgetUsd').value = settings.budget_usd || 100;
        }

        async function saveSettings() {
            const data = {
                openai_api_key: document.getElementById('openaiKey').value || undefined,
                google_api_key: document.getElementById('googleKey').value || undefined,
                default_model: document.getElementById('defaultModel').value,
                budget_usd: parseFloat(document.getElementById('budgetUsd').value)
            };

            // Remove empty values
            Object.keys(data).forEach(k => data[k] === undefined && delete data[k]);

            await fetch('/api/v2/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            alert('Settings saved!');
        }

        loadSettings();
    </script>
</body>
</html>
"""

def get_seed_html() -> str:
    """Generate seed page HTML - the main story input GUI."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Seed Your Story - WriterAI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e4e4e7; min-height: 100vh;
        }
        .container { max-width: 1000px; margin: 0 auto; padding: 20px; padding-bottom: 100px; }
        header {
            display: flex; justify-content: space-between; align-items: center;
            padding: 20px 0; border-bottom: 1px solid #374151;
        }
        h1 { font-size: 1.8rem; color: #a78bfa; }
        nav a { color: #9ca3af; text-decoration: none; margin-left: 20px; }
        nav a:hover { color: #a78bfa; }
        nav a.active { color: #a78bfa; font-weight: 600; }

        .hero { text-align: center; padding: 40px 0 30px; }
        .hero h2 { font-size: 2rem; margin-bottom: 10px; color: #a78bfa; }
        .hero p { color: #9ca3af; font-size: 1.1rem; max-width: 600px; margin: 0 auto; }

        .mode-selector {
            display: flex; justify-content: center; gap: 12px; margin: 30px 0;
        }
        .mode-btn {
            padding: 12px 24px; border-radius: 8px; border: 2px solid #374151;
            background: transparent; color: #9ca3af; cursor: pointer;
            font-size: 1rem; transition: all 0.2s;
        }
        .mode-btn:hover { border-color: #a78bfa; color: #a78bfa; }
        .mode-btn.active { background: #a78bfa; color: #1a1a2e; border-color: #a78bfa; }

        .section { margin-bottom: 30px; }
        .section-header {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 15px; cursor: pointer;
        }
        .section-header h3 { color: #a78bfa; font-size: 1.1rem; }
        .section-header .badge {
            background: #374151; color: #9ca3af; padding: 4px 10px;
            border-radius: 12px; font-size: 0.8rem;
        }
        .section-header .badge.required { background: #7c3aed; color: white; }
        .section-header .badge.filled { background: #10b981; color: white; }

        .section-content {
            background: rgba(255,255,255,0.03); border-radius: 12px;
            padding: 20px; border: 1px solid #374151;
        }
        .section-content.collapsed { display: none; }

        .form-group { margin-bottom: 20px; }
        .form-group:last-child { margin-bottom: 0; }
        label { display: block; margin-bottom: 8px; color: #9ca3af; font-size: 0.9rem; }
        .label-hint { color: #6b7280; font-size: 0.8rem; margin-top: 4px; }

        input, textarea, select {
            width: 100%; padding: 12px; border-radius: 8px;
            border: 1px solid #374151; background: rgba(0,0,0,0.3);
            color: #e4e4e7; font-size: 1rem; font-family: inherit;
        }
        input:focus, textarea:focus, select:focus {
            outline: none; border-color: #a78bfa;
        }
        textarea { min-height: 120px; resize: vertical; }
        textarea.large { min-height: 200px; }

        .template-box {
            background: rgba(0,0,0,0.4); border: 1px dashed #374151;
            border-radius: 8px; padding: 15px; margin-bottom: 20px;
        }
        .template-box h4 { color: #a78bfa; margin-bottom: 10px; font-size: 0.9rem; }
        .template-box pre {
            color: #9ca3af; font-size: 0.85rem; white-space: pre-wrap;
            font-family: 'Monaco', 'Consolas', monospace;
        }

        .progress-bar {
            position: fixed; bottom: 0; left: 0; right: 0;
            background: rgba(26,26,46,0.98); padding: 20px;
            border-top: 1px solid #374151; z-index: 100;
        }
        .progress-inner {
            max-width: 1000px; margin: 0 auto;
            display: flex; justify-content: space-between; align-items: center;
        }
        .progress-stats { color: #9ca3af; }
        .progress-stats span { color: #a78bfa; font-weight: 600; }
        .btn-group { display: flex; gap: 12px; }

        .btn {
            padding: 12px 28px; border-radius: 8px; border: none;
            font-size: 1rem; font-weight: 600; cursor: pointer;
            transition: all 0.2s;
        }
        .btn-primary { background: #a78bfa; color: #1a1a2e; }
        .btn-primary:hover { background: #8b5cf6; }
        .btn-secondary { background: #374151; color: #e4e4e7; }
        .btn-secondary:hover { background: #4b5563; }

        .quick-fill {
            background: rgba(167, 139, 250, 0.1); border: 1px solid #a78bfa;
            border-radius: 8px; padding: 15px; margin-bottom: 20px;
        }
        .quick-fill h4 { color: #a78bfa; margin-bottom: 10px; }
        .quick-fill p { color: #9ca3af; font-size: 0.9rem; margin-bottom: 10px; }
        .quick-fill textarea { min-height: 150px; }

        .success-modal {
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.8); display: none; z-index: 200;
            justify-content: center; align-items: center;
        }
        .success-modal.show { display: flex; }
        .success-content {
            background: #1a1a2e; border-radius: 16px; padding: 40px;
            text-align: center; max-width: 500px; border: 1px solid #374151;
        }
        .success-content h2 { color: #10b981; margin-bottom: 20px; }
        .success-content p { color: #9ca3af; margin-bottom: 20px; }
        .success-content .path {
            background: rgba(0,0,0,0.3); padding: 12px; border-radius: 8px;
            font-family: monospace; color: #a78bfa; margin-bottom: 20px;
            word-break: break-all;
        }

        .copy-template-btn {
            position: absolute; top: 10px; right: 10px;
            background: #374151; color: #9ca3af; border: none;
            padding: 6px 12px; border-radius: 6px; cursor: pointer;
            font-size: 0.8rem;
        }
        .copy-template-btn:hover { background: #4b5563; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>WriterAI</h1>
            <nav>
                <a href="/">Dashboard</a>
                <a href="/projects">Projects</a>
                <a href="/seed" class="active">Seed Story</a>
                <a href="/ideas">Ideas</a>
                <a href="/settings">Settings</a>
            </nav>
        </header>

        <section class="hero">
            <h2>Seed Your Story</h2>
            <p>Fill in what you have, skip what you don't. AI will expand the rest into a complete novel blueprint.</p>
        </section>

        <!-- JSON Template Section -->
        <div class="quick-fill" style="position: relative;">
            <h4>Quick Fill: Copy Template to LLM, Paste Back Filled</h4>
            <p>1. Click "Copy Template" 2. Paste to ChatGPT/Claude with your story idea 3. Paste filled JSON back and click Parse</p>
            <button class="copy-template-btn" id="copyBtn" onclick="copyTemplate()">Copy Template</button>
            <pre id="jsonTemplate" style="background: rgba(0,0,0,0.5); padding: 15px; border-radius: 8px; font-size: 0.8rem; overflow-x: auto; max-height: 400px; overflow-y: auto; margin: 15px 0; color: #a78bfa; white-space: pre-wrap;">{
  "idea": "REQUIRED: Your core story concept in 1-3 sentences",
  "title": "Working title for the novel",
  "genre": "sci-fi | fantasy | mystery | thriller | romance | horror | literary | historical",
  "tone": "dark, hopeful, gritty, whimsical, satirical, etc.",
  "target_length": "novella (30k) | standard (60k) | epic (100k+)",

  "setting": "Time, place, atmosphere. Be specific.",
  "world_rules": "What's possible/impossible? Magic system? Technology? Society rules?",
  "key_locations": "Important places where scenes happen. List 3-5.",

  "protagonist": "Name, age, role, personality, goal, flaw, what blocks them",
  "antagonist": "Name, role, motivation, methods, relationship to protagonist",
  "other_characters": "Supporting cast with names, roles, relationships",

  "premise": "The central 'what if' of your story",
  "central_conflict": "The main tension driving the plot",
  "key_plot_points": "Opening, inciting incident, midpoint, low point, climax, resolution",
  "subplots": "Secondary storylines (romance, mystery, character arcs)",

  "themes": "Core ideas explored (identity, power, love, redemption, etc.)",
  "central_question": "The philosophical question the story asks",
  "motifs": "Recurring symbols, images, or patterns",

  "writing_style": "POV, tense, prose style, pacing preferences",
  "influences": "Comparable books, authors, or media that inspire this story",
  "avoid": "Tropes, elements, or approaches you do NOT want",

  "market_positioning": "Target subgenre, reader expectations, comp titles, keywords",
  "beat_sheet": "Opening (5%): setup. Inciting (10%): disruption. Threshold (25%): point of no return. Midpoint (50%): major shift. Low point (75%): all is lost. Climax (85%): confrontation. Resolution (95%): new equilibrium.",
  "aesthetic_guide": "Fashion brands, luxury items, sensory details (smells, sounds, textures)",
  "tropes": "List key tropes with when/how to execute them",
  "dialogue_bank": "Signature phrases, endearments, power lines for characters",
  "cultural_notes": "Specific cultural details, terminology, customs needed",
  "commercial_notes": "Series potential, blurb hooks, chapter structure, mobile-first tips"
}</pre>
            <div style="margin-top: 15px;">
                <label style="color: #a78bfa; font-weight: 600;">Paste Filled JSON Here:</label>
                <textarea id="quickPaste" placeholder='Paste the JSON filled by your LLM here...' style="font-family: monospace; min-height: 120px;"></textarea>
                <button class="btn btn-primary" id="parseBtn" style="margin-top: 10px;" onclick="parseJSON()">Parse JSON &amp; Fill Form</button>
            </div>
        </div>

        <form id="seedForm">
            <!-- REQUIRED: Core Idea -->
            <div class="section">
                <div class="section-header" onclick="toggleSection(this)">
                    <h3>Core Idea</h3>
                    <span class="badge required">Required</span>
                </div>
                <div class="section-content">
                    <div class="form-group">
                        <label>Your Story Idea *</label>
                        <textarea id="idea" name="idea" class="large" required
                            placeholder="A detective who can read memories discovers her own past was fabricated by the same corporation she works for..."></textarea>
                        <p class="label-hint">One sentence or several paragraphs - as much as you have.</p>
                    </div>
                </div>
            </div>

            <!-- Basic Info -->
            <div class="section">
                <div class="section-header" onclick="toggleSection(this)">
                    <h3>Basic Info</h3>
                    <span class="badge" id="badge-basic">Optional</span>
                </div>
                <div class="section-content">
                    <div class="form-group">
                        <label>Working Title</label>
                        <input type="text" id="title" name="title" placeholder="The Memory Merchant">
                    </div>
                    <div class="form-group">
                        <label>Genre</label>
                        <select id="genre" name="genre">
                            <option value="">-- Let AI decide --</option>
                            <option value="sci-fi">Science Fiction</option>
                            <option value="fantasy">Fantasy</option>
                            <option value="mystery">Mystery</option>
                            <option value="thriller">Thriller</option>
                            <option value="romance">Romance</option>
                            <option value="horror">Horror</option>
                            <option value="literary">Literary Fiction</option>
                            <option value="historical">Historical Fiction</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Tone</label>
                        <input type="text" id="tone" name="tone" placeholder="dark, hopeful, gritty, whimsical, satirical...">
                    </div>
                    <div class="form-group">
                        <label>Target Length</label>
                        <select id="target_length" name="target_length">
                            <option value="">-- Standard (60k words) --</option>
                            <option value="novella (30k)">Novella (30k words)</option>
                            <option value="standard (60k)">Standard Novel (60k words)</option>
                            <option value="epic (100k+)">Epic (100k+ words)</option>
                        </select>
                    </div>
                </div>
            </div>

            <!-- World & Setting -->
            <div class="section">
                <div class="section-header" onclick="toggleSection(this)">
                    <h3>World &amp; Setting</h3>
                    <span class="badge" id="badge-world">Optional</span>
                </div>
                <div class="section-content">
                    <div class="form-group">
                        <label>Setting</label>
                        <textarea id="setting" name="setting" placeholder="Near-future Tokyo, 2089. Neon-lit corporate dystopia meets traditional temples hidden in the urban sprawl..."></textarea>
                    </div>
                    <div class="form-group">
                        <label>World Rules</label>
                        <textarea id="world_rules" name="world_rules" placeholder="Memory reading requires physical contact. Memories can be bought/sold on the black market. The rich preserve memories in 'vaults'..."></textarea>
                        <p class="label-hint">What's possible/impossible? Magic system? Technology?</p>
                    </div>
                    <div class="form-group">
                        <label>Key Locations</label>
                        <textarea id="key_locations" name="key_locations" placeholder="- The Memory Exchange: Black market hub&#10;- Vault 7: Elite memory storage facility&#10;- The Blank District: Where the memory-wiped live"></textarea>
                    </div>
                </div>
            </div>

            <!-- Characters -->
            <div class="section">
                <div class="section-header" onclick="toggleSection(this)">
                    <h3>Characters</h3>
                    <span class="badge" id="badge-chars">Optional</span>
                </div>
                <div class="section-content">
                    <div class="form-group">
                        <label>Protagonist</label>
                        <textarea id="protagonist" name="protagonist" placeholder="Yuki Tanaka, 32, Memory Detective. Cold exterior, secretly afraid her own memories are fake. Wants truth about her past..."></textarea>
                        <p class="label-hint">Name, role, traits, goals, what blocks them</p>
                    </div>
                    <div class="form-group">
                        <label>Antagonist</label>
                        <textarea id="antagonist" name="antagonist" placeholder="The Archivist - runs the Memory Exchange. Knows Yuki's real past. Uses that knowledge to manipulate her..."></textarea>
                    </div>
                    <div class="form-group">
                        <label>Other Characters</label>
                        <textarea id="other_characters" name="other_characters" class="large" placeholder="- Kenji: Partner, comic relief, secretly in love with her&#10;- Dr. Sato: Created memory tech, now regrets it&#10;- The Ghost: Mysterious figure with no memories at all"></textarea>
                    </div>
                </div>
            </div>

            <!-- Plot & Structure -->
            <div class="section">
                <div class="section-header" onclick="toggleSection(this)">
                    <h3>Plot &amp; Structure</h3>
                    <span class="badge" id="badge-plot">Optional</span>
                </div>
                <div class="section-content">
                    <div class="form-group">
                        <label>Premise</label>
                        <textarea id="premise" name="premise" placeholder="What if your entire identity was a lie designed to make you the perfect weapon?"></textarea>
                        <p class="label-hint">The central "what if" of your story</p>
                    </div>
                    <div class="form-group">
                        <label>Central Conflict</label>
                        <textarea id="central_conflict" name="central_conflict" placeholder="Yuki must choose between the comfortable lie of her current life and the dangerous truth of who she really was."></textarea>
                    </div>
                    <div class="form-group">
                        <label>Key Plot Points</label>
                        <textarea id="key_plot_points" name="key_plot_points" class="large" placeholder="- Opening: Yuki reads a dying man's memory, sees her own face&#10;- Inciting incident: Hired to find someone who is herself&#10;- Midpoint: Discovers she was an assassin&#10;- Low point: Her partner was assigned to watch her&#10;- Climax: Confronts the Archivist, must choose which self to be"></textarea>
                    </div>
                    <div class="form-group">
                        <label>Subplots</label>
                        <textarea id="subplots" name="subplots" placeholder="- Romance: Feelings for Kenji despite knowing he was her handler&#10;- Mystery: Who ordered her memory wipe?"></textarea>
                    </div>
                </div>
            </div>

            <!-- Themes & Meaning -->
            <div class="section">
                <div class="section-header" onclick="toggleSection(this)">
                    <h3>Themes &amp; Deeper Meaning</h3>
                    <span class="badge" id="badge-themes">Optional</span>
                </div>
                <div class="section-content">
                    <div class="form-group">
                        <label>Themes</label>
                        <textarea id="themes" name="themes" placeholder="Identity, authenticity, technology ethics, found family, escaping vs embracing the past"></textarea>
                    </div>
                    <div class="form-group">
                        <label>Central Question</label>
                        <input type="text" id="central_question" name="central_question" placeholder="If our memories make us who we are, can we ever truly change?">
                    </div>
                    <div class="form-group">
                        <label>Motifs</label>
                        <textarea id="motifs" name="motifs" placeholder="Mirrors (identity), rain (cleansing), photographs (captured moments), locked doors (secrets)"></textarea>
                    </div>
                </div>
            </div>

            <!-- Style & Voice -->
            <div class="section">
                <div class="section-header" onclick="toggleSection(this)">
                    <h3>Style &amp; Voice</h3>
                    <span class="badge" id="badge-style">Optional</span>
                </div>
                <div class="section-content">
                    <div class="form-group">
                        <label>Writing Style</label>
                        <textarea id="writing_style" name="writing_style" placeholder="Sparse, noir-influenced prose. Short punchy sentences during action. First person present tense."></textarea>
                    </div>
                    <div class="form-group">
                        <label>Influences</label>
                        <input type="text" id="influences" name="influences" placeholder="Blade Runner meets Memento, with the emotional depth of Never Let Me Go">
                    </div>
                    <div class="form-group">
                        <label>Things to Avoid</label>
                        <textarea id="avoid" name="avoid" placeholder="No love triangles. No chosen one prophecy. No grimdark - keep some hope."></textarea>
                    </div>
                </div>
            </div>

            <!-- Strategic Guidance (from LLM analysis) -->
            <div class="section">
                <div class="section-header" onclick="toggleSection(this)">
                    <h3>Strategic Guidance</h3>
                    <span class="badge" id="badge-strategic">Optional</span>
                </div>
                <div class="section-content">
                    <p class="label-hint" style="margin-bottom: 20px; color: #9ca3af;">These fields capture market insights, craft guidance, and commercial notes to help the AI write more effectively.</p>

                    <div class="form-group">
                        <label>Market Positioning</label>
                        <textarea id="market_positioning" name="market_positioning" placeholder="Target subgenre (e.g., Dark Bratva Romance), reader expectations, comparable titles, KU optimization notes..."></textarea>
                    </div>
                    <div class="form-group">
                        <label>Beat Sheet / Pacing Notes</label>
                        <textarea id="beat_sheet" name="beat_sheet" class="large" placeholder="Opening (0-5%): Setup normal world...&#10;Inciting incident (10%): ...&#10;Threshold (25%): Enters new world...&#10;Midpoint (50%): Major shift...&#10;Low point (75%): All is lost...&#10;Climax (85%): ...&#10;Resolution: HEA/HFN..."></textarea>
                    </div>
                    <div class="form-group">
                        <label>Aesthetic Guide (Fashion, Luxury, Sensory)</label>
                        <textarea id="aesthetic_guide" name="aesthetic_guide" class="large" placeholder="Fashion: Brioni suits, D&G dresses, fur coats...&#10;Luxury: G-Wagon, Beluga vodka, penthouse...&#10;Smells: leather, gunpowder, cologne...&#10;Sounds: vault-door thud, accented whispers...&#10;Textures: silk, cold metal, rough hands..."></textarea>
                    </div>
                    <div class="form-group">
                        <label>Tropes to Execute</label>
                        <textarea id="tropes" name="tropes" class="large" placeholder="- Touch Her and Die: Before 50%, calm violence, immediate caretaking after&#10;- Who Did This To You: Cold rage, tends wound himself&#10;- Forced Proximity / Golden Cage: Luxurious captivity&#10;- Praise Kink: Specific to her body/actions, not generic"></textarea>
                    </div>
                    <div class="form-group">
                        <label>Dialogue Bank</label>
                        <textarea id="dialogue_bank" name="dialogue_bank" class="large" placeholder="Praise phrases: 'You take me so well', 'Good girl', 'Look at you...'&#10;Endearments: Zolotse (gold), Kotyonek (kitten), Moya dusha (my soul)&#10;Power lines: 'Touch her and I burn your world down'"></textarea>
                    </div>
                    <div class="form-group">
                        <label>Cultural Notes</label>
                        <textarea id="cultural_notes" name="cultural_notes" placeholder="Bratva hierarchy: Pakhan (boss), Brigadier (captain), Vor (thief)...&#10;Russian customs, language, stoicism, cultural details for authenticity..."></textarea>
                    </div>
                    <div class="form-group">
                        <label>Commercial Notes</label>
                        <textarea id="commercial_notes" name="commercial_notes" placeholder="Series potential, blurb hooks, mobile-first writing (short paragraphs), chapter cliffhangers, keyword strategy..."></textarea>
                    </div>
                </div>
            </div>
        </form>
    </div>

    <!-- Fixed Progress Bar -->
    <div class="progress-bar">
        <div class="progress-inner">
            <div class="progress-stats">
                <span id="filledCount">0</span> fields filled |
                AI will expand <span id="aiCount">21</span> story sections |
                <span style="color: #6b7280;">+ strategic guidance</span>
            </div>
            <div class="btn-group">
                <button class="btn btn-secondary" onclick="clearForm()">Clear All</button>
                <button class="btn btn-primary" onclick="createProject()">Create Project</button>
            </div>
        </div>
    </div>

    <!-- Success Modal -->
    <div class="success-modal" id="successModal">
        <div class="success-content">
            <h2>Project Created!</h2>
            <p>Your story seed has been saved and is ready for generation.</p>
            <div class="path" id="projectPath"></div>
            <p id="fieldStats"></p>
            <div class="btn-group" style="justify-content: center;">
                <button class="btn btn-secondary" onclick="closeModal()">Create Another</button>
                <a href="/projects" class="btn btn-primary">View Projects</a>
            </div>
        </div>
    </div>

    <script>
        // Track form state - core story fields
        const coreFields = [
            'idea', 'title', 'genre', 'tone', 'target_length',
            'setting', 'world_rules', 'key_locations',
            'protagonist', 'antagonist', 'other_characters',
            'premise', 'central_conflict', 'key_plot_points', 'subplots',
            'themes', 'central_question', 'motifs',
            'writing_style', 'influences', 'avoid'
        ];

        // Strategic guidance fields
        const strategicFields = [
            'market_positioning', 'beat_sheet', 'aesthetic_guide',
            'tropes', 'dialogue_bank', 'cultural_notes', 'commercial_notes'
        ];

        const fields = [...coreFields, ...strategicFields];

        function updateProgress() {
            let coreFilled = 0;
            let strategicFilled = 0;

            coreFields.forEach(field => {
                const el = document.getElementById(field);
                if (el && el.value && el.value.trim()) coreFilled++;
            });
            strategicFields.forEach(field => {
                const el = document.getElementById(field);
                if (el && el.value && el.value.trim()) strategicFilled++;
            });

            const totalFilled = coreFilled + strategicFilled;
            document.getElementById('filledCount').textContent = totalFilled;
            document.getElementById('aiCount').textContent = (coreFields.length - coreFilled);

            // Update section badges
            updateSectionBadge('badge-basic', ['title', 'genre', 'tone', 'target_length']);
            updateSectionBadge('badge-world', ['setting', 'world_rules', 'key_locations']);
            updateSectionBadge('badge-chars', ['protagonist', 'antagonist', 'other_characters']);
            updateSectionBadge('badge-plot', ['premise', 'central_conflict', 'key_plot_points', 'subplots']);
            updateSectionBadge('badge-themes', ['themes', 'central_question', 'motifs']);
            updateSectionBadge('badge-style', ['writing_style', 'influences', 'avoid']);
            updateSectionBadge('badge-strategic', strategicFields);
        }

        function updateSectionBadge(badgeId, fieldIds) {
            const badge = document.getElementById(badgeId);
            if (!badge) return;

            const filled = fieldIds.filter(id => {
                const el = document.getElementById(id);
                return el && el.value && el.value.trim();
            }).length;

            if (filled === fieldIds.length) {
                badge.className = 'badge filled';
                badge.textContent = 'Complete';
            } else if (filled > 0) {
                badge.className = 'badge filled';
                badge.textContent = filled + '/' + fieldIds.length;
            } else {
                badge.className = 'badge';
                badge.textContent = 'Optional';
            }
        }

        function toggleSection(header) {
            const content = header.nextElementSibling;
            content.classList.toggle('collapsed');
        }

        function copyTemplate() {
            const template = document.getElementById('jsonTemplate').textContent;

            // Try modern clipboard API first
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(template).then(() => {
                    showCopySuccess();
                }).catch(err => {
                    console.log('Clipboard API failed, trying fallback:', err);
                    copyFallback(template);
                });
            } else {
                copyFallback(template);
            }
        }

        function copyFallback(text) {
            // Fallback for older browsers or HTTP contexts
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.left = '-9999px';
            document.body.appendChild(textarea);
            textarea.select();
            try {
                document.execCommand('copy');
                showCopySuccess();
            } catch (err) {
                alert('Copy failed. Please select the template text manually and copy.');
            }
            document.body.removeChild(textarea);
        }

        function showCopySuccess() {
            const btn = document.getElementById('copyBtn');
            btn.textContent = 'Copied!';
            btn.style.background = '#10b981';
            setTimeout(() => {
                btn.textContent = 'Copy Template';
                btn.style.background = '#374151';
            }, 2000);
        }

        function parseJSON() {
            const text = document.getElementById('quickPaste').value.trim();
            if (!text) {
                alert('Please paste the filled JSON first.');
                return;
            }

            // Clean the input
            let cleanText = text;

            // Remove markdown code blocks (``` or ```json)
            var codeBlockRe = /^`{3}[a-z]*\\n?/;
            var endBlockRe = /\\n?`{3}$/;
            if (codeBlockRe.test(cleanText)) {
                cleanText = cleanText.replace(codeBlockRe, '').replace(endBlockRe, '');
            }
            cleanText = cleanText.trim();

            // Fix common LLM JSON mistakes
            // Fix empty values like "key":, -> "key": ""
            cleanText = cleanText.replace(/:\\s*,/g, ': "",');
            cleanText = cleanText.replace(/:\\s*}/g, ': ""}');
            // Fix trailing commas before } or ]
            cleanText = cleanText.replace(/,\\s*}/g, '}');
            cleanText = cleanText.replace(/,\\s*]/g, ']');

            console.log('Attempting to parse:', cleanText.substring(0, 200) + '...');

            try {
                const data = JSON.parse(cleanText);
                console.log('Parsed successfully. Keys:', Object.keys(data));

                let filledCount = 0;
                const results = [];

                fields.forEach(field => {
                    const el = document.getElementById(field);
                    if (!el) {
                        console.warn('No form element for field:', field);
                        return;
                    }

                    let value = data[field];

                    // Skip if not present
                    if (value === undefined || value === null) {
                        return;
                    }

                    // Convert objects/arrays to string
                    if (typeof value === 'object') {
                        if (Array.isArray(value)) {
                            value = value.map(item => {
                                if (typeof item === 'object') {
                                    return Object.entries(item).map(([k,v]) => k + ': ' + v).join(', ');
                                }
                                return String(item);
                            }).join('\\n');
                        } else {
                            value = Object.entries(value).map(([k,v]) => {
                                if (typeof v === 'object') {
                                    return k + ': ' + JSON.stringify(v);
                                }
                                return k + ': ' + v;
                            }).join('\\n');
                        }
                    }

                    // Convert to string
                    value = String(value).trim();

                    // Skip template placeholders - check for common placeholder patterns
                    const placeholderStarts = [
                        'REQUIRED:', 'Working title', 'Time, place', 'Important places',
                        'Name, age', 'Name, role', 'Supporting cast', 'The central',
                        'Opening, inciting', 'Secondary storylines', 'Core ideas',
                        'The philosophical', 'Recurring symbols', 'POV, tense',
                        'Comparable books', 'Tropes, elements', 'Target subgenre',
                        'Opening (5%)', 'Fashion brands', 'List key tropes',
                        'Signature phrases', 'Specific cultural', 'Series potential'
                    ];
                    const isPlaceholder = value === '' ||
                        value.includes(' | ') ||
                        value.indexOf('possible') === 6 ||
                        placeholderStarts.some(p => value.startsWith(p));

                    if (isPlaceholder) {
                        console.log('Skipping placeholder for:', field);
                        return;
                    }

                    el.value = value;
                    filledCount++;
                    results.push(field);
                    console.log('Filled:', field);
                });

                updateProgress();
                document.getElementById('quickPaste').value = '';

                if (filledCount > 0) {
                    alert('Success! Filled ' + filledCount + ' fields: ' + results.join(', '));
                } else {
                    alert('No fields were filled. Make sure you filled in the template values (not just left the placeholders).');
                }

            } catch (e) {
                console.error('JSON parse error:', e);
                alert('JSON parsing failed: ' + e.message + '. Make sure the text is valid JSON format.');
            }
        }

        function clearForm() {
            if (!confirm('Clear all fields?')) return;
            fields.forEach(field => {
                const el = document.getElementById(field);
                if (el) el.value = '';
            });
            updateProgress();
        }

        async function createProject() {
            const idea = document.getElementById('idea').value;
            if (!idea || !idea.trim()) {
                alert('Please enter at least your story idea.');
                document.getElementById('idea').focus();
                return;
            }

            const seedData = {};
            fields.forEach(field => {
                const el = document.getElementById(field);
                if (el && el.value && el.value.trim()) {
                    seedData[field] = el.value.trim();
                }
            });

            try {
                const response = await fetch('/api/v2/seed', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ seed: seedData, expand: true })
                });

                const result = await response.json();

                if (response.ok) {
                    document.getElementById('projectPath').textContent = result.project_path;
                    document.getElementById('fieldStats').textContent =
                        result.fields_provided + ' fields provided, ' + (result.fields_total - result.fields_provided) + ' will be AI-generated';
                    document.getElementById('successModal').classList.add('show');
                } else {
                    alert('Error: ' + (result.detail || 'Unknown error'));
                }
            } catch (error) {
                alert('Failed to create project: ' + error.message);
            }
        }

        function closeModal() {
            document.getElementById('successModal').classList.remove('show');
            clearForm();
        }

        // Add event listeners for form fields
        fields.forEach(field => {
            const el = document.getElementById(field);
            if (el) {
                el.addEventListener('input', updateProgress);
            }
        });

        // Add button event listeners
        document.getElementById('copyBtn').addEventListener('click', copyTemplate);
        document.getElementById('parseBtn').addEventListener('click', parseJSON);

        // Initial update
        updateProgress();
        console.log('WriterAI Seed page initialized. Fields tracked:', fields.length);
    </script>
</body>
</html>
"""

# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Run the web server."""
    import argparse
    parser = argparse.ArgumentParser(description="WriterAI Web Dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    uvicorn.run(
        "prometheus_novel.interfaces.web.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main()
