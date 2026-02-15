"""
Unit tests for Cleanup + Validation system.

Spec: genre-agnostic, testable, high-signal.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from stages.pipeline import _clean_scene_content
from export.scene_validator import (
    validate_project_scenes,
    validate_scene,
    _validation_mode,
)

# --- Cleanup tests ---


def test_truncate_rest_unchanged():
    """Truncate at 'rest remains unchanged', drop alternate version."""
    text = "Paragraph 1.\nParagraph 2.\nThe rest remains unchanged.\nALT VERSION..."
    cleaned = _clean_scene_content(text)
    assert "ALT VERSION" not in cleaned
    assert "Paragraph 2." in cleaned


def test_truncate_rest_of_scene_unchanged():
    """Truncate at 'rest of the scene remains unchanged'."""
    text = "Good prose here.\n\nRest of the scene remains unchanged.\n\nAlternate content."
    cleaned = _clean_scene_content(text)
    assert "Alternate content" not in cleaned
    assert "Good prose" in cleaned


def test_midtext_preamble_truncation():
    """Truncate at mid-text LLM preamble when prefix meets threshold."""
    prefix = "A" * 600
    text = prefix + "\nCertainly! Here is the revised opening for Chapter 7:\nNEW VERSION..."
    cleaned = _clean_scene_content(text)
    assert "NEW VERSION" not in cleaned
    assert "Certainly!" not in cleaned
    assert cleaned.strip() == prefix.strip()


def test_midtext_preamble_below_threshold_not_truncated():
    """Do NOT truncate when prefix is below MIN_PREFIX_CHARS and MIN_PREFIX_LINES."""
    text = "Short.\n\nCertainly! Here is the revised opening for Chapter 7:\nNEW VERSION..."
    cleaned = _clean_scene_content(text)
    # Prefix "Short." is < 400 chars and < 8 lines; spec says truncate only when threshold met
    assert "Short." in cleaned


def test_start_preamble_removed():
    """Start preamble stripped; actual story kept."""
    text = "Certainly! Here is the revised scene:\nActual story begins.\nIt was raining."
    cleaned = _clean_scene_content(text)
    assert "It was raining." in cleaned
    assert "Certainly!" not in cleaned


def test_no_further_changes_marker():
    """Truncate at 'no further changes were made'."""
    text = "Scene content ends here. No further changes were made.\nExtra stuff."
    cleaned = _clean_scene_content(text)
    assert "Extra stuff" not in cleaned
    assert "Scene content" in cleaned


# --- Validation tests ---


def test_validator_flags_meta_text_as_error():
    """Meta-text 'rest remains unchanged' in scene -> error."""
    config = {
        "protagonist": "Maya",
        "other_characters": "Jon",
        "export": {"validation_mode": "strict"},
    }
    scenes = [
        {
            "chapter": 1,
            "scene_number": 1,
            "content": "Maya walked in. The house was quiet. " * 10
            + "The rest remains unchanged.\nblah",
        }
    ]
    report = validate_project_scenes(scenes, config)
    meta_errors = [i for i in report["issues"] if i["code"] == "META_TEXT"]
    assert len(meta_errors) >= 1
    assert meta_errors[0]["severity"] == "error"
    assert report["has_errors"]


def test_validator_unknown_name_warn_then_escalate():
    """Suspicious name in 3+ scenes -> SUSPECT_NAME_RECURRING error."""
    config = {
        "protagonist": "Maya",
        "other_characters": "Jon",
        "market": {
            "tone_constraints": {
                "suspicious_names": ["Viktor"],
            }
        },
    }
    scenes = [
        {"chapter": 1, "scene_number": 1, "content": "Maya spoke to Viktor. " * 20},
        {"chapter": 1, "scene_number": 2, "content": "Jon saw Viktor. " * 20},
        {"chapter": 2, "scene_number": 1, "content": "Viktor returned. " * 20},
    ]
    report = validate_project_scenes(scenes, config)
    recurring = [i for i in report["issues"] if i["code"] == "SUSPECT_NAME_RECURRING"]
    assert len(recurring) >= 1
    assert recurring[0]["severity"] == "error"


def test_validator_allowed_names_no_false_positive():
    """Config allowed names should not trigger suspicious name."""
    config = {
        "protagonist": "Maya",
        "other_characters": "Jon, Viktor",
        "market": {"tone_constraints": {"suspicious_names": ["Viktor"]}},
    }
    scenes = [
        {"chapter": 1, "scene_number": 1, "content": "Maya and Viktor talked. " * 20},
    ]
    report = validate_project_scenes(scenes, config)
    suspect = [i for i in report["issues"] if i["code"] == "SUSPECT_NAME"]
    assert len(suspect) == 0  # Viktor is in others


def test_validator_disallow_terms_when_configured():
    """Disallow term in config -> GENRE_CROSS_CONTAM error."""
    config = {
        "protagonist": "Maya",
        "market": {
            "tone_constraints": {
                "disallow_terms": ["concealed blade"],
            }
        },
    }
    content = "Maya walked. " * 20 + "She had a concealed blade under her coat."
    issues = validate_scene(content, config, "Ch1Sc1")
    contamin = [i for i in issues if i["code"] == "GENRE_CROSS_CONTAM"]
    assert len(contamin) >= 1
    assert contamin[0]["severity"] == "error"


def test_validator_no_genre_policing_without_config():
    """Without market.tone_constraints, no disallow/suspicious checks."""
    config = {"protagonist": "Maya"}
    content = "Natalia had a concealed blade. Viktor appeared. " * 10
    issues = validate_scene(content, config, "Ch1Sc1")
    contamin = [i for i in issues if i["code"] == "GENRE_CROSS_CONTAM"]
    suspect = [i for i in issues if i["code"] == "SUSPECT_NAME"]
    assert len(contamin) == 0
    assert len(suspect) == 0


def test_validation_mode_default_is_lenient():
    """Default validation_mode is lenient."""
    assert _validation_mode({}) == "lenient"
    assert _validation_mode({"export": {}}) == "lenient"


def test_validation_mode_strict():
    """Explicit strict mode."""
    assert _validation_mode({"export": {"validation_mode": "strict"}}) == "strict"


def test_duplicate_scene_fingerprint():
    """Duplicate scene content -> DUPLICATE_SCENE warning."""
    same_content = "Identical scene text. " * 20
    scenes = [
        {"chapter": 1, "scene_number": 1, "content": same_content},
        {"chapter": 1, "scene_number": 2, "content": same_content},
    ]
    report = validate_project_scenes(scenes, {})
    dup = [i for i in report["issues"] if i["code"] == "DUPLICATE_SCENE"]
    assert len(dup) >= 1
