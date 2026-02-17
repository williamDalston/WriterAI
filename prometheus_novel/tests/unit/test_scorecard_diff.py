"""Tests for scorecard regression — run-to-run comparison."""
import sys
import os
import json
import shutil
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from quality.scorecard_diff import (
    generate_run_id,
    build_run_manifest,
    compute_diff,
    store_and_diff,
    _read_pointer,
    _write_pointer,
    _load_run_scorecard,
    _prune_old_runs,
    _extract_metric_value,
    _extract_metric_pass,
    _compute_status_change,
)
from pathlib import Path


def _make_scorecard(score=0.85, passed=True, lex_avg=0.72, lex_pass=True,
                    dd_var=0.12, dd_pass=True, emo_ent=2.1, emo_pass=True,
                    verb_avg=0.68, verb_pass=True, end_even=0.75, end_pass=True):
    """Build a realistic quality_scorecard.json dict."""
    return {
        "lexical_diversity": {"manuscript_avg": lex_avg, "pass": lex_pass, "per_scene": [lex_avg]},
        "dialogue_density_variance": {"variance": dd_var, "mean": 0.35, "pass": dd_pass, "per_scene": [0.35]},
        "emotional_mode_diversity": {"entropy": emo_ent, "max_entropy": 3.0, "pass": emo_pass, "mode_counts": {"ANGER": 3, "JOY": 2}},
        "verb_specificity_index": {"manuscript_avg": verb_avg, "pass": verb_pass, "per_scene": [verb_avg]},
        "scene_ending_distribution": {"evenness_score": end_even, "pass": end_pass, "ending_counts": {"ACTION": 3, "DIALOGUE": 3}},
        "pass": passed,
        "weighted": {"score": score, "pass_score": 0.70, "pass": passed, "hard_fail": False, "warnings": []},
    }


