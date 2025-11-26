import os, json, hashlib, time, argparse, subprocess, sys
from pathlib import Path
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv(dotenv_path=Path(__file__).with_name(".env"), override=True)

SCRIPT_DIR = Path(__file__).parent
DEFAULT_ROOT = SCRIPT_DIR.parent
INDEX_DEFAULT = SCRIPT_DIR / "ai_index" / "index.json"

OUT_VECTORS = SCRIPT_DIR / "vector_store.npz"
OUT_META = SCRIPT_DIR / "vector_meta.json"
CACHE_FILE = SCRIPT_DIR / "vector_cache.json"

# Model configuration - can be overridden via environment variable
DEFAULT_MODEL = "microsoft/unixcoder-base"  # Code-trained model (768 dims)
MODEL_NAME = os.getenv("EMBED_MODEL", DEFAULT_MODEL)

# GPU configuration
USE_GPU = os.getenv("USE_GPU", "auto")  # auto, true, false
GPU_DEVICE = None  # Will be set during model initialization

EXTENSIONS = {".cpp", ".h", ".hpp", ".inl", ".cs"}
if os.getenv("INDEX_DOCS", "0") == "1":
    EXTENSIONS |= {".md", ".txt"}

MAX_FILE_CHARS = 120_000

# Chunking configuration
USE_SEMANTIC_CHUNKING = os.getenv("SEMANTIC_CHUNKING", "1") == "1"  # Default: ON
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "2000" if USE_SEMANTIC_CHUNKING else "1500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
EMBED_BATCH = 32

# Import semantic chunker if enabled
if USE_SEMANTIC_CHUNKING:
    try:
        from utils.semantic_chunker import SemanticChunker
        SEMANTIC_CHUNKER = SemanticChunker(
            max_chunk_size=CHUNK_SIZE,
            min_chunk_size=500,
            overlap=CHUNK_OVERLAP
        )
    except ImportError:
        print("Warning: Could not import SemanticChunker, falling back to character-based chunking")
        USE_SEMANTIC_CHUNKING = False
        SEMANTIC_CHUNKER = None
else:
    SEMANTIC_CHUNKER = None

def sha256(s: str) -> str:
    import hashlib as _hl
    return _hl.sha256(s.encode("utf-8", errors="ignore")).hexdigest()

def load_index_file(index_path: Path) -> List[Path]:
    if not index_path.exists():
        raise SystemExit(f"Index not found: {index_path}")
    try:
        data = json.loads(index_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"Invalid index JSON: {e}")
    files = []
    for f in data.get("files", []):
        fp = f.get("fullPath") or f.get("path")
        if not fp:
            continue
        p = Path(fp)
        if p.exists() and p.is_file() and p.suffix.lower() in EXTENSIONS:
            files.append(p)
    if not files:
        raise SystemExit("No usable files in index.")
    return files

def iter_source_files(root: Path) -> List[Path]:
    return [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONS]

# ===== Modular File Discovery System =====

# Default UE5 exclusion patterns
DEFAULT_UE5_EXCLUDES = [
    # Build artifacts
    "Intermediate", "Binaries", "DerivedDataCache", "Saved",
    # IDE files
    ".vs", ".vscode", ".idea",
    # Version control
    ".git", ".hg", ".svn",
    # Platform-specific
    "Build/BatchFiles", "Build/Android", "Build/IOS", "Build/Linux", "Build/Mac",
    # Third-party
    "ThirdParty",
    # Documentation/assets
    "Documentation", "Content", "Extras"
]

def should_exclude_path(path: Path, exclude_patterns: List[str]) -> bool:
    """
    Check if any part of path matches exclusion patterns.
    Uses path component matching (not substring).
    """
    path_parts = path.parts
    return any(pattern in path_parts for pattern in exclude_patterns)

