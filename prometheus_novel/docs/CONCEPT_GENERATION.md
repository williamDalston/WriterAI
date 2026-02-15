# Concept Generation: Architecture and Improvement Guide

> **Purpose:** Document how high-concept generation works, ensure it is as good as possible, and provide clear improvement paths.

---

## 1. Role of the High Concept

The **high concept** is the first planning stage in the pipeline. It produces a single, compelling paragraph that:

1. Captures the unique hook or twist
2. States the central conflict
3. Conveys the emotional core
4. Suggests what makes the story fresh

This output feeds **every subsequent planning stage** (world_building, beat_sheet, emotional_architecture, character_profiles, master_outline, trope_integration, motif_embedding) and several drafting/polish stages. Quality here cascades through the entire pipeline.

---

## 2. Current Architecture

### 2.1 Pipeline Location

| Aspect | Value |
|--------|-------|
| Stage name | `high_concept` |
| Phase | Planning (first stage) |
| Dependencies | None (uses only config) |
| Output consumer | world_building, beat_sheet, emotional_architecture, character_profiles, master_outline, trope_integration, motif_embedding, chapter_hooks |

### 2.2 Implementation Location

**File:** `prometheus_novel/stages/pipeline.py`  
**Method:** `_stage_high_concept()` (lines ~3089–3117)

### 2.3 Input Flow

```
config.yaml
    ↓
_build_story_context()     ← Core story elements
_build_strategic_guidance() ← Strategic / commercial guidance
    ↓
Inline prompt (hardcoded)
    ↓
client.generate(prompt)
    ↓
state.high_concept (raw string)
```

### 2.4 Story Context (`_build_story_context()`)

Pulls from `config` and builds a text block with:

| Section | Config keys |
|---------|-------------|
| Core | title, genre, tone, target_length |
| Idea | synopsis (as CORE IDEA) |
| Characters | protagonist, antagonist, other_characters |
| World | setting, world_rules, key_locations |
| Plot | premise, central_conflict, key_plot_points, subplots |
| Themes | themes, central_question, motifs |
| Style | writing_style, influences, avoid |

Empty sections are omitted. This gives the model a full view of the story seed.

### 2.5 Strategic Guidance (`_build_strategic_guidance()`)

Pulls from `config.strategic_guidance`:

| Key | Purpose |
|-----|---------|
| market_positioning | Commercial / comps framing |
| beat_sheet | Pacing / structure notes |
| aesthetic_guide | Visual / tonal direction |
| tropes | Tropes to lean into |
| dialogue_bank | Sample lines / voice |
| cultural_notes | Authenticity / research |
| pacing_notes | Rhythm and tension |
| commercial_notes | Market / audience notes |

If all values are empty, returns empty string (section not added).

### 2.6 Current Prompt (inline, hardcoded)

```python
prompt = f"""You are an expert novelist. Generate a compelling high-concept summary for a novel.

{story_context}
{strategic}

Create a powerful one-paragraph high concept that captures:
1. The unique hook or twist
2. The central conflict
3. The emotional core
4. What makes this story fresh

High Concept:"""
```

### 2.7 Generation Call

```python
client = self.get_client_for_stage("high_concept")  # STAGE_MODELS["high_concept"] = "gpt"
if client:
    temp = self.get_temperature_for_stage("high_concept")  # 0.4
    response = await client.generate(prompt, temperature=temp, max_tokens=400)
    self.state.high_concept = (response.content or "").strip()
```

**Resolved:** temperature (0.4) and max_tokens (400) now passed; output is stripped.  
**Remaining gaps:** No system prompt, no stop sequences, no formal validation.

---

## 3. Unused Prompt Templates

The pipeline does **not** use `load_prompt_template()` or `render_prompt()` for high_concept. Two template files exist but are not wired in:

### 3.1 `prompts/default/high_concept_prompt.txt`

```
You are an expert novelist. Your task is to generate a high-concept summary for a novel.
The novel's synopsis is: {{ novel_synopsis }}

Generate a compelling, one-paragraph high concept, focusing on the core conflict and unique hook.
```

- Uses only `novel_synopsis` (minimal context).
- Less context than the inline prompt.

### 3.2 `prompts/experimental_v2/high_concept_prompt.txt`

```
As a visionary storyteller, craft a high-concept pitch for a novel.
The core idea is: {{ novel_synopsis }}

Focus on a unique twist, a compelling central question, and a strong sense of genre. Aim for a pitch that grabs attention immediately.
```

- Same limitation: only `novel_synopsis`.
- Different framing (“visionary storyteller”, “pitch”).

Neither template exposes story context or strategic guidance, so they are less capable than the current inline prompt.

---

## 4. Model Routing and Temperature

| Setting | Value |
|---------|-------|
| STAGE_MODELS["high_concept"] | `"gpt"` |
| STAGE_TEMPERATURES["high_concept"] | `0.4` |

`get_client_for_stage("high_concept")` resolves to the GPT client. Temperature is defined but **not passed** to `client.generate()`.

---

