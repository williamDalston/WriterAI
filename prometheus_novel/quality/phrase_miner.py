"""Model-agnostic hot phrase miner.

Scans all scenes in a manuscript and automatically surfaces repeated phrases
(n-grams) that signal AI template usage or stylistic monotony.

Outputs a structured report and optionally writes a YAML config file
that the suppression pass can consume.
"""

import re
import string
import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)

# English stopwords (lightweight, no nltk dependency)
_STOPWORDS = frozenset(
    "i me my myself we our ours ourselves you your yours yourself yourselves "
    "he him his himself she her hers herself it its itself they them their "
    "theirs themselves what which who whom this that these those am is are "
    "was were be been being have has had having do does did doing a an the "
    "and but if or because as until while of at by for with about against "
    "between through during before after above below to from up down in out "
    "on off over under again further then once here there when where why how "
    "all both each few more most other some such no nor not only own same so "
    "than too very s t can will just don should now d ll m o re ve y ain "
    "aren couldn didn doesn hadn hasn haven isn ma mightn mustn needn shan "
    "shouldn wasn weren won wouldn".split()
)


def _normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower()
    # Replace smart quotes/dashes with plain equivalents
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2014", " ").replace("\u2013", " ")
    text = text.translate(str.maketrans("", "", string.punctuation))
    return " ".join(text.split())


def _extract_ngrams(text: str, n: int) -> List[str]:
    """Extract word-level n-grams from normalized text."""
    words = text.split()
    if len(words) < n:
        return []
    return [" ".join(words[i : i + n]) for i in range(len(words) - n + 1)]


def _stopword_ratio(phrase: str) -> float:
    """Fraction of tokens that are stopwords."""
    tokens = phrase.split()
    if not tokens:
        return 1.0
    return sum(1 for t in tokens if t in _STOPWORDS) / len(tokens)


def _has_content_word(phrase: str) -> bool:
    """Check if phrase contains at least one non-stopword alphabetic token."""
    return any(t not in _STOPWORDS and t.isalpha() for t in phrase.split())


