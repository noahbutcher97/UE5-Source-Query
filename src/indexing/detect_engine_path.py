"""
Detect Unreal Engine installation paths across different systems.
Supports Windows registry lookup, common install locations, and manual entry.
"""
import sys
import winreg
import json
from pathlib import Path
from typing import List, Optional, Dict


def detect_from_registry() -> List[Dict[str, str]]:
    """
    Detect UE5 installations from Windows registry.

    Returns:
        List of dicts with 'version', 'path', and 'engine_root' keys
    """
    installations = []
    registry_failures = []

    # Epic Games Launcher registry key
    registry_paths = [
        r"SOFTWARE\EpicGames\Unreal Engine",
        r"SOFTWARE\WOW6432Node\EpicGames\Unreal Engine",
    ]

    for reg_path in registry_paths:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
            i = 0
            while True:
                try:
                    version = winreg.EnumKey(key, i)
                    subkey = winreg.OpenKey(key, version)
                    try:
                        install_dir, _ = winreg.QueryValueEx(subkey, "InstalledDirectory")
                        engine_root = Path(install_dir) / "Engine"
                        if engine_root.exists():
                            installations.append({
                                "version": version,
                                "path": str(install_dir),
                                "engine_root": str(engine_root)
                            })
                    except FileNotFoundError:
                        pass
                    finally:
                        winreg.CloseKey(subkey)
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
        except PermissionError:
            registry_failures.append(("Permission denied", reg_path))
            continue
        except FileNotFoundError:
            continue  # Silent - expected if path doesn't exist
        except Exception as e:
            registry_failures.append((str(e), reg_path))
            continue

    # Report failures if no installations found
    if registry_failures and not installations:
        print("\n[WARNING] Registry search encountered issues:")
        for error, path in registry_failures:
            print(f"  - {path}: {error}")
        print("\n  Try running as Administrator for full detection")
        print("  Or continue with manual path entry below\n")

    return installations


def detect_from_common_locations() -> List[Dict[str, str]]:
    """
    Search common UE5 installation locations.

    Returns:
        List of dicts with 'version', 'path', and 'engine_root' keys
    """
    installations = []

    # Common installation directories
    search_roots = [
        Path("C:/Program Files/Epic Games"),
        Path("D:/Program Files/Epic Games"),
        Path("E:/Program Files/Epic Games"),
        Path("C:/Epic Games"),
        Path("D:/Epic Games"),
        Path("E:/Epic Games"),
        Path("C:/UnrealEngine"),
        Path("D:/UnrealEngine"),
        Path("E:/UnrealEngine"),
    ]

    for root in search_roots:
        if not root.exists():
            continue

        # Look for UE_* directories
        for ue_dir in root.glob("UE_*"):
            if not ue_dir.is_dir():
                continue

            engine_root = ue_dir / "Engine"
            if engine_root.exists():
                version = ue_dir.name
                installations.append({
                    "version": version,
                    "path": str(ue_dir),
                    "engine_root": str(engine_root)
                })

    return installations


def validate_engine_path(path: str) -> Optional[Dict[str, str]]:
    """
    Validate that a given path is a valid UE5 Engine directory.

    Args:
        path: Path to validate (should be Engine root or parent directory)

    Returns:
        Dict with installation info if valid, None otherwise
    """
    path = Path(path)

    # If path ends with "Engine", use it directly
    if path.name == "Engine" and path.exists():
        engine_root = path
        parent = path.parent
    # Otherwise, assume it's the UE installation root
    elif (path / "Engine").exists():
        engine_root = path / "Engine"
        parent = path
    else:
        return None

    # Validate by checking for key directories/files
    required_paths = [
        engine_root / "Source",
        engine_root / "Plugins",
        engine_root / "Build",
    ]

    if all(p.exists() for p in required_paths):
        version = parent.name if parent.name.startswith("UE_") else "Custom"
        return {
            "version": version,
            "path": str(parent),
            "engine_root": str(engine_root)
        }

    return None


def get_engine_path_interactive() -> Optional[str]:
    """
    Interactive prompt to get UE5 engine path from user.

    Returns:
        Engine root path string, or None if cancelled
    """
    print("\n" + "="*70)
    print("UE5 Engine Path Detection")
    print("="*70)

    # Try registry detection
    print("\n[1/3] Searching Windows Registry...")
    registry_installs = detect_from_registry()

    # Try common locations
    print("[2/3] Searching common installation locations...")
    common_installs = detect_from_common_locations()

    # Combine and deduplicate
    all_installs = registry_installs + common_installs
    seen = set()
    unique_installs = []
    for install in all_installs:
        key = install["engine_root"]
        if key not in seen:
            seen.add(key)
            unique_installs.append(install)

    # Display results
    print(f"[3/3] Found {len(unique_installs)} UE5 installation(s)\n")

    if unique_installs:
        print("Detected installations:")
        for i, install in enumerate(unique_installs, 1):
            print(f"  [{i}] {install['version']}")
            print(f"      Path: {install['engine_root']}")
        print()

        # Prompt user to select
        while True:
            choice = input(f"Select installation (1-{len(unique_installs)}) or 'c' for custom path: ").strip().lower()

            if choice == 'c':
                break

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(unique_installs):
                    return unique_installs[idx]["engine_root"]
                else:
                    print(f"Please enter a number between 1 and {len(unique_installs)}")
            except ValueError:
                print("Invalid input. Enter a number or 'c' for custom path.")

    # Manual entry
    print("\nNo installations detected or custom path requested.")
    print("Please enter the path to your Unreal Engine installation.")
    print("Examples:")
    print("  C:\\Program Files\\Epic Games\\UE_5.3\\Engine")
    print("  D:\\UnrealEngine\\UE_5.4\\Engine")
    print()

    while True:
        custom_path = input("Engine path (or 'q' to quit): ").strip()

        if custom_path.lower() == 'q':
            return None

        # Remove quotes if user included them
        custom_path = custom_path.strip('"').strip("'")

        validation = validate_engine_path(custom_path)
        if validation:
            print(f"\n✓ Valid engine path: {validation['engine_root']}")
            return validation["engine_root"]
        else:
            print(f"\n✗ Invalid path: {custom_path}")
            print("  Path must contain Engine/Source, Engine/Plugins, and Engine/Build directories")
            print()


