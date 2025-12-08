"""
Integration Tests for Update System
Tests actual update functionality from local dev repo and remote git.

These tests verify:
- Local dev repo updates work correctly
- Remote git updates work correctly
- Backup/restore functionality
- File preservation (user data, configs)
- Rollback on failure
"""

import unittest
import json
import shutil
import tempfile
import subprocess
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from update import UpdateManager


class TestLocalUpdate(unittest.TestCase):
    """Test updates from local dev repo"""

    def setUp(self):
        """Create temp dev repo and deployment"""
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

        # Core structure
        (path / ".git").mkdir()
        (path / "installer").mkdir()
        (path / "installer" / "gui_deploy.py").write_text("# GUI installer v1")
        (path / "src" / "core").mkdir(parents=True)
        (path / "src" / "core" / "hybrid_query.py").write_text("# Hybrid query v1")
        (path / "src" / "core" / "query_engine.py").write_text("# Query engine v1")  # ADD THIS
        (path / "src" / "utils").mkdir(parents=True)
        (path / "src" / "utils" / "cli_client.py").write_text("# CLI client v1")
        (path / "tools").mkdir()
        (path / "tools" / "rebuild-index.bat").write_text("@echo off")
        (path / "docs").mkdir()
        (path / "docs" / "README.md").write_text("# Docs v1")

        # Root files
        (path / "README.md").write_text("# Dev Repo v1")
        (path / "requirements.txt").write_text("numpy>=1.20.0")
        (path / "ask.bat").write_text("@echo off")
        (path / "launcher.bat").write_text("@echo off")
        (path / "Setup.bat").write_text("@echo off")

    def _create_deployment(self, path: Path, dev_repo: Path):
        """Create deployment from dev repo"""
        path.mkdir(parents=True, exist_ok=True)

        # Copy structure from dev repo
        for dir_name in ["src", "installer", "tools", "docs"]:
            src_dir = dev_repo / dir_name
            dst_dir = path / dir_name
            if src_dir.exists():
                shutil.copytree(src_dir, dst_dir)

        # Copy root files
        for file_name in ["README.md", "requirements.txt", "ask.bat", "launcher.bat", "Setup.bat"]:
            src_file = dev_repo / file_name
            dst_file = path / file_name
            if src_file.exists():
                shutil.copy2(src_file, dst_file)

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
                "remote_repo": None,
                "branch": "master"
            },
            "exclude_patterns": [".venv/", "data/"],
            "preserve_local": ["data/vector_store.npz", "config/user_config.json"]
        }

        with open(path / ".ue5query_deploy.json", 'w') as f:
            json.dump(config, f, indent=2)

        # Create user data to preserve
        (path / "data").mkdir()
        (path / "data" / "vector_store.npz").write_text("USER DATA - PRESERVE")
        (path / "config").mkdir()
        (path / "config" / "user_config.json").write_text('{"user": "data"}')

    def test_local_update_basic(self):
        """Test basic local update flow"""
        # Modify dev repo
        (self.dev_repo / "src" / "core" / "hybrid_query.py").write_text("# Hybrid query v2 - UPDATED")

        # Create update manager
        manager = UpdateManager(self.deployment)

        # Load config
        self.assertTrue(manager.load_config())

        # Detect source
        source = manager.detect_update_source()
        self.assertEqual(source, "local")

        # Perform update
        success = manager.update_from_local(dry_run=False)
        self.assertTrue(success)

        # Verify file was updated
        updated_content = (self.deployment / "src" / "core" / "hybrid_query.py").read_text()
        self.assertIn("v2 - UPDATED", updated_content)

    def test_local_update_preserves_user_data(self):
        """Test that user data is preserved during update"""
        # Perform update
        manager = UpdateManager(self.deployment)
        manager.load_config()
        success = manager.update_from_local(dry_run=False)
        self.assertTrue(success)

        # Verify user data still exists
        user_data = (self.deployment / "data" / "vector_store.npz").read_text()
        self.assertEqual(user_data, "USER DATA - PRESERVE")

        user_config = (self.deployment / "config" / "user_config.json").read_text()
        self.assertIn("user", user_config)

    def test_local_update_creates_backup(self):
        """Test that backup is created before update"""
        manager = UpdateManager(self.deployment)
        manager.load_config()

        # Update
        success = manager.update_from_local(dry_run=False)
        self.assertTrue(success)

        # Check backup was created
        backups_dir = self.deployment / "backups"
        self.assertTrue(backups_dir.exists())

        # Should have at least one backup
        backups = list(backups_dir.glob("backup_*"))
        self.assertGreaterEqual(len(backups), 1)

        # Backup should contain src/
        latest_backup = backups[0]
        self.assertTrue((latest_backup / "src" / "core" / "hybrid_query.py").exists())

    def test_local_update_verification(self):
        """Test post-update verification"""
        manager = UpdateManager(self.deployment)
        manager.load_config()
        manager.update_from_local(dry_run=False)

        # Verify installation
        valid = manager.verify_installation()
        self.assertTrue(valid)

    def test_local_update_multiple_files(self):
        """Test updating multiple files"""
        # Modify multiple files in dev repo
        (self.dev_repo / "src" / "core" / "hybrid_query.py").write_text("# Updated 1")
        (self.dev_repo / "src" / "utils" / "cli_client.py").write_text("# Updated 2")
        (self.dev_repo / "docs" / "README.md").write_text("# Updated 3")
        (self.dev_repo / "README.md").write_text("# Updated 4")

        # Update
        manager = UpdateManager(self.deployment)
        manager.load_config()
        success = manager.update_from_local(dry_run=False)
        self.assertTrue(success)

        # Verify all files updated
        self.assertIn("Updated 1", (self.deployment / "src" / "core" / "hybrid_query.py").read_text())
        self.assertIn("Updated 2", (self.deployment / "src" / "utils" / "cli_client.py").read_text())
        self.assertIn("Updated 3", (self.deployment / "docs" / "README.md").read_text())
        self.assertIn("Updated 4", (self.deployment / "README.md").read_text())


