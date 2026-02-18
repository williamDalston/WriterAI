"""Run overuse analysis on a manuscript.

Detects words and phrases used more than threshold (default 10).
Outputs report JSON and optional YAML for phrase_replacement_banks.
Supports docx, md, or project (pipeline_state) input.

Usage:
    python -m prometheus_novel.scripts.run_overuse_analysis [path]
    python -m prometheus_novel.scripts.run_overuse_analysis --docx path/to.docx
    python -m prometheus_novel.scripts.run_overuse_analysis -p burning-vows-30k --threshold 8
"""

import json
import sys
from pathlib import Path

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROJECT = PROJECT_ROOT / "data/projects/burning-vows-30k"


def extract_text(path: Path) -> str:
    """Extract text from docx, md, or pipeline_state.json."""
    path = Path(path)
    if not path.exists():
        return ""

    if path.suffix.lower() == ".docx":
        try:
            from docx import Document
            doc = Document(str(path))
            return "\n\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
        except ImportError:
            print("[ERROR] pip install python-docx for .docx support")
            return ""

    if path.suffix.lower() == ".md":
        return path.read_text(encoding="utf-8")

    if path.name == "pipeline_state.json":
        data = json.loads(path.read_text(encoding="utf-8"))
        scenes = data.get("scenes", [])
        parts = []
        for s in scenes:
            if isinstance(s, dict) and s.get("content"):
                parts.append(s["content"])
        return "\n\n".join(parts)

    return ""


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Overuse analysis for manuscripts")
    parser.add_argument("path", nargs="?", default=None, help="Docx, md, or project path")
    parser.add_argument("--docx", "-d", help="Path to .docx file")
    parser.add_argument("--project", "-p", help="Project name (e.g. burning-vows-30k)")
    parser.add_argument("--threshold", "-t", type=int, default=10,
        help="Flag words/phrases with count > this (default: 10)")
    parser.add_argument("--output", "-o", help="Output dir (default: same as input)")
    parser.add_argument("--yaml", "-y", action="store_true",
        help="Write overuse_banks.yaml for phrase_replacement_banks")
    parser.add_argument("--top", type=int, default=50,
        help="Top N words/phrases in YAML (default: 50)")
    parser.add_argument("--no-ignore-words", action="store_true",
        help="Don't exclude common words (like, into, etc.) from word report")
    args = parser.parse_args()

    # Resolve input path
    base = PROJECT_ROOT.parent
    if args.docx:
        in_path = Path(args.docx)
        if not in_path.is_absolute():
            in_path = (base / args.docx).resolve()
    elif args.project:
        proj = PROJECT_ROOT / "data/projects" / args.project
        # Prefer docx in output, else md, else pipeline_state
        for cand in [
            proj / "output" / "Burning Vows Final_KDP_audit_fixed.docx",
            proj / "output" / "Burning Vows Final_KDP.docx",
            proj / "output" / "Burning Vows Final.docx",
            proj / "output" / f"{args.project}.md",
            proj / "pipeline_state.json",
        ]:
            if cand.exists():
                in_path = cand
                break
        else:
            in_path = proj / "pipeline_state.json"
    elif args.path:
        in_path = Path(args.path)
        if not in_path.is_absolute():
            in_path = (base / args.path).resolve()
    else:
        in_path = DEFAULT_PROJECT / "output" / "Burning Vows Final_KDP_audit_fixed.docx"
        if not in_path.exists():
            in_path = DEFAULT_PROJECT / "pipeline_state.json"

    if not in_path.exists():
        print(f"[ERROR] Not found: {in_path}")
        return 1

    text = extract_text(in_path)
    if not text.strip():
        print("[ERROR] No text extracted")
        return 1

    from prometheus_novel.quality.overuse_analyzer import (
        analyze_overuse,
        report_to_replacement_yaml,
    )

    report = analyze_overuse(
        text,
        word_threshold=args.threshold,
        phrase_threshold=args.threshold,
        ignore_words=set() if args.no_ignore_words else None,
    )

    out_dir = args.output or in_path.parent
    if in_path.parent != out_dir:
        out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = in_path.stem
    if "_audit_fixed" in stem or "_KDP" in stem:
        stem = stem.replace("_audit_fixed", "").replace("_KDP", "")

    # Save JSON
    json_path = Path(out_dir) / "overuse_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Report: {json_path}")

    # Print summary
    stats = report.get("stats", {})
    words = report.get("overused_words", [])
    phrases = report.get("overused_phrases", [])

    print(f"\nWords over {args.threshold}: {len(words)}")
    for w in words[:15]:
        print(f"  {w['word']}: {w['count']}")
    if len(words) > 15:
        print(f"  ... and {len(words) - 15} more")

    print(f"\nPhrases over {args.threshold}: {len(phrases)}")
    for p in phrases[:15]:
        print(f"  \"{p['phrase']}\": {p['count']}")
    if len(phrases) > 15:
        print(f"  ... and {len(phrases) - 15} more")

    if args.yaml:
        yaml_path = Path(out_dir) / "overuse_detected.yaml"
        report_to_replacement_yaml(report, yaml_path, top_words=args.top, top_phrases=args.top)
        print(f"\nYAML (add replacements, merge with phrase_replacement_banks): {yaml_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
