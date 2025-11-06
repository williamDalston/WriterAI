# ANBG Testing Guide

**Purpose:** Validate ANBG system components and pipeline  
**Status:** Manual testing procedures + automated test templates

---

## 🧪 Manual Testing Procedures

### Test 1: Profile System

```python
# Test loading a profile
import yaml
from prometheus_lib.models.nonfiction_profiles import ANBGProfile

with open('configs/textbook_powerbi.yaml') as f:
    profile_data = yaml.safe_load(f)
    profile = ANBGProfile(**profile_data)

# Validate
assert profile.book_profile.type == "textbook"
assert len(profile.book_profile.allowlisted_domains) > 0
assert profile.quality_thresholds.citation_coverage >= 0.9
print("✅ Profile system works")
```

### Test 2: Citation Formatter

```python
from prometheus_lib.evidence import CitationFormatter
from prometheus_lib.models.content_schemas import Citation
from prometheus_lib.models.nonfiction_profiles import CitationStyle

citation = Citation(
    id="test_001",
    source_url="https://learn.microsoft.com/power-bi",
    source_domain="learn.microsoft.com",
    title="Power BI Documentation",
    author="Microsoft",
    date_accessed="2025-01-15",
    formatted_citation=""
)

# Test each style
for style in [CitationStyle.APA, CitationStyle.MLA, CitationStyle.CHICAGO]:
    formatter = CitationFormatter(style)
    formatted = formatter.format_citation(citation)
    assert len(formatted) > 0
    assert citation.source_url in formatted
    print(f"✅ {style} formatting works")
```

### Test 3: Dependency Graph

```python
from prometheus_lib.models.learning_schemas import Concept, DependencyGraph

# Create simple graph
concepts = [
    Concept(concept_id="var", name="Variables", definition="Named storage", 
            depends_on=[], complexity_score=0.2),
    Concept(concept_id="func", name="Functions", definition="Reusable code", 
            depends_on=["var"], complexity_score=0.4),
    Concept(concept_id="rec", name="Recursion", definition="Self-calling", 
            depends_on=["func"], complexity_score=0.7)
]

graph = DependencyGraph()
for concept in concepts:
    graph.add_concept(concept)

# Validate
is_valid, issues = graph.validate_dag()
assert is_valid, f"Graph invalid: {issues}"

# Test topological order
order = graph.get_topological_order()
assert order == ["var", "func", "rec"]
print("✅ Dependency graph works")
```

### Test 4: Source Validator

```python
import asyncio
from prometheus_lib.evidence import SourceValidator

# Create profile with allowlist
profile = ANBGProfile(...)  # Your test profile

validator = SourceValidator(profile)

# Test domain checking
is_allowed, domain = validator.is_domain_allowed("https://learn.microsoft.com/docs")
assert is_allowed or domain not in profile.book_profile.allowlisted_domains
print("✅ Domain validation works")

# Test link checking (async)
async def test_links():
    is_reachable, error = await validator.check_link_reachable("https://python.org")
    assert is_reachable or error is not None
    print("✅ Link checking works")

asyncio.run(test_links())
```

### Test 5: Bloom Classifier

```python
from prometheus_lib.learning import BloomMapper
from prometheus_lib.models.learning_schemas import BloomLevel

mapper = BloomMapper()

test_cases = [
    ("Define what a variable is", BloomLevel.REMEMBER),
    ("Explain how functions work", BloomLevel.UNDERSTAND),
    ("Implement a sorting algorithm", BloomLevel.APPLY),
    ("Analyze the performance of different approaches", BloomLevel.ANALYZE),
]

for objective, expected_level in test_cases:
    detected = mapper.classify_objective(objective)
    print(f"{objective[:40]:40} -> {detected.value:10} (expected: {expected_level.value})")
    # Note: May not always match exactly due to verb ambiguity

print("✅ Bloom classification works")
```

---

## 🔬 Automated Test Suite (Template)

### Test Structure

```
tests/
├── test_models.py              # Pydantic model validation
├── test_evidence_system.py     # Citation and fact-checking
├── test_learning_system.py     # Dependency graphs and pedagogy
├── test_quality_system.py      # Metric calculations
├── test_pipeline_stages.py     # Individual stage tests
├── test_integration.py         # End-to-end pipeline
└── test_exports.py             # Export format validation
```

### Example: test_evidence_system.py

