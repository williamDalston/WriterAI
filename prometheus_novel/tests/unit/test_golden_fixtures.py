"""
Golden fixture regression tests.

Fast, deterministic tests that protect against exact failure modes
observed in pipeline runs. No LLM needed -- pure input/output verification.

Run with: pytest tests/unit/test_golden_fixtures.py -v
"""
import sys
import re
import pytest
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from stages.pipeline import _clean_scene_content, _postprocess_scene
from export.scene_validator import validate_scene, META_TEXT_PATTERNS


# ---------------------------------------------------------------------------
# Fixtures: small, fixed prose snippets exercising known failure modes
# ---------------------------------------------------------------------------

PROSE_WITH_SINGLE_ITALIC = (
    "She whispered *mine* and turned away. The door swung shut behind her."
)

PROSE_WITH_ITALIC_SENTENCE = (
    "Marcus stared at the wreckage. *This can't be happening.* He pressed "
    "his back against the cold wall and tried to breathe."
)

PROSE_WITH_MULTI_ITALICS = (
    "The corridor stretched endlessly. *Keep moving.* She gripped the railing. "
    "*Don't look down.* Her knuckles whitened against the metal."
)

CERTAINLY_PREAMBLE = (
    "Certainly! Here is the revised scene:\n\n"
    "The rain hammered the windshield as Elena gripped the steering wheel. "
    "Beside her, Marcus said nothing. The silence was louder than the storm."
)

SURE_PREAMBLE = (
    "Sure, here's the enhanced version:\n\n"
    "Smoke curled from the barrel of the revolver. Jonas lowered his arm."
)

IVE_REVISED_PREAMBLE = (
    "I've revised the scene to add more tension:\n\n"
    "Glass crunched underfoot. The hallway stretched into darkness."
)

BELOW_IS_PREAMBLE = (
    "Below is the revised scene:\n\n"
    "The market was alive with color and noise."
)

REST_UNCHANGED_TAIL = (
    "Elena pushed through the crowd. The air smelled of cinnamon and rain.\n\n"
    "The rest of the scene remains unchanged."
)

ANALYSIS_TAIL = (
    "Marcus reached for the door handle. The metal was ice-cold beneath his "
    "fingers. He twisted it slowly, half-expecting resistance, but the latch "
    "gave with a soft click. The hallway beyond was dark, lit only by the "
    "amber glow of a distant streetlamp filtering through a cracked window. "
    "Dust motes drifted in the thin beam of light. He stepped inside and "
    "pulled the door shut behind him. The silence was absolute.\n\n"
    "---\n\n"
    "**Changes made:** Improved sensory details and pacing."
)

# Long enough text to survive cleanup thresholds (>150 chars for validator, >50 words for salvage)
LONG_PROSE_BLOCK = (
    "Elena pushed through the crowd, her heart pounding against her ribs. "
    "The market stalls blurred past -- a kaleidoscope of silk scarves, copper "
    "lanterns, and stacked spice jars. Somewhere behind her, boots struck "
    "cobblestone in a rhythm that matched her own frantic pulse. She ducked "
    "beneath a merchant's awning, pressing herself against the rough brick "
    "wall. The footsteps slowed. Stopped. She held her breath and counted "
    "the seconds, each one stretching like taffy in a child's hands. When she "
    "finally dared to look, the alley was empty. But the feeling of being "
    "watched clung to her skin like wet cloth."
)


# ---------------------------------------------------------------------------
# Test 1: POV routing -- _build_scene_context includes POV character data
# ---------------------------------------------------------------------------
# NOTE: _build_scene_context is an instance method on PipelineOrchestrator
# that requires self.state, so we test the POV flow at the _postprocess_scene
# level: verify that the POV character name passes through postprocessing
# without corruption, and that scene metadata's "pov" field is respected.

class TestPOVRouting:
    """Verify POV character information flows correctly through processing."""

    def test_pov_character_name_survives_postprocess(self):
        """Protagonist name should not be stripped by postprocessing."""
        prose = (
            "I stepped into the archive. The dust was thick enough to taste. "
            "My fingers traced the spine of the nearest ledger."
        )
        result = _postprocess_scene(prose, protagonist_name="Elena")
        assert "archive" in result
        assert "dust" in result
        # First-person prose should survive postprocess without corruption
        assert "I stepped" in result or "stepped" in result

    def test_scene_pov_field_structure(self):
        """Scene dict with 'pov' key should be usable for POV routing."""
        scene = {
            "chapter": 2,
            "scene_number": 1,
            "scene_id": "ch02_s01",
            "pov": "Elena",
            "content": "I watched the sun set over the harbor.",
        }
        # Verify pov field is accessible (this is the field _generate_prose reads)
        assert scene.get("pov") == "Elena"
        assert scene.get("scene_id") == "ch02_s01"

    def test_dual_pov_scenes_have_distinct_pov(self):
        """In dual-POV novels, each scene's pov field should differ by character."""
        scenes = [
            {"chapter": 1, "scene_number": 1, "pov": "Elena", "content": "I opened the door."},
            {"chapter": 1, "scene_number": 2, "pov": "Marcus", "content": "I heard the door open."},
        ]
        pov_set = {s["pov"] for s in scenes}
        assert len(pov_set) == 2
        assert "Elena" in pov_set
        assert "Marcus" in pov_set


