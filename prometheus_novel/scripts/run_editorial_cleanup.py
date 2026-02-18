"""Run deterministic editorial cleanup on a project manuscript.

Strips preambles, grounding artifacts, fixes POV, double periods, filter words,
Elena hallucination, Marco ring, timeline, Enzo line, mussed, between-us.

Usage:
    python -m prometheus_novel.scripts.run_editorial_cleanup data/projects/burning-vows-30k
    python -m prometheus_novel.scripts.run_editorial_cleanup data/projects/burning-vows-30k --no-elena
"""

import argparse
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


def main():
    parser = argparse.ArgumentParser(description="Editorial cleanup: grounding strips, POV fixes, Elena removal")
    parser.add_argument(
        "project_path",
        type=str,
        default="data/projects/burning-vows-30k",
        nargs="?",
        help="Path to project",
    )
    parser.add_argument("--no-grounding", action="store_true", help="Skip grounding artifact removal")
    parser.add_argument("--no-pov", action="store_true", help="Skip POV pronoun fixes")
    parser.add_argument("--no-elena", action="store_true", help="Skip Elena hallucination removal")
    parser.add_argument("--dry-run", action="store_true", help="Report what would change, don't write")
    args = parser.parse_args()

    project_path = Path(args.project_path)
    if not project_path.is_absolute():
        project_path = PROJECT_ROOT / project_path

    if not project_path.exists():
        print(f"[ERROR] Project not found: {project_path}")
        return 1

    state_file = project_path / "pipeline_state.json"
    if not state_file.exists():
        print(f"[ERROR] pipeline_state.json not found")
        return 1

    from quality.editorial_cleanup import run_editorial_cleanup

    with open(state_file, encoding="utf-8") as f:
        state_data = json.load(f)
    scenes = state_data.get("scenes") or []
    if not scenes:
        print("[ERROR] No scenes in pipeline state")
        return 1

    print(f"[INFO] Running editorial cleanup on {len(scenes)} scenes")
    print(f"  strip_grounding={not args.no_grounding}, fix_pov={not args.no_pov}, remove_elena={not args.no_elena}")

    report = run_editorial_cleanup(
        scenes,
        strip_grounding=not args.no_grounding,
        fix_pov=not args.no_pov,
        remove_elena=not args.no_elena,
    )

    print(f"\n[OK] Editorial cleanup complete")
    print(f"  Preambles: {report.get('preambles_stripped', 0)} | Grounding: {report['grounding_removed']} | Double periods: {report.get('double_periods_fixed', 0)} | Filter words: {report.get('filter_words_fixed', 0)}")
    print(f"  POV fixed: {report['pov_fixed']} | Elena removed: {report['elena_removed']}")
    print(f"  Marco ring: {report.get('marco_ring_fixed', 0)} | Timeline: {report.get('timeline_fixed', 0)} | Enzo: {report.get('enzos_line_fixed', 0)}")
    print(f"  Mussed: {report.get('mussed_fixed', 0)} | Between-us: {report.get('between_us_fixed', 0)}")
    print(f"  Scenes modified: {report['scenes_modified']}")

    if not args.dry_run and report["scenes_modified"] > 0:
        # Backup then persist
        backup = project_path / "pipeline_state.json.pre_editorial_cleanup"
        import shutil
        import yaml
        shutil.copy2(state_file, backup)
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2, ensure_ascii=False)
        print(f"[INFO] State persisted; backup at {backup.name}")
        # Recompile .md and .docx
        output_dir = project_path / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        scenes = state_data.get("scenes") or []
        outline = state_data.get("master_outline") or []
        config_path = project_path / "config.yaml"
        config = {}
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
        ch_titles = {}
        for ch_data in outline:
            if isinstance(ch_data, dict):
                ch_titles[int(ch_data.get("chapter", 0))] = ch_data.get("chapter_title", "")
        total_words = sum(len(s.get("content", "").split()) for s in scenes)
        title = config.get("title", "Novel")
        synopsis = config.get("synopsis") or config.get("high_concept", "") or ""
        full_text = f"# {title}\n\n*{synopsis}*\n\n---\n\n"
        current_chapter = None
        for scene in scenes:
            chapter = int(scene.get("chapter", 1))
            if chapter != current_chapter:
                ch_title = ch_titles.get(chapter, "")
                full_text += f"\n\n## Chapter {chapter}: {ch_title}\n\n" if ch_title else f"\n\n## Chapter {chapter}\n\n"
                current_chapter = chapter
            else:
                full_text += "\n\n⁂\n\n"
            full_text += scene.get("content", "")
        full_text += "\n\n---\n\n# THE END\n\n*Word Count: {total_words:,}*\n"
        project_name = config.get("project_name", "novel")
        md_path = output_dir / f"{project_name}.md"
        md_path.write_text(full_text.format(total_words=total_words), encoding="utf-8")
        print(f"[INFO] Recompiled: {md_path.name}")
        # Export to Word
        try:
            from prometheus_novel.export.docx_exporter import KDPExporter
            exporter = KDPExporter(project_path)
            docx_path = exporter.export()
            print(f"[INFO] Exported Word: {docx_path.name}")
        except Exception as e:
            print(f"[WARN] Docx export skipped: {e}")
    elif args.dry_run:
        print("[DRY RUN] No changes written")

    return 0


if __name__ == "__main__":
    sys.exit(main())
