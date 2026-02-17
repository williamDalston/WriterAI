"""
Config Schema Validator — load-time validation with flexible modes.

Catches typos (protaganist), missing required keys, and recommends optional keys.
Config-driven: config.enhancements.config_validation.enabled, mode: warn|strict|off
"""

import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("config_validator")

REQUIRED_KEYS = ["synopsis", "premise"]  # At least one
RECOMMENDED_KEYS = [
    "protagonist", "genre", "writing_style", "strategic_guidance",
    "key_plot_points", "central_conflict", "tone",
]
COMMON_TYPOS = {
    "protaganist": "protagonist",
    "antaganist": "antagonist",
    "synoposis": "synopsis",
    "charachter": "character",
    "writeing_style": "writing_style",
}
VALID_KEYS = {
    "title", "synopsis", "premise", "genre", "protagonist", "antagonist",
    "other_characters", "setting", "world_rules", "tone", "themes", "motifs",
    "writing_style", "avoid", "influences", "key_plot_points", "central_conflict",
    "central_question", "subplots", "strategic_guidance", "target_length",
    "project_name", "budget_usd", "model_defaults", "defense", "export",
    "enhancements", "style_samples", "_project_path",
}


def validate_config(
    config: Dict[str, Any],
    mode: str = "warn",
) -> Tuple[bool, List[str]]:
    """Validate config. Returns (pass, list of warning/error strings)."""
    issues = []

    if mode == "off":
        return True, []

    # 1. Typos: keys that look like common typos
    for key in config:
        if key.lower() in COMMON_TYPOS:
            suggestion = COMMON_TYPOS[key.lower()]
            msg = f'Config key "{key}" may be a typo. Did you mean "{suggestion}"?'
            if mode == "strict":
                issues.append(f"ERROR: {msg}")
            else:
                issues.append(f"WARN: {msg}")
                logger.warning(msg)

    # 2. Required: at least synopsis or premise
    has_story = bool(config.get("synopsis") or config.get("premise"))
    if not has_story:
        msg = "Config missing required story input: add 'synopsis' or 'premise'"
        if mode == "strict":
            issues.append(f"ERROR: {msg}")
        else:
            issues.append(f"WARN: {msg}")
            logger.warning(msg)

    # 3. Recommended but missing
    for key in RECOMMENDED_KEYS:
        if key not in config or (isinstance(config.get(key), str) and not config[key].strip()):
            if key == "strategic_guidance" and isinstance(config.get(key), dict):
                continue
            issues.append(f"INFO: Recommended key '{key}' is missing or empty")

    # 4. Unknown keys (lenient: only log, don't fail)
    for key in config:
        if key.startswith("_"):
            continue
        key_lower = key.lower().replace("-", "_")
        known = any(k.lower().replace("-", "_") == key_lower for k in VALID_KEYS)
        if not known and key not in ("cover", "status"):
            logger.debug("Config has unknown key: %s", key)

    passed = not any(s.startswith("ERROR") for s in issues)
    return passed, issues
