# CoverGen — AI Book Cover Generation for Amazon KDP

> **Purpose:** Generate professional book covers for both Kindle eBooks and KDP print paperbacks. Uses GPT Image 1 for artwork generation and programmatic text overlay for pixel-perfect typography.

---

## Prerequisites

### 1. OpenAI API Key

CoverGen uses GPT Image 1 for artwork. You need an OpenAI API key with image generation access.

```bash
export OPENAI_API_KEY="sk-..."
# or add to .env in your project directory
```

### 2. Python Dependencies

```bash
pip install Pillow fpdf2
# or: pip install -r requirements.txt (installs everything)
```

### 3. Bundled Fonts

CoverGen ships with 8 OFL-licensed fonts in `covergen/fonts/`. No additional font installation is needed.

| Font | Style | Used For |
|------|-------|----------|
| **Oswald Bold** | Condensed sans-serif | Display titles (cinematic, dark, minimalist) |
| **Oswald Medium** | Condensed sans-serif | Spine text, minimalist titles |
| **Libre Baskerville Regular/Bold/Italic** | Classic serif | Author names, body text, back cover |
| **Lora Regular/Bold/BoldItalic** | Soft serif | Romantic/literary titles and text |

---

## Quick Start

```bash
# Generate both eBook + print covers
writerai cover -c path/to/config.yaml

# Generate with a specific style
writerai cover -c config.yaml --style dark

# eBook cover only (no print PDF)
writerai cover -c config.yaml --ebook-only

# Print cover only (front + spine + back + PDF)
writerai cover -c config.yaml --print-only

# Override author name and page count
writerai cover -c config.yaml --author "Jane Author" --page-count 280

# Use a different trim size
writerai cover -c config.yaml --trim-size 5.5x8.5
```

---

## CLI Options

```
writerai cover --config/-c <path>     (required) Path to project config.yaml
               --style/-s <preset>    Visual style preset (see below)
               --trim-size <size>     Print trim: 6x9, 5.5x8.5, or 5x8 (default: 6x9)
               --page-count <int>     Page count for spine width (default: 300)
               --author <name>        Author name override
               --model/-m <model>     Override LLM model for art direction
               --ebook-only           Generate eBook cover only
               --print-only           Generate print cover only
               --force                Overwrite existing cover files
```

---

## Config

Add an optional `cover` section to your project's `config.yaml`:

```yaml
title: "Burning Vows"
genre: "romance"
synopsis: "A firefighter and a burn surgeon clash..."

# Optional cover configuration
cover:
  author_name: "Jane Author"
  subtitle: "A Novel"
  tagline: "Some fires can't be contained"
  series_name: "Hearts on Fire"
  series_number: "1"
  author_bio: "Jane Author writes steamy romance from her kitchen table in Brooklyn."

  # Print specifications
  trim_size: "6x9"           # 6x9 | 5.5x8.5 | 5x8
  page_count: 300            # For spine width calculation
  paper_type: "white"        # white | cream

  # Style
  style: "romantic"          # cinematic | illustrated | minimalist | dark | romantic | literary
  custom_art_prompt: ""      # Override AI-generated art direction entirely

  # Typography overrides (optional — defaults from style preset)
  title_font: ""             # e.g., "Oswald-Bold"
  author_font: ""            # e.g., "LibreBaskerville-Regular"
  title_color: ""            # Hex, e.g., "#FFE8D0"

  # Back cover blurb (optional — auto-generated from synopsis if omitted)
  blurb: ""
```

All `cover` fields are optional. The engine derives defaults from:
- **title** — from the root `title` field
- **style** — auto-detected from `genre` (see Style Presets below)
- **blurb** — loaded from BookOps `01_positioning.md` if available, otherwise generated from `synopsis`
- **fonts** — from the selected style preset

---

## Style Presets

CoverGen includes 6 visual styles. If not specified, the style is auto-detected from your genre.

| Preset | Description | Auto-Selected For | Title Font | Text Color |
|--------|-------------|-------------------|------------|------------|
| **cinematic** | Dramatic lighting, high contrast, photorealistic | thriller, mystery, sci-fi, historical | Oswald Bold | White on dark |
| **illustrated** | Digital illustration, painted, vibrant | fantasy, urban fantasy | Lora Bold | White on dark |
| **minimalist** | Clean, symbolic, lots of negative space | nonfiction, self-help | Oswald Medium | Dark on light |
| **dark** | Atmospheric, deep shadows, noir | horror, paranormal | Oswald Bold | Warm on dark |
| **romantic** | Warm golden light, soft focus, intimate | romance | Lora BoldItalic | Warm white on dark |
| **literary** | Subtle textures, muted palette, abstract | literary fiction, memoir | Libre Baskerville Bold | Dark on light |

### Genre Auto-Detection