def load_dirs_from_file(file_path: Path, verbose: bool = False) -> List[Path]:
    """Load and validate directories from text file."""
    if not file_path.exists():
        return []

    dirs = []
    for line_num, line in enumerate(file_path.read_text(encoding='utf-8').splitlines(), 1):
        line = line.strip()

        # Skip comments and empty lines
        if not line or line.startswith('#'):
            continue

        path = Path(line)
        if path.exists() and path.is_dir():
            dirs.append(path)
        elif verbose:
            print(f"Warning line {line_num}: Skipping invalid directory: {line}")

    return dirs

def load_exclusions_from_file(file_path: Path, verbose: bool = False) -> tuple:
    """
    Load exclusion patterns from .indexignore file.

    Returns:
        (dir_patterns, file_patterns) - Separate directory and file patterns
    """
    if not file_path.exists():
        return [], []

    dir_patterns = []
    file_patterns = []

    for line_num, line in enumerate(file_path.read_text(encoding='utf-8').splitlines(), 1):
        line = line.strip()

        # Skip comments and empty lines
        if not line or line.startswith('#'):
            continue

        # Detect pattern type
        if '*' in line or '?' in line or '[' in line:
            # Glob pattern = file pattern
            file_patterns.append(line)
        else:
            # Plain text = directory pattern
            dir_patterns.append(line)

        if verbose:
            pattern_type = "file" if line in file_patterns else "directory"
            print(f"  Loaded {pattern_type} exclusion: {line}")

    return dir_patterns, file_patterns

def load_all_indexignore_files(roots: List[Path], verbose: bool = False) -> tuple:
    """
    Load .indexignore files from multiple locations and merge.

    Search order:
    1. Current working directory
    2. Each root directory
    3. User home directory (~/.indexignore)
    """
    all_dir_patterns = []
    all_file_patterns = []

    # Check locations in order
    locations = [
        Path.cwd() / ".indexignore",    # Current directory
        Path.home() / ".indexignore"    # User home
    ]

    # Add root directories
    for root in roots:
        locations.append(root / ".indexignore")

    for location in locations:
        if location.exists():
            if verbose:
                print(f"Loading exclusions from: {location}")

            dir_pats, file_pats = load_exclusions_from_file(location, verbose)
            all_dir_patterns.extend(dir_pats)
            all_file_patterns.extend(file_pats)

    return all_dir_patterns, all_file_patterns

def matches_extension(file_path: Path, extensions: set) -> bool:
    """Check if file extension is in allowed set."""
    return file_path.suffix.lower() in extensions

def matches_file_pattern(file_path: Path, include_patterns: List[str] = None,
                        exclude_patterns: List[str] = None) -> bool:
    """
    Check if filename matches include/exclude patterns.
    Uses fnmatch for glob patterns.

    Priority: Exclusions override inclusions
    """
    from fnmatch import fnmatch

    filename = file_path.name

    # Check exclusions first (blacklist wins)
    if exclude_patterns:
        for pattern in exclude_patterns:
            if fnmatch(filename, pattern):
                return False

    # Check inclusions (if specified, must match)
    if include_patterns:
        return any(fnmatch(filename, pattern) for pattern in include_patterns)

    # No patterns = include by default
    return True

def passes_filters(file_path: Path, extensions: set, exclude_dirs: List[str],
                  include_files: List[str] = None, exclude_files: List[str] = None) -> bool:
    """
    Complete filtering pipeline.
    All filters must pass for file to be included.
    """
    # Layer 1: Extension filter
    if not matches_extension(file_path, extensions):
        return False

    # Layer 2: Directory exclusion
    if should_exclude_path(file_path, exclude_dirs):
        return False

    # Layer 3: File pattern filter
    if not matches_file_pattern(file_path, include_files, exclude_files):
        return False

    return True

