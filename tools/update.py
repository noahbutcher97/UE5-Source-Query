#!/usr/bin/env python3
"""
Bidirectional Update System for UE5 Source Query

Two-way update utility that works intelligently based on context:

**When run from DEV REPO:**
    Updates ALL tracked deployments with local changes
    Usage: python tools/update.py --push-all
           python tools/update.py --push <deployment_path>

**When run from DEPLOYED REPO:**
    Pulls updates from dev repo or remote
    Usage: python tools/update.py                    # Auto-detect source
           python tools/update.py --source local     # Force local dev repo
           python tools/update.py --source remote    # Force remote repo
           python tools/update.py --check            # Check for updates only

**General Options:**
    --dry-run          Show what would change without applying
    --force            Force update even if versions match
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

# Default exclusion patterns (Fallback if config missing)
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

# Deployment exclusion patterns (Fallback)
DEPLOYMENT_EXCLUDES = [
    "src/research",
    "src/research/**",
    "docs/Development",
    "docs/Development/**",
    "docs/_archive",
    "docs/_archive/**",
    "src/indexing/BuildSourceIndex.ps1",
    "src/indexing/BuildSourceIndexAdmin.bat",
    "tests/DEPLOYMENT_TEST_RESULTS.md",
    "tools/setup-git-lfs.bat",
    "CLAUDE.md",
    "GEMINI.md",
]

# Load rules from centralized config
try:
    config_path = Path(__file__).parent.parent / "config" / "deployment_rules.json"
    if config_path.exists():
        with open(config_path, "r") as f:
            rules = json.load(f)
            DEFAULT_EXCLUDES = rules.get("default_excludes", DEFAULT_EXCLUDES)
            DEPLOYMENT_EXCLUDES = rules.get("deployment_excludes", DEPLOYMENT_EXCLUDES)
except Exception as e:
    print(f"[WARN] Failed to load deployment rules: {e}")

def clean_dev_files(deployment_root: Path):
    """Remove dev-only files from existing deployment."""
    dev_files = [
        "src/research",
        "docs/Development",
        "docs/_archive",
        "src/indexing/BuildSourceIndex.ps1",
        "src/indexing/BuildSourceIndexAdmin.bat",
        "CLAUDE.md",
        "GEMINI.md",
        "tools/setup-git-lfs.bat",
        "tests/DEPLOYMENT_TEST_RESULTS.md",
    ]

    print("[CLEANUP] Removing dev-only files from deployment...")
    removed_count = 0

    for file_path in dev_files:
        full_path = deployment_root / file_path
        try:
            if full_path.is_dir():
                shutil.rmtree(full_path, ignore_errors=True)
                print(f"  [OK] Removed dev directory: {file_path}")
                removed_count += 1
            elif full_path.is_file():
                full_path.unlink(missing_ok=True)
                print(f"  [OK] Removed dev file: {file_path}")
                removed_count += 1
        except Exception as e:
            print(f"  [WARN] Could not remove {file_path}: {e}")

    if removed_count > 0:
        print(f"[OK] Cleaned {removed_count} dev files/directories")
    else:
        print("[OK] No dev files found (deployment already clean)")

def clear_python_cache(root_dir: Path):
    """Clear all Python cache files (.pyc, __pycache__) to ensure new code loads"""
    print("[CACHE] Clearing Python cache files...")
    count = 0

    # Remove __pycache__ directories
    for pycache_dir in root_dir.rglob("__pycache__"):
        try:
            shutil.rmtree(pycache_dir)
            count += 1
        except Exception:
            pass  # Ignore errors, some might be in use

    # Remove .pyc files
    for pyc_file in root_dir.rglob("*.pyc"):
        try:
            pyc_file.unlink()
            count += 1
        except Exception:
            pass

    if count > 0:
        print(f"[OK] Cleared {count} cache files/directories")
    return count

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


def get_version(root: Path) -> Optional[str]:
    """Get version from src/__init__.py"""
    try:
        init_file = root / "src" / "__init__.py"
        if init_file.exists():
            with open(init_file, 'r') as f:
                for line in f:
                    if line.startswith('__version__'):
                        # Extract version string
                        return line.split('=')[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return None


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two semantic version strings.

    Returns:
        1 if v1 > v2
        0 if v1 == v2
        -1 if v1 < v2
    """
    try:
        # Parse semantic versions (e.g., "2.0.0")
        parts1 = [int(x) for x in v1.split('.')]
        parts2 = [int(x) for x in v2.split('.')]

        # Pad to same length
        max_len = max(len(parts1), len(parts2))
        parts1.extend([0] * (max_len - len(parts1)))
        parts2.extend([0] * (max_len - len(parts2)))

        # Compare
        for p1, p2 in zip(parts1, parts2):
            if p1 > p2:
                return 1
            elif p1 < p2:
                return -1
        return 0
    except Exception:
        # If parsing fails, assume equal
        return 0


