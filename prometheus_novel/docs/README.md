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
