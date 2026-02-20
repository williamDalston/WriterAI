#!/usr/bin/env python3
"""Redraft scenes with critical content breaks (plot/continuity/setting errors).

Targets:
  ch01_s01 - Elena reveals scandal too early + crate subplot goes nowhere
  ch02_s02 - Sunlight references at 600ft depth
  ch04_s02 - Truncated mid-sentence
  ch08_s01 - Jax killed (must be unnamed crew member)
  ch12_s01 - Aris casually present as survivor (he's the unmasked saboteur)
"""
import json
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml
from prometheus_lib.llm.clients import OllamaClient

PROJECT = "the-bends"
MODEL = "qwen2.5:14b"

# Scene-specific continuity notes that override/correct the broken content
SCENE_NOTES = {
    "ch01_s01": (
        "=== CRITICAL CONTINUITY NOTES ===\n"
        "This is the OPENING scene of the novel. Elena is at a surface dock, morning, before descending.\n"
        "Elena does NOT reveal her buried scandal here. She only hints at it much later (chapter 5, fully confessed chapter 9).\n"
        "There is NO mysterious crate. Do NOT invent subplots.\n"
        "Characters present: Elena (narrator), Jax Vale (her client, disgraced influencer), Silas Greer (billionaire sponsor),\n"
        "Captain Mara Sato (briefly), Dr. Aris Kade (observed from distance, silent, watching).\n"
        "Silas is MALE. Use HE/HIS for Silas. Never 'her voice' for Silas.\n"
        "Elena is hyper-competent and controlled. She sees through everyone's performance.\n"
        "The scene ends with them boarding. Elena notices Aris watching her like he already knows her.\n"
        "Tone: polished surface tension, PR world meets physical world. Elena is in control (for now)."
    ),
    "ch02_s02": (
        "=== CRITICAL SETTING NOTE ===\n"
        "They are 600 FEET UNDERWATER in the Aethelgard habitat. There is NO sunlight. NO dawn. NO morning light.\n"
        "The only light sources are: amber emergency lighting, fluorescent corridor strips, blue-white LEDs in cabins.\n"
        "Elena wakes to metallic groans. The habitat shifts and creaks. Condensation everywhere.\n"
        "She walks the Spine Corridor in near-darkness with only her wrist lamp.\n"
        "She returns to her cabin and counts breaths to manage fear she won't name.\n"
        "Minimal dialogue. Jax might briefly appear in the corridor but this is mostly internal.\n"
        "End on: Elena counting breaths until the shift alarm sounds, hating herself for needing the crutch.\n"
        "Sensory details: condensation on metal, recycled air taste, distant mechanical hums, pressure in ears."
    ),
    "ch04_s02": (
        "=== CONTINUITY NOTE ===\n"
        "This is 'First Accusations' — the group turns on each other in the Velvet Lounge.\n"
        "Silas proposes a 'public statement' out of habit. Elena realizes he can't stop performing even now.\n"
        "Silas is MALE — use HE/HIS/HIM.\n"
        "Dr. Aris Kade is present but stays quiet, observing, smiling without warmth.\n"
        "Elena tries to prevent hysteria but LOSES control of the room.\n"
        "Outcome: Elena is labeled a manipulator. Lines are drawn. Trust fractures.\n"
        "The scene must have a COMPLETE ending — a concrete image or action, NOT cut off mid-sentence.\n"
        "Do NOT end with a philosophical summary. End on a specific moment: a look, a gesture, a door closing."
    ),
    "ch08_s01": (
        "=== CRITICAL CONTINUITY NOTE ===\n"
        "JAX VALE IS ALIVE. He does NOT die in this scene or any scene.\n"
        "The person who dies is an UNNAMED crew member — found dead in the Med Nook during/after a blackout.\n"
        "The death has eerie logistics: the victim is in a sealed space that should have been inaccessible.\n"
        "MOTHER's logs around the time of death are corrupted.\n"
        "Characters present: Elena (narrator), Priya Nand (med tech, examining body), Mara (enforcing order).\n"
        "Jax may be mentioned but is NOT the victim. He is alive elsewhere.\n"
        "Elena's goal: keep Priya from breaking, keep the group functional, commit to hunting the saboteur.\n"
        "Conflict: fear wants superstition (cursed habitat); Elena demands evidence.\n"
        "Priya names medical symptoms. Mara enforces order. Elena interrogates gently, then sharply."
    ),
    "ch12_s01": (
        "=== CRITICAL CONTINUITY NOTE ===\n"
        "Dr. Aris Kade is NOT here. He was unmasked as the saboteur in chapter 10.\n"
        "He was left behind / detained / lost when they escaped in the diving bell.\n"
        "Survivors on the rescue vessel: Elena, Mara, Jax, possibly Priya. NOT Aris. NOT Silas (left behind).\n"
        "This is aftermath: decompression chamber on a rescue vessel. First clean air.\n"
        "Elena's phones return but she doesn't reach for hers first — that's the differentiator.\n"
        "Old persona tries to reassert (spin the story, manage the narrative).\n"
        "Elena REFUSES. She prepares to tell the truth publicly without spinning it.\n"
        "Quiet aftermath tone. Mara's exhaustion. Priya's trembling hands. Elena speaking plainly.\n"
        "End on a concrete moment, not a summary."
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
- Elena Vance: crisis PR fixer, narrator (first person). Hyper-competent, emotionally avoidant. 34 years old.
- Jax Vale: disgraced influencer, Elena's client. Male. Performative, cracking under pressure. Use HE/HIS.
- Dr. Aris Kade: habitat systems expert. Male. Cold, precise. THE HIDDEN SABOTEUR (Elena does not know yet). Use HE/HIS.
- Captain Mara Sato: habitat commander. Female. Blunt, physical, keeps people moving. Use SHE/HER.
- Linnea Shaw: habitat architect. Female. Proud, defensive. Use SHE/HER.
- Priya Nand: med tech. Female. Practical, observant. Use SHE/HER.
- Silas Greer: billionaire sponsor. MALE. Smooth, calculating. Use HE/HIS. Never "her" for Silas.
- MOTHER: habitat AI system. Genderless monotone voice.

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
- FIRST PERSON PRESENT TENSE as {pov}. "I" = {pov}. Use present tense verbs: "I walk", "I see", "he says". NOT past tense.
- Never refer to {pov} by name in narration.
- "my" refers ONLY to {pov}'s own body, voice, hands, eyes. For other characters, use THEIR name and THEIR pronouns.
- Example: "His hands clench" NOT "my hands clench" when describing Jax. "Her voice is sharp" NOT "my voice is sharp" when describing Mara.
- When Jax speaks, write: Jax says / his voice / he looks. NEVER: my voice / I say (unless Elena is speaking).
- Open with ACTION or DIALOGUE, not description
- At least 4 lines of quoted dialogue spread across the scene
- No preamble, no title, no meta-commentary
- Target: 800-1000 words
- AVOID: {avoid}
- Write ONLY in English
- Do NOT repeat phrases. Each sentence must be unique.
- End the scene with a concrete action, image, or line of dialogue. NOT an emotional summary. NOT a repeated phrase.

Write the complete scene now:"""


def strip_loops(text):
    """Remove phrase loops (same sequence repeated 3+ times in tail)."""
    words = text.split()
    if len(words) > 20:
        tail = " ".join(words[-50:]).lower()
        last5 = " ".join(words[-5:]).lower()
        count = tail.count(last5)
        if count >= 3:
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

        if non_latin > 0.05 or words < 200:
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
