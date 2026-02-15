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
| Detect prompt injection in context | Two-factor detection: injection phrase + structural cue (avoids false positives on villain dialogue) |
| Auto-fix validation errors | G→Pipeline feedback loop (prioritized by severity, with entity preservation guard) |
| Track quality trends across runs | Cross-run JSONL metrics + config fingerprint + delta analysis |
| Hot-configurable DE-AI patterns | `configs/surgical_replacements.yaml` (loaded at runtime) |
| Prevent aggressive LLM rewrites | Per-paragraph word count guard in final_deai middle section |
| Halt cascading failures | Circuit breaker: 3 consecutive stage failures halts pipeline |
| Track per-stage meta-text rate | Forbidden marker rate metric after each prose stage |
| Precise pattern suppression | `disabled_builtins` by exact pattern_name (with legacy substring fallback) |
| Preserve entities on rewrite | Entity intersection check: protagonist + >=2 shared named entities required |
| Filter freshness false positives | Content-word bigrams (stopwords + character names filtered) |
| Salvage meta-marker awareness | Active salvage flags restored content containing hard meta-markers for regen |
| Configurable defense thresholds | All hardcoded thresholds overridable via `config.yaml defense.thresholds` namespace |
| Budget guards | Max retries/stage, max rewritten scenes, defense cost ratio — prevents runaway defense spending |
| Prose integrity checksums | SHA256 hashes at raw and clean stages per scene (`content_hash_raw`, `content_hash_clean`) |
| Extended quote masking | Italic thoughts, block quotes, bracketed messages excluded from POV/cleanup passes |
| Foreign word whitelist | Per-project whitelist in config + sentence-length guard (single words preserved unless in foreign cluster) |
| Sliding window semantic dedup | Non-overlapping window comparison replaces midpoint split — catches mid-scene restarts |
| Cleanup audit trail | Cleanup morgue JSONL logs every deletion with trigger pattern, context, and phase |
| Name-aware pronoun guard | Per-paragraph He/She→I skips paragraphs mentioning other same-gender characters |
| Model drift alarm | Preamble/meta-text rate jump >50% AND >3 absolute triggers alarm with config fingerprint |
| YAML config validation | Schema validation on cleanup_patterns and surgical_replacements load (keys + regex compilation) |
| Feedback loop retention guard | ≥80% word count retention required for LLM rewrites (up from 50%) |
| Entity guard scaling | Short scenes (<200w) require only ≥1 shared noun (vs ≥2 for normal), prevents false rejection |
| Threshold bounds validation | All thresholds clamped to valid [min, max] range; logs warning on out-of-bounds config |
| Prompt echo/leak detection | 12 FORMAT_CONTRACT fingerprints checked in output; prompt_leak is fixable with retry |
| Dialogue integrity check | Unbalanced smart/straight quotes + dialogue-to-narration ratio >85% flagged |
| Incident packet logging | `incidents.jsonl` records all rollbacks, circuit breaker trips with failure categorization |
| Run status checkpoint | `run_status.json` updated after each stage: completed stages, budget, incidents |
| Circuit breaker failure categorization | Transient (API/timeout/429) vs content (validation) classification on each incident |
| Canary scene pre-flight | Tests each unique model with a tiny prose prompt before real run; catches prompt leak/preamble/downtime |
| Defense mode switch | observe (log only) / protect (default) / aggressive (stricter thresholds via multipliers) |
| Continuation marker detection | Trailing "...", "(continued)", "[Scene continues]", "to be continued" caught in critic gate |
| Morgue size rotation | JSONL morgue auto-rotates at 5MB; prevents unbounded file growth across runs |
| Common caps entity filter | `COMMON_CAPS` set filters 60+ sentence-start words from entity guard (avoids false "The"/"General" matches) |
| Context containment boundary | `<user_content_boundary>` XML fences around scene content in prompts; injection incident logging |
| Salvage restore audit | Salvage restores logged to cleanup morgue with `salvage_restore` phase tag |

**Non-goals:** No genre policing unless config opts in. No heavy-handed rewriting -- cleanup truncates; validation flags.

---

## 2. Pipeline Flow (24 stages, 7 phases)

```
PLANNING -> DRAFTING -> CONTINUITY -> REFINEMENT -> POLISH -> DE-AI -> VALIDATION
```

| Phase | Stages |
|-------|--------|
| **Planning** (8) | high_concept, world_building, beat_sheet, emotional_architecture, character_profiles, motif_embedding, master_outline, trope_integration |
| **Drafting** (3) | scene_drafting, scene_expansion, structure_gate |
| **Continuity** (4) | continuity_audit, continuity_fix, continuity_recheck, self_refinement |
| **Refinement** (3) | voice_human_pass, continuity_audit_2, continuity_fix_2 |
| **Polish** (3) | dialogue_polish, prose_polish, chapter_hooks |
| **DE-AI** (1) | final_deai |
| **Validation** (2) | quality_audit, output_validation (includes G→Pipeline feedback loop as sub-step) |

