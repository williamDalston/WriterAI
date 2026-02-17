# Cursor-Ready Task List

> **Format:** Ticket-style breakdown with acceptance criteria. Hand to Cursor or a contributor to implement in order.

---

## T1: Outline JSON retry/repair (HIGH) — DONE

**Problem:** Qwen (and others) sometimes emit unterminated JSON strings in outline batches, causing chapter loss and downstream chaos.

**Acceptance criteria:**
- [x] Retry loop only breaks on `_is_valid_outline_batch(batch)`. Raw wrappers do NOT count as success.
- [x] On parse failure, at least one retry attempt occurs (regenerate with lower temp).
- [x] Tier A: Local repair (suffix closure / object extraction) attempted before regeneration.
- [x] Backfill uses same retry/repair ladder (min 1 retry, MAX_BACKFILL_RETRIES=2).
- [x] Failures + recoveries logged in `run_report.json` under `outline_json`.
- [x] `resolved_config.yaml` meta updated with outline parse/repair summary counters.

---

## T2: Stable scene IDs — audit and harden (HIGH)

**Status:** Partially implemented. Scene IDs are stamped at outline time (~line 4616) and flow into scene drafting. Audit remaining gaps.

**Format:** `ch{chapter:02d}_s{scene:02d}` (e.g. `ch02_s01`)

### Implementation checklist

- [x] **Outline time:** IDs exist on every scene in master_outline (4616–4624)
- [x] **Backfill:** Backfilled chapters get IDs in the same stamping pass (loop runs after backfill)
- [x] **Scene drafting:** Each drafted scene has `scene_id` from outline (6180, 6436)
- [x] **Micro-passes:** Dialogue drought, AI-tell scrub, scene-turn repair, dedup tail — preserve `scene_id` (mutate scene dict in-place, 6520)
- [x] **Regeneration tail:** Dedup tail regen only updates content; scene_id preserved
- [x] **Meters:** Quality meters use `scene_id` or derive ch02_s01 format (`quality_meters.py`)
- [x] **Export:** Validator `_scene_id()` prefers `scene.get("scene_id")`, fallback ch02_s01
- [x] **Outline resampling:** Collision repair patches `scene["scene_name"]` in place; identity rule documented in `_regenerate_colliding_scene_names`

**Regeneration rule:** Any function that regenerates a scene must return **text only** (or patch fields in place), never a new scene dict.

**Integrity meter:** `scene_id_integrity_check()` in quality_meters; run via `run_all_meters`. Catches mismatches, duplicates, missing IDs.

### Edge cases to verify

| Case | Expected behavior |
|------|-------------------|
| Backfill adds chapter 5 | ch05_s01, ch05_s02, ... stamped after backfill |
| Dedup truncates ch11_s02 | Regenerated tail keeps scene_id ch11_s02 |
| Scene name collision repair | Only `scene_name` changes; patch in place, never replace scene dict |
| Meters (act tripod, micro-prose) | Report by scene_id for stable targeting |
| Upstream omits scene_id | `scene_body_similarity_meter` sets `scene_id_fallback` for diagnostics |

### Files

- `stages/pipeline.py` (master_outline 4616–4624, scene_drafting 6180/6436, _post_draft_micro_passes)
- `stages/quality_meters.py`
- `export/docx_exporter.py`

---

## T3: Expand run_report provenance (MEDIUM)

**Acceptance criteria:**
- [ ] Add to run_report.json: `run_id`, `git_commit` (standalone — same as resolved_config meta)
- [ ] Add: `project_name`, `title`, `target_length`
- [ ] Add: model versions / names used
- [ ] Add: seed fingerprint, fixture mode (smoke vs real) if applicable
- [ ] Add: meters summary per stage (if available)
- [ ] Write run_report.json to `output/` alongside resolved_config.yaml

**Files:** `stages/pipeline.py`, `configs/config_resolver.py` (reuse provenance helpers)

---

## T4: Doctor command (MEDIUM)

**Acceptance criteria:**
- [ ] CLI: `writerai doctor` or `python -m prometheus_novel.interfaces.cli.main doctor`
- [ ] Checks: deps importable, output dir exists and writable, fixtures load, model endpoint reachable
- [ ] Prints resolved config path and run_report location
- [ ] Warns if running smoke on 7b when user might expect 14b
- [ ] Exit 0 if all OK, non-zero with actionable message if not

**Files:** `interfaces/cli/main.py`, new `cmd_doctor()` or `commands/doctor.py`

---

## T5: Smoke test timeout (LOW)

**Acceptance criteria:**
- [ ] Add per-test timeout (e.g. pytest-timeout 300s for smoke)
- [ ] Or: internal timer in smoke fixtures that fails fast
- [ ] Smoke stays under ~5 min total for all 3 tests

**Files:** `pyproject.toml` (pytest-timeout), or `tests/conftest.py`

---

## T6: PROMETHEUS_SMOKE_MODEL env override (LOW)

**Acceptance criteria:**
- [ ] Smoke tests read `PROMETHEUS_SMOKE_MODEL` (default: `qwen2.5:7b`)
- [ ] Resolved config (when run via pytest) includes `meta.provenance.fixture_mode: smoke` and `meta.provenance.smoke_model: <actual>`
- [ ] Enables nightly runs with 14b to catch drift

**Files:** `tests/test_planning_smoke.py`, `tests/test_act_tripod.py`, `tests/test_micro_prose.py`, `tests/conftest.py`

---

## T7: Debug pack helper (LOW)

**Acceptance criteria:**
- [ ] CLI: `python -m prometheus_novel.tools.debug_pack -p data/projects/<name>`
- [ ] Zips: resolved_config.yaml, run_report.json (if exists), config.yaml, seed_data.yaml (if exists)
- [ ] Output: `<project_name>_debug_<run_id>.zip` in project output dir
- [ ] Exit 0 on success

**Files:** `prometheus_novel/tools/debug_pack.py` (new), wire into CLI or standalone

---

## Dependency order

```
T1 (outline retry) ──► independent, do first
T2 (stable IDs) ────► audit + harden (core already done)
T3 (run_report) ───► can reuse provenance from config_resolver
T4 (doctor) ───────► independent
T5 (timeout) ──────► independent
T6 (smoke model) ──► small, depends on smoke tests existing (done)
T7 (debug pack) ───► independent, low effort
```

---

## Quick "are we done?" check

- [ ] Unit tests: `pytest -m "not smoke"` passes
- [ ] Smoke tests: `pytest -m smoke` passes (with Ollama)
- [ ] Resolved config written with provenance on every run
- [ ] Doctor command runs and reports status
- [ ] Outline stage retries on JSON failure
- [ ] Scenes have stable IDs in master_outline
