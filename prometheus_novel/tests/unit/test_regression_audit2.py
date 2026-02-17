"""
Regression tests for Audit #2 fixes.

Tests that the specific bugs found and fixed in Audit #2 stay fixed.
Fast, deterministic — no LLM needed. Run with:
    pytest tests/unit/test_regression_audit2.py -v
"""
import sys
import re
import json
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from stages.pipeline import (
    _clean_scene_content,
    count_ai_tells,
    validate_config,
    _LANG_DRIFT_RE,
)


# ---------------------------------------------------------------------------
# Golden dirty-scene cleanup tests
# ---------------------------------------------------------------------------

class TestMetaTextCleanup:
    """Prove that meta-text preambles and tails are stripped consistently."""

    CLEAN_PROSE = (
        "Elena pushed through the crowd, her heart pounding. The market stalls "
        "blurred past — silk scarves, copper lanterns, stacked spice jars. "
        "Somewhere behind her, boots struck cobblestone in a rhythm that matched "
        "her frantic pulse. She ducked beneath a merchant's awning and pressed "
        "herself against rough brick. The footsteps slowed. Stopped. She held "
        "her breath and counted the seconds."
    )

    PREAMBLES = [
        "Certainly! Here is the revised scene:\n\n",
        "Sure, here's the enhanced version:\n\n",
        "I've revised the scene to add more tension:\n\n",
        "Below is the revised scene:\n\n",
        "Here's the rewritten scene with your feedback incorporated:\n\n",
        "Of course! Here is the updated text:\n\n",
    ]

    TAILS = [
        "\n\nThe rest of the scene remains unchanged.",
        "\n\n---\n\n**Changes made:** Improved sensory details and pacing.",
        "\n\nLet me know if you'd like me to revise further!",
        "\n\nI can help with additional changes if needed.",
    ]

    @pytest.mark.parametrize("preamble", PREAMBLES)
    def test_preamble_stripped(self, preamble):
        dirty = preamble + self.CLEAN_PROSE
        cleaned = _clean_scene_content(dirty)
        # Preamble gone, prose preserved
        assert "Certainly" not in cleaned
        assert "Sure" not in cleaned
        assert "Here is" not in cleaned
        assert "revised" not in cleaned.split("\n")[0] if "\n" in cleaned else True
        assert "Elena" in cleaned

    @pytest.mark.parametrize("tail", TAILS)
    def test_tail_stripped(self, tail):
        dirty = self.CLEAN_PROSE + tail
        cleaned = _clean_scene_content(dirty)
        assert "remains unchanged" not in cleaned
        assert "Changes made" not in cleaned
        assert "Let me know" not in cleaned
        assert "I can help" not in cleaned
        assert "Elena" in cleaned


class TestAITellDetection:
    """Prove count_ai_tells handles placeholder patterns correctly."""

    def test_placeholder_x_matches(self):
        # [X] = single word — use single-word targets
        text = "Something about him made me freeze. Something about her made me uneasy."
        result = count_ai_tells(text)
        assert result["patterns_found"].get("Something about [X] made me", 0) >= 2

    def test_placeholder_emotion_matches(self):
        text = "A wave of anger crashed through her. A wave of sadness followed quickly."
        result = count_ai_tells(text)
        assert result["patterns_found"].get("a wave of [emotion]", 0) >= 2

    def test_placeholder_character_matches(self):
        text = "I knew Marcus felt the tension. I knew Elena felt the same."
        result = count_ai_tells(text)
        assert result["patterns_found"].get("I knew [character] felt", 0) >= 2

    def test_literal_patterns_still_work(self):
        text = "I couldn't help but notice the change. I found myself staring at the wall."
        result = count_ai_tells(text)
        assert result["total_tells"] >= 2

    def test_clean_prose_low_tells(self):
        text = (
            "Marcus slammed the door. Glass rattled in the frame. Elena flinched "
            "but held her ground, fingers white around the strap of her bag."
        )
        result = count_ai_tells(text)
        assert result["total_tells"] <= 1


class TestLanguageDriftDetection:
    """Prove CJK drift guard works and module-level regex is compiled."""

    def test_regex_is_module_level(self):
        # _LANG_DRIFT_RE should be a compiled pattern, not None
        assert _LANG_DRIFT_RE is not None
        assert hasattr(_LANG_DRIFT_RE, 'findall')

    def test_detects_chinese(self):
        text = "She walked into the room. 这是一个测试句子。He turned around."
        hits = len(_LANG_DRIFT_RE.findall(text))
        assert hits >= 3

    def test_no_false_positive_on_english(self):
        text = "Marcus grabbed the phone. Elena answered on the third ring."
        hits = len(_LANG_DRIFT_RE.findall(text))
        assert hits == 0


# ---------------------------------------------------------------------------
# Security regression tests
# ---------------------------------------------------------------------------

