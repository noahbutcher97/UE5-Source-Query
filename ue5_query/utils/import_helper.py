"""
Universal import helper for environment-agnostic imports.

This module provides utilities to detect the execution environment and
import modules correctly whether running in:
- Development repository (scripts run from project root)
- Distributed package (scripts run from Scripts/ subdirectory)
- Git clone (for contributors/testers)
"""

import sys
from pathlib import Path

def is_dev_environment():
    """
    Detect if running in development/git repository vs distributed package.

    Returns:
        bool: True if in dev/git repo, False if in distributed package
    """
    # Find the root directory (where this file's ue5_query/ parent is)
    current_file = Path(__file__).resolve()

    # Go up: import_helper.py -> utils/ -> ue5_query/ -> root
    potential_root = current_file.parent.parent.parent

    # Dev/git indicators
    has_git = (potential_root / ".git").exists()
    has_requirements = (potential_root / "requirements.txt").exists()
    has_setup_bat = (potential_root / "Setup.bat").exists()
    has_installer_dir = (potential_root / "installer").exists()

    # If we have git or the full development structure, it's dev
    if has_git or (has_requirements and has_setup_bat and has_installer_dir):
        return True

    # Otherwise, it's a distributed package
    return False

def get_import_context():
    """
    Get the current import context.

    Returns:
        str: 'dev' for development environment, 'dist' for distributed package
    """
    return 'dev' if is_dev_environment() else 'dist'

def universal_import(module_path, names=None):
    """
    Import a module or specific names from a module, working in both environments.

    Args:
        module_path (str): Module path like 'utils.file_utils' or 'core.hybrid_query'
        names (list): Optional list of specific names to import

    Returns:
        module or dict: The imported module, or dict of {name: object} if names specified

    Example:
        # Import entire module
        config_manager = universal_import('utils.config_manager')

        # Import specific names
        imports = universal_import('utils.file_utils', ['atomic_write', 'ensure_dir'])
        atomic_write = imports['atomic_write']
    """
    # Try absolute import first (dev environment)
    try:
        full_path = f"ue5_query.{module_path}"
        module = __import__(full_path, fromlist=names or [''])

        if names:
            return {name: getattr(module, name) for name in names}
        return module

    except ImportError:
        # Fall back to relative import (distributed environment)
        module = __import__(module_path, fromlist=names or [''])

        if names:
            return {name: getattr(module, name) for name in names}
        return module

# Convenience function for the most common pattern
def try_import(absolute_path, relative_path, names):
    """
    Try absolute import, fall back to relative.

    Args:
        absolute_path (str): Absolute import like 'ue5_query.utils.file_utils'
        relative_path (str): Relative import like 'utils.file_utils'
        names (list): Names to import from the module

    Returns:
        tuple: Imported objects in the order of names

    Example:
        atomic_write, ensure_dir = try_import(
            'ue5_query.utils.file_utils',
            'utils.file_utils',
            ['atomic_write', 'ensure_dir']
        )
    """
    try:
        module = __import__(absolute_path, fromlist=names)
    except ImportError:
        module = __import__(relative_path, fromlist=names)

    if len(names) == 1:
        return getattr(module, names[0])
    return tuple(getattr(module, name) for name in names)
