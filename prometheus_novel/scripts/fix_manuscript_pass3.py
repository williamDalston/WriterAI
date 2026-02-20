#!/usr/bin/env python3
"""Pass 3: Comprehensive mechanical fix — pronouns, tense, repetition, duplicates.

Sends ALL 24 scenes through Claude Sonnet with strict rules and scene-specific notes.
"""
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

# ── System prompt: universal rules ────────────────────────────────────────────

SYSTEM_PROMPT = r"""You are a surgical prose editor. Fix ONLY the specific issues listed below.
Preserve the story, plot, dialogue, characters, and meaning EXACTLY. Do not add new content.
Do not remove plot beats. Change only what is broken.

═══ GENDER LOCKS (absolute, never deviate) ═══
• Elena Vance — FEMALE, first-person narrator → I / my / me / mine
• Jax Vale — MALE → he / him / his  (NEVER she/her for Jax)
• Captain Mara Sato — FEMALE → she / her / hers
• Dr. Aris Kade — MALE → he / him / his  (NEVER she/her for Aris/Kade)
• Linnea Shaw — FEMALE → she / her
• Priya Nand — FEMALE → she / her
• Silas Greer — MALE → he / him / his
• MOTHER — AI system, genderless → "it" or quoted speech

═══ FIRST-PERSON POV (Elena is the narrator) ═══
• All narration = Elena's internal voice → "I" / "my" / "me"
• "my" = ONLY Elena's body, thoughts, and possessions
• Other characters' body parts, voices, faces → his/her/their (NOT "my")
  WRONG: "He wiped my palms" (about Jax) → RIGHT: "He wiped his palms"
  WRONG: "My jaw works" (about Jax) → RIGHT: "His jaw works"
  WRONG: "My voice barely carries" (about Jax speaking) → RIGHT: "His voice barely carries"
  WRONG: "I reached into his tool kit" (Elena narrating Aris's action as her own) → fix attribution
• NEVER write "Elena walked" or "Elena turned" in narration — she IS Elena → "I walk" / "I turn"

═══ PRESENT TENSE (narration only) ═══
• All narration in PRESENT TENSE: "I walk", "She turns", "The light flickers"
• Past tense ONLY allowed inside:
  - Dialogue (characters may speak in past tense)
  - Brief past-perfect backstory framing ("had taken" for one sentence max)
  - Explicit memories clearly marked as such
• Fix all past-tense narration: "walked" → "walks", "turned" → "turns", etc.

═══ REPETITION CAPS (per scene) ═══
Replace excess occurrences with VARIED physical reactions. Don't just delete — substitute.
• "jaw clenches/tightens/works/locks" — MAX 1 per scene. Alternatives: throat tightens,
  teeth press together, molars ache, a muscle in the cheek twitches, lips press thin
• "adjust(s) sleeves" — MAX 1 per scene (Elena's signature). Alternatives: fingers
  find the hem, tug at a cuff, smooth fabric over the wrist
• "picks at cuticle" — MAX 1 per scene (Jax's tic). Alternatives: thumbnail scrapes
  the pad of his index finger, fingers drum his thigh, he flexes his hands
• "knuckles go/turn white" — MAX 1 per scene. Alternatives: grip tightens, fingers
  dig in, nails bite metal/palm/fabric
• "metallic/ozone taste" — MAX 1 per scene. Alternatives: stale recirculated air,
  the tang of machine oil, a chemical edge at the back of my throat
• "pulse hammers/pounds" — MAX 1 per scene. Alternatives: blood thuds in my ears,
  heartbeat kicks, adrenaline hums under my skin
• "lights flicker" — ONLY if it advances plot. If decorative, cut entirely.

═══ DIALOGUE VOICE (differentiate characters) ═══
If dialogue from different characters sounds identical (clipped fragments, rhetorical questions),
adjust to match their personality:
• Jax: emotionally reactive, self-aware, informal. Uses fillers ("Like, right now?"), self-deprecating.
• Mara: procedural, military-precise, minimal. States facts. Rarely questions. ("Oxygen's gone in forty minutes. Bell dock or nothing.")
• Aris: clinical, measured, deliberately provocative. Uses complete sentences with subtle menace.
• Silas: polished, PR-cadence, never wastes words. Pitches even accusations like keynote points.
• Linnea: sharp, slightly venomous, positioning. Always angling for relevance.
• Priya: professional calm masking fear. Medical precision in speech.
Do NOT rewrite all dialogue — only adjust where multiple characters sound identical.

═══ DUPLICATE TEXT ═══
If the same phrase, sentence, or beat appears twice in the scene, DELETE the second occurrence.
Do not add replacement text — just remove the duplicate.

═══ OUTPUT ═══
Return ONLY the corrected prose. No commentary. No headers. No "Here is the fixed version."
No markdown formatting. Just the clean scene text."""