def discover_source_files(roots: List[Path] = None, exclude_patterns: List[str] = None,
                         extensions: set = None, include_file_patterns: List[str] = None,
                         exclude_file_patterns: List[str] = None, verbose: bool = False) -> List[Path]:
    """
    Unified file discovery supporting all input methods.

    Args:
        roots: List of directories to scan recursively
        exclude_patterns: Path patterns to exclude (e.g., ["Intermediate", "Binaries"])
        extensions: File extensions to include (defaults to EXTENSIONS global)
        include_file_patterns: Only include files matching these patterns (glob)
        exclude_file_patterns: Exclude files matching these patterns (glob)
        verbose: Print discovery progress

    Returns:
        Deduplicated, sorted list of source file paths
    """
    if extensions is None:
        extensions = EXTENSIONS

    if exclude_patterns is None:
        exclude_patterns = []

    if not roots:
        return []

    all_files = set()

    for root in roots:
        if not root.exists() or not root.is_dir():
            if verbose:
                print(f"Warning: Skipping non-existent directory: {root}")
            continue

        if verbose:
            print(f"Scanning directory: {root}")

        # Recursively find all files
        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue

            # Apply all filters
            if passes_filters(file_path, extensions, exclude_patterns,
                            include_file_patterns, exclude_file_patterns):
                all_files.add(file_path)

    # Return sorted, deduplicated list
    return sorted(all_files)

# ===== End Modular File Discovery System =====

def chunk_text(text: str, file_path: str = "") -> List[str]:
    """
    Chunk text using either semantic or character-based chunking.

    Args:
        text: Text to chunk
        file_path: Optional file path for semantic chunking context

    Returns:
        List of text chunks
    """
    if len(text) <= CHUNK_SIZE:
        return [text]

    # Use semantic chunking if enabled and chunker is available
    if USE_SEMANTIC_CHUNKING and SEMANTIC_CHUNKER is not None:
        try:
            return SEMANTIC_CHUNKER.chunk(text, file_path)
        except Exception as e:
            # Fall back to character-based on error
            print(f"Warning: Semantic chunking failed for {file_path}: {e}")
            pass

    # Fallback: character-based chunking
    chunks = []
    step = CHUNK_SIZE - CHUNK_OVERLAP
    for start in range(0, len(text), step):
        chunk = text[start:start + CHUNK_SIZE]
        if len(chunk) < 300 and start != 0:
            break
        chunks.append(chunk)
    return chunks

def load_existing() -> tuple[Optional[np.ndarray], Optional[List[dict]]]:
    if not OUT_VECTORS.exists() or not OUT_META.exists():
        return None, None
    try:
        arr = np.load(OUT_VECTORS)["embeddings"]
        meta = json.loads(OUT_META.read_text())["items"]
        return arr, meta
    except (KeyError, json.JSONDecodeError, OSError) as e:
        print(f"Warning: Failed to load existing data: {e}")
        return None, None

def load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return {}

def save_cache(cache: dict) -> None:
    CACHE_FILE.write_text(json.dumps(cache, indent=2))

def embed_batches(model: SentenceTransformer, texts: List[str]) -> np.ndarray:
    if not texts:
        return np.zeros((0, model.get_sentence_embedding_dimension()))
    bar = tqdm(total=len(texts), desc="Embedding chunks", unit="chunk") if tqdm else None
    all_vecs = []
    for i in range(0, len(texts), EMBED_BATCH):
        batch = texts[i:i + EMBED_BATCH]
        try:
            # Set max_seq_length to model's limit (512 for most transformers)
            # truncate=True ensures oversized chunks are handled gracefully
            vecs = model.encode(
                batch,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
                truncate=True,  # Automatically truncate oversized chunks
                max_length=512  # Explicit maximum sequence length
            )
            all_vecs.append(vecs)
        except IndexError as e:
            # Fallback: encode chunks one by one with truncation
            print(f"\nWarning: Batch encoding failed at index {i}, encoding individually...")
            for text in batch:
                try:
                    vec = model.encode(
                        [text],
                        convert_to_numpy=True,
                        normalize_embeddings=True,
                        show_progress_bar=False,
                        truncate=True,
                        max_length=512
                    )
                    all_vecs.append(vec)
                except Exception as e2:
                    # Skip problematic chunk and use zero vector
                    print(f"Error embedding chunk (skipping): {str(e2)[:100]}")
                    zero_vec = np.zeros((1, model.get_sentence_embedding_dimension()))
                    all_vecs.append(zero_vec)
        if bar: bar.update(len(batch))
    if bar: bar.close()
    return np.vstack(all_vecs)

