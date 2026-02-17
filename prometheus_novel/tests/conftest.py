"""
Pytest Configuration and Fixtures

Provides common fixtures for testing the WriterAI system.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from typing import Generator, AsyncGenerator
import yaml
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# Async Support
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Project Fixtures
# ============================================================================

@pytest.fixture
def temp_project_dir() -> Generator[Path, None, None]:
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test-project"
        project_dir.mkdir()
        (project_dir / "drafts").mkdir()
        (project_dir / "output").mkdir()
        (project_dir / "memory").mkdir()
        yield project_dir


@pytest.fixture
def sample_config() -> dict:
    """Sample project configuration."""
    return {
        "project_name": "test-novel",
        "title": "Test Novel",
        "genre": "sci-fi",
        "synopsis": "A test story about testing",
        "protagonist": "A scientist who discovers AI consciousness",
        "target_length": "standard (60k)",
        "themes": ["technology", "humanity"],
        "conflicts": ["man vs machine"],
        "archetypes": ["scientist", "AI"],
        "budget_usd": 10,
        "model_defaults": {
            "local_model": "gpt-4o-mini",
            "api_model": "gpt-4o-mini",
            "critic_model": "gpt-4o-mini",
            "fallback_model": "gpt-3.5-turbo"
        },
        "stage_model_map": {
            "high_concept": "api_model",
            "beat_sheet": "api_model",
            "write_scene": "api_model",
            "self_refine": "critic_model"
        }
    }


@pytest.fixture
def project_with_config(temp_project_dir: Path, sample_config: dict) -> Path:
    """Create a project directory with config file."""
    config_file = temp_project_dir / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(sample_config, f)
    return temp_project_dir


# ============================================================================
# Smoke Test Fixtures (for pytest -m smoke)
# ============================================================================

@pytest.fixture
def smoke_project() -> Generator[Path, None, None]:
    """Materialize a temporary project from embedded smoke config.
    Smoke tests use this instead of hardcoded data/projects/<name> paths.
    """
    fixtures_dir = PROJECT_ROOT / "tests" / "fixtures"
    config_src = fixtures_dir / "smoke_config.yaml"
    if not config_src.exists():
        pytest.skip(f"Smoke fixture not found: {config_src}")

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "smoke-test-project"
        project_dir.mkdir()
        (project_dir / "drafts").mkdir()
        (project_dir / "output").mkdir()
        (project_dir / "memory").mkdir()

        with open(config_src) as f:
            config = yaml.safe_load(f)
        with open(project_dir / "config.yaml", "w") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

        yield project_dir


# ============================================================================
# Mock LLM Client
# ============================================================================

class MockLLMClient:
    """Mock LLM client for testing."""

    def __init__(self, model_name: str = "mock-model"):
        self.model_name = model_name
        self.call_count = 0
        self.last_prompt = None

    async def generate(self, prompt: str, **kwargs) -> "MockLLMResponse":
        self.call_count += 1
        self.last_prompt = prompt

        # Return mock response
        from prometheus_lib.llm.clients import LLMResponse
        return LLMResponse(
            content=f"Mock response for: {prompt[:50]}...",
            model=self.model_name,
            input_tokens=len(prompt) // 4,
            output_tokens=50,
            finish_reason="stop"
        )

    async def generate_stream(self, prompt: str, **kwargs):
        self.call_count += 1
        self.last_prompt = prompt

        words = f"Mock streaming response for: {prompt[:30]}...".split()
        for word in words:
            yield word + " "


@pytest.fixture
def mock_llm_client() -> MockLLMClient:
    """Provide a mock LLM client."""
    return MockLLMClient()


# ============================================================================
# Web App Fixtures
# ============================================================================

@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    from fastapi.testclient import TestClient
    from prometheus_novel.interfaces.web.app import app
    return TestClient(app)


@pytest.fixture
async def async_test_client():
    """Create an async test client for the FastAPI app."""
    from httpx import AsyncClient
    from prometheus_novel.interfaces.web.app import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
