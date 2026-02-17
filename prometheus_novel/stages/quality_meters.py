"""
Deterministic (non-LLM) quality meters for local model evaluation.

Three meters that catch the exact failure modes local models tend to have:
1. Repetition meter  -- ngram overlap across scenes (loops)
2. Scene name dedup  -- duplicate/near-duplicate scene titles (recycling)
3. Voice distinctiveness -- character dialogue overlap (same-voice syndrome)

All meters are cheap (regex + counting, no LLM needed) and produce
numeric scores storable in scene.meta and run_report.json.
"""

import re
import logging
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("quality_meters")


def _derive_scene_id(scene: Dict) -> str:
    """Fallback when scene_id missing: ch02_s01 format."""
    ch = scene.get("chapter") or scene.get("ch", 0)
    sc = scene.get("scene_number") or scene.get("scene", 0)
    try:
        return f"ch{int(ch):02d}_s{int(sc):02d}"
    except (TypeError, ValueError):
        return f"ch??_s??"


def scene_id_integrity_check(scenes: List[Dict]) -> Dict:
    """Validate scene_id consistency: expected vs actual, uniqueness, no gaps.

    Catches reorder drift, duplicate IDs, and upstream omission.
    Run after outline or before export as a seatbelt alarm.

    Returns:
        {
            "pass": bool,
            "mismatches": [(expected, actual, chapter, scene_idx), ...],
            "duplicates": [scene_id, ...],
            "missing": [(chapter, scene_idx), ...],
        }
    """
    mismatches = []
    seen_ids: Dict[str, int] = {}
    missing = []

    for i, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            continue
        ch = scene.get("chapter", 0) or 0
        sc_num = scene.get("scene_number") or scene.get("scene", i + 1) or (i + 1)
        try:
            ch_int = int(ch)
            sc_int = int(sc_num)
        except (TypeError, ValueError):
            ch_int, sc_int = 0, i + 1
        expected = f"ch{ch_int:02d}_s{sc_int:02d}"
        actual = scene.get("scene_id")

        if not actual:
            missing.append((ch_int, sc_int))
            continue

        if actual != expected:
            mismatches.append((expected, actual, ch_int, sc_int))

        if actual in seen_ids:
            seen_ids[actual] += 1
        else:
            seen_ids[actual] = 1

    duplicates = [sid for sid, count in seen_ids.items() if count > 1]
    passed = not mismatches and not duplicates and not missing

    if not passed:
        logger.warning(
            f"scene_id integrity failed: mismatches={len(mismatches)}, "
            f"duplicates={duplicates[:5]}, missing={len(missing)}"
        )

    return {
        "pass": passed,
        "mismatches": mismatches,
        "duplicates": duplicates,
        "missing": missing,
    }


# ============================================================================
# 1. REPETITION METER
# ============================================================================

def _extract_ngrams(text: str, n: int = 4) -> List[str]:
    """Extract word n-grams from text, lowercased, stopwords kept."""
    words = re.findall(r'\b[a-z]+\b', text.lower())
    if len(words) < n:
        return []
    return [" ".join(words[i:i+n]) for i in range(len(words) - n + 1)]


