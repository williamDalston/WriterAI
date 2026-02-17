"""
Quiet Killers — deterministic checks and transforms for subtle prose quality issues.

Checks (warnings):
1. Continuity tripwires: time/location/object drift without transition
2. Pronoun clarity: he/she soup, consecutive pronoun-only references
3. Stakes articulation: STAKELESS_TENSION when tension high but no stakes
4. Generic verbs: weak-verb overuse
5. Filter phrases: I saw/heard/felt/noticed overuse
6. Emotional temperature monotony: EMO_FLATLINE
7. Too tidy dialogue: no interrupt/dodge/callback
8. Scene purpose redundancy (v1: prefix match; v2: triple-match classifier)
9. Chapter structure variety
10. Final-line punch: SUMMARY/ATMOSPHERE endings
11. Scene function classification: REVEAL/BOND/CONFLICT/DECISION/AFTERMATH/PURSUIT
12. Cross-scene continuity: time flow, character presence, location drift

Transforms (applied):
- Filter removal: "I noticed X" → "X" when redundant
- Weak verb substitution (limited budget)
- Final-line auto-rewrite for SUMMARY/ATMOSPHERE
"""

import re
import random
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("quiet_killers")

# === CONTINUITY TRIPWIRES ===
_TIME_OF_DAY = re.compile(
    r"\b(night|morning|noon|midday|evening|dusk|dawn|midnight|afternoon)\b",
    re.IGNORECASE,
)
_LOCATION_NAMES = re.compile(
    r"\b(kitchen|hallway|bedroom|office|street|car|restaurant|balcony|courtroom|"
    r"bathroom|basement|attic|rooftop|garden|alley|warehouse|dock|bridge|"
    r"hospital|church|library|bar|pub|hotel|lobby|elevator|stairwell|"
    r"garage|park|forest|woods|cabin|apartment|mansion|prison|cell|"
    r"station|airport|harbor|pier|marketplace|arena|stadium|theater|"
    r"classroom|cafeteria|diner|clinic|morgue|chapel|cemetery|"
    r"parking lot|sidewalk|highway|trail|beach|shore|riverbank|cave)\b",
    re.IGNORECASE,
)
_TRANSITION_VERBS = re.compile(
    r"\b(walked|stepped|drove|moved|went|headed|turned|followed|later|minutes later|"
    r"ran|rushed|hurried|traveled|crossed|climbed|descended|entered|left|returned|"
    r"fled|stumbled|sprinted|crept|wandered|rode|sailed|flew|arrived|departed|"
    r"made (?:my|her|his|their|our) way)\b",
    re.IGNORECASE,
)
# Object possession tracking — detect acquire / release / use events
_TRACKABLE_OBJECTS = (
    "glass|cup|mug|phone|keys|letter|book|knife|gun|bag|purse|"
    "bottle|pen|folder|envelope|photo|photograph|cigarette|umbrella|sword"
)
_OBJ_ACQUIRE = re.compile(
    rf"\b(picked up|grabbed|took|clutched|held|carried|snatched|seized|"
    rf"reached for|lifted|caught)\b\s+(?:\w+\s+){{0,3}}\b({_TRACKABLE_OBJECTS})\b|"
    rf"\b({_TRACKABLE_OBJECTS})\b\s+(?:\w+\s+){{0,3}}\b(in (?:my|her|his|their) hand)",
    re.IGNORECASE,
)
_OBJ_RELEASE = re.compile(
    rf"\b(set down|put down|dropped|released|tossed|placed|left|"
    rf"slid|laid|slammed down|threw)\b\s+(?:\w+\s+){{0,3}}\b({_TRACKABLE_OBJECTS})\b|"
    rf"\b({_TRACKABLE_OBJECTS})\b\s+(?:\w+\s+){{0,3}}\b(on the|onto the|down on|aside|away)",
    re.IGNORECASE,
)
_OBJ_USE = re.compile(
    rf"\b(sipped|drank from|checked|read|typed on|scrolled|"
    rf"turned|unlocked with|aimed|fired|opened|flipped through|"
    rf"poured from|stirred|dialed|swung)\b\s+(?:\w+\s+){{0,3}}\b({_TRACKABLE_OBJECTS})\b",
    re.IGNORECASE,
)
_OBJ_NAME_RE = re.compile(rf"^({_TRACKABLE_OBJECTS})$", re.IGNORECASE)

