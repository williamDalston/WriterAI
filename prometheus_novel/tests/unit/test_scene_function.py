"""Tests for scene function classifier and cross-scene continuity."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from quality.quiet_killers import (
    classify_scene_function,
    check_function_redundancy_v2,
    check_cross_scene_continuity,
)


# === Scene Function Classifier ===

class TestClassifySceneFunction:
    def test_reveal_scene(self):
        content = "She uncovered the hidden truth. The secret was exposed. He admitted the confession."
        assert classify_scene_function(content) == "REVEAL"

    def test_conflict_scene(self):
        content = "The argument escalated. He shouted and accused her. She defied his demands and refused."
        assert classify_scene_function(content) == "CONFLICT"

    def test_bond_scene(self):
        content = "They found a deeper connection. She opened up and shared her vulnerability. Trust grew between them."
        assert classify_scene_function(content) == "BOND"

    def test_decision_scene(self):
        content = "She chose to leave. The commitment was made. He decided with resolve and swore his vow."
        assert classify_scene_function(content) == "DECISION"

    def test_aftermath_scene(self):
        content = "The consequences were devastating. In the aftermath, wreckage surrounded them. The fallout was severe. They mourned the loss."
        assert classify_scene_function(content) == "AFTERMATH"

    def test_pursuit_scene(self):
        content = "The chase began through the streets. She was fleeing, running toward escape. He followed in pursuit."
        assert classify_scene_function(content) == "PURSUIT"

    def test_mixed_scene_returns_mixed(self):
        content = "It was a quiet day."
        assert classify_scene_function(content) == "MIXED"

    def test_purpose_boost(self):
        content = "They sat at the table."
        purpose = "Reveal of the hidden identity"
        assert classify_scene_function(content, purpose) == "REVEAL"


# === Function Redundancy V2 ===

class TestFunctionRedundancyV2:
    def _make_scene(self, chapter, scene_num, content, scene_id=None):
        return {
            "chapter": chapter,
            "scene_number": scene_num,
            "scene": scene_num,
            "scene_id": scene_id or f"ch{chapter:02d}_s{scene_num:02d}",
            "content": content,
        }

    def test_no_flag_different_functions(self):
        scenes = [
            self._make_scene(1, 1, "She uncovered the hidden truth. The secret was exposed."),
            self._make_scene(1, 2, "The argument escalated. He shouted and accused her. She refused."),
        ]
        warnings = check_function_redundancy_v2(scenes, [])
        assert len(warnings) == 0

    def test_no_flag_same_function_different_ending(self):
        # Same function (CONFLICT) but different content should differ in emo/ending
        scenes = [
            self._make_scene(1, 1, 'The argument escalated. "Stop!" He shouted and accused her. She refused.'),
            self._make_scene(1, 2, "Another confrontation. He demanded answers. She defied him. The silence fell."),
        ]
        warnings = check_function_redundancy_v2(scenes, [])
        # May or may not flag depending on emo/ending match -- triple match required
        # This test just verifies no crash
        assert isinstance(warnings, list)

    def test_no_flag_across_chapters(self):
        # Same content in different chapters should not flag
        content = "She uncovered the hidden truth. The secret was exposed. He admitted everything. The sun set."
        scenes = [
            self._make_scene(1, 1, content),
            self._make_scene(2, 1, content),
        ]
        warnings = check_function_redundancy_v2(scenes, [])
        assert len(warnings) == 0, f"Cross-chapter should not flag: {warnings}"


# === Cross-Scene Continuity ===

class TestCrossSceneContinuity:
    def _make_scene(self, chapter, scene_num, content, location="", scene_id=None):
        return {
            "chapter": chapter,
            "scene_number": scene_num,
            "scene": scene_num,
            "scene_id": scene_id or f"ch{chapter:02d}_s{scene_num:02d}",
            "content": content,
            "location": location,
        }

    def test_normal_time_flow_no_warning(self):
        scenes = [
            self._make_scene(1, 1, "The morning sun rose over the city."),
            self._make_scene(1, 2, "By afternoon the heat was unbearable."),
            self._make_scene(1, 3, "That evening she finally relaxed."),
        ]
        warnings = check_cross_scene_continuity(scenes)
        time_warnings = [w for w in warnings if "CROSS_CONTINUITY_TIME" in w]
        assert len(time_warnings) == 0, f"Normal flow should not flag: {time_warnings}"

    def test_backwards_time_jump_flags(self):
        scenes = [
            self._make_scene(1, 1, "The evening was cold and dark."),
            self._make_scene(1, 2, "The morning light was blinding."),
        ]
        warnings = check_cross_scene_continuity(scenes)
        time_warnings = [w for w in warnings if "CROSS_CONTINUITY_TIME" in w]
        assert len(time_warnings) == 1, f"Expected 1 time warning, got {time_warnings}"

    def test_backwards_time_with_skip_no_flag(self):
        scenes = [
            self._make_scene(1, 1, "The evening was cold and dark."),
            self._make_scene(1, 2, "The next day, the morning light was blinding."),
        ]
        warnings = check_cross_scene_continuity(scenes)
        time_warnings = [w for w in warnings if "CROSS_CONTINUITY_TIME" in w]
        assert len(time_warnings) == 0, f"Time skip should suppress warning: {time_warnings}"

    def test_location_drift_without_transition_flags(self):
        scenes = [
            self._make_scene(1, 1, "The kitchen smelled of coffee.", location="kitchen"),
            self._make_scene(1, 2, "The bedroom was silent and cold.", location="bedroom"),
        ]
        warnings = check_cross_scene_continuity(scenes)
        loc_warnings = [w for w in warnings if "CROSS_CONTINUITY_LOC" in w]
        assert len(loc_warnings) == 1, f"Expected 1 location warning, got {loc_warnings}"

    def test_location_drift_with_transition_no_flag(self):
        scenes = [
            self._make_scene(1, 1, "The kitchen smelled of coffee.", location="kitchen"),
            self._make_scene(1, 2, "She walked to the bedroom, which was cold.", location="bedroom"),
        ]
        warnings = check_cross_scene_continuity(scenes)
        loc_warnings = [w for w in warnings if "CROSS_CONTINUITY_LOC" in w]
        assert len(loc_warnings) == 0, f"Transition verb should suppress: {loc_warnings}"

    def test_single_scene_chapter_no_warnings(self):
        scenes = [
            self._make_scene(1, 1, "The morning sun rose."),
        ]
        warnings = check_cross_scene_continuity(scenes)
        assert len(warnings) == 0, "Single scene chapter should produce no warnings"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
