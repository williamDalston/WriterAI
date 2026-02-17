"""Policy loader — builds a Policy from hardcoded defaults + YAML overrides.

Resolution chain (each layer overrides the previous):
    1. default_policy()  — hardcoded baselines (exact copies of current code)
    2. configs/cleanup_patterns.yaml  — migrated into cleanup section
    3. projects/<id>/policy.yaml  — project-level overrides
    4. projects/<id>/lexicon.yaml  — merged into lexicon section

Missing files = no-op (debug log only).  Never crashes on load.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .merge import deep_merge
from .schema import (
    CleanupPolicy,
    ExportGatePolicy,
    InlinePattern,
    LexiconPolicy,
    MetaTextPattern,
    PhraseMiningConfig,
    Policy,
    QualityPolishPolicy,
    RegexPattern,
    ValidationPolicy,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Hardcoded defaults — exact copies of values currently scattered in code
# ---------------------------------------------------------------------------

_DEFAULT_TRUNCATE_MARKERS = [
    "the rest remains unchanged",
    "rest of the scene remains unchanged",
    "rest of the chapter remains unchanged",
    "everything after this remains unchanged",
    "no further changes were made",
]

_DEFAULT_PREAMBLE_MARKERS = [
    "certainly! here is",
    "here is the revised",
    "below is the updated",
    "as requested, here is",
    "sure! here's",
]

# From pipeline.py _named_inline_patterns (~line 995-1035)
_DEFAULT_INLINE_PATTERNS = [
    InlinePattern(name="rest_unchanged", pattern=r'(?:The )?rest (?:of (?:the |this )?(?:scene|chapter|text|content) )?(?:remains?|is) unchanged[^.]*[.\s]*'),
    InlinePattern(name="rest_unchanged_bracket", pattern=r'\[(?:The )?rest (?:of (?:the |this )?(?:scene|chapter))? remains unchanged[^\]]*\]\s*'),
    InlinePattern(name="current_scene_header", pattern=r'CURRENT SCENE(?: MODIFIED)?:\s*'),
    InlinePattern(name="visible_pct_marker", pattern=r'Visible:\s*\d+%\s*[–—-]\s*\d+%\s*'),
    InlinePattern(name="enhanced_scene_header", pattern=r'(?:ENHANCED|EXPANDED|POLISHED|FIXED|REVISED) SCENE:\s*'),
    InlinePattern(name="heres_revised", pattern=r"(?:Sure[,.]?\s*)?[Hh]ere'?s?\s+(?:the |a )?(?:revised|enhanced|polished|expanded|edited)\s+(?:version|scene|text|content)[.:]\s*"),
    InlinePattern(name="hook_instruction_bleed", pattern=r'A great chapter-(?:ending|opening) hook can be:\s*(?:\n[-•*][^\n]+)*'),
    InlinePattern(name="writing_tips_bullets", pattern=r'(?:\n[-•*]\s*(?:A cliffhanger|In medias res|A striking sensory|A provocative|Immediate conflict|Disorientation|A kiss or romantic|A threat delivered|A question raised|A twist revealed|An emotional gut-punch|A decision made)[^\n]*)+'),
    InlinePattern(name="scene_header_chapter", pattern=r'Chapter\s+\d+,?\s*Scene\s+\d+\s*(?:POV:[^\n]*)?'),
    InlinePattern(name="scene_header_pov", pattern=r'POV:\s*FIRST PERSON[^\n]*'),
    InlinePattern(name="scene_header_count", pattern=r'Scene\s+\d+\s+of\s+\d+[^\n]*'),
    InlinePattern(name="xml_tag_scene", pattern=r'</?scene[^>]*>'),
    InlinePattern(name="xml_tag_chapter", pattern=r'</?chapter[^>]*>'),
    InlinePattern(name="xml_tag_content", pattern=r'</?content[^>]*>'),
    InlinePattern(name="beat_sheet_physical", pattern=r'Physical beats:\s*(?:\n[-•*][^\n]+)*'),
    InlinePattern(name="beat_sheet_emotional", pattern=r'Emotional beats:\s*(?:\n[-•*][^\n]+)*'),
    InlinePattern(name="beat_sheet_sensory", pattern=r'Sensory details:\s*(?:\n[-•*][^\n]+)*'),
]

# From scene_validator.py META_TEXT_PATTERNS (lines 19-29)
_DEFAULT_META_TEXT_PATTERNS = [
    MetaTextPattern(regex=r"certainly!?\s*(?:here\s+is|here's)", code="META_TEXT", pattern_name="certainly_preamble"),
    MetaTextPattern(regex=r"of\s+course!?\s*(?:here\s+is|here's)", code="META_TEXT", pattern_name="of_course_preamble"),
    MetaTextPattern(regex=r"here\s+is\s+the\s+revised\b", code="META_TEXT", pattern_name="here_is_revised"),
    MetaTextPattern(regex=r"below\s+is\s+the\s+(?:revised|updated)\b", code="META_TEXT", pattern_name="below_is_updated"),
    MetaTextPattern(regex=r"as\s+requested,?\s*(?:here\s+is|here's)", code="META_TEXT", pattern_name="as_requested"),
    MetaTextPattern(regex=r"sure!?\s*(?:here\s+is|here's)", code="META_TEXT", pattern_name="sure_preamble"),
    MetaTextPattern(regex=r"(?:the\s+)?rest\s+(?:of\s+the\s+(?:scene|chapter)\s+)?(?:remains?|is)\s+unchanged", code="META_TEXT", pattern_name="rest_unchanged"),
    MetaTextPattern(regex=r"i\s+can\s+help\s+with\b", code="META_TEXT", pattern_name="i_can_help"),
    MetaTextPattern(regex=r"let\s+me\s+know\s+if\s+you\s+want\b", code="META_TEXT", pattern_name="let_me_know"),
]

# Default forbidden phrases for prose generation (from pipeline.py ~line 6804)
_DEFAULT_STYLE_AVOID = [
    "couldn't help but",
    "found myself",
    "a sense of",
    "I realized",
    "the weight of",
    "more than just",
    "a mix of",
    "a hint of",
    "a wave of",
    "something shifted",
    "hung in the air",
    "settled over her/him/them/me",
    "washed over",
    "cut through the silence/tension/air",
    "I couldn't shake",
]


# ---------------------------------------------------------------------------
# default_policy() — returns exact current behavior
# ---------------------------------------------------------------------------

def default_policy() -> Policy:
    """Return a Policy populated with all current hardcoded values.

    When no policy.yaml or lexicon.yaml exists, this is what every consumer
    sees.  Changing a default here changes it for ALL projects that don't
    override it — do so carefully.
    """
    return Policy(
        policy_version="1.0",
        cleanup=CleanupPolicy(
            truncate_markers=list(_DEFAULT_TRUNCATE_MARKERS),
            preamble_markers=list(_DEFAULT_PREAMBLE_MARKERS),
            inline_patterns=[p.model_copy() for p in _DEFAULT_INLINE_PATTERNS],
            regex_patterns=[],
            disabled_builtins=[],
        ),
        validation=ValidationPolicy(
            meta_text_patterns=[p.model_copy() for p in _DEFAULT_META_TEXT_PATTERNS],
            suspect_name_threshold=3,
            min_scene_words=100,
        ),
        lexicon=LexiconPolicy(
            style_avoid=list(_DEFAULT_STYLE_AVOID),
        ),
        quality_polish=QualityPolishPolicy(),
        export_gate=ExportGatePolicy(),
    )


# ---------------------------------------------------------------------------
# YAML loading helpers
# ---------------------------------------------------------------------------

def _safe_yaml_load(path: Path) -> Optional[Dict[str, Any]]:
    """Load a YAML file; return None on any failure."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else None
    except Exception as exc:
        logger.warning("Failed to load %s: %s", path, exc)
        return None


