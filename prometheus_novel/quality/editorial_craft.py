"""Editorial craft checks — manuscript-level patterns a developmental editor would flag.

Adds to craft_scorecard:
- Motif saturation (PRICE_TAGS, CITRUS, SALT, etc. per chapter)
- Gesture frequency (per-character physical tic overuse)
- Scene transition grounding (TIME/PLACE/CAST in first 50 words)
- Simile density (per 1000 words)
- Chapter length distribution (flag outliers)
- Paragraph-ending cadence variation
"""

import logging
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger("editorial_craft")

# Motif categories for saturation check (Editorial Craft Gaps #2)
MOTIF_PATTERNS = {
    "CITRUS": re.compile(r"\b(lemon|lemons|lemon-scented|citrus|orange zest|grapefruit|bergamot)\b", re.IGNORECASE),
    "SALT": re.compile(r"\b(salt air|salt spray|salt on|salty|salt of|salt-bleached)\b", re.IGNORECASE),
    "PRICE_TAGS": re.compile(r"€\d+(?:\.\d{2})?|\$\d+(?:\.\d{2})?|\d+\.\d{2}(?:\s*euro|eur)?", re.IGNORECASE),
    "MOTHS_LIGHT": re.compile(r"\b(moth|moths)\b.*\b(light|lantern|lamp|bulb)\b|\b(light|lantern).*\b(moth)", re.IGNORECASE),
    "COFFEE_STAINS": re.compile(r"\b(coffee ring|coffee stain|ring of|dried.*cup|cup.*stain)\b", re.IGNORECASE),
    "STICKY_SURFACES": re.compile(r"\b(sticky|tacky|residue|ring of.*dried)\b", re.IGNORECASE),
    "SCAR_TOUCHING": re.compile(r"\b(scar|scarred).*(touch|brush|finger|thumb)|(touch|brush|finger).*(scar)\b", re.IGNORECASE),
    "HAIR_TUCKING": re.compile(r"\b(tuck(?:ed|ing)?\s+.*(?:hair|curl).*behind)\b", re.IGNORECASE),
}

# Per-character gesture patterns (character -> [(pattern, label), ...])
GESTURE_PATTERNS = {
    "lena": [
        (re.compile(r"\b(tuck(?:ed|ing)?\s+(?:a\s+)?curl\s+behind\s+(?:my|her)\s+ear)\b", re.IGNORECASE), "curl_tuck"),
        (re.compile(r"\b(press(?:ed|ing)\s+(?:my|her)\s+thumb\s+against)\b", re.IGNORECASE), "thumb_press"),
        (re.compile(r"\b(straighten(?:ed|ing)\s+(?:my|her)\s+shoulders)\b", re.IGNORECASE), "shoulders_straighten"),
        (re.compile(r"\b(I\s+cross(?:ed|ing)\s+my\s+arms|crossed\s+my\s+arms)\b", re.IGNORECASE), "cross_arms"),
    ],
    "marco": [
        (re.compile(r"\b(ran\s+(?:his|my)\s+hand\s+through\s+(?:his|my)\s+hair)\b", re.IGNORECASE), "hair_run"),
        (re.compile(r"\b((?:his|my)\s+jaw\s+(?:work(?:ed|ing)|tighten(?:ed|ing)))\b", re.IGNORECASE), "jaw_work"),
        (re.compile(r"\bleaving\s+it\s+(?:ruffled|rumpled)\b", re.IGNORECASE), "leaving_ruffled"),
    ],
}

# Simile markers
SIMILE_PATTERNS = [
    re.compile(r"\blike\s+(?:a|an|the)\b", re.IGNORECASE),
    re.compile(r"\bas\s+if\b", re.IGNORECASE),
    re.compile(r"\bas\s+though\b", re.IGNORECASE),
    re.compile(r"\bthe\s+way\s+[a-z]+\s+[a-z]+\b", re.IGNORECASE),
]

# Paragraph-ending classification
_CADENCE_LYRICAL = re.compile(r"\b(moment|connection|promise|truth|heart|soul|walls?|armor|barrier)\b.*[.!?]$", re.IGNORECASE)
_CADENCE_SENSORY = re.compile(r"\b(warmth|cool|heat|skin|breath|touch|fingers|lips)\b.*[.!?]$", re.IGNORECASE)
_CADENCE_ABRUPT = re.compile(r"^[^.!?]{1,35}[.!?]\s*$", re.MULTILINE)  # Short sentence

