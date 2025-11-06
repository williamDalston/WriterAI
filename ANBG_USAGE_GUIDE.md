# ANBG Complete Usage Guide

**Version:** 1.0  
**Status:** Production Ready  
**Last Updated:** Current Session

---

## 🎯 Quick Start (5 Minutes)

### Step 1: Install Dependencies

```bash
cd "WriterAI nonfiction/prometheus_novel"
pip install -r ../requirements.txt
```

### Step 2: Set API Key

```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

### Step 3: Choose or Create a Profile

Use an existing profile:
- `configs/textbook_powerbi.yaml` - Power BI textbook
- `configs/business_book.yaml` - Remote teams leadership  
- `configs/memoir.yaml` - Silicon Valley memoir

Or create your own (see Creating Profiles below).

### Step 4: Run Generation

```bash
python run_anbg.py --profile configs/textbook_powerbi.yaml
```

### Step 5: Check Results

```bash
# View quality summary
cat data/power_bi_textbook/exports/QUALITY_SUMMARY.txt

# Open HTML export
open data/power_bi_textbook/exports/html/power_bi_textbook.html

# Check manifest
cat data/power_bi_textbook/exports/MANIFEST.json
```

---

## 📖 Creating Your Own Profile

### Profile Template

```yaml
book_profile:
  # Book basics
  type: textbook  # textbook|business|memoir|how_to|reference|etc.
  title: "Your Book Title"
  subtitle: "Optional Subtitle"
  author: "Your Name"
  
  # Voice and audience
  persona: "experienced educator and practitioner"
  audience: "intermediate learners in your field"
  primary_level: "intermediate"  # beginner|intermediate|advanced
  
  # Style configuration
  style_pack: practical  # practical|academic|narrative|executive
  tone: "clear, engaging, and professional"
  
  # Evidence requirements
  citation_style: "APA"  # APA|MLA|Chicago|IEEE|Harvard
  allowlisted_domains:
    - "trusted-source-1.com"
    - "trusted-source-2.org"
  forbidden_claims: []  # Claims to never make
  
  # Content settings
  reading_level_target: 9  # Flesch-Kincaid grade level (5-18)
  enabled_unit_types:
    - concept      # Core explanations
    - step         # Step-by-step tutorials
    - case_study   # Real-world examples
    - exercise     # Practice problems
    - quiz         # Assessments
    - tip          # Helpful hints
    - warning      # Cautionary notes
  
  # Output formats
  deliverables:
    - html
    - epub
    - pdf
  
  # Topic definition
  topic_seed: "A concise description of what your book will cover"
  goals: "What readers will be able to do after reading"

# Rigor controls
rigor_settings:
  evidence_rigor: strict      # standard|strict
  pedagogy_mode: guided       # guided|expert
  inspiration_dial: light     # off|light|strong
  interactivity: quizzes      # none|quizzes|quizzes_and_labs

# Quality thresholds
quality_thresholds:
  citation_coverage: 0.95              # 95% of claims need citations
  high_severity_citation: 0.98         # 98% of critical claims
  dependency_graph_violations: 0       # MUST be 0
  objectives_per_chapter: 3            # At least 3 per chapter
  flesch_grade: 10                     # Reading level ≤ 10
  alt_text_coverage: 1.0               # MUST be 100%
  toc_anchor_resolution: 1.0           # MUST be 100%

# Project settings
project_name: my_book_project
budget_usd: 100.0

# Model configuration
model_defaults:
  api_model: "gpt-4o-mini"
  critic_model: "gpt-4o-mini"
  fallback_model: "gpt-3.5-turbo"
