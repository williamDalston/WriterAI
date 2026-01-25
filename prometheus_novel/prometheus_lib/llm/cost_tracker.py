# Tracks token usage and cost per call
from typing import Dict
from prometheus_lib.models.novel_state import PrometheusState
import logging

logger = logging.getLogger(__name__)

class CostTracker:
    def __init__(self):
        # Example pricing (per 1M tokens) - replace with actual pricing
        self.model_pricing: Dict[str, Dict[str, float]] = {
            "gpt-4o-mini": {"input_cost_per_million_tokens": 0.15, "output_cost_per_million_tokens": 0.60},
            "gpt-3.5-turbo": {"input_cost_per_million_tokens": 0.50, "output_cost_per_million_tokens": 1.50},
            "gemini-2.0-flash": {"input_cost_per_million_tokens": 0.35, "output_cost_per_million_tokens": 0.70},
            "gpt-local": {"input_cost_per_million_tokens": 0.01, "output_cost_per_million_tokens": 0.02}, # Very cheap local model
            "gpt-4o-mini-nano": {"input_cost_per_million_tokens": 0.05, "output_cost_per_million_tokens": 0.10}, # Placeholder for a cheaper mini
        }

    def calculate_cost(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
        pricing = self.model_pricing.get(model_name)
        if not pricing:
            logger.warning(f"Pricing not found for model: {model_name}. Assuming 0 cost.")
            return 0.0

        input_cost = (input_tokens / 1_000_000) * pricing["input_cost_per_million_tokens"]
        output_cost = (output_tokens / 1_000_000) * pricing["output_cost_per_million_tokens"]
        return input_cost + output_cost

    def add_cost(self, stage_name: str, model_name: str, input_tokens: int, output_tokens: int, state: PrometheusState):
        cost = self.calculate_cost(model_name, input_tokens, output_tokens)
        state.total_cost_usd += cost
        logger.info(f"Stage '{stage_name}' used {input_tokens} input, {output_tokens} output tokens from {model_name}. Cost: ${cost:.4f}. Total: ${state.total_cost_usd:.4f}")
