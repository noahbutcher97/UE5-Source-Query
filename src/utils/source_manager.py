from pathlib import Path
from src.utils.file_utils import atomic_write

class SourceManager:
    """Helper to manage EngineDirs.txt and ProjectDirs.txt"""
    def __init__(self, script_dir):
        self.script_dir = script_dir
        self.engine_template_file = script_dir / "src" / "indexing" / "EngineDirs.template.txt"
        self.engine_dirs_file = script_dir / "src" / "indexing" / "EngineDirs.txt"
        self.project_dirs_file = script_dir / "src" / "indexing" / "ProjectDirs.txt"

    def get_default_engine_dirs(self):
        """Reads the default engine directories from the template file."""
        if not self.engine_template_file.exists():
            return []
        with open(self.engine_template_file, 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]

    def get_engine_dirs(self):
        if not self.engine_dirs_file.exists():
            return self.get_default_engine_dirs() # Default to template if not yet generated
        with open(self.engine_dirs_file, 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]

    def add_engine_dir(self, path):
        current = self.get_engine_dirs()
        if str(path) not in current:
            current.append(str(path))
            self._save_engine_dirs(current)
            return True
        return False

    def remove_engine_dir(self, path):
        current = self.get_engine_dirs()
        if path in current:
            current.remove(path)
            self._save_engine_dirs(current)
            return True
        return False

    def reset_engine_dirs(self):
        self._save_engine_dirs(self.get_default_engine_dirs())

    def _save_engine_dirs(self, dirs):
        self.engine_dirs_file.parent.mkdir(parents=True, exist_ok=True)
        with atomic_write(self.engine_dirs_file, 'w') as f:
            f.write("# User-defined Engine Directories (Managed by Dashboard)\n")
            f.write("# Use {ENGINE_ROOT} placeholder for detected engine path\n")
            for d in dirs:
                f.write(f"{d}\n")

    def get_project_dirs(self):
        if not self.project_dirs_file.exists():
            return []
        with open(self.project_dirs_file, 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]

    def add_project_dir(self, path):
        current = self.get_project_dirs()
        if str(path) not in current:
            current.append(str(path))
            self._save_project_dirs(current)
            return True
        return False

    def remove_project_dir(self, path):
        current = self.get_project_dirs()
        if path in current:
            current.remove(path)
            self._save_project_dirs(current)
            return True
        return False

    def _save_project_dirs(self, dirs):
        self.project_dirs_file.parent.mkdir(parents=True, exist_ok=True)
        with atomic_write(self.project_dirs_file, 'w') as f:
            f.write("# User-defined Project Directories\n")
            for d in dirs:
                f.write(f"{d}\n")
