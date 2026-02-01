"""
Unit tests for universal import system.

Tests that all modules can be imported correctly in both:
- Development environment (running from project root)
- Distributed environment (running from Scripts/ subdirectory)
"""

import sys
import os
import subprocess
import tempfile
import shutil
from pathlib import Path
import unittest

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "ue5_query"


class TestUniversalImports(unittest.TestCase):
    """Test universal imports work in dev environment"""

    def setUp(self):
        """Ensure project root is in path for dev testing"""
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))

    def test_config_manager_import_dev(self):
        """Test config_manager imports in dev environment"""
        try:
            from ue5_query.utils.config_manager import ConfigManager
            self.assertTrue(True, "Successfully imported ConfigManager with absolute path")
        except ImportError as e:
            self.fail(f"Failed to import ConfigManager in dev environment: {e}")

    def test_source_manager_import_dev(self):
        """Test source_manager imports in dev environment"""
        try:
            from ue5_query.utils.source_manager import SourceManager
            self.assertTrue(True, "Successfully imported SourceManager with absolute path")
        except ImportError as e:
            self.fail(f"Failed to import SourceManager in dev environment: {e}")

    def test_hybrid_query_import_dev(self):
        """Test hybrid_query imports in dev environment"""
        try:
            from ue5_query.core.hybrid_query import HybridQueryEngine
            self.assertTrue(True, "Successfully imported HybridQueryEngine with absolute path")
        except ImportError as e:
            self.fail(f"Failed to import HybridQueryEngine in dev environment: {e}")

    def test_gui_dashboard_import_dev(self):
        """Test gui_dashboard imports in dev environment"""
        try:
            from ue5_query.management.gui_dashboard import UnifiedDashboard
            self.assertTrue(True, "Successfully imported UnifiedDashboard")
        except ImportError as e:
            self.fail(f"Failed to import UnifiedDashboard in dev environment: {e}")

    def test_build_embeddings_import_dev(self):
        """Test build_embeddings can import semantic_chunker"""
        # Simulate the conditional import in build_embeddings.py
        try:
            from ue5_query.utils.semantic_chunker import SemanticChunker
            self.assertTrue(True, "Successfully imported SemanticChunker")
        except ImportError:
            try:
                from ue5_query.utils.semantic_chunker import SemanticChunker
                self.assertTrue(True, "Successfully imported SemanticChunker with fallback")
            except ImportError as e:
                self.fail(f"Failed to import SemanticChunker in dev environment: {e}")


class TestDistributedEnvironment(unittest.TestCase):
    """Test imports work when simulating distributed package structure"""

    @classmethod
    def setUpClass(cls):
        """Create a temporary distribution structure"""
        cls.temp_dir = Path(tempfile.mkdtemp())
        cls.dist_scripts = cls.temp_dir / "Scripts"
        cls.dist_src = cls.dist_scripts / "ue5_query"

        # Copy source files to simulate distribution
        shutil.copytree(SRC_DIR, cls.dist_src)

        # Copy any necessary config files
        if (PROJECT_ROOT / "config").exists():
            shutil.copytree(PROJECT_ROOT / "config", cls.dist_scripts / "config")

        # Create empty data directory
        (cls.dist_scripts / "data").mkdir(exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        """Clean up temporary directory"""
        if cls.temp_dir.exists():
            shutil.rmtree(cls.temp_dir)

    def test_hybrid_query_in_dist(self):
        """Test hybrid_query works in distributed environment"""
        script = f"""
import sys
from pathlib import Path

# Simulate distributed environment
TOOL_ROOT = Path(r'{self.dist_scripts}')
sys.path.insert(0, str(TOOL_ROOT))

try:
    from ue5_query.core.hybrid_query import HybridQueryEngine
    print("SUCCESS: HybridQueryEngine imported")
except ImportError as e:
    print(f"FAIL: {{e}}")
    sys.exit(1)
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True
        )
        self.assertIn("SUCCESS", result.stdout, f"Failed in dist env: {result.stderr}")

    def test_config_manager_in_dist(self):
        """Test config_manager works in distributed environment"""
        script = f"""
import sys
from pathlib import Path

TOOL_ROOT = Path(r'{self.dist_scripts}')
sys.path.insert(0, str(TOOL_ROOT))

try:
    from ue5_query.utils.config_manager import ConfigManager
    print("SUCCESS: ConfigManager imported")
except ImportError as e:
    print(f"FAIL: {{e}}")
    sys.exit(1)
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True
        )
        self.assertIn("SUCCESS", result.stdout, f"Failed in dist env: {result.stderr}")

    def test_source_manager_in_dist(self):
        """Test source_manager works in distributed environment"""
        script = f"""
import sys
from pathlib import Path

TOOL_ROOT = Path(r'{self.dist_scripts}')
sys.path.insert(0, str(TOOL_ROOT))

try:
    from ue5_query.utils.source_manager import SourceManager
    print("SUCCESS: SourceManager imported")
except ImportError as e:
    print(f"FAIL: {{e}}")
    sys.exit(1)
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True
        )
        self.assertIn("SUCCESS", result.stdout, f"Failed in dist env: {result.stderr}")

    def test_gui_dashboard_in_dist(self):
        """Test gui_dashboard works in distributed environment"""
        script = f"""
