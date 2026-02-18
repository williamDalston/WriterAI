"""
WriterAI CLI - Command Line Interface

Provides command-line access to novel generation functionality:
- Create new projects interactively or from files
- Generate novels from existing projects
- Compile output to various formats
- Manage ideas and settings
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Optional
import argparse
import json

# Fix Windows cp1252 encoding — allow Unicode in log output (arrows, deltas, etc.)
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env so API keys are available to LLM clients
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(usecwd=True))

try:
    import yaml
except ImportError:
    print("Installing PyYAML...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml"])
    import yaml

from prometheus_lib.utils.logging_config import setup_logging
import logging

setup_logging()
logger = logging.getLogger("writerai.cli")

# ANSI colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    # Aliases for call sites that use RED/YELLOW
    RED = FAIL
    YELLOW = WARNING


def print_banner():
    """Print the WriterAI banner."""
    banner = f"""
{Colors.CYAN}================================================================
                      {Colors.BOLD}WriterAI{Colors.END}{Colors.CYAN}
          {Colors.GREEN}AI-Powered Novel Generation System{Colors.CYAN}
================================================================{Colors.END}
"""
    print(banner)


def print_success(msg: str):
    """Print success message."""
    print(f"{Colors.GREEN}[OK] {msg}{Colors.END}")


def print_error(msg: str):
    """Print error message."""
    print(f"{Colors.FAIL}[ERROR] {msg}{Colors.END}")


def print_info(msg: str):
    """Print info message."""
    print(f"{Colors.BLUE}[INFO] {msg}{Colors.END}")


def print_warning(msg: str):
    """Print warning message."""
    print(f"{Colors.WARNING}[WARN] {msg}{Colors.END}")


# ============================================================================
# Genre Templates
# ============================================================================

GENRE_TEMPLATES = {
    "sci-fi": {
        "themes": ["technology", "humanity", "exploration", "progress"],
        "conflicts": ["man vs machine", "survival", "identity", "ethics"],
        "archetypes": ["scientist", "pilot", "AI", "rebel"]
    },
    "fantasy": {
        "themes": ["magic", "destiny", "good vs evil", "coming of age"],
        "conflicts": ["quest", "war", "dark lord", "ancient prophecy"],
        "archetypes": ["wizard", "warrior", "chosen one", "mentor"]
    },
    "mystery": {
        "themes": ["truth", "justice", "deception", "obsession"],
        "conflicts": ["whodunit", "cover-up", "cold case", "conspiracy"],
        "archetypes": ["detective", "suspect", "victim", "witness"]
    },
    "thriller": {
        "themes": ["survival", "paranoia", "corruption", "revenge"],
        "conflicts": ["chase", "conspiracy", "countdown", "psychological"],
        "archetypes": ["protagonist", "antagonist", "ally", "double agent"]
    },
    "romance": {
        "themes": ["love", "fate", "sacrifice", "growth"],
        "conflicts": ["forbidden love", "misunderstanding", "rivalry", "timing"],
        "archetypes": ["lovers", "rival", "matchmaker", "obstacle"]
    },
    "literary": {
        "themes": ["identity", "mortality", "society", "relationships"],
        "conflicts": ["internal", "familial", "societal", "existential"],
        "archetypes": ["everyman", "outcast", "mentor", "shadow self"]
    }
}


# ============================================================================
# Commands
# ============================================================================

def cmd_new(args):
    """Create a new novel project."""
    print_banner()

    if args.interactive:
        # Interactive mode
        print(f"\n{Colors.HEADER}Create New Project{Colors.END}\n")

        name = input("Project name (slug): ").strip()
        if not name:
            print_error("Project name is required")
            return 1

        title = input("Novel title: ").strip() or name.replace("-", " ").title()

        print("\nAvailable genres:")
        for i, genre in enumerate(GENRE_TEMPLATES.keys(), 1):
            print(f"  {i}. {genre}")
        genre_idx = input("Select genre (1-6): ").strip()
        try:
            genre = list(GENRE_TEMPLATES.keys())[int(genre_idx) - 1]
        except (ValueError, IndexError):
            genre = "literary"

        synopsis = input("\nSynopsis (or press Enter to skip): ").strip()
        if not synopsis:
            synopsis = input("One-sentence premise: ").strip()

    elif args.from_file:
        # Load from file
        file_path = Path(args.from_file)
        if not file_path.exists():
            print_error(f"File not found: {file_path}")
            return 1

        content = file_path.read_text(encoding="utf-8")
        # Parse simple format: Title, Genre, Synopsis
        lines = content.strip().split("\n")
        name = lines[0].lower().replace(" ", "-") if lines else "untitled"
        title = lines[0] if lines else "Untitled"
        genre = lines[1].lower() if len(lines) > 1 else "literary"
        synopsis = "\n".join(lines[2:]) if len(lines) > 2 else ""

    else:
        # Command line arguments
        name = args.name or (args.title.lower().replace(" ", "-") if args.title else "untitled")
        title = args.title or name.replace("-", " ").title()
        genre = args.genre or "literary"
        synopsis = args.synopsis or ""

    # Sanitize and validate
    import re as _re
    name = _re.sub(r'[^a-z0-9_-]', '', name.lower())
    if not name:
        print_error("Project name is required (must contain alphanumeric characters)")
        return 1

    # Create project directory with path traversal guard
    projects_dir = PROJECT_ROOT / "data" / "projects"
    project_dir = (projects_dir / name).resolve()
    if not str(project_dir).startswith(str(projects_dir.resolve())):
        print_error("Invalid project name (path traversal detected)")
        return 1
    project_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (project_dir / "drafts").mkdir(exist_ok=True)
    (project_dir / "output").mkdir(exist_ok=True)
    (project_dir / "memory").mkdir(exist_ok=True)

    # Get genre template
    template = GENRE_TEMPLATES.get(genre, GENRE_TEMPLATES["literary"])

    # Create project config
    config = {
        "project_name": name,
        "title": title,
        "genre": genre,
        "synopsis": synopsis,
        "themes": template["themes"],
        "conflicts": template["conflicts"],
        "archetypes": template["archetypes"],
        "budget_usd": 0,
        "model_defaults": {
            "local_model": "qwen2.5:7b",
            "api_model": "qwen2.5:7b",
            "critic_model": "qwen2.5:7b",
            "fallback_model": "qwen2.5:7b"
        },
        "stage_model_map": {
            "high_concept": "api_model",
            "beat_sheet": "api_model",
            "write_scene": "api_model",
            "self_refine": "critic_model"
        },
        "status": "created"
    }

    config_file = project_dir / "config.yaml"
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False)

    print_success(f"Project created: {project_dir}")
    print_info(f"Config saved to: {config_file}")

    if not args.auto_confirm:
        print(f"\n{Colors.CYAN}Next steps:{Colors.END}")
        print(f"  1. Edit {config_file} to customize your project")
        print(f"  2. Run: python -m prometheus_novel.interfaces.cli.main generate --config {config_file}")

    return 0


def cmd_generate(args):
    """Generate a novel from a project config."""
    print_banner()

    config_path = Path(args.config)
    if not config_path.exists():
        print_error(f"Config file not found: {config_path}")
        return 1

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    print(f"\n{Colors.HEADER}Generating Novel: {config.get('title', 'Untitled')}{Colors.END}\n")
    print_info(f"Genre: {config.get('genre', 'unknown')}")
    print_info(f"Budget: ${config.get('budget_usd', 100)}")

    # Set up LLM clients (same pattern as web dashboard)
    from prometheus_lib.llm.clients import get_client, is_ollama_model
    from stages.pipeline import PipelineOrchestrator

    model_defaults = config.get("model_defaults", {})
    api_model = model_defaults.get("api_model", "qwen2.5:7b")
    critic_model = model_defaults.get("critic_model", api_model)
    fallback_model = model_defaults.get("fallback_model", api_model)

    llm_clients = {}
    default_client = get_client(api_model)
    llm_clients["gpt"] = default_client
    llm_clients["claude"] = get_client(critic_model)
    llm_clients["gemini"] = get_client(fallback_model)

    local_tag = "Ollama" if is_ollama_model(api_model) else "API"
    print_info(f"Model: {api_model} ({local_tag})")
    if critic_model != api_model:
        print_info(f"Critic: {critic_model}")
    if fallback_model != api_model:
        print_info(f"Fallback: {fallback_model}")

    project_path = config_path.parent
    orchestrator = PipelineOrchestrator(
        project_path,
        llm_client=default_client,
        llm_clients=llm_clients
    )

    # Determine stage range
    all_stages = orchestrator.STAGES
    stages_to_run = None  # None = all stages (default)

    if args.stage:
        # Single stage
        if args.stage not in all_stages:
            print_error(f"Unknown stage: {args.stage}")
            print_info(f"Available stages: {', '.join(all_stages)}")
            return 1
        stages_to_run = [args.stage]
        print_info(f"Running single stage: {args.stage}")

    elif args.start_stage or args.end_stage:
        # Stage range
        start = args.start_stage or all_stages[0]
        end = args.end_stage or all_stages[-1]

        if start not in all_stages:
            print_error(f"Unknown start stage: {start}")
            print_info(f"Available stages: {', '.join(all_stages)}")
            return 1
        if end not in all_stages:
            print_error(f"Unknown end stage: {end}")
            print_info(f"Available stages: {', '.join(all_stages)}")
            return 1

        start_idx = all_stages.index(start)
        end_idx = all_stages.index(end)
        if start_idx > end_idx:
            print_error(f"Start stage '{start}' comes after end stage '{end}'")
            return 1

        stages_to_run = all_stages[start_idx:end_idx + 1]
        print_info(f"Running stages {start} -> {end} ({len(stages_to_run)} stages)")

    else:
        print_info(f"Running full {len(all_stages)}-stage pipeline")

    # When user explicitly requested specific stages, load checkpoint so we have scenes/outline etc.
    resume = args.resume
    if not resume and stages_to_run is not None:
        checkpoint = project_path / "pipeline_state.json"
        if checkpoint.exists():
            resume = True
            print_info("Loading checkpoint (required for stage-range runs)")

    if resume:
        print_info("Resuming from last checkpoint")

    # List stages if --list-stages
    if getattr(args, 'list_stages', False):
        print(f"\n{Colors.CYAN}Available stages ({len(all_stages)}):{Colors.END}\n")
        for i, s in enumerate(all_stages, 1):
            print(f"  {i:2d}. {s}")
        return 0

    # Run
    print(f"\n{Colors.CYAN}Starting pipeline...{Colors.END}\n")

    async def _run():
        return await orchestrator.run(stages=stages_to_run, resume=resume)

    try:
        final_state = asyncio.run(_run())
    except KeyboardInterrupt:
        print_warning("\nPipeline interrupted. State saved at last checkpoint.")
        return 1
    except Exception as e:
        print_error(f"Pipeline failed: {e}")
        return 1

    print_success("\nPipeline complete!")
    if hasattr(final_state, 'total_tokens'):
        print_info(f"Total tokens: {final_state.total_tokens:,}")
    if hasattr(final_state, 'total_cost_usd'):
        print_info(f"Total cost: ${final_state.total_cost_usd:.4f}")
    print_info(f"Output: {project_path / 'output'}")

    return 0


def cmd_compile(args):
    """Compile novel to output format."""
    print_banner()

    config_path = Path(args.config)
    if not config_path.exists():
        print_error(f"Config file not found: {config_path}")
        return 1

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    output_format = args.format or "html"
    project_dir = config_path.parent
    output_dir = project_dir / "output"
    output_dir.mkdir(exist_ok=True)

    print(f"\n{Colors.HEADER}Compiling: {config.get('title', 'Untitled')}{Colors.END}")
    print_info(f"Format: {output_format.upper()}")

    # Generate output file
    output_file = output_dir / f"{config.get('project_name', 'novel')}.{output_format}"

    if output_format == "html":
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{config.get('title', 'Untitled')}</title>
    <style>
        body {{ font-family: Georgia, serif; max-width: 800px; margin: 40px auto; padding: 20px; }}
        h1 {{ text-align: center; }}
    </style>
</head>
<body>
    <h1>{config.get('title', 'Untitled')}</h1>
    <p><em>{config.get('synopsis', '')}</em></p>
    <hr>
    <p>[Novel content would be compiled here]</p>
</body>
</html>"""
        output_file.write_text(html_content, encoding="utf-8")

    elif output_format == "markdown":
        md_content = f"""# {config.get('title', 'Untitled')}

*{config.get('synopsis', '')}*

---

[Novel content would be compiled here]
"""
        output_file.write_text(md_content, encoding="utf-8")

    print_success(f"Compiled to: {output_file}")
    return 0


