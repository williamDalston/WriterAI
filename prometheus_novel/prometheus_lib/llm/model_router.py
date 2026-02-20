# Model router for stage selection and cost enforcement
import asyncio
from typing import Any, Dict, Optional, Type
from prometheus_lib.models.config_schemas import ConfigSchema
from prometheus_lib.models.novel_state import PrometheusState
from prometheus_lib.llm.clients import BaseLLMClient, OpenAIClient, GeminiClient, OllamaClient, AnthropicClient, is_ollama_model, count_tokens
from prometheus_lib.llm.cost_tracker import CostTracker
from prometheus_lib.utils.error_handling import BudgetExceededError, LLMGenerationError
import logging

logger = logging.getLogger(__name__)

class InitializationError(Exception):
    pass

# Map model keys to client classes
# Ollama models (local, no cost) - use OllamaClient for any model name that passes is_ollama_model
def _get_client_class(model_name: str) -> Type[BaseLLMClient]:
    if is_ollama_model(model_name):
        return OllamaClient
    return MODEL_CLIENT_MAP.get(model_name, OllamaClient)  # Default to local if unknown

MODEL_CLIENT_MAP: Dict[str, Type[BaseLLMClient]] = {
    # Local models
    "gpt-local": OllamaClient,
    "qwen2.5:7b": OllamaClient,
    "qwen2.5:14b": OllamaClient,
    "qwen3:14b": OllamaClient,
    "qwen3-nothink": OllamaClient,
    "qwen2.5": OllamaClient,
    "llama3.2": OllamaClient,
    "llama3.1": OllamaClient,
    "mistral": OllamaClient,
    "phi3": OllamaClient,
    "deepseek": OllamaClient,
    # OpenAI models
    "gpt-5-mini": OpenAIClient,
    "gpt-4o": OpenAIClient,
    "gpt-4o-mini": OpenAIClient,
    "gpt-4o-mini-nano": OpenAIClient,
    "gpt-3.5-turbo": OpenAIClient,
    "o1-mini": OpenAIClient,
    # Anthropic models
    "claude-sonnet-4-20250514": AnthropicClient,
    "claude-sonnet-4-5-20250929": AnthropicClient,
    "claude-opus-4-6": AnthropicClient,
    "claude-haiku-4-5-20251001": AnthropicClient,
    # Google models
    "gemini-2.0-flash": GeminiClient,
    "gemini-1.5-pro": GeminiClient,
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
            if model_name and model_name not in MODEL_CLIENT_MAP and not is_ollama_model(model_name):
                errors.append(f"Default '{key}' -> '{model_name}' not mapped in MODEL_CLIENT_MAP.")
        for stage, model_key in self.config.stage_model_map.root.items():
            if model_key not in defaults:
                errors.append(f"Stage '{stage}' uses unknown model key '{model_key}'.")
            else:
                model_name = defaults.get(model_key)
                if model_name and model_name not in MODEL_CLIENT_MAP and not is_ollama_model(model_name):
                    errors.append(f"Stage '{stage}' -> '{model_name}' not mapped in MODEL_CLIENT_MAP.")
        if errors:
            raise InitializationError("\n".join(errors))


    async def get_client_for_stage(self, stage_name: str, state: PrometheusState) -> BaseLLMClient:
        model_key = self.config.stage_model_map.root.get(stage_name)
        if not model_key:
            raise ValueError(f"No model configured for stage: {stage_name}")

        primary_model_name = getattr(self.config.model_defaults, model_key, None) if hasattr(self.config.model_defaults, '__dataclass_fields__') or hasattr(self.config.model_defaults, 'model_fields') else self.config.model_defaults.get(model_key) if isinstance(self.config.model_defaults, dict) else None
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
            client_class = _get_client_class(selected_model_name)
            self._clients[selected_model_name] = client_class(selected_model_name)

        return self._clients[selected_model_name]

    async def generate_with_router(self, stage_name: str, prompt: str, state: PrometheusState, **kwargs) -> str:
        # This method wraps the client.generate to handle fallbacks, retries, cost tracking
        selected_client = None
        try:
            selected_client = await self.get_client_for_stage(stage_name, state)

            # Budget check before expensive call
            if self.config.budget_usd > 0:
                input_tokens_est = count_tokens(prompt, selected_client.model_name)
                est_cost = self.cost_tracker.calculate_cost(
                    selected_client.model_name, input_tokens_est, kwargs.get("max_tokens", 4096)
                )
                if state.total_cost_usd + est_cost > self.config.budget_usd:
                    raise BudgetExceededError(
                        f"Estimated cost ${est_cost:.4f} would exceed budget. "
                        f"Current: ${state.total_cost_usd:.2f}, Budget: ${self.config.budget_usd:.2f}"
                    )

            # Actual generation
            response = await selected_client.generate(prompt, **kwargs)
            generated_text = response.content if hasattr(response, "content") else str(response)

            # Use accurate token counts from response, fall back to counting
            input_tokens = getattr(response, "input_tokens", None) or count_tokens(prompt, selected_client.model_name)
            output_tokens = getattr(response, "output_tokens", None) or count_tokens(generated_text, selected_client.model_name)
            self.cost_tracker.add_cost(stage_name, selected_client.model_name, input_tokens, output_tokens, state)

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
                        fallback_client_class = _get_client_class(fallback_model_name)
                        self._clients[fallback_model_name] = fallback_client_class(fallback_model_name)

                    fallback_client = self._clients[fallback_model_name]
                    response = await fallback_client.generate(prompt, **kwargs)
                    generated_text = response.content if hasattr(response, "content") else str(response)

                    # Track cost for fallback with accurate counting
                    input_tokens = getattr(response, "input_tokens", None) or count_tokens(prompt, fallback_client.model_name)
                    output_tokens = getattr(response, "output_tokens", None) or count_tokens(generated_text, fallback_client.model_name)
                    self.cost_tracker.add_cost(stage_name, fallback_client.model_name, input_tokens, output_tokens, state)
                    logger.info(f"Fallback successful for stage {stage_name} using {fallback_model_name}.")
                    return generated_text
                except Exception as fallback_e:
                    logger.error(f"Fallback model '{fallback_model_name}' also failed for stage {stage_name}: {fallback_e}")
                    raise LLMGenerationError(f"All LLM attempts failed for stage {stage_name}: {fallback_e}", original_exception=fallback_e)
            else:
                raise LLMGenerationError(f"LLM generation failed for stage {stage_name}: {e}", original_exception=e)

