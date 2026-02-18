"""Editorial cleanup — deterministic fixes for common manuscript artifacts.

P0 (Critical):
1. Preamble meta-text: Strip "X found herself/himself in the..." (24 hits).
2. Grounding insert artifacts: Strip repeated sensory sentences.
3. POV pronoun confusion: Fix "my" → "her" on other characters.
4. Elena hallucination: Remove Ch4 phantom character passage.

P1 (High):
5. Marco's wedding ring, Enzo line, timeline, "leaving it slightly mussed", "between us like".
6. New grounding: "Glass clinked...", "floorboards creaked...", "Ice shifted...".

P2 (Medium):
7. Double periods (".." → ".").
8. Filter words: "I could feel" → "I felt"; strip "I could see/hear" hedges.

All edits are deterministic — no LLM, no voice drift.
"""

import logging
import re
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("editorial_cleanup")

# Exact grounding sentences to strip (also match inline, not just paragraphs)
_GROUNDING_STRIP = [
    r"I reached for something solid and grabbed the edge of the table\.\s*",
    r"I reached for the glass and turned it slowly\.\s*",
    r"I stood and crossed to the railing\.\s*",
    r"I sat straighter and reached for the nearest solid thing\.\s*",
    r"I pushed the hair from my face and sat straighter\.\s*",
    r"I grabbed the fabric of my sleeve and twisted\.\s*",
    r"I turned my hands over, studying the lines\.\s*",
    r"I grabbed the nearest solid thing and held on\.\s*",
    r"I turned the ring on my finger without thinking\.\s*",
    r"I stepped back and shoved my hands into my pockets\.\s*",
    r"I sat with my spine against the wall, counting breaths\.\s*",
    r"I stood, walked two steps, and sat back down\.\s*",
    # Variants that appear in the manuscript
    r"My jaw clenched as I grabbed the edge of the table\.\s*",
    r"My jaw clenched as I gripped the edge of the table\.\s*",
    r"My jaw clenches as I grab the edge of the table\.\s*",
    r"My jaw clenches as I grip the edge of the table\.\s*",
    r"My knuckles crack as I grip the edge of the table\.\s*",
    r"I pressed my temple with my fingertips, finding the edge of the table for support\.\s*",
    r"I pressed my temple and turned slowly\.\s*",
    r"I pressed my temple against the cool stone wall\.\s*",
    r"I pressed my hand flat to keep the runner from sliding and let the question land where it would\.\s*",  # only if orphaned/mechanical
]
# Simpler: strip as standalone paragraphs (between \n\n)
_GROUNDING_PARAGRAPHS = [
    "I reached for something solid and grabbed the edge of the table.",
    "I reached for the glass and turned it slowly.",
    "I stood and crossed to the railing.",
    "I sat straighter and reached for the nearest solid thing.",
    "I pushed the hair from my face and sat straighter.",
    "I grabbed the fabric of my sleeve and twisted.",
    "I turned my hands over, studying the lines.",
    "I grabbed the nearest solid thing and held on.",
    "I turned the ring on my finger without thinking.",
    "I stepped back and shoved my hands into my pockets.",
    "I sat with my spine against the wall, counting breaths.",
    "I stood, walked two steps, and sat back down.",
    "My jaw clenched as I grabbed the edge of the table.",
    "My jaw clenched as I gripped the edge of the table.",
    "My jaw clenches as I grab the edge of the table.",
    "My jaw clenches as I grip the edge of the table.",
    "My knuckles crack as I grip the edge of the table.",
    "I pressed my temple with my fingertips, finding the edge of the table for support.",
    "I pressed my temple and turned slowly.",
    # Scorecard: additional variants
    "I grabbed the edge of the table.",
    "I gripped the edge of the table.",
    "Silence filled the room.",
    # P1 additional grounding (other LLM audit)
    "Glass clinked against the table.",
    "The floorboards creaked under shifting weight.",
    "Ice shifted in a glass no one was drinking.",
]


