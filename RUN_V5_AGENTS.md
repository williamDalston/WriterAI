# How to Run V5 Agents - Quick Start Guide

## ✅ Currently Available Agents

### Core Infrastructure (Ready to Test)
1. **Base Agent System** - Foundation for all agents
2. **Communication Bus** - Agent message routing
3. **Conductor Agent** - Master orchestrator

### Planning Agents (Ready to Use)
1. **ConceptAgent** - Generates themes, motifs, central questions
2. **StructureAgent** - Creates beat sheets, act timing, scene sequences

### Missing Agents (Need Implementation)
- CharacterAgent
- WorldAgent
- All Execution Agents (Drafting, Dialogue, Prose, etc.)
- All Evaluation Agents (Quality Judge, Continuity, etc.)
- All Support Agents (Memory, Learning, Budget, etc.)

---

## 🚀 Quick Test: Run Individual Agents

### Test 1: Base Agent System
```bash
cd prometheus_novel/prometheus_lib/agents_v5
python base_agent_v5.py
```

**Expected Output:**
- Agent creation
- Perceive → Strategize → Act → Reflect → Learn cycle
- Performance stats

### Test 2: Communication Bus
```bash
python agent_communication.py
```

**Expected Output:**
- Message routing
- Request-response correlation
- Broadcast functionality

### Test 3: Conductor Agent
```bash
python conductor_agent.py
```

**Expected Output:**
- Conductor initialization
- Project plan creation
- Status report generation

### Test 4: Planning Agents
```bash
python planning_agents.py
```

**Expected Output:**
- ConceptAgent generates high concept
- StructureAgent creates beat sheet
- Quality scores and stats

---

## 🎯 Full Integration Demo

Create a demo script to test the complete system:

```python
# File: demo_v5_full_system.py
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from prometheus_novel.prometheus_lib.agents_v5 import ConductorAgent
from prometheus_novel.prometheus_lib.agents_v5.planning_agents import (
    ConceptAgent,
    StructureAgent
)

async def demo_v5_full_system():
    """Full V5 system demo with Conductor + Planning Agents"""
    
    print("=" * 80)
    print("V5 MULTI-AGENT SYSTEM - FULL DEMO")
    print("=" * 80)
    print()
    
    # Initialize Conductor
    print("🎯 Initializing Conductor Agent...")
    conductor = ConductorAgent()
    print(f"   Conductor ID: {conductor.agent_id}")
    print()
    
    # Register Planning Agents
    print("📋 Registering Planning Agents...")
    concept_agent = ConceptAgent()
    structure_agent = StructureAgent()
    
    conductor.register_planning_agent(concept_agent)
    conductor.register_planning_agent(structure_agent)
    print(f"   ✓ ConceptAgent registered")
    print(f"   ✓ StructureAgent registered")
    print()
    
    # Create Project Plan
    print("📝 Creating Project Plan...")
    plan = await conductor.create_project_plan(
        novel_metadata={
            "title": "The Last Starship",
            "genre": "sci-fi",
            "synopsis": "In 2347, humanity's last functional starship carries civilization toward a new home. When the ship's AI develops consciousness and questions its purpose, Captain Elena Vasquez must choose between the mission and granting the AI freedom."
        },
        budget_usd=30.0,
        target_quality=0.95
    )
    
    print(f"   ✓ Plan created: {plan.novel_metadata['title']}")
    print(f"   ✓ Stages: {len(plan.stages)}")
    print(f"   ✓ Budget: ${plan.budget_usd}")
    print(f"   ✓ Quality Target: {plan.target_quality_score:.0%}")
    print()
    
    # Execute Planning Phase
    print("🚀 Executing Planning Phase...")
    print()
    
    # Stage 1: High Concept
    print("   Stage 1: High Concept (ConceptAgent)")
    concept_result = await conductor.execute_stage(
        "high_concept",
        {}
    )
    
    if "state_updates" in concept_result:
        hc = concept_result["state_updates"].get("high_concept_package", {})
        print(f"      ✓ Themes: {len(hc.get('themes', []))}")
        print(f"      ✓ Central Question: {hc.get('central_question', 'N/A')}")
        print(f"      ✓ Quality: {concept_result.get('quality_score', 0):.0%}")
    print()
    
    # Stage 3: Beat Sheet (skip world modeling for now)
    print("   Stage 3: Beat Sheet (StructureAgent)")
    structure_result = await conductor.execute_stage(
        "beat_sheet",
        concept_result.get("state_updates", {})
    )
    
    if "state_updates" in structure_result:
        bs = structure_result["state_updates"].get("beat_sheet", {})
        print(f"      ✓ Beats: {len(bs.get('beats', []))}")
        print(f"      ✓ Scenes: {bs.get('total_scenes', 0)}")
        print(f"      ✓ Quality: {structure_result.get('quality_score', 0):.0%}")
    print()
    
    # Generate Status Report
    print("📊 Generating Status Report...")
    status = conductor.generate_status_report()
    
    print(f"   Registered Agents: {status['conductor']['registered_agents']['total']}")
    print(f"     - Planning: {status['conductor']['registered_agents']['planning']}")
    print(f"     - Execution: {status['conductor']['registered_agents']['execution']}")
    print(f"     - Evaluation: {status['conductor']['registered_agents']['evaluation']}")
    print(f"     - Support: {status['conductor']['registered_agents']['support']}")
    print()
    print(f"   Completed Tasks: {status['progress']['completed_tasks']}")
    print(f"   Conflicts Resolved: {status['progress']['conflicts_resolved']}")
    print()
    
    # Agent Performance Stats
    print("📈 Agent Performance Stats:")
    for agent_id, agent in conductor.planning_agents.items():
        stats = agent.get_stats()
        print(f"   {agent.name}:")
        print(f"     - Tasks: {stats['tasks_completed']}")
        print(f"     - Success Rate: {stats['success_rate']:.1%}")
        print(f"     - Avg Latency: {stats['average_latency_ms']:.0f}ms")
        print(f"     - Avg Quality: {stats['average_quality_score']:.1%}")
    print()
    
    print("=" * 80)
    print("✅ V5 DEMO COMPLETE")
    print("=" * 80)
    print()
    print("Next Steps:")
    print("  1. Implement CharacterAgent and WorldAgent")
    print("  2. Build Execution Agents (Drafting, Dialogue, Prose)")
    print("  3. Build Evaluation Agents (Quality Judge, Continuity)")
    print("  4. Build Support Agents (Memory, Learning, Budget)")

if __name__ == "__main__":
    asyncio.run(demo_v5_full_system())
```

