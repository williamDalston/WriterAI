"""Quick sanity check for Editor Studio correction fixes."""
from editor_studio.orchestrator import (
    _parse_tension_collapse,
    _parse_final_line_ending,
    _validate_output,
)


def test_parse_tension_collapse():
    w = ["TENSION_COLLAPSE: scene drops from 7 to 3—consider smoother transition"]
    prev, curr = _parse_tension_collapse(w)
    assert prev == 7 and curr == 3
    prev2, curr2 = _parse_tension_collapse([])
    assert prev2 == 7 and curr2 == 3  # default


def test_parse_final_line_ending():
    assert _parse_final_line_ending({"FINAL_LINE_ATMOSPHERE": ["x"]}) == "ATMOSPHERE"
    assert _parse_final_line_ending({"FINAL_LINE_SUMMARY": ["y"]}) == "SUMMARY"
    assert _parse_final_line_ending({}) == "ATMOSPHERE"  # default


def test_validate_output():
    # Valid: similar length, enough content
    orig = "word " * 50  # 50 words
    new_ok = "word " * 55  # 55 words, under 1.5x
    assert _validate_output(orig, new_ok) is True
    # Invalid: too short
    assert _validate_output("x" * 100, "a") is False
    # Invalid: length balloons
    long = "word " * 500
    assert _validate_output("short text here", long) is False
    # Valid: empty orig, new has enough content
    assert _validate_output("", "x " * 30) is True  # 60 chars, passes min
