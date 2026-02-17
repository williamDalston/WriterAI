# PROMETHEUS-NOVEL 1.0 Documentation

This directory contains documentation, runbooks, and failure scenarios for the PROMETHEUS-NOVEL 1.0 project.

## Project Overview
(Briefly describe the project's goal and high-level architecture)

## Getting Started
1.  **Scaffold the project:**
    ```bash
    python prometheus_novel_scaffold.py
    ```
2.  **Install dependencies (using Poetry):**
    ```bash
    cd prometheus_novel
    poetry install
    poetry shell
    ```
3.  **Configure API Keys:**
    Edit the `.env` file in the project root to add your LLM API keys.
    ```
    OPENAI_API_KEY=sk-...
    # GOOGLE_API_KEY=your_gemini_api_key
    ```
4.  **Run the main pipeline (conceptual):**
    ```bash
    python run_prometheus.py
    ```
5.  **Run the API (conceptual):**
    ```bash
    uvicorn api:app --reload --port 8000
    ```

## Getting Running (Tests)

Dev dependencies (including `pytest-asyncio`) are required for tests:

```bash
cd prometheus_novel
poetry install   # installs dev deps; or: pip install pytest pytest-asyncio
```

**Run unit tests:**
```bash
pytest
```

**Run smoke tests** (require Ollama or API; use temp project from `tests/fixtures/`):
```bash
pytest -m smoke
```
Smoke tests run with `qwen2.5:7b` and reduced token budgets. Treat them as a **boot sequence** (plumbing, contracts, stage order, no explosions), not a performance or prose-quality benchmark. For quality evaluation, run the same tests manually with 14b or your target model.

**Run slow/stress tests:**
```bash
pytest -m slow
```

**Skip smoke/slow** (CI, or when LLM not available):
```bash
pytest -m "not smoke and not slow"
```

## Quality System

* **[QUALITY_SYSTEM_OVERVIEW.md](QUALITY_SYSTEM_OVERVIEW.md)** — State of quality infrastructure, what regeneration changes, required artifacts, hard vs soft gates.
* **[QUALITY_RUNBOOK.md](QUALITY_RUNBOOK.md)** — Triage rules: what to do when TENSION_COLLAPSE, CH1_HOOK_WEAK, facts drift, hot phrases, or budget warns.
* **[WRITING_RULES_GAP_ANALYSIS.md](WRITING_RULES_GAP_ANALYSIS.md)** — Built-in rules, gaps, recommendations, governance maturity.

## Architecture & Defense Layers

* **[DEFENSE_ARCHITECTURE.md](DEFENSE_ARCHITECTURE.md)** — Defense layers, problem→defense mapping, artifact metrics, config reference, and improvement inference guide.

* **[MODEL_SWAP_GUIDE.md](MODEL_SWAP_GUIDE.md)** — Switching from local Qwen to paid models (OpenAI, Anthropic, Gemini). Config + calibration only; no code changes.

* **[AUDIOBOOK_GUIDE.md](AUDIOBOOK_GUIDE.md)** — Generating ACX/Audible-compliant audiobooks via Google Cloud TTS. Multi-voice support, cost estimation, CLI usage, and troubleshooting.

## Runbooks & Failure Scenarios
(Detailed guides for operating the system, diagnosing issues, and recovery procedures)

* **Cold Start Procedure:** How to start the system from scratch.
* **Resuming Generation:** How to pick up from a previous state after a pause or crash.
* **Budget Exceeded:** What to do when the LLM budget is hit.
* **LLM API Rate Limits/Errors:** Troubleshooting steps for API issues.
* **Memory Exhaustion:** How to handle and prevent Out-of-Memory errors.
* **Consistency Issues:** How to debug narrative inconsistencies.
* **Data Corruption:** Steps for recovering from corrupted state/memory.
* **Adding New Stages/Critics:** Guide for extending the system.

---
