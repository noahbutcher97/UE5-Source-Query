"""
Comprehensive installation verification script for UE5 Source Query Tool.
Validates all components are correctly installed and functional.

Usage:
    python verify_installation.py [--verbose]

Exit codes:
    0 - All checks passed
    1 - One or more critical checks failed
    2 - Warnings only (non-critical issues)
"""

import sys
import json
from pathlib import Path
from typing import Tuple, List, Optional


class HealthCheckResult:
    """Result of a health check"""
    def __init__(self, name: str, passed: bool, message: str, is_critical: bool = True):
        self.name = name
        self.passed = passed
        self.message = message
        self.is_critical = is_critical


def get_script_root() -> Path:
    """Get the root directory of the installation"""
    # This file is in src/utils/, so go up two levels
    return Path(__file__).parent.parent.parent


def verify_python_version() -> HealthCheckResult:
    """Check Python >= 3.8"""
    try:
        version_info = sys.version_info
        version_str = f"{version_info.major}.{version_info.minor}.{version_info.micro}"

        if version_info.major < 3 or (version_info.major == 3 and version_info.minor < 8):
            return HealthCheckResult(
                "Python Version",
                False,
                f"Python 3.8+ required, found {version_str}. Please upgrade Python.",
                is_critical=True
            )

        return HealthCheckResult(
            "Python Version",
            True,
            f"Python {version_str} (compatible)",
            is_critical=True
        )
    except Exception as e:
        return HealthCheckResult(
            "Python Version",
            False,
            f"Failed to check Python version: {e}",
            is_critical=True
        )


def verify_virtual_environment() -> HealthCheckResult:
    """Check venv exists and is functional"""
    root = get_script_root()
    venv_python = root / ".venv" / "Scripts" / "python.exe"

    if not venv_python.exists():
        return HealthCheckResult(
            "Virtual Environment",
            False,
            f"Virtual environment not found at {venv_python}. Run install.bat or configure.bat.",
            is_critical=True
        )

    # Check if it's executable
    if not venv_python.is_file():
        return HealthCheckResult(
            "Virtual Environment",
            False,
            f"Virtual environment Python is not a file: {venv_python}",
            is_critical=True
        )

    return HealthCheckResult(
        "Virtual Environment",
        True,
        f"Virtual environment found at {venv_python}",
        is_critical=True
    )


def verify_required_packages() -> HealthCheckResult:
    """Test imports of all required packages"""
    required_packages = [
        ("sentence_transformers", "sentence-transformers"),
        ("anthropic", "anthropic"),
        ("numpy", "numpy"),
    ]

    missing = []
    for module_name, package_name in required_packages:
        try:
            __import__(module_name)
        except ImportError:
            missing.append(package_name)

    if missing:
        return HealthCheckResult(
            "Required Packages",
            False,
            f"Missing packages: {', '.join(missing)}. Run: pip install -r requirements.txt",
            is_critical=True
        )

    return HealthCheckResult(
        "Required Packages",
        True,
        f"All required packages installed ({len(required_packages)} checked)",
        is_critical=True
    )


def verify_config_file() -> HealthCheckResult:
    """Check config/.env exists with valid API key format"""
    root = get_script_root()
    config_file = root / "config" / ".env"

    if not config_file.exists():
        return HealthCheckResult(
            "Configuration File",
            False,
            f"Config file not found: {config_file}. Run configure.bat to create it.",
            is_critical=True
        )

    # Read and validate API key
    try:
        content = config_file.read_text()

        # Look for API key line
        api_key = None
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('ANTHROPIC_API_KEY='):
                api_key = line.split('=', 1)[1].strip()
                break

        if not api_key:
            return HealthCheckResult(
                "Configuration File",
                False,
                "ANTHROPIC_API_KEY not found in config. Run configure.bat.",
                is_critical=True
            )

        if api_key == "your_api_key_here" or len(api_key) < 20:
            return HealthCheckResult(
                "Configuration File",
                False,
                "ANTHROPIC_API_KEY appears to be placeholder. Set your actual API key in config/.env",
                is_critical=True
            )

        return HealthCheckResult(
            "Configuration File",
            True,
            f"Configuration file valid with API key configured",
            is_critical=True
        )

    except Exception as e:
        return HealthCheckResult(
            "Configuration File",
            False,
            f"Failed to read config file: {e}",
            is_critical=True
        )


