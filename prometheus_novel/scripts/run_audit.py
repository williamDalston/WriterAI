"""Run developmental + fresh-eyes audit on a project. Prints summary, saves JSON.

Usage:
    python -m prometheus_novel.scripts.run_audit data/projects/burning-vows-30k
"""

import json
import sys
from pathlib import Path

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    proj_path = sys.argv[1] if len(sys.argv) > 1 else "data/projects/burning-vows-30k"
    proj = Path(proj_path)
    if not proj.is_absolute():
        proj = PROJECT_ROOT / proj
    if not proj.exists():
        print(f"[ERROR] Project not found: {proj}")
        return 1

    config_path = proj / "config.yaml"
    config = {}
    if config_path.exists():
        import yaml
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    state_file = proj / "pipeline_state.json"
    if not state_file.exists():
        print("[ERROR] pipeline_state.json not found")
        return 1

    with open(state_file, encoding="utf-8") as f:
        state = json.load(f)
    scenes = state.get("scenes", [])
    outline = state.get("master_outline", [])
    chars = state.get("characters", [])

    from quality.developmental_audit import run_developmental_audit

    r = run_developmental_audit(scenes, outline, chars, config)
    print("\n=== Developmental Audit (deterministic) ===")
    print(f"Pass: {r.get('pass', True)} | Findings: {len(r.get('findings', []))}")
    for f in r.get("findings", [])[:20]:
        t = f.get("type", "")
        c = f.get("code", "")
        m = (f.get("message", "") or "")[:80]
        sid = f.get("scene_id", "")
        print(f"  [{t}] {sid} {c}: {m}")

    out_dir = proj / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    da_path = out_dir / "developmental_audit.json"
    with open(da_path, "w", encoding="utf-8") as f:
        json.dump(r, f, indent=2, ensure_ascii=False)
    print(f"\n[INFO] Developmental audit saved to {da_path.name}")

    # Run fresh eyes (LLM) if available
    fresh_path = out_dir / "fresh_eyes_audit.json"
    if fresh_path.exists():
        with open(fresh_path, encoding="utf-8") as f:
            fe = json.load(f)
        fe_findings = fe.get("findings", [])
        print(f"\n=== Fresh Eyes Audit (LLM) — {len(fe_findings)} findings ===")
        for f in fe_findings[:15]:
            print(f"  - {f.get('code','')} [{f.get('scene_id','')}]: {(f.get('message','') or '')[:70]}...")
    else:
        print("\n[INFO] Run 'python -m prometheus_novel.scripts.run_fresh_eyes <project>' for LLM audit")

    return 0


if __name__ == "__main__":
    sys.exit(main())
