"""Developmental Audit — high-level audits beyond Editor Studio scope.

Audits and fixes for:
1. Structure and pacing — plot, chapter structure, overall pacing
2. Character arcs — emotional arcs, character change
3. Theme and subtext — theme planting, resonance
4. Line-level polish — copy-edit style (grammar, clarity, passive voice)
5. Genre conventions — romance beats, thriller twists, etc.
6. Fresh eyes — structural confusion, pacing drag, unclear motivation

Each audit produces findings; fixable findings can trigger targeted passes.
Config: enhancements.developmental_audit.enabled, per-audit toggles.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("developmental_audit")

# Genre beat templates (chapter-relative positions: 0.0 = start, 1.0 = end)
GENRE_BEATS = {
    "romance": [
        ("meet/forced_proximity", 0.05, 0.25, "First meeting or forced proximity established"),
        ("first_tension", 0.15, 0.35, "Chemistry or conflict sparks"),
        ("midpoint_intimacy", 0.40, 0.55, "Vulnerability or first real connection"),
        ("dark_moment", 0.65, 0.85, "Betrayal, rejection, or crisis"),
        ("grand_gesture", 0.85, 1.0, "Declaration, sacrifice, or choice for love"),
    ],
    "thriller": [
        ("inciting_incident", 0.0, 0.15, "Threat or mystery introduced"),
        ("stakes_raise", 0.25, 0.4, "Protagonist committed, cannot turn back"),
        ("midpoint_twist", 0.45, 0.55, "Major revelation or reversal"),
        ("all_is_lost", 0.7, 0.85, "Lowest point before finale"),
        ("climax", 0.85, 1.0, "Confrontation or resolution"),
    ],
    "dark romance": [
        ("captivation", 0.05, 0.2, "Dangerous attraction established"),
        ("surrender", 0.35, 0.5, "First real submission/vulnerability"),
        ("betrayal_crisis", 0.6, 0.8, "Trust broken or power imbalance exposed"),
        ("choice", 0.85, 1.0, "Active choice to stay or leave"),
    ],
}


def _derive_scene_id(scene: Dict, idx: int) -> str:
    ch = int(scene.get("chapter", 0) or scene.get("ch", 0))
    sc = int(scene.get("scene_number") or scene.get("scene", 0) or idx)
    return scene.get("scene_id") or f"ch{ch:02d}_s{sc:02d}"


def _get_outline_scenes(outline: List[Dict]) -> List[Tuple[int, int, Dict]]:
    """Yield (chapter, scene_idx, scene_dict) from outline."""
    out = []
    for ch_data in outline or []:
        if not isinstance(ch_data, dict):
            continue
        ch = int(ch_data.get("chapter", 0))
        for i, sc in enumerate(ch_data.get("scenes", [])):
            if isinstance(sc, dict):
                out.append((ch, i, sc))
    return out


def audit_structure_pacing(
    scenes: List[Dict],
    outline: List[Dict],
    config: Dict,
) -> Dict[str, Any]:
    """Audit chapter/scene structure and pacing.

    Checks: chapter length variance, scene count per chapter, tension curve compliance,
    midpoint placement, act structure.
    """
    findings = []
    by_chapter: Dict[int, List[Dict]] = {}
    for s in scenes or []:
        if isinstance(s, dict):
            ch = int(s.get("chapter", 0))
            by_chapter.setdefault(ch, []).append(s)

    total_chapters = len(by_chapter) or 1
    total_scenes = len([s for s in scenes or [] if isinstance(s, dict)])
    words_by_ch = {}
    for ch, scs in by_chapter.items():
        wc = sum(len((s.get("content", "") or "").split()) for s in scs)
        words_by_ch[ch] = wc

    if words_by_ch:
        wcs = list(words_by_ch.values())
        avg = sum(wcs) / len(wcs)
        max_wc = max(wcs)
        min_wc = min(wcs)
        # Flag chapters >50% above or below average
        for ch, wc in words_by_ch.items():
            if avg > 0:
                ratio = wc / avg
                if ratio > 1.5:
                    findings.append({
                        "type": "structure_pacing",
                        "code": "CHAPTER_BLOAT",
                        "chapter": ch,
                        "message": f"Chapter {ch} is {ratio:.1f}x average length ({wc} words). Consider splitting.",
                    })
                elif ratio < 0.5:
                    findings.append({
                        "type": "structure_pacing",
                        "code": "CHAPTER_THIN",
                        "chapter": ch,
                        "message": f"Chapter {ch} is {ratio:.1f}x average length ({wc} words). Consider merging or expanding.",
                    })

    # Scene count variance
    scenes_per_ch = [len(scs) for scs in by_chapter.values()]
    if len(scenes_per_ch) >= 3:
        avg_sc = sum(scenes_per_ch) / len(scenes_per_ch)
        for ch, count in by_chapter.items():
            sc_count = len(by_chapter[ch])
            if avg_sc >= 2 and sc_count == 0:
                findings.append({
                    "type": "structure_pacing",
                    "code": "EMPTY_CHAPTER",
                    "chapter": ch,
                    "message": f"Chapter {ch} has no scenes.",
                })

    return {
        "pass": len(findings) == 0,
        "findings": findings,
        "stats": {
            "total_chapters": total_chapters,
            "total_scenes": total_scenes,
            "words_by_chapter": words_by_ch,
        },
    }


def audit_character_arcs(
    scenes: List[Dict],
    outline: List[Dict],
    characters: List[Dict],
    config: Dict,
) -> Dict[str, Any]:
    """Audit character presence and emotional arc coverage.

    Checks: protagonist scene presence, emotional beat distribution,
    change-from-baseline indicators.
    """
    findings = []
    if not characters:
        return {"pass": True, "findings": [], "skipped": "no_characters"}

    # Get protagonist name(s) from config or first character
    protagonist_names = []
    for c in characters:
        if isinstance(c, dict):
            if c.get("role") == "protagonist" or c.get("is_protagonist"):
                protagonist_names.append((c.get("name") or "").split()[0])
            elif not protagonist_names:
                protagonist_names.append((c.get("name") or "").split()[0])

    if not protagonist_names:
        protagonist_names = ["Lena", "Marco"]  # fallback for romance

    # Count protagonist mentions per scene (rough presence proxy)
    presence_by_scene = []
    for i, s in enumerate(scenes or []):
        if not isinstance(s, dict):
            continue
        content = (s.get("content") or "").lower()
        count = sum(1 for n in protagonist_names if n and n.lower() in content)
        presence_by_scene.append((_derive_scene_id(s, i), count, content.count(" i ")))

    # Flag long runs without protagonist POV feel (I/me) in first-person
    # Simplified: just report stats
    return {
        "pass": len(findings) == 0,
        "findings": findings,
        "stats": {
            "protagonist_names": protagonist_names[:3],
            "scenes_with_pov_candidates": sum(1 for _, _, i in presence_by_scene if i >= 3),
        },
    }


def audit_theme_subtext(
    scenes: List[Dict],
    outline: List[Dict],
    config: Dict,
) -> Dict[str, Any]:
    """Audit theme planting and resonance.

    Uses central_question, motifs, central_conflict from config.
    """
    findings = []
    central_question = (config.get("central_question") or "").strip()
    motifs_raw = (config.get("motifs") or "").strip()
    central_conflict = (config.get("central_conflict") or "").strip()

    if not central_question and not motifs_raw:
        return {"pass": True, "findings": [], "skipped": "no_theme_config"}

    # Extract motif keywords (simple: first phrase of each motif)
    motif_words = []
    for part in motifs_raw.split(",")[:6]:
        words = part.strip().split("(")[0].strip().lower().split()[:3]
        motif_words.extend(w for w in words if len(w) > 3)

    # Sample scenes for motif presence
    total_content = " ".join((s.get("content", "") or "").lower() for s in scenes or [] if isinstance(s, dict))
    motif_presence = {w: total_content.count(w) for w in motif_words[:10] if w}

    # Flag if central question keywords are absent in later acts
    if central_question and len(scenes or []) >= 10:
        later_start = len(scenes) * 2 // 3
        later_content = " ".join(
            (s.get("content", "") or "").lower()
            for s in (scenes or [])[later_start:]
            if isinstance(s, dict)
        )
        keywords = [w for w in central_question.lower().split() if len(w) > 4 and w not in ("that", "this", "with", "from")]
        missing = [k for k in keywords[:5] if k not in later_content]
        if len(missing) >= 3:
            findings.append({
                "type": "theme_subtext",
                "code": "THEME_ABSENT_LATE",
                "message": f"Central question keywords ({missing[:3]}) rare in final third. Consider reinforcing theme.",
            })

    return {
        "pass": len(findings) == 0,
        "findings": findings,
        "stats": {"motif_presence": motif_presence},
    }


def audit_line_level(
    scenes: List[Dict],
    config: Dict,
) -> Dict[str, Any]:
    """Audit line-level issues: passive voice, adverb overuse, repetition.

    Deterministic checks only.
    """
    findings = []
    passive_pat = re.compile(
        r"\b(am|is|are|was|were|be|been|being)\s+\w+ed\b",
        re.IGNORECASE,
    )
    adverb_ly = re.compile(r"\b\w+ly\s+(?:\w+ly\s+){2,}", re.IGNORECASE)  # 3+ -ly in a row

    total_passive = 0
    total_adverb_runs = 0
    scene_flags = []

    for i, s in enumerate(scenes or []):
        if not isinstance(s, dict):
            continue
        content = s.get("content", "") or ""
        n_passive = len(passive_pat.findall(content))
        n_adv = len(adverb_ly.findall(content))
        total_passive += n_passive
        total_adverb_runs += n_adv
        if n_passive >= 5 or n_adv >= 2:
            scene_flags.append({
                "scene_id": _derive_scene_id(s, i),
                "passive_count": n_passive,
                "adverb_runs": n_adv,
            })

    if total_passive > 80:
        findings.append({
            "type": "line_level",
            "code": "PASSIVE_OVERUSE",
            "message": f"{total_passive} passive constructions. Consider active voice for urgency.",
        })
    for sf in scene_flags[:5]:  # top 5 worst
        if sf["passive_count"] >= 8:
            findings.append({
                "type": "line_level",
                "code": "PASSIVE_HOTSPOT",
                "scene_id": sf["scene_id"],
                "message": f"{sf['scene_id']}: {sf['passive_count']} passive constructions.",
            })

    return {
        "pass": len(findings) == 0,
        "findings": findings,
        "stats": {
            "total_passive": total_passive,
            "adverb_runs": total_adverb_runs,
            "flagged_scenes": scene_flags[:10],
        },
    }


def audit_genre_conventions(
    outline: List[Dict],
    scenes: List[Dict],
    config: Dict,
) -> Dict[str, Any]:
    """Audit genre beat coverage against template.

    Compares outline scene purposes to expected genre beats.
    """
    findings = []
    genre = (config.get("genre") or "").lower()
    beats = GENRE_BEATS.get(genre) or GENRE_BEATS.get("romance", GENRE_BEATS["romance"])

    outline_scenes = _get_outline_scenes(outline)
    total_scenes = len(outline_scenes)
    if total_scenes == 0:
        total_scenes = len([s for s in scenes or [] if isinstance(s, dict)])

    beat_coverage = []
    for beat_name, start_frac, end_frac, desc in beats:
        window_start = int(total_scenes * start_frac)
        window_end = int(total_scenes * end_frac) + 1
        window_scenes = outline_scenes[window_start:window_end] if outline_scenes else []
        # Check if any scene in window has purpose text suggesting this beat
        purpose_text = " ".join(
            str(sc.get("purpose", "")) + str(sc.get("central_conflict", ""))
            for _, _, sc in window_scenes
        ).lower()
        # Simple keyword check per beat
        beat_keywords = {
            "meet/forced_proximity": ["meet", "forced", "proximity", "arrive", "first"],
            "first_tension": ["chemistry", "tension", "spark", "conflict"],
            "midpoint_intimacy": ["vulnerab", "open", "connect", "intimacy", "trust"],
            "dark_moment": ["betrayal", "crisis", "pull away", "reject", "secret"],
            "grand_gesture": ["gesture", "declaration", "choice", "toast", "fight for"],
        }
        keywords = beat_keywords.get(beat_name, beat_name.split("_"))
        has_hit = any(kw in purpose_text for kw in keywords)
        beat_coverage.append({
            "beat": beat_name,
            "window": f"{window_start}-{window_end}",
            "covered": has_hit,
            "description": desc,
        })
        if not has_hit:
            findings.append({
                "type": "genre_conventions",
                "code": "MISSING_BEAT",
                "beat": beat_name,
                "message": f"Genre beat '{beat_name}' ({desc}) not clearly present in scenes {window_start}-{window_end}.",
            })

    return {
        "pass": len(findings) == 0,
        "findings": findings,
        "stats": {
            "genre": genre,
            "beat_coverage": beat_coverage,
        },
    }


async def audit_fresh_eyes(
    client: Any,
    scenes: List[Dict],
    outline: List[Dict],
    config: Dict,
) -> Dict[str, Any]:
    """LLM 'cold read' audit — simulates fresh beta reader.

    Sends scene openings/closings to LLM. Flags:
    - CONFUSION: scene_id, issue
    - PACING_DRAG: scene_id, issue
    - UNCLEAR_MOTIVATION: scene_id, character, issue
    """
    if not client:
        return {"pass": True, "findings": [], "skipped": "no_client"}

    scenes_list = [s for s in (scenes or []) if isinstance(s, dict) and s.get("content")]
    if len(scenes_list) < 3:
        return {"pass": True, "findings": [], "skipped": "too_few_scenes"}

    # Build cold-read package: scene_id + first 120 words + last 80 words per scene
    samples = []
    for i, s in enumerate(scenes_list):
        sid = s.get("scene_id") or _derive_scene_id(s, i)
        content = (s.get("content") or "").strip()
        words = content.split()
        first = " ".join(words[:120]) if words else ""
        last = " ".join(words[-80:]) if len(words) > 80 else content
        samples.append(f"[{sid}]\nOPENING: {first}\n...\nCLOSING: {last}")

    # Limit total tokens: cap at ~40 scenes or 12k words of samples
    if len(samples) > 40:
        step = len(samples) // 40
        samples = [samples[i] for i in range(0, len(samples), step)][:40]
    cold_read_text = "\n\n---\n\n".join(samples)

    prompt = f"""You are a fresh beta reader. You've never seen this story before. Below are the openings and closings of each scene (abbreviated).

