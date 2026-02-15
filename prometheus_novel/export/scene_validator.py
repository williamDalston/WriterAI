"""
Pre-export scene validation: genre-agnostic, config-driven.

Detects:
- Meta-text artifacts (META_TEXT → error)
- Unknown character names (SUSPECT_NAME → warning; SUSPECT_NAME_RECURRING → error if ≥3 scenes)
- Genre cross-contamination (only when config opts in via market.tone_constraints)
"""

import hashlib
import re
import logging
from typing import Dict, Any, List, Set, Optional

logger = logging.getLogger(__name__)

# Meta-text patterns: high-confidence artifacts
# Each tuple: (regex, code, human-readable pattern_name)
META_TEXT_PATTERNS = [
    (r"certainly!?\s*(?:here\s+is|here's)", "META_TEXT", "certainly_preamble"),
    (r"here\s+is\s+the\s+revised\b", "META_TEXT", "here_is_revised"),
    (r"below\s+is\s+the\s+(?:revised|updated)\b", "META_TEXT", "below_is_updated"),
    (r"as\s+requested,?\s*(?:here\s+is|here's)", "META_TEXT", "as_requested"),
    (r"sure!?\s*(?:here\s+is|here's)", "META_TEXT", "sure_preamble"),
    (r"(?:the\s+)?rest\s+(?:of\s+the\s+(?:scene|chapter)\s+)?(?:remains?|is)\s+unchanged", "META_TEXT", "rest_unchanged"),
    (r"i\s+can\s+help\s+with\b", "META_TEXT", "i_can_help"),
    (r"let\s+me\s+know\s+if\s+you\s+want\b", "META_TEXT", "let_me_know"),
]

# Recurrence threshold for escalating unknown name to error
SUSPECT_NAME_ERROR_THRESHOLD = 3


def _allowed_names(config: Dict[str, Any]) -> Set[str]:
    """Build allowed character names from config."""
    names: Set[str] = set()
    # New format: characters.protagonist, characters.others
    chars = config.get("characters", {})
    if isinstance(chars, dict):
        prot = chars.get("protagonist", "") or ""
        if prot:
            first = str(prot).split()[0].strip(".,")
            if len(first) > 1:
                names.add(first)
        others = chars.get("others", [])
        if isinstance(others, str):
            others = [o.strip() for o in re.split(r"[,—]", others) if o.strip()]
        for o in others:
            if isinstance(o, str):
                first = o.split()[0].strip(".,")
                if len(first) > 1:
                    names.add(first)
    # Legacy format: protagonist, other_characters
    if not names:
        prot = config.get("protagonist", "") or ""
        if prot:
            first = str(prot).split()[0].strip(".,")
            if len(first) > 1:
                names.add(first)
        other = config.get("other_characters", "") or ""
        for part in re.split(r"[,—\n]", other):
            m = re.search(r"\b([A-Z][a-z]+)\s+[A-Z]", part)
            if m:
                names.add(m.group(1))
            m = re.match(r"\s*([A-Z][a-z]+)\s*[—\-]", part)
            if m:
                names.add(m.group(1))
            # Single first-name in "Name" or "Name—desc" format
            m = re.search(r"\b([A-Z][a-z]{2,})\b", part.strip())
            if m:
                names.add(m.group(1))
    return names


