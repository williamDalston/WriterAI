"""Strip preamble artifacts and filter words from Burning Vows 30k.

P0: Remove "Lena Castillo found herself in the ..." sentence prefixes
P2: Fix double periods (subsumed by P0 in most cases, but also standalone)
P3: Remove filter words ("I could feel/see/hear" → direct sensation)

Operates on pipeline_state.json (source of truth), then recompiles .md.
"""

import json
import re
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

PROJECT = Path(__file__).parent.parent / "data" / "projects" / "burning-vows-30k"
STATE_FILE = PROJECT / "pipeline_state.json"

# ── P0: Preamble pattern ──
# Matches "Lena Castillo found herself in the <location description>." or ".."
# The preamble always starts the scene and is followed by actual prose.
PREAMBLE_RE = re.compile(
    r'^Lena Castillo found herself in the [^.]+\.\.?\s*',
    re.IGNORECASE
)

# ── P2: Double periods ──
DOUBLE_PERIOD_RE = re.compile(r'\.\.(?!\.)')  # ".." but not "..."

# ── P3: Filter word patterns (conservative) ──
# Only strip clear filter constructions, preserve natural usage
FILTER_REPLACEMENTS = [
    # "I could feel X" → "X" (with the verb/noun that follows)
    (re.compile(r'\bI could feel\b', re.IGNORECASE), ''),
    # "I could see X" → "X"
    (re.compile(r'\bI could see\b', re.IGNORECASE), ''),
    # "I could hear X" → "X"
    (re.compile(r'\bI could hear\b', re.IGNORECASE), ''),
    # "I can feel X" → "X"
    (re.compile(r'\bI can feel\b', re.IGNORECASE), ''),
    # "I can see X" → "X"
    (re.compile(r'\bI can see\b', re.IGNORECASE), ''),
    # "I can hear X" → "X"
    (re.compile(r'\bI can hear\b', re.IGNORECASE), ''),
]

# Contexts where filter removal would sound wrong — skip these
FILTER_SKIP_CONTEXTS = [
    "I can hear her",      # natural phone/distance dialogue
    "I can see that",      # dialogue response
    "I can see dust",      # specific sensory, reads fine
    "I can feel myself",   # reflexive, natural
    "I can feel the question",  # abstract, natural
]


def strip_preamble(content: str) -> tuple:
    """Remove preamble artifact from start of scene. Returns (new_content, was_modified)."""
    m = PREAMBLE_RE.match(content)
    if not m:
        return content, False
    # After stripping, capitalize the first letter of remaining text
    remainder = content[m.end():]
    if remainder and remainder[0].islower():
        remainder = remainder[0].upper() + remainder[1:]
    return remainder, True


def fix_double_periods(content: str) -> tuple:
    """Replace '..' with '.' (but not '...' ellipsis). Returns (new_content, count)."""
    count = len(DOUBLE_PERIOD_RE.findall(content))
    if count == 0:
        return content, 0
    return DOUBLE_PERIOD_RE.sub('.', content), count


def strip_filters(content: str) -> tuple:
    """Remove filter words conservatively. Returns (new_content, count)."""
    total = 0
    for pattern, replacement in FILTER_REPLACEMENTS:
        # Find all matches
        for m in pattern.finditer(content):
            start = max(0, m.start() - 30)
            context = content[start:m.end() + 30]
            # Skip if context matches a known safe pattern
            if any(skip in context for skip in FILTER_SKIP_CONTEXTS):
                continue
            # Check what follows the filter phrase
            after = content[m.end():m.end() + 50].strip()
            # If followed by a noun/adjective (the, his, her, my, a, the, sweat, etc.)
            # the removal works. If followed by "that" or a verb, it's likely dialogue.
            if after and after.split()[0].lower() in ('that', 'what', 'how', 'why', 'if'):
                continue  # dialogue or clause, skip

            # Perform replacement for this single match
            before_text = content[:m.start()]
            after_text = content[m.end():]

            # Clean up: if removal leaves ", X" or "; X" or "and X", capitalize X
            after_stripped = after_text.lstrip()
            if after_stripped:
                first_word = after_stripped.split()[0] if after_stripped.split() else ""
                # If previous char is start-of-sentence context, capitalize
                prev_chars = before_text.rstrip()
                if prev_chars and prev_chars[-1] in '.!?";\n':
                    after_text = after_stripped[0].upper() + after_stripped[1:]
                elif prev_chars and prev_chars[-1] == ',':
                    # "blah, I could see X" → "blah, X" (keep comma)
                    after_text = ' ' + after_stripped
                elif not prev_chars or prev_chars[-1] in (' ', '\n'):
                    # Standalone at sentence boundary
                    after_text = after_stripped[0].upper() + after_stripped[1:]

            content = before_text + after_text
            total += 1
            break  # re-search after modification (positions shifted)

    # Multi-pass: keep going until no more matches
    if total > 0:
        more_content, more_count = strip_filters(content)
        return more_content, total + more_count

    # Clean up artifacts: double spaces, space before period/comma
    content = re.sub(r'  +', ' ', content)
    content = re.sub(r' ([.,;!?])', r'\1', content)
    return content, total


def recompile_md(state: dict, scenes: list) -> int:
    """Recompile the .md manuscript from scenes. Returns word count."""
    outline = state.get("master_outline", [])
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
            full_text += "\n\n\u2042\n\n"
        full_text += scene.get("content", "")
    full_text += "\n\n---\n\n# THE END\n\n"
    full_text += f"*Word Count: {total_words:,}*\n"

    md_path = PROJECT / "output" / "burning-vows-30k.md"
    md_path.write_text(full_text, encoding="utf-8")
    return total_words


def main():
    print("=" * 60)
    print("P0-P3 FIX SCRIPT — Burning Vows 30k")
    print("=" * 60)

    with open(STATE_FILE, encoding="utf-8") as f:
        state = json.load(f)

    scenes = [s for s in state.get("scenes", []) if isinstance(s, dict)]

    stats = {
        "scenes_total": len(scenes),
        "preambles_stripped": 0,
        "double_periods_fixed": 0,
        "filters_removed": 0,
        "scenes_modified": 0,
    }

    for i, scene in enumerate(scenes):
        content = scene.get("content", "")
        if not content:
            continue

        original = content

        # ── P0: Strip preamble ──
        content, preamble_hit = strip_preamble(content)
        if preamble_hit:
            stats["preambles_stripped"] += 1

        # ── P2: Double periods ──
        content, dp_count = fix_double_periods(content)
        stats["double_periods_fixed"] += dp_count

        # ── P3: Filter words ──
        content, filter_count = strip_filters(content)
        stats["filters_removed"] += filter_count

        # Commit
        if content != original:
            scene["content"] = content
            stats["scenes_modified"] += 1

    # Save pipeline_state.json
    state["scenes"] = scenes
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

    # Recompile .md
    total_words = recompile_md(state, scenes)

    # Report
    print(f"\nScenes total:          {stats['scenes_total']}")
    print(f"Scenes modified:       {stats['scenes_modified']}")
    print(f"Preambles stripped:    {stats['preambles_stripped']}")
    print(f"Double periods fixed:  {stats['double_periods_fixed']}")
    print(f"Filters removed:       {stats['filters_removed']}")
    print(f"\nTotal words:           {total_words:,}")
    print(f"Saved: {STATE_FILE}")
    print(f"Compiled: {PROJECT / 'output' / 'burning-vows-30k.md'}")
    print("\nDone.")


if __name__ == "__main__":
    main()
