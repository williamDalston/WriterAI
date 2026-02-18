"""Run editorial craft checks on a project or docx.

Runs motif saturation, gesture frequency, scene transitions, simile density,
chapter length, tense consistency, and paragraph cadence. Outputs JSON report.

Usage:
    python -m prometheus_novel.scripts.run_editorial_craft [project_path]
    python -m prometheus_novel.scripts.run_editorial_craft --docx path/to.docx
"""

import json
import sys
from pathlib import Path

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
DEFAULT_PROJECT = PROJECT_ROOT / "data/projects/burning-vows-30k"


def load_scenes_from_project(proj: Path) -> list:
    """Load scenes from pipeline_state.json."""
    state_file = proj / "pipeline_state.json"
    if not state_file.exists():
        return []
    data = json.loads(state_file.read_text(encoding="utf-8"))
    return data.get("scenes", [])


def load_scenes_from_docx(path: Path) -> list:
    """Extract text from docx, split into pseudo-scenes by chapter headers."""
    try:
        from docx import Document
    except ImportError:
        return []
    doc = Document(str(path))
    scenes = []
    ch = 1
    buf = []
    for p in doc.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        if p.style.name == "Heading 1" and t.startswith("Chapter"):
            if buf:
                scenes.append({"chapter": ch, "scene_number": 1, "content": "\n\n".join(buf)})
                buf = []
            try:
                ch = int(t.replace("Chapter", "").strip())
            except ValueError:
                ch += 1
        else:
            buf.append(t)
    if buf:
        scenes.append({"chapter": ch, "scene_number": 1, "content": "\n\n".join(buf)})
    return scenes


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", help="Project path")
    parser.add_argument("--docx", "-d", help="Docx path (extracts pseudo-scenes)")
    parser.add_argument("--output", "-o", help="Output JSON path")
    args = parser.parse_args()

    base = PROJECT_ROOT.parent
    if args.docx:
        docx_path = Path(args.docx)
        if not docx_path.is_absolute():
            docx_path = (base / args.docx).resolve()
        scenes = load_scenes_from_docx(docx_path)
        out_dir = docx_path.parent
    else:
        proj = Path(args.path or str(DEFAULT_PROJECT))
        if not proj.is_absolute():
            cand = base / args.path if args.path else DEFAULT_PROJECT
            proj = cand.resolve() if cand.exists() else (PROJECT_ROOT / "data/projects" / (args.path or "burning-vows-30k"))
        scenes = load_scenes_from_project(proj)
        out_dir = proj / "output"

    if not scenes:
        print("[ERROR] No scenes loaded")
        return 1

    from quality.editorial_craft import run_editorial_craft_checks

    report = run_editorial_craft_checks(scenes, {})

    out_path = Path(args.output) if args.output else out_dir / "editorial_craft_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Report: {out_path}")
    violations = report.get("violations", [])
    print(f"\nViolations: {len(violations)}")
    for v in violations[:10]:
        print(f"  [{v.get('type', '?')}] {v.get('message', v)[:80]}...")
    if len(violations) > 10:
        print(f"  ... and {len(violations) - 10} more")
    print(f"\nPass: {report.get('pass', False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
