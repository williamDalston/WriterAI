# WriterAI Usage Guide

## Your Novel in 3 Simple Steps

### Step 1: Create Your Project

Choose your preferred method:

#### Method A: Interactive (Recommended for First-Time Users)

```bash
cd prometheus_novel
python prometheus new --interactive
```

You'll be prompted for:
- Novel title
- Genre
- Synopsis (multi-line)
- Main characters
- Setting
- Tone

#### Method B: Paste Your Idea

Create a text file with your novel concept:

```text
Title: The Memory Merchant

Genre: Science Fiction / Thriller

Synopsis:
In 2089, memories are currency. Dr. Elena Torres runs an underground 
clinic where she extracts and sells memories to the highest bidder. 
When a client's memory reveals a corporate conspiracy that could 
reshape society, Elena must decide whether to profit from the truth 
or expose it—knowing either choice could destroy her.

Characters:
- Dr. Elena Torres - Memory extraction specialist, 38, morally ambiguous
- Victor Chen - Corporate investigator, hunting for the leaked memory
- Iris - Elena's AI assistant, developing unexpected loyalties
- Marcus Webb - Elena's ex-partner, now working for the corporation

Setting: Neo-Singapore, 2089 - a sprawling megacity where memories are bought and sold

Tone: Noir meets cyberpunk - dark, morally complex, with moments of hope

Themes:
- The commodification of human experience
- What makes us who we are
- Truth vs. survival
- The ethics of technology
```

Then run:
```bash
python prometheus new --from-file my-novel-idea.txt
```

#### Method C: Quick Command Line

```bash
python prometheus new \
  --title "The Memory Merchant" \
  --genre "sci-fi" \
  --synopsis "In 2089, memories are currency..." \
  --auto-confirm
```

### Step 2: Generate Your Novel

After creating your project, you'll see:

```
✅ Project 'The Memory Merchant' created successfully!
📁 Config: prometheus_novel/configs/the_memory_merchant.yaml
📁 Data: prometheus_novel/data/the_memory_merchant

🚀 Start generating with:
   python prometheus generate --config configs/the_memory_merchant.yaml --all
```

**Run the full pipeline:**

```bash
python prometheus generate --config configs/the_memory_merchant.yaml --all
```

This will run all 12 stages:
1. High Concept (5-10 min)
2. World Modeling (10-15 min)
3. Beat Sheet (15-20 min)
4. Character Profiles (10-15 min)
5. Scene Sketches (20-30 min)
6. Scene Drafting (60-120 min) ⚠️ Longest stage
7. Self-Refinement (30-45 min)
8. Continuity Audit (15-20 min)
9. Human Passes (30-45 min)
10. Humanize Voice (20-30 min)
11. Motif Infusion (15-20 min)
12. Output Validation (10-15 min)

**Total time**: 4-8 hours depending on novel length and model speed

**Or run stages individually:**

```bash
# Just the concept stage
python prometheus generate --config configs/the_memory_merchant.yaml --stage high_concept

# Stages 1-5 (outline only, no prose)
python prometheus generate --config configs/the_memory_merchant.yaml --start-stage 1 --end-stage 5

# Resume from stage 6
python prometheus generate --config configs/the_memory_merchant.yaml --start-stage 6 --end-stage 12
```

### Step 3: Compile Your Novel

Once generation is complete:

```bash
python prometheus compile --config configs/the_memory_merchant.yaml
```

Your novel will be at: `output/the_memory_merchant.md`

## Advanced Usage

### Monitoring Progress

```bash
# Check project status
python prometheus status --config configs/the_memory_merchant.yaml

# View project details
python prometheus info --config configs/the_memory_merchant.yaml

# List all projects
python prometheus list
```

### Resuming After Interruption

If the pipeline is interrupted:

```bash
# Resume from last checkpoint
python prometheus generate --config configs/the_memory_merchant.yaml --resume

# Or manually specify where to continue
python prometheus generate --config configs/the_memory_merchant.yaml --start-stage 7
```

### Cost Management

Monitor costs in real-time. The system will:
- Track token usage
- Calculate costs
- Warn at 80% of budget
- Stop at budget limit

**Check costs:**
```bash
# Costs are logged to: logs/prometheus_novel.log
tail -f logs/prometheus_novel.log | grep "Cost:"
```

**Modify budget:**

Edit your project's config file:
```yaml
# configs/the_memory_merchant.yaml
budget_usd: 200.0  # Increase from default $100
```

### Using Different Models

**Edit config to use different models:**

```yaml
model_defaults:
  api_model: gpt-4o-mini        # Fast, cheap
  # api_model: gpt-4o          # Slower, expensive, better quality
  # api_model: gpt-3.5-turbo   # Fastest, cheapest, lower quality
```

**Use local models (if available):**
```yaml
model_defaults:
  local_model: llama-70b
  api_model: gpt-4o-mini
```

### Customizing Output

**Change output format:**
```bash
python prometheus compile --config configs/your_novel.yaml --format html
python prometheus compile --config configs/your_novel.yaml --format pdf
```

**Custom output location:**
```bash
python prometheus compile --config configs/your_novel.yaml --output /path/to/my_novel.md
```

### Genre-Specific Tips

#### Science Fiction
- Be specific about your technology/science
- Define clear rules for your world
- Consider social implications

#### Fantasy
- Establish magic system rules early
- Create rich cultural details
- Map out world geography

#### Mystery
- Plant clues in your synopsis
- Define the mystery clearly
- Mention red herrings if desired

#### Thriller
- Emphasize stakes and time pressure
- Define clear antagonist
- Specify danger/threat

#### Romance
- Focus on character emotions
- Define relationship obstacles
- Specify character chemistry

## Troubleshooting

### "ModuleNotFoundError"

