"""Tests for quality.pov_consistency module."""

import unittest

from quality.pov_consistency import (
    _count_subject_pronouns,
    _mask_dialogue,
    audit_pov_consistency,
    batch_audit_pov,
    format_pov_report,
)


def _scene(content, pov="Lena", chapter=1, scene=1):
    return {
        "content": content,
        "pov": pov,
        "chapter": chapter,
        "scene": scene,
        "scene_id": f"ch{chapter:02d}_s{scene:02d}",
    }


class TestMaskDialogue(unittest.TestCase):
    def test_masks_double_quotes(self):
        text = 'He said "I want to leave" and turned.'
        masked = _mask_dialogue(text)
        assert "I want to leave" not in masked
        assert "DIALOGUE" in masked

    def test_masks_smart_quotes(self):
        text = '\u201cShe ran fast,\u201d he said.'
        masked = _mask_dialogue(text)
        assert "She ran" not in masked

    def test_no_quotes(self):
        text = "I walked through the rain."
        masked = _mask_dialogue(text)
        assert masked == text


class TestCountSubjectPronouns(unittest.TestCase):
    def test_first_person(self):
        text = "I walked to the door. I turned the handle."
        counts = _count_subject_pronouns(text)
        assert counts["I"] == 2
        assert counts["He"] == 0
        assert counts["She"] == 0

    def test_third_person_male(self):
        text = "He walked to the door. He turned the handle."
        counts = _count_subject_pronouns(text)
        assert counts["He"] == 2
        assert counts["I"] == 0

    def test_third_person_female(self):
        text = "She walked to the door. She grabbed the key."
        counts = _count_subject_pronouns(text)
        assert counts["She"] == 2

    def test_mixed_pronouns(self):
        text = "I stared at the wall. He swallowed hard. She leaned in."
        counts = _count_subject_pronouns(text)
        assert counts["I"] >= 1
        assert counts["He"] >= 1
        assert counts["She"] >= 1

    def test_dialogue_excluded(self):
        text = '"He was wrong," I said. I turned away.'
        counts = _count_subject_pronouns(text)
        # "He" inside quotes should be masked
        assert counts["I"] >= 1


class TestAuditPovConsistency(unittest.TestCase):
    def test_clean_first_person(self):
        content = (
            "I walked down the corridor. I could hear footsteps behind me.\n\n"
            "I turned the corner and paused. The door was locked."
        )
        result = audit_pov_consistency(content, "Lena", "first")
        assert result["pass"] is True
        assert len(result["violations"]) == 0

    def test_mixed_pronouns_in_paragraph(self):
        content = (
            "I stared at the screen. He swallowed hard. "
            "She leaned against the wall. I felt the tension rise."
        )
        result = audit_pov_consistency(content, "Maya", "first")
        assert result["pass"] is False
        assert any(v["type"] == "POV_PARAGRAPH_DRIFT" for v in result["violations"])

    def test_dialogue_pronouns_not_flagged(self):
        content = (
            '"He was always like that," I said. I shook my head.\n\n'
            '"She told me everything," I whispered. I turned to the window.'
        )
        result = audit_pov_consistency(content, "Maya", "first")
        # He/She in dialogue should not count as narration drift
        assert result["pass"] is True

    def test_third_person_slip(self):
        content = (
            "She turned to face the door. She reached for the handle.\n\n"
            "He stepped back. He looked worried. He couldn't breathe."
        )
        result = audit_pov_consistency(content, "Maya", "first")
        # Entire paragraphs in third person = drift
        assert result["pass"] is False

    def test_short_content_passes(self):
        result = audit_pov_consistency("Short.", "Lena", "first")
        assert result["pass"] is True

    def test_empty_content(self):
        result = audit_pov_consistency("", "Lena", "first")
        assert result["pass"] is True

    def test_third_limited_mode_clean(self):
        content = (
            "She walked down the corridor. She could hear footsteps.\n\n"
            "She turned the corner and paused. The door was locked."
        )
        result = audit_pov_consistency(content, "Maya", "third_limited")
        assert result["pass"] is True

    def test_third_limited_with_first_person_drift(self):
        content = (
            "She walked down the corridor. I could hear footsteps. "
            "I turned the corner."
        )
        result = audit_pov_consistency(content, "Maya", "third_limited")
        assert result["pass"] is False

    def test_paragraph_count(self):
        content = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        result = audit_pov_consistency(content, "Lena", "first")
        assert result["paragraph_count"] == 3


class TestBatchAuditPov(unittest.TestCase):
    def test_all_clean(self):
        scenes = [
            _scene("I walked to the door. I turned the handle."),
            _scene("I sat down at the table. I picked up the phone."),
        ]
        result = batch_audit_pov(scenes)
        assert result["pass"] is True
        assert result["scenes_with_drift"] == 0

    def test_one_scene_with_drift(self):
        scenes = [
            _scene("I walked to the door. I turned the handle."),
            _scene("I stared at him. He swallowed hard. I felt uneasy."),
        ]
        result = batch_audit_pov(scenes)
        assert result["pass"] is False
        assert result["scenes_with_drift"] == 1
        assert result["violations"][0]["scene_id"] == "ch01_s01"

    def test_empty_scenes(self):
        result = batch_audit_pov([])
        assert result["pass"] is True


class TestFormatReport(unittest.TestCase):
    def test_basic_format(self):
        report = {
            "pass": False,
            "total_violations": 2,
            "scenes_with_drift": 1,
            "total_scenes": 5,
            "violations": [
                {
                    "severity": "high",
                    "scene_id": "ch01_s02",
                    "paragraph_index": 1,
                    "message": "mixed pronouns",
                },
            ],
        }
        text = format_pov_report(report)
        assert "NO" in text
        assert "ch01_s02" in text


if __name__ == "__main__":
    unittest.main()
