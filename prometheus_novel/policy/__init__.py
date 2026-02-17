"""Centralized policy layer — single source of truth for all rule ecosystems.

Usage::

    from prometheus_novel.policy import load_policy, default_policy, Policy

    # Load with project overrides (policy.yaml + lexicon.yaml)
    policy = load_policy(project_path=Path("data/projects/burning-vows"))

    # Or use hardcoded defaults (identical to pre-policy behavior)
    policy = default_policy()
"""

from .loader import default_policy, load_policy
from .schema import (
    CleanupPolicy,
    ExportGatePolicy,
    InlinePattern,
    LexiconPolicy,
    MetaTextPattern,
    Policy,
    QualityMetersConfig,
    QualityPolishPolicy,
    RegexPattern,
    ScorecardMetricWeight,
    ScorecardRegressionConfig,
    ScorecardWeightsConfig,
    ValidationPolicy,
)

__all__ = [
    "CleanupPolicy",
    "ExportGatePolicy",
    "InlinePattern",
    "LexiconPolicy",
    "MetaTextPattern",
    "Policy",
    "QualityMetersConfig",
    "QualityPolishPolicy",
    "RegexPattern",
    "ScorecardMetricWeight",
    "ScorecardRegressionConfig",
    "ScorecardWeightsConfig",
    "ValidationPolicy",
    "default_policy",
    "load_policy",
]
