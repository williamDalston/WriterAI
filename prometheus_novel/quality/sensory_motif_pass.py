"""Sensory motif diversification pass.

Tracks primary sensory motifs (lemons, salt, etc.) per 5,000 words.
When a motif exceeds its threshold, replaces excess occurrences with
swap candidates to avoid sensory overload and repetition.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)

_WORDS_PER_UNIT = 5000


def _count_words(texts: List[str]) -> int:
    """Approximate word count across all scene texts."""
    return sum(len(t.split()) for t in texts)


def _load_motif_config(config_path: Path) -> Dict[str, Dict[str, Any]]:
    """Load sensory motifs config. Returns motif_name -> {pattern, max_per_5k, swap_candidates}."""
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("motifs", {})


def process_sensory_motifs(
    texts: List[str],
    config_path: Optional[Path] = None,
    words_per_unit: int = _WORDS_PER_UNIT,
) -> Tuple[List[str], Dict[str, Any]]:
    """Apply sensory motif diversification.

    For each motif exceeding max_per_5k per N words, replace excess
    occurrences with rotating swap candidates.

    Returns:
        (modified_texts, report_dict)
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent / "configs" / "sensory_motifs.yaml"

    motifs = _load_motif_config(config_path)
    if not motifs:
        return texts, {"skipped": "no motif config"}

    total_words = _count_words(texts)
    report: Dict[str, Any] = {
        "total_words": total_words,
        "motifs_processed": 0,
        "total_replacements": 0,
        "per_motif": {},
    }

    modified = list(texts)

    for motif_name, motif_cfg in motifs.items():
        pattern_str = motif_cfg.get("pattern", "")
        if not pattern_str:
            continue
        max_per_5k = motif_cfg.get("max_per_5k", 4)
        swap_candidates = motif_cfg.get("swap_candidates", [])
        if not swap_candidates:
            continue

        try:
            pattern = re.compile(pattern_str, re.IGNORECASE)
        except re.error as e:
            logger.warning("Sensory motif '%s' invalid regex: %s", motif_name, e)
            continue

        # Count total occurrences across manuscript
        all_matches: List[Tuple[int, int, str]] = []  # (scene_idx, char_start, matched_text)
        for scene_idx, text in enumerate(modified):
            for m in pattern.finditer(text):
                all_matches.append((scene_idx, m.start(), m.group()))

        count = len(all_matches)
        if count == 0:
            report["per_motif"][motif_name] = {
                "count": 0,
                "threshold": 0,
                "replaced": 0,
            }
            continue

        # Threshold: (total_words / 5000) * max_per_5k, rounded down
        units = max(1, total_words // words_per_unit)
        threshold = int(units * max_per_5k)
        to_replace = max(0, count - threshold)

        if to_replace == 0:
            report["per_motif"][motif_name] = {
                "count": count,
                "threshold": threshold,
                "replaced": 0,
            }
            continue

        report["motifs_processed"] += 1
        report["total_replacements"] += to_replace
        report["per_motif"][motif_name] = {
            "count": count,
            "threshold": threshold,
            "replaced": to_replace,
        }

        # Replace excess occurrences — process from end backwards so positions stay valid
        swap_idx = 0
        matches_to_replace = all_matches[-to_replace:]
        for scene_idx, char_start, matched in reversed(matches_to_replace):
            repl = swap_candidates[swap_idx % len(swap_candidates)]
            swap_idx += 1
            if matched and matched[0].isupper():
                repl = repl[0].upper() + repl[1:] if len(repl) > 1 else repl.upper()

            text = modified[scene_idx]
            # Replace this occurrence — work backwards so char_start is still valid
            modified[scene_idx] = text[:char_start] + repl + text[char_start + len(matched) :]

        logger.info(
            "Sensory motif '%s': %d occurrences, threshold %d, replaced %d",
            motif_name, count, threshold, to_replace,
        )

    return modified, report
