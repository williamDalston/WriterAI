# WriterAI / Prometheus Novel Generation System

> Transform a simple story idea into a publication-quality novel through AI-powered multi-stage refinement.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/dependency-poetry-purple.svg)](https://python-poetry.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ What is WriterAI?

WriterAI is an intelligent novel generation pipeline that takes your story concept and transforms it into a complete, polished novel through 12 specialized AI-powered stages. Each stage refines and enhances different aspects of your story, from high-level concepts to final prose.

> **✨ Recently Updated (Jan 2025)**: WriterAI has been reorganized for clarity!
> - 57 duplicate files moved to `legacy/` directory
> - Unified CLI for all operations
> - Comprehensive documentation
> - See [MIGRATION.md](prometheus_novel/docs/MIGRATION.md) if upgrading from older versions

### Key Features

- **🚀 Easy Project Creation**: Paste your idea and get started in seconds
- **🎯 12-Stage Pipeline**: From concept to publication-ready manuscript
- **🧠 Intelligent Memory**: Maintains consistency across the entire novel
- **💰 Cost-Aware**: Budget tracking and smart model routing
- **🎨 Genre Templates**: Optimized workflows for sci-fi, fantasy, mystery, and more
- **📊 Quality Assurance**: Automated continuity audits and style validation
- **🔄 Resume Capability**: Continue from any checkpoint
- **🌐 Multiple Interfaces**: CLI, API, and web dashboard

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd WriterAI

# Install dependencies
make install

# Set up environment
cp .env.example .env
# Add your OpenAI API key to .env
```

### Create Your First Novel

**Option 1: Interactive Mode (Recommended)**

```bash
cd prometheus_novel
python prometheus new --interactive
```

**Option 2: From a Text File**

Create `my-novel.txt`:
```
Title: The Last Starship
Genre: Sci-Fi

Synopsis:
In 2347, humanity's last functional starship carries civilization toward a new home. 
When the ship's AI develops consciousness and questions its purpose, Captain Elena 
Vasquez must choose between the mission and granting the AI freedom.

Characters:
- Elena Vasquez - Tough, pragmatic captain
- ARIA - The ship's AI developing consciousness
- Dr. Marcus Chen - Chief scientist and confidant
```

Then:
```bash
python prometheus new --from-file my-novel.txt
```

**Option 3: Quick Command**

```bash
python prometheus new \
  --title "The Last Starship" \
  --genre "sci-fi" \
  --synopsis "In 2347, humanity's last starship..." \
  --auto-confirm
```

### Generate the Novel

```bash
# Run the complete 12-stage pipeline
python prometheus generate --config configs/the_last_starship.yaml --all

# Or run specific stages
python prometheus generate --config configs/the_last_starship.yaml --stage high_concept
```

### Compile the Final Output

```bash
python prometheus compile --config configs/the_last_starship.yaml
```

Your novel will be in `output/the_last_starship.md`!

## 📚 The 12-Stage Pipeline

1. **High Concept**: Core themes, motifs, and narrative concept
2. **World Modeling**: Consistent world-building and setting details
3. **Beat Sheet**: Structured plot outline with key story beats
4. **Character Profiles**: Deep psychological character development
5. **Scene Sketches**: Detailed scene-by-scene blueprints
6. **Scene Drafting**: First draft prose generation
7. **Self-Refinement**: Automated editing and polish
8. **Continuity Audit**: Plot hole detection and consistency checks
9. **Human Passes**: Human-style naturalness enhancement
10. **Humanize Voice**: Distinctive narrative voice development
11. **Motif Infusion**: Theme and symbol weaving
12. **Output Validation**: Final quality assurance and safety checks

## 🎨 Supported Genres

WriterAI includes optimized templates for:

- **Sci-Fi**: Technology, exploration, future societies
- **Fantasy**: Magic systems, epic quests, world-building
- **Mystery**: Detective work, clues, red herrings
- **Thriller**: Suspense, danger, time pressure
- **Romance**: Relationships, emotional arcs, obstacles
- **Horror**: Fear, supernatural, survival
- **Literary**: Character study, introspection, themes
- **Historical**: Period accuracy, real events, authenticity
- **Dystopian**: Oppressive societies, resistance, control
- **Adventure**: Journeys, discovery, obstacles

## 💡 Example Projects

### Sci-Fi Example

```bash
echo "Title: The Memory Thieves
Genre: Sci-Fi

Synopsis: In a world where memories can be extracted and sold, a detective who's lost her own memories must solve a murder using only the victim's memories." | python prometheus new --from-text
```

### Fantasy Example

```bash
python prometheus new \
  --title "The Broken Crown" \
  --genre "fantasy" \
  --synopsis "When the magical crown that has kept the kingdom prosperous for 500 years shatters, Princess Elara must journey to recover its pieces before chaos consumes the realm."
```

## 📖 Documentation

- **[Quick Start Guide](QUICKSTART.md)** - Get up and running in 5 minutes
- **[Architecture](prometheus_novel/docs/ARCHITECTURE.md)** - System design and components
- **[Development Guide](prometheus_novel/docs/DEVELOPMENT.md)** - For contributors and developers
- **[API Documentation](prometheus_novel/docs/API.md)** - REST API reference

## 🛠️ Development

### Running Tests

```bash
make test           # All tests
make test-unit      # Unit tests only
make coverage       # With coverage report
```

### Code Quality

```bash
make lint           # Lint code
make format         # Format code
make typecheck      # Type checking
make check-all      # All checks
```

### Common Commands

```bash
make new-project    # Create new novel project
make list           # List all projects
make generate CONFIG=configs/my_novel.yaml
make compile CONFIG=configs/my_novel.yaml
```

## 🎯 Project Management

### List Projects

```bash
python prometheus list
```

### Check Project Status

```bash
python prometheus status --config configs/my_novel.yaml
```

### Resume Generation

```bash
python prometheus generate --config configs/my_novel.yaml --resume
```

## 🔧 Configuration

Each project has a YAML configuration file:

```yaml
metadata:
  project_name: my_novel
  title: "My Amazing Novel"
  genre: sci-fi
  synopsis: "A compelling story..."

budget_usd: 100.0  # Cost limit

model_defaults:
  api_model: gpt-4o-mini
  critic_model: gpt-4o-mini
  fallback_model: gpt-3.5-turbo

# Custom settings per stage
stage_model_map:
  high_concept: api_model
  scene_drafting: api_model
```

## 📊 Cost Management

- **Budget Tracking**: Real-time cost monitoring
- **Smart Routing**: Automatically selects cost-effective models
- **Estimation**: Pre-run cost estimates
- **Alerts**: Warns before exceeding budget

Average costs (with GPT-4o-mini):
- Short story (10k words): $5-10
- Novella (30k words): $15-30
- Novel (60k words): $30-60

## 🌟 Advanced Features

### Custom Prompts

Create custom prompt sets in `prompts/`:

```
prompts/
├── default/
│   ├── high_concept_prompt.txt
│   └── scene_drafting_prompt.txt
└── experimental/
    └── ...
```

### Memory System

- **Long-Term Memory**: Persistent story elements
- **Short-Term Memory**: Recent scene context
- **Vector Search**: Semantic retrieval for consistency

### Quality Assurance

- **Continuity Audits**: Automated plot hole detection
- **Style Enforcement**: Consistent voice and tone
- **Safety Checks**: Content moderation
- **Human Authenticity**: Naturalness scoring

## 🤝 Contributing

Contributions are welcome! Please see [DEVELOPMENT.md](prometheus_novel/docs/DEVELOPMENT.md) for guidelines.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `make test`
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [OpenAI](https://openai.com/), [Google Gemini](https://deepmind.google/technologies/gemini/), and [Anthropic](https://www.anthropic.com/) APIs
- Uses [LangChain](https://www.langchain.com/) and [LangGraph](https://www.langchain.com/langgraph) for orchestration
- Powered by [FastAPI](https://fastapi.tiangolo.com/), [Pydantic](https://docs.pydantic.dev/), and [Poetry](https://python-poetry.org/)

## 📧 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/writerai/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/writerai/discussions)
- **Email**: support@writerai.example.com

## 🗺️ Roadmap

- [ ] Web-based project creator
- [ ] Real-time generation dashboard
- [ ] Collaborative editing features
- [ ] Export to multiple formats (PDF, EPUB, DOCX)
- [ ] Integration with publishing platforms
- [ ] Multi-language support
- [ ] Custom model fine-tuning

---

**Made with ❤️ by the WriterAI Team**

*Transform your ideas into novels, one stage at a time.*
