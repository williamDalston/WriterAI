"""Genre mode settings — escalation, gating, tone.

Derives escalation_mode, gating_type, tone_density from config.genre or explicit
config keys. Used to vary outline generation and scene prompts between thriller
(danger escalation, info gates) and romance (intimacy escalation, emotional gates).

See docs/ROMANCE_ADAPTATION_GUIDE.md for full context.
"""



def get_genre_mode_settings(config: dict) -> dict:
    """Extract genre mode settings from project config.

    Args:
        config: Project config (from config.yaml).

    Returns:
        dict with keys: genre_mode, escalation_mode, gating_type, tone_density,
        romance (sub-dict when genre_mode is romance).
    """
    genre_raw = (config.get("genre") or "").lower().strip()
    genre_mode = (config.get("genre_mode") or genre_raw or "thriller").lower()

    # Map genre to defaults when not explicitly set
    if "romance" in genre_mode or "romantic" in genre_mode:
        default_escalation = "intimacy"
        default_gating = "emotional"
        default_tone = "breathing_room"
    elif "suspense" in genre_mode and "romantic" in genre_raw:
        default_escalation = "hybrid"
        default_gating = "both"
        default_tone = "breathing_room"
    else:
        default_escalation = "danger"
        default_gating = "info"
        default_tone = "compressed"

    return {
        "genre_mode": genre_mode,
        "escalation_mode": config.get("escalation_mode") or default_escalation,
        "gating_type": config.get("gating_type") or default_gating,
        "tone_density": config.get("tone_density") or default_tone,
        "romance": config.get("romance") or {},
    }


def build_escalation_prompt_block(config: dict) -> str:
    """Build prompt block describing escalation structure for outline/scene drafting.

    Args:
        config: Project config (from config.yaml).

    Returns:
        String to inject into prompts, or empty if thriller default.
    """
    settings = get_genre_mode_settings(config or {})
    esc = settings.get("escalation_mode", "danger")
    gate = settings.get("gating_type", "info")
    tone = settings.get("tone_density", "compressed")

    if esc == "danger" and gate == "info" and tone == "compressed":
        return ""  # Default thriller — no extra block needed

    lines = ["\n=== GENRE MODE (structure) ==="]

    if esc == "intimacy":
        lines.append(
            "ESCALATION: Intimacy ladder - Attraction -> Tension -> Emotional intimacy "
            "-> Threat to relationship -> Choice -> Commitment."
        )
    elif esc == "hybrid":
        lines.append(
            "ESCALATION: Hybrid — both danger AND intimacy escalate in parallel."
        )
    else:
        lines.append(
            "ESCALATION: Danger ladder - Environmental -> Forensic -> Psychological -> Institutional."
        )

    if gate == "emotional":
        lines.append(
            "GATING: Emotional vulnerability withheld. Physical intimacy only after "
            "emotional trust threshold. Backstory trauma at midpoint. Public confession in final act."
        )
    elif gate == "both":
        lines.append(
            "GATING: Both info (mystery) and emotional (relationship) — withhold accordingly."
        )
    else:
        lines.append("GATING: Info withheld. Reveals at designated beats.")

    if tone == "breathing_room":
        lines.append(
            "TONE: Breathing room. Interior longing. Slow burn. Allow subtext and micro-moments."
        )

    # Emotional temperature curve: romance oscillates, doesn't escalate linearly
    romance_cfg = settings.get("romance") or {}
    wave = romance_cfg.get("emotional_wave_pattern", "oscillating")
    if esc == "intimacy" and wave == "oscillating":
        lines.append(
            "TEMPERATURE CURVE: Romance oscillates (rise/fall cycles). Allow retreat after "
            "intimacy, conflict after vulnerability. Avoid 3+ chapters of linear rise or fall. "
            "Black moment = lowest point before commitment."
        )

    return "\n".join(lines) + "\n"
