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

    # --- New Tests Implemented Below ---

    def test_default_semantic_fallback(self):
        """Test queries that mention an entity but aren't defs or conceptual"""
        # "FVector math calculation" -> Semantic search with entity enhancement
        # It's not a definition query, not purely conceptual (no "how", "why"), but has an entity.
        intent = self.analyzer.analyze("FVector math calculation")
        self.assertEqual(intent.query_type, QueryType.SEMANTIC)
        self.assertEqual(intent.confidence, 0.5)
        # Should still get basic struct keywords in enhancement
        self.assertIn("struct", intent.enhanced_query)

    def test_enhance_query_variations(self):
        """Test query enhancement for different entity types and context"""
        # Class methods
        # "AActor methods" -> Hybrid or Definition?
        # "methods" is in DEFINITION_KEYWORDS, so it triggers Hybrid path
        intent = self.analyzer.analyze("AActor methods")
        self.assertEqual(intent.query_type, QueryType.HYBRID)
        self.assertIn("UFUNCTION", intent.enhanced_query)

        # Enum values
        # "list ECollisionChannel values please" -> Semantic (values not in DEF_KEYWORDS, long enough query)
        intent = self.analyzer.analyze("list ECollisionChannel values please")
        self.assertEqual(intent.query_type, QueryType.SEMANTIC) 
        self.assertIn("UENUM", intent.enhanced_query)
        self.assertIn("values", intent.enhanced_query)

        # Function parameters
        # "LineTraceSingleByChannel parameters" -> Hybrid (parameters is in DEFINITION_KEYWORDS)
        intent = self.analyzer.analyze("LineTraceSingleByChannel parameters")
        self.assertEqual(intent.query_type, QueryType.HYBRID)
        self.assertIn("UFUNCTION", intent.enhanced_query)
        
    def test_pattern_variations(self):
        """Test various definition pattern permutations"""
        variations = [
            ("what is FHitResult", EntityType.STRUCT, "FHitResult"),
            ("define AActor", EntityType.CLASS, "AActor"),
            ("find ECollisionChannel", EntityType.ENUM, "ECollisionChannel"),
            ("show me FVector", EntityType.STRUCT, "FVector"),
        ]
        for q, expected_type, expected_name in variations:
            intent = self.analyzer.analyze(q)
            self.assertEqual(intent.query_type, QueryType.DEFINITION, f"Failed for '{q}'")
            self.assertEqual(intent.entity_type, expected_type)
            self.assertEqual(intent.entity_name, expected_name)

    def test_case_sensitivity(self):
        """Test case insensitivity for keywords"""
        intent = self.analyzer.analyze("STRUCT FHitResult")
        self.assertEqual(intent.query_type, QueryType.DEFINITION)
        
        intent = self.analyzer.analyze("struct FHitResult")
        self.assertEqual(intent.query_type, QueryType.DEFINITION)

    def test_bare_entity_edge_cases(self):
        """Test bare entity logic with too many words"""
        # "The FVector usage is amazing" -> >2 significant words
        # Changed from "FVector struct" to avoid regex match
        q = "The FVector usage is amazing"
        intent = self.analyzer.analyze(q)
        # Should NOT be bare definition (0.85 conf)
        self.assertNotEqual(intent.confidence, 0.85, "Should not trigger bare entity definition")
        self.assertEqual(intent.query_type, QueryType.SEMANTIC)

    def test_empty_input(self):
        """Test empty or whitespace input"""
        intent = self.analyzer.analyze("")
        # Should return default semantic with low confidence
        self.assertEqual(intent.query_type, QueryType.SEMANTIC)
        
        intent = self.analyzer.analyze("   ")
        self.assertEqual(intent.query_type, QueryType.SEMANTIC)

if __name__ == '__main__':
    unittest.main()