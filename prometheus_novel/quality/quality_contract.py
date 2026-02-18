"""
Quality Contract v1 — deterministic craft checks for cadence, causality, escalation, specificity.

Produces per-scene JSON audit trail with warnings:
- CAUSALITY: connector paragraphs with no prior reference; "somehow/suddenly/it hit me" without stimulus
- DEFLECTION: high-tension scene has 2+ reflective paragraphs in a row (no threat/choice/revelation)
- WALLPAPER_RISK: no OBJECT/SOCIAL/TIME anchors (only BODY + ATMOSPHERE)
- DIALOGUE_EXPOSITORY: high-tension scene, dialogue lines too long; 2+ commas + because/that/which
- RHYTHM_FLATLINE: sentence length variance below threshold

Model-agnostic, genre-safe, all-books.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("quality_contract")

# Connectors that MUST reference prior beat when starting a paragraph
_CONNECTOR_STARTS = re.compile(r"^\s*(And|But|Still|Then|So),\s", re.IGNORECASE)

# "Because vibes" transitions — need concrete stimulus in prior 1-2 sentences
_VIBES_PHRASES = [
    r"\bsomehow\b",
    r"\bsuddenly\b",
    r"\bfor a moment\b",
    r"\bit hit me\b",
    r"\bit struck me\b",
    r"\bsomething about (?:it|that|him|her)\b",
]
_VIBES_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _VIBES_PHRASES]

# Prior noun/pronoun anchors for causal link check (simple heuristic)
_ANCHOR_WORDS = re.compile(
    r"\b(i|me|my|he|him|his|she|her|they|them|we|us|it|this|that|here|there)\b",
    re.IGNORECASE,
)

# Anchor category regexes (lightweight heuristics)
_OBJECT_ANCHOR = re.compile(
    r"\b(phone|keys|letter|book|cup|glass|knife|gun|bag|ring|watch|door|table|chair)\b|"
    r"\b(hand|fist|finger|wrist)\s+(around|on|gripping|holding)\b",
    re.IGNORECASE,
)
_PLACE_ANCHOR = re.compile(
    r"\b(corner|doorway|wall|window|stairs|hall|room|street|alley)\b|"
    r"\b(across|behind|between|against)\s+(the|a)\b",
    re.IGNORECASE,
)
_SOCIAL_ANCHOR = re.compile(
    r"\b(said|asked|told|whispered|yelled)\b|"
    r"\b(other people|strangers|crowd|everyone|nobody)\b|"
    r"\b(rule|law|protocol|proper|expected)\b|"
    r"\b(status|rank|position)\b",
    re.IGNORECASE,
)
_TIME_ANCHOR = re.compile(
    r"\b(minutes|hours|days|weeks|deadline|midnight|noon|morning|evening)\b|"
    r"\b(before|after|until|by the time)\b|"
    r"\b(running out|run out|too late|in time)\b",
    re.IGNORECASE,
)
_MONEY_ANCHOR = re.compile(
    r"\b(cost|price|pay|paid|owe|owed|dollar|euro|budget|expensive|cheap)\b|"
    r"\b(distance|miles|kilometers)\b|"
    r"\b(procedure|process|paperwork)\b",
    re.IGNORECASE,
)
_BODY_ANCHOR = re.compile(
    r"\b(hand|eye|face|chest|heart|breath|pulse|blood)\b|"
    r"\b(ached|trembled|flinched|stiffened)\b",
    re.IGNORECASE,
)
_ATMOSPHERE_ANCHOR = re.compile(
    r"\b(warm|cold|quiet|loud|dark|bright|soft|sharp)\b|"
    r"\b(rain|wind|sun|light|shadow|smell|scent)\b",
    re.IGNORECASE,
)

# Opening move heuristics (first ~80 words)
_OPENING_DIALOGUE = re.compile(r'^["\']|^\s*["\']', re.MULTILINE)
_OPENING_ACTION = re.compile(
    r"^(?:I|She|He|They|We)\s+(stood|walked|ran|grabbed|reached|pushed|turned|stepped)",
    re.IGNORECASE,
)
_OPENING_SETTING = re.compile(
    r"^(?:The|A|An)\s+(?:room|house|street|sun|rain|morning|evening|light|darkness)",
    re.IGNORECASE,
)
_OPENING_INTERNAL = re.compile(
    r"^(?:I|She|He)\s+(?:knew|thought|wondered|realized|felt|wished|hoped|believed)",
    re.IGNORECASE,
)
_OPENING_FLASHBACK = re.compile(
    r"\b(years ago|months ago|that (?:morning|night|day)|back when|the last time)\b",
    re.IGNORECASE,
)

# Expository dialogue risk: 2+ commas AND because/that/which (within a single line)
def _is_expository_line(line: str) -> bool:
    if line.count(",") < 2:
        return False
    return bool(re.search(r"\b(because|that|which)\b", line, re.IGNORECASE))


def _derive_scene_id(scene: Dict, idx: int) -> str:
    """Fallback scene_id."""
    ch = scene.get("chapter") or scene.get("ch", 0)
    sc = scene.get("scene_number") or scene.get("scene", 0)
    try:
        return f"ch{int(ch):02d}_s{int(sc):02d}"
    except (TypeError, ValueError):
        return f"ch??_s{idx:02d}"


def _get_tension_level(scene: Dict, outline: List[Dict]) -> int:
    """Get tension_level for scene from outline or default 5."""
    ch = scene.get("chapter", 0)
    sc = scene.get("scene_number") or scene.get("scene", 0)
    for chapter in (outline or []):
        if not isinstance(chapter, dict):
            continue
        if int(chapter.get("chapter", 0)) == int(ch):
            for s in chapter.get("scenes", []):
                if not isinstance(s, dict):
                    continue
                if int(s.get("scene", s.get("scene_number", 0))) == int(sc):
                    try:
                        return int(s.get("tension_level", 5))
                    except (TypeError, ValueError):
                        return 5
            break
    return 5


def _tag_paragraph_type(para: str) -> str:
    """Classify paragraph as ACTION, DIALOGUE, INTERNAL, or DESCRIPTION."""
    para = para.strip()
    if not para:
        return "DESCRIPTION"
    # Dialogue-heavy
    quote_count = para.count('"') + para.count("'")
    if quote_count >= 2 and len(para.split()) < 80:
        return "DIALOGUE"
    # Action: physical verbs, movement
    if re.search(
        r"\b(grabbed|pushed|ran|walked|turned|reached|stepped|stood|sat|threw)\b",
        para,
        re.IGNORECASE,
    ):
        return "ACTION"
    # Internal: thought, felt, knew, wondered
    if re.search(
        r"\b(I|she|he)\s+(knew|thought|felt|wondered|realized|wished|hoped|believed)\b",
        para,
        re.IGNORECASE,
    ):
        return "INTERNAL"
    # Default: description
    return "DESCRIPTION"


def _check_causality(paragraphs: List[str]) -> List[str]:
    """Flag paragraphs with causal/logic violations."""
    warnings = []
    prev_text = ""
    for i, para in enumerate(paragraphs):
        if not para.strip():
            continue
        para_lower = para.strip().lower()

        # Connector without prior reference
        if _CONNECTOR_STARTS.match(para):
            prev_words = set(prev_text.lower().split())
            para_word_list = para_lower.split()[:15]  # first 15 words as list
            # Check for noun/pronoun overlap with prior
            anchors_in_para = set(_ANCHOR_WORDS.findall(para))
            if not prev_text or (not any(w in prev_words for w in para_word_list)):
                warnings.append(
                    f"CAUSALITY: paragraph {i+1} starts with connector but may not reference prior beat"
                )

        # Vibes phrases without concrete stimulus
        for pat in _VIBES_PATTERNS:
            if pat.search(para):
                prev_sents = re.split(r"[.!?]+", prev_text)[-2:]  # Last 2 sentences
                prev_combined = " ".join(s.strip() for s in prev_sents if s.strip())
                if not prev_combined or len(prev_combined.split()) < 8:
                    warnings.append(
                        f"CAUSALITY: paragraph {i+1} uses '{pat.pattern}' without clear prior stimulus"
                    )
                break

        prev_text += " " + para

    return warnings


def _check_deflection(paragraphs: List[str], tension_level: int) -> List[str]:
    """For tension>=6, flag 2+ consecutive reflective (INTERNAL+DESCRIPTION) paragraphs."""
    if tension_level < 6:
        return []

    tags = [_tag_paragraph_type(p) for p in paragraphs if p.strip()]
    if len(tags) < 3:
        return []

    reflective = {"INTERNAL", "DESCRIPTION"}
    run = 0
    max_run = 0
    for t in tags:
        if t in reflective:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 0

    if max_run >= 2:
        return [
            "DEFLECTION: high-tension scene has 2+ reflective paragraphs in a row — "
            "add threat, choice, revelation, or friction"
        ]
    return []


def _check_anchor_categories(content: str) -> Tuple[Dict[str, bool], List[str]]:
    """Detect anchor categories present. WALLPAPER_RISK if only BODY + ATMOSPHERE."""
    found = {
        "OBJECT": bool(_OBJECT_ANCHOR.search(content)),
        "PLACE": bool(_PLACE_ANCHOR.search(content)),
        "SOCIAL": bool(_SOCIAL_ANCHOR.search(content)),
        "TIME": bool(_TIME_ANCHOR.search(content)),
        "MONEY": bool(_MONEY_ANCHOR.search(content)),
        "BODY": bool(_BODY_ANCHOR.search(content)),
        "ATMOSPHERE": bool(_ATMOSPHERE_ANCHOR.search(content)),
    }
    meaningful = found["OBJECT"] or found["PLACE"] or found["SOCIAL"] or found["TIME"] or found["MONEY"]
    only_wallpaper = found["BODY"] or found["ATMOSPHERE"]
    if only_wallpaper and not meaningful:
        return found, ["WALLPAPER_RISK: no OBJECT/SOCIAL/TIME anchors detected"]
    return found, []


def _check_dialogue_line_economy(
    content: str, tension_level: int
) -> Tuple[float, int, List[str]]:
    """Short-line ratio and expository risk for high-tension scenes."""
    warnings = []
    # Extract quoted dialogue lines (double quotes + smart quotes only;
    # single quotes match contractions like don't/can't, so skip them)
    lines = re.findall(r'"([^"]+)"', content)
    lines.extend(re.findall(r'[\u201c]([^\u201d]+)[\u201d]', content))
    if not lines:
        return 1.0, 0, []

    short = sum(1 for L in lines if len(L.split()) <= 10)
    ratio = short / len(lines)
    expository = sum(1 for L in lines if _is_expository_line(L))

    if tension_level >= 6:
        if ratio < 0.30:
            warnings.append(
                f"DIALOGUE_EXPOSITORY: high-tension scene — only {ratio:.0%} dialogue lines under 10 words "
                f"(target 30-40%)"
            )
        if expository > 0:
            warnings.append(
                f"DIALOGUE_EXPOSITORY: {expository} dialogue line(s) with 2+ commas + because/that/which"
            )

    return ratio, expository, warnings


def _classify_opening_move(text: str) -> str:
    """Classify first ~80 words as IN_MEDIAS_RES, DIALOGUE, SETTING, INTERNAL, FLASHBACK."""
    first = " ".join(text.split()[:80]) if text else ""
    if not first:
        return "UNKNOWN"
    if _OPENING_DIALOGUE.search(first[:50]):
        return "DIALOGUE"
    if _OPENING_ACTION.search(first[:80]):
        return "IN_MEDIAS_RES"
    if _OPENING_FLASHBACK.search(first[:120]):
        return "FLASHBACK"
    if _OPENING_INTERNAL.search(first[:60]):
        return "INTERNAL"
    if _OPENING_SETTING.search(first[:60]):
        return "SETTING"
    return "UNKNOWN"


def _check_rhythm_variance(content: str) -> Tuple[bool, bool, List[str]]:
    """Check for very short (<=6), long (>=25), and flatline (N consecutive in 12-18 band)."""
    warnings = []
    sentences = re.split(r"[.!?]+", content)
    sentences = [s.strip() for s in sentences if s.strip()]

    lengths = [len(s.split()) for s in sentences]
    if not lengths:
        return False, False, []

    has_short = any(l <= 6 for l in lengths)
    has_long = any(l >= 25 for l in lengths)

    # Rolling window: 4+ consecutive in 12-18 word band
    band = [12, 18]
    run = 0
    max_run = 0
    for l in lengths:
        if band[0] <= l <= band[1]:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 0

    if max_run >= 4:
        warnings.append(
            "RHYTHM_FLATLINE: 4+ consecutive sentences in 12-18 word band — vary length"
        )
    if not has_short:
        warnings.append("RHYTHM_FLATLINE: no very short sentence (≤6 words)")
    if not has_long:
        warnings.append("RHYTHM_FLATLINE: no long sentence (≥25 words)")

    return has_short, has_long, warnings


def run_quality_contract(
    scenes: List[Dict],
    outline: List[Dict],
    quality_polish_report: Optional[Dict] = None,
) -> Dict:
    """Run all Quality Contract checks. Returns per-scene contracts + opening move history.

    Returns:
        {
            "contracts": [
                {
                    "scene_id": "Ch02_s01",
                    "tension_level": 7,
                    "opening_move": "IN_MEDIAS_RES",
                    "edits": {"phrase_suppressor": 3, "dialogue_trimmer": 2, ...},
                    "warnings": ["DEFLECTION: ...", "WALLPAPER_RISK: ..."],
                },
                ...
            ],
            "opening_move_history": [{"chapter": 1, "move": "DIALOGUE"}, ...],
            "opening_move_violations": ["Ch3 repeats Ch2 opening type"],
        }
    """
    contracts = []
    opening_move_history: List[Dict] = []
    opening_move_violations: List[str] = []
    prev_move: Optional[str] = None
    prev_chapter = 0

    # Extract edit counts from quality_polish_report (scene-agnostic totals)
    def get_edits(report: Optional[Dict]) -> Dict:
        if not report:
            return {}
        edits = {}
        for key, short_key in [
            ("phrase_suppression", "phrase_suppressor"),
            ("dialogue_trimming", "dialogue_trimmer"),
            ("emotion_diversification", "emotion_diversifier"),
            ("cliche_cluster_repair", "cliche_cluster"),
        ]:
            r = report.get(key, {})
            if isinstance(r, dict):
                total = r.get("total_replacements") or r.get("total_replaced") or r.get("tags_trimmed", 0)
                if isinstance(total, (int, float)) and total > 0:
                    edits[short_key] = int(total)
        return edits

    report_edits = get_edits(quality_polish_report)

    for idx, scene in enumerate(scenes or []):
        if not isinstance(scene, dict):
            continue
        content = scene.get("content", "")
        scene_id = scene.get("scene_id") or _derive_scene_id(scene, idx)
        ch = int(scene.get("chapter", 0))
        sc = int(scene.get("scene_number") or scene.get("scene", 0))
        tension_level = _get_tension_level(scene, outline)

        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        all_warnings: List[str] = []

        # Causality
        all_warnings.extend(_check_causality(paragraphs))

        # Deflection
        all_warnings.extend(_check_deflection(paragraphs, tension_level))

        # Anchor categories
        _, anchor_warnings = _check_anchor_categories(content)
        all_warnings.extend(anchor_warnings)

        # Dialogue economy
        _, _, dialogue_warnings = _check_dialogue_line_economy(content, tension_level)
        all_warnings.extend(dialogue_warnings)

        # Rhythm
        _, _, rhythm_warnings = _check_rhythm_variance(content)
        all_warnings.extend(rhythm_warnings)

        # Quiet Killers (per-scene deterministic checks)
        try:
            from quality.quiet_killers import (
                check_continuity_tripwires,
                check_pronoun_clarity,
                check_stakes_articulation,
                check_generic_verbs,
                check_filter_overuse,
                check_dialogue_tidy,
                check_truncation,
                _classify_ending,
            )
            all_warnings.extend(check_continuity_tripwires(content))
            all_warnings.extend(check_truncation(content))
            all_warnings.extend(check_pronoun_clarity(content))
            all_warnings.extend(check_stakes_articulation(content, tension_level))
            all_warnings.extend(check_generic_verbs(content))
            all_warnings.extend(check_filter_overuse(content))
            all_warnings.extend(check_dialogue_tidy(content, tension_level))
            last_para = paragraphs[-1].strip() if paragraphs else ""
            if last_para:
                ending = _classify_ending(last_para)
                if ending in ("SUMMARY", "ATMOSPHERE"):
                    all_warnings.append(
                        f"FINAL_LINE_{ending}: scene ends with {ending}—consider ACTION or DIALOGUE"
                    )
        except ImportError:
            pass
        except Exception as e:
            logger.debug("Quiet killers check failed (non-blocking): %s", e)

        # Tension curve compliance: flag sharp drops between adjacent scenes
        if idx > 0 and outline:
            prev_tension = _get_tension_level((scenes or [])[idx - 1], outline)
            if prev_tension >= 7 and tension_level <= 3:
                all_warnings.append(
                    f"TENSION_COLLAPSE: scene drops from {prev_tension} to {tension_level}—consider smoother transition"
                )

        # Ch1 first 250-word hook: must have dialogue, action, or concrete question
        if ch == 1 and sc == 1 and content:
            first_250 = " ".join(content.split()[:250])
            has_dialogue = '"' in first_250 or '\u201c' in first_250
            has_action = bool(re.search(
                r"\b(grabbed|walked|ran|reached|pushed|turned|stepped|stood|threw)\b",
                first_250, re.IGNORECASE,
            ))
            has_question = "?" in first_250
            if not (has_dialogue or has_action or has_question) and len(first_250.split()) >= 100:
                all_warnings.append(
                    "CH1_HOOK_WEAK: first 250 words lack dialogue, action, or question—hook readers earlier"
                )

        # Scene function classification (F2)
        scene_func = "UNKNOWN"
        try:
            from quality.quiet_killers import classify_scene_function, _get_purpose_from_outline
            purpose_text = _get_purpose_from_outline(scene, outline or [])
            scene_func = classify_scene_function(content, purpose_text)
        except (ImportError, Exception):
            pass

        # Dynamic Conflict Guard: scene following REVEAL must not immediately resolve tension
        if idx > 0:
            prev_scene = (scenes or [])[idx - 1]
            if isinstance(prev_scene, dict):
                prev_content = prev_scene.get("content", "")
                prev_func = "UNKNOWN"
                try:
                    from quality.quiet_killers import classify_scene_function, _get_purpose_from_outline
                    prev_purpose = _get_purpose_from_outline(prev_scene, outline or [])
                    prev_func = classify_scene_function(prev_content, prev_purpose)
                except (ImportError, Exception):
                    pass
                if prev_func == "REVEAL":
                    # Flag if current scene suggests instant resolution rather than new obstacle
                    resolution_cues = re.compile(
                        r"\b(softened|forgiven|put (?:it|that) behind (?:us|them)|moved past|"
                        r"made peace|settled (?:the|our|their)|resolved (?:everything|it)|"
                        r"understanding (?:passed|spread)|agreed to (?:let|put)|"
                        r"apologized (?:and|,)|all was (?:forgiven|well)|"
                        r"cleared the air|buried the hatchet)\b",
                        re.IGNORECASE,
                    )
                    if resolution_cues.search(content):
                        all_warnings.append(
                            "CONFLICT_DEFLATION: scene follows REVEAL but contains instant-resolution "
                            "language; reveals should create NEW obstacles, not end conflict"
                        )

        # Opening move (for chapter-openers)
        opening_move = _classify_opening_move(content)
        if sc == 1:
            opening_move_history.append({"chapter": ch, "scene_id": scene_id, "move": opening_move})
            if prev_move and prev_move == opening_move and ch == prev_chapter + 1:
                opening_move_violations.append(
                    f"{scene_id} repeats Ch{prev_chapter} opening type ({opening_move})"
                )
            prev_move = opening_move
            prev_chapter = ch

        contracts.append({
            "scene_id": scene_id,
            "tension_level": tension_level,
            "opening_move": opening_move,
            "scene_function": scene_func,
            "edits": report_edits,
            "warnings": all_warnings,
        })

    # Batch quiet killers: emo_flatline, scene_redundancy (v2), chapter_variety, cross-scene continuity
    try:
        from quality.quiet_killers import (
            check_emo_flatline,
            check_function_redundancy_v2,
            check_chapter_variety,
            check_cross_scene_continuity,
        )
        emo_w = check_emo_flatline(scenes or [])
        red_w = check_function_redundancy_v2(scenes or [], outline or [])
        cross_w = check_cross_scene_continuity(scenes or [])
        # Build chapter dicts with scenes for chapter_variety
        ch_map: Dict[int, list] = {}
        for s in (scenes or []):
            if isinstance(s, dict):
                ch = int(s.get("chapter", 0))
                ch_map.setdefault(ch, []).append(s)
        ch_variety_w = []
        for ch_num, ch_scenes in ch_map.items():
            ch_variety_w.extend(
                check_chapter_variety([{"chapter": ch_num, "scenes": ch_scenes}])
            )
        batch_warnings = emo_w + red_w + cross_w + ch_variety_w
    except (ImportError, Exception):
        batch_warnings = []

    return {
        "contracts": contracts,
        "opening_move_history": opening_move_history,
        "opening_move_violations": opening_move_violations,
        "batch_warnings": batch_warnings,
    }
