#!/usr/bin/env python3
"""Fix all quality issues in the-bends manuscript using Claude Sonnet.

Issues:
1. Supernatural elements in ch01_s02 (bloated hand) and ch12_s02 (sea creature)
2. Pervasive pronoun confusion (~40+ instances across all scenes)
3. Tense drift (mixed past/present when config says present)
4. Phantom characters (Dane, Chen, Okafor not in roster)
"""
import asyncio
import json
import sys
import os
import re
from pathlib import Path

# Fix encoding on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to path + load .env
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(usecwd=True))
from prometheus_lib.llm.clients import AnthropicClient

PROJECT = Path(__file__).resolve().parent.parent / "data" / "projects" / "the-bends"
STATE_FILE = PROJECT / "pipeline_state.json"
MODEL = "claude-sonnet-4-5-20250929"

# Scenes needing full redraft (supernatural content)
REDRAFT_SCENES = {
    1: """CRITICAL — THIS SCENE MUST BE COMPLETELY REWRITTEN:
The current version ends with a SUPERNATURAL HORROR sequence: a bloated gray-white hand pushing
through a torn bulkhead, joints bending wrong, pulling itself through torn metal. This VIOLATES
the novel's world rules ("Hard physics only" / "avoid: supernatural monsters").

REWRITE THE ENTIRE SCENE following these rules:
- This is the TRANSFER CHAMBER / BOARDING sequence. Elena and crew seal into the Aethelgard.
- NO supernatural elements. NO bloated hands. NO body horror. NO creatures pushing through walls.
- Hard science only: saturation diving, pressure equalization, sealed hatches, mechanical sounds.
- The tension comes from claustrophobia, interpersonal friction, and the unknown depth.
- End with an ominous but REALISTIC beat (system warning, pressure anomaly, strange mechanical sound).
- First person present tense from Elena's POV ("I" = Elena, a woman).
- Characters present: Mara (captain, female), Jax (male), Dr. Aris Kade (male).
- KEEP the same approximate word count (~540 words).""",

    23: """CRITICAL — THIS SCENE MUST BE COMPLETELY REWRITTEN:
The current version ends with a SUPERNATURAL SEA CREATURE: a massive pale segmented thing rising
toward the glass with a milky-white eye the size of a head. Jax screams. This VIOLATES the
novel's world rules ("Hard physics only" / "avoid: supernatural monsters").

REWRITE THE ENTIRE SCENE following these rules:
- This is the FINAL SCENE. Elena is on the rescue vessel after escaping the Aethelgard.
- NO sea creatures. NO monsters. NO supernatural elements. NO milky-white eyes. NO tentacles.
- Hard physics only. The ocean is dark, empty, indifferent — not alive with monsters.
- End with Elena's internal reckoning: who she is without the mask, without the performance.
- The dread comes from what she now knows about herself and what she did, not from external horror.
- First person present tense from Elena's POV ("I" = Elena, a woman).
- Jax is alive but silent/traumatized. Mara is present. No Aris (he was unmasked as saboteur).
- Fix ALL pronoun issues: Elena is female, "I/my/me" for her own body. "his" for Jax.
- KEEP the same approximate word count (~710 words).""",
}

# Scene-specific notes for known problem scenes
SCENE_NOTES = {
    "ch02_s02": """CRITICAL PRONOUN FIX NEEDED: The second half of this scene switches from
first-person "I" to third-person "he/him/his" for Elena. Elena is FEMALE and the narrator.
ALL narration must use "I/my/me" for Elena. "He/his/him" is ONLY for male characters (Jax, Aris, Silas).
Examples of what's WRONG in this scene:
- "Each breath coats his throat" → "Each breath coats my throat"
- "His boots leave prints" → "My boots leave prints"
- "if he stood on the cot he could touch it" → "if I stood on the cot I could touch it"
- "He pulls air in through his nose" → "I pull air in through my nose"
- "He closes his eyes" → "I close my eyes"
- "He's on his feet before he can think" → "I'm on my feet before I can think"
Fix EVERY instance of he/him/his that refers to Elena.""",

    "ch05_s01": """THREE ISSUES TO FIX:
1. PHANTOM CHARACTER: "Dane" is NOT in the character roster. Replace with "a crew tech" or
   "one of the maintenance crew" — do NOT name him. Keep the death scene but remove the name.
2. TENSE: The entire scene is in PAST TENSE. Convert ALL narration to PRESENT TENSE.
   "Dane's hand was still reaching" → "The tech's hand is still reaching"
   "I found him" → "I find him"  "Priya knelt" → "Priya kneels"
3. PRONOUN: "My face is calm. Too calm." — if this describes Aris's face, use "His face".""",

    "ch07_s02": """PRONOUN FIXES NEEDED:
- "The words die somewhere between my brain and his tongue" → Elena's tongue = "my tongue"
- At the end: after Jax speaks ("Elena, the backup wasn't unplugged"), "My voice shakes" should be
  "His voice shakes" if it's Jax speaking, or clarify attribution.
- Fix any other pronoun confusion where "his" is used for Elena's body parts.""",

    "ch12_s02": """PRONOUN FIXES (in addition to supernatural rewrite):
- "My hands curl tight, nails digging crescents into his palms" → "my palms"
- "I drop his hand" → "I drop his hand" is OK if dropping Jax's hand, but verify context
- "I breathe in through his nose" → "my nose"
- "But I stop halfway up his arm" → "my arm"
- Elena is FEMALE. All her body parts = "my". Jax's body parts = "his".""",
}