def _tone_constraints(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get tone constraints if config opts in."""
    market = config.get("market", {}) or {}
    return market.get("tone_constraints", {}) or {}


def _validation_mode(config: Dict[str, Any]) -> str:
    """Export validation mode: strict | lenient."""
    export_cfg = config.get("export", {}) or {}
    return str(export_cfg.get("validation_mode", "lenient")).lower() or "lenient"


def _scene_id(scene: Dict[str, Any], index: int) -> str:
    ch = scene.get("chapter", index + 1)
    sc = scene.get("scene_number", 1)
    return f"Ch{ch}Sc{sc}"


def _excerpt(text: str, max_len: int = 60) -> str:
    s = (text or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 3].rstrip() + "..."


def validate_scene(
    content: str,
    config: Dict[str, Any],
    scene_id: str = "",
    scene_index: int = -1,
) -> List[Dict[str, Any]]:
    """
    Validate a single scene. Returns list of structured issues.
    Each issue: {severity, code, scene_id, scene_index, offset, excerpt, pattern_name, message}
    """
    issues: List[Dict[str, Any]] = []
    if not content:
        return issues

    content_len = len(content)
    if content_len < 150:
        return issues

    # 3.1 Meta-text checks (error)
    for pattern, code, pattern_name in META_TEXT_PATTERNS:
        m = re.search(pattern, content, re.IGNORECASE)
        if m:
            issues.append({
                "severity": "error",
                "code": code,
                "scene_id": scene_id,
                "scene_index": scene_index,
                "offset": m.start(),
                "excerpt": _excerpt(content[max(0, m.start() - 20) : m.end() + 40]),
                "pattern_name": pattern_name,
                "message": f"Meta-text artifact ({pattern_name})",
            })

    # 3.1b Word count check
    word_count = len(content.split())
    if word_count < 100:
        issues.append({
            "severity": "warning",
            "code": "SHORT_SCENE",
            "scene_id": scene_id,
            "scene_index": scene_index,
            "offset": 0,
            "excerpt": _excerpt(content[:120]),
            "pattern_name": "word_count_low",
            "message": f"Scene has only {word_count} words (expected 100+)",
        })

    # 3.2 Character-name validation (warning by default)
    allowed = _allowed_names(config)
    tone = _tone_constraints(config)
    suspicious_names: List[str] = tone.get("suspicious_names", [])
    if not suspicious_names and allowed:
        suspicious_names = []  # Only use if explicitly in config

    for name in suspicious_names:
        if name in allowed:
            continue
        count = len(re.findall(rf"\b{re.escape(name)}\b", content, re.IGNORECASE))
        if count >= 1:
            issues.append({
                "severity": "warning",
                "code": "SUSPECT_NAME",
                "scene_id": scene_id,
                "scene_index": scene_index,
                "offset": 0,
                "excerpt": _excerpt(content[:200]),
                "pattern_name": "suspect_character_name",
                "message": f"Character '{name}' appears {count}x (not in allowed list)",
            })

    # 3.3 Disallow terms (only when config opts in)
    disallow_terms = tone.get("disallow_terms", [])
    for term in disallow_terms:
        pat = re.escape(term) if isinstance(term, str) else term
        m = re.search(pat, content, re.IGNORECASE)
        if m:
            issues.append({
                "severity": "error",
                "code": "GENRE_CROSS_CONTAM",
                "scene_id": scene_id,
                "scene_index": scene_index,
                "offset": m.start(),
                "excerpt": _excerpt(content[max(0, m.start() - 20) : m.end() + 40]),
                "pattern_name": f"disallow_term_{term[:20]}",
                "message": f"Disallowed term in scene: '{term}'",
            })

    return issues


def validate_project_scenes(
    scenes: List[Dict[str, Any]],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Validate all scenes before export.

    Returns:
        {
            "issues": [...],
            "has_errors": bool,
            "has_warnings": bool,
        }
    """
    all_issues: List[Dict[str, Any]] = []
    name_scene_counts: Dict[str, Set[str]] = {}  # name -> set of scene_ids

    tone = _tone_constraints(config)
    suspicious_names: List[str] = tone.get("suspicious_names", [])
    allowed = _allowed_names(config)

    for i, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            continue
        content = scene.get("content", "") or ""
        sid = _scene_id(scene, i)
        scene_issues = validate_scene(content, config, sid, scene_index=i)
        all_issues.extend(scene_issues)

        # Track suspicious name recurrence across scenes
        for name in suspicious_names:
            if name in allowed:
                continue
            if re.search(rf"\b{re.escape(name)}\b", content, re.IGNORECASE):
                name_scene_counts.setdefault(name, set()).add(sid)

    # 3.4 Escalate recurring unknown names to error
    for name, scene_ids in name_scene_counts.items():
        if len(scene_ids) >= SUSPECT_NAME_ERROR_THRESHOLD:
            all_issues.append({
                "severity": "error",
                "code": "SUSPECT_NAME_RECURRING",
                "scene_id": ",".join(sorted(scene_ids)),
                "scene_index": -1,
                "offset": 0,
                "excerpt": "",
                "pattern_name": "recurring_suspect_name",
                "message": f"Character '{name}' appears in {len(scene_ids)} scenes (likely cross-contamination)",
            })

    # Scene fingerprint: duplicate content detection
    seen_hashes: Dict[str, str] = {}
    seen_indices: Dict[str, int] = {}
    for i, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            continue
        content = scene.get("content", "") or ""
        if len(content) < 100:
            continue
        fp = compute_scene_fingerprint(content)
        sid = _scene_id(scene, i)
        if fp in seen_hashes:
            all_issues.append({
                "severity": "warning",
                "code": "DUPLICATE_SCENE",
                "scene_id": f"{seen_hashes[fp]}, {sid}",
                "scene_index": i,
                "offset": 0,
                "excerpt": _excerpt(content),
                "pattern_name": "duplicate_fingerprint",
                "message": f"Duplicate scene content detected (same fingerprint as {seen_hashes[fp]})",
            })
        else:
            seen_hashes[fp] = sid
            seen_indices[fp] = i

    has_errors = any(i["severity"] == "error" for i in all_issues)
    has_warnings = any(i["severity"] == "warning" for i in all_issues)

    return {
        "issues": all_issues,
        "has_errors": has_errors,
        "has_warnings": has_warnings,
        "summary": format_validation_report(all_issues),
    }


def format_validation_report(issues: List[Dict[str, Any]]) -> str:
    """Format issues into an actionable human-readable report.

    Groups by scene, shows severity, pattern name, offset, and excerpt
    so the user knows exactly where to look.
    """
    if not issues:
        return "No issues found."

    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]

    lines = [f"Validation: {len(errors)} error(s), {len(warnings)} warning(s)"]
    lines.append("=" * 60)

    # Group by scene_id for readability
    by_scene: Dict[str, List[Dict[str, Any]]] = {}
    for issue in issues:
        sid = issue.get("scene_id", "unknown")
        by_scene.setdefault(sid, []).append(issue)

    for sid in sorted(by_scene.keys()):
        scene_issues = by_scene[sid]
        idx = scene_issues[0].get("scene_index", -1)
        idx_str = f" (index {idx})" if idx >= 0 else ""
        lines.append(f"\n  {sid}{idx_str}:")
        for issue in scene_issues:
            sev = issue["severity"].upper()
            pname = issue.get("pattern_name", issue["code"])
            offset = issue.get("offset", 0)
            excerpt = issue.get("excerpt", "")
            lines.append(f"    [{sev}] {pname} @ offset {offset}")
            if excerpt:
                lines.append(f"           \"{excerpt}\"")

    return "\n".join(lines)


def compute_scene_fingerprint(content: str) -> str:
    """SHA256 hash of normalized content for duplicate detection."""
    normalized = " ".join((content or "").split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
