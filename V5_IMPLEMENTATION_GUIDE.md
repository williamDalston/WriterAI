# V5 Multi-Agent System Implementation Guide

**Version:** 5.0.0  
**Date:** November 6, 2025  
**Status:** Foundation Complete, Ready for Development

---

## What's Been Built

### ✅ Core Infrastructure (Complete)

1. **Base Agent System** (`prometheus_lib/agents_v5/base_agent_v5.py`)
   - Agent base class with perceive-strategize-act-reflect-learn cycle
   - Memory system (short-term, long-term, learned patterns)
   - Tool system
   - Performance tracking
   - Collaboration capabilities

2. **Communication System** (`prometheus_lib/agents_v5/agent_communication.py`)
   - AgentCommunicationBus for message routing
   - Priority-based queuing
   - Request-response correlation
   - Broadcast support
   - Message history

3. **Conductor Agent** (`prometheus_lib/agents_v5/conductor_agent.py`)
   - Master orchestrator
   - Project planning
   - Task delegation
   - Conflict resolution
   - Quality gate enforcement

4. **Example Planning Agents** (`prometheus_lib/agents_v5/planning_agents.py`)
   - ConceptAgent (themes, motifs, central questions)
   - StructureAgent (beat sheets, act timing, scene sequence)

---

## Quick Start: Running the V5 Demo

### Step 1: Test Individual Components

```bash
cd prometheus_novel/prometheus_lib/agents_v5

# Test base agent
python base_agent_v5.py

# Test communication bus
python agent_communication.py

# Test conductor
python conductor_agent.py

# Test planning agents
python planning_agents.py
```

### Step 2: Run Full Integration Demo

```python
# Create demo script: demo_v5_system.py
import asyncio
from prometheus_lib.agents_v5 import ConductorAgent
from prometheus_lib.agents_v5.planning_agents import ConceptAgent, StructureAgent

async def demo_v5():
    # Initialize conductor
    conductor = ConductorAgent()
    
    # Register specialist agents
    concept_agent = ConceptAgent()
    structure_agent = StructureAgent()
    
    conductor.register_planning_agent(concept_agent)
    conductor.register_planning_agent(structure_agent)
    
    # Create project plan
    plan = await conductor.create_project_plan(
        novel_metadata={
            "title": "The Last Starship",
            "genre": "sci-fi",
            "synopsis": "In 2347, humanity's last starship carries civilization toward a new home."
        },
        budget_usd=30.0,
        target_quality=0.95
    )
    
    print(f"Created plan: {plan.novel_metadata['title']}")
    print(f"Stages: {len(plan.stages)}")
    
    # Generate status report
    status = conductor.generate_status_report()
    print(f"\nRegistered agents: {status['conductor']['registered_agents']['total']}")

asyncio.run(demo_v5())
```

---

## Architecture Overview

### Agent Hierarchy

```
ConductorAgent (Meta-orchestrator)
    ├── Planning Agents
    │   ├── ConceptAgent
    │   ├── StructureAgent  
    │   ├── CharacterAgent (TODO)
    │   └── WorldAgent (TODO)
    │
    ├── Execution Agents (TODO)
    │   ├── DraftingAgent
    │   ├── DialogueAgent
    │   ├── ProseAgent
    │   ├── ActionAgent
    │   └── DescriptionAgent
    │
    ├── Evaluation Agents (TODO)
    │   ├── QualityJudgeAgent
    │   ├── ContinuityAgent
    │   ├── EmotionalAgent
    │   └── ThemeAgent
    │
    └── Support Agents (TODO)
        ├── MemoryAgent
        ├── LearningAgent
        ├── BudgetAgent
        ├── ResearchAgent
        ├── ExportAgent
        └── AnalyticsAgent
```

### Agent Communication Flow

```
1. Conductor creates ProjectPlan
2. Conductor delegates Stage 1 to ConceptAgent
3. ConceptAgent:
   - Perceives input (synopsis, genre)
   - Strategizes (check prerequisites)
   - Acts (generate high concept)
   - Reflects (assess quality)
   - Learns (store successful patterns)
4. ConceptAgent sends result back to Conductor
5. Conductor checks quality gates
6. Conductor delegates Stage 3 to StructureAgent (with Concept output)
7. ... repeat for all stages
```

