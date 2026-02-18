"""Apply deterministic quality fixes to an existing manuscript.

Runs the 5 quality transforms we built (no LLM calls, $0 cost):
1. classify_scene_profile — label each scene with mode + risk
2. apply_deflection_grounding — break reflective runs in high-tension scenes
3. apply_bridge_insert — patch scene openings when location changes
4. apply_final_line_rewrite — mode-aware ending rewrites
5. Gesture diversification — replace overused physical tics

Usage:
    python scripts/apply_manual_fixes.py
"""

import json
import re
import sys
import os
from pathlib import Path
from collections import defaultdict

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from quality.quiet_killers import (
    classify_scene_profile,
    classify_scene_function,
    apply_deflection_grounding,
    apply_bridge_insert,
    apply_final_line_rewrite,
)

PROJECT = Path(__file__).parent.parent / "data" / "projects" / "burning-vows-30k"
STATE_FILE = PROJECT / "pipeline_state.json"
CONTRACT_FILE = PROJECT / "output" / "quality_contract.json"

# ── Gesture replacements (position-specific to avoid monotony) ──
GESTURE_REPLACEMENTS = {
    "hand through his hair": [
        "thumb along his jaw",
        "knuckles against the railing",
        "palm flat on the table",
        "fingers along his collar",
        "hand down his face",
    ],
    "close enough that I": [
        "near enough that I",
        "so close I",
        "inches away, and I",
        "right there, and I",
        "within arm's reach, and I",
    ],
    "his shoulder brushes mine": [
        "his arm grazes mine",
        "his elbow nudges mine",
        "his knuckles brush my wrist",
        "his sleeve catches my arm",
    ],
    "curl behind my ear": [
        "strand from my face",
        "loose hair from my temple",
        "lock off my shoulder",
        "piece back from my forehead",
    ],
}


def load_tension_map(contract_path: Path, outline: list) -> dict:
    """Build scene_id -> tension_level from quality contract + outline."""
    tension = {}
    # From quality contract (actual measured tension)
    if contract_path.exists():
        with open(contract_path, encoding="utf-8") as f:
            qc = json.load(f)
        for c in qc.get("contracts", []):
            sid = c.get("scene_id", "")
            t = c.get("tension_level", 5)
            if sid:
                tension[sid] = int(t)
    # Fill gaps from outline
    for ch in outline or []:
        if not isinstance(ch, dict):
            continue
        ch_num = int(ch.get("chapter", 0))
        for sc in ch.get("scenes", []):
            if not isinstance(sc, dict):
                continue
            sc_num = int(sc.get("scene", sc.get("scene_number", 0)))
            sid = sc.get("scene_id", f"ch{ch_num:02d}_s{sc_num:02d}")
            if sid not in tension:
                try:
                    tension[sid] = int(sc.get("tension_level", 5))
                except (ValueError, TypeError):
                    tension[sid] = 5
    return tension


def load_warning_map(contract_path: Path) -> dict:
    """Build scene_id -> list of warning strings."""
    out = defaultdict(list)
    if not contract_path.exists():
        return dict(out)
    with open(contract_path, encoding="utf-8") as f:
        qc = json.load(f)
    for c in qc.get("contracts", []):
        sid = c.get("scene_id", "")
        for w in c.get("warnings", []):
            if w:
                out[sid].append(w)
    return dict(out)


def apply_gesture_fixes_manuscript(scenes: list, stats: dict) -> None:
    """Replace overused gestures across the whole manuscript (not per-scene).

    Keeps the FIRST occurrence in the whole book, replaces subsequent ones.
    """
    for phrase, replacements in GESTURE_REPLACEMENTS.items():
        # Find all occurrences across all scenes with (scene_idx, position)
        all_hits = []
        for i, scene in enumerate(scenes):
            content = scene.get("content", "")
            for m in re.finditer(re.escape(phrase), content, re.IGNORECASE):
                all_hits.append((i, m.start(), m.end()))
        if len(all_hits) <= 1:
            continue
        # Keep first, replace rest (process in reverse order within each scene)
        replacement_idx = 0
        # Group by scene, process each scene's hits in reverse
        by_scene = {}
        for scene_i, start, end in all_hits[1:]:  # skip first occurrence
            by_scene.setdefault(scene_i, []).append((start, end))
        for scene_i, positions in by_scene.items():
            content = scenes[scene_i].get("content", "")
            for start, end in reversed(positions):
                if replacement_idx >= len(replacements):
                    replacement_idx = 0
                original = content[start:end]
                repl = replacements[replacement_idx]
                if original[0].isupper():
                    repl = repl[0].upper() + repl[1:]
                content = content[:start] + repl + content[end:]
                stats["gesture_replacements"] += 1
                replacement_idx += 1
            scenes[scene_i]["content"] = content