# === STAKES TOKENS ===
_STAKES_PATTERNS = [
    re.compile(r"\b(reputation|reputational)\b", re.IGNORECASE),
    re.compile(r"\b(safety|danger|threat|risk)\b", re.IGNORECASE),
    re.compile(r"\b(freedom|prison|trapped|escape)\b", re.IGNORECASE),
    re.compile(r"\b(money|cost|owe|debt|payment)\b", re.IGNORECASE),
    re.compile(r"\b(relationship|marriage|divorce|family)\b", re.IGNORECASE),
    re.compile(r"\b(identity|who i am|truth about)\b", re.IGNORECASE),
    re.compile(r"\b(future|plans|dreams|hopes)\b", re.IGNORECASE),
]

# === GENERIC WEAK VERBS ===
_WEAK_VERBS = {"turned", "looked", "nodded", "glanced", "shrugged", "sighed"}
_STRONG_ALTERNATIVES = {
    "turned": ["spun", "whirled", "pivoted"],
    "looked": ["stared", "glared", "peered"],
    "nodded": ["dipped his chin", "gave a curt nod"],
    "glanced": ["cut a look", "flicked a glance"],
    "shrugged": ["lifted a shoulder", "shrugged one shoulder"],
    "sighed": ["exhaled", "breathed out"],
}

# === FILTER PHRASES (I + perception verb) ===
_FILTER_PATTERNS = [
    (re.compile(r"^\s*I saw\s+", re.IGNORECASE | re.MULTILINE), "I saw "),
    (re.compile(r"^\s*I heard\s+", re.IGNORECASE | re.MULTILINE), "I heard "),
    (re.compile(r"^\s*I felt\s+", re.IGNORECASE | re.MULTILINE), "I felt "),
    (re.compile(r"^\s*I noticed\s+", re.IGNORECASE | re.MULTILINE), "I noticed "),
    (re.compile(r"^\s*I realized\s+", re.IGNORECASE | re.MULTILINE), "I realized "),
]
# For removal: "I noticed the door was open." → "The door was open."
_FILTER_REMOVAL = [
    (re.compile(r"^\s*I (?:saw|heard|noticed)\s+", re.IGNORECASE | re.MULTILINE), ""),
    (re.compile(r"^\s*I (?:felt|realized)\s+(?:that\s+)?", re.IGNORECASE | re.MULTILINE), ""),
]

# === EMOTIONAL MODES ===
_EMO_KEYWORDS = {
    "defensive_humor": r"\b(joke|laughed|sarcasm|teasing)\b",
    "avoidance": r"\b(change the subject|didn\'t want to talk|deflect)\b",
    "anger": r"\b(angry|furious|yelled|snapped)\b",
    "tenderness": r"\b(soft|gently|touched|held)\b",
    "curiosity": r"\b(wondered|curious|asked)\b",
    "shame": r"\b(ashamed|embarrassed|looked away)\b",
    "relief": r"\b(relief|relaxed|breathed)\b",
    "pride": r"\b(proud|chin up|stood tall)\b",
}

# === FINAL-LINE CLASSIFICATION ===
_ENDING_ACTION = re.compile(
    r"\b(grabbed|walked|turned|closed|opened|pulled|pushed|stood|ran|"
    r"slammed|reached|stepped|drove|left|dropped)\b.*[.!?]$",
    re.IGNORECASE,
)
_ENDING_DIALOGUE = re.compile(r'["\'][^"\']*[.!?]["\']?\s*$', re.MULTILINE)
_ENDING_REVELATION = re.compile(r"\b(knew|understood|realized)\s+", re.IGNORECASE)
_ENDING_SUMMARY = re.compile(
    r"\b(changed|forever|nothing would|everything had|moment that|"
    r"somehow that was enough|for now that was|and that was enough|"
    r"whatever comes next|whatever happened next|whatever tomorrow|"
    r"ready to face|one step at a time|a new beginning|"
    r"something had shifted|something between us|"
    r"the first step toward|for the first time in|"
    r"the world felt different|everything felt different)\b.*[.!?]$",
    re.IGNORECASE,
)
_ENDING_ATMOSPHERE = re.compile(
    r"\b(sun set|rain fell|silence|darkness|light|wind)\b.*[.!?]$",
    re.IGNORECASE,
)

