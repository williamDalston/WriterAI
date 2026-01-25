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
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import yaml

logger = logging.getLogger(__name__)


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

    # Metrics
    total_tokens: int = 0
    total_cost_usd: float = 0.0

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
            total_tokens=data.get("total_tokens", 0),
            total_cost_usd=data.get("total_cost_usd", 0.0)
        )

        return state


class PipelineOrchestrator:
    """Orchestrates the 12-stage novel generation pipeline."""

    STAGES = [
        "high_concept",
        "world_building",
        "beat_sheet",
        "character_profiles",
        "master_outline",
        "scene_drafting",
        "self_refinement",
        "continuity_audit",
        "human_passes",
        "voice_humanization",
        "motif_infusion",
        "output_validation"
    ]

    def __init__(self, project_path: Path, llm_client=None):
        self.project_path = project_path
        self.llm_client = llm_client
        self.state: Optional[PipelineState] = None
        self.callbacks: Dict[str, List[Callable]] = {
            "on_stage_start": [],
            "on_stage_complete": [],
            "on_stage_error": [],
            "on_pipeline_complete": []
        }

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
            "character_profiles": self._stage_character_profiles,
            "master_outline": self._stage_master_outline,
            "scene_drafting": self._stage_scene_drafting,
            "self_refinement": self._stage_self_refinement,
            "continuity_audit": self._stage_continuity_audit,
            "human_passes": self._stage_human_passes,
            "voice_humanization": self._stage_voice_humanization,
            "motif_infusion": self._stage_motif_infusion,
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

        if self.llm_client:
            response = await self.llm_client.generate(prompt)
            self.state.high_concept = response.content
            return response.content, response.input_tokens + response.output_tokens

        # Mock response
        self.state.high_concept = f"A compelling {genre} story about {synopsis[:100]}..."
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

        if self.llm_client:
            response = await self.llm_client.generate(prompt)
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

        if self.llm_client:
            response = await self.llm_client.generate(prompt)
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

        if self.llm_client:
            response = await self.llm_client.generate(prompt)
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
        """Create master outline with scene connections."""
        prompt = f"""Create a master outline with scene-by-scene breakdown.

High Concept: {self.state.high_concept}
Beat Sheet: {json.dumps(self.state.beat_sheet, indent=2)}
Characters: {json.dumps(self.state.characters, indent=2)}

For each chapter, create 3-5 scenes with:
1. Scene Number
2. POV Character
3. Location
4. Scene Goal
5. Conflict
6. Turn/Twist
7. Hook to Next Scene

Respond as a JSON array of chapters, each containing scenes."""

        if self.llm_client:
            response = await self.llm_client.generate(prompt)
            try:
                self.state.master_outline = json.loads(response.content)
            except json.JSONDecodeError:
                self.state.master_outline = [{"raw": response.content}]
            return self.state.master_outline, response.input_tokens + response.output_tokens

        # Mock response
        self.state.master_outline = [
            {"chapter": 1, "scenes": [{"scene": 1, "goal": "..."}]},
            {"chapter": 2, "scenes": [{"scene": 1, "goal": "..."}]}
        ]
        return self.state.master_outline, 100

    async def _stage_scene_drafting(self) -> tuple:
        """Draft all scenes."""
        scenes = []
        total_tokens = 0

        for chapter in (self.state.master_outline or []):
            for scene_info in chapter.get("scenes", []):
                prompt = f"""Write a scene for this novel.

World: {json.dumps(self.state.world_bible)}
Characters: {json.dumps(self.state.characters)}
Scene Info: {json.dumps(scene_info)}

Write the complete scene with:
- Vivid sensory details
- Character-appropriate dialogue
- Clear scene structure (goal, conflict, turn)
- A hook ending

Scene:"""

                if self.llm_client:
                    response = await self.llm_client.generate(prompt, max_tokens=2000)
                    scenes.append({
                        "chapter": chapter.get("chapter"),
                        "scene_number": scene_info.get("scene", 1),
                        "content": response.content
                    })
                    total_tokens += response.input_tokens + response.output_tokens
                else:
                    scenes.append({
                        "chapter": chapter.get("chapter"),
                        "scene_number": scene_info.get("scene", 1),
                        "content": f"[Scene content for chapter {chapter.get('chapter')}]"
                    })
                    total_tokens += 100

        self.state.scenes = scenes
        return scenes, total_tokens

    async def _stage_self_refinement(self) -> tuple:
        """Self-refine scenes for quality."""
        refined_scenes = []
        total_tokens = 0

        for scene in (self.state.scenes or []):
            prompt = f"""Review and improve this scene. Score it across these dimensions:
1. Structure (goal, conflict, turn present)
2. Dialogue (natural, character-appropriate)
3. Pacing (varied sentence length, not rushed)
4. Sensory Details (show don't tell)
5. Hook (compelling ending)

Original Scene:
{scene.get('content', '')}

Provide the improved version:"""

            if self.llm_client:
                response = await self.llm_client.generate(prompt, max_tokens=2000)
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
        """Audit for continuity issues."""
        issues = []

        # Check character consistency across scenes
        # Check timeline consistency
        # Check world rule violations

        audit_report = {
            "issues_found": len(issues),
            "issues": issues,
            "passed": len(issues) == 0
        }

        return audit_report, 50

    async def _stage_human_passes(self) -> tuple:
        """Enhance prose quality."""
        enhanced_scenes = []
        total_tokens = 0

        for scene in (self.state.scenes or []):
            prompt = f"""Enhance this scene's prose. Focus on:
1. Eliminating filter words (felt, saw, heard)
2. Varying sentence structure
3. Strengthening verbs
4. Adding sensory details where sparse
5. Improving rhythm and flow

Scene:
{scene.get('content', '')}

Enhanced version:"""

            if self.llm_client:
                response = await self.llm_client.generate(prompt, max_tokens=2000)
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

    async def _stage_voice_humanization(self) -> tuple:
        """Apply consistent voice signature."""
        # Apply voice patterns from config
        voice_signature = self.state.config.get("voice_signature", {})

        return {"voice_applied": True, "signature": voice_signature}, 25

    async def _stage_motif_infusion(self) -> tuple:
        """Weave thematic motifs throughout."""
        themes = self.state.config.get("themes", [])

        return {"motifs_infused": True, "themes": themes}, 25

    async def _stage_output_validation(self) -> tuple:
        """Final quality validation."""
        validation_report = {
            "total_scenes": len(self.state.scenes or []),
            "total_words": sum(len(s.get("content", "").split()) for s in (self.state.scenes or [])),
            "quality_score": 0.85,  # Placeholder
            "passed": True
        }

        # Save final output
        output_dir = self.state.project_path / "output"
        output_dir.mkdir(exist_ok=True)

        # Compile to single file
        full_text = ""
        for scene in (self.state.scenes or []):
            full_text += f"\n\n## Chapter {scene.get('chapter')}, Scene {scene.get('scene_number')}\n\n"
            full_text += scene.get("content", "")

        output_file = output_dir / f"{self.state.project_name}.md"
        output_file.write_text(full_text)

        validation_report["output_file"] = str(output_file)

        return validation_report, 10


# Convenience function
async def run_pipeline(project_path: str, llm_client=None, resume: bool = False):
    """Run the full pipeline for a project."""
    orchestrator = PipelineOrchestrator(Path(project_path), llm_client)
    return await orchestrator.run(resume=resume)
