import unittest
import json
from pathlib import Path

class TestDeploymentConfig(unittest.TestCase):
    def setUp(self):
        self.config_path = Path(__file__).parent.parent / "config" / "deployment_rules.json"

    def test_config_exists(self):
        """Verify that deployment_rules.json exists"""
        self.assertTrue(self.config_path.exists(), f"Config file missing at {self.config_path}")

    def test_config_is_valid_json(self):
        """Verify that the config file is valid JSON and contains required keys"""
        with open(self.config_path, "r") as f:
            rules = json.load(f)
            
        self.assertIn("default_excludes", rules)
        self.assertIn("deployment_excludes", rules)
        
        # Verify they are lists
        self.assertIsInstance(rules["default_excludes"], list)
        self.assertIsInstance(rules["deployment_excludes"], list)
        
        # Verify they are not empty
        self.assertGreater(len(rules["default_excludes"]), 0)
        self.assertGreater(len(rules["deployment_excludes"]), 0)

    def test_update_manager_loads_config(self):
        """Verify that UpdateManager can load these rules (Integration check)"""
        try:
            import sys
            # Add project root to path
            root_dir = Path(__file__).parent.parent
            sys.path.insert(0, str(root_dir))
            
            from tools.update import DEFAULT_EXCLUDES, DEPLOYMENT_EXCLUDES
            
            # Load the rules manually to compare
            with open(self.config_path, "r") as f:
                rules = json.load(f)
            
            # The globals in update.py should match the file content
            # (Note: This assumes the test runs in an environment where update.py successfully loaded the file)
            self.assertEqual(DEFAULT_EXCLUDES, rules["default_excludes"])
            self.assertEqual(DEPLOYMENT_EXCLUDES, rules["deployment_excludes"])
        except ImportError:
            self.skipTest("Update tool not found or imports failed")

if __name__ == '__main__':
    unittest.main()