def repetition_meter(
    scenes: List[Dict],
    local_window: int = 10,
    ngram_size: int = 4,
    local_threshold: float = 0.15,
    global_hot_count: int = 3,
) -> Dict:
    """Measure repetition across scenes using n-gram overlap.

    Returns:
        {
            "local_flags": [(scene_idx, overlap_ratio, shared_phrases), ...],
            "global_hot_phrases": [(phrase, count), ...],
            "per_scene_overlap": [float, ...],
            "avg_overlap": float,
            "max_overlap": float,
            "pass": bool,
        }
    """
    all_ngrams_per_scene = []
    global_ngram_counts = Counter()

    for scene in scenes:
        content = scene.get("content", "")
        ngrams = set(_extract_ngrams(content, ngram_size))
        all_ngrams_per_scene.append(ngrams)
        global_ngram_counts.update(ngrams)

    local_flags = []
    per_scene_overlap = []

    for i, current_ngrams in enumerate(all_ngrams_per_scene):
        if not current_ngrams:
            per_scene_overlap.append(0.0)
            continue

        # Compare against previous N scenes (local window)
        window_start = max(0, i - local_window)
        window_ngrams = set()
        for j in range(window_start, i):
            window_ngrams |= all_ngrams_per_scene[j]

        if not window_ngrams:
            per_scene_overlap.append(0.0)
            continue

        shared = current_ngrams & window_ngrams
        overlap = len(shared) / len(current_ngrams) if current_ngrams else 0.0
        per_scene_overlap.append(round(overlap, 3))

        if overlap > local_threshold:
            # Get top shared phrases for diagnostics
            top_shared = sorted(shared)[:5]
            local_flags.append((i, round(overlap, 3), top_shared))

    # Global hot phrases: ngrams appearing in 3+ scenes
    global_hot = [
        (phrase, count)
        for phrase, count in global_ngram_counts.most_common(20)
        if count >= global_hot_count
    ]

    avg_overlap = (
        sum(per_scene_overlap) / len(per_scene_overlap)
        if per_scene_overlap else 0.0
    )
    max_overlap = max(per_scene_overlap) if per_scene_overlap else 0.0

    # Pass: no more than 1 flag per 10 scenes
    max_flags = max(1, len(scenes) // 10)
    passed = len(local_flags) <= max_flags

    return {
        "local_flags": local_flags,
        "global_hot_phrases": global_hot,
        "per_scene_overlap": per_scene_overlap,
        "avg_overlap": round(avg_overlap, 3),
        "max_overlap": round(max_overlap, 3),
        "flagged_scenes": len(local_flags),
        "total_scenes": len(scenes),
        "pass": passed,
    }


# ============================================================================
# 2. SCENE NAME DEDUP METER
# ============================================================================

def _normalize_name(name: str) -> str:
    """Normalize scene name for comparison: lowercase, strip punctuation."""
    return re.sub(r'[^a-z0-9\s]', '', name.lower()).strip()


def _token_jaccard(a: str, b: str) -> float:
    """Token-level Jaccard similarity between two strings."""
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def scene_name_dedup_meter(
    outline: List[Dict],
    exact_threshold: float = 1.0,
    fuzzy_threshold: float = 0.6,
) -> Dict:
    """Detect duplicate and near-duplicate scene names in the outline.

    Returns:
        {
            "exact_duplicates": [(name, count, locations), ...],
            "near_duplicates": [(name_a, name_b, jaccard, loc_a, loc_b), ...],
            "total_names": int,
            "unique_names": int,
            "duplicate_count": int,
            "near_duplicate_count": int,
            "pass": bool,
        }
    """
    # Collect all scene names with locations
    scene_names = []  # [(normalized, original, "Ch{x}-S{y}")]
    for ch in outline:
        if not isinstance(ch, dict):
            continue
        ch_num = ch.get("chapter", ch.get("chapter_number", "?"))
        for sc in ch.get("scenes", []):
            if not isinstance(sc, dict):
                continue
            sc_num = sc.get("scene", sc.get("scene_number", "?"))
            name = sc.get("scene_name", "")
            if name:
                norm = _normalize_name(name)
                scene_names.append((norm, name, f"Ch{ch_num}-S{sc_num}"))

    # Exact duplicates
    name_counts = Counter(norm for norm, _, _ in scene_names)
    exact_dupes = []
    for norm, count in name_counts.items():
        if count > 1:
            locations = [loc for n, _, loc in scene_names if n == norm]
            original = next(orig for n, orig, _ in scene_names if n == norm)
            exact_dupes.append((original, count, locations))

    # Near duplicates (Jaccard > threshold)
    near_dupes = []
    checked = set()
    for i, (norm_a, orig_a, loc_a) in enumerate(scene_names):
        for j, (norm_b, orig_b, loc_b) in enumerate(scene_names):
            if i >= j:
                continue
            pair_key = (min(norm_a, norm_b), max(norm_a, norm_b))
            if pair_key in checked:
                continue
            checked.add(pair_key)

            if norm_a == norm_b:
                continue  # Already in exact_dupes

            jaccard = _token_jaccard(norm_a, norm_b)
            if jaccard >= fuzzy_threshold:
                near_dupes.append((orig_a, orig_b, round(jaccard, 2), loc_a, loc_b))

    unique_names = len(set(norm for norm, _, _ in scene_names))
    dup_count = sum(c - 1 for _, c, _ in exact_dupes)

    # Pass: <=2 total duplicates (exact + near)
    passed = (dup_count + len(near_dupes)) <= 2

    return {
        "exact_duplicates": exact_dupes,
        "near_duplicates": near_dupes,
        "total_names": len(scene_names),
        "unique_names": unique_names,
        "duplicate_count": dup_count,
        "near_duplicate_count": len(near_dupes),
        "pass": passed,
    }


# ============================================================================
# 3. VOICE DISTINCTIVENESS METER
# ============================================================================

def _extract_dialogue_by_character(
    scenes: List[Dict],
    characters: List[Dict],
) -> Dict[str, List[str]]:
    """Extract dialogue lines attributed to each character.

    Heuristic: looks for patterns like:
      "dialogue" I said
      "dialogue" she/he said
      "dialogue" [Character] said
    """
    char_names = {}
    for ch in characters:
        if isinstance(ch, dict) and ch.get("name"):
            name = ch["name"]
            # Map full name and first name
            char_names[name.lower()] = name
            first = name.split()[0]
            if len(first) > 2:
                char_names[first.lower()] = name

    dialogue_by_char = defaultdict(list)

    for scene in scenes:
        content = scene.get("content", "")
        if not content:
            continue

        pov = scene.get("pov", "").lower()

        # Find dialogue + attribution patterns
        # Pattern: "dialogue" followed by attribution
        for match in re.finditer(
            r'[\u201c"]([^\u201d"]{10,})[\u201d"][^\u201d"]*?(?:(\w+)\s+(?:said|whispered|murmured|replied|asked|snapped|muttered|called|yelled|answered|demanded|insisted|admitted|suggested|offered|growled|hissed|breathed))',
            content, re.IGNORECASE
        ):
            dialogue_text = match.group(1)
            speaker_ref = match.group(2).lower()

            # Determine speaker
            if speaker_ref == "i":
                # First person = POV character
                for cname_lower, cname in char_names.items():
                    if cname_lower in pov or pov in cname_lower:
                        dialogue_by_char[cname].append(dialogue_text)
                        break
            elif speaker_ref in char_names:
                dialogue_by_char[char_names[speaker_ref]].append(dialogue_text)
            elif speaker_ref in ("she", "he", "they"):
                # Try to attribute based on context (best effort)
                pass

    return dict(dialogue_by_char)


def _word_profile(texts: List[str], top_n: int = 30) -> Counter:
    """Build a word frequency profile from a list of texts."""
    stopwords = {
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
    }

    words = Counter()
    for text in texts:
        for word in re.findall(r'\b[a-z]+\b', text.lower()):
            if word not in stopwords and len(word) > 2:
                words[word] += 1

    return Counter(dict(words.most_common(top_n)))


def voice_distinctiveness_meter(
    scenes: List[Dict],
    characters: List[Dict],
    overlap_threshold: float = 0.55,
) -> Dict:
    """Measure how distinct each character's dialogue voice is.

    Compares top-30 word profiles across characters using Jaccard.
    High overlap = "same speaker syndrome."

    Returns:
        {
            "character_profiles": {name: [top words]},
            "pairwise_overlap": [(char_a, char_b, jaccard), ...],
            "avg_overlap": float,
            "max_overlap": float,
            "lines_per_character": {name: count},
            "pass": bool,
        }
    """
    dialogue_by_char = _extract_dialogue_by_character(scenes, characters)

    if len(dialogue_by_char) < 2:
        return {
            "character_profiles": {},
            "pairwise_overlap": [],
            "avg_overlap": 0.0,
            "max_overlap": 0.0,
            "lines_per_character": {
                k: len(v) for k, v in dialogue_by_char.items()
            },
            "pass": True,
            "note": "Fewer than 2 characters with dialogue found",
        }

    # Build word profiles
    profiles = {}
    for char_name, lines in dialogue_by_char.items():
        if len(lines) >= 2:  # Need at least 2 lines for meaningful profile
            profile = _word_profile(lines)
            profiles[char_name] = profile

    if len(profiles) < 2:
        return {
            "character_profiles": {
                k: list(v.keys())[:10] for k, v in profiles.items()
            },
            "pairwise_overlap": [],
            "avg_overlap": 0.0,
            "max_overlap": 0.0,
            "lines_per_character": {
                k: len(v) for k, v in dialogue_by_char.items()
            },
            "pass": True,
            "note": "Fewer than 2 characters with sufficient dialogue",
        }

    # Pairwise Jaccard on top words
    char_names = sorted(profiles.keys())
    pairwise = []
    for i, name_a in enumerate(char_names):
        for j, name_b in enumerate(char_names):
            if i >= j:
                continue
            words_a = set(profiles[name_a].keys())
            words_b = set(profiles[name_b].keys())
            if not words_a or not words_b:
                continue
            jaccard = len(words_a & words_b) / len(words_a | words_b)
            pairwise.append((name_a, name_b, round(jaccard, 3)))

    avg_overlap = (
        sum(j for _, _, j in pairwise) / len(pairwise)
        if pairwise else 0.0
    )
    max_overlap = max((j for _, _, j in pairwise), default=0.0)

    passed = max_overlap < overlap_threshold

    return {
        "character_profiles": {
            k: list(v.keys())[:10] for k, v in profiles.items()
        },
        "pairwise_overlap": pairwise,
        "avg_overlap": round(avg_overlap, 3),
        "max_overlap": round(max_overlap, 3),
        "lines_per_character": {
            k: len(v) for k, v in dialogue_by_char.items()
        },
        "pass": passed,
    }


# ============================================================================
# 4. SEMANTIC SCENE SIMILARITY METER
# ============================================================================

_SCENE_STOPWORDS = {
    "the", "a", "an", "i", "you", "we", "he", "she", "they", "it",
    "is", "are", "was", "were", "be", "been", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may",
    "might", "can", "to", "of", "in", "for", "on", "with", "at",
    "by", "from", "as", "into", "through", "during", "before", "after",
    "and", "but", "or", "not", "so", "yet", "if", "when", "than",
    "that", "this", "what", "which", "who", "my", "your", "his", "her",
    "its", "our", "their", "me", "him", "us", "them", "said", "just",
    "like", "then", "back", "out", "up", "down", "now", "even", "still",
    "only", "very", "too", "also", "much", "more", "most", "some",
    "all", "any", "been", "being", "own", "other", "over", "such",
    "about", "between", "each", "how", "off",
}


def _content_keywords(text: str, top_n: int = 40) -> Counter:
    """Extract top content words from scene text (lightweight TF proxy)."""
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())
    filtered = [w for w in words if w not in _SCENE_STOPWORDS]
    return Counter(dict(Counter(filtered).most_common(top_n)))


