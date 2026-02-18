# Polish Stage Consolidation Plan

**Goal:** Best final results via layered passes—not brute-force mutation.

**Principle:** Each pass operates on a different layer. No two full-scene rewrites with the same objective.

---

## Current State: Overlap Map

| Stage | Scope | Unique Value | Redundant With |
|-------|-------|--------------|----------------|
| **self_refinement** | Full scene | avoid_list, simple 7-rule prompt | voice_human_pass (100% overlap) |
| **voice_human_pass** | Full scene | Cross-scene repetition blacklist, POV negative anchors, stakes injection, repetition scanner, AI tell kill list, 6 JOBs | — (this is the keeper) |
| **dialogue_polish** | Full scene | DIALOGUE_TIDY compression, dialogue bank, character profiles, bad-tag blacklist | voice JOB 3 (dialogue), targeted_refinement deflection/dialogue_friction |
| **prose_polish** | Full scene | Rhetorical devices, scene-ending enforcement, PRESERVATION_CONSTRAINTS, "subtle only" | voice JOB 6 (surface cleanup), repetition scanner (already in voice) |
| **chapter_hooks** | First/last 2-3 paras | Genre-aware hook types | ✅ Scoped—keep |
| **targeted_refinement** | Full scene (per pass) | quality_contract targeting, deflection/stakes/rhythm/gesture per flagged scene | voice (stakes, deflection), dialogue_polish |
| **final_deai** | Deterministic patterns | No LLM, surgical replacement | ✅ Keep |
| **quality_polish** | Deterministic | Phrase suppression, no LLM | ✅ Keep |

---

## Unique Contributions to Preserve

### From self_refinement (merge into voice_human_pass)
- `avoid_list` from config — voice_human_pass does NOT currently use this
- Simpler "revision priorities" ordering — voice's 6 JOBs already cover this; add avoid_list to voice

### From dialogue_polish (merge or scope)
- DIALOGUE_TIDY block (interrupt/deflection/beat when 4+ lines, no friction) — **already in voice JOB 3**, but dialogue_polish adds:
  - dialogue_bank, cultural_notes from strategic_guidance
  - Character profiles in prompt
  - Bad dialogue tag blacklist ("said with a smile", "my voice carried", etc.)
  - CONFLICT_DIALOGUE_CONSTRAINTS for tension ≥6
- **Recommendation:** Merge dialogue-specific rules (bad tags, dialogue bank) into voice_human_pass. The dialogue work is covered by JOB 3; add the tag blacklist and bank as optional blocks.

### From prose_polish (merge or drop)
- Rhetorical devices (tricolon, chiasmus, etc.) — nice-to-have, not critical
- Scene ending enforcement (SUMMARY/ATMOSPHERE → DIALOGUE/DECISION/ACTION) — **add to voice_human_pass** (it has "no emotional summaries" but not explicit ending-type fix)
- Repetition scanner — already in voice
- PRESERVATION_CONSTRAINTS — voice doesn't include these; **add to voice** to harden output
- **Recommendation:** Merge ending enforcement + PRESERVATION_CONSTRAINTS into voice. Drop prose_polish. Rhetorical devices are marginal.

### From targeted_refinement
- Quality-contract-based targeting (only fix scenes with specific flags)
- Passes: deflection, stakes, rhythm, gesture_diversify, tension_collapse, causality, etc.
- **Reality:** Still outputs full scene per pass. "Surgical" in intent, not in implementation.
- **Recommendation:** Keep targeted_refinement but run it ONLY when quality_meters flag issues. It's opt-in and targeted—different layer (issue-specific patches). Or: move its logic earlier—if we have ONE voice pass, targeted_refinement becomes "second pass for flagged scenes only." That's acceptable: it's conditional, not universal.

---

## Target Architecture

### Phase 1 — Structure (unchanged)
```
structure_gate
continuity_audit
continuity_fix
continuity_recheck
```

### Phase 2 — The Single Heavy Rewrite
```
voice_human_pass  ← MASTER STAGE (absorbs self_refinement, dialogue rules, prose ending enforcement, PRESERVATION_CONSTRAINTS)
```

**voice_human_pass enhancements (merge from dropped stages):**
1. Add `avoid_list` from config to prompt
2. Add PRESERVATION_CONSTRAINTS block (prevent re-introduction of AI tells)
3. Add scene ending enforcement: if last paragraph is SUMMARY/ATMOSPHERE, require DIALOGUE/DECISION/ACTION
4. Add optional dialogue_bank + cultural_notes when present in strategic_guidance
5. Add bad dialogue tag blacklist (from dialogue_polish)
6. Keep: repetition blacklist, stakes injection, repetition scanner, negative anchors, 6 JOBs

