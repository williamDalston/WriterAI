"""Continuity state tracker for scene-level content consistency.

Provides two guards:
1. Pre-draft context injection (alive/dead roster, knowledge gates, hard rules)
2. Post-draft content validation (dead character presence, setting violations, info leaks)

Usage:
    cs = ContinuityState.from_outline(outline, config, characters)
    block = cs.build_context_block("ch08_s01", pov="Elena Vance", prev_tail="...")
    result = cs.validate_content("ch08_s01", scene_text, pov="Elena Vance")
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keywords used to infer state_changes from outline purpose/outcome text
# ---------------------------------------------------------------------------
_DEATH_KEYWORDS = [
    r'\bdeath\b', r'\bdead\b', r'\bdies?\b', r'\bkill(?:ed|s)?\b',
    r'\bbody\b', r'\bcorpse\b', r'\bmurder(?:ed)?\b', r'\bvictim\b',
    r'\bno pulse\b', r'\bfound (?:him|her|them) (?:dead|lifeless)\b',
]
_REVEAL_KEYWORDS = [
    r'\breveal\b', r'\bunmask(?:ed)?\b', r'\bconfess(?:es|ed)?\b',
    r'\badmit(?:s|ted)?\b', r'\bexpose[sd]?\b', r'\btruth comes? out\b',
    r'\bdiscover(?:s|ed)?\b.*(?:sabotag|betray|secret|guilty)',
]

# Setting constraint keywords that should never appear in certain settings
_UNDERWATER_BANNED = [
    "sunlight", "sunshine", "blue sky", "clear sky", "open sky",
    "horizon line", "birds overhead", "fresh breeze", "wind in",
    "warm breeze", "cool breeze", "open air",
]


@dataclass
class InfoGate:
    """A fact that should not appear before a specific scene."""
    fact: str
    trigger_phrases: List[str]
    reveal_at: str  # scene_id where this fact becomes known


@dataclass
class ContinuityState:
    """Tracks character state, knowledge, and setting rules across scenes."""

    # Character roster
    alive: Set[str] = field(default_factory=set)
    dead: Dict[str, dict] = field(default_factory=dict)  # name -> {scene_id, cause}

    # Per-scene events parsed from outline
    scene_events: Dict[str, dict] = field(default_factory=dict)

    # Knowledge gating: facts with reveal scenes
    info_gates: List[InfoGate] = field(default_factory=list)

    # Hard setting rules (non-negotiable physical constraints)
    hard_rules: List[str] = field(default_factory=list)

    # Banned keywords per setting constraint
    setting_bans: List[str] = field(default_factory=list)

    # Design fidelity: plot elements forbidden unless in outline (prevents generation drift)
    design_forbidden: List[str] = field(default_factory=list)

    # Ordered scene IDs for comparison
    scene_order: List[str] = field(default_factory=list)

    # Character location tracking (Fix I)
    character_locations: Dict[str, str] = field(default_factory=dict)  # name -> last_known_location
    location_scene_map: Dict[str, str] = field(default_factory=dict)  # name -> scene_id where set

    @classmethod
    def from_outline(
        cls,
        outline: list,
        config: dict,
        characters: list = None,
    ) -> "ContinuityState":
        """Build continuity state from master outline + config."""
        cs = cls()

        # 1. Initialize alive roster from characters + config
        char_names = set()
        for ch in (characters or []):
            if isinstance(ch, dict):
                name = (ch.get("name") or ch.get("full_name") or "").strip()
                if name:
                    char_names.add(name)
        # Also extract from other_characters config string
        other_chars = config.get("other_characters", "")
        if other_chars:
            for match in re.findall(r"([A-Z][a-z]+(?: [A-Z][a-z]+)*)", str(other_chars)):
                char_names.add(match.strip())
        # Add protagonist
        protagonist = config.get("protagonist", "")
        if protagonist:
            prot_match = re.match(r"([A-Z][a-z]+(?: [A-Z][a-z]+)*)", protagonist)
            if prot_match:
                char_names.add(prot_match.group(1))
        cs.alive = char_names.copy()

        # 2. Parse scene order and events from outline
        for ch_entry in outline:
            if not isinstance(ch_entry, dict):
                continue
            ch_num = ch_entry.get("chapter_number", ch_entry.get("chapter", 0))
            for sc in ch_entry.get("scenes", []):
                if not isinstance(sc, dict):
                    continue
                sc_num = sc.get("scene_number", sc.get("scene", 0))
                sid = sc.get("scene_id", f"ch{ch_num:02d}_s{sc_num:02d}")
                cs.scene_order.append(sid)

                # Check for explicit state_changes field (preferred)
                state_changes = sc.get("state_changes", {})
                events = {}

                if state_changes:
                    events["deaths"] = state_changes.get("deaths", [])
                    events["reveals"] = state_changes.get("reveals", [])
                else:
                    # Infer from purpose/outcome text
                    purpose = sc.get("purpose", "").lower()
                    outcome = sc.get("outcome", "").lower()
                    combined = f"{purpose} {outcome}"

                    # Detect deaths
                    for pat in _DEATH_KEYWORDS:
                        if re.search(pat, combined, re.IGNORECASE):
                            events.setdefault("deaths", [])
                            # Don't know WHO dies from keywords alone —
                            # mark as "unnamed" unless specific name found
                            for name in char_names:
                                first = name.split()[0].lower()
                                if first in combined:
                                    events["deaths"].append(name)
                                    break
                            else:
                                events.setdefault("deaths", []).append("unnamed")
                            break

                    # Detect reveals
                    for pat in _REVEAL_KEYWORDS:
                        if re.search(pat, combined, re.IGNORECASE):
                            events.setdefault("reveals", [])
                            events["reveals"].append(combined[:100])
                            break

                cs.scene_events[sid] = events

        # 3. Build info gates from config
        antagonist = config.get("antagonist", "")
        if antagonist:
            # Find the reveal scene for the antagonist
            ant_name = ""
            ant_match = re.match(r"([A-Z][a-z]+(?: [A-Z][a-z]+)*)", antagonist)
            if ant_match:
                ant_name = ant_match.group(1)

            if ant_name:
                reveal_sid = None
                for sid, events in cs.scene_events.items():
                    for reveal in events.get("reveals", []):
                        if ant_name.split()[0].lower() in reveal.lower():
                            reveal_sid = sid
                            break
                    # Also check if scene purpose mentions "reveal antagonist"
                    if reveal_sid:
                        break

                # Search outline directly for reveal scene
                if not reveal_sid:
                    for ch_entry in outline:
                        if not isinstance(ch_entry, dict):
                            continue
                        for sc in ch_entry.get("scenes", []):
                            if not isinstance(sc, dict):
                                continue
                            purpose = (sc.get("purpose") or "").lower()
                            if "reveal" in purpose and "antagonist" in purpose:
                                ch_n = ch_entry.get("chapter_number", ch_entry.get("chapter", 0))
                                sc_n = sc.get("scene_number", sc.get("scene", 0))
                                reveal_sid = sc.get("scene_id", f"ch{ch_n:02d}_s{sc_n:02d}")
                                break
                        if reveal_sid:
                            break

                if reveal_sid and ant_name:
                    first_name = ant_name.split()[0]
                    last_name = ant_name.split()[-1] if len(ant_name.split()) > 1 else ""
                    triggers = [
                        f"{first_name}.*sabotag",
                        f"{first_name}.*disabled",
                        f"{first_name}.*did it",
                        f"{first_name}.*guilty",
                        f"{first_name}.*killer",
                        f"{first_name}.*murderer",
                        f"{first_name} is the",
                        f"{first_name}.*betray",
                    ]
                    if last_name and last_name != first_name:
                        triggers.append(f"{last_name}.*sabotag")
                    cs.info_gates.append(InfoGate(
                        fact=f"{ant_name} is the antagonist/saboteur",
                        trigger_phrases=triggers,
                        reveal_at=reveal_sid,
                    ))
                    logger.info(
                        "Info gate: '%s' gated until %s (%d trigger phrases)",
                        ant_name, reveal_sid, len(triggers),
                    )

        # 4. Build hard setting rules from config
        world_rules = config.get("world_rules", "")
        setting = config.get("setting", "")
        combined_setting = f"{world_rules} {setting}".lower()

        if "underwater" in combined_setting or "deep-sea" in combined_setting or "deep sea" in combined_setting:
            depth_match = re.search(r'(\d+)\s*(?:ft|feet|m|meters)', combined_setting)
            depth_str = f" at {depth_match.group(0)}" if depth_match else ""
            cs.hard_rules.append(f"Setting is UNDERWATER{depth_str}. NO sunlight, NO open sky, NO birds, NO fresh air, NO wind.")
            cs.hard_rules.append("Light sources: emergency amber/red lighting, fluorescent strips, blue-white LEDs, bioluminescence only.")
            cs.setting_bans = list(_UNDERWATER_BANNED)

        if "no fast escape" in combined_setting or "sealed" in combined_setting:
            cs.hard_rules.append("No quick exit. Decompression required. Characters cannot simply leave.")

        if "limited oxygen" in combined_setting or "co₂" in combined_setting or "co2" in combined_setting:
            cs.hard_rules.append("Oxygen is limited. CO₂ buildup is a constant threat. Air tastes stale/metallic.")

        # 5. Design fidelity: forbid plot elements that cause genre drift
        # Built-in: clone/double/doppelgänger unless explicitly in outline
        cs.design_forbidden = [
            r"\b(?:clone|cloned|cloning)\b",
            r"\bdouble\b.*(?:wears?|wearing|copy|printed)\b",
            r"\bdoppelg[aä]nger\b",
            r"\bprinted a copy (?:of|of the)\b",
            r"\b(?:the )?double (?:steps?|raises?|tilts?|smiles?|holds?)\b",
            r"\b(?:same|identical) (?:face|form) (?:emerges?|steps?)\b",
            r"\bwears? (?:her|his) face like (?:a stolen )?uniform\b",
        ]

        # 5b. Genre lock: when true, forbid supernatural/creature elements in thriller/mystery
        genre = str(config.get("genre", "")).lower()
        genre_lock = config.get("genre_lock", False)
        if genre_lock and genre in ("thriller", "mystery", "psychological thriller", "psychological"):
            cs.design_forbidden.extend([
                r"\b(?:creature|monster|entity)\s+(?:with|having|has)\s+(?:milky|pale|white)\s+eyes?\b",
                r"\b(?:bloated|gray-white|grey-white|segmented)\s+(?:hand|hands|body|figure)\b",
                r"\bjoints?\s+.*(?:bending|bent)\s+the\s+wrong\s+way\b",
                r"\b(?:massive|pale and segmented)\s+creature\b",
                r"\bmilky\s+white\s+eye\b",
            ])

        return cs

    def _scene_index(self, scene_id: str) -> int:
        """Get ordinal position of a scene in the story."""
        try:
            return self.scene_order.index(scene_id)
        except ValueError:
            return -1

    def get_alive_at(self, scene_id: str) -> Set[str]:
        """Return set of characters alive at the start of a given scene."""
        alive = self.alive.copy()
        target_idx = self._scene_index(scene_id)
        if target_idx < 0:
            return alive

        # Process deaths from all PRIOR scenes
        for sid in self.scene_order[:target_idx]:
            events = self.scene_events.get(sid, {})
            for name in events.get("deaths", []):
                if name != "unnamed" and name in alive:
                    alive.discard(name)
        return alive

    def get_dead_at(self, scene_id: str) -> Dict[str, str]:
        """Return dict of {name: scene_id} for characters dead before this scene."""
        dead = {}
        target_idx = self._scene_index(scene_id)
        if target_idx < 0:
            return dead

        for sid in self.scene_order[:target_idx]:
            events = self.scene_events.get(sid, {})
            for name in events.get("deaths", []):
                if name != "unnamed":
                    dead[name] = sid
        return dead

    def get_knowledge_at(self, scene_id: str, pov: str) -> Tuple[List[str], List[str]]:
        """Return (knows, does_not_know) lists for a POV character at a given scene."""
        knows = []
        does_not_know = []
        target_idx = self._scene_index(scene_id)

        for gate in self.info_gates:
            reveal_idx = self._scene_index(gate.reveal_at)
            if reveal_idx < 0:
                continue
            if target_idx < reveal_idx:
                does_not_know.append(gate.fact)
            else:
                knows.append(gate.fact)

        return knows, does_not_know

    def build_context_block(
        self,
        scene_id: str,
        pov: str,
        prev_tail: str = "",
        outline_outcome: str = "",
    ) -> str:
        """Build the continuity state block for prompt injection."""
        alive = sorted(self.get_alive_at(scene_id))
        dead = self.get_dead_at(scene_id)
        knows, does_not_know = self.get_knowledge_at(scene_id, pov)

        lines = [
            "=== CONTINUITY STATE (AUTO-GENERATED — OBEY STRICTLY) ===",
            f"Scene: {scene_id}",
            f"POV: {pov}",
            f"Characters ALIVE: {', '.join(alive) if alive else 'None'}",
        ]

        if dead:
            dead_strs = [f"{n} (died in {sid})" for n, sid in dead.items()]
            lines.append(f"Characters DEAD: {', '.join(dead_strs)}")
            lines.append("DEAD characters MUST NOT appear as physically present. "
                         "They may only be referenced in memory, dialogue, or flashback.")
        else:
            lines.append("Characters DEAD: None yet")

        if self.hard_rules:
            lines.append("")
            lines.append("HARD SETTING RULES (non-negotiable physics):")
            for rule in self.hard_rules:
                lines.append(f"  - {rule}")

        if self.design_forbidden:
            lines.append("")
            lines.append("DESIGN FIDELITY (do NOT introduce):")
            lines.append("  - Clones, doubles, or doppelgängers of any character")
            lines.append("  - Characters not in the roster (no new invented NPCs)")
            lines.append("  - Plot twists beyond the outlined antagonist and premise")
            lines.append("  - Supernatural or genre-shifting elements from config.avoid")

        if knows or does_not_know:
            lines.append("")
            if knows:
                lines.append(f"{pov} KNOWS: {'; '.join(knows)}")
            if does_not_know:
                lines.append(f"{pov} does NOT KNOW (do NOT reveal): {'; '.join(does_not_know)}")

        if prev_tail:
            lines.append("")
            lines.append(f"Previous scene ended with: \"{prev_tail}\"")

        if outline_outcome:
            lines.append(f"This scene must achieve: {outline_outcome}")

        return "\n".join(lines)

    def validate_content(
        self,
        scene_id: str,
        text: str,
        pov: str = "",
        character_names: Set[str] = None,
    ) -> dict:
        """Post-draft content validation. Returns {ok, errors, retry_notes}."""
        errors = []
        retry_notes = []

        if not text or not text.strip():
            return {"ok": False, "errors": ["Empty scene"], "retry_notes": ["Write a complete scene."]}

        text_lower = text.lower()

        # 1. Dead character appearing as physically present
        dead = self.get_dead_at(scene_id)
        if dead:
            # Memory/flashback exemption words
            memory_ctx = {"remembered", "memory", "memorial", "photo", "photograph",
                          "thinking about", "thought of", "used to", "once told",
                          "had said", "before the", "back when"}
            for name, died_in in dead.items():
                first_name = name.split()[0]
                if first_name.lower() in text_lower:
                    # Check if ALL mentions are in memory context
                    # Find all mention positions
                    positions = [m.start() for m in re.finditer(
                        re.escape(first_name), text, re.IGNORECASE
                    )]
                    active_mentions = 0
                    for pos in positions:
                        # Check 80 chars before the mention for memory context
                        window = text[max(0, pos - 80):pos + len(first_name) + 80].lower()
                        if not any(ctx in window for ctx in memory_ctx):
                            # Check for active-presence verbs near the mention
                            active_verbs = (
                                r'said|says|walked|walks|stood|stands|looked|looks|turned|turns|'
                                r'stepped|steps|grabbed|grabs|smiled|smiles|laughed|laughs|moved|moves|'
                                r'leaned|leans|sat|sits|nods|nodded|shrugs|shrugged|points|pointed|'
                                r'whispers|whispered|enters|entered|exits|exited|reaches|reached|'
                                r'pushes|pushed|pulls|pulled|holds|held|approaches|approached|'
                                r'follows|followed|speaks|spoke|asks|asked|replies|replied|adds|added|'
                                r'touches|touched|stares|stared|backs|backed|races|raced|stumbles|stumbled|'
                                r'collapses|collapsed|gasps|gasped|growls|growled'
                            )
                            if re.search(
                                rf'{re.escape(first_name.lower())}\s+(?:{active_verbs})',
                                window
                            ):
                                active_mentions += 1
                    if active_mentions >= 1:
                        errors.append(f"Dead character '{name}' (died {died_in}) appears as physically present.")
                        retry_notes.append(
                            f"Remove {name} from active scene. {name} died in {died_in}. "
                            f"They may only appear in memory/dialogue about the past."
                        )

        # 2. Setting violations (banned keywords)
        if self.setting_bans:
            hits = []
            for ban in self.setting_bans:
                if ban.lower() in text_lower:
                    hits.append(ban)
            if hits:
                errors.append(f"Setting violation — impossible references: {', '.join(hits)}")
                rule_summary = "; ".join(self.hard_rules[:2]) if self.hard_rules else "underwater"
                retry_notes.append(
                    f"Remove references to: {', '.join(hits)}. "
                    f"Setting constraint: {rule_summary}. "
                    f"Replace with emergency lighting, condensation, metallic air, pressure effects."
                )

        # 2b. Design fidelity: forbid clone/double/doppelgänger and config.avoid elements
        if self.design_forbidden:
            text_lower = text.lower()
            for pat in self.design_forbidden:
                if re.search(pat, text, re.IGNORECASE):
                    errors.append(
                        "Design drift: Scene introduces plot elements forbidden by design "
                        "(e.g. clone, double, doppelgänger, or config.avoid). "
                        "Stay within the outlined antagonist and premise."
                    )
                    retry_notes.append(
                        "Remove clone/double/doppelgänger or other invented plot elements. "
                        "The antagonist and premise are fixed in config. "
                        "Do not invent duplicate characters, AI body-doubles, or supernatural twists."
                    )
                    break  # One hit is enough

        # 3. Info leak detection (knowledge gating)
        target_idx = self._scene_index(scene_id)
        for gate in self.info_gates:
            reveal_idx = self._scene_index(gate.reveal_at)
            if reveal_idx < 0 or target_idx >= reveal_idx:
                continue  # Already revealed, no gate needed
            for phrase_pat in gate.trigger_phrases:
                if re.search(phrase_pat, text, re.IGNORECASE):
                    errors.append(f"Info leak: '{gate.fact}' referenced before reveal in {gate.reveal_at}")
                    retry_notes.append(
                        f"Remove any implication that {gate.fact}. "
                        f"This is not revealed until {gate.reveal_at}. "
                        f"Keep suspicion ambiguous; do not name or confirm the antagonist."
                    )
                    break  # One hit per gate is enough

        # 4. Completion check (mid-sentence already checked by format validator,
        #    but we add a stronger check here)
        stripped = text.rstrip()
        if stripped and stripped[-1] not in '.!?"\u201d\u2019':
            last_word = stripped.split()[-1] if stripped.split() else ""
            if last_word and not last_word.endswith((".", "!", "?", '"', "\u201d")):
                errors.append("Scene appears incomplete — does not end with terminal punctuation.")
                retry_notes.append(
                    "Ensure the scene ends with a complete sentence. "
                    "End on a concrete action, image, or line of dialogue."
                )

        ok = len(errors) == 0
        if not ok:
            logger.warning(
                "Continuity validation FAILED for %s: %d error(s): %s",
                scene_id, len(errors), "; ".join(errors),
            )

        return {"ok": ok, "errors": errors, "retry_notes": retry_notes}

    # --- Character location tracking (Fix I) ---

    # Transition verbs that explain a character moving between locations
    _TRANSITION_VERBS = re.compile(
        r'\b(?:went|travel(?:ed|s)|moved|walk(?:ed|s)|drove|driv(?:es|ing)|'
        r'flew|head(?:ed|s)|return(?:ed|s)|arriv(?:ed|es)|came|left|'
        r'enter(?:ed|s)|exit(?:ed|s)|ran|rush(?:ed|es)|crept|climb(?:ed|s)|'
        r'descend(?:ed|s)|cross(?:ed|es)|reach(?:ed|es)|step(?:ped|s) (?:into|out|through))\b',
        re.IGNORECASE,
    )

    # Location extraction: "in the [Location]", "at the [Location]", etc.
    _LOCATION_EXTRACT = re.compile(
        r'\b(?:in|at|inside|on|aboard|within)\s+(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})',
    )

    def update_character_location(self, scene_id: str, char_name: str, location: str) -> None:
        """Update a character's last known location."""
        if char_name and location:
            self.character_locations[char_name] = location
            self.location_scene_map[char_name] = scene_id

    def get_character_location(self, char_name: str) -> Optional[Tuple[str, str]]:
        """Get a character's last known location and the scene where it was set."""
        if char_name in self.character_locations:
            return (self.character_locations[char_name], self.location_scene_map.get(char_name, "unknown"))
        return None

    def validate_location_continuity(
        self,
        scene_id: str,
        text: str,
        participants: List[str],
    ) -> dict:
        """Check if characters moved locations without transition language.

        Args:
            scene_id: Current scene ID.
            text: Scene content.
            participants: Character names present in scene.

        Returns:
            dict with 'pass' bool and 'issues' list of warning strings.
        """
        issues = []
        if not text or not participants:
            return {"pass": True, "issues": []}

        # Extract current scene location from first 500 chars
        first_500 = text[:500]
        loc_match = self._LOCATION_EXTRACT.search(first_500)
        current_location = loc_match.group(1).strip() if loc_match else ""

        # Check for transition verbs in first 500 chars
        has_transition = bool(self._TRANSITION_VERBS.search(first_500))

        for char in participants:
            prev = self.get_character_location(char)
            if not prev or not current_location:
                continue
            prev_location, prev_scene = prev
            # Normalize for comparison
            prev_norm = prev_location.lower().strip()
            curr_norm = current_location.lower().strip()
            # Skip if same location or unknown
            if not prev_norm or not curr_norm or prev_norm == curr_norm:
                continue
            # Skip if one is a substring of the other (e.g. "Bridge" vs "The Bridge")
            if prev_norm in curr_norm or curr_norm in prev_norm:
                continue
            # Flag if location changed without transition language
            if not has_transition:
                issues.append(
                    f"{char} was at '{prev_location}' in {prev_scene}, "
                    f"now at '{current_location}' — no transition verb found in opening"
                )

        # Update locations for all participants
        if current_location:
            for char in participants:
                self.update_character_location(scene_id, char, current_location)

        if issues:
            for issue in issues:
                logger.warning("Location continuity: %s", issue)

        return {"pass": len(issues) == 0, "issues": issues}