**Prose stages** (get FORMAT_CONTRACT + stop sequences):
scene_drafting, scene_expansion, self_refinement, continuity_fix, continuity_fix_2, voice_human_pass, dialogue_polish, prose_polish, chapter_hooks, final_deai. **structure_gate** repair path (when FAIL triggers) also uses `_generate_prose`.

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
- End your output with <END_PROSE_a3f1b2c9> on its own line when finished.
```
(Where `a3f1b2c9` is the per-run nonce — a different hex string each time.)

**Nonce sentinel:** Each pipeline run generates a unique 8-hex-char nonce via `secrets.token_hex(4)`. The static `<END_PROSE>` in FORMAT_CONTRACT is replaced with `<END_PROSE_{nonce}>` (e.g. `<END_PROSE_a3f1b2c9>`), making the stop token unpredictable (won't appear in training data) and unique per run (prevents cross-run prose collisions). The postprocessor strips both static and nonce variants via regex `(?i)<END_PROSE(?:_[a-f0-9]+)?>`.

**Override:** Stages can pass a custom `system_prompt`; otherwise the nonce-aware format contract is default.

---

### Layer B: Sentinel Stop Token + Backup Sequences

**Location:** `PROSE_SENTINEL` (static) + `self._prose_sentinel` / `self._stop_sequences` (per-run) in `pipeline.py`; passed to clients via `stop=` / `stop_sequences=`
**When:** Every LLM call for prose stages
**Purpose:** Primary: nonce sentinel gives clean, unique stop per run. Backup: catch assistant-mode preambles if model ignores sentinel.

| Token | Purpose |
|-------|---------|
| `\n<END_PROSE_a3f1...>` | **Primary nonce sentinel** -- unique per run, unpredictable |
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
| `_validate_context_schema()` | Runtime check for red flags: credentials, Python code, import statements, template placeholders, debug markers, **prompt injection attempts** (two-factor detection: 5 injection phrases × 7 structural cues. Both present = ERROR (high-confidence injection). Phrase alone = WARNING (may be villain dialogue). Prevents false positives on "ignore him" type prose). Logs warnings; does not block. |
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

#### F1: `_clean_scene_content()` -- multi-phase cleanup

| Phase | Purpose |
|-------|---------|
| **1** | Strip preamble at **start** ("Certainly! Here is...", "Sure, here's...") |
| **1.5** | **Truncate** at "rest remains unchanged" (and YAML markers). Keep text before; drop alternate. |
| **1.6** | **Truncate** at mid-text LLM preamble ("Certainly! Here is the revised opening...") if prefix >= 400 chars or >= 8 lines |
| **2** | Truncate at tail markers (---, ***, "Changes made:", etc.) |
| **2.5** | **Salvage guardrail (active + meta-aware)**: If remaining text < 150 words or < 2 paragraphs, log warning. If < 50 words **and the original pre-cleanup input had 3x more words (≥50)**, automatically **restores the pre-cleanup input**. Before restoring, checks for **hard meta-markers** (preambles, "rest unchanged", "changes made:", "here is the revised") — if found, restores but flags `[contains meta-markers, needs regen]` so downstream feedback loop can prioritize it. |
| **3** | Inline removal (CURRENT SCENE:, Physical beats:, XML tags, etc.) |
| **4** | Whitespace cleanup |

**YAML extension:** `configs/cleanup_patterns.yaml` adds `inline_truncate_markers`, `inline_preamble_markers`, `regex_patterns`.

**`disabled_builtins`:** YAML list of exact pattern names (preferred) or substring matches (legacy fallback). Each built-in pattern has a unique name (e.g., `beat_sheet_physical`, `rest_unchanged`, `hook_instruction_bleed`). Listing a pattern_name in `disabled_builtins` skips that exact pattern. Substring matching still works as fallback for backwards compatibility.

#### F2: `_detect_duplicate_content()`

Three detection layers:

1. **Stitch marker split:** Split on stitch markers (rest unchanged, `---`, `***`, "Version N", "Alternative:", "Revised:", "Take N"); keep segment 0.
2. **Suffix/prefix overlap:** Check if the last N words (N = 60, 40, or 25) appear earlier in the text. If so, truncate at the duplicate. Catches verbatim ending repetition.
3. **N-gram similarity dedup:** Paragraph-level Jaccard similarity (> 60% overlap = duplicate paragraph removed).

#### F2b: `_detect_semantic_duplicates()` — Sliding Window

**When:** After duplicate detection, before POV enforcement.
**Purpose:** Catch paraphrased restarts (same content rewritten slightly differently).

- **Sliding window approach (v5):** Builds non-overlapping windows of `WINDOW_SIZE` paragraphs (max 3, min 2). Compares each window against all previous non-overlapping windows. Non-overlapping stride prevents false positives from shared paragraph content.
- Computes embedding cosine similarity (sentence-transformers `all-MiniLM-L6-v2` if available) or falls back to bigram Jaccard overlap.
- Threshold: > 50% similarity = truncate at the start of the duplicate window.
- **Minimum text length:** 500 chars (skip short scenes).
- **Why sliding instead of midpoint:** Midpoint split only catches "restart from beginning" pattern. Sliding window catches mid-scene restarts, partial rewrites, and late-scene paraphrasing.

#### F3: `_enforce_first_person_pov()`

Gender-aware POV enforcement with three protection mechanisms:

1. **Dialogue quote masking:** `_mask_quoted_dialogue()` replaces all text inside quotation marks ("..." and curly quotes), italic thoughts (`*...*`), block quotes (`> ...`), and bracketed messages (`[...]`) with `__DIALOGUE_N__` placeholders before any pronoun replacement. Preserves sentence-boundary punctuation after placeholders so subsequent patterns still match. Restores dialogue after all replacements.

2. **Clause-level possessive guard:** `_safe_poss_replace()` checks 20 chars before each possessive match. Skips replacement if preceded by relative pronouns (`who`, `that`, `which`, etc.) or `of` -- prevents "the woman who had been his friend" from becoming "my friend".

3. **Name-aware pronoun guard (v5):** POV replacement operates per-paragraph. Before replacing `He/She → I` in a paragraph, scans for other capitalized character names (excluding the protagonist and common caps like "The", "This"). If the paragraph mentions another same-gender character (e.g., "Viktor"), pronoun replacements are skipped for that paragraph to prevent "Viktor lunged. He swung" → "I swung" catastrophic errors.

4. **Core replacements:**
   - `[Name] verb` -> `I verb` (always safe)
   - `[Name]'s body_part` -> `my body_part` (always safe)
   - `He/She verb` -> `I verb` (gender-matched, sentence boundaries only, name-aware)
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
| **P8: Generic clause-level POV** | "She paused, my hand trembling" | -> "her hand trembling" (detects `She/He` + `my/My` in same sentence, replaces possessive to match third-person subject) |

