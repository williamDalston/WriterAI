# V5 Agent Run Guide - Numbered Agent Reference

**All 23 Agents with Unique Numbers and Run Instructions**

---

## 🎯 Core Infrastructure Agents

### Agent #1: ConductorAgent ✅
**Status:** ✅ Implemented | **Can Run:** ✅ Yes

**Purpose:** Meta-orchestrator that coordinates all other agents

**Run Command:**
```bash
cd prometheus_novel/prometheus_lib/agents_v5
python conductor_agent.py
```

**Or in Python:**
```python
from prometheus_novel.prometheus_lib.agents_v5 import ConductorAgent
import asyncio

async def run():
    conductor = ConductorAgent()
    plan = await conductor.create_project_plan({
        "title": "Test Novel",
        "genre": "sci-fi",
        "synopsis": "A test story"
    })
    print(f"Plan created: {plan.novel_metadata['title']}")

asyncio.run(run())
```

**Test Status:** ✅ Working

---

### Agent #2: Base Agent (Foundation) ✅
**Status:** ✅ Implemented | **Can Run:** ✅ Yes

**Purpose:** Foundation class for all agents

**Run Command:**
```bash
cd prometheus_novel/prometheus_lib/agents_v5
python base_agent_v5.py
```

**Test Status:** ✅ Working

---

## 📋 Planning Agents (Pre-Writing)

### Agent #3: ConceptAgent ✅
**Status:** ✅ Implemented | **Can Run:** ✅ Yes

**Purpose:** Generates themes, motifs, central questions, emotional core

**Run Command:**
```bash
cd prometheus_novel/prometheus_lib/agents_v5
python planning_agents.py
```

**Or in Python:**
```python
from prometheus_novel.prometheus_lib.agents_v5.planning_agents import ConceptAgent
import asyncio

async def run():
    agent = ConceptAgent()
    result = await agent.run(
        input_data={
            "title": "The Last Starship",
            "genre": "sci-fi",
            "synopsis": "In 2347, humanity's last starship..."
        },
        context={"task_type": "high_concept"}
    )
    print(f"Themes: {len(result['state_updates']['high_concept_package']['themes'])}")
    print(f"Quality: {result['quality_score']:.0%}")

asyncio.run(run())
```

**Test Status:** ✅ Working

---

### Agent #4: WorldAgent ❌
**Status:** ❌ Not Implemented | **Can Run:** ❌ No

**Purpose:** World-building specialist (rules, cultural context, locations)

**To Implement:**
```python
# File: prometheus_novel/prometheus_lib/agents_v5/planning_agents.py
# Add after StructureAgent

class WorldAgent(Agent):
    def __init__(self, llm_client=None):
        super().__init__(
            name="WorldAgent",
            role="world_builder",
            expertise=["world_rules", "cultural_context", "locations", "consistency"]
        )
        self.llm_client = llm_client
    
    async def strategize(self, perception: Dict[str, Any]) -> AgentDecision:
        # Check prerequisites
        high_concept = perception.get("input_data", {}).get("high_concept_package")
        if not high_concept:
            return AgentDecision(
                decision_type=DecisionType.REQUEST_CHANGES,
                reasoning="High concept required",
                confidence=0.95
            )
        return AgentDecision(decision_type=DecisionType.CONTINUE, confidence=0.9)
    
    async def _execute_task(self, input_data: Any, context: Dict[str, Any]) -> Any:
        # Generate world rules, cultural context, locations
        # TODO: Implement world-building logic
        return {
            "state_updates": {"world_package": {}},
            "quality_score": 0.90
        }
```

**Run Command (after implementation):**
```bash
cd prometheus_novel
python -c "
from prometheus_novel.prometheus_lib.agents_v5.planning_agents import WorldAgent
import asyncio
asyncio.run(WorldAgent().run({'high_concept_package': {}}, {}))
"
```

**Priority:** 🔥 High

---