# Tense detection (Editorial Craft Gaps #6) — approximate via common verb patterns
_PRESENT_VERBS = re.compile(r"\b(am|is|are|was|were)\b|\b(\w+)(?:s|es)\s+(?:\w+\s+)*\b|\b(I|we|you|they)\s+(\w+)\b", re.IGNORECASE)
_PAST_VERBS = re.compile(r"\b(was|were|had|did)\b|\b(\w+ed)\b|\b(\w+)(?:t|d)\s+", re.IGNORECASE)
# Simplified: count " -ed " words vs " -s " (3rd person present) and "is/are" vs "was/were"
_PAST_SIMPLE = re.compile(r"\b\w+ed\b", re.IGNORECASE)
_PRESENT_S = re.compile(r"\b(he|she|it|marco|lena|sofia|dante|gianna)\s+\w+s\b", re.IGNORECASE)
_IS_ARE = re.compile(r"\b(is|are)\b", re.IGNORECASE)
_WAS_WERE = re.compile(r"\b(was|were)\b", re.IGNORECASE)


def _chapters_from_scenes(scenes: List[Dict]) -> Dict[int, str]:
    """Build chapter_num -> full text."""
    by_ch: Dict[int, List[str]] = defaultdict(list)
    for s in (scenes or []):
        if not isinstance(s, dict):
            continue
        ch = int(s.get("chapter", 0))
        content = s.get("content", "")
        if content:
            by_ch[ch].append(content)
    return {ch: "\n\n".join(texts) for ch, texts in by_ch.items()}


def motif_saturation_meter(scenes: List[Dict]) -> Dict[str, Any]:
    """Flag motif categories appearing in >60% of chapters or >3x total for specific devices."""
    chapters = _chapters_from_scenes(scenes)
    total_chapters = len(chapters)
    if total_chapters == 0:
        return {"violations": [], "per_motif": {}, "pass": True}

    violations = []
    per_motif: Dict[str, Dict] = {}

    for name, pat in MOTIF_PATTERNS.items():
        ch_count = sum(1 for text in chapters.values() if pat.search(text))
        total_count = sum(len(pat.findall(text)) for text in chapters.values())
        pct_chapters = ch_count / total_chapters if total_chapters else 0
        per_motif[name] = {"chapters_with": ch_count, "total_occurrences": total_count, "pct_chapters": round(pct_chapters, 2)}

        if pct_chapters > 0.6:
            violations.append({
                "type": "motif_saturation",
                "motif": name,
                "message": f"{name} appears in {ch_count}/{total_chapters} chapters ({pct_chapters*100:.0f}%). "
                           "Consider varying: use different grounding devices (child's drawing, dented railing, chalkboard menu).",
            })
        if name == "PRICE_TAGS" and total_count > 3:
            violations.append({
                "type": "device_overuse",
                "motif": name,
                "message": f"Price tags/stickers appear {total_count}x. After 3 uses, vary the grounding device.",
            })

    return {"violations": violations, "per_motif": per_motif, "pass": len(violations) == 0}


def gesture_frequency_meter(scenes: List[Dict], config: Dict) -> Dict[str, Any]:
    """Flag physical tics exceeding max per character (default 3)."""
    max_per_gesture = 3
    counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    violations = []

    for s in (scenes or []):
        if not isinstance(s, dict):
            continue
        content = s.get("content", "")
        for char_key, patterns in GESTURE_PATTERNS.items():
            for pat, label in patterns:
                n = len(pat.findall(content))
                if n > 0:
                    counts[char_key][label] += n

    for char_key, gestures in counts.items():
        for label, count in gestures.items():
            if count > max_per_gesture:
                violations.append({
                    "type": "gesture_overuse",
                    "character": char_key,
                    "gesture": label,
                    "count": count,
                    "message": f"{char_key.title()} uses '{label.replace('_', ' ')}' {count}x (max {max_per_gesture}). "
                               "Replace excess with: temple press, pleat tablecloth, bite cheek, rotate ring.",
                })

    return {"violations": violations, "counts": {k: dict(v) for k, v in counts.items()}, "pass": len(violations) == 0}


