"""Tests for outline diversity validator — scene signatures + 5 diversity checks."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from quality.outline_diversity import (
    compute_scene_signature,
    validate_outline_diversity,
    format_diversity_report,
    _classify,
    _normalize_location,
    _extract_participants,
    _signature_similarity,
    _suggest_fix,
    _SCENE_FUNCTIONS,
    _EMOTIONAL_MODES,
    _INTERACTION_TYPES,
)


# === Scene Signature Computation ===

class TestComputeSceneSignature:
    def test_returns_all_fields(self):
        scene = {
            "purpose": "Valentina confronts Marco about the secret",
            "central_conflict": "trust vs betrayal",
            "location": "Kitchen",
            "pov": "Valentina",
            "outcome": "argument escalates",
            "emotional_arc": "anger builds to rage",
        }
        sig = compute_scene_signature(scene)
        assert set(sig.keys()) == {
            "function", "emotional_mode", "location",
            "participants", "interaction_type", "has_plot_delta",
        }

    def test_function_classification(self):
        scene = {"purpose": "She uncovers the hidden truth, a secret confession is revealed"}
        sig = compute_scene_signature(scene)
        assert sig["function"] == "REVEAL"

    def test_conflict_function(self):
        scene = {"purpose": "They confront each other in an argument. She refuses."}
        sig = compute_scene_signature(scene)
        assert sig["function"] == "CONFLICT"

    def test_emotional_mode(self):
        scene = {"emotional_arc": "tension builds, frustration and anger rise"}
        sig = compute_scene_signature(scene)
        assert sig["emotional_mode"] == "conflict"

    def test_location_normalized(self):
        scene = {"location": "The Kitchen"}
        sig = compute_scene_signature(scene)
        assert sig["location"] == "kitchen"

    def test_participants_from_pov_and_purpose(self):
        scene = {"pov": "Valentina", "purpose": "Marco reveals truth", "central_conflict": ""}
        sig = compute_scene_signature(scene)
        assert "valentina" in sig["participants"]
        assert "marco" in sig["participants"]

    def test_has_plot_delta_yes(self):
        scene = {"outcome": "She decides to leave town"}
        sig = compute_scene_signature(scene)
        assert sig["has_plot_delta"] == "yes"

    def test_has_plot_delta_no(self):
        scene = {"outcome": ""}
        sig = compute_scene_signature(scene)
        assert sig["has_plot_delta"] == "no"

    def test_empty_scene(self):
        sig = compute_scene_signature({})
        assert sig["function"] == "MIXED"
        assert sig["emotional_mode"] == "MIXED"
        assert sig["location"] == ""
        assert sig["participants"] == "unknown"

    def test_interaction_type_discovery(self):
        scene = {"purpose": "She discovers the hidden letter and realizes the truth"}
        sig = compute_scene_signature(scene)
        assert sig["interaction_type"] == "discovery"

    def test_interaction_type_intimacy(self):
        scene = {"purpose": "They kiss passionately in the bedroom, desire overwhelming them"}
        sig = compute_scene_signature(scene)
        assert sig["interaction_type"] == "intimacy"


# === Helper Functions ===

class TestClassify:
    def test_returns_top_match(self):
        assert _classify("secret truth revealed confession", _SCENE_FUNCTIONS) == "REVEAL"

    def test_returns_mixed_for_no_hits(self):
        assert _classify("the cat sat on the mat", _SCENE_FUNCTIONS) == "MIXED"

    def test_returns_mixed_for_empty(self):
        assert _classify("", _SCENE_FUNCTIONS) == "MIXED"


class TestNormalizeLocation:
    def test_strips_articles(self):
        assert _normalize_location("The Kitchen") == "kitchen"

    def test_strips_prepositions(self):
        assert _normalize_location("At the Beach") == "beach"

    def test_lowercases(self):
        assert _normalize_location("ROOFTOP") == "rooftop"

    def test_collapses_whitespace(self):
        assert _normalize_location("  the  old  garden  ") == "old garden"


class TestExtractParticipants:
    def test_extracts_pov_and_names(self):
        scene = {"pov": "Valentina", "purpose": "Marco argues", "central_conflict": ""}
        result = _extract_participants(scene)
        assert "valentina" in result
        assert "marco" in result

    def test_returns_unknown_for_empty(self):
        assert _extract_participants({}) == "unknown"

    def test_deduplicates_pov_in_purpose(self):
        scene = {"pov": "Marco", "purpose": "Marco finds letter", "central_conflict": ""}
        result = _extract_participants(scene)
        # Marco should appear only once
        assert result.count("marco") == 1


class TestSignatureSimilarity:
    def test_identical_signatures(self):
        sig = {"function": "REVEAL", "emotional_mode": "conflict",
               "location": "kitchen", "participants": "marco+valentina",
               "interaction_type": "confrontation"}
        assert _signature_similarity(sig, sig) == 1.0

    def test_completely_different(self):
        sig_a = {"function": "REVEAL", "emotional_mode": "joy",
                 "location": "beach", "participants": "sofia",
                 "interaction_type": "bonding"}
        sig_b = {"function": "CONFLICT", "emotional_mode": "dread",
                 "location": "prison", "participants": "marco",
                 "interaction_type": "escape"}
        assert _signature_similarity(sig_a, sig_b) == 0.0

    def test_mixed_not_counted(self):
        """MIXED matches should not count as similarity."""
        sig_a = {"function": "MIXED", "emotional_mode": "MIXED",
                 "location": "MIXED", "participants": "MIXED",
                 "interaction_type": "MIXED"}
        sig_b = {"function": "MIXED", "emotional_mode": "MIXED",
                 "location": "MIXED", "participants": "MIXED",
                 "interaction_type": "MIXED"}
        assert _signature_similarity(sig_a, sig_b) == 0.0

    def test_partial_overlap(self):
        sig_a = {"function": "REVEAL", "emotional_mode": "conflict",
                 "location": "kitchen", "participants": "marco",
                 "interaction_type": "confrontation"}
        sig_b = {"function": "REVEAL", "emotional_mode": "joy",
                 "location": "beach", "participants": "marco",
                 "interaction_type": "bonding"}
        sim = _signature_similarity(sig_a, sig_b)
        assert 0.3 <= sim <= 0.5  # 2/5 match


# === Validate Outline Diversity ===

class TestValidateOutlineDiversity:
    def _make_outline(self, scenes_data):
        """Build an outline from a list of (chapter, scene_num, kwargs) tuples."""
        chapters = {}
        for ch, sc, kwargs in scenes_data:
            if ch not in chapters:
                chapters[ch] = {"chapter": ch, "scenes": []}
            scene = {"scene": sc, "scene_number": sc}
            scene.update(kwargs)
            chapters[ch]["scenes"].append(scene)
        return list(chapters.values())

    def test_pass_with_diverse_scenes(self):
        outline = self._make_outline([
            (1, 1, {"purpose": "She discovers the secret letter", "location": "attic",
                     "emotional_arc": "curiosity rises", "outcome": "finds clue"}),
            (1, 2, {"purpose": "Confrontation with Marco about betrayal", "location": "kitchen",
                     "emotional_arc": "anger erupts", "outcome": "he storms out"}),
            (1, 3, {"purpose": "Valentina bonds with Sofia over shared grief", "location": "park",
                     "emotional_arc": "tenderness and vulnerability", "outcome": "pact formed"}),
            (2, 1, {"purpose": "She decides to leave the city", "location": "apartment",
                     "emotional_arc": "determination", "outcome": "packs bags"}),
        ])
        report = validate_outline_diversity(outline)
        assert report["pass"] is True
        assert report["high_severity"] == 0

    def test_fail_adjacent_duplicates(self):
        """Two nearly identical scenes (same function, emotion, location, participants, interaction)."""
        outline = self._make_outline([
            (1, 1, {"purpose": "Valentina confronts Marco, they argue and clash about trust",
                     "location": "kitchen", "emotional_arc": "anger frustration tension conflict",
                     "outcome": "he storms out", "pov": "Valentina",
                     "central_conflict": "Valentina confronts Marco about trust"}),
            (1, 2, {"purpose": "Valentina confronts Marco again, they argue and clash about betrayal",
                     "location": "kitchen", "emotional_arc": "anger frustration tension conflict rage",
                     "outcome": "she storms out", "pov": "Valentina",
                     "central_conflict": "Valentina confronts Marco about betrayal"}),
            (1, 3, {"purpose": "Discovery of hidden letter in forest", "location": "forest",
                     "emotional_arc": "curiosity excitement wonder", "outcome": "finds clue"}),
            (2, 1, {"purpose": "Bonding with Sofia at the beach", "location": "beach",
                     "emotional_arc": "tender gentle warmth", "outcome": "trust deepens"}),
        ])
        report = validate_outline_diversity(outline)
        # Should flag the adjacent confrontation scenes
        adj_violations = [v for v in report["violations"] if v["type"] == "ADJACENT_DUPLICATE"]
        assert len(adj_violations) >= 1

    def test_fail_function_monotony(self):
        """All scenes with same function should trigger FUNCTION_MONOTONY."""
        outline = self._make_outline([
            (1, 1, {"purpose": "secret revealed", "location": "a", "outcome": "x"}),
            (1, 2, {"purpose": "truth discovered", "location": "b", "outcome": "y"}),
            (2, 1, {"purpose": "confession revealed", "location": "c", "outcome": "z"}),
            (2, 2, {"purpose": "hidden secret found", "location": "d", "outcome": "w"}),
        ])
        report = validate_outline_diversity(outline, max_same_function_ratio=0.40)
        mono_violations = [v for v in report["violations"] if v["type"] == "FUNCTION_MONOTONY"]
        assert len(mono_violations) >= 1
        assert mono_violations[0]["function"] == "REVEAL"

    def test_fail_emotional_monotony(self):
        outline = self._make_outline([
            (1, 1, {"purpose": "A", "emotional_arc": "anger and frustration rise", "outcome": "x"}),
            (1, 2, {"purpose": "B", "emotional_arc": "bitter tension builds", "outcome": "y"}),
            (2, 1, {"purpose": "C", "emotional_arc": "rage and conflict erupt", "outcome": "z"}),
            (2, 2, {"purpose": "D", "emotional_arc": "angry confrontation", "outcome": "w"}),
        ])
        report = validate_outline_diversity(outline, max_same_function_ratio=0.40)
        emo_violations = [v for v in report["violations"] if v["type"] == "EMOTIONAL_MONOTONY"]
        assert len(emo_violations) >= 1

    def test_fail_location_clustering(self):
        """5+ scenes in same location should flag LOCATION_CLUSTERING."""
        outline = self._make_outline([
            (1, 1, {"purpose": "A", "location": "kitchen", "outcome": "x"}),
            (1, 2, {"purpose": "B", "location": "kitchen", "outcome": "y"}),
            (2, 1, {"purpose": "C", "location": "kitchen", "outcome": "z"}),
            (2, 2, {"purpose": "D", "location": "kitchen", "outcome": "w"}),
            (3, 1, {"purpose": "E", "location": "kitchen", "outcome": "v"}),
            (3, 2, {"purpose": "F", "location": "kitchen", "outcome": "u"}),
        ])
        report = validate_outline_diversity(outline)
        loc_violations = [v for v in report["violations"] if v["type"] == "LOCATION_CLUSTERING"]
        assert len(loc_violations) >= 1

    def test_window_duplicates(self):
        """Non-adjacent similar scenes within window should flag WINDOW_DUPLICATE."""
        outline = self._make_outline([
            (1, 1, {"purpose": "Confrontation about trust", "location": "kitchen",
                     "emotional_arc": "anger", "outcome": "fight", "pov": "Val",
                     "central_conflict": "trust"}),
            (1, 2, {"purpose": "Discovery of letter", "location": "attic",
                     "emotional_arc": "curiosity", "outcome": "finds clue"}),
            (1, 3, {"purpose": "Bonding with friend", "location": "park",
                     "emotional_arc": "tenderness", "outcome": "pact"}),
            (2, 1, {"purpose": "Confrontation about betrayal", "location": "kitchen",
                     "emotional_arc": "anger", "outcome": "fight escalates", "pov": "Val",
                     "central_conflict": "betrayal"}),
        ])
        report = validate_outline_diversity(outline, window=5, window_threshold=0.60)
        win_violations = [v for v in report["violations"] if v["type"] == "WINDOW_DUPLICATE"]
        # Scene 1 and 4 are similar but not adjacent → window duplicate
        assert len(win_violations) >= 1

    def test_too_few_scenes_passes(self):
        """Less than 3 scenes should always pass (not enough data)."""
        outline = self._make_outline([
            (1, 1, {"purpose": "A", "outcome": "x"}),
            (1, 2, {"purpose": "B", "outcome": "y"}),
        ])
        report = validate_outline_diversity(outline)
        assert report["pass"] is True
        assert report["total_scenes"] == 2

    def test_empty_outline(self):
        report = validate_outline_diversity([])
        assert report["pass"] is True
        assert report["total_scenes"] == 0

    def test_none_outline(self):
        report = validate_outline_diversity(None)
        assert report["pass"] is True

    def test_report_includes_distributions(self):
        outline = self._make_outline([
            (1, 1, {"purpose": "secret revealed", "emotional_arc": "fear", "location": "attic", "outcome": "x"}),
            (1, 2, {"purpose": "they bond together", "emotional_arc": "joy", "location": "park", "outcome": "y"}),
            (2, 1, {"purpose": "confrontation fight", "emotional_arc": "anger", "location": "kitchen", "outcome": "z"}),
        ])
        report = validate_outline_diversity(outline)
        assert "function_distribution" in report
        assert "emotional_distribution" in report
        assert "location_distribution" in report

    def test_custom_thresholds(self):
        """Very strict thresholds should flag more violations."""
        outline = self._make_outline([
            (1, 1, {"purpose": "A reveals secret", "location": "house", "outcome": "x"}),
            (1, 2, {"purpose": "B reveals truth", "location": "office", "outcome": "y"}),
            (2, 1, {"purpose": "C discovers hidden", "location": "park", "outcome": "z"}),
        ])
        # With very strict max_same_function_ratio, should flag REVEAL monotony
        report = validate_outline_diversity(outline, max_same_function_ratio=0.30)
        assert len(report["violations"]) > 0


# === Suggest Fix ===

class TestSuggestFix:
    def test_suggests_location_change(self):
        sig_a = {"location": "kitchen", "function": "A", "emotional_mode": "B", "interaction_type": "C"}
        sig_b = {"location": "kitchen", "function": "X", "emotional_mode": "Y", "interaction_type": "Z"}
        suggestion = _suggest_fix(sig_a, sig_b, {}, {})
        assert "location" in suggestion.lower()

    def test_suggests_interaction_change(self):
        sig_a = {"location": "a", "function": "X", "emotional_mode": "B", "interaction_type": "confrontation"}
        sig_b = {"location": "b", "function": "Y", "emotional_mode": "Z", "interaction_type": "confrontation"}
        suggestion = _suggest_fix(sig_a, sig_b, {}, {})
        assert "interaction" in suggestion.lower()

    def test_fallback_suggestion(self):
        sig_a = {"location": "a", "function": "X", "emotional_mode": "B", "interaction_type": "C"}
        sig_b = {"location": "b", "function": "Y", "emotional_mode": "Z", "interaction_type": "D"}
        suggestion = _suggest_fix(sig_a, sig_b, {}, {})
        assert "differentiate" in suggestion.lower()


# === Format Report ===

class TestFormatDiversityReport:
    def test_formats_passing_report(self):
        report = {
            "pass": True, "total_scenes": 10,
            "high_severity": 0, "medium_severity": 0, "low_severity": 0,
            "violations": [], "function_distribution": {"REVEAL": 3, "CONFLICT": 4},
            "emotional_distribution": {}, "location_distribution": {},
        }
        text = format_diversity_report(report)
        assert "PASS" in text or "YES" in text
        assert "10" in text

    def test_formats_failing_report(self):
        report = {
            "pass": False, "total_scenes": 5,
            "high_severity": 1, "medium_severity": 0, "low_severity": 0,
            "violations": [{
                "type": "FUNCTION_MONOTONY", "severity": "high",
                "function": "REVEAL", "count": 4, "total": 5,
                "ratio": 0.80, "suggestion": "diversify",
            }],
            "function_distribution": {}, "emotional_distribution": {},
            "location_distribution": {},
        }
        text = format_diversity_report(report)
        assert "NO" in text
        assert "FUNCTION_MONOTONY" in text
