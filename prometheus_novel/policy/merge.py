"""Deep-merge utility for policy layering.

Single canonical implementation — replaces quality/policy._deep_merge.
Merge rule: dicts recurse (override wins), lists REPLACE, scalars override.
"""

from copy import deepcopy
from typing import Any, Dict


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge *override* into *base*.

    - Dicts: recurse (keys in override win on conflict)
    - Lists: override replaces base entirely (no extend/union)
    - Scalars: override wins

    Neither input is mutated; a fresh dict is returned.
    """
    merged = deepcopy(base)
    for key, value in override.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged
