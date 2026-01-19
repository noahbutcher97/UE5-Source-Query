"""
Standalone vector store validation script.
Can be run independently or integrated into health checks.

Usage:
    python verify_vector_store.py [--verbose]

Exit codes:
    0 - Vector store is valid
    1 - Vector store is invalid or missing
    2 - Vector store exists but has warnings
"""

import sys
import json
import numpy as np
from pathlib import Path
from typing import Tuple, Optional


class VectorStoreStatus:
    """Encapsulates vector store validation results"""
    def __init__(self, exists: bool, valid: bool, message: str,
                 chunk_count: int = 0, size_mb: float = 0.0, warnings: list = None,
                 dimensions: int = 0, embed_model: str = ""):
        self.exists = exists
        self.valid = valid
        self.message = message
        self.chunk_count = chunk_count
        self.size_mb = size_mb
        self.warnings = warnings or []
        self.dimensions = dimensions
        self.embed_model = embed_model


def get_script_root() -> Path:
    """Get the root directory of the installation"""
    # This file is in src/utils/, so go up two levels
    return Path(__file__).parent.parent.parent


def validate_vector_store(verbose: bool = False) -> VectorStoreStatus:
    """
    Comprehensive validation of vector store integrity.

    Returns:
        VectorStoreStatus object with validation results
    """
    root = get_script_root()
    vector_file = root / "data" / "vector_store.npz"
    meta_file = root / "data" / "vector_meta.json"

    warnings = []

    # Check for engine version mismatch with .uproject
    try:
        # Import engine helper functions
        from ue5_query.utils.engine_helper import find_uproject_in_directory, get_engine_version_from_uproject

        # Look for .uproject file
        uproject = find_uproject_in_directory(root)
        if uproject:
            project_version = get_engine_version_from_uproject(str(uproject))
            if project_version:
                # Read indexed engine version from config
                config_file = root / "config" / ".env"
                indexed_version = None
                if config_file.exists():
                    with open(config_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith('UE_ENGINE_ROOT='):
                                engine_root = line.split('=', 1)[1].strip()
                                # Extract version from path like "C:\Program Files\Epic Games\UE_5.3\Engine"
                                import re
                                match = re.search(r'UE[_-]?(\d+\.\d+)', engine_root)
                                if match:
                                    indexed_version = match.group(1)
                                break

                # Compare versions
                if indexed_version and project_version != indexed_version:
                    warnings.append(
                        f"Engine version mismatch: Project uses {project_version} but index built from {indexed_version}. "
                        f"Consider rebuilding index with correct engine version."
                    )
                elif verbose and indexed_version:
                    print(f"[INFO] Engine version match: {project_version} (project) == {indexed_version} (index)")
    except Exception as e:
        if verbose:
            print(f"[DEBUG] Failed to check engine version: {e}")

    # Check existence
    if not vector_file.exists() and not meta_file.exists():
        return VectorStoreStatus(
            exists=False,
            valid=False,
            message="Vector store not built. Run rebuild-index.bat to create it."
        )

    # Check for partial presence (data corruption indicator)
    if vector_file.exists() and not meta_file.exists():
        return VectorStoreStatus(
            exists=True,
            valid=False,
            message=f"Vector store exists but metadata missing: {meta_file}\n"
                    f"This indicates corruption. Rebuild with: rebuild-index.bat --force"
        )

    if meta_file.exists() and not vector_file.exists():
        return VectorStoreStatus(
            exists=True,
            valid=False,
            message=f"Metadata exists but vector store missing: {vector_file}\n"
                    f"This indicates corruption. Rebuild with: rebuild-index.bat --force"
        )

    # Both files exist - validate integrity
    try:
        # Check file sizes
        vector_size = vector_file.stat().st_size
        meta_size = meta_file.stat().st_size
        vector_size_mb = vector_size / (1024 * 1024)

        if vector_size == 0:
            return VectorStoreStatus(
                exists=True,
                valid=False,
                message="Vector store file is empty. Rebuild with: rebuild-index.bat --force"
            )

        if meta_size == 0:
            return VectorStoreStatus(
                exists=True,
                valid=False,
                message="Metadata file is empty. Rebuild with: rebuild-index.bat --force"
            )

        # Load and validate structure
        try:
            vectors = np.load(vector_file, allow_pickle=False)
            embeddings = vectors['embeddings']
        except Exception as e:
            return VectorStoreStatus(
                exists=True,
                valid=False,
                message=f"Failed to load vector store: {e}\n"
                        f"File may be corrupted. Rebuild with: rebuild-index.bat --force"
            )

        try:
            meta_data = json.loads(meta_file.read_text(encoding='utf-8'))
            items = meta_data.get('items', [])
        except json.JSONDecodeError as e:
            return VectorStoreStatus(
                exists=True,
                valid=False,
                message=f"Metadata JSON is corrupted: {e}\n"
                        f"Rebuild with: rebuild-index.bat --force"
            )
        except Exception as e:
            return VectorStoreStatus(
                exists=True,
                valid=False,
                message=f"Failed to read metadata: {e}\n"
                        f"Rebuild with: rebuild-index.bat --force"
            )

        # Validate alignment
        if len(embeddings) != len(items):
            return VectorStoreStatus(
                exists=True,
                valid=False,
                message=f"Vector/metadata mismatch: {len(embeddings)} embeddings != {len(items)} metadata entries\n"
                        f"Rebuild with: rebuild-index.bat --force",
                chunk_count=len(items),
                size_mb=vector_size_mb
            )

        # Check for minimum viable size
        if len(items) < 100:
            warnings.append(f"Only {len(items)} chunks indexed - unusually small. Expected thousands for full UE5 source.")

        # Detect configured embed model and expected dimensions
        embed_model = 'sentence-transformers/all-MiniLM-L6-v2'  # Default

        # Read config directly from .env file (avoid import issues)
        config_file = root / "config" / ".env"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('EMBED_MODEL='):
                            embed_model = line.split('=', 1)[1].strip()
                            if verbose:
                                print(f"[DEBUG] Read EMBED_MODEL from config: {embed_model}")
                            break
            except Exception as e:
                if verbose:
                    print(f"[DEBUG] Failed to read config file, using default. Error: {e}")

        # Map known models to expected dimensions
        model_dims = {
            'sentence-transformers/all-MiniLM-L6-v2': 384,
            'microsoft/unixcoder-base': 768,
            'sentence-transformers/all-mpnet-base-v2': 768,
        }

        expected_dims = model_dims.get(embed_model, None)
        actual_dims = embeddings.shape[1]

        # Infer actual model from dimensions
        # Prefer more specific models (unixcoder for code, mpnet for general)
        def infer_model_from_dims(dims: int) -> Optional[str]:
            if dims == 384:
                return 'sentence-transformers/all-MiniLM-L6-v2'
            elif dims == 768:
                # Prefer unixcoder for code-specific embeddings
                return 'microsoft/unixcoder-base'
            return None

        inferred_model = infer_model_from_dims(actual_dims)

        if expected_dims and actual_dims != expected_dims:
            # Config doesn't match actual vector store
            if inferred_model:
                warnings.append(f"Vector store uses {actual_dims}D embeddings ({inferred_model}), but config specifies '{embed_model}' ({expected_dims}D). Consider updating config to match.")
                # Use inferred model for display
                embed_model = inferred_model
            else:
                warnings.append(f"Embedding dimensions are {actual_dims}, but configured model '{embed_model}' expects {expected_dims}. Vector store may have been built with a different model. Consider rebuilding.")
        elif expected_dims is None:
            # Unknown configured model - try to infer
            if inferred_model:
                embed_model = inferred_model
                if verbose:
                    print(f"[INFO] Inferred model from dimensions: {inferred_model} ({actual_dims}D)")
            else:
                # Unknown model and unknown dimensions
                if verbose:
                    print(f"[INFO] Unknown embed model '{embed_model}', cannot validate dimensions. Actual dimensions: {actual_dims}")

        # Check for NaN or inf values
        if np.any(np.isnan(embeddings)) or np.any(np.isinf(embeddings)):
            return VectorStoreStatus(
                exists=True,
                valid=False,
                message="Vector store contains NaN or Inf values. Rebuild with: rebuild-index.bat --force",
                chunk_count=len(items),
                size_mb=vector_size_mb
            )

        # Success!
        return VectorStoreStatus(
            exists=True,
            valid=True,
            message=f"Vector store is valid and ready to use.",
            chunk_count=len(items),
            size_mb=vector_size_mb,
            warnings=warnings,
            dimensions=actual_dims,
            embed_model=embed_model
        )

    except Exception as e:
        return VectorStoreStatus(
            exists=True,
            valid=False,
            message=f"Unexpected error during validation: {e}\n"
                    f"Consider rebuilding with: rebuild-index.bat --force"
        )


def print_status(status: VectorStoreStatus, verbose: bool = False):
    """Print validation results in user-friendly format"""
    print("\n" + "="*70)
    print("Vector Store Validation")
    print("="*70)
    print()

    if not status.exists:
        print("[!] NOT BUILT")
        print(f"    {status.message}")
        print()
        print("Next steps:")
        print("  1. Run: rebuild-index.bat")
        print("  2. Wait for indexing to complete (may take 5-15 minutes)")
        print()
        return

    if not status.valid:
        print("[X] INVALID")
        print(f"    {status.message}")
        if status.chunk_count > 0:
            print(f"    Chunks: {status.chunk_count}")
            print(f"    Size: {status.size_mb:.1f} MB")
        print()
        return

    # Valid store
    print("[OK] VALID")
    print(f"    {status.message}")
    print(f"    Chunks: {status.chunk_count:,}")
    print(f"    Size: {status.size_mb:.1f} MB")
    if status.dimensions and status.embed_model:
        print(f"    Dimensions: {status.dimensions} ({status.embed_model})")
    elif status.dimensions:
        print(f"    Dimensions: {status.dimensions}")

    if status.warnings:
        print()
        print("WARNINGS:")
        for warning in status.warnings:
            print(f"  [!] {warning}")

    print()
    print("="*70)

    if verbose and status.valid:
        print("\nDetailed Statistics:")
        print(f"  Embeddings shape: ({status.chunk_count}, 384)")
        print(f"  Storage format: NumPy compressed (.npz)")
        print(f"  Metadata format: JSON")
        print()


def main():
    """Main entry point"""
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    status = validate_vector_store(verbose)
    print_status(status, verbose)

    # Exit codes
    if not status.exists or not status.valid:
        sys.exit(1)  # Invalid or missing
    elif status.warnings:
        sys.exit(2)  # Valid but has warnings
    else:
        sys.exit(0)  # All good


if __name__ == "__main__":
    main()
