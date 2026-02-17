# Audiobook Generation — ACX/Audible-Compliant via Google Cloud TTS

> **Purpose:** Convert a completed novel into per-chapter MP3 files that meet Audible's ACX submission requirements, using Google Cloud Text-to-Speech with multi-voice support for dual-POV novels.

---

## Prerequisites

### 1. Google Cloud Credentials

You need a Google Cloud project with the Text-to-Speech API enabled.

```bash
# Option A: Service account key (recommended for servers)
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"

# Option B: Application Default Credentials (recommended for local dev)
gcloud auth application-default login
```

Enable the API: https://console.cloud.google.com/apis/library/texttospeech.googleapis.com

### 2. FFmpeg

PyDub requires FFmpeg for MP3 encoding.

```bash
# Windows
choco install ffmpeg
# or: winget install ffmpeg

# macOS
brew install ffmpeg

# Linux
sudo apt install ffmpeg
```

### 3. Python Dependencies

```bash
pip install google-cloud-texttospeech pydub
# or: poetry install (if using the project's pyproject.toml)
```

---

## Quick Start

```bash
# 1. Estimate cost (no audio generated)
writerai audiobook -c path/to/config.yaml --dry-run

# 2. Generate all chapters
writerai audiobook -c path/to/config.yaml

# 3. Generate specific chapters only
writerai audiobook -c path/to/config.yaml --chapters 1 5 12

# 4. Regenerate everything (overwrite existing files)
writerai audiobook -c path/to/config.yaml --force -y
```

---

## Config

Add an `audiobook` section to your project's `config.yaml`:

```yaml
audiobook:
  # Default narrator voice (Google Cloud TTS voice ID)
  voice_default: en-US-Neural2-D

  # Multi-POV: map character names to different voices
  voice_map:
    "Elena": en-US-Neural2-F      # Female voice for Elena's POV chapters
    "Kaelen": en-US-Neural2-D     # Male voice for Kaelen's POV chapters

  # Speech parameters
  speaking_rate: 0.95              # 0.25–4.0 (0.95 = slightly slow for narration)
  pitch: 0                        # -20 to +20 semitones

  # Credits
  narrator_credit: "AI Narrator"  # Name spoken in opening/closing credits
```

If the `audiobook` section is omitted, defaults are used:
- Voice: `en-US-Neural2-D` (male, US English, Neural2)
- Rate: `0.95`
- No multi-voice mapping

### Choosing Voices

Browse available voices: https://cloud.google.com/text-to-speech/docs/voices

Recommended for audiobooks:
| Voice | Gender | Tier | Notes |
|-------|--------|------|-------|
| en-US-Neural2-D | Male | Neural2 | Clear, natural, good for narration |
| en-US-Neural2-F | Female | Neural2 | Warm, expressive |
| en-US-Neural2-A | Male | Neural2 | Deeper tone |
| en-US-Neural2-C | Female | Neural2 | Crisp, professional |
| en-US-Studio-O | Male | Studio | Premium quality ($30/1M chars) |
| en-US-Studio-Q | Female | Studio | Premium quality ($30/1M chars) |

---

## Output Structure

```
project/audiobook/
├── {name}_opening_credits.mp3      # Title, author, narrator
├── {name}_ch01.mp3                 # Chapter 1
├── {name}_ch02.mp3                 # Chapter 2
├── ...
├── {name}_closing_credits.mp3      # "The end" + credits
└── audiobook_manifest.json         # Tracking: files, compliance, cost
```

### Manifest

`audiobook_manifest.json` records:
- Files generated/skipped
- Per-chapter ACX compliance results (RMS, peak, duration)
- Total characters used and estimated cost
- Voice configuration used

---

## ACX Compliance

The module automatically ensures all output meets Audible's ACX submission requirements:

| Requirement | Target | ACX Spec |
|-------------|--------|----------|
| Format | MP3, 192 kbps CBR | 192+ kbps CBR |
| Sample rate | 44.1 kHz | 44.1 kHz |
| Channels | Mono | Mono (consistent throughout) |
| RMS level | -20 dB | -23 to -18 dB |
| Peak level | ≤ -3 dB | ≤ -3 dB |
| Room tone (head) | 0.5s | 0.5–1.0s |
| Room tone (tail) | 3.0s | 1.0–5.0s |
| Max duration | 120 min/file | 120 min/file |

