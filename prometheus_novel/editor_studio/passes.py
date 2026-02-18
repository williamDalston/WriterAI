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

PASS_2_DIALOGUE_FRICTION = """=== TASK: Add dialogue subtext and friction ===
This high-tension scene's dialogue is too cooperative. Real humans dodge.

REQUIRED (add at least 2 of these):
- One interrupted line (em-dash: "I never said—")
- One evasive answer (character answers a different question)
- One strategic silence (character refuses to respond; beats fill the gap)
- One misdirection (says something true that implies something false)
- One lie-by-omission (answers literally but withholds the key detail)
- One half-sentence that trails off ("If you really think that...")

RULE: In high-stakes dialogue, no one answers the real question directly
on the first try. The first response should dodge, deflect, or redirect.
The truth comes out through pressure, not volunteering.

Keep the same information exchange and emotional arc. Add friction, not length.
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

PASS_TRUNCATION_COMPLETE = """=== TASK: Complete truncated scene ===
This scene appears to cut off mid-sentence or lack clear closure.

Complete the final sentence(s) naturally. Match the tone and POV. Do NOT add a new plot beat or paragraph—only finish what's already begun.

Output the FULL scene with your completion."""

PASS_OPENING_VARY = """=== TASK: Vary chapter opening ===
This is the first scene of a new chapter. It currently opens the same way as the previous chapter ({prev_opening}).

Change the OPENING 1–3 sentences to use a different hook:
- If previous was internal/reflective → open with DIALOGUE, ACTION, or concrete SETTING
- If previous was dialogue → open with IN_MEDIAS_RES (physical action) or INTERNAL (thought)
- If previous was setting → open with DIALOGUE or ACTION

Do NOT change the rest of the scene. Only replace or reshape the opening.
Output the FULL scene with your change."""

PASS_CROSS_SCENE_TRANSITION = """=== TASK: Add cross-scene transition ===
The reader is jumping from the previous scene to this one without a bridge.

Previous context: {prev_context}
This scene starts in: {curr_context}

Add 1–2 transition sentences at the VERY START of this scene that:
- Bridge the time/location/emotional shift
- Orient the reader (where we are, when, who's present)
- Feel natural, not expositional

Do NOT change the rest of the scene. Only ADD at the beginning.
Output the FULL scene with your addition."""

PASS_LINE_SHARPEN = """=== TASK: Line-level sharpness ===
Perform ONLY these micro-edits (do not rewrite structure or plot):

1. FILTER WORDS: Replace "saw/heard/noticed/realized/felt/watched/observed"
   with direct sensation. "I saw the light flicker" → "The light flickered."
   "She heard footsteps" → "Footsteps scraped the tile."

2. WEAK VERBS: Replace "was/got/started to/began to/seemed to/appeared to"
   with specific verbs. "He was angry" → "His jaw tightened."
   "She started to run" → "She ran."

3. ADVERBS: Cut adverbs that echo the verb. "whispered softly" → "whispered."
   "slammed angrily" → "slammed." Keep adverbs that reverse expectation
   ("gently slammed" = intentional contrast — keep).

4. WORDINESS: Compress 10-15% without cutting beats or sensory detail.
   "She was someone who always made sure to" → "She always"
   "The fact that he had been" → "He'd been"

5. SENTENCE RHYTHM: Ensure at least one ≤6-word sentence and one ≥25-word
   sentence per page of prose. Break up any run of 4+ same-length sentences.

Do NOT change plot, dialogue content, character voice, or emotional beats.
Output the FULL scene with your edits."""
