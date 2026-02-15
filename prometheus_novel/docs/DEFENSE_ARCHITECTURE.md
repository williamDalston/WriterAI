# Prometheus Novel: Defense Architecture

> **Purpose:** Track all defensive layers, problem types, and setup so we can infer improvements and diagnose issues.

---

## 1. Design Goals (the "no surprises" contract)

| Goal | Implementation |
|------|----------------|
| Strip meta-artifacts without eating real prose | Multi-phase cleanup + high-confidence markers only + anchor-based protection |
| Prevent "version stitching" (two versions in one output) | Stitch marker split + duplicate detection + suffix/prefix overlap + semantic dedup |
| Catch cross-contamination as warnings by default | Pre-export validation, config-driven |
| Make patterns extendable without code edits | `configs/cleanup_patterns.yaml` + `disabled_builtins` suppression |
| Quantify model vs system | Artifact metrics + critic gate (raw output) + scoring function |
| Protect hooks and openings during surgical passes | Paragraph-based head/tail protection in final_deai |
| Trace context provenance | Context hashing + origin stamps in debug logs |
| Transaction safety with rollback | 6-check integrity validation with snapshot restore (includes forbidden-marker explosion) |
| Prevent cross-run prose collision | Per-run nonce sentinel (`<END_PROSE_{hex}>`) |
| Detect recycled language | Freshness score (bigram overlap against prior 3 scenes) |
| Detect prompt injection in context | 5 injection patterns in schema validation |
| Auto-fix validation errors | G→Pipeline feedback loop (postprocess + LLM rewrite) |
| Track quality trends across runs | Cross-run JSONL metrics persistence + delta analysis |
| Hot-configurable DE-AI patterns | `configs/surgical_replacements.yaml` (loaded at runtime) |

**Non-goals:** No genre policing unless config opts in. No heavy-handed rewriting -- cleanup truncates; validation flags.

---

## 2. Pipeline Flow (21 stages, 7 phases)

```
PLANNING -> DRAFTING -> REFINEMENT -> POLISH -> VALIDATION -> OUTPUT -> FEEDBACK
```

| Phase | Stages |
|-------|--------|
| **Planning** (8) | high_concept, world_building, beat_sheet, emotional_architecture, character_profiles, motif_embedding, master_outline, trope_integration |
| **Drafting** (3) | scene_drafting, scene_expansion, self_refinement |
| **Continuity** (2) | continuity_audit, continuity_fix |
| **Refinement** (3) | voice_human_pass, continuity_audit_2, continuity_fix_2 |
| **Polish** (3) | dialogue_polish, prose_polish, chapter_hooks |
| **DE-AI** (1) | final_deai |
| **Validation** (1) | quality_audit, output_validation |

**Prose stages** (get FORMAT_CONTRACT + stop sequences):
scene_drafting, scene_expansion, self_refinement, continuity_fix, voice_human_pass, continuity_fix_2, dialogue_polish, prose_polish, chapter_hooks, final_deai

**Critic gate stages** (retry on failure): All prose stages except `final_deai` (uses direct API with paragraph-based hook protection, not `_generate_prose`).

---

## 3. Defensive Layers (in order of application)

### Layer A: Format Contract (Generation Prompt)

**Location:** `FORMAT_CONTRACT` constant + per-run `self._format_contract` in `pipeline.py`
**When:** Injected as system prompt for all 10 prose stages via `_generate_prose()`
**Purpose:** Instruct model to output prose only; never preamble, commentary, alternatives, or truncation markers.

```
ABSOLUTE RULES:
- Output ONLY narrative prose
- NEVER: "Certainly", "Here is", "Sure", headings, bullet points, commentary
- NEVER: "The rest remains unchanged", alternatives, "[Scene continues...]"
- End your output with <END_PROSE_{nonce}> on its own line when finished.
```

