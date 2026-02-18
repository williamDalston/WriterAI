"""Dialogue concreteness checker — detects thesis-statement dialogue.

Catches dialogue lines that are pure abstraction/philosophy without grounding:
  - "Data never lies, but people do." (aphorism)
  - "Truth is a double-edged sword." (concept statement)
  - "You can't control fate." (abstract rhetoric)

Complements check_therapy_speak() (clinical language) and
check_dialogue_tidy() (too-polished dialogue).
"""

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Abstract noun and concrete anchor sets
# ---------------------------------------------------------------------------

_ABSTRACT_NOUNS = frozenset({
    "truth", "power", "justice", "freedom", "trust", "loyalty",
    "fear", "hope", "fate", "destiny", "reality", "control",
    "knowledge", "data", "information", "corruption", "system",
    "order", "chaos", "balance", "choice", "sacrifice", "duty",
    "honor", "vengeance", "redemption", "salvation", "love",
    "beauty", "meaning", "purpose", "progress", "nature",
    "innocence", "guilt", "mercy", "strength", "weakness",
    "courage", "wisdom", "time", "death", "life",
})

_CONCRETE_ANCHORS = frozenset({
    # Objects
    "door", "gun", "phone", "car", "table", "chair", "window",
    "knife", "key", "badge", "bottle", "glass", "book", "letter",
    "bag", "box", "file", "screen", "camera", "rope", "card",
    "ring", "clock", "wallet", "lighter", "cigarette", "pill",
    # Body parts
    "hand", "face", "eyes", "blood", "finger", "arm", "shoulder",
    "mouth", "lip", "jaw", "throat", "chest", "stomach", "knee",
    # Money/specifics
    "money", "dollar", "cash", "coin", "check",
    # Actions (concrete verbs)
    "grabbed", "punched", "ran", "drove", "pulled", "pushed",
    "kicked", "threw", "dropped", "slammed", "locked", "broke",
    "poured", "ate", "drank", "shot", "stabbed", "burned",
})

# ---------------------------------------------------------------------------
# Aphorism patterns (subject + copula + abstract)
# ---------------------------------------------------------------------------

_APHORISM_PATTERNS = [
    # "[Abstract] is/are [modifier]? [abstract]"
    re.compile(
        r"\b(?:truth|love|power|justice|freedom|trust|loyalty|fear|hope|fate|"
        r"destiny|reality|life|death|time|knowledge|data|information|control|"
        r"order|chaos|balance|choice|sacrifice|duty|honor|courage|wisdom)"
        r"\s+(?:is|are|was|were)\s+(?:a\s+)?(?:\w+\s+){0,2}"
        r"(?:weapon|shield|currency|poison|gift|curse|burden|choice|illusion|"
        r"game|trap|prison|key|door|mirror|sword|tool|lie|commodity|luxury|"
        r"weakness|strength|double.edged\s+sword|necessary\s+evil)",
        re.IGNORECASE,
    ),
    # "You can't [verb] [abstract]"
    re.compile(
        r"\byou\s+(?:can'?t|cannot|couldn'?t)\s+"
        r"(?:control|stop|fight|escape|ignore|hide\s+from|run\s+from|"
        r"change|trust|outrun|cheat|bargain\s+with)\s+"
        r"(?:truth|fate|destiny|reality|the\s+future|the\s+past|love|"
        r"power|time|death|nature|progress|justice|change)",
        re.IGNORECASE,
    ),
    # "The only [abstract] that matters"
    re.compile(
        r"\bthe\s+only\s+(?:thing|truth|question|answer|choice|option|"
        r"power|weapon|way|path|solution)\s+(?:that\s+)?"
        r"(?:matters|counts|remains|works|lasts)\b",
        re.IGNORECASE,
    ),
    # "In the end, [abstract]"
    re.compile(
        r"\b(?:in\s+the\s+end|at\s+the\s+end\s+of\s+the\s+day|"
        r"when\s+all\s+is\s+said\s+and\s+done|when\s+it\s+comes\s+down\s+to\s+it)"
        r"\s*,?\s*(?:all\s+(?:that\s+)?(?:matters|remains|counts)|"
        r"we\s+(?:all|only)\s+(?:have|want|need))\b",
        re.IGNORECASE,
    ),
    # "People [verb] what they [verb]" / "Everyone [verb]"
    re.compile(
        r"\b(?:people|everyone|we\s+all|nobody|no\s+one)\s+"
        r"(?:want|fear|need|choose|deserve|become|believe|forget|remember)\s+"
        r"(?:what|who|the\s+(?:truth|things|answers|power))\b",
        re.IGNORECASE,
    ),
]

# Dialogue extraction
_DIALOGUE_LINE_RE = re.compile(r'["\u201c]([^"\u201d]{8,})["\u201d]')


def _extract_dialogue_lines(content: str) -> List[str]:
    """Extract dialogue lines (>= 8 chars) from scene content."""
    return [m.group(1).strip() for m in _DIALOGUE_LINE_RE.finditer(content)]


def _is_abstract_line(line: str) -> bool:
    """Check if a dialogue line is predominantly abstract (no concrete anchors)."""
    words = set(re.findall(r"\b[a-z]+\b", line.lower()))
    abstract_count = len(words & _ABSTRACT_NOUNS)
    concrete_count = len(words & _CONCRETE_ANCHORS)
    # Abstract if 2+ abstract nouns and 0 concrete anchors
    return abstract_count >= 2 and concrete_count == 0