def verify_template_file() -> HealthCheckResult:
    """Validate EngineDirs.template.txt exists and has placeholders"""
    root = get_script_root()
    template_file = root / "ue5_query" / "indexing" / "EngineDirs.template.txt"

    if not template_file.exists():
        return HealthCheckResult(
            "Template File",
            False,
            f"Template file not found: {template_file}. Installation may be incomplete.",
            is_critical=True
        )

    try:
        content = template_file.read_text()

        if "{ENGINE_ROOT}" not in content:
            return HealthCheckResult(
                "Template File",
                False,
                "Template file doesn't contain {ENGINE_ROOT} placeholder. File may be corrupted.",
                is_critical=True
            )

        # Count non-comment lines
        lines = [l.strip() for l in content.split('\n') if l.strip() and not l.strip().startswith('#')]

        if len(lines) < 5:
            return HealthCheckResult(
                "Template File",
                False,
                f"Template file has too few entries ({len(lines)}). Expected at least 5.",
                is_critical=False
            )

        return HealthCheckResult(
            "Template File",
            True,
            f"Template file valid with {len(lines)} directory entries",
            is_critical=True
        )

    except Exception as e:
        return HealthCheckResult(
            "Template File",
            False,
            f"Failed to read template file: {e}",
            is_critical=True
        )


def verify_engine_paths() -> HealthCheckResult:
    """Validate EngineDirs.txt exists and paths are valid"""
    root = get_script_root()
    engine_dirs_file = root / "ue5_query" / "indexing" / "EngineDirs.txt"

    if not engine_dirs_file.exists():
        return HealthCheckResult(
            "Engine Paths",
            False,
            "EngineDirs.txt not found. Run configure.bat or fix-paths.bat to generate it.",
            is_critical=False  # Not critical until user tries to build index
        )

    try:
        content = engine_dirs_file.read_text()
        lines = [l.strip() for l in content.split('\n') if l.strip() and not l.strip().startswith('#')]

        if len(lines) == 0:
            return HealthCheckResult(
                "Engine Paths",
                False,
                "EngineDirs.txt is empty. Run fix-paths.bat to regenerate.",
                is_critical=False
            )

        # Resolve {ENGINE_ROOT} placeholder from config
        engine_root = None
        config_file = root / "config" / ".env"
        if config_file.exists():
            with open(config_file, 'r') as f:
                for config_line in f:
                    config_line = config_line.strip()
                    if config_line.startswith('UE_ENGINE_ROOT='):
                        engine_root = config_line.split('=', 1)[1].strip()
                        break

        # Check a sample of paths
        valid_count = 0
        invalid_paths = []
        for line in lines[:5]:  # Check first 5 paths
            # Resolve placeholder if present
            if '{ENGINE_ROOT}' in line and engine_root:
                resolved_line = line.replace('{ENGINE_ROOT}', engine_root)
            else:
                resolved_line = line

            path = Path(resolved_line)
            if path.exists() and path.is_dir():
                valid_count += 1
            else:
                invalid_paths.append(line)

        if valid_count == 0 and len(lines) > 0:
            if not engine_root:
                return HealthCheckResult(
                    "Engine Paths",
                    False,
                    f"Engine root not configured in config/.env. Run Configuration tab to set UE_ENGINE_ROOT.",
                    is_critical=False
                )
            return HealthCheckResult(
                "Engine Paths",
                False,
                f"None of the checked paths exist. Run fix-paths.bat to regenerate for your system.",
                is_critical=False
            )

        if invalid_paths:
            return HealthCheckResult(
                "Engine Paths",
                True,
                f"EngineDirs.txt has {len(lines)} entries ({valid_count}/{len(lines[:5])} checked paths exist). " +
                "Some paths may not exist on this system.",
                is_critical=False
            )

        return HealthCheckResult(
            "Engine Paths",
            True,
            f"EngineDirs.txt valid with {len(lines)} entries (all checked paths exist)",
            is_critical=False
        )

    except Exception as e:
        return HealthCheckResult(
            "Engine Paths",
            False,
            f"Failed to validate EngineDirs.txt: {e}",
            is_critical=False
        )


