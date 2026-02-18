"""Tests for quality.stakes_escalation module."""

import unittest

from quality.stakes_escalation import (
    _detect_stakes,
    _has_consequence,
    _has_cost,
    _is_discovery_only,
    track_stakes_progression,
    format_stakes_report,
)


def _scene(content, tension_level=5, scene_id="ch01_s01"):
    return {
        "content": content,
        "tension_level": tension_level,
        "scene_id": scene_id,
    }


class TestDetectStakes(unittest.TestCase):
    def test_safety_stakes(self):
        cats = _detect_stakes("The danger was clear. They had to escape the threat.")
        assert "SAFETY" in cats

    def test_money_stakes(self):
        cats = _detect_stakes("The debt was crushing. Payment was due tomorrow.")
        assert "MONEY" in cats

    def test_life_death(self):
        cats = _detect_stakes("If they didn't act, someone would die. Murder was imminent.")
        assert "LIFE_DEATH" in cats

    def test_multiple_categories(self):
        cats = _detect_stakes(
            "Her reputation was at risk, the danger was real, "
            "and the money was gone."
        )
        assert "REPUTATION" in cats
        assert "SAFETY" in cats
        assert "MONEY" in cats

    def test_no_stakes(self):
        cats = _detect_stakes("The sun was warm. Birds sang in the trees.")
        assert len(cats) == 0

    def test_truth_stakes(self):
        cats = _detect_stakes("The conspiracy went deeper. She needed proof.")
        assert "TRUTH" in cats


class TestHasConsequence(unittest.TestCase):
    def test_with_consequence(self):
        assert _has_consequence("Everything was destroyed. The building was ruined.")

    def test_death_consequence(self):
        assert _has_consequence("He was killed in the explosion.")

    def test_betrayal(self):
        assert _has_consequence("She had been betrayed by the one person she trusted.")

    def test_no_consequence(self):
        assert not _has_consequence("They sat and talked about the weather.")

    def test_point_of_no_return(self):
        assert _has_consequence("There was no going back after what she'd done.")


class TestHasCost(unittest.TestCase):
    def test_sacrifice(self):
        assert _has_cost("She gave up everything to protect them.")

    def test_isolation(self):
        assert _has_cost("He was alone now. Cut off from everyone.")

    def test_injury(self):
        assert _has_cost("The wound on her arm was deep.")

    def test_no_cost(self):
        assert not _has_cost("They had lunch at the cafe.")


class TestIsDiscoveryOnly(unittest.TestCase):
    def test_discovery_only(self):
        text = "She found the document in the drawer. The symbol was there again."
        assert _is_discovery_only(text)

    def test_discovery_with_consequence(self):
        text = "She found the document. The building was destroyed moments later."
        assert not _is_discovery_only(text)

    def test_no_discovery(self):
        text = "They walked through the park."
        assert not _is_discovery_only(text)


class TestTrackStakesProgression(unittest.TestCase):
    def test_empty_scenes(self):
        result = track_stakes_progression([])
        assert result["pass"] is True

    def test_healthy_progression(self):
        scenes = [
            _scene("The danger was growing. Someone had been killed.", 7, "ch01_s01"),
            _scene("The debt was crushing. Everything was destroyed.", 8, "ch02_s01"),
            _scene("She gave up her freedom. She was alone now.", 9, "ch03_s01"),
        ]
        result = track_stakes_progression(scenes)
        assert result["pass"] is True
        assert result["escalation_score"] > 0.5

    def test_stakes_plateau(self):
        # 3 consecutive high-tension scenes with only SAFETY
        scenes = [
            _scene("The danger was imminent. Risk everywhere.", 7, "ch01_s01"),
            _scene("More danger ahead. The threat grew.", 8, "ch02_s01"),
            _scene("Danger again. The risk was real.", 7, "ch03_s01"),
        ]
        result = track_stakes_progression(scenes, plateau_window=3)
        plateau_violations = [v for v in result["violations"] if v["type"] == "STAKES_PLATEAU"]
        assert len(plateau_violations) >= 1

    def test_consequence_deficit(self):
        # Many high-tension scenes without consequences
        scenes = [
            _scene("Danger everywhere. Risk is high.", 7, f"ch{i:02d}_s01")
            for i in range(1, 9)
        ]
        result = track_stakes_progression(scenes)
        deficit = [v for v in result["violations"] if v["type"] == "CONSEQUENCE_DEFICIT"]
        assert len(deficit) >= 1

    def test_symbolic_only(self):
        # Many discovery-only scenes
        scenes = [
            _scene("She found the symbol on the wall. She noticed the pattern.", 5, f"ch{i:02d}_s01")
            for i in range(1, 10)
        ]
        result = track_stakes_progression(scenes)
        symbolic = [v for v in result["violations"] if v["type"] == "SYMBOLIC_ONLY"]
        assert len(symbolic) >= 1

    def test_low_tension_not_checked_for_plateau(self):
        # Low-tension scenes shouldn't trigger plateau
        scenes = [
            _scene("They had coffee. It was pleasant.", 3, f"ch{i:02d}_s01")
            for i in range(1, 6)
        ]
        result = track_stakes_progression(scenes)
        assert result["pass"] is True

    def test_progression_structure(self):
        scenes = [
            _scene("The danger was real.", 7, "ch01_s01"),
        ]
        result = track_stakes_progression(scenes)
        assert len(result["progression"]) == 1
        p = result["progression"][0]
        assert "scene_id" in p
        assert "tension_level" in p
        assert "stakes_categories" in p
        assert "has_consequence" in p


class TestFormatReport(unittest.TestCase):
    def test_basic_format(self):
        report = {
            "pass": False,
            "violations": [
                {"severity": "high", "type": "CONSEQUENCE_DEFICIT", "message": "60% deficit"},
            ],
            "progression": [
                {"scene_id": "ch01_s01", "tension_level": 7, "has_consequence": False, "is_discovery_only": True},
            ],
            "escalation_score": 0.3,
        }
        text = format_stakes_report(report)
        assert "NO" in text
        assert "CONSEQUENCE_DEFICIT" in text


if __name__ == "__main__":
    unittest.main()
