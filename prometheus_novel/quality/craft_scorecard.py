"""
Craft Scorecard — deterministic metrics for quantified craft improvement.

Produces craft_scorecard.json with:
- Phrase entropy (lexical diversity)
- Dialogue density variance
- Emotional mode diversity
- Verb specificity index
- Scene ending distribution

Config-driven: config.enhancements.craft_scorecard.enabled (default True).
"""

import re
import logging
from collections import Counter
from typing import Dict, List, Optional, Any

logger = logging.getLogger("craft_scorecard")

# Weak verbs for specificity index
_WEAK_VERBS = {"turned", "looked", "nodded", "glanced", "shrugged", "sighed", "said", "asked"}
_ENDING_ACTION = re.compile(r"\b(grabbed|walked|turned|closed|opened|said|asked)\b", re.IGNORECASE)
_ENDING_DIALOGUE = re.compile(r'["\'][^"\']*[.!?]["\']?\s*$', re.MULTILINE)
_ENDING_SUMMARY = re.compile(r"\b(changed|forever|nothing would|everything had|moment that)\b", re.IGNORECASE)
_ENDING_ATMOSPHERE = re.compile(r"\b(sun set|rain fell|silence|darkness|wind)\b", re.IGNORECASE)
_EMO_KEYWORDS = [
    r"\b(joke|laughed|sarcasm|teasing)\b",
    r"\b(angry|furious|yelled|snapped)\b",
    r"\b(soft|gently|touched|held)\b",
    r"\b(wondered|curious|asked)\b",
    r"\b(ashamed|embarrassed)\b",
    r"\b(relief|relaxed|breathed)\b",
]


def _extract_ngrams(text: str, n: int) -> List[str]:
    """Word n-grams, lowercased."""
    words = re.findall(r"\b[a-z]+\b", text.lower())
    return [" ".join(words[i : i + n]) for i in range(len(words) - n + 1)] if len(words) >= n else []


def _phrase_entropy(scenes: List[Dict], n: int = 4) -> float:
    """Distinct n-grams / total n-grams. Higher = more diverse."""
    all_ngrams = []
    for s in scenes or []:
        content = (s.get("content") or "").lower()
        all_ngrams.extend(_extract_ngrams(content, n))
    if not all_ngrams:
        return 0.0
    distinct = len(set(all_ngrams))
    return distinct / len(all_ngrams)


def _dialogue_density_variance(scenes: List[Dict]) -> Dict[str, float]:
    """Dialogue % per scene; return mean, std (sample)."""
    ratios = []
    for s in scenes or []:
        content = s.get("content", "")
        if not content:
            continue
        total = len(content.split())
        quoted = len(re.findall(r'"[^"]*"', content))  # word count in quotes
        ratios.append(quoted / total if total > 0 else 0)
    if len(ratios) < 2:
        return {"mean": ratios[0] if ratios else 0, "std": 0}
    mean = sum(ratios) / len(ratios)
    var = sum((r - mean) ** 2 for r in ratios) / (len(ratios) - 1)
    return {"mean": round(mean, 4), "std": round(var ** 0.5, 4)}


def _emotional_mode_diversity(scenes: List[Dict]) -> int:
    """Count of distinct emotional modes detected across manuscript."""
    modes_seen = set()
    for s in scenes or []:
        content = (s.get("content") or "").lower()
        for i, pat in enumerate(_EMO_KEYWORDS):
            if re.search(pat, content, re.IGNORECASE):
                modes_seen.add(i)
    return len(modes_seen)


def _verb_specificity_index(scenes: List[Dict]) -> float:
    """1 - (weak_verbs / total_verbs). Higher = more specific."""
    weak_count = 0
    total_verbs = 0
    verb_pat = re.compile(r"\b([a-z]+ed|[a-z]+ing|[a-z]+s)\b", re.IGNORECASE)
    for s in scenes or []:
        content = (s.get("content") or "").lower()
        words = content.split()
        for w in words:
            m = verb_pat.match(w)
            if m:
                total_verbs += 1
                if m.group(1).lower() in _WEAK_VERBS:
                    weak_count += 1
    if total_verbs == 0:
        return 1.0
    return round(1 - (weak_count / total_verbs), 4)


def _scene_ending_distribution(scenes: List[Dict]) -> Dict[str, float]:
    """ACTION, DIALOGUE, SUMMARY, ATMOSPHERE, UNKNOWN."""
    counts = {"ACTION": 0, "DIALOGUE": 0, "SUMMARY": 0, "ATMOSPHERE": 0, "UNKNOWN": 0}
    for s in scenes or []:
        content = s.get("content", "")
        paras = [p.strip() for p in content.split("\n\n") if p.strip()]
        if not paras:
            counts["UNKNOWN"] += 1
            continue
        last = paras[-1][-80:]
        if _ENDING_DIALOGUE.search(last):
            counts["DIALOGUE"] += 1
        elif _ENDING_ACTION.search(last):
            counts["ACTION"] += 1
        elif _ENDING_SUMMARY.search(last):
            counts["SUMMARY"] += 1
        elif _ENDING_ATMOSPHERE.search(last):
            counts["ATMOSPHERE"] += 1
        else:
            counts["UNKNOWN"] += 1
    n = len(scenes) or 1
    return {k: round(v / n, 4) for k, v in counts.items()}


def compute_craft_scorecard(
    scenes: List[Dict],
    config: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Compute all craft metrics. Returns dict suitable for JSON."""
    cfg = (config or {}).get("enhancements", {}).get("craft_scorecard", {})
    if cfg.get("enabled", True) is False:
        return {"skipped": "disabled by config"}

    scenes_list = [s for s in (scenes or []) if isinstance(s, dict)]
    if not scenes_list:
        return {"skipped": "no scenes"}

    phrase_ent = _phrase_entropy(scenes_list, n=4)
    dialogue_stats = _dialogue_density_variance(scenes_list)
    emo_div = _emotional_mode_diversity(scenes_list)
    verb_spec = _verb_specificity_index(scenes_list)
    ending_dist = _scene_ending_distribution(scenes_list)

    scorecard = {
        "phrase_entropy": round(phrase_ent, 4),
        "dialogue_density": dialogue_stats,
        "emotional_mode_count": emo_div,
        "verb_specificity_index": verb_spec,
        "ending_distribution": ending_dist,
        "scene_count": len(scenes_list),
    }
    # Optional: single "health" score 0-100 for dashboards
    health = (
        phrase_ent * 25
        + min(dialogue_stats["std"] * 100, 25)
        + emo_div * 5
        + verb_spec * 25
        + (ending_dist.get("ACTION", 0) + ending_dist.get("DIALOGUE", 0)) * 20
    )
    scorecard["health_score"] = round(min(100, max(0, health)), 1)

    # Editorial craft checks (motif saturation, gesture freq, scene transitions, simile density, etc.)
    if cfg.get("editorial_craft", True):
        try:
            from quality.editorial_craft import run_editorial_craft_checks
            editorial = run_editorial_craft_checks(scenes_list, config)
            if "skipped" not in editorial:
                scorecard["editorial_craft"] = editorial
        except Exception as ex:
            logger.warning("Editorial craft checks failed: %s", ex)

    return scorecard