---

## Creating a New Specialized Agent

### Template

```python
from .base_agent_v5 import Agent, AgentDecision, DecisionType
import logging

logger = logging.getLogger(__name__)

class MySpecializedAgent(Agent):
    """
    Agent description and responsibilities.
    """
    
    def __init__(self, llm_client=None):
        super().__init__(
            name="MySpecializedAgent",
            role="my_role",
            expertise=["skill1", "skill2", "skill3"]
        )
        self.llm_client = llm_client
        
        logger.info(f"{self.name} initialized")
    
    async def strategize(self, perception: Dict[str, Any]) -> AgentDecision:
        """
        Decide how to approach the task.
        Check prerequisites, determine strategy.
        """
        context = perception.get("context", {})
        input_data = perception.get("input_data", {})
        
        # Check prerequisites
        required_field = input_data.get("required_field")
        if not required_field:
            return AgentDecision(
                decision_type=DecisionType.REQUEST_CHANGES,
                reasoning="Missing required field",
                confidence=0.95
            )
        
        # Decide strategy
        return AgentDecision(
            decision_type=DecisionType.CONTINUE,
            reasoning="All prerequisites met",
            confidence=0.90,
            metadata={"approach": "standard"}
        )
    
    async def _execute_task(self, input_data: Any, context: Dict[str, Any]) -> Any:
        """
        Execute the agent's primary function.
        """
        logger.info(f"{self.name} executing task...")
        
        # Do the work
        result = await self._do_specialized_work(input_data)
        
        # Return in standard format
        return {
            "state_updates": {
                "my_output": result
            },
            "quality_score": 0.88,
            "metadata": {
                "processing_notes": "Task completed successfully"
            }
        }
    
    async def _do_specialized_work(self, input_data: Any) -> Any:
        """Helper method for actual work"""
        # Implement your logic here
        return {"status": "done"}
```

### Registering with Conductor

```python
# Create your agent
my_agent = MySpecializedAgent()

# Register with conductor (choose appropriate category)
conductor.register_planning_agent(my_agent)
# OR
conductor.register_execution_agent(my_agent)
# OR
conductor.register_evaluation_agent(my_agent)
# OR
conductor.register_support_agent(my_agent)
```

---

## Agent Collaboration Patterns

### Pattern 1: Sequential Delegation

```python
async def sequential_workflow(conductor):
    # Step 1: Concept
    concept_result = await conductor.delegate_task(
        agent_id=concept_agent.agent_id,
        task_type="high_concept",
        task_data={"synopsis": "..."}
    )
    
    # Step 2: Structure (uses concept output)
    structure_result = await conductor.delegate_task(
        agent_id=structure_agent.agent_id,
        task_type="beat_sheet",
        task_data={
            "high_concept_package": concept_result["state_updates"]["high_concept_package"]
        }
    )
    
    return structure_result
```

### Pattern 2: Parallel Execution

```python
async def parallel_workflow(conductor):
    # Execute multiple agents in parallel
    results = await asyncio.gather(
        conductor.delegate_task(dialogue_agent.agent_id, "dialogue", data1),
        conductor.delegate_task(prose_agent.agent_id, "description", data2),
        conductor.delegate_task(action_agent.agent_id, "choreography", data3)
    )
    
    # Synthesize results
    return synthesis_agent.merge(results)
```

### Pattern 3: Agent-to-Agent Communication

```python
# Agent A sends query to Agent B
from .agent_communication import create_query_message

query = create_query_message(
    sender=self.agent_id,
    receiver=other_agent_id,
    query="What is the character's current emotional state?",
    context={"scene_id": "scene_15"}
)

response = await self.communication_bus.send_and_wait(query, timeout=10.0)
```

---

## Next Steps for Development

### Phase 1: Complete Planning Agents (Week 1)

- [ ] Create `CharacterAgent`
  - Deep character profiles
  - Relationship mapping
  - Character arc planning
  - Voice definition

- [ ] Create `WorldAgent`
  - World rules
  - Cultural context
  - Location details
  - Consistency tracking

