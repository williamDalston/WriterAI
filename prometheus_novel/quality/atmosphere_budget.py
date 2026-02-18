"""Atmospheric phrase family budgeting.

Catches conceptual repetition that exact n-gram matching misses:
  - "neon flickered" / "neon pulsed" / "neon cast shadows" = same concept
  - "ozone smell" / "petrichor" / "rain slicked" = same atmosphere
  - "heart pounded" / "pulse raced" / "blood surged" = same physical reaction

Groups related phrases into families with per-10k-word budgets.
Excess occurrences are replaced with alternatives (like sensory_motif_pass).
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default atmosphere families
# ---------------------------------------------------------------------------

ATMOSPHERE_FAMILIES: Dict[str, Dict[str, Any]] = {
    "neon_light": {
        "pattern": r"\bneon\b(?:\s+(?:flicker|pulse|glow|light|sign|buzz|hum|cast|wash|bath|lit|reflect|bleed|bled|spill|flash|blink))?(?:ed|ing|s)?\b",
        "budget_per_10k": 4,
        "replacements": [
            "the streetlight stuttered",
            "a sodium lamp buzzed overhead",
            "light from the sign bled across the wet pavement",
            "the display flickered once",
            "harsh fluorescent light",
        ],
    },
    "rain_weather": {
        "pattern": r"\b(?:rain\s+(?:fell|pattered|drummed|slicked|hammered|lashed|streaked)|(?:ozone|petrichor)\b|drizzle[ds]?\b|downpour\b|(?:puddle|gutter)\s+(?:water|overflow))",
        "budget_per_10k": 5,
        "replacements": [
            "water ran down the glass",
            "the street was slick underfoot",
            "moisture beaded on the window",
            "wet asphalt reflected headlights",
            "the air tasted of storm",
        ],
    },
    "heartbeat_pulse": {
        "pattern": r"\b(?:heart(?:beat)?\s+(?:pound|race|throb|hammer|thump|kick|surge|skip|stutter)|pulse\s+(?:race|pound|throb|kick|hammer|spike|quicken)|blood\s+(?:rush|surge|pound|roar|sing))(?:ed|ing|s)?\b",
        "budget_per_10k": 3,
        "replacements": [
            "adrenaline hit",
            "her breath came faster",
            "a jolt ran through her",
            "every nerve pulled taut",
            "the tension coiled tighter",
        ],
    },
    "bass_music": {
        "pattern": r"\b(?:bass\s+(?:thump|throb|pulse|boom|beat|drop|line|note)|beat\s+(?:pulse|throb|pound))(?:ed|ing|s)?\b",
        "budget_per_10k": 3,
        "replacements": [
            "music vibrated through the floor",
            "the sound system shook the walls",
            "a low frequency hummed in her chest",
            "the rhythm was more felt than heard",
        ],
    },
    "server_hum": {
        "pattern": r"\b(?:server|machine|circuit|processor|mainframe|terminal)\s+(?:hum|buzz|whir|drone|purr|click)(?:med|ming|zed|zing|red|ring|s)?\b",
        "budget_per_10k": 3,
        "replacements": [
            "cooling fans cycled somewhere below",
            "the rack LEDs blinked in sequence",
            "heat poured off the stacked hardware",
            "a status light turned amber",
        ],
    },
    "metallic_taste": {
        "pattern": r"\b(?:metallic\s+(?:tang|taste|scent|bite)|copper\s+(?:taste|tang|scent)|taste[ds]?\s+(?:metal|copper|blood|iron))\b",
        "budget_per_10k": 2,
        "replacements": [
            "something bitter at the back of her throat",
            "the air had a sharp chemical edge",
            "she swallowed hard",
            "her mouth went dry",
        ],
    },
    "darkness_shadow": {
        "pattern": r"\b(?:shadow|darkness|gloom)\s+(?:fell|spread|deepened|swallowed|crept|pooled|gathered|pressed|closed)(?:\s+in)?\b",
        "budget_per_10k": 4,
        "replacements": [
            "the light didn't reach here",
            "the corridor narrowed ahead",
            "visibility dropped to arm's length",
            "the only light came from her screen",
        ],
    },
    "silence_quiet": {
        "pattern": r"\b(?:silence\s+(?:fell|hung|stretched|filled|settled|pressed|returned|descended|thickened)|the\s+quiet\s+(?:pressed|settled|grew|deepened))\b",
        "budget_per_10k": 4,
        "replacements": [
            "neither of them spoke",
            "the room held its breath",
            "the only sound was the ventilation",
            "nothing moved",
            "she waited. He didn't answer.",
        ],
    },
    "city_pulse": {
        "pattern": r"\b(?:city'?s?\s+(?:pulse|heartbeat|rhythm|hum|breath|energy|veins|arteries)|urban\s+(?:pulse|rhythm|heartbeat))\b",
        "budget_per_10k": 3,
        "replacements": [
            "traffic noise filtered in from outside",
            "a siren wailed three blocks over",
            "somewhere a horn blared",
            "the usual street noise was absent",
        ],
    },
}


def _compile_family(family: Dict[str, Any]) -> re.Pattern:
    """Compile a family's pattern string into a regex."""
    return re.compile(family["pattern"], re.IGNORECASE)


