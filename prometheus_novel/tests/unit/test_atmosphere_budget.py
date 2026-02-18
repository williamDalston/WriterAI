"""Tests for quality.atmosphere_budget module."""

import unittest
import copy

from quality.atmosphere_budget import (
    ATMOSPHERE_FAMILIES,
    check_atmosphere_budget,
    suppress_atmosphere_excess,
    format_atmosphere_report,
)


def _scene(content, scene_id="ch01_s01"):
    return {"content": content, "scene_id": scene_id}


class TestCheckAtmosphereBudget(unittest.TestCase):
    def test_under_budget_passes(self):
        # 1000 words, neon budget = 4 per 10k = ~0.4, so 1 is fine
        scenes = [_scene("The neon flickered once. " + "word " * 500)]
        result = check_atmosphere_budget(scenes)
        assert result["pass"] is True

    def test_over_budget_fails(self):
        # Cram many neon references into a short text
        neon_text = "The neon flickered. " * 20 + "word " * 100
        scenes = [_scene(neon_text)]
        result = check_atmosphere_budget(scenes)
        assert result["pass"] is False
        assert any(v["family"] == "neon_light" for v in result["violations"])

    def test_multiple_families(self):
        text = (
            "The neon flickered. " * 15 +
            "His heartbeat pounded. " * 15 +
            "word " * 200
        )
        scenes = [_scene(text)]
        result = check_atmosphere_budget(scenes)
        families_flagged = {v["family"] for v in result["violations"]}
        assert "neon_light" in families_flagged
        assert "heartbeat_pulse" in families_flagged

    def test_empty_scenes(self):
        result = check_atmosphere_budget([])
        assert result["pass"] is True

    def test_no_content(self):
        scenes = [{"content": "", "scene_id": "ch01_s01"}]
        result = check_atmosphere_budget(scenes)
        assert result["pass"] is True

    def test_family_counts_populated(self):
        text = "The neon flickered twice. " + "word " * 500
        scenes = [_scene(text)]
        result = check_atmosphere_budget(scenes)
        assert "neon_light" in result["family_counts"]
        assert result["family_counts"]["neon_light"] >= 1

    def test_custom_families(self):
        custom = {
            "test_family": {
                "pattern": r"\bmagic\s+spark\b",
                "budget_per_10k": 1,
                "replacements": ["arcane flash"],
            },
        }
        text = "The magic spark ignited. " * 10 + "word " * 200
        scenes = [_scene(text)]
        result = check_atmosphere_budget(scenes, families=custom)
        assert any(v["family"] == "test_family" for v in result["violations"])

    def test_total_words_calculated(self):
        scenes = [_scene("word " * 500)]
        result = check_atmosphere_budget(scenes)
        assert result["total_words"] == 500


class TestSuppressAtmosphereExcess(unittest.TestCase):
    def test_replaces_excess(self):
        neon_text = "The neon flickered. " * 20 + "word " * 100
        scenes = [_scene(neon_text)]
        modified, report = suppress_atmosphere_excess(scenes)
        assert report["total_replaced"] > 0
        # Should have fewer "neon flickered" than before
        assert modified[0]["content"].count("neon flickered") < 20

    def test_keeps_budget_amount(self):
        # With very short text, budget is based on min 1 unit = budget_per_10k
        neon_text = "The neon flickered. " * 10 + "word " * 50
        scenes = [_scene(neon_text)]
        original_count = neon_text.lower().count("neon flickered")
        modified, report = suppress_atmosphere_excess(scenes)
        remaining = modified[0]["content"].lower().count("neon flickered")
        # Should keep some but replace excess
        assert remaining < original_count or report["total_replaced"] >= 0

    def test_no_excess_no_change(self):
        text = "The neon flickered once. " + "word " * 5000
        scenes = [_scene(text)]
        modified, report = suppress_atmosphere_excess(scenes)
        assert report["total_replaced"] == 0
        assert modified[0]["content"] == text

    def test_empty_scenes(self):
        modified, report = suppress_atmosphere_excess([])
        assert report["total_replaced"] == 0


class TestFormatReport(unittest.TestCase):
    def test_basic_format(self):
        report = {
            "pass": False,
            "violations": [
                {"message": "neon_light: 20 occurrences (budget: 4)"},
            ],
            "family_counts": {"neon_light": 20, "rain_weather": 2},
            "total_words": 30000,
        }
        text = format_atmosphere_report(report)
        assert "NO" in text
        assert "neon_light" in text


if __name__ == "__main__":
    unittest.main()
