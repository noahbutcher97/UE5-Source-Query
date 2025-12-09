"""
GUI Smoke Tests

Tests that GUI applications can initialize without crashing.
Does NOT test full GUI functionality (that requires manual testing),
but verifies imports work and windows can be created.
"""

import unittest
import sys
import os
from pathlib import Path
import threading
import time
import tkinter as tk

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Suppress GUI windows during testing
os.environ['RUNNING_TESTS'] = '1'


class TestDeploymentWizardImports(unittest.TestCase):
    """Test that deployment wizard can be imported without errors"""

    def test_import_gui_deploy(self):
        """Test importing the deployment wizard module"""
        try:
            # This will fail if there are import errors
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "gui_deploy",
                Path(__file__).parent.parent / "installer" / "gui_deploy.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Verify the main class exists
            self.assertTrue(hasattr(module, 'DeploymentWizard'))
        except Exception as e:
            self.fail(f"Failed to import gui_deploy: {e}")

    def test_deployment_wizard_dependencies(self):
        """Test that all dependencies for deployment wizard are available"""
        dependencies = [
            'src.utils.gui_theme',
            'src.utils.config_manager',
            'src.utils.source_manager',
            'src.utils.engine_helper',
            'src.utils.gpu_helper',
            'src.utils.cuda_installer'
        ]

        for dep in dependencies:
            with self.subTest(dependency=dep):
                try:
                    __import__(dep)
                except ImportError as e:
                    self.fail(f"Failed to import {dep}: {e}")

    def test_deployment_wizard_initialization(self):
        """Test that deployment wizard can be instantiated without crashing"""
        try:
            # Create hidden root window
            root = tk.Tk()
            root.withdraw()  # Hide window

            # Import and instantiate
            from installer.gui_deploy import DeploymentWizard

            # This should create the wizard without errors
            # (it won't show because window is withdrawn)
            wizard = DeploymentWizard(root)

            # Verify it was created
            self.assertIsNotNone(wizard)

            # Cleanup
            root.destroy()

        except Exception as e:
            self.fail(f"Failed to instantiate DeploymentWizard: {e}")


class TestDashboardImports(unittest.TestCase):
    """Test that unified dashboard can be imported without errors"""

    def test_import_gui_dashboard(self):
        """Test importing the dashboard module"""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "gui_dashboard",
                Path(__file__).parent.parent / "src" / "management" / "gui_dashboard.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Verify the main class exists
            self.assertTrue(hasattr(module, 'UnifiedDashboard'))
        except Exception as e:
            self.fail(f"Failed to import gui_dashboard: {e}")

    def test_dashboard_dependencies(self):
        """Test that all dependencies for dashboard are available"""
        dependencies = [
            'src.utils.gui_theme',
            'src.utils.config_manager',
            'src.utils.source_manager',
            'src.utils.engine_helper',
            'src.utils.gpu_helper',
            'src.core.hybrid_query'
        ]

        for dep in dependencies:
            with self.subTest(dependency=dep):
                try:
                    __import__(dep)
                except ImportError as e:
                    self.fail(f"Failed to import {dep}: {e}")

    def test_dashboard_initialization(self):
        """Test that dashboard can be instantiated without crashing"""
        try:
            # Create hidden root window
            root = tk.Tk()
            root.withdraw()  # Hide window

            # Import and instantiate
            from src.management.gui_dashboard import UnifiedDashboard

            # This should create the dashboard without errors
            # (it won't show because window is withdrawn)
            dashboard = UnifiedDashboard(root)

            # Verify it was created
            self.assertIsNotNone(dashboard)

            # Cleanup
            root.destroy()

        except Exception as e:
            self.fail(f"Failed to instantiate UnifiedDashboard: {e}")