### Phase 2: Build Execution Agents (Weeks 2-3)

- [ ] Create `DraftingAgent`
  - Scene construction
  - Narrative flow
  - Hook placement

- [ ] Create `DialogueAgent`
  - Voice distinctness
  - Subtext generation
  - Rhythm variation

- [ ] Create `ProseAgent`
  - Imagery selection
  - Sensory detail
  - Rhythm matching mood

- [ ] Create `ActionAgent`
  - Movement choreography
  - Spatial clarity
  - Visceral detail

- [ ] Create `DescriptionAgent`
  - Setting immersion
  - Atmosphere creation
  - 5-sense engagement

- [ ] Create `SynthesisAgent`
  - Merge agent outputs
  - Resolve conflicts
  - Ensure coherence

### Phase 3: Build Evaluation Agents (Week 4)

- [ ] Create `QualityJudgeAgent`
  - Integrate V4 12-dimension judge
  - Line-level scoring
  - Revision targeting

- [ ] Create `ContinuityAgent`
  - Plot hole detection
  - Character consistency
  - Timeline validation

- [ ] Create `EmotionalAgent`
  - Emotional arc tracking
  - Reader impact prediction
  - Mood consistency

- [ ] Create `ThemeAgent`
  - Thematic resonance scoring
  - Symbolic depth analysis
  - Theme presence validation

### Phase 4: Build Support Agents (Week 5)

- [ ] Create `MemoryAgent`
  - Semantic storage
  - Context retrieval
  - Consistency checking

- [ ] Create `LearningAgent`
  - Pattern extraction
  - Quality tracking
  - Strategy updates

- [ ] Create `BudgetAgent`
  - Cost tracking
  - Model selection
  - Budget forecasting

- [ ] Create `ResearchAgent`
  - Fact checking
  - Cultural authenticity
  - Technical accuracy

- [ ] Create `ExportAgent`
  - Kindle formatting
  - Multi-format export
  - Professional styling

- [ ] Create `AnalyticsAgent`
  - Performance dashboards
  - Quality trends
  - Bottleneck identification

### Phase 5: Integration & Testing (Week 6)

- [ ] End-to-end scene generation test
- [ ] Full novel generation test
- [ ] Performance benchmarking
- [ ] Quality comparison vs V4
- [ ] Cost analysis

### Phase 6: Advanced Features (Weeks 7-8)

- [ ] Agent negotiation protocol
- [ ] Dynamic agent composition
- [ ] Multi-novel learning
- [ ] Genre-specific teams
- [ ] Human-in-the-loop collaboration

---

## Testing Strategy

### Unit Tests

```python
import pytest
from prometheus_lib.agents_v5.planning_agents import ConceptAgent

@pytest.mark.asyncio
async def test_concept_agent_theme_extraction():
    agent = ConceptAgent()
    
    result = await agent.run(
        input_data={
            "title": "Test Novel",
            "genre": "sci-fi",
            "synopsis": "A story about identity and technology"
        },
        context={"task_type": "high_concept"}
    )
    
    assert "high_concept_package" in result["state_updates"]
    assert len(result["state_updates"]["high_concept_package"]["themes"]) > 0
    assert result["quality_score"] >= 0.85
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_conductor_delegates_to_agents():
    conductor = ConductorAgent()
    concept_agent = ConceptAgent()
    conductor.register_planning_agent(concept_agent)
    
    result = await conductor.execute_stage(
        "high_concept",
        {"synopsis": "Test story"}
    )
    
    assert result["quality_score"] >= 0.85
    assert len(conductor.completed_tasks) == 1
```

### Performance Tests

```python
@pytest.mark.asyncio
async def test_parallel_agent_execution():
    import time
    
    start = time.time()
    
    # Run 3 agents in parallel
    results = await asyncio.gather(
        agent1.run(data1, context1),
        agent2.run(data2, context2),
        agent3.run(data3, context3)
    )
    
    elapsed = time.time() - start
    
    # Should be faster than sequential (< 3x single agent time)
    assert elapsed < expected_max_time
```

---

## Performance Optimization

### Caching

