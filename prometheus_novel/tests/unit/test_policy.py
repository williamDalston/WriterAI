"""Tests for centralized policy layer: schema, merge, loader, enforcement."""

import json
import sys
import os
import tempfile
from pathlib import Path

import pytest
import yaml

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from policy.schema import (
    CleanupPolicy,
    ExportGatePolicy,
    InlinePattern,
    LexiconPolicy,
    MetaTextPattern,
    Policy,
    QualityPolishPolicy,
    ValidationPolicy,
)
from policy.merge import deep_merge
from policy.loader import (
    default_policy,
    load_policy,
    _migrate_cleanup_yaml,
    _migrate_lexicon_yaml,
)


# ============================================================================
# 1. TestDefaultPolicy — hardcoded defaults are valid and complete
# ============================================================================


class TestDefaultPolicy:
    def test_returns_valid_policy(self):
        """default_policy() returns a fully populated Policy."""
        p = default_policy()
        assert isinstance(p, Policy)
        assert p.policy_version == "1.0"

    def test_cleanup_has_truncate_markers(self):
        """Cleanup section includes all current truncate markers."""
        p = default_policy()
        assert len(p.cleanup.truncate_markers) >= 5
        assert "the rest remains unchanged" in p.cleanup.truncate_markers

    def test_cleanup_has_preamble_markers(self):
        p = default_policy()
        assert len(p.cleanup.preamble_markers) >= 5
        assert "certainly! here is" in p.cleanup.preamble_markers

    def test_cleanup_has_inline_patterns(self):
        """All 17 built-in inline patterns are present."""
        p = default_policy()
        names = {ip.name for ip in p.cleanup.inline_patterns}
        assert "rest_unchanged" in names
        assert "xml_tag_scene" in names
        assert "beat_sheet_physical" in names
        assert len(p.cleanup.inline_patterns) >= 17

    def test_validation_has_meta_text_patterns(self):
        """All 9 META_TEXT_PATTERNS from scene_validator are present."""
        p = default_policy()
        pattern_names = {m.pattern_name for m in p.validation.meta_text_patterns}
        assert "certainly_preamble" in pattern_names
        assert "rest_unchanged" in pattern_names
        assert "let_me_know" in pattern_names
        assert len(p.validation.meta_text_patterns) == 9

    def test_validation_thresholds(self):
        p = default_policy()
        assert p.validation.suspect_name_threshold == 3
        assert p.validation.min_scene_words == 100

    def test_lexicon_has_style_avoid(self):
        """Default forbidden phrases are present."""
        p = default_policy()
        assert len(p.lexicon.style_avoid) >= 10
        assert "couldn't help but" in p.lexicon.style_avoid
        assert "a sense of" in p.lexicon.style_avoid

    def test_quality_polish_defaults(self):
        """Quality polish defaults match quality/policy.py _FALLBACK_POLICY."""
        p = default_policy()
        qp = p.quality_polish
        assert "phrase_mining" in qp.enabled_passes
        assert "cliche_repair" in qp.enabled_passes
        assert qp.ceiling.max_edits_per_scene == 15
        assert qp.phrase_suppression.keep_first_default == 2
        assert qp.dialogue_trimming.max_tag_words == 12
        assert qp.emotion_diversification.density_threshold == 5.0
        assert qp.cliche_clusters.only_flagged is True

    def test_export_gate_defaults(self):
        p = default_policy()
        assert p.export_gate.enabled is True
        assert "CRITICAL" in p.export_gate.fail_on_severity
        assert "HIGH" in p.export_gate.fail_on_severity


# ============================================================================
# 2. TestPolicyMerge — deep merge semantics
# ============================================================================