# ---------------------------------------------------------------------------
# Test 2: Italics preservation through postprocessing
# ---------------------------------------------------------------------------

class TestItalicsPreservation:
    """Verify cleanup and postprocess preserve *italic* markers for inner thoughts."""

    def test_single_word_italic_preserved_clean(self):
        """Single-word italic marker survives _clean_scene_content."""
        result = _clean_scene_content(PROSE_WITH_SINGLE_ITALIC)
        assert "*mine*" in result

    def test_single_word_italic_preserved_postprocess(self):
        """Single-word italic marker survives _postprocess_scene."""
        result = _postprocess_scene(PROSE_WITH_SINGLE_ITALIC, protagonist_name="Elena")
        assert "*mine*" in result

    def test_italic_sentence_preserved_clean(self):
        """Italic sentence (inner thought) survives _clean_scene_content."""
        result = _clean_scene_content(PROSE_WITH_ITALIC_SENTENCE)
        assert "*This can't be happening.*" in result

    def test_italic_sentence_preserved_postprocess(self):
        """Italic sentence survives full _postprocess_scene chain."""
        result = _postprocess_scene(PROSE_WITH_ITALIC_SENTENCE, protagonist_name="Marcus")
        assert "*This can't be happening.*" in result

    def test_multiple_italics_all_preserved(self):
        """Multiple italic markers in one paragraph all survive."""
        result = _postprocess_scene(PROSE_WITH_MULTI_ITALICS, protagonist_name="Lena")
        assert "*Keep moving.*" in result
        assert "*Don't look down.*" in result

    def test_italic_not_confused_with_separator(self):
        """Phase 2 tail patterns use \\n***\\n -- single-line *word* must not match."""
        # The tail pattern is: r'\n\*\*\*+\s*\n' which requires newline-star-star-star-newline
        # Single-word italic *word* should NOT trigger this
        text = "She said *never* again. The finality was absolute."
        result = _clean_scene_content(text)
        assert "*never*" in result


# ---------------------------------------------------------------------------
# Test 3: Meta-text / artifact prevention
# ---------------------------------------------------------------------------

class TestMetaTextStripping:
    """Verify _clean_scene_content strips LLM artifacts while keeping prose."""

    def test_certainly_preamble_stripped(self):
        """'Certainly! Here is the revised scene:' gets stripped."""
        result = _clean_scene_content(CERTAINLY_PREAMBLE)
        assert "Certainly" not in result
        assert "revised scene" not in result
        assert "rain hammered" in result

    def test_sure_preamble_stripped(self):
        """'Sure, here's the enhanced version:' gets stripped."""
        result = _clean_scene_content(SURE_PREAMBLE)
        assert "Sure" not in result
        assert "enhanced version" not in result
        assert "Smoke curled" in result

    def test_ive_revised_preamble_stripped(self):
        """'I've revised the scene...' gets stripped."""
        result = _clean_scene_content(IVE_REVISED_PREAMBLE)
        assert "I've revised" not in result
        assert "Glass crunched" in result

    def test_below_is_preamble_stripped(self):
        """'Below is the revised scene:' gets stripped."""
        result = _clean_scene_content(BELOW_IS_PREAMBLE)
        assert "Below is" not in result
        assert "market was alive" in result

    def test_rest_unchanged_tail_stripped(self):
        """'The rest of the scene remains unchanged' gets stripped."""
        result = _clean_scene_content(REST_UNCHANGED_TAIL)
        assert "remains unchanged" not in result
        assert "cinnamon" in result

    def test_analysis_tail_stripped(self):
        """Trailing analysis block (--- separator + **Changes made:**) stripped."""
        result = _clean_scene_content(ANALYSIS_TAIL)
        assert "Changes made" not in result
        assert "ice-cold" in result

    def test_end_prose_sentinel_stripped(self):
        """<END_PROSE> sentinel stripped by _postprocess_scene."""
        text = "The door slammed shut. <END_PROSE>"
        result = _postprocess_scene(text)
        assert "<END_PROSE>" not in result
        assert "door slammed" in result

    def test_end_prose_nonce_sentinel_stripped(self):
        """<END_PROSE_a3f1b2c9> nonce variant stripped by _postprocess_scene."""
        text = "The door slammed shut. <END_PROSE_a3f1b2c9>"
        result = _postprocess_scene(text)
        assert "END_PROSE" not in result
        assert "door slammed" in result

    def test_clean_prose_passes_through_unchanged(self):
        """Clean prose with no artifacts should pass through unmodified."""
        clean = "The rain hammered the windshield. Elena gripped the steering wheel."
        result = _clean_scene_content(clean)
        assert result.strip() == clean.strip()

    def test_inline_xml_tags_stripped(self):
        """XML tags like <scene> or <chapter> get stripped."""
        text = "<scene>The vault door swung open.</scene>"
        result = _clean_scene_content(text)
        assert "<scene>" not in result
        assert "</scene>" not in result
        assert "vault door" in result


