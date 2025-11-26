"""
Installation helper script for copying files reliably across platforms.
"""
import sys
import shutil
from pathlib import Path


def copy_directory(src_dir: Path, dest_dir: Path, pattern: str = "*"):
    """Copy files matching pattern from src to dest."""
    src_dir = Path(src_dir)
    dest_dir = Path(dest_dir)

    if not src_dir.exists():
        print(f"ERROR: Source directory does not exist: {src_dir}")
        return False

    # Create destination directory
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Copy files matching pattern
    files_copied = 0
    for src_file in src_dir.glob(pattern):
        if src_file.is_file():
            dest_file = dest_dir / src_file.name
            shutil.copy2(src_file, dest_file)
            files_copied += 1

    return files_copied > 0


def copy_file(src_file: Path, dest_dir: Path):
    """Copy a single file to destination directory."""
    src_file = Path(src_file)
    dest_dir = Path(dest_dir)

    if not src_file.exists():
        print(f"ERROR: Source file does not exist: {src_file}")
        return False

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / src_file.name
    shutil.copy2(src_file, dest_file)
    return True


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: install_helper.py <source_dir> <target_dir>")
        print(f"Received {len(sys.argv)} arguments: {sys.argv}")
        sys.exit(1)

    source_root = Path(sys.argv[1])
    target_root = Path(sys.argv[2])

    print(f"Source: {source_root}")
    print(f"Target: {target_root}")

    print("Copying UE5 Source Query files...")

    # Copy source directories
    success = True
    success &= copy_directory(source_root / "src" / "core", target_root / "src" / "core", "*.py")
    success &= copy_directory(source_root / "src" / "indexing", target_root / "src" / "indexing", "*")

    # Copy root files
    for filename in ["ask.bat", "requirements.txt", "requirements-gpu.txt"]:
        file_path = source_root / filename
        if file_path.exists():
            copy_file(file_path, target_root)

    # Copy src/__init__.py
    src_init = source_root / "src" / "__init__.py"
    if src_init.exists():
        copy_file(src_init, target_root / "src")

    # Copy config template
    config_template = source_root / "config" / ".env.template"
    if config_template.exists():
        copy_file(config_template, target_root / "config")

    # Copy configure.bat if exists
    configure_bat = source_root / "configure.bat"
    if configure_bat.exists():
        copy_file(configure_bat, target_root)

    if success:
        print("File copying completed successfully!")
        sys.exit(0)
    else:
        print("ERROR: Some files failed to copy")
        sys.exit(1)