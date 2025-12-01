import os
import shutil
import tempfile
from pathlib import Path
from contextlib import contextmanager

@contextmanager
def atomic_write(file_path, mode='w', encoding='utf-8'):
    """
    Context manager for atomic file writes.
    Writes to a temporary file and renames it to the target file on success.
    """
    path = Path(file_path)
    # Create temp file in the same directory to ensure atomic rename works
    temp_dir = path.parent
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    fd, temp_path = tempfile.mkstemp(dir=temp_dir, text=True)
    os.close(fd)
    
    try:
        with open(temp_path, mode, encoding=encoding) as f:
            yield f
        # Atomic rename (replace)
        shutil.move(temp_path, path)
    except Exception:
        # Clean up temp file on failure
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise
