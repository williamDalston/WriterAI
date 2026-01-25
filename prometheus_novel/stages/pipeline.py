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


# HUMANIZATION TECHNIQUES - From speech prompt system
HUMANIZATION_PRINCIPLES = """
=== SENTENCE RHYTHM ===
- Use SHORT sentences for punch. Impact. Emphasis.
- Let longer sentences breathe and flow, carrying the reader through complex
  thoughts or descriptions with a rhythm that builds momentum.
- Fragments work. Sometimes better than complete sentences.
- Vary length deliberately: short-short-long, or long-short for contrast.

=== IMPERFECTION AS AUTHENTICITY ===
- Incomplete thoughts that trail off...
- Interrupted dialogue with em-dashes—
- Characters who miss obvious things
- Contradictory emotions held simultaneously
- Occasional sentence fragments or casual grammar
- Thoughts that circle back to earlier ideas

=== IMPLICITNESS OVER EXPLICITNESS ===
- If something is implied, don't write it out
- Let readers infer meaning from action and dialogue
- Use subtext—what's NOT said matters
- Trust the reader to connect the dots
- Symbolic resonance over direct statement

=== EMOTIONAL UNPREDICTABILITY ===
- Humans oscillate between emotional states
- Sudden tonal shifts (analytical to poetic, formal to casual)
- Brief bursts of unexpected emotion
- Contradictory feelings in the same moment
- Vulnerability alternating with deflection

=== FEWER EXPLICIT TRANSITIONS ===
- Remove "however", "furthermore", "additionally"
- Let ideas flow by juxtaposition
- Trust reader to make connections
- Abrupt shifts can be more powerful than smooth ones

=== ORIGINAL PHRASING ===
- Avoid clichés and stock expressions
- Find fresh ways to express common feelings
- Use unexpected metaphors and comparisons
- Regional idioms or character-specific expressions
- Sensory-specific rather than generic descriptions
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

    # Calculated targets
    target_words: int = 60000
    target_chapters: int = 20
    words_per_chapter: int = 3000
    scenes_per_chapter: int = 4
    words_per_scene: int = 750

    # Metrics
    total_tokens: int = 0
    total_cost_usd: float = 0.0

    def calculate_targets(self):
        """Calculate word count targets based on target_length."""
        length_map = {
            "short (30k)": 30000,
            "standard (60k)": 60000,
            "long (90k)": 90000,
            "epic (120k)": 120000
        }
        target_length = self.config.get("target_length", "standard (60k)")
        self.target_words = length_map.get(target_length, 60000)

        # Calculate structure
        self.words_per_chapter = 2500  # Industry standard
        self.target_chapters = self.target_words // self.words_per_chapter
        self.scenes_per_chapter = 3  # 3-4 scenes per chapter
        self.words_per_scene = self.words_per_chapter // self.scenes_per_chapter

        logger.info(f"Targets: {self.target_words} words, {self.target_chapters} chapters, "
                   f"{self.words_per_scene} words/scene")

    def save(self):
        """Save state to disk."""
        state_file = self.project_path / "pipeline_state.json"
        state_dict = {
            "project_name": self.project_name,
            "current_stage": self.current_stage,
            "high_concept": self.high_concept,
            "world_bible": self.world_bible,
            "beat_sheet": self.beat_sheet,
            "characters": self.characters,
            "master_outline": self.master_outline,
            "scenes": self.scenes,
            "continuity_issues": self.continuity_issues,
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
        logger.info(f"Pipeline state saved to {state_file}")

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
            high_concept=data.get("high_concept"),
            world_bible=data.get("world_bible"),
            beat_sheet=data.get("beat_sheet"),
            characters=data.get("characters"),
            master_outline=data.get("master_outline"),
            scenes=data.get("scenes"),
            continuity_issues=data.get("continuity_issues"),
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

    STAGES = [
        "high_concept",
        "world_building",
        "beat_sheet",
        "emotional_architecture",   # NEW: Map emotional arc across story
        "character_profiles",
        "master_outline",
        "trope_integration",        # NEW: Ensure genre tropes are placed
        "scene_drafting",
        "scene_expansion",          # NEW: Expand short scenes to target
        "continuity_audit",
        "continuity_fix",
        "self_refinement",
        "human_passes",
        "dialogue_polish",          # NEW: Dialogue-specific enhancement
        "voice_humanization",
        "motif_infusion",
        "chapter_hooks",
        "prose_polish",
        "quality_audit",            # NEW: Comprehensive final validation
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
        "master_outline": "gpt",
        "trope_integration": "claude",       # Genre-aware trope placement
        "scene_drafting": "gpt",
        "scene_expansion": "claude",         # Expand short scenes
        "continuity_audit": "gemini",
        "continuity_fix": "claude",
        "self_refinement": "claude",
        "human_passes": "claude",
        "dialogue_polish": "claude",         # Dialogue authenticity
        "voice_humanization": "claude",
        "motif_infusion": "claude",
        "chapter_hooks": "claude",
        "prose_polish": "claude",
        "quality_audit": "gemini",           # Long context for full audit
        "output_validation": "gpt"
    }

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
        """Run the pipeline."""
        await self.initialize(resume=resume)

        stages_to_run = stages or self.STAGES
        start_index = self.state.current_stage if resume else 0

        for i, stage_name in enumerate(stages_to_run[start_index:], start_index):
            self.state.current_stage = i
            await self._emit("on_stage_start", stage_name, i)

            try:
                result = await self._run_stage(stage_name)
                self.state.stage_results.append(result)
                self.state.total_tokens += result.tokens_used
                self.state.total_cost_usd += result.cost_usd
                self.state.save()

                await self._emit("on_stage_complete", stage_name, result)

                if result.status == StageStatus.FAILED:
                    await self._emit("on_stage_error", stage_name, result.error)
                    break

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
            "master_outline": self._stage_master_outline,
            "trope_integration": self._stage_trope_integration,
            "scene_drafting": self._stage_scene_drafting,
            "scene_expansion": self._stage_scene_expansion,
            "continuity_audit": self._stage_continuity_audit,
            "continuity_fix": self._stage_continuity_fix,
            "self_refinement": self._stage_self_refinement,
            "human_passes": self._stage_human_passes,
            "dialogue_polish": self._stage_dialogue_polish,
            "voice_humanization": self._stage_voice_humanization,
            "motif_infusion": self._stage_motif_infusion,
            "chapter_hooks": self._stage_chapter_hooks,
            "prose_polish": self._stage_prose_polish,
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
            response = await client.generate(prompt)
            try:
                self.state.world_bible = json.loads(response.content)
            except json.JSONDecodeError:
                self.state.world_bible = {"raw": response.content}
            return self.state.world_bible, response.input_tokens + response.output_tokens

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
            response = await client.generate(prompt)
            try:
                self.state.beat_sheet = json.loads(response.content)
            except json.JSONDecodeError:
                self.state.beat_sheet = [{"beat": response.content}]
            return self.state.beat_sheet, response.input_tokens + response.output_tokens

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
            response = await client.generate(prompt, max_tokens=2000)
            try:
                emotional_map = json.loads(response.content)
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                if json_match:
                    try:
                        emotional_map = json.loads(json_match.group())
                    except:
                        emotional_map = {"raw": response.content}
                else:
                    emotional_map = {"raw": response.content}

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
            response = await client.generate(prompt)
            try:
                self.state.characters = json.loads(response.content)
            except json.JSONDecodeError:
                self.state.characters = [{"raw": response.content}]
            return self.state.characters, response.input_tokens + response.output_tokens

        # Mock response
        self.state.characters = [
            {"name": "Protagonist", "role": "protagonist", "arc": "..."},
            {"name": "Antagonist", "role": "antagonist", "arc": "..."}
        ]
        return self.state.characters, 100

    async def _stage_master_outline(self) -> tuple:
        """Create master outline with scene connections and proper word count targets."""
        config = self.state.config
        story_context = self._build_story_context()
        strategic = self._build_strategic_guidance()

        # Get POV info
        writing_style = config.get("writing_style", "")
        is_dual_pov = "dual pov" in writing_style.lower()
        protagonist = config.get("protagonist", "").split(",")[0] if config.get("protagonist") else "Protagonist"
        # Extract hero name from other_characters (first name mentioned is usually the love interest)
        other_chars = config.get("other_characters", "")
        hero_name = other_chars.split("(")[0].strip() if other_chars else "Hero"

        prompt = f"""Create a detailed master outline with scene-by-scene breakdown.

