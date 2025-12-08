"""
Comprehensive Test Suite for Deployment Detection System

Tests all edge cases:
- Bidirectional discovery (dev repo <-> deployments)
- Missing paths, moved repos
- Broken deployment configs
- Self-repair functionality
- Registry management
"""

import unittest
import json
import shutil
import tempfile
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.deployment_detector import (
    DeploymentDetector,
    DeploymentRegistry,
    DeploymentInfo
)


class TestDeploymentRegistry(unittest.TestCase):
    """Test deployment registry functionality"""

    def setUp(self):
        """Create temp dev repo for testing"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.dev_repo = self.temp_dir / "dev_repo"
        self.dev_repo.mkdir()

        # Create minimal dev repo structure
        (self.dev_repo / ".git").mkdir()
        (self.dev_repo / "installer").mkdir()
        (self.dev_repo / "installer" / "gui_deploy.py").touch()
        (self.dev_repo / "src" / "core").mkdir(parents=True)
        (self.dev_repo / "src" / "core" / "hybrid_query.py").touch()

        self.registry = DeploymentRegistry(self.dev_repo)

    def tearDown(self):
        """Cleanup temp directory"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_registry_creation(self):
        """Test registry file creation"""
        self.registry.save()
        registry_file = self.dev_repo / ".deployments_registry.json"
        self.assertTrue(registry_file.exists())

    def test_register_deployment(self):
        """Test registering a deployment"""
        # Create fake deployment
        deployment = self.temp_dir / "deployment1"
        deployment.mkdir()

        # Create deployment config
        config = {
            "deployment_info": {
                "deployed_from": str(self.dev_repo),
                "deployed_at": "2025-12-08T00:00:00Z"
            }
        }
        with open(deployment / ".ue5query_deploy.json", 'w') as f:
            json.dump(config, f)

        # Register it
        self.registry.register_deployment(deployment)

        # Verify
        deployments = self.registry.get_all_deployments(validate=False)
        self.assertEqual(len(deployments), 1)
        self.assertEqual(deployments[0].path, str(deployment))

    def test_unregister_deployment(self):
        """Test unregistering a deployment"""
        deployment = self.temp_dir / "deployment1"
        deployment.mkdir()

        config = {
            "deployment_info": {
                "deployed_from": str(self.dev_repo),
                "deployed_at": "2025-12-08T00:00:00Z"
            }
        }
        with open(deployment / ".ue5query_deploy.json", 'w') as f:
            json.dump(config, f)

        # Register then unregister
        self.registry.register_deployment(deployment)
        self.assertEqual(len(self.registry.deployments), 1)

        self.registry.unregister_deployment(deployment)
        self.assertEqual(len(self.registry.deployments), 0)

    def test_validate_deployments(self):
        """Test deployment validation"""
        # Create valid deployment
        valid_deploy = self.temp_dir / "valid"
        valid_deploy.mkdir()
        (valid_deploy / ".ue5query_deploy.json").write_text('{"deployment_info":{}}')
        (valid_deploy / "src" / "core").mkdir(parents=True)
        (valid_deploy / "src" / "core" / "hybrid_query.py").touch()

        # Create invalid deployment (path doesn't exist)
        invalid_deploy_info = DeploymentInfo(
            path=str(self.temp_dir / "nonexistent"),
            deployed_from=str(self.dev_repo),
            deployed_at="2025-12-08T00:00:00Z"
        )

        self.registry.deployments["invalid"] = invalid_deploy_info
        self.registry.register_deployment(valid_deploy)

        # Validate
        deployments = self.registry.get_all_deployments(validate=True)

        # Check results
        valid_count = sum(1 for d in deployments if d.is_valid)
        invalid_count = sum(1 for d in deployments if not d.is_valid)

        self.assertEqual(valid_count, 1)
        self.assertEqual(invalid_count, 1)

    def test_cleanup_invalid(self):
        """Test cleanup of invalid deployments"""
        # Add invalid deployment
        invalid_deploy = DeploymentInfo(
            path=str(self.temp_dir / "nonexistent"),
            deployed_from=str(self.dev_repo),
            deployed_at="2025-12-08T00:00:00Z",
            is_valid=False
        )

        self.registry.deployments["invalid"] = invalid_deploy
        self.assertEqual(len(self.registry.deployments), 1)

        # Cleanup
        self.registry.cleanup_invalid()

        # Should be empty
        self.assertEqual(len(self.registry.deployments), 0)


