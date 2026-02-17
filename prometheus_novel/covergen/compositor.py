"""Cover compositor — text overlay, spine, back cover, and full wrap assembly.

All typography is rendered programmatically (not by the AI image generator)
for pixel-perfect, reliable text rendering on book covers.
"""

import logging
import textwrap
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

logger = logging.getLogger(__name__)

# Directory containing bundled OFL fonts
_FONTS_DIR = Path(__file__).resolve().parent / "fonts"


# ---------------------------------------------------------------------------
# Font loading
# ---------------------------------------------------------------------------

def get_font(font_name: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a TrueType font with fallback chain.

    Search order:
        1. covergen/fonts/{font_name}.ttf
        2. System fonts directory
        3. Pillow default (last resort)
    """
    # 1. Bundled fonts
    bundled = _FONTS_DIR / f"{font_name}.ttf"
    if bundled.exists():
        return ImageFont.truetype(str(bundled), size)

    # 2. System fonts (Windows)
    import platform
    if platform.system() == "Windows":
        sys_font = Path("C:/Windows/Fonts") / f"{font_name}.ttf"
        if sys_font.exists():
            return ImageFont.truetype(str(sys_font), size)

    # 3. Pillow default
    logger.warning("Font '%s' not found, using Pillow default", font_name)
    return ImageFont.load_default(size)


# ---------------------------------------------------------------------------
# Color analysis
# ---------------------------------------------------------------------------

def analyze_luminance(image: Image.Image, region: str = "full") -> float:
    """Compute average luminance (0.0 = black, 1.0 = white) of an image region.

    Args:
        image: Source image.
        region: "full", "top" (top 35%), or "bottom" (bottom 25%).

    Returns:
        Average luminance as float 0..1.
    """
    if region == "top":
        box = (0, 0, image.width, int(image.height * 0.35))
    elif region == "bottom":
        box = (0, int(image.height * 0.75), image.width, image.height)
    else:
        box = None

    sample = image.crop(box) if box else image
    gray = sample.convert("L")
    histogram = gray.histogram()
    total_pixels = sum(histogram)
    if total_pixels == 0:
        return 0.5
    weighted = sum(i * count for i, count in enumerate(histogram))
    return weighted / (total_pixels * 255.0)


def pick_text_color(luminance: float) -> Tuple[int, int, int]:
    """Choose white or dark text based on background luminance."""
    if luminance < 0.45:
        return (255, 255, 255)
    return (30, 25, 20)


def pick_stroke_color(text_color: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Choose stroke/outline color opposite to text."""
    if text_color[0] > 128:
        return (0, 0, 0)
    return (200, 200, 200)


# ---------------------------------------------------------------------------
# Text rendering helpers
# ---------------------------------------------------------------------------

def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test = f"{current_line} {word}".strip()
        bbox = font.getbbox(test)
        if bbox[2] <= max_width:
            current_line = test
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)
    return lines or [text]


def _render_text_block(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    x_center: int,
    y_start: int,
    max_width: int,
    color: Tuple[int, int, int] = (255, 255, 255),
    stroke_width: int = 0,
    stroke_color: Optional[Tuple[int, int, int]] = None,
    shadow: bool = False,
    line_spacing: float = 1.3,
) -> int:
    """Render wrapped text centered at x_center, starting at y_start.

    Returns:
        y position after the last line.
    """
    lines = _wrap_text(text, font, max_width)
    ascent, descent = font.getmetrics()
    line_height = int((ascent + descent) * line_spacing)

    y = y_start
    for line in lines:
        bbox = font.getbbox(line)
        text_width = bbox[2] - bbox[0]
        tx = x_center - text_width // 2

        # Drop shadow
        if shadow:
            shadow_offset = max(2, stroke_width + 1)
            draw.text(
                (tx + shadow_offset, y + shadow_offset),
                line, font=font, fill=(0, 0, 0, 180),
            )

        # Stroke outline
        if stroke_width > 0 and stroke_color:
            draw.text(
                (tx, y), line, font=font, fill=color,
                stroke_width=stroke_width, stroke_fill=stroke_color,
            )
        else:
            draw.text((tx, y), line, font=font, fill=color)

        y += line_height

    return y