## 5. Quality Improvement Checklist

### 5.1 Quick Wins (Low Effort)

| # | Change | Benefit | Status |
|---|--------|---------|--------|
| 1 | Pass `temperature=0.4` (or `get_temperature_for_stage("high_concept")`) to `client.generate()` | More consistent outputs | ✅ Done |
| 2 | Pass `max_tokens=400` to avoid overly long paragraphs | Bounded output length | ✅ Done |
| 3 | Add minimal postprocess: trim leading/trailing whitespace | Cleaner storage and downstream use | ✅ Done (.strip()) |

### 5.2 Medium Effort

| # | Change | Benefit |
|---|--------|---------|
| 4 | Use `render_prompt()` with a new template that includes `story_context` and `strategic_guidance` placeholders | Versionable prompts, A/B testing, consistent structure |
| 5 | Add an optional planning-stage system prompt (e.g. “Output only the high concept, no preamble”) | Reduce meta-text and commentary |
| 6 | Add genre-specific guidance in the prompt (e.g. romance: emphasize tension and stakes; thriller: emphasize stakes and twist) | Better genre fit |

### 5.3 Higher Effort

| # | Change | Benefit |
|---|--------|---------|
| 7 | Light validation: reject outputs with “Here is”, “Certainly”, bullet points, or multiple paragraphs | Catch bad outputs early |
| 8 | Optional critic pass: score alignment with hook, conflict, emotional core, freshness | Quality feedback / retry loop |
| 9 | Structured output: JSON with `hook`, `conflict`, `emotional_core`, `freshness`, then compose paragraph | More controllable, testable structure |

---

## 6. Recommended Template Structure

If switching to `render_prompt()`, the template should expose the same information as the inline prompt:

```jinja2
You are an expert novelist. Generate a compelling high-concept summary for a novel.

{{ story_context }}
{{ strategic_guidance }}

Create a powerful one-paragraph high concept that captures:
1. The unique hook or twist
2. The central conflict
3. The emotional core
4. What makes this story fresh

Output ONLY the high concept paragraph. No preamble, headings, or commentary.

High Concept:
```

Variables:
- `story_context`: output of `_build_story_context()`
- `strategic_guidance`: output of `_build_strategic_guidance()`

---

## 7. Minimum Viable Inputs

The high concept stage runs first and depends only on config. To avoid poor outputs:

- **Required:** `synopsis` or `premise` (used in CORE IDEA / premise)
- **Recommended:** `genre`, `protagonist`, `central_conflict`
- **Helpful:** `title`, `setting`, `themes`, `central_question`, `strategic_guidance`

Projects created via the seed command start with at least `synopsis` (from IDEA). Manual configs should ensure at least one of synopsis/premise is present.

---

## 8. Downstream Usage

The high concept is injected into later stages as plain text:

- `world_building`: `High Concept: {self.state.high_concept}`
- `beat_sheet`: same
- `emotional_architecture`: `STORY CONCEPT: {self.state.high_concept}`
- `character_profiles`: same
- `master_outline`: `HIGH CONCEPT: {self.state.high_concept}`
- `trope_integration`: same
- `motif_embedding`: same
- `chapter_hooks`: same

Single-paragraph, prose-only output is ideal for these consumers. Avoid:
- Bullet points or lists
- Multiple paragraphs
- Meta-commentary (“Here is the high concept…”)

---

## 9. Relation to Defense Architecture

The high concept stage is a **planning** stage, not prose. It does **not** use:

- FORMAT_CONTRACT (prose-only)
- Stop sequences / nonce sentinel
- Critic gate / retry

That is acceptable for planning, but we can still:

- Add stop sequences for obvious meta-text (e.g. `\nCertainly!`, `\nHere is the`)
- Apply light validation before storing
- Optionally add a planning-specific meta-text filter for consistency with DEFENSE_ARCHITECTURE patterns

---

## 10. Summary of Changes to Prioritize

| Priority | Action | Status |
|----------|--------|--------|
| **P0** | Pass `temperature` (0.4) and `max_tokens` (400) to `client.generate()`, strip output | ✅ Implemented |
| **P1** | Trim and normalize whitespace on output before storing | ✅ Done (strip) |
| **P2** | Add a proper template (with story_context + strategic_guidance) and switch to `render_prompt()` | Pending |
| **P3** | Add optional light validation (single paragraph, no preamble) | Pending |
| **P4** | Consider genre-specific prompt variants or structured output | Pending |

---

## Appendix: Code References

| Item | Location |
|------|----------|
| `_stage_high_concept()` | `pipeline.py` ~3089–3117 |
| `_build_story_context()` | `pipeline.py` ~2989–3048 |
| `_build_strategic_guidance()` | `pipeline.py` ~3051–3083 |
| Default template | `prompts/default/high_concept_prompt.txt` |
| Experimental template | `prompts/experimental_v2/high_concept_prompt.txt` |
| `render_prompt()` | `prometheus_lib/utils/prompt_loader.py` |
| `get_client_for_stage()` | `pipeline.py` ~2520 |
