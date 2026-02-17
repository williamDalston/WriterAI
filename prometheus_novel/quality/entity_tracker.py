"""Cross-scene entity consistency tracker — detects name/relationship contradictions.

Scans all drafted scenes for `[Name]'s [relationship]` patterns and flags:
1. ENTITY_RENAME: same relationship role has different names across scenes
   (e.g., "Marco's brother Luca" in ch3 vs "Marco's brother Matteo" in ch18)
2. ENTITY_ROLE_CONFLICT: same name assigned conflicting roles
   (e.g., "Sofia, his sister" in ch5 vs "Sofia, his ex-wife" in ch12)

Runs AFTER scene drafting, before final polish. Non-blocking (quality warning).
"""

import logging
import re
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("entity_tracker")

# Patterns to extract entity-relationship pairs
# Pattern A: "Name's relationship" — e.g., "Marco's brother"
_POSSESSIVE_REL = re.compile(
    r"\b([A-Z][a-z]{2,})'s\s+"
    r"(brother|sister|mother|father|son|daughter|husband|wife|"
    r"aunt|uncle|cousin|grandmother|grandfather|"
    r"partner|fiancé|fiancée|fiance|fiancee|"
    r"ex-wife|ex-husband|ex-boyfriend|ex-girlfriend|"
    r"best friend|friend|lover|mentor|boss|"
    r"stepmother|stepfather|stepbrother|stepsister)\b"
    r"(?:\s*,?\s*\b([A-Z][a-z]{2,})\b)?",
    re.IGNORECASE,
)

# Pattern B: "Name, his/her relationship" — e.g., "Luca, his brother"
_APPOSITIVE_REL = re.compile(
    r"\b([A-Z][a-z]{2,})\b\s*,\s*"
    r"(?:his|her|their)\s+"
    r"(brother|sister|mother|father|son|daughter|husband|wife|"
    r"aunt|uncle|cousin|grandmother|grandfather|"
    r"partner|fiancé|fiancée|fiance|fiancee|"
    r"ex-wife|ex-husband|ex-boyfriend|ex-girlfriend|"
    r"best friend|friend|lover|mentor|boss|"
    r"stepmother|stepfather|stepbrother|stepsister)\b",
)

# Pattern C: "his/her relationship Name" — e.g., "her brother Luca"
_PRONOUN_REL_NAME = re.compile(
    r"\b(?:his|her|their)\s+"
    r"(brother|sister|mother|father|son|daughter|husband|wife|"
    r"aunt|uncle|cousin|grandmother|grandfather|"
    r"partner|fiancé|fiancée|fiance|fiancee|"
    r"ex-wife|ex-husband|ex-boyfriend|ex-girlfriend|"
    r"best friend|friend|lover|mentor|boss|"
    r"stepmother|stepfather|stepbrother|stepsister)\b"
    r"\s*,?\s*\b([A-Z][a-z]{2,})\b",
)


def _normalize_role(role: str) -> str:
    """Normalize a relationship role for comparison."""
    role = role.lower().strip()
    # Normalize variants
    role = role.replace("fiancée", "fiance").replace("fiancé", "fiance")
    role = role.replace("fiancee", "fiance")
    role = role.replace("best friend", "friend")
    return role


def extract_entity_pairs(
    text: str,
    scene_id: str = "",
) -> List[Dict[str, str]]:
    """Extract entity-relationship pairs from a scene text.

    Returns list of dicts: {owner, role, name, scene_id, pattern}.
    """
    pairs = []

    # Pattern A: "Marco's brother Luca"
    for m in _POSSESSIVE_REL.finditer(text):
        owner = m.group(1)
        role = m.group(2)
        name = m.group(3)  # May be None if no name follows
        pairs.append({
            "owner": owner,
            "role": _normalize_role(role),
            "name": name if name else "",
            "scene_id": scene_id,
            "pattern": "possessive",
        })

    # Pattern B: "Luca, his brother" — here Luca IS the relationship
    for m in _APPOSITIVE_REL.finditer(text):
        name = m.group(1)
        role = m.group(2)
        pairs.append({
            "owner": "",  # Owner is the pronoun referent (unknown without context)
            "role": _normalize_role(role),
            "name": name,
            "scene_id": scene_id,
            "pattern": "appositive",
        })

    # Pattern C: "her brother Luca"
    for m in _PRONOUN_REL_NAME.finditer(text):
        role = m.group(1)
        name = m.group(2)
        pairs.append({
            "owner": "",  # Owner is the pronoun referent
            "role": _normalize_role(role),
            "name": name,
            "scene_id": scene_id,
            "pattern": "pronoun_rel",
        })

    return pairs


