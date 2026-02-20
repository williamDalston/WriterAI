"""Reference Bible loader for pipeline-integrated novel generation.

Parses a reference_bible.md into structured sections and provides
extraction methods for injecting into scene drafting, voice pass,
and continuity audit prompts.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ReferenceBible:
    """Loads and parses a reference bible markdown file.

    Provides targeted extraction for pipeline injection points:
    - Character rules (filtered by characters present in a scene)
    - POV rules
    - Scene-specific outline beats
    - Tense rules
    - Repetition blacklist
    - Character DO NOT lists
    - Chapter ending variety tracker
    - Truth file (redacted for continuity audit)
    - Unresolved thread tracking
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self._raw = ""
        self._sections: Dict[str, str] = {}
        self._characters: Dict[str, str] = {}  # lowercase first name -> full entry
        self._character_donots: Dict[str, List[str]] = {}  # lowercase first name -> DO NOT items
        self._scene_outlines: Dict[str, str] = {}  # "ch01_s01" -> outline text
        self._loaded = False

        if self.path.exists():
            self._load()
        else:
            logger.warning("Reference bible not found: %s", self.path)

    def _load(self):
        """Parse the bible into sections and sub-structures."""
        self._raw = self.path.read_text(encoding="utf-8")
        self._sections = self._parse_h2_sections(self._raw)
        self._parse_characters()
        self._parse_scene_outlines()
        self._loaded = True
        logger.info(
            "Reference bible loaded: %d sections, %d characters, %d scene outlines",
            len(self._sections), len(self._characters), len(self._scene_outlines),
        )

    @property
    def loaded(self) -> bool:
        return self._loaded

    # ── Section Parsing ──────────────────────────────────────────────

    @staticmethod
    def _parse_h2_sections(text: str) -> Dict[str, str]:
        """Split markdown by ## headers into {normalized_key: content}."""
        sections = {}
        # Match ## N. TITLE or ## TITLE
        pattern = re.compile(r"^## \d*\.?\s*(.+)$", re.MULTILINE)
        matches = list(pattern.finditer(text))
        for i, m in enumerate(matches):
            key = m.group(1).strip().lower()
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            sections[key] = text[start:end].strip()
        return sections

    def _section(self, *keys: str) -> str:
        """Get a section by trying multiple key variations."""
        for k in keys:
            kl = k.lower().strip()
            for sk, sv in self._sections.items():
                if kl in sk:
                    return sv
        return ""

    # ── Character Parsing ────────────────────────────────────────────

    def _parse_characters(self):
        """Extract individual character entries from the CHARACTER BIBLE section."""
        char_section = self._section("character bible")
        if not char_section:
            return

        # Split on ### headers (character names)
        pattern = re.compile(r"^### (.+)$", re.MULTILINE)
        matches = list(pattern.finditer(char_section))
        for i, m in enumerate(matches):
            name_line = m.group(1).strip()
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(char_section)
            entry = char_section[start:end].strip()

            # Extract first name for matching, stripping titles
            # "Captain Mara Sato" -> "mara", "Dr. Aris Kade" -> "aris"
            _TITLE_PREFIXES = {"captain", "dr.", "dr", "professor", "prof.", "sir", "dame", "lady", "lord"}
            raw_name = name_line.split("(")[0].strip()
            name_parts = raw_name.split()
            while name_parts and name_parts[0].lower().rstrip(".") in {t.rstrip(".") for t in _TITLE_PREFIXES}:
                name_parts.pop(0)
            first_name = name_parts[0].lower() if name_parts else raw_name.split()[0].lower()
            self._characters[first_name] = entry

            # Extract DO NOT list
            donot_match = re.search(
                r"\*\*\w+ DOES NOT:\*\*\s*(.+?)(?:\n\n|\n---|\Z)",
                entry, re.DOTALL,
            )
            if donot_match:
                items = [
                    item.strip().rstrip(".")
                    for item in donot_match.group(1).split(",")
                    if item.strip()
                ]
                self._character_donots[first_name] = items

    # ── Scene Outline Parsing ────────────────────────────────────────

    def _parse_scene_outlines(self):
        """Extract per-scene outlines from the SCENE-BY-SCENE OUTLINE section."""
        outline_section = self._section("scene-by-scene outline", "scene outline")
        if not outline_section:
            return

        # Split by chapter headers (### Chapter N: Title)
        ch_pattern = re.compile(r"^### Chapter (\d+):\s*(.+)$", re.MULTILINE)
        ch_matches = list(ch_pattern.finditer(outline_section))

        for ci, cm in enumerate(ch_matches):
            ch_num = int(cm.group(1))
            ch_start = cm.end()
            ch_end = ch_matches[ci + 1].start() if ci + 1 < len(ch_matches) else len(outline_section)
            ch_text = outline_section[ch_start:ch_end]

            # Split by scene headers (**Scene N — Title**)
            sc_pattern = re.compile(
                r"\*\*Scene (\d+)\s*[—–-]\s*(.+?)\*\*",
                re.MULTILINE,
            )
            sc_matches = list(sc_pattern.finditer(ch_text))

            for si, sm in enumerate(sc_matches):
                sc_num = int(sm.group(1))
                sc_start = sm.end()
                sc_end = sc_matches[si + 1].start() if si + 1 < len(sc_matches) else ch_end - cm.end()
                sc_text = ch_text[sc_start:min(sc_end, len(ch_text))].strip()

                # Remove trailing character location blocks for cleaner injection
                loc_idx = sc_text.find("**Character locations")
                if loc_idx > 0:
                    sc_text = sc_text[:loc_idx].strip()

                key = f"ch{ch_num:02d}_s{sc_num:02d}"
                self._scene_outlines[key] = sc_text

    # ── Extraction Methods (for pipeline injection) ──────────────────

    def get_character_rules(self, character_names: List[str]) -> str:
        """Return character bible entries for characters present in a scene.

        Args:
            character_names: List of character names (first or full names).

        Returns:
            Formatted string with relevant character rules, speech patterns,
            physical vocabulary, and DO NOT constraints.
        """
        if not self._characters:
            return ""

        parts = []
        matched = set()
        for name in character_names:
            first = name.strip().split()[0].lower()
            if first in self._characters and first not in matched:
                matched.add(first)
                entry = self._characters[first]
                # Extract only the most critical sections for prompt injection
                # (full entry is too long — extract speech, physical, DO NOT)
                condensed = self._condense_character_entry(first, entry)
                if condensed:
                    parts.append(condensed)

        if not parts:
            return ""

        return (
            "\n=== REFERENCE BIBLE: CHARACTER RULES (enforce strictly) ===\n"
            + "\n".join(parts) + "\n"
        )

    def _condense_character_entry(self, first_name: str, entry: str) -> str:
        """Extract speech pattern, physical vocabulary, and DO NOT from a character entry."""
        lines = []
        name_title = first_name.capitalize()

        # Speech pattern
        speech = self._extract_field(entry, "Speech pattern")
        if speech:
            lines.append(f"[{name_title}] SPEECH: {speech}")

        # Physical vocabulary
        phys = self._extract_field(entry, "Physical vocabulary")
        if phys:
            lines.append(f"[{name_title}] PHYSICAL: {phys}")

        # DO NOT
        if first_name in self._character_donots:
            donots = self._character_donots[first_name]
            lines.append(f"[{name_title}] DO NOT: {'; '.join(donots)}")

        # Signature habit (Elena only)
        habit = self._extract_field(entry, "Signature habit")
        if habit:
            lines.append(f"[{name_title}] SIGNATURE HABIT: {habit}")

        return "\n".join(lines)

    @staticmethod
    def _extract_field(entry: str, field_name: str) -> str:
        """Extract a **Field:** block from a character entry."""
        pattern = re.compile(
            rf"\*\*{re.escape(field_name)}[^*]*\*\*[:\s]*(.+?)(?=\n\*\*|\n---|\Z)",
            re.DOTALL | re.IGNORECASE,
        )
        m = pattern.search(entry)
        if not m:
            return ""
        text = m.group(1).strip()
        # Collapse to single line for prompt efficiency
        text = re.sub(r"\n- ", " | ", text)
        text = re.sub(r"\n+", " ", text)
        # Trim to ~300 chars if very long
        if len(text) > 400:
            text = text[:397] + "..."
        return text

    def get_pov_rules(self) -> str:
        """Return POV and knowledge rules for prompt injection."""
        pov = self._section("pov and knowledge rules", "pov rules")
        if not pov:
            return ""
        # Strip markdown formatting for cleaner prompt injection
        pov = re.sub(r"\*\*(.+?)\*\*", r"\1", pov)
        return (
            "\n=== REFERENCE BIBLE: POV CONSTRAINTS (enforce strictly) ===\n"
            + pov.strip() + "\n"
        )

    def get_scene_outline(self, chapter: int, scene: int) -> str:
        """Return the bible's outline for a specific scene.

        This tells the LLM exactly what should happen in this scene,
        including key beats, character locations, and ending type.
        """
        key = f"ch{chapter:02d}_s{scene:02d}"
        outline = self._scene_outlines.get(key, "")
        if not outline:
            return ""
        return (
            f"\n=== REFERENCE BIBLE: SCENE BLUEPRINT (ch{chapter} s{scene}) ===\n"
            f"Follow this outline precisely. Hit the KEY BEAT.\n"
            f"{outline.strip()}\n"
        )

    def get_tense_rules(self) -> str:
        """Return tense rules for prompt injection."""
        tense = self._section("tense rules")
        if not tense:
            return ""
        # Extract just the rules, not examples
        rules = []
        for line in tense.split("\n"):
            line = line.strip()
            if line.startswith("**Rule:") or line.startswith("Rule:"):
                rules.append(line.replace("**", ""))
            elif line.startswith("**Primary tense:") or line.startswith("Primary tense:"):
                rules.insert(0, line.replace("**", ""))
        if not rules:
            return ""
        return (
            "\n=== REFERENCE BIBLE: TENSE RULES ===\n"
            + "\n".join(rules) + "\n"
        )

    def get_repetition_blacklist(self) -> str:
        """Return the repetition blacklist for voice pass enforcement.

        Includes hard-capped tics, sensory phrase limits, sentence patterns,
        and chapter ending constraints.
        """
        blacklist = self._section("repetition blacklist")
        if not blacklist:
            return ""
        # Convert markdown tables to bullet lists for prompt injection.
        lines = ["\n=== REFERENCE BIBLE: REPETITION BLACKLIST (hard caps) ==="]
        lines.append("These phrases have STRICT frequency limits across the manuscript.")
        lines.append("If a phrase has already reached its limit, REPLACE it with the suggested alternative.\n")

        # Match all table rows (3 or 4+ columns)
        _SKIP_HEADERS = {"tic", "phrase / pattern", "pattern", "thread", "chapter"}
        for row_match in re.finditer(r"^\|(.+)\|$", blacklist, re.MULTILINE):
            cells = [c.strip() for c in row_match.group(1).split("|")]
            if len(cells) < 3:
                continue
            # Skip header rows and separator rows (----)
            if cells[0].startswith("-") or cells[0].lower() in _SKIP_HEADERS:
                continue
            if len(cells) == 4:
                # 4-column: Tic | Character | Max Uses | Placement Notes
                tic, character, max_uses, _notes = cells
                lines.append(f"- {tic} ({character}): max {max_uses} uses")
            else:
                # 3-column: Phrase | Max Uses | Alternative/Notes
                phrase, max_uses, alt = cells[0], cells[1], cells[2]
                lines.append(f"- {phrase}: max {max_uses} uses. Alternative: {alt}")

        return "\n".join(lines) + "\n"

    def get_character_donots_for_scene(self, character_names: List[str]) -> str:
        """Return DO NOT lists for all characters in a scene.

        Used in voice pass to enforce character-specific physical vocabulary
        boundaries (e.g., Elena does NOT pick at cuticles).
        """
        parts = []
        matched = set()
        for name in character_names:
            first = name.strip().split()[0].lower()
            if first in self._character_donots and first not in matched:
                matched.add(first)
                donots = self._character_donots[first]
                parts.append(f"{first.capitalize()} DOES NOT: {'; '.join(donots)}")

        if not parts:
            return ""
        return (
            "\n=== CHARACTER PHYSICAL VOCABULARY BOUNDARIES ===\n"
            "Each character has EXCLUSIVE physical tics. Do NOT cross-assign:\n"
            + "\n".join(f"- {p}" for p in parts) + "\n"
        )

    def get_ending_type(self, chapter: int) -> str:
        """Return the prescribed ending type for a chapter.

        Used to enforce chapter ending variety.
        """
        tracker = self._section("chapter ending variety tracker", "ending variety")
        if not tracker:
            return ""

        for row_match in re.finditer(
            r"^\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|",
            tracker, re.MULTILINE,
        ):
            ch_num = int(row_match.group(1))
            if ch_num == chapter:
                ending_type = row_match.group(2).strip()
                description = row_match.group(3).strip()
                return (
                    f"\n=== CHAPTER ENDING TYPE (from Reference Bible) ===\n"
                    f"This chapter MUST end with: {ending_type}\n"
                    f"Specifically: {description}\n"
                    f"Do NOT end with a blackout/darkness unless this is one of the 2 permitted blackout chapters.\n"
                )
        return ""

    def get_word_target(self, chapter: int) -> Optional[int]:
        """Return the target word count for a chapter."""
        targets = self._section("word count targets")
        if not targets:
            return None

        for row_match in re.finditer(
            r"^\|\s*(\d+)\s*\|\s*([\d,]+)\s*\|",
            targets, re.MULTILINE,
        ):
            ch_num = int(row_match.group(1))
            if ch_num == chapter:
                return int(row_match.group(2).replace(",", ""))
        return None

    def get_truth_file_redacted(self, chapter: int) -> str:
        """Return truth file content redacted to what Elena can know by this chapter.

        Early chapters: only what's publicly known (Jax scandal, rehab purpose).
        Mid chapters: experiment hints but not full truth.
        Late chapters: full truth (Elena has discovered it).
        """
        truth = self._section("truth file")
        if not truth:
            return ""

        if chapter <= 3:
            # Elena only knows the public story
            return (
                "\n=== TRUTH FILE (what the narrator knows at this point) ===\n"
                "Elena knows: Jax's charity scandal is public. She was hired to manage his rehab.\n"
                "She knows the Aethelgard is a luxury habitat. She senses something is off\n"
                "(Aris watching her, MOTHER's tone) but has no proof.\n"
                "She does NOT know about the experiment, Silas's involvement, or Aris's role.\n"
            )
        elif chapter <= 6:
            # Elena suspects but doesn't have the full picture
            return (
                "\n=== TRUTH FILE (what the narrator knows at this point) ===\n"
                "Elena suspects sabotage. She has found physical evidence (tampered systems,\n"
                "latex residue, off-log equipment use). She suspects Aris but can't prove it.\n"
                "She does NOT know about the behavioral experiment framework, Silas's funding\n"
                "of the research, or MOTHER's reprogramming. She does NOT know about Silas's\n"
                "exit strategy or Mara's eventual deal with Silas.\n"
            )
        elif chapter <= 9:
            # Elena is piecing it together
            return (
                "\n=== TRUTH FILE (what the narrator knows at this point) ===\n"
                "Elena knows someone is running deliberate trials. She's named it aloud:\n"
                "'Someone's running trials. We're the subjects.' She suspects Aris as operator.\n"
                "She doesn't yet know Silas is the architect. She doesn't know about the\n"
                "exit strategies or Mara's pragmatic deal.\n"
            )
        else:
            # Chapters 10-12: Elena knows (nearly) everything
            return (
                "\n=== TRUTH FILE (what the narrator knows at this point) ===\n"
                "Elena knows the full conspiracy: Silas funded it, Aris ran the experiments,\n"
                "MOTHER logged behavioral data, Jax's rehab was the cover story.\n"
                "The tech's death was Aris's miscalculation. The tether snap was real (unplanned).\n"
                "Silas has exit strategies. Mara made a pragmatic deal with Silas.\n"
                + truth.strip() + "\n"
            )

    def get_thread_tracking(self) -> str:
        """Return unresolved thread tracking for continuity audit."""
        threads = self._section("unresolved thread tracking", "thread tracking")
        if not threads:
            return ""
        return (
            "\n=== REFERENCE BIBLE: UNRESOLVED THREADS ===\n"
            "Check that these threads are progressing correctly:\n"
            + threads.strip() + "\n"
        )

    # ── Romance-specific (return empty if section absent) ───────────────────

    def get_touch_progression(self, chapter: int) -> str:
        """Return touch progression rule for a chapter (romance).

        Table format: | Ch | Touch type | Initiator | Meaning |
        """
        section = self._section("touch progression map", "touch progression")
        if not section:
            return ""
        for row_match in re.finditer(
            r"^\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|",
            section, re.MULTILINE,
        ):
            ch_num = int(row_match.group(1))
            if ch_num == chapter:
                touch, initiator, meaning = (
                    row_match.group(2).strip(),
                    row_match.group(3).strip(),
                    row_match.group(4).strip(),
                )
                return (
                    f"\n=== TOUCH PROGRESSION (Ch{chapter}) ===\n"
                    f"Touch type: {touch} | Initiator: {initiator} | Meaning: {meaning}\n"
                    "Physical intimacy must follow emotional trust. Do not skip steps.\n"
                )
        return ""

    def get_emotional_breadcrumbs(self, chapter: int) -> str:
        """Return emotional breadcrumb summary for a chapter (romance).

        Tracks what each lead revealed/withheld.
        """
        section = self._section("emotional breadcrumb tracker", "emotional breadcrumbs")
        if not section:
            return ""
        for row_match in re.finditer(
            r"^\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|",
            section, re.MULTILINE,
        ):
            ch_num = int(row_match.group(1))
            if ch_num == chapter:
                lead_a, lead_b, revealed, withheld = (
                    row_match.group(2).strip(),
                    row_match.group(3).strip(),
                    row_match.group(4).strip(),
                    row_match.group(5).strip(),
                )
                return (
                    f"\n=== EMOTIONAL BREADCRUMBS (Ch{chapter}) ===\n"
                    f"Lead A: {lead_a} | Lead B: {lead_b}\n"
                    f"Revealed: {revealed}\nWithheld: {withheld}\n"
                )
        return ""

    def get_vulnerability_index(self, chapter: int) -> str:
        """Return vulnerability index for a chapter (romance).

        Who has leverage, who retreats, misreads.
        """
        section = self._section("vulnerability index")
        if not section:
            return ""
        for row_match in re.finditer(
            r"^\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|",
            section, re.MULTILINE,
        ):
            ch_num = int(row_match.group(1))
            if ch_num == chapter:
                leverage, retreats, misread = (
                    row_match.group(2).strip(),
                    row_match.group(3).strip(),
                    row_match.group(4).strip(),
                )
                return (
                    f"\n=== VULNERABILITY (Ch{chapter}) ===\n"
                    f"Emotional leverage: {leverage}\n"
                    f"Who retreats: {retreats}\nMisread: {misread}\n"
                )
        return ""

    def get_premise(self) -> str:
        """Return the premise section."""
        return self._section("premise")

    def get_setting_map(self) -> str:
        """Return the setting map."""
        return self._section("setting map")