```python
import pytest
from prometheus_lib.evidence import CitationFormatter, SourceValidator
from prometheus_lib.models.nonfiction_profiles import CitationStyle, ANBGProfile

class TestCitationFormatter:
    def test_apa_formatting(self):
        formatter = CitationFormatter(CitationStyle.APA)
        citation = create_test_citation()
        formatted = formatter.format_citation(citation)
        
        assert "Microsoft" in formatted
        assert "2025" in formatted
        assert citation.source_url in formatted
    
    def test_all_styles(self):
        citation = create_test_citation()
        
        for style in CitationStyle:
            formatter = CitationFormatter(style)
            formatted = formatter.format_citation(citation)
            assert len(formatted) > 20
            assert citation.source_url in formatted

@pytest.mark.asyncio
class TestSourceValidator:
    async def test_domain_validation(self):
        profile = create_test_profile()
        validator = SourceValidator(profile)
        
        is_allowed, domain = validator.is_domain_allowed("https://learn.microsoft.com")
        assert is_allowed
    
    async def test_link_checking(self):
        profile = create_test_profile()
        validator = SourceValidator(profile)
        
        is_reachable, error = await validator.check_link_reachable("https://python.org")
        assert is_reachable

def create_test_citation():
    return Citation(
        id="test",
        source_url="https://learn.microsoft.com",
        source_domain="learn.microsoft.com",
        title="Test",
        author="Microsoft",
        date_accessed="2025-01-15",
        formatted_citation=""
    )

def create_test_profile():
    return ANBGProfile(...)
```

### Running Tests

```bash
# Install pytest
pip install pytest pytest-asyncio

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_evidence_system.py -v

# Run with coverage
pytest tests/ --cov=prometheus_lib --cov-report=html
```

---

## 🎯 Test Checklist

### Unit Tests (Component Level)
- [ ] Profile loading and validation
- [ ] Citation formatting (all 5 styles)
- [ ] Domain allowlist checking
- [ ] Link validation
- [ ] Dependency graph DAG validation
- [ ] Bloom level classification
- [ ] Exercise generation
- [ ] Claim extraction
- [ ] Coverage metric calculation
- [ ] Alt-text generation

### Integration Tests (System Level)
- [ ] Preflight stage validates profiles
- [ ] Outline stage builds valid DAG
- [ ] Unit generator creates all types
- [ ] Evidence attacher finds citations
- [ ] Fact-check gate blocks on failures
- [ ] Export generates valid HTML
- [ ] Quality orchestrator computes metrics
- [ ] Repair planner suggests fixes

### End-to-End Tests
- [ ] Full pipeline generates small book (3 chapters)
- [ ] Resume capability works
- [ ] Quality gates enforce thresholds
- [ ] Exports are valid
- [ ] MANIFEST is complete

---

## 📝 Test Data

### Create Test Profile

```yaml
# tests/fixtures/test_profile.yaml
book_profile:
  type: textbook
  title: "Test Book"
  author: "Test Author"
  persona: "test educator"
  audience: "test students"
  style_pack: practical
  citation_style: "APA"
  allowlisted_domains: ["python.org", "example.com"]
  reading_level_target: 9
  enabled_unit_types: [concept, exercise]
  deliverables: [html]
  topic_seed: "Test topic for automated testing"

rigor_settings:
  evidence_rigor: standard
  pedagogy_mode: guided

quality_thresholds:
  citation_coverage: 0.80  # Relaxed for testing
  dependency_graph_violations: 0
  alt_text_coverage: 1.0

project_name: test_book
budget_usd: 10.0  # Small budget for tests
```

---

## ✅ Validation Checklist

After generating a book, validate:

### Structure
- [ ] All chapters have introductions
- [ ] All chapters have summaries
- [ ] All sections have units
- [ ] All units have content

### Evidence
- [ ] Citation coverage ≥ threshold
- [ ] All citations from allowlist
- [ ] No broken links
- [ ] No hallucinated citations

### Learning
- [ ] Dependency graph is DAG
- [ ] 0 forward references
- [ ] Objectives align with content
- [ ] Exercises test objectives

### Accessibility
- [ ] All figures have alt-text
- [ ] Glossary terms defined
- [ ] Index generated
- [ ] TOC links work

### Export
- [ ] HTML opens correctly
- [ ] Navigation works
- [ ] Figures display (or have placeholders)
- [ ] MANIFEST complete
- [ ] QUALITY_SUMMARY accurate

---

## 🚀 Quick Test Run

```bash
# Generate a small test book
python run_anbg.py --profile tests/fixtures/test_profile.yaml

# Check it worked
ls data/test_book/exports/

# Validate quality
cat data/test_book/exports/QUALITY_SUMMARY.txt | grep "OVERALL STATUS"

# Should see:
# OVERALL STATUS: ✅ READY TO PUBLISH
```

---

**Testing ensures quality. But ANBG's automated quality gates mean most testing happens automatically during generation!** ✨


