"""Apply audit fixes to pipeline_state.json scenes.

Usage:
    python -m prometheus_novel.scripts.apply_audit_fixes data/projects/burning-vows-30k
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def fix_ch01_s02(content: str) -> str:
    """Clarify Sofia toasting Dante but watching Lena."""
    old = 'Her grin widened. \"—I said \'to the one I love.\'\" The table leaned forward with anticipation.'
    new = 'Her grin widened. \"—I said \'to the one I love.\'\" She\'d aimed the words at Dante, but her eyes never left mine. The table leaned forward with anticipation.'
    if old in content:
        return content.replace(old, new)
    return content


def fix_ch02_s02(content: str) -> str:
    """Remove duplicate photographer paragraph at end."""
    dup = "\n\nHours later, after endless calls and negotiations, dawn broke over the monastery walls. Marco checked his screen and his face changed. \"Merda.\" He looked up. \"Photographer wants to move ceremony shots to tomorrow morning. Weather forecast shows rain during reception.\""
    if content.endswith(dup):
        return content[: -len(dup)]
    if dup in content:
        return content.replace(dup, "")
    return content


def fix_ch07_s03(content: str) -> str:
    """Fix POV shift: Lena found herself -> I walked."""
    old = "Lena found herself walking the path from the office door toward the jasmine grove, the route winding between terraces in the late afternoon light slipping toward golden hour, a journey that would end in Sofia's suite overlooking the sea. I lock"
    new = "I walked the path from the office door toward the jasmine grove, the route winding between terraces in the late afternoon light slipping toward golden hour, a journey that would end in Sofia's suite overlooking the sea. I lock"
    if old in content:
        return content.replace(old, new)
    return content


def fix_ch04_s03(content: str) -> str:
    """Trim excessive market description (trash bin, pigeon, child, scarves, cheese)."""
    # Remove: Behind him a municipal trash bin... through "exasperated and fond."
    old = " Behind him a municipal trash bin gapes open, mussel shells glittering like pale teeth and a smear of something oily that has no business near a lemon stand. The smell makes the sugar taste less saccharine and more complicated. A pigeon lands on the rim, pecking at something I can't see, its head bobbing with mechanical precision. The market churns around us—voices haggling over tomatoes, the scrape of wooden crates across cobblestones, someone's radio crackling with static and what might be soccer scores. I should leave. I should take the vendor's gift and walk back to the monastery where wedding logistics wait like patient vultures. Instead, I find myself studying the way sunlight catches in the crystallized lime peels, how they look like amber fragments of something precious and lost.\n\nI manage a smile. \"Grazie.\"\n\nHe beams as if I've given him something instead of the other way around. His wife—the woman with the sticky fingers—nods approvingly and turns to help another customer, her hands already reaching for another paper cone. The cobblestones beneath my feet are uneven, worn smooth by centuries of footsteps. Each step makes the candied peels rattle, a small percussion that follows me as I navigate between stalls selling everything from hand-knitted scarves to wheels of cheese so pungent they make my eyes water. A child runs past, chasing a soccer ball that bounces erratically off the stones, his mother calling after him in rapid Italian that sounds both exasperated and fond."
    new = " I find myself studying the way sunlight catches in the crystallized lime peels, how they look like amber fragments of something precious and lost.\n\nI manage a smile. \"Grazie.\"\n\nHe beams as if I've given him something instead of the other way around. His wife—the woman with the sticky fingers—nods approvingly and turns to help another customer."
    if old in content:
        return content.replace(old, new)
    return content


def fix_ch07_s01(content: str) -> str:
    """Trim duplicate backup pens/coffee paragraph and repetitive mundane details."""
    # Remove the duplicate paragraph that starts with "Twenty minutes later, I find myself in the village bar ordering espresso."
    dup = "Twenty minutes later, I find myself in the village bar ordering espresso. The practical details crowd my mind like armor against the emotional minefield spreading across the breakfast table. My shoes are sensible flats, broken in and reliable. My bag contains backup pens and emergency supplies. I am prepared for bureaucracy, if not for the way Marco's fingers drum against his thigh in a rhythm that matches my accelerating pulse.\n\nAfter collecting the coffee, I make my way back to the office. I head for the narrow stairs that lead down to the office and whatever paperwork waits there, my footsteps echoing in the morning stillness like a countdown to something I'm not ready to face."
    if dup in content:
        content = content.replace(
            dup,
            "Twenty minutes later, after grabbing the coffee Sofia requested, I climb the narrow stairs to the office, my footsteps echoing in the morning stillness like a countdown to something I'm not ready to face."
        )
    # Trim first backup pens mention - make it briefer
    old = "The practical details crowd my mind like armor against the emotional minefield spreading across the breakfast table. My shoes are sensible flats, broken in and reliable. My bag contains backup pens and emergency supplies. I am prepared for bureaucracy, if not for the way Marco's fingers drum against his thigh in a rhythm that matches my accelerating pulse. Dante appears"
    new = "The practical details crowd my mind like armor against the emotional minefield. Dante appears"
    if old in content:
        content = content.replace(old, new)
    return content


def fix_ch05_s02(content: str) -> str:
    """Add motivation for rejection after kiss."""
    old = "He reaches for my face—gentle, hesitant. \"Lena—\"\n\nI shake my head, pulling back further, the tenderness in his touch too much like David's had been in those final weeks when he'd tried to convince me we could still make it work. \"No.\""
    new = "He reaches for my face—gentle, hesitant. \"Lena—\"\n\nI shake my head, pulling back further. The tenderness in his touch—and how much I wanted to lean into it—terrified me. David had touched me like this in those final weeks, and I'd believed him when he said we could still make it work. I couldn't afford to believe Marco now. \"No.\""
    if old in content:
        return content.replace(old, new)
    return content


def fix_ch08_s02(content: str) -> str:
    """Add context for why orange zest spill matters."""
    old = "I fumble for the marmellata and my thumb finds the label's cheap sticker, half-lifted so it peels like an old promise.\n\n\"Do you remember—\" My voice cracks. \"Those jars we used to—after the seating charts?\""
    new = "I fumble for the marmellata and my thumb finds the label's cheap sticker, half-lifted so it peels like an old promise. That jar had survived a dozen planning sessions—one of the last things we'd built together before everything fell apart. Losing it would feel like losing proof we'd ever been a team.\n\n\"Do you remember—\" My voice cracks. \"Those jars we used to—after the seating charts?\""
    if "I fumble for the marmellata" in content and "That jar had survived" not in content:
        # Insert after first sentence of the fumble paragraph
        insert_pos = content.find('\"Do you remember—\"')
        if insert_pos > 0:
            before = content[:insert_pos].rstrip()
            if not before.endswith("team."):
                content = content.replace(
                    "half-lifted so it peels like an old promise.\n\n\"Do you remember—\"",
                    "half-lifted so it peels like an old promise. That jar had survived a dozen planning sessions—one of the last things we'd built together before everything fell apart. Losing it would feel like losing proof we'd ever been a team.\n\n\"Do you remember—\""
                )
    return content


def main():
    proj_path = sys.argv[1] if len(sys.argv) > 1 else "data/projects/burning-vows-30k"
    proj = Path(proj_path)
    if not proj.is_absolute():
        proj = PROJECT_ROOT / proj
    state_file = proj / "pipeline_state.json"
    if not state_file.exists():
        print(f"[ERROR] {state_file} not found")
        return 1

    with open(state_file, encoding="utf-8") as f:
        state = json.load(f)
    scenes = state.get("scenes") or []
    fixes = 0
    for scene in scenes:
        if not isinstance(scene, dict) or not scene.get("content"):
            continue
        sid = scene.get("scene_id", "")
        content = scene["content"]
        orig = content

        if sid == "ch01_s02":
            content = fix_ch01_s02(content)
        elif sid == "ch02_s02":
            content = fix_ch02_s02(content)
        elif sid == "ch07_s03":
            content = fix_ch07_s03(content)
        elif sid == "ch04_s03":
            content = fix_ch04_s03(content)
        elif sid == "ch07_s01":
            content = fix_ch07_s01(content)
        elif sid == "ch05_s02":
            content = fix_ch05_s02(content)
        elif sid == "ch08_s02":
            content = fix_ch08_s02(content)

        if content != orig:
            scene["content"] = content
            fixes += 1
            print(f"  Fixed {sid}")

    if fixes > 0:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        print(f"\n[OK] Applied {fixes} scene fixes to {state_file}")
    else:
        print("[INFO] No fixes applied (content may have changed)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