class TestGUITheme(unittest.TestCase):
    """Test GUI theme utilities"""

    def test_theme_import(self):
        """Test that Theme class can be imported"""
        from src.utils.gui_theme import Theme

        # Verify Theme has expected attributes
        self.assertTrue(hasattr(Theme, 'PRIMARY'))
        self.assertTrue(hasattr(Theme, 'SECONDARY'))
        self.assertTrue(hasattr(Theme, 'BG_LIGHT'))
        self.assertTrue(hasattr(Theme, 'apply'))
        self.assertTrue(hasattr(Theme, 'create_header'))

    def test_theme_font_attributes(self):
        """Test that all expected font attributes exist"""
        from src.utils.gui_theme import Theme

        # These are the font attributes GUIs should use
        required_fonts = [
            'FONT_HEADER',
            'FONT_SUBHEADER',
            'FONT_NORMAL',
            'FONT_BOLD',
            'FONT_SMALL',
            'FONT_MONO'
        ]

        for font_attr in required_fonts:
            with self.subTest(attribute=font_attr):
                self.assertTrue(
                    hasattr(Theme, font_attr),
                    f"Theme missing required font attribute: {font_attr}"
                )

    def test_theme_color_attributes(self):
        """Test that all expected color attributes exist"""
        from src.utils.gui_theme import Theme

        required_colors = [
            'PRIMARY',
            'SECONDARY',
            'SUCCESS',
            'WARNING',
            'ERROR',
            'BG_LIGHT',
            'BG_DARK',
            'TEXT_LIGHT',
            'TEXT_DARK'
        ]

        for color_attr in required_colors:
            with self.subTest(attribute=color_attr):
                self.assertTrue(
                    hasattr(Theme, color_attr),
                    f"Theme missing required color attribute: {color_attr}"
                )

    def test_theme_apply_works(self):
        """Test that Theme.apply() works without errors"""
        from src.utils.gui_theme import Theme

        root = tk.Tk()
        root.withdraw()

        try:
            # Should not raise any errors
            Theme.apply(root)
        except Exception as e:
            self.fail(f"Theme.apply() failed: {e}")
        finally:
            root.destroy()

    def test_theme_create_header_works(self):
        """Test that Theme.create_header() works without errors"""
        from src.utils.gui_theme import Theme

        root = tk.Tk()
        root.withdraw()

        try:
            header = Theme.create_header(root, "Test Title", "Test Subtitle")
            self.assertIsNotNone(header)
        except Exception as e:
            self.fail(f"Theme.create_header() failed: {e}")
        finally:
            root.destroy()


class TestUtilityModules(unittest.TestCase):
    """Test that utility modules can be imported"""

    def test_config_manager_import(self):
        """Test ConfigManager import and instantiation"""
        from src.utils.config_manager import ConfigManager

        # Test instantiation with temp directory
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = ConfigManager(Path(tmpdir))
            self.assertIsNotNone(cm)

    def test_source_manager_import(self):
        """Test SourceManager import and instantiation"""
        from src.utils.source_manager import SourceManager

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create required directory structure
            src_dir = Path(tmpdir) / "src" / "indexing"
            src_dir.mkdir(parents=True, exist_ok=True)

            sm = SourceManager(Path(tmpdir))
            self.assertIsNotNone(sm)

    def test_engine_helper_import(self):
        """Test engine_helper functions import"""
        from src.utils.engine_helper import get_available_engines, resolve_uproject_source

        self.assertTrue(callable(get_available_engines))
        self.assertTrue(callable(resolve_uproject_source))

    def test_gpu_helper_import(self):
        """Test gpu_helper functions import"""
        from src.utils.gpu_helper import detect_nvidia_gpu, get_gpu_summary

        self.assertTrue(callable(detect_nvidia_gpu))
        self.assertTrue(callable(get_gpu_summary))


class TestCoreModules(unittest.TestCase):
    """Test that core query modules can be imported"""

    def test_hybrid_query_import(self):
        """Test HybridQueryEngine import"""
        # Skip if embeddings not available (not required for GUI tests)
        try:
            from src.core.hybrid_query import HybridQueryEngine
            self.assertTrue(callable(HybridQueryEngine))
        except (FileNotFoundError, RuntimeError):
            self.skipTest("Vector store not built - skipping hybrid query test")

    def test_query_intent_import(self):
        """Test query intent analyzer import"""
        from src.core.query_intent import QueryIntentAnalyzer, QueryType

        self.assertTrue(callable(QueryIntentAnalyzer))
        self.assertTrue(hasattr(QueryType, 'DEFINITION'))

    def test_definition_extractor_import(self):
        """Test definition extractor import"""
        from src.core.definition_extractor import DefinitionExtractor

        self.assertTrue(callable(DefinitionExtractor))