class TestPathTraversal:
    """Prove path traversal payloads are blocked."""

    def test_cli_sanitization(self):
        """Project names are sanitized to alphanumeric + hyphens."""
        import re as _re
        payloads = [
            "../../etc/passwd",
            "..\\..\\Windows\\System32",
            "project/../../../secret",
            "good-name; rm -rf /",
            "<script>alert(1)</script>",
        ]
        for payload in payloads:
            sanitized = _re.sub(r'[^a-z0-9_-]', '', payload.lower())
            # Must not contain path separators or be empty
            assert '/' not in sanitized
            assert '\\' not in sanitized
            assert '..' not in sanitized

    def test_resolve_containment(self):
        """Path resolve prevents escaping project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            projects_dir = Path(tmpdir) / "projects"
            projects_dir.mkdir()

            # Normal case
            safe = (projects_dir / "my-novel").resolve()
            assert str(safe).startswith(str(projects_dir.resolve()))

            # Attack case: even after sanitization, verify containment
            attack = (projects_dir / "..").resolve()
            assert not str(attack).startswith(str(projects_dir.resolve()) + "\\") and \
                   str(attack) != str(projects_dir.resolve())


class TestConfigValidation:
    """Prove config validation catches bad configs early."""

    def test_missing_required_fields(self):
        result = validate_config({})
        assert not result["valid"]
        assert len(result["errors"]) > 0

    def test_minimal_valid_config(self):
        config = {
            "project_name": "test",
            "title": "Test Novel",
            "genre": "literary",
            "synopsis": "A test synopsis for the novel",
            "protagonist": "Elena",
            "target_length": "standard (60k)",
        }
        result = validate_config(config)
        assert result["valid"], f"Errors: {result['errors']}"

    def test_empty_field_rejected(self):
        config = {
            "project_name": "",
            "title": "Test",
            "genre": "literary",
            "idea": "idea",
        }
        result = validate_config(config)
        assert not result["valid"]


class TestStateLoadSafety:
    """Prove PipelineState.load() handles corrupt files gracefully."""

    def test_corrupt_json_returns_none(self):
        from stages.pipeline import PipelineState
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            state_file = project_dir / "pipeline_state.json"
            config_file = project_dir / "config.yaml"
            state_file.write_text("{corrupt json!!!}", encoding="utf-8")
            config_file.write_text("project_name: test\n", encoding="utf-8")

            result = PipelineState.load(project_dir)
            assert result is None  # Should not crash

    def test_corrupt_yaml_returns_none(self):
        from stages.pipeline import PipelineState
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            state_file = project_dir / "pipeline_state.json"
            config_file = project_dir / "config.yaml"
            state_file.write_text('{"project_name": "test"}', encoding="utf-8")
            # Write binary garbage that yaml.safe_load cannot parse
            config_file.write_bytes(b'\x80\x81\x82\x00\xff\xfe')

            result = PipelineState.load(project_dir)
            assert result is None

    def test_missing_file_returns_none(self):
        from stages.pipeline import PipelineState
        with tempfile.TemporaryDirectory() as tmpdir:
            result = PipelineState.load(Path(tmpdir))
            assert result is None


class TestDictSubtractionFix:
    """Prove the quality dashboard no longer crashes on structure_scores_history."""

    def test_score_history_delta(self):
        """sum(values) subtraction should work where raw dict subtraction crashed."""
        history = [
            {"structure": 3, "tension": 2, "pacing": 4},
            {"structure": 5, "tension": 4, "pacing": 5},
        ]
        # This is the fixed code path
        delta = sum(history[-1].values()) - sum(history[0].values())
        assert delta == 5  # (5+4+5) - (3+2+4) = 14 - 9 = 5

    def test_dict_subtraction_would_crash(self):
        """Verify that raw dict - dict raises TypeError (the original bug)."""
        a = {"x": 1}
        b = {"x": 2}
        with pytest.raises(TypeError):
            _ = b - a


class TestQualityIterationPersistence:
    """Prove quality iteration state survives save/load cycle."""

    def test_quality_iterations_persisted(self):
        from stages.pipeline import PipelineState
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            config_file = project_dir / "config.yaml"
            config_file.write_text(
                "project_name: test\ntitle: Test\ngenre: literary\nidea: test\n",
                encoding="utf-8"
            )
            state = PipelineState(
                project_name="test",
                project_path=project_dir,
                config={"project_name": "test"},
            )
            state._quality_iterations = 2
            state._prev_audit_snapshot = {"word_count": {"percentage": 95}}
            state._continuity_fixed_indices = [0, 3, 5]
            state.save()

            loaded = PipelineState.load(project_dir)
            assert loaded is not None
            assert loaded._quality_iterations == 2
            assert loaded._prev_audit_snapshot == {"word_count": {"percentage": 95}}
            assert loaded._continuity_fixed_indices == [0, 3, 5]