### Agent #5: StructureAgent ✅
**Status:** ✅ Implemented | **Can Run:** ✅ Yes

**Purpose:** Creates beat sheets, act timing, scene sequences

**Run Command:**
```bash
cd prometheus_novel/prometheus_lib/agents_v5
python planning_agents.py
```

**Or in Python:**
```python
from prometheus_novel.prometheus_lib.agents_v5.planning_agents import StructureAgent
import asyncio

async def run():
    agent = StructureAgent()
    result = await agent.run(
        input_data={
            "high_concept_package": {"genre": "sci-fi"},
            "target_length": 60000
        },
        context={"task_type": "beat_sheet"}
    )
    print(f"Beats: {len(result['state_updates']['beat_sheet']['beats'])}")
    print(f"Scenes: {result['state_updates']['beat_sheet']['total_scenes']}")

asyncio.run(run())
```

**Test Status:** ✅ Working

---

### Agent #6: CharacterAgent ❌
**Status:** ❌ Not Implemented | **Can Run:** ❌ No

**Purpose:** Character psychologist (profiles, relationships, arcs, voices)

**To Implement:**
```python
# File: prometheus_novel/prometheus_lib/agents_v5/planning_agents.py
# Add after StructureAgent

class CharacterAgent(Agent):
    def __init__(self, llm_client=None):
        super().__init__(
            name="CharacterAgent",
            role="character_psychologist",
            expertise=["character_profiles", "relationships", "character_arcs", "voice_definition"]
        )
        self.llm_client = llm_client
    
    async def strategize(self, perception: Dict[str, Any]) -> AgentDecision:
        # Check prerequisites
        high_concept = perception.get("input_data", {}).get("high_concept_package")
        if not high_concept:
            return AgentDecision(
                decision_type=DecisionType.REQUEST_CHANGES,
                reasoning="High concept required",
                confidence=0.95
            )
        return AgentDecision(decision_type=DecisionType.CONTINUE, confidence=0.9)
    
    async def _execute_task(self, input_data: Any, context: Dict[str, Any]) -> Any:
        # Generate character profiles, relationships, arcs
        # TODO: Implement character development logic
        return {
            "state_updates": {"character_profiles": {}},
            "quality_score": 0.90
        }
```

**Run Command (after implementation):**
```bash
cd prometheus_novel
python -c "
from prometheus_novel.prometheus_lib.agents_v5.planning_agents import CharacterAgent
import asyncio
asyncio.run(CharacterAgent().run({'high_concept_package': {}}, {}))
"
```

**Priority:** 🔥 High

---

## ✍️ Execution Agents (Writing)

### Agent #7: DraftingAgent ❌
**Status:** ❌ Not Implemented | **Can Run:** ❌ No

**Purpose:** Scene constructor (narrative flow, hook placement)

**To Implement:**
```python
# File: prometheus_novel/prometheus_lib/agents_v5/execution_agents.py (create new file)

from .base_agent_v5 import Agent, AgentDecision, DecisionType

class DraftingAgent(Agent):
    def __init__(self, llm_client=None):
        super().__init__(
            name="DraftingAgent",
            role="scene_constructor",
            expertise=["scene_construction", "narrative_flow", "hook_placement"]
        )
        self.llm_client = llm_client
    
    async def _execute_task(self, input_data: Any, context: Dict[str, Any]) -> Any:
        # Generate scene draft
        # TODO: Implement scene drafting logic
        return {
            "state_updates": {"scene_draft": ""},
            "quality_score": 0.90
        }
```

**Run Command (after implementation):**
```bash
cd prometheus_novel
python -c "
from prometheus_novel.prometheus_lib.agents_v5.execution_agents import DraftingAgent
import asyncio
asyncio.run(DraftingAgent().run({'scene_plan': {}}, {}))
"
```

**Priority:** ⚡ Medium

---

### Agent #8: DialogueAgent ❌
**Status:** ❌ Not Implemented | **Can Run:** ❌ No