#### F4: `_strip_emotional_summaries()`, `_limit_tic_frequency()`, `_flag_language_inconsistencies()`

- **Emotional summaries:** ~30+ patterns matching paragraph-ending sentences that explain what a scene means emotionally (e.g. "This wasn't just about...", "Something about this moment...", "A fragile connection...", "Whatever came next...", "For the first time in..."). Now handles:
  - **Single-sentence paragraphs:** If the entire paragraph is a summary pattern, remove it entirely.
  - **Anchor-based protection:** Before removing, checks the matched sentence for concrete anchors: sensory words (smell, taste, cold, etc.), concrete objects (door, rain, phone, etc.), action verbs (grabbed, slammed, fell, etc.), or proper nouns (real character/place names, excluding common words like "This", "Something", "Tonight"). Anchored sentences are kept -- they have real detail, not empty AI filler.
- **Tics:** 30+ patterns (hair taming, jaw clenching, heart racing, warmth spreading, comfort zone, etc.). Limits each to max occurrences per scene (typically 1-2).
- **Language (v5):** Fixes wrong-language phrases (e.g. Spanish in Italian setting). Now with:
  - **Foreign word whitelist:** Per-project list from `config.yaml defense.foreign_word_whitelist` — whitelisted words/phrases are never touched (e.g., "khachapuri", "amore mio").
  - **Sentence-length guard:** Single foreign words (1 token) only replaced if surrounded by 2+ other foreign-looking words (accented characters). Multi-word patterns (2+ words like "Mi amor") always apply.
  - Quoted text already protected upstream by dialogue masking.

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
1. **Prioritization:** Scenes sorted by error count (most errors first), then by index (early chapters first)
2. **Systemic flag:** If >5 scenes need fixes, logs `SYSTEMIC` error indicating upstream stage failure
3. First attempt: re-run through `_postprocess_scene()` (no LLM cost)
4. If still dirty: request clean rewrite from LLM with format contract
5. **Entity preservation guard:** Rewrite accepted only if:
   - Protagonist name (or "I" for first-person) preserved
   - >=2 shared capitalized nouns between original and rewrite (prevents character drift)
6. Accept rewrite only if it retains ≥50% of original word count (prevents empty rewrites)
7. Max 5 scenes per feedback loop (bounds cost)
8. Results include `total_fixable`, `attempted`, `fixed`, `systemic_warning`

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

**Circuit Breaker:** If 3 consecutive stages fail (and restore snapshots), the pipeline halts entirely with a `CIRCUIT BREAKER` error log that includes the failed stage names and diagnostic guidance. Prevents runaway cost/time when the model is systematically broken. Resets on any successful stage completion.

---

### Layer I: Final DE-AI Post-Check

**Location:** End of `_stage_final_deai()` in `pipeline.py`
**When:** After all scenes processed by final_deai
**Purpose:** Since final_deai bypasses the critic gate, it needs its own validation.

