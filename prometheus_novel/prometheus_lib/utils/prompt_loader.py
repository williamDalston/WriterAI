# Prompt loading and caching utilities
import os
from pathlib import Path
import functools
import logging
from typing import Any
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

# Initialize Jinja2 environment globally for prompt loading
# Assumes 'prompts' directory is at the project root
_jinja_env = Environment(loader=FileSystemLoader(Path(__file__).parents[2] / "prompts"))

@functools.lru_cache(maxsize=128) # Cache loaded prompt templates
def load_prompt_template(template_name: str, prompt_set_dir: str = "default") -> Any: # Returns a Jinja2 Template object
    '''
    Loads a Jinja2 prompt template from the specified prompt set directory.
    Templates are cached in memory.

    Args:
        template_name (str): The name of the template file (e.g., 'write_scene_prompt.txt').
        prompt_set_dir (str): The subdirectory within 'prompts/' to load from (e.g., 'default', 'experimental_v2').

    Returns:
        jinja2.Template: The loaded Jinja2 template object.

    Raises:
        FileNotFoundError: If the template file does not exist.
    '''
    full_template_path = Path(prompt_set_dir) / template_name
    try:
        template = _jinja_env.get_template(str(full_template_path))
        logger.debug(f"Loaded prompt template: {full_template_path}")
        return template
    except Exception as e: # Jinja2 can raise TemplateNotFound or other errors
        logger.error(f"Failed to load prompt template '{full_template_path}': {e}")
        raise FileNotFoundError(f"Prompt template '{full_template_path}' not found or invalid: {e}")

if __name__ == '__main__':
    # Example usage
    try:
        template = load_prompt_template("high_concept_prompt.txt", "default")
        rendered_prompt = template.render(novel_synopsis="A test synopsis.")
        print(f"Loaded and rendered a default prompt:\n{rendered_prompt[:100]}...")

        template_v2 = load_prompt_template("high_concept_prompt.txt", "experimental_v2")
        rendered_prompt_v2 = template_v2.render(novel_synopsis="Another test synopsis.")
        print(f"\nLoaded and rendered an experimental prompt:\n{rendered_prompt_v2[:100]}...")

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
