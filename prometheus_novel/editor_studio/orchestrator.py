"""Editor Studio orchestrator — runs surgical refinement passes on existing manuscript."""

import json
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from editor_studio.passes import (
    PASS_0_DEFLECTION,
    PASS_1_CONTINUITY,
    PASS_2_DIALOGUE_FRICTION,
    PASS_3_STAKES,
    PASS_4_FINAL_LINE,
    PASS_5_VOICE,
    PASS_6_PREMIUM,
    PASS_RHYTHM,
    PASS_TENSION_COLLAPSE,
    PASS_GESTURE_DIVERSIFY,
    PASS_CAUSALITY,
)

# Overused physical tics to replace (from weakness report / editorial_craft)
OVERUSED_GESTURES = [
    "hand through his hair",
    "hand through her hair",
    "ran his hand through",
    "ran her hand through",
    "close enough that I",
    "the scar on my",
    "scar on my left",
    "his shoulder brushes mine",
    "curl behind my ear",
    "tucked a curl",
]

logger = logging.getLogger("editor_studio")


def _scene_id(scene: Dict) -> str:
    """Derive scene_id from scene dict."""
    ch = int(scene.get("chapter", 0))
    sc = int(scene.get("scene_number") or scene.get("scene", 0))
    return scene.get("scene_id") or f"ch{ch:02d}_s{sc:02d}"


def _map_contract_to_scenes(contracts: List[Dict]) -> Dict[str, List[str]]:
    """Map scene_id -> list of warning strings."""
    out: Dict[str, List[str]] = defaultdict(list)
    for c in contracts or []:
        sid = c.get("scene_id", "")
        for w in c.get("warnings", []):
            if w:
                out[sid].append(w)
    return dict(out)


def _warnings_by_type(warnings: List[str]) -> Dict[str, List[str]]:
    """Group warnings by prefix (CONTINUITY, DIALOGUE_TIDY, etc.)."""
    groups: Dict[str, List[str]] = defaultdict(list)
    for w in warnings:
        prefix = w.split(":")[0] if ":" in w else "OTHER"
        groups[prefix].append(w)
    return dict(groups)


def _parse_tension_collapse(warnings: List[str]) -> Tuple[int, int]:
    """Extract prev_tension and curr_tension from TENSION_COLLAPSE warning.
    Format: 'TENSION_COLLAPSE: scene drops from 7 to 3—consider smoother transition'
    """
    for w in warnings:
        m = re.search(r"drops?\s+from\s+(\d+)\s+to\s+(\d+)", w, re.IGNORECASE)
        if m:
            return int(m.group(1)), int(m.group(2))
    return 7, 3


def _parse_final_line_ending(by_type: Dict[str, List[str]]) -> str:
    """Extract ending type from FINAL_LINE_ATMOSPHERE or FINAL_LINE_SUMMARY."""
    for key in ("FINAL_LINE_ATMOSPHERE", "FINAL_LINE_SUMMARY"):
        if by_type.get(key):
            return key.replace("FINAL_LINE_", "")
    return "ATMOSPHERE"


def _validate_output(original: str, new_content: str, max_length_ratio: float = 1.5) -> bool:
    """Reject outputs that balloon length or are obviously broken."""
    if not new_content or len(new_content.strip()) < 50:
        return False
    orig_words = len(original.split())
    new_words = len(new_content.split())
    if orig_words > 0 and new_words > orig_words * max_length_ratio:
        return False
    return True


def _get_client(config: Dict, stage_key: str = "claude") -> Any:
    """Get LLM client from config. Uses critic_model or api_model."""
    try:
        from prometheus_lib.llm.clients import get_client
        defaults = config.get("model_defaults", {}) or {}
        model = defaults.get("critic_model") or defaults.get("api_model") or "gpt-4o-mini"
        return get_client(model)
    except Exception as e:
        logger.warning("Could not load LLM client: %s", e)
        return None


# Pass-specific temperature: structural fixes low, voice/premium slightly higher
PASS_TEMPERATURES = {
    "deflection": 0.4,
    "continuity": 0.2,
    "dialogue_friction": 0.3,
    "stakes": 0.3,
    "final_line": 0.3,
    "rhythm": 0.2,
    "tension_collapse": 0.3,
    "causality": 0.2,
    "gesture_diversify": 0.3,
    "voice": 0.5,
    "premium": 0.5,
}


