# Quality and safety validation
import asyncio
from typing import Dict, Any, List
import logging
from prometheus_lib.llm.model_router import LLMModelRouter
from prometheus_lib.models.novel_state import PrometheusState
from prometheus_lib.utils.error_handling import LLMGenerationError
from prometheus_lib.utils.prompt_loader import load_prompt_template
import json

logger = logging.getLogger(__name__)

class OutputValidator:
    def __init__(self, llm_router: LLMModelRouter):
        self.llm_router = llm_router

    async def validate_output(self, text: str, validation_rules: Dict[str, Any], state: PrometheusState) -> Dict[str, Any]:
        '''
        Validates the quality and safety of generated text before storage.

        Args:
            text (str): The generated text to validate.
            validation_rules (Dict[str, Any]): Rules for validation (e.g., min_length, max_toxicity).
            state (PrometheusState): The current novel state (for LLM routing).

        Returns:
            Dict[str, Any]: A validation report including 'is_valid' and 'issues'.
        '''
        logger.info(f"Validating generated output for Chapter {state.current_chapter}, Scene {state.current_scene}")
        issues: List[Dict[str, str]] = []
        is_valid = True

        # Rule-based checks (examples)
        min_length = validation_rules.get("min_length", 200)
        if len(text) < min_length:
            issues.append({"type": "LENGTH_TOO_SHORT", "description": f"Text is too short ({len(text)} chars), expected at least {min_length}."})
            is_valid = False
        
        # LLM-based safety/quality check
        safety_check_prompt_vars = {
            "text_to_check": text,
            "max_toxicity_threshold": validation_rules.get("max_toxicity", 0.1)
        }
        template = load_prompt_template("output_safety_prompt.txt", state.novel_outline.metadata.prompt_set_directory)
        safety_prompt = template.render(**safety_check_prompt_vars)

        try:
            critic_llm_client = await self.llm_router.get_client_for_stage("self_refine", state) # Use critic model
            safety_response_json = await critic_llm_client.generate(safety_prompt, temperature=0.1, max_output_tokens=100)
            
            safety_report = json.loads(safety_response_json)
            if not isinstance(safety_report, dict) or "is_safe" not in safety_report:
                raise ValueError("Safety critic did not return expected JSON format.")
            
            if not safety_report["is_safe"]:
                issues.append({"type": "SAFETY_VIOLATION", "description": safety_report.get("reason", "Content deemed unsafe.")})
                is_valid = False
            
            if not safety_report.get("is_quality_ok", True): # Assume quality check from same LLM call
                issues.append({"type": "LOW_QUALITY", "description": safety_report.get("quality_reason", "Content quality is low.")})
                is_valid = False

        except LLMGenerationError as e:
            logger.error(f"Failed to get safety/quality audit from LLM: {e}")
            issues.append({"type": "LLM_ERROR", "description": f"Failed to run safety/quality check due to LLM error: {e}"})
            is_valid = False # Treat LLM error in validation as a failure
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse safety/quality JSON: {e}. Raw: {safety_response_json[:200]}...")
            issues.append({"type": "PARSING_ERROR", "description": f"Failed to parse LLM safety/quality output: {e}"})
            is_valid = False
        except Exception as e:
            logger.error(f"An unexpected error occurred during output validation: {e}", exc_info=True)
            raise # Re-raise critical errors

        return {"is_valid": is_valid, "issues": issues}
