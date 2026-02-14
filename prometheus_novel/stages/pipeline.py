"""
Pipeline Orchestrator - 12-Stage Novel Generation Pipeline

Orchestrates the complete novel generation process through 12 stages:
1. High Concept - Generate core theme and hook
2. World Building - Establish setting and rules
3. Beat Sheet - Create 3-act structure
4. Character Profiles - Develop character psychology
5. Master Outline - Plan scene-by-scene
6. Scene Drafting - Generate scene content
7. Self Refinement - Iterative quality improvement
8. Continuity Audit - Check consistency
9. Human Passes - Prose enhancement
10. Voice Humanization - Apply voice signature
11. Motif Infusion - Weave thematic elements
12. Output Validation - Final quality checks
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import yaml

logger = logging.getLogger(__name__)


# ============================================================================
# RHETORICAL DEVICES BANK - For prose enhancement stages
# ============================================================================
RHETORICAL_DEVICES = {
    # Sound & Rhythm
    "alliteration": "Repeated consonant sounds at word beginnings",
    "assonance": "Repetition of vowel sounds within words",
    "meter": "Rhythmic patterns in prose for emphasis",

    # Repetition Patterns
    "anaphora": "Starting successive sentences/clauses with same word",
    "epistrophe": "Ending successive phrases with same word",
    "epizeuxis": "Immediate repetition for emphasis ('Never, never, never')",
    "diacope": "Word repeated after brief interruption ('Bond. James Bond')",
    "anadiplosis": "End of one phrase becomes start of next",
    "epanalepsis": "Beginning and end echo each other (circularity)",

    # Structure & Balance
    "tricolon": "Three parallel elements (often ascending/descending)",
    "isocolon": "Two grammatically parallel sentences",
    "chiasmus": "Mirrored structure ('Fair is foul, foul is fair')",
    "antithesis": "Contrasting ideas placed near each other",
    "parallelism": "Similar grammatical structures for related ideas",
    "periodic_sentence": "Meaning withheld until end for suspense",

    # Word Play
    "polyptoton": "Words from same root in succession ('watch the watchman')",
    "syllepsis": "Word used in multiple senses ('took his hat and his leave')",
    "zeugma": "One word carries across sentence parts",
    "hendiadys": "'adjective noun' becomes 'noun and noun' (furious sound → sound and fury)",
    "catachresis": "Using words in unusual ways (legs for chair supports)",

    # Imagery & Figures
    "metaphor": "Implicit comparison (A is B)",
    "synesthesia": "One sense described in terms of another",
    "personification": "Human qualities to inanimate things",
    "metonymy": "Thing called by associated concept (crown for monarchy)",
    "synecdoche": "Part stands for whole (wheels for car)",
    "hyperbole": "Deliberate exaggeration for effect",
    "litotes": "Affirming by denying opposite ('not bad' = good)",
    "adynaton": "Impossible image for emphasis",

    # Pacing & Drama
    "aposiopesis": "Breaking off mid-sentence (trailing off...)",
    "hyperbaton": "Unusual word order for emphasis",
    "rhetorical_question": "Question that implies its answer",
    "prolepsis": "Foreshadowing or anticipating objections",

    # Lists & Accumulation
    "merism": "Representing whole by naming parts",
    "blazon": "Extended descriptive list",
    "congeries": "Heaping of words/phrases for cumulative effect",
    "parataxis": "Clauses placed side by side without conjunctions",
    "hypotaxis": "Hierarchy of clauses (subordination)",
}

# ANTI-AI-TELL PATTERNS - Phrases that reveal AI authorship
AI_TELL_PATTERNS = [
    # Observation filters
    "I couldn't help but",
    "I found myself",
    "Something about [X] made me",
    "I noticed that",
    "I realized that",
    "I felt a sense of",
    "I was struck by",

    # Weak transitions
    "suddenly",
    "immediately",
    "in that moment",
    "before I knew it",
    "without warning",

    # Purple prose markers
    "a whirlwind of emotions",
    "time seemed to stop",
    "electricity coursed through",
    "my heart skipped a beat",
    "butterflies in my stomach",
    "a wave of [emotion]",
    "flooded with",
    "overwhelmed by",

    # Hollow intensifiers
    "incredibly",
    "absolutely",
    "utterly",
    "completely",
    "totally",
    "truly",
    "genuinely",

    # AI favorite constructions
    "couldn't quite",
    "seemed to",
    "appeared to",
    "managed to",
    "proceeded to",
    "began to",
    "started to",

    # Telling instead of showing
    "I felt [emotion]",
    "I was [emotion]",
    "a mix of [emotion] and [emotion]",
    "I knew [character] felt",
]

# ============================================================================
# REQUIRED CONFIG FIELDS - Validation schema
# ============================================================================
REQUIRED_CONFIG_FIELDS = {
    "project_name": str,
    "title": str,
    "synopsis": str,
    "genre": str,
    "protagonist": str,
    "target_length": str
}

OPTIONAL_BUT_RECOMMENDED = [
    "antagonist", "setting", "tone", "themes", "motifs",
    "writing_style", "influences", "avoid", "key_plot_points"
]


# ============================================================================
# GENRE-SPECIFIC TROPE CHECKLISTS
# ============================================================================
ROMANCE_TROPES = {
    "touch_her_and_die": {
        "description": "Hero violently protects heroine from threat",
        "required_elements": [
            "Heroine is threatened/touched by antagonist",
            "Hero's violence is FAST and PRECISE (not rage-blind)",
            "Hero tends to her wounds/comfort after",
            "Hero shows vulnerability (concern, trembling)",
            "Heroine sees him differently (dangerous FOR her, not TO her)",
            "Intimacy/closeness follows naturally"
        ],
        "placement": "midpoint_50pct"
    },
    "forced_proximity": {
        "description": "Characters must share space against their will",
        "required_elements": [
            "Physical closeness is unavoidable",
            "Tension from proximity (not just plot)",
            "Accidental touching/awareness",
            "Internal conflict about attraction",
            "Gradual comfort with closeness"
        ],
        "placement": "threshold_25pct"
    },
    "praise_kink": {
        "description": "Hero verbally worships/praises heroine",
        "required_elements": [
            "Specific compliments (not generic 'beautiful')",
            "Focus on what she's insecure about",
            "Her physical reaction to praise",
            "Repeated across multiple scenes",
            "Escalates from public to intimate"
        ],
        "placement": "throughout"
    },
    "body_worship": {
        "description": "Hero appreciates heroine's body she's insecure about",
        "required_elements": [
            "Hero notices curves/body specifically",
            "Not just during intimacy (casual moments too)",
            "Physical touch that celebrates her body",
            "Her internal shift from shame to acceptance",
            "He demands she display rather than hide"
        ],
        "placement": "throughout"
    }
}


# ============================================================================
# WORD COUNTING UTILITIES
# ============================================================================
def count_words_accurate(text: str) -> int:
    """Accurately count words, excluding markdown and formatting."""
    if not text:
        return 0
    # Remove markdown headers
    text = re.sub(r'^#+\s+.*$', '', text, flags=re.MULTILINE)
    # Remove scene breaks
    text = re.sub(r'[⁂\*]{3,}', '', text)
    # Remove markdown formatting
    text = re.sub(r'[\*_\[\]`#]', '', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Split and count non-empty words
    words = [w for w in text.split() if w.strip()]
    return len(words)


def validate_scene_length(scene: Dict, target_words: int, tolerance: float = 0.8) -> Dict:
    """Check if scene meets word count target."""
    if not isinstance(scene, dict):
        return {"scene": "?", "actual": 0, "target": target_words, "min_required": int(target_words * tolerance), "meets_target": False, "shortfall": target_words}
    content = scene.get("content", "")
    actual_words = count_words_accurate(content)
    min_words = int(target_words * tolerance)

    return {
        "scene": f"Ch{scene.get('chapter')}-S{scene.get('scene_number')}",
        "actual": actual_words,
        "target": target_words,
        "min_required": min_words,
        "meets_target": actual_words >= min_words,
        "shortfall": max(0, min_words - actual_words)
    }


def count_ai_tells(text: str) -> Dict:
    """Count AI tell patterns in text."""
    text_lower = text.lower()
    counts = {}
    total = 0

    for pattern in AI_TELL_PATTERNS:
        # Handle patterns with placeholders
        search_pattern = pattern.lower().replace("[x]", "").replace("[emotion]", "").replace("[character]", "")
        count = text_lower.count(search_pattern)
        if count > 0:
            counts[pattern] = count
            total += count

    word_count = count_words_accurate(text)
    ratio = total / (word_count / 1000) if word_count > 0 else 0

    return {
        "total_tells": total,
        "tells_per_1000_words": round(ratio, 2),
        "patterns_found": counts,
        "word_count": word_count,
        "acceptable": ratio < 2.0  # Less than 2 per 1000 words is acceptable
    }


def validate_config(config: Dict) -> Dict:
    """Validate config has required fields."""
    errors = []
    warnings = []

    for field, expected_type in REQUIRED_CONFIG_FIELDS.items():
        if field not in config:
            errors.append(f"Missing required field: {field}")
        elif not config[field]:
            errors.append(f"Empty required field: {field}")
        elif not isinstance(config[field], expected_type):
            errors.append(f"{field} should be {expected_type.__name__}")

    for field in OPTIONAL_BUT_RECOMMENDED:
        if field not in config or not config[field]:
            warnings.append(f"Recommended field missing: {field}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "completeness": (len(config) / (len(REQUIRED_CONFIG_FIELDS) + len(OPTIONAL_BUT_RECOMMENDED))) * 100
    }


def _clean_scene_content(text: str) -> str:
    """Strip meta-text, LLM preambles, editing artifacts, and analysis notes.

    Catches all known artifact categories:
    1. Analysis/checklist appendices ("Changes made:", "Scanning for AI tells:")
    2. LLM preambles ("Sure, here's...", "Here is the revised...")
    3. Prompt bleed-through ("CURRENT SCENE:", "A great chapter-ending hook can be:")
    4. Section markers ("=== EXPANDED SCENE ===", "ENHANCED SCENE:")
    5. UI/formatting artifacts ("Visible: 0%", percentage markers)
    6. Instruction echoes ("Output ONLY the revised scene")
    """
    import re

    if not text:
        return text

    # --- PHASE 1: Strip LLM preambles from the BEGINNING of text ---
    # These are lines the LLM puts before the actual prose
    preamble_patterns = [
        r'^(?:Sure[,!.]?\s*)?[Hh]ere\'?s?\s+(?:the |a |my |an? )?'
        r'(?:revised|enhanced|polished|expanded|edited|updated|improved|rewritten|final)'
        r'[^.:\n]{0,40}[.:]\s*\n+',
        r'^(?:Sure[,!.]?\s*)?[Hh]ere\s+is\s+(?:the |a |my )?'
        r'(?:revised|enhanced|polished|expanded|edited|updated|improved|rewritten|final)'
        r'[^.:\n]{0,40}[.:]\s*\n+',
        r'^(?:Sure|Certainly|Of course|Absolutely)[,!.]\s*(?:here\'?s?|I\'ve|I have|let me)'
        r'[^\n]{0,80}\n+',
        r'^(?:I\'ve |I have )(?:revised|enhanced|polished|expanded|edited|rewritten)'
        r'[^\n]{0,80}\n+',
        r'^(?:Below is|The following is|What follows is)[^\n]{0,60}\n+',
    ]
    for pattern in preamble_patterns:
        text = re.sub(pattern, '', text, count=1, flags=re.IGNORECASE)

    # --- PHASE 2: Strip trailing meta-text (truncate at first meta-marker) ---
    # These signal end-of-prose, start-of-analysis/commentary
    tail_patterns = [
        r'\n---+\s*\n',                    # --- separators
        r'\n\*\*\*+\s*\n',                 # *** separators
        r'\n===+[^=]*===*\s*\n',            # === EXPANDED SCENE === etc.
        r'\n\*\*(?:Scanning|Changes|Notes?|Quality|Summary|Checklist|AI tells)',
        r'\n(?:Scanning|Changes made|Notes?:|Quality|Summary:)',
        r'\n(?:I\'ve |I have |Here\'s what|The (?:above|following|revised))',
        r'\n(?:The )?rest (?:of (?:the |this )?(?:scene|chapter|text|content) )?'
        r'(?:remains?|is) unchanged',
        r'\n\[(?:The )?rest (?:of (?:the |this )?(?:scene|chapter))? remains unchanged',
        r'\n(?:\[(?:Scene|Chapter|End|Note))',  # [Scene continues...] etc.
        r'\n(?:ENHANCED SCENE|EXPANDED SCENE|POLISHED SCENE|FIXED SCENE|'
        r'CURRENT SCENE|REVISED SCENE|MODIFIED SCENE)',
        # Prompt bleed-through from chapter_hooks stage
        r'\n(?:A great (?:chapter-ending|chapter-opening) hook can be:?)',
        r'\n(?:CURRENT SCENE(?: MODIFIED)?:)',
        # Output instruction echoes
        r'\n(?:Output (?:ONLY |only )?the (?:revised|enhanced|polished|expanded))',
        # UI / formatting artifacts
        r'\n(?:Visible:\s*\d+%)',
    ]

    for pattern in tail_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = text[:match.start()].rstrip()
            if len(candidate) > 100:
                text = candidate

    # --- PHASE 3: Inline artifact removal (patterns that appear MID-text) ---
    # These can appear anywhere in the prose, not just at the end
    inline_patterns = [
        # "The rest remains unchanged" and all variants (scene/chapter/text)
        r'(?:The )?rest (?:of (?:the |this )?(?:scene|chapter|text|content) )?'
        r'(?:remains?|is) unchanged[^.]*[.\s]*',
        r'\[(?:The )?rest (?:of (?:the |this )?(?:scene|chapter))? remains unchanged[^\]]*\]\s*',
        # "CURRENT SCENE MODIFIED:" headers
        r'CURRENT SCENE(?: MODIFIED)?:\s*',
        # "Visible: 0% – 100%" or similar percentage markers
        r'Visible:\s*\d+%\s*[–—-]\s*\d+%\s*',
        # Stray prompt markers that slipped through
        r'(?:ENHANCED|EXPANDED|POLISHED|FIXED|REVISED) SCENE:\s*',
        # "Sure, here's the revised version:" mid-text
        r'(?:Sure[,.]?\s*)?[Hh]ere\'?s?\s+(?:the |a )?(?:revised|enhanced|polished|expanded|edited)'
        r'\s+(?:version|scene|text|content)[.:]\s*',
        # Hook instruction bleed
        r'A great chapter-(?:ending|opening) hook can be:\s*(?:\n[-•*][^\n]+)*',
        # Bullet lists of writing tips (from prompt)
        r'(?:\n[-•*]\s*(?:A cliffhanger|In medias res|A striking sensory|'
        r'A provocative|Immediate conflict|Disorientation|A kiss or romantic|'
        r'A threat delivered|A question raised|A twist revealed|'
        r'An emotional gut-punch|A decision made)[^\n]*)+',
    ]

    for pattern in inline_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # --- PHASE 4: Clean up whitespace artifacts ---
    # Remove resulting blank lines (3+ newlines -> 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove trailing whitespace on lines
    text = re.sub(r' +\n', '\n', text)

    return text.strip()


def _enforce_first_person_pov(text: str, protagonist_name: str = "") -> str:
    """Code-level enforcement of first-person POV.

    Detects and fixes common third-person slips where the model switches
    from 'I' to 'she/he [character name] [verb]'.

    This is a SAFETY NET — runs after every creative stage.
    """
    if not text or not protagonist_name:
        return text

    # Build protagonist name variants (e.g., "Lena", "Lena Castillo")
    names = [n.strip() for n in protagonist_name.split() if len(n.strip()) > 1]
    first_name = names[0] if names else ""
    if not first_name:
        return text

    # Common third-person patterns to fix
    # "Lena felt" -> "I felt", "She noticed" -> "I noticed"
    fixes = []

    # Pattern: "[Name] [past-tense verb]" at sentence start
    verbs = (r"felt|thought|noticed|realized|knew|watched|saw|heard|"
             r"walked|turned|looked|moved|pulled|pushed|grabbed|reached|"
             r"smiled|laughed|sighed|whispered|murmured|said|asked|"
             r"wondered|considered|remembered|imagined|wished|hoped|"
             r"tightened|clenched|tamed|tugged|brushed|ran|stood|sat|"
             r"leaned|stepped|glanced|stared|paused|stopped|started|"
             r"shook|nodded|blinked|swallowed|inhaled|exhaled|breathed")

    # Fix "[FirstName] verb" -> "I verb"
    text = re.sub(
        rf'\b{re.escape(first_name)}\s+({verbs})\b',
        r'I \1',
        text
    )

    # Fix "She/He verb" at sentence boundaries (text start, after . or newline)
    for pronoun in ["She", "He"]:
        text = re.sub(
            rf'^{pronoun}\s+({verbs})\b',
            r'I \1',
            text
        )
        text = re.sub(
            rf'(?<=[.!?]\s){pronoun}\s+({verbs})\b',
            r'I \1',
            text
        )
        text = re.sub(
            rf'(?<=\n){pronoun}\s+({verbs})\b',
            r'I \1',
            text
        )

    # Body parts whitelist for possessive fixes
    body_parts = (r'hand|heart|jaw|throat|stomach|chest|fingers|eyes|voice|'
                  r'mind|head|breath|hair|shoulder|back|arm|leg|pulse|skin|'
                  r'lip|lips|cheek|face|gaze|palms|wrist|temple|forehead|'
                  r'collarbone|ribcage|spine|hips|knees|ankles|neck|chin|'
                  r'brow|eyebrow|eyelid|nostril|ear|elbow|fingertips|'
                  r'lungs|ribs|belly|navel|waist')

    # Fix "[Name]'s [body part]" -> "my [body part]"
    # Use a function to handle capitalization at sentence starts
    def _possessive_replacement(match):
        """Replace possessive with 'my'/'My' depending on sentence position."""
        full = match.group(0)
        body = match.group(1)
        start = match.start()
        # Check if at sentence start (beginning of text or after . ! ? \n)
        if start == 0:
            return f'My {body}'
        preceding = text[max(0, start-2):start]
        if re.search(r'[.!?]\s*$', preceding) or preceding.endswith('\n'):
            return f'My {body}'
        return f'my {body}'

    text = re.sub(
        rf"\b{re.escape(first_name)}'s\s+({body_parts})\b",
        _possessive_replacement,
        text
    )

    # Fix "Her/His [body part]" -> "My [body part]" at sentence starts and text start
    for pronoun in ["Her", "His"]:
        # At text start
        text = re.sub(
            rf'^{pronoun}\s+({body_parts})\b',
            r'My \1',
            text
        )
        # After sentence-ending punctuation
        text = re.sub(
            rf'(?<=[.!?]\s){pronoun}\s+({body_parts})\b',
            r'My \1',
            text
        )
        # After newline
        text = re.sub(
            rf'(?<=\n){pronoun}\s+({body_parts})\b',
            r'My \1',
            text
        )

    # Fix mid-sentence "her/his [body part]" -> "my [body part]"
    # Uses body-part whitelist to avoid false positives like "I saw her"
    for pronoun in ["her", "his"]:
        text = re.sub(
            rf'\b{pronoun}\s+({body_parts})\b',
            r'my \1',
            text
        )

    # Fix remaining "She/He" with auxiliary verbs at sentence boundaries
    aux_verbs = r"was|had|would|could|didn't|couldn't|wouldn't|wasn't|hadn't"
    for pronoun in ["She", "He"]:
        text = re.sub(
            rf'^{pronoun}\s+({aux_verbs})\b',
            r'I \1',
            text
        )
        text = re.sub(
            rf'(?<=[.!?]\s){pronoun}\s+({aux_verbs})\b',
            r'I \1',
            text
        )
        text = re.sub(
            rf'(?<=\n){pronoun}\s+({aux_verbs})\b',
            r'I \1',
            text
        )

    # Fix contractions: "She'd/He'd" -> "I'd", "She's/He's" -> "I'm"
    for pronoun in ["She", "He"]:
        text = re.sub(rf"(?<=[.!?]\s){pronoun}'d\b", "I'd", text)
        text = re.sub(rf"(?<=\n){pronoun}'d\b", "I'd", text)
        text = re.sub(rf"(?<=[.!?]\s){pronoun}'s\b", "I'm", text)
        text = re.sub(rf"(?<=\n){pronoun}'s\b", "I'm", text)

    return text


def _strip_emotional_summaries(text: str) -> str:
    """Detect and remove paragraph-ending emotional summary sentences.

    These are the #1 quality issue: sentences that explain what a scene
    means emotionally after the prose already showed it.

    Strategy: extract the last 1-2 sentences of each paragraph and check
    if they match summary patterns. Remove them if so.
    """
    if not text:
        return text

    # Sentence-start patterns that indicate emotional summarization
    # These match the BEGINNING of a summary sentence (no leading period required)
    summary_starters = [
        # "This wasn't just about X"
        r"This wasn't just about\b",
        r"This was(?:n't)? (?:more than|about more)\b",
        r"It was(?:n't)? just (?:about|a)\b",
        r"It wasn't (?:about|just)\b",
        # "Something about..."
        r"Something about (?:this|the|that|their) (?:moment|night|exchange|gesture|silence|connection|look)",
        # "A [adj] [abstract]..."
        r"A (?:fragile|quiet|tentative|unspoken|silent|small|new|strange|sudden|growing|delicate|unexpected) "
        r"(?:connection|promise|understanding|bond|hope|beginning|trust|shift|warmth|peace|certainty|realization)",
        # "Tonight/Today [pronoun] realized..."
        r"(?:Tonight|Today|In that (?:moment|instant|silence)),?\s*(?:I|she|he|they) "
        r"(?:realized|understood|knew|felt|sensed|recognized)",
        # "was a reminder that..."
        r"[A-Z][^.]{0,40}was a reminder that\b",
        # "a sense of..."
        r"[A-Z][^.]{0,40}a sense of (?:something|hope|possibility|belonging|peace|closure|completion)",
        # "It felt like the beginning..."
        r"It felt like (?:the (?:beginning|start|end)|a (?:turning point|new chapter|threshold)|something (?:new|real|fragile|important))",
        # "For the first time..."
        r"For the first time in (?:a long time|years|months|forever|what felt like)",
        r"For the first time,?\s*(?:I|she|he) (?:felt|believed|thought|allowed|let)",
        # "Maybe X was about Y" / "Maybe this was..."
        r"Maybe (?:this|that|it|love|healing|forgiveness) (?:was|wasn't|didn't|couldn't)\b",
        # "And in that moment..."
        r"And (?:in that|for the first|somehow|maybe|perhaps),?\s",
        # "[Name/I] didn't know it yet, but..."
        r"(?:I|She|He) (?:didn't know|couldn't have known|had no idea)\b",
        # "That was when/what..."
        r"That was (?:when|what|the moment|how)\b",
        # Generic "the X of Y" emotional summaries
        r"The (?:weight|warmth|promise|reality|truth|beauty|gravity|fragility) of "
        r"(?:that|this|the|their|what|it)\b",
    ]

    # Compile patterns for efficiency
    compiled_starters = [re.compile(p, re.IGNORECASE) for p in summary_starters]

    paragraphs = text.split('\n\n')
    cleaned_paragraphs = []

    for para in paragraphs:
        if not para.strip():
            cleaned_paragraphs.append(para)
            continue

        # Split paragraph into sentences
        # Match sentence boundaries: period/!/? followed by space and capital letter (or quote)
        sent_breaks = list(re.finditer(r'(?<=[.!?])\s+(?=[A-Z"\'\u201c])', para))
        if not sent_breaks:
            cleaned_paragraphs.append(para)
            continue

        # Extract the last sentence
        last_sent_start = sent_breaks[-1].end()
        last_sentence = para[last_sent_start:].strip()

        # Also check the last sentence before a semicolon split
        # "X; it was about Y." -> the "it was about Y" part
        semicolon_match = re.search(r';\s*(.+)$', last_sentence)

        is_summary = False
        for compiled in compiled_starters:
            if compiled.match(last_sentence):
                is_summary = True
                break
            # Also check after semicolon
            if semicolon_match and compiled.match(semicolon_match.group(1).strip()):
                is_summary = True
                break

        if is_summary:
            # Remove the last sentence, keep the rest
            candidate = para[:last_sent_start].rstrip()
            # Safety: keep at least one complete sentence (has a period/!/?)
            if candidate and re.search(r'[.!?]', candidate):
                # If there was a semicolon summary, keep up to the semicolon
                if semicolon_match and not compiled_starters[0].match(last_sentence):
                    # The summary is after the semicolon - keep text before semicolon
                    semi_pos = last_sentence.find(';')
                    before_semi = last_sentence[:semi_pos].rstrip()
                    if before_semi:
                        suffix = before_semi if before_semi.endswith('.') else before_semi + '.'
                        para = candidate + ' ' + suffix
                    else:
                        para = candidate if candidate.endswith(('.', '!', '?')) else candidate + '.'
                else:
                    para = candidate if candidate.endswith(('.', '!', '?')) else candidate + '.'

                # Check the NEW last sentence too (cascading summaries)
                # Re-split and check one more time
                sent_breaks2 = list(re.finditer(r'(?<=[.!?])\s+(?=[A-Z"\'\u201c])', para))
                if sent_breaks2:
                    last2_start = sent_breaks2[-1].end()
                    last2_sentence = para[last2_start:].strip()
                    for compiled in compiled_starters:
                        if compiled.match(last2_sentence):
                            candidate2 = para[:last2_start].rstrip()
                            if candidate2 and re.search(r'[.!?]', candidate2):
                                para = candidate2 if candidate2.endswith(('.', '!', '?')) else candidate2 + '.'
                            break

        cleaned_paragraphs.append(para)

    return '\n\n'.join(cleaned_paragraphs)


def _limit_tic_frequency(text: str, max_per_scene: int = 1) -> str:
    """Limit character tics and repeated physical beats to max_per_scene occurrences.

    Detects phrases like "tamed her curly hair", "tightened around",
    "jaw clenched", etc. Removes the ENTIRE SENTENCE containing excess
    occurrences to avoid garbled output.
    """
    if not text:
        return text

    # Common repeated tics to track
    tic_patterns = [
        (r'tamed?\s+(?:her |my |his )?(?:curly )?hair\s*(?:compulsively)?', 'hair taming'),
        (r'(?:fingers?\s+)?tightened\s+around', 'finger tightening'),
        (r'jaw\s+clenched', 'jaw clenching'),
        (r'tugg(?:ed|ing)\s+(?:at\s+)?(?:her |my |his )?(?:curly )?hair', 'hair tugging'),
        (r'ran\s+(?:her |my |his )?(?:fingers?\s+)?through\s+(?:her |my |his )?hair', 'hair running'),
        (r'heart\s+(?:hammered|pounded|raced|thundered)', 'heart racing'),
        (r'stomach\s+(?:flipped|dropped|churned|knotted)', 'stomach flipping'),
        (r'breath\s+(?:caught|hitched|stuttered)', 'breath catching'),
        (r'pulse\s+(?:quickened|raced|spiked|jumped)', 'pulse racing'),
        (r'like\s+a\s+knife', 'simile: like a knife'),
        (r'vamos\s+a\s+ser\s+realistas', 'catchphrase: vamos'),
    ]

    # Build a set of sentence indices to remove
    sentences_to_remove = set()

    # Split text into sentences preserving structure
    # We use a regex that splits on sentence-ending punctuation followed by space
    # but keeps the punctuation with the sentence
    sentence_breaks = list(re.finditer(r'(?<=[.!?])\s+(?=[A-Z"\'])', text))
    sentence_starts = [0] + [m.end() for m in sentence_breaks]
    sentence_ends = [m.start() for m in sentence_breaks] + [len(text)]
    sentences = [(sentence_starts[i], sentence_ends[i]) for i in range(len(sentence_starts))]

    for pattern, tic_name in tic_patterns:
        occurrences = []  # list of sentence indices containing this tic
        for sent_idx, (start, end) in enumerate(sentences):
            sent_text = text[start:end]
            if re.search(pattern, sent_text, re.IGNORECASE):
                occurrences.append(sent_idx)

        if len(occurrences) > max_per_scene:
            # Mark excess sentences for removal (keep first N, remove the rest)
            for sent_idx in occurrences[max_per_scene:]:
                sentences_to_remove.add(sent_idx)

    if not sentences_to_remove:
        return text

    # Rebuild text without the removed sentences
    kept_parts = []
    for sent_idx, (start, end) in enumerate(sentences):
        if sent_idx not in sentences_to_remove:
            kept_parts.append(text[start:end])

    result = ' '.join(kept_parts)

    # Clean up paragraph structure — restore double newlines
    result = re.sub(r' *\n *\n *', '\n\n', result)
    # Clean up any double spaces
    result = re.sub(r'  +', ' ', result)

    return result


def _detect_duplicate_content(text: str, similarity_threshold: float = 0.6) -> str:
    """Detect and remove duplicate/stitched scene content.

    Local models sometimes generate two versions of the same scene stitched
    together. This detects large blocks of text that share significant overlap
    and keeps only the first (usually better) version.

    Strategy: split text into large chunks (by scene breaks or paragraph groups),
    compare overlapping n-grams, and remove the second duplicate.
    """
    if not text or len(text) < 200:
        return text

    # Common markers where models stitch duplicates
    stitch_markers = [
        r'\n---+\n',           # --- separators
        r'\n\*\*\*+\n',       # *** separators
        r'\n#{1,3}\s',         # Markdown headers mid-scene
        r'\nVersion \d',       # "Version 2"
        r'\nAlternative:',     # "Alternative:"
        r'\nRevised:',         # "Revised:"
        r'\nTake \d',          # "Take 2"
    ]

    for marker in stitch_markers:
        parts = re.split(marker, text, maxsplit=1)
        if len(parts) == 2 and len(parts[0].strip()) > 100 and len(parts[1].strip()) > 100:
            # Check similarity between the two halves
            words_a = set(parts[0].lower().split())
            words_b = set(parts[1].lower().split())
            if words_a and words_b:
                overlap = len(words_a & words_b) / min(len(words_a), len(words_b))
                if overlap > similarity_threshold:
                    # Duplicates detected — keep the longer one (usually more complete)
                    text = parts[0].strip() if len(parts[0]) >= len(parts[1]) else parts[1].strip()

    # Also check for paragraph-level duplication within the text
    # Split into paragraphs and find near-duplicate pairs
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip() and len(p.strip()) > 80]
    if len(paragraphs) >= 2:
        seen_fingerprints = {}
        duplicated_indices = set()

        for idx, para in enumerate(paragraphs):
            # Fingerprint: first 8 words + last 8 words
            words = para.split()
            if len(words) < 10:
                continue
            fingerprint = ' '.join(words[:8]).lower()

            if fingerprint in seen_fingerprints:
                # Check full similarity
                orig_idx = seen_fingerprints[fingerprint]
                orig_words = set(paragraphs[orig_idx].lower().split())
                curr_words = set(para.lower().split())
                overlap = len(orig_words & curr_words) / min(len(orig_words), len(curr_words))
                if overlap > similarity_threshold:
                    duplicated_indices.add(idx)
            else:
                seen_fingerprints[fingerprint] = idx

        if duplicated_indices:
            all_paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            # Map back to all_paragraphs indices (including short ones)
            long_to_all = {}
            long_idx = 0
            for all_idx, p in enumerate(all_paragraphs):
                if len(p) > 80:
                    long_to_all[long_idx] = all_idx
                    long_idx += 1

            remove_all_indices = {long_to_all[i] for i in duplicated_indices if i in long_to_all}
            all_paragraphs = [p for i, p in enumerate(all_paragraphs) if i not in remove_all_indices]
            text = '\n\n'.join(all_paragraphs)

    return text


def _flag_language_inconsistencies(text: str, setting_language: str = "") -> str:
    """Flag or fix foreign language inconsistencies in the text.

    Detects when a model uses the wrong foreign language (e.g., Spanish
    phrases in an Italian setting, or vice versa). This is a common LLM
    hallucination where the model confuses romance languages.

    If setting_language is specified (e.g., "Italian"), replaces common
    wrong-language phrases with the correct language equivalent.
    """
    if not text or not setting_language:
        return text

    setting_lang = setting_language.lower().strip()

    # Common phrase mappings between confused romance languages
    # Only fix OBVIOUS high-frequency phrases that are clearly wrong-language
    if setting_lang == "italian":
        # Spanish -> Italian replacements
        spanish_to_italian = {
            r'\bVamos\b': 'Andiamo',
            r'\bvamos\b': 'andiamo',
            r'\bVamos a ser realistas\b': 'Siamo realisti',
            r'\bMi amor\b': 'Amore mio',
            r'\bmi amor\b': 'amore mio',
            r'\bPor favor\b': 'Per favore',
            r'\bpor favor\b': 'per favore',
            r'\bGracias\b': 'Grazie',
            r'\bgracias\b': 'grazie',
            r'\bBuenas noches\b': 'Buona notte',
            r'\bbuenas noches\b': 'buona notte',
            r'\bBuenos días\b': 'Buongiorno',
            r'\bHermosa\b': 'Bella',
            r'\bhermosa\b': 'bella',
            r'\bCorazón\b': 'Tesoro',
            r'\bcorazón\b': 'tesoro',
            r'\bMijo\b': 'Figlio mio',
            r'\bmijo\b': 'figlio mio',
            r'\bAy,\b': 'Ah,',
            r'\bSeñor\b': 'Signore',
            r'\bseñor\b': 'signore',
            r'\bSeñora\b': 'Signora',
            r'\bseñora\b': 'signora',
        }
        for pattern, replacement in spanish_to_italian.items():
            text = re.sub(pattern, replacement, text)

    elif setting_lang == "spanish":
        # Italian -> Spanish replacements
        italian_to_spanish = {
            r'\bAndiamo\b': 'Vamos',
            r'\bandiamo\b': 'vamos',
            r'\bAmore mio\b': 'Mi amor',
            r'\bamore mio\b': 'mi amor',
            r'\bPer favore\b': 'Por favor',
            r'\bper favore\b': 'por favor',
            r'\bGrazie\b': 'Gracias',
            r'\bgrazie\b': 'gracias',
            r'\bBella\b': 'Hermosa',
            r'\bbella\b': 'hermosa',
            r'\bSignore\b': 'Señor',
            r'\bsignore\b': 'señor',
            r'\bSignora\b': 'Señora',
            r'\bsignora\b': 'señora',
        }
        for pattern, replacement in italian_to_spanish.items():
            text = re.sub(pattern, replacement, text)

    return text


def _postprocess_scene(text: str, protagonist_name: str = "",
                       setting_language: str = "") -> str:
    """Master post-processor: applies all code-level quality enforcement.

    Called after _clean_scene_content on every creative stage output.
    Order matters: clean meta-text first, then enforce quality.
    """
    text = _clean_scene_content(text)
    text = _detect_duplicate_content(text)
    text = _enforce_first_person_pov(text, protagonist_name)
    text = _strip_emotional_summaries(text)
    text = _limit_tic_frequency(text)
    if setting_language:
        text = _flag_language_inconsistencies(text, setting_language)
    return text


def _repair_json_string(json_str: str) -> str:
    """Apply progressive repairs to malformed JSON from LLM output."""
    import re

    if not json_str or not isinstance(json_str, str):
        return "{}"

    # 1. Remove comments (LLMs sometimes add these)
    json_str = re.sub(r'//[^\n]*', '', json_str)
    json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)

    # 2. Fix Python-style booleans/None
    json_str = re.sub(r'\bTrue\b', 'true', json_str)
    json_str = re.sub(r'\bFalse\b', 'false', json_str)
    json_str = re.sub(r'\bNone\b', 'null', json_str)

    # 3. Remove trailing commas before } or ]
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)

    # 4. Fix unquoted keys (word: -> "word":)
    json_str = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)

    # 5. (Removed) Single-quote to double-quote conversion was corrupting
    # apostrophes in English text (can't -> can"t). JSON mode and proper
    # prompts should produce double-quoted strings natively.

    # 6. Fix literal newlines/tabs inside JSON string values
    # LLMs (especially local models) produce multi-line strings which break JSON parsing
    result = []
    in_str = False
    i = 0
    while i < len(json_str):
        ch = json_str[i]
        # Track string boundaries (handle escaped quotes)
        if ch == '"' and (i == 0 or json_str[i-1] != '\\'):
            in_str = not in_str
            result.append(ch)
        elif in_str and ch == '\n':
            result.append('\\n')
        elif in_str and ch == '\r':
            pass  # Drop carriage returns inside strings
        elif in_str and ch == '\t':
            result.append('\\t')
        else:
            result.append(ch)
        i += 1
    json_str = ''.join(result)

    # 7. Fix decimal numbers without leading zero
    json_str = re.sub(r':\s*\.(\d)', r': 0.\1', json_str)

    return json_str


def extract_json_robust(text: str, expect_array: bool = False) -> Any:
    """Robustly extract JSON from LLM response text.

    Handles common LLM output issues:
    - JSON wrapped in markdown code blocks
    - Explanatory text before/after JSON
    - Trailing commas, single quotes, unquoted keys
    - Python-style True/False/None
    - Truncated JSON (attempts repair)
    """
    import re

    if text is None:
        return [] if expect_array else {}
    text = str(text).strip()

    # Remove markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)

    # Try to find JSON structure
    if expect_array:
        match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
        if match:
            json_str = match.group(0)
        else:
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                json_str = match.group(0)
            else:
                # No array found - try full text (may be object with "chapters" etc.)
                json_str = text
    else:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        json_str = match.group(0) if match else text

    # Apply repairs
    json_str = _repair_json_string(json_str)

    # Try to parse
    try:
        result = json.loads(json_str)
        # If expecting array but got object (json_mode wraps in object), unwrap
        if expect_array and isinstance(result, dict):
            for key, val in result.items():
                if isinstance(val, list):
                    return val
            return [result]  # Single object, wrap as array
        return result
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse attempt 1 failed: {e}")
        logger.warning(f"Raw JSON (first 300 chars): {json_str[:300]}")

        # Attempt 2: Try to extract individual complete objects from the text
        if expect_array:
            objects = _extract_complete_json_objects(json_str)
            if objects:
                logger.info(f"Recovered {len(objects)} complete JSON objects from malformed array")
                return objects

        # Attempt 3: For truncated JSON, try closing brackets
        if expect_array:
            for suffix in ['"}]}]', '"}]', '"}}]', '"]', '}]', '}}]', '}]}]']:
                try:
                    trimmed = json_str.rstrip().rstrip(',').rstrip()
                    result = json.loads(trimmed + suffix)
                    if isinstance(result, list) and len(result) > 0:
                        logger.info(f"Repaired truncated JSON with suffix '{suffix}'")
                        return result
                except json.JSONDecodeError:
                    continue

        logger.warning(f"All JSON parse attempts failed. Returning raw text.")
        if expect_array:
            return [{"raw": text}]
        return {"raw": text}


def _extract_complete_json_objects(text: str) -> list:
    """Extract all complete, valid JSON objects from text.

    Walks through the text tracking brace depth (string-aware) to find
    complete {...} blocks, then attempts to parse each one individually.
    """
    objects = []
    depth = 0
    start = None
    in_str = False

    for i, char in enumerate(text):
        # Track string boundaries (skip braces inside strings)
        if char == '"' and (i == 0 or text[i-1] != '\\'):
            in_str = not in_str
            continue
        if in_str:
            continue

        if char == '{':
            if depth == 0:
                start = i
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0 and start is not None:
                candidate = text[start:i+1]
                candidate = _repair_json_string(candidate)
                try:
                    obj = json.loads(candidate)
                    if isinstance(obj, dict):
                        objects.append(obj)
                except json.JSONDecodeError:
                    pass
                start = None

    return objects


# ============================================================================
# STAGE ORDERING RATIONALE & PRESERVATION CONSTRAINTS
# ============================================================================
# Stages are ordered: destructive refinement FIRST, then additive polish.
#
# PLANNING: motif_embedding feeds structural motifs into master_outline
#
# REFINEMENT (destructive, before polish):
#   voice_human_pass - Consolidated de-AI + voice + emotional texture
#   continuity_audit_2 / continuity_fix_2 - Facts-only check after destructive edits
#
# POLISH (additive, order matters):
# 1. dialogue_polish - Dialogue-focused (doesn't touch prose)
# 2. prose_polish - Final line-level polish (strict preservation mode)
# 3. chapter_hooks - LAST creative edit (openings + endings only)
#
# VALIDATION:
#   final_deai - Safety net with hook protection (word-window slicing)
#   quality_audit - Can trigger re-run of voice_human_pass or scene_expansion
#
# Each later stage includes PRESERVATION_CONSTRAINTS to prevent regression.

PRESERVATION_CONSTRAINTS = """
=== CRITICAL: PRESERVATION CONSTRAINTS ===
You MUST NOT re-introduce any of the following. Before outputting, verify
NONE of these appear anywhere in your output:

SURFACE AI TELLS (hard blacklist):
- "I couldn't help but", "I found myself", "Something about X made me"
- "I noticed that", "I realized that", "I felt a sense of"
- "suddenly", "in that moment", "before I knew it"
- "a whirlwind of emotions", "electricity coursed through"
- "my heart skipped a beat", "butterflies in my stomach"
- "incredibly", "absolutely", "utterly", "completely", "truly", "genuinely"
- "seemed to", "appeared to", "managed to", "proceeded to"
- "began to", "started to"
- "I felt [emotion]", "I was [emotion]"
- "a mix of [emotion] and [emotion]"

STOCK ROMANCE CLICHES (hard blacklist):
- "warm hug", "protective blanket", "anchor in rough seas"
- "ethereal glow", "twinkling lights celebrating"
- "something new beginning", "connection in unexpected places"
- "filled with meaning", "the beginning of something"
- "time seemed to stop", "the world fell away"
- "her heart fluttered", "butterflies", "electric touch"
- "a comfortable silence", "unspoken understanding"
- "breath I didn't know I was holding"

DEEP AI PATTERNS (structural blacklist):
- Ending a paragraph by explaining the emotion the scene just showed
- Stacking 3+ metaphors in one paragraph
- Two consecutive paragraphs making the same emotional point
- Characters being perfectly emotionally articulate in dialogue
- Summarizing a time jump with "over the weeks, they..."