def _keyword_jaccard(a: Counter, b: Counter) -> float:
    """Jaccard similarity on keyword sets."""
    keys_a = set(a.keys())
    keys_b = set(b.keys())
    if not keys_a or not keys_b:
        return 0.0
    return len(keys_a & keys_b) / len(keys_a | keys_b)


def scene_body_similarity_meter(
    scenes: List[Dict],
    similarity_threshold: float = 0.50,
    top_keywords: int = 40,
) -> Dict:
    """Detect scenes with suspiciously similar content (same beats, different titles).

    Uses top-N content keyword Jaccard as a lightweight TF-IDF proxy.
    Catches: "The Vault Door" vs "The Archive Lock" with identical story beats.

    Returns:
        {
            "similar_pairs": [(scene_a_id, scene_b_id, jaccard, shared_words), ...],
            "max_similarity": float,
            "avg_similarity": float,
            "pass": bool,
            "scene_id_fallback": [sid, ...]  # When upstream omitted scene_id; aids debugging
        }
    """
    # Build keyword profiles per scene; track fallback IDs for diagnostics
    profiles = []
    fallback_sids = []
    for scene in scenes:
        content = scene.get("content", "")
        sid = scene.get("scene_id") or _derive_scene_id(scene)
        if not scene.get("scene_id"):
            fallback_sids.append(sid)
        keywords = _content_keywords(content, top_keywords)
        profiles.append((sid, keywords))

    similar_pairs = []
    all_sims = []

    for i in range(len(profiles)):
        for j in range(i + 1, len(profiles)):
            sid_a, kw_a = profiles[i]
            sid_b, kw_b = profiles[j]
            sim = _keyword_jaccard(kw_a, kw_b)
            all_sims.append(sim)
            if sim >= similarity_threshold:
                shared = sorted(set(kw_a.keys()) & set(kw_b.keys()))[:10]
                similar_pairs.append((sid_a, sid_b, round(sim, 3), shared))

    avg_sim = sum(all_sims) / len(all_sims) if all_sims else 0.0
    max_sim = max(all_sims) if all_sims else 0.0

    # Pass: no pair exceeds threshold
    passed = len(similar_pairs) == 0

    result = {
        "similar_pairs": similar_pairs,
        "max_similarity": round(max_sim, 3),
        "avg_similarity": round(avg_sim, 3),
        "total_pairs": len(all_sims),
        "flagged_pairs": len(similar_pairs),
        "pass": passed,
    }
    if fallback_sids:
        result["scene_id_fallback"] = fallback_sids  # Upstream omitted scene_id; derived
    return result