import sys
from pathlib import Path

TOOL_ROOT = Path(r'{self.dist_scripts}')
sys.path.insert(0, str(TOOL_ROOT))

try:
    from ue5_query.management.gui_dashboard import UnifiedDashboard
    print("SUCCESS: UnifiedDashboard imported")
except ImportError as e:
    print(f"FAIL: {{e}}")
    sys.exit(1)
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True
        )
        self.assertIn("SUCCESS", result.stdout, f"Failed in dist env: {result.stderr}")


class TestImportHelper(unittest.TestCase):
    """Test the import_helper utility module"""

    def setUp(self):
        """Ensure project root is in path"""
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))

    def test_is_dev_environment(self):
        """Test environment detection"""
        from ue5_query.utils.import_helper import is_dev_environment, get_import_context

        # Should detect dev environment when run from project root
        is_dev = is_dev_environment()
        context = get_import_context()

        # In our test environment, we have .git and project structure
        self.assertTrue(is_dev, "Should detect dev environment in project root")
        self.assertEqual(context, 'dev', "Should return 'dev' context")

    def test_universal_import_module(self):
        """Test universal_import function"""
        from ue5_query.utils.import_helper import universal_import

        # Test importing entire module
        config_manager = universal_import('utils.config_manager')
        self.assertTrue(hasattr(config_manager, 'ConfigManager'), "Should import module")

    def test_universal_import_names(self):
        """Test universal_import with specific names"""
        from ue5_query.utils.import_helper import universal_import

        # Test importing specific names
        imports = universal_import('utils.config_manager', ['ConfigManager'])
        self.assertIn('ConfigManager', imports, "Should import specific names")
        self.assertTrue(callable(imports['ConfigManager']), "Should be a class")

    def test_try_import_single(self):
        """Test try_import with single name"""
        from ue5_query.utils.import_helper import try_import

        ConfigManager = try_import(
            'src.utils.config_manager',
            'utils.config_manager',
            ['ConfigManager']
        )
        self.assertTrue(callable(ConfigManager), "Should return single class")

    def test_try_import_multiple(self):
        """Test try_import with multiple names"""
        from ue5_query.utils.import_helper import try_import

        # Import from query_intent (has multiple classes/enums)
        imports = try_import(
            'src.core.query_intent',
            'core.query_intent',
            ['QueryType', 'EntityType']
        )
        self.assertEqual(len(imports), 2, "Should return tuple of classes")
        # Check they're the right types
        self.assertTrue(hasattr(imports[0], 'DEFINITION'), "Should be QueryType enum")
        self.assertTrue(hasattr(imports[1], 'STRUCT'), "Should be EntityType enum")


class TestIntegration(unittest.TestCase):
    """Integration tests for complete workflows"""

    def setUp(self):
        """Ensure project root is in path"""
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))

    def test_config_manager_instantiation(self):
        """Test ConfigManager can be instantiated and used"""
        from ue5_query.utils.config_manager import ConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            cm = ConfigManager(Path(tmpdir))
            # Should create with defaults
            self.assertIsNotNone(cm)
            # Should have get method
            self.assertTrue(hasattr(cm, 'get'))

    def test_source_manager_instantiation(self):
        """Test SourceManager can be instantiated and used"""
        from ue5_query.utils.source_manager import SourceManager

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SourceManager(Path(tmpdir))
            # Should create with defaults
            self.assertIsNotNone(sm)
            # Should have methods
            self.assertTrue(hasattr(sm, 'get_engine_dirs'))

    def test_hybrid_query_engine_instantiation(self):
        """Test HybridQueryEngine can be instantiated"""
        # This requires vector store, so just test import and class structure
        from ue5_query.core.hybrid_query import HybridQueryEngine

        self.assertTrue(callable(HybridQueryEngine))
        self.assertTrue(hasattr(HybridQueryEngine, 'query'))


def run_tests():
    """Run all tests and print results"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestUniversalImports))
    suite.addTests(loader.loadTestsFromTestCase(TestDistributedEnvironment))
    suite.addTests(loader.loadTestsFromTestCase(TestImportHelper))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