def cmd_ideas(args):
    """Manage ideas."""
    ideas_file = PROJECT_ROOT / "data" / "ideas.json"

    if args.add:
        # Add new idea
        ideas = []
        if ideas_file.exists():
            ideas = json.loads(ideas_file.read_text(encoding="utf-8"))

        idea = {
            "id": len(ideas) + 1,
            "content": args.add,
            "source": "cli",
            "tags": args.tags.split(",") if args.tags else []
        }
        ideas.append(idea)

        ideas_file.parent.mkdir(parents=True, exist_ok=True)
        ideas_file.write_text(json.dumps(ideas, indent=2), encoding="utf-8")
        print_success(f"Idea #{idea['id']} saved")

    elif args.list:
        # List ideas
        if not ideas_file.exists():
            print_info("No ideas saved yet")
            return 0

        ideas = json.loads(ideas_file.read_text(encoding="utf-8"))
        print(f"\n{Colors.HEADER}Your Ideas{Colors.END}\n")
        for idea in ideas:
            print(f"  #{idea['id']}: {idea['content'][:60]}...")
            if idea.get('tags'):
                print(f"       Tags: {', '.join(idea['tags'])}")

    return 0


def cmd_editor_studio(args):
    """Run Editor Studio — surgical refinement passes on completed manuscript."""
    print_banner()
    project_path = None
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            print_error(f"Config not found: {config_path}")
            return 1
        project_path = config_path.parent
    elif args.project:
        project_path = Path(args.project)
    else:
        # Default to burning-vows-30k for convenience
        project_path = PROJECT_ROOT / "data" / "projects" / "burning-vows-30k"
    if not project_path.exists():
        print_error(f"Project not found: {project_path}")
        return 1
    passes_enabled = [p.strip() for p in (args.passes or "").split(",") if p.strip()] or None
    if args.dry_run:
        state_file = project_path / "pipeline_state.json"
        contract_file = project_path / "output" / "quality_contract.json"
        print(f"\n{Colors.HEADER}[DRY RUN] Editor Studio{Colors.END}\n")
        print_info(f"Project: {project_path}")
        print_info(f"pipeline_state.json: {'found' if state_file.exists() else 'MISSING'}")
        print_info(f"quality_contract.json: {'found' if contract_file.exists() else 'MISSING'}")
        print_info(f"Passes: {passes_enabled or 'all'}")
        return 0
    print(f"\n{Colors.HEADER}Editor Studio — Surgical Refinement{Colors.END}\n")
    print_info(f"Project: {project_path}")
    config_path = project_path / "config.yaml"
    config = {}
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    from prometheus_lib.llm.clients import get_client
    defaults = config.get("model_defaults", {}) or {}
    model = defaults.get("critic_model") or defaults.get("api_model") or "gpt-4o-mini"
    print_info(f"Model: {model}")

    async def _run():
        from editor_studio.orchestrator import run_editor_studio
        client = get_client(model)
        return await run_editor_studio(project_path, passes_enabled=passes_enabled, client=client)

    try:
        report = asyncio.run(_run())
    except Exception as e:
        print_error(f"Editor Studio failed: {e}")
        return 1
    if report.get("errors"):
        for e in report["errors"]:
            print_error(str(e))
        return 1
    print_success("\nEditor Studio complete!")
    print_info(f"Scenes modified: {report.get('scenes_modified', 0)}")
    for p in report.get("passes_run", []):
        print_info(f"  {p.get('pass')}: {p.get('scenes_modified', 0)}/{p.get('scenes_processed', 0)} scenes")
    return 0


