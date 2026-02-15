"""Test all pipeline fixes: gender POV, scene cleanup, story state, genre hooks."""
import sys, os
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(__file__))

passed = 0
failed = 0


def test(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  PASS: {name}")
        passed += 1
    else:
        print(f"  FAIL: {name} — {detail}")
        failed += 1


# ═══════════════════════════════════════════════════════════════
# 1. GENDER-AWARE POV ENFORCER
# ═══════════════════════════════════════════════════════════════
print("\n=== 1. Gender-Aware POV Enforcer ===")
from prometheus_novel.stages.pipeline import _enforce_first_person_pov

# 1a. Male protagonist: "He walked" → "I walked" but "She smiled" stays
text = "He walked into the room. She smiled at him."
result = _enforce_first_person_pov(text, "Ethan Reeves", "male")
test("Male: 'He walked' → 'I walked'", "I walked" in result, repr(result))
test("Male: 'She smiled' stays", "She smiled" in result, repr(result))

# 1b. Male: "his jaw" → "my jaw" but "her hair" stays (THE CRITICAL BUG FIX)
text = "I clenched his jaw. I tucked a strand behind her ear."
result = _enforce_first_person_pov(text, "Ethan", "male")
test("Male: 'his jaw' → 'my jaw'", "my jaw" in result, repr(result))
test("Male: 'her ear' STAYS (love interest)", "her ear" in result, repr(result))

# 1c. Female protagonist: opposite behavior
text = "She felt tired. He smiled at her."
result = _enforce_first_person_pov(text, "Lena", "female")
test("Female: 'She felt' → 'I felt'", "I felt" in result, repr(result))
test("Female: 'He smiled' stays", "He smiled" in result, repr(result))

# 1d. Female: "her heart" → "my heart" but "his jaw" stays
text = "I felt her heart race. I saw his jaw clench."
result = _enforce_first_person_pov(text, "Lena", "female")
test("Female: 'her heart' → 'my heart'", "my heart" in result, repr(result))
test("Female: 'his jaw' STAYS", "his jaw" in result, repr(result))

# 1e. Unknown gender: only fix name, skip pronouns
text = "Ethan walked away. He felt tired. She smiled."
result = _enforce_first_person_pov(text, "Ethan", "")
test("Unknown: 'Ethan walked' → 'I walked'", "I walked" in result, repr(result))
test("Unknown: 'He felt' stays (no gender)", "He felt" in result, repr(result))
test("Unknown: 'She smiled' stays", "She smiled" in result, repr(result))

# 1f. Name possessive: "Ethan's voice" → "my voice"
text = "Ethan's voice cracked."
result = _enforce_first_person_pov(text, "Ethan", "male")
test("Name possessive: 'Ethan's voice' → 'My voice'",
     "My voice" in result or "my voice" in result, repr(result))

# ═══════════════════════════════════════════════════════════════
# 2. SCENE HEADER / XML TAG CLEANUP
# ═══════════════════════════════════════════════════════════════
print("\n=== 2. Scene Header & XML Cleanup ===")
from prometheus_novel.stages.pipeline import _clean_scene_content

# 2a. Scene header
text = "Chapter 3, Scene 2 POV: FIRST PERSON — Ethan\nI walked into the bar."
result = _clean_scene_content(text)
test("Scene header removed", "Chapter 3" not in result and "I walked" in result, repr(result))

# 2b. XML tags
text = "<scene>\nI opened the door.\n</scene>"
result = _clean_scene_content(text)
test("<scene> tags removed", "<scene>" not in result and "</scene>" not in result
     and "I opened" in result, repr(result))

# 2c. Beat sheet artifacts
text = "I looked at her.\nPhysical beats:\n- My fingers traced the table\n- I shifted my weight"
result = _clean_scene_content(text)
test("Beat sheet 'Physical beats:' removed", "Physical beats" not in result
     and "I looked" in result, repr(result))

# 2d. POV header
text = "POV: FIRST PERSON — Ethan Reeves\nThe coffee was terrible."
result = _clean_scene_content(text)
test("POV header removed", "POV:" not in result and "coffee" in result, repr(result))

# 2e. "Remains unchanged" mid-text
text = "I smiled at her. The rest of the scene remains unchanged. She waved back."
result = _clean_scene_content(text)
test("'remains unchanged' removed inline",
     "remains unchanged" not in result and "I smiled" in result, repr(result))

# 2f. LLM preamble
text = "Sure, here's the revised version:\nI walked into the room and sat down."
result = _clean_scene_content(text)
test("LLM preamble stripped", "Sure" not in result and "revised" not in result
     and "walked" in result, repr(result))

# 2g. "A great chapter-ending hook can be:" + bullet list
text = "I closed the door.\nA great chapter-ending hook can be:\n- A cliffhanger\n- A twist revealed\nShe left."
result = _clean_scene_content(text)
test("Hook instruction + bullets removed",
     "great chapter-ending" not in result and "I closed" in result, repr(result))


# ═══════════════════════════════════════════════════════════════
# 3. STORY STATE BUILDER
# ═══════════════════════════════════════════════════════════════
print("\n=== 3. Story State Builder ===")

# Create a mock orchestrator with outline data
class MockState:
    def __init__(self):
        self.config = {
            "genre": "romance",
            "protagonist": "Ethan Reeves, 29. American software engineer",
            "writing_style": "First person, Ethan's POV",
        }
        self.master_outline = [
            {
                "chapter": 1,
                "chapter_title": "The Flight",
                "scenes": [
                    {"scene": 1, "scene_name": "Boarding", "purpose": "Ethan boards the plane", "location": "DFW Airport"},
                    {"scene": 2, "scene_name": "Seatmates", "purpose": "They meet in adjacent seats", "location": "Airplane Cabin"},
                    {"scene": 3, "scene_name": "Landing", "purpose": "They land and separate", "location": "Mexico City Airport"},
                ]
            },
            {
                "chapter": 2,
                "chapter_title": "The Search",
                "scenes": [
                    {"scene": 1, "scene_name": "Instagram", "purpose": "Ethan finds Ana online", "location": "Ethan's apartment, Austin"},
                    {"scene": 2, "scene_name": "First Message", "purpose": "He sends her a DM", "location": "Ethan's apartment, Austin"},
                ]
            },
            {
                "chapter": 3,
                "chapter_title": "Connection",
                "scenes": [
                    {"scene": 1, "scene_name": "First Call", "purpose": "First video call", "location": "Ethan's apartment, Austin"},
                    {"scene": 2, "scene_name": "Late Night", "purpose": "3am call, deeper bond", "location": "Ethan's apartment, Austin"},
                ]
            },
        ]
        self.characters = {}
        self.scenes = []

class MockOrchestrator:
    def __init__(self):
        self.state = MockState()

# Import the method — it's an instance method on PipelineOrchestrator
from prometheus_novel.stages.pipeline import PipelineOrchestrator
# We can test _build_story_state by calling it on a mock
orch = MockOrchestrator()
# Bind the method
orch._build_story_state = PipelineOrchestrator._build_story_state.__get__(orch)

# Simulate: we're writing Chapter 2, Scene 2. 4 scenes already written.
written_scenes = [
    {"chapter": 1, "scene_number": 1, "location": "DFW Airport", "content": "..."},
    {"chapter": 1, "scene_number": 2, "location": "Airplane Cabin", "content": "..."},
    {"chapter": 1, "scene_number": 3, "location": "Mexico City Airport", "content": "..."},
    {"chapter": 2, "scene_number": 1, "location": "Ethan's apartment, Austin", "content": "..."},
]

result = orch._build_story_state(written_scenes, current_chapter=2, current_scene=2)

test("Contains story progress", "scene 5" in result.lower() or "Scene 5" in result, repr(result[:200]))
test("Contains COMPLETED chapter 1", "Ch1" in result and "The Flight" in result, repr(result[:400]))
test("Says ALREADY HAPPENED", "ALREADY HAPPENED" in result, repr(result[:500]))
test("Shows current chapter scenes", "WRITING NOW" in result, repr(result))
test("Shows Scene 1 as DONE in chapter 2", "[DONE]" in result, repr(result))
test("Contains recent locations", "DFW Airport" in result or "Airplane Cabin" in result or "Ethan's apartment" in result, repr(result))
test("Contains CRITICAL CONTINUITY RULES", "ALREADY MET" in result, repr(result))
test("Contains relationship state (romance)", "NARRATIVE ARC" in result, repr(result))

# 3b. Test with many scenes in same location (coffee shop detection)
many_scenes = [
    {"chapter": 1, "scene_number": i, "location": "Corner Café", "content": "..."}
    for i in range(1, 6)
]
result2 = orch._build_story_state(many_scenes, current_chapter=2, current_scene=1)
test("Overused location flagged", "OVERUSED" in result2 or "Corner Café" in result2, repr(result2))

# 3c. Test opening scene (no prior context)
result3 = orch._build_story_state([], current_chapter=1, current_scene=1)
test("Opening scene: no ALREADY MET warning", "ALREADY MET" not in result3, repr(result3))
test("Opening scene: shows chapter 1 as current", "CURRENT CHAPTER 1" in result3, repr(result3))


# ═══════════════════════════════════════════════════════════════
# 4. PREVIOUS SCENE CONTEXT (rewritten)
# ═══════════════════════════════════════════════════════════════
print("\n=== 4. Previous Scene Context ===")

orch._get_previous_scenes_context = PipelineOrchestrator._get_previous_scenes_context.__get__(orch)

# Test with scenes that have multi-paragraph content
scenes_with_content = [
    {"chapter": 1, "scene_number": 1, "location": "Airport", "content": "First paragraph.\n\nSecond paragraph.\n\nThird paragraph ending scene."},
    {"chapter": 1, "scene_number": 2, "location": "Plane", "content": "Para one.\n\nPara two.\n\nThe plane touched down and I felt my stomach drop."},
]

result = orch._get_previous_scenes_context(scenes_with_content)
test("Returns endings (not beginnings)", "ending scene" in result.lower() or "stomach drop" in result.lower(), repr(result))
test("Shows location", "Airport" in result or "Plane" in result, repr(result))
test("Labels as ENDING", "ENDING" in result, repr(result))

# Empty scenes
result_empty = orch._get_previous_scenes_context([])
test("Empty scenes: opening message", "opening scene" in result_empty.lower(), repr(result_empty))


# ═══════════════════════════════════════════════════════════════
# 5. PROTAGONIST GENDER DETECTION
# ═══════════════════════════════════════════════════════════════
print("\n=== 5. Protagonist Gender Detection ===")

orch._get_protagonist_gender = PipelineOrchestrator._get_protagonist_gender.__get__(orch)

# Default config has "Ethan" and "Ethan's POV"
result = orch._get_protagonist_gender()
test("Ethan detected as male", result == "male", f"got '{result}'")

# Female protagonist
orch.state.config["protagonist"] = "Lena Vasquez, 28. She is a detective."
orch.state.config["writing_style"] = "First person, Lena's POV"
result = orch._get_protagonist_gender()
test("Lena detected as female", result == "female", f"got '{result}'")

# Ambiguous
orch.state.config["protagonist"] = "Alex, 30. A scientist."
orch.state.config["writing_style"] = "First person, Alex's POV"
result = orch._get_protagonist_gender()
test("Alex detected as unknown", result == "", f"got '{result}'")


# ═══════════════════════════════════════════════════════════════
# 6. CONTEXTUAL POV REPAIR (_repair_pov_context_errors)
# ═══════════════════════════════════════════════════════════════
print("\n=== 6. Contextual POV Repair ===")
from prometheus_novel.stages.pipeline import _repair_pov_context_errors

# 6a. Pattern 1: "she whispered, my voice" -> "her voice"
text = "She whispered, my voice barely audible in the dark."
result = _repair_pov_context_errors(text, "male")
test("P1: 'she whispered, my voice' → 'her voice'",
     "her voice" in result and "my voice" not in result, repr(result))

# 6b. Pattern 1 with different verb: "she said, my eyes"
text = "She said, my eyes sparkling with mischief."
result = _repair_pov_context_errors(text, "male")
test("P1: 'she said, my eyes' → 'her eyes'",
     "her eyes" in result, repr(result))

# 6c. Pattern 2: "[Name] said, my voice" -> "her voice"
text = "Ana said, my voice soft and clear."
result = _repair_pov_context_errors(text, "male")
test("P2: 'Ana said, my voice' → 'her voice'",
     "her voice" in result, repr(result))

# 6d. Pattern 3: "She rolled my eyes" -> "her eyes"
text = "She rolled my eyes and turned away."
result = _repair_pov_context_errors(text, "male")
test("P3: 'She rolled my eyes' → 'her eyes'",
     "her eyes" in result, repr(result))

# 6e. Pattern 3: "She tilted my head" -> "her head"
text = "She tilted my head to the side."
result = _repair_pov_context_errors(text, "male")
test("P3: 'She tilted my head' → 'her head'",
     "her head" in result, repr(result))

# 6f. Pattern 4: "I smiled, gazing at me" -> "She smiled, gazing at me"
text = "I smiled warmly, gazing at me across the table."
result = _repair_pov_context_errors(text, "male")
test("P4: 'I smiled, gazing at me' → 'She smiled'",
     "She smiled" in result, repr(result))

# 6g. Pattern 5: "I turned to face me" -> "She turned to face me"
text = "I turned to face me with a serious expression."
result = _repair_pov_context_errors(text, "male")
test("P5: 'I turned to face me' → 'She turned'",
     "She turned" in result, repr(result))

# 6h. Pattern 5: "I looked at me" -> "She looked at me"
text = "I looked at me with concern."
result = _repair_pov_context_errors(text, "male")
test("P5: 'I looked at me' → 'She looked at me'",
     "She looked at me" in result, repr(result))

# 6i. Pattern 6: "I followed my back" -> "I followed her back"
text = "I followed my back through the corridor."
result = _repair_pov_context_errors(text, "male")
test("P6: 'I followed my back' → 'her back'",
     "her back" in result, repr(result))

# 6j. Pattern 7: Strip markdown bold/italic
text = "I felt **terrified** but kept my *composure* intact."
result = _repair_pov_context_errors(text, "male")
test("P7: Markdown **bold** stripped",
     "**" not in result and "terrified" in result, repr(result))
test("P7: Markdown *italic* stripped",
     result.count("*") == 0 and "composure" in result, repr(result))

# 6k. Female protagonist: uses "his" instead of "her"
text = "He whispered, my voice cracking with emotion."
result = _repair_pov_context_errors(text, "female")
test("Female P1: 'he whispered, my voice' → 'his voice'",
     "his voice" in result, repr(result))

# 6l. Unknown gender: returns unchanged
text = "She whispered, my voice barely audible."
result = _repair_pov_context_errors(text, "")
test("Unknown gender: no changes",
     "my voice" in result, repr(result))

# 6m. No false positive: narrator's own possessive stays
text = "I whispered, my voice barely audible."
result = _repair_pov_context_errors(text, "male")
test("No false positive: 'I whispered, my voice' stays",
     "my voice" in result, repr(result))


# ═══════════════════════════════════════════════════════════════
# 7. EXPANDED EMOTIONAL SUMMARY STRIPPING
# ═══════════════════════════════════════════════════════════════
print("\n=== 7. Expanded Emotional Summary Stripping ===")
from prometheus_novel.stages.pipeline import _strip_emotional_summaries

# 7a. "This small moment" pattern
text = "I smiled at her.\n\nShe took my hand. This small moment felt like everything."
result = _strip_emotional_summaries(text)
test("'This small moment' stripped",
     "This small moment" not in result and "I smiled" in result, repr(result))

# 7b. "whatever came next" pattern
text = "I kissed her forehead.\n\nI held her close. Whatever came next, I was ready."
result = _strip_emotional_summaries(text)
test("'Whatever came next' stripped",
     "Whatever came next" not in result and "I kissed" in result, repr(result))

# 7c. "a testament to" pattern
text = "The code compiled.\n\nIt worked perfectly. It was a testament to our hard work."
result = _strip_emotional_summaries(text)
test("'a testament to' stripped",
     "testament" not in result, repr(result))


# ═══════════════════════════════════════════════════════════════
# 8. EXPANDED TIC FREQUENCY LIMITER
# ═══════════════════════════════════════════════════════════════
print("\n=== 8. Expanded Tic Frequency Limiter ===")
from prometheus_novel.stages.pipeline import _limit_tic_frequency

# 8a. "comfort zone" repeated too many times
text = "I left my comfort zone.\n\nThis was out of my comfort zone.\n\nWay outside my comfort zone."
result = _limit_tic_frequency(text)
comfort_count = result.lower().count("comfort zone")
test("'comfort zone' limited to <=2 occurrences",
     comfort_count <= 2, f"found {comfort_count}")

# 8b. "warmth spread" repeated
text = "Warmth spread through me.\n\nWarmth spread in my chest.\n\nWarmth spread again."
result = _limit_tic_frequency(text)
warmth_count = result.lower().count("warmth spread")
test("'warmth spread' limited",
     warmth_count <= 2, f"found {warmth_count}")


# ═══════════════════════════════════════════════════════════════
# 9. DEFENSE ARCHITECTURE IMPROVEMENTS
# ═══════════════════════════════════════════════════════════════
print("\n=== 9. Defense Architecture Improvements ===")

# 9a. Issue-specific retry feedback constants exist
from prometheus_novel.stages.pipeline import ISSUE_SPECIFIC_FEEDBACK
test("Issue-specific feedback dict exists",
     isinstance(ISSUE_SPECIFIC_FEEDBACK, dict) and len(ISSUE_SPECIFIC_FEEDBACK) >= 4,
     f"got {type(ISSUE_SPECIFIC_FEEDBACK)} len {len(ISSUE_SPECIFIC_FEEDBACK)}")
test("Feedback has preamble key", "preamble" in ISSUE_SPECIFIC_FEEDBACK, "")
test("Feedback has truncation key", "truncation_marker" in ISSUE_SPECIFIC_FEEDBACK, "")

# 9b. Fuzzy preamble detection via n-gram similarity
test("n-gram sim: exact preamble = high similarity",
     PipelineOrchestrator._ngram_similarity("sure here is the revised scene", "sure here is the revised scene") > 0.9,
     "")
test("n-gram sim: novel variant catches preamble",
     PipelineOrchestrator._ngram_similarity("okay so here is the improved scene", "sure here is the revised scene") > 0.2,
     "")
test("n-gram sim: prose != preamble",
     PipelineOrchestrator._ngram_similarity("The rain hammered the windshield as I drove", "sure here is the revised scene") < 0.15,
     "")

# 9c. Semantic dedup function exists and works
from prometheus_novel.stages.pipeline import _detect_semantic_duplicates

# Paraphrased restart (same content, slightly different wording — must be >500 chars total)
para1 = ("The rain poured down as I walked through the dark city streets. My coat was soaked through "
         "and the cold bit into my skin. Every step felt heavier than the last. The neon signs reflected "
         "off the wet pavement like scattered jewels. I pulled my collar up against the wind.")
para2 = ("Rain fell heavily as I made my way through the darkened city. My jacket was completely drenched "
         "and the chill cut through to my bones. Each footfall seemed more weary than the one before. "
         "Neon lights bounced off the slick asphalt like tiny gemstones. I tugged my collar higher.")
text_dup = para1 + "\n\n" + para1 + "\n\n" + para2 + "\n\n" + para2
result = _detect_semantic_duplicates(text_dup, threshold=0.4)
test("Semantic dedup: removes paraphrased second half",
     len(result) < len(text_dup), f"len {len(result)} vs {len(text_dup)}")

# Short text: no change
short = "Hello world.\n\nGoodbye."
test("Semantic dedup: short text unchanged",
     _detect_semantic_duplicates(short) == short, "")

# 9d. Clause-level possessive guard (POV enforcement)
from prometheus_novel.stages.pipeline import _enforce_first_person_pov

# "the woman who had been his closest friend" should NOT become "my closest friend"
text = "The woman who had been his closest friend walked in."
result = _enforce_first_person_pov(text, "Ethan", "male")
test("Clause guard: 'who had been his' stays (relative clause)",
     "his closest" in result, repr(result))

# Regular possessive still converts
text = "I clenched his jaw tightly."
result = _enforce_first_person_pov(text, "Ethan", "male")
test("Regular possessive: 'his jaw' -> 'my jaw'",
     "my jaw" in result, repr(result))

# "a friend of his" should stay
text = "She was a friend of his."
result = _enforce_first_person_pov(text, "Ethan", "male")
# Note: "of his" has no body_part, so it wouldn't match anyway. Test for safety.
test("'of his' context: no false positive",
     "his" in result.lower(), repr(result))

# 9e. disabled_builtins YAML support
from prometheus_novel.stages.pipeline import _clean_scene_content, _load_cleanup_config
cfg = _load_cleanup_config()
test("Cleanup config loads disabled_builtins key",
     "disabled_builtins" in cfg, repr(list(cfg.keys())))

# 9f. Context schema validation (test the method exists and catches red flags)
import logging
# Temporarily capture warnings
from prometheus_novel.stages.pipeline import PipelineOrchestrator
orch2 = MockOrchestrator()
orch2._validate_context_schema = PipelineOrchestrator._validate_context_schema.__get__(orch2)
# This should NOT raise — just logs a warning for suspicious content
try:
    orch2._validate_context_schema("WRITING STYLE: literary\ndef some_function():\n    pass", 0)
    test("Context schema: validates without crashing", True, "")
except Exception as e:
    test("Context schema: validates without crashing", False, str(e))

# Clean context should pass silently
try:
    orch2._validate_context_schema("WRITING STYLE: literary\nTONE: dark and moody", 0)
    test("Context schema: clean context passes", True, "")
except Exception as e:
    test("Context schema: clean context passes", False, str(e))

# 9g. Alignment check method exists
orch3 = MockOrchestrator()
orch3._check_alignment = PipelineOrchestrator._check_alignment.__get__(orch3)
orch3.state.scenes = [
    {"chapter": 1, "scene_number": i, "content": "Some scene content about the flight and boarding."}
    for i in range(1, 11)
]
# At index 0 it should return None (not a check interval)
result = orch3._check_alignment(0)
test("Alignment check: index 0 returns None", result is None, repr(result))
# At index 5 it should run (default interval = 5)
result = orch3._check_alignment(5)
# May or may not return a warning depending on overlap — just check it doesn't crash
test("Alignment check: index 5 runs without error", True, "")


# ═══════════════════════════════════════════════════════════════
# 10. DEFENSE ARCHITECTURE BATCH 2
# ═══════════════════════════════════════════════════════════════
print("\n=== 10. Defense Architecture Batch 2 ===")

# 10a. Sentinel stop token constant exists
from prometheus_novel.stages.pipeline import PROSE_SENTINEL, CREATIVE_STOP_SEQUENCES
test("PROSE_SENTINEL defined", "<END_PROSE>" in PROSE_SENTINEL, repr(PROSE_SENTINEL))
test("Sentinel is first stop sequence", CREATIVE_STOP_SEQUENCES[0] == PROSE_SENTINEL,
     f"first={repr(CREATIVE_STOP_SEQUENCES[0])}")

# 10b. Sentinel stripping in postprocess
from prometheus_novel.stages.pipeline import _postprocess_scene
text_with_sentinel = "I walked into the room.\n<END_PROSE>"
result = _postprocess_scene(text_with_sentinel)
test("Sentinel stripped from output", "<END_PROSE>" not in result and "walked" in result, repr(result))

# Case-insensitive
text_with_sentinel2 = "She smiled at me.\n<end_prose>\n"
result2 = _postprocess_scene(text_with_sentinel2)
test("Sentinel stripped case-insensitive", "<end_prose>" not in result2 and "smiled" in result2, repr(result2))

# 10c. Critic gate scoring function
from prometheus_novel.stages.pipeline import PipelineOrchestrator
# We can't easily call the inner _score_output directly, but we can verify
# the method _generate_prose exists and has the scoring logic
import inspect
source = inspect.getsource(PipelineOrchestrator._generate_prose)
test("Scoring function in _generate_prose", "_score_output" in source, "")
test("Hard penalties in scoring", "-100" in source or "100" in source, "")
test("Soft penalties in scoring", "too_short" in source and "pov_drift" in source, "")

# 10d. Post-truncation salvage guardrail
# Test via _clean_scene_content — after stripping, if too short, should warn but not crash
short_text = "Hello."
result = _clean_scene_content(short_text)
test("Short text survives cleanup", result is not None, repr(result))

# 10e. Suffix/prefix overlap in dedup
from prometheus_novel.stages.pipeline import _detect_duplicate_content
# Text with duplicated ending (must be 25+ words for overlap detection)
ending = ("The rain hammered down on the cobblestones as she walked away into the night "
          "leaving me standing alone under the flickering streetlight with nothing but the cold "
          "wind and the echo of her footsteps fading into the distant darkness ahead")
text_with_overlap = f"I stood at the corner watching the sunset. {ending} Then I went home. And I wondered about life and meaning and purpose. {ending}"
result = _detect_duplicate_content(text_with_overlap)
test("Suffix/prefix overlap: duplicate ending removed",
     len(result) < len(text_with_overlap), f"len {len(result)} vs {len(text_with_overlap)}")

# 10f. Quote masking for POV enforcement
# "He said" inside dialogue should NOT be converted when protag is male
text = 'I replied, "He said he would come tomorrow." He walked away.'
result = _enforce_first_person_pov(text, "Ethan", "male")
# "He said" inside quotes should stay, "He walked" outside should convert to "I walked"
test("Quote-masked: 'He said' in quotes stays",
     '"He said' in result or '"he said' in result.lower(), repr(result))
test("Quote-masked: 'He walked' outside converts to 'I walked'",
     "I walked" in result, repr(result))

# 10g. Anchor-based emotional summary protection
# Sentence with concrete anchor should survive summary stripping
text = "I walked home.\n\nThe cold bit through my jacket. Something about this moment felt different as the rain fell on the cracked pavement."
result = _strip_emotional_summaries(text)
test("Anchor protection: sentence with 'rain' + 'pavement' kept",
     "rain" in result and "pavement" in result, repr(result))

# Pure summary without anchors should be stripped
text2 = "I walked home.\n\nSomething about this moment felt different and meaningful."
result2 = _strip_emotional_summaries(text2)
test("No anchor: 'something about this moment' stripped",
     "Something about this moment" not in result2, repr(result2))

# 10h. Context hashing (verify the code runs without error)
orch4 = MockOrchestrator()
orch4.state.scenes = [
    {"chapter": 1, "scene_number": 1, "content": "Some content here.", "location": "Park"}
]
orch4.state.config = {
    "genre": "romance",
    "writing_style": "literary prose",
    "tone": "dark and moody"
}
orch4._build_scene_context = PipelineOrchestrator._build_scene_context.__get__(orch4)
orch4._build_story_state = PipelineOrchestrator._build_story_state.__get__(orch4)
orch4._get_previous_scenes_context = PipelineOrchestrator._get_previous_scenes_context.__get__(orch4)
orch4._validate_context_schema = PipelineOrchestrator._validate_context_schema.__get__(orch4)
orch4._check_alignment = PipelineOrchestrator._check_alignment.__get__(orch4)
try:
    ctx = orch4._build_scene_context(0, include_story_state=False, include_previous=0)
    test("Context hashing: builds without error", isinstance(ctx, str) and len(ctx) > 0, repr(ctx[:80]))
except Exception as e:
    test("Context hashing: builds without error", False, str(e))

# 10i. Pre-export validation: actionable reports
from prometheus_novel.export.scene_validator import validate_scene, validate_project_scenes, format_validation_report
issues = validate_scene(
    "Certainly! Here is the revised scene with more detail. " + "x " * 200,
    {"characters": {"protagonist": "Ethan"}},
    scene_id="Ch1Sc1",
    scene_index=0
)
test("Validator: scene_index in issue", issues[0].get("scene_index") == 0, repr(issues[0]))
test("Validator: pattern_name in issue", "pattern_name" in issues[0], repr(issues[0]))
test("Validator: pattern_name is 'certainly_preamble'", issues[0]["pattern_name"] == "certainly_preamble", repr(issues[0]))

# Format report
report = format_validation_report(issues)
test("Report: contains scene id", "Ch1Sc1" in report, repr(report[:200]))
test("Report: contains index", "index 0" in report, repr(report[:200]))
test("Report: contains pattern name", "certainly_preamble" in report, repr(report[:200]))

# Word count check
short_issues = validate_scene(
    "Too short. " * 20,  # ~40 words
    {"characters": {"protagonist": "Ethan"}},
    scene_id="Ch1Sc2",
    scene_index=1
)
short_codes = [i["code"] for i in short_issues]
test("Validator: SHORT_SCENE for <100 words", "SHORT_SCENE" in short_codes, repr(short_codes))

# Full project validation returns summary
proj_result = validate_project_scenes(
    [{"chapter": 1, "scene_number": 1, "content": "Certainly! Here is the revised scene. " + "x " * 200}],
    {"characters": {"protagonist": "Ethan"}}
)
test("Project validation: has summary key", "summary" in proj_result, repr(list(proj_result.keys())))
test("Project validation: summary is formatted string",
     isinstance(proj_result["summary"], str) and "error" in proj_result["summary"].lower(),
     repr(proj_result["summary"][:100]))

# 10j. Final DE-AI paragraph-based protection
# Verify the source uses paragraph splitting instead of word splitting for chapter ends
source_deai = inspect.getsource(PipelineOrchestrator._stage_final_deai)
test("DE-AI: uses paragraph split", "split('\\n\\n')" in source_deai, "")
test("DE-AI: HEAD_PARAS defined", "HEAD_PARAS" in source_deai, "")
test("DE-AI: TAIL_PARAS defined", "TAIL_PARAS" in source_deai, "")
test("DE-AI: no HEAD_WORDS (old approach removed)", "HEAD_WORDS" not in source_deai, "")


# ═══════════════════════════════════════════════════════════════
# 11. BATCH 3: DEFENSE ARCHITECTURE IMPROVEMENTS
# ═══════════════════════════════════════════════════════════════
print("\n=== 11. Batch 3: Defense Architecture Improvements ===")
from prometheus_novel.stages.pipeline import FORMAT_CONTRACT, PipelineOrchestrator

# 11a. Nonce sentinel per run
print("  -- 11a. Nonce sentinel --")
orch5 = object.__new__(PipelineOrchestrator)
orch5.project_path = Path(".")
orch5.llm_client = None
orch5.llm_clients = {}
orch5.state = None
orch5.callbacks = {}
# Run __init__ nonce generation
PipelineOrchestrator.__init__(orch5, Path("."))
test("Nonce: _run_nonce exists and is 8 hex chars",
     hasattr(orch5, "_run_nonce") and len(orch5._run_nonce) == 8 and all(c in "0123456789abcdef" for c in orch5._run_nonce),
     repr(getattr(orch5, "_run_nonce", None)))
test("Nonce: _format_contract contains nonce",
     orch5._run_nonce in orch5._format_contract,
     repr(orch5._format_contract[-80:]))
test("Nonce: _stop_sequences first element has nonce",
     orch5._run_nonce in orch5._stop_sequences[0],
     repr(orch5._stop_sequences[0]))
test("Nonce: static FORMAT_CONTRACT unchanged (no nonce)",
     "<END_PROSE>" in FORMAT_CONTRACT and "_" not in FORMAT_CONTRACT.split("<END_PROSE>")[1][:5],
     repr(FORMAT_CONTRACT[-80:]))

# 11b. Nonce sentinel stripping in postprocessor
print("  -- 11b. Nonce sentinel stripping --")
from prometheus_novel.stages.pipeline import _postprocess_scene
# Static variant
result_static = _postprocess_scene("The rain fell softly.\n<END_PROSE>")
test("Strip static sentinel", "END_PROSE" not in result_static, repr(result_static))
# Nonce variant
result_nonce = _postprocess_scene("The rain fell softly.\n<END_PROSE_a3f1b2c9>")
test("Strip nonce sentinel", "END_PROSE" not in result_nonce, repr(result_nonce))
# Mixed case
result_mixed = _postprocess_scene("The rain fell softly.\n<end_prose_beef1234>")
test("Strip nonce sentinel case-insensitive", "end_prose" not in result_mixed.lower(), repr(result_mixed))

# 11c. Assistant-anchor guard for fuzzy preamble
print("  -- 11c. Assistant-anchor guard --")
source_critic = inspect.getsource(PipelineOrchestrator._validate_scene_output)
test("Anchor guard: _ASSISTANT_ANCHORS referenced",
     "_ASSISTANT_ANCHORS" in source_critic or "has_anchor" in source_critic,
     "")
# Check that the anchor set is defined in the method
test("Anchor set defined in critic gate",
     "_ASSISTANT_ANCHORS" in source_critic and "revised" in source_critic,
     "")

# 11d. Active salvage guardrail
print("  -- 11d. Active salvage guardrail --")
from prometheus_novel.stages.pipeline import _clean_scene_content
# When cleanup strips too aggressively and original was much longer
long_original = "Long prose paragraph one. " * 20 + "Certainly! Here is the revised scene. " + "Another paragraph of prose. " * 3
cleaned = _clean_scene_content(long_original)
# The cleanup should handle the meta-text but preserve enough content
# If salvage kicks in, it restores original when cleanup strips to <50 words and original was 3x longer
test("Salvage: cleaned result has content (not empty)",
     len(cleaned.split()) > 10,
     f"only {len(cleaned.split())} words")

# 11e. Prompt injection detection in context validation
print("  -- 11e. Prompt injection detection --")
source_schema = inspect.getsource(PipelineOrchestrator._validate_context_schema)
test("Schema validation: prompt injection patterns present",
     "ignore" in source_schema.lower() and "injection" in source_schema.lower(),
     "")
test("Schema validation: role injection pattern",
     "role injection" in source_schema.lower() or "act as" in source_schema.lower(),
     "")
test("Schema validation: system override pattern",
     "system override" in source_schema.lower() or "system.*override" in source_schema.lower(),
     "")

# 11f. Freshness score in quality audit
print("  -- 11f. Freshness score --")
source_audit = inspect.getsource(PipelineOrchestrator._stage_quality_audit)
test("Quality audit: bigram overlap check exists",
     "bigram" in source_audit.lower() or "scene_bigrams" in source_audit,
     "")
test("Quality audit: stale threshold (0.40)",
     "0.40" in source_audit or "0.4" in source_audit,
     "")

# 11g. Forbidden-marker explosion check in transaction safety
print("  -- 11g. Forbidden-marker explosion --")
source_run = inspect.getsource(PipelineOrchestrator._run_stage)
test("Transaction safety: meta_markers pattern",
     "meta_markers" in source_run or "polluted" in source_run,
     "")
test("Transaction safety: 40% threshold",
     "0.4" in source_run,
     "")

# 11h. Config-driven surgical replacements
print("  -- 11h. Config-driven surgical replacements --")
import yaml as yaml_test
yaml_path = Path(__file__).parent / "prometheus_novel" / "configs" / "surgical_replacements.yaml"
test("Surgical YAML: file exists", yaml_path.exists(), str(yaml_path))
if yaml_path.exists():
    with open(yaml_path, "r") as f:
        yaml_data = yaml_test.safe_load(f)
    test("Surgical YAML: has ai_tell_phrases",
         "ai_tell_phrases" in yaml_data,
         repr(list(yaml_data.keys())))
    test("Surgical YAML: has hollow_intensifiers",
         "hollow_intensifiers" in yaml_data,
         repr(list(yaml_data.keys())))
    test("Surgical YAML: has stock_metaphors",
         "stock_metaphors" in yaml_data,
         repr(list(yaml_data.keys())))
    test("Surgical YAML: has emotional_summarization",
         "emotional_summarization" in yaml_data,
         repr(list(yaml_data.keys())))

# Test the loader method
orch6 = object.__new__(PipelineOrchestrator)
PipelineOrchestrator.__init__(orch6, Path("."))
orch6._load_surgical_replacements = PipelineOrchestrator._load_surgical_replacements.__get__(orch6)
replacements = orch6._load_surgical_replacements()
test("Surgical loader: returns dict",
     isinstance(replacements, dict) and len(replacements) > 20,
     f"got {type(replacements).__name__} with {len(replacements)} entries")
test("Surgical loader: contains known pattern",
     "I found myself" in replacements,
     repr(list(replacements.keys())[:5]))

# 11i. Feedback loop method exists
print("  -- 11i. Feedback loop --")
test("Feedback loop: _validation_feedback_loop method exists",
     hasattr(PipelineOrchestrator, "_validation_feedback_loop"),
     "")
source_feedback = inspect.getsource(PipelineOrchestrator._validation_feedback_loop)
test("Feedback loop: imports scene_validator",
     "scene_validator" in source_feedback or "validate_project_scenes" in source_feedback,
     "")
test("Feedback loop: MAX_REGEN limit",
     "MAX_REGEN" in source_feedback,
     "")
test("Feedback loop: uses _postprocess_scene",
     "_postprocess_scene" in source_feedback,
     "")

# 11j. Cross-run metrics persistence
print("  -- 11j. Cross-run metrics --")
test("Metrics persistence: _persist_artifact_metrics exists",
     hasattr(PipelineOrchestrator, "_persist_artifact_metrics"),
     "")
test("Metrics delta: _compute_metrics_delta exists",
     hasattr(PipelineOrchestrator, "_compute_metrics_delta"),
     "")
source_persist = inspect.getsource(PipelineOrchestrator._persist_artifact_metrics)
test("Metrics persistence: writes JSONL",
     "jsonl" in source_persist.lower() or "artifact_metrics_history" in source_persist,
     "")
source_delta = inspect.getsource(PipelineOrchestrator._compute_metrics_delta)
test("Metrics delta: computes direction (improved/regressed)",
     "improved" in source_delta and "regressed" in source_delta,
     "")

# 11k. Final DE-AI uses _load_surgical_replacements
print("  -- 11k. DE-AI uses YAML loader --")
source_deai2 = inspect.getsource(PipelineOrchestrator._stage_final_deai)
test("DE-AI: calls _load_surgical_replacements",
     "_load_surgical_replacements" in source_deai2,
     "")
test("DE-AI: no inline hardcoded dict (old approach removed)",
     "# AI tell phrases" not in source_deai2,
     "old hardcoded dict still present")

# 11l. Output validation hooks metrics persistence + feedback
print("  -- 11l. Output validation integration --")
source_outval = inspect.getsource(PipelineOrchestrator._stage_output_validation)
test("Output validation: calls _persist_artifact_metrics",
     "_persist_artifact_metrics" in source_outval,
     "")
test("Output validation: calls _compute_metrics_delta",
     "_compute_metrics_delta" in source_outval,
     "")
test("Output validation: calls _validation_feedback_loop",
     "_validation_feedback_loop" in source_outval,
     "")


# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print(f"RESULTS: {passed} passed, {failed} failed out of {passed+failed}")
if failed == 0:
    print("ALL TESTS PASSED!")
else:
    print(f"FAILURES: {failed}")
    sys.exit(1)
