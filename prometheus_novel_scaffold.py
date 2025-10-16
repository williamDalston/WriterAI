#!/usr/bin/env python3
"""
PROMETHEUS-NOVEL 1.0 Scaffold Generator
Creates the initial project structure for the agentic novel generation pipeline.
"""

import os
from pathlib import Path

# Define project structure
project_root = Path("prometheus_novel")
dirs = [
    "configs",
    "prometheus_lib",
    "prometheus_lib/llm",
    "prometheus_lib/memory", 
    "prometheus_lib/models",
    "prometheus_lib/utils",
    "prometheus_lib/critics",
    "stages",
    "prompts",
    "prompts/default",
    "prompts/experimental_v2",
    "data",
    "logs",
    "docs"
]

# Files to create with placeholder content
files = {
    'configs/the_empathy_clause.yaml': """# Novel-specific configuration (budget, model mapping, prompt set)
project_name: the_empathy_clause
budget_usd: 1000  # Example budget
model_defaults:
  local_model: gpt-local
  api_model: gpt-4o-mini
  critic_model: gpt-4o-mini-nano
  fallback_model: gpt-3.5-turbo
stage_model_map:
  high_concept: api_model
  beat_sheet: api_model
  write_scene: api_model
  self_refine: critic_model
prompt_set_directory: prompts/default
""",
    'configs/env_config.py': """# Centralized environment config loader
from pathlib import Path
import os
from prometheus_lib.models.config_schemas import ConfigSchema
import yaml # Added for config loading

def load_config(env: str = None) -> ConfigSchema:
    # Determine the config file path based on environment
    config_name = f"{env}_config.yaml" if env else "the_empathy_clause.yaml"
    config_path = Path(__file__).parent / config_name

    if not config_path.exists():
        if env:
            print(f"Warning: Environment-specific config '{config_name}' not found. Falling back to 'the_empathy_clause.yaml'.")
            config_path = Path(__file__).parent / "the_empathy_clause.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Default config 'the_empathy_clause.yaml' not found at {config_path}. Please create it.")

    print(f"Loading configuration from: {config_path}")
    with open(config_path, 'r') as f:
        raw_config = yaml.safe_load(f)

    # Validate config using Pydantic schema
    config = ConfigSchema.model_validate(raw_config) # Use model_validate for Pydantic v2
    print(f"Active config for project: {config.project_name}")
    return config

if __name__ == '__main__':
    # Example usage:
    try:
        # Load default config or from env var PROMETHEUS_ENV
        current_env = os.getenv("PROMETHEUS_ENV")
        loaded_config = load_config(current_env)
        print(f"Successfully loaded config for {loaded_config.project_name}")
    except Exception as e:
        print(f"Error loading configuration: {e}")
""",
    'prometheus_lib/llm/clients.py': """# Async LLM client wrappers (OpenAI, Gemini, etc.)
import os
import asyncio
from typing import Any, Dict, Optional

class BaseLLMClient:
    def __init__(self, model_name: str):
        self.model_name = model_name

    async def generate(self, prompt: str, **kwargs) -> str:
        raise NotImplementedError("Subclasses must implement this method")

class OpenAIClient(BaseLLMClient):
    def __init__(self, model_name: str):
        super().__init__(model_name)
        # Placeholder for actual OpenAI client initialization
        # from openai import AsyncOpenAI
        # self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        print(f"Initialized OpenAI client for model: {model_name}")

    async def generate(self, prompt: str, **kwargs) -> str:
        # Placeholder for actual API call
        # response = await self.client.chat.completions.create(...)
        await asyncio.sleep(0.1) # Simulate async call
        return f"Generated text from {self.model_name} for prompt: {prompt[:50]}..."

class GeminiClient(BaseLLMClient):
    def __init__(self, model_name: str):
        super().__init__(model_name)
        # Placeholder for actual Gemini client initialization
        # from google.generativeai import GenerativeModel # Example
        # self.model = GenerativeModel(model_name)
        print(f"Initialized Gemini client for model: {model_name}")

    async def generate(self, prompt: str, **kwargs) -> str:
        # Placeholder for actual API call
        # response = await self.model.generate_content(prompt, **kwargs)
        await asyncio.sleep(0.1) # Simulate async call
        return f"Generated text from {self.model_name} for prompt: {prompt[:50]}..."

# Add more client classes as needed
""",
    'prometheus_lib/llm/model_router.py': """# Model router for stage selection and cost enforcement
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
            raise InitializationError("\n".join(errors))


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

""",
    'prometheus_lib/llm/cost_tracker.py': """# Tracks token usage and cost per call
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
""",
    'prometheus_lib/memory/vector_store.py': """# Hybrid search and caching implementation
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
import functools
import logging

logger = logging.getLogger(__name__)

# Placeholder for a simple in-memory vector store like ChromaDB or FAISS
# In a real scenario, you'd initialize and interact with a proper vector database client.
class MockVectorDB:
    def __init__(self):
        self.documents: List[Dict[str, Any]] = []
        self.embeddings: List[List[float]] = [] # Simulate embeddings
        self.next_id = 0

    async def add_documents(self, documents: List[Dict[str, Any]]):
        # Simulate batch embedding and adding
        logger.info(f"Simulating batch adding {len(documents)} documents to vector store.")
        await asyncio.sleep(0.05) # Simulate async operation
        for doc in documents:
            doc_id = str(self.next_id)
            self.documents.append({"id": doc_id, "content": doc.get("content"), "metadata": doc.get("metadata", {})})
            self.embeddings.append([hash(doc.get("content", "")) % 1000 / 1000.0] * 128) # Dummy embedding
            self.next_id += 1
        logger.info(f"Added {len(documents)} documents. Total documents: {len(self.documents)}")

    async def search(self, query_embedding: List[float], k: int) -> List[Dict[str, Any]]:
        # Simulate semantic search
        logger.info(f"Simulating semantic search for query. k={k}")
        await asyncio.sleep(0.02)
        # Return dummy results for now
        return self.documents[:k] # Return first k documents as dummy results

    async def keyword_search(self, query: str, k: int) -> List[Dict[str, Any]]:
        # Simulate BM25 or keyword search
        logger.info(f"Simulating keyword search for query: '{query}'. k={k}")
        await asyncio.sleep(0.01)
        # Return dummy results for now, based on simple content check
        return [doc for doc in self.documents if query.lower() in doc.get("content", "").lower()][:k]

class VectorStore:
    def __init__(self):
        self._db = None # Will be initialized asynchronously

    async def initialize_vector_db(self, data_path: Path):
        '''Initializes the vector database asynchronously.'''
        logger.info(f"Initializing vector database at {data_path}...")
        # Placeholder for actual ChromaDB/FAISS/Qdrant/Pinecone initialization
        self._db = MockVectorDB() # Using mock for scaffold
        await asyncio.sleep(0.1) # Simulate async setup
        logger.info("Vector database initialized.")

    @functools.lru_cache(maxsize=128) # Simple in-memory LRU cache
    async def hybrid_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        '''
        Combines keyword-based search (BM25) with semantic vector search.
        Results are cached.
        '''
        if not self._db:
            raise RuntimeError("Vector database not initialized. Call initialize_vector_db first.")

        logger.info(f"Performing hybrid search for query: '{query}'")
        # In a real scenario, you'd get query embedding here
        query_embedding = [0.1] * 128 # Dummy embedding

        # Phase 1: Hybrid Search
        semantic_results = await self._db.search(query_embedding, k)
        keyword_results = await self._db.keyword_search(query, k)

        # Combine and deduplicate results
        combined_results = {doc["id"]: doc for doc in semantic_results + keyword_results}.values()
        combined_list = list(combined_results)

        # Phase 2: Re-ranking (Placeholder for a cross-encoder model)
        re_ranked_results = await self.re_rank_documents(query, combined_list)
        logger.info(f"Hybrid search completed. Found {len(re_ranked_results)} results.")
        return re_ranked_results[:k] # Return top k after re-ranking

    async def re_rank_documents(self, query: str, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        '''
        Re-ranks documents using a more powerful cross-encoder model.
        Placeholder for actual re-ranking logic.
        '''
        logger.info(f"Simulating re-ranking for {len(documents)} documents.")
        await asyncio.sleep(0.01)
        # Simple dummy re-ranking: sort by length of content
        return sorted(documents, key=lambda x: len(x.get("content", "")), reverse=True)

    async def add_documents_batch(self, documents: List[Dict[str, Any]]):
        '''Adds documents to the vector store in batches.'''
        if not self._db:
            raise RuntimeError("Vector database not initialized. Call initialize_vector_db first.")
        await self._db.add_documents(documents)

    # For cache invalidation, you'd typically clear the cache explicitly
    def clear_cache(self):
        self.hybrid_search.cache_clear()
        logger.info("Vector store cache cleared.")
""",
    'prometheus_lib/memory/state_manager.py': """# LTM/STM management logic
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
        summary_prompt = f"Summarize the following scene concisely for short-term memory:\n\n{scene_text}"
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
            "Previous Scene Summaries:\\n" + "\\n".join(context_parts["summaries"]) +
            "\\n\\nRelevant Facts & Outline:\\n" + "\\n".join(context_parts["facts"])
        )

        # Context window management (placeholder for actual token counting)
        # This would require a token counter specific to the LLM being used
        # For now, a simple character limit
        max_context_length = 4000 # Example character limit, replace with actual token limit logic
        if len(full_context_str) > max_context_length:
            logger.warning(f"Context length ({len(full_context_str)}) exceeds max ({max_context_length}). Trimming.")
            # This is a naive trimming. A real solution would use LLM to summarize or prioritize.
            full_context_str = full_context_str[:max_context_length] + "... [CONTEXT TRUNCATED]"

        return {"full_context": full_context_str, "summaries": "\\n".join(context_parts["summaries"]), "facts": "\\n".join(context_parts["facts"])}
""",
    'prometheus_lib/memory/cleanup.py': """# Memory cleanup strategies
import asyncio
from typing import List, Dict, Any
from prometheus_lib.models.novel_state import PrometheusState
import logging

logger = logging.getLogger(__name__)

class MemoryCleanup:
    def __init__(self, vector_store_instance: Any): # Accept generic vector store
        self.vector_store = vector_store_instance

    async def prune_old_stm(self, state: PrometheusState, retention_policy: int = 5):
        '''
        Removes or summarizes older STM entries to prevent indefinite growth.
        Retention policy: keep last 'retention_policy' scenes in full detail, summarize older.
        '''
        logger.info(f"Pruning old STM entries. Retention policy: {retention_policy} scenes.")
        # This would involve querying the vector store for old STM entries
        # and potentially deleting them or replacing them with higher-level summaries.
        # For scaffold, simulate.
        if len(state.generated_novel_text.get(state.current_chapter, {})) > retention_policy:
            old_scene_numbers = sorted(state.generated_novel_text[state.current_chapter].keys())[:-retention_policy]
            for scene_num in old_scene_numbers:
                # In a real system, you'd delete from vector store or replace with summary
                logger.info(f"Simulating pruning of old scene {state.current_chapter}:{scene_num}")
                # del state.generated_novel_text[state.current_chapter][scene_num] # Don't delete actual text, just memory representation

    async def archive_novel_data(self, project_name: str, data_path: Path):
        '''Moves completed novel data or old snapshots to an archive.'''
        logger.info(f"Archiving novel data for '{project_name}' from {data_path}.")
        import time
        archive_dir = data_path.parent / "archives" / project_name / f"archive_{int(time.time())}"
        archive_dir.mkdir(parents=True, exist_ok=True)
        # Simulate moving files
        # shutil.move(data_path / project_name / "outputs", archive_dir / "outputs")
        # shutil.move(data_path / project_name / "state_snapshots", archive_dir / "state_snapshots")
        logger.info(f"Novel data for '{project_name}' archived to {archive_dir}.")
""",
    'prometheus_lib/models/config_schemas.py': """# Pydantic schema for config validation
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
    budget_usd: PositiveFloat = Field(..., description="Total budget in USD for LLM calls.")
    model_defaults: ModelDefaults
    stage_model_map: StageModelMap
    prompt_set_directory: str = Field("prompts/default", description="Directory containing prompt templates.")
    # Add other configuration parameters here as needed

    @validator('budget_usd')
    def budget_must_be_reasonable(cls, v):
        if v < 10.0: # Example: minimum budget
            raise ValueError("Budget must be at least $10.00 to be reasonable for novel generation.")
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
    invalid_config_data["budget_usd"] = 5.0
    try:
        ConfigSchema(**invalid_config_data)
    except ValidationError as e:
        print("\\nInvalid budget test passed (expected error):")
        print(e.json())
""",
    'prometheus_lib/models/outline_schemas.py': """# Pydantic schema for novel outline
from __future__ import annotations  # add this at the very top
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class NovelMetadata(BaseModel):
    project_name: str = Field(..., description="Unique identifier for the novel project.")
    title: str
    genre: str
    sub_genres: Optional[List[str]] = None
    target_audience: Optional[str] = None
    overall_tone: Optional[str] = None
    logline: Optional[str] = None
    synopsis: Optional[str] = None
    prompt_set_directory: str = Field("prompts/default", description="Specific prompt set to use for this novel.")

class Relationship(BaseModel):
    target_character_id: str
    type_of_relationship: str
    description: str

class Character(BaseModel):
    id: str = Field(..., description="Unique ID for the character.")
    name: str
    archetype: Optional[str] = None
    physical_description: Optional[str] = None
    personality_traits: Optional[str] = None
    backstory: Optional[str] = None
    motivations: Optional[str] = None
    goals: Optional[str] = None
    flaws: Optional[str] = None
    relationships: Optional[List[Relationship]] = None
    arc_summary: Optional[str] = None

class Setting(BaseModel):
    id: str = Field(..., description="Unique ID for the setting.")
    name: str
    type: Optional[str] = None
    physical_description: Optional[str] = None
    atmosphere: Optional[str] = None
    significance_to_plot: Optional[str] = None
    key_features: Optional[List[str]] = None

class PlotPoint(BaseModel):
    id: str = Field(..., description="Unique ID for the plot point.")
    type: str = Field(..., description="Type of plot point (e.g., Inciting Incident, Climax).")
    description: str
    characters_involved: Optional[List[str]] = None # List of character IDs
    setting_id: Optional[str] = None # ID of the primary setting
    desired_outcome: Optional[str] = None
    emotional_impact: Optional[str] = None
    sub_beats: Optional[List['PlotPoint']] = None # Nested plot points

class Theme(BaseModel):
    name: str
    description: Optional[str] = None
    how_it_manifests_in_story: Optional[str] = None

class StyleGuide(BaseModel):
    writing_style: Optional[str] = None
    preferred_vocabulary: Optional[List[str]] = None
    avoid_vocabulary: Optional[List[str]] = None
    sentence_length_preference: Optional[str] = None
    pacing_preference: Optional[str] = None

class NovelOutline(BaseModel):
    metadata: NovelMetadata
    characters: List[Character] = Field(default_factory=list)
    settings: List[Setting] = Field(default_factory=list)
    plot_points: List[PlotPoint] = Field(default_factory=list)
    themes: List[Theme] = Field(default_factory=list)
    style_guide: StyleGuide = Field(default_factory=StyleGuide)

# Forward reference for recursive PlotPoint definition - removed model_rebuild() for Pydantic v2

if __name__ == '__main__':
    # Example usage
    outline_data = {
        "metadata": {
            "project_name": "the_empathy_clause",
            "title": "The Empathy Clause",
            "genre": "Sci-Fi",
            "synopsis": "In a future where emotions are suppressed, a rogue empath discovers a hidden government program and must decide whether to restore humanity's feelings, even if it means chaos.",
            "prompt_set_directory": "prompts/default"
        },
        "characters": [
            {"id": "eva", "name": "Eva Rostova", "archetype": "Hero", "physical_description": "Pale, slender, with intense blue eyes.", "personality_traits": "Quiet, observant, secretly empathetic.", "backstory": "Grew up in a emotionless society.", "motivations": "Discover truth, restore emotion.", "goals": "Uncover the program.", "flaws": "Hesitant, fears exposure.", "relationships": [{"target_character_id": "dr_kane", "type_of_relationship": "mentor", "description": "Former professor, now a contact."}]},
            {"id": "dr_kane", "name": "Dr. Elias Kane", "archetype": "Mentor", "physical_description": "Aging, kind eyes, weary.", "personality_traits": "Wise, cautious, regretful.", "backstory": "Former lead scientist on the suppression project.", "motivations": "Redeem past mistakes.", "goals": "Help Eva, prevent disaster.", "flaws": "Fearful, easily discouraged."}
        ],
        "settings": [
            {"id": "city_core", "name": "Neo-Veridia City Core", "type": "City", "physical_description": "Sleek, towering chrome buildings, automated walkways, sterile.", "atmosphere": "Orderly, quiet, oppressive.", "significance_to_plot": "Main setting for daily life and initial discoveries."},
            {"id": "underground_lab", "name": "The Archive", "type": "Secret Lab", "physical_description": "Hidden beneath the city, dimly lit, filled with old tech and data.", "atmosphere": "Mysterious, dangerous, claustrophobic.", "significance_to_plot": "Where the truth about the empathy clause is stored."}
        ],
        "plot_points": [
            {
                "id": "inciting_incident",
                "type": "Inciting Incident",
                "description": "Eva experiences a surge of suppressed emotion, triggered by a malfunctioning empathy dampener.",
                "characters_involved": ["eva"],
                "setting_id": "city_core",
                "desired_outcome": "Eva realizes she's different and seeks answers.",
                "emotional_impact": "Confusion, fear, nascent curiosity."
            },
            {
                "id": "call_to_adventure",
                "type": "Call to Adventure",
                "description": "Dr. Kane contacts Eva, revealing the 'Empathy Clause' and hinting at a solution.",
                "characters_involved": ["eva", "dr_kane"],
                "setting_id": "city_core",
                "desired_outcome": "Eva agrees to help Dr. Kane.",
                "emotional_impact": "Hope, apprehension."
            }
        ],
        "themes": [
            {"name": "The Cost of Order", "description": "Exploring the trade-off between societal control and human emotion."},
            {"name": "Reclaiming Humanity", "description": "The journey to rediscover suppressed feelings."}
        ],
        "style_guide": {
            "writing_style": "clinical, detached, with moments of raw emotional breakthrough",
            "preferred_vocabulary": ["suppression", "dampener", "protocol", "resonance", "stasis"],
            "avoid_vocabulary": ["happy", "sad", "angry"] # Initially, to emphasize emotional void
        }
    }

    try:
        outline = NovelOutline(**outline_data)
        print("NovelOutline validated successfully!")
        print(outline.model_dump_json(indent=2))
    except ValidationError as e:
        print("NovelOutline validation failed:")
        print(e.json())
""",
    'prometheus_lib/models/novel_state.py': """# Pydantic model for PrometheusState
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

# Assuming NovelOutline is defined in outline_schemas.py
from prometheus_lib.models.outline_schemas import NovelOutline

class PrometheusState(BaseModel):
    novel_outline: NovelOutline
    current_chapter: int = 1
    current_scene: int = 1
    active_plot_point_id: Optional[str] = None
    generated_novel_text: Dict[int, Dict[int, str]] = Field(default_factory=dict) # {chapter_num: {scene_num: "text"}}
    character_current_states: Dict[str, Dict[str, Any]] = Field(default_factory=dict) # {char_id: {"knowledge": "...", "emotion": "..."}}
    plot_point_statuses: Dict[str, str] = Field(default_factory=dict) # {plot_point_id: "completed"}
    total_cost_usd: float = 0.0
    retry_counts: Dict[str, int] = Field(default_factory=dict) # {stage_id: count}
    memory_context: Dict[str, Any] = Field(default_factory=dict) # Cached retrieved context
    critique_results: Dict[str, Any] = Field(default_factory=dict) # Results from critique stage
    # Add fields for versioning, timestamps, etc.

    async def persist_to_disk(self, filepath: Path, version: Optional[str] = None):
        '''
        Asynchronously persists the current PrometheusState to disk.
        Includes versioning and basic compression/deduplication (conceptual).
        '''
        filepath.parent.mkdir(parents=True, exist_ok=True)
        if version is None:
            import time
            version = f"v{self.current_chapter:03d}_{self.current_scene:03d}_{int(time.time())}"
        
        snapshot_path = filepath.with_name(f"{filepath.stem}_{version}{filepath.suffix}")
        
        # Conceptual compression/deduplication:
        # In a real system, you might only save deltas or use a more efficient format
        # For now, just save the full JSON
        
        try:
            # Use asyncio to write to file to prevent blocking
            await asyncio.to_thread(lambda: snapshot_path.write_text(self.model_dump_json(indent=2)))
            logger.info(f"PrometheusState persisted to: {snapshot_path}")
        except Exception as e:
            logger.error(f"Failed to persist PrometheusState to disk: {e}")

    @classmethod
    async def load_from_disk(cls, filepath: Path) -> Optional['PrometheusState']:
        '''
        Asynchronously loads PrometheusState from disk.
        '''
        if not filepath.exists():
            logger.warning(f"No PrometheusState found at {filepath}. Starting fresh.")
            return None
        
        try:
            data = await asyncio.to_thread(filepath.read_text)
            state = cls.model_validate_json(data)
            logger.info(f"PrometheusState loaded from: {filepath}")
            return state
        except Exception as e:
            logger.error(f"Failed to load PrometheusState from disk: {e}")
            return None
""",
    'prometheus_lib/utils/prompt_loader.py': """# Prompt loading and caching utilities
import os
from pathlib import Path
import functools
import logging
from typing import Any
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

# Initialize Jinja2 environment globally for prompt loading
# Assumes 'prompts' directory is at the project root
_jinja_env = Environment(loader=FileSystemLoader(Path(__file__).parents[2] / "prompts"))

@functools.lru_cache(maxsize=128) # Cache loaded prompt templates
def load_prompt_template(template_name: str, prompt_set_dir: str = "default") -> Any: # Returns a Jinja2 Template object
    '''
    Loads a Jinja2 prompt template from the specified prompt set directory.
    Templates are cached in memory.

    Args:
        template_name (str): The name of the template file (e.g., 'write_scene_prompt.txt').
        prompt_set_dir (str): The subdirectory within 'prompts/' to load from (e.g., 'default', 'experimental_v2').

    Returns:
        jinja2.Template: The loaded Jinja2 template object.

    Raises:
        FileNotFoundError: If the template file does not exist.
    '''
    full_template_path = Path(prompt_set_dir) / template_name
    try:
        template = _jinja_env.get_template(str(full_template_path))
        logger.debug(f"Loaded prompt template: {full_template_path}")
        return template
    except Exception as e: # Jinja2 can raise TemplateNotFound or other errors
        logger.error(f"Failed to load prompt template '{full_template_path}': {e}")
        raise FileNotFoundError(f"Prompt template '{full_template_path}' not found or invalid: {e}")

if __name__ == '__main__':
    # Example usage
    try:
        template = load_prompt_template("high_concept_prompt.txt", "default")
        rendered_prompt = template.render(novel_synopsis="A test synopsis.")
        print(f"Loaded and rendered a default prompt:\\n{rendered_prompt[:100]}...")

        template_v2 = load_prompt_template("high_concept_prompt.txt", "experimental_v2")
        rendered_prompt_v2 = template_v2.render(novel_synopsis="Another test synopsis.")
        print(f"\\nLoaded and rendered an experimental prompt:\\n{rendered_prompt_v2[:100]}...")

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
""",
    'prometheus_lib/utils/logging_config.py': """# Centralized logging setup
import logging
import os

def setup_logging(level=logging.INFO):
    '''
    Sets up centralized logging for the PROMETHEUS-NOVEL project.
    Logs to console and a file.
    '''
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "prometheus_novel.log")

    # Clear existing handlers to prevent duplicate logs
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    for handler in logging.getLogger().handlers[:]:
        logging.getLogger().removeHandler(handler)

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    # Set specific log levels for noisy libraries if needed
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('tenacity').setLevel(logging.INFO) # Keep retries visible
    
    logger = logging.getLogger(__name__)
    logger.info("Logging configured.")

if __name__ == '__main__':
    setup_logging(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")
    logger.critical("This is a critical message.")
""",
    'prometheus_lib/utils/error_handling.py': """# Custom exceptions and error handlers
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class PrometheusError(Exception):
    '''Base exception for PROMETHEUS-NOVEL errors.'''
    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(message)
        self.original_exception = original_exception
        if original_exception:
            logger.error(f"PrometheusError: {message} (Original: {type(original_exception).__name__}: {original_exception})", exc_info=True)
        else:
            logger.error(f"PrometheusError: {message}")

class BudgetExceededError(PrometheusError):
    '''Raised when the LLM budget is exceeded.'''
    def __init__(self, message: str = "LLM budget exceeded."):
        super().__init__(message)
        logger.critical(f"BudgetExceededError: {message}")

class LLMGenerationError(PrometheusError):
    '''Raised when an LLM generation fails after retries/fallbacks.'''
    def __init__(self, message: str = "LLM generation failed.", original_exception: Optional[Exception] = None):
        super().__init__(message, original_exception)
        logger.error(f"LLMGenerationError: {message}")

class ValidationError(PrometheusError):
    '''Raised when data validation fails (e.g., Pydantic errors).'''
    def __init__(self, message: str = "Data validation failed.", original_exception: Optional[Exception] = None):
        super().__init__(message, original_exception)
        logger.error(f"ValidationError: {message}")

class MemoryError(PrometheusError):
    '''Raised for issues with memory management (e.g., vector store).'''
    def __init__(self, message: str = "Memory operation failed.", original_exception: Optional[Exception] = None):
        super().__init__(message, original_exception)
        logger.error(f"MemoryError: {message}")

# Centralized error handler (example for a web API or main loop)
def handle_exception(e: Exception):
    '''
    Centralized handler for uncaught exceptions.
    Logs the error and provides a human-readable message.
    '''
    if isinstance(e, PrometheusError):
        # Prometheus custom errors are already logged with context
        logger.error(f"Handled Prometheus Error: {e.args[0]}")
    else:
        logger.exception(f"An unhandled critical error occurred: {e}") # Log full traceback
        # Graceful degradation / notification
        # metrics.increment_error_counter("critical_unhandled_error") # Example metric
    print(f"\nCRITICAL ERROR: {e.args[0] if isinstance(e, PrometheusError) else 'An unexpected error occurred.'}")
    # In a production system, you might send alerts, shut down gracefully, etc.

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        raise BudgetExceededError("You ran out of money!")
    except PrometheusError as e:
        print(f"Caught: {e}")

    try:
        import requests # Simulate an external library error
        requests.get("http://nonexistent-url-12345.com")
    except Exception as e:
        handle_exception(e)

    try:
        raise LLMGenerationError("AI went rogue.", original_exception=ValueError("Bad output"))
    except PrometheusError as e:
        print(f"Caught: {e}")
""",
    'prometheus_lib/utils/sanitization.py': """# Input sanitization functions
import logging
import re

logger = logging.getLogger(__name__)

def sanitize_input(text: str) -> str:
    '''
    Sanitizes user input to prevent prompt injection or other malicious content.
    Removes potentially harmful characters or sequences.
    '''
    if not isinstance(text, str):
        logger.warning(f"Non-string input to sanitize_input: {type(text)}")
        return str(text) # Convert to string if not already

    # Remove common injection patterns (e.g., triple backticks, special characters)
    # This is a basic example; real sanitization might involve more sophisticated NLP or regex
    sanitized_text = text.replace('```', '')  # Remove markdown code blocks
    sanitized_text = re.sub(r'[<>{}$]', '', sanitized_text) # Remove common special chars
    sanitized_text = sanitized_text.strip() # Remove leading/trailing whitespace

    if len(text) != len(sanitized_text):
        logger.debug(f"Input sanitized: Original '{text[:50]}...' -> Sanitized '{sanitized_text[:50]}...'")
    return sanitized_text

def validate_text_length(text: str, max_length: int) -> bool:
    '''Checks if text length is within limits.'''
    return len(text) <= max_length

# Add more sanitization/validation functions as needed
""",
    'prometheus_lib/utils/metrics.py': """# Monitoring and metrics utilities
import time
from collections import defaultdict
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Simple in-memory metrics store for demonstration
_metrics_data: Dict[str, Any] = defaultdict(lambda: {"count": 0, "sum": 0.0, "last_value": None, "timestamps": []})

def increment_counter(name: str, value: int = 1):
    '''Increments a counter metric.'''
    _metrics_data[name]["count"] += value
    logger.debug(f"Metric '{name}' incremented to {_metrics_data[name]['count']}")

def gauge(name: str, value: float):
    '''Sets a gauge metric to a specific value.'''
    _metrics_data[name]["last_value"] = value
    logger.debug(f"Metric '{{name}}' set to {{value}}")

def observe_latency(name: str, start_time: float):
    '''Records latency for an operation.'''
    latency = time.time() - start_time
    _metrics_data[name]["sum"] += latency
    _metrics_data[name]["count"] += 1
    _metrics_data[name]["timestamps"].append(latency) # Store for p95/p99 calculation
    logger.debug(f"Metric '{{name}}' observed latency: {{latency:.4f}}s")

def get_metrics_snapshot() -> Dict[str, Any]:
    '''Returns a snapshot of current metrics.'''
    snapshot = {}
    for name, data in _metrics_data.items():
        if "timestamps" in data and data["count"] > 0:
            latencies = sorted(data["timestamps"])
            p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0
            p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0
            snapshot[name] = {
                "count": data["count"],
                "sum": data["sum"],
                "avg_latency": data["sum"] / data["count"] if data["count"] > 0 else 0,
                "p95_latency": p95,
                "p99_latency": p99,
                "last_value": data.get("last_value")
            }
        else:
            snapshot[name] = data
    return snapshot

def reset_metrics():
    '''Resets all metrics.'''
    _metrics_data.clear()
    logger.info("All metrics reset.")

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    
    increment_counter("api_calls_total")
    gauge("current_budget_usd", 500.0)
    
    start = time.time()
    time.sleep(0.05)
    observe_latency("llm_call_latency", start)

    start = time.time()
    time.sleep(0.12)
    observe_latency("llm_call_latency", start)

    increment_counter("api_calls_total", 2)

    snapshot = get_metrics_snapshot()
    print("\\nMetrics Snapshot:")
    import json
    print(json.dumps(snapshot, indent=2))

    reset_metrics()
    print("\\nMetrics after reset:", get_metrics_snapshot())
""",
    'prometheus_lib/critics/continuity_auditor.py': """# Continuity auditor for scene consistency
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
""",
    'prometheus_lib/critics/style_critic.py': """# Style critique logic
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
""",
    'prometheus_lib/critics/output_validator.py': """# Quality and safety validation
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
""",
    'run_prometheus.py': """# Main orchestration script for LangGraph workflow
import asyncio
import os
from pathlib import Path
import logging

# Setup logging first
from prometheus_lib.utils.logging_config import setup_logging
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import core components
from prometheus_lib.models.novel_state import PrometheusState
from prometheus_lib.models.outline_schemas import NovelOutline # For initial outline loading
from prometheus_lib.llm.model_router import LLMModelRouter
from prometheus_lib.llm.cost_tracker import CostTracker
from prometheus_lib.memory.vector_store import VectorStore
from prometheus_lib.memory.state_manager import StateManager
from prometheus_lib.memory.cleanup import MemoryCleanup
from prometheus_lib.critics.continuity_auditor import ContinuityAuditor
from prometheus_lib.critics.style_critic import StyleCritic
from prometheus_lib.critics.output_validator import OutputValidator
from prometheus_lib.utils.error_handling import handle_exception, PrometheusError, BudgetExceededError
from prometheus_lib.utils.metrics import get_metrics_snapshot, reset_metrics, gauge, increment_counter

# Import config loader
from configs.env_config import load_config

# Import LangGraph (assuming it's installed)
# from langgraph.graph import StateGraph, END

# Placeholder for stage functions (will be dynamically loaded or imported)
# from stages.stage_01_high_concept import high_concept_node
# from stages.stage_07_write_scene import write_scene_node

# --- Dependency Injection Setup ---
class AppServices:
    def __init__(self, config):
        self.config = config
        self.cost_tracker = CostTracker()
        self.llm_router = LLMModelRouter(config, self.cost_tracker)
        self.vector_store = VectorStore()
        self.state_manager = StateManager(self.vector_store, self.llm_router)
        self.memory_cleanup = MemoryCleanup(self.vector_store) # Pass vector store instance
        self.continuity_auditor = ContinuityAuditor(self.llm_router, self.state_manager)
        self.style_critic = StyleCritic(self.llm_router)
        self.output_validator = OutputValidator(self.llm_router)

    async def initialize(self):
        '''Initializes asynchronous services.'''
        await self.vector_store.initialize_vector_db(Path(f"data/{self.config.project_name}/memory/vector_db"))
        # Add other async initializations here

# --- LangGraph Workflow Definition (Conceptual) ---
# This part would typically be defined using LangGraph's StateGraph
# For scaffolding, we'll outline the conceptual flow.
# def create_novel_generation_graph(services: AppServices):
#     workflow = StateGraph(PrometheusState)

#     # Define nodes (stages)
#     workflow.add_node("high_concept", high_concept_node)
#     workflow.add_node("write_scene", write_scene_node)
#     # ... add all other stages

#     # Define edges (transitions)
#     workflow.add_edge("high_concept", "beat_sheet") # Example
#     workflow.add_edge("write_scene", "self_refine")

#     # Define conditional edges (e.g., based on critique results)
#     # workflow.add_conditional_edges(
#     #     "self_refine",
#     #     lambda state: "retry_scene" if not state.critique_results.get("is_valid") else "next_stage",
#     #     {"retry_scene": "write_scene", "next_stage": "motif_infusion"}
#     # )

#     # Define entry and exit points
#     workflow.set_entry_point("high_concept")
#     workflow.set_finish_point("output") # Final output stage

#     app = workflow.compile()
#     return app

# --- Main Execution Function ---
async def main():
    logger.info("Starting PROMETHEUS-NOVEL 1.0 generation pipeline.")

    # 1. Load Configuration
    try:
        config = load_config(os.getenv("PROMETHEUS_ENV"))
        gauge("budget_usd_configured", config.budget_usd)
    except Exception as e:
        handle_exception(e)
        return

    # 2. Initialize Services
    services = AppServices(config)
    try:
        await services.initialize()
    except Exception as e:
        handle_exception(e)
        return

    # 3. Load or Initialize Novel State
    project_data_path = Path(f"data/{config.project_name}/state_snapshots")
    latest_state_file = project_data_path / "latest_state.json" # Or find the latest versioned file
    
    initial_state = await PrometheusState.load_from_disk(latest_state_file)
    if initial_state is None:
        logger.info("No existing state found. Initializing new novel outline.")
        # Placeholder: In a real app, you'd load the initial outline from a file or user input
        # For now, create a dummy outline or load from outline_schemas example
        from prometheus_lib.models.outline_schemas import NovelOutline, NovelMetadata
        initial_outline = NovelOutline(metadata=NovelMetadata(project_name=config.project_name, title="The Empathy Clause", genre="Sci-Fi"))
        initial_state = PrometheusState(novel_outline=initial_outline)
        await services.state_manager.update_ltm(initial_outline) # Initialize LTM

    # Update initial state with current services (e.g., LLM router, state manager) if needed
    # This is where LangGraph's state management and node arguments come into play.
    # For a simple sequential run:
    current_state = initial_state
    
    # 4. Execute Stages (Conceptual Sequential Run for Scaffold)
    logger.info("Starting conceptual sequential stage execution...")
    try:
        # Example: Run high concept stage
        # current_state = await high_concept_node(current_state, services.llm_router, services.state_manager)
        # logger.info("High concept stage completed.")

        # Example: Simulate writing a scene
        # To run write_scene_node, current_state needs an active_plot_point_id
        # For testing, manually set one:
        if not current_state.active_plot_point_id and current_state.novel_outline.plot_points:
            current_state.active_plot_point_id = current_state.novel_outline.plot_points[0].id
            logger.info(f"Set active plot point to: {current_state.active_plot_point_id}")
        
        # current_state = await write_scene_node(current_state, services.llm_router, services.state_manager)
        # logger.info("Write scene stage completed.")

        # Simulate a loop for a few scenes/chapters
        for chapter in range(current_state.current_chapter, current_state.current_chapter + 2): # Generate 2 chapters
            current_state.current_chapter = chapter
            for scene in range(current_state.current_scene, current_state.current_scene + 3): # Generate 3 scenes per chapter
                current_state.current_scene = scene
                logger.info(f"Generating Chapter {chapter}, Scene {scene}...")
                # In a real LangGraph, this would be handled by node execution
                # For scaffold, simulate direct calls or a simplified loop
                
                # Simulate LLM call and state update
                # This is where you would call your actual stage functions
                # For example:
                # current_state = await write_scene_node(current_state, services.llm_router, services.state_manager)
                
                # Simulate cost and state update for demonstration
                await asyncio.sleep(0.5) # Simulate work
                services.cost_tracker.add_cost(f"stage_write_scene_{chapter}_{scene}", "gpt-4o-mini", 500, 1000, current_state)
                current_state.generated_novel_text.setdefault(chapter, {})[scene] = f"Content for Chapter {chapter}, Scene {scene}."
                await current_state.persist_to_disk(project_data_path / "latest_state.json")
                
                # Simulate memory cleanup periodically
                if scene % 2 == 0: # Every 2 scenes
                    await services.memory_cleanup.prune_old_stm(current_state, retention_policy=1)

        logger.info("Conceptual novel generation finished.")

    except BudgetExceededError as e:
        logger.critical(f"Generation halted: {e}")
    except PrometheusError as e:
        logger.error(f"Pipeline error: {e}")
        handle_exception(e) # Centralized error handling
    except Exception as e:
        logger.exception("An unexpected critical error occurred during pipeline execution.")
        handle_exception(e)

    # 5. Final Metrics and Cleanup
    final_metrics = get_metrics_snapshot()
    logger.info(f"Final Metrics:\\n{json.dumps(final_metrics, indent=2)}")
    reset_metrics()

    # Optional: Archive data after completion
    # await services.memory_cleanup.archive_novel_data(config.project_name, Path("data"))

if __name__ == "__main__":
    import json # Import json here for main
    asyncio.run(main())
""",
    'api.py': """# FastAPI or Flask entrypoint for external interaction
import asyncio
from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

# Setup logging for the API
from prometheus_lib.utils.logging_config import setup_logging
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import core components needed by the API
from prometheus_lib.models.novel_state import PrometheusState
from prometheus_lib.models.outline_schemas import NovelOutline
from prometheus_lib.llm.model_router import LLMModelRouter
from prometheus_lib.llm.cost_tracker import CostTracker
from prometheus_lib.memory.vector_store import VectorStore
from prometheus_lib.memory.state_manager import StateManager
from prometheus_lib.utils.error_handling import PrometheusError, BudgetExceededError, handle_exception
from prometheus_lib.utils.metrics import get_metrics_snapshot, gauge, increment_counter, observe_latency

# Import config loader
from configs.env_config import load_config

# --- API Specific Models ---
class GenerateRequest(BaseModel):
    novel_id: str
    stage_name: str
    prompt_override: Optional[str] = None
    # Add other parameters needed for specific stage generation

class NovelStateResponse(BaseModel):
    novel_id: str
    current_chapter: int
    current_scene: int
    total_cost_usd: float
    # Add more fields as needed for API response

class HealthCheckResponse(BaseModel):
    status: str = "ok"
    uptime_seconds: float
    metrics: Dict[str, Any]

# --- FastAPI App Initialization ---
app = FastAPI(
    title="PROMETHEUS-NOVEL API",
    description="API for agentic novel generation pipeline.",
    version="1.0.0",
)

# --- Global Services (initialized once) ---
# In a real production setup, these might be managed by a dependency injection container
# or loaded more robustly. For scaffolding, a simple global setup.
_app_services: Optional[Any] = None # Will hold AppServices instance

async def get_app_services() -> Any:
    global _app_services
    if _app_services is None:
        logger.info("Initializing API services...")
        try:
            config = load_config(os.getenv("PROMETHEUS_ENV"))
            _app_services = AppServices(config) # Use the AppServices class from run_prometheus.py
            await _app_services.initialize()
            logger.info("API services initialized successfully.")
        except Exception as e:
            logger.critical(f"Failed to initialize API services: {e}", exc_info=True)
            raise RuntimeError(f"API startup failed: {e}")
    return _app_services

# --- API Endpoints ---

@app.on_event("startup")
async def startup_event():
    await get_app_services() # Ensure services are initialized on startup

@app.get("/health", response_model=HealthCheckResponse, summary="Health Check")
async def health_check():
    '''Returns the health status of the API and current metrics.'''
    start_time = app.state.start_time if hasattr(app.state, 'start_time') else time.time()
    uptime = time.time() - start_time
    metrics_snapshot = get_metrics_snapshot()
    return HealthCheckResponse(status="ok", uptime_seconds=uptime, metrics=metrics_snapshot)

@app.post("/generate", response_model=NovelStateResponse, status_code=status.HTTP_202_ACCEPTED, summary="Trigger Novel Generation Stage")
async def trigger_generation(request: GenerateRequest, services: Any = Depends(get_app_services)):
    '''
    Triggers a specific stage of novel generation for a given novel ID.
    This endpoint is asynchronous and returns immediately, with generation happening in the background.
    '''
    logger.info(f"Received generation request for novel '{request.novel_id}', stage '{request.stage_name}'")
    increment_counter(f"api_requests_generate_{request.stage_name}")

    # Load novel state (or create new if not exists)
    project_data_path = Path(f"data/{request.novel_id}/state_snapshots")
    latest_state_file = project_data_path / "latest_state.json"
    current_state = await PrometheusState.load_from_disk(latest_state_file)

    if current_state is None:
        # For a new novel, create a basic outline or load from a default
        logger.info(f"No existing state for novel '{request.novel_id}'. Initializing new outline.")
        initial_outline = NovelOutline(metadata=NovelMetadata(project_name=request.novel_id, title=f"New Novel: {request.novel_id}", genre="Unknown"))
        current_state = PrometheusState(novel_outline=initial_outline)
        await services.state_manager.update_ltm(initial_outline) # Initialize LTM

    # Find the stage function (conceptual)
    # In a real LangGraph setup, you'd trigger the graph execution.
    # For scaffold, we'll simulate triggering a stage.
    # stage_func = getattr(stages_module, f"stage_{request.stage_name}_node", None) # Example dynamic load
    # if not stage_func:
    #     raise HTTPException(status_code=400, detail=f"Unknown stage: {request.stage_name}")

    async def _run_stage_in_background(state: PrometheusState):
        try:
            # Simulate running the stage
            logger.info(f"Background task: Running stage '{request.stage_name}' for novel '{request.novel_id}'")
            # This is where the actual stage logic would be called, e.g.:
            # updated_state = await stage_func(state, services.llm_router, services.state_manager)
            
            # For scaffold, simulate update
            await asyncio.sleep(2) # Simulate work
            state.total_cost_usd += 0.5 # Simulate cost
            state.current_scene += 1 # Simulate progress
            state.generated_novel_text.setdefault(state.current_chapter, {})[state.current_scene] = f"API-generated content for {request.novel_id}."
            await state.persist_to_disk(latest_state_file)
            logger.info(f"Background task: Stage '{request.stage_name}' completed for novel '{request.novel_id}'.")
            gauge(f"novel_{request.novel_id}_cost", state.total_cost_usd)
            increment_counter(f"novel_{request.novel_id}_scenes_completed")

        except BudgetExceededError as e:
            logger.error(f"Budget exceeded for novel '{request.novel_id}': {e}")
            # Notify user via some mechanism (e.g., webhook, internal message)
        except PrometheusError as e:
            logger.error(f"Prometheus Novel Error in background task for '{request.novel_id}': {e}")
        except Exception as e:
            handle_exception(e) # Catch all unexpected errors

    # Run the stage in a background task so the API call returns immediately
    asyncio.create_task(_run_stage_in_background(current_state))

    return NovelStateResponse(
        novel_id=request.novel_id,
        current_chapter=current_state.current_chapter,
        current_scene=current_state.current_scene,
        total_cost_usd=current_state.total_cost_usd
    )

@app.get("/novel/{novel_id}/state", response_model=NovelStateResponse, summary="Get Novel State")
async def get_novel_state(novel_id: str):
    '''Retrieves the current state of a novel.'''
    project_data_path = Path(f"data/{novel_id}/state_snapshots")
    latest_state_file = project_data_path / "latest_state.json"
    state = await PrometheusState.load_from_disk(latest_state_file)

    if state is None:
        raise HTTPException(status_code=404, detail=f"Novel '{novel_id}' not found or no state available.")

    return NovelStateResponse(
        novel_id=novel_id,
        current_chapter=state.current_chapter,
        current_scene=state.current_scene,
        total_cost_usd=state.total_cost_usd
    )

@app.get("/novel/{novel_id}/output", summary="Get Generated Novel Output")
async def get_novel_output(novel_id: str, chapter: Optional[int] = None, scene: Optional[int] = None):
    '''Retrieves generated novel text. Can specify chapter and scene.'''
    project_data_path = Path(f"data/{novel_id}/state_snapshots")
    latest_state_file = project_data_path / "latest_state.json"
    state = await PrometheusState.load_from_disk(latest_state_file)

    if state is None:
        raise HTTPException(status_code=404, detail=f"Novel '{novel_id}' not found or no state available.")

    if chapter is None:
        return state.generated_novel_text # Return all text
    
    if chapter not in state.generated_novel_text:
        raise HTTPException(status_code=404, detail=f"Chapter {chapter} not found for novel '{novel_id}'.")
    
    if scene is None:
        return state.generated_novel_text[chapter] # Return all scenes in chapter
    
    if scene not in state.generated_novel_text[chapter]:
        raise HTTPException(status_code=404, detail=f"Scene {scene} not found in Chapter {chapter} for novel '{novel_id}'.")
    
    return state.generated_novel_text[chapter][scene]

# --- Security (Placeholder) ---
# In a real app, implement:
# - API Key authentication (e.g., FastAPI Depends with APIKeyHeader)
# - OAuth2/JWT for user authentication
# - Role-based access control
# - Input validation (already started with Pydantic models)
# - Output sanitization (already started with output_validator)
# - Rate limiting (already in model_router, but also apply at API gateway/FastAPI level)
# - CORS configuration
# - HTTPS enforcement
# - Secure secret management (e.g., HashiCorp Vault, AWS Secrets Manager)

# To run this API:
# uvicorn api:app --reload --port 8000
""",
    'pyproject.toml': """[tool.poetry]
name = "prometheus-novel"
version = "0.1.0"
description = "Agentic novel generation pipeline"
authors = ["Your Name <you@example.com>"]
readme = "README.md"

[tool.poetry.dependencies]
python = "^3.10"
pydantic = "^2.5.3" # Pydantic v2
pyyaml = "^6.0.1" # For loading YAML configs
openai = "^1.10.0" # For OpenAI LLM client
google-generativeai = "^0.3.0" # For Gemini LLM client
aiohttp = "^3.9.3" # For async HTTP requests
tenacity = "^8.2.3" # For retries
jinja2 = "^3.1.3" # For prompt templating
langchain = "^0.1.0" # Core LangChain utilities (if used, otherwise remove)
langgraph = "^0.0.30" # For orchestration (adjust version as needed)
chromadb = "^0.4.22" # Example vector database
sentence-transformers = "^2.2.2" # For embeddings and re-ranking
uvicorn = "^0.27.0" # For running FastAPI
fastapi = "^0.109.0" # For API layer
redis = "^5.0.1" # For external caching (if used)
# filelock = "^3.13.1" # For file locking (if using local files for state/DB)

[tool.poetry.group.dev.dependencies]
mypy = "^1.8.0" # For static type checking
ruff = "^0.2.1" # For linting and formatting
pytest = "^8.0.0" # For testing
pytest-asyncio = "^0.23.5" # For testing async code

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.mypy]
# MyPy configuration
# enforce 100% type coverage for new code
disallow_untyped_defs = true
no_implicit_optional = true
warn_return_any = true
warn_unused_ignores = true
show_error_codes = true
# strict = true # Consider enabling strict mode gradually

[tool.ruff]
# Ruff configuration (linting and formatting)
line-length = 120
select = ["E", "F", "W", "I", "N", "D", "UP", "B", "C4", "A"] # Common lint rules
ignore = ["D100", "D104", "D105", "D107"] # Ignore missing docstrings for modules/functions/classes (adjust as needed)

[tool.ruff.per-file-ignores]
"__init__.py" = ["F401"] # Allow unused imports in __init__.py
"tests/*" = ["D"] # Don't enforce docstrings in tests

""",
    '.env': '# API_KEY=your_openai_api_key_here\n# PROMETHEUS_ENV=dev # Set to dev, staging, prod etc.\n',
    'docs/README.md': """# PROMETHEUS-NOVEL 1.0 Documentation

This directory contains documentation, runbooks, and failure scenarios for the PROMETHEUS-NOVEL 1.0 project.

## Project Overview
(Briefly describe the project's goal and high-level architecture)

## Getting Started
1.  **Scaffold the project:**
    ```bash
    python prometheus_novel_scaffold.py
    ```
2.  **Install dependencies (using Poetry):**
    ```bash
    cd prometheus_novel
    poetry install
    poetry shell
    ```
3.  **Configure API Keys:**
    Edit the `.env` file in the project root to add your LLM API keys.
    ```
    OPENAI_API_KEY=sk-...
    # GOOGLE_API_KEY=your_gemini_api_key
    ```
4.  **Run the main pipeline (conceptual):**
    ```bash
    python run_prometheus.py
    ```
5.  **Run the API (conceptual):**
    ```bash
    uvicorn api:app --reload --port 8000
    ```

## Runbooks & Failure Scenarios
(Detailed guides for operating the system, diagnosing issues, and recovery procedures)

* **Cold Start Procedure:** How to start the system from scratch.
* **Resuming Generation:** How to pick up from a previous state after a pause or crash.
* **Budget Exceeded:** What to do when the LLM budget is hit.
* **LLM API Rate Limits/Errors:** Troubleshooting steps for API issues.
* **Memory Exhaustion:** How to handle and prevent Out-of-Memory errors.
* **Consistency Issues:** How to debug narrative inconsistencies.
* **Data Corruption:** Steps for recovering from corrupted state/memory.
* **Adding New Stages/Critics:** Guide for extending the system.

---
""",
    # Add placeholder prompt files
    'prompts/default/high_concept_prompt.txt': """You are an expert novelist. Your task is to generate a high-concept summary for a novel.
The novel's synopsis is: {{ novel_synopsis }}

Generate a compelling, one-paragraph high concept, focusing on the core conflict and unique hook.
""",
    'prompts/default/write_scene_prompt.txt': """You are a master storyteller. Write a detailed scene for a novel.
Novel Title: {{ novel_title }}
Novel Synopsis: {{ novel_synopsis }}

Current Plot Point: {{ plot_point_description }}
Characters Involved:
{{ characters_involved_details }}

Setting:
{{ setting_details }}

Relevant Previous Context and Facts:
{{ retrieved_memory_context }}

Style Guide: {{ style_guide }}

Write the scene, focusing on advancing the plot point, developing characters, and utilizing the setting. Ensure the tone aligns with the style guide.
""",
    'prompts/default/continuity_audit_prompt.txt': """You are a meticulous continuity editor for a novel.
Review the following scene for any inconsistencies with the provided novel outline and relevant context.

Scene to Audit:
---
{{ scene_text }}
---

Novel Outline Summary: {{ novel_outline_summary }}

Relevant Context (previous scenes, character backstories, world rules):
---
{{ relevant_context }}
---

Character Current States (important for behavioral consistency):
---
{{ character_current_states }}
---

Identify any issues related to:
- Character behavior or knowledge contradicting their established traits or current state.
- Plot holes or contradictions with the overall outline.
- Inconsistencies with the described setting or world rules.

Respond ONLY with a JSON object in the following format:
{
  "is_consistent": true/false,
  "issues": [
    {"type": "CHARACTER_INCONSISTENCY", "description": "...", "location": "...", "suggested_fix": "..."},
    {"type": "PLOT_HOLE", "description": "...", "location": "...", "suggested_fix": "..."},
    {"type": "SETTING_CONTRADICTION", "description": "...", "location": "...", "suggested_fix": "..."}
  ],
  "overall_comment": "..."
}
If no issues, "issues" should be an empty array and "is_consistent" true.
""",
    'prompts/default/style_critique_prompt.txt': """You are a discerning literary critic.
Critique the following scene for adherence to the provided style guide.

Scene to Critique:
---
{{ scene_text }}
---

Style Guide:
---
{{ style_guide_details }}
---

Evaluate aspects like:
- Writing style (e.g., formal, informal, poetic, gritty, conversational)
- Vocabulary usage (preferred/avoided words)
- Sentence length and complexity
- Pacing
- Overall tone and atmosphere

Respond ONLY with a JSON object in the following format:
{
  "is_style_adherent": true/false,
  "issues": [
    {"type": "TONE_MISMATCH", "description": "...", "example_text": "...", "suggested_fix": "..."},
    {"type": "VOCABULARY_MISUSE", "description": "...", "example_text": "...", "suggested_fix": "..."}
  ],
  "overall_comment": "..."
}
If no issues, "issues" should be an empty array and "is_style_adherent" true.
""",
    'prompts/default/output_safety_prompt.txt': """You are a content moderation and quality assurance AI.
Review the following text for safety, quality, and general appropriateness for a novel.

Text to Review:
---
{{ text_to_check }}
---

Consider:
- Is the content free from hate speech, violence, sexual content, or other harmful material?
- Is the content coherent, relevant to the implied context, and well-written?
- Does it meet a minimum quality threshold?

Respond ONLY with a JSON object in the following format:
{
  "is_safe": true/false,
  "reason": "If not safe, explain why.",
  "is_quality_ok": true/false,
  "quality_reason": "If not high quality, explain why.",
  "overall_assessment": "Brief summary."
}
""",
    'prompts/experimental_v2/high_concept_prompt.txt': """As a visionary storyteller, craft a high-concept pitch for a novel.
The core idea is: {{ novel_synopsis }}

Focus on a unique twist, a compelling central question, and a strong sense of genre. Aim for a pitch that grabs attention immediately.
""",
    'prompts/experimental_v2/write_scene_prompt.txt': """You are an experimental novelist, pushing boundaries. Write a scene.
Novel: {{ novel_title }}
Premise: {{ novel_synopsis }}

Current Narrative Beat: {{ plot_point_description }}
Characters Present:
{{ characters_involved_details }}

Environment:
{{ setting_details }}

Memory Stream:
{{ retrieved_memory_context }}

Style Directives: {{ style_guide }}

Infuse the scene with unexpected turns, deep character psychology, and vivid, sensory details. Experiment with narrative voice and pacing while adhering to the core beat.
""",
}  # <--- This closing brace is critical!

# Create directories
for d in dirs:
    dir_path = project_root / d
    dir_path.mkdir(parents=True, exist_ok=True)
    # Touch __init__.py for Python packages
    if 'prometheus_lib' in d or d == 'stages':
        init_file = dir_path / '__init__.py'
        if not init_file.exists(): # Only create if it doesn't exist
            init_file.write_text('# Package init\n')
    # Add __init__.py to prompt subdirectories
    if d.startswith('prompts/'):
        init_file = dir_path / '__init__.py'
        if not init_file.exists():
            init_file.write_text('# Prompt set init\n')

# Create files with placeholder content
for rel_path, content in files.items():
    file_path = project_root / rel_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if not file_path.exists(): # Only write if file doesn't exist
        file_path.write_text(content)

print(f"Scaffolded PROMETHEUS-NOVEL project at {project_root.resolve()}")