def is_dev_repo(root: Path) -> bool:
    """Check if this is a dev repo (has .git and .deployments_registry.json)"""
    return (root / ".git").exists() and (root / ".deployments_registry.json").exists()


def is_deployed_repo(root: Path) -> bool:
    """Check if this is a deployed repo (has .ue5query_deploy.json)"""
    return (root / ".ue5query_deploy.json").exists()


class UpdateManager:
    """Manages updates for deployed UE5 Source Query installations"""

    def __init__(self, deployment_root: Path, logger=None):
        self.deployment_root = deployment_root
        self.config_file = deployment_root / ".ue5query_deploy.json"
        self.config: Optional[Dict[str, Any]] = None
        self.backup_dir: Optional[Path] = None
        self.logger = logger if logger else print

    def log(self, msg):
        self.logger(msg)

    def load_config(self) -> bool:
        """Load deployment configuration"""
        if not self.config_file.exists():
            self.log(f"[ERROR] Deployment config not found: {self.config_file}")
            self.log("This doesn't appear to be a deployed installation.")
            self.log("Run the GUI installer to deploy first.")
            return False

        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
            self.log(f"[OK] Loaded deployment config")
            return True
        except json.JSONDecodeError as e:
            self.log(f"[ERROR] Failed to parse config: {e}")
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
                self.log(f"[ERROR] Invalid source: {force_source}. Use 'local' or 'remote'.")
                return None
            self.log(f"[CONFIG] Forcing update source: {force_source}")
            return force_source

        # Try local dev repo first
        local_repo = self.config.get("update_sources", {}).get("local_dev_repo")
        if local_repo:
            local_path = Path(local_repo)
            if self._is_valid_dev_repo(local_path):
                self.log(f"[OK] Found local dev repo: {local_path}")
                return 'local'
            else:
                self.log(f"[WARN]  Local dev repo not valid: {local_path}")

        # Fall back to remote
        remote_repo = self.config.get("update_sources", {}).get("remote_repo")
        if remote_repo:
            self.log(f"[REMOTE] Using remote repo: {remote_repo}")
            return 'remote'

        self.log("[ERROR] No update source available!")
        self.log("Configure local_dev_repo or remote_repo in .ue5query_deploy.json")
        return None

    def _is_valid_dev_repo(self, path: Path) -> bool:
        """Check if path is a valid UE5 Source Query dev repo"""
        if not path.exists():
            return False

        # Check for key files
        has_core = (path / "src" / "core" / "hybrid_query.py").exists() or \
                   (path / "ue5_query" / "core" / "hybrid_query.py").exists()
        
        required_files = [
            path / "installer" / "gui_deploy.py",
            path / "README.md"
        ]
        return has_core and all(f.exists() for f in required_files)

    def create_backup(self) -> bool:
        """Create backup before update"""
        import uuid
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Add unique suffix to avoid collisions in rapid updates
        unique_id = str(uuid.uuid4())[:8]
        self.backup_dir = self.deployment_root / "backups" / f"backup_{timestamp}_{unique_id}"

        self.log(f"[BACKUP] Creating backup: {self.backup_dir}")

        try:
            self.backup_dir.mkdir(parents=True, exist_ok=False)

            # Backup critical directories
            for dir_name in ["ue5_query", "src", "installer", "tools", "tests"]:
                src_dir = self.deployment_root / dir_name
                if src_dir.exists():
                    shutil.copytree(src_dir, self.backup_dir / dir_name)

            # Backup config
            if self.config_file.exists():
                shutil.copy2(self.config_file, self.backup_dir / ".ue5query_deploy.json")

            self.log(f"[OK] Backup created successfully")
            return True

        except Exception as e:
            self.log(f"[ERROR] Backup failed: {e}")
            return False

    def update_from_local(self, dry_run: bool = False) -> bool:
        """Update from local dev repo"""
        local_repo = Path(self.config["update_sources"]["local_dev_repo"])
        self.log(f"\n[UPDATE] Updating from local dev repo: {local_repo}")

        if not self._is_valid_dev_repo(local_repo):
            self.log(f"[ERROR] Invalid dev repo: {local_repo}")
            return False

        # Clean dev-only files from deployment before updating
        clean_dev_files(self.deployment_root)

        # Directories to sync
        sync_dirs = ["ue5_query", "src", "installer", "tools", "tests", "docs", "examples"]

        exclude_patterns = DEFAULT_EXCLUDES + DEPLOYMENT_EXCLUDES + self.config.get("exclude_patterns", [])

        if dry_run:
            self.log("\n[CHECK] DRY RUN - Would update:")
            for dir_name in sync_dirs:
                src = local_repo / dir_name
                if src.exists():
                    self.log(f"  - {dir_name}/")
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
                    self.log(f"[WARN]  Skipping {dir_name}/ (not found in source)")
                    continue

                self.log(f"[DIR] Syncing {dir_name}/...")

                # Remove existing directory (except preserved files)
                if dst_dir.exists():
                    self._safe_remove_dir(dst_dir)

                # Filter exclusion patterns for this directory
                # Convert "src/research" → "research" when syncing src/
                dir_specific_patterns = []
                for pattern in exclude_patterns:
                    if "/" in pattern or "\\" in pattern:
                        # Path-based pattern - check if it applies to this directory
                        norm_pattern = pattern.replace("\\", "/")
                        if norm_pattern.startswith(f"{dir_name}/"):
                            # Strip directory prefix: "src/research" → "research"
                            relative_pattern = norm_pattern[len(dir_name)+1:]
                            dir_specific_patterns.append(relative_pattern)
                    else:
                        # Simple filename pattern - apply to all directories
                        dir_specific_patterns.append(pattern)

                # Copy new version
                shutil.copytree(
                    src_dir,
                    dst_dir,
                    ignore=shutil.ignore_patterns(*dir_specific_patterns) if dir_specific_patterns else None
                )

            # Copy root files
            for file_name in ["README.md", "requirements.txt", "ask.bat", "launcher.bat", "Setup.bat", "bootstrap.py"]:
                src_file = local_repo / file_name
                dst_file = self.deployment_root / file_name
                if src_file.exists():
                    shutil.copy2(src_file, dst_file)
                    self.log(f"[FILE] Updated {file_name}")

            # Restore preserved files from backup
            self._restore_preserved_files()

            # Update deployment config
            self._update_deployment_info("local", local_repo)

            # Clear Python cache to ensure new code loads
            self.log("")
            clear_python_cache(self.deployment_root)

            # Run post-update tasks (e.g. package installation)
            self._post_update_tasks()

            # Create restart marker for running GUIs
            marker_file = self.deployment_root / ".needs_restart"
            try:
                from datetime import datetime
                marker_file.write_text(f"Updated at {datetime.now().isoformat()}")
                self.log("[NOTIFY] Created restart marker for running GUIs")
            except Exception as e:
                self.log(f"[WARN] Could not create restart marker: {e}")

            self.log("\n[OK] Local update completed successfully!")
            return True

        except Exception as e:
            self.log(f"\n[ERROR] Update failed: {e}")
            self.log("Attempting rollback...")
            self._rollback()
            return False

    def update_from_remote(self, dry_run: bool = False) -> bool:
        """Update from remote GitHub repo"""
        remote_repo = self.config["update_sources"]["remote_repo"]
        branch = self.config["update_sources"].get("branch", "master")

        self.log(f"\n[REMOTE] Updating from remote repo: {remote_repo}")
        self.log(f"Branch: {branch}")

        if dry_run:
            self.log("\n[CHECK] DRY RUN - Would fetch from remote")
            return True

        # Create temporary directory for git clone
        temp_dir = self.deployment_root / "temp_update"

        # Force cleanup of any existing temp directory for fresh clone
        robust_rmtree(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Always clone fresh for reliability
            self.log("[DOWNLOAD] Cloning repository...")
            subprocess.run(
                ["git", "clone", "-b", branch, remote_repo, str(temp_dir)],
                check=True,
                capture_output=True
            )

            # Clean dev-only files from deployment before updating
            clean_dev_files(self.deployment_root)

            # Create backup
            if not self.create_backup():
                return False

            # Copy files from temp to deployment
            self.log("[UPDATE] Installing update...")
            exclude_patterns = DEFAULT_EXCLUDES + DEPLOYMENT_EXCLUDES + self.config.get("exclude_patterns", [])

            for dir_name in ["ue5_query", "src", "installer", "tools", "tests", "docs", "examples"]:
                src_dir = temp_dir / dir_name
                dst_dir = self.deployment_root / dir_name

                if src_dir.exists():
                    if dst_dir.exists():
                        self._safe_remove_dir(dst_dir)

                    # Filter exclusion patterns for this directory
                    # Convert "src/research" → "research" when syncing src/
                    dir_specific_patterns = []
                    for pattern in exclude_patterns:
                        if "/" in pattern or "\\" in pattern:
                            # Path-based pattern - check if it applies to this directory
                            norm_pattern = pattern.replace("\\", "/")
                            if norm_pattern.startswith(f"{dir_name}/"):
                                # Strip directory prefix: "src/research" → "research"
                                relative_pattern = norm_pattern[len(dir_name)+1:]
                                dir_specific_patterns.append(relative_pattern)
                        else:
                            # Simple filename pattern - apply to all directories
                            dir_specific_patterns.append(pattern)

                    shutil.copytree(
                        src_dir,
                        dst_dir,
                        ignore=shutil.ignore_patterns(*dir_specific_patterns) if dir_specific_patterns else None
                    )
                    self.log(f"[OK] Updated {dir_name}/")

            # Restore preserved files
            self._restore_preserved_files()

            # Update deployment config
            self._update_deployment_info("remote", remote_repo)

            # Clear Python cache to ensure new code loads
            self.log("")
            clear_python_cache(self.deployment_root)

            # Run post-update tasks (e.g. package installation)
            self._post_update_tasks()

            # Create restart marker for running GUIs
            marker_file = self.deployment_root / ".needs_restart"
            try:
                from datetime import datetime
                marker_file.write_text(f"Updated at {datetime.now().isoformat()}")
                self.log("[NOTIFY] Created restart marker for running GUIs")
            except Exception as e:
                self.log(f"[WARN] Could not create restart marker: {e}")

            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)

            self.log("\n[OK] Remote update completed successfully!")
            return True

        except subprocess.CalledProcessError as e:
            self.log(f"\n[ERROR] Git command failed: {e}")
            self.log(e.stderr.decode() if e.stderr else "")
            return False
        except Exception as e:
            self.log(f"\n[ERROR] Update failed: {e}")
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
                self.log(f"[PRESERVE] Restored preserved file: {file_path}")

    def _post_update_tasks(self):
        """Run post-update maintenance tasks (e.g., package installation)"""
        pyproject = self.deployment_root / "pyproject.toml"
        if pyproject.exists():
            self.log("\n[SETUP] Updating package installation...")
            try:
                # Determine python executable to use (venv or system)
                # Look for venv first
                venv_python = self.deployment_root / ".venv" / "Scripts" / "python.exe"
                if venv_python.exists():
                    python_exe = str(venv_python)
                else:
                    import sys
                    python_exe = sys.executable

                subprocess.run(
                    [python_exe, "-m", "pip", "install", "-e", "."],
                    cwd=str(self.deployment_root),
                    check=True,
                    capture_output=True
                )
                self.log("[OK] Package installed in editable mode")
            except subprocess.CalledProcessError as e:
                self.log(f"[WARN] Failed to install package: {e}")
                self.log("       (The tool will still work via compatibility imports)")
            except Exception as e:
                self.log(f"[WARN] Error during post-update setup: {e}")

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
            self.log("[ERROR] No backup available for rollback!")
            return False

        try:
            self.log(f"[ROLLBACK]  Rolling back from: {self.backup_dir}")

            for dir_name in ["ue5_query", "src", "installer", "tools", "tests", "examples"]:
                backup_src = self.backup_dir / dir_name
                if backup_src.exists():
                    dest = self.deployment_root / dir_name
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(backup_src, dest)

            self.log("[OK] Rollback successful")
            return True

        except Exception as e:
            self.log(f"[ERROR] Rollback failed: {e}")
            return False

    def check_for_updates(self, source: str) -> Optional[Dict[str, Any]]:
        """
        Check if updates are available without applying them.

        Returns:
            Dict with keys: 'available', 'current_version', 'source_version', 'source'
        """
        current_version = get_version(self.deployment_root)
        source_version = None

        if source == "local":
            local_repo = Path(self.config["update_sources"]["local_dev_repo"])
            source_version = get_version(local_repo)
        elif source == "remote":
            # For remote, we'd need to fetch version without full clone
            # Simplified: assume updates available
            source_version = "remote"

        result = {
            'current_version': current_version or "unknown",
            'source_version': source_version or "unknown",
            'source': source
        }

        if current_version and source_version and source_version != "remote":
            result['available'] = compare_versions(source_version, current_version) > 0
        else:
            result['available'] = True  # Assume updates available if can't determine

        return result

    def push_to_deployment(self, target_path: Path, dry_run: bool = False, force: bool = False) -> bool:
        """
        Push updates from dev repo to a single deployment.

        Args:
            target_path: Path to deployment directory
            dry_run: If True, only show what would be updated
            force: If True, push even if versions are same (incremental update)

        Returns:
            True if successful
        """
        if not is_deployed_repo(target_path):
            self.log(f"[ERROR] {target_path} is not a deployed installation")
            return False

        # Get versions
        source_version = get_version(Path.cwd())
        target_version = get_version(target_path)

        self.log(f"\n[PUSH] {target_path}")
        self.log(f"  Source: {source_version or 'unknown'}")
        self.log(f"  Target: {target_version or 'unknown'}")

        if source_version and target_version and not force:
            comparison = compare_versions(source_version, target_version)
            if comparison == 0:
                self.log(f"  [SKIP] Already up-to-date (use --force for incremental push)")
                return True
            elif comparison < 0:
                self.log(f"  [WARN] Target is newer than source!")
        elif force and source_version == target_version:
            self.log(f"  [FORCE] Incremental push (same version)")

        if dry_run:
            self.log(f"  [DRY-RUN] Would update files")
            return True

        # Create temporary UpdateManager for this deployment
        # Pass the same logger to the temporary manager
        temp_manager = UpdateManager(target_path, logger=self.logger)
        if not temp_manager.load_config():
            return False

        # Use local update method
        return temp_manager.update_from_local(dry_run=False)

    def push_to_all_deployments(self, dry_run: bool = False, force: bool = False) -> int:
        """
        Push updates from dev repo to ALL tracked deployments.

        Args:
            dry_run: If True, only show what would be updated
            force: If True, push even if versions are same (incremental update)

        Returns:
            Number of deployments successfully updated
        """
        dev_root = Path.cwd()
        registry_file = dev_root / ".deployments_registry.json"

        if not registry_file.exists():
            self.log("[ERROR] No deployments registry found")
            self.log("This doesn't appear to be a dev repo.")
            return 0

        try:
            with open(registry_file, 'r') as f:
                registry = json.load(f)
        except Exception as e:
            self.log(f"[ERROR] Failed to read registry: {e}")
            return 0

        deployments_dict = registry.get('deployments', {})
        if not deployments_dict:
            self.log("[INFO] No deployments tracked")
            return 0

        self.log(f"\n[PUSH-ALL] Updating {len(deployments_dict)} deployment(s)\n")

        success_count = 0
        for deploy_id, deploy_info in deployments_dict.items():
            deploy_path = Path(deploy_info['path'])
            if deploy_path.exists():
                if self.push_to_deployment(deploy_path, dry_run, force):
                    success_count += 1
            else:
                self.log(f"[WARN] Deployment not found: {deploy_path}")

        self.log(f"\n[SUMMARY] Updated {success_count}/{len(deployments_dict)} deployments")
        return success_count

    def verify_installation(self) -> bool:
        """Verify installation after update"""
        self.log("\n[CHECK] Verifying installation...")

        # Support both new and old structure
        prefix = "ue5_query"
        if (self.deployment_root / "src").exists() and not (self.deployment_root / "ue5_query").exists():
            prefix = "src"

        checks = [
            ("Core module", self.deployment_root / prefix / "core" / "hybrid_query.py"),
            ("Query engine", self.deployment_root / prefix / "core" / "query_engine.py"),
            ("CLI client", self.deployment_root / prefix / "utils" / "cli_client.py"),
            ("Config file", self.config_file),
        ]

        all_ok = True
        for name, path in checks:
            if path.exists():
                self.log(f"  [OK] {name}")
            else:
                self.log(f"  [ERROR] {name} - MISSING!")
                all_ok = False

        return all_ok


