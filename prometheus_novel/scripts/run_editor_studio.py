"""Editor Studio — surgical refinement passes on completed manuscripts.

Runs 3–6 micro-passes to add shine without full regeneration.
Different tools, different mindset: editor + sculptor, not factory.

Passes (target quality_contract warnings):
  0. deflection       — Break up reflective runs (20 scenes in BV) [PRIORITY]
  1. continuity       — Add transitions for time/location jumps
  2. dialogue_friction — Interruptions, deflections, texture in dialogue
  3. stakes           — One anchor sentence: what's at risk
  4. final_line       — Upgrade scene endings (decision/question/action)
  5. rhythm           — Vary sentence length (RHYTHM_FLATLINE)
  6. tension_collapse  — Smooth tension landing (e.g. ch13_s03)
  7. causality        — Fix connector paragraphs with no prior reference
  8. gesture_diversify — Replace "hand through his hair" etc. (manuscript-wide scan)
  9. voice            — Character voice micro-tweaks (top 10 tension scenes)
 10. premium          — Opening, midpoint, final chapter (expensive-model targets)

Usage:
    python -m scripts.run_editor_studio data/projects/burning-vows-30k
    python -m scripts.run_editor_studio data/projects/burning-vows-30k --passes continuity,dialogue_friction
    python -m scripts.run_editor_studio data/projects/burning-vows-30k --dry-run
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(usecwd=True))


def main():
    parser = argparse.ArgumentParser(
        description="Editor Studio: surgical refinement passes on completed manuscripts",
    )
    parser.add_argument(
        "project_path",
        type=str,
        default="data/projects/burning-vows-30k",
        nargs="?",
        help="Path to project (e.g. data/projects/burning-vows-30k)",
    )
    parser.add_argument(
        "--passes",
        type=str,
        default=None,
        help="Comma-separated passes (default: all). Options: continuity,dialogue_friction,stakes,final_line,voice,premium",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be run without making changes",
    )
    args = parser.parse_args()

    project_path = Path(args.project_path)
    if not project_path.is_absolute():
        project_path = PROJECT_ROOT / project_path

    if not project_path.exists():
        print(f"[ERROR] Project not found: {project_path}")
        return 1

    passes_enabled = None
    if args.passes:
        passes_enabled = [p.strip() for p in args.passes.split(",") if p.strip()]

    if args.dry_run:
        # Just report what we'd do
        state_file = project_path / "pipeline_state.json"
        contract_file = project_path / "output" / "quality_contract.json"
        print("[DRY RUN] Editor Studio")
        print(f"  Project: {project_path}")
        print(f"  pipeline_state.json: {'found' if state_file.exists() else 'MISSING'}")
        print(f"  quality_contract.json: {'found' if contract_file.exists() else 'MISSING'}")
        if passes_enabled:
            print(f"  Passes: {passes_enabled}")
        else:
            print("  Passes: all (continuity, dialogue_friction, stakes, final_line, voice, premium)")
        return 0

    async def _run():
        from editor_studio.orchestrator import run_editor_studio

        # Load client from project config
        config_path = project_path / "config.yaml"
        config = {}
        if config_path.exists():
            import yaml
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
        from prometheus_lib.llm.clients import get_client
        defaults = config.get("model_defaults", {}) or {}
        model = defaults.get("critic_model") or defaults.get("api_model") or "gpt-4o-mini"
        client = get_client(model)
        print(f"[INFO] Using model: {model}")

        report = await run_editor_studio(
            project_path,
            passes_enabled=passes_enabled,
            client=client,
        )
        return report

    report = asyncio.run(_run())

    if report.get("errors"):
        for e in report["errors"]:
            print(f"[ERROR] {e}")
        return 1

    print(f"\n[OK] Editor Studio complete")
    print(f"  Scenes modified: {report.get('scenes_modified', 0)}")
    for p in report.get("passes_run", []):
        print(f"  - {p.get('pass')}: {p.get('scenes_modified', 0)}/{p.get('scenes_processed', 0)} scenes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
