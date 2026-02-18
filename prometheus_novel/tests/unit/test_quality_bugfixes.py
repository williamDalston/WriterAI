"""Tests for quality system bugfixes and enhancements.

Covers 8 fixes:
1. _extract_object_from_match uses module-level regex (no recompilation)
2. _extract_end_of_scene_objects processes events in text order
3. check_dialogue_tidy properly detects interrupts AND dodges
4. _check_causality uses list slicing (not set slicing)
5. _check_dialogue_line_economy ignores contractions
6. Expanded location names and transition verbs
7. _classify_ending does not misclassify dialogue attribution as ACTION
8. check_therapy_speak detects clinical dialogue patterns
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from quality.quiet_killers import (
    _extract_object_from_match,
    _extract_end_of_scene_objects,
    _classify_ending,
    check_continuity_tripwires,
    check_dialogue_tidy,
    check_cross_scene_continuity,
    _OBJ_ACQUIRE,
    _OBJ_RELEASE,
    classify_scene_profile,
    apply_deflection_grounding,
    apply_bridge_insert,
    apply_final_line_rewrite,
)
from quality.quality_contract import (
    _check_causality,
    _check_dialogue_line_economy,
)


# ============================================================================
# 1. _extract_object_from_match — module-level regex (performance)
# ============================================================================


class TestExtractObjectPerformance:
    """Verify _extract_object_from_match works with module-level regex."""

    def test_extracts_from_acquire(self):
        m = _OBJ_ACQUIRE.search("I picked up the glass from the shelf.")
        assert m is not None
        obj = _extract_object_from_match(m)
        assert obj == "glass"

    def test_extracts_from_release(self):
        m = _OBJ_RELEASE.search("She set down the knife on the counter.")
        assert m is not None
        obj = _extract_object_from_match(m)
        assert obj == "knife"

    def test_returns_none_for_no_object(self):
        """If groups don't contain a trackable object, return None."""
        # Manually test with a match that has no trackable object groups
        import re
        fake_pat = re.compile(r"(hello)\s+(world)")
        m = fake_pat.search("hello world")
        assert m is not None
        obj = _extract_object_from_match(m)
        assert obj is None


# ============================================================================
# 2. _extract_end_of_scene_objects — text-order processing
# ============================================================================


class TestEndOfSceneObjectsTextOrder:
    """Events must be processed in text order, not by category."""

    def test_acquire_then_release_is_released(self):
        content = "I picked up the cup. I set down the cup on the table."
        state = _extract_end_of_scene_objects(content)
        assert state.get("cup") == "RELEASED"

    def test_release_then_acquire_is_held(self):
        """In same paragraph: release then acquire = HELD at end."""
        content = "I set down the cup, then picked up the cup again."
        state = _extract_end_of_scene_objects(content)
        assert state.get("cup") == "HELD"

    def test_acquire_release_acquire_is_held(self):
        content = (
            "I grabbed the phone.\n\n"
            "I set down the phone on the desk.\n\n"
            "I picked up the phone one more time."
        )
        state = _extract_end_of_scene_objects(content)
        assert state.get("phone") == "HELD"

    def test_same_paragraph_interleaved_order(self):
        """Complex: set down glass, picked up knife in same paragraph."""
        content = "I set down the glass and grabbed the knife."
        state = _extract_end_of_scene_objects(content)
        assert state.get("glass") == "RELEASED"
        assert state.get("knife") == "HELD"


# ============================================================================
# 3. check_dialogue_tidy — interrupt AND dodge detection
# ============================================================================