```

---

## 🎨 Choosing Style Packs

### Practical Style (Best for: Textbooks, How-To Guides)
- Short sentences (15-20 words)
- Active voice
- Step-by-step instructions
- Frequent examples
- TL;DR sections
- Tips and callouts

**Example:**
> "In this chapter, you'll learn how to build dashboards. We'll walk through each step. By the end, you'll have a working dashboard."

### Academic Style (Best for: Research, Scholarly Works)
- Longer sentences (20-30 words)
- Formal tone
- High citation density
- Technical terminology
- Thorough development

**Example:**
> "This chapter examines distributed cognition in organizational contexts. Drawing upon Hutchins (1995), we present a framework for understanding knowledge construction."

### Narrative Style (Best for: Memoirs, Popular Science)
- Varied sentence length
- First person acceptable
- Personal stories
- Emotional engagement
- Immersive reading

**Example:**
> "I still remember walking into that startup office in 1995. We didn't know it then, but we were standing at the edge of a revolution."

### Executive Style (Best for: Business Books)
- Very short sentences (10-15 words)
- Punchy and direct
- TL;DR everywhere
- Bullet points
- Action-oriented

**Example:**
> "**TL;DR:** Remote teams are 35% more productive with async communication. Here's how. [3 bullet points follow]"

---

## 🔧 Advanced Usage

### Resume from Checkpoint

```bash
# If generation was interrupted
python run_anbg.py --profile configs/my_book.yaml --resume
```

### Custom Knowledge Base

Add your own sources:

```bash
# Create knowledge directory
mkdir -p data/my_book_project/knowledge

# Add your files (.txt, .md, .pdf, .docx)
cp my_research_notes.md data/my_book_project/knowledge/
cp expert_interview.txt data/my_book_project/knowledge/

# Run with knowledge ingestion
python run_anbg.py --profile configs/my_book.yaml
```

Stage 2 will automatically index your knowledge.

### Adjusting Rigor

**For stricter evidence requirements:**
```yaml
rigor_settings:
  evidence_rigor: strict  # Raises high_severity threshold to 98%
quality_thresholds:
  citation_coverage: 0.98  # Even stricter
```

**For more scaffolding:**
```yaml
rigor_settings:
  pedagogy_mode: guided  # More hints and support
```

**For denser content:**
```yaml
rigor_settings:
  pedagogy_mode: expert  # Less hand-holding
```

---

## 📊 Understanding Quality Reports

### QUALITY_SUMMARY.txt

```
================================================================================
QUALITY SUMMARY
================================================================================
Project: power_bi_textbook
Book: Mastering Power BI

BLOCKING GATES (Must Pass)
--------------------------------------------------------------------------------
Citation Coverage: 96.3% (threshold: 95.0%) ✅ PASS
Dependency Graph Violations: 0 (threshold: 0) ✅ PASS
Alt-Text Coverage: 100.0% (threshold: 100.0%) ✅ PASS

NON-BLOCKING METRICS
--------------------------------------------------------------------------------
Flesch Grade Level: 9.2 (target: ≤10)
Jargon Explained: 97.1% (target: ≥95.0%)

OVERALL STATUS: ✅ READY TO PUBLISH
================================================================================
```

**What to look for:**
- ✅ All blocking gates must PASS
- ⚠️  Non-blocking can be warnings
- ❌ Failed gates show repair plans

### MANIFEST.json

Contains complete metadata:
- Generation seed (for reproducibility)
- Models used per stage
- Prompts used
- Total cost
- Build time
- Citation sources
- Quality metrics

**Use for:**
- Reproducibility
- Auditing
- Cost tracking
- Quality verification

---

## 🔍 Troubleshooting

### Issue: "Citation coverage below threshold"

**Cause:** Not enough claims have citations

**Fix:**
1. Check allowlisted domains are accessible
2. Increase allowlist to include more trusted sources
3. Lower threshold temporarily (not recommended for strict books)
4. Run repair: System will suggest rerunning stage 5

### Issue: "Dependency graph violations detected"

**Cause:** Forward references (using concepts before defining them)

**Fix:**
1. Check outline stage output
2. System will auto-fix circular dependencies
3. If issues persist, manually adjust chapter order in profile

### Issue: "Alt-text coverage below 100%"

**Cause:** Some figures missing alt-text

**Fix:**
1. System should auto-generate alt-text in stage 8
2. If failed, check LLM connectivity
3. Manually add alt-text to figures if needed

### Issue: "Budget exceeded"

**Cause:** Generation costs exceeded budget

**Fix:**
1. Increase budget in profile
2. Use cheaper models (gpt-3.5-turbo)
3. Reduce chapter count
4. Resume from checkpoint to continue

### Issue: "Reading level too high"

**Cause:** Content above target grade level

**Fix:**
1. Stage 10 should auto-simplify
2. Lower reading_level_target in profile
3. Choose "practical" style pack (simpler language)

---

## 🎓 Best Practices

### For Textbooks
```yaml
book_profile:
  type: textbook
  style_pack: practical
  reading_level_target: 9
  enabled_unit_types: [concept, step, exercise, quiz, deep_dive]
rigor_settings:
  evidence_rigor: strict
  pedagogy_mode: guided
  interactivity: quizzes
```

### For Business Books
```yaml
book_profile:
  type: business
  style_pack: executive
  reading_level_target: 11
  enabled_unit_types: [concept, case_study, best_practice, tip]
rigor_settings:
  evidence_rigor: strict
  pedagogy_mode: expert
  inspiration_dial: strong
```

### For Memoirs
```yaml
book_profile:
  type: memoir
  style_pack: narrative
  reading_level_target: 8
  enabled_unit_types: [concept, case_study, tip]
rigor_settings:
  evidence_rigor: standard
  pedagogy_mode: expert
  inspiration_dial: strong
```

---

## 📈 Monitoring Generation

### Progress Tracking

During generation, check:

```bash
# View current state
cat data/my_book/state_snapshots/latest_state_*.json

# Check stage status
grep "stage_status" data/my_book/state_snapshots/latest_state_*.json

# Monitor cost
grep "total_cost_usd" data/my_book/state_snapshots/latest_state_*.json
```

### Log Files

```bash
# View generation logs
tail -f logs/prometheus_novel.log

# Search for errors
grep "ERROR" logs/prometheus_novel.log

# Check specific stage
grep "STAGE 5" logs/prometheus_novel.log
```

---

## 🔬 Testing Your Book

### Manual Quality Checks

1. **Read first chapter** - Is it engaging?
2. **Check 3 random citations** - Do links work?
3. **Test cross-references** - Do they link correctly?
4. **Review glossary** - Are definitions clear?
5. **Try 2 exercises** - Are they solvable?

### Automated Quality Checks

```bash
# Quality summary shows all metrics
cat data/my_book/exports/QUALITY_SUMMARY.txt

# Check specific metrics
grep "citation_coverage" data/my_book/exports/MANIFEST.json
grep "flesch_grade" data/my_book/exports/MANIFEST.json
```

---

## 📚 Understanding the Pipeline

### What Each Stage Does

1. **Preflight** - Validates your profile is complete
2. **Knowledge** - Indexes your custom sources (optional)
3. **Outline** - Builds dependency graph + chapter structure
4. **Units** - Generates all content (concepts, steps, exercises)
5. **Evidence** - Attaches citations from allowlist
6. **Fact-Check** - Verifies all citations (BLOCKS if fails)
7. **Exercises** - Adds practice and assessments
8. **Visuals** - Creates figures with alt-text
9. **Interlinking** - Adds cross-refs, glossary, index
10. **Clarity** - Tunes readability
11. **Compliance** - Adds disclaimers
12. **Export** - Generates EPUB/PDF/HTML
13. **Review** - Optional human checklist

### Total Time

- **Small book (5 chapters):** 30-60 minutes
- **Medium book (10 chapters):** 1-2 hours
- **Large book (15 chapters):** 2-4 hours

### Total Cost

- **Small book:** $20-40
- **Medium book:** $50-100
- **Large book:** $100-200

Actual costs depend on:
- Chapter count
- Unit complexity
- Model selection
- Evidence rigor

---

## 🎊 You're Ready!

Everything you need is in place:
- ✅ Complete system
- ✅ Example profiles
- ✅ Documentation
- ✅ Quality gates
- ✅ Error handling

**Start generating your first non-fiction book!** 🚀

---

For questions or issues, see README_ANBG.md or check the implementation documentation.


