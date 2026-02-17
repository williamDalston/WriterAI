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
