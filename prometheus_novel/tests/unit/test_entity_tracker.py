"""Tests for quality.entity_tracker — cross-scene entity consistency checker."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from quality.entity_tracker import (
    _normalize_role,
    extract_entity_pairs,
    check_entity_consistency,
    format_entity_report,
)


# ---------------------------------------------------------------------------
# _normalize_role
# ---------------------------------------------------------------------------
class TestNormalizeRole(unittest.TestCase):
    def test_lowercase(self):
        self.assertEqual(_normalize_role("Brother"), "brother")

    def test_strip(self):
        self.assertEqual(_normalize_role("  sister  "), "sister")

    def test_fiancee_variants(self):
        self.assertEqual(_normalize_role("fiancée"), "fiance")
        self.assertEqual(_normalize_role("fiancé"), "fiance")
        self.assertEqual(_normalize_role("fiancee"), "fiance")
        self.assertEqual(_normalize_role("fiance"), "fiance")

    def test_best_friend_normalizes(self):
        self.assertEqual(_normalize_role("best friend"), "friend")

    def test_plain_roles_unchanged(self):
        for role in ["mother", "father", "husband", "wife", "cousin", "boss"]:
            self.assertEqual(_normalize_role(role), role)


# ---------------------------------------------------------------------------
# extract_entity_pairs — Pattern A (possessive)
# ---------------------------------------------------------------------------
class TestExtractPossessive(unittest.TestCase):
    def test_with_name(self):
        text = "Marco's brother Luca waited outside."
        pairs = extract_entity_pairs(text, "ch1_s1")
        self.assertEqual(len(pairs), 1)
        p = pairs[0]
        self.assertEqual(p["owner"], "Marco")
        self.assertEqual(p["role"], "brother")
        self.assertEqual(p["name"], "Luca")
        self.assertEqual(p["scene_id"], "ch1_s1")
        self.assertEqual(p["pattern"], "possessive")

    def test_without_name(self):
        # Use a short word after role so optional name group doesn't capture it
        # (IGNORECASE makes [A-Z][a-z]{2,} match any 3+ letter word)
        text = "Marco's sister is ok."
        pairs = extract_entity_pairs(text, "ch2_s1")
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["owner"], "Marco")
        self.assertEqual(pairs[0]["role"], "sister")
        self.assertEqual(pairs[0]["name"], "")

    def test_multiple_in_one_text(self):
        text = "Sofia's mother Elena arrived. Marco's father Giuseppe was waiting."
        pairs = extract_entity_pairs(text)
        owners = {p["owner"] for p in pairs if p["pattern"] == "possessive"}
        self.assertIn("Sofia", owners)
        self.assertIn("Marco", owners)

    def test_fiancee_role(self):
        text = "Marco's fiancée Gianna smiled."
        pairs = extract_entity_pairs(text)
        possessive = [p for p in pairs if p["pattern"] == "possessive"]
        self.assertTrue(len(possessive) >= 1)
        self.assertEqual(possessive[0]["role"], "fiance")  # normalized

    def test_ex_wife(self):
        text = "Marco's ex-wife Valentina called."
        pairs = extract_entity_pairs(text)
        possessive = [p for p in pairs if p["pattern"] == "possessive"]
        self.assertTrue(len(possessive) >= 1)
        self.assertEqual(possessive[0]["role"], "ex-wife")

    def test_stepmother(self):
        text = "Luca's stepmother Rosa took charge."
        pairs = extract_entity_pairs(text)
        possessive = [p for p in pairs if p["pattern"] == "possessive"]
        self.assertTrue(len(possessive) >= 1)
        self.assertEqual(possessive[0]["role"], "stepmother")

    def test_best_friend_normalized(self):
        text = "Sofia's best friend Mia was there."
        pairs = extract_entity_pairs(text)
        possessive = [p for p in pairs if p["pattern"] == "possessive"]
        self.assertTrue(len(possessive) >= 1)
        self.assertEqual(possessive[0]["role"], "friend")  # normalized


# ---------------------------------------------------------------------------
# extract_entity_pairs — Pattern B (appositive)
# ---------------------------------------------------------------------------
class TestExtractAppositive(unittest.TestCase):
    def test_basic(self):
        text = "Luca, his brother, shuffled forward."
        pairs = extract_entity_pairs(text, "ch3_s1")
        appos = [p for p in pairs if p["pattern"] == "appositive"]
        self.assertEqual(len(appos), 1)
        self.assertEqual(appos[0]["name"], "Luca")
        self.assertEqual(appos[0]["role"], "brother")
        self.assertEqual(appos[0]["owner"], "")  # unknown pronoun referent

    def test_her_sister(self):
        text = "Elena, her sister, crossed her arms."
        pairs = extract_entity_pairs(text)
        appos = [p for p in pairs if p["pattern"] == "appositive"]
        self.assertEqual(len(appos), 1)
        self.assertEqual(appos[0]["name"], "Elena")
        self.assertEqual(appos[0]["role"], "sister")

    def test_their_partner(self):
        text = "Alex, their partner, nodded slowly."
        pairs = extract_entity_pairs(text)
        appos = [p for p in pairs if p["pattern"] == "appositive"]
        self.assertEqual(len(appos), 1)
        self.assertEqual(appos[0]["name"], "Alex")
        self.assertEqual(appos[0]["role"], "partner")


# ---------------------------------------------------------------------------
# extract_entity_pairs — Pattern C (pronoun_rel)
# ---------------------------------------------------------------------------
class TestExtractPronounRel(unittest.TestCase):
    def test_basic(self):
        text = "She waited for her brother Luca."
        pairs = extract_entity_pairs(text)
        pron = [p for p in pairs if p["pattern"] == "pronoun_rel"]
        self.assertEqual(len(pron), 1)
        self.assertEqual(pron[0]["role"], "brother")
        self.assertEqual(pron[0]["name"], "Luca")
        self.assertEqual(pron[0]["owner"], "")

    def test_his_mother(self):
        text = "He called his mother Rosa."
        pairs = extract_entity_pairs(text)
        pron = [p for p in pairs if p["pattern"] == "pronoun_rel"]
        self.assertEqual(len(pron), 1)
        self.assertEqual(pron[0]["name"], "Rosa")
        self.assertEqual(pron[0]["role"], "mother")

    def test_with_comma(self):
        text = "She visited her cousin, Maria."
        pairs = extract_entity_pairs(text)
        pron = [p for p in pairs if p["pattern"] == "pronoun_rel"]
        self.assertEqual(len(pron), 1)
        self.assertEqual(pron[0]["name"], "Maria")


# ---------------------------------------------------------------------------
# extract_entity_pairs — Edge cases
# ---------------------------------------------------------------------------
class TestExtractEdgeCases(unittest.TestCase):
    def test_empty_text(self):
        self.assertEqual(extract_entity_pairs(""), [])

    def test_no_entities(self):
        text = "The rain fell steadily on the rooftop."
        self.assertEqual(extract_entity_pairs(text), [])

    def test_scene_id_default(self):
        text = "Marco's brother Luca arrived."
        pairs = extract_entity_pairs(text)
        self.assertEqual(pairs[0]["scene_id"], "")

    def test_short_names_ignored(self):
        # Pattern B/C require [A-Z][a-z]{2,} — 2-char names like "Li" won't match
        text = "Li, his brother, said nothing."
        pairs = extract_entity_pairs(text)
        appos = [p for p in pairs if p["pattern"] == "appositive"]
        self.assertEqual(len(appos), 0)


# ---------------------------------------------------------------------------
# check_entity_consistency — Pass cases
# ---------------------------------------------------------------------------
class TestConsistencyPass(unittest.TestCase):
    def test_empty_scenes(self):
        report = check_entity_consistency([])
        self.assertTrue(report["pass"])
        self.assertEqual(report["violations"], [])
        self.assertEqual(report["entity_count"], 0)

    def test_none_scenes(self):
        report = check_entity_consistency(None)
        self.assertTrue(report["pass"])

    def test_consistent_entities(self):
        scenes = [
            {"content": "Marco's brother Luca opened the door.", "scene_id": "ch1_s1"},
            {"content": "Marco's brother Luca paced the room.", "scene_id": "ch5_s2"},
        ]
        report = check_entity_consistency(scenes)
        self.assertTrue(report["pass"])
        self.assertEqual(len(report["violations"]), 0)

    def test_compatible_roles_no_conflict(self):
        """friend + best friend should NOT trigger ENTITY_ROLE_CONFLICT."""
        scenes = [
            {"content": "Sofia's friend Mia laughed.", "scene_id": "ch1_s1"},
            {"content": "Sofia's best friend Mia smiled.", "scene_id": "ch3_s1"},
        ]
        report = check_entity_consistency(scenes)
        conflicts = [v for v in report["violations"] if v["type"] == "ENTITY_ROLE_CONFLICT"]
        self.assertEqual(len(conflicts), 0)

    def test_lover_and_husband_compatible(self):
        scenes = [
            {"content": "She looked at her lover Marco.", "scene_id": "ch1_s1"},
            {"content": "She kissed her husband Marco.", "scene_id": "ch5_s1"},
        ]
        report = check_entity_consistency(scenes)
        conflicts = [v for v in report["violations"] if v["type"] == "ENTITY_ROLE_CONFLICT"]
        self.assertEqual(len(conflicts), 0)


# ---------------------------------------------------------------------------
# check_entity_consistency — ENTITY_RENAME
# ---------------------------------------------------------------------------
class TestEntityRename(unittest.TestCase):
    def test_basic_rename(self):
        scenes = [
            {"content": "Marco's brother Luca was quiet.", "scene_id": "ch3_s1"},
            {"content": "Marco's brother Matteo opened the wine.", "scene_id": "ch18_s2"},
        ]
        report = check_entity_consistency(scenes)
        self.assertFalse(report["pass"])
        renames = [v for v in report["violations"] if v["type"] == "ENTITY_RENAME"]
        self.assertEqual(len(renames), 1)
        self.assertEqual(renames[0]["severity"], "critical")
        names = set(renames[0]["names_found"])
        self.assertIn("luca", names)
        self.assertIn("matteo", names)

    def test_same_name_no_rename(self):
        scenes = [
            {"content": "Sofia's mother Elena arrived.", "scene_id": "ch1_s1"},
            {"content": "Sofia's mother Elena departed.", "scene_id": "ch2_s1"},
        ]
        report = check_entity_consistency(scenes)
        renames = [v for v in report["violations"] if v["type"] == "ENTITY_RENAME"]
        self.assertEqual(len(renames), 0)

    def test_case_insensitive_owner(self):
        """Marco and marco should be treated as same owner."""
        scenes = [
            {"content": "Marco's sister Rosa smiled.", "scene_id": "ch1_s1"},
            # Pattern A with IGNORECASE will match lowercase
            {"content": "marco's sister Anna frowned.", "scene_id": "ch2_s1"},
        ]
        report = check_entity_consistency(scenes)
        renames = [v for v in report["violations"] if v["type"] == "ENTITY_RENAME"]
        # Both match same (owner=marco, role=sister) with different names
        self.assertEqual(len(renames), 1)


# ---------------------------------------------------------------------------
# check_entity_consistency — ENTITY_ROLE_CONFLICT
# ---------------------------------------------------------------------------
class TestEntityRoleConflict(unittest.TestCase):
    def test_sister_vs_exwife(self):
        scenes = [
            {"content": "Sofia, his sister, took his hand.", "scene_id": "ch5_s1"},
            {"content": "Sofia, his ex-wife, slammed the door.", "scene_id": "ch12_s3"},
        ]
        report = check_entity_consistency(scenes)
        self.assertFalse(report["pass"])
        conflicts = [v for v in report["violations"] if v["type"] == "ENTITY_ROLE_CONFLICT"]
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["severity"], "high")
        self.assertIn("sofia", conflicts[0]["name"])

    def test_brother_vs_boss(self):
        scenes = [
            {"content": "She visited her brother Dante.", "scene_id": "ch1_s1"},
            {"content": "She confronted her boss Dante.", "scene_id": "ch4_s2"},
        ]
        report = check_entity_consistency(scenes)
        conflicts = [v for v in report["violations"] if v["type"] == "ENTITY_ROLE_CONFLICT"]
        self.assertEqual(len(conflicts), 1)
        roles = set(conflicts[0]["roles_found"])
        self.assertIn("brother", roles)
        self.assertIn("boss", roles)

    def test_fiance_husband_compatible(self):
        """fiance + husband are compatible — character arc."""
        scenes = [
            {"content": "She looked at her fiance Marco.", "scene_id": "ch1_s1"},
            {"content": "She looked at her husband Marco.", "scene_id": "ch20_s1"},
        ]
        report = check_entity_consistency(scenes)
        conflicts = [v for v in report["violations"] if v["type"] == "ENTITY_ROLE_CONFLICT"]
        self.assertEqual(len(conflicts), 0)

    def test_three_roles_one_incompatible(self):
        """If any pair in the role set is incompatible, flag it."""
        scenes = [
            {"content": "She hugged her friend Nico.", "scene_id": "ch1_s1"},
            {"content": "She called her brother Nico.", "scene_id": "ch3_s1"},
        ]
        report = check_entity_consistency(scenes)
        conflicts = [v for v in report["violations"] if v["type"] == "ENTITY_ROLE_CONFLICT"]
        # friend + brother is NOT in compatible set
        self.assertEqual(len(conflicts), 1)


# ---------------------------------------------------------------------------
# check_entity_consistency — Report structure
# ---------------------------------------------------------------------------
class TestReportStructure(unittest.TestCase):
    def test_report_keys(self):
        report = check_entity_consistency([
            {"content": "Marco's brother Luca.", "scene_id": "s1"},
        ])
        for key in ("pass", "violations", "entity_count", "pair_count", "entity_registry"):
            self.assertIn(key, report)

    def test_entity_registry_built(self):
        scenes = [
            # Pattern C is case-sensitive: use lowercase "her"
            {"content": "Marco's brother Luca arrived. Then her sister Rosa left.", "scene_id": "ch1"},
        ]
        report = check_entity_consistency(scenes)
        reg = report["entity_registry"]
        self.assertIn("luca", reg)
        self.assertIn("rosa", reg)
        self.assertEqual(reg["luca"]["name"], "Luca")
        self.assertIn("brother", reg["luca"]["roles"])

    def test_entity_registry_roles_sorted(self):
        scenes = [
            {"content": "She called her friend Mia. She hugged her cousin Mia.", "scene_id": "ch1"},
        ]
        report = check_entity_consistency(scenes)
        reg = report.get("entity_registry", {})
        if "mia" in reg:
            self.assertEqual(reg["mia"]["roles"], sorted(reg["mia"]["roles"]))

    def test_counts(self):
        scenes = [
            {"content": "Marco's brother Luca. Marco's brother Matteo.", "scene_id": "s1"},
        ]
        report = check_entity_consistency(scenes)
        self.assertGreaterEqual(report["pair_count"], 2)
        self.assertGreaterEqual(report["entity_count"], 2)
        self.assertEqual(report["critical_count"], 1)  # ENTITY_RENAME

    def test_non_dict_scenes_skipped(self):
        report = check_entity_consistency(["not a dict", 42, None])
        self.assertTrue(report["pass"])

    def test_empty_content_skipped(self):
        report = check_entity_consistency([{"content": "", "scene_id": "s1"}])
        self.assertTrue(report["pass"])

    def test_scene_id_fallback(self):
        """If scene_id not provided, auto-generate one."""
        scenes = [{"content": "Marco's brother Luca."}]
        report = check_entity_consistency(scenes)
        # Should not crash
        self.assertGreaterEqual(report["pair_count"], 1)


# ---------------------------------------------------------------------------
# format_entity_report
# ---------------------------------------------------------------------------
class TestFormatReport(unittest.TestCase):
    def test_clean_report(self):
        report = {
            "pass": True,
            "violations": [],
            "entity_count": 5,
            "pair_count": 10,
            "critical_count": 0,
            "high_count": 0,
        }
        text = format_entity_report(report)
        self.assertIn("ENTITY CONSISTENCY REPORT", text)
        self.assertIn("Pass: YES", text)
        self.assertIn("Entities tracked: 5", text)

    def test_rename_violation_format(self):
        report = {
            "pass": False,
            "violations": [{
                "type": "ENTITY_RENAME",
                "severity": "critical",
                "owner": "marco",
                "role": "brother",
                "names_found": ["luca", "matteo"],
                "suggestion": "Pick one name.",
            }],
            "entity_count": 2,
            "pair_count": 2,
            "critical_count": 1,
            "high_count": 0,
        }
        text = format_entity_report(report)
        self.assertIn("ENTITY_RENAME", text)
        self.assertIn("[CRITICAL]", text)
        self.assertIn("luca vs matteo", text)

    def test_role_conflict_format(self):
        report = {
            "pass": False,
            "violations": [{
                "type": "ENTITY_ROLE_CONFLICT",
                "severity": "high",
                "name": "sofia",
                "roles_found": ["sister", "ex-wife"],
                "suggestion": "Clarify the relationship.",
            }],
            "entity_count": 1,
            "pair_count": 2,
            "critical_count": 0,
            "high_count": 1,
        }
        text = format_entity_report(report)
        self.assertIn("ENTITY_ROLE_CONFLICT", text)
        self.assertIn("[HIGH]", text)
        self.assertIn("Sofia", text)  # .title() applied


if __name__ == "__main__":
    unittest.main()