# === SCENE FUNCTION CLASSIFICATION (F2) ===
_SCENE_FUNCTIONS = {
    "REVEAL": re.compile(
        r"\b(secret|discovery|truth|learned|found out|confession|unveil|reveal|"
        r"hidden|uncovered|exposed|admitted|realized the truth)\b",
        re.IGNORECASE,
    ),
    "BOND": re.compile(
        r"\b(connection|intimacy|trust|together|closer|understanding|bond|"
        r"vulnerable|opened up|shared|comfort|embrace|forgive)\b",
        re.IGNORECASE,
    ),
    "CONFLICT": re.compile(
        r"\b(confrontation|argument|opposition|fight|clash|resist|challenge|"
        r"shouted|accused|betrayed|demanded|refused|defied)\b",
        re.IGNORECASE,
    ),
    "DECISION": re.compile(
        r"\b(choice|turning point|commitment|chose|decided|resolve|"
        r"determination|vow|swore|committed|no going back)\b",
        re.IGNORECASE,
    ),
    "AFTERMATH": re.compile(
        r"\b(processing|regrouping|consequences|aftermath|damage|loss|"
        r"wreckage|picking up the pieces|fallout|reckoning|mourning)\b",
        re.IGNORECASE,
    ),
    "PURSUIT": re.compile(
        r"\b(chase|search|journey|hunt|follow|track|pursuit|seek|"
        r"looking for|racing|running toward|escape|fleeing)\b",
        re.IGNORECASE,
    ),
}

# === CROSS-SCENE CONTINUITY (F3) ===
_TIME_ORDER = {
    "dawn": 0, "morning": 1, "noon": 2, "midday": 2,
    "afternoon": 3, "evening": 4, "dusk": 4,
    "night": 5, "midnight": 6,
}
_TIME_SKIP = re.compile(
    r"\b(later|next day|next morning|hours passed|time passed|"
    r"the following|by the time|when .+ woke|days later|that night)\b",
    re.IGNORECASE,
)
_PROPER_NAME = re.compile(r"(?<=[.!?\s])\s*([A-Z][a-z]{2,})")


def _classify_ending(sentence: str) -> str:
    """Classify last sentence as ACTION, DIALOGUE, REVELATION, SUMMARY, ATMOSPHERE."""
    s = sentence.strip()
    if not s:
        return "UNKNOWN"
    if _ENDING_DIALOGUE.search(s[-80:]):
        return "DIALOGUE"
    if _ENDING_ACTION.search(s[-60:]):
        return "ACTION"
    if _ENDING_REVELATION.search(s):
        return "REVELATION"
    if _ENDING_SUMMARY.search(s):
        return "SUMMARY"
    if _ENDING_ATMOSPHERE.search(s):
        return "ATMOSPHERE"
    return "UNKNOWN"


def check_continuity_tripwires(content: str) -> List[str]:
    """Flag time/location/object drift without transition verb."""
    warnings = []
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    prev_time = None
    prev_loc = None

    # Object possession state: object_name -> "HELD" | "RELEASED"
    obj_state: Dict[str, str] = {}

    for i, para in enumerate(paragraphs):
        time_match = _TIME_OF_DAY.search(para)
        loc_match = _LOCATION_NAMES.search(para)
        has_transition = bool(_TRANSITION_VERBS.search(para))

        if time_match and prev_time and time_match.group(1).lower() != prev_time and not has_transition:
            warnings.append(f"CONTINUITY: paragraph {i+1} shifts time ({prev_time} → {time_match.group(1)}) without transition")
        if time_match:
            prev_time = time_match.group(1).lower()

        if loc_match and prev_loc and loc_match.group(1).lower() != prev_loc and not has_transition:
            warnings.append(f"CONTINUITY: paragraph {i+1} shifts location ({prev_loc} → {loc_match.group(1)}) without transition")
        if loc_match:
            prev_loc = loc_match.group(1).lower()

        # Object possession tracking
        _check_object_possession(para, i, obj_state, warnings)

    return warnings


def _extract_object_from_match(match: re.Match) -> Optional[str]:
    """Extract the trackable object name from a regex match."""
    for g in match.groups():
        if g and _OBJ_NAME_RE.match(g):
            return g.lower()
    return None


