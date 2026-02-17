# PROMETHEUS-NOVEL Reliability Runbook

> **Purpose:** Checklist and workflows for keeping the pipeline testable, reproducible, and debuggable. Use this when onboarding, debugging, or handing off to Cursor.

---

## 1. Pre-flight checklist (before any run)

| Check | Command / Action |
|-------|------------------|
| Dev deps installed | `poetry install` or `pip install pytest pytest-asyncio` |
| Unit tests pass | `pytest -m "not smoke and not slow"` |
| Project has config | `data/projects/<name>/config.yaml` exists with required fields |
| Output dir writable | `data/projects/<name>/output/` exists or will be created |
| Model reachable | Ollama running (local) or API keys set (cloud) |

---

## 2. Test commands (memorize these)

```bash
# Unit tests only (CI, no LLM)
pytest -m "not smoke and not slow"

# Smoke tests (temp project, 7b; validates plumbing)
pytest -m smoke

# Slow tests (full planning + drafting)
pytest -m slow

# Everything
pytest
```

**Smoke tests use `qwen2.5:7b`** — they validate stability, not prose quality. For quality evaluation, run manually with 14b or target model.

---

## 3. Config resolution (what actually ran)

Every pipeline run writes `output/resolved_config.yaml` with:

- **Merged config:** env defaults → project config → CLI overlay
- **Provenance (meta):** run_id, timestamp_utc, git_commit, python_version, platform, model_routing_summary, seed_fingerprint

**When something fails:** Open `resolved_config.yaml` first. It tells you exactly what the run used.

---

## 4. Smoke vs real runs

| Mode | Model | Purpose |
|------|-------|---------|
| `pytest -m smoke` | qwen2.5:7b | Fast plumbing check, no disk project needed |
| Manual `python -m tests.test_planning_smoke` | qwen2.5:14b (default) | Full planning with the-glass-registry |
| CLI `generate -c config.yaml` | From config | Real novel generation |

**Nightly / drift check:** Run smoke with 14b via `PROMETHEUS_SMOKE_MODEL=qwen2.5:14b` (when implemented) to catch "works in smoke, fails in reality."

---

## 5. Known failure modes and fixes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `pytest -m smoke` fails with import error | Missing pytest-asyncio | `pip install pytest-asyncio` |
| Smoke passes, real run fails | 7b vs 14b behavior | Run smoke with 14b (nightly); compare resolved_config |
| Missing chapters in outline | JSON parse failure (Qwen unterminated string) | **Outstanding:** Add outline JSON retry/repair |
| Scene selection wrong | Unstable IDs, ordinal drift | **Outstanding:** Assign stable scene IDs at outline time |
| "Which config is truth?" | Two config systems (env vs project) | Use `resolved_config.yaml` — it's the single merged truth |
| Tests depend on the-glass-registry | Hardcoded project path | Use `smoke_project` fixture; `tests/fixtures/smoke_config.yaml` |

---

## 6. When a run fails: what artifacts to attach

For reproducible debugging, attach these when reporting or analyzing a failure:

| Artifact | Path | Why |
|----------|------|-----|
| Resolved config | `output/resolved_config.yaml` | Exact config + provenance used |
| Run report | `output/run_report.json` | Stage outcomes, meters, errors |
| Failing stage logs | Console / log output | Error message, stack trace |
| Seed / config used | `config.yaml`, `seed_data.yaml` | Input to reproduce |

One-liner to pack for a bug report:
```bash
zip debug-pack.zip output/resolved_config.yaml output/run_report.json config.yaml
```

---

## 7. CI strategy

**Default CI:**
```bash
pytest -m "not smoke and not slow"
```

**Optional CI job (manual/scheduled):**
```bash
pytest -m smoke
```

**Nightly:** Smoke with 14b (or real config) to catch model-specific drift.

---

## 8. What’s still missing (priority order)

1. **Outline JSON retry/repair** — #1 pipeline-integrity hole; causes missing chapters
2. **Stable scene IDs** (`ch02_s01`) — deterministic selection, safer dedup, exact reproducibility
3. **Expanded run_report provenance** — git hash, model versions, seed fingerprint, fixture mode
4. **Doctor command** — `writerai doctor` checks deps, fixtures, output dir, model reachability
5. **Smoke timeout** — per-test timeout so smoke stays fast
6. **PROMETHEUS_SMOKE_MODEL** — env override for smoke model (7b default, 14b for nightly)

---

## 9. File locations

| Artifact | Location |
|----------|----------|
| Resolved config | `data/projects/<name>/output/resolved_config.yaml` |
| Smoke fixture config | `tests/fixtures/smoke_config.yaml` |
| Pipeline stages | `stages/pipeline.py` |
| Config resolver | `configs/config_resolver.py` |
| Run report | `data/projects/<name>/output/run_report.json` (when written) |
