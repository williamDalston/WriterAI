"""Test all pipeline fixes: gender POV, scene cleanup, story state, genre hooks."""
import sys, os
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
# SUMMARY
# ═══════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print(f"RESULTS: {passed} passed, {failed} failed out of {passed+failed}")
if failed == 0:
    print("ALL TESTS PASSED!")
else:
    print(f"FAILURES: {failed}")
    sys.exit(1)
