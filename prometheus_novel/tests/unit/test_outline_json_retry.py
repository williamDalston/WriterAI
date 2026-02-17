"""Unit tests for T1 outline JSON retry/repair: raw failure, valid batch, repair path."""

import sys
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from stages.pipeline import (
    _is_raw_failure,
    _is_valid_outline_batch,
    extract_json_robust,
    PipelineOrchestrator,
    PipelineState,
)


def test_is_raw_failure_dict():
    """Dict with 'raw' key is failure."""
    assert _is_raw_failure({"raw": "some text"}) is True
    assert _is_raw_failure({}) is False
    assert _is_raw_failure({"chapters": []}) is False


def test_is_raw_failure_list_of_raw():
    """List of single dict with 'raw' is failure (extract_json_robust fallback)."""
    assert _is_raw_failure([{"raw": "truncated json..."}]) is True
    assert _is_raw_failure([{"chapter": 1, "scenes": []}]) is False


def test_is_raw_failure_none():
    """None is failure."""
    assert _is_raw_failure(None) is True


def test_is_valid_outline_batch_rejects_raw():
    """Raw wrapper must not be accepted as valid."""
    assert _is_valid_outline_batch([{"raw": "x"}]) is False
    assert _is_valid_outline_batch({"raw": "x"}) is False


def test_is_valid_outline_batch_accepts_chapters():
    """Chapters with scenes list is valid."""
    valid = [
        {"chapter": 1, "scenes": [{"scene": 1, "scene_name": "A"}]},
        {"chapter": 2, "scenes": [{"scene": 1}]},
    ]
    assert _is_valid_outline_batch(valid) is True


def test_is_valid_outline_batch_rejects_empty():
    """Empty list is invalid."""
    assert _is_valid_outline_batch([]) is False


def test_is_valid_outline_batch_rejects_no_scenes():
    """Chapter without scenes list is invalid."""
    assert _is_valid_outline_batch([{"chapter": 1}]) is False
    assert _is_valid_outline_batch([{"chapter": 1, "scenes": "not a list"}]) is False


def test_extract_json_robust_returns_raw_on_failure():
    """extract_json_robust returns raw wrapper on parse failure (never raises)."""
    result = extract_json_robust("not valid json at all {{{", expect_array=True)
    assert _is_raw_failure(result) is True
    assert isinstance(result, list)
    assert len(result) == 1
    assert "raw" in result[0]


def test_retry_loop_would_not_break_on_raw():
    """Simulated: if retry loop used truthy check, it would break incorrectly.
    With _is_valid_outline_batch, it correctly rejects."""
    fake_result = extract_json_robust("garbage {]", expect_array=True)
    assert fake_result  # truthy!
    assert _is_valid_outline_batch(fake_result) is False  # correctly rejected


@pytest.mark.asyncio
async def test_raw_then_valid_retry_recovery(project_with_config):
    """Integration-style: extract_json_robust returns raw on attempt 0, valid on attempt 1.
    Assert retries happen, recoveries recorded, attempts==2, success True.
    Catches regressions where 'if batch: break' could be reintroduced."""
    # Setup state with minimal planning data for 1-chapter outline
    config = {
        "project_name": "retry-test",
        "title": "Retry Test",
        "genre": "sci-fi",
        "synopsis": "Test",
        "protagonist": "Hero",
        "target_length": "novelette (15k)",
        "writing_style": "single pov",
    }
    state = PipelineState(
        project_name="retry-test",
        project_path=project_with_config,
        config=config,
        high_concept="A test concept",
        beat_sheet=[{"act": 1, "beat": "Setup"}],
        characters=[{"name": "Hero", "role": "protagonist"}],
        target_chapters=1,
        scenes_per_chapter=1,
        motif_map={},
    )
    state.calculate_targets()
    state.target_chapters = 1  # Override so we have exactly 1 batch (ch 1 only)

    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.content = '{"chapters":[{"chapter":1,"scenes":[{"scene":1}]}]}'
    mock_resp.input_tokens = 100
    mock_resp.output_tokens = 50
    mock_client.generate.return_value = mock_resp

    orchestrator = PipelineOrchestrator(
        project_with_config,
        llm_client=mock_client,
        llm_clients={"gpt": mock_client},
    )
    orchestrator.state = state

    raw_fail = [{"raw": "truncated or bad json"}]
    valid_batch = [{"chapter": 1, "chapter_title": "Ch1", "scenes": [{"scene": 1, "scene_name": "Start"}]}]

    with patch("stages.pipeline.extract_json_robust", side_effect=[raw_fail, valid_batch]):
        result = await orchestrator._run_stage("master_outline")

    assert result.status.value == "completed"
    assert orchestrator.state.outline_json_report is not None
    batches = orchestrator.state.outline_json_report.get("batches", [])
    assert len(batches) == 1
    b = batches[0]
    assert b["attempts_made"] == 2
    assert b["parse_failures"] >= 1
    assert b["success"] is True