| Check | Action |
|-------|--------|
| Word count delta > 15% for any scene | Restore original scene (the "fix" was worse) |
| **Per-paragraph word count > 50% loss** | **Reject LLM rewrite of middle section** (paragraph shrank too aggressively). Keeps original middle paragraphs. Only applies to chapter-end scenes with head/tail protection. |
| Homogeneous corruption (>30% share prefix) | Restore ALL scenes to pre-deai state |

---

### Layer J: Budget Guards (v5)

**Location:** `_budget_tracker` dict on `PipelineOrchestrator`, checked in `_generate_prose()`, `_validation_feedback_loop()`, `_persist_artifact_metrics()`
**When:** During generation (per retry), feedback loop (per rewrite), and post-run (ratio check)
**Purpose:** Prevent runaway defense spending. Three limits:

| Guard | Default | Location | What happens |
|-------|---------|----------|--------------|
| Max retries per stage | 3 | `_generate_prose()` | After 3 retries for one stage, accepts output with known issues + logs BUDGET GUARD warning |
| Max rewritten scenes | 15 | `_validation_feedback_loop()` | After 15 scenes rewritten across all loops, stops rewriting + logs BUDGET GUARD warning |
| Defense cost ratio | 30% | `_persist_artifact_metrics()` | If defense tokens / total tokens > 30%, logs BUDGET GUARD warning (advisory, not blocking) |

**Tracking:** `_budget_tracker` stores `retries_per_stage` (dict), `rewritten_scenes` (int), `defense_tokens` (int), `generation_tokens` (int). Reset at start of each `run()`. Persisted in `artifact_metrics_history.jsonl` under the `budget` key.

---

### Layer K: Cleanup Morgue (v5)

**Location:** `_cleanup_morgue` list + `_log_to_morgue()` / `_flush_morgue()` in `pipeline.py`
**When:** During Phase 3 inline removal + output validation flush
**Purpose:** Audit trail of every text deletion. Enables false positive review without re-running pipeline.

Each entry: `{scene_id, deleted_text (first 200 chars), trigger_pattern, phase, timestamp}`. Flushed to `{project_path}/cleanup_morgue.jsonl` during output validation.

---

### Layer L: Model Drift Alarm (v5)

**Location:** `_compute_metrics_delta()` in `pipeline.py`
**When:** After persisting current run metrics
**Purpose:** Detect sudden quality degradation between runs.

Triggers when `scenes_with_preamble` or `scenes_with_meta_text` jumps >50% AND increases by >3 absolute. Logs `MODEL DRIFT ALARM` with run nonce, model IDs, and config hashes for debugging.

### Layer M: Incident Packet + Run Status (v6)

**Location:** `_log_incident()`, `_flush_incidents()`, `_write_run_status()` in `pipeline.py`
**When:** On every rollback, circuit breaker trip, canary failure; run_status updated after each stage
**Purpose:** Structured post-mortem data for debugging failed runs.

- `incidents.jsonl`: Each entry has `timestamp`, `stage`, `category`, `severity`, `failure_type` (transient/content), `detail`, `scene_count_before/after`
- `run_status.json`: Overwritten after each stage with completed stages, budget snapshot, incident count, scene count, total tokens/cost
- Failure categorization: `_classify_failure()` checks error message against `_TRANSIENT_ERROR_PATTERNS` (timeout, 429, 503, connection, etc.) to separate infrastructure issues from content problems

### Layer N: Canary Scene Pre-Flight (v6)

**Location:** `_canary_scene_check()` in `pipeline.py`
**When:** After `run()` initializes, before main stage loop
**Purpose:** Quick model health check that catches prompt leak, preamble, and API failures before burning tokens.

- Sends "Write exactly two sentences of fiction about a cat sitting on a windowsill watching rain" to each unique model client
- Checks for: empty response, FORMAT_CONTRACT fingerprints in output, preamble patterns
- Logs canary_failure incidents but does NOT halt the run (warning, not error)
- Can be disabled via `defense.canary_enabled: false` in config

### Layer O: Defense Mode Switch (v6)

**Location:** `_defense_mode` attribute, `_get_threshold()`, `_run_stage()` in `pipeline.py`
**When:** Set from `config.yaml defense.mode` at start of `run()`
**Purpose:** Allow users to tune defense aggressiveness per-project.

| Mode | Behavior |
|------|----------|
| **observe** | All checks run and incidents are logged, but NO snapshot restores happen. Scene content flows through unchecked. For debugging/analysis. |
| **protect** | Default. All checks active; rollback on failure. |
| **aggressive** | All `_AGGRESSIVE_MULTIPLIERS` applied: detection thresholds tightened by ~30% (e.g. `scene_count_drop_pct` × 0.7). Catches subtler corruption at the cost of more false positives/restores. |

### Layer P: Dialogue + Continuation Integrity (v6)

**Location:** `_validate_scene_output()` in `pipeline.py`
**When:** Critic gate, runs on every prose stage output
**Purpose:** Catch sneaky truncation and garbled dialogue.

