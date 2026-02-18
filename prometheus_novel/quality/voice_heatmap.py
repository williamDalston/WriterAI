"""Voice heatmap diagnostic: flag scenes flatter than average.

Per-scene: adverb density, weak verb frequency, abstract noun density,
sentence length variance. Scenes flatter than average get flagged for
priority polish or higher-weight revision.

Config: enhancements.voice_heatmap.enabled
"""

import re
from typing import Dict, List, Optional, Any

# Weak verbs that signal passive/flat prose
_WEAK_VERBS = re.compile(
    r"\b(was|were|is|are|be|been|being|has|have|had|get|gets|got|"
    r"go|goes|went|make|makes|made|do|does|did|seemed|seems|"
    r"felt|feel|feels|began|begin|begins|started|start|starts|"
    r"tried|try|tries|managed|manage|wanted|want|wants)\b",
    re.IGNORECASE,
)

# Abstract nouns (same set as repetition_scanner)
_ABSTRACT_NOUNS = re.compile(
    r"\b(fear|truth|feeling|memory|hope|love|idea|thought|moment|"
    r"thing|something|nothing|everything|realization|understanding|"
    r"knowledge|sense|emotion|connection|distance|silence)\b",
    re.IGNORECASE,
)

# Adverbs (ly-ending, common flat intensifiers)
_ADVERBS = re.compile(r"\b\w+ly\b", re.IGNORECASE)


def compute_scene_metrics(content: str) -> Dict[str, float]:
    """Compute per-scene voice metrics.

    Returns:
        adverb_density: adverbs per 500 words
        weak_verb_density: weak verbs per 500 words
        abstract_noun_density: abstract nouns per 500 words
        sentence_length_variance: std dev of sentence word counts (0 if < 5 sentences)
    """
    if not content or len(content.strip()) < 50:
        return {}

    words = content.split()
    word_count = len(words)
    if word_count < 20:
        return {}

    norm = word_count / 500.0
    adverb_count = len(_ADVERBS.findall(content))
    weak_count = len(_WEAK_VERBS.findall(content))
    abstract_count = len(_ABSTRACT_NOUNS.findall(content))

    sentences = [s.strip() for s in re.split(r"[.!?]+", content) if s.strip() and len(s.strip()) > 5]
    lengths = [len(s.split()) for s in sentences]
    variance = 0.0
    if len(lengths) >= 5:
        mean_l = sum(lengths) / len(lengths)
        variance = (sum((x - mean_l) ** 2 for x in lengths) / len(lengths)) ** 0.5

    return {
        "adverb_density": adverb_count / norm if norm > 0 else 0,
        "weak_verb_density": weak_count / norm if norm > 0 else 0,
        "abstract_noun_density": abstract_count / norm if norm > 0 else 0,
        "sentence_length_variance": variance,
    }


def compute_heatmap(
    scenes: List[Dict],
    config: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Compute voice heatmap across all scenes. Flag scenes flatter than average.

    Args:
        scenes: List of scene dicts with "content" key
        config: Optional config with enhancements.voice_heatmap settings

    Returns:
        {
            "enabled": bool,
            "per_scene": [{"scene_id", "chapter", "scene_number", "metrics", "flags"}],
            "averages": {...},
            "flat_scenes": [scene_id list],
            "warnings": [str],
        }
    """
    cfg = (config or {}).get("enhancements", {}).get("voice_heatmap", {})
    if not cfg.get("enabled", True):
        return {"enabled": False}

    all_metrics: List[Dict] = []
    for scene in (scenes or []):
        if not isinstance(scene, dict):
            continue
        content = scene.get("content", "")
        metrics = compute_scene_metrics(content)
        if not metrics:
            continue

        scene_id = scene.get("scene_id") or scene.get("id") or ""
        ch = scene.get("chapter", 0)
        sn = scene.get("scene_number", scene.get("scene", 0))
        all_metrics.append({
            "scene_id": scene_id,
            "chapter": ch,
            "scene_number": sn,
            "metrics": metrics,
        })

    if not all_metrics:
        return {"enabled": True, "per_scene": [], "averages": {}, "flat_scenes": [], "warnings": []}

    # Compute averages
    n = len(all_metrics)
    avg = {
        "adverb_density": sum(m["metrics"]["adverb_density"] for m in all_metrics) / n,
        "weak_verb_density": sum(m["metrics"]["weak_verb_density"] for m in all_metrics) / n,
        "abstract_noun_density": sum(m["metrics"]["abstract_noun_density"] for m in all_metrics) / n,
        "sentence_length_variance": sum(m["metrics"]["sentence_length_variance"] for m in all_metrics) / n,
    }

    # Flag scenes flatter than average (higher adverb/weak/abstract, lower variance)
    flat_threshold = float(cfg.get("flat_threshold", 1.2))  # 1.2 = 20% worse than avg
    flat_scenes: List[str] = []
    warnings: List[str] = []

    for m in all_metrics:
        flags = []
        met = m["metrics"]
        # Higher density = flatter
        if avg["adverb_density"] > 0 and met["adverb_density"] >= avg["adverb_density"] * flat_threshold:
            flags.append("high_adverb_density")
        if avg["weak_verb_density"] > 0 and met["weak_verb_density"] >= avg["weak_verb_density"] * flat_threshold:
            flags.append("high_weak_verb_density")
        if avg["abstract_noun_density"] > 0 and met["abstract_noun_density"] >= avg["abstract_noun_density"] * flat_threshold:
            flags.append("high_abstract_noun_density")
        # Lower variance = flatter rhythm
        if avg["sentence_length_variance"] > 2 and met["sentence_length_variance"] < avg["sentence_length_variance"] / flat_threshold:
            flags.append("low_sentence_variance")

        m["flags"] = flags
        if flags:
            sid = m.get("scene_id") or f"ch{m['chapter']}_s{m['scene_number']}"
            flat_scenes.append(sid)
            warnings.append(f"FLAT: {sid} — {', '.join(flags)}")

    return {
        "enabled": True,
        "per_scene": all_metrics,
        "averages": avg,
        "flat_scenes": flat_scenes,
        "warnings": warnings,
    }


def get_flat_scene_ids(scenes: List[Dict], config: Optional[Dict] = None) -> List[str]:
    """Convenience: return list of scene IDs flatter than average."""
    result = compute_heatmap(scenes, config)
    return result.get("flat_scenes", [])


def build_voice_heatmap(scenes: List[Dict], config: Optional[Dict] = None) -> Dict[str, Any]:
    """Alias for compute_heatmap. Used by quality_meters stage."""
    return compute_heatmap(scenes, config)