**Purpose:** Dialogue specialist (voice distinctness, subtext, rhythm)

**To Implement:**
```python
# File: prometheus_novel/prometheus_lib/agents_v5/execution_agents.py

class DialogueAgent(Agent):
    def __init__(self, llm_client=None):
        super().__init__(
            name="DialogueAgent",
            role="dialogue_specialist",
            expertise=["voice_distinctness", "subtext", "natural_speech", "rhythm"]
        )
        self.llm_client = llm_client
    
    async def _execute_task(self, input_data: Any, context: Dict[str, Any]) -> Any:
        # Generate dialogue with subtext
        # TODO: Implement dialogue generation logic
        return {
            "state_updates": {"dialogue": ""},
            "quality_score": 0.90
        }
```

**Run Command (after implementation):**
```bash
cd prometheus_novel
python -c "
from prometheus_novel.prometheus_lib.agents_v5.execution_agents import DialogueAgent
import asyncio
asyncio.run(DialogueAgent().run({'scene_plan': {}}, {}))
"
```

**Priority:** ⚡ Medium

---

### Agent #9: ProseAgent ❌
**Status:** ❌ Not Implemented | **Can Run:** ❌ No

**Purpose:** Prose stylist (imagery, rhythm, sensory detail, atmosphere)

**To Implement:**
```python
# File: prometheus_novel/prometheus_lib/agents_v5/execution_agents.py

class ProseAgent(Agent):
    def __init__(self, llm_client=None):
        super().__init__(
            name="ProseAgent",
            role="prose_stylist",
            expertise=["imagery", "rhythm", "sensory_detail", "atmosphere"]
        )
        self.llm_client = llm_client
    
    async def _execute_task(self, input_data: Any, context: Dict[str, Any]) -> Any:
        # Generate prose with imagery and rhythm
        # TODO: Implement prose generation logic
        return {
            "state_updates": {"prose": ""},
            "quality_score": 0.90
        }
```

**Run Command (after implementation):**
```bash
cd prometheus_novel
python -c "
from prometheus_novel.prometheus_lib.agents_v5.execution_agents import ProseAgent
import asyncio
asyncio.run(ProseAgent().run({'scene_plan': {}}, {}))
"
```

**Priority:** ⚡ Medium

---

### Agent #10: ActionAgent ❌
**Status:** ❌ Not Implemented | **Can Run:** ❌ No

**Purpose:** Action choreographer (movement, spatial clarity, visceral detail)

**To Implement:**
```python
# File: prometheus_novel/prometheus_lib/agents_v5/execution_agents.py

class ActionAgent(Agent):
    def __init__(self, llm_client=None):
        super().__init__(
            name="ActionAgent",
            role="action_choreographer",
            expertise=["movement", "choreography", "spatial_clarity", "visceral_detail"]
        )
        self.llm_client = llm_client
    
    async def _execute_task(self, input_data: Any, context: Dict[str, Any]) -> Any:
        # Generate action sequences
        # TODO: Implement action choreography logic
        return {
            "state_updates": {"action_sequence": ""},
            "quality_score": 0.90
        }
```

**Run Command (after implementation):**
```bash
cd prometheus_novel
python -c "
from prometheus_novel.prometheus_lib.agents_v5.execution_agents import ActionAgent
import asyncio
asyncio.run(ActionAgent().run({'scene_plan': {}}, {}))
"
```

**Priority:** ⚡ Medium

---

### Agent #11: DescriptionAgent ❌
**Status:** ❌ Not Implemented | **Can Run:** ❌ No

**Purpose:** Setting specialist (immersion, 5 senses, atmosphere)