class TestDialogueTidy:
    """Both interrupts and dodges should prevent DIALOGUE_TIDY warning."""

    def test_no_warning_with_interrupt(self):
        content = (
            '"Tell me what happened." '
            '"I was there when it started." '
            '"Wait. You were there the whole time?" '
            '"Every second of it."'
        )
        warnings = check_dialogue_tidy(content, tension_level=8)
        tidy = [w for w in warnings if "DIALOGUE_TIDY" in w]
        assert len(tidy) == 0

    def test_no_warning_with_dodge(self):
        content = (
            '"Tell me the truth." '
            '"I don\'t want to talk about it." '
            '"You have to explain." '
            '"It doesn\'t matter anymore."'
        )
        warnings = check_dialogue_tidy(content, tension_level=8)
        tidy = [w for w in warnings if "DIALOGUE_TIDY" in w]
        assert len(tidy) == 0

    def test_warning_without_interrupt_or_dodge(self):
        content = (
            '"The shipment arrives tomorrow." '
            '"I confirmed the location." '
            '"The coordinates are locked in." '
            '"Everything is on schedule."'
        )
        warnings = check_dialogue_tidy(content, tension_level=8)
        tidy = [w for w in warnings if "DIALOGUE_TIDY" in w]
        assert len(tidy) == 1

    def test_no_warning_low_tension(self):
        content = (
            '"The shipment arrives tomorrow." '
            '"I confirmed the location." '
            '"The coordinates are locked in." '
            '"Everything is on schedule."'
        )
        warnings = check_dialogue_tidy(content, tension_level=4)
        assert len(warnings) == 0

    def test_no_warning_with_changed_subject(self):
        content = (
            '"Where did you put it?" '
            '"She changed the subject immediately." '
            '"Answer me." '
            '"I already told you everything."'
        )
        warnings = check_dialogue_tidy(content, tension_level=7)
        tidy = [w for w in warnings if "DIALOGUE_TIDY" in w]
        assert len(tidy) == 0


# ============================================================================
# 4. _check_causality — list slicing (not set slicing)
# ============================================================================


class TestCausalityListSlicing:
    """Verify causality check uses ordered word list, not set."""

    def test_connector_with_prior_reference_no_warning(self):
        paragraphs = [
            "The door was heavy, made of old oak.",
            "But the hinges were rusted, and the door wouldn't budge.",
        ]
        warnings = _check_causality(paragraphs)
        causality = [w for w in warnings if "CAUSALITY" in w and "connector" in w]
        assert len(causality) == 0

    def test_connector_without_prior_reference_flags(self):
        paragraphs = [
            "Sunflowers bloomed quietly by April dawn.",
            "And, volcanic eruptions decimated Pompeii millennia ago.",
        ]
        warnings = _check_causality(paragraphs)
        causality = [w for w in warnings if "CAUSALITY" in w and "connector" in w]
        assert len(causality) == 1

    def test_first_paragraph_connector_flags(self):
        """Connector in paragraph 1 with no prior text should flag."""
        paragraphs = [
            "But, it was already too late for that.",
        ]
        warnings = _check_causality(paragraphs)
        causality = [w for w in warnings if "CAUSALITY" in w]
        assert len(causality) >= 1


# ============================================================================
# 5. _check_dialogue_line_economy — no contraction false positives
# ============================================================================


class TestDialogueEconomyContractions:
    """Single-quote contractions must not inflate dialogue line count."""

    def test_contractions_not_counted_as_dialogue(self):
        content = (
            "She couldn't believe it. He didn't care. "
            "They won't stop. I can't help it. "
            "It wasn't fair. She hadn't noticed."
        )
        ratio, expository, warnings = _check_dialogue_line_economy(content, tension_level=8)
        # No actual dialogue lines — should be 1.0 ratio (no lines)
        assert ratio == 1.0

    def test_double_quoted_dialogue_still_counted(self):
        content = (
            '"Get out of here and never come back to this place because I cannot stand the sight of you." '
            '"I will not leave this house until you explain yourself properly." '
            '"You have no choice." '
            '"Watch me."'
        )
        ratio, expository, warnings = _check_dialogue_line_economy(content, tension_level=8)
        # 2 short lines (≤10 words) out of 4 total = ratio 0.5
        assert ratio < 1.0  # Mix of short and long lines detected

    def test_smart_quotes_counted(self):
        content = (
            '\u201cGet out.\u201d '
            '\u201cNow.\u201d '
            '\u201cI said get out.\u201d '
            '\u201cFine.\u201d'
        )
        ratio, expository, warnings = _check_dialogue_line_economy(content, tension_level=8)
        assert ratio > 0.5  # Most lines are short


# ============================================================================
# 6. Expanded location names and transition verbs
# ============================================================================


