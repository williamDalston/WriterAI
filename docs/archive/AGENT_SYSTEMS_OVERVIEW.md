# Agent Systems Overview - Complete Guide

**Two distinct agent systems for WriterAI**

---

## 🎯 Two Agent Systems

### 1. Worker Agents (Letters: A, B, C...) 
**Purpose:** Build and improve the WriterAI project itself  
**Work on:** Project codebase (code, tests, docs, configs)  
**When:** During development/automation  
**Naming:** Letters (A, B, C, D, E, F, G, H, I, J...)

### 2. Runtime Agents (Numbers: #1, #2, #3... #22)
**Purpose:** Generate novels when the project runs  
**Work on:** Novel content (themes, scenes, prose)  
**When:** During novel generation  
**Naming:** Numbers (#1, #2, #3... #22)

---

## 📋 Worker Agents (Letters) - Project Development

### Agent A: CodeGeneratorAgent ✅
**Purpose:** Generate code for new features, agents, modules

**Run:**
```bash
python worker_agents.py A --task "generate WorldAgent implementation"
```

### Agent B: TestGeneratorAgent ✅
**Purpose:** Generate and maintain test suites

**Run:**
```bash
python worker_agents.py B --task "generate tests for WorldAgent"
```

### Agent C: DocumentationAgent ✅
**Purpose:** Generate and maintain documentation

**Run:**
```bash
python worker_agents.py C --task "document WorldAgent"
```

### Agent D: RefactorAgent ❌ (TODO)
**Purpose:** Improve code quality through refactoring

### Agent E: QualityAgent ❌ (TODO)
**Purpose:** Monitor and improve code quality

### Agent F: FeatureAgent ❌ (TODO)
**Purpose:** Implement new features end-to-end

### Agent G: BugFixAgent ❌ (TODO)
**Purpose:** Identify and fix bugs

### Agent H: IntegrationAgent ❌ (TODO)
**Purpose:** Integrate new components with existing system

### Agent I: PerformanceAgent ❌ (TODO)
**Purpose:** Optimize performance

### Agent J: SecurityAgent ❌ (TODO)
**Purpose:** Ensure security best practices

---

## 📋 Runtime Agents (Numbers) - Novel Generation

### Agent #1: ConductorAgent ✅
**Purpose:** Meta-orchestrator for novel generation

**Run:**
```bash
python run_agent.py 1
```

### Agent #2: Base Agent ✅
**Purpose:** Foundation class for all agents

### Agent #3: ConceptAgent ✅
**Purpose:** Generates themes, motifs, central questions

**Run:**
```bash
python run_agent.py 3
```

### Agent #4: WorldAgent ❌ (TODO)
**Purpose:** World-building specialist

### Agent #5: StructureAgent ✅
**Purpose:** Creates beat sheets, act timing, scene sequences

**Run:**
```bash
python run_agent.py 5
```

### Agent #6: CharacterAgent ❌ (TODO)
**Purpose:** Character psychologist

### Agent #7-22: (See AGENT_RUN_GUIDE.md for full list)

---

## 🔄 How They Work Together

### Example: Implementing WorldAgent

**Step 1: Worker Agents (Development)**
```bash
# Agent A generates code
python worker_agents.py A --task "generate WorldAgent implementation" --target-file "prometheus_novel/prometheus_lib/agents_v5/planning_agents.py"

# Agent B generates tests
python worker_agents.py B --task "generate tests for WorldAgent"

# Agent C generates documentation
python worker_agents.py C --task "document WorldAgent"
```

**Step 2: Runtime Agents (Novel Generation)**
```bash
# Now WorldAgent (#4) is available for novel generation
python prometheus generate --config configs/my_novel.yaml
# Agent #4 (WorldAgent) will be used during generation
```

---

## 📊 Quick Reference

### Worker Agents (Letters)
- **List:** `python worker_agents.py list`
- **Run:** `python worker_agents.py <letter> --task "<task>"`
- **Example:** `python worker_agents.py A --task "generate CharacterAgent"`

### Runtime Agents (Numbers)
- **List:** `python run_agent.py list`
- **Run:** `python run_agent.py <number>`
- **Example:** `python run_agent.py 3`

---

## 🎯 Summary

**Two Systems:**

1. **Worker Agents (A-J)** - Build the project
   - Automate development
   - Generate code
   - Improve quality
   - Meta-level operations

2. **Runtime Agents (#1-22)** - Generate novels
   - Work during execution
   - Generate content
   - Novel generation
   - Content-level operations

**Both systems work together to:**
- Automate project development (Worker Agents)
- Generate high-quality novels (Runtime Agents)

---

**Ready to use both systems!**



