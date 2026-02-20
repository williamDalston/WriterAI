#!/usr/bin/env python3
"""Pass 2: Fix remaining pronoun confusion in scenes missed by pass 1."""
import asyncio
import json
import sys
import os
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(usecwd=True))
from prometheus_lib.llm.clients import AnthropicClient

PROJECT = Path(__file__).resolve().parent.parent / "data" / "projects" / "the-bends"
STATE_FILE = PROJECT / "pipeline_state.json"
MODEL = "claude-sonnet-4-5-20250929"

FIX_PROMPT = """You are an expert prose editor performing SURGICAL fixes on a first-person thriller novel.
The narrator is Elena Vance, a 34-year-old WOMAN. The narration is FIRST PERSON PRESENT TENSE.

FIX ONLY pronoun ownership errors. Preserve the story, dialogue, and plot EXACTLY.

RULE: "my" = ONLY Elena's body/possessions. Other characters' body parts belong to THEM.

Common errors to fix:
- "He wipes my palms on his thighs" → "He wipes his palms on his thighs"
- "I meet my eyes" (when meeting someone else's eyes) → "I meet his eyes" / "I meet her eyes"
- "My face is neutral" (describing Aris/Jax) → "His face is neutral"
- "My voice barely carries" (Jax speaking) → "His voice barely carries"
- "My breath fogging it up" (Jax's breath) → "his breath fogging it up"
- "My hand moves toward the console" (Aris's hand) → "His hand moves toward the console"
- "My jaw works" (about another character) → "His jaw works"
- "My gaze" (about another character) → "his gaze"
- "He stops picking at my hand" → "He stops picking at his hand"

CONTEXT: Elena = I/my/me (female). Jax Vale = he/his/him (male). Aris Kade = he/his/him (male).
Mara Sato = she/her (female). Priya = she/her. Silas = he/his/him.

Output ONLY the corrected prose. No commentary. No headers."""

SCENES_TO_FIX = {
    "ch05_s02": """Fix pronoun confusion:
- "My cheek pressed flat against the grating" (dead tech's cheek) → "His cheek pressed flat"
- "My face is calm. Too calm." (describing Aris) → "His face is calm. Too calm."
- Any other "my" used for other characters' body parts.""",

    "ch06_s01": """Fix SEVERE pronoun confusion throughout:
- "He wipes my palms on his thighs" → "He wipes his palms on his thighs"
- "I meet my eyes" (meeting Aris's eyes) → "I meet his eyes"
- "My face is neutral, but my eyes track every movement I make" (Aris watching) → "His face is neutral, but his eyes track every movement I make"
- "My voice is quieter" (Aris speaking) → "His voice is quieter"
- "My hand moves toward the console" (Aris's hand) → "His hand moves toward the console"
This scene has many instances. Fix ALL of them.""",

    "ch06_s02": """Fix pronoun confusion:
- "Jax stands too close to the glass, my breath fogging it up" → "his breath fogging it up"
- "He turns. My face catches the unstable light" → "His face catches the unstable light"
- "He stops picking at my hand" → "He stops picking at his hand"
- "there's less performance in my gaze" (Jax's gaze) → "his gaze"
Fix ALL instances where "my" refers to Jax's body parts.""",

    "ch09_s01": """Fix pronoun confusion:
- "My jaw works like he's chewing glass" (about Jax) → "His jaw works like he's chewing glass"
- "My voice barely carries. He's asking his reflection" → "His voice barely carries."
Fix ALL instances where "my" is used for another character's body.""",
}


async def main():
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    scenes = state.get("scenes", [])
    print(f"Loaded {len(scenes)} scenes")

    client = AnthropicClient(model_name=MODEL)
    print(f"Using model: {MODEL}\n")

    fixed_count = 0
    for scene in scenes:
        sid = scene.get("scene_id", "")
        if sid not in SCENES_TO_FIX:
            continue

        content = scene.get("content", "")
        if not content:
            continue

        notes = SCENES_TO_FIX[sid]
        print(f"  [{sid}] Fixing pronoun confusion...")

        prompt = f"""{notes}

=== SCENE TO FIX ({sid}) ===
{content}

=== OUTPUT THE CORRECTED SCENE (prose only) ==="""

        response = await client.generate(
            prompt,
            system_prompt=FIX_PROMPT,
            max_tokens=8000,
            temperature=0.2,
        )
        fixed = response.content.strip() if response else ""

        # Strip preamble
        for marker in ("Here is", "Here's", "Fixed scene:", "Fixed version:", "===", "Below is"):
            if fixed.lower().startswith(marker.lower()):
                fixed = fixed[len(marker):].strip()
                if fixed.startswith(":"):
                    fixed = fixed[1:].strip()

        if not fixed or len(fixed) < 50:
            print(f"    WARNING: empty response, keeping original")
            continue

        orig_wc = len(content.split())
        new_wc = len(fixed.split())
        retention = new_wc / orig_wc if orig_wc > 0 else 0

        if retention < 0.40:
            print(f"    WARNING: collapsed ({orig_wc} -> {new_wc}), keeping original")
            continue

        scene["content"] = fixed
        fixed_count += 1
        print(f"    FIXED: {orig_wc} -> {new_wc} words ({retention:.0%} retention)")

    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDone: {fixed_count} scenes fixed")
    print(f"State saved to {STATE_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