def generate_engine_dirs(template_path: Path, output_path: Path, engine_root: str) -> bool:
    """
    Generate EngineDirs.txt from template by substituting {ENGINE_ROOT}.

    Args:
        template_path: Path to EngineDirs.template.txt
        output_path: Path to write EngineDirs.txt
        engine_root: Engine root path to substitute

    Returns:
        True if successful, False otherwise
    """
    try:
        if not template_path.exists():
            print(f"ERROR: Template not found: {template_path}")
            return False

        # Read template
        template_content = template_path.read_text(encoding='utf-8')

        # Normalize engine_root path (remove trailing slashes/backslashes)
        engine_root = str(Path(engine_root)).rstrip('/\\')

        # Substitute placeholder
        output_content = template_content.replace("{ENGINE_ROOT}", engine_root)

        # Verify substitution happened
        if "{ENGINE_ROOT}" in output_content:
            print("WARNING: Some {ENGINE_ROOT} placeholders were not replaced")

        # Write output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_content, encoding='utf-8')

        # Count directories
        lines = [line.strip() for line in output_content.split('\n')
                if line.strip() and not line.strip().startswith('#')]
        dir_count = len(lines)

        # NEW: Validate generated paths exist
        valid_count = 0
        invalid_paths = []
        for line in lines:
            path = Path(line)
            if path.exists() and path.is_dir():
                valid_count += 1
            else:
                invalid_paths.append(str(line))

        if valid_count == 0 and dir_count > 0:
            print(f"\n✗ ERROR: None of the generated paths exist!")
            print(f"  Engine Root: {engine_root}")
            print(f"  This suggests the wrong engine path was selected.")
            print(f"\n  First few paths that should exist:")
            for p in lines[:3]:
                print(f"    - {p}")
            return False

        if len(invalid_paths) > len(lines) / 2:
            print(f"\n⚠ WARNING: Most paths don't exist ({len(invalid_paths)}/{len(lines)})")
            print(f"  Invalid paths (first 5):")
            for p in invalid_paths[:5]:
                print(f"    - {p}")
            print()

            response = input("Continue anyway? (y/N): ").strip().lower()
            if response != 'y':
                print("Operation cancelled. Try selecting a different UE5 installation.")
                return False

        print(f"\n✓ Generated {output_path}")
        print(f"  Engine Root: {engine_root}")
        print(f"  Directories: {dir_count}")
        print(f"  Valid paths: {valid_count}/{dir_count}")

        return True

    except Exception as e:
        print(f"ERROR: Failed to generate EngineDirs.txt: {e}")
        return False


import json

if __name__ == "__main__":
    # JSON output mode (for GUI)
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        registry_installs = detect_from_registry()
        common_installs = detect_from_common_locations()
        
        all_installs = registry_installs + common_installs
        
        # Deduplicate based on engine_root
        seen = set()
        unique_installs = []
        for install in all_installs:
            key = install["engine_root"]
            if key not in seen:
                seen.add(key)
                unique_installs.append(install)
        
        print(json.dumps(unique_installs))
        sys.exit(0)

    # Auto-detect mode (legacy support)
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        registry_installs = detect_from_registry()
        common_installs = detect_from_common_locations()
        if registry_installs + common_installs:
            print(f"Engine Root: {(registry_installs + common_installs)[0]['engine_root']}")
            sys.exit(0)
        sys.exit(1)

    # Interactive mode
    if len(sys.argv) == 1:
        engine_root = get_engine_path_interactive()
        if engine_root:
            print(f"\nDetected Engine Root: {engine_root}")

            # Generate EngineDirs.txt if template exists
            script_dir = Path(__file__).parent
            template = script_dir / "EngineDirs.template.txt"
            output = script_dir / "EngineDirs.txt"

            if template.exists():
                print("\nGenerating EngineDirs.txt from template...")
                if generate_engine_dirs(template, output, engine_root):
                    sys.exit(0)
                else:
                    sys.exit(1)
            else:
                print(f"\nWARNING: Template not found: {template}")
                print("Skipping EngineDirs.txt generation")
                sys.exit(0)
        else:
            print("\nCancelled by user")
            sys.exit(1)

    # Command-line mode: python detect_engine_path.py <template> <output> [engine_root]
    elif len(sys.argv) >= 3:
        template_path = Path(sys.argv[1])
        output_path = Path(sys.argv[2])

        if len(sys.argv) >= 4:
            # Engine root provided
            engine_root = sys.argv[3]
            validation = validate_engine_path(engine_root)
            if not validation:
                print(f"ERROR: Invalid engine path: {engine_root}")
                sys.exit(1)
            engine_root = validation["engine_root"]
        else:
            # Detect interactively
            engine_root = get_engine_path_interactive()
            if not engine_root:
                sys.exit(1)

        if generate_engine_dirs(template_path, output_path, engine_root):
            sys.exit(0)
        else:
            sys.exit(1)

    else:
        print("Usage:")
        print("  Interactive: python detect_engine_path.py")
        print("  CLI: python detect_engine_path.py <template> <output> [engine_root]")
        sys.exit(1)