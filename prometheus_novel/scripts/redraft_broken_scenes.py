#!/usr/bin/env python3
"""Redraft broken scenes with full continuity context."""
import json
import sys
import re
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml
from prometheus_lib.llm.clients import OllamaClient

PROJECT = "the-bends"
MODEL = "qwen2.5:14b"

# Scene-specific continuity notes
SCENE_NOTES = {
    "ch05_s01": (
        "=== CRITICAL CONTINUITY NOTE ===\n"
        'The "first death" in this scene is NOT Dr. Aris Kade. Aris is alive and remains alive until chapter 10.\n'
        "The victim is an unnamed crew technician found in the utility corridor.\n"
        "Dr. Aris Kade does NOT appear in this scene. Elena discovers the body and suspects foul play.\n"
        "Mara arrives and they realize this death is physically impossible given the sealed sections."
    ),
    "ch05_s02": (
        "=== CONTINUITY NOTE ===\n"
        "Elena just found an unnamed crew technician dead in the utility corridor.\n"
        "Dr. Aris Kade is ALIVE. Elena is investigating the death privately.\n"
        "She begins to suspect the disaster was deliberate. Her buried scandal weighs on her.\n"
        "She does NOT go looking for Aris. She reviews evidence alone in her cabin."
    ),
    "ch06_s01": (
        "=== CONTINUITY NOTE ===\n"
        'Dr. Aris Kade is ALIVE and active. He blocks Elena from accessing life support diagnostics "for safety."\n'
        "Elena is suspicious of him but does not confront him yet. She pockets a broken seal as evidence.\n"
        "A crew technician was found dead in the previous chapter."
    ),
    "ch09_s01": (
        "=== CONTINUITY NOTE ===\n"
        "Elena and Jax are alone in the Velvet Lounge, late at night.\n"
        "Elena admits her past complicity: she buried evidence in a previous scandal. Someone died because of it.\n"
        "This is deeply personal: shame vs intimacy.\n"
        "Jax forgives her imperfectly. They become a team.\n"
        "At this point: sabotage is confirmed, Aris is the prime suspect, Elena has been accused by the group."
    ),
    "ch11_s02": (
        "=== CONTINUITY NOTE ===\n"
        "They are inside the diving bell beginning ascent. Not everyone fits: someone was left behind.\n"
        "Elena made the choice about who stays. This is the emotional climax.\n"
        "They rise through dark water. Grief hits while action is still required.\n"
        "Bioluminescence outside the glass. Elena is fundamentally changed.\n"
        "The scene should feel like both loss and release. End on a concrete image, not repetition."
    ),
    "ch12_s02": (
        "=== CONTINUITY NOTE ===\n"
        "Elena is on the rescue vessel, post-decompression. She stands at a corridor window at night, looking at the ocean surface.\n"
        "The temptation of performance vs the relief of truth. Her old persona tries to reassert; she refuses.\n"
        "This is the FINAL scene of the novel. It must feel like a quiet, earned ending.\n"
        "She breathes. She lets it be enough. No grand gesture, no audience.\n"
        "End on a single concrete image: not repetition, not summary."
    ),
}


