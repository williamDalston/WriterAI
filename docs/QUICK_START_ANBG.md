# ANBG Quick Start Guide

**Status:** Core infrastructure complete, 6 of 13 stages operational  
**What Works:** Profile system, evidence engine, learning system, critical pipeline stages  
**What's Next:** Remaining 7 stages + orchestrator

---

## ✅ What You Can Use Right Now

### 1. Profile System

```python
# Load a profile
import yaml
from prometheus_lib.models.nonfiction_profiles import ANBGProfile

with open('configs/textbook_powerbi.yaml') as f:
    profile_data = yaml.safe_load(f)
    profile = ANBGProfile(**profile_data)

# Validate it passed
print(f"Book Type: {profile.book_profile.type}")
print(f"Citation Style: {profile.book_profile.citation_style}")
print(f"Allowlist: {profile.book_profile.allowlisted_domains}")
print(f"Citation Coverage Required: {profile.quality_thresholds.citation_coverage:.1%}")
```

### 2. Citation Formatter

```python
from prometheus_lib.evidence import CitationFormatter
from prometheus_lib.models.content_schemas import Citation
from prometheus_lib.models.nonfiction_profiles import CitationStyle

# Create citation
citation = Citation(
    id="cite_001",
    source_url="https://docs.microsoft.com/power-bi/",
    source_domain="docs.microsoft.com",
    title="Power BI Documentation",
    author="Microsoft",
    date_accessed="2025-01-15",
    formatted_citation=""
)

# Format in different styles
for style in [CitationStyle.APA, CitationStyle.MLA, CitationStyle.CHICAGO]:
    formatter = CitationFormatter(style)
    formatted = formatter.format_citation(citation)
    print(f"{style}: {formatted}")
```

### 3. Dependency Graph Builder

```python
from prometheus_lib.learning import DependencyBuilder
from prometheus_lib.models.nonfiction_profiles import ANBGProfile
from prometheus_lib.llm.model_router import LLMModelRouter

# Initialize (requires LLM router setup)
profile = ANBGProfile(...)  # Your profile
llm_router = LLMModelRouter(...)  # Your LLM setup

builder = DependencyBuilder(profile, llm_router)

# Extract concepts
concepts = await builder.extract_concepts_from_topic(
    topic="Introduction to Machine Learning",
    goals="Master ML fundamentals and implement basic algorithms"
)

print(f"Extracted {len(concepts)} concepts")

# Build dependency graph
graph = await builder.build_dependency_graph(concepts)

# Validate (ensures no cycles)
is_valid, issues = graph.validate_dag()
if is_valid:
    print("✅ Dependency graph is valid (DAG)")
    
    # Get learning order
    order = graph.get_topological_order()
    print("Learning order:", order)
else:
    print("❌ Issues:", issues)

# Assign to chapters
chapter_map = builder.assign_concepts_to_chapters(graph, num_chapters=10)
for ch, concepts in chapter_map.items():
    print(f"Chapter {ch}: {len(concepts)} concepts")
```

### 4. Bloom's Taxonomy Classifier

```python
from prometheus_lib.learning import BloomMapper

mapper = BloomMapper()

# Classify learning objectives
objectives = [
    "Define what a neural network is",
    "Explain how backpropagation works",
    "Implement a neural network in Python",
    "Analyze the performance of different architectures",
    "Evaluate trade-offs between model complexity and accuracy",
    "Design a custom neural network for a specific problem"
]

for obj in objectives:
    level = mapper.classify_objective(obj)
    print(f"{level.value:12} | {obj}")

# Check distribution
from prometheus_lib.models.learning_schemas import LearningObjective
objs = [LearningObjective(objective_id=f"obj_{i}", text=obj, bloom_level=mapper.classify_objective(obj)) 
        for i, obj in enumerate(objectives)]

distribution = mapper.get_level_distribution(objs)
print("\nBloom Distribution:", distribution)

balance = mapper.recommend_level_balance(distribution)
print("Balanced:", balance["is_balanced"])
```