def mine_hot_phrases(
    scenes: List[str],
    *,
    n_min: int = 3,
    n_max: int = 8,
    min_total: int = 8,
    min_scenes: int = 4,
    max_in_scene_threshold: int = 3,
    burst_threshold: int = 5,
    window: int = 10,
    min_phrase_chars: int = 14,
    max_stopword_ratio: float = 0.60,
    ignore_phrases: Optional[List[str]] = None,
    ignore_regex: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Mine repeated phrases from a list of scene texts.

    Args:
        scenes: List of scene text strings (in chapter/scene order).
        n_min/n_max: N-gram size range (inclusive).
        min_total: Minimum total occurrences to flag.
        min_scenes: Minimum distinct scenes to flag.
        max_in_scene_threshold: Flag if any single scene has this many.
        burst_threshold: Flag if sliding window has this many.
        window: Sliding window size for burst detection.
        min_phrase_chars: Minimum character length for a phrase.
        max_stopword_ratio: Skip phrases with more stopwords than this.
        ignore_phrases: Phrases to skip entirely.
        ignore_regex: Regex patterns to skip.

    Returns:
        Dict with 'phrases' list (sorted by severity) and 'stats'.
    """
    ignore_set = set(_normalize(p) for p in (ignore_phrases or []))
    ignore_patterns = [re.compile(r, re.IGNORECASE) for r in (ignore_regex or [])]

    # Phase 1: Extract n-grams per scene
    scene_ngrams: List[Counter] = []
    for scene_text in scenes:
        norm = _normalize(scene_text)
        counter: Counter = Counter()
        for n in range(n_min, n_max + 1):
            for ng in _extract_ngrams(norm, n):
                counter[ng] += 1
        scene_ngrams.append(counter)

    # Phase 2: Aggregate counts
    total_counts: Counter = Counter()
    scene_presence: Dict[str, int] = defaultdict(int)
    max_in_scene: Dict[str, int] = defaultdict(int)
    per_scene_counts: Dict[str, List[int]] = defaultdict(list)

    for idx, counter in enumerate(scene_ngrams):
        seen_in_scene = set()
        for phrase, count in counter.items():
            total_counts[phrase] += count
            if phrase not in seen_in_scene:
                scene_presence[phrase] += 1
                seen_in_scene.add(phrase)
            max_in_scene[phrase] = max(max_in_scene[phrase], count)
        # Track per-scene for burst detection
        for phrase in total_counts:
            per_scene_counts[phrase].append(counter.get(phrase, 0))

    # Pad per_scene_counts to scene count length
    num_scenes = len(scenes)
    for phrase in per_scene_counts:
        while len(per_scene_counts[phrase]) < num_scenes:
            per_scene_counts[phrase].append(0)

    # Phase 3: Compute burst scores
    def _burst_score(counts: List[int], w: int) -> int:
        if len(counts) < w:
            return sum(counts)
        return max(sum(counts[i : i + w]) for i in range(len(counts) - w + 1))

    # Phase 4: Filter and flag
    flagged = []
    for phrase, total in total_counts.items():
        # Basic filters
        if len(phrase) < min_phrase_chars:
            continue
        if not _has_content_word(phrase):
            continue
        if _stopword_ratio(phrase) > max_stopword_ratio:
            continue
        if phrase in ignore_set:
            continue
        if any(pat.search(phrase) for pat in ignore_patterns):
            continue

        sc_count = scene_presence[phrase]
        mis = max_in_scene[phrase]
        burst = _burst_score(per_scene_counts[phrase], window)

        # Flag conditions
        is_flagged = False
        reason = []
        if total >= min_total and sc_count >= min_scenes:
            is_flagged = True
            reason.append(f"total={total} scenes={sc_count}")
        if mis >= max_in_scene_threshold:
            is_flagged = True
            reason.append(f"max_in_scene={mis}")
        if burst >= burst_threshold:
            is_flagged = True
            reason.append(f"burst={burst}")

        if is_flagged:
            # Severity scoring: higher = worse
            severity = total * 2 + sc_count + mis * 3 + burst
            flagged.append({
                "phrase": phrase,
                "total_count": total,
                "scene_count": sc_count,
                "max_in_scene": mis,
                "burst_score": burst,
                "severity": severity,
                "reason": "; ".join(reason),
                "keep_first": min(2, max(1, total // 5)),
            })

    # Sort by severity (descending)
    flagged.sort(key=lambda x: x["severity"], reverse=True)

    # Deduplicate overlapping phrases: if a longer phrase contains a shorter one
    # and both are flagged, prefer the longer one
    final = []
    seen_phrases = set()
    for entry in flagged:
        phrase = entry["phrase"]
        # Check if this phrase is a substring of an already-kept longer phrase
        is_subphrase = any(phrase in kept and phrase != kept for kept in seen_phrases)
        if not is_subphrase:
            final.append(entry)
            seen_phrases.add(phrase)

    return {
        "phrases": final,
        "stats": {
            "total_scenes": num_scenes,
            "unique_ngrams_checked": len(total_counts),
            "phrases_flagged": len(final),
        },
    }


def write_auto_yaml(
    report: Dict[str, Any],
    output_path: Path,
    top_n: int = 50,
) -> Path:
    """Write auto-generated hot phrases YAML for the suppression pass.

    Args:
        report: Output from mine_hot_phrases().
        output_path: Where to write the YAML.
        top_n: Maximum phrases to include.

    Returns:
        Path to the written file.
    """
    phrases_out = []
    for entry in report["phrases"][:top_n]:
        phrases_out.append({
            "phrase": entry["phrase"],
            "total": entry["total_count"],
            "scenes": entry["scene_count"],
            "severity": "high" if entry["severity"] > 30 else "medium",
            "keep_first": entry["keep_first"],
        })

    data = {
        "generated": True,
        "rules": {
            "min_total": 8,
            "min_scenes": 4,
        },
        "phrases": phrases_out,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    logger.info("Wrote %d hot phrases to %s", len(phrases_out), output_path)
    return output_path


def load_phrase_config(
    auto_path: Optional[Path] = None,
    manual_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Load and merge manual + auto hot phrase configs.

    Manual entries override auto entries for the same phrase.
    """
    phrases: Dict[str, Dict[str, Any]] = {}

    for path in [auto_path, manual_path]:
        if path and path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            for entry in data.get("phrases", []):
                phrases[entry["phrase"]] = entry

    return sorted(phrases.values(), key=lambda x: x.get("total", 0), reverse=True)


def load_miner_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load optional miner configuration (ignore lists, thresholds)."""
    defaults = {
        "ignore_phrases": [],
        "ignore_regex": [],
    }
    if config_path and config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        defaults.update(data)
    return defaults
