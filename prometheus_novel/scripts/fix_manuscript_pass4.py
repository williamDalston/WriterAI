#!/usr/bin/env python3
"""Pass 4: Structural rewrites — plot coherence, MOTHER thread, Aris motivation,
setting physics, Sato double, body bag, Silas paradox, ending resolution.

Only touches scenes that need structural/creative changes (12 of 24).
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

# ── Plot Bible (injected into every rewrite) ─────────────────────────────────

PLOT_BIBLE = """
═══ PLOT BIBLE — GROUND TRUTH FOR ALL SCENES ═══

SETTING:
• The Aethelgard is a deep-sea habitat on the ocean floor, NOT visible from shore.
• Access: surface dock → boat to offshore platform → transfer chamber → pressurized
  descent into the habitat. The surface platform has a docking structure; the habitat
  itself is hundreds of meters below.
• Hard physics only. No supernatural elements. All strange events have rational causes:
  equipment sabotage, CO₂-induced perceptual distortion, or deliberate manipulation.

CHARACTERS & ROLES:
• Elena Vance (narrator, female, I/my/me): Media consultant and crisis fixer. NOT an
  engineer. She knows emergency protocols from mandatory onboarding briefing, but relies
  on specialists for technical work. Her skills are reading people, managing narratives,
  and staying calm under pressure.
• Jax Vale (male, he/him/his): Disgraced influencer. Elena's client. Emotionally reactive,
  self-aware, informal speech. Genuine underneath the performance.
• Captain Mara Sato (female, she/her): Former Navy, runs the habitat crew. Procedural,
  military-precise, minimal speech. Competent and pragmatic.
• Dr. Aris Kade (male, he/him/his): Officially the "systems specialist." Actually a
  behavioral psychologist hired by Silas to run covert stress-response experiments on
  the crew. He engineers crises to study human behavior under extreme pressure. Clinical,
  measured, deliberately provocative speech. His sabotage is calibrated — he pushes to
  the edge but has safety margins (mostly). The crew tech's death was NOT planned — it was
  the experiment going wrong, and Aris knows it.
• Silas Greer (male, he/him/his): Billionaire sponsor. Bankrolling the entire project.
  Jax's "rehabilitation" is the cover story. The real purpose: an extreme behavioral study
  — how people perform under escalating pressure when they can't leave. Silas wants the
  data and the content. Polished, PR-cadence speech. Always has an exit strategy.
• Linnea Shaw (female, she/her): Habitat architect. Sharp, slightly venomous, positioning.
• Priya Nand (female, she/her): Medical technician. Professional calm masking fear.
• MOTHER: The habitat's AI system. Monitors everything. Has been compromised/co-opted by
  Silas's project to feed data. Has hardcoded safety overrides that prevent actual lethal
  events (usually). Should appear periodically through the novel — not just in Ch2.

THE EXPERIMENT (Aris + Silas):
• Aris was hired by Silas before the mission began. His role as "systems specialist" is cover.
• Aris engineers escalating crises: environmental fluctuations, communication blackouts,
  locked doors, atmospheric venting — all designed to push people to their limits.
• MOTHER's safety overrides prevent most crises from becoming lethal. The crew tech's death
  was an accident — Aris's tampering with environmental controls had an unintended cascade.
• Silas has always had his own extraction plan: a second emergency evacuation bell in
  Section D that he arranged during construction.

NARRATION RULES:
• First person present tense (Elena). "I walk", "She turns", "He says."
• "my" = ONLY Elena's body/possessions. Others' body parts = his/her/their.
• No meta-narration ("No. Wait. Rewind."). Stay in scene.
"""

# ── Scene-specific structural rewrites ────────────────────────────────────────

SCENES_TO_FIX = {
    "ch01_s01": {
        "action": "LIGHT EDIT",
        "notes": """Fix setting physics ONLY. Keep everything else exactly the same.

CHANGE: "The Aethelgard glows just offshore like an underwater Taj Mahal, all chrome
and glass beneath the morning sun's hesitant rays."
→ The Aethelgard is deep underwater and NOT visible from shore. What Elena sees from the
dock is the SURFACE PLATFORM — a docking structure with the transfer chamber. Rewrite this
one sentence to describe the surface platform/dock instead, with Elena knowing the habitat
is far below. Something like: the offshore platform sits low on the water, all industrial
steel and guide cables disappearing into the deep.