### What Happens Automatically

1. **SSML conversion** — Prose is converted to SSML with paragraph pauses (500ms), scene breaks (2s), chapter headers spoken aloud
2. **Chunking** — Text is split at sentence boundaries to stay within Google TTS's 5,000-byte request limit
3. **Normalization** — Audio is normalized to -20 dB RMS (center of ACX range), with peak limiting at -3 dB
4. **Room tone** — 0.5s silence prepended, 3s silence appended to each file
5. **Validation** — Each chapter is checked against all ACX specs; issues are logged as warnings

---

## Multi-Voice (Dual-POV)

When `voice_map` is configured, the engine resolves voices per-scene based on the `pov_character` field from the pipeline state.

**How it works:**
1. Each scene has a `pov_character` field set during outline generation
2. The engine matches the character's first name (case-insensitive) against `voice_map` keys
3. If no match is found, `voice_default` is used
4. For chapters with mixed POVs, scenes are processed individually so the voice can switch mid-chapter, with 2-second pauses between scenes

---

## Cost

Google Cloud TTS Neural2 pricing: **$16 per 1 million characters**.

| Novel Length | Est. Characters | Est. Cost |
|-------------|----------------|-----------|
| 30k words (novella) | ~180k chars | ~$3 |
| 60k words (novel) | ~360k chars | ~$6 |
| 90k words (long novel) | ~540k chars | ~$9 |

Character counts include ~15% SSML markup overhead.

Use `--dry-run` to see exact estimates before generating:

```bash
writerai audiobook -c config.yaml --dry-run
```

The command always shows cost and asks for confirmation before proceeding (skip with `--yes`).

---

## CLI Reference

```
writerai audiobook [OPTIONS]

Required:
  --config, -c PATH    Path to project config.yaml

Options:
  --dry-run            Estimate cost only, don't generate audio
  --force              Overwrite existing MP3 files
  --yes, -y            Skip cost confirmation prompt
  --chapters N [N ...] Generate specific chapters only (e.g., --chapters 1 5 12)
```

---

## Resume / Incremental Generation

The module supports incremental generation:
- Existing MP3 files are **skipped** by default
- Use `--force` to regenerate all files
- Use `--chapters` to regenerate specific chapters

This means if generation fails mid-run, you can simply re-run the command and it will pick up where it left off.

---

## Architecture

```
config.yaml + pipeline_state.json
        │
        ▼
  AudiobookEngine.from_config_path()
        │
        ├─→ ssml.py: prose_to_ssml() → build_chapter_ssml() → chunk_ssml()
        │
        ├─→ tts_client.py: TTSClient.synthesize() (Google Cloud TTS, rate-limited)
        │
        ├─→ audio_post.py: concatenate → room tone → normalize → validate → export MP3
        │
        └─→ audiobook_manifest.json
```

### Module Files

| File | Purpose |
|------|---------|
| `audiobook/__init__.py` | Exports `AudiobookEngine` |
| `audiobook/engine.py` | Main orchestrator (mirrors BookOpsEngine pattern) |
| `audiobook/ssml.py` | SSML conversion + sentence-boundary chunking |
| `audiobook/audio_post.py` | PyDub post-processing for ACX compliance |
| `audiobook/tts_client.py` | Google Cloud TTS wrapper with retry/rate limiting |

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `FFmpeg not found` | PyDub can't find FFmpeg binary | Install FFmpeg and ensure it's in PATH |
| `Failed to initialize Google Cloud TTS client` | Missing or invalid credentials | Set `GOOGLE_APPLICATION_CREDENTIALS` or run `gcloud auth application-default login` |
| `No scenes with content found` | Pipeline hasn't completed drafting | Run `writerai generate` first |
| `TTS rate limited` | Too many requests/minute | Automatic: backs off and retries (up to 3x) |
| `RMS too low/high` after generation | Edge case in normalization | Re-run with `--force`; check manifest for details |
| `Peak too high` | Loud TTS output + gain | Normalization handles this automatically; if persists, lower `speaking_rate` |
