"""Style presets for cover generation.

Each preset defines art direction modifiers, default typography, and color choices
that map to common genre conventions.
"""

from typing import Any, Dict

STYLE_PRESETS: Dict[str, Dict[str, Any]] = {
    "cinematic": {
        "description": "Dramatic lighting, high contrast, photorealistic",
        "art_modifiers": (
            "cinematic lighting, dramatic shadows, high contrast, photorealistic, "
            "film grain, anamorphic lens, moody atmosphere, 35mm photography"
        ),
        "default_text_color": (255, 255, 255),
        "default_bg_color": (15, 15, 20),
        "title_font": "Oswald-Bold",
        "author_font": "LibreBaskerville-Regular",
        "text_shadow": True,
        "text_stroke_width": 2,
    },
    "illustrated": {
        "description": "Digital illustration, painted style, vibrant colors",
        "art_modifiers": (
            "digital illustration, painted style, vibrant colors, detailed brushwork, "
            "fantasy art, concept art quality"
        ),
        "default_text_color": (255, 255, 255),
        "default_bg_color": (25, 20, 35),
        "title_font": "Lora-Bold",
        "author_font": "Lora-Regular",
        "text_shadow": True,
        "text_stroke_width": 2,
    },
    "minimalist": {
        "description": "Clean, simple, symbolic, lots of negative space",
        "art_modifiers": (
            "minimalist design, clean composition, symbolic imagery, negative space, "
            "simple shapes, elegant, understated"
        ),
        "default_text_color": (30, 30, 30),
        "default_bg_color": (245, 240, 235),
        "title_font": "Oswald-Medium",
        "author_font": "LibreBaskerville-Regular",
        "text_shadow": False,
        "text_stroke_width": 0,
    },
    "dark": {
        "description": "Dark, atmospheric, horror/thriller mood",
        "art_modifiers": (
            "dark atmosphere, deep shadows, low key lighting, ominous, foreboding, "
            "noir, chiaroscuro, mist, desaturated"
        ),
        "default_text_color": (200, 180, 160),
        "default_bg_color": (10, 8, 12),
        "title_font": "Oswald-Bold",
        "author_font": "LibreBaskerville-Regular",
        "text_shadow": True,
        "text_stroke_width": 2,
    },
    "romantic": {
        "description": "Warm tones, golden light, soft focus, intimate",
        "art_modifiers": (
            "warm golden light, soft focus, romantic atmosphere, intimate mood, "
            "bokeh, sunset tones, dreamy, soft color palette"
        ),
        "default_text_color": (255, 248, 240),
        "default_bg_color": (60, 30, 40),
        "title_font": "Lora-BoldItalic",
        "author_font": "Lora-Regular",
        "text_shadow": True,
        "text_stroke_width": 1,
    },
    "literary": {
        "description": "Subtle, textured, abstract, understated sophistication",
        "art_modifiers": (
            "abstract composition, subtle textures, muted palette, artistic, "
            "watercolor impression, literary fiction aesthetic"
        ),
        "default_text_color": (40, 35, 30),
        "default_bg_color": (230, 225, 215),
        "title_font": "LibreBaskerville-Bold",
        "author_font": "LibreBaskerville-Regular",
        "text_shadow": False,
        "text_stroke_width": 0,
    },
}

# Genre → preset auto-selection
_GENRE_MAP: Dict[str, str] = {
    "romance": "romantic",
    "romantic suspense": "cinematic",
    "thriller": "dark",
    "horror": "dark",
    "mystery": "cinematic",
    "sci-fi": "cinematic",
    "science fiction": "cinematic",
    "fantasy": "illustrated",
    "literary fiction": "literary",
    "literary": "literary",
    "nonfiction": "minimalist",
    "self-help": "minimalist",
    "memoir": "literary",
    "historical": "cinematic",
    "paranormal": "dark",
    "urban fantasy": "illustrated",
    "contemporary": "cinematic",
}


def get_preset(name: str) -> Dict[str, Any]:
    """Get style preset by name, falling back to 'cinematic'."""
    return STYLE_PRESETS.get(name, STYLE_PRESETS["cinematic"])


def auto_select_preset(genre: str) -> str:
    """Suggest a style preset based on genre string."""
    genre_lower = genre.lower().strip()
    for key, preset_name in _GENRE_MAP.items():
        if key in genre_lower:
            return preset_name
    return "cinematic"
