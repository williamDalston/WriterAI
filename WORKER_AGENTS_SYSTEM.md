# Worker Agents System - Project Development Automation

**Worker Agents (Letters: A, B, C...) - Build and improve the WriterAI project itself**

---

## 🎯 Purpose

Worker Agents automate the **development and improvement** of the WriterAI project:
- Code generation
- Testing
- Documentation
- Refactoring
- Quality improvements
- Feature development
- Bug fixes

**These are META-AGENTS that work on the project codebase itself, not on novel generation.**

---

## 📋 Worker Agent Registry (Letters)

### Agent A: CodeGeneratorAgent
**Purpose:** Generate code for new features, agents, modules

**Capabilities:**
- Generate agent implementations from templates
- Create new modules following project patterns
- Generate tests for new code
- Create documentation from code

**Example Use:**
```bash
python worker_agents.py A --task "generate CharacterAgent implementation"
```

---

### Agent B: TestGeneratorAgent
**Purpose:** Generate and maintain test suites

**Capabilities:**
- Generate unit tests for new code
- Generate integration tests
- Update existing tests
- Run test suites and report results

**Example Use:**
```bash
python worker_agents.py B --task "generate tests for all planning agents"
```

---

### Agent C: DocumentationAgent
**Purpose:** Generate and maintain documentation

**Capabilities:**
- Generate API documentation
- Update README files
- Create usage guides
- Generate architecture diagrams
- Keep docs in sync with code

**Example Use:**
```bash
python worker_agents.py C --task "update all agent documentation"
```

---

### Agent D: RefactorAgent
**Purpose:** Improve code quality through refactoring

**Capabilities:**
- Identify code smells
- Suggest refactoring opportunities
- Apply safe refactorings
- Improve code organization
- Optimize performance

**Example Use:**
```bash
python worker_agents.py D --task "refactor agent communication system"
```

---

### Agent E: QualityAgent
**Purpose:** Monitor and improve code quality

**Capabilities:**
- Run linters and fix issues
- Check code coverage
- Identify security issues
- Enforce coding standards
- Generate quality reports

**Example Use:**
```bash
python worker_agents.py E --task "check code quality and fix issues"
```

---

### Agent F: FeatureAgent
**Purpose:** Implement new features end-to-end

**Capabilities:**
- Plan feature implementation
- Generate code
- Create tests
- Update documentation
- Integrate with existing code

**Example Use:**
```bash
python worker_agents.py F --task "implement WorldAgent with full integration"
```

---

### Agent G: BugFixAgent
**Purpose:** Identify and fix bugs

**Capabilities:**
- Analyze error logs
- Identify root causes
- Generate fixes
- Test fixes
- Update related code

**Example Use:**
```bash
python worker_agents.py G --task "fix all failing tests"
```

---

### Agent H: IntegrationAgent
**Purpose:** Integrate new components with existing system

**Capabilities:**
- Identify integration points
- Update imports and dependencies
- Modify existing code for compatibility
- Test integrations
- Resolve conflicts

**Example Use:**
```bash
python worker_agents.py H --task "integrate new agents with conductor"
```

---

### Agent I: PerformanceAgent
**Purpose:** Optimize performance

**Capabilities:**
- Profile code execution
- Identify bottlenecks
- Suggest optimizations
- Implement performance improvements
- Benchmark changes

**Example Use:**
```bash
python worker_agents.py I --task "optimize agent communication latency"
```

---

### Agent J: SecurityAgent
**Purpose:** Ensure security best practices

**Capabilities:**
- Scan for vulnerabilities
- Check API key handling
- Review authentication
- Suggest security improvements
- Update security policies

**Example Use:**
```bash
python worker_agents.py J --task "audit security and fix issues"
```

---

## 🔄 Worker Agent Workflow

### Example: Implementing a New Runtime Agent

```
1. Agent F (FeatureAgent) plans implementation
   ↓
2. Agent A (CodeGeneratorAgent) generates code
   ↓
3. Agent B (TestGeneratorAgent) generates tests
   ↓
4. Agent H (IntegrationAgent) integrates with system
   ↓
5. Agent E (QualityAgent) checks quality
   ↓
6. Agent C (DocumentationAgent) updates docs
   ↓
7. Agent B (TestGeneratorAgent) runs full test suite
   ↓
8. Agent F (FeatureAgent) marks feature complete
```

