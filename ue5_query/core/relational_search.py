"""
UE5 Source Query - Relational Filtered Search (v2.1)
Combines SQLite relational filtering with NumPy vector scoring.
"""

import numpy as np
from typing import List, Dict, Optional, Any
from pathlib import Path
from ue5_query.utils.logger import get_project_logger
from ue5_query.utils.db_manager import DatabaseManager

logger = get_project_logger(__name__)

class RelationalFilteredSearch:
    """
    Hybrid search engine that uses SQLite for boolean filtering and NumPy for vector similarity.
    
    Refactors the original FilteredSearch to move O(N) mask-based filtering into 
    O(log N) or O(index) SQL queries.
    """

    def __init__(self, embeddings: np.ndarray, db_manager: DatabaseManager):
        """
        Args:
            embeddings: Vector embeddings (N x D)
            db_manager: Async database manager
        """
        self.embeddings = embeddings
        self.db = db_manager

    async def search(
        self,
        query_vec: np.ndarray,
        top_k: int = 5,
        # Filters (Passed to SQLite)
        entity: Optional[str] = None,
        entity_type: Optional[str] = None,
        origin: Optional[str] = None,
        has_uproperty: Optional[bool] = None,
        has_uclass: Optional[bool] = None,
        has_ufunction: Optional[bool] = None,
        has_ustruct: Optional[bool] = None,
        file_type: Optional[str] = None,
        # Boosting (NumPy Phase)
        boost_entities: Optional[List[str]] = None,
        boost_macros: bool = False,
        use_logical_boosts: bool = True,
        # Query context
        query_text: Optional[str] = None,
        query_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform a filtered search using SQLite for indices and NumPy for scoring.
        """
        
        # 1. Apply Relational Filters (SQLite Phase)
        # We build a dynamic query to get valid vector_indexes
        sql = "SELECT vector_index, id, path, has_uproperty, has_ufunction, has_uclass, has_ustruct FROM chunks_view WHERE 1=1"
        # Using a view 'chunks_view' would be cleaner, but let's build the join for now
        sql = """
            SELECT c.vector_index, c.id, f.path, f.origin, c.chunk_index, c.total_chunks,
                   c.has_uproperty, c.has_ufunction, c.has_uclass, c.has_ustruct,
                   f.is_header, f.is_implementation
            FROM chunks c
            JOIN files f ON f.id = c.file_id
            WHERE 1=1
        """
        params = []
        
        if origin:
            sql += " AND f.origin = ?"
            params.append(origin)
            
        if has_uproperty is not None:
            sql += " AND c.has_uproperty = ?"
            params.append(1 if has_uproperty else 0)
            
        if file_type == 'header':
            sql += " AND f.is_header = 1"
        elif file_type == 'implementation':
            sql += " AND f.is_implementation = 1"
            
        if entity:
            sql += " AND c.id IN (SELECT ce.chunk_id FROM chunk_entities ce JOIN entities e ON e.id = ce.entity_id WHERE e.name = ?)"
            params.append(entity)
            
        if entity_type:
            sql += " AND c.id IN (SELECT ce.chunk_id FROM chunk_entities ce JOIN entities e ON e.id = ce.entity_id WHERE e.type = ?)"
            params.append(entity_type)

        # Execute relational filter
        valid_rows = await self.db.fetch_all(sql, tuple(params))
        
        if not valid_rows:
            # If no results found with strict filters, we return empty
            # unless it was a global search (no filters), handled by caller
            return []

        # 2. Vector Similarity (NumPy Phase)
        valid_indices = [row['vector_index'] for row in valid_rows]
        subset_embeddings = self.embeddings[valid_indices]
        
        # Score query
        scores = subset_embeddings @ query_vec
        
        # 3. Relevance Boosting
        results = []
        for i, row in enumerate(valid_rows):
            score = float(scores[i])
            idx = valid_indices[i]
            
            boost_factor = 1.0
            
            # Macro Boosting (Using DB columns)
            if boost_macros:
                if row['has_uproperty'] or row['has_ufunction'] or row['has_uclass'] or row['has_ustruct']:
                    boost_factor *= 1.15
            
            # Logical Boosts (File Name matching etc)
            if use_logical_boosts and boost_entities:
                path_lower = Path(row['path']).name.lower()
                for ent in boost_entities:
                    entity_base = ent.lstrip('FUAE').lower()
                    if entity_base in path_lower:
                        boost_factor *= 3.0
                        break
                
                # Header prioritization
                if query_type in ['definition', 'hybrid']:
                    if row['is_header']: boost_factor *= 2.5
                    elif row['is_implementation']: boost_factor *= 0.5

            score *= boost_factor
            
            # Prepare result record
            res = dict(row)
            res['score'] = score
            results.append(res)

        # 4. Sort and return
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]
