"""Audio post-processing for ACX/Audible compliance.

Uses PyDub (+ FFmpeg) to concatenate TTS chunks, normalize levels,
add room tone, validate compliance, and export MP3s.
"""

import io
import logging
import math
import re
from pathlib import Path
from typing import Any, Dict, List

try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None

logger = logging.getLogger(__name__)


def _require_pydub():
    """Raise RuntimeError if pydub is not installed."""
    if AudioSegment is None:
        raise RuntimeError(
            "pydub is required for audiobook post-processing. "
            "Install it with: pip install pydub  (also requires FFmpeg)"
        )

# ---------------------------------------------------------------------------
# ACX specification constants
# ---------------------------------------------------------------------------

ACX_SAMPLE_RATE = 44100          # Hz
ACX_CHANNELS = 1                 # Mono
ACX_BITRATE = "192k"             # CBR
ACX_BIT_DEPTH = 16               # bits
ACX_RMS_TARGET_DB = -20.0        # Center of ACX range (-23 to -18)
ACX_RMS_MIN_DB = -23.0           # Floor
ACX_RMS_MAX_DB = -18.0           # Ceiling
ACX_PEAK_MAX_DB = -3.0           # Max peak
ACX_NOISE_FLOOR_MAX_DB = -60.0   # Max noise floor
ROOM_TONE_HEAD_MS = 500          # 0.5s silence at start
ROOM_TONE_TAIL_MS = 3000         # 3s silence at end
MAX_CHAPTER_DURATION_MS = 120 * 60 * 1000  # 120 minutes


# ---------------------------------------------------------------------------
# Room tone
# ---------------------------------------------------------------------------

def generate_room_tone(duration_ms: int) -> "AudioSegment":
    """Generate silence (room tone) at ACX specs.

    Returns a silent AudioSegment at 44.1kHz, 16-bit, mono.
    """
    _require_pydub()
    return AudioSegment.silent(
        duration=duration_ms,
        frame_rate=ACX_SAMPLE_RATE,
    )


# ---------------------------------------------------------------------------
# Chunk concatenation
# ---------------------------------------------------------------------------

def concatenate_chunks(chunk_audio_list: List[bytes]) -> "AudioSegment":
    """Concatenate raw MP3 byte chunks into a single AudioSegment.

    Each chunk comes from Google TTS as MP3 bytes.
    """
    _require_pydub()
    if not chunk_audio_list:
        return AudioSegment.silent(duration=100, frame_rate=ACX_SAMPLE_RATE)

    segments: List[AudioSegment] = []
    for chunk_bytes in chunk_audio_list:
        seg = AudioSegment.from_file(io.BytesIO(chunk_bytes), format="mp3")
        segments.append(seg)

    combined = segments[0]
    for seg in segments[1:]:
        combined += seg

    return combined


# ---------------------------------------------------------------------------
# ACX normalization
# ---------------------------------------------------------------------------

