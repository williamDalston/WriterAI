# Model Strategy: Best Quality per Dollar

> **Purpose:** Final model choices for the three buckets—best quality per dollar, minimal friction, works with the current defense stack. No code changes required; only `model_defaults` update.

---

## 1. Final Model Choices

### 1) gpt bucket (planning JSON, bulk drafting, mechanical passes)

**Model:** **GPT-5 mini** (via OpenAI)  
- [OpenAI Pricing](https://openai.com/api/pricing/)

**Why:** Extremely strong instruction-following and structure; cheap enough that you can "waste" tokens on retries without guilt.

### 2) claude bucket (voice, emotion, dialogue, polish)

**Model:** **Claude Sonnet 4.5** (via Anthropic)  
- [Claude API Pricing](https://docs.anthropic.com/en/docs/about-claude/pricing)

**Why:** This is the "make it feel like a human wrote it" engine. For KU shifter romance, it's the biggest perceived-quality lever: dialogue rhythm, subtext, intimacy beats, and the cleanest anti-AI texture.

### 3) gemini bucket (long-context audits, scoring, continuity, validation)

**Model:** **Gemini 2.5 Flash** (via Google)  
- [Vertex AI Pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing)

**Why:** Strong at wide-context scanning and structured analysis for cheap. Perfect for continuity_audit, quality_audit, structure_gate style work.

---

## 2. Drop-in Config

Put this in your env defaults (`the_empathy_clause.yaml` / `{env}_config.yaml`) or override per project:

```yaml
model_defaults:
  api_model: gpt-5-mini
  critic_model: claude-sonnet-4.5
  fallback_model: gemini-2.5-flash
```

That's it. No code changes required if your routing is already `stage → bucket → model_defaults`.

---

## 3. Important Notes (so nothing bites you later)

### A) Do not remove your Qwen-specific "micro-pass" guards

Keep them. They become a **quality ratchet** even with paid models:

- dialogue drought guard
- AI-tell scrub
- scene-turn repair
- dedup-tail regen

Paid models reduce how often these fire, but when they do fire, they save chapters from going soft.

### B) POV plumbing still matters

Even with premium models, your per-scene POV routing is important, because postprocessing is doing real work (first-person enforcement + cleanup). That fix stays relevant.

---

## 4. Budget Reality Check

OpenAI lists GPT-5 mini at **$0.25 / 1M input tokens** and **$2.00 / 1M output tokens**.  
That makes the high-volume parts (outline retries, scene drafting, mechanical passes) very affordable.

Spend will be dominated by **Claude Sonnet 4.5** output on polish-heavy stages.  
For **30k novellas**, it's typically nowhere near $50 unless you loop polish stages excessively or run lots of full rerolls.

---

## 5. What to Change When Switching to Paid

Only this:

1. Update `model_defaults` as in section 2.
2. Optionally increase `max_tokens` on the most verbose prose stages (if you currently capped them tightly for Qwen).

Everything else (retry logic, scene IDs, POV, meters, defense layers) stays the same.

---

## 6. Optional Insurance Switch

Keep a second preset for cheap drafting experiments, then flip to the premium preset only when you like the outline. This fits Kindle Unlimited economics: fewer full rewrites, more publishable passes.

Example cheap-draft preset (for outline + first draft only):

```yaml
# Cheap preset: use for outline + drafting experiments
model_defaults:
  api_model: gpt-5-mini
  critic_model: gpt-5-mini      # Same as gpt for cheap drafting
  fallback_model: gemini-2.5-flash
```

Switch to the main preset (with claude-sonnet-4.5 on critic) when you're ready for polish.

---

## 7. Architecture Alignment

The pipeline follows **DEFENSE_ARCHITECTURE** (24 stages, 7 phases). Current `STAGE_MODELS` routing is unchanged:

| Bucket | Stages |
|--------|--------|
| **gpt** | high_concept, beat_sheet, master_outline, scene_drafting, final_deai, output_validation |
| **claude** | emotional_architecture, character_profiles, motif_embedding, trope_integration, scene_expansion, continuity_fix, continuity_fix_2, self_refinement, voice_human_pass, dialogue_polish, prose_polish, chapter_hooks |
| **gemini** | world_building, structure_gate, continuity_audit, continuity_recheck, continuity_audit_2, quality_audit |

---

## 8. Local Model Recommendations (Ollama)

When running fully local with Ollama:

**Structure gate:** Swap `qwen2.5:14b` → `qwen3:14b` for the structure_gate stage. Same VRAM, better reasoning for JSON scoring/repair. Drop-in via Ollama:

```yaml
model_defaults:
  api_model: qwen2.5:14b
  critic_model: qwen2.5:14b
  fallback_model: qwen2.5:14b
  structure_gate_model: qwen3:14b

stage_model_map:
  structure_gate: structure_gate_model
```

**Optional experiment (scenes needing stronger reasoning):** Try GPT-OSS 20B at Q4 with a capped context window. In your Ollama modelfile, set `num_ctx 8192` to fit larger scenes while staying within VRAM.

---

## Appendix: Code References

| Item | Location |
|------|----------|
| STAGES | pipeline.py ~2917 |
| STAGE_MODELS | pipeline.py ~2965 |
| get_client_for_stage | pipeline.py ~3310 |
| model_defaults mapping | interfaces/cli/main.py ~249; api_model→gpt, critic_model→claude, fallback_model→gemini |
| DEFENSE_ARCHITECTURE | docs/DEFENSE_ARCHITECTURE.md |
