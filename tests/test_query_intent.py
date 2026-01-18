import sys
import unittest
from pathlib import Path

# Add src to path to allow imports without package installation
TOOL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(TOOL_ROOT / "src"))

from core.query_intent import QueryIntentAnalyzer, QueryType, EntityType

class TestQueryIntentAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = QueryIntentAnalyzer()

    def test_definition_struct(self):
        """Test explicit struct definition queries"""
        queries = [
            "struct FHitResult",
            "FHitResult struct",
            "definition of FHitResult",
            "define FHitResult"
        ]
        for q in queries:
            intent = self.analyzer.analyze(q)
            self.assertEqual(intent.query_type, QueryType.DEFINITION, f"Failed for '{q}'")
            self.assertEqual(intent.entity_type, EntityType.STRUCT)
            self.assertEqual(intent.entity_name, "FHitResult")

    def test_definition_class(self):
        """Test explicit class definition queries"""
        queries = [
            "class AActor",
            "AActor class",
            "show me AActor"
        ]
        for q in queries:
            intent = self.analyzer.analyze(q)
            self.assertEqual(intent.query_type, QueryType.DEFINITION, f"Failed for '{q}'")
            self.assertEqual(intent.entity_type, EntityType.CLASS)
            self.assertEqual(intent.entity_name, "AActor")

    def test_bare_entity_lookup(self):
        """Test bare entity name lookups"""
        # "FVector" -> struct FVector
        intent = self.analyzer.analyze("FVector")
        self.assertEqual(intent.query_type, QueryType.DEFINITION)
        self.assertEqual(intent.entity_type, EntityType.STRUCT)
        self.assertEqual(intent.entity_name, "FVector")

        # "AActor" -> class AActor
        intent = self.analyzer.analyze("AActor")
        self.assertEqual(intent.query_type, QueryType.DEFINITION)
        self.assertEqual(intent.entity_type, EntityType.CLASS)
        self.assertEqual(intent.entity_name, "AActor")

    def test_semantic_query(self):
        """Test conceptual/semantic queries"""
        queries = [
            "how does garbage collection work",
            "explain replication",
            "best practices for networking"
        ]
        for q in queries:
            intent = self.analyzer.analyze(q)
            self.assertEqual(intent.query_type, QueryType.SEMANTIC, f"Failed for '{q}'")

    def test_hybrid_query(self):
        """Test queries that mix entity definition with semantic questions"""
        # "FHitResult members" -> definition/hybrid
        # The analyzer logic: "entity_candidates and has_definition_hints and not is_conceptual" -> HYBRID
        q = "FHitResult members"
        intent = self.analyzer.analyze(q)
        self.assertEqual(intent.query_type, QueryType.HYBRID)
        self.assertEqual(intent.entity_name, "FHitResult")
        self.assertIn("members", intent.enhanced_query)

    def test_function_detection(self):
        """Test function queries"""
        q = "LineTraceSingleByChannel function"
        intent = self.analyzer.analyze(q)
        self.assertEqual(intent.query_type, QueryType.DEFINITION)
        self.assertEqual(intent.entity_type, EntityType.FUNCTION)
        self.assertEqual(intent.entity_name, "LineTraceSingleByChannel")

if __name__ == '__main__':
    unittest.main()