# Preamble meta-text: "Lena Castillo found herself in the...", "Lena found herself in the..."
_PREAMBLE_PATTERN = re.compile(
    r"^[A-Za-z]+(?:\s+[A-Za-z]+)?\s+found\s+(?:her|him)self\s+in\s+(?:the\s+)?[^.]+\.[ \t]*",
    re.IGNORECASE,
)
_PREAMBLE_I_PATTERN = re.compile(
    r"^I\s+found\s+myself\s+in\s+(?:the\s+)?[^.]+\.[ \t]*",
    re.IGNORECASE,
)

# Double periods: .. -> .
_DOUBLE_PERIOD_PATTERN = re.compile(r"\.\.")

# Filter words: I could feel → I felt; strip I could see/hear
_FILTER_FEEL = re.compile(r"\bI could feel\b", re.IGNORECASE)
_FILTER_SEE = re.compile(r"\bI could see\b", re.IGNORECASE)
_FILTER_HEAR = re.compile(r"\bI could hear\b", re.IGNORECASE)


def _strip_grounding_inline(text: str, phrases: List[str]) -> Tuple[str, int]:
    """Remove grounding phrases when they appear inline (mid-paragraph)."""
    removed = 0
    result = text
    for phrase in phrases:
        for before in (r"\.\s+", r"\n\n", r"\n"):
            for after in (r"\s+", r"\n\n", r"\n"):
                pattern = f"({before})({re.escape(phrase)})({after})"
                new_result, n = re.subn(pattern, r"\1\3", result)
                if n > 0:
                    result = new_result
                    removed += n
    return result, removed


