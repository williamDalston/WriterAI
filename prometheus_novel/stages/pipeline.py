"""
Pipeline Orchestrator - Novel Generation Pipeline

Orchestrates the complete novel generation process through 24 stages across
planning, drafting, refinement, polish, and validation phases:

Planning: high_concept, world_building, beat_sheet, emotional_architecture,
  character_profiles, motif_embedding, master_outline, trope_integration
Drafting: scene_drafting, scene_expansion, structure_gate, continuity_audit,
  continuity_fix, continuity_recheck, self_refinement
Refinement: voice_human_pass, continuity_audit_2, continuity_fix_2
Polish: dialogue_polish, prose_polish, chapter_hooks
Validation: final_deai, quality_audit, output_validation
"""

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import secrets
import yaml
from datetime import datetime

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


# ============================================================================
# HIGH CONCEPT — Validation, Fingerprinting, Drift Detection
# ============================================================================

# Generic phrases that signal the LLM fell back to vague filler
CONCEPT_GENERIC_PHRASES = [
    "must confront", "dark secrets", "nothing is as it seems",
    "everything changes", "will never be the same", "a journey of",
    "discovers the truth", "faces their greatest challenge",
    "a tale of love and loss", "in a world where",
    "against all odds", "race against time", "uncover the mystery",
    "hidden truths", "dark past", "shocking revelation",
    "unlikely hero", "must choose between",
]

# Stop sequences for planning stages (non-prose outputs)
PLANNING_STOP_SEQUENCES = [
    "\nCertainly", "\nHere is", "\nAs requested",
    "\nI hope this", "\nLet me know", "\nWould you like",
    "\nNote:", "\n---\n",
]

# Stop sequences for structure gate scoring (JSON analysis, not prose)
STRUCTURE_GATE_STOP_SEQUENCES = [
    "\nCertainly", "\nHere is", "\nSure",
    "\nNotes:", "\nExplanation:", "\nAnalysis:",
    "\nI hope", "\nLet me know", "\n---\n",
]

STRUCTURE_GATE_SYSTEM_PROMPT = """You are a story structure analyst. You output ONLY valid JSON.
No markdown. No commentary. No explanation. Just the JSON object."""

# Categories for structure gate scoring (0-5 each, 25 total)
STRUCTURE_CATEGORIES = ["structure", "tension", "emotional_beat", "dialogue_realism", "scene_turn"]

# ── Category fill-in templates ──────────────────────────────────────────────
# Per-category diagnostic: what 4-5 looks like, common deficits, fill-in
# directives, and machine-checkable success criteria.
CATEGORY_FILL_INS: Dict[str, Dict[str, Any]] = {
    "structure": {
        "description": "clear goal, obstacle, tactic, pressure (why now)",
        "common_deficits": [
            "Goal is vague or implicit",
            "Obstacle is emotional mood, not concrete blocker",
            "No 'why now' constraint creating urgency",
        ],
        "directives": [
            "State the POV character's concrete goal in the FIRST 120 words.",
            "Add a named external obstacle (person/rule/deadline/barrier), not mood.",
            "Add a 'why now' pressure (time limit, discovery risk, scarcity).",
        ],
        "success_criteria": [
            "By paragraph 2 the goal is one clear sentence.",
            "Obstacle is external, not emotional.",
            "Delay is costly — a pressure element is explicit.",
        ],
        "check_hints": [
            "first_120_words_contain_goal_verb",
            "obstacle_is_noun_not_adjective",
            "urgency_word_in_first_half",
        ],
    },
    "tension": {
        "description": "active conflict, uncertainty, explicit consequences, escalation",
        "common_deficits": [
            "Stakes implied, never stated",
            "No ticking consequence if goal fails",
            "Tension flat — same level start to finish",
        ],
        "directives": [
            "Name a concrete consequence of failure in the FIRST 120 words (job/safety/relationship/freedom).",
            "Add a worsening beat AFTER the midpoint — something gets harder or more dangerous.",
            "Last paragraph must contain an escalation line (action or irreversible choice, NOT summary).",
        ],
        "success_criteria": [
            "A named consequence appears before the scene midpoint.",
            "Second half contains a complication that first half did not.",
            "Last paragraph escalates — no summary, no reflection.",
        ],
        "check_hints": [
            "consequence_word_in_first_half",
            "complication_after_midpoint",
            "last_para_is_action_not_summary",
        ],
    },
    "emotional_beat": {
        "description": "clear internal shift from one posture to another, shown through behavior",
        "common_deficits": [
            "Character starts and ends in same emotional state",
            "Emotion told ('she felt sad') not shown through behavior",
            "No want-vs-fear contradiction resolving into choice",
        ],
        "directives": [
            "Start with one emotional posture, end with a DIFFERENT one — name both.",
            "Show the shift through a BEHAVIOR CHANGE (what the character physically does differently).",
            "Add one want-vs-fear contradiction that resolves into a concrete action.",
        ],
        "success_criteria": [
            "First-quarter emotion word differs from last-quarter emotion word.",
            "At least one physical behavior change is visible (not narration only).",
            "A contradiction produces a decision or physical action.",
        ],
        "check_hints": [
            "emotion_words_differ_first_vs_last_quarter",
            "action_verb_after_turning_point",
            "decision_or_choice_verb_present",
        ],
    },
    "dialogue_realism": {
        "description": "subtext, evasion, distinct voices, not exposition dumps",
        "common_deficits": [
            "Characters answer directly — no evasion",
            "Dialogue is exposition — explaining things both know",
            "All characters sound identical",
        ],
        "directives": [
            "Add one INTERRUPTION or DEFLECTION (character answers a different question).",
            "Add one line where said ≠ meant (subtext).",
            "Add one concrete physical action DURING dialogue (grounding gesture, not 'she said').",
        ],
        "success_criteria": [
            "One dialogue line contains evasion, deflection, or interruption.",
            "One exchange has visible subtext (said ≠ meant).",
            "One physical action occurs mid-conversation (not a speech tag).",
        ],
        "check_hints": [
            "interruption_or_ellipsis_in_dialogue",
            "action_beat_during_dialogue",
            "dialogue_lines_have_varied_length",
        ],
    },
    "scene_turn": {
        "description": "ending changes stakes, knowledge, or relationships; next action is forced",
        "common_deficits": [
            "Scene ends same as it started",
            "No new info changes the next action",
            "Ending is summary/reflection, not pivot",
        ],
        "directives": [
            "Last paragraph MUST introduce: new info, irreversible choice, or a loss.",
            "Character's plan at scene end must differ from plan at scene start.",
            "Final sentence = action, dialogue, or charged image. NEVER reflection/summary.",
        ],
        "success_criteria": [
            "Last paragraph contains new-info/choice/loss (not recap).",
            "Character's situation has objectively changed.",
            "Final sentence is action/dialogue/sensory — zero summary words.",
        ],
        "check_hints": [
            "last_para_has_new_info_or_choice",
            "final_sentence_is_action_or_dialogue",
            "no_summary_words_in_last_sentence",
        ],
    },
}

# System prompt for the structure gate repair pass
STRUCTURE_REPAIR_SYSTEM_PROMPT = (
    "You are a ruthless story surgeon. Fix only what is necessary to satisfy the scorecard. "
    "Preserve voice, POV, and continuity. Output only the revised scene."
)

HIGH_CONCEPT_SYSTEM_PROMPT = """You are a senior acquisitions editor at a major publishing house.
Your job: distill a novel's premise into a single compelling paragraph that would make an agent
request the full manuscript.

RULES:
- Output ONLY the high concept paragraph. No preamble, no commentary, no alternatives.
- Be SPECIFIC: name the protagonist, the setting, the central tension, and the emotional stakes.
- Avoid generic phrasing: "must confront", "dark secrets", "nothing is as it seems" — these are filler.
- The concept should make clear WHY this story is fresh and WHO it's for.
- Do NOT restate the synopsis verbatim. Distill and sharpen it.
- Maximum 4 sentences. Every word must earn its place."""


def validate_high_concept(text: str, config: Dict) -> Dict[str, Any]:
    """Validate a high concept candidate. Returns score + issues dict.

    Checks: preamble, length, truncation, multi-paragraph, generic phrases,
    specificity (named protagonist, setting), synopsis restatement.
    """
    issues = {}
    original = text

    # 1. Strip preamble
    preamble_patterns = [
        r'^(?:Sure[,!.]?\s*)?[Hh]ere\'?s?\s+(?:the |a |my )?(?:high\s+concept|concept)[^.:\n]{0,40}[.:]\s*\n+',
        r'^(?:Sure|Certainly|Of course)[,!.]\s*[^\n]{0,60}\n+',
        r'^(?:High\s+Concept:?\s*\n+)',
    ]
    for pat in preamble_patterns:
        text = re.sub(pat, '', text, count=1)
    text = text.strip()
    if text != original.strip():
        issues["preamble_stripped"] = True

    # 2. Length check
    word_count = len(text.split())
    if word_count < 15:
        issues["too_short"] = word_count
    if word_count > 120:
        issues["too_long"] = word_count

    # 3. Truncation detection
    if text and text[-1] not in '.!?"\'':
        issues["possible_truncation"] = text[-30:]

    # 4. Multi-paragraph trim (keep only first substantive paragraph)
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if len(paragraphs) > 1:
        # Keep only the longest paragraph (likely the concept itself)
        text = max(paragraphs, key=len)
        issues["multi_paragraph_trimmed"] = len(paragraphs)

    # 5. Generic phrase detection
    text_lower = text.lower()
    found_generic = [p for p in CONCEPT_GENERIC_PHRASES if p in text_lower]
    if found_generic:
        issues["generic_phrases"] = found_generic

    # 6. Specificity check — protagonist name should appear
    protagonist = config.get("protagonist", "")
    if protagonist:
        # Extract first name from protagonist field
        proto_first = protagonist.split(",")[0].split("(")[0].strip().split()[0]
        # Common non-name starters that indicate an unnamed protagonist
        _NON_NAME_STARTERS = {
            "a", "an", "the", "my", "our", "one", "some", "this", "that",
            "young", "old", "determined", "brave", "strong", "mysterious",
        }
        if proto_first and len(proto_first) > 2 and proto_first.lower() not in _NON_NAME_STARTERS:
            if proto_first.lower() not in text_lower:
                issues["missing_protagonist_name"] = proto_first
        else:
            # Config protagonist has no real name — concept can't prove specificity
            issues["unnamed_protagonist_config"] = protagonist[:60]

    # 7. Synopsis restatement guard (bigram overlap)
    synopsis = config.get("synopsis", "")
    if synopsis and text:
        syn_words = synopsis.lower().split()
        txt_words = text_lower.split()
        if len(syn_words) >= 4 and len(txt_words) >= 4:
            syn_bigrams = set(zip(syn_words[:-1], syn_words[1:]))
            txt_bigrams = set(zip(txt_words[:-1], txt_words[1:]))
            if syn_bigrams:
                overlap = len(syn_bigrams & txt_bigrams) / len(syn_bigrams)
                if overlap > 0.5:
                    issues["synopsis_restatement"] = round(overlap, 2)

    # 8. Semantic similarity guard (catches paraphrase-based restatement)
    if synopsis and text and "synopsis_restatement" not in issues:
        sim = _semantic_similarity_check(synopsis, text)
        if sim > 0.85:
            issues["semantic_restatement"] = round(sim, 3)

    # 9. Input quality gate penalty — if the synopsis itself was generic,
    #    the concept is tainted even if it only echoes a few phrases.
    input_generic_count = config.get("_input_generic_count", 0)
    if input_generic_count >= 3:
        issues["input_quality_warning"] = input_generic_count

    # Score: start at 100, deduct for issues
    score = 100
    if "too_short" in issues:
        score -= 40
    if "too_long" in issues:
        score -= 10
    if "possible_truncation" in issues:
        score -= 20
    if "generic_phrases" in issues:
        score -= 8 * len(issues["generic_phrases"])
    if "missing_protagonist_name" in issues:
        score -= 15
    if "unnamed_protagonist_config" in issues:
        score -= 12
    if "synopsis_restatement" in issues:
        score -= 30
    if "semantic_restatement" in issues:
        score -= 25
    if "preamble_stripped" in issues:
        score -= 5
    if "input_quality_warning" in issues:
        # Scale: 3 generics in input = -15, 5+ = -25, 10+ = -40
        count = issues["input_quality_warning"]
        score -= min(5 * count, 40)

    return {
        "text": text,
        "score": max(0, score),
        "word_count": word_count,
        "issues": issues,
        "pass": score >= 50 and "too_short" not in issues,
    }


def build_concept_fingerprint(text: str) -> Dict[str, Any]:
    """Build a fingerprint for drift detection: hash + keywords + entities."""
    import hashlib
    clean = text.strip()

    # SHA256 hash for exact-match detection
    content_hash = hashlib.sha256(clean.encode("utf-8")).hexdigest()[:16]

    # Keyword extraction: significant words (4+ chars, not stopwords)
    stopwords = {
        "this", "that", "with", "from", "have", "been", "will", "would",
        "could", "should", "their", "there", "where", "when", "what",
        "about", "which", "into", "than", "then", "them", "they", "these",
        "those", "each", "every", "some", "more", "also", "just", "only",
        "very", "most", "much", "such", "like", "even", "after", "before",
        "between", "through", "during", "against", "without", "because",
        "while", "being", "having", "doing", "other", "another",
    }
    words = re.findall(r'\b[a-zA-Z]{4,}\b', clean.lower())
    word_freq = {}
    for w in words:
        if w not in stopwords:
            word_freq[w] = word_freq.get(w, 0) + 1
    keywords = sorted(word_freq, key=word_freq.get, reverse=True)[:15]

    # Entity extraction: capitalized words that aren't sentence starters
    sentences = re.split(r'[.!?]\s+', clean)
    entities = set()
    for sent in sentences:
        words_in_sent = sent.split()
        for i, w in enumerate(words_in_sent):
            if i > 0 and w[0:1].isupper() and w not in COMMON_CAPS and len(w) > 2:
                entities.add(w.rstrip(".,;:!?'\""))

    return {
        "hash": content_hash,
        "keywords": keywords,
        "entities": sorted(entities),
    }


def check_concept_drift(fingerprint: Dict[str, Any], stage_output: str,
                         threshold: float = 0.3) -> Dict[str, Any]:
    """Check if downstream stage output has drifted from concept fingerprint.

    Returns drift report with keyword overlap ratio and missing entities.
    """
    if not fingerprint or not stage_output:
        return {"drifted": False, "reason": "insufficient_data"}

    output_lower = stage_output.lower()
    fp_keywords = fingerprint.get("keywords", [])
    fp_entities = fingerprint.get("entities", [])

    # Keyword overlap
    if fp_keywords:
        present = sum(1 for kw in fp_keywords if kw in output_lower)
        keyword_overlap = present / len(fp_keywords)
    else:
        keyword_overlap = 1.0

    # Entity presence
    missing_entities = [e for e in fp_entities if e.lower() not in output_lower]

    drifted = keyword_overlap < threshold
    return {
        "drifted": drifted,
        "keyword_overlap": round(keyword_overlap, 2),
        "keywords_checked": len(fp_keywords),
        "keywords_found": int(keyword_overlap * len(fp_keywords)) if fp_keywords else 0,
        "missing_entities": missing_entities,
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


# Common capitalized words that are NOT entity names (sentence starters, titles, etc.)
# Used by entity guard to avoid counting these as "shared nouns"
COMMON_CAPS = {
    "The", "This", "That", "These", "Those", "There", "Their", "They",
    "She", "Her", "His", "Him", "Not", "But", "And", "For", "Its",
    "Was", "Were", "Are", "Has", "Had", "Have", "Did", "Does",
    "May", "Can", "Will", "Would", "Could", "Should", "Might",
    "Now", "Then", "Here", "Where", "When", "How", "Why", "What",
    "Who", "Whom", "Which", "Each", "Every", "Some", "Any", "All",
    "Before", "After", "During", "Between", "Among",
    "Chapter", "Scene", "Part", "Section", "Page",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    "January", "February", "March", "April", "June", "July",
    "August", "September", "October", "November", "December",
    "General", "Captain", "Doctor", "Professor", "Father", "Mother",
    "Sir", "Lord", "Lady", "King", "Queen", "Prince", "Princess",
}

# --- Cleanup regex constants (spec: genre-agnostic, high-confidence markers only) ---
REST_UNCHANGED_RE = re.compile(
    r"(?is)\b("
    r"the\s+rest\s+(of\s+the\s+(?:scene|chapter)\s+)?remains\s+unchanged"
    r"|the\s+rest\s+remains\s+unchanged"
    r"|rest\s+of\s+the\s+(?:scene|chapter)\s+remains\s+unchanged"
    r"|everything\s+after\s+this\s+remains\s+unchanged"
    r"|no\s+further\s+changes\s+were\s+made"
    r")\b"
)

MIN_PREFIX_CHARS = 400
MIN_PREFIX_LINES = 8

LLM_PREAMBLE_RE = re.compile(
    r"(?ims)"
    r"(?:certainly!?\s*|sure!?\s*|of\s+course!?\s*|as\s+requested,?\s*)?"
    r"(?:here\s+is|below\s+is)\s+"
    r"(?:the\s+)?(?:revised|updated|new)\s+"
    r"(?:opening|version|scene|chapter|section|passage)\b",
)


def _validate_yaml_config(data: Dict[str, Any], config_name: str,
                          expected_keys: set, regex_keys: set = None) -> Dict[str, Any]:
    """Lightweight schema validation for YAML config files.

    Checks: expected keys exist, regex patterns compile, values are correct types.
    Returns validated data (may be modified with warnings logged).
    """
    if not isinstance(data, dict):
        logger.warning(f"{config_name}: expected dict, got {type(data).__name__}. Using empty config.")
        return {}
    # Check for unexpected top-level keys
    unknown = set(data.keys()) - expected_keys
    if unknown:
        logger.warning(f"{config_name}: unknown keys {unknown} (will be ignored)")
    # Validate regex patterns compile
    for key in (regex_keys or set()):
        patterns = data.get(key, [])
        if isinstance(patterns, list):
            for i, item in enumerate(patterns):
                pat = item.get("pattern") if isinstance(item, dict) else item if isinstance(item, str) else None
                if pat:
                    try:
                        re.compile(pat)
                    except re.error as e:
                        logger.error(f"{config_name}: invalid regex in {key}[{i}]: {e}. Removing.")
                        if isinstance(patterns, list) and i < len(patterns):
                            patterns[i] = None
            data[key] = [p for p in patterns if p is not None]
    return data


_cached_cleanup_config: Optional[Dict[str, Any]] = None


def _load_cleanup_config() -> Dict[str, Any]:
    """Load optional cleanup patterns from configs/cleanup_patterns.yaml.

    Cached after first load to avoid repeated file I/O during scene processing.
    """
    global _cached_cleanup_config
    if _cached_cleanup_config is not None:
        return _cached_cleanup_config
    try:
        config_path = Path(__file__).resolve().parent.parent / "configs" / "cleanup_patterns.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            _cached_cleanup_config = _validate_yaml_config(
                data, "cleanup_patterns.yaml",
                expected_keys={"inline_truncate_markers", "inline_preamble_markers",
                               "regex_patterns", "disabled_builtins", "inline"},
                regex_keys={"regex_patterns"}
            )
            logger.info("Loaded cleanup_patterns.yaml (cached for session — restart to pick up edits)")
            return _cached_cleanup_config
    except Exception as e:
        logger.warning(f"Failed to load cleanup_patterns.yaml: {e}")
    _cached_cleanup_config = {}
    return _cached_cleanup_config


# Cleanup morgue: log every "smart deletion" for auditability
_cleanup_morgue: List[Dict[str, Any]] = []


def _log_to_morgue(scene_id: str, deleted_text: str, trigger_pattern: str,
                   phase: str = "", anchor_check: str = ""):
    """Log a deletion to the cleanup morgue for post-run audit."""
    if deleted_text and len(deleted_text.strip()) > 5:
        _cleanup_morgue.append({
            "scene_id": scene_id,
            "deleted_text": deleted_text.strip()[:200],
            "trigger_pattern": trigger_pattern,
            "phase": phase,
            "anchor_check": anchor_check,
        })


def _flush_morgue(project_path):
    """Write morgue entries to JSONL file and clear buffer."""
    global _cleanup_morgue
    if not _cleanup_morgue or not project_path:
        return
    try:
        morgue_path = Path(project_path) / "cleanup_morgue.jsonl"
        # Morgue size limit: rotate if file exceeds 5MB
        _MORGUE_MAX_BYTES = 5 * 1024 * 1024
        if morgue_path.exists() and morgue_path.stat().st_size > _MORGUE_MAX_BYTES:
            rotated = morgue_path.with_suffix(".jsonl.old")
            try:
                if rotated.exists():
                    rotated.unlink()
                morgue_path.rename(rotated)
                logger.info(f"Cleanup morgue rotated (>{_MORGUE_MAX_BYTES // (1024*1024)}MB)")
            except Exception as rot_e:
                logger.warning(f"Morgue rotation failed: {rot_e}")
        with open(morgue_path, "a", encoding="utf-8") as f:
            for entry in _cleanup_morgue:
                f.write(json.dumps(entry) + "\n")
        logger.info(f"Cleanup morgue: {len(_cleanup_morgue)} deletions logged to {morgue_path}")
    except Exception as e:
        logger.warning(f"Failed to write cleanup morgue: {e}")
    _cleanup_morgue = []


# Incident log: structured records for rollbacks and defense events
_incident_buffer: List[Dict[str, Any]] = []


# Transient failure patterns (API/infrastructure issues, retryable)
_TRANSIENT_ERROR_PATTERNS = [
    r"timeout", r"rate.?limit", r"429", r"503", r"502", r"connection",
    r"network", r"socket", r"ssl", r"dns", r"ECONNRESET", r"ETIMEDOUT",
    r"api.*error", r"service.*unavailable", r"quota.*exceeded",
]


def _classify_failure(error_msg: str) -> str:
    """Classify a failure as 'transient' (infrastructure) or 'content' (validation)."""
    if not error_msg:
        return "unknown"
    msg_lower = error_msg.lower()
    for pat in _TRANSIENT_ERROR_PATTERNS:
        if re.search(pat, msg_lower):
            return "transient"
    return "content"


def _log_incident(stage: str, category: str, detail: str, severity: str = "error",
                  scene_count_before: int = 0, scene_count_after: int = 0,
                  failure_type: str = ""):
    """Log an incident for post-run analysis (rollbacks, circuit breaker trips, etc.)."""
    if not failure_type:
        failure_type = _classify_failure(detail)
    _incident_buffer.append({
        "timestamp": datetime.now().isoformat(),
        "stage": stage,
        "category": category,
        "severity": severity,
        "failure_type": failure_type,
        "detail": detail,
        "scene_count_before": scene_count_before,
        "scene_count_after": scene_count_after,
    })


def _flush_incidents(project_path):
    """Write incident buffer to incidents.jsonl and clear."""
    global _incident_buffer
    if not _incident_buffer or not project_path:
        return
    try:
        incident_path = Path(project_path) / "incidents.jsonl"
        with open(incident_path, "a", encoding="utf-8") as f:
            for entry in _incident_buffer:
                f.write(json.dumps(entry) + "\n")
        logger.info(f"Incidents: {len(_incident_buffer)} events logged to {incident_path}")
    except Exception as e:
        logger.warning(f"Failed to write incidents: {e}")
    _incident_buffer = []


def _clean_scene_content(text: str, scene_id: str = "") -> str:
    """Strip meta-text, LLM preambles, editing artifacts, and analysis notes.

    Catches all known artifact categories:
    1. Analysis/checklist appendices ("Changes made:", "Scanning for AI tells:")
    2. LLM preambles ("Sure, here's...", "Here is the revised...")
    3. Prompt bleed-through ("CURRENT SCENE:", "A great chapter-ending hook can be:")
    4. Section markers ("=== EXPANDED SCENE ===", "ENHANCED SCENE:")
    5. UI/formatting artifacts ("Visible: 0%", percentage markers)
    6. Instruction echoes ("Output ONLY the revised scene")

    Optional: configs/cleanup_patterns.yaml can add extra inline patterns.

    Salvage guardrail: If cleanup strips content to <50 words, restores the
    pre-cleanup input rather than passing corrupt/empty content downstream.
    """
    import re
    _original_input = text  # Keep for salvage restore

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
        r'(?:[^.:\n]{0,60}(?:opening|version|scene|chapter)[^.:\n]{0,40})?[.:]\s*\n+',
        r'^(?:Sure|Certainly|Of course|Absolutely)[,!.]\s*(?:here\'?s?|I\'ve|I have|let me|here is)'
        r'[^\n]{0,100}\n+',
        r'^(?:I\'ve |I have )(?:revised|enhanced|polished|expanded|edited|rewritten)'
        r'[^\n]{0,80}\n+',
        r'^(?:Below is|The following is|What follows is)[^\n]{0,60}\n+',
    ]
    for pattern in preamble_patterns:
        text = re.sub(pattern, '', text, count=1, flags=re.IGNORECASE)

    # --- PHASE 1.5: Truncate at "rest remains unchanged" (discard alternate versions) ---
    rest_match = REST_UNCHANGED_RE.search(text)
    if rest_match:
        pre = text[:rest_match.start()].rstrip()
        text = pre
        logger.info("Cleanup: truncated at rest-unchanged marker (kept %d chars)", len(pre))
    else:
        # Optional YAML markers (add more truncate points)
        cleanup_cfg = _load_cleanup_config()
        for marker in cleanup_cfg.get("inline_truncate_markers", []) or []:
            if not isinstance(marker, str):
                continue
            pos = text.lower().find(marker.lower())
            if pos >= 0:
                pre = text[:pos].rstrip()
                text = pre
                logger.info("Cleanup: truncated at YAML marker %r (kept %d chars)", marker[:40], len(pre))
                break

    # --- PHASE 1.6: Truncate at LLM preamble mid-text (wrong pasted assistant content) ---
    mid_match = LLM_PREAMBLE_RE.search(text)
    if mid_match:
        pre = text[:mid_match.start()].rstrip()
        prefix_chars = len(pre)
        prefix_lines = len(pre.splitlines())
        if prefix_chars >= MIN_PREFIX_CHARS or prefix_lines >= MIN_PREFIX_LINES:
            text = pre
            logger.info(
                "Cleanup: truncated at mid-text LLM preamble (kept %d chars, %d lines)",
                prefix_chars, prefix_lines,
            )
    else:
        cleanup_cfg = _load_cleanup_config()
        for marker in cleanup_cfg.get("inline_preamble_markers", []) or []:
            if not isinstance(marker, str):
                continue
            pos = text.lower().find(marker.lower())
            if pos >= 0:
                pre = text[:pos].rstrip()
                if len(pre) >= MIN_PREFIX_CHARS or len(pre.splitlines()) >= MIN_PREFIX_LINES:
                    text = pre
                    logger.info("Cleanup: truncated at YAML preamble marker %r", marker[:40])
                break

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
        # Assistant-style closers (chatbot bleed-through)
        r'\n(?:I can help|Let me know if you)',
    ]

    for pattern in tail_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = text[:match.start()].rstrip()
            if len(candidate) > 100:
                text = candidate

    # --- PHASE 2.5: Post-truncation salvage guardrail ---
    # After truncation, if remaining content is too small, RESTORE pre-cleanup input
    # rather than passing corrupt/empty content downstream
    stripped = text.strip()
    word_count = len(stripped.split())
    paragraph_count = len([p for p in stripped.split('\n\n') if p.strip()])
    if word_count < 150 or paragraph_count < 2:
        if word_count < 50:
            original_wc = len((_original_input or "").split())
            logger.warning(
                f"Cleanup salvage failed: only {word_count} words, {paragraph_count} paragraphs "
                f"after truncation. Content may be corrupt."
            )
            # If the original had substantially more content, restore it
            # (the cleanup was too aggressive — better to have artifacts than nothing)
            if original_wc > word_count * 3 and original_wc >= 50:
                # Check if original contains hard meta-markers — if so, restore
                # but flag for regen rather than shipping garbage
                _hard_markers = [
                    r'(?i)certainly!?\s*here\s+is',
                    r'(?i)the\s+rest\s+remains?\s+unchanged',
                    r'(?i)changes\s+made:',
                    r'(?i)here\s+is\s+the\s+revised',
                ]
                has_hard_meta = any(
                    re.search(pat, _original_input) for pat in _hard_markers
                )
                logger.warning(
                    f"Salvage: restoring pre-cleanup input ({original_wc} words) "
                    f"instead of stripped output ({word_count} words)"
                    f"{' [contains meta-markers, needs regen]' if has_hard_meta else ''}"
                )
                _log_to_morgue(
                    scene_id, stripped[:200],
                    "salvage_restore",
                    phase="2.5_salvage",
                    anchor_check=f"restored_wc={original_wc},stripped_wc={word_count},has_meta={has_hard_meta}"
                )
                text = _original_input

    # --- PHASE 3: Inline artifact removal (patterns that appear MID-text) ---
    # Each pattern is (name, regex). Names enable exact disabled_builtins matching.
    _named_inline_patterns = [
        ("rest_unchanged", r'(?:The )?rest (?:of (?:the |this )?(?:scene|chapter|text|content) )?'
         r'(?:remains?|is) unchanged[^.]*[.\s]*'),
        ("rest_unchanged_bracket", r'\[(?:The )?rest (?:of (?:the |this )?(?:scene|chapter))? remains unchanged[^\]]*\]\s*'),
        ("current_scene_header", r'CURRENT SCENE(?: MODIFIED)?:\s*'),
        ("visible_pct_marker", r'Visible:\s*\d+%\s*[–—-]\s*\d+%\s*'),
        ("enhanced_scene_header", r'(?:ENHANCED|EXPANDED|POLISHED|FIXED|REVISED) SCENE:\s*'),
        ("heres_revised", r'(?:Sure[,.]?\s*)?[Hh]ere\'?s?\s+(?:the |a )?(?:revised|enhanced|polished|expanded|edited)'
         r'\s+(?:version|scene|text|content)[.:]\s*'),
        ("hook_instruction_bleed", r'A great chapter-(?:ending|opening) hook can be:\s*(?:\n[-•*][^\n]+)*'),
        ("writing_tips_bullets", r'(?:\n[-•*]\s*(?:A cliffhanger|In medias res|A striking sensory|'
         r'A provocative|Immediate conflict|Disorientation|A kiss or romantic|'
         r'A threat delivered|A question raised|A twist revealed|'
         r'An emotional gut-punch|A decision made)[^\n]*)+'),
        ("scene_header_chapter", r'Chapter\s+\d+,?\s*Scene\s+\d+\s*(?:POV:[^\n]*)?'),
        ("scene_header_pov", r'POV:\s*FIRST PERSON[^\n]*'),
        ("scene_header_count", r'Scene\s+\d+\s+of\s+\d+[^\n]*'),
        ("xml_tag_scene", r'</?scene[^>]*>'),
        ("xml_tag_chapter", r'</?chapter[^>]*>'),
        ("xml_tag_content", r'</?content[^>]*>'),
        ("beat_sheet_physical", r'Physical beats:\s*(?:\n[-•*][^\n]+)*'),
        ("beat_sheet_emotional", r'Emotional beats:\s*(?:\n[-•*][^\n]+)*'),
        ("beat_sheet_sensory", r'Sensory details:\s*(?:\n[-•*][^\n]+)*'),
    ]

    # Merge optional custom patterns from configs/cleanup_patterns.yaml
    cleanup_cfg = _load_cleanup_config()
    for item in cleanup_cfg.get("inline", []) or []:
        if isinstance(item, str):
            _named_inline_patterns.append(("custom_inline", item))
    for item in cleanup_cfg.get("regex_patterns", []) or []:
        if isinstance(item, dict) and item.get("pattern"):
            _named_inline_patterns.append((item.get("name", "custom_regex"), item["pattern"]))

    # Filter out disabled built-in patterns by exact pattern_name.
    # Also supports legacy substring matching as fallback.
    disabled = cleanup_cfg.get("disabled_builtins", []) or []
    if disabled:
        disabled_set = set(d.strip() for d in disabled if isinstance(d, str))
        _named_inline_patterns = [
            (name, pat) for name, pat in _named_inline_patterns
            if name not in disabled_set and not any(d.lower() in pat.lower() for d in disabled_set)
        ]

    for _name, pattern in _named_inline_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            _log_to_morgue(scene_id, match.group(0), _name, phase="3_inline")
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # --- PHASE 4: Clean up whitespace artifacts ---
    # Remove resulting blank lines (3+ newlines -> 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove trailing whitespace on lines
    text = re.sub(r' +\n', '\n', text)

    return text.strip()


def _mask_quoted_dialogue(text: str):
    """Mask text inside quotation marks to protect dialogue from POV replacement.

    Returns (masked_text, restore_fn). Call restore_fn(modified_text) to put
    dialogue back. This prevents "He said" inside dialogue from being converted.
    """
    placeholders = {}
    counter = [0]

    boundary_puncs = {}  # key -> punctuation char added after placeholder

    def _replacer(match):
        key = f"__DIALOGUE_{counter[0]}__"
        quoted = match.group(0)
        placeholders[key] = quoted
        counter[0] += 1
        # Preserve sentence boundary: if the quote ends with punctuation before
        # the closing quote mark, keep that punctuation after the placeholder
        # so patterns like (?<=[.!?]\s) still match after the dialogue
        inner = quoted[1:-1] if len(quoted) >= 2 else ""
        if inner and inner[-1] in '.!?':
            boundary_puncs[key] = inner[-1]
            return key + inner[-1]
        return key

    # Match \u201c...\u201d and "..." style quotes
    masked = re.sub(r'[\u201c"][^\u201d"]*[\u201d"]', _replacer, text)
    masked = re.sub(r'"[^"]*"', _replacer, masked)
    # Italic thoughts: *thought text* (single asterisks, not bold **)
    masked = re.sub(r'(?<!\*)\*(?!\*)[^*\n]{3,80}\*(?!\*)', _replacer, masked)
    # Italic thoughts: _thought text_ (underscore style, not __bold__)
    masked = re.sub(r'(?<!_)_(?!_)[^_\n]{3,80}_(?!_)', _replacer, masked)
    # Block quotes: lines starting with >
    masked = re.sub(r'^>[^\n]+', _replacer, masked, flags=re.MULTILINE)
    # Bracketed message blocks: [Text message:] ... or [Letter:]
    masked = re.sub(r'\[[^\]]{3,80}\]', _replacer, masked)

    def restore(modified_text):
        result = modified_text
        for key, original in placeholders.items():
            # If we added boundary punctuation, remove it alongside the placeholder
            if key in boundary_puncs:
                result = result.replace(key + boundary_puncs[key], original)
            result = result.replace(key, original)
        return result

    return masked, restore


