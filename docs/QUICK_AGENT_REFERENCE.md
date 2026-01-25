# Quick Agent Reference - Numbered Agents

## 🚀 Quick Run Commands

### Run Any Agent by Number
```bash
cd prometheus_novel
python run_agent.py <agent_number>
```

### List All Agents
```bash
cd prometheus_novel
python run_agent.py list
```

### Run Full Demo (All Available Agents)
```bash
cd prometheus_novel
python demo_v5_full_system.py
```

---

## 📋 All 22 Agents (Numbered)

### ✅ Implemented (Can Run Now)

| # | Agent Name | Quick Run |
|---|------------|-----------|
| **#1** | **ConductorAgent** | `python run_agent.py 1` |
| **#2** | **Base Agent** | `python run_agent.py 2` |
| **#3** | **ConceptAgent** | `python run_agent.py 3` |
| **#5** | **StructureAgent** | `python run_agent.py 5` |

### ❌ Not Implemented (Need Development)

| # | Agent Name | Status |
|---|------------|--------|
| **#4** | **WorldAgent** | ❌ TODO - High Priority |
| **#6** | **CharacterAgent** | ❌ TODO - High Priority |
| **#7** | **DraftingAgent** | ❌ TODO - Medium Priority |
| **#8** | **DialogueAgent** | ❌ TODO - Medium Priority |
| **#9** | **ProseAgent** | ❌ TODO - Medium Priority |
| **#10** | **ActionAgent** | ❌ TODO - Medium Priority |
| **#11** | **DescriptionAgent** | ❌ TODO - Medium Priority |
| **#12** | **SynthesisAgent** | ❌ TODO - Medium Priority |
| **#13** | **QualityJudgeAgent** | ❌ TODO - Medium Priority |
| **#14** | **ContinuityAgent** | ❌ TODO - Medium Priority |
| **#15** | **EmotionalAgent** | ❌ TODO - Medium Priority |
| **#16** | **ThemeAgent** | ❌ TODO - Medium Priority |
| **#17** | **MemoryAgent** | ❌ TODO - Low Priority |
| **#18** | **LearningAgent** | ❌ TODO - Low Priority |
| **#19** | **BudgetAgent** | ❌ TODO - Low Priority |
| **#20** | **ResearchAgent** | ❌ TODO - Low Priority |
| **#21** | **ExportAgent** | ❌ TODO - Low Priority |
| **#22** | **AnalyticsAgent** | ❌ TODO - Low Priority |

---

## 🎯 Agent Categories

### Core Infrastructure (2 agents)
- **#1** ConductorAgent ✅
- **#2** Base Agent ✅

### Planning Agents (4 agents)
- **#3** ConceptAgent ✅
- **#4** WorldAgent ❌
- **#5** StructureAgent ✅
- **#6** CharacterAgent ❌

### Execution Agents (6 agents)
- **#7** DraftingAgent ❌
- **#8** DialogueAgent ❌
- **#9** ProseAgent ❌
- **#10** ActionAgent ❌
- **#11** DescriptionAgent ❌
- **#12** SynthesisAgent ❌

### Evaluation Agents (4 agents)
- **#13** QualityJudgeAgent ❌
- **#14** ContinuityAgent ❌
- **#15** EmotionalAgent ❌
- **#16** ThemeAgent ❌

### Support Agents (6 agents)
- **#17** MemoryAgent ❌
- **#18** LearningAgent ❌
- **#19** BudgetAgent ❌
- **#20** ResearchAgent ❌
- **#21** ExportAgent ❌
- **#22** AnalyticsAgent ❌

---

## 📖 Detailed Documentation

- **Full Run Guide:** `AGENT_RUN_GUIDE.md` - Complete instructions for all agents
- **Agent Names List:** `AGENT_NAMES_LIST.md` - All agent names and details
- **Architecture:** `AGENT_ARCHITECTURE_V5_ROADMAP.md` - Complete V5 system design
- **Implementation:** `V5_IMPLEMENTATION_GUIDE.md` - How to implement new agents

---

## 🎬 Example Usage

### Run Agent #1 (Conductor)
```bash
cd prometheus_novel
python run_agent.py 1
```

**Output:**
```
================================================================================
AGENT #1: ConductorAgent
================================================================================

✓ Conductor initialized: <agent_id>
✓ Plan created: Test Novel
✓ Stages: 12
✓ Registered agents: 0

✅ ConductorAgent test complete!
```

### Run Agent #3 (Concept)
```bash
cd prometheus_novel
python run_agent.py 3
```

**Output:**
```
================================================================================
AGENT #3: ConceptAgent
================================================================================

✓ ConceptAgent initialized
✓ Themes: 3
✓ Central Question: What is the price of technology?
✓ Motifs: 4
✓ Quality Score: 90%

✅ ConceptAgent test complete!
```

### List All Agents
```bash
cd prometheus_novel
python run_agent.py list
```

**Output:**
```
================================================================================
V5 AGENT REGISTRY - All 22 Agents
================================================================================

#    Name                      Status        Can Run
--------------------------------------------------------------------------------
1    ConductorAgent            ✅ Implemented ✅ Yes
2    Base Agent                ✅ Implemented ✅ Yes
3    ConceptAgent              ✅ Implemented ✅ Yes
4    WorldAgent                ❌ Not Implemented ❌ No
5    StructureAgent            ✅ Implemented ✅ Yes
...
```

---

## 🔧 Troubleshooting

### Issue: Import errors
```bash
# Make sure you're in the right directory
cd prometheus_novel

# Check Python path
python -c "import sys; print(sys.path)"
```

### Issue: Agent not found
```bash
# List all available agents
python run_agent.py list

# Check if agent is implemented
# See AGENT_RUN_GUIDE.md for implementation status
```

### Issue: Agent not implemented
```bash
# See AGENT_RUN_GUIDE.md for implementation instructions
# Each agent has a "To Implement" section with code template
```

---

## 📊 Status Summary

**Total Agents:** 22
- **✅ Implemented:** 4 (18%)
- **❌ Not Implemented:** 18 (82%)

**By Priority:**
- **🔥 High Priority:** 2 agents (#4, #6)
- **⚡ Medium Priority:** 10 agents (#7-#16)
- **📝 Low Priority:** 6 agents (#17-#22)

---

**Ready to run? Start with: `python run_agent.py list`**



