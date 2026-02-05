"""
UE5 Source Query - Asynchronous Query Engine (v2.1)
Utilizes SQLite for metadata filtering and FTS5 search.
"""

import os
import json
import time
import asyncio
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from functools import lru_cache

from ue5_query.utils.logger import get_project_logger
from ue5_query.utils.db_manager import DatabaseManager

logger = get_project_logger(__name__)

class SemanticSearchEngine:
    """
    Handles semantic search using embeddings and SQLite metadata.
    Designed for async execution within FastAPI.
    """
    
    def __init__(self, vector_dir: Optional[Path] = None, model_name: str = "microsoft/unixcoder-base"):
        if vector_dir is None:
            # Default to project data directory
            root = Path(__file__).resolve().parent.parent.parent
            vector_dir = root / "data"
            
        self.vector_path = vector_dir / "vector_store.npz"
        self.db_manager = DatabaseManager(vector_dir / "ue5_query.db")
        self.model_name = model_name
        self._embeddings: Optional[np.ndarray] = None
        self._model = None

    def _get_model(self):
        """Lazy load the embedding model"""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def load_embeddings(self):
        """Load embeddings into memory (synchronous, typically done at startup)"""
        if not self.vector_path.exists():
            raise FileNotFoundError(f"Vector store missing at {self.vector_path}")
        
        logger.info(f"Loading embeddings from {self.vector_path}...")
        # Use memory map for efficiency with large arrays
        data = np.load(self.vector_path, mmap_mode="r", allow_pickle=False)
        self._embeddings = data["embeddings"]
        logger.info(f"Loaded {len(self._embeddings)} embeddings.")

    async def embed_query(self, query_text: str) -> np.ndarray:
        """Embed a query string using the model (run in thread pool to avoid blocking)"""
        loop = asyncio.get_event_loop()
        model = self._get_model()
        return await loop.run_in_executor(
            None, 
            lambda: model.encode([query_text], convert_to_numpy=True, normalize_embeddings=True)[0]
        )

    async def search(self, 
                     query_text: str, 
                     top_k: int = 5, 
                     origin: Optional[str] = None,
                     entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Perform a filtered semantic search.
        1. Query SQLite for valid vector_indexes based on filters.
        2. Perform vector similarity search on the subset.
        3. Join back with SQLite for full metadata.
        """
        if self._embeddings is None:
            self.load_embeddings()

        # 1. Get filtered indices from DB
        # If no filters, we use all indices (None returns empty list in current helper, let's fix that)
        filtered_indices = await self.db_manager.filter_chunks(origin=origin, entity_type=entity_type)
        
        # 2. Embed the query
        qvec = await self.embed_query(query_text)
        
        # 3. Vector Search
        if filtered_indices:
            # Re-align embeddings to filtered subset
            subset_embeddings = self._embeddings[filtered_indices]
            sims = subset_embeddings @ qvec
            
            # Find top K in subset
            top_subset_idxs = np.argsort(-sims)[:top_k]
            
            # Map back to original vector_index
            top_results = []
            for idx in top_subset_idxs:
                vector_idx = filtered_indices[idx]
                score = float(sims[idx])
                top_results.append((vector_idx, score))
        else:
            # Search all embeddings
            sims = self._embeddings @ qvec
            top_idxs = np.argsort(-sims)[:top_k]
            top_results = [(int(idx), float(sims[idx])) for idx in top_idxs]

        # 4. Enriched Metadata Retrieval
        final_hits = []
        for vector_idx, score in top_results:
            # Query full metadata for this chunk
            sql = """
                SELECT c.*, f.path, f.origin
                FROM chunks c
                JOIN files f ON f.id = c.file_id
                WHERE c.vector_index = ?
            """
            meta = await self.db_manager.fetch_one(sql, (vector_idx,))
            if meta:
                meta['score'] = score
                final_hits.append(meta)
                
        return final_hits

    async def search_definitions(self, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search exact definitions using SQLite FTS5"""
        return await self.db_manager.search_definitions(query_text, limit)

    async def close(self):
        await self.db_manager.close()
