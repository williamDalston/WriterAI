"""AudiobookEngine — generates ACX-compliant audiobook MP3s from pipeline scenes.

Uses Google Cloud Text-to-Speech (Neural2 voices) with multi-voice support
for dual-POV novels. Follows the BookOpsEngine pattern.
"""

import json
import logging
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

_SSML_TAG_RE = re.compile(r'<[^>]+>')

import yaml

from prometheus_novel.audiobook.tts_client import TTSClient
from prometheus_novel.audiobook.ssml import (
    build_chapter_ssml,
    chunk_ssml,
    estimate_characters,
    estimate_cost_usd,
    OPENING_CREDITS_SSML,
    CLOSING_CREDITS_SSML,
)
from prometheus_novel.audiobook.audio_post import (
    concatenate_chunks,
    normalize_to_acx,
    validate_acx_compliance,
    add_room_tone,
    export_chapter_mp3,
    sanitize_filename,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# AudiobookEngine
# ---------------------------------------------------------------------------

@dataclass
class AudiobookEngine:
    """Generates ACX-compliant audiobook MP3s from pipeline scenes."""

    project_path: Path
    config: Dict[str, Any]
    scenes: List[Dict[str, Any]]
    audiobook_config: Dict[str, Any]
    tts_client: Optional[TTSClient] = None
    output_dir: Optional[Path] = None

    # Progress tracking
    _generated_files: List[str] = field(default_factory=list)
    _skipped_files: List[str] = field(default_factory=list)
    _errors: List[str] = field(default_factory=list)
    _total_chars: int = 0

    @classmethod
    def from_config_path(cls, config_path: Path) -> "AudiobookEngine":
        """Factory: load config + scenes, validate prerequisites.

        Raises:
            FileNotFoundError: config or pipeline_state.json missing.
            ValueError: No scenes with content found.
            RuntimeError: FFmpeg not available.
        """
        config_path = Path(config_path)
        project_path = config_path.parent

        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        # Load scenes from pipeline_state.json
        state_file = project_path / "pipeline_state.json"
        if not state_file.exists():
            raise FileNotFoundError(
                f"pipeline_state.json not found at {state_file}. "
                "Run the generation pipeline first (writerai generate)."
            )

        try:
            with open(state_file, encoding="utf-8") as f:
                state_data = json.load(f)
        except (json.JSONDecodeError, Exception) as e:
            raise ValueError(f"Could not parse pipeline_state.json: {e}")

        raw_scenes = state_data.get("scenes", [])
        scenes = [
            s for s in raw_scenes
            if isinstance(s, dict) and s.get("content")
        ]
        if not scenes:
            raise ValueError(
                "No scenes with content found in pipeline_state.json. "
                "Ensure the pipeline has completed scene_drafting."
            )

        # Extract audiobook config with defaults
        ab_config = config.get("audiobook", {}) or {}
        ab_config.setdefault("voice_default", "en-US-Neural2-D")
        ab_config.setdefault("voice_map", {})
        ab_config.setdefault("speaking_rate", 0.95)
        ab_config.setdefault("pitch", 0)
        ab_config.setdefault("narrator_credit", "AI Narrator")

        # Validate FFmpeg
        _check_ffmpeg()

        output_dir = project_path / "audiobook"

        # Initialize TTS client
        tts_client = TTSClient.create()

        engine = cls(
            project_path=project_path,
            config=config,
            scenes=scenes,
            audiobook_config=ab_config,
            tts_client=tts_client,
            output_dir=output_dir,
        )

        logger.info(
            f"AudiobookEngine initialized: {len(scenes)} scenes, "
            f"voice={ab_config['voice_default']}, output={output_dir}"
        )
        return engine

    # ------------------------------------------------------------------
    # Voice resolution (multi-POV)
    # ------------------------------------------------------------------

    def _resolve_voice(self, scene: Dict[str, Any]) -> str:
        """Resolve TTS voice for a scene based on POV character.

        Priority:
        1. voice_map match on pov_character (case-insensitive first-name)
        2. voice_default
        """
        voice_map = self.audiobook_config.get("voice_map", {})
        pov = scene.get("pov_character", scene.get("pov", ""))

        if pov and voice_map:
            # Exact match
            if pov in voice_map:
                return voice_map[pov]
            # Case-insensitive first-name match
            pov_lower = pov.strip().split()[0].lower() if pov.strip() else ""
            for char_name, voice_id in voice_map.items():
                char_first = char_name.strip().split()[0].lower()
                if char_first == pov_lower:
                    return voice_id

        return self.audiobook_config["voice_default"]

    # ------------------------------------------------------------------
    # Chapter grouping
    # ------------------------------------------------------------------

    def _group_scenes_by_chapter(self) -> Dict[int, List[Dict[str, Any]]]:
        """Group scenes by chapter number, sorted."""
        chapters: Dict[int, List[Dict]] = {}
        for scene in self.scenes:
            if not isinstance(scene, dict):
                continue
            ch = scene.get("chapter", 1)
            chapters.setdefault(ch, []).append(scene)
        return dict(sorted(chapters.items()))

    # ------------------------------------------------------------------
    # Chapter audio generation
    # ------------------------------------------------------------------

    async def _generate_chapter_audio(
        self,
        chapter_num: int,
        scenes: List[Dict[str, Any]],
    ) -> Path:
        """Generate a single chapter MP3 file.

        Handles multi-voice chapters by processing scene-by-scene
        when different POV characters use different voices.
        """
        logger.info(f"  Generating Chapter {chapter_num} ({len(scenes)} scenes)...")

        # Check if chapter has mixed voices
        voices_in_chapter = set(self._resolve_voice(s) for s in scenes)
        is_multi_voice = len(voices_in_chapter) > 1

        all_audio_chunks: List[bytes] = []

        if is_multi_voice:
            # Process scene by scene to switch voices
            for i, scene in enumerate(scenes):
                voice = self._resolve_voice(scene)
                scene_ssml = build_chapter_ssml(
                    chapter_num if i == 0 else None,  # Header only on first scene
                    [scene],
                )
                chunks = chunk_ssml(scene_ssml)
                for chunk in chunks:
                    audio_bytes = await self.tts_client.synthesize(
                        ssml=chunk,
                        voice_name=voice,
                        speaking_rate=self.audiobook_config["speaking_rate"],
                        pitch=self.audiobook_config["pitch"],
                    )
                    all_audio_chunks.append(audio_bytes)
                    self._total_chars += len(_SSML_TAG_RE.sub('', chunk))
        else:
            # Single voice — process entire chapter at once
            voice = self._resolve_voice(scenes[0])
            chapter_ssml = build_chapter_ssml(chapter_num, scenes)
            chunks = chunk_ssml(chapter_ssml)
            for chunk in chunks:
                audio_bytes = await self.tts_client.synthesize(
                    ssml=chunk,
                    voice_name=voice,
                    speaking_rate=self.audiobook_config["speaking_rate"],
                    pitch=self.audiobook_config["pitch"],
                )
                all_audio_chunks.append(audio_bytes)
                self._total_chars += len(_SSML_TAG_RE.sub('', chunk))

        # Concatenate + post-process
        combined = concatenate_chunks(all_audio_chunks)
        combined = add_room_tone(combined)
        combined = normalize_to_acx(combined)

        # Validate
        compliance = validate_acx_compliance(combined)
        if not compliance["compliant"]:
            for issue in compliance["issues"]:
                logger.warning(f"  ACX issue in Ch{chapter_num}: {issue}")

        # Export
        project_name = self.config.get("project_name", "novel")
        filename = sanitize_filename(f"{project_name}_ch{chapter_num:02d}")
        output_path = self.output_dir / f"{filename}.mp3"
        export_chapter_mp3(combined, output_path)

        duration_min = compliance["duration_minutes"]
        logger.info(
            f"  Chapter {chapter_num}: {duration_min:.1f} min, "
            f"RMS={compliance['rms_db']:.1f}dB, "
            f"Peak={compliance['peak_db']:.1f}dB"
        )

        return output_path

    # ------------------------------------------------------------------
    # Credits generation
    # ------------------------------------------------------------------

    async def _generate_credits(self, credits_type: str) -> Path:
        """Generate opening or closing credits MP3.

        Args:
            credits_type: "opening" or "closing"
        """
        title = self.config.get("title", "Untitled")
        author = self.config.get("author", "the author")
        narrator = self.audiobook_config.get("narrator_credit", "the narrator")

        if credits_type == "opening":
            ssml = OPENING_CREDITS_SSML.format(
                title=title, author=author, narrator=narrator,
            )
        else:
            year = datetime.now().year
            ssml = CLOSING_CREDITS_SSML.format(
                title=title, author=author, narrator=narrator, year=year,
            )

        audio_bytes = await self.tts_client.synthesize(
            ssml=ssml,
            voice_name=self.audiobook_config["voice_default"],
            speaking_rate=0.9,  # Slower for credits
        )

        combined = concatenate_chunks([audio_bytes])
        combined = add_room_tone(combined)
        combined = normalize_to_acx(combined)

        project_name = self.config.get("project_name", "novel")
        filename = sanitize_filename(f"{project_name}_{credits_type}_credits")
        output_path = self.output_dir / f"{filename}.mp3"
        export_chapter_mp3(combined, output_path)

        logger.info(f"  {credits_type.title()} credits: {output_path.name}")
        return output_path

    # ------------------------------------------------------------------
    # Cost estimation
    # ------------------------------------------------------------------

    def estimate_cost(self) -> Dict[str, Any]:
        """Calculate total character count and estimated cost."""
        chapters = self._group_scenes_by_chapter()
        raw_chars = estimate_characters(self.scenes)
        ssml_overhead = int(raw_chars * 0.15)  # ~15% SSML markup
        total_with_overhead = raw_chars + ssml_overhead
        cost = estimate_cost_usd(total_with_overhead)

        return {
            "total_characters": raw_chars,
            "ssml_overhead_chars": ssml_overhead,
            "estimated_total_chars": total_with_overhead,
            "estimated_cost_usd": round(cost, 2),
            "rate_per_million": 16.0,
            "chapters": len(chapters),
        }

    # ------------------------------------------------------------------
    # Main orchestration
    # ------------------------------------------------------------------

    async def generate_all(
        self,
        force: bool = False,
        chapter_filter: Optional[List[int]] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Generate all audiobook files.

        Args:
            force: Overwrite existing MP3 files.
            chapter_filter: Only generate specific chapters (None = all).
            dry_run: Only estimate cost, don't synthesize.

        Returns:
            Result dict with generated/skipped/errors lists and cost info.
        """
        # Cost estimation
        cost_info = self.estimate_cost()
        logger.info(
            f"Audiobook estimate: {cost_info['estimated_total_chars']:,} chars, "
            f"${cost_info['estimated_cost_usd']:.2f} "
            f"({cost_info['chapters']} chapters)"
        )

        if dry_run:
            return {
                "generated": [],
                "skipped": [],
                "errors": [],
                "total_chars": cost_info["estimated_total_chars"],
                "estimated_cost_usd": cost_info["estimated_cost_usd"],
                "acx_compliance": {},
                "dry_run": True,
            }

        self.output_dir.mkdir(parents=True, exist_ok=True)

        chapters = self._group_scenes_by_chapter()
        compliance_results: Dict[str, Any] = {}

        # --- Opening credits ---
        project_name = self.config.get("project_name", "novel")
        opening_name = sanitize_filename(f"{project_name}_opening_credits")
        opening_path = self.output_dir / f"{opening_name}.mp3"

        if force or not opening_path.exists():
            try:
                path = await self._generate_credits("opening")
                self._generated_files.append(str(path))
            except Exception as e:
                logger.error(f"Failed to generate opening credits: {e}")
                self._errors.append(f"opening_credits: {e}")
        else:
            self._skipped_files.append(str(opening_path))

        # --- Chapters ---
        for chapter_num, chapter_scenes in chapters.items():
            if chapter_filter and chapter_num not in chapter_filter:
                continue

            filename = sanitize_filename(f"{project_name}_ch{chapter_num:02d}")
            existing = self.output_dir / f"{filename}.mp3"

            if not force and existing.exists():
                logger.info(f"  Skipping Chapter {chapter_num} (exists, use --force)")
                self._skipped_files.append(str(existing))
                continue

            try:
                path = await self._generate_chapter_audio(chapter_num, chapter_scenes)
                self._generated_files.append(str(path))

                # Post-export compliance check
                from pydub import AudioSegment
                audio = AudioSegment.from_mp3(str(path))
                compliance = validate_acx_compliance(audio)
                compliance_results[f"ch{chapter_num:02d}"] = compliance

            except Exception as e:
                logger.error(f"Failed to generate Chapter {chapter_num}: {e}")
                self._errors.append(f"ch{chapter_num:02d}: {e}")

        # --- Closing credits ---
        closing_name = sanitize_filename(f"{project_name}_closing_credits")
        closing_path = self.output_dir / f"{closing_name}.mp3"

        if force or not closing_path.exists():
            try:
                path = await self._generate_credits("closing")
                self._generated_files.append(str(path))
            except Exception as e:
                logger.error(f"Failed to generate closing credits: {e}")
                self._errors.append(f"closing_credits: {e}")
        else:
            self._skipped_files.append(str(closing_path))

        # --- Manifest ---
        self._write_manifest(compliance_results)

        return {
            "generated": list(self._generated_files),
            "skipped": list(self._skipped_files),
            "errors": list(self._errors),
            "total_chars": self._total_chars,
            "estimated_cost_usd": round(estimate_cost_usd(self._total_chars), 2),
            "acx_compliance": compliance_results,
        }

    # ------------------------------------------------------------------
    # Manifest
    # ------------------------------------------------------------------

    def _write_manifest(self, compliance: Dict[str, Any]):
        """Write audiobook_manifest.json to output dir for tracking."""
        manifest = {
            "project": self.config.get("project_name"),
            "title": self.config.get("title"),
            "generated_at": datetime.now().isoformat(),
            "voice_default": self.audiobook_config["voice_default"],
            "voice_map": self.audiobook_config.get("voice_map", {}),
            "speaking_rate": self.audiobook_config["speaking_rate"],
            "files_generated": self._generated_files,
            "files_skipped": self._skipped_files,
            "errors": self._errors,
            "total_characters_used": self._total_chars,
            "estimated_cost_usd": round(estimate_cost_usd(self._total_chars), 2),
            "acx_compliance": compliance,
        }
        manifest_path = self.output_dir / "audiobook_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, default=str)
        logger.info(f"Manifest written: {manifest_path}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def print_summary(self):
        """Print results to console."""
        print(f"\n{'=' * 50}")
        print(f"Audiobook Complete: {self.config.get('title', 'Untitled')}")
        print(f"Output: {self.output_dir}")
        print(f"{'=' * 50}")

        if self._generated_files:
            print(f"\nGenerated ({len(self._generated_files)} files):")
            for f in self._generated_files:
                print(f"  + {Path(f).name}")

        if self._skipped_files:
            print(f"\nSkipped ({len(self._skipped_files)} files):")
            for f in self._skipped_files:
                print(f"  - {Path(f).name}")

        if self._errors:
            print(f"\nErrors ({len(self._errors)}):")
            for err in self._errors:
                print(f"  ! {err}")

        chars = self._total_chars
        cost = estimate_cost_usd(chars)
        print(f"\nCharacters used: {chars:,}")
        print(f"Estimated cost: ${cost:.2f}")
        print()


# ---------------------------------------------------------------------------
# FFmpeg check
# ---------------------------------------------------------------------------

def _check_ffmpeg():
    """Verify FFmpeg is available. Raises RuntimeError if not found."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "FFmpeg not found. PyDub requires FFmpeg for MP3 encoding.\n"
            "Install:\n"
            "  Windows: choco install ffmpeg  (or winget install ffmpeg)\n"
            "  macOS:   brew install ffmpeg\n"
            "  Linux:   sudo apt install ffmpeg\n"
            "  Docs:    https://ffmpeg.org/download.html"
        )
