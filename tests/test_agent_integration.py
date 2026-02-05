import unittest
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from ue5_query.core.output_formatter import OutputFormatter, OutputFormat

# Mock data structures to simulate engine results
@dataclass
class MockDefResult:
    # Use dict-like behavior for output formatter (which expects dicts or objects with attributes)
    # The current OutputFormatter implementation expects dictionaries for most fields, 
    # but the mock in output_formatter.py main() used a class.
    # Let's align with what OutputFormatter.format actually expects (dicts in the results list).
    pass

class TestAgentIntegration(unittest.TestCase):
    """
    Verifies that the system produces valid structured output (JSON, XML, Code)
    as expected by AI agents (Claude Code, Gemini CLI).
    """

    def setUp(self):
        # Create a mock query result that mimics HybridQueryEngine output
        self.mock_results = {
            "question": "FHitResult members",
            "intent": {
                "query_type": "hybrid",
                "confidence": 0.85,
                "entity_name": "FHitResult",
                "reasoning": "Test reasoning"
            },
            "definition_results": [
                {
                    "type": "definition",
                    "entity_type": "struct",
                    "entity_name": "FHitResult",
                    "file_path": "Engine/Source/Runtime/Engine/Classes/Engine/HitResult.h",
                    "line_start": 42,
                    "line_end": 150,
                    "match_quality": 1.0,
                    "definition": "struct FHitResult {\n    float Time;\n};",
                    "members": ["float Time"],
                    "origin": "engine"
                }
            ],
            "semantic_results": [
                {
                    "path": "Engine/Source/Runtime/Engine/Classes/Engine/HitResult.h",
                    "chunk_index": 2,
                    "total_chunks": 5,
                    "score": 0.95,
                    "origin": "engine",
                    "entities": ["FHitResult"]
                }
            ],
            "combined_results": [],
            "timing": {
                "total": 1.0
            }
        }

    def test_json_format_validity(self):
        """Ensure --format json produces valid JSON with required fields"""
        output = OutputFormatter.format(self.mock_results, OutputFormat.JSON)
        data = json.loads(output)
        
        self.assertIn("query", data)
        self.assertIn("results", data)
        self.assertEqual(data["query"]["question"], "FHitResult members")
        self.assertEqual(len(data["results"]["definitions"]), 1)
        self.assertEqual(data["results"]["definitions"][0]["entity_name"], "FHitResult")

    def test_jsonl_format_validity(self):
        """Ensure --format jsonl produces valid JSON lines"""
        output = OutputFormatter.format(self.mock_results, OutputFormat.JSONL)
        lines = output.strip().split('\n')
        
        # Should have at least metadata, defs, semantic, timing
        self.assertGreaterEqual(len(lines), 3)
        
        # Verify first line is metadata
        meta = json.loads(lines[0])
        self.assertEqual(meta["type"], "query_metadata")
        
        # Verify we find the definition
        def_found = False
        for line in lines:
            obj = json.loads(line)
            if obj.get("type") == "definition":
                self.assertEqual(obj["entity_name"], "FHitResult")
                def_found = True
        self.assertTrue(def_found)

    def test_xml_format_validity(self):
        """Ensure --format xml produces valid XML"""
        output = OutputFormatter.format(self.mock_results, OutputFormat.XML)
        
        try:
            root = ET.fromstring(output)
            self.assertEqual(root.tag, "query_result")
            self.assertIsNotNone(root.find("query/question"))
            self.assertIsNotNone(root.find("results/definitions/definition"))
        except ET.ParseError as e:
            self.fail(f"XML parsing failed: {e}")

    def test_code_format_content(self):
        """Ensure --format code returns clean code snippets"""
        output = OutputFormatter.format(self.mock_results, OutputFormat.CODE)
        
        self.assertIn("struct FHitResult", output)
        self.assertIn("// File: Engine/Source/Runtime/Engine/Classes/Engine/HitResult.h:42", output)
        # Should not contain JSON or Markdown markup
        self.assertNotIn("```", output)
        self.assertNotIn('{\"query\":', output)

    def test_no_code_flag(self):
        """Ensure --no-code (include_code=False) works for JSON"""
        # Testing via direct call since format arg controls include_code
        output = OutputFormatter.format(self.mock_results, OutputFormat.JSON, include_code=False)
        data = json.loads(output)
        
        def_res = data["results"]["definitions"][0]
        self.assertNotIn("definition", def_res)
        self.assertNotIn("members", def_res)

    def test_markdown_format(self):
        """Ensure --format markdown produces readable markdown"""
        output = OutputFormatter.format(self.mock_results, OutputFormat.MARKDOWN)
        self.assertIn("# Query: FHitResult members", output)
        self.assertIn("### 1. struct `FHitResult`", output)
        self.assertIn("```cpp", output)

if __name__ == '__main__':
    unittest.main()
