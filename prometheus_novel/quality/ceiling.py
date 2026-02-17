"""Ceiling rules — guardrails that prevent quality passes from over-editing.

Each pass checks these limits per-scene. When a ceiling is hit, the pass
stops for that scene, logs a WARNING, and moves on. This prevents the
quality system from sandblasting voice or tone.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict

logger = logging.getLogger(__name__)


@dataclass
class CeilingRules:
    """Configuration for quality pass edit limits."""

    # Max edits in a single scene (across all patterns in one pass)
    max_edits_per_scene: int = 15

    # Max edits per 1,000 words (proportional to scene length)
    max_edits_per_1k_words: float = 8.0

    # Max replacements for a single phrase family per chapter
    max_per_family_per_chapter: int = 5

    # Max % of sentences that can be changed in a single scene
    max_pct_sentences_changed: float = 20.0

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CeilingRules":
        """Create from a dict, ignoring unknown keys."""
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in known})


class CeilingTracker:
    """Tracks edits per scene/chapter and enforces ceiling rules."""

    def __init__(self, rules: CeilingRules):
        self.rules = rules
        self._scene_edits: Dict[int, int] = {}  # scene_idx -> edit count
        self._scene_word_counts: Dict[int, int] = {}
        self._family_chapter_edits: Dict[str, int] = {}  # "family:chapter" -> count
        self._ceiling_hits: Dict[str, int] = {}  # reason -> count
        self._scenes_capped: set = set()

    def register_scene(self, scene_idx: int, word_count: int) -> None:
        """Register a scene's word count for proportional limit calculation."""
        self._scene_word_counts[scene_idx] = word_count
        self._scene_edits.setdefault(scene_idx, 0)

    def can_edit(
        self,
        scene_idx: int,
        family: str = "",
        chapter: int = 0,
    ) -> bool:
        """Check if another edit is allowed for this scene/family/chapter.

        Returns True if under all ceilings, False if any ceiling hit.
        """
        edits = self._scene_edits.get(scene_idx, 0)

        # Check 1: absolute per-scene cap
        if edits >= self.rules.max_edits_per_scene:
            self._record_hit("max_edits_per_scene", scene_idx)
            return False

        # Check 2: per-1k-words cap
        wc = self._scene_word_counts.get(scene_idx, 500)
        limit = max(1, int(self.rules.max_edits_per_1k_words * wc / 1000))
        if edits >= limit:
            self._record_hit("max_edits_per_1k_words", scene_idx)
            return False

        # Check 3: per-family-per-chapter cap
        if family and chapter > 0:
            key = f"{family}:{chapter}"
            fam_edits = self._family_chapter_edits.get(key, 0)
            if fam_edits >= self.rules.max_per_family_per_chapter:
                self._record_hit("max_per_family_per_chapter", scene_idx)
                return False

        return True

    def record_edit(
        self,
        scene_idx: int,
        family: str = "",
        chapter: int = 0,
    ) -> None:
        """Record that an edit was made."""
        self._scene_edits[scene_idx] = self._scene_edits.get(scene_idx, 0) + 1
        if family and chapter > 0:
            key = f"{family}:{chapter}"
            self._family_chapter_edits[key] = self._family_chapter_edits.get(key, 0) + 1

    def _record_hit(self, reason: str, scene_idx: int) -> None:
        """Record a ceiling hit."""
        self._ceiling_hits[reason] = self._ceiling_hits.get(reason, 0) + 1
        if scene_idx not in self._scenes_capped:
            self._scenes_capped.add(scene_idx)
            logger.warning(
                "Ceiling hit: %s on scene %d (edits=%d, words=%d)",
                reason, scene_idx,
                self._scene_edits.get(scene_idx, 0),
                self._scene_word_counts.get(scene_idx, 0),
            )

    def report(self) -> Dict[str, Any]:
        """Return ceiling enforcement summary."""
        return {
            "ceiling_hits": dict(self._ceiling_hits),
            "scenes_capped": len(self._scenes_capped),
            "total_edits_tracked": sum(self._scene_edits.values()),
        }