**Nonce sentinel:** Each pipeline run generates a unique 8-hex-char nonce via `secrets.token_hex(4)` (e.g. `a3f1b2c9`). The static `<END_PROSE>` is replaced with `<END_PROSE_{nonce}>` in the format contract, making the stop token unpredictable (won't appear in training data) and unique per run (prevents cross-run prose collisions). The postprocessor strips both static and nonce variants via regex `<END_PROSE(?:_[a-f0-9]+)?>`.

**Override:** Stages can pass a custom `system_prompt`; otherwise the nonce-aware format contract is default.

---

### Layer B: Sentinel Stop Token + Backup Sequences

**Location:** `PROSE_SENTINEL` (static) + `self._prose_sentinel` / `self._stop_sequences` (per-run) in `pipeline.py`; passed to clients via `stop=` / `stop_sequences=`
**When:** Every LLM call for prose stages
**Purpose:** Primary: nonce sentinel gives clean, unique stop per run. Backup: catch assistant-mode preambles if model ignores sentinel.

| Token | Purpose |
|-------|---------|
| `\n<END_PROSE_{nonce}>` | **Primary nonce sentinel** -- unique per run, unpredictable |
| `\nCertainly! Here` | Blocks assistant-mode preamble restart |
| `\nHere is the` | Blocks "Here is the revised..." |
| `\nAs requested,` | Blocks assistant acknowledgment |
| `\nThe rest remains unchanged` | Blocks truncation marker |
| `\nChanges made:` | Blocks analysis footer |
| `\nScanning for AI` | Blocks checklist footer |
| `\n**Changes made` | Blocks markdown-style analysis |
| `\n**Scanning for` | Blocks markdown-style checklist |
| `\n[The rest` | Blocks bracketed notes |
| `\n[Scene continues` | Blocks stage-direction artifacts |

**Design:** Backup sequences are "assistant-y" (start with capital letter + space) to avoid false positives in prose. The old generic tokens (`\nCertainly`, `\nNotes:`) were replaced with more specific phrases.

**Client mapping:** OpenAI + Ollama use `stop=`; Anthropic uses `stop_sequences=`.

**Sentinel stripping:** `_postprocess_scene()` strips `<END_PROSE>` and `<END_PROSE_{hex}>` (nonce variant) via regex before any other processing.

---

### Layer C: Context Hygiene

**Location:** `_build_scene_context()` in `pipeline.py`
**When:** Assembles context for scene-generation prompts
**Purpose:** Single entry point so we never inject wrong data. Now includes schema validation, alignment checking, and provenance tracking.

**INCLUDED:**
- Writing style, tone, avoid list
- Story state (facts from outline -- prevents "first meeting loop", hallucinated locations)
- Previous scene endings (transition continuity, paragraph-based)
- Periodic alignment check (every 5 scenes vs outline)

**NEVER INCLUDED:**
- Other project data
- Old candidates / debug text
- Explanations or meta-commentary

**Sub-components:**

| Component | Purpose |
|-----------|---------|
| `_validate_context_schema()` | Runtime check for red flags: credentials, Python code, import statements, template placeholders, debug markers, **prompt injection attempts** (5 patterns: "ignore previous instructions", role injection, system override, context override, instruction reset). Logs warnings; does not block. |
| `_check_alignment()` | Every 5 scenes, compares scene content keywords against outline entries. Warns if <15% keyword overlap (scenes drifting from beat sheet). |
| **Context hashing + origin stamps** | SHA256 hash (12-char truncated) of assembled context logged at DEBUG level with origin section names and char count. Enables tracing which context produced which scene output. |

---

### Layer D: Critic Gate (Pre-Postprocess Validation)

**Location:** `_validate_scene_output()` in `pipeline.py`
**When:** Runs on **raw** LLM output **before** postprocessing (measures model behavior)
**Purpose:** Detect fixable issues; trigger retry when appropriate. Now includes fuzzy preamble detection.

**Checks:**

| Check | Pattern / Logic |
|-------|-----------------|
| Preamble (exact) | First 200 chars: "Sure", "Certainly", "Here is", "Below is", "I've revised" |
| **Preamble (fuzzy)** | **N-gram Jaccard similarity** (trigram overlap > 35%) against 14 exemplar preamble strings. **Gated by assistant-anchor check**: only runs if the first line contains an anchor word (revised, rewritten, enhanced, below, here is, as requested, changes made, version, i've, let me, etc.). This prevents false positives on prose openings that happen to share trigrams with exemplars. |
| Truncation marker | REST_UNCHANGED_RE |
| Alternate version | "Option A/B", "Version 1/2", "=== EXPANDED SCENE ===" |
| Analysis commentary | "Changes made:", "Notes:", "**Scanning", "**Quality" |
| Too short | < 50 words |
| POV drift | 3+ third-person refs (e.g. "Lena said") in first-person story |

**Fixable issues** (trigger retry): preamble, truncation_marker, alternate_version, analysis_commentary
**Not fixable by retry:** too_short, pov_drift (still recorded)

**Fuzzy detection details:** `_ngram_similarity(text_a, text_b, n=3)` computes Jaccard similarity of character trigram sets. The 14 exemplars cover "Certainly here is", "Sure here's the revised", "As you requested", "I've rewritten the", "Below is the improved", etc. A first-120-chars sample > 35% overlap with any exemplar triggers the preamble flag.

---

### Layer E: Retry Policy (Scoring + Issue-Specific Feedback)

**Location:** `_generate_prose()` in `pipeline.py`
**When:** Critic gate fails on fixable issues
**Behavior:** Retry once. Both attempts scored; better score wins.

**Scoring function (`_score_output`):**

| Category | Penalty/Bonus |
|----------|---------------|
| Hard artifacts (preamble, truncation, alternate, analysis) | **-100 each** |
| Too short | -30 |
| POV drift | -20 |
| Word count >= 200 | **+min(wc/50, 20)** (up to +20 bonus) |

The scoring function replaces the old "fewer issues wins" logic with a numeric comparison, allowing nuanced trade-offs (e.g., a slightly short but artifact-free output beats a full-length output with preamble).

**Issue-specific retry feedback:**
Instead of a generic retry prefix, the system now builds targeted feedback from `ISSUE_SPECIFIC_FEEDBACK`:

| Issue | Feedback |
|-------|----------|
| `preamble` | "YOUR ERROR: You started your output with a preamble/greeting..." |
| `truncation_marker` | "YOUR ERROR: You truncated the scene with a note..." |
| `alternate_version` | "YOUR ERROR: You output multiple versions..." |
| `analysis_commentary` | "YOUR ERROR: You appended analysis/commentary..." |

This tells the model *exactly what went wrong* instead of repeating a generic warning.

**Diminishing-returns early exit:** In `quality_audit`, if word-count delta < 5% AND tells-delta < 0.5 between iterations, `needs_iteration` is set to `False` to avoid wasteful re-runs.

---

### Layer F: Postprocessing (Cleanup + Quality)

**Location:** `_postprocess()` -> `_postprocess_scene()` in `pipeline.py`
**When:** After every prose generation (and retry, if any)
**Order:** Sentinel strip -> Clean -> Duplicate detect -> Semantic dedup -> POV enforce -> POV repair -> Strip emotional summaries -> Limit tics -> Language fix

#### F1: `_clean_scene_content()` -- 5 phases

| Phase | Purpose |
|-------|---------|
| **1** | Strip preamble at **start** ("Certainly! Here is...", "Sure, here's...") |
| **1.5** | **Truncate** at "rest remains unchanged" (and YAML markers). Keep text before; drop alternate. |
| **1.6** | **Truncate** at mid-text LLM preamble ("Certainly! Here is the revised opening...") if prefix >= 400 chars or >= 8 lines |
| **2** | Truncate at tail markers (---, ***, "Changes made:", etc.) |
| **2.5** | **Salvage guardrail (active)**: If remaining text < 150 words or < 2 paragraphs, log warning. If < 50 words **and the original pre-cleanup input had 3x more words (≥50)**, automatically **restores the pre-cleanup input** (over-stripping is worse than leaving artifacts). Otherwise logs as "salvage failed". |
| **3** | Inline removal (CURRENT SCENE:, Physical beats:, XML tags, etc.) |
| **4** | Whitespace cleanup |

**YAML extension:** `configs/cleanup_patterns.yaml` adds `inline_truncate_markers`, `inline_preamble_markers`, `regex_patterns`.

**`disabled_builtins`:** YAML list of substring matches. Any built-in pattern containing a listed substring is skipped for that project. Prevents false positives (e.g., if your prose legitimately uses "Physical beats").

#### F2: `_detect_duplicate_content()`

Three detection layers:

1. **Stitch marker split:** Split on stitch markers (rest unchanged, `---`, `***`, "Version N", "Alternative:", "Revised:", "Take N"); keep segment 0.
2. **Suffix/prefix overlap:** Check if the last N words (N = 60, 40, or 25) appear earlier in the text. If so, truncate at the duplicate. Catches verbatim ending repetition.
3. **N-gram similarity dedup:** Paragraph-level Jaccard similarity (> 60% overlap = duplicate paragraph removed).

#### F2b: `_detect_semantic_duplicates()`

**When:** After duplicate detection, before POV enforcement.
**Purpose:** Catch paraphrased restarts (same content rewritten slightly differently).

- Splits text at paragraph midpoint.
- Computes embedding cosine similarity (sentence-transformers `all-MiniLM-L6-v2` if available) or falls back to bigram Jaccard overlap.
- Threshold: > 50% similarity = keep only first half.
- **Minimum text length:** 500 chars (skip short scenes).

#### F3: `_enforce_first_person_pov()`

Gender-aware POV enforcement with three protection mechanisms:

1. **Dialogue quote masking:** `_mask_quoted_dialogue()` replaces all text inside quotation marks ("..." and curly quotes) with `__DIALOGUE_N__` placeholders before any pronoun replacement. Preserves sentence-boundary punctuation after placeholders so subsequent patterns still match. Restores dialogue after all replacements.

2. **Clause-level possessive guard:** `_safe_poss_replace()` checks 20 chars before each possessive match. Skips replacement if preceded by relative pronouns (`who`, `that`, `which`, etc.) or `of` -- prevents "the woman who had been his friend" from becoming "my friend".

3. **Core replacements:**
   - `[Name] verb` -> `I verb` (always safe)
   - `[Name]'s body_part` -> `my body_part` (always safe)
   - `He/She verb` -> `I verb` (gender-matched, sentence boundaries only)
   - `his/her body_part` -> `my body_part` (gender-matched, with clause guard)

#### F3b: `_repair_pov_context_errors()`

**Purpose:** Fix contextual POV corruption where third-person subject + first-person possessive clash. The #1 defect in local LLM output.

| Pattern | Example | Fix |
|---------|---------|-----|
| P1: `she said, my voice` | "She whispered, my voice barely audible" | -> "her voice" |
| P2: `[Name] said, my voice` | "Ana said, my voice soft" | -> "her voice" |
| P3: `She [verb] my [body]` | "She rolled my eyes" | -> "her eyes" |
| P4: `I smiled, gazing at me` | "I smiled warmly, gazing at me" | -> "She smiled" |
| P5: `I [verb] at/to me` | "I turned to face me" | -> "She turned" |
| P6: `I followed my back` | "I followed my back through..." | -> "her back" |
| P7: Markdown artifacts | "I felt **terrified**" | -> strip `**` and `*` |

#### F4: `_strip_emotional_summaries()`, `_limit_tic_frequency()`, `_flag_language_inconsistencies()`

- **Emotional summaries:** ~30+ patterns matching paragraph-ending sentences that explain what a scene means emotionally (e.g. "This wasn't just about...", "Something about this moment...", "A fragile connection...", "Whatever came next...", "For the first time in..."). Now handles:
  - **Single-sentence paragraphs:** If the entire paragraph is a summary pattern, remove it entirely.
  - **Anchor-based protection:** Before removing, checks the matched sentence for concrete anchors: sensory words (smell, taste, cold, etc.), concrete objects (door, rain, phone, etc.), action verbs (grabbed, slammed, fell, etc.), or proper nouns (real character/place names, excluding common words like "This", "Something", "Tonight"). Anchored sentences are kept -- they have real detail, not empty AI filler.
- **Tics:** 30+ patterns (hair taming, jaw clenching, heart racing, warmth spreading, comfort zone, etc.). Limits each to max occurrences per scene (typically 1-2).
- **Language:** Fixes wrong-language phrases (e.g. Spanish in Italian setting).

---

### Layer G: Pre-Export Validation

**Location:** `export/scene_validator.py`; called from `docx_exporter._validate_scenes()`
**When:** Before building the Word document
**Purpose:** Catch meta-text, cross-contamination, duplicate scenes. Now produces actionable reports.

| Check | Severity | Config |
|-------|----------|--------|
| META_TEXT | error | Built-in (8 patterns, each with `pattern_name`) |
| SHORT_SCENE | warning | Built-in (< 100 words) |
| SUSPECT_NAME | warning | `market.tone_constraints.suspicious_names` |
| SUSPECT_NAME_RECURRING | error | Same name in >= 3 scenes |
| GENRE_CROSS_CONTAM | error | `market.tone_constraints.disallow_terms` |
| DUPLICATE_SCENE | warning | SHA256 fingerprint match |

**Issue structure:** Each issue now includes:
- `severity`, `code`, `scene_id`, **`scene_index`** (integer), `offset`, `excerpt`, **`pattern_name`** (human-readable), `message`

**Formatted report:** `format_validation_report(issues)` produces a grouped, human-readable report:
```
Validation: 2 error(s), 1 warning(s)
============================================================

  Ch1Sc1 (index 0):
    [ERROR] certainly_preamble @ offset 0
           "Certainly! Here is the revised scene..."
    [WARNING] word_count_low @ offset 0
           "Too short. Too short. Too short..."
```

**Validation mode:** `export.validation_mode` in project config.
- `strict`: Block export on any error.
- `lenient` (default): Log issues, allow export.

**G→Pipeline Feedback Loop** (`_validation_feedback_loop()`):

During `output_validation`, scene validation runs automatically. For scenes with `META_TEXT` errors:
1. First attempt: re-run through `_postprocess_scene()` (no LLM cost)
2. If still dirty: request clean rewrite from LLM with format contract
3. Accept rewrite only if it retains ≥50% of original word count (prevents empty rewrites)
4. Max 5 scenes per feedback loop (bounds cost)
5. Results stored in `validation_report["feedback_loop"]`

---

### Layer H: Transaction Safety (6-Check Integrity)

**Location:** `_run_stage()` in `pipeline.py`
**When:** Before/after each prose stage
**Behavior:** Snapshot `self.state.scenes` before prose stage. After stage completes, run 6 integrity checks. Any failure restores the snapshot and returns `StageStatus.FAILED`.

| Check | Trigger | What It Catches |
|-------|---------|-----------------|
| **1. Scene count drop** | `new_count < old_count * 0.5` | Stage deleted/lost half the scenes |
| **2. Prefix corruption** | >30% of scenes share identical first 100 chars | Stage wrote same preamble/garbage into every scene |
| **3. Emptied scenes** | Any scene that had content (>50 chars) is now empty | Stage blanked out scenes |
| **4. Average word count plummet** | Avg word count dropped >40% | Stage truncated/corrupted most scenes |
| **5. Forbidden-marker explosion** | >40% of scenes contain meta-text markers (preambles, "rest unchanged", "changes made:", etc.) | Model regressed to assistant mode across the board |
| **6. Fingerprint uniqueness collapse** | Unique scene fingerprints dropped >50% | Previously-distinct scenes became identical |

Each check logs an ERROR with specifics and restores the snapshot. The stage result includes the error description.

---

### Layer I: Final DE-AI Post-Check

**Location:** End of `_stage_final_deai()` in `pipeline.py`
**When:** After all scenes processed by final_deai
**Purpose:** Since final_deai bypasses the critic gate, it needs its own validation.

| Check | Action |
|-------|--------|
| Word count delta > 15% for any scene | Restore original scene (the "fix" was worse) |
| Homogeneous corruption (>30% share prefix) | Restore ALL scenes to pre-deai state |

---

### Validation-Phase Stages (final_deai, quality_audit, output_validation)

These run after polish and have their own logic:

| Stage | Purpose | Defense Role |
|-------|---------|--------------|
| **final_deai** | Surgical AI-tell removal | **Paragraph-based protection:** First 3 paragraphs (chapter opening) and last 4 paragraphs (chapter hook) are *protected*. Only the *middle* paragraphs of chapter-end scenes are edited. Uses **SURGICAL_REPLACEMENTS loaded from `configs/surgical_replacements.yaml`** (40+ patterns across 4 categories: AI tells, hollow intensifiers, stock metaphors, emotional summarization; falls back to hardcoded defaults if YAML missing) and nonce-aware FORMAT_CONTRACT for targeted LLM rewrites. Includes Layer I post-check. |
| **quality_audit** | Audit word count, AI tells, scene lengths, spice, hooks, **freshness** | Can set `needs_iteration` and `stages_to_rerun`. Triggers re-run of **scene_expansion** (word count low, short scenes) or **voice_human_pass** (AI tells high). Max 2 iterations. **Diminishing-returns exit:** Skips re-run if word% delta < 5% AND tells delta < 0.5. **Freshness score (step 6):** Computes bigram overlap between each scene and its 3 predecessors; flags scenes with >40% overlap as "stale" (recycled language). |
| **output_validation** | Final stats + quality rating + feedback loop + save | Produces `validation_report` with word counts, quality_score (LLM rates 3 sample scenes), **artifact_metrics**, **feedback loop results**, and **cross-run metrics delta**. Runs Layer G→Pipeline feedback loop (see below). Persists artifact metrics to JSONL history. Saves markdown and pipeline state. |

---

## 4. Problem -> Defense Mapping

| Problem | Primary Defense | Fallback |
|---------|-----------------|----------|
| "Certainly! Here is..." | B (sentinel + stop) | A, D (exact + fuzzy preamble) -> E (scored retry), F1, G |
| "The rest remains unchanged" | B (stop seq) | D -> E (issue-specific retry), F1.5, F2, G |
| Duplicate/stitched versions | F2 (stitch + suffix/prefix + n-gram) | F2b (semantic dedup), D (alternate_version) |
| Cross-contamination (wrong names) | C (context hygiene + schema validation) | G (config-driven + pattern_name) |
| POV drift (third-person slip) | F3 (quote-masked, clause-guarded enforce) | F3b (contextual repair), D (records for metrics) |
| Analysis/commentary appended | B (sentinel), A | D -> E (issue-specific), F1 Phase 2, G |
| AI tells / hollow prose | F4 (limit tics), final_deai (paragraph-protected) | Layer I (post-check restores on corruption) |
| Emotional summary filler | F4 (anchor-protected stripping) | -- |
| Stage crash / corrupt output | H (5-check transaction safety) | -- |
| Paraphrased restart (same content, different words) | F2b (semantic dedup) | -- |
| Scene drift from outline | C (alignment check every 5 scenes) | -- |
| Suspicious data in context | C (schema validation + prompt injection detection) | -- |
| Cleanup over-stripping | F1 Phase 2.5 (active salvage guardrail), disabled_builtins | F4 anchor protection |
| Forbidden-marker explosion (model regressed) | H check 5 (>40% scenes polluted → rollback) | -- |
| Stale/recycled language across scenes | quality_audit freshness score (bigram overlap >40%) | -- |
| Cross-run quality regression | Cross-run metrics delta analysis | -- |
| Meta-text leaking to export | G→Pipeline feedback loop (auto postprocess + rewrite) | G pre-export validation |
| Prompt injection in context | C (5 injection patterns in schema validation) | -- |

---

## 5. Artifact Metrics (Diagnostics)

**Location:** `PipelineState.artifact_metrics`
**Persisted:** Yes (saved in `{project_path}/pipeline_state.json` per run, **and appended to `{project_path}/artifact_metrics_history.jsonl` for cross-run trend analysis**)
**Logged:** `_log_artifact_summary()` after each stage; included in `output_validation`'s validation report

| Metric | Meaning |
|--------|---------|
| `total_scenes_generated` | All scene outputs |
| `scenes_with_preamble` | Raw output had preamble (model issue) |
| `scenes_with_meta_text` | Truncation or analysis marker |
| `scenes_with_duplicate_marker` | Alternate version marker |
| `scenes_with_pov_drift` | Third-person refs in first-person story |
| `scenes_retried` | Critic gate triggered retry |
| `per_stage.{stage}` | Breakdown by stage |
| `per_scene.{scene}.retried` | Whether specific scene was retried |
| `per_scene.{scene}.preamble` | Preamble detected in specific scene |

**Cross-run delta analysis** (`_compute_metrics_delta()`):

After persisting current metrics to JSONL, computes a delta against the previous run. Each metric gets a `previous`, `current`, `change`, and `direction` (improved/regressed/changed). Delta is included in `validation_report["metrics_delta"]`.

Example output:
```json
{
  "scenes_with_preamble": {"previous": 5, "current": 2, "change": -3, "direction": "improved"},
  "scenes_retried": {"previous": 8, "current": 12, "change": 4, "direction": "regressed"}
}
```

**How to infer:**
- High `preamble` / `truncation` -> model still emitting meta-text; consider stronger FORMAT_CONTRACT or more stop sequences.
- High `retried` -> critic gate useful but retries add cost. Check if issue-specific feedback is helping.
- High `pov_drift` -> POV enforcement (F3) helps; check dialogue masking works.
- Per-stage spikes -> that stage's prompt or model needs tuning.
- Diminishing returns triggered -> audit is working efficiently; no wasted iterations.
- **Cross-run regression** -> compare delta; if `preamble` regressed, check if model version changed or temperature increased.

---

## 6. Config Reference

### Project config (`config.yaml`)

```yaml
# POV / voice
writing_style: "First person, Lena's POV"
protagonist: "Lena Castillo, 31..."
other_characters: "Sofia Chen--..., Marco Vitale--..."

# Pre-export validation
export:
  validation_mode: lenient   # or strict

# Genre constraints (opt-in)
market:
  tone_constraints:
    disallow_terms: ["concealed blade", "bratva"]
    suspicious_names: ["Natalia", "Viktor"]
```

### Cleanup patterns (`configs/cleanup_patterns.yaml`)

```yaml
inline_truncate_markers:
  - "the rest remains unchanged"
  - "rest of the scene remains unchanged"
  # ... add more

inline_preamble_markers:
  - "certainly! here is"
  - "here is the revised"
  # ... add more

regex_patterns:
  - name: meta_opening
    pattern: "(?is)^\\s*(certainly|sure)..."

# Suppress specific built-in patterns per project
disabled_builtins:
  - "Physical beats"     # Our prose legitimately uses this phrase
  # ... add more substrings to suppress
```

**Merge rule:** Built-ins always present; YAML adds more. `disabled_builtins` suppresses specific built-in patterns by substring match.

### Surgical replacements (`configs/surgical_replacements.yaml`)

```yaml
ai_tell_phrases:
  "I couldn't help but notice": ""
  "I found myself": "I"
  # ...

hollow_intensifiers:
  " incredibly ": " "
  # ...

stock_metaphors:
  "a whirlwind of emotions": "confusion"
  # ...

emotional_summarization:
  "This wasn't just about": ""
  # ...
```

**Loaded by:** `_load_surgical_replacements()` in `PipelineOrchestrator`. Falls back to hardcoded `_DEFAULT_SURGICAL_REPLACEMENTS` if YAML not found. All categories are flattened into a single `{pattern: replacement}` dict. Changes take effect on next pipeline run (no restart needed).

---

## 7. Improvement Inference Guide

| Symptom | Likely Cause | Action |
|---------|--------------|--------|
| Preamble still in output | Stop sequences not firing; fuzzy detection missed | Add variant to CREATIVE_STOP_SEQUENCES; add exemplar to `_PREAMBLE_EXEMPLARS`; check client passes `stop` |
| "Rest unchanged" + alternate kept | Cleanup truncation missed | Verify Phase 1.5 runs; add marker to YAML if needed |
| Wrong character names in scene | Context from other project | Audit `_build_scene_context`; check context hash logs; check `_validate_context_schema()` warnings |
| POV drift after voice_human_pass | F3 not applied, wrong gender, or dialogue masking failed | Check `_get_protagonist_gender()`; ensure F3 runs; verify quote masking covers curly quotes |
| "his friend" incorrectly -> "my friend" | Clause guard missed a pattern | Add relative pronoun to `_safe_poss_replace()` lookback |
| Good prose stripped by cleanup | Pattern matched legitimate content | Add phrase to `disabled_builtins` in YAML; check anchor protection |
| Summary sentence kept despite pattern match | Anchor detection false positive | Review anchor word lists; may need to exclude word from common-caps set |
| High retry rate | Model ignores FORMAT_CONTRACT | Strengthen A; check issue-specific feedback; try lower temperature |
| Per-stage preamble spike | Stage-specific prompt leak | Review stage prompt; add explicit prose-only instruction |
| Export blocked (strict) | Validation error | Fix scenes or set `validation_mode: lenient`; check report for scene_index + pattern_name |
| Duplicate scenes in docx | F2 didn't split | Add marker to stitch_markers; check suffix/prefix overlap thresholds; check G DUPLICATE_SCENE |
| Scenes drifting from outline | Beat sheet divergence | Check alignment warnings in logs (every 5 scenes); review outline coverage |
| Stage emptied/corrupted scenes | LLM hallucinated or failed | Transaction safety (H) should auto-restore; check logs for which check triggered |
| Quality audit re-running forever | Diminishing returns not detected | Check `_prev_audit_snapshot` delta thresholds |
| Stale/repetitive language across scenes | Model recycling phrases | Check freshness score in quality_audit; scenes >40% bigram overlap flagged |
| Meta-text in exported docx | Feedback loop didn't catch it | Check feedback_loop report in validation_report; may need to add patterns to scene_validator |
| Metrics regressed from last run | Model version or config changed | Check `metrics_delta` in validation_report for direction of change |
| Prompt injection in scene context | Malicious content in project data | Check schema validation warnings in logs; 5 injection patterns checked |
| Many scenes trigger forbidden-marker check | Model systematically regressed | Transaction safety check 5 (>40% scenes polluted) triggers rollback; check model/temp |

---

## 8. File Reference

| Component | File |
|-----------|------|
| FORMAT_CONTRACT, PROSE_SENTINEL, nonce sentinel, stop sequences, retry, scoring | `prometheus_novel/stages/pipeline.py` |
| Critic gate, fuzzy preamble (anchor-gated), artifact metrics | `prometheus_novel/stages/pipeline.py` |
| Context assembly, schema validation (+ prompt injection), alignment check, hashing | `prometheus_novel/stages/pipeline.py` (_build_scene_context, _validate_context_schema, _check_alignment) |
| Cleanup, postprocess, active salvage guardrail | `prometheus_novel/stages/pipeline.py` (_clean_scene_content) |
| Duplicate detection (stitch + suffix/prefix + n-gram + semantic) | `prometheus_novel/stages/pipeline.py` (_detect_duplicate_content, _detect_semantic_duplicates) |
| POV enforcement (quote masking, clause guard, contextual repair) | `prometheus_novel/stages/pipeline.py` (_enforce_first_person_pov, _mask_quoted_dialogue, _repair_pov_context_errors) |
| Emotional summary stripping (anchor-protected) | `prometheus_novel/stages/pipeline.py` (_strip_emotional_summaries) |
| Transaction safety (6-check integrity + forbidden-marker explosion) | `prometheus_novel/stages/pipeline.py` (_run_stage) |
| Final DE-AI (paragraph-based protection + post-check) | `prometheus_novel/stages/pipeline.py` (_stage_final_deai) |
| Freshness score (bigram overlap) | `prometheus_novel/stages/pipeline.py` (_stage_quality_audit) |
| Feedback loop (G→Pipeline auto-fix) | `prometheus_novel/stages/pipeline.py` (_validation_feedback_loop) |
| Cross-run metrics persistence + delta | `prometheus_novel/stages/pipeline.py` (_persist_artifact_metrics, _compute_metrics_delta) |
| Surgical replacements YAML config | `prometheus_novel/configs/surgical_replacements.yaml` |
| Pre-export validation (actionable reports) | `prometheus_novel/export/scene_validator.py` |
| Export + validation mode | `prometheus_novel/export/docx_exporter.py` |
| Cleanup patterns YAML + disabled_builtins | `prometheus_novel/configs/cleanup_patterns.yaml` |
| LLM clients (stop mapping) | `prometheus_novel/prometheus_lib/llm/clients.py` |

**State file:** `{project_path}/pipeline_state.json` -- contains scenes, artifact_metrics, completed_stages, etc.
**Metrics history:** `{project_path}/artifact_metrics_history.jsonl` -- append-only JSONL with per-run metrics for trend analysis.