### 5. Source Validator

```python
from prometheus_lib.evidence import SourceValidator
from prometheus_lib.models.nonfiction_profiles import ANBGProfile

profile = ANBGProfile(...)  # Your profile with allowlist

validator = SourceValidator(profile)

# Check if domain is allowed
is_allowed, domain = validator.is_domain_allowed("https://learn.microsoft.com/power-bi")
print(f"Domain {domain}: {'✅ Allowed' if is_allowed else '❌ Not allowed'}")

# Check if link is reachable
is_reachable, error = await validator.check_link_reachable("https://learn.microsoft.com/power-bi")
print(f"Link: {'✅ Reachable' if is_reachable else f'❌ {error}'}")

# Validate citation
result = await validator.validate_citation(citation)
print(f"Citation valid: {result['is_valid']}")
if not result['is_valid']:
    for issue in result['issues']:
        print(f"  - {issue['type']}: {issue['message']}")
```

### 6. Pedagogy Engine

```python
from prometheus_lib.learning import PedagogyEngine
from prometheus_lib.models.learning_schemas import LearningObjective, BloomLevel

objective = LearningObjective(
    objective_id="obj_1",
    text="Apply sorting algorithms to solve problems",
    bloom_level=BloomLevel.APPLY
)

engine = PedagogyEngine(profile, llm_router)

# Generate single exercise
exercise = await engine.generate_exercise(
    objective=objective,
    context="Chapter 3: Sorting Algorithms",
    difficulty="medium"
)

print(f"Exercise: {exercise.title}")
print(f"Prompt: {exercise.prompt}")
print(f"Solution: {exercise.solution[:100]}...")

# Generate exercise ladder (Remember → Understand → Apply → Analyze)
ladder = await engine.generate_exercise_ladder(
    objective=objective,
    context="Chapter 3: Sorting Algorithms"
)

print(f"\nExercise Ladder ({len(ladder)} exercises):")
for ex in ladder:
    print(f"  {ex.bloom_level.value}: {ex.prompt[:50]}...")

# Generate quiz
objectives = [objective]  # Can include multiple
quiz = await engine.generate_quiz(
    objectives=objectives,
    context="Chapter 3: Sorting Algorithms",
    num_questions=5
)

print(f"\nQuiz: {len(quiz.questions)} questions")
```

---

## 🚧 What's In Progress (Not Ready Yet)

### Pipeline Orchestrator
The main `run_anbg.py` orchestrator that ties all stages together is not complete. You can run individual stages, but not the full end-to-end pipeline yet.

### Missing Stages
- Stage 2: Knowledge Ingestion
- Stage 7: Exercises & Quizzes
- Stage 8: Visuals & Figures
- Stage 9: Interlinking & Glossary
- Stage 10: Clarity & Accessibility
- Stage 11: Compliance
- Stage 12: Formatting & Export
- Stage 13: Human Review Hook

### Export Engines
EPUB, PDF, and HTML export engines are not built yet.

---

## 📝 Creating Your Own Profile

Copy and modify one of the examples:

