"""
Canonical Facts Ledger — lightweight per-scene fact log for continuity.

Logs: location, characters_present, time_anchor, key_events.
Updated during scene drafting. Written to output/facts_ledger.json.

Config: enhancements.facts_ledger.enabled (default True).
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("facts_ledger")

# Patterns to extract simple facts from scene content
_LOC_PAT = re.compile(r"\b(in|at|inside|outside)\s+(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b")
_TIME_PAT = re.compile(r"\b(morning|afternoon|evening|night|dawn|dusk|later that (?:day|night)|the next day)\b", re.IGNORECASE)


def _extract_location_from_content(content: str) -> Optional[str]:
    """Heuristic: first strong location mention."""
    for m in _LOC_PAT.finditer(content[:1500]):
        return m.group(2).strip()
    return None


def _extract_time_anchor(content: str) -> Optional[str]:
    """First time-of-day or temporal phrase."""
    m = _TIME_PAT.search(content)
    return m.group(1).strip() if m else None


def _extract_characters_from_content(content: str, known_names: List[str]) -> List[str]:
    """Names that appear in dialogue or narration (simple: capitalized words that match known)."""
    if not known_names:
        return []
    seen = set()
    for name in known_names:
        if name and name.lower() in content.lower():
            seen.add(name)
    return sorted(seen)


def build_facts_for_scene(
    scene: Dict,
    scene_idx: int,
    known_characters: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build a single scene's fact entry from outline + content."""
    content = scene.get("content", "")
    ch = scene.get("chapter", 0)
    sc = scene.get("scene_number") or scene.get("scene", 0)
    scene_id = scene.get("scene_id") or f"ch{ch:02d}_s{sc:02d}"

    facts = {
        "scene_id": scene_id,
        "chapter": ch,
        "scene": sc,
        "location": scene.get("location") or _extract_location_from_content(content),
        "characters_present": scene.get("pov") and [scene.get("pov")] or [],
        "time_anchor": _extract_time_anchor(content),
        "key_events": [],  # Placeholder; could add LLM extraction later
    }

    if known_characters:
        present = _extract_characters_from_content(content, known_characters)
        if present:
            facts["characters_present"] = list(dict.fromkeys(
                (facts.get("characters_present") or []) + present
            ))

    return facts


def build_facts_ledger(
    scenes: List[Dict],
    characters: Optional[List[Dict]] = None,
    config: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Build full ledger from scenes."""
    cfg = (config or {}).get("enhancements", {}).get("facts_ledger", {})
    if cfg.get("enabled", True) is False:
        return {"skipped": "disabled by config"}

    known_names = []
    if characters:
        for c in characters:
            if isinstance(c, dict) and c.get("name"):
                known_names.append(c["name"])
            elif hasattr(c, "name"):
                known_names.append(getattr(c, "name", ""))

    entries = []
    for idx, scene in enumerate(scenes or []):
        if not isinstance(scene, dict):
            continue
        entry = build_facts_for_scene(scene, idx, known_names)
        entries.append(entry)

    return {"entries": entries, "scene_count": len(entries)}


def write_facts_ledger(ledger: Dict, output_dir: Path) -> None:
    """Write ledger to output/facts_ledger.json."""
    if "skipped" in ledger:
        return
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "facts_ledger.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2, ensure_ascii=False)
    logger.info("Facts ledger written to %s", path)
