# python
# ===== File: QueryEmbeddings.py =====
"""
Enhanced query utility:
  python QueryEmbeddings.py "your question here"
Flags:
  --top-k N            How many chunks to return (default 5)
  --json               Output answer + matches as JSON
  --dry-run            Do not call Anthropic; just show selected docs
  --no-api             Skip API call (alias of --dry-run)
  --copy               Copy the full text of matched snippets to the clipboard
  --pattern SUBSTR     Only consider files whose path contains substring
  --extensions .cpp,.h Filter by comma-separated extensions
  --show-prompt        Print full constructed prompt before (or without) API
  --max-chars N        Override snippet truncation length
  --model NAME         Override embedding model (env EMBED_MODEL also works)
  --api-model NAME     Override Anthropic model (env ANTHROPIC_MODEL also works)
"""
import sys, os, json, time, argparse, subprocess
import numpy as np
from pathlib import Path
from functools import lru_cache
from sentence_transformers import SentenceTransformer
from anthropic import Anthropic
from dotenv import load_dotenv

TOOL_ROOT = Path(__file__).parent.parent.parent  # Go up to D:\DevTools\UE5-Source-Query
load_dotenv(dotenv_path=TOOL_ROOT / "config" / ".env", override=True)

SCRIPT_DIR = Path(__file__).parent

# Vector store location - can be overridden via environment variable
# Priority: ENV var > default (TOOL_ROOT/data)
DEFAULT_VECTOR_DIR = os.getenv("VECTOR_OUTPUT_DIR", str(TOOL_ROOT / "data"))
VECTORS = Path(DEFAULT_VECTOR_DIR) / "vector_store.npz"
META = Path(DEFAULT_VECTOR_DIR) / "vector_meta.json"

DEFAULT_EMBED_MODEL = "microsoft/unixcoder-base"  # Code-trained model (768 dims)
DEFAULT_API_MODEL = "claude-3-haiku-20240307"

# Global model singleton (lazy)
_MODEL = None

def get_model(name: str):
    global _MODEL
    if _MODEL is None or getattr(_MODEL, "_name", "") != name:
        _MODEL = SentenceTransformer(name)
        _MODEL._name = name
    return _MODEL

def load_store():
    if not VECTORS.exists() or not META.exists():
        raise SystemExit("Vector store missing. Run: python BuildEmbeddings.py --use-index")
    # memory map for large arrays
    arr = np.load(VECTORS, mmap_mode="r")["embeddings"]
    meta = json.loads(META.read_text())["items"]
    return arr, meta

@lru_cache(maxsize=64)
def embed_query_cached(q: str, model_name: str):
    model = get_model(model_name)
    return model.encode([q], convert_to_numpy=True, normalize_embeddings=True)[0]

def filter_meta(meta, pattern: str, extensions_set):
    if not pattern and not extensions_set:
        return meta
    out = []
    for m in meta:
        p = m["path"]
        if pattern and pattern.lower() not in p.lower():
            continue
        if extensions_set:
            suffix = Path(p).suffix.lower()
            if suffix not in extensions_set:
                continue
        out.append(m)
    return out

def select(qvec, embeddings, meta, k):
    # meta and embeddings aligned by index
    sims = embeddings @ qvec
    idxs = np.argsort(-sims)[:k]
    out = []
    for i in idxs:
        m = meta[i].copy()
        m["score"] = float(sims[i])
        out.append(m)
    return out

def load_snippet(record, max_chars: int):
    try:
        # This now loads the full file content to get the exact chunk
        text = Path(record["path"]).read_text(encoding="utf-8", errors="ignore")
        chunk_size = record.get("chunk_size", 1500)
        chunk_overlap = record.get("chunk_overlap", 200)
        step = chunk_size - chunk_overlap
        start = record["chunk_index"] * step
        return text[start:start + chunk_size]
    except Exception:
        return ""

def build_prompt(question, hits):
    sections = []
    for i, h in enumerate(hits, 1):
        snippet = load_snippet(h, -1) # Load full snippet
        sections.append(
            f"[Doc {i} score={h['score']:.3f} path={h['path']} chunk={h['chunk_index']+1}/{h['total_chunks']}]\n{snippet}"
        )
    return (
            "You are a domain assistant. Use ONLY the provided context to answer.\n"
            "If uncertain, say you are not sure.\n\n"
            + "\n\n".join(sections)
            + f"\n\nQuestion:\n{question}\n\nAnswer:"
    )