**To Implement:**
```python
# File: prometheus_novel/prometheus_lib/agents_v5/execution_agents.py

class DescriptionAgent(Agent):
    def __init__(self, llm_client=None):
        super().__init__(
            name="DescriptionAgent",
            role="setting_specialist",
            expertise=["setting_immersion", "sensory_detail", "atmosphere", "five_senses"]
        )
        self.llm_client = llm_client
    
    async def _execute_task(self, input_data: Any, context: Dict[str, Any]) -> Any:
        # Generate setting descriptions
        # TODO: Implement description generation logic
        return {
            "state_updates": {"description": ""},
            "quality_score": 0.90
        }
```

**Run Command (after implementation):**
```bash
cd prometheus_novel
python -c "
from prometheus_novel.prometheus_lib.agents_v5.execution_agents import DescriptionAgent
import asyncio
asyncio.run(DescriptionAgent().run({'scene_plan': {}}, {}))
"
```

**Priority:** ⚡ Medium

---

### Agent #12: SynthesisAgent ✅
**Status:** ✅ Implemented | **Can Run:** ✅ Yes

**Purpose:** Output synthesizer (merges agent outputs, resolves conflicts)

**Run Command:**
```bash
cd prometheus_novel/prometheus_lib/agents_v5
python execution_agents.py
```

**Or in Python:**
```python
from prometheus_novel.prometheus_lib.agents_v5.execution_agents import SynthesisAgent
import asyncio

async def run():
    agent = SynthesisAgent()
    
    # Mock agent outputs
    agent_outputs = {
        "DialogueAgent": {
            "state_updates": {"dialogue": '"Hello," she said.'},
            "characters": ["Alice", "Bob"]
        },
        "ProseAgent": {
            "state_updates": {"prose": "The room was dimly lit."}
        },
        "ActionAgent": {
            "state_updates": {"action": "She walked across the room."}
        },
        "DescriptionAgent": {
            "state_updates": {"description": "The old library smelled of dust."}
        }
    }
    
    result = await agent.run(
        input_data={
            "agent_outputs": agent_outputs,
            "scene_plan": {
                "scene_title": "Test Scene",
                "target_word_count": 100
            }
        },
        context={"task_type": "synthesis"}
    )
    
    print(f"Synthesized scene: {result['state_updates']['synthesized_scene']['word_count']} words")
    print(f"Conflicts resolved: {result['state_updates']['synthesized_scene']['conflicts_resolved']}")
    print(f"Quality score: {result['quality_score']:.0%}")

asyncio.run(run())
```

**Features:**
- Merges outputs from DialogueAgent, ProseAgent, ActionAgent, DescriptionAgent
- Detects and resolves conflicts between agent outputs
- Checks coherence of merged scene
- Refines narrative flow
- Handles partial agent outputs gracefully

**Test Status:** ✅ Working

---

## ⚖️ Evaluation Agents (Quality Assurance)

### Agent #13: QualityJudgeAgent ❌
**Status:** ❌ Not Implemented | **Can Run:** ❌ No

**Purpose:** Quality assessor (12-dimension scoring, line-level analysis)

**To Implement:**
```python
# File: prometheus_novel/prometheus_lib/agents_v5/evaluation_agents.py (create new file)

from .base_agent_v5 import Agent, AgentDecision, DecisionType
from prometheus_lib.critics.scene_judge import SceneJudge

class QualityJudgeAgent(Agent):
    def __init__(self, llm_client=None):
        super().__init__(
            name="QualityJudgeAgent",
            role="quality_assessor",
            expertise=["12_dimension_scoring", "line_level_analysis", "revision_targeting"]
        )
        self.llm_client = llm_client
        self.judge = SceneJudge()  # Integrate V4 judge
    
    async def _execute_task(self, input_data: Any, context: Dict[str, Any]) -> Any:
        scene_text = input_data.get("scene_text", "")
        scene_plan = input_data.get("scene_plan", {})
        
        # Run 12-dimension scoring
        judgment = self.judge.judge_scene(scene_text, scene_plan.get("characters", []), {})
        
        return {
            "state_updates": {"quality_report": judgment},
            "quality_score": judgment.get("overall_score", 0.0)
        }
```