```bash
# Make sure you're in the right directory
cd prometheus_novel

# Install dependencies
make install
# or
poetry install
```

### "OpenAI API Error"

```bash
# Check your .env file
cat .env | grep OPENAI_API_KEY

# Should show: OPENAI_API_KEY=sk-...
# If not, add it:
echo "OPENAI_API_KEY=sk-your-key-here" >> .env
```

### "Budget Exceeded"

Either:
1. Increase budget in config:
   ```yaml
   budget_usd: 200.0
   ```

2. Use cheaper models:
   ```yaml
   model_defaults:
     api_model: gpt-3.5-turbo
   ```

3. Generate fewer scenes:
   ```yaml
   max_scenes: 20  # Default is usually 30-50
   ```

### "Generation Taking Too Long"

Stage 6 (Scene Drafting) is the slowest. Options:

1. **Run stages 1-5 first** (fast, creates outline):
   ```bash
   python prometheus generate --config configs/your_novel.yaml --end-stage 5
   ```

2. **Review and adjust** the beat sheet before drafting

3. **Use faster model** for drafting:
   ```yaml
   stage_model_map:
     scene_drafting: local_model  # If available
   ```

### "Output Quality Not Great"

Try:
1. **More detailed synopsis** - Give more information upfront
2. **Better model** - Use gpt-4o instead of gpt-4o-mini
3. **Clearer genre** - Be specific (e.g., "hard sci-fi" vs just "sci-fi")
4. **Run refinement stages twice** - Stages 7-11 can be run multiple times

### "Inconsistencies in Story"

```bash
# Run continuity audit again
python prometheus generate --config configs/your_novel.yaml --stage continuity_audit

# Or full refinement pass
python prometheus generate --config configs/your_novel.yaml --start-stage 7 --end-stage 11
```

## Pro Tips

### 1. Start with a Clear Synopsis
The better your synopsis, the better the output. Include:
- Main conflict
- Key characters
- Setting
- Tone/mood
- Themes

### 2. Use the Right Genre
Genre affects:
- Prompt selection
- Style guidance
- Pacing
- World-building focus

### 3. Review After Stage 5
Stages 1-5 create the outline. Review it before running stage 6 (drafting):

```bash
# Generate outline only
python prometheus generate --config configs/your_novel.yaml --end-stage 5

# Review files in data/your_novel/outputs/

# If satisfied, continue
python prometheus generate --config configs/your_novel.yaml --start-stage 6
```

### 4. Save Checkpoints
Always use `--save-checkpoints` for long runs:

```bash
python prometheus generate --config configs/your_novel.yaml --all --save-checkpoints
```

### 5. Budget Wisely
Estimated costs (gpt-4o-mini):
- Outline only (stages 1-5): $2-5
- Full short story (10k words): $5-10
- Full novella (30k words): $15-30
- Full novel (60k words): $30-60

Budget accordingly!

### 6. Iterate on Refinement
Stages 7-11 can be run multiple times:

```bash
# First pass
python prometheus generate --config configs/your_novel.yaml --start-stage 7 --end-stage 11

# Review, then second pass
python prometheus generate --config configs/your_novel.yaml --start-stage 7 --end-stage 11
```

### 7. Use Templates
Genre templates provide optimized settings:

```bash
# Templates are automatically applied based on genre
# sci-fi, fantasy, mystery, thriller, romance, horror, literary, historical, dystopian, adventure
```

## Example Workflow

Here's a complete example from start to finish:

```bash
# 1. Create project
cat > my-novel.txt << 'EOF'
Title: Echoes of Tomorrow
Genre: Dystopian

Synopsis:
In 2157, the Global AI Council has achieved perfect order by predicting 
and preventing all crimes before they occur. Maya Zhou, a "Precog" who 
can see the future, discovers that the system is about to condemn her 
daughter for a crime she hasn't committed yet. To save her, Maya must 
commit the one crime the system can't predict: the impossible.

Characters:
- Maya Zhou - Precog, mother, torn between duty and love
- Aria Zhou - Maya's 16-year-old daughter, innocent
- Director Reeves - Head of Global AI Council, true believer
- Kai - Underground resistance leader, offers Maya a way out

Setting: Neo-Beijing, 2157 - surveillance state, pristine but lifeless
Tone: Dark, urgent, with hope for humanity
Themes: Free will, motherhood, the price of safety, rebellion
EOF

# 2. Create project
python prometheus new --from-file my-novel.txt

# 3. Generate (stages 1-5 first for review)
python prometheus generate --config configs/echoes_of_tomorrow.yaml --end-stage 5

# 4. Review outline in data/echoes_of_tomorrow/outputs/

# 5. Generate full novel
python prometheus generate --config configs/echoes_of_tomorrow.yaml --start-stage 6 --all

# 6. Compile
python prometheus compile --config configs/echoes_of_tomorrow.yaml

# 7. Read your novel!
cat output/echoes_of_tomorrow.md
```

## Getting Help

### Command Help

```bash
# General help
python prometheus --help

# Command-specific help
python prometheus new --help
python prometheus generate --help
python prometheus compile --help
```

### Logs

```bash
# View logs
tail -f logs/prometheus_novel.log

# Search for errors
grep ERROR logs/prometheus_novel.log
```

### Documentation

- **Quick Start**: [QUICKSTART.md](QUICKSTART.md)
- **Architecture**: [prometheus_novel/docs/ARCHITECTURE.md](prometheus_novel/docs/ARCHITECTURE.md)
- **Development**: [prometheus_novel/docs/DEVELOPMENT.md](prometheus_novel/docs/DEVELOPMENT.md)

---

**Happy Writing! 📚✨**

*Remember: The AI is your co-writer. The better your input, the better the output.*

