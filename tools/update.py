#!/usr/bin/env python3
"""
Smart Update System for UE5 Source Query
Updates deployed installation from local dev repo or remote GitHub.

Usage:
    python tools/update.py                    # Auto-detect source
    python tools/update.py --source local     # Force local dev repo
    python tools/update.py --source remote    # Force remote repo
    python tools/update.py --dry-run          # Show what would change
"""

import json
import subprocess
import shutil
import argparse
import stat
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

# Default exclusion patterns (never copy these)
DEFAULT_EXCLUDES = [
    ".venv",
    ".git",
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".pytest_cache",
    ".coverage",
    "*.log",
    ".DS_Store",
    "Thumbs.db"
]

# Files to preserve (never overwrite)
PRESERVE_FILES = [
    "data/vector_store.npz",
    "data/vector_meta.json",
    "data/vector_meta_enriched.json",
    "data/vector_cache.json",
    "config/user_config.json",
    ".env"
]


def remove_readonly(func, path, exc_info):
    """Error handler for shutil.rmtree to handle read-only files (like git files on Windows)"""
    # Clear the readonly bit and try again
    try:
        Path(path).chmod(stat.S_IWRITE)
        func(path)
    except:
        pass


def robust_rmtree(path: Path, max_attempts: int = 3):
    """Robustly remove a directory tree, handling read-only files and filesystem locks"""
    if not path.exists():
        return

    for attempt in range(max_attempts):
        try:
            shutil.rmtree(path, onerror=remove_readonly)
            # Verify it's actually gone
            if not path.exists():
                return
        except (OSError, PermissionError):
            pass

        # Wait before retry
        if attempt < max_attempts - 1:
            time.sleep(0.2)

    # Last resort: ignore errors
    try:
        shutil.rmtree(path, ignore_errors=True)
    except:
        pass