class TestPolicyMerge:
    def test_scalars_override(self):
        base = {"a": 1, "b": 2}
        override = {"b": 99}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 99}

    def test_dicts_recurse(self):
        base = {"outer": {"a": 1, "b": 2}}
        override = {"outer": {"b": 99, "c": 3}}
        result = deep_merge(base, override)
        assert result == {"outer": {"a": 1, "b": 99, "c": 3}}

    def test_lists_replace(self):
        """Lists in override REPLACE base entirely (no extend)."""
        base = {"items": [1, 2, 3]}
        override = {"items": [99]}
        result = deep_merge(base, override)
        assert result == {"items": [99]}

    def test_base_not_mutated(self):
        base = {"a": {"x": 1}}
        override = {"a": {"x": 99}}
        deep_merge(base, override)
        assert base["a"]["x"] == 1

    def test_override_not_mutated(self):
        base = {"a": 1}
        override = {"b": [1, 2]}
        result = deep_merge(base, override)
        result["b"].append(3)
        assert override["b"] == [1, 2]

    def test_project_policy_overrides_base(self):
        """Simulate project policy.yaml overriding defaults."""
        base = default_policy().model_dump()
        override = {
            "validation": {"suspect_name_threshold": 5},
            "export_gate": {"fail_on_severity": ["CRITICAL"]},
        }
        merged = deep_merge(base, override)
        p = Policy.model_validate(merged)
        assert p.validation.suspect_name_threshold == 5
        assert p.export_gate.fail_on_severity == ["CRITICAL"]
        # Non-overridden values preserved
        assert len(p.cleanup.truncate_markers) >= 5


# ============================================================================
# 3. TestLexiconEnforcement — block/allow names and terms
# ============================================================================


class TestLexiconEnforcement:
    def test_block_names_populated(self):
        """Block names from lexicon.yaml are loaded."""
        data = {"block": {"names": ["Elara", "Kael"]}}
        fragment = _migrate_lexicon_yaml(data)
        assert fragment["lexicon"]["block_names"] == ["Elara", "Kael"]

    def test_allow_characters_populated(self):
        data = {"allow": {"characters": ["Marco", "Sofia"]}}
        fragment = _migrate_lexicon_yaml(data)
        assert fragment["lexicon"]["allow_characters"] == ["Marco", "Sofia"]

    def test_block_terms_populated(self):
        data = {"block": {"terms": ["zombie", "spaceship"]}}
        fragment = _migrate_lexicon_yaml(data)
        assert fragment["lexicon"]["block_terms"] == ["zombie", "spaceship"]

    def test_style_avoid_populated(self):
        data = {"style_avoid": ["couldn't help but", "I realized"]}
        fragment = _migrate_lexicon_yaml(data)
        assert fragment["lexicon"]["style_avoid"] == ["couldn't help but", "I realized"]

    def test_foreign_whitelist_populated(self):
        data = {"foreign_whitelist": ["señora", "trattoria"]}
        fragment = _migrate_lexicon_yaml(data)
        assert fragment["lexicon"]["foreign_whitelist"] == ["señora", "trattoria"]

    def test_empty_lexicon_returns_empty(self):
        fragment = _migrate_lexicon_yaml({})
        assert fragment == {}


# ============================================================================
# 4. TestExportGate — severity-based export blocking
# ============================================================================


class TestExportGate:
    def test_default_blocks_critical_and_high(self):
        p = default_policy()
        assert p.export_gate.enabled is True
        assert "CRITICAL" in p.export_gate.fail_on_severity
        assert "HIGH" in p.export_gate.fail_on_severity
        assert "LOW" not in p.export_gate.fail_on_severity

    def test_disabled_gate_allows_everything(self):
        p = default_policy()
        p_dict = p.model_dump()
        p_dict["export_gate"]["enabled"] = False
        p2 = Policy.model_validate(p_dict)
        assert p2.export_gate.enabled is False

    def test_custom_severity_list(self):
        p_dict = default_policy().model_dump()
        p_dict["export_gate"]["fail_on_severity"] = ["CRITICAL"]
        p2 = Policy.model_validate(p_dict)
        assert p2.export_gate.fail_on_severity == ["CRITICAL"]
        assert "HIGH" not in p2.export_gate.fail_on_severity

    def test_severity_check_logic(self):
        """Simulate the export gate check: issue severity in fail_on_severity."""
        gate = ExportGatePolicy(enabled=True, fail_on_severity=["CRITICAL", "HIGH"])
        issues = [
            {"severity": "error", "code": "META_TEXT"},
            {"severity": "warning", "code": "SHORT_SCENE"},
        ]
        # Map severity to gate levels
        severity_map = {"error": "HIGH", "warning": "LOW"}
        should_block = gate.enabled and any(
            severity_map.get(i["severity"], "LOW") in gate.fail_on_severity
            for i in issues
        )
        assert should_block is True

    def test_severity_check_passes_when_only_warnings(self):
        gate = ExportGatePolicy(enabled=True, fail_on_severity=["CRITICAL", "HIGH"])
        issues = [{"severity": "warning", "code": "SHORT_SCENE"}]
        severity_map = {"error": "HIGH", "warning": "LOW"}
        should_block = gate.enabled and any(
            severity_map.get(i["severity"], "LOW") in gate.fail_on_severity
            for i in issues
        )
        assert should_block is False


