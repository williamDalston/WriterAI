"""Run only the Fresh Eyes audit — LLM cold-read for CONFUSION, PACING_DRAG, UNCLEAR_MOTIVATION.

Usage:
    python -m prometheus_novel.scripts.run_fresh_eyes data/projects/burning-vows-30k
    python -m prometheus_novel.scripts.run_fresh_eyes data/projects/burning-vows-30k --apply-fixes
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
    parser = argparse.ArgumentParser(description="Run Fresh Eyes audit only")
    parser.add_argument(
        "project_path",
        type=str,
        default="data/projects/burning-vows-30k",
        nargs="?",
        help="Path to project",
    )
    parser.add_argument(
        "--apply-fixes",
        action="store_true",
        help="Apply developmental fixes for CONFUSION and UNCLEAR_MOTIVATION",
    )
    args = parser.parse_args()

    project_path = Path(args.project_path)
    if not project_path.is_absolute():
        project_path = PROJECT_ROOT / project_path

    if not project_path.exists():
        print(f"[ERROR] Project not found: {project_path}")
        return 1

    state_file = project_path / "pipeline_state.json"
    if not state_file.exists():
        print(f"[ERROR] pipeline_state.json not found at {project_path}")
        return 1

    config_path = project_path / "config.yaml"
    config = {}
    if config_path.exists():
        import yaml
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    async def _run():
        from quality.developmental_audit import audit_fresh_eyes
        from prometheus_lib.llm.clients import get_client

        defaults = config.get("model_defaults", {}) or {}
        model = defaults.get("critic_model") or defaults.get("api_model") or "claude-sonnet-4-20250514"
        client = get_client(model)
        print(f"[INFO] Using model: {model}")

        with open(state_file, encoding="utf-8") as f:
            state_data = json.load(f)
        scenes = state_data.get("scenes") or []
        outline = state_data.get("master_outline") or []

        print("[INFO] Running fresh eyes audit...")
        result = await audit_fresh_eyes(client, scenes, outline, config)

        if result.get("skipped"):
            print(f"[WARN] Fresh eyes skipped: {result['skipped']}")
            return result

        findings = result.get("findings", [])
        print(f"\n[OK] Fresh eyes complete: {len(findings)} findings")
        for f in findings:
            code = f.get("code", "")
            scene_id = f.get("scene_id", "")
            msg = f.get("message", f.get("issue", ""))
            print(f"  - {code} [{scene_id}]: {msg[:80]}...")

        output_dir = project_path / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / "fresh_eyes_audit.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"[INFO] Results saved to {out_path}")

        if args.apply_fixes and findings:
            from quality.developmental_fixes import run_developmental_fixes
            audit_report = {"pass": False, "findings": findings, "findings_by_type": {}}
            for x in findings:
                code = x.get("code", "")
                audit_report["findings_by_type"].setdefault(code, []).append(x)
            fix_report = await run_developmental_fixes(
                scenes=scenes,
                audit_report=audit_report,
                client=client,
                config=config,
                dry_run=False,
            )
            modified = fix_report.get("scenes_modified", 0)
            if modified > 0:
                # Persist scenes back to pipeline_state
                state_data["scenes"] = scenes
                with open(state_file, "w", encoding="utf-8") as f:
                    json.dump(state_data, f, indent=2, ensure_ascii=False)
                print(f"[OK] Applied fixes: {fix_report.get('fixes_applied', 0)} fixes across {modified} scenes")
            else:
                print("[INFO] No fixes applied (developmental_fixes may not handle these codes)")

        return result

    asyncio.run(_run())
    return 0


if __name__ == "__main__":
    sys.exit(main())
