# python
# ===== File: ue_path_utils.py =====
"""
Utilities for parsing Unreal Engine paths, modules, and includes.
"""
from pathlib import Path
from typing import Optional, Tuple, Dict

class UEPathUtils:
    """Helper for UE5 path resolution"""

    @staticmethod
    def guess_module_and_include(file_path: str, engine_root: Optional[str] = None) -> Dict[str, str]:
        """
        Guess the Module name and correct #include path for a file.
        
        Args:
            file_path: Full path to the file.
            engine_root: Optional engine root to verify relative paths.
            
        Returns:
            Dict with 'module' (str) and 'include' (str).
        """
        path = Path(file_path)
        parts = path.parts
        
        module_name = "Unknown"
        include_path = path.name # Fallback
        
        # Strategy 1: Look for "Source" folder and walk down
        # Standard structure: .../Source/<Category>/<Module>/...
        try:
            if "Source" in parts:
                source_idx = len(parts) - 1 - parts[::-1].index("Source")
                # Module is usually the immediate subdirectory of Source's child (Category)
                # e.g. Source/Runtime/Engine -> Engine
                # e.g. Source/Editor/UnrealEd -> UnrealEd
                # e.g. Source/Developer/ToolWidgets -> ToolWidgets
                
                # Check for Category (Runtime, Editor, etc)
                if source_idx + 2 < len(parts):
                    # Module is typically parts[source_idx + 2]
                    # But could be deeper if nested? Usually Build.cs is at Module root.
                    # Let's try to find Build.cs by walking UP from the file
                    current_dir = path.parent
                    while current_dir.name != "Source" and len(current_dir.parts) > source_idx:
                        # Check for *.Build.cs in this dir
                        build_files = list(current_dir.glob("*.Build.cs"))
                        if build_files:
                            module_name = build_files[0].stem.replace(".Build", "")
                            break
                        current_dir = current_dir.parent
                    
                    if module_name == "Unknown" and source_idx + 2 < len(parts):
                         # Heuristic: <Category>/<Module>
                         module_name = parts[source_idx + 2]

        except ValueError:
            pass

        # Strategy 2: Include Path calculation
        # Standard: Include relative to "Public" or "Classes"
        # .../Module/Public/MyFile.h -> #include "MyFile.h"
        # .../Module/Classes/MyFile.h -> #include "MyFile.h"
        # .../Module/Public/Sub/MyFile.h -> #include "Sub/MyFile.h"
        
        # Try to find 'Public' or 'Classes'
        if "Public" in parts:
            idx = len(parts) - 1 - parts[::-1].index("Public")
            # Include path is everything after Public
            include_path = "/".join(parts[idx+1:])
        elif "Classes" in parts:
            idx = len(parts) - 1 - parts[::-1].index("Classes")
            # Include path is everything after Classes
            include_path = "/".join(parts[idx+1:])
        else:
            # Maybe it's in Private? (Not usually included, but for completeness)
            if "Private" in parts:
                idx = len(parts) - 1 - parts[::-1].index("Private")
                include_path = "/".join(parts[idx+1:])
            else:
                # Just filename if no standard structure
                include_path = path.name

        # Clean separators
        include_path = include_path.replace("\\", "/")
        
        return {
            "module": module_name,
            "include": f'#include "{include_path}"'
        }