def check_entity_consistency(
    scenes: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Check entity consistency across all drafted scenes.

    Args:
        scenes: List of scene dicts with 'content' and optional 'scene_id'.

    Returns:
        Report dict with violations and entity registry.
    """
    # Collect all pairs across all scenes
    all_pairs: List[Dict[str, str]] = []
    for scene in (scenes or []):
        if not isinstance(scene, dict):
            continue
        content = scene.get("content", "")
        if not content:
            continue
        scene_id = scene.get("scene_id", f"scene_{len(all_pairs)}")
        pairs = extract_entity_pairs(content, scene_id)
        all_pairs.extend(pairs)

    if not all_pairs:
        return {
            "pass": True,
            "violations": [],
            "entity_count": 0,
            "pair_count": 0,
        }

    violations: List[Dict[str, Any]] = []

    # --- Check 1: ENTITY_RENAME ---
    # Group by (owner, role) → set of names
    # If the same owner+role maps to different names, flag it.
    owner_role_names: Dict[Tuple[str, str], Dict[str, List[str]]] = {}
    for p in all_pairs:
        if not p["owner"] or not p["name"]:
            continue
        key = (p["owner"].lower(), p["role"])
        if key not in owner_role_names:
            owner_role_names[key] = {}
        name_lower = p["name"].lower()
        if name_lower not in owner_role_names[key]:
            owner_role_names[key][name_lower] = []
        owner_role_names[key][name_lower].append(p["scene_id"])

    for (owner, role), names_map in owner_role_names.items():
        if len(names_map) > 1:
            names_list = list(names_map.keys())
            violations.append({
                "type": "ENTITY_RENAME",
                "severity": "critical",
                "owner": owner,
                "role": role,
                "names_found": names_list,
                "scenes": {n: scenes for n, scenes in names_map.items()},
                "suggestion": f"{owner.title()}'s {role} is called "
                              f"{' AND '.join(names_list)} in different scenes. "
                              f"Pick one name and use it consistently.",
            })

    # --- Check 2: ENTITY_ROLE_CONFLICT ---
    # Group by name → set of roles (from all patterns)
    name_roles: Dict[str, Dict[str, List[str]]] = {}
    for p in all_pairs:
        if not p["name"]:
            continue
        name_lower = p["name"].lower()
        if name_lower not in name_roles:
            name_roles[name_lower] = {}
        role = p["role"]
        if role not in name_roles[name_lower]:
            name_roles[name_lower][role] = []
        name_roles[name_lower][role].append(p["scene_id"])

    # Only flag genuinely conflicting roles (not "friend" + "best friend")
    _COMPATIBLE_ROLES = {
        frozenset({"friend", "best friend"}),
        frozenset({"fiance", "husband"}),
        frozenset({"fiance", "wife"}),
        frozenset({"lover", "husband"}),
        frozenset({"lover", "wife"}),
        frozenset({"lover", "partner"}),
        frozenset({"boyfriend", "partner"}),
        frozenset({"girlfriend", "partner"}),
    }

    for name, roles_map in name_roles.items():
        if len(roles_map) <= 1:
            continue
        role_set = set(roles_map.keys())
        # Check if all role pairs are compatible
        conflicting = False
        roles_list = list(role_set)
        for i in range(len(roles_list)):
            for j in range(i + 1, len(roles_list)):
                pair = frozenset({roles_list[i], roles_list[j]})
                if pair not in _COMPATIBLE_ROLES:
                    conflicting = True
                    break
            if conflicting:
                break

        if conflicting:
            violations.append({
                "type": "ENTITY_ROLE_CONFLICT",
                "severity": "high",
                "name": name,
                "roles_found": list(role_set),
                "scenes": {r: scenes for r, scenes in roles_map.items()},
                "suggestion": f"{name.title()} is called both "
                              f"{' and '.join(role_set)} in different scenes. "
                              f"Clarify the correct relationship.",
            })

    # Build entity registry for downstream consumption
    entity_registry = {}
    for p in all_pairs:
        if p["name"]:
            name_lower = p["name"].lower()
            if name_lower not in entity_registry:
                entity_registry[name_lower] = {
                    "name": p["name"],
                    "roles": set(),
                    "scenes": set(),
                }
            entity_registry[name_lower]["roles"].add(p["role"])
            entity_registry[name_lower]["scenes"].add(p["scene_id"])

    # Convert sets to lists for JSON serialization
    for entry in entity_registry.values():
        entry["roles"] = sorted(entry["roles"])
        entry["scenes"] = sorted(entry["scenes"])

    critical = sum(1 for v in violations if v["severity"] == "critical")
    high = sum(1 for v in violations if v["severity"] == "high")

    return {
        "pass": critical == 0 and high == 0,
        "violations": violations,
        "critical_count": critical,
        "high_count": high,
        "entity_count": len(entity_registry),
        "pair_count": len(all_pairs),
        "entity_registry": entity_registry,
    }


def format_entity_report(report: Dict[str, Any]) -> str:
    """Format an entity consistency report as human-readable text."""
    lines = [
        "=== ENTITY CONSISTENCY REPORT ===",
        f"Entities tracked: {report['entity_count']}",
        f"Relationship pairs found: {report['pair_count']}",
        f"Pass: {'YES' if report['pass'] else 'NO'}",
        f"Violations: {report.get('critical_count', 0)} critical, {report.get('high_count', 0)} high",
    ]

    for v in report.get("violations", []):
        lines.append(f"\n  [{v['severity'].upper()}] {v['type']}")
        if v["type"] == "ENTITY_RENAME":
            lines.append(f"    {v['owner'].title()}'s {v['role']}: {' vs '.join(v['names_found'])}")
        elif v["type"] == "ENTITY_ROLE_CONFLICT":
            lines.append(f"    {v['name'].title()}: {' vs '.join(v['roles_found'])}")
        lines.append(f"    Fix: {v['suggestion']}")

    return "\n".join(lines)
