# 🌸 BLOOMING REWRITE ENGINE 2.0 - QUICK START GUIDE

**Get started in 5 minutes!**  
**Phase 1 Complete** - All features ready to use

---

## 🚀 FASTEST PATH: One-Sentence to Novel

### **Step 1: Generate Narrative Seed (30 seconds)**

```bash
cd /Users/williamalston/Desktop/WriterAI/prometheus_novel

python cli.py generate-seed \
  --prompt "A detective who can read memories discovers someone is stealing them" \
  --show-summary \
  --output memory_thief.yaml
```

**Output:**
```
🌱 BLOOMING REWRITE ENGINE 2.0 - Narrative Seed Generation
============================================================
Prompt: A detective who can read memories discovers someone is stealing them

🔄 Generating narrative framework...
✅ Narrative seed generated successfully!
📄 Saved to: memory_thief.yaml

============================================================
NARRATIVE SEED SUMMARY
============================================================

Title: The Memory Thief
Project: the_memory_thief
Genre: Mystery Thriller
Subgenres: Psychological Thriller, Science Fiction
Target Audience: Adult

Core Themes:
  - Identity and Memory
  - Power and Corruption
  - Truth and Reality

Main Characters:
  - Detective Sarah Chen (Protagonist)
  - The Collector (Antagonist)

Setting:
  Time: Near Future (2045)
  Place: Neo-Chicago
============================================================
```

---

### **Step 2: Generate Complete Novel (60-90 minutes)**

```bash
# Use the generated seed
python cli.py generate \
  --config memory_thief.yaml \
  --output-dir output/memory_thief
```

**This will:**
1. Run all 12 implementation stages
2. Generate 50,000-60,000 word novel
3. Apply human authenticity enhancement
4. Perform continuity audits
5. Humanize voice and infuse motifs
6. Validate and score quality

**Output:**
- `output/memory_thief/novel.txt` (60k words)
- `output/memory_thief/novel_state.json` (full state)
- `output/memory_thief/final_report.json` (quality metrics)

---

### **Step 3: Generate Visualizations (2 minutes)**

```bash
# Scene Map (shows narrative structure)
python cli.py visualize \
  --type scene_map \
  --state-file output/memory_thief/novel_state.json \
  --output memory_thief_scenes.svg

# Emotional Heatmap (shows emotional progression)
python cli.py visualize \
  --type emotional_heatmap \
  --state-file output/memory_thief/novel_state.json

# Character Relationships (shows network)
python cli.py visualize \
  --type character_diagram \
  --state-file output/memory_thief/novel_state.json
```

**Output:**
- `memory_thief_scenes.svg` (interactive scene map)
- `emotional_heatmap.html` (interactive emotion tracking)
- `emotional_heatmap_arc.html` (emotion over time)
- `emotional_heatmap_combined.html` (all-in-one)
- `character_relationships.png` (network graph)
- `character_relationships_matrix.png` (interaction heatmap)

---

## 🎨 EXAMPLE WORKFLOWS

### **Workflow 1: Romance Novel**

```bash
# 1. Generate seed
python cli.py generate-seed \
  --prompt "Two rival architects compete to design a building but fall in love" \
  --genre "romance" \
  --tone "warm and emotional" \
  --output romance_seed.yaml

# 2. Review and refine seed (optional)
cat romance_seed.yaml

# 3. Generate novel
python cli.py generate --config romance_seed.yaml

# 4. Visualize
python cli.py visualize --type emotional_heatmap --state-file output/novel_state.json
python cli.py visualize --type character_diagram --state-file output/novel_state.json
```

---

### **Workflow 2: Sci-Fi Epic**