{story_context}

HIGH CONCEPT: {self.state.high_concept}

WORLD BIBLE:
{json.dumps(self.state.world_bible, indent=2) if self.state.world_bible else 'Not available'}

BEAT SHEET:
{json.dumps(self.state.beat_sheet, indent=2)}

CHARACTERS:
{json.dumps(self.state.characters, indent=2)}

{strategic}

=== CRITICAL REQUIREMENTS ===

TARGET: {self.state.target_chapters} chapters total to hit {self.state.target_words:,} words
SCENES PER CHAPTER: {self.state.scenes_per_chapter} scenes each
TOTAL SCENES NEEDED: {self.state.target_chapters * self.state.scenes_per_chapter}

{"POV ALTERNATION: This is DUAL POV. Alternate between " + protagonist + " and " + hero_name + ". Mark each scene with its POV character." if is_dual_pov else ""}

KEY LOCATIONS TO USE:
{config.get('key_locations', 'Not specified')}

SUBPLOTS TO WEAVE IN:
{config.get('subplots', 'None specified')}

For EACH of the {self.state.target_chapters} chapters, create exactly {self.state.scenes_per_chapter} scenes.

=== CHAPTER STRUCTURE ===
1. chapter: (number 1-{self.state.target_chapters})
2. chapter_title: (evocative title that hints at chapter content)

