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

        return engines
    except subprocess.CalledProcessError as e:
        raise Exception(f"Detection failed: {e.stderr}")
    except json.JSONDecodeError:
        raise Exception("Invalid JSON output from detector")
    except Exception as e:
        raise Exception(f"Error running detector: {e}")

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