class TestGUIComponents(unittest.TestCase):
    """Test that critical GUI components can be created"""

    def test_scrolledtext_creation(self):
        """Test that ScrolledText widgets can be created"""
        from tkinter import scrolledtext

        root = tk.Tk()
        root.withdraw()

        try:
            text = scrolledtext.ScrolledText(root, height=10, width=50)
            self.assertIsNotNone(text)
        except Exception as e:
            self.fail(f"Failed to create ScrolledText: {e}")
        finally:
            root.destroy()

    def test_ttk_notebook_creation(self):
        """Test that ttk.Notebook (tabs) can be created"""
        from tkinter import ttk

        root = tk.Tk()
        root.withdraw()

        try:
            notebook = ttk.Notebook(root)
            tab1 = ttk.Frame(notebook)
            notebook.add(tab1, text="Test Tab")
            self.assertIsNotNone(notebook)
        except Exception as e:
            self.fail(f"Failed to create Notebook: {e}")
        finally:
            root.destroy()

    def test_dashboard_tabs_exist(self):
        """Test that dashboard creates all expected tabs"""
        root = tk.Tk()
        root.withdraw()

        try:
            from src.management.gui_dashboard import UnifiedDashboard
            dashboard = UnifiedDashboard(root)

            # Verify tabs were created
            self.assertTrue(hasattr(dashboard, 'notebook'))
            self.assertIsNotNone(dashboard.notebook)

            # Verify tab methods exist
            self.assertTrue(hasattr(dashboard, 'build_query_tab'))
            self.assertTrue(hasattr(dashboard, 'build_sources_tab'))
            self.assertTrue(hasattr(dashboard, 'build_config_tab'))
            self.assertTrue(hasattr(dashboard, 'build_maintenance_tab'))
            self.assertTrue(hasattr(dashboard, 'build_diagnostics_tab'))

        except Exception as e:
            self.fail(f"Failed to verify dashboard tabs: {e}")
        finally:
            root.destroy()


class TestGUIDialogs(unittest.TestCase):
    """Test that GUI dialog methods exist and are callable"""

    def test_dashboard_help_dialog_exists(self):
        """Test that dashboard has detection help dialog method"""
        root = tk.Tk()
        root.withdraw()

        try:
            from src.management.gui_dashboard import UnifiedDashboard
            dashboard = UnifiedDashboard(root)

            # Verify help dialog method exists
            self.assertTrue(hasattr(dashboard, 'show_detection_help_dialog'))
            self.assertTrue(callable(dashboard.show_detection_help_dialog))

        except Exception as e:
            self.fail(f"Failed to verify help dialog: {e}")
        finally:
            root.destroy()

    def test_deployment_wizard_help_dialog_exists(self):
        """Test that deployment wizard has detection help dialog method"""
        root = tk.Tk()
        root.withdraw()

        try:
            from installer.gui_deploy import DeploymentWizard
            wizard = DeploymentWizard(root)

            # Verify help dialog method exists
            self.assertTrue(hasattr(wizard, 'show_detection_help_dialog'))
            self.assertTrue(callable(wizard.show_detection_help_dialog))

        except Exception as e:
            self.fail(f"Failed to verify help dialog: {e}")
        finally:
            root.destroy()


class TestBatchScripts(unittest.TestCase):
    """Test that batch scripts exist and are valid"""

    def setUp(self):
        self.project_root = Path(__file__).parent.parent

    def test_launcher_exists(self):
        """Test launcher.bat exists"""
        launcher = self.project_root / "launcher.bat"
        self.assertTrue(launcher.exists(), "launcher.bat not found")

    def test_setup_exists(self):
        """Test Setup.bat exists"""
        setup = self.project_root / "Setup.bat"
        self.assertTrue(setup.exists(), "Setup.bat not found")

    def test_run_tests_exists(self):
        """Test run-tests.bat exists"""
        run_tests = self.project_root / "tools" / "run-tests.bat"
        self.assertTrue(run_tests.exists(), "tools/run-tests.bat not found")

    def test_launcher_references_correct_file(self):
        """Test that launcher.bat references the correct python file"""
        launcher = self.project_root / "launcher.bat"
        content = launcher.read_text()

        # Should reference gui_dashboard.py
        self.assertIn("gui_dashboard.py", content, "launcher.bat doesn't reference gui_dashboard.py")

    def test_setup_references_correct_file(self):
        """Test that Setup.bat references the correct python file"""
        setup = self.project_root / "Setup.bat"
        content = setup.read_text()

        # Should reference gui_deploy.py
        self.assertIn("gui_deploy.py", content, "Setup.bat doesn't reference gui_deploy.py")


def run_tests():
    """Run all GUI smoke tests"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
