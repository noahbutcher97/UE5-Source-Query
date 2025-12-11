import sys
import subprocess
import json
from pathlib import Path

def get_available_engines(script_dir: Path, use_cache: bool = True):
    """
    Detect installed UE5 engines using the new Phase 6 detection system.

    Uses multiple detection strategies in priority order:
    1. Environment variables (UE5_ENGINE_PATH, UE_ROOT, etc.)
    2. Config files (.ue5query)
    3. Windows Registry
    4. Common install locations

    Args:
        script_dir: Root directory of the script
        use_cache: Use cached results if available and fresh (default: True)

    Returns:
        List[Dict] containing engine information with keys:
            - version: Engine version string
            - engine_root: Path to Engine directory
            - path: Parent directory (backward compatibility)
            - source: Detection source (env_var, config_file, registry, common_location)
            - validated: Whether validation checks passed
            - health_score: 0.0-1.0 health score
            - issues: List of critical issues
            - warnings: List of non-critical warnings

    Raises:
        Exception on failure.
    """
    try:
        # Import the new detection system - universal import for both environments
        try:
            from src.utils.environment_detector import get_detector
        except ImportError:
            from utils.environment_detector import get_detector

        # Get detector with proper cache path
        detector = get_detector(script_dir)

        # Run detection
        installations = detector.detect_engines(use_cache=use_cache, validate=True)

        # Convert to dict format
        return [inst.to_dict() for inst in installations]

    except ImportError:
        # Fallback to old detection method if new system not available
        return _legacy_detection(script_dir)
    except Exception as e:
        # If new system fails, try legacy fallback
        try:
            return _legacy_detection(script_dir)
        except:
            raise Exception(f"Detection failed: {e}")


def _legacy_detection(script_dir: Path):
    """Legacy detection using detect_engine_path.py (fallback)"""
    detect_script = script_dir / "src" / "indexing" / "detect_engine_path.py"

    # Ensure script exists
    if not detect_script.exists():
        raise Exception("Detection script not found")

    try:
        result = subprocess.run(
            [sys.executable, str(detect_script), "--json"],
            capture_output=True,
            text=True,
            check=True
        )
        engines = json.loads(result.stdout)

        # Add backward compatibility fields
        for engine in engines:
            if "source" not in engine:
                engine["source"] = "legacy_detection"
            if "validated" not in engine:
                engine["validated"] = False
            if "health_score" not in engine:
                engine["health_score"] = 0.7  # Assume decent health

        # Sort by version descending (newest first)
        # Extract numeric version for sorting (e.g., "UE_5.3" -> 5.3, "UE_4.23" -> 4.23)
        def version_key(engine):
            version = engine.get("version", "")
            try:
                # Extract version number from format like "UE_5.3" or "5.3"
                version_str = version.replace("UE_", "").replace("UE", "")
                parts = version_str.split(".")
                # Convert to float for comparison (5.3 > 4.23)
                if len(parts) >= 2:
                    return float(f"{parts[0]}.{parts[1]}")
                elif len(parts) == 1:
                    return float(parts[0])
            except (ValueError, IndexError):
                pass
            return 0.0  # Unknown versions go to end

        engines.sort(key=version_key, reverse=True)

        return engines
    except subprocess.CalledProcessError as e:
        raise Exception(f"Detection failed: {e.stderr}")
    except json.JSONDecodeError:
        raise Exception("Invalid JSON output from detector")
    except Exception as e:
        raise Exception(f"Error running detector: {e}")

def get_engine_version_from_uproject(uproject_path: str) -> str:
    """
    Extract the EngineAssociation version from a .uproject file.

    Args:
        uproject_path: Path to .uproject file

    Returns:
        Engine version string (e.g., "5.3") or None if not found
    """
    try:
        path = Path(uproject_path)
        if not path.exists() or not path.suffix == '.uproject':
            return None

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('EngineAssociation')
    except Exception:
        return None


def find_uproject_in_directory(directory: Path) -> Path:
    """
    Find the most relevant .uproject file in a directory tree using intelligent heuristics.

    Search strategy:
    1. Current directory (highest priority - likely a deployment inside project)
    2. Immediate subdirectories (1 level deep - e.g., project root contains Scripts/)
    3. Parent directories (up to 5 levels - e.g., Scripts is inside project)
    4. Sibling directories (same parent - e.g., Scripts/ and Source/ are siblings)

    Prioritization:
    - Closer proximity to starting directory = higher relevance
    - Direct ancestors/descendants preferred over siblings
    - Stop at first match in each search tier

    Args:
        directory: Starting directory (e.g., deployment destination)

    Returns:
        Path to most relevant .uproject file or None if not found
    """
    directory = Path(directory).resolve()

    # Tier 1: Current directory (deployment IS the project root)
    for uproject in directory.glob("*.uproject"):
        if uproject.is_file():
            return uproject

    # Tier 2: Immediate subdirectories (deployment contains project subdirs)
    # Common pattern: D:\UnrealProjects\MyGame\Scripts\ (deployment)
    #                 D:\UnrealProjects\MyGame\MyGame.uproject (project file)
    try:
        for subdir in directory.iterdir():
            if subdir.is_dir():
                for uproject in subdir.glob("*.uproject"):
                    if uproject.is_file():
                        return uproject
    except (PermissionError, OSError):
        pass  # Skip inaccessible directories

    # Tier 3: Parent directories (deployment is inside project)
    # Common pattern: D:\UnrealProjects\MyGame\MyGame.uproject (project)
    #                 D:\UnrealProjects\MyGame\Scripts\ (deployment inside)
    current = directory.parent
    for depth in range(5):  # Max 5 levels up
        if current == current.parent:
            break

        for uproject in current.glob("*.uproject"):
            if uproject.is_file():
                # Verify this .uproject is actually an ancestor context
                # (not just a random project in a parent directory)
                try:
                    directory.relative_to(current)  # Will raise ValueError if not relative
                    return uproject
                except ValueError:
                    continue  # Not a true ancestor, keep searching

        current = current.parent

    # Tier 4: Sibling directories (deployment and project are siblings)
    # Pattern: D:\UnrealProjects\MyGame\Scripts\ (deployment)
    #          D:\UnrealProjects\MyGame\Source\ (sibling with code)
    #          D:\UnrealProjects\MyGame\MyGame.uproject (sibling project file)
    parent = directory.parent
    if parent and parent.exists():
        try:
            for sibling in parent.iterdir():
                if sibling.is_dir() and sibling != directory:
                    for uproject in sibling.glob("*.uproject"):
                        if uproject.is_file():
                            return uproject
        except (PermissionError, OSError):
            pass

    return None


