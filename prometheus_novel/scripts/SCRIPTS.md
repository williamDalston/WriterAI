# Prometheus Novel Scripts

Scripts and utilities for the novel pipeline. **For LLM agents:** use this index to find the right tool for a task.

---

## Pipeline-wired (run during `generate`)

These run automatically as part of the generation pipeline. No standalone script needed.

| Component | Stage | Location |
|-----------|-------|----------|
| Editorial cleanup | `quality_polish` (final step) | `quality/editorial_cleanup.py` |
| Editor Studio passes | `targeted_refinement` | `editor_studio/orchestrator.py` |
| Developmental audit | `developmental_audit` | `quality/developmental_audit.py` |
| Fresh eyes audit | `developmental_audit` | `quality/developmental_audit.py` → `audit_fresh_eyes` |
| Quality audit | `quality_audit` | `stages/pipeline.py` |
| Docx/KDP export | `output_validation` | `export/docx_exporter.py` |

---

## CLI Commands (`writerai <cmd>`)

Run via main CLI for discoverability:

| Command | Purpose | Example |
|---------|---------|---------|
| `writerai generate -c <config>` | Full pipeline | `writerai generate -c data/projects/my-novel/config.yaml` |
| `writerai editor-studio -p <project>` | Surgical refinement passes | `writerai editor-studio -p data/projects/burning-vows-30k` |
| `writerai editorial-cleanup -p <project>` | Deterministic cleanup (preambles, POV, grounding, etc.) | `writerai editorial-cleanup -p data/projects/burning-vows-30k` |
| `writerai audit -p <project>` | Run developmental + fresh-eyes audit | `writerai audit -p data/projects/burning-vows-30k` |
| `writerai compile -c <config>` | Compile to html/epub/md/docx | `writerai compile -c data/projects/my-novel/config.yaml --format docx` |

---

## Standalone Scripts (module invocation)

Use when you need direct control or the CLI doesn't expose an option.

### Quality & Cleanup

| Script | Purpose | When to use |
|--------|---------|-------------|
| `python -m prometheus_novel.scripts.run_editorial_cleanup <project>` | Strip preambles, grounding, fix POV, filter words, etc. | Post-pipeline polish; also runs in pipeline |
| `python -m prometheus_novel.scripts.run_fresh_eyes <project>` | LLM cold-read audit (CONFUSION, PACING_DRAG, UNCLEAR_MOTIVATION) | Run audit without full pipeline |
| `python -m prometheus_novel.scripts.run_audit <project>` | Developmental audit (deterministic) + prints fresh-eyes summary | Quick audit report |
| `python -m prometheus_novel.scripts.run_editor_studio <project>` | Editor Studio passes (continuity, dialogue, stakes, etc.) | Same as `writerai editor-studio` |

### Standalone Docx Audit & Formatting

| Script | Purpose | When to use |
|--------|---------|-------------|
| `python -m prometheus_novel.scripts.run_docx_audit [path/to/docx]` | Audit quality of a standalone .docx | Grammarly-edited or exported manuscript; no pipeline_state needed |
| `python -m prometheus_novel.scripts.fix_docx_kdp_formatting [path/to/docx]` | Apply KDP formatting (6x9, Garamond, margins) | Fix formatting on edited docx before KDP upload; saves as \<name\>_KDP.docx |
| `python -m prometheus_novel.scripts.apply_audit_fixes_docx [path/to/docx]` | Apply audit fixes (ellipsis, Marco ring, temple tic, duplicates) | Post-Grammarly cleanup; saves as \<name\>_audit_fixed.docx |
| `python -m prometheus_novel.scripts.run_overuse_analysis [path]` | Detect words/phrases over threshold (default 10) | Dynamic overuse detection; outputs overuse_report.json + overuse_detected.yaml |
| `python -m prometheus_novel.scripts.apply_overuse_replacements [docx]` | Apply phrase replacements from banks/overuse config | After adding replacements to overuse_detected.yaml; rotates alternatives |

**Pipeline improvements (Option A + B):** See `docs/PIPELINE_IMPROVEMENTS_SPEC.md`. New stages: `roster_gate`, `pov_enforcer`. Prompt blocks: roster reminder, scene transition grounding, voice under pressure, strengthened causality.
| `python -m prometheus_novel.scripts.run_editorial_craft [project]` | Editorial craft checks (motif, gesture, simile, tense, cadence) | See EDITORIAL_CRAFT_GAPS.md; outputs editorial_craft_report.json |

### Reporting & Comparison

| Script | Purpose | When to use |
|--------|---------|-------------|
| `python -m prometheus_novel.scripts.print_run_results [project]` | Dashboard: run status, scorecard, contract, facts | Inspect pipeline output |
| `python -m prometheus_novel.scripts.print_scorecard_diff [path]` | Scorecard delta vs previous run | Compare quality before/after |
| `python -m prometheus_novel.scripts.recheck_quality [project]` | Re-run quality_contract, compare warning counts | Post-fix validation |

### Ad-hoc & Legacy

| Script | Purpose | Status |
|--------|---------|--------|
| `python -m prometheus_novel.scripts.apply_audit_fixes <project>` | Apply fixes for audit findings (ch01_s02, ch02_s02, etc.) | One-off; Burning Vows audit |
| `python -m prometheus_novel.scripts.apply_manual_fixes [project]` | quiet_killers transforms (bridge, grounding, gesture diversify) | **Legacy** — pipeline runs these via quality_polish |
| `python -m prometheus_novel.scripts.strip_preambles_and_filters` | P0/P2/P3 preamble + filter strips | **Deprecated** — use `run_editorial_cleanup` |

---

## Quick Reference for LLM Agents

**"Run editorial cleanup on project"**  
→ `writerai editorial-cleanup -p data/projects/<project>` or  
→ `python -m prometheus_novel.scripts.run_editorial_cleanup data/projects/<project>`

**"Audit the manuscript"**  
→ `writerai audit -p data/projects/<project>` or  
→ `python -m prometheus_novel.scripts.run_fresh_eyes data/projects/<project>`

**"Fix audit findings"**  
→ `python -m prometheus_novel.scripts.apply_audit_fixes data/projects/<project>` (audit-specific)

**"Export to Word"**  
→ Run `writerai editorial-cleanup` (recompiles .md + .docx) or `writerai compile -c <config> --format docx`

**"Show pipeline results"**  
→ `python -m prometheus_novel.scripts.print_run_results data/projects/<project>`
