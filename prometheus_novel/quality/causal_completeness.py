"""Causal completeness audit — flags secrets/reveals that never explain WHAT.

When characters react emotionally to a secret (file, case, past event) but
the reader never learns what actually happened, the plot engine is hollow.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Patterns that suggest a secret/reveal is referenced
_SECRET_REF_PATTERNS = [
    re.compile(r"\b(the (?:file|case|secret|truth|past|incident))\b", re.IGNORECASE),
    re.compile(r"\b(what (?:I did|lena did|happened|she did|he did))\b", re.IGNORECASE),
    re.compile(r"\b(never (?:told|said|explained|revealed|admitted))\b", re.IGNORECASE),
    re.compile(r"\b(counsel of record|represented|petitioner|divorce (?:case|file))\b", re.IGNORECASE),
    re.compile(r"\b(case number|NY-\d+-|docket)\b", re.IGNORECASE),
]

# Patterns that suggest concrete exposition (WHAT was delivered)
_EXPOSITION_PATTERNS = [
    re.compile(r"\b(I (?:represented|defended|handled|filed|argued))\b", re.IGNORECASE),
    re.compile(r"\b(the (?:custody|custody dispute|divorce) (?:case|filing))\b", re.IGNORECASE),
    re.compile(r"\b(uncle|aunt|cousin|family member)\s+(?:lost|losing|was)\b", re.IGNORECASE),
    re.compile(r"\b(specifically|concretely|in fact|actually)\s+[^.!?]{10,80}[.!?]", re.IGNORECASE),
    re.compile(r"\b(it was (?:about|because|when))\s+[^.!?]{15,120}[.!?]", re.IGNORECASE),
]


def _extract_secret_threads_from_outline(outline: List[Dict], config: Dict) -> List[Dict]:
    """Extract plot threads that are secrets/reveals from outline + config."""
    threads = []
    key_points = config.get("key_plot_points", "")
    if key_points:
        for line in str(key_points).split("\n"):
            line = line.strip()
            if not line or not any(
                k in line.lower()
                for k in ("secret", "reveal", "file", "discover", "truth", "divorce", "case")
            ):
                continue
            threads.append({
                "id": f"thread_{len(threads)}",
                "source": "key_plot_points",
                "description": line[:200],
                "type": "SECRET" if "secret" in line.lower() or "reveal" in line.lower() else "REVEAL",
            })
    # Scan outline scene purposes
    for ch in (outline or []):
        if not isinstance(ch, dict):
            continue
        for sc in ch.get("scenes", []):
            if not isinstance(sc, dict):
                continue
            purpose = (sc.get("purpose") or "") + " " + (sc.get("central_conflict") or "")
            if any(
                k in purpose.lower()
                for k in ("secret", "reveal", "file", "discover", "divorce", "legal")
            ):
                threads.append({
                    "id": f"ch{ch.get('chapter',0)}_s{sc.get('scene',0)}",
                    "source": "outline",
                    "description": purpose[:200],
                    "type": "REVEAL",
                })
    return threads


def _count_secret_refs(text: str) -> int:
    """Count how many times secret/reveal is referenced with emotional weight."""
    count = 0
    for pat in _SECRET_REF_PATTERNS:
        count += len(pat.findall(text))
    return count


def _count_exposition(text: str) -> int:
    """Count sentences that deliver concrete WHAT/WHY."""
    count = 0
    for pat in _EXPOSITION_PATTERNS:
        count += len(pat.findall(text))
    return count


def check_causal_completeness(
    scenes: List[Dict],
    outline: List[Dict],
    config: Dict,
    min_refs_for_flag: int = 5,
) -> Dict[str, Any]:
    """Check if secret/reveal threads are referenced but never explained.

    Returns:
        {
            "violations": [{"thread": str, "ref_count": int, "exposition_count": int,
                           "message": str, "target_scene_id": str}],
            "pass": bool,
        }
    """
    threads = _extract_secret_threads_from_outline(outline, config)
    if not threads:
        return {"violations": [], "pass": True}

    # Per-scene ref counts to find best target for adding exposition
    target_scene_id = ""
    max_refs = 0
    full_text = ""

    for scene in (scenes or []):
        if not isinstance(scene, dict):
            continue
        content = scene.get("content", "")
        refs = _count_secret_refs(content)
        if refs > max_refs:
            max_refs = refs
            target_scene_id = scene.get("scene_id") or (
                f"ch{int(scene.get('chapter',0)):02d}_s{int(scene.get('scene_number',0)):02d}"
            )
        full_text += "\n\n" + content

    ref_count = _count_secret_refs(full_text)
    exp_count = _count_exposition(full_text)

    violations: List[Dict[str, Any]] = []

    # Flag: many references to secret/case/file but minimal concrete exposition
    if ref_count >= min_refs_for_flag and exp_count < 2:
        violations.append({
            "thread": "secret/legal/reveal",
            "ref_count": ref_count,
            "exposition_count": exp_count,
            "target_scene_id": target_scene_id,
            "message": (
                f"Manuscript references the secret/case/file {ref_count}+ times but delivers "
                f"minimal concrete exposition ({exp_count} beats). Readers react to an undefined "
                "stimulus. Add 2-3 sentences (in scene with reveal or high emotional weight) "
                "explaining: what specifically happened, what case it was, and why it matters."
            ),
        })
        logger.warning(
            "Causal completeness: %d secret refs, %d exposition beats — add concrete WHAT",
            ref_count, exp_count,
        )

    return {
        "violations": violations,
        "pass": len(violations) == 0,
    }
