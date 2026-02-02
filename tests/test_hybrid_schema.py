
import unittest
from pathlib import Path
from typing import Dict, Any
from ue5_query.core.hybrid_query import HybridQueryEngine
from ue5_query.core.types import QueryResult, SemanticResultDict
from ue5_query.core.query_intent import QueryIntentAnalyzer, QueryIntent, QueryType, EntityType

# Mock ConfigManager
class MockConfigManager:
    def get(self, key, default=None):
        return default

class TestHybridSchema(unittest.TestCase):
    def setUp(self):
        # Setup mock data for HybridQueryEngine
        self.mock_meta = [
            {
                'path': 'Engine/Source/Runtime/Core/Public/Math/Vector.h', 
                'origin': 'engine', 
                'chunk_index': 0, 
                'total_chunks': 1,
                'entities': ['FVector'],
                'entity_types': ['struct']
            },
            {
                'path': 'Games/MyGame/Source/MyGame/MyActor.cpp', 
                'origin': 'project', 
                'chunk_index': 0, 
                'total_chunks': 1,
                'entities': ['AMyActor'],
                'entity_types': ['class']
            }
        ]
        # Mock embeddings (dummy array)
        import numpy as np
        self.mock_embeddings = np.zeros((2, 768))
        
        # Instantiate engine without loading real model/data
        self.engine = HybridQueryEngine(
            Path('.'), 
            embeddings=self.mock_embeddings, 
            metadata=self.mock_meta,
            config_manager=MockConfigManager()
        )
        
        # Mock the model to avoid loading
        class MockModel:
            def encode(self, texts, **kwargs):
                return np.zeros((len(texts), 768))
        self.engine.model = MockModel()

    def test_return_type_schema(self):
        """Verify query returns correct TypedDict structure"""
        result = self.engine.query("FVector", top_k=1)
        
        # Check top-level keys
        expected_keys = QueryResult.__annotations__.keys()
        self.assertTrue(all(k in result for k in expected_keys), f"Missing keys in result: {result.keys()}")
        
        # Check intent keys
        expected_intent_keys = {'type', 'entity_type', 'entity_name', 'confidence', 'reasoning', 'enhanced_query', 'scope', 'expanded_terms', 'is_file_search'}
        self.assertTrue(all(k in result['intent'] for k in expected_intent_keys), f"Missing keys in intent: {result['intent'].keys()}")
        
        # Check is_file_search boolean
        self.assertIsInstance(result['intent']['is_file_search'], bool)

    def test_semantic_result_schema(self):
        """Verify semantic search results match TypedDict"""
        # Force a semantic search
        result = self.engine.query("concept of vectors", top_k=1)
        sem_results = result['semantic_results']
        
        if sem_results:
            item = sem_results[0]
            # Verify keys match SemanticResultDict
            expected_keys = SemanticResultDict.__annotations__.keys()
            # Note: TypedDict keys are checked at runtime here
            for k in expected_keys:
                self.assertIn(k, item, f"Missing key {k} in semantic result")

    def test_empty_query_guard(self):
        """Test graceful handling of empty queries"""
        empty_res = self.engine.query("")
        self.assertEqual(empty_res['intent']['type'], 'unknown')
        self.assertEqual(len(empty_res['combined_results']), 0)
        
        none_res = self.engine.query(None) # type: ignore
        self.assertEqual(none_res['intent']['type'], 'unknown')

    def test_path_normalization_cache(self):
        """Verify paths are normalized in cache"""
        # Check cache populated in __init__
        self.assertIn('all', self.engine._scope_cache)
        self.assertIn('engine', self.engine._scope_cache)
        
        # Check normalization
        cached_files = self.engine._scope_cache['engine']
        self.assertTrue(len(cached_files) > 0)
        
        # Check that meta was updated with path_norm
        self.assertIn('path_norm', self.engine.meta[0])

if __name__ == '__main__':
    unittest.main()
