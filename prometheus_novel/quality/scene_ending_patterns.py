"""Scene-ending pattern detector — prevents repetitive structure.

Flags when too many scenes end with the same type (e.g. romantic escalation,
atmosphere fade) so the pipeline can surface violations for human review or
trigger targeted re-ending.
"""

import logging
import re
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

# Ending types — CONFESSION + NEAR_KISS merge as ROMANTIC_ESCALATION
_ENDING_CONFESSION = re.compile(
    r"\b(told her|told him|confessed|admitted|whispered|said quietly|"
    r"couldn't hold back|had to say|the words slipped|truth I'd been|"
    r"what I felt|what I'd never said|finally said)\b",
    re.IGNORECASE,
)
_ENDING_NEAR_KISS = re.compile(
    r"\b(lips|kiss|leaned in|closer|inches from|breath between|"
    r"almost kissed|pulled away|stepped back|didn't kiss|"
    r"could have kissed|before I could)\b.*[.!?]$",
    re.IGNORECASE,
)
_ENDING_CLIFFHANGER = re.compile(
    r"\b(suddenly|then|before|when|as |until |the door|the phone|"
    r"interrupted|burst in|arrived|appeared|heard|saw that)\b.*[.!?]$",
    re.IGNORECASE,
)
_ENDING_DEPARTURE = re.compile(
    r"\b(walked away|left|turned and|headed|stepped out|disappeared|"
    r"into the|toward the|without looking back|down the)\b.*[.!?]$",
    re.IGNORECASE,
)
_ENDING_DECISION = re.compile(
    r"\b(decided|would|wouldn't|had to|no choice|only one thing|"
    r"knew what|make this right|go back|stay|leave)\b.*[.!?]$",
    re.IGNORECASE,
)
_ENDING_QUIET = re.compile(
    r"\b(silence|stillness|quiet|darkness|morning|salt air|"
    r"sea|wind|rain|nothing else)\b.*[.!?]$",
    re.IGNORECASE,
)
_ENDING_DIALOGUE = re.compile(r'["\u201c][^"\u201d]*[.!?]["\u201d]?\s*$', re.MULTILINE)
_ENDING_ACTION = re.compile(
    r"\b(grabbed|walked|turned|closed|opened|pulled|pushed|stood|"
    r"reached|stepped|ran|slammed|dropped|locked|fired|"
    r"threw|kicked|climbed|ducked|sprinted|bolted|charged)\b.*[.!?]$",
    re.IGNORECASE,
)
_ENDING_HUMOR = re.compile(
    r"\b(snorted|laughed|grinned|shook my head|rolled my eyes|"
    r"typical|of course|naturally)\b.*[.!?]$",
    re.IGNORECASE,
)
_ENDING_THREAT = re.compile(
    r"\b(coming\s+for|wouldn'?t\s+stop|next\s+time|warned|promised|"
    r"watching|waiting\s+for|hunting|not\s+over|"
    r"they'?d\s+be\s+back|only\s+a\s+matter\s+of\s+time)\b.*[.!?]$",
    re.IGNORECASE,
)
_ENDING_COST = re.compile(
    r"\b(gone|lost|never\s+see|couldn'?t\s+take\s+back|too\s+late|"
    r"paid|price|empty|no\s+longer|"
    r"that\s+was\s+the\s+cost|some\s+things\s+can'?t\s+be)\b.*[.!?]$",
    re.IGNORECASE,
)
_ENDING_REVERSAL = re.compile(
    r"\b(but\s+then|everything\s+changed|hadn'?t\s+expected|wrong\s+about|"
    r"lied|wasn'?t\s+what|turned\s+out|the\s+truth\s+was|"
    r"not\s+what\s+(?:she|he|they|it)\s+seemed)\b.*[.!?]$",
    re.IGNORECASE,
)

# Romantic escalation = CONFESSION or NEAR_KISS (count together)
ROMANTIC_ESCALATION = "ROMANTIC_ESCALATION"


