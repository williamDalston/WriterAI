"""
Act Tripod Test (Confidence Ladder - Test C)

Generates 3 full chapters (one per act) and evaluates:
  - Gate A pass rate (with/without repair)
  - Dialogue line count & density
  - Repetition meter across scenes
  - Scene body similarity (same-beats detection)
  - Voice distinctiveness + sub-metrics
  - Continuity: names, goals, relationships consistent across acts
  - Escalation: Act 2 harder than Act 1, Act 3 has irreversible cost

Chapters selected:
  - Ch2  (Act 1: inciting incident + lock-in)
  - Ch6  (Act 2: escalation + reversal)
  - Ch11 (Act 3: climax setup + consequence)

Usage:
    python -m tests.test_act_tripod
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

# Fix Windows cp1252 encoding issues with Unicode scene content
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
logger = logging.getLogger("act_tripod")

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

# One chapter per act
TARGET_CHAPTERS = [2, 6, 11]


def count_words(text):
    text = re.sub(r'^#+\s+.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'[\*_\[\]`#]', '', text)
    return len(text.split())


def analyze_scene(content, label):
    """Quick scene quality check returning metrics dict."""
    if not content or not content.strip():
        return {"label": label, "word_count": 0, "error": "empty"}

    word_count = count_words(content)
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    sentences = [s.strip() for s in re.split(r'[.!?]+', content) if s.strip()]
    dialogue_lines = len(re.findall(r'"[^"]{5,}"', content))

    # POV
    first_person = len(re.findall(r'\bI\b', content))
    third_person = len(re.findall(r'\b(he|she) (said|thought|felt|looked|turned|walked)\b', content, re.I))

    # AI tells
    ai_tells = [
        "couldn't help but", "found myself", "a sense of", "electricity",
        "butterflies in", "walls crumbling", "breath I didn't know",
        "heart skipped", "everything changed", "nothing would ever be the same",
    ]
    found_tells = [t for t in ai_tells if t.lower() in content.lower()]

    # Scene turn
    has_turn = False
    if paragraphs:
        last_para = paragraphs[-1].lower()
        turn_signals = ["but", "then", "until", "except", "suddenly", "instead",
                        "realize", "understand", "knew", "changed", "shifted",
                        "door", "phone", "voice", "said", "asked", "told"]
        has_turn = any(sig in last_para for sig in turn_signals)

    # Preamble
    preamble = False
    first_line = content.strip().split('\n')[0].lower()
    preamble_pats = [
        r"^(certainly|sure|here is|below is|as requested|i'd be happy)",
        r"^(chapter \d+|scene \d+:)",
    ]
    for pat in preamble_pats:
        if re.search(pat, first_line):
            preamble = True
            break

    # Sentence rhythm
    avg_sl, sl_var = 0, 0
    if sentences:
        lengths = [len(s.split()) for s in sentences if s.split()]
        if lengths:
            avg_sl = sum(lengths) / len(lengths)
            sl_var = (sum((l - avg_sl) ** 2 for l in lengths) / len(lengths)) ** 0.5

    return {
        "label": label,
        "word_count": word_count,
        "paragraphs": len(paragraphs),
        "sentences": len(sentences),
        "dialogue_lines": dialogue_lines,
        "first_person_refs": first_person,
        "third_person_refs": third_person,
        "ai_tells": found_tells,
        "scene_turn": has_turn,
        "preamble": preamble,
        "avg_sentence_length": round(avg_sl, 1),
        "sentence_length_variance": round(sl_var, 1),
    }


def check_continuity(scenes):
    """Check name/entity consistency across all scenes."""
    # Extract character names mentioned per scene
    all_names_per_scene = []
    for scene in scenes:
        content = scene.get("content", "")
        # Find capitalized proper nouns (crude but effective)
        names = set(re.findall(r'\b[A-Z][a-z]{2,}\b', content))
        # Filter out sentence starters (approximate)
        names -= {"The", "She", "But", "And", "His", "Her", "Its", "Our", "This",
                   "That", "When", "Then", "Now", "Here", "There", "What", "How",
                   "Not", "Just", "Even", "Still", "Only", "Once", "After", "Before"}
        all_names_per_scene.append(names)

    if len(all_names_per_scene) < 2:
        return {"consistent": True, "note": "Too few scenes to check"}

    # Core names: appear in 50%+ of scenes
    from collections import Counter
    name_counts = Counter()
    for names in all_names_per_scene:
        name_counts.update(names)

    total = len(all_names_per_scene)
    core_names = {n for n, c in name_counts.items() if c >= total * 0.3}
    sporadic_names = {n for n, c in name_counts.items() if c == 1 and len(n) > 3}

    return {
        "core_names": sorted(core_names),
        "sporadic_names": sorted(sporadic_names)[:10],
        "total_unique_names": len(name_counts),
        "scenes_checked": total,
    }


async def run_act_tripod(project_path: Path = None, model: str = "qwen2.5:14b"):
    """Run act tripod test. project_path defaults to the-glass-registry."""
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
    print("ACT TRIPOD TEST -- The Glass Registry")
    print("Model: qwen2.5:14b (Q4_K_M, 32k context)")
    print(f"Target chapters: {TARGET_CHAPTERS} (Act 1 / Act 2 / Act 3)")
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
            print(f"  {stage:30s} OK  {elapsed:6.1f}s  {tokens:5d} tok")
        except Exception as e:
            elapsed = time.time() - t0
            planning_time += elapsed
            print(f"  {stage:30s} FAILED  {elapsed:6.1f}s  {e}")
            if stage in ("high_concept", "master_outline"):
                print("  CRITICAL: Cannot continue without this stage.")
                return

    print(f"\n  Planning total: {planning_time:.1f}s, {planning_tokens} tokens")

    if not pipeline.state.master_outline:
        print("  ERROR: No master outline. Cannot draft.")
        return

    total_chapters = len(pipeline.state.master_outline)
    total_scenes = sum(
        len(ch.get("scenes", []))
        for ch in pipeline.state.master_outline if isinstance(ch, dict)
    )
    print(f"  Outline: {total_chapters} chapters, {total_scenes} scenes")

    # --- Phase 2: Draft 3 target chapters (all scenes in each) ---
    print("\n--- PHASE 2: Prose Drafting (3 full chapters) ---")

    full_outline = copy.deepcopy(pipeline.state.master_outline)

    # Filter to target chapters (keep ALL scenes in each)
    filtered_outline = []
    for ch in full_outline:
        if not isinstance(ch, dict):
            continue
        ch_num = ch.get("chapter", 0)
        if ch_num in TARGET_CHAPTERS:
            filtered_outline.append(ch)

    filtered_scenes = sum(len(c.get("scenes", [])) for c in filtered_outline)
    print(f"  Filtered: {len(filtered_outline)} chapters, {filtered_scenes} scenes")

    for ch in filtered_outline:
        ch_num = ch.get("chapter", "?")
        scenes_in_ch = ch.get("scenes", [])
        print(f"  Ch{ch_num}: {len(scenes_in_ch)} scenes")
        for sc in scenes_in_ch:
            sid = sc.get("scene_id", "?")
            name = sc.get("scene_name", "?")
            print(f"    {sid}: {name}")

    pipeline.state.master_outline = filtered_outline

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
        print(f"\n  PROSE DRAFTING FAILED ({prose_elapsed:.1f}s): {e}")
        import traceback
        traceback.print_exc()
        pipeline.state.master_outline = full_outline
        return

    pipeline.state.master_outline = full_outline

    drafted_scenes = pipeline.state.scenes
    print(f"\n  Drafted: {len(drafted_scenes)} scenes in {prose_elapsed:.1f}s, {prose_tokens} tokens")

    # --- Phase 3: Quality Meters ---
    print("\n" + "=" * 70)
    print("DETERMINISTIC QUALITY METERS")
    print("=" * 70)

    meter_report = run_all_meters(
        scenes=drafted_scenes,
        outline=full_outline,
        characters=pipeline.state.characters or [],
    )
    print_meter_report(meter_report)

    # --- Phase 4: Per-Scene Analysis ---
    print("\n" + "=" * 70)
    print("PER-SCENE ANALYSIS")
    print("=" * 70)

    all_metrics = []
    all_issues = []

    for scene in drafted_scenes:
        sid = scene.get("scene_id", f"Ch{scene.get('chapter', '?')}-S{scene.get('scene_number', '?')}")
        content = scene.get("content", "")
        metrics = analyze_scene(content, sid)
        all_metrics.append(metrics)

        wc = metrics["word_count"]
        target = pipeline.state.words_per_scene
        pct = (wc / target * 100) if target else 0

        print(f"\n  {sid}: {wc} words ({pct:.0f}%), "
              f"{metrics['paragraphs']} paras, "
              f"{metrics['dialogue_lines']} dialogue, "
              f"I={metrics['first_person_refs']}")

        if metrics.get("preamble"):
            print(f"    ISSUE: preamble detected")
            all_issues.append(f"{sid}: preamble")
        if metrics.get("ai_tells"):
            print(f"    ISSUE: AI tells: {metrics['ai_tells']}")
            all_issues.append(f"{sid}: {len(metrics['ai_tells'])} AI tells")
        if not metrics.get("scene_turn"):
            print(f"    ISSUE: no scene turn detected")
            all_issues.append(f"{sid}: no scene turn")
        if metrics["dialogue_lines"] == 0:
            print(f"    ISSUE: no dialogue")
            all_issues.append(f"{sid}: no dialogue")
        if pct < 50:
            print(f"    ISSUE: very short ({pct:.0f}% of target)")
            all_issues.append(f"{sid}: very short")

        # Opening + closing preview
        if content:
            opening = content[:200].replace('\n', ' ')
            closing_paras = content.strip().split('\n\n')
            closing = closing_paras[-1][:200].replace('\n', ' ') if closing_paras else ""
            print(f"    OPEN:  {opening}...")
            print(f"    CLOSE: {closing}...")

    # --- Phase 5: Cross-Act Analysis ---
    print("\n" + "=" * 70)
    print("CROSS-ACT ANALYSIS")
    print("=" * 70)

    # Group scenes by act
    act_groups = {2: [], 6: [], 11: []}
    for scene in drafted_scenes:
        ch = scene.get("chapter", 0)
        if ch in act_groups:
            act_groups[ch].append(scene)

    # Continuity
    print("\n--- Continuity ---")
    cont = check_continuity(drafted_scenes)
    print(f"  Core names (30%+ scenes): {cont.get('core_names', [])}")
    print(f"  Sporadic names (1 scene):  {cont.get('sporadic_names', [])[:8]}")
    print(f"  Total unique names:        {cont.get('total_unique_names', 0)}")

    # Escalation check (word count and dialogue density per act)
    print("\n--- Escalation ---")
    for ch_num in TARGET_CHAPTERS:
        ch_scenes = act_groups.get(ch_num, [])
        if not ch_scenes:
            print(f"  Ch{ch_num}: no scenes drafted")
            continue
        avg_wc = sum(count_words(s.get("content", "")) for s in ch_scenes) / len(ch_scenes)
        avg_dl = sum(len(re.findall(r'"[^"]{5,}"', s.get("content", ""))) for s in ch_scenes) / len(ch_scenes)
        turns = sum(1 for m in all_metrics if m["label"].startswith(f"ch{ch_num:02d}") and m.get("scene_turn"))
        print(f"  Ch{ch_num}: avg {avg_wc:.0f} words, {avg_dl:.1f} dialogue lines/scene, "
              f"{turns}/{len(ch_scenes)} scene turns")

    # --- Summary ---
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")

    print(f"\n  Scenes drafted:  {len(drafted_scenes)}")
    print(f"  Planning time:   {planning_time:.1f}s ({planning_tokens} tokens)")
    print(f"  Prose time:      {prose_elapsed:.1f}s ({prose_tokens} tokens)")
    print(f"  Total time:      {planning_time + prose_elapsed:.1f}s")
    print(f"  Total tokens:    {planning_tokens + prose_tokens}")

    if all_metrics:
        avg_wc = sum(m["word_count"] for m in all_metrics) / len(all_metrics)
        avg_dl = sum(m["dialogue_lines"] for m in all_metrics) / len(all_metrics)
        total_tells = sum(len(m.get("ai_tells", [])) for m in all_metrics)
        scenes_with_turn = sum(1 for m in all_metrics if m.get("scene_turn"))
        preambles = sum(1 for m in all_metrics if m.get("preamble"))

        print(f"\n  Avg word count:     {avg_wc:.0f}")
        print(f"  Avg dialogue lines: {avg_dl:.1f}")
        print(f"  Total AI tells:     {total_tells}")
        print(f"  Scenes with turn:   {scenes_with_turn}/{len(all_metrics)}")
        print(f"  Preambles:          {preambles}/{len(all_metrics)}")

    meters_pass = meter_report.get("all_pass", True)
    print(f"\n  Meters: {'ALL PASS' if meters_pass else 'FAILURES DETECTED'}")

    if all_issues:
        print(f"\n  Issues ({len(all_issues)}):")
        for issue in all_issues:
            print(f"    - {issue}")

    # Verdict
    critical = [i for i in all_issues if "preamble" in i or "very short" in i]
    if critical:
        verdict = f"NEEDS WORK ({len(critical)} critical)"
    elif not meters_pass:
        verdict = "NEEDS WORK (meter failures)"
    elif len(all_issues) > len(drafted_scenes):
        verdict = "ACCEPTABLE (issues exceed scene count)"
    else:
        verdict = "PASS"

    print(f"\n  ACT TRIPOD VERDICT: {verdict}")
    print(f"\n{'=' * 70}")

    return {
        "verdict": verdict,
        "total_scenes": len(drafted_scenes),
        "preambles": preambles if all_metrics else 0,
        "avg_word_count": avg_wc if all_metrics else 0,
        "meters_pass": meters_pass,
        "critical_issues": len(critical),
    }


@pytest.mark.smoke
@pytest.mark.slow
def test_act_tripod(smoke_project):
    """Pytest wrapper for act tripod. Uses temp project from fixtures."""
    result = asyncio.run(run_act_tripod(project_path=smoke_project, model="qwen2.5:7b"))
    # Structural invariants that must hold for any non-broken run
    assert result["total_scenes"] > 0, "No scenes were drafted"
    assert result["preambles"] == 0, f"Preambles detected in {result['preambles']} scenes"
    assert result["avg_word_count"] >= 200, f"Avg word count too low: {result['avg_word_count']}"
    assert result["critical_issues"] == 0, f"Critical issues found: {result['critical_issues']}"


if __name__ == "__main__":
    asyncio.run(run_act_tripod())
