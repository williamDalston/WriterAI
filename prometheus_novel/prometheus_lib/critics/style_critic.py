# Style critique logic
import asyncio
from typing import Dict, Any, List
import logging
import json
from prometheus_lib.models.novel_state import PrometheusState
from prometheus_lib.models.outline_schemas import StyleGuide
from prometheus_lib.llm.model_router import LLMModelRouter
from prometheus_lib.utils.error_handling import LLMGenerationError
from prometheus_lib.utils.prompt_loader import load_prompt_template

logger = logging.getLogger(__name__)

class StyleCritic:
    def __init__(self, llm_router: LLMModelRouter):
        self.llm_router = llm_router

    async def critique_style(self, scene_text: str, style_guide: StyleGuide, state: PrometheusState) -> Dict[str, Any]:
        '''
        Critiques a generated scene for adherence to the novel's style guide.

        Args:
            scene_text (str): The text of the scene to critique.
            style_guide (StyleGuide): The novel's defined style guide.
            state (PrometheusState): The current novel state (for LLM routing).

        Returns:
            Dict[str, Any]: A report with stylistic issues and suggestions.
        '''
        logger.info(f"Critiquing scene style for Chapter {state.current_chapter}, Scene {state.current_scene}")

        # Build prompt for critic LLM
        prompt_vars = {
            "scene_text": scene_text,
            "style_guide_details": style_guide.model_dump_json()
        }
        
        # Load prompt template for style critique
        template = load_prompt_template("style_critique_prompt.txt", state.novel_outline.metadata.prompt_set_directory)
        critique_prompt = template.render(**prompt_vars)

        try:
            critic_llm_client = await self.llm_router.get_client_for_stage("self_refine", state) # Use critic model
            critique_response_json = await critic_llm_client.generate(critique_prompt, temperature=0.2, max_output_tokens=300)
            
            # Expecting structured JSON output from LLM for critique
            critique_report = json.loads(critique_response_json)
            if not isinstance(critique_report, dict) or "issues" not in critique_report:
                raise ValueError("Critic did not return expected JSON format.")
            
            logger.info(f"Style critique complete. Issues found: {len(critique_report.get('issues', []))}")
            return critique_report
        except LLMGenerationError as e:
            logger.error(f"Failed to get style critique from LLM: {e}")
            return {"issues": [{"type": "LLM_ERROR", "description": f"Failed to critique style due to LLM error: {e}"}], "suggested_fixes": []}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse style critique JSON: {e}. Raw: {critique_response_json[:200]}...")
            return {"issues": [{"type": "PARSING_ERROR", "description": f"Failed to parse LLM critique output: {e}"}], "suggested_fixes": []}
        except Exception as e:
            logger.error(f"An unexpected error occurred during style critique: {e}", exc_info=True)
            raise # Re-raise critical errors
