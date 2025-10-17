# 🚀 Quick Export Reference Card

## One-Command Export (Recommended)

Export your novel in **all formats** at once:

```bash
python prometheus_novel/export_all_formats.py \
  --state data/YOUR_NOVEL_NAME/state_snapshots/latest_state_*.json \
  --output-dir outputs/compiled
```

This creates:
- ✅ `novel.md` - Markdown format
- ✅ `novel_kindle.docx` - **Kindle-ready Word document**

---

## Individual Exports

### Kindle-Ready .docx (For Upload)

```bash
python prometheus_novel/export_kindle_docx.py \
  --state data/YOUR_NOVEL_NAME/state_snapshots/latest_state_*.json \
  --output outputs/my_novel.docx
```

**Features:**
- ✅ 6x9 inch format (Kindle/KDP standard)
- ✅ Table of contents
- ✅ Chapter titles
- ✅ Professional formatting
- ✅ Ready to upload to Amazon KDP

### Markdown .md

```bash
python prometheus_novel/compile_novel.py \
  --state data/YOUR_NOVEL_NAME/state_snapshots/latest_state_*.json \
  --output outputs/my_novel.md
```

---

## Finding Your State File

Your latest state file is located at:
```
data/[your_novel_slug]/state_snapshots/latest_state_*.json
```

To find it:
```bash
ls -lt data/*/state_snapshots/latest_state_*.json | head -1
```

---

## Custom Options

### With Author & Title

```bash
python prometheus_novel/export_all_formats.py \
  --state data/YOUR_NOVEL/state_snapshots/latest_state_*.json \
  --title "My Amazing Novel" \
  --author "Your Name" \
  --subtitle "An Epic Tale"
```

### Change Chapter Length

```bash
python prometheus_novel/export_kindle_docx.py \
  --state [path] \
  --output outputs/novel.docx \
  --scenes-per-chapter 5
```

---

## What You Get

### 📄 novel_kindle.docx
- **Perfect for:** Kindle Direct Publishing (KDP), Amazon, other platforms
- **Page size:** 6x9 inches
- **Includes:** Title page, table of contents, chapters, scene breaks
- **Format:** Professional book formatting
- **Ready to:** Upload immediately to KDP

### 📝 novel.md
- **Perfect for:** Editing, version control, plain text viewing
- **Includes:** YAML frontmatter, chapter structure, world rules
- **Format:** Clean Markdown
- **Can convert to:** PDF, HTML, ePub (using Pandoc)

---

## Upload to Kindle

1. Go to [kdp.amazon.com](https://kdp.amazon.com)
2. Create new title (Kindle eBook or Paperback)
3. Upload your `novel_kindle.docx` file
4. Preview and publish!

**Full instructions:** See `KINDLE_EXPORT_GUIDE.md`

---

## Install Dependencies

If you get import errors:

```bash
pip install python-docx pydantic pyyaml
```

Or install all requirements:

```bash
pip install -r prometheus_novel/requirements.txt
```

---

## Troubleshooting

**"No scenes found"**
→ Your novel generation isn't complete yet. Run the full pipeline first.

**"Module not found"**
→ Install dependencies: `pip install python-docx`

**"State file not found"**
→ Check the path. Use `ls data/*/state_snapshots/` to find it.

---

## 🎯 Fastest Path to Publication

1. **Generate novel:**
   ```bash
   python prometheus_novel/run_full_generation.py --config configs/your_config.yaml
   ```

2. **Export all formats:**
   ```bash
   python prometheus_novel/export_all_formats.py \
     --state data/your_novel/state_snapshots/latest_state_*.json
   ```

3. **Open** `outputs/compiled/novel_kindle.docx`

4. **Upload** to [kdp.amazon.com](https://kdp.amazon.com)

5. **Publish!** 🎉

---

**That's it! Your novel is publication-ready!** 📚✨