def _is_aphorism(line: str) -> bool:
    """Check if a dialogue line matches an aphorism pattern."""
    for pat in _APHORISM_PATTERNS:
        if pat.search(line):
            return True
    return False


def check_dialogue_concreteness(
    content: str,
    scene_id: str = "",
    abstract_threshold: float = 0.40,
) -> Dict[str, Any]:
    """Check dialogue lines for abstract rhetoric vs concrete speech.

    Args:
        content: Scene prose text.
        scene_id: Scene identifier for reporting.
        abstract_threshold: Max ratio of abstract lines before flagging.

    Returns:
        {
            "pass": bool,
            "violations": [{type, severity, line, scene_id}],
            "abstract_ratio": float,
            "total_dialogue_lines": int,
            "aphorism_count": int,
            "abstract_count": int,
        }
    """
    lines = _extract_dialogue_lines(content)
    if not lines:
        return {
            "pass": True,
            "violations": [],
            "abstract_ratio": 0.0,
            "total_dialogue_lines": 0,
            "aphorism_count": 0,
            "abstract_count": 0,
        }

    violations: List[Dict[str, Any]] = []
    aphorisms = []
    abstract_lines = []

    for line in lines:
        if _is_aphorism(line):
            aphorisms.append(line)
            violations.append({
                "type": "THESIS_STATEMENT_DIALOGUE",
                "severity": "medium",
                "line": line[:100] + ("..." if len(line) > 100 else ""),
                "scene_id": scene_id,
                "message": f"Aphorism in dialogue: \"{line[:80]}...\"" if len(line) > 80 else f"Aphorism in dialogue: \"{line}\"",
            })
        elif _is_abstract_line(line):
            abstract_lines.append(line)

    # Check for aphorism cluster (3+ in one scene = TED talk)
    if len(aphorisms) >= 3:
        violations.append({
            "type": "APHORISM_CLUSTER",
            "severity": "high",
            "line": "",
            "scene_id": scene_id,
            "message": (
                f"{len(aphorisms)} aphoristic dialogue lines in one scene "
                f"(characters sound like a thesis defense)"
            ),
        })

    # Check abstract ratio
    total_abstract = len(aphorisms) + len(abstract_lines)
    abstract_ratio = total_abstract / len(lines) if lines else 0.0

    if abstract_ratio > abstract_threshold and len(lines) >= 4:
        violations.append({
            "type": "ABSTRACT_DIALOGUE_RATIO",
            "severity": "medium",
            "line": "",
            "scene_id": scene_id,
            "message": (
                f"{abstract_ratio:.0%} of dialogue is abstract "
                f"({total_abstract}/{len(lines)} lines lack concrete anchors)"
            ),
        })

    # Pass fails on high-severity violations
    high = [v for v in violations if v["severity"] in ("high", "critical")]
    return {
        "pass": len(high) == 0,
        "violations": violations,
        "abstract_ratio": round(abstract_ratio, 3),
        "total_dialogue_lines": len(lines),
        "aphorism_count": len(aphorisms),
        "abstract_count": len(abstract_lines),
    }


def batch_check_dialogue(
    scenes: List[Dict],
    abstract_threshold: float = 0.40,
) -> Dict[str, Any]:
    """Run dialogue concreteness check across all scenes.

    Returns:
        {
            "pass": bool,
            "total_violations": int,
            "scenes_with_issues": int,
            "total_scenes": int,
            "total_aphorisms": int,
            "avg_abstract_ratio": float,
            "violations": [all violations],
        }
    """
    all_violations: List[Dict] = []
    scenes_with_issues = 0
    total_aphorisms = 0
    abstract_ratios = []

    for scene in (scenes or []):
        if not isinstance(scene, dict):
            continue
        content = scene.get("content", "")
        if not content:
            continue

        scene_id = scene.get("scene_id", "")
        report = check_dialogue_concreteness(
            content, scene_id, abstract_threshold,
        )

        if not report["pass"] or report["violations"]:
            scenes_with_issues += 1
            all_violations.extend(report["violations"])

        total_aphorisms += report["aphorism_count"]
        if report["total_dialogue_lines"] > 0:
            abstract_ratios.append(report["abstract_ratio"])

    avg_ratio = (
        sum(abstract_ratios) / len(abstract_ratios)
        if abstract_ratios else 0.0
    )

    return {
        "pass": all(v["severity"] != "high" for v in all_violations),
        "total_violations": len(all_violations),
        "scenes_with_issues": scenes_with_issues,
        "total_scenes": len(scenes or []),
        "total_aphorisms": total_aphorisms,
        "avg_abstract_ratio": round(avg_ratio, 3),
        "violations": all_violations,
    }


def format_dialogue_report(report: Dict[str, Any]) -> str:
    """Human-readable dialogue concreteness report."""
    lines = ["=== DIALOGUE CONCRETENESS REPORT ==="]
    lines.append(f"Pass: {'YES' if report.get('pass') else 'NO'}")
    lines.append(
        f"Scenes with issues: {report.get('scenes_with_issues', 0)}"
        f"/{report.get('total_scenes', 0)}"
    )
    lines.append(f"Total aphorisms: {report.get('total_aphorisms', 0)}")
    lines.append(f"Avg abstract ratio: {report.get('avg_abstract_ratio', 0):.1%}")

    for v in report.get("violations", [])[:10]:
        lines.append(f"  [{v['severity'].upper()}] {v.get('scene_id', '?')}: {v['message']}")

    if len(report.get("violations", [])) > 10:
        lines.append(f"  ... and {len(report['violations']) - 10} more")

    return "\n".join(lines)
