"""Character voice differentiation — checks that voice profiles are followed.

Complements the existing voice meters in quality_meters.py:
  - voice_distinctiveness_meter: Jaccard word overlap (symptom detection)
  - voice_sub_metrics: catchphrase dominance + rhythm variance

This module checks whether voice profiles are *actually followed* and provides
actionable diagnostics for repair.

Five checks:
  1. SIGNATURE_WORD_ABSENT — signature_words don't appear in dialogue
  2. FORBIDDEN_PHRASE_USED — character uses a forbidden phrase
  3. SIGNATURE_BLEED — Character A uses Character B's signature words
  4. NGRAM_HOMOGENIZATION — characters share too many multi-word constructions
  5. RHYTHM_PROFILE_MISMATCH — actual sentence length doesn't match declared profile
"""

import logging
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stopwords (shared with quality_meters for consistency)
# ---------------------------------------------------------------------------
_STOPWORDS = frozenset({
    "the", "a", "an", "i", "you", "we", "he", "she", "they", "it",
    "is", "are", "was", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "will", "would", "could", "should",
    "may", "might", "can", "shall", "to", "of", "in", "for", "on",
    "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "out", "off",
    "up", "down", "and", "but", "or", "nor", "not", "so", "yet",
    "both", "either", "neither", "each", "every", "all", "any",
    "few", "more", "most", "other", "some", "such", "no", "only",
    "same", "than", "too", "very", "just", "because", "if", "when",
    "than", "that", "this", "what", "which", "who", "whom",
    "my", "your", "his", "her", "its", "our", "their",
    "me", "him", "us", "them", "myself", "yourself",
    "don", "didn", "doesn", "won", "wouldn", "couldn", "shouldn",
    "ll", "ve", "re", "m", "s", "t", "d",
})

# Sentence length bucket boundaries (words per sentence)
_SHORT_CEILING = 8
_LONG_FLOOR = 15


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_ngrams(text: str, n: int) -> List[str]:
    """Extract word n-grams from lowercased text."""
    words = re.findall(r"\b[a-z]+\b", text.lower())
    if len(words) < n:
        return []
    return [" ".join(words[i:i + n]) for i in range(len(words) - n + 1)]


def _ngram_profile(lines: List[str], ns: Tuple[int, ...] = (2, 3), top_n: int = 30) -> Counter:
    """Build an n-gram frequency profile across all dialogue lines.

    Filters out n-grams composed entirely of stopwords.
    """
    counts: Counter = Counter()
    for line in lines:
        for n in ns:
            for gram in _extract_ngrams(line, n):
                words = gram.split()
                if not all(w in _STOPWORDS for w in words):
                    counts[gram] += 1
    return Counter(dict(counts.most_common(top_n)))


def _classify_sentence_length_bucket(avg_words: float) -> str:
    """Classify average sentence length into short/medium/long."""
    if avg_words < _SHORT_CEILING:
        return "short"
    elif avg_words > _LONG_FLOOR:
        return "long"
    return "medium"


def _sentence_lengths(lines: List[str]) -> List[int]:
    """Extract sentence lengths (word counts) from dialogue lines."""
    lengths = []
    for line in lines:
        for sent in re.split(r"[.!?]+", line):
            sent = sent.strip()
            if sent:
                lengths.append(len(sent.split()))
    return lengths


def _word_profile(lines: List[str], top_n: int = 30) -> Counter:
    """Build a word frequency profile from dialogue lines (content words only)."""
    words: Counter = Counter()
    for line in lines:
        for word in re.findall(r"\b[a-z]+\b", line.lower()):
            if word not in _STOPWORDS and len(word) > 2:
                words[word] += 1
    return Counter(dict(words.most_common(top_n)))


# ---------------------------------------------------------------------------
# Per-character fingerprint
# ---------------------------------------------------------------------------

