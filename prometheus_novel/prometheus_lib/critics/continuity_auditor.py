# Continuity auditor for scene consistency
import asyncio
from typing import Dict, Any, List
import logging
import json
from prometheus_lib.models.novel_state import PrometheusState
from prometheus_lib.llm.model_router import LLMModelRouter
from prometheus_lib.memory.state_manager import StateManager
from prometheus_lib.utils.error_handling import LLMGenerationError
from prometheus_lib.utils.prompt_loader import load_prompt_template

logger = logging.getLogger(__name__)

class ContinuityAuditor:
    def __init__(self, llm_router: LLMModelRouter, state_manager: StateManager):
        self.llm_router = llm_router
        self.state_manager = state_manager

    async def audit_scene(self, scene_text: str, state: PrometheusState) -> Dict[str, Any]:
        '''
        Audits a generated scene for continuity and consistency against LTM/STM.

        Args:
            scene_text (str): The text of the scene to audit.
            state (PrometheusState): The current novel state.

        Returns:
            Dict[str, Any]: A report with issues found and suggested fixes.
        '''
        logger.info(f"Auditing scene for continuity: Chapter {state.current_chapter}, Scene {state.current_scene}")

        # Retrieve relevant LTM (outline) and STM (previous scenes, character states)
        context_query = f"Check continuity for scene: {scene_text[:100]}..."
        retrieved_context = await self.state_manager.retrieve_context(context_query, state)

        # Build prompt for critic LLM
        prompt_vars = {
            "scene_text": scene_text,
            "novel_outline_summary": state.novel_outline.metadata.synopsis,
            "relevant_context": retrieved_context.get("full_context", ""),
            "character_current_states": {char_id: state.character_current_states.get(char_id, {}) for char_id in state.novel_outline.characters.keys()} # Pass relevant char states
        }
        
        # Load prompt template for continuity audit
        template = load_prompt_template("continuity_audit_prompt.txt", state.novel_outline.metadata.prompt_set_directory)
        audit_prompt = template.render(**prompt_vars)

        try:
            critic_llm_client = await self.llm_router.get_client_for_stage("self_refine", state) # Use critic model
            audit_response_json = await critic_llm_client.generate(audit_prompt, temperature=0.2, max_output_tokens=500)
            
            # Expecting structured JSON output from LLM for critique
            audit_report = json.loads(audit_response_json)
            if not isinstance(audit_report, dict) or "issues" not in audit_report:
                raise ValueError("Critic did not return expected JSON format.")
            
            logger.info(f"Continuity audit complete. Issues found: {len(audit_report.get('issues', []))}")
            return audit_report
        except LLMGenerationError as e:
            logger.error(f"Failed to get continuity audit from LLM: {e}")
            return {"issues": [{"type": "LLM_ERROR", "description": f"Failed to audit scene due to LLM error: {e}"}], "suggested_fixes": []}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse continuity audit JSON: {e}. Raw: {audit_response_json[:200]}...")
            return {"issues": [{"type": "PARSING_ERROR", "description": f"Failed to parse LLM audit output: {e}"}], "suggested_fixes": []}
        except Exception as e:
            logger.error(f"An unexpected error occurred during continuity audit: {e}", exc_info=True)
            raise # Re-raise critical errors