def _enforce_first_person_pov(text: str, protagonist_name: str = "",
                              protagonist_gender: str = "") -> str:
    """Code-level enforcement of first-person POV with GENDER AWARENESS.

    CRITICAL: Only convert pronouns that match the PROTAGONIST's gender.
    - Male protagonist (Ethan): convert He/His/Him → I/My/Me. LEAVE She/Her alone.
    - Female protagonist (Lena): convert She/Her → I/My. LEAVE He/His alone.
    - Unknown gender: only convert [Name] references, skip pronoun fixes.

    Dialogue inside quotation marks is PROTECTED (masked before replacement,
    restored after). This prevents "He" in dialogue from being converted.

    This prevents the catastrophic bug where "her hair" (referring to the
    love interest) gets converted to "my hair" for a male narrator.
    """
    if not text or not protagonist_name:
        return text

    names = [n.strip() for n in protagonist_name.split() if len(n.strip()) > 1]
    first_name = names[0] if names else ""
    if not first_name:
        return text

    # Protect dialogue from pronoun replacement (mask quotes, restore after)
    text, restore_dialogue = _mask_quoted_dialogue(text)

    gender = protagonist_gender.lower().strip()

    # Determine which pronouns belong to the protagonist
    if gender == "male":
        subj_pronoun = "He"     # "He walked" -> "I walked"
        poss_pronoun_cap = "His"  # "His jaw" -> "My jaw"
        poss_pronoun = "his"    # "his jaw" -> "my jaw"
    elif gender == "female":
        subj_pronoun = "She"
        poss_pronoun_cap = "Her"
        poss_pronoun = "her"
    else:
        # Unknown gender: only fix [Name] references, skip all pronoun fixes
        subj_pronoun = None
        poss_pronoun_cap = None
        poss_pronoun = None

    # Common past-tense verbs for "[Name/Pronoun] [verb]" patterns
    verbs = (r"felt|thought|noticed|realized|knew|watched|saw|heard|"
             r"walked|turned|looked|moved|pulled|pushed|grabbed|reached|"
             r"smiled|laughed|sighed|whispered|murmured|said|asked|"
             r"wondered|considered|remembered|imagined|wished|hoped|"
             r"tightened|clenched|tamed|tugged|brushed|ran|stood|sat|"
             r"leaned|stepped|glanced|stared|paused|stopped|started|"
             r"shook|nodded|blinked|swallowed|inhaled|exhaled|breathed")

    aux_verbs = r"was|had|would|could|didn't|couldn't|wouldn't|wasn't|hadn't"

    body_parts = (r'hand|heart|jaw|throat|stomach|chest|fingers|eyes|voice|'
                  r'mind|head|breath|hair|shoulder|back|arm|leg|pulse|skin|'
                  r'lip|lips|cheek|face|gaze|palms|wrist|temple|forehead|'
                  r'collarbone|ribcage|spine|hips|knees|ankles|neck|chin|'
                  r'brow|eyebrow|eyelid|nostril|ear|elbow|fingertips|'
                  r'lungs|ribs|belly|navel|waist')

    # === ALWAYS SAFE: Fix "[FirstName] verb" -> "I verb" ===
    text = re.sub(
        rf'\b{re.escape(first_name)}\s+({verbs})\b',
        r'I \1',
        text
    )

    # === ALWAYS SAFE: Fix "[FirstName]'s [body part]" -> "my [body part]" ===
    def _possessive_replacement(match):
        body = match.group(1)
        start = match.start()
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

    # === GENDER-SPECIFIC: Only fix pronouns matching protagonist's gender ===
    # Name-aware pronoun guard: if other characters of the same gender are
    # mentioned near a pronoun, the pronoun likely refers to them, not protagonist.
    # We check per-paragraph: if a paragraph contains another same-gender character
    # name, we skip pronoun→I conversion for that paragraph.
    _other_same_gender_names: set = set()
    # (populated lazily below when subj_pronoun is set)

    if subj_pronoun:
        # Build set of other character names that share protagonist's gender
        # by checking if the config has other_characters info
        # We use a simple heuristic: names that appear in the text are relevant
        import os as _os  # only for env check, not used otherwise
        # Extract capitalized names from the text that aren't the protagonist
        _all_caps_names = set(re.findall(r'\b[A-Z][a-z]{2,}\b', text))
        _all_caps_names.discard(first_name)
        # Common words that look like names but aren't
        _common_caps = {"The", "This", "That", "When", "Where", "What", "How",
                        "Then", "But", "And", "His", "Her", "She", "They",
                        "Chapter", "Scene", "Part"}
        _other_same_gender_names = _all_caps_names - _common_caps

        # Per-paragraph name-aware replacement
        paragraphs = text.split('\n\n')
        new_paragraphs = []
        for para in paragraphs:
            # Check if paragraph mentions any other capitalized name
            para_has_other_name = any(
                re.search(rf'\b{re.escape(n)}\b', para) for n in _other_same_gender_names
            )
            if para_has_other_name:
                # Skip pronoun→I for this paragraph (ambiguous who "He/She" refers to)
                new_paragraphs.append(para)
                continue

            # Safe to convert: paragraph only has protagonist
            for boundary in [rf'^{subj_pronoun}', rf'(?<=[.!?]\s){subj_pronoun}', rf'(?<=\n){subj_pronoun}']:
                para = re.sub(rf'{boundary}\s+({verbs})\b', r'I \1', para)
                para = re.sub(rf'{boundary}\s+({aux_verbs})\b', r'I \1', para)

            # Fix "[Pronoun]'d" -> "I'd", "[Pronoun]'s" -> "I'm" contractions
            for boundary in [rf'(?<=[.!?]\s){subj_pronoun}', rf'(?<=\n){subj_pronoun}']:
                para = re.sub(rf"{boundary}'d\b", "I'd", para)
                para = re.sub(rf"{boundary}'s\b", "I'm", para)

            new_paragraphs.append(para)
        text = '\n\n'.join(new_paragraphs)

    if poss_pronoun_cap:
        # Fix "[PossPronoun] [body part]" -> "My [body part]" at sentence starts
        for boundary in [rf'^{poss_pronoun_cap}', rf'(?<=[.!?]\s){poss_pronoun_cap}', rf'(?<=\n){poss_pronoun_cap}']:
            text = re.sub(rf'{boundary}\s+({body_parts})\b', r'My \1', text)

    if poss_pronoun:
        # Fix mid-sentence "[poss_pronoun] [body part]" -> "my [body part]"
        # ONLY for the protagonist's pronoun, not the opposite gender
        # CLAUSE GUARD: Skip if preceded by relative pronoun/clause marker
        # (e.g. "the woman who had been his closest friend" should NOT become "my closest friend")
        def _safe_poss_replace(match):
            start = match.start()
            # Look back up to 20 chars for clause markers
            lookback = text[max(0, start-20):start].lower()
            # Skip if inside a relative clause (who, that, which, whose, whom, where)
            if re.search(r'\b(?:who|that|which|whose|whom|where|when)\s+(?:\w+\s+)*$', lookback):
                return match.group(0)  # Keep original
            # Skip if preceded by "of" (e.g. "a friend of his" should stay)
            if lookback.rstrip().endswith(' of'):
                return match.group(0)
            return f'my {match.group(1)}'

        text = re.sub(
            rf'\b{poss_pronoun}\s+({body_parts})\b',
            _safe_poss_replace,
            text
        )

    # Restore masked dialogue
    text = restore_dialogue(text)

    return text


def _repair_pov_context_errors(text: str, protagonist_gender: str = "") -> str:
    """Fix contextual POV corruption where third-person subject + first-person possessive clash.

    The #1 defect in qwen2.5:14b output: when Ana (third person) does something,
    the LLM writes "my" for her body/voice/face instead of "her".

    High-confidence patterns (almost never produce false positives):
    1. "she said/whispered/asked, my voice..." -> "her voice"
    2. "she said, my eyes sparkling" -> "her eyes sparkling"
    3. "She rolled my eyes" -> "She rolled her eyes"
    4. "I smiled warmly, gazing at me" -> "She smiled warmly, gazing at me"
    5. "I turned to face me" -> "She turned to face me"
    """
    if not text:
        return text

    gender = protagonist_gender.lower().strip()

    # Determine the OTHER character's pronouns (the non-narrator)
    if gender == "male":
        other_subj = "she"
        other_subj_cap = "She"
        other_poss = "her"
        other_poss_cap = "Her"
    elif gender == "female":
        other_subj = "he"
        other_subj_cap = "He"
        other_poss = "his"
        other_poss_cap = "His"
    else:
        return text  # Can't fix without knowing gender

    # Body/attribute nouns that get misattributed
    body_attrs = (r'voice|eyes|face|lips|head|hair|gaze|smile|expression|'
                  r'brow|eyebrow|chin|jaw|cheek|shoulder|shoulders|hand|hands|'
                  r'fingers|finger|arm|arms|back|chest|breath|wrist|palm|palms|'
                  r'forehead|temple|ear|ears|neck|nose|mouth|knees|lap|'
                  r'foot|feet|leg|legs|hip|hips|skin|throat|tongue')

    # Dialogue/action verbs that signal the SUBJECT is the non-narrator
    dialogue_verbs = (r'said|whispered|murmured|called|replied|asked|answered|'
                      r'continued|began|started|added|suggested|admitted|'
                      r'laughed|smiled|grinned|chuckled|sighed|exclaimed|'
                      r'urged|teased|joked|offered|warned|promised|'
                      r'shouted|yelled|cried|sobbed|snapped|hissed|groaned')

    # === PATTERN 1: "she [dialogue_verb], my [body_attr]" -> "her [body_attr]" ===
    # This catches: "she whispered, my voice barely audible"
    # The possessive after a comma following her dialogue tag = HER attribute
    text = re.sub(
        rf'({other_subj_cap}|{other_subj})\s+({dialogue_verbs})(\s*,\s*)my\s+({body_attrs})\b',
        lambda m: f'{m.group(1)} {m.group(2)}{m.group(3)}{other_poss} {m.group(4)}',
        text,
        flags=re.IGNORECASE
    )

    # === PATTERN 2: "[Name] [dialogue_verb], my [body_attr]" -> "her [body_attr]" ===
    # Catches: "Ana said, my voice soft and clear"
    # We match any capitalized word + dialogue verb + comma + "my [body]"
    text = re.sub(
        rf'(\b[A-Z][a-z]+)\s+({dialogue_verbs})(\s*,\s*)my\s+({body_attrs})\b',
        lambda m: f'{m.group(1)} {m.group(2)}{m.group(3)}{other_poss} {m.group(4)}',
        text,
        flags=re.IGNORECASE
    )

    # === PATTERN 3: "She [self-action verb] my [body_attr]" -> "her [body_attr]" ===
    # Catches: "She rolled my eyes", "She tilted my head", "She shook my head"
    # These verbs imply the subject acts on THEIR OWN body part
    self_action_verbs = (r'rolled|tilted|shook|nodded|tossed|flipped|'
                         r'narrowed|widened|closed|squeezed|pursed|'
                         r'bit|clenched|rubbed|tucked|brushed')
    text = re.sub(
        rf'({other_subj_cap})\s+({self_action_verbs})\s+my\s+({body_attrs})\b',
        lambda m: f'{m.group(1)} {m.group(2)} {other_poss} {m.group(3)}',
        text
    )

    # === PATTERN 4: "I [verb], [gerund] at/to me" -> "She [verb], [gerund] at/to me" ===
    # Catches: "I smiled warmly, gazing at me" (should be "She smiled warmly, gazing at me")
    # The gerund clause targeting "me" means the subject is the OTHER person
    gerunds = r'gazing|looking|staring|smiling|grinning|beaming|glancing|peering|waving'
    text = re.sub(
        rf'^I\s+({dialogue_verbs})(\s+\w+)?\s*,\s*({gerunds})\s+at\s+me\b',
        lambda m: f'{other_subj_cap} {m.group(1)}{m.group(2) or ""}, {m.group(3)} at me',
        text,
        flags=re.MULTILINE
    )
    text = re.sub(
        rf'(?<=[.!?]\s)I\s+({dialogue_verbs})(\s+\w+)?\s*,\s*({gerunds})\s+at\s+me\b',
        lambda m: f'{other_subj_cap} {m.group(1)}{m.group(2) or ""}, {m.group(3)} at me',
        text
    )

    # === PATTERN 5: "I [verb] at/to me" (self-referential) -> "She [verb] at/to me" ===
    # Catches: "I turned to face me", "I looked up at me", "I glanced at me"
    look_verbs = r'turned|looked|glanced|smiled|waved|nodded|called|reached'
    text = re.sub(
        rf'^I\s+({look_verbs})\s+(?:to face|at|toward|towards)\s+me\b',
        lambda m: f'{other_subj_cap} {m.group(1)} {m.group(0).split(m.group(1), 1)[1].strip().split("I ", 1)[-1] if "I " in m.group(0) else m.group(0)[len("I " + m.group(1)):]}',
        text,
        flags=re.MULTILINE
    )
    # Simpler version for common patterns:
    text = re.sub(
        r'\bI turned to face me\b',
        f'{other_subj_cap} turned to face me',
        text
    )
    text = re.sub(
        r'\bI looked (?:up )?at me\b',
        f'{other_subj_cap} looked at me',
        text
    )
    text = re.sub(
        r'\bI glanced at me\b',
        f'{other_subj_cap} glanced at me',
        text
    )
    text = re.sub(
        r'\bI smiled back at me\b',
        f'{other_subj_cap} smiled back at me',
        text
    )
    text = re.sub(
        r'\bI stood beside me\b',
        f'{other_subj_cap} stood beside me',
        text
    )

    # === PATTERN 6: "I followed my back" -> "I followed her back" ===
    text = re.sub(
        r'\bI followed my\s+(back|lead)\b',
        lambda m: f'I followed {other_poss} {m.group(1)}',
        text
    )

    # === PATTERN 7: Strip stray markdown bold from prose ===
    # Only strip **bold** markers. Single *italic* is preserved for inner voice
    # (e.g. wolf voice: *Mine. Ours. Protect.*) which is a legitimate style element.
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)

    # === PATTERN 8: Generic clause-level POV clash ===
    # Any comma-delimited clause containing BOTH a third-person subject (she/he)
    # and a first-person possessive (my/me) is a POV clash.
    # "She turned, my hand trembling" → "She turned, her hand trembling"
    # "He leaned forward, my breath catching" → "He leaned forward, his breath catching"
    def _fix_clause_pov(match):
        clause = match.group(0)
        # Determine which third-person is present
        has_she = bool(re.search(r'\b[Ss]he\b', clause))
        has_he = bool(re.search(r'\b[Hh]e\b', clause)) and not has_she
        if has_she:
            clause = re.sub(r'\bmy\b', 'her', clause)
            clause = re.sub(r'\bMy\b', 'Her', clause)
        elif has_he:
            clause = re.sub(r'\bmy\b', 'his', clause)
            clause = re.sub(r'\bMy\b', 'His', clause)
        return clause

    # Match: [She/He ...], [my ...] within same comma-segment pair
    # Requires third-person subject in first clause, first-person possessive in second
    text = re.sub(
        r'(?<=[.!?]\s)\b(?:She|He)\b[^,]{3,40},\s*(?:my|My)\b[^.!?]{3,60}[.!?]',
        _fix_clause_pov,
        text
    )

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
        r"[A-Z][^.]{0,40}a sense of (?:something|hope|possibility|belonging|peace|closure|completion|"
        r"closure mixed with|anticipation|connection|warmth|longing)",
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
        r"The (?:weight|warmth|promise|reality|truth|beauty|gravity|fragility|possibilities|"
        r"thought|notion|idea) of (?:that|this|the|their|what|it|facing|an uncertain|our)\b",

        # === NEW PATTERNS from Seat 27B audit (40+ missed) ===
        # "sometimes [gerund/stepping/etc.]..."
        r"[Ss]ometimes(?:,)?\s+(?:stepping|it's in|it takes|the best|you just|love|life)\b",
        # "This [small/encounter/connection] [verb]..."
        r"This (?:small moment|encounter|connection|journey) (?:encapsulated|felt|was|had)\b",
        # "Our connection/journey had..."
        r"Our (?:connection|journey|night|relationship) (?:had|felt|was|blossomed|deepened)\b",
        # "The future/world/room/city [verb]..."
        r"The (?:future|world|room|city|day|night|possibilities) (?:remained|felt|seemed|outside|stretched)\b",
        # "new and hopeful" / "newfound hope"
        r"[^.]{0,30}(?:new and hopeful|newfound hope|flicker of hope|glimmering hope|hope that filled)\b",
        # Aphoristic endings with "it was both..."
        r"It was both (?:exhilarating|terrifying|beautiful|painful|liberating|overwhelming)\b",
        # "I felt [abstract noun] [growing/building/settling]..."
        r"I felt (?:belonging|hope|peace|gratitude|connection|warmth|something)\s+"
        r"(?:starting to|take root|growing|building|settling|stirring|blossoming)\b",
        # "a thread/bridge/link between..."
        r"[^.]{0,30}(?:a thread|a bridge|a link|an invisible thread) between\b",
        # "Yet amidst the uncertainty..."
        r"Yet (?:amidst|despite|in spite of|through) the (?:uncertainty|chaos|confusion|distance|pain)\b",
        # "was setting me on a new path"
        r"[^.]{0,40}(?:setting me on|putting me on|leading me toward) a new (?:path|direction|chapter)\b",
        # "each word/step/moment felt like..."
        r"[Ee]ach (?:word|step|moment|breath|gesture|touch) felt like\b",
        # "a testament to..."
        r"[^.]{0,30}a testament to (?:the|our|their|how)\b",
        # "with [pronoun] by my side..."
        r"[Ww]ith (?:her|him|Ana|them) by my side,?\s*(?:I felt|everything|the world|nothing)\b",
        # "what came/comes next" as emotional summary
        r"[^.]{0,30}(?:whatever|what(?:ever)?)\s+(?:came|comes|lay|lies|awaited)\s+(?:next|ahead)\b",
        # "there was no going back"
        r"[Tt]here was no going back\b",
        # "a chance for something new"
        r"[^.]{0,30}a chance for something (?:new|different|real|beautiful|more)\b",
        # "The [noun] around me [verb]"
        r"The (?:room|world|city|air|space|noise|sounds?) around (?:me|us) (?:seemed|felt|faded|"
        r"dissolved|melted|blurred)\b",
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
            # Single-sentence paragraph: check if the whole paragraph is a summary
            is_single_summary = False
            for compiled in compiled_starters:
                if compiled.match(para.strip()):
                    is_single_summary = True
                    break
            if is_single_summary:
                # Don't append — remove the entire summary paragraph
                continue
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
            # ANCHOR CHECK: if the sentence has concrete sensory/action anchors,
            # it's likely legitimate interiority, not empty AI summary. Keep it.
            _COMMON_CAPS = {
                "the", "this", "that", "these", "those", "there", "they",
                "something", "sometimes", "someone", "somehow", "somewhere",
                "whatever", "whenever", "wherever", "whoever", "however",
                "maybe", "perhaps", "tonight", "today", "tomorrow", "yesterday",
                "and", "but", "yet", "for", "our", "its", "with", "each",
            }
            def _has_proper_noun(sent):
                """Check for proper nouns (capitalized words that aren't common sentence starters)."""
                for m in re.finditer(r'\b([A-Z][a-z]{2,})(?:\'s)?\b', sent):
                    if m.group(1).lower() not in _COMMON_CAPS:
                        return True
                return False

            anchor_patterns = [
                r'\b(?:smell|taste|sound|cold|warm|wet|rough|smooth|sharp|bitter|sweet)\b',
                r'\b(?:door|window|glass|table|phone|car|street|rain|snow|wind|light)\b',
                r'\b(?:grabbed|pulled|pushed|slammed|kissed|threw|ran|jumped|fell)\b',
            ]
            has_anchor = any(re.search(ap, last_sentence) for ap in anchor_patterns)
            has_anchor = has_anchor or _has_proper_noun(last_sentence)
            if has_anchor:
                # Sentence has concrete detail — keep it (not pure AI filler)
                cleaned_paragraphs.append(para)
                continue

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
        # Physical tics
        (r'tamed?\s+(?:her |my |his )?(?:curly )?hair\s*(?:compulsively)?', 'hair taming'),
        (r'(?:fingers?\s+)?tightened\s+around', 'finger tightening'),
        (r'jaw\s+clenched', 'jaw clenching'),
        (r'tugg(?:ed|ing)\s+(?:at\s+)?(?:her |my |his )?(?:curly )?hair', 'hair tugging'),
        (r'ran\s+(?:her |my |his )?(?:fingers?\s+)?through\s+(?:her |my |his )?hair', 'hair running'),
        (r'heart\s+(?:hammered|pounded|raced|thundered|fluttered|skipped)', 'heart racing'),
        (r'stomach\s+(?:flipped|dropped|churned|knotted)', 'stomach flipping'),
        (r'breath\s+(?:caught|hitched|stuttered)', 'breath catching'),
        (r'pulse\s+(?:quickened|raced|spiked|jumped)', 'pulse racing'),
        (r'like\s+a\s+knife', 'simile: like a knife'),
        (r'vamos\s+a\s+ser\s+realistas', 'catchphrase: vamos'),
        # NEW from Seat 27B audit
        (r'(?:my |the )?phone\s+(?:buzzed|vibrated|pinged|chimed|rang)', 'phone buzzed'),
        (r'eyes?\s+(?:sparkl|twinkl)(?:ed|ing)', 'eyes sparkling'),
        (r'(?:a )?comfortable\s+silence', 'comfortable silence'),
        (r'(?:step(?:ping|ped)?\s+(?:out\s+of|outside)\s+(?:my|the|his|her)\s+)?comfort\s+zone', 'comfort zone'),
        (r'warmth\s+(?:spread|flooded|bloomed|filled|coursed)\s+(?:through|in)', 'warmth spread'),
        (r'(?:cool|warm|gentle|soft)\s+breeze', 'breeze descriptor'),
        (r'(?:fingers?\s+)?(?:drumm|tapp|hover)(?:ed|ing)', 'finger drumming'),
        (r'(?:a )?mix of\s+(?:\w+\s+)?(?:and|yet)', 'a mix of emotions'),
        (r'weight\s+of\s+(?:the|this|that|his|her|their|uncertainty|decision)', 'weight of abstraction'),
        (r'(?:the )?city\s+(?:hummed|buzzed|pulsed|thrummed)', 'city hummed'),
        (r'(?:uncharted|unfamiliar|unknown)\s+territory', 'uncharted territory'),
        (r"nodded,?\s+even though\s+(?:she|he)\s+couldn't\s+see", 'nodded unseen'),
        (r"let's\s+see\s+where\s+(?:this|it)\s+(?:goes|takes|leads)", 'see where this goes'),
        (r'tucked?\s+(?:a\s+)?strand\s+(?:of\s+)?(?:\w+\s+)?hair\s+behind', 'hair tucking'),
        (r'(?:my|her|his)\s+(?:notebook|journal)\s+(?:out|from|under|on|beside)', 'notebook prop'),
        (r'each\s+(?:step|word|moment|breath)\s+(?:felt|was|seemed)\s+like', 'each X felt like'),
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
    together. Split on stitch markers first (keep segment 0), then run
    similarity-based duplicate detection.
    """
    if not text or len(text) < 200:
        return text

    # Stitch markers: split FIRST, keep segment 0, drop the rest
    stitch_markers = [
        r"(?i)(?:the\s+)?rest\s+(?:of\s+the\s+(?:scene|chapter)\s+)?(?:remains?|is)\s+unchanged",
        r"\n---+\n",
        r"\n\*\*\*+\n",
        r"\n#{1,3}\s*(?:revised\s+)?version",
        r"\nVersion\s+\d",
        r"\nAlternative:",
        r"\nRevised:",
        r"\nTake\s+\d",
    ]

    for marker in stitch_markers:
        parts = re.split(marker, text, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2 and len(parts[0].strip()) > 50:
            text = parts[0].strip()
            break

    # Similarity-based duplicate detection
    stitch_markers_similarity = [
        r"\n---+\n",
        r"\n\*\*\*+\n",
        r"\n#{1,3}\s",
        r"\nVersion\s+\d",
        r"\nAlternative:",
        r"\nRevised:",
        r"\nTake\s+\d",
    ]

    for marker in stitch_markers_similarity:
        parts = re.split(marker, text, maxsplit=1)
        if len(parts) == 2 and len(parts[0].strip()) > 100 and len(parts[1].strip()) > 100:
            words_a = set(parts[0].lower().split())
            words_b = set(parts[1].lower().split())
            if words_a and words_b:
                overlap = len(words_a & words_b) / min(len(words_a), len(words_b))
                if overlap > similarity_threshold:
                    text = parts[0].strip()

    # Suffix/prefix overlap check: catch when the model repeats the last N words
    # at the start of a "continuation" (common restart pattern)
    words = text.split()
    if len(words) > 100:
        for overlap_size in [60, 40, 25]:
            if len(words) < overlap_size * 2.5:
                continue
            suffix = " ".join(words[-overlap_size:]).lower()
            # Search for this suffix appearing earlier in the text
            full_lower = text.lower()
            first_pos = full_lower.find(suffix)
            last_pos = full_lower.rfind(suffix)
            if first_pos != last_pos and first_pos >= 0:
                # The suffix appears twice — keep everything up to the restart
                # (the second occurrence starts the duplicate)
                text = text[:last_pos].rstrip()
                logger.info(f"Dedup: suffix/prefix overlap ({overlap_size} words) removed restart at pos {last_pos}")
                break

    # Paragraph-level duplication within the text
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


_cached_st_model = None  # Module-level cache for SentenceTransformer (lazy-loaded)


def _get_st_model():
    """Get or lazily load the SentenceTransformer model (cached across calls)."""
    global _cached_st_model
    if _cached_st_model is None:
        from sentence_transformers import SentenceTransformer
        _cached_st_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Loaded SentenceTransformer model (cached for session)")
    return _cached_st_model


def _semantic_similarity_check(text_a: str, text_b: str) -> float:
    """Compute semantic similarity between two text segments using word overlap + TF-IDF weighting.

    Falls back to enhanced word overlap when sentence-transformers is unavailable.
    Returns 0.0-1.0 similarity score.
    """
    # Try sentence-transformers first (if available and texts are large enough)
    if len(text_a) > 200 and len(text_b) > 200:
        try:
            from sentence_transformers import util
            model = _get_st_model()
            embeddings = model.encode([text_a[:1000], text_b[:1000]], convert_to_tensor=True)
            sim = float(util.cos_sim(embeddings[0], embeddings[1])[0][0])
            return sim
        except (ImportError, Exception):
            pass

    # Fallback: enhanced word overlap with IDF-like weighting
    import math
    words_a = text_a.lower().split()
    words_b = text_b.lower().split()
    if not words_a or not words_b:
        return 0.0

    # Use unique bigrams for better semantic signal than unigrams
    bigrams_a = set(zip(words_a, words_a[1:])) if len(words_a) > 1 else set(words_a)
    bigrams_b = set(zip(words_b, words_b[1:])) if len(words_b) > 1 else set(words_b)

    if not bigrams_a or not bigrams_b:
        return 0.0

    overlap = len(bigrams_a & bigrams_b)
    return overlap / min(len(bigrams_a), len(bigrams_b))


def _normalize_paragraph_for_dedup(text: str) -> str:
    """Normalize a paragraph for exact/near-exact duplicate detection.

    Lowercase, collapse whitespace, strip punctuation. Two paragraphs that
    differ only in capitalization, trailing spaces, or punctuation style
    will produce the same normalized form.
    """
    t = text.lower().strip()
    t = re.sub(r'[^\w\s]', '', t)       # Strip punctuation
    t = re.sub(r'\s+', ' ', t).strip()  # Collapse whitespace
    return t


def _detect_semantic_duplicates(text: str, threshold: float = 0.90) -> str:
    """Within-scene duplicate detection using normalized paragraph hashing.

    Catches genuine copy-paste restarts and paraphrased re-runs without
    false-positiving on normal thematic overlap within a scene.

    Two detection modes:
    1. Exact/near-exact: normalized paragraph hash comparison (fast, no embeddings)
    2. High-threshold word overlap (0.90+): catches slightly reworded restarts

    Previous approach used semantic embeddings at 0.75 threshold, which
    false-positived on paragraphs sharing characters/setting vocabulary.
    """
    if not text or len(text) < 500:
        return text

    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip() and len(p.strip()) > 100]
    if len(paragraphs) < 6:
        # Need at least 6 paragraphs for a meaningful restart detection
        # (3 original + 3 restarted). Short scenes don't restart.
        return text

    # --- Pass 1: Exact/near-exact paragraph hash matching ---
    # A restart typically reproduces 2+ consecutive paragraphs from earlier.
    # Look for consecutive duplicate runs.
    normalized = [_normalize_paragraph_for_dedup(p) for p in paragraphs]
    hashes = [hash(n) for n in normalized]

    # Find the first paragraph that starts a run of 2+ consecutive duplicates
    # matching an earlier position in the text.
    truncate_at = None
    for j in range(3, len(hashes)):  # Start checking from paragraph 4+
        # Check if paragraphs j and j+1 match any earlier consecutive pair
        if j + 1 >= len(hashes):
            break
        for k in range(j - 1):
            if k + 1 >= j:
                break
            if hashes[j] == hashes[k] and hashes[j + 1] == hashes[k + 1]:
                truncate_at = j
                logger.info(
                    f"Exact dedup: paragraphs {j}-{j+1} are exact duplicates of "
                    f"paragraphs {k}-{k+1}. Truncating at paragraph {j}."
                )
                break
        if truncate_at is not None:
            break

    # --- Pass 2: High-threshold word overlap for slightly reworded restarts ---
    # Only if Pass 1 found nothing. Uses sliding windows of 3 paragraphs.
    if truncate_at is None:
        WINDOW_SIZE = min(3, len(paragraphs) // 2)
        if WINDOW_SIZE >= 2:
            windows = []
            for i in range(0, len(paragraphs) - WINDOW_SIZE + 1, WINDOW_SIZE):
                window_text = '\n\n'.join(paragraphs[i:i + WINDOW_SIZE])
                window_words = set(window_text.lower().split())
                windows.append((i, window_words, len(window_text)))

            for j in range(1, len(windows)):
                j_start, j_words, j_len = windows[j]
                # Don't start checking until at least paragraph 6
                if j_start < 6:
                    continue
                for k in range(j):
                    k_start, k_words, k_len = windows[k]
                    # Only compare similar-length windows
                    len_ratio = j_len / k_len if k_len else 0
                    if 0.5 < len_ratio < 2.0 and k_words and j_words:
                        overlap = len(j_words & k_words) / min(len(j_words), len(k_words))
                        if overlap > threshold:
                            truncate_at = j_start
                            logger.info(
                                f"Near-exact dedup: window at para {j_start} has "
                                f"{overlap:.0%} word overlap with window at para {k_start}. "
                                f"Truncating at paragraph {truncate_at}."
                            )
                            break
                if truncate_at is not None:
                    break

    if truncate_at is not None and truncate_at > 0:
        kept = paragraphs[:truncate_at]
        logger.info(
            f"Dedup: kept {len(kept)}/{len(paragraphs)} paragraphs. "
            f"Duplicate tail ({len(paragraphs) - truncate_at} paras) removed. "
            f"Scene flagged for tail regeneration."
        )
        return '\n\n'.join(kept) + "\n\n[DEDUP_TAIL_TRUNCATED]"

    return text


def _flag_language_inconsistencies(text: str, setting_language: str = "",
                                   foreign_whitelist: list = None) -> str:
    """Flag or fix foreign language inconsistencies in the text.

    Detects when a model uses the wrong foreign language (e.g., Spanish
    phrases in an Italian setting, or vice versa). This is a common LLM
    hallucination where the model confuses romance languages.

    If setting_language is specified (e.g., "Italian"), replaces common
    wrong-language phrases with the correct language equivalent.

    Guards:
    - foreign_whitelist: list of words/phrases to never touch (food terms, endearments, etc.)
    - Quoted text is already masked upstream via _mask_quoted_dialogue
    - Single foreign words (< 3 consecutive) are only replaced if they match
      multi-word patterns (3+ words) — lone words are presumed intentional
    """
    if not text or not setting_language:
        return text

    setting_lang = setting_language.lower().strip()
    whitelist = set((w.lower().strip() for w in (foreign_whitelist or [])))

    # Common phrase mappings between confused romance languages
    # Only fix OBVIOUS high-frequency phrases that are clearly wrong-language
    if setting_lang == "italian":
        # Spanish -> Italian replacements
        spanish_to_italian = {
            r'\bVamos a ser realistas\b': 'Siamo realisti',
            r'\bBuenas noches\b': 'Buona notte',
            r'\bbuenas noches\b': 'buona notte',
            r'\bBuenos días\b': 'Buongiorno',
            r'\bMi amor\b': 'Amore mio',
            r'\bmi amor\b': 'amore mio',
            r'\bPor favor\b': 'Per favore',
            r'\bpor favor\b': 'per favore',
            r'\bFiglio mio\b': 'Figlio mio',
            r'\bVamos\b': 'Andiamo',
            r'\bvamos\b': 'andiamo',
            r'\bGracias\b': 'Grazie',
            r'\bgracias\b': 'grazie',
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
            r'\bseñora\b': 'señora',
        }
        replacements = spanish_to_italian

    elif setting_lang == "spanish":
        # Italian -> Spanish replacements
        italian_to_spanish = {
            r'\bAmore mio\b': 'Mi amor',
            r'\bamore mio\b': 'mi amor',
            r'\bPer favore\b': 'Por favor',
            r'\bper favore\b': 'por favor',
            r'\bAndiamo\b': 'Vamos',
            r'\bandiamo\b': 'vamos',
            r'\bGrazie\b': 'Gracias',
            r'\bgrazie\b': 'gracias',
            r'\bBella\b': 'Hermosa',
            r'\bbella\b': 'hermosa',
            r'\bSignore\b': 'Señor',
            r'\bsignore\b': 'señor',
            r'\bSignora\b': 'Señora',
            r'\bsignora\b': 'señora',
        }
        replacements = italian_to_spanish
    else:
        return text

    for pattern, replacement in replacements.items():
        # Extract the plain text from the regex pattern (strip \b markers)
        plain = re.sub(r'\\b', '', pattern).strip()

        # Whitelist guard: skip if this word/phrase is whitelisted
        if plain.lower() in whitelist:
            continue

        # Sentence-length guard: single words (1-2 tokens) require the match
        # to be in a context of 3+ consecutive non-English words OR be a
        # multi-word pattern. Multi-word patterns (3+ words) always apply.
        word_count = len(plain.split())
        if word_count < 3:
            # For short patterns, only apply if in a cluster of foreign words
            # (relaxed: multi-word patterns like "Mi amor" are 2 words — always fix)
            if word_count < 2:
                # Single-word: check if it appears in a run of 3+ foreign-looking words
                # by verifying the surrounding context has other non-English words
                def _guarded_replace(match):
                    start = max(0, match.start() - 40)
                    end = min(len(text), match.end() + 40)
                    context = text[start:end]
                    # Count words that look foreign (contain accented chars or are
                    # in the replacement table)
                    foreign_words = sum(
                        1 for w in context.split()
                        if any(ord(c) > 127 for c in w)
                    )
                    if foreign_words >= 2:
                        return replacement
                    return match.group(0)  # Leave single foreign word alone
                text = re.sub(pattern, _guarded_replace, text)
                continue

        text = re.sub(pattern, replacement, text)

    return text


def _postprocess_scene(text: str, protagonist_name: str = "",
                       setting_language: str = "",
                       protagonist_gender: str = "",
                       foreign_whitelist: list = None) -> str:
    """Master post-processor: applies all code-level quality enforcement.

    Called after _clean_scene_content on every creative stage output.
    Order matters: strip sentinel → clean meta-text → enforce quality.
    """
    # Strip sentinel token if present (matches both static <END_PROSE> and
    # per-run nonce variants like <END_PROSE_a3f1b2c9>)
    text = re.sub(r'\s*<END_PROSE(?:_[a-f0-9]+)?>\s*$', '', text or '', flags=re.IGNORECASE).strip()
    text = _clean_scene_content(text)
    text = _detect_duplicate_content(text)
    text = _detect_semantic_duplicates(text)
    text = _enforce_first_person_pov(text, protagonist_name, protagonist_gender)
    # ORDERING INVARIANT: F3b (repair) MUST run after F3 (enforce).
    # F3 may create patterns like "She whispered, my voice" that F3b fixes.
    # If this order is ever changed, POV corruption will be reintroduced silently.
    text = _repair_pov_context_errors(text, protagonist_gender)
    text = _strip_emotional_summaries(text)
    text = _limit_tic_frequency(text)
    if setting_language:
        text = _flag_language_inconsistencies(text, setting_language, foreign_whitelist)
    # Final sanity: detect catastrophic pronoun corruption after all transforms
    drift = _detect_pov_drift(text, protagonist_name, protagonist_gender)
    if drift:
        logger.warning(f"POV drift detected after postprocess: {drift}")
    return text


def _detect_pov_drift(text: str, pov_name: str, pov_gender: str) -> str:
    """Detect catastrophic POV pronoun corruption after postprocessing.

    Checks for patterns that indicate the wrong pronoun conversion was applied:
    - First-person "I" mixed with same-gender third-person as self-reference
    - Corruption sentinels: "I said," she/he (first-person + wrong speaker tag)

    Returns a warning string if drift detected, empty string if clean.
    """
    if not text or not pov_gender:
        return ""

    # Strip dialogue to only check narrative voice
    narrative = re.sub(r'"[^"]*"', '', text)
    narrative = re.sub(r'[\u201c][^\u201d]*[\u201d]', '', narrative)

    i_count = len(re.findall(r'\bI\b', narrative))
    if i_count < 3:
        return ""  # Not enough first-person to judge

    # Count third-person pronouns that match the POV character's gender
    # These are suspicious — they might be the narrator referring to themselves
    if pov_gender == "male":
        # Male POV: "He walked" should have been converted to "I walked"
        same_gender_3p = len(re.findall(r'\bHe\s+(?:walked|thought|felt|looked|turned|knew|noticed|realized)\b', narrative))
    elif pov_gender == "female":
        same_gender_3p = len(re.findall(r'\bShe\s+(?:walked|thought|felt|looked|turned|knew|noticed|realized)\b', narrative))
    else:
        return ""

    # Corruption sentinel: "I said/whispered," + wrong speaker tag
    # e.g., male POV: "I said," he whispered — means "he" is referring to
    # the narrator, which shouldn't happen in first person
    if pov_gender == "male":
        corruption_patterns = len(re.findall(
            r'\bI\s+(?:said|whispered|murmured|asked)\b[^.]*\bhe\b',
            narrative, re.IGNORECASE
        ))
    else:
        corruption_patterns = len(re.findall(
            r'\bI\s+(?:said|whispered|murmured|asked)\b[^.]*\bshe\b',
            narrative, re.IGNORECASE
        ))

    issues = []
    # If same-gender 3rd person > I-verb count, something went wrong
    if same_gender_3p > i_count * 0.3 and same_gender_3p >= 3:
        issues.append(
            f"high same-gender 3rd person ({same_gender_3p} vs {i_count} I-refs)"
        )
    if corruption_patterns >= 2:
        issues.append(f"corruption sentinels ({corruption_patterns} 'I said...he/she' patterns)")

    return "; ".join(issues)


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


def _is_raw_failure(obj: Any) -> bool:
    """True if parse 'result' is a failure wrapper, not valid data."""
    if obj is None:
        return True
    if isinstance(obj, dict) and "raw" in obj:
        return True
    if isinstance(obj, list) and len(obj) == 1 and isinstance(obj[0], dict) and "raw" in obj[0]:
        return True
    return False


def _is_valid_outline_batch(batch: Any) -> bool:
    """True if batch has valid outline shape: list of chapters with scenes. Rejects raw wrappers."""
    if _is_raw_failure(batch):
        return False
    if not isinstance(batch, list) or len(batch) == 0:
        return False
    # Flat scenes: all items look like scene dicts (scene_name, scene/chapter)
    def is_flat_scene(x):
        return isinstance(x, dict) and ("scene" in x or "scene_number" in x or "scene_name" in x)
    if all(is_flat_scene(x) for x in batch):
        return True
    # Chapters-array: each has scenes list (chapter can be filled in later)
    for ch in batch:
        if not isinstance(ch, dict) or "raw" in ch:
            return False
        scenes = ch.get("scenes")
        if not isinstance(scenes, list):
            return False
    return True


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


# ============================================================================
# FORMAT CONTRACT — System prompt for all prose-generating stages
# Prevents meta-text at generation time (not just cleanup)
# ============================================================================
FORMAT_CONTRACT = """You are a fiction author writing a novel. Your output is PROSE ONLY.

ABSOLUTE RULES:
- Output ONLY narrative prose (dialogue, action, description, interiority)
- NEVER output: "Certainly", "Here is", "Sure", "As requested", greetings, sign-offs
- NEVER output: headings, bullet points, numbered lists, markdown formatting
- NEVER output: commentary, analysis, "Changes made:", "Notes:", summaries
- NEVER output: alternatives ("Option A / Option B"), bracketed stage directions
- NEVER output: "The rest remains unchanged" or any truncation marker
- NEVER output: "[Scene continues...]" or "[Rest of scene unchanged]"
- If unsure whether to explain or continue the scene: CONTINUE THE SCENE

BAD (do not do this):
  "Here's the revised scene with more sensory detail:

  The morning light filtered..."

GOOD (do this):
  The morning light filtered through salt-crusted windows...

End your output with <END_PROSE> on its own line when finished."""

# Sentinel token: primary stop mechanism. The model is instructed to emit this,
# and we also set it as a stop sequence so generation halts cleanly.
PROSE_SENTINEL = "\n<END_PROSE>"

# Backup stop sequences — catch assistant-style meta-text that bypasses the sentinel.
# These are deliberately "assistant-y" (unlikely to appear in prose/dialogue) to
# minimize false positives. Generic tokens like "\nNotes:" removed to avoid
# clipping legitimate prose (e.g. a character's notebook).
CREATIVE_STOP_SEQUENCES = [
    PROSE_SENTINEL,
    "\nCertainly! Here",
    "\nHere is the",
    "\nAs requested,",
    "\nThe rest remains unchanged",
    "\nChanges made:",
    "\nScanning for AI",
    "\n**Changes made",
    "\n**Scanning for",
    "\n[The rest",
    "\n[Scene continues",
]

# Retry prefix for critic gate failures
STRICT_RETRY_PREFIX = (
    "CRITICAL: Your previous output contained non-prose content. "
    "Output ABSOLUTELY NOTHING except narrative prose. "
    "No preamble. No commentary. No explanation. No headers. "
    "Start with the first word of the prose. End with the last word.\n\n"
)

# Issue-specific retry feedback: tell the model WHAT went wrong so the retry is targeted
ISSUE_SPECIFIC_FEEDBACK = {
    "preamble": (
        "YOUR ERROR: You started your output with a preamble like 'Sure, here is...' or 'Certainly!'. "
        "This is NOT prose. Start DIRECTLY with the first word of the narrative scene. "
        "No greeting. No acknowledgment. No introduction."
    ),
    "truncation_marker": (
        "YOUR ERROR: You truncated the scene with 'the rest remains unchanged' or similar. "
        "You MUST output the COMPLETE scene from beginning to end. Do not abbreviate, "
        "skip, or summarize any part. Write every word."
    ),
    "alternate_version": (
        "YOUR ERROR: You output multiple versions (Option A/B, Version 1/2, alternatives). "
        "Output exactly ONE version of the scene. No alternatives. No options. One continuous narrative."
    ),
    "analysis_commentary": (
        "YOUR ERROR: You appended analysis, notes, or commentary after the prose "
        "('Changes made:', 'Notes:', 'Scanning for...'). Output ONLY the scene text. "
        "Nothing after the last word of prose."
    ),
    "prompt_leak": (
        "YOUR ERROR: You echoed parts of your system instructions into the output "
        "(e.g. 'ABSOLUTE RULES', 'Output ONLY narrative prose', '<END_PROSE>'). "
        "Your system prompt is NEVER part of the story. Output ONLY narrative prose "
        "with no meta-text, no instructions, no rules."
    ),
}

# Stages that generate prose (not JSON/analysis) — get format contract + stop sequences
PROSE_STAGES = {
    "scene_drafting", "scene_expansion", "structure_gate", "self_refinement",
    "continuity_fix", "continuity_recheck", "voice_human_pass", "continuity_fix_2",
    "dialogue_polish", "prose_polish", "chapter_hooks", "final_deai"
}

# Stages where full critic gate runs (retry on failure)
# Excludes final_deai (special word-window logic)
CRITIC_GATE_STAGES = {
    "scene_drafting", "scene_expansion", "structure_gate", "self_refinement",
    "continuity_fix", "continuity_recheck", "voice_human_pass", "continuity_fix_2",
    "dialogue_polish", "prose_polish", "chapter_hooks"
}


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
    high_concept_candidates: Optional[List[str]] = None  # Best-of-N candidates
    high_concept_fingerprint: Optional[Dict[str, Any]] = None  # Hash + keywords + entities
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

    # Artifact tracking — per-scene metrics for model vs system diagnostics
    artifact_metrics: Dict[str, Any] = field(default_factory=lambda: {
        "total_scenes_generated": 0,
        "scenes_with_meta_text": 0,
        "scenes_with_preamble": 0,
        "scenes_with_duplicate_marker": 0,
        "scenes_with_pov_drift": 0,
        "scenes_retried": 0,
        "per_stage": {},
    })

    # Checkpoint tracking - which stages completed successfully
    completed_stages: List[str] = field(default_factory=list)

    # Outline JSON parse/repair telemetry (T1) - written to run_report
    outline_json_report: Optional[Dict[str, Any]] = None

    def calculate_targets(self):
        """Calculate word count targets based on target_length and genre."""
        length_map = {
            "micro (5k)": 5000,
            "novelette (15k)": 15000,
            "novella (30k)": 30000,
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
        """Save state to disk with checkpoint data for reliable resume.

        Uses atomic write (temp file + os.replace) to prevent corruption
        from mid-write crashes. A crash during json.dump() only corrupts
        the .tmp file; the previous checkpoint survives intact.
        """
        state_file = self.project_path / "pipeline_state.json"
        tmp_file = self.project_path / "pipeline_state.json.tmp"
        state_dict = {
            "project_name": self.project_name,
            "current_stage": self.current_stage,
            "completed_stages": self.completed_stages,
            "high_concept": self.high_concept,
            "high_concept_candidates": self.high_concept_candidates,
            "high_concept_fingerprint": self.high_concept_fingerprint,
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
            "artifact_metrics": self.artifact_metrics,
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
        # Atomic write: dump to temp file, then replace original.
        # If json.dump fails (e.g. disk full), clean up the partial tmp file.
        try:
            with open(tmp_file, "w") as f:
                json.dump(state_dict, f, indent=2)
            os.replace(str(tmp_file), str(state_file))
        except Exception:
            try:
                tmp_file.unlink(missing_ok=True)
            except OSError:
                pass
            raise
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
            high_concept_candidates=data.get("high_concept_candidates"),
            high_concept_fingerprint=data.get("high_concept_fingerprint"),
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
            total_cost_usd=data.get("total_cost_usd", 0.0),
            artifact_metrics=data.get("artifact_metrics", {
                "total_scenes_generated": 0,
                "scenes_with_meta_text": 0,
                "scenes_with_preamble": 0,
                "scenes_with_duplicate_marker": 0,
                "scenes_with_pov_drift": 0,
                "scenes_retried": 0,
                "per_stage": {},
            })
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
        "structure_gate",       # Gate A: structure/tension scorecard before continuity
        "continuity_audit",
        "continuity_fix",
        "continuity_recheck",   # Tight loop: re-audit only fixed scenes, max 2 iterations
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
        "structure_gate": "gemini",          # Structure scoring (JSON analysis)
        "continuity_audit": "gemini",
        "continuity_fix": "claude",
        "continuity_recheck": "gemini",      # Re-audit fixed scenes (analysis)
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
        "high_concept": 0.65,
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
        "structure_gate": 0.15,              # Low temp for objective scoring
        "continuity_recheck": 0.2,           # Low temp for factual re-audit
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
        """Get appropriate temperature for a stage.

        Config overrides (stage_temperatures or model_tuning.stage_temperatures) take
        precedence over built-in defaults. Use for paid-model calibration.
        """
        if self.state and self.state.config:
            tuning = self.state.config.get("model_tuning", {}) or {}
            temps = tuning.get("stage_temperatures") or self.state.config.get("stage_temperatures") or {}
            if isinstance(temps, dict) and stage_name in temps:
                return float(temps[stage_name])
        return self.STAGE_TEMPERATURES.get(stage_name, 0.7)

    def get_max_tokens_for_stage(self, stage_name: str, computed_default: int) -> int:
        """Get max_tokens for a stage. Config override takes precedence.

        Use for paid-model calibration: paid models often need higher runway for
        scene_drafting, lower for outline/planning.
        """
        if self.state and self.state.config:
            tuning = self.state.config.get("model_tuning", {}) or {}
            caps = tuning.get("stage_max_tokens") or self.state.config.get("stage_max_tokens") or {}
            if isinstance(caps, dict) and stage_name in caps:
                return int(caps[stage_name])
        return computed_default

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

        # Per-run nonce sentinel: prevents cross-run prose collision and
        # makes the stop token unpredictable (can't appear in training data).
        self._run_nonce = secrets.token_hex(4)  # 8 hex chars, e.g. "a3f1b2c9"
        nonce_sentinel = f"<END_PROSE_{self._run_nonce}>"
        self._prose_sentinel = f"\n{nonce_sentinel}"
        self._format_contract = FORMAT_CONTRACT.replace(
            "<END_PROSE>", nonce_sentinel
        )
        self._stop_sequences = [
            self._prose_sentinel,
        ] + CREATIVE_STOP_SEQUENCES[1:]  # Keep backup sequences, replace primary

        # Defense mode: observe (log only), protect (default), aggressive (stricter)
        self._defense_mode = "protect"

        # Budget tracker: tracks defense-related resource usage per run
        self._budget_tracker = {
            "retries_per_stage": {},   # stage_name -> retry count
            "rewritten_scenes": 0,     # total scenes rewritten in feedback loops
            "defense_tokens": 0,       # tokens spent on retries + feedback rewrites
            "generation_tokens": 0,    # tokens spent on primary generation
        }

    # Default defense thresholds — overridable via config.yaml defense.thresholds
    _DEFAULT_DEFENSE_THRESHOLDS = {
        "scene_count_drop_pct": 0.50,         # H check 1: scene count < X of original
        "prefix_corruption_pct": 0.30,        # H check 2: >X of scenes share first 100 chars
        "avg_word_plummet_pct": 0.40,         # H check 4: avg wc dropped > X
        "forbidden_marker_pct": 0.40,         # H check 5: >X of scenes contain meta-markers
        "fingerprint_collapse_pct": 0.50,     # H check 6: unique fingerprints < X of original
        "deai_word_delta_pct": 0.15,          # Layer I: scene wc delta > X -> restore
        "deai_paragraph_loss_pct": 0.50,      # Layer I: paragraph wc loss > X -> reject rewrite
        "salvage_min_words": 150,             # F1 2.5: salvage warning threshold
        "salvage_min_paragraphs": 2,          # F1 2.5: salvage warning threshold
        "salvage_restore_ratio": 3.0,         # F1 2.5: original/stripped ratio for restore
        "freshness_bigram_pct": 0.40,         # quality_audit: bigram overlap > X = stale
        "feedback_loop_max_scenes": 5,        # G: max scenes per feedback loop
        "feedback_loop_wc_retention": 0.80,   # G: min word count retention for LLM rewrite (surgical removal = high retention)
        "circuit_breaker_threshold": 3,       # consecutive stage failures before halt
        "semantic_dedup_threshold": 0.75,     # F2b: cosine/Jaccard > X = duplicate (0.50 was too aggressive)
        "duplicate_ngram_threshold": 0.60,    # F2: paragraph ngram overlap > X = duplicate
        "budget_max_retries_per_stage": 3,    # max retries per stage per run
        "budget_max_rewritten_scenes": 15,    # max total scenes rewritten (all feedback loops)
        "budget_max_defense_ratio": 0.30,     # max fraction of total tokens on defense
        "entity_guard_short_scene_words": 200,  # scenes below this word count use relaxed noun threshold
        "entity_guard_short_scene_nouns": 1,    # min shared nouns required for short scenes
        "structure_gate_max_iterations": 3,     # max score→repair→rescore cycles (was hardcoded 2)
        "structure_gate_pass_total": 16,        # total score (out of 25) to pass
        "structure_gate_pass_min": 3,           # minimum per-category score to pass
        "structure_gate_diminishing_threshold": 1,  # stop if improvement < this many points
    }

    # Defense modes: observe (log only), protect (default — log + intervene), aggressive (stricter thresholds)
    DEFENSE_MODES = {"observe", "protect", "aggressive"}

    # Bounds for threshold validation: key -> (min, max)
    # Prevents user misconfiguration (e.g. setting pct thresholds > 1.0 or negative)
    _THRESHOLD_BOUNDS = {
        "scene_count_drop_pct": (0.10, 0.95),
        "prefix_corruption_pct": (0.05, 0.80),
        "avg_word_plummet_pct": (0.10, 0.90),
        "forbidden_marker_pct": (0.05, 0.90),
        "fingerprint_collapse_pct": (0.10, 0.95),
        "deai_word_delta_pct": (0.05, 0.50),
        "deai_paragraph_loss_pct": (0.10, 0.90),
        "salvage_min_words": (10, 1000),
        "salvage_min_paragraphs": (1, 20),
        "salvage_restore_ratio": (1.5, 10.0),
        "freshness_bigram_pct": (0.10, 0.90),
        "feedback_loop_max_scenes": (1, 50),
        "feedback_loop_wc_retention": (0.30, 1.0),
        "circuit_breaker_threshold": (1, 20),
        "semantic_dedup_threshold": (0.20, 0.95),
        "duplicate_ngram_threshold": (0.20, 0.95),
        "budget_max_retries_per_stage": (0, 20),
        "budget_max_rewritten_scenes": (0, 100),
        "budget_max_defense_ratio": (0.05, 0.90),
        "entity_guard_short_scene_words": (50, 500),
        "entity_guard_short_scene_nouns": (0, 5),
        "structure_gate_max_iterations": (1, 5),
        "structure_gate_pass_total": (10, 25),
        "structure_gate_pass_min": (1, 5),
        "structure_gate_diminishing_threshold": (0, 5),
    }

    # Aggressive mode multipliers: tighten percentage thresholds by this factor
    # (multiply detection thresholds, meaning MORE sensitive)
    _AGGRESSIVE_MULTIPLIERS = {
        "scene_count_drop_pct": 0.7,      # trigger earlier
        "prefix_corruption_pct": 0.7,
        "avg_word_plummet_pct": 0.7,
        "forbidden_marker_pct": 0.7,
        "fingerprint_collapse_pct": 0.7,
        "deai_word_delta_pct": 0.7,
        "semantic_dedup_threshold": 0.85,  # stricter similarity detection
        "duplicate_ngram_threshold": 0.85,
        "feedback_loop_wc_retention": 1.1, # require MORE retention
        "budget_max_defense_ratio": 1.3,   # allow more defense spending
    }

    def _get_threshold(self, key: str) -> float:
        """Get defense threshold from config or default, with bounds validation."""
        if key not in self._DEFAULT_DEFENSE_THRESHOLDS:
            logger.warning(f"Unknown threshold key '{key}', returning 0.5")
            return 0.5
        value = self._DEFAULT_DEFENSE_THRESHOLDS[key]
        if self.state and self.state.config:
            user_thresholds = self.state.config.get("defense", {}).get("thresholds", {})
            if key in user_thresholds:
                value = float(user_thresholds[key])
        # Aggressive mode: tighten thresholds
        if self._defense_mode == "aggressive" and key in self._AGGRESSIVE_MULTIPLIERS:
            value *= self._AGGRESSIVE_MULTIPLIERS[key]
        # Clamp to valid bounds if defined
        if key in self._THRESHOLD_BOUNDS:
            lo, hi = self._THRESHOLD_BOUNDS[key]
            if value < lo or value > hi:
                clamped = max(lo, min(hi, value))
                logger.warning(
                    f"Threshold '{key}' value {value} out of bounds [{lo}, {hi}], "
                    f"clamped to {clamped}"
                )
                value = clamped
        return value

    def _write_run_status(self, last_stage: str, result=None):
        """Write run_status.json at phase boundaries for monitoring."""
        if not self.state or not self.state.project_path:
            return
        try:
            status = {
                "timestamp": datetime.now().isoformat(),
                "last_stage": last_stage,
                "last_status": result.status.value if result else "unknown",
                "completed_stages": list(self.state.completed_stages),
                "total_stages": len(self.state.completed_stages),
                "total_tokens": self.state.total_tokens,
                "total_cost_usd": round(self.state.total_cost_usd, 4),
                "scene_count": len(self.state.scenes) if self.state.scenes else 0,
                "incidents": len(_incident_buffer),
                "budget": {
                    "defense_tokens": self._budget_tracker.get("defense_tokens", 0),
                    "generation_tokens": self._budget_tracker.get("generation_tokens", 0),
                    "rewritten_scenes": self._budget_tracker.get("rewritten_scenes", 0),
                },
            }
            status_path = Path(self.state.project_path) / "run_status.json"
            with open(status_path, "w", encoding="utf-8") as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            logger.debug(f"Failed to write run_status.json: {e}")

    async def _canary_scene_check(self):
        """Pre-flight model check: send a tiny prose prompt and verify clean output.

        Catches obvious model misconfiguration (wrong API key, model down, model
        echoing system prompt) BEFORE burning tokens on real scenes.
        """
        defense_cfg = {}
        if self.state and self.state.config:
            defense_cfg = self.state.config.get("defense", {}) or {}
        if not defense_cfg.get("canary_enabled", True):
            return  # User opted out

        canary_prompt = (
            "Write exactly two sentences of fiction about a cat sitting on a windowsill "
            "watching rain. Output ONLY the two sentences, nothing else."
        )
        # Try each unique client
        clients_tested = set()
        for stage_name in ["scene_drafting", "self_refinement", "final_deai"]:
            try:
                client = self.get_client_for_stage(stage_name)
                client_id = id(client)
                if client_id in clients_tested:
                    continue
                clients_tested.add(client_id)

                response = await client.generate(
                    canary_prompt,
                    max_tokens=200,
                    system_prompt=self._format_contract,
                    stop=self._stop_sequences
                )
                text = (response.content or "").strip()

                # Check for obvious problems
                problems = []
                if not text or len(text) < 10:
                    problems.append("empty_response")
                if any(fp in text for fp in ["ABSOLUTE RULES", "NEVER output", "<END_PROSE>",
                                              "Output ONLY", "CONTINUE THE SCENE"]):
                    problems.append("prompt_leak")
                preamble_pats = [
                    r'^(?:Sure|Certainly|Of course)[,!.\s]',
                    r'^(?:Here\s+is|Below\s+is)',
                ]
                for pat in preamble_pats:
                    if re.search(pat, text[:100], re.IGNORECASE):
                        problems.append("preamble")
                        break

                if problems:
                    logger.warning(
                        f"CANARY CHECK: model for {stage_name} failed pre-flight "
                        f"({', '.join(problems)}). Output: {text[:100]}"
                    )
                    _log_incident(stage_name, "canary_failure",
                                  f"Pre-flight failed: {', '.join(problems)}",
                                  severity="warning", failure_type="content")
                else:
                    logger.info(f"Canary check passed for {stage_name} model")

            except Exception as e:
                logger.warning(f"CANARY CHECK: model for {stage_name} unavailable: {e}")
                _log_incident(stage_name, "canary_failure",
                              str(e)[:200], severity="warning")

    def get_client_for_stage(self, stage_name: str):
        """Get the appropriate LLM client for a given stage.

        Uses smart routing to pick the best model, with fallback to default.
        Config: model_overrides (stage -> gpt|claude|gemini) or stage_model_map
        (stage -> api_model|critic_model|fallback_model). Both supported for
        easy local/paid swap.
        """
        # Check for stage-specific override in config
        if self.state and self.state.config:
            cfg = self.state.config
            model_overrides = cfg.get("model_overrides", {})
            stage_model_map = cfg.get("stage_model_map", {})

            # model_overrides: stage -> gpt|claude|gemini (direct bucket)
            if stage_name in model_overrides:
                model_type = model_overrides[stage_name]
                if model_type in self.llm_clients:
                    logger.info(f"Using override model '{model_type}' for stage: {stage_name}")
                    return self.llm_clients[model_type]

            # stage_model_map: stage -> api_model|critic_model|fallback_model
            # Maps to gpt/claude/gemini (api->gpt, critic->claude, fallback->gemini)
            if stage_name in stage_model_map:
                key = stage_model_map[stage_name]
                bucket = {"api_model": "gpt", "critic_model": "claude", "fallback_model": "gemini"}.get(key, "gpt")
                if bucket in self.llm_clients:
                    logger.info(f"Using stage_model_map '{key}' ({bucket}) for stage: {stage_name}")
                    return self.llm_clients[bucket]

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

        # Write resolved config for reproducibility (env + project merged)
        try:
            from prometheus_novel.configs.config_resolver import resolve_and_write
            resolve_and_write(self.project_path, env=os.getenv("PROMETHEUS_ENV"))
        except Exception as e:
            logger.debug(f"Could not write resolved config: {e}")

        # Set defense mode from config
        defense_cfg = self.state.config.get("defense", {}) or {}
        mode = str(defense_cfg.get("mode", "protect")).lower()
        if mode in self.DEFENSE_MODES:
            self._defense_mode = mode
        else:
            logger.warning(f"Unknown defense mode '{mode}', using 'protect'")
            self._defense_mode = "protect"
        logger.info(f"Defense mode: {self._defense_mode}")

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

        # Reset budget tracker for this run
        self._budget_tracker = {
            "retries_per_stage": {},
            "rewritten_scenes": 0,
            "defense_tokens": 0,
            "generation_tokens": 0,
        }

        # Pre-flight canary scene check
        await self._canary_scene_check()

        # Circuit breaker: halt after N consecutive stage failures + snapshot restores
        CIRCUIT_BREAKER_THRESHOLD = int(self._get_threshold("circuit_breaker_threshold"))
        consecutive_failures = 0

        try:
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
                        consecutive_failures = 0  # Reset circuit breaker on success

                    self.state.save()
                    self._write_run_status(stage_name, result)

                    await self._emit("on_stage_complete", stage_name, result)

                    if result.status == StageStatus.FAILED:
                        consecutive_failures += 1
                        await self._emit("on_stage_error", stage_name, result.error)

                        # Circuit breaker: halt pipeline after N consecutive failures
                        if consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
                            failed_stages = [
                                r.stage_name for r in self.state.stage_results[-CIRCUIT_BREAKER_THRESHOLD:]
                                if r.status == StageStatus.FAILED
                            ]
                            logger.error(
                                f"CIRCUIT BREAKER: {consecutive_failures} consecutive stage failures "
                                f"({', '.join(failed_stages)}). Halting pipeline. "
                                f"Diagnostic: check model availability, config validity, and scene state."
                            )
                            _log_incident(
                                ",".join(failed_stages), "circuit_breaker_trip",
                                f"{consecutive_failures} consecutive failures",
                                severity="critical"
                            )
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

        finally:
            output_dir = self.state.project_path / "output" if getattr(self.state, "project_path", None) else None
            if output_dir and getattr(self.state, "outline_json_report", None):
                from prometheus_novel.configs.config_resolver import update_resolved_outline_meta
                update_resolved_outline_meta(output_dir, self.state.outline_json_report)

        await self._emit("on_pipeline_complete", self.state)
        return self.state

    async def _run_stage(self, stage_name: str) -> StageResult:
        """Run a single pipeline stage with transaction safety.

        For prose stages: snapshots self.state.scenes before running.
        If the stage fails or produces obviously corrupt output (scene count
        drops below 50% of input), restores the snapshot.
        """
        import time
        import copy
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
            "structure_gate": self._stage_structure_gate,
            "continuity_audit": self._stage_continuity_audit,
            "continuity_fix": self._stage_continuity_fix,
            "continuity_recheck": self._stage_continuity_recheck,
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

        # Transaction safety: snapshot scenes before prose stages
        scenes_snapshot = None
        if stage_name in PROSE_STAGES and self.state.scenes:
            scenes_snapshot = copy.deepcopy(self.state.scenes)

        try:
            output, tokens = await handler()
            duration = time.time() - start_time

            # Validate: stage didn't corrupt scenes
            # In observe mode: log incidents but don't restore snapshots
            _observe_only = self._defense_mode == "observe"
            if scenes_snapshot and self.state.scenes is not None:
                new_count = len(self.state.scenes)
                old_count = len(scenes_snapshot)

                # Check 1: Scene count didn't drop below threshold
                if new_count < old_count * self._get_threshold("scene_count_drop_pct"):
                    logger.error(
                        f"Transaction safety: {stage_name} produced {new_count} scenes "
                        f"from {old_count} input. Restoring snapshot."
                    )
                    _log_incident(stage_name, "scene_count_drop",
                                  f"Scene count {old_count}->{new_count}",
                                  scene_count_before=old_count, scene_count_after=new_count)
                    if not _observe_only:
                        self.state.scenes = scenes_snapshot
                        return StageResult(
                            stage_name=stage_name,
                            status=StageStatus.FAILED,
                            error=f"Scene count dropped from {old_count} to {new_count}",
                            duration_seconds=duration
                        )

                # Check 2: Content-hash corruption — if >30% of scenes share
                # identical first 100 chars, the stage likely wrote the same
                # preamble/garbage into every scene
                if new_count > 5:
                    prefixes = []
                    for s in self.state.scenes:
                        if isinstance(s, dict):
                            c = s.get("content", "")
                            prefixes.append(c[:100].lower().strip() if c else "")
                    from collections import Counter
                    prefix_counts = Counter(p for p in prefixes if p)
                    for prefix, count in prefix_counts.most_common(1):
                        if count > new_count * self._get_threshold("prefix_corruption_pct"):
                            logger.error(
                                f"Transaction safety: {stage_name} content-hash corruption — "
                                f"{count}/{new_count} scenes share identical first 100 chars. "
                                f"Restoring snapshot."
                            )
                            _log_incident(stage_name, "prefix_corruption",
                                          f"{count}/{new_count} scenes share identical prefix",
                                          scene_count_before=old_count, scene_count_after=new_count)
                            if not _observe_only:
                                self.state.scenes = scenes_snapshot
                                return StageResult(
                                    stage_name=stage_name,
                                    status=StageStatus.FAILED,
                                    error=f"Content corruption: {count}/{new_count} scenes identical prefix",
                                    duration_seconds=duration
                                )

                # Check 3: No scene that had content is now empty
                emptied = 0
                for i, (orig, new) in enumerate(zip(scenes_snapshot, self.state.scenes)):
                    if isinstance(orig, dict) and isinstance(new, dict):
                        orig_c = (orig.get("content") or "").strip()
                        new_c = (new.get("content") or "").strip()
                        if len(orig_c) > 50 and len(new_c) == 0:
                            emptied += 1
                if emptied > 0:
                    logger.error(
                        f"Transaction safety: {stage_name} emptied {emptied} scenes. "
                        f"Restoring snapshot."
                    )
                    _log_incident(stage_name, "scenes_emptied",
                                  f"{emptied} scenes emptied",
                                  scene_count_before=old_count, scene_count_after=new_count)
                    if not _observe_only:
                        self.state.scenes = scenes_snapshot
                        return StageResult(
                            stage_name=stage_name,
                            status=StageStatus.FAILED,
                            error=f"{emptied} scenes emptied by stage",
                            duration_seconds=duration
                        )

                # Check 4: Average word count didn't plummet (>40% avg loss)
                def _avg_wc(scene_list):
                    wcs = []
                    for s in scene_list:
                        if isinstance(s, dict):
                            c = s.get("content", "") or ""
                            wcs.append(len(c.split()))
                    return sum(wcs) / max(len(wcs), 1)

                old_avg = _avg_wc(scenes_snapshot)
                new_avg = _avg_wc(self.state.scenes)
                if old_avg > 100 and new_avg < old_avg * (1 - self._get_threshold("avg_word_plummet_pct")):
                    logger.error(
                        f"Transaction safety: {stage_name} average word count dropped "
                        f"{old_avg:.0f} -> {new_avg:.0f} ({(1 - new_avg/old_avg)*100:.0f}% loss). "
                        f"Restoring snapshot."
                    )
                    _log_incident(stage_name, "avg_word_plummet",
                                  f"Avg wc {old_avg:.0f}->{new_avg:.0f}",
                                  scene_count_before=old_count, scene_count_after=new_count)
                    if not _observe_only:
                        self.state.scenes = scenes_snapshot
                        return StageResult(
                            stage_name=stage_name,
                            status=StageStatus.FAILED,
                            error=f"Avg word count dropped {old_avg:.0f}->{new_avg:.0f}",
                            duration_seconds=duration
                        )

                # Check 5: Forbidden-marker explosion — if >40% of scenes contain
                # meta-text markers after the stage, the stage polluted everything
                if new_count > 3:
                    meta_markers = [
                        r'(?i)certainly!?\s*here\s+is',
                        r'(?i)the\s+rest\s+(?:of\s+the\s+)?(?:scene\s+)?remains?\s+unchanged',
                        r'(?i)changes\s+made:',
                        r'(?i)here\s+is\s+the\s+revised',
                    ]
                    polluted = 0
                    for s in self.state.scenes:
                        if isinstance(s, dict):
                            c = s.get("content", "") or ""
                            if any(re.search(pat, c) for pat in meta_markers):
                                polluted += 1
                    if polluted > new_count * self._get_threshold("forbidden_marker_pct"):
                        logger.error(
                            f"Transaction safety: {stage_name} meta-marker explosion — "
                            f"{polluted}/{new_count} scenes contain meta-text markers. "
                            f"Restoring snapshot."
                        )
                        _log_incident(stage_name, "meta_marker_explosion",
                                      f"{polluted}/{new_count} scenes polluted",
                                      scene_count_before=old_count, scene_count_after=new_count)
                        if not _observe_only:
                            self.state.scenes = scenes_snapshot
                            return StageResult(
                                stage_name=stage_name,
                                status=StageStatus.FAILED,
                                error=f"Meta-marker pollution: {polluted}/{new_count} scenes",
                                duration_seconds=duration
                            )

                # Check 6: Previously-distinct scenes didn't become identical
                import hashlib as _hl
                def _fp(s):
                    c = s.get("content", "") if isinstance(s, dict) else ""
                    return _hl.sha256((c or "").encode()).hexdigest()[:16]
                old_fps = [_fp(s) for s in scenes_snapshot]
                new_fps = [_fp(s) for s in self.state.scenes[:len(scenes_snapshot)]]
                old_unique = len(set(old_fps))
                new_unique = len(set(new_fps))
                if old_unique > 3 and new_unique < old_unique * self._get_threshold("fingerprint_collapse_pct"):
                    logger.error(
                        f"Transaction safety: {stage_name} fingerprint uniqueness collapsed "
                        f"{old_unique} -> {new_unique} distinct scenes. Restoring snapshot."
                    )
                    _log_incident(stage_name, "fingerprint_collapse",
                                  f"Unique scenes {old_unique}->{new_unique}",
                                  scene_count_before=old_count, scene_count_after=new_count)
                    if not _observe_only:
                        self.state.scenes = scenes_snapshot
                        return StageResult(
                            stage_name=stage_name,
                            status=StageStatus.FAILED,
                            error=f"Scene uniqueness collapsed: {old_unique}->{new_unique}",
                            duration_seconds=duration
                        )

            # Per-stage forbidden marker rate: track even when under threshold
            if self.state.scenes and len(self.state.scenes) > 0:
                _meta_pats = [
                    r'(?i)certainly!?\s*here\s+is',
                    r'(?i)the\s+rest\s+(?:of\s+the\s+)?(?:scene\s+)?remains?\s+unchanged',
                    r'(?i)changes\s+made:',
                    r'(?i)here\s+is\s+the\s+revised',
                ]
                _polluted = sum(
                    1 for s in self.state.scenes
                    if isinstance(s, dict) and any(
                        re.search(pat, s.get("content", "") or "") for pat in _meta_pats
                    )
                )
                _rate = _polluted / len(self.state.scenes)
                if stage_name not in self.state.artifact_metrics.get("per_stage", {}):
                    self.state.artifact_metrics.setdefault("per_stage", {})[stage_name] = {
                        "scenes": 0, "preamble": 0, "truncation": 0,
                        "alternate": 0, "analysis": 0, "pov_drift": 0,
                        "too_short": 0, "retried": 0
                    }
                self.state.artifact_metrics["per_stage"][stage_name]["forbidden_marker_rate"] = round(_rate, 4)
                if _rate > 0:
                    logger.info(f"Forbidden marker rate after {stage_name}: {_rate:.1%} ({_polluted}/{len(self.state.scenes)})")

            # Log artifact metrics for this stage
            self._log_artifact_summary(stage_name)

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

            # Restore scenes on error
            if scenes_snapshot is not None:
                logger.warning(f"Restoring scene snapshot after {stage_name} failure")
                _log_incident(stage_name, "exception_rollback",
                              str(e)[:200], severity="error",
                              scene_count_before=len(scenes_snapshot))
                self.state.scenes = scenes_snapshot

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
        """Generate high concept using Best-of-3 ensemble + validation + fingerprint.

        Generates 3 candidates with different creative angles (commercial,
        original, emotional), validates each, selects the best, builds a
        fingerprint for downstream drift detection.
        """
        config = self.state.config
        genre = config.get("genre", "literary fiction")

        # ── Input quality gate ─────────────────────────────────────────
        # Warn early if the synopsis is packed with generic phrases —
        # this predicts the LLM will echo them back.
        synopsis_raw = config.get("synopsis", "")
        if synopsis_raw:
            syn_lower = synopsis_raw.lower()
            input_generics = [p for p in CONCEPT_GENERIC_PHRASES if p in syn_lower]
            if len(input_generics) >= 3:
                logger.warning(
                    f"INPUT QUALITY GATE: Synopsis contains {len(input_generics)} "
                    f"generic phrases {input_generics}. High concept candidates "
                    f"will likely inherit these — consider rewriting the synopsis."
                )
                # Tighten pass threshold for this run: lower the bar the LLM
                # needs to clear means we're lenient; we want the opposite.
                # We store the count so validate_high_concept can access it.
                config["_input_generic_count"] = len(input_generics)

        # Lighter context for this stage: synopsis + genre + protagonist + conflict + themes
        context_parts = [
            f"GENRE: {genre}",
            f"TITLE: {config.get('title', 'Untitled')}",
        ]
        if config.get("synopsis"):
            context_parts.append(f"\nSYNOPSIS:\n{config.get('synopsis')}")
        if config.get("protagonist"):
            context_parts.append(f"\nPROTAGONIST:\n{config.get('protagonist')}")
        if config.get("central_conflict"):
            context_parts.append(f"\nCENTRAL CONFLICT:\n{config.get('central_conflict')}")
        if config.get("themes"):
            context_parts.append(f"\nTHEMES:\n{config.get('themes')}")
        if config.get("tone"):
            context_parts.append(f"\nTONE: {config.get('tone')}")
        if config.get("central_question"):
            context_parts.append(f"\nCENTRAL QUESTION: {config.get('central_question')}")
        light_context = "\n".join(context_parts)

        # Genre-specific guidance addendum
        genre_lower = genre.lower()
        genre_addendum = ""
        if "romance" in genre_lower:
            genre_addendum = (
                "\nFor this ROMANCE: foreground the central relationship tension, "
                "the trope(s), the emotional stakes of both leads, and why this "
                "pairing is fresh. Name both protagonists."
            )
        elif "thriller" in genre_lower or "mystery" in genre_lower:
            genre_addendum = (
                "\nFor this THRILLER/MYSTERY: lead with the inciting crime or threat, "
                "the protagonist's unique vulnerability, the ticking clock, and the "
                "twist that separates this from the genre pack."
            )
        elif "fantasy" in genre_lower or "sci-fi" in genre_lower or "science fiction" in genre_lower:
            genre_addendum = (
                "\nFor this SPECULATIVE FICTION: ground the concept in its unique world rule, "
                "name the protagonist and their specific power/limitation, and make the "
                "external threat mirror the internal conflict."
            )
        elif "literary" in genre_lower:
            genre_addendum = (
                "\nFor LITERARY FICTION: lead with the emotional question, the protagonist's "
                "central contradiction, and the specific milieu. Prioritize voice and "
                "thematic resonance over plot mechanics."
            )

        # Three creative angles for Best-of-3
        angle_instructions = {
            "commercial": (
                "Angle: COMMERCIAL HOOK. Lead with the market hook — what makes "
                "a reader grab this off the shelf. Emphasize the 'what if' premise, "
                "the stakes, and the genre promise."
            ),
            "original": (
                "Angle: ORIGINALITY. Lead with what makes this story unlike anything "
                "else in the genre. Emphasize the fresh twist, the subverted expectation, "
                "the element no reader has seen before."
            ),
            "emotional": (
                "Angle: EMOTIONAL CORE. Lead with the protagonist's deepest fear or "
                "desire. Make the reader feel the emotional stakes before they understand "
                "the plot mechanics. This should ache."
            ),
        }

        client = self.get_client_for_stage("high_concept")
        if not client:
            self.state.high_concept = "A compelling story about the given synopsis..."
            return self.state.high_concept, 100

        temp = self.get_temperature_for_stage("high_concept")
        total_tokens = 0
        candidates = []

        # Generate 3 candidates in parallel
        async def _gen_candidate(angle_name: str, angle_instruction: str) -> dict:
            prompt = f"""{light_context}
{genre_addendum}