def _check_object_possession(
    para: str, para_idx: int,
    obj_state: Dict[str, str],
    warnings: List[str],
) -> None:
    """Track object acquire/release/use events and flag contradictions.

    Events are processed in TEXT ORDER (by match position) to avoid false
    positives when a paragraph has "set down X, picked up X, sipped X".

    Flags:
    - POSSESSION_GHOST: object used after being set down (without re-acquiring)
    - POSSESSION_DOUBLE_DROP: object released twice without re-acquiring
    """
    # Collect all events with their text positions
    events: List[Tuple[int, str, str]] = []  # (position, event_type, object)

    for m in _OBJ_ACQUIRE.finditer(para):
        obj = _extract_object_from_match(m)
        if obj:
            events.append((m.start(), "acquire", obj))

    for m in _OBJ_RELEASE.finditer(para):
        obj = _extract_object_from_match(m)
        if obj:
            events.append((m.start(), "release", obj))

    for m in _OBJ_USE.finditer(para):
        obj = _extract_object_from_match(m)
        if obj:
            events.append((m.start(), "use", obj))

    # Process in text order (ascending position)
    events.sort(key=lambda e: e[0])

    for _pos, event_type, obj in events:
        if event_type == "acquire":
            obj_state[obj] = "HELD"
        elif event_type == "release":
            if obj_state.get(obj) == "RELEASED":
                warnings.append(
                    f"POSSESSION_DOUBLE_DROP: paragraph {para_idx + 1} releases "
                    f"'{obj}' that was already set down"
                )
            obj_state[obj] = "RELEASED"
        elif event_type == "use":
            if obj_state.get(obj) == "RELEASED":
                warnings.append(
                    f"POSSESSION_GHOST: paragraph {para_idx + 1} uses '{obj}' "
                    f"that was set down earlier (no re-acquire)"
                )


def check_pronoun_clarity(content: str, same_gender_count: int = 2) -> List[str]:
    """Flag consecutive pronoun-only references without name re-anchor."""
    warnings = []
    max_pronoun_run = 4  # Allow up to 4 "he/she" before needing name
    para_count = 0
    for para in content.split("\n\n"):
        para = para.strip()
        if not para or '"' in para[:50]:  # Skip dialogue-heavy
            continue
        # Count consecutive he/she without proper noun
        runs = re.findall(r"\b(he|she|him|her|his)\b", para, re.IGNORECASE)
        names = re.findall(r"\b[A-Z][a-z]+\b", para)  # Proper nouns
        if len(runs) > max_pronoun_run and len(names) < 2:
            para_count += 1
            if para_count >= 2:
                warnings.append(
                    "PRONOUN_SOUP: 2+ paragraphs with many pronoun references and few name anchors"
                )
                break
    return warnings


def check_stakes_articulation(content: str, tension_level: int) -> List[str]:
    """Flag STAKELESS_TENSION when tension high but no stakes token."""
    if tension_level < 6:
        return []
    for pat in _STAKES_PATTERNS:
        if pat.search(content):
            return []
    return ["STAKELESS_TENSION: high-tension scene has no concrete stakes (reputation, safety, relationship, etc.)"]


def check_generic_verbs(content: str) -> List[str]:
    """Flag weak-verb overuse."""
    words = content.lower().split()
    counts = {}
    for w in _WEAK_VERBS:
        counts[w] = words.count(w)
    total_weak = sum(counts.values())
    if total_weak > 6:
        top = sorted(counts.items(), key=lambda x: -x[1])[:2]
        return [f"WEAK_VERBS: overuse of generic verbs ({top[0][0]} x{top[0][1]}, etc.)"]
    return []


def check_filter_overuse(content: str) -> List[str]:
    """Flag sentences starting with I + perception verb too often."""
    sentences = re.split(r"[.!?]+", content)
    filter_starts = sum(
        1 for s in sentences
        if re.match(r"^\s*I\s+(saw|heard|felt|noticed|realized)\s+", s, re.IGNORECASE)
    )
    if filter_starts > 3:
        return ["FILTER_OVERUSE: too many sentences starting with I saw/heard/felt/noticed"]
    return []


def check_emo_flatline(scenes: List[Dict]) -> List[str]:
    """Flag chapter with 5+ scenes in same emotional mode."""
    mode_counts: Dict[str, List[int]] = {}  # mode -> [scene indices]
    for idx, scene in enumerate(scenes or []):
        content = (scene.get("content") or "").lower()
        best_mode = None
        best_count = 0
        for mode, pat_str in _EMO_KEYWORDS.items():
            count = len(re.findall(pat_str, content, re.IGNORECASE))
            if count > best_count:
                best_count = count
                best_mode = mode
        if best_mode:
            mode_counts.setdefault(best_mode, []).append(idx)
    for mode, indices in mode_counts.items():
        # Check for 5+ consecutive
        indices.sort()
        run = 1
        for i in range(1, len(indices)):
            if indices[i] == indices[i - 1] + 1:
                run += 1
                if run >= 5:
                    return [f"EMO_FLATLINE: 5+ consecutive scenes dominated by {mode}"]
            else:
                run = 1
    return []