def compute_voice_fingerprint(
    lines: List[str],
    voice_profile: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Compute a voice fingerprint from a character's dialogue lines.

    Args:
        lines: Dialogue lines attributed to this character.
        voice_profile: Optional voice profile dict with signature_words,
                       forbidden_phrases, sentence_length fields.

    Returns:
        Fingerprint dict with word_profile, ngram_profile, sentence_lengths,
        signature_word_hits, forbidden_phrase_hits, total_lines, total_words.
    """
    if not lines:
        return {
            "word_profile": Counter(),
            "ngram_profile": Counter(),
            "sentence_lengths": {"mean": 0.0, "std": 0.0, "bucket": "medium"},
            "signature_word_hits": {},
            "forbidden_phrase_hits": [],
            "total_lines": 0,
            "total_words": 0,
        }

    wp = _word_profile(lines)
    ngp = _ngram_profile(lines)

    sl = _sentence_lengths(lines)
    if sl:
        mean_sl = sum(sl) / len(sl)
        std_sl = (sum((x - mean_sl) ** 2 for x in sl) / len(sl)) ** 0.5
    else:
        mean_sl, std_sl = 0.0, 0.0

    total_words = sum(len(line.split()) for line in lines)

    # Signature word hits
    sig_hits: Dict[str, int] = {}
    if voice_profile and voice_profile.get("signature_words"):
        all_text = " ".join(lines).lower()
        for word in voice_profile["signature_words"]:
            w = word.lower().strip()
            if w:
                sig_hits[w] = len(re.findall(rf"\b{re.escape(w)}\b", all_text))

    # Forbidden phrase hits
    forbidden_hits: List[str] = []
    if voice_profile and voice_profile.get("forbidden_phrases"):
        all_text = " ".join(lines).lower()
        for phrase in voice_profile["forbidden_phrases"]:
            p = phrase.lower().strip()
            if p and p in all_text:
                forbidden_hits.append(phrase)

    return {
        "word_profile": wp,
        "ngram_profile": ngp,
        "sentence_lengths": {
            "mean": round(mean_sl, 1),
            "std": round(std_sl, 1),
            "bucket": _classify_sentence_length_bucket(mean_sl),
        },
        "signature_word_hits": sig_hits,
        "forbidden_phrase_hits": forbidden_hits,
        "total_lines": len(lines),
        "total_words": total_words,
    }


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _check_signature_adherence(
    fingerprint: Dict,
    voice_profile: Dict,
    character: str,
    min_hits: int = 2,
) -> List[Dict[str, Any]]:
    """Check that signature words actually appear in dialogue."""
    violations = []
    sig_hits = fingerprint.get("signature_word_hits", {})
    if not sig_hits:
        return violations

    present = sum(1 for count in sig_hits.values() if count > 0)
    total = len(sig_hits)

    if present < min_hits and total > 0:
        absent = [w for w, c in sig_hits.items() if c == 0]
        violations.append({
            "type": "SIGNATURE_WORD_ABSENT",
            "severity": "medium",
            "character": character,
            "message": (
                f"{character}: only {present}/{total} signature words appear in dialogue. "
                f"Missing: {', '.join(absent[:5])}"
            ),
            "detail": {"present": present, "total": total, "absent": absent},
        })
    return violations


def _check_forbidden_phrases(
    fingerprint: Dict,
    voice_profile: Dict,
    character: str,
) -> List[Dict[str, Any]]:
    """Check that forbidden phrases are not used."""
    violations = []
    hits = fingerprint.get("forbidden_phrase_hits", [])
    for phrase in hits:
        violations.append({
            "type": "FORBIDDEN_PHRASE_USED",
            "severity": "high",
            "character": character,
            "message": f"{character} uses forbidden phrase: \"{phrase}\"",
            "detail": {"phrase": phrase},
        })
    return violations


def _check_signature_bleed(
    fingerprints: Dict[str, Dict],
    voice_profiles: Dict[str, Dict],
) -> List[Dict[str, Any]]:
    """Check if Character A uses Character B's signature words."""
    violations = []
    char_names = sorted(fingerprints.keys())

    for name_a in char_names:
        fp_a = fingerprints[name_a]
        wp_a = fp_a.get("word_profile", Counter())
        if not wp_a:
            continue

        for name_b in char_names:
            if name_a == name_b:
                continue
            vp_b = voice_profiles.get(name_b, {})
            sig_words_b = vp_b.get("signature_words", [])
            if not sig_words_b:
                continue

            # Check if A uses B's signature words frequently
            bleed_words = []
            for word in sig_words_b:
                w = word.lower().strip()
                if w and w in wp_a and wp_a[w] >= 2:
                    bleed_words.append(w)

            if len(bleed_words) >= 2:
                violations.append({
                    "type": "SIGNATURE_BLEED",
                    "severity": "medium",
                    "character": name_a,
                    "message": (
                        f"{name_a} uses {name_b}'s signature words: "
                        f"{', '.join(bleed_words)}"
                    ),
                    "detail": {
                        "speaker": name_a,
                        "owner": name_b,
                        "bleed_words": bleed_words,
                    },
                })
    return violations


def _check_ngram_overlap(
    fingerprints: Dict[str, Dict],
    threshold: float = 0.40,
) -> Tuple[List[Dict[str, Any]], List[Tuple[str, str, float]]]:
    """Check n-gram overlap between character pairs.

    Returns (violations, pairwise_overlap).
    """
    violations = []
    pairwise = []
    char_names = sorted(fingerprints.keys())

    for i, name_a in enumerate(char_names):
        for j, name_b in enumerate(char_names):
            if i >= j:
                continue
            ngrams_a = set(fingerprints[name_a].get("ngram_profile", {}).keys())
            ngrams_b = set(fingerprints[name_b].get("ngram_profile", {}).keys())
            if not ngrams_a or not ngrams_b:
                continue

            jaccard = len(ngrams_a & ngrams_b) / len(ngrams_a | ngrams_b)
            pairwise.append((name_a, name_b, round(jaccard, 3)))

            if jaccard >= threshold:
                shared = sorted(ngrams_a & ngrams_b)[:5]
                violations.append({
                    "type": "NGRAM_HOMOGENIZATION",
                    "severity": "high",
                    "character": f"{name_a} / {name_b}",
                    "message": (
                        f"{name_a} and {name_b} share {jaccard:.0%} of n-gram constructions. "
                        f"Shared: {', '.join(shared)}"
                    ),
                    "detail": {
                        "pair": (name_a, name_b),
                        "overlap": round(jaccard, 3),
                        "shared_ngrams": shared,
                    },
                })

    return violations, pairwise


def _check_rhythm_profile_match(
    fingerprint: Dict,
    voice_profile: Dict,
    character: str,
) -> List[Dict[str, Any]]:
    """Check that actual sentence length matches declared profile."""
    violations = []
    declared = voice_profile.get("sentence_length", "")
    if not declared:
        return violations

    actual = fingerprint.get("sentence_lengths", {})
    actual_bucket = actual.get("bucket", "medium")
    actual_mean = actual.get("mean", 0.0)

    if actual_mean == 0.0:
        return violations

    declared = declared.lower().strip()
    if declared not in ("short", "medium", "long"):
        return violations

    if declared != actual_bucket:
        violations.append({
            "type": "RHYTHM_PROFILE_MISMATCH",
            "severity": "medium",
            "character": character,
            "message": (
                f"{character}: declared sentence_length=\"{declared}\" but "
                f"actual avg is {actual_mean:.1f} words/sentence (\"{actual_bucket}\")"
            ),
            "detail": {
                "declared": declared,
                "actual_bucket": actual_bucket,
                "actual_mean": actual_mean,
            },
        })
    return violations


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def check_voice_differentiation(
    scenes: List[Dict],
    characters: List[Dict],
    voice_profiles: Optional[Dict] = None,
    *,
    min_signature_hits: int = 2,
    ngram_overlap_threshold: float = 0.40,
    min_lines_for_eval: int = 5,
) -> Dict[str, Any]:
    """Run all voice differentiation checks.

    Args:
        scenes: List of scene dicts with "content" and "pov" fields.
        characters: List of character dicts with "name" field.
        voice_profiles: Optional dict mapping character name to voice profile.
        min_signature_hits: Minimum number of signature words that must appear.
        ngram_overlap_threshold: Jaccard threshold for n-gram overlap between pairs.
        min_lines_for_eval: Minimum dialogue lines per character to evaluate.

    Returns:
        {
            "pass": bool,
            "violations": [{"type", "severity", "character", "message", "detail"}],
            "character_fingerprints": {name: serializable fingerprint},
            "pairwise_ngram_overlap": [(char_a, char_b, overlap)],
            "suggestions": [str],
        }
    """
    voice_profiles = voice_profiles or {}

    # Extract dialogue per character — reuse logic from quality_meters
    from stages.quality_meters import _extract_dialogue_by_character
    dialogue_by_char = _extract_dialogue_by_character(scenes, characters)

    if len(dialogue_by_char) < 1:
        return {
            "pass": True,
            "violations": [],
            "character_fingerprints": {},
            "pairwise_ngram_overlap": [],
            "suggestions": [],
            "note": "No character dialogue found",
        }

    # Build fingerprints
    fingerprints: Dict[str, Dict] = {}
    for char_name, lines in dialogue_by_char.items():
        if len(lines) < min_lines_for_eval:
            continue
        vp = voice_profiles.get(char_name, {})
        fingerprints[char_name] = compute_voice_fingerprint(lines, vp)

    if not fingerprints:
        return {
            "pass": True,
            "violations": [],
            "character_fingerprints": {},
            "pairwise_ngram_overlap": [],
            "suggestions": [],
            "note": f"No characters with >= {min_lines_for_eval} dialogue lines",
        }

    # Run all checks
    violations: List[Dict] = []
    suggestions: List[str] = []

    for char_name, fp in fingerprints.items():
        vp = voice_profiles.get(char_name, {})
        if not vp:
            continue

        # Check 1: Signature word adherence
        violations.extend(_check_signature_adherence(
            fp, vp, char_name, min_hits=min_signature_hits,
        ))

        # Check 2: Forbidden phrase enforcement
        violations.extend(_check_forbidden_phrases(fp, vp, char_name))

        # Check 5: Rhythm profile match
        violations.extend(_check_rhythm_profile_match(fp, vp, char_name))

    # Check 3: Signature bleed (cross-character)
    if len(fingerprints) >= 2 and voice_profiles:
        violations.extend(_check_signature_bleed(fingerprints, voice_profiles))

    # Check 4: N-gram overlap
    pairwise_ngram: List[Tuple[str, str, float]] = []
    if len(fingerprints) >= 2:
        ngram_violations, pairwise_ngram = _check_ngram_overlap(
            fingerprints, threshold=ngram_overlap_threshold,
        )
        violations.extend(ngram_violations)

    # Generate suggestions from violations
    violation_types = {v["type"] for v in violations}
    if "SIGNATURE_WORD_ABSENT" in violation_types:
        suggestions.append(
            "Inject signature words into drafting prompt more aggressively "
            "(e.g., 'This character MUST use: [words]')"
        )
    if "FORBIDDEN_PHRASE_USED" in violation_types:
        suggestions.append(
            "Add forbidden phrases to FORMAT_CONTRACT stop-sequence list "
            "or reinforce in system prompt"
        )
    if "NGRAM_HOMOGENIZATION" in violation_types:
        suggestions.append(
            "Add per-character sentence structure constraints "
            "(e.g., 'Character A favors questions, Character B favors commands')"
        )
    if "SIGNATURE_BLEED" in violation_types:
        suggestions.append(
            "Ensure voice profiles explicitly forbid other characters' signature words"
        )
    if "RHYTHM_PROFILE_MISMATCH" in violation_types:
        suggestions.append(
            "Reinforce sentence_length constraint in drafting prompt "
            "(e.g., 'Keep sentences under 8 words for this character')"
        )

    # Determine pass/fail (high-severity violations fail)
    high_violations = [v for v in violations if v["severity"] in ("high", "critical")]
    passed = len(high_violations) == 0

    # Serialize fingerprints for JSON output
    serializable_fps = {}
    for name, fp in fingerprints.items():
        serializable_fps[name] = {
            "top_words": list(fp["word_profile"].keys())[:10],
            "top_ngrams": list(fp["ngram_profile"].keys())[:10],
            "sentence_lengths": fp["sentence_lengths"],
            "signature_word_hits": fp["signature_word_hits"],
            "forbidden_phrase_hits": fp["forbidden_phrase_hits"],
            "total_lines": fp["total_lines"],
            "total_words": fp["total_words"],
        }

    return {
        "pass": passed,
        "violations": violations,
        "character_fingerprints": serializable_fps,
        "pairwise_ngram_overlap": pairwise_ngram,
        "suggestions": suggestions,
    }


# ---------------------------------------------------------------------------
# Human-readable report
# ---------------------------------------------------------------------------

def format_voice_report(report: Dict[str, Any]) -> str:
    """Format the voice differentiation report for logging."""
    lines = []
    lines.append("=== VOICE DIFFERENTIATION REPORT ===")
    lines.append(f"Pass: {'YES' if report.get('pass') else 'NO'}")

    violations = report.get("violations", [])
    if violations:
        lines.append(f"\nViolations ({len(violations)}):")
        for v in violations:
            lines.append(f"  [{v['severity'].upper()}] {v['type']}: {v['message']}")
    else:
        lines.append("\nNo violations found.")

    fps = report.get("character_fingerprints", {})
    if fps:
        lines.append(f"\nCharacter fingerprints ({len(fps)}):")
        for name, fp in fps.items():
            lines.append(f"  {name}: {fp['total_lines']} lines, {fp['total_words']} words")
            sl = fp.get("sentence_lengths", {})
            lines.append(f"    Sentence length: {sl.get('mean', 0):.1f} avg ({sl.get('bucket', '?')})")
            top = fp.get("top_words", [])[:5]
            if top:
                lines.append(f"    Top words: {', '.join(top)}")

    pairwise = report.get("pairwise_ngram_overlap", [])
    if pairwise:
        lines.append(f"\nPairwise n-gram overlap:")
        for a, b, j in pairwise:
            lines.append(f"  {a} <-> {b}: {j:.1%}")

    suggestions = report.get("suggestions", [])
    if suggestions:
        lines.append(f"\nSuggestions:")
        for s in suggestions:
            lines.append(f"  - {s}")

    return "\n".join(lines)
