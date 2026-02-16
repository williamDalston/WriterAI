"""
Micro-Prose Test -- Blackwood Pack (Wolf Shifter Dual-POV)

Runs planning stages, then drafts 3 targeted scenes to validate:
  1. Dual first-person POV (Elena + Kaelen alternating chapters)
  2. Wolf voice in italics (Kaelen's inner wolf)
  3. Genre-specific quality (sensory detail, tension, forced proximity)
  4. POV postprocessing correctness (no pronoun corruption)

Scenes selected to stress dual-POV pipeline:
  Scene 1: Ch1-S1 (Elena POV)  -- blizzard opening, hook, first-person female
  Scene 2: Ch2-S1 (Kaelen POV) -- wolf awakening, forced proximity, first-person male
  Scene 3: Ch6-S1 (Kaelen POV) -- midpoint attack, caretaking, high emotional stakes

Usage:
    python -m tests.test_micro_prose_blackwood
"""

import sys
import asyncio
import logging
import json
import time
import re
import copy
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from prometheus_lib.llm.clients import OllamaClient
from stages.pipeline import PipelineOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("micro_prose_blackwood")

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

# Target scenes: (chapter, scene) tuples
# Ch1 = Elena (odd), Ch2 = Kaelen (even), Ch6 = Kaelen (even)
TARGET_SCENES = [
    (1, 1),   # Elena POV -- blizzard opening
    (2, 1),   # Kaelen POV -- wolf awakening, perimeter
    (6, 1),   # Kaelen POV -- midpoint attack + caretaking
]

# Expected POV per chapter (from config: Elena odd, Kaelen even)
EXPECTED_POV = {
    1: "Elena",
    2: "Kaelen",
    3: "Elena",
    4: "Kaelen",
    5: "Elena",
    6: "Kaelen",
    7: "Elena",
    8: "Kaelen",
    9: "Elena",
    10: "Kaelen",
    11: "Elena",
    12: "Kaelen",
}


