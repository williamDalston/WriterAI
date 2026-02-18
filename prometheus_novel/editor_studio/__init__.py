"""Editor Studio — surgical refinement passes on completed manuscripts.

Runs 3–6 micro-passes to transform an existing draft into polished prose.
Think marble statue with a chisel: targeted edits, no full regeneration.

Usage:
    python -m scripts.run_editor_studio data/projects/burning-vows-30k
"""

from editor_studio.orchestrator import EditorStudioOrchestrator, run_editor_studio

__all__ = ["EditorStudioOrchestrator", "run_editor_studio"]