# ---------------------------------------------------------------------------
# Test 4: Scene validator catches META_TEXT
# ---------------------------------------------------------------------------

class TestSceneValidator:
    """Verify scene_validator catches artifact patterns in exported scenes."""

    # Minimal config for validation
    MINIMAL_CONFIG = {"characters": {"protagonist": "Elena", "others": "Marcus"}}

    def test_certainly_preamble_flagged(self):
        """'Certainly! Here is...' caught by validator."""
        content = "Certainly! Here is the opening. " + LONG_PROSE_BLOCK
        issues = validate_scene(content, self.MINIMAL_CONFIG, scene_id="ch01_s01")
        codes = [i["code"] for i in issues]
        assert "META_TEXT" in codes
        # Check it identifies the right pattern
        pnames = [i["pattern_name"] for i in issues]
        assert "certainly_preamble" in pnames

    def test_of_course_preamble_flagged(self):
        """'Of course! Here's...' caught by validator."""
        content = "Of course! Here's the revised text. " + LONG_PROSE_BLOCK
        issues = validate_scene(content, self.MINIMAL_CONFIG, scene_id="ch01_s01")
        codes = [i["code"] for i in issues]
        assert "META_TEXT" in codes

    def test_rest_unchanged_flagged(self):
        """'The rest remains unchanged' caught by validator."""
        content = LONG_PROSE_BLOCK + " The rest remains unchanged."
        issues = validate_scene(content, self.MINIMAL_CONFIG, scene_id="ch02_s01")
        codes = [i["code"] for i in issues]
        assert "META_TEXT" in codes
        pnames = [i["pattern_name"] for i in issues]
        assert "rest_unchanged" in pnames

    def test_i_can_help_flagged(self):
        """'I can help with...' caught by validator."""
        content = LONG_PROSE_BLOCK + " I can help with any revisions you need."
        issues = validate_scene(content, self.MINIMAL_CONFIG, scene_id="ch03_s01")
        codes = [i["code"] for i in issues]
        assert "META_TEXT" in codes

    def test_let_me_know_flagged(self):
        """'Let me know if you want...' caught by validator."""
        content = LONG_PROSE_BLOCK + " Let me know if you want me to adjust."
        issues = validate_scene(content, self.MINIMAL_CONFIG, scene_id="ch03_s02")
        codes = [i["code"] for i in issues]
        assert "META_TEXT" in codes

    def test_clean_prose_no_issues(self):
        """Clean prose should not trigger any META_TEXT issues."""
        issues = validate_scene(LONG_PROSE_BLOCK, self.MINIMAL_CONFIG, scene_id="ch01_s01")
        meta_issues = [i for i in issues if i["code"] == "META_TEXT"]
        assert len(meta_issues) == 0

    def test_short_scene_skipped(self):
        """Scenes under 150 chars are skipped entirely (no false positives)."""
        issues = validate_scene("Short.", self.MINIMAL_CONFIG, scene_id="ch01_s01")
        assert len(issues) == 0

    def test_all_meta_patterns_are_regex_valid(self):
        """Every pattern in META_TEXT_PATTERNS should compile without error."""
        for pattern, code, name in META_TEXT_PATTERNS:
            compiled = re.compile(pattern, re.IGNORECASE)
            assert compiled is not None, f"Pattern {name!r} failed to compile"

    def test_issue_structure_has_required_fields(self):
        """Each issue dict should contain all required keys."""
        content = "Certainly! Here is the scene. " + LONG_PROSE_BLOCK
        issues = validate_scene(content, self.MINIMAL_CONFIG, scene_id="ch01_s01")
        assert len(issues) > 0
        required_keys = {"severity", "code", "scene_id", "scene_index", "offset",
                         "excerpt", "pattern_name", "message"}
        for issue in issues:
            assert required_keys.issubset(issue.keys()), (
                f"Issue missing keys: {required_keys - issue.keys()}"
            )

    def test_here_is_the_revised_flagged(self):
        """'Here is the revised...' caught by validator."""
        content = LONG_PROSE_BLOCK + " Here is the revised ending."
        issues = validate_scene(content, self.MINIMAL_CONFIG, scene_id="ch04_s01")
        codes = [i["code"] for i in issues]
        assert "META_TEXT" in codes
        pnames = [i["pattern_name"] for i in issues]
        assert "here_is_revised" in pnames

    def test_sure_preamble_flagged(self):
        """'Sure! Here's...' caught by validator."""
        content = "Sure! Here's the polished draft. " + LONG_PROSE_BLOCK
        issues = validate_scene(content, self.MINIMAL_CONFIG, scene_id="ch01_s02")
        codes = [i["code"] for i in issues]
        assert "META_TEXT" in codes
        pnames = [i["pattern_name"] for i in issues]
        assert "sure_preamble" in pnames