```python
from functools import lru_cache

class ConceptAgent(Agent):
    @lru_cache(maxsize=100)
    def _get_theme_keywords(self, genre: str) -> List[str]:
        """Cache genre-theme mappings"""
        return GENRE_THEMES.get(genre, DEFAULT_THEMES)
```

### Parallel Execution

```python
# Execute independent agents in parallel
async def execute_planning_phase(conductor, input_data):
    concept, world = await asyncio.gather(
        conductor.delegate_task(concept_agent_id, "high_concept", input_data),
        conductor.delegate_task(world_agent_id, "world_modeling", input_data)
    )
    
    # Then character (depends on both)
    characters = await conductor.delegate_task(
        character_agent_id,
        "character_profiles",
        {"concept": concept, "world": world}
    )
```

### Resource Pooling

```python
# Reuse LLM clients across agents
llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

concept_agent = ConceptAgent(llm_client=llm_client)
structure_agent = StructureAgent(llm_client=llm_client)
character_agent = CharacterAgent(llm_client=llm_client)
```

---

## Monitoring & Debugging

### Enable Debug Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("prometheus_lib.agents_v5")
logger.setLevel(logging.DEBUG)
```

### Agent Performance Dashboard

```python
def print_agent_stats(conductor):
    status = conductor.generate_status_report()
    
    print("=" * 60)
    print("AGENT PERFORMANCE DASHBOARD")
    print("=" * 60)
    
    all_agents = {
        **conductor.planning_agents,
        **conductor.execution_agents,
        **conductor.evaluation_agents,
        **conductor.support_agents
    }
    
    for agent_id, agent in all_agents.items():
        stats = agent.get_stats()
        print(f"\n{agent.name}:")
        print(f"  Tasks: {stats['tasks_completed']}")
        print(f"  Success Rate: {stats['success_rate']:.1%}")
        print(f"  Avg Latency: {stats['average_latency_ms']:.0f}ms")
        print(f"  Avg Quality: {stats['average_quality_score']:.1%}")
```

### Message Tracing

```python
# View recent messages
history = conductor.bus.get_message_history(limit=20)

for msg in history:
    print(f"{msg.sender} → {msg.receiver}: {msg.message_type.value}")
```

---

## Troubleshooting

### Issue: Agent not receiving messages

**Solution:**
```python
# Ensure agent is registered with bus
conductor.register_planning_agent(my_agent)

# Check agent is in bus
print(my_agent.agent_id in conductor.bus.agents)  # Should be True
```

### Issue: Timeout waiting for agent response

**Solution:**
```python
# Increase timeout
result = await conductor.bus.send_and_wait(message, timeout=120.0)

# Or check if agent is processing
print(f"Agent state: {agent.state}")
```

### Issue: Quality gates failing

**Solution:**
```python
# Check which gate failed
for gate in conductor.default_quality_gates:
    passed = conductor._evaluate_gate(gate, stage_result)
    print(f"{gate.name}: {'✓' if passed else '✗'}")

# Adjust thresholds if needed
conductor.default_quality_gates[0].threshold = 0.85
```

---

## Best Practices

1. **Single Responsibility**: Each agent should have one clear expertise area
2. **Explicit Communication**: Use message bus, not direct method calls
3. **Quality Tracking**: Always return quality_score in results
4. **Error Handling**: Use try/except and log errors
5. **Documentation**: Document agent expertise and prerequisites
6. **Testing**: Write tests for each agent's core functionality
7. **Monitoring**: Track agent performance metrics
8. **Graceful Degradation**: Have fallback strategies

---

## Resources

- **Architecture Doc**: `AGENT_ARCHITECTURE_V5_ROADMAP.md`
- **Source Code**: `prometheus_novel/prometheus_lib/agents_v5/`
- **Tests**: `prometheus_novel/tests/agents_v5/` (to be created)
- **Examples**: `prometheus_novel/examples/v5_demos/` (to be created)

---

## Getting Help

1. Check this guide first
2. Review agent source code docstrings
3. Run test scripts to see examples
4. Enable debug logging
5. Check message history for communication issues

---

**Status:** ✅ Foundation Ready  
**Next Milestone:** Complete all Planning Agents (Week 1)  
**Target:** Full V5 System Operational (8 weeks)