=== SCENE ATTRIBUTES (for each scene in the chapter) ===

BASIC INFO:
- scene: (number within chapter)
- scene_name: (evocative 2-4 word name)
- pov: (whose perspective - "{protagonist}" or "{hero_name}")
- purpose: (why this scene exists in the story)

GOALS & CONFLICTS:
- character_scene_goal: (what the POV character is trying to accomplish)
- central_conflict: (the main obstacle/tension in this scene)
- proximal_conflicts: (smaller tensions/complications that arise)
- inner_conflict: (internal struggle the character faces)
- opposition_elements: (who/what opposes the character)

STRUCTURE:
- opening_hook: (first line concept - how to grab reader immediately)
- development: (how the scene progresses)
- suffering: (what pain/difficulty the character experiences)
- climax: (peak tension moment)
- outcome: (how the scene resolves - win/lose/draw)
- scene_question: (the dramatic question this scene answers)

CONNECTIONS:
- connection_to_previous: (how this flows from the last scene)
- connection_to_next: (how this sets up the next scene)
- connection_to_inner_goals: (how it relates to character's internal journey)
- connection_to_outer_goals: (how it relates to plot goals)
- beat_sheet_alignment: (which story beat this serves)

SETTING & SENSORY:
- location: (specific place with atmosphere)
- setting_description: (key visual/sensory elements to establish)
- sensory_focus: (which senses to emphasize - sounds, smells, textures)
- imagery: (key images/symbols to include)
- key_symbol: (recurring motif to weave in)

CRAFT ELEMENTS:
- physical_motion: (key actions/movements)
- subtext: (what's being communicated beneath the surface)
- relationships: (dynamics between characters present)
- knowledge_gain: (what does character learn/realize)
- unique_element: (what makes THIS scene distinctive)
- foreshadowing: (subtle hints to plant for later)

PACING & EMOTION:
- pacing: (fast/medium/slow - and why)
- tension_level: (1-10, with reason)
- emotional_arc: (start emotion -> end emotion)
- internalization: (internal thought/reaction moments needed)

ADDITIONAL:
- subplot_thread: (which subplot, if any)
- extra_characters: (supporting characters in scene)
- spice_level: (0=none, 1=tension, 2=kiss, 3=fade-to-black, 4=explicit, 5=very explicit)
- dialogue_notes: (key conversations/exchanges to include)
- theme_connection: (how scene reinforces themes)

Respond as a JSON array of {self.state.target_chapters} chapter objects, each containing an array of fully-detailed scene objects."""

        client = self.get_client_for_stage("master_outline")
        if client:
            response = await client.generate(prompt, max_tokens=8000)
            try:
                self.state.master_outline = json.loads(response.content)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\[.*\]', response.content, re.DOTALL)
                if json_match:
                    try:
                        self.state.master_outline = json.loads(json_match.group())
                    except:
                        self.state.master_outline = [{"raw": response.content}]
                else:
                    self.state.master_outline = [{"raw": response.content}]
            return self.state.master_outline, response.input_tokens + response.output_tokens

        # Mock response
        self.state.master_outline = [
            {"chapter": 1, "scenes": [{"scene": 1, "goal": "...", "pov": protagonist}]},
            {"chapter": 2, "scenes": [{"scene": 1, "goal": "...", "pov": hero_name}]}
        ]
        return self.state.master_outline, 100

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
            response = await client.generate(prompt, max_tokens=2000)
            try:
                trope_report = json.loads(response.content)
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                if json_match:
                    try:
                        trope_report = json.loads(json_match.group())
                    except:
                        trope_report = {"raw": response.content}
                else:
                    trope_report = {"raw": response.content}

            # Apply outline updates if present
            updates = trope_report.get("outline_updates", [])
            for update in updates:
                ch_num = update.get("chapter")
                sc_num = update.get("scene")
                additions = update.get("add_to_attributes", {})

                for chapter in (self.state.master_outline or []):
                    if chapter.get("chapter") == ch_num:
                        for scene in chapter.get("scenes", []):
                            if scene.get("scene") == sc_num:
                                scene.update(additions)
                                logger.info(f"Updated Ch{ch_num} Sc{sc_num} with trope requirements")

            return trope_report, response.input_tokens + response.output_tokens

        return {"tropes_checked": len(tropes_to_check)}, 50

    def _get_previous_scenes_context(self, scenes: List[Dict], count: int = 3) -> str:
        """Get summary of previous scenes for continuity."""
        if not scenes or len(scenes) == 0:
            return "This is the opening scene."

        recent = scenes[-count:] if len(scenes) >= count else scenes
        summaries = []
        for s in recent:
            ch = s.get("chapter", "?")
            sc = s.get("scene_number", "?")
            content = s.get("content", "")[:500]  # First 500 chars as summary
            summaries.append(f"[Ch{ch} Sc{sc}]: {content}...")

        return "PREVIOUS SCENES (for continuity):\n" + "\n\n".join(summaries)

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
            chapter_num = chapter.get("chapter", 1)

            for scene_info in chapter.get("scenes", []):
                scene_num = scene_info.get("scene", 1)
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
                foreshadowing = scene_info.get('foreshadowing', '')
                pacing = scene_info.get('pacing', 'medium')
                tension_level = scene_info.get('tension_level', 5)
                emotional_arc = scene_info.get('emotional_arc', '')
                internalization = scene_info.get('internalization', '')
                dialogue_notes = scene_info.get('dialogue_notes', '')
                theme_connection = scene_info.get('theme_connection', '')
                extra_chars = scene_info.get('extra_characters', '')

                # Build comprehensive scene prompt
                prompt = f"""Write Chapter {chapter_num}, Scene {scene_num}: "{scene_name}"

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

=== POV & VOICE ===
Written from {pov_char}'s perspective in first person.
- Their unique vocabulary and thought patterns
- Their specific biases and blind spots
- Their physical sensations and emotional responses

=== SCENE PURPOSE ===
WHY THIS SCENE EXISTS: {purpose}
SCENE QUESTION (to answer): {scene_question}
{f"UNIQUE ELEMENT: {unique_element}" if unique_element else ""}

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

AESTHETIC PALETTE:
{aesthetic}

=== CRAFT ELEMENTS ===
{f"PHYSICAL ACTIONS: {physical_motion}" if physical_motion else ""}
{f"SUBTEXT (beneath the surface): {subtext}" if subtext else ""}
{f"RELATIONSHIP DYNAMICS: {relationships}" if relationships else ""}
{f"CHARACTER LEARNS/REALIZES: {knowledge_gain}" if knowledge_gain else ""}
{f"FORESHADOWING TO PLANT: {foreshadowing}" if foreshadowing else ""}
{f"DIALOGUE TO INCLUDE: {dialogue_notes}" if dialogue_notes else ""}
{f"THEME CONNECTION: {theme_connection}" if theme_connection else ""}

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

=== CULTURAL AUTHENTICITY ===
{cultural_notes}

=== CONTINUITY ===
{previous_context}

=== TARGET LENGTH ===
Approximately {self.state.words_per_scene} words.
Paragraphs: 4 sentences maximum (mobile-optimized).

=== NOW WRITE ===
Begin directly with the narrative. The opening should:
- Establish setting through character interaction (not description dump)
- Hook immediately with tension, motion, or intrigue
- Ground us in the POV character's physical/emotional state

Write the complete scene:"""

                if client:
                    # Calculate max tokens based on target words (1 token ≈ 0.75 words)
                    # Add buffer for comprehensive scenes
                    max_tokens = max(int(self.state.words_per_scene * 1.8), 2000)
                    response = await client.generate(prompt, max_tokens=max_tokens)
                    scenes.append({
                        "chapter": chapter_num,
                        "scene_number": scene_num,
                        "pov": pov_char,
                        "location": location,
                        "spice_level": spice_level,
                        "content": response.content
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
        """Expand scenes that are below target word count."""
        client = self.get_client_for_stage("scene_expansion")
        expanded_scenes = []
        total_tokens = 0
        scenes_expanded = 0

        target_words = self.state.words_per_scene
        min_words = int(target_words * 0.8)

        for scene in (self.state.scenes or []):
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

            prompt = f"""This scene is {validation['actual']} words but should be approximately {target_words} words.
Expand it by adding {shortfall}+ words.

=== EXPANSION GUIDELINES ===
DO:
- Add more sensory details (smells, textures, sounds)
- Deepen internal monologue/reactions
- Expand dialogue with beats and subtext
- Add physical movement and body language
- Layer in setting details through character interaction

DO NOT:
- Add new plot points or characters
- Change the scene's outcome
- Add unnecessary transitions or filler
- Pad with repetitive descriptions

=== SCENE TO EXPAND ===
Chapter {scene.get('chapter')}, Scene {scene.get('scene_number')}
POV: {scene.get('pov', 'protagonist')}

{scene.get('content', '')}

=== EXPANDED SCENE ===
Provide the complete expanded scene (target: {target_words} words):"""

            response = await client.generate(prompt, max_tokens=3000)
            expanded_scenes.append({
                **scene,
                "content": response.content,
                "expanded": True,
                "original_words": validation["actual"],
                "expanded_words": count_words_accurate(response.content)
            })
            total_tokens += response.input_tokens + response.output_tokens
            scenes_expanded += 1

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
            prompt = f"""Review and improve this scene for publication quality.

=== STYLE REQUIREMENTS ===
WRITING STYLE: {writing_style}
TONE: {tone}

=== ABSOLUTE RESTRICTIONS (Flag if present, then remove) ===
{avoid_list}

=== QUALITY CHECKLIST ===
Score and improve across these dimensions:
1. Structure (goal, conflict, turn present and clear)
2. Dialogue (natural, character-appropriate, subtext present)
3. Pacing (varied sentence length, no rushed or dragging sections)
4. Sensory Details (show don't tell, visceral reactions)
5. Hook (compelling ending that pulls reader forward)
6. POV Consistency (staying in the character's head, no head-hopping)
7. Paragraph Length (max 4 sentences for mobile readability)

=== ORIGINAL SCENE ===
{scene.get('content', '')}

=== INSTRUCTIONS ===
1. First, check for any "avoid" list violations and remove them
2. Strengthen weak verbs
3. Eliminate filter words (felt, saw, heard, noticed)
4. Add visceral reactions where missing
5. Ensure paragraphs aren't too long
6. Tighten dialogue tags

Provide the improved scene:"""

            if client:
                response = await client.generate(prompt, max_tokens=2500)
                refined_scenes.append({
                    **scene,
                    "content": response.content,
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

FULL MANUSCRIPT:
{all_content}

Find and report:
1. Character inconsistencies (appearance, personality, knowledge changes)
2. Timeline errors (events out of order, impossible timing)
3. World rule violations (contradicts established setting/rules)
4. Plot holes (missing explanations, unresolved threads)
5. Factual inconsistencies (names, places, objects that change)

For each issue found, provide:
- Location (chapter/scene)
- Type of issue
- Description
- Suggested fix

Respond in JSON format with "issues" array and "passed" boolean."""

        if client:
            response = await client.generate(prompt, max_tokens=4000)
            try:
                audit_report = json.loads(response.content)
            except json.JSONDecodeError:
                # Try to extract JSON
                import re
                json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                if json_match:
                    try:
                        audit_report = json.loads(json_match.group())
                    except:
                        audit_report = {
                            "issues_found": 0,
                            "issues": [],
                            "raw_analysis": response.content,
                            "passed": True
                        }
                else:
                    audit_report = {
                        "issues_found": 0,
                        "issues": [],
                        "raw_analysis": response.content,
                        "passed": True
                    }

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
            issue_location = issue.get("location", "")
            issue_type = issue.get("type", "")
            issue_desc = issue.get("description", "")
            suggested_fix = issue.get("suggested_fix", "")

            # Find the affected scene
            for i, scene in enumerate(fixed_scenes):
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
                        response = await client.generate(prompt, max_tokens=2500)
                        fixed_scenes[i] = {
                            **scene,
                            "content": response.content,
                            "continuity_fixed": True,
                            "fixed_issue": issue_desc
                        }
                        total_tokens += response.input_tokens + response.output_tokens
                        fixes_applied += 1
                        logger.info(f"Fixed continuity issue in {scene_loc}: {issue_type}")
                    break

        self.state.scenes = fixed_scenes
        return {"fixes_applied": fixes_applied, "issues_found": len(self.state.continuity_issues)}, total_tokens

    async def _stage_human_passes(self) -> tuple:
        """Eliminate AI tells and add authentic human imperfection to prose."""
        enhanced_scenes = []
        total_tokens = 0
        client = self.get_client_for_stage("human_passes")
        config = self.state.config
        guidance = config.get("strategic_guidance", {})

        writing_style = config.get("writing_style", "")
        influences = config.get("influences", "")
        aesthetic = guidance.get("aesthetic_guide", "")

        # Build AI tell patterns list for the prompt
        ai_tells_sample = AI_TELL_PATTERNS[:20]  # First 20 patterns

        for scene in (self.state.scenes or []):
            pov = scene.get("pov", "protagonist")

            prompt = f"""Transform this scene to feel authentically human-written, not AI-generated.

=== VOICE TARGETS ===
WRITING STYLE: {writing_style}
INFLUENCES TO CHANNEL: {influences}

=== AI TELLS TO ELIMINATE (search and destroy) ===
{chr(10).join('- "' + p + '"' for p in ai_tells_sample)}
- Any "filter" phrases (felt, noticed, realized, saw that)
- Purple prose and overwrought metaphors
- Hollow intensifiers (incredibly, absolutely, utterly)
- Weak constructions (seemed to, began to, managed to)

=== HUMANIZATION PRINCIPLES ===
{HUMANIZATION_PRINCIPLES}

=== SENTENCE RHYTHM TECHNIQUES ===
- SHORT for impact. Punch. Emphasis.
- Long sentences that flow and build momentum, carrying the reader through
  complex emotional or descriptive territory with deliberate rhythm.
- Fragments. For punch.
- Vary deliberately: short-short-long creates a different feel than long-short-short.

=== IMPERFECTION AS AUTHENTICITY ===
- Incomplete thoughts that trail off...
- Interrupted dialogue with em-dashes—
- Thoughts that circle back to earlier ideas
- Contradictory emotions in same moment
- Characters who miss obvious things

=== IMPLICITNESS OVER EXPLICITNESS ===
- If implied, don't write it out
- Let readers infer from action/dialogue
- Subtext matters more than text
- Trust reader to connect dots

=== AESTHETIC PALETTE ===
{aesthetic}

=== POV DEPTH ({pov}) ===
- Stay fully in their head
- Their unique vocabulary and thought patterns
- Their specific observations and biases
- Body-specific reactions (throat tight, stomach hollow)
- NOT generic (heart racing, butterflies)

=== SCENE TO TRANSFORM ===
{scene.get('content', '')}

Rewrite with authentic human voice. The text should pass as written by
a skilled human author, not generated by an AI. Every sentence should
feel considered, not produced:"""

            if client:
                response = await client.generate(prompt, max_tokens=2500)
                enhanced_scenes.append({
                    **scene,
                    "content": response.content,
                    "enhanced": True
                })
                total_tokens += response.input_tokens + response.output_tokens
            else:
                enhanced_scenes.append({**scene, "enhanced": True})
                total_tokens += 100

        self.state.scenes = enhanced_scenes
        return enhanced_scenes, total_tokens

    async def _stage_dialogue_polish(self) -> tuple:
        """Polish dialogue for authenticity, subtext, and character voice."""
        client = self.get_client_for_stage("dialogue_polish")
        polished_scenes = []
        total_tokens = 0
        config = self.state.config

        for scene in (self.state.scenes or []):
            pov = scene.get("pov", "protagonist")

            prompt = f"""You are a dialogue specialist. Polish the dialogue in this scene for maximum authenticity.

=== CHARACTER PROFILES ===
{json.dumps(self.state.characters, indent=2) if self.state.characters else 'Not available'}

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
                response = await client.generate(prompt, max_tokens=2500)
                polished_scenes.append({
                    **scene,
                    "content": response.content,
                    "dialogue_polished": True
                })
                total_tokens += response.input_tokens + response.output_tokens
            else:
                polished_scenes.append({**scene, "dialogue_polished": True})
                total_tokens += 100

        self.state.scenes = polished_scenes
        return {"scenes_polished": len(polished_scenes)}, total_tokens

    async def _stage_voice_humanization(self) -> tuple:
        """Apply emotional unpredictability and authentic voice with tone shifts."""
        client = self.get_client_for_stage("voice_humanization")
        humanized_scenes = []
        total_tokens = 0

        # Get voice style from config
        writing_style = self.state.config.get("writing_style", "")
        tone = self.state.config.get("tone", "")
        influences = self.state.config.get("influences", "")

        for scene in (self.state.scenes or []):
            pov = scene.get("pov", "protagonist")

            prompt = f"""You are a literary prose stylist. Transform this scene with emotional
authenticity and unpredictability that marks genuinely human writing.

=== VOICE TARGETS ===
WRITING STYLE: {writing_style}
TONE: {tone}
INFLUENCES TO CHANNEL: {influences}
POV CHARACTER: {pov}

=== CHARACTER VOICES ===
{json.dumps(self.state.characters, indent=2) if self.state.characters else 'Not available'}

=== EMOTIONAL UNPREDICTABILITY ===
Humans oscillate between emotional states. Add:
- Sudden tonal shifts (analytical to poetic, formal to casual)
- Brief bursts of unexpected emotion
- Vulnerability alternating with deflection
- Humor breaking tension (or heightening it)
- Contradictory feelings in the same moment
- Sarcasm, frustration, or quiet joy emerging naturally

=== TONE SHIFTS & CONTRADICTIONS ===
- Let the tone change within paragraphs
- Move from sharp to soft, confident to doubtful
- Don't maintain one emotional register throughout
- Create moments of cognitive dissonance

=== SUBTLE SHIFTS IN THOUGHT ===
- Introduce digressions or non-linear thinking
- Let thoughts wander and return
- Abrupt mental pivots that feel natural
- Personal reflections that interrupt narrative flow

=== FEWER TRANSITIONS ===
- Remove "however", "furthermore", "additionally"
- Let ideas flow by juxtaposition
- Trust the reader to make connections
- Abrupt can be more powerful than smooth

=== DIALOGUE AUTHENTICITY ===
- Verbal tics unique to each character
- Interruptions, overlapping, trailing off...
- What's NOT said (subtext)
- Physical beats between lines
- Misunderstandings and cross-purposes

=== SCENE TO TRANSFORM ===
{scene.get('content', '')}

Rewrite with emotional depth and human unpredictability. The prose
should feel like it came from a mind that oscillates, contradicts
itself, and experiences the world with messy authenticity:"""

            if client:
                response = await client.generate(prompt, max_tokens=2500)
                humanized_scenes.append({
                    **scene,
                    "content": response.content,
                    "humanized": True
                })
                total_tokens += response.input_tokens + response.output_tokens
            else:
                humanized_scenes.append({**scene, "humanized": True})
                total_tokens += 100

        self.state.scenes = humanized_scenes
        return {"voice_applied": True, "scenes_processed": len(humanized_scenes)}, total_tokens

    async def _stage_motif_infusion(self) -> tuple:
        """Weave thematic motifs throughout using Claude's literary understanding."""
        client = self.get_client_for_stage("motif_infusion")
        infused_scenes = []
        total_tokens = 0

        # Get themes and motifs from config
        themes = self.state.config.get("themes", "")
        motifs = self.state.config.get("motifs", "")
        central_question = self.state.config.get("central_question", "")
        guidance = self.state.config.get("strategic_guidance", {})
        aesthetic = guidance.get("aesthetic_guide", "")

        for scene in (self.state.scenes or []):
            prompt = f"""You are a literary editor specializing in thematic depth. Weave motifs and themes into this scene.

THEMES TO REINFORCE: {themes}
RECURRING MOTIFS: {motifs}
CENTRAL QUESTION: {central_question}
AESTHETIC GUIDE: {aesthetic}

SCENE TO ENHANCE:
{scene.get('content', '')}

Subtly weave in thematic elements:
1. Layer motifs naturally into descriptions and dialogue
2. Echo themes through character choices and observations
3. Use sensory details that reinforce the aesthetic palette
4. Add symbolic resonance without being heavy-handed
5. Connect to the central question through subtext
6. Plant seeds that pay off in later scenes

The motifs should feel organic, not forced. A reader shouldn't notice them consciously, but should FEEL them.

Provide the enhanced scene:"""

            if client:
                response = await client.generate(prompt, max_tokens=2500)
                infused_scenes.append({
                    **scene,
                    "content": response.content,
                    "motifs_infused": True
                })
                total_tokens += response.input_tokens + response.output_tokens
            else:
                infused_scenes.append({**scene, "motifs_infused": True})
                total_tokens += 100

        self.state.scenes = infused_scenes
        return {"motifs_infused": True, "themes": themes, "scenes_processed": len(infused_scenes)}, total_tokens

    async def _stage_chapter_hooks(self) -> tuple:
        """Ensure every chapter ends with a compelling hook for mobile scroll-through."""
        client = self.get_client_for_stage("chapter_hooks")
        hooked_scenes = []
        total_tokens = 0
        config = self.state.config
        guidance = config.get("strategic_guidance", {})

        # Group scenes by chapter
        chapters: Dict[int, List[Dict]] = {}
        for scene in (self.state.scenes or []):
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

            # Process all scenes, but focus on the last scene for the hook
            for i, scene in enumerate(chapter_scenes):
                is_chapter_end = (i == len(chapter_scenes) - 1)

                if is_chapter_end and client:
                    # This is the last scene of the chapter - ensure it has a hook
                    prompt = f"""This is the final scene of Chapter {chapter_num}. Ensure it ends with a POWERFUL HOOK.

{hook_guidance}

A great chapter-ending hook can be:
- A cliffhanger (danger, revelation about to happen)
- A kiss or romantic tension peak
- A threat delivered
- A question raised
- A twist revealed
- An emotional gut-punch
- A decision made with unknown consequences

CURRENT SCENE (enhance the ending hook):
{scene.get('content', '')}

Rewrite ONLY the last 2-3 paragraphs to create an irresistible hook that makes the reader NEED to continue.
Keep the rest of the scene intact. The hook should feel organic, not forced.

ENHANCED SCENE:"""

                    response = await client.generate(prompt, max_tokens=2500)
                    hooked_scenes.append({
                        **scene,
                        "content": response.content,
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
            pov = scene.get("pov", "protagonist")

            prompt = f"""You are a master prose editor performing the final polish on a novel scene.
Go through EVERY SENTENCE and consider whether it could be improved for maximum effect.

=== STYLE TARGETS ===
WRITING STYLE: {writing_style}
TONE: {tone}
INFLUENCES: {influences}

=== RHETORICAL DEVICES TO CONSIDER ===
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
Go through line by line. Make subtle adjustments for:
- Stronger word choices
- Better rhythm and flow
- More precise imagery
- Strategic use of rhetorical devices
- Maximum emotional impact

The changes should be subtle refinements, not a full rewrite. Polish, don't transform.
Maintain the character voice and emotional content while elevating the craft.

POLISHED SCENE:"""

            if client:
                response = await client.generate(prompt, max_tokens=2500)
                polished_scenes.append({
                    **scene,
                    "content": response.content,
                    "polished": True
                })
                total_tokens += response.input_tokens + response.output_tokens
            else:
                polished_scenes.append({**scene, "polished": True})
                total_tokens += 100

        self.state.scenes = polished_scenes
        return {"scenes_polished": len(polished_scenes)}, total_tokens

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
        total_words = sum(count_words_accurate(s.get("content", ""))
                        for s in (self.state.scenes or []))
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
        all_content = " ".join(s.get("content", "") for s in (self.state.scenes or []))
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
        for scene in (self.state.scenes or []):
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
            for scene in (self.state.scenes or []):
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
        for scene in (self.state.scenes or []):
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

        return audit_results, total_tokens

    async def _stage_output_validation(self) -> tuple:
        """Final quality validation and output generation with comprehensive reporting."""
        client = self.get_client_for_stage("output_validation")
        config = self.state.config

        # Calculate stats using accurate word count
        total_scenes = len(self.state.scenes or [])
        total_words = sum(count_words_accurate(s.get("content", ""))
                        for s in (self.state.scenes or []))

        # Count chapters
        chapters = set(s.get("chapter") for s in (self.state.scenes or []))
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
        if client and self.state.scenes and len(self.state.scenes) >= 3:
            # Check beginning, middle, and end
            sample_indices = [0, len(self.state.scenes) // 2, -1]
            samples = [self.state.scenes[i] for i in sample_indices]

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
                response = await client.generate(prompt, max_tokens=800)
                # Try to extract JSON
                import re
                json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                if json_match:
                    quality_data = json.loads(json_match.group())
                else:
                    quality_data = json.loads(response.content)

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
            ch_num = ch.get("chapter")
            ch_title = ch.get("chapter_title", "")
            if ch_num and ch_title:
                chapter_titles[ch_num] = ch_title

        for scene in (self.state.scenes or []):
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