{angle_instruction}

Write ONE paragraph (2-4 sentences) that captures the high concept of this novel.
Be SPECIFIC: name the protagonist, the setting, the central tension, and what's at stake emotionally.
Do NOT restate the synopsis. Distill and sharpen it into a pitch."""

            response = await client.generate(
                prompt,
                system_prompt=HIGH_CONCEPT_SYSTEM_PROMPT,
                temperature=temp,
                max_tokens=500,
                stop=PLANNING_STOP_SEQUENCES,
            )
            tokens = response.input_tokens + response.output_tokens
            raw = (response.content or "").strip()
            validation = validate_high_concept(raw, config)
            return {
                "angle": angle_name,
                "raw": raw,
                "text": validation["text"],
                "score": validation["score"],
                "issues": validation["issues"],
                "pass": validation["pass"],
                "tokens": tokens,
            }

        tasks = [
            _gen_candidate(name, instr)
            for name, instr in angle_instructions.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in results:
            if isinstance(r, Exception):
                logger.warning(f"High concept candidate failed: {r}")
                continue
            candidates.append(r)
            total_tokens += r["tokens"]

        # Filter to passing candidates
        passing = [c for c in candidates if c["pass"]]

        if not passing:
            # All candidates failed validation — retry once with strict prompt
            logger.warning("All 3 high concept candidates failed validation. Retrying with strict prompt.")
            strict_prompt = f"""{light_context}

