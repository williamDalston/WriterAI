# Memory cleanup strategies using real vector store
import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any
from prometheus_lib.models.novel_state import PrometheusState
from prometheus_lib.memory.vector_store import VectorStore
import logging

logger = logging.getLogger(__name__)

class MemoryCleanup:
    def __init__(self, vector_store_instance: VectorStore):
        self.vector_store = vector_store_instance

    async def prune_old_stm(self, state: PrometheusState, retention_policy: int = 5):
        """Remove old STM entries from vector store to prevent unbounded growth.

        Keeps the last `retention_policy` scenes' summaries in the vector store,
        deletes older ones. The actual novel text in state.generated_novel_text
        is NOT affected — only the memory/retrieval representations.
        """
        logger.info(f"Pruning old STM entries. Retention: last {retention_policy} scenes.")

        current_chapter = state.current_chapter
        current_scene = state.current_scene

        # Calculate which scenes to prune: anything older than retention_policy scenes
        scenes_to_keep = set()
        scene_count = 0
        for ch in range(current_chapter, 0, -1):
            chapter_scenes = state.generated_novel_text.get(ch, {})
            for sc in sorted(chapter_scenes.keys(), reverse=True):
                if scene_count < retention_policy:
                    scenes_to_keep.add((ch, sc))
                    scene_count += 1
                else:
                    break
            if scene_count >= retention_policy:
                break

        # Delete old STM entries from vector store
        # We delete by metadata filter for scenes not in the keep set
        for ch, chapter_scenes in state.generated_novel_text.items():
            for sc in chapter_scenes:
                if (ch, sc) not in scenes_to_keep:
                    try:
                        await self.vector_store.delete_by_metadata({
                            "type": "scene_summary",
                            "memory_type": "stm",
                            "chapter": ch,
                            "scene": sc
                        })
                        logger.debug(f"Pruned STM for chapter {ch}, scene {sc}")
                    except Exception as e:
                        logger.warning(f"Failed to prune STM Ch{ch}-S{sc}: {e}")

        logger.info(f"STM pruning complete. Kept {len(scenes_to_keep)} recent scene summaries.")

    async def archive_novel_data(self, project_name: str, data_path: Path):
        """Move completed novel data to an archive directory."""
        logger.info(f"Archiving novel data for '{project_name}' from {data_path}.")
        archive_dir = data_path.parent / "archives" / project_name / f"archive_{int(time.time())}"
        archive_dir.mkdir(parents=True, exist_ok=True)

        import shutil
        # Archive output files if they exist
        for subdir in ["output", "drafts", "memory"]:
            source = data_path / subdir
            if source.exists():
                dest = archive_dir / subdir
                try:
                    shutil.copytree(str(source), str(dest))
                    logger.info(f"Archived {subdir} -> {dest}")
                except Exception as e:
                    logger.warning(f"Failed to archive {subdir}: {e}")

        logger.info(f"Novel data for '{project_name}' archived to {archive_dir}.")