# ---------------------------------------------------------------------------
# Test 5: DOCX scene sorting
# ---------------------------------------------------------------------------

class TestDocxSceneSorting:
    """Verify the sort key produces correct chapter/scene ordering."""

    @staticmethod
    def _scene_sort_key(sc: dict):
        """Replica of the sort key from docx_exporter.py."""
        return (
            int(sc.get("scene_number") or sc.get("scene") or 10**9),
            str(sc.get("scene_id") or ""),
        )

    def test_scenes_sort_by_scene_number(self):
        """Scenes within a chapter sort by scene_number."""
        scenes = [
            {"scene_number": 3, "scene_id": "ch01_s03", "content": "Third"},
            {"scene_number": 1, "scene_id": "ch01_s01", "content": "First"},
            {"scene_number": 2, "scene_id": "ch01_s02", "content": "Second"},
        ]
        sorted_scenes = sorted(scenes, key=self._scene_sort_key)
        assert [s["scene_number"] for s in sorted_scenes] == [1, 2, 3]

    def test_scene_field_fallback(self):
        """Scenes using 'scene' key (legacy) instead of 'scene_number' still sort."""
        scenes = [
            {"scene": 2, "scene_id": "ch03_s02"},
            {"scene": 1, "scene_id": "ch03_s01"},
        ]
        sorted_scenes = sorted(scenes, key=self._scene_sort_key)
        assert sorted_scenes[0]["scene_id"] == "ch03_s01"
        assert sorted_scenes[1]["scene_id"] == "ch03_s02"

    def test_missing_scene_number_sorts_last(self):
        """Scenes without scene_number go to the end (10**9 fallback)."""
        scenes = [
            {"scene_id": "orphan"},
            {"scene_number": 1, "scene_id": "ch01_s01"},
        ]
        sorted_scenes = sorted(scenes, key=self._scene_sort_key)
        assert sorted_scenes[0]["scene_id"] == "ch01_s01"
        assert sorted_scenes[1]["scene_id"] == "orphan"

    def test_tiebreaker_by_scene_id_string(self):
        """When scene_number is identical, tiebreak by scene_id alphabetically."""
        scenes = [
            {"scene_number": 1, "scene_id": "ch01_s01b"},
            {"scene_number": 1, "scene_id": "ch01_s01a"},
        ]
        sorted_scenes = sorted(scenes, key=self._scene_sort_key)
        assert sorted_scenes[0]["scene_id"] == "ch01_s01a"
        assert sorted_scenes[1]["scene_id"] == "ch01_s01b"

    def test_chapter_then_scene_sorting(self):
        """Full chapter grouping + scene sorting (replicates exporter logic)."""
        all_scenes = [
            {"chapter": 2, "scene_number": 2, "scene_id": "ch02_s02"},
            {"chapter": 1, "scene_number": 2, "scene_id": "ch01_s02"},
            {"chapter": 2, "scene_number": 1, "scene_id": "ch02_s01"},
            {"chapter": 1, "scene_number": 1, "scene_id": "ch01_s01"},
        ]
        # Group by chapter, then sort scenes within each chapter
        chapters = {}
        for sc in all_scenes:
            ch = sc.get("chapter", 1)
            chapters.setdefault(ch, []).append(sc)
        ordered_ids = []
        for ch_num in sorted(chapters.keys()):
            for sc in sorted(chapters[ch_num], key=self._scene_sort_key):
                ordered_ids.append(sc["scene_id"])
        assert ordered_ids == ["ch01_s01", "ch01_s02", "ch02_s01", "ch02_s02"]

    def test_string_scene_number_coerced_to_int(self):
        """String scene numbers (from JSON parse) should still sort correctly."""
        scenes = [
            {"scene_number": "3", "scene_id": "ch01_s03"},
            {"scene_number": "1", "scene_id": "ch01_s01"},
            {"scene_number": "2", "scene_id": "ch01_s02"},
        ]
        sorted_scenes = sorted(scenes, key=self._scene_sort_key)
        assert [s["scene_id"] for s in sorted_scenes] == [
            "ch01_s01", "ch01_s02", "ch01_s03"
        ]