def resolve_uproject_source(uproject_path: str) -> str:
    """
    Given a .uproject path, returns the expected Source directory.
    Returns None if Source directory doesn't exist.
    """
    path = Path(uproject_path)
    if not path.exists():
        return None

    source_dir = path.parent / "Source"
    if source_dir.exists() and source_dir.is_dir():
        return str(source_dir)
    return None


def detect_engine_from_vector_store(script_dir: Path):
    """
    Detect engine version from vector store metadata.

    Returns:
        Dict with 'version', 'engine_root', and 'source' keys, or None if not found
    """
    import json
    import re

    vector_meta = script_dir / "data" / "vector_meta.json"

    if not vector_meta.exists():
        return None

    try:
        with open(vector_meta, 'r') as f:
            data = json.load(f)

        # Sample first few items to find engine paths
        items = data.get('items', [])
        if not items:
            return None

        # Look for engine paths in first 10 items
        for item in items[:10]:
            path = item.get('path', '')

            # Extract engine version from path (e.g., "C:\...\UE_5.3\Engine\...")
            match = re.search(r'[/\\]UE[_-]?(\d+\.\d+)[/\\]', path)
            if match:
                version = match.group(1)
                # Extract engine root
                engine_match = re.search(r'(.+?[/\\]UE[_-]?\d+\.\d+[/\\]Engine)', path)
                if engine_match:
                    engine_root = engine_match.group(1)
                    return {
                        'version': f"UE_{version}",
                        'engine_root': engine_root,
                        'path': str(Path(engine_root).parent),
                        'source': 'vector_store'
                    }

        return None
    except Exception:
        return None


def get_smart_engine_path(script_dir: Path):
    """
    Smart engine path detection with priority:
    1. Vector store (if built index exists)
    2. Project .uproject file (if in project context)
    3. Config file
    4. Auto-detection (newest version)

    Returns:
        Dict with 'path', 'version', 'source', and 'is_user_override' keys
    """
    import json

    result = {
        'path': None,
        'version': None,
        'source': None,
        'is_user_override': False
    }

    # Check for user override marker
    override_file = script_dir / ".engine_override"
    if override_file.exists():
        result['is_user_override'] = True
        try:
            with open(override_file, 'r') as f:
                override_data = json.load(f)
                result['path'] = override_data.get('engine_root')
                result['version'] = override_data.get('version')
                result['source'] = 'user_override'
                if result['path'] and Path(result['path']).exists():
                    return result
        except:
            pass

    # Priority 1: Vector store
    vector_engine = detect_engine_from_vector_store(script_dir)
    if vector_engine:
        result.update(vector_engine)
        return result

    # Priority 2: Project .uproject file
    uproject = find_uproject_in_directory(script_dir)
    if uproject:
        project_version = get_engine_version_from_uproject(str(uproject))
        if project_version:
            # Try to find matching engine
            try:
                engines = get_available_engines(script_dir)
                for engine in engines:
                    engine_ver = engine.get('version', '')
                    if project_version in engine_ver:
                        result['path'] = engine.get('path') or engine.get('engine_root')
                        result['version'] = engine_ver
                        result['source'] = 'uproject'
                        return result
            except:
                pass

    # Priority 3: Config file
    config_file = script_dir / "config" / ".env"
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('UE_ENGINE_ROOT='):
                        engine_root = line.split('=', 1)[1].strip()
                        if Path(engine_root).exists():
                            # Extract version from path
                            import re
                            match = re.search(r'UE[_-]?(\d+\.\d+)', engine_root)
                            if match:
                                result['path'] = engine_root
                                result['version'] = f"UE_{match.group(1)}"
                                result['source'] = 'config'
                                return result
        except:
            pass

    # Priority 4: Auto-detection (newest)
    try:
        engines = get_available_engines(script_dir)
        if engines:
            first = engines[0]
            result['path'] = first.get('path') or first.get('engine_root')
            result['version'] = first.get('version')
            result['source'] = 'auto_detect'
            return result
    except:
        pass

    return result