# ============================================================================
# 5. VOICE SUB-METRICS (catchphrase overuse + rhythm variance)
# ============================================================================

def voice_sub_metrics(
    scenes: List[Dict],
    characters: List[Dict],
    catchphrase_dominance_threshold: float = 0.40,
    min_rhythm_variance: float = 3.0,
) -> Dict:
    """Additional voice quality checks beyond word-profile Jaccard.

    Sub-metric A: Catchphrase overuse penalty
      If a character's top-3 dialogue words account for >40% of their total
      dialogue word count, flag as "catchphrase overuse" (bland repetition).

    Sub-metric B: Dialogue rhythm variance
      Measure sentence-length variance within each character's dialogue.
      Real voices differ in rhythm, not just vocabulary.

    Returns:
        {
            "catchphrase_flags": [(char, top3_ratio, top3_words), ...],
            "rhythm_per_character": {char: {"avg_len": float, "std_dev": float}},
            "rhythm_flags": [(char, std_dev), ...],
            "pass": bool,
        }
    """
    dialogue_by_char = _extract_dialogue_by_character(scenes, characters)

    catchphrase_flags = []
    rhythm_data = {}
    rhythm_flags = []

    for char_name, lines in dialogue_by_char.items():
        if len(lines) < 3:
            continue

        # A) Catchphrase dominance
        all_words = []
        for line in lines:
            all_words.extend(re.findall(r'\b[a-z]{3,}\b', line.lower()))
        content_words = [w for w in all_words if w not in _SCENE_STOPWORDS]
        if content_words:
            counts = Counter(content_words)
            top3 = counts.most_common(3)
            top3_total = sum(c for _, c in top3)
            ratio = top3_total / len(content_words)
            if ratio > catchphrase_dominance_threshold:
                catchphrase_flags.append((
                    char_name,
                    round(ratio, 3),
                    [w for w, _ in top3]
                ))

        # B) Rhythm variance (sentence lengths within dialogue)
        sentence_lengths = []
        for line in lines:
            sents = [s.strip() for s in re.split(r'[.!?]+', line) if s.strip()]
            sentence_lengths.extend(len(s.split()) for s in sents)

        if sentence_lengths:
            avg_len = sum(sentence_lengths) / len(sentence_lengths)
            std_dev = (sum((l - avg_len) ** 2 for l in sentence_lengths) / len(sentence_lengths)) ** 0.5
            rhythm_data[char_name] = {
                "avg_len": round(avg_len, 1),
                "std_dev": round(std_dev, 1),
            }
            if std_dev < min_rhythm_variance:
                rhythm_flags.append((char_name, round(std_dev, 1)))

    passed = len(catchphrase_flags) == 0 and len(rhythm_flags) == 0

    return {
        "catchphrase_flags": catchphrase_flags,
        "rhythm_per_character": rhythm_data,
        "rhythm_flags": rhythm_flags,
        "pass": passed,
    }


