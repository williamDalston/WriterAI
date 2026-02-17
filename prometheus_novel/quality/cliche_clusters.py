"""Cliche cluster detector + repair — category-based repetition handling.

Unlike the phrase miner (exact n-gram matching), this detects semantic
families of tropes via regex pattern groups. Catches formulaic writing
even when surface phrasing varies across models.

The repair pass replaces excess occurrences (beyond keep_first) with
rotating alternatives from the YAML config, preserving capitalization.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from quality.ceiling import CeilingTracker

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "configs" / "cliche_clusters.yaml"


def load_cluster_config(config_path: Path) -> Dict[str, Any]:
    """Load cliche cluster definitions from YAML."""
    if not config_path.exists():
        logger.warning("Cliche cluster config not found: %s", config_path)
        return {"clusters": {}}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {"clusters": {}}


def _compile_patterns(cluster_def: Dict[str, Any]) -> List[Tuple[re.Pattern, List[str]]]:
    """Compile regex patterns from a cluster definition.

    Returns list of (compiled_regex, replacements) tuples.
    Handles both old format (patterns as strings) and new format
    (patterns as dicts with regex + replacements).
    """
    compiled = []
    for p in cluster_def.get("patterns", []):
        if isinstance(p, str):
            # Old format: pattern string only, no replacements
            try:
                compiled.append((re.compile(p, re.IGNORECASE), []))
            except re.error as e:
                logger.warning("Invalid regex: %s — %s", p, e)
        elif isinstance(p, dict):
            # New format: {regex: ..., replacements: [...]}
            regex_str = p.get("regex", "")
            replacements = p.get("replacements", [])
            try:
                compiled.append((re.compile(regex_str, re.IGNORECASE), replacements))
            except re.error as e:
                logger.warning("Invalid regex: %s — %s", regex_str, e)
    return compiled


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
        data = load_cluster_config(config_path or _DEFAULT_CONFIG_PATH)
    else:
        data = clusters_dict

    clusters = data.get("clusters", {})
    results: Dict[str, Dict[str, Any]] = {}

    for cluster_name, cluster_def in clusters.items():
        label = cluster_def.get("label", cluster_name)
        threshold = cluster_def.get("threshold", 10)
        compiled = _compile_patterns(cluster_def)

        total_hits = 0
        scene_hits = 0
        examples: List[str] = []
        per_scene: List[int] = []

        for scene in scenes:
            scene_count = 0
            for regex, _ in compiled:
                matches = list(regex.finditer(scene))
                scene_count += len(matches)
                if matches and len(examples) < 3:
                    for m in matches:
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


def repair_clusters(
    scenes: List[str],
    config_path: Optional[Path] = None,
    clusters_dict: Optional[Dict[str, Any]] = None,
    only_flagged: bool = True,
    ceiling: Optional["CeilingTracker"] = None,
) -> Tuple[List[str], Dict[str, Any]]:
    """Repair cliche clusters by replacing excess occurrences with alternatives.

    For each cluster, the first `keep_first` occurrences (across the entire
    manuscript, in scene order) are left untouched. Subsequent occurrences
    are replaced with rotating alternatives from the config.

    Args:
        scenes: List of scene texts in order.
        config_path: Path to cliche_clusters.yaml.
        clusters_dict: Pre-loaded cluster config (overrides config_path).
        only_flagged: If True, only repair clusters that exceed their threshold.
        ceiling: Optional CeilingTracker for edit limits.

    Returns:
        Tuple of (modified_scenes, report_dict).
    """
    if clusters_dict is None:
        data = load_cluster_config(config_path or _DEFAULT_CONFIG_PATH)
    else:
        data = clusters_dict

    clusters = data.get("clusters", {})

    # First pass: detect to know which clusters are flagged
    if only_flagged:
        detection = detect_clusters(scenes, clusters_dict=data)
        flagged_names = set(detection["flagged_names"])
    else:
        flagged_names = set(clusters.keys())

    modified = list(scenes)
    report: Dict[str, Dict[str, Any]] = {}

    # Register scenes with ceiling tracker
    if ceiling:
        for i, text in enumerate(modified):
            ceiling.register_scene(i, len(text.split()))

    for cluster_name, cluster_def in clusters.items():
        if cluster_name not in flagged_names:
            continue

        keep_first = cluster_def.get("keep_first", 2)
        compiled = _compile_patterns(cluster_def)

        pattern_occurrence: Dict[int, int] = {}
        pattern_replacement_idx: Dict[int, int] = {}
        cluster_replaced = 0
        cluster_found = 0

        for scene_idx in range(len(modified)):
            text = modified[scene_idx]
            any_changed = False

            for pat_idx, (regex, replacements) in enumerate(compiled):
                if pat_idx not in pattern_occurrence:
                    pattern_occurrence[pat_idx] = 0
                    pattern_replacement_idx[pat_idx] = 0

                matches = list(regex.finditer(text))
                if not matches:
                    continue

                cluster_found += len(matches)

                for match in reversed(matches):
                    pattern_occurrence[pat_idx] += 1
                    total_cluster_occ = sum(pattern_occurrence.values())

                    if total_cluster_occ <= keep_first:
                        continue

                    if not replacements:
                        continue

                    # Check ceiling before editing
                    if ceiling and not ceiling.can_edit(
                        scene_idx, family=cluster_name
                    ):
                        continue

                    ridx = pattern_replacement_idx[pat_idx]
                    repl = replacements[ridx % len(replacements)]
                    pattern_replacement_idx[pat_idx] = ridx + 1

                    original = match.group()
                    if original[0].isupper():
                        repl = repl[0].upper() + repl[1:]

                    text = text[: match.start()] + repl + text[match.end() :]
                    cluster_replaced += 1
                    any_changed = True

                    if ceiling:
                        ceiling.record_edit(scene_idx, family=cluster_name)

            if any_changed:
                modified[scene_idx] = text

        if cluster_found > 0:
            report[cluster_name] = {
                "label": cluster_def.get("label", cluster_name),
                "found": cluster_found,
                "kept": min(keep_first, cluster_found),
                "replaced": cluster_replaced,
            }
            if cluster_replaced > 0:
                logger.info(
                    "Cluster '%s': %d found, %d kept, %d replaced",
                    cluster_name, cluster_found,
                    min(keep_first, cluster_found), cluster_replaced,
                )

    total_replaced = sum(r["replaced"] for r in report.values())
    summary = {
        "clusters_repaired": len([r for r in report.values() if r["replaced"] > 0]),
        "total_replaced": total_replaced,
        "per_cluster": report,
    }

    return modified, summary
