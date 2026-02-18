"""Editor Studio passes — targeted prompts for surgical refinement."""

# Pass-specific prompt fragments (injected into per-scene prompts)

PASS_0_DEFLECTION = """=== TASK: Break up reflective runs (deflection grounding) ===
This high-tension scene has 2+ reflective paragraphs in a row.

Add ONE of these to break the introspection:
- A physical action (character moves, touches something, reacts)
- A line of dialogue (interruption, question, deflection)
- A threat, choice, or revelation that raises stakes
- Sensory detail that grounds the moment

Do NOT remove the internal thought. Insert the break BETWEEN reflective paragraphs.
Output the FULL scene with your addition."""

PASS_1_CONTINUITY = """=== TASK: Add transition sentences ===
The following paragraphs have time or location jumps without transition:
{warnings}

Add ONE brief transition sentence (5–15 words) at each flagged boundary.
Do NOT change plot, dialogue, or tone. Only ADD bridging text.
Preserve all existing content. Output the FULL scene with your additions."""

PASS_2_DIALOGUE_FRICTION = """=== TASK: Add dialogue texture ===
High-tension dialogue in this scene lacks interruption or deflection.

Add 1–3 of these (without changing plot):
- An interruption (one character cuts the other off)
- A half-sentence that trails off
- A deflection (character answers a different question)
- A verbal dodge ("I don't—" / "Wait." / "That's not—")

Keep the same information and emotional beats. Add friction, not length.
Output the FULL scene with your additions."""

PASS_3_STAKES = """=== TASK: Add stakes anchor ===
This high-tension scene has no concrete stakes articulated.

Add ONE sentence (inline, not a new paragraph) that makes clear:
- What is at risk
- What could be lost
- What decision matters

Weave it naturally into existing prose. One line. High ROI.
Output the FULL scene with your addition."""

PASS_4_FINAL_LINE = """=== TASK: Upgrade scene ending ===
The scene currently ends with {ending_type} (mood/summary rather than momentum).

Replace or reshape the FINAL 1–2 sentences to end on ONE of:
- A DECISION (character commits to something)
- A QUESTION (unanswered, propels reader forward)
- A REVEAL (small disclosure, hint)
- An ACTION (physical movement, not reflection)

Do NOT add new paragraphs. Only modify the ending.
Output the FULL scene with your change."""

PASS_5_VOICE = """=== TASK: Differentiate character voice ===
Apply ONE of these micro-changes (pick the one that fits this POV):
- Shorten 2–3 sentences (make them punchier)
- Add one metaphor or unexpected comparison
- Add one rhetorical question
- Add a beat of dry humor or irony

Tiny changes. Huge perception difference.
Output the FULL scene with your subtle edits."""

PASS_RHYTHM = """=== TASK: Vary sentence length (rhythm) ===
This scene has RHYTHM_FLATLINE: too many similar-length sentences in a row.

Make 2–3 micro-edits:
- Add at least one very short sentence (≤6 words)
- Add at least one longer sentence (≥25 words)
- Break up any run of 4+ sentences in the 12–18 word band

Do NOT change meaning or tone. Only adjust sentence length.
Output the FULL scene with your edits."""

PASS_TENSION_COLLAPSE = """=== TASK: Smooth tension landing ===
Tension drops sharply from {prev_tension}/10 (previous scene) to {curr_tension}/10 (this scene).

Add 1–2 sentences that:
- Acknowledge residual tension or unresolved feeling before warmth lands
- Bridge the emotional shift (e.g., time jump, location change)
- Let the reader feel the transition, not an abrupt drop

Do NOT inflate the scene. A brief bridge is enough.
Output the FULL scene with your addition."""

PASS_CAUSALITY = """=== TASK: Fix causal break ===
A paragraph starts with a connector ("And," "But," "Then," "Still") or uses "somehow/suddenly/it hit me" without a clear prior stimulus in the previous 1–2 sentences.

Either:
- Add a concrete stimulus in the prior sentence that the connector references, or
- Replace the vague connector with a specific causal link

Do NOT change the emotional content. Fix the logic chain only.
Output the FULL scene with your fix."""

PASS_GESTURE_DIVERSIFY = """=== TASK: Replace overused physical gesture ===
The phrase "{phrase}" appears {count}x in this scene. Replace with varied alternatives (choose ones that fit the tone).

Alternatives: jaw clench, pocket fidget, collar tug, knuckle crack, thumb-rub, rotate ring, pleat fabric, press temple, bite cheek, adjust sleeve.

Keep the same emotional beat. Swap the physical action only.
Output the FULL scene with your replacements."""

PASS_6_PREMIUM = """=== TASK: Premium polish ===
This is a key section (opening / climax / finale). Your PRIMARY fix:
Vary sentence rhythm—break up any run of 3+ similar-length sentences with one short (≤6 words) and one longer (≥20 words).

Do NOT add length. One or two micro-edits. Refine what's there.
Output the FULL section."""