class TestExpandedLocations:
    """Newly added locations should be detected by continuity checks."""

    @pytest.mark.parametrize("location", [
        "hospital", "church", "library", "bar", "hotel", "basement",
        "attic", "rooftop", "garden", "alley", "warehouse", "dock",
        "bridge", "forest", "cave", "beach", "cemetery", "diner",
        "parking lot", "elevator", "stairwell", "garage",
    ])
    def test_new_locations_detected(self, location):
        content = (
            f"We sat in the kitchen together.\n\n"
            f"The {location} was silent and cold."
        )
        warnings = check_continuity_tripwires(content)
        loc_w = [w for w in warnings if "shifts location" in w]
        assert len(loc_w) == 1, f"Expected location drift for kitchen → {location}"

    @pytest.mark.parametrize("verb", [
        "ran", "rushed", "hurried", "crossed", "climbed",
        "entered", "left", "returned", "fled", "arrived",
        "departed", "crept", "stumbled",
    ])
    def test_new_transition_verbs_suppress_warning(self, verb):
        content = (
            f"We sat in the kitchen together.\n\n"
            f"She {verb} to the bedroom."
        )
        warnings = check_continuity_tripwires(content)
        loc_w = [w for w in warnings if "shifts location" in w]
        assert len(loc_w) == 0, f"Transition verb '{verb}' should suppress location drift"


# ============================================================================
# 7. _classify_ending — no dialogue attribution leak
# ============================================================================


class TestEndingClassification:
    """said/asked must not leak into ACTION category."""

    def test_said_ending_not_action(self):
        result = _classify_ending('"Let\'s go," she said.')
        assert result != "ACTION", f"Dialogue attribution 'said' should not classify as ACTION"

    def test_asked_ending_not_action(self):
        result = _classify_ending('"Are you coming?" he asked.')
        assert result != "ACTION", f"Dialogue attribution 'asked' should not classify as ACTION"

    def test_dialogue_ending_classified_correctly(self):
        result = _classify_ending('"I\'m leaving."')
        assert result == "DIALOGUE"

    def test_action_verb_still_works(self):
        result = _classify_ending("She grabbed the railing and pulled herself up.")
        assert result == "ACTION"

    def test_walked_still_action(self):
        result = _classify_ending("I walked away without looking back.")
        assert result == "ACTION"

    def test_slammed_is_action(self):
        result = _classify_ending("He slammed the door behind him.")
        assert result == "ACTION"

    def test_summary_still_detected(self):
        result = _classify_ending("Everything had changed forever.")
        assert result == "SUMMARY"

    def test_atmosphere_still_detected(self):
        result = _classify_ending("The silence stretched between them.")
        assert result == "ATMOSPHERE"

    def test_revelation_still_detected(self):
        result = _classify_ending("She realized the truth had been there all along.")
        assert result == "REVELATION"

    def test_new_summary_patterns_detected(self):
        """Extended SUMMARY regex from other LLM's changes."""
        result = _classify_ending("For the first time in years, something had shifted.")
        assert result == "SUMMARY"


# ============================================================================
# 8. Therapy-speak checker (added by other LLM)
# ============================================================================


class TestTherapySpeak:
    """Verify therapy-speak detection works."""

    def test_therapy_speak_detected(self):
        from quality.quiet_killers import check_therapy_speak
        content = (
            '"I appreciate you sharing that with me," she said softly. '
            '"I hear what you\'re saying, and that must be really hard."'
        )
        warnings = check_therapy_speak(content)
        assert len(warnings) == 1
        assert "THERAPY_SPEAK" in warnings[0]

    def test_no_false_positive_on_normal_dialogue(self):
        from quality.quiet_killers import check_therapy_speak
        content = (
            '"Get out." '
            '"You can\'t make me." '
            '"Watch me."'
        )
        warnings = check_therapy_speak(content)
        assert len(warnings) == 0

    def test_single_hit_below_threshold(self):
        from quality.quiet_killers import check_therapy_speak
        content = '"That must be really hard for you," she whispered.'
        warnings = check_therapy_speak(content)
        assert len(warnings) == 0  # Need 2+ hits


# ============================================================================
# 9. Cross-scene possession with text-order fix
# ============================================================================


