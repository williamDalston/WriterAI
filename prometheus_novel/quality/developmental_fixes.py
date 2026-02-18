"""Developmental Fixes — targeted passes driven by developmental_audit findings.

Fix strategies:
- PASSIVE_HOTSPOT → reduce passive voice in flagged scenes (LLM)
- THEME_ABSENT_LATE → add one theme-resonant line (LLM)
- MISSING_BEAT → suggest beat insertion (report-only or LLM draft)

These run after developmental_audit; only fixable findings trigger passes.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("developmental_fixes")

# Pass prompts for fixable finding types
PASS_PASSIVE_REDUCE = """=== TASK: Reduce passive voice ===
This scene has too many passive constructions (e.g. "was held", "is carried", "are made").

Convert 3–5 passive phrases to active voice. Preserve meaning and tone.
Example: "The door was opened by him" → "He opened the door"

Do NOT rewrite the whole scene. Only change the flagged constructions.
Output the FULL scene with your edits."""

PASS_THEME_PLANT = """=== TASK: Add theme resonance ===
The central question is: {central_question}

Add ONE sentence (inline, natural) that reinforces this theme.
Weave it into existing prose. Do not add a new paragraph.
Output the FULL scene with your addition."""

PASS_CONFUSION_CLARIFY = """=== TASK: Clarify confusing moment ===
A fresh reader found this confusing: {issue}

Add ONE clarifying sentence or tweak the existing prose so the confusion is resolved.
Do NOT add a new paragraph. Weave the fix in naturally.
Output the FULL scene with your fix."""

PASS_MOTIVATION_GROUND = """=== TASK: Ground character motivation ===
A fresh reader found this unmotivated: {issue}
Character: {character}

Add ONE sentence that makes the character's choice or action feel motivated.
Weave it inline. Do not add a new paragraph.
Output the FULL scene with your addition."""


async def run_passive_reduce(
    client: Any,
    scene: Dict,
    config: Dict,
) -> Optional[str]:
    """Run passive-voice reduction on one scene."""
    if not client:
        return None
    content = scene.get("content", "") or ""
    if not content:
        return content

    scene_id = scene.get("scene_id") or f"ch{scene.get('chapter',0):02d}_s{scene.get('scene_number',0):02d}"
    prompt = f"""You are a copy editor. Fix passive voice only.

Scene ID: {scene_id}

{PASS_PASSIVE_REDUCE}

=== CURRENT SCENE ===
{content}

=== OUTPUT ===
Return ONLY the revised scene text. No commentary."""

    try:
        response = await client.generate(prompt, max_tokens=4000, temperature=0.2)
        if response and response.content:
            return response.content.strip()
    except Exception as e:
        logger.warning("Passive reduce failed for %s: %s", scene_id, e)
    return None


async def run_confusion_clarify(
    client: Any,
    scene: Dict,
    issue: str,
    config: Dict,
) -> Optional[str]:
    """Add clarifying line for confused reader."""
    if not client or not issue:
        return None
    content = scene.get("content", "") or ""
    if not content:
        return content

    scene_id = scene.get("scene_id") or f"ch{scene.get('chapter',0):02d}_s{scene.get('scene_number',0):02d}"
    task = PASS_CONFUSION_CLARIFY.format(issue=issue)
    prompt = f"""You are a developmental editor. Clarify for the reader.

Scene ID: {scene_id}

{task}

=== CURRENT SCENE ===
{content}

=== OUTPUT ===
Return ONLY the revised scene text. No commentary."""

    try:
        response = await client.generate(prompt, max_tokens=4000, temperature=0.3)
        if response and response.content:
            return response.content.strip()
    except Exception as e:
        logger.warning("Confusion clarify failed for %s: %s", scene_id, e)
    return None


async def run_motivation_ground(
    client: Any,
    scene: Dict,
    issue: str,
    character: str,
    config: Dict,
) -> Optional[str]:
    """Add motivation-grounding line."""
    if not client or not issue:
        return None
    content = scene.get("content", "") or ""
    if not content:
        return content

    scene_id = scene.get("scene_id") or f"ch{scene.get('chapter',0):02d}_s{scene.get('scene_number',0):02d}"
    task = PASS_MOTIVATION_GROUND.format(issue=issue, character=character or "character")
    prompt = f"""You are a developmental editor. Ground motivation.

Scene ID: {scene_id}

{task}

=== CURRENT SCENE ===
{content}

