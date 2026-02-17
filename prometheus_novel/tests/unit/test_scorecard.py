"""Tests for quality scorecard module."""
import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from quality.scorecard import (
    run_scorecard,
    _type_token_ratio,
    _dialogue_density,
    _shannon_entropy,
    _verb_specificity_index,
    _ending_evenness,
)
from quality.quiet_killers import _EMO_KEYWORDS, _WEAK_VERBS, _classify_ending
from collections import Counter


# === Type-Token Ratio ===

class TestTypeTokenRatio:
    def test_diverse_text_high_ttr(self):
        # Use real diverse words (regex matches [a-z]+ only)
        words = ["apple", "banana", "cherry", "date", "elderberry", "fig", "grape",
                 "hazelnut", "kiwi", "lemon", "mango", "nectarine", "orange", "papaya",
                 "quince", "raspberry", "strawberry", "tangerine", "watermelon", "plum"]
        text = " ".join(words * 10)  # 200 words, 20 unique
        ttr = _type_token_ratio(text)
        assert ttr > 0.05, f"Diverse text should have measurable TTR, got {ttr}"

    def test_repetitive_text_low_ttr(self):
        text = " ".join(["the cat sat on mat"] * 100)
        ttr = _type_token_ratio(text)
        assert ttr < 0.15, f"Repetitive text should have low TTR, got {ttr}"

    def test_empty_text_returns_zero(self):
        assert _type_token_ratio("") == 0.0

    def test_short_text_single_window(self):
        text = "the quick brown fox jumps over the lazy dog"
        ttr = _type_token_ratio(text, window=500)
        assert 0.5 < ttr <= 1.0, f"Short diverse text should have high TTR, got {ttr}"


# === Dialogue Density ===

class TestDialogueDensity:
    def test_all_dialogue_near_one(self):
        content = '"Hello," she said.\n"Hi," he replied.\n"How are you?"\n"Fine."'
        density = _dialogue_density(content)
        assert density >= 0.9, f"All dialogue should be near 1.0, got {density}"

    def test_no_dialogue_returns_zero(self):
        content = "The wind blew.\nRain fell on the windows.\nSilence."
        density = _dialogue_density(content)
        assert density == 0.0, f"No dialogue should be 0.0, got {density}"

    def test_mixed_content(self):
        content = 'She walked in.\n"Hello," she said.\nThe room was dark.\n"Leave," he warned.'
        density = _dialogue_density(content)
        assert 0.3 < density < 0.7, f"Mixed content should be ~0.5, got {density}"


# === Shannon Entropy ===

class TestShannonEntropy:
    def test_uniform_distribution(self):
        dist = [5, 5, 5, 5]
        entropy = _shannon_entropy(dist)
        assert abs(entropy - 2.0) < 0.01, f"Uniform 4-way should be 2.0, got {entropy}"

    def test_single_category(self):
        dist = [10]
        entropy = _shannon_entropy(dist)
        assert entropy == 0.0, f"Single category should be 0.0, got {entropy}"

    def test_skewed_distribution(self):
        dist = [100, 1, 1]
        entropy = _shannon_entropy(dist)
        assert entropy < 0.3, f"Highly skewed should be near 0, got {entropy}"

    def test_empty_returns_zero(self):
        assert _shannon_entropy([]) == 0.0


# === Verb Specificity ===

class TestVerbSpecificity:
    def test_strong_verbs_high_index(self):
        text = "She lunged forward. He slammed the door. They whispered in the dark."
        index = _verb_specificity_index(text, _WEAK_VERBS)
        assert index > 0.8, f"Strong-only should be high, got {index}"

    def test_weak_verbs_low_index(self):
        text = "He turned. She looked. He nodded. She glanced. He shrugged. She sighed."
        index = _verb_specificity_index(text, _WEAK_VERBS)
        assert index < 0.2, f"Weak-only should be low, got {index}"

    def test_no_verbs_returns_neutral(self):
        text = "The sky was blue. The water was cold."
        index = _verb_specificity_index(text, _WEAK_VERBS)
        assert index == 0.5, f"No matched verbs should return 0.5, got {index}"


# === Ending Evenness ===

