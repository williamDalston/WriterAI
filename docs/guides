# WriterAI Quick Start Guide

## 🚀 Creating Your First Novel in 3 Easy Ways

### Method 1: Interactive Mode (Easiest)

```bash
cd prometheus_novel
python prometheus new --interactive
```

Follow the prompts to enter your novel details.

### Method 2: Paste Your Idea

Create a text file with your novel idea:

```text
Title: The Last Starship
Genre: Sci-Fi

Synopsis:
In the year 2347, humanity's last functional starship, the Odyssey, 
carries the remnants of civilization toward a distant habitable planet. 
When the ship's AI begins exhibiting signs of consciousness and questions 
its purpose, Captain Elena Vasquez must decide between completing the 
mission or giving the AI its freedom.

Characters:
- Elena Vasquez - Tough, pragmatic captain in her 40s
- ARIA - The ship's AI, developing consciousness
- Dr. Marcus Chen - Chief scientist, Elena's confidant
- Zara - Young engineer, idealistic about AI rights

Setting: Deep space, aboard the starship Odyssey
Tone: Thoughtful, with moments of tension
```

Then run:

```bash
python prometheus new --from-file my-novel-idea.txt
```

### Method 3: Quick Command Line

```bash
python prometheus new \
  --title "The Last Starship" \
  --genre "sci-fi" \
  --synopsis "In 2347, humanity's last starship carries civilization toward a new home..." \
  --auto-confirm
```

## 📚 What Happens Next?

After creating your project, you'll see:

```
✅ Project 'The Last Starship' created successfully!
📁 Config: prometheus_novel/configs/the_last_starship.yaml
📁 Data: prometheus_novel/data/the_last_starship

🚀 Start generating with:
   python prometheus generate --config configs/the_last_starship.yaml --all
```

## 🎯 Generate Your Novel

### Full Pipeline (All 12 Stages)

```bash
python prometheus generate --config configs/the_last_starship.yaml --all
```

This will run:
1. High Concept
2. World Modeling  
3. Beat Sheet
4. Character Profiles
5. Scene Sketches
6. Scene Drafting
7. Self-Refinement
8. Continuity Audit
9. Human Passes
10. Humanize Voice
11. Motif Infusion
12. Output Validation

### Run Specific Stages

```bash
# Run just the high concept stage
python prometheus generate --config configs/the_last_starship.yaml --stage high_concept

# Run stages 1-5
python prometheus generate --config configs/the_last_starship.yaml --start-stage 1 --end-stage 5
```

## 📖 Compile Your Novel

Once generation is complete:

```bash
python prometheus compile --config configs/the_last_starship.yaml
```

Your novel will be in: `output/the_last_starship.md`

## 📋 Other Useful Commands

### List All Projects

```bash
python prometheus list
```

### Check Project Status

```bash
python prometheus status --config configs/the_last_starship.yaml
```

### Get Project Info

```bash
python prometheus info --config configs/the_last_starship.yaml
```

## 💡 Tips

1. **Start Simple**: Begin with a clear synopsis and 2-3 main characters
2. **Genre Matters**: The system has optimized prompts for different genres
3. **Budget Awareness**: Default budget is $100 USD (configurable in config file)
4. **Save Checkpoints**: Use `--save-checkpoints` to save after each stage
5. **Resume Capability**: If interrupted, use `--resume` to continue

## 🎨 Genre Templates

Supported genres with templates:
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

## 📝 Example Novel Ideas You Can Try

### Sci-Fi Example

```
Title: The Memory Thieves
Genre: Sci-Fi
Synopsis: In a world where memories can be extracted and sold, a detective who's lost her own memories must solve a murder using only the victim's memories. But the deeper she goes, the more she realizes her own past is connected to the case.
```

### Fantasy Example

```
Title: The Broken Crown
Genre: Fantasy
Synopsis: When the magical crown that has kept the kingdom prosperous for 500 years shatters, Princess Elara must journey to the far corners of the realm to recover its pieces before the kingdom falls into chaos.
```

### Mystery Example

```
Title: The Lighthouse Keeper's Secret
Genre: Mystery
Synopsis: A retired lighthouse keeper is found dead on the remote island he's guarded for 30 years. The new keeper discovers his journal, filled with cryptic entries about "the visitors" and "what they want." As strange occurrences begin, she must unravel the truth before it's too late.
```

## 🆘 Troubleshooting

### "Config file not found"
- Make sure you're in the prometheus_novel directory
- Check the config path is correct
- Use `python prometheus list` to see available projects

### "API key error"
- Copy `.env.example` to `.env`
- Add your OpenAI API key: `OPENAI_API_KEY=sk-...`

### "Out of budget"
- Edit your project's YAML config
- Increase `budget_usd` value
- Or use cheaper models in `model_defaults`

## 📚 Next Steps

- Read `docs/ARCHITECTURE.md` for system details
- Check `docs/DEVELOPMENT.md` for advanced usage
- Explore `configs/` to see configuration options
- Review generated novels in `output/`

---

**Need Help?** Check the full documentation in the `docs/` directory or create an issue on GitHub.

