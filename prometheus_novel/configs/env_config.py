# Centralized environment config loader
from pathlib import Path
import os
from prometheus_lib.models.config_schemas import ConfigSchema
import yaml # Added for config loading

def load_config(env: str = None) -> ConfigSchema:
    # Determine the config file path based on environment
    config_name = f"{env}_config.yaml" if env else "the_empathy_clause.yaml"
    config_path = Path(__file__).parent / config_name

    if not config_path.exists():
        if env:
            print(f"Warning: Environment-specific config '{config_name}' not found. Falling back to 'the_empathy_clause.yaml'.")
            config_path = Path(__file__).parent / "the_empathy_clause.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Default config 'the_empathy_clause.yaml' not found at {config_path}. Please create it.")

    print(f"Loading configuration from: {config_path}")
    with open(config_path, 'r') as f:
        raw_config = yaml.safe_load(f)

    # Validate config using Pydantic schema
    config = ConfigSchema.model_validate(raw_config) # Use model_validate for Pydantic v2
    print(f"Active config for project: {config.project_name}")
    return config

if __name__ == '__main__':
    # Example usage:
    try:
        # Load default config or from env var PROMETHEUS_ENV
        current_env = os.getenv("PROMETHEUS_ENV")
        loaded_config = load_config(current_env)
        print(f"Successfully loaded config for {loaded_config.project_name}")
    except Exception as e:
        print(f"Error loading configuration: {e}")