```bash
# 1. Generate seed with specific settings
python cli.py generate-seed \
  --prompt "Humanity's last colony ship encounters a signal from an extinct alien race" \
  --genre "science fiction" \
  --audience "adult" \
  --tone "epic and philosophical" \
  --output scifi_seed.yaml

# 2. Generate novel with custom settings
python cli.py generate \
  --config scifi_seed.yaml \
  --output-dir output/last_colony

# 3. Create all visualizations
python cli.py visualize --type scene_map --state-file output/last_colony/novel_state.json
python cli.py visualize --type emotional_heatmap --state-file output/last_colony/novel_state.json
python cli.py visualize --type character_diagram --state-file output/last_colony/novel_state.json
```

---

### **Workflow 3: Literary Fiction**

```bash
# 1. Generate seed
python cli.py generate-seed \
  --prompt "An elderly woman writes letters to her younger self across time" \
  --genre "literary fiction" \
  --tone "contemplative and poetic" \
  --author "Your Name" \
  --output literary_seed.yaml

# 2. Generate with maximum quality settings
# (Edit config to set: default_authenticity_level: expert)

python cli.py generate --config literary_seed.yaml

# 3. Analyze emotional depth
python cli.py visualize --type emotional_heatmap --state-file output/novel_state.json
```

---

## 🔧 ADVANCED USAGE

### **Custom Seed Refinement**

```python
# In Python
from prometheus_lib.generators.narrative_seed_generator import NarrativeSeedGenerator

generator = NarrativeSeedGenerator()

# Generate initial seed
seed = await generator.generate_from_prompt(
    "A chef discovers forgotten recipes that alter reality"
)

# Refine based on feedback
refined_seed = await generator.refine_seed(
    seed,
    "Make it darker and add a mystery element"
)

# Save refined seed
generator.save_to_yaml(refined_seed, "refined_recipe_reality.yaml")
```

### **Programmatic Visualization**

```python
from prometheus_lib.visualization.scene_map_renderer import SceneMapRenderer
from prometheus_lib.visualization.emotional_heatmap import EmotionalHeatmapGenerator
from prometheus_lib.visualization.character_diagram import CharacterRelationshipDiagram

# Load novel state
with open("output/novel_state.json") as f:
    state = json.load(f)

# Generate all visualizations
renderer = SceneMapRenderer()
renderer.generate_scene_map_svg(
    state['scenes'], 
    state['narrative_framework'],
    output_path="custom_scene_map.svg",
    layout="spiral"  # Try different layouts!
)

heatmap_gen = EmotionalHeatmapGenerator()
heatmap_gen.generate_combined_visualization(
    state['scenes'],
    output_path="full_emotional_analysis.html"
)

diagram = CharacterRelationshipDiagram()
diagram.generate_diagram(
    state['characters'],
    state['scenes'],
    output_path="relationships.png",
    layout="kamada_kawai"  # Different layout algorithm
)
```

---

## 📊 VISUALIZATION EXAMPLES

### **Scene Map**
Shows narrative structure with:
- Color-coded scene types (setup, conflict, climax, resolution)
- Node size based on emotional intensity
- Connections showing scene flow
- Interactive tooltips with details

**Use for:**
- Planning narrative structure
- Identifying pacing issues
- Balancing scene types
- Visual storytelling

---

### **Emotional Heatmap**
Shows emotional progression with:
- 8 emotion dimensions (joy, sadness, anger, fear, etc.)
- Intensity across all scenes
- Emotional arc line charts
- Statistical analysis

**Use for:**
- Tracking emotional pacing
- Ensuring emotional variety
- Planning climactic moments
- Balancing emotional tone

---

### **Character Relationship Diagram**
Shows character dynamics with:
- Network graph of all relationships
- Node size = character importance
- Edge thickness = interaction frequency
- Interaction matrix heatmap

**Use for:**
- Understanding relationship dynamics
- Identifying isolated characters
- Planning character interactions
- Balancing screen time

---

## 🎯 COMMON USE CASES

### **Use Case 1: Planning a Novel**

1. Generate seed to get framework
2. Review seed summary
3. Generate scene map to visualize structure
4. Adjust seed if needed (refine)
5. Generate novel with confidence

---

### **Use Case 2: Analyzing Existing Novel**