def _auto_fit_font(
    text: str,
    font_name: str,
    max_width: int,
    max_height: int,
    start_size: int = 200,
    min_size: int = 24,
    line_spacing: float = 1.3,
) -> Tuple[ImageFont.FreeTypeFont, int]:
    """Find the largest font size that fits text within the given bounds.

    Returns (font, font_size).
    """
    for size in range(start_size, min_size - 1, -4):
        font = get_font(font_name, size)
        lines = _wrap_text(text, font, max_width)
        ascent, descent = font.getmetrics()
        line_height = int((ascent + descent) * line_spacing)
        total_height = line_height * len(lines)
        if total_height <= max_height:
            return font, size
    return get_font(font_name, min_size), min_size


# ---------------------------------------------------------------------------
# Front cover composition
# ---------------------------------------------------------------------------

def compose_front_cover(
    artwork: Image.Image,
    title: str,
    author_name: str,
    subtitle: str = "",
    series_name: str = "",
    title_font_name: str = "Oswald-Bold",
    author_font_name: str = "LibreBaskerville-Regular",
    text_color: Optional[Tuple[int, int, int]] = None,
    stroke_width: int = 2,
    shadow: bool = True,
) -> Image.Image:
    """Compose front cover: artwork + title + subtitle + author name.

    Text placement:
        - Title: top area (~15-35% from top)
        - Subtitle: below title
        - Series: above title (small)
        - Author name: bottom area (~80-90% from top)

    If text_color is None, auto-detects from artwork luminance.
    """
    cover = artwork.copy().convert("RGBA")
    draw = ImageDraw.Draw(cover)
    w, h = cover.size
    max_text_width = int(w * 0.80)
    x_center = w // 2

    # Auto-detect text color from artwork
    if text_color is None:
        top_lum = analyze_luminance(artwork, "top")
        bottom_lum = analyze_luminance(artwork, "bottom")
        title_color = pick_text_color(top_lum)
        author_color = pick_text_color(bottom_lum)
    else:
        title_color = text_color
        author_color = text_color

    stroke_fill = pick_stroke_color(title_color)
    author_stroke_fill = pick_stroke_color(author_color)

    y_cursor = int(h * 0.12)

    # Series name (small, above title)
    if series_name:
        series_font = get_font(author_font_name, max(20, int(h * 0.022)))
        y_cursor = _render_text_block(
            draw, series_name.upper(), series_font, x_center, y_cursor,
            max_text_width, title_color,
            stroke_width=max(1, stroke_width - 1), stroke_color=stroke_fill,
            shadow=shadow, line_spacing=1.2,
        )
        y_cursor += int(h * 0.015)

    # Title (large, auto-fitted)
    title_area_height = int(h * 0.22)
    title_font, _ = _auto_fit_font(
        title.upper(), title_font_name, max_text_width, title_area_height,
        start_size=int(h * 0.12), min_size=int(h * 0.04),
    )
    y_cursor = _render_text_block(
        draw, title.upper(), title_font, x_center, y_cursor,
        max_text_width, title_color,
        stroke_width=stroke_width, stroke_color=stroke_fill,
        shadow=shadow, line_spacing=1.15,
    )

    # Subtitle
    if subtitle:
        y_cursor += int(h * 0.02)
        sub_font = get_font(author_font_name, max(20, int(h * 0.028)))
        y_cursor = _render_text_block(
            draw, subtitle, sub_font, x_center, y_cursor,
            max_text_width, title_color,
            stroke_width=max(1, stroke_width - 1), stroke_color=stroke_fill,
            shadow=shadow,
        )

    # Author name (bottom)
    author_y = int(h * 0.84)
    author_font, _ = _auto_fit_font(
        author_name, author_font_name, max_text_width, int(h * 0.10),
        start_size=int(h * 0.05), min_size=int(h * 0.025),
    )
    _render_text_block(
        draw, author_name, author_font, x_center, author_y,
        max_text_width, author_color,
        stroke_width=stroke_width, stroke_color=author_stroke_fill,
        shadow=shadow,
    )

    return cover.convert("RGB")