### Phase 3 — Light Continuity Check
```
continuity_audit_2
continuity_fix_2
pov_enforcer
```

### Phase 4 — Scoped Polish (no full-scene rewrites)
```
chapter_hooks     ← First/last 2-3 paragraphs only
```

### Phase 5 — Deterministic Cleanup
```
final_deai
quality_polish
quality_meters
```

### Phase 6 — Conditional Targeted Fixes (opt-in)
```
targeted_refinement   ← Only runs when quality_contract flags issues; per-scene passes
developmental_audit
quality_audit
output_validation
```

---

## Stages to DROP

| Stage | Action |
|-------|--------|
| **self_refinement** | DROP. Merge avoid_list into voice_human_pass. |
| **dialogue_polish** | DROP. Merge tag blacklist, dialogue_bank, DIALOGUE_TIDY into voice_human_pass. |
| **prose_polish** | DROP. Merge ending enforcement, PRESERVATION_CONSTRAINTS into voice_human_pass. |

---

## New STAGES Order (after consolidation)

```python
# After continuity_recheck:
"voice_human_pass",      # Single heavy rewrite (master stage)
"continuity_audit_2",
"continuity_fix_2",
"pov_enforcer",
"chapter_hooks",        # Scoped: first/last paras only
"final_deai",
"quality_polish",
"quality_meters",
"targeted_refinement",  # Conditional, issue-targeted
"developmental_audit",
"quality_audit",
"output_validation"
```

**Removed:** self_refinement, dialogue_polish, prose_polish

---

## Implementation Checklist