def normalize_to_acx(audio: AudioSegment) -> AudioSegment:
    """Normalize audio to ACX-compliant levels.

    Steps:
    1. Convert to mono, 44.1kHz, 16-bit
    2. Calculate gain needed for -20 dB RMS target
    3. Apply gain
    4. If peak > -3dB after gain, reduce to prevent clipping
    """
    # Convert to ACX format
    audio = audio.set_channels(ACX_CHANNELS)
    audio = audio.set_frame_rate(ACX_SAMPLE_RATE)
    audio = audio.set_sample_width(ACX_BIT_DEPTH // 8)  # bytes

    # Current RMS in dBFS
    current_rms = audio.dBFS
    if current_rms == float("-inf"):
        logger.warning("Audio is silent, skipping normalization")
        return audio

    # Calculate gain to reach target RMS
    gain_needed = ACX_RMS_TARGET_DB - current_rms
    audio = audio.apply_gain(gain_needed)

    # Check peak after gain — if too hot, pull back
    peak_db = audio.max_dBFS
    if peak_db > ACX_PEAK_MAX_DB:
        overshoot = peak_db - ACX_PEAK_MAX_DB
        audio = audio.apply_gain(-overshoot)
        logger.info(
            f"Peak limiting: reduced gain by {overshoot:.1f}dB "
            f"(peak was {peak_db:.1f}dB, now {audio.max_dBFS:.1f}dB)"
        )

    return audio


# ---------------------------------------------------------------------------
# ACX validation
# ---------------------------------------------------------------------------

def validate_acx_compliance(audio: AudioSegment) -> Dict[str, Any]:
    """Validate that audio meets all ACX requirements.

    Returns a dict with compliance status and measurements.
    """
    issues: List[str] = []

    # RMS level
    rms_db = audio.dBFS
    if rms_db < ACX_RMS_MIN_DB:
        issues.append(f"RMS too low: {rms_db:.1f}dB (min {ACX_RMS_MIN_DB}dB)")
    elif rms_db > ACX_RMS_MAX_DB:
        issues.append(f"RMS too high: {rms_db:.1f}dB (max {ACX_RMS_MAX_DB}dB)")

    # Peak level
    peak_db = audio.max_dBFS
    if peak_db > ACX_PEAK_MAX_DB:
        issues.append(f"Peak too high: {peak_db:.1f}dB (max {ACX_PEAK_MAX_DB}dB)")

    # Sample rate
    if audio.frame_rate != ACX_SAMPLE_RATE:
        issues.append(f"Wrong sample rate: {audio.frame_rate}Hz (need {ACX_SAMPLE_RATE}Hz)")

    # Channels
    if audio.channels != ACX_CHANNELS:
        issues.append(f"Wrong channels: {audio.channels} (need {ACX_CHANNELS} mono)")

    # Duration
    duration_ms = len(audio)
    duration_minutes = duration_ms / 60_000
    if duration_ms > MAX_CHAPTER_DURATION_MS:
        issues.append(
            f"Too long: {duration_minutes:.1f} min (max 120 min)"
        )

    return {
        "compliant": len(issues) == 0,
        "rms_db": round(rms_db, 1),
        "peak_db": round(peak_db, 1),
        "duration_minutes": round(duration_minutes, 1),
        "sample_rate": audio.frame_rate,
        "channels": audio.channels,
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Room tone padding
# ---------------------------------------------------------------------------

def add_room_tone(audio: AudioSegment) -> AudioSegment:
    """Add room tone padding: 0.5s head + 3s tail.

    ACX requires:
    - 0.5–1.0s room tone at start
    - 1.0–5.0s room tone at end
    """
    head = generate_room_tone(ROOM_TONE_HEAD_MS)
    tail = generate_room_tone(ROOM_TONE_TAIL_MS)
    return head + audio + tail


# ---------------------------------------------------------------------------
# MP3 export
# ---------------------------------------------------------------------------

def export_chapter_mp3(audio: AudioSegment, output_path: Path) -> Path:
    """Export AudioSegment as ACX-compliant MP3.

    Settings: 192 kbps CBR, 44.1 kHz, 16-bit, mono.
    Requires FFmpeg to be installed on the system.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    audio.export(
        str(output_path),
        format="mp3",
        bitrate=ACX_BITRATE,
        parameters=[
            "-ar", str(ACX_SAMPLE_RATE),
            "-ac", str(ACX_CHANNELS),
        ],
    )

    logger.info(f"Exported: {output_path} ({len(audio) / 1000:.1f}s)")
    return output_path


# ---------------------------------------------------------------------------
# Filename sanitization
# ---------------------------------------------------------------------------

def sanitize_filename(name: str) -> str:
    """Convert to ACX-safe filename: US alphanumeric + underscores only.

    Rules:
    - Replace spaces/hyphens with underscores
    - Strip non-alphanumeric/non-underscore characters
    - Lowercase
    - Truncate to 50 chars
    """
    name = name.lower().strip()
    name = re.sub(r"[\s\-]+", "_", name)
    name = re.sub(r"[^a-z0-9_]", "", name)
    name = re.sub(r"_+", "_", name)  # Collapse multiple underscores
    name = name.strip("_")
    return name[:50]