# The main fix prompt - comprehensive, with examples
FIX_PROMPT = """You are an expert prose editor performing SURGICAL fixes on a first-person thriller novel.
The narrator is Elena Vance, a 34-year-old WOMAN. The narration is FIRST PERSON PRESENT TENSE ("I walk", "I see").

FIX these issues. Preserve the story, dialogue, and plot EXACTLY. Change ONLY what is broken.

RULE 1 — FIRST PERSON POV:
All narration must be first person. Elena = "I/my/me/mine".
WRONG: "He closes his eyes. Keeps counting." (when describing Elena)
RIGHT: "I close my eyes. Keep counting."
WRONG: "His boots leave prints in the condensation."  (when describing Elena)
RIGHT: "My boots leave prints in the condensation."
WRONG: "She walks through the corridor" (when narrating Elena's actions)
RIGHT: "I walk through the corridor"

RULE 2 — PRONOUN OWNERSHIP:
"my" = ONLY Elena's body/possessions. Other characters' body parts belong to THEM.
WRONG: "He wiped my palms" → RIGHT: "He wiped his palms"
WRONG: "Jax doesn't lift my head" → RIGHT: "Jax doesn't lift his head"
WRONG: "My jaw tightened" (about Aris) → RIGHT: "His jaw tightened"
Elena (female): I/my/me. Jax (male): he/his/him. Mara (female): she/her. Aris (male): he/his/him.

RULE 3 — PRESENT TENSE:
Narration = present tense. Past tense ONLY inside dialogue or explicit memories/flashbacks.
WRONG: "I walked down the corridor" → RIGHT: "I walk down the corridor"
WRONG: "She turned to face me" → RIGHT: "She turns to face me"
WRONG: "The lights flickered" → RIGHT: "The lights flicker"

RULE 4 — CHARACTER ROSTER:
Only these characters exist: Elena Vance, Jax Vale, Captain Mara Sato, Linnea Shaw, Priya Nand,
Silas Greer, Dr. Aris Kade, MOTHER (habitat AI).
Replace "Dane" → "a crew tech" or "the technician". Remove "Chen" and "Okafor".

RULE 5 — NO SUPERNATURAL:
Hard physics only. No monsters, creatures, supernatural elements, bloated hands, milky eyes, tentacles.

Output ONLY the corrected prose. No commentary. No headers. No explanations. No "Here is the fixed version"."""


async def fix_scene(client, scene_text: str, scene_id: str, extra_notes: str = "") -> str:
    """Send scene through Claude for targeted fixes."""
    prompt = f"""{extra_notes}

=== SCENE TO FIX ({scene_id}) ===
{scene_text}

=== OUTPUT THE CORRECTED SCENE BELOW (prose only, no commentary) ==="""

    response = await client.generate(
        prompt,
        system_prompt=FIX_PROMPT,
        max_tokens=8000,
        temperature=0.2,
    )
    fixed = response.content.strip() if response else ""

    # Strip any preamble the model might add
    for marker in ("Here is", "Here's", "Fixed scene:", "Fixed version:", "===", "Below is"):
        if fixed.lower().startswith(marker.lower()):
            fixed = fixed[len(marker):].strip()
            # Remove trailing colon if present
            if fixed.startswith(":"):
                fixed = fixed[1:].strip()

    return fixed