**Run Command (after implementation):**
```bash
cd prometheus_novel
python -c "
from prometheus_novel.prometheus_lib.agents_v5.evaluation_agents import QualityJudgeAgent
import asyncio
asyncio.run(QualityJudgeAgent().run({'scene_text': 'Test scene', 'scene_plan': {}}, {}))
"
```

**Priority:** ⚡ Medium

---

### Agent #14: ContinuityAgent ❌
**Status:** ❌ Not Implemented | **Can Run:** ❌ No

**Purpose:** Continuity auditor (plot holes, character consistency, timeline)

**To Implement:**
```python
# File: prometheus_novel/prometheus_lib/agents_v5/evaluation_agents.py

class ContinuityAgent(Agent):
    def __init__(self, llm_client=None):
        super().__init__(
            name="ContinuityAgent",
            role="continuity_auditor",
            expertise=["plot_holes", "character_consistency", "timeline_validation"]
        )
        self.llm_client = llm_client
    
    async def _execute_task(self, input_data: Any, context: Dict[str, Any]) -> Any:
        # Check continuity across all scenes
        # TODO: Implement continuity checking logic
        return {
            "state_updates": {"continuity_report": {}},
            "quality_score": 0.90
        }
```

**Run Command (after implementation):**
```bash
cd prometheus_novel
python -c "
from prometheus_novel.prometheus_lib.agents_v5.evaluation_agents import ContinuityAgent
import asyncio
asyncio.run(ContinuityAgent().run({'all_scenes': []}, {}))
"
```

**Priority:** ⚡ Medium

---

### Agent #15: EmotionalAgent ❌
**Status:** ❌ Not Implemented | **Can Run:** ❌ No

**Purpose:** Emotional arc tracker (reader impact, mood consistency)

**To Implement:**
```python
# File: prometheus_novel/prometheus_lib/agents_v5/evaluation_agents.py

class EmotionalAgent(Agent):
    def __init__(self, llm_client=None):
        super().__init__(
            name="EmotionalAgent",
            role="emotional_arc_tracker",
            expertise=["emotional_trajectory", "reader_impact", "mood_consistency"]
        )
        self.llm_client = llm_client
    
    async def _execute_task(self, input_data: Any, context: Dict[str, Any]) -> Any:
        # Track emotional arc
        # TODO: Implement emotional tracking logic
        return {
            "state_updates": {"emotional_report": {}},
            "quality_score": 0.90
        }
```

**Run Command (after implementation):**
```bash
cd prometheus_novel
python -c "
from prometheus_novel.prometheus_lib.agents_v5.evaluation_agents import EmotionalAgent
import asyncio
asyncio.run(EmotionalAgent().run({'scene_text': '', 'intended_arc': []}, {}))
"
```

**Priority:** ⚡ Medium

---

### Agent #16: ThemeAgent ❌
**Status:** ❌ Not Implemented | **Can Run:** ❌ No

**Purpose:** Thematic analyst (resonance, symbolic depth, theme presence)

**To Implement:**
```python
# File: prometheus_novel/prometheus_lib/agents_v5/evaluation_agents.py

class ThemeAgent(Agent):
    def __init__(self, llm_client=None):
        super().__init__(
            name="ThemeAgent",
            role="thematic_analyst",
            expertise=["thematic_resonance", "symbolic_depth", "theme_presence"]
        )
        self.llm_client = llm_client
    
    async def _execute_task(self, input_data: Any, context: Dict[str, Any]) -> Any:
        # Analyze thematic resonance
        # TODO: Implement theme analysis logic
        return {
            "state_updates": {"theme_report": {}},
            "quality_score": 0.90
        }
```

**Run Command (after implementation):**
```bash
cd prometheus_novel
python -c "
from prometheus_novel.prometheus_lib.agents_v5.evaluation_agents import ThemeAgent
import asyncio
asyncio.run(ThemeAgent().run({'scene_text': '', 'thematic_framework': {}}, {}))
"
```