def verify_vector_store() -> HealthCheckResult:
    """Check vector store integrity if it exists"""
    root = get_script_root()
    vector_file = root / "data" / "vector_store.npz"
    meta_file = root / "data" / "vector_meta.json"

    # Not critical if it doesn't exist - user may not have built index yet
    if not vector_file.exists() and not meta_file.exists():
        return HealthCheckResult(
            "Vector Store",
            True,
            "Vector store not built yet. Run rebuild-index.bat to build.",
            is_critical=False
        )

    # But if one exists and not the other, that's a problem
    if vector_file.exists() and not meta_file.exists():
        return HealthCheckResult(
            "Vector Store",
            False,
            f"Vector store exists but metadata missing: {meta_file}. Rebuild with rebuild-index.bat --force",
            is_critical=False
        )

    if meta_file.exists() and not vector_file.exists():
        return HealthCheckResult(
            "Vector Store",
            False,
            f"Metadata exists but vector store missing: {vector_file}. Rebuild with rebuild-index.bat --force",
            is_critical=False
        )

    # Both exist - check sizes
    try:
        vector_size = vector_file.stat().st_size
        meta_size = meta_file.stat().st_size

        if vector_size == 0 or meta_size == 0:
            return HealthCheckResult(
                "Vector Store",
                False,
                "Vector store files are empty. Rebuild with rebuild-index.bat --force",
                is_critical=False
            )

        # Try to load metadata to get count
        try:
            meta_data = json.loads(meta_file.read_text())
            chunk_count = len(meta_data.get('items', []))

            vector_size_mb = vector_size / (1024 * 1024)

            return HealthCheckResult(
                "Vector Store",
                True,
                f"Vector store exists with {chunk_count} chunks ({vector_size_mb:.1f}MB)",
                is_critical=False
            )
        except json.JSONDecodeError:
            return HealthCheckResult(
                "Vector Store",
                False,
                "Vector store metadata is corrupted (invalid JSON). Rebuild with rebuild-index.bat --force",
                is_critical=False
            )

    except Exception as e:
        return HealthCheckResult(
            "Vector Store",
            False,
            f"Failed to check vector store: {e}",
            is_critical=False
        )


def run_all_checks(verbose: bool = False) -> Tuple[List[HealthCheckResult], List[HealthCheckResult]]:
    """Run all health checks and return results"""
    checks = [
        verify_python_version,
        verify_virtual_environment,
        verify_required_packages,
        verify_config_file,
        verify_template_file,
        verify_engine_paths,
        verify_vector_store,
    ]

    passed = []
    failed = []

    for check_func in checks:
        result = check_func()
        if result.passed:
            passed.append(result)
        else:
            failed.append(result)

    return passed, failed


def print_results(passed: List[HealthCheckResult], failed: List[HealthCheckResult], verbose: bool = False):
    """Print health check results in a user-friendly format"""

    print("\n" + "="*70)
    print("UE5 Source Query - Health Check Results")
    print("="*70)
    print()

    # Print failures first (most important)
    if failed:
        critical_failures = [f for f in failed if f.is_critical]
        warnings = [f for f in failed if not f.is_critical]

        if critical_failures:
            print("CRITICAL ISSUES:")
            print("-" * 70)
            for result in critical_failures:
                print(f"  [X] {result.name}")
                print(f"      {result.message}")
                print()

        if warnings:
            print("WARNINGS:")
            print("-" * 70)
            for result in warnings:
                print(f"  [!] {result.name}")
                print(f"      {result.message}")
                print()

    # Print passes if verbose or if everything passed
    if verbose or not failed:
        if passed:
            print("PASSED CHECKS:")
            print("-" * 70)
            for result in passed:
                print(f"  [OK] {result.name}")
                if verbose:
                    print(f"    {result.message}")
            print()

    # Summary
    total = len(passed) + len(failed)
    critical_failures = len([f for f in failed if f.is_critical])
    warnings = len([f for f in failed if not f.is_critical])

    print("="*70)
    print(f"Summary: {len(passed)}/{total} checks passed")
    if critical_failures > 0:
        print(f"         {critical_failures} critical failure(s)")
    if warnings > 0:
        print(f"         {warnings} warning(s)")
    print("="*70)
    print()

    if critical_failures > 0:
        print("NEXT STEPS:")
        print("  1. Fix critical issues listed above")
        print("  2. Run: configure.bat (if config issues)")
        print("  3. Run: health-check.bat (to verify fixes)")
        print()
        print("For detailed help: docs\\TROUBLESHOOTING.md")
        print()
    elif warnings > 0:
        print("System is functional but has warnings.")
        print("Address warnings when convenient.")
        print()
    else:
        print("All checks passed! System is ready to use.")
        print("Try: ask.bat \"What is FVector\"")
        print()


def main():
    """Main entry point"""
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    passed, failed = run_all_checks(verbose)
    print_results(passed, failed, verbose)

    # Exit with appropriate code
    critical_failures = [f for f in failed if f.is_critical]
    if critical_failures:
        sys.exit(1)  # Critical failure
    elif failed:
        sys.exit(2)  # Warnings only
    else:
        sys.exit(0)  # All passed


if __name__ == "__main__":
    main()
