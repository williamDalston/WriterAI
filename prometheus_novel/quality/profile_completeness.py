"""Character profile completeness checker — prevents entity drift by ensuring
character profiles have enough "authorized facts" before drafting begins.

Evaluates each major character against a genre-aware rubric and reports:
- completeness_score (0.0 - 1.0)
- missing_fields (list of what's absent)
- promptable_patch (block of text the LLM could fill in)

Config-driven via policy (warn / strict / off).
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("profile_completeness")

# Rubric: field name -> (weight, checker_function_name)
# Weight determines importance in the completeness score.
_RUBRIC = [
    ("full_name", 1.0, "Full character name"),
    ("age_or_life_stage", 0.5, "Age or life stage"),
    ("physical_description", 0.8, "Physical appearance"),
    ("backstory", 1.0, "Backstory / formative events"),
    ("personality_strengths", 0.6, "Personality strengths"),
    ("personality_flaws", 0.6, "Personality flaws"),
    ("voice_markers", 0.8, "Speech patterns / voice markers"),
    ("relationships_named", 1.0, "Named relationships to other characters"),
    ("goals_external", 0.7, "External goals (plot-level)"),
    ("goals_internal", 0.7, "Internal goals (character growth)"),
    ("arc", 0.8, "Character arc (start → end)"),
    ("signature_behaviors", 0.5, "Signature behaviors / physical tics"),
    ("family_network", 0.9, "Family members with NAMES (if they appear in story)"),
    ("constraints", 0.4, "What the character refuses to do"),
    ("location_anchors", 0.3, "Home base / workplace"),
]

# For "family_network" — keywords indicating family members
_FAMILY_KEYWORDS = re.compile(
    r"\b(brother|sister|mother|father|son|daughter|husband|wife|"
    r"sibling|parent|child|grandmother|grandfather|uncle|aunt|"
    r"cousin|nephew|niece|abuela|abuelo|mama|papa|mom|dad)\b",
    re.IGNORECASE,
)

# For detecting if a family mention has an actual NAME attached
_NAMED_FAMILY = re.compile(
    r"\b(brother|sister|mother|father|son|daughter|husband|wife|"
    r"sibling|parent|grandmother|grandfather|uncle|aunt|cousin|"
    r"nephew|niece|abuela|abuelo|mama|papa|mom|dad)\b"
    r"[^.!?]{0,30}\b([A-Z][a-z]{2,})\b",
    re.IGNORECASE,
)


def _check_field(character: dict, field_name: str, config: dict = None) -> bool:
    """Check if a specific rubric field is adequately populated."""

    if field_name == "full_name":
        name = character.get("name", "")
        # Should have at least a first and last name
        return bool(name) and len(name.split()) >= 2

    elif field_name == "age_or_life_stage":
        # Check name field, backstory, physical_description for age references
        all_text = _all_text(character)
        return bool(re.search(r"\b(\d{1,2}\s*(?:years? old|year-old)|young adult|middle.aged|teen|elderly|in (?:her|his|their) (?:twenties|thirties|forties|fifties))\b", all_text, re.IGNORECASE))

    elif field_name == "physical_description":
        desc = character.get("physical_description", "")
        return len(desc) >= 30  # At least a couple sentences

    elif field_name == "backstory":
        backstory = character.get("backstory", "")
        return len(backstory) >= 50

    elif field_name == "personality_strengths":
        personality = character.get("personality", {})
        if isinstance(personality, dict):
            strengths = personality.get("strengths", [])
            return isinstance(strengths, list) and len(strengths) >= 2
        return False

    elif field_name == "personality_flaws":
        personality = character.get("personality", {})
        if isinstance(personality, dict):
            flaws = personality.get("flaws", [])
            return isinstance(flaws, list) and len(flaws) >= 2
        return False

    elif field_name == "voice_markers":
        voice = character.get("voice", {})
        if isinstance(voice, dict):
            phrases = voice.get("phrases", [])
            vocab = voice.get("vocabulary", [])
            has_voice = (isinstance(phrases, list) and len(phrases) >= 1) or \
                        (isinstance(vocab, list) and len(vocab) >= 1)
            return has_voice
        return False

    elif field_name == "relationships_named":
        rels = character.get("relationships", {})
        if isinstance(rels, dict):
            return len(rels) >= 1
        return False

    elif field_name == "goals_external":
        goals = character.get("goals", {})
        if isinstance(goals, dict):
            ext = goals.get("external", [])
            return isinstance(ext, list) and len(ext) >= 1
        return False

    elif field_name == "goals_internal":
        goals = character.get("goals", {})
        if isinstance(goals, dict):
            internal = goals.get("internal", [])
            return isinstance(internal, list) and len(internal) >= 1
        return False

    elif field_name == "arc":
        arc = character.get("arc", "")
        return len(str(arc)) >= 20

    elif field_name == "signature_behaviors":
        behaviors = character.get("signature_behaviors", [])
        return isinstance(behaviors, list) and len(behaviors) >= 1

    elif field_name == "family_network":
        all_text = _all_text(character)
        # If family is mentioned, check that names are provided
        has_family_mention = bool(_FAMILY_KEYWORDS.search(all_text))
        if not has_family_mention:
            return True  # No family mentioned = not applicable = pass
        has_named = bool(_NAMED_FAMILY.search(all_text))
        return has_named

    elif field_name == "constraints":
        all_text = _all_text(character)
        return bool(re.search(r"\b(refuses?|won'?t|never|cannot|avoid|reject|unwilling)\b", all_text, re.IGNORECASE))

    elif field_name == "location_anchors":
        all_text = _all_text(character)
        return bool(re.search(r"\b(apartment|house|office|home|work|lives in|based in|NYC|New York|firm)\b", all_text, re.IGNORECASE))

    return False


def _all_text(character: dict) -> str:
    """Concatenate all text fields of a character for broad searches."""
    parts = []
    for key, val in character.items():
        if isinstance(val, str):
            parts.append(val)
        elif isinstance(val, dict):
            for v in val.values():
                if isinstance(v, str):
                    parts.append(v)
                elif isinstance(v, list):
                    parts.extend(str(x) for x in v)
        elif isinstance(val, list):
            parts.extend(str(x) for x in val)
    return " ".join(parts)


def check_character_completeness(
    character: dict,
    config: dict = None,
) -> Dict[str, Any]:
    """Check a single character profile against the completeness rubric.

    Returns:
        Dict with: name, role, completeness_score, present_fields, missing_fields.
    """
    name = character.get("name", "Unknown")
    role = character.get("role", "unknown")

    present = []
    missing = []
    total_weight = 0.0
    earned_weight = 0.0

    for field_name, weight, description in _RUBRIC:
        total_weight += weight
        if _check_field(character, field_name, config):
            present.append({"field": field_name, "description": description})
            earned_weight += weight
        else:
            missing.append({"field": field_name, "description": description, "weight": weight})

    score = earned_weight / total_weight if total_weight > 0 else 0.0

    return {
        "name": name,
        "role": role,
        "completeness_score": round(score, 2),
        "present_count": len(present),
        "missing_count": len(missing),
        "total_fields": len(_RUBRIC),
        "present_fields": present,
        "missing_fields": missing,
    }


def check_all_profiles(
    characters: List[Dict[str, Any]],
    min_score: float = 0.80,
    config: dict = None,
) -> Dict[str, Any]:
    """Check all character profiles and return a comprehensive report.

    Args:
        characters: List of character profile dicts.
        min_score: Minimum completeness score to pass.
        config: Optional project config for genre-aware checks.

    Returns:
        Report dict with per-character results and overall pass/fail.
    """
    if not characters:
        return {
            "pass": False,
            "reason": "No character profiles found",
            "profiles": [],
            "overall_score": 0.0,
        }

    results = []
    for char in characters:
        if not isinstance(char, dict):
            continue
        result = check_character_completeness(char, config)
        results.append(result)

    if not results:
        return {
            "pass": False,
            "reason": "No valid character profiles",
            "profiles": [],
            "overall_score": 0.0,
        }

    # Only major characters (protagonist, love_interest, antagonist) must meet threshold
    major_roles = {"protagonist", "love_interest", "antagonist", "main character"}
    major_results = [r for r in results if r["role"].lower() in major_roles]
    if not major_results:
        # If no explicit roles, check top 3 by profile size
        major_results = sorted(results, key=lambda r: -r["completeness_score"])[:3]

    overall_score = sum(r["completeness_score"] for r in results) / len(results)
    major_pass = all(r["completeness_score"] >= min_score for r in major_results)
    all_pass = all(r["completeness_score"] >= min_score * 0.7 for r in results)

    return {
        "pass": major_pass,
        "overall_score": round(overall_score, 2),
        "major_characters_pass": major_pass,
        "all_characters_pass": all_pass,
        "min_score_threshold": min_score,
        "profiles": results,
        "patch_needed": [
            r["name"] for r in results if r["completeness_score"] < min_score
        ],
    }


def build_patch_prompt(character: dict, missing_fields: List[Dict]) -> str:
    """Build a prompt to generate missing profile fields for a character.

    Returns a prompt string that can be sent to an LLM to fill in gaps.
    """
    name = character.get("name", "Unknown")
    role = character.get("role", "unknown")
    existing = _all_text(character)[:500]  # Context from existing profile

    field_list = "\n".join(f"- {m['description']}" for m in missing_fields)

    return f"""Complete the following character profile fields for {name} ({role}).