=== OUTPUT ===
Return ONLY the revised scene text. No commentary."""

    try:
        response = await client.generate(prompt, max_tokens=4000, temperature=0.3)
        if response and response.content:
            return response.content.strip()
    except Exception as e:
        logger.warning("Motivation ground failed for %s: %s", scene_id, e)
    return None


async def run_theme_plant(
    client: Any,
    scene: Dict,
    central_question: str,
    config: Dict,
) -> Optional[str]:
    """Add one theme-resonant line to scene."""
    if not client or not central_question:
        return None
    content = scene.get("content", "") or ""
    if not content:
        return content

    scene_id = scene.get("scene_id") or f"ch{scene.get('chapter',0):02d}_s{scene.get('scene_number',0):02d}"
    task = PASS_THEME_PLANT.format(central_question=central_question)
    prompt = f"""You are a developmental editor. Add theme resonance.

Scene ID: {scene_id}

{task}

=== CURRENT SCENE ===
{content}

=== OUTPUT ===
Return ONLY the revised scene text. No commentary."""

    try:
        response = await client.generate(prompt, max_tokens=4000, temperature=0.4)
        if response and response.content:
            return response.content.strip()
    except Exception as e:
        logger.warning("Theme plant failed for %s: %s", scene_id, e)
    return None


def _validate_output(original: str, new_content: str, max_ratio: float = 1.2) -> bool:
    """Reject outputs that balloon."""
    if not new_content or len(new_content.strip()) < 50:
        return False
    ow = len(original.split())
    nw = len(new_content.split())
    return ow == 0 or nw <= ow * max_ratio


async def run_developmental_fixes(
    scenes: List[Dict],
    audit_report: Dict[str, Any],
    client: Any,
    config: Dict,
    *,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Run fix passes for fixable developmental findings.

    Args:
        scenes: Scene list (modified in-place unless dry_run)
        audit_report: Output from run_developmental_audit
        client: LLM client
        config: Project config
        dry_run: If True, do not modify scenes, only return planned fixes

    Returns:
        Report with fixes_applied, scenes_modified, errors.
    """
    report = {
        "fixes_planned": [],
        "fixes_applied": 0,
        "scenes_modified": 0,
        "errors": [],
    }

    findings = audit_report.get("findings", [])
    fixable = [f for f in findings if f.get("code") in (
        "PASSIVE_HOTSPOT", "THEME_ABSENT_LATE", "CONFUSION", "UNCLEAR_MOTIVATION"
    )]
    if not fixable:
        return report

    scene_by_id = {}
    for s in scenes or []:
        if isinstance(s, dict):
            sid = s.get("scene_id") or f"ch{int(s.get('chapter',0)):02d}_s{int(s.get('scene_number') or s.get('scene',0)):02d}"
            scene_by_id[(sid or "").lower()] = s

    central_question = (config.get("central_question") or "").strip()

    # For THEME_ABSENT_LATE (no scene_id), pick first scene in final third
    theme_scene_id = None
    if any(f.get("code") == "THEME_ABSENT_LATE" for f in fixable):
        later_start = int(len(scenes or []) * 2 / 3)
        for s in (scenes or [])[later_start:]:
            if isinstance(s, dict) and (s.get("content") or "").strip():
                theme_scene_id = (s.get("scene_id") or f"ch{int(s.get('chapter',0)):02d}_s{int(s.get('scene_number') or s.get('scene',0)):02d}").lower()
                break

    for finding in fixable:
        code = finding.get("code")
        scene_id = finding.get("scene_id") or (theme_scene_id if code == "THEME_ABSENT_LATE" else None)
        if not scene_id:
            continue
        sid_key = scene_id.lower() if isinstance(scene_id, str) else scene_id
        if sid_key not in scene_by_id:
            continue

        scene = scene_by_id.get(sid_key)
        if not scene or not scene.get("content"):
            continue

        report["fixes_planned"].append({"code": code, "scene_id": scene_id})

        if dry_run:
            continue

        orig = scene.get("content", "")
        new_content = None

        if code == "PASSIVE_HOTSPOT":
            new_content = await run_passive_reduce(client, scene, config)
        elif code == "THEME_ABSENT_LATE" and central_question:
            new_content = await run_theme_plant(client, scene, central_question, config)
        elif code == "CONFUSION":
            issue = finding.get("issue") or (finding.get("message", "").split(": ", 1)[-1] if finding.get("message") else "")
            new_content = await run_confusion_clarify(client, scene, issue, config)
        elif code == "UNCLEAR_MOTIVATION":
            issue = finding.get("issue") or (finding.get("message", "") or "").split("): ", 1)[-1]
            char = finding.get("character", "")
            new_content = await run_motivation_ground(client, scene, issue, char, config)

        if new_content and new_content != orig and _validate_output(orig, new_content):
            scene["content"] = new_content
            report["fixes_applied"] += 1
            report["scenes_modified"] += 1

    return report
