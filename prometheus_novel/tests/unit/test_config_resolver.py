"""
Unit tests for config resolution and deep merge semantics.
"""

import pytest
import tempfile
from pathlib import Path
import yaml

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from configs.config_resolver import (
    _deep_merge,
    resolve_config,
    resolve_and_write,
)


class TestDeepMerge:
    """Verify deep merge: dicts merge, lists/scalars replace."""

    def test_nested_dict_merge(self):
        """Nested dicts are merged recursively; project can extend env."""
        base = {"a": {"x": 1, "y": 2}}
        overlay = {"a": {"y": 99, "z": 3}}
        result = _deep_merge(base, overlay)
        assert result["a"] == {"x": 1, "y": 99, "z": 3}

    def test_list_replace_not_concat(self):
        """Lists are replaced entirely; no concatenation."""
        base = {"keyword_targets": ["a", "b", "c"]}
        overlay = {"keyword_targets": ["x", "y"]}
        result = _deep_merge(base, overlay)
        assert result["keyword_targets"] == ["x", "y"]

    def test_scalar_replace(self):
        """Scalars are replaced."""
        base = {"title": "Old"}
        overlay = {"title": "New"}
        result = _deep_merge(base, overlay)
        assert result["title"] == "New"

    def test_null_replace(self):
        """None in overlay replaces base value."""
        base = {"opt": "value"}
        overlay = {"opt": None}
        result = _deep_merge(base, overlay)
        assert result["opt"] is None


class TestResolveAndWrite:
    """Verify resolve_and_write produces valid output with provenance."""

    def test_resolved_config_has_provenance(self):
        """Provenance block includes run_id, timestamp_utc, git_commit."""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "proj"
            p.mkdir()
            (p / "config.yaml").write_text(yaml.dump({
                "project_name": "test",
                "title": "Test",
                "synopsis": "x",
                "genre": "sci-fi",
                "protagonist": "y",
                "target_length": "60k",
            }))
            resolved = resolve_and_write(p)
            out = p / "output" / "resolved_config.yaml"
            assert out.exists()
            data = yaml.safe_load(out.read_text())
            prov = data["meta"]["provenance"]
            assert "run_id" in prov
            assert prov["timestamp_utc"].endswith("Z")
            assert "git_commit" in prov
            assert prov["model_routing_summary"] in ("(defaults)", "") or "api=" in prov["model_routing_summary"]