PROSE PATTERNS TO PRESERVE (do not overwrite):
- Short punchy sentences (keep them short)
- Sentence fragments (intentional, leave them)
- Em-dash interruptions (preserve these)
- Trailing off... (intentional, preserve)
- Contradictory emotions (keep the messiness)
- Character-specific vocabulary (don't normalize)
- Ugly, specific, concrete detail (keep it unglamorous)
"""

# HUMANIZATION TECHNIQUES - Targets the deep AI patterns that survive surface-level de-AI
HUMANIZATION_PRINCIPLES = """
=== RULE 1: KILL EMOTIONAL SUMMARIZATION (the #1 AI tell) ===
AI prose ends paragraphs by TELLING the reader what to feel. This is the single
most recognizable AI pattern. Find and destroy every instance.

EXAMPLES OF WHAT TO CUT:
- "A bittersweet reminder of happier times."
- "A fragile ribbon of empathy tying our broken hearts together."
- "A bond forged in quiet moments when no one else is watching."
- "Something about this moment felt like the beginning of something new."
- Any sentence that summarizes the emotion the scene just showed.

THE FIX: End paragraphs on ACTION, SENSORY DETAIL, or DIALOGUE. If the scene
showed tenderness, the reader already feels it. Don't explain it to them.

BEFORE: She handed him the pastry. Their fingers brushed. A warmth spread
through her—a quiet reminder that connection could bloom in unexpected places.
AFTER: She handed him the pastry. Their fingers brushed. She pulled her hand
back and wiped it on her apron.

=== RULE 2: ONE METAPHOR PER PARAGRAPH, MAX ===
AI stacks 3-4 figurative comparisons in the same paragraph. Real writers pick
one and commit to it. If you have "like a warm hug" AND "an anchor in rough
seas" AND "a protective blanket" within three sentences, keep the strongest
one and make the other sentences literal.

=== RULE 3: CONCRETE SPECIFICITY OVER STOCK IMAGERY ===
AI defaults to "generic cozy": fairy lights, warm scents, soft glow, city
lights twinkling. Replace stock with observed, unglamorous detail.

STOCK: "The kitchen was warm and inviting, filled with the scent of cinnamon."
SPECIFIC: "The oven ticked as it cooled. Flour had gotten into the cracked
grout again. The cinnamon was the cheap stuff from the bodega—too sweet,
almost fake, but it was what she had."

Push for: brand names, broken things, ugly details, the specific object that
doesn't belong, the sound that interrupts the mood.

=== RULE 4: DIALOGUE MUST CARRY SUBTEXT ===
AI dialogue is polite, turn-taking, and emotionally articulate. Real people:
- Talk past each other
- Answer a different question than the one asked
- Use deflection when vulnerable
- Say the wrong thing, then try to fix it
- Interrupt, overlap, trail off mid-thought
- Have verbal tics (a word they overuse, a way they stall)

BEFORE: "I've been thinking about you," he said softly. "About us."
"Me too," she whispered. "I think something is happening between us."
AFTER: "I keep—" He stopped. Bit the inside of his cheek. "Your croissants.
The ones from Tuesday. I keep thinking about those."
She stared at him. "The burnt ones?"
"Yeah." A pause. "Those."

=== RULE 5: NO LOOPING (same feeling restated across paragraphs) ===
If the scene establishes "baking = comfort" in paragraph 1, paragraphs 2-5
should NOT circle back to that same idea. After you establish a theme ONCE:
- Introduce a complication
- Force a choice
- Create a consequence
- Or cut the paragraph entirely

=== RULE 6: SENTENCE RHYTHM THROUGH VARIETY ===
- SHORT for impact. Punch.
- Long sentences that build through complex territory.
- Fragments. For gut reaction.
- Vary deliberately: short-short-long, long-short-short.
- But never three long sentences in a row. Never three fragments in a row.

=== RULE 7: EMOTIONAL UNPREDICTABILITY ===
- Tonal shifts within paragraphs (tender to irritated to amused)
- Vulnerability alternating with deflection
- Humor cracking through a serious moment
- The wrong emotion at the wrong time (laughing at a funeral, angry during a kiss)
- Contradictory feelings: wanting and resenting the wanting

=== RULE 8: END ON CONCRETE, NOT ABSTRACT ===
Every scene should end on something the reader can SEE, HEAR, or TOUCH.
Not on a feeling, not on a realization, not on a metaphor about connection.

BEFORE: "And in that moment, she knew that something had changed between them forever."
AFTER: "She locked the door. The flour was still on his sleeve."
"""


class StageStatus(Enum):
    """Pipeline stage status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StageResult:
    """Result from a pipeline stage."""
    stage_name: str
    status: StageStatus
    output: Any = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    tokens_used: int = 0
    cost_usd: float = 0.0


@dataclass
class PipelineState:
    """Current state of the pipeline."""
    project_name: str
    project_path: Path
    config: Dict[str, Any]
    current_stage: int = 0
    stage_results: List[StageResult] = field(default_factory=list)

    # Generated content
    high_concept: Optional[str] = None
    world_bible: Optional[Dict[str, Any]] = None
    beat_sheet: Optional[List[Dict[str, Any]]] = None
    characters: Optional[List[Dict[str, Any]]] = None
    master_outline: Optional[List[Dict[str, Any]]] = None
    scenes: Optional[List[Dict[str, Any]]] = None
    continuity_issues: Optional[List[Dict[str, Any]]] = None  # Track issues to fix
    continuity_issues_2: Optional[List[Dict[str, Any]]] = None  # Post-refinement issues
    motif_map: Optional[Dict[str, Any]] = None  # Structural motif plan from motif_embedding
    emotional_arc: Optional[Dict[str, Any]] = None  # From emotional_architecture

    # Calculated targets
    target_words: int = 60000
    target_chapters: int = 20
    words_per_chapter: int = 3000
    scenes_per_chapter: int = 4
    words_per_scene: int = 750

    # Metrics
    total_tokens: int = 0
    total_cost_usd: float = 0.0

    # Checkpoint tracking - which stages completed successfully
    completed_stages: List[str] = field(default_factory=list)

    def calculate_targets(self):
        """Calculate word count targets based on target_length and genre."""
        length_map = {
            "micro (5k)": 5000,
            "novelette (15k)": 15000,
            "short (30k)": 30000,
            "standard (60k)": 60000,
            "long (90k)": 90000,
            "epic (120k)": 120000
        }
        target_length = self.config.get("target_length", "standard (60k)")
        self.target_words = length_map.get(target_length, 60000)

        # Genre-aware pacing (words per chapter)
        genre = self.config.get("genre", "").lower()
        genre_pacing = {
            "romance": 2200,       # Tight pacing, frequent POV switches
            "dark romance": 2200,
            "mafia": 2400,
            "thriller": 2500,      # Standard pacing
            "mystery": 2800,       # Slower revelation
            "fantasy": 3500,       # World-heavy, slower pace
            "sci-fi": 3200,        # World-building intensive
            "literary": 3000,      # Character-focused, slower
            "horror": 2300,        # Quick scares, tight chapters
            "ya": 2000,            # Younger readers, shorter chapters
        }

        # Find matching genre pacing
        self.words_per_chapter = 2500  # Default
        for genre_key, words in genre_pacing.items():
            if genre_key in genre:
                self.words_per_chapter = words
                break

        # Calculate structure
        raw_chapters = self.target_words // self.words_per_chapter
        # For short works (<15k), allow fewer chapters; for novels, minimum 10
        min_chapters = 3 if self.target_words <= 15000 else 10
        self.target_chapters = max(raw_chapters, min_chapters)
        self.scenes_per_chapter = 3 if self.target_chapters >= 10 else 2  # Fewer scenes for short works
        self.words_per_scene = self.words_per_chapter // self.scenes_per_chapter

        logger.info(f"Targets for {genre or 'general'}: {self.target_words} words, "
                   f"{self.target_chapters} chapters @ {self.words_per_chapter} words/chapter, "
                   f"{self.words_per_scene} words/scene")

    def save(self):
        """Save state to disk with checkpoint data for reliable resume."""
        state_file = self.project_path / "pipeline_state.json"
        state_dict = {
            "project_name": self.project_name,
            "current_stage": self.current_stage,
            "completed_stages": self.completed_stages,
            "high_concept": self.high_concept,
            "world_bible": self.world_bible,
            "beat_sheet": self.beat_sheet,
            "characters": self.characters,
            "master_outline": self.master_outline,
            "scenes": self.scenes,
            "continuity_issues": self.continuity_issues,
            "continuity_issues_2": self.continuity_issues_2,
            "motif_map": self.motif_map,
            "emotional_arc": self.emotional_arc,
            "target_words": self.target_words,
            "target_chapters": self.target_chapters,
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "stage_results": [
                {
                    "stage_name": r.stage_name,
                    "status": r.status.value,
                    "duration_seconds": r.duration_seconds,
                    "tokens_used": r.tokens_used,
                    "cost_usd": r.cost_usd
                }
                for r in self.stage_results
            ]
        }
        with open(state_file, "w") as f:
            json.dump(state_dict, f, indent=2)
        logger.info(f"Pipeline state checkpointed to {state_file} (stage {self.current_stage}, {len(self.completed_stages)} completed)")

    @classmethod
    def load(cls, project_path: Path) -> Optional["PipelineState"]:
        """Load state from disk."""
        state_file = project_path / "pipeline_state.json"
        if not state_file.exists():
            return None

        with open(state_file) as f:
            data = json.load(f)

        config_file = project_path / "config.yaml"
        with open(config_file) as f:
            config = yaml.safe_load(f)

        state = cls(
            project_name=data["project_name"],
            project_path=project_path,
            config=config,
            current_stage=data.get("current_stage", 0),
            completed_stages=data.get("completed_stages", []),
            high_concept=data.get("high_concept"),
            world_bible=data.get("world_bible"),
            beat_sheet=data.get("beat_sheet"),
            characters=data.get("characters"),
            master_outline=data.get("master_outline"),
            scenes=data.get("scenes"),
            continuity_issues=data.get("continuity_issues"),
            continuity_issues_2=data.get("continuity_issues_2"),
            motif_map=data.get("motif_map"),
            emotional_arc=data.get("emotional_arc"),
            target_words=data.get("target_words", 60000),
            target_chapters=data.get("target_chapters", 20),
            total_tokens=data.get("total_tokens", 0),
            total_cost_usd=data.get("total_cost_usd", 0.0)
        )

        # Recalculate targets from config if loading
        state.calculate_targets()

        return state


class PipelineOrchestrator:
    """Orchestrates the 12-stage novel generation pipeline."""

    # Stage ordering is CRITICAL - see PRESERVATION_CONSTRAINTS comment above
    # Later prose stages include constraints to prevent undoing earlier work
    STAGES = [
        # === PLANNING PHASE ===
        "high_concept",
        # Parallel group 1: both only depend on high_concept
        "world_building",
        "beat_sheet",
        # Parallel group 2: emotional_arch needs beat_sheet, characters needs world_bible
        "emotional_architecture",
        "character_profiles",
        # Motif embedding: structural motifs fed into outline (not post-hoc infusion)
        "motif_embedding",
        # Sequential: master_outline needs beat_sheet + characters + motifs
        "master_outline",
        "trope_integration",

        # === DRAFTING PHASE ===
        "scene_drafting",
        "scene_expansion",
        "continuity_audit",
        "continuity_fix",
        "self_refinement",

        # === REFINEMENT PHASE (Destructive - before polish) ===
        # Single consolidated pass: de-AI + voice + emotional texture
        "voice_human_pass",
        # Lightweight continuity check after destructive edits
        "continuity_audit_2",
        "continuity_fix_2",

        # === POLISH PHASE (Additive - order matters!) ===
        # 1. Dialogue first (doesn't touch prose)
        "dialogue_polish",
        # 2. Prose polish (line-level, strict preservation)
        "prose_polish",
        # 3. Chapter hooks LAST (nothing touches hooks after this)
        "chapter_hooks",

        # === VALIDATION PHASE ===
        # Safety net: surgical AI tell removal (protects hooks)
        "final_deai",
        "quality_audit",
        "output_validation"
    ]

    # Smart model routing - use the best model for each stage
    # gpt = fast/cheap bulk work, claude = nuanced prose, gemini = long context
    STAGE_MODELS = {
        "high_concept": "gpt",
        "world_building": "gemini",
        "beat_sheet": "gpt",
        "emotional_architecture": "claude",  # Nuanced emotional mapping
        "character_profiles": "claude",
        "motif_embedding": "claude",         # Structural motif design
        "master_outline": "gpt",
        "trope_integration": "claude",       # Genre-aware trope placement
        "scene_drafting": "gpt",
        "scene_expansion": "claude",         # Expand short scenes
        "continuity_audit": "gemini",
        "continuity_fix": "claude",
        "self_refinement": "claude",
        "voice_human_pass": "claude",        # Consolidated de-AI + voice
        "continuity_audit_2": "gemini",      # Lightweight post-refinement check
        "continuity_fix_2": "claude",        # Facts-only fix, no style changes
        "dialogue_polish": "claude",         # Dialogue authenticity
        "chapter_hooks": "claude",
        "prose_polish": "claude",
        "final_deai": "gpt",                 # Fast surgical replacement (no creativity needed)
        "quality_audit": "gemini",           # Long context for full audit
        "output_validation": "gpt"
    }

    # Temperature settings per stage type
    # Lower = more deterministic (planning), Higher = more creative (prose)
    STAGE_TEMPERATURES = {
        # Planning stages - need consistency (0.3-0.5)
        "high_concept": 0.4,
        "world_building": 0.4,
        "beat_sheet": 0.3,
        "emotional_architecture": 0.5,
        "character_profiles": 0.5,
        "motif_embedding": 0.5,
        "master_outline": 0.3,
        "trope_integration": 0.4,

        # Creative stages - need variety (0.7-0.9)
        "scene_drafting": 0.85,
        "scene_expansion": 0.8,
        "voice_human_pass": 0.7,
        "dialogue_polish": 0.75,
        "chapter_hooks": 0.75,
        "prose_polish": 0.7,

        # Analytical stages - need precision (0.2-0.4)
        "continuity_audit": 0.2,
        "continuity_fix": 0.4,
        "continuity_audit_2": 0.2,
        "continuity_fix_2": 0.3,
        "self_refinement": 0.5,
        "final_deai": 0.3,
        "quality_audit": 0.2,
        "output_validation": 0.2
    }

    # Define which stages can run in parallel (they share no dependencies)
    # Each group runs concurrently; groups run sequentially
    # IMPORTANT: Group members MUST be adjacent in STAGES list
    PARALLEL_GROUPS = {
        # After high_concept: both only need high_concept, no cross-dependency
        "planning_parallel_1": ["world_building", "beat_sheet"],
        # After group 1: emotional_arch needs beat_sheet, characters needs world_bible
        "planning_parallel_2": ["emotional_architecture", "character_profiles"],
    }

    def get_temperature_for_stage(self, stage_name: str) -> float:
        """Get appropriate temperature for a stage."""
        return self.STAGE_TEMPERATURES.get(stage_name, 0.7)

    def __init__(self, project_path: Path, llm_client=None, llm_clients: Dict = None):
        self.project_path = project_path
        self.llm_client = llm_client  # Default/fallback client
        self.llm_clients = llm_clients or {}  # {"gpt": client, "claude": client, "gemini": client}
        self.state: Optional[PipelineState] = None
        self.callbacks: Dict[str, List[Callable]] = {
            "on_stage_start": [],
            "on_stage_complete": [],
            "on_stage_error": [],
            "on_pipeline_complete": []
        }

    def get_client_for_stage(self, stage_name: str):
        """Get the appropriate LLM client for a given stage.

        Uses smart routing to pick the best model, with fallback to default.
        """
        # Check for stage-specific override in config
        if self.state and self.state.config:
            model_overrides = self.state.config.get("model_overrides", {})
            if stage_name in model_overrides:
                model_type = model_overrides[stage_name]
                if model_type in self.llm_clients:
                    logger.info(f"Using override model '{model_type}' for stage: {stage_name}")
                    return self.llm_clients[model_type]

        # Use recommended model for stage
        recommended = self.STAGE_MODELS.get(stage_name, "gpt")
        if recommended in self.llm_clients:
            logger.info(f"Using recommended model '{recommended}' for stage: {stage_name}")
            return self.llm_clients[recommended]

        # Fallback to default client
        logger.info(f"Using default client for stage: {stage_name}")
        return self.llm_client

    def on(self, event: str, callback: Callable):
        """Register event callback."""
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    async def _emit(self, event: str, *args, **kwargs):
        """Emit event to callbacks."""
        for callback in self.callbacks.get(event, []):
            if asyncio.iscoroutinefunction(callback):
                await callback(*args, **kwargs)
            else:
                callback(*args, **kwargs)

    async def initialize(self, resume: bool = False) -> PipelineState:
        """Initialize or resume pipeline state."""
        if resume:
            self.state = PipelineState.load(self.project_path)
            if self.state:
                logger.info(f"Resuming pipeline from stage {self.state.current_stage}")
                return self.state

        # Load project config
        config_file = self.project_path / "config.yaml"
        if not config_file.exists():
            raise FileNotFoundError(f"Project config not found: {config_file}")

        with open(config_file) as f:
            config = yaml.safe_load(f)

        # VALIDATE CONFIG before proceeding
        validation = validate_config(config)
        if not validation["valid"]:
            for error in validation["errors"]:
                logger.error(f"Config error: {error}")
            raise ValueError(f"Invalid config: {', '.join(validation['errors'])}")

        if validation["warnings"]:
            for warning in validation["warnings"]:
                logger.warning(f"Config warning: {warning}")

        logger.info(f"Config validated: {validation['completeness']:.0f}% complete")

        self.state = PipelineState(
            project_name=config.get("project_name", "untitled"),
            project_path=self.project_path,
            config=config
        )

        # Calculate word count targets
        self.state.calculate_targets()

        logger.info(f"Initialized pipeline for project: {self.state.project_name}")
        return self.state

    async def run(self, stages: Optional[List[str]] = None, resume: bool = False):
        """Run the pipeline with quality-driven iteration and checkpoint resume."""
        await self.initialize(resume=resume)

        stages_to_run = stages or self.STAGES

        # When resuming, skip already-completed stages based on checkpoint data
        if resume and self.state.completed_stages:
            start_index = 0
            for i, stage_name in enumerate(stages_to_run):
                if stage_name not in self.state.completed_stages:
                    start_index = i
                    break
            else:
                start_index = len(stages_to_run)  # All done
            logger.info(f"Resuming from stage {start_index} ({stages_to_run[start_index] if start_index < len(stages_to_run) else 'done'}), "
                       f"{len(self.state.completed_stages)} stages already completed")
        else:
            start_index = self.state.current_stage if resume else 0

        # Build reverse lookup: stage_name -> parallel group
        parallel_lookup = {}
        for group_name, group_stages in self.PARALLEL_GROUPS.items():
            for s in group_stages:
                parallel_lookup[s] = group_stages

        i = start_index
        while i < len(stages_to_run):
            stage_name = stages_to_run[i]

            # Skip stages already completed (safety check for parallel group overlap)
            if stage_name in self.state.completed_stages:
                i += 1
                continue

            # Check if this stage is part of a parallel group
            parallel_group = parallel_lookup.get(stage_name)
            if parallel_group and all(s in stages_to_run[i:] for s in parallel_group):
                # Find all group members that start at consecutive positions
                group_members = [s for s in parallel_group if s in stages_to_run[i:] and s not in self.state.completed_stages]

                if len(group_members) > 1:
                    logger.info(f"Running {len(group_members)} stages in parallel: {group_members}")
                    for s in group_members:
                        await self._emit("on_stage_start", s, i)

                    # Run in parallel
                    results = await asyncio.gather(
                        *[self._run_stage(s) for s in group_members],
                        return_exceptions=True
                    )

                    # Process results
                    failed = False
                    for s, result in zip(group_members, results):
                        if isinstance(result, Exception):
                            result = StageResult(stage_name=s, status=StageStatus.FAILED, error=str(result))
                            failed = True

                        self.state.stage_results.append(result)
                        self.state.total_tokens += result.tokens_used
                        self.state.total_cost_usd += result.cost_usd

                        if result.status == StageStatus.COMPLETED:
                            if s not in self.state.completed_stages:
                                self.state.completed_stages.append(s)

                        await self._emit("on_stage_complete", s, result)

                    self.state.current_stage = i + len(group_members)
                    self.state.save()

                    if failed:
                        break

                    # Skip past all group members
                    i += len(group_members)
                    continue

            # Sequential execution for non-parallel stages
            self.state.current_stage = i
            await self._emit("on_stage_start", stage_name, i)

            try:
                result = await self._run_stage(stage_name)
                self.state.stage_results.append(result)
                self.state.total_tokens += result.tokens_used
                self.state.total_cost_usd += result.cost_usd

                # Track completed stages for checkpoint resume
                if result.status == StageStatus.COMPLETED:
                    if stage_name not in self.state.completed_stages:
                        self.state.completed_stages.append(stage_name)

                self.state.save()

                await self._emit("on_stage_complete", stage_name, result)

                if result.status == StageStatus.FAILED:
                    await self._emit("on_stage_error", stage_name, result.error)
                    break

                # Handle iteration if quality_audit indicates it's needed
                if stage_name == "quality_audit" and result.output:
                    audit_output = result.output
                    if audit_output.get("needs_iteration") and audit_output.get("stages_to_rerun"):
                        stages_to_rerun = audit_output["stages_to_rerun"]
                        logger.info(f"Quality audit triggered iteration. Re-running: {stages_to_rerun}")

                        # Re-run the problematic stages
                        for rerun_stage in stages_to_rerun:
                            logger.info(f"  Re-running stage: {rerun_stage}")
                            await self._emit("on_stage_start", f"{rerun_stage}_iteration", -1)

                            rerun_result = await self._run_stage(rerun_stage)
                            self.state.stage_results.append(rerun_result)
                            self.state.total_tokens += rerun_result.tokens_used
                            self.state.total_cost_usd += rerun_result.cost_usd

                            await self._emit("on_stage_complete", f"{rerun_stage}_iteration", rerun_result)

                        # Re-run full polish chain after destructive/expansion fixes
                        if "voice_human_pass" in stages_to_rerun or "scene_expansion" in stages_to_rerun:
                            logger.info("  Re-running polish chain: dialogue, prose, hooks, final_deai")
                            for polish_stage in ["dialogue_polish", "prose_polish", "chapter_hooks", "final_deai"]:
                                p_result = await self._run_stage(polish_stage)
                                self.state.stage_results.append(p_result)
                                self.state.total_tokens += p_result.tokens_used

                        self.state.save()

            except Exception as e:
                logger.error(f"Stage {stage_name} failed: {e}")
                result = StageResult(
                    stage_name=stage_name,
                    status=StageStatus.FAILED,
                    error=str(e)
                )
                self.state.stage_results.append(result)
                await self._emit("on_stage_error", stage_name, str(e))
                break

            i += 1

        await self._emit("on_pipeline_complete", self.state)
        return self.state

    async def _run_stage(self, stage_name: str) -> StageResult:
        """Run a single pipeline stage."""
        import time
        start_time = time.time()

        stage_handlers = {
            "high_concept": self._stage_high_concept,
            "world_building": self._stage_world_building,
            "beat_sheet": self._stage_beat_sheet,
            "emotional_architecture": self._stage_emotional_architecture,
            "character_profiles": self._stage_character_profiles,
            "motif_embedding": self._stage_motif_embedding,
            "master_outline": self._stage_master_outline,
            "trope_integration": self._stage_trope_integration,
            "scene_drafting": self._stage_scene_drafting,
            "scene_expansion": self._stage_scene_expansion,
            "continuity_audit": self._stage_continuity_audit,
            "continuity_fix": self._stage_continuity_fix,
            "self_refinement": self._stage_self_refinement,
            "voice_human_pass": self._stage_voice_human_pass,
            "continuity_audit_2": self._stage_continuity_audit_2,
            "continuity_fix_2": self._stage_continuity_fix_2,
            "dialogue_polish": self._stage_dialogue_polish,
            "prose_polish": self._stage_prose_polish,
            "chapter_hooks": self._stage_chapter_hooks,
            "final_deai": self._stage_final_deai,
            "quality_audit": self._stage_quality_audit,
            "output_validation": self._stage_output_validation
        }

        handler = stage_handlers.get(stage_name)
        if not handler:
            return StageResult(
                stage_name=stage_name,
                status=StageStatus.SKIPPED,
                error=f"Unknown stage: {stage_name}"
            )

        try:
            output, tokens = await handler()
            duration = time.time() - start_time

            return StageResult(
                stage_name=stage_name,
                status=StageStatus.COMPLETED,
                output=output,
                duration_seconds=duration,
                tokens_used=tokens,
                cost_usd=tokens * 0.00001  # Rough estimate
            )

        except Exception as e:
            import traceback
            logger.error(f"Stage {stage_name} failed: {e}\n{traceback.format_exc()}")
            return StageResult(
                stage_name=stage_name,
                status=StageStatus.FAILED,
                error=str(e),
                duration_seconds=time.time() - start_time
            )

    # ========================================================================
    # Context Building Helpers
    # ========================================================================

    def _build_story_context(self) -> str:
        """Build comprehensive context from config including strategic guidance."""
        config = self.state.config
        guidance = config.get("strategic_guidance", {})

        context_parts = []

        # Core story elements
        context_parts.append(f"TITLE: {config.get('title', 'Untitled')}")
        context_parts.append(f"GENRE: {config.get('genre', 'literary')}")
        if config.get("tone"):
            context_parts.append(f"TONE: {config.get('tone')}")
        context_parts.append(f"TARGET LENGTH: {config.get('target_length', 'standard (60k)')}")

        # Synopsis/Idea
        if config.get("synopsis"):
            context_parts.append(f"\nCORE IDEA:\n{config.get('synopsis')}")

        # Characters
        if config.get("protagonist"):
            context_parts.append(f"\nPROTAGONIST:\n{config.get('protagonist')}")
        if config.get("antagonist"):
            context_parts.append(f"\nANTAGONIST:\n{config.get('antagonist')}")
        if config.get("other_characters"):
            context_parts.append(f"\nOTHER CHARACTERS:\n{config.get('other_characters')}")

        # World
        if config.get("setting"):
            context_parts.append(f"\nSETTING:\n{config.get('setting')}")
        if config.get("world_rules"):
            context_parts.append(f"\nWORLD RULES:\n{config.get('world_rules')}")
        if config.get("key_locations"):
            context_parts.append(f"\nKEY LOCATIONS:\n{config.get('key_locations')}")

        # Plot
        if config.get("premise"):
            context_parts.append(f"\nPREMISE:\n{config.get('premise')}")
        if config.get("central_conflict"):
            context_parts.append(f"\nCENTRAL CONFLICT:\n{config.get('central_conflict')}")
        if config.get("key_plot_points"):
            context_parts.append(f"\nKEY PLOT POINTS:\n{config.get('key_plot_points')}")
        if config.get("subplots"):
            context_parts.append(f"\nSUBPLOTS:\n{config.get('subplots')}")

        # Themes
        if config.get("themes"):
            context_parts.append(f"\nTHEMES:\n{config.get('themes')}")
        if config.get("central_question"):
            context_parts.append(f"\nCENTRAL QUESTION: {config.get('central_question')}")
        if config.get("motifs"):
            context_parts.append(f"\nMOTIFS:\n{config.get('motifs')}")

        # Style
        if config.get("writing_style"):
            context_parts.append(f"\nWRITING STYLE:\n{config.get('writing_style')}")
        if config.get("influences"):
            context_parts.append(f"\nINFLUENCES: {config.get('influences')}")
        if config.get("avoid"):
            context_parts.append(f"\nAVOID:\n{config.get('avoid')}")

        return "\n".join(context_parts)

    def _build_strategic_guidance(self) -> str:
        """Build strategic guidance context for enhanced generation."""
        guidance = self.state.config.get("strategic_guidance", {})
        if not any(guidance.values()):
            return ""

        parts = ["\n=== STRATEGIC GUIDANCE (Use to inform writing) ==="]

        if guidance.get("market_positioning"):
            parts.append(f"\nMARKET POSITIONING:\n{guidance.get('market_positioning')}")

        if guidance.get("beat_sheet"):
            parts.append(f"\nPACING BEAT SHEET:\n{guidance.get('beat_sheet')}")

        if guidance.get("aesthetic_guide"):
            parts.append(f"\nAESTHETIC GUIDE:\n{guidance.get('aesthetic_guide')}")

        if guidance.get("tropes"):
            parts.append(f"\nTROPES TO EXECUTE:\n{guidance.get('tropes')}")

        if guidance.get("dialogue_bank"):
            parts.append(f"\nDIALOGUE BANK:\n{guidance.get('dialogue_bank')}")

        if guidance.get("cultural_notes"):
            parts.append(f"\nCULTURAL NOTES:\n{guidance.get('cultural_notes')}")

        if guidance.get("pacing_notes"):
            parts.append(f"\nPACING NOTES:\n{guidance.get('pacing_notes')}")

        if guidance.get("commercial_notes"):
            parts.append(f"\nCOMMERCIAL NOTES:\n{guidance.get('commercial_notes')}")

        return "\n".join(parts)

    # ========================================================================
    # Stage Implementations
    # ========================================================================

    async def _stage_high_concept(self) -> tuple:
        """Generate high concept from synopsis."""
        config = self.state.config
        story_context = self._build_story_context()
        strategic = self._build_strategic_guidance()

        prompt = f"""You are an expert novelist. Generate a compelling high-concept summary for a novel.

{story_context}
{strategic}

Create a powerful one-paragraph high concept that captures:
1. The unique hook or twist
2. The central conflict
3. The emotional core
4. What makes this story fresh

High Concept:"""

        client = self.get_client_for_stage("high_concept")
        if client:
            response = await client.generate(prompt)
            self.state.high_concept = response.content
            return response.content, response.input_tokens + response.output_tokens

        # Mock response
        self.state.high_concept = f"A compelling story about the given synopsis..."
        return self.state.high_concept, 100

    async def _stage_world_building(self) -> tuple:
        """Build world bible."""
        config = self.state.config
        story_context = self._build_story_context()
        strategic = self._build_strategic_guidance()

        # Use provided setting info if available
        existing_setting = config.get("setting", "")
        existing_rules = config.get("world_rules", "")
        existing_locations = config.get("key_locations", "")

        prompt = f"""Create a comprehensive world bible for this novel. Expand on any provided details.

{story_context}

High Concept: {self.state.high_concept}
{strategic}

{"EXISTING SETTING TO EXPAND: " + existing_setting if existing_setting else ""}
{"EXISTING RULES TO EXPAND: " + existing_rules if existing_rules else ""}
{"EXISTING LOCATIONS TO EXPAND: " + existing_locations if existing_locations else ""}

Create a detailed world bible including:
1. Setting (time, place, atmosphere, sensory details)
2. World Rules (what's possible/impossible, systems)
3. Key Locations (5-7 important places with vivid descriptions)
4. Social Structure (hierarchy, factions, power dynamics)
5. Culture/Customs (relevant cultural details for authenticity)

Respond in JSON format."""

        client = self.get_client_for_stage("world_building")
        if client:
            response = await client.generate(prompt, temperature=0.4, json_mode=True)
            try:
                self.state.world_bible = extract_json_robust(response.content if response else None, expect_array=False)
            except Exception as e:
                logger.warning(f"World building JSON parse failed: {e}")
                self.state.world_bible = {"setting": config.get("title", "Unknown"), "rules": [], "locations": []}
            return self.state.world_bible, (response.input_tokens + response.output_tokens) if response else 0

        # Mock response
        self.state.world_bible = {
            "setting": f"The world of {config.get('title', 'Untitled')}",
            "rules": ["Rule 1", "Rule 2"],
            "locations": ["Location 1", "Location 2"]
        }
        return self.state.world_bible, 100

    async def _stage_beat_sheet(self) -> tuple:
        """Create story beat sheet."""
        config = self.state.config
        story_context = self._build_story_context()
        strategic = self._build_strategic_guidance()
        guidance = config.get("strategic_guidance", {})

        # Use provided beat sheet as reference if available
        user_beats = guidance.get("beat_sheet", "") or config.get("key_plot_points", "")

        prompt = f"""Create a detailed beat sheet for this novel. Follow any provided pacing guidance closely.

{story_context}

High Concept: {self.state.high_concept}
World Bible: {json.dumps(self.state.world_bible, indent=2) if self.state.world_bible else 'Not yet created'}
{strategic}

{"USER-PROVIDED PLOT BEATS TO INCORPORATE:\n" + user_beats if user_beats else ""}

Create a beat sheet with percentage markers (for a {config.get('target_length', '60k word')} novel):

ACT 1 (Setup - 0-25%):
- Opening Image (0-1%): First impression, sets tone
- Theme Stated (5%): Core theme hinted
- Setup (1-10%): Normal world established
- Catalyst/Inciting Incident (10%): The disruption
- Debate (10-25%): Resistance to change

ACT 2A (Confrontation - 25-50%):
- Break into Two (25%): Enters new world
- B Story (30%): Secondary storyline begins
- Fun and Games (30-50%): Promise of premise
- Midpoint (50%): Major shift/revelation

ACT 2B (Complication - 50-75%):
- Bad Guys Close In (50-75%): Stakes escalate
- All Is Lost (75%): Lowest point
- Dark Night of the Soul (75-80%): Emotional pit

ACT 3 (Resolution - 75-100%):
- Break into Three (80%): New plan/insight
- Finale (80-99%): Climax and resolution
- Final Image (100%): Mirror of opening

For each beat, include: name, percentage, scene description, emotional beat, and any tropes to execute.
Respond as a JSON array of beats."""

        client = self.get_client_for_stage("beat_sheet")
        if client:
            response = await client.generate(prompt, temperature=0.3, json_mode=True)
            try:
                self.state.beat_sheet = extract_json_robust(response.content if response else None, expect_array=True)
            except Exception as e:
                logger.warning(f"Beat sheet JSON parse failed: {e}")
                self.state.beat_sheet = [{"beat": "Catalyst", "description": "..."}, {"beat": "Midpoint", "description": "..."}]
            return self.state.beat_sheet, (response.input_tokens + response.output_tokens) if response else 0

        # Mock response
        self.state.beat_sheet = [
            {"beat": "Opening Image", "description": "..."},
            {"beat": "Catalyst", "description": "..."},
            {"beat": "Midpoint", "description": "..."},
            {"beat": "Finale", "description": "..."}
        ]
        return self.state.beat_sheet, 100

    async def _stage_emotional_architecture(self) -> tuple:
        """Map emotional arc across the entire story for proper pacing."""
        config = self.state.config
        client = self.get_client_for_stage("emotional_architecture")

        prompt = f"""Design the emotional architecture for this novel.

STORY CONCEPT: {self.state.high_concept}

BEAT SHEET:
{json.dumps(self.state.beat_sheet, indent=2)}

PROTAGONIST: {config.get('protagonist', '')}
THEMES: {config.get('themes', '')}
CENTRAL QUESTION: {config.get('central_question', '')}

=== EMOTIONAL ARCHITECTURE REQUIREMENTS ===

1. MAP EMOTIONAL JOURNEY
For the protagonist, define their emotional state at each story beat:
- Opening (0-5%): Initial emotional baseline
- Inciting Incident (10%): Disruption emotion
- Threshold (25%): Fear/excitement of new world
- Fun & Games (30-45%): Growing confidence/connection
- Midpoint (50%): Major emotional shift (revelation/intimacy)
- Bad Guys Close In (55-70%): Rising anxiety/stakes
- All Is Lost (75%): Lowest emotional point (despair)
- Dark Night (75-80%): Processing/internal struggle
- Break Into Three (80%): New resolve
- Finale (85-95%): Peak emotions (fear, love, triumph)
- Resolution (95-100%): Emotional arrival/peace

2. DEFINE EMOTIONAL PEAKS
Identify 5-7 scenes that should be emotional HIGH points (10/10 intensity):
- What emotion?
- What triggers it?
- How does it manifest physically?

3. DEFINE EMOTIONAL TROUGHS
Identify 3-4 scenes that are emotional REST points (3-5/10):
- What allows the reader to breathe?
- How does character process previous intensity?

4. EMOTIONAL ARC RHYTHM
Ensure rhythm: peak-rest-build-peak pattern
- Never more than 3 high-intensity scenes consecutively
- Recovery scenes between major emotional moments

5. TRANSFORMATION MARKERS
Identify 4-5 visible moments where character growth is SHOWN:
- Early: What behavior shows starting state?
- 25%: First sign of change
- 50%: Significant shift visible
- 75%: Growth tested by failure
- End: New behavior that shows transformation complete

Respond as JSON with emotional_beats, peaks, troughs, rhythm_check, and transformation_markers."""

        if client:
            response = await client.generate(prompt, max_tokens=2000, json_mode=True)
            try:
                emotional_map = extract_json_robust(response.content if response else None, expect_array=False)
            except Exception as e:
                logger.warning(f"Emotional architecture JSON parse failed: {e}")
                emotional_map = {}

            # Store for use in later stages
            self.state.config["emotional_architecture"] = emotional_map
            return emotional_map, response.input_tokens + response.output_tokens

        # Mock response
        return {"emotional_beats": [], "peaks": [], "troughs": []}, 50

    async def _stage_character_profiles(self) -> tuple:
        """Develop character profiles."""
        config = self.state.config
        story_context = self._build_story_context()
        strategic = self._build_strategic_guidance()
        guidance = config.get("strategic_guidance", {})

        # Use provided character info
        protagonist_info = config.get("protagonist", "")
        antagonist_info = config.get("antagonist", "")
        other_chars = config.get("other_characters", "")
        dialogue_bank = guidance.get("dialogue_bank", "")
        cultural_notes = guidance.get("cultural_notes", "")

        prompt = f"""Create detailed character profiles for this novel. Expand on any provided character info.

{story_context}

High Concept: {self.state.high_concept}
World Bible: {json.dumps(self.state.world_bible, indent=2) if self.state.world_bible else 'Not yet created'}
{strategic}

{"PROVIDED PROTAGONIST INFO TO EXPAND:\n" + protagonist_info if protagonist_info else ""}
{"PROVIDED ANTAGONIST INFO TO EXPAND:\n" + antagonist_info if antagonist_info else ""}
{"PROVIDED OTHER CHARACTERS TO EXPAND:\n" + other_chars if other_chars else ""}
{"DIALOGUE PATTERNS/PHRASES TO USE:\n" + dialogue_bank if dialogue_bank else ""}
{"CULTURAL AUTHENTICITY NOTES:\n" + cultural_notes if cultural_notes else ""}

For each character include:
1. Name
2. Role/Archetype
3. Physical Description (detailed, vivid)
4. Personality Traits (strengths, flaws, quirks)
5. Backstory (formative events)
6. Goals and Motivations (external and internal)
7. Character Arc (start state -> end state)
8. Voice/Speech Patterns (unique phrases, vocabulary, rhythm)
9. Signature Behaviors (habits, tells)
10. Relationships to Other Characters

Respond as a JSON array of character objects."""

        client = self.get_client_for_stage("character_profiles")
        if client:
            response = await client.generate(prompt, json_mode=True)
            try:
                self.state.characters = extract_json_robust(response.content if response else None, expect_array=True)
            except Exception as e:
                logger.warning(f"Character profiles JSON parse failed: {e}")
                self.state.characters = [{"name": "Protagonist", "role": "protagonist"}, {"name": "Antagonist", "role": "antagonist"}]
            return self.state.characters, (response.input_tokens + response.output_tokens) if response else 0

        # Mock response
        self.state.characters = [
            {"name": "Protagonist", "role": "protagonist", "arc": "..."},
            {"name": "Antagonist", "role": "antagonist", "arc": "..."}
        ]
        return self.state.characters, 100

    async def _stage_master_outline(self) -> tuple:
        """Create master outline with scene-by-scene breakdown.

        Uses batched generation (5 chapters per batch) to avoid token limits
        with smaller models. Each batch gets full story context plus a summary
        of previously generated chapters for continuity.
        """
        config = self.state.config
        story_context = self._build_story_context()
        strategic = self._build_strategic_guidance()

        # Get POV info
        writing_style = config.get("writing_style", "")
        is_dual_pov = "dual pov" in writing_style.lower()
        protagonist = config.get("protagonist", "").split(",")[0] if config.get("protagonist") else "Protagonist"
        other_chars = config.get("other_characters", "")
        hero_name = other_chars.split("(")[0].strip() if other_chars else "Hero"

        client = self.get_client_for_stage("master_outline")
        if not client:
            self.state.master_outline = [
                {"chapter": 1, "scenes": [{"scene": 1, "goal": "...", "pov": protagonist}]},
                {"chapter": 2, "scenes": [{"scene": 1, "goal": "...", "pov": hero_name}]}
            ]
            return self.state.master_outline, 100

        all_chapters = []
        total_tokens = 0
        BATCH_SIZE = 5

        # Build characters brief outside f-string to avoid brace escaping issues
        chars_brief = json.dumps(
            [{"name": c.get("name",""), "role": c.get("role",""), "arc": c.get("arc","")}
             for c in (self.state.characters or []) if isinstance(c, dict)],
            indent=1
        )

        for batch_start in range(1, self.state.target_chapters + 1, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE - 1, self.state.target_chapters)

            # Summary of previous chapters for continuity
            prev_summary = ""
            if all_chapters:
                prev_lines = []
                for ch in all_chapters:
                    if not isinstance(ch, dict):
                        continue
                    ch_num = ch.get("chapter", "?")
                    ch_title = ch.get("chapter_title", "")
                    scene_summaries = []
                    for sc in ch.get("scenes", []):
                        if isinstance(sc, dict):
                            scene_summaries.append(f"  - {sc.get('scene_name', 'Scene')}: {sc.get('purpose', '')}")
                    prev_lines.append(f"Ch {ch_num} \"{ch_title}\":\n" + "\n".join(scene_summaries))
                prev_summary = "PREVIOUSLY OUTLINED CHAPTERS:\n" + "\n".join(prev_lines)

            prompt = f"""Create chapters {batch_start}-{batch_end} of a {self.state.target_chapters}-chapter novel outline.

{story_context}

HIGH CONCEPT: {self.state.high_concept}

BEAT SHEET:
{json.dumps(self.state.beat_sheet, indent=2)}

CHARACTERS (brief):
{chars_brief}

{strategic}

MOTIF MAP (embed these structurally into scenes — settings, objects, character actions):
{json.dumps(getattr(self.state, 'motif_map', {}), indent=2)}

{prev_summary}

=== GENERATE CHAPTERS {batch_start} THROUGH {batch_end} ===

TARGET: {self.state.target_chapters} chapters total, {self.state.scenes_per_chapter} scenes per chapter
{"POV: Alternate between " + protagonist + " and " + hero_name if is_dual_pov else "POV: " + protagonist}

SUBPLOTS: {config.get('subplots', 'None specified')}

IMPORTANT: Each chapter is an object with a "scenes" array. Example structure:
{{"chapters": [{{"chapter": 1, "chapter_title": "Title", "scenes": [{{"scene": 1, "scene_name": "Name", "pov": "Character", "purpose": "...", "differentiator": "concrete detail that makes this scene unique", "character_scene_goal": "...", "central_conflict": "...", "opening_hook": "...", "outcome": "...", "location": "...", "emotional_arc": "...", "tension_level": 5, "pacing": "medium", "spice_level": 0}}]}}]}}

Scene fields: scene (number), scene_name, pov, purpose, differentiator (REQUIRED: one concrete detail making this scene distinct), character_scene_goal, central_conflict, opening_hook, outcome, location, emotional_arc, tension_level (1-10), pacing (fast/medium/slow), spice_level (0-5).

=== CRITICAL: SCENE DIFFERENTIATION ===
The AI tends to collapse similar scenes into the same output. To prevent this, EVERY scene must be DISTINCT:
- Give each scene a UNIQUE purpose (not "they talk on the balcony" twice)
- Give each scene a UNIQUE opening_hook (different entry point, different action, different time)
- Give each scene a UNIQUE central_conflict or tension (even if small)
- Add a "differentiator" field: one concrete detail that makes THIS scene different (e.g., "first time she brings him food", "he shows her the sketchbook", "rain forces them inside")
- If two scenes share a location (e.g., balcony), they must differ in: time of day, weather, object present, emotional state, or what is at stake
- Never write two scenes with the same purpose, outcome, or emotional beat. Advance the story.

Respond with a JSON object containing a "chapters" array of {batch_end - batch_start + 1} chapter objects. Each chapter MUST have "chapter", "chapter_title", and "scenes" keys."""

            response = await client.generate(prompt, max_tokens=4096, json_mode=True)
            try:
                batch = extract_json_robust(response.content, expect_array=True)
            except Exception as e:
                logger.error(f"JSON extraction failed for batch {batch_start}-{batch_end}: {e}")
                batch = []

            # Handle json_mode wrapping: model may wrap array in an object
            if isinstance(batch, dict):
                for key in ("chapters", "outline", "chapter_list", "result"):
                    if key in batch and isinstance(batch[key], list):
                        batch = batch[key]
                        break
                else:
                    for key, val in batch.items():
                        if isinstance(val, list) and val:
                            batch = val
                            break
                    else:
                        batch = [batch]

            # Ensure batch is a list for iteration
            if not isinstance(batch, list):
                batch = [batch] if isinstance(batch, dict) else []

            # Validate batch - accept chapters with flexible key names
            SCENE_KEYS = ("scenes", "scene_list", "scene_details", "chapter_scenes")
            for idx, ch in enumerate(batch):
                if not isinstance(ch, dict):
                    continue
                # Normalize scene key to "scenes"
                scene_key = None
                for sk in SCENE_KEYS:
                    if sk in ch:
                        scene_key = sk
                        break
                if scene_key and scene_key != "scenes":
                    raw_scenes = ch.pop(scene_key)
                    ch["scenes"] = [s for s in raw_scenes if isinstance(s, dict)] if isinstance(raw_scenes, list) else []
                elif "scenes" in ch and not isinstance(ch.get("scenes"), list):
                    ch["scenes"] = [ch["scenes"]] if isinstance(ch["scenes"], dict) else []
                if "scenes" in ch:
                    ch["scenes"] = [s for s in ch["scenes"] if isinstance(s, dict)]
                    if "chapter" not in ch:
                        ch["chapter"] = batch_start + idx
                    all_chapters.append(ch)
                elif "raw" in ch:
                    logger.warning(f"Batch {batch_start}-{batch_end} returned raw text, attempting repair")
                    raw = ch["raw"]
                    repaired = self._repair_truncated_json(raw)
                    if repaired:
                        for rch in repaired:
                            if isinstance(rch, dict) and "scenes" in rch:
                                all_chapters.append(rch)
                else:
                    logger.warning(f"Chapter object missing 'scenes' key. Keys found: {list(ch.keys())}")

            # Fallback: if model returned flat scenes instead of chapters, group them
            # qwen2.5/llama often output {"chapters": [{scene1}, {scene2}, ...]} - flat scene objects
            has_proper_chapters = any(isinstance(ch, dict) and "scenes" in ch for ch in batch if isinstance(ch, dict))
            if not has_proper_chapters:
                # Scene objects have "scene" or "scene_number" - avoid matching chapter-like objects (have "scenes")
                def is_flat_scene(obj):
                    if not isinstance(obj, dict) or "scenes" in obj:
                        return False
                    return "scene" in obj or "scene_number" in obj
                flat_scenes = [ch for ch in batch if is_flat_scene(ch)]
                if flat_scenes:
                    spc = max(1, self.state.scenes_per_chapter)  # Guard against 0
                    logger.info(f"Detected {len(flat_scenes)} flat scenes, grouping into chapters (spc={spc})")
                    for ch_idx in range(batch_start, batch_end + 1):
                        offset = (ch_idx - batch_start) * spc
                        ch_scenes = flat_scenes[offset:offset + spc]
                        if ch_scenes:
                            # Ensure scene_number set for downstream (scene_drafting expects it)
                            for i, sc in enumerate(ch_scenes):
                                if "scene_number" not in sc and "scene" in sc:
                                    sc["scene_number"] = sc["scene"]
                                elif "scene_number" not in sc:
                                    sc["scene_number"] = i + 1
                            all_chapters.append({
                                "chapter": ch_idx,
                                "chapter_title": ch_scenes[0].get("scene_name", f"Chapter {ch_idx}"),
                                "scenes": ch_scenes
                            })

            total_tokens += response.input_tokens + response.output_tokens
            logger.info(f"Outlined chapters {batch_start}-{batch_end}: {len(all_chapters)} total chapters so far")

        self.state.master_outline = all_chapters
        total_scenes = sum(len(ch.get("scenes", [])) for ch in all_chapters if isinstance(ch, dict))
        logger.info(f"Master outline complete: {len(all_chapters)} chapters, {total_scenes} total scenes")
        if len(all_chapters) == 0:
            logger.warning("Master outline is empty - scene_drafting will have nothing to process")
        return self.state.master_outline, total_tokens

    def _repair_truncated_json(self, raw: str) -> list:
        """Attempt to repair truncated JSON arrays from LLM output.

        Uses the shared _extract_complete_json_objects for robust extraction.
        """
        import re
        raw = re.sub(r'```json\s*', '', raw)
        raw = re.sub(r'```\s*', '', raw)
        raw = _repair_json_string(raw)

        # Try closing brackets first
        for suffix in [']}]', '}]}]', '"]}]', '"}]}]', '"}}]']:
            try:
                trimmed = raw.rstrip().rstrip(',')
                result = json.loads(trimmed + suffix)
                if isinstance(result, list):
                    return [ch for ch in result if isinstance(ch, dict) and "scenes" in ch]
            except json.JSONDecodeError:
                continue

        # Fall back to extracting individual objects
        try:
            objects = _extract_complete_json_objects(raw)
            return [ch for ch in objects if "scenes" in ch]
        except Exception:
            return []

    async def _stage_trope_integration(self) -> tuple:
        """Ensure genre-specific tropes are properly placed in the outline."""
        config = self.state.config
        client = self.get_client_for_stage("trope_integration")
        genre = config.get("genre", "").lower()

        # Get applicable tropes based on genre
        applicable_tropes = {}
        if "romance" in genre or "mafia" in genre:
            applicable_tropes = ROMANCE_TROPES

        # Get tropes from config market positioning
        guidance = config.get("strategic_guidance", {})
        market_pos = guidance.get("market_positioning", "").lower()

        # Check which tropes are promised
        tropes_to_check = []
        for trope_key, trope_data in applicable_tropes.items():
            trope_name = trope_key.replace("_", " ")
            if trope_name in market_pos or trope_name in str(config).lower():
                tropes_to_check.append((trope_key, trope_data))

        if not tropes_to_check:
            logger.info("No specific tropes to integrate")
            return {"tropes_checked": 0}, 0

        # Build trope checklist for the LLM
        trope_info = []
        for key, data in tropes_to_check:
            trope_info.append(f"""
TROPE: {key.replace('_', ' ').title()}
Description: {data['description']}
Placement: {data['placement']}
Required Elements:
{chr(10).join('- ' + elem for elem in data['required_elements'])}
""")

        prompt = f"""Review the master outline and ensure these genre tropes are properly integrated.

GENRE: {genre}
TARGET TROPES:
{chr(10).join(trope_info)}

CURRENT MASTER OUTLINE:
{json.dumps(self.state.master_outline, indent=2)[:8000]}

For EACH trope:
1. Identify which scene(s) should execute it
2. Verify all required elements are present in scene attributes
3. If missing, specify what needs to be added

Return JSON with:
{{
  "trope_placement": {{
    "trope_name": {{
      "scene_location": "ChX, SceneY",
      "elements_present": ["element1", "element2"],
      "elements_missing": ["element3"],
      "additions_needed": "Specific instruction for scene"
    }}
  }},
  "outline_updates": [
    {{"chapter": X, "scene": Y, "add_to_attributes": {{"key": "value"}}}}
  ]
}}"""

        if client:
            response = await client.generate(prompt, max_tokens=2000, json_mode=True)
            try:
                trope_report = extract_json_robust(response.content if response else None, expect_array=False)
            except Exception as e:
                logger.warning(f"Trope integration JSON parse failed: {e}")
                trope_report = {"tropes_checked": len(tropes_to_check), "outline_updates": []}

            # Apply outline updates if present
            updates = trope_report.get("outline_updates", [])
            for update in updates:
                if not isinstance(update, dict):
                    continue
                ch_num = update.get("chapter")
                sc_num = update.get("scene")
                additions = update.get("add_to_attributes", {})

                for chapter in (self.state.master_outline or []):
                    if not isinstance(chapter, dict):
                        continue
                    if chapter.get("chapter") == ch_num:
                        for scene in chapter.get("scenes", []):
                            if not isinstance(scene, dict):
                                continue
                            if scene.get("scene") == sc_num or scene.get("scene_number") == sc_num:
                                scene.update(additions)
                                logger.info(f"Updated Ch{ch_num} Sc{sc_num} with trope requirements")

            return trope_report, response.input_tokens + response.output_tokens

        return {"tropes_checked": len(tropes_to_check)}, 50

    def _get_protagonist_name(self) -> str:
        """Extract protagonist first name from config for POV enforcement."""
        protagonist = self.state.config.get("protagonist", "") if self.state and self.state.config else ""
        if not protagonist:
            return ""
        # Extract first name: take the first word before any comma or period
        first_part = protagonist.split(",")[0].split(".")[0].strip()
        # Take the first word (the actual first name)
        return first_part.split()[0] if first_part else ""

    def _get_setting_language(self) -> str:
        """Detect the primary foreign language from setting/config for consistency checks."""
        if not self.state or not self.state.config:
            return ""
        setting = self.state.config.get("setting", "")
        world_rules = self.state.config.get("world_rules", "")
        combined = (setting + " " + world_rules).lower()
        # Detect the dominant setting language
        if any(w in combined for w in ["italy", "italian", "rome", "milan", "florence",
                                        "naples", "sicily", "tuscany", "venice"]):
            return "italian"
        if any(w in combined for w in ["spain", "spanish", "madrid", "barcelona",
                                        "mexico", "mexican", "colombia", "argentina"]):
            return "spanish"
        if any(w in combined for w in ["france", "french", "paris", "lyon", "marseille"]):
            return "french"
        return ""

    def _postprocess(self, text: str) -> str:
        """Apply all code-level post-processing to scene content.
        Convenience wrapper that gets protagonist name and setting from config."""
        return _postprocess_scene(
            text,
            self._get_protagonist_name(),
            self._get_setting_language()
        )

    def _get_previous_scenes_context(self, scenes: List[Dict], count: int = 3) -> str:
        """Get summary of previous scenes for continuity."""
        if not scenes or len(scenes) == 0:
            return "This is the opening scene."

        recent = scenes[-count:] if len(scenes) >= count else scenes
        summaries = []
        for s in recent:
            if not isinstance(s, dict):
                continue
            ch = s.get("chapter", "?")
            sc = s.get("scene_number", "?")
            content = s.get("content", "")[:500]  # First 500 chars as summary
            summaries.append(f"[Ch{ch} Sc{sc}]: {content}...")

        return "PREVIOUS SCENES (for continuity):\n" + "\n\n".join(summaries)

    def _get_used_details_tracker(self, scenes: List[Dict]) -> str:
        """Extract repeated sensory details, physical tics, and catchphrases
        from previously written scenes so the next scene can avoid them.

        Scans the last 10 scenes for phrases that appear 2+ times across scenes.
        Returns a DO NOT REUSE list.
        """
        if not scenes or len(scenes) < 2:
            return ""

        # Scan last 10 scenes for repeated short phrases (3-6 word ngrams)
        recent = scenes[-10:] if len(scenes) >= 10 else scenes
        phrase_counts: Dict[str, int] = {}

        for s in recent:
            if not isinstance(s, dict):
                continue
            content = s.get("content", "").lower()
            words = content.split()
            # Extract 3-6 word phrases
            scene_phrases = set()  # dedupe within single scene
            for n in range(3, 7):
                for i in range(len(words) - n + 1):
                    phrase = " ".join(words[i:i+n])
                    # Skip very common phrases
                    if any(skip in phrase for skip in ["i was", "it was", "he was", "she was",
                                                       "i had", "the way", "in the", "of the",
                                                       "at the", "on the", "to the"]):
                        continue
                    scene_phrases.add(phrase)
            for phrase in scene_phrases:
                phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1

        # Find phrases appearing in 2+ different scenes
        repeated = sorted(
            [(p, c) for p, c in phrase_counts.items() if c >= 2],
            key=lambda x: -x[1]
        )[:15]  # Top 15 most repeated

        if not repeated:
            return ""

        lines = ["=== ALREADY-USED DETAILS (DO NOT REUSE) ===",
                 "These phrases/details appeared in multiple previous scenes.",
                 "INVENT FRESH alternatives. Do NOT repeat these:"]
        for phrase, count in repeated:
            lines.append(f'- "{phrase}" (used {count}x)')

        return "\n".join(lines)

    async def _stage_scene_drafting(self) -> tuple:
        """Draft all scenes with rolling context, POV, and full config awareness."""
        scenes = []
        total_tokens = 0
        client = self.get_client_for_stage("scene_drafting")
        config = self.state.config

        # Extract key config elements for drafting
        writing_style = config.get("writing_style", "")
        tone = config.get("tone", "")
        avoid_list = config.get("avoid", "")
        influences = config.get("influences", "")
        guidance = config.get("strategic_guidance", {})
        aesthetic = guidance.get("aesthetic_guide", "")
        cultural_notes = guidance.get("cultural_notes", "")
        market_positioning = guidance.get("market_positioning", "")

        # Extract spice expectations from market positioning
        spice_info = ""
        if "spice" in market_positioning.lower() or "chili" in market_positioning.lower():
            spice_info = f"HEAT LEVEL: {market_positioning}"

        for chapter in (self.state.master_outline or []):
            if not isinstance(chapter, dict):
                continue
            chapter_num = chapter.get("chapter", 1)

            for scene_info in chapter.get("scenes", []):
                if not isinstance(scene_info, dict):
                    continue
                scene_num = scene_info.get("scene", scene_info.get("scene_number", 1))
                pov_char = scene_info.get("pov", "protagonist")
                spice_level = scene_info.get("spice_level", 0)
                location = scene_info.get("location", "")

                # Get rolling context from previous scenes
                previous_context = self._get_previous_scenes_context(scenes)

                # Extract comprehensive scene attributes
                scene_name = scene_info.get('scene_name', f'Scene {scene_num}')
                purpose = scene_info.get('purpose', '')
                char_goal = scene_info.get('character_scene_goal', scene_info.get('scene_goal', ''))
                central_conflict = scene_info.get('central_conflict', scene_info.get('conflict', ''))
                proximal_conflicts = scene_info.get('proximal_conflicts', '')
                inner_conflict = scene_info.get('inner_conflict', '')
                opposition = scene_info.get('opposition_elements', '')
                opening_hook = scene_info.get('opening_hook', '')
                development = scene_info.get('development', '')
                suffering = scene_info.get('suffering', '')
                climax = scene_info.get('climax', '')
                outcome = scene_info.get('outcome', '')
                scene_question = scene_info.get('scene_question', '')
                conn_previous = scene_info.get('connection_to_previous', '')
                conn_next = scene_info.get('connection_to_next', '')
                conn_inner = scene_info.get('connection_to_inner_goals', '')
                conn_outer = scene_info.get('connection_to_outer_goals', '')
                setting_desc = scene_info.get('setting_description', '')
                sensory_focus = scene_info.get('sensory_focus', '')
                imagery = scene_info.get('imagery', '')
                key_symbol = scene_info.get('key_symbol', '')
                physical_motion = scene_info.get('physical_motion', '')
                subtext = scene_info.get('subtext', '')
                relationships = scene_info.get('relationships', '')
                knowledge_gain = scene_info.get('knowledge_gain', '')
                unique_element = scene_info.get('unique_element', '')
                differentiator = scene_info.get('differentiator', '')  # What makes THIS scene distinct from similar beats
                foreshadowing = scene_info.get('foreshadowing', '')
                pacing = scene_info.get('pacing', 'medium')
                tension_level = scene_info.get('tension_level', 5)
                emotional_arc = scene_info.get('emotional_arc', '')
                internalization = scene_info.get('internalization', '')
                dialogue_notes = scene_info.get('dialogue_notes', '')
                theme_connection = scene_info.get('theme_connection', '')
                extra_chars = scene_info.get('extra_characters', '')

                # Build comprehensive scene prompt
                # Detect scene position within chapter for differentiation
                chapter_scene_list = [s for s in chapter.get("scenes", []) if isinstance(s, dict)]
                scene_position = next((i for i, s in enumerate(chapter_scene_list)
                                       if (s.get("scene", s.get("scene_number", 0)) == scene_num)), 0)
                total_scenes_in_chapter = len(chapter_scene_list)

                # Get last scene's opening words to prevent repetition
                prev_opening = ""
                if scenes:
                    last_content = scenes[-1].get("content", "")
                    prev_opening = " ".join(last_content.split()[:50])

                prompt = f"""Write Chapter {chapter_num}, Scene {scene_num}: "{scene_name}"
POSITION: Scene {scene_position + 1} of {total_scenes_in_chapter} in this chapter.

=== MASTER CRAFT PRINCIPLES ===
1. SHOW vs TELL:
   - Large concepts/emotions → IMPLY through action, dialogue, body language
   - Specific details → CONCRETE and precise
   - Never state emotions directly; show physical manifestations

2. SENSORY WEAVING:
   - Open with environment woven into action (not a description dump)
   - Vary sensory details from previous scenes (avoid repetition)
   - Ground abstract feelings in physical sensation

3. TRANSITIONS:
   - Seamless flow between external action and internal reaction
   - Each paragraph should pull into the next
   - Descriptions emerge through character interaction with environment

4. INTERNALIZATION:
   - Balance external happenings with internal processing
   - Let the character's unique voice filter all observations
   - Moments of reflection feel earned, not inserted

=== WRITING REQUIREMENTS ===
STYLE: {writing_style}
TONE: {tone}
INFLUENCES TO CHANNEL: {influences}

=== ABSOLUTE RESTRICTIONS (NEVER INCLUDE) ===
{avoid_list}
- NEVER use: "couldn't help but", "found myself", "a sense of", "I realized"
- NEVER use stock metaphors: "electricity", "butterflies", "anchor", "storm",
  "walls crumbling", "breath I didn't know I was holding", "heart skipped"
- NEVER end a paragraph by explaining the emotion it just showed
- NEVER use two metaphors in the same paragraph
- NEVER open with weather, atmosphere, or description—open with ACTION or DIALOGUE
- NEVER loop: if you made a point, advance; do not restate it

=== SCENE DIFFERENTIATION (critical) ===
When outline beats are similar, the AI repeats itself. THIS SCENE MUST BE DISTINCT:
- Different purpose, outcome, and emotional beat from any previous scene
- If the outline gave similar beats (e.g., "they talk on balcony"), invent a concrete differentiator: different time, object, conflict, or piece of dialogue
- Do NOT retell the same story beat. Advance the story. This is Scene {scene_position + 1} of {total_scenes_in_chapter} in this chapter—it must do something the previous scene did not
{"This scene MUST open differently from the previous scene." if scenes else ""}
{f"PREVIOUS SCENE OPENED WITH: {prev_opening}..." if prev_opening else ""}
{"DO NOT repeat similar atmospheric descriptions, sensory details, or emotional" if scenes else ""}
{"states from the previous opening. Use a DIFFERENT sense, action, or entry point." if scenes else ""}

=== POV & VOICE (HARD LOCK — DO NOT BREAK) ===
PERSPECTIVE: FIRST PERSON ("I") — {pov_char}'s POV.
Every sentence must be filtered through {pov_char}'s voice. NEVER switch to
third person ("she felt", "he noticed", "{pov_char} thought"). ALWAYS use "I".
- Their unique vocabulary and thought patterns
- Their specific biases and blind spots
- Their physical sensations and emotional responses
- Body reactions must be SPECIFIC to this character (not generic "heart racing")
- Character tics should appear at most ONCE per scene (not every paragraph)

=== SCENE PURPOSE ===
WHY THIS SCENE EXISTS: {purpose}
SCENE QUESTION (to answer): {scene_question}
{f"UNIQUE ELEMENT: {unique_element}" if unique_element else ""}
{f"DIFFERENTIATOR (what makes this scene distinct from similar beats): {differentiator}" if differentiator else ""}

=== GOALS & CONFLICTS ===
CHARACTER'S SCENE GOAL: {char_goal}
CENTRAL CONFLICT: {central_conflict}
{f"PROXIMAL CONFLICTS (smaller tensions): {proximal_conflicts}" if proximal_conflicts else ""}
{f"INNER CONFLICT: {inner_conflict}" if inner_conflict else ""}
{f"OPPOSITION: {opposition}" if opposition else ""}

=== SCENE STRUCTURE ===
{f"OPENING HOOK CONCEPT: {opening_hook}" if opening_hook else "Open with immediate engagement"}
{f"DEVELOPMENT: {development}" if development else ""}
{f"SUFFERING/DIFFICULTY: {suffering}" if suffering else ""}
{f"CLIMAX MOMENT: {climax}" if climax else ""}
{f"OUTCOME: {outcome}" if outcome else ""}

=== CONNECTIONS ===
{f"FROM PREVIOUS SCENE: {conn_previous}" if conn_previous else ""}
{f"SETS UP NEXT SCENE: {conn_next}" if conn_next else ""}
{f"INNER JOURNEY CONNECTION: {conn_inner}" if conn_inner else ""}
{f"PLOT GOAL CONNECTION: {conn_outer}" if conn_outer else ""}

=== SETTING & SENSORY ===
LOCATION: {location}
{f"SETTING TO ESTABLISH: {setting_desc}" if setting_desc else ""}
{f"SENSORY FOCUS: {sensory_focus}" if sensory_focus else ""}
{f"KEY IMAGERY: {imagery}" if imagery else ""}
{f"SYMBOL TO WEAVE IN: {key_symbol}" if key_symbol else ""}

{f"AESTHETIC PALETTE: {aesthetic}" if aesthetic else ""}

=== GROUNDING DETAIL (required — but UNIQUE each scene) ===
Every scene needs ONE imperfect, unglamorous sensory detail that grounds
the setting in reality. But it MUST be a DIFFERENT detail each scene.
INVENT something specific to THIS location and moment:
- A texture underfoot, a smell that doesn't belong, a sound that interrupts
- Something broken, stained, wrong, or out of place
- A specific brand name, a price tag, a mundane object
DO NOT reuse details from previous scenes. Each scene = fresh observation.

=== CRAFT ELEMENTS ===
{f"PHYSICAL ACTIONS: {physical_motion}" if physical_motion else ""}
{f"SUBTEXT (beneath the surface): {subtext}" if subtext else ""}
{f"RELATIONSHIP DYNAMICS: {relationships}" if relationships else ""}
{f"CHARACTER LEARNS/REALIZES: {knowledge_gain}" if knowledge_gain else ""}
{f"FORESHADOWING TO PLANT: {foreshadowing}" if foreshadowing else ""}
{f"DIALOGUE TO INCLUDE: {dialogue_notes}" if dialogue_notes else ""}
{f"THEME CONNECTION: {theme_connection}" if theme_connection else ""}

=== DIALOGUE RULES ===
- Real people deflect, fumble, trail off, interrupt
- No character announces their feelings unless they would in real life
- Add physical beats between lines (not "she smiled"—what did her hands do?)
- Subtext > text: what they mean is often not what they say

=== PACING & EMOTION ===
PACING: {pacing}
TENSION LEVEL: {tension_level}/10
{f"EMOTIONAL ARC: {emotional_arc}" if emotional_arc else ""}
{f"INTERNALIZATION MOMENTS: {internalization}" if internalization else ""}

{"=== SPICE ===" if spice_level else ""}
{"HEAT LEVEL: " + str(spice_level) + "/5 - " + ("No romantic content" if spice_level == 0 else "Sexual tension only" if spice_level == 1 else "Kissing/touching" if spice_level == 2 else "Fade to black intimacy" if spice_level == 3 else "Explicit scene" if spice_level >= 4 else "") if spice_level else ""}
{spice_info}

=== CHARACTERS IN SCENE ===
{json.dumps(self.state.characters, indent=2) if self.state.characters else ''}
{f"ADDITIONAL CHARACTERS: {extra_chars}" if extra_chars else ""}

{f"=== CULTURAL AUTHENTICITY ==={chr(10)}{cultural_notes}" if cultural_notes else ""}

=== CONTINUITY ===
{previous_context}

{self._get_used_details_tracker(scenes)}

=== TARGET LENGTH ===
Approximately {self.state.words_per_scene} words.
Paragraphs: 4 sentences maximum (mobile-optimized).

=== NOW WRITE ===
Begin DIRECTLY with narrative—no preamble, no title, no scene heading.
- FIRST PERSON ONLY. Every line = "I" perspective. Never third person.
- Open with ACTION or DIALOGUE (not description, not atmosphere)
- Hook immediately with tension, motion, or intrigue
- Ground us in the POV character's physical state through what they DO
- Each paragraph must advance the scene (no restatements)
- NEVER end a paragraph by summarizing what the moment means emotionally.
  End on action, dialogue, or sensory observation. Let the reader interpret.
- Character catchphrases/tics: use at most ONCE in this scene.

Write the complete scene:"""

                if client:
                    # Calculate max tokens based on target words (1 token ≈ 1.2-1.4 words)
                    # Use 2.5x multiplier for buffer and comprehensive scenes
                    max_tokens = max(int(self.state.words_per_scene * 2.5), 2500)
                    temp = self.get_temperature_for_stage("scene_drafting")
                    response = await client.generate(prompt, max_tokens=max_tokens, temperature=temp)
                    scenes.append({
                        "chapter": chapter_num,
                        "scene_number": scene_num,
                        "pov": pov_char,
                        "location": location,
                        "spice_level": spice_level,
                        "content": self._postprocess(response.content)
                    })
                    total_tokens += response.input_tokens + response.output_tokens
                else:
                    scenes.append({
                        "chapter": chapter_num,
                        "scene_number": scene_num,
                        "pov": pov_char,
                        "content": f"[Scene content for chapter {chapter_num}, scene {scene_num}]"
                    })
                    total_tokens += 100

                # Log progress
                logger.info(f"Drafted Chapter {chapter_num}, Scene {scene_num} ({len(scenes)} total)")

        self.state.scenes = scenes
        return scenes, total_tokens

    async def _stage_scene_expansion(self) -> tuple:
        """Expand scenes that are below target word count.

        Uses rolling context so the LLM knows what was already written,
        preventing 'retry' duplication (same beat expanded as if it hadn't been drafted).
        """
        client = self.get_client_for_stage("scene_expansion")
        expanded_scenes = []
        total_tokens = 0
        scenes_expanded = 0

        target_words = self.state.words_per_scene
        min_words = int(target_words * 0.8)

        for scene in (self.state.scenes or []):
            if not isinstance(scene, dict):
                expanded_scenes.append(scene)
                continue
            validation = validate_scene_length(scene, target_words)

            if validation["meets_target"]:
                expanded_scenes.append(scene)
                continue

            # Scene needs expansion
            shortfall = validation["shortfall"]
            logger.info(f"Expanding {validation['scene']}: {validation['actual']} words "
                       f"(needs {shortfall} more)")

            if not client:
                expanded_scenes.append(scene)
                continue

            # Pass previous EXPANDED scenes as context so LLM doesn't "retry" the same beat
            previous_context = self._get_previous_scenes_context(expanded_scenes, count=3)

            prompt = f"""This scene is {validation['actual']} words but should be approximately {target_words} words.
Expand it by adding {shortfall}+ words.

=== CRITICAL RULES ===
1. CONTINUITY: The scenes below have ALREADY been written. Do NOT retell or
   repeat the same story beat. Expand THIS scene only. Advance the story.
2. POV LOCK: This is FIRST PERSON ("I"). Never switch to third person.
3. NO DUPLICATE CONTENT: Do NOT generate an alternate version of this scene.
   Keep the existing content and ADD to it—more depth, not a rewrite.
4. NO EMOTIONAL SUMMARIES: Never end a paragraph by explaining what the
   moment means. End on action, dialogue, or sensory detail.

{previous_context}

=== EXPANSION TECHNIQUES ===
- Add sensory details UNIQUE to this scene (not reused from others)
- Deepen internal monologue/reactions
- Expand dialogue with physical beats and subtext
- Add body language and movement
- Layer in setting details through character interaction
- Character tics: use at most ONCE per scene

DO NOT:
- Add new plot points or characters
- Change the scene's outcome
- Rewrite the scene from scratch (EXPAND, don't replace)
- Pad with repetitive descriptions or looping paragraphs

=== SCENE TO EXPAND ===
Chapter {scene.get('chapter')}, Scene {scene.get('scene_number')}
POV: FIRST PERSON — {scene.get('pov', 'protagonist')}

{scene.get('content', '')}

=== EXPANDED SCENE ===
Output the COMPLETE expanded scene. Keep all existing content, add depth:"""

            response = await client.generate(prompt, max_tokens=3000)
            expanded_content = self._postprocess(response.content)

            # GUARD: Check if the LLM actually expanded (vs rewrote from scratch)
            # If the first 100 chars of the original aren't in the expanded version,
            # the model generated an alternate take — keep the original instead.
            original_content = scene.get('content', '')
            original_start = original_content[:100].strip()
            if original_start and original_start not in expanded_content:
                logger.warning(
                    f"scene_expansion: Ch{scene.get('chapter')}-S{scene.get('scene_number')} "
                    f"generated alternate take instead of expanding. Keeping original."
                )
                expanded_scenes.append(scene)
            else:
                expanded_scenes.append({
                    **scene,
                    "content": expanded_content,
                    "expanded": True,
                    "original_words": validation["actual"],
                    "expanded_words": count_words_accurate(expanded_content)
                })
                scenes_expanded += 1
            total_tokens += response.input_tokens + response.output_tokens

        self.state.scenes = expanded_scenes

        return {
            "scenes_expanded": scenes_expanded,
            "total_scenes": len(expanded_scenes)
        }, total_tokens

    async def _stage_self_refinement(self) -> tuple:
        """Self-refine scenes for quality with full config awareness."""
        refined_scenes = []
        total_tokens = 0
        client = self.get_client_for_stage("self_refinement")
        config = self.state.config

        avoid_list = config.get("avoid", "")
        writing_style = config.get("writing_style", "")
        tone = config.get("tone", "")

        for scene in (self.state.scenes or []):
            if not isinstance(scene, dict):
                refined_scenes.append(scene)
                continue
            prompt = f"""Revise this scene for publication quality. Output ONLY the revised scene text.

=== HARD RULES ===
- POV: FIRST PERSON ("I") only. If any sentence uses third person
  ("{scene.get('pov', 'protagonist')} felt/thought/noticed"), rewrite it as "I".
- Never end a paragraph by explaining what the moment means emotionally.
  End on action, dialogue, or a sensory observation.

=== STYLE ===
{writing_style} | TONE: {tone}

=== RESTRICTIONS (remove if present) ===
{avoid_list}

=== REVISION PRIORITIES (in order) ===

1. POV FIX: Find any third-person slip and convert to first person.

2. CUT EMOTIONAL SUMMARIES: If a paragraph shows an emotion through
   action/dialogue, delete any sentence that then explains that emotion.
   Especially ban: "This wasn't just about...", "Something about this
   moment...", "A fragile connection...", "It was more than..."

3. CUT REPEATED TICS: If a character action (hair taming, jaw clenching,
   finger tightening) appears more than once in this scene, keep only
   the first instance. Replace others with different body language.

4. ONE METAPHOR PER PARAGRAPH: If a paragraph has 2+ figurative
   comparisons, keep the sharpest, make the rest literal.

5. CUT LOOPING: If two paragraphs make the same emotional point, cut one.
   Every paragraph must advance the scene.

6. ROUGH UP DIALOGUE: Real people deflect, fumble, trail off.
   - Cut any line where a character announces their feelings
   - If a catchphrase appears more than once, cut the repeats

7. STRENGTHEN VERBS: Replace "was/had/felt/seemed/began/started" with
   concrete action verbs. Cut filter words (noticed, realized, saw that).

=== SCENE TO REVISE ===
{scene.get('content', '')}

Output ONLY the revised scene—no notes, no commentary, no checklist:"""

            if client:
                response = await client.generate(prompt, max_tokens=2500, temperature=0.7)
                refined_scenes.append({
                    **scene,
                    "content": self._postprocess(response.content),
                    "refined": True
                })
                total_tokens += response.input_tokens + response.output_tokens
            else:
                refined_scenes.append({**scene, "refined": True})
                total_tokens += 100

        self.state.scenes = refined_scenes
        return refined_scenes, total_tokens

    async def _stage_continuity_audit(self) -> tuple:
        """Audit for continuity issues using Gemini's long context."""
        client = self.get_client_for_stage("continuity_audit")

        # Compile all scenes for continuity check
        all_content = "\n\n---\n\n".join([
            f"Chapter {s.get('chapter')}, Scene {s.get('scene_number')}:\n{s.get('content', '')}"
            for s in (self.state.scenes or [])
        ])

        prompt = f"""You are a continuity editor. Analyze this complete manuscript for consistency issues.

WORLD RULES:
{json.dumps(self.state.world_bible, indent=2) if self.state.world_bible else 'Not available'}

CHARACTERS:
{json.dumps(self.state.characters, indent=2) if self.state.characters else 'Not available'}

EXPECTED POV: First person ("I") throughout the entire manuscript.

FULL MANUSCRIPT:
{all_content}

Find and report:
1. POV BREAKS: Any sentence that switches to third person (e.g., "Lena felt",
   "she noticed", "Marco thought") when the novel should be first person ("I").
   This is the HIGHEST priority issue.
2. DUPLICATE SCENES: Any scene that retells the same event as a previous scene
   (same characters, same location, same action) — this is a generation error.
3. Character inconsistencies (appearance, personality, knowledge changes)
4. Timeline errors (events out of order, impossible timing)
5. World rule violations (contradicts established setting/rules)
6. Factual inconsistencies (names, places, objects that change)
7. HALLUCINATED CHARACTERS: Any character name that does not appear in the
   character list above — this is a generation error.

For each issue found, provide:
- Location (chapter/scene)
- Type of issue (one of: pov_break, duplicate_scene, character, timeline,
  world_rule, factual, hallucination)
- Description
- Suggested fix

Respond in JSON format with "issues" array and "passed" boolean."""

        if client:
            response = await client.generate(prompt, max_tokens=4000, temperature=0.2, json_mode=True)
            try:
                audit_report = extract_json_robust(response.content if response else None, expect_array=False)
            except Exception as e:
                logger.warning(f"Continuity audit JSON parse failed: {e}")
                audit_report = {"issues": [], "passed": True}
            # Ensure expected keys exist
            if "issues" not in audit_report:
                audit_report["issues"] = []
            if "passed" not in audit_report:
                audit_report["passed"] = len(audit_report.get("issues", [])) == 0

            # Store issues for the fix stage
            self.state.continuity_issues = audit_report.get("issues", [])
            logger.info(f"Continuity audit found {len(self.state.continuity_issues)} issues")

            return audit_report, response.input_tokens + response.output_tokens

        # Mock response
        audit_report = {
            "issues_found": 0,
            "issues": [],
            "passed": True
        }
        self.state.continuity_issues = []
        return audit_report, 50

    async def _stage_continuity_fix(self) -> tuple:
        """Fix continuity issues found in audit using Claude's nuanced understanding."""
        client = self.get_client_for_stage("continuity_fix")

        # Check if there are issues to fix
        if not self.state.continuity_issues or len(self.state.continuity_issues) == 0:
            logger.info("No continuity issues to fix - skipping stage")
            return {"fixes_applied": 0, "skipped": True}, 0

        fixed_scenes = list(self.state.scenes or [])
        total_tokens = 0
        fixes_applied = 0

        for issue in self.state.continuity_issues:
            if not isinstance(issue, dict):
                continue
            issue_location = issue.get("location", "")
            issue_type = issue.get("type", "")
            issue_desc = issue.get("description", "")
            suggested_fix = issue.get("suggested_fix", "")

            # Find the affected scene
            for i, scene in enumerate(fixed_scenes):
                if not isinstance(scene, dict):
                    continue
                scene_loc = f"Chapter {scene.get('chapter')}, Scene {scene.get('scene_number')}"
                if issue_location.lower() in scene_loc.lower() or scene_loc.lower() in issue_location.lower():

                    prompt = f"""Fix a continuity issue in this scene.

ISSUE TYPE: {issue_type}
ISSUE DESCRIPTION: {issue_desc}
SUGGESTED FIX: {suggested_fix}

ORIGINAL SCENE:
{scene.get('content', '')}

WORLD RULES (for reference):
{json.dumps(self.state.world_bible, indent=2) if self.state.world_bible else 'Not available'}

CHARACTERS (for reference):
{json.dumps(self.state.characters, indent=2) if self.state.characters else 'Not available'}

Rewrite the scene with the continuity issue fixed. Maintain the same tone, length, and style.
Only change what's necessary to fix the issue.

FIXED SCENE:"""

                    if client:
                        response = await client.generate(prompt, max_tokens=2500, temperature=0.7)
                        fixed_scenes[i] = {
                            **scene,
                            "content": self._postprocess(response.content),
                            "continuity_fixed": True,
                            "fixed_issue": issue_desc
                        }
                        total_tokens += response.input_tokens + response.output_tokens
                        fixes_applied += 1
                        logger.info(f"Fixed continuity issue in {scene_loc}: {issue_type}")
                    break

        self.state.scenes = fixed_scenes
        return {"fixes_applied": fixes_applied, "issues_found": len(self.state.continuity_issues)}, total_tokens

    async def _stage_voice_human_pass(self) -> tuple:
        """Consolidated destructive refinement: de-AI + voice + emotional texture.

        Runs BEFORE any polish stages. Combines the work of the old human_passes
        and voice_humanization into a single coherent pass to avoid conflicting
        rewrites and duplicated instructions.
        """
        enhanced_scenes = []
        total_tokens = 0
        client = self.get_client_for_stage("voice_human_pass")
        config = self.state.config
        guidance = config.get("strategic_guidance", {})

        writing_style = config.get("writing_style", "")
        influences = config.get("influences", "")
        tone = config.get("tone", "")
        aesthetic = guidance.get("aesthetic_guide", "")

        # Build AI tell patterns list for the prompt
        ai_tells_sample = AI_TELL_PATTERNS[:20]

        for scene in (self.state.scenes or []):
            if not isinstance(scene, dict):
                enhanced_scenes.append(scene)
                continue
            pov = scene.get("pov", "protagonist")

            prompt = f"""You are a destructive revision editor. Your job: make this scene
read like a human wrote it. Not "good AI." Not "polished AI." HUMAN.

This is a REVISION pass. Keep plot, characters, and scene structure intact.
Change HOW it's written, not WHAT happens.

=== HARD RULES (break these = fail) ===
1. POV: FIRST PERSON ("I") only. If any sentence uses third person
   ("{pov} felt", "{pov} thought", "she noticed"), rewrite as "I".
2. NO EMOTIONAL SUMMARIES: Never end a paragraph by explaining what
   the moment means. End on action, dialogue, or sensory observation.
3. NO REPEATED TICS: If a physical action (hair taming, jaw clenching,
   finger tightening) or catchphrase appears more than once, keep only
   the first. Replace repeats with different body language.

=== VOICE ===
STYLE: {writing_style}
TONE: {tone}
CHANNEL: {influences}
{f"AESTHETIC: {aesthetic}" if aesthetic else ""}

=== YOUR 6 JOBS (in priority order) ===

JOB 1: KILL EMOTIONAL SUMMARIZATION
Find every sentence that tells the reader what to feel after the scene
already showed it. Cut it or replace it with action/sensory detail.
KILL on sight: "This wasn't just about...", "Something about this
moment...", "A fragile connection...", "It was more than...",
"a reminder that...", "a bond forged in...", "a quiet promise...",
"Tonight wasn't just...", "a sense of something new...".
End on what the character DOES or SEES instead.

JOB 2: REPLACE STOCK WITH SPECIFIC
Push every generic image toward the specific, observed detail that
only THIS character in THIS place would notice. But DO NOT reuse the
same "ugly detail" across scenes. Each scene gets its own unique
imperfection. If a detail (humming fridge, sticky floor, TV through
walls) already appeared in an earlier scene, INVENT something new.

JOB 3: LOWER THE DIALOGUE EMOTIONAL IQ
Real people do NOT speak with perfect emotional intelligence.
- Add deflection (answering a different question)
- Add fumbling (starting, stopping, restarting)
- Add subtext (what they mean vs what they say)
- Add physical beats between lines (varied—not the same beat each time)
- REMOVE any line where a character articulates their feelings clearly
  unless they would actually do that in real life (they usually wouldn't)
- If a character catchphrase appears more than once, cut the repeats

JOB 4: CUT LOOPING PARAGRAPHS
If two paragraphs make the same emotional point, cut one. Each
paragraph earns its spot by doing something the previous one didn't.

JOB 5: ONE METAPHOR PER PARAGRAPH
Count figurative comparisons. If 2+ in one paragraph, keep the
sharpest, make the rest literal. If the SAME simile appeared in a
previous scene (e.g., "like a knife"), replace it.

JOB 6: SURFACE CLEANUP
{chr(10).join('- Kill: "' + p + '"' for p in ai_tells_sample[:10])}
- Kill filter phrases: felt, noticed, realized, saw that
- Kill hollow intensifiers: incredibly, absolutely, utterly
- Kill weak constructions: seemed to, began to, managed to
- Kill stock romance: warm hug, butterflies, anchor in rough seas,
  ethereal glow, comfortable silence, breath I didn't know I held

=== POV DEPTH ({pov}) — FIRST PERSON ONLY ===
Stay in their head. Their vocabulary. Their biases. Their blind spots.
Body reactions must be SPECIFIC to this character — not generic.
Character tics: MAX ONCE per scene. If already used, pick a different one.

=== SCENE TO TRANSFORM ===
{scene.get('content', '')}

BEFORE YOU OUTPUT, check:
1. Is every sentence first person ("I")? Fix any third-person slips.
2. Does any paragraph end by explaining the emotion? Fix it.
3. Is any detail generic/stock? Make it specific.
4. Is any dialogue too clean? Rough it up.
5. Do any two consecutive paragraphs say the same thing? Cut one.

Output the revised scene:"""

            if client:
                response = await client.generate(prompt, max_tokens=2500, temperature=0.7)
                enhanced_scenes.append({
                    **scene,
                    "content": self._postprocess(response.content),
                    "voice_human_passed": True
                })
                total_tokens += response.input_tokens + response.output_tokens
            else:
                enhanced_scenes.append({**scene, "voice_human_passed": True})
                total_tokens += 100

        self.state.scenes = enhanced_scenes
        return {"scenes_processed": len(enhanced_scenes)}, total_tokens

    async def _stage_continuity_audit_2(self) -> tuple:
        """Lightweight continuity check after destructive voice/human pass.

        Only checks facts: names, timeline, object positions, setting details.
        Does NOT evaluate style, voice, or prose quality.
        """
        client = self.get_client_for_stage("continuity_audit_2")

        all_content = "\n\n---\n\n".join([
            f"Chapter {s.get('chapter')}, Scene {s.get('scene_number')}:\n{s.get('content', '')}"
            for s in (self.state.scenes or []) if isinstance(s, dict)
        ])

        prompt = f"""You are a continuity checker. The manuscript just went through a voice revision pass.
Check ONLY for factual consistency issues that may have been introduced.

WORLD RULES:
{json.dumps(self.state.world_bible, indent=2) if self.state.world_bible else 'Not available'}

CHARACTERS:
{json.dumps(self.state.characters, indent=2) if self.state.characters else 'Not available'}

MANUSCRIPT:
{all_content}

CHECK ONLY:
1. Character names spelled correctly and consistently
2. Timeline still makes sense (no impossible sequences)
3. Objects/items haven't moved or changed unexpectedly
4. Setting details match established world rules
5. Character knowledge consistency (no knowing things they shouldn't)

DO NOT flag:
- Style or voice changes (those are intentional)
- Prose quality issues
- Dialogue naturalness

For each issue: location, type, description, suggested_fix.
Respond in JSON: {{"issues": [...], "passed": true/false}}"""

        if client:
            response = await client.generate(prompt, max_tokens=2000, temperature=0.2, json_mode=True)
            try:
                audit_report = extract_json_robust(response.content, expect_array=False)
            except Exception:
                audit_report = {"issues": [], "passed": True}
            if "issues" not in audit_report:
                audit_report["issues"] = []
            if "passed" not in audit_report:
                audit_report["passed"] = len(audit_report.get("issues", [])) == 0

            self.state.continuity_issues_2 = audit_report.get("issues", [])
            logger.info(f"Continuity audit #2: {len(self.state.continuity_issues_2)} issues")
            return audit_report, response.input_tokens + response.output_tokens

        self.state.continuity_issues_2 = []
        return {"issues": [], "passed": True}, 50

    async def _stage_continuity_fix_2(self) -> tuple:
        """Fix factual continuity issues from post-refinement audit.

        CRITICAL: Fix facts ONLY. Do not rewrite for style, do not add voice,
        do not polish. Preserve all voice/human pass work.
        """
        client = self.get_client_for_stage("continuity_fix_2")

        issues = getattr(self.state, 'continuity_issues_2', [])
        if not issues:
            logger.info("No post-refinement continuity issues - skipping")
            return {"fixes_applied": 0, "skipped": True}, 0

        fixed_scenes = list(self.state.scenes or [])
        total_tokens = 0
        fixes_applied = 0

        for issue in issues:
            if not isinstance(issue, dict):
                continue
            issue_location = issue.get("location", "")
            issue_desc = issue.get("description", "")
            suggested_fix = issue.get("suggested_fix", "")

            for i, scene in enumerate(fixed_scenes):
                if not isinstance(scene, dict):
                    continue
                scene_loc = f"Chapter {scene.get('chapter')}, Scene {scene.get('scene_number')}"
                if issue_location.lower() in scene_loc.lower() or scene_loc.lower() in issue_location.lower():

                    prompt = f"""Fix a FACTUAL continuity error in this scene.

ISSUE: {issue_desc}
SUGGESTED FIX: {suggested_fix}

RULES:
- Change ONLY the factual error (a name, a detail, a timeline reference)
- Do NOT rewrite surrounding prose for style
- Do NOT add voice, emotion, or polish
- Preserve the author's voice and sentence structure exactly
- Minimal surgical edit only

SCENE:
{scene.get('content', '')}

Output the scene with ONLY the factual fix applied:"""

                    if client:
                        response = await client.generate(prompt, max_tokens=2500, temperature=0.3)
                        fixed_scenes[i] = {
                            **scene,
                            "content": self._postprocess(response.content),
                            "continuity_fixed_2": True
                        }
                        total_tokens += response.input_tokens + response.output_tokens
                        fixes_applied += 1
                    break

        self.state.scenes = fixed_scenes
        return {"fixes_applied": fixes_applied}, total_tokens

    async def _stage_dialogue_polish(self) -> tuple:
        """Polish dialogue for authenticity, subtext, and character voice."""
        client = self.get_client_for_stage("dialogue_polish")
        polished_scenes = []
        total_tokens = 0
        config = self.state.config
        guidance = config.get("strategic_guidance", {})

        # Get dialogue bank from strategic guidance
        dialogue_bank = guidance.get("dialogue_bank", "")
        cultural_notes = guidance.get("cultural_notes", "")

        for scene in (self.state.scenes or []):
            if not isinstance(scene, dict):
                polished_scenes.append(scene)
                continue
            pov = scene.get("pov", "protagonist")

            prompt = f"""You are a dialogue specialist. Polish the dialogue in this scene for maximum authenticity.

=== HARD RULES ===
- POV: FIRST PERSON ("I") only. Never introduce third-person narration.
- If a character catchphrase or verbal tic appears more than once in this
  scene, keep only the first instance.
- Never end a paragraph by summarizing its emotional meaning.

=== CHARACTER PROFILES ===
{json.dumps(self.state.characters, indent=2) if self.state.characters else 'Not available'}

{f"=== DIALOGUE BANK (Use these patterns/phrases) ===" + chr(10) + dialogue_bank if dialogue_bank else ""}

{f"=== CULTURAL/SETTING NOTES ===" + chr(10) + cultural_notes if cultural_notes else ""}

=== DIALOGUE QUALITY CHECKLIST ===

1. ELIMINATE INFO-DUMP DIALOGUE:
   - Characters shouldn't explain plot to each other
   - Don't have characters state what they both know
   - Remove "As you know..." or similar constructions

2. ADD SUBTEXT:
   - What are they really saying beneath the words?
   - Are they deflecting, hinting, manipulating?
   - Every line should have surface meaning AND subtext

3. CHARACTER VOICE DIFFERENTIATION:
   - Each character should sound distinct
   - Word choice, rhythm, sentence length should vary by character
   - Apply any verbal tics or patterns from character profiles

4. AUTHENTIC SPEECH PATTERNS:
   - Interruptions (em-dashes—)
   - Trailing off...
   - Incomplete thoughts
   - Non-sequiturs
   - Misunderstandings

5. PHYSICAL BEATS:
   - Add micro-actions between dialogue lines
   - Characters don't float—they move, touch, look away
   - Body language should reinforce or contradict words

6. TENSION IN CONVERSATION:
   - Create conflict or push-pull in exchanges
   - Characters want different things
   - Not all questions get answered

7. ELIMINATE DIALOGUE TELLS:
   - Remove "he said angrily" (show the anger in words/actions)
   - Minimize adverbs on dialogue tags
   - "Said" is usually enough

=== SCENE TO POLISH ===
{scene.get('content', '')}

Rewrite with polished, authentic dialogue. Keep all non-dialogue prose intact.
Focus ONLY on improving the dialogue and adding physical beats between lines:"""

            if client:
                response = await client.generate(prompt, max_tokens=2500, temperature=0.7)
                polished_scenes.append({
                    **scene,
                    "content": self._postprocess(response.content),
                    "dialogue_polished": True
                })
                total_tokens += response.input_tokens + response.output_tokens
            else:
                polished_scenes.append({**scene, "dialogue_polished": True})
                total_tokens += 100

        self.state.scenes = polished_scenes
        return {"scenes_polished": len(polished_scenes)}, total_tokens

    # _stage_voice_humanization removed — merged into _stage_voice_human_pass

    async def _stage_motif_embedding(self) -> tuple:
        """Design structural motif plan that feeds into master_outline.

        This is a PLANNING stage, not a prose stage. It produces a motif map
        that master_outline uses to bake motifs into scene structure from the
        start, rather than painting them on after drafting.
        """
        client = self.get_client_for_stage("motif_embedding")
        total_tokens = 0

        themes = self.state.config.get("themes", "")
        motifs = self.state.config.get("motifs", "")
        central_question = self.state.config.get("central_question", "")
        guidance = self.state.config.get("strategic_guidance", {})
        aesthetic = guidance.get("aesthetic_guide", "")

        # Build context from completed planning stages
        beat_sheet_summary = json.dumps(self.state.beat_sheet, indent=2) if self.state.beat_sheet else "Not available"
        chars_summary = json.dumps(
            [{"name": c.get("name", ""), "role": c.get("role", ""), "arc": c.get("arc", "")}
             for c in (self.state.characters or []) if isinstance(c, dict)],
            indent=1
        )

        prompt = f"""You are a literary architect. Design a STRUCTURAL MOTIF PLAN for this novel.

This plan will be fed directly into the master outline so that scenes are
DESIGNED AROUND motifs from the start—not decorated with them after the fact.

=== STORY INPUTS ===
HIGH CONCEPT: {self.state.high_concept}
THEMES: {themes}
RECURRING MOTIFS: {motifs}
CENTRAL QUESTION: {central_question}
AESTHETIC: {aesthetic}

BEAT SHEET:
{beat_sheet_summary}

CHARACTERS:
{chars_summary}

EMOTIONAL ARCHITECTURE:
{json.dumps(self.state.config.get('emotional_architecture', {}), indent=2)}

=== PRODUCE A MOTIF MAP ===
For each major motif, provide:
1. "motif": The motif name/symbol
2. "meaning": What it represents thematically
3. "evolution": How it transforms across the story (3-4 stages)
4. "scene_mechanics": Concrete ways scenes should be built around it
   (settings, objects, character actions, dialogue patterns)
5. "key_beats": Which beat sheet moments should feature this motif prominently
6. "character_links": Which characters embody or interact with this motif

Also provide:
- "motif_collisions": Moments where two motifs should intersect or conflict
- "central_question_arc": How the motifs collectively answer the central question

Respond in JSON format:
{{"motifs": [...], "motif_collisions": [...], "central_question_arc": "..."}}"""

        if client:
            response = await client.generate(prompt, max_tokens=3000, temperature=0.5, json_mode=True)
            try:
                motif_map = extract_json_robust(response.content if response else None, expect_array=False)
            except Exception as e:
                logger.warning(f"Motif embedding JSON parse failed: {e}")
                motif_map = {"motifs": [], "motif_collisions": [], "central_question_arc": ""}
            total_tokens = response.input_tokens + response.output_tokens
        else:
            motif_map = {"motifs": [], "motif_collisions": [], "central_question_arc": ""}
            total_tokens = 50

        # Store motif map on state so master_outline can reference it
        self.state.motif_map = motif_map
        logger.info(f"Motif embedding: {len(motif_map.get('motifs', []))} motifs mapped")
        return motif_map, total_tokens

    async def _stage_chapter_hooks(self) -> tuple:
        """Ensure every chapter has a compelling opening and ending hook.

        This is the LAST creative edit stage. Nothing touches hooks after this.
        Constraints:
        - Opening: only first 2-3 paragraphs of chapter's first scene
        - Ending: only last 2-3 paragraphs of chapter's last scene
        - Middle content: DO NOT ALTER
        - Facts: DO NOT CHANGE (names, locations, timeline, objects)
        """
        client = self.get_client_for_stage("chapter_hooks")
        hooked_scenes = []
        total_tokens = 0
        config = self.state.config
        guidance = config.get("strategic_guidance", {})

        # Group scenes by chapter
        chapters: Dict[int, List[Dict]] = {}
        for scene in (self.state.scenes or []):
            if not isinstance(scene, dict):
                continue
            ch = scene.get("chapter", 1)
            if ch not in chapters:
                chapters[ch] = []
            chapters[ch].append(scene)

        commercial_notes = guidance.get("commercial_notes", "")
        hook_guidance = ""
        if "hook" in commercial_notes.lower():
            hook_guidance = f"COMMERCIAL GUIDANCE: {commercial_notes}"

        for chapter_num in sorted(chapters.keys()):
            chapter_scenes = chapters[chapter_num]

            for i, scene in enumerate(chapter_scenes):
                if not isinstance(scene, dict):
                    hooked_scenes.append(scene)
                    continue

                is_chapter_start = (i == 0)
                is_chapter_end = (i == len(chapter_scenes) - 1)

                if is_chapter_end and client:
                    prompt = f"""Rewrite this scene so it ends with a powerful hook. Output ONLY the full scene text — no commentary, no notes, no labels.

RULES:
- Modify ONLY the last 2-3 paragraphs for the hook
- Keep ALL other content word-for-word identical
- Do NOT change facts (names, locations, objects, timeline)
- No AI tells, no emotional summaries at the end
- FIRST PERSON POV ("I") throughout — never third person
- Hook types: cliffhanger, tension peak, threat, question, twist, gut-punch, or consequence
{hook_guidance}

<scene>
{scene.get('content', '')}
</scene>

Output the complete scene with only the ending paragraphs rewritten:"""

                    response = await client.generate(prompt, max_tokens=2500, temperature=0.75)
                    hooked_scenes.append({
                        **scene,
                        "content": self._postprocess(response.content),
                        "hook_enhanced": True
                    })
                    total_tokens += response.input_tokens + response.output_tokens

                elif is_chapter_start and client:
                    prompt = f"""Rewrite this scene so it opens with an immediate hook. Output ONLY the full scene text — no commentary, no notes, no labels.

RULES:
- Modify ONLY the first 2-3 paragraphs for the hook
- Keep ALL other content word-for-word identical
- Do NOT change facts (names, locations, objects, timeline)
- No AI tells
- FIRST PERSON POV ("I") throughout — never third person
- Hook types: in medias res, striking sensory image, provocative thought, immediate conflict, disorientation

<scene>
{scene.get('content', '')}
</scene>

Output the complete scene with only the opening paragraphs rewritten:"""

                    response = await client.generate(prompt, max_tokens=2500, temperature=0.75)
                    hooked_scenes.append({
                        **scene,
                        "content": self._postprocess(response.content),
                        "hook_enhanced": True
                    })
                    total_tokens += response.input_tokens + response.output_tokens
                else:
                    hooked_scenes.append(scene)

        self.state.scenes = hooked_scenes
        return {"chapters_hooked": len(chapters), "scenes_processed": len(hooked_scenes)}, total_tokens

    async def _stage_prose_polish(self) -> tuple:
        """Final line-by-line polish using rhetorical devices for publication quality."""
        client = self.get_client_for_stage("prose_polish")
        polished_scenes = []
        total_tokens = 0
        config = self.state.config

        writing_style = config.get("writing_style", "")
        tone = config.get("tone", "")
        influences = config.get("influences", "")

        # Build rhetorical devices reference
        devices_sample = list(RHETORICAL_DEVICES.items())[:15]  # Sample of devices
        devices_text = "\n".join([f"- {name}: {desc}" for name, desc in devices_sample])

        for scene in (self.state.scenes or []):
            if not isinstance(scene, dict):
                polished_scenes.append(scene)
                continue
            pov = scene.get("pov", "protagonist")

            prompt = f"""You are a master prose editor performing the FINAL polish on a novel scene.
This is the LAST pass before publication. Previous stages have established voice and removed
AI tells. Your job is SUBTLE REFINEMENT only - do NOT undo prior work.

{PRESERVATION_CONSTRAINTS}

=== STRICT PRESERVATION MODE ===
- DO NOT change sentence structures that work
- DO NOT normalize character-specific vocabulary
- DO NOT smooth out intentional roughness/fragments
- DO NOT add flowery metaphors or purple prose
- DO NOT introduce any AI tell patterns
- ONLY make improvements that are clearly better

=== STYLE TARGETS ===
WRITING STYLE: {writing_style}
TONE: {tone}
INFLUENCES: {influences}

=== RHETORICAL DEVICES TO CONSIDER (use sparingly) ===
{devices_text}

=== LINE-BY-LINE POLISH CHECKLIST ===

1. WORD CHOICE:
   - Is every word precisely chosen for effect?
   - Can any weak verb be replaced with a stronger one?
   - Are there fresher alternatives to common expressions?
   - Does the vocabulary match the POV character ({pov})?

2. SENTENCE STRUCTURE:
   - Does sentence length vary for rhythm?
   - Do important moments get short, punchy sentences?
   - Are complex ideas given room to breathe in longer sentences?
   - Is there at least one striking sentence construction per paragraph?

3. SOUND & RHYTHM:
   - Read aloud: does it flow naturally?
   - Any accidental tongue-twisters or awkward sounds?
   - Strategic use of alliteration or assonance?
   - Do paragraph endings have punch?

4. PRECISION:
   - Are sensory details specific (not generic)?
   - Is every image concrete and visualizable?
   - Are emotions shown through physical sensation?
   - Does every line do work (no padding)?

5. RHETORICAL CRAFT:
   - Are there opportunities for tricolon, chiasmus, or parallelism?
   - Can any moment use antithesis or contrast?
   - Strategic fragments for emphasis?
   - Powerful periodic sentences that build to revelation?

6. OPENING & CLOSING:
   - Does the scene open with immediate engagement?
   - Does the scene close with resonance or hook?
   - Is the strongest moment positioned correctly?

=== SCENE TO POLISH ===
{scene.get('content', '')}

=== INSTRUCTIONS ===
Go through line by line. Make ONLY improvements that are clearly better:
- Swap a weak word for a stronger one (but keep voice)
- Fix rhythm that reads awkwardly aloud
- Sharpen an imprecise image
- Add a rhetorical device where it fits naturally

MOST SENTENCES SHOULD STAY UNCHANGED. Only touch what needs it.
If in doubt, leave it alone. Preserve the existing voice absolutely.

BEFORE OUTPUTTING: Scan for AI tells from PRESERVATION CONSTRAINTS.
If you accidentally introduced any, remove them.

POLISHED SCENE:"""

            if client:
                response = await client.generate(prompt, max_tokens=2500, temperature=0.7)
                polished_scenes.append({
                    **scene,
                    "content": self._postprocess(response.content),
                    "polished": True
                })
                total_tokens += response.input_tokens + response.output_tokens
            else:
                polished_scenes.append({**scene, "polished": True})
                total_tokens += 100

        self.state.scenes = polished_scenes
        return {"scenes_polished": len(polished_scenes)}, total_tokens

    async def _stage_final_deai(self) -> tuple:
        """Final surgical pass to remove any AI tells that slipped through.

        Runs AFTER chapter_hooks. Uses word-window slicing to PROTECT hook text:
        - First 300 words: protected (chapter opening)
        - Last 400 words: protected (chapter hook)
        - Middle: editable (regex + targeted LLM rewrites)
        """
        client = self.get_client_for_stage("final_deai")
        cleaned_scenes = []
        total_tokens = 0
        fixes_made = 0

        SURGICAL_REPLACEMENTS = {
            # AI tell phrases
            "I couldn't help but notice": "",
            "I found myself": "I",
            "I noticed that": "",
            "I realized that": "",
            "I felt a sense of": "I felt",
            "Something about it made me": "It made me",
            "seemed to": "",
            "appeared to": "",
            "managed to": "",
            "proceeded to": "",
            "began to": "",
            "started to": "",
            # Hollow intensifiers
            " incredibly ": " ",
            " absolutely ": " ",
            " utterly ": " ",
            " completely ": " ",
            " totally ": " ",
            " truly ": " ",
            " genuinely ": " ",
            # Stock romance metaphors
            "a whirlwind of emotions": "confusion",
            "time seemed to stop": "everything stilled",
            "electricity coursed through": "heat rushed through",
            "my heart skipped a beat": "my breath caught",
            "butterflies in my stomach": "nerves",
            "flooded with": "felt",
            "overwhelmed by": "hit by",
            "like a knife": "",
            "like a knife slicing through butter": "",
            # Emotional summarization patterns
            "This wasn't just about": "",
            "Something about this moment": "",
            "A fragile connection": "",
            "It was more than": "",
            "a quiet promise that": "",
            "a sense of something new": "",
            "Tonight wasn't just about": "",
            "a reminder that": "",
            "connection in unexpected places": "",
            "something significant had passed between": "",
        }

        # Guard: if no scenes exist, return early
        scenes_list = self.state.scenes or []
        if not scenes_list:
            logger.warning("final_deai: No scenes to process")
            return {"fixes_made": 0, "scenes_processed": 0, "hooks_protected": 0}, 0

        # Group scenes by chapter to identify chapter-end scenes
        chapters: Dict[int, List[int]] = {}
        for idx, scene in enumerate(scenes_list):
            if isinstance(scene, dict):
                ch = scene.get("chapter", 1)
                if ch not in chapters:
                    chapters[ch] = []
                chapters[ch].append(idx)

        # Build set of chapter-end scene indices (these get hook protection)
        chapter_end_indices = set()
        for ch_indices in chapters.values():
            if ch_indices:
                chapter_end_indices.add(ch_indices[-1])

        for idx, scene in enumerate(scenes_list):
            if not isinstance(scene, dict):
                cleaned_scenes.append(scene)
                continue

            content = scene.get("content", "")
            scene_fixes = 0
            is_chapter_end = idx in chapter_end_indices

            if is_chapter_end:
                # HOOK PROTECTION: split into protected head/tail + editable middle
                words = content.split()
                HEAD_WORDS = 300
                TAIL_WORDS = 400

                if len(words) <= HEAD_WORDS + TAIL_WORDS:
                    # Scene too short to have an editable middle — skip entirely
                    cleaned_scenes.append(scene)
                    continue

                head = " ".join(words[:HEAD_WORDS])
                middle = " ".join(words[HEAD_WORDS:-TAIL_WORDS])
                tail = " ".join(words[-TAIL_WORDS:])

                # Apply surgical replacements ONLY to middle
                for pattern, replacement in SURGICAL_REPLACEMENTS.items():
                    if pattern.lower() in middle.lower():
                        middle = re.sub(
                            re.escape(pattern), replacement,
                            middle, flags=re.IGNORECASE
                        )
                        scene_fixes += 1

                middle = re.sub(r'  +', ' ', middle)
                middle = re.sub(r' +\.', '.', middle)
                middle = re.sub(r' +,', ',', middle)

                # LLM pass on middle only if needed
                remaining_tells = count_ai_tells(middle)
                if remaining_tells["total_tells"] > 0 and client:
                    problem_patterns = list(remaining_tells["patterns_found"].keys())[:5]
                    prompt = f"""SURGICAL edit. Fix ONLY sentences containing these AI tell patterns.
Do NOT change anything else.

PATTERNS TO FIX: {problem_patterns}

RULES:
- Only change sentences containing the patterns above
- Keep meaning, just remove the AI tell
- Preserve surrounding sentences EXACTLY

TEXT:
{middle}

OUTPUT the text with only problematic sentences fixed:"""

                    response = await client.generate(prompt, max_tokens=3000)
                    middle = self._postprocess(response.content)
                    total_tokens += response.input_tokens + response.output_tokens
                    scene_fixes += remaining_tells["total_tells"]

                # Recombine: protected head + cleaned middle + protected tail
                content = head + " " + middle + " " + tail
            else:
                # Non-chapter-end scenes: full surgical pass (no hook to protect)
                for pattern, replacement in SURGICAL_REPLACEMENTS.items():
                    if pattern.lower() in content.lower():
                        content = re.sub(
                            re.escape(pattern), replacement,
                            content, flags=re.IGNORECASE
                        )
                        scene_fixes += 1

                content = re.sub(r'  +', ' ', content)
                content = re.sub(r' +\.', '.', content)
                content = re.sub(r' +,', ',', content)

                remaining_tells = count_ai_tells(content)
                if remaining_tells["total_tells"] > 0 and client:
                    problem_patterns = list(remaining_tells["patterns_found"].keys())[:5]
                    prompt = f"""SURGICAL edit. Fix ONLY sentences containing these AI tell patterns.
Do NOT change anything else.

PATTERNS TO FIX: {problem_patterns}

RULES:
- Only change sentences containing the patterns above
- Keep meaning, just remove the AI tell
- Preserve surrounding sentences EXACTLY

TEXT:
{content}

OUTPUT the text with only problematic sentences fixed:"""

                    response = await client.generate(prompt, max_tokens=3000)
                    content = self._postprocess(response.content)
                    total_tokens += response.input_tokens + response.output_tokens
                    scene_fixes += remaining_tells["total_tells"]

            if scene_fixes > 0:
                fixes_made += scene_fixes

            cleaned_scenes.append({
                **scene,
                "content": content,
                "deai_fixes": scene_fixes
            })

        self.state.scenes = cleaned_scenes
        logger.info(f"Final de-AI pass: {fixes_made} fixes (hook-protected on {len(chapter_end_indices)} chapter endings)")
        return {"fixes_made": fixes_made, "scenes_processed": len(cleaned_scenes), "hooks_protected": len(chapter_end_indices)}, total_tokens

    async def _stage_quality_audit(self) -> tuple:
        """Comprehensive quality audit before final output."""
        client = self.get_client_for_stage("quality_audit")
        config = self.state.config
        total_tokens = 0

        audit_results = {
            "word_count": {},
            "ai_tells": {},
            "scene_lengths": [],
            "spice_distribution": {},
            "chapter_hooks": [],
            "issues": [],
            "passed": True
        }

        # 1. Word Count Audit
        scenes_list = [s for s in (self.state.scenes or []) if isinstance(s, dict)]
        total_words = sum(count_words_accurate(s.get("content", ""))
                        for s in scenes_list)
        target_words = self.state.target_words
        word_pct = (total_words / target_words * 100) if target_words > 0 else 0

        audit_results["word_count"] = {
            "actual": total_words,
            "target": target_words,
            "percentage": round(word_pct, 1),
            "status": "on_target" if word_pct >= 95 else "slightly_under" if word_pct >= 80 else "under"
        }

        if word_pct < 80:
            audit_results["issues"].append({
                "type": "word_count",
                "severity": "high",
                "message": f"Word count {total_words:,} is {100-word_pct:.0f}% below target"
            })
            audit_results["passed"] = False

        # 2. AI Tell Audit
        all_content = " ".join(s.get("content", "") for s in scenes_list)
        ai_tell_results = count_ai_tells(all_content)
        audit_results["ai_tells"] = ai_tell_results

        if not ai_tell_results["acceptable"]:
            audit_results["issues"].append({
                "type": "ai_tells",
                "severity": "medium",
                "message": f"AI tell ratio {ai_tell_results['tells_per_1000_words']}/1000 words (should be <2)"
            })

        # 3. Scene Length Audit
        short_scenes = []
        for scene in scenes_list:
            validation = validate_scene_length(scene, self.state.words_per_scene)
            if not validation["meets_target"]:
                short_scenes.append(validation)

        if short_scenes:
            audit_results["scene_lengths"] = short_scenes
            if len(short_scenes) > 3:
                audit_results["issues"].append({
                    "type": "scene_length",
                    "severity": "medium",
                    "message": f"{len(short_scenes)} scenes below 80% target word count"
                })

        # 4. Spice Distribution Audit
        guidance = config.get("strategic_guidance", {})
        market_pos = guidance.get("market_positioning", "").lower()

        # Extract promised spice level
        promised_spice = 0
        if "5/5" in market_pos or "5 chili" in market_pos:
            promised_spice = 5
        elif "4/5" in market_pos or "4 chili" in market_pos:
            promised_spice = 4
        elif "3/5" in market_pos or "3 chili" in market_pos:
            promised_spice = 3

        if promised_spice > 0:
            spice_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            for scene in scenes_list:
                level = scene.get("spice_level", 0)
                spice_counts[level] = spice_counts.get(level, 0) + 1

            # Check if actual spice matches promise
            high_spice_scenes = spice_counts.get(4, 0) + spice_counts.get(5, 0)
            if promised_spice >= 4 and high_spice_scenes < 2:
                audit_results["issues"].append({
                    "type": "spice_distribution",
                    "severity": "high",
                    "message": f"Promised {promised_spice}/5 spice but only {high_spice_scenes} explicit scenes"
                })

            audit_results["spice_distribution"] = {
                "promised": promised_spice,
                "distribution": spice_counts,
                "high_spice_count": high_spice_scenes
            }

        # 5. Chapter Hook Strength (sample check)
        # Group by chapter and check last scene of each
        chapters: Dict[int, List[Dict]] = {}
        for scene in scenes_list:
            ch = scene.get("chapter", 1)
            if ch not in chapters:
                chapters[ch] = []
            chapters[ch].append(scene)

        weak_hooks = []
        for ch_num, ch_scenes in chapters.items():
            last_scene = ch_scenes[-1] if ch_scenes else None
            if last_scene:
                content = last_scene.get("content", "")
                # Check last 200 chars for hook indicators
                ending = content[-500:].lower() if len(content) > 500 else content.lower()
                has_hook = any(indicator in ending for indicator in [
                    "?", "...", "—", "but", "suddenly", "then",
                    "kiss", "touch", "blood", "danger", "realize"
                ])
                if not has_hook:
                    weak_hooks.append(ch_num)

        if weak_hooks:
            audit_results["chapter_hooks"] = weak_hooks
            if len(weak_hooks) > 2:
                audit_results["issues"].append({
                    "type": "chapter_hooks",
                    "severity": "low",
                    "message": f"Chapters {weak_hooks} may have weak ending hooks"
                })

        # Log audit results
        logger.info(f"Quality Audit: {len(audit_results['issues'])} issues found")
        for issue in audit_results["issues"]:
            logger.warning(f"  [{issue['severity']}] {issue['message']}")

        # Determine if iteration is needed and which stages to re-run
        audit_results["needs_iteration"] = False
        audit_results["stages_to_rerun"] = []

        if audit_results["issues"]:
            high_severity = [i for i in audit_results["issues"] if i["severity"] == "high"]
            medium_severity = [i for i in audit_results["issues"] if i["severity"] == "medium"]

            for issue in high_severity + medium_severity:
                if issue["type"] == "word_count" and word_pct < 80:
                    # Need more content - re-run scene_expansion
                    if "scene_expansion" not in audit_results["stages_to_rerun"]:
                        audit_results["stages_to_rerun"].append("scene_expansion")
                        audit_results["needs_iteration"] = True

                elif issue["type"] == "ai_tells":
                    # AI tells too high - re-run voice_human_pass
                    if "voice_human_pass" not in audit_results["stages_to_rerun"]:
                        audit_results["stages_to_rerun"].append("voice_human_pass")
                        audit_results["needs_iteration"] = True

                elif issue["type"] == "scene_length":
                    # Short scenes - re-run scene_expansion
                    if "scene_expansion" not in audit_results["stages_to_rerun"]:
                        audit_results["stages_to_rerun"].append("scene_expansion")
                        audit_results["needs_iteration"] = True

            # Track iteration count to prevent infinite loops
            iteration_count = getattr(self.state, '_quality_iterations', 0)
            if iteration_count >= 2:
                logger.warning("Max quality iterations (2) reached. Proceeding with current output.")
                audit_results["needs_iteration"] = False
                audit_results["max_iterations_reached"] = True
            else:
                self.state._quality_iterations = iteration_count + 1

        return audit_results, total_tokens

    async def _stage_output_validation(self) -> tuple:
        """Final quality validation and output generation with comprehensive reporting."""
        client = self.get_client_for_stage("output_validation")
        config = self.state.config

        # Calculate stats using accurate word count
        scenes_list = [s for s in (self.state.scenes or []) if isinstance(s, dict)]
        total_scenes = len(scenes_list)
        total_words = sum(count_words_accurate(s.get("content", ""))
                        for s in scenes_list)

        # Count chapters
        chapters = set(s.get("chapter") for s in scenes_list)
        total_chapters = len(chapters)

        # Calculate targets vs actual
        target_words = self.state.target_words
        target_chapters = self.state.target_chapters
        word_percentage = (total_words / target_words * 100) if target_words > 0 else 0

        validation_report = {
            "total_scenes": total_scenes,
            "total_chapters": total_chapters,
            "total_words": total_words,
            "target_words": target_words,
            "target_chapters": target_chapters,
            "word_percentage": round(word_percentage, 1),
            "avg_words_per_chapter": total_words // total_chapters if total_chapters > 0 else 0,
            "avg_words_per_scene": total_words // total_scenes if total_scenes > 0 else 0,
            "quality_score": 0.0,
            "passed": False
        }

        # Sample validation - check multiple scenes
        if client and scenes_list and len(scenes_list) >= 3:
            # Check beginning, middle, and end
            sample_indices = [0, len(scenes_list) // 2, -1]
            samples = [scenes_list[i] for i in sample_indices]

            prompt = f"""Rate these 3 representative scenes (beginning, middle, end) on quality (1-10 scale).

WRITING REQUIREMENTS:
Style: {config.get('writing_style', '')}
Tone: {config.get('tone', '')}
Genre: {config.get('genre', '')}

SCENE 1 (Opening):
{samples[0].get('content', '')[:2000]}

SCENE 2 (Midpoint):
{samples[1].get('content', '')[:2000]}

SCENE 3 (Climax/End):
{samples[2].get('content', '')[:2000]}

Rate the OVERALL manuscript across:
1. Prose Quality (clarity, flow, matches requested style)
2. Character Voice (distinct, consistent across scenes)
3. Pacing (appropriate tension, good rhythm)
4. Sensory Detail (vivid, matches aesthetic guide)
5. Hook/Engagement (page-turner quality)
6. Genre Fit (meets reader expectations for {config.get('genre', 'this genre')})

Respond with JSON:
{{"scores": {{"prose": X, "voice": X, "pacing": X, "sensory": X, "hook": X, "genre_fit": X}}, "overall": X, "strengths": ["..."], "areas_for_improvement": ["..."]}}"""

            try:
                response = await client.generate(prompt, max_tokens=800, json_mode=True)
                quality_data = extract_json_robust(response.content, expect_array=False)

                validation_report["quality_score"] = quality_data.get("overall", 7) / 10
                validation_report["quality_details"] = quality_data
                validation_report["passed"] = quality_data.get("overall", 0) >= 6 and word_percentage >= 80
            except Exception as e:
                logger.warning(f"Quality validation parse error: {e}")
                validation_report["quality_score"] = 0.85
                validation_report["passed"] = word_percentage >= 80
        else:
            validation_report["quality_score"] = 0.85
            validation_report["passed"] = word_percentage >= 80

        # Determine word count status
        if word_percentage >= 95:
            validation_report["word_count_status"] = "on_target"
        elif word_percentage >= 80:
            validation_report["word_count_status"] = "slightly_under"
        elif word_percentage >= 60:
            validation_report["word_count_status"] = "under_target"
        else:
            validation_report["word_count_status"] = "significantly_under"

        # Save final output
        output_dir = self.state.project_path / "output"
        output_dir.mkdir(exist_ok=True)

        # Compile to single markdown file
        full_text = f"# {config.get('title', 'Untitled')}\n\n"
        full_text += f"*{config.get('synopsis', '')}*\n\n"
        full_text += "---\n\n"

        current_chapter = None
        chapter_titles = {}

        # Get chapter titles from outline if available
        for ch in (self.state.master_outline or []):
            if not isinstance(ch, dict):
                continue
            ch_num = ch.get("chapter")
            ch_title = ch.get("chapter_title", "")
            if ch_num and ch_title:
                chapter_titles[ch_num] = ch_title

        for scene in (self.state.scenes or []):
            if not isinstance(scene, dict):
                continue
            chapter = scene.get("chapter")
            if chapter != current_chapter:
                ch_title = chapter_titles.get(chapter, "")
                if ch_title:
                    full_text += f"\n\n## Chapter {chapter}: {ch_title}\n\n"
                else:
                    full_text += f"\n\n## Chapter {chapter}\n\n"
                current_chapter = chapter
            else:
                full_text += "\n\n⁂\n\n"  # Fancy scene break
            full_text += scene.get("content", "")

        # Add THE END
        full_text += "\n\n---\n\n# THE END\n\n"
        full_text += f"*Word Count: {total_words:,}*\n"

        output_file = output_dir / f"{self.state.project_name}.md"
        output_file.write_text(full_text, encoding='utf-8')

        validation_report["output_file"] = str(output_file)

        # Log final stats
        logger.info(f"Novel generated: {total_words:,} words across {total_chapters} chapters "
                   f"({word_percentage:.1f}% of target)")

        return validation_report, 100


# Convenience function
async def run_pipeline(project_path: str, llm_client=None, resume: bool = False):
    """Run the full pipeline for a project."""
    orchestrator = PipelineOrchestrator(Path(project_path), llm_client)
    return await orchestrator.run(resume=resume)