def is_index_stale(index_path: Path, root: Path) -> bool:
    if not index_path.exists():
        return True
    index_mtime = index_path.stat().st_mtime
    for p in iter_source_files(root):
        if p.stat().st_mtime > index_mtime:
            return True
    return False

def is_index_empty(index_path: Path) -> bool:
    if not index_path.exists():
        return True
    try:
        data = json.loads(index_path.read_text(encoding="utf-8-sig"))
        return len(data.get("files", [])) == 0
    except json.JSONDecodeError:
        return True

def _quote(a: str) -> str:
    return f'"{a}"' if (" " in a or "\t" in a) else a

def _invoke_indexer(args_list: list[str], verbose: bool):
    bat_path = SCRIPT_DIR / "BuildSourceIndexAdmin.bat"
    if not bat_path.exists():
        raise SystemExit(f"Batch file not found: {bat_path}")
    # Quote args with spaces
    safe_args = [_quote(a) for a in args_list]
    cmd = [str(bat_path)] + safe_args
    if verbose:
        print("Indexer command:", " ".join(cmd))
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        raise SystemExit("Index build timed out.")
    if result.returncode != 0:
        if verbose:
            print("STDOUT:\n", result.stdout)
            print("STDERR:\n", result.stderr)
        raise SystemExit("Index build failed. Run manually with elevated privileges if needed.")
    if verbose:
        print("Index build output:\n", result.stdout.strip())

