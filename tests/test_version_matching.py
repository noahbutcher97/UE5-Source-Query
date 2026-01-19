"""
Test version matching logic

Ensures 5.3, 5.3.0, and 5.3.2 are all treated as compatible versions.
"""

import unittest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ue5_query.utils.environment_detector import ValidationPipeline


class TestVersionMatching(unittest.TestCase):
    """Test version normalization and matching"""

    def setUp(self):
        self.validator = ValidationPipeline()

    def test_normalize_version_full(self):
        """Test normalizing full version strings"""
        self.assertEqual(self.validator._normalize_version("5.3.2"), (5, 3, 2))
        self.assertEqual(self.validator._normalize_version("5.4.0"), (5, 4, 0))
        self.assertEqual(self.validator._normalize_version("4.27.2"), (4, 27, 2))

    def test_normalize_version_partial(self):
        """Test normalizing partial version strings"""
        # Should pad with zeros
        self.assertEqual(self.validator._normalize_version("5.3"), (5, 3, 0))
        self.assertEqual(self.validator._normalize_version("5"), (5, 0, 0))

    def test_normalize_version_invalid(self):
        """Test normalizing invalid version strings"""
        # Should handle gracefully
        self.assertEqual(self.validator._normalize_version("invalid"), (0, 0, 0))
        self.assertEqual(self.validator._normalize_version(""), (0, 0, 0))

    def test_versions_match_identical(self):
        """Test matching identical versions"""
        self.assertTrue(self.validator._versions_match("5.3.2", "5.3.2"))
        self.assertTrue(self.validator._versions_match("5.3", "5.3"))

    def test_versions_match_patch_difference(self):
        """Test matching versions with different patches (should match)"""
        # These should all match because major.minor are the same
        self.assertTrue(self.validator._versions_match("5.3", "5.3.0"))
        self.assertTrue(self.validator._versions_match("5.3", "5.3.2"))
        self.assertTrue(self.validator._versions_match("5.3.2", "5.3"))
        self.assertTrue(self.validator._versions_match("5.3.0", "5.3.2"))

    def test_versions_dont_match_minor(self):
        """Test that different minor versions don't match"""
        self.assertFalse(self.validator._versions_match("5.3", "5.4"))
        self.assertFalse(self.validator._versions_match("5.3.2", "5.4.0"))
        self.assertFalse(self.validator._versions_match("4.27", "5.3"))

    def test_versions_dont_match_major(self):
        """Test that different major versions don't match"""
        self.assertFalse(self.validator._versions_match("4.27", "5.27"))
        self.assertFalse(self.validator._versions_match("5.3", "4.3"))


class TestVersionDisplay(unittest.TestCase):
    """Test that version display works correctly"""

    def test_truncated_versions_acceptable(self):
        """Test that truncated versions (5.3 instead of 5.3.2) are acceptable"""
        validator = ValidationPipeline()

        # User sees "5.3" but actual version is "5.3.2"
        # This should NOT trigger a warning
        self.assertTrue(validator._versions_match("5.3", "5.3.2"))


def run_tests():
    """Run all version matching tests"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
