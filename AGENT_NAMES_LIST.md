# Complete List of V5 Agent Names

## 🎯 Core Infrastructure Agents

### 1. **ConductorAgent** ✅ (Implemented)
- **Role:** Meta-orchestrator
- **Purpose:** Coordinates all agents, resolves conflicts, enforces quality gates
- **Status:** ✅ Complete and ready to use

### 2. **Base Agent** (Abstract Class)
- **Class:** `Agent` (in `base_agent_v5.py`)
- **Purpose:** Foundation class for all specialized agents
- **Status:** ✅ Complete

### 3. **StageAgent** (Utility Class)
- **Purpose:** Wrapper for pipeline stages
- **Status:** ✅ Complete

---

## 📋 Planning Agents (Pre-Writing)

### 4. **ConceptAgent** ✅ (Implemented)
- **Role:** High-concept developer
- **Expertise:** Themes, motifs, central questions, emotional core
- **Replaces:** Stage 1 (High Concept)
- **Status:** ✅ Complete and ready to use

### 5. **WorldAgent** ❌ (Not Implemented)
- **Role:** World-building specialist
- **Expertise:** World rules, cultural context, location details, consistency
- **Replaces:** Stage 2 (World Modeling)
- **Status:** ❌ TODO - High Priority

### 6. **StructureAgent** ✅ (Implemented)
- **Role:** Plot architect
- **Expertise:** Three-act structure, story beats, pacing, dramatic timing
- **Replaces:** Stage 3 (Beat Sheet)
- **Status:** ✅ Complete and ready to use

### 7. **CharacterAgent** ❌ (Not Implemented)
- **Role:** Character psychologist
- **Expertise:** Character psychology, relationship mapping, character arcs, voice definition
- **Replaces:** Stage 4 (Character Profiles)
- **Status:** ❌ TODO - High Priority

---

## ✍️ Execution Agents (Writing)

### 8. **DraftingAgent** ❌ (Not Implemented)
- **Role:** Scene constructor
- **Expertise:** Scene construction, narrative flow, hook placement
- **Replaces:** Stage 6 (Scene Drafting)
- **Status:** ❌ TODO - Medium Priority

### 9. **DialogueAgent** ❌ (Not Implemented)
- **Role:** Dialogue specialist
- **Expertise:** Voice distinctness, subtext, natural speech, rhythm
- **Collaborates with:** CharacterAgent
- **Status:** ❌ TODO - Medium Priority

### 10. **ProseAgent** ❌ (Not Implemented)
- **Role:** Prose stylist
- **Expertise:** Imagery, rhythm, sensory detail, atmosphere
- **Collaborates with:** WorldAgent
- **Status:** ❌ TODO - Medium Priority

### 11. **ActionAgent** ❌ (Not Implemented)
- **Role:** Action choreographer
- **Expertise:** Movement, choreography, spatial clarity, visceral detail
- **Collaborates with:** DraftingAgent
- **Status:** ❌ TODO - Medium Priority

### 12. **DescriptionAgent** ❌ (Not Implemented)
- **Role:** Setting specialist
- **Expertise:** Setting immersion, sensory detail (5 senses), atmosphere
- **Collaborates with:** WorldAgent, ProseAgent
- **Status:** ❌ TODO - Medium Priority

### 13. **SynthesisAgent** ❌ (Not Implemented)
- **Role:** Output synthesizer
- **Expertise:** Merging agent outputs, resolving conflicts, ensuring coherence
- **Status:** ❌ TODO - Medium Priority

---

## ⚖️ Evaluation Agents (Quality Assurance)

### 14. **QualityJudgeAgent** ❌ (Not Implemented)
- **Role:** Quality assessor
- **Expertise:** 12-dimension scoring (inherits V4 judge), line-level analysis
- **Replaces:** V4 Scene Judge
- **Status:** ❌ TODO - Medium Priority (Integrate V4 judge)

### 15. **ContinuityAgent** ❌ (Not Implemented)
- **Role:** Continuity auditor
- **Expertise:** Plot holes, character consistency, timeline validation
- **Replaces:** Stage 8 (Continuity Audit)
- **Status:** ❌ TODO - Medium Priority