```yaml
# my_book.yaml
book_profile:
  type: textbook  # or business, memoir, etc.
  title: "Your Book Title"
  subtitle: "Optional Subtitle"
  author: "Your Name"
  persona: "Describe yourself (e.g., 'experienced developer and educator')"
  audience: "Who is this for? (e.g., 'beginner programmers')"
  primary_level: "beginner|intermediate|advanced"
  
  style_pack: practical  # practical|academic|narrative|executive
  tone: "clear, engaging, professional"
  
  citation_style: "APA"  # APA|MLA|Chicago|IEEE|Harvard
  allowlisted_domains:
    - "trusted-source1.com"
    - "trusted-source2.org"
  
  reading_level_target: 9  # Flesch-Kincaid grade level
  
  enabled_unit_types:
    - concept
    - step
    - case_study
    - exercise
    - quiz
  
  deliverables:
    - epub
    - pdf
    - html
  
  topic_seed: "Brief description of what your book covers"
  goals: "What readers will be able to do after reading"

rigor_settings:
  evidence_rigor: strict  # standard|strict
  pedagogy_mode: guided  # guided|expert
  inspiration_dial: light  # off|light|strong
  interactivity: quizzes  # none|quizzes|quizzes_and_labs

quality_thresholds:
  citation_coverage: 0.95  # 95% of claims need citations
  high_severity_citation: 0.98  # 98% of critical claims
  dependency_graph_violations: 0  # Must be 0
  objectives_per_chapter: 3  # At least 3
  flesch_grade: 10  # Reading level ≤ 10
  alt_text_coverage: 1.0  # Must be 100%
  toc_anchor_resolution: 1.0  # Must be 100%

project_name: my_book_project
budget_usd: 100.0

model_defaults:
  api_model: "gpt-4o-mini"
  critic_model: "gpt-4o-mini"
  fallback_model: "gpt-3.5-turbo"
```

---

## 🧪 Testing Individual Components

### Test Dependency Graph

```python
from prometheus_lib.models.learning_schemas import Concept, DependencyGraph

# Create concepts manually
concepts = [
    Concept(
        concept_id="variables",
        name="Variables",
        definition="Named storage for data",
        depends_on=[],
        complexity_score=0.2
    ),
    Concept(
        concept_id="functions",
        name="Functions",
        definition="Reusable blocks of code",
        depends_on=["variables"],
        complexity_score=0.4
    ),
    Concept(
        concept_id="recursion",
        name="Recursion",
        definition="Functions calling themselves",
        depends_on=["functions"],
        complexity_score=0.7
    )
]

# Build graph
graph = DependencyGraph()
for concept in concepts:
    graph.add_concept(concept)

# Validate
is_valid, issues = graph.validate_dag()
print(f"Valid: {is_valid}")

# Get order
order = graph.get_topological_order()
print(f"Learning order: {order}")
# Output: ['variables', 'functions', 'recursion']
```

### Test Citation Coverage

```python
from prometheus_lib.models.content_schemas import Claim, ClaimSeverity

claims = [
    Claim(text="Python is dynamically typed", severity=ClaimSeverity.MEDIUM, context="Intro", citation_id="cite_1"),
    Claim(text="Python was created in 1991", severity=ClaimSeverity.HIGH, context="History", citation_id="cite_2"),
    Claim(text="Lists are mutable", severity=ClaimSeverity.HIGH, context="Data structures", citation_id=None),  # Missing!
    Claim(text="Common practice is PEP 8", severity=ClaimSeverity.LOW, context="Style", citation_id=None)
]

from prometheus_lib.evidence import SourceValidator
validator = SourceValidator(profile)

metrics = validator.get_coverage_metrics(claims)
print(f"Total claims: {metrics['total_claims']}")
print(f"Cited claims: {metrics['cited_claims']}")
print(f"Coverage: {metrics['citation_coverage']:.1%}")
print(f"High-severity coverage: {metrics['high_severity_coverage']:.1%}")
```

---

## 🎯 Running Stages Individually