def format_matches(matches):
    lines = []
    for m in matches:
        lines.append(f"{m['score']:.3f} | {m['path']} | chunk {m['chunk_index']+1}/{m['total_chunks']} chars={m.get('chars','?')}")
    return "\n".join(lines)

def copy_to_clipboard(text: str):
    try:
        subprocess.run(["clip"], input=text.strip(), text=True, check=True)
        print("Copied context to clipboard.")
    except (FileNotFoundError, subprocess.SubprocessError) as e:
        print(f"Error: Failed to copy to clipboard: {e}", file=sys.stderr)

def query(question: str, top_k: int, embed_model_name: str, api_model_name: str, max_chars: int,
          pattern: str, extensions: str, dry_run: bool, show_prompt: bool, json_out: bool, copy_context: bool):
    phase = {}
    t0 = time.perf_counter()
    embeddings, meta = load_store()
    phase["load_store_s"] = time.perf_counter() - t0

    extensions_set = {e.strip().lower() for e in extensions.split(",") if e.strip()} if extensions else set()
    if extensions_set and not all(e.startswith(".") for e in extensions_set):
        extensions_set = {"."+e if not e.startswith(".") else e for e in extensions_set}

    t1 = time.perf_counter()
    meta_filtered = filter_meta(meta, pattern, extensions_set)
    if not meta_filtered:
        raise SystemExit("No documents match filter.")
    # Re-align embeddings via indices of retained meta
    if len(meta_filtered) != len(meta):
        # Build mapping of kept indices
        keep_indices = [i for i,m in enumerate(meta) if m in meta_filtered]
        embeddings = embeddings[keep_indices]
        meta = meta_filtered
    phase["filter_s"] = time.perf_counter() - t1

    t2 = time.perf_counter()
    qvec = embed_query_cached(question, embed_model_name)
    phase["embed_query_s"] = time.perf_counter() - t2

    t3 = time.perf_counter()
    hits = select(qvec, embeddings, meta, top_k)
    phase["select_s"] = time.perf_counter() - t3

    if copy_context:
        context_parts = []
        for h in hits:
            snippet = load_snippet(h, -1)
            context_parts.append(f"// From: {h['path']}\n{snippet}\n")
        full_context = "\n".join(context_parts)
        copy_to_clipboard(full_context)

    prompt = build_prompt(question, hits)
    phase["build_prompt_s"] = time.perf_counter() - t3 - phase["select_s"]

    if show_prompt:
        print("---- Prompt ----")
        print(prompt)
        print("---- End Prompt ----")

    if dry_run or copy_context:
        if json_out:
            print(json.dumps({
                "question": question,
                "matches": hits,
                "timing": phase
            }, indent=2))
        else:
            print("\nMatches:\n" + format_matches(hits))
            print("\nTiming (s): " + ", ".join(f"{k}={v:.3f}" for k,v in phase.items()))
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY missing (check .env).")

    t4 = time.perf_counter()
    client = Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=api_model_name,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )
    phase["api_call_s"] = time.perf_counter() - t4
    answer = resp.content[0].text

    if json_out:
        print(json.dumps({
            "question": question,
            "answer": answer,
            "matches": hits,
            "timing": phase
        }, indent=2))
    else:
        print("Answer:\n" + answer)
        print("\nMatches:\n" + format_matches(hits))
        print("\nTiming (s): " + ", ".join(f"{k}={v:.3f}" for k,v in phase.items()))

def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("question", nargs="+")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-api", action="store_true")
    parser.add_argument("--copy", action="store_true", help="Copy matched context to clipboard and exit.")
    parser.add_argument("--pattern", default="")
    parser.add_argument("--extensions", default="")
    parser.add_argument("--show-prompt", action="store_true")
    parser.add_argument("--max-chars", type=int, default=1800)
    parser.add_argument("--model", default=os.getenv("EMBED_MODEL", DEFAULT_EMBED_MODEL), help="Embedding model name")
    parser.add_argument("--api-model", default=os.getenv("ANTHROPIC_MODEL", DEFAULT_API_MODEL), help="Anthropic model name")
    args = parser.parse_args()
    question = " ".join(args.question)
    query(question=question,
          top_k=args.top_k,
          embed_model_name=args.model,
          api_model_name=args.api_model,
          max_chars=args.max_chars,
          pattern=args.pattern,
          extensions=args.extensions,
          dry_run=args.dry_run or args.no_api,
          show_prompt=args.show_prompt,
          json_out=args.json,
          copy_context=args.copy)

if __name__ == "__main__":
    main()