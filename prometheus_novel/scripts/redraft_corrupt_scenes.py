#!/usr/bin/env python3
"""Surgical redraft of corrupt (language-drift) scenes using qwen2.5:14b.

Reads pipeline_state.json, identifies scenes with >30% non-Latin characters,
rebuilds a scene prompt from outline data, calls qwen2.5:14b, and replaces
the scene content in-place. Does NOT touch clean scenes.

Usage:
    cd prometheus_novel
    python scripts/redraft_corrupt_scenes.py --project the-bends [--dry-run]
"""
import argparse
import asyncio
import json
import sys
import os
from pathlib import Path

# Add prometheus_novel to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prometheus_lib.llm.clients import OllamaClient


CORRUPT_THRESHOLD = 0.30  # >30% non-Latin = corrupt
REDRAFT_MODEL = "qwen2.5:14b"
MAX_TOKENS = 6000
TEMPERATURE = 0.7


def detect_corrupt(text: str) -> tuple[float, bool]:
    """Return (non_latin_ratio, is_corrupt)."""
    if not text:
        return 1.0, True
    alpha = [c for c in text if c.isalpha()]
    if not alpha:
        return 1.0, True
    non_latin = sum(1 for c in alpha if ord(c) > 127)
    ratio = non_latin / len(alpha)
    return ratio, ratio > CORRUPT_THRESHOLD


def find_outline_entry(outline: list, chapter: int, scene_num: int) -> dict:
    """Find the matching outline entry for a scene."""
    for ch in outline:
        if not isinstance(ch, dict):
            continue
        ch_num = ch.get("chapter_number", ch.get("chapter", 0))
        if ch_num != chapter:
            continue
        for sc in (ch.get("scenes") or []):
            if not isinstance(sc, dict):
                continue
            sn = sc.get("scene_number", sc.get("scene", 0))
            if sn == scene_num:
                return sc
    return {}


def build_redraft_prompt(outline_entry: dict, config: dict, state: dict) -> str:
    """Build a scene drafting prompt from outline data."""
    pov = outline_entry.get("pov", "Elena Vance")
    location = outline_entry.get("location", "Unknown")
    purpose = outline_entry.get("purpose", "")
    scene_name = outline_entry.get("scene_name", "")
    conflict = outline_entry.get("central_conflict", "")
    opening_hook = outline_entry.get("opening_hook", "")
    outcome = outline_entry.get("outcome", "")
    tension = outline_entry.get("tension_level", 5)
    pacing = outline_entry.get("pacing", "medium")
    dialogue_notes = outline_entry.get("dialogue_notes", "")
    differentiator = outline_entry.get("differentiator", "")
    char_goal = outline_entry.get("character_scene_goal", "")

    # Pull config info
    synopsis = config.get("synopsis", "")
    writing_style = config.get("writing_style", "close first-person present")
    tone = config.get("tone", "")
    setting_desc = config.get("setting", "")
    avoid = config.get("avoid", "")

    # World bible summary
    wb = state.get("world_bible", {})
    wb_setting = wb.get("setting", "") if isinstance(wb, dict) else ""

    prompt = f"""You are writing a scene for a thriller novel.

=== STORY ===
{synopsis}

=== WRITING STYLE ===
{writing_style}
Tone: {tone}

=== THIS SCENE ===
Scene: {scene_name}
Location: {location}
POV Character: {pov} (first person, "I")
Purpose: {purpose}
What makes this scene unique: {differentiator}
Character's goal: {char_goal}
Central conflict: {conflict}
Opening hook concept: {opening_hook}
Outcome: {outcome}
Tension level: {tension}/10
Pacing: {pacing}
Dialogue notes: {dialogue_notes}

=== SETTING ===
{wb_setting}
{setting_desc}

=== RULES ===
- Write in FIRST PERSON PRESENT TENSE as {pov}
- "I" = {pov}. Never refer to {pov} by name in narration.
- Open with ACTION or DIALOGUE, not description
- Include at least 4 lines of quoted dialogue
- No preamble, no title, no scene heading
- No meta-commentary, no "Chapter X", no author notes
- Paragraphs: 4 sentences max
- Target: approximately 800 words
- AVOID: {avoid}
- Write ONLY in English. No other languages.

Write the complete scene now:"""

    return prompt