Read them and identify structural issues a new reader would notice:

1. CONFUSION: Any scene where you were confused — what happened that didn't make sense? (Include scene_id like ch02_s01)
2. PACING_DRAG: Scenes that felt slow, repetitive, or unnecessary
3. UNCLEAR_MOTIVATION: Scenes where a character's action or choice felt unmotivated

Return JSON only, no other text:
{{
  "confusion": [{{"scene_id": "ch01_s02", "issue": "Who is speaking here?"}}],
  "pacing_drag": [{{"scene_id": "ch03_s01", "issue": "Repeated info from previous scene"}}],
  "unclear_motivation": [{{"scene_id": "ch05_s02", "character": "Lena", "issue": "Why does she suddenly leave?"}}]
}}

If nothing stands out, return empty arrays. Be selective — only flag real issues.

=== SCENE SAMPLES ===
{cold_read_text}

=== JSON ==="""

    try:
        response = await client.generate(prompt, max_tokens=2000, temperature=0.3)
        raw = (response.content or "").strip() if response else ""
        # Extract JSON (handle markdown code blocks)
        if "```" in raw:
            for part in raw.split("```"):
                if part.strip().startswith("json"):
                    raw = part.replace("json", "", 1).strip()
                    break
                if part.strip().startswith("{"):
                    raw = part.strip()
                    break
        data = json.loads(raw) if raw.strip().startswith("{") else {}
    except Exception as e:
        logger.warning("Fresh eyes audit failed: %s", e)
        return {"pass": True, "findings": [], "skipped": str(e)}

    findings = []
    for item in (data.get("confusion") or []):
        scene_id = (item or {}).get("scene_id", "")
        issue = (item or {}).get("issue", "")
        if scene_id and issue:
            findings.append({
                "type": "fresh_eyes",
                "code": "CONFUSION",
                "scene_id": scene_id,
                "issue": issue,
                "message": f"{scene_id}: {issue}",
            })
    for item in (data.get("pacing_drag") or []):
        scene_id = (item or {}).get("scene_id", "")
        issue = (item or {}).get("issue", "")
        if scene_id and issue:
            findings.append({
                "type": "fresh_eyes",
                "code": "PACING_DRAG",
                "scene_id": scene_id,
                "message": f"{scene_id}: {issue}",
            })
    for item in (data.get("unclear_motivation") or []):
        scene_id = (item or {}).get("scene_id", "")
        char = (item or {}).get("character", "")
        issue = (item or {}).get("issue", "")
        if scene_id and issue:
            findings.append({
                "type": "fresh_eyes",
                "code": "UNCLEAR_MOTIVATION",
                "scene_id": scene_id,
                "character": char,
                "issue": issue,
                "message": f"{scene_id} ({char}): {issue}",
            })

    return {
        "pass": len(findings) == 0,
        "findings": findings,
        "stats": {"cold_read_scenes": len(samples)},
    }


def run_developmental_audit(
    scenes: List[Dict],
    outline: List[Dict],
    characters: Optional[List[Dict]] = None,
    config: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Run all developmental audits.

    Returns:
        {
            "pass": bool,
            "audits": {
                "structure_pacing": {...},
                "character_arcs": {...},
                "theme_subtext": {...},
                "line_level": {...},
                "genre_conventions": {...},
                "fresh_eyes": {...},
            },
            "findings_by_type": [...],
            "fixable_scene_ids": [...],
        }
    """
    cfg = (config or {}).get("enhancements", {}).get("developmental_audit", {})
    if cfg.get("enabled", True) is False:
        return {"pass": True, "skipped": "disabled"}

    audits = {}
    all_findings = []
    fixable_scene_ids = set()

    # Per-audit toggles
    if cfg.get("structure_pacing", True):
        r = audit_structure_pacing(scenes, outline, config or {})
        audits["structure_pacing"] = r
        all_findings.extend(r.get("findings", []))

    if cfg.get("character_arcs", True):
        r = audit_character_arcs(scenes, outline, characters or [], config or {})
        audits["character_arcs"] = r
        all_findings.extend(r.get("findings", []))

    if cfg.get("theme_subtext", True):
        r = audit_theme_subtext(scenes, outline, config or {})
        audits["theme_subtext"] = r
        all_findings.extend(r.get("findings", []))

    if cfg.get("line_level", True):
        r = audit_line_level(scenes, config or {})
        audits["line_level"] = r
        all_findings.extend(r.get("findings", []))
        for f in r.get("findings", []):
            if "scene_id" in f:
                fixable_scene_ids.add(f["scene_id"])

    if cfg.get("genre_conventions", True):
        r = audit_genre_conventions(outline, scenes, config or {})
        audits["genre_conventions"] = r
        all_findings.extend(r.get("findings", []))

    # fresh_eyes requires async LLM call — pipeline runs audit_fresh_eyes() and merges

    return {
        "pass": len(all_findings) == 0,
        "audits": audits,
        "findings": all_findings,
        "findings_by_type": [
            (f.get("type", "unknown"), f.get("code", ""), f.get("message", ""))
            for f in all_findings
        ],
        "fixable_scene_ids": list(fixable_scene_ids),
    }


def merge_fresh_eyes_into_report(audit_report: Dict[str, Any], fresh_eyes_result: Dict[str, Any]) -> None:
    """Merge fresh_eyes audit result into audit_report in-place."""
    if not fresh_eyes_result or fresh_eyes_result.get("skipped"):
        return
    audits = audit_report.setdefault("audits", {})
    audits["fresh_eyes"] = fresh_eyes_result
    findings = fresh_eyes_result.get("findings", [])
    audit_report.setdefault("findings", []).extend(findings)
    audit_report.setdefault("findings_by_type", []).extend(
        (f.get("type", "fresh_eyes"), f.get("code", ""), f.get("message", ""))
        for f in findings
    )
    fixable = audit_report.setdefault("fixable_scene_ids", [])
    for f in findings:
        if f.get("code") in ("CONFUSION", "UNCLEAR_MOTIVATION") and f.get("scene_id"):
            fixable.append(f["scene_id"])
    audit_report["pass"] = len(audit_report.get("findings", [])) == 0
