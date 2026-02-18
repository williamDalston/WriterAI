# Developmental Audit

High-level audits and fixes that run **after Editor Studio**, addressing gaps Editor Studio doesn't cover:

| Dimension | Audit | Fix |
|-----------|-------|-----|
| **Structure & pacing** | Chapter length variance, scene count, act balance | Report-only (manual review) |
| **Character arcs** | Protagonist presence, emotional beat distribution | Report-only |
| **Theme & subtext** | Motif presence, central question in final third | **THEME_ABSENT_LATE** → Add one theme-resonant line |
| **Line-level polish** | Passive voice, adverb runs | **PASSIVE_HOTSPOT** → Reduce passive in flagged scenes |
| **Genre conventions** | Romance/thriller beat coverage | Report-only (missing beats flagged) |
| **Fresh eyes** | LLM cold-read: confusion, pacing drag, unclear motivation | **CONFUSION** → Clarify; **UNCLEAR_MOTIVATION** → Ground motivation |

## Pipeline

New stage `developmental_audit` runs after `targeted_refinement`, before `quality_audit`.

1. **Audit** — Deterministic checks produce findings
2. **Fix** — LLM passes for fixable findings (PASSIVE_HOTSPOT, THEME_ABSENT_LATE, CONFUSION, UNCLEAR_MOTIVATION)
3. **Report** — `output/developmental_audit.json` with findings and fix stats

## Config

```yaml
enhancements:
  developmental_audit:
    enabled: true
    fixes_enabled: true      # Apply passive/theme fixes (default: true)
    dry_run: false           # If true, audit only, no scene edits
    structure_pacing: true
    character_arcs: true
    theme_subtext: true
    line_level: true
    genre_conventions: true
    fresh_eyes: true         # LLM cold-read (default: on)
```

## Genre Beat Templates

Supported: `romance`, `thriller`, `dark romance`. Others fall back to romance template.

Beats are checked against outline scene purposes in position windows (e.g. dark moment in 65–85% of manuscript). Missing beats produce `MISSING_BEAT` findings for manual review.

## Output

- `output/developmental_audit.json` — Findings, audit stats, fix counts
- `run_report.json` — Includes `developmental_audit` key with full report

---

## Editor Studio: Additional Passes (Pipeline)

The following are **Editor Studio** passes (targeted_refinement stage), not developmental_audit:

| Pass | Detection | Fix |
|------|-----------|-----|
| **truncation_complete** | TRUNCATION (scene ends with —, ..., or lacks closure) | Complete the final sentence(s) |
| **opening_vary** | opening_move_violations (chapter repeats prior opening type) | Change opening to different hook |
| **cross_scene_transition** | CROSS_CONTINUITY_LOC, CROSS_CONTINUITY_TIME in batch_warnings | Add 1–2 bridge sentences at scene start |

Requires full `quality_contract_report` (contracts + opening_move_violations + batch_warnings). Pipeline passes this automatically.
