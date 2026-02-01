import unittest
from unittest.mock import MagicMock, patch
from ue5_query.ai.service import IntelligenceService

class TestIntelligenceService(unittest.TestCase):
    def setUp(self):
        self.mock_config = MagicMock()
        self.mock_config.get.return_value = "dummy_key"

    @patch('ue5_query.ai.service.Anthropic')
    def test_initialization_success(self, MockAnthropic):
        service = IntelligenceService(self.mock_config)
        self.assertTrue(service.is_available())
        MockAnthropic.assert_called_once()

    @patch('ue5_query.ai.service.Anthropic')
    def test_initialization_failure(self, MockAnthropic):
        # Simulate import error or init error
        MockAnthropic.side_effect = Exception("API Error")
        
        service = IntelligenceService(self.mock_config)
        self.assertFalse(service.is_available())

    def test_missing_key(self):
        self.mock_config.get.return_value = ""
        service = IntelligenceService(self.mock_config)
        self.assertFalse(service.is_available())

if __name__ == '__main__':
    unittest.main()