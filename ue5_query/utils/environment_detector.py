"""
Phase 6: Environment Detection System

Comprehensive UE5 engine and project detection with multiple strategies:
- Environment variables
- Config files (.ue5query)
- Windows Registry
- Common install locations
- Recursive search (opt-in)

Features:
- Multi-strategy waterfall detection
- Validation pipeline with health scoring
- Result caching (24hr TTL)
- Better error recovery guidance
"""

import os
import sys
import json
import winreg
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum


class DetectionSource(Enum):
    """Source of detection"""
    ENV_VAR = "environment_variable"
    CONFIG_FILE = "config_file"
    REGISTRY = "windows_registry"
    COMMON_LOC = "common_location"
    RECURSIVE = "recursive_search"
    MANUAL = "manual_entry"


@dataclass
class EngineInstallation:
    """Represents a detected UE5 installation"""
    version: str
    engine_root: Path
    source: DetectionSource
    validated: bool = False
    health_score: float = 0.0
    issues: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.warnings is None:
            self.warnings = []

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "version": self.version,
            "engine_root": str(self.engine_root),
            "path": str(self.engine_root.parent),  # Backward compatibility
            "source": self.source.value,
            "validated": self.validated,
            "health_score": self.health_score,
            "issues": self.issues,
            "warnings": self.warnings
        }


@dataclass
class ProjectInfo:
    """Represents a detected UE5 project"""
    name: str
    project_root: Path
    uproject_file: Path
    source_dirs: List[Path]
    engine_association: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "project_root": str(self.project_root),
            "uproject_file": str(self.uproject_file),
            "source_dirs": [str(d) for d in self.source_dirs],
            "engine_association": self.engine_association
        }


@dataclass
class ValidationResult:
    """Result of validation pipeline"""
    valid: bool
    health_score: float
    issues: List[str]
    warnings: List[str]
    checks_passed: int
    checks_total: int


@dataclass
class CheckResult:
    """Result of a single validation check"""
    passed: bool
    score: float
    issue: Optional[str] = None
    warning: Optional[str] = None


class DetectionStrategy(ABC):
    """Base class for detection strategies"""

    @abstractmethod
    def detect(self) -> List[EngineInstallation]:
        """Run detection and return found installations"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return strategy name for logging"""
        pass


class EnvVarStrategy(DetectionStrategy):
    """Check environment variables for engine path"""

    ENV_VARS = [
        "UE5_ENGINE_PATH",
        "UE_ROOT",
        "UNREAL_ENGINE_PATH",
        "UE5_ROOT",
        "UE_ENGINE_PATH"
    ]

    def get_name(self) -> str:
        return "Environment Variables"

    def detect(self) -> List[EngineInstallation]:
        """Check all known environment variables"""
        installations = []

        for env_var in self.ENV_VARS:
            value = os.environ.get(env_var)
            if not value:
                continue

            engine_path = Path(value)

            # Handle both full engine path and parent directory
            if engine_path.name == "Engine" and engine_path.exists():
                engine_root = engine_path
            elif (engine_path / "Engine").exists():
                engine_root = engine_path / "Engine"
            else:
                continue

            # Extract version from parent directory name
            parent_name = engine_root.parent.name
            version = self._extract_version(parent_name)

            installations.append(EngineInstallation(
                version=version,
                engine_root=engine_root,
                source=DetectionSource.ENV_VAR
            ))

        return installations

    def _extract_version(self, dirname: str) -> str:
        """Extract version from directory name like UE_5.3"""
        if dirname.startswith("UE_"):
            return dirname[3:]
        return dirname


