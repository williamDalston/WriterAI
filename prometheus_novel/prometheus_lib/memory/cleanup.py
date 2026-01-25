# Memory cleanup strategies
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
