"""
Unit tests for Phase 6 - Environment Detection System

Tests all detection strategies, validation pipeline, and caching.
"""

import unittest
import tempfile
import json
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ue5_query.utils.environment_detector import (
    EnvironmentDetector,
    EnvVarStrategy,
    ConfigFileStrategy,
    RegistryStrategy,
    CommonLocStrategy,
    ValidationPipeline,
    EngineInstallation,
    DetectionSource,
    get_detector
)


class TestEnvVarStrategy(unittest.TestCase):
    """Test environment variable detection"""

    def setUp(self):
        self.strategy = EnvVarStrategy()
        # Save original env vars
        self.original_env = {}
        for var in EnvVarStrategy.ENV_VARS:
            self.original_env[var] = os.environ.get(var)

    def tearDown(self):
        # Restore original env vars
        for var, value in self.original_env.items():
            if value is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = value

    def test_detect_with_ue5_engine_path(self):
        """Test detection with UE5_ENGINE_PATH"""
        test_path = Path(tempfile.mkdtemp()) / "UE_5.3" / "Engine"
        test_path.mkdir(parents=True, exist_ok=True)

        os.environ["UE5_ENGINE_PATH"] = str(test_path)

        installations = self.strategy.detect()

        self.assertEqual(len(installations), 1)
        self.assertEqual(installations[0].engine_root, test_path)
        self.assertEqual(installations[0].source, DetectionSource.ENV_VAR)
        self.assertEqual(installations[0].version, "5.3")

        # Cleanup
        import shutil
        shutil.rmtree(test_path.parent.parent, ignore_errors=True)

    def test_detect_with_ue_root(self):
        """Test detection with UE_ROOT"""
        test_path = Path(tempfile.mkdtemp()) / "UE_5.4" / "Engine"
        test_path.mkdir(parents=True, exist_ok=True)

        os.environ["UE_ROOT"] = str(test_path)

        installations = self.strategy.detect()

        self.assertEqual(len(installations), 1)
        self.assertEqual(installations[0].version, "5.4")

        # Cleanup
        import shutil
        shutil.rmtree(test_path.parent.parent, ignore_errors=True)

    def test_detect_with_parent_directory(self):
        """Test detection when env var points to parent directory"""
        parent_path = Path(tempfile.mkdtemp()) / "UE_5.3"
        engine_path = parent_path / "Engine"
        engine_path.mkdir(parents=True, exist_ok=True)

        os.environ["UE5_ENGINE_PATH"] = str(parent_path)

        installations = self.strategy.detect()

        self.assertEqual(len(installations), 1)
        self.assertEqual(installations[0].engine_root, engine_path)

        # Cleanup
        import shutil
        shutil.rmtree(engine_path.parent.parent, ignore_errors=True)

    def test_detect_with_no_env_vars(self):
        """Test detection when no env vars set"""
        for var in EnvVarStrategy.ENV_VARS:
            os.environ.pop(var, None)

        installations = self.strategy.detect()

        self.assertEqual(len(installations), 0)

    def test_detect_with_invalid_path(self):
        """Test detection with non-existent path"""
        os.environ["UE5_ENGINE_PATH"] = "C:/NonExistent/Path"

        installations = self.strategy.detect()

        self.assertEqual(len(installations), 0)


class TestConfigFileStrategy(unittest.TestCase):
    """Test config file detection"""

    def setUp(self):
        self.strategy = ConfigFileStrategy()
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_cwd = Path.cwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        os.chdir(self.original_cwd)
        # Cleanup temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detect_with_json_config(self):
        """Test detection with JSON config file"""
        config_path = self.temp_dir / ".ue5query"
        engine_path = self.temp_dir / "UE_5.3" / "Engine"
        engine_path.mkdir(parents=True, exist_ok=True)

        config = {
            "engine": {
                "path": str(engine_path),
                "version": "5.3.2"
            }
        }

        config_path.write_text(json.dumps(config))

        installations = self.strategy.detect()

        self.assertEqual(len(installations), 1)
        self.assertEqual(installations[0].engine_root, engine_path)
        self.assertEqual(installations[0].version, "5.3.2")
        self.assertEqual(installations[0].source, DetectionSource.CONFIG_FILE)

    def test_detect_with_missing_config(self):
        """Test detection when no config file exists"""
        installations = self.strategy.detect()

        self.assertEqual(len(installations), 0)

    def test_detect_with_malformed_config(self):
        """Test detection with malformed config"""
        config_path = self.temp_dir / ".ue5query"
        config_path.write_text("invalid json {{{")

        installations = self.strategy.detect()

        self.assertEqual(len(installations), 0)

    def test_detect_with_missing_engine_path(self):
        """Test detection when config has no engine path"""
        config_path = self.temp_dir / ".ue5query"
        config = {"engine": {}}
        config_path.write_text(json.dumps(config))

        installations = self.strategy.detect()

        self.assertEqual(len(installations), 0)


