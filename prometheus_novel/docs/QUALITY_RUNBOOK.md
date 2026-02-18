# Quality Runbook: What to Do When Checks Fail

> **Purpose:** Triage rules for quality check failures. Use this when a run completes and artifacts show issues, or when you're iterating on a manuscript.

---

## Human Readability Gate (Before Paid Polish)

**Before running paid polish** (voice_human_pass, dialogue_polish, prose_polish), read **3 sample scenes**:
- **Early** (first ~10% of scenes)
- **Midpoint** (~50%)
- **Climax** (last ~10%)

If structurally stiff (flat dialogue, weak bones, repetitive beats), fix upstream first. Polish amplifies structure—weak bones stay weak.

**How to get scene indices:**
```bash
writerai pre-polish-sample --config path/to/config.yaml
```
Prints scene IDs for early, midpoint, climax. Load `pipeline_state.json` and read those scenes before proceeding.

---

## Required Artifacts (Where to Look)

Before triaging, inspect:

- `output/quality_contract.json` — per-scene warnings
- `output/craft_scorecard.json` — aggregate metrics
- `output/facts_ledger.json` — continuity by scene

---

## Triage Rules

| When This Fails | Action |
|-----------------|--------|
| **TENSION_COLLAPSE** | Revise outline escalation (adjacent scenes shouldn't drop 8→3) OR add tension-preservation prompt constraint for that scene pair |
| **CH1_HOOK_WEAK** | Rewrite first 250 words manually, OR enforce stronger hook elements in Ch1 Sc1 drafting prompt (dialogue/action/question) |
| **Facts drift** (ledger shows name/location/time inconsistency) | Strengthen entity anchor block in scene drafting; add canonical facts to prompt from previous scenes |
| **Hot phrase spike** (repetition) | Increase suppressor strength in `phrase_suppressor` config; widen `used_details_global_hot.top_n` or tracking window |
| **Budget guard warning** | Reduce `tokens_per_scene` in `enhancements.budget_guard`; shorten run (fewer scenes); or raise `budget_usd` |
| **Structure gate failures** | Check `structure_gate_pass_total` / `pass_min`; add repair iterations or adjust scene-level purpose in outline |
| **Craft scorecard regression** (entropy down, ending skew) | Compare with previous run; adjust quality polish policy or scene turn repair rules |

---

## Closed-Loop Workflow

1. Run pipeline → inspect artifacts
2. Map warnings to triage rule above
3. Fix upstream (outline, config, seed) or tighten prompt/validator
4. Regenerate (probabilistic — may need 1–2 retries)
5. Re-inspect → diff scorecard if regression snapshot enabled

---

## Human Readability Gate (Pre-Polish Checkpoint)

**Before paid polish**, read 3 sample scenes: early, midpoint, climax. If structurally stiff, fix upstream first—polish amplifies structure; weak bones stay weak.

**Process:**
1. Run `writerai pre-polish-sample --config path/to/config.yaml` to print scene indices for early, midpoint, climax (and optionally flat scenes from voice heatmap)
2. Read those scenes in the compiled output or `pipeline_state.json`
3. If stiff/weak: adjust outline, scene purposes, or tension before running voice_human_pass / prose_polish

---

## When the Problem Is Upstream

If issues persist across regenerations with same seed:

- **Flat tension curve** → Fix outline `tension_level` values; add escalation beats
- **Repetitive structure** → Vary scene functions (Reveal/Bond/Conflict/Decision) in outline
- **Wrong tone** → Adjust `strategic_guidance` (market_positioning, aesthetic_guide)
- **POV/voice drift** → Strengthen POV block and character voice in config

Quality checks detect and reduce. They don't fix structural or strategic root causes.