def main():
    parser = argparse.ArgumentParser(
        description="Bidirectional Update System for UE5 Source Query",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # From deployed repo - pull updates
  python tools/update.py
  python tools/update.py --check
  python tools/update.py --source local

  # From dev repo - push to deployments
  python tools/update.py --push-all
  python tools/update.py --push /path/to/deployment
        """
    )

    # Pull mode arguments (for deployed repos)
    parser.add_argument("--source", choices=["local", "remote"], help="Force update source (pull mode)")
    parser.add_argument("--check", action="store_true", help="Check for updates without applying")

    # Push mode arguments (for dev repos)
    parser.add_argument("--push-all", action="store_true", help="Push updates to all tracked deployments (dev repo only)")
    parser.add_argument("--push", type=str, metavar="PATH", help="Push updates to specific deployment (dev repo only)")

    # General arguments
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without applying")
    parser.add_argument("--force", action="store_true", help="Force update even if versions match")

    args = parser.parse_args()

    print("=" * 70)
    print("UE5 Source Query - Bidirectional Update System")
    print("=" * 70)

    current_root = Path.cwd()
    print(f"\nCurrent directory: {current_root}")

    # Detect environment
    is_dev = is_dev_repo(current_root)
    is_deployed = is_deployed_repo(current_root)

    if is_dev:
        print("[MODE] Development Repository")
        current_version = get_version(current_root)
        print(f"Version: {current_version or 'unknown'}\n")
    elif is_deployed:
        print("[MODE] Deployed Installation")
        current_version = get_version(current_root)
        print(f"Version: {current_version or 'unknown'}\n")
    else:
        print("[ERROR] Unknown repository type")
        print("This doesn't appear to be a dev repo or deployed installation.")
        return 1

    # === PUSH MODE (Dev Repo → Deployments) ===
    if args.push_all or args.push:
        if not is_dev:
            print("[ERROR] Push mode only works from development repository")
            return 1

        manager = UpdateManager(current_root)  # Dummy manager for push methods

        if args.push_all:
            success_count = manager.push_to_all_deployments(dry_run=args.dry_run, force=args.force)
            return 0 if success_count > 0 else 1

        elif args.push:
            target_path = Path(args.push).resolve()
            success = manager.push_to_deployment(target_path, dry_run=args.dry_run, force=args.force)
            return 0 if success else 1

    # === PULL MODE (Deployed Repo ← Source) ===
    if not is_deployed:
        print("[ERROR] Pull mode only works from deployed installation")
        print("Use --push-all or --push from development repository")
        return 1

    manager = UpdateManager(current_root)

    # Load deployment config
    if not manager.load_config():
        return 1

    # Check for updates
    if args.check:
        print("\n[CHECK] Checking for updates...")
        source = manager.detect_update_source(args.source)
        if not source:
            return 1

        update_info = manager.check_for_updates(source)
        print(f"\n  Current: {update_info['current_version']}")
        print(f"  Source:  {update_info['source_version']} ({update_info['source']})")

        if update_info['available']:
            print(f"\n  [!] Updates available")
            print(f"\nRun without --check to apply updates")
        else:
            print(f"\n  [OK] Already up-to-date")

        return 0

    # Detect update source
    source = manager.detect_update_source(args.source)
    if not source:
        return 1

    # Check version before updating (skip if --force)
    if not args.force:
        update_info = manager.check_for_updates(source)
        if not update_info['available']:
            print(f"\n[INFO] Already up-to-date (version {update_info['current_version']})")
            print(f"Use --force to update anyway\n")
            return 0

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
            print("\n[WARN] Verification failed! Installation may be incomplete.")
            return 1

        print("\n" + "=" * 70)
        print("[OK] Update completed successfully!")
        print("=" * 70)

    return 0


if __name__ == "__main__":
    exit(main())
