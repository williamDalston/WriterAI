# Pydantic model for PrometheusState
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