# ============================================================================
# 5. TestBackwardCompat — no policy.yaml produces identical behavior
# ============================================================================


class TestBackwardCompat:
    def test_load_without_project_path(self):
        """load_policy(None) returns valid defaults."""
        p = load_policy(project_path=None)
        assert isinstance(p, Policy)
        assert len(p.cleanup.inline_patterns) >= 17

    def test_load_with_nonexistent_project(self):
        """Missing project dir is a no-op (no crash)."""
        p = load_policy(project_path=Path("/nonexistent/path/does/not/exist"))
        assert isinstance(p, Policy)
        # Defaults still present
        assert len(p.validation.meta_text_patterns) == 9

    def test_cleanup_yaml_migration(self):
        """cleanup_patterns.yaml is auto-migrated into cleanup section."""
        data = {
            "inline_truncate_markers": ["custom marker one"],
            "inline_preamble_markers": ["custom preamble"],
            "disabled_builtins": ["beat_sheet_physical"],
            "regex_patterns": [{"name": "test_pat", "pattern": r"test\d+"}],
        }
        fragment = _migrate_cleanup_yaml(data)
        assert fragment["cleanup"]["truncate_markers"] == ["custom marker one"]
        assert fragment["cleanup"]["preamble_markers"] == ["custom preamble"]
        assert fragment["cleanup"]["disabled_builtins"] == ["beat_sheet_physical"]
        assert len(fragment["cleanup"]["regex_patterns"]) == 1
        assert fragment["cleanup"]["regex_patterns"][0]["name"] == "test_pat"

    def test_full_merge_chain_with_temp_files(self):
        """End-to-end: default + project policy.yaml + lexicon.yaml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)

            # Write a policy.yaml override
            policy_data = {
                "policy_version": "2.0",
                "validation": {"suspect_name_threshold": 5},
                "export_gate": {"fail_on_severity": ["CRITICAL"]},
            }
            with open(project / "policy.yaml", "w", encoding="utf-8") as f:
                yaml.dump(policy_data, f)

            # Write a lexicon.yaml
            lexicon_data = {
                "allow": {"characters": ["Marco", "Sofia"]},
                "block": {"names": ["Elara"], "terms": ["spaceship"]},
                "style_avoid": ["custom avoid phrase"],
                "foreign_whitelist": ["trattoria"],
            }
            with open(project / "lexicon.yaml", "w", encoding="utf-8") as f:
                yaml.dump(lexicon_data, f)

            p = load_policy(project_path=project)

            # policy.yaml overrides applied
            assert p.policy_version == "2.0"
            assert p.validation.suspect_name_threshold == 5
            assert p.export_gate.fail_on_severity == ["CRITICAL"]

            # lexicon.yaml merged
            assert p.lexicon.allow_characters == ["Marco", "Sofia"]
            assert p.lexicon.block_names == ["Elara"]
            assert p.lexicon.block_terms == ["spaceship"]
            assert p.lexicon.style_avoid == ["custom avoid phrase"]
            assert p.lexicon.foreign_whitelist == ["trattoria"]

            # Non-overridden defaults preserved
            assert len(p.cleanup.inline_patterns) >= 17
            assert len(p.validation.meta_text_patterns) == 9

    def test_corrupt_policy_yaml_falls_back(self):
        """Malformed YAML doesn't crash, falls back to defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            with open(project / "policy.yaml", "wb") as f:
                f.write(b'\x80\x81\x82\x00\xff\xfe')

            p = load_policy(project_path=project)
            assert isinstance(p, Policy)
            assert len(p.validation.meta_text_patterns) == 9

    def test_policy_version_stamped(self):
        """policy_version carries through the merge chain."""
        p = default_policy()
        assert p.policy_version == "1.0"
