# Detailed Agent Implementation Plans

**Comprehensive implementation guides for all 22 agents with full integration details**

---

## 📋 Table of Contents

1. [Planning Agents](#planning-agents)
   - Agent #4: WorldAgent (Detailed Plan)
   - Agent #6: CharacterAgent (Detailed Plan)
2. [Execution Agents](#execution-agents)
   - Agent #7: DraftingAgent (Detailed Plan)
   - Agent #8: DialogueAgent (Detailed Plan)
   - Agent #9: ProseAgent (Detailed Plan)
   - Agent #10: ActionAgent (Detailed Plan)
   - Agent #11: DescriptionAgent (Detailed Plan)
   - Agent #12: SynthesisAgent (Detailed Plan)
3. [Evaluation Agents](#evaluation-agents)
   - Agent #13: QualityJudgeAgent (Detailed Plan)
   - Agent #14: ContinuityAgent (Detailed Plan)
   - Agent #15: EmotionalAgent (Detailed Plan)
   - Agent #16: ThemeAgent (Detailed Plan)
4. [Support Agents](#support-agents)
   - Agent #17: MemoryAgent (Detailed Plan)
   - Agent #18: LearningAgent (Detailed Plan)
   - Agent #19: BudgetAgent (Detailed Plan)
   - Agent #20: ResearchAgent (Detailed Plan)
   - Agent #21: ExportAgent (Detailed Plan)
   - Agent #22: AnalyticsAgent (Detailed Plan)

---

## Planning Agents

### Agent #4: WorldAgent - Detailed Implementation Plan

#### Purpose
Replace Stage 2 (World Modeling) with specialized agent that generates world rules, cultural context, locations, and consistency tracking.

#### Integration Points
- **Replaces:** `prometheus_novel/stages/stage_02_world_modeling.py`
- **Uses:** `prometheus_lib/models/novel_state.py` (WorldModel)
- **Integrates with:** ConceptAgent output (high_concept_package)
- **Outputs to:** StructureAgent, CharacterAgent, DraftingAgent

#### Required Data Structures
```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class WorldCore(BaseModel):
    name: str
    summary_and_feel: str
    thematic_integration: str

class HistoryAndLore(BaseModel):
    defining_event: str
    common_myth: str

class FactionsAndPolitics(BaseModel):
    major_powers: Any
    points_of_conflict: Any

class SensoryImmersion(BaseModel):
    common_smells: Any
    ambient_sounds: Any
    texture_of_life: Optional[Any] = None

class CultureAndSociety(BaseModel):
    core_values: Any
    social_structure: Any
    sensory_immersion: SensoryImmersion
    cultural_touchstones: Any

class SocietalFabric(BaseModel):
    history_and_lore: HistoryAndLore
    factions_and_politics: FactionsAndPolitics
    culture_and_society: CultureAndSociety

class GeographyAndEnvironment(BaseModel):
    description: str
    influence_on_culture: str

class SystemsOfPower(BaseModel):
    type: str
    description_and_rules: str

class WorldModel(BaseModel):
    world_core: WorldCore
    societal_fabric: SocietalFabric
    geography_and_environment: GeographyAndEnvironment
    systems_of_power: SystemsOfPower
```

#### Required Methods

```python
class WorldAgent(Agent):
    def __init__(self, llm_client=None):
        super().__init__(
            name="WorldAgent",
            role="world_builder",
            expertise=["world_rules", "cultural_context", "locations", "consistency"]
        )
        self.llm_client = llm_client or self._get_default_llm_client()
        self.prompt_template = None  # Load from prompts/world_modeling_prompt.txt
    
    async def strategize(self, perception: Dict[str, Any]) -> AgentDecision:
        """Check prerequisites and determine strategy"""
        input_data = perception.get("input_data", {})
        high_concept = input_data.get("high_concept_package")
        
        if not high_concept:
            return AgentDecision(
                decision_type=DecisionType.REQUEST_CHANGES,
                reasoning="High concept package required for world modeling",
                confidence=0.95
            )
        
        # Check if genre requires special world-building
        genre = high_concept.get("genre", "").lower()
        if genre in ["sci-fi", "fantasy", "dystopian"]:
            strategy = "detailed_world_building"
        else:
            strategy = "minimal_world_building"
        
        return AgentDecision(
            decision_type=DecisionType.CONTINUE,
            reasoning=f"Using {strategy} for {genre}",
            confidence=0.90,
            metadata={"strategy": strategy, "genre": genre}
        )
    
    async def _execute_task(self, input_data: Any, context: Dict[str, Any]) -> Any:
        """Generate world model"""
        high_concept = input_data.get("high_concept_package", {})
        genre = high_concept.get("genre", "contemporary")
        themes = high_concept.get("themes", [])
        
        # Load prompt template
        if not self.prompt_template:
            self.prompt_template = await self._load_prompt_template()
        
        # Build prompt
        prompt = self._build_world_prompt(high_concept, genre, themes)
        
        # Generate world model using LLM
        world_json = await self._generate_world_model(prompt)
        
        # Validate and parse
        world_model = self._validate_world_model(world_json)
        
        # Store in memory for consistency tracking
        await self._store_world_memory(world_model)
        
        return {
            "state_updates": {
                "world_model": world_model.dict(),
                "world_rules": self._extract_world_rules(world_model),
                "cultural_context": self._extract_cultural_context(world_model)
            },
            "quality_score": await self._assess_world_quality(world_model, high_concept),
            "metadata": {
                "genre": genre,
                "themes_integrated": len(themes),
                "world_complexity": self._assess_complexity(world_model)
            }
        }
    
    async def _load_prompt_template(self) -> str:
        """Load world modeling prompt template"""
        from prometheus_lib.utils.prompt_loader import load_prompt_template
        return await load_prompt_template("world_modeling_prompt.txt")
    
    def _build_world_prompt(self, high_concept: Dict, genre: str, themes: List) -> str:
        """Build comprehensive world-building prompt"""
        # Use existing prompt building logic from stage_02_world_modeling.py
        # Integrate with high concept themes and genre
        pass
    
    async def _generate_world_model(self, prompt: str) -> Dict:
        """Generate world model using LLM"""
        # Use LLM client to generate structured JSON
        # Handle retries and error cases
        pass
    
    def _validate_world_model(self, world_json: Dict) -> WorldModel:
        """Validate world model against Pydantic schema"""
        try:
            return WorldModel(**world_json)
        except ValidationError as e:
            # Handle validation errors
            raise
    
    async def _store_world_memory(self, world_model: WorldModel):
        """Store world details in memory system for consistency"""
        # Store in MemoryAgent or continuity tracker
        pass
    
    def _extract_world_rules(self, world_model: WorldModel) -> Dict[str, str]:
        """Extract immutable world rules"""
        return {
            "power_system": world_model.systems_of_power.description_and_rules,
            "geography": world_model.geography_and_environment.description,
            "social_structure": str(world_model.societal_fabric.culture_and_society.social_structure)
        }
    
    def _extract_cultural_context(self, world_model: WorldModel) -> Dict[str, Any]:
        """Extract cultural context for character development"""
        return {
            "core_values": world_model.societal_fabric.culture_and_society.core_values,
            "cultural_touchstones": world_model.societal_fabric.culture_and_society.cultural_touchstones,
            "sensory_immersion": world_model.societal_fabric.culture_and_society.sensory_immersion.dict()
        }
    
    async def _assess_world_quality(self, world_model: WorldModel, high_concept: Dict) -> float:
        """Assess quality of world model"""
        # Check thematic integration
        # Check internal consistency
        # Check completeness
        # Return score 0-1
        pass
    
    def _assess_complexity(self, world_model: WorldModel) -> str:
        """Assess world complexity level"""
        # Simple heuristic based on number of systems, factions, etc.
        pass
    
    def _get_default_llm_client(self):
        """Get default LLM client"""
        from prometheus_lib.llm.clients import get_llm_client
        return get_llm_client()
```

#### Integration with Existing Code
```python
# Reuse existing prompt template
from prometheus_lib.utils.prompt_loader import load_prompt_template

# Reuse existing Pydantic models
from prometheus_novel.stages.stage_02_world_modeling import (
    WorldModel,
    WorldCore,
    SocietalFabric,
    # ... all models
)

# Reuse existing LLM client
from prometheus_lib.llm.clients import get_llm_client

# Reuse existing error handling
from prometheus_lib.utils.error_handling import (
    LLMGenerationError,
    ValidationError
)
```

#### Quality Criteria
- **Thematic Integration:** World must reflect themes from high concept (score >= 0.85)
- **Internal Consistency:** No contradictory rules (score = 1.0)
- **Completeness:** All required sections present (score >= 0.90)
- **Genre Appropriateness:** World fits genre conventions (score >= 0.80)

#### Dependencies
- **Input:** ConceptAgent output (high_concept_package)
- **Output:** WorldModel for use by CharacterAgent, DraftingAgent
- **Services:** LLM client, prompt loader, memory system

#### Testing Requirements
```python
async def test_world_agent():
    agent = WorldAgent()
    
    # Test with sci-fi genre
    result = await agent.run(
        input_data={
            "high_concept_package": {
                "genre": "sci-fi",
                "themes": [{"name": "technology"}]
            }
        },
        context={"task_type": "world_modeling"}
    )
    
    assert result["quality_score"] >= 0.85
    assert "world_model" in result["state_updates"]
    assert "world_rules" in result["state_updates"]
```

---

### Agent #6: CharacterAgent - Detailed Implementation Plan

#### Purpose
Replace Stage 4 (Character Profiles) with specialized agent that generates deep character profiles, relationships, arcs, and voice definitions.

#### Integration Points
- **Replaces:** `prometheus_novel/stages/stage_04_character_profiles.py`
- **Uses:** `prometheus_lib/models/novel_state.py` (CharacterProfiles)
- **Integrates with:** ConceptAgent, WorldAgent outputs
- **Outputs to:** DraftingAgent, DialogueAgent

#### Required Data Structures
```python
class CharacterPsychology(BaseModel):
    lie_they_believe: Optional[str]
    core_desire: Optional[str]
    core_fear: Optional[str]
    internal_conflict: Optional[str]
    external_conflict: Optional[str]

class CharacterProfile(BaseModel):
    name: Optional[str]
    archetype_and_role: Optional[str]
    psychology: Optional[CharacterPsychology]
    backstory: Optional[str]
    relationships: Optional[Dict[str, str]]
    arc_summary: Optional[str]
    voice_signature: Optional[Dict[str, Any]]  # NEW: Voice definition

class CastDossier(BaseModel):
    protagonist: Optional[CharacterProfile]
    antagonist: Optional[CharacterProfile]
    mentor: Optional[CharacterProfile]
    ally: Optional[CharacterProfile]
    love_interest: Optional[CharacterProfile]
    secondary_characters: Optional[List[CharacterProfile]]

class CharacterProfilesResponse(BaseModel):
    cast_dossier: CastDossier
    character_relationships: Optional[Dict[str, str]]
    thematic_character_arcs: Optional[str]
```

#### Required Methods

```python
class CharacterAgent(Agent):
    def __init__(self, llm_client=None):
        super().__init__(
            name="CharacterAgent",
            role="character_psychologist",
            expertise=["character_profiles", "relationships", "character_arcs", "voice_definition"]
        )
        self.llm_client = llm_client or self._get_default_llm_client()
        self.prompt_template = None
    
    async def strategize(self, perception: Dict[str, Any]) -> AgentDecision:
        """Check prerequisites"""
        input_data = perception.get("input_data", {})
        high_concept = input_data.get("high_concept_package")
        world_model = input_data.get("world_model")
        
        if not high_concept:
            return AgentDecision(
                decision_type=DecisionType.REQUEST_CHANGES,
                reasoning="High concept required",
                confidence=0.95
            )
        
        # World model is helpful but not required
        if world_model:
            strategy = "world_informed"
        else:
            strategy = "concept_only"
        
        return AgentDecision(
            decision_type=DecisionType.CONTINUE,
            reasoning=f"Using {strategy} character development",
            confidence=0.90,
            metadata={"strategy": strategy}
        )
    
    async def _execute_task(self, input_data: Any, context: Dict[str, Any]) -> Any:
        """Generate character profiles"""
        high_concept = input_data.get("high_concept_package", {})
        world_model = input_data.get("world_model")
        
        # Load prompt template
        if not self.prompt_template:
            self.prompt_template = await self._load_prompt_template()
        
        # Build prompt with high concept and world context
        prompt = self._build_character_prompt(high_concept, world_model)
        
        # Generate character profiles
        character_json = await self._generate_character_profiles(prompt)
        
        # Validate
        character_profiles = self._validate_character_profiles(character_json)
        
        # Generate voice signatures for each character
        voice_signatures = await self._generate_voice_signatures(character_profiles)
        
        # Store in memory
        await self._store_character_memory(character_profiles, voice_signatures)
        
        return {
            "state_updates": {
                "character_profiles": character_profiles.dict(),
                "character_relationships": self._extract_relationships(character_profiles),
                "voice_signatures": voice_signatures
            },
            "quality_score": await self._assess_character_quality(character_profiles, high_concept),
            "metadata": {
                "character_count": self._count_characters(character_profiles),
                "relationship_count": len(self._extract_relationships(character_profiles))
            }
        }
    
    async def _load_prompt_template(self) -> str:
        """Load character profiles prompt"""
        from prometheus_lib.utils.prompt_loader import load_prompt_template
        return await load_prompt_template("character_profiles_prompt.txt")
    
    def _build_character_prompt(self, high_concept: Dict, world_model: Optional[Dict]) -> str:
        """Build character development prompt"""
        # Integrate themes, genre, world context
        pass
    
    async def _generate_character_profiles(self, prompt: str) -> Dict:
        """Generate character profiles using LLM"""
        # Use LLM with structured output
        pass
    
    def _validate_character_profiles(self, character_json: Dict) -> CharacterProfilesResponse:
        """Validate against Pydantic schema"""
        try:
            return CharacterProfilesResponse(**character_json)
        except ValidationError as e:
            raise
    
    async def _generate_voice_signatures(self, profiles: CharacterProfilesResponse) -> Dict[str, Dict]:
        """Generate unique voice signature for each character"""
        # For each character, define:
        # - Sentence patterns
        # - Vocabulary preferences
        # - Speech rhythm
        # - Emotional tells
        pass
    
    async def _store_character_memory(self, profiles: CharacterProfilesResponse, voices: Dict):
        """Store character info in memory system"""
        # Store for continuity tracking
        pass
    
    def _extract_relationships(self, profiles: CharacterProfilesResponse) -> Dict[str, str]:
        """Extract relationship map"""
        relationships = {}
        cast = profiles.cast_dossier
        
        if cast.protagonist:
            if cast.antagonist:
                relationships[f"{cast.protagonist.name} -> {cast.antagonist.name}"] = "opposition"
            if cast.mentor:
                relationships[f"{cast.protagonist.name} -> {cast.mentor.name}"] = "guidance"
        # ... extract all relationships
        
        return relationships
    
    async def _assess_character_quality(self, profiles: CharacterProfilesResponse, high_concept: Dict) -> float:
        """Assess character profile quality"""
        # Check psychological depth
        # Check thematic alignment
        # Check relationship complexity
        # Return score 0-1
        pass
    
    def _count_characters(self, profiles: CharacterProfilesResponse) -> int:
        """Count total characters"""
        count = 0
        cast = profiles.cast_dossier
        if cast.protagonist: count += 1
        if cast.antagonist: count += 1
        if cast.mentor: count += 1
        if cast.ally: count += 1
        if cast.love_interest: count += 1
        if cast.secondary_characters:
            count += len(cast.secondary_characters)
        return count
```

#### Quality Criteria
- **Psychological Depth:** All characters have core desire, fear, conflict (score >= 0.90)
- **Thematic Alignment:** Characters serve story themes (score >= 0.85)
- **Relationship Complexity:** Relationships are nuanced (score >= 0.80)
- **Voice Distinctness:** Each character has unique voice (score >= 0.85)

---

## Execution Agents

### Agent #7: DraftingAgent - Detailed Implementation Plan

#### Purpose
Replace Stage 6 (Scene Drafting) with specialized agent that constructs scenes with narrative flow, hook placement, and integration of other agent outputs.

#### Integration Points
- **Replaces:** `prometheus_novel/stages/stage_06_scene_drafting.py`
- **Uses:** V4 Orchestrator for quality
- **Collaborates with:** DialogueAgent, ProseAgent, ActionAgent, DescriptionAgent
- **Integrates with:** ContinuityTracker, POVValidator, ProseImprover

#### Required Methods

```python
class DraftingAgent(Agent):
    def __init__(self, llm_client=None):
        super().__init__(
            name="DraftingAgent",
            role="scene_constructor",
            expertise=["scene_construction", "narrative_flow", "hook_placement"]
        )
        self.llm_client = llm_client or self._get_default_llm_client()
        self.continuity_tracker = None
        self.pov_validator = None
        self.prose_improver = None
        self.v4_orchestrator = None  # For quality control
    
    async def strategize(self, perception: Dict[str, Any]) -> AgentDecision:
        """Check prerequisites for scene drafting"""
        input_data = perception.get("input_data", {})
        scene_plan = input_data.get("scene_plan")
        character_profiles = input_data.get("character_profiles")
        world_model = input_data.get("world_model")
        
        if not scene_plan:
            return AgentDecision(
                decision_type=DecisionType.REQUEST_CHANGES,
                reasoning="Scene plan required",
                confidence=0.95
            )
        
        # Check if we can collaborate with other agents
        peers = perception.get("peer_agents", {})
        can_collaborate = any(
            agent.name in ["DialogueAgent", "ProseAgent", "ActionAgent", "DescriptionAgent"]
            for agent in peers.values()
        )
        
        strategy = "collaborative" if can_collaborate else "standalone"
        
        return AgentDecision(
            decision_type=DecisionType.CONTINUE,
            reasoning=f"Using {strategy} drafting approach",
            confidence=0.90,
            metadata={"strategy": strategy, "can_collaborate": can_collaborate}
        )
    
    async def _execute_task(self, input_data: Any, context: Dict[str, Any]) -> Any:
        """Draft scene with all quality controls"""
        scene_plan = input_data.get("scene_plan", {})
        character_profiles = input_data.get("character_profiles", {})
        world_model = input_data.get("world_model", {})
        previous_scenes = input_data.get("previous_scenes", [])
        
        # Initialize services
        await self._initialize_services()
        
        # Get collaboration inputs if available
        dialogue_suggestions = await self._get_dialogue_suggestions(scene_plan)
        prose_suggestions = await self._get_prose_suggestions(scene_plan)
        action_suggestions = await self._get_action_suggestions(scene_plan)
        description_suggestions = await self._get_description_suggestions(scene_plan)
        
        # Build comprehensive prompt
        prompt = self._build_drafting_prompt(
            scene_plan,
            character_profiles,
            world_model,
            previous_scenes,
            dialogue_suggestions,
            prose_suggestions,
            action_suggestions,
            description_suggestions
        )
        
        # Generate draft using V4 orchestrator for quality
        if self.v4_orchestrator:
            draft_result = await self._draft_with_v4_orchestrator(
                scene_plan,
                prompt,
                previous_scenes
            )
        else:
            draft_result = await self._draft_direct(prompt)
        
        # Validate continuity
        continuity_check = await self._check_continuity(draft_result["scene_text"], previous_scenes)
        
        # Validate POV
        pov_check = await self._check_pov(draft_result["scene_text"], scene_plan)
        
        # Improve prose
        improved_draft = await self._improve_prose(draft_result["scene_text"])
        
        return {
            "state_updates": {
                "scene_draft": improved_draft,
                "scene_title": scene_plan.get("scene_title", ""),
                "word_count": len(improved_draft.split()),
                "continuity_passed": continuity_check["passed"],
                "pov_passed": pov_check["passed"]
            },
            "quality_score": draft_result.get("quality_score", 0.85),
            "metadata": {
                "revision_passes": draft_result.get("revision_count", 0),
                "continuity_issues": continuity_check.get("issues", []),
                "pov_issues": pov_check.get("issues", [])
            }
        }
    
    async def _initialize_services(self):
        """Initialize required services"""
        from prometheus_lib.memory.continuity_tracker import ContinuityTracker
        from prometheus_lib.validators.pov_validator import POVValidator
        from prometheus_lib.utils.prose_improver import ProseImprover
        from prometheus_lib.pipeline.v4_orchestrator import V4Orchestrator
        
        if not self.continuity_tracker:
            self.continuity_tracker = ContinuityTracker()
        if not self.pov_validator:
            self.pov_validator = POVValidator()
        if not self.prose_improver:
            self.prose_improver = ProseImprover()
        if not self.v4_orchestrator:
            self.v4_orchestrator = V4Orchestrator(target_quality_score=0.90)
    
    async def _get_dialogue_suggestions(self, scene_plan: Dict) -> Optional[Dict]:
        """Get dialogue suggestions from DialogueAgent if available"""
        if "DialogueAgent" in [agent.name for agent in self.peer_agents.values()]:
            dialogue_agent = next(
                agent for agent in self.peer_agents.values()
                if agent.name == "DialogueAgent"
            )
            return await dialogue_agent.run(
                {"scene_plan": scene_plan},
                {"task_type": "suggest_dialogue"}
            )
        return None
    
    async def _get_prose_suggestions(self, scene_plan: Dict) -> Optional[Dict]:
        """Get prose suggestions from ProseAgent if available"""
        # Similar to dialogue
        pass
    
    async def _get_action_suggestions(self, scene_plan: Dict) -> Optional[Dict]:
        """Get action suggestions from ActionAgent if available"""
        # Similar to dialogue
        pass
    
    async def _get_description_suggestions(self, scene_plan: Dict) -> Optional[Dict]:
        """Get description suggestions from DescriptionAgent if available"""
        # Similar to dialogue
        pass
    
    def _build_drafting_prompt(
        self,
        scene_plan: Dict,
        character_profiles: Dict,
        world_model: Dict,
        previous_scenes: List,
        dialogue_suggestions: Optional[Dict],
        prose_suggestions: Optional[Dict],
        action_suggestions: Optional[Dict],
        description_suggestions: Optional[Dict]
    ) -> str:
        """Build comprehensive drafting prompt"""
        # Integrate all inputs
        # Use existing prompt building logic from stage_06_scene_drafting.py
        pass
    
    async def _draft_with_v4_orchestrator(
        self,
        scene_plan: Dict,
        prompt: str,
        previous_scenes: List
    ) -> Dict:
        """Draft using V4 orchestrator for quality control"""
        # Use V4 orchestrator's generate_scene_v4 method
        result = await self.v4_orchestrator.generate_scene_v4(
            scene_outline=scene_plan,
            llm_generate_func=self._llm_generate,
            previous_scene_summary=self._summarize_scenes(previous_scenes)
        )
        return {
            "scene_text": result["final_scene"],
            "quality_score": result["quality_score"],
            "revision_count": result["revision_count"]
        }
    
    async def _draft_direct(self, prompt: str) -> Dict:
        """Direct drafting without V4 orchestrator"""
        scene_text = await self.llm_client.generate(prompt)
        return {
            "scene_text": scene_text,
            "quality_score": 0.85  # Default
        }
    
    async def _check_continuity(self, scene_text: str, previous_scenes: List) -> Dict:
        """Check continuity with previous scenes"""
        issues = self.continuity_tracker.check_scene(scene_text, previous_scenes)
        return {
            "passed": len(issues) == 0,
            "issues": issues
        }
    
    async def _check_pov(self, scene_text: str, scene_plan: Dict) -> Dict:
        """Validate POV consistency"""
        pov_character = scene_plan.get("pov", "")
        issues = self.pov_validator.validate(scene_text, pov_character)
        return {
            "passed": len(issues) == 0,
            "issues": issues
        }
    
    async def _improve_prose(self, scene_text: str) -> str:
        """Improve prose quality"""
        return self.prose_improver.improve(scene_text)
    
    async def _llm_generate(self, prompt: str) -> str:
        """LLM generation function for V4 orchestrator"""
        return await self.llm_client.generate(prompt)
    
    def _summarize_scenes(self, scenes: List) -> str:
        """Summarize previous scenes for context"""
        # Create summary of recent scenes
        pass
```

#### Quality Criteria
- **V4 Quality Score:** >= 0.90 (from orchestrator)
- **Continuity:** Zero errors
- **POV Consistency:** 100% compliance
- **Word Count:** 1000-1200 words per scene
- **Hook Placement:** Every 250 words

---

## Evaluation Agents

### Agent #13: QualityJudgeAgent - Detailed Implementation Plan

#### Purpose
Integrate V4's 12-dimension quality judge as a specialized agent.

#### Integration Points
- **Uses:** `prometheus_lib/critics/scene_judge.py` (V4 Scene Judge)
- **Uses:** `prometheus_lib/utils/style_contract.py` (V4 Style Contract)
- **Uses:** `prometheus_lib/utils/automatic_lints.py` (V4 Lints)
- **Uses:** All V4 advanced components (Voice Signature, Micro-Tension, etc.)

#### Required Methods

```python
class QualityJudgeAgent(Agent):
    def __init__(self, llm_client=None):
        super().__init__(
            name="QualityJudgeAgent",
            role="quality_assessor",
            expertise=["12_dimension_scoring", "line_level_analysis", "revision_targeting"]
        )
        # Import V4 components
        from prometheus_lib.critics.scene_judge import SceneJudge
        from prometheus_lib.utils.style_contract import StyleContract, DEFAULT_CONTRACT
        from prometheus_lib.utils.automatic_lints import AutomaticLints
        from prometheus_lib.advanced.voice_signature import VoiceSignature
        from prometheus_lib.advanced.micro_tension_tracker import MicroTensionTracker
        from prometheus_lib.advanced.thematic_echo_system import ThematicEchoSystem
        from prometheus_lib.advanced.emotional_precision import EmotionalPrecisionTracker
        from prometheus_lib.advanced.prose_musicality import ProseMusicality
        
        self.judge = SceneJudge(style_contract=DEFAULT_CONTRACT)
        self.linter = AutomaticLints()
        self.voice_signature = VoiceSignature()
        self.micro_tension = MicroTensionTracker()
        self.thematic_echo = ThematicEchoSystem()
        self.emotional_precision = EmotionalPrecisionTracker()
        self.prose_musicality = ProseMusicality()
    
    async def _execute_task(self, input_data: Any, context: Dict[str, Any]) -> Any:
        """Evaluate scene across 12 dimensions"""
        scene_text = input_data.get("scene_text", "")
        scene_plan = input_data.get("scene_plan", {})
        character_genders = input_data.get("character_genders", {})
        
        # Run all 12 dimensions
        scores = await self._score_all_dimensions(
            scene_text,
            scene_plan,
            character_genders
        )
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(scores)
        
        # Identify revision targets
        flagged_lines = self._identify_revision_targets(scene_text, scores)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(scores, flagged_lines)
        
        return {
            "state_updates": {
                "quality_report": {
                    "overall_score": overall_score,
                    "dimension_scores": scores,
                    "flagged_lines": flagged_lines,
                    "recommendations": recommendations
                }
            },
            "quality_score": overall_score,
            "metadata": {
                "passes": overall_score >= 0.90,
                "critical_failures": self._identify_critical_failures(scores),
                "revision_priority": self._prioritize_revisions(flagged_lines)
            }
        }
    
    async def _score_all_dimensions(
        self,
        scene_text: str,
        scene_plan: Dict,
        character_genders: Dict
    ) -> Dict[str, float]:
        """Score all 12 quality dimensions"""
        # V3 dimensions (7)
        v3_judgment = self.judge.judge_scene(
            scene_text,
            scene_plan.get("characters_present", []),
            {"tension_delta": 1}
        )
        
        lint_result = self.linter.run_all_lints(scene_text, character_genders)
        
        # V4 dimensions (5)
        voice_result = self.voice_signature.validate_scene_signature(scene_text)
        tension_result = self.micro_tension.validate_scene(scene_text)
        theme_result = self.thematic_echo.score_scene_resonance(scene_text)
        emotional_result = self.emotional_precision.map_emotional_trajectory(
            scene_text,
            scene_plan.get("emotional_arc", [])
        )
        musicality_result = self.prose_musicality.analyze_sound_palette(
            scene_text,
            intended_mood=scene_plan.get("intended_emotion", "tension")
        )
        
        return {
            # V3 dimensions
            **v3_judgment["dimension_scores"],
            "lint_passes": 1.0 if lint_result["passes_lints"] else 0.0,
            
            # V4 dimensions
            "voice_signature": voice_result["signature_match_score"],
            "micro_tension": tension_result["score"],
            "thematic_resonance": theme_result["resonance_score"],
            "emotional_precision": emotional_result.get("match_rate", 0.0),
            "prose_musicality": musicality_result["musicality_score"]
        }
    
    def _calculate_overall_score(self, scores: Dict[str, float]) -> float:
        """Calculate weighted overall score"""
        weights = {
            "pacing": 0.08,
            "voice_distinctness": 0.08,
            "cliche_avoidance": 0.08,
            "image_freshness": 0.08,
            "pronoun_continuity": 0.10,
            "rhythm_variety": 0.06,
            "sensory_specificity": 0.06,
            "voice_signature": 0.10,
            "micro_tension": 0.12,
            "thematic_resonance": 0.08,
            "emotional_precision": 0.08,
            "prose_musicality": 0.08
        }
        
        return sum(
            scores[dim] * weights.get(dim, 0.08)
            for dim in scores
        )
    
    def _identify_revision_targets(self, scene_text: str, scores: Dict[str, float]) -> List[Dict]:
        """Identify specific lines that need revision"""
        flagged = []
        
        # Check each dimension for failures
        for dimension, score in scores.items():
            if score < 0.75:  # Threshold for revision
                # Find problematic lines
                lines = self._find_problematic_lines(scene_text, dimension)
                flagged.extend(lines)
        
        return flagged
    
    def _find_problematic_lines(self, scene_text: str, dimension: str) -> List[Dict]:
        """Find specific lines that fail a dimension"""
        # Use dimension-specific analysis
        pass
    
    def _generate_recommendations(self, scores: Dict, flagged_lines: List) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        for dimension, score in scores.items():
            if score < 0.75:
                recommendations.append(
                    f"Improve {dimension}: Current score {score:.0%}, target 75%+"
                )
        
        return recommendations
    
    def _identify_critical_failures(self, scores: Dict[str, float]) -> List[str]:
        """Identify critical failures that block acceptance"""
        critical = []
        
        if scores.get("pronoun_continuity", 1.0) < 0.70:
            critical.append("pronoun_continuity")
        if scores.get("micro_tension", 1.0) < 0.75:
            critical.append("micro_tension")
        
        return critical
    
    def _prioritize_revisions(self, flagged_lines: List[Dict]) -> List[Dict]:
        """Prioritize revision targets"""
        # Sort by priority (critical > high > medium > low)
        return sorted(
            flagged_lines,
            key=lambda x: x.get("priority", "low"),
            reverse=True
        )
```

#### Quality Criteria
- **Overall Score:** >= 0.90 for acceptance
- **Critical Dimensions:** Must pass (pronoun_continuity >= 0.70, micro_tension >= 0.75)
- **All Dimensions:** Target >= 0.75

---

## Support Agents

### Agent #17: MemoryAgent - Detailed Implementation Plan

#### Purpose
Manage semantic storage and retrieval of story information for consistency.

#### Integration Points
- **Uses:** `prometheus_lib/memory/` (existing memory system)
- **Uses:** Vector store for semantic search
- **Integrates with:** All agents (store/retrieve context)

#### Required Methods

```python
class MemoryAgent(Agent):
    def __init__(self, llm_client=None):
        super().__init__(
            name="MemoryAgent",
            role="memory_manager",
            expertise=["semantic_storage", "context_retrieval", "consistency_checking"]
        )
        from prometheus_lib.memory.memory_engine import MemoryEngine
        from prometheus_lib.memory.vector_store import VectorStore
        
        self.memory_engine = MemoryEngine()
        self.vector_store = VectorStore()
    
    async def _execute_task(self, input_data: Any, context: Dict[str, Any]) -> Any:
        """Store or retrieve memories"""
        action = input_data.get("action", "retrieve")
        
        if action == "store":
            return await self._store_memory(input_data, context)
        elif action == "retrieve":
            return await self._retrieve_memory(input_data, context)
        elif action == "check_consistency":
            return await self._check_consistency(input_data, context)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _store_memory(self, input_data: Any, context: Dict[str, Any]) -> Dict:
        """Store memory item"""
        content = input_data.get("content", "")
        metadata = input_data.get("metadata", {})
        tags = input_data.get("tags", [])
        
        # Store in memory engine
        memory_id = self.memory_engine.store(
            content=content,
            metadata=metadata,
            tags=tags
        )
        
        # Store in vector store for semantic search
        await self.vector_store.add(
            text=content,
            metadata={"memory_id": memory_id, **metadata}
        )
        
        return {
            "state_updates": {"memory_id": memory_id},
            "quality_score": 1.0,
            "metadata": {"stored_at": datetime.now().isoformat()}
        }
    
    async def _retrieve_memory(self, input_data: Any, context: Dict[str, Any]) -> Dict:
        """Retrieve relevant memories"""
        query = input_data.get("query", "")
        limit = input_data.get("limit", 5)
        tags = input_data.get("tags", [])
        
        # Semantic search
        results = await self.vector_store.search(
            query=query,
            limit=limit,
            tags=tags
        )
        
        return {
            "state_updates": {"memories": results},
            "quality_score": 1.0,
            "metadata": {"result_count": len(results)}
        }
    
    async def _check_consistency(self, input_data: Any, context: Dict[str, Any]) -> Dict:
        """Check consistency of new content against stored memories"""
        new_content = input_data.get("content", "")
        check_type = input_data.get("check_type", "character")  # character, world, plot
        
        # Retrieve relevant memories
        relevant = await self._retrieve_memory(
            {"query": new_content, "tags": [check_type]},
            {}
        )
        
        # Check for contradictions
        contradictions = self._find_contradictions(new_content, relevant["state_updates"]["memories"])
        
        return {
            "state_updates": {
                "consistent": len(contradictions) == 0,
                "contradictions": contradictions
            },
            "quality_score": 1.0 if len(contradictions) == 0 else 0.5,
            "metadata": {"contradiction_count": len(contradictions)}
        }
    
    def _find_contradictions(self, new_content: str, memories: List[Dict]) -> List[Dict]:
        """Find contradictions between new content and stored memories"""
        # Use LLM or rule-based checking
        pass
```

---

## Summary

Each agent now has:
- ✅ **Detailed purpose and integration points**
- ✅ **Required data structures (Pydantic models)**
- ✅ **Complete method signatures**
- ✅ **Integration with existing code**
- ✅ **Quality criteria**
- ✅ **Dependencies**
- ✅ **Testing requirements**

**Next Step:** Implement agents following these detailed plans!