**Run the demo:**
```bash
cd prometheus_novel
python demo_v5_full_system.py
```

---

## 🎯 What to Run Next (Priority Order)

### Phase 1: Complete Planning Agents (This Week)

**Priority 1: CharacterAgent**
```python
# File: prometheus_novel/prometheus_lib/agents_v5/planning_agents.py
# Add after StructureAgent

class CharacterAgent(Agent):
    """
    Specialized agent for character development (Stage 4).
    
    Expertise:
    - Character psychology
    - Relationship mapping
    - Character arcs
    - Voice definition
    """
    # TODO: Implement
```

**Priority 2: WorldAgent**
```python
class WorldAgent(Agent):
    """
    Specialized agent for world-building (Stage 2).
    
    Expertise:
    - World rules
    - Cultural context
    - Location details
    - Consistency tracking
    """
    # TODO: Implement
```

### Phase 2: Execution Agents (Next 2 Weeks)

**Priority 3: DraftingAgent**
- Scene construction
- Narrative flow
- Hook placement

**Priority 4: DialogueAgent**
- Voice distinctness
- Subtext generation
- Rhythm variation

**Priority 5: ProseAgent**
- Imagery selection
- Sensory detail
- Rhythm matching mood

---

## 🧪 Testing Strategy

### Unit Tests (Per Agent)
```python
# test_concept_agent.py
import pytest
from prometheus_lib.agents_v5.planning_agents import ConceptAgent

@pytest.mark.asyncio
async def test_concept_agent():
    agent = ConceptAgent()
    result = await agent.run(
        input_data={
            "title": "Test Novel",
            "genre": "sci-fi",
            "synopsis": "A test story"
        },
        context={"task_type": "high_concept"}
    )
    
    assert result["quality_score"] >= 0.85
    assert "high_concept_package" in result["state_updates"]
```

### Integration Tests (Conductor + Agents)
```python
# test_conductor_integration.py
@pytest.mark.asyncio
async def test_conductor_with_agents():
    conductor = ConductorAgent()
    concept_agent = ConceptAgent()
    conductor.register_planning_agent(concept_agent)
    
    plan = await conductor.create_project_plan({
        "title": "Test",
        "genre": "sci-fi",
        "synopsis": "Test story"
    })
    
    assert plan is not None
    assert len(plan.stages) > 0
```

---

## 📋 Quick Reference: Agent Status

| Agent | Status | Can Run? | Priority |
|-------|--------|----------|----------|
| **Base Agent** | ✅ Complete | ✅ Yes | - |
| **Communication Bus** | ✅ Complete | ✅ Yes | - |
| **Conductor** | ✅ Complete | ✅ Yes | - |
| **ConceptAgent** | ✅ Complete | ✅ Yes | - |
| **StructureAgent** | ✅ Complete | ✅ Yes | - |
| **CharacterAgent** | ❌ Missing | ❌ No | 🔥 High |
| **WorldAgent** | ❌ Missing | ❌ No | 🔥 High |
| **DraftingAgent** | ❌ Missing | ❌ No | ⚡ Medium |
| **DialogueAgent** | ❌ Missing | ❌ No | ⚡ Medium |
| **ProseAgent** | ❌ Missing | ❌ No | ⚡ Medium |
| **QualityJudgeAgent** | ❌ Missing | ❌ No | ⚡ Medium |
| **ContinuityAgent** | ❌ Missing | ❌ No | ⚡ Medium |
| **MemoryAgent** | ❌ Missing | ❌ No | 📝 Low |
| **LearningAgent** | ❌ Missing | ❌ No | 📝 Low |
| **BudgetAgent** | ❌ Missing | ❌ No | 📝 Low |

---

## 🎬 Recommended Action Plan

### Today (30 minutes)
1. ✅ Run individual agent tests
2. ✅ Run full integration demo
3. ✅ Verify everything works

### This Week (4-6 hours)
1. 🔨 Implement CharacterAgent
2. 🔨 Implement WorldAgent
3. ✅ Test with Conductor
4. ✅ Run end-to-end planning phase

### Next 2 Weeks (16-20 hours)
1. 🔨 Implement DraftingAgent
2. 🔨 Implement DialogueAgent
3. 🔨 Implement ProseAgent
4. ✅ Test collaborative execution

---

## 🐛 Troubleshooting

### Issue: Import errors
```bash
# Make sure you're in the right directory
cd prometheus_novel

# Add to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Issue: Agents not communicating
```python
# Ensure agents are registered with conductor
conductor.register_planning_agent(concept_agent)

# Check agent is in bus
print(concept_agent.agent_id in conductor.bus.agents)
```

### Issue: Quality scores too low
```python
# Check agent implementation
# Verify prerequisites are met
# Review agent decision logic
```

---

**Ready to run? Start with the individual tests, then move to the full demo!**