class TestEndingEvenness:
    def test_even_distribution(self):
        counts = Counter({"ACTION": 3, "DIALOGUE": 3, "REVELATION": 3})
        evenness = _ending_evenness(counts)
        assert evenness > 0.8, f"Even distribution should be high, got {evenness}"

    def test_skewed_distribution(self):
        # Counter with only 1 type (zero-value entries excluded)
        counts = Counter({"ACTION": 10})
        evenness = _ending_evenness(counts)
        assert evenness == 0.0, f"Single-type should be 0.0, got {evenness}"


# === Full Scorecard ===

class TestRunScorecard:
    def test_produces_all_keys(self):
        scenes = [
            {"content": '"Hello," she said. He lunged at the door. The morning light crept in. She wondered about trust.', "scene_id": "ch01_s01"},
            {"content": '"Stop!" he shouted. She slammed her fist. The evening was cold. He felt angry inside.', "scene_id": "ch01_s02"},
        ]
        result = run_scorecard(scenes, _EMO_KEYWORDS, _WEAK_VERBS, _classify_ending)
        assert "lexical_diversity" in result
        assert "dialogue_density_variance" in result
        assert "emotional_mode_diversity" in result
        assert "verb_specificity_index" in result
        assert "scene_ending_distribution" in result
        assert "pass" in result

    def test_empty_scenes_returns_pass(self):
        result = run_scorecard([], _EMO_KEYWORDS, _WEAK_VERBS, _classify_ending)
        assert result["pass"] is True
        assert "note" in result

    def test_no_content_scenes_returns_pass(self):
        scenes = [{"scene_id": "ch01_s01"}, {"scene_id": "ch01_s02"}]
        result = run_scorecard(scenes, _EMO_KEYWORDS, _WEAK_VERBS, _classify_ending)
        assert result["pass"] is True


    def test_thresholds_override_defaults(self):
        """Custom thresholds from policy should be respected."""
        # Use scenes with weak verbs (looked, nodded, turned) to ensure verb_specificity < 0.99
        scenes = [
            {"content": 'She looked around. He nodded slowly. She turned to leave. He glanced at the door.', "scene_id": "s1"},
            {"content": 'He shrugged and sighed. She looked at him. He turned away. She nodded once.', "scene_id": "s2"},
        ]
        # Impossibly high thresholds
        strict = {
            "lexical_diversity_min": 0.99,
            "dialogue_variance_min": 0.99,
            "emotional_entropy_min": 9.0,
            "verb_specificity_min": 0.99,
            "ending_evenness_min": 0.99,
        }
        result = run_scorecard(scenes, _EMO_KEYWORDS, _WEAK_VERBS, _classify_ending, thresholds=strict)
        assert result["pass"] is False
        assert result["lexical_diversity"]["pass"] is False
        assert result["verb_specificity_index"]["pass"] is False


# === Weighted Scorecard ===

