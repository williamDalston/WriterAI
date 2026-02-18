# Pipeline Improvements Spec — Option A (New Stages)

Companion to prompt-level fixes. Use this spec to wire new stages into the pipeline.
**Canonical manuscript:** `Burning Vows Final_KDP_audit_fixed_replaced.docx`

---

## 1. Roster Gate (Deterministic, Runs Early)

**Purpose:** Block hallucinated characters before they propagate. Runs BEFORE scene_expansion so bad scenes don't get expanded.

**Insert position:** After `scene_drafting`, before `scene_expansion`

```
STAGE_ORDER modification:
  "scene_drafting",
  "roster_gate",        # NEW — blocks on violation if config.roster_gate.block_on_violation
  "scene_expansion",
  ...
```

**Implementation:**

```python
# quality/character_roster.py — already exists
# pipeline.py — add _stage_roster_gate

async def _stage_roster_gate(self) -> tuple:
    """Check character roster; optionally block if violations exceed threshold."""
    from quality.character_roster import check_character_roster

    roster_violations = check_character_roster(
        self.state.scenes,
        self.state.master_outline,
        self.state.characters,
        self.state.config,
        min_dialogue_for_flag=2,  # Stricter: flag at 2 lines
    )

    cfg = self.state.config.get("enhancements", {}).get("roster_gate", {})
    block = cfg.get("block_on_violation", False)
    max_allowed = cfg.get("max_violations", 0)

    if block and len(roster_violations) > max_allowed:
        scene_ids = [v["scene_id"] for v in roster_violations]
        return {
            "blocked": True,
            "violations": roster_violations,
            "message": f"Roster gate: {len(roster_violations)} scene(s) have hallucinated characters. "
                       f"Fix or add to roster: {scene_ids}",
        }, 0

    self.state.roster_violations = roster_violations
    return {
        "violations": roster_violations,
        "blocked": False,
    }, 50
```

**Config:**
```yaml
enhancements:
  roster_gate:
    enabled: true
    block_on_violation: false   # true = fail pipeline if violations
    max_violations: 0
```

---

## 2. POV Enforcer (Micro-Pass, Runs in voice_human_pass or as Standalone)

**Purpose:** Deterministic POV pronoun fixes. The pipeline already has `_postprocess` and `_micro_pov_pronoun_fix`. A dedicated stage ensures POV is re-checked after any destructive LLM pass.

**Option 2a — Integrated:** Add POV re-enforce as final step of `_stage_voice_human_pass` (already partially there).

**Option 2b — Standalone stage:** Add `pov_enforcer` after `continuity_fix_2`:

```python
async def _stage_pov_enforcer(self) -> tuple:
    """Deterministic POV pronoun fix pass. No LLM — regex/surgical replacement."""
    fixed_count = 0
    for i, scene in enumerate(self.state.scenes or []):
        if not isinstance(scene, dict) or not scene.get("content"):
            continue
        pov = (scene.get("pov") or self.state.config.get("protagonist", "")).split()[0]
        if not pov:
            continue
        content = scene["content"]
        # Use existing _micro_pov_pronoun_fix from pipeline
        new_content = self._micro_pov_pronoun_fix(content, pov)
        if new_content != content:
            scene["content"] = new_content
            fixed_count += 1
    return {"scenes_fixed": fixed_count}, 10
```

**Wiring:** Add to STAGE_ORDER after `continuity_fix_2`, before `dialogue_polish`.

---

## 3. Causal Completeness (LLM Micro-Pass)

**Purpose:** Fix paragraphs that start with connector words (And, But, Still, Then, So) without a clear prior reference. Quality_contract flags these; this stage FIXES them via LLM.

**Insert position:** In `targeted_refinement` — ensure PASS_CAUSALITY is always run. Or add standalone `causal_completeness` stage.

**Implementation (reuse Editor Studio PASS_CAUSALITY):**

The Editor Studio already has `PASS_CAUSALITY`. The targeted_refinement stage runs Editor Studio passes. Ensure CAUSALITY is in the default passes list:

```python
# editor_studio/orchestrator.py — verify PASS_CAUSALITY is in DEFAULT_PASSES
# quality_contract already produces CAUSALITY warnings
# targeted_refinement targets scenes with CAUSALITY in warnings
```

**Standalone stage (if needed):**

```python
async def _stage_causal_completeness(self) -> tuple:
    """Fix CAUSALITY violations: connector paragraphs without prior reference."""
    from quality.quality_contract import run_quality_contract
    contracts = run_quality_contract(self.state.scenes, self.state.master_outline, self.state.config)
    causality_scenes = [
        c["scene_id"] for c in contracts.get("contracts", [])
        if any("CAUSALITY" in str(w) for w in c.get("warnings", []))
    ]
    if not causality_scenes:
        return {"fixed": 0}, 0

    client = self.get_client_for_stage("causal_completeness")
    for sid in causality_scenes:
        # Find scene, send to LLM with: "This paragraph starts with And/But/Still. Add explicit reference to prior beat."
        # Similar to PASS_CAUSALITY in editor_studio
        ...
    return {"scenes_fixed": n}, tokens
```

---

## 4. Scene Transition Grounding (Deterministic Check + Optional Fix)

**Purpose:** Ensure first 50 words of each scene have 2 of 3: TIME, PLACE, CAST. Already in editorial_craft.scene_transition_grounding. Wire into quality_meters or add as quality_audit input.

**Implementation:** Editorial craft already implements this. Ensure `run_editorial_craft_checks` is called in quality_meters/craft_scorecard and violations surface to quality_audit.

---

## 5. Stage Registration Checklist

To add a new stage:

1. Add stage name to `STAGE_ORDER` in `pipeline.py`
2. Add `"stage_name": self._stage_handler` to `stage_handlers` dict
3. Add `STAGE_MODELS` and `STAGE_TEMPERATURES` entries
4. Add to `PROSE_STAGES` if it modifies scenes (for transaction safety)
5. Implement `async def _stage_xxx(self) -> tuple: (report_dict, token_count)`

---

## Summary: Implemented

| Stage       | Type        | Insert After    | Blocks?   | Status |
|-------------|-------------|-----------------|-----------|--------|
| roster_gate | Deterministic | scene_drafting  | Configurable | **Wired** |
| pov_enforcer| Deterministic | continuity_fix_2 | No         | **Wired** |

Causal completeness: Editor Studio PASS_CAUSALITY already runs in targeted_refinement. No new stage needed.

---

## Option B: Prompt-Level Fixes (Implemented)

Added to scene drafting prompt in `pipeline.py`:

1. **CHARACTER ROSTER** — `_build_roster_reminder_block()` — lists allowed characters, forbids new named characters
2. **SCENE TRANSITION GROUNDING** — `_build_scene_transition_grounding_block()` — for mid-chapter scenes: require 2 of 3 (TIME/PLACE/CAST) in first 50 words
3. **VOICE UNDER PRESSURE** — `_build_voice_under_pressure_block()` — when tension ≥7: character must sharpen, not flatten
4. **CAUSALITY (strengthened)** — connector words must reference prior beat explicitly; added examples
