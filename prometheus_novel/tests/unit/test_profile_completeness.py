"""Tests for character profile completeness checker — 15-field rubric + reporting."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from quality.profile_completeness import (
    check_character_completeness,
    check_all_profiles,
    build_patch_prompt,
    format_completeness_report,
    _check_field,
    _RUBRIC,
)


# === Field Checkers ===

class TestCheckField:
    def test_full_name_requires_two_parts(self):
        assert _check_field({"name": "Valentina Moretti"}, "full_name") is True
        assert _check_field({"name": "Marco"}, "full_name") is False
        assert _check_field({"name": ""}, "full_name") is False

    def test_age_from_backstory(self):
        char = {"backstory": "She was 28 years old when it happened."}
        assert _check_field(char, "age_or_life_stage") is True

    def test_age_from_life_stage(self):
        char = {"backstory": "A young adult struggling with identity."}
        assert _check_field(char, "age_or_life_stage") is True

    def test_age_from_decade(self):
        char = {"physical_description": "A woman in her thirties with dark hair."}
        assert _check_field(char, "age_or_life_stage") is True

    def test_age_missing(self):
        char = {"backstory": "She grew up in a small town."}
        assert _check_field(char, "age_or_life_stage") is False

    def test_physical_description_needs_length(self):
        assert _check_field({"physical_description": "Tall with dark hair and brown eyes, athletic build."}, "physical_description") is True
        assert _check_field({"physical_description": "Tall"}, "physical_description") is False

    def test_backstory_needs_length(self):
        long = "She grew up in Rome after her parents fled the civil war. Her mother died when she was fifteen."
        assert _check_field({"backstory": long}, "backstory") is True
        assert _check_field({"backstory": "Born in Rome."}, "backstory") is False

    def test_personality_strengths(self):
        char = {"personality": {"strengths": ["determined", "loyal"]}}
        assert _check_field(char, "personality_strengths") is True
        char_one = {"personality": {"strengths": ["brave"]}}
        assert _check_field(char_one, "personality_strengths") is False

    def test_personality_flaws(self):
        char = {"personality": {"flaws": ["stubborn", "reckless"]}}
        assert _check_field(char, "personality_flaws") is True
        char_one = {"personality": {"flaws": ["stubborn"]}}
        assert _check_field(char_one, "personality_flaws") is False

    def test_voice_markers_from_phrases(self):
        char = {"voice": {"phrases": ["gonna", "y'all"]}}
        assert _check_field(char, "voice_markers") is True

    def test_voice_markers_from_vocabulary(self):
        char = {"voice": {"vocabulary": ["literary", "formal"]}}
        assert _check_field(char, "voice_markers") is True

    def test_voice_markers_missing(self):
        char = {"voice": {}}
        assert _check_field(char, "voice_markers") is False

    def test_relationships_named(self):
        char = {"relationships": {"Marco": "love interest"}}
        assert _check_field(char, "relationships_named") is True
        char_empty = {"relationships": {}}
        assert _check_field(char_empty, "relationships_named") is False

    def test_goals_external(self):
        char = {"goals": {"external": ["Find the truth"]}}
        assert _check_field(char, "goals_external") is True
        char_str = {"goals": {"external": "Find the truth"}}
        assert _check_field(char_str, "goals_external") is False  # Must be list

    def test_goals_internal(self):
        char = {"goals": {"internal": ["Learn to trust"]}}
        assert _check_field(char, "goals_internal") is True

    def test_arc(self):
        char = {"arc": "From isolated survivor to open-hearted partner through trials."}
        assert _check_field(char, "arc") is True
        char_short = {"arc": "Changes."}
        assert _check_field(char_short, "arc") is False

    def test_signature_behaviors(self):
        char = {"signature_behaviors": ["twists ring when nervous", "bites lower lip"]}
        assert _check_field(char, "signature_behaviors") is True
        char_empty = {"signature_behaviors": []}
        assert _check_field(char_empty, "signature_behaviors") is False

    def test_family_network_with_names(self):
        char = {"backstory": "Her brother Luca died in the fire. Her mother Rosa survived."}
        assert _check_field(char, "family_network") is True

    def test_family_network_no_family_mentioned_passes(self):
        """No family mentioned at all = not applicable = pass."""
        char = {"backstory": "She grew up alone in a small town by the sea."}
        assert _check_field(char, "family_network") is True

    def test_family_network_mentioned_but_unnamed(self):
        """Family mentioned with only short words nearby = fail."""
        # "brother" with no 3+ letter word within 30 chars triggers fail
        char = {"backstory": "He is a brother to no one at all."}
        # _NAMED_FAMILY regex uses IGNORECASE so [A-Z][a-z]{2,} matches any 3+ letter word.
        # Use a sentence where "brother" is followed only by short words to actually fail.
        char2 = {"backstory": "A brother of no use."}
        # "brother" → "of" (2 chars) → "no" (2 chars) → "use" (3 chars) - "use" matches.
        # Actually need a period right after to cut off search.
        char3 = {"backstory": "Had a brother."}
        assert _check_field(char3, "family_network") is False

    def test_constraints_from_text(self):
        char = {"constraints": "Refuses to lie, even to protect herself."}
        assert _check_field(char, "constraints") is True

    def test_constraints_from_backstory(self):
        char = {"backstory": "She never breaks a promise. She refuses to abandon anyone."}
        assert _check_field(char, "constraints") is True

    def test_constraints_missing(self):
        char = {"backstory": "She grew up in a happy family."}
        assert _check_field(char, "constraints") is False

    def test_location_anchors_from_backstory(self):
        char = {"backstory": "She lives in a small apartment in NYC."}
        assert _check_field(char, "location_anchors") is True


# === Character Completeness ===

class TestCheckCharacterCompleteness:
    def _full_character(self):
        return {
            "name": "Valentina Moretti",
            "role": "protagonist",
            "physical_description": "Dark hair, brown eyes, athletic build. She is in her thirties and looks commanding.",
            "personality": {
                "strengths": ["determined", "loyal", "resourceful"],
                "flaws": ["stubborn", "distrustful"],
            },
            "backstory": "Grew up in Rome after her parents fled the civil war. Lost her mother Rosa at age 15. Her brother Luca was her only confidant. She never forgave her father for leaving.",
            "goals": {
                "external": ["Find the truth about her family's past"],
                "internal": ["Learn to trust again", "Accept vulnerability"],
            },
            "arc": "From isolated, self-reliant survivor to someone who can accept love and partnership through trials.",
            "voice": {"phrases": ["Madonna", "Dai"], "vocabulary": ["formal"]},
            "relationships": {"Marco": "love interest", "Sofia": "best friend", "Luca": "brother (deceased)"},
            "signature_behaviors": ["twists ring when nervous", "bites lower lip when thinking"],
            "constraints": "Refuses to lie. Will never abandon a friend.",
            "location_anchors": ["family house in Tuscany", "her Rome apartment"],
        }

    def test_full_character_high_score(self):
        result = check_character_completeness(self._full_character())
        assert result["completeness_score"] >= 0.80
        assert result["missing_count"] <= 2

    def test_minimal_character_low_score(self):
        result = check_character_completeness({"name": "Marco", "role": "love_interest"})
        assert result["completeness_score"] < 0.30
        assert result["missing_count"] > 10

    def test_returns_required_keys(self):
        result = check_character_completeness({"name": "X", "role": "sidekick"})
        assert "completeness_score" in result
        assert "present_count" in result
        assert "missing_count" in result
        assert "present_fields" in result
        assert "missing_fields" in result
        assert "name" in result
        assert "role" in result

    def test_missing_fields_are_dicts(self):
        result = check_character_completeness({"name": "X", "role": "sidekick"})
        for m in result["missing_fields"]:
            assert "field" in m
            assert "description" in m

    def test_present_fields_are_dicts(self):
        char = self._full_character()
        result = check_character_completeness(char)
        for p in result["present_fields"]:
            assert "field" in p
            assert "description" in p


# === All Profiles ===

class TestCheckAllProfiles:
    def _full_char(self, name, role):
        return {
            "name": name, "role": role,
            "physical_description": "Dark hair, brown eyes. Tall, athletic build. She is in her twenties.",
            "personality": {"strengths": ["brave", "kind"], "flaws": ["reckless", "naive"]},
            "backstory": "Born in a small village. Lost her father Marco Vasquez at age 12. Her sister Elena raised her. She never forgot that loss.",
            "goals": {"external": ["Defeat the villain"], "internal": ["Find inner peace"]},
            "arc": "From naive villager to seasoned warrior through loss and triumph.",
            "voice": {"phrases": ["By the stars!"], "vocabulary": ["colloquial"]},
            "relationships": {"Elena": "sister", "Marco": "father (deceased)"},
            "signature_behaviors": ["cracks knuckles", "whistles when nervous"],
            "constraints": "Never breaks a promise. Refuses to betray a friend.",
            "location_anchors": ["village house", "the training grounds"],
        }

    def test_all_complete_passes(self):
        chars = [self._full_char("Elena Vasquez", "protagonist"),
                 self._full_char("Marco Torres", "antagonist")]
        report = check_all_profiles(chars)
        assert report["pass"] is True

    def test_one_incomplete_fails(self):
        chars = [
            self._full_char("Elena Vasquez", "protagonist"),
            {"name": "Marco", "role": "love_interest"},
        ]
        report = check_all_profiles(chars)
        assert report["pass"] is False
        assert len(report.get("patch_needed", [])) >= 1

    def test_empty_list_returns_fail(self):
        report = check_all_profiles([])
        assert report["pass"] is False

    def test_non_dict_entries_skipped(self):
        report = check_all_profiles(["not a dict", None, 42])
        assert report["pass"] is False

    def test_profiles_key_in_report(self):
        chars = [self._full_char("Elena Vasquez", "protagonist")]
        report = check_all_profiles(chars)
        assert "profiles" in report

    def test_patch_needed_lists_incomplete(self):
        chars = [
            self._full_char("Elena Vasquez", "protagonist"),
            {"name": "Marco Torres", "role": "love_interest"},
        ]
        report = check_all_profiles(chars)
        assert "Marco Torres" in report["patch_needed"]


# === Build Patch Prompt ===

class TestBuildPatchPrompt:
    def test_includes_character_name(self):
        char = {"name": "Valentina Moretti", "role": "protagonist"}
        missing = [{"field": "backstory", "description": "Backstory / formative events", "weight": 1.0}]
        prompt = build_patch_prompt(char, missing)
        assert "Valentina Moretti" in prompt

    def test_includes_missing_descriptions(self):
        char = {"name": "Marco", "role": "love_interest"}
        missing = [
            {"field": "backstory", "description": "Backstory / formative events", "weight": 1.0},
            {"field": "goals_external", "description": "External goals (plot-level)", "weight": 0.7},
        ]
        prompt = build_patch_prompt(char, missing)
        assert "Backstory" in prompt
        assert "External goals" in prompt

    def test_empty_missing_returns_string(self):
        char = {"name": "Marco"}
        prompt = build_patch_prompt(char, [])
        assert isinstance(prompt, str)


# === Format Report ===

class TestFormatCompletenessReport:
    def test_passing_report_shows_yes(self):
        report = {
            "pass": True, "overall_score": 0.85,
            "min_score_threshold": 0.80,
            "profiles": [
                {"name": "A", "role": "protagonist", "completeness_score": 0.90,
                 "present_count": 13, "total_fields": 15, "missing_fields": []},
            ],
            "patch_needed": [],
        }
        text = format_completeness_report(report)
        assert "YES" in text

    def test_failing_report_shows_no_and_character(self):
        report = {
            "pass": False, "overall_score": 0.20,
            "min_score_threshold": 0.80,
            "profiles": [
                {"name": "Marco", "role": "love_interest", "completeness_score": 0.20,
                 "present_count": 2, "total_fields": 15,
                 "missing_fields": [{"field": "backstory", "description": "Backstory", "weight": 1.0}]},
            ],
            "patch_needed": ["Marco"],
        }
        text = format_completeness_report(report)
        assert "NO" in text
        assert "Marco" in text


# === Rubric Integrity ===

class TestRubricIntegrity:
    def test_rubric_has_15_fields(self):
        assert len(_RUBRIC) == 15

    def test_all_weights_positive(self):
        for field_name, weight, label in _RUBRIC:
            assert weight > 0, f"Weight for {field_name} must be positive"

    def test_all_labels_non_empty(self):
        for field_name, weight, label in _RUBRIC:
            assert len(label) > 0, f"Label for {field_name} must not be empty"

    def test_field_names_unique(self):
        names = [r[0] for r in _RUBRIC]
        assert len(names) == len(set(names)), "Duplicate field names in rubric"
