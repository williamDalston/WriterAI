# ANBG: Autonomous Non-Fiction Book Generator

> **Transform any topic into a publication-quality non-fiction book with evidence-based content and proper pedagogical structure.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Status](https://img.shields.io/badge/status-core_complete-green.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 What is ANBG?

ANBG is a **universal, profile-driven system** that can generate any type of non-fiction book:
- 📚 Textbooks
- 💼 Business books  
- 📖 Memoirs
- 🔬 Academic texts
- 📘 Reference materials
- 🎓 How-to guides
- 🧬 Popular science

### Key Principles

1. **Evidence-First:** Every material claim requires citation from allowlisted sources
2. **Learning-First:** Dependency graphs ensure concepts are introduced in proper order
3. **Quality Gates:** 27+ objective, measurable metrics with blocking gates
4. **Universal:** Any non-fiction type via profiles, not hardcoded assumptions
5. **Verifiable:** Complete MANIFEST with sources, models, prompts, and timing

---

## ✨ Features

### 🔬 Evidence System
- **RAG-Based Citation:** Automatically finds and attaches citations from allowlisted sources
- **Multi-Format:** APA, MLA, Chicago, IEEE, Harvard citation styles
- **Fact-Checking:** BLOCKING gate validates all claims have proper citations
- **Link Validation:** Checks all URLs are reachable
- **Hallucination Detection:** Verifies citations actually support claims

### 📚 Learning System
- **Dependency Graphs:** DAG ensures no forward references
- **Bloom's Taxonomy:** Classifies objectives and exercises by cognitive level
- **Pedagogy Engine:** Generates scaffolded learning (I do → We do → You do)
- **Exercise Ladders:** Remember → Understand → Apply → Analyze progression
- **Learning Order Validation:** BLOCKING check ensures definitions before use

### 🎨 Content Units
- **Concept:** Core explanations with definitions and examples
- **Step:** Procedural instructions with screenshots
- **Case Study:** Real-world examples with analysis
- **Exercise:** Practice problems with solutions and hints
- **Quiz:** Assessments with mixed question types
- **Deep Dive:** Optional advanced material
- **Callouts:** Tips, warnings, best practices
- **Figures & Tables:** With required alt-text and captions

### 📊 Quality Metrics

**Factuality (BLOCKING):**
- Citation coverage ≥ 95%
- High-severity coverage ≥ 98%
- Hallucinated citations = 0

**Structure (BLOCKING):**
- Dependency graph violations = 0
- Objectives per chapter ≥ 3
- Forward references = 0

**Accessibility (BLOCKING):**
- Alt-text coverage = 100%
- TOC anchor resolution = 100%

**Pedagogy:**
- Hook coverage ≥ 90%
- Example density ≥ 1 per 600-700 words
- Transfer exercises ≥ 40%

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
cd "WriterAI nonfiction"

# Install dependencies
pip install -r requirements.txt

# Set up environment
export OPENAI_API_KEY="your-key-here"
```

### Create Your First Book

**1. Create a Profile**

```yaml
# configs/my_textbook.yaml
book_profile:
  type: textbook
  title: "Introduction to Python Programming"
  subtitle: "From Basics to Advanced"
  author: "Your Name"
  persona: "experienced software engineer and educator"
  audience: "beginner programmers"
  style_pack: practical
  citation_style: "APA"
  allowlisted_domains:
    - "python.org"
    - "docs.python.org"
    - "realpython.com"
  topic_seed: "A comprehensive introduction to Python programming covering basics, data structures, OOP, and real-world applications"
  enabled_unit_types:
    - concept
    - step
    - exercise
    - quiz
    - case_study

rigor_settings:
  evidence_rigor: strict
  pedagogy_mode: guided
  inspiration_dial: light

quality_thresholds:
  citation_coverage: 0.95
  dependency_graph_violations: 0
  alt_text_coverage: 1.0

project_name: python_intro_textbook
budget_usd: 100.0
```

**2. Run Generation** (coming soon)

```python
from prometheus_lib.models.nonfiction_profiles import ANBGProfile
from prometheus_lib.models.nonfiction_state import ANBGState
from prometheus_lib.models.content_schemas import BookManuscript
import yaml

# Load profile
with open('configs/my_textbook.yaml') as f:
    profile_data = yaml.safe_load(f)
    profile = ANBGProfile(**profile_data)

# Initialize state
manuscript = BookManuscript(
    title=profile.book_profile.title,
    author=profile.book_profile.author
)
state = ANBGState(profile=profile, manuscript=manuscript)

# Run pipeline (orchestrator in development)
# await run_anbg_pipeline(state)
```

---

## 📖 Profile System

### Book Types

```python
class BookType(str, Enum):
    TEXTBOOK = "textbook"
    SELF_HELP = "self_help"
    MEMOIR = "memoir"
    BUSINESS = "business"
    BIOGRAPHY = "biography"
    HISTORY = "history"
    REFERENCE = "reference"
    HOW_TO = "how_to"
    POPULAR_SCIENCE = "popular_science"
    ACADEMIC = "academic"
```

### Style Packs

| Style | Sentence Length | Citation Density | TL;DR | Best For |
|-------|----------------|------------------|-------|----------|
| **Practical** | Medium | Moderate | Yes | Textbooks, how-to |
| **Academic** | Long | High | No | Research, scholarly |
| **Narrative** | Varied | Low | No | Memoirs, stories |
| **Executive** | Short | Moderate | Yes | Business, summaries |

### Rigor Settings

```yaml
rigor_settings:
  evidence_rigor: standard | strict
  pedagogy_mode: guided | expert
  inspiration_dial: off | light | strong
  interactivity: none | quizzes | quizzes_and_labs
```

---

## 🏗️ Architecture

### Pipeline Stages

```
Stage 1:  Preflight ★              Validate profile, initialize
Stage 2:  Knowledge Ingestion      Index user sources (optional)
Stage 3:  Outline Planner ★        Build dependency graph, structure
Stage 4:  Unit Generator           Generate content units
Stage 5:  Evidence Attacher ★      Attach citations via RAG
Stage 6:  Fact-Check Gate ★        Verify all citations
Stage 7:  Exercises & Quizzes      Generate assessments
Stage 8:  Visuals & Figures        Add diagrams, alt-text
Stage 9:  Interlinking & Glossary  Cross-refs, glossary, index
Stage 10: Clarity & Accessibility  Readability, jargon
Stage 11: Compliance               Licenses, disclaimers
Stage 12: Formatting & Export ★    EPUB/PDF/HTML
Stage 13: Human Review             10-minute checklist

★ = Blocking gate (must pass to continue)
```

### Data Flow

```
Profile → Preflight → Concepts → Dependency Graph → Outline
    ↓
Units → Claims → Citations (RAG) → Fact-Check
    ↓
Exercises → Figures → Interlinking → Export
    ↓
EPUB + PDF + HTML + MANIFEST + QUALITY_SUMMARY
```

---

## 📋 Examples

### Example 1: Power BI Textbook

See `configs/textbook_powerbi.yaml`

**Features:**
- Strict evidence from microsoft.com, dax.guide
- Practical style with step-by-step tutorials
- Guided pedagogy with scaffolding
- Interactive HTML with quizzes
- 95% citation coverage required

### Example 2: Remote Teams Business Book

See `configs/business_book.yaml`

**Features:**
- Executive style with concise summaries
- Evidence from HBR, McKinsey, Gallup
- Expert pedagogy (dense content)
- Case studies and frameworks
- 90% citation coverage

### Example 3: Silicon Valley Memoir

See `configs/memoir.yaml`

**Features:**
- Narrative style with personal voice
- Standard evidence rigor
- Inspiration dial: strong (hooks, anecdotes)
- Reading level: 8 (accessible)
- Chicago citation style

---

## 🔧 Component APIs

### Citation Formatter

```python
from prometheus_lib.evidence import CitationFormatter
from prometheus_lib.models.nonfiction_profiles import CitationStyle

formatter = CitationFormatter(CitationStyle.APA)

citation = Citation(
    id="cite_001",
    source_url="https://python.org/docs/tutorial",
    source_domain="python.org",
    title="Python Tutorial",
    author="Python Software Foundation",
    date_accessed="2025-01-15"
)

# Format full citation
formatted = formatter.format_citation(citation)
# Output: "Python Software Foundation. (2025). Python Tutorial. python.org. https://python.org/docs/tutorial"

# Create in-text citation
in_text = formatter.create_in_text_citation(citation)
# Output: "(Python Software Foundation, 2025)"
```

### Dependency Builder

```python
from prometheus_lib.learning import DependencyBuilder

builder = DependencyBuilder(profile, llm_router)

# Extract concepts
concepts = await builder.extract_concepts_from_topic(
    topic="Introduction to Machine Learning",
    goals="Students will understand ML fundamentals and implement basic algorithms"
)

# Build graph
graph = await builder.build_dependency_graph(concepts)

# Validate (ensures no cycles)
is_valid, issues = graph.validate_dag()

# Get learning order
learning_order = graph.get_topological_order()
# Output: ['linear_algebra', 'calculus', 'probability', 'regression', 'classification', ...]
```

### Bloom Mapper

```python
from prometheus_lib.learning import BloomMapper

mapper = BloomMapper()

# Classify objective
objective = "Explain how neural networks process information"
level = mapper.classify_objective(objective)
# Output: BloomLevel.UNDERSTAND

# Get distribution
objectives = [...]  # List of LearningObjective objects
distribution = mapper.get_level_distribution(objectives)
# Output: {'remember': 2, 'understand': 5, 'apply': 3, 'analyze': 2}

# Check balance
balance = mapper.recommend_level_balance(distribution)
# Output: {'is_balanced': True, 'recommendations': []}
```

---

## 📊 Quality Reports

### QUALITY_SUMMARY Output

```
================================================================================
QUALITY SUMMARY
================================================================================
Project: power_bi_textbook
Book: Mastering Power BI
Generated: Wed Jan 15 2025 14:30:22

BLOCKING GATES (Must Pass)
--------------------------------------------------------------------------------
Citation Coverage: 96.3% (threshold: 95.0%) ✅ PASS
High Severity Citation: 98.5% (threshold: 98.0%) ✅ PASS
Hallucinated Citations: 0 (threshold: 0) ✅ PASS
Dependency Graph Violations: 0 (threshold: 0) ✅ PASS
Alt-Text Coverage: 100.0% (threshold: 100.0%) ✅ PASS
TOC Anchor Resolution: 100.0% (threshold: 100.0%) ✅ PASS

NON-BLOCKING METRICS
--------------------------------------------------------------------------------
Flesch Grade Level: 9.2 (target: ≤10)
Jargon Explained: 97.1% (target: ≥95.0%)
Hook Coverage: 91.7% (target: ≥90.0%)
Example Density: 0.0015 (target: ≥0.0014)

================================================================================
OVERALL STATUS: ✅ READY TO PUBLISH
================================================================================
```

### MANIFEST Output

```json
{
  "project_name": "power_bi_textbook",
  "book_title": "Mastering Power BI",
  "generation_seed": 42,
  "total_build_time_hours": 1.8,
  "models_used": {
    "outline_planner": ["gpt-4o-mini"],
    "unit_generator": ["gpt-4o-mini"],
    "evidence_attacher": ["gpt-4o-mini"]
  },
  "total_cost_usd": 87.45,
  "total_citations": 287,
  "allowlisted_domains": [
    "learn.microsoft.com",
    "docs.microsoft.com",
    "powerbi.microsoft.com"
  ],
  "quality_metrics": {
    "citation_coverage": 0.963,
    "dependency_graph_violations": 0,
    "all_blocking_gates_pass": true
  }
}
```

---

## 🎓 Pedagogical Features

### I Do / We Do / You Do Sequences

```python
from prometheus_lib.learning import PedagogyEngine

engine = PedagogyEngine(profile, llm_router)

# Generate scaffolded sequence
sequence = await engine.generate_scaffolded_sequence(
    objective=objective,
    context="Chapter 3: Data Modeling"
)

# Produces:
# - Demonstration unit (I do): Worked example with thinking visible
# - Guided practice (We do): Problem with hints and scaffolding
# - Independent practice (You do): Full exercise for transfer
```

### Exercise Ladders

```python
# Generate progression through Bloom levels
ladder = await engine.generate_exercise_ladder(
    objective=objective,
    context="Chapter 5: DAX Functions"
)

# Produces 4 exercises:
# 1. Remember (easy): "List the basic DAX aggregation functions"
# 2. Understand (medium): "Explain when to use CALCULATE vs CALCULATETABLE"
# 3. Apply (medium): "Create a DAX measure that calculates year-over-year growth"
# 4. Analyze (hard): "Debug this complex DAX formula and explain the error"
```

---

## 🚧 Current Status

### ✅ Completed (Phases 1-3)
- Core data models and profiles
- Evidence & citation system
- Learning & pedagogy system
- Stage 1: Preflight
- Stage 3: Outline Planner

### 🚧 In Progress (Phase 4)
- Stage 2: Knowledge Ingestion
- Stage 4: Unit Generator
- Stages 5-13: Processing and export

### ⏳ Planned (Phases 5-11)
- Quality orchestrator
- Export engines (EPUB/PDF/HTML)
- Performance optimizations
- Testing suite
- Complete documentation

---

## 📚 Documentation

- **[Implementation Progress](ANBG_IMPLEMENTATION_PROGRESS.md)** - Detailed progress tracker
- **[Transformation Summary](ANBG_TRANSFORMATION_SUMMARY.md)** - What's been built
- **[Master Prompt](../✳️ MASTER PROMPT)** - Original specification
- **[Example Profiles](configs/)** - Sample configurations

---

## 🤝 Contributing

ANBG is in active development. Contributions welcome for:
- Additional pipeline stages
- New unit types
- Export format support
- Quality metric calculators
- Prompt engineering
- Testing and validation

---

## 🎯 Roadmap

**v0.1 (Current):** Core infrastructure + 2 stages  
**v0.2 (Next):** All 13 stages implemented  
**v0.3:** Quality orchestrator + exports  
**v0.4:** Performance optimization + caching  
**v0.5:** Testing + documentation  
**v1.0:** Production-ready ANBG

---

## 📝 License

MIT (presumed from original WriterAI system)

---

## 🙏 Acknowledgments

**Transformed from:** WriterAI Fiction Novel Generation System  
**Pedagogical Frameworks:** Bloom's Taxonomy, Vygotsky's ZPD, Hattie's Visible Learning  
**Citation Standards:** APA, MLA, Chicago, IEEE, Harvard  
**Built with:** Python, Pydantic, NetworkX, OpenAI API

---

## 📧 Support

For questions, issues, or contributions, see the project repository.

---

**ANBG: Because non-fiction deserves the same AI innovation as fiction.** 📚


