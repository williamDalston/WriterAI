# Writing Rules: Built-In Coverage & Gap Analysis

This document answers: *Do we have solid writing rules baked in? Are we missing something that will leave the writing wanting?*

---

## 1. What’s Solid (Built-In)

### 1.1 Format & Output Control

| Layer | Location | Purpose |
|------|----------|---------|
| **FORMAT_CONTRACT** | pipeline.py ~2616 | Meta-text prevention: prose-only, no preamble, no commentary, stop sequences |
| **config.avoid** | Project config | Project-specific banned phrases (merged into scene drafting) |
| **surgical_replacements.yaml** | configs/ | ~40 patterns: AI tells, hollow intensifiers, stock metaphors, emotional summarization |

### 1.2 Scene Drafting

| Block | Content |
|-------|---------|
| **MASTER CRAFT PRINCIPLES** | Show vs tell, sensory weaving, transitions, internalization |
| **ABSOLUTE RESTRICTIONS** | Hardcoded bans: "couldn't help but", "found myself", "a sense of", stock metaphors, POV errors |
| **POV & VOICE** | First-person lock, correct "my" vs "her/his", explicit wrong/right examples |
| **DIALOGUE RULES** | Subject in tags ("I said" / "she said"), distinct voices, no therapeutic tone |
| **SCENE DIFFERENTIATION** | Different purpose/outcome from previous, differentiator, prev_opening injection |

### 1.3 Refinement & Polish

| Stage | Rules |
|-------|-------|
| **voice_human_pass** | HUMANIZATION_PRINCIPLES (8 rules): kill emotional summarization, one metaphor/para, concrete specificity, dialogue subtext, no looping, sentence rhythm, emotional unpredictability, end on concrete |
| **dialogue_polish** | HARD RULES + 8-point checklist (info-dump, subtext, voice diff, authentic speech, beats, tension, dialogue tells, bad tag blacklist) |
| **prose_polish** | PRESERVATION_CONSTRAINTS + rhetorical devices + 6-point checklist (word choice, structure, rhythm, precision, craft, opening/closing) |
| **chapter_hooks** | Romance-specific variant for genre; opening/ending focus |

### 1.4 Postprocess / Defense

| Mechanism | Role |
|-----------|------|
| **Emotional summary removal** | Paragraph-ending "felt like the beginning of something" type sentences |
| **POV enforcement** | Pronoun normalization, name-aware per-paragraph handling |
| **Semantic dedup** | Truncate restart loops within a scene |
| **final_deai** | Paragraph-window slicing with hook protection; surgical YAML replacements |
| **Scene turn repair** | Last 2 paragraphs must contain decision/revelation/action; end on action/dialogue, not reflection |

### 1.5 Repetition Controls

| System | Scope |
|--------|-------|
| **used_details_tracker** | Last 10 scenes: top 15 repeated 3–6 word phrases → injected into scene drafting |
| **Repetition blacklist** | Phrases in 3+ scenes across manuscript → injected into voice_human_pass |
| **phrase_suppressor / cliche_clusters** | Cross-manuscript phrase suppression and cluster repair |

---

## 2. Gaps & Potential Desired Rules

### 2.1 Likely Gaps

| Gap | Current State | Possible Addition |
|-----|---------------|-------------------|
| **Genre-specific prose rules** | Romance handled mostly at outline level; prose rules are generic | Add genre block: e.g. romance: "no instalove language", "slow burn = emotional resistance before surrender", "HEA stakes in subtext" |
| **Cross-chapter opening variety** | Only last scene's first 50 words passed | Track openings of last N chapters; inject "Do NOT echo these opening patterns: [list]" |
| **Scene-ending emotional summary** | Paragraph-level removal; scene turn repair prefers action/dialogue | Add check for scene-ending "and she knew everything had changed" style lines; expand scene turn repair to explicitly cut emotional-summary endings |
| **Exposition dumps in narrative** | Dialogue info-dump covered; "over the weeks they…" in blacklist | Explicit rule: no block of backstory/exposition; weave or cut |
| **First-page hook** | Chapter hooks stage exists; no special first-chapter rule | Optional: "First 250 words must hook; no slow atmospheric open" for Ch1 |
| **Tension curve enforcement** | Outline has tension_level; not clearly injected into prose | Inject "This scene: tension_level N. Maintain or escalate; do not deflate mid-scene." |

### 2.2 Lower-Priority Gaps