class ConfigFileStrategy(DetectionStrategy):
    """Check .ue5query config files"""

    def get_name(self) -> str:
        return "Config Files"

    def detect(self) -> List[EngineInstallation]:
        """Search for .ue5query files in standard locations"""
        installations = []

        config_files = self._find_config_files()

        for config_path in config_files:
            try:
                config = self._load_config(config_path)
                engine_info = config.get("engine", {})

                if not engine_info:
                    continue

                path = engine_info.get("path")
                if not path:
                    continue

                engine_root = Path(path)
                if not engine_root.exists():
                    continue

                version = engine_info.get("version", self._extract_version(engine_root.parent.name))

                installations.append(EngineInstallation(
                    version=version,
                    engine_root=engine_root,
                    source=DetectionSource.CONFIG_FILE
                ))

            except Exception as e:
                # Silently skip malformed config files
                continue

        return installations

    def _find_config_files(self) -> List[Path]:
        """Find .ue5query files in standard locations"""
        locations = [
            Path.cwd() / ".ue5query",
            Path.home() / ".ue5query",
            Path.cwd().parent / ".ue5query"
        ]

        return [f for f in locations if f.exists() and f.is_file()]

    def _load_config(self, config_path: Path) -> Dict:
        """Load config file (supports JSON and YAML)"""
        content = config_path.read_text(encoding='utf-8')

        # Try JSON first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try YAML if available
        try:
            import yaml
            return yaml.safe_load(content)
        except ImportError:
            # YAML not available, only JSON supported
            pass
        except Exception:
            pass

        return {}

    def _extract_version(self, dirname: str) -> str:
        """Extract version from directory name"""
        if dirname.startswith("UE_"):
            return dirname[3:]
        return dirname


class RegistryStrategy(DetectionStrategy):
    """Check Windows Registry for Epic Games Launcher installs"""

    REGISTRY_PATHS = [
        r"SOFTWARE\EpicGames\Unreal Engine",
        r"SOFTWARE\WOW6432Node\EpicGames\Unreal Engine",
    ]

    def get_name(self) -> str:
        return "Windows Registry"

    def detect(self) -> List[EngineInstallation]:
        """Query Windows Registry"""
        if sys.platform != "win32":
            return []

        installations = []

        for reg_path in self.REGISTRY_PATHS:
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
                i = 0
                while True:
                    try:
                        version = winreg.EnumKey(key, i)
                        subkey = winreg.OpenKey(key, version)
                        try:
                            install_dir, _ = winreg.QueryValueEx(subkey, "InstalledDirectory")
                            engine_root = Path(install_dir) / "Engine"

                            if engine_root.exists():
                                installations.append(EngineInstallation(
                                    version=version,
                                    engine_root=engine_root,
                                    source=DetectionSource.REGISTRY
                                ))
                        except FileNotFoundError:
                            pass
                        finally:
                            winreg.CloseKey(subkey)
                        i += 1
                    except OSError:
                        break
                winreg.CloseKey(key)
            except (PermissionError, FileNotFoundError):
                continue
            except Exception:
                continue

        return installations


class CommonLocStrategy(DetectionStrategy):
    """Search common install locations"""

    def get_name(self) -> str:
        return "Common Locations"

    def detect(self) -> List[EngineInstallation]:
        """Search all common installation directories"""
        installations = []

        search_roots = self._get_search_roots()

        for root in search_roots:
            if not root.exists():
                continue

            # Look for UE_* directories
            try:
                for ue_dir in root.glob("UE_*"):
                    if not ue_dir.is_dir():
                        continue

                    engine_root = ue_dir / "Engine"
                    if engine_root.exists() and engine_root.is_dir():
                        version = ue_dir.name[3:] if ue_dir.name.startswith("UE_") else ue_dir.name

                        installations.append(EngineInstallation(
                            version=version,
                            engine_root=engine_root,
                            source=DetectionSource.COMMON_LOC
                        ))
            except PermissionError:
                continue

        return installations

    def _get_search_roots(self) -> List[Path]:
        """Get list of common search root directories"""
        roots = []

        # Standard locations
        standard = [
            "Program Files/Epic Games",
            "Epic Games",
            "UnrealEngine"
        ]

        # Try all drive letters A-Z
        for i in range(26):
            drive = f"{chr(65+i)}:/"
            for loc in standard:
                roots.append(Path(drive) / loc)

        return roots


class RecursiveSearchStrategy(DetectionStrategy):
    """Deep recursive search (slow, opt-in only)"""

    def __init__(self, max_depth: int = 3, timeout_seconds: int = 5):
        self.max_depth = max_depth
        self.timeout_seconds = timeout_seconds

    def get_name(self) -> str:
        return "Recursive Search"

    def detect(self) -> List[EngineInstallation]:
        """
        Recursive search - NOT implemented by default (too slow)
        This is a placeholder for opt-in deep search
        """
        # TODO: Implement if needed
        return []