async def _run_pass(
    client: Any,
    scene: Dict,
    task_block: str,
    config: Dict,
    *,
    context: str = "",
    temperature: float = 0.4,
) -> Optional[str]:
    """Run one pass on one scene. Returns modified content or None."""
    if not client:
        return None
    content = scene.get("content", "")
    if not content:
        return content

    scene_id = _scene_id(scene)
    pov = scene.get("pov", "protagonist")
    genre = config.get("genre", "")
    characters = config.get("characters", [])
    char_names = []
    if isinstance(characters, list):
        for c in characters[:6]:
            if isinstance(c, dict) and c.get("name"):
                char_names.append(str(c["name"]))
            elif isinstance(c, str):
                char_names.append(c)
    voice_context = ""
    if genre or char_names:
        parts = []
        if genre:
            parts.append(f"Genre: {genre}")
        if char_names:
            parts.append(f"Characters: {', '.join(char_names)}")
        voice_context = "\n".join(parts)

    prompt = f"""You are a surgical revision editor. Your job: make ONE targeted fix. Do not rewrite the whole scene.

Scene ID: {scene_id}
POV: {pov}
{voice_context + chr(10) if voice_context else ""}{task_block}

=== CURRENT SCENE ===
{content}

=== OUTPUT ===
Return ONLY the revised scene text. No commentary. No "Here is the revised scene." Just the prose."""

    if context:
        prompt = f"{context}\n\n{prompt}"

    try:
        response = await client.generate(prompt, max_tokens=4000, temperature=temperature)
        if response and response.content:
            return response.content.strip()
    except Exception as e:
        logger.warning("Pass failed for %s: %s", scene_id, e)
    return None