| Genre Contains | Preset Selected |
|---------------|-----------------|
| romance | romantic |
| thriller, horror, paranormal | dark |
| fantasy, urban fantasy | illustrated |
| sci-fi, mystery, historical, contemporary | cinematic |
| literary, memoir | literary |
| nonfiction, self-help | minimalist |
| (anything else) | cinematic (default) |

Override with `--style` or `cover.style` in config.

---

## Output Files

After running `writerai cover`, the project gains a `covergen/` directory:

```
project_path/
  covergen/
    cover_artwork_raw.png      # Raw AI-generated artwork (no text)
    art_prompt.txt             # Art direction prompt used (for reproducibility)
    cover_ebook.jpg            # eBook cover — 2560x1600 px, JPEG, RGB
    cover_print_front.png      # Print front cover at 300 DPI
    cover_print_spine.png      # Spine strip
    cover_print_back.png       # Back cover with blurb + barcode zone
    cover_print_wrap.png       # Full assembled wrap (back + spine + front)
    cover_print.pdf            # Final print cover PDF for KDP upload
    cover_report.md            # Generation report with dimensions + cost
```

---

## How It Works

### Generation Pipeline

```
Step 1: Load Config
  Read config.yaml + pipeline_state.json (if available) + BookOps blurb

Step 2: Art Direction (LLM)
  Assemble genre/setting/tone/themes/motifs into a visual prompt
  LLM crafts a detailed scene description for the image generator
  Prompt explicitly bans text/typography (all text is overlaid later)

Step 3: Generate Artwork (GPT Image 1)
  Portrait orientation (1024x1536)
  High quality, PNG format
  Retries up to 3 times on failure

Step 4: Upscale
  LANCZOS resampling + mild unsharp mask
  eBook: fit/crop to 2560x1600
  Print: fit/crop to trim dimensions at 300 DPI

Step 5: Compose eBook Cover
  Overlay title (auto-sized to fit), subtitle, series name, author name
  Auto-detect text color from background luminance
  Save as JPEG (KDP eBook format)

Step 6: Compose Print Front Cover
  Same layout as eBook but at print resolution (e.g. 1800x2700 for 6x9)

Step 7: Compose Spine
  Rotated title + author name (top-to-bottom reading)
  Text omitted if spine < 0.25" (too narrow)

Step 8: Compose Back Cover
  Blurred/darkened artwork background
  Tagline, blurb text, author bio
  2"x1.2" barcode zone reserved in lower-right corner

Step 9: Assemble Full Wrap
  [bleed] [back] [spine] [front] [bleed] as a single image
  Edge pixels extended into bleed areas

Step 10: Export PDF
  Single-page PDF at physical dimensions, 300 DPI
  Ready for KDP print upload
```

### Why Programmatic Text (Not AI-Generated)?

AI image generators (including GPT Image 1) are unreliable at rendering text. Common issues:
- Misspelled words, garbled characters
- Inconsistent font styles across regenerations
- No control over kerning, weight, or exact positioning

CoverGen generates artwork **without any text**, then overlays title/author/blurb using Pillow with professional TrueType fonts. This ensures:
- Pixel-perfect, readable typography every time
- Consistent font choices across regenerations
- Full control over color, size, and placement

### Auto Text Color Detection

The compositor analyzes the artwork's luminance in the title region (top 35%) and author region (bottom 25%) to automatically choose:
- **White text with dark stroke** on dark backgrounds
- **Dark text** on light backgrounds

Override with `cover.title_color` in config (hex format).

---

## KDP Specifications Handled

### eBook (Kindle)

| Spec | Value |
|------|-------|
| Dimensions | 2560 x 1600 px |
| Aspect ratio | 1.6:1 (height:width) |
| Format | JPEG, RGB |
| DPI | 72+ (300 recommended) |

### Print (Paperback)

| Spec | Value |
|------|-------|
| DPI | 300 |
| Bleed | 0.125" on all sides |
| Safe zone | 0.25" from trim edges |
| Barcode zone | 2" x 1.2" in lower-right of back cover |
| Color space | RGB (KDP accepts; CMYK conversion deferred to future version) |
| Format | Single-page PDF |

### Spine Width Calculation

| Paper Type | Formula | Example (300 pages) |
|------------|---------|-------------------|
| White | page_count x 0.002252" | 0.676" |
| Cream | page_count x 0.0025" | 0.750" |

Spine text rules:
- **80+ pages**: spine text allowed
- **< 0.5" spine** (~222 pages white): title only, no author
- **< 0.25" spine** (~111 pages white): no text (blank spine)

### Supported Trim Sizes

| Size | Common Use |
|------|------------|
| **6 x 9** (default) | Most popular trade paperback |
| **5.5 x 8.5** | Traditional trade paperback |
| **5 x 8** | Compact fiction |

### Full Wrap Dimensions

```
Total Width  = 0.125 + trim_width + spine_width + trim_width + 0.125
Total Height = 0.125 + trim_height + 0.125
```