def scene_transition_grounding(scenes: List[Dict]) -> Dict[str, Any]:
    """Check first 50 words of each scene for TIME, PLACE, CAST — need 2 of 3."""
    time_pat = re.compile(r"\b(morning|afternoon|evening|night|dawn|dusk|hours? later|minutes? later|"
                          r"the next day|when|by the time|two hours)\b", re.IGNORECASE)
    place_pat = re.compile(r"\b(courtyard|balcony|villa|room|kitchen|terrace|grove|beach|chapel|"
                          r"monastery|office|path|stone|inside|outside)\b", re.IGNORECASE)
    cast_pat = re.compile(r"\b(Marco|Lena|Sofia|Dante|Gianna|Enzo)\b")  # Character names

    violations = []
    for s in (scenes or []):
        if not isinstance(s, dict):
            continue
        content = s.get("content", "")
        first_50 = " ".join(content.split()[:50])
        if len(first_50.split()) < 20:
            continue
        has_time = bool(time_pat.search(first_50))
        has_place = bool(place_pat.search(first_50))
        has_cast = bool(cast_pat.search(first_50))
        present = sum([has_time, has_place, has_cast])
        if present < 2:
            sid = s.get("scene_id") or f"ch{int(s.get('chapter',0)):02d}_s{int(s.get('scene_number',0)):02d}"
            violations.append({
                "type": "transition_ungrounded",
                "scene_id": sid,
                "message": f"{sid} opens with insufficient grounding (only {present}/3: time, place, cast). "
                           "Add brief orienting clause in first 50 words.",
            })

    return {"violations": violations, "pass": len(violations) == 0}


def simile_density_meter(scenes: List[Dict], target_per_1k: float = 1.5) -> Dict[str, Any]:
    """Count similes per 1000 words. Romance target ~1.0-1.5; flag if >2.0."""
    full_text = "\n\n".join(s.get("content", "") for s in (scenes or []) if isinstance(s, dict))
    words = len(full_text.split())
    if words < 500:
        return {"similes_per_1k": 0, "violations": [], "pass": True}

    simile_count = sum(len(pat.findall(full_text)) for pat in SIMILE_PATTERNS)
    per_1k = simile_count / (words / 1000)

    violations = []
    if per_1k > 2.0:
        violations.append({
            "type": "simile_density",
            "message": f"Simile density {per_1k:.1f}/1000 words (target 1.0-1.5). "
                       "Cut weakest similes: clichés, redundant comparisons, overextended metaphors.",
        })

    return {"similes_per_1k": round(per_1k, 2), "total_similes": simile_count, "words": words,
            "violations": violations, "pass": len(violations) == 0}


def chapter_length_meter(scenes: List[Dict]) -> Dict[str, Any]:
    """Flag chapters deviating >25% from mean. Resolution chapter should be at least 80% of mean."""
    chapters = _chapters_from_scenes(scenes)
    if not chapters:
        return {"violations": [], "per_chapter": {}, "pass": True}

    lengths = {ch: len(text.split()) for ch, text in chapters.items()}
    mean_len = sum(lengths.values()) / len(lengths)
    violations = []
    last_ch = max(chapters.keys()) if chapters else 0

    for ch, wc in lengths.items():
        pct_of_mean = wc / mean_len if mean_len else 1
        if abs(pct_of_mean - 1) > 0.25:
            violations.append({
                "type": "chapter_length_deviation",
                "chapter": ch,
                "words": wc,
                "pct_of_mean": round(pct_of_mean, 2),
                "message": f"Ch{ch} is {wc} words ({pct_of_mean*100:.0f}% of mean {mean_len:.0f}). "
                           "Consider rebalancing." + (" Resolution chapter feels truncated." if ch == last_ch and pct_of_mean < 0.8 else ""),
            })

    return {"violations": violations, "per_chapter": lengths, "mean": round(mean_len, 0), "pass": len(violations) == 0}


def tense_consistency_meter(scenes: List[Dict]) -> Dict[str, Any]:
    """Flag scenes with ambiguous or mixed tense. Editorial Craft Gaps #6."""
    violations = []
    per_scene = {}
    for s in (scenes or []):
        if not isinstance(s, dict):
            continue
        content = s.get("content", "")
        past_ed = len(_PAST_SIMPLE.findall(content))
        present_s = len(_PRESENT_S.findall(content))
        is_are = len(_IS_ARE.findall(content))
        was_were = len(_WAS_WERE.findall(content))
        past_score = past_ed + was_were
        present_score = present_s + is_are
        total = past_score + present_score
        sid = s.get("scene_id") or f"ch{int(s.get('chapter',0)):02d}_s{int(s.get('scene_number',0)):02d}"

        if total < 5:
            per_scene[sid] = {"dominant": "unknown"}
            continue

        pct_past = past_score / total
        pct_present = present_score / total
        per_scene[sid] = {"pct_past": round(pct_past, 2), "pct_present": round(pct_present, 2)}

        if pct_past >= 0.6:
            per_scene[sid]["dominant"] = "past"
        elif pct_present >= 0.6:
            per_scene[sid]["dominant"] = "present"
        else:
            per_scene[sid]["dominant"] = "ambiguous"
            violations.append({
                "type": "tense_ambiguous",
                "scene_id": sid,
                "message": f"{sid} mixed tense ({pct_past*100:.0f}% past, {pct_present*100:.0f}% present). "
                           "Establish dominant; exception for dialogue, flashbacks.",
            })

    if scenes:
        all_content = "\n\n".join(s.get("content", "") for s in scenes if isinstance(s, dict) and s.get("content"))
        total_past = len(_PAST_SIMPLE.findall(all_content)) + len(_WAS_WERE.findall(all_content))
        total_present = len(_PRESENT_S.findall(all_content)) + len(_IS_ARE.findall(all_content))
        total = total_past + total_present
        if total > 20:
            ms_pct = total_present / total
            if 0.35 <= ms_pct <= 0.65:
                violations.append({
                    "type": "tense_manuscript_mixed",
                    "message": f"Manuscript mixes past ({100-ms_pct*100:.0f}%) and present ({ms_pct*100:.0f}%). "
                               "Consider config.narration.tense: present|past.",
                })

    return {"violations": violations, "per_scene": per_scene, "pass": len(violations) == 0}