# POV pronoun: "my" → "her" when describing another female character's body/voice
# Be conservative: only replace when clearly wrong (verb implies subject's own body)
_POV_FIXES = [
    # cleared my throat → her (the clearer is clearing their own throat)
    (r"(\b(?:She|He|Gianna|Sofia|Elena|Aunt\s+Luisa|The\s+woman|Someone)\b[^.]*?)cleared my throat", r"\1cleared her throat"),
    (r"cleared my throat", r"cleared her throat"),
    # narrows my eyes → her
    (r"narrows my eyes", r"narrows her eyes"),
    (r"narrowed my eyes", r"narrowed her eyes"),
    # , my face flushed (other's face)
    (r"([^.]{10,}?(?:She|Sofia|Gianna|Elena)\b[^.]*?), my face flushed", r"\1, her face flushed"),
    (r", my face flushed", r", her face flushed"),
    # between my palms → her (when other character does the action)
    (r"rolled it between my palms", r"rolled it between her palms"),
    # my voice (other speaking) — "She leans forward, my voice" → "her voice"
    (r", my voice taking", r", her voice taking"),
    (r", my voice carries", r", her voice carries"),
    # "My voice cuts through" when Elena — preceded by Elena context
    (r"My voice cuts through the market noise like it always did", r"Her voice cuts through the market noise like it always did"),
    # my collarbone
    (r"straightened until my collarbone showed", r"straightened until her collarbone showed"),
    # My eyes find mine (Sofia) → Her eyes
    (r"My eyes find mine through dark lashes", r"Her eyes find mine through dark lashes"),
    # places my hand → places her hand
    (r"She places my hand on", r"She places her hand on"),
    (r"Gianna places my hand", r"Gianna places her hand"),
    # I look up into my eyes → her eyes (Elena)
    (r"I look up into my eyes", r"I look up into her eyes"),
    # my hair is shorter (Elena's hair), my eyes look (Elena's eyes)
    (r"my hair is shorter now, cut in a way that frames her face and makes my eyes look", r"her hair is shorter now, cut in a way that frames her face and makes her eyes look"),
    # my fingers brushing mine (Elena's fingers brushing Lena's)
    (r"my fingers brushing mine as we reach", r"her fingers brushing mine as we reach"),
    # She doesn't look away from my face (Elena looking at Lena — actually "my" = Lena's face, so that could be correct. But "she doesn't look away from my face" - if "she" is Elena, she's looking at Lena's face, so "my" is correct. Skip.)
    # My voice carries absolute certainty (Sofia)
    # "My voice" at sentence start when it's another character speaking
    (r"My voice carries absolute certainty", r"Her voice carries absolute certainty"),
    # fingers at my hips - could be "her hands at my hips" (Sofia's hands at Lena's hips) - "my hips" = Lena's, correct. "hands at my hips" - Her hands at my hips.
    (r"hands at my hips, fingers splayed", r"hands at my hips, fingers splayed"),  # no change - my hips = Lena's
    (r"My voice stops me at the threshold", r"Her voice stops me at the threshold"),
    (r"My voice drops to that gentle tone", r"Her voice drops to that gentle tone"),
    (r"My voice cut through the whispers", r"Her voice cut through the whispers"),
    (r"My voice carries over the crowd", r"Her voice carries over the crowd"),
    # Additional from full scan
    (r"Sofia said, his voice all honey", r"Sofia said, her voice all honey"),
    (r"Sofia said, his voice all honey over broken glass", r"Sofia said, her voice all honey over broken glass"),
    (r"so my chin nearly brushed", r"so her chin nearly brushed"),
    (r"She dropped my voice", r"She dropped her voice"),
    (r"the gold cross at my throat", r"the gold cross at her throat"),
    (r"My fingers twist the strap of her purse", r"Her fingers twist the strap of her purse"),
    (r"flicker across my face", r"flicker across her face"),
    (r"my fingers soft but insistent", r"her fingers soft but insistent"),
    (r"My voice carries that thread of panic", r"Her voice carries that thread of panic"),
    (r"My voice drops to a whisper", r"Her voice drops to a whisper"),
    (r"My fingers crumpled the paper", r"Her fingers crumpled the paper"),
    (r"My voice went deadly quiet", r"Her voice went deadly quiet"),
    (r"My fingers found my wrist", r"Her fingers found my wrist"),
    (r"My eyes find mine", r"Her eyes find mine"),
    (r"my fingers tapping the napkin", r"her fingers tapping the napkin"),
    (r"My voice drops to something almost private", r"Her voice drops to something almost private"),
    (r"until my collarbone showed", r"until her collarbone showed"),
    # a woman snapped, his voice → her voice
    (r"a woman in the third pew snapped, his voice", r"a woman in the third pew snapped, her voice"),
    # Gianna speaking: "This rearranges the family." My voice → Her voice
    (r"\"This rearranges the family.\" My voice cuts through the morning air", r'"This rearranges the family." Her voice cuts through the morning air'),
]

# Compile POV regexes
_POV_PATTERNS = [(re.compile(p), r) for p, r in _POV_FIXES]

# Marco's wedding ring — he's best man, not groom
_MARCO_RING_FIXES = [
    (r"His wedding ring caught the light", r"His signet ring caught the light"),
    (r"Marco's wedding ring catches the light", r"Marco's signet ring catches the light"),
]

# Timeline consistency
_TIMELINE_FIXES = [
    (r"four years ago", r"three years ago"),
    (r"five years ago", r"three years ago"),
]

# Enzo identity confusion — romantic line that should be Marco (Enzo is friend/ally, not romantic)
_ENZO_FIXES = [
    (r'"I\'ve been waiting three years for someone to write me a note like that\.?"', r'"That\'s the kind of note that changes everything."'),
    # Truncated: "Then you should know," he whispered, "I've been waiting three years for someone to..."
    (r'"Then you should know," he whispered, "I\'ve been waiting three years for someone to\.\.\."', r'"Then you should know," he said, "you\'re braver than you think."'),
]

# "leaving it slightly mussed" — vary (replace with alternatives)
_MUSSED_FIXES = [
    (r"leaving it slightly mussed", r"leaving it ruffled"),
]