# ---------------------------------------------------------------------------
# Spine composition
# ---------------------------------------------------------------------------

def compose_spine(
    title: str,
    author_name: str,
    spine_width_px: int,
    height_px: int,
    bg_color: Tuple[int, int, int] = (30, 30, 30),
    text_color: Tuple[int, int, int] = (220, 220, 220),
    title_font_name: str = "Oswald-Bold",
    author_font_name: str = "LibreBaskerville-Regular",
) -> Image.Image:
    """Generate spine image with rotated title and author.

    KDP convention: text reads top-to-bottom (rotate 90 degrees CW).
    If spine < 0.5" (150px at 300 DPI), only title (no author).
    If spine < 0.25" (75px at 300 DPI), leave blank.
    """
    spine = Image.new("RGB", (spine_width_px, height_px), bg_color)

    if spine_width_px < 75:
        logger.info("Spine too narrow (%dpx) for text, leaving blank", spine_width_px)
        return spine

    # Text is rendered on a tall, narrow canvas then rotated
    usable_height = height_px - 100  # margins
    include_author = spine_width_px >= 150

    if include_author:
        spine_text = f"{title.upper()}    {author_name}"
    else:
        spine_text = title.upper()

    # Font size proportional to spine width
    font_size = max(14, int(spine_width_px * 0.55))
    font = get_font(title_font_name, font_size)

    # Render text on a horizontal canvas, then rotate
    bbox = font.getbbox(spine_text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Create horizontal text image
    txt_img = Image.new("RGBA", (text_width + 20, text_height + 20), (0, 0, 0, 0))
    txt_draw = ImageDraw.Draw(txt_img)
    txt_draw.text((10, 10), spine_text, font=font, fill=text_color)

    # Rotate 90 degrees clockwise (top-to-bottom reading)
    rotated = txt_img.rotate(-90, expand=True, resample=Image.BICUBIC)

    # Scale if too tall
    if rotated.height > usable_height:
        scale = usable_height / rotated.height
        new_w = max(1, int(rotated.width * scale))
        new_h = int(rotated.height * scale)
        rotated = rotated.resize((new_w, new_h), Image.LANCZOS)

    # Center on spine
    x = (spine_width_px - rotated.width) // 2
    y = (height_px - rotated.height) // 2
    spine.paste(rotated, (x, y), rotated)

    return spine


# ---------------------------------------------------------------------------
# Back cover composition
# ---------------------------------------------------------------------------

def compose_back_cover(
    blurb: str,
    author_bio: str,
    width_px: int,
    height_px: int,
    bg_color: Tuple[int, int, int] = (30, 30, 30),
    text_color: Tuple[int, int, int] = (220, 220, 220),
    tagline: str = "",
    body_font_name: str = "LibreBaskerville-Regular",
    artwork_bg: Optional[Image.Image] = None,
    safe_zone_px: int = 75,
    barcode_width_px: int = 600,
    barcode_height_px: int = 360,
    show_barcode: bool = True,
) -> Image.Image:
    """Generate back cover with blurb, author bio, and barcode zone.

    Layout (top to bottom):
        - Safe zone padding
        - Tagline (if provided)
        - Blurb text (centered, wrapped)
        - Author bio (smaller text)
        - [gap]
        - Barcode zone: clear rectangle in lower-right
        - Safe zone padding
    """
    if artwork_bg is not None:
        # Use blurred/darkened artwork as background
        back = artwork_bg.copy().resize((width_px, height_px), Image.LANCZOS)
        # Darken + blur for readability
        from PIL import ImageEnhance
        back = ImageEnhance.Brightness(back).enhance(0.3)
        back = back.filter(ImageFilter.GaussianBlur(radius=8))
    else:
        back = Image.new("RGB", (width_px, height_px), bg_color)

    draw = ImageDraw.Draw(back)
    margin = safe_zone_px + 30
    max_text_width = width_px - margin * 2
    x_center = width_px // 2
    y = margin

    # Tagline
    if tagline:
        tag_font = get_font(body_font_name, max(18, int(height_px * 0.022)))
        y = _render_text_block(
            draw, tagline.upper(), tag_font, x_center, y,
            max_text_width, text_color, line_spacing=1.4,
        )
        y += int(height_px * 0.04)

    # Blurb
    if blurb:
        blurb_font = get_font(body_font_name, max(16, int(height_px * 0.020)))
        y = _render_text_block(
            draw, blurb, blurb_font, x_center, y,
            max_text_width, text_color, line_spacing=1.5,
        )
        y += int(height_px * 0.05)

    # Author bio
    if author_bio:
        bio_font = get_font(body_font_name, max(14, int(height_px * 0.016)))
        # Separator line
        line_y = y
        draw.line(
            [(margin, line_y), (width_px - margin, line_y)],
            fill=(*text_color[:3], 80) if len(text_color) > 3 else text_color,
            width=1,
        )
        y = line_y + 20
        _render_text_block(
            draw, author_bio, bio_font, x_center, y,
            max_text_width, text_color, line_spacing=1.5,
        )

    # Barcode zone (lower-right, white rectangle with outline)
    if show_barcode:
        barcode_x = width_px - margin - barcode_width_px
        barcode_y = height_px - margin - barcode_height_px
        draw.rectangle(
            [barcode_x, barcode_y, barcode_x + barcode_width_px, barcode_y + barcode_height_px],
            fill=(255, 255, 255),
            outline=(180, 180, 180),
            width=2,
        )
        # Placeholder text
        bc_font = get_font("Oswald-Medium", 18)
        draw.text(
            (barcode_x + barcode_width_px // 2, barcode_y + barcode_height_px // 2),
            "ISBN BARCODE", font=bc_font, fill=(150, 150, 150), anchor="mm",
        )

    return back


# ---------------------------------------------------------------------------
# Full wrap assembly
# ---------------------------------------------------------------------------

def assemble_full_wrap(
    front: Image.Image,
    spine: Image.Image,
    back: Image.Image,
    bleed_px: int,
) -> Image.Image:
    """Assemble full wrap: [bleed][back][spine][front][bleed] with vertical bleed.

    Bleed areas extend the edge pixels outward.
    """
    wrap_w = bleed_px + back.width + spine.width + front.width + bleed_px
    wrap_h = bleed_px + front.height + bleed_px

    wrap = Image.new("RGB", (wrap_w, wrap_h), (0, 0, 0))

    # Paste main panels (offset by bleed)
    x = bleed_px
    wrap.paste(back, (x, bleed_px))
    x += back.width
    wrap.paste(spine, (x, bleed_px))
    x += spine.width
    wrap.paste(front, (x, bleed_px))

    # Fill bleed by extending edge pixels
    _fill_bleed(wrap, bleed_px, back.width, spine.width, front.width, front.height)

    return wrap


def _fill_bleed(
    wrap: Image.Image,
    bleed: int,
    back_w: int,
    spine_w: int,
    front_w: int,
    panel_h: int,
) -> None:
    """Fill bleed areas by mirroring edge pixels."""
    # Left bleed (mirror left edge of back cover)
    if bleed > 0:
        left_strip = wrap.crop((bleed, bleed, bleed + 1, bleed + panel_h))
        for i in range(bleed):
            wrap.paste(left_strip, (i, bleed))

        # Right bleed (mirror right edge of front cover)
        right_x = bleed + back_w + spine_w + front_w - 1
        right_strip = wrap.crop((right_x, bleed, right_x + 1, bleed + panel_h))
        for i in range(bleed):
            wrap.paste(right_strip, (right_x + 1 + i, bleed))

        # Top bleed (mirror top row of panels)
        top_strip = wrap.crop((0, bleed, wrap.width, bleed + 1))
        for i in range(bleed):
            wrap.paste(top_strip, (0, i))

        # Bottom bleed (mirror bottom row of panels)
        bottom_y = bleed + panel_h - 1
        bottom_strip = wrap.crop((0, bottom_y, wrap.width, bottom_y + 1))
        for i in range(bleed):
            wrap.paste(bottom_strip, (0, bottom_y + 1 + i))
