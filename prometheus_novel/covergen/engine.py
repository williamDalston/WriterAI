"""CoverGen Engine — generates book cover artwork for Amazon KDP.

Produces both eBook covers (2560x1600 JPEG) and full-wrap print covers
(front + spine + back as a single PDF at 300 DPI).

Workflow:
    1. Load project config + optional pipeline state
    2. Generate art direction prompt via LLM
    3. Generate cover artwork via GPT Image 1
    4. Upscale to target dimensions
    5. Composite text (title, author, blurb) programmatically
    6. Assemble full wrap (back + spine + front)
    7. Export eBook JPEG + print PDF
"""

import io
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from PIL import Image

from prometheus_novel.covergen.art_director import (
    generate_art_prompt,
    generate_back_cover_blurb,
)
from prometheus_novel.covergen.compositor import (
    assemble_full_wrap,
    compose_back_cover,
    compose_front_cover,
    compose_spine,
)
from prometheus_novel.covergen.image_gen import generate_cover_image
from prometheus_novel.covergen.pdf_export import export_print_pdf
from prometheus_novel.covergen.presets import auto_select_preset, get_preset
from prometheus_novel.covergen.upscaler import (
    EBOOK_HEIGHT,
    EBOOK_WIDTH,
    calculate_print_dimensions,
    fit_and_crop,
    upscale_image,
)
from prometheus_novel.prometheus_lib.llm.clients import get_client

logger = logging.getLogger(__name__)


@dataclass
class CoverConfig:
    """All cover generation parameters."""

    title: str
    author_name: str = "Author Name"
    subtitle: str = ""
    tagline: str = ""
    series_name: str = ""
    series_number: str = ""
    synopsis_blurb: str = ""
    author_bio: str = ""

    # Print specifications
    trim_size: str = "6x9"
    page_count: int = 300
    paper_type: str = "white"

    # Style
    style_preset: str = ""  # empty = auto-detect from genre
    custom_art_prompt: str = ""

    # Typography overrides
    title_font: str = ""
    author_font: str = ""
    title_color: Optional[tuple] = None

    # Layout options
    show_barcode: bool = True

    # Output
    output_dir: Optional[Path] = None


