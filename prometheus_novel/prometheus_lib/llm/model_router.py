# Model router for stage selection and cost enforcement
import asyncio
from typing import Any, Dict, Optional, Type
from prometheus_lib.models.config_schemas import ConfigSchema
from prometheus_lib.models.novel_state import PrometheusState
from prometheus_lib.llm.clients import BaseLLMClient, OpenAIClient, GeminiClient # Import your clients
from prometheus_lib.llm.cost_tracker import CostTracker
from prometheus_lib.utils.error_handling import BudgetExceededError, LLMGenerationError
import logging

logger = logging.getLogger(__name__)

class InitializationError(Exception):
    pass

# Map model keys to client classes
MODEL_CLIENT_MAP: Dict[str, Type[BaseLLMClient]] = {
    "gpt-local": OpenAIClient, # Example: map a local name to a client
    "gpt-4o-mini": OpenAIClient,
    "gpt-4o-mini-nano": OpenAIClient,
    "gpt-3.5-turbo": OpenAIClient,
    "gemini-2.0-flash": GeminiClient,
    # Add more mappings as you implement clients
}

class LLMModelRouter:
    def __init__(self, config: ConfigSchema, cost_tracker: CostTracker):
        self.config = config
        self.cost_tracker = cost_tracker
        self._clients: Dict[str, BaseLLMClient] = {} # Cache initialized clients

        # Validate model availability at init
        self._validate_model_availability()

    def _validate_model_availability(self):
        errors = []
        defaults = self.config.model_defaults.model_dump()
        for key, model_name in defaults.items():
            if model_name not in MODEL_CLIENT_MAP:
                errors.append(f"Default '{key}' -> '{model_name}' not mapped in MODEL_CLIENT_MAP.")
        for stage, model_key in self.config.stage_model_map.root.items():
            if model_key not in defaults:
                errors.append(f"Stage '{stage}' uses unknown model key '{model_key}'.")
            else:
                model_name = defaults[model_key]
                if model_name not in MODEL_CLIENT_MAP:
                    errors.append(f"Stage '{stage}' -> '{model_name}' not mapped in MODEL_CLIENT_MAP.")
        if errors:
            raise InitializationError("
".join(errors))


    async def get_client_for_stage(self, stage_name: str, state: PrometheusState) -> BaseLLMClient:
        model_key = self.config.stage_model_map.root.get(stage_name)
        if not model_key:
            raise ValueError(f"No model configured for stage: {stage_name}")

        primary_model_name = self.config.model_defaults.get(model_key)
        if not primary_model_name:
            raise ValueError(f"Model key '{model_key}' not found in model_defaults.")

        # Dynamic model selection logic (placeholder)
        # Example: if prompt is very short, maybe use a cheaper model than api_model
        # if len(prompt) < 100 and stage_name == "write_scene" and state.total_cost_usd < self.config.budget_usd * 0.5:
        #     selected_model_name = self.config.model_defaults.get("local_model", primary_model_name)
        # else:
        selected_model_name = primary_model_name

        # Budget check (before expensive call)
        # This would involve a token estimation utility here
        # estimated_cost = self.cost_tracker.estimate_cost(selected_model_name, prompt_tokens_estimate, completion_tokens_estimate)
        # if state.total_cost_usd + estimated_cost > self.config.budget_usd:
        #     raise BudgetExceededError(f"Estimated cost {estimated_cost:.2f} would exceed budget. Current: {state.total_cost_usd:.2f}, Budget: {self.config.budget_usd:.2f}")

        if selected_model_name not in self._clients:
            client_class = MODEL_CLIENT_MAP.get(selected_model_name)
            if not client_class:
                raise ValueError(f"No client class mapped for model: {selected_model_name}")
            self._clients[selected_model_name] = client_class(selected_model_name)

        return self._clients[selected_model_name]

    async def generate_with_router(self, stage_name: str, prompt: str, state: PrometheusState, **kwargs) -> str:
        # This method wraps the client.generate to handle fallbacks, retries, cost tracking
        selected_client = None
        try:
            selected_client = await self.get_client_for_stage(stage_name, state)
            # Simulate token usage for cost tracking
            input_tokens = len(prompt) // 4 # Very rough estimate
            output_tokens_estimate = kwargs.get("max_output_tokens", 500) // 4 # Rough estimate

            # Actual generation
            generated_text = await selected_client.generate(prompt, **kwargs)

            # After successful generation, track cost
            # In a real scenario, you'd get actual token usage from the LLM response
            self.cost_tracker.add_cost(stage_name, selected_client.model_name, input_tokens, len(generated_text), state)

            return generated_text
        except BudgetExceededError:
            raise # Propagate budget error
        except Exception as e:
            logger.error(f"Primary model '{selected_client.model_name if selected_client else 'N/A'}' failed for stage {stage_name}: {e}")
            # Fallback logic
            fallback_model_name = self.config.model_defaults.get("fallback_model")
            if fallback_model_name and fallback_model_name != (selected_client.model_name if selected_client else None):
                logger.info(f"Attempting fallback to model: {fallback_model_name} for stage {stage_name}")
                try:
                    if fallback_model_name not in self._clients:
                        fallback_client_class = MODEL_CLIENT_MAP.get(fallback_model_name)
                        if not fallback_client_class:
                            raise ValueError(f"No client class mapped for fallback model: {fallback_model_name}")
                        self._clients[fallback_model_name] = fallback_client_class(fallback_model_name)

                    fallback_client = self._clients[fallback_model_name]
                    generated_text = await fallback_client.generate(prompt, **kwargs)

                    # Track cost for fallback
                    input_tokens = len(prompt) // 4
                    self.cost_tracker.add_cost(stage_name, fallback_client.model_name, input_tokens, len(generated_text), state)
                    logger.info(f"Fallback successful for stage {stage_name} using {fallback_model_name}.")
                    return generated_text
                except Exception as fallback_e:
                    logger.error(f"Fallback model '{fallback_model_name}' also failed for stage {stage_name}: {fallback_e}")
                    raise LLMGenerationError(f"All LLM attempts failed for stage {stage_name}: {fallback_e}", original_exception=fallback_e)
            else:
                raise LLMGenerationError(f"LLM generation failed for stage {stage_name}: {e}", original_exception=e)

