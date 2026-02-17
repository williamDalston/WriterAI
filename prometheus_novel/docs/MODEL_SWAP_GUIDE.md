# Model Swap Guide: Qwen → Hybrid Paid

Switching from local Qwen to paid models (OpenAI, Anthropic, Gemini) is **config + calibration**, not a rebuild. All reliability work—atomic checkpoints, retry logic, meters, micro-passes—stays unchanged.

## What Stays Unchanged

| Area | Status |
|------|--------|
| Atomic checkpointing, graceful client guards | ✅ Unchanged |
| Config resolver, provenance, runbooks, debug pack | ✅ Unchanged |
| Validation & QC: meters, scene_id integrity | ✅ Unchanged |
| Micro-passes: dialogue drought, AI-tell scrub, turn repair, dedup tail | ✅ Unchanged (you may tighten triggers to reduce paid calls) |
| Raw-wrapper failure logic, retry-on-parse, backfill | ✅ Unchanged |

## The Minimal-Diff Switch

### 1. Change `model_defaults` (which physical model per bucket)

```yaml
model_defaults:
  api_model: gpt-4o-mini          # or claude-3-haiku, gemini-1.5-flash
  critic_model: claude-3-haiku    # nuanced prose, continuity
  fallback_model: gemini-1.5-flash # long context, audits
```

The CLI maps:
- `gpt` bucket → `api_model`
- `claude` bucket → `critic_model`
- `gemini` bucket → `fallback_model`

### 2. Add `model_tuning` (optional: temps + max_tokens per stage)

Use `configs/hybrid_paid_preset.yaml` as a base, or merge into your project:

```yaml
model_tuning:
  stage_temperatures:
    master_outline: 0.2    # Lower for JSON/planning
    scene_drafting: 0.7    # Creative
    final_deai: 0.2        # Low for surgical scrub
  stage_max_tokens:
    scene_drafting: 4500   # Paid models need runway
    scene_expansion: 2500  # Can shrink if drafting hits target
```

### 3. Optional: `model_overrides` (route stages to different buckets)

```yaml
model_overrides:
  scene_drafting: claude   # Use critic bucket for prose
  continuity_fix: claude
```

## Token Budgets & Length Targets

| Stage | Qwen Default | Paid Suggestion |
|-------|--------------|-----------------|
| scene_drafting | words_per_scene × 2.5, min 2500 | 4000–5000 (give runway) |
| scene_expansion | 3000 | 2000–2500 (often shrink; drafting gets closer) |
| master_outline | 4096 / 3072 retry | 4096 (paid models obey JSON better) |

## Temperature Calibration

| Stage Type | Qwen Tuning | Paid Starting Point |
|------------|-------------|---------------------|
| JSON / outline | 0.3–0.5 | 0.1–0.3 |
| Drafting | 0.85 | 0.6–0.9 |
| Micro-repairs / scrub | 0.2–0.4 | 0.2–0.4 |
| Judging / scoring | 0.15–0.2 | 0.0–0.2 |

Then let your meters tell you what to nudge.

## JSON Compliance

Keep all guards:
- Raw wrapper is failure
- Retry on parse failure
- Chapter completeness backfill

What you can adjust:
- Fewer retries (e.g. `MAX_OUTLINE_RETRIES: 1`) once stable, to save cost
- Provider-native structured output where available—but keep the parser as the last line of defense

## Micro-Pass Triggers (Cost Control)

Paid models trip them less. You can raise thresholds to avoid unnecessary rewrites:

| Guard | Qwen Default | Paid Option |
|-------|--------------|-------------|
| Dialogue drought | &lt; 3 lines | &lt; 2 (or only Act 3) |
| AI tells | &lt;= 1 before scrub | &lt;= 2 |
| Scene turn | ≥ 2 signals | ≥ 1 if endings are strong |

Goal: reduce paid calls without reducing quality.

## Context Strategy (Batch Size)

Keep your batching. For paid models, avoid shoving the full bible + 12-chapter summary into every call. Feed:

- Scene contract
- Current chapter summary
- 3–5 critical continuity facts
- Short “do-not-repeat” list (scene names, beats) if needed

## Provider Quirks Checklist

- [ ] Stop sequences actually respected (no mid-scene truncation)
- [ ] Streaming handlers handle empty chunks
- [ ] Backoff/jitter for 429s/timeouts
- [ ] Key masking covers the provider’s error formats

## Verification Runs

After swapping config:

1. `pytest`
2. `pytest -m smoke`
3. Micro-prose test
4. Outline stress test
5. Act tripod (Ch2, Ch6, Ch11)

Compare before/after using the same meters:

- Dialogue density (especially Act 3)
- AI-tell counts
- Scene-turn pass rate
- Repetition + similarity
- `outline_json_report` totals (should drop)

## Quick Start

1. **Env overlay:** `PROMETHEUS_ENV=hybrid_paid` loads `configs/hybrid_paid_config.yaml`.
2. **Or merge:** Copy `model_defaults` and `model_tuning` from that file into your project `config.yaml`.
3. Set `model_defaults` to your chosen paid models (OpenAI, Anthropic, Gemini).
4. Run the verification suite (`pytest`, smoke, outline stress, act tripod).
5. Adjust `model_tuning` based on meter results.

No code changes required.
