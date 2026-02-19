# Tracks token usage and cost per call with up-to-date pricing
from typing import Dict
from prometheus_lib.models.novel_state import PrometheusState
from prometheus_lib.llm.clients import is_ollama_model
import logging

logger = logging.getLogger(__name__)

class CostTracker:
    def __init__(self):
        # Pricing per 1M tokens - kept current as of 2025
        self.model_pricing: Dict[str, Dict[str, float]] = {
            # OpenAI models
            "gpt-4o": {"input_cost_per_million_tokens": 2.50, "output_cost_per_million_tokens": 10.00},
            "gpt-4o-mini": {"input_cost_per_million_tokens": 0.15, "output_cost_per_million_tokens": 0.60},
            "gpt-4o-mini-nano": {"input_cost_per_million_tokens": 0.05, "output_cost_per_million_tokens": 0.10},
            "gpt-3.5-turbo": {"input_cost_per_million_tokens": 0.50, "output_cost_per_million_tokens": 1.50},
            "o1-mini": {"input_cost_per_million_tokens": 3.00, "output_cost_per_million_tokens": 12.00},

            # Anthropic models
            "claude-sonnet-4-20250514": {"input_cost_per_million_tokens": 3.00, "output_cost_per_million_tokens": 15.00},
            "claude-sonnet-4-5-20250929": {"input_cost_per_million_tokens": 3.00, "output_cost_per_million_tokens": 15.00},
            "claude-opus-4-6": {"input_cost_per_million_tokens": 15.00, "output_cost_per_million_tokens": 75.00},
            "claude-haiku-4-5-20251001": {"input_cost_per_million_tokens": 0.80, "output_cost_per_million_tokens": 4.00},

            # Google models
            "gemini-2.0-flash": {"input_cost_per_million_tokens": 0.35, "output_cost_per_million_tokens": 0.70},
            "gemini-1.5-pro": {"input_cost_per_million_tokens": 1.25, "output_cost_per_million_tokens": 5.00},

            # Local Ollama models - zero cost
            "gpt-local": {"input_cost_per_million_tokens": 0.0, "output_cost_per_million_tokens": 0.0},
            "qwen2.5": {"input_cost_per_million_tokens": 0.0, "output_cost_per_million_tokens": 0.0},
            "qwen2.5:7b": {"input_cost_per_million_tokens": 0.0, "output_cost_per_million_tokens": 0.0},
            "qwen3:14b": {"input_cost_per_million_tokens": 0.0, "output_cost_per_million_tokens": 0.0},
            "llama3.2": {"input_cost_per_million_tokens": 0.0, "output_cost_per_million_tokens": 0.0},
            "llama3.1": {"input_cost_per_million_tokens": 0.0, "output_cost_per_million_tokens": 0.0},
            "mistral": {"input_cost_per_million_tokens": 0.0, "output_cost_per_million_tokens": 0.0},
            "phi3": {"input_cost_per_million_tokens": 0.0, "output_cost_per_million_tokens": 0.0},
            "deepseek": {"input_cost_per_million_tokens": 0.0, "output_cost_per_million_tokens": 0.0},
        }

        # Running totals for reporting
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.calls_by_stage: Dict[str, int] = {}
        self.cost_by_model: Dict[str, float] = {}

    def calculate_cost(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
        if is_ollama_model(model_name):
            return 0.0
        pricing = self.model_pricing.get(model_name)
        if not pricing:
            # Try partial match for versioned model names
            for key in self.model_pricing:
                if key in model_name or model_name in key:
                    pricing = self.model_pricing[key]
                    break
        if not pricing:
            logger.warning(f"Pricing not found for model: {model_name}. Assuming $0.50/$1.50 per 1M tokens.")
            pricing = {"input_cost_per_million_tokens": 0.50, "output_cost_per_million_tokens": 1.50}

        input_cost = (input_tokens / 1_000_000) * pricing["input_cost_per_million_tokens"]
        output_cost = (output_tokens / 1_000_000) * pricing["output_cost_per_million_tokens"]
        return input_cost + output_cost

    def add_cost(self, stage_name: str, model_name: str, input_tokens: int, output_tokens: int, state: PrometheusState):
        cost = self.calculate_cost(model_name, input_tokens, output_tokens)
        state.total_cost_usd += cost

        # Track running totals
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += cost
        self.calls_by_stage[stage_name] = self.calls_by_stage.get(stage_name, 0) + 1
        self.cost_by_model[model_name] = self.cost_by_model.get(model_name, 0.0) + cost

        logger.info(
            f"Stage '{stage_name}' | {model_name} | "
            f"{input_tokens:,} in + {output_tokens:,} out tokens | "
            f"Cost: ${cost:.4f} | Total: ${state.total_cost_usd:.4f}"
        )

    def get_summary(self) -> Dict:
        """Get cost tracking summary for reporting."""
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_cost_usd": round(self.total_cost, 4),
            "calls_by_stage": self.calls_by_stage,
            "cost_by_model": {k: round(v, 4) for k, v in self.cost_by_model.items()}
        }
