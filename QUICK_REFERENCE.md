# WriterAI Quick Reference Card

**Version**: 2.0 (Post-Reorganization)  
**Status**: Production Ready ✅

## 🚀 Quick Start (30 Seconds)

```bash
cd /Users/williamalston/Desktop/WriterAI/prometheus_novel

# Create a project interactively
python -m interfaces.cli.main new --interactive

# Or use the example
python -m interfaces.cli.main new --from-file ../examples/quick-start-example.txt

# List your projects
python -m interfaces.cli.main list
```

## 📋 Common Commands

### Project Creation
```bash
# Interactive (easiest)
python -m interfaces.cli.main new --interactive

# From file
python -m interfaces.cli.main new --from-file novel-idea.txt

# From stdin
cat idea.txt | python -m interfaces.cli.main new --from-text

# Quick command
python -m interfaces.cli.main new --title "Title" --genre "sci-fi" --synopsis "..."
```

### Novel Generation
```bash
# Full pipeline (all 12 stages)
python -m interfaces.cli.main generate --config configs/my_novel.yaml --all

# Specific stage
python -m interfaces.cli.main generate --config configs/my_novel.yaml --stage high_concept

# Stages 1-5 (outline only, fast)
python -m interfaces.cli.main generate --config configs/my_novel.yaml --end-stage 5

# Resume from checkpoint
python -m interfaces.cli.main generate --config configs/my_novel.yaml --resume
```

### Compilation
```bash
# Compile to markdown
python -m interfaces.cli.main compile --config configs/my_novel.yaml

# Specify output
python -m interfaces.cli.main compile --config configs/my_novel.yaml --output my_novel.md
```

### Project Management
```bash
# List all projects
python -m interfaces.cli.main list

# Check status
python -m interfaces.cli.main status --config configs/my_novel.yaml

# Get info
python -m interfaces.cli.main info --config configs/my_novel.yaml
```

## 🔍 Ideas Database

### Search & Manage Ideas
```bash
# Initialize database
make db-init

# Import ideas
make db-import

# Search ideas
make db-search QUERY="science fiction"

# View statistics
make db-stats
```

## 🧪 Testing & Quality

### Run Tests
```bash
# All tests
make test

# Unit tests only
make test-unit

# With coverage
make coverage

# Fast tests only
make test-fast
```

### Code Quality
```bash
# Check code
make lint

# Auto-format
make format

# Type check
make typecheck

# All checks
make check-all
```

### Pre-Commit
```bash
# Install hooks
make pre-commit-install

# Run manually
make pre-commit-run
```

## 📚 Documentation

### Where to Look
- **START_HERE.md** - Begin here
- **QUICKSTART.md** - 5-minute guide
- **USAGE_GUIDE.md** - Complete reference
- **docs/ARCHITECTURE.md** - System design
- **docs/DEVELOPMENT.md** - Developer guide
- **CONTRIBUTING.md** - How to contribute

### Quick Links
```bash
# View documentation
cat START_HERE.md
cat QUICKSTART.md

# Open in editor
code USAGE_GUIDE.md
```

## 🛠️ Development

### Setup
```bash
# Install dependencies
make install

# Set up environment
cp .env.example .env
# Edit .env with your API keys
```

### Common Tasks
```bash
# Create project
make new-project

# Run tests
make test

# Check quality
make check-all

# Clean temp files
make clean
```

## 🎨 Genre Templates

Available genres with optimized settings:
- `sci-fi` - Science fiction
- `fantasy` - Fantasy
- `mystery` - Mystery/Detective
- `thriller` - Thriller/Suspense
- `romance` - Romance
- `horror` - Horror
- `literary` - Literary fiction
- `historical` - Historical fiction
- `dystopian` - Dystopian
- `adventure` - Adventure

Just specify genre when creating project!

## 📂 File Locations

### Important Directories
- `interfaces/cli/` - CLI implementation
- `tests/` - All tests
- `legacy/` - Archived old files (57 files)
- `docs/` - Documentation
- `configs/` - Project configurations
- `prompts/` - Prompt templates
- `data/ideas/` - Ideas database

### Core Files
- `prometheus` - CLI wrapper (executable)
- `pipeline.py` - Main pipeline
- `api.py` - API server
- `compile_novel.py` - Novel compilation
- `Makefile` - Development commands

## 🆘 Troubleshooting

### Common Issues

**Command not found**:
```bash
cd prometheus_novel
python -m interfaces.cli.main --help
```

**Import errors**:
```bash
make install
```

**Tests failing**:
```bash
make test
# Check logs/prometheus_novel.log
```

**Can't find feature**:
```bash
# Check help
python -m interfaces.cli.main --help

# Check documentation
cat USAGE_GUIDE.md
```

## 💡 Pro Tips

1. **Start with Interactive Mode**
   ```bash
   python -m interfaces.cli.main new --interactive
   ```

2. **Generate Outline First** (fast)
   ```bash
   python -m interfaces.cli.main generate --config configs/project.yaml --end-stage 5
   ```

3. **Use Make Commands**
   ```bash
   make help  # See all commands
   ```

4. **Search Ideas**
   ```bash
   make db-search QUERY="your topic"
   ```

5. **Check Examples**
   ```bash
   cat examples/quick-start-example.txt
   ```

## 🔗 Quick Links

### Key Documents
| Document | Purpose |
|----------|---------|
| START_HERE.md | Quick overview |
| GET_STARTED_NOW.md | Immediate usage |
| QUICKSTART.md | 5-minute tutorial |
| USAGE_GUIDE.md | Complete guide |
| COMPLETE_IMPLEMENTATION_SUMMARY.md | What was built |

### Commands Summary
| Task | Command |
|------|---------|
| Create project | `python -m interfaces.cli.main new --interactive` |
| Generate novel | `python -m interfaces.cli.main generate --config ... --all` |
| Compile result | `python -m interfaces.cli.main compile --config ...` |
| Search ideas | `make db-search QUERY="..."` |
| Run tests | `make test` |
| Check quality | `make check-all` |

## 📊 Statistics

- **Root .py files**: 8 (was 50+)
- **Legacy files**: 57 (archived)
- **Test files**: 19 (organized)
- **Ideas in database**: 899
- **Documentation files**: 15
- **Make commands**: 35+

## ✅ What's Working

- ✅ Novel project creation (4 methods)
- ✅ Unified CLI (6 commands)
- ✅ Ideas database (899 entries, searchable)
- ✅ Organized tests (19 files)
- ✅ CI/CD pipeline (GitHub Actions)
- ✅ Pre-commit hooks
- ✅ Comprehensive documentation
- ✅ Development tools (Makefile)

## 🎯 Next Steps

1. **Try It**: Create a project right now!
2. **Explore**: Search the ideas database
3. **Generate**: Create your first novel
4. **Contribute**: See CONTRIBUTING.md

---

## 📞 Need Help?

1. Check documentation: `cat START_HERE.md`
2. View examples: `cat examples/quick-start-example.txt`
3. Run help: `python -m interfaces.cli.main --help`
4. Check logs: `tail logs/prometheus_novel.log`

---

## 🎉 You're Ready!

Everything is set up and ready to use. Start creating amazing novels!

```bash
cd prometheus_novel
python -m interfaces.cli.main new --interactive
```

---

*Quick Reference v2.0 | System Ready | Let's Write!*

