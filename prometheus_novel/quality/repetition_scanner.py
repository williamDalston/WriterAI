"""Lightweight per-scene repetition scanner for polish prompt injection.

Runs before voice_human_pass / prose_polish to produce targeted flags.
Flags: SENTENCE_OPENING_REPETITION, RHYTHM_FLATLINE, ABSTRACT_NOUN_DENSITY,
       FILTER_WORD_DENSITY, ADVERB_DENSITY.
"""

import re
from typing import Dict, List, Tuple


# Abstract nouns that signal reflective/flat prose when overused
_ABSTRACT_NOUNS = re.compile(
    r"\b(fear|truth|feeling|memory|hope|love|idea|thought|moment|"
    r"thing|something|nothing|everything|realization|understanding|"
    r"knowledge|sense|emotion|connection|distance|silence|"
    r"pain|guilt|shame|power|justice|freedom|trust|loyalty|"
    r"fate|destiny|reality|control|sacrifice|duty|honor|"
    r"courage|wisdom|beauty|meaning|purpose|innocence|"
    r"redemption|vengeance|mercy|strength|weakness)\b",
    re.IGNORECASE,
)

# Filter words: narrator "sees/hears/notices" instead of direct sensation
_FILTER_WORDS = re.compile(
    r"\b(I\s+)?(saw|heard|noticed|realized|felt|watched|observed|"
    r"could\s+see|could\s+hear|could\s+feel|seemed\s+to|"
    r"appeared\s+to|looked\s+like)\b",
    re.IGNORECASE,
)

# Adverbs ending in -ly (exclude common non-adverb -ly words)
_ADVERB_LY = re.compile(r"\b\w{4,}ly\b", re.IGNORECASE)
_NOT_ADVERBS = frozenset({
    "only", "early", "family", "finally", "really", "likely", "daily",
    "ugly", "holy", "belly", "ally", "lily", "fly", "july", "reply",
    "supply", "apply", "italy", "rally", "jelly", "bully", "tally",
    "fully",
})


def compute_abstract_noun_density(content: str) -> float:
    """Count abstract nouns per 1000 words. Returns density value."""
    words = content.split()
    if len(words) < 50:
        return 0.0
    hits = len(_ABSTRACT_NOUNS.findall(content))
    return round(hits / (len(words) / 1000), 1)


def _count_filter_words(content: str) -> float:
    """Count filter words per 1000 words."""
    words = content.split()
    if len(words) < 50:
        return 0.0
    hits = len(_FILTER_WORDS.findall(content))
    return round(hits / (len(words) / 1000), 1)


def _count_adverbs(content: str) -> float:
    """Count -ly adverbs per 1000 words."""
    words = content.split()
    if len(words) < 50:
        return 0.0
    matches = _ADVERB_LY.findall(content)
    hits = sum(1 for m in matches if m.lower() not in _NOT_ADVERBS)
    return round(hits / (len(words) / 1000), 1)


def scan_scene_repetition(content: str, tension_level: int = 5) -> List[str]:
    """Scan scene for repetition patterns. Returns list of flag strings.

    Flags:
    - SENTENCE_OPENING_REPETITION: >40% of sentences start with same 2-word prefix
    - RHYTHM_FLATLINE: 4+ consecutive sentences in 12-18 word band
    - ABSTRACT_NOUN_DENSITY: high density of abstract nouns (reflective prose)
    - FILTER_WORD_DENSITY: too many filter words (saw/heard/noticed/felt)
    - ADVERB_DENSITY: too many -ly adverbs
    """
    if not content or len(content.strip()) < 100:
        return []

    flags: List[str] = []
    sentences = [s.strip() for s in re.split(r"[.!?]+", content) if s.strip() and len(s.strip()) > 10]
    if len(sentences) < 5:
        return flags

    # 1. Sentence opening repetition
    from collections import Counter
    openings = []
    for s in sentences:
        words = s.split()[:2]
        if len(words) >= 2:
            openings.append(" ".join(w.lower() for w in words))
    if openings:
        most_common, count = Counter(openings).most_common(1)[0]
        if count >= len(openings) * 0.4:
            flags.append(
                "SENTENCE_OPENING_REPETITION: >40% of sentences start with same pattern — vary openings"
            )

    # 2. Rhythm flatline: 4+ consecutive in 12-18 word band
    lengths = [len(s.split()) for s in sentences]
    run = 0
    for L in lengths:
        if 12 <= L <= 18:
            run += 1
            if run >= 4:
                flags.append(
                    "RHYTHM_FLATLINE: 4+ consecutive mid-length sentences — add short punch and long build"
                )
                break
        else:
            run = 0
    else:
        # Also flag if no short (≤6) or long (≥25) sentences
        has_short = any(L <= 6 for L in lengths)
        has_long = any(L >= 25 for L in lengths)
        if not has_short or not has_long:
            flags.append(
                "RHYTHM_FLATLINE: vary sentence length (add ≤6-word punch; add ≥25-word build)"
            )

    # 3. Abstract noun density (per 1k words, threshold: 15)
    abstract_density = compute_abstract_noun_density(content)
    if abstract_density >= 15:
        flags.append(
            f"ABSTRACT_NOUN_DENSITY: {abstract_density}/1k words (threshold: 15) — replace with concrete action/sensory"
        )

    # 4. Filter word density (per 1k words, threshold: 8)
    filter_density = _count_filter_words(content)
    if filter_density >= 8:
        flags.append(
            f"FILTER_WORD_DENSITY: {filter_density}/1k words (threshold: 8) — cut saw/heard/noticed/felt, use direct sensation"
        )

    # 5. Adverb density (per 1k words, threshold: 12)
    adverb_density = _count_adverbs(content)
    if adverb_density >= 12:
        flags.append(
            f"ADVERB_DENSITY: {adverb_density}/1k words (threshold: 12) — cut adverbs that echo the verb"
        )

    return flags


def scan_scene_for_polish(content: str, tension_level: int = 5) -> List[str]:
    """Alias for scan_scene_repetition. Used by voice_human_pass and prose_polish."""
    return scan_scene_repetition(content, tension_level)
