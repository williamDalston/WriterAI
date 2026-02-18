"""Hot phrase suppression pass.

Reads a hot phrases config (auto-generated or manual) and reduces repeated
phrases across a manuscript by replacing excess occurrences with rotating
alternatives.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from quality.ceiling import CeilingTracker

logger = logging.getLogger(__name__)


# Default replacement banks for common AI-heavy phrases.
# These are used when no explicit replacements are provided in config.
_DEFAULT_REPLACEMENTS: Dict[str, List[str]] = {
    "barely above a whisper": [
        "so quiet I almost missed it",
        "in a low voice",
        "under his breath",
        "almost inaudible",
        "half-swallowed",
    ],
    "voice barely above a": [
        "voice so low it was nearly",
        "voice dropping to",
        "voice reduced to",
        "voice thinned to",
        "voice trailing into",
    ],
    "the air between us": [
        "the space between us",
        "the silence between us",
        "the gap separating us",
        "what hung unspoken",
        "the charged stillness",
    ],
    "we need to talk": [
        "there's something I need to say",
        "can we—just, sit for a minute",
        "don't walk away yet",
        "hold on",
        "wait",
    ],
    "take a deep breath": [
        "draw in air slowly",
        "steady myself",
        "fill my lungs",
        "pause to breathe",
        "let the air settle in my chest",
    ],
    "a deep breath": [
        "a slow breath",
        "a measured inhale",
        "a steadying breath",
        "a long exhale",
    ],
    "heart races": [
        "pulse kicks",
        "chest tightens",
        "blood rushes",
        "heart hammers once, hard",
    ],
    "breath catches": [
        "lungs stall",
        "air locks in my throat",
        "I forget to breathe",
        "something catches behind my ribs",
    ],
    "stomach churns": [
        "gut twists",
        "nausea prickles",
        "something sinks in my belly",
        "my insides clench",
    ],
    "i swallow hard": [
        "my throat clicks",
        "I force down the lump",
        "I try to swallow",
        "my mouth goes dry",
    ],
    "swallow hard": [
        "throat tightening",
        "forcing down the knot",
        "pushing past the lump",
        "dry swallow",
    ],
    # Production Run 8 additions: high-frequency phrases from 66k-word generation
    "eyes meet": [
        "gazes caught",
        "looks collided",
        "glances snagged",
        "eyes found each other",
    ],
    "eyes lock": [
        "gazes held",
        "stares tangled",
        "looks caught and held",
        "neither of us blinked",
    ],
    "unspoken understanding": [
        "tacit agreement",
        "wordless recognition",
        "a knowing look",
        "mutual acknowledgment",
        "silent accord",
    ],
    "resolve and determination": [
        "conviction",
        "grit",
        "stubbornness",
        "purpose",
        "certainty",
    ],
}


def load_replacement_banks(*paths: Union[Path, str]) -> Dict[str, List[str]]:
    """Load replacement banks from YAML files (dynamic config, no code changes).

    Merges banks from all provided paths; later paths override earlier for same phrase.
    Format: { banks: { "phrase": ["replacement1", ...], ... } }
    Project override: <project>/phrase_replacement_banks.yaml
    """
    import yaml

    bank: Dict[str, List[str]] = {}
    for p in paths:
        path = Path(p) if not isinstance(p, Path) else p
        if not path.exists():
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            raw = data.get("banks") or data
            if isinstance(raw, dict):
                for k, v in raw.items():
                    if isinstance(v, list) and v:
                        bank[str(k).strip()] = [str(x) for x in v]
        except Exception as e:
            logger.warning("Failed to load replacement banks from %s: %s", path, e)
    return bank


def suppress_phrases(
    scenes: List[str],
    phrase_configs: List[Dict[str, Any]],
    replacement_bank: Optional[Dict[str, List[str]]] = None,
    ceiling: Optional["CeilingTracker"] = None,
) -> Tuple[List[str], Dict[str, Any]]:
    """Suppress repeated phrases across a manuscript.

    Args:
        scenes: List of scene texts in order.
        phrase_configs: List of dicts with at least 'phrase' and 'keep_first'.
            Optional 'replacements' list per phrase.
        replacement_bank: Global replacement bank (phrase -> alternatives).
            Merged with _DEFAULT_REPLACEMENTS.
        ceiling: Optional CeilingTracker for edit limits.

    Returns:
        Tuple of (modified_scenes, report_dict).
    """
    bank = dict(_DEFAULT_REPLACEMENTS)
    if replacement_bank:
        bank.update(replacement_bank)

    report: Dict[str, Dict[str, int]] = {}
    modified = list(scenes)

    # Register scenes with ceiling tracker
    if ceiling:
        for i, text in enumerate(modified):
            ceiling.register_scene(i, len(text.split()))

    for config in phrase_configs:
        if not isinstance(config, dict):
            continue
        phrase = config.get("phrase")
        if not phrase:
            continue
        keep_first = config.get("keep_first", 2)
        replacements = config.get("replacements") or bank.get(phrase, [])

        if not replacements:
            logger.debug("No replacements for '%s', skipping suppression", phrase)
            continue

        escaped = re.escape(phrase)
        pattern = re.compile(escaped, re.IGNORECASE)

        occurrence = 0
        replaced = 0
        replacement_idx = 0

        for scene_idx in range(len(modified)):
            text = modified[scene_idx]
            matches = list(pattern.finditer(text))
            if not matches:
                continue

            new_text = text
            for match in reversed(matches):
                occurrence += 1
                if occurrence <= keep_first:
                    continue

                # Check ceiling before editing
                if ceiling and not ceiling.can_edit(scene_idx, family=phrase):
                    continue

                repl = replacements[replacement_idx % len(replacements)]
                replacement_idx += 1

                original = match.group()
                if repl and original[0].isupper():
                    repl = repl[0].upper() + repl[1:]

                new_text = new_text[: match.start()] + repl + new_text[match.end() :]
                replaced += 1

                if ceiling:
                    ceiling.record_edit(scene_idx, family=phrase)

            modified[scene_idx] = new_text

        report[phrase] = {
            "total_found": occurrence,
            "kept": min(keep_first, occurrence),
            "replaced": replaced,
        }

        if replaced > 0:
            logger.info(
                "Phrase '%s': %d found, %d kept, %d replaced",
                phrase, occurrence, min(keep_first, occurrence), replaced,
            )

    summary = {
        "phrases_processed": len(phrase_configs),
        "total_replacements": sum(r["replaced"] for r in report.values()),
        "per_phrase": report,
    }

    return modified, summary