# ── Scene-specific notes ──────────────────────────────────────────────────────

SCENE_NOTES = {
    "ch01_s01": """SCENE-SPECIFIC FIXES:
- "My jaw works." — Whose jaw? If Elena's, keep as "My jaw works." If someone else's, fix.
- "that same unsettling grin still plastered across my face" — if describing Jax's face, use "his face"
- Jax is MALE throughout. Fix any "her" for Jax.
- This is the DOCK BOARDING scene. Elena arrives at the dock, boards the Aethelgard.
- Check every "my" — does it refer to Elena's body or someone else's?""",

    "ch01_s02": """CRITICAL SCENE-SPECIFIC FIXES:
- "Jax had met us at the helipad after I'd found HER room empty, HER gear already loaded"
  → Jax is MALE. Fix to "his room empty, his gear already loaded"
- "I don't look at her. Her eyes are on the bulkhead" — who is "her"? If Mara, fine. If Jax, fix to "him/His"
- This scene should be a CONTINUATION of ch01_s01 (they've boarded, now going deeper into
  the habitat), NOT an alternative boarding via helicopter. Remove the helicopter reference
  if it contradicts the dock boarding in the previous scene. Replace with: they've descended
  from the deck into the transfer chamber for pressure equalization.
- Fix the opening to flow from the dock boarding: they've boarded and are now in the transfer
  chamber being sealed for descent/pressurization.
- Keep all the atmospheric detail (hatch sealing, airlock panel, stale air).
- Mara = she/her, Jax = he/him/his, Aris = he/him/his.""",

    "ch02_s01": """SCENE-SPECIFIC FIXES:
- "His voice barely carries. He's asking his reflection, not us." — if this is Jax, "his" is correct.
  But verify every pronoun carefully.
- Check MOTHER's dialogue attributions.
- Jax = MALE (he/him/his). Aris = MALE. Mara = FEMALE. Linnea = FEMALE.
- DUPLICATE TEXT: "the Velvet Lounge opens like a mouth" appears TWICE in this scene.
  Keep the FIRST occurrence only. Rewrite the second to avoid repetition (e.g., "the lounge
  swallows us" or just remove the simile).
- DIALOGUE VOICE: Give each character a distinct speech pattern:
  * Jax: emotionally reactive, self-referential, tries to charm ("This is insane." / "Like, right now?")
  * Linnea: pointed, slightly venomous, positioning herself ("I should prep him first.")
  * Mara: procedural, clipped, rule-citing ("Authenticity metrics. Priority one.")
  Preserve these distinctions. Don't make everyone speak in the same clipped fragments.""",

    "ch02_s02": """SCENE-SPECIFIC FIXES:
- This scene was previously fixed for massive he/him→I/my conversion. Verify it's clean.
- Elena is the narrator, alone in her cabin, then visits Jax's cabin.
- All narration = present tense.
- Jax = MALE (he/him/his).""",

    "ch03_s01": """CRITICAL SCENE-SPECIFIC FIXES:
- DUPLICATE PASSAGE: "My breath comes faster, shallow. The pulse of adrenaline. The body's
  way of saying, this is not a simulation." appears TWICE in this scene. DELETE the second
  occurrence entirely (keep the first).
- Dr. Aris Kade is MALE. Fix any "She" for Kade → "He".
  WRONG: "She looks at me like a data point" (about Kade) → "He looks at me like a data point"
- "I reached into his tool kit" — if this is Aris reaching, fix to "He reaches into his tool kit"
  (present tense + correct attribution). If Elena is reaching into Aris's kit: "I reach into his tool kit"
- Verify all pronouns: Jax=he, Aris=he, Elena=I.""",

    "ch03_s02": """SCENE-SPECIFIC FIXES:
- Aris Kade = MALE (he/him/his). Fix any she/her for Aris.
- Present tense narration throughout.
- Check for jaw/sleeve/cuticle repetition.""",

    "ch04_s01": """CRITICAL SCENE-SPECIFIC FIXES:
- "Dr. Kade watches me... She looks at me like a data point" → Kade is MALE: "He looks at me"
- "He tilts his head" (one line later) — correct for Kade, but the she→he switch mid-paragraph
  needs to be consistent. Make ALL Kade references he/him/his.
- "I reach into his tool kit and pull out a small device" — who is "I"? If Elena narrating her
  own action, fine. If describing Aris, fix to "He reaches into his tool kit and pulls out..."
- "My nails have left crescents in his palms" — whose palms? If Elena's own palms: "my palms".
  If someone else's: "his palms" is correct.
- Present tense: fix any past-tense narration.""",

    "ch04_s02": """SCENE-SPECIFIC FIXES:
- Check all pronouns. Jax=he, Mara=she, Aris=he, Silas=he, Linnea=she, Priya=she.
- "Jax's breath keeps hitching" — verify Jax is consistently male.
- Present tense narration.""",

    "ch05_s01": """SCENE-SPECIFIC FIXES:
- The dead tech should NOT be named (no "Dane"). Should be "the tech" / "a crew tech" / "the technician."
- Verify no phantom characters (no Dane, Chen, Okafor, Marcus).
- Present tense throughout narration.
- Check pronoun ownership carefully.""",

    "ch05_s02": """SCENE-SPECIFIC FIXES:
- "His cheek pressed flat against the grating" — whose cheek? If the dead tech: correct.
  If describing someone alive, verify context.
- "My face is calm. Too calm." — whose face? If Aris: "His face is calm."
- Aris = MALE. Present tense.""",

    "ch06_s01": """SCENE-SPECIFIC FIXES:
- Previously fixed for "He wipes my palms" → "his palms" etc. Verify all fixes held.
- Aris Kade = MALE throughout.
- Check for any remaining "my [body part]" that should be "his [body part]" for Aris.""",

    "ch06_s02": """SCENE-SPECIFIC FIXES:
- Previously fixed for "my breath fogging" → "his breath" etc. Verify.
- Jax = MALE throughout.
- Check observation deck scene for pronoun clarity.""",

    "ch07_s01": """SCENE-SPECIFIC FIXES:
- Mara slams Elena into the door frame. Check all physical actions are attributed correctly.
- Mara = FEMALE, Elena = I/my/me.
- Present tense narration.""",

    "ch07_s02": """SCENE-SPECIFIC FIXES:
- "The words die somewhere between my brain and my tongue" — if this is Elena trying to speak,
  "my tongue" is correct. Verify context.
- Silas = MALE. Jax = MALE.
- Check dialogue attribution at the end of the scene.""",

    "ch08_s01": """SCENE-SPECIFIC FIXES:
- Check body discovery scene. The deceased is an unnamed crew member.
- Mara = FEMALE, Priya = FEMALE.
- Present tense.""",

    "ch08_s02": """SCENE-SPECIFIC FIXES:
- Linnea = FEMALE. Aris = MALE.
- "The zipper moving. From the inside." — this is a plot beat, preserve it.
- Check pronoun consistency throughout.
- TENSE FIX: "Now I stood at the interface terminal, needing data more than I needed rest"
  → "Now I stand at the interface terminal, needing data more than I need rest"
- Fix ALL past-tense narration in this scene to present tense.""",

    "ch09_s01": """CRITICAL SCENE-SPECIFIC FIXES:
- Dr. Kade is MALE: "Dr. Kade's voice cuts in... She's holding a datapad" →
  "He's holding a datapad"
- PHANTOM CHARACTER: "Marcus" does NOT exist in the character roster.
  Remove "Marcus steps into the light" and the entire Marcus subplot. Replace with a
  generic crew member or remove the passage. Marcus's line about hydraulic fluid can
  be given to an unnamed maintenance crew member.
- "Captain Sato double/doppelganger" passage — this appears to be an intentional plot
  element. KEEP IT but ensure pronouns are correct. The real Sato and the double should
  both be she/her.
- Present tense narration. Fix all past-tense verbs.
- Jax = MALE throughout.""",

    "ch09_s02": """SCENE-SPECIFIC FIXES:
- Check all pronouns. Kade = MALE, Sato = FEMALE, Jax = MALE.
- Present tense.
- Repetition check.""",

    "ch10_s01": """SCENE-SPECIFIC FIXES:
- Aris = MALE. "His shoe scuffs against mine" — correct if referring to Aris's shoe.
- Mara = FEMALE.
- Present tense.
- Check "my" ownership throughout.""",

    "ch10_s02": """SCENE-SPECIFIC FIXES:
- Linnea = FEMALE, Mara = FEMALE, Jax = MALE.
- "Jax jerks my head" — should this be "Jax jerks HIS head"? If Jax is turning his own
  head: "Jax jerks his head". If someone jerks Elena's head: clarify.
- TENSE FIX: "The descent from life support to the ballast deck took less than a minute,
  but the temperature dropped ten degrees and the air turned thick" → Convert to present:
  "The descent from life support to the ballast deck takes less than a minute, but the
  temperature drops ten degrees and the air turns thick"
- Fix ALL past-tense narration to present tense.
- Check bell dock scene for plot clarity.""",

    "ch11_s01": """CRITICAL SCENE-SPECIFIC FIXES:
- "My voice cracks" — whose voice? If this is Jax speaking to Elena: "His voice cracks"
- "My jaw works like he's chewing through words" — mixed pronouns. If Elena's jaw:
  "My jaw works like I'm chewing through words". If Jax's: "His jaw works like he's chewing"
- Dr. Kade = MALE: "white coat" → fine. But verify all pronouns.
- "My eyes flick to my temple where he presses two fingers against the pulse point" —
  VERY confused. If Jax is pressing Elena's temple: "His eyes flick to my temple where
  he presses two fingers against the pulse point" or clarify who is doing what.
- Captain Sato = FEMALE.
- Present tense throughout.""",

    "ch11_s02": """SCENE-SPECIFIC FIXES:
- Diving bell scene. Multiple characters present: Elena, Jax, Silas, Sato, Kade, Priya, Linnea.
- Verify all pronouns match gender locks.
- "He" in this scene could be Jax, Silas, Kade, or any male. Ensure context makes clear
  which "he" is being referenced.
- Present tense.
- Check for Silas continuity (he stays behind, then appears in another bell — preserve
  this as a plot beat but ensure it reads clearly).""",

    "ch12_s01": """SCENE-SPECIFIC FIXES:
- Rescue/surface scene. Elena, Jax, Mara, Priya present.
- Jax = MALE, Mara = FEMALE, Priya = FEMALE.
- "his clasped hands" — verify whose hands.
- Present tense for narration.""",

    "ch12_s02": """SCENE-SPECIFIC FIXES:
- Final scene. Elena alone with her reflection.
- "My hands curl tight, nails digging crescents into my palms" — if Elena's: correct.
- Mara = FEMALE. Jax = MALE.
- This is the emotional climax. Preserve the introspective tone.
- Present tense.""",
}


