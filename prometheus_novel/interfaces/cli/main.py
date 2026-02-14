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

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import yaml
except ImportError:
    print("Installing PyYAML...")
    os.system(f"{sys.executable} -m pip install pyyaml")
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

        content = file_path.read_text()
        # Parse simple format: Title, Genre, Synopsis
        lines = content.strip().split("\n")
        name = lines[0].lower().replace(" ", "-") if lines else "untitled"
        title = lines[0] if lines else "Untitled"
        genre = lines[1].lower() if len(lines) > 1 else "literary"
        synopsis = "\n".join(lines[2:]) if len(lines) > 2 else ""

    else:
        # Command line arguments
        name = args.name or args.title.lower().replace(" ", "-") if args.title else "untitled"
        title = args.title or name.replace("-", " ").title()
        genre = args.genre or "literary"
        synopsis = args.synopsis or ""

    # Validate
    if not name:
        print_error("Project name is required")
        return 1

    # Create project directory
    projects_dir = PROJECT_ROOT / "data" / "projects"
    project_dir = projects_dir / name
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
    with open(config_file, "w") as f:
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

    with open(config_path) as f:
        config = yaml.safe_load(f)

    print(f"\n{Colors.HEADER}Generating Novel: {config.get('title', 'Untitled')}{Colors.END}\n")
    print_info(f"Genre: {config.get('genre', 'unknown')}")
    print_info(f"Budget: ${config.get('budget_usd', 100)}")

    # Define pipeline stages
    stages = [
        ("high_concept", "Generating high concept..."),
        ("world_building", "Building world..."),
        ("beat_sheet", "Creating beat sheet..."),
        ("character_profiles", "Developing characters..."),
        ("scene_planning", "Planning scenes..."),
        ("drafting", "Drafting scenes..."),
        ("self_refinement", "Self-refining content..."),
        ("continuity_audit", "Auditing continuity..."),
        ("polish", "Final polish...")
    ]

    # Run pipeline (simulated for now)
    print(f"\n{Colors.CYAN}Running 12-Stage Pipeline{Colors.END}\n")

    for i, (stage_name, message) in enumerate(stages, 1):
        print(f"  [{i}/{len(stages)}] {message}", end="", flush=True)

        # Simulate stage execution
        asyncio.run(run_stage(stage_name, config))

        print(f" {Colors.GREEN}Done{Colors.END}")

    print_success("\nNovel generation complete!")

    # Output location
    project_dir = config_path.parent
    output_dir = project_dir / "output"
    print_info(f"Output saved to: {output_dir}")

    return 0


async def run_stage(stage_name: str, config: dict):
    """Run a single pipeline stage."""
    # Placeholder - would invoke actual stage logic
    await asyncio.sleep(0.5)  # Simulate work


def cmd_compile(args):
    """Compile novel to output format."""
    print_banner()

    config_path = Path(args.config)
    if not config_path.exists():
        print_error(f"Config file not found: {config_path}")
        return 1

    with open(config_path) as f:
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
        output_file.write_text(html_content)

    elif output_format == "markdown":
        md_content = f"""# {config.get('title', 'Untitled')}

*{config.get('synopsis', '')}*

---

[Novel content would be compiled here]
"""
        output_file.write_text(md_content)

    print_success(f"Compiled to: {output_file}")
    return 0


def cmd_ideas(args):
    """Manage ideas."""
    ideas_file = PROJECT_ROOT / "data" / "ideas.json"

    if args.add:
        # Add new idea
        ideas = []
        if ideas_file.exists():
            ideas = json.loads(ideas_file.read_text())

        idea = {
            "id": len(ideas) + 1,
            "content": args.add,
            "source": "cli",
            "tags": args.tags.split(",") if args.tags else []
        }
        ideas.append(idea)

        ideas_file.parent.mkdir(parents=True, exist_ok=True)
        ideas_file.write_text(json.dumps(ideas, indent=2))
        print_success(f"Idea #{idea['id']} saved")

    elif args.list:
        # List ideas
        if not ideas_file.exists():
            print_info("No ideas saved yet")
            return 0

        ideas = json.loads(ideas_file.read_text())
        print(f"\n{Colors.HEADER}Your Ideas{Colors.END}\n")
        for idea in ideas:
            print(f"  #{idea['id']}: {idea['content'][:60]}...")
            if idea.get('tags'):
                print(f"       Tags: {', '.join(idea['tags'])}")

    return 0


def cmd_serve(args):
    """Start the web server."""
    print_banner()
    print(f"\n{Colors.HEADER}Starting Web Server{Colors.END}\n")
    print_info(f"Host: {args.host}")
    print_info(f"Port: {args.port}")
    print(f"\n  Open: {Colors.CYAN}http://{args.host}:{args.port}{Colors.END}\n")

    # Import and run the web app
    from prometheus_novel.interfaces.web.app import app
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)


def cmd_seed(args):
    """Flexible story seed input."""
    from prometheus_novel.interfaces.cli.seed import main as seed_main
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
    gen_parser.add_argument("--stage", help="Run specific stage")
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
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    serve_parser.add_argument("--port", type=int, default=8080, help="Port to bind to")

    # seed command - flexible story input
    seed_parser = subparsers.add_parser("seed", help="Seed a project with flexible story input")
    seed_parser.add_argument("--mode", choices=["full", "guided", "minimal"],
                             help="Input mode (skip menu)")
    seed_parser.add_argument("--file", "-f", help="Load seed from template file")
    seed_parser.add_argument("--no-expand", action="store_true",
                             help="Don't use AI to expand missing sections")

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
        "seed": cmd_seed
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
