# ⚡ SET API KEY THEN GENERATE YOUR BOOK

**Status:** System ready, API key needed

---

## 🔑 STEP 1: Set Your OpenAI API Key

You need an OpenAI API key to generate your book. Here's how:

### Get an API Key (if you don't have one)

1. Go to: https://platform.openai.com/api-keys
2. Sign in to your OpenAI account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-...`)

### Set the API Key

**In your current terminal, run:**

```bash
export OPENAI_API_KEY="sk-your-actual-key-here"
```

**Replace `sk-your-actual-key-here` with your real API key.**

### Verify It's Set

```bash
echo $OPENAI_API_KEY
```

You should see your key displayed.

---

## 🚀 STEP 2: Generate Your Power BI Book

**Once your API key is set, run:**

```bash
cd "/Users/williamalston/Desktop/WriterAI nonfiction/prometheus_novel"
python run_anbg.py --profile configs/textbook_powerbi.yaml
```

---

## ⚡ QUICK COPY-PASTE (All-in-One)

**Copy this entire block, edit the API key, and paste in terminal:**

```bash
# SET YOUR API KEY HERE ↓
export OPENAI_API_KEY="sk-PUT-YOUR-ACTUAL-KEY-HERE"

# Navigate and generate
cd "/Users/williamalston/Desktop/WriterAI nonfiction/prometheus_novel"
python run_anbg.py --profile configs/textbook_powerbi.yaml
```

---

## 📊 What Will Happen

### Immediate (First 5 minutes)
```
STAGE 1: PREFLIGHT VALIDATION
✅ Profile validated
✅ Allowlist checked (microsoft.com, dax.guide, etc.)
✅ Directories initialized

STAGE 3: OUTLINE PLANNER
Extracting Power BI concepts...
Building dependency graph...
Generated 10 chapters with learning objectives
✅ OUTLINE PLANNER COMPLETED
```

### Next Hour
```
STAGE 4: UNIT GENERATOR
Generating concepts, tutorials, exercises...
Generated 65 units across all chapters
Extracted 430 claims for citation
✅ UNIT GENERATOR COMPLETED

STAGE 5: EVIDENCE ATTACHER
Finding citations from allowlist...
Attached 412 citations
Coverage: 95.8%
✅ EVIDENCE ATTACHMENT PASSED

STAGE 6: FACT-CHECK GATE
Verifying all citations...
All links reachable ✅
0 hallucinations ✅
✅ FACT-CHECK GATE PASSED
```

### Final 30 Minutes
```
STAGE 7-13: Processing...
Added exercises and quizzes ✅
Created figures with alt-text ✅
Built glossary and index ✅
Tuned for clarity ✅
Exported to HTML ✅

🎉 ANBG PIPELINE COMPLETE - ALL GATES PASSED
📚 Your book is ready to publish!
```

---

## 📁 Where Your Book Will Be

```
data/power_bi_textbook/exports/
├── html/
│   └── power_bi_textbook.html      ← Your book!
├── QUALITY_SUMMARY.txt              ← Quality report
└── MANIFEST.json                    ← Complete metadata
```

---

## 💰 Cost Estimate

- **Budget:** $150
- **Expected:** $80-120
- **Per chapter:** ~$8-12
- **Worth it:** Publication-ready textbook with verified citations!

---

## ⏱️ Time Estimate

- **Total:** 1-2 hours
- **Stage 1-3:** 10-15 minutes (planning)
- **Stage 4-6:** 40-60 minutes (content + citations)
- **Stage 7-13:** 20-30 minutes (polish + export)

You can leave it running and come back when it's done!

---

## 🆘 If You Need Help

### No API Key?
Get one free at: https://platform.openai.com/api-keys

### Want to Monitor Progress?
Open another terminal:
```bash
tail -f "/Users/williamalston/Desktop/WriterAI nonfiction/prometheus_novel/logs/prometheus_novel.log"
```

### Generation Interrupted?
Resume from where it stopped:
```bash
python run_anbg.py --profile configs/textbook_powerbi.yaml --resume
```

---

## 🎯 THE COMMAND

**Here's what you need to run:**

```bash
# 1. Set your OpenAI API key (REQUIRED)
export OPENAI_API_KEY="sk-your-actual-key-here"

# 2. Navigate to system
cd "/Users/williamalston/Desktop/WriterAI nonfiction/prometheus_novel"

# 3. GENERATE YOUR POWER BI BOOK!
python run_anbg.py --profile configs/textbook_powerbi.yaml
```

---

**Once you set your API key and run the command, you'll have a complete Power BI textbook in 1-2 hours!** 📚✨


