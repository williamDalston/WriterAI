"""
Micro-Prose Test -- runs the Glass Registry through all 8 planning stages,
then drafts 3 targeted scenes to evaluate prose quality.

Scenes selected to stress different pipeline muscles:
  1. Early hook scene  (Ch2, S1)  -- fresh context, must hook reader
  2. Mid-book pressure (Ch8, S2)  -- deep context, qwen recycling risk
  3. Late turning point (Ch12, S2) -- climax zone, highest emotional stakes

Usage:
    python -m tests.test_micro_prose
"""

import sys
import asyncio
import logging
import pytest
import json
import time
import re
import copy
from pathlib import Path

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
logger = logging.getLogger("micro_prose")

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

# Scenes to draft: (chapter, scene) tuples
# Also tracked by scene_id for stable targeting (ch02_s01 etc.)
TARGET_SCENES = [
    (2, 1),   # Early hook     -> scene_id: ch02_s01
    (8, 2),   # Mid-book pressure -> scene_id: ch08_s02
    (12, 2),  # Late turning point -> scene_id: ch12_s02
]
TARGET_SCENE_IDS = {"ch02_s01", "ch08_s02", "ch12_s02"}


def count_words(text):
    """Count words in text, stripping markdown."""
    text = re.sub(r'^#+\s+.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'[\*_\[\]`#]', '', text)
    return len(text.split())


def check_scene_quality(content, scene_label):
    """Run quality checks on a drafted scene. Returns dict of metrics."""
    if not content or not content.strip():
        return {"error": "Empty scene", "word_count": 0}

    words = content.split()
    word_count = count_words(content)
    sentences = [s.strip() for s in re.split(r'[.!?]+', content) if s.strip()]
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

    metrics = {
        "word_count": word_count,
        "paragraph_count": len(paragraphs),
        "sentence_count": len(sentences),
    }

    # 1. Preamble check
    preamble_patterns = [
        r"^(certainly|sure|here is|below is|as requested|i'd be happy)",
        r"^(chapter \d+|scene \d+:)",
    ]
    first_line = content.strip().split('\n')[0].lower()
    for pat in preamble_patterns:
        if re.search(pat, first_line):
            metrics["preamble_detected"] = first_line[:80]
            break

    # 2. POV check (should be first person)
    first_person_count = len(re.findall(r'\bI\b', content))
    third_person_count = len(re.findall(r'\b(he|she) (said|thought|felt|looked|turned|walked)\b', content, re.I))
    metrics["first_person_refs"] = first_person_count
    metrics["third_person_refs"] = third_person_count
    if first_person_count < 5:
        metrics["pov_issue"] = "Low first-person count"

    # 3. Dialogue presence
    dialogue_lines = len(re.findall(r'"[^"]{5,}"', content))
    metrics["dialogue_lines"] = dialogue_lines
    if dialogue_lines == 0:
        metrics["dialogue_issue"] = "No dialogue found"

    # 4. Sensory detail check
    tactile_words = re.findall(r'\b(rough|smooth|cold|warm|wet|dry|sharp|soft|hard|grit|friction|press|texture|skin|touch|grip|fingers|palm)\b', content, re.I)
    sound_words = re.findall(r'\b(sound|noise|whisper|murmur|echo|hum|creak|click|slam|ring|silence|buzz|roar|hiss|scrape|footstep|voice)\b', content, re.I)
    metrics["tactile_words"] = len(tactile_words)
    metrics["sound_words"] = len(sound_words)
    if len(tactile_words) == 0:
        metrics["sensory_issue_tactile"] = "No tactile detail found"
    if len(sound_words) == 0:
        metrics["sensory_issue_sound"] = "No sound detail found"

    # 5. Scene turn check (does the final paragraph contain a shift?)
    if paragraphs:
        last_para = paragraphs[-1].lower()
        turn_signals = ["but", "then", "until", "except", "suddenly", "instead",
                        "realize", "understand", "knew", "changed", "shifted",
                        "door", "phone", "voice", "said", "asked", "told"]
        has_turn = any(sig in last_para for sig in turn_signals)
        metrics["scene_turn_detected"] = has_turn
        if not has_turn:
            metrics["turn_issue"] = "No clear scene turn in final paragraph"

    # 6. AI tell-phrases
    ai_tells = [
        "couldn't help but", "found myself", "a sense of", "I realized",
        "electricity", "butterflies in", "walls crumbling",
        "breath I didn't know", "heart skipped", "everything changed",
        "nothing would ever be the same",
    ]
    found_tells = [t for t in ai_tells if t.lower() in content.lower()]
    metrics["ai_tells_found"] = found_tells
    metrics["ai_tell_count"] = len(found_tells)

    # 7. Subtext check (dialogue followed by contradicting action/thought)
    # Simple heuristic: look for "said" followed by internal thought within 200 chars
    subtext_candidates = len(re.findall(r'"[^"]+"\s*(?:I|she|he)\s+said.*?(?:but|though|even as|despite)', content, re.I | re.DOTALL))
    metrics["subtext_signals"] = subtext_candidates

    # 8. Sentence length variance
    if sentences:
        lengths = [len(s.split()) for s in sentences if s.split()]
        if lengths:
            avg_len = sum(lengths) / len(lengths)
            variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
            metrics["avg_sentence_length"] = round(avg_len, 1)
            metrics["sentence_length_variance"] = round(variance ** 0.5, 1)

    return metrics


async def run_micro_prose(project_path: Path = None, model: str = "qwen2.5:14b"):
    """Run micro-prose test. project_path defaults to the-glass-registry."""
    if project_path is None:
        project_path = ROOT / "data" / "projects" / "the-glass-registry"
    if not (project_path / "config.yaml").exists():
        logger.error(f"Project not found at {project_path}")
        return

    ollama = OllamaClient(model)
    pipeline = PipelineOrchestrator(
        project_path=project_path,
        llm_client=ollama,
        llm_clients={"gpt": ollama, "claude": ollama, "gemini": ollama},
    )

    await pipeline.initialize()

    print("\n" + "=" * 70)
    print("MICRO-PROSE TEST -- The Glass Registry")
    print("Model: qwen2.5:14b (Q4_K_M, 32k context)")
    print(f"Target scenes: {TARGET_SCENES}")
    print("=" * 70)

    # --- Phase 1: Run planning stages ---
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

            print(f"  {stage:30s} OK  {elapsed:6.1f}s  {tokens:5d} tok")

        except Exception as e:
            elapsed = time.time() - t0
            planning_time += elapsed
            print(f"  {stage:30s} FAILED  {elapsed:6.1f}s  {e}")
            if stage in ("high_concept", "master_outline"):
                print("  CRITICAL: Cannot continue without this stage.")
                return

    print(f"\n  Planning total: {planning_time:.1f}s, {planning_tokens} tokens")

    # Verify we have an outline
    if not pipeline.state.master_outline:
        print("  ERROR: No master outline generated. Cannot draft scenes.")
        return

    total_chapters = len(pipeline.state.master_outline)
    total_scenes = sum(
        len(ch.get("scenes", []))
        for ch in pipeline.state.master_outline
        if isinstance(ch, dict)
    )
    print(f"  Outline: {total_chapters} chapters, {total_scenes} scenes")

    # --- Phase 2: Draft 3 target scenes ---
    print("\n--- PHASE 2: Prose Drafting (3 target scenes) ---")

    # Save full outline, then filter to only target chapters
    full_outline = copy.deepcopy(pipeline.state.master_outline)

    # Build a filtered outline with only the target scenes' chapters.
    # Primary: match by scene_id (stable). Fallback: match by (chapter, scene_number).
    target_chapter_nums = sorted(set(ch for ch, _ in TARGET_SCENES))
    filtered_outline = []
    for ch in full_outline:
        if not isinstance(ch, dict):
            continue
        ch_num = ch.get("chapter", 0)
        if ch_num in target_chapter_nums:
            target_scene_nums = [s for c, s in TARGET_SCENES if c == ch_num]
            filtered_scenes = []
            for sc in ch.get("scenes", []):
                if not isinstance(sc, dict):
                    continue
                # Primary: scene_id match
                if sc.get("scene_id") in TARGET_SCENE_IDS:
                    filtered_scenes.append(sc)
                # Fallback: number match
                elif sc.get("scene", sc.get("scene_number", 0)) in target_scene_nums:
                    filtered_scenes.append(sc)
            ch_copy = dict(ch)
            ch_copy["scenes"] = filtered_scenes
            filtered_outline.append(ch_copy)

    print(f"  Filtered outline: {len(filtered_outline)} chapters, "
          f"{sum(len(c.get('scenes', [])) for c in filtered_outline)} scenes")

    # Show which scenes we're drafting
    for ch in filtered_outline:
        ch_num = ch.get("chapter", "?")
        for sc in ch.get("scenes", []):
            sc_num = sc.get("scene", sc.get("scene_number", "?"))
            sc_name = sc.get("scene_name", "?")
            purpose = sc.get("purpose", "?")[:80]
            print(f"  --> Ch{ch_num}-S{sc_num}: \"{sc_name}\" -- {purpose}")

    # Replace outline with filtered version for drafting
    pipeline.state.master_outline = filtered_outline

    # Run scene_drafting
    prose_t0 = time.time()
    try:
        result = await pipeline._stage_scene_drafting()
        prose_elapsed = time.time() - prose_t0

        if isinstance(result, tuple) and len(result) == 2:
            scenes_out, prose_tokens = result
        else:
            scenes_out, prose_tokens = result, 0

    except Exception as e:
        prose_elapsed = time.time() - prose_t0
        print(f"\n  PROSE DRAFTING FAILED ({prose_elapsed:.1f}s): {e}")
        import traceback
        traceback.print_exc()
        # Restore outline
        pipeline.state.master_outline = full_outline
        return

    # Restore full outline
    pipeline.state.master_outline = full_outline

    print(f"\n  Prose drafting: {prose_elapsed:.1f}s, {prose_tokens} tokens, {len(pipeline.state.scenes)} scenes")

    # --- Phase 2.5: Deterministic Quality Meters ---
    print("\n" + "=" * 70)
    print("DETERMINISTIC QUALITY METERS")
    print("=" * 70)

    meter_report = run_all_meters(
        scenes=pipeline.state.scenes,
        outline=full_outline,
        characters=pipeline.state.characters or [],
    )
    print_meter_report(meter_report)

    # --- Phase 3: Quality Analysis ---
    print("\n" + "=" * 70)
    print("QUALITY ANALYSIS")
    print("=" * 70)

    all_issues = []
    all_metrics = []

    for i, scene in enumerate(pipeline.state.scenes):
        ch = scene.get("chapter", "?")
        sc = scene.get("scene_number", "?")
        content = scene.get("content", "")
        label = f"Ch{ch}-S{sc}"

        print(f"\n--- Scene {i+1}: {label} ---")

        metrics = check_scene_quality(content, label)
        all_metrics.append(metrics)

        # Basic stats
        wc = metrics["word_count"]
        paras = metrics["paragraph_count"]
        sents = metrics["sentence_count"]
        print(f"  Words: {wc}  |  Paragraphs: {paras}  |  Sentences: {sents}")

        # Word count target check
        target = pipeline.state.words_per_scene
        pct = (wc / target * 100) if target else 0
        status = "OK" if pct >= 80 else "SHORT" if pct >= 50 else "VERY SHORT"
        print(f"  Target: {target} words -> {pct:.0f}% ({status})")

        # POV
        fp = metrics.get("first_person_refs", 0)
        tp = metrics.get("third_person_refs", 0)
        pov_ok = fp > 5 and "pov_issue" not in metrics
        print(f"  POV: {'OK' if pov_ok else 'ISSUE'} (I={fp}, she/he-verb={tp})")

        # Dialogue
        dl = metrics.get("dialogue_lines", 0)
        print(f"  Dialogue: {dl} lines {'(OK)' if dl >= 2 else '(LOW)'}")

        # Sensory
        tac = metrics.get("tactile_words", 0)
        snd = metrics.get("sound_words", 0)
        print(f"  Sensory: tactile={tac}, sound={snd} "
              f"{'(OK)' if tac > 0 and snd > 0 else '(MISSING)' if tac == 0 and snd == 0 else '(PARTIAL)'}")

        # Scene turn
        has_turn = metrics.get("scene_turn_detected", False)
        print(f"  Scene turn: {'DETECTED' if has_turn else 'MISSING'}")

        # AI tells
        tells = metrics.get("ai_tells_found", [])
        if tells:
            print(f"  AI tells: {tells}")
        else:
            print(f"  AI tells: None (clean)")

        # Sentence rhythm
        avg_sl = metrics.get("avg_sentence_length", 0)
        sl_var = metrics.get("sentence_length_variance", 0)
        rhythm_ok = sl_var >= 3.0  # Want variety
        print(f"  Rhythm: avg {avg_sl} words/sentence, variance {sl_var} {'(varied)' if rhythm_ok else '(monotonous)'}")

        # Subtext
        sub = metrics.get("subtext_signals", 0)
        print(f"  Subtext signals: {sub}")

        # Preamble
        if "preamble_detected" in metrics:
            print(f"  PREAMBLE: {metrics['preamble_detected']}")
            all_issues.append(f"{label}: preamble detected")

        # Collect issues
        for key in ("pov_issue", "dialogue_issue", "sensory_issue_tactile",
                     "sensory_issue_sound", "turn_issue"):
            if key in metrics:
                all_issues.append(f"{label}: {metrics[key]}")

        if tells:
            all_issues.append(f"{label}: {len(tells)} AI tell-phrases")

        # Preview
        preview = content[:300].replace('\n', ' ') if content else "(empty)"
        print(f"\n  OPENING:\n    {preview}...")

        # Last paragraph
        if content:
            last_para = content.strip().split('\n\n')[-1] if '\n\n' in content else content[-300:]
            last_preview = last_para[:300].replace('\n', ' ')
            print(f"\n  CLOSING:\n    {last_preview}...")

    # --- Summary ---
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")

    print(f"\n  Scenes drafted: {len(pipeline.state.scenes)}")
    print(f"  Planning time:  {planning_time:.1f}s ({planning_tokens} tokens)")
    print(f"  Prose time:     {prose_elapsed:.1f}s ({prose_tokens} tokens)")
    print(f"  Total time:     {planning_time + prose_elapsed:.1f}s")
    print(f"  Total tokens:   {planning_tokens + prose_tokens}")

    # Aggregate metrics
    if all_metrics:
        avg_wc = sum(m.get("word_count", 0) for m in all_metrics) / len(all_metrics)
        avg_dl = sum(m.get("dialogue_lines", 0) for m in all_metrics) / len(all_metrics)
        total_tells = sum(m.get("ai_tell_count", 0) for m in all_metrics)
        scenes_with_turn = sum(1 for m in all_metrics if m.get("scene_turn_detected"))
        scenes_with_preamble = sum(1 for m in all_metrics if "preamble_detected" in m)

        print(f"\n  Avg word count:     {avg_wc:.0f}")
        print(f"  Avg dialogue lines: {avg_dl:.1f}")
        print(f"  Total AI tells:     {total_tells}")
        print(f"  Scenes with turn:   {scenes_with_turn}/{len(all_metrics)}")
        print(f"  Preambles:          {scenes_with_preamble}/{len(all_metrics)}")

    if all_issues:
        print(f"\n  Issues ({len(all_issues)}):")
        for issue in all_issues:
            print(f"    - {issue}")
    else:
        print(f"\n  Issues: None")

    # Meter summary
    meters_pass = meter_report.get("all_pass", True)
    rep_pass = meter_report.get("repetition", {}).get("pass", True)
    dedup_pass = meter_report.get("scene_dedup", {}).get("pass", True)
    voice_pass = meter_report.get("voice", {}).get("pass", True)

    print(f"\n  Meters: rep={'PASS' if rep_pass else 'FAIL'}, "
          f"dedup={'PASS' if dedup_pass else 'FAIL'}, "
          f"voice={'PASS' if voice_pass else 'FAIL'}")

    # Pass/fail
    critical_issues = [i for i in all_issues if "preamble" in i or "pov" in i.lower()]
    if critical_issues:
        print(f"\n  VERDICT: NEEDS WORK ({len(critical_issues)} critical issues)")
    elif not meters_pass:
        print(f"\n  VERDICT: NEEDS WORK (meter failures)")
    elif len(all_issues) > 3:
        print(f"\n  VERDICT: ACCEPTABLE (minor issues)")
    else:
        print(f"\n  VERDICT: PASS")

    print(f"\n{'=' * 70}")

    return {
        "total_scenes": len(all_metrics),
        "preambles": sum(1 for i in all_issues if "preamble" in i),
        "meters_pass": meters_pass,
        "critical_issues": len(critical_issues),
    }


@pytest.mark.smoke
@pytest.mark.slow
def test_micro_prose(smoke_project):
    """Pytest wrapper for micro-prose. Uses temp project from fixtures."""
    result = asyncio.run(run_micro_prose(project_path=smoke_project, model="qwen2.5:7b"))
    assert result["total_scenes"] > 0, "No scenes were drafted"
    assert result["preambles"] == 0, f"Preambles detected"
    assert result["critical_issues"] == 0, f"Critical issues found: {result['critical_issues']}"


if __name__ == "__main__":
    asyncio.run(run_micro_prose())
