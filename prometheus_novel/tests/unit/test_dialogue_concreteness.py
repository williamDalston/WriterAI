"""Tests for quality.dialogue_concreteness module."""

import unittest

from quality.dialogue_concreteness import (
    _extract_dialogue_lines,
    _is_abstract_line,
    _is_aphorism,
    check_dialogue_concreteness,
    batch_check_dialogue,
    format_dialogue_report,
)


def _scene(content, scene_id="ch01_s01"):
    return {"content": content, "scene_id": scene_id}


class TestExtractDialogueLines(unittest.TestCase):
    def test_double_quotes(self):
        text = '"I need to leave now," she said. "This is dangerous."'
        lines = _extract_dialogue_lines(text)
        assert len(lines) == 2

    def test_smart_quotes(self):
        text = '\u201cI need to leave now,\u201d she said.'
        lines = _extract_dialogue_lines(text)
        assert len(lines) == 1

    def test_short_lines_filtered(self):
        text = '"Hi," she said.'  # Under 8 chars
        lines = _extract_dialogue_lines(text)
        assert len(lines) == 0

    def test_no_dialogue(self):
        text = "The rain fell. She walked away."
        lines = _extract_dialogue_lines(text)
        assert len(lines) == 0


class TestIsAbstractLine(unittest.TestCase):
    def test_abstract(self):
        assert _is_abstract_line("Truth and power are the only things that matter in this life")

    def test_concrete(self):
        assert not _is_abstract_line("Grab the gun from the table and run")

    def test_mixed_below_threshold(self):
        # One abstract noun + concrete anchor = not abstract
        assert not _is_abstract_line("The truth was in the phone she grabbed")

    def test_single_abstract_not_enough(self):
        # Need 2+ abstract nouns
        assert not _is_abstract_line("Truth is what we need right now")


class TestIsAphorism(unittest.TestCase):
    def test_truth_is_weapon(self):
        assert _is_aphorism("Truth is a weapon we all wield")

    def test_cant_control(self):
        assert _is_aphorism("You can't control fate no matter what you do")

    def test_the_only_thing(self):
        assert _is_aphorism("The only thing that matters is survival")

    def test_concrete_not_aphorism(self):
        assert not _is_aphorism("Grab the bag and let's go")

    def test_in_the_end(self):
        assert _is_aphorism("In the end, all that matters is what we choose")

    def test_people_believe(self):
        assert _is_aphorism("People believe what they want to believe")


class TestCheckDialogueConcreteness(unittest.TestCase):
    def test_clean_dialogue(self):
        content = (
            '"Grab the phone from the table," she said. '
            '"I\'ll meet you at the car," he replied.'
        )
        result = check_dialogue_concreteness(content, "ch01_s01")
        assert result["pass"] is True
        assert result["aphorism_count"] == 0

    def test_aphorism_detected(self):
        content = '"Truth is a weapon," she said quietly.'
        result = check_dialogue_concreteness(content, "ch01_s01")
        assert result["aphorism_count"] == 1
        assert any(v["type"] == "THESIS_STATEMENT_DIALOGUE" for v in result["violations"])

    def test_aphorism_cluster(self):
        content = (
            '"Truth is a weapon," she said. '
            '"Power is a curse," he replied. '
            '"Freedom is an illusion," she whispered. '
            '"Love is a trap," he added.'
        )
        result = check_dialogue_concreteness(content, "ch01_s01")
        assert any(v["type"] == "APHORISM_CLUSTER" for v in result["violations"])

    def test_no_dialogue_passes(self):
        content = "The sun was setting. Rain fell on the street."
        result = check_dialogue_concreteness(content, "ch01_s01")
        assert result["pass"] is True
        assert result["total_dialogue_lines"] == 0

    def test_abstract_ratio(self):
        content = (
            '"Truth and power control everything in this world," she said. '
            '"Justice and freedom are just words for the powerless," he replied. '
            '"Fear and hope drive all human choices in life," she added. '
            '"Knowledge without wisdom is dangerous to humanity," he said.'
        )
        result = check_dialogue_concreteness(content, "ch01_s01")
        assert result["abstract_ratio"] > 0.0


class TestBatchCheckDialogue(unittest.TestCase):
    def test_all_clean(self):
        scenes = [
            _scene('"Grab the phone," she said.', "ch01_s01"),
            _scene('"Meet me at the car," he replied.', "ch02_s01"),
        ]
        result = batch_check_dialogue(scenes)
        assert result["total_aphorisms"] == 0

    def test_detects_across_scenes(self):
        scenes = [
            _scene('"Truth is a weapon," she said.', "ch01_s01"),
            _scene('"Power is a curse," he replied.', "ch02_s01"),
        ]
        result = batch_check_dialogue(scenes)
        assert result["total_aphorisms"] == 2

    def test_empty(self):
        result = batch_check_dialogue([])
        assert result["pass"] is True


class TestFormatReport(unittest.TestCase):
    def test_basic(self):
        report = {
            "pass": False,
            "total_violations": 2,
            "scenes_with_issues": 1,
            "total_scenes": 5,
            "total_aphorisms": 2,
            "avg_abstract_ratio": 0.35,
            "violations": [
                {
                    "type": "THESIS_STATEMENT_DIALOGUE",
                    "severity": "medium",
                    "scene_id": "ch01_s01",
                    "message": "Aphorism detected",
                },
            ],
        }
        text = format_dialogue_report(report)
        assert "aphorisms: 2" in text.lower() or "aphorisms" in text.lower()


if __name__ == "__main__":
    unittest.main()