def main():
    print("=" * 60)
    print("MANUAL FIX SCRIPT — Burning Vows 30k")
    print("=" * 60)

    with open(STATE_FILE, encoding="utf-8") as f:
        state = json.load(f)

    scenes = [s for s in state.get("scenes", []) if isinstance(s, dict)]
    outline = state.get("master_outline", [])
    tension_map = load_tension_map(CONTRACT_FILE, outline)
    warning_map = load_warning_map(CONTRACT_FILE)

    stats = {
        "scenes_total": len(scenes),
        "deflection_fixes": 0,
        "bridge_inserts": 0,
        "final_line_rewrites": 0,
        "gesture_replacements": 0,
        "scenes_modified": 0,
        "scene_profiles_added": 0,
    }

    for i, scene in enumerate(scenes):
        sid = scene.get("scene_id", f"scene_{i}")
        content = scene.get("content", "")
        if not content:
            continue

        original = content
        tension = tension_map.get(sid, 5)
        location = scene.get("location", "")
        pov = scene.get("pov", "")
        warnings = warning_map.get(sid, [])

        # ── 1. Classify scene profile ──
        purpose = ""
        # Try to get purpose from outline
        for ch in outline:
            if not isinstance(ch, dict):
                continue
            for sc in ch.get("scenes", []):
                if isinstance(sc, dict) and sc.get("scene_id") == sid:
                    purpose = sc.get("purpose", sc.get("summary", ""))
                    break

        func_label = classify_scene_function(content, purpose)
        profile = classify_scene_profile(content, purpose, tension, func_label)
        scene["scene_profile"] = profile
        scene["scene_function"] = func_label
        scene["tension_level"] = tension
        stats["scene_profiles_added"] += 1

        scene_mode = profile.get("scene_mode", "default")

        # ── 2. Deflection grounding (tension >= 6, has DEFLECTION warning) ──
        has_deflection = any("DEFLECTION" in w for w in warnings)
        if has_deflection and tension >= 6:
            content = apply_deflection_grounding(content, tension_level=tension)
            if content != original:
                stats["deflection_fixes"] += 1

        # ── 3. Bridge insert — DISABLED (introduces false continuity warnings) ──
        # prev_text = scenes[i - 1].get("content", "") if i > 0 else ""
        # prev_loc = scenes[i - 1].get("location", "") if i > 0 else ""
        # has_continuity = any("CONTINUITY" in w for w in warnings)
        # if has_continuity or (prev_loc and location and prev_loc != location):
        #     content_bridged = apply_bridge_insert(...)
        #     if content_bridged != content:
        #         stats["bridge_inserts"] += 1
        #         content = content_bridged

        # ── 4. Final line rewrite (mode-aware) ──
        has_final_line = any("FINAL_LINE" in w for w in warnings)
        if has_final_line:
            content_rewritten = apply_final_line_rewrite(content, scene_mode=scene_mode)
            if content_rewritten != content:
                stats["final_line_rewrites"] += 1
                content = content_rewritten

        # ── Commit changes ──
        if content != original:
            scene["content"] = content
            stats["scenes_modified"] += 1

    # ── 5. Gesture diversification (manuscript-wide) ──
    apply_gesture_fixes_manuscript(scenes, stats)

    # ── Save ──
    state["scenes"] = scenes
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

    # ── Report ──
    print(f"\nScenes total:          {stats['scenes_total']}")
    print(f"Scenes modified:       {stats['scenes_modified']}")
    print(f"Scene profiles added:  {stats['scene_profiles_added']}")
    print(f"Deflection fixes:      {stats['deflection_fixes']}")
    print(f"Bridge inserts:        {stats['bridge_inserts']}")
    print(f"Final line rewrites:   {stats['final_line_rewrites']}")
    print(f"Gesture replacements:  {stats['gesture_replacements']}")
    print(f"\nSaved to: {STATE_FILE}")

    # ── Recompile .md ──
    config_path = PROJECT / "config.yaml"
    import yaml
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    ch_titles = {}
    for ch_data in outline or []:
        if isinstance(ch_data, dict):
            ch_titles[int(ch_data.get("chapter", 0))] = ch_data.get("chapter_title", "")

    total_words = sum(len(s.get("content", "").split()) for s in scenes)
    title = config.get("title", "Burning Vows")
    synopsis = config.get("synopsis") or config.get("high_concept") or state.get("high_concept", "")

    full_text = f"# {title}\n\n"
    full_text += f"*{synopsis}*\n\n"
    full_text += "---\n\n"
    current_chapter = None
    for scene in scenes:
        chapter = int(scene.get("chapter", 1))
        if chapter != current_chapter:
            ch_title = ch_titles.get(chapter, "")
            if ch_title:
                full_text += f"\n\n## Chapter {chapter}: {ch_title}\n\n"
            else:
                full_text += f"\n\n## Chapter {chapter}\n\n"
            current_chapter = chapter
        else:
            full_text += "\n\n⁂\n\n"
        full_text += scene.get("content", "")
    full_text += "\n\n---\n\n# THE END\n\n"
    full_text += f"*Word Count: {total_words:,}*\n"

    md_path = PROJECT / "output" / "burning-vows-30k.md"
    md_path.write_text(full_text, encoding="utf-8")
    print(f"Recompiled manuscript: {md_path}")
    print(f"Total words: {total_words:,}")
    print("\nDone. Run quality_meters to verify improvement.")


if __name__ == "__main__":
    main()
