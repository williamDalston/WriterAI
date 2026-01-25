# How to Use WriterAI - Simple Guide

## 🚀 Create a Novel Project (30 Seconds)

### Step 1: Navigate to Directory

```bash
cd /Users/williamalston/Desktop/WriterAI/prometheus_novel
```

### Step 2: Create Your Project

**Option A - Interactive (Easiest)**:
```bash
python -m interfaces.cli.main new --interactive
```

Answer the prompts:
- Novel title
- Genre (sci-fi, fantasy, mystery, etc.)
- Synopsis (paste your story idea)
- Main characters
- Setting
- Tone

**Option B - From File**:

Create `my-novel.txt`:
```
Title: The Memory Merchant
Genre: Sci-Fi

Synopsis:
In 2089, memories are currency. Dr. Elena Torres runs an underground 
clinic extracting and selling memories. When a client's memory reveals 
a corporate conspiracy, Elena must choose: profit or expose the truth.

Characters:
- Elena Torres - Memory specialist, morally ambiguous
- Victor Chen - Corporate investigator
- Iris - AI assistant with growing loyalties
```

Then run:
```bash
python -m interfaces.cli.main new --from-file my-novel.txt
```

**Option C - Quick Command**:
```bash
python -m interfaces.cli.main new \
  --title "My Novel" \
  --genre "sci-fi" \
  --synopsis "Your story here..." \
  --auto-confirm
```

### Step 3: Generate Your Novel

```bash
# Full pipeline (all 12 stages, ~4-8 hours)
python -m interfaces.cli.main generate \
  --config configs/your_project.yaml \
  --all

# Or just the outline (fast, ~10 minutes)
python -m interfaces.cli.main generate \
  --config configs/your_project.yaml \
  --end-stage 5
```

### Step 4: Compile the Result

```bash
python -m interfaces.cli.main compile \
  --config configs/your_project.yaml
```

Your novel is in `output/your_project.md`!

---

## 🔍 Search for Ideas

```bash
# Search the database (899 ideas)
make db-search QUERY="fantasy"
make db-search QUERY="detective"
make db-search QUERY="space"

# View all statistics
make db-stats
```

---

## 📋 Common Commands

### List Your Projects
```bash
python -m interfaces.cli.main list
```

### Check Project Status
```bash
python -m interfaces.cli.main status --config configs/your_project.yaml
```

### Run Tests
```bash
make test
```

### See All Commands
```bash
make help
python -m interfaces.cli.main --help
```

---

## 📚 More Help

- **Quick Reference**: `QUICK_REFERENCE.md`
- **Complete Guide**: `USAGE_GUIDE.md`
- **Examples**: `examples/quick-start-example.txt`
- **Documentation Index**: `DOCUMENTATION_INDEX.md`

---

## ✅ That's It!

**Three simple steps**:
1. Create project (30 seconds)
2. Generate novel (automatic)
3. Compile result (automatic)

**Start now**:
```bash
cd /Users/williamalston/Desktop/WriterAI/prometheus_novel
python -m interfaces.cli.main new --interactive
```

**Happy writing!** ✨

