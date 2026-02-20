# Engine Freeze Checklist — Before Book 2

**Purpose:** Consolidate all manual interventions from Book 1 into automated engine behavior. Once done, the next book should run without scene-by-scene surgery.

**Strategic principle:**
> Finish this book cleanly. Then spend **one dedicated session** doing the Engine Consolidation Pass. After that, stop touching architecture.
>
> The next book should feel 60–70% easier—not because writing is easier, but because you won't be interrupting yourself every 15 minutes.

---

## The Four Pillars of the Consolidation Pass

| # | Pillar | What it means |
|---|--------|---------------|
| 1 | **Manual → automated** | Every correction you made by hand goes into logic, prompts, or config |
| 2 | **Schema defaults** | Lock policy values; version the schema; no mid-run drift |
| 3 | **Prompt contract** | Freeze the drafting prompt; changes require version bump + doc update |
| 4 | **Document the flow** | One source of truth for what runs, in what order, and what's frozen |

---

**Target flow for Book 2:**
```
1. Create reference_bible.md
2. Update config.yaml
3. Run pipeline from high_concept → output_validation
4. Review locked manuscript
5. Grammarly pass
6. Publish
```

No manual JSON edits. No pronoun repair scripts. No Aris-reframing passes.

---

## Detailed Items (by pillar)

*Pillar 1 (Manual → automated): 1, 2, 3, 6. Pillar 2 (Schema defaults): 4, 5, 7. Pillar 3 (Prompt contract): 8. Pillar 4 (Document flow): 9.*

---

## 1. Pronoun Repair — Already Baked ✓

**Status:** `pipeline.py` already has deterministic post-voice repair.

**What exists:**
- `_repair_*` functions (pov slip, gender drift, name→pronoun)
- `pov_enforcer` stage re-applies fixes after destructive passes
- `_micro_pov_pronoun_fix()` runs after micro-passes
- POV slip detection in critic gate → triggers retry

**Verify before freeze:**
- [ ] Salvage cleanup does NOT strip so aggressively that pronoun repair fails on truncated content
- [ ] `fixable_issues` includes `pov_pronoun_confusion` and `gender_pronoun_drift` for retry path
- [ ] All post-processing passes (self_refinement, voice_human_pass, etc.) route through `_micro_pov_pronoun_fix` before final output

**Action:** Run a full pipeline on a test project; inspect one scene with known pronoun issues. Confirm repair runs and corrects without manual script.

---

## 2. Aris-Style Antagonist Entrance Strategy — Bake Into Drafting

**Status:** NOT in prompts. Discovered mid-run; applied manually.

**Rule:** For thriller/mystery antagonists (especially hidden saboteurs), early entrances should be **effect before cause**:
- Timer already running, numbers on screen, voice before body
- Delay full physical description until tension is established
- One concrete detail later in the scene, not upfront

**Implementation:**
- [ ] Add to `reference_bible.md` schema: optional `antagonist_entrance_rule` section
- [ ] In `_load_reference_bible_excerpt()` or scene-drafting prompt assembly: if `reference_bible` has antagonist entrance guidance, inject it into the prompt
- [ ] Add to `stages/pipeline.py` scene prompt (near `antagonist_checkpoint`): a conditional block when `genre in (thriller, mystery)` and `antagonist` is defined in config:
  ```
  === ANTAGONIST PRESENCE (early chapters) ===
  When [antagonist] enters a scene in Acts 1–2: lead with EFFECT before CAUSE.
  - Voice before body ("A voice from the doorway. Measured. Aris.")
  - Action before identification ("Someone is already at the console. I don't need to look.")
  - Timer/readout before person ("The timer is running when it shouldn't be. And then he speaks.")
  Delay full physical description until tension is established. One detail later, not upfront.
  ```

**Location:** `pipeline.py` ~line 9799, adjacent to `{antagonist_checkpoint}`.

---

## 3. Guilt / Emotional Breadcrumb Pattern — Bake Into Escalation Template

**Status:** Partially exists. Romance has `get_emotional_breadcrumbs()`. Thriller has antagonist "breadcrumb" in `_build_antagonist_reveal_checkpoint` for FIRST SUSPICION scene only.