CRITICAL: Your previous outputs were rejected for being too vague or containing non-concept text.
Write EXACTLY ONE paragraph (2-4 sentences). Name the protagonist. Name the setting.
State the central tension and emotional stakes. Be specific, not generic.
No preamble. No commentary. Start with the first word of the concept."""

            response = await client.generate(
                strict_prompt,
                system_prompt=HIGH_CONCEPT_SYSTEM_PROMPT,
                temperature=0.5,
                max_tokens=500,
                stop=PLANNING_STOP_SEQUENCES,
            )
            total_tokens += response.input_tokens + response.output_tokens
            raw = (response.content or "").strip()
            validation = validate_high_concept(raw, config)
            if validation["pass"]:
                passing = [{
                    "angle": "strict_retry",
                    "raw": raw,
                    "text": validation["text"],
                    "score": validation["score"],
                    "issues": validation["issues"],
                    "pass": True,
                    "tokens": response.input_tokens + response.output_tokens,
                }]
            else:
                # Last resort: use the best-scoring candidate even if it didn't pass
                if candidates:
                    best_failing = max(candidates, key=lambda c: c["score"])
                    logger.warning(
                        f"High concept: using best failing candidate "
                        f"(score={best_failing['score']}, issues={best_failing['issues']})"
                    )
                    passing = [best_failing]
                else:
                    raise RuntimeError("High concept generation failed: no candidates produced")

        # Select best passing candidate
        best = max(passing, key=lambda c: c["score"])
        self.state.high_concept = best["text"]

        # Store all candidates for inspection
        self.state.high_concept_candidates = [
            {"angle": c["angle"], "text": c["text"], "score": c["score"], "issues": c["issues"]}
            for c in candidates
        ]

        # Build fingerprint for drift detection
        self.state.high_concept_fingerprint = build_concept_fingerprint(best["text"])

        logger.info(
            f"High concept selected: angle={best['angle']}, score={best['score']}, "
            f"candidates={len(candidates)}, passing={len(passing)}"
        )
        if best.get("issues"):
            logger.info(f"High concept issues (accepted): {best['issues']}")

        return self.state.high_concept, total_tokens

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

            # Concept drift check
            if self.state.high_concept_fingerprint and response and response.content:
                drift = check_concept_drift(self.state.high_concept_fingerprint, response.content)
                if drift.get("drifted"):
                    logger.warning(
                        f"CONCEPT DRIFT in beat_sheet: keyword_overlap={drift['keyword_overlap']}, "
                        f"missing_entities={drift.get('missing_entities', [])}"
                    )

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
            self.state.emotional_arc = emotional_map
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

For each character, respond with these EXACT JSON keys:
- "name": character name
- "role": role/archetype
- "physical_description": detailed, vivid appearance
- "personality": strengths, flaws, quirks
- "backstory": formative events
- "goals": external and internal motivations
- "arc": start state -> end state transformation
- "voice": unique phrases, vocabulary, speech rhythm
- "signature_behaviors": habits, tells
- "relationships": connections to other characters

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
        BATCH_SIZE = 3

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

            # Collect used scene names for dedup guard
            used_scene_names = []
            for ch in all_chapters:
                if not isinstance(ch, dict):
                    continue
                for sc in ch.get("scenes", []):
                    if isinstance(sc, dict):
                        sn = sc.get("scene_name", "")
                        if sn:
                            used_scene_names.append(sn)

            dedup_guard = ""
            if used_scene_names:
                names_list = "\n".join(f"  - {n}" for n in used_scene_names)
                dedup_guard = (
                    f"\n=== ALREADY-USED SCENE NAMES (DO NOT REUSE OR PARAPHRASE) ===\n"
                    f"{names_list}\n"
                    f"Create NEW scene names that do not share more than 2 consecutive "
                    f"words with any name above. Each scene must have a fresh, specific title.\n"
                )
            # Within-batch uniqueness: model generates all batch scenes in one call
            within_batch_guard = (
                f"\n=== WITHIN THIS BATCH (chapters {batch_start}-{batch_end}) ===\n"
                f"Every scene_name must be UNIQUE. No two scenes in this batch may share the same "
                f"or nearly identical name (e.g. \"Late Night Call\" and \"Late Night Calls\" are duplicates).\n"
            )

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
{dedup_guard}
{within_batch_guard}
=== MANDATORY PLOT POINTS (these MUST appear in the outline) ===
{config.get('key_plot_points', 'None specified')}
Every event listed above MUST be dramatized in at least one scene. Map them to chapters:
- Events described as "ACT 1" must appear in chapters 1-{max(1, self.state.target_chapters // 4)}
- Events described as "ACT 2" must appear in chapters {self.state.target_chapters // 4 + 1}-{self.state.target_chapters * 3 // 4}
- Events described as "ACT 3" must appear in chapters {self.state.target_chapters * 3 // 4 + 1}-{self.state.target_chapters}
If a key_plot_point describes the INCITING INCIDENT (first meeting, discovery, etc.),
it MUST be in Chapter 1 or 2. Do NOT skip it or start the story after it happened.

=== GENERATE CHAPTERS {batch_start} THROUGH {batch_end} ===

TARGET: {self.state.target_chapters} chapters total, {self.state.scenes_per_chapter} scenes per chapter
{self._build_pov_prompt_block(batch_start, batch_end) if is_dual_pov else "POV: " + protagonist}

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

=== STRUCTURAL CAPS (hard limits) ===
1. DIGITAL INTERACTION SCENES: Max 2 per act (roughly every {self.state.target_chapters // 3} chapters).
   "Digital interaction" = character reads/sends a text, checks phone, video calls,
   scrolls social media, or stares at a screen as the main action. If a scene's
   PRIMARY action is phone/laptop, it counts. Background phone use does not.
   After the cap, force characters into physical-world scenes.

2. SUSPENSE THREADS: If you introduce a threat, mystery, shadow, secret, or
   unanswered question, you MUST mark it with a "thread" field in the scene:
   {{"thread": "shadow_figure", "thread_action": "introduce"}}
   Later scenes that advance or resolve that thread must also mark it:
   {{"thread": "shadow_figure", "thread_action": "escalate"|"resolve"}}
   Every introduced thread MUST have at least one "escalate" and one "resolve"
   within the outline. No dangling suspense.

3. OPENING HOOK VARIETY: Across the full outline, chapter openings must vary:
   - At least 2 must open mid-dialogue
   - At least 2 must open with physical action (not thinking/observing)
   - At least 1 must open with a time jump or location change
   - No more than 2 consecutive chapters may open with internal monologue

4. GENRE DISCIPLINE ({config.get('genre', 'general').upper()}):
{"   - ROMANCE: Do NOT plan any thriller/horror/suspense beats (no shadowy figures, no mysterious notes, no stalkers, no anonymous threats). Tension comes from EMOTIONAL stakes: miscommunication, fear of vulnerability, distance, cultural differences, timing." if 'romance' in config.get('genre', '').lower() else ""}
{"   - Hooks must come from character emotion and relationship tension, NOT from manufactured danger." if 'romance' in config.get('genre', '').lower() else ""}
   - Every scene must serve the story's genre. Do not inject elements from other genres.
   - Location variety: no more than 3 scenes total in cafes/coffee shops across the entire outline.

Respond with a JSON object containing a "chapters" array of {batch_end - batch_start + 1} chapter objects. Each chapter MUST have "chapter", "chapter_title", and "scenes" keys."""

            # Retry loop: only break on valid outline shape. Raw wrapper is NOT success.
            MAX_OUTLINE_RETRIES = 2
            batch = []
            raw_text = ""
            failure_modes = []
            recoveries = []
            if self.state.outline_json_report is None:
                self.state.outline_json_report = {"batches": [], "backfill": {"requested": [], "attempts": [], "failures": []}}

            for retry_idx in range(MAX_OUTLINE_RETRIES + 1):
                retry_temp = 0.4 if retry_idx > 0 else None
                retry_max = self.get_max_tokens_for_stage("master_outline", 3072 if retry_idx > 0 else 4096)
                response = await client.generate(prompt, max_tokens=retry_max,
                                                  json_mode=True, temperature=retry_temp,
                                                  timeout=600)
                raw_text = response.content if response else ""
                batch = extract_json_robust(raw_text, expect_array=True)

                if _is_valid_outline_batch(batch):
                    if retry_idx > 0:
                        recoveries.append({"attempt": retry_idx, "type": "regenerate_success"})
                    break

                # Record failure
                fail_type = "raw_wrapper" if _is_raw_failure(batch) else "invalid_shape"
                failure_modes.append({"attempt": retry_idx, "type": fail_type, "chars": len(raw_text)})

                # Tier A: local repair on raw text
                repair_raw = raw_text
                if _is_raw_failure(batch) and isinstance(batch, list) and batch and isinstance(batch[0], dict):
                    repair_raw = batch[0].get("raw", raw_text)
                repaired = self._repair_truncated_json(repair_raw)
                if repaired and _is_valid_outline_batch(repaired):
                    batch = repaired
                    recoveries.append({"attempt": retry_idx, "type": "local_repair", "chapters_extracted": len(repaired)})
                    logger.info(f"Outline batch {batch_start}-{batch_end} recovered via local repair")
                    break

                if retry_idx < MAX_OUTLINE_RETRIES:
                    logger.warning(f"Outline batch {batch_start}-{batch_end} parse failed "
                                   f"(attempt {retry_idx + 1}/{MAX_OUTLINE_RETRIES + 1}): {fail_type}. Retrying...")
                else:
                    logger.error(f"Outline batch {batch_start}-{batch_end} failed after {MAX_OUTLINE_RETRIES + 1} attempts")

            attempts_made = len(failure_modes) + (1 if _is_valid_outline_batch(batch) else 0)
            parse_failures = len(failure_modes)
            repair_uses = sum(1 for r in recoveries if r.get("type") == "local_repair")
            self.state.outline_json_report["batches"].append({
                "batch_range": f"{batch_start}-{batch_end}",
                "attempts_made": attempts_made,
                "parse_failures": parse_failures,
                "repair_uses": repair_uses,
                "success": _is_valid_outline_batch(batch),
                "failure_modes": failure_modes,
                "recoveries": recoveries,
            })

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
            # Collect into validated_batch first so we can run collision detection before appending
            validated_batch = []
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
                    validated_batch.append(ch)
                elif "raw" in ch:
                    logger.warning(f"Batch {batch_start}-{batch_end} returned raw text, attempting repair")
                    raw = ch["raw"]
                    repaired = self._repair_truncated_json(raw)
                    if repaired:
                        for rch in repaired:
                            if isinstance(rch, dict) and "scenes" in rch:
                                validated_batch.append(rch)
                else:
                    logger.warning(f"Chapter object missing 'scenes' key. Keys found: {list(ch.keys())}")

            # Fallback: if model returned flat scenes instead of chapters, group them
            # qwen2.5/llama often output {"chapters": [{scene1}, {scene2}, ...]} - flat scene objects
            has_proper_chapters = any(isinstance(ch, dict) and "scenes" in ch for ch in batch if isinstance(ch, dict))
            if not has_proper_chapters:
                def is_flat_scene(obj):
                    if not isinstance(obj, dict) or "scenes" in obj:
                        return False
                    return "scene" in obj or "scene_number" in obj
                flat_scenes = [ch for ch in batch if is_flat_scene(ch)]
                if flat_scenes:
                    spc = max(1, self.state.scenes_per_chapter)
                    expected_chapters = set(range(batch_start, batch_end + 1))
                    logger.info(f"Detected {len(flat_scenes)} flat scenes, grouping into chapters (spc={spc})")
                    for ch_idx in range(batch_start, batch_end + 1):
                        offset = (ch_idx - batch_start) * spc
                        ch_scenes = flat_scenes[offset:offset + spc]
                        if ch_scenes:
                            # Ensure scene_number set for downstream; sort by scene_number for contiguous order
                            for i, sc in enumerate(ch_scenes):
                                if "scene_number" not in sc and "scene" in sc:
                                    sc["scene_number"] = sc["scene"]
                                elif "scene_number" not in sc:
                                    sc["scene_number"] = i + 1
                            ch_scenes.sort(key=lambda s: s.get("scene_number", 0))
                            validated_batch.append({
                                "chapter": ch_idx,
                                "chapter_title": ch_scenes[0].get("scene_name", f"Chapter {ch_idx}"),
                                "scenes": ch_scenes
                            })
                    # Safety: drop chapters with no scenes; ensure chapter numbers in expected set
                    validated_batch[:] = [
                        ch for ch in validated_batch
                        if isinstance(ch, dict) and ch.get("chapter") in expected_chapters
                        and isinstance(ch.get("scenes"), list) and len(ch["scenes"]) >= 1
                    ]

            # Post-gen collision detector: fix duplicate/near-duplicate scene names
            if validated_batch:
                collisions = self._detect_scene_name_collisions(validated_batch, used_scene_names)
                if collisions:
                    logger.warning(f"Scene name collisions: {len(collisions)} duplicates in batch {batch_start}-{batch_end}")
                    regen_tokens = await self._regenerate_colliding_scene_names(
                        client, validated_batch, collisions, used_scene_names
                    )
                    total_tokens += regen_tokens

            all_chapters.extend(validated_batch)
            total_tokens += response.input_tokens + response.output_tokens
            logger.info(f"Outlined chapters {batch_start}-{batch_end}: {len(all_chapters)} total chapters so far")

        # Chapter completeness check: detect and backfill any missing chapters
        produced_nums = {ch.get("chapter", 0) for ch in all_chapters if isinstance(ch, dict)}
        expected_nums = set(range(1, self.state.target_chapters + 1))
        missing = sorted(expected_nums - produced_nums)
        if missing:
            if self.state.outline_json_report:
                self.state.outline_json_report["backfill"]["requested"] = [int(m) for m in missing]
            logger.warning(f"Missing chapters after outline generation: {missing}. "
                           f"Attempting per-chapter backfill...")
            MAX_BACKFILL_RETRIES = 2
            for miss_ch in missing:
                expected_pov = self._expected_pov_for_chapter(miss_ch)
                backfill_prompt = f"""{story_context}
{strategic}

Generate ONLY chapter {miss_ch} of {self.state.target_chapters}.
Include {self.state.scenes_per_chapter} scenes per chapter.
POV for chapter {miss_ch}: ALL scenes must have "pov": "{expected_pov}".

Each scene must include: scene (number), scene_name, pov, purpose, differentiator, character_scene_goal, central_conflict, opening_hook, outcome, location, emotional_arc, tension_level (1-10), pacing, spice_level (0-5).

Respond with a JSON object: {{"chapters": [{{"chapter": {miss_ch}, "chapter_title": "...", "scenes": [...]}}]}}"""
                bf_success = False
                bf_attempts = 0
                bf_recovery = None
                for bf_retry in range(MAX_BACKFILL_RETRIES + 1):
                    try:
                        bf_response = await client.generate(backfill_prompt, max_tokens=2048,
                                                            json_mode=True, temperature=0.4,
                                                            timeout=600)
                        bf_raw = bf_response.content if bf_response else ""
                        bf_batch = extract_json_robust(bf_raw, expect_array=True)
                        if isinstance(bf_batch, dict):
                            for key in ("chapters", "outline"):
                                if key in bf_batch and isinstance(bf_batch[key], list):
                                    bf_batch = bf_batch[key]
                                    break
                        if isinstance(bf_batch, list):
                            valid_chs = [ch for ch in bf_batch if isinstance(ch, dict) and "scenes" in ch]
                            if valid_chs:
                                bf_ch = valid_chs[0]
                                bf_ch["chapter"] = miss_ch
                                all_chapters.append(bf_ch)
                                logger.info(f"Backfilled chapter {miss_ch}")
                                total_tokens += bf_response.input_tokens + bf_response.output_tokens
                                bf_success = True
                                bf_attempts = bf_retry + 1
                                if bf_retry > 0:
                                    bf_recovery = "regenerate_success"
                                break
                        if _is_raw_failure(bf_batch):
                            repair_raw = bf_raw
                            if isinstance(bf_batch, list) and bf_batch and isinstance(bf_batch[0], dict):
                                repair_raw = bf_batch[0].get("raw", bf_raw)
                            repaired = self._repair_truncated_json(repair_raw)
                            if repaired:
                                valid_chs = [ch for ch in repaired if isinstance(ch, dict) and "scenes" in ch]
                                if valid_chs:
                                    bf_ch = valid_chs[0]
                                    bf_ch["chapter"] = miss_ch
                                    all_chapters.append(bf_ch)
                                    logger.info(f"Backfilled chapter {miss_ch} via local repair")
                                    total_tokens += bf_response.input_tokens + bf_response.output_tokens
                                    bf_success = True
                                    bf_attempts = bf_retry + 1
                                    bf_recovery = "local_repair"
                                    break
                    except Exception as e:
                        logger.warning(f"Backfill chapter {miss_ch} attempt {bf_retry + 1} failed: {e}")
                    bf_attempts = bf_retry + 1
                if self.state.outline_json_report:
                    self.state.outline_json_report["backfill"]["attempts"].append({
                        "chapter": miss_ch, "attempts": bf_attempts + 1, "success": bf_success, "recovery": bf_recovery
                    })
                if not bf_success and self.state.outline_json_report:
                    self.state.outline_json_report["backfill"]["failures"].append(miss_ch)
            # Re-sort by chapter number
            all_chapters.sort(key=lambda ch: ch.get("chapter", 0) if isinstance(ch, dict) else 0)

        # Deterministic scene order within each chapter (chapter_index, scene_index)
        def _scene_sort_key(s):
            if not isinstance(s, dict):
                return 0
            v = s.get("scene_number") or s.get("scene", 0) or 0
            try:
                return int(v)
            except (TypeError, ValueError):
                return 0

        for ch in all_chapters:
            if isinstance(ch, dict) and "scenes" in ch:
                ch["scenes"] = sorted(ch["scenes"], key=_scene_sort_key)

        # Stamp stable scene IDs: "ch02_s01" etc. Iteration order is
        # chapter_num then scene_index. If scene_id already exists (e.g. reload),
        # assert it matches expected; do not overwrite.
        for ch in all_chapters:
            if not isinstance(ch, dict):
                continue
            ch_num = int(ch.get("chapter", 0))
            for i, sc in enumerate(ch.get("scenes", [])):
                if not isinstance(sc, dict):
                    continue
                expected = f"ch{ch_num:02d}_s{i+1:02d}"
                existing = sc.get("scene_id")
                if existing:
                    if existing != expected:
                        logger.error(
                            f"scene_id mismatch: expected {expected}, got {existing} "
                            f"(ch={ch_num}, scene_idx={i}); possible reorder/stamp drift"
                        )
                        raise ValueError(f"scene_id integrity: {existing} != {expected}")
                else:
                    sc["scene_id"] = expected

        # Deterministic POV normalization: overwrite scene POVs to match
        # the dual-POV chapter rule. This is the safety net — even if the model
        # freelances POVs, every scene gets the correct chapter-level assignment.
        self._normalize_outline_pov(all_chapters)

        self.state.master_outline = all_chapters
        total_scenes = sum(len(ch.get("scenes", [])) for ch in all_chapters if isinstance(ch, dict))
        logger.info(f"Master outline complete: {len(all_chapters)} chapters, {total_scenes} total scenes")
        if len(all_chapters) == 0:
            logger.warning("Master outline is empty - scene_drafting will have nothing to process")

        # Concept drift check on full outline text
        if self.state.high_concept_fingerprint and all_chapters:
            outline_text = json.dumps(all_chapters, indent=1)
            drift = check_concept_drift(self.state.high_concept_fingerprint, outline_text)
            if drift.get("drifted"):
                logger.warning(
                    f"CONCEPT DRIFT in master_outline: keyword_overlap={drift['keyword_overlap']}, "
                    f"missing_entities={drift.get('missing_entities', [])}"
                )

        return self.state.master_outline, total_tokens

    def _scene_name_fuzzy_match(self, a: str, b: str) -> bool:
        """True if two scene names are too similar (duplicate risk)."""
        if not a or not b:
            return False
        a_norm = a.lower().strip()
        b_norm = b.lower().strip()
        if a_norm == b_norm:
            return True
        a_words = [w for w in a_norm.split() if len(w) > 2]
        b_words = set(w for w in b_norm.split() if len(w) > 2)
        if not a_words or not b_words:
            return False
        # Two+ consecutive words in common
        for i in range(len(a_words) - 1):
            bigram = f"{a_words[i]} {a_words[i+1]}"
            if bigram in b_norm or (a_words[i] in b_words and a_words[i + 1] in b_words):
                return True
        # One name contained in the other (e.g. "Late Night" in "Late Night Call")
        if len(a_norm) >= 4 and len(b_norm) >= 4:
            if a_norm in b_norm or b_norm in a_norm:
                return True
        return False

    def _detect_scene_name_collisions(
        self, batch_chapters: list, used_names: list
    ) -> list:
        """Returns list of (ch_idx, sc_idx, scene, collided_with)."""
        collisions = []
        seen_in_batch = []
        for ch_idx, ch in enumerate(batch_chapters):
            if not isinstance(ch, dict):
                continue
            for sc_idx, sc in enumerate(ch.get("scenes", [])):
                if not isinstance(sc, dict):
                    continue
                name = (sc.get("scene_name") or "").strip()
                if not name:
                    continue
                # Check against used (previous batches)
                for prev in used_names:
                    if self._scene_name_fuzzy_match(name, prev):
                        collisions.append((ch_idx, sc_idx, sc, prev))
                        break
                else:
                    # Check against seen in this batch
                    for seen_name, (sci, scj) in seen_in_batch:
                        if self._scene_name_fuzzy_match(name, seen_name):
                            collisions.append((ch_idx, sc_idx, sc, seen_name))
                            break
                    else:
                        seen_in_batch.append((name, (ch_idx, sc_idx)))
        return collisions

    async def _regenerate_colliding_scene_names(
        self, client, batch_chapters: list, collisions: list, used_names: list
    ) -> int:
        """Regenerate scene_name for colliding scenes. Returns tokens used.

        Scene identity is immutable: we patch the existing scene dict in place,
        overwriting only scene_name. Never replace the scene object or reassign
        chapter/scene indices. scene_id is stamped based on chapter_index + scene_index.
        """
        if not client or not collisions:
            return 0
        total_tokens = 0
        blacklist = list(used_names)
        for ch_idx, sc_idx, scene, _ in collisions:
            purpose = scene.get("purpose", "")[:200]
            differentiator = scene.get("differentiator", "")[:150]
            names_bl = ", ".join(blacklist[-50:]) if blacklist else "none yet"
            prompt = f"""Generate a UNIQUE scene name (2-8 words) for this scene.
Purpose: {purpose}
Differentiator: {differentiator}

DO NOT use or closely paraphrase any of these already-used names:
{names_bl}

Output ONLY the new scene name, nothing else. No quotes, no commentary."""
            try:
                response = await client.generate(prompt, max_tokens=50, temperature=0.4)
                if response and response.content:
                    new_name = response.content.strip().strip('"\'')
                    if new_name and len(new_name) < 100:
                        scene["scene_name"] = new_name
                        blacklist.append(new_name)
                        logger.info(f"Regenerated scene name: {new_name}")
                total_tokens += (response.input_tokens or 0) + (response.output_tokens or 0)
            except Exception as e:
                logger.warning(f"Scene name regenerate failed: {e}")
        return total_tokens

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
        if "romance" in genre or "romantic" in genre or "mafia" in genre:
            applicable_tropes = ROMANCE_TROPES

        # Get tropes from config market positioning AND strategic_guidance.tropes
        guidance = config.get("strategic_guidance", {})
        market_pos = guidance.get("market_positioning", "").lower()
        user_tropes_raw = guidance.get("tropes", "")
        config_str_lower = str(config).lower()

        # Check which predefined tropes are promised
        tropes_to_check = []
        for trope_key, trope_data in applicable_tropes.items():
            trope_name = trope_key.replace("_", " ")
            if trope_name in market_pos or trope_name in config_str_lower:
                tropes_to_check.append((trope_key, trope_data))

        # Also parse user-defined tropes from strategic_guidance.tropes
        if user_tropes_raw:
            for line in user_tropes_raw.split("\n"):
                line = line.strip().lstrip("-").strip()
                if not line:
                    continue
                # Skip if already covered by a predefined trope
                line_lower = line.lower()
                already_covered = any(
                    tk.replace("_", " ") in line_lower
                    for tk, _ in tropes_to_check
                )
                if not already_covered:
                    trope_key = line_lower.replace(" ", "_").replace("-", "_")[:40]
                    tropes_to_check.append((trope_key, {
                        "description": line,
                        "required_elements": [f"Execute '{line}' trope naturally in scene"],
                        "placement": "per_outline",
                    }))

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
                                # Protect normalized POV from being overwritten by trope additions
                                saved_pov = scene.get("pov")
                                scene.update(additions)
                                if saved_pov:
                                    scene["pov"] = saved_pov
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

    def _get_protagonist_gender(self) -> str:
        """Detect protagonist gender from config for POV pronoun safety.

        Returns 'male', 'female', or '' (unknown).
        Uses writing_style POV hints and name heuristics.
        """
        if not self.state or not self.state.config:
            return ""
        config = self.state.config
        writing_style = config.get("writing_style", "").lower()
        protagonist = config.get("protagonist", "").lower()

        # Check explicit POV hints in writing_style
        # "Mia's POV" / "her POV" -> female
        # "Ethan's POV" / "his POV" -> male
        if "his pov" in writing_style or "he/" in writing_style:
            return "male"
        if "her pov" in writing_style or "she/" in writing_style:
            return "female"

        # Check protagonist description for gender signals
        male_signals = ["he ", "his ", "him ", " man", " boy", " male",
                        " husband", " father", " son", " brother", " guy"]
        female_signals = ["she ", "her ", " woman", " girl", " female",
                          " wife", " mother", " daughter", " sister"]

        male_score = sum(1 for s in male_signals if s in protagonist)
        female_score = sum(1 for s in female_signals if s in protagonist)

        # Check writing_style for pronoun references
        if "mia's" in writing_style or "lena's" in writing_style:
            female_score += 2
        if "ethan's" in writing_style or "eli's" in writing_style:
            male_score += 2

        # Check for common gendered terms in protagonist field
        combined = protagonist + " " + writing_style
        if any(t in combined for t in [" her ", "she's", "she is"]):
            female_score += 1
        if any(t in combined for t in [" his ", "he's", "he is"]):
            male_score += 1

        if male_score > female_score:
            return "male"
        if female_score > male_score:
            return "female"
        return ""

    def _get_foreign_whitelist(self) -> list:
        """Get project-specific foreign word whitelist from config."""
        if self.state and self.state.config:
            return self.state.config.get("defense", {}).get("foreign_word_whitelist", [])
        return []

    @staticmethod
    def _normalize_character_name(name: str) -> str:
        """Normalize a character name for matching: lowercase, strip parens/titles/punctuation."""
        if not name:
            return ""
        # Strip parentheticals like "(Alpha)" or "(30, the Alpha...)"
        cleaned = re.sub(r'\([^)]*\)', '', name)
        # Strip common titles/prefixes
        cleaned = re.sub(r'\b(alpha|beta|dr|mr|mrs|ms|the)\b', '', cleaned, flags=re.IGNORECASE)
        # Strip punctuation, collapse whitespace
        cleaned = re.sub(r'[^\w\s]', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip().lower()
        return cleaned.split()[0] if cleaned else ""

    def _get_character_gender(self, character_name: str) -> str:
        """Detect gender for any character by name, searching config fields.

        Checks protagonist and other_characters descriptions for gender signals.
        Name matching is normalized (lowercase, stripped of titles/parens).
        Returns 'male', 'female', or '' (unknown).
        """
        if not character_name or not self.state or not self.state.config:
            return ""

        config = self.state.config
        char_normalized = self._normalize_character_name(character_name)
        if not char_normalized:
            return ""

        # Check if this is the protagonist
        protagonist = config.get("protagonist", "")
        if protagonist:
            protag_normalized = self._normalize_character_name(protagonist)
            if protag_normalized == char_normalized:
                return self._get_protagonist_gender()

        # Search other_characters for this character's description
        other_chars = config.get("other_characters", "")
        if not other_chars:
            return ""

        # Extract the description block for this character
        # Primary: match "CharName ... (description)" — parens contain the character bio
        char_first = character_name.strip().split()[0]
        paren_pattern = re.compile(
            rf'\b{re.escape(char_first)}\b[^(]*\([^)]*\)',
            re.IGNORECASE
        )
        match = paren_pattern.search(other_chars)
        if not match:
            # Fallback: match "CharName ... next sentence."
            fallback = re.compile(
                rf'\b{re.escape(char_first)}\b[^.]*\.',
                re.IGNORECASE
            )
            match = fallback.search(other_chars)
        if match:
            char_desc = match.group(0).lower()
        else:
            char_desc = ""

        if not char_desc:
            return ""

        # Check for explicit gender markers
        male_signals = [" male", " man,", " man.", " boy", " husband", " father",
                        " son,", " son.", " brother", " guy", " he ", " his "]
        female_signals = [" female", " woman", " girl", " wife", " mother",
                          " daughter", " sister", " she ", " her "]

        male_score = sum(1 for s in male_signals if s in char_desc)
        female_score = sum(1 for s in female_signals if s in char_desc)

        if male_score > female_score:
            return "male"
        if female_score > male_score:
            return "female"
        return ""

    @staticmethod
    def _infer_gender_from_pronouns(text: str) -> str:
        """Fallback gender inference from pronoun frequency in raw text.

        Used when config-based gender detection returns unknown.
        Counts he/his/him vs she/her outside dialogue, requires 2x dominance.
        Returns 'male', 'female', or '' (unknown).
        """
        if not text:
            return ""
        # Strip dialogue to avoid counting character speech
        stripped = re.sub(r'"[^"]*"', '', text)
        stripped = re.sub(r'[\u201c][^\u201d]*[\u201d]', '', stripped)

        he_count = len(re.findall(r'\b(?:he|his|him)\b', stripped, re.IGNORECASE))
        she_count = len(re.findall(r'\b(?:she|her|hers)\b', stripped, re.IGNORECASE))

        if he_count >= 2 * she_count and he_count >= 3:
            return "male"
        if she_count >= 2 * he_count and she_count >= 3:
            return "female"
        return ""

    def _get_dual_pov_characters(self) -> tuple:
        """Get (protagonist_name, secondary_name) for dual-POV projects.

        Returns the two POV character names extracted from config.
        Protagonist = odd chapters, secondary (first in other_characters) = even chapters.
        """
        config = self.state.config
        protag = config.get("protagonist", "").split(",")[0].strip() if config.get("protagonist") else "Protagonist"
        other = config.get("other_characters", "")
        secondary = other.split("(")[0].strip() if other else "Hero"
        return protag, secondary

    def _expected_pov_for_chapter(self, chapter_num: int) -> str:
        """Return the expected POV character name for a chapter number.

        Dual-POV rule: odd chapters = protagonist, even chapters = secondary.
        Falls back to protagonist for non-dual-POV projects.
        """
        writing_style = self.state.config.get("writing_style", "")
        if "dual pov" not in writing_style.lower():
            return self._get_protagonist_name()
        protag, secondary = self._get_dual_pov_characters()
        return protag if chapter_num % 2 == 1 else secondary

    def _build_pov_prompt_block(self, batch_start: int, batch_end: int) -> str:
        """Build explicit POV assignment block for master_outline prompt.

        Creates a per-chapter POV table so the model can't freelance.
        """
        protag, secondary = self._get_dual_pov_characters()
        lines = [
            f"=== DUAL POV: CHAPTER-LEVEL ASSIGNMENT (NON-NEGOTIABLE) ===",
            f"This novel uses DUAL FIRST-PERSON POV. POV is assigned PER CHAPTER, not per scene.",
            f"Odd chapters: {protag} (all scenes in odd chapters use {protag}'s POV)",
            f"Even chapters: {secondary} (all scenes in even chapters use {secondary}'s POV)",
            f"",
            f"POV TABLE for this batch:",
        ]
        for ch in range(batch_start, batch_end + 1):
            pov_char = protag if ch % 2 == 1 else secondary
            lines.append(f"  Chapter {ch}: pov = \"{pov_char}\" (ALL scenes)")
        lines.extend([
            f"",
            f"EVERY scene object must include \"pov\": \"{protag}\" or \"pov\": \"{secondary}\"",
            f"matching the chapter rule above. Do NOT mix POVs within a chapter.",
        ])
        return "\n".join(lines)

    def _normalize_outline_pov(self, chapters: list) -> int:
        """Deterministic POV normalizer: overwrite scene POVs to match chapter rule.

        Returns the number of POV mismatches corrected.
        """
        writing_style = self.state.config.get("writing_style", "")
        if "dual pov" not in writing_style.lower():
            return 0

        corrections = 0
        for ch in chapters:
            if not isinstance(ch, dict):
                continue
            ch_num = ch.get("chapter", 0)
            expected = self._expected_pov_for_chapter(ch_num)
            for sc in ch.get("scenes", []):
                if not isinstance(sc, dict):
                    continue
                current = sc.get("pov", "")
                if not current or self._normalize_character_name(current) != self._normalize_character_name(expected):
                    sc["pov"] = expected
                    corrections += 1
        if corrections:
            logger.info(f"POV normalizer: corrected {corrections} scene POV assignments to match chapter rule")
        return corrections

    def _build_voice_modifiers_block(self, pov_char: str, chapter_num: int) -> str:
        """Build voice modifier instructions for the scene drafting prompt.

        Detects italic inner voice (wolf voice, etc.) from writing_style config
        and generates explicit formatting examples when the current POV character
        has an inner voice described in the config.
        """
        writing_style = self.state.config.get("writing_style", "").lower()
        if "italic" not in writing_style:
            return ""

        # Parse which character has the italic inner voice
        # Config format: "Kaelen's wolf voice appears in italics as a distinct..."
        ws_full = self.state.config.get("writing_style", "")
        pov_lower = pov_char.lower().split()[0]  # First name only

        # Check if this POV character is the one with the italic voice
        if pov_lower not in ws_full.lower():
            return ""

        # Find the italic voice description
        italic_idx = ws_full.lower().find("italic")
        if italic_idx == -1:
            return ""

        # Extract context around "italic" mention (sentence or surrounding text)
        # Look backwards for the character name
        pre_text = ws_full[:italic_idx + 80]

        # Only generate if this character's name appears near "italic"
        name_idx = pre_text.lower().rfind(pov_lower)
        if name_idx == -1 or (italic_idx - name_idx) > 120:
            return ""

        # Extract the voice description
        voice_desc = ws_full[name_idx:min(len(ws_full), italic_idx + 200)]
        # Trim to sentence boundary
        for end_char in ['.', ')', '\n']:
            end_idx = voice_desc.find(end_char, 50)
            if end_idx != -1:
                voice_desc = voice_desc[:end_idx + 1]
                break

        return f"""
=== INNER VOICE (ITALIC FORMATTING — REQUIRED) ===
From the style guide: {voice_desc.strip()}

You MUST include italic inner voice lines in this scene. Format: *italic text*
These are {pov_char}'s raw, unfiltered inner thoughts — short, primal, distinct
from the narrative voice.

EXAMPLES (adapt to the scene):
  *Mine.* The thought hit before I could stop it.
  *Protect. Keep. Ours.* My hands shook with the effort of staying still.
  I forced myself to breathe. *Not yet. Not safe.*
  *She's here.* The wolf surged against my ribs.

RULES:
- Include at least 2-3 italic inner voice lines per scene
- Keep them SHORT (1-5 words typically, max 10)
- They interrupt the narrative — placed on their own line or mid-paragraph
- They should feel involuntary, like intrusive thoughts
- Use asterisks for italics: *word* (not _word_)
"""

    def _get_pov_info(self, pov_character: str = "", scene_text: str = "") -> tuple:
        """Get (name, gender) for the current POV character.

        If pov_character is provided and differs from the global protagonist,
        looks up that character's info. Otherwise returns global protagonist info.
        Falls back to pronoun frequency in scene_text if config lookup fails.
        Returns (pov_name: str, pov_gender: str).
        """
        protag_name = self._get_protagonist_name()

        if not pov_character or not pov_character.strip():
            return protag_name, self._get_protagonist_gender()

        # Normalize for comparison
        pov_normalized = self._normalize_character_name(pov_character)
        protag_normalized = self._normalize_character_name(protag_name)

        if pov_normalized == protag_normalized:
            return protag_name, self._get_protagonist_gender()

        # POV is a non-protagonist character — use their name and detect their gender
        pov_first = pov_character.strip().split()[0]
        pov_gender = self._get_character_gender(pov_character)

        # Fallback: if config-based detection failed, try pronoun counting in scene text
        if not pov_gender and scene_text:
            pov_gender = self._infer_gender_from_pronouns(scene_text)
            if pov_gender:
                logger.debug(
                    f"Gender for {pov_first} inferred from pronouns: {pov_gender}"
                )

        return pov_first, pov_gender

    def _postprocess(self, text: str, pov_character: str = "") -> str:
        """Apply all code-level post-processing to scene content.

        Convenience wrapper that gets POV character info from config.
        For dual-POV projects, pass pov_character to use the correct name/gender
        instead of the global protagonist.
        """
        # Pass raw text for pronoun-based fallback gender inference
        pov_name, pov_gender = self._get_pov_info(pov_character, scene_text=text)
        return _postprocess_scene(
            text,
            pov_name,
            self._get_setting_language(),
            pov_gender,
            self._get_foreign_whitelist()
        )

    # ========================================================================
    # Critic Gate, Artifact Metrics, Prose Generation Wrapper
    # ========================================================================

    # Fuzzy preamble detection: exemplars of meta-text openings
    # Used for n-gram similarity matching against first 100 chars of output
    _PREAMBLE_EXEMPLARS = [
        "sure here is the revised scene",
        "certainly here is the enhanced version",
        "here is the polished scene as requested",
        "i've revised the scene to",
        "i have rewritten the text",
        "below is the expanded scene",
        "the following is the updated version",
        "of course here is the revised",
        "absolutely here is the scene",
        "here's the revised opening",
        "sure here's the updated chapter",
        "as requested here is the",
        "let me provide the revised",
        "i've enhanced the scene",
    ]

    @staticmethod
    def _ngram_similarity(text_a: str, text_b: str, n: int = 3) -> float:
        """Character n-gram Jaccard similarity between two strings."""
        a_lower = text_a.lower().strip()
        b_lower = text_b.lower().strip()
        if len(a_lower) < n or len(b_lower) < n:
            return 0.0
        ngrams_a = set(a_lower[i:i+n] for i in range(len(a_lower) - n + 1))
        ngrams_b = set(b_lower[i:i+n] for i in range(len(b_lower) - n + 1))
        if not ngrams_a or not ngrams_b:
            return 0.0
        return len(ngrams_a & ngrams_b) / len(ngrams_a | ngrams_b)

    def _validate_scene_output(self, text: str, scene_meta: dict = None) -> dict:
        """Lightweight critic gate: check raw LLM output for obvious problems.

        Runs BEFORE postprocessing so we can measure what the model actually produced.
        Returns dict with 'pass' bool and specific issue flags.
        """
        if not text:
            return {"pass": False, "issues": {"empty": True}, "word_count": 0}

        issues = {}

        # Check for preamble / meta-text in first 200 chars — exact patterns
        preamble_patterns = [
            r'^(?:Sure|Certainly|Of course|Absolutely)[,!.\s]',
            r'^(?:Here\s+is|Below\s+is|I\'ve\s+(?:revised|enhanced|rewritten))',
            r'^(?:The\s+following\s+is)',
        ]
        for pat in preamble_patterns:
            if re.search(pat, text[:200], re.IGNORECASE):
                issues["preamble"] = True
                break

        # Fuzzy preamble detection: catch novel variants via n-gram similarity
        # GUARD: Only run fuzzy detection if the first line has an "assistant-y anchor"
        # word. This prevents false positives on prose starting with '"Sure," I said...'
        _ASSISTANT_ANCHORS = {
            "revised", "rewritten", "enhanced", "polished", "updated", "improved",
            "expanded", "below", "here is", "here's", "as requested", "following",
            "changes made", "version", "i've", "i have", "let me",
        }
        if "preamble" not in issues:
            first_line = text.split('\n', 1)[0][:120]
            first_lower = first_line.lower()
            # Only check if the line has an assistant-y anchor word
            has_anchor = any(anchor in first_lower for anchor in _ASSISTANT_ANCHORS)
            if has_anchor and len(first_line) < 100:
                max_sim = max(
                    (self._ngram_similarity(first_line, ex) for ex in self._PREAMBLE_EXEMPLARS),
                    default=0.0
                )
                if max_sim > 0.35:  # 35% n-gram overlap = likely a preamble variant
                    issues["preamble"] = True
                    logger.debug(f"Fuzzy preamble detected (similarity={max_sim:.2f}): {first_line[:60]}")

        # Check for "rest remains unchanged" / truncation
        if REST_UNCHANGED_RE.search(text):
            issues["truncation_marker"] = True

        # Sneaky continuation markers (subtle truncation the model uses to cut short)
        # Only check the last 100 chars to avoid false positives from dialogue
        tail = text[-100:] if len(text) > 100 else text
        _CONTINUATION_PATTERNS = [
            r'\.\.\.\s*$',                          # trailing ellipsis
            r'\(continued\)\s*$',                    # (continued)
            r'\[continued\]\s*$',                    # [continued]
            r'(?i)to\s+be\s+continued\.?\s*$',       # To be continued
            r'\[Scene\s+continues\]',                # [Scene continues]
            r'\[Rest\s+of\s+scene[^\]]*\]',          # [Rest of scene...]
            r'(?i)and\s+so\s+(?:on|forth)\.?\s*$',   # and so on/forth
        ]
        for pat in _CONTINUATION_PATTERNS:
            if re.search(pat, tail):
                issues["continuation_marker"] = True
                break

        # Check for duplicate/alternate markers
        alt_patterns = [
            r'(?:Option [AB]|Version [12]|Alternative)',
            r'===\s*(?:EXPANDED|ENHANCED|POLISHED|REVISED)\s*(?:SCENE|VERSION)',
        ]
        for pat in alt_patterns:
            if re.search(pat, text, re.IGNORECASE):
                issues["alternate_version"] = True
                break

        # Check for analysis/commentary appended after prose
        analysis_patterns = [
            r'\n(?:Changes made|Notes?:|Summary:|Checklist:)',
            r'\n\*\*(?:Scanning|Changes|Quality)',
        ]
        for pat in analysis_patterns:
            if re.search(pat, text, re.IGNORECASE):
                issues["analysis_commentary"] = True
                break

        # Minimum content check
        word_count = count_words_accurate(text)
        if word_count < 50:
            issues["too_short"] = True

        # POV drift check (quick heuristic for first-person stories)
        writing_style = self.state.config.get("writing_style", "").lower()
        if "first person" in writing_style:
            protagonist_name = self._get_protagonist_name()
            if protagonist_name:
                third_person_refs = len(re.findall(
                    rf'\b{re.escape(protagonist_name)}\s+(?:said|thought|felt|walked|looked|smiled|laughed)',
                    text, re.IGNORECASE
                ))
                if third_person_refs >= 3:
                    issues["pov_drift"] = True

        # Prompt echo/leak detector: FORMAT_CONTRACT fragments in prose
        _PROMPT_LEAK_FINGERPRINTS = [
            "ABSOLUTE RULES",
            "Output ONLY narrative prose",
            "NEVER output:",
            "NEVER output: headings",
            "End your output with <END_PROSE>",
            "<END_PROSE>",
            "CONTINUE THE SCENE",
            "commentary, analysis",
            "bracketed stage directions",
            "truncation marker",
            "BAD (do not do this)",
            "GOOD (do this)",
        ]
        for fp in _PROMPT_LEAK_FINGERPRINTS:
            if fp in text:
                issues["prompt_leak"] = True
                logger.warning(f"Prompt leak detected: '{fp}' found in scene output")
                break

        # Dialogue integrity check: unbalanced quotes or extreme dialogue ratio
        if word_count >= 100:
            open_quotes = text.count('\u201c') + text.count('"')  # " and "
            close_quotes = text.count('\u201d') + text.count('"')  # " and "
            # For straight quotes ("), count should be even
            straight_quotes = text.count('"')
            smart_open = text.count('\u201c')
            smart_close = text.count('\u201d')
            if smart_open + smart_close > 0:
                # Smart quotes: open/close should match within tolerance
                if abs(smart_open - smart_close) > 2:
                    issues["dialogue_unbalanced"] = True
                    logger.debug(
                        f"Unbalanced smart quotes: {smart_open} open vs {smart_close} close"
                    )
            elif straight_quotes > 0 and straight_quotes % 2 != 0:
                # Odd number of straight quotes = likely unbalanced
                if straight_quotes > 3:  # Ignore single quote edge cases
                    issues["dialogue_unbalanced"] = True
                    logger.debug(f"Odd straight quote count: {straight_quotes}")

            # Dialogue ratio guard: too much or too little dialogue can indicate problems
            # Count words inside quotes as a rough dialogue ratio
            dialogue_segments = re.findall(
                r'[\u201c"]([^"\u201d]{5,})[\u201d"]', text
            )
            dialogue_words = sum(len(seg.split()) for seg in dialogue_segments)
            dialogue_ratio = dialogue_words / word_count if word_count > 0 else 0
            if dialogue_ratio > 0.85:
                issues["dialogue_ratio_high"] = True
                logger.debug(f"Dialogue ratio very high: {dialogue_ratio:.0%}")

        return {
            "pass": len(issues) == 0,
            "issues": issues,
            "word_count": word_count
        }

    def _record_artifact_metrics(self, stage_name: str, scene_meta: dict,
                                  validation: dict, is_retry: bool = False):
        """Record artifact detection metrics for diagnostics."""
        metrics = self.state.artifact_metrics

        metrics["total_scenes_generated"] += 1

        if stage_name not in metrics["per_stage"]:
            metrics["per_stage"][stage_name] = {
                "scenes": 0, "preamble": 0, "truncation": 0,
                "alternate": 0, "analysis": 0, "pov_drift": 0,
                "too_short": 0, "prompt_leak": 0, "retried": 0
            }

        sm = metrics["per_stage"][stage_name]
        sm["scenes"] += 1

        issues = validation.get("issues", {})
        if issues.get("preamble"):
            sm["preamble"] += 1
            metrics["scenes_with_preamble"] += 1
        if issues.get("truncation_marker"):
            sm["truncation"] += 1
            metrics["scenes_with_meta_text"] += 1
        if issues.get("alternate_version"):
            sm["alternate"] += 1
            metrics["scenes_with_duplicate_marker"] += 1
        if issues.get("analysis_commentary"):
            sm["analysis"] += 1
            metrics["scenes_with_meta_text"] += 1
        if issues.get("pov_drift"):
            sm["pov_drift"] += 1
            metrics["scenes_with_pov_drift"] += 1
        if issues.get("too_short"):
            sm["too_short"] += 1
        if issues.get("prompt_leak"):
            sm["prompt_leak"] = sm.get("prompt_leak", 0) + 1
            metrics["scenes_with_meta_text"] += 1
        if is_retry:
            sm["retried"] += 1
            metrics["scenes_retried"] += 1

    def _build_config_fingerprint(self) -> Dict[str, Any]:
        """Build an explainable config fingerprint for cross-run comparability.

        Stores model/provider info and content hashes of config files so
        that metric deltas can be attributed to config changes vs code changes.
        """
        import hashlib as _hl
        fingerprint: Dict[str, Any] = {}

        # Model routing info
        config = self.state.config if self.state else {}
        fingerprint["model_overrides"] = config.get("model_overrides", {})

        # LLM client info (what's actually connected)
        client_info = {}
        for name, client in (self.llm_clients or {}).items():
            model_id = getattr(client, "model", getattr(client, "model_name", "unknown"))
            client_info[name] = str(model_id)
        if self.llm_client:
            client_info["default"] = str(
                getattr(self.llm_client, "model", getattr(self.llm_client, "model_name", "unknown"))
            )
        fingerprint["clients"] = client_info

        # Content hashes of config files
        config_files = ["config.yaml", "configs/cleanup_patterns.yaml", "configs/surgical_replacements.yaml"]
        file_hashes = {}
        for rel_path in config_files:
            full_path = self.state.project_path / rel_path if "configs/" not in rel_path else (
                Path(__file__).parent.parent / rel_path
            )
            if full_path.exists():
                try:
                    content = full_path.read_text(encoding="utf-8")
                    file_hashes[rel_path] = _hl.sha256(content.encode()).hexdigest()[:12]
                except Exception:
                    file_hashes[rel_path] = "read_error"
        fingerprint["config_hashes"] = file_hashes

        return fingerprint

    def _persist_artifact_metrics(self):
        """Save artifact metrics to cross-run history file (JSONL).

        Each line is a JSON object with run_nonce, timestamp, config
        fingerprint, and metrics. Enables trend analysis across runs.
        """
        import datetime
        history_path = self.state.project_path / "artifact_metrics_history.jsonl"
        # Compute defense cost ratio
        gen_tok = self._budget_tracker.get("generation_tokens", 0)
        def_tok = self._budget_tracker.get("defense_tokens", 0)
        total_tok = gen_tok + def_tok
        defense_ratio = round(def_tok / total_tok, 4) if total_tok > 0 else 0.0
        max_ratio = self._get_threshold("budget_max_defense_ratio")
        if defense_ratio > max_ratio:
            logger.warning(
                f"BUDGET GUARD: defense cost ratio {defense_ratio:.1%} exceeds limit "
                f"{max_ratio:.0%} (defense={def_tok}, generation={gen_tok})"
            )

        entry = {
            "run_nonce": self._run_nonce,
            "timestamp": datetime.datetime.now().isoformat(),
            "config_fingerprint": self._build_config_fingerprint(),
            "metrics": self.state.artifact_metrics,
            "budget": {
                "defense_tokens": def_tok,
                "generation_tokens": gen_tok,
                "defense_cost_ratio": defense_ratio,
                "retries_per_stage": dict(self._budget_tracker.get("retries_per_stage", {})),
                "rewritten_scenes": self._budget_tracker.get("rewritten_scenes", 0),
            },
        }
        try:
            with open(history_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            logger.info(f"Artifact metrics persisted to {history_path}")
        except Exception as e:
            logger.warning(f"Failed to persist artifact metrics: {e}")

    def _compute_metrics_delta(self) -> Optional[Dict[str, Any]]:
        """Compare current run metrics against the previous run.

        Returns a delta dict showing improvement/regression per metric,
        or None if no prior run exists.
        """
        history_path = self.state.project_path / "artifact_metrics_history.jsonl"
        if not history_path.exists():
            return None

        try:
            lines = history_path.read_text(encoding="utf-8").strip().split("\n")
            # Need at least 2 entries (previous + current)
            if len(lines) < 2:
                return None

            prev = json.loads(lines[-2])["metrics"]
            curr = self.state.artifact_metrics

            delta = {}
            for key in ["total_scenes_generated", "scenes_with_meta_text",
                         "scenes_with_preamble", "scenes_with_duplicate_marker",
                         "scenes_with_pov_drift", "scenes_retried"]:
                prev_val = prev.get(key, 0)
                curr_val = curr.get(key, 0)
                if prev_val != curr_val:
                    direction = "improved" if curr_val < prev_val else "regressed"
                    # For total_scenes_generated, more is neutral not regression
                    if key == "total_scenes_generated":
                        direction = "changed"
                    delta[key] = {
                        "previous": prev_val,
                        "current": curr_val,
                        "change": curr_val - prev_val,
                        "direction": direction,
                    }

            if delta:
                logger.info(f"Metrics delta vs previous run: {json.dumps(delta, indent=2)}")

            # Model drift alarm: if preamble or forbidden marker rate jumped significantly
            drift_keys = ["scenes_with_preamble", "scenes_with_meta_text"]
            for dk in drift_keys:
                if dk in delta and delta[dk]["direction"] == "regressed":
                    prev_v = delta[dk]["previous"]
                    curr_v = delta[dk]["current"]
                    # Alarm if absolute increase > 3 AND relative increase > 50%
                    if curr_v - prev_v > 3 and prev_v > 0 and curr_v / prev_v > 1.5:
                        fp = self._build_config_fingerprint()
                        logger.error(
                            f"MODEL DRIFT ALARM: {dk} jumped {prev_v}->{curr_v} "
                            f"(+{curr_v - prev_v}). "
                            f"Run nonce: {self._run_nonce}, "
                            f"Models: {fp.get('clients', {})}, "
                            f"Config hashes: {fp.get('config_hashes', {})}. "
                            f"Consider lowering temperature or checking model version."
                        )

            return delta if delta else None
        except Exception as e:
            logger.warning(f"Failed to compute metrics delta: {e}")
            return None

    async def _generate_prose(self, client, prompt: str, stage_name: str,
                               scene_meta: dict = None, **kwargs) -> tuple:
        """Generate prose with format contract, stop sequences, critic gate, and metrics.

        Centralizes the generate → validate → retry → postprocess pipeline.
        Returns (processed_content: str, tokens_used: int).
        """
        # Inject format contract as system prompt (stage can override)
        # Uses per-run nonce sentinel to avoid cross-run collisions
        kwargs.setdefault('system_prompt', self._format_contract)

        # Add stop sequences for creative stages (nonce sentinel + backups)
        kwargs.setdefault('stop', self._stop_sequences)

        # Generate
        response = await client.generate(prompt, **kwargs)
        total_tokens = response.input_tokens + response.output_tokens
        self._budget_tracker["generation_tokens"] += response.input_tokens + response.output_tokens

        # Run critic gate on raw output
        validation = self._validate_scene_output(response.content, scene_meta)
        self._record_artifact_metrics(stage_name, scene_meta or {}, validation)

        # If critic gate fails on fixable issues, retry once with issue-specific feedback
        fixable_issues = {"preamble", "truncation_marker", "alternate_version", "analysis_commentary", "prompt_leak"}
        detected = set(validation.get("issues", {}).keys())

        # Budget guard: check retry budget before attempting
        stage_retries = self._budget_tracker["retries_per_stage"].get(stage_name, 0)
        max_retries = int(self._get_threshold("budget_max_retries_per_stage"))
        budget_allows_retry = stage_retries < max_retries

        if not validation["pass"] and detected & fixable_issues and budget_allows_retry:
            # Track retry in budget
            self._budget_tracker["retries_per_stage"][stage_name] = stage_retries + 1

            # Build targeted feedback telling the model exactly what went wrong
            specific_feedback = []
            for issue in detected & fixable_issues:
                if issue in ISSUE_SPECIFIC_FEEDBACK:
                    specific_feedback.append(ISSUE_SPECIFIC_FEEDBACK[issue])
            feedback_str = "\n".join(specific_feedback) if specific_feedback else STRICT_RETRY_PREFIX

            logger.warning(
                f"Critic gate failed for {stage_name} "
                f"({', '.join(detected)}). Retrying with issue-specific feedback. "
                f"(retry {stage_retries + 1}/{max_retries})"
            )
            strict_kwargs = dict(kwargs)
            strict_kwargs['system_prompt'] = self._format_contract + "\n" + feedback_str + "\n"
            response2 = await client.generate(prompt, **strict_kwargs)
            retry_tokens = response2.input_tokens + response2.output_tokens
            total_tokens += retry_tokens
            self._budget_tracker["defense_tokens"] += retry_tokens

            validation2 = self._validate_scene_output(response2.content, scene_meta)
            self._record_artifact_metrics(stage_name, scene_meta or {}, validation2, is_retry=True)

            # Score both outputs: hard penalties for artifacts, soft bonuses for quality
            def _score_output(val, content):
                score = 0
                issues = val.get("issues", {})
                # Hard penalties (artifacts that ruin the output)
                score -= 100 * len({"preamble", "truncation_marker", "alternate_version",
                                     "analysis_commentary", "prompt_leak"} & set(issues.keys()))
                # Soft penalties
                if issues.get("too_short"):
                    score -= 30
                if issues.get("pov_drift"):
                    score -= 20
                # Quality bonuses
                wc = val.get("word_count", 0)
                if wc >= 200:
                    score += min(wc / 50, 20)  # Up to +20 for good length
                return score

            score1 = _score_output(validation, response.content)
            score2 = _score_output(validation2, response2.content)
            if score2 > score1:
                response = response2
        elif not validation["pass"] and detected & fixable_issues and not budget_allows_retry:
            logger.warning(
                f"BUDGET GUARD: retry budget exhausted for {stage_name} "
                f"({stage_retries}/{max_retries} retries used). "
                f"Accepting output with issues: {', '.join(detected)}"
            )

        # Postprocess (cleanup + POV + de-AI + tic limiting)
        # Extract per-scene POV character for dual-POV support
        pov_character = (scene_meta or {}).get("pov", "")
        processed = self._postprocess(response.content, pov_character=pov_character)

        # Prose integrity checksums: hash at raw and clean stages
        import hashlib as _hl
        raw_hash = _hl.sha256((response.content or "").encode()).hexdigest()[:12]
        clean_hash = _hl.sha256((processed or "").encode()).hexdigest()[:12]
        if scene_meta:
            scene_meta["content_hash_raw"] = raw_hash
            scene_meta["content_hash_clean"] = clean_hash
            if raw_hash != clean_hash:
                logger.debug(
                    f"Prose integrity: {stage_name} raw={raw_hash} clean={clean_hash} "
                    f"(postprocessing changed content)"
                )

        return processed, total_tokens

    # Allowed keys in assembled context — anything else is a bug
    _CONTEXT_ALLOWED_SECTIONS = {
        "WRITING STYLE", "TONE", "AVOID", "STORY STATE", "PREVIOUS SCENE ENDING",
    }

    def _build_scene_context(self, scene_index: int, scenes: list = None,
                              include_story_state: bool = True,
                              include_previous: int = 2) -> str:
        """Single approved entry point for scene context assembly.

        Context hygiene rules:
        - ONLY pulls from current project's state (self.state)
        - Sources: style constraints, story state (facts), previous scene tails
        - NEVER injects: other project data, old candidates, debug text, explanations
        - Schema validation: assembled context is checked for unexpected sections
        """
        scenes = scenes or self.state.scenes or []
        config = self.state.config
        parts = []

        # Style constraints (always included)
        parts.append(f"WRITING STYLE: {config.get('writing_style', 'literary prose')}")
        parts.append(f"TONE: {config.get('tone', '')}")
        if config.get("avoid"):
            parts.append(f"AVOID: {config.get('avoid')}")

        # Story state — facts already established (prevents contradiction/loops)
        if include_story_state and scenes and scene_index > 0:
            current_scene = scenes[scene_index] if scene_index < len(scenes) else {}
            story_state = self._build_story_state(
                scenes[:scene_index],
                current_chapter=current_scene.get("chapter", 1),
                current_scene=current_scene.get("scene_number", 1)
            )
            if story_state:
                parts.append(f"\n{story_state}")

        # Previous scene tail — transition continuity
        # Wrapped in containment boundary to prevent scene content from being
        # interpreted as instructions (defense against prompt injection via content)
        if include_previous > 0 and scenes and scene_index > 0:
            prev_scenes = scenes[max(0, scene_index - include_previous):scene_index]
            prev_context = self._get_previous_scenes_context(prev_scenes, count=include_previous)
            if prev_context:
                parts.append(
                    f"\n<user_content_boundary>"
                    f"\nPREVIOUS SCENE ENDING:\n{prev_context}"
                    f"\n</user_content_boundary>"
                )

        # Periodic alignment check: warn if scenes are drifting from beat sheet
        alignment_warning = self._check_alignment(scene_index)
        if alignment_warning:
            parts.append(f"\n{alignment_warning}")

        result = "\n".join(parts)

        # Schema validation: check that no unexpected data leaked into context
        self._validate_context_schema(result, scene_index)

        # Context hashing + origin stamps for traceability
        import hashlib
        ctx_hash = hashlib.sha256(result.encode("utf-8")).hexdigest()[:12]
        origins = [p.split(":")[0].split("\n")[-1].strip() for p in parts if p.strip()]
        logger.debug(
            f"Context for scene {scene_index}: hash={ctx_hash}, "
            f"origins=[{', '.join(origins[:6])}], len={len(result)} chars"
        )

        return result

    def _validate_context_schema(self, context: str, scene_index: int):
        """Runtime check that assembled context only contains expected sections.

        Catches accidental injection of debug data, other project state, or
        prompt fragments that shouldn't be in scene context.
        """
        # Check for suspicious content that should never be in scene context
        red_flags = [
            (r'(?i)\b(?:api[_-]?key|secret|password|token)\s*[:=]', "credential leak"),
            (r'(?i)\bdef\s+\w+\s*\(', "Python code in context"),
            (r'(?i)\bclass\s+\w+\s*[:(]', "Python class in context"),
            (r'(?m)^\s*(?:import\s+\w+|from\s+\w+\s+import\b)', "Python import statement in context"),
            (r'\{\{.*?\}\}', "template placeholder in context"),
            (r'(?i)(?:TODO|FIXME|HACK|XXX):', "debug marker in context"),
        ]
        for pattern, description in red_flags:
            if re.search(pattern, context):
                logger.warning(
                    f"Context schema violation at scene {scene_index}: {description}. "
                    f"Context may contain injected data."
                )

        # Two-factor prompt injection detection: requires BOTH an injection phrase
        # AND a structural cue to avoid false-positives on villain dialogue
        _INJECTION_PHRASES = [
            r'(?i)ignore (?:all )?previous (?:instructions|prompts|rules)',
            r'(?i)(?:you are|act as|pretend to be) (?:a |an )?(?:different|new|helpful)',
            r'(?i)(?:system|admin|root)\s*(?:prompt|override|access)',
            r'(?i)disregard (?:all |any )?(?:above|prior|previous)',
            r'(?i)(?:forget|reset) (?:everything|all|your) (?:instructions|rules|context)',
        ]
        _STRUCTURAL_CUES = [
            r'(?i)\bsystem\s*:', r'(?i)\bassistant\s*:', r'(?i)\brole\s*=',
            r'(?i)###\s*instructions', r'(?i)</?(?:system|instructions|prompt)>',
            r'(?i)\[INST\]', r'(?i)\bBEGIN\s+INSTRUCTION',
        ]
        has_phrase = any(re.search(p, context) for p in _INJECTION_PHRASES)
        has_cue = any(re.search(c, context) for c in _STRUCTURAL_CUES)
        if has_phrase and has_cue:
            logger.error(
                f"HIGH-CONFIDENCE prompt injection at scene {scene_index}: "
                f"injection phrase + structural cue both present."
            )
            _log_incident(f"scene_{scene_index}", "prompt_injection",
                          "High-confidence injection: phrase + structural cue",
                          severity="critical", failure_type="content")
        elif has_phrase:
            logger.warning(
                f"Possible prompt injection at scene {scene_index} "
                f"(phrase match only, no structural cue — may be dialogue)."
            )

    def _log_artifact_summary(self, stage_name: str):
        """Log artifact metrics summary for a completed stage."""
        sm = self.state.artifact_metrics.get("per_stage", {}).get(stage_name)
        if not sm or sm["scenes"] == 0:
            return
        issues_count = sum(v for k, v in sm.items() if k not in ("scenes", "retried"))
        if issues_count > 0:
            logger.info(
                f"Artifact metrics for {stage_name}: {sm['scenes']} scenes, "
                f"{issues_count} issues detected "
                f"(preamble={sm['preamble']}, truncation={sm['truncation']}, "
                f"alternate={sm['alternate']}, analysis={sm['analysis']}, "
                f"pov_drift={sm['pov_drift']}), {sm['retried']} retried"
            )

    def _get_previous_scenes_context(self, scenes: List[Dict], count: int = 2) -> str:
        """Get the ending of the most recent scenes for seamless transitions.

        Instead of dumping 500 raw chars, gives the LAST 2 paragraphs of recent
        scenes — which is what the AI needs to write a seamless continuation.
        """
        if not scenes or len(scenes) == 0:
            return "This is the opening scene."

        recent = scenes[-count:] if len(scenes) >= count else scenes
        summaries = []
        for s in recent:
            if not isinstance(s, dict):
                continue
            ch = s.get("chapter", "?")
            sc = s.get("scene_number", "?")
            loc = s.get("location", "unknown")
            content = s.get("content", "")
            # Get last 2 paragraphs (the transition point)
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            ending = "\n\n".join(paragraphs[-2:]) if len(paragraphs) >= 2 else content[-400:]
            # Truncate if still too long
            if len(ending) > 500:
                ending = ending[-500:]
            summaries.append(f"[Ch{ch} Sc{sc}, Location: {loc}] ENDING:\n{ending}")

        return "PREVIOUS SCENE ENDINGS (continue seamlessly from here):\n" + "\n\n".join(summaries)

    def _check_alignment(self, scene_index: int, check_interval: int = 5) -> Optional[str]:
        """Periodic alignment check: compare recent scenes against beat sheet.

        Runs every `check_interval` scenes. Returns a warning string if scenes
        are drifting from the planned beat sheet, or None if aligned.

        This catches gradual drift: tone shifts, unauthorized subplots,
        character trait escalation beyond what was outlined.
        """
        # Only check at intervals (every N scenes)
        if scene_index == 0 or scene_index % check_interval != 0:
            return None

        scenes = self.state.scenes or []
        beat_sheet = getattr(self.state, 'beat_sheet', None)
        outline = self.state.master_outline or []

        if not scenes or not outline:
            return None

        # Get the last `check_interval` scenes' content
        recent_start = max(0, scene_index - check_interval)
        recent_scenes = scenes[recent_start:scene_index]
        recent_text = " ".join(
            s.get("content", "")[:300] for s in recent_scenes if isinstance(s, dict)
        )

        if not recent_text or len(recent_text) < 100:
            return None

        # Build expected content from outline for these scenes
        expected_parts = []
        for s in recent_scenes:
            if not isinstance(s, dict):
                continue
            ch = s.get("chapter", 0)
            sn = s.get("scene_number", 0)
            # Find matching outline entry
            for ch_outline in outline:
                if ch_outline.get("chapter") == ch:
                    for scene_outline in ch_outline.get("scenes", []):
                        if scene_outline.get("scene") == sn:
                            expected_parts.append(
                                f"{scene_outline.get('purpose', '')} "
                                f"{scene_outline.get('scene_name', '')}"
                            )

        if not expected_parts:
            return None

        expected_text = " ".join(expected_parts)

        # Compare using bigram overlap (lightweight, no dependencies)
        recent_words = recent_text.lower().split()
        expected_words = expected_text.lower().split()

        # Extract key nouns/verbs from expected (skip common words)
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "and", "or",
                      "to", "in", "of", "for", "with", "on", "at", "by", "from",
                      "that", "this", "it", "he", "she", "they", "his", "her"}
        expected_keywords = {w for w in expected_words if w not in stop_words and len(w) > 2}
        recent_set = set(recent_words)

        if not expected_keywords:
            return None

        # Check what fraction of expected keywords appear in recent scenes
        found = expected_keywords & recent_set
        coverage = len(found) / len(expected_keywords) if expected_keywords else 1.0

        if coverage < 0.15:  # Less than 15% keyword overlap = significant drift
            missing = expected_keywords - found
            warning = (
                f"ALIGNMENT WARNING (scenes {recent_start+1}-{scene_index}): "
                f"Only {coverage:.0%} keyword overlap with outline. "
                f"Missing expected elements: {', '.join(list(missing)[:8])}. "
                f"Scenes may be drifting from planned beat sheet."
            )
            logger.warning(warning)
            return warning

        return None

    def _build_story_state(self, scenes: List[Dict], current_chapter: int, current_scene: int) -> str:
        """Build structured story state for continuity injection.

        This is the #1 fix for the 'first meeting loop' and 'hallucinated locations'
        problems. By injecting a compact state of what has ALREADY happened, the AI
        cannot re-do earlier beats or invent contradictory facts.

        Uses OUTLINE data (not generated text) for reliability.
        """
        outline = self.state.master_outline or []
        config = self.state.config
        lines = []

        # 1. Story progress — where we are in the overall structure
        total_chapters = len([ch for ch in outline if isinstance(ch, dict)])
        total_scenes = sum(
            len(ch.get("scenes", []))
            for ch in outline if isinstance(ch, dict)
        )
        scenes_written = len(scenes)
        lines.append(f"STORY PROGRESS: Writing scene {scenes_written + 1} of ~{total_scenes}. "
                      f"Chapter {current_chapter} of {total_chapters}.")

        # 2. Completed chapters — one-liner from outline (NOT from generated text)
        completed = []
        for ch in outline:
            if not isinstance(ch, dict):
                continue
            ch_num = ch.get("chapter", 0)
            if ch_num < current_chapter:
                ch_title = ch.get("chapter_title", f"Chapter {ch_num}")
                scene_purposes = [
                    s.get("purpose", "")
                    for s in ch.get("scenes", [])
                    if isinstance(s, dict) and s.get("purpose")
                ]
                summary = "; ".join(scene_purposes[:3])
                if len(summary) > 200:
                    summary = summary[:200] + "..."
                completed.append(f"  Ch{ch_num} \"{ch_title}\": {summary}")

        if completed:
            lines.append("")
            lines.append("COMPLETED CHAPTERS (these events ALREADY HAPPENED — do NOT redo them):")
            # Show all completed chapters, but compress if too many
            if len(completed) > 10:
                lines.extend(completed[:5])
                lines.append(f"  ... ({len(completed) - 10} chapters omitted) ...")
                lines.extend(completed[-5:])
            else:
                lines.extend(completed)

        # 3. Current chapter — what's done vs upcoming
        current_ch = next(
            (ch for ch in outline if isinstance(ch, dict) and ch.get("chapter") == current_chapter),
            None
        )
        if current_ch:
            ch_title = current_ch.get("chapter_title", "")
            ch_scenes = current_ch.get("scenes", [])
            lines.append(f"")
            lines.append(f"CURRENT CHAPTER {current_chapter} \"{ch_title}\":")
            for s in ch_scenes:
                if not isinstance(s, dict):
                    continue
                s_num = s.get("scene", s.get("scene_number", 0))
                purpose = s.get("purpose", f"Scene {s_num}")
                loc = s.get("location", "")
                if s_num < current_scene:
                    lines.append(f"  Scene {s_num}: {purpose} @ {loc} [DONE]")
                elif s_num == current_scene:
                    lines.append(f"  Scene {s_num}: {purpose} @ {loc} [WRITING NOW <<<]")
                else:
                    lines.append(f"  Scene {s_num}: {purpose} @ {loc} [upcoming]")

        # 4. Location tracking — prevent coffee shop singularity
        loc_counts: Dict[str, int] = {}
        for s in scenes:
            if isinstance(s, dict):
                loc = s.get("location", "")
                if loc:
                    loc_counts[loc] = loc_counts.get(loc, 0) + 1

        recent_locs = []
        for s in scenes[-5:]:
            if isinstance(s, dict) and s.get("location"):
                recent_locs.append(s["location"])

        if recent_locs:
            lines.append(f"")
            lines.append(f"RECENT LOCATIONS (last {len(recent_locs)} scenes): {', '.join(recent_locs)}")
            overused = [f'"{loc}" ({c}x)' for loc, c in loc_counts.items() if c >= 3]
            if overused:
                lines.append(f"OVERUSED — pick a DIFFERENT location: {', '.join(overused)}")

        # 5. Relationship / story-arc state based on progress percentage
        if total_scenes > 0:
            progress_pct = scenes_written / total_scenes * 100
            genre = config.get("genre", "").lower()
            if "romance" in genre:
                if progress_pct < 15:
                    rel_state = "FIRST MEETING phase. Characters are strangers discovering each other."
                elif progress_pct < 30:
                    rel_state = "EARLY CONNECTION. Characters have met and are building rapport. Past first introductions."
                elif progress_pct < 50:
                    rel_state = "DEEPENING BOND. Characters know each other well. Relationship is established and growing."
                elif progress_pct < 70:
                    rel_state = "COMPLICATIONS/STRAIN. Relationship being tested. Real challenges emerging."
                elif progress_pct < 85:
                    rel_state = "CRISIS/DARK MOMENT. Major obstacle or separation threatening the relationship."
                else:
                    rel_state = "RESOLUTION. Characters confronting their fears. Moving toward commitment or acceptance."
            else:
                if progress_pct < 25:
                    rel_state = "ACT 1 — Setup and inciting incident."
                elif progress_pct < 50:
                    rel_state = "ACT 2A — Rising action, complications building."
                elif progress_pct < 75:
                    rel_state = "ACT 2B — Midpoint crossed, stakes escalating."
                else:
                    rel_state = "ACT 3 — Climax and resolution."
            lines.append(f"")
            lines.append(f"NARRATIVE ARC: {rel_state}")

        # 6. Critical continuity warnings based on common AI failures
        if scenes_written > 0:
            lines.append(f"")
            lines.append("CRITICAL CONTINUITY RULES:")
            lines.append("- Characters have ALREADY MET. Do NOT write a first meeting.")
            lines.append("- Do NOT re-introduce characters the narrator already knows.")
            lines.append("- The narrator's location/situation must match the outline above.")
            if scenes_written > 5:
                lines.append("- Do NOT default to a coffee shop/café unless the outline specifies one.")

        return "\n".join(lines)

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

        # Pre-serialize large objects once (avoid re-serializing per scene)
        _characters_json = json.dumps(self.state.characters, indent=2) if self.state.characters else ''
        _world_bible_json = json.dumps(self.state.world_bible, indent=2) if self.state.world_bible else ''

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
            chapter_num = int(chapter.get("chapter", 1))

            for scene_info in chapter.get("scenes", []):
                if not isinstance(scene_info, dict):
                    continue
                scene_num = int(scene_info.get("scene", scene_info.get("scene_number", 1)))
                stable_id = scene_info.get("scene_id", f"ch{chapter_num:02d}_s{scene_num:02d}")
                pov_char = scene_info.get("pov", "protagonist")
                try:
                    spice_level = int(scene_info.get("spice_level", 0))
                except (ValueError, TypeError):
                    spice_level = 0
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
                try:
                    tension_level = int(scene_info.get('tension_level', 5))
                except (ValueError, TypeError):
                    tension_level = 5
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

                # Build voice modifier block (wolf voice, etc.) if applicable
                voice_modifiers = self._build_voice_modifiers_block(pov_char, chapter_num)

                prompt = f"""Write Chapter {chapter_num}, Scene {scene_num}: "{scene_name}"
POSITION: Scene {scene_position + 1} of {total_scenes_in_chapter} in this chapter.
YOU ARE {pov_char.upper()}. You are writing AS {pov_char}, in first person. "I" = {pov_char}.

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
Every sentence must be filtered through {pov_char}'s voice.
- "I" = ONLY {pov_char}. Other characters are "she/he/they".
- "my" = ONLY {pov_char}'s body/voice/face. Other characters' = "her/his/their".
- Character tics should appear at most ONCE per scene (not every paragraph)

CRITICAL POV ERRORS TO AVOID (the AI makes these constantly):
WRONG: "she whispered, my voice barely audible" — "my voice" is wrong, it's HER voice
WRONG: "She rolled my eyes" — she rolled HER eyes, not mine
WRONG: "I smiled warmly, gazing at me" — this is nonsensical, should be "She smiled"
WRONG: "she said, my eyes sparkling" — HER eyes are sparkling, not mine
WRONG: "I turned to face me" — should be "She turned to face me"
RIGHT: "she whispered, her voice barely audible"
RIGHT: "She rolled her eyes"
RIGHT: "She smiled warmly, gazing at me"
When "she" does something, everything in that clause (voice, eyes, face, lips, hands)
belongs to HER, not to "my".

=== DIALOGUE RULES ===
- Every dialogue tag MUST have a subject: "I said" or "she said" — NEVER just "said softly"
- {pov_char} and other characters must sound DIFFERENT:
  - Give each character distinct speech patterns, vocabulary, and sentence length
  - The love interest should have culturally specific expressions or syntax
  - Characters should NOT speak in identical therapeutic-affirmation register
  - Real people interrupt, use slang, trail off, repeat themselves, dodge questions
{voice_modifiers}
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
{_characters_json}
{f"ADDITIONAL CHARACTERS: {extra_chars}" if extra_chars else ""}

{f"=== CULTURAL AUTHENTICITY ==={chr(10)}{cultural_notes}" if cultural_notes else ""}

=== STORY STATE (what has happened so far — READ THIS CAREFULLY) ===
{self._build_story_state(scenes, chapter_num, scene_num)}

=== CONTINUITY (previous scene endings — continue from here) ===
{previous_context}

{self._get_used_details_tracker(scenes)}

=== TARGET LENGTH ===
Approximately {self.state.words_per_scene} words.
Paragraphs: 4 sentences maximum (mobile-optimized).
You must reach at least {int(self.state.words_per_scene * 0.7)} words before concluding.
Do NOT end the scene until the scene turn has occurred.

=== NOW WRITE ===
REMINDER: You are {pov_char}. "I" = {pov_char}. Write every sentence from inside {pov_char}'s head.
If {pov_char} is mentioned by name in the narrative, something is WRONG — {pov_char} would say "I", not their own name.
Begin DIRECTLY with narrative—no preamble, no title, no scene heading.
- FIRST PERSON ONLY. Every line = "I" perspective. Never third person.
- Open with ACTION or DIALOGUE (not description, not atmosphere)
- Hook immediately with tension, motion, or intrigue
- Ground us in {pov_char}'s physical state through what {pov_char} DOES
- Each paragraph must advance the scene (no restatements)
- NEVER end a paragraph by summarizing what the moment means emotionally.
  End on action, dialogue, or sensory observation. Let the reader interpret.
- Character catchphrases/tics: use at most ONCE in this scene.
- MINIMUM DIALOGUE: at least 4 lines of quoted dialogue ("..."). Spread across the scene.
  At least 1 quoted line must appear in the final 25% of the scene.
  Dialogue advances the scene — it must reveal, challenge, or shift the dynamic.
{"- Include italic inner voice (*thoughts*) as instructed above." if voice_modifiers else ""}

Write the complete scene as {pov_char} ("I"):"""

                # Context safety: validate the inline-assembled prompt for
                # credential leaks, injection attempts, and template placeholders.
                # Scene drafting builds context inline (not via _build_scene_context),
                # so we must explicitly run schema validation here.
                self._validate_context_schema(prompt, len(scenes))

                if client:
                    # Calculate max tokens based on target words (1 token ≈ 1.2-1.4 words)
                    # Use 2.5x multiplier for buffer and comprehensive scenes.
                    # Config stage_max_tokens.scene_drafting overrides (e.g. paid models).
                    computed = max(int(self.state.words_per_scene * 2.5), 2500)
                    max_tokens = self.get_max_tokens_for_stage("scene_drafting", computed)
                    temp = self.get_temperature_for_stage("scene_drafting")
                    content, tokens = await self._generate_prose(
                        client, prompt, "scene_drafting",
                        scene_meta={"chapter": chapter_num, "scene": scene_num, "pov": pov_char},
                        max_tokens=max_tokens, temperature=temp)
                    scenes.append({
                        "chapter": chapter_num,
                        "scene_number": scene_num,
                        "scene_id": stable_id,
                        "pov": pov_char,
                        "location": location,
                        "spice_level": spice_level,
                        "content": content
                    })
                    total_tokens += tokens
                else:
                    scenes.append({
                        "chapter": chapter_num,
                        "scene_number": scene_num,
                        "scene_id": stable_id,
                        "pov": pov_char,
                        "content": f"[Scene content for chapter {chapter_num}, scene {scene_num}]"
                    })
                    total_tokens += 100

                # Log progress
                logger.info(f"Drafted Chapter {chapter_num}, Scene {scene_num} ({len(scenes)} total)")

        # Post-draft micro-passes: dialogue drought, AI-tell scrub, scene-turn repair,
        # and dedup tail regeneration. These run on every scene after initial drafting.
        scenes, micro_tokens = await self._post_draft_micro_passes(scenes)
        total_tokens += micro_tokens

        self.state.scenes = scenes
        return scenes, total_tokens

    # ========================================================================
    # Post-Draft Micro-Passes
    # ========================================================================

    async def _post_draft_micro_passes(self, scenes: list) -> tuple:
        """Run quality micro-passes on drafted scenes.

        Returns (updated_scenes, tokens_used).
        Passes run in order:
          1. Semantic dedup tail regeneration (scenes truncated by dedup)
          2. Dialogue drought guard (min 3 dialogue lines)
          3. AI-tell scrub (remove AI-tell phrases)
          4. Scene-turn repair (ensure scene ends with a turn)
        """
        client = self.get_client_for_stage("scene_drafting")
        if not client:
            return scenes, 0

        total_tokens = 0
        updated = []

        for scene in scenes:
            content = scene.get("content", "")
            sid = scene.get("scene_id",
                            f"ch{int(scene.get('chapter', 0)):02d}_s{int(scene.get('scene_number', 0)):02d}")
            pov = scene.get("pov", "protagonist")

            if not content or len(content.strip()) < 200:
                updated.append(scene)
                continue

            scene_tokens = 0

            # Wrap all 4 micro-passes in a per-scene timeout guard (15 min).
            # Belt-and-suspenders: individual generate() calls have 300s timeouts,
            # but asyncio cancellation on Windows can be unreliable.
            try:
                async def _run_micro_passes():
                    nonlocal content
                    _tokens = 0

                    # Pass 1: Dedup tail regeneration
                    if "[DEDUP_TAIL_TRUNCATED]" in content:
                        content, t = await self._micro_regen_dedup_tail(
                            client, content, scene, sid, pov)
                        _tokens += t

                    # Pass 2: Dialogue drought guard
                    content, t = await self._micro_dialogue_drought(
                        client, content, scene, sid, pov)
                    _tokens += t

                    # Pass 3: AI-tell scrub
                    content, t = await self._micro_ai_tell_scrub(
                        client, content, scene, sid, pov)
                    _tokens += t

                    # Pass 4: Scene-turn repair
                    content, t = await self._micro_scene_turn_repair(
                        client, content, scene, sid, pov)
                    _tokens += t

                    # Pass 5: Wolf voice seed (LAST — after all rewrites to prevent overwrites)
                    content, t = await self._micro_wolf_voice_seed(
                        client, content, scene, sid, pov)
                    _tokens += t
                    return _tokens

                scene_tokens = await asyncio.wait_for(_run_micro_passes(), timeout=900)
            except Exception as e:
                logger.warning(f"Micro-pass timeout/error for {sid}: {type(e).__name__}: {e}")

            # Safety: ensure no sentinel markers survive into stored content
            content = content.replace("[DEDUP_TAIL_TRUNCATED]", "").strip()
            scene["content"] = content
            total_tokens += scene_tokens
            updated.append(scene)

        if total_tokens > 0:
            logger.info(f"Post-draft micro-passes: {total_tokens} tokens across {len(updated)} scenes")

        return updated, total_tokens

    async def _micro_regen_dedup_tail(self, client, content: str, scene: dict,
                                       sid: str, pov: str) -> tuple:
        """Regenerate tail paragraphs that were truncated by semantic dedup.

        Instead of accepting a truncated scene, generates new concluding
        paragraphs with a 'new beat' constraint to avoid repeating the
        content that triggered dedup.
        """
        content = content.replace("\n\n[DEDUP_TAIL_TRUNCATED]", "").strip()

        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if len(paragraphs) < 2:
            return content, 0

        target_paras = max(3, len(paragraphs) // 3)

        prompt = f"""Continue this scene with {target_paras} NEW paragraphs.
The scene was building toward its climax but the ending was repetitive and has been removed.

=== CRITICAL: NEW BEAT CONSTRAINT ===
The continuation must introduce a NEW development — NOT restate what already happened.
Options: a reveal, a reversal, a decision, an interruption, a physical action.
Do NOT echo the emotional state or situation from the existing paragraphs.

=== POV LOCK ===
FIRST PERSON ("I") — {pov}'s POV. Maintain the exact same voice and style.

=== EXISTING SCENE (continue from here) ===
{content}

=== NOW CONTINUE ===
Write {target_paras} new paragraphs that advance the scene to its conclusion.
Include a scene turn (something changes, someone decides, a truth emerges).
End on action or dialogue, not reflection."""

        try:
            response = await client.generate(
                prompt, max_tokens=1500, temperature=0.6,
                system_prompt=self._format_contract,
                stop=self._stop_sequences, timeout=300)
            tokens = response.input_tokens + response.output_tokens

            new_tail = self._postprocess(response.content, pov_character=pov)
            if new_tail and len(new_tail.strip()) > 100:
                content = content + "\n\n" + new_tail.strip()
                logger.info(f"Dedup tail regen for {sid}: added {len(new_tail.split())} words")

            return content, tokens
        except Exception as e:
            logger.warning(f"Dedup tail regen failed for {sid}: {e}")
            return content, 0

    async def _micro_dialogue_drought(self, client, content: str, scene: dict,
                                       sid: str, pov: str) -> tuple:
        """Surgically insert dialogue into scenes that lack it.

        Instead of rewriting the whole scene (which causes word-count loss),
        identifies 2-3 anchor points in the existing prose and asks the model
        to insert short dialogue exchanges at those points only.
        """
        MIN_DIALOGUE_LINES = 3

        dialogue_lines = len(re.findall(r'"[^"]{5,}"', content))
        if dialogue_lines >= MIN_DIALOGUE_LINES:
            return content, 0

        logger.info(f"Dialogue drought in {sid}: {dialogue_lines} lines (min {MIN_DIALOGUE_LINES})")

        # Find insertion anchors: paragraphs with interaction cues
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if len(paragraphs) < 3:
            return content, 0

        # Build annotated scene with [KEEP] / [INSERT DIALOGUE HERE] markers
        interaction_cues = re.compile(
            r'\b(looked at|turned to|faced|glanced|stared|nodded|shook|'
            r'stepped|moved toward|reached|grabbed|touched|voice|spoke|'
            r'whispered|mouth|lips|jaw|throat|eyes met)\b', re.IGNORECASE)

        anchors = []
        for i, para in enumerate(paragraphs):
            if interaction_cues.search(para) and i > 0:
                anchors.append(i)

        # If no interaction cues, pick paragraph before final 2 + midpoint
        if not anchors:
            mid = len(paragraphs) // 2
            anchors = [mid, max(mid + 1, len(paragraphs) - 3)]

        # Limit to 3 anchors, spread across the scene
        anchors = sorted(set(anchors))[:3]
        needed = max(MIN_DIALOGUE_LINES - dialogue_lines + 1, 3)

        # Build the annotated scene
        annotated_parts = []
        for i, para in enumerate(paragraphs):
            if i in anchors:
                annotated_parts.append(f"[INSERT DIALOGUE AFTER THIS PARAGRAPH]\n{para}")
            else:
                annotated_parts.append(f"[KEEP VERBATIM]\n{para}")

        annotated_scene = '\n\n'.join(annotated_parts)

        prompt = f"""This scene has only {dialogue_lines} dialogue lines. Insert dialogue at the marked points.

=== RULES (NON-NEGOTIABLE) ===
1. Every paragraph marked [KEEP VERBATIM] must appear UNCHANGED in your output.
2. After each [INSERT DIALOGUE AFTER THIS PARAGRAPH], add 1-2 short dialogue exchanges.
3. A dialogue exchange = a quoted line + a physical beat (what hands/eyes/body do).
4. Total new dialogue: at least {needed} quoted lines spread across the insert points.
5. Dialogue must CAUSE A TURN — reveal, challenge, deflect, or surprise.
6. Each character sounds DIFFERENT. Real people fumble, dodge, interrupt.
7. You may ONLY add lines. Do NOT delete, rephrase, or compress any existing text.
8. The final output must be LONGER than the input (you're adding, not replacing).

=== POV LOCK ===
FIRST PERSON ("I") — {pov}'s POV.

=== SCENE WITH INSERTION MARKERS ===
{annotated_scene}

=== NOW OUTPUT ===
Return the complete scene with dialogue inserted at the marked points.
Remove all [KEEP VERBATIM] and [INSERT DIALOGUE AFTER THIS PARAGRAPH] markers.
Output ONLY the scene text — no commentary, no labels."""

        try:
            max_tokens = min(max(int(len(content.split()) * 2.5), 2500), 5000)
            response = await client.generate(
                prompt, max_tokens=max_tokens, temperature=0.5,
                system_prompt=self._format_contract,
                stop=self._stop_sequences, timeout=300)
            tokens = response.input_tokens + response.output_tokens

            new_content = self._postprocess(response.content, pov_character=pov)
            # Strip any surviving markers
            new_content = re.sub(r'\[(?:KEEP VERBATIM|INSERT DIALOGUE[^\]]*)\]\s*', '', new_content)

            # Validate: must have dialogue AND not shrink
            new_dialogue = len(re.findall(r'"[^"]{5,}"', new_content))
            old_words = len(content.split())
            new_words = len(new_content.split())

            if (new_dialogue >= MIN_DIALOGUE_LINES and
                    new_words >= old_words * 0.92 and
                    new_content and len(new_content.strip()) > 200):
                logger.info(f"Dialogue drought fixed in {sid}: "
                           f"{dialogue_lines} -> {new_dialogue} lines")
                return new_content, tokens
            else:
                logger.warning(f"Dialogue fix rejected for {sid}: "
                             f"dialogue {new_dialogue}, words {new_words}/{old_words}")
                return content, tokens
        except Exception as e:
            logger.warning(f"Dialogue drought fix failed for {sid}: {e}")
            return content, 0

    async def _micro_ai_tell_scrub(self, client, content: str, scene: dict,
                                    sid: str, pov: str) -> tuple:
        """Scrub AI-tell phrases from scene content.

        Treats AI tells as lint errors: finds them, rewrites only the
        offending sentences to show-not-tell, keeps everything else verbatim.
        """
        tell_results = count_ai_tells(content)

        if tell_results["total_tells"] <= 1:
            return content, 0

        found_tells = list(tell_results["patterns_found"].keys())
        logger.info(f"AI tells in {sid}: {tell_results['total_tells']} "
                    f"({', '.join(found_tells[:5])})")

        tell_list = '\n'.join(f'- "{t}"' for t in found_tells[:10])

        prompt = f"""Remove these AI-tell phrases from the scene. For each one,
rewrite the sentence to SHOW the emotion through action, body language, or sensory detail.

=== PHRASES TO KILL ===
{tell_list}

=== REWRITE RULES ===
1. Replace each tell with a concrete physical action or sensory detail.
2. "I felt a sense of dread" -> describe the physical sensation (stomach, throat, hands).
3. "I couldn't help but notice" -> just describe what the character notices.
4. "Suddenly" -> delete it. Start the action directly.
5. Keep EVERYTHING ELSE verbatim. Only change sentences containing these phrases.

=== POV LOCK ===
FIRST PERSON ("I") — {pov}'s POV.

=== SCENE TO FIX ===
{content}

=== NOW REWRITE ===
Output the complete scene with tells replaced. Change ONLY the sentences
that contain the listed phrases. Everything else stays EXACTLY as written."""

        try:
            max_tokens = min(max(int(len(content.split()) * 1.5), 2000), 4096)
            response = await client.generate(
                prompt, max_tokens=max_tokens, temperature=0.3,
                system_prompt=self._format_contract,
                stop=self._stop_sequences, timeout=300)
            tokens = response.input_tokens + response.output_tokens

            new_content = self._postprocess(response.content, pov_character=pov)

            # Validate: fewer tells, similar word count
            new_tells = count_ai_tells(new_content)
            old_words = len(content.split())
            new_words = len(new_content.split())

            if (new_tells["total_tells"] < tell_results["total_tells"] and
                    new_words >= old_words * 0.8 and
                    new_content and len(new_content.strip()) > 200):
                logger.info(f"AI tells scrubbed in {sid}: "
                           f"{tell_results['total_tells']} -> {new_tells['total_tells']}")
                return new_content, tokens
            else:
                logger.warning(f"AI tell scrub rejected for {sid}: "
                             f"tells {new_tells['total_tells']}, words {new_words}/{old_words}")
                return content, tokens
        except Exception as e:
            logger.warning(f"AI tell scrub failed for {sid}: {e}")
            return content, 0

    async def _micro_scene_turn_repair(self, client, content: str, scene: dict,
                                        sid: str, pov: str) -> tuple:
        """Repair scenes that lack a scene turn in the final paragraphs.

        Only rewrites the last 2 paragraphs — the rest stays untouched.
        The new ending must contain a clear turn: decision, revelation,
        action, or shift.
        """
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if len(paragraphs) < 3:
            return content, 0

        # Check last 2 paragraphs for turn signals
        last_two = '\n\n'.join(paragraphs[-2:]).lower()
        turn_signals = [
            "but", "then", "until", "except", "instead",
            "realize", "understand", "knew", "changed", "shifted",
            "door", "phone", "voice", "said", "asked", "told",
            "decided", "chose", "turned", "stopped", "froze",
            "no", "wait", "wrong", "different", "?",
        ]
        has_turn = sum(1 for sig in turn_signals if sig in last_two)

        if has_turn >= 2:
            return content, 0

        logger.info(f"No scene turn in {sid}: repairing final paragraphs")

        kept = '\n\n'.join(paragraphs[:-2])
        old_ending = '\n\n'.join(paragraphs[-2:])

        prompt = f"""The ending of this scene lacks a scene turn. Rewrite ONLY the final 2 paragraphs
to include a clear turn — something that changes the situation or the character's understanding.

=== WHAT IS A SCENE TURN? ===
A moment where the scene's trajectory shifts:
- A decision that can't be undone
- New information that changes everything
- An action that creates consequences
- A question or statement that reframes the conflict
The turn must be EARNED by what came before, not random.

=== SCENE CONTEXT (keep this, do NOT rewrite) ===
{kept}

=== CURRENT ENDING (rewrite this) ===
{old_ending}

=== POV LOCK ===
FIRST PERSON ("I") — {pov}'s POV.

=== NOW REWRITE ===
Write exactly 2 paragraphs that replace the current ending. The new ending must:
1. Flow naturally from the context above
2. Contain a clear turn (decision, revelation, action, or shift)
3. End on action or dialogue, NOT reflection or summary
4. Match the tone and voice of the rest of the scene"""

        try:
            response = await client.generate(
                prompt, max_tokens=800, temperature=0.5,
                system_prompt=self._format_contract,
                stop=self._stop_sequences, timeout=300)
            tokens = response.input_tokens + response.output_tokens

            new_ending = self._postprocess(response.content, pov_character=pov)

            if new_ending and len(new_ending.strip()) > 50:
                new_ending_lower = new_ending.lower()
                new_turn_count = sum(1 for sig in turn_signals if sig in new_ending_lower)

                if new_turn_count >= 2:
                    content = kept + "\n\n" + new_ending.strip()
                    logger.info(f"Scene turn repaired in {sid}")
                    return content, tokens
                else:
                    logger.warning(f"Turn repair for {sid} still lacks signals, keeping original")
                    return content, tokens

            return content, tokens
        except Exception as e:
            logger.warning(f"Scene turn repair failed for {sid}: {e}")
            return content, 0

    async def _micro_wolf_voice_seed(self, client, content: str, scene: dict,
                                      sid: str, pov: str) -> tuple:
        """Insert one italic inner-voice line if the scene should have it but doesn't.

        Detects whether the current POV character has an italic inner voice
        defined in writing_style config. If so and the scene has zero italic
        lines, surgically inserts exactly one in the opening 3 paragraphs.
        """
        # Check if this POV character has an italic inner voice
        writing_style = self.state.config.get("writing_style", "")
        if "italic" not in writing_style.lower():
            return content, 0

        pov_lower = pov.lower().split()[0]  # First name
        ws_lower = writing_style.lower()

        # Check if this character's name appears near "italic" in the style guide
        italic_idx = ws_lower.find("italic")
        if italic_idx == -1:
            return content, 0

        # Search backwards from "italic" for the character name
        pre_text = ws_lower[:italic_idx + 20]
        name_idx = pre_text.rfind(pov_lower)
        if name_idx == -1 or (italic_idx - name_idx) > 120:
            return content, 0  # This character doesn't have the inner voice

        # Check if scene already has italic inner voice
        italic_phrases = re.findall(r'(?<!\*)\*(?!\*)[^*\n]{1,40}\*(?!\*)', content)
        if italic_phrases:
            return content, 0  # Already has italics, skip

        logger.info(f"Wolf voice missing in {sid}: inserting italic seed")

        # Find a good insertion point in the first 3 paragraphs
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if len(paragraphs) < 3:
            return content, 0

        # Pick the first paragraph that has an emotional or sensory moment
        insert_idx = 1  # Default: after paragraph 2
        emotion_cues = re.compile(
            r'\b(chest|gut|stomach|heart|pulse|hands|fists|jaw|teeth|breath|'
            r'muscle|tension|instinct|wolf|scent|smell|pine|heat)\b', re.IGNORECASE)
        for i in range(min(3, len(paragraphs))):
            if emotion_cues.search(paragraphs[i]):
                insert_idx = i
                break

        # Build a minimal prompt for exactly one italic line
        context_para = paragraphs[insert_idx]
        prompt = f"""Add exactly ONE italic inner-voice thought to this paragraph.

=== RULES ===
1. The italic thought is {pov}'s raw, primal inner voice — 1 to 5 words.
2. Format: *word.* or *short phrase.*
3. It must feel involuntary, like an intrusive thought.
4. Place it where emotion peaks in the paragraph — mid-sentence or between sentences.
5. Return ONLY the paragraph with the italic thought inserted. Nothing else.

=== PARAGRAPH ===
{context_para}

=== OUTPUT ===
Return the paragraph with exactly one *italic thought* added:"""

        try:
            response = await client.generate(
                prompt, max_tokens=600, temperature=0.5,
                system_prompt=self._format_contract,
                stop=self._stop_sequences, timeout=120)
            tokens = response.input_tokens + response.output_tokens

            new_para = response.content.strip()
            # Remove any preamble/labels the model might add
            new_para = re.sub(r'^(?:Here|Output|Paragraph|The paragraph)[^\n]*\n', '', new_para, flags=re.IGNORECASE).strip()

            # Validate: must contain an italic phrase and most of the original
            new_italics = re.findall(r'(?<!\*)\*(?!\*)[^*\n]{1,40}\*(?!\*)', new_para)
            orig_words = set(context_para.lower().split())
            new_words_set = set(new_para.lower().split())
            overlap = len(orig_words & new_words_set) / max(len(orig_words), 1)

            if new_italics and overlap >= 0.7 and len(new_para) > len(context_para) * 0.8:
                paragraphs[insert_idx] = new_para
                content = '\n\n'.join(paragraphs)
                logger.info(f"Wolf voice seeded in {sid}: '{new_italics[0]}'")
                return content, tokens
            else:
                logger.warning(f"Wolf voice seed rejected for {sid}: "
                             f"italics={len(new_italics)}, overlap={overlap:.2f}")
                return content, tokens
        except Exception as e:
            logger.warning(f"Wolf voice seed failed for {sid}: {e}")
            return content, 0

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

            exp_max = self.get_max_tokens_for_stage("scene_expansion", 3000)
            expanded_content, exp_tokens = await self._generate_prose(
                client, prompt, "scene_expansion",
                scene_meta={"chapter": scene.get("chapter"), "scene": scene.get("scene_number"), "pov": scene.get("pov", "")},
                max_tokens=exp_max)

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
            total_tokens += exp_tokens

        self.state.scenes = expanded_scenes

        return {
            "scenes_expanded": scenes_expanded,
            "total_scenes": len(expanded_scenes)
        }, total_tokens

    def _get_outline_for_scene(self, chapter: int, scene_number: int) -> dict:
        """Map a (chapter, scene_number) pair to its outline scene dict.

        Returns empty dict if not found (graceful degradation).
        """
        for ch in (self.state.master_outline or []):
            if ch.get("chapter") == chapter:
                for sc in ch.get("scenes", []):
                    sc_num = sc.get("scene", sc.get("scene_number"))
                    if sc_num == scene_number:
                        return sc
        return {}

    # ── Quality escalation helpers ──────────────────────────────────────────

    def _build_repair_directives(
        self, scores: Dict[str, int], llm_fixes: List[str],
        llm_fail_reasons: Dict[str, list] = None,
    ) -> Dict[str, Any]:
        """Merge LLM-provided fixes with CATEGORY_FILL_INS templates.

        Returns dict with:
          directives:  list[str]   — ordered repair imperatives
          success_criteria: list[str] — machine-checkable criteria for re-score
          patch_targets: list[str] — which parts of the scene to touch
        """
        directives: list[str] = []
        criteria: list[str] = []
        patch_targets: list[str] = []

        weak_cats = [c for c in STRUCTURE_CATEGORIES if scores.get(c, 0) < 3]

        for cat in weak_cats:
            fill = CATEGORY_FILL_INS.get(cat, {})
            # Prefer LLM-specific fail_reasons when available, else use template
            cat_reasons = (llm_fail_reasons or {}).get(cat, fill.get("common_deficits", []))

            # Add template directives for this category
            for d in fill.get("directives", []):
                if d not in directives:
                    directives.append(d)

            # Add template success criteria
            for c in fill.get("success_criteria", []):
                if c not in criteria:
                    criteria.append(c)

            # Infer patch targets from category
            if cat == "structure":
                patch_targets.append("opening paragraphs (goal statement)")
                patch_targets.append("middle section (obstacle + tactic)")
            elif cat == "tension":
                patch_targets.append("consequence/stakes passages")
            elif cat == "emotional_beat":
                patch_targets.append("emotional arc transitions")
            elif cat == "dialogue_realism":
                patch_targets.append("dialogue exchanges")
            elif cat == "scene_turn":
                patch_targets.append("final beat / closing paragraphs")

        # Append LLM-generated fixes that aren't already covered
        for f in (llm_fixes or [])[:4]:
            if f and f not in directives:
                directives.append(f)

        return {
            "directives": directives,
            "success_criteria": criteria,
            "patch_targets": patch_targets,
        }

    @staticmethod
    def _mark_repair_spans(content: str, patch_targets: List[str]) -> str:
        """Annotate scene paragraphs with [KEEP VERBATIM] / [FIX THIS] markers.

        Maps semantic patch_targets to paragraph indices:
          "opening paragraphs"  → first 2 paragraphs
          "middle section"      → paragraphs between opening and closing
          "final beat"          → last 2 paragraphs
          "dialogue exchanges"  → paragraphs containing quoted speech
          "emotional arc"       → middle 50% of paragraphs
          "consequence/stakes"  → middle 50% of paragraphs
        Falls back to full-scene repair if >70% of paragraphs are targeted.
        """
        paragraphs = [p for p in content.split("\n\n") if p.strip()]
        n = len(paragraphs)
        if n < 4:
            # Scene too short for span targeting — repair everything
            return content

        fix_indices: set = set()
        targets_lower = " ".join(patch_targets).lower()

        if "opening" in targets_lower or "goal statement" in targets_lower:
            fix_indices.update(range(min(2, n)))
        if "obstacle" in targets_lower or "tactic" in targets_lower or "middle" in targets_lower:
            fix_indices.update(range(2, max(2, n - 2)))
        if "final" in targets_lower or "closing" in targets_lower:
            fix_indices.update(range(max(0, n - 2), n))
        if "dialogue" in targets_lower:
            for i, p in enumerate(paragraphs):
                if '"' in p or '\u201c' in p:  # straight or smart quotes
                    fix_indices.add(i)
        if "emotional" in targets_lower or "consequence" in targets_lower or "stakes" in targets_lower:
            quarter = max(1, n // 4)
            fix_indices.update(range(quarter, n - quarter))

        # Fallback: if too many paragraphs are targeted, don't bother with markers
        if len(fix_indices) > n * 0.7:
            return content

        marked = []
        for i, p in enumerate(paragraphs):
            tag = "[FIX THIS]" if i in fix_indices else "[KEEP VERBATIM]"
            marked.append(f"{tag}\n{p}")
        return "\n\n".join(marked)

    def _build_structure_repair_prompt(
        self, content: str, meta: dict, scores: Dict[str, int],
        repair_info: Dict[str, Any], target_words: int,
    ) -> str:
        """Build a targeted repair prompt with explicit success criteria.

        Uses span-targeted patching: paragraphs are marked [KEEP VERBATIM]
        or [FIX THIS] so the model knows exactly what to touch. Preserves
        80%+ wording and proves compliance via success criteria.
        """
        weak_cats = [c for c in STRUCTURE_CATEGORIES if scores.get(c, 0) < 3]
        score_lines = "\n".join(
            f"  * {cat}: {scores.get(cat, 0)}/5{' **WEAK**' if cat in weak_cats else ''}"
            for cat in STRUCTURE_CATEGORIES
        )
        directive_lines = "\n".join(
            f"{i+1}. {d}" for i, d in enumerate(repair_info["directives"])
        )
        criteria_lines = "\n".join(
            f"  * {c}" for c in repair_info["success_criteria"]
        )
        patch_lines = ", ".join(repair_info["patch_targets"]) if repair_info["patch_targets"] else "any"

        # Annotate scene with paragraph-level repair markers
        marked_content = self._mark_repair_spans(content, repair_info["patch_targets"])
        has_markers = "[FIX THIS]" in marked_content

        span_instruction = (
            "Paragraphs marked [KEEP VERBATIM] must be preserved word-for-word. "
            "Only rewrite paragraphs marked [FIX THIS]. "
            "Remove all [KEEP VERBATIM] and [FIX THIS] tags from your output."
        ) if has_markers else (
            f"Only modify these spans: {patch_lines}. Keep everything else verbatim where possible."
        )

        return f"""Rewrite this scene to fix structural weaknesses.

NON-NEGOTIABLES:
- Output ONLY the revised scene. No preamble, no headings, no notes, no tags.
- Preserve first-person POV and the existing character names and facts.
- Keep at least 80% of the original wording unless a change is required to meet the success criteria.
- Keep scene length within ±15% of the original (~{target_words} words).
- {span_instruction}

SCENE META (truth you must satisfy):
{json.dumps(meta, ensure_ascii=False)}

ORIGINAL SCENE:
{marked_content}

SCORECARD:
{score_lines}

REPAIR DIRECTIVES:
{directive_lines}

SUCCESS CRITERIA (must be detectable on re-read):
{criteria_lines}

Now output the revised scene."""

    async def _stage_structure_gate(self) -> tuple:
        """Quality escalation gate: score → diagnose → repair → rescore.

        For each scene, scores 5 categories (0-5 each, 25 total):
          structure, tension, emotional_beat, dialogue_realism, scene_turn

        Enhanced scoring outputs per-category fail_reasons, repair_directives,
        and patch_targets for targeted repairs with explicit success criteria.

        Quality escalation loop:
          1. Score scene (JSON with fail_reasons + repair_directives)
          2. Build repair prompt with category fill-ins + success criteria
          3. Repair scene via _generate_prose
          4. Re-score repaired scene
          5. Stop when: target achieved, improvement < threshold, or max iterations

        Configurable via defense.thresholds:
          structure_gate_max_iterations (default 3)
          structure_gate_pass_total (default 16)
          structure_gate_pass_min (default 3)
          structure_gate_diminishing_threshold (default 1)
        """
        if not self.state.scenes:
            logger.info("structure_gate: no scenes, skipping")
            return {"skipped": True}, 0

        scoring_client = self.get_client_for_stage("structure_gate")
        repair_client = self.get_client_for_stage("continuity_fix")  # Claude for prose repair
        if not scoring_client:
            logger.warning("structure_gate: no scoring client available, skipping")
            return {"skipped": True, "reason": "no_client"}, 0

        total_tokens = 0
        target_words = self.state.words_per_scene or 750

        # Pull configurable thresholds
        max_iterations = int(self._get_threshold("structure_gate_max_iterations"))
        pass_total = int(self._get_threshold("structure_gate_pass_total"))
        pass_min = int(self._get_threshold("structure_gate_pass_min"))
        diminishing_threshold = int(self._get_threshold("structure_gate_diminishing_threshold"))

        # Track results for logging/debugging
        gate_results = {
            "iterations": [],
            "scenes_failed_final": [],
            "scenes_repaired": 0,
            "pass_criteria": {"total": pass_total, "min": pass_min},
        }

        # Build index of all scenes to check (skip very short/empty)
        candidates = []
        for idx, scene in enumerate(self.state.scenes):
            if not isinstance(scene, dict):
                continue
            content = scene.get("content", "")
            if len(content.split()) < 100:  # Skip scenes under 100 words
                continue
            candidates.append(idx)

        # Track which scenes are currently failing + their last scores for diminishing returns
        failing_indices = set(candidates)
        prev_scores_by_idx: Dict[int, int] = {}  # idx -> previous total score

        for iteration in range(1, max_iterations + 1):
            iter_report = {
                "iteration": iteration, "scored": 0, "failed": 0,
                "repaired": 0, "diminishing_returns_stopped": 0,
            }

            # --- SCORING PASS ---
            still_failing = []
            for idx in sorted(failing_indices):
                scene = self.state.scenes[idx]
                chapter = scene.get("chapter", 0)
                scene_num = scene.get("scene_number", 0)
                content = scene.get("content", "")
                outline = self._get_outline_for_scene(chapter, scene_num)

                # Build compact outline meta for scoring prompt
                meta = {
                    "scene_name": outline.get("scene_name", ""),
                    "pov": outline.get("pov", scene.get("pov", "")),
                    "purpose": outline.get("purpose", ""),
                    "character_scene_goal": outline.get("character_scene_goal", ""),
                    "central_conflict": outline.get("central_conflict", ""),
                    "emotional_arc": outline.get("emotional_arc", ""),
                    "outcome": outline.get("outcome", ""),
                    "tension_level": outline.get("tension_level", ""),
                }

                # Truncate scene for scoring: first 120 words (opening) + last 300 words (climax/turn)
                words = content.split()
                if len(words) > 500:
                    opening = " ".join(words[:120])
                    ending = " ".join(words[-300:])
                    scene_excerpt = f"{opening}\n\n[...middle omitted for brevity...]\n\n{ending}"
                else:
                    scene_excerpt = content

                # Enhanced scoring prompt: requests fail_reasons, repair_directives, patch_targets
                scoring_prompt = f"""Evaluate this scene's narrative structure.

OUTPUT ONLY JSON with this exact schema:
{{"scores": {{"structure": 0, "tension": 0, "emotional_beat": 0, "dialogue_realism": 0, "scene_turn": 0}}, "fail_reasons": {{"structure": ["..."], "tension": ["..."]}}, "repair_directives": ["max 4 imperatives"], "patch_targets": ["opening paragraphs", "final beat"], "reasons": ["max 4 short bullets"], "fixes": ["max 4 concrete fix directives"]}}

Only include fail_reasons for categories scoring below 3. Each fail_reason should be 1 sentence explaining WHAT is missing.

Rubric (0-5 each, 5 is best):
- structure: clear goal stated early, concrete obstacle, tactic progression, coherent beginning/middle/end
- tension: active conflict or pressure, explicit stakes/consequences, uncertainty, escalation over scene
- emotional_beat: clear internal shift from one posture to another, shown through behavior change, matches intended arc
- dialogue_realism: subtext present, evasion/deflection, distinct voices, not exposition dumps
- scene_turn: ending changes stakes/knowledge/relationships, next action is forced, no summary endings

Target length: ~{target_words} words.

SCENE META:
{json.dumps(meta, ensure_ascii=False)}

SCENE TEXT:
{scene_excerpt}

JSON:"""

                try:
                    response = await scoring_client.generate(
                        scoring_prompt,
                        system_prompt=STRUCTURE_GATE_SYSTEM_PROMPT,
                        temperature=self.get_temperature_for_stage("structure_gate"),
                        max_tokens=600,  # Larger to accommodate fail_reasons
                        stop=STRUCTURE_GATE_STOP_SEQUENCES,
                        json_mode=True,
                    )
                    total_tokens += response.input_tokens + response.output_tokens
                    iter_report["scored"] += 1

                    # Parse scorecard
                    payload = extract_json_robust(response.content, expect_array=False)
                    if not isinstance(payload, dict):
                        payload = {}
                    scores_raw = payload.get("scores", {})
                    reasons = payload.get("reasons", [])
                    fixes = payload.get("fixes", [])
                    fail_reasons = payload.get("fail_reasons", {})
                    llm_directives = payload.get("repair_directives", [])
                    llm_patch_targets = payload.get("patch_targets", [])

                    # Normalize scores: ensure all categories present and in 0-5
                    scores = {}
                    for cat in STRUCTURE_CATEGORIES:
                        v = scores_raw.get(cat)
                        if isinstance(v, (int, float)) and 0 <= v <= 5:
                            scores[cat] = int(v)
                        else:
                            scores[cat] = 0  # Missing = treat as failing

                    score_total = sum(scores.values())
                    score_min = min(scores.values())
                    passed = score_total >= pass_total and score_min >= pass_min

                    if passed:
                        logger.info(
                            f"  structure_gate: Ch{chapter}-S{scene_num} PASS "
                            f"({score_total}/25, min={score_min})"
                        )
                    else:
                        # Diminishing returns check: if we repaired this scene and
                        # the score didn't improve by at least the threshold, stop trying
                        prev_total = prev_scores_by_idx.get(idx)
                        if prev_total is not None and iteration > 1:
                            improvement = score_total - prev_total
                            if improvement < diminishing_threshold:
                                logger.info(
                                    f"  structure_gate: Ch{chapter}-S{scene_num} diminishing returns "
                                    f"({prev_total}→{score_total}, Δ{improvement}), stopping repairs"
                                )
                                iter_report["diminishing_returns_stopped"] += 1
                                # Don't add to still_failing — accept current version
                                prev_scores_by_idx[idx] = score_total
                                continue

                        logger.warning(
                            f"  structure_gate: Ch{chapter}-S{scene_num} FAIL "
                            f"({score_total}/25, min={score_min}) — {scores}"
                        )
                        still_failing.append((idx, scores, fixes, fail_reasons, llm_directives))
                        iter_report["failed"] += 1
                        prev_scores_by_idx[idx] = score_total

                except Exception as e:
                    logger.warning(f"  structure_gate: scoring failed for Ch{chapter}-S{scene_num}: {e}")
                    continue

            # --- REPAIR PASS (only on failing scenes) ---
            if not still_failing or not repair_client:
                failing_indices = set()
                gate_results["iterations"].append(iter_report)
                break

            for idx, scores, fixes, fail_reasons, llm_directives in still_failing:
                scene = self.state.scenes[idx]
                chapter = scene.get("chapter", 0)
                scene_num = scene.get("scene_number", 0)
                content = scene.get("content", "")
                outline = self._get_outline_for_scene(chapter, scene_num)

                meta = {
                    "scene_name": outline.get("scene_name", ""),
                    "pov": outline.get("pov", scene.get("pov", "")),
                    "purpose": outline.get("purpose", ""),
                    "character_scene_goal": outline.get("character_scene_goal", ""),
                    "central_conflict": outline.get("central_conflict", ""),
                    "emotional_arc": outline.get("emotional_arc", ""),
                    "outcome": outline.get("outcome", ""),
                    "tension_level": outline.get("tension_level", ""),
                    "location": outline.get("location", scene.get("location", "")),
                }

                # Build repair directives by merging LLM diagnostics with template fill-ins
                repair_info = self._build_repair_directives(
                    scores, fixes + llm_directives, fail_reasons,
                )

                # Build targeted repair prompt with explicit success criteria
                repair_prompt = self._build_structure_repair_prompt(
                    content, meta, scores, repair_info, target_words,
                )

                try:
                    repaired_content, tokens = await self._generate_prose(
                        repair_client, repair_prompt, "structure_gate",
                        scene_meta={"chapter": chapter, "scene": scene_num, "pov": scene.get("pov", "")},
                        system_prompt=STRUCTURE_REPAIR_SYSTEM_PROMPT,
                        max_tokens=int(target_words * 2.2),
                        temperature=0.45,
                    )
                    total_tokens += tokens

                    # Verify repair didn't produce garbage (basic length check)
                    repaired_words = len(repaired_content.split()) if repaired_content else 0
                    original_words = len(content.split())
                    if repaired_content and repaired_words >= original_words * 0.5:
                        # Preserve score history for debugging
                        score_history = scene.get("structure_scores_history", [])
                        score_history.append(scores)

                        self.state.scenes[idx] = {
                            **scene,
                            "content": repaired_content,
                            "structure_repaired": True,
                            "structure_repair_iteration": iteration,
                            "structure_scores_before": scores,
                            "structure_scores_history": score_history,
                            "structure_repair_directives": repair_info["directives"],
                        }
                        iter_report["repaired"] += 1
                        gate_results["scenes_repaired"] += 1
                        logger.info(
                            f"    structure_gate: repaired Ch{chapter}-S{scene_num} "
                            f"iter={iteration} ({original_words}→{repaired_words} words)"
                        )
                    else:
                        logger.warning(
                            f"    structure_gate: repair too short for Ch{chapter}-S{scene_num} "
                            f"({repaired_words} words), keeping original"
                        )
                except Exception as e:
                    logger.warning(f"    structure_gate: repair failed for Ch{chapter}-S{scene_num}: {e}")

            # Update failing set for next iteration (rescore the repaired scenes)
            failing_indices = {idx for idx, _, _, _, _ in still_failing}
            gate_results["iterations"].append(iter_report)

        # Final summary
        gate_results["scenes_failed_final"] = sorted(failing_indices)
        if failing_indices:
            logger.warning(
                f"structure_gate: {len(failing_indices)} scenes still failing after "
                f"{max_iterations} iterations: {sorted(failing_indices)}"
            )
        else:
            logger.info("structure_gate: all scenes passed")

        return gate_results, total_tokens

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
                content, tokens = await self._generate_prose(
                    client, prompt, "self_refinement",
                    scene_meta={"chapter": scene.get("chapter"), "scene": scene.get("scene_number"), "pov": scene.get("pov", "")},
                    max_tokens=2500, temperature=0.7)
                refined_scenes.append({
                    **scene,
                    "content": content,
                    "refined": True
                })
                total_tokens += tokens
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
8. DANGLING SUSPENSE: Any threat, mystery, shadow, secret, or unanswered
   question that is introduced but never resolved or addressed again.
   Examples: a mysterious figure appears but is never explained, a phone
   call creates tension but is never followed up, a character mentions a
   secret that's never revealed. For each dangling thread, note where it
   was introduced and suggest where it should be resolved or cut.
9. REPETITIVE SCENE STRUCTURES: Scenes that follow the same pattern
   (e.g., "character checks phone → reads message → feels emotion → stares
   out window" appearing multiple times). Flag any scene pattern that
   repeats 3+ times.

For each issue found, provide:
- Location (chapter/scene)
- Type of issue (one of: pov_break, duplicate_scene, character, timeline,
  world_rule, factual, hallucination, dangling_suspense, repetitive_structure)
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
            self.state._continuity_fixed_indices = []
            return {"fixes_applied": 0, "skipped": True}, 0

        # Pre-serialize large objects once (avoid re-serializing per scene)
        _world_bible_json = json.dumps(self.state.world_bible, indent=2) if self.state.world_bible else 'Not available'
        _characters_json = json.dumps(self.state.characters, indent=2) if self.state.characters else 'Not available'

        fixed_scenes = list(self.state.scenes or [])
        total_tokens = 0
        fixes_applied = 0
        fixed_indices = set()  # Track which scene indices were modified

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
{_world_bible_json}

CHARACTERS (for reference):
{_characters_json}

Rewrite the scene with the continuity issue fixed. Maintain the same tone, length, and style.
Only change what's necessary to fix the issue.

FIXED SCENE:"""

                    if client:
                        content, tokens = await self._generate_prose(
                            client, prompt, "continuity_fix",
                            scene_meta={"chapter": scene.get("chapter"), "scene": scene.get("scene_number"), "pov": scene.get("pov", "")},
                            max_tokens=2500, temperature=0.7)
                        fixed_scenes[i] = {
                            **scene,
                            "content": content,
                            "continuity_fixed": True,
                            "fixed_issue": issue_desc
                        }
                        total_tokens += tokens
                        fixes_applied += 1
                        fixed_indices.add(i)
                        logger.info(f"Fixed continuity issue in {scene_loc}: {issue_type}")
                    break

        self.state.scenes = fixed_scenes
        # Store fixed indices for continuity_recheck to target
        self.state._continuity_fixed_indices = sorted(fixed_indices)
        logger.info(f"Continuity fix modified {len(fixed_indices)} scenes: {sorted(fixed_indices)}")
        return {"fixes_applied": fixes_applied, "issues_found": len(self.state.continuity_issues)}, total_tokens

    async def _stage_continuity_recheck(self) -> tuple:
        """Tight re-audit loop on scenes modified by continuity_fix.

        Only re-audits the specific scenes that were just fixed.
        If issues remain, re-fixes and re-audits. Max 2 loops.
        Prevents continuity fixes from introducing new issues.
        """
        fixed_indices = getattr(self.state, '_continuity_fixed_indices', []) or []
        if not fixed_indices:
            logger.info("continuity_recheck: no fixed scenes to verify, skipping")
            return {"skipped": True, "reason": "no_fixed_scenes"}, 0

        audit_client = self.get_client_for_stage("continuity_recheck")
        fix_client = self.get_client_for_stage("continuity_fix")
        if not audit_client:
            logger.warning("continuity_recheck: no audit client available, skipping")
            return {"skipped": True, "reason": "no_client"}, 0

        total_tokens = 0
        max_loops = 2
        recheck_report = {"loops": [], "total_fixes": 0}
        remaining_indices = list(fixed_indices)

        for loop_num in range(1, max_loops + 1):
            if not remaining_indices:
                break

            # --- RE-AUDIT: Build targeted manuscript excerpt for only the fixed scenes ---
            targeted_content = "\n\n---\n\n".join([
                f"Chapter {self.state.scenes[i].get('chapter')}, "
                f"Scene {self.state.scenes[i].get('scene_number')}:\n"
                f"{self.state.scenes[i].get('content', '')}"
                for i in remaining_indices
                if i < len(self.state.scenes) and isinstance(self.state.scenes[i], dict)
            ])

            if not targeted_content.strip():
                break

            audit_prompt = f"""You are a continuity editor. Check ONLY these scenes for issues introduced by recent edits.

WORLD RULES:
{json.dumps(self.state.world_bible, indent=2) if self.state.world_bible else 'Not available'}

CHARACTERS:
{json.dumps(self.state.characters, indent=2) if self.state.characters else 'Not available'}

EXPECTED POV: First person ("I") throughout.

SCENES TO VERIFY (these were recently rewritten):
{targeted_content}

Check for:
1. POV breaks introduced by the rewrite
2. Character inconsistencies (names, traits changed)
3. Timeline errors introduced
4. Factual contradictions with established details
5. Hallucinated characters not in the character list

For each issue, provide location, type, description, suggested_fix.
If all scenes are clean, return {{"issues": [], "passed": true}}.

Respond in JSON with "issues" array and "passed" boolean."""

            try:
                response = await audit_client.generate(
                    audit_prompt, max_tokens=2000,
                    temperature=self.get_temperature_for_stage("continuity_recheck"),
                    json_mode=True,
                )
                total_tokens += response.input_tokens + response.output_tokens
                audit_result = extract_json_robust(response.content, expect_array=False)
            except Exception as e:
                logger.warning(f"continuity_recheck: audit parse failed on loop {loop_num}: {e}")
                audit_result = {"issues": [], "passed": True}

            issues = audit_result.get("issues", []) if isinstance(audit_result, dict) else []
            loop_report = {"loop": loop_num, "indices_checked": remaining_indices[:], "issues_found": len(issues)}

            if not issues:
                logger.info(f"continuity_recheck: loop {loop_num} — all {len(remaining_indices)} scenes verified clean")
                recheck_report["loops"].append(loop_report)
                remaining_indices = []
                break

            logger.warning(f"continuity_recheck: loop {loop_num} — {len(issues)} issues in fixed scenes")

            # --- RE-FIX: Apply targeted fixes to scenes with remaining issues ---
            if not fix_client:
                logger.warning("continuity_recheck: no fix client, cannot re-fix")
                recheck_report["loops"].append(loop_report)
                break

            scenes_fixed_this_loop = set()
            for issue in issues:
                if not isinstance(issue, dict):
                    continue
                issue_location = issue.get("location", "")
                issue_type = issue.get("type", "")
                issue_desc = issue.get("description", "")
                suggested_fix = issue.get("suggested_fix", "")

                # Find matching scene in our remaining indices
                for idx in remaining_indices:
                    if idx >= len(self.state.scenes):
                        continue
                    scene = self.state.scenes[idx]
                    if not isinstance(scene, dict):
                        continue
                    scene_loc = f"Chapter {scene.get('chapter')}, Scene {scene.get('scene_number')}"
                    if issue_location.lower() in scene_loc.lower() or scene_loc.lower() in issue_location.lower():
                        fix_prompt = f"""Fix a continuity issue in this scene.

ISSUE TYPE: {issue_type}
ISSUE DESCRIPTION: {issue_desc}
SUGGESTED FIX: {suggested_fix}

ORIGINAL SCENE:
{scene.get('content', '')}

Rewrite the scene with ONLY this issue fixed. Maintain tone, length, and style.
Minimal change only — do not restructure.

FIXED SCENE:"""

                        try:
                            content, tokens = await self._generate_prose(
                                fix_client, fix_prompt, "continuity_recheck",
                                scene_meta={"chapter": scene.get("chapter"), "scene": scene.get("scene_number"), "pov": scene.get("pov", "")},
                                max_tokens=2500, temperature=0.5,
                            )
                            total_tokens += tokens
                            self.state.scenes[idx] = {
                                **scene,
                                "content": content,
                                "continuity_rechecked": True,
                            }
                            scenes_fixed_this_loop.add(idx)
                            recheck_report["total_fixes"] += 1
                            logger.info(f"  continuity_recheck: re-fixed {scene_loc}: {issue_type}")
                        except Exception as e:
                            logger.warning(f"  continuity_recheck: re-fix failed for {scene_loc}: {e}")
                        break

            loop_report["scenes_re_fixed"] = len(scenes_fixed_this_loop)
            recheck_report["loops"].append(loop_report)

            # Next loop only rechecks scenes we just re-fixed
            remaining_indices = sorted(scenes_fixed_this_loop)

        if remaining_indices:
            logger.warning(
                f"continuity_recheck: {len(remaining_indices)} scenes may still have issues "
                f"after {max_loops} loops"
            )

        return recheck_report, total_tokens

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

        # === CROSS-SCENE REPETITION DETECTOR ===
        # Scan all scenes for repeated phrases (3+ word n-grams appearing 3+ times)
        # and repeated physical beats, then inject as per-scene blacklist
        from collections import Counter
        all_scene_texts = [
            s.get("content", "") for s in (self.state.scenes or []) if isinstance(s, dict)
        ]

        # Find repeated phrases (4-8 word n-grams across scenes)
        phrase_counts = Counter()
        for text in all_scene_texts:
            words = text.lower().split()
            seen_in_scene = set()  # Only count each phrase once per scene
            for n in range(4, 9):
                for i in range(len(words) - n + 1):
                    phrase = " ".join(words[i:i+n])
                    if phrase not in seen_in_scene:
                        seen_in_scene.add(phrase)
                        phrase_counts[phrase] += 1

        # Repeated physical/emotional beats (common AI tics)
        beat_patterns = [
            "fingers hovered", "heart pounded", "heart raced", "pulse quickened",
            "breath caught", "stomach flipped", "hands trembled", "jaw clenched",
            "fists clenched", "eyes widened", "brow furrowed", "lips parted",
            "chest tightened", "throat tightened", "shoulders tensed",
            "screen flickered", "phone buzzed", "room felt heavy",
            "hair behind her ear", "tucked a strand", "bit her lip",
            "ran a hand through", "let out a breath", "released a breath",
        ]
        repeated_beats = [b for b in beat_patterns
                          if sum(1 for t in all_scene_texts if b.lower() in t.lower()) >= 2]

        # Collect phrases that appear in 3+ different scenes (likely AI repetition)
        repeated_phrases = [phrase for phrase, count in phrase_counts.most_common(30)
                           if count >= 3 and len(phrase) > 15]  # Skip short common phrases

        # Build the repetition blacklist for injection into prompts
        repetition_blacklist = ""
        if repeated_beats or repeated_phrases:
            blacklist_items = []
            for beat in repeated_beats[:15]:
                blacklist_items.append(f'- "{beat}"')
            for phrase in repeated_phrases[:10]:
                blacklist_items.append(f'- "{phrase}"')
            repetition_blacklist = (
                "\n=== CROSS-SCENE REPETITION BLACKLIST ===\n"
                "These phrases/beats appear too many times across the manuscript.\n"
                "Use each ONE MORE TIME AT MOST across the entire novel. If it appears\n"
                "in this scene, REPLACE it with a different physical action or phrasing:\n"
                + "\n".join(blacklist_items)
            )

        logger.info(f"Repetition detector: {len(repeated_beats)} repeated beats, "
                     f"{len(repeated_phrases)} repeated phrases found")

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
{repetition_blacklist}

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
                content, tokens = await self._generate_prose(
                    client, prompt, "voice_human_pass",
                    scene_meta={"chapter": scene.get("chapter"), "scene": scene.get("scene_number"), "pov": scene.get("pov", "")},
                    max_tokens=2500, temperature=0.7)
                enhanced_scenes.append({
                    **scene,
                    "content": content,
                    "voice_human_passed": True
                })
                total_tokens += tokens
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
                        content, tokens = await self._generate_prose(
                            client, prompt, "continuity_fix_2",
                            scene_meta={"chapter": scene.get("chapter"), "scene": scene.get("scene_number"), "pov": scene.get("pov", "")},
                            max_tokens=2500, temperature=0.3)
                        fixed_scenes[i] = {
                            **scene,
                            "content": content,
                            "continuity_fixed_2": True
                        }
                        total_tokens += tokens
                        fixes_applied += 1
                    break

        self.state.scenes = fixed_scenes
        return {"fixes_applied": fixes_applied}, total_tokens

    async def _stage_dialogue_polish(self) -> tuple:
        """Polish dialogue for authenticity, subtext, and character voice."""
        client = self.get_client_for_stage("dialogue_polish")
        # Pre-serialize large objects once (avoid re-serializing per scene)
        _characters_json = json.dumps(self.state.characters, indent=2) if self.state.characters else 'Not available'
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
{_characters_json}

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

8. KILL BAD DIALOGUE TAGS (hard blacklist):
   - NEVER: "said with a smile", "said with a grin", "said with a laugh"
     → Replace with action beat: She smiled. "Line of dialogue."
   - NEVER: "my voice carried", "her voice was soft", "his voice was firm"
     → The words themselves should convey tone. Cut the voice description.
   - NEVER: "my eyes sparkled", "her eyes danced", "his eyes darkened"
     → Eyes don't speak. Use a physical beat instead.
   - NEVER: "I breathed", "she exhaled", "he whispered" (when not actually whispering)
     → Replace with "said" or cut the tag entirely.
   - NEVER: "I admitted", "she confessed", "he revealed"
     → These tell the reader the line is important. Let the line do that work.
   - PREFERRED: "said", no tag (beat instead), or action tag
     Example: He set down his cup. "That's not what I meant."

=== SCENE TO POLISH ===
{scene.get('content', '')}

Rewrite with polished, authentic dialogue. Keep all non-dialogue prose intact.
Focus ONLY on improving the dialogue and adding physical beats between lines:"""

            if client:
                content, tokens = await self._generate_prose(
                    client, prompt, "dialogue_polish",
                    scene_meta={"chapter": scene.get("chapter"), "scene": scene.get("scene_number"), "pov": scene.get("pov", "")},
                    max_tokens=2500, temperature=0.7)
                polished_scenes.append({
                    **scene,
                    "content": content,
                    "dialogue_polished": True
                })
                total_tokens += tokens
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

        # Genre-aware hook types — prevent thriller cliffhangers in romance etc.
        genre = config.get("genre", "").lower()
        if genre in ("romance", "contemporary romance", "rom-com"):
            hook_types = ("emotional revelation, unanswered question, romantic tension peak, "
                         "vulnerability moment, a choice that changes everything, "
                         "an almost-kiss or interrupted moment, a confession left hanging")
            hook_warning = ("DO NOT add thriller/suspense elements (no shadowy figures, "
                          "mysterious notes, glowing eyes, threats, or danger). "
                          "This is a ROMANCE — hooks come from EMOTIONAL stakes, not physical danger.")
        elif genre in ("thriller", "suspense", "mystery", "crime"):
            hook_types = ("cliffhanger, threat delivered, revelation, pursuit, "
                         "betrayal discovered, danger escalation, ticking clock")
            hook_warning = ""
        elif genre in ("fantasy", "sci-fi", "science fiction"):
            hook_types = ("world-altering revelation, power shift, quest complication, "
                         "betrayal, impossible choice, new threat revealed")
            hook_warning = ""
        else:
            hook_types = ("emotional gut-punch, unanswered question, tension peak, "
                         "twist revealed, a decision with consequences")
            hook_warning = ""

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
- Hook types for this genre: {hook_types}
{hook_warning}
{hook_guidance}

<scene>
{scene.get('content', '')}
</scene>

Output the complete scene with only the ending paragraphs rewritten:"""

                    content, tokens = await self._generate_prose(
                        client, prompt, "chapter_hooks",
                        scene_meta={"chapter": scene.get("chapter"), "scene": scene.get("scene_number"), "pov": scene.get("pov", "")},
                        max_tokens=2500, temperature=0.75)
                    hooked_scenes.append({
                        **scene,
                        "content": content,
                        "hook_enhanced": True
                    })
                    total_tokens += tokens

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

                    content, tokens = await self._generate_prose(
                        client, prompt, "chapter_hooks",
                        scene_meta={"chapter": scene.get("chapter"), "scene": scene.get("scene_number"), "pov": scene.get("pov", "")},
                        max_tokens=2500, temperature=0.75)
                    hooked_scenes.append({
                        **scene,
                        "content": content,
                        "hook_enhanced": True
                    })
                    total_tokens += tokens
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
                content, tokens = await self._generate_prose(
                    client, prompt, "prose_polish",
                    scene_meta={"chapter": scene.get("chapter"), "scene": scene.get("scene_number"), "pov": scene.get("pov", "")},
                    max_tokens=2500, temperature=0.7)
                polished_scenes.append({
                    **scene,
                    "content": content,
                    "polished": True
                })
                total_tokens += tokens
            else:
                polished_scenes.append({**scene, "polished": True})
                total_tokens += 100

        self.state.scenes = polished_scenes
        return {"scenes_polished": len(polished_scenes)}, total_tokens

    # Default surgical replacements (fallback if YAML not found)
    _DEFAULT_SURGICAL_REPLACEMENTS = {
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
        " incredibly ": " ",
        " absolutely ": " ",
        " utterly ": " ",
        " completely ": " ",
        " totally ": " ",
        " truly ": " ",
        " genuinely ": " ",
        "a whirlwind of emotions": "confusion",
        "time seemed to stop": "everything stilled",
        "electricity coursed through": "heat rushed through",
        "my heart skipped a beat": "my breath caught",
        "butterflies in my stomach": "nerves",
        "flooded with": "felt",
        "overwhelmed by": "hit by",
        "like a knife": "",
        "like a knife slicing through butter": "",
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

    def _load_surgical_replacements(self) -> Dict[str, str]:
        """Load surgical replacements from YAML config, falling back to defaults."""
        yaml_path = Path(__file__).parent.parent / "configs" / "surgical_replacements.yaml"
        if yaml_path.exists():
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                # Validate: all categories should be dicts with string keys/values
                if not isinstance(data, dict):
                    logger.warning("surgical_replacements.yaml: expected dict, using defaults")
                    return dict(self._DEFAULT_SURGICAL_REPLACEMENTS)
                merged: Dict[str, str] = {}
                for cat_name, category in data.items():
                    if isinstance(category, dict):
                        for pattern, replacement in category.items():
                            if not isinstance(pattern, str):
                                logger.warning(f"surgical_replacements.yaml: non-string pattern in {cat_name}, skipping")
                                continue
                            if not isinstance(replacement, str):
                                logger.warning(f"surgical_replacements.yaml: non-string replacement for '{pattern}', using empty")
                                replacement = ""
                            merged[pattern] = replacement
                    elif category is not None:
                        logger.warning(f"surgical_replacements.yaml: category '{cat_name}' is not a dict, skipping")
                if merged:
                    logger.info(f"Loaded {len(merged)} surgical replacements from YAML")
                    return merged
            except Exception as e:
                logger.warning(f"Failed to load surgical_replacements.yaml: {e}")
        return dict(self._DEFAULT_SURGICAL_REPLACEMENTS)

    async def _stage_final_deai(self) -> tuple:
        """Final surgical pass to remove any AI tells that slipped through.

        Runs AFTER chapter_hooks. Uses paragraph-based slicing to PROTECT hook text:
        - First 3 paragraphs: protected (chapter opening)
        - Last 4 paragraphs: protected (chapter hook)
        - Middle: editable (regex + targeted LLM rewrites)
        """
        client = self.get_client_for_stage("final_deai")
        cleaned_scenes = []
        total_tokens = 0
        fixes_made = 0

        # Load surgical replacements from YAML config (hot-reloadable per run)
        SURGICAL_REPLACEMENTS = self._load_surgical_replacements()

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
                # HOOK PROTECTION: paragraph-based split (respects boundaries)
                paragraphs = [p for p in content.split('\n\n') if p.strip()]
                HEAD_PARAS = 3   # Protect opening paragraphs
                TAIL_PARAS = 4   # Protect closing paragraphs (hook text)

                if len(paragraphs) <= HEAD_PARAS + TAIL_PARAS:
                    # Scene too short to have an editable middle — skip entirely
                    cleaned_scenes.append(scene)
                    continue

                head = "\n\n".join(paragraphs[:HEAD_PARAS])
                middle = "\n\n".join(paragraphs[HEAD_PARAS:-TAIL_PARAS])
                tail = "\n\n".join(paragraphs[-TAIL_PARAS:])

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

                    response = await client.generate(
                        prompt, max_tokens=3000,
                        system_prompt=self._format_contract,
                        stop=self._stop_sequences)
                    rewritten_middle = self._postprocess(response.content, pov_character=scene.get("pov", ""))
                    total_tokens += response.input_tokens + response.output_tokens

                    # Per-paragraph word count guard: reject if any paragraph
                    # lost >50% of its words (LLM rewrote too aggressively)
                    orig_paras = [p for p in middle.split('\n\n') if p.strip()]
                    new_paras = [p for p in rewritten_middle.split('\n\n') if p.strip()]
                    para_ok = True
                    if len(orig_paras) == len(new_paras):
                        for op, np in zip(orig_paras, new_paras):
                            owc = len(op.split())
                            nwc = len(np.split())
                            if owc > 20 and nwc < owc * (1 - self._get_threshold("deai_paragraph_loss_pct")):
                                logger.warning(
                                    f"final_deai: paragraph shrank {owc}->{nwc} words "
                                    f"(>{50}% loss), rejecting LLM rewrite for scene {idx}"
                                )
                                para_ok = False
                                break
                    if para_ok:
                        middle = rewritten_middle
                        scene_fixes += remaining_tells["total_tells"]
                    else:
                        logger.info(f"final_deai: kept original middle for scene {idx} (paragraph shrinkage)")

                # Recombine: protected head + cleaned middle + protected tail
                content = head + "\n\n" + middle + "\n\n" + tail
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

                    response = await client.generate(
                        prompt, max_tokens=3000,
                        system_prompt=self._format_contract,
                        stop=self._stop_sequences)
                    content = self._postprocess(response.content, pov_character=scene.get("pov", ""))
                    total_tokens += response.input_tokens + response.output_tokens
                    scene_fixes += remaining_tells["total_tells"]

            if scene_fixes > 0:
                fixes_made += scene_fixes

            cleaned_scenes.append({
                **scene,
                "content": content,
                "deai_fixes": scene_fixes
            })

        # --- POST-CHECK: Validate final_deai didn't corrupt content ---
        # Since final_deai bypasses critic gate, we need lightweight sanity checks
        deai_issues = []
        for idx, (orig, cleaned) in enumerate(zip(scenes_list, cleaned_scenes)):
            if not isinstance(orig, dict) or not isinstance(cleaned, dict):
                continue
            orig_wc = count_words_accurate(orig.get("content", ""))
            new_wc = count_words_accurate(cleaned.get("content", ""))
            if orig_wc > 0:
                delta_pct = (orig_wc - new_wc) / orig_wc * 100
                # Flag if word count dropped more than threshold (LLM hallucinated/truncated)
                if delta_pct > self._get_threshold("deai_word_delta_pct") * 100:
                    deai_issues.append(
                        f"Scene {idx} lost {delta_pct:.0f}% words ({orig_wc}->{new_wc})"
                    )
                    # Restore original — the "fix" was worse than the disease
                    cleaned_scenes[idx] = orig
                    fixes_made -= cleaned.get("deai_fixes", 0)
                    logger.warning(f"final_deai post-check: restored scene {idx} (lost {delta_pct:.0f}% words)")

        # Check for homogeneous corruption (>30% of scenes start with same prefix)
        if len(cleaned_scenes) > 5:
            prefixes = []
            for s in cleaned_scenes:
                if isinstance(s, dict):
                    c = s.get("content", "")
                    prefixes.append(c[:100].lower().strip() if c else "")
            from collections import Counter
            prefix_counts = Counter(p for p in prefixes if p)
            for prefix, count in prefix_counts.most_common(1):
                if count > len(cleaned_scenes) * 0.3:
                    logger.error(
                        f"final_deai post-check: {count}/{len(cleaned_scenes)} scenes share "
                        f"first 100 chars — possible corruption. Restoring all."
                    )
                    cleaned_scenes = list(scenes_list)  # Restore ALL
                    fixes_made = 0
                    deai_issues.append(f"Homogeneous corruption: {count} scenes same prefix")
                    break

        self.state.scenes = cleaned_scenes
        logger.info(f"Final de-AI pass: {fixes_made} fixes (hook-protected on {len(chapter_end_indices)} chapter endings)")
        if deai_issues:
            logger.warning(f"final_deai post-check issues: {deai_issues}")
        return {"fixes_made": fixes_made, "scenes_processed": len(cleaned_scenes),
                "hooks_protected": len(chapter_end_indices), "post_check_issues": deai_issues}, total_tokens

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

        # 6. Freshness Score — detect language recycling across scenes
        # Compare content-word bigram overlap of each scene vs prior 3 scenes.
        # Filters stopwords and character names to avoid false positives.
        _FRESHNESS_STOPWORDS = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "is", "was", "were", "are", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "shall", "can", "not", "no", "so",
            "if", "then", "than", "that", "this", "it", "its", "my", "your", "his",
            "her", "our", "their", "i", "me", "we", "he", "she", "they", "you",
            "him", "them", "us", "what", "which", "who", "whom", "how", "when",
            "where", "why", "all", "each", "every", "both", "few", "more", "most",
            "some", "any", "as", "up", "out", "into", "over", "just", "like",
            "about", "back", "down", "still", "even", "also", "too", "very",
        }
        # Build name filter from config (protagonist + other character first names)
        _name_filter = set()
        protag_name = self._get_protagonist_name()
        if protag_name:
            _name_filter.add(protag_name.split()[0].lower())
        for ch in (self.state.config or {}).get("characters", {}).get("others", []):
            if isinstance(ch, str) and ch.strip():
                _name_filter.add(ch.strip().split()[0].lower())

        def _content_bigrams(text):
            words = [w for w in text.lower().split()
                     if w not in _FRESHNESS_STOPWORDS and w not in _name_filter and len(w) > 2]
            return set(zip(words, words[1:])) if len(words) > 1 else set()

        stale_scenes = []
        for i, scene in enumerate(scenes_list):
            content = scene.get("content", "")
            if not content or i < 1:
                continue
            if len(content.split()) < 50:
                continue
            scene_bigrams = _content_bigrams(content)
            # Collect bigrams from prior 3 scenes
            prior_bigrams = set()
            for j in range(max(0, i - 3), i):
                prior_bigrams.update(_content_bigrams(scenes_list[j].get("content", "")))
            if not prior_bigrams or not scene_bigrams:
                continue
            overlap = len(scene_bigrams & prior_bigrams) / len(scene_bigrams)
            freshness_thresh = self._get_threshold("freshness_bigram_pct")
            if overlap > freshness_thresh:  # content-word bigram reuse = stale
                stale_scenes.append({
                    "scene_index": i,
                    "chapter": scene.get("chapter", "?"),
                    "scene_number": scene.get("scene_number", "?"),
                    "overlap_pct": round(overlap * 100, 1)
                })

        if stale_scenes:
            audit_results["freshness"] = {"stale_scenes": stale_scenes}
            if len(stale_scenes) > len(scenes_list) * 0.2:
                audit_results["issues"].append({
                    "type": "freshness",
                    "severity": "medium",
                    "message": f"{len(stale_scenes)} scenes have >{freshness_thresh:.0%} bigram overlap with recent scenes (language recycling)"
                })
                # Stale language flagged — will trigger voice_human_pass
                # in the stages_to_rerun logic below
            logger.info(f"Freshness: {len(stale_scenes)} stale scenes detected")

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

                elif issue["type"] == "freshness":
                    # Stale/recycled language - re-run voice_human_pass
                    if "voice_human_pass" not in audit_results["stages_to_rerun"]:
                        audit_results["stages_to_rerun"].append("voice_human_pass")
                        audit_results["needs_iteration"] = True

            # Track iteration count and detect diminishing returns
            iteration_count = getattr(self.state, '_quality_iterations', 0)
            if iteration_count >= 2:
                logger.warning("Max quality iterations (2) reached. Proceeding with current output.")
                audit_results["needs_iteration"] = False
                audit_results["max_iterations_reached"] = True
            elif iteration_count > 0:
                # Check if previous iteration actually helped (diminishing returns)
                prev_audit = getattr(self.state, '_prev_audit_snapshot', None)
                if prev_audit:
                    prev_wc = prev_audit.get("word_count", {}).get("percentage", 0)
                    prev_tells = prev_audit.get("ai_tells", {}).get("tells_per_1000_words", 99)
                    curr_wc = word_pct
                    curr_tells = ai_tell_results.get("tells_per_1000_words", 99)
                    wc_delta = abs(curr_wc - prev_wc)
                    tells_delta = abs(prev_tells - curr_tells)
                    # If neither metric improved by more than 5%, skip iteration
                    if wc_delta < 5 and tells_delta < 0.5:
                        logger.warning(
                            f"Diminishing returns: word% delta={wc_delta:.1f}%, "
                            f"tells delta={tells_delta:.2f}/1k. Skipping iteration."
                        )
                        audit_results["needs_iteration"] = False
                        audit_results["diminishing_returns"] = True
                    else:
                        self.state._quality_iterations = iteration_count + 1
                else:
                    self.state._quality_iterations = iteration_count + 1
            else:
                self.state._quality_iterations = iteration_count + 1

            # Snapshot current audit for diminishing-returns comparison next iteration
            self.state._prev_audit_snapshot = {
                "word_count": audit_results["word_count"],
                "ai_tells": audit_results["ai_tells"]
            }

        return audit_results, total_tokens

    async def _validation_feedback_loop(self, client) -> Optional[Dict[str, Any]]:
        """Layer G → Pipeline feedback: validate scenes and auto-fix errors.

        Runs scene_validator on all scenes. For META_TEXT errors, attempts targeted
        re-generation of affected scenes (max 1 retry per scene, max 5 scenes per run).
        Returns a report dict or None if no issues found.
        """
        try:
            from prometheus_novel.export.scene_validator import validate_project_scenes
        except ImportError:
            try:
                from export.scene_validator import validate_project_scenes
            except ImportError:
                logger.debug("scene_validator not available, skipping feedback loop")
                return None

        scenes_list = self.state.scenes or []
        config = self.state.config or {}
        report = validate_project_scenes(scenes_list, config)

        if not report.get("has_errors"):
            return None

        # Collect scene indices with META_TEXT errors (fixable via re-generation)
        # Track error count per scene for prioritization
        scene_error_counts: Dict[int, int] = {}
        for issue in report.get("issues", []):
            if issue.get("code") == "META_TEXT" and issue.get("scene_index", -1) >= 0:
                idx = issue["scene_index"]
                scene_error_counts[idx] = scene_error_counts.get(idx, 0) + 1

        if not scene_error_counts:
            logger.info("Validation errors found but none are auto-fixable META_TEXT")
            return {"errors_found": len(report["issues"]), "auto_fixed": 0, "skipped": "no fixable errors"}

        # Prioritize: errors first by count (severity), then by position (early chapters
        # matter more for reader first impressions)
        prioritized = sorted(
            scene_error_counts.keys(),
            key=lambda i: (-scene_error_counts[i], i)  # Most errors first, then lowest index
        )

        # Limit to 5 scenes per feedback loop to bound cost
        MAX_REGEN = int(self._get_threshold("feedback_loop_max_scenes"))
        total_fixable = len(prioritized)
        fixable_indices = prioritized[:MAX_REGEN]

        # If >MAX_REGEN scenes need fixes, flag systemic upstream failure
        systemic_flag = None
        if total_fixable > MAX_REGEN:
            systemic_flag = (
                f"SYSTEMIC: {total_fixable} scenes have META_TEXT errors "
                f"(only fixing top {MAX_REGEN}). Upstream stage likely failed."
            )
            logger.error(systemic_flag)

        fixed = 0
        max_rewritten = int(self._get_threshold("budget_max_rewritten_scenes"))

        for idx in fixable_indices:
            # Budget guard: check total rewritten scenes across all feedback loops
            if self._budget_tracker["rewritten_scenes"] >= max_rewritten:
                logger.warning(
                    f"BUDGET GUARD: rewritten scene limit reached "
                    f"({self._budget_tracker['rewritten_scenes']}/{max_rewritten}). "
                    f"Skipping remaining {len(fixable_indices) - fixable_indices.index(idx)} scenes."
                )
                break

            scene = scenes_list[idx]
            if not isinstance(scene, dict):
                continue

            content = scene.get("content", "")
            if not content or not client:
                continue

            # Re-run through postprocessor (which strips meta-text)
            # Use per-scene POV for dual-POV support
            pov_name, pov_gender = self._get_pov_info(scene.get("pov", ""), scene_text=content)
            language = self._get_setting_language()
            cleaned = _postprocess_scene(content, pov_name, language, pov_gender)

            # If postprocessor fixed it, accept
            from prometheus_novel.export.scene_validator import validate_scene
            recheck = validate_scene(cleaned, config, f"Ch{scene.get('chapter', idx+1)}Sc{scene.get('scene_number', 1)}", idx)
            meta_errors = [i for i in recheck if i.get("code") == "META_TEXT"]

            if not meta_errors:
                scenes_list[idx]["content"] = cleaned
                fixed += 1
                self._budget_tracker["rewritten_scenes"] += 1
                logger.info(f"Feedback loop: fixed scene {idx} via postprocessor")
            else:
                # Last resort: request a clean rewrite from LLM
                logger.warning(f"Feedback loop: scene {idx} still has meta-text after postprocess, requesting rewrite")
                try:
                    prompt = (
                        f"Rewrite this scene as pure narrative prose. Remove ALL meta-text "
                        f"(preambles like 'Here is...', commentary, explanations). "
                        f"Keep the same story content, characters, and events.\n\n{content[:4000]}"
                    )
                    response = await client.generate(
                        prompt, max_tokens=3000,
                        system_prompt=self._format_contract,
                        stop=self._stop_sequences
                    )
                    # Track defense tokens for LLM rewrite
                    self._budget_tracker["defense_tokens"] += (
                        response.input_tokens + response.output_tokens
                    )
                    rewritten = _postprocess_scene(response.content, pov_name, language, pov_gender)
                    # Accept rewrite only if it preserves length AND key entities
                    _retention = self._get_threshold("feedback_loop_wc_retention")
                    if len(rewritten.split()) >= len(content.split()) * _retention:
                        # Entity preservation: protagonist + shared nouns (scaled by scene length)
                        orig_nouns = set(re.findall(r'\b[A-Z][a-z]{2,}\b', content)) - COMMON_CAPS
                        new_nouns = set(re.findall(r'\b[A-Z][a-z]{2,}\b', rewritten)) - COMMON_CAPS
                        protag_first = (pov_name or "").split()[0] if pov_name else ""
                        protag_preserved = (
                            not protag_first or
                            protag_first in rewritten or
                            "I " in rewritten  # First-person POV counts
                        )
                        shared_nouns = len(orig_nouns & new_nouns)
                        # Scale noun requirement by scene length
                        scene_wc = len(content.split())
                        short_threshold = int(self._get_threshold("entity_guard_short_scene_words"))
                        if scene_wc < short_threshold:
                            min_nouns = int(self._get_threshold("entity_guard_short_scene_nouns"))
                        else:
                            min_nouns = 2
                        if protag_preserved and (shared_nouns >= min_nouns or len(orig_nouns) < 3):
                            scenes_list[idx]["content"] = rewritten
                            fixed += 1
                            self._budget_tracker["rewritten_scenes"] += 1
                            logger.info(f"Feedback loop: rewrote scene {idx} (entity check: shared={shared_nouns}, min={min_nouns}, wc={scene_wc})")
                        else:
                            logger.warning(
                                f"Feedback loop: rejected rewrite for scene {idx} "
                                f"(entity drift: protag={protag_preserved}, shared={shared_nouns}/{len(orig_nouns)}, min_required={min_nouns}, wc={scene_wc})"
                            )
                except Exception as e:
                    logger.warning(f"Feedback loop rewrite failed for scene {idx}: {e}")

        self.state.scenes = scenes_list
        result = {
            "errors_found": len(report["issues"]),
            "total_fixable": total_fixable,
            "attempted": len(fixable_indices),
            "auto_fixed": fixed,
            "summary": report.get("summary", ""),
        }
        if systemic_flag:
            result["systemic_warning"] = systemic_flag
        logger.info(f"Feedback loop complete: {fixed}/{len(fixable_indices)} scenes fixed")
        return result

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

        # Include artifact metrics in validation report
        validation_report["artifact_metrics"] = self.state.artifact_metrics

        # Layer G → Pipeline feedback loop: run scene validation and auto-fix errors
        regen_report = await self._validation_feedback_loop(client)
        if regen_report:
            validation_report["feedback_loop"] = regen_report
            # Recalculate word count after fixes
            total_words = sum(count_words_accurate(s.get("content", ""))
                            for s in (self.state.scenes or []) if isinstance(s, dict))
            validation_report["total_words"] = total_words
            word_percentage = (total_words / target_words * 100) if target_words > 0 else 0
            validation_report["word_percentage"] = round(word_percentage, 1)

        # Flush cleanup morgue to JSONL for auditability
        _flush_morgue(self.state.project_path)

        # Flush incident log for rollback/defense event analysis
        _flush_incidents(self.state.project_path)

        # Persist artifact metrics for cross-run trend analysis
        self._persist_artifact_metrics()
        metrics_delta = self._compute_metrics_delta()
        if metrics_delta:
            validation_report["metrics_delta"] = metrics_delta

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

        # Persist run report as structured JSON for post-run analysis
        # This is the "flight recorder" — one file shows the whole run
        run_report = {
            "run_timestamp": datetime.now().isoformat(),
            "project_name": self.state.project_name,
            "config_keys": sorted(config.keys()),
            "stages_completed": list(self.state.completed_stages),
            "validation": validation_report,
            "outline_json": self.state.outline_json_report if self.state.outline_json_report else {},
            "cost": {
                "total_tokens": self.state.total_tokens,
                "total_cost_usd": self.state.total_cost_usd,
                "stage_costs": [
                    {"stage": r.stage_name, "tokens": r.tokens_used, "cost": r.cost_usd}
                    for r in self.state.stage_results
                ],
            },
            "artifact_metrics": self.state.artifact_metrics,
            "defense_budget": dict(self._budget_tracker),
        }
        # Quality dashboard: % scenes flagged by each defense mechanism
        if self.state.scenes:
            total_sc = len(self.state.scenes)
            am = self.state.artifact_metrics
            flagged_dedup = sum(1 for m in am.values() if m.get("retried")) if am else 0
            flagged_gate = sum(1 for m in am.values()
                              if m.get("structure_repair_iteration", 0) > 0) if am else 0
            avg_repair_delta = 0.0
            repair_deltas = []
            for m in (am or {}).values():
                history = m.get("structure_scores_history", [])
                if len(history) >= 2:
                    repair_deltas.append(history[-1] - history[0])
            if repair_deltas:
                avg_repair_delta = sum(repair_deltas) / len(repair_deltas)

            run_report["quality_dashboard"] = {
                "pct_scenes_flagged_semantic_dedup": round(flagged_dedup / total_sc * 100, 1) if total_sc else 0,
                "pct_scenes_repaired_structure_gate": round(flagged_gate / total_sc * 100, 1) if total_sc else 0,
                "avg_score_delta_per_repair": round(avg_repair_delta, 2),
                "total_scenes": total_sc,
            }

        # Add high concept info if available
        if self.state.high_concept_fingerprint:
            run_report["high_concept_fingerprint"] = self.state.high_concept_fingerprint
        if metrics_delta:
            run_report["metrics_delta"] = metrics_delta

        report_file = output_dir / "run_report.json"
        try:
            with open(report_file, "w") as f:
                json.dump(run_report, f, indent=2, default=str)
            logger.info(f"Run report saved to {report_file}")
        except Exception as e:
            logger.warning(f"Failed to save run report: {e}")

        # Log final stats
        logger.info(f"Novel generated: {total_words:,} words across {total_chapters} chapters "
                   f"({word_percentage:.1f}% of target)")

        return validation_report, 100


# Convenience function
async def run_pipeline(project_path: str, llm_client=None, resume: bool = False):
    """Run the full pipeline for a project."""
    orchestrator = PipelineOrchestrator(Path(project_path), llm_client)
    return await orchestrator.run(resume=resume)
