from pathlib import Path
import os

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

    def _normalize(self, path_str):
        """Normalize path for consistent comparison"""
        try:
            return os.path.normpath(str(Path(path_str).resolve()))
        except:
            return os.path.normpath(str(path_str))

    def _is_duplicate(self, path_str, current_list):
        """Check if path exists in list (case-insensitive on Windows)"""
        norm_path = self._normalize(path_str).lower() if os.name == 'nt' else self._normalize(path_str)
        
        for existing in current_list:
            norm_existing = self._normalize(existing).lower() if os.name == 'nt' else self._normalize(existing)
            if norm_path == norm_existing:
                return True
        return False

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
        
        # 1. Check if exact duplicate (Robust)
        if self._is_duplicate(path_str, current):
            return False, "Path already exists."

        # 2. Add and Optimize
        candidate_list = current + [path_str]
        optimized = UEPathUtils.optimize_path_list(candidate_list)
        
        # 3. Analyze changes for feedback
        # Check if our new path survived optimization
        if not self._is_duplicate(path_str, optimized):
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
            if not self._is_duplicate(path_str, candidate_list):
                candidate_list.append(path_str)
            else:
                messages.append(f"Skipped duplicate: {Path(path_str).name}")

        # Optimize once for the whole batch
        optimized = UEPathUtils.optimize_path_list(candidate_list)
        
        # Analyze what happened
        for path in paths:
            path_str = str(path)
            if self._is_duplicate(path_str, optimized):
                if not self._is_duplicate(path_str, current):
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

    def remove_engine_dirs(self, paths_to_remove, engine_root=None):
        """Batch remove engine directories"""
        current = self.get_engine_dirs()
        if engine_root is None:
            engine_root = os.getenv("UE_ENGINE_ROOT", "")
        
        # Normalize targets for comparison
        norm_targets = set()
        for p in paths_to_remove:
            norm = self._normalize(p).lower() if os.name == 'nt' else self._normalize(p)
            norm_targets.add(norm)
        
        new_list = []
        removed_count = 0
        
        for entry in current:
            # Resolve placeholders
            resolved = entry
            if "{ENGINE_ROOT}" in entry and engine_root:
                resolved = entry.replace("{ENGINE_ROOT}", engine_root)
            
            norm_entry = self._normalize(resolved).lower() if os.name == 'nt' else self._normalize(resolved)
            
            if norm_entry in norm_targets:
                removed_count += 1
                continue
            
            new_list.append(entry)
            
        if removed_count > 0:
            self._save_engine_dirs(new_list)
            return True, f"Removed {removed_count} paths."
        return False, "No matching paths found."

    def clear_engine_dirs(self):
        """Remove all engine directories"""
        self._save_engine_dirs([])

    def remove_engine_dir(self, path_to_remove):
        # Legacy wrapper
        success, _ = self.remove_engine_dirs([path_to_remove])
        return success

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
        
        if self._is_duplicate(path_str, current):
            return False, "Path already exists."

        candidate_list = current + [path_str]
        optimized = UEPathUtils.optimize_path_list(candidate_list)
        
        if not self._is_duplicate(path_str, optimized):
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
            if not self._is_duplicate(path_str, candidate_list):
                candidate_list.append(path_str)
            else:
                messages.append(f"Skipped duplicate: {Path(path_str).name}")

        optimized = UEPathUtils.optimize_path_list(candidate_list)
        
        for path in paths:
            path_str = str(path)
            if self._is_duplicate(path_str, optimized) and not self._is_duplicate(path_str, current):
                added_count += 1
            elif not self._is_duplicate(path_str, optimized):
                try:
                    parent = next((p for p in optimized if Path(path_str).is_relative_to(Path(p))), None)
                    if parent and parent != path_str:
                        messages.append(f"Skipped {Path(path_str).name}: Covered by '{Path(parent).name}'")
                except:
                    pass

        if optimized != current:
            self._save_project_dirs(optimized)
            
        return added_count, messages

    def remove_project_dirs(self, paths_to_remove):
        """Batch remove project directories"""
        current = self.get_project_dirs()
        
        norm_targets = set()
        for p in paths_to_remove:
            norm = self._normalize(p).lower() if os.name == 'nt' else self._normalize(p)
            norm_targets.add(norm)
        
        new_list = []
        removed_count = 0
        
        for entry in current:
            norm_entry = self._normalize(entry).lower() if os.name == 'nt' else self._normalize(entry)
            
            if norm_entry in norm_targets:
                removed_count += 1
                continue
            new_list.append(entry)
            
        if removed_count > 0:
            self._save_project_dirs(new_list)
            return True, f"Removed {removed_count} paths."
        return False, "No matching paths found."

    def clear_project_dirs(self):
        """Remove all project directories"""
        self._save_project_dirs([])

    def remove_project_dir(self, path_to_remove):
        # Legacy wrapper
        success, _ = self.remove_project_dirs([path_to_remove])
        return success

    def _save_project_dirs(self, dirs):
        self.project_dirs_file.parent.mkdir(parents=True, exist_ok=True)
        with atomic_write(self.project_dirs_file, 'w') as f:
            f.write("# User-defined Project Directories\n")
            for d in dirs:
                f.write(f"{d}\n")