# "between us like [simile]" — diversify
_BETWEEN_US_ALTERNATIVES = [
    (r"between us like an unexploded mine", r"between us, heavy and unspoken"),
    (r"between us like an accusation", r"between us, sharp enough to cut"),
    (r"between us like a dare", r"between us, bold and waiting"),
    (r"between us like a blade", r"between us, cold and precise"),
    (r"between us like a battlefield map", r"between us, marked with old trenches"),
    (r"between us like smoke", r"between us, obscuring what we mean"),
    (r"between us like evidence", r"between us, undeniable"),
    (r"between us like stones", r"between us, weighted and silent"),
]

# Elena hallucination: phrase that starts the block to remove (through end of scene beat)
_ELENA_START = "Then she steps into my line of sight, and the air thins."
_ELENA_END_PHRASE = "like a bridge I'm terrified to cross."
# Fallback: remove from "Then she steps" to "terrified to cross" inclusive
_ELENA_PATTERN = re.compile(
    r"\n\nThen she steps into my line of sight[^.]+?Elena[^.]+?terrified to cross\.\s*",
    re.DOTALL,
)
# Simpler: remove the entire block as a string span
_ELENA_ALT_START = "Then she steps into my line of sight"
_ELENA_ALT_END = "I look up into Elena's eyes, still crouched here among the scattered sweets, and the confession hangs between us like a bridge I'm terrified to cross."


# Regex to strip sentences containing grounding phrases (catches embedded cases)
_GROUNDING_SENTENCE_PATTERNS = [
    re.compile(r"[.!?]\s*(I reached for something solid and grabbed the edge of the table\.?)\s+", re.IGNORECASE),
    re.compile(r"[.!?]\s*(I grabbed the edge of the table\.?)\s+", re.IGNORECASE),
    re.compile(r"[.!?]\s*(I gripped the edge of the table\.?)\s+", re.IGNORECASE),
    re.compile(r"[.!?]\s*(I reached for the glass and turned it slowly\.?)\s+", re.IGNORECASE),
    re.compile(r"[.!?]\s*(I stood and crossed to the railing\.?)\s+", re.IGNORECASE),
    re.compile(r"[.!?]\s*(My jaw clenched as I grabbed the edge of the table\.?)\s+", re.IGNORECASE),
    re.compile(r"[.!?]\s*(My jaw clenched as I gripped the edge of the table\.?)\s+", re.IGNORECASE),
    re.compile(r"[.!?]\s*(My knuckles crack as I grip the edge of the table\.?)\s+", re.IGNORECASE),
    re.compile(r"[.!?]\s*(Silence filled the room\.?)\s+", re.IGNORECASE),
]


def strip_grounding_artifacts(text: str) -> Tuple[str, int]:
    """Remove grounding insert sentences. Returns (modified_text, count_removed)."""
    if not text or not text.strip():
        return text, 0
    removed = 0
    result = text
    # First: strip sentence patterns (catches embedded)
    for pattern in _GROUNDING_SENTENCE_PATTERNS:
        new_result, n = pattern.subn(r". ", result)
        if n > 0:
            result = new_result
            removed += n
    for phrase in _GROUNDING_PARAGRAPHS:
        # Remove as full paragraph (surrounded by \n\n or at start/end)
        patterns = [
            "\n\n" + phrase + "\n\n",
            "\n\n" + phrase + "\n",
            "\n" + phrase + "\n\n",
            "\n" + phrase + "\n",
        ]
        for p in patterns:
            prev_len = len(result)
            result = result.replace(p, "\n\n")
            if len(result) < prev_len:
                removed += 1
        # Also at start
        if result.startswith(phrase + "\n\n"):
            result = result[len(phrase) + 2 :]
            removed += 1
        if result.startswith(phrase + "\n"):
            result = result[len(phrase) + 1 :]
            removed += 1
        # At end
        if result.endswith("\n\n" + phrase):
            result = result[: -(len(phrase) + 2)]
            removed += 1
        if result.endswith("\n" + phrase):
            result = result[: -(len(phrase) + 1)]
            removed += 1
    # Inline pass: catch phrases embedded mid-paragraph
    inline_result, inline_n = _strip_grounding_inline(result, _GROUNDING_PARAGRAPHS)
    if inline_n > 0:
        result = inline_result
        removed += inline_n
    # Clean up any double \n\n\n
    while "\n\n\n" in result:
        result = result.replace("\n\n\n", "\n\n")
    return result, removed