def count_words(text):
    text = re.sub(r'^#+\s+.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'[\*_\[\]`#]', '', text)
    return len(text.split())


def count_pronouns(text):
    """Count pronoun groups in narrative text (dialogue stripped).

    Returns dict with counts for each pronoun category.
    """
    # Strip dialogue to only count narrative voice
    narrative = re.sub(r'"[^"]*"', '', text)
    narrative = re.sub(r'[\u201c][^\u201d]*[\u201d]', '', narrative)

    return {
        "I/my/me": len(re.findall(r'\b(?:I|my|me)\b', narrative)),
        "he/his/him": len(re.findall(r'\b(?:he|his|him)\b', narrative, re.IGNORECASE)),
        "she/her": len(re.findall(r'\b(?:she|her|hers)\b', narrative, re.IGNORECASE)),
    }


def check_corruption_sentinels(content, pov_gender):
    """Check for catastrophic pronoun corruption patterns.

    Returns list of corruption issues found.
    """
    issues = []

    # Strip dialogue
    narrative = re.sub(r'"[^"]*"', '', content)

    # Sentinel 1: "I said/whispered," + same-gender pronoun as speaker tag
    # This indicates the postprocessor converted the wrong pronoun
    if pov_gender == "male":
        # Male POV: "I said," he → corruption (he = narrator in 1st person)
        bad_tags = re.findall(
            r'\bI\s+(?:said|whispered|murmured|asked)[^.]*?\bhe\b',
            narrative, re.IGNORECASE
        )
        if bad_tags:
            issues.append(f"Corruption: {len(bad_tags)}x 'I said...he' (self-reference in 3rd person)")
    elif pov_gender == "female":
        bad_tags = re.findall(
            r'\bI\s+(?:said|whispered|murmured|asked)[^.]*?\bshe\b',
            narrative, re.IGNORECASE
        )
        if bad_tags:
            issues.append(f"Corruption: {len(bad_tags)}x 'I said...she' (self-reference in 3rd person)")

    # Sentinel 2: "my hands on her hips" in male POV (possessive swap)
    # or "my jaw clenched, his eyes" in female POV
    if pov_gender == "male":
        # Male POV narrator shouldn't have "She" + narrator body parts with "my"
        # "She grabbed my hand" is fine (other char grabs narrator's hand)
        # "my hands on her" is fine (narrator touching other)
        # But "She looked at me with my eyes" is corruption
        pass  # Too many false positives — skip for now

    # Sentinel 3: name used where "I" should be
    if pov_gender == "male":
        # Check if Kaelen is used in third person as narrator
        kaelen_3p = len(re.findall(
            r'\bKaelen\s+(?:thought|felt|walked|looked|turned|moved|knew|noticed|realized)',
            narrative, re.IGNORECASE
        ))
        if kaelen_3p > 0:
            issues.append(f"Narrator Kaelen in 3rd person {kaelen_3p}x (should be 'I')")
    elif pov_gender == "female":
        elena_3p = len(re.findall(
            r'\bElena\s+(?:thought|felt|walked|looked|turned|moved|knew|noticed|realized)',
            narrative, re.IGNORECASE
        ))
        if elena_3p > 0:
            issues.append(f"Narrator Elena in 3rd person {elena_3p}x (should be 'I')")

    return issues


def check_pov_correctness(content, chapter_num, scene_label):
    """Validate POV is correct for this chapter.

    Checks:
    - First person ("I") is dominant
    - No head-hopping (wrong character's internal thoughts)
    - Correct gender pronoun enforcement
    - Corruption sentinels
    - Before/after pronoun counts
    """
    expected = EXPECTED_POV.get(chapter_num, "unknown")
    issues = []

    # Pronoun counts (narrative only, dialogue stripped)
    pronouns = count_pronouns(content)

    # First-person dominance check
    i_count = pronouns["I/my/me"]
    if i_count < 5:
        issues.append(f"Low first-person count ({i_count})")

    pov_gender = ""
    if expected == "Elena":
        pov_gender = "female"
        # Elena is female. "She/her" in narrative should be lower than "I/my/me"
        # Some "she/her" is fine (referring to other female characters)
        # But "he/his" as self-reference = wrong conversion applied
        he_count = pronouns["he/his/him"]
        she_count = pronouns["she/her"]
        i_verb = len(re.findall(r'\bI\s+(walked|thought|felt|looked|turned)', content))
        he_verb = len(re.findall(r'\bHe\s+(walked|thought|felt|looked|turned)', content))
        if he_verb > i_verb + 5:
            issues.append(f"Suspicious He-verb dominance ({he_verb} vs I-verb {i_verb})")

    elif expected == "Kaelen":
        pov_gender = "male"
        # Kaelen is male. "He/his" in narrative should be lower than "I/my/me"
        he_count = pronouns["he/his/him"]
        she_count = pronouns["she/her"]
        i_verb = len(re.findall(r'\bI\s+(walked|thought|felt|looked|turned)', content))
        she_verb = len(re.findall(r'\bShe\s+(walked|thought|felt|looked|turned)', content))
        if she_verb > i_verb + 5:
            issues.append(f"Suspicious She-verb dominance ({she_verb} vs I-verb {i_verb})")

        # Check for wolf voice (italics) — Kaelen chapters should have some
        italic_phrases = re.findall(r'\*([^*]+)\*|_([^_]+)_', content)
        wolf_voice_count = len(italic_phrases)
        if wolf_voice_count == 0:
            issues.append("No wolf voice (italic inner monologue) detected in Kaelen chapter")

    # Run corruption sentinels
    corruption = check_corruption_sentinels(content, pov_gender)
    issues.extend(corruption)

    return {
        "expected_pov": expected,
        "pov_gender": pov_gender,
        "pronoun_counts": pronouns,
        "corruption_sentinels": corruption,
        "issues": issues,
        "pass": len(issues) == 0,
    }


def check_scene_quality(content, scene_label, chapter_num):
    """Run quality checks on a drafted scene."""
    if not content or not content.strip():
        return {"error": "Empty scene", "word_count": 0}

    word_count = count_words(content)
    sentences = [s.strip() for s in re.split(r'[.!?]+', content) if s.strip()]
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

    metrics = {
        "word_count": word_count,
        "paragraph_count": len(paragraphs),
        "sentence_count": len(sentences),
    }

    # Preamble check
    preamble_patterns = [
        r"^(certainly|sure|here is|below is|as requested|i'd be happy)",
        r"^(chapter \d+|scene \d+:)",
    ]
    first_line = content.strip().split('\n')[0].lower()
    for pat in preamble_patterns:
        if re.search(pat, first_line):
            metrics["preamble_detected"] = first_line[:80]
            break

    # POV correctness (dual-POV specific)
    pov_result = check_pov_correctness(content, chapter_num, scene_label)
    metrics["pov_check"] = pov_result

    # Dialogue
    dialogue_lines = len(re.findall(r'"[^"]{5,}"', content))
    metrics["dialogue_lines"] = dialogue_lines
    if dialogue_lines == 0:
        metrics["dialogue_issue"] = "No dialogue found"

    # Genre-specific sensory checks (wolf shifter)
    cold_words = re.findall(r'\b(cold|ice|frost|snow|blizzard|shiver|freeze|frozen|chill|wind|winter|storm)\b', content, re.I)
    scent_words = re.findall(r'\b(scent|smell|pine|woodsmoke|rain|musk|blood|adrenaline|ozone|diesel)\b', content, re.I)
    touch_words = re.findall(r'\b(skin|heat|warm|touch|grip|fingers|palm|rough|press|pulse|heartbeat|shudder)\b', content, re.I)
    metrics["cold_words"] = len(cold_words)
    metrics["scent_words"] = len(scent_words)
    metrics["touch_words"] = len(touch_words)

    # AI tells
    ai_tells = [
        "couldn't help but", "found myself", "a sense of", "I realized",
        "electricity coursed", "butterflies in", "walls crumbling",
        "breath I didn't know", "heart skipped", "everything changed",
        "nothing would ever be the same", "a whirlwind of",
    ]
    found_tells = [t for t in ai_tells if t.lower() in content.lower()]
    metrics["ai_tells_found"] = found_tells
    metrics["ai_tell_count"] = len(found_tells)

    # Sentence rhythm
    if sentences:
        lengths = [len(s.split()) for s in sentences if s.split()]
        if lengths:
            avg_len = sum(lengths) / len(lengths)
            variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
            metrics["avg_sentence_length"] = round(avg_len, 1)
            metrics["sentence_length_variance"] = round(variance ** 0.5, 1)

    # Scene turn
    if paragraphs:
        last_para = paragraphs[-1].lower()
        turn_signals = ["but", "then", "until", "except", "instead",
                        "realize", "knew", "changed", "shifted",
                        "door", "phone", "voice", "said", "asked"]
        has_turn = any(sig in last_para for sig in turn_signals)
        metrics["scene_turn_detected"] = has_turn

    return metrics


async def run_micro_prose_blackwood():
    project_path = ROOT / "data" / "projects" / "blackwood-pack"
    if not (project_path / "config.yaml").exists():
        logger.error(f"Blackwood Pack project not found at {project_path}")
        return

    ollama = OllamaClient("qwen2.5:14b")
    pipeline = PipelineOrchestrator(
        project_path=project_path,
        llm_client=ollama,
        llm_clients={"gpt": ollama, "claude": ollama, "gemini": ollama},
    )

    await pipeline.initialize()

    print("\n" + "=" * 70)
    print("MICRO-PROSE TEST -- Blackwood Pack (Dual-POV Wolf Shifter)")
    print("Model: qwen2.5:14b (Q4_K_M, 32k context)")
    print(f"Target scenes: {TARGET_SCENES}")
    print("POV map: Elena (odd chapters), Kaelen (even chapters)")
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

    # Verify outline
    if not pipeline.state.master_outline:
        print("  ERROR: No master outline generated.")
        return

    total_chapters = len(pipeline.state.master_outline)
    total_scenes = sum(
        len(ch.get("scenes", []))
        for ch in pipeline.state.master_outline
        if isinstance(ch, dict)
    )
    print(f"  Outline: {total_chapters} chapters, {total_scenes} scenes")

    # Show POV assignments from outline
    print("\n  POV assignments from outline:")
    for ch in pipeline.state.master_outline:
        if not isinstance(ch, dict):
            continue
        ch_num = ch.get("chapter", "?")
        for sc in ch.get("scenes", []):
            if isinstance(sc, dict):
                pov = sc.get("pov", "?")
                expected = EXPECTED_POV.get(ch_num, "?")
                match = "OK" if pov and expected.lower() in pov.lower() else "MISMATCH"
                if ch_num in [c for c, _ in TARGET_SCENES]:
                    sc_num = sc.get("scene", sc.get("scene_number", "?"))
                    print(f"    Ch{ch_num}-S{sc_num}: pov={pov} (expected={expected}) [{match}]")

    # --- Phase 2: Draft target scenes ---
    print("\n--- PHASE 2: Prose Drafting (3 target scenes) ---")

    full_outline = copy.deepcopy(pipeline.state.master_outline)

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
                sc_num = sc.get("scene", sc.get("scene_number", 0))
                if sc_num in target_scene_nums:
                    filtered_scenes.append(sc)
            ch_copy = dict(ch)
            ch_copy["scenes"] = filtered_scenes
            filtered_outline.append(ch_copy)

    print(f"  Filtered outline: {len(filtered_outline)} chapters, "
          f"{sum(len(c.get('scenes', [])) for c in filtered_outline)} scenes")

    for ch in filtered_outline:
        ch_num = ch.get("chapter", "?")
        for sc in ch.get("scenes", []):
            sc_num = sc.get("scene", sc.get("scene_number", "?"))
            sc_name = sc.get("scene_name", "?")
            pov = sc.get("pov", "?")
            print(f"  --> Ch{ch_num}-S{sc_num}: \"{sc_name}\" (POV: {pov})")

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

    print(f"\n  Prose drafting: {prose_elapsed:.1f}s, {prose_tokens} tokens, "
          f"{len(pipeline.state.scenes)} scenes")

    # --- Phase 3: Quality Analysis ---
    print("\n" + "=" * 70)
    print("DUAL-POV QUALITY ANALYSIS")
    print("=" * 70)

    all_issues = []
    all_metrics = []
    pov_pass_count = 0

    for i, scene in enumerate(pipeline.state.scenes):
        ch = scene.get("chapter", 0)
        sc = scene.get("scene_number", "?")
        content = scene.get("content", "")
        pov = scene.get("pov", "?")
        label = f"Ch{ch}-S{sc}"

        print(f"\n--- Scene {i+1}: {label} (POV: {pov}) ---")

        metrics = check_scene_quality(content, label, ch)
        all_metrics.append(metrics)

        # Basic stats
        wc = metrics["word_count"]
        paras = metrics["paragraph_count"]
        sents = metrics["sentence_count"]
        print(f"  Words: {wc}  |  Paragraphs: {paras}  |  Sentences: {sents}")

        # Word count check
        target = pipeline.state.words_per_scene
        pct = (wc / target * 100) if target else 0
        status = "OK" if pct >= 80 else "SHORT" if pct >= 50 else "VERY SHORT"
        print(f"  Target: {target} words -> {pct:.0f}% ({status})")

        # POV correctness (CRITICAL for dual-POV)
        pov_check = metrics.get("pov_check", {})
        expected_pov = pov_check.get("expected_pov", "?")
        pov_gender = pov_check.get("pov_gender", "?")
        pov_ok = pov_check.get("pass", False)
        pcounts = pov_check.get("pronoun_counts", {})
        i_count = pcounts.get("I/my/me", 0)
        he_count = pcounts.get("he/his/him", 0)
        she_count = pcounts.get("she/her", 0)
        if pov_ok:
            pov_pass_count += 1
        print(f"  POV: {'PASS' if pov_ok else 'FAIL'} "
              f"(expected={expected_pov}, gender={pov_gender})")
        print(f"  Pronouns (narrative): I/my/me={i_count}  "
              f"he/his/him={he_count}  she/her={she_count}")

        # Corruption sentinels
        corruptions = pov_check.get("corruption_sentinels", [])
        if corruptions:
            for c in corruptions:
                print(f"    !! {c}")

        for issue in pov_check.get("issues", []):
            print(f"    -> {issue}")
            all_issues.append(f"{label}: POV: {issue}")

        # Dialogue
        dl = metrics.get("dialogue_lines", 0)
        print(f"  Dialogue: {dl} lines {'(OK)' if dl >= 2 else '(LOW)'}")

        # Genre sensory
        cold = metrics.get("cold_words", 0)
        scent = metrics.get("scent_words", 0)
        touch = metrics.get("touch_words", 0)
        print(f"  Sensory: cold={cold}, scent={scent}, touch={touch}")

        # AI tells
        tells = metrics.get("ai_tells_found", [])
        print(f"  AI tells: {tells if tells else 'None (clean)'}")

        # Rhythm
        avg_sl = metrics.get("avg_sentence_length", 0)
        sl_var = metrics.get("sentence_length_variance", 0)
        print(f"  Rhythm: avg {avg_sl} words/sentence, variance {sl_var} "
              f"{'(varied)' if sl_var >= 3.0 else '(monotonous)'}")

        # Scene turn
        has_turn = metrics.get("scene_turn_detected", False)
        print(f"  Scene turn: {'DETECTED' if has_turn else 'MISSING'}")

        # Preamble
        if "preamble_detected" in metrics:
            print(f"  PREAMBLE: {metrics['preamble_detected']}")
            all_issues.append(f"{label}: preamble detected")

        # Collect other issues
        if "dialogue_issue" in metrics:
            all_issues.append(f"{label}: {metrics['dialogue_issue']}")
        if tells:
            all_issues.append(f"{label}: {len(tells)} AI tell-phrases")

        # Preview
        preview = content[:300].replace('\n', ' ') if content else "(empty)"
        print(f"\n  OPENING:\n    {preview}...")

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

    # Dual-POV verdict
    total_scenes = len(pipeline.state.scenes)
    print(f"\n  DUAL-POV: {pov_pass_count}/{total_scenes} scenes passed POV check")

    # Per-scene pronoun summary table
    print(f"\n  Pronoun summary (narrative only, dialogue stripped):")
    print(f"  {'Scene':<12} {'POV':<8} {'Gender':<7} {'I/my/me':>7} {'he/his':>7} {'she/her':>7} {'Result':<6}")
    print(f"  {'-'*60}")
    for i, m in enumerate(all_metrics):
        pc = m.get("pov_check", {})
        pcnts = pc.get("pronoun_counts", {})
        sc = pipeline.state.scenes[i] if i < len(pipeline.state.scenes) else {}
        lbl = f"Ch{sc.get('chapter', '?')}-S{sc.get('scene_number', '?')}"
        print(f"  {lbl:<12} {pc.get('expected_pov', '?'):<8} "
              f"{pc.get('pov_gender', '?'):<7} "
              f"{pcnts.get('I/my/me', 0):>7} "
              f"{pcnts.get('he/his/him', 0):>7} "
              f"{pcnts.get('she/her', 0):>7} "
              f"{'PASS' if pc.get('pass') else 'FAIL':<6}")

    if all_metrics:
        avg_wc = sum(m.get("word_count", 0) for m in all_metrics) / len(all_metrics)
        total_tells = sum(m.get("ai_tell_count", 0) for m in all_metrics)
        scenes_with_turn = sum(1 for m in all_metrics if m.get("scene_turn_detected"))

        print(f"  Avg word count:   {avg_wc:.0f}")
        print(f"  Total AI tells:   {total_tells}")
        print(f"  Scenes with turn: {scenes_with_turn}/{total_scenes}")

    if all_issues:
        print(f"\n  Issues ({len(all_issues)}):")
        for issue in all_issues:
            print(f"    - {issue}")
    else:
        print(f"\n  Issues: None")

    # Verdict
    pov_issues = [i for i in all_issues if "POV" in i]
    preamble_issues = [i for i in all_issues if "preamble" in i]
    critical = pov_issues + preamble_issues

    if critical:
        print(f"\n  VERDICT: FAIL ({len(critical)} critical issues)")
    elif pov_pass_count < total_scenes:
        print(f"\n  VERDICT: NEEDS WORK (POV issues)")
    elif len(all_issues) > 3:
        print(f"\n  VERDICT: ACCEPTABLE (minor issues)")
    else:
        print(f"\n  VERDICT: PASS")

    print(f"\n{'=' * 70}")


if __name__ == "__main__":
    asyncio.run(run_micro_prose_blackwood())
