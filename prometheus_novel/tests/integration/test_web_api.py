"""
Integration Tests for Web API

Tests the FastAPI web application endpoints.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, test_client):
        """Test health check returns healthy status."""
        response = test_client.get("/api/v2/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestProjectsAPI:
    """Tests for projects API endpoints."""

    def test_list_projects_empty(self, test_client):
        """Test listing projects when none exist."""
        response = test_client.get("/api/v2/projects")

        assert response.status_code == 200
        data = response.json()
        assert "projects" in data

    def test_create_project(self, test_client):
        """Test creating a new project."""
        response = test_client.post(
            "/api/v2/projects",
            json={
                "name": "test-project",
                "title": "Test Project",
                "genre": "sci-fi",
                "synopsis": "A test project"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "created"

    def test_create_project_no_name(self, test_client):
        """Test creating project without name fails."""
        response = test_client.post(
            "/api/v2/projects",
            json={"title": "No Name Project"}
        )

        assert response.status_code == 400


class TestIdeasAPI:
    """Tests for ideas API endpoints."""

    def test_list_ideas(self, test_client):
        """Test listing ideas."""
        response = test_client.get("/api/v2/ideas")

        assert response.status_code == 200
        data = response.json()
        assert "ideas" in data

    def test_save_idea(self, test_client):
        """Test saving a new idea."""
        response = test_client.post(
            "/api/v2/ideas",
            json={
                "content": "A great story idea",
                "tags": ["sci-fi", "adventure"]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "saved"
        assert data["idea"]["content"] == "A great story idea"


class TestSettingsAPI:
    """Tests for settings API endpoints."""

    def test_get_settings(self, test_client):
        """Test getting settings."""
        response = test_client.get("/api/v2/settings")

        assert response.status_code == 200
        data = response.json()
        assert "default_model" in data

    def test_update_settings(self, test_client):
        """Test updating settings."""
        response = test_client.post(
            "/api/v2/settings",
            json={"budget_usd": 200.0}
        )

        assert response.status_code == 200


class TestDashboardPages:
    """Tests for dashboard HTML pages."""

    def test_dashboard_page(self, test_client):
        """Test main dashboard page loads."""
        response = test_client.get("/")

        assert response.status_code == 200
        assert "WriterAI" in response.text

    def test_projects_page(self, test_client):
        """Test projects page loads."""
        response = test_client.get("/projects")

        assert response.status_code == 200
        assert "Projects" in response.text or "Project" in response.text

    def test_ideas_page(self, test_client):
        """Test ideas page loads."""
        response = test_client.get("/ideas")

        assert response.status_code == 200
        assert "Ideas" in response.text or "Idea" in response.text

    def test_settings_page(self, test_client):
        """Test settings page loads."""
        response = test_client.get("/settings")

        assert response.status_code == 200
        assert "Settings" in response.text