class ValidationPipeline:
    """Validate detected engine installations"""

    def validate(self, install: EngineInstallation) -> ValidationResult:
        """Run all validation checks"""
        # First check: Path existence
        path_check = self._check_path_exists(install)
        if not path_check.passed:
            return ValidationResult(
                valid=False,
                health_score=0.0,
                issues=[path_check.issue],
                warnings=[],
                checks_passed=0,
                checks_total=4
            )

        checks = [
            lambda x: path_check, # Already run
            self._check_directory_structure,
            self._check_build_version,
            self._check_source_availability
        ]

        results = []
        # Skip the first one since we already have it
        results.append(path_check)
        for check in checks[1:]:
            results.append(check(install))

        passed_checks = sum(1 for r in results if r.passed)
        total_checks = len(results)

        # Aggregate results
        issues = [r.issue for r in results if r.issue]
        warnings = [r.warning for r in results if r.warning]
        health_score = sum(r.score for r in results) / total_checks if total_checks > 0 else 0.0

        return ValidationResult(
            valid=all(r.passed for r in results),
            health_score=health_score,
            issues=issues,
            warnings=warnings,
            checks_passed=passed_checks,
            checks_total=total_checks
        )

    def _check_path_exists(self, install: EngineInstallation) -> CheckResult:
        """Verify engine root path exists"""
        if install.engine_root.exists() and install.engine_root.is_dir():
            return CheckResult(passed=True, score=1.0)
        return CheckResult(
            passed=False,
            score=0.0,
            issue=f"Engine path does not exist: {install.engine_root}"
        )

    def _check_directory_structure(self, install: EngineInstallation) -> CheckResult:
        """Verify required directories exist"""
        required_dirs = ["Source", "Plugins", "Build"]
        missing = []

        for dirname in required_dirs:
            dir_path = install.engine_root / dirname
            if not dir_path.exists():
                missing.append(dirname)

        if not missing:
            return CheckResult(passed=True, score=1.0)

        # Partial score based on how many directories exist
        score = 1.0 - (len(missing) / len(required_dirs))

        if len(missing) == len(required_dirs):
            return CheckResult(
                passed=False,
                score=score,
                issue=f"Missing required directories: {', '.join(missing)}"
            )

        return CheckResult(
            passed=True,
            score=score,
            warning=f"Missing some directories: {', '.join(missing)}"
        )

    def _normalize_version(self, version: str) -> tuple:
        """Normalize version string to comparable tuple (major, minor, patch)"""
        parts = version.split('.')
        # Pad with zeros if needed
        while len(parts) < 3:
            parts.append('0')
        # Convert to integers for comparison, defaulting to 0 for invalid parts
        try:
            return tuple(int(p) if p.isdigit() else 0 for p in parts[:3])
        except:
            return (0, 0, 0)

    def _versions_match(self, version1: str, version2: str) -> bool:
        """Check if two versions match (ignoring patch differences for display)

        Examples:
            5.3 matches 5.3.0, 5.3.2, 5.3.10
            5.3.2 matches 5.3
            5.4 does NOT match 5.3
        """
        v1 = self._normalize_version(version1)
        v2 = self._normalize_version(version2)

        # Match on major.minor, ignore patch differences
        return v1[0] == v2[0] and v1[1] == v2[1]

    def _check_build_version(self, install: EngineInstallation) -> CheckResult:
        """Check for Build.version file"""
        version_file = install.engine_root / "Build" / "Build.version"

        if version_file.exists():
            try:
                content = json.loads(version_file.read_text())
                major = content.get("MajorVersion", "")
                minor = content.get("MinorVersion", "")
                patch = content.get("PatchVersion", "")

                if major and minor:
                    detected_version = f"{major}.{minor}.{patch}" if patch else f"{major}.{minor}"

                    # Use smart version matching (5.3 == 5.3.0 == 5.3.2)
                    if not self._versions_match(install.version, detected_version):
                        # True mismatch (e.g., 5.3 vs 5.4)
                        return CheckResult(
                            passed=True,
                            score=0.9,
                            warning=f"Version mismatch: detected {detected_version}, labeled as {install.version}"
                        )

                    # Versions match - update to full version for display consistency
                    # Only update if the detected version has more detail
                    if detected_version.count('.') > install.version.count('.'):
                        install.version = detected_version

                    return CheckResult(passed=True, score=1.0)
            except:
                pass

        return CheckResult(
            passed=True,
            score=0.7,
            warning="Could not verify engine version"
        )

    def _check_source_availability(self, install: EngineInstallation) -> CheckResult:
        """Check if source code is available"""
        source_dir = install.engine_root / "Source"

        if not source_dir.exists():
            return CheckResult(
                passed=True,
                score=0.5,
                warning="Source directory not found (binary-only install?)"
            )

        # Check for some expected source files
        runtime_dir = source_dir / "Runtime"
        if runtime_dir.exists():
            return CheckResult(passed=True, score=1.0)

        return CheckResult(
            passed=True,
            score=0.8,
            warning="Source directory structure incomplete"
        )


