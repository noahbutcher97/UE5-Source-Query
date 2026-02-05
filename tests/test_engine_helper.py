"""
Integration tests for engine_helper.py

Tests the integration between engine_helper and environment_detector.
"""

import unittest
import tempfile
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ue5_query.utils.engine_helper import get_available_engines, resolve_uproject_source


class TestGetAvailableEngines(unittest.TestCase):
    """Test get_available_engines integration"""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.script_dir = self.temp_dir

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('ue5_query.utils.engine_helper.get_detector')
    def test_returns_dict_format(self, mock_get_detector):
        """Test that get_available_engines returns proper dict format"""
        # Mock detector
        mock_detector = MagicMock()
        mock_installation = MagicMock()
        mock_installation.to_dict.return_value = {
            "version": "5.3",
            "engine_root": "/path/Engine",
            "path": "/path",
            "source": "env_var",
            "validated": True,
            "health_score": 1.0,
            "issues": [],
            "warnings": []
        }
        mock_detector.detect_engines.return_value = [mock_installation]
        mock_get_detector.return_value = mock_detector

        result = get_available_engines(self.script_dir)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIn("version", result[0])
        self.assertIn("engine_root", result[0])
        self.assertIn("source", result[0])
        self.assertIn("health_score", result[0])

    @patch('ue5_query.utils.engine_helper.get_detector')
    def test_uses_cache_by_default(self, mock_get_detector):
        """Test that cache is used by default"""
        mock_detector = MagicMock()
        mock_detector.detect_engines.return_value = []
        mock_get_detector.return_value = mock_detector

        get_available_engines(self.script_dir)

        # Verify detect_engines was called with use_cache=True
        mock_detector.detect_engines.assert_called_once()
        call_args = mock_detector.detect_engines.call_args
        self.assertTrue(call_args.kwargs.get('use_cache', True))

    @patch('ue5_query.utils.engine_helper.get_detector')
    def test_can_disable_cache(self, mock_get_detector):
        """Test that cache can be disabled"""
        mock_detector = MagicMock()
        mock_detector.detect_engines.return_value = []
        mock_get_detector.return_value = mock_detector

        get_available_engines(self.script_dir, use_cache=False)

        call_args = mock_detector.detect_engines.call_args
        self.assertFalse(call_args.kwargs.get('use_cache'))

    @patch('ue5_query.utils.engine_helper.get_detector')
    def test_handles_detection_failure(self, mock_get_detector):
        """Test graceful handling of detection failure"""
        mock_get_detector.side_effect = Exception("Detection failed")

        # Should raise exception with helpful message
        with self.assertRaises(Exception) as context:
            get_available_engines(self.script_dir)

        self.assertIn("Detection failed", str(context.exception))


class TestResolveUprojectSource(unittest.TestCase):
    """Test resolve_uproject_source function"""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_resolves_existing_source_directory(self):
        """Test resolving existing Source directory"""
        uproject = self.temp_dir / "MyProject.uproject"
        source_dir = self.temp_dir / "Source"

        uproject.touch()
        source_dir.mkdir()

        result = resolve_uproject_source(str(uproject))

        self.assertEqual(result, str(source_dir))

    def test_returns_none_for_missing_source(self):
        """Test returns None when Source directory doesn't exist"""
        uproject = self.temp_dir / "MyProject.uproject"
        uproject.touch()

        result = resolve_uproject_source(str(uproject))

        self.assertIsNone(result)

    def test_returns_none_for_missing_uproject(self):
        """Test returns None when .uproject doesn't exist"""
        uproject = self.temp_dir / "NonExistent.uproject"

        result = resolve_uproject_source(str(uproject))

        self.assertIsNone(result)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