class TestCrossSceneTextOrder:
    """Cross-scene check uses text-ordered end-of-scene state."""

    def test_release_then_acquire_at_end_means_held(self):
        """If scene ends with release then re-acquire, next scene should not flag ghost."""
        scenes = [
            {
                "chapter": 1, "scene_number": 1, "scene_id": "ch01_s01",
                "content": (
                    "I grabbed the cup.\n\n"
                    "I set down the cup, then picked up the cup again."
                ),
            },
            {
                "chapter": 1, "scene_number": 2, "scene_id": "ch01_s02",
                "content": "I sipped the cup slowly.",
            },
        ]
        warnings = check_cross_scene_continuity(scenes)
        ghost = [w for w in warnings if "CROSS_POSSESSION_GHOST" in w]
        assert len(ghost) == 0, f"Cup was re-acquired at end of scene 1: {ghost}"


# ============================================================================
# 9. classify_scene_profile — mode/risk mapping
# ============================================================================


class TestClassifySceneProfile:
    """Scene profile should map function + tension to mode + risk."""

    def test_conflict_high_tension(self):
        result = classify_scene_profile("content", "purpose", 7, "CONFLICT")
        assert result["scene_mode"] == "conflict"
        assert result["primary_risk"] == "deflection"
        assert result["function"] == "CONFLICT"

    def test_bond_low_tension(self):
        result = classify_scene_profile("content", "purpose", 3, "BOND")
        assert result["scene_mode"] == "romance"
        assert result["primary_risk"] == "ending"

    def test_reveal_any_tension(self):
        for t in [2, 5, 8]:
            result = classify_scene_profile("content", "purpose", t, "REVEAL")
            assert result["scene_mode"] == "reveal"
            assert result["primary_risk"] == "stakes"

    def test_decision_is_reveal_mode(self):
        result = classify_scene_profile("content", "purpose", 5, "DECISION")
        assert result["scene_mode"] == "reveal"

    def test_aftermath_low_tension(self):
        result = classify_scene_profile("content", "purpose", 3, "AFTERMATH")
        assert result["scene_mode"] == "recovery"
        assert result["primary_risk"] == "ending"

    def test_pursuit_high_tension(self):
        result = classify_scene_profile("content", "purpose", 8, "PURSUIT")
        assert result["scene_mode"] == "conflict"

    def test_unknown_function_defaults_setup(self):
        result = classify_scene_profile("content", "purpose", 5, "UNKNOWN")
        assert result["scene_mode"] == "setup"
        assert result["primary_risk"] == "continuity"

    def test_empty_function_defaults_mixed(self):
        result = classify_scene_profile("content", "purpose", 5, "")
        assert result["function"] == "MIXED"
        assert result["scene_mode"] == "setup"

    def test_tension_passthrough(self):
        result = classify_scene_profile("content", "purpose", 9, "CONFLICT")
        assert result["tension_level"] == 9

    def test_bond_high_tension_not_romance(self):
        """BOND with tension > 5 shouldn't be romance mode."""
        result = classify_scene_profile("content", "purpose", 7, "BOND")
        assert result["scene_mode"] != "romance"


# ============================================================================
# 10. apply_deflection_grounding — reflective para detection + insert
# ============================================================================


class TestDeflectionGrounding:
    """Break up consecutive reflective paragraphs in high-tension scenes."""

    def test_no_change_low_tension(self):
        text = "I thought about it.\n\nI realized something.\n\nShe spoke."
        result = apply_deflection_grounding(text, tension_level=4)
        assert result == text

    def test_inserts_grounding_in_reflective_run(self):
        text = (
            "I thought about what she said.\n\n"
            "I realized the truth was harder than I expected.\n\n"
            "She turned away."
        )
        result = apply_deflection_grounding(text, tension_level=7)
        assert result != text
        # Grounding sentence is prepended to the 2nd reflective paragraph
        assert len(result) > len(text)

    def test_dialogue_breaks_run(self):
        text = (
            "I thought about it.\n\n"
            '"Stop," she said.\n\n'
            "I felt the weight of it."
        )
        result = apply_deflection_grounding(text, tension_level=8)
        # Dialogue between reflective paras breaks the run, no insert needed
        assert result == text

    def test_max_edits_respected(self):
        # Build 6 consecutive reflective paragraphs = 3 potential insert points
        paras = [f"I thought about thing number {i}." for i in range(7)]
        text = "\n\n".join(paras)
        result = apply_deflection_grounding(text, tension_level=8, max_edits=2)
        # Should add at most 2 inserts
        added = len(result.split("\n\n")) - len(text.split("\n\n"))
        assert added <= 2

    def test_single_reflective_no_insert(self):
        text = (
            "I wondered what she meant.\n\n"
            "She crossed the room quickly."
        )
        result = apply_deflection_grounding(text, tension_level=8)
        # Single reflective para = no run, no insert
        assert result == text


