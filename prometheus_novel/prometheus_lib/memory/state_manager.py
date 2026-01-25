# LTM/STM management logic
import asyncio
from typing import Dict, Any, List, Optional
from prometheus_lib.models.novel_state import PrometheusState
from prometheus_lib.models.outline_schemas import NovelOutline
from prometheus_lib.memory.vector_store import VectorStore
from prometheus_lib.llm.model_router import LLMModelRouter
from prometheus_lib.utils.error_handling import LLMGenerationError
import logging

logger = logging.getLogger(__name__)

class StateManager:
    def __init__(self, vector_store: VectorStore, llm_router: LLMModelRouter):
        self.vector_store = vector_store
        self.llm_router = llm_router
        self._ltm_version = 0 # Track LTM version for consistency
        self._stm_history: List[Dict[str, Any]] = [] # Store STM deltas/snapshots

    async def update_ltm(self, novel_outline: NovelOutline):
        '''
        Populates the vector store with outline details (LTM).
        Supports versioning by storing deltas or snapshots.
        '''
        logger.info(f"Updating Long-Term Memory (LTM) for novel: {novel_outline.metadata.title}")
        documents_to_add: List[Dict[str, Any]] = []

        # Add novel metadata
        documents_to_add.append({
            "content": novel_outline.metadata.model_dump_json(),
            "metadata": {"type": "novel_metadata", "novel_id": novel_outline.metadata.project_name, "version": self._ltm_version}
        })

        # Add characters
        for char in novel_outline.characters:
            documents_to_add.append({
                "content": char.model_dump_json(),
                "metadata": {"type": "character", "novel_id": novel_outline.metadata.project_name, "char_id": char.id, "version": self._ltm_version}
            })
        # Add settings
        for setting in novel_outline.settings:
            documents_to_add.append({
                "content": setting.model_dump_json(),
                "metadata": {"type": "setting", "novel_id": novel_outline.metadata.project_name, "setting_id": setting.id, "version": self._ltm_version}
            })
        # Add plot points (can be flattened or hierarchical)
        def flatten_plot_points(pps, chapter=None, scene=None):
            flat_pps = []
            for pp in pps:
                flat_pps.append({
                    "content": pp.model_dump_json(),
                    "metadata": {
                        "type": "plot_point",
                        "novel_id": novel_outline.metadata.project_name,
                        "plot_id": pp.id,
                        "chapter": chapter,
                        "scene": scene,
                        "version": self._ltm_version
                    }
                })
                if pp.sub_beats:
                    flat_pps.extend(flatten_plot_points(pp.sub_beats, chapter, scene)) # Recursively flatten
            return flat_pps

        documents_to_add.extend(flatten_plot_points(novel_outline.plot_points))

        await self.vector_store.add_documents_batch(documents_to_add)
        self._ltm_version += 1
        logger.info(f"LTM updated to version {self._ltm_version}.")

    async def update_stm(self, scene_text: str, current_state: PrometheusState):
        '''
        Summarizes the latest generated scene and updates character_current_states (STM).
        Stores STM deltas/snapshots.
        '''
        logger.info(f"Updating Short-Term Memory (STM) for chapter {current_state.current_chapter}, scene {current_state.current_scene}")

        # Use LLM to summarize the scene for STM
        summary_prompt = f"Summarize the following scene concisely for short-term memory:

{scene_text}"
        try:
            summary_llm_client = await self.llm_router.get_client_for_stage("memory_summary", current_state) # Assuming a model for summary
            scene_summary = await summary_llm_client.generate(summary_prompt, max_output_tokens=100, temperature=0.3)
        except LLMGenerationError as e:
            logger.warning(f"Failed to generate scene summary for STM: {e}. Storing raw text.")
            scene_summary = scene_text[:200] + "..." # Fallback to truncated raw text

        stm_entry = {
            "content": scene_summary,
            "metadata": {
                "type": "scene_summary",
                "novel_id": current_state.novel_outline.metadata.project_name,
                "chapter": current_state.current_chapter,
                "scene": current_state.current_scene,
                "timestamp": asyncio.current_task()._loop.time() # Simple timestamp
            }
        }
        await self.vector_store.add_documents_batch([stm_entry])
        self._stm_history.append(stm_entry) # Keep a history of STM updates

        logger.info(f"STM updated with summary for chapter {current_state.current_chapter}, scene {current_state.current_scene}.")

    async def retrieve_context(self, query: str, state: PrometheusState) -> Dict[str, str]:
        '''
        Retrieves relevant LTM and STM context based on the query.
        Includes logic to trim/summarize context if it exceeds token limits.
        '''
        logger.info(f"Retrieving context for query: '{query}'")
        retrieved_docs = await self.vector_store.hybrid_search(query, k=10) # Retrieve top 10 relevant docs

        context_parts: Dict[str, List[str]] = {"summaries": [], "facts": []}
        for doc in retrieved_docs:
            doc_type = doc["metadata"].get("type")
            content = doc["content"]
            if doc_type == "scene_summary":
                context_parts["summaries"].append(content)
            else: # Treat other types (character, setting, plot_point, novel_metadata) as facts
                context_parts["facts"].append(content)

        full_context_str = (
            "Previous Scene Summaries:\n" + "\n".join(context_parts["summaries"]) +
            "\n\nRelevant Facts & Outline:\n" + "\n".join(context_parts["facts"])
        )

        # Context window management (placeholder for actual token counting)
        # This would require a token counter specific to the LLM being used
        # For now, a simple character limit
        max_context_length = 4000 # Example character limit, replace with actual token limit logic
        if len(full_context_str) > max_context_length:
            logger.warning(f"Context length ({len(full_context_str)}) exceeds max ({max_context_length}). Trimming.")
            # This is a naive trimming. A real solution would use LLM to summarize or prioritize.
            full_context_str = full_context_str[:max_context_length] + "... [CONTEXT TRUNCATED]"

        return {"full_context": full_context_str, "summaries": "\n".join(context_parts["summaries"]), "facts": "\n".join(context_parts["facts"])}