---

## 🎯 Runtime Agents (Numbers) - Novel Generation

**Runtime Agents (#1-22) - Work DURING novel generation**

These are the agents that operate when you run:
```bash
python prometheus generate --config configs/my_novel.yaml
```

They work on **novel content**, not project code:
- Agent #3: ConceptAgent - Generates themes for the novel
- Agent #5: StructureAgent - Creates plot structure for the novel
- Agent #7: DraftingAgent - Writes scene prose for the novel
- etc.

---

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────┐
│              WORKER AGENTS (Letters)                    │
│  Build and improve the WriterAI project itself         │
│  A: CodeGen  B: Tests  C: Docs  D: Refactor  etc.     │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              WRITERAI PROJECT CODEBASE                   │
│  All the code, tests, docs, configs                      │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│           RUNTIME AGENTS (Numbers)                       │
│  Work during novel generation                           │
│  #1: Conductor  #3: Concept  #5: Structure  etc.       │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              GENERATED NOVELS                            │
│  The actual novel outputs                               │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Run Worker Agent
```bash
# Generate code for a new agent
python worker_agents.py A --task "generate WorldAgent implementation"

# Generate tests
python worker_agents.py B --task "generate tests for WorldAgent"

# Update documentation
python worker_agents.py C --task "document WorldAgent"

# Full feature implementation
python worker_agents.py F --task "implement WorldAgent end-to-end"
```

### Run Runtime Agent (Novel Generation)
```bash
# Use numbered agents during novel generation
python prometheus generate --config configs/my_novel.yaml

# Or run individual runtime agents
python run_agent.py 3  # ConceptAgent
python run_agent.py 5  # StructureAgent
```

---

## 📝 Naming Convention

- **Worker Agents:** Letters (A, B, C, D, E, F, G, H, I, J...)
  - Work on project codebase
  - Development automation
  - Meta-level operations

- **Runtime Agents:** Numbers (#1, #2, #3... #22)
  - Work on novel content
  - Novel generation
  - Content-level operations

---

## 🎯 Example: Complete Automation

### Scenario: Implement WorldAgent

**Worker Agents (Development):**
```bash
# 1. Plan implementation
python worker_agents.py F --task "plan WorldAgent implementation"

# 2. Generate code
python worker_agents.py A --task "generate WorldAgent code from template"

# 3. Generate tests
python worker_agents.py B --task "generate tests for WorldAgent"

# 4. Integrate
python worker_agents.py H --task "integrate WorldAgent with ConductorAgent"

# 5. Quality check
python worker_agents.py E --task "check WorldAgent code quality"

# 6. Documentation
python worker_agents.py C --task "document WorldAgent"

# 7. Final test
python worker_agents.py B --task "run full test suite"
```

**Runtime Agents (Novel Generation):**
```bash
# Now WorldAgent (#4) is available for novel generation
python prometheus generate --config configs/my_novel.yaml
# Agent #4 (WorldAgent) will be used during generation
```

---

## 🔧 Implementation Plan

### Phase 1: Core Worker Agents
1. **Agent A:** CodeGeneratorAgent
2. **Agent B:** TestGeneratorAgent
3. **Agent C:** DocumentationAgent

### Phase 2: Quality Worker Agents
4. **Agent D:** RefactorAgent
5. **Agent E:** QualityAgent

### Phase 3: Feature Worker Agents
6. **Agent F:** FeatureAgent
7. **Agent G:** BugFixAgent
8. **Agent H:** IntegrationAgent

### Phase 4: Advanced Worker Agents
9. **Agent I:** PerformanceAgent
10. **Agent J:** SecurityAgent

---

## 📋 Summary

**Two Agent Systems:**

1. **Worker Agents (Letters)** - Build the project
   - Automate development
   - Generate code
   - Improve quality
   - Meta-level operations

2. **Runtime Agents (Numbers)** - Generate novels
   - Work during execution
   - Generate content
   - Novel generation
   - Content-level operations

**Both systems work together to:**
- Automate project development (Worker Agents)
- Generate high-quality novels (Runtime Agents)

---

**Ready to implement Worker Agents? Let's start with Agent A (CodeGeneratorAgent)!**