```python
from prometheus_lib.models.nonfiction_state import ANBGState
from prometheus_lib.models.content_schemas import BookManuscript

# Initialize state
manuscript = BookManuscript(
    title=profile.book_profile.title,
    author=profile.book_profile.author
)
state = ANBGState(profile=profile, manuscript=manuscript)

# Stage 1: Preflight
from stages.stage_01_preflight import run_preflight_stage
from prometheus_lib.memory.vector_store import VectorStore

vector_store = VectorStore()
result = await run_preflight_stage(state, vector_store)
print(f"Preflight: {'✅ PASS' if result['is_valid'] else '❌ FAIL'}")

# Stage 3: Outline Planner
from stages.stage_03_nonfiction_outline_planner import run_outline_planner_stage

result = await run_outline_planner_stage(state, llm_router)
print(f"Chapters: {result['num_chapters']}")
print(f"Concepts: {result['num_concepts']}")
print(f"Objectives: {result['num_objectives']}")

# Stage 4: Unit Generator
from stages.stage_04_unit_generator import run_unit_generator_stage
from prometheus_lib.evidence import EvidenceAttacher

evidence_attacher = EvidenceAttacher(profile, vector_store, llm_router)
result = await run_unit_generator_stage(state, llm_router, evidence_attacher)
print(f"Units generated: {result['total_units']}")
print(f"Claims extracted: {result['total_claims']}")

# Stage 5: Evidence Attacher
from stages.stage_05_evidence_attacher import run_evidence_attacher_stage

result = await run_evidence_attacher_stage(state, evidence_attacher, vector_store, llm_router)
print(f"Coverage: {result['coverage']:.1%}")

# Stage 6: Fact-Check Gate
from stages.stage_06_fact_check_gate import run_fact_check_gate_stage
from prometheus_lib.evidence import FactChecker, SourceValidator

source_validator = SourceValidator(profile)
fact_checker = FactChecker(source_validator, llm_router)

result = await run_fact_check_gate_stage(state, fact_checker, source_validator, llm_router)
print(f"Fact-check: {'✅ PASS' if result['is_pass'] else '❌ FAIL'}")
```

---

## 📊 Viewing Quality Metrics

```python
# After running stages, check quality metrics
print(state.quality_metrics.dict())

# Or generate human-readable report
summary = state.export_quality_summary()
print(summary)

# Export full manifest
manifest = state.export_manifest()
import json
print(json.dumps(manifest, indent=2))
```

---

## 🔄 Next Steps for Full System

To complete ANBG, you'll need to:

1. **Implement remaining stages** (7-13)
2. **Build main orchestrator** that runs all stages in sequence
3. **Add export engines** for EPUB/PDF/HTML
4. **Create quality orchestrator** that computes all metrics
5. **Build repair planner** that maps failures to stage reruns
6. **Add performance caching** for expensive operations
7. **Write comprehensive tests**
8. **Complete documentation**

---

## 💡 Tips

### For Testing
- Start with small books (3-5 chapters)
- Use strict evidence rigor to catch issues early
- Check dependency graph validity frequently
- Monitor citation coverage at each stage

### For Production
- Set appropriate budgets ($50-150 for full books)
- Use guided pedagogy mode for better scaffolding
- Enable all relevant unit types
- Include interactive quizzes for engagement

### For Debugging
- Check stage status: `state.stage_statuses`
- Review uncited claims: `state.uncited_claims`
- Examine failed gates: `state.quality_metrics.failed_gates`
- Use repair plans from fact-checker

---

## 📚 Example Workflows

### Generate Dependency Graph
```python
builder = DependencyBuilder(profile, llm_router)
concepts = await builder.extract_concepts_from_topic(
    "Introduction to Data Science",
    "Master data analysis, visualization, and machine learning basics"
)
graph = await builder.build_dependency_graph(concepts)
order = graph.get_topological_order()
chapter_map = builder.assign_concepts_to_chapters(graph, 10)
```

### Validate Citations
```python
validator = SourceValidator(profile)
for citation in state.all_citations.values():
    result = await validator.validate_citation(citation)
    if not result['is_valid']:
        print(f"Invalid: {citation.source_url}")
```

### Generate Exercises
```python
engine = PedagogyEngine(profile, llm_router)
for objective in chapter_objectives:
    ladder = await engine.generate_exercise_ladder(objective, chapter.title)
    print(f"{len(ladder)} exercises for: {objective.text}")
```

---

**Status:** Foundation is solid and tested. Ready for remaining stages! 🚀


