from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import os

@dataclass
class LayoutProfile:
    name: str
    description: str
    markers: List[str]
    correction_strategy: str  # 'none' or 'append_child'
    target_child: Optional[str] = None

class InvalidEngineLayoutError(Exception):
    """Raised when a path does not match any known engine structure."""
    pass

class EnginePathNormalizer:
    """
    Validates and normalizes Unreal Engine paths based on predefined layout profiles.
    """
    
    # Define known layouts (could be moved to JSON later)
    LAYOUTS = [
        LayoutProfile(
            name="Launcher_Standard_Internal",
            description="Standard Epic Launcher Install (Internal Root)",
            markers=["Source", "Config", "Content", "Binaries"],
            correction_strategy="none"
        ),
        LayoutProfile(
            name="Launcher_Standard_Base",
            description="Standard Epic Launcher Install (Base Root)",
            markers=["Engine", "Engine/Source"],
            correction_strategy="append_child",
            target_child="Engine"
        ),
        LayoutProfile(
            name="Source_Build_GitHub",
            description="GitHub Source Build",
            markers=["GenerateProjectFiles.bat", "Engine/Source"],
            correction_strategy="append_child",
            target_child="Engine"
        )
    ]

    def normalize(self, input_path: Path) -> Path:
        """
        Validate and normalize an engine path.
        
        Args:
            input_path: The candidate path to check.
            
        Returns:
            The normalized path pointing to the Engine root (containing Source/).
            
        Raises:
            FileNotFoundError: If input path doesn't exist.
            InvalidEngineLayoutError: If path structure is unrecognized.
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Path not found: {input_path}")

        # Iterate Profiles (Priority Order)
        for profile in self.LAYOUTS:
            if self._matches_profile(input_path, profile):
                # Apply Correction Strategy
                if profile.correction_strategy == 'none':
                    return input_path
                elif profile.correction_strategy == 'append_child':
                    return input_path / profile.target_child
        
        # Fallback / Failure
        raise InvalidEngineLayoutError(f"Path {input_path} does not match any known engine structure.")

    def _matches_profile(self, path: Path, profile: LayoutProfile) -> bool:
        """Check if path contains all markers defined in the profile."""
        try:
            for marker in profile.markers:
                marker_path = path / marker
                if not marker_path.exists():
                    return False
            return True
        except OSError:
            # Handle permission errors or other OS issues gracefully
            return False
