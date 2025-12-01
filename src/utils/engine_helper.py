import sys
import subprocess
import json
from pathlib import Path

def get_available_engines(script_dir: Path):
    """
    Calls the detection script and returns a list of installed engines.
    Returns: List[Dict] containing 'version' and 'engine_root'.
    Raises: Exception on failure.
    """
    detect_script = script_dir / "src" / "indexing" / "detect_engine_path.py"
    
    # Ensure script exists
    if not detect_script.exists():
        # Fallback for when running from installer where src might be relative
        # Try looking relative to this file if script_dir isn't root
        pass 

    try:
        result = subprocess.run(
            [sys.executable, str(detect_script), "--json"],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
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