# ============================================================================
# COMBINED REPORT
# ============================================================================

def run_all_meters(
    scenes: List[Dict],
    outline: List[Dict],
    characters: List[Dict],
) -> Dict:
    """Run all meters including scene_id integrity. Return combined report.

    Returns:
        {
            "scene_id_integrity": {...},
            "repetition": {...},
            "scene_dedup": {...},
            "voice": {...},
            "scene_similarity": {...},
            "voice_sub": {...},
            "all_pass": bool,
        }
    """
    integrity = scene_id_integrity_check(scenes) if scenes else {
        "pass": True, "note": "No scenes to check"
    }
    rep = repetition_meter(scenes) if scenes else {
        "pass": True, "note": "No scenes to check"
    }
    dedup = scene_name_dedup_meter(outline) if outline else {
        "pass": True, "note": "No outline to check"
    }
    voice = voice_distinctiveness_meter(scenes, characters) if scenes else {
        "pass": True, "note": "No scenes to check"
    }
    sim = scene_body_similarity_meter(scenes) if scenes and len(scenes) >= 2 else {
        "pass": True, "note": "Need 2+ scenes for similarity check"
    }
    vsub = voice_sub_metrics(scenes, characters) if scenes else {
        "pass": True, "note": "No scenes to check"
    }

    return {
        "scene_id_integrity": integrity,
        "repetition": rep,
        "scene_dedup": dedup,
        "voice": voice,
        "scene_similarity": sim,
        "voice_sub": vsub,
        "all_pass": (
            integrity.get("pass", True) and rep.get("pass", True) and
            dedup.get("pass", True) and voice.get("pass", True) and
            sim.get("pass", True) and vsub.get("pass", True)
        ),
    }


