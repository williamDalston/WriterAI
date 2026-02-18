"""Tests for quality.voice_differentiation module."""

import unittest
from collections import Counter

from quality.voice_differentiation import (
    _classify_sentence_length_bucket,
    _extract_ngrams,
    _ngram_profile,
    _sentence_lengths,
    _check_signature_adherence,
    _check_forbidden_phrases,
    _check_signature_bleed,
    _check_ngram_overlap,
    _check_rhythm_profile_match,
    compute_voice_fingerprint,
    check_voice_differentiation,
    format_voice_report,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scene(content, pov="Lena", chapter=1, scene=1):
    return {
        "content": content,
        "pov": pov,
        "chapter": chapter,
        "scene": scene,
        "scene_id": f"ch{chapter:02d}_s{scene:02d}",
    }


def _make_character(name, role="protagonist"):
    return {"name": name, "role": role}


def _make_voice_profile(
    sentence_length="medium",
    signature_words=None,
    forbidden_phrases=None,
):
    return {
        "sentence_length": sentence_length,
        "signature_words": signature_words or [],
        "forbidden_phrases": forbidden_phrases or [],
        "rhythm_rule": "Test rule",
        "conflict_tell": "Test tell",
    }


# ===========================================================================
# N-gram extraction
# ===========================================================================

class TestExtractNgrams(unittest.TestCase):
    def test_bigrams(self):
        grams = _extract_ngrams("I need to find the answer", 2)
        assert "need to" in grams
        assert "find the" in grams

    def test_trigrams(self):
        grams = _extract_ngrams("I need to find the answer", 3)
        assert "need to find" in grams

    def test_short_text(self):
        grams = _extract_ngrams("hello", 2)
        assert grams == []

    def test_empty_text(self):
        grams = _extract_ngrams("", 2)
        assert grams == []


class TestNgramProfile(unittest.TestCase):
    def test_basic_profile(self):
        lines = [
            "I need to find the answer quickly",
            "I need to understand what happened",
            "She need to leave before dawn",
        ]
        profile = _ngram_profile(lines, ns=(2,), top_n=10)
        assert isinstance(profile, Counter)
        assert "need to" in profile
        assert profile["need to"] == 3

    def test_stopword_only_grams_filtered(self):
        lines = ["the and the and the and"]
        profile = _ngram_profile(lines, ns=(2,), top_n=10)
        # All-stopword n-grams should be filtered out
        assert len(profile) == 0


# ===========================================================================
# Sentence length classification
# ===========================================================================

class TestSentenceLengthBucket(unittest.TestCase):
    def test_short(self):
        assert _classify_sentence_length_bucket(5.0) == "short"
        assert _classify_sentence_length_bucket(7.9) == "short"

    def test_medium(self):
        assert _classify_sentence_length_bucket(8.0) == "medium"
        assert _classify_sentence_length_bucket(12.0) == "medium"
        assert _classify_sentence_length_bucket(15.0) == "medium"

    def test_long(self):
        assert _classify_sentence_length_bucket(15.1) == "long"
        assert _classify_sentence_length_bucket(25.0) == "long"


class TestSentenceLengths(unittest.TestCase):
    def test_basic(self):
        lines = ["I went home. She stayed behind."]
        lengths = _sentence_lengths(lines)
        assert lengths == [3, 3]

    def test_multiple_lines(self):
        lines = ["Short line.", "This is a longer sentence with more words."]
        lengths = _sentence_lengths(lines)
        assert len(lengths) == 2
        assert lengths[0] == 2  # "Short line"
        assert lengths[1] == 8  # "This is a longer sentence with more words"

    def test_empty(self):
        lengths = _sentence_lengths([])
        assert lengths == []


# ===========================================================================
# Fingerprint computation
# ===========================================================================

class TestComputeVoiceFingerprint(unittest.TestCase):
    def test_basic(self):
        lines = [
            "I grabbed the knife and cut the rope.",
            "The water rushed past my ankles.",
            "Listen carefully. We leave at dawn.",
        ]
        fp = compute_voice_fingerprint(lines)
        assert fp["total_lines"] == 3
        assert fp["total_words"] > 0
        assert isinstance(fp["word_profile"], Counter)
        assert isinstance(fp["ngram_profile"], Counter)
        assert "mean" in fp["sentence_lengths"]
        assert "bucket" in fp["sentence_lengths"]

    def test_with_voice_profile(self):
        lines = [
            "Listen, we need to move quickly.",
            "I grabbed the rope and pulled.",
        ]
        vp = _make_voice_profile(
            signature_words=["listen", "quickly", "nonsense", "precisely", "absolutely"],
            forbidden_phrases=["I couldn't help but"],
        )
        fp = compute_voice_fingerprint(lines, vp)
        assert fp["signature_word_hits"]["listen"] == 1
        assert fp["signature_word_hits"]["quickly"] == 1
        assert fp["signature_word_hits"]["nonsense"] == 0
        assert fp["forbidden_phrase_hits"] == []

    def test_forbidden_phrase_detected(self):
        lines = ["I couldn't help but notice the flowers."]
        vp = _make_voice_profile(
            forbidden_phrases=["I couldn't help but"],
        )
        fp = compute_voice_fingerprint(lines, vp)
        assert "I couldn't help but" in fp["forbidden_phrase_hits"]

    def test_empty_lines(self):
        fp = compute_voice_fingerprint([])
        assert fp["total_lines"] == 0
        assert fp["total_words"] == 0
        assert fp["sentence_lengths"]["mean"] == 0.0

    def test_single_line(self):
        fp = compute_voice_fingerprint(["Hello there."])
        assert fp["total_lines"] == 1


# ===========================================================================
# Signature adherence check
# ===========================================================================

class TestSignatureAdherence(unittest.TestCase):
    def test_all_present(self):
        fp = {
            "signature_word_hits": {
                "listen": 3, "quickly": 2, "nonsense": 1,
                "precisely": 1, "absolutely": 1,
            },
        }
        vp = _make_voice_profile(
            signature_words=["listen", "quickly", "nonsense", "precisely", "absolutely"]
        )
        violations = _check_signature_adherence(fp, vp, "Lena", min_hits=2)
        assert len(violations) == 0

    def test_none_present(self):
        fp = {
            "signature_word_hits": {
                "listen": 0, "quickly": 0, "nonsense": 0,
                "precisely": 0, "absolutely": 0,
            },
        }
        vp = _make_voice_profile(
            signature_words=["listen", "quickly", "nonsense", "precisely", "absolutely"]
        )
        violations = _check_signature_adherence(fp, vp, "Lena", min_hits=2)
        assert len(violations) == 1
        assert violations[0]["type"] == "SIGNATURE_WORD_ABSENT"

    def test_partial_below_threshold(self):
        fp = {
            "signature_word_hits": {
                "listen": 2, "quickly": 0, "nonsense": 0,
                "precisely": 0, "absolutely": 0,
            },
        }
        vp = _make_voice_profile(
            signature_words=["listen", "quickly", "nonsense", "precisely", "absolutely"]
        )
        violations = _check_signature_adherence(fp, vp, "Marco", min_hits=2)
        assert len(violations) == 1
        assert "1/5" in violations[0]["message"]

    def test_no_signature_words(self):
        fp = {"signature_word_hits": {}}
        vp = _make_voice_profile()
        violations = _check_signature_adherence(fp, vp, "Lena")
        assert len(violations) == 0


# ===========================================================================
# Forbidden phrase check
# ===========================================================================

class TestForbiddenPhrases(unittest.TestCase):
    def test_found(self):
        fp = {"forbidden_phrase_hits": ["I couldn't help but", "a sense of"]}
        vp = _make_voice_profile(
            forbidden_phrases=["I couldn't help but", "a sense of"]
        )
        violations = _check_forbidden_phrases(fp, vp, "Lena")
        assert len(violations) == 2
        assert all(v["type"] == "FORBIDDEN_PHRASE_USED" for v in violations)
        assert all(v["severity"] == "high" for v in violations)

    def test_clean(self):
        fp = {"forbidden_phrase_hits": []}
        vp = _make_voice_profile(forbidden_phrases=["I couldn't help but"])
        violations = _check_forbidden_phrases(fp, vp, "Lena")
        assert len(violations) == 0


# ===========================================================================
# Signature bleed check
# ===========================================================================

class TestSignatureBleed(unittest.TestCase):
    def test_bleed_detected(self):
        # Lena uses Marco's signature words frequently
        fingerprints = {
            "Lena": {
                "word_profile": Counter({"ocean": 3, "storm": 2, "knife": 4}),
            },
            "Marco": {
                "word_profile": Counter({"pasta": 5, "wine": 3}),
            },
        }
        voice_profiles = {
            "Lena": _make_voice_profile(signature_words=["ocean", "storm"]),
            "Marco": _make_voice_profile(signature_words=["ocean", "storm", "knife"]),
        }
        violations = _check_signature_bleed(fingerprints, voice_profiles)
        assert len(violations) == 1
        assert violations[0]["type"] == "SIGNATURE_BLEED"
        assert violations[0]["character"] == "Lena"

    def test_no_bleed(self):
        fingerprints = {
            "Lena": {
                "word_profile": Counter({"ocean": 3, "storm": 2}),
            },
            "Marco": {
                "word_profile": Counter({"pasta": 5, "wine": 3}),
            },
        }
        voice_profiles = {
            "Lena": _make_voice_profile(signature_words=["ocean", "storm"]),
            "Marco": _make_voice_profile(signature_words=["pasta", "wine"]),
        }
        violations = _check_signature_bleed(fingerprints, voice_profiles)
        assert len(violations) == 0

    def test_single_word_not_bleed(self):
        # Using just 1 of another character's signature words isn't bleed (need >= 2)
        fingerprints = {
            "Lena": {
                "word_profile": Counter({"ocean": 3}),
            },
            "Marco": {
                "word_profile": Counter({"pasta": 5}),
            },
        }
        voice_profiles = {
            "Lena": _make_voice_profile(signature_words=["ocean"]),
            "Marco": _make_voice_profile(signature_words=["ocean", "pasta"]),
        }
        violations = _check_signature_bleed(fingerprints, voice_profiles)
        assert len(violations) == 0


# ===========================================================================
# N-gram overlap check
# ===========================================================================

class TestNgramOverlap(unittest.TestCase):
    def test_high_overlap(self):
        shared = {f"word{i} word{i+1}": 3 for i in range(20)}
        fingerprints = {
            "Lena": {"ngram_profile": Counter(shared)},
            "Marco": {"ngram_profile": Counter(shared)},
        }
        violations, pairwise = _check_ngram_overlap(fingerprints, threshold=0.40)
        assert len(violations) == 1
        assert violations[0]["type"] == "NGRAM_HOMOGENIZATION"
        assert pairwise[0][2] == 1.0  # identical

    def test_low_overlap(self):
        fingerprints = {
            "Lena": {"ngram_profile": Counter({"run fast": 3, "dark night": 2})},
            "Marco": {"ngram_profile": Counter({"cook well": 4, "red wine": 3})},
        }
        violations, pairwise = _check_ngram_overlap(fingerprints, threshold=0.40)
        assert len(violations) == 0
        assert pairwise[0][2] == 0.0

    def test_threshold_boundary(self):
        # 2 shared out of 5 total = 0.40 Jaccard
        fingerprints = {
            "Lena": {"ngram_profile": Counter({"run fast": 3, "dark night": 2, "shared one": 1})},
            "Marco": {"ngram_profile": Counter({"cook well": 4, "red wine": 3, "shared one": 1})},
        }
        violations, pairwise = _check_ngram_overlap(fingerprints, threshold=0.40)
        # Jaccard = 1 / 5 = 0.20, below threshold
        assert len(violations) == 0


# ===========================================================================
# Rhythm profile match check
# ===========================================================================

class TestRhythmProfileMatch(unittest.TestCase):
    def test_short_matches_short(self):
        fp = {"sentence_lengths": {"mean": 5.0, "std": 1.5, "bucket": "short"}}
        vp = _make_voice_profile(sentence_length="short")
        violations = _check_rhythm_profile_match(fp, vp, "Lena")
        assert len(violations) == 0

    def test_short_but_long(self):
        fp = {"sentence_lengths": {"mean": 18.0, "std": 3.0, "bucket": "long"}}
        vp = _make_voice_profile(sentence_length="short")
        violations = _check_rhythm_profile_match(fp, vp, "Lena")
        assert len(violations) == 1
        assert violations[0]["type"] == "RHYTHM_PROFILE_MISMATCH"

    def test_no_profile(self):
        fp = {"sentence_lengths": {"mean": 10.0, "std": 2.0, "bucket": "medium"}}
        vp = _make_voice_profile(sentence_length="")
        violations = _check_rhythm_profile_match(fp, vp, "Lena")
        assert len(violations) == 0

    def test_zero_mean(self):
        fp = {"sentence_lengths": {"mean": 0.0, "std": 0.0, "bucket": "medium"}}
        vp = _make_voice_profile(sentence_length="short")
        violations = _check_rhythm_profile_match(fp, vp, "Lena")
        assert len(violations) == 0


# ===========================================================================
# Integration: check_voice_differentiation
# ===========================================================================

class TestCheckVoiceDifferentiation(unittest.TestCase):
    def _build_scenes_and_chars(self):
        """Build test scenes with distinct character dialogue."""
        scenes = [
            _make_scene(
                '"I need to find the answer," Lena said quietly. '
                '"This ocean reminds me of home," Lena whispered.',
                pov="Lena",
            ),
            _make_scene(
                '"The pasta is almost ready," Marco said with a grin. '
                '"Pass me the wine," Marco added.',
                pov="Marco",
                chapter=2, scene=1,
            ),
        ]
        characters = [
            _make_character("Lena Castillo"),
            _make_character("Marco Vitale", role="love_interest"),
        ]
        return scenes, characters

    def test_all_pass_no_profiles(self):
        scenes, characters = self._build_scenes_and_chars()
        result = check_voice_differentiation(
            scenes, characters,
            min_lines_for_eval=1,
        )
        assert result["pass"] is True
        assert len(result["violations"]) == 0

    def test_single_character(self):
        scenes = [
            _make_scene('"Hello," I said.', pov="Lena"),
        ]
        characters = [_make_character("Lena")]
        result = check_voice_differentiation(scenes, characters, min_lines_for_eval=1)
        assert result["pass"] is True

    def test_no_dialogue(self):
        scenes = [
            _make_scene("The sun set over the ocean. Waves crashed on the shore.", pov="Lena"),
        ]
        characters = [_make_character("Lena")]
        result = check_voice_differentiation(scenes, characters)
        assert result["pass"] is True
        assert "note" in result

    def test_empty_scenes(self):
        result = check_voice_differentiation([], [])
        assert result["pass"] is True

    def test_forbidden_phrase_violation(self):
        scenes = [
            _make_scene(
                '"I couldn\'t help but notice the flowers," Lena said. '
                '"The garden was beautiful," Lena added.',
                pov="Lena",
            ),
        ]
        characters = [_make_character("Lena")]
        voice_profiles = {
            "Lena": _make_voice_profile(
                forbidden_phrases=["I couldn't help but"],
            ),
        }
        result = check_voice_differentiation(
            scenes, characters,
            voice_profiles=voice_profiles,
            min_lines_for_eval=1,
        )
        # FORBIDDEN_PHRASE_USED is high severity, so pass should be False
        assert result["pass"] is False
        assert any(v["type"] == "FORBIDDEN_PHRASE_USED" for v in result["violations"])

    def test_signature_word_absent_violation(self):
        scenes = [
            _make_scene(
                '"The weather is nice," Lena said. '
                '"I agree completely," Lena added. '
                '"We should go outside," Lena suggested.',
                pov="Lena",
            ),
        ]
        characters = [_make_character("Lena")]
        voice_profiles = {
            "Lena": _make_voice_profile(
                signature_words=["precisely", "nonsense", "absolutely", "indeed", "clearly"],
            ),
        }
        result = check_voice_differentiation(
            scenes, characters,
            voice_profiles=voice_profiles,
            min_lines_for_eval=1,
        )
        assert any(v["type"] == "SIGNATURE_WORD_ABSENT" for v in result["violations"])

    def test_suggestions_generated(self):
        scenes = [
            _make_scene(
                '"I couldn\'t help but wonder," Lena said. '
                '"This is strange," Lena added.',
                pov="Lena",
            ),
        ]
        characters = [_make_character("Lena")]
        voice_profiles = {
            "Lena": _make_voice_profile(
                forbidden_phrases=["I couldn't help but"],
                signature_words=["ocean", "storm", "fire", "blade", "silence"],
            ),
        }
        result = check_voice_differentiation(
            scenes, characters,
            voice_profiles=voice_profiles,
            min_lines_for_eval=1,
        )
        assert len(result["suggestions"]) > 0

    def test_min_lines_threshold(self):
        """Characters with fewer lines than min_lines_for_eval are skipped."""
        scenes = [
            _make_scene('"Hello," Lena said.', pov="Lena"),
        ]
        characters = [_make_character("Lena")]
        voice_profiles = {
            "Lena": _make_voice_profile(
                signature_words=["missing1", "missing2", "missing3", "missing4", "missing5"],
            ),
        }
        result = check_voice_differentiation(
            scenes, characters,
            voice_profiles=voice_profiles,
            min_lines_for_eval=10,  # Lena has only 1 line
        )
        assert result["pass"] is True
        assert "note" in result


# ===========================================================================
# Report formatting
# ===========================================================================

class TestFormatReport(unittest.TestCase):
    def test_with_violations(self):
        report = {
            "pass": False,
            "violations": [
                {
                    "type": "FORBIDDEN_PHRASE_USED",
                    "severity": "high",
                    "character": "Lena",
                    "message": 'Lena uses forbidden phrase: "I couldn\'t help but"',
                },
            ],
            "character_fingerprints": {
                "Lena": {
                    "total_lines": 5,
                    "total_words": 50,
                    "sentence_lengths": {"mean": 10.0, "std": 2.0, "bucket": "medium"},
                    "top_words": ["ocean", "storm"],
                },
            },
            "pairwise_ngram_overlap": [],
            "suggestions": ["Reinforce forbidden phrases in prompt"],
        }
        text = format_voice_report(report)
        assert "FORBIDDEN_PHRASE_USED" in text
        assert "Lena" in text
        assert "NO" in text  # Pass: NO

    def test_clean_report(self):
        report = {
            "pass": True,
            "violations": [],
            "character_fingerprints": {},
            "pairwise_ngram_overlap": [],
            "suggestions": [],
        }
        text = format_voice_report(report)
        assert "YES" in text
        assert "No violations" in text


if __name__ == "__main__":
    unittest.main()
