"""
Re-ranking engine using Cross-Encoders.
Improves search precision by re-scoring top vector candidates against the query.
"""
import time
from typing import List, Dict, Any, Optional
from sentence_transformers import CrossEncoder
import numpy as np

try:
    from ue5_query.utils.logger import get_project_logger
except ImportError:
    import logging
    get_project_logger = logging.getLogger

logger = get_project_logger(__name__)

class SearchReranker:
    """
    Re-ranks search results using a Cross-Encoder model.
    Cross-Encoders are slower but much more precise than Bi-Encoders (vectors).
    """
    
    # Fast, high-quality model for re-ranking
    # ~25ms per doc on CPU
    DEFAULT_MODEL = "cross-encoder/ms-marco-TinyBERT-L-2-v2"

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self._model = None
        self._is_loading = False

    def _load_model(self):
        """Lazy load the model"""
        if self._model is None and not self._is_loading:
            self._is_loading = True
            logger.info(f"Loading CrossEncoder: {self.model_name}")
            try:
                self._model = CrossEncoder(self.model_name)
            except Exception as e:
                logger.error(f"Failed to load CrossEncoder: {e}")
                raise
            finally:
                self._is_loading = False

    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Re-rank a list of candidate results.
        
        Args:
            query: User query string
            candidates: List of result dicts. MUST contain 'text' or 'definition' or be able to load it.
                        If 'text' is missing, it will rely on metadata string representation.
            top_k: Number of results to return
            
        Returns:
            Re-ranked top_k results
        """
        if not candidates:
            return []
            
        self._load_model()
        if not self._model:
            return candidates[:top_k]

        # Prepare pairs for model
        # [ [query, doc1], [query, doc2], ... ]
        pairs = []
        for c in candidates:
            # Determine document text
            # 1. Use explicit text if available (from snippet extraction)
            doc_text = c.get('text_snippet')
            
            # 2. Use definition if available
            if not doc_text:
                doc_text = c.get('definition')
                
            # 3. Fallback: Construct synthetic text from metadata
            if not doc_text:
                entities = " ".join(c.get('entities', []))
                path = c.get('path', '')
                doc_text = f"{path} {entities}"
                
            pairs.append([query, doc_text])

        # Predict scores
        # Returns list of floats
        scores = self._model.predict(pairs)

        # Assign new scores and sort
        for i, candidate in enumerate(candidates):
            # Normalize cross-encoder score (logits) to be somewhat comparable?
            # Actually, just replace the score for ranking purposes
            # Store original score for debug
            candidate['vector_score'] = candidate.get('score', 0)
            candidate['rerank_score'] = float(scores[i])
            candidate['score'] = float(scores[i]) # Update main score for sorting

        # Sort descending
        reranked = sorted(candidates, key=lambda x: x['score'], reverse=True)
        
        return reranked[:top_k]