def _classify_ending(content: str, tail_words: int = 150) -> str:
    """Classify scene ending into one of the pattern categories."""
    words = content.split()
    tail = " ".join(words[-tail_words:]) if len(words) >= tail_words else content
    last_para = tail.split("\n\n")[-1].strip() if tail else ""
    last_sent = last_para.split(".")[-1].strip() + "." if last_para else ""

    if _ENDING_DIALOGUE.search(last_para[-100:]):
        return "DIALOGUE"
    if _ENDING_NEAR_KISS.search(last_sent):
        return ROMANTIC_ESCALATION
    if _ENDING_CONFESSION.search(last_sent):
        return ROMANTIC_ESCALATION
    if _ENDING_CLIFFHANGER.search(last_sent):
        return "CLIFFHANGER"
    if _ENDING_DEPARTURE.search(last_sent):
        return "DEPARTURE"
    if _ENDING_DECISION.search(last_sent):
        return "DECISION"
    if _ENDING_THREAT.search(last_sent):
        return "THREAT"
    if _ENDING_COST.search(last_sent):
        return "COST"
    if _ENDING_REVERSAL.search(last_sent):
        return "REVERSAL"
    if _ENDING_HUMOR.search(last_sent):
        return "HUMOR"
    if _ENDING_QUIET.search(last_sent):
        return "QUIET"
    if _ENDING_ACTION.search(last_sent):
        return "ACTION"
    return "OTHER"


def check_scene_ending_patterns(
    scenes: List[Dict],
    max_consecutive_same: int = 2,
    max_per_window: int = 3,
    window_size: int = 5,
) -> Dict[str, Any]:
    """Detect repetitive scene-ending patterns.

    Rules:
    - No more than max_consecutive_same consecutive scenes with same ending type
    - No more than max_per_window of same type in any window_size-scene window
    - ROMANTIC_ESCALATION = CONFESSION + NEAR_KISS merged

    Returns:
        {
            "violations": [{"type": str, "scenes": [...], "message": str}],
            "ending_types": [{"scene_id": str, "ending_type": str}, ...],
            "pass": bool,
        }
    """
    ending_types: List[Tuple[str, str]] = []
    for scene in (scenes or []):
        if not isinstance(scene, dict):
            continue
        content = scene.get("content", "")
        sid = scene.get("scene_id") or f"ch{int(scene.get('chapter',0)):02d}_s{int(scene.get('scene_number',0)):02d}"
        etype = _classify_ending(content)
        ending_types.append((sid, etype))

    violations: List[Dict[str, Any]] = []

    # Check consecutive same
    i = 0
    while i < len(ending_types):
        sid, etype = ending_types[i]
        run = 1
        run_ids = [sid]
        j = i + 1
        while j < len(ending_types) and ending_types[j][1] == etype:
            run += 1
            run_ids.append(ending_types[j][0])
            j += 1
        if run > max_consecutive_same:
            violations.append({
                "type": "consecutive_same",
                "ending_type": etype,
                "scenes": run_ids,
                "message": f"{run} consecutive scenes end with {etype} (max {max_consecutive_same}): {', '.join(run_ids)}",
            })
            logger.warning(
                "Scene ending pattern: %d consecutive %s endings at %s",
                run, etype, ", ".join(run_ids[:3]),
            )
        i = j

    # Check window density
    for start in range(len(ending_types) - window_size + 1):
        window = ending_types[start : start + window_size]
        counts: Dict[str, List[str]] = {}
        for sid, etype in window:
            counts.setdefault(etype, []).append(sid)
        for etype, ids in counts.items():
            if len(ids) > max_per_window:
                violations.append({
                    "type": "window_density",
                    "ending_type": etype,
                    "scenes": ids,
                    "message": f"{len(ids)} scenes with {etype} ending in 5-scene window (max {max_per_window}): {', '.join(ids)}",
                })
                logger.warning(
                    "Scene ending pattern: %d %s endings in 5-scene window at %s",
                    len(ids), etype, ", ".join(ids[:3]),
                )

    return {
        "violations": violations,
        "ending_types": [{"scene_id": s, "ending_type": e} for s, e in ending_types],
        "pass": len(violations) == 0,
    }
