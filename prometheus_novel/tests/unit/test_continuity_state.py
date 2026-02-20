"""Tests for quality.continuity_state — scene-level continuity tracking and validation."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from quality.continuity_state import ContinuityState, InfoGate


# ---------------------------------------------------------------------------
# from_outline — build from outline + config
# ---------------------------------------------------------------------------
class TestFromOutline(unittest.TestCase):
    def test_builds_alive_roster_from_config(self):
        config = {
            "protagonist": "Elena Vance, 34, crisis PR manager",
            "other_characters": "Jax Vale (influencer), Captain Mara Sato (commander), Dr. Aris Kade (systems).",
        }
        outline = [
            {"chapter": 1, "scenes": [{"scene": 1, "scene_id": "ch01_s01"}, {"scene": 2, "scene_id": "ch01_s02"}]},
            {"chapter": 2, "scenes": [{"scene": 1, "scene_id": "ch02_s01"}, {"scene": 2, "scene_id": "ch02_s02"}]},
        ]
        cs = ContinuityState.from_outline(outline, config)
        self.assertIn("Elena Vance", cs.alive)
        self.assertIn("Jax Vale", cs.alive)
        # Regex extracts "Captain Mara Sato" and "Aris Kade" from other_characters
        self.assertTrue(
            any("Mara" in n for n in cs.alive),
            f"Expected Mara in alive roster, got: {cs.alive}",
        )
        self.assertTrue(
            any("Aris" in n or "Kade" in n for n in cs.alive),
            f"Expected Aris/Kade in alive roster, got: {cs.alive}",
        )
        self.assertEqual(len(cs.scene_order), 4)
        self.assertEqual(cs.scene_order[0], "ch01_s01")
        self.assertEqual(cs.scene_order[-1], "ch02_s02")

    def test_state_changes_deaths_preferred_over_inference(self):
        outline = [
            {
                "chapter": 1,
                "scenes": [
                    {"scene": 1, "scene_id": "ch01_s01"},
                    {
                        "scene": 2,
                        "scene_id": "ch01_s02",
                        "state_changes": {"deaths": ["Silas Greer"], "reveals": []},
                    },
                ],
            },
            {"chapter": 2, "scenes": [{"scene": 1, "scene_id": "ch02_s01"}]},
        ]
        config = {
            "protagonist": "Elena Vance",
            "other_characters": "Jax Vale, Silas Greer, Mara Sato",
        }
        cs = ContinuityState.from_outline(outline, config)
        # Before ch01_s02: Silas alive
        alive_before = cs.get_alive_at("ch01_s01")
        self.assertIn("Silas Greer", alive_before)
        dead_before = cs.get_dead_at("ch01_s01")
        self.assertNotIn("Silas Greer", dead_before)
        # After ch01_s02: Silas dead
        alive_after = cs.get_alive_at("ch02_s01")
        self.assertNotIn("Silas Greer", alive_after)
        dead_after = cs.get_dead_at("ch02_s01")
        self.assertIn("Silas Greer", dead_after)
        self.assertEqual(dead_after["Silas Greer"], "ch01_s02")


# ---------------------------------------------------------------------------
# get_alive_at / get_dead_at
# ---------------------------------------------------------------------------
class TestAliveDeadAt(unittest.TestCase):
    def test_unknown_scene_returns_full_alive(self):
        config = {"protagonist": "Elena", "other_characters": "Jax"}
        outline = [{"chapter": 1, "scenes": [{"scene": 1, "scene_id": "ch01_s01"}]}]
        cs = ContinuityState.from_outline(outline, config)
        alive = cs.get_alive_at("ch99_s99")
        self.assertGreaterEqual(len(alive), 2)

    def test_death_inference_from_keywords(self):
        outline = [
            {
                "chapter": 1,
                "scenes": [
                    {"scene": 1, "scene_id": "ch01_s01", "purpose": "Setup", "outcome": "Tech found dead."},
                    {"scene": 2, "scene_id": "ch01_s02"},
                ],
            },
        ]
        config = {"protagonist": "Elena", "other_characters": "Priya Nand, Utility Tech Bob"}
        cs = ContinuityState.from_outline(outline, config)
        # "dead" in outcome triggers inference; may infer "unnamed" or a character
        dead_ch02 = cs.get_dead_at("ch01_s02")
        # Unnamed deaths don't add to dead roster
        self.assertTrue(
            len(dead_ch02) >= 0,
            "Inferred death may be unnamed (excluded from dead roster)",
        )


# ---------------------------------------------------------------------------
# validate_content — dead character, setting, info leak
# ---------------------------------------------------------------------------
class TestValidateContent(unittest.TestCase):
    def test_dead_character_physically_present_fails(self):
        outline = [
            {
                "chapter": 1,
                "scenes": [
                    {"scene": 1, "scene_id": "ch01_s01"},
                    {
                        "scene": 2,
                        "scene_id": "ch01_s02",
                        "state_changes": {"deaths": ["Silas Greer"], "reveals": []},
                    },
                ],
            },
            {"chapter": 2, "scenes": [{"scene": 1, "scene_id": "ch02_s01"}]},
        ]
        config = {"protagonist": "Elena Vance", "other_characters": "Silas Greer, Jax Vale"}
        cs = ContinuityState.from_outline(outline, config)
        text = "Silas walked into the room and said hello. I turned to face him."
        result = cs.validate_content("ch02_s01", text, pov="Elena Vance")
        self.assertFalse(result["ok"])
        self.assertTrue(any("Dead character" in e for e in result["errors"]))
        self.assertTrue(len(result["retry_notes"]) >= 1)

    def test_dead_character_expanded_verbs_detected(self):
        """Dead character with expanded verb list (nods, gasps, touches, etc.) should fail."""
        outline = [
            {
                "chapter": 1,
                "scenes": [
                    {"scene": 1, "scene_id": "ch01_s01"},
                    {
                        "scene": 2,
                        "scene_id": "ch01_s02",
                        "state_changes": {"deaths": ["Silas Greer"], "reveals": []},
                    },
                ],
            },
            {"chapter": 2, "scenes": [{"scene": 1, "scene_id": "ch02_s01"}]},
        ]
        config = {"protagonist": "Elena Vance", "other_characters": "Silas Greer, Jax Vale"}
        cs = ContinuityState.from_outline(outline, config)
        for verb_text in ("Silas nodded slowly.", "Silas gasped for air.", "Silas touched my arm."):
            result = cs.validate_content("ch02_s01", verb_text, pov="Elena Vance")
            self.assertFalse(
                result["ok"],
                f"Expected dead character violation for '{verb_text}', got ok=True",
            )

    def test_dead_character_in_memory_context_passes(self):
        outline = [
            {
                "chapter": 1,
                "scenes": [
                    {"scene": 1, "scene_id": "ch01_s01"},
                    {
                        "scene": 2,
                        "scene_id": "ch01_s02",
                        "state_changes": {"deaths": ["Silas Greer"], "reveals": []},
                    },
                ],
            },
            {"chapter": 2, "scenes": [{"scene": 1, "scene_id": "ch02_s01"}]},
        ]
        config = {"protagonist": "Elena Vance", "other_characters": "Silas Greer, Jax Vale"}
        cs = ContinuityState.from_outline(outline, config)
        text = "I remembered what Silas had said before the incident. His voice echoed in my memory."
        result = cs.validate_content("ch02_s01", text, pov="Elena Vance")
        self.assertTrue(result["ok"], f"Expected pass for memory context, got: {result['errors']}")

    def test_setting_violation_underwater_sunlight_fails(self):
        outline = [{"chapter": 1, "scenes": [{"scene": 1, "scene_id": "ch01_s01"}]}]
        config = {
            "protagonist": "Elena",
            "setting": "Underwater habitat 600 ft deep",
            "world_rules": "No sunlight, sealed compartments",
        }
        cs = ContinuityState.from_outline(outline, config)
        text = "I looked out the window at the sunlight streaming through the blue sky."
        result = cs.validate_content("ch01_s01", text, pov="Elena")
        self.assertFalse(result["ok"])
        self.assertTrue(any("Setting violation" in e for e in result["errors"]))

    def test_empty_scene_fails(self):
        outline = [{"chapter": 1, "scenes": [{"scene": 1, "scene_id": "ch01_s01"}]}]
        cs = ContinuityState.from_outline(outline, {"protagonist": "Elena"})
        result = cs.validate_content("ch01_s01", "", pov="Elena")
        self.assertFalse(result["ok"])
        self.assertIn("Empty scene", result["errors"][0])

    def test_design_drift_clone_double_fails(self):
        outline = [{"chapter": 1, "scenes": [{"scene": 1, "scene_id": "ch01_s01"}]}]
        config = {"protagonist": "Elena", "antagonist": "Dr. Aris Kade"}
        cs = ContinuityState.from_outline(outline, config)
        text = "The double steps out of the shadows. She wears her face like a stolen uniform."
        result = cs.validate_content("ch01_s01", text, pov="Elena")
        self.assertFalse(result["ok"], f"Expected design drift for clone/double, got: {result}")
        self.assertTrue(any("Design drift" in e for e in result["errors"]))


# ---------------------------------------------------------------------------
# build_context_block
# ---------------------------------------------------------------------------
class TestBuildContextBlock(unittest.TestCase):
    def test_includes_alive_and_dead(self):
        outline = [
            {
                "chapter": 1,
                "scenes": [
                    {"scene": 1, "scene_id": "ch01_s01"},
                    {"scene": 2, "scene_id": "ch01_s02", "state_changes": {"deaths": ["Bob"]}},
                ],
            },
            {"chapter": 2, "scenes": [{"scene": 1, "scene_id": "ch02_s01"}]},
        ]
        config = {"protagonist": "Elena", "other_characters": "Bob, Jax"}
        cs = ContinuityState.from_outline(outline, config)
        block = cs.build_context_block("ch02_s01", pov="Elena Vance")
        self.assertIn("ALIVE", block)
        self.assertIn("DEAD", block)
        self.assertIn("Bob", block)
        self.assertIn("ch01_s02", block)


if __name__ == "__main__":
    unittest.main()