def check_dialogue_tidy(content: str, tension_level: int) -> List[str]:
    """Flag high-tension dialogue with no interrupt/dodge/callback."""
    if tension_level < 6:
        return []
    lines = re.findall(r'"([^"]+)"', content)
    if len(lines) < 4:
        return []
    has_interrupt = any(re.search(r"\b(Wait|No|Stop|What)\s*[.!?]", l) for l in lines)
    has_dodge = any(
        re.search(r"\b(I don'?t|doesn'?t matter|none of your|not your|changed? the subject)\b", l, re.IGNORECASE)
        for l in lines
    )
    warnings = []
    if not has_interrupt and not has_dodge:
        warnings.append(
            "DIALOGUE_TIDY: high-tension dialogue lacks interruption or dodge "
            "(Wait./No./Stop./I don't.../changed the subject)"
        )
    return warnings


def check_scene_function_redundancy(scenes: List[Dict], outline: List[Dict]) -> List[str]:
    """Flag adjacent scenes with same function + emotional mode."""
    # Simplified: compare purpose/outcome
    prev_purpose = None
    prev_chapter = None
    for idx, scene in enumerate(scenes or []):
        ch = scene.get("chapter", 0)
        # Get scene purpose from outline
        purpose = ""
        for chap in (outline or []):
            if int(chap.get("chapter", 0)) == int(ch):
                for sc in chap.get("scenes", []):
                    outline_sc = sc.get("scene", sc.get("scene_number"))
                    pip_sc = scene.get("scene_number", scene.get("scene"))
                    if outline_sc == pip_sc or int(outline_sc or 0) == int(pip_sc or 0):
                        purpose = (sc.get("purpose") or "")[:50]
                        break
        if purpose and prev_purpose and ch == prev_chapter:
            if purpose.lower()[:30] == prev_purpose.lower()[:30]:
                return [f"SCENE_REDUNDANCY: scene {idx} has similar purpose to previous"]
        prev_purpose = purpose
        prev_chapter = ch
    return []


def check_chapter_variety(chapters: List[Dict]) -> List[str]:
    """Flag chapter lacking short/sharp, slow/sensory, dialogue-heavy mix."""
    for ch_data in chapters or []:
        scenes = ch_data.get("scenes", [])
        if len(scenes) < 2:
            continue
        has_short = False
        has_sensory = False
        has_dialogue = False
        for s in scenes:
            content = s.get("content", "")
            wc = len(content.split())
            if wc < 400:
                has_short = True
            if content.count('"') >= 8:
                has_dialogue = True
            if re.search(r"\b(smell|scent|texture|warm|cold|soft)\b", content, re.IGNORECASE):
                has_sensory = True
        if not (has_short or has_sensory or has_dialogue):
            return ["CHAPTER_VARIETY: chapter lacks short/sharp, sensory, or dialogue-heavy scene"]
    return []


# === F2: SCENE FUNCTION CLASSIFIER ===


def classify_scene_function(content: str, purpose: str = "") -> str:
    """Classify scene's narrative function via keyword heuristics.

    Returns one of: REVEAL, BOND, CONFLICT, DECISION, AFTERMATH, PURSUIT, MIXED.
    Purpose text gets 3x weight (concentrated description).
    """
    scores: Dict[str, int] = {}
    content_lower = content.lower()
    purpose_lower = purpose.lower()
    for func, pattern in _SCENE_FUNCTIONS.items():
        content_hits = len(pattern.findall(content_lower))
        purpose_hits = len(pattern.findall(purpose_lower)) * 3
        scores[func] = content_hits + purpose_hits

    if not any(scores.values()):
        return "MIXED"

    top_func = max(scores, key=scores.get)
    top_score = scores[top_func]
    if top_score == 0:
        return "MIXED"

    # Check for near-ties (within 1 hit)
    runners_up = [f for f, s in scores.items() if f != top_func and s >= top_score - 1 and s > 0]
    if runners_up:
        return "MIXED"

    return top_func