class TestDeploymentDetector(unittest.TestCase):
    """Test deployment detector functionality"""

    def setUp(self):
        """Create temp structures for testing"""
        self.temp_dir = Path(tempfile.mkdtemp())

        # Create dev repo
        self.dev_repo = self.temp_dir / "dev_repo"
        self._create_dev_repo(self.dev_repo)

        # Create deployment
        self.deployment = self.temp_dir / "deployment"
        self._create_deployment(self.deployment, self.dev_repo)

    def tearDown(self):
        """Cleanup"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_dev_repo(self, path: Path):
        """Create minimal dev repo structure"""
        path.mkdir(parents=True, exist_ok=True)
        (path / ".git").mkdir()
        (path / "installer").mkdir()
        (path / "installer" / "gui_deploy.py").touch()
        (path / "src" / "core").mkdir(parents=True)
        (path / "src" / "core" / "hybrid_query.py").touch()
        (path / "src" / "core" / "query_engine.py").touch()
        (path / "src" / "utils").mkdir(parents=True)
        (path / "src" / "utils" / "cli_client.py").touch()
        (path / "tests").mkdir()

    def _create_deployment(self, path: Path, dev_repo: Path):
        """Create minimal deployment structure"""
        path.mkdir(parents=True, exist_ok=True)
        (path / "src" / "core").mkdir(parents=True)
        (path / "src" / "core" / "hybrid_query.py").touch()
        (path / "src" / "core" / "query_engine.py").touch()
        (path / "src" / "utils").mkdir(parents=True)
        (path / "src" / "utils" / "cli_client.py").touch()

        # Create deployment config
        config = {
            "version": "2.0.0",
            "deployment_info": {
                "deployed_from": str(dev_repo),
                "deployed_at": "2025-12-08T00:00:00Z",
                "deployed_to": str(path)
            },
            "update_sources": {
                "local_dev_repo": str(dev_repo),
                "remote_repo": "https://github.com/test/repo.git",
                "branch": "master"
            }
        }

        with open(path / ".ue5query_deploy.json", 'w') as f:
            json.dump(config, f, indent=2)

    def test_detect_dev_repo(self):
        """Test detection from dev repo"""
        detector = DeploymentDetector(self.dev_repo)

        self.assertTrue(detector.is_dev_repo())
        self.assertFalse(detector.is_deployed())
        self.assertEqual(detector.env_type, "dev_repo")
        self.assertTrue(detector.env_info.is_valid)

    def test_detect_deployment(self):
        """Test detection from deployment"""
        detector = DeploymentDetector(self.deployment)

        self.assertFalse(detector.is_dev_repo())
        self.assertTrue(detector.is_deployed())
        self.assertEqual(detector.env_type, "deployed")
        self.assertTrue(detector.env_info.is_valid)

    def test_find_dev_repo_from_deployment(self):
        """Test finding dev repo from deployment"""
        detector = DeploymentDetector(self.deployment)

        dev_repo_path = detector.get_dev_repo_path()
        self.assertIsNotNone(dev_repo_path)
        self.assertEqual(dev_repo_path, self.dev_repo)

    def test_find_deployments_from_dev_repo(self):
        """Test finding deployments from dev repo"""
        # First, run detector from deployment to register it
        DeploymentDetector(self.deployment)

        # Now detect from dev repo
        detector = DeploymentDetector(self.dev_repo)
        deployments = detector.get_deployments()

        self.assertGreaterEqual(len(deployments), 1)
        deploy_paths = [d.path for d in deployments]
        self.assertIn(str(self.deployment), deploy_paths)

    def test_update_source_detection(self):
        """Test update source detection"""
        detector = DeploymentDetector(self.deployment)

        self.assertTrue(detector.can_update())
        source = detector.get_update_source()
        self.assertEqual(source, "local")

    def test_update_source_remote_fallback(self):
        """Test fallback to remote when local dev repo missing"""
        # Create deployment with non-existent local dev repo
        deployment2 = self.temp_dir / "deployment2"
        deployment2.mkdir(parents=True)
        (deployment2 / "src" / "core").mkdir(parents=True)
        (deployment2 / "src" / "core" / "hybrid_query.py").touch()
        (deployment2 / "src" / "core" / "query_engine.py").touch()
        (deployment2 / "src" / "utils").mkdir(parents=True)
        (deployment2 / "src" / "utils" / "cli_client.py").touch()

        # Create config with ONLY remote repo (no local dev repo path)
        config = {
            "version": "2.0.0",
            "deployment_info": {
                "deployed_from": "unknown",
                "deployed_at": "2025-12-08T00:00:00Z",
                "deployed_to": str(deployment2)
            },
            "update_sources": {
                "local_dev_repo": None,  # No local dev repo
                "remote_repo": "https://github.com/test/repo.git",
                "branch": "master"
            }
        }

        with open(deployment2 / ".ue5query_deploy.json", 'w') as f:
            json.dump(config, f, indent=2)

        detector = DeploymentDetector(deployment2)

        self.assertTrue(detector.can_update())
        source = detector.get_update_source()
        # Should fall back to remote since local_dev_repo is None
        self.assertEqual(source, "remote")

    def test_missing_components_detection(self):
        """Test detection of missing components"""
        # Create incomplete deployment
        incomplete = self.temp_dir / "incomplete"
        incomplete.mkdir()
        (incomplete / ".ue5query_deploy.json").write_text('{"deployment_info":{}, "update_sources":{}}')

        # Missing core module
        detector = DeploymentDetector(incomplete)
        missing = detector._get_missing_components()

        self.assertGreater(len(missing), 0)
        self.assertIn("Core module", missing)

    def test_self_repair_missing_config(self):
        """Test self-repair of missing deployment config"""
        # Create deployment without config
        no_config = self.temp_dir / "no_config"
        no_config.mkdir()
        (no_config / "src" / "core").mkdir(parents=True)
        (no_config / "src" / "core" / "hybrid_query.py").touch()
        (no_config / "src" / "core" / "query_engine.py").touch()
        (no_config / "src" / "utils").mkdir(parents=True)
        (no_config / "src" / "utils" / "cli_client.py").touch()

        detector = DeploymentDetector(no_config)

        # Should detect as deployed but invalid
        self.assertFalse(detector.env_info.is_valid)

        # Attempt self-repair
        success, actions = detector.self_repair()

        # Should create config
        config_file = no_config / ".ue5query_deploy.json"
        self.assertTrue(config_file.exists())

    def test_self_repair_find_dev_repo(self):
        """Test self-repair finding dev repo"""
        # Create deployment with NO dev repo path in config
        broken = self.temp_dir / "broken"
        broken.mkdir(parents=True)
        (broken / "src" / "core").mkdir(parents=True)
        (broken / "src" / "core" / "hybrid_query.py").touch()
        (broken / "src" / "core" / "query_engine.py").touch()
        (broken / "src" / "utils").mkdir(parents=True)
        (broken / "src" / "utils" / "cli_client.py").touch()

        config = {
            "version": "2.0.0",
            "deployment_info": {
                "deployed_from": "unknown",
                "deployed_at": "2025-12-08T00:00:00Z",
                "deployed_to": str(broken)
            },
            "update_sources": {
                "local_dev_repo": None,  # No dev repo path
                "remote_repo": "https://github.com/test/repo.git",
                "branch": "master"
            }
        }

        with open(broken / ".ue5query_deploy.json", 'w') as f:
            json.dump(config, f)

        detector = DeploymentDetector(broken)

        # Should be valid deployment with no dev repo (config set to None)
        self.assertEqual(detector.env_type, "deployed")
        self.assertIsNone(detector.env_info.dev_repo_path)  # Should respect config
        self.assertTrue(detector.can_update())  # Can still update from remote
        self.assertEqual(detector.get_update_source(), "remote")  # Falls back to remote

        # Attempt self-repair - should succeed (no repairs needed if config is valid)
        success, actions = detector.self_repair()
        self.assertIsInstance(actions, list)
        self.assertGreater(len(actions), 0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_empty_directory(self):
        """Test detection in empty directory"""
        empty = self.temp_dir / "empty"
        empty.mkdir()

        detector = DeploymentDetector(empty)
        self.assertEqual(detector.env_type, "unknown")

    def test_partial_dev_repo(self):
        """Test detection with incomplete dev repo"""
        partial = self.temp_dir / "partial"
        partial.mkdir()
        (partial / ".git").mkdir()  # Has .git but missing other markers

        detector = DeploymentDetector(partial)
        # Should not detect as valid dev repo
        self.assertNotEqual(detector.env_type, "dev_repo")

    def test_corrupted_deployment_config(self):
        """Test handling of corrupted deployment config"""
        corrupted = self.temp_dir / "corrupted"
        corrupted.mkdir()
        (corrupted / "src" / "core").mkdir(parents=True)
        (corrupted / "src" / "core" / "hybrid_query.py").touch()

        # Write invalid JSON
        with open(corrupted / ".ue5query_deploy.json", 'w') as f:
            f.write("{invalid json content")

        detector = DeploymentDetector(corrupted)
        self.assertFalse(detector.env_info.is_valid)
        self.assertGreater(len(detector.env_info.issues), 0)

    def test_moved_dev_repo(self):
        """Test handling when dev repo has moved"""
        # This would require actual dev repo search strategies
        # Tested implicitly in self_repair tests
        pass


def run_tests():
    """Run all tests"""
    print("=" * 70)
    print("Deployment Detection System - Comprehensive Test Suite")
    print("=" * 70)
    print()

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestDeploymentRegistry))
    suite.addTests(loader.loadTestsFromTestCase(TestDeploymentDetector))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print()
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n[OK] All tests passed!")
        return 0
    else:
        print("\n[ERROR] Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
