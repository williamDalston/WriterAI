# LTM/STM management logic with semantic-boundary-aware context truncation
import asyncio
import time
from typing import Dict, Any, List, Optional
from ..models.novel_state import PrometheusState
from ..models.outline_schemas import NovelOutline
from .vector_store import VectorStore
from ..llm.model_router import LLMModelRouter
from ..utils.error_handling import LLMGenerationError
import logging

logger = logging.getLogger(__name__)


def truncate_at_sentence_boundary(text: str, max_chars: int) -> str:
    """Truncate text at the nearest sentence boundary before max_chars.

    Instead of cutting mid-word or mid-sentence, finds the last complete
    sentence that fits within the limit. Falls back to paragraph, then
    word boundary if no sentence boundary is found.
    """
    if len(text) <= max_chars:
        return text

    # Try to find the last sentence boundary (. ! ? followed by space or newline)
    truncated = text[:max_chars]

    # Look for sentence endings: period/exclamation/question followed by whitespace
    best_cut = -1
    for i in range(len(truncated) - 1, max(0, len(truncated) - 500), -1):
        if truncated[i] in '.!?' and (i + 1 >= len(truncated) or truncated[i + 1] in ' \n\r\t'):
            best_cut = i + 1
            break

    if best_cut > max_chars * 0.5:  # Only use if we keep at least 50% of content
        return truncated[:best_cut].rstrip()

    # Fall back to paragraph boundary
    last_newline = truncated.rfind('\n\n')
    if last_newline > max_chars * 0.5:
        return truncated[:last_newline].rstrip()

    # Fall back to single newline
    last_newline = truncated.rfind('\n')
    if last_newline > max_chars * 0.5:
        return truncated[:last_newline].rstrip()

    # Fall back to word boundary
    last_space = truncated.rfind(' ')
    if last_space > max_chars * 0.5:
        return truncated[:last_space].rstrip()

    # Last resort: hard cut
    return truncated


