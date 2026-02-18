# Pipeline V2 Roadmap — Structural Upgrades

*Not cosmetic tweaks. System upgrades.*

Based on production runs (The Last Truth, Burning Vows) and editorial observations. The structure is stable. Rollback safety works. Budget guard works. This roadmap optimizes **rewrite robustness** and **targeted polish** so prose feels human under pressure.

---

## Priority Order

| # | Upgrade | Status | Effort | Notes |
|---|---------|--------|--------|-------|
| 1 | Rewrite token budgets | ✅ Done | — | stage_max_tokens in config |
| 2 | Output length guard | ✅ Done | — | rewrite_min_length_ratio 0.85 |
| 3 | Stakes injector | ✅ Done | — | voice_human_pass; tension ≥8 |
| 4 | Dialogue compression | ✅ Done | — | dialogue_polish prompt when DIALOGUE_TIDY |
| 5 | Context window pre-flight | ✅ Done | — | _generate_prose clamps max_tokens |
| 6 | Repetition scanner before polish | ✅ Done | Medium | Targeted polish prompts |
| 7 | Scene ending action enforcement | ✅ Done | Low | Strengthen existing meter |
| 8 | Bond scene drift classifier | Done | Medium | Draft vs intended type |
| 9 | Cost kill switch | Done | Low | Abort on runaway polish |
| 10 | Voice heatmap diagnostic | Done | Low | Flag flat scenes |
| 11 | Human readability gate | Done | — | Read 3 scenes before paid polish |
| 12 | Draft vs rewrite model split | Done | Low | Config separation |

---

## 1️⃣ Rewrite Token Budget — ✅ DONE

**Problem:** Rewrite stages receive ~3k input, capped at 2.5k output → truncation → rollback.

**Fix:** `model_tuning.stage_max_tokens` in config.

| Stage | Suggested | Current (the-last-truth) |
|-------|-----------|--------------------------|
| self_refinement | 5000 | 4500 → bump to 5000 |
| voice_human_pass | 5000 | 4500 → bump to 5000 |
| dialogue_polish | 4500 | 4500 ✓ |
| prose_polish | 4500 | 4500 ✓ |
| chapter_hooks | 3000 | 4500 (generous; 3000 fine for hooks-only) |

---

## 2️⃣ Output Length Guard — ✅ DONE

**Problem:** Model can "successfully" finish but shrink scenes dramatically. Silent collapse.

**Fix:** In `_generate_prose()`, after validation: if `scene_meta.original_word_count` and rewritten < 0.85 × original → add `scene_collapse` issue, trigger retry with feedback.

**Config:** `defense.thresholds.rewrite_min_length_ratio` (default 0.85). Overridable per project.

---

## 3️⃣ Stakes Injector — ✅ DONE

**Problem:** High tension (≥8) with no explicit stakes reads hollow.

**Fix:** In `voice_human_pass`, before building prompt: if `tension_level >= 8` and `check_stakes_articulation()` returns STAKELESS_TENSION → inject stakes block into prompt.

**Location:** `_stage_voice_human_pass`; uses `quality.quiet_killers.check_stakes_articulation`.

---

## 4️⃣ Dialogue Compression Pass — ✅ DONE

**Problem:** 3+ consecutive clean exchanges with no interruptions/beats/dodges → stiff.

**Fix:** In `dialogue_polish`, when `check_dialogue_tidy()` flags DIALOGUE_TIDY → inject mandatory block: add (1) interrupted line, (2) deflecting answer, (3) physical beat between exchanges.

**Location:** `_stage_dialogue_polish`; uses `quality.quiet_killers.check_dialogue_tidy`.

---

## 5️⃣ Context Window Pre-Flight Check — ✅ DONE

**Problem:** Polish can implode when `prompt_tokens + expected_output > context_limit`.

**Fix:** In `_generate_prose()`, before `client.generate`: estimate prompt tokens, get `get_context_limit(model_name)` (parses -8k/-16k/-32k from name, provider defaults). If `prompt_tokens + max_tokens > limit` → clamp `max_tokens` to `limit - prompt_tokens - 100`.

**Config:** `model_defaults.model_context_limit` (optional override).

**Location:** `_generate_prose`; `prometheus_lib.llm.clients.get_context_limit`.

---

## 6️⃣ Repetition Scanner Before Polish — ✅ DONE