def load_project():
    base = Path(__file__).resolve().parent.parent / "data" / "projects" / PROJECT
    with open(base / "pipeline_state.json", "r", encoding="utf-8") as f:
        state = json.load(f)
    with open(base / "config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return state, config, base


def get_outline_entry(outline, chapter, scene_num):
    for ch in outline:
        if not isinstance(ch, dict):
            continue
        if ch.get("chapter_number", ch.get("chapter", 0)) != chapter:
            continue
        for sc in ch.get("scenes") or []:
            if isinstance(sc, dict) and sc.get("scene_number", sc.get("scene", 0)) == scene_num:
                return sc
    return {}


def build_prompt(entry, config, extra_context=""):
    pov = entry.get("pov", "Elena Vance")
    loc = entry.get("location", "")
    purpose = entry.get("purpose", "")
    conflict = entry.get("central_conflict", "")
    opening_hook = entry.get("opening_hook", "")
    outcome = entry.get("outcome", "")
    tension = entry.get("tension_level", 5)
    pacing = entry.get("pacing", "medium")
    dialogue_notes = entry.get("dialogue_notes", "")
    diff = entry.get("differentiator", "")
    char_goal = entry.get("character_scene_goal", "")
    synopsis = config.get("synopsis", "")
    style = config.get("writing_style", "")
    tone = config.get("tone", "")
    avoid = config.get("avoid", "")

    return f"""You are writing a scene for a thriller novel set in a luxury underwater habitat (the Aethelgard) 600ft deep in the North Atlantic.

=== STORY ===
{synopsis}

=== CHARACTERS (ALL ALIVE unless stated otherwise) ===
- Elena Vance: crisis PR fixer, narrator (first person). Hyper-competent, emotionally avoidant.
- Jax Vale: disgraced influencer, Elena's client. Performative, cracking under pressure.
- Dr. Aris Kade: habitat systems expert. Cold, precise. THE HIDDEN SABOTEUR (Elena does not know yet).
- Captain Mara Sato: habitat commander. Blunt, physical, keeps people moving.
- Linnea Shaw: habitat architect. Proud, defensive.
- Priya Nand: med tech. Practical, observant.
- Silas Greer: billionaire sponsor. Smooth, calculating.
- MOTHER: habitat AI system.

{extra_context}

=== THIS SCENE ===
Location: {loc}
POV: {pov} (first person present tense, "I")
Purpose: {purpose}
What makes it unique: {diff}
Character goal: {char_goal}
Central conflict: {conflict}
Opening hook: {opening_hook}
Outcome: {outcome}
Tension: {tension}/10, Pacing: {pacing}
Dialogue notes: {dialogue_notes}

=== STYLE ===
{style}
Tone: {tone}

=== RULES ===
- FIRST PERSON PRESENT TENSE as {pov}. "I" = {pov}.
- Never refer to {pov} by name in narration.
- When describing another character, use THEIR name and THEIR pronouns. "His hands" not "my hands" for someone else.
- Open with ACTION or DIALOGUE
- At least 4 lines of quoted dialogue spread across the scene
- No preamble, no title, no meta-commentary
- Target: 800-1000 words
- AVOID: {avoid}
- Write ONLY in English
- Do NOT repeat phrases. Each sentence must be unique.
- End the scene with a concrete action, image, or line of dialogue. NOT an emotional summary. NOT a repeated phrase.

Write the complete scene now:"""


def strip_loops(text):
    """Remove phrase loops (same 10+ char sequence repeated 3+ times)."""
    # Catch tail loops
    words = text.split()
    if len(words) > 20:
        tail = " ".join(words[-50:]).lower()
        # Check if last 5 words repeat
        last5 = " ".join(words[-5:]).lower()
        count = tail.count(last5)
        if count >= 3:
            # Find where the loop starts and truncate
            for i in range(len(words) - 10, 0, -1):
                chunk = " ".join(words[i:i+5]).lower()
                if chunk != last5:
                    text = " ".join(words[:i+5])
                    break
    return text


async def main():
    state, config, base = load_project()
    scenes = state.get("scenes", [])
    outline = state.get("master_outline", [])
    sid_map = {sc.get("scene_id", ""): i for i, sc in enumerate(scenes)}

    client = OllamaClient(MODEL)
    await client._ensure_initialized()
    print(f"Using model: {MODEL}\n")

    targets = list(SCENE_NOTES.keys())

    for sid in targets:
        idx = sid_map.get(sid)
        if idx is None:
            print(f"  {sid}: NOT FOUND, skipping")
            continue

        sc = scenes[idx]
        entry = get_outline_entry(outline, sc["chapter"], sc["scene_number"])
        if not entry:
            print(f"  {sid}: No outline entry, skipping")
            continue

        # Get previous scene ending for continuity
        prev_text = ""
        if idx > 0:
            prev_content = scenes[idx - 1].get("content", "")
            prev_text = " ".join(prev_content.split()[-60:])

        extra = SCENE_NOTES[sid]
        if prev_text:
            extra += f"\n\n=== PREVIOUS SCENE ENDING (continue from here) ===\n...{prev_text}"

        prompt = build_prompt(entry, config, extra)
        old_words = len(sc.get("content", "").split())
        print(f"  Drafting {sid} (was {old_words}w)...")

        resp = await client.generate(prompt=prompt, max_tokens=6000, temperature=0.7)
        text = strip_loops(resp.content.strip())
        words = len(text.split())

        # Validate
        alpha = [c for c in text if c.isalpha()]
        non_latin = sum(1 for c in alpha if ord(c) > 127) / len(alpha) if alpha else 1.0

        if non_latin > 0.1 or words < 100:
            print(f"    Retry ({non_latin:.1%} non-Latin, {words}w)...")
            resp = await client.generate(prompt=prompt, max_tokens=6000, temperature=0.7)
            text = strip_loops(resp.content.strip())
            words = len(text.split())

        sc["content"] = text
        print(f"  OK: {sid} -> {words}w")

    # Save
    with open(base / "pipeline_state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {base / 'pipeline_state.json'}")


if __name__ == "__main__":
    asyncio.run(main())