def cmd_serve(args):
    """Start the web server."""
    print_banner()
    print(f"\n{Colors.HEADER}Starting Web Server{Colors.END}\n")
    print_info(f"Host: {args.host}")
    print_info(f"Port: {args.port}")
    print(f"\n  Open: {Colors.CYAN}http://{args.host}:{args.port}{Colors.END}\n")

    # Import and run the web app
    from interfaces.web.app import app
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)


def cmd_seed(args):
    """Flexible story seed input."""
    from interfaces.cli.seed import main as seed_main
    # Pass through the args
    import sys
    original_argv = sys.argv
    new_argv = ["writerai-seed"]
    if args.mode:
        new_argv.extend(["--mode", args.mode])
    if args.file:
        new_argv.extend(["--file", args.file])
    if args.no_expand:
        new_argv.append("--no-expand")
    sys.argv = new_argv
    result = seed_main()
    sys.argv = original_argv
    return result


def cmd_audiobook(args):
    """Generate ACX-compliant audiobook MP3s from pipeline scenes."""
    print_banner()
    config_path = Path(args.config)
    if not config_path.exists():
        print_error(f"Config file not found: {config_path}")
        return 1

    print(f"\n{Colors.HEADER}Audiobook: Generating ACX-Compliant MP3s{Colors.END}\n")

    import asyncio

    async def _run():
        from audiobook.engine import AudiobookEngine
        engine = AudiobookEngine.from_config_path(config_path)

        # Cost estimation first
        cost_info = engine.estimate_cost()
        print_info(f"Chapters: {cost_info['chapters']}")
        print_info(f"Characters: {cost_info['estimated_total_chars']:,}")
        print_info(f"Estimated cost: ${cost_info['estimated_cost_usd']:.2f}")
        print_info(f"Voice: {engine.audiobook_config['voice_default']}")

        if engine.audiobook_config.get("voice_map"):
            voice_count = len(engine.audiobook_config["voice_map"])
            print_info(f"Multi-voice: {voice_count} character voice(s)")

        # Dry run mode
        if getattr(args, "dry_run", False):
            print_info("Dry run mode — no audio generated")
            return {"dry_run": True, **cost_info}

        # Confirm cost (unless --yes flag)
        if not getattr(args, "yes", False):
            confirm = input(
                f"\nProceed with generation? "
                f"(estimated ${cost_info['estimated_cost_usd']:.2f}) [y/N]: "
            ).strip().lower()
            if confirm != "y":
                print_warning("Aborted by user")
                return {"aborted": True}

        force = getattr(args, "force", False)
        chapter_filter = None
        if hasattr(args, "chapters") and args.chapters:
            chapter_filter = [int(c) for c in args.chapters]

        result = await engine.generate_all(
            force=force,
            chapter_filter=chapter_filter,
        )
        engine.print_summary()
        return result

    try:
        result = asyncio.run(_run())
        if result.get("aborted") or result.get("dry_run"):
            return 0
        if result.get("errors"):
            print_warning(f"{len(result['errors'])} error(s) during generation")
        else:
            print_success("All audiobook files generated successfully")
        return 0
    except FileNotFoundError as e:
        print_error(str(e))
        return 1
    except RuntimeError as e:
        print_error(str(e))
        return 1
    except Exception as e:
        print_error(f"Audiobook generation failed: {e}")
        return 1


