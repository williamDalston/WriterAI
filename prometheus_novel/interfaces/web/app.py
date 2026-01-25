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

# Setup logging
logger = setup_logging("writerai.web")

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
            "default_model": "gpt-4o-mini",
            "budget_usd": 100.0,
            "theme": "dark"
        }

    def load_projects(self):
        """Load existing projects from disk."""
        projects_dir = PROJECT_ROOT / "data" / "projects"
        if projects_dir.exists():
            for project_path in projects_dir.iterdir():
                if project_path.is_dir():
                    config_file = project_path / "config.yaml"
                    if config_file.exists():
                        self.projects[project_path.name] = {
                            "name": project_path.name,
                            "path": str(project_path),
                            "status": "ready"
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

# CORS middleware for browser plugin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

    if not project_name:
        raise HTTPException(status_code=400, detail="Project name required")

    # Create project directory
    project_dir = PROJECT_ROOT / "data" / "projects" / project_name
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
    with open(config_file, "w") as f:
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
    # Mask API keys
    safe_settings = {**app_state.settings}
    if safe_settings.get("openai_api_key"):
        safe_settings["openai_api_key"] = "sk-..." + safe_settings["openai_api_key"][-4:]
    if safe_settings.get("google_api_key"):
        safe_settings["google_api_key"] = "..." + safe_settings["google_api_key"][-4:]
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
    """Run novel generation in background."""
    try:
        stages = [
            "high_concept", "world_building", "beat_sheet",
            "character_profiles", "scene_planning", "drafting",
            "self_refinement", "continuity_audit", "polish"
        ]

        for i, stage in enumerate(stages):
            app_state.active_generations[generation_id].update({
                "current_stage": stage,
                "progress": int((i / len(stages)) * 100)
            })

            # Broadcast progress
            await manager.broadcast({
                "type": "generation_progress",
                "generation_id": generation_id,
                "project": project_name,
                "stage": stage,
                "progress": int((i / len(stages)) * 100)
            })

            # Simulate stage processing
            await asyncio.sleep(1)

        app_state.active_generations[generation_id].update({
            "status": "completed",
            "progress": 100
        })

        await manager.broadcast({
            "type": "generation_complete",
            "generation_id": generation_id,
            "project": project_name
        })

    except Exception as e:
        logger.error(f"Generation failed: {e}")
        app_state.active_generations[generation_id].update({
            "status": "failed",
            "error": str(e)
        })


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
                <a href="/projects">Projects</a>
                <a href="/ideas">Ideas</a>
                <a href="/settings">Settings</a>
            </nav>
        </header>

        <section class="hero">
            <h2>AI-Powered Novel Generation</h2>
            <p>Transform your ideas into publication-ready novels</p>
            <a href="/projects" class="btn">Start New Project</a>
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
        .status-generating { background: #f59e0b; color: #fff; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>WriterAI</h1>
            <nav>
                <a href="/">Dashboard</a>
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
                <div class="project-card">
                    <div>
                        <h3>${p.name}</h3>
                        <p style="color: #9ca3af;">${p.path}</p>
                    </div>
                    <span class="project-status status-${p.status}">${p.status}</span>
                </div>
            `).join('');
        }

        loadProjects();
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
                    <p>${idea.content}</p>
                    <div class="idea-meta">Source: ${idea.source}</div>
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
                    <option value="gpt-4o-mini">GPT-4o Mini (Fast, Cheap)</option>
                    <option value="gpt-4o">GPT-4o (Quality)</option>
                    <option value="gpt-4-turbo">GPT-4 Turbo</option>
                    <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
                </select>
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

# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Run the web server."""
    import argparse
    parser = argparse.ArgumentParser(description="WriterAI Web Dashboard")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
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
