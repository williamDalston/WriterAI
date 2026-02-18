# Editorial Craft Gaps — Implementation Status

Companion to the Editorial Craft Gaps specification. Maps each proposed check to implementation status.

## Implemented (Deterministic)

| # | Check | Module | Status |
|---|-------|--------|--------|
| 2 | **Motif saturation** | `editorial_craft.motif_saturation_meter` | ✓ CITRUS, SALT, PRICE_TAGS, MOTHS_LIGHT, COFFEE_STAINS, STICKY_SURFACES, SCAR_TOUCHING, HAIR_TUCKING |
| 3 | **Gesture frequency** | `editorial_craft.gesture_frequency_meter` | ✓ Lena: curl_tuck, thumb_press, shoulders, cross_arms; Marco: hair_run, jaw_work, leaving_ruffled |
| 4 | **Paragraph-ending cadence** | `editorial_craft.paragraph_cadence_meter` | ✓ Consecutive LYRICAL run; FLAT % floor |
| 5 | **Scene transition grounding** | `editorial_craft.scene_transition_grounding` | ✓ TIME/PLACE/CAST in first 50 words |
| 6 | **Tense consistency** | `editorial_craft.tense_consistency_meter` | ✓ Per-scene dominant tense; manuscript-level mix flag |
| 7 | **Simile density** | `editorial_craft.simile_density_meter` | ✓ like/as if/as though; flag if >2.0/1k words |
| 10 | **Chapter length distribution** | `editorial_craft.chapter_length_meter` | ✓ >25% deviation; resolution chapter 80% floor |

## Pipeline Wiring

- **craft_scorecard**: `config.enhancements.craft_scorecard.editorial_craft` (default True)  
  Runs `run_editorial_craft_checks` and merges into `craft_scorecard.json`.
- **Standalone**: `python -m prometheus_novel.scripts.run_editorial_craft [project]`  
  Outputs `editorial_craft_report.json`.

## Not Yet Implemented (LLM-Dependent)

| # | Check | Detection | Notes |
|---|-------|-----------|-------|
| 1 | Dialogue voice drift | LLM classification | Compare character voice across tension levels |
| 8 | Interiority ratio | LLM sentence classification | ACTION/DIALOGUE/INTERIOR/SENSORY per scene |
| 9 | Initiative balance | LLM event classification | Who initiates touch/confession; 40/60–60/40 target |

## Config Extension

For tense enforcement during drafting:

```yaml
narration:
  pov: first_person
  pov_character: Lena
  tense: present  # or past — future: enforce in scene_drafting
```
