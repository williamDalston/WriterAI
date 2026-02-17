"""Idempotence test: running quality polish twice should produce ~0 changes on the second pass.

This proves the quality system converges and doesn't create replacement loops.
"""
import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from pathlib import Path
from collections import Counter

from quality.phrase_miner import mine_hot_phrases, write_auto_yaml, load_phrase_config, load_miner_config
from quality.phrase_suppressor import suppress_phrases
from quality.dialogue_trimmer import process_scenes as trim_dialogue_scenes
from quality.emotion_diversifier import process_scenes as diversify_emotion_scenes
from quality.cliche_clusters import repair_clusters, detect_clusters


def run_quality_polish(texts, configs_dir):
    """Run the full quality polish pass on a list of scene texts. Returns (modified_texts, report)."""
    report = {}

    # 1. Phrase mining
    miner_cfg = load_miner_config(configs_dir / "phrase_miner.yaml")
    mine_result = mine_hot_phrases(
        texts,
        ignore_phrases=miner_cfg.get("ignore_phrases", []),
        ignore_regex=miner_cfg.get("ignore_regex", []),
    )
    auto_yaml_path = configs_dir / "hot_phrases.auto.yaml"
    write_auto_yaml(mine_result, auto_yaml_path)
    report["phrases_flagged"] = mine_result["stats"]["phrases_flagged"]

    # 2. Phrase suppression
    phrase_configs = load_phrase_config(auto_path=auto_yaml_path)
    if phrase_configs:
        texts, suppress_report = suppress_phrases(texts, phrase_configs)
        report["phrase_replacements"] = suppress_report["total_replacements"]
    else:
        report["phrase_replacements"] = 0

    # 3. Dialogue trimming
    texts, dialogue_report = trim_dialogue_scenes(texts)
    report["dialogue_trims"] = dialogue_report["tags_trimmed"]

    # 4. Emotion diversification
    texts, emotion_report = diversify_emotion_scenes(texts)
    report["emotion_replacements"] = emotion_report["total_replaced"]

    # 5. Cliche cluster repair
    texts, cluster_report = repair_clusters(texts, only_flagged=True)
    report["cliche_replacements"] = cluster_report["total_replaced"]

    # 6. Detect remaining
    detect_report = detect_clusters(texts)
    report["cliche_flagged_after"] = detect_report["flagged_count"]

    report["total_changes"] = (
        report["phrase_replacements"]
        + report["dialogue_trims"]
        + report["emotion_replacements"]
        + report["cliche_replacements"]
    )

    return texts, report


def main():
    # Load Burning Vows scenes
    state_path = Path(__file__).parent.parent / "data" / "projects" / "burning-vows" / "pipeline_state.json"
    if not state_path.exists():
        print("SKIP: Burning Vows pipeline_state.json not found")
        return

    with open(state_path, "r", encoding="utf-8") as f:
        state = json.load(f)

    scenes = [s for s in state.get("scenes", []) if isinstance(s, dict) and s.get("content")]
    texts = [s["content"] for s in scenes]
    configs_dir = Path(__file__).parent.parent / "configs"

    print(f"Loaded {len(texts)} scenes from Burning Vows")
    print()

    # --- Pass 1 ---
    print("=== PASS 1 ===")
    texts_after_1, report_1 = run_quality_polish(texts, configs_dir)
    print(f"  Phrase replacements:   {report_1['phrase_replacements']}")
    print(f"  Dialogue trims:        {report_1['dialogue_trims']}")
    print(f"  Emotion replacements:  {report_1['emotion_replacements']}")
    print(f"  Cliche replacements:   {report_1['cliche_replacements']}")
    print(f"  TOTAL changes:         {report_1['total_changes']}")
    print(f"  Cliche clusters still flagged: {report_1['cliche_flagged_after']}")
    print()

    # --- Pass 2 ---
    print("=== PASS 2 (should be ~0 changes) ===")
    texts_after_2, report_2 = run_quality_polish(texts_after_1, configs_dir)
    print(f"  Phrase replacements:   {report_2['phrase_replacements']}")
    print(f"  Dialogue trims:        {report_2['dialogue_trims']}")
    print(f"  Emotion replacements:  {report_2['emotion_replacements']}")
    print(f"  Cliche replacements:   {report_2['cliche_replacements']}")
    print(f"  TOTAL changes:         {report_2['total_changes']}")
    print()

    # --- Verdict ---
    pass2_changes = report_2["total_changes"]
    pass1_changes = report_1["total_changes"]

    if pass2_changes == 0:
        print("IDEMPOTENCE: PERFECT - 0 changes on second pass")
    elif pass2_changes <= 3:
        print(f"IDEMPOTENCE: NEAR-PERFECT - {pass2_changes} residual changes (acceptable)")
    else:
        pct = pass2_changes / max(pass1_changes, 1) * 100
        print(f"IDEMPOTENCE: WARNING - {pass2_changes} changes on pass 2 ({pct:.1f}% of pass 1)")
        if pass2_changes > pass1_changes * 0.1:
            print("FAIL: second pass made >10% as many changes as first — possible replacement loop")
            sys.exit(1)

    # Count exact text differences
    diffs = sum(1 for a, b in zip(texts_after_1, texts_after_2) if a != b)
    print(f"\nScenes with any text difference between pass 1 and pass 2: {diffs}/{len(texts)}")


if __name__ == "__main__":
    main()