@dataclass
class CoverEngine:
    """Orchestrates the full cover generation pipeline."""

    project_path: Path
    config: Dict[str, Any]
    cover_config: CoverConfig
    client: Any = None              # LLM client for art direction / blurb
    pipeline_state: Optional[Dict[str, Any]] = None

    _generated_files: List[str] = field(default_factory=list)
    _errors: List[str] = field(default_factory=list)
    _cost_usd: float = 0.0
    _art_prompt: str = ""

    @classmethod
    def from_config_path(
        cls,
        config_path: Path,
        style: Optional[str] = None,
        trim_size: Optional[str] = None,
        page_count: Optional[int] = None,
        author_name: Optional[str] = None,
        model_override: Optional[str] = None,
    ) -> "CoverEngine":
        """Factory: load config, build CoverConfig, init clients."""
        config_path = Path(config_path)
        project_path = config_path.parent

        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        title = config.get("title", "Untitled")
        if not title or title.strip().upper() == "TODO":
            raise ValueError("Config must have a 'title' field for cover generation.")

        # Load optional pipeline state
        pipeline_state = None
        state_file = project_path / "pipeline_state.json"
        if state_file.exists():
            try:
                with open(state_file, encoding="utf-8") as f:
                    pipeline_state = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Could not load pipeline_state.json: %s", e)

        # Load optional BookOps blurb
        bookops_blurb = ""
        positioning_file = project_path / "bookops" / "01_positioning.md"
        if positioning_file.exists():
            try:
                text = positioning_file.read_text(encoding="utf-8")
                # Extract blurb section if present
                if "blurb" in text.lower():
                    bookops_blurb = text
            except OSError:
                pass

        # Build CoverConfig from config.yaml cover section + CLI overrides
        cover_section = config.get("cover", {})
        if not isinstance(cover_section, dict):
            cover_section = {}

        genre = config.get("genre", "")
        resolved_style = style or cover_section.get("style", "")
        if not resolved_style:
            resolved_style = auto_select_preset(genre)

        preset = get_preset(resolved_style)

        cover_config = CoverConfig(
            title=title,
            author_name=author_name or cover_section.get("author_name", "Author Name"),
            subtitle=cover_section.get("subtitle", ""),
            tagline=cover_section.get("tagline", ""),
            series_name=cover_section.get("series_name", ""),
            series_number=cover_section.get("series_number", ""),
            synopsis_blurb=cover_section.get("blurb", "") or bookops_blurb,
            author_bio=cover_section.get("author_bio", ""),
            trim_size=trim_size or cover_section.get("trim_size", "6x9"),
            page_count=page_count or cover_section.get("page_count", 300),
            paper_type=cover_section.get("paper_type", "white"),
            style_preset=resolved_style,
            custom_art_prompt=cover_section.get("custom_art_prompt", ""),
            title_font=cover_section.get("title_font", "") or preset["title_font"],
            author_font=cover_section.get("author_font", "") or preset["author_font"],
            show_barcode=cover_section.get("show_barcode", True),
        )

        # Parse title_color from hex if provided
        hex_color = cover_section.get("title_color", "")
        if hex_color and isinstance(hex_color, str) and hex_color.startswith("#"):
            try:
                r = int(hex_color[1:3], 16)
                g = int(hex_color[3:5], 16)
                b = int(hex_color[5:7], 16)
                cover_config.title_color = (r, g, b)
            except (ValueError, IndexError):
                pass

        cover_config.output_dir = project_path / "covergen"

        # LLM client for art direction and blurb generation
        if model_override:
            model_name = model_override
        else:
            defaults = config.get("model_defaults", {})
            model_name = defaults.get("api_model", defaults.get("local_model", "gpt-4o-mini"))

        llm_client = get_client(model_name)

        engine = cls(
            project_path=project_path,
            config=config,
            cover_config=cover_config,
            client=llm_client,
            pipeline_state=pipeline_state,
        )

        logger.info(
            "CoverGen initialized: title='%s', style=%s, trim=%s, pages=%d",
            title, resolved_style, cover_config.trim_size, cover_config.page_count,
        )
        return engine

    # ------------------------------------------------------------------
    # Output helper
    # ------------------------------------------------------------------

    def _save_file(self, filename: str, data: Any, mode: str = "wb") -> Path:
        """Save a file to the output directory."""
        self.cover_config.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.cover_config.output_dir / filename
        if mode == "wb":
            path.write_bytes(data)
        else:
            path.write_text(data, encoding="utf-8")
        self._generated_files.append(filename)
        return path

    # ------------------------------------------------------------------
    # Pipeline steps
    # ------------------------------------------------------------------

    async def _step_art_direction(self) -> str:
        """Step 2: Generate art direction prompt via LLM."""
        cc = self.cover_config

        if cc.custom_art_prompt:
            logger.info("Using custom art prompt from config")
            self._art_prompt = cc.custom_art_prompt
        else:
            self._art_prompt = await generate_art_prompt(
                config=self.config,
                style_preset=cc.style_preset,
                llm_client=self.client,
                pipeline_state=self.pipeline_state,
            )

        # Save for reproducibility
        self._save_file("art_prompt.txt", self._art_prompt, mode="w")
        return self._art_prompt

    async def _step_generate_artwork(self) -> Image.Image:
        """Step 3: Generate cover artwork via GPT Image 1."""
        result = await generate_cover_image(
            prompt=self._art_prompt,
            orientation="portrait",
            quality="high",
            output_format="png",
        )
        self._cost_usd += result.cost_usd

        # Save raw artwork
        self._save_file("cover_artwork_raw.png", result.image_bytes)

        # Load into PIL
        return Image.open(io.BytesIO(result.image_bytes)).convert("RGB")

    async def _step_generate_blurb(self) -> str:
        """Generate back cover blurb if needed."""
        cc = self.cover_config
        if cc.synopsis_blurb and len(cc.synopsis_blurb) > 50:
            return cc.synopsis_blurb

        blurb = await generate_back_cover_blurb(
            config=self.config,
            llm_client=self.client,
            existing_blurb=cc.synopsis_blurb,
        )
        cc.synopsis_blurb = blurb
        return blurb

    def _step_compose_ebook(self, artwork: Image.Image) -> Image.Image:
        """Step 5: Compose eBook cover (2560x1600)."""
        cc = self.cover_config
        preset = get_preset(cc.style_preset)

        # Fit artwork to eBook aspect ratio (1.6:1 height:width → width:height = 1600:2560)
        ebook_art = fit_and_crop(artwork, EBOOK_WIDTH, EBOOK_HEIGHT)

        ebook_cover = compose_front_cover(
            artwork=ebook_art,
            title=cc.title,
            author_name=cc.author_name,
            subtitle=cc.subtitle,
            series_name=cc.series_name,
            title_font_name=cc.title_font,
            author_font_name=cc.author_font,
            text_color=cc.title_color,
            stroke_width=preset.get("text_stroke_width", 2),
            shadow=preset.get("text_shadow", True),
        )

        # Save as JPEG (KDP ebook format)
        buf = io.BytesIO()
        ebook_cover.convert("RGB").save(buf, format="JPEG", quality=95, dpi=(72, 72))
        self._save_file("cover_ebook.jpg", buf.getvalue())

        return ebook_cover

    def _step_compose_print(self, artwork: Image.Image) -> Image.Image:
        """Steps 6-9: Compose full print wrap."""
        cc = self.cover_config
        preset = get_preset(cc.style_preset)

        dims = calculate_print_dimensions(
            trim_size=cc.trim_size,
            page_count=cc.page_count,
            paper_type=cc.paper_type,
        )

        # Step 6: Front cover at print resolution
        front_art = fit_and_crop(artwork, dims.front_width_px, dims.front_height_px)
        front = compose_front_cover(
            artwork=front_art,
            title=cc.title,
            author_name=cc.author_name,
            subtitle=cc.subtitle,
            series_name=cc.series_name,
            title_font_name=cc.title_font,
            author_font_name=cc.author_font,
            text_color=cc.title_color,
            stroke_width=preset.get("text_stroke_width", 2),
            shadow=preset.get("text_shadow", True),
        )
        buf = io.BytesIO()
        front.save(buf, format="PNG", dpi=(300, 300))
        self._save_file("cover_print_front.png", buf.getvalue())

        # Step 7: Spine
        spine = compose_spine(
            title=cc.title,
            author_name=cc.author_name,
            spine_width_px=dims.spine_width_px,
            height_px=dims.front_height_px,
            bg_color=preset["default_bg_color"],
            text_color=preset["default_text_color"],
            title_font_name=cc.title_font,
            author_font_name=cc.author_font,
        )
        buf = io.BytesIO()
        spine.save(buf, format="PNG", dpi=(300, 300))
        self._save_file("cover_print_spine.png", buf.getvalue())

        # Step 8: Back cover
        back = compose_back_cover(
            blurb=cc.synopsis_blurb,
            author_bio=cc.author_bio,
            width_px=dims.back_width_px,
            height_px=dims.back_height_px,
            bg_color=preset["default_bg_color"],
            text_color=preset["default_text_color"],
            tagline=cc.tagline,
            body_font_name=cc.author_font,
            artwork_bg=artwork,
            safe_zone_px=dims.safe_zone_px,
            barcode_width_px=dims.barcode_width_px,
            barcode_height_px=dims.barcode_height_px,
            show_barcode=cc.show_barcode,
        )
        buf = io.BytesIO()
        back.save(buf, format="PNG", dpi=(300, 300))
        self._save_file("cover_print_back.png", buf.getvalue())

        # Step 9: Assemble full wrap
        wrap = assemble_full_wrap(
            front=front,
            spine=spine,
            back=back,
            bleed_px=dims.bleed_px,
        )
        buf = io.BytesIO()
        wrap.save(buf, format="PNG", dpi=(300, 300))
        self._save_file("cover_print_wrap.png", buf.getvalue())

        # Step 10: Export PDF
        pdf_path = self.cover_config.output_dir / "cover_print.pdf"
        export_print_pdf(
            cover_image=wrap,
            output_path=pdf_path,
            total_width_inches=dims.total_width_inches,
            total_height_inches=dims.total_height_inches,
        )
        self._generated_files.append("cover_print.pdf")

        return wrap

    def _generate_report(self) -> str:
        """Generate cover_report.md summarizing the generation."""
        cc = self.cover_config
        dims = calculate_print_dimensions(cc.trim_size, cc.page_count, cc.paper_type)

        lines = [
            "# Cover Generation Report",
            "",
            f"**Title:** {cc.title}",
            f"**Author:** {cc.author_name}",
            f"**Style Preset:** {cc.style_preset}",
            f"**Trim Size:** {cc.trim_size}",
            f"**Page Count:** {cc.page_count}",
            f"**Paper Type:** {cc.paper_type}",
            f"**Spine Width:** {dims.spine_width:.3f}\"",
            "",
            "## Dimensions",
            "",
            f"- eBook: {EBOOK_WIDTH}x{EBOOK_HEIGHT} px (JPEG, RGB)",
            f"- Print front: {dims.front_width_px}x{dims.front_height_px} px (300 DPI)",
            f"- Print spine: {dims.spine_width_px}x{dims.front_height_px} px",
            f"- Print full wrap: {dims.total_width_px}x{dims.total_height_px} px "
            f"({dims.total_width_inches:.3f}\" x {dims.total_height_inches:.3f}\")",
            "",
            "## Generated Files",
            "",
        ]
        for fname in self._generated_files:
            lines.append(f"- `{fname}`")

        lines += [
            "",
            f"## Cost",
            "",
            f"Image generation: ${self._cost_usd:.4f}",
            "",
            "## Art Direction Prompt",
            "",
            "```",
            self._art_prompt,
            "```",
        ]

        if self._errors:
            lines += ["", "## Errors", ""]
            for err in self._errors:
                lines.append(f"- {err}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Main entry points
    # ------------------------------------------------------------------

    async def generate_all(self) -> Dict[str, Any]:
        """Full pipeline: art direction -> image gen -> compose -> export.

        Returns dict with file paths and metadata.
        """
        logger.info("Starting cover generation for '%s'", self.cover_config.title)

        # Step 2: Art direction
        await self._step_art_direction()

        # Step 3: Generate artwork + Step blurb (parallel)
        artwork = await self._step_generate_artwork()
        await self._step_generate_blurb()

        # Step 5: eBook cover
        try:
            self._step_compose_ebook(artwork)
        except Exception as e:
            self._errors.append(f"eBook cover failed: {e}")
            logger.error("eBook cover composition failed: %s", e)

        # Steps 6-10: Print cover
        try:
            self._step_compose_print(artwork)
        except Exception as e:
            self._errors.append(f"Print cover failed: {e}")
            logger.error("Print cover composition failed: %s", e)

        # Report
        report = self._generate_report()
        self._save_file("cover_report.md", report, mode="w")

        return {
            "files": self._generated_files,
            "cost_usd": self._cost_usd,
            "errors": self._errors,
            "output_dir": str(self.cover_config.output_dir),
        }

    async def generate_ebook_cover(self) -> Dict[str, Any]:
        """Generate only the eBook cover."""
        await self._step_art_direction()
        artwork = await self._step_generate_artwork()
        self._step_compose_ebook(artwork)

        report = self._generate_report()
        self._save_file("cover_report.md", report, mode="w")

        return {
            "files": self._generated_files,
            "cost_usd": self._cost_usd,
            "output_dir": str(self.cover_config.output_dir),
        }

    async def generate_print_cover(self) -> Dict[str, Any]:
        """Generate only the print cover (front + spine + back + PDF)."""
        await self._step_art_direction()
        artwork = await self._step_generate_artwork()
        await self._step_generate_blurb()
        self._step_compose_print(artwork)

        report = self._generate_report()
        self._save_file("cover_report.md", report, mode="w")

        return {
            "files": self._generated_files,
            "cost_usd": self._cost_usd,
            "output_dir": str(self.cover_config.output_dir),
        }

    def print_summary(self) -> None:
        """Print generation results to console."""
        cc = self.cover_config
        print(f"\n  Cover generated for: {cc.title}")
        print(f"  Style: {cc.style_preset}")
        print(f"  Output: {cc.output_dir}/")
        print(f"  Files:")
        for f in self._generated_files:
            print(f"    - {f}")
        print(f"  Cost: ${self._cost_usd:.4f}")
        if self._errors:
            print(f"  Errors:")
            for err in self._errors:
                print(f"    - {err}")
        print()
