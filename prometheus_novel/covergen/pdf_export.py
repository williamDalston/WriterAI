"""PDF export for KDP print covers using fpdf2."""

import logging
import tempfile
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


def export_print_pdf(
    cover_image: Image.Image,
    output_path: Path,
    total_width_inches: float,
    total_height_inches: float,
    dpi: int = 300,
) -> Path:
    """Export assembled full-wrap cover as a single-page PDF.

    The cover image fills the entire page at the specified physical dimensions.
    KDP requires a single-page PDF with no crop marks or template text.

    Args:
        cover_image: Full wrap cover image (back + spine + front with bleeds).
        output_path: Where to save the PDF.
        total_width_inches: Physical width including bleeds.
        total_height_inches: Physical height including bleeds.
        dpi: Target DPI (default 300 for KDP).

    Returns:
        Path to the saved PDF.
    """
    from fpdf import FPDF

    # fpdf2 works in mm
    width_mm = total_width_inches * 25.4
    height_mm = total_height_inches * 25.4

    pdf = FPDF(unit="mm", format=(width_mm, height_mm))
    pdf.set_auto_page_break(False)
    pdf.set_margin(0)
    pdf.add_page()

    # Save image to temp JPEG (smaller than PNG for PDF embedding)
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()  # Close before PIL writes (required on Windows)
    try:
        # Ensure RGB for JPEG
        if cover_image.mode != "RGB":
            cover_image = cover_image.convert("RGB")
        cover_image.save(tmp_path, format="JPEG", quality=95, dpi=(dpi, dpi))

        pdf.image(str(tmp_path), x=0, y=0, w=width_mm, h=height_mm)
        pdf.output(str(output_path))

        logger.info(
            "Print PDF saved: %s (%.2f x %.2f mm, %d DPI)",
            output_path, width_mm, height_mm, dpi,
        )
    finally:
        tmp_path.unlink(missing_ok=True)

    return output_path
