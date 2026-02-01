import unittest
from unittest.mock import MagicMock
from ue5_query.ai.context_builder import ContextBuilder

class TestContextBuilder(unittest.TestCase):
    def setUp(self):
        self.builder = ContextBuilder(max_chars=1000)

    def test_build_context_definitions(self):
        results = {
            'definition_results': [
                {
                    'entity_name': 'FTestStruct',
                    'file_path': 'Test.h',
                    'definition': 'struct FTestStruct { int A; };'
                }
            ],
            'semantic_results': []
        }
        
        context = self.builder.build_context(results)
        
        self.assertIn('<context>', context)
        self.assertIn('<definition name="FTestStruct"', context)
        self.assertIn('struct FTestStruct { int A; };', context)

    def test_truncation(self):
        # Create a builder with very small limit
        small_builder = ContextBuilder(max_chars=50)
        
        results = {
            'definition_results': [
                {
                    'entity_name': 'FLargeStruct',
                    'file_path': 'Large.h',
                    'definition': 'A' * 100
                }
            ]
        }
        
        context = small_builder.build_context(results)
        # Should contain context tag but might skip the entry if it's too big alone
        # Or checking logic: current_chars + len(entry) > max_chars
        # Entry length is approx 100+. Max is 50.
        # So it should result in empty context content.
        
        self.assertIn('<context>', context)
        self.assertNotIn('FLargeStruct', context)

    def test_format_system_prompt(self):
        base = "You are AI."
        context = "<context>...</context>"
        prompt = self.builder.format_system_prompt(base, context)
        
        self.assertIn(base, prompt)
        self.assertIn(context, prompt)
        self.assertIn("access to the following relevant UE5 source code", prompt)

if __name__ == '__main__':
    unittest.main()