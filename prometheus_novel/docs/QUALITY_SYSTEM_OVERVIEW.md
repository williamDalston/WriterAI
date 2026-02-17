# Quality System Overview

> **Purpose:** State of the quality infrastructure, what regeneration changes, and how to evaluate runs. Operator-facing.

---

## What We've Addressed (System-Level)

| Weakness | Fix |
|----------|-----|
| Tension collapse (scene drops 8→3) | `TENSION_COLLAPSE` check in quality contract |
| Weak Ch1 opening | `CH1_HOOK_WEAK` check + drafting hook rule |
| Repetition (phrase déjà vu, similar beats) | Global hot list + phrase suppressor + scene-function classification |
| Continuity drift (names, places, time) | Facts ledger + continuity tripwires |
| Validator false positives | Ordering fixes + deterministic causality + dialogue logic fixes |
| Silent cost overruns | Budget guard pre-drafting |
| No pause points | Human review gates |
| Romance specificity | Romance genre block + `intimacy_beat` structure category |
| No baseline metrics | Craft scorecard outputs |
| No run-to-run comparison | Regression snapshot: `runs/<run_id>/`, `scorecard_diff.json` |

---

## What Regeneration Changes

Regeneration now benefits from **stronger prevention and detection**: more reliable validators, continuity logging, repetition control, genre structure expectations.

**Output remains probabilistic.** Same seed/outline can still yield different prose and a different set of issues. The system catches and reduces problems; it does not guarantee elimination.

---

## What Still Depends on Seed/Outline

If the root cause is structural (flat escalation, repetitive beats), premise/seed tone, or strategic guidance (heat, tropes, voice), regeneration won't reliably fix it. Those need adjustments upstream.

---

## How to Evaluate a Run (Required Artifacts)

Inspect these files in `output/`:

| Artifact | What It Tells You |
|----------|-------------------|
| `quality_contract.json` | Per-scene warnings (TENSION_COLLAPSE, CH1_HOOK_WEAK, CAUSALITY, DEFLECTION, etc.), opening move history |
| `craft_scorecard.json` | Phrase entropy, dialogue density, emotional modes, verb specificity, ending distribution, health_score |
| `facts_ledger.json` | Per-scene continuity (location, characters_present, time_anchor) |
| `scorecard_diff.json` | Current vs previous run: metric deltas, regression flag |
| `runs/<run_id>/craft_scorecard.json` | Per-run snapshot for history |

See **[QUALITY_RUNBOOK.md](QUALITY_RUNBOOK.md)** for triage rules when something fails.

**View diff cleanly:** `python -m prometheus_novel.scripts.print_scorecard_diff` or with `jq . output/scorecard_diff.json`

---

## Hard Gates vs Soft Warnings (Current State)

| Type | Behavior | Examples |
|------|----------|----------|
| **Soft (warn)** | Log and continue | TENSION_COLLAPSE, CH1_HOOK_WEAK, budget guard warning |
| **Hard (fail)** | Stop run / force retry | Structure gate below threshold (configurable), circuit breaker |

When **genre-weighted scorecard + per-metric warn/fail** lands, this table will be explicit in config. For now, most quality checks are soft; structure gate can enforce pass criteria.

---

## Future: Genre-Weighted Metrics

Planned evolution:

- Metrics are **genre-weighted** (romance upweights dialogue density; thriller upweights tension curve)
- Each metric has **warn-only** vs **fail-stop** config
- `run_profile` (e.g. `romance_short`, `thriller_fast`) maps to meter weights + structure categories + gates