async def fix_scene(client, scene_text: str, scene_id: str, notes: str) -> str:
    """Send scene through Claude for comprehensive fix."""
    prompt = f"""{notes}

=== SCENE ({scene_id}) ===
{scene_text}

=== OUTPUT THE CORRECTED SCENE (prose only, no commentary) ==="""

    response = await client.generate(
        prompt,
        system_prompt=SYSTEM_PROMPT,
        max_tokens=8000,
        temperature=0.15,
    )
    fixed = response.content.strip() if response else ""

    # Strip any preamble
    for marker in ("Here is", "Here's", "Fixed scene:", "Fixed version:",
                   "===", "Below is", "Corrected scene:", "Output:"):
        if fixed.lower().startswith(marker.lower()):
            fixed = fixed[len(marker):].strip()
            if fixed.startswith(":"):
                fixed = fixed[1:].strip()

    return fixed


async def main():
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    scenes = state.get("scenes", [])
    print(f"Loaded {len(scenes)} scenes from pipeline_state.json")

    client = AnthropicClient(model_name=MODEL)
    print(f"Using model: {MODEL}")
    print(f"Processing ALL {len(scenes)} scenes...\n")

    fixed_count = 0
    unchanged_count = 0

    for i, scene in enumerate(scenes):
        sid = scene.get("scene_id", f"scene_{i}")
        content = scene.get("content", "")
        if not content or len(content) < 50:
            print(f"  [{sid}] SKIP (empty)")
            continue

        notes = SCENE_NOTES.get(sid, "No scene-specific notes. Apply universal rules.")
        print(f"  [{sid}] Processing... ", end="", flush=True)

        orig_wc = len(content.split())
        fixed = await fix_scene(client, content, sid, notes)

        if not fixed or len(fixed) < 50:
            print(f"WARN: empty response, keeping original")
            unchanged_count += 1
            continue

        new_wc = len(fixed.split())
        retention = new_wc / orig_wc if orig_wc > 0 else 0

        if retention < 0.40:
            print(f"WARN: collapsed ({orig_wc}->{new_wc}), keeping original")
            unchanged_count += 1
            continue

        if retention > 1.30:
            print(f"WARN: inflated ({orig_wc}->{new_wc}), keeping original")
            unchanged_count += 1
            continue

        scene["content"] = fixed
        fixed_count += 1
        pct = f"{retention:.0%}"
        print(f"OK ({orig_wc}->{new_wc} words, {pct})")

    # Save
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDone: {fixed_count} scenes fixed, {unchanged_count} unchanged")
    print(f"State saved to {STATE_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
