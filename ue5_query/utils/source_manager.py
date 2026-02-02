from pathlib import Path

from ue5_query.utils.file_utils import atomic_write
from ue5_query.utils.ue_path_utils import UEPathUtils

class SourceManager:
    """Helper to manage EngineDirs.txt and ProjectDirs.txt"""
    def __init__(self, script_dir):
        self.script_dir = script_dir
        # Paths are now relative to the package root
        package_root = Path(__file__).resolve().parent.parent
        self.engine_template_file = package_root / "indexing" / "EngineDirs.template.txt"
        self.engine_dirs_file = package_root / "indexing" / "EngineDirs.txt"
        self.project_dirs_file = package_root / "indexing" / "ProjectDirs.txt"

    def get_default_engine_dirs(self):
        """Reads the default engine directories from the template file."""
        if not self.engine_template_file.exists():
            return []
        with open(self.engine_template_file, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]

    def get_engine_dirs(self):
        if not self.engine_dirs_file.exists():
            return self.get_default_engine_dirs() # Default to template if not yet generated
        with open(self.engine_dirs_file, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]

    def add_engine_dir(self, path):
        """
        Add engine directory with intelligent subsumption.
        Returns: (success, message)
        """
        current = self.get_engine_dirs()
        path_str = str(path)
        
        # 1. Check if exact duplicate
        if path_str in current:
            return False, "Path already exists."

        # 2. Add and Optimize
        candidate_list = current + [path_str]
        optimized = UEPathUtils.optimize_path_list(candidate_list)
        
        # 3. Analyze changes for feedback
        if path_str not in optimized:
            # The new path was redundant (a parent already exists)
            # Find which parent covers it
            parent = next((p for p in optimized if Path(path_str).is_relative_to(Path(p))), "a parent folder")
            return False, f"Skipped: Covered by '{parent}'."
        
        # If we are here, the new path was added.
        # Check if any OLD paths were removed (subsumed)
        removed_count = len(current) - (len(optimized) - 1)
        
        self._save_engine_dirs(optimized)
        
        if removed_count > 0:
            return True, f"Added path and removed {removed_count} redundant child entries."
        return True, "Path added successfully."

    def add_engine_dirs(self, paths):
        """
        Add multiple engine directories with optimized bulk processing.
        Returns: (success_count, messages)
        """
        current = self.get_engine_dirs()
        candidate_list = list(current)
        messages = []
        added_count = 0
        
        # Add all candidates
        for path in paths:
            path_str = str(path)
            if path_str not in candidate_list:
                candidate_list.append(path_str)
            else:
                messages.append(f"Skipped duplicate: {Path(path_str).name}")

        # Optimize once for the whole batch
        optimized = UEPathUtils.optimize_path_list(candidate_list)
        
        # Analyze what happened
        for path in paths:
            path_str = str(path)
            if path_str in optimized:
                if path_str not in current:
                    added_count += 1
            else:
                # If not in optimized, it was either subsumed or was a duplicate
                # Check subsumption
                try:
                    parent = next((p for p in optimized if Path(path_str).is_relative_to(Path(p))), None)
                    if parent and parent != path_str:
                        messages.append(f"Skipped {Path(path_str).name}: Covered by '{Path(parent).name}'")
                except:
                    pass

        if optimized != current:
            self._save_engine_dirs(optimized)
            
        return added_count, messages

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
        with open(self.project_dirs_file, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]

    def add_project_dir(self, path):
        """
        Add project directory with intelligent subsumption.
        Returns: (success, message)
        """
        current = self.get_project_dirs()
        path_str = str(path)
        
        if path_str in current:
            return False, "Path already exists."

        candidate_list = current + [path_str]
        optimized = UEPathUtils.optimize_path_list(candidate_list)
        
        if path_str not in optimized:
            parent = next((p for p in optimized if Path(path_str).is_relative_to(Path(p))), "a parent folder")
            return False, f"Skipped: Covered by '{parent}'."
        
        removed_count = len(current) - (len(optimized) - 1)
        self._save_project_dirs(optimized)
        
        if removed_count > 0:
            return True, f"Added path and removed {removed_count} redundant child entries."
        return True, "Path added successfully."

    def add_project_dirs(self, paths):
        """
        Add multiple project directories with optimized bulk processing.
        Returns: (success_count, messages)
        """
        current = self.get_project_dirs()
        candidate_list = list(current)
        messages = []
        added_count = 0
        
        for path in paths:
            path_str = str(path)
            if path_str not in candidate_list:
                candidate_list.append(path_str)
            else:
                messages.append(f"Skipped duplicate: {Path(path_str).name}")

        optimized = UEPathUtils.optimize_path_list(candidate_list)
        
        for path in paths:
            path_str = str(path)
            if path_str in optimized and path_str not in current:
                added_count += 1
            elif path_str not in optimized:
                try:
                    parent = next((p for p in optimized if Path(path_str).is_relative_to(Path(p))), None)
                    if parent and parent != path_str:
                        messages.append(f"Skipped {Path(path_str).name}: Covered by '{Path(parent).name}'")
                except:
                    pass

        if optimized != current:
            self._save_project_dirs(optimized)
            
        return added_count, messages

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