async def main():
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    scenes = state.get("scenes", [])
    print(f"Loaded {len(scenes)} scenes from pipeline_state.json")

    client = AnthropicClient(model_name=MODEL)
    print(f"Using model: {MODEL}")

    fixed_count = 0
    skipped_count = 0

    for i, scene in enumerate(scenes):
        sid = scene.get("scene_id", f"scene_{i}")
        content = scene.get("content", "")
        if not content or len(content) < 50:
            print(f"  [{sid}] SKIP (empty/short)")
            skipped_count += 1
            continue

        # Check if this scene needs a full redraft (supernatural content)
        extra = ""
        action = "FIX"
        if i in REDRAFT_SCENES:
            extra = REDRAFT_SCENES[i]
            action = "REDRAFT"
        elif sid in SCENE_NOTES:
            extra = SCENE_NOTES[sid]
            action = "TARGETED FIX"
        else:
            # Broad detection — send everything that might have issues
            has_pronoun_my = bool(re.search(
                r'\b(?:He|She)\b[^.!?]{0,60}\bmy\s+(?:voice|eyes|face|head|jaw|hand|hands|fingers|palms|back|breath|gaze|throat|shoulders|arms|knees|legs|wrist|temples|forehead|tongue|feet|chest|stomach|spine|neck|hip|hips|skin|hair|mouth|nose|ear|ears|lip|lips)\b',
                content
            ))
            # Detect third-person narration of Elena (he/his/him where Elena is narrator)
            has_third_person_elena = bool(re.search(
                r'\bElena (?:walked|followed|turned|moved|stepped|looked|said|ran|stood|reached|pulled|pushed|grabbed|leaned|stared|stopped|started|watched|realized|noticed)\b',
                content
            ))
            has_phantom = bool(re.search(r'\bDane\b|\bChen\b|\bOkafor\b', content))

            # Tense check: count past vs present verbs in narration
            narration = re.sub(r'["\u201c][^"\u201d]*["\u201d]', '', content)
            past_count = len(re.findall(
                r'\b(?:was|were|had|walked|turned|looked|moved|pulled|pushed|stood|felt|knew|saw|heard|took|came|went|found|thought|grabbed|leaned|stared|reached|stepped|stopped|started|watched|realized|noticed)\b',
                narration
            ))
            present_count = len(re.findall(
                r'\b(?:is|am|are|has|walks?|turns?|looks?|moves?|pulls?|pushes?|stands?|feels?|knows?|sees?|hears?|takes?|comes?|goes?|finds?|thinks?|grabs?|leans?|stares?|reaches?|steps?|stops?|starts?|watches?|realizes?|notices?)\b',
                narration
            ))
            total_verbs = past_count + present_count
            has_tense_issue = total_verbs >= 10 and past_count / total_verbs > 0.40

            # Broader pronoun check: "his [body]" in a sentence where no male character is named
            # (catches Elena referred to as "he/his")
            has_loose_pronoun = False
            sentences = re.split(r'[.!?]+', content)
            male_names = {"Jax", "Aris", "Silas", "Kade", "Vale", "Greer"}
            for sent in sentences:
                if re.search(r'\bhis\s+(?:throat|boots|eyes|breath|nose|mouth|face)\b', sent, re.IGNORECASE):
                    if not any(name in sent for name in male_names) and "I" in sent:
                        has_loose_pronoun = True
                        break

            issues = []
            if has_pronoun_my:
                issues.append("pronoun(my)")
            if has_loose_pronoun:
                issues.append("pronoun(his)")
            if has_phantom:
                issues.append("phantom")
            if has_third_person_elena:
                issues.append("3rd-person")
            if has_tense_issue:
                issues.append(f"tense({past_count}p/{present_count}pr)")

            if not issues:
                print(f"  [{sid}] CLEAN — no issues detected")
                skipped_count += 1
                continue

            extra = f"Issues detected in this scene: {', '.join(issues)}. Fix them per the rules above."

        print(f"  [{sid}] {action}: {extra[:80]}...")

        # Fix the scene
        orig_wc = len(content.split())
        fixed = await fix_scene(client, content, sid, extra)

        if not fixed or len(fixed) < 50:
            print(f"    WARNING: empty/short response, keeping original")
            skipped_count += 1
            continue

        new_wc = len(fixed.split())
        retention = new_wc / orig_wc if orig_wc > 0 else 0

        if retention < 0.40:
            print(f"    WARNING: scene collapsed ({orig_wc} -> {new_wc} words, {retention:.0%}), keeping original")
            skipped_count += 1
            continue

        scene["content"] = fixed
        fixed_count += 1
        print(f"    FIXED: {orig_wc} -> {new_wc} words ({retention:.0%} retention)")

    # Save
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDone: {fixed_count} scenes fixed, {skipped_count} skipped")
    print(f"State saved to {STATE_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
