# Romance Genre Preparation Guide

When switching from mystery/thriller to romance, the **architecture transfers** but the **metrics and escalation map** must be redesigned. This doc captures what to reuse, what to adapt, and what to add.

---

## What Transfers Perfectly

| Component | Thriller Use | Romance Use |
|-----------|--------------|-------------|
| **Character Bible** | Speech patterns, physical vocabulary, DO NOT | Same — plus romantic lead chemistry notes |
| **Truth File** | Plot secrets, what POV knows | Backstory trauma, what each lead has confessed |
| **Power Shift Tracker** | Who has leverage over whom | Who has emotional leverage, who retreats, who misreads |
| **Unresolved Threads** | Mystery threads | Emotional threads (trust, vulnerability, confession) |
| **Ending Type Tracker** | Per-chapter ending diversity | Same — romance needs varied chapter endings too |
| **Word Count Targets** | Per-chapter targets | Romance often 60–80k; slow burn needs breathing room |
| **POV Enforcement** | First/third, pronoun rules | Same |
| **Repetition Blacklist** | Physical tics, sensory phrases | Same — plus romance-specific (overused longing phrases) |
| **Protagonist Competence** | Limits (Elena can't do forensics) | Limits (lead can't fix other's trauma solo) |

---

## Info Gates → Emotional Gates

**Same mechanism. Different content.**

| Thriller Gate | Romance Gate | When to Release |
|---------------|--------------|-----------------|
| "Dr." identity withheld | Physical intimacy | After emotional trust threshold |
| Who sabotaged it | Backstory trauma | Midpoint or later |
| Culprit reveal | Public confession / "I love you" | Final act |
| Evidence chain | Touch progression | Escalation ladder (see below) |

**Config hook:** `gate_type: "info"` (thriller) vs `gate_type: "emotional"` (romance). Pipeline uses this to select gate semantics in prompts and continuity state.

---

## Escalation Ladder Swap

### Thriller Escalation (current)
Environmental → Forensic → Psychological → Institutional

### Romance Escalation (target)
1. **Attraction** — Awareness, glances, subtext, desire suppression  
2. **Tension** — Proximity, near-misses, misinterpretations  
3. **Emotional intimacy** — Vulnerability, shared secrets, trust  
4. **Threat to relationship** — Misunderstanding, external pressure, internal wound  
5. **Choice** — Stay or leave, risk or retreat  
6. **Commitment** — Declaration, HEA/HFN

**Config hook:** `escalation_mode: "danger"` vs `escalation_mode: "intimacy"`. Outline stage and scene drafting use this to enforce the correct ladder.

---

## Engine Swap: Mystery vs Chemistry

| Thriller Engine | Romance Engine |
|-----------------|----------------|
| "What's happening?" | "Will they choose each other?" |
| Logic-reveal layer | Sensory-emotional layer |
| Evidence, deduction | Micro-moments, touches, glances |
| Surveillance, stakes | Desire suppression, subtext |
| Tension = physical danger | Tension = emotional risk |

**Implication:** Scene function classification (`quiet_killers.classify_scene_function`) may need romance-specific categories: *attraction_beat*, *tension_escalation*, *vulnerability_reveal*, *misunderstanding*, *choice_point*, *commitment*.

---

## New Romance-Specific Tracks

Add these to `reference_bible.md` (or equivalent) when doing romance:

### 1. Emotional Breadcrumb Tracker
Per-chapter: What emotional beat did each lead experience? What did they reveal? What did they withhold?

### 2. Touch Progression Map
| Chapter | Touch type | Who initiates | Meaning |
|---------|------------|---------------|---------|
| 1–3 | Accidental brush, hand hold | — | Awareness |
| 4–6 | Deliberate touch, arm/back | — | Tension |
| 7+ | Escalation per subgenre | — | Intimacy gate |

### 3. Vulnerability Index
Per chapter: Who is more vulnerable? Who has emotional leverage? Who retreats? Who misreads?

### 4. Intimacy Gate Enforcement
Physical intimacy must follow emotional trust. Flag scenes where touch/kiss happens before vulnerability threshold.

### 5. Conflict Authenticity Validator
Third-act breakups must be *earned* — grounded in character wounds, not contrived. Validator checks: Did the conflict thread exist before Ch 10? Is the wound established?

---

## Tone Density

| Genre | Prose | Pacing | Target length |
|-------|-------|--------|---------------|
| Thriller | Compressed, precise, lean | Tension-forward | 17–60k typical |
| Romance | Breathing room, interior longing | Slow burn beats | 60–80k+ for slow burn |
| Dark academia / romantic suspense | Hybrid | Thriller pacing + romance subplot | 60–80k |

**Config hook:** `pacing_mode: "thriller"` vs `pacing_mode: "slow_burn"` — affects `words_per_chapter`, scene length guidance, and "breathing room" injection in prompts.

---

## Config Schema Additions (for romance)

```yaml
# Genre mode — switches escalation and gate semantics
genre_mode: thriller   # or romance, romantic_suspense, dark_academia

# When genre_mode: romance
romance:
  escalation_mode: intimacy      # danger | intimacy
  gate_type: emotional           # info | emotional
  pacing_mode: slow_burn         # thriller | slow_burn
  subgenre: contemporary         # contemporary | dark_academia | romantic_suspense | historical
  heat_level: 3                  # 0-5 (closed door to explicit)
  intimacy_gate:
    # Physical escalation must follow emotional trust
    first_kiss_after_chapter: 6
    consummation_after_chapter: 10  # or "off_page"
```

---

## Reference Bible Sections for Romance

Add these H2 sections to `reference_bible.md` when doing romance:

```
## TOUCH PROGRESSION MAP
| Ch | Touch | Initiator | Meaning |

## EMOTIONAL BREADCRUMB TRACKER
| Ch | Lead A | Lead B | Revealed | Withheld |

## VULNERABILITY INDEX
| Ch | Who has leverage | Who retreats | Misread |

## INTIMACY GATES
- First kiss: Ch X (after [emotional beat])
- ...
```

`bible_loader.py` can be extended with `get_touch_progression()`, `get_emotional_breadcrumbs()`, `get_vulnerability_index()` for prompt injection.

---

## What Not to Over-Engineer

Romance readers care about:
- Authentic emotional voice
- Chemistry realism
- Dialogue rhythm
- Interior longing

**Principle:** Enforce structure without flattening feeling. The system should guardrail *bad* patterns (repeated beats, contrived conflict, chemistry that skips steps) without forcing mechanical beats. Leave room for the model to generate authentic micro-moments.

---

## Subgenre Quick Reference

| Subgenre | Thriller instincts | Romance instincts | Best fit |
|----------|-------------------|-------------------|----------|
| **Contemporary romance** | Minimal | Full — chemistry, slow burn | Romance mode |
| **Dark academia** | Setting, secrets, atmosphere | Rivals-to-lovers, tension | Hybrid |
| **Romantic suspense** | Danger escalation, mystery | Emotional gates, chemistry | Both — dual engine |
| **Historical romance** | Period stakes | Courtship, propriety gates | Romance + period rules |

---

## Implementation Order (when switching)

1. ~~**Config:** Add `genre_mode`, `romance` block to schema~~ — Done: `configs/romance_config_template.yaml`
2. ~~**Bible loader:** Add `get_touch_progression()`, `get_emotional_breadcrumbs()`, `get_vulnerability_index()`~~ — Done: injected when `genre_mode: romance`
3. ~~**Scene drafting:** Romance bible sections injected when romance mode + reference bible present~~ — Done
4. **Outline stage:** When `genre_mode: romance`, use intimacy escalation ladder in outline instructions (TODO)
5. **Continuity / gates:** Add `gate_type: emotional` path — track vulnerability/confession state (TODO)
6. **Critic gate:** Add romance-specific checks (intimacy before trust, contrived breakup, repeated longing phrases) (TODO)

---

## Contemporary vs Dark Academia / Romantic Suspense

| Choice | Config | What changes |
|--------|--------|--------------|
| **Contemporary romance** | `genre_mode: romance`, `subgenre: contemporary` | Full chemistry engine, minimal thriller elements |
| **Dark academia** | `genre_mode: romance`, `subgenre: dark_academia` | Keep rivals-to-lovers, atmosphere, secrets; thriller instincts still apply to setting |
| **Romantic suspense** | `genre_mode: romantic_suspense` | **Dual engine**: danger escalation AND intimacy escalation; both Info Gates and Emotional Gates |
