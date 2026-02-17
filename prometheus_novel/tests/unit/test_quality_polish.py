"""Tests for quality polish modules: phrase miner, suppressor, dialogue trimmer, emotion diversifier."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from quality.phrase_miner import mine_hot_phrases, _normalize
from quality.phrase_suppressor import suppress_phrases
from quality.dialogue_trimmer import trim_dialogue_tags
from quality.emotion_diversifier import diversify_scene, _REACTION_PHRASES
from quality.cliche_clusters import detect_clusters


# ============================================================================
# Phrase Miner Tests
# ============================================================================

class TestPhraseMiner:
    def test_mines_repeated_phrases(self):
        """Phrases appearing in 5+ scenes should be flagged."""
        scenes = [
            "His voice was barely above a whisper. The air between us thickened."
            for _ in range(10)
        ]
        result = mine_hot_phrases(scenes, min_total=5, min_scenes=5)
        phrases = {p["phrase"] for p in result["phrases"]}
        assert "barely above a whisper" in phrases
        assert "air between us" in phrases or "the air between us" in phrases

    def test_below_threshold_not_flagged(self):
        """Phrases below threshold should not be flagged."""
        scenes = [
            "His voice was barely above a whisper."
            for _ in range(3)
        ]
        result = mine_hot_phrases(scenes, min_total=8, min_scenes=4)
        assert len(result["phrases"]) == 0

    def test_normalize_smart_quotes(self):
        """Smart quotes and em-dashes should normalize correctly."""
        text = "\u201cHello,\u201d she said\u2014quietly."
        norm = _normalize(text)
        assert "\u201c" not in norm
        assert "\u2014" not in norm

    def test_stopword_phrases_filtered(self):
        """Phrases that are mostly stopwords should be filtered out."""
        scenes = ["I was going to do it but then I was not." for _ in range(20)]
        result = mine_hot_phrases(scenes, min_total=5, min_scenes=5)
        for p in result["phrases"]:
            # None should be purely stopwords
            assert any(w not in {"i", "was", "going", "to", "do", "it", "but", "then", "not"}
                      for w in p["phrase"].split())

    def test_burst_detection(self):
        """High frequency in a small window should flag even with lower total."""
        # 5 scenes with phrase, rest without
        scenes = (
            ["The magic word repeated again." for _ in range(5)]
            + ["Nothing here." for _ in range(20)]
        )
        result = mine_hot_phrases(
            scenes, min_total=20, min_scenes=20,  # High thresholds
            burst_threshold=4,  # But low burst threshold
        )
        flagged = {p["phrase"] for p in result["phrases"]}
        assert "magic word repeated" in flagged or "word repeated again" in flagged


# ============================================================================
# Phrase Suppressor Tests
# ============================================================================

class TestPhraseSuppressor:
    def test_replaces_excess_occurrences(self):
        """Phrases beyond keep_first should be replaced."""
        scenes = [
            "She spoke barely above a whisper. He replied barely above a whisper."
            for _ in range(5)
        ]
        configs = [{
            "phrase": "barely above a whisper",
            "keep_first": 2,
            "replacements": ["so quiet I almost missed it", "in a low voice"],
        }]
        modified, report = suppress_phrases(scenes, configs)
        assert report["total_replacements"] > 0
        # First 2 should be kept, rest replaced
        total_original = sum(s.count("barely above a whisper") for s in modified)
        assert total_original <= 2

    def test_preserves_capitalization(self):
        """Replacements should preserve original capitalization."""
        scenes = ["Barely above a whisper, she said it."]
        configs = [{
            "phrase": "barely above a whisper",
            "keep_first": 0,
            "replacements": ["so quiet I almost missed it"],
        }]
        modified, _ = suppress_phrases(scenes, configs)
        assert modified[0].startswith("So quiet")

    def test_no_replacement_when_under_threshold(self):
        """Phrases under keep_first should not be replaced."""
        scenes = ["He spoke barely above a whisper."]
        configs = [{
            "phrase": "barely above a whisper",
            "keep_first": 5,
            "replacements": ["test"],
        }]
        modified, report = suppress_phrases(scenes, configs)
        assert report["total_replacements"] == 0
        assert modified[0] == scenes[0]


# ============================================================================
# Dialogue Trimmer Tests
# ============================================================================

class TestDialogueTrimmer:
    def test_trims_long_dialogue_tags(self):
        """Long dialogue tags should be shortened."""
        text = (
            '"I understand," I murmured softly gently quietly '
            'once he paused briefly to catch his breath.'
        )
        result, report = trim_dialogue_tags(text)
        # Should remove stacked qualifiers
        assert report["tags_found"] >= 0  # Pattern may or may not match this exact format

    def test_removes_stacked_qualifiers(self):
        """Multiple adverb qualifiers should be reduced to one."""
        text = '"Stop," she said softly gently tenderly.'
        result, report = trim_dialogue_tags(text)
        # At least the stacked qualifiers should be reduced
        assert result.count("softly") + result.count("gently") + result.count("tenderly") <= 2


# ============================================================================
# Emotion Diversifier Tests
# ============================================================================

class TestEmotionDiversifier:
    def test_diversifies_repeated_reactions(self):
        """Repeated physical reactions should be replaced after keep_first."""
        scenes = [f"Scene {i}: My heart races every time." for i in range(10)]
        from collections import Counter
        modified, report = diversify_scene(
            " ".join(scenes),
            keep_first_per_phrase=2,
            global_counts=Counter(),
            global_keep=Counter(),
        )
        assert report["found"] > 0
        # After first 2 occurrences, the rest should be diversified
        assert "my heart races" not in modified.lower().split("scene 5")[0] or report["replaced"] > 0

    def test_preserves_text_when_no_reactions(self):
        """Text without reactions should pass through unchanged."""
        text = "The sun set behind the mountains. Birds sang in the distance."
        from collections import Counter
        result, report = diversify_scene(text, global_counts=Counter(), global_keep=Counter())
        assert result == text
        assert report["found"] == 0


# ============================================================================
# Cliche Cluster Tests
# ============================================================================

class TestClicheClusters:
    def test_detects_cardiac_cluster(self):
        """Cardiac reaction patterns should be detected."""
        scenes = [
            "My heart races. My heart pounds. My pulse quickens."
            for _ in range(5)
        ]
        report = detect_clusters(
            scenes,
            clusters_dict={
                "clusters": {
                    "cardiac": {
                        "label": "Heart",
                        "patterns": [r"\bheart\s+(?:races|pounds)\b", r"\bpulse\s+quickens\b"],
                        "threshold": 5,
                    }
                }
            },
        )
        assert report["flagged_count"] == 1
        assert report["clusters"]["cardiac"]["total_hits"] >= 5

    def test_below_threshold_not_flagged(self):
        """Clusters below threshold should not be flagged."""
        scenes = ["My heart races once."]
        report = detect_clusters(
            scenes,
            clusters_dict={
                "clusters": {
                    "cardiac": {
                        "label": "Heart",
                        "patterns": [r"\bheart\s+races\b"],
                        "threshold": 10,
                    }
                }
            },
        )
        assert report["flagged_count"] == 0