class TestValidationPipeline(unittest.TestCase):
    """Test validation pipeline"""

    def setUp(self):
        self.validator = ValidationPipeline()
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_perfect_installation(self):
        """Test validation of perfect installation"""
        engine_root = self.temp_dir / "Engine"
        (engine_root / "Source").mkdir(parents=True, exist_ok=True)
        (engine_root / "Plugins").mkdir(parents=True, exist_ok=True)
        (engine_root / "Build").mkdir(parents=True, exist_ok=True)
        (engine_root / "Source" / "Runtime").mkdir(parents=True, exist_ok=True)

        # Create Build.version
        build_version = {
            "MajorVersion": 5,
            "MinorVersion": 3,
            "PatchVersion": 2
        }
        (engine_root / "Build" / "Build.version").write_text(json.dumps(build_version))

        install = EngineInstallation(
            version="5.3",
            engine_root=engine_root,
            source=DetectionSource.MANUAL
        )

        result = self.validator.validate(install)

        self.assertTrue(result.valid)
        self.assertEqual(result.health_score, 1.0)
        self.assertEqual(len(result.issues), 0)
        self.assertEqual(result.checks_passed, result.checks_total)

    def test_validate_missing_directories(self):
        """Test validation with missing directories"""
        engine_root = self.temp_dir / "Engine"
        engine_root.mkdir(parents=True, exist_ok=True)
        # Only create Source, missing Plugins and Build

        (engine_root / "Source").mkdir(exist_ok=True)

        install = EngineInstallation(
            version="5.3",
            engine_root=engine_root,
            source=DetectionSource.MANUAL
        )

        result = self.validator.validate(install)

        self.assertTrue(result.valid)  # Still valid, but lower health
        self.assertLess(result.health_score, 1.0)
        self.assertGreater(len(result.warnings), 0)

    def test_validate_nonexistent_path(self):
        """Test validation of non-existent path"""
        engine_root = self.temp_dir / "NonExistent"

        install = EngineInstallation(
            version="5.3",
            engine_root=engine_root,
            source=DetectionSource.MANUAL
        )

        result = self.validator.validate(install)

        self.assertFalse(result.valid)
        self.assertEqual(result.health_score, 0.0)
        self.assertGreater(len(result.issues), 0)


class TestEnvironmentDetector(unittest.TestCase):
    """Test main environment detector"""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.cache_file = self.temp_dir / "detection_cache.json"
        self.detector = EnvironmentDetector(cache_file=self.cache_file)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_deduplication(self):
        """Test that duplicate installations are deduplicated"""
        engine_root = self.temp_dir / "UE_5.3" / "Engine"
        engine_root.mkdir(parents=True, exist_ok=True)

        # Create two installations with same root but different sources
        installs = [
            EngineInstallation(
                version="5.3",
                engine_root=engine_root,
                source=DetectionSource.REGISTRY
            ),
            EngineInstallation(
                version="5.3",
                engine_root=engine_root,
                source=DetectionSource.ENV_VAR
            )
        ]

        deduplicated = self.detector._deduplicate(installs)

        self.assertEqual(len(deduplicated), 1)
        # ENV_VAR has higher priority than REGISTRY
        self.assertEqual(deduplicated[0].source, DetectionSource.ENV_VAR)

    def test_caching(self):
        """Test detection result caching"""
        engine_root = self.temp_dir / "UE_5.3" / "Engine"
        (engine_root / "Source").mkdir(parents=True, exist_ok=True)
        (engine_root / "Plugins").mkdir(parents=True, exist_ok=True)
        (engine_root / "Build").mkdir(parents=True, exist_ok=True)

        install = EngineInstallation(
            version="5.3",
            engine_root=engine_root,
            source=DetectionSource.MANUAL,
            validated=True,
            health_score=1.0
        )

        # Save to cache
        self.detector._save_to_cache([install])

        # Load from cache
        cached = self.detector._load_from_cache()

        self.assertIsNotNone(cached)
        self.assertEqual(len(cached), 1)
        self.assertEqual(cached[0].version, "5.3")
        self.assertEqual(cached[0].engine_root, engine_root)
        self.assertEqual(cached[0].health_score, 1.0)

    def test_cache_expiration(self):
        """Test that expired cache is not loaded"""
        # Create cache with old timestamp
        from datetime import datetime, timedelta

        old_time = datetime.now() - timedelta(hours=25)  # 25 hours ago
        cache_data = {
            "last_scan": old_time.isoformat(),
            "engines": []
        }

        self.cache_file.write_text(json.dumps(cache_data))

        # Should return None for expired cache
        cached = self.detector._load_from_cache()

        self.assertIsNone(cached)

    @patch('src.utils.environment_detector.EnvVarStrategy.detect')
    @patch('src.utils.environment_detector.ConfigFileStrategy.detect')
    @patch('src.utils.environment_detector.RegistryStrategy.detect')
    @patch('src.utils.environment_detector.CommonLocStrategy.detect')
    def test_detect_engines_merges_strategies(self, mock_common, mock_registry, mock_config, mock_envvar):
        """Test that detect_engines merges results from all strategies"""
        engine1 = EngineInstallation(
            version="5.3",
            engine_root=Path("/path1/Engine"),
            source=DetectionSource.ENV_VAR
        )
        engine2 = EngineInstallation(
            version="5.4",
            engine_root=Path("/path2/Engine"),
            source=DetectionSource.REGISTRY
        )

        mock_envvar.return_value = [engine1]
        mock_config.return_value = []
        mock_registry.return_value = [engine2]
        mock_common.return_value = []

        installations = self.detector.detect_engines(use_cache=False, validate=False)

        # Should have both engines
        self.assertEqual(len(installations), 2)


class TestGetDetectorFactory(unittest.TestCase):
    """Test get_detector factory function"""

    def test_get_detector_creates_with_cache_path(self):
        """Test that get_detector creates detector with proper cache path"""
        script_dir = Path(__file__).parent.parent

        detector = get_detector(script_dir)

        self.assertIsNotNone(detector)
        expected_cache = script_dir / "config" / "detection_cache.json"
        self.assertEqual(detector.cache_file, expected_cache)

    def test_get_detector_with_none_uses_parent(self):
        """Test that get_detector with None uses parent directory"""
        detector = get_detector(None)

        self.assertIsNotNone(detector)
        self.assertIsNotNone(detector.cache_file)


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
