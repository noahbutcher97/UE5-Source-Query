# python
# ===== File: FilteredSearch.py =====
"""
Enhanced semantic search with metadata filtering and relevance boosting.
Uses enriched metadata to improve search accuracy.
"""
import numpy as np
from typing import List, Dict, Optional, Set
from pathlib import Path


class FilteredSearch:
    """
    Semantic search with metadata-based filtering and boosting.

    Filters:
    - entity: Only chunks containing specific entity
    - entity_type: Only chunks with specific types (struct, class, enum)
    - has_macro: Only chunks with UE5 macros (UPROPERTY, UCLASS, etc.)
    - file_type: Only headers or implementation files

    Boosting:
    - Chunks with matching entities score higher
    - Chunks with UE5 macros score higher for definition queries
    """

    def __init__(self, embeddings: np.ndarray, metadata: List[Dict]):
        """
        Args:
            embeddings: Vector embeddings (N x 384)
            metadata: Enriched metadata (must have 'entities', 'entity_types', etc.)
        """
        self.embeddings = embeddings
        self.metadata = metadata

        # Check if metadata is enriched
        self.is_enriched = any('entities' in m for m in metadata)
        if not self.is_enriched:
            print("WARNING: Metadata not enriched. Filtering will be limited.")

    def search(
        self,
        query_vec: np.ndarray,
        top_k: int = 5,
        # Filters
        entity: Optional[str] = None,
        entity_type: Optional[str] = None,
        origin: Optional[str] = None,  # 'engine' or 'project'
        has_uproperty: Optional[bool] = None,
        has_uclass: Optional[bool] = None,
        has_ufunction: Optional[bool] = None,
        has_ustruct: Optional[bool] = None,
        file_type: Optional[str] = None,  # 'header' or 'implementation'
        # Boosting
        boost_entities: Optional[List[str]] = None,
        boost_macros: bool = False,
        # Logical compensation for poor models
        use_logical_boosts: bool = True,
        # Text query for sparse scoring
        query_text: Optional[str] = None,
        query_type: Optional[str] = None  # 'definition', 'hybrid', 'semantic'
    ) -> List[Dict]:
        """
        Search with filtering and relevance boosting.

        Args:
            query_vec: Query embedding vector
            top_k: Number of results
            entity: Filter to chunks containing this entity
            entity_type: Filter by type ('struct', 'class', 'enum')
            origin: Filter by origin ('engine', 'project')
            has_uproperty: Filter by UPROPERTY presence
            has_uclass: Filter by UCLASS presence
            has_ufunction: Filter by UFUNCTION presence
            has_ustruct: Filter by USTRUCT presence
            file_type: 'header' or 'implementation'
            boost_entities: List of entities to boost in ranking
            boost_macros: Boost chunks with UE5 macros
            query_text: Raw query text for keyword/sparse scoring boost

        Returns:
            List of results with scores
        """
        # Calculate base similarity scores (Dense Score)
        scores = self.embeddings @ query_vec

        # Apply filters
        valid_indices = self._apply_filters(
            entity=entity,
            entity_type=entity_type,
            origin=origin,
            has_uproperty=has_uproperty,
            has_uclass=has_uclass,
            has_ufunction=has_ufunction,
            has_ustruct=has_ustruct,
            file_type=file_type
        )

        # Apply sparse scoring (Keyword Boost)
        if query_text:
            sparse_scores = self._calculate_sparse_score(query_text, valid_indices)
            # Combine: Dense + 0.3 * Sparse
            # This ensures strong keyword matches bubble up
            for i, idx in enumerate(valid_indices):
                scores[idx] += sparse_scores[i]

        # Apply boosting
        if boost_entities or boost_macros:
            scores = self._apply_boosting(
                scores,
                boost_entities=boost_entities,
                boost_macros=boost_macros
            )

        # Apply logical boosts (compensate for poor model)
        if use_logical_boosts and boost_entities:
            scores = self._apply_logical_boosts(
                scores,
                boost_entities=boost_entities,
                query_type=query_type
            )

        # Filter scores to valid indices
        filtered_scores = np.full_like(scores, -np.inf)
        filtered_scores[valid_indices] = scores[valid_indices]

        # Get top-k
        top_indices = np.argsort(-filtered_scores)[:top_k]

        # Build results
        results = []
        for idx in top_indices:
            if filtered_scores[idx] > -np.inf:  # Only include valid results
                result = self.metadata[idx].copy()
                result['score'] = float(filtered_scores[idx])
                results.append(result)

        return results

    def _calculate_sparse_score(self, query: str, indices: List[int]) -> np.ndarray:
        """
        Calculate sparse (keyword) score for selected indices.
        Simple BM25-lite approach: favors matches in file names and entities.
        """
        if not query or not indices:
            return np.zeros(0) if not indices else np.zeros(len(indices))

        query_tokens = set(query.lower().split())
        # Remove common stop words to reduce noise
        stop_words = {'the', 'a', 'an', 'in', 'on', 'at', 'for', 'to', 'of', 'is', 'are', 'how', 'why', 'what'}
        query_tokens -= stop_words
        
        if not query_tokens:
            return np.zeros(len(indices))

        sparse_scores = np.zeros(len(indices))
        
        for i, idx in enumerate(indices):
            meta = self.metadata[idx]
            score = 0.0
            
            # Check path (High value for file name matches)
            path_str = str(meta.get('path', '')).lower()
            file_name = Path(path_str).name
            
            # Check entities (High value)
            entities = [str(e).lower() for e in meta.get('entities', [])]
            
            for token in query_tokens:
                # File Name match (Strong signal)
                if token in file_name:
                    score += 0.4
                elif token in path_str:
                    score += 0.1
                
                # Exact entity match
                if token in entities:
                    score += 0.5
                # Partial entity match
                elif any(token in e for e in entities):
                    score += 0.2
                    
            sparse_scores[i] = score
            
        return sparse_scores

    def _apply_filters(
        self,
        entity: Optional[str],
        entity_type: Optional[str],
        origin: Optional[str],
        has_uproperty: Optional[bool],
        has_uclass: Optional[bool],
        has_ufunction: Optional[bool],
        has_ustruct: Optional[bool],
        file_type: Optional[str]
    ) -> List[int]:
        """Apply filters and return valid indices"""
        valid_indices = []

        for i, meta in enumerate(self.metadata):
            # Origin filter
            if origin is not None:
                # Default to 'engine' for backward compatibility
                chunk_origin = meta.get('origin', 'engine')
                if chunk_origin != origin:
                    continue

            # Entity filter
            if entity is not None:
                if not self.is_enriched:
                    continue
                entities = meta.get('entities', [])
                if entity not in entities:
                    continue

            # Entity type filter
            if entity_type is not None:
                if not self.is_enriched:
                    continue
                entity_types = meta.get('entity_types', [])
                if entity_type not in entity_types:
                    continue

            # UPROPERTY filter
            if has_uproperty is not None:
                if not self.is_enriched:
                    continue
                if meta.get('has_uproperty', False) != has_uproperty:
                    continue

            # UCLASS filter
            if has_uclass is not None:
                if not self.is_enriched:
                    continue
                if meta.get('has_uclass', False) != has_uclass:
                    continue

            # UFUNCTION filter
            if has_ufunction is not None:
                if not self.is_enriched:
                    continue
                if meta.get('has_ufunction', False) != has_ufunction:
                    continue

            # USTRUCT filter
            if has_ustruct is not None:
                if not self.is_enriched:
                    continue
                if meta.get('has_ustruct', False) != has_ustruct:
                    continue

            # File type filter
            if file_type is not None:
                if not self.is_enriched:
                    continue
                if file_type == 'header' and not meta.get('is_header', False):
                    continue
                if file_type == 'implementation' and not meta.get('is_implementation', False):
                    continue

            valid_indices.append(i)

        return valid_indices

    def _apply_boosting(
        self,
        scores: np.ndarray,
        boost_entities: Optional[List[str]],
        boost_macros: bool
    ) -> np.ndarray:
        """Apply relevance boosting to scores"""
        if not self.is_enriched:
            return scores

        boosted_scores = scores.copy()

        for i, meta in enumerate(self.metadata):
            boost_factor = 1.0

            # Boost if contains target entities
            if boost_entities:
                entities = meta.get('entities', [])
                if any(e in entities for e in boost_entities):
                    boost_factor *= 1.2  # 20% boost

            # Boost if has UE5 macros
            if boost_macros:
                has_any_macro = (
                    meta.get('has_uproperty', False) or
                    meta.get('has_ufunction', False) or
                    meta.get('has_uclass', False) or
                    meta.get('has_ustruct', False)
                )
                if has_any_macro:
                    boost_factor *= 1.15  # 15% boost

            boosted_scores[i] *= boost_factor

        return boosted_scores

    def _apply_logical_boosts(
        self,
        scores: np.ndarray,
        boost_entities: Optional[List[str]],
        query_type: Optional[str]
    ) -> np.ndarray:
        """
        Apply logical/structural boosts to compensate for poor embedding model.

        Uses file paths, header/impl distinction, and entity co-occurrence
        to improve ranking without relying on semantic similarity.

        Boosts:
        1. File Path Matching: 3x if entity name appears in filename
        2. Header Prioritization: 2.5x for .h files on definition queries
        3. Entity Co-occurrence: 0.1x penalty if target entity not present
        4. Multi-entity bonus: 1.3x for chunks with >3 entities (rich definitions)
        """
        if not self.is_enriched or not boost_entities:
            return scores

        boosted_scores = scores.copy()

        for i, meta in enumerate(self.metadata):
            boost_factor = 1.0

            # 1. File Path Matching (3x boost)
            for entity in boost_entities:
                # Strip UE5 prefixes (F, U, A, E) to get base name
                entity_base = entity.lstrip('FUAE')
                path_lower = Path(meta['path']).name.lower()
                if entity_base.lower() in path_lower:
                    boost_factor *= 3.0
                    break

            # 2. Header Prioritization (for definition queries)
            if query_type in ['definition', 'hybrid']:
                if meta.get('is_header', False):
                    boost_factor *= 2.5  # Headers contain definitions
                elif meta.get('is_implementation', False):
                    boost_factor *= 0.5  # Implementation less relevant for defs

            # 3. Entity Co-occurrence (require entity presence)
            entities = meta.get('entities', [])
            has_target_entity = any(e in entities for e in boost_entities)
            if not has_target_entity:
                boost_factor *= 0.1  # Heavy penalty for missing target entity

            # 4. Multi-entity bonus (rich definition area)
            if len(entities) > 3:
                boost_factor *= 1.3

            boosted_scores[i] *= boost_factor

        return boosted_scores


