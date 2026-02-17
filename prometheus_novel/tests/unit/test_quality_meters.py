"""Unit tests for quality_meters, including scene_id integrity."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from stages.quality_meters import (
    scene_id_integrity_check,
    run_all_meters,
)


def test_scene_id_integrity_pass():
    """Scenes with correct scene_ids pass."""
    scenes = [
        {"chapter": 1, "scene_number": 1, "scene_id": "ch01_s01", "content": "a"},
        {"chapter": 1, "scene_number": 2, "scene_id": "ch01_s02", "content": "b"},
        {"chapter": 2, "scene_number": 1, "scene_id": "ch02_s01", "content": "c"},
    ]
    r = scene_id_integrity_check(scenes)
    assert r["pass"] is True
    assert r["mismatches"] == []
    assert r["duplicates"] == []
    assert r["missing"] == []


def test_scene_id_integrity_mismatch():
    """Wrong scene_id -> mismatch."""
    scenes = [
        {"chapter": 2, "scene_number": 1, "scene_id": "ch01_s01", "content": "a"},
    ]
    r = scene_id_integrity_check(scenes)
    assert r["pass"] is False
    assert len(r["mismatches"]) == 1
    exp, act, ch, sc = r["mismatches"][0]
    assert exp == "ch02_s01"
    assert act == "ch01_s01"


def test_scene_id_integrity_duplicate():
    """Duplicate scene_ids -> duplicates list."""
    scenes = [
        {"chapter": 1, "scene_number": 1, "scene_id": "ch01_s01", "content": "a"},
        {"chapter": 2, "scene_number": 1, "scene_id": "ch01_s01", "content": "b"},
    ]
    r = scene_id_integrity_check(scenes)
    assert r["pass"] is False
    assert "ch01_s01" in r["duplicates"]


def test_scene_id_integrity_missing():
    """Scenes without scene_id -> missing list."""
    scenes = [
        {"chapter": 1, "scene_number": 1, "content": "a"},
        {"chapter": 1, "scene_number": 2, "scene_id": "ch01_s02", "content": "b"},
    ]
    r = scene_id_integrity_check(scenes)
    assert r["pass"] is False
    assert len(r["missing"]) == 1
    assert r["missing"][0] == (1, 1)


def test_run_all_meters_includes_integrity():
    """run_all_meters includes scene_id_integrity and all_pass respects it."""
    scenes = [
        {"chapter": 1, "scene_number": 1, "scene_id": "ch01_s01", "content": "x" * 200},
    ]
    report = run_all_meters(scenes, [], [])
    assert "scene_id_integrity" in report
    assert report["scene_id_integrity"]["pass"] is True
    # Integrity failure should pull all_pass down
    bad = [
        {"chapter": 1, "scene_number": 1, "content": "x" * 200},
    ]
    bad_report = run_all_meters(bad, [], [])
    assert bad_report["scene_id_integrity"]["pass"] is False
    assert bad_report["all_pass"] is False
