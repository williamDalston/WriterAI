"""Cliche cluster detector — category-based repetition detection.

Unlike the phrase miner (exact n-gram matching), this detects semantic
families of tropes via regex pattern groups. Catches formulaic writing
even when surface phrasing varies across models.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)


def load_cluster_config(config_path: Path) -> Dict[str, Any]:
    """Load cliche cluster definitions from YAML."""
    if not config_path.exists():
        logger.warning("Cliche cluster config not found: %s", config_path)
        return {"clusters": {}}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {"clusters": {}}


def detect_clusters(
    scenes: List[str],
    config_path: Optional[Path] = None,
    clusters_dict: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Detect cliche cluster occurrences across scenes.

    Args:
        scenes: List of scene texts.
        config_path: Path to cliche_clusters.yaml.
        clusters_dict: Pre-loaded cluster config (overrides config_path).

    Returns:
        Report with per-cluster counts, flagged clusters, and details.
    """
    if clusters_dict is None:
        if config_path is None:
            config_path = Path(__file__).parent.parent / "configs" / "cliche_clusters.yaml"
        data = load_cluster_config(config_path)
    else:
        data = clusters_dict

    clusters = data.get("clusters", {})
    results: Dict[str, Dict[str, Any]] = {}

    for cluster_name, cluster_def in clusters.items():
        label = cluster_def.get("label", cluster_name)
        patterns = cluster_def.get("patterns", [])
        threshold = cluster_def.get("threshold", 10)

        compiled = []
        for p in patterns:
            try:
                compiled.append(re.compile(p, re.IGNORECASE))
            except re.error as e:
                logger.warning("Invalid regex in cluster '%s': %s — %s", cluster_name, p, e)

        total_hits = 0
        scene_hits = 0
        examples: List[str] = []
        per_scene: List[int] = []

        for scene in scenes:
            scene_count = 0
            for regex in compiled:
                matches = regex.findall(scene)
                scene_count += len(matches)
                if matches and len(examples) < 3:
                    # Find the full sentence containing the match
                    for m in regex.finditer(scene):
                        start = max(0, scene.rfind(".", 0, m.start()) + 1)
                        end = scene.find(".", m.end())
                        if end == -1:
                            end = min(len(scene), m.end() + 80)
                        example = scene[start:end].strip()[:120]
                        if example and len(examples) < 3:
                            examples.append(example)

            total_hits += scene_count
            per_scene.append(scene_count)
            if scene_count > 0:
                scene_hits += 1

        flagged = total_hits >= threshold
        results[cluster_name] = {
            "label": label,
            "total_hits": total_hits,
            "scenes_with_hits": scene_hits,
            "threshold": threshold,
            "flagged": flagged,
            "examples": examples,
            "max_in_scene": max(per_scene) if per_scene else 0,
        }

    flagged_clusters = {k: v for k, v in results.items() if v["flagged"]}

    return {
        "clusters": results,
        "flagged_count": len(flagged_clusters),
        "total_clusters": len(results),
        "flagged_names": list(flagged_clusters.keys()),
    }
