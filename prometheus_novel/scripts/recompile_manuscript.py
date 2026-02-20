#!/usr/bin/env python3
"""Recompile the-bends.md from pipeline_state.json after scene fixes."""
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT = Path(__file__).resolve().parent.parent / "data" / "projects" / "the-bends"
STATE_FILE = PROJECT / "pipeline_state.json"
OUTPUT_DIR = PROJECT / "output"

state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
scenes = state.get("scenes", [])
outline = state.get("master_outline", [])

# Build chapter title map
chapter_titles = {}
for ch in (outline or []):
    if isinstance(ch, dict):
        ch_num = ch.get("chapter")
        ch_title = ch.get("chapter_title", "")
        if ch_num and ch_title:
            chapter_titles[ch_num] = ch_title

# Assemble
project_name = state.get("project_name", "the-bends")
full_text = f"# {project_name.replace('-', ' ').title()}\n\n"
current_chapter = None
total_words = 0

for scene in scenes:
    if not isinstance(scene, dict):
        continue
    content = scene.get("content", "")
    total_words += len(content.split())

    chapter = scene.get("chapter")
    if chapter != current_chapter:
        ch_title = chapter_titles.get(chapter, "")
        if ch_title:
            full_text += f"\n\n## Chapter {chapter}: {ch_title}\n\n"
        else:
            full_text += f"\n\n## Chapter {chapter}\n\n"
        current_chapter = chapter
    else:
        full_text += "\n\n---\n\n"
    full_text += content

full_text += "\n\n---\n\n# THE END\n\n"
full_text += f"*Word Count: {total_words:,}*\n"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
output_file = OUTPUT_DIR / f"{project_name}.md"
output_file.write_text(full_text, encoding="utf-8")

print(f"Manuscript recompiled: {output_file}")
print(f"Total words: {total_words:,}")
print(f"Scenes: {len(scenes)}")
