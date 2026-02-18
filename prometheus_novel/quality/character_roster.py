"""Character roster consistency check.

Flags scenes where a character with significant presence (dialogue, emotional weight)
is not in the outline/character roster — catches hallucinated subplots like Elena.
"""

import logging
import re
from typing import Any, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


def _extract_roster(outline: List[Dict], characters: List[Dict], config: Dict) -> Set[str]:
    """Extract canonical character roster (first names, lowercase)."""
    roster: Set[str] = set()
    # From character_profiles
    for c in (characters or []):
        if isinstance(c, dict):
            name = (c.get("name") or "").split()[0]
            if name:
                roster.add(name.lower())
    # From outline scene POVs and referenced names
    for ch in (outline or []):
        if not isinstance(ch, dict):
            continue
        for sc in ch.get("scenes", []):
            if not isinstance(sc, dict):
                continue
            pov = (sc.get("pov") or "").split()[0]
            if pov:
                roster.add(pov.lower())
    # From config other_characters, protagonist, antagonist
    for key in ("protagonist", "antagonist", "other_characters"):
        val = config.get(key, "")
        if val:
            for m in re.findall(r"\b([A-Z][a-z]{2,})\b", str(val)):
                roster.add(m.lower())
    return roster


def _count_dialogue_lines(text: str, name: str) -> int:
    """Count dialogue lines attributed to this character."""
    # Patterns: "Name said/said Name", '"...' after Name
    name_esc = re.escape(name)
    # "Name said" or "Name whispered" etc.
    prefix = len(re.findall(rf"\b{name_esc}\s+(?:said|whispered|asked|replied|murmured|exclaimed|called|added|continued|began|offered|warned|joked|teased)\b", text, re.IGNORECASE))
    # '"..." Name said' (dialogue before attribution)
    suffix = len(re.findall(rf'["\u201c][^"\u201d]*["\u201d]\s+{name_esc}\s+(?:said|whispered|asked|replied|murmured|exclaimed)', text, re.IGNORECASE))
    return prefix + suffix


def _extract_named_characters_in_scene(text: str) -> Dict[str, int]:
    """Extract named characters (capitalized multi-char words) with approximate significance."""
    # Skip common false positives
    skip = {"the", "i", "a", "he", "she", "they", "it", "we", "you", "my", "me",
            "chapter", "scene", "am", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "must", "can", "said", "asked", "told"}
    candidates: Dict[str, int] = {}
    # Multi-word names: "Sofia Chen", "Marco Vitale" — use first name for roster
    for m in re.finditer(r"\b([A-Z][a-z]{2,})\s+([A-Z][a-z]{2,})\b", text):
        first, _ = m.group(1), m.group(2)
        if first.lower() not in skip:
            candidates[first.lower()] = candidates.get(first.lower(), 0) + 1
    # Single capitalized names (less reliable, but catch "Elena")
    for m in re.finditer(r"(?<=[.!?\s])([A-Z][a-z]{2,})(?=\s+(?:said|whispered|asked|walked|turned|looked|smiled|nodded|reached|grabbed|pressed|touched))", text):
        n = m.group(1).lower()
        if n not in skip:
            candidates[n] = candidates.get(n, 0) + 2  # Weight by likely significance
    return candidates


def check_character_roster(
    scenes: List[Dict],
    outline: List[Dict],
    characters: List[Dict],
    config: Dict,
    min_dialogue_for_flag: int = 3,
) -> List[Dict[str, Any]]:
    """Check for hallucinated characters (significant presence but not in roster).

    Returns list of violations: {scene_id, character, dialogue_lines, reason}.
    """
    roster = _extract_roster(outline, characters, config)
    if not roster:
        return []

    violations: List[Dict[str, Any]] = []
    for i, scene in enumerate(scenes or []):
        if not isinstance(scene, dict):
            continue
        content = scene.get("content", "")
        if not content or len(content) < 100:
            continue
        ch = scene.get("chapter", 0)
        sc = scene.get("scene_number") or scene.get("scene", 0)
        scene_id = scene.get("scene_id") or f"ch{int(ch):02d}_s{int(sc):02d}"

        named = _extract_named_characters_in_scene(content)
        for name_lower, weight in named.items():
            if name_lower in roster:
                continue
            dialogue_lines = _count_dialogue_lines(content, name_lower)
            # Flag if: has 3+ dialogue lines, OR high presence (emotional interaction)
            if dialogue_lines >= min_dialogue_for_flag:
                violations.append({
                    "scene_id": scene_id,
                    "character": name_lower.title(),
                    "dialogue_lines": dialogue_lines,
                    "reason": f"Character '{name_lower.title()}' has {dialogue_lines} dialogue lines but is not in outline/character roster (possible hallucination)",
                })
                logger.warning(
                    "Character roster violation: %s in %s — %d dialogue lines, not in roster",
                    name_lower.title(), scene_id, dialogue_lines,
                )
            elif weight >= 4 and dialogue_lines >= 1:
                # Significant mentions + some dialogue
                violations.append({
                    "scene_id": scene_id,
                    "character": name_lower.title(),
                    "dialogue_lines": dialogue_lines,
                    "reason": f"Character '{name_lower.title()}' has significant presence (emotional/dialogue) but is not in outline roster",
                })
                logger.warning(
                    "Character roster violation: %s in %s — significant presence, not in roster",
                    name_lower.title(), scene_id,
                )

    return violations