def paragraph_cadence_meter(scenes: List[Dict]) -> Dict[str, Any]:
    """Flag consecutive LYRICAL paragraph endings (>3) and low FLAT representation."""
    violations = []
    for s in (scenes or []):
        if not isinstance(s, dict):
            continue
        content = s.get("content", "")
        paras = [p.strip() for p in content.split("\n\n") if p.strip() and len(p.strip()) > 10]
        if len(paras) < 5:
            continue

        endings = []
        for p in paras:
            # Extract last sentence: after final . ! or ?
            parts = re.split(r"(?<=[.!?])\s+", p.strip())
            last_sent = (parts[-1] if parts else p.strip()).strip()
            if not last_sent:
                endings.append("FLAT")
                continue
            if _CADENCE_LYRICAL.search(last_sent):
                endings.append("LYRICAL")
            elif _CADENCE_SENSORY.search(last_sent):
                endings.append("SENSORY")
            elif len(last_sent.split()) < 8:
                endings.append("ABRUPT")
            else:
                endings.append("FLAT")

        # Check consecutive LYRICAL
        run = 0
        for e in endings:
            if e == "LYRICAL":
                run += 1
                if run > 3:
                    sid = s.get("scene_id") or f"ch{int(s.get('chapter',0)):02d}_s{int(s.get('scene_number',0)):02d}"
                    violations.append({
                        "type": "cadence_lyrical_run",
                        "scene_id": sid,
                        "message": f"{sid} has {run}+ consecutive LYRICAL paragraph endings. "
                                   "Rewrite some to end FLAT or ABRUPT for rhythm.",
                    })
                    break
            else:
                run = 0

        flat_pct = endings.count("FLAT") / len(endings) if endings else 0
        if flat_pct < 0.2 and len(endings) >= 5:
            sid = s.get("scene_id") or f"ch{int(s.get('chapter',0)):02d}_s{int(s.get('scene_number',0)):02d}"
            violations.append({
                "type": "cadence_flat_low",
                "scene_id": sid,
                "message": f"{sid} has only {flat_pct*100:.0f}% FLAT paragraph endings. "
                           "Strong writing varies; add factual/action endings.",
            })

    return {"violations": violations, "pass": len(violations) == 0}


def run_editorial_craft_checks(
    scenes: List[Dict],
    config: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Run all editorial craft checks. Merge into craft_scorecard or report separately."""
    config = config or {}
    scenes_list = [s for s in (scenes or []) if isinstance(s, dict)]
    if not scenes_list:
        return {"skipped": "no scenes"}

    all_violations = []
    report = {}

    m = motif_saturation_meter(scenes_list)
    report["motif_saturation"] = m
    all_violations.extend(m.get("violations", []))

    g = gesture_frequency_meter(scenes_list, config)
    report["gesture_frequency"] = g
    all_violations.extend(g.get("violations", []))

    t = scene_transition_grounding(scenes_list)
    report["scene_transitions"] = t
    all_violations.extend(t.get("violations", []))

    s = simile_density_meter(scenes_list)
    report["simile_density"] = s
    all_violations.extend(s.get("violations", []))

    c = chapter_length_meter(scenes_list)
    report["chapter_length"] = c
    all_violations.extend(c.get("violations", []))

    tns = tense_consistency_meter(scenes_list)
    report["tense_consistency"] = tns
    all_violations.extend(tns.get("violations", []))

    p = paragraph_cadence_meter(scenes_list)
    report["paragraph_cadence"] = p
    all_violations.extend(p.get("violations", []))

    report["violations"] = all_violations
    report["pass"] = len(all_violations) == 0

    if all_violations:
        for v in all_violations[:5]:  # Log first 5
            logger.warning("Editorial craft: %s", v.get("message", v))

    return report