- **Dialogue unbalanced:** Smart quotes (`\u201c`/`\u201d`) must match within ±2; odd straight quote count > 3 flagged
- **Dialogue ratio high:** >85% of scene words inside quotes indicates possible all-dialogue corruption
- **Continuation markers:** 7 patterns in last 100 chars: trailing `...`, `(continued)`, `[continued]`, "to be continued", "[Scene continues]", "[Rest of scene...]", "and so on/forth"

---

### Quality Gate Stages (structure_gate, continuity_recheck)

**structure_gate** (Gate A Lite) — `pipeline.py` ~5869

| Attribute | Value |
|-----------|-------|
| **Position** | After scene_expansion, before continuity_audit |
| **Purpose** | Fix scene structure before continuity — avoid "decorating a house while the foundation is wet" |
| **Scoring** | Gemini, temp 0.15, JSON mode. 5 categories (0–5 each): structure, tension, emotional_beat, dialogue_realism, scene_turn |
| **Pass condition** | Total ≥ 16/25 AND no category < 3 |
| **Repair** | FAIL triggers targeted rewrite via `_generate_prose` (Claude, temp 0.45) — gets full artifact prevention |
| **Context** | Outline via `_get_outline_for_scene()`; scene text truncated to last 900 words for scoring efficiency |
| **Stop rule** | Max 2 iterations per scene; still-failing scenes get WARNING log, pipeline continues |
| **Repair prompt** | Includes specific fix directives from the scorecard |

**continuity_recheck** — `pipeline.py` ~6340

| Attribute | Value |
|-----------|-------|
| **Position** | After continuity_fix, before self_refinement |
| **Purpose** | Re-validate fixed scenes — continuity_fix does not blindly pass |
| **Scope** | Audits only scenes in `self.state._continuity_fixed_indices` (tracked by continuity_fix) |
| **Loop** | If new issues found → re-fix → re-audit. Max 2 loops, then WARNING and move on |
| **Token efficiency** | Targeted audit (only modified scenes), not full manuscript |
| **Re-fix** | Uses continuity_fix client (Claude), temp 0.5; each loop narrows to only re-fixed scenes |

---

### Validation-Phase Stages (final_deai, quality_audit, output_validation)

These run after polish and have their own logic:

| Stage | Purpose | Defense Role |
|-------|---------|--------------|
| **final_deai** | Surgical AI-tell removal | **Paragraph-based protection:** First 3 paragraphs (chapter opening) and last 4 paragraphs (chapter hook) are *protected*. Only the *middle* paragraphs of chapter-end scenes are edited. Uses **SURGICAL_REPLACEMENTS loaded from `configs/surgical_replacements.yaml`** (40+ patterns across 4 categories: AI tells, hollow intensifiers, stock metaphors, emotional summarization; falls back to hardcoded defaults if YAML missing) and nonce-aware FORMAT_CONTRACT for targeted LLM rewrites. **Per-paragraph word count guard** rejects LLM rewrites where any paragraph lost >50% of its words (catches aggressive rewrites at paragraph level, not just scene level). Includes Layer I post-check. |
| **quality_audit** | Audit word count, AI tells, scene lengths, spice, hooks, **freshness** | Can set `needs_iteration` and `stages_to_rerun`. Triggers re-run of **scene_expansion** (word count low, short scenes), **voice_human_pass** (AI tells high or freshness flagged). Max 2 iterations. **Diminishing-returns exit:** Skips re-run if word% delta < 5% AND tells delta < 0.5. **Freshness score (step 6):** Computes **content-word bigram** overlap (filters ~80 stopwords + character names + words <=2 chars) between each scene and its 3 predecessors; flags scenes with >40% overlap as "stale." Freshness issues now trigger `voice_human_pass` rerun in `stages_to_rerun`. |
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
| Stage crash / corrupt output | H (6-check transaction safety) | -- |
| Paraphrased restart (same content, different words) | F2b (semantic dedup) | -- |
| Scene drift from outline | C (alignment check every 5 scenes) | -- |
| Suspicious data in context | C (schema validation + prompt injection detection) | -- |
| Cleanup over-stripping | F1 Phase 2.5 (active salvage guardrail), disabled_builtins | F4 anchor protection |
| Forbidden-marker explosion (model regressed) | H check 5 (>40% scenes polluted → rollback) | -- |
| Stale/recycled language across scenes | quality_audit freshness score (bigram overlap >40%) | -- |
| Cross-run quality regression | Cross-run metrics delta analysis | -- |
| Meta-text leaking to export | G→Pipeline feedback loop (auto postprocess + rewrite) | G pre-export validation |
| Prompt injection in context | C (two-factor: injection phrase × structural cue) | Single-phrase = warning only |
| Aggressive LLM rewrite in final_deai | Layer I per-paragraph word count guard (>50% loss = reject) | Scene-level 15% delta check |
| Cascading stage failures | Circuit breaker (3 consecutive failures → halt) | -- |
| Entity drift on feedback rewrite | G entity preservation guard (protagonist + ≥2 shared nouns) | Word count threshold |
| Runaway defense spending | Budget guards: max retries/stage (3), max rewrites (15), defense ratio (30%) | Logged in artifact_metrics_history |
| Wrong-language foreign phrases | Language inconsistency fixer (Italian↔Spanish) with whitelist + sentence guard | Only multi-word patterns auto-fixed |
| Prose modified silently | Prose integrity checksums (raw vs clean hash per scene) | Logged in scene_meta |
| Over-deletion (false positive cleanup) | Cleanup morgue JSONL audit trail | Manual review + disabled_builtins |
| Name collision in POV fix (Viktor → I) | Name-aware pronoun guard (per-paragraph, skips other-name paragraphs) | -- |
| Model quality regression between runs | Model drift alarm (rate jump detection + config fingerprint diff) | -- |
| Invalid YAML configs | Schema validation on load (unknown keys, broken regexes flagged) | -- |
| Mid-scene paraphrased restart | Sliding window semantic dedup (non-overlapping windows) | Old midpoint check replaced |
| Prompt echo / system prompt in output | P (12 FORMAT_CONTRACT fingerprints) | D prompt_leak → E (retry with feedback) |
| Sneaky truncation ("...", "to be continued") | P (7 continuation marker patterns in tail) | D truncation_marker |
| Unbalanced dialogue quotes | P (smart quote ±2, odd straight quote > 3) | Warning, not error |
| Short scene rewrite rejected (entity guard) | G entity guard scaling (≥1 noun for <200w) | COMMON_CAPS filter |
| Model down / API timeout before run | N canary scene pre-flight | Incident logged as transient |
| False positive entity guard ("The", "General") | COMMON_CAPS exclusion set (60+ common words) | -- |
| Rollback event not traceable | M incident packet (incidents.jsonl) | -- |
| Run interrupted (no progress data) | M run_status.json (written after each stage) | -- |
| Over-aggressive defense thresholds | O defense mode switch (observe/protect/aggressive) | Threshold bounds validation |
| Invalid threshold in config | Bounds validation (clamp + warning) | Default used as fallback |
| Morgue file grows unbounded | Morgue rotation (5MB limit, .jsonl.old archive) | -- |
| Context injection via scene content | C containment boundary (`<user_content_boundary>` fences) | Two-factor injection detection |
| Salvage restore event not auditable | Salvage logged to morgue with phase=2.5_salvage | -- |
| Weak scene structure (flat tension, unclear goal, missing stakes) | structure_gate (Gate A Lite) — scorecard + targeted repair, max 2 iter | -- |
| Continuity fix introduces new issues or misses some | continuity_recheck — re-audit fixed scenes only, loop until pass or max 2 | -- |

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
| `per_stage.{stage}` | Breakdown by stage (includes `forbidden_marker_rate`: fraction of scenes with meta-text markers after stage completion) |
| `per_scene.{scene}.retried` | Whether specific scene was retried |
| `per_scene.{scene}.preamble` | Preamble detected in specific scene |
| `per_scene.{scene}.content_hash_raw` | SHA256 (12-char) of raw LLM output |
| `per_scene.{scene}.content_hash_clean` | SHA256 (12-char) after postprocessing |

**Budget tracking** (in `artifact_metrics_history.jsonl` entries):

| Field | Meaning |
|-------|---------|
| `budget.defense_tokens` | Tokens spent on retries + feedback loop rewrites |
| `budget.generation_tokens` | Tokens spent on primary generation |
| `budget.defense_cost_ratio` | defense / (defense + generation), ideally < 0.30 |
| `budget.retries_per_stage` | Map of stage_name → retry count this run |
| `budget.rewritten_scenes` | Total scenes rewritten in feedback loops this run |

**Config fingerprint** (`_build_config_fingerprint()`):

Each JSONL entry now includes a `config_fingerprint` object:
- `clients`: map of connected LLM client names to model IDs
- `model_overrides`: stage-specific model overrides from config
- `config_hashes`: SHA256 (12-char) of `config.yaml`, `cleanup_patterns.yaml`, `surgical_replacements.yaml`

This makes metric regressions *explainable* — you can see whether a change in preamble rate correlates with a model change, config edit, or code change.

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

# Suppress specific built-in patterns per project (by exact name or substring)
disabled_builtins:
  - "beat_sheet_physical"     # Exact pattern_name (preferred)
  - "Physical beats"          # Legacy substring match (fallback)
  # Available names: rest_unchanged, rest_unchanged_bracket, current_scene_header,
  # visible_pct_marker, enhanced_scene_header, heres_revised, hook_instruction_bleed,
  # writing_tips_bullets, scene_header_chapter, scene_header_pov, scene_header_count,
  # xml_tag_scene, xml_tag_chapter, xml_tag_content, beat_sheet_physical,
  # beat_sheet_emotional, beat_sheet_sensory
