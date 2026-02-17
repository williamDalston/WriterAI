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
8. Scene purpose redundancy
9. Chapter structure variety
10. Final-line punch: SUMMARY/ATMOSPHERE endings

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
    r"\b(kitchen|hallway|bedroom|office|street|car|restaurant|balcony|courtroom)\b",
    re.IGNORECASE,
)
_TRANSITION_VERBS = re.compile(
    r"\b(walked|stepped|drove|moved|went|headed|turned|followed|later|minutes later)\b",
    re.IGNORECASE,
)
_OBJECT_HAND = re.compile(
    r"\b(glass|cup|phone|keys|letter|book)\s+(in my hand|in her hand|in his hand)\b|"
    r"\b(set down|put down|picked up|grabbed|released)\b",
    re.IGNORECASE,
)

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
_ENDING_ACTION = re.compile(r"\b(grabbed|walked|turned|closed|opened|said|asked)\b.*[.!?]$", re.IGNORECASE)
_ENDING_DIALOGUE = re.compile(r'["\'][^"\']*[.!?]["\']?\s*$', re.MULTILINE)
_ENDING_REVELATION = re.compile(r"\b(knew|understood|realized)\s+", re.IGNORECASE)
_ENDING_SUMMARY = re.compile(
    r"\b(changed|forever|nothing would|everything had|moment that)\b.*[.!?]$",
    re.IGNORECASE,
)
_ENDING_ATMOSPHERE = re.compile(
    r"\b(sun set|rain fell|silence|darkness|light|wind)\b.*[.!?]$",
    re.IGNORECASE,
)


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
    prev_obj = None

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

    return warnings


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
    has_interrupt = any(re.search(r"\b(Wait\.|No\.|Stop\.|What\?)\b", l) for l in lines)
    has_dodge = any("" in l or "I don't" in l for l in lines)  # Simplified
    if not has_interrupt:
        return ["DIALOGUE_TIDY: high-tension dialogue lacks interruption (Wait./No./Stop.)"]
    return []


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
                    if sc.get("scene") == scene.get("scene_number"):
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
    last_sent = sentences[-2] + (sentences[-1] if len(sentences) > 1 else "")
    classification = _classify_ending(last_sent)
    if classification not in ("SUMMARY", "ATMOSPHERE"):
        return content
    # Simple fix: use a generic action ending from prior context
    action_endings = [
        "She turned away.",
        "He left the room.",
        "I didn't look back.",
        "The door closed behind him.",
    ]
    new_ending = random.choice(action_endings)
    kept = "\n\n".join(paragraphs[:-1])
    return kept + "\n\n" + new_ending