class UpdateManager:
    """Manages updates for deployed UE5 Source Query installations"""

    def __init__(self, deployment_root: Path):
        self.deployment_root = deployment_root
        self.config_file = deployment_root / ".ue5query_deploy.json"
        self.config: Optional[Dict[str, Any]] = None
        self.backup_dir: Optional[Path] = None

    def load_config(self) -> bool:
        """Load deployment configuration"""
        if not self.config_file.exists():
            print(f"[ERROR] Deployment config not found: {self.config_file}")
            print("This doesn't appear to be a deployed installation.")
            print("Run the GUI installer to deploy first.")
            return False

        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
            print(f"[OK] Loaded deployment config")
            return True
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse config: {e}")
            return False

    def detect_update_source(self, force_source: Optional[str] = None) -> Optional[str]:
        """
        Detect best update source (local dev repo or remote).

        Args:
            force_source: 'local' or 'remote' to override auto-detection

        Returns:
            'local' or 'remote' or None if no source available
        """
        if force_source:
            if force_source not in ['local', 'remote']:
                print(f"[ERROR] Invalid source: {force_source}. Use 'local' or 'remote'.")
                return None
            print(f"[CONFIG] Forcing update source: {force_source}")
            return force_source

        # Try local dev repo first
        local_repo = self.config.get("update_sources", {}).get("local_dev_repo")
        if local_repo:
            local_path = Path(local_repo)
            if self._is_valid_dev_repo(local_path):
                print(f"[OK] Found local dev repo: {local_path}")
                return 'local'
            else:
                print(f"[WARN]  Local dev repo not valid: {local_path}")

        # Fall back to remote
        remote_repo = self.config.get("update_sources", {}).get("remote_repo")
        if remote_repo:
            print(f"[REMOTE] Using remote repo: {remote_repo}")
            return 'remote'

        print("[ERROR] No update source available!")
        print("Configure local_dev_repo or remote_repo in .ue5query_deploy.json")
        return None

    def _is_valid_dev_repo(self, path: Path) -> bool:
        """Check if path is a valid UE5 Source Query dev repo"""
        if not path.exists():
            return False

        # Check for key files
        required = [
            path / "src" / "core" / "hybrid_query.py",
            path / "installer" / "gui_deploy.py",
            path / "README.md"
        ]
        return all(f.exists() for f in required)

    def create_backup(self) -> bool:
        """Create backup before update"""
        import uuid
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Add unique suffix to avoid collisions in rapid updates
        unique_id = str(uuid.uuid4())[:8]
        self.backup_dir = self.deployment_root / "backups" / f"backup_{timestamp}_{unique_id}"

        print(f"[BACKUP] Creating backup: {self.backup_dir}")

        try:
            self.backup_dir.mkdir(parents=True, exist_ok=False)

            # Backup critical directories
            for dir_name in ["src", "installer", "tools"]:
                src_dir = self.deployment_root / dir_name
                if src_dir.exists():
                    shutil.copytree(src_dir, self.backup_dir / dir_name)

            # Backup config
            if self.config_file.exists():
                shutil.copy2(self.config_file, self.backup_dir / ".ue5query_deploy.json")

            print(f"[OK] Backup created successfully")
            return True

        except Exception as e:
            print(f"[ERROR] Backup failed: {e}")
            return False

    def update_from_local(self, dry_run: bool = False) -> bool:
        """Update from local dev repo"""
        local_repo = Path(self.config["update_sources"]["local_dev_repo"])
        print(f"\n[UPDATE] Updating from local dev repo: {local_repo}")

        if not self._is_valid_dev_repo(local_repo):
            print(f"[ERROR] Invalid dev repo: {local_repo}")
            return False

        # Directories to sync
        sync_dirs = ["src", "installer", "tools", "docs"]

        exclude_patterns = DEFAULT_EXCLUDES + self.config.get("exclude_patterns", [])

        if dry_run:
            print("\n[CHECK] DRY RUN - Would update:")
            for dir_name in sync_dirs:
                src = local_repo / dir_name
                if src.exists():
                    print(f"  - {dir_name}/")
            return True

        # Create backup
        if not self.create_backup():
            return False

        try:
            # Copy directories
            for dir_name in sync_dirs:
                src_dir = local_repo / dir_name
                dst_dir = self.deployment_root / dir_name

                if not src_dir.exists():
                    print(f"[WARN]  Skipping {dir_name}/ (not found in source)")
                    continue

                print(f"[DIR] Syncing {dir_name}/...")

                # Remove existing directory (except preserved files)
                if dst_dir.exists():
                    self._safe_remove_dir(dst_dir)

                # Copy new version
                shutil.copytree(
                    src_dir,
                    dst_dir,
                    ignore=shutil.ignore_patterns(*exclude_patterns)
                )

            # Copy root files
            for file_name in ["README.md", "requirements.txt", "ask.bat", "launcher.bat", "Setup.bat"]:
                src_file = local_repo / file_name
                dst_file = self.deployment_root / file_name
                if src_file.exists():
                    shutil.copy2(src_file, dst_file)
                    print(f"[FILE] Updated {file_name}")

            # Restore preserved files from backup
            self._restore_preserved_files()

            # Update deployment config
            self._update_deployment_info("local", local_repo)

            print("\n[OK] Local update completed successfully!")
            return True

        except Exception as e:
            print(f"\n[ERROR] Update failed: {e}")
            print("Attempting rollback...")
            self._rollback()
            return False

    def update_from_remote(self, dry_run: bool = False) -> bool:
        """Update from remote GitHub repo"""
        remote_repo = self.config["update_sources"]["remote_repo"]
        branch = self.config["update_sources"].get("branch", "master")

        print(f"\n[REMOTE] Updating from remote repo: {remote_repo}")
        print(f"Branch: {branch}")

        if dry_run:
            print("\n[CHECK] DRY RUN - Would fetch from remote")
            return True

        # Create temporary directory for git clone
        temp_dir = self.deployment_root / "temp_update"

        # Force cleanup of any existing temp directory for fresh clone
        robust_rmtree(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Always clone fresh for reliability
            print("[DOWNLOAD] Cloning repository...")
            subprocess.run(
                ["git", "clone", "-b", branch, remote_repo, str(temp_dir)],
                check=True,
                capture_output=True
            )

            # Create backup
            if not self.create_backup():
                return False

            # Copy files from temp to deployment
            print("[UPDATE] Installing update...")
            for dir_name in ["src", "installer", "tools", "docs"]:
                src_dir = temp_dir / dir_name
                dst_dir = self.deployment_root / dir_name

                if src_dir.exists():
                    if dst_dir.exists():
                        self._safe_remove_dir(dst_dir)
                    shutil.copytree(src_dir, dst_dir, ignore=shutil.ignore_patterns(*DEFAULT_EXCLUDES))
                    print(f"[OK] Updated {dir_name}/")

            # Restore preserved files
            self._restore_preserved_files()

            # Update deployment config
            self._update_deployment_info("remote", remote_repo)

            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)

            print("\n[OK] Remote update completed successfully!")
            return True

        except subprocess.CalledProcessError as e:
            print(f"\n[ERROR] Git command failed: {e}")
            print(e.stderr.decode() if e.stderr else "")
            return False
        except Exception as e:
            print(f"\n[ERROR] Update failed: {e}")
            self._rollback()
            return False
        finally:
            # Always cleanup temp directory
            robust_rmtree(temp_dir)

    def _safe_remove_dir(self, directory: Path):
        """Remove directory while preserving certain files"""
        preserve_paths = [self.deployment_root / p for p in PRESERVE_FILES]

        for preserve_path in preserve_paths:
            if preserve_path.exists() and preserve_path.is_relative_to(directory):
                # This file should be preserved, skip deletion
                continue

        # Remove directory
        if directory.exists():
            shutil.rmtree(directory, ignore_errors=True)

    def _restore_preserved_files(self):
        """Restore preserved files from backup"""
        if not self.backup_dir:
            return

        for file_path in PRESERVE_FILES:
            backup_file = self.backup_dir / file_path
            dest_file = self.deployment_root / file_path

            if backup_file.exists():
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_file, dest_file)
                print(f"[PRESERVE] Restored preserved file: {file_path}")

    def _update_deployment_info(self, source: str, source_path):
        """Update deployment info in config"""
        if not self.config:
            return

        self.config["deployment_info"]["last_updated"] = datetime.now().isoformat()
        self.config["deployment_info"]["update_source"] = source
        self.config["deployment_info"]["updated_from"] = str(source_path)

        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def _rollback(self) -> bool:
        """Rollback to backup on failure"""
        if not self.backup_dir or not self.backup_dir.exists():
            print("[ERROR] No backup available for rollback!")
            return False

        try:
            print(f"[ROLLBACK]  Rolling back from: {self.backup_dir}")

            for dir_name in ["src", "installer", "tools"]:
                backup_src = self.backup_dir / dir_name
                if backup_src.exists():
                    dest = self.deployment_root / dir_name
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(backup_src, dest)

            print("[OK] Rollback successful")
            return True

        except Exception as e:
            print(f"[ERROR] Rollback failed: {e}")
            return False

    def verify_installation(self) -> bool:
        """Verify installation after update"""
        print("\n[CHECK] Verifying installation...")

        checks = [
            ("Core module", self.deployment_root / "src" / "core" / "hybrid_query.py"),
            ("Query engine", self.deployment_root / "src" / "core" / "query_engine.py"),
            ("CLI client", self.deployment_root / "src" / "utils" / "cli_client.py"),
            ("Config file", self.config_file),
        ]

        all_ok = True
        for name, path in checks:
            if path.exists():
                print(f"  [OK] {name}")
            else:
                print(f"  [ERROR] {name} - MISSING!")
                all_ok = False

        return all_ok


def main():
    parser = argparse.ArgumentParser(description="Update UE5 Source Query installation")
    parser.add_argument("--source", choices=["local", "remote"], help="Force update source")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without applying")
    args = parser.parse_args()

    print("=" * 60)
    print("UE5 Source Query - Smart Update System")
    print("=" * 60)

    # Detect deployment root (current directory)
    deployment_root = Path.cwd()
    print(f"\nDeployment: {deployment_root}")

    # Initialize update manager
    manager = UpdateManager(deployment_root)

    # Load config
    if not manager.load_config():
        return 1

    # Detect update source
    source = manager.detect_update_source(args.source)
    if not source:
        return 1

    # Perform update
    if source == "local":
        success = manager.update_from_local(dry_run=args.dry_run)
    else:
        success = manager.update_from_remote(dry_run=args.dry_run)

    if not success:
        return 1

    # Verify installation (skip for dry run)
    if not args.dry_run:
        if not manager.verify_installation():
            print("\n[WARN]  Verification failed! Installation may be incomplete.")
            return 1

        print("\n" + "=" * 60)
        print("[OK] Update completed successfully!")
        print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
