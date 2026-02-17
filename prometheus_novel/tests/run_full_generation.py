"""Full 12-chapter generation runner for Burning Vows.

Runs all planning stages + ALL chapters (no filtering), then collects:
1. chapters + scenes generated
2. meter summary (all 6 meters)
3. dialogue drought triggered/accepted
4. turn rate %
5. top 5 hot phrases
6. total tokens + micro-pass tokens %

Usage:
    python -u -m tests.run_full_generation
"""

import sys
import asyncio
import logging
import json
import time
import re
import collections
from pathlib import Path

# Fix Windows cp1252 encoding issues
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from prometheus_lib.llm.clients import OllamaClient
from stages.pipeline import PipelineOrchestrator
from stages.quality_meters import run_all_meters, print_meter_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("full_gen")

PLANNING_STAGES = [
    "high_concept",
    "world_building",
    "beat_sheet",
    "emotional_architecture",
    "character_profiles",
    "motif_embedding",
    "master_outline",
    "trope_integration",
]

MODEL = "qwen2.5:14b"


def count_words(text):
    text = re.sub(r'^#+\s+.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'[\*_\[\]`#]', '', text)
    return len(text.split())


def extract_hot_phrases(scenes, top_n=5):
    """Find most repeated 3-6 word phrases across scenes."""
    phrase_counts = collections.Counter()
    skip = {"i was", "it was", "he was", "she was", "i had", "the way",
            "in the", "of the", "at the", "on the", "to the", "and the",
            "i could", "i didn", "but i", "that i", "for the", "with the"}

    for s in scenes:
        content = s.get("content", "").lower()
        words = content.split()
        scene_phrases = set()
        for n in range(3, 7):
            for i in range(len(words) - n + 1):
                phrase = " ".join(words[i:i+n])
                if any(sk in phrase for sk in skip):
                    continue
                scene_phrases.add(phrase)
        for p in scene_phrases:
            phrase_counts[p] += 1

    return phrase_counts.most_common(top_n)


async def run_full_generation():
    project_path = ROOT / "data" / "projects" / "burning-vows"
    if not (project_path / "config.yaml").exists():
        logger.error(f"Project not found at {project_path}")
        return

    ollama = OllamaClient(MODEL)
    pipeline = PipelineOrchestrator(
        project_path=project_path,
        llm_client=ollama,
        llm_clients={"gpt": ollama, "claude": ollama, "gemini": ollama},
    )

    await pipeline.initialize()

    print("\n" + "=" * 70)
    print("FULL 12-CHAPTER GENERATION -- Burning Vows")
    print(f"Model: {MODEL} (Q4_K_M, 32k context)")
    print("=" * 70)

    # --- Phase 1: Planning ---
    print("\n--- PHASE 1: Planning (8 stages) ---")
    planning_time = 0
    planning_tokens = 0

    for stage in PLANNING_STAGES:
        t0 = time.time()
        try:
            handler = getattr(pipeline, f"_stage_{stage}")
            result = await handler()
            elapsed = time.time() - t0
            planning_time += elapsed
            if isinstance(result, tuple) and len(result) == 2:
                _, tokens = result
            else:
                tokens = 0
            planning_tokens += tokens
            print(f"  {stage:30s} OK  {elapsed:6.1f}s  {tokens:5d} tok", flush=True)
        except Exception as e:
            elapsed = time.time() - t0
            planning_time += elapsed
            print(f"  {stage:30s} FAILED  {elapsed:6.1f}s  {e}", flush=True)
            if stage in ("high_concept", "master_outline"):
                print("  CRITICAL: Cannot continue without this stage.")
                return

    print(f"\n  Planning total: {planning_time:.1f}s, {planning_tokens} tokens", flush=True)

    if not pipeline.state.master_outline:
        print("  ERROR: No master outline. Cannot draft.")
        return

    total_chapters = len(pipeline.state.master_outline)
    total_scenes = sum(
        len(ch.get("scenes", []))
        for ch in pipeline.state.master_outline if isinstance(ch, dict)
    )
    print(f"  Outline: {total_chapters} chapters, {total_scenes} scenes", flush=True)

    # --- Phase 2: Draft ALL chapters ---
    print(f"\n--- PHASE 2: Prose Drafting (ALL {total_chapters} chapters) ---", flush=True)

    prose_t0 = time.time()
    try:
        result = await pipeline._stage_scene_drafting()
        prose_elapsed = time.time() - prose_t0
        if isinstance(result, tuple) and len(result) == 2:
            _, prose_tokens = result
        else:
            prose_tokens = 0
    except Exception as e:
        prose_elapsed = time.time() - prose_t0
        print(f"\n  PROSE DRAFTING FAILED ({prose_elapsed:.1f}s): {e}", flush=True)
        import traceback
        traceback.print_exc()
        # Still try to analyze whatever we got
        prose_tokens = 0

    drafted_scenes = pipeline.state.scenes
    print(f"\n  Drafted: {len(drafted_scenes)} scenes in {prose_elapsed:.1f}s, {prose_tokens} tokens", flush=True)

    # --- Phase 3: Quality Meters ---
    print("\n" + "=" * 70)
    print("DETERMINISTIC QUALITY METERS")
    print("=" * 70)

    meter_report = run_all_meters(
        scenes=drafted_scenes,
        outline=pipeline.state.master_outline,
        characters=pipeline.state.characters or [],
    )
    print_meter_report(meter_report)

    # --- Phase 4: Per-Scene Analysis ---
    print("\n" + "=" * 70)
    print("PER-SCENE ANALYSIS")
    print("=" * 70)

    all_metrics = []
    all_issues = []
    turn_signals = [
        "but", "then", "until", "except", "instead",
        "realize", "understand", "knew", "changed", "shifted",
        "door", "phone", "voice", "said", "asked", "told",
        "decided", "chose", "turned", "stopped", "froze",
        "no", "wait", "wrong", "different", "?",
        "prove", "show me", "try me", "let's see", "make me",
        "dare", "confront", "face me", "choose", "swear",
    ]

    for scene in drafted_scenes:
        sid = scene.get("scene_id", f"Ch{scene.get('chapter', '?')}-S{scene.get('scene_number', '?')}")
        content = scene.get("content", "")
        wc = count_words(content)
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        dialogue_lines = len(re.findall(r'["\u201c][^\u201d"]{5,}["\u201d]', content))

        # Scene turn check
        if len(paragraphs) >= 2:
            last_two = '\n\n'.join(paragraphs[-2:]).lower()
            has_turn = sum(1 for sig in turn_signals if sig in last_two) >= 2
        else:
            has_turn = False

        # Preamble check
        first_line = content[:200].lower() if content else ""
        preamble = any(p in first_line for p in [
            "here is", "here's", "sure,", "certainly", "i'll write",
            "## scene", "**scene", "scene:", "chapter:"
        ])

        # AI tells
        ai_tell_patterns = [
            "i couldn't help but", "i found myself", "something about",
            "a sense of", "i realized", "i noticed",
        ]
        tells = [p for p in ai_tell_patterns if p in content.lower()]

        metrics = {
            "label": sid,
            "word_count": wc,
            "paragraphs": len(paragraphs),
            "dialogue_lines": dialogue_lines,
            "scene_turn": has_turn,
            "preamble": preamble,
            "ai_tells": tells,
        }
        all_metrics.append(metrics)

        target = pipeline.state.words_per_scene if hasattr(pipeline.state, 'words_per_scene') else 1000
        pct = (wc / target * 100) if target else 0

        print(f"\n  {sid}: {wc} words ({pct:.0f}%), "
              f"{len(paragraphs)} paras, "
              f"{dialogue_lines} dialogue, "
              f"turn={'Y' if has_turn else 'N'}", flush=True)

        if preamble:
            print(f"    ISSUE: preamble detected")
            all_issues.append(f"{sid}: preamble")
        if tells:
            print(f"    ISSUE: AI tells: {tells}")
            all_issues.append(f"{sid}: {len(tells)} AI tells")
        if not has_turn:
            print(f"    ISSUE: no scene turn detected")
            all_issues.append(f"{sid}: no scene turn")
        if dialogue_lines == 0:
            print(f"    ISSUE: no dialogue")
            all_issues.append(f"{sid}: no dialogue")
        if pct < 50:
            print(f"    ISSUE: very short ({pct:.0f}% of target)")
            all_issues.append(f"{sid}: very short")

        # Opening + closing preview
        if content:
            opening = content[:150].replace('\n', ' ')
            closing_paras = content.strip().split('\n\n')
            closing = closing_paras[-1][:150].replace('\n', ' ') if closing_paras else ""
            print(f"    OPEN:  {opening}...")
            print(f"    CLOSE: {closing}...")

    # --- Phase 5: Summary (the 6-line report) ---
    print(f"\n{'=' * 70}")
    print("6-LINE SUMMARY")
    print(f"{'=' * 70}")

    # 1. chapters + scenes
    chapter_nums = sorted(set(s.get("chapter", 0) for s in drafted_scenes))
    print(f"\n  1) Chapters: {len(chapter_nums)}/{total_chapters}, Scenes: {len(drafted_scenes)}/{total_scenes}")

    # 2. meter summary
    meters_pass = meter_report.get("all_pass", True)
    meter_names = []
    for key, val in meter_report.items():
        if isinstance(val, dict) and "pass" in val:
            status = "PASS" if val["pass"] else "FAIL"
            meter_names.append(f"{key}={status}")
    print(f"  2) Meters: {'ALL PASS' if meters_pass else 'FAILURES'} — {', '.join(meter_names)}")

    # 3. dialogue drought
    am = getattr(pipeline.state, 'artifact_metrics', {})
    drought_triggered = sum(1 for m in all_metrics if m["dialogue_lines"] < 3)
    drought_accepted = 0  # Infer from scenes that have >= 3 dialogue lines after micro-passes
    for m in all_metrics:
        if m["dialogue_lines"] >= 3:
            drought_accepted += 1
    # Check micro-pass logs from artifact_metrics
    micro_stats = am.get("micro_pass_stats", {})
    if micro_stats:
        dd_triggered = micro_stats.get("dialogue_drought_triggered", "?")
        dd_accepted = micro_stats.get("dialogue_drought_accepted", "?")
        print(f"  3) Dialogue drought: {dd_triggered} triggered, {dd_accepted} accepted")
    else:
        scenes_with_dialogue = sum(1 for m in all_metrics if m["dialogue_lines"] >= 3)
        print(f"  3) Dialogue: {scenes_with_dialogue}/{len(all_metrics)} scenes have 3+ dialogue lines")

    # 4. turn rate
    turns = sum(1 for m in all_metrics if m["scene_turn"])
    turn_rate = (turns / len(all_metrics) * 100) if all_metrics else 0
    print(f"  4) Turn rate: {turns}/{len(all_metrics)} ({turn_rate:.0f}%)")

    # 5. top 5 hot phrases
    hot = extract_hot_phrases(drafted_scenes, 5)
    print(f"  5) Hot phrases: {[f'{p} ({c}x)' for p, c in hot]}")

    # 6. total tokens + micro-pass %
    total_tokens = planning_tokens + prose_tokens
    micro_tokens = sum(
        v.get("tokens", 0) for v in micro_stats.values()
        if isinstance(v, dict) and "tokens" in v
    ) if micro_stats else 0
    micro_pct = (micro_tokens / total_tokens * 100) if total_tokens > 0 else 0
    print(f"  6) Total tokens: {total_tokens}, micro-pass: {micro_tokens} ({micro_pct:.1f}%)")

    # Verdict
    critical = [i for i in all_issues if "preamble" in i or "very short" in i]
    preambles = sum(1 for m in all_metrics if m.get("preamble"))
    if critical:
        verdict = f"NEEDS WORK ({len(critical)} critical)"
    elif not meters_pass:
        verdict = "NEEDS WORK (meter failures)"
    elif len(all_issues) > len(drafted_scenes):
        verdict = "ACCEPTABLE (issues exceed scene count)"
    else:
        verdict = "PASS"

    print(f"\n  VERDICT: {verdict}")
    print(f"\n  Time: planning {planning_time:.1f}s + prose {prose_elapsed:.1f}s = {planning_time + prose_elapsed:.1f}s")
    print(f"\n{'=' * 70}")

    return {
        "verdict": verdict,
        "total_chapters": len(chapter_nums),
        "total_scenes": len(drafted_scenes),
        "preambles": preambles,
        "avg_word_count": sum(m["word_count"] for m in all_metrics) / len(all_metrics) if all_metrics else 0,
        "meters_pass": meters_pass,
        "turn_rate": turn_rate,
        "total_tokens": total_tokens,
    }


if __name__ == "__main__":
    asyncio.run(run_full_generation())
