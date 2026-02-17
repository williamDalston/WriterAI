"""Tests for quality observability: delta report, ceiling rules, policy loader, loop guard."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from quality.delta_report import compute_scene_delta, compute_pass_delta, build_delta_report
from quality.ceiling import CeilingRules, CeilingTracker
from quality.policy import load_policy, is_pass_enabled, _deep_merge
from quality.loop_guard import check_replacement_loops


# ============================================================================
# Delta Report Tests
# ============================================================================

class TestDeltaReport:
    def test_unchanged_scene_delta(self):
        """Unchanged scene should report no changes."""
        d = compute_scene_delta("Hello world.", "Hello world.")
        assert d["changed"] is False

    def test_changed_scene_delta(self):
        """Changed scene should report sentence-level delta."""
        before = "My heart races. The air between us thickened. She smiled."
        after = "My pulse kicks. The air between us thickened. She smiled."
        d = compute_scene_delta(before, after)
        assert d["changed"] is True
        assert d["sentences_removed"] >= 1
        assert d["pct_sentences_changed"] > 0

    def test_pass_delta_tracks_hottest_scenes(self):
        """Scenes with >10% sentence changes should be flagged as hot."""
        before = [
            "Sentence one. Sentence two. Sentence three.",
            "A. B. C. D. E. F. G. H. I. J.",  # 10 sentences
        ]
        # Change 50% of scene 1
        after = [
            "Sentence one. REPLACED. REPLACED.",
            "A. B. C. D. E. F. G. H. I. J.",  # unchanged
        ]
        delta = compute_pass_delta(before, after, "test_pass", {})
        assert delta["scenes_changed"] == 1
        assert delta["pct_scenes_changed"] == 50.0

    def test_build_delta_report_structure(self):
        """Full delta report should have version, summary, passes, unresolved."""
        delta = build_delta_report(
            [{"pass": "test", "scenes_changed": 5, "scenes_total": 10,
              "pct_scenes_changed": 50.0, "total_sentences_changed": 3,
              "pct_sentences_changed": 2.0, "chars_delta": -100,
              "hottest_scenes": [], "pass_report_summary": {"tags_trimmed": 5}}],
            {"some_issue": True},
        )
        assert delta["version"] == 1
        assert "summary" in delta
        assert "passes" in delta
        assert delta["unresolved"]["some_issue"] is True


# ============================================================================
# Ceiling Rules Tests
# ============================================================================

class TestCeiling:
    def test_default_limits(self):
        """Default ceiling should allow reasonable edits."""
        rules = CeilingRules()
        tracker = CeilingTracker(rules)
        tracker.register_scene(0, 1000)

        for i in range(8):
            assert tracker.can_edit(0) is True
            tracker.record_edit(0)

    def test_per_scene_cap(self):
        """Should block after max_edits_per_scene reached."""
        rules = CeilingRules(max_edits_per_scene=3)
        tracker = CeilingTracker(rules)
        tracker.register_scene(0, 500)

        for i in range(3):
            assert tracker.can_edit(0) is True
            tracker.record_edit(0)

        assert tracker.can_edit(0) is False

    def test_per_1k_words_cap(self):
        """Short scenes should have lower absolute edit limits."""
        rules = CeilingRules(max_edits_per_1k_words=4.0, max_edits_per_scene=100)
        tracker = CeilingTracker(rules)
        tracker.register_scene(0, 250)  # 250 words = max 1 edit (4 * 0.25)

        assert tracker.can_edit(0) is True
        tracker.record_edit(0)
        assert tracker.can_edit(0) is False

    def test_per_family_per_chapter_cap(self):
        """Same family in same chapter should be capped."""
        rules = CeilingRules(
            max_per_family_per_chapter=2,
            max_edits_per_scene=100,
            max_edits_per_1k_words=100,
        )
        tracker = CeilingTracker(rules)
        tracker.register_scene(0, 2000)

        tracker.record_edit(0, family="cardiac", chapter=1)
        tracker.record_edit(0, family="cardiac", chapter=1)
        assert tracker.can_edit(0, family="cardiac", chapter=1) is False
        # Different family should still be ok
        assert tracker.can_edit(0, family="respiratory", chapter=1) is True

    def test_report_structure(self):
        """Report should show ceiling hits."""
        rules = CeilingRules(max_edits_per_scene=2)
        tracker = CeilingTracker(rules)
        tracker.register_scene(0, 500)
        tracker.record_edit(0)
        tracker.record_edit(0)
        tracker.can_edit(0)  # Trigger a ceiling hit

        r = tracker.report()
        assert r["scenes_capped"] == 1
        assert "max_edits_per_scene" in r["ceiling_hits"]

    def test_from_dict(self):
        """CeilingRules.from_dict should ignore unknown keys."""
        rules = CeilingRules.from_dict({
            "max_edits_per_scene": 5,
            "unknown_key": 999,
        })
        assert rules.max_edits_per_scene == 5
        assert rules.max_edits_per_1k_words == 8.0  # default


# ============================================================================
# Policy Loader Tests
# ============================================================================

class TestPolicy:
    def test_default_policy(self):
        """Default policy should have all expected keys."""
        policy = load_policy(genre="romance")
        assert "ceiling" in policy
        assert "enabled_passes" in policy
        assert "phrase_suppression" in policy

    def test_genre_fallback(self):
        """Unknown genre should fall back to default preset."""
        policy = load_policy(genre="nonexistent_genre_xyz")
        assert "ceiling" in policy
        assert "enabled_passes" in policy

    def test_project_overrides(self):
        """Project overrides should merge on top of preset."""
        policy = load_policy(
            genre="romance",
            project_overrides={"ceiling": {"max_edits_per_scene": 99}},
        )
        assert policy["ceiling"]["max_edits_per_scene"] == 99
        # Other ceiling values should still be present
        assert "max_edits_per_1k_words" in policy["ceiling"]

    def test_is_pass_enabled(self):
        """is_pass_enabled should check enabled_passes list."""
        policy = {"enabled_passes": ["phrase_mining", "cliche_repair"]}
        assert is_pass_enabled(policy, "phrase_mining") is True
        assert is_pass_enabled(policy, "dialogue_trimming") is False

    def test_deep_merge(self):
        """Nested dicts should merge recursively."""
        base = {"a": {"b": 1, "c": 2}, "d": 3}
        override = {"a": {"c": 99}, "e": 5}
        merged = _deep_merge(base, override)
        assert merged["a"]["b"] == 1
        assert merged["a"]["c"] == 99
        assert merged["d"] == 3
        assert merged["e"] == 5


# ============================================================================
# Loop Guard Tests
# ============================================================================

class TestLoopGuard:
    def test_detects_collision(self):
        """Replacement that matches another module's pattern should be flagged."""
        cliche_config = {
            "clusters": {
                "cardiac": {
                    "label": "Heart",
                    "keep_first": 2,
                    "threshold": 5,
                    "patterns": [
                        {"regex": r"\bheart\s+races\b", "replacements": ["pulse kicks"]},
                    ],
                }
            }
        }
        # phrase_suppressor bank has "pulse kicks" as a detection target
        phrase_bank = {
            "pulse kicks": ["something else"],
        }
        emotion_phrases = {}

        report = check_replacement_loops(cliche_config, phrase_bank, emotion_phrases)
        assert report["collisions_found"] >= 1
        assert any("pulse kicks" in c["replacement"] for c in report["collisions"])

    def test_no_false_positives_self_collision(self):
        """Replacements should not flag against their own source."""
        cliche_config = {
            "clusters": {
                "cardiac": {
                    "label": "Heart",
                    "keep_first": 2,
                    "threshold": 5,
                    "patterns": [
                        {"regex": r"\bheart\s+races\b", "replacements": ["unique phrase xyz"]},
                    ],
                }
            }
        }
        report = check_replacement_loops(cliche_config, {}, {})
        assert report["collisions_found"] == 0

    def test_clean_banks_no_collisions(self):
        """Independent replacement banks should produce 0 collisions."""
        cliche_config = {
            "clusters": {
                "test": {
                    "patterns": [
                        {"regex": r"\bfoo bar\b", "replacements": ["baz qux"]},
                    ],
                    "keep_first": 1,
                    "threshold": 5,
                }
            }
        }
        phrase_bank = {"something else": ["totally different"]}
        emotion_phrases = {"another thing": {"category": "x", "replacements": ["yet another"]}}

        report = check_replacement_loops(cliche_config, phrase_bank, emotion_phrases)
        assert report["collisions_found"] == 0