**Priority:** ⚡ Medium

---

## 🛠️ Support Agents (Cross-Cutting)

### Agent #17: MemoryAgent ❌
**Status:** ❌ Not Implemented | **Can Run:** ❌ No

**Purpose:** Memory manager (semantic storage, context retrieval)

**To Implement:**
```python
# File: prometheus_novel/prometheus_lib/agents_v5/support_agents.py (create new file)

from .base_agent_v5 import Agent, AgentDecision, DecisionType

class MemoryAgent(Agent):
    def __init__(self, llm_client=None):
        super().__init__(
            name="MemoryAgent",
            role="memory_manager",
            expertise=["semantic_storage", "context_retrieval", "consistency_checking"]
        )
        self.llm_client = llm_client
        self.memory_store = {}  # In-memory store (can use vector DB)
    
    async def _execute_task(self, input_data: Any, context: Dict[str, Any]) -> Any:
        # Store or retrieve memories
        # TODO: Implement memory system logic
        return {
            "state_updates": {"memory_result": {}},
            "quality_score": 1.0
        }
```

**Run Command (after implementation):**
```bash
cd prometheus_novel
python -c "
from prometheus_novel.prometheus_lib.agents_v5.support_agents import MemoryAgent
import asyncio
asyncio.run(MemoryAgent().run({'action': 'store', 'content': 'test'}, {}))
"
```

**Priority:** 📝 Low

---

### Agent #18: LearningAgent ❌
**Status:** ❌ Not Implemented | **Can Run:** ❌ No

**Purpose:** Pattern learner (extracts patterns, updates strategies)

**To Implement:**
```python
# File: prometheus_novel/prometheus_lib/agents_v5/support_agents.py

class LearningAgent(Agent):
    def __init__(self, llm_client=None):
        super().__init__(
            name="LearningAgent",
            role="pattern_learner",
            expertise=["pattern_extraction", "quality_tracking", "strategy_updates"]
        )
        self.llm_client = llm_client
    
    async def _execute_task(self, input_data: Any, context: Dict[str, Any]) -> Any:
        # Learn from results
        # TODO: Implement learning logic
        return {
            "state_updates": {"learned_patterns": {}},
            "quality_score": 1.0
        }
```

**Run Command (after implementation):**
```bash
cd prometheus_novel
python -c "
from prometheus_novel.prometheus_lib.agents_v5.support_agents import LearningAgent
import asyncio
asyncio.run(LearningAgent().run({'generation_results': {}}, {}))
"
```

**Priority:** 📝 Low

---

### Agent #19: BudgetAgent ❌
**Status:** ❌ Not Implemented | **Can Run:** ❌ No

**Purpose:** Cost optimizer (tracks costs, selects models, forecasts budget)

**To Implement:**
```python
# File: prometheus_novel/prometheus_lib/agents_v5/support_agents.py

class BudgetAgent(Agent):
    def __init__(self, llm_client=None):
        super().__init__(
            name="BudgetAgent",
            role="cost_optimizer",
            expertise=["cost_tracking", "model_selection", "budget_forecasting"]
        )
        self.llm_client = llm_client
        self.total_cost = 0.0
    
    async def _execute_task(self, input_data: Any, context: Dict[str, Any]) -> Any:
        # Track or forecast costs
        # TODO: Implement budget tracking logic
        return {
            "state_updates": {"budget_report": {}},
            "quality_score": 1.0
        }
```

**Run Command (after implementation):**
```bash
cd prometheus_novel
python -c "
from prometheus_novel.prometheus_lib.agents_v5.support_agents import BudgetAgent
import asyncio
asyncio.run(BudgetAgent().run({'action': 'track', 'cost': 0.50}, {}))
"
```

**Priority:** 📝 Low

---

