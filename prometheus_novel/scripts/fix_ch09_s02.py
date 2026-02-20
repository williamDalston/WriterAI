#!/usr/bin/env python3
"""Fix ch09_s02 — remove surviving doppelganger, keep bridge content."""
import asyncio
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(usecwd=True))
from prometheus_lib.llm.clients import AnthropicClient

PROJECT = Path(__file__).resolve().parent.parent / "data" / "projects" / "the-bends"
STATE_FILE = PROJECT / "pipeline_state.json"

SYSTEM = """You are a senior fiction editor. Rewrite this scene following the rules below.

PLOT BIBLE:
• Aethelgard is a deep-sea habitat. Hard physics only. NO supernatural elements whatsoever.
• Elena Vance (narrator, female, I/my/me): media consultant, first-person present tense.
• Jax Vale (male): her client. Dr. Aris Kade (male): behavioral psychologist running
  stress experiments for Silas. Captain Mara Sato (female): runs the crew.
• Aris engineers crises to study crew responses. MOTHER (habitat AI) has safety overrides.
• There is NO doppelganger. There is NO double of Captain Sato. No one "wears her face."
  No one has a "too-wide smile." No mechanical voice copies. None of that exists.
• The previous scene (ch09_s01) established: a figure in maintenance coveralls used Sato's
  stolen override key to seal the corridor. MOTHER ran a 60-second atmospheric test.
  They survived because MOTHER's safety override kicked in.

RULES: First person present tense. "my" = only Elena. Gender locks enforced.
No character named Marcus exists. Dr. Kade = MALE (he/him/his).

CRITICAL: Output 800-900 words. Tight prose. No supernatural elements."""

NOTES = """REWRITE THIS SCENE to remove ALL remnants of the Sato doppelganger.

The scene currently has TWO parts:
1. GOOD — Bridge content (surviving the locked corridor, MOTHER safety override, manual hatch release)
2. BAD — The old doppelganger sequence ("wears her face like a stolen uniform," "too-wide smile,"
   "the double," magnetic seals, atmospheric venting by the double)

KEEP PART 1 (the bridge content at the start — surviving the venting, manual hatch release).
Then transition into the EXISTING GOOD CONTENT from this scene:
- Elena's confession to Jax about burying evidence ("I buried evidence once. Before all this.")
- Jax's reaction and their tentative alliance
- Walking through the dark corridor together
- The Spine Corridor encounter with Jax's tablet
- The servo motor / lock cycling sounds
- Elena confronting Jax about knowing something
- The emotional weight of their conversation

REMOVE COMPLETELY:
- Any reference to a "double" or doppelganger of Sato
- "wears her face like a stolen uniform"
- "printed a copy of the captain"
- "same sharp jawline, same pale scar"
- "the double's voice is Sato's voice but flatter, mechanical"
- "the double tilts her head"
- "the double smiles, too wide"
- "Only I do" (the double speaking)
- Any magnetic seals triggered by the double
- Any atmospheric venting commanded by the double

The scene should flow: bridge (survived the test) → Elena/Jax confession → walking together →
Spine Corridor tension → forward momentum toward the next chapter.

OUTPUT ONLY THE REWRITTEN SCENE. No commentary. 800-900 words."""


async def main():
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    scenes = state.get("scenes", [])

    target = None
    for scene in scenes:
        if scene.get("scene_id") == "ch09_s02":
            target = scene
            break

    if not target:
        print("ERROR: ch09_s02 not found")
        return

    content = target.get("content", "")
    orig_wc = len(content.split())
    print(f"ch09_s02: {orig_wc} words. Rewriting...")

    client = AnthropicClient(model_name="claude-sonnet-4-5-20250929")

    prompt = f"""{NOTES}

=== CURRENT SCENE (ch09_s02) ===
{content}

=== OUTPUT REWRITTEN SCENE (800-900 words, prose only) ==="""

    response = await client.generate(prompt, system_prompt=SYSTEM, max_tokens=6000, temperature=0.3)
    fixed = response.content.strip() if response else ""

    for marker in ("Here is", "Here's", "===", "Below is", "Rewritten"):
        if fixed.lower().startswith(marker.lower()):
            fixed = fixed[len(marker):].strip()
            if fixed.startswith(":"):
                fixed = fixed[1:].strip()

    new_wc = len(fixed.split())
    print(f"Result: {new_wc} words ({new_wc/orig_wc:.0%} of original)")

    if 500 <= new_wc <= 1100:
        target["content"] = fixed
        STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        print("Saved.")
    else:
        print(f"WARN: {new_wc} words out of range, not saved.")


if __name__ == "__main__":
    asyncio.run(main())