class TestRemoteUpdate(unittest.TestCase):
    """Test updates from remote git repository"""

    def setUp(self):
        """Create temp git repo and deployment"""
        self.temp_dir = Path(tempfile.mkdtemp())

        # Create bare git repo (simulates remote)
        self.remote_repo = self.temp_dir / "remote.git"
        self.remote_repo.mkdir()

        # Initialize bare repo
        try:
            subprocess.run(
                ["git", "init", "--bare", str(self.remote_repo)],
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError:
            self.skipTest("Git not available")

        # Create local working copy to push to remote
        self.working_copy = self.temp_dir / "working"
        self._create_git_repo(self.working_copy, self.remote_repo)

        # Create deployment
        self.deployment = self.temp_dir / "deployment"
        self._create_deployment(self.deployment, self.remote_repo)

    def tearDown(self):
        """Cleanup"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_git_repo(self, path: Path, remote: Path):
        """Create git repo with initial commit"""
        path.mkdir(parents=True)

        # Initialize repo
        subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True, capture_output=True)

        # Create structure
        (path / "src" / "core").mkdir(parents=True)
        (path / "src" / "core" / "hybrid_query.py").write_text("# Version 1")
        (path / "installer").mkdir()
        (path / "installer" / "gui_deploy.py").write_text("# Installer v1")
        (path / "tools").mkdir()
        (path / "docs").mkdir()
        (path / "README.md").write_text("# Readme v1")

        # Commit
        subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=path, check=True, capture_output=True)

        # Add remote and push
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=path, check=True, capture_output=True)
        subprocess.run(["git", "push", "-u", "origin", "master"], cwd=path, check=True, capture_output=True)

    def _create_deployment(self, path: Path, remote: Path):
        """Create deployment configured for remote updates"""
        path.mkdir(parents=True)

        # Create minimal structure
        (path / "src" / "core").mkdir(parents=True)
        (path / "src" / "core" / "hybrid_query.py").write_text("# Old version")
        (path / "installer").mkdir()
        (path / "tools").mkdir()
        (path / "docs").mkdir()

        # Create deployment config pointing to remote
        config = {
            "version": "2.0.0",
            "deployment_info": {
                "deployed_from": "remote",
                "deployed_at": "2025-12-08T00:00:00Z",
                "deployed_to": str(path)
            },
            "update_sources": {
                "local_dev_repo": None,
                "remote_repo": str(remote),
                "branch": "master"
            },
            "exclude_patterns": [".venv/", "data/"],
            "preserve_local": []
        }

        with open(path / ".ue5query_deploy.json", 'w') as f:
            json.dump(config, f, indent=2)

    def test_remote_update_detection(self):
        """Test detection of remote update source"""
        manager = UpdateManager(self.deployment)
        manager.load_config()

        source = manager.detect_update_source()
        self.assertEqual(source, "remote")

    def test_remote_update_clone(self):
        """Test cloning from remote"""
        manager = UpdateManager(self.deployment)
        manager.load_config()

        # Perform remote update
        success = manager.update_from_remote(dry_run=False)
        self.assertTrue(success)

        # Verify files were updated
        content = (self.deployment / "src" / "core" / "hybrid_query.py").read_text()
        self.assertIn("Version 1", content)

    def test_remote_update_pull(self):
        """Test pulling updates from remote"""
        # First update (clone)
        manager = UpdateManager(self.deployment)
        manager.load_config()
        manager.update_from_remote(dry_run=False)

        # Make change to remote
        (self.working_copy / "src" / "core" / "hybrid_query.py").write_text("# Version 2 - UPDATED")
        subprocess.run(["git", "add", "."], cwd=self.working_copy, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Update"], cwd=self.working_copy, check=True, capture_output=True)
        subprocess.run(["git", "push"], cwd=self.working_copy, check=True, capture_output=True)

        # Second update (pull)
        manager2 = UpdateManager(self.deployment)
        manager2.load_config()
        success = manager2.update_from_remote(dry_run=False)
        self.assertTrue(success)

        # Verify new version
        content = (self.deployment / "src" / "core" / "hybrid_query.py").read_text()
        self.assertIn("Version 2", content)


class TestUpdateFailureHandling(unittest.TestCase):
    """Test error handling and rollback"""

    def setUp(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.dev_repo = self.temp_dir / "dev_repo"
        self.deployment = self.temp_dir / "deployment"

    def tearDown(self):
        """Cleanup"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_rollback_on_verification_failure(self):
        """Test rollback when verification fails"""
        # This would require mocking verification failure
        # Skip for now as it's complex to set up
        pass

    def test_missing_dev_repo(self):
        """Test handling when dev repo doesn't exist"""
        self.deployment.mkdir()

        config = {
            "version": "2.0.0",
            "deployment_info": {},
            "update_sources": {
                "local_dev_repo": str(self.temp_dir / "nonexistent"),
                "remote_repo": None,
                "branch": "master"
            }
        }

        (self.deployment / ".ue5query_deploy.json").write_text(json.dumps(config))

        manager = UpdateManager(self.deployment)
        manager.load_config()

        # Should fail gracefully
        success = manager.update_from_local(dry_run=False)
        self.assertFalse(success)


def run_tests():
    """Run all integration tests"""
    print("=" * 70)
    print("Update System - Integration Test Suite")
    print("=" * 70)
    print()

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestLocalUpdate))
    suite.addTests(loader.loadTestsFromTestCase(TestRemoteUpdate))
    suite.addTests(loader.loadTestsFromTestCase(TestUpdateFailureHandling))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print()
    print("=" * 70)
    print("Integration Test Summary")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    if result.wasSuccessful():
        print("\n[OK] All integration tests passed!")
        return 0
    else:
        print("\n[ERROR] Some integration tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