class StateManager:
    def __init__(self, vector_store: VectorStore, llm_router: LLMModelRouter):
        self.vector_store = vector_store
        self.llm_router = llm_router
        self._ltm_version = 0
        self._stm_history: List[Dict[str, Any]] = []

    async def update_ltm(self, novel_outline: NovelOutline):
        """Populates the vector store with outline details (LTM)."""
        logger.info(f"Updating Long-Term Memory (LTM) for novel: {novel_outline.metadata.title}")

        # Delete previous LTM version to prevent stale data
        if self._ltm_version > 0:
            await self.vector_store.delete_by_metadata({
                "novel_id": novel_outline.metadata.project_name,
                "memory_type": "ltm"
            })

        documents_to_add: List[Dict[str, Any]] = []

        # Add novel metadata
        documents_to_add.append({
            "content": novel_outline.metadata.model_dump_json(),
            "metadata": {
                "type": "novel_metadata",
                "memory_type": "ltm",
                "novel_id": novel_outline.metadata.project_name,
                "version": self._ltm_version
            }
        })

        # Add characters
        for char in novel_outline.characters:
            documents_to_add.append({
                "content": char.model_dump_json(),
                "metadata": {
                    "type": "character",
                    "memory_type": "ltm",
                    "novel_id": novel_outline.metadata.project_name,
                    "char_id": char.id,
                    "version": self._ltm_version
                }
            })

        # Add settings
        for setting in novel_outline.settings:
            documents_to_add.append({
                "content": setting.model_dump_json(),
                "metadata": {
                    "type": "setting",
                    "memory_type": "ltm",
                    "novel_id": novel_outline.metadata.project_name,
                    "setting_id": setting.id,
                    "version": self._ltm_version
                }
            })

        # Add plot points (flattened)
        def flatten_plot_points(pps, chapter=None, scene=None):
            flat_pps = []
            for pp in pps:
                flat_pps.append({
                    "content": pp.model_dump_json(),
                    "metadata": {
                        "type": "plot_point",
                        "memory_type": "ltm",
                        "novel_id": novel_outline.metadata.project_name,
                        "plot_id": pp.id,
                        "chapter": str(chapter) if chapter else "",
                        "scene": str(scene) if scene else "",
                        "version": self._ltm_version
                    }
                })
                if pp.sub_beats:
                    flat_pps.extend(flatten_plot_points(pp.sub_beats, chapter, scene))
            return flat_pps

        documents_to_add.extend(flatten_plot_points(novel_outline.plot_points))

        await self.vector_store.add_documents_batch(documents_to_add)
        self._ltm_version += 1
        logger.info(f"LTM updated to version {self._ltm_version} ({len(documents_to_add)} documents)")

    async def update_stm(self, scene_text: str, current_state: PrometheusState):
        """Summarizes the latest scene and stores it as short-term memory."""
        chapter = current_state.current_chapter
        scene = current_state.current_scene
        logger.info(f"Updating Short-Term Memory (STM) for chapter {chapter}, scene {scene}")

        # Use LLM to summarize the scene for STM
        summary_prompt = (
            "Summarize the following scene concisely for short-term memory. "
            "Include: key events, character emotional states, any revealed information, "
            "and setting changes. Be specific about names and details.\n\n"
            f"{scene_text}"
        )

        summary_content = ""
        try:
            summary_llm_client = await self.llm_router.get_client_for_stage("memory_summary", current_state)
            response = await summary_llm_client.generate(summary_prompt, max_tokens=150, temperature=0.3)
            summary_content = response.content if hasattr(response, 'content') else str(response)
        except (LLMGenerationError, Exception) as e:
            logger.warning(f"Failed to generate scene summary for STM: {e}. Using extractive summary.")
            # Extractive fallback: take first and last sentences
            sentences = [s.strip() for s in scene_text.replace('\n', ' ').split('.') if s.strip()]
            if len(sentences) > 4:
                summary_content = '. '.join(sentences[:2] + sentences[-2:]) + '.'
            else:
                summary_content = truncate_at_sentence_boundary(scene_text, 300)

        stm_entry = {
            "content": summary_content,
            "metadata": {
                "type": "scene_summary",
                "memory_type": "stm",
                "novel_id": current_state.novel_outline.metadata.project_name,
                "chapter": chapter,
                "scene": scene,
                "timestamp": time.time()
            }
        }
        await self.vector_store.add_documents_batch([stm_entry])
        self._stm_history.append(stm_entry)

        logger.info(f"STM updated for chapter {chapter}, scene {scene} ({len(summary_content)} chars)")

    async def retrieve_context(self, query: str, state: PrometheusState, max_context_chars: int = 6000) -> Dict[str, str]:
        """Retrieve relevant LTM and STM context using semantic search.

        Uses sentence-boundary-aware truncation instead of hard character cuts.
        Prioritizes recent scene summaries and directly relevant facts.
        """
        logger.info(f"Retrieving context for query: '{query[:80]}...'")

        # Semantic search retrieves the most relevant documents
        retrieved_docs = await self.vector_store.hybrid_search(query, k=15)

        # Also fetch recent scene summaries for temporal context
        recent_summaries = await self.vector_store.search_by_metadata(
            {"type": "scene_summary", "memory_type": "stm"},
            k=5
        )

        # Merge and deduplicate
        seen_ids = set()
        all_docs = []
        for doc in retrieved_docs + recent_summaries:
            doc_id = doc.get("id", "")
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                all_docs.append(doc)

        # Separate by type for structured context
        summaries = []
        facts = []

        for doc in all_docs:
            doc_type = doc["metadata"].get("type", "")
            content = doc["content"]

            if doc_type == "scene_summary":
                chapter = doc["metadata"].get("chapter", "?")
                scene = doc["metadata"].get("scene", "?")
                summaries.append(f"[Ch{chapter}-S{scene}] {content}")
            else:
                facts.append(content)

        # Build context string with budget allocation
        # Give 40% to summaries, 60% to facts
        summary_budget = int(max_context_chars * 0.4)
        facts_budget = int(max_context_chars * 0.6)

        summary_text = "\n".join(summaries)
        facts_text = "\n".join(facts)

        # Truncate at sentence boundaries
        if len(summary_text) > summary_budget:
            summary_text = truncate_at_sentence_boundary(summary_text, summary_budget)

        if len(facts_text) > facts_budget:
            facts_text = truncate_at_sentence_boundary(facts_text, facts_budget)

        full_context_str = ""
        if summary_text:
            full_context_str += "Previous Scene Summaries:\n" + summary_text
        if facts_text:
            if full_context_str:
                full_context_str += "\n\n"
            full_context_str += "Relevant Facts & Outline:\n" + facts_text

        return {
            "full_context": full_context_str,
            "summaries": "\n".join(summaries),
            "facts": "\n".join(facts)
        }