```

**Merge rule:** Built-ins always present; YAML adds more. `disabled_builtins` suppresses patterns by **exact pattern_name** (preferred) or substring match (legacy fallback).

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
| Circuit breaker halted pipeline | 3+ consecutive stage failures | Check model availability, API keys, config validity; review failed stage names in log |
| Feedback loop rejects rewrites | Entity drift detected | Check protagonist name config; may need to relax shared-noun threshold for short scenes |
| final_deai paragraph guard triggered | LLM aggressively rewrote middle | Normal safety behavior; original paragraphs kept. Consider simpler patterns in surgical_replacements.yaml |
| Forbidden marker rate climbing over runs | Model trending toward assistant mode | Compare config_fingerprint in JSONL history; may need temperature adjustment or model change |
| Budget guard: retry limit hit | Stage keeps failing critic gate | Check stage prompt; lower temperature; consider stronger model for that stage |
| Budget guard: rewrite limit hit | Too many feedback loop rewrites | Upstream meta-text problem; fix the source stage rather than relying on feedback loop |
| Budget guard: defense ratio high | >30% tokens on defense | Model may be wrong choice for these stages; check `budget` in JSONL history |
| Legitimate foreign word replaced | Whitelist missing entry | Add word/phrase to `defense.foreign_word_whitelist` in config.yaml |
| Cleanup morgue shows false positives | Pattern too aggressive | Review `cleanup_morgue.jsonl`; add pattern to `disabled_builtins` |
| MODEL DRIFT ALARM in logs | Preamble/meta-text rate jumped between runs | Compare config_fingerprint; model version may have changed |
| YAML validation warnings on load | Config file has unknown keys or broken regex | Fix the config file; check pattern syntax |
| Prose integrity hashes differ (raw ≠ clean) | Normal — postprocessing cleaned something | Review scene_meta hashes; if hash difference unexpected, check what was cleaned |
| Name-aware guard skipping paragraphs | Other character names detected in paragraph | Expected behavior; prevents "Viktor → I" catastrophic bug |

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
| Structure gate (Gate A Lite) | `prometheus_novel/stages/pipeline.py` (_stage_structure_gate, ~5869) |
| Continuity recheck | `prometheus_novel/stages/pipeline.py` (_stage_continuity_recheck, ~6340) |
| Feedback loop (G→Pipeline auto-fix) | `prometheus_novel/stages/pipeline.py` (_validation_feedback_loop) |
| Cross-run metrics + config fingerprint + delta | `prometheus_novel/stages/pipeline.py` (_build_config_fingerprint, _persist_artifact_metrics, _compute_metrics_delta) |
| Circuit breaker (consecutive failure halt) | `prometheus_novel/stages/pipeline.py` (run method) |
| Per-stage forbidden marker rate | `prometheus_novel/stages/pipeline.py` (_run_stage) |
| Surgical replacements YAML config | `prometheus_novel/configs/surgical_replacements.yaml` |
| Pre-export validation (actionable reports) | `prometheus_novel/export/scene_validator.py` |
| Export + validation mode | `prometheus_novel/export/docx_exporter.py` |
| Cleanup patterns YAML + disabled_builtins | `prometheus_novel/configs/cleanup_patterns.yaml` |
| LLM clients (stop mapping) | `prometheus_novel/prometheus_lib/llm/clients.py` |

| Budget guards (retry cap, rewrite cap, defense cost ratio) | `prometheus_novel/stages/pipeline.py` (_generate_prose, _validation_feedback_loop, _persist_artifact_metrics) |
| Cleanup morgue (audit trail of all deletions) | `{project_path}/cleanup_morgue.jsonl` |
| Foreign word whitelist + sentence-length guard | `prometheus_novel/stages/pipeline.py` (_flag_language_inconsistencies) |
| Sliding window semantic dedup | `prometheus_novel/stages/pipeline.py` (_detect_semantic_duplicates) |
| Name-aware pronoun guard | `prometheus_novel/stages/pipeline.py` (_enforce_first_person_pov) |
| Model drift alarm | `prometheus_novel/stages/pipeline.py` (_compute_metrics_delta) |
| YAML config validation | `prometheus_novel/stages/pipeline.py` (_validate_yaml_config, _load_cleanup_config) |
| Prose integrity checksums | `prometheus_novel/stages/pipeline.py` (_generate_prose) |

**State file:** `{project_path}/pipeline_state.json` -- contains scenes, artifact_metrics, completed_stages, etc.
**Metrics history:** `{project_path}/artifact_metrics_history.jsonl` -- append-only JSONL with per-run metrics for trend analysis.
**Cleanup morgue:** `{project_path}/cleanup_morgue.jsonl` -- append-only JSONL log of every text deletion with context.

---

## 9. Operational Playbook

### Pre-Run Checklist

1. **Config validation**: The pipeline auto-validates `cleanup_patterns.yaml` and `surgical_replacements.yaml` on load. Fix any warnings before continuing.
2. **Model availability**: Ensure all configured LLM clients are reachable. The circuit breaker halts after 3 consecutive failures.
3. **Resume state**: If resuming a prior run, verify `pipeline_state.json` exists and `completed_stages` is correct.
4. **Defense thresholds**: Review `config.yaml → defense.thresholds` overrides. Defaults are production-tested; only override with cause.

### During-Run Monitoring

| Signal | Where to find it | Action |
|--------|-------------------|--------|
| `CIRCUIT BREAKER` in logs | `run()` method | Pipeline halted. Check model availability, API keys. Retry. |
| `BUDGET GUARD: retry budget exhausted` | `_generate_prose()` | Stage hit max retries. Output has known issues. Review that scene manually. |
| `BUDGET GUARD: rewritten scene limit` | `_validation_feedback_loop()` | Too many scenes needed fixes. Indicates systemic upstream issue. |
| `BUDGET GUARD: defense cost ratio exceeds limit` | `_persist_artifact_metrics()` | >30% of tokens spent on defense (retries/rewrites). Consider stronger base model or lower temperature. |
| `MODEL DRIFT ALARM` | `_compute_metrics_delta()` | Preamble/meta-text rate jumped vs. prior run. Check model version change or config drift. |
| `SYSTEMIC:` prefix in feedback loop | `_validation_feedback_loop()` | >5 scenes had META_TEXT errors. Upstream stage likely failed. |
| `Transaction safety:` in logs | `_run_stage()` | A stage corrupted scene data. Snapshot auto-restored. Review which check fired. |

### Post-Run Review

1. **Artifact metrics history**: `artifact_metrics_history.jsonl` — compare `defense_cost_ratio` across runs. Ratio climbing → model quality declining.
2. **Cleanup morgue**: `cleanup_morgue.jsonl` — audit what text was deleted and why. Look for false positives (legitimate prose incorrectly flagged).
3. **Validation report**: Check `output_validation` stage output for remaining issues.
4. **Metrics delta**: If `_compute_metrics_delta` shows regression, compare `config_fingerprint` to identify what changed.
5. **Prose integrity checksums**: Compare `content_hash_raw` vs `content_hash_clean` in scene_meta to measure postprocessing impact.

### Tuning Guide

| Symptom | Threshold to adjust | Direction |
|---------|---------------------|-----------|
| Too many false positive cleanups | `disabled_builtins` in cleanup_patterns.yaml | Add pattern names to disable list |
| Legitimate foreign words being replaced | `defense.foreign_word_whitelist` in config.yaml | Add words/phrases to whitelist |
| Feedback loop too aggressive | `feedback_loop_wc_retention` | Raise toward 0.90 (stricter preservation) |
| Feedback loop too permissive | `feedback_loop_wc_retention` | Lower toward 0.70 (allow more rewriting) |
| Circuit breaker too sensitive | `circuit_breaker_threshold` | Raise from 3 to 5 |
| Budget exhausting retries | `budget_max_retries_per_stage` | Raise from 3; but also check why retries are needed |
| Defense cost too high | `budget_max_defense_ratio` | Lower if billing-sensitive; root-cause the retry need |
| Duplicate detection too aggressive | `semantic_dedup_threshold` | Raise toward 0.7 (require higher similarity to dedup) |
| Paragraph guard rejecting good rewrites | `deai_paragraph_loss_pct` | Raise toward 0.60 (allow more paragraph shortening) |

### Config.yaml Defense Namespace Reference

```yaml
defense:
  thresholds:
    scene_count_drop_pct: 0.50
    prefix_corruption_pct: 0.30
    avg_word_plummet_pct: 0.40
    forbidden_marker_pct: 0.40
    fingerprint_collapse_pct: 0.50
    deai_word_delta_pct: 0.15
    deai_paragraph_loss_pct: 0.50
    salvage_min_words: 150
    salvage_min_paragraphs: 2
    salvage_restore_ratio: 3.0
    freshness_bigram_pct: 0.40
    feedback_loop_max_scenes: 5
    feedback_loop_wc_retention: 0.80
    circuit_breaker_threshold: 3
    semantic_dedup_threshold: 0.50
    duplicate_ngram_threshold: 0.60
    budget_max_retries_per_stage: 3
    budget_max_rewritten_scenes: 15
    budget_max_defense_ratio: 0.30
    entity_guard_short_scene_words: 200
    entity_guard_short_scene_nouns: 1
  foreign_word_whitelist:
    - "khachapuri"
    - "amore mio"
    # Add project-specific words/phrases here
  mode: protect           # observe | protect | aggressive
  canary_enabled: true    # Pre-flight model check before run
```

### v6 Output Files

| File | Location | Purpose |
|------|----------|---------|
| `incidents.jsonl` | `{project}/incidents.jsonl` | Rollback events, circuit breaker trips, canary failures with failure_type categorization |
| `run_status.json` | `{project}/run_status.json` | Current run progress: last stage, completed stages, budget snapshot, incident count |
| `cleanup_morgue.jsonl` | `{project}/cleanup_morgue.jsonl` | Audit trail of all text deletions + salvage restores (auto-rotated at 5MB) |