# ---------------------------------------------------------------------------
# Test 6: Quality meter scene_id integrity -- edge cases
# ---------------------------------------------------------------------------

class TestSceneIdIntegrity:
    """Verify scene_id_integrity_check handles edge cases."""

    def _import_checker(self):
        from stages.quality_meters import scene_id_integrity_check
        return scene_id_integrity_check

    def test_string_chapter_numbers(self):
        """Chapters stored as strings (e.g. from JSON) should coerce to int."""
        check = self._import_checker()
        scenes = [
            {"chapter": "2", "scene_number": "1", "scene_id": "ch02_s01"},
            {"chapter": "2", "scene_number": "2", "scene_id": "ch02_s02"},
        ]
        result = check(scenes)
        assert result["pass"] is True
        assert result["mismatches"] == []
        assert result["duplicates"] == []
        assert result["missing"] == []

    def test_missing_scene_id_detected(self):
        """Scenes without scene_id are reported as missing."""
        check = self._import_checker()
        scenes = [
            {"chapter": 1, "scene_number": 1},  # no scene_id
        ]
        result = check(scenes)
        assert result["pass"] is False
        assert len(result["missing"]) == 1
        assert result["missing"][0] == (1, 1)

    def test_duplicate_scene_id_detected(self):
        """Duplicate scene_ids are reported."""
        check = self._import_checker()
        scenes = [
            {"chapter": 1, "scene_number": 1, "scene_id": "ch01_s01"},
            {"chapter": 1, "scene_number": 2, "scene_id": "ch01_s01"},  # duplicate!
        ]
        result = check(scenes)
        assert result["pass"] is False
        assert "ch01_s01" in result["duplicates"]

    def test_mismatch_detected(self):
        """Wrong scene_id vs expected is reported as mismatch."""
        check = self._import_checker()
        scenes = [
            {"chapter": 3, "scene_number": 1, "scene_id": "ch02_s01"},  # wrong chapter
        ]
        result = check(scenes)
        assert result["pass"] is False
        assert len(result["mismatches"]) == 1
        expected, actual, ch, sc = result["mismatches"][0]
        assert expected == "ch03_s01"
        assert actual == "ch02_s01"

    def test_perfect_sequence_passes(self):
        """A correct sequence of scene_ids passes."""
        check = self._import_checker()
        scenes = [
            {"chapter": 1, "scene_number": 1, "scene_id": "ch01_s01"},
            {"chapter": 1, "scene_number": 2, "scene_id": "ch01_s02"},
            {"chapter": 2, "scene_number": 1, "scene_id": "ch02_s01"},
        ]
        result = check(scenes)
        assert result["pass"] is True

    def test_non_dict_scenes_skipped(self):
        """Non-dict entries in scenes list are silently skipped."""
        check = self._import_checker()
        scenes = [
            None,
            "garbage",
            {"chapter": 1, "scene_number": 1, "scene_id": "ch01_s01"},
        ]
        result = check(scenes)
        assert result["pass"] is True

    def test_mixed_string_int_chapter_coercion(self):
        """Mix of string and int chapter/scene numbers all coerce correctly."""
        check = self._import_checker()
        scenes = [
            {"chapter": 1, "scene_number": "1", "scene_id": "ch01_s01"},
            {"chapter": "1", "scene_number": 2, "scene_id": "ch01_s02"},
            {"chapter": "2", "scene_number": "1", "scene_id": "ch02_s01"},
        ]
        result = check(scenes)
        assert result["pass"] is True
        assert result["mismatches"] == []

    def test_unparseable_chapter_falls_back(self):
        """Non-numeric chapter/scene falls back to ch00_s{i+1}."""
        check = self._import_checker()
        scenes = [
            {"chapter": "prologue", "scene_number": "intro", "scene_id": "ch00_s01"},
        ]
        result = check(scenes)
        # Fallback: ch_int=0, sc_int=i+1=1 -> expected "ch00_s01"
        assert result["pass"] is True