### Agent #20: ResearchAgent ❌
**Status:** ❌ Not Implemented | **Can Run:** ❌ No

**Purpose:** Fact checker (verifies facts, cultural authenticity, technical accuracy)

**To Implement:**
```python
# File: prometheus_novel/prometheus_lib/agents_v5/support_agents.py

class ResearchAgent(Agent):
    def __init__(self, llm_client=None):
        super().__init__(
            name="ResearchAgent",
            role="fact_checker",
            expertise=["fact_checking", "cultural_authenticity", "technical_accuracy"]
        )
        self.llm_client = llm_client
    
    async def _execute_task(self, input_data: Any, context: Dict[str, Any]) -> Any:
        # Research and verify facts
        # TODO: Implement research logic
        return {
            "state_updates": {"research_report": {}},
            "quality_score": 1.0
        }
```

**Run Command (after implementation):**
```bash
cd prometheus_novel
python -c "
from prometheus_novel.prometheus_lib.agents_v5.support_agents import ResearchAgent
import asyncio
asyncio.run(ResearchAgent().run({'query': 'test fact', 'context': {}}, {}))
"
```

**Priority:** 📝 Low

---

### Agent #21: ExportAgent ❌
**Status:** ❌ Not Implemented | **Can Run:** ❌ No

**Purpose:** Format specialist (Kindle formatting, multi-format export)

**To Implement:**
```python
# File: prometheus_novel/prometheus_lib/agents_v5/support_agents.py

class ExportAgent(Agent):
    def __init__(self, llm_client=None):
        super().__init__(
            name="ExportAgent",
            role="format_specialist",
            expertise=["kindle_formatting", "multi_format_export", "professional_styling"]
        )
        self.llm_client = llm_client
    
    async def _execute_task(self, input_data: Any, context: Dict[str, Any]) -> Any:
        # Export in various formats
        # TODO: Implement export logic
        return {
            "state_updates": {"export_files": []},
            "quality_score": 1.0
        }
```

**Run Command (after implementation):**
```bash
cd prometheus_novel
python -c "
from prometheus_novel.prometheus_lib.agents_v5.support_agents import ExportAgent
import asyncio
asyncio.run(ExportAgent().run({'novel_text': '', 'formats': ['kindle']}, {}))
"
```

**Priority:** 📝 Low

---

### Agent #22: AnalyticsAgent ❌
**Status:** ❌ Not Implemented | **Can Run:** ❌ No

**Purpose:** Performance analyst (dashboards, quality trends, bottlenecks)

**To Implement:**
```python
# File: prometheus_novel/prometheus_lib/agents_v5/support_agents.py

class AnalyticsAgent(Agent):
    def __init__(self, llm_client=None):
        super().__init__(
            name="AnalyticsAgent",
            role="performance_analyst",
            expertise=["dashboards", "quality_trends", "bottleneck_identification"]
        )
        self.llm_client = llm_client
    
    async def _execute_task(self, input_data: Any, context: Dict[str, Any]) -> Any:
        # Generate analytics and insights
        # TODO: Implement analytics logic
        return {
            "state_updates": {"analytics_report": {}},
            "quality_score": 1.0
        }
```

**Run Command (after implementation):**
```bash
cd prometheus_novel
python -c "
from prometheus_novel.prometheus_lib.agents_v5.support_agents import AnalyticsAgent
import asyncio
asyncio.run(AnalyticsAgent().run({'metrics': {}}, {}))
"
```

**Priority:** 📝 Low

---

## 🚀 Quick Run All Available Agents

### Run All Implemented Agents (Agents #1, #2, #3, #5)
```bash
cd prometheus_novel
python demo_v5_full_system.py
```

This runs:
- Agent #1: ConductorAgent
- Agent #3: ConceptAgent
- Agent #5: StructureAgent
- Agent #12: SynthesisAgent