Example (6x9, 300 pages, white paper):
```
Spine  = 300 x 0.002252 = 0.676"
Width  = 0.125 + 6.0 + 0.676 + 6.0 + 0.125 = 12.926"
Height = 0.125 + 9.0 + 0.125 = 9.250"
At 300 DPI: 3877 x 2775 px
```

---

## BookOps Integration

When running `writerai bookops`, cover generation is available as **doc 09**:

```bash
# Generate all BookOps docs including cover
writerai bookops -c config.yaml

# Generate only the cover via BookOps
writerai bookops -c config.yaml --docs 09
```

Requirements for BookOps cover generation:
- `OPENAI_API_KEY` must be set (skipped silently if not)
- `Pillow` and `fpdf2` must be installed (skipped with a note if not)

The BookOps engine writes `09_cover_report.md` to the `bookops/` directory with a summary, while the actual cover files go to `covergen/`.

---

## Cost

| Component | Cost |
|-----------|------|
| GPT Image 1 (high quality, portrait) | ~$0.17 - $0.25 per image |
| LLM art direction prompt | ~$0.001 (GPT-4o-mini) |
| LLM blurb generation | ~$0.001 (GPT-4o-mini) |
| **Total per cover** | **~$0.17 - $0.25** |

Retries on failure add to cost. The `cover_report.md` includes exact cost tracking.

---

## Customization

### Custom Art Prompt

Skip the LLM art direction step entirely by providing your own prompt:

```yaml
cover:
  custom_art_prompt: >
    A misty mountain lake at dawn, pine forests reflected in still water,
    a single rowboat on the shore, watercolor painting style, soft pastels,
    atmospheric fog, peaceful and contemplative mood. No text, no lettering.
```

Always end custom prompts with "No text, no lettering" to prevent the image generator from adding text.

### Custom Fonts

Override the preset's font choices:

```yaml
cover:
  title_font: "Oswald-Bold"              # Must match a file in covergen/fonts/
  author_font: "LibreBaskerville-Italic"
```

To add your own fonts, place `.ttf` files in `prometheus_novel/covergen/fonts/` and reference them by filename (without `.ttf`).

### Custom Text Color

Force a specific text color instead of auto-detection:

```yaml
cover:
  title_color: "#FFD700"    # Gold
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `OPENAI_API_KEY not set` | Set the environment variable: `export OPENAI_API_KEY="sk-..."` |
| `ModuleNotFoundError: Pillow` | Run `pip install Pillow` |
| `ModuleNotFoundError: fpdf` | Run `pip install fpdf2` (note: `fpdf2`, not `fpdf`) |
| Cover text is hard to read | Try a different `style` preset, or set `title_color` manually |
| Spine text missing | Your page count produces a spine < 0.25". Increase `page_count` or leave spine blank (KDP allows it) |
| Image generation fails | Check your OpenAI API key has image access. The system retries 3 times automatically |
| Content policy rejection | GPT Image 1 may refuse certain prompts. Use `custom_art_prompt` to rephrase |
| Barcode zone overlaps text | Back cover text is too long. Shorten your blurb or author bio |

---

## Architecture

```
prometheus_novel/covergen/
  __init__.py         Exports CoverEngine
  engine.py           CoverEngine orchestrator — runs the 10-step pipeline
  art_director.py     LLM-based art direction prompt generation
  image_gen.py        GPT Image 1 API wrapper with retry + cost tracking
  upscaler.py         LANCZOS upscaling + KDP dimension calculations
  compositor.py       Text overlay (front, spine, back) + full wrap assembly
  pdf_export.py       Full-wrap image → single-page PDF via fpdf2
  presets.py          6 style presets + genre auto-detection
  fonts/              8 bundled OFL fonts (Oswald, LibreBaskerville, Lora)
```

### Key Design Decisions

1. **AI artwork only, no AI text** — all typography rendered programmatically by Pillow
2. **Pillow LANCZOS over Real-ESRGAN** — avoids PyTorch dependency (~2GB); LANCZOS is sufficient for high-quality AI artwork
3. **fpdf2 over reportlab** — MIT-licensed, ~200KB, pure Python; reportlab is heavier with license complications
4. **RGB for v1** — KDP accepts RGB print covers; CMYK conversion deferred to a future `--cmyk` flag
5. **Separate module from BookOps** — different dependencies, failure modes, and invocation patterns; BookOps calls in optionally

---

## Code References

| Item | Location |
|------|----------|
| CoverEngine | `covergen/engine.py` |
| CoverConfig dataclass | `covergen/engine.py` |
| Style presets | `covergen/presets.py` |
| Art direction prompt | `covergen/art_director.py` |
| GPT Image 1 wrapper | `covergen/image_gen.py` |
| KDP dimension math | `covergen/upscaler.py` |
| Text compositor | `covergen/compositor.py` |
| PDF export | `covergen/pdf_export.py` |
| CLI command | `interfaces/cli/main.py` → `cmd_cover()` |
| BookOps integration | `bookops/engine.py` → `_generate_cover()` |
| Bundled fonts | `covergen/fonts/*.ttf` |
