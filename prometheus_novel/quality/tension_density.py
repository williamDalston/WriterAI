"""
Tension Density Gate — measures narrative value per scene.

Four dimensions scored per scene:
1. New Information: mystery reframed, constraint added, fact revealed
2. Power Shift: leverage changes hands, authority challenged or gained
3. Irreversible Action: door closes, resource spent, alliance breaks, someone dies
4. Emotional Turn: trust changes, confession seed, shame spike, vulnerability

Scoring:
- Each dimension: present (1) or absent (0)
- Scene score: 0-4
- Score 0-1: flag for scene_turn_injection micro-pass
- Score 2-4: pass

Designed to be deterministic and fast (no LLM calls).
Integrates with scorecard system via JSON report.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("tension_density")


# ── Dimension 1: New Information ────────────────────────────────────────────

_INFO_DISCOVERY_VERBS = re.compile(
    r"\b(discover|realize|recognize|notice|find|uncover|detect|identify|spot|"
    r"figure out|piece together|connect|decode|decipher|intercept|overhear)\b",
    re.IGNORECASE,
)

_INFO_EVIDENCE_MARKERS = re.compile(
    r"\b(evidence|proof|log|record|file|message|signal|footage|timestamp|"
    r"override|breach|anomaly|discrepancy|residue|tampering|sabotage|"
    r"data|readout|sensor|diagnostic|alert|warning)\b",
    re.IGNORECASE,
)

_INFO_REFRAME_PATTERNS = re.compile(
    r"(?:not what (?:I|we|she|he) thought|which means|that explains|"
    r"all along|this whole time|never (?:was|were|about)|"
    r"the real (?:reason|question|problem)|now (?:I|we) know|"
    r"so that's (?:why|how|what)|changes everything|"
    r"(?:I|we) (?:didn't|don't) know (?:that|about|the)|"
    r"makes sense now|pieces (?:fall|click|fit))",
    re.IGNORECASE,
)

_INFO_QUESTION_MARKERS = re.compile(
    r"(?:who (?:did|has|is|was)|what (?:happened|if)|why (?:would|did|is)|"
    r"how (?:did|could|is)|where (?:did|is|was))\b",
    re.IGNORECASE,
)


def _score_new_information(text: str, dialogue: str, narration: str) -> Tuple[bool, List[str]]:
    """Score dimension 1: does the scene introduce new information?"""
    signals = []

    # Discovery verbs in narration (not dialogue — characters can talk about
    # discovering things without the reader learning something new)
    discovery_hits = _INFO_DISCOVERY_VERBS.findall(narration)
    if len(discovery_hits) >= 2:
        signals.append(f"discovery_verbs: {', '.join(discovery_hits[:3])}")

    # Evidence/data markers (strong signal in thriller)
    evidence_hits = _INFO_EVIDENCE_MARKERS.findall(text)
    if len(evidence_hits) >= 2:
        signals.append(f"evidence_markers: {', '.join(evidence_hits[:3])}")

    # Reframing language
    reframe_hits = _INFO_REFRAME_PATTERNS.findall(text)
    if reframe_hits:
        signals.append(f"reframe: {reframe_hits[0][:40]}")

    # Questions that drive mystery (in dialogue or narration)
    question_hits = _INFO_QUESTION_MARKERS.findall(text)
    if len(question_hits) >= 2:
        signals.append(f"mystery_questions: {len(question_hits)}")

    # Present if 2+ signal types fire, or 1 strong signal (reframe/evidence)
    present = len(signals) >= 2 or any("reframe" in s or "evidence" in s for s in signals)
    return present, signals


# ── Dimension 2: Power Shift ───────────────────────────────────────────────

_POWER_CONFRONTATION = re.compile(
    r"\b(confront|accuse|demand|challenge|defy|refuse|reject|override|"
    r"block|deny|threaten|warn|command|order|insist|expose|call out)\b",
    re.IGNORECASE,
)

_POWER_SUBMISSION = re.compile(
    r"\b(submit|yield|agree|comply|back down|step aside|cave|concede|"
    r"surrender|obey|defer|relent|fold|give in|stand down)\b",
    re.IGNORECASE,
)

_POWER_PHYSICAL = re.compile(
    r"\b(grab|shove|slam|pin|block|restrain|push|drag|corner|trap|"
    r"seize|grip|hold|force|lock|seal)\b",
    re.IGNORECASE,
)

_POWER_AUTHORITY_MARKERS = re.compile(
    r"(?:takes? (?:control|charge|command|over)|in charge now|"
    r"not (?:your|his|her) (?:call|decision|choice)|"
    r"you (?:don't|do not) get to|"
    r"I'm (?:in charge|running this|making the call)|"
    r"who (?:put|gave) you|no longer (?:your|his|her))",
    re.IGNORECASE,
)


def _score_power_shift(text: str, dialogue: str, narration: str) -> Tuple[bool, List[str]]:
    """Score dimension 2: does leverage change hands?"""
    signals = []

    confront_hits = _POWER_CONFRONTATION.findall(text)
    if len(confront_hits) >= 2:
        signals.append(f"confrontation: {', '.join(confront_hits[:3])}")

    submit_hits = _POWER_SUBMISSION.findall(text)
    if submit_hits:
        signals.append(f"submission: {', '.join(submit_hits[:2])}")

    physical_hits = _POWER_PHYSICAL.findall(text)
    if len(physical_hits) >= 2:
        signals.append(f"physical_dominance: {', '.join(physical_hits[:3])}")

    authority_hits = _POWER_AUTHORITY_MARKERS.findall(text)
    if authority_hits:
        signals.append(f"authority_claim: {authority_hits[0][:40]}")

    # Confrontation + submission = definite shift
    has_confrontation = any("confrontation" in s for s in signals)
    has_submission = any("submission" in s for s in signals)
    has_authority = any("authority" in s for s in signals)

    present = (has_confrontation and has_submission) or \
              has_authority or \
              len(signals) >= 2
    return present, signals


# ── Dimension 3: Irreversible Action ──────────────────────────────────────

_IRREVERSIBLE_CONSEQUENCE = re.compile(
    r"\b(dead|dies?|kill|destroy|break|shatter|collapse|flood|breach|"
    r"seal|lock|cut|sever|detonate|delete|erase|lose|gone|"
    r"no (?:going|turning) back|can't (?:undo|unsee|unhear|take back)|"
    r"too late|point of no return|damage (?:is )?done)\b",
    re.IGNORECASE,
)

_IRREVERSIBLE_RESOURCE = re.compile(
    r"\b(oxygen (?:drops?|falls?|runs?|running|depleted|gone)|"
    r"power (?:fails?|dies?|drops?|gone|cut)|"
    r"comm(?:s|unication)? (?:goes?|went|cut|dead|down|dies?)|"
    r"time (?:runs? out|running out|up|left)|"
    r"countdown|timer|minutes (?:left|remaining)|"
    r"last (?:chance|option|resort)|"
    r"battery (?:dead|dying|low)|fuel (?:low|empty|gone))\b",
    re.IGNORECASE,
)

_IRREVERSIBLE_ALLIANCE = re.compile(
    r"(?:(?:trust|alliance|deal|pact|agreement) (?:broken|shattered|over|done|gone)|"
    r"betray|abandon|leave (?:him|her|them|us) behind|"
    r"on (?:your|my|his|her) own now|"
    r"can't trust|don't trust|never trust|"
    r"chose (?:wrong|sides?|him|her|them))",
    re.IGNORECASE,
)


def _score_irreversible_action(text: str, dialogue: str, narration: str) -> Tuple[bool, List[str]]:
    """Score dimension 3: does a door close permanently?"""
    signals = []

    consequence_hits = _IRREVERSIBLE_CONSEQUENCE.findall(text)
    if consequence_hits:
        signals.append(f"consequence: {', '.join(consequence_hits[:3])}")

    resource_hits = _IRREVERSIBLE_RESOURCE.findall(text)
    if resource_hits:
        signals.append(f"resource_loss: {', '.join(resource_hits[:2])}")

    alliance_hits = _IRREVERSIBLE_ALLIANCE.findall(text)
    if alliance_hits:
        signals.append(f"alliance_break: {alliance_hits[0][:40]}")

    present = len(signals) >= 1  # Any irreversible signal is strong
    return present, signals


# ── Dimension 4: Emotional Turn ───────────────────────────────────────────

_EMOTIONAL_VULNERABILITY = re.compile(
    r"\b(confess|admit|apologize|forgive|ashamed|guilty|afraid|scared|"
    r"sorry|regret|shame|vulnerable|exposed|honest|truth|trust|"
    r"believe|hope|need|miss|hurt|broken|tired|alone)\b",
    re.IGNORECASE,
)

_EMOTIONAL_SHIFT_MARKERS = re.compile(
    r"(?:for the first time|something (?:shifts?|changes?|breaks?) (?:in|between)|"
    r"(?:I|she|he) (?:didn't|don't|doesn't) expect|"
    r"(?:voice|expression|face|eyes) (?:soften|harden|change|shift|break)|"
    r"almost (?:gentle|kind|honest|real|human)|"
    r"drops? (?:the|his|her|my) (?:guard|mask|pretense|act)|"
    r"(?:real|genuine|honest) for (?:the first time|once))",
    re.IGNORECASE,
)

_EMOTIONAL_SOMATIC = re.compile(
    r"(?:hands? (?:cold|trembl|shak)|throat (?:tight|close|burn)|"
    r"stomach (?:drop|churn|knot|clench)|chest (?:tight|ache|burn|hollow)|"
    r"eyes? (?:burn|sting|blur|wet|water)|"
    r"can't (?:breathe|swallow|speak|look)|"
    r"pulse (?:kick|hammer|race|spike)|heart (?:hammer|race|pound))",
    re.IGNORECASE,
)

_EMOTIONAL_TRUST_CHANGE = re.compile(
    r"(?:begin(?:s|ning)? to trust|start(?:s|ing)? to (?:trust|believe)|"
    r"choose(?:s)? to (?:trust|believe|follow)|"
    r"together|with (?:me|you|him|her|us)|"
    r"not alone|beside (?:me|him|her)|"
    r"stop(?:s)? (?:pretending|performing|lying)|"
    r"mean(?:s)? it|real(?:ly)? mean)",
    re.IGNORECASE,
)


def _score_emotional_turn(text: str, dialogue: str, narration: str) -> Tuple[bool, List[str]]:
    """Score dimension 4: does trust/emotion shift?"""
    signals = []

    vuln_hits = _EMOTIONAL_VULNERABILITY.findall(dialogue)
    if len(vuln_hits) >= 2:
        signals.append(f"vulnerability_in_dialogue: {', '.join(vuln_hits[:3])}")

    shift_hits = _EMOTIONAL_SHIFT_MARKERS.findall(text)
    if shift_hits:
        signals.append(f"emotional_shift: {shift_hits[0][:40]}")

    somatic_hits = _EMOTIONAL_SOMATIC.findall(narration)
    if len(somatic_hits) >= 2:
        signals.append(f"somatic_response: {', '.join(str(h)[:20] for h in somatic_hits[:3])}")

    trust_hits = _EMOTIONAL_TRUST_CHANGE.findall(text)
    if trust_hits:
        signals.append(f"trust_change: {trust_hits[0][:30]}")

    # Need either explicit shift marker or 2+ softer signals
    present = any("shift" in s or "trust" in s for s in signals) or len(signals) >= 2
    return present, signals


# ── Text Splitting Utilities ──────────────────────────────────────────────

_DIALOGUE_RE = re.compile(r'"[^"]*"')
_SMART_DIALOGUE_RE = re.compile(r'\u201c[^\u201d]*\u201d')


def _split_dialogue_narration(text: str) -> Tuple[str, str]:
    """Split text into dialogue and narration components."""
    dialogue_parts = _DIALOGUE_RE.findall(text) + _SMART_DIALOGUE_RE.findall(text)
    dialogue = " ".join(dialogue_parts)
    narration = _DIALOGUE_RE.sub("", text)
    narration = _SMART_DIALOGUE_RE.sub("", narration)
    return dialogue, narration


# ── Main Scoring Function ────────────────────────────────────────────────

def score_tension_density(
    content: str,
    scene_id: str = "",
    purpose: str = "",
) -> Dict:
    """Score a single scene's tension density across 4 dimensions.

    Args:
        content: Scene prose text.
        scene_id: Scene identifier (e.g. 'ch03_s01').
        purpose: Scene purpose from outline (used as context, not scored).

    Returns:
        Dict with score, per-dimension results, verdict, and recommendation.
    """
    if not content or len(content.split()) < 50:
        return {
            "scene_id": scene_id,
            "tension_score": 0,
            "dimensions": {},
            "verdict": "skip",
            "recommendation": "Scene too short to evaluate",
        }

    dialogue, narration = _split_dialogue_narration(content)

    # Score each dimension
    d1_present, d1_signals = _score_new_information(content, dialogue, narration)
    d2_present, d2_signals = _score_power_shift(content, dialogue, narration)
    d3_present, d3_signals = _score_irreversible_action(content, dialogue, narration)
    d4_present, d4_signals = _score_emotional_turn(content, dialogue, narration)

    score = sum([d1_present, d2_present, d3_present, d4_present])

    # Build recommendation for low-scoring scenes
    recommendation = None
    if score < 2:
        missing = []
        if not d1_present:
            missing.append("new_information")
        if not d2_present:
            missing.append("power_shift")
        if not d3_present:
            missing.append("irreversible_action")
        if not d4_present:
            missing.append("emotional_turn")
        recommendation = f"Scene scores {score}/4. Missing: {', '.join(missing)}. Consider scene_turn_injection."

    # Verdict
    if score >= 2:
        verdict = "pass"
    elif score == 1:
        verdict = "warn"
    else:
        verdict = "inject"

    return {
        "scene_id": scene_id,
        "tension_score": score,
        "dimensions": {
            "new_information": {"present": d1_present, "signals": d1_signals},
            "power_shift": {"present": d2_present, "signals": d2_signals},
            "irreversible_action": {"present": d3_present, "signals": d3_signals},
            "emotional_turn": {"present": d4_present, "signals": d4_signals},
        },
        "verdict": verdict,
        "recommendation": recommendation,
    }


def run_tension_density(
    scenes: List[Dict],
    mode: str = "warn",
    min_score: int = 2,
) -> Dict:
    """Run tension density gate across all scenes.

    Args:
        scenes: List of scene dicts with 'content', 'scene_id', optional 'purpose'.
        mode: 'warn' (log only), 'strict' (flag for injection), 'off' (skip).
        min_score: Minimum score to pass (default 2 of 4).

    Returns:
        Report dict with per-scene scores, summary stats, and flagged scenes.
    """
    if mode == "off":
        return {"mode": "off", "scenes": [], "flagged": [], "summary": {}}

    results = []
    flagged = []

    for scene in scenes:
        content = scene.get("content", "")
        scene_id = scene.get("scene_id", "")
        purpose = scene.get("purpose", "")

        # Skip locked scenes (already approved)
        if scene.get("locked"):
            results.append({
                "scene_id": scene_id,
                "tension_score": -1,
                "verdict": "locked",
                "recommendation": None,
            })
            continue

        result = score_tension_density(content, scene_id, purpose)
        results.append(result)

        if result["tension_score"] < min_score and result["verdict"] != "skip":
            flagged.append(result)
            if mode == "warn":
                logger.warning(
                    "Tension density: %s scores %d/4 (%s). %s",
                    scene_id, result["tension_score"], result["verdict"],
                    result.get("recommendation", "")
                )
            elif mode == "strict":
                logger.error(
                    "Tension density FAIL: %s scores %d/4. Flagged for scene_turn_injection.",
                    scene_id, result["tension_score"]
                )

    # Summary
    scored = [r for r in results if r.get("tension_score", -1) >= 0]
    avg_score = sum(r["tension_score"] for r in scored) / len(scored) if scored else 0

    # Dimension coverage across all scenes
    dim_coverage = {
        "new_information": 0,
        "power_shift": 0,
        "irreversible_action": 0,
        "emotional_turn": 0,
    }
    for r in scored:
        dims = r.get("dimensions", {})
        for dim_name, dim_data in dims.items():
            if isinstance(dim_data, dict) and dim_data.get("present"):
                dim_coverage[dim_name] += 1

    summary = {
        "total_scenes": len(scenes),
        "scored_scenes": len(scored),
        "flagged_scenes": len(flagged),
        "average_score": round(avg_score, 2),
        "dimension_coverage": dim_coverage,
        "pass_rate": round(
            sum(1 for r in scored if r["tension_score"] >= min_score) / len(scored), 2
        ) if scored else 0,
    }

    return {
        "mode": mode,
        "min_score": min_score,
        "scenes": results,
        "flagged": flagged,
        "summary": summary,
    }
