"""
Bidirectional Deployment Detection System
Discovers connections between dev repos and deployed distributions.

Features:
- Dev repo -> Find all deployments updating from it
- Deployment -> Find source dev repo (or fall back to remote)
- Deployment registry for tracking connections
- Self-repairing logic for broken links
- Handles all edge cases (missing paths, moved repos, etc.)
"""

import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib


@dataclass
class DeploymentInfo:
    """Information about a deployment"""
    path: str
    deployed_from: str
    deployed_at: str
    last_updated: Optional[str] = None
    is_valid: bool = True
    issues: List[str] = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []


@dataclass
class EnvironmentInfo:
    """Complete environment information"""
    current_path: str
    environment_type: str  # 'dev_repo' or 'deployed'
    is_valid: bool
    dev_repo_path: Optional[str] = None
    deployments: List[DeploymentInfo] = None
    remote_repo: Optional[str] = None
    can_update: bool = False
    issues: List[str] = None

    def __post_init__(self):
        if self.deployments is None:
            self.deployments = []
        if self.issues is None:
            self.issues = []


class DeploymentRegistry:
    """
    Manages registry of deployment connections.

    Registry file: <dev_repo>/.deployments_registry.json
    Tracks all deployments that update from this dev repo.
    """

    def __init__(self, dev_repo_path: Path):
        self.dev_repo_path = dev_repo_path
        self.registry_file = dev_repo_path / ".deployments_registry.json"
        self.deployments: Dict[str, DeploymentInfo] = {}
        self.load()

    def load(self):
        """Load registry from file"""
        if not self.registry_file.exists():
            return

        try:
            with open(self.registry_file, 'r') as f:
                data = json.load(f)

            # Convert dict entries to DeploymentInfo objects
            for deploy_id, deploy_data in data.get("deployments", {}).items():
                self.deployments[deploy_id] = DeploymentInfo(**deploy_data)
        except Exception as e:
            print(f"[WARN] Failed to load deployment registry: {e}")

    def save(self):
        """Save registry to file"""
        data = {
            "dev_repo": str(self.dev_repo_path),
            "last_updated": datetime.now().isoformat(),
            "deployments": {
                deploy_id: asdict(info)
                for deploy_id, info in self.deployments.items()
            }
        }

        try:
            with open(self.registry_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[WARN] Failed to save deployment registry: {e}")

    def register_deployment(self, deployment_path: Path):
        """Register a new deployment"""
        deploy_id = self._get_deployment_id(deployment_path)

        # Check if deployment has config file
        config_file = deployment_path / ".ue5query_deploy.json"
        if not config_file.exists():
            return

        try:
            with open(config_file, 'r') as f:
                config = json.load(f)

            deploy_info = DeploymentInfo(
                path=str(deployment_path),
                deployed_from=config.get("deployment_info", {}).get("deployed_from", ""),
                deployed_at=config.get("deployment_info", {}).get("deployed_at", ""),
                last_updated=config.get("deployment_info", {}).get("last_updated"),
                is_valid=True
            )

            self.deployments[deploy_id] = deploy_info
            self.save()
        except Exception as e:
            print(f"[WARN] Failed to register deployment: {e}")

    def unregister_deployment(self, deployment_path: Path):
        """Remove deployment from registry"""
        deploy_id = self._get_deployment_id(deployment_path)
        if deploy_id in self.deployments:
            del self.deployments[deploy_id]
            self.save()

    def get_all_deployments(self, validate: bool = True) -> List[DeploymentInfo]:
        """
        Get all registered deployments.

        Args:
            validate: Check if deployments still exist

        Returns:
            List of DeploymentInfo objects
        """
        deployments = list(self.deployments.values())

        if validate:
            # Validate each deployment
            for deploy in deployments:
                deploy_path = Path(deploy.path)
                deploy.issues = []

                # Check if path exists
                if not deploy_path.exists():
                    deploy.is_valid = False
                    deploy.issues.append(f"Path not found: {deploy_path}")
                    continue

                # Check if config file exists
                config_file = deploy_path / ".ue5query_deploy.json"
                if not config_file.exists():
                    deploy.is_valid = False
                    deploy.issues.append("Deployment config missing")
                    continue

                # Check if core module exists
                core_module = deploy_path / "src" / "core" / "hybrid_query.py"
                if not core_module.exists():
                    deploy.is_valid = False
                    deploy.issues.append("Core module missing")

            # Update registry with validation results
            self.save()

        return deployments

    def cleanup_invalid(self):
        """Remove invalid deployments from registry"""
        valid_ids = [
            deploy_id for deploy_id, info in self.deployments.items()
            if info.is_valid
        ]

        self.deployments = {
            deploy_id: info
            for deploy_id, info in self.deployments.items()
            if deploy_id in valid_ids
        }

        self.save()

    @staticmethod
    def _get_deployment_id(deployment_path: Path) -> str:
        """Generate unique ID for deployment based on path"""
        path_str = str(deployment_path.resolve())
        return hashlib.md5(path_str.encode()).hexdigest()[:12]


class DeploymentDetector:
    """
    Bidirectional deployment detection system.

    Capabilities:
    - Detect environment type (dev repo or deployed)
    - From dev repo: Find all deployments
    - From deployment: Find source dev repo
    - Self-repair broken connections
    - Handle all edge cases
    """

    def __init__(self, start_path: Optional[Path] = None):
        """
        Initialize detector.

        Args:
            start_path: Starting directory (default: cwd)
        """
        self.start_path = Path(start_path) if start_path else Path.cwd()
        self.root = self._find_project_root()
        self.env_type = self._detect_environment_type()
        self.env_info = self._build_environment_info()

    def _find_project_root(self) -> Path:
        """
        Find project root by walking up directory tree.

        Looks for:
        - .git/ (dev repo marker)
        - .ue5query_deploy.json (deployment marker)
        - src/core/hybrid_query.py (both)

        Returns:
            Path to project root, or start_path if not found
        """
        current = self.start_path.resolve()

        for _ in range(15):  # Max depth
            # Dev repo marker
            if (current / ".git").exists() and (current / "installer" / "gui_deploy.py").exists():
                return current

            # Deployment marker
            if (current / ".ue5query_deploy.json").exists():
                return current

            # Core module (both environments)
            if (current / "src" / "core" / "hybrid_query.py").exists():
                return current

            # Move up
            parent = current.parent
            if parent == current:  # Filesystem root
                break
            current = parent

        return self.start_path

    def _detect_environment_type(self) -> str:
        """
        Detect if current location is dev repo or deployment.

        Returns:
            'dev_repo', 'deployed', or 'unknown'
        """
        # Dev repo has .git and installer/
        has_git = (self.root / ".git").exists()
        has_installer = (self.root / "installer" / "gui_deploy.py").exists()
        has_tests = (self.root / "tests").exists()

        if has_git and has_installer:
            return "dev_repo"

        # Deployment has config and no .git
        has_deploy_config = (self.root / ".ue5query_deploy.json").exists()

        if has_deploy_config and not has_git:
            return "deployed"

        # Ambiguous - try to infer
        has_core = (self.root / "src" / "core" / "hybrid_query.py").exists()

        if has_core:
            # Has core module but unclear which type
            if has_tests:
                return "dev_repo"  # Tests suggest dev repo
            return "deployed"  # Assume deployed

        return "unknown"

    def _build_environment_info(self) -> EnvironmentInfo:
        """
        Build complete environment information.

        Returns:
            EnvironmentInfo object with all details
        """
        env_info = EnvironmentInfo(
            current_path=str(self.root),
            environment_type=self.env_type,
            is_valid=True
        )

        if self.env_type == "dev_repo":
            env_info = self._build_dev_repo_info(env_info)
        elif self.env_type == "deployed":
            env_info = self._build_deployment_info(env_info)
        else:
            env_info.is_valid = False
            env_info.issues.append("Unknown environment type")

        return env_info

    def _build_dev_repo_info(self, env_info: EnvironmentInfo) -> EnvironmentInfo:
        """Build info for dev repo environment"""
        env_info.dev_repo_path = str(self.root)

        # Load deployment registry
        registry = DeploymentRegistry(self.root)
        env_info.deployments = registry.get_all_deployments(validate=True)

        # Detect git remote
        try:
            import subprocess
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                env_info.remote_repo = result.stdout.strip()
        except:
            pass

        # Can't update dev repo itself
        env_info.can_update = False

        return env_info

    def _build_deployment_info(self, env_info: EnvironmentInfo) -> EnvironmentInfo:
        """Build info for deployed environment"""
        config_file = self.root / ".ue5query_deploy.json"

        if not config_file.exists():
            env_info.is_valid = False
            env_info.issues.append("Deployment config missing")
            return env_info

        try:
            with open(config_file, 'r') as f:
                config = json.load(f)

            # Extract update sources
            update_sources = config.get("update_sources", {})
            local_dev_repo = update_sources.get("local_dev_repo")
            remote_repo = update_sources.get("remote_repo")

            # Only try to find dev repo if one is configured
            # Don't auto-discover if user explicitly set to None or didn't configure
            dev_repo_path = None
            if local_dev_repo:  # Only if explicitly configured (not None)
                dev_repo_path = self._find_dev_repo(local_dev_repo)

            if dev_repo_path:
                env_info.dev_repo_path = str(dev_repo_path)
                env_info.can_update = True

                # Register this deployment with dev repo
                self._register_with_dev_repo(dev_repo_path)
            elif remote_repo:
                env_info.remote_repo = remote_repo
                env_info.can_update = True
            else:
                env_info.issues.append("No update source available")
                env_info.can_update = False

        except Exception as e:
            env_info.is_valid = False
            env_info.issues.append(f"Failed to read deployment config: {e}")

        return env_info

    def _find_dev_repo(self, configured_path: Optional[str]) -> Optional[Path]:
        """
        Find dev repo using multiple strategies.

        Strategies:
        1. Check configured path (PRIORITY - trust the config!)
        2. Search common locations (only if configured path invalid)
        3. Search parent directories (only if no config)
        4. Search sibling directories (last resort)

        Args:
            configured_path: Path from deployment config

        Returns:
            Path to dev repo if found, None otherwise
        """
        # Strategy 1: Configured path - HIGHEST PRIORITY
        # If configured path exists and is valid, use it IMMEDIATELY
        if configured_path:
            configured = Path(configured_path)
            if self._is_valid_dev_repo(configured):
                return configured
            # Configured path invalid but specified - don't search randomly!
            # Only continue if path looks like a placeholder or is clearly wrong
            if configured.exists() or str(configured).startswith("/nonexistent"):
                # Path was real but invalid, or is a placeholder - allow fallback
                pass
            else:
                # Configured path missing - maybe moved, allow search
                pass

        # Strategy 2: Common locations (only if no valid configured path)
        # Look for UE5-Source-Query in common dev locations
        common_locations = [
            Path.home() / "Documents" / "UE5-Source-Query",
            Path.home() / "Dev" / "UE5-Source-Query",
            Path.home() / "Projects" / "UE5-Source-Query",
            Path("D:/DevTools/UE5-Source-Query"),
            Path("C:/DevTools/UE5-Source-Query"),
        ]

        for location in common_locations:
            if self._is_valid_dev_repo(location):
                return location

        # Strategy 3: Parent directories (only if no config specified)
        # Walk up from deployment looking for dev repo
        # ONLY if configured_path was None (not specified at all)
        if configured_path is None:
            current = self.root.parent
            for _ in range(5):
                potential_dev = current / "UE5-Source-Query"
                if self._is_valid_dev_repo(potential_dev):
                    return potential_dev

                # Check if parent itself is dev repo
                if self._is_valid_dev_repo(current):
                    return current

                current = current.parent

        # Strategy 4: Sibling directories (last resort)
        # Only if no config specified
        if configured_path is None and self.root.parent.exists():
            for sibling in self.root.parent.iterdir():
                if sibling.is_dir() and "UE5" in sibling.name:
                    if self._is_valid_dev_repo(sibling):
                        return sibling

        return None

    def _is_valid_dev_repo(self, path: Path) -> bool:
        """
        Check if path is a valid dev repo.

        Args:
            path: Path to check

        Returns:
            True if valid dev repo
        """
        if not path.exists():
            return False

        # Required markers
        required = [
            path / ".git",
            path / "installer" / "gui_deploy.py",
            path / "src" / "core" / "hybrid_query.py",
        ]

        return all(marker.exists() for marker in required)

    def _register_with_dev_repo(self, dev_repo_path: Path):
        """Register current deployment with dev repo registry"""
        try:
            registry = DeploymentRegistry(dev_repo_path)
            registry.register_deployment(self.root)
        except Exception as e:
            print(f"[WARN] Failed to register with dev repo: {e}")

    def is_dev_repo(self) -> bool:
        """Check if current environment is dev repo"""
        return self.env_type == "dev_repo"

    def is_deployed(self) -> bool:
        """Check if current environment is deployed"""
        return self.env_type == "deployed"

    def get_dev_repo_path(self) -> Optional[Path]:
        """Get path to dev repo (from deployment or self)"""
        if self.env_info.dev_repo_path:
            return Path(self.env_info.dev_repo_path)
        return None

    def get_deployments(self) -> List[DeploymentInfo]:
        """Get all deployments (only from dev repo)"""
        return self.env_info.deployments

    def can_update(self) -> bool:
        """Check if current environment can be updated"""
        return self.env_info.can_update

    def get_update_source(self) -> Optional[str]:
        """
        Get best update source.

        Returns:
            'local' if dev repo available, 'remote' if only remote, None otherwise
        """
        if self.env_info.dev_repo_path:
            dev_path = Path(self.env_info.dev_repo_path)
            if dev_path.exists() and self._is_valid_dev_repo(dev_path):
                return "local"

        if self.env_info.remote_repo:
            return "remote"

        return None

    def self_repair(self) -> Tuple[bool, List[str]]:
        """
        Attempt to self-repair broken deployment.

        Returns:
            Tuple of (success, list of actions taken)
        """
        actions = []

        if not self.env_info.is_valid:
            actions.append("[REPAIR] Environment is invalid")

            # Try to repair deployment config
            if self.is_deployed():
                config_file = self.root / ".ue5query_deploy.json"

                if not config_file.exists():
                    actions.append("[REPAIR] Creating missing deployment config")
                    # Create minimal config
                    self._create_minimal_deployment_config()
                    actions.append("[OK] Created deployment config")
                    return (True, actions)

        # Check for missing components
        missing_components = self._get_missing_components()

        if missing_components:
            actions.append(f"[REPAIR] Missing components: {', '.join(missing_components)}")

            # If can update, suggest update
            if self.can_update():
                actions.append("[REPAIR] Run 'update.bat' to restore missing components")
                return (False, actions)
            else:
                actions.append("[ERROR] Cannot auto-repair: No update source available")
                return (False, actions)

        # Try to find dev repo if configured path is broken
        if self.is_deployed() and not self.env_info.dev_repo_path:
            actions.append("[REPAIR] Searching for dev repo...")
            dev_repo = self._find_dev_repo(None)

            if dev_repo:
                actions.append(f"[OK] Found dev repo: {dev_repo}")
                # Update deployment config
                self._update_deployment_config_dev_repo(dev_repo)
                actions.append("[OK] Updated deployment config")
                return (True, actions)

        actions.append("[OK] No repairs needed")
        return (True, actions)

    def _get_missing_components(self) -> List[str]:
        """Get list of missing critical components"""
        missing = []

        critical = [
            ("src/core/hybrid_query.py", "Core module"),
            ("src/core/query_engine.py", "Query engine"),
            ("src/utils/cli_client.py", "CLI client"),
        ]

        for path_str, name in critical:
            if not (self.root / path_str).exists():
                missing.append(name)

        return missing

    def _create_minimal_deployment_config(self):
        """Create minimal deployment config for repair"""
        config = {
            "version": "2.0.0",
            "deployment_info": {
                "deployed_at": datetime.now().isoformat(),
                "deployed_from": "unknown",
                "deployment_method": "self_repair",
                "deployed_to": str(self.root),
            },
            "update_sources": {
                "local_dev_repo": None,
                "remote_repo": "https://github.com/yourusername/UE5-Source-Query.git",
                "branch": "master"
            },
            "update_strategy": "auto",
            "exclude_patterns": [],
            "preserve_local": []
        }

        config_file = self.root / ".ue5query_deploy.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

    def _update_deployment_config_dev_repo(self, dev_repo_path: Path):
        """Update deployment config with found dev repo"""
        config_file = self.root / ".ue5query_deploy.json"

        if not config_file.exists():
            return

        with open(config_file, 'r') as f:
            config = json.load(f)

        config["update_sources"]["local_dev_repo"] = str(dev_repo_path)
        config["deployment_info"]["last_updated"] = datetime.now().isoformat()
        config["deployment_info"]["update_source"] = "self_repair"

        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

    def to_dict(self) -> Dict[str, Any]:
        """Export environment info as dict"""
        return asdict(self.env_info)

    def print_status(self):
        """Print environment status"""
        print("=" * 60)
        print("Deployment Detector Status")
        print("=" * 60)
        print(f"\nCurrent Path: {self.root}")
        print(f"Environment Type: {self.env_type}")
        print(f"Is Valid: {self.env_info.is_valid}")

        if self.env_info.dev_repo_path:
            print(f"\nDev Repo: {self.env_info.dev_repo_path}")

        if self.env_info.remote_repo:
            print(f"Remote Repo: {self.env_info.remote_repo}")

        print(f"\nCan Update: {self.env_info.can_update}")
        if self.env_info.can_update:
            source = self.get_update_source()
            print(f"Update Source: {source}")

        if self.env_info.deployments:
            print(f"\nDeployments ({len(self.env_info.deployments)}):")
            for deploy in self.env_info.deployments:
                status = "[OK]" if deploy.is_valid else "[INVALID]"
                print(f"  {status} {deploy.path}")
                if deploy.issues:
                    for issue in deploy.issues:
                        print(f"      - {issue}")

        if self.env_info.issues:
            print(f"\nIssues:")
            for issue in self.env_info.issues:
                print(f"  - {issue}")

        print("=" * 60)


# Global detector instance
_detector: Optional[DeploymentDetector] = None


def get_detector(refresh: bool = False) -> DeploymentDetector:
    """
    Get global deployment detector instance.

    Args:
        refresh: Force re-detection

    Returns:
        Singleton DeploymentDetector
    """
    global _detector
    if _detector is None or refresh:
        _detector = DeploymentDetector()
    return _detector


def is_dev_repo() -> bool:
    """Check if current environment is dev repo"""
    return get_detector().is_dev_repo()


def is_deployed() -> bool:
    """Check if current environment is deployed"""
    return get_detector().is_deployed()


def get_dev_repo_path() -> Optional[Path]:
    """Get path to dev repo"""
    return get_detector().get_dev_repo_path()


def get_deployments() -> List[DeploymentInfo]:
    """Get all deployments (from dev repo)"""
    return get_detector().get_deployments()


if __name__ == "__main__":
    """Test deployment detection from command line"""
    import sys

    detector = DeploymentDetector()
    detector.print_status()

    # Offer self-repair if issues detected
    if not detector.env_info.is_valid or detector.env_info.issues:
        print("\n[WARN] Issues detected. Attempting self-repair...")
        success, actions = detector.self_repair()

        print("\nRepair Actions:")
        for action in actions:
            print(f"  {action}")

        if success:
            print("\n[OK] Self-repair successful!")
        else:
            print("\n[ERROR] Self-repair failed!")
            sys.exit(1)
