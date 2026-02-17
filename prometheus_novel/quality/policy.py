"""Project quality policy loader — DEPRECATED.

.. deprecated::
    This module is superseded by ``prometheus_novel.policy`` (centralized
    policy layer).  All rule ecosystems — cleanup, validation, lexicon,
    quality polish, and export gating — are now managed by a single
    ``Policy`` Pydantic model loaded once at pipeline init.

    Migration guide:
        Old::

            from quality.policy import load_policy, is_pass_enabled
            policy = load_policy(genre="romance", project_overrides={...})
            if is_pass_enabled(policy, "phrase_mining"): ...

        New::

            from policy import load_policy as load_central_policy
            policy = load_central_policy(project_path=project_path)
            qp = policy.quality_polish.model_dump()
            if is_pass_enabled(qp, "phrase_mining"): ...

    This shim will be removed in a future release.
"""

import logging
import warnings
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)

_DEFAULT_POLICY_PATH = Path(__file__).parent.parent / "configs" / "quality_policy.yaml"

# ── Deprecation helpers ──────────────────────────────────────────────

_DEPRECATION_MSG = (
    "quality.policy is deprecated — use prometheus_novel.policy instead. "
    "See module docstring for migration guide."
)


def _warn_once() -> None:
    warnings.warn(_DEPRECATION_MSG, DeprecationWarning, stacklevel=3)


# ── Legacy deep merge (kept for backward compat) ────────────────────

def _deep_merge(base: Dict, override: Dict) -> Dict:
    """Recursively merge override into base (override wins).

    .. deprecated:: Use ``policy.merge.deep_merge`` instead.
    """
    merged = deepcopy(base)
    for k, v in override.items():
        if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
            merged[k] = _deep_merge(merged[k], v)
        else:
            merged[k] = deepcopy(v)
    return merged


# Hardcoded fallback when no YAML file is found
_FALLBACK_POLICY: Dict[str, Any] = {
    "ceiling": {
        "max_edits_per_scene": 15,
        "max_edits_per_1k_words": 8.0,
        "max_per_family_per_chapter": 5,
        "max_pct_sentences_changed": 20.0,
    },
    "phrase_suppression": {
        "keep_first_default": 2,
        "enabled": True,
    },
    "dialogue_trimming": {
        "max_tag_words": 12,
        "enabled": True,
    },
    "emotion_diversification": {
        "keep_first": 2,
        "density_threshold": 5.0,
        "enabled": True,
    },
    "cliche_clusters": {
        "only_flagged": True,
        "enabled": True,
    },
    "phrase_mining": {
        "enabled": True,
    },
    "enabled_passes": [
        "phrase_mining",
        "phrase_suppression",
        "dialogue_trimming",
        "emotion_diversification",
        "cliche_repair",
    ],
}


def load_policy(
    genre: str = "romance",
    project_overrides: Optional[Dict[str, Any]] = None,
    policy_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Load quality policy for a genre, with optional project overrides.

    .. deprecated::
        Use ``prometheus_novel.policy.load_policy()`` and access
        ``policy.quality_polish`` instead.

    Resolution order:
        1. Hardcoded fallback
        2. Genre preset from quality_policy.yaml
        3. Project-level overrides from project config.yaml

    Args:
        genre: Genre key matching a preset in quality_policy.yaml.
        project_overrides: Dict from project config's quality_policy section.
        policy_path: Path to quality_policy.yaml (uses default if None).

    Returns:
        Merged policy dict.
    """
    _warn_once()

    policy = deepcopy(_FALLBACK_POLICY)

    # Load YAML presets
    yaml_path = policy_path or _DEFAULT_POLICY_PATH
    if yaml_path.exists():
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            presets = data.get("presets", {})
            genre_key = genre.lower().strip()

            if genre_key in presets:
                policy = _deep_merge(policy, presets[genre_key])
                logger.info("Loaded quality policy preset: %s", genre_key)
            else:
                # Try default_preset
                default_key = data.get("default_preset", "romance")
                if default_key in presets:
                    policy = _deep_merge(policy, presets[default_key])
                    logger.info(
                        "Genre '%s' not found, using default preset: %s",
                        genre_key, default_key,
                    )
        except Exception as e:
            logger.warning("Failed to load quality policy YAML: %s", e)
    else:
        logger.info("No quality_policy.yaml found, using hardcoded defaults")

    # Apply project overrides
    if project_overrides:
        policy = _deep_merge(policy, project_overrides)
        logger.info("Applied %d project-level quality policy overrides", len(project_overrides))

    return policy


def is_pass_enabled(policy: Dict[str, Any], pass_name: str) -> bool:
    """Check if a quality pass is enabled in the policy.

    This function remains fully functional and is the recommended way to
    check pass enablement on both legacy dicts and ``quality_polish.model_dump()``
    dicts from the centralized policy.
    """
    enabled_passes = policy.get("enabled_passes", [])
    if enabled_passes:
        return pass_name in enabled_passes

    # Fallback: check individual pass config
    pass_cfg = policy.get(pass_name, {})
    return pass_cfg.get("enabled", True)