EXISTING PROFILE CONTEXT:
{existing}

MISSING FIELDS (fill in each one):
{field_list}

RULES:
- Be specific and concrete. Use actual names, not "his brother" or "her friend."
- If mentioning family members, give them first AND last names.
- Voice markers: give 3-5 specific words/phrases this character uses often.
- Constraints: what does this character refuse to do? What lines won't they cross?
- Keep each answer to 1-3 sentences.

Output as a JSON object with field names as keys."""


def format_completeness_report(report: Dict[str, Any]) -> str:
    """Format a completeness report as human-readable text."""
    lines = [
        "=== CHARACTER PROFILE COMPLETENESS ===",
        f"Overall score: {report['overall_score']:.0%}",
        f"Pass: {'YES' if report['pass'] else 'NO'}",
        f"Threshold: {report.get('min_score_threshold', 0.80):.0%}",
    ]

    for r in report.get("profiles", []):
        status = "PASS" if r["completeness_score"] >= report.get("min_score_threshold", 0.80) else "FAIL"
        lines.append(f"\n  {r['name']} ({r['role']}): {r['completeness_score']:.0%} [{status}]")
        lines.append(f"    Present: {r['present_count']}/{r['total_fields']}")
        if r["missing_fields"]:
            missing_names = [m["description"] for m in r["missing_fields"]]
            lines.append(f"    Missing: {', '.join(missing_names)}")

    if report.get("patch_needed"):
        lines.append(f"\n  Patch needed for: {', '.join(report['patch_needed'])}")

    return "\n".join(lines)
