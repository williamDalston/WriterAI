#!/usr/bin/env python3
"""Fix ch09_s01 only — Sato double removal with strict word cap."""
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
• Aethelgard is a deep-sea habitat. Hard physics only. No supernatural elements.
• Elena Vance (narrator, female, I/my/me): media consultant, first-person present tense.
• Jax Vale (male): her client. Dr. Aris Kade (male): secret behavioral psychologist running
  stress experiments for Silas. Captain Mara Sato (female): runs the crew.
• Aris engineers crises to study crew responses. MOTHER (habitat AI) has safety overrides.
• No character named "Marcus" exists.

RULES: First person present tense. "my" = only Elena. Gender locks enforced.

CRITICAL: Keep the rewrite to 500-600 words MAX. Tight, lean prose. No padding."""

NOTES = """MAJOR REWRITE — remove the literal Sato doppelganger. Replace with grounded thriller:

1. Elena, Jax, and Dr. Kade are in the Spine Corridor. Tension is high.
2. A figure emerges from a maintenance access panel in dim emergency lighting.
   Elena's vision blurs (CO2 headache — she's had pressure behind her eyes all day).
   For a split second she thinks it looks like Sato — same build, same silhouette —
   but it's someone in maintenance coveralls. Face obscured. Moves fast.
3. The figure uses a stolen override key to seal the corridor. Sato checks her belt —
   her key is gone. Pickpocketed.
4. MOTHER's voice: "Section C sealed. Atmospheric adjustment in progress. Duration: sixty seconds."
5. Air thins. People panic. Elena counts. Sixty seconds of terror.
6. MOTHER's safety override kicks in — air normalizes. But doors stay locked (manual override needed).
7. Elena realizes: this was staged. Calibrated. Someone is TESTING them. Not trying to kill them.
   The crew tech who died was the experiment going wrong.

Keep: Paranoia atmosphere, Jax's fear, the key being stolen, doors locking.
Remove: Literal double, "too-wide smile", mechanical voice, "same pale scar", multiple Satos.
DO NOT include Marcus. He does not exist.

OUTPUT ONLY THE REWRITTEN SCENE. 500-600 words. No commentary."""


async def main():
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    scenes = state.get("scenes", [])

    # Find ch09_s01
    target = None
    for scene in scenes:
        if scene.get("scene_id") == "ch09_s01":
            target = scene
            break

    if not target:
        print("ERROR: ch09_s01 not found")
        return

    content = target.get("content", "")
    orig_wc = len(content.split())
    print(f"ch09_s01: {orig_wc} words. Rewriting...")

    client = AnthropicClient(model_name="claude-sonnet-4-5-20250929")

    prompt = f"""{NOTES}

=== CURRENT SCENE (ch09_s01) ===
{content}

=== OUTPUT REWRITTEN SCENE (500-600 words, prose only) ==="""

    response = await client.generate(prompt, system_prompt=SYSTEM, max_tokens=4000, temperature=0.3)
    fixed = response.content.strip() if response else ""

    for marker in ("Here is", "Here's", "===", "Below is", "Rewritten"):
        if fixed.lower().startswith(marker.lower()):
            fixed = fixed[len(marker):].strip()
            if fixed.startswith(":"):
                fixed = fixed[1:].strip()

    new_wc = len(fixed.split())
    print(f"Result: {new_wc} words ({new_wc/orig_wc:.0%} of original)")

    if 300 <= new_wc <= 800:
        target["content"] = fixed
        STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        print("Saved.")
    else:
        print(f"WARN: {new_wc} words out of range, not saved.")


if __name__ == "__main__":
    asyncio.run(main())
