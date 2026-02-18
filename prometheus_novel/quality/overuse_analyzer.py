"""Overuse analyzer — detect words and phrases used too often.

Scans a manuscript for:
1. Word frequency: significant words (non-stopwords, 3+ chars) over threshold
2. Phrase frequency: 2–5 word n-grams over threshold

Outputs a report and optional YAML in phrase_replacement_banks format
for dynamic detection and replacement. Integrates with phrase_suppressor.
"""

import re
import string
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_STOPWORDS = frozenset(
    "i me my myself we our ours ourselves you your yours yourself yourselves "
    "he him his herself she her hers it its they them their what which who "
    "this that these those am is are was were be been being have has had "
    "do does did doing a an the and but if or because as until while of at "
    "by for with about against between through during before after above "
    "below to from up down in out on off over under again further then once "
    "here there when where why how all both each few more most other some "
    "such no nor not only own same so than too very just can will should "
    "now".split()
)


def _normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower()
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2014", " ").replace("\u2013", " ")
    text = text.translate(str.maketrans("", "", string.punctuation))
    return " ".join(text.split())


def _extract_ngrams(text: str, n: int) -> List[str]:
    """Extract word-level n-grams."""
    words = text.split()
    if len(words) < n:
        return []
    return [" ".join(words[i : i + n]) for i in range(len(words) - n + 1)]


def _stopword_ratio(phrase: str) -> float:
    """Fraction of tokens that are stopwords."""
    tokens = phrase.split()
    return sum(1 for t in tokens if t in _STOPWORDS) / len(tokens) if tokens else 0


def _has_content_word(phrase: str) -> bool:
    """Phrase has at least one non-stopword alphabetic token."""
    return any(t not in _STOPWORDS and t.isalpha() for t in phrase.split())


# Common words to exclude from word-frequency report (often acceptable)
_DEFAULT_IGNORE_WORDS = frozenset(["like", "into", "one", "back", "way", "something"])


def analyze_overuse(
    text: str,
    *,
    word_threshold: int = 10,
    phrase_threshold: int = 10,
    phrase_min_words: int = 2,
    phrase_max_words: int = 5,
    phrase_min_chars: int = 8,
    phrase_max_stopword_ratio: float = 0.70,
    min_word_len: int = 3,
    ignore_words: Optional[set] = None,
) -> Dict[str, Any]:
    """Detect overused words and phrases.

    Args:
        text: Full manuscript text.
        word_threshold: Flag words with count > this.
        phrase_threshold: Flag phrases with count > this.
        phrase_min_words: Minimum n-gram size.
        phrase_max_words: Maximum n-gram size.
        phrase_min_chars: Minimum phrase length.
        phrase_max_stopword_ratio: Skip phrases with too many stopwords.
        min_word_len: Minimum word length for word-frequency.

    Returns:
        Dict with overused_words, overused_phrases, stats.
    """
    ignore = _DEFAULT_IGNORE_WORDS if ignore_words is None else ignore_words
    norm = _normalize(text)
    words = norm.split()

    # 1. Word frequency (content words only)
    word_counts: Counter = Counter()
    for w in words:
        if len(w) >= min_word_len and w not in _STOPWORDS and w.isalpha() and w not in ignore:
            word_counts[w] += 1

    overused_words = [
        {"word": w, "count": c}
        for w, c in word_counts.most_common()
        if c > word_threshold
    ]

    # 2. Phrase frequency (n-grams)
    phrase_counts: Counter = Counter()
    for n in range(phrase_min_words, phrase_max_words + 1):
        for ng in _extract_ngrams(norm, n):
            phrase_counts[ng] += 1

    overused_phrases = []
    for phrase, count in phrase_counts.most_common():
        if count <= phrase_threshold:
            continue
        if len(phrase) < phrase_min_chars:
            continue
        if _stopword_ratio(phrase) > phrase_max_stopword_ratio:
            continue
        if not _has_content_word(phrase):
            continue
        overused_phrases.append({
            "phrase": phrase,
            "count": count,
            "keep_first": min(2, max(1, count // 5)),
        })

    # Deduplicate overlapping phrases (prefer longer)
    seen = set()
    final_phrases = []
    for entry in sorted(overused_phrases, key=lambda x: (-len(x["phrase"].split()), -x["count"])):
        p = entry["phrase"]
        if any(p in s and p != s for s in seen):
            continue
        final_phrases.append(entry)
        seen.add(p)

    return {
        "overused_words": overused_words,
        "overused_phrases": final_phrases,
        "stats": {
            "word_count": len(words),
            "unique_content_words": len(word_counts),
            "words_over_threshold": len(overused_words),
            "phrases_over_threshold": len(final_phrases),
            "word_threshold": word_threshold,
            "phrase_threshold": phrase_threshold,
        },
    }


def report_to_replacement_yaml(
    report: Dict[str, Any],
    output_path: Path,
    *,
    include_words: bool = True,
    include_phrases: bool = True,
    top_words: int = 50,
    top_phrases: int = 50,
) -> Path:
    """Write overuse report to YAML in phrase_replacement_banks format.

    Phrases get placeholder replacement lists; words get empty lists.
    User can add replacements and merge with phrase_replacement_banks.yaml.
    """
    banks: Dict[str, List[str]] = {}
    if include_phrases:
        for entry in report.get("overused_phrases", [])[:top_phrases]:
            banks[entry["phrase"]] = []  # User fills in alternatives
    if include_words:
        for entry in report.get("overused_words", [])[:top_words]:
            banks[entry["word"]] = []  # User fills in alternatives

    data = {
        "banks": banks,
        "_meta": {
            "word_threshold": report.get("stats", {}).get("word_threshold", 10),
            "phrase_threshold": report.get("stats", {}).get("phrase_threshold", 10),
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    import yaml
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    return output_path
