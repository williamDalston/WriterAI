"""Centralized policy schema — Pydantic models for all rule ecosystems.

Single source of truth for cleanup, validation, lexicon, quality polish,
and export gating rules.  Loaded once per pipeline run, passed everywhere.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sub-models for CleanupPolicy
# ---------------------------------------------------------------------------

class InlinePattern(BaseModel):
    """Named inline cleanup regex (Phase 3 of _clean_scene_content)."""
    name: str
    pattern: str


class RegexPattern(BaseModel):
    """Extra regex pattern from YAML config."""
    name: str = "custom_regex"
    pattern: str


# ---------------------------------------------------------------------------
# Sub-models for ValidationPolicy
# ---------------------------------------------------------------------------

class MetaTextPattern(BaseModel):
    """Export-time meta-text detection pattern."""
    regex: str
    code: str = "META_TEXT"
    pattern_name: str


# ---------------------------------------------------------------------------
# Sub-models for QualityPolishPolicy
# ---------------------------------------------------------------------------

class CeilingConfig(BaseModel):
    max_edits_per_scene: int = 15
    max_edits_per_1k_words: float = 8.0
    max_per_family_per_chapter: int = 5
    max_pct_sentences_changed: float = 20.0


class PhraseSuppressionConfig(BaseModel):
    keep_first_default: int = 2
    enabled: bool = True


class DialogueTrimmingConfig(BaseModel):
    max_tag_words: int = 12
    enabled: bool = True


class EmotionDiversificationConfig(BaseModel):
    keep_first: int = 2
    density_threshold: float = 5.0
    enabled: bool = True


class ClicheClusterConfig(BaseModel):
    only_flagged: bool = True
    enabled: bool = True


class PhraseMiningConfig(BaseModel):
    min_n: int = 3
    max_n: int = 7
    min_total_count: int = 8
    min_scene_count: int = 4
    min_content_ratio: float = 0.40
    max_phrases: int = 50
    max_examples: int = 3
    ignore_phrases: List[str] = Field(default_factory=list)
    ignore_regex: List[str] = Field(default_factory=list)
    enabled: bool = True


class ScorecardRegressionConfig(BaseModel):
    """Run-to-run scorecard comparison configuration."""
    enabled: bool = False
    compare_to: str = "last_successful"  # "last_successful" | "previous" | "baseline"
    baseline_run_id: str = ""
    regression_threshold: float = 0.05
    warn_on_regression: bool = True
    fail_on_regression: bool = False
    max_history: int = 50


class ScorecardMetricWeight(BaseModel):
    """Per-metric weight and failure behavior for weighted scorecard."""
    weight: float = 0.20
    action_on_fail: str = "warn"  # "warn" | "fail" | "off"


class ScorecardWeightsConfig(BaseModel):
    """Weighted scorecard configuration — genre-tunable metric importance."""
    mode: str = "boolean"  # "boolean" (all-or-nothing) | "weighted"
    pass_score: float = 0.70  # minimum weighted score to pass (weighted mode)
    lexical_diversity: ScorecardMetricWeight = Field(
        default_factory=lambda: ScorecardMetricWeight(weight=0.20, action_on_fail="warn"),
    )
    dialogue_density: ScorecardMetricWeight = Field(
        default_factory=lambda: ScorecardMetricWeight(weight=0.20, action_on_fail="warn"),
    )
    emotional_diversity: ScorecardMetricWeight = Field(
        default_factory=lambda: ScorecardMetricWeight(weight=0.20, action_on_fail="warn"),
    )
    verb_specificity: ScorecardMetricWeight = Field(
        default_factory=lambda: ScorecardMetricWeight(weight=0.20, action_on_fail="warn"),
    )
    scene_endings: ScorecardMetricWeight = Field(
        default_factory=lambda: ScorecardMetricWeight(weight=0.20, action_on_fail="warn"),
    )


class QualityMetersConfig(BaseModel):
    """Thresholds for deterministic quality meters — genre-tunable."""
    # Voice distinctiveness
    voice_overlap_threshold: float = 0.55
    catchphrase_dominance_threshold: float = 0.40
    min_rhythm_variance: float = 3.0
    pronoun_lookback_chars: int = 300
    # Scorecard (F1)
    lexical_diversity_min: float = 0.40
    dialogue_variance_min: float = 0.01
    emotional_entropy_min: float = 1.5
    verb_specificity_min: float = 0.30
    ending_evenness_min: float = 0.40
    ttr_window: int = 500
    # Scorecard weighting
    scorecard_weights: ScorecardWeightsConfig = Field(
        default_factory=ScorecardWeightsConfig,
    )
    # Scorecard regression (run-to-run comparison)
    scorecard_regression: ScorecardRegressionConfig = Field(
        default_factory=ScorecardRegressionConfig,
    )
    # Repetition
    repetition_local_window: int = 10
    # Scene similarity
    scene_similarity_threshold: float = 0.50
    # Hot phrase feedback
    max_hot_phrases_feedback: int = 15
    # Continuity
    character_mention_threshold: int = 3
    transition_search_chars: int = 500


# ---------------------------------------------------------------------------
# Top-level policy sections
# ---------------------------------------------------------------------------

class CleanupPolicy(BaseModel):
    """Rules for _clean_scene_content phases 1.5 / 1.6 / 3."""
    truncate_markers: List[str] = Field(default_factory=list)
    preamble_markers: List[str] = Field(default_factory=list)
    inline_patterns: List[InlinePattern] = Field(default_factory=list)
    regex_patterns: List[RegexPattern] = Field(default_factory=list)
    disabled_builtins: List[str] = Field(default_factory=list)


class ValidationPolicy(BaseModel):
    """Rules for scene_validator.py meta-text detection."""
    meta_text_patterns: List[MetaTextPattern] = Field(default_factory=list)
    suspect_name_threshold: int = 3
    min_scene_words: int = 100


class LexiconPolicy(BaseModel):
    """Per-project vocabulary rules."""
    allow_characters: List[str] = Field(default_factory=list)
    allow_locations: List[str] = Field(default_factory=list)
    block_names: List[str] = Field(default_factory=list)
    block_terms: List[str] = Field(default_factory=list)
    style_avoid: List[str] = Field(default_factory=list)
    foreign_whitelist: List[str] = Field(default_factory=list)


class QualityPolishPolicy(BaseModel):
    """Subsumes quality/policy.py _FALLBACK_POLICY."""
    enabled_passes: List[str] = Field(default_factory=lambda: [
        "phrase_mining",
        "phrase_suppression",
        "dialogue_trimming",
        "emotion_diversification",
        "cliche_repair",
    ])
    ceiling: CeilingConfig = Field(default_factory=CeilingConfig)
    phrase_suppression: PhraseSuppressionConfig = Field(
        default_factory=PhraseSuppressionConfig,
    )
    dialogue_trimming: DialogueTrimmingConfig = Field(
        default_factory=DialogueTrimmingConfig,
    )
    emotion_diversification: EmotionDiversificationConfig = Field(
        default_factory=EmotionDiversificationConfig,
    )
    cliche_clusters: ClicheClusterConfig = Field(
        default_factory=ClicheClusterConfig,
    )
    phrase_mining: PhraseMiningConfig = Field(
        default_factory=PhraseMiningConfig,
    )
    quality_meters: QualityMetersConfig = Field(
        default_factory=QualityMetersConfig,
    )


class OutlineDiversityPolicy(BaseModel):
    """Config for outline diversity validation after master_outline stage."""
    mode: str = "warn"  # "warn" | "strict" | "off"
    window: int = 5
    adjacent_threshold: float = 0.80
    window_threshold: float = 0.70
    max_same_function_ratio: float = 0.45
    max_regen_attempts: int = 2  # strict mode: regen flagged scenes up to N times


class ProfileCompletenessPolicy(BaseModel):
    """Config for character profile completeness check before scene_drafting."""
    mode: str = "warn"  # "warn" | "strict" | "off"
    min_score: float = 0.70
    major_role_threshold: float = 0.80
    auto_patch: bool = True  # strict mode: LLM-patch missing fields


class ExportGatePolicy(BaseModel):
    """Pre-export validation gate."""
    enabled: bool = True
    fail_on_severity: List[str] = Field(
        default_factory=lambda: ["CRITICAL", "HIGH"],
    )


class Policy(BaseModel):
    """Root policy object — single source of truth for all rule ecosystems."""
    policy_version: str = "1.0"
    cleanup: CleanupPolicy = Field(default_factory=CleanupPolicy)
    validation: ValidationPolicy = Field(default_factory=ValidationPolicy)
    lexicon: LexiconPolicy = Field(default_factory=LexiconPolicy)
    quality_polish: QualityPolishPolicy = Field(
        default_factory=QualityPolishPolicy,
    )
    export_gate: ExportGatePolicy = Field(default_factory=ExportGatePolicy)
    outline_diversity: OutlineDiversityPolicy = Field(
        default_factory=OutlineDiversityPolicy,
    )
    profile_completeness: ProfileCompletenessPolicy = Field(
        default_factory=ProfileCompletenessPolicy,
    )