| Gap | Notes |
|-----|------|
| **Third-person drift** | "she wondered", "he felt" in first-person — POV rules are strong; could add these to PRESERVATION_CONSTRAINTS if slips occur |
| **Instalove / too-fast emotional movement** | Romance-specific; could live in strategic_guidance or genre block |
| **Over-explaining character motivation** | Partially covered by "show don't tell"; could add explicit "don't spell out why they did X" |
| **White-room dialogue** | Dialogue polish pushes physical beats; no hard rule that every exchange has at least one grounding detail |

---

## 3. Recommendations → IMPLEMENTED (2025-02)

### P0 (High Impact, Low Effort) — DONE

1. **Inject tension_level into scene drafting** ✓  
   - Maps tension to syntax: high (8+) → short punchy sentences, visceral only, no introspection; low (≤3) → room for introspection, complex rhythm; mid → balance.

2. **Extend scene turn repair (bow-tie killer)** ✓  
   - `_BOW_TIE_MARKERS` list: "knew that", "realized that", "felt like", "changed forever", etc.  
   - If last paragraph has bow-tie markers → always repair, regardless of turn signals.  
   - Custom prompt note for bow-tie repairs; validation accepts if new ending has no bow-tie.

3. **Chapter-opening variety** ✓  
   - `_get_chapter_openings_to_avoid()`: collects first ~30 words of last 3 chapters' first scenes.  
   - Injected into scene drafting as "OPENINGS TO AVOID ECHOING".  
   - Structure gate: for chapter-opening scenes, adds OPENING VARIETY CHECK to scoring prompt.

### P1 (Medium Impact) — DONE

4. **Genre prose block** ✓  
   - When `genre in ("romance", "contemporary romance", "rom-com")`: no instalove, slow burn, stakes in subtext.

5. **First-chapter hook rule** ✓  
   - For Ch1 Sc1: "Open with immediate engagement (action or dialogue). Hook in the first 100 words."

### P2 (Nice to Have) — DONE

6. **Exposition block rule** ✓  
   - In ABSOLUTE RESTRICTIONS: "Never dump backstory in a block. Weave or imply; reveal through conflict or dialogue."

7. **White-room guard** ✓  
   - In dialogue polish PHYSICAL BEATS: "Every dialogue exchange should include at least one grounding detail (setting, object, body) so it's not floating in a void."

---

## 4. Summary

**Yes, the system has solid, multi-layered writing rules:**

- Format control, scene drafting craft principles, POV and dialogue rules, voice humanization, dialogue and prose polish, chapter hooks, surgical de-AI, and repetition controls are all in place.

**All identified gaps have been implemented (P0, P1, P2):**

- Tension → syntax constraints  
- Bow-tie ending detection and repair  
- Chapter-opening variety (drafting + structure gate)  
- Romance genre prose block  
- First-chapter hook rule  
- Exposition block rule  
- White-room guard  

---

## 5. Layer 2: Cadence, Causality, Escalation, Specificity (2025-02)

### 5.1 Causality & micro-logic
- **Rule (drafting):** Every paragraph must have explicit causal link; connectors (And/But/Still/Then) must reference prior beat; no "somehow/suddenly/it hit me" without prior stimulus.
- **Check (quality_contract):** CAUSALITY warning for connector paragraphs without prior reference; VIBES_PHRASES detection.

### 5.2 Escalation integrity (no mid-scene sag)
- **Rule (drafting):** For tension ≥ 6: forbid 2+ purely reflective paragraphs; add threat/choice/revelation/friction.
- **Check (quality_contract):** Paragraph tagged ACTION/DIALOGUE/INTERNAL/DESCRIPTION; DEFLECTION warning if high-tension + 2+ reflective in a row.

### 5.3 Concrete specificity (anchor categories)
- **Rule (drafting):** Each scene ≥1 anchor from OBJECT, PLACE, SOCIAL, TIME, MONEY/LOGISTICS, BODY.
- **Check (quality_contract):** WALLPAPER_RISK if only BODY + ATMOSPHERE.

### 5.4 Dialogue compression / line economy
- **Rule (drafting):** For tension ≥ 6: 30–40% dialogue lines under 10 words; avoid 2+ commas + because/that/which.
- **Check (quality_contract):** DIALOGUE_EXPOSITORY warning for high-tension scenes.

### 5.5 Chapter opening move type
- **Rule (drafting):** *_get_chapter_openings_to_avoid* now includes move type (IN_MEDIAS_RES, DIALOGUE, SETTING, INTERNAL); never repeat same type 2 chapters in a row.
- **Check (quality_contract):** opening_move_history, opening_move_violations.

