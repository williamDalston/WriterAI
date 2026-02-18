"""Test truncation, opening_vary, cross_scene_transition."""
from quality.quiet_killers import check_truncation


def test_truncation():
    emdash = "\u2014"
    long_trailing = "A " * 25 + "saw him" + emdash  # 50+ chars, ends with em-dash
    assert len(check_truncation(long_trailing)) > 0
    long_ellipsis = "A " * 25 + "turned away..."
    assert len(check_truncation(long_ellipsis)) > 0
    assert len(check_truncation("The room was silent. I left.")) == 0
