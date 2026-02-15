# Pipeline Audit Guide: Full Breakdown of All Sections

> **Purpose:** Comprehensive reference for auditing each major area of the Prometheus Novel pipeline. Use this to ensure best results, identify improvement opportunities, and diagnose quality issues.

---

## Table of Contents

1. [High-Cascade Planning Stages](#1-high-cascade-planning-stages)
2. [Context Assembly](#2-context-assembly)
3. [Prose Generation Pipeline](#3-prose-generation-pipeline)
4. [Input Quality (Seed and Config)](#4-input-quality-seed-and-config)
5. [Defense-Related Configs](#5-defense-related-configs)
6. [Artifact Prevention Infrastructure](#6-artifact-prevention-infrastructure)
7. [Export and Validation](#7-export-and-validation)
8. [Token Economics & Context Pressure](#8-token-economics--context-pressure)
9. [State Persistence & Recovery](#9-state-persistence--recovery)
10. [Prompt Echo & Regurgitation Defense](#10-prompt-echo--regurgitation-defense)
11. [Planning Output Validators](#11-planning-output-validators)
12. [Drift Remediation & Calibration](#12-drift-remediation--calibration)
13. [Forensic Instrumentation](#13-forensic-instrumentation)
14. [Operational Runbook](#14-operational-runbook)
15. [Continuity as Data: Canonical Facts Ledger](#15-continuity-as-data-canonical-facts-ledger)
16. [Caching and Reuse Strategy](#16-caching-and-reuse-strategy)
17. [Async Reliability and Partial Failure Semantics](#17-async-reliability-and-partial-failure-semantics)
18. [Embeddings and Similarity Reproducibility](#18-embeddings-and-similarity-reproducibility)
19. [Copyright and Derivative Phrase Hygiene](#19-copyright-and-derivative-phrase-hygiene)
20. [Export Formatting QA and Layout Contracts](#20-export-formatting-qa-and-layout-contracts)
21. [Human-in-the-Loop Hooks](#21-human-in-the-loop-hooks)
22. [Experiment Harness for Prompt Iteration](#22-experiment-harness-for-prompt-iteration)

---

## 1. High-Cascade Planning Stages

These stages produce artifacts that feed many downstream stages. Quality here cascades through the entire pipeline.

### 1.1 high_concept

| Attribute | Value |
|-----------|-------|
| **Location** | `pipeline.py` ~3548 |
| **Documentation** | `docs/CONCEPT_GENERATION.md` |
| **Inputs** | Lighter context: synopsis, genre, protagonist, central_conflict, themes, tone, central_question (NOT full `_build_story_context()`) |
| **Output** | Single paragraph (validated, best-of-3 selected) |
| **Downstream** | world_building, beat_sheet, emotional_architecture, character_profiles, master_outline, trope_integration, motif_embedding, chapter_hooks |
| **Model** | gpt (STAGE_MODELS) |
| **Temperature** | 0.65 (bumped from 0.4 — creative seed needs variety) |
| **Params** | max_tokens=500, system_prompt=HIGH_CONCEPT_SYSTEM_PROMPT, stop=PLANNING_STOP_SEQUENCES |
| **System Prompt** | Acquisitions editor persona — enforces specificity, bans generic phrasing |
| **State fields** | `high_concept_candidates` (all 3), `high_concept_fingerprint` (hash + keywords + entities) |

**Best-of-3 Ensemble:**
- 3 parallel LLM calls with different creative angles:
  - **Commercial:** Market hook, "what if" premise, genre promise
  - **Original:** Fresh twist, subverted expectation, uniqueness
  - **Emotional:** Protagonist's deepest fear/desire, emotional stakes first
- Genre-specific addendum injected for romance, thriller/mystery, speculative fiction, literary
- Each candidate validated by `validate_high_concept()`, scored 0–100
- Best passing candidate selected; all 3 stored in `state.high_concept_candidates`

**Validation (`validate_high_concept()` at ~312):**
1. Preamble stripping (3 regex patterns)
2. Length check (15–120 words)
3. Truncation detection (sentence-ending punctuation)
4. Multi-paragraph trim (keeps longest paragraph)
5. Generic phrase blacklist (18 phrases in `CONCEPT_GENERIC_PHRASES`)
6. Specificity check (protagonist first name must appear)
7. Synopsis restatement guard (bigram overlap > 50% = fail)

**Scoring:** Start at 100; deductions: too_short (-40), truncation (-20), missing_protagonist (-15), synopsis_restatement (-30), generic_phrases (-8 each), too_long (-10), preamble_stripped (-5). Pass threshold: score >= 50 AND not too_short.

**Fallback cascade:**
1. If all 3 candidates fail → strict retry (temperature 0.5, explicit anti-preamble instructions)
2. If strict retry fails → use best-scoring candidate regardless of pass/fail
3. If zero candidates produced → raise RuntimeError (stage failure)

**Fingerprint (`build_concept_fingerprint()` at ~404):**
- SHA256 hash (first 16 hex chars) for exact-match detection
- Keyword extraction: top 15 significant words (4+ chars, stopwords filtered)
- Entity extraction: capitalized non-sentence-starter words (COMMON_CAPS excluded)
- Stored in `state.high_concept_fingerprint`, persisted in pipeline_state.json

**Drift Detection (`check_concept_drift()` at ~445):**
- Compares downstream stage output against fingerprint keywords
- Threshold: < 30% keyword overlap = CONCEPT DRIFT warning
- Reports: keyword_overlap ratio, keywords_found/checked, missing_entities
- Wired into: `_stage_beat_sheet`, `_stage_master_outline`

> **Cascade warning:** high_concept is the root node of the planning DAG. A weak concept produces a weak beat_sheet no matter how good the beat_sheet stage logic is. Always audit high_concept *before* beat_sheet.

**Audit focus:** Candidate quality spread across angles, validation false-positive rate, drift threshold calibration, genre addendum coverage. See CONCEPT_GENERATION.md for improvement checklist.

---

### 1.2 world_building

| Attribute | Value |
|-----------|-------|
| **Location** | `pipeline.py` ~3744 |
| **Inputs** | story_context, high_concept, strategic_guidance, existing setting/rules/locations from config |
| **Output** | JSON object: setting, rules, locations, etc. |
| **Downstream** | beat_sheet, character_profiles, master_outline |
| **Model** | gemini |
| **Params** | temperature=0.4, json_mode=True |
| **Fallback** | Minimal mock with `"rules": ["Rule 1", "Rule 2"]` |

**Key prompt elements:**
- Setting (time, place, atmosphere, sensory)
- World rules (possibilities/impossibilities)
- Key locations (5–7)
- Social structure
- Culture/customs

**Audit focus:** Internal consistency, expansion of user-provided details, JSON schema stability.

---

### 1.3 beat_sheet

| Attribute | Value |
|-----------|-------|
| **Location** | `pipeline.py` ~3793 |
| **Inputs** | story_context, high_concept, world_bible, strategic_guidance, user beats (strategic_guidance.beat_sheet or key_plot_points) |
| **Output** | JSON array of beats with name, percentage, scene description, emotional beat, tropes |
| **Downstream** | emotional_architecture, master_outline |
| **Model** | gpt |
| **Params** | temperature=0.3, json_mode=True |
| **Structure** | Save the Cat / 4-act with percentage markers (0–25%, 25–50%, etc.) |
| **Drift check** | Post-generation `check_concept_drift()` against `high_concept_fingerprint`; logs WARNING if keyword overlap < 30% |

**Key prompt elements:**
- Full Save the Cat beat structure (Opening Image → Final Image)
- Target length for percentage calibration
- User-provided plot beats to incorporate

> **User beat integration gap:** When users provide beats via `strategic_guidance.beat_sheet`, it is unclear whether they *merge* with Save the Cat or *replace* it. If merged, conflict resolution between user beats and standard structure beats is not documented. Audit the prompt to confirm behavior and document it.

**Audit focus:** Beat completeness, percentage accuracy, emotional beat coverage, user beat integration, concept drift warnings, merge-vs-replace semantics.

---

### 1.4 emotional_architecture

| Attribute | Value |
|-----------|-------|
| **Location** | `pipeline.py` ~3870 |
| **Inputs** | high_concept, beat_sheet, protagonist, themes, central_question |
| **Output** | JSON: emotional_beats, peaks, troughs, rhythm_check, transformation_markers |
| **Downstream** | Stored in config["emotional_architecture"]; used by motif_embedding, master_outline |
| **Model** | claude |
| **Params** | max_tokens=2000, json_mode=True (no explicit temperature) |
| **Fallback** | `{"emotional_beats": [], "peaks": [], "troughs": []}` |

**Key prompt elements:**
- Emotional state per beat
- 5–7 emotional peaks (10/10 intensity)
- 3–4 troughs (rest points)
- Peak-rest-build-peak rhythm (max 3 high-intensity in a row)
- 4–5 transformation markers (shown behavior change)

> **Parameterization gap:** No explicit temperature passed. Claude client default applies, which may differ from what was intended. See §14.5 for client normalization checklist.

**Audit focus:** Peak/trough balance, transformation markers alignment with beats, rhythm compliance.

---

### 1.5 character_profiles

| Attribute | Value |
|-----------|-------|
| **Location** | `pipeline.py` ~3943 |
| **Inputs** | story_context, high_concept, world_bible, strategic_guidance, protagonist/antagonist/other_characters, dialogue_bank, cultural_notes |
| **Output** | JSON array of character objects |
| **Downstream** | master_outline, scene_drafting (full character list in prompt) |
| **Model** | claude |
| **Params** | json_mode=True (no explicit temperature) |
| **Fallback** | `[{"name": "Protagonist", "role": "protagonist"}, {"name": "Antagonist", "role": "antagonist"}]` |

**Required fields per character:** Name, Role, Physical Description, Personality, Backstory, Goals, Arc, Voice/Speech Patterns, Signature Behaviors, Relationships.

> **Parameterization gap:** No explicit temperature or max_tokens. See §14.5 for client normalization checklist.

**Audit focus:** Voice distinctiveness, arc clarity, dialogue pattern usability for scene drafting.

---

### 1.6 master_outline

| Attribute | Value |
|-----------|-------|
| **Location** | `pipeline.py` ~4002 |
| **Inputs** | story_context, high_concept, beat_sheet, characters (brief), strategic_guidance, motif_map, key_plot_points, subplots |
| **Output** | List of chapter objects, each with scenes array |
| **Downstream** | scene_drafting, continuity_audit, alignment check |
| **Model** | gpt |
| **Params** | Batched (5 chapters per batch), max_tokens=4096, json_mode=True |
| **Structure** | Each scene: scene, scene_name, pov, purpose, differentiator (REQUIRED), character_scene_goal, central_conflict, opening_hook, outcome, location, emotional_arc, tension_level, pacing, spice_level |
| **Drift check** | Post-generation `check_concept_drift()` on full outline JSON against `high_concept_fingerprint`; logs WARNING if keyword overlap < 30% |

**Critical prompt elements:**
- Mandatory plot points (key_plot_points) MUST appear, mapped to acts
- Inciting incident MUST be Ch1 or Ch2
- Scene differentiation: UNIQUE purpose, opening_hook, central_conflict per scene
- Structural caps: max 2 digital-interaction scenes per act, suspense threads introduce/escalate/resolve, opening hook variety, genre discipline
- Romance: no thriller/horror beats, tension from emotional stakes
- Location variety: max 3 scenes in cafes/coffee shops total

**Audit focus:** Plot point coverage, scene differentiation, genre discipline, structural cap compliance, JSON extraction robustness, concept drift warnings.

---

### 1.7 motif_embedding

| Attribute | Value |
|-----------|-------|
| **Location** | `pipeline.py` ~6435 |
| **Inputs** | themes, motifs, central_question, aesthetic_guide, beat_sheet, characters, emotional_architecture |
| **Output** | motif_map: motifs with meaning, evolution, scene_mechanics, key_beats, character_links; motif_collisions; central_question_arc |
| **Downstream** | master_outline (injects motif_map into outline prompt) |
| **Model** | claude |
| **Runs** | Before master_outline (planning parallel group 2 with character_profiles) |

**Audit focus:** Motif evolution across story, scene_mechanics usability for outline generation.

---

### 1.8 trope_integration

| Attribute | Value |
|-----------|-------|
| **Location** | `pipeline.py` ~4270 |
| **Inputs** | genre, market_positioning (strategic_guidance), master_outline |
| **Output** | trope_placement report; optionally applies outline_updates |
| **Downstream** | Modifies master_outline in place |
| **Model** | claude |
| **Params** | max_tokens=2000, json_mode=True |
| **Scope** | Romance/mafia genres use ROMANCE_TROPES; tropes matched from market_positioning |

**Audit focus:** Trope detection from config, required elements verification, outline update application.

---

## 2. Context Assembly

### 2.1 _build_story_context()

| Attribute | Value |
|-----------|-------|
| **Location** | `pipeline.py` ~3448 |
| **Used by** | world_building, beat_sheet, character_profiles, master_outline (NOTE: high_concept now uses lighter inline context) |

**Sections (config keys):**
- Core: title, genre, tone, target_length
- CORE IDEA: synopsis
- Characters: protagonist, antagonist, other_characters
- World: setting, world_rules, key_locations
- Plot: premise, central_conflict, key_plot_points, subplots
- Themes: themes, central_question, motifs
- Style: writing_style, influences, avoid

Empty sections are omitted. All non-empty values are concatenated.

> **Config typo risk:** No schema validation at project load (see §4.2). A typo like `protaganist` instead of `protagonist` silently produces an empty character section. The model never sees the character data and nobody knows until the output is bland.

**Audit focus:** Field completeness, ordering, redundancy with strategic_guidance.

---

### 2.2 _build_strategic_guidance()

| Attribute | Value |
|-----------|-------|
| **Location** | `pipeline.py` ~3510 |
| **Source** | config.strategic_guidance |
| **Sections** | market_positioning, beat_sheet, aesthetic_guide, tropes, dialogue_bank, cultural_notes, pacing_notes, commercial_notes |

Returns empty string if all values are empty.

> **Seeding gap:** Strategic guidance is not populated by the seed command (§4.1). Users who don't know to add it manually run planning stages without market positioning, aesthetic direction, cultural notes, or dialogue samples. A romance novel without `market_positioning` or `tropes` produces a generic beat sheet that misses reader expectations. The seed guided mode should at least *ask* about genre-specific guidance.

**Audit focus:** Overlap with story_context, completeness for genre-specific projects, seeding coverage.

---

### 2.3 _build_scene_context()

| Attribute | Value |
|-----------|-------|
| **Location** | `pipeline.py` ~4954 |
| **Used by** | scene_drafting, scene_expansion, self_refinement |
| **Allowed sections** | WRITING STYLE, TONE, AVOID, STORY STATE, PREVIOUS SCENE ENDING |

**Components:**
1. **Style constraints:** writing_style, tone, avoid (always)
2. **Story state:** `_build_story_state()` when scene_index > 0
3. **Previous scene tail:** last 2 paragraphs of last N scenes (default 2)
4. **Alignment warning:** `_check_alignment()` if triggered

**Context hygiene:** Single entry point; only current project state; schema validation via `_validate_context_schema()`; SHA256 hash logged at DEBUG.

> **Critical bypass:** Scene drafting (§3.2) does NOT use `_build_scene_context()` for the main block. It builds context inline, bypassing injection detection, context hashing, and alignment checks. Either refactor scene drafting to use this function, or duplicate the safety checks in the inline path.

**Audit focus:** Story state completeness, previous-scene window size, alignment check frequency, scene drafting bypass.

---

### 2.4 _build_story_state()

| Attribute | Value |
|-----------|-------|
| **Location** | `pipeline.py` ~5198 |
| **Purpose** | Fix "first meeting loop" and "hallucinated locations" by injecting what has ALREADY happened |

**Sections:**
1. STORY PROGRESS: scene N of total, chapter X of Y
2. COMPLETED CHAPTERS: outline-purposes only (not generated text)
3. CURRENT CHAPTER: scene-by-scene with DONE / WRITING NOW / upcoming
4. RECENT LOCATIONS + OVERUSED (pick different location if ≥3 uses)
5. NARRATIVE ARC: genre-specific (romance vs generic act structure)
6. CRITICAL CONTINUITY RULES: characters already met, no re-intro, etc.

**Uses outline data only** for reliability.

**Audit focus:** Romance vs generic arc accuracy, overused location threshold, completed-chapter compression for long novels.

---

### 2.5 _validate_context_schema()

| Attribute | Value |
|-----------|-------|
| **Location** | `pipeline.py` ~5020 |
| **Purpose** | Detect credential leaks, Python code, template placeholders, debug markers, prompt injection |

**Red flags:** api_key, secret, password, token; def/class/import; {{...}}; TODO/FIXME

**Injection detection (two-factor):**
- Injection phrases: "ignore previous instructions", "you are/act as", "system prompt", etc.
- Structural cues: system:, assistant:, ### instructions, [INST], etc.
- Both present → ERROR (high confidence)
- Phrase only → WARNING (may be villain dialogue)

**Audit focus:** False positive rate, coverage of injection patterns.

---

### 2.6 _check_alignment()

| Attribute | Value |
|-----------|-------|
| **Location** | `pipeline.py` ~5115 |
| **When** | Every `check_interval` scenes (default 5) |
| **Logic** | Compare last N scenes' content vs outline expected content; keyword overlap |

**Threshold:** <15% keyword overlap = ALIGNMENT WARNING injected into context.

**Method:** Bigram-style keyword extraction from outline (purpose, scene_name); stopwords filtered; recent scene words vs expected keywords.

**Audit focus:** 15% threshold suitability, check_interval, keyword extraction quality.

---

## 3. Prose Generation Pipeline

### 3.1 _generate_prose()

| Attribute | Value |
|-----------|-------|
| **Location** | `pipeline.py` ~4844 |
| **Used by** | scene_drafting, scene_expansion, self_refinement, continuity_fix, continuity_fix_2, voice_human_pass, dialogue_polish, chapter_hooks, prose_polish |

**Flow:**
1. Inject FORMAT_CONTRACT as system prompt
2. Add stop sequences (nonce sentinel + backups)
3. Generate
4. Critic gate: `_validate_scene_output()`
5. Record artifact metrics
6. If fixable issues: retry with issue-specific feedback (budget guard applies)
7. Score both outputs; keep better one
8. Postprocess (cleanup, POV, de-AI, tic limiting)
9. Prose integrity checksums (raw/clean hashes)

**Fixable issues:** preamble, truncation_marker, alternate_version, analysis_commentary, prompt_leak

**Budget guards:** max retries per stage (default 3), defense cost ratio.

**Audit focus:** Critic gate accuracy, retry effectiveness, postprocess completeness.

---

### 3.2 Scene Drafting Prompt Structure

| Attribute | Value |
|-----------|-------|
| **Location** | `pipeline.py` ~5384 |
| **Per-scene** | Inline f-string, ~200 lines |

**Sections:**
- MASTER CRAFT PRINCIPLES: show vs tell, sensory weaving, transitions, internalization
- WRITING REQUIREMENTS: style, tone, influences
- ABSOLUTE RESTRICTIONS: avoid list + hardcoded (couldn't help but, stock metaphors, etc.)
- SCENE DIFFERENTIATION: different from previous, prev opening words
- POV & VOICE: first person, POV character, common POV errors with examples
- DIALOGUE RULES: subject required, distinct voices
- SCENE PURPOSE, GOALS & CONFLICTS, STRUCTURE, CONNECTIONS
- SETTING & SENSORY, GROUNDING DETAIL
- CRAFT ELEMENTS, PACING & EMOTION, SPICE
- CHARACTERS IN SCENE (full JSON), CULTURAL AUTHENTICITY
- STORY STATE (`_build_story_state`)
- CONTINUITY (`_get_previous_scenes_context` → `previous_context`)
- USED DETAILS TRACKER (`_get_used_details_tracker`)
- TARGET LENGTH (words_per_scene)
- NOW WRITE (directives)

> **Context bypass (critical gap):** Scene drafting does NOT use `_build_scene_context()` for the main block. Story state and previous context are built separately via inline code. This means the carefully defended context assembly — schema validation (`_validate_context_schema`), alignment checking (`_check_alignment`), provenance hashing — is bypassed for the most important prose stage. Either refactor scene drafting to route through `_build_scene_context()`, or duplicate the safety checks in the inline path.

**Audit focus:** Prompt length vs model context, redundancy, missing genre-specific guidance, context bypass remediation.

---

### 3.3 Scene Expansion

| Attribute | Value |
|-----------|-------|
| **Location** | `pipeline.py` ~5500+ |
| **Purpose** | Expand short scenes to meet word target |
| **Uses** | `_generate_prose()` |
| **Model** | claude |

**Audit focus:** Expansion criteria (too-short threshold), preservation of original content, integration with scene differentiation.

---

### 3.4 _get_used_details_tracker()

| Attribute | Value |
|-----------|-------|
| **Location** | `pipeline.py` ~5335 |
| **Purpose** | Avoid repeating phrases across last 10 scenes |
| **Method** | 3–6 word ngrams; phrases in 2+ scenes → DO NOT REUSE list |
| **Exclusions** | "i was", "it was", "the way", "in the", etc. |
| **Limit** | Top 15 most repeated |

> **Window limitation:** For scenes 80+ in a long novel, 10 scenes back may miss a phrase from scene 5 that was last used in scene 30. Consider a tiered window: exact phrases from last 10 scenes, plus a "global hot list" of the 5 most-used phrases across the entire novel so far.

**Audit focus:** Ngram length, exclusion list completeness, 15-phrase limit, window adequacy for long novels.

---

## 4. Input Quality (Seed and Config)

### 4.1 Seed Command

| Attribute | Value |
|-----------|-------|
| **Location** | `interfaces/cli/seed.py` |
| **Modes** | Full (paste template), Guided (step-by-step), Minimal (one-liner + AI expand) |
| **Required** | IDEA only (`validate_seed`) |
| **Optional** | All TEMPLATE_SECTIONS (TITLE, GENRE, SETTING, PROTAGONIST, etc.) |

**Config mapping (create_project_from_seed):**
- IDEA → synopsis
- TITLE → title
- GENRE, TONE, TARGET_LENGTH, setting, world_rules, key_locations
- protagonist, antagonist, other_characters
- premise, central_conflict, key_plot_points, subplots
- themes, central_question, motifs
- writing_style, influences, avoid
- stage_model_map: high_concept, beat_sheet, write_scene, self_refine

**Validation:** `validate_seed()` — only checks IDEA present.

> **Strategic guidance not seeded:** `strategic_guidance` (market_positioning, aesthetic_guide, tropes, dialogue_bank, cultural_notes) is not populated by any seed mode. Users must add it manually. The guided mode should at least ask about genre-specific guidance, even if answers are optional. Without it, planning stages run without market positioning — a romance novel won't get trope-aware beats.

**Audit focus:** Expand missing sections with AI (optional step); validation strictness; strategic_guidance seeding gap.

---

### 4.2 Config Schema

| Attribute | Value |
|-----------|-------|
| **No formal schema** | Config is dict; keys used ad hoc throughout pipeline |
| **Defense config** | `config.defense.thresholds` overrides `_DEFAULT_DEFENSE_THRESHOLDS` |
| **Export config** | `config.export.validation_mode` (lenient/strict) |

> **No formal schema.** A project with a typo (`protaganist` instead of `protagonist`) silently produces an empty character section in `_build_story_context()`, and nobody knows until the output is bland. A load-time schema check with warnings for missing recommended fields would catch this.

**Minimum viable for pipeline:** synopsis or premise (high_concept); genre recommended. Seed guarantees synopsis from IDEA.

**Audit focus:** Document required vs optional keys; schema validation at project load; typo detection.

---

## 5. Defense-Related Configs

### 5.1 cleanup_patterns.yaml

| Attribute | Value |
|-----------|-------|
| **Location** | `configs/cleanup_patterns.yaml` |
| **Purpose** | Configurable patterns for scene content cleanup |

**Sections:**
- `inline_truncate_markers`: "the rest remains unchanged", etc.
- `inline_preamble_markers`: "certainly! here is", "here is the revised", etc.
- `regex_patterns`: meta_opening (certainly/sure/as requested + here is + revised/updated)
- `disabled_builtins`: List of pattern names to suppress (exact or substring)

**Available built-in names:** rest_unchanged, rest_unchanged_bracket, current_scene_header, visible_pct_marker, enhanced_scene_header, heres_revised, hook_instruction_bleed, writing_tips_bullets, scene_header_*, xml_tag_*, beat_sheet_physical/emotional/sensory

**Audit focus:** False positives in your genre; coverage of new artifact types.

---

### 5.2 surgical_replacements.yaml

| Attribute | Value |
|-----------|-------|
| **Location** | `configs/surgical_replacements.yaml` |
| **Purpose** | DE-AI stage phrase replacements |
| **Loaded** | Runtime; changes apply on next run |

**Categories:**
- ai_tell_phrases: "I couldn't help but notice" → "", "I found myself" → "I", etc.
- hollow_intensifiers: " incredibly " → " ", etc.
- stock_metaphors: "a whirlwind of emotions" → "confusion", etc.
- emotional_summarization: "This wasn't just about" → "", etc.

**Audit focus:** Over-aggressive replacements; missing phrases for your genre.

---

### 5.3 defense.thresholds (config.yaml)

| Attribute | Value |
|-----------|-------|
| **Location** | `config.yaml` → `defense.thresholds` |
| **Defaults** | `_DEFAULT_DEFENSE_THRESHOLDS` in pipeline.py |

**Key thresholds:**

| Key | Default | Purpose |
|-----|---------|---------|
| scene_count_drop_pct | 0.50 | Integrity check: scene count < X of original |
| prefix_corruption_pct | 0.30 | >X of scenes share first 100 chars |
| forbidden_marker_pct | 0.40 | >X of scenes contain meta-markers |
| salvage_min_words | 150 | Salvage warning |
| salvage_restore_ratio | 3.0 | Original/stripped ratio for restore |
| feedback_loop_max_scenes | 5 | Max scenes per feedback loop |
| feedback_loop_wc_retention | 0.80 | Min word count retention for LLM rewrite |
| budget_max_retries_per_stage | 3 | Max retries per stage |
| budget_max_rewritten_scenes | 15 | Max total rewritten in feedback loops |
| entity_guard_short_scene_words | 200 | Relaxed noun threshold for short scenes |
| entity_guard_short_scene_nouns | 1 | Min shared nouns for short scenes |

**Bounds:** Validated via `_THRESHOLD_BOUNDS`; clamped if out of range.

**Aggressive mode:** Multipliers tighten detection (see `_AGGRESSIVE_MULTIPLIERS`).

**Audit focus:** Default appropriateness for your hardware/budget; aggressive mode when quality is critical.

---

## 6. Artifact Prevention Infrastructure

These systems work together to prevent LLM artifacts (preambles, meta-text, truncation markers) from reaching the final manuscript.

### 6.1 FORMAT_CONTRACT

| Attribute | Value |
|-----------|-------|
| **Location** | `pipeline.py` ~2260 |
| **Type** | System prompt constant |
| **Used by** | `_generate_prose()` (all prose stages), `_stage_final_deai()` (direct injection) |

Negative/positive example prompt injected as `system_prompt` into every prose generation call. Bans: greetings, commentary, headings, bullet points, alternatives, truncation markers. Includes a per-run nonce sentinel (`<END_PROSE_{nonce}>`) that makes the stop token unpredictable.

---

### 6.2 CREATIVE_STOP_SEQUENCES

| Attribute | Value |
|-----------|-------|
| **Location** | `pipeline.py` ~2290 |
| **Count** | 12 stop tokens |
| **Used by** | `_generate_prose()`, `_stage_final_deai()` |
| **Client mapping** | OpenAI/Ollama: `stop=`, Anthropic: `stop_sequences=` |

Prevents meta-text from being generated (saves tokens vs post-hoc cleanup). First token replaced at runtime with nonce sentinel.

---

### 6.3 _validate_scene_output() (Critic Gate)

| Attribute | Value |
|-----------|-------|
| **Location** | `pipeline.py` ~4497 |
| **Called by** | `_generate_prose()` |
| **Purpose** | Validate raw LLM output BEFORE postprocessing |

**Checks:**
1. Empty output
2. Preamble detection (3 regex patterns)
3. REST_UNCHANGED truncation marker
4. Alternate version markers ("Option A", "Version 1")
5. Analysis commentary ("Changes made:", "Scanning for")
6. Minimum word count (50 words)
7. POV drift (third-person references to protagonist in first-person narrative)

**Returns:** `{"pass": bool, "issues": dict, "word_count": int}`

---

### 6.4 _generate_prose() Wrapper

| Attribute | Value |
|-----------|-------|
| **Location** | `pipeline.py` ~4844 |
| **Used by** | 10 prose stages |

**Full flow:** FORMAT_CONTRACT → stop sequences → generate → critic gate → artifact metrics → retry (if fixable) → score comparison → postprocess → integrity checksums.

**Fixable issues:** preamble, truncation_marker, alternate_version, analysis_commentary, prompt_leak. Retries use `STRICT_RETRY_PREFIX` with issue-specific feedback.

---

### 6.5 Artifact Metrics

| Attribute | Value |
|-----------|-------|
| **Location** | `_record_artifact_metrics()` at ~4658 |
| **Storage** | `state.artifact_metrics` (persisted in pipeline_state.json) |
| **Tracked** | preamble, truncation, alternate, analysis, pov_drift, retried (per stage, per scene) |
| **Summary** | `_log_artifact_summary()` logs per-stage totals at stage end |

---

### 6.6 Transaction Safety

| Attribute | Value |
|-----------|-------|
| **Location** | `_run_stage()` ~2974 |
| **Scope** | All stages in `PROSE_STAGES` |

`copy.deepcopy(self.state.scenes)` snapshot before prose stages. Restores on: exception, or scene count dropping below 50% of snapshot. Prevents catastrophic scene loss from a single bad stage.

---

### 6.7 High Concept Validation

| Attribute | Value |
|-----------|-------|
| **Location** | `validate_high_concept()` ~312, `build_concept_fingerprint()` ~404, `check_concept_drift()` ~445 |
| **Constants** | `CONCEPT_GENERIC_PHRASES` ~282, `PLANNING_STOP_SEQUENCES` ~293, `HIGH_CONCEPT_SYSTEM_PROMPT` ~299 |

See [Section 1.1 high_concept](#11-high_concept) for full details on the Best-of-3 ensemble, validation, fingerprinting, and drift detection.

**Audit focus:** Validation false-positive rate (especially specificity check for unusual name formats), drift threshold calibration (30% may be too aggressive for loosely-structured stories), generic phrase list completeness.

---

## 7. Export and Validation

### 7.1 G→Pipeline Feedback Loop

| Attribute | Value |
|-----------|-------|
| **Location** | `pipeline.py` ~7323 (`_validation_feedback_loop`) |
| **Called from** | `_stage_output_validation()` |
| **Purpose** | Validate scenes; auto-fix META_TEXT errors |

**Flow:**
1. `validate_project_scenes()` (scene_validator)
2. Collect scene indices with META_TEXT errors
3. Prioritize by error count, then by position (early chapters first)
4. Cap at `feedback_loop_max_scenes` (default 5)
5. For each: try postprocess first; if still meta-text, request LLM rewrite
6. Entity preservation: protagonist + shared nouns; word count retention ≥ feedback_loop_wc_retention
7. Budget guard: stop at `budget_max_rewritten_scenes` (default 15)

**Systemic flag:** If >5 scenes need fixes, log "SYSTEMIC: upstream stage likely failed".

> **Silent budget exhaustion:** If a project hits the `budget_max_rewritten_scenes` limit (15), the system stops fixing errors and logs a warning the user may miss. If later chapters have sudden quality drops, check whether this limit was hit.

**Audit focus:** META_TEXT detection coverage, entity preservation strictness, budget appropriateness, budget exhaustion visibility.

---

### 7.2 output_validation Stage

| Attribute | Value |
|-----------|-------|
| **Location** | `pipeline.py` ~7481 |
| **Purpose** | Final stats, quality score, feedback loop, save |

**Steps:**
1. Word count, chapter count, targets
2. Sample validation: 3 scenes (beginning, middle, end) rated by LLM on prose, voice, pacing, sensory, hook, genre_fit
3. quality_score = overall/10; passed = overall≥6 and word_percentage≥80
4. `_validation_feedback_loop()` → fix META_TEXT
5. Flush morgue, incidents, persist artifact metrics
6. Save markdown, pipeline state

> **Sampling limitation:** 3 scenes out of a 90-scene novel is a 3% sample rate. If quality issues cluster (e.g., act 2 sags while act 1 and 3 are fine), beginning/middle/end sampling could miss it entirely. Consider sampling 1 per act, or weighting samples toward scenes flagged by freshness or alignment checks.

**Audit focus:** Quality scoring rubric, sample selection, pass/fail thresholds, sample representativeness.

---

### 7.3 scene_validator (Pre-Export)

| Attribute | Value |
|-----------|-------|
| **Location** | `export/scene_validator.py` |
| **Called from** | docx_exporter._validate_scenes(), _validation_feedback_loop |
| **Mode** | config.export.validation_mode (lenient/strict) |

**Detects:**
- META_TEXT: certainly_preamble, here_is_revised, below_is_updated, as_requested, sure_preamble, rest_unchanged, i_can_help, let_me_know
- SUSPECT_NAME: unknown character name (warning)
- SUSPECT_NAME_RECURRING: ≥3 scenes (error)
- Genre cross-contamination: only when config.market.tone_constraints opts in

**Strict mode:** Raise on errors, block export.

**Lenient mode:** Log only, allow export.

**Audit focus:** META_TEXT pattern coverage, name extraction from config, tone_constraints usage.

---

### 7.4 Pre-Export Validation (docx_exporter)

| Attribute | Value |
|-----------|-------|
| **Location** | `export/docx_exporter.py` ~266 |
| **Method** | `_validate_scenes()` |
| **Behavior** | Runs scene_validator; in strict mode, raises on validation errors |

**Audit focus:** Validation vs export ordering; user feedback when blocked.

---

## 8. Token Economics & Context Pressure

> In long-form generation, context windows fill up. If context grows linearly with chapter count, model recall degrades, latency spikes, or the call fails on token limits. These are the silent killers.

### 8.1 Context Pruning Strategy

| Attribute | Value |
|-----------|-------|
| **Previous scenes** | `_get_previous_scenes_context()` at ~5087: last 2 paragraphs of last N scenes (default N=2), hard-truncated to 500 chars if ending is too long |
| **Story state** | `_build_story_state()` at ~5198: structured recap of completed chapters (outline-only, not prose), current chapter progress, locations, relationships. Compresses chapter summaries when >10 chapters |
| **Used details tracker** | `_get_used_details_tracker()` at ~5335: 3-6 word ngrams from last 10 scenes, top 15 repeated phrases |
| **Truncation method** | Character-based (500 char max per ending), NOT token-based |

**Current state:** Context pruning is heuristic — character and paragraph limits, not token-counted. No global token budget per call.

**Audit focus:**
- **Context saturation:** Does the system summarize Chapter 1 before starting Chapter 15, or does it feed progressively more raw outline data? (Currently: outline-only summaries with compression after 10 chapters)
- **Token budget:** No hard cap on total context sent per call. The only limit is `max_tokens` for output (varies 200–4096 per stage). Risk: scene drafting prompts may exceed model context window for long novels.
- **Pruning logs:** Context schema hash logged at DEBUG level. No explicit log of what was dropped during pruning.
- **Recommendation:** Add token estimation before each call; log warning if estimated context > 80% of model window.

---

### 8.2 Cost-per-Stage Monitoring

| Attribute | Value |
|-----------|-------|
| **Location** | `cost_tracker.py` (CostTracker class) |
| **Pricing** | Model pricing table: OpenAI (gpt-4o, gpt-4o-mini), Anthropic (claude-sonnet, claude-haiku), Google (gemini-1.5-pro/flash), Ollama ($0) |
| **Granularity** | Per-call cost = (input_tokens / 1M) x input_rate + (output_tokens / 1M) x output_rate |
| **Storage** | `state.total_cost_usd`, `state.total_tokens`, per-stage in `state.stage_results[]` (stage_name, status, tokens_used, cost_usd) |
| **Logging** | `logger.info()` with cost breakdown per call |
| **Summary** | `get_summary()` returns total_input_tokens, total_output_tokens, total_cost_usd, calls_by_stage, cost_by_model |

**Audit focus:**
- **Vampire stages:** Identify stages consuming 80% of budget for 10% of value (common offenders: `continuity_audit`, `trope_integration`, large-batch `master_outline`).
- **Retry cost:** Multiply `retried_scenes` x `avg_scene_tokens` from artifact_metrics to compute critic gate overhead.
- **Ensemble cost:** High concept Best-of-3 triples the base cost. Monitor if strict retry (4th call) fires frequently.
- **Recommendation:** Add a "budget guard" that warns before starting scene_drafting if estimated remaining cost exceeds `config.budget_usd`.

---

### 8.3 Dry Run Cost Estimator

| Attribute | Value |
|-----------|-------|
| **Status** | NOT IMPLEMENTED |
| **Proposed logic** | Token count of (outline + characters + world) x num_scenes x avg_context_multiplier |

**Why it matters:** Prevent billing surprises before launching a 50-chapter run. Should be mandatory before the drafting phase.

**Audit focus:**
- Flag if average context-per-scene exceeds 20k tokens (expensive for larger models).
- Warn if total estimated cost exceeds `config.budget_usd`.

---

## 9. State Persistence & Recovery

> The pipeline *will* crash (API timeout, laptop sleep, unhandled exception). Recovery robustness determines whether users lose hours of work.

### 9.1 Save Mechanism

| Attribute | Value |
|-----------|-------|
| **Location** | `PipelineState.save()` at ~2464 |
| **Method** | Direct `json.dump()` to `pipeline_state.json` |
| **Atomicity** | **NOT ATOMIC** — no temp file, no `os.rename`, no file locking |
| **Frequency** | After each **stage** completion; also after snapshot restoration and stage failures |
| **NOT per-scene** | Scenes are only persisted when the enclosing stage completes |

**Risk:** A crash during `json.dump()` write produces a 0-byte or truncated file = total state loss.

**Audit focus:**
- **Corruption check:** Verify the code writes directly to the final file (it does). A write-replace pattern (`pipeline_state.json.tmp` → `os.rename`) would be safer.
- **Frequency gap:** Scene drafting may generate 30+ scenes before saving. A crash mid-stage loses all generated scenes since last checkpoint.
- **Recommendation:** Implement atomic write (temp file + rename). Optionally save after every N scenes (e.g., every 5) within long stages.

---

### 9.2 Resume Logic

| Attribute | Value |
|-----------|-------|
| **Location** | `_run_pipeline()` at ~2992; `completed_stages` list |
| **Granularity** | **Stage-level** — can resume from the first incomplete stage |
| **Mid-stage resume** | **NOT SUPPORTED** — if `scene_drafting` crashes on scene 5 of 20, it restarts the entire stage (but existing scenes from prior runs are preserved in state) |
| **Circuit breaker** | Halts after N consecutive failures + snapshot restores |
| **Parallel groups** | Correctly handles parallel stage groups; can resume within a group |

**Audit focus:**
- **Partial stage recovery:** Scene drafting is the longest stage. Recommend tracking `completed_scene_indices` within the stage so resume skips already-generated scenes.
- **Config drift on resume:** If `config.yaml` is changed between runs and the user resumes, the pipeline uses the **new** config. No drift warning between saved state's config and current config.
- **Recommendation:** On resume, hash the config and compare with the saved hash. Warn on drift. Optionally store config snapshot in state.

---

## 10. Prompt Echo & Regurgitation Defense

> A common LLM failure mode: rewriting prompt instructions back as prose instead of writing the story. ("The scene opens with high tension as requested, showing sensory details...")

### 10.1 Input-Output Similarity Check

| Attribute | Value |
|-----------|-------|
| **Existing defense** | `_validate_scene_output()` checks for analysis commentary ("Changes made:", "Scanning for") |
| **Existing defense** | `_clean_scene_content()` strips 40+ known preamble/instruction echo patterns |
| **Existing defense** | `_validate_context_schema()` detects prompt injection scaffolding in context |
| **Existing defense** | `validate_high_concept()` checks synopsis restatement via bigram overlap |

**Gap:** No generic N-gram overlap check between the full prompt text and the generated output. A scene that subtly echoes craft instructions ("She showed rather than told her emotions, weaving sensory details...") may slip through.

**Audit focus:**
- **Instruction bleed:** Check if output contains phrases from FORMAT_CONTRACT, MASTER CRAFT PRINCIPLES, or scene drafting instructions ("Show, Don't Tell", "sensory details", "unique opening hook").
- **Synopsis leaks:** In high_concept, the bigram overlap guard catches direct restatement. Confirm downstream stages (beat_sheet, master_outline) don't simply regurgitate the synopsis as beat descriptions.
- **Prompt echo in prompt_bleed detector:** `_validate_scene_output()` has a `prompt_leak` check at ~4211 that detects FORMAT_CONTRACT fragments in prose output. Verify coverage.

---

### 10.2 Instruction Bleed Detection

| Attribute | Value |
|-----------|-------|
| **Location** | `_validate_scene_output()` prompt_leak check at ~4211 |
| **Logic** | Scans prose for FORMAT_CONTRACT instruction fragments |
| **Scope** | Prose stages only (via `_generate_prose()`) |

**Not covered:**
- Planning stage outputs (beat_sheet, outline) echoing prompt structure
- Scene drafting echoing MASTER CRAFT PRINCIPLES as prose
- Dialogue echoing DIALOGUE RULES instructions

**Recommendation:** Add a lightweight instruction-echo detector: extract 5-word ngrams from the prompt, check if >N appear verbatim in the output. Log as WARNING, not as reject (to avoid false positives on common phrases).

---

## 11. Planning Output Validators

> Planning stages produce JSON artifacts that cascade through the entire pipeline. Currently, malformed planning output propagates silently — the pipeline uses fallback mocks but doesn't flag the degradation. Apply the same "critic gate" philosophy to planning that prose already has.

### 11.1 Definition of Done per Artifact

These are the validation checks each planning artifact should pass before being accepted. Items marked **[EXISTS]** are currently implemented; **[MISSING]** are recommended additions.

**high_concept:**
- [EXISTS] Validated by `validate_high_concept()`: preamble, length, truncation, generic phrases, specificity, synopsis restatement
- [EXISTS] Scored 0-100; must pass >= 50
- [EXISTS] Best-of-3 selection with fallback cascade

**world_building:**
- [EXISTS] Fallback mock if JSON parse fails
- [MISSING] Required keys validation: `setting`, `rules`, `locations` must be present and non-empty
- [MISSING] Locations count check: 5-7 expected (per prompt), flag if < 3 or > 12
- [MISSING] Placeholder detection: reject if any value is literally "Rule 1", "Location 1"

**beat_sheet:**
- [EXISTS] Fallback mock if JSON parse fails
- [EXISTS] Concept drift check post-generation
- [MISSING] Required beat names: Opening Image, Catalyst, Midpoint, All Is Lost, Finale must be present
- [MISSING] Percentage monotonicity: beat percentages must be in ascending order
- [MISSING] Beat count check: expect 12-16 beats for standard structure

**character_profiles:**
- [EXISTS] Fallback mock if JSON parse fails
- [MISSING] Required fields per character: name, role, arc, voice (at minimum)
- [MISSING] Voice uniqueness: compare dialogue_bank/speech_patterns across characters; flag if >80% token overlap
- [MISSING] Protagonist presence: ensure at least one character with role="protagonist"

**master_outline:**
- [EXISTS] Scene key normalization (multiple key names accepted)
- [EXISTS] Flat-scene grouping fallback for local models
- [EXISTS] Concept drift check post-generation
- [MISSING] Required scene keys: `differentiator`, `opening_hook`, `central_conflict` must be non-empty
- [MISSING] Opening hook variety: flag if >2 consecutive chapters start with same hook type
- [MISSING] Location cap enforcement: flag if >3 scenes in cafes/coffee shops
- [MISSING] Thread tracking: verify every introduced `thread` has at least one `resolve`

---

### 11.2 JSON Repair Policy

| Attribute | Value |
|-----------|-------|
| **Primary** | `extract_json_robust()` at ~1978: 7-step repair pipeline |
| **Secondary** | `_extract_complete_json_objects()` at ~2056: balanced-brace extraction |
| **Tertiary** | `_repair_truncated_json()` at ~4243: closing-bracket suffix attempts |
| **Final fallback** | Return raw text wrapped as `{"raw": text}` or `[{"raw": text}]` |

**7-step repair pipeline:**
1. Remove `//` and `/* */` comments
2. Fix Python-style booleans: `True`→`true`, `False`→`false`, `None`→`null`
3. Remove trailing commas before `}` or `]`
4. Fix unquoted keys: `word:` → `"word":`
5. ~~Single-quote conversion~~ **DISABLED** — was corrupting apostrophes in English text (can't → can"t)
6. Fix literal newlines/tabs inside JSON strings (character-by-character escape)
7. Fix decimal without leading zero: `.5` → `0.5`

**Closing bracket suffixes tried:** `]}]`, `}]}]`, `"]}]`, `"}]}]`, `"}}]`, `"]`, `}]`, `}}]`, `}]}]`

**Audit focus:**
- Step 5 is disabled for good reason — verify it stays disabled.
- Monitor `_repair_json_string` invocation rate (high rate = model consistently produces bad JSON = prompt issue).
- Track how often the "final fallback" (raw text wrap) triggers — this means total parse failure.

---

## 12. Drift Remediation & Calibration

> Detection without response is just expensive logging. When drift is detected, the pipeline should self-correct.

### 12.1 Drift Response Strategy

| Attribute | Value |
|-----------|-------|
| **Current state** | `check_concept_drift()` logs WARNING in beat_sheet and master_outline |
| **Response** | **NONE** — drift is detected but not acted upon |

**Recommended remediation path:**
1. **Anchor injection:** When drift triggers, inject a "NON-NEGOTIABLE ANCHORS" block into the next stage prompt containing the fingerprint keywords and entities.
2. **Temperature tightening:** Optionally reduce temperature by 0.05-0.1 for the drifted stage's next batch (e.g., master_outline batch 2 after batch 1 drifted).
3. **Re-anchor checkpoint:** After master_outline completes with drift warning, compare each chapter's scenes against the fingerprint. Flag specific chapters that drifted most.

**Audit focus:** Drift remediation should be opt-in (config flag) to avoid over-constraining creative stages.

---

### 12.2 Synopsis Overlap Calibration

| Attribute | Value |
|-----------|-------|
| **Current rule** | Bigram overlap > 50% between synopsis and high concept = synopsis_restatement (-30 score) |
| **Risk** | One-sided threshold punishes good concepts that intentionally reuse signature phrasing |

**Recommended: two-sided band:**

| Overlap | Interpretation | Action |
|---------|---------------|--------|
| < 15% | Possible hallucination / tangent | WARN: concept may have drifted from synopsis |
| 15-50% | Healthy distillation | PASS |
| > 50% | Paraphrase / restatement | PENALIZE (-30) |

**Audit focus:** Monitor false positive rate. If quality concepts are being penalized for legitimate phrasing reuse, widen the band or reduce the penalty.

---

### 12.3 Specificity Check Edge Cases

The protagonist name specificity check (`validate_high_concept()`) has known edge cases:

| Case | Example | Current behavior | Recommended |
|------|---------|-----------------|-------------|
| Single-name protagonist | "Zara" | Works correctly | OK |
| No first name | "The Girl", "Number Seven" | Always fails specificity | Allow config override: `protagonist_alias` |
| Multi-part names | "María de los Santos" | Checks "María" only | OK (first-word extraction) |
| Nickname vs formal | Config says "Elizabeth", concept uses "Liz" | Fails specificity | Allow aliases list in config |
| Non-Latin names with particles | "ibn Rashid", "van der Berg" | May check "ibn" / "van" | Filter common particles |

**Recommendation:** Add an optional `config.protagonist_aliases` list. If present, specificity check accepts any alias.

---

### 12.4 Ensemble Spread Metric

| Attribute | Value |
|-----------|-------|
| **Status** | NOT IMPLEMENTED |
| **Proposed** | Jaccard similarity on keywords between the 3 high concept candidates |

**Why it matters:** If all three candidates (commercial, original, emotional) produce near-identical text, the prompt is over-constraining or the model is stuck in a groove. A healthy ensemble has candidate Jaccard similarity < 0.6.

**Recommendation:** Compute pairwise keyword Jaccard between candidates. Log as INFO. If all pairs > 0.7, log WARNING "low ensemble diversity — consider widening angle prompts or raising temperature."

---

### 12.5 Downstream Anchoring (Beyond beat_sheet/master_outline)

Currently drift is checked in beat_sheet and master_outline. Additional stages that consume high_concept and could drift:

| Stage | Risk level | Recommendation |
|-------|-----------|---------------|
| emotional_architecture | Medium | WARN-level drift check on emotional_beats output |
| character_profiles | Medium | Check that protagonist arc keywords overlap with concept |
| motif_embedding | Low-Medium | Check that motif themes overlap with concept keywords |
| trope_integration | Low | Tropes should serve the concept, not redirect it |

**Audit focus:** Start with WARN-only checks; promote to remediation only if drift proves frequent.

---

## 13. Forensic Instrumentation

> When a scene goes wrong, you need to reproduce the exact system state at that moment without re-running the whole pipeline.

### 13.1 Prompt Snapshots

| Attribute | Value |
|-----------|-------|
| **Current state** | `prompt_loader.py` tracks metadata only: template name, version hash (SHA256), rendered length, stage, timestamp |
| **Gap** | **Actual prompt text is NOT saved.** Cannot replay a generation with the identical prompt. |

**What exists:**
- `_prompt_usage_log` in-memory list (lost on process exit)
- `get_prompt_usage_stats()` returns render counts, versions, stages per template

**What's missing:**
- Full rendered prompt text persistence (proposed: `debug/prompts/{stage}_{scene_id}_{timestamp}.txt`)
- Prompt hash per LLM call logged alongside response
- Model + temperature + stop sequences logged per call

**Audit focus:**
- When a scene is bad, can you prove whether it was "prompt changed" vs "model changed" vs "config changed"? Currently: no.
- **Recommendation:** Per-stage, persist: `prompt_hash`, `prompt_char_count`, `estimated_tokens`, `model`, `temperature`, `stop_sequences`. Optionally save full prompt text in debug mode.

---

### 13.2 Narrative Telemetry

| Attribute | Value |
|-----------|-------|
| **Status** | NOT IMPLEMENTED as a unified system |
| **Partial** | Word count per scene (exists), AI tell count (exists), artifact metrics per scene (exists) |

**Proposed per-scene metrics (stored in `state.scenes[i].meta`):**

| Metric | Purpose | Diagnostic |
|--------|---------|-----------|
| `dialogue_ratio` | % of scene that is dialogue | > 80% = "talking heads" (characters in white void) |
| `sentence_length_variance` | StdDev of sentence lengths | < 2.0 = monotonous rhythm |
| `adjective_density` | Adjectives / total words | > 15% = purple prose |
| `unique_word_ratio` | Unique words / total words | < 0.4 = repetitive vocabulary |
| `sensory_word_count` | Count of sensory words (taste, smell, texture, sound) | 0 = missing sensory grounding |
| `paragraph_count` | Number of paragraphs | Useful for pacing analysis |

**Audit focus:** These are cheap to compute (regex + counting, no LLM needed). Adding them to the state enables post-run quality heatmaps.

---

### 13.3 The Graveyard (Macro-Deletions)

| Attribute | Value |
|-----------|-------|
| **Existing** | `cleanup_morgue.jsonl` — micro-deletions (stripped preambles, meta-text fragments) |
| **Gap** | No log of **entire scenes** that were discarded during critic gate retry or feedback loop rewrite |

**Proposed:** `graveyard.jsonl` — triggered when:
- A scene is completely re-generated due to critic gate failure
- A scene is rewritten by `_validation_feedback_loop()`
- A scene is restored from snapshot (transaction safety rollback)

**Fields:** `timestamp`, `stage`, `scene_id`, `reason` (critic_gate_fail, feedback_rewrite, snapshot_restore), `original_text` (first 500 chars), `word_count`, `issues`

**Audit focus:**
- **Salvage:** Sometimes a "failed" scene contains a brilliant monologue. The graveyard preserves it for manual recovery.
- **Pattern detection:** If 5+ scenes are graveyard'd for "too_short", the expansion prompt is weak. If all are "preamble", the FORMAT_CONTRACT isn't reaching the model.

---

### 13.4 Unified Run Report

| Attribute | Value |
|-----------|-------|
| **Status** | NOT IMPLEMENTED as a single artifact |
| **Partial** | Cost summary (CostTracker), artifact metrics (state), validation report (output_validation), incidents (incidents.jsonl), morgue (cleanup_morgue.jsonl) |

**Proposed: `run_report.json`** — written at pipeline completion, consolidating:

```
{
  "run_id": "...",
  "timestamp": "...",
  "config_hash": "...",
  "stages_completed": [...],
  "high_concept": {
    "selected": {"angle": "emotional", "score": 92, "text": "..."},
    "candidates": [{"angle": "...", "score": ..., "issues": {...}}, ...],
    "fingerprint": {"hash": "...", "keywords": [...], "entities": [...]}
  },
  "drift_checks": {
    "beat_sheet": {"drifted": false, "keyword_overlap": 0.73},
    "master_outline": {"drifted": false, "keyword_overlap": 0.60}
  },
  "artifact_metrics": {"total_scenes_generated": 30, "scenes_with_preamble": 2, ...},
  "cost": {"total_usd": 1.47, "by_stage": {...}, "by_model": {...}},
  "fallbacks_used": ["world_building_mock", "strict_retry_high_concept"],
  "warnings": ["CONCEPT DRIFT in master_outline batch 3"],
  "quality_score": 7.2,
  "word_count": {"actual": 62340, "target": 60000, "percentage": 103.9}
}
```

**Audit focus:** This is the "flight recorder." When something's off, open one file and see the whole story.

---

## 14. Operational Runbook

### 14.1 Failure Taxonomy

Use this severity rubric consistently across all stages and logs:

| Severity | Meaning | Action | Examples |
|----------|---------|--------|----------|
| **ERROR** | Blocks pipeline progress | Stage fails, retry or abort | Invalid JSON after all repair attempts, empty LLM response, zero scenes generated, missing required config keys |
| **WARN** | Degrades quality silently | Log + continue, review post-run | Drift detected, fallback mock used, low ensemble diversity, partial JSON repair, high artifact rate |
| **INFO** | Normal operational data | Log for analytics | Candidate scores, token usage, stage timing, cleanup morgue entries |

**Audit focus:** Review logs for WARN entries that should be ERROR (silent degradation that ruins output quality).

---

### 14.2 Common Failure Runbook

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `world_building` returns fallback mock | JSON parse failure; model returned prose instead of JSON | Check `json_mode=True` is reaching the client. For Ollama, verify model supports structured output. Lower temperature to 0.3 |
| `master_outline` empty | Batch JSON extraction failed for all batches | Check `extract_json_robust` logs. Verify model context window fits the outline prompt. Reduce BATCH_SIZE from 5 to 3 |
| Outline scenes missing `differentiator` | Model ignoring the required field | Add explicit JSON example in prompt showing the field. For local models, add `"differentiator": "REQUIRED"` to the schema |
| Artifact metrics spike (>20% preamble rate) | Stop sequences not reaching model, or FORMAT_CONTRACT dropped from prompt | Verify client passes `stop=` parameter. Check that `system_prompt` is being set (not overridden by another kwarg) |
| `CONCEPT DRIFT` warning in beat_sheet | Model generated beats that don't align with the high concept | Review the high concept itself — if it's too abstract, drift is expected. Consider tightening drift threshold or injecting concept anchors into beat_sheet prompt |
| High concept all-fail (strict retry triggered) | Prompt too constraining, or model can't produce specific-enough output | Lower specificity penalty. Check if protagonist name is extractable from config. Review generic phrase list for false positives |
| `scene_drafting` scenes all < 500 words | `words_per_scene` calculation too low, or model not respecting length | Check `target_length` and `scenes_per_chapter` config. Verify the word target appears in the prompt. Consider raising `max_tokens` |
| Resume produces duplicate content | Mid-stage crash; stage restarts but existing scenes aren't cleared | Verify `completed_stages` doesn't include the crashed stage. Check if scene_drafting clears `state.scenes` at start |
| Critic gate retry rate > 30% | FORMAT_CONTRACT not effective for this model | Check model-specific stop sequence support. Consider model-specific FORMAT_CONTRACT variants |
| Cost exceeds budget 3x | Retry storms, large context windows, expensive models on high-volume stages | Check artifact metrics for retry rate. Move bulk stages (scene_drafting) to cheaper models. Reduce context window |

---

### 14.3 Tuning Guide for New Thresholds

| Threshold | Default | Symptom: Too Tight | Symptom: Too Loose | Adjustment |
|-----------|---------|--------------------|--------------------|------------|
| Drift keyword overlap | 30% | Too many false drift warnings on loosely-structured stories | Genuine drift goes undetected | Raise to 25% (tighter) or 40% (looser). Widen keyword list (increase from 15 to 20) |
| Synopsis bigram overlap | 50% | Good concepts penalized for legitimate phrasing reuse | Concepts that copy-paste the synopsis pass | Lower to 40% (stricter) or raise to 60% (more permissive) |
| High concept word window | 15–120 | Punchy 2-sentence concepts fail `too_short` | Verbose 3-paragraph concepts pass | Lower min to 10 or raise max to 150 |
| Generic phrase penalty | -8 per phrase | Concepts with one common phrase get tanked | Generic concepts pass | Raise to -12 (stricter) or lower to -5 (more permissive) |
| Specificity (protagonist name) | -15 if missing | Names with particles/nicknames always fail | Protagonist not mentioned in concept | Add `protagonist_aliases` config. Lower penalty to -10 |
| Critic gate min words | 50 | Short stylistic scenes fail (flash-forward, epilogue) | Truncated scenes pass | Lower to 30 for specific stages, keep 50 for drafting |

---

### 14.4 Debug / Determinism Mode

| Setting | Normal | Debug Mode |
|---------|--------|------------|
| Temperature | Per-stage (0.2–0.85) | Reduce all by 0.1 (floor 0.1) |
| High concept ensemble | Best-of-3 parallel | Single call (commercial angle only) |
| Prompt snapshots | Metadata only | Full prompt text saved to `debug/prompts/` |
| Context hashing | SHA256 at DEBUG level | SHA256 at INFO level with char count |
| Artifact metrics | Per-stage summary | Per-scene detail |
| State save frequency | Per-stage | Per-scene (every 5) |
| JSON repair logging | Silent on success | Log every repair step |

> **Activation:** Proposed `config.debug_mode: true` flag. Gives reproducible runs for chasing weird failures.

---

### 14.5 Model Behavior Normalization Checklist

Verify across all supported LLM clients (OpenAI, Anthropic, Ollama, Gemini):

| Behavior | OpenAI | Anthropic | Ollama | Gemini |
|----------|--------|-----------|--------|--------|
| `stop` sequences parameter | `stop=` | `stop_sequences=` | `stop=` | Verify support |
| `system_prompt` support | Via `system` role message | Via `system` parameter | Via `system` in messages | Verify support |
| `json_mode` enforcement | `response_format: {"type": "json_object"}` | Not native; prompt-based | `format: json` | Verify support |
| Max output tokens | `max_tokens` | `max_tokens` | `max_tokens` (may be `num_predict`) | Verify param name |
| Temperature range | 0.0–2.0 | 0.0–1.0 | 0.0–2.0 | Verify range |
| Timeout handling | `asyncio.wait_for` | `asyncio.wait_for` | `asyncio.wait_for` | Verify support |

**Audit focus:** "Works on GPT, weird on Claude" whack-a-mole. Verify stop sequences actually stop generation (not just logged and ignored). Verify json_mode actually produces valid JSON (Ollama wraps arrays in objects).

---

## 15. Continuity as Data: Canonical Facts Ledger

`_build_story_state()` is descriptive. A structured facts ledger prevents subtle contradictions that survive prose cleanup.

### 15.1 Facts Ledger Design

| Attribute | Value |
|-----------|-------|
| **Status** | NOT IMPLEMENTED — proposed |
| **Purpose** | Prevent contradictions: re-introductions, location teleports, forgotten objects |

**Recommended ledger fields:**
- `relationships`: who knows who, current status (strangers/acquaintances/friends/lovers/enemies)
- `locations`: last seen location per character
- `objects`: important objects and who has them
- `promises`: vows, threats, deadlines
- `injuries`: physical state changes

**Audit checks:**
- Facts update only from outline + approved scene events
- Facts included in `_build_scene_context()` as a compact block
- Validator: no "re-introduction" of already-met characters

**Audit focus:** Ledger completeness, update trigger correctness, injection into context.

---

### 15.2 Continuity Regression Signals

**Recommended metrics:**
- `continuity_conflict_count` per chapter
- `reintroduced_character_count` — characters re-introduced after first meeting
- `location_teleport_count` — character changes location without transition scene

**Audit focus:** Metric collection points, threshold for pipeline warning vs halt.

---

## 16. Caching and Reuse Strategy

Planning stages are expensive. Re-running them unnecessarily introduces drift.

### 16.1 Planning Cache Policy

| Attribute | Value |
|-----------|-------|
| **Status** | NOT IMPLEMENTED — proposed |
| **Purpose** | Avoid recomputing expensive planning stages when inputs haven't changed |

**Cache keys based on:**
- `prompt_hash` (SHA256 of normalized prompt)
- `model_id`
- `temperature`
- `schema_version`

**Policy:**
- If story seed unchanged AND prompt hash unchanged → reuse high_concept / beat_sheet / world_bible
- Recompute only when inputs changed

**Audit checks:**
- Cached outputs are tagged with provenance and fingerprint
- Cache invalidation is explicit, not accidental (e.g., changing temperature invalidates)
- Cache hits are logged (to detect stale data)

**Audit focus:** Invalidation correctness, provenance tracking, stale cache detection.

---

## 17. Async Reliability and Partial Failure Semantics

Async pipelines fail in half-successful ways. Clean recovery requires explicit rules beyond the state persistence in §9.

### 17.1 Error Taxonomy

| Error Class | Retry? | Recovery |
|-------------|--------|----------|
| `NETWORK_FAIL` | Yes (exponential backoff) | Retry up to 3 times |
| `RATE_LIMIT` | Yes (respect Retry-After) | Backoff with jitter |
| `MODEL_UNAVAILABLE` | No | Fall back to alternate model or halt |
| `PARSER_FAIL` | Yes (with repair prompt) | JSON repair loop (§11.2) |
| `VALIDATION_FAIL` | Yes (with feedback) | Critic gate retry (§3.1) |

**Partial success rule:**
- Planning stages: can continue with fallback, but MUST log `DEGRADED_MODE`
- Prose stages: prefer rollback and halt if integrity checks trip

**Audit checks:**
- Per-stage timeouts + retry with exponential backoff (separate from content retries)
- Clean resume from last completed stage without re-running earlier stages unintentionally
- `completed_stages` list in pipeline_state.json accurately reflects only fully successful stages

**Audit focus:** Resume correctness, partial failure visibility, error classification coverage.

---

## 18. Embeddings and Similarity Reproducibility

Semantic dedup and freshness scoring depend on embeddings. The embedding model is a hidden dependency.

### 18.1 Embedding Model Tracking

| Attribute | Value |
|-----------|-------|
| **Current model** | all-MiniLM-L6-v2 (sentence-transformers) |
| **Used by** | ChromaDB vector store, semantic dedup, freshness scoring |

**Audit checks:**
- Record `embedding_model_id` + version in metrics
- If sentence-transformers is missing, fallback behavior is logged clearly (no silent downgrade)

**Deterministic fallback ordering:**
1. Embeddings cosine similarity
2. Bigram Jaccard similarity
3. Paragraph fingerprint (hash-based)

**Audit focus:** Model version pinning, fallback logging, similarity threshold stability across model versions.

---

## 19. Copyright and Derivative Phrase Hygiene

Not a moral panic — a practical risk reducer. Distinct from prompt echo defense (§10) which catches instruction bleed.

### 19.1 Influence Guard

| Attribute | Value |
|-----------|-------|
| **Purpose** | Ensure `influences` in config are treated as tonal constraints, not templates |

**Audit checks:**
- Prompts use "evoke the vibe of [influence]" not "write like [influence]"
- Lightweight detector for unusually long verbatim sequences repeated across scenes
- Optional: small blacklist of ultra-famous phrases (if desired)

**Audit focus:** Influence prompt language, verbatim sequence detection.

---

## 20. Export Formatting QA and Layout Contracts

Docx/PDF exports are the surprise boss fight.

### 20.1 Export Layout Contract

| Attribute | Value |
|-----------|-------|
| **Location** | `export/docx_exporter.py` |
| **Purpose** | Ensure consistent, professional formatting |

**Contract elements:**
- Scene separator style (consistent throughout)
- Chapter title formatting (font, size, spacing)
- Paragraph spacing rules
- Dialogue formatting preservation (quotes, em-dashes)
- Italics/bold preservation through cleanup pipeline

**Round-trip sanity test:**
1. Export docx
2. Re-read docx text
3. Compare paragraph count and word count within tolerance

**Audit focus:** Formatting preservation through postprocess pipeline, italics/quotes survival, export consistency.

---

## 21. Human-in-the-Loop Hooks

Even with automation, manual correction needs "one lever."

### 21.1 Checkpoint Pauses

Optional pause points for human review:
- After master_outline (structural approval before prose investment)
- After first drafted chapter (voice/style approval)
- Before final_deai (last chance to pin content)

### 21.2 Content Pinning

| Attribute | Value |
|-----------|-------|
| **Status** | NOT IMPLEMENTED — proposed |
| **Purpose** | Protect manually edited content from automated passes |

**Mechanisms:**
- "Pin this paragraph" — immune to de-AI/cleanup
- "Pin these facts" — facts ledger cannot override them

**Audit checks:**
- Manual edits preserved across reruns (hash-based "user edited" detection)
- Pinned content clearly marked in pipeline state

**Audit focus:** Pin mechanism reliability, rerun preservation, pin visibility in state.

---

## 22. Experiment Harness for Prompt Iteration

Rich defenses need a lab bench.

### 22.1 A/B Framework for Planning Prompts

| Attribute | Value |
|-----------|-------|
| **Status** | NOT IMPLEMENTED — proposed |
| **Purpose** | Compare prompt versions with metrics |

**Workflow:**
- `high_concept_prompt_v1`, `v2`, etc. (versioned prompt files)
- Compare with metrics: hook clarity, uniqueness, downstream outline variance
- Track which prompt version produced each run

### 22.2 Parameter Sweep Mode

Small grid over temperature/top_p for high_concept and beat_sheet:
- Pick best by rubric score + structural validation pass rate
- Store sweep results separately from production runs

**Audit checks:**
- Experiment outputs stored in isolation (not mixed with production runs)
- Sweep results include prompt hash, model ID, all params
- Winner selection criteria documented

**Audit focus:** Experiment isolation, reproducibility, winner selection rigor.

---

## Appendix A: Recommended Audit Order

| Priority | Area | Rationale |
|----------|------|-----------|
| 1 | high_concept + validation (§1.1, §6.7) | Root of planning DAG; Best-of-3 + fingerprint now defends it |
| 2 | beat_sheet (§1.3) | Structural backbone; feeds outline and emotional arc; has drift check |
| 3 | master_outline (§1.6) | Maps beats to scenes; scene differentiation critical; has drift check |
| 4 | _build_scene_context / story_state (§2.3, §2.4) | What each scene receives; prevents loops and drift |
| 5 | Scene drafting prompt (§3.2) | Longest prompt; context bypass gap; redundancy |
| 6 | Artifact prevention (§6.1–§6.6) | System-level defense across all prose stages |
| 7 | Planning output validators (§11) | Definition of Done for JSON artifacts; silent degradation prevention |
| 8 | Token economics (§8) | Context pressure, cost monitoring, budget guards |
| 9 | Config/seed validation (§4.1, §4.2) | Ensure solid inputs before pipeline runs |
| 10 | character_profiles (§1.5) | Voice and arc feed dialogue and prose |
| 11 | State persistence (§9) | Atomic writes, resume logic, crash recovery |
| 12 | Drift remediation (§12) | Detection without response is expensive logging |
| 13 | Validation feedback loop (§7.1) | Last line of defense for meta-text |
| 14 | Defense configs (§5.1–§5.3) | Tunable without code changes |
| 15 | Forensic instrumentation (§13) | Prompt snapshots, run report, graveyard |
| 16 | Async reliability (§17) | Prevents corrupted partial runs |

---

## Appendix B: Known Structural Issues

Issues identified during audit that should be resolved:

| Issue | Section | Severity | Description |
|-------|---------|----------|-------------|
| Scene drafting context bypass | §3.2 | **High** | Scene drafting builds context inline, bypassing `_build_scene_context()` safety checks (injection detection, alignment, provenance hashing) |
| Non-atomic state writes | §9.1 | **High** | `pipeline_state.json` written directly with no temp file + rename; crash during write = total state loss |
| Inconsistent parameterization | §14.5 | Medium | Some stages omit temperature/max_tokens, using silent client defaults that differ across providers |
| No config schema validation | §4.2 | Medium | Config typos silently produce empty fields; no load-time check |
| Strategic guidance not seeded | §2.2, §4.1 | Medium | Genre-critical guidance requires manual addition; seed guided mode doesn't ask |
| 3-scene quality sampling | §7.2 | Medium | 3% sample rate may miss clustered quality issues in acts |
| Silent budget exhaustion | §7.1 | Medium | `budget_max_rewritten_scenes` limit stops fixing errors with only a log warning |
| No prompt text persistence | §13.1 | Medium | Cannot replay a generation with the identical prompt; metadata only |
| Drift detected but not remediated | §12.1 | Medium | `check_concept_drift()` logs WARNING but takes no corrective action |
| No mid-stage resume | §9.2 | Medium | Scene drafting crash at scene 5/20 restarts entire stage |
| Used details tracker window | §3.4 | Low | 10-scene window insufficient for long novels; needs tiered/global hot list |
| User beat merge semantics | §1.3 | Low | Unclear if user beats merge with or replace Save the Cat structure |
| Pipeline.py monolith | — | Low (maintainability) | ~7000+ lines housing all layers; impedes isolated testing |

---

## Appendix C: Code Reference Map

| Component | File:Line |
|-----------|-----------|
| **Planning Stages** | |
| _stage_high_concept | pipeline.py ~3548 |
| _stage_world_building | pipeline.py ~3744 |
| _stage_beat_sheet | pipeline.py ~3793 |
| _stage_emotional_architecture | pipeline.py ~3870 |
| _stage_character_profiles | pipeline.py ~3943 |
| _stage_master_outline | pipeline.py ~4002 |
| _stage_trope_integration | pipeline.py ~4270 |
| _stage_motif_embedding | pipeline.py ~6435 |
| **Context Assembly** | |
| _build_story_context | pipeline.py ~3448 |
| _build_strategic_guidance | pipeline.py ~3510 |
| _build_scene_context | pipeline.py ~4954 |
| _build_story_state | pipeline.py ~5198 |
| _validate_context_schema | pipeline.py ~5020 |
| _check_alignment | pipeline.py ~5115 |
| _get_previous_scenes_context | pipeline.py ~5087 |
| _get_used_details_tracker | pipeline.py ~5335 |
| **Prose Generation** | |
| _generate_prose | pipeline.py ~4844 |
| _stage_scene_drafting | pipeline.py ~5384 |
| **Artifact Prevention** | |
| FORMAT_CONTRACT | pipeline.py ~2260 |
| CREATIVE_STOP_SEQUENCES | pipeline.py ~2290 |
| STRICT_RETRY_PREFIX | pipeline.py ~2304 |
| _validate_scene_output | pipeline.py ~4497 |
| _record_artifact_metrics | pipeline.py ~4658 |
| STAGE_TEMPERATURES | pipeline.py ~2634 |
| **High Concept Defense** | |
| CONCEPT_GENERIC_PHRASES | pipeline.py ~282 |
| PLANNING_STOP_SEQUENCES | pipeline.py ~293 |
| HIGH_CONCEPT_SYSTEM_PROMPT | pipeline.py ~299 |
| validate_high_concept | pipeline.py ~312 |
| build_concept_fingerprint | pipeline.py ~404 |
| check_concept_drift | pipeline.py ~445 |
| **State & Recovery** | |
| PipelineState.save | pipeline.py ~2464 |
| PipelineState.load | pipeline.py ~2502 |
| completed_stages (resume) | pipeline.py ~2992 |
| **Cost Tracking** | |
| CostTracker | cost_tracker.py |
| **JSON Repair** | |
| extract_json_robust | pipeline.py ~1978 |
| _repair_json_string | pipeline.py ~1924 |
| _extract_complete_json_objects | pipeline.py ~2056 |
| _repair_truncated_json | pipeline.py ~4243 |
| **Export & Validation** | |
| _validation_feedback_loop | pipeline.py ~7323 |
| _stage_output_validation | pipeline.py ~7481 |
| validate_seed | interfaces/cli/seed.py ~279 |
| create_project_from_seed | interfaces/cli/seed.py ~539 |
| validate_project_scenes | export/scene_validator.py |
| **Config Files** | |
| cleanup_patterns | configs/cleanup_patterns.yaml |
| surgical_replacements | configs/surgical_replacements.yaml |
| DEFAULT_DEFENSE_THRESHOLDS | pipeline.py ~2634 |
| **Logging & Forensics** | |
| _cleanup_morgue | pipeline.py ~393 |
| _incident_buffer | pipeline.py ~437 |
| _flush_morgue | pipeline.py ~409 |
| _flush_incidents | pipeline.py ~477 |
| prompt_loader usage log | prometheus_lib/utils/prompt_loader.py |

---

## Appendix D: Regression Suite Guidance

### Golden Seed Configs

Maintain 3-5 canonical project configs for regression testing:

| Config | Genre | Purpose |
|--------|-------|---------|
| `burning-vows` | Romance | Full strategic guidance, rich config, tests genre-specific tropes |
| (proposed) `steel-horizon` | Sci-fi/Thriller | Tests speculative fiction genre addendum, ticking clock, world-building depth |
| (proposed) `quiet-rooms` | Literary fiction | Tests emotional architecture depth, minimal plot, voice-driven |
| (proposed) `minimal-seed` | Unspecified | Tests graceful degradation with minimal config (synopsis only) |

### Regression Metrics to Track

| Metric | Baseline | Regression = |
|--------|----------|-------------|
| High concept score (best candidate) | >= 75 | < 60 for 2+ configs |
| High concept ensemble diversity (Jaccard) | < 0.6 | > 0.8 (all candidates identical) |
| Drift overlap in beat_sheet | > 0.5 | < 0.3 (concept lost) |
| Drift overlap in master_outline | > 0.4 | < 0.25 (concept lost) |
| Artifact rate (preamble per 10k words) | < 2% | > 5% |
| Strict retry frequency (high concept) | < 20% of runs | > 50% |
| Fallback mock frequency (any planning stage) | < 5% | > 15% |
| Export pass rate (strict mode) | > 90% | < 75% |
| Cost per 60k-word novel (GPT-4o) | ~$3-5 | > $10 (retry storm) |

---

## Appendix E: Template Versioning

Even with inline prompts, track prompt versions for change management:

| Prompt | Current Version | Last Changed |
|--------|----------------|-------------|
| HIGH_CONCEPT_SYSTEM_PROMPT | v2026-02-14a | Best-of-3 ensemble + validation |
| FORMAT_CONTRACT | v2026-02-14a | Nonce sentinel, negative/positive examples |
| STRICT_RETRY_PREFIX | v2026-02-14a | Issue-specific retry feedback |
| Scene drafting (inline) | v2026-02-14a | Story state + used details tracker |
| Master outline (inline) | v2026-02-14a | Structural caps, genre discipline, thread tracking |

**Recommendation:** Add a `PROMPT_VERSIONS` dict constant in pipeline.py mapping prompt names to version strings. Log at pipeline start. When a regression appears, diff the versions to isolate whether a prompt change caused it.

Maintain `docs/CHANGELOG_PROMPTS.md` with 1-line diffs per change.
