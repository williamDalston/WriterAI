# WriterAI Novel Generation System - Complete Technical Specification

**Version:** 2.0
**Last Updated:** January 2026
**Purpose:** Complete system reconstruction document

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Project Structure](#3-project-structure)
4. [Configuration System](#4-configuration-system)
5. [LLM Client System](#5-llm-client-system)
6. [Pipeline Stages (Complete)](#6-pipeline-stages)
7. [Stage Ordering Rationale](#7-stage-ordering-rationale)
8. [Humanization System](#8-humanization-system)
9. [Quality Assurance](#9-quality-assurance)
10. [Export System](#10-export-system)
11. [Web Interface](#11-web-interface)
12. [Key Algorithms](#12-key-algorithms)
13. [Reconstruction Checklist](#13-reconstruction-checklist)

---

## 1. System Overview

### What It Does
WriterAI is an automated novel generation system that takes a story seed (premise, characters, setting) and produces a complete, publication-ready novel in Word format suitable for Kindle Direct Publishing (KDP).

### Key Capabilities
- Generates 30,000 to 120,000 word novels
- Supports multiple genres with genre-specific pacing
- Multi-model routing (GPT for bulk, Claude for prose, Gemini for long context)
- AI-tell detection and removal
- Professional KDP formatting
- Real-time progress via WebSocket

### Core Philosophy
1. **Planning before drafting** - Extensive outlining ensures coherent plots
2. **Additive before subtractive** - Add content, then refine/remove
3. **Humanization last** - De-AI-ify after all content is finalized
4. **Iteration on failure** - Quality audit can trigger re-runs

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        WEB INTERFACE                             │
│                   (FastAPI + WebSocket)                          │
│                      Port 8080                                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PIPELINE ORCHESTRATOR                         │
│                  (22 sequential stages)                          │
│                                                                  │
│  Planning → Drafting → Refinement → Humanization → Validation   │
└────────────────────────────┬────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │  OpenAI  │   │  Claude  │   │  Gemini  │
        │   GPT    │   │ Anthropic│   │  Google  │
        └──────────┘   └──────────┘   └──────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      KDP EXPORTER                                │
│               (Word Document Generation)                         │
│              6x9 trim, Garamond 11pt                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Project Structure

```
WriterAI/
├── prometheus_novel/
│   ├── stages/
│   │   └── pipeline.py          # Main orchestrator (2900+ lines)
│   │
│   ├── prometheus_lib/
│   │   ├── llm/
│   │   │   └── clients.py       # OpenAI, Gemini, Anthropic wrappers
│   │   ├── models/
│   │   │   └── config_schemas.py
│   │   └── utils/
│   │
│   ├── interfaces/
│   │   └── web/
│   │       └── app.py           # FastAPI web dashboard
│   │
│   ├── export/
│   │   └── docx_exporter.py     # KDP Word export
│   │
│   └── data/
│       └── projects/
│           └── {project-name}/
│               ├── config.yaml       # Project configuration
│               ├── pipeline_state.json
│               └── output/
│                   └── {project}_KDP.docx
│
└── SYSTEM_SPECIFICATION.md      # This document
```

---

## 4. Configuration System

### 4.1 Required Config Fields

```yaml
project_name: string     # URL-safe identifier
title: string            # Book title
synopsis: string         # 2-3 sentence summary
genre: string            # "romance", "fantasy", "thriller", etc.
protagonist: string      # Main character description
target_length: string    # "short (30k)", "standard (60k)", "long (90k)", "epic (120k)"
```

### 4.2 Recommended Fields

```yaml
antagonist: string
setting: string
tone: string             # "dark", "humorous", "literary"
themes: string           # Comma-separated themes
motifs: string           # Recurring symbols/images
writing_style: string    # POV, tense, prose style
influences: string       # Comp titles
avoid: string            # Things to never include
key_plot_points: string  # Major beats
```

### 4.3 Strategic Guidance Block

```yaml
strategic_guidance:
  market_positioning: |
    Target Subgenre: Dark Mafia Romance
    Reader Expectations: 4/5 spice, "Touch Her and Die" trope
    Comp Titles: Painted Scars, Alliance Series
    Keywords: arranged marriage, possessive alpha

  beat_sheet: |
    opening_5pct: Setup - heroine hiding, debt revealed
    inciting_10pct: The Meeting - contract signed
    threshold_25pct: Move-in day, gilded cage
    midpoint_50pct: The Gala, violence, first spice
    low_point_75pct: Betrayal, she flees
    climax_85pct: Rescue, he takes bullet
    resolution_95pct: She chooses him, HEA

  aesthetic_guide: |
    Fashion: Hanifa, Dolce & Gabbana, vintage furs
    Luxury: G-Wagon, Beluga Vodka, Brioni suits
    Sensory: sandalwood, gun oil, cold marble

  tropes: |
    - touch_her_and_die
    - forced_proximity
    - praise_kink
    - body_worship

  dialogue_bank: |
    Hero phrases: "Look at me", "You're mine"
    Heroine phrases: internal defiance, quiet observations

  cultural_notes: |
    Use: Pakhan (Boss), Brigadier (Captain)
    Vodka neat, no ice
    Affection through protection, not words

  commercial_notes: |
    End every chapter on a hook
    Mobile-first: 4 sentences max per paragraph
```

### 4.4 Genre-Aware Pacing

```python
GENRE_PACING = {
    "romance": 2200,      # words/chapter - tight, frequent POV switches
    "dark romance": 2200,
    "mafia": 2400,
    "thriller": 2500,     # standard
    "mystery": 2800,      # slower revelation
    "fantasy": 3500,      # world-heavy
    "sci-fi": 3200,
    "literary": 3000,
    "horror": 2300,       # quick scares
    "ya": 2000,           # younger readers
}
```

---

## 5. LLM Client System

### 5.1 Client Architecture

```python
@dataclass
class LLMResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    finish_reason: str = "stop"
    raw_response: Any = None


class BaseLLMClient(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse
```

### 5.2 Retry Logic

```python
DEFAULT_TIMEOUT_SECONDS = 120
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1.0
MAX_RETRY_DELAY = 30.0
RETRY_MULTIPLIER = 2.0

# Rate limiting: 50 requests/minute per provider
# Exponential backoff with jitter
# Auth errors (401) - don't retry, raise immediately
# Rate limits (429) - 3x longer backoff
# Server errors (5xx) - standard backoff
```

### 5.3 Model Routing

```python
STAGE_MODELS = {
    # Planning stages - GPT (fast, cheap)
    "high_concept": "gpt",
    "beat_sheet": "gpt",
    "master_outline": "gpt",

    # Creative stages - Claude (nuanced)
    "emotional_architecture": "claude",
    "character_profiles": "claude",
    "scene_expansion": "claude",
    "human_passes": "claude",
    "voice_humanization": "claude",
    "prose_polish": "claude",

    # Long context - Gemini
    "world_building": "gemini",
    "continuity_audit": "gemini",
    "quality_audit": "gemini",
}
```

### 5.4 Temperature Settings

```python
STAGE_TEMPERATURES = {
    # Analytical (0.2-0.4) - need precision
    "continuity_audit": 0.2,
    "quality_audit": 0.2,
    "output_validation": 0.2,
    "beat_sheet": 0.3,
    "master_outline": 0.3,
    "final_deai": 0.3,

    # Balanced (0.4-0.6)
    "high_concept": 0.4,
    "world_building": 0.4,
    "trope_integration": 0.4,
    "continuity_fix": 0.4,
    "emotional_architecture": 0.5,
    "character_profiles": 0.5,
    "self_refinement": 0.5,
    "human_passes": 0.6,

    # Creative (0.7-0.9) - need variety
    "motif_infusion": 0.7,
    "prose_polish": 0.7,
    "dialogue_polish": 0.75,
    "chapter_hooks": 0.75,
    "scene_expansion": 0.8,
    "voice_humanization": 0.8,
    "scene_drafting": 0.85,
}
```

---

## 6. Pipeline Stages

### Complete Stage List (22 stages)

```python
STAGES = [
    # === PLANNING PHASE ===
    "high_concept",           # 1. Core theme and hook
    "world_building",         # 2. Setting, rules, locations
    "beat_sheet",             # 3. 3-act structure with percentages
    "emotional_architecture", # 4. Emotional arc mapping
    "character_profiles",     # 5. Deep character psychology
    "master_outline",         # 6. Scene-by-scene plan
    "trope_integration",      # 7. Genre tropes placement

    # === DRAFTING PHASE ===
    "scene_drafting",         # 8. Generate all scenes
    "scene_expansion",        # 9. Expand short scenes
    "continuity_audit",       # 10. Find inconsistencies
    "continuity_fix",         # 11. Fix inconsistencies
    "self_refinement",        # 12. General quality pass

    # === PROSE REFINEMENT PHASE ===
    "motif_infusion",         # 13. Add thematic elements (ADDITIVE)
    "chapter_hooks",          # 14. Enhance chapter endings (TARGETED)
    "dialogue_polish",        # 15. Dialogue authenticity
    "human_passes",           # 16. Remove AI tells
    "voice_humanization",     # 17. Emotional unpredictability
    "prose_polish",           # 18. Final line-level polish
    "final_deai",             # 19. Surgical AI tell removal

    # === VALIDATION PHASE ===
    "quality_audit",          # 20. Comprehensive validation
    "output_validation"       # 21. Final format check
]
```

---

### Stage 1: HIGH_CONCEPT

**Purpose:** Generate the core thematic hook that drives the entire novel.

**Model:** GPT | **Temperature:** 0.4

**Prompt Pattern:**
```
Create a compelling high concept for this novel.

TITLE: {title}
GENRE: {genre}
SYNOPSIS: {synopsis}

A high concept should be:
1. One sentence that captures the unique hook
2. Conveys the central tension/question
3. Implies the emotional journey
4. Marketable and memorable

Respond with just the high concept (one paragraph):
```

**Output:** Single string stored in `state.high_concept`

---

### Stage 2: WORLD_BUILDING

**Purpose:** Establish the complete world bible with rules, locations, and sensory details.

**Model:** Gemini | **Temperature:** 0.4

**Prompt Pattern:**
```
Create a comprehensive world bible for this novel.

{story_context}

Create a world bible with:
1. SETTING: Time, place, atmosphere
2. WORLD RULES: How things work (magic, society, etc.)
3. KEY LOCATIONS: 4-6 locations with sensory details
4. CULTURAL DETAILS: Customs, hierarchy, language
5. SENSORY PALETTE: Smells, sounds, textures
6. AESTHETIC GUIDE: Fashion, architecture, objects

Respond as JSON:
{
  "setting": {...},
  "rules": [...],
  "locations": [...],
  "culture": {...},
  "sensory": {...}
}
```

**Output:** JSON object stored in `state.world_bible`

---

### Stage 3: BEAT_SHEET

**Purpose:** Create the 3-act structure with percentage-based pacing markers.

**Model:** GPT | **Temperature:** 0.3

**Prompt Pattern:**
```
Create a detailed beat sheet for this novel.

{story_context}
{strategic_guidance}

USER-PROVIDED PACING:
{user_beats}

Create beats matching this structure:
- opening_5pct: Setup and status quo
- inciting_10pct: Catalyst that disrupts
- debate_15pct: Reluctance and stakes
- threshold_25pct: Point of no return
- fun_and_games_30pct: Promise of premise
- midpoint_50pct: Major shift/revelation
- bad_guys_55pct: Enemies respond
- all_is_lost_75pct: Darkest moment
- dark_night_80pct: Internal revelation
- climax_85pct: Final confrontation
- resolution_95pct: New status quo

Respond as JSON array:
[
  {"beat": "opening_5pct", "description": "...", "percentage": 5},
  ...
]
```

**Output:** JSON array stored in `state.beat_sheet`

---

### Stage 4: EMOTIONAL_ARCHITECTURE

**Purpose:** Map the emotional journey across every beat for proper pacing.

**Model:** Claude | **Temperature:** 0.5

**Prompt Pattern:**
```
Design the emotional architecture for this novel.

STORY CONCEPT: {high_concept}
BEAT SHEET: {beat_sheet}
PROTAGONIST: {protagonist}

For each beat, define:
1. EMOTIONAL STATE: What protagonist feels (0-10 intensity)
2. READER EMOTION: What reader should feel
3. TONAL REGISTER: Dark, hopeful, tense, romantic, etc.
4. TRANSFORMATION MARKERS: How character is changing
5. SPICE PROGRESSION: If romance, where are intimate moments

Ensure:
- Emotional peaks don't cluster together
- Breathing room between intense scenes
- Clear escalation pattern
- Satisfying emotional resolution

Respond as JSON with beat-by-beat emotional mapping.
```

**Output:** JSON object with emotional arc data

---

### Stage 5: CHARACTER_PROFILES

**Purpose:** Deep psychological profiles for all major characters.

**Model:** Claude | **Temperature:** 0.5

**Prompt Pattern:**
```
Create deep character profiles for this novel.

{story_context}
DIALOGUE BANK: {dialogue_bank}

For each major character, create:

1. PSYCHOLOGY:
   - Core wound
   - Defense mechanisms
   - Secret desire vs. stated goal
   - Fatal flaw

2. VOICE:
   - Speech patterns (formal/casual, vocabulary level)
   - Verbal tics or catchphrases
   - How they deflect vs. confront
   - What topics they avoid

3. PHYSICALITY:
   - Signature gestures
   - Physical tells when lying/nervous/aroused
   - How they occupy space

4. RELATIONSHIPS:
   - How they see each other initially
   - Trigger points for conflict
   - Moments of unexpected vulnerability

Respond as JSON array of character objects.
```

**Output:** JSON array stored in `state.characters`

---

### Stage 6: MASTER_OUTLINE

**Purpose:** Create scene-by-scene outline with all details needed for drafting.

**Model:** GPT | **Temperature:** 0.3

**Max Tokens:** 8000

**Prompt Pattern:**
```
Create a comprehensive scene-by-scene outline.

{story_context}
{beat_sheet}
{characters}
{world_bible}

TARGET: {target_chapters} chapters, {scenes_per_chapter} scenes each

For EACH scene, provide:
{
  "chapter": 1,
  "scene_number": 1,
  "beat": "opening_5pct",
  "pov": "protagonist name",
  "location": "specific place",
  "time": "day/night, how much time passed",
  "present_characters": ["list"],
  "scene_goal": "what must happen",
  "conflict": "what opposes the goal",
  "emotional_beat": "what reader should feel",
  "opening_hook": "first line concept",
  "closing_hook": "last line concept",
  "spice_level": 0-5,
  "tension_level": 1-10,
  "key_dialogue": "important exchange",
  "sensory_focus": "dominant sense",
  "foreshadowing": "what to plant",
  "callback": "what to pay off"
}

Respond as JSON array of scene objects.
```

**Output:** JSON array stored in `state.master_outline`

---

### Stage 7: TROPE_INTEGRATION

**Purpose:** Ensure genre-specific tropes are properly placed in the outline.

**Model:** Claude | **Temperature:** 0.4

**Trope Definitions (Romance):**
```python
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
```

---

### Stage 8: SCENE_DRAFTING

**Purpose:** Generate the actual prose for every scene.

**Model:** GPT | **Temperature:** 0.85

**Max Tokens:** `words_per_scene * 2.5` (minimum 2500)

**Prompt Pattern (per scene):**
```
Write Chapter {chapter}, Scene {scene_number}.

=== MASTER CRAFT PRINCIPLES ===
1. SHOW vs TELL: Physical sensations reveal emotions
2. DIALOGUE SUBTEXT: What's not said matters more
3. SENSORY IMMERSION: Ground every scene in 2-3 senses
4. PACING: Short sentences for tension, longer for reflection
5. HOOKS: First line grabs, last line propels

=== SCENE REQUIREMENTS ===
POV: {pov} (first person, deep POV)
LOCATION: {location}
GOAL: {scene_goal}
CONFLICT: {conflict}
EMOTIONAL BEAT: {emotional_beat}
TENSION: {tension_level}/10

=== OPENING ===
Hook concept: {opening_hook}

=== CLOSING ===
Hook concept: {closing_hook}

=== SENSORY FOCUS ===
Dominant sense: {sensory_focus}
Aesthetic palette: {aesthetic}

=== SPICE LEVEL: {spice_level}/5 ===
0: No romantic content
1: Sexual tension only
2: Kissing/touching
3: Fade to black intimacy
4: Explicit scene
5: Very explicit

=== CHARACTERS PRESENT ===
{characters}

=== CULTURAL NOTES ===
{cultural_notes}

=== CONTINUITY ===
Previous scene ended with: {previous_context}

=== TARGET LENGTH ===
{words_per_scene} words
Paragraphs: 4 sentences max (mobile-optimized)

Begin directly with narrative. No preamble.
```

---

### Stage 9: SCENE_EXPANSION

**Purpose:** Expand any scene below 80% of target word count.

**Model:** Claude | **Temperature:** 0.8

**Trigger:** Scene word count < `target * 0.8`

**Prompt Pattern:**
```
This scene is {actual} words but needs {target} words.

EXPANSION TECHNIQUES:
1. Add sensory details (ground each moment in senses)
2. Deepen internal monologue (what does POV notice/feel)
3. Extend dialogue beats (add physical actions between lines)
4. Slow key moments (expand turning points)
5. Add micro-tensions (small obstacles, hesitations)

DO NOT:
- Add new plot points
- Change scene direction
- Add characters not already present
- Pad with meaningless description

Current scene:
{content}

Expand to ~{target} words while maintaining voice and pacing.
```

---

### Stage 10: CONTINUITY_AUDIT

**Purpose:** Find inconsistencies across the manuscript.

**Model:** Gemini (long context) | **Temperature:** 0.2

**Prompt Pattern:**
```
Audit this manuscript for continuity errors.

FULL MANUSCRIPT:
{all_scenes}

Check for:
1. CHARACTER INCONSISTENCIES:
   - Physical descriptions that change
   - Personality contradictions
   - Knowledge they shouldn't have

2. TIMELINE ISSUES:
   - Events out of order
   - Impossible timing
   - Day/night confusion

3. SETTING ERRORS:
   - Location details that change
   - Characters in wrong places

4. PLOT HOLES:
   - Unresolved threads
   - Contradictory information
   - Missing cause-effect

5. OBJECT TRACKING:
   - Items that appear/disappear
   - Clothing changes mid-scene

Report as JSON:
{
  "issues": [
    {
      "type": "character/timeline/setting/plot/object",
      "severity": "high/medium/low",
      "scene": "Ch1-S2",
      "description": "...",
      "fix_suggestion": "..."
    }
  ]
}
```

---

### Stage 11: CONTINUITY_FIX

**Purpose:** Fix the continuity issues found in audit.

**Model:** Claude | **Temperature:** 0.4

**Process:** For each issue, rewrite the affected scene section.

---

### Stage 12: SELF_REFINEMENT

**Purpose:** General quality improvement pass.

**Model:** Claude | **Temperature:** 0.5

**Prompt Pattern:**
```
Refine this scene for publication quality.

CHECKLIST:
1. POV Consistency (staying in character's head)
2. Dialogue Attribution (clear who's speaking)
3. Paragraph Flow (smooth transitions)
4. Sentence Variety (length varies appropriately)
5. Show vs Tell (emotions through physical sensation)
6. Redundancy (no repeated information)
7. Paragraph Length (4 sentences max for mobile)

Scene to refine:
{content}

Provide the refined scene:
```

---

### Stage 13: MOTIF_INFUSION

**Purpose:** Weave thematic elements throughout (ADDITIVE - don't rewrite).

**Model:** Claude | **Temperature:** 0.7

**Prompt Pattern:**
```
Add motifs and themes to this scene. This is ADDITIVE - touch lightly.

{PRESERVATION_CONSTRAINTS}

THEMES: {themes}
MOTIFS: {motifs}
CENTRAL QUESTION: {central_question}
AESTHETIC: {aesthetic}

ADDITIVE TECHNIQUES (minimal intervention):
1. Add 1-2 sensory details per scene that echo motifs
2. Slip a thematic reference into existing dialogue naturally
3. Add a single symbolic object or observation
4. Plant one seed that pays off later
5. DO NOT rewrite entire paragraphs

Scene to enhance:
{content}

If scene already has good thematic resonance, leave mostly unchanged.
```

---

### Stage 14: CHAPTER_HOOKS

**Purpose:** Ensure every chapter ends compellingly.

**Model:** Claude | **Temperature:** 0.75

**Prompt Pattern:**
```
This is the final scene of Chapter {chapter}. Ensure powerful hook.

Only modify LAST 2-3 paragraphs. Keep everything else exactly.
Do NOT introduce AI tells.

Great chapter-ending hooks:
- Cliffhanger (danger, revelation imminent)
- Romantic tension peak (almost kiss, interrupted)
- Threat delivered
- Question raised
- Twist revealed
- Emotional gut-punch
- Decision with unknown consequences

Current scene:
{content}

Rewrite ONLY the last 2-3 paragraphs:
```

---

### Stage 15: DIALOGUE_POLISH

**Purpose:** Make dialogue authentic with subtext and character voice.

**Model:** Claude | **Temperature:** 0.75

**Prompt Pattern:**
```
Polish dialogue for maximum authenticity.

{PRESERVATION_CONSTRAINTS}

CHARACTER PROFILES: {characters}
DIALOGUE BANK: {dialogue_bank}
CULTURAL NOTES: {cultural_notes}

DIALOGUE QUALITY CHECKLIST:

1. ELIMINATE INFO-DUMP:
   - No explaining what both characters know
   - No "As you know..." constructions

2. ADD SUBTEXT:
   - Surface meaning AND hidden meaning
   - Deflection, hints, manipulation

3. CHARACTER DIFFERENTIATION:
   - Each character sounds distinct
   - Apply verbal tics from profiles

4. AUTHENTIC PATTERNS:
   - Interruptions (em-dashes—)
   - Trailing off...
   - Non-sequiturs
   - Misunderstandings

5. PHYSICAL BEATS:
   - Micro-actions between lines
   - Body language contradicting words

6. ELIMINATE TELLS:
   - Remove "he said angrily" (show in words)
   - Minimize adverbs on tags

Scene to polish:
{content}
```

---

### Stage 16: HUMAN_PASSES

**Purpose:** Remove AI-generated patterns and add authentic imperfection.

**Model:** Claude | **Temperature:** 0.6

**AI Tell Patterns to Remove:**
```python
AI_TELL_PATTERNS = [
    # Observation filters
    "I couldn't help but",
    "I found myself",
    "Something about [X] made me",
    "I noticed that",
    "I realized that",
    "I felt a sense of",

    # Weak transitions
    "suddenly",
    "in that moment",
    "before I knew it",

    # Purple prose
    "a whirlwind of emotions",
    "time seemed to stop",
    "electricity coursed through",
    "my heart skipped a beat",
    "butterflies in my stomach",

    # Hollow intensifiers
    "incredibly", "absolutely", "utterly",
    "completely", "totally", "truly",

    # Weak constructions
    "seemed to", "appeared to",
    "managed to", "proceeded to",
    "began to", "started to",

    # Telling
    "I felt [emotion]",
    "a mix of [emotion] and [emotion]"
]
```

**Humanization Principles:**
```
=== SENTENCE RHYTHM ===
- SHORT for punch. Impact. Emphasis.
- Long sentences that flow and build momentum
- Fragments. For punch.
- Vary: short-short-long creates different feel

=== IMPERFECTION AS AUTHENTICITY ===
- Incomplete thoughts that trail off...
- Interrupted dialogue with em-dashes—
- Thoughts that circle back
- Contradictory emotions in same moment

=== IMPLICITNESS OVER EXPLICITNESS ===
- If implied, don't write it out
- Let readers infer from action/dialogue
- Subtext matters more than text
- Trust reader to connect dots

=== EMOTIONAL UNPREDICTABILITY ===
- Sudden tonal shifts
- Vulnerability alternating with deflection
- Humor breaking tension
- Sarcasm, frustration emerging naturally
```

---

### Stage 17: VOICE_HUMANIZATION

**Purpose:** Add emotional texture and unpredictability.

**Model:** Claude | **Temperature:** 0.8

**Prompt Pattern:**
```
Enhance with emotional authenticity. ENHANCE, don't fully rewrite.

{PRESERVATION_CONSTRAINTS}

VOICE TARGETS:
Style: {writing_style}
Tone: {tone}
Influences: {influences}
POV: {pov}

EMOTIONAL UNPREDICTABILITY:
- Sudden tonal shifts (analytical to poetic)
- Brief bursts of unexpected emotion
- Vulnerability alternating with deflection
- Contradictory feelings in same moment

TONE SHIFTS:
- Change within paragraphs
- Sharp to soft, confident to doubtful
- Don't maintain one register throughout

FEWER TRANSITIONS:
- Remove "however", "furthermore"
- Let ideas flow by juxtaposition
- Abrupt can be more powerful

Scene to enhance:
{content}

BEFORE OUTPUTTING: Verify no AI tells from PRESERVATION CONSTRAINTS.
```

---

### Stage 18: PROSE_POLISH

**Purpose:** Final line-level improvements (STRICT PRESERVATION MODE).

**Model:** Claude | **Temperature:** 0.7

**Prompt Pattern:**
```
FINAL polish. Previous stages established voice.
SUBTLE REFINEMENT only - do NOT undo prior work.

{PRESERVATION_CONSTRAINTS}

=== STRICT PRESERVATION MODE ===
- DO NOT change working sentence structures
- DO NOT normalize character vocabulary
- DO NOT smooth intentional roughness/fragments
- DO NOT add flowery metaphors
- ONLY make improvements that are clearly better

RHETORICAL DEVICES TO CONSIDER:
- Tricolon: Three parallel elements
- Chiasmus: Mirrored structure
- Anaphora: Repeated starts
- Antithesis: Contrasting ideas
- Alliteration: For rhythm

LINE-BY-LINE CHECKLIST:
1. Word choice: Is every word precisely chosen?
2. Rhythm: Does sentence length vary?
3. Precision: Are images concrete?
4. Sound: Does it flow when read aloud?

MOST SENTENCES SHOULD STAY UNCHANGED.
If in doubt, leave alone.

Scene to polish:
{content}

BEFORE OUTPUTTING: Scan for AI tells.
```

---

### Stage 19: FINAL_DEAI

**Purpose:** Surgical removal of any remaining AI tells.

**Model:** GPT | **Temperature:** 0.3

**Surgical Replacements (No LLM needed):**
```python
SURGICAL_REPLACEMENTS = {
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
    "a whirlwind of emotions": "confusion",
    "time seemed to stop": "everything stilled",
    "electricity coursed through": "heat rushed through",
    "my heart skipped a beat": "my breath caught",
}
```

**Process:**
1. Apply regex replacements for known patterns
2. Clean double spaces from deletions
3. If tells remain, ask LLM to fix ONLY those sentences
4. Never rewrite entire paragraphs

---

### Stage 20: QUALITY_AUDIT

**Purpose:** Comprehensive validation with iteration trigger.

**Model:** Gemini | **Temperature:** 0.2

**Checks Performed:**
```python
audit_results = {
    "word_count": {
        "actual": total_words,
        "target": target_words,
        "percentage": word_pct,
        "status": "on_target" if >= 95 else "under"
    },

    "ai_tells": {
        "total_tells": count,
        "tells_per_1000_words": ratio,
        "acceptable": ratio < 2.0
    },

    "scene_lengths": [
        {"scene": "Ch1-S2", "actual": 650, "target": 800, "shortfall": 150}
    ],

    "spice_distribution": {
        "promised": 4,
        "distribution": {0: 50, 1: 15, 2: 8, 3: 4, 4: 2, 5: 1},
        "high_spice_count": 3
    },

    "chapter_hooks": [2, 5, 8],  # Chapters with weak hooks

    "issues": [...],
    "passed": True/False,
    "needs_iteration": True/False,
    "stages_to_rerun": ["human_passes", "scene_expansion"]
}
```

**Iteration Logic:**
```python
if word_pct < 80:
    stages_to_rerun.append("scene_expansion")

if ai_tells_per_1000 > 2.0:
    stages_to_rerun.append("human_passes")

# Max 2 iterations to prevent loops
if iteration_count >= 2:
    needs_iteration = False
```

---

### Stage 21: OUTPUT_VALIDATION

**Purpose:** Final format and structure check.

**Model:** GPT | **Temperature:** 0.2

**Validates:**
- Chapter numbering is sequential
- Scene ordering is correct
- No empty scenes
- Markdown structure is valid
- All required metadata present

---

## 7. Stage Ordering Rationale

```
PROSE REFINEMENT ORDER (Critical!):

1. motif_infusion     │ ADDITIVE: Adds thematic elements first
2. chapter_hooks      │ ADDITIVE: Modifies only chapter endings
                      │
                      ▼ All content now exists

3. dialogue_polish    │ POLISH: Catches all dialogue including additions
                      │
                      ▼ Dialogue finalized

4. human_passes       │ DE-AI: Removes AI tells from everything
5. voice_humanization │ TEXTURE: Adds emotional depth
                      │        (with preservation constraints)
                      │
                      ▼ Humanization complete

6. prose_polish       │ FINAL: Line-level only, strict preservation
7. final_deai         │ SAFETY NET: Surgical removal of any remaining
                      │
                      ▼ Ready for validation

8. quality_audit      → If fails: triggers iteration to specific stages
```

**Why This Order:**
1. **Additive stages BEFORE humanization** - Can't humanize what doesn't exist
2. **Dialogue polish AFTER additive** - So new dialogue gets polished
3. **Human passes AFTER all content** - Removes AI tells from final content
4. **Voice humanization with constraints** - Adds texture without re-introducing AI tells
5. **Prose polish in strict mode** - Only improves, never harms
6. **Final deai as safety net** - Catches anything that slipped through

---

## 8. Humanization System

### 8.1 PRESERVATION_CONSTRAINTS Constant

```python
PRESERVATION_CONSTRAINTS = """
=== CRITICAL: PRESERVATION CONSTRAINTS ===
You MUST NOT re-introduce any AI tell patterns that were previously removed.

AI TELLS TO AVOID (automatic rejection if found):
- "I couldn't help but", "I found myself", "Something about X made me"
- "I noticed that", "I realized that", "I felt a sense of"
- "suddenly", "in that moment", "before I knew it"
- "a whirlwind of emotions", "electricity coursed through"
- "my heart skipped a beat", "butterflies in my stomach"
- "incredibly", "absolutely", "utterly", "completely", "truly"
- "seemed to", "appeared to", "managed to", "proceeded to"
- "began to", "started to"
- "I felt [emotion]", "I was [emotion]"
- "a mix of [emotion] and [emotion]"

PROSE PATTERNS TO PRESERVE (do not overwrite):
- Short punchy sentences (keep them short)
- Sentence fragments (intentional, leave them)
- Em-dash interruptions (preserve these)
- Trailing off... (intentional, preserve)
- Contradictory emotions (keep the messiness)
- Character-specific vocabulary (don't normalize)

IF YOU ADD NEW TEXT, verify it:
- Contains no AI tells from the list above
- Matches the existing voice and rhythm
- Doesn't add flowery metaphors or purple prose
"""
```

### 8.2 Robust JSON Extraction

```python
def extract_json_robust(text: str, expect_array: bool = False) -> Any:
    """Handle common LLM JSON issues."""
    import re

    # Remove markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)

    # Find JSON structure
    if expect_array:
        match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
    else:
        match = re.search(r'\{.*\}', text, re.DOTALL)

    json_str = match.group(0) if match else text

    # Fix trailing commas
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return [{"raw": text}] if expect_array else {"raw": text}
```

---

## 9. Quality Assurance

### 9.1 Word Count Accuracy

```python
def count_words_accurate(text: str) -> int:
    """Count words excluding markdown formatting."""
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
    # Count
    words = [w for w in text.split() if w.strip()]
    return len(words)
```

### 9.2 AI Tell Detection

```python
def count_ai_tells(text: str) -> Dict:
    """Count AI tell patterns in text."""
    text_lower = text.lower()
    counts = {}
    total = 0

    for pattern in AI_TELL_PATTERNS:
        search = pattern.lower().replace("[x]", "").replace("[emotion]", "")
        count = text_lower.count(search)
        if count > 0:
            counts[pattern] = count
            total += count

    word_count = count_words_accurate(text)
    ratio = total / (word_count / 1000) if word_count > 0 else 0

    return {
        "total_tells": total,
        "tells_per_1000_words": round(ratio, 2),
        "patterns_found": counts,
        "acceptable": ratio < 2.0  # Less than 2 per 1000 words
    }
```

### 9.3 Config Validation

```python
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

def validate_config(config: Dict) -> Dict:
    errors = []
    warnings = []

    for field, expected_type in REQUIRED_CONFIG_FIELDS.items():
        if field not in config:
            errors.append(f"Missing required: {field}")
        elif not config[field]:
            errors.append(f"Empty required: {field}")

    for field in OPTIONAL_BUT_RECOMMENDED:
        if field not in config:
            warnings.append(f"Recommended missing: {field}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "completeness": len(config) / 15 * 100
    }
```

---

## 10. Export System

### 10.1 KDP Settings

```python
class KDPExporter:
    # 6x9 trim size (standard trade paperback)
    PAGE_WIDTH = Inches(6)
    PAGE_HEIGHT = Inches(9)

    # Margins
    MARGIN_TOP = Inches(0.75)
    MARGIN_BOTTOM = Inches(0.75)
    MARGIN_LEFT = Inches(0.75)
    MARGIN_RIGHT = Inches(0.5)
    MARGIN_GUTTER = Inches(0.25)

    # Typography
    BODY_FONT = "Garamond"
    BODY_SIZE = Pt(11)
    CHAPTER_FONT = "Garamond"
    CHAPTER_SIZE = Pt(24)

    # Paragraph formatting
    LINE_SPACING = 1.5
    FIRST_LINE_INDENT = Inches(0.3)
```

### 10.2 Document Structure

```
Title Page
  - Title (28pt, centered)
  - "A {Genre} Novel" subtitle
  - Page break

Copyright Page
  - Copyright notice
  - Disclaimer
  - Page break

Chapter 1
  - Heading (24pt, centered, page break before)
  - Scene 1 (first paragraph no indent)
  - Scene 2 (scene break: * * *)
  - ...

Chapter 2
  ...
```

---

## 11. Web Interface

### 11.1 API Endpoints

```
GET  /                       # Dashboard
GET  /seed                   # Seed form
GET  /projects               # Projects list
GET  /ideas                  # Ideas brainstorm

POST /api/v2/seed            # Create project from seed
POST /api/v2/generate/{name} # Start generation
GET  /api/v2/projects        # List all projects
GET  /api/v2/projects/{name} # Get project details
POST /api/v2/export/{name}   # Export to Word

WS   /ws                     # Real-time progress updates
```

### 11.2 WebSocket Messages

```javascript
// Progress update
{
  "type": "generation_progress",
  "project": "his-curvy-bratva-bride",
  "stage": "scene_drafting",
  "progress": 45,
  "message": "Drafting Chapter 3, Scene 2"
}

// Stage complete
{
  "type": "stage_complete",
  "stage": "scene_drafting",
  "duration": 234.5,
  "tokens": 45000
}

// Generation complete
{
  "type": "generation_complete",
  "project": "his-curvy-bratva-bride",
  "total_words": 62450,
  "total_cost": 12.34
}
```

---

## 12. Key Algorithms

### 12.1 Scene Length Tolerance

```python
def validate_scene_length(scene: Dict, target: int, tolerance: float = 0.8):
    actual = count_words_accurate(scene.get("content", ""))
    min_required = int(target * tolerance)

    return {
        "scene": f"Ch{scene['chapter']}-S{scene['scene_number']}",
        "actual": actual,
        "target": target,
        "min_required": min_required,
        "meets_target": actual >= min_required,
        "shortfall": max(0, min_required - actual)
    }
```

### 12.2 Genre-Aware Targets

```python
def calculate_targets(self):
    length_map = {
        "short (30k)": 30000,
        "standard (60k)": 60000,
        "long (90k)": 90000,
        "epic (120k)": 120000
    }

    genre_pacing = {
        "romance": 2200,
        "fantasy": 3500,
        "thriller": 2500,
        # ...
    }

    self.target_words = length_map.get(target_length, 60000)

    genre = self.config.get("genre", "").lower()
    self.words_per_chapter = 2500  # default
    for genre_key, words in genre_pacing.items():
        if genre_key in genre:
            self.words_per_chapter = words
            break

    self.target_chapters = self.target_words // self.words_per_chapter
    self.scenes_per_chapter = 3
    self.words_per_scene = self.words_per_chapter // 3
```

---

## 13. Reconstruction Checklist

If you need to rebuild the system from scratch:

### Phase 1: Core Infrastructure
- [ ] Create `prometheus_lib/llm/clients.py` with OpenAI, Gemini, Anthropic clients
- [ ] Add retry logic, rate limiting, timeout to clients
- [ ] Create `LLMResponse` dataclass
- [ ] Create `LLMError`, `AuthenticationError`, `RateLimitError`, `TimeoutError`

### Phase 2: Pipeline Framework
- [ ] Create `stages/pipeline.py`
- [ ] Define `PipelineState` dataclass
- [ ] Define `StageResult` dataclass
- [ ] Define `StageStatus` enum
- [ ] Create `PipelineOrchestrator` class
- [ ] Implement `STAGES` list (22 stages)
- [ ] Implement `STAGE_MODELS` dict
- [ ] Implement `STAGE_TEMPERATURES` dict

### Phase 3: Constants and Utilities
- [ ] Add `AI_TELL_PATTERNS` list
- [ ] Add `RHETORICAL_DEVICES` dict
- [ ] Add `ROMANCE_TROPES` dict
- [ ] Add `PRESERVATION_CONSTRAINTS` string
- [ ] Add `HUMANIZATION_PRINCIPLES` string
- [ ] Implement `count_words_accurate()`
- [ ] Implement `count_ai_tells()`
- [ ] Implement `validate_config()`
- [ ] Implement `extract_json_robust()`

### Phase 4: Stage Implementations
- [ ] Implement all 22 stage handler methods
- [ ] Add proper prompts to each stage
- [ ] Add temperature to each generate call
- [ ] Add max_tokens appropriate to each stage

### Phase 5: Iteration Logic
- [ ] Implement quality_audit with issue detection
- [ ] Add `needs_iteration` and `stages_to_rerun` logic
- [ ] Update `run()` to handle iteration
- [ ] Add 2-iteration maximum

### Phase 6: Export
- [ ] Create `export/docx_exporter.py`
- [ ] Implement `KDPExporter` class
- [ ] Set page size, margins, typography
- [ ] Implement title page, copyright page
- [ ] Implement chapter/scene formatting

### Phase 7: Web Interface
- [ ] Create `interfaces/web/app.py`
- [ ] Add FastAPI routes
- [ ] Add WebSocket for progress
- [ ] Add seed form
- [ ] Add projects list
- [ ] Add export endpoint

### Phase 8: Testing
- [ ] Create test project config
- [ ] Run single stage to verify
- [ ] Run full pipeline
- [ ] Verify export
- [ ] Check AI tell count < 2/1000 words

---

## Appendix: Sample Config

```yaml
project_name: his-curvy-bratva-bride
title: His Curvy Bratva Bride
genre: romance
synopsis: A plus-size art curator is forced into marriage with a ruthless Bratva boss to settle her father's debt, only to find herself worshipped and protected by the very monster she was warned against.
protagonist: Natalia Petrov, 22, Aspiring Curator
antagonist: Sergei Kozlov, rival faction leader
target_length: standard (60k)
setting: Modern NYC, Brighton Beach Russian enclave
tone: Dark, visceral, high-heat, opulent
themes: Body Worship, Safety in Danger, Morality of Violence
motifs: G-Wagon door thud, Russian Vodka, Corsets, Cold vs Heat, Red
writing_style: Dual POV (1st Person), punchy prose, mobile-optimized
influences: Sophie Lark, Katee Robert, The Sopranos
avoid: Weight loss arcs, cheating, weak groveling, cliffhanger endings

strategic_guidance:
  market_positioning: |
    Target: Dark Mafia Romance / Curvy Heroine
    Spice: 4/5 chili peppers
    Tropes: Touch Her and Die, forced proximity, praise kink

  beat_sheet: |
    opening_5pct: Natalia at gallery, insecurities established
    inciting_10pct: Father's debt, Alexei claims her
    midpoint_50pct: The Gala - violence, then first spice
    low_point_75pct: She thinks he's using her, runs
    climax_85pct: Warehouse rescue, he takes bullet
    resolution_95pct: She chooses him, HEA
```

---

**Document Version:** 2.0
**Total Lines:** ~2,000
**Purpose:** Complete system reconstruction reference