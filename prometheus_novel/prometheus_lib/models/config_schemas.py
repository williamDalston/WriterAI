# Pydantic schema for config validation
from pydantic import BaseModel, Field, PositiveFloat, ValidationError, validator, RootModel
from typing import Dict, Optional

class ModelDefaults(BaseModel):
    local_model: str
    api_model: str
    critic_model: str
    fallback_model: Optional[str] = None

# Use RootModel in Pydantic v2
class StageModelMap(RootModel[Dict[str, str]]):
    pass

class ConfigSchema(BaseModel):
    project_name: str
    budget_usd: float = Field(..., ge=0, description="Total budget in USD. Use 0 for local (free) models.")
    model_defaults: ModelDefaults
    stage_model_map: StageModelMap
    prompt_set_directory: str = Field("prompts/default", description="Directory containing prompt templates.")
    # Add other configuration parameters here as needed

    @validator('budget_usd')
    def budget_must_be_reasonable(cls, v):
        if v < 0:
            raise ValueError("Budget cannot be negative.")
        if v > 0 and v < 1:
            raise ValueError("Budget must be at least $1.00 for API models, or $0 for local-only.")
        if v > 10000.0: # Example: maximum budget to prevent accidental large spends
            print("Warning: Very large budget specified. Ensure this is intentional.")
        return v

    @validator('model_defaults')
    def all_default_models_must_be_defined(cls, v, values):
        # This validator would ideally check against a global list of available models
        # For now, it ensures fallback_model is valid if specified
        if v.fallback_model and v.fallback_model not in v.model_dump().values():
            # This check is more complex as fallback_model refers to a name, not a key
            # A more robust check would be in model_router.py's __init__
            pass # Placeholder
        return v

    @validator('stage_model_map')
    def stage_models_must_map_to_defaults(cls, v, values):
        if 'model_defaults' in values:
            default_models = values['model_defaults'].model_dump().keys()
            for stage, model_key in v.root.items():
                if model_key not in default_models:
                    raise ValueError(f"Stage '{stage}' maps to unknown model key '{model_key}'. Must be one of {list(default_models)}")
        return v

    # Convenience helper so the rest of your code reads cleanly
    def stage_map(self) -> Dict[str, str]:
        return self.stage_model_map.root

if __name__ == '__main__':
    # Example usage and validation test
    config_data = {
        "project_name": "Test Novel",
        "budget_usd": 50.0,
        "model_defaults": {
            "local_model": "gpt-local",
            "api_model": "gpt-4o-mini",
            "critic_model": "gpt-4o-mini-nano",
            "fallback_model": "gpt-3.5-turbo"
        },
        "stage_model_map": {
            "high_concept": "local_model",
            "write_scene": "api_model",
            "self_refine": "critic_model"
        },
        "prompt_set_directory": "prompts/default"
    }

    try:
        config = ConfigSchema(**config_data)
        print("Config validated successfully!")
        print(config.model_dump_json(indent=2))
    except ValidationError as e:
        print("Config validation failed:")
        print(e.json())

    # Test with invalid budget
    invalid_config_data = config_data.copy()
    invalid_config_data["budget_usd"] = 0.5  # Between 0 and 1 is invalid
    try:
        ConfigSchema(**invalid_config_data)
    except ValidationError as e:
        print("\nInvalid budget test passed (expected error):")
        print(e.json())