### 16. **EmotionalAgent** ❌ (Not Implemented)
- **Role:** Emotional arc tracker
- **Expertise:** Emotional trajectory, reader impact prediction, mood consistency
- **Status:** ❌ TODO - Medium Priority

### 17. **ThemeAgent** ❌ (Not Implemented)
- **Role:** Thematic analyst
- **Expertise:** Thematic resonance, symbolic depth, theme presence validation
- **Replaces:** Stage 11 (Motif Infusion)
- **Status:** ❌ TODO - Medium Priority

---

## 🛠️ Support Agents (Cross-Cutting)

### 18. **MemoryAgent** ❌ (Not Implemented)
- **Role:** Memory manager
- **Expertise:** Semantic storage, context retrieval, consistency checking
- **Status:** ❌ TODO - Low Priority

### 19. **LearningAgent** ❌ (Not Implemented)
- **Role:** Pattern learner
- **Expertise:** Pattern extraction, quality tracking, strategy updates
- **Status:** ❌ TODO - Low Priority

### 20. **BudgetAgent** ❌ (Not Implemented)
- **Role:** Cost optimizer
- **Expertise:** Cost tracking, model selection, budget forecasting
- **Status:** ❌ TODO - Low Priority

### 21. **ResearchAgent** ❌ (Not Implemented)
- **Role:** Fact checker
- **Expertise:** Fact checking, cultural authenticity, technical accuracy
- **Status:** ❌ TODO - Low Priority

### 22. **ExportAgent** ❌ (Not Implemented)
- **Role:** Format specialist
- **Expertise:** Kindle formatting, multi-format export, professional styling
- **Status:** ❌ TODO - Low Priority

### 23. **AnalyticsAgent** ❌ (Not Implemented)
- **Role:** Performance analyst
- **Expertise:** Performance dashboards, quality trends, bottleneck identification
- **Status:** ❌ TODO - Low Priority

---

## 📊 Summary

### ✅ Implemented (4 agents)
1. ConductorAgent
2. ConceptAgent
3. StructureAgent
4. Base Agent (foundation class)

### ❌ Not Implemented (19 agents)
- **High Priority (2):** WorldAgent, CharacterAgent
- **Medium Priority (9):** DraftingAgent, DialogueAgent, ProseAgent, ActionAgent, DescriptionAgent, SynthesisAgent, QualityJudgeAgent, ContinuityAgent, EmotionalAgent, ThemeAgent
- **Low Priority (6):** MemoryAgent, LearningAgent, BudgetAgent, ResearchAgent, ExportAgent, AnalyticsAgent

### Total: 23 Agents Planned
- **4 Complete** (17%)
- **19 Remaining** (83%)

---

## Quick Reference by Category

### Planning (4 agents)
- ✅ ConceptAgent
- ❌ WorldAgent
- ✅ StructureAgent
- ❌ CharacterAgent

### Execution (6 agents)
- ❌ DraftingAgent
- ❌ DialogueAgent
- ❌ ProseAgent
- ❌ ActionAgent
- ❌ DescriptionAgent
- ❌ SynthesisAgent

### Evaluation (4 agents)
- ❌ QualityJudgeAgent
- ❌ ContinuityAgent
- ❌ EmotionalAgent
- ❌ ThemeAgent

### Support (6 agents)
- ❌ MemoryAgent
- ❌ LearningAgent
- ❌ BudgetAgent
- ❌ ResearchAgent
- ❌ ExportAgent
- ❌ AnalyticsAgent

### Core (3 agents)
- ✅ ConductorAgent
- ✅ Base Agent
- ✅ StageAgent (utility)

---

## Naming Convention

All agents follow the pattern: `[Domain]Agent`

Examples:
- `ConceptAgent` - handles concepts
- `DialogueAgent` - handles dialogue
- `MemoryAgent` - handles memory

The only exception is `ConductorAgent` which is the meta-orchestrator.