def print_meter_report(report: Dict) -> None:
    """Print a human-readable meter report to stdout."""
    print("\n--- DETERMINISTIC QUALITY METERS ---")

    # Scene ID integrity
    integrity = report.get("scene_id_integrity", {})
    status = "PASS" if integrity.get("pass") else "FAIL"
    print(f"\n  [0] Scene ID Integrity: {status}")
    if not integrity.get("pass"):
        if integrity.get("mismatches"):
            for exp, act, ch, sc in integrity["mismatches"][:5]:
                print(f"      Mismatch: expected {exp}, got {act} (ch{ch} s{sc})")
        if integrity.get("duplicates"):
            print(f"      Duplicates: {integrity['duplicates'][:5]}")
        if integrity.get("missing"):
            print(f"      Missing: {len(integrity['missing'])} scenes without scene_id")

    # Repetition
    rep = report.get("repetition", {})
    status = "PASS" if rep.get("pass") else "FAIL"
    print(f"\n  [1] Repetition Meter: {status}")
    print(f"      Avg overlap:   {rep.get('avg_overlap', 0):.3f}")
    print(f"      Max overlap:   {rep.get('max_overlap', 0):.3f}")
    print(f"      Flagged:       {rep.get('flagged_scenes', 0)}/{rep.get('total_scenes', 0)} scenes")
    if rep.get("local_flags"):
        for idx, overlap, phrases in rep["local_flags"][:3]:
            print(f"      Scene {idx}: overlap={overlap} [{', '.join(phrases[:2])}...]")
    if rep.get("global_hot_phrases"):
        print(f"      Hot phrases:   {len(rep['global_hot_phrases'])} (appearing 3+ times)")
        for phrase, count in rep["global_hot_phrases"][:3]:
            print(f"        \"{phrase}\" ({count}x)")

    # Scene dedup
    dedup = report.get("scene_dedup", {})
    status = "PASS" if dedup.get("pass") else "FAIL"
    print(f"\n  [2] Scene Name Dedup: {status}")
    print(f"      Total names:   {dedup.get('total_names', 0)}")
    print(f"      Unique names:  {dedup.get('unique_names', 0)}")
    print(f"      Exact dupes:   {dedup.get('duplicate_count', 0)}")
    print(f"      Near dupes:    {dedup.get('near_duplicate_count', 0)}")
    if dedup.get("exact_duplicates"):
        for name, count, locs in dedup["exact_duplicates"][:3]:
            print(f"        \"{name}\" x{count} at {', '.join(locs)}")
    if dedup.get("near_duplicates"):
        for a, b, jac, loc_a, loc_b in dedup["near_duplicates"][:3]:
            print(f"        \"{a}\" ~ \"{b}\" (jaccard={jac}) at {loc_a}, {loc_b}")

    # Voice
    voice = report.get("voice", {})
    status = "PASS" if voice.get("pass") else "FAIL"
    print(f"\n  [3] Voice Distinctiveness: {status}")
    lines = voice.get("lines_per_character", {})
    if lines:
        for char, count in sorted(lines.items()):
            top = voice.get("character_profiles", {}).get(char, [])
            top_str = ", ".join(top[:5]) if top else "n/a"
            print(f"      {char}: {count} lines [{top_str}]")
    if voice.get("pairwise_overlap"):
        for a, b, jac in voice["pairwise_overlap"]:
            flag = " <<< SIMILAR" if jac >= 0.55 else ""
            print(f"      {a} vs {b}: jaccard={jac}{flag}")
    print(f"      Avg overlap:   {voice.get('avg_overlap', 0):.3f}")
    print(f"      Max overlap:   {voice.get('max_overlap', 0):.3f}")
    if voice.get("note"):
        print(f"      Note: {voice['note']}")

    # Scene similarity
    sim = report.get("scene_similarity", {})
    status = "PASS" if sim.get("pass") else "FAIL"
    print(f"\n  [4] Scene Body Similarity: {status}")
    print(f"      Avg similarity: {sim.get('avg_similarity', 0):.3f}")
    print(f"      Max similarity: {sim.get('max_similarity', 0):.3f}")
    print(f"      Flagged pairs:  {sim.get('flagged_pairs', 0)}/{sim.get('total_pairs', 0)}")
    if sim.get("similar_pairs"):
        for a, b, jac, shared in sim["similar_pairs"][:3]:
            print(f"        {a} ~ {b}: jaccard={jac} [{', '.join(shared[:5])}]")
    if sim.get("note"):
        print(f"      Note: {sim['note']}")

    # Voice sub-metrics
    vsub = report.get("voice_sub", {})
    status = "PASS" if vsub.get("pass") else "FAIL"
    print(f"\n  [5] Voice Sub-Metrics: {status}")
    if vsub.get("catchphrase_flags"):
        for char, ratio, words in vsub["catchphrase_flags"]:
            print(f"      CATCHPHRASE: {char} top-3 = {ratio:.0%} [{', '.join(words)}]")
    else:
        print(f"      Catchphrase overuse: None")
    rhythm = vsub.get("rhythm_per_character", {})
    if rhythm:
        for char, data in sorted(rhythm.items()):
            std = data.get("std_dev", data.get("variance", 0))
            flag = " <<< MONOTONE" if std < 3.0 else ""
            print(f"      {char}: avg_len={data['avg_len']}, rhythm_std={std}{flag}")
    if vsub.get("rhythm_flags"):
        print(f"      Rhythm flags: {len(vsub['rhythm_flags'])} characters monotone")
    if vsub.get("note"):
        print(f"      Note: {vsub['note']}")

    # Overall
    overall = "PASS" if report.get("all_pass") else "FAIL"
    print(f"\n  METERS OVERALL: {overall}")