**Gap:** Protagonist guilt arc (e.g., Elena's buried maintenance logs) was calibrated in-flight. No systematic escalation template for "protagonist's hidden complicity" breadcrumbs across acts.

**Implementation:**
- [ ] Add to `reference_bible.md` optional section: `protagonist_guilt_arc` or `emotional_breadcrumbs` (thriller flavor)
- [ ] In `genre_mode.py` or `bible_loader.py`: if genre is thriller AND reference_bible has guilt/breadcrumb beats, inject per-chapter guidance into scene prompts
- [ ] Document format in `docs/REFERENCE_BIBLE_SCHEMA.md` (if it exists) or in `ENGINE_FREEZE_CHECKLIST.md`

**Example format for reference_bible:**
```markdown
## PROTAGONIST GUILT ARC (thriller)
- Ch 1–2: Establish control; no overt guilt yet
- Ch 3–4: First physical reminder (smell, object, phrase) — brief, unexplained
- Ch 5–6: One line of deflection when confronted with past
- Ch 7–8: Guilt surfaces in a moment of stress; suppress quickly
- Ch 9–10: Confession or confrontation
```

**Action:** Add to `bible_loader.py` a `get_guilt_breadcrumbs(chapter_num)` (or similar) that returns empty string if not present, else the relevant beat. Inject into scene prompt when available.

---

## 4. Word Count Policy — Lock in Config

**Status:** `target_length` in config drives `target_words` via `length_map` in pipeline. Values: micro (5k), novelette (15k), compact (18k), novella (30k), standard (60k), long (90k), epic (120k).

**Risk:** Mid-run changes to `target_length` or manual overrides in `pipeline_state.json` cause recalculation, scene expansion loops, or scope creep.

**Implementation:**
- [ ] Add to `config.yaml` validation: `target_length` is READ-ONCE at pipeline init; log a warning if it differs from `pipeline_state.target_words` when resuming
- [ ] Document: "Do not change target_length mid-run. Create a new project for a different length."
- [ ] Ensure `configs/schema_validator.py` (or equivalent) flags `target_length` changes in a running project

**Action:** In pipeline init/resume logic: if `state.target_words` exists and differs from freshly computed value, log: `"Target length mismatch. Using state.target_words=%d (frozen). Config target_length=%s would yield %d."`

---

## 5. Tension Density Thresholds — Finalize

**Status:** `quality/tension_density.py` exists. `TensionDensityPolicy` in `policy/schema.py`: `min_score: 2`, `inject_on_fail: True`.

**Risk:** Manual re-evaluation of pacing during run; inconsistent "is this scene thin?" decisions.

**Implementation:**
- [ ] Confirm `min_score: 2` is the ship-ready default (0–4 scale; 2 = at least 2 of: new info, power shift, irreversible action, emotional turn)
- [ ] If `mode: "strict"` and score < min: verify `scene_turn_injection` micro-pass is wired and tested
- [ ] Document in `docs/QUALITY_SYSTEM_OVERVIEW.md` or equivalent: "Tension density gate runs after scene_drafting. Score 0–1 triggers scene_turn_injection. Do not lower min_score below 2 for thriller."

**Action:** Run `tension_density` on 5–10 scenes from the-bends; confirm scores align with editorial intuition. Adjust `min_score` once, then freeze.

---

## 6. Salvage Cleanup Hardening

**Status:** Cleanup strips preambles, truncation markers, etc. Bug observed: over-aggressive stripping can reduce content below retention threshold, trigger "salvage failed" or restore cycles.

**Implementation:**
- [ ] Review `_cleanup_salvage` (or equivalent) logic: minimum retention ratio, when to restore vs. flag for regen
- [ ] Add unit test: input with mixed good content + meta markers; output must retain ≥85% of non-meta content
- [ ] Document: "Salvage cleanup will never reduce word count by more than X% unless meta markers are present."

**Location:** `pipeline.py` around cleanup/salvage functions.

---

## 7. Schema Defaults — Freeze

**Status:** `policy/schema.py` defines `Policy` with defaults for cleanup, validation, tension_density, etc.

**Action:**
- [ ] Export a `policy_fingerprint` or version string when pipeline runs; store in `pipeline_state.json`
- [ ] If policy schema changes between runs, log: "Policy schema version changed. Engine behavior may differ."
- [ ] Tag current schema as `policy_version: "1.3"` (or next) when freeze is complete

---

## 8. Prompt Contract — Freeze

**Status:** Scene drafting prompt is ~200 lines in `pipeline.py`. Changes affect all future runs.

**Action:**
- [ ] Copy the canonical scene-drafting prompt (or its key blocks) into `docs/PROMPT_CONTRACT_v1.3.md` as reference
- [ ] Add a comment in `pipeline.py` at the prompt template: `# PROMPT CONTRACT v1.3 — see docs/PROMPT_CONTRACT_v1.3.md`
- [ ] Rule: Any change to the prompt contract requires a new version bump and update to the doc

---

## 9. Document the Stable Flow

**Action:**
- [ ] Create or update `docs/STABLE_RUN_FLOW.md`:
  1. high_concept → beat_sheet → master_outline
  2. scene_drafting (with roster_gate, reference_bible, antagonist_checkpoint, Aris-style block when applicable)
  3. structure_gate, continuity_audit, continuity_fix
  4. self_refinement, voice_human_pass (with pov_enforcer)
  5. output_validation, recompile
  6. No manual stages. No JSON edits. No fix_manuscript scripts.

- [ ] List which stages are optional (e.g., scene_expansion for short drafts) vs. required
- [ ] Document the single point of config: `config.yaml` + `reference_bible.md`. No tweaks in pipeline_state except what the pipeline writes.

---

## Freeze Completion Criteria

Before starting Book 2, all items above must be:
- [ ] Implemented or explicitly deferred (with a ticket)
- [ ] Tested on at least one full pipeline run (can be the-bends re-seed or a throwaway project)
- [ ] Documented in this checklist or linked docs

**Ship statement:**
> This is version 1.3 of the engine. It ships. No architecture changes until Book 2 is drafted.

**Reminder:** The goal isn't perfection—it's *predictability*. A known engine that occasionally needs a light edit is better than an ever-shifting engine that needs constant surgery.

---

## Appendix: the-bends Manual Interventions (Now Engine Targets)

| Intervention | Engine Target |
|--------------|---------------|
| Pronoun drift repair | `_micro_pov_pronoun_fix`, `pov_enforcer` — verify coverage |
| Salvage cleanup bug | Harden retention logic, add test |
| Tension density tuning | Freeze `min_score: 2`, document |
| Aris entrance reframing | Add to scene prompt when thriller + antagonist |
| Guilt breadcrumb timing | Add `get_guilt_breadcrumbs()` to bible_loader, inject when present |
| Word count policy | Lock target_length at init, no mid-run change |
| Phrase caps | Already in config + validation |
| Tense consistency | Already in reference_bible inject_tense_rules |