def _migrate_cleanup_yaml(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert cleanup_patterns.yaml into a policy-shaped dict fragment.

    Only touches the ``cleanup`` key so it can be deep-merged into the
    policy dict without clobbering other sections.
    """
    cleanup: Dict[str, Any] = {}

    markers = data.get("inline_truncate_markers")
    if isinstance(markers, list):
        cleanup["truncate_markers"] = markers

    preambles = data.get("inline_preamble_markers")
    if isinstance(preambles, list):
        cleanup["preamble_markers"] = preambles

    disabled = data.get("disabled_builtins")
    if isinstance(disabled, list):
        cleanup["disabled_builtins"] = disabled

    regex_list = data.get("regex_patterns")
    if isinstance(regex_list, list):
        cleanup["regex_patterns"] = [
            {"name": item.get("name", "custom_regex"), "pattern": item["pattern"]}
            for item in regex_list
            if isinstance(item, dict) and item.get("pattern")
        ]

    inline_list = data.get("inline")
    if isinstance(inline_list, list):
        extra = []
        for item in inline_list:
            if isinstance(item, str):
                extra.append({"name": "custom_inline", "pattern": item})
            elif isinstance(item, dict) and item.get("pattern"):
                extra.append({"name": item.get("name", "custom_inline"), "pattern": item["pattern"]})
        if extra:
            cleanup.setdefault("regex_patterns", []).extend(extra)

    return {"cleanup": cleanup} if cleanup else {}


def _migrate_lexicon_yaml(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert lexicon.yaml into a policy-shaped dict fragment."""
    lexicon: Dict[str, Any] = {}

    allow = data.get("allow", {})
    if isinstance(allow, dict):
        if isinstance(allow.get("characters"), list):
            lexicon["allow_characters"] = allow["characters"]
        if isinstance(allow.get("locations"), list):
            lexicon["allow_locations"] = allow["locations"]

    block = data.get("block", {})
    if isinstance(block, dict):
        if isinstance(block.get("names"), list):
            lexicon["block_names"] = block["names"]
        if isinstance(block.get("terms"), list):
            lexicon["block_terms"] = block["terms"]

    if isinstance(data.get("style_avoid"), list):
        lexicon["style_avoid"] = data["style_avoid"]

    if isinstance(data.get("foreign_whitelist"), list):
        lexicon["foreign_whitelist"] = data["foreign_whitelist"]

    return {"lexicon": lexicon} if lexicon else {}


# ---------------------------------------------------------------------------
# load_policy() — the main entry point
# ---------------------------------------------------------------------------

def load_policy(project_path: Optional[Path] = None) -> Policy:
    """Load policy with merge chain.

    Resolution order (each overrides previous):
        1. ``default_policy()``  (hardcoded baselines)
        2. ``configs/cleanup_patterns.yaml``  (auto-migrated)
        3. ``<project_path>/policy.yaml``  (project overrides)
        4. ``<project_path>/lexicon.yaml``  (merged into lexicon)

    Args:
        project_path: Path to the project directory (e.g.
            ``prometheus_novel/data/projects/burning-vows/``).
            If *None*, only hardcoded defaults are used.

    Returns:
        Fully resolved :class:`Policy`.
    """
    base_dict = default_policy().model_dump()

    # Layer 2: configs/cleanup_patterns.yaml (lives next to source, not per-project)
    configs_dir = Path(__file__).resolve().parent.parent / "configs"
    cleanup_yaml = _safe_yaml_load(configs_dir / "cleanup_patterns.yaml")
    if cleanup_yaml:
        fragment = _migrate_cleanup_yaml(cleanup_yaml)
        if fragment:
            base_dict = deep_merge(base_dict, fragment)
            logger.debug("Policy: merged cleanup_patterns.yaml")

    # Layer 3: project policy.yaml
    if project_path:
        project_dir = Path(project_path)
        policy_yaml = _safe_yaml_load(project_dir / "policy.yaml")
        if policy_yaml:
            base_dict = deep_merge(base_dict, policy_yaml)
            logger.info("Policy: merged project policy.yaml from %s", project_dir)

        # Layer 4: project lexicon.yaml
        lexicon_yaml = _safe_yaml_load(project_dir / "lexicon.yaml")
        if lexicon_yaml:
            fragment = _migrate_lexicon_yaml(lexicon_yaml)
            if fragment:
                base_dict = deep_merge(base_dict, fragment)
                logger.info("Policy: merged project lexicon.yaml from %s", project_dir)

    try:
        return Policy.model_validate(base_dict)
    except Exception as exc:
        logger.error("Policy validation failed, falling back to defaults: %s", exc)
        return default_policy()