1. Load novel state file
2. Generate all visualizations
3. Review emotional heatmap for pacing
4. Check character diagram for balance
5. Use scene map for structure analysis

---

### **Use Case 3: Iterative Development**

1. Generate seed
2. Generate partial novel (scenes 1-20)
3. Review visualizations
4. Refine approach
5. Generate remaining scenes
6. Final polish

---

## 💡 TIPS & TRICKS

### **Better Prompts**

❌ Too vague: "A story about friendship"  
✅ Better: "Two childhood enemies reunite at their high school reunion and must work together to solve a mystery"

❌ Too generic: "A romance"  
✅ Better: "A wedding planner falls for her client's ex-fiancé while planning the wedding"

### **Seed Refinement**

After generating a seed, you can refine it:

```bash
# Initial seed
python cli.py generate-seed --prompt "A witch loses her powers"

# If you want it darker
# Edit the YAML file manually or use refine_seed() in Python

# Or regenerate with hints
python cli.py generate-seed \
  --prompt "A witch loses her powers and must survive in a hostile world" \
  --tone "dark and gritty" \
  --genre "dark fantasy"
```

### **Visualization Layout Options**

Scene maps support different layouts:
- `grid`: Organized, easy to read (default)
- `spiral`: Shows progression visually
- `tree`: Hierarchical (for structured narratives)

---

## 🆘 TROUBLESHOOTING

### **"No such file or directory"**

Make sure you're in the correct directory:
```bash
cd /Users/williamalston/Desktop/WriterAI/prometheus_novel
```

### **"LLM generation failed"**

Check that your LLM client is configured:
- Verify API keys in `.env`
- Check model availability
- Ensure network connection

### **"Cannot find module"**

Install dependencies:
```bash
pip install svgwrite plotly networkx matplotlib pyyaml
```

### **Visualizations not generating**

1. Check state file exists
2. Verify JSON format is valid
3. Ensure output directory is writable
4. Check logs for specific errors

---

## 📚 COMPLETE COMMAND REFERENCE

### **Generate-Seed Command**

```bash
python cli.py generate-seed [OPTIONS]

Options:
  --prompt TEXT        One-sentence story idea [REQUIRED]
  --genre TEXT         Genre hint (optional)
  --audience TEXT      Target audience (optional)
  --tone TEXT          Desired tone (optional)
  --author TEXT        Author name (default: "Writer")
  --output TEXT        Output YAML file (default: "initial_idea.yaml")
  --show-summary       Display detailed seed summary
  --help              Show help message
```

### **Generate Command**

```bash
python cli.py generate [OPTIONS]

Options:
  --prompt TEXT        Novel prompt [REQUIRED]
  --title TEXT         Novel title
  --genre TEXT         Genre (default: "contemporary")
  --subgenres TEXT...  Subgenres
  --audience TEXT      Target audience (default: "adult")
  --tone TEXT          Tone (default: "serious")
  --pacing TEXT        Pacing (default: "moderate")
  --theme TEXT         Theme (default: "human connection")
  --motifs TEXT...     Motifs
  --output-dir TEXT    Output directory (default: "output")
  --config TEXT        Use config YAML file instead
  --help              Show help message
```

### **Visualize Command**

```bash
python cli.py visualize [OPTIONS]

Options:
  --type TEXT          Visualization type [REQUIRED]
                       Choices: scene_map, character_diagram, emotional_heatmap
  --state-file TEXT    Novel state JSON file
  --output TEXT        Output file (auto-named if not provided)
  --help              Show help message
```

---

## 🎓 NEXT STEPS

Now that Phase 1 is complete:

1. **Try it out!** Generate your first novel from a prompt
2. **Explore visualizations** - See your story structure visually
3. **Share feedback** - Help improve the system
4. **Plan Phase 2** - Distributed memory, real-time collaboration, polish automation

---

**Welcome to the future of narrative generation!** 🌸✨

*Quick Start Guide - Version 1.0*  
*Created: October 17, 2025*  
*System: Blooming Rewrite Engine 2.0*

