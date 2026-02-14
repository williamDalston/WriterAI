# Hybrid search and caching implementation using ChromaDB + sentence-transformers
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
import hashlib

logger = logging.getLogger(__name__)


class VectorStore:
    """Production vector store using ChromaDB for persistence and sentence-transformers for embeddings."""

    def __init__(self):
        self._client = None
        self._collection = None
        self._embedding_fn = None
        self._initialized = False
        # Simple query cache: hash(query+k) -> results
        self._cache: Dict[str, List[Dict[str, Any]]] = {}
        self._cache_max = 128

    async def initialize_vector_db(self, data_path: Path, collection_name: str = "prometheus_memory"):
        """Initialize ChromaDB with sentence-transformer embeddings."""
        if self._initialized:
            return

        data_path = Path(data_path)
        data_path.mkdir(parents=True, exist_ok=True)

        try:
            import chromadb
            from chromadb.config import Settings

            # Persistent ChromaDB client stored on disk
            self._client = await asyncio.to_thread(
                chromadb.PersistentClient,
                path=str(data_path),
                settings=Settings(anonymized_telemetry=False)
            )

            # Load sentence-transformer for embeddings
            self._embedding_fn = await self._load_embedding_function()

            # Get or create collection with the embedding function
            self._collection = await asyncio.to_thread(
                self._client.get_or_create_collection,
                name=collection_name,
                embedding_function=self._embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )

            self._initialized = True
            count = self._collection.count()
            logger.info(f"ChromaDB initialized at {data_path} with {count} existing documents")

        except ImportError as e:
            logger.error(
                f"Required packages not installed: {e}. "
                "Install with: pip install chromadb sentence-transformers"
            )
            raise
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

    async def _load_embedding_function(self):
        """Load sentence-transformer embedding function for ChromaDB."""
        try:
            from chromadb.utils import embedding_functions
            ef = await asyncio.to_thread(
                embedding_functions.SentenceTransformerEmbeddingFunction,
                model_name="all-MiniLM-L6-v2"  # Fast, good quality, 384 dims
            )
            logger.info("Loaded sentence-transformer embedding model: all-MiniLM-L6-v2")
            return ef
        except Exception as e:
            logger.warning(f"Failed to load sentence-transformers ({e}), falling back to default")
            from chromadb.utils import embedding_functions
            return embedding_functions.DefaultEmbeddingFunction()

    def _ensure_initialized(self):
        if not self._initialized or not self._collection:
            raise RuntimeError("Vector database not initialized. Call initialize_vector_db first.")

    async def add_documents_batch(self, documents: List[Dict[str, Any]]):
        """Add documents to ChromaDB in batches."""
        self._ensure_initialized()

        if not documents:
            return

        ids = []
        contents = []
        metadatas = []

        for doc in documents:
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})

            # Generate stable ID from content hash + metadata
            id_source = content + str(sorted(metadata.items()))
            doc_id = hashlib.sha256(id_source.encode()).hexdigest()[:16]
            ids.append(doc_id)
            contents.append(content)

            # ChromaDB metadata values must be str, int, float, or bool
            clean_meta = {}
            for k, v in metadata.items():
                if v is None:
                    continue
                if isinstance(v, (str, int, float, bool)):
                    clean_meta[k] = v
                else:
                    clean_meta[k] = str(v)
            metadatas.append(clean_meta)

        # Batch upsert (handles duplicates gracefully)
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_contents = contents[i:i + batch_size]
            batch_metas = metadatas[i:i + batch_size]

            await asyncio.to_thread(
                self._collection.upsert,
                ids=batch_ids,
                documents=batch_contents,
                metadatas=batch_metas
            )

        # Invalidate cache since data changed
        self._cache.clear()
        logger.info(f"Added {len(ids)} documents to vector store (total: {self._collection.count()})")

    async def hybrid_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Semantic search via ChromaDB embeddings with result caching."""
        self._ensure_initialized()

        # Check cache
        cache_key = hashlib.md5(f"{query}:{k}".encode()).hexdigest()
        if cache_key in self._cache:
            logger.debug(f"Cache hit for query: '{query[:50]}...'")
            return self._cache[cache_key]

        collection_count = self._collection.count()
        if collection_count == 0:
            return []

        # Don't request more results than exist
        actual_k = min(k, collection_count)

        try:
            # Semantic search using ChromaDB's built-in embedding search
            results = await asyncio.to_thread(
                self._collection.query,
                query_texts=[query],
                n_results=actual_k,
                include=["documents", "metadatas", "distances"]
            )

            # Format results
            formatted = []
            if results and results["documents"] and results["documents"][0]:
                for idx, (doc, meta, dist) in enumerate(zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0]
                )):
                    formatted.append({
                        "id": results["ids"][0][idx] if results["ids"] else str(idx),
                        "content": doc,
                        "metadata": meta,
                        "score": 1.0 - dist  # Convert distance to similarity score
                    })

            # Sort by relevance score (highest first)
            formatted.sort(key=lambda x: x.get("score", 0), reverse=True)

            # Cache results
            if len(self._cache) >= self._cache_max:
                # Evict oldest entry
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            self._cache[cache_key] = formatted

            logger.info(f"Hybrid search found {len(formatted)} results for: '{query[:50]}...'")
            return formatted

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    async def search_by_metadata(self, filters: Dict[str, Any], k: int = 10) -> List[Dict[str, Any]]:
        """Search documents by metadata filters (e.g., type=character, chapter=3)."""
        self._ensure_initialized()

        collection_count = self._collection.count()
        if collection_count == 0:
            return []

        actual_k = min(k, collection_count)

        # Build ChromaDB where filter
        where_filter = {}
        for key, value in filters.items():
            if isinstance(value, (str, int, float, bool)):
                where_filter[key] = value

        if not where_filter:
            return []

        try:
            results = await asyncio.to_thread(
                self._collection.get,
                where=where_filter,
                limit=actual_k,
                include=["documents", "metadatas"]
            )

            formatted = []
            if results and results["documents"]:
                for idx, (doc, meta) in enumerate(zip(results["documents"], results["metadatas"])):
                    formatted.append({
                        "id": results["ids"][idx],
                        "content": doc,
                        "metadata": meta,
                        "score": 1.0
                    })

            return formatted

        except Exception as e:
            logger.error(f"Metadata search failed: {e}")
            return []

    async def delete_by_metadata(self, filters: Dict[str, Any]):
        """Delete documents matching metadata filters."""
        self._ensure_initialized()

        where_filter = {k: v for k, v in filters.items() if isinstance(v, (str, int, float, bool))}
        if not where_filter:
            return

        try:
            await asyncio.to_thread(self._collection.delete, where=where_filter)
            self._cache.clear()
            logger.info(f"Deleted documents matching: {where_filter}")
        except Exception as e:
            logger.error(f"Delete failed: {e}")

    def clear_cache(self):
        """Clear the search result cache."""
        self._cache.clear()
        logger.info("Vector store cache cleared.")

    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        if not self._initialized:
            return {"initialized": False}

        count = self._collection.count() if self._collection else 0
        return {
            "initialized": True,
            "total_documents": count,
            "cache_size": len(self._cache),
            "cache_max": self._cache_max
        }