class EnvironmentDetector:
    """Main detection orchestrator"""

    def __init__(self, cache_file: Optional[Path] = None):
        """
        Initialize detector

        Args:
            cache_file: Path to cache file (default: config/detection_cache.json)
        """
        self.strategies = [
            EnvVarStrategy(),
            ConfigFileStrategy(),
            RegistryStrategy(),
            CommonLocStrategy()
            # RecursiveSearchStrategy() - opt-in only
        ]

        self.validator = ValidationPipeline()
        self.cache_file = cache_file
        self.cache_ttl = timedelta(hours=24)

    def detect_engines(self, use_cache: bool = True, validate: bool = True) -> List[EngineInstallation]:
        """
        Run all detection strategies and return found engines

        Args:
            use_cache: Use cached results if available and fresh
            validate: Run validation pipeline on detected engines

        Returns:
            List of EngineInstallation objects, sorted by health score
        """
        # Try cache first
        if use_cache and self.cache_file:
            cached = self._load_from_cache()
            if cached is not None:
                return cached

        # Run all strategies
        all_installations = []

        for strategy in self.strategies:
            try:
                found = strategy.detect()
                all_installations.extend(found)
            except Exception as e:
                # Log error but continue with other strategies
                print(f"[WARNING] {strategy.get_name()} failed: {e}")
                continue

        # Deduplicate by engine_root
        unique_installs = self._deduplicate(all_installations)

        # Validate if requested
        if validate:
            for install in unique_installs:
                result = self.validator.validate(install)
                install.validated = True
                install.health_score = result.health_score
                install.issues = result.issues
                install.warnings = result.warnings

        # Sort by health score (highest first)
        unique_installs.sort(key=lambda x: x.health_score, reverse=True)

        # Cache results
        if self.cache_file:
            self._save_to_cache(unique_installs)

        return unique_installs

    def detect_projects(self, search_root: Optional[Path] = None) -> List[ProjectInfo]:
        """
        Find .uproject files

        Args:
            search_root: Directory to search (default: current directory)

        Returns:
            List of ProjectInfo objects
        """
        if search_root is None:
            search_root = Path.cwd()

        projects = []

        # Search for .uproject files
        try:
            for uproject_file in search_root.rglob("*.uproject"):
                try:
                    project_info = self._parse_project(uproject_file)
                    if project_info:
                        projects.append(project_info)
                except Exception:
                    continue
        except Exception:
            pass

        return projects

    def _deduplicate(self, installations: List[EngineInstallation]) -> List[EngineInstallation]:
        """Remove duplicates, preferring higher-priority sources"""
        seen = {}

        # Priority order (lower index = higher priority)
        source_priority = {
            DetectionSource.ENV_VAR: 0,
            DetectionSource.CONFIG_FILE: 1,
            DetectionSource.REGISTRY: 2,
            DetectionSource.COMMON_LOC: 3,
            DetectionSource.RECURSIVE: 4,
            DetectionSource.MANUAL: 5
        }

        for install in installations:
            key = str(install.engine_root.resolve())

            if key not in seen:
                seen[key] = install
            else:
                # Keep the one with higher priority
                existing = seen[key]
                if source_priority[install.source] < source_priority[existing.source]:
                    seen[key] = install

        return list(seen.values())

    def _parse_project(self, uproject_file: Path) -> Optional[ProjectInfo]:
        """Parse .uproject file and extract info"""
        try:
            content = json.loads(uproject_file.read_text())

            project_root = uproject_file.parent
            name = uproject_file.stem

            # Find source directories
            source_dirs = []
            source_dir = project_root / "Source"
            if source_dir.exists():
                source_dirs.append(source_dir)

            # Check for plugins with source
            plugins_dir = project_root / "Plugins"
            if plugins_dir.exists():
                for plugin_dir in plugins_dir.iterdir():
                    plugin_source = plugin_dir / "Source"
                    if plugin_source.exists():
                        source_dirs.append(plugin_source)

            engine_association = content.get("EngineAssociation")

            return ProjectInfo(
                name=name,
                project_root=project_root,
                uproject_file=uproject_file,
                source_dirs=source_dirs,
                engine_association=engine_association
            )
        except Exception:
            return None

    def _load_from_cache(self) -> Optional[List[EngineInstallation]]:
        """Load cached detection results"""
        if not self.cache_file or not self.cache_file.exists():
            return None

        try:
            cache_data = json.loads(self.cache_file.read_text())

            # Check cache age
            last_scan = datetime.fromisoformat(cache_data.get("last_scan", ""))
            if datetime.now() - last_scan > self.cache_ttl:
                return None  # Cache expired

            # Reconstruct installations
            installations = []
            for item in cache_data.get("engines", []):
                install = EngineInstallation(
                    version=item["version"],
                    engine_root=Path(item["engine_root"]),
                    source=DetectionSource(item["source"]),
                    validated=item.get("validated", False),
                    health_score=item.get("health_score", 0.0),
                    issues=item.get("issues", []),
                    warnings=item.get("warnings", [])
                )
                installations.append(install)

            return installations
        except Exception:
            return None

    def _save_to_cache(self, installations: List[EngineInstallation]):
        """Save detection results to cache"""
        if not self.cache_file:
            return

        # Ensure cache directory exists
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

        cache_data = {
            "last_scan": datetime.now().isoformat(),
            "engines": [inst.to_dict() for inst in installations]
        }

        try:
            self.cache_file.write_text(json.dumps(cache_data, indent=2))
        except Exception as e:
            # Silently fail - caching is not critical
            pass


def get_detector(script_dir: Optional[Path] = None) -> EnvironmentDetector:
    """
    Factory function to create EnvironmentDetector with proper cache path

    Args:
        script_dir: Root directory of the script (for cache location)

    Returns:
        Configured EnvironmentDetector instance
    """
    if script_dir is None:
        script_dir = Path(__file__).parent.parent

    cache_file = script_dir / "config" / "detection_cache.json"
    return EnvironmentDetector(cache_file=cache_file)


if __name__ == "__main__":
    # CLI test interface
    import argparse

    parser = argparse.ArgumentParser(description="UE5 Environment Detector")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--no-cache", action="store_true", help="Bypass cache")
    parser.add_argument("--projects", action="store_true", help="Detect projects instead")

    args = parser.parse_args()

    detector = get_detector()

    if args.projects:
        projects = detector.detect_projects()

        if args.json:
            print(json.dumps([p.to_dict() for p in projects], indent=2))
        else:
            print(f"\nFound {len(projects)} project(s):\n")
            for proj in projects:
                print(f"  {proj.name}")
                print(f"    Path: {proj.project_root}")
                print(f"    Engine: {proj.engine_association or 'Unknown'}")
                print()
    else:
        installations = detector.detect_engines(use_cache=not args.no_cache)

        if args.json:
            print(json.dumps([inst.to_dict() for inst in installations], indent=2))
        else:
            print(f"\nFound {len(installations)} engine installation(s):\n")
            for inst in installations:
                print(f"  {inst.version}")
                print(f"    Path: {inst.engine_root}")
                print(f"    Source: {inst.source.value}")
                print(f"    Health: {inst.health_score:.0%}")
                if inst.warnings:
                    print(f"    Warnings: {', '.join(inst.warnings)}")
                if inst.issues:
                    print(f"    Issues: {', '.join(inst.issues)}")
                print()