def _get_purpose_from_outline(scene: Dict, outline: List[Dict]) -> str:
    """Extract purpose string from outline matching scene's chapter/scene_number."""
    ch = scene.get("chapter", 0)
    for chap in (outline or []):
        if int(chap.get("chapter", 0)) == int(ch):
            for sc in chap.get("scenes", []):
                outline_sc = sc.get("scene", sc.get("scene_number"))
                pip_sc = scene.get("scene_number", scene.get("scene"))
                if outline_sc == pip_sc or int(outline_sc or 0) == int(pip_sc or 0):
                    return sc.get("purpose") or ""
    return ""


def _classify_dominant_emo_mode(content: str) -> Optional[str]:
    """Classify dominant emotional mode using _EMO_KEYWORDS."""
    best_mode = None
    best_count = 0
    content_lower = content.lower()
    for mode, pat_str in _EMO_KEYWORDS.items():
        count = len(re.findall(pat_str, content_lower, re.IGNORECASE))
        if count > best_count:
            best_count = count
            best_mode = mode
    return best_mode


def _get_last_paragraph(content: str) -> str:
    """Return last non-empty paragraph."""
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    return paragraphs[-1] if paragraphs else ""


def check_function_redundancy_v2(scenes: List[Dict], outline: List[Dict]) -> List[str]:
    """Flag adjacent scenes with SAME function + SAME emotional mode + SAME ending type.

    Triple match = genuine redundancy (avoids false positives from single-axis match).
    Replaces the simpler check_scene_function_redundancy (prefix match only).
    """
    warnings = []
    prev_func = None
    prev_emo = None
    prev_ending = None
    prev_chapter = None

    for idx, scene in enumerate(scenes or []):
        if not isinstance(scene, dict):
            continue
        content = scene.get("content", "")
        ch = scene.get("chapter", 0)

        purpose = _get_purpose_from_outline(scene, outline)
        func = classify_scene_function(content, purpose)
        emo = _classify_dominant_emo_mode(content)
        last_para = _get_last_paragraph(content)
        ending = _classify_ending(last_para) if last_para else "UNKNOWN"

        if (ch == prev_chapter and
                func == prev_func and func != "MIXED" and
                emo == prev_emo and emo is not None and
                ending == prev_ending):
            scene_id = scene.get("scene_id", f"scene_{idx}")
            warnings.append(
                f"FUNCTION_REDUNDANCY: {scene_id} matches previous scene "
                f"(function={func}, emo={emo}, ending={ending})"
            )

        prev_func = func
        prev_emo = emo
        prev_ending = ending
        prev_chapter = ch

    return warnings


# === F3: CROSS-SCENE CONTINUITY TRIPWIRES ===


def _check_time_flow(ch_num: int, ch_scenes: List[Tuple[int, Dict]]) -> List[str]:
    """Flag impossible backwards time jumps in same chapter without time skip."""
    warnings = []
    prev_time_val = -1
    prev_time_label = None

    for idx, scene in ch_scenes:
        content = scene.get("content", "")
        times = _TIME_OF_DAY.findall(content)
        has_time_skip = bool(_TIME_SKIP.search(content))

        if times:
            last_time = times[-1].lower()
            time_val = _TIME_ORDER.get(last_time, -1)

            if (prev_time_val >= 0 and time_val >= 0 and
                    time_val < prev_time_val and not has_time_skip):
                scene_id = scene.get("scene_id", f"scene_{idx}")
                warnings.append(
                    f"CROSS_CONTINUITY_TIME: ch{ch_num} {scene_id} jumps backwards "
                    f"({prev_time_label} -> {last_time}) without time skip"
                )

            prev_time_val = time_val
            prev_time_label = last_time

    return warnings


def _check_character_presence(ch_num: int, ch_scenes: List[Tuple[int, Dict]]) -> List[str]:
    """Flag characters appearing in scene N+1 who weren't in scene N."""
    warnings = []
    prev_names: Optional[set] = None

    for i, (idx, scene) in enumerate(ch_scenes):
        content = scene.get("content", "")
        all_names = set()
        for para in content.split("\n\n"):
            trimmed = para.strip()
            if not trimmed:
                continue
            found = _PROPER_NAME.findall(trimmed)
            all_names.update(n.lower() for n in found if len(n) >= 3)

        # Also add names from scene metadata
        scene_chars = scene.get("characters", [])
        if isinstance(scene_chars, list):
            for c in scene_chars:
                if isinstance(c, str) and len(c) >= 3:
                    all_names.add(c.lower().split()[0])

        if prev_names is not None and i > 0:
            new_names = all_names - prev_names
            for name in new_names:
                count = content.lower().count(name)
                if count >= 3:
                    scene_id = scene.get("scene_id", f"scene_{idx}")
                    warnings.append(
                        f"CROSS_CONTINUITY_CHAR: ch{ch_num} {scene_id} introduces "
                        f"'{name}' (x{count}) without presence in previous scene"
                    )

        prev_names = all_names

    return warnings