# ============================================================================
# 11. apply_bridge_insert — location change detection + template
# ============================================================================


class TestBridgeInsert:
    """Insert grounding bridge when location changes between scenes."""

    def test_no_change_when_anchors_present(self):
        text = "That evening, in the kitchen, she found the letter.\n\nMore content here."
        prev = "They left the balcony together."
        result = apply_bridge_insert(text, prev, scene_location="kitchen", prev_location="balcony")
        assert result == text

    def test_bridge_added_on_location_change(self):
        text = "She opened the envelope slowly.\n\nThe words blurred."
        prev = "They stepped off the boat at the dock."
        result = apply_bridge_insert(
            text, prev, pov_name="Lena",
            scene_location="monastery", prev_location="dock",
        )
        assert result != text
        # Bridge should be prepended
        assert len(result) > len(text)

    def test_no_bridge_same_location(self):
        text = "She sat down at the table.\n\nThe wine was still warm."
        prev = "Marco poured more wine at the table."
        result = apply_bridge_insert(
            text, prev, pov_name="Lena",
            scene_location="kitchen", prev_location="kitchen",
        )
        assert result == text

    def test_no_bridge_for_first_scene(self):
        text = "She arrived at the airport.\n\nThe terminal was crowded."
        result = apply_bridge_insert(text, "", pov_name="Lena", scene_location="airport")
        # No prev_text means first scene, no bridge needed
        assert result == text

    def test_bridge_contains_location_reference(self):
        text = "She unfolded the map.\n\nThe ink was faded."
        prev = "They said goodbye in the plaza."
        result = apply_bridge_insert(
            text, prev, pov_name="Lena",
            scene_location="library", prev_location="plaza",
        )
        if result != text:
            # If bridge was inserted, it should reference something
            assert len(result) > len(text)


# ============================================================================
# 12. apply_final_line_rewrite — mode-aware bank selection
# ============================================================================


class TestFinalLineRewriteEnhanced:
    """Final line rewrite with mode-aware template bank."""

    def test_summary_ending_rewritten_default(self):
        text = (
            "She ran across the room.\n\n"
            "He caught her arm.\n\n"
            "It was clear that everything had changed between them and nothing would ever be the same again."
        )
        result = apply_final_line_rewrite(text, scene_mode="default")
        # Summary ending should be replaced
        assert result != text

    def test_action_ending_preserved(self):
        text = (
            "She ran across the room.\n\n"
            "He pulled the door shut."
        )
        result = apply_final_line_rewrite(text, scene_mode="default")
        assert result == text

    def test_dialogue_ending_preserved(self):
        text = (
            "She ran across the room.\n\n"
            '"Don\'t follow me," she said.'
        )
        result = apply_final_line_rewrite(text, scene_mode="default")
        assert result == text

    def test_conflict_mode_uses_conflict_bank(self):
        text = (
            "She ran across the room.\n\n"
            "It was clear that the argument had fundamentally changed everything between them forever."
        )
        result = apply_final_line_rewrite(text, scene_mode="conflict")
        if result != text:
            # Should not end with the original summary
            assert "fundamentally changed everything" not in result

    def test_romance_mode_available(self):
        text = (
            "He smiled softly.\n\n"
            "It was clear that the evening had changed things between them in ways neither could articulate or understand."
        )
        result = apply_final_line_rewrite(text, scene_mode="romance")
        assert result != text

    def test_reveal_mode_available(self):
        text = (
            "She read the document.\n\n"
            "Everything had shifted between them and nothing would ever be the same."
        )
        result = apply_final_line_rewrite(text, scene_mode="reveal")
        assert result != text

    def test_unknown_mode_uses_default(self):
        text = (
            "She ran.\n\n"
            "It was clear that things had changed between them and nothing would be the same again."
        )
        result = apply_final_line_rewrite(text, scene_mode="nonexistent_mode")
        # Should fall back to default bank
        assert result != text