async def redraft_scene(client: OllamaClient, prompt: str) -> str:
    """Call qwen2.5:14b and return the generated text."""
    response = await client.generate(
        prompt=prompt,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    )
    return response.content.strip()


async def main():
    parser = argparse.ArgumentParser(description="Redraft corrupt scenes")
    parser.add_argument("--project", required=True, help="Project name")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be redrafted without doing it")
    parser.add_argument("--threshold", type=float, default=CORRUPT_THRESHOLD, help="Non-Latin ratio threshold")
    args = parser.parse_args()

    project_dir = Path(__file__).resolve().parent.parent / "data" / "projects" / args.project
    state_path = project_dir / "pipeline_state.json"
    config_path = project_dir / "config.yaml"

    if not state_path.exists():
        print(f"ERROR: {state_path} not found")
        sys.exit(1)

    # Load state
    with open(state_path, "r", encoding="utf-8") as f:
        state = json.load(f)

    # Load config
    import yaml
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    scenes = state.get("scenes", [])
    outline = state.get("master_outline", [])

    # Find corrupt scenes
    corrupt = []
    for i, sc in enumerate(scenes):
        sid = sc.get("scene_id", "")
        text = sc.get("content", "")
        ratio, is_bad = detect_corrupt(text)
        if is_bad:
            words = len(text.split()) if text else 0
            corrupt.append((i, sid, ratio, words))

    if not corrupt:
        print("No corrupt scenes found. All clean!")
        return

    print(f"Found {len(corrupt)} corrupt scenes:")
    for idx, sid, ratio, words in corrupt:
        print(f"  {sid}: {ratio:.1%} non-Latin, {words} words")

    if args.dry_run:
        print("\n[DRY RUN] Would redraft the above scenes. Use without --dry-run to execute.")
        return

    # Initialize client
    client = OllamaClient(REDRAFT_MODEL)
    await client._ensure_initialized()
    print(f"\nUsing model: {REDRAFT_MODEL}")

    # Redraft each corrupt scene
    for idx, sid, ratio, old_words in corrupt:
        sc = scenes[idx]
        chapter = sc.get("chapter", 0)
        scene_num = sc.get("scene_number", 0)

        outline_entry = find_outline_entry(outline, chapter, scene_num)
        if not outline_entry:
            print(f"  WARNING: No outline entry for {sid} (ch{chapter} s{scene_num}). Skipping.")
            continue

        prompt = build_redraft_prompt(outline_entry, config, state)
        print(f"\n  Redrafting {sid} (was {old_words} words, {ratio:.1%} non-Latin)...")

        try:
            new_content = await redraft_scene(client, prompt)

            # Validate: check it's actually English
            new_ratio, still_bad = detect_corrupt(new_content)
            new_words = len(new_content.split())

            if still_bad:
                print(f"  WARNING: Redraft still corrupt ({new_ratio:.1%} non-Latin). Retrying...")
                new_content = await redraft_scene(client, prompt)
                new_ratio, still_bad = detect_corrupt(new_content)
                new_words = len(new_content.split())
                if still_bad:
                    print(f"  FAILED: Still corrupt after retry. Skipping {sid}.")
                    continue

            # Replace content
            sc["content"] = new_content
            print(f"  OK: {sid} -> {new_words} words, {new_ratio:.1%} non-Latin")

        except Exception as e:
            print(f"  ERROR redrafting {sid}: {e}")
            continue

    # Save state
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(f"\nSaved updated state to {state_path}")

    # Summary
    print(f"\nRedraft complete: {len(corrupt)} scenes processed")


if __name__ == "__main__":
    asyncio.run(main())