**Problem:** DEFLECTION, RHYTHM_FLATLINE, STAKELESS_TENSION — polish is generic without signals.

**Fix:** Before polish:

- Sentence opening repetition check
- Paragraph-length clustering
- Abstract noun density (fear, truth, feeling, memory…)

Feed flags into polish prompt: *"Reduce reflective density and vary sentence rhythm. Avoid abstract emotional labeling."*

**Location:** `quality/repetition_scanner.py`; injected into voice_human_pass and prose_polish.

---

## 7️⃣ Scene Ending Action Enforcement — ✅ DONE

**Problem:** Scenes ending on mood/metaphor/atmosphere — commercial fiction prefers dialogue/decision/action.

**Fix:** When `_classify_ending()` returns SUMMARY or ATMOSPHERE for the last paragraph → inject prompt block requiring ending on dialogue, decision, or physical action.

**Location:** `_stage_prose_polish`; uses `quality.quiet_killers._classify_ending`.

---

## 8️⃣ Bond Scene Drift Classifier — PLANNED

**Problem:** Outline has bond ratio; draft-level drift can erode it.

**Fix:** After scene_drafting, classify scene: PLOT | FRICTION | BOND | CRISIS. If actual ≠ intended → flag for rewrite or re-draft.

**Location:** New post-draft classifier; feedback into scene_drafting or continuity_fix.

---

## 9️⃣ Cost Kill Switch — DONE

**Problem:** Runaway polish loops burn money.

**Fix:** If any stage fails 3× consecutively OR cost exceeds X% of budget → abort pipeline.

**Location:** Circuit breaker for failures; `_check_cost_kill_switch()` for budget. Config: `enhancements.cost_kill_switch.enabled`, `abort_at_pct` (default 1.0).

---

## 🔟 Voice Heatmap Diagnostic — DONE

**Problem:** Polish everything equally; some scenes are statistically flatter.

**Fix:** Per-scene: adverb density, weak verb frequency, abstract noun density, sentence length variance. Flag scenes flatter than average. Polish those first (or with higher weight).

**Location:** `quality/voice_heatmap.py`; runs in quality_meters stage. Config: `enhancements.voice_heatmap.enabled`.

---

## 1️⃣1️⃣ Human Readability Gate — DONE

**Problem:** Polish amplifies structure. Weak bones stay weak.

**Fix:** Before paid polish, read 3 scenes: early, midpoint, climax. If structurally stiff → fix upstream first.

**Process:** QUALITY_RUNBOOK updated. `writerai pre-polish-sample --config path` prints scene indices. `writerai generate --pre-polish-sample` prints and exits before running.

---

## 1️⃣2️⃣ Draft vs Rewrite Model Split — DONE

**Problem:** Draft config wasn't tuned for rewrite behavior. Different cognitive tasks.

**Fix:** Config:

```yaml
model_defaults:
  draft_model: gpt-oss-20b      # or api_model for paid
  rewrite_model: claude-sonnet-4 # or critic_model
```

**Location:** `get_client_for_stage()` routes draft stages (scene_drafting, master_outline, etc.) to draft bucket, rewrite stages (voice_human_pass, prose_polish, etc.) to rewrite bucket. `stage_model_map` supports `draft_model` and `rewrite_model` keys.

---

## What NOT to Change

- Do not rewrite early stages
- Do not overcomplicate motif system
- Do not add more gates
- Do not add more meters

**Improve precision, not complexity.**

---

## Implementation Batches

### Batch A (Critical) — ✅ DONE
1. ✅ Bump stage_max_tokens to 5000 for self_refinement, voice_human_pass
2. ✅ Output length guard (rewrite_min_length_ratio 0.85)
3. ✅ Stakes injector for high-tension scenes

### Batch B (High impact) — ✅ DONE
4. ✅ Dialogue compression pass
5. ✅ Context window pre-flight check

### Batch C (Targeted polish) — ✅ DONE
6. ✅ Repetition scanner → polish prompt injection
7. ✅ Scene ending action enforcement (stricter)

### Batch D (Observability + safety) — DONE
8. Cost kill switch
9. Voice heatmap diagnostic
10. Draft/rewrite model split

### Batch E (Structural) — DONE
11. Bond scene drift classifier

### Manual — DONE
12. Human readability gate (runbook + pre-polish-sample CLI)

---

*Last updated: from production learnings. Pipeline is commercially dangerous once rewrite robustness and targeted polish are in place.*