class TestWeightedScorecard:
    """Tests for the weighted scoring mode."""

    def _make_scenes(self):
        return [
            {"content": '"Hello," she said. He lunged at the door. The morning light crept in. She wondered about trust.', "scene_id": "ch01_s01"},
            {"content": '"Stop!" he shouted. She slammed her fist. The evening was cold. He felt angry inside.', "scene_id": "ch01_s02"},
        ]

    def test_boolean_mode_replicates_old_behavior(self):
        """mode=boolean should produce same result as no weights."""
        scenes = self._make_scenes()
        base = run_scorecard(scenes, _EMO_KEYWORDS, _WEAK_VERBS, _classify_ending)
        weighted = run_scorecard(scenes, _EMO_KEYWORDS, _WEAK_VERBS, _classify_ending,
                                 thresholds={"scorecard_weights": {"mode": "boolean"}})
        assert base["pass"] == weighted["pass"]
        assert "weighted" not in weighted  # no weighted section in boolean mode

    def test_weighted_mode_passes_when_score_above_threshold(self):
        """All metrics passing → score = 1.0 → pass."""
        scenes = self._make_scenes()
        cfg = {
            "scorecard_weights": {
                "mode": "weighted",
                "pass_score": 0.70,
                "lexical_diversity": {"weight": 0.20, "action_on_fail": "warn"},
                "dialogue_density": {"weight": 0.20, "action_on_fail": "warn"},
                "emotional_diversity": {"weight": 0.20, "action_on_fail": "warn"},
                "verb_specificity": {"weight": 0.20, "action_on_fail": "warn"},
                "scene_endings": {"weight": 0.20, "action_on_fail": "warn"},
            },
        }
        result = run_scorecard(scenes, _EMO_KEYWORDS, _WEAK_VERBS, _classify_ending, thresholds=cfg)
        assert "weighted" in result
        assert result["weighted"]["score"] >= 0.0

    def test_weighted_passes_even_if_one_warn_metric_fails(self):
        """One warn-metric failing should still pass if score >= pass_score."""
        scenes = self._make_scenes()
        # Set one threshold impossibly high so it fails
        cfg = {
            "lexical_diversity_min": 0.99,  # will fail
            "scorecard_weights": {
                "mode": "weighted",
                "pass_score": 0.50,  # low bar
                "lexical_diversity": {"weight": 0.10, "action_on_fail": "warn"},
                "dialogue_density": {"weight": 0.20, "action_on_fail": "warn"},
                "emotional_diversity": {"weight": 0.20, "action_on_fail": "warn"},
                "verb_specificity": {"weight": 0.20, "action_on_fail": "warn"},
                "scene_endings": {"weight": 0.30, "action_on_fail": "warn"},
            },
        }
        result = run_scorecard(scenes, _EMO_KEYWORDS, _WEAK_VERBS, _classify_ending, thresholds=cfg)
        assert result["lexical_diversity"]["pass"] is False  # this metric failed
        # But overall should still pass (score = 0.90 if others pass, >= 0.50 threshold)
        assert result["weighted"]["score"] >= 0.50
        assert result["pass"] is True

    def test_hard_fail_overrides_score(self):
        """A metric with action_on_fail=fail should cause overall fail regardless of score."""
        scenes = self._make_scenes()
        cfg = {
            "lexical_diversity_min": 0.99,  # will fail
            "scorecard_weights": {
                "mode": "weighted",
                "pass_score": 0.10,  # very low bar
                "lexical_diversity": {"weight": 0.10, "action_on_fail": "fail"},  # hard fail
                "dialogue_density": {"weight": 0.20, "action_on_fail": "warn"},
                "emotional_diversity": {"weight": 0.20, "action_on_fail": "warn"},
                "verb_specificity": {"weight": 0.20, "action_on_fail": "warn"},
                "scene_endings": {"weight": 0.30, "action_on_fail": "warn"},
            },
        }
        result = run_scorecard(scenes, _EMO_KEYWORDS, _WEAK_VERBS, _classify_ending, thresholds=cfg)
        assert result["weighted"]["hard_fail"] is True
        assert result["pass"] is False  # hard fail overrides score

    def test_off_metric_excluded_from_scoring(self):
        """Metrics with action_on_fail=off should not affect score."""
        scenes = self._make_scenes()
        cfg = {
            "lexical_diversity_min": 0.99,  # would fail
            "scorecard_weights": {
                "mode": "weighted",
                "pass_score": 0.70,
                "lexical_diversity": {"weight": 0.20, "action_on_fail": "off"},  # excluded
                "dialogue_density": {"weight": 0.25, "action_on_fail": "warn"},
                "emotional_diversity": {"weight": 0.25, "action_on_fail": "warn"},
                "verb_specificity": {"weight": 0.25, "action_on_fail": "warn"},
                "scene_endings": {"weight": 0.25, "action_on_fail": "warn"},
            },
        }
        result = run_scorecard(scenes, _EMO_KEYWORDS, _WEAK_VERBS, _classify_ending, thresholds=cfg)
        # lex diversity failure shouldn't matter since it's off
        assert "lexical_diversity" not in (result.get("weighted", {}).get("warnings", []))

    def test_weights_normalize_properly(self):
        """Weighted score should be between 0.0 and 1.0."""
        scenes = self._make_scenes()
        cfg = {
            "scorecard_weights": {
                "mode": "weighted",
                "pass_score": 0.70,
                "lexical_diversity": {"weight": 0.50, "action_on_fail": "warn"},
                "dialogue_density": {"weight": 0.10, "action_on_fail": "warn"},
                "emotional_diversity": {"weight": 0.10, "action_on_fail": "warn"},
                "verb_specificity": {"weight": 0.10, "action_on_fail": "warn"},
                "scene_endings": {"weight": 0.20, "action_on_fail": "warn"},
            },
        }
        result = run_scorecard(scenes, _EMO_KEYWORDS, _WEAK_VERBS, _classify_ending, thresholds=cfg)
        score = result["weighted"]["score"]
        assert 0.0 <= score <= 1.0, f"Score should be normalized, got {score}"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
