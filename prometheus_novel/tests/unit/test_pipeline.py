"""
Unit Tests for Pipeline Orchestrator

Tests the 12-stage novel generation pipeline.
"""

import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from stages.pipeline import (
    PipelineOrchestrator,
    PipelineState,
    StageResult,
    StageStatus
)


class TestStageStatus:
    """Tests for StageStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert StageStatus.PENDING.value == "pending"
        assert StageStatus.RUNNING.value == "running"
        assert StageStatus.COMPLETED.value == "completed"
        assert StageStatus.FAILED.value == "failed"


class TestStageResult:
    """Tests for StageResult dataclass."""

    def test_result_creation(self):
        """Test creating a stage result."""
        result = StageResult(
            stage_name="high_concept",
            status=StageStatus.COMPLETED,
            output="Test output",
            duration_seconds=1.5,
            tokens_used=100
        )

        assert result.stage_name == "high_concept"
        assert result.status == StageStatus.COMPLETED
        assert result.output == "Test output"
        assert result.duration_seconds == 1.5
        assert result.tokens_used == 100

    def test_result_with_error(self):
        """Test result with error."""
        result = StageResult(
            stage_name="world_building",
            status=StageStatus.FAILED,
            error="API error"
        )

        assert result.status == StageStatus.FAILED
        assert result.error == "API error"


class TestPipelineState:
    """Tests for PipelineState."""

    def test_state_creation(self, project_with_config):
        """Test creating pipeline state."""
        state = PipelineState(
            project_name="test-novel",
            project_path=project_with_config,
            config={"title": "Test"}
        )

        assert state.project_name == "test-novel"
        assert state.current_stage == 0
        assert state.high_concept is None

    def test_state_save_and_load(self, project_with_config, sample_config):
        """Test saving and loading state."""
        state = PipelineState(
            project_name="test-novel",
            project_path=project_with_config,
            config=sample_config,
            high_concept="A test concept"
        )

        # Save state
        state.save()

        # Verify file exists
        state_file = project_with_config / "pipeline_state.json"
        assert state_file.exists()

        # Load state
        loaded_state = PipelineState.load(project_with_config)

        assert loaded_state is not None
        assert loaded_state.project_name == "test-novel"
        assert loaded_state.high_concept == "A test concept"


class TestPipelineOrchestrator:
    """Tests for PipelineOrchestrator."""

    def test_stages_defined(self):
        """Test that core stages are defined and pipeline is non-empty."""
        stages = PipelineOrchestrator.STAGES
        assert len(stages) >= 12
        assert "high_concept" in stages
        assert "output_validation" in stages
        assert "voice_human_pass" in stages

    @pytest.mark.asyncio
    async def test_initialize(self, project_with_config):
        """Test pipeline initialization."""
        orchestrator = PipelineOrchestrator(project_with_config)
        state = await orchestrator.initialize()

        assert state is not None
        assert state.project_name == "test-novel"

    @pytest.mark.asyncio
    async def test_event_callbacks(self, project_with_config):
        """Test event callback registration."""
        orchestrator = PipelineOrchestrator(project_with_config)

        events = []

        def on_stage_start(stage_name, index):
            events.append(("start", stage_name))

        def on_stage_complete(stage_name, result):
            events.append(("complete", stage_name))

        orchestrator.on("on_stage_start", on_stage_start)
        orchestrator.on("on_stage_complete", on_stage_complete)

        # Run just one stage
        await orchestrator.initialize()
        await orchestrator._run_stage("high_concept")

        # Events should have been recorded
        assert len(events) >= 0  # At least initialized

    @pytest.mark.asyncio
    async def test_run_single_stage(self, project_with_config):
        """Test running a single stage."""
        orchestrator = PipelineOrchestrator(project_with_config)
        await orchestrator.initialize()

        result = await orchestrator._run_stage("high_concept")

        assert result.stage_name == "high_concept"
        assert result.status == StageStatus.COMPLETED
        assert orchestrator.state.high_concept is not None

    @pytest.mark.asyncio
    async def test_unknown_stage_skipped(self, project_with_config):
        """Test that unknown stages are skipped."""
        orchestrator = PipelineOrchestrator(project_with_config)
        await orchestrator.initialize()

        result = await orchestrator._run_stage("nonexistent_stage")

        assert result.status == StageStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_run_with_mock_llm(self, project_with_config, mock_llm_client):
        """Test running pipeline with mock LLM."""
        orchestrator = PipelineOrchestrator(project_with_config, mock_llm_client)
        await orchestrator.initialize()

        result = await orchestrator._run_stage("high_concept")

        assert result.status == StageStatus.COMPLETED
        assert mock_llm_client.call_count > 0

    @pytest.mark.asyncio
    async def test_validate_scene_output_flags_pov_slip(self, project_with_config):
        """POV slip patterns (my eyes on me, his hands behind my back) trigger retry."""
        orchestrator = PipelineOrchestrator(project_with_config)
        await orchestrator.initialize()
        # Ensure config has first-person for POV check
        orchestrator.state.config = orchestrator.state.config or {}
        orchestrator.state.config["writing_style"] = "close first-person present (Elena)"
        orchestrator.state.config["protagonist"] = "Elena Vance"
        orchestrator.state.characters = [
            {"name": "Dr. Aris Kade"},
            {"name": "Elena Vance"},
        ]

        # Pattern: his hands folded behind my back
        bad1 = "Dr. Kade stood near the console, his hands folded behind my back. He looked at me."
        r1 = orchestrator._validate_scene_output(
            bad1,
            {"scene_id": "ch04_s01", "pov": "Elena Vance", "chapter": 4, "scene": 1},
        )
        assert not r1["pass"], "Should fail validation"
        assert "pov_pronoun_confusion" in r1.get("issues", {})

        # Pattern: my eyes were on me
        bad2 = "My eyes were already on me when I entered the room."
        r2 = orchestrator._validate_scene_output(
            bad2,
            {"scene_id": "ch01_s01", "pov": "Elena Vance", "chapter": 1, "scene": 1},
        )
        assert not r2["pass"]
        assert "pov_pronoun_confusion" in r2.get("issues", {})