1. **Enhance voice_human_pass**
   - [ ] Add `avoid_list` block
   - [ ] Add PRESERVATION_CONSTRAINTS block
   - [ ] Add scene ending enforcement (classify_ending, inject block when SUMMARY/ATMOSPHERE)
   - [ ] Add optional dialogue_bank + cultural_notes
   - [ ] Add bad dialogue tag blacklist (8 rules from dialogue_polish)
   - [ ] Ensure DIALOGUE_TIDY block is present (already have check_dialogue_tidy; verify it's in voice)

2. **Remove stages from STAGES list**
   - [ ] Remove self_refinement
   - [ ] Remove dialogue_polish
   - [ ] Remove prose_polish

3. **Update stage registry**
   - [ ] Remove handlers for dropped stages (or make them no-op that log "deprecated")
   - [ ] Update any --stage, --start-stage, --end-stage docs

4. **Config backward compatibility**
   - [ ] If config has stage_model_map for removed stages, log warning and ignore
   - [ ] model_tuning.stage_max_tokens for removed stages: harmless to leave

5. **Testing**
   - [ ] Run pipeline on a small project (e.g. 3-chapter) with new order
   - [ ] Compare output quality vs previous 4-pass stack
   - [ ] Verify cost reduction (~40-60% in polish phase)

---

## Expected Outcomes

- **Cost:** ~40-60% reduction in polish-phase tokens
- **Quality:** More coherent voice, less stylistic drift, fewer truncation rollbacks
- **Stability:** Fewer full-scene mutations = fewer failure modes
- **Speed:** Fewer LLM calls per scene

---

## Rollback Plan

Keep the removed stage functions in codebase but unused. Add config flag:
```yaml
enhancements:
  legacy_polish_stack: false  # true = run self_refinement, dialogue_polish, prose_polish (deprecated)
```
If consolidation causes regressions, flip to true for one run while debugging.

---

## Refinements (Pressure-Tested)

### 1. voice_human_pass: Hierarchical Priority Order

The merged prompt must not be a blob. If everything is weighted equally, focus dilutes. **Order matters.**

Internal execution order:
```
Priority 1: Structural integrity (no content loss, preserve beats)
Priority 2: Remove AI artifacts + repetition
Priority 3: Strengthen stakes + tension
Priority 4: Dialogue friction & compression
Priority 5: Verb & sentence tightening
Priority 6: Ending enforcement
Priority 7: avoid_list cleanup
```

This prevents: stakes from overwriting character nuance; avoid_list from flattening tone; ending enforcement from forcing awkward last lines.

### 2. strict_preservation_mode

Add boolean to voice_human_pass:
```yaml
enhancements:
  voice_human_pass:
    strict_preservation_mode: true  # default true
```

When true:
- No scene reordering
- No character deletion
- No added subplots
- No tone inversion
- **Only refinement**

Ensures the heavy rewrite never mutates structure.

### 3. Pronoun/POV Collapse — Prevention, Not Correction

`pov_enforcer` runs *after* voice_human_pass. Damage happens *during* the rewrite. Prevention beats correction.

**Add to voice_human_pass prompt:**
```
=== CHARACTER PRONOUN ANCHORS (hard constraint) ===
Maya = she/her
Javier = he/him
Dr. Kline = he/him
[Auto-generated from characters list; inject before every scene]
```

Prevents pronoun errors at source instead of patching later.

### 4. Ending Classification — Deterministic, Not LLM

Do NOT let the LLM decide if the ending is SUMMARY/ATMOSPHERE. Use existing `_classify_ending()` first.

```
if ending_type in [SUMMARY, ATMOSPHERE]:
    inject instruction: rewrite final paragraph to DIALOGUE/DECISION/ACTION
```

Makes the rewrite targeted, not speculative.

### 5. targeted_refinement — Never Auto After Success

**Rule:** targeted_refinement must NEVER run automatically after a successful voice pass.

Only run if:
- quality_meters flag an issue (DEFLECTION, DIALOGUE_TIDY, STAKELESS_TENSION, FINAL_LINE_ATMOSPHERE)
- OR user manually requests it

```python
if quality_score < threshold or manual_request:
    run targeted_refinement
else:
    skip
```

Otherwise it becomes a stealth second full rewrite layer.

### 6. Quality Meters as Safety Net

With fewer passes, we lose "accidental" fixes from pass 3 that fixed what pass 1 missed. **Quality meters replace that with intentional measurement.**

Critical flags that gate targeted_refinement:
- DEFLECTION
- DIALOGUE_TIDY
- STAKELESS_TENSION
- FINAL_LINE_ATMOSPHERE

If those meters pass, no extra polish needed.

### 7. Prompt Length Warning

The merged voice_human_pass adds: avoid_list, PRESERVATION_CONSTRAINTS, ending enforcement, dialogue_bank, cultural_notes, tag blacklist, pronoun anchors to an already complex 6-JOB prompt.

**If combined prompt exceeds ~3K tokens of instruction, the model will ignore the bottom half.**

- Structure prompt hierarchically; put non-negotiable rules at top
- Consider splitting into "must-read" (first 1.5K) vs "reference" (condensed)
- Test for instruction adherence after merge

### 8. Repetition Loops — Generation-Time, Not Polish

"The city was alive" x60 is a **generation** issue, not polish. No downstream editing fixes a 2,000-word repetition loop cleanly.

**Needed:** Detection at generation time:
- Token-level repetition scoring (e.g. n-gram density threshold)
- Post-generation gate: reject and re-generate scenes with repetition density above threshold
- Runs **before** any polish stages (after scene_drafting / scene_expansion)

Location: `_generate_prose` or post-draft validation. Existing `_detect_phrase_loops` in pipeline helps; may need to tighten thresholds or add rejection + retry.

### 9. Pacing / Action-to-Description Ratio

The novel's biggest readability problem: action-to-description ratio. No stage explicitly addresses this.

**Add:** Lightweight classifier in quality_meters:
- Score description density per scene (e.g. % of paragraph that is setting/atmosphere vs action/dialogue)
- Flag scenes exceeding threshold
- Feed into targeted_refinement with new pass: "trim description" (reduce purple prose, keep action beats)

### 10. story_bible Persistence Layer

Per-character state doc updated per chapter:
- name, gender, status, last known location, speech patterns
- Injected into voice_human_pass and continuity_audit
- Prevents majority of continuity and voice-flattening issues at source

**Phase:** Design after consolidation. Feeds both drafting and polish stages.

---

## Implementation Additions

6. **voice_human_pass refinements**
   - [ ] Add character pronoun anchors (Maya=she/her, etc.) from characters list
   - [ ] Add strict_preservation_mode block when enabled
   - [ ] Structure prompt with priority order (P1–P7) explicitly labeled
   - [ ] Keep ending classification deterministic; inject block only when classifier returns SUMMARY/ATMOSPHERE

7. **targeted_refinement gate**
   - [ ] Add `quality_score < threshold` check; skip when meters pass
   - [ ] Add config: `enhancements.targeted_refinement.auto_run: false` (default: only on quality failure or manual)

8. **Repetition gate (pre-polish)**
   - [ ] Add or tighten repetition-density gate after scene_drafting
   - [ ] Reject + retry when phrase loop detected above threshold

9. **Pacing classifier**
   - [ ] Add description_density metric to quality_meters
   - [ ] Flag scenes for targeted_refinement "trim description" pass