def _check_location_drift(ch_num: int, ch_scenes: List[Tuple[int, Dict]]) -> List[str]:
    """Flag adjacent scenes in same chapter with different locations but no transition."""
    warnings = []
    prev_location = None

    for idx, scene in ch_scenes:
        content = scene.get("content", "")
        location = (scene.get("location") or "").lower().strip()

        if not location:
            matches = _LOCATION_NAMES.findall(content)
            if matches:
                location = matches[0].lower()

        has_transition = bool(_TRANSITION_VERBS.search(content[:500]))

        if (location and prev_location and
                location != prev_location and
                not has_transition):
            scene_id = scene.get("scene_id", f"scene_{idx}")
            warnings.append(
                f"CROSS_CONTINUITY_LOC: ch{ch_num} {scene_id} shifts location "
                f"({prev_location} -> {location}) without transition verb"
            )

        if location:
            prev_location = location

    return warnings


def _extract_end_of_scene_objects(content: str) -> Dict[str, str]:
    """Extract object possession state at end of scene.

    Returns dict of {object_name: "HELD"|"RELEASED"}.
    Events processed in TEXT ORDER per paragraph (same logic as
    _check_object_possession) to avoid acquire/release ordering bugs.
    """
    state: Dict[str, str] = {}
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    for para in paragraphs:
        events: List[Tuple[int, str, str]] = []
        for m in _OBJ_ACQUIRE.finditer(para):
            obj = _extract_object_from_match(m)
            if obj:
                events.append((m.start(), "acquire", obj))
        for m in _OBJ_RELEASE.finditer(para):
            obj = _extract_object_from_match(m)
            if obj:
                events.append((m.start(), "release", obj))
        events.sort(key=lambda e: e[0])
        for _pos, event_type, obj in events:
            state[obj] = "HELD" if event_type == "acquire" else "RELEASED"
    return state


def _check_object_continuity(ch_num: int, ch_scenes: List[Tuple[int, Dict]]) -> List[str]:
    """Flag cross-scene object possession contradictions within a chapter.

    If scene N ends with an object RELEASED, and scene N+1 uses that object
    without re-acquiring it, flag as CROSS_POSSESSION_GHOST.
    """
    warnings = []
    prev_state: Dict[str, str] = {}

    for idx, scene in ch_scenes:
        content = scene.get("content", "")
        if not content:
            continue

        # Check: does this scene USE objects that previous scene RELEASED?
        for m in _OBJ_USE.finditer(content):
            obj = _extract_object_from_match(m)
            if obj and prev_state.get(obj) == "RELEASED":
                # Check if this scene re-acquires the object before using it
                first_use_pos = m.start()
                pre_text = content[:first_use_pos]
                reacquired = False
                for acq_m in _OBJ_ACQUIRE.finditer(pre_text):
                    acq_obj = _extract_object_from_match(acq_m)
                    if acq_obj == obj:
                        reacquired = True
                        break
                if not reacquired:
                    scene_id = scene.get("scene_id", f"scene_{idx}")
                    warnings.append(
                        f"CROSS_POSSESSION_GHOST: ch{ch_num} {scene_id} uses "
                        f"'{obj}' that was set down in previous scene"
                    )

        # Update state for next scene
        prev_state = _extract_end_of_scene_objects(content)

    return warnings


def check_cross_scene_continuity(scenes: List[Dict]) -> List[str]:
    """Cross-scene continuity checks within each chapter.

    Checks:
    1. Time-of-day flow: flag backwards jumps without time skip
    2. Character presence: flag character appearing without prior introduction
    3. Location drift: flag location change without transition verb
    4. Object possession: flag objects used after being released in prior scene

    Returns list of warning strings. Non-blocking.
    """
    warnings = []

    # Group scenes by chapter
    chapters: Dict[int, List[Tuple[int, Dict]]] = {}
    for idx, scene in enumerate(scenes or []):
        if not isinstance(scene, dict):
            continue
        ch = int(scene.get("chapter", 0))
        chapters.setdefault(ch, []).append((idx, scene))

    for ch_num, ch_scenes in sorted(chapters.items()):
        if len(ch_scenes) < 2:
            continue
        warnings.extend(_check_time_flow(ch_num, ch_scenes))
        warnings.extend(_check_character_presence(ch_num, ch_scenes))
        warnings.extend(_check_location_drift(ch_num, ch_scenes))
        warnings.extend(_check_object_continuity(ch_num, ch_scenes))

    return warnings