async def run_editor_studio(
    project_path: Path,
    passes_enabled: Optional[List[str]] = None,
    client: Optional[Any] = None,
    *,
    scenes: Optional[List[Dict]] = None,
    config: Optional[Dict] = None,
    contracts: Optional[List[Dict]] = None,
    overused_phrases: Optional[List[str]] = None,
    characters: Optional[List[Any]] = None,
    genre: Optional[str] = None,
    skip_persist: bool = False,
) -> Dict[str, Any]:
    """Run Editor Studio passes on a completed manuscript.

    Args:
        project_path: Path to project (e.g. data/projects/burning-vows-30k)
        passes_enabled: Which passes to run (default: all)
        client: Optional pre-initialized LLM client
        scenes: Optional in-memory scenes (skip disk load when provided)
        config: Optional config dict
        contracts: Optional quality_contract contracts list
        overused_phrases: Optional manuscript-specific overused phrases for gesture_diversify.
            When provided, replaces OVERUSED_GESTURES (dynamic per-book detection).
        characters: Optional list (from pipeline state) for voice context in prompts.
        genre: Optional genre string (from config) for voice context in prompts.
        skip_persist: If True, do not write back to disk (caller owns state)

    Returns:
        Report dict with per-pass stats and any errors.
    """
    project_path = Path(project_path)
    output_dir = project_path / "output"
    state_file = project_path / "pipeline_state.json"
    contract_file = output_dir / "quality_contract.json"
    config_file = project_path / "config.yaml"

    report: Dict[str, Any] = {
        "passes_run": [],
        "scenes_modified": 0,
        "errors": [],
        "project_path": str(project_path),
    }

    # Load or use provided state
    if scenes is not None:
        state = {"scenes": scenes, "master_outline": [], "project_name": project_path.name}
    else:
        if not state_file.exists():
            report["errors"].append("pipeline_state.json not found — run pipeline first")
            return report
        with open(state_file, encoding="utf-8") as f:
            state = json.load(f)
        scenes = state.get("scenes", [])

    if not scenes:
        report["errors"].append("No scenes")
        return report

    if config is None:
        config = state.get("config", {}) or {}
        if config_file.exists():
            import yaml
            with open(config_file, encoding="utf-8") as f:
                config = yaml.safe_load(f) or config

    # Load quality contract for targeting
    if contracts is not None:
        warnings_by_scene = _map_contract_to_scenes(contracts)
    else:
        warnings_by_scene = {}
        if contract_file.exists():
            with open(contract_file, encoding="utf-8") as f:
                qc = json.load(f)
            warnings_by_scene = _map_contract_to_scenes(qc.get("contracts", []))

    # Resolve client
    llm = client or _get_client(config)
    if not llm:
        report["errors"].append("No LLM client available")
        return report

    # Merge genre/characters for voice context (pipeline may pass from state)
    run_config = dict(config or {})
    if genre is not None:
        run_config["genre"] = genre
    elif "genre" not in run_config and config:
        run_config.setdefault("genre", config.get("genre", ""))
    if characters is not None:
        run_config["characters"] = characters
    elif "characters" not in run_config and config:
        run_config.setdefault("characters", config.get("characters", []))

    # Default: run all passes (deflection first — highest impact)
    all_pass_names = [
        "deflection",
        "continuity",
        "dialogue_friction",
        "stakes",
        "final_line",
        "rhythm",
        "tension_collapse",
        "causality",
        "gesture_diversify",
        "voice",
        "premium",
    ]
    to_run = passes_enabled or all_pass_names

    scenes_list = [s for s in scenes if isinstance(s, dict)]
    modified_count = 0

    # gesture_diversify: use manuscript-mined phrases when provided, else fallback
    gesture_phrases = overused_phrases if overused_phrases else OVERUSED_GESTURES

    for pass_name in to_run:
        if pass_name not in all_pass_names:
            continue
        pass_modified = 0

        # Build list of scene indices to process per pass
        if pass_name == "deflection":
            target_ids = {s for s, w in warnings_by_scene.items() if any("DEFLECTION" in x for x in w)}
        elif pass_name == "continuity":
            target_ids = {s for s, w in warnings_by_scene.items() if any("CONTINUITY" in x for x in w)}
        elif pass_name == "dialogue_friction":
            target_ids = {s for s, w in warnings_by_scene.items() if any("DIALOGUE_TIDY" in x for x in w)}
        elif pass_name == "stakes":
            target_ids = {s for s, w in warnings_by_scene.items() if any("STAKELESS" in x for x in w)}
        elif pass_name == "final_line":
            target_ids = {s for s, w in warnings_by_scene.items() if any("FINAL_LINE" in x for x in w)}
        elif pass_name == "rhythm":
            target_ids = {s for s, w in warnings_by_scene.items() if any("RHYTHM" in x for x in w)}
        elif pass_name == "tension_collapse":
            target_ids = {s for s, w in warnings_by_scene.items() if any("TENSION_COLLAPSE" in x for x in w)}
        elif pass_name == "causality":
            target_ids = {s for s, w in warnings_by_scene.items() if any("CAUSALITY" in x for x in w)}
        elif pass_name == "gesture_diversify":
            # Target scenes containing overused phrases (manuscript-mined or fallback)
            target_indices = {
                i for i, s in enumerate(scenes_list)
                if any(
                    phrase.lower() in (s.get("content") or "").lower()
                    for phrase in gesture_phrases
                )
            }
        elif pass_name == "voice":
            # Broad pass: top 10 scenes by tension
            by_tension = sorted(
                [(i, s) for i, s in enumerate(scenes_list) if s.get("content")],
                key=lambda x: int(x[1].get("tension_level", 0)),
                reverse=True,
            )
            target_indices = {i for i, _ in by_tension[:10]}
        elif pass_name == "premium":
            # Opening (first 500-800 words), final chapter, midpoint — high ROI
            last_ch = max(int(s.get("chapter", 1)) for s in scenes_list) if scenes_list else 1
            target_indices = {0, len(scenes_list) // 2}
            for i, s in enumerate(scenes_list):
                if int(s.get("chapter", 0)) == last_ch:
                    target_indices.add(i)
        else:
            target_ids = set()
            if pass_name != "gesture_diversify":
                target_indices = set()

        # For passes that use scene_id targeting (from quality_contract)
        if pass_name in ("deflection", "continuity", "dialogue_friction", "stakes", "final_line", "rhythm", "tension_collapse", "causality"):
            target_indices = {
                i for i, s in enumerate(scenes_list)
                if _scene_id(s) in target_ids
            }

        if not target_indices and pass_name not in ("voice", "gesture_diversify"):
            logger.info("Pass %s: no targeted scenes", pass_name)
            report["passes_run"].append({"pass": pass_name, "scenes_processed": 0})
            continue

        for idx in sorted(target_indices):
            if idx >= len(scenes_list):
                continue
            scene = scenes_list[idx]
            sid = _scene_id(scene)
            warnings = warnings_by_scene.get(sid, [])
            by_type = _warnings_by_type(warnings)

            if pass_name == "deflection":
                task = PASS_0_DEFLECTION
            elif pass_name == "continuity":
                task = PASS_1_CONTINUITY.format(warnings="\n".join(by_type.get("CONTINUITY", [])))
            elif pass_name == "dialogue_friction":
                task = PASS_2_DIALOGUE_FRICTION
            elif pass_name == "stakes":
                task = PASS_3_STAKES
            elif pass_name == "final_line":
                ending_type = _parse_final_line_ending(by_type)
                task = PASS_4_FINAL_LINE.format(ending_type=ending_type)
            elif pass_name == "voice":
                task = PASS_5_VOICE
            elif pass_name == "rhythm":
                task = PASS_RHYTHM
            elif pass_name == "tension_collapse":
                prev_t, curr_t = _parse_tension_collapse(warnings)
                task = PASS_TENSION_COLLAPSE.format(prev_tension=prev_t, curr_tension=curr_t)
            elif pass_name == "causality":
                task = PASS_CAUSALITY
            elif pass_name == "gesture_diversify":
                content_lower = (scene.get("content") or "").lower()
                found = [p for p in gesture_phrases if p.lower() in content_lower]
                phrase = found[0] if found else (gesture_phrases[0] if gesture_phrases else "hand through his hair")
                count = content_lower.count(phrase.lower())
                task = PASS_GESTURE_DIVERSIFY.format(phrase=phrase, count=count)
            elif pass_name == "premium":
                task = PASS_6_PREMIUM
            else:
                continue

            temp = PASS_TEMPERATURES.get(pass_name, 0.4)
            new_content = await _run_pass(llm, scene, task, run_config, temperature=temp)
            orig_content = scene.get("content", "")
            if (
                new_content
                and new_content != orig_content
                and _validate_output(orig_content, new_content)
            ):
                scene["content"] = new_content
                pass_modified += 1
                modified_count += 1
            elif new_content and not _validate_output(orig_content, new_content):
                logger.debug(
                    "Pass %s rejected output for %s (length/validation)",
                    pass_name, sid,
                )

        report["passes_run"].append({
            "pass": pass_name,
            "scenes_processed": len(target_indices),
            "scenes_modified": pass_modified,
        })
        logger.info("Pass %s: %d modified", pass_name, pass_modified)

    report["scenes_modified"] = modified_count

    # Persist back to pipeline_state and output (unless skip_persist)
    if modified_count > 0 and not skip_persist:
        state["scenes"] = scenes
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        logger.info("Saved %d scene changes to pipeline_state.json", modified_count)

        # Recompile manuscript to .md (match pipeline output format)
        try:
            outline = state.get("master_outline", [])
            ch_titles: Dict[int, str] = {}
            for ch_data in outline or []:
                if isinstance(ch_data, dict):
                    ch_titles[int(ch_data.get("chapter", 0))] = ch_data.get("chapter_title", "")
            total_words = sum(len(s.get("content", "").split()) for s in scenes_list)
            full_text = f"# {config.get('title', project_path.name)}\n\n"
            synopsis = config.get("synopsis") or config.get("high_concept") or state.get("high_concept", "")
            full_text += f"*{synopsis}*\n\n"
            full_text += "---\n\n"
            current_chapter = None
            for scene in scenes_list:
                chapter = int(scene.get("chapter", 1))
                if chapter != current_chapter:
                    ch_title = ch_titles.get(chapter, "")
                    if ch_title:
                        full_text += f"\n\n## Chapter {chapter}: {ch_title}\n\n"
                    else:
                        full_text += f"\n\n## Chapter {chapter}\n\n"
                    current_chapter = chapter
                else:
                    full_text += "\n\n⁂\n\n"
                full_text += scene.get("content", "")
            full_text += "\n\n---\n\n# THE END\n\n"
            full_text += f"*Word Count: {total_words:,}*\n"
            project_name = state.get("project_name", project_path.name)
            md_path = output_dir / f"{project_name}.md"
            md_path.write_text(full_text, encoding="utf-8")
            logger.info("Recompiled manuscript to %s", md_path)
        except Exception as e:
            report["errors"].append(f"Recompile failed: {e}")

    return report


class EditorStudioOrchestrator:
    """Orchestrates Editor Studio passes. Async interface."""

    def __init__(self, project_path: Path, client: Optional[Any] = None):
        self.project_path = Path(project_path)
        self.client = client
        self.report: Dict[str, Any] = {}

    async def run(self, passes_enabled: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run passes and return report."""
        self.report = await run_editor_studio(
            self.project_path,
            passes_enabled=passes_enabled,
            client=self.client,
        )
        return self.report