def build(incremental: bool, force: bool, use_index: bool, index_path: Path, root: Path, auto_build_index: bool, verbose: bool,
          dirs: List[str] = None, dirs_file: str = None, extensions: set = None,
          exclude_patterns: List[str] = None, include_file_patterns: List[str] = None, exclude_file_patterns: List[str] = None,
          ps_root: str = "", ps_source_dirs: List[str] = None, ps_use_engine_dirs: bool = False, ps_output_dir: str = "",
          ps_include_extensions: List[str] = None, ps_exclude_dirs: List[str] = None,
          ps_max_file_bytes: int = 10*1024*1024, ps_preview_lines: int = 20, ps_force_index: bool = False,
          ps_serve_http: bool = False, ps_bind_host: str = "127.0.0.1", ps_port: int = 8008,
          ps_background_server: bool = False, ps_engine_dirs_file: str = "EngineDirs.txt") -> None:

    def build_args():
        args_list = []
        if ps_root:
            args_list.extend(['-Root', ps_root])
        for sd in ps_source_dirs:
            args_list.extend(['-SourceDirs', sd])
        if ps_use_engine_dirs:
            args_list.append('-UseEngineDirs')
        if ps_engine_dirs_file:
            args_list.extend(['-EngineDirsFile', ps_engine_dirs_file])
        if ps_output_dir:
            args_list.extend(['-OutputDir', ps_output_dir])
        for ie in ps_include_extensions:
            args_list.extend(['-IncludeExtensions', ie])
        for ed in ps_exclude_dirs:
            args_list.extend(['-ExcludeDirs', ed])
        args_list.extend(['-MaxFileBytes', str(ps_max_file_bytes)])
        args_list.extend(['-PreviewLines', str(ps_preview_lines)])
        if ps_force_index:
            args_list.append('-Force')
        if ps_serve_http:
            args_list.append('-ServeHttp')
        args_list.extend(['-BindHost', ps_bind_host])
        args_list.extend(['-Port', str(ps_port)])
        if ps_background_server:
            args_list.append('-BackgroundServer')
        if verbose:
            args_list.append('-Verbose')
        return args_list

    if use_index and auto_build_index:
        need_build = (not index_path.exists()) or is_index_empty(index_path)
        stale = False
        if not need_build and is_index_stale(index_path, root):
            stale = True
        if need_build or stale:
            if verbose:
                print(("Building index..." if need_build else "Rebuilding stale index..."))
            _invoke_indexer(build_args(), verbose)

    # Determine input mode and discover files
    if use_index:
        # Mode 1: Use pre-built index (backward compatibility)
        files = load_index_file(index_path)
        if verbose:
            print(f"Loaded {len(files)} files from index")

    elif dirs_file:
        # Mode 2: Load directories from file
        roots = load_dirs_from_file(Path(dirs_file), verbose=verbose)
        if verbose:
            print(f"Loaded {len(roots)} directories from {dirs_file}")
        files = discover_source_files(
            roots=roots,
            exclude_patterns=exclude_patterns,
            extensions=extensions,
            include_file_patterns=include_file_patterns,
            exclude_file_patterns=exclude_file_patterns,
            verbose=verbose
        )

    elif dirs:
        # Mode 3: Use directories from CLI
        roots = [Path(d) for d in dirs if Path(d).exists()]
        if verbose:
            print(f"Scanning {len(roots)} directories from --dirs")
        files = discover_source_files(
            roots=roots,
            exclude_patterns=exclude_patterns,
            extensions=extensions,
            include_file_patterns=include_file_patterns,
            exclude_file_patterns=exclude_file_patterns,
            verbose=verbose
        )

    else:
        # Mode 4: Default to single root with exclusions
        if verbose:
            print(f"Scanning default root: {root}")
        files = discover_source_files(
            roots=[root],
            exclude_patterns=exclude_patterns,
            extensions=extensions,
            include_file_patterns=include_file_patterns,
            exclude_file_patterns=exclude_file_patterns,
            verbose=verbose
        )

    if not files:
        print("No source files found. Check paths and exclusion patterns.")
        return

    existing_embeddings, existing_meta = load_existing()
    cache = load_cache() if incremental and not force else {}

    # Initialize model with GPU support
    global GPU_DEVICE
    model = SentenceTransformer(MODEL_NAME)

    # Auto-detect or configure GPU
    if USE_GPU == "auto":
        try:
            import torch
            if torch.cuda.is_available():
                GPU_DEVICE = "cuda"
                model = model.to(GPU_DEVICE)
                if verbose:
                    print(f"GPU detected: {torch.cuda.get_device_name(0)}")
                    print(f"Using CUDA for embeddings (expect 6-10x speedup)")
        except ImportError:
            if verbose:
                print("PyTorch not available, using CPU")
    elif USE_GPU == "true":
        try:
            import torch
            GPU_DEVICE = "cuda"
            model = model.to(GPU_DEVICE)
            if verbose:
                print(f"GPU forced: {torch.cuda.get_device_name(0)}")
        except Exception as e:
            print(f"Error: Failed to use GPU: {e}")
            raise

    new_texts, new_meta = [], []
    reused_embeddings, reused_meta = [], []

    iterator = tqdm(files, desc="Scanning files", unit="file") if tqdm else files
    for file in iterator:
        try:
            raw = file.read_text(encoding="utf-8", errors="ignore")
        except OSError as e:
            if verbose:
                print(f"Warning: Could not read {file}: {e}")
            continue
        if len(raw) > MAX_FILE_CHARS:
            continue
        file_hash = sha256(raw)
        chunks = chunk_text(raw, str(file))
        if incremental and not force and file_hash in cache and cache[file_hash]["count"] == len(chunks):
            if existing_embeddings is not None:
                path_str = str(file)
                for idx, m in enumerate(existing_meta):
                    if m.get("path") == path_str:
                        reused_embeddings.append(existing_embeddings[idx])
                        reused_meta.append(m)
                        break
            continue
        for idx, chunk in enumerate(chunks):
            new_texts.append(chunk)
            new_meta.append({
                "path": str(file),
                "chunk_index": idx,
                "total_chunks": len(chunks),
                "chars": len(chunk)
            })
        cache[file_hash] = {"path": str(file), "count": len(chunks)}

    if not new_texts and reused_embeddings:
        print("No changes detected; nothing new to embed.")
        return

    if verbose:
        print(f"New chunks={len(new_texts)} Reused={len(reused_meta)}")

    t_embed_start = time.time()
    new_embeddings = embed_batches(model, new_texts)

    if reused_embeddings:
        embeddings = np.vstack([np.vstack(reused_embeddings), new_embeddings]) if new_embeddings.size else np.vstack(reused_embeddings)
        meta = reused_meta + new_meta
    else:
        embeddings = new_embeddings
        meta = new_meta

    np.savez_compressed(OUT_VECTORS, embeddings=embeddings)
    OUT_META.write_text(json.dumps({"items": meta}, indent=2))
    if incremental or force:
        save_cache(cache)

    print(f"Done. Total chunks={len(meta)} (new={len(new_meta)} reused={len(reused_meta)})")
    print(f"Embedding phase {time.time() - t_embed_start:.1f}s")
    print(f"Wrote {OUT_VECTORS.name}, {OUT_META.name}")

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--incremental", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--use-index", action="store_true", help="Use prebuilt ai_index/index.json file list.")
    ap.add_argument("--index-path", default=str(INDEX_DEFAULT), help="Path to index.json.")
    ap.add_argument("--root", default=str(DEFAULT_ROOT), help="Fallback root if not using index.")
    ap.add_argument("--auto-build-index", action="store_true", default=True, help="Automatically build index if missing or stale.")
    ap.add_argument("--verbose", action="store_true", help="Enable verbose logging.")

    # New modular file discovery arguments
    ap.add_argument("--dirs", nargs="+", help="Directories to scan (can specify multiple)")
    ap.add_argument("--dirs-file", help="File containing directory list (e.g., EngineDirs.txt)")

    # Extension filtering (Layer 1)
    ap.add_argument("--extensions", nargs="+", default=[".cpp", ".h", ".hpp", ".inl", ".cs"],
                    help="File extensions to include (default: .cpp .h .hpp .inl .cs)")
    ap.add_argument("--include-docs", action="store_true",
                    help="Also index documentation files (.md, .txt)")

    # Directory exclusion (Layer 2)
    ap.add_argument("--exclude", action="append", default=[],
                    help="Directory patterns to exclude (added to defaults)")
    ap.add_argument("--no-default-excludes", action="store_true",
                    help="Disable default UE5 exclusions (Intermediate, Binaries, etc.)")

    # File pattern filtering (Layer 3)
    ap.add_argument("--include-files", nargs="+",
                    help="Include only files matching these patterns (glob: *Vehicle*.cpp)")
    ap.add_argument("--exclude-files", nargs="+",
                    help="Exclude files matching these patterns (glob: *Test*.cpp)")

    # .indexignore support
    ap.add_argument("--indexignore", help="Path to specific .indexignore file to load")
    ap.add_argument("--no-indexignore", action="store_true",
                    help="Disable automatic .indexignore file loading")

    # Indexer pass-through (DEPRECATED - for backward compatibility only)
    ap.add_argument("--Root", default="", help="Primary root directory to scan.")
    ap.add_argument("--SourceDirs", action='append', default=[], help="Additional source directories to scan.")
    ap.add_argument("--UseEngineDirs", action='store_true', help="Scan predefined Unreal Engine directories.")
    ap.add_argument("--EngineDirsFile", default="EngineDirs.txt", help="File listing engine directories.")
    ap.add_argument("--OutputDir", default=str(SCRIPT_DIR / "ai_index"), help="Directory for index.json.")
    ap.add_argument("--IncludeExtensions", action='append', default=['.cpp', '.h', '.hpp', '.inl', '.cs'], help="File extensions to include.")
    ap.add_argument("--ExcludeDirs", action='append', default=[], help="Directories to exclude.")
    ap.add_argument("--MaxFileBytes", type=int, default=10*1024*1024, help="Max file size in bytes.")
    ap.add_argument("--PreviewLines", type=int, default=20, help="Lines to include as preview.")
    ap.add_argument("--Force", action='store_true', help="Overwrite output directory if it exists.")
    ap.add_argument("--ServeHttp", action='store_true', help="Start HTTP server after indexing.")
    ap.add_argument("--BindHost", default='127.0.0.1', help="Host for HTTP server.")
    ap.add_argument("--Port", type=int, default=8008, help="Port for HTTP server.")
    ap.add_argument("--BackgroundServer", action='store_true', help="Run HTTP server in background.")
    args = ap.parse_args()

    # Build extension set
    extensions = set(args.extensions)
    if args.include_docs:
        extensions.update({".md", ".txt"})

    # Load .indexignore patterns (unless disabled)
    indexignore_dir_pats = []
    indexignore_file_pats = []

    if not args.no_indexignore:
        if args.indexignore:
            # Load specific .indexignore file
            indexignore_dir_pats, indexignore_file_pats = load_exclusions_from_file(
                Path(args.indexignore), verbose=args.verbose
            )
        else:
            # Auto-discover .indexignore files
            roots_to_check = []
            if args.dirs:
                roots_to_check = [Path(d) for d in args.dirs]
            elif args.dirs_file:
                roots_to_check = load_dirs_from_file(Path(args.dirs_file))
            elif args.root:
                roots_to_check = [Path(args.root)]

            if roots_to_check:
                indexignore_dir_pats, indexignore_file_pats = load_all_indexignore_files(
                    roots_to_check, verbose=args.verbose
                )

    # Build exclusion patterns (merge .indexignore + CLI + defaults)
    exclude_patterns = list(DEFAULT_UE5_EXCLUDES) if not args.no_default_excludes else []
    exclude_patterns.extend(indexignore_dir_pats)  # Add .indexignore patterns
    exclude_patterns.extend(args.exclude)          # Add CLI patterns

    # Build file exclusion patterns (merge .indexignore + CLI)
    exclude_file_patterns = list(indexignore_file_pats)
    if args.exclude_files:
        exclude_file_patterns.extend(args.exclude_files)

    build(incremental=args.incremental,
          force=args.force,
          use_index=args.use_index,
          index_path=Path(args.index_path),
          root=Path(args.root),
          auto_build_index=args.auto_build_index,
          verbose=args.verbose,
          # New modular discovery parameters
          dirs=args.dirs,
          dirs_file=args.dirs_file,
          extensions=extensions,
          exclude_patterns=exclude_patterns,
          include_file_patterns=args.include_files,
          exclude_file_patterns=exclude_file_patterns,
          ps_root=args.Root,
          ps_source_dirs=args.SourceDirs,
          ps_use_engine_dirs=args.UseEngineDirs,
          ps_output_dir=args.OutputDir,
          ps_include_extensions=args.IncludeExtensions,
          ps_exclude_dirs=args.ExcludeDirs,
          ps_max_file_bytes=args.MaxFileBytes,
          ps_preview_lines=args.PreviewLines,
          ps_force_index=args.Force,
          ps_serve_http=args.ServeHttp,
          ps_bind_host=args.BindHost,
          ps_port=args.Port,
          ps_background_server=args.BackgroundServer,
          ps_engine_dirs_file=args.EngineDirsFile)

if __name__ == "__main__":
    main()
