"""
Quality Scorecard -- aggregate deterministic metrics for manuscript health.

Computes 5 metrics:
1. Lexical Diversity (type-token ratio on sliding window)
2. Dialogue Density Variance (dialogue lines / total lines per scene)
3. Emotional Mode Diversity (Shannon entropy over emotion classification)
4. Verb Specificity Index (specific verbs vs weak verbs)
5. Scene Ending Distribution (ending type evenness)

All metrics are deterministic, zero-cost, JSON-serializable.
"""

import re
import math
import logging
from collections import Counter
from typing import Callable, Dict, List, Optional, Set

logger = logging.getLogger("scorecard")

# Strong verbs for verb specificity index
_STRONG_VERBS = {
    # Physical action
    "lunged", "slammed", "staggered", "sprinted", "crept", "stormed",
    "darted", "scrambled", "yanked", "hurled", "clenched", "seized",
    "gripped", "bolted", "plunged", "crawled", "pivoted", "whirled",
    "shoved", "dragged", "wrenched", "vaulted", "leapt", "ducked",
    # Emotional / sensory
    "whispered", "flinched", "recoiled", "trembled", "swayed", "erupted",
    "blazed", "soared", "surged", "shuddered", "winced", "gasped",
    "snarled", "hissed", "murmured", "stammered", "shrieked", "sobbed",
    # Impact / destruction
    "carved", "hammered", "shattered", "smashed", "splintered", "crushed",
    "ripped", "gouged", "cleaved", "pierced",
    # Stealth / pursuit
    "stalked", "prowled", "shadowed", "ambushed", "pounced", "cornered",
}

_WORD_RE = re.compile(r"\b[a-z]+\b")


def _type_token_ratio(text: str, window: int = 500) -> float:
    """Sliding-window type-token ratio. Higher = more diverse vocabulary."""
    words = _WORD_RE.findall(text.lower())
    if not words:
        return 0.0
    if len(words) <= window:
        return len(set(words)) / len(words)
    # Sliding window average
    total = 0.0
    steps = 0
    for i in range(0, len(words) - window + 1, window // 2):
        chunk = words[i : i + window]
        total += len(set(chunk)) / len(chunk)
        steps += 1
    return total / steps if steps > 0 else 0.0


def _dialogue_density(content: str) -> float:
    """Fraction of lines containing dialogue (quotes)."""
    lines = [ln for ln in content.split("\n") if ln.strip()]
    if not lines:
        return 0.0
    dialogue_lines = sum(
        1 for ln in lines
        if '"' in ln or "\u201c" in ln or "\u201d" in ln
    )
    return dialogue_lines / len(lines)


def _classify_dominant_emo(content: str, emo_keywords: Dict[str, str]) -> Optional[str]:
    """Classify dominant emotional mode using keyword regexes."""
    best_mode = None
    best_count = 0
    content_lower = content.lower()
    for mode, pat_str in emo_keywords.items():
        count = len(re.findall(pat_str, content_lower, re.IGNORECASE))
        if count > best_count:
            best_count = count
            best_mode = mode
    return best_mode


def _shannon_entropy(distribution: List[int]) -> float:
    """Shannon entropy over a count distribution."""
    total = sum(distribution)
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in distribution:
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)
    return entropy


def _verb_specificity_index(content: str, weak_verbs: Set[str]) -> float:
    """Ratio of strong verbs to (strong + weak). 0.5 if none found."""
    words = _WORD_RE.findall(content.lower())
    weak_count = sum(1 for w in words if w in weak_verbs)
    strong_count = sum(1 for w in words if w in _STRONG_VERBS)
    total = strong_count + weak_count
    if total == 0:
        return 0.5  # neutral
    return strong_count / total


def _ending_evenness(ending_counts: Counter) -> float:
    """Evenness score for ending type distribution. Higher = more even."""
    total = sum(ending_counts.values())
    if total == 0:
        return 0.0
    n_types = len(ending_counts)
    if n_types <= 1:
        return 0.0
    expected = total / n_types
    chi_sq = sum((v - expected) ** 2 / expected for v in ending_counts.values())
    return 1.0 - (chi_sq / (chi_sq + total))