def main():
    """Example usage"""
    import json
    from sentence_transformers import SentenceTransformer

    TOOL_ROOT = Path(__file__).parent.parent.parent

    # Load data (requires enriched metadata)
    vectors_path = TOOL_ROOT / "data" / "vector_store.npz"
    meta_path = TOOL_ROOT / "data" / "vector_meta_enriched.json"

    if not meta_path.exists():
        print(f"Enriched metadata not found at: {meta_path}")
        print("Run: python src/indexing/metadata_enricher.py data/vector_meta.json")
        return

    embeddings = np.load(vectors_path, mmap_mode="r", allow_pickle=False)["embeddings"]
    metadata = json.loads(meta_path.read_text())['items']

    # Create filtered search
    search = FilteredSearch(embeddings, metadata)

    # Encode query
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    query = "collision detection members"
    qvec = model.encode([query], normalize_embeddings=True)[0]

    # Search with filters
    print("=== Filtered Search Examples ===\n")

    # Example 1: Find chunks with FHitResult
    print("1. Chunks containing FHitResult:")
    results = search.search(qvec, top_k=3, entity="FHitResult")
    for r in results:
        print(f"  {Path(r['path']).name} | entities: {r.get('entities', [])}")

    # Example 2: Find struct definitions with UPROPERTY
    print("\n2. Struct chunks with UPROPERTY:")
    results = search.search(qvec, top_k=3, entity_type="struct", has_uproperty=True)
    for r in results:
        print(f"  {Path(r['path']).name} | types: {r.get('entity_types', [])}")

    # Example 3: Boost chunks with entities
    print("\n3. Search with entity boosting:")
    results = search.search(qvec, top_k=3, boost_entities=["FHitResult", "FVector"])
    for r in results:
        print(f"  {Path(r['path']).name} | score: {r['score']:.3f} | entities: {r.get('entities', [])}")


if __name__ == "__main__":
    main()