Also fix: "they board the Aethelgard and descend toward the living quarters below deck"
→ They board the surface platform. The actual habitat descent comes in the next scene.

Keep all dialogue, character interactions, and atmosphere exactly the same."""
    },

    "ch04_s02": {
        "action": "ADD CONTENT",
        "notes": """Two additions to this scene. Keep everything else exactly the same.

ADD 1 — ELENA'S COMPETENCE JUSTIFICATION:
When Elena starts assessing the situation or checking systems, add a brief internal thought:
something like "The onboarding briefing covered emergency triage—read the indicators, report
to crew, don't touch what you don't understand." This justifies why a media consultant knows
emergency protocols without making her an engineer.

ADD 2 — MOTHER REFERENCE:
At some natural moment during the panic/discussion, add MOTHER speaking through the speakers.
Something like: MOTHER's voice cuts through the noise—"Atmospheric deviation detected.
Crew advisory: remain in designated safe zones." Keep it brief, functional, slightly eerie
in its calm. One or two sentences max.

Keep all existing dialogue and plot beats intact."""
    },

    "ch06_s01": {
        "action": "ADD CONTENT",
        "notes": """One small addition. Keep everything else exactly the same.

ADD — MOTHER MONITORING:
When Elena enters the Life Support Bay, add a brief MOTHER reference. The console shows
MOTHER's monitoring log, or MOTHER announces something through the speaker. Keep it to
1-2 sentences. Example: "The console screen scrolls with MOTHER's automated log—temperature,
pressure, O₂ levels, all annotated with timestamps I can't make sense of." Or MOTHER's
voice: "Life support bay accessed. Logging personnel." Something that reminds the reader
MOTHER exists and is watching everything.

Keep all existing content intact."""
    },

    "ch08_s02": {
        "action": "STRUCTURAL REWRITE",
        "notes": """Fix the body bag scene. Keep the ATMOSPHERE and TENSION but ground it in reality.

THE PROBLEM: The scene ends with a literal body bag unzipping from the inside on a live
monitor feed. This is supernatural and contradicts the hard-physics world rules.

THE FIX: The monitor feed is corrupted/manipulated. What Elena and Linnea see is NOT live
footage — it's a doctored feed, or the monitor is glitching, or Aris has spliced footage
to frighten them. Linnea should notice something wrong: a timestamp mismatch, a frame skip,
a resolution change — something that tells them this isn't real-time.

Keep these elements:
- Elena and Linnea at the interface terminal investigating corrupted logs
- The escalating tension and claustrophobia
- The "Aris sends his regards" message (or rephrase as a system message that implies Aris)
- The coordinates to the morgue level
- The CREEPY feeling of the body bag scene — but now it's creepy because someone STAGED it

Replace: "The zipper moving. From the inside." and Linnea's terrified reaction
With: The monitor shows footage of the body bag — and the zipper shifts. But Linnea notices:
"That's not live. Look at the timestamp — this was recorded three hours ago." Someone
edited this footage and pushed it to their terminal. The horror isn't supernatural — it's
that someone is watching them and knows exactly how to get inside their heads.

Also add a MOTHER reference: when the terminal disconnects, MOTHER's voice says something
like "Interface terminal disconnected. Session logged." — clinical, indifferent, watching."""
    },

    "ch09_s01": {
        "action": "MAJOR STRUCTURAL REWRITE",
        "notes": """This scene needs the biggest fix. Remove the literal Sato doppelganger. Ground
everything in hard physics.

THE PROBLEM: A literal double of Captain Sato emerges from an access panel — same face,
same scar, speaking with a slightly mechanical voice. This is supernatural and never
explained. It breaks the world rules completely.

THE FIX: Replace the doppelganger with this sequence:
1. Elena, Jax, and others are in the Spine Corridor.
2. A figure emerges from the maintenance access panel — but Elena's vision is blurring
   (CO₂ levels have been rising; she's been having headaches, pressure behind her eyes).
3. For a moment she THINKS it looks like Sato — same build, same sharp jawline — but as
   her vision clears, she realizes it's someone in maintenance coveralls, face hidden by
   the dim emergency lighting. OR: it's Aris, who she momentarily mistakes for Sato in
   her CO₂-addled state.
4. Whoever it is uses Sato's stolen override key to seal the section. Sato checks her
   belt — the key is gone. Someone pickpocketed it.
5. MOTHER's voice announces: "Section C sealed. Atmospheric adjustment in progress.
   Duration: sixty seconds." — NOT "atmospheric venting begins." It's a controlled test,
   not a murder attempt. MOTHER's safety overrides limit it.
6. The sixty seconds are terrifying — air thins, people panic — but it stops. MOTHER's
   hardcoded safety limits kick in. The doors don't unlock though — manual override needed.
7. Elena realizes: this was staged. Calibrated. Someone is TESTING them.

Remove: The literal "double" with Sato's face, the "too-wide smile," the mechanical voice,
the "same pale scar." All of that goes. Replace with grounded tension.

Keep: The atmosphere of paranoia, Jax's fear, the corridor setting, the key being stolen,
the doors locking. Keep the scene's emotional core: Elena realizing someone is engineering
their fear.

ALSO: Dr. Kade should be referred to as "he" throughout (MALE).
Marcus does NOT exist — he was removed in a previous pass. Do not reintroduce him."""
    },

    "ch09_s02": {
        "action": "ADD BRIDGE CONTENT",
        "notes": """Add bridge content at the START of this scene to explain how they survived the
locked corridor from the previous scene.

ADD AT THE BEGINNING (2-3 paragraphs):
After the sixty-second atmospheric test ended, MOTHER's safety override restored normal air.
But the doors stayed locked — manual override only. Elena and the others spent [some time]
working the manual release on the corridor hatch. Mara found a service panel. Priya checked
everyone's vitals. Someone (Elena? Mara?) got the hatch open.

Then transition into the existing scene content. The existing scene starts with Elena's
confession to Jax about burying evidence — keep ALL of that. Just add the bridge at the top
so the reader understands how they got from "locked corridor with venting atmosphere" to
"Elena having a private conversation with Jax."

Keep the bridge SHORT — 2-3 tight paragraphs max. This is transition, not a new scene."""
    },

    "ch10_s01": {
        "action": "STRUCTURAL REWRITE",
        "notes": """Sharpen Aris's motivation reveal. Add MOTHER going offline.

ARIS'S MOTIVATION: When Aris confronts Elena in Life Support, his dialogue should hint
more clearly at the experiment. Keep his existing lines but ADD or ADJUST:
- "I wanted you to see it. What your work turns into when the cameras are off." — KEEP this.
- Add something that reveals his role: "You think this is sabotage. It's not. It's
  observation." Or: "Every variable controlled. Every response logged. You're not a victim,
  Elena — you're a subject."
- His "Ask him — he signs the checks" line pointing to Silas should stay — it's the
  breadcrumb connecting Aris to Silas.

MOTHER GOING OFFLINE: During or right after the Aris confrontation, MOTHER's voice should
cut out mid-sentence or announce something ominous: "System override in progress. Monitoring
suspended—" then static. This marks the point where Aris (or Silas remotely) takes full
control of the habitat systems.

Keep: The emotional core of Elena's confrontation with Aris. Mara's arrival and pragmatism.
Elena and Mara working on the backup system together.

ELENA'S COMPETENCE: When Elena works on the system, she should defer to Mara for the
technical diagnosis. Elena's contribution is reading the situation and making decisions,
not rewiring circuits. Mara does the hands-on work."""
    },

    "ch10_s02": {
        "action": "STRUCTURAL REWRITE",
        "notes": """Establish the second bell. Set up Silas's exit strategy.

THE KEY ADDITION: During the bell dock discussion, someone (Linnea, who designed the place)
should mention that the Aethelgard has TWO emergency evacuation bells — the main one at
the bell dock, and a secondary one in Section D, installed during construction as a
redundancy measure. This plants the seed for Silas's later escape.

When Silas says "I'll stay" — he's performing nobility, but Elena should feel something
off about it. A line like: "Something in his expression makes my skin crawl. Too calm.
Too ready." Keep this existing beat but make Elena's suspicion sharper.

ADD AFTER SILAS LEAVES: When Mara's vest is found with her comm unit, add a brief MOTHER
line — either the speaker crackles with "Emergency bell deployed. Section D" or Elena
notices it on a status display. This confirms Silas took the secondary bell, not the
main one. He was never going to stay behind.

Keep: The escalating panic, the oxygen math, the emotional beats between characters,
the discovery of Mara's vest."""
    },

    "ch11_s01": {
        "action": "STRUCTURAL REWRITE",
        "notes": """Aris experiment reveal + fix Elena/Jax pronoun confusion.

THE BIG REVEAL: In this scene, Elena confronts the bell/escape decision. Add a moment
where the truth about Aris crystallizes. Either:
- Elena finds evidence (a tablet, a log, a MOTHER recording) that shows Aris's experiment
  logs — timestamped entries documenting crew stress responses, fear metrics, behavioral data.
- Or Elena says it out loud: "He wasn't trying to kill us. He was studying us."
- Connect to Silas: "Silas funded the whole thing. Jax's rehabilitation was the cover story.
  We were the experiment."

This doesn't need to be a long speech — just 3-4 sentences where the pieces click into place.

PRONOUN FIXES:
- "My voice cracks" (if Jax speaking) → "His voice cracks"
- "My jaw works like he's chewing through words" → fix to be consistent
- "My eyes flick to my temple where he presses two fingers" → clarify who is doing what
- Elena is "I", Jax is "he", Kade is "he", Sato is "she"

Dr. Kade: The line "This isn't a skeleton, Elena. It's a machine." — Kade is MALE (he/him).

Keep: The bell scene tension, Elena's confession about watching people die, the emotional
weight of descending into the bell."""
    },

    "ch11_s02": {
        "action": "STRUCTURAL REWRITE",
        "notes": """Fix the Silas paradox. Make his second appearance logical, not supernatural.

THE PROBLEM: Silas steps through the bell door and stays behind. Then another bell appears
below them with Silas inside. This reads as supernatural duplication.

THE FIX: When Elena sees the second bell rising:
- Someone (Captain Sato or Linnea) recognizes it: "That's the Section D emergency bell."
  Or "That's the secondary evac unit — from the construction dock."
- Elena realizes: Silas knew about it all along. He built this place. He always had his
  own way out. His "noble sacrifice" of staying behind was performance — he walked straight
  to the second bell the moment they left.
- The emotional hit: even at the end, Silas was performing. Just like Elena used to.
  The parallel should sting.

KEEP: The atmospheric detail (bioluminescence, cable sounds, cold), the emotional beats
between Elena and the crew, the sense of ascending from darkness. The bell scraping sound.
Silas's face in the porthole — but now it's not mysterious or supernatural, it's infuriating.
Elena realizes she's been played.

Remove: "That's impossible" — it's NOT impossible. It's pragmatic. Replace with something
like: "Of course." or Elena's realization landing.

Also: keep all character genders locked. Silas = he, Sato = she, Kade = he, Jax = he."""
    },

    "ch12_s01": {
        "action": "ADD CONTENT",
        "notes": """Add the revelation landing. Keep existing rescue/surface content.

ADD: During the decompression/recovery scene, Elena's internal monologue should crystallize
what she's figured out. 2-3 sentences woven into existing beats:
- "Silas funded the habitat. Aris ran the experiment. MOTHER logged every panic response,
  every argument, every breakdown. And Jax's rehabilitation was just the door they used
  to get us all inside."
- Connect to the crew tech's death: "The technician wasn't supposed to die. That was
  Aris's margin of error — the moment the experiment stopped being controlled and became real."
- Elena decides: she's going to tell the truth. Not perform. Not manage the narrative.
  Plant this decision here so the final scene pays it off.

When Mara says "Then breathe. You've earned that much." — Elena should feel the weight of
what she's about to do. She knows that once she talks, Silas's money, Aris's reputation,
and her own career are all finished.

Keep ALL existing content. Just weave in 2-3 internal thoughts."""
    },

    "ch12_s02": {
        "action": "STRUCTURAL REWRITE",
        "notes": """Rewrite the ending for clear thematic resolution. This is the final scene.

THE PROBLEM: The current ending is atmospheric but vague. Elena stands at a window, reflects,
and... nothing resolves. No decision. No action. No clear thematic close.

THE FIX: Keep the reflective atmosphere but add RESOLUTION:

1. KEEP: Elena alone at the corridor window. Mara's visit and departure. The ocean imagery.
   The internal reflection about masks and performance.

2. ADD — THE DECISION: Elena doesn't just stand there. She makes a choice:
   - She pulls out her phone/tablet/recording device.
   - She begins recording. Her voice. Her testimony. What Silas built. What Aris did.
     What she covered up for Jax before this. All of it.
   - "This is Elena Vance. I'm a crisis consultant. I was hired to manage Jax Vale's
     public rehabilitation aboard the Aethelgard deep-sea habitat. What follows is the truth
     about what happened down there."
   - She doesn't deliver the whole testimony — just the opening. The reader understands:
     she's done performing. She's choosing truth over safety.

3. KEEP: The ocean imagery at the end. But now it means something different — the ocean is
   indifferent, but Elena isn't. She's choosing to act.

4. FINAL LINE: Should land as a clear thematic close. Not another vague reflection.
   Something like the recording device's red light blinking in the dark glass. Or:
   "The ocean doesn't care what I did to survive. But I do. And that's enough to start."
   Or let Elena's voice carry forward — she's talking now, finally, and she won't stop.

TONE: Quiet. Not triumphant. This isn't a victory — it's a reckoning. Elena knows this
will destroy her career, expose her past cover-ups, and end everything she built. But she
does it anyway because the alternative — silence — is the thing that killed people.

Keep the scene roughly the same length (~800 words). Don't inflate it."""
    },
}

