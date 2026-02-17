"""Image upscaling and KDP dimension calculations."""

import logging
from dataclasses import dataclass
from typing import Dict

from PIL import Image, ImageFilter

logger = logging.getLogger(__name__)

# KDP spine width multipliers (inches per page)
SPINE_MULTIPLIER_WHITE = 0.002252
SPINE_MULTIPLIER_CREAM = 0.0025

# Standard trim sizes (width x height in inches)
TRIM_SIZES = {
    "6x9": (6.0, 9.0),
    "5.5x8.5": (5.5, 8.5),
    "5x8": (5.0, 8.0),
}

# KDP constants
BLEED_INCHES = 0.125
SAFE_ZONE_INCHES = 0.25
PRINT_DPI = 300
BARCODE_WIDTH_INCHES = 2.0
BARCODE_HEIGHT_INCHES = 1.2

# eBook cover specs (portrait: 1600w x 2560h for KDP)
EBOOK_WIDTH = 1600
EBOOK_HEIGHT = 2560
assert EBOOK_HEIGHT > EBOOK_WIDTH, "eBook cover must be portrait (H > W)"


@dataclass
class PrintDimensions:
    """Calculated pixel dimensions for a KDP print cover at 300 DPI."""
    trim_width: float       # inches
    trim_height: float      # inches
    spine_width: float      # inches
    bleed: float            # inches

    @property
    def front_width_px(self) -> int:
        return int(self.trim_width * PRINT_DPI)

    @property
    def front_height_px(self) -> int:
        return int(self.trim_height * PRINT_DPI)

    @property
    def spine_width_px(self) -> int:
        return max(1, int(self.spine_width * PRINT_DPI))

    @property
    def back_width_px(self) -> int:
        return self.front_width_px

    @property
    def back_height_px(self) -> int:
        return self.front_height_px

    @property
    def bleed_px(self) -> int:
        return int(self.bleed * PRINT_DPI)

    @property
    def safe_zone_px(self) -> int:
        return int(SAFE_ZONE_INCHES * PRINT_DPI)

    @property
    def barcode_width_px(self) -> int:
        return int(BARCODE_WIDTH_INCHES * PRINT_DPI)

    @property
    def barcode_height_px(self) -> int:
        return int(BARCODE_HEIGHT_INCHES * PRINT_DPI)

    @property
    def total_width_inches(self) -> float:
        return self.bleed + self.trim_width + self.spine_width + self.trim_width + self.bleed

    @property
    def total_height_inches(self) -> float:
        return self.bleed + self.trim_height + self.bleed

    @property
    def total_width_px(self) -> int:
        return int(self.total_width_inches * PRINT_DPI)

    @property
    def total_height_px(self) -> int:
        return int(self.total_height_inches * PRINT_DPI)


def calculate_print_dimensions(
    trim_size: str = "6x9",
    page_count: int = 300,
    paper_type: str = "white",
) -> PrintDimensions:
    """Calculate all pixel dimensions for a KDP print cover.

    Args:
        trim_size: One of "6x9", "5.5x8.5", "5x8".
        page_count: Number of pages (for spine width).
        paper_type: "white" or "cream".

    Returns:
        PrintDimensions with all calculated values.
    """
    if trim_size not in TRIM_SIZES:
        logger.warning("Unknown trim size '%s', defaulting to 6x9", trim_size)
        trim_size = "6x9"

    trim_w, trim_h = TRIM_SIZES[trim_size]
    multiplier = SPINE_MULTIPLIER_CREAM if paper_type == "cream" else SPINE_MULTIPLIER_WHITE
    spine_w = page_count * multiplier

    dims = PrintDimensions(
        trim_width=trim_w,
        trim_height=trim_h,
        spine_width=spine_w,
        bleed=BLEED_INCHES,
    )

    logger.info(
        "Print dimensions: trim=%sx%s, spine=%.3f\", total=%dx%d px at %d DPI",
        trim_w, trim_h, spine_w, dims.total_width_px, dims.total_height_px, PRINT_DPI,
    )
    return dims


def upscale_image(
    image: Image.Image,
    target_width: int,
    target_height: int,
) -> Image.Image:
    """Upscale image to target resolution using LANCZOS resampling.

    Applies mild unsharp mask after upscale to compensate for softening.
    """
    if image.size == (target_width, target_height):
        return image

    logger.info(
        "Upscaling %dx%d → %dx%d (LANCZOS)",
        image.width, image.height, target_width, target_height,
    )
    resampled = image.resize((target_width, target_height), Image.LANCZOS)

    # Mild sharpening to restore detail
    sharpened = resampled.filter(
        ImageFilter.UnsharpMask(radius=1.5, percent=30, threshold=2)
    )
    return sharpened


def fit_and_crop(
    image: Image.Image,
    target_width: int,
    target_height: int,
) -> Image.Image:
    """Resize image to fill target dimensions, cropping excess.

    Centers the crop to preserve the focal point of the artwork.
    """
    src_ratio = image.width / image.height
    tgt_ratio = target_width / target_height

    if src_ratio > tgt_ratio:
        # Source is wider — scale by height, crop width
        scale_h = target_height
        scale_w = int(image.width * (target_height / image.height))
    else:
        # Source is taller — scale by width, crop height
        scale_w = target_width
        scale_h = int(image.height * (target_width / image.width))

    scaled = image.resize((scale_w, scale_h), Image.LANCZOS)

    # Center crop
    left = (scale_w - target_width) // 2
    top = (scale_h - target_height) // 2
    cropped = scaled.crop((left, top, left + target_width, top + target_height))

    # Mild sharpening
    return cropped.filter(
        ImageFilter.UnsharpMask(radius=1.5, percent=30, threshold=2)
    )
