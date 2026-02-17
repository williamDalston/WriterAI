"""LLM-based art direction for cover artwork generation.

Generates detailed visual prompts from novel metadata. The prompts describe
imagery only — never text, typography, or lettering — since all title/author
text is composited programmatically.
"""

import logging
from typing import Any, Dict, Optional

from prometheus_novel.covergen.presets import get_preset

logger = logging.getLogger(__name__)

ART_DIRECTOR_SYSTEM = """\
You are an art director for book covers at a major publishing house.
You create detailed visual descriptions for cover background artwork.

CRITICAL RULES — FOLLOW EXACTLY:
- NEVER mention text, typography, letters, words, title, author name, or any lettering
- NEVER describe text placement, font choices, or written elements
- Focus ONLY on visual imagery: mood, lighting, color palette, composition, subjects, setting
- Leave the top ~30% and bottom ~20% of the frame relatively uncluttered \
(these areas will have text overlaid later, but do NOT mention this)
- Describe a single static image, not a narrative or sequence
- The image should have one dominant focal point
- Be specific about colors, textures, atmosphere, and lighting direction
- Keep the description under 200 words
- Output ONLY the visual description, no preamble or commentary"""


async def generate_art_prompt(
    config: Dict[str, Any],
    style_preset: str,
    llm_client: Any,
    pipeline_state: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a visual art direction prompt from novel metadata.

    Assembles context from genre, setting, tone, themes, motifs, and the
    selected style preset, then asks the LLM to craft a detailed visual
    description suitable for an image generator.

    Args:
        config: Project config.yaml dict.
        style_preset: Name of the style preset (e.g. "cinematic", "romantic").
        llm_client: An LLM client with async generate() method.
        pipeline_state: Optional loaded pipeline state for richer context.

    Returns:
        A visual description prompt string (no text/typography references).
    """
    preset = get_preset(style_preset)

    # Assemble context from config
    context_parts = []

    genre = config.get("genre", "")
    if genre:
        context_parts.append(f"Genre: {genre}")

    title = config.get("title", "Untitled")
    context_parts.append(f"Book title (for thematic reference only, NOT to be rendered): {title}")

    setting = config.get("setting", "")
    if setting:
        context_parts.append(f"Setting: {setting}")

    tone = config.get("tone", "")
    if tone:
        context_parts.append(f"Tone/mood: {tone}")

    themes = config.get("themes", "")
    if themes:
        if isinstance(themes, list):
            themes = ", ".join(themes)
        context_parts.append(f"Themes: {themes}")

    motifs = config.get("motifs", "")
    if motifs:
        if isinstance(motifs, list):
            motifs = ", ".join(motifs)
        context_parts.append(f"Visual motifs: {motifs}")

    protagonist = config.get("protagonist", "")
    if protagonist:
        context_parts.append(f"Protagonist: {protagonist}")

    synopsis = config.get("synopsis", "")
    if synopsis:
        # Truncate to keep prompt focused
        context_parts.append(f"Synopsis (for mood reference): {synopsis[:300]}")

    # Strategic guidance / aesthetic hints
    strat = config.get("strategic_guidance", {})
    if isinstance(strat, dict):
        aesthetic = strat.get("aesthetic_guide", "")
        if aesthetic:
            context_parts.append(f"Aesthetic guidance: {aesthetic}")

    # Pipeline state for richer context
    if pipeline_state:
        high_concept = pipeline_state.get("high_concept", "")
        if high_concept:
            context_parts.append(f"High concept: {high_concept[:200]}")

        world_bible = pipeline_state.get("world_bible", {})
        if isinstance(world_bible, dict):
            visual_setting = world_bible.get("setting", "")
            if visual_setting and isinstance(visual_setting, str):
                context_parts.append(f"World setting detail: {visual_setting[:200]}")

    context_block = "\n".join(context_parts)

    user_prompt = f"""\
Create a detailed visual description for the background artwork of a book cover.

NOVEL CONTEXT:
{context_block}

STYLE DIRECTION: {preset['description']}
Art style modifiers: {preset['art_modifiers']}

Generate a vivid, specific visual description for the cover artwork. \
Focus on composition, lighting, color palette, atmosphere, and focal subjects. \
Remember: NO text, NO typography, NO lettering of any kind in the image."""

    logger.info("Generating art direction prompt (style=%s)", style_preset)

    response = await llm_client.generate(
        prompt=user_prompt,
        system_prompt=ART_DIRECTOR_SYSTEM,
        max_tokens=500,
        temperature=0.7,
    )

    art_prompt = response.content.strip()

    # Append style modifiers to ensure the image generator applies them
    full_prompt = f"{art_prompt}\n\nStyle: {preset['art_modifiers']}. No text, no words, no lettering."

    logger.info("Art direction prompt generated (%d chars)", len(full_prompt))
    return full_prompt


async def generate_back_cover_blurb(
    config: Dict[str, Any],
    llm_client: Any,
    existing_blurb: str = "",
) -> str:
    """Generate or refine a back-cover blurb (150-200 words).

    If an existing blurb is provided (e.g. from BookOps 01_positioning.md),
    refines it to back-cover format. Otherwise generates fresh from synopsis.

    Args:
        config: Project config.yaml dict.
        llm_client: An LLM client with async generate() method.
        existing_blurb: Pre-existing blurb text to refine.

    Returns:
        Back cover blurb text (150-200 words).
    """
    title = config.get("title", "Untitled")
    genre = config.get("genre", "")
    synopsis = config.get("synopsis", "")

    if existing_blurb:
        prompt = f"""\
Refine this book blurb for the BACK COVER of a {genre} novel titled "{title}".

EXISTING BLURB:
{existing_blurb}

Requirements:
- 150-200 words
- Hooks the reader, ends on a question or cliffhanger
- No spoilers beyond the first act
- No quotes, review blurbs, or meta-commentary
- Just the blurb text, no preamble"""
    else:
        prompt = f"""\
Write a compelling back-cover blurb for a {genre} novel titled "{title}".

SYNOPSIS:
{synopsis[:500]}

Requirements:
- 150-200 words
- Hooks the reader, ends on a question or cliffhanger
- No spoilers beyond the first act
- No quotes, review blurbs, or meta-commentary
- Just the blurb text, no preamble"""

    response = await llm_client.generate(
        prompt=prompt,
        system_prompt="You write compelling book jacket copy for major publishers. Output only the blurb text.",
        max_tokens=400,
        temperature=0.7,
    )

    return response.content.strip()