def strip_preambles(text: str) -> Tuple[str, int]:
    """Remove preamble meta-text: 'Lena Castillo found herself in the...', etc.
    Returns (modified_text, count_removed).
    """
    if not text or not text.strip():
        return text, 0
    removed = 0
    paras = text.split("\n\n")
    out = []
    for para in paras:
        orig = para
        # Strip leading preamble sentence(s) from paragraph
        while True:
            m = _PREAMBLE_PATTERN.match(para) or _PREAMBLE_I_PATTERN.match(para)
            if m:
                para = para[m.end() :].lstrip()
                removed += 1
            else:
                break
        if para.strip():
            out.append(para)
    return "\n\n".join(out), removed


def fix_double_periods(text: str) -> Tuple[str, int]:
    """Replace .. or ... with single period. Returns (modified_text, count_fixed)."""
    if not text:
        return text, 0
    result, n = _DOUBLE_PERIOD_PATTERN.subn(".", text)
    return result, n


def fix_filter_words(text: str) -> Tuple[str, int]:
    """I could feel -> I felt; strip I could see/hear. Returns (modified_text, count_fixed)."""
    if not text:
        return text, 0
    fixed = 0
    result = text
    result, c = _FILTER_FEEL.subn("I felt", result)
    fixed += c
    # Strip "I could see" - often followed by clause; just remove the hedge
    result, c = re.subn(r"\bI could see\b", "I saw", result, flags=re.IGNORECASE)
    fixed += c
    result, c = re.subn(r"\bI could hear\b", "I heard", result, flags=re.IGNORECASE)
    fixed += c
    return result, fixed


def fix_pov_pronouns(text: str) -> Tuple[str, int]:
    """Fix POV pronoun confusion (my → her). Returns (modified_text, count_fixed)."""
    if not text or not text.strip():
        return text, 0
    fixed = 0
    result = text
    for pattern, repl in _POV_PATTERNS:
        new_result, n = pattern.subn(repl, result)
        if n > 0:
            result = new_result
            fixed += n
    return result, fixed


def remove_elena_hallucination(text: str, scene_id: str = "") -> Tuple[str, bool]:
    """Remove the Elena hallucination block from Ch4 market scene.
    Returns (modified_text, was_removed).
    """
    if not text or "Elena" not in text or "Then she steps into my line of sight" not in text:
        return text, False
    if "ch04_s03" not in str(scene_id) and "ch4" not in str(scene_id).lower():
        return text, False

    start_idx = text.find(_ELENA_ALT_START)
    if start_idx == -1:
        return text, False
    # Find end: full sentence ending with "like a bridge I'm terrified to cross."
    end_phrase = "like a bridge I'm terrified to cross."
    end_idx = text.find(end_phrase, start_idx)
    if end_idx == -1:
        return text, False
    end_idx += len(end_phrase)

    pre = text[:start_idx].rstrip()
    post = text[end_idx:].lstrip()
    result = pre + ("\n\n" + post if post else "")
    return result, True


def fix_marco_ring(text: str) -> Tuple[str, int]:
    """Fix Marco's wedding ring → signet ring (he's best man, not groom)."""
    result, n = text, 0
    for p, r in _MARCO_RING_FIXES:
        new_result, c = re.subn(p, r, result)
        if c > 0:
            result, n = new_result, n + c
    return result, n


def fix_timeline(text: str) -> Tuple[str, int]:
    """Fix timeline: four/five years ago → three years."""
    result, n = text, 0
    for p, r in _TIMELINE_FIXES:
        new_result, c = re.subn(p, r, result)
        if c > 0:
            result, n = new_result, n + c
    return result, n