def _seed_run(runs_dir, run_id, scorecard, passed=True):
    """Create a run directory with scorecard and manifest."""
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "quality_scorecard.json").write_text(
        json.dumps(scorecard, indent=2), encoding="utf-8"
    )
    manifest = {
        "run_id": run_id,
        "timestamp": "2026-02-17T00:00:00+00:00",
        "passed": passed,
        "weighted_score": scorecard.get("weighted", {}).get("score"),
        "hard_fail": False,
        "scene_count": 10,
        "policy_fingerprint": "",
        "model": "gpt-5-mini",
    }
    (run_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


class TestGenerateRunId:
    def test_format(self):
        rid = generate_run_id()
        assert "_" in rid
        parts = rid.split("_")
        assert len(parts) == 2
        assert parts[0].endswith("Z")
        assert len(parts[1]) == 6  # 3 bytes hex

    def test_unique(self):
        ids = {generate_run_id() for _ in range(20)}
        assert len(ids) == 20


class TestBuildRunManifest:
    def test_all_fields_present(self):
        sc = _make_scorecard(score=0.90, passed=True)
        m = build_run_manifest("run-1", sc, policy_hash="abc", model="gpt-5", scene_count=42)
        assert m["run_id"] == "run-1"
        assert m["passed"] is True
        assert m["weighted_score"] == 0.90
        assert m["hard_fail"] is False
        assert m["scene_count"] == 42
        assert m["policy_fingerprint"] == "abc"
        assert m["model"] == "gpt-5"
        assert "timestamp" in m

    def test_failed_scorecard(self):
        sc = _make_scorecard(passed=False)
        m = build_run_manifest("run-2", sc)
        assert m["passed"] is False

    def test_no_weighted_section(self):
        sc = {"pass": True}
        m = build_run_manifest("run-3", sc)
        assert m["weighted_score"] is None
        assert m["hard_fail"] is False


class TestComputeDiff:
    def test_no_previous_run(self):
        sc = _make_scorecard()
        diff = compute_diff(sc, None, "run-1")
        assert diff["compare_to"]["available"] is False
        assert diff["overall"]["score_prev"] is None
        assert diff["overall"]["score_delta"] is None
        assert diff["overall"]["regression"] is False
        for m in diff["metrics"].values():
            assert m["status_change"] == "no_compare"

    def test_improvement_detected(self):
        prev = _make_scorecard(score=0.70, lex_avg=0.50, lex_pass=False)
        curr = _make_scorecard(score=0.90, lex_avg=0.75, lex_pass=True)
        diff = compute_diff(curr, prev, "run-2", "run-1")
        assert diff["compare_to"]["available"] is True
        assert diff["overall"]["score_delta"] == 0.20
        assert diff["overall"]["regression"] is False
        assert "lexical_diversity" in diff["top_contributors"]["improvements"]

    def test_regression_detected(self):
        prev = _make_scorecard(score=0.90, verb_avg=0.80, verb_pass=True)
        curr = _make_scorecard(score=0.60, verb_avg=0.25, verb_pass=False)
        diff = compute_diff(curr, prev, "run-2", "run-1", regression_threshold=0.05)
        assert diff["overall"]["regression"] is True
        assert diff["overall"]["score_delta"] == -0.30
        assert "verb_specificity" in diff["top_contributors"]["regressions"]

    def test_regression_within_threshold(self):
        prev = _make_scorecard(score=0.90)
        curr = _make_scorecard(score=0.88)
        diff = compute_diff(curr, prev, "run-2", "run-1", regression_threshold=0.05)
        assert diff["overall"]["regression"] is False
        assert diff["overall"]["score_delta"] == -0.02

    def test_unchanged_scores(self):
        sc = _make_scorecard(score=0.85)
        diff = compute_diff(sc, sc, "run-2", "run-1")
        assert diff["overall"]["score_delta"] == 0.0
        assert diff["overall"]["regression"] is False
        for m in diff["metrics"].values():
            assert m["status_change"] == "unchanged"

    def test_weights_config_included(self):
        sc = _make_scorecard()
        wcfg = {
            "lexical_diversity": {"weight": 0.30, "action_on_fail": "fail"},
            "dialogue_density": {"weight": 0.10, "action_on_fail": "warn"},
        }
        diff = compute_diff(sc, None, "run-1", weights_cfg=wcfg)
        assert diff["metrics"]["lexical_diversity"]["weight"] == 0.30
        assert diff["metrics"]["lexical_diversity"]["action_on_fail"] == "fail"
        assert diff["metrics"]["dialogue_density"]["weight"] == 0.10


class TestStatusChange:
    def test_no_prev(self):
        assert _compute_status_change(True, None, 0.1) == "no_compare"

    def test_fail_to_pass(self):
        assert _compute_status_change(True, False, 0.1) == "improved"

    def test_pass_to_fail(self):
        assert _compute_status_change(False, True, -0.1) == "regressed"

    def test_both_pass_positive_delta(self):
        assert _compute_status_change(True, True, 0.05) == "improved"

    def test_both_pass_negative_delta(self):
        assert _compute_status_change(True, True, -0.05) == "regressed"

    def test_both_pass_zero_delta(self):
        assert _compute_status_change(True, True, 0.0) == "unchanged"


class TestStoreAndDiff:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_disabled_returns_early(self):
        result = store_and_diff(self.tmpdir, _make_scorecard(), regression_cfg={"enabled": False})
        assert result == {"enabled": False}

    def test_creates_run_dir_and_files(self):
        sc = _make_scorecard()
        cfg = {"enabled": True, "compare_to": "last_successful", "max_history": 50}
        result = store_and_diff(self.tmpdir, sc, regression_cfg=cfg)
        runs_dir = self.tmpdir / "runs"
        assert runs_dir.exists()
        # Should have exactly one run directory
        run_dirs = [d for d in runs_dir.iterdir() if d.is_dir()]
        assert len(run_dirs) == 1
        run_dir = run_dirs[0]
        assert (run_dir / "quality_scorecard.json").exists()
        assert (run_dir / "run_manifest.json").exists()
        assert (run_dir / "scorecard_diff.json").exists()
        # Also written to output root
        assert (self.tmpdir / "scorecard_diff.json").exists()
        # Pointer updated
        latest = json.loads((runs_dir / "latest.json").read_text(encoding="utf-8"))
        assert latest["run_id"] == run_dir.name

    def test_first_run_no_comparison(self):
        sc = _make_scorecard()
        cfg = {"enabled": True, "compare_to": "last_successful"}
        result = store_and_diff(self.tmpdir, sc, regression_cfg=cfg)
        assert result["compare_to"]["available"] is False
        assert result["overall"]["regression"] is False

    def test_compare_to_previous(self):
        runs_dir = self.tmpdir / "runs"
        runs_dir.mkdir(parents=True)
        prev_sc = _make_scorecard(score=0.70, lex_avg=0.50)
        _seed_run(runs_dir, "prev-run", prev_sc, passed=True)
        _write_pointer(runs_dir, "latest.json", "prev-run")

        curr_sc = _make_scorecard(score=0.90, lex_avg=0.75)
        cfg = {"enabled": True, "compare_to": "previous"}
        result = store_and_diff(self.tmpdir, curr_sc, regression_cfg=cfg)
        assert result["compare_to"]["available"] is True
        assert result["compare_to"]["run_id"] == "prev-run"
        assert result["overall"]["score_delta"] == 0.20

    def test_compare_to_last_successful_skips_failed(self):
        runs_dir = self.tmpdir / "runs"
        runs_dir.mkdir(parents=True)

        # Seed a successful run
        good_sc = _make_scorecard(score=0.85, passed=True)
        _seed_run(runs_dir, "good-run", good_sc, passed=True)
        _write_pointer(runs_dir, "last_successful.json", "good-run")

        # Seed a failed run (latest but not last_successful)
        bad_sc = _make_scorecard(score=0.40, passed=False)
        _seed_run(runs_dir, "bad-run", bad_sc, passed=False)
        _write_pointer(runs_dir, "latest.json", "bad-run")

        # Current run compares to last_successful, not latest
        curr_sc = _make_scorecard(score=0.88)
        cfg = {"enabled": True, "compare_to": "last_successful"}
        result = store_and_diff(self.tmpdir, curr_sc, regression_cfg=cfg)
        assert result["compare_to"]["run_id"] == "good-run"
        assert result["overall"]["score_delta"] == 0.03

    def test_missing_compare_target(self):
        runs_dir = self.tmpdir / "runs"
        runs_dir.mkdir(parents=True)
        # Point to a run that doesn't exist
        _write_pointer(runs_dir, "last_successful.json", "ghost-run")

        sc = _make_scorecard()
        cfg = {"enabled": True, "compare_to": "last_successful"}
        result = store_and_diff(self.tmpdir, sc, regression_cfg=cfg)
        assert result["compare_to"]["available"] is False

    def test_successful_run_updates_last_successful_pointer(self):
        sc = _make_scorecard(passed=True)
        cfg = {"enabled": True}
        store_and_diff(self.tmpdir, sc, regression_cfg=cfg)
        runs_dir = self.tmpdir / "runs"
        assert (runs_dir / "last_successful.json").exists()

    def test_failed_run_does_not_update_last_successful_pointer(self):
        runs_dir = self.tmpdir / "runs"
        runs_dir.mkdir(parents=True)
        # Seed a prior successful run
        good_sc = _make_scorecard(passed=True)
        _seed_run(runs_dir, "good-run", good_sc, passed=True)
        _write_pointer(runs_dir, "last_successful.json", "good-run")

        # Current run fails
        bad_sc = _make_scorecard(passed=False)
        cfg = {"enabled": True}
        store_and_diff(self.tmpdir, bad_sc, regression_cfg=cfg)
        # last_successful should still point to good-run
        ptr = json.loads((runs_dir / "last_successful.json").read_text(encoding="utf-8"))
        assert ptr["run_id"] == "good-run"

    def test_baseline_compare(self):
        runs_dir = self.tmpdir / "runs"
        runs_dir.mkdir(parents=True)
        base_sc = _make_scorecard(score=0.80)
        _seed_run(runs_dir, "baseline-001", base_sc, passed=True)

        curr_sc = _make_scorecard(score=0.92)
        cfg = {"enabled": True, "compare_to": "baseline", "baseline_run_id": "baseline-001"}
        result = store_and_diff(self.tmpdir, curr_sc, regression_cfg=cfg)
        assert result["compare_to"]["run_id"] == "baseline-001"
        assert result["overall"]["score_delta"] == 0.12

    def test_regression_threshold(self):
        runs_dir = self.tmpdir / "runs"
        runs_dir.mkdir(parents=True)
        prev_sc = _make_scorecard(score=0.90)
        _seed_run(runs_dir, "prev-run", prev_sc, passed=True)
        _write_pointer(runs_dir, "last_successful.json", "prev-run")

        # Drop of 0.08 with threshold 0.10 → no regression
        curr_sc = _make_scorecard(score=0.82)
        cfg = {"enabled": True, "compare_to": "last_successful", "regression_threshold": 0.10}
        result = store_and_diff(self.tmpdir, curr_sc, regression_cfg=cfg)
        assert result["overall"]["regression"] is False

        # Now last_successful points to the 0.82 run (it passed).
        # Drop of 0.15 from 0.82 → 0.67, exceeds threshold 0.10 → regression
        curr_sc2 = _make_scorecard(score=0.67)
        cfg2 = {"enabled": True, "compare_to": "last_successful", "regression_threshold": 0.10}
        result2 = store_and_diff(self.tmpdir, curr_sc2, regression_cfg=cfg2)
        assert result2["overall"]["regression"] is True


class TestPruneOldRuns:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_prunes_beyond_max_history(self):
        runs_dir = self.tmpdir / "runs"
        runs_dir.mkdir(parents=True)
        # Create 5 run directories with sortable names
        for i in range(5):
            d = runs_dir / f"2026-02-17T00-0{i}-00Z_abc{i:03d}"
            d.mkdir()
            (d / "quality_scorecard.json").write_text("{}", encoding="utf-8")

        assert len([d for d in runs_dir.iterdir() if d.is_dir()]) == 5
        _prune_old_runs(runs_dir, max_history=3)
        remaining = sorted([d.name for d in runs_dir.iterdir() if d.is_dir()])
        assert len(remaining) == 3
        # Should keep the 3 newest (sorted last)
        assert remaining[0] == "2026-02-17T00-02-00Z_abc002"
        assert remaining[2] == "2026-02-17T00-04-00Z_abc004"

    def test_no_prune_within_limit(self):
        runs_dir = self.tmpdir / "runs"
        runs_dir.mkdir(parents=True)
        for i in range(3):
            d = runs_dir / f"run-{i}"
            d.mkdir()
        _prune_old_runs(runs_dir, max_history=5)
        assert len([d for d in runs_dir.iterdir() if d.is_dir()]) == 3


class TestExtractors:
    def test_extract_metric_value(self):
        sc = _make_scorecard(lex_avg=0.72)
        assert _extract_metric_value(sc, "lexical_diversity") == 0.72
        assert _extract_metric_value(sc, "nonexistent") is None

    def test_extract_metric_pass(self):
        sc = _make_scorecard(verb_pass=False)
        assert _extract_metric_pass(sc, "verb_specificity_index") is False
        assert _extract_metric_pass(sc, "nonexistent") is None

    def test_extract_from_non_dict(self):
        sc = {"lexical_diversity": "not_a_dict"}
        assert _extract_metric_value(sc, "lexical_diversity") is None
        assert _extract_metric_pass(sc, "lexical_diversity") is None


class TestPointers:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_write_and_read(self):
        _write_pointer(self.tmpdir, "latest.json", "run-abc")
        assert _read_pointer(self.tmpdir, "latest.json") == "run-abc"

    def test_read_missing(self):
        assert _read_pointer(self.tmpdir, "nonexistent.json") is None

    def test_read_corrupted(self):
        (self.tmpdir / "bad.json").write_text("not json{{{", encoding="utf-8")
        assert _read_pointer(self.tmpdir, "bad.json") is None


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
