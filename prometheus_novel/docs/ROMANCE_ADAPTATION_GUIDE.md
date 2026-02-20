# Romance Adaptation Guide

How to adapt the WriterAI pipeline from mystery/thriller to romance without losing structural discipline. The same architecture works—the **metrics and escalation map** must be redesigned.

---

## What Transfers Perfectly

| Component | Thriller Use | Romance Use |
|-----------|--------------|-------------|
| Character Bible | Speech patterns, physical vocabulary, DO NOT lists | Same—distinct voices prevent flat dialogue |
| Truth File | Plot facts, what POV knows when | Emotional truths, backstory reveals, what each character believes |
| Power Shift Tracker | Who has leverage in investigation | Who has emotional leverage, who retreats, who misreads |
| Unresolved Threads Map | Plot questions, reveals | Emotional questions, vulnerability thresholds |
| Ending Type Tracker | Blackout / revelation / action | Emotional beat / touch milestone / confession / choice |
| Word Count Targets | Per-chapter pacing | Same—romance often needs *more* words (60–80k typical) |
| POV Enforcement | First/third, no pronoun slip | Same |
| Repetition Blacklist | Physical tics, sensory phrases | Same—emotional beats can repeat just like tics |

**All of that transfers. Romance benefits from discipline.**

---

## Info Gates → Emotional Gates

Same mechanism. Different content.

| Thriller Gate | Romance Gate |
|---------------|---------------|
| "Dr." withheld until Ch10 | Physical intimacy withheld until emotional trust threshold |
| Saboteur identity withheld | Backstory trauma withheld until midpoint |
| Evidence revealed in Act 3 | Public confession withheld until final act |

**Config concept:** `gating_type: "info"` vs `gating_type: "emotional"`. The pipeline uses this to decide what to withhold and when to allow reveals.

---

## Escalation Ladder: Danger vs Intimacy

### Thriller Escalation (current)

```
Environmental → Forensic → Psychological → Institutional
(habitat fails → evidence found → mind games → systems collapse)
```

### Romance Escalation (required)

```
Attraction → Tension → Emotional intimacy → Threat to relationship → Choice → Commitment
```

**Config concept:** `escalation_mode: "danger"` vs `escalation_mode: "intimacy"`. Outline generation and scene prompts use this to structure beats.

---

## Emotional Temperature Curve (Oscillation)

**Critical difference:** Thrillers escalate linearly. Romance does not.

Romance oscillates:

```
Attraction ↑
Retreat ↓
Intimacy ↑
Conflict ↓
Vulnerability ↑
Fear ↓
Black Moment ↓↓↓
Commitment ↑↑↑
```

Without oscillation, romance feels flat—constant forward pressure feels unnatural. The system must allow rise/retreat cycles, not just linear escalation.

**Config concept:**

```yaml
emotional_wave_pattern: oscillating   # oscillating | rising_only
```

**Per-chapter (reference_bible or outline):**

| Chapter | Temperature | Primary driver |
|---------|-------------|----------------|
| 1 | rise | Attraction |
| 2 | fall | Retreat / misread |
| 3 | rise | Micro-moment |
| 4 | fall | Conflict / obstacle |
| ... | ... | ... |
| N-1 | fall | Black moment |
| N | rise | Commitment / HEA |