# ── System prompt for structural rewrites ─────────────────────────────────────

SYSTEM_PROMPT = f"""You are a senior fiction editor performing STRUCTURAL rewrites on a
first-person present-tense thriller novel. You have access to the PLOT BIBLE below, which
is the canonical ground truth for all story elements.

{PLOT_BIBLE}

EDITING RULES:
• Preserve the author's voice: tight, atmospheric, morally complex.
• Maintain first-person present tense (Elena narrating).
• "my" = only Elena's body/possessions. Others = his/her/their.
• Gender locks: Jax=he, Mara=she, Aris=he, Silas=he, Linnea=she, Priya=she.
• No supernatural elements. Ground everything in hard physics, human psychology, or technology.
• Keep existing dialogue where possible — adjust voice only where characters sound identical.
• When ADDING content, match the surrounding prose style exactly.
• When REMOVING content, close the gap seamlessly.
• Keep scene length within ±15% of original unless instructed otherwise.

Output ONLY the rewritten scene. No commentary. No headers. No "Here is the rewritten version."
Just the clean prose."""


async def fix_scene(client, scene_text: str, scene_id: str, notes: str) -> str:
    """Send scene through Claude for structural rewrite."""
    prompt = f"""{notes}

=== CURRENT SCENE ({scene_id}) ===
{scene_text}

=== OUTPUT THE REWRITTEN SCENE (prose only, no commentary) ==="""

    response = await client.generate(
        prompt,
        system_prompt=SYSTEM_PROMPT,
        max_tokens=10000,
        temperature=0.3,
    )
    fixed = response.content.strip() if response else ""

    # Strip any preamble
    for marker in ("Here is", "Here's", "Fixed scene:", "Fixed version:",
                   "Rewritten scene:", "===", "Below is", "Output:"):
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
    print(f"Structural fixes for {len(SCENES_TO_FIX)} scenes...\n")

    fixed_count = 0

    for scene in scenes:
        sid = scene.get("scene_id", "")
        if sid not in SCENES_TO_FIX:
            continue

        content = scene.get("content", "")
        if not content:
            continue

        info = SCENES_TO_FIX[sid]
        action = info["action"]
        notes = info["notes"]

        print(f"  [{sid}] {action}... ", end="", flush=True)

        orig_wc = len(content.split())
        fixed = await fix_scene(client, content, sid, notes)

        if not fixed or len(fixed) < 50:
            print(f"WARN: empty response, keeping original")
            continue

        new_wc = len(fixed.split())
        retention = new_wc / orig_wc if orig_wc > 0 else 0

        # More generous bounds for structural rewrites
        if retention < 0.35:
            print(f"WARN: collapsed ({orig_wc}->{new_wc}), keeping original")
            continue

        if retention > 1.60:
            print(f"WARN: inflated ({orig_wc}->{new_wc}), keeping original")
            continue

        scene["content"] = fixed
        fixed_count += 1
        print(f"OK ({orig_wc}->{new_wc} words, {retention:.0%})")

    # Save
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDone: {fixed_count}/{len(SCENES_TO_FIX)} scenes structurally rewritten")
    print(f"State saved to {STATE_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