def apply_filter_removal(text: str, max_edits: int = 5) -> str:
    """Convert 'I noticed X' → 'X' when redundant. Limited budget."""
    edits = 0
    replacements = [
        (re.compile(r"\bI noticed (?:that )?", re.IGNORECASE), ""),
        (re.compile(r"\bI saw (?:that )?", re.IGNORECASE), ""),
        (re.compile(r"\bI heard (?:that )?", re.IGNORECASE), ""),
        (re.compile(r"\bI felt (?:that )?", re.IGNORECASE), ""),
        (re.compile(r"\bI realized (?:that )?", re.IGNORECASE), ""),
    ]
    for pattern, repl in replacements:
        if edits >= max_edits:
            break
        new_text, n = pattern.subn(repl, text, count=1)  # One per pattern type
        if n > 0:
            text = new_text
            edits += 1
    return text


def apply_weak_verb_substitution(text: str, budget: int = 3) -> str:
    """Replace up to `budget` weak verbs with stronger alternatives."""
    result = text
    edits = 0
    for weak, alts in _STRONG_ALTERNATIVES.items():
        if edits >= budget:
            break
        pat = re.compile(r"\b" + weak + r"\b", re.IGNORECASE)
        matches = list(pat.finditer(result))
        if len(matches) >= 2 and edits < budget:
            # Replace one occurrence
            pick = random.randint(0, len(matches) - 1)
            m = matches[pick]
            alt = random.choice(alts)
            result = result[: m.start()] + alt + result[m.end() :]
            edits += 1
    return result


def apply_final_line_rewrite(content: str) -> str:
    """If last sentence is SUMMARY or ATMOSPHERE, replace with action-based ending."""
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    if len(paragraphs) < 2:
        return content
    last = paragraphs[-1]
    sentences = re.split(r"([.!?]\s+)", last)
    if not sentences:
        return content
    if len(sentences) < 2:
        last_sent = sentences[0]
    else:
        last_sent = sentences[-2] + sentences[-1]
    classification = _classify_ending(last_sent)
    if classification not in ("SUMMARY", "ATMOSPHERE"):
        return content
    # POV-agnostic action endings (work in any person)
    action_endings = [
        "The door clicked shut.",
        "Silence filled the room.",
        "Outside, the wind picked up.",
        "A light went out down the hall.",
        "The clock on the wall ticked once, twice.",
        "Somewhere, a door slammed.",
        "Rain began to fall.",
        "The last ember died in the grate.",
    ]
    new_ending = random.choice(action_endings)
    kept = "\n\n".join(paragraphs[:-1])
    return kept + "\n\n" + new_ending


# === THERAPY-SPEAK CHECKER ===

_THERAPY_PATTERNS = [
    re.compile(r'\bi appreciate you sharing\b', re.IGNORECASE),
    re.compile(r"\bi hear what you'?re saying\b", re.IGNORECASE),
    re.compile(r'\bthat must be (?:really |so )?hard\b', re.IGNORECASE),
    re.compile(r'\bi need you to understand\b', re.IGNORECASE),
    re.compile(r'\bi want to be honest with you\b', re.IGNORECASE),
    re.compile(r'\bthank you for being vulnerable\b', re.IGNORECASE),
    re.compile(r"\bi'?m processing\b", re.IGNORECASE),
    re.compile(r'\bwe should talk about what happened\b', re.IGNORECASE),
    re.compile(r'\bi want you to know that i\b', re.IGNORECASE),
    re.compile(r"\bit'?s okay to feel\b", re.IGNORECASE),
]


def check_therapy_speak(content: str) -> List[str]:
    """Flag dialogue that sounds like a therapy session rather than natural conversation.

    Returns list of warning strings. Non-blocking (quality warning only).
    """
    warnings = []
    hits = []
    for pat in _THERAPY_PATTERNS:
        matches = pat.findall(content)
        if matches:
            hits.extend(matches)

    if len(hits) >= 2:
        examples = hits[:3]
        warnings.append(
            f"THERAPY_SPEAK: {len(hits)} instances of therapeutic dialogue "
            f"(e.g., {', '.join(repr(h) for h in examples)}). "
            f"Characters should express emotion through behavior, not clinical language."
        )
    return warnings