Enforce thresholds (don't let three chapters in a row rise or fall). Don't micromanage—allow organic oscillation.

---

## Engine Swap: Mystery vs Chemistry

| Thriller Engine | Romance Engine |
|-----------------|----------------|
| "What's happening?" | "Will they choose each other?" |
| Logic reveals | Emotional reveals |
| Evidence stacking | Micro-moments, touches, subtext |
| Surveillance themes | Desire suppression, glances, misinterpretations |

**New layer:** Sensory-emotional tracking, not logic-reveal tracking.

---

## Romance-Specific Trackers (to add)

| Tracker | Purpose |
|---------|---------|
| **Emotional Breadcrumb Tracker** | What each character has revealed about their past/feelings. Gate premature vulnerability. |
| **Touch Progression Map** | First touch → hand-hold → kiss → intimacy. Enforce escalation, not regression. |
| **Vulnerability Index** | Per chapter: who is more exposed, who retreats, who misreads. |
| **Intimacy Gate Enforcement** | Physical intimacy only after emotional trust threshold. Config-driven. |
| **Conflict Authenticity Validator** | Third-act breakup must be earned. Misunderstandings must feel real, not contrived. |

---

## Tone Density

| Thriller | Romance |
|----------|---------|
| Compressed. Precise. Lean. | Breathing room. Interior longing. Slow burn. |
| 17–25k acceptable | 60–80k typical (contemporary); 80–100k (historical, epic) |
| Short chapters, oxygen-tight | Longer beats, room for subtext |

**Config concept:** `tone_density: "compressed"` vs `tone_density: "breathing_room"`. Affects target words per scene and chapter.

---

## Config Schema Additions (when implementing romance)

```yaml
# Genre mode — switches escalation and gating
genre_mode: romance   # thriller | romance | romantic_suspense

# Escalation type
escalation_mode: intimacy   # danger | intimacy (default from genre_mode)

# Gating type
gating_type: emotional   # info | emotional (default from genre_mode)

# Tone density
tone_density: breathing_room   # compressed | breathing_room (default from genre_mode)

# Romance-specific (only used when genre_mode: romance)
romance:
  intimacy_gate: midpoint    # when physical intimacy is allowed: first_kiss | midpoint | act3
  touch_progression: enforced   # track and enforce: touch -> hand -> kiss -> intimacy
  hea_required: true          # HEA/HFN expected; validate ending
  conflict_validator: true    # third-act breakup must be earned
  emotional_wave_pattern: oscillating   # oscillating (rise/fall cycles) | rising_only (linear)
```

---

## Romantic Suspense (hybrid)

For dark academia / romantic suspense where thriller instincts still apply:

```yaml
genre_mode: romantic_suspense
escalation_mode: hybrid   # both danger AND intimacy escalate in parallel
gating_type: both        # info gates (mystery) + emotional gates (relationship)
```

---

## Implementation Order

1. **Phase 1 (low effort):** Add `genre_mode`, `escalation_mode`, `gating_type`, `tone_density` to config schema. Default from `genre` field. Use in outline prompts to vary beat structure.
2. **Phase 2 (medium effort):** Add `romance` block. Implement touch progression tracking in ContinuityState (or equivalent). Add intimacy gate check to scene validation.
3. **Phase 3 (higher effort):** Emotional breadcrumb tracker, vulnerability index, conflict authenticity validator. These may require new state structures and validation passes.

---

## Risk: Over-Validation

> Romance readers are ruthless about: authentic emotional voice, chemistry realism, dialogue rhythm, interior longing.

**If you over-engineer mechanically, it'll feel synthetic.**

Romance dies if:
- Touch progression becomes checklisty.
- Emotional gates feel procedural.
- Conflict validator neuters messy arguments.
- Vulnerability index becomes robotic.

**The system must:** Enforce thresholds. **Not** micromanage chemistry.

Use the same bible/discipline architecture—swap the escalation math. Don't add so many validators that the prose loses heat.

---

## Quick Reference: Thriller vs Romance Defaults

| Setting | Thriller | Romance |
|---------|----------|---------|
| target_length | 18–60k | 60–80k |
| escalation_mode | danger | intimacy |
| gating_type | info | emotional |
| tone_density | compressed | breathing_room |
| chapter_ending_types | blackout, revelation, action | emotional beat, touch milestone, confession, choice |
| central_question | "What's happening?" | "Will they choose each other?" |

---

## Sample Romance config.yaml (minimal)

```yaml
# === IDENTITY ===
project_name: my-romance
title: "Second Chance at the Orchard"
genre: romance
target_length: "standard (60k)"
status: seeded

# === STORY CORE ===
premise: "A divorced baker returns to her family orchard to save it from bankruptcy—and confronts the ex she left behind."
protagonist: "Maya Chen, 38, pastry chef. Guarded, practical, carries guilt from the divorce."
antagonist: "The past / self-sabotage (external: the orchard's debt)"
central_conflict: "Maya must trust Jake again while the orchard's survival depends on them working together."
central_question: "Will they choose each other this time?"

# Genre mode (auto-derived from genre: romance, but can override)
# escalation_mode: intimacy
# gating_type: emotional
# tone_density: breathing_room

# Romance-specific (optional)
romance:
  intimacy_gate: midpoint
  hea_required: true

# === CONTENT ELEMENTS ===
writing_style: "close first-person present (Maya), dual POV alternating"
avoid: "instalove; third-act breakup without earned conflict; off-page resolution"
```

When `genre: romance`, the pipeline automatically sets `escalation_mode: intimacy`, `gating_type: emotional`, and `tone_density: breathing_room`. The outline and scene prompts receive the GENRE MODE block with intimacy ladder and emotional gating instructions.

---

## Sample Romance Config (copy into config.yaml)

```yaml
genre: romance
genre_mode: romance
target_length: "standard (60k)"

# Explicit overrides (optional — defaults derived from genre)
escalation_mode: intimacy
gating_type: emotional
tone_density: breathing_room

romance:
  intimacy_gate: midpoint
  touch_progression: enforced
  hea_required: true
  conflict_validator: true
```

---

## Sample Romance config.yaml Snippet

```yaml
genre: contemporary romance
genre_mode: romance   # optional; inferred from genre if omitted
target_length: "standard (60k)"
escalation_mode: intimacy
gating_type: emotional
tone_density: breathing_room

romance:
  intimacy_gate: midpoint    # first_kiss | midpoint | act3
  touch_progression: enforced
  hea_required: true
  conflict_validator: true

reference_bible:
  enabled: true
  inject_character_rules: true
  inject_emotional_gates: true   # future: emotional breadcrumb tracker
  inject_touch_progression: true # future: touch map
```

---

## Reference Bible: Romance Chapter Ending Types

When using `reference_bible.md` for romance, the Chapter Ending Variety Tracker should use:

| Chapter | Ending type | Description |
|---------|-------------|-------------|
| 1 | Attraction beat | First real look, spark, or friction |
| 2 | Tension | Misread, retreat, or obstacle |
| 3 | Micro-moment | Shared laugh, accidental touch, subtext |
| 4 | Vulnerability | One character drops guard |
| 5 | Stakes raise | External threat or internal conflict |
| ... | ... | ... |
| N-1 | Black moment | Breakup, betrayal, or choice point |
| N | Commitment | HEA/HFN—they choose each other |

Replace thriller endings (blackout, revelation, action) with emotional beats.

---

## Subgenre-Specific Escalation Ladders

The escalation ladder changes by subgenre. Choose one and align your reference_bible / outline accordingly.

| Subgenre | Escalation shape | Central tension |
|----------|------------------|----------------|
| **Clean contemporary** | Gentle oscillation, slower climb. First kiss often midpoint+. HEA soft. | Compatibility, timing, fear of commitment |
| **Second-chance adult** | High stakes from Ch1 (history). Oscillation between hope and regret. Trust rebuild. | "Will the same mistake happen again?" |
| **Dark academia** | Danger + intimacy in parallel. Threat escalates while relationship deepens. | Survival + "Can I trust you in the dark?" |
| **Romantic suspense** | Hybrid ladder. Info gates (who's the threat?) + emotional gates (when do they trust?). | Stakes from both mystery and relationship |

**Sweet spot for this engine:** Romantic suspense, dark academia, psychological intimacy with danger backdrop. The system naturally thinks in power, leverage, hidden motives, psychological mirroring—pure small-town slow-burn contemporary is possible but your engine loves stakes.
