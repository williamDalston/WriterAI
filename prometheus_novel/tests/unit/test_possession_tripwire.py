"""Tests for object possession continuity tripwires.

Covers within-scene and cross-scene detection of:
- POSSESSION_GHOST: object used after being set down
- POSSESSION_DOUBLE_DROP: object released twice without re-acquiring
- CROSS_POSSESSION_GHOST: object used in scene N+1 after release in scene N
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from quality.quiet_killers import (
    check_continuity_tripwires,
    check_cross_scene_continuity,
    _check_object_possession,
    _extract_end_of_scene_objects,
)


# ============================================================================
# 1. Within-scene: POSSESSION_GHOST
# ============================================================================


class TestPossessionGhost:
    """Object used after being set down without re-acquiring."""

    def test_sipped_after_set_down(self):
        content = (
            "I picked up the cup and took a long sip.\n\n"
            "The conversation grew tense. I set down the cup on the counter.\n\n"
            "My hands were shaking. I sipped the cup again to calm my nerves."
        )
        warnings = check_continuity_tripwires(content)
        ghost = [w for w in warnings if "POSSESSION_GHOST" in w]
        assert len(ghost) == 1
        assert "cup" in ghost[0]

    def test_no_ghost_when_reacquired(self):
        content = (
            "I grabbed the glass from the shelf.\n\n"
            "I set down the glass on the table.\n\n"
            "A moment later I picked up the glass and drank from the glass."
        )
        warnings = check_continuity_tripwires(content)
        ghost = [w for w in warnings if "POSSESSION_GHOST" in w]
        assert len(ghost) == 0

    def test_no_ghost_without_release(self):
        content = (
            "I picked up the phone and scrolled through messages.\n\n"
            "The screen glowed in the dark. I checked the phone again."
        )
        warnings = check_continuity_tripwires(content)
        ghost = [w for w in warnings if "POSSESSION_GHOST" in w]
        assert len(ghost) == 0

    def test_no_false_positive_on_clean_prose(self):
        content = (
            "The morning light filtered through the curtains.\n\n"
            "She crossed the room and sat by the window.\n\n"
            "The silence stretched between us, heavy and warm."
        )
        warnings = check_continuity_tripwires(content)
        ghost = [w for w in warnings if "POSSESSION" in w]
        assert len(ghost) == 0

    def test_multiple_objects_tracked_independently(self):
        content = (
            "I grabbed the phone and the keys from the counter.\n\n"
            "I dropped the keys into my pocket. I set down the phone on the table.\n\n"
            "I checked the phone one more time before leaving."
        )
        warnings = check_continuity_tripwires(content)
        ghost = [w for w in warnings if "POSSESSION_GHOST" in w]
        assert len(ghost) == 1
        assert "phone" in ghost[0]


# ============================================================================
# 2. Within-scene: POSSESSION_DOUBLE_DROP
# ============================================================================


class TestPossessionDoubleDrop:
    """Object released twice without re-acquiring."""

    def test_double_release_flagged(self):
        content = (
            "I grabbed the glass of wine.\n\n"
            "I set down the glass carefully.\n\n"
            "I put down the glass again and turned away."
        )
        warnings = check_continuity_tripwires(content)
        double = [w for w in warnings if "DOUBLE_DROP" in w]
        assert len(double) == 1
        assert "glass" in double[0]

    def test_release_then_acquire_then_release_is_fine(self):
        content = (
            "I grabbed the book from the shelf.\n\n"
            "I set down the book on the desk.\n\n"
            "I picked up the book again, then put down the book for good."
        )
        warnings = check_continuity_tripwires(content)
        double = [w for w in warnings if "DOUBLE_DROP" in w]
        assert len(double) == 0


# ============================================================================
# 2b. Intra-paragraph event ordering
# ============================================================================


class TestIntraParagraphOrdering:
    """Events in a single paragraph must be processed in text order."""

    def test_release_then_reacquire_then_use_no_ghost(self):
        """Release before acquire in same paragraph should not false-positive."""
        content = (
            "I grabbed the glass from the bar.\n\n"
            "I set down the glass, then picked up the glass and sipped the glass."
        )
        warnings = check_continuity_tripwires(content)
        ghost = [w for w in warnings if "POSSESSION_GHOST" in w]
        assert len(ghost) == 0, f"Should not flag ghost after re-acquire: {ghost}"

    def test_acquire_then_release_then_use_flags_ghost(self):
        """Acquire then release then use in same paragraph = ghost."""
        content = (
            "I picked up the cup, set down the cup on the table, then sipped the cup."
        )
        warnings = check_continuity_tripwires(content)
        ghost = [w for w in warnings if "POSSESSION_GHOST" in w]
        assert len(ghost) == 1, f"Should flag ghost: acquire→release→use in one para"


# ============================================================================
# 3. Cross-scene: CROSS_POSSESSION_GHOST
# ============================================================================


class TestCrossScenePossession:
    """Object used in scene N+1 after being released in scene N."""

    def test_cross_scene_ghost_detected(self):
        scenes = [
            {
                "chapter": 1, "scene_number": 1, "scene_id": "ch01_s01",
                "content": (
                    "I grabbed the cup of coffee.\n\n"
                    "We talked for a while. I set down the cup."
                ),
            },
            {
                "chapter": 1, "scene_number": 2, "scene_id": "ch01_s02",
                "content": (
                    "The next morning, I sipped the cup slowly."
                ),
            },
        ]
        warnings = check_cross_scene_continuity(scenes)
        ghost = [w for w in warnings if "CROSS_POSSESSION_GHOST" in w]
        assert len(ghost) == 1
        assert "cup" in ghost[0]
        assert "ch01_s02" in ghost[0]

    def test_no_cross_ghost_when_reacquired(self):
        scenes = [
            {
                "chapter": 1, "scene_number": 1, "scene_id": "ch01_s01",
                "content": (
                    "I grabbed the phone. I set down the phone on the counter."
                ),
            },
            {
                "chapter": 1, "scene_number": 2, "scene_id": "ch01_s02",
                "content": (
                    "I picked up the phone again. I checked the phone for messages."
                ),
            },
        ]
        warnings = check_cross_scene_continuity(scenes)
        ghost = [w for w in warnings if "CROSS_POSSESSION_GHOST" in w]
        assert len(ghost) == 0

    def test_no_cross_ghost_across_chapters(self):
        """Cross-scene checks are within-chapter only."""
        scenes = [
            {
                "chapter": 1, "scene_number": 1, "scene_id": "ch01_s01",
                "content": "I grabbed the knife. I set down the knife.",
            },
            {
                "chapter": 2, "scene_number": 1, "scene_id": "ch02_s01",
                "content": "I swung the knife at the rope.",
            },
        ]
        warnings = check_cross_scene_continuity(scenes)
        ghost = [w for w in warnings if "CROSS_POSSESSION_GHOST" in w]
        assert len(ghost) == 0

    def test_no_false_positive_clean_scenes(self):
        scenes = [
            {
                "chapter": 1, "scene_number": 1, "scene_id": "ch01_s01",
                "content": "The room was dark. She stood by the window.",
            },
            {
                "chapter": 1, "scene_number": 2, "scene_id": "ch01_s02",
                "content": "Morning came. I walked to the kitchen.",
            },
        ]
        warnings = check_cross_scene_continuity(scenes)
        ghost = [w for w in warnings if "POSSESSION" in w]
        assert len(ghost) == 0


# ============================================================================
# 4. Helper functions
# ============================================================================


class TestObjectStateExtraction:
    """Test _extract_end_of_scene_objects helper."""

    def test_held_at_end(self):
        content = "I picked up the glass and walked out."
        state = _extract_end_of_scene_objects(content)
        assert state.get("glass") == "HELD"

    def test_released_at_end(self):
        content = (
            "I grabbed the phone.\n\n"
            "I set down the phone on the table."
        )
        state = _extract_end_of_scene_objects(content)
        assert state.get("phone") == "RELEASED"

    def test_empty_content(self):
        state = _extract_end_of_scene_objects("")
        assert state == {}

    def test_no_objects(self):
        content = "The sky was gray. She spoke softly."
        state = _extract_end_of_scene_objects(content)
        assert state == {}


# ============================================================================
# 5. Existing tripwires still work (regression)
# ============================================================================


class TestExistingTripwiresRegression:
    """Ensure time/location drift checks are unbroken."""

    def test_time_drift_still_detected(self):
        content = (
            "The morning sun was bright.\n\n"
            "The midnight sky loomed overhead."
        )
        warnings = check_continuity_tripwires(content)
        time_w = [w for w in warnings if "shifts time" in w]
        assert len(time_w) == 1

    def test_location_drift_still_detected(self):
        content = (
            "We sat in the kitchen together.\n\n"
            "The courtroom was silent and cold."
        )
        warnings = check_continuity_tripwires(content)
        loc_w = [w for w in warnings if "shifts location" in w]
        assert len(loc_w) == 1

    def test_no_false_positive_with_transition(self):
        content = (
            "We sat in the kitchen together.\n\n"
            "I walked down the hallway to the bedroom."
        )
        warnings = check_continuity_tripwires(content)
        loc_w = [w for w in warnings if "shifts location" in w]
        assert len(loc_w) == 0
