"""Paragraph-level POV consistency audit.

Catches pronoun drift that scene-level checks miss:
  - "I stared..." → "He swallowed..." → "She leaned..." in same paragraph
  - Mixed subject pronouns within non-dialogue narration

Complements _repair_pov_context_errors() (pattern-based repair) and
_validate_scene_output() (scene-level critic gate).
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Subject pronoun patterns (sentence-initial or after period/semicolon)
_FIRST_PERSON_SUBJECT = re.compile(
    r"(?:^|(?<=[.!?;]\s))I\s+(?:was|had|have|am|could|would|should|might|"
    r"will|did|do|felt|thought|knew|saw|heard|turned|walked|looked|said|"
    r"stared|grabbed|pulled|pushed|ran|stood|sat|leaned|reached|stepped|"
    r"tried|wanted|needed|couldn|didn|don|wasn|shouldn|wouldn|haven|"
    r"let|took|held|made|got|went|came|found|kept|set|put|gave|"
    r"told|asked|watched|noticed|realized|remembered|nodded|shook|"
    r"closed|opened|swallowed|breathed|whispered|muttered|snapped|"
    r"pressed|touched|gripped|clenched|raised|dropped|followed|"
    r"moved|started|stopped|paused|waited|glanced)\b",
    re.MULTILINE,
)

_THIRD_MALE_SUBJECT = re.compile(
    r"(?:^|(?<=[.!?;]\s))He\s+(?:was|had|have|could|would|should|might|"
    r"will|did|felt|thought|knew|saw|heard|turned|walked|looked|said|"
    r"stared|grabbed|pulled|pushed|ran|stood|sat|leaned|reached|stepped|"
    r"tried|wanted|needed|let|took|held|made|got|went|came|found|"
    r"told|asked|watched|noticed|realized|remembered|nodded|shook|"
    r"closed|opened|swallowed|breathed|whispered|muttered|snapped|"
    r"pressed|touched|gripped|clenched|raised|dropped|followed|"
    r"moved|started|stopped|paused|waited|glanced)\b",
    re.MULTILINE,
)

_THIRD_FEMALE_SUBJECT = re.compile(
    r"(?:^|(?<=[.!?;]\s))She\s+(?:was|had|have|could|would|should|might|"
    r"will|did|felt|thought|knew|saw|heard|turned|walked|looked|said|"
    r"stared|grabbed|pulled|pushed|ran|stood|sat|leaned|reached|stepped|"
    r"tried|wanted|needed|let|took|held|made|got|went|came|found|"
    r"told|asked|watched|noticed|realized|remembered|nodded|shook|"
    r"closed|opened|swallowed|breathed|whispered|muttered|snapped|"
    r"pressed|touched|gripped|clenched|raised|dropped|followed|"
    r"moved|started|stopped|paused|waited|glanced)\b",
    re.MULTILINE,
)

# Dialogue masking: remove quoted text before analysis
_DIALOGUE_RE = re.compile(r'["\u201c][^"\u201d]*["\u201d]')


def _mask_dialogue(text: str) -> str:
    """Replace dialogue with placeholder to avoid counting pronouns in speech."""
    return _DIALOGUE_RE.sub(" DIALOGUE ", text)


def _count_subject_pronouns(text: str) -> Dict[str, int]:
    """Count subject pronouns (I/He/She) as sentence subjects in narration."""
    masked = _mask_dialogue(text)
    return {
        "I": len(_FIRST_PERSON_SUBJECT.findall(masked)),
        "He": len(_THIRD_MALE_SUBJECT.findall(masked)),
        "She": len(_THIRD_FEMALE_SUBJECT.findall(masked)),
    }


def audit_pov_consistency(
    content: str,
    pov_character: str = "",
    pov_mode: str = "first",
) -> Dict[str, Any]:
    """Check paragraph-level POV pronoun consistency.

    Args:
        content: Scene prose text.
        pov_character: Name of the POV character (for context in messages).
        pov_mode: "first" (I-narration) or "third_limited" (He/She-narration).

    Returns:
        {
            "pass": bool,
            "violations": [{type, paragraph_index, pronouns_found, excerpt}],
            "paragraph_count": int,
            "clean_paragraphs": int,
        }
    """
    if not content or len(content) < 50:
        return {
            "pass": True,
            "violations": [],
            "paragraph_count": 0,
            "clean_paragraphs": 0,
        }

    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    violations: List[Dict[str, Any]] = []
    clean = 0

    for i, para in enumerate(paragraphs):
        if len(para) < 30:
            clean += 1
            continue

        counts = _count_subject_pronouns(para)

        if pov_mode == "first":
            # First-person: "I" is expected. He/She as subjects = drift
            has_i = counts["I"] > 0
            has_he = counts["He"] > 0
            has_she = counts["She"] > 0

            if has_i and (has_he or has_she):
                intruders = []
                if has_he:
                    intruders.append(f"He({counts['He']})")
                if has_she:
                    intruders.append(f"She({counts['She']})")
                violations.append({
                    "type": "POV_PARAGRAPH_DRIFT",
                    "severity": "high",
                    "paragraph_index": i,
                    "pronouns_found": ["I"] + [p.split("(")[0] for p in intruders],
                    "message": (
                        f"Paragraph {i+1}: first-person 'I' mixed with "
                        f"{', '.join(intruders)} as narration subjects"
                    ),
                    "excerpt": para[:120] + ("..." if len(para) > 120 else ""),
                })
            elif not has_i and (has_he or has_she) and (counts["He"] + counts["She"]) >= 2:
                # Entire paragraph slipped into third person
                violations.append({
                    "type": "POV_PARAGRAPH_DRIFT",
                    "severity": "high",
                    "paragraph_index": i,
                    "pronouns_found": (
                        (["He"] if has_he else []) +
                        (["She"] if has_she else [])
                    ),
                    "message": (
                        f"Paragraph {i+1}: expected first-person 'I' but found only "
                        f"third-person narration ({counts['He']} He, {counts['She']} She)"
                    ),
                    "excerpt": para[:120] + ("..." if len(para) > 120 else ""),
                })
            else:
                clean += 1

        elif pov_mode == "third_limited":
            # Third-limited: one of He/She is expected. "I" = drift
            has_i = counts["I"] > 0
            has_he = counts["He"] > 0
            has_she = counts["She"] > 0

            if has_i and (has_he or has_she):
                violations.append({
                    "type": "POV_PARAGRAPH_DRIFT",
                    "severity": "high",
                    "paragraph_index": i,
                    "pronouns_found": (
                        ["I"] +
                        (["He"] if has_he else []) +
                        (["She"] if has_she else [])
                    ),
                    "message": (
                        f"Paragraph {i+1}: third-limited POV mixed with "
                        f"first-person 'I' ({counts['I']} instances)"
                    ),
                    "excerpt": para[:120] + ("..." if len(para) > 120 else ""),
                })
            elif has_he and has_she and counts["He"] >= 2 and counts["She"] >= 2:
                # Both He and She used heavily — ambiguous POV
                violations.append({
                    "type": "POV_PARAGRAPH_DRIFT",
                    "severity": "medium",
                    "paragraph_index": i,
                    "pronouns_found": ["He", "She"],
                    "message": (
                        f"Paragraph {i+1}: both He({counts['He']}) and "
                        f"She({counts['She']}) used as subjects — ambiguous POV"
                    ),
                    "excerpt": para[:120] + ("..." if len(para) > 120 else ""),
                })
            else:
                clean += 1
        else:
            clean += 1

    return {
        "pass": len(violations) == 0,
        "violations": violations,
        "paragraph_count": len(paragraphs),
        "clean_paragraphs": clean,
    }


def batch_audit_pov(
    scenes: List[Dict],
    pov_mode: str = "first",
) -> Dict[str, Any]:
    """Run POV audit across all scenes.

    Args:
        scenes: List of scene dicts with "content" and optionally "pov" fields.
        pov_mode: Default POV mode for all scenes.

    Returns:
        {
            "pass": bool,
            "total_violations": int,
            "scenes_with_drift": int,
            "total_scenes": int,
            "violations": [all violations with scene_id added],
        }
    """
    all_violations: List[Dict] = []
    scenes_with_drift = 0

    for scene in (scenes or []):
        if not isinstance(scene, dict):
            continue
        content = scene.get("content", "")
        if not content:
            continue

        pov_char = scene.get("pov", "")
        scene_id = scene.get("scene_id", "")

        report = audit_pov_consistency(content, pov_char, pov_mode)
        if not report["pass"]:
            scenes_with_drift += 1
            for v in report["violations"]:
                v["scene_id"] = scene_id
                all_violations.append(v)

    return {
        "pass": len(all_violations) == 0,
        "total_violations": len(all_violations),
        "scenes_with_drift": scenes_with_drift,
        "total_scenes": len(scenes or []),
        "violations": all_violations,
    }


def format_pov_report(report: Dict[str, Any]) -> str:
    """Human-readable POV consistency report."""
    lines = ["=== POV CONSISTENCY REPORT ==="]
    lines.append(f"Pass: {'YES' if report.get('pass') else 'NO'}")
    lines.append(
        f"Scenes with drift: {report.get('scenes_with_drift', 0)}"
        f"/{report.get('total_scenes', 0)}"
    )

    for v in report.get("violations", [])[:10]:
        lines.append(
            f"  [{v.get('severity', '?').upper()}] {v.get('scene_id', '?')} "
            f"p{v.get('paragraph_index', '?')+1}: {v.get('message', '')}"
        )

    if len(report.get("violations", [])) > 10:
        lines.append(f"  ... and {len(report['violations']) - 10} more")

    return "\n".join(lines)