### 5.6 Rhythm variance
- **Rule (drafting):** ≥1 very short (≤6 words), ≥1 long (≥25 words); avoid 4+ consecutive in 12–18 word band.
- **Check (quality_contract):** RHYTHM_FLATLINE warning.

### 5.7 Quality Contract v1
- **Output:** `quality_contract.json` in project output dir.
- **Schema:** contracts (scene_id, tension_level, opening_move, edits, warnings), opening_move_history, opening_move_violations.
- **Wiring:** `_stage_quality_meters` calls `run_quality_contract`, merges into meter report, writes JSON.

---

## 6. Governance Maturity Assessment (2025-02)

The system now has four governance primitives that move it from "clever pipeline" to **editorial infrastructure**:

| Primitive | Module | Role |
|-----------|--------|------|
| **Eyes** | `delta_report.py` | Before/after diff counts per pass, per-scene hotspot flagging |
| **Leash** | `ceiling.py` | Max edits per scene, per 1k words, per family per chapter |
| **Brain** | `policy.py` | Genre presets (romance/thriller/literary/fantasy) + project overrides |
| **Self-awareness** | `loop_guard.py` | Cross-module collision detection, replacement feedback loop prevention |

### 6.1 What This Achieves

**Deterministic Editing Budget** — `ceiling.py` prevents over-editing good prose, infinite synonym churn, and LLM-style oscillation where phrases mutate forever. The system is stable across reruns; idempotence at zero diffs is verified.

**Genre-Aware Behavior Without Hardcoding** — `policy.py` + YAML means romance can allow warmth but cap melodrama, thriller can allow sharper verbs and shorter sentences, literary can allow metaphor density. Genre rules live in config, not code.

**Loop Guard = Editorial Safety Net** — Cross-module collision detection stops phrase_suppressor undoing emotion_diversifier, dialogue_trimmer fighting cliche repair, and infinite swap cycles. This is compiler-level safety for prose edits.

**Delta Reporting = Observability** — `quality_delta.json` gives before/after diff counts, per-pass impact, and evidence of diminishing returns. Measurable craft, not vibes.

### 6.2 Three-Layer Architecture

Most prose pipelines stop at repair. This system has all three:

| Layer | Status |
|-------|--------|
| **Generation** | Strong — FORMAT_CONTRACT, voice profiles, stop sequences, craft principles, tension-syntax mapping |
| **Repair** | Strong — micro-passes, structure gate, scene turn repair, final_deai, quality polish |
| **Governance** | Strong — ceilings, policy, loop guard, delta reports, quality contract |

### 6.3 Architectural Roles

The system now behaves as a full publishing stack in software form:

| Role | System Component |
|------|-----------------|
| **Writer** | Scene drafting with craft principles, voice profiles, tension constraints |
| **Editor** | Micro-passes, structure gate, voice_human_pass, dialogue/prose polish |
| **Managing Editor** | `policy.py` — applies genre policy, enables/disables passes |
| **Copy Chief** | `ceiling.py` — enforces editing budgets, prevents sandblasting |
| **Audit Department** | `delta_report.py` — before/after evidence, per-pass impact |
| **QA Department** | `quality_contract.py` + `quality_meters` — deterministic checks |
| **Safety Inspector** | `loop_guard.py` — cross-module collision prevention |

### 6.4 Next Frontier (Optional Evolutions)

These are not required for commercial fiction quality. The current infrastructure is already top-tier. These are the path from "excellent" to "formidably robust."

#### F1. Quality Scoring Feedback Loop
Turn delta metrics into a deterministic **scorecard** (no LLM):
- Phrase entropy
- Dialogue density variance
- Emotional mode diversity
- Verb specificity index
- Scene ending type distribution

Moves from pass/fail to **quantified craft improvement** ("Book improved 14% in lexical diversity, 22% in dialogue realism").

#### F2. Scene Function Classification
Macro repetition is the last big narrative risk. Light classifier for scene function:
- Reveal / Bond / Conflict / Decision / Aftermath / Pursuit

If two adjacent scenes share the same function + emotional mode + ending type, flag it. Prevents "three almost-kisses in a row" syndrome.

#### F3. Continuity Tripwires (Low Cost, High Trust)
Tiny checks, massive realism gain:
- Time of day drift
- Object possession drift
- Character presence drift
- Location transitions

Even simple noun/verb heuristics catch 80% of continuity wobble. Readers forgive prose; they don't forgive broken reality.

### 6.5 What Is NOT Needed

The system does **not** need:
- More LLM passes
- Heavier prompts
- More regex patterns
- Style transfer stages

The "AI voice" problem is already solved better than most published tools.