def cmd_bookops(args):
    """Generate BookOps launch assets and revision guidance."""
    print_banner()
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"{Colors.RED}Config file not found: {config_path}{Colors.END}")
        return 1

    print(f"\n{Colors.HEADER}BookOps: Generating Launch & Revision Assets{Colors.END}\n")

    import asyncio

    async def _run():
        from bookops.engine import BookOpsEngine
        engine = BookOpsEngine.from_config_path(
            config_path,
            model_override=getattr(args, "model", None),
        )
        doc_filter = args.docs if hasattr(args, "docs") and args.docs else None
        force = getattr(args, "force", False)
        result = await engine.generate_all(doc_filter=doc_filter, force=force)
        engine.print_summary()
        return result

    try:
        result = asyncio.run(_run())
        if result.get("passed"):
            print(f"{Colors.GREEN}All self-checks passed.{Colors.END}")
        else:
            print(f"{Colors.YELLOW}Self-check issues found — see _self_check_report.md{Colors.END}")
        return 0
    except Exception as e:
        print(f"{Colors.RED}BookOps failed: {e}{Colors.END}")
        return 1


def cmd_cover(args):
    """Generate book cover artwork for KDP."""
    print_banner()
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"{Colors.RED}Config file not found: {config_path}{Colors.END}")
        return 1

    print(f"\n{Colors.HEADER}CoverGen: Generating Book Cover{Colors.END}\n")

    import asyncio

    async def _run():
        from covergen.engine import CoverEngine
        engine = CoverEngine.from_config_path(
            config_path,
            style=getattr(args, "style", None),
            trim_size=getattr(args, "trim_size", None),
            page_count=getattr(args, "page_count", None),
            author_name=getattr(args, "author", None),
            model_override=getattr(args, "model", None),
        )

        if getattr(args, "ebook_only", False):
            result = await engine.generate_ebook_cover()
        elif getattr(args, "print_only", False):
            result = await engine.generate_print_cover()
        else:
            result = await engine.generate_all()

        engine.print_summary()
        return result

    try:
        result = asyncio.run(_run())
        if result.get("errors"):
            print(f"{Colors.YELLOW}Some steps had errors — see cover_report.md{Colors.END}")
        else:
            print(f"{Colors.GREEN}Cover generation complete.{Colors.END}")
        return 0
    except Exception as e:
        print(f"{Colors.RED}Cover generation failed: {e}{Colors.END}")
        return 1


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="writerai",
        description="WriterAI - AI-Powered Novel Generation"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # new command
    new_parser = subparsers.add_parser("new", help="Create a new novel project")
    new_parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    new_parser.add_argument("--from-file", "-f", help="Create from text file")
    new_parser.add_argument("--name", help="Project name (slug)")
    new_parser.add_argument("--title", help="Novel title")
    new_parser.add_argument("--genre", help="Genre (sci-fi, fantasy, mystery, thriller, romance, literary)")
    new_parser.add_argument("--synopsis", help="Novel synopsis")
    new_parser.add_argument("--auto-confirm", action="store_true", help="Skip confirmation prompts")

    # generate command
    gen_parser = subparsers.add_parser("generate", help="Generate novel from project")
    gen_parser.add_argument("--config", "-c", required=True, help="Path to project config.yaml")
    gen_parser.add_argument("--all", action="store_true", help="Run all stages")
    gen_parser.add_argument("--stage", help="Run a single specific stage")
    gen_parser.add_argument("--start-stage", dest="start_stage", help="Start from this stage (inclusive)")
    gen_parser.add_argument("--end-stage", dest="end_stage", help="Stop after this stage (inclusive)")
    gen_parser.add_argument("--list-stages", dest="list_stages", action="store_true", help="List all pipeline stages and exit")
    gen_parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")

    # compile command
    compile_parser = subparsers.add_parser("compile", help="Compile novel to output format")
    compile_parser.add_argument("--config", "-c", required=True, help="Path to project config.yaml")
    compile_parser.add_argument("--format", choices=["html", "epub", "markdown", "docx"], default="html")

    # ideas command
    ideas_parser = subparsers.add_parser("ideas", help="Manage ideas")
    ideas_parser.add_argument("--add", "-a", help="Add a new idea")
    ideas_parser.add_argument("--tags", "-t", help="Comma-separated tags")
    ideas_parser.add_argument("--list", "-l", action="store_true", help="List all ideas")

    # serve command
    serve_parser = subparsers.add_parser("serve", help="Start web server")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    serve_parser.add_argument("--port", type=int, default=8080, help="Port to bind to")

    # seed command - flexible story input
    seed_parser = subparsers.add_parser("seed", help="Seed a project with flexible story input")
    seed_parser.add_argument("--mode", choices=["full", "guided", "minimal"],
                             help="Input mode (skip menu)")
    seed_parser.add_argument("--file", "-f", help="Load seed from template file")
    seed_parser.add_argument("--no-expand", action="store_true",
                             help="Don't use AI to expand missing sections")

    # bookops command - generate launch assets & revision guidance
    bookops_parser = subparsers.add_parser("bookops", help="Generate launch assets & revision guidance")
    bookops_parser.add_argument("--config", "-c", required=True, help="Path to project config.yaml")
    bookops_parser.add_argument("--model", "-m", help="Override LLM model (e.g., claude-sonnet-4-20250514)")
    bookops_parser.add_argument("--docs", nargs="*", help="Generate specific docs only (e.g., 01 02 05)")
    bookops_parser.add_argument("--force", action="store_true", help="Overwrite existing bookops output")

    # cover command - generate book cover artwork
    cover_parser = subparsers.add_parser("cover", help="Generate book cover artwork for KDP")
    cover_parser.add_argument("--config", "-c", required=True, help="Path to project config.yaml")
    cover_parser.add_argument("--style", "-s",
        choices=["cinematic", "illustrated", "minimalist", "dark", "romantic", "literary"],
        help="Visual style preset (default: auto-detect from genre)")
    cover_parser.add_argument("--trim-size", dest="trim_size",
        choices=["6x9", "5.5x8.5", "5x8"],
        help="Print trim size in inches (default: 6x9)")
    cover_parser.add_argument("--page-count", dest="page_count", type=int,
        help="Page count for spine width calculation (default: 300)")
    cover_parser.add_argument("--author", help="Author name for cover")
    cover_parser.add_argument("--model", "-m", help="Override LLM model for art direction")
    cover_parser.add_argument("--ebook-only", dest="ebook_only", action="store_true",
        help="Generate eBook cover only")
    cover_parser.add_argument("--print-only", dest="print_only", action="store_true",
        help="Generate print cover only")
    cover_parser.add_argument("--force", action="store_true",
        help="Overwrite existing cover files")

    # editor-studio command - surgical refinement passes on completed manuscript
    studio_parser = subparsers.add_parser(
        "editor-studio",
        help="Surgical refinement passes on completed manuscript (continuity, dialogue, stakes, etc.)",
    )
    studio_parser.add_argument(
        "--config", "-c",
        help="Path to project config.yaml (project_path = config.parent)",
    )
    studio_parser.add_argument(
        "--project", "-p",
        help="Path to project dir (alternative to --config)",
    )
    studio_parser.add_argument(
        "--passes",
        help="Comma-separated passes: continuity,dialogue_friction,stakes,final_line,voice,premium (default: all)",
    )
    studio_parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Show what would run, no changes")

    # audiobook command - generate ACX-compliant audiobook MP3s
    audio_parser = subparsers.add_parser("audiobook", help="Generate ACX-compliant audiobook MP3s")
    audio_parser.add_argument("--config", "-c", required=True, help="Path to project config.yaml")
    audio_parser.add_argument("--force", action="store_true", help="Overwrite existing MP3 files")
    audio_parser.add_argument("--dry-run", dest="dry_run", action="store_true",
                              help="Estimate cost only, don't generate")
    audio_parser.add_argument("--yes", "-y", action="store_true",
                              help="Skip cost confirmation prompt")
    audio_parser.add_argument("--chapters", nargs="*", type=int,
                              help="Generate specific chapters only (e.g., --chapters 1 5 12)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # Dispatch to command handler
    commands = {
        "new": cmd_new,
        "generate": cmd_generate,
        "compile": cmd_compile,
        "ideas": cmd_ideas,
        "serve": cmd_serve,
        "seed": cmd_seed,
        "bookops": cmd_bookops,
        "cover": cmd_cover,
        "editor-studio": cmd_editor_studio,
        "audiobook": cmd_audiobook,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
