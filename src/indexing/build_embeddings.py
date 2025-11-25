import os, json, hashlib, time, argparse, subprocess
from pathlib import Path
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

load_dotenv(dotenv_path=Path(__file__).with_name(".env"), override=True)

SCRIPT_DIR = Path(__file__).parent
DEFAULT_ROOT = SCRIPT_DIR.parent
INDEX_DEFAULT = SCRIPT_DIR / "ai_index" / "index.json"

OUT_VECTORS = SCRIPT_DIR / "vector_store.npz"
OUT_META = SCRIPT_DIR / "vector_meta.json"
CACHE_FILE = SCRIPT_DIR / "vector_cache.json"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

EXTENSIONS = {".cpp", ".h", ".hpp", ".inl", ".cs"}
if os.getenv("INDEX_DOCS", "0") == "1":
    EXTENSIONS |= {".md", ".txt"}

MAX_FILE_CHARS = 120_000
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200
EMBED_BATCH = 32

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

def chunk_text(text: str) -> List[str]:
    if len(text) <= CHUNK_SIZE:
        return [text]
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
        vecs = model.encode(batch, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
        all_vecs.append(vecs)
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
          ps_root: str, ps_source_dirs: List[str], ps_use_engine_dirs: bool, ps_output_dir: str, ps_include_extensions: List[str],
          ps_exclude_dirs: List[str], ps_max_file_bytes: int, ps_preview_lines: int, ps_force_index: bool, ps_serve_http: bool,
          ps_bind_host: str, ps_port: int, ps_background_server: bool, ps_engine_dirs_file: str) -> None:

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

    if use_index:
        files = load_index_file(index_path)
        if verbose:
            print(f"Loaded {len(files)} files from index: {index_path}")
    else:
        files = iter_source_files(root)
        if verbose:
            print(f"Discovered {len(files)} files under root {root}")
    if not files:
        print("No source files found.")
        return

    existing_embeddings, existing_meta = load_existing()
    cache = load_cache() if incremental and not force else {}

    model = SentenceTransformer(MODEL_NAME)

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
        chunks = chunk_text(raw)
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
    # Indexer pass-through
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

    build(incremental=args.incremental,
          force=args.force,
          use_index=args.use_index,
          index_path=Path(args.index_path),
          root=Path(args.root),
          auto_build_index=args.auto_build_index,
          verbose=args.verbose,
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