def fix_enzos_line(text: str) -> Tuple[str, int]:
    """Fix Enzo romantic line → supportive alternative."""
    result, n = text, 0
    for p, r in _ENZO_FIXES:
        new_result, c = re.subn(p, r, result)
        if c > 0:
            result, n = new_result, n + c
    return result, n


def fix_mussed(text: str) -> Tuple[str, int]:
    """Vary 'leaving it slightly mussed'."""
    result, n = text, 0
    for p, r in _MUSSED_FIXES:
        new_result, c = re.subn(p, r, result)
        if c > 0:
            result, n = new_result, n + c
    return result, n


def fix_between_us(text: str) -> Tuple[str, int]:
    """Diversify 'between us like [simile]'."""
    result, n = text, 0
    for p, r in _BETWEEN_US_ALTERNATIVES:
        new_result, c = re.subn(p, r, result)
        if c > 0:
            result, n = new_result, n + c
    return result, n


def run_editorial_cleanup(
    scenes: List[Dict],
    *,
    do_strip_preambles: bool = True,
    strip_grounding: bool = True,
    do_fix_double_periods: bool = True,
    do_fix_filter_words: bool = True,
    fix_pov: bool = True,
    remove_elena: bool = True,
    apply_marco_ring: bool = True,
    apply_timeline: bool = True,
    apply_enzos_line: bool = True,
    apply_mussed: bool = True,
    apply_between_us: bool = True,
) -> Dict[str, Any]:
    """Run full editorial cleanup on scenes. Modifies scenes in-place.

    Returns report with counts for each fix type.
    """
    report = {
        "preambles_stripped": 0,
        "grounding_removed": 0,
        "double_periods_fixed": 0,
        "filter_words_fixed": 0,
        "pov_fixed": 0,
        "elena_removed": False,
        "marco_ring_fixed": 0,
        "timeline_fixed": 0,
        "enzos_line_fixed": 0,
        "mussed_fixed": 0,
        "between_us_fixed": 0,
        "scenes_modified": 0,
    }
    for scene in scenes or []:
        if not isinstance(scene, dict) or not scene.get("content"):
            continue
        content = scene["content"]
        sid = scene.get("scene_id", "")
        modified = False

        if do_strip_preambles:
            content, n = strip_preambles(content)
            if n > 0:
                report["preambles_stripped"] += n
                modified = True

        if strip_grounding:
            content, n = strip_grounding_artifacts(content)
            if n > 0:
                report["grounding_removed"] += n
                modified = True

        if do_fix_double_periods:
            content, n = fix_double_periods(content)
            if n > 0:
                report["double_periods_fixed"] += n
                modified = True

        if do_fix_filter_words:
            content, n = fix_filter_words(content)
            if n > 0:
                report["filter_words_fixed"] += n
                modified = True

        if fix_pov:
            content, n = fix_pov_pronouns(content)
            if n > 0:
                report["pov_fixed"] += n
                modified = True

        if remove_elena and sid == "ch04_s03":
            content, removed = remove_elena_hallucination(content, sid)
            if removed:
                report["elena_removed"] = True
                modified = True

        if apply_marco_ring:
            content, n = fix_marco_ring(content)
            if n > 0:
                report["marco_ring_fixed"] += n
                modified = True

        if apply_timeline:
            content, n = fix_timeline(content)
            if n > 0:
                report["timeline_fixed"] += n
                modified = True

        if apply_enzos_line:
            content, n = fix_enzos_line(content)
            if n > 0:
                report["enzos_line_fixed"] += n
                modified = True

        if apply_mussed:
            content, n = fix_mussed(content)
            if n > 0:
                report["mussed_fixed"] += n
                modified = True

        if apply_between_us:
            content, n = fix_between_us(content)
            if n > 0:
                report["between_us_fixed"] += n
                modified = True

        if modified:
            scene["content"] = content
            report["scenes_modified"] += 1

    return report
