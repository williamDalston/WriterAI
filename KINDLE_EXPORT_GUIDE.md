# 📚 Kindle Export Guide - Perfect .docx Format

Your WriterAI system now exports **publication-ready .docx files** specifically formatted for **Kindle Direct Publishing (KDP)**.

## ✅ What You Get

Your final novel export includes:

### 📄 Professional Formatting
- **6x9 inch page size** (Kindle/KDP standard)
- **Times New Roman 12pt** body text
- **Justified text** with proper indentation
- **Professional margins** (0.75" all sides)
- **1.15 line spacing** for readability

### 📑 Complete Book Structure
- ✅ **Title page** with book title and author
- ✅ **Table of Contents** (automatically generated)
- ✅ **Chapter titles** (thematic titles from your novel)
- ✅ **Scene breaks** (*** separators between scenes)
- ✅ **Page breaks** between chapters

### 🎯 Ready for Upload
- ✅ Compatible with Kindle Direct Publishing (KDP)
- ✅ Compatible with Amazon's manuscript requirements
- ✅ No additional formatting needed
- ✅ Upload directly to KDP or other platforms

---

## 🚀 How to Use

### Basic Export

After your novel is generated, run:

```bash
python prometheus_novel/export_kindle_docx.py \
  --state data/your_novel_name/state_snapshots/latest_state_*.json \
  --output outputs/your_novel_kindle.docx
```

### With Custom Metadata

```bash
python prometheus_novel/export_kindle_docx.py \
  --state data/your_novel_name/state_snapshots/latest_state_*.json \
  --output outputs/your_novel_kindle.docx \
  --title "Your Novel Title" \
  --author "Your Name" \
  --subtitle "An Epic Story"
```

### Advanced Options

```bash
# Change scenes per chapter (default: 3)
python prometheus_novel/export_kindle_docx.py \
  --state data/your_novel_name/state_snapshots/latest_state_*.json \
  --output outputs/your_novel_kindle.docx \
  --scenes-per-chapter 5

# Exclude table of contents
python prometheus_novel/export_kindle_docx.py \
  --state data/your_novel_name/state_snapshots/latest_state_*.json \
  --output outputs/your_novel_kindle.docx \
  --no-toc
```

---

## 📤 Upload to Kindle Direct Publishing

### Step 1: Log into KDP
Go to [kdp.amazon.com](https://kdp.amazon.com) and sign in.

### Step 2: Create New Title
1. Click **"+ Kindle eBook"** or **"+ Paperback"**
2. Fill in the book details (title, author, description, etc.)

### Step 3: Upload Your Manuscript
1. In the **"Manuscript"** section
2. Click **"Upload Manuscript"**
3. Select your `.docx` file
4. Amazon will automatically convert it

### Step 4: Preview & Publish
1. Use the **"Preview"** feature to check formatting
2. The table of contents will be automatically detected
3. All chapter breaks will be preserved
4. When satisfied, click **"Publish Your Kindle eBook"**

---

## 📋 File Format Details

### Page Size
- **Width:** 6 inches
- **Height:** 9 inches
- Standard for print books and Kindle formatting

### Typography
- **Body Font:** Times New Roman 12pt
- **Chapter Titles:** Times New Roman 18pt, Bold, Centered
- **Book Title:** Times New Roman 28pt, Bold, Centered
- **Scene Breaks:** *** (three asterisks, centered)

### Margins
- **Top:** 0.75"
- **Bottom:** 0.75"
- **Left:** 0.75"
- **Right:** 0.75"

### Paragraph Formatting
- **First line indent:** 0.25"
- **Alignment:** Justified
- **Line spacing:** 1.15

---

## 🎨 Customization Options

### Chapter Grouping
By default, 3 scenes = 1 chapter. To change:

```bash
--scenes-per-chapter 5  # 5 scenes per chapter
```

### Title Override
Override the title from your state file:

```bash
--title "My Custom Title"
```

### Author Name
Specify or override the author:

```bash
--author "J.K. Rowling"
```

### Subtitle
Add a subtitle to your title page:

```bash
--subtitle "A Tale of Adventure and Magic"
```

---

## 🔧 Troubleshooting

### "No scenes found" Error
**Cause:** Your state file doesn't have completed scenes yet.

**Solution:** Make sure your novel generation has completed all stages:
```bash
python prometheus_novel/run_full_generation.py --config configs/your_config.yaml
```

### Missing Chapter Titles
**Cause:** Chapter titles weren't generated during the pipeline.

**Solution:** The system will automatically create numbered chapters (Chapter 1, Chapter 2, etc.)

### Table of Contents Not Showing
**Cause:** You used `--no-toc` flag or TOC generation was skipped.

**Solution:** Remove the `--no-toc` flag:
```bash
python prometheus_novel/export_kindle_docx.py --state <path> --output <path>
```

---

## 📊 What's Included in the Export

Your `.docx` file contains:

1. **Title Page**
   - Book title (large, centered, bold)
   - Subtitle (if provided)
   - Author name (by [author])

2. **Table of Contents**
   - List of all chapters with titles
   - Properly formatted
   - Page break after

3. **Chapters**
   - Each chapter on a new page
   - Chapter title (large, centered, bold)
   - All scenes in that chapter
   - Scene breaks between scenes (*** centered)

4. **Professional Typography**
   - Proper indentation
   - Justified text
   - Consistent spacing
   - Print-ready formatting

---

## ✨ Pro Tips

### For Kindle eBooks
- The 6x9 format will be automatically converted to eBook format by Amazon
- Chapter titles will become navigation points
- Table of contents will be interactive in the eBook

### For Print Books (KDP Paperback)
- 6x9 is the most popular paperback size
- No additional formatting needed
- Upload the same `.docx` file

### For Other Platforms
- This format works on IngramSpark, Draft2Digital, and other platforms
- May need minor adjustments for specific platform requirements
- Base formatting is industry-standard

---

## 🎯 Quick Start Summary

1. **Generate your novel** using WriterAI
2. **Find the latest state file** in `data/your_novel/state_snapshots/`
3. **Run the export tool:**
   ```bash
   python prometheus_novel/export_kindle_docx.py \
     --state data/your_novel/state_snapshots/latest_state_*.json \
     --output outputs/my_novel_kindle.docx
   ```
4. **Open the .docx file** and verify it looks good
5. **Upload to KDP** or your preferred platform
6. **Publish your book!** 🎉

---

## 📞 Support

If you encounter issues:
1. Check that your novel generation completed successfully
2. Verify the state file path is correct
3. Make sure `python-docx` is installed: `pip install python-docx`
4. Check the console output for specific error messages

---

**Your novel is now ready for the world! 🌟**