def run_scorecard(
    scenes: List[Dict],
    emo_keywords: Dict[str, str],
    weak_verbs: Set[str],
    classify_ending_fn: Callable[[str], str],
    thresholds: Optional[Dict] = None,
) -> Dict:
    """Compute quality scorecard across all scenes.

    Args:
        scenes: List of scene dicts with "content" key.
        emo_keywords: Emotion keyword dict from quiet_killers._EMO_KEYWORDS.
        weak_verbs: Set of weak verbs from quiet_killers._WEAK_VERBS.
        classify_ending_fn: quiet_killers._classify_ending function.
        thresholds: Optional dict of genre-tuned thresholds from policy.

    Returns:
        Dict with 5 metric sections + overall pass.
    """
    if not scenes:
        return {"pass": True, "note": "No scenes to score"}

    content_scenes = [s for s in scenes if isinstance(s, dict) and s.get("content")]
    if not content_scenes:
        return {"pass": True, "note": "No scenes with content"}

    # Per-scene metrics
    ttr_scores = []
    dd_scores = []
    emo_modes: List[Optional[str]] = []
    verb_scores = []
    ending_types: List[str] = []

    for scene in content_scenes:
        content = scene["content"]
        scene_id = scene.get("scene_id", "?")

        ttr_scores.append(round(_type_token_ratio(content), 4))
        dd_scores.append(round(_dialogue_density(content), 4))
        emo_modes.append(_classify_dominant_emo(content, emo_keywords))
        verb_scores.append(round(_verb_specificity_index(content, weak_verbs), 4))

        # Ending classification
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        last_para = paragraphs[-1] if paragraphs else ""
        ending_types.append(classify_ending_fn(last_para) if last_para else "UNKNOWN")

    # Aggregates
    n = len(content_scenes)
    t = thresholds or {}

    # 1. Lexical diversity
    ttr_avg = sum(ttr_scores) / n
    ld_pass = ttr_avg >= t.get("lexical_diversity_min", 0.40)

    # 2. Dialogue density variance
    dd_mean = sum(dd_scores) / n
    dd_variance = sum((d - dd_mean) ** 2 for d in dd_scores) / n if n > 1 else 0.0
    dd_pass = dd_variance >= t.get("dialogue_variance_min", 0.01)

    # 3. Emotional mode diversity
    mode_counts = Counter(m for m in emo_modes if m is not None)
    emo_entropy = _shannon_entropy(list(mode_counts.values()))
    max_entropy = math.log2(len(mode_counts)) if len(mode_counts) > 1 else 0.0
    emo_pass = emo_entropy >= t.get("emotional_entropy_min", 1.5)

    # 4. Verb specificity
    verb_avg = sum(verb_scores) / n
    verb_pass = verb_avg >= t.get("verb_specificity_min", 0.30)

    # 5. Scene ending distribution
    ending_counts = Counter(ending_types)
    evenness = _ending_evenness(ending_counts)
    ending_pass = evenness >= t.get("ending_evenness_min", 0.40)

    # 6. Abstract noun density (per 1k words)
    try:
        from quality.repetition_scanner import compute_abstract_noun_density
        and_scores = [compute_abstract_noun_density(s["content"]) for s in content_scenes]
        and_avg = sum(and_scores) / n if n else 0.0
        and_pass = and_avg <= t.get("abstract_noun_density_max", 12.0)
    except Exception:
        and_scores = []
        and_avg = 0.0
        and_pass = True

    # Build per-metric results
    metric_results = {
        "lexical_diversity": {
            "per_scene": ttr_scores,
            "manuscript_avg": round(ttr_avg, 4),
            "pass": ld_pass,
        },
        "dialogue_density_variance": {
            "per_scene": dd_scores,
            "variance": round(dd_variance, 6),
            "mean": round(dd_mean, 4),
            "pass": dd_pass,
        },
        "emotional_mode_diversity": {
            "mode_counts": dict(mode_counts),
            "entropy": round(emo_entropy, 4),
            "max_entropy": round(max_entropy, 4),
            "pass": emo_pass,
        },
        "verb_specificity_index": {
            "per_scene": verb_scores,
            "manuscript_avg": round(verb_avg, 4),
            "pass": verb_pass,
        },
        "scene_ending_distribution": {
            "ending_counts": dict(ending_counts),
            "evenness_score": round(evenness, 4),
            "pass": ending_pass,
        },
        "abstract_noun_density": {
            "per_scene": and_scores,
            "manuscript_avg": round(and_avg, 1),
            "threshold_max": t.get("abstract_noun_density_max", 12.0),
            "pass": and_pass,
        },
    }

    # Weighted scoring (from policy scorecard_weights config)
    weights_cfg = t.get("scorecard_weights") or {}
    mode = weights_cfg.get("mode", "boolean")

    if mode == "weighted":
        weighted_result = _compute_weighted_pass(metric_results, weights_cfg)
        metric_results["weighted"] = weighted_result
        overall_pass = weighted_result["pass"]
    else:
        overall_pass = ld_pass and dd_pass and emo_pass and verb_pass and ending_pass and and_pass

    metric_results["pass"] = overall_pass
    return metric_results


# Mapping from weight config keys → metric result keys
_METRIC_KEY_MAP = {
    "lexical_diversity": "lexical_diversity",
    "dialogue_density": "dialogue_density_variance",
    "emotional_diversity": "emotional_mode_diversity",
    "verb_specificity": "verb_specificity_index",
    "scene_endings": "scene_ending_distribution",
    "abstract_noun_density": "abstract_noun_density",
}


def _compute_weighted_pass(
    metric_results: Dict,
    weights_cfg: Dict,
) -> Dict:
    """Compute weighted pass/fail from per-metric results and weight config.

    Returns dict with score, pass, warnings, and hard_fail details.
    """
    pass_score = weights_cfg.get("pass_score", 0.70)
    total_weight = 0.0
    earned_weight = 0.0
    warnings = []
    hard_fail = False

    for cfg_key, result_key in _METRIC_KEY_MAP.items():
        metric_cfg = weights_cfg.get(cfg_key, {})
        if isinstance(metric_cfg, dict):
            weight = metric_cfg.get("weight", 0.20)
            action = metric_cfg.get("action_on_fail", "warn")
        else:
            weight = 0.20
            action = "warn"

        if action == "off":
            continue

        total_weight += weight
        metric_passed = metric_results.get(result_key, {}).get("pass", True)

        if metric_passed:
            earned_weight += weight
        else:
            if action == "fail":
                hard_fail = True
                warnings.append(f"{cfg_key}: HARD FAIL (action_on_fail=fail)")
            else:
                warnings.append(f"{cfg_key}: below threshold (warn)")

    score = round(earned_weight / total_weight, 4) if total_weight > 0 else 1.0
    passed = score >= pass_score and not hard_fail

    return {
        "score": score,
        "pass_score": pass_score,
        "pass": passed,
        "hard_fail": hard_fail,
        "warnings": warnings,
    }
