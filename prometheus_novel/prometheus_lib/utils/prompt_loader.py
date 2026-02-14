# Prompt loading, caching, and versioning utilities
import hashlib
import time
from pathlib import Path
import functools
import logging
from typing import Any, Dict
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

# Initialize Jinja2 environment globally for prompt loading
_jinja_env = Environment(loader=FileSystemLoader(Path(__file__).parents[2] / "prompts"))

# Track prompt usage for analytics and A/B testing
_prompt_usage_log: list = []


def _hash_template(content: str) -> str:
    """Generate a short hash of template content for versioning."""
    return hashlib.sha256(content.encode()).hexdigest()[:12]


@functools.lru_cache(maxsize=128)
def load_prompt_template(template_name: str, prompt_set_dir: str = "default") -> Any:
    """Load a Jinja2 prompt template from the specified prompt set directory.

    Templates are cached in memory. Each template is version-tracked via content hash.
    """
    full_template_path = Path(prompt_set_dir) / template_name
    try:
        template = _jinja_env.get_template(str(full_template_path))
        logger.debug(f"Loaded prompt template: {full_template_path}")
        return template
    except Exception as e:
        logger.error(f"Failed to load prompt template '{full_template_path}': {e}")
        raise FileNotFoundError(f"Prompt template '{full_template_path}' not found or invalid: {e}")


def render_prompt(
    template_name: str,
    prompt_set_dir: str = "default",
    stage_name: str = "",
    **kwargs
) -> str:
    """Load and render a prompt template with tracking.

    This is the preferred entry point - it loads, renders, and logs prompt usage
    for versioning and analytics.
    """
    template = load_prompt_template(template_name, prompt_set_dir)
    rendered = template.render(**kwargs)

    # Track usage
    version_hash = _hash_template(rendered)
    _prompt_usage_log.append({
        "template": template_name,
        "prompt_set": prompt_set_dir,
        "stage": stage_name,
        "version_hash": version_hash,
        "rendered_length": len(rendered),
        "timestamp": time.time()
    })

    logger.debug(
        f"Rendered prompt '{template_name}' (set={prompt_set_dir}, "
        f"version={version_hash}, {len(rendered)} chars)"
    )
    return rendered


def get_prompt_usage_stats() -> Dict[str, Any]:
    """Get prompt usage statistics for analytics and A/B comparison."""
    if not _prompt_usage_log:
        return {"total_renders": 0, "templates": {}}

    stats: Dict[str, Any] = {
        "total_renders": len(_prompt_usage_log),
        "templates": {}
    }

    for entry in _prompt_usage_log:
        template = entry["template"]
        if template not in stats["templates"]:
            stats["templates"][template] = {
                "render_count": 0,
                "prompt_sets_used": set(),
                "versions_seen": set(),
                "stages": set()
            }
        t = stats["templates"][template]
        t["render_count"] += 1
        t["prompt_sets_used"].add(entry["prompt_set"])
        t["versions_seen"].add(entry["version_hash"])
        t["stages"].add(entry["stage"])

    # Convert sets to lists for JSON serialization
    for template_stats in stats["templates"].values():
        template_stats["prompt_sets_used"] = list(template_stats["prompt_sets_used"])
        template_stats["versions_seen"] = list(template_stats["versions_seen"])
        template_stats["stages"] = list(template_stats["stages"])

    return stats


def list_available_prompt_sets() -> list:
    """List all available prompt set directories."""
    prompts_dir = Path(__file__).parents[2] / "prompts"
    if not prompts_dir.exists():
        return []
    return [d.name for d in prompts_dir.iterdir() if d.is_dir()]


def clear_prompt_cache():
    """Clear the template cache (useful when editing prompts during development)."""
    load_prompt_template.cache_clear()
    logger.info("Prompt template cache cleared.")


if __name__ == '__main__':
    try:
        template = load_prompt_template("high_concept_prompt.txt", "default")
        rendered_prompt = template.render(novel_synopsis="A test synopsis.")
        print(f"Loaded and rendered a default prompt:\n{rendered_prompt[:100]}...")

        print(f"\nAvailable prompt sets: {list_available_prompt_sets()}")
        print(f"Usage stats: {get_prompt_usage_stats()}")

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