### Run Individual Tests
```bash
cd prometheus_novel/prometheus_lib/agents_v5

# Test Agent #1: Conductor
python conductor_agent.py

# Test Agent #2: Base Agent
python base_agent_v5.py

# Test Agent #3: ConceptAgent
python planning_agents.py

# Test Agent #12: SynthesisAgent
python execution_agents.py
```

---

## 📊 Agent Status Summary

| Agent # | Name | Status | Can Run | Priority |
|---------|------|--------|---------|----------|
| #1 | ConductorAgent | ✅ | ✅ | - |
| #2 | Base Agent | ✅ | ✅ | - |
| #3 | ConceptAgent | ✅ | ✅ | - |
| #4 | WorldAgent | ❌ | ❌ | 🔥 High |
| #5 | StructureAgent | ✅ | ✅ | - |
| #6 | CharacterAgent | ❌ | ❌ | 🔥 High |
| #7 | DraftingAgent | ❌ | ❌ | ⚡ Medium |
| #8 | DialogueAgent | ❌ | ❌ | ⚡ Medium |
| #9 | ProseAgent | ❌ | ❌ | ⚡ Medium |
| #10 | ActionAgent | ❌ | ❌ | ⚡ Medium |
| #11 | DescriptionAgent | ❌ | ❌ | ⚡ Medium |
| #12 | SynthesisAgent | ✅ | ✅ | - |
| #13 | QualityJudgeAgent | ❌ | ❌ | ⚡ Medium |
| #14 | ContinuityAgent | ❌ | ❌ | ⚡ Medium |
| #15 | EmotionalAgent | ❌ | ❌ | ⚡ Medium |
| #16 | ThemeAgent | ❌ | ❌ | ⚡ Medium |
| #17 | MemoryAgent | ❌ | ❌ | 📝 Low |
| #18 | LearningAgent | ❌ | ❌ | 📝 Low |
| #19 | BudgetAgent | ❌ | ❌ | 📝 Low |
| #20 | ResearchAgent | ❌ | ❌ | 📝 Low |
| #21 | ExportAgent | ❌ | ❌ | 📝 Low |
| #22 | AnalyticsAgent | ❌ | ❌ | 📝 Low |

**Total:** 22 Agents
- **✅ Implemented:** 5 (23%)
- **❌ Not Implemented:** 17 (77%)

---

## 🎯 Recommended Implementation Order

### Week 1: Complete Planning Agents
1. ✅ Agent #3: ConceptAgent (Done)
2. ✅ Agent #5: StructureAgent (Done)
3. 🔨 Agent #4: WorldAgent (Next)
4. 🔨 Agent #6: CharacterAgent (Next)

### Week 2-3: Execution Agents
5. 🔨 Agent #7: DraftingAgent
6. 🔨 Agent #8: DialogueAgent
7. 🔨 Agent #9: ProseAgent
8. 🔨 Agent #10: ActionAgent
9. 🔨 Agent #11: DescriptionAgent
10. 🔨 Agent #12: SynthesisAgent

### Week 4: Evaluation Agents
11. 🔨 Agent #13: QualityJudgeAgent
12. 🔨 Agent #14: ContinuityAgent
13. 🔨 Agent #15: EmotionalAgent
14. 🔨 Agent #16: ThemeAgent

### Week 5: Support Agents
15. 🔨 Agent #17: MemoryAgent
16. 🔨 Agent #18: LearningAgent
17. 🔨 Agent #19: BudgetAgent
18. 🔨 Agent #20: ResearchAgent
19. 🔨 Agent #21: ExportAgent
20. 🔨 Agent #22: AnalyticsAgent

---

## 📝 Notes

- All agents follow the pattern: `[Domain]Agent`
- All agents inherit from `Agent` base class
- All agents implement `perceive → strategize → act → reflect → learn` cycle
- Run commands assume you're in the `prometheus_novel` directory
- Python commands can be run directly or saved as scripts

---

**Ready to run? Start with the full demo: `python demo_v5_full_system.py`**