def check_atmosphere_budget(
    scenes: List[Dict],
    families: Optional[Dict[str, Dict]] = None,
) -> Dict[str, Any]:
    """Check atmospheric phrase family usage against budgets.

    Args:
        scenes: List of scene dicts with "content" field.
        families: Override family definitions (default: ATMOSPHERE_FAMILIES).

    Returns:
        {
            "pass": bool,
            "violations": [{type, family, count, budget, excess, scenes}],
            "family_counts": {family: count},
            "total_words": int,
        }
    """
    families = families or ATMOSPHERE_FAMILIES
    if not scenes:
        return {
            "pass": True,
            "violations": [],
            "family_counts": {},
            "total_words": 0,
        }

    # Count total words
    total_words = 0
    for scene in scenes:
        if isinstance(scene, dict):
            content = scene.get("content", "")
            total_words += len(content.split())

    if total_words == 0:
        return {
            "pass": True,
            "violations": [],
            "family_counts": {},
            "total_words": 0,
        }

    units_10k = max(1, total_words / 10_000)

    # Count per family
    family_counts: Dict[str, int] = {}
    family_scenes: Dict[str, List[str]] = {}
    violations: List[Dict[str, Any]] = []

    for fam_name, fam_def in families.items():
        pat = _compile_family(fam_def)
        count = 0
        scene_ids = []

        for scene in scenes:
            if not isinstance(scene, dict):
                continue
            content = scene.get("content", "")
            if not content:
                continue
            hits = len(pat.findall(content))
            if hits > 0:
                count += hits
                scene_ids.append(scene.get("scene_id", "unknown"))

        family_counts[fam_name] = count
        family_scenes[fam_name] = scene_ids

        budget = int(fam_def.get("budget_per_10k", 5) * units_10k)
        if count > budget:
            violations.append({
                "type": "ATMOSPHERE_OVERUSE",
                "severity": "medium",
                "family": fam_name,
                "count": count,
                "budget": budget,
                "excess": count - budget,
                "scenes": scene_ids[:10],
                "message": (
                    f"{fam_name}: {count} occurrences "
                    f"(budget: {budget} for {total_words} words). "
                    f"Excess: {count - budget}"
                ),
            })

    return {
        "pass": len(violations) == 0,
        "violations": violations,
        "family_counts": family_counts,
        "total_words": total_words,
    }


def suppress_atmosphere_excess(
    scenes: List[Dict],
    families: Optional[Dict[str, Dict]] = None,
) -> Tuple[List[Dict], Dict[str, Any]]:
    """Replace excess atmospheric phrases beyond budget with alternatives.

    Keeps the first N (budget) occurrences and replaces the rest.
    Returns (modified_scenes, report).
    """
    families = families or ATMOSPHERE_FAMILIES
    report: Dict[str, Any] = {"replacements": {}, "total_replaced": 0}

    if not scenes:
        return scenes, report

    # Count total words for budget calculation
    total_words = sum(
        len(scene.get("content", "").split())
        for scene in scenes if isinstance(scene, dict)
    )
    if total_words == 0:
        return scenes, report

    units_10k = max(1, total_words / 10_000)

    for fam_name, fam_def in families.items():
        pat = _compile_family(fam_def)
        budget = int(fam_def.get("budget_per_10k", 5) * units_10k)
        replacements = fam_def.get("replacements", [])
        if not replacements:
            continue

        # Collect all matches across all scenes (with positions)
        all_matches: List[Tuple[int, int, int, str]] = []  # (scene_idx, start, end, text)
        for si, scene in enumerate(scenes):
            if not isinstance(scene, dict):
                continue
            content = scene.get("content", "")
            for m in pat.finditer(content):
                all_matches.append((si, m.start(), m.end(), m.group()))

        if len(all_matches) <= budget:
            continue

        # Keep first `budget` occurrences, replace the rest
        to_replace = all_matches[budget:]
        replace_count = 0
        rep_idx = 0

        # Group by scene and process in reverse order (preserve positions)
        by_scene: Dict[int, List[Tuple[int, int, str]]] = {}
        for si, start, end, text in to_replace:
            by_scene.setdefault(si, []).append((start, end, text))

        for si in sorted(by_scene.keys()):
            if not isinstance(scenes[si], dict):
                continue
            content = scenes[si].get("content", "")
            # Process in reverse order to preserve character positions
            for start, end, original in sorted(by_scene[si], key=lambda x: x[0], reverse=True):
                replacement = replacements[rep_idx % len(replacements)]
                rep_idx += 1

                # Preserve capitalization
                if original and original[0].isupper():
                    replacement = replacement[0].upper() + replacement[1:]

                content = content[:start] + replacement + content[end:]
                replace_count += 1

            scenes[si]["content"] = content

        if replace_count > 0:
            report["replacements"][fam_name] = {
                "total_found": len(all_matches),
                "kept": budget,
                "replaced": replace_count,
            }
            report["total_replaced"] += replace_count

    return scenes, report


def format_atmosphere_report(report: Dict[str, Any]) -> str:
    """Human-readable atmosphere budget report."""
    lines = ["=== ATMOSPHERE BUDGET REPORT ==="]
    lines.append(f"Pass: {'YES' if report.get('pass') else 'NO'}")
    lines.append(f"Total words: {report.get('total_words', 0):,}")

    fc = report.get("family_counts", {})
    if fc:
        lines.append("\nFamily usage:")
        for fam, count in sorted(fc.items(), key=lambda x: -x[1]):
            lines.append(f"  {fam}: {count}")

    for v in report.get("violations", []):
        lines.append(f"\n  [OVERUSE] {v['message']}")

    return "\n".join(lines)
