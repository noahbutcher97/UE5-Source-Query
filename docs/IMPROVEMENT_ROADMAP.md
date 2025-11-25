# UE5.3 Vector Search System - Improvement Roadmap

## Overview

This document outlines potential improvements to the vector search system, categorized by priority and effort. All items are optional enhancements - the system is already production-ready.

---

## Quick Wins (High Impact, Low Effort)

### 1. Add `.env.example` Template
**Impact**: High | **Effort**: 5 minutes | **Priority**: P0

**Problem**: New team members don't know what to put in `.env`

**Solution**:
```bash
# Create template file
cat > .env.example << 'EOF'
# Anthropic API Key (optional - only needed for natural language answers)
# Get your key at: https://console.anthropic.com/
ANTHROPIC_API_KEY=your-key-here

# Python path (auto-configured by venv)
PYTHONPATH=D:\path\to\.venv\Lib\site-packages

# Optional: Override embedding model
# EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Optional: Override API model
# ANTHROPIC_MODEL=claude-3-haiku-20240307
EOF
```

**Benefits**:
- Clear onboarding instructions
- Documents environment variables
- Prevents accidental API key commits

---

### 2. Add `requirements.txt`
**Impact**: High | **Effort**: 5 minutes | **Priority**: P0

**Problem**: No documented dependencies for venv setup

**Solution**:
```txt
# Core dependencies
sentence-transformers>=2.2.0
anthropic>=0.7.0
numpy>=1.24.0
python-dotenv>=1.0.0

# Optional dependencies
tqdm>=4.65.0  # Progress bars
```

**Benefits**:
- Reproducible environment setup
- Version pinning for stability
- Easy team member onboarding

---

### 3. Add Scripts `README.md`
**Impact**: High | **Effort**: 15 minutes | **Priority**: P0

**Problem**: No quick-start documentation in Scripts directory

**Solution**: Create `docs/Scripts/README.md` with:
- Quick start guide
- System requirements
- Installation steps
- Common usage examples
- Troubleshooting

**Benefits**:
- Self-documenting system
- Reduces support questions
- Better discoverability

---

### 4. Improve `ask.bat` Error Handling
**Impact**: Medium | **Effort**: 10 minutes | **Priority**: P1

**Current**:
```batch
@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%.venv\Scripts\activate.bat"
python "%SCRIPT_DIR%QueryEmbeddings.py" %*
call "%SCRIPT_DIR%.venv\Scripts\deactivate.bat"
endlocal
```

**Improved**:
```batch
@echo off
setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"

REM Check if venv exists
if not exist "%SCRIPT_DIR%.venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found at: %SCRIPT_DIR%.venv
    echo.
    echo Please create the virtual environment:
    echo   python -m venv "%SCRIPT_DIR%.venv"
    echo   "%SCRIPT_DIR%.venv\Scripts\pip" install -r requirements.txt
    exit /b 1
)

REM Activate venv
call "%SCRIPT_DIR%.venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    exit /b 1
)

REM Run query script
python "%SCRIPT_DIR%QueryEmbeddings.py" %*
set RESULT=%errorlevel%

REM Deactivate venv
call "%SCRIPT_DIR%.venv\Scripts\deactivate.bat"

REM Exit with script result
exit /b %RESULT%
```

**Benefits**:
- Clear error messages
- Detects missing venv
- Preserves exit codes
- Guides user to fix issues

---

## Performance Optimizations (Medium Impact, Medium Effort)

### 5. Add Query Result Caching
**Impact**: High | **Effort**: 2 hours | **Priority**: P1

**Problem**: Repeated identical queries re-compute embeddings and search

**Solution**: Add persistent query cache
```python
# QueryEmbeddings.py improvements
import hashlib
from pathlib import Path

QUERY_CACHE = SCRIPT_DIR / "query_cache.json"
MAX_CACHE_SIZE = 1000

def cache_key(query: str, top_k: int, pattern: str, extensions: str) -> str:
    """Generate unique cache key for query parameters"""
    data = f"{query}|{top_k}|{pattern}|{extensions}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]

def get_cached_results(key: str) -> dict | None:
    """Retrieve cached query results"""
    if not QUERY_CACHE.exists():
        return None
    try:
        cache = json.loads(QUERY_CACHE.read_text())
        if key in cache:
            entry = cache[key]
            # Check if cache is fresh (vector store hasn't changed)
            if entry["store_mtime"] == VECTORS.stat().st_mtime:
                return entry["results"]
    except (json.JSONDecodeError, KeyError):
        pass
    return None

def save_cached_results(key: str, results: list) -> None:
    """Save query results to cache"""
    try:
        cache = json.loads(QUERY_CACHE.read_text()) if QUERY_CACHE.exists() else {}
    except json.JSONDecodeError:
        cache = {}

    # Implement LRU eviction if cache too large
    if len(cache) >= MAX_CACHE_SIZE:
        # Remove oldest entry
        oldest_key = min(cache, key=lambda k: cache[k].get("timestamp", 0))
        del cache[oldest_key]

    cache[key] = {
        "results": results,
        "timestamp": time.time(),
        "store_mtime": VECTORS.stat().st_mtime
    }
    QUERY_CACHE.write_text(json.dumps(cache, indent=2))
```

**Benefits**:
- Instant results for repeated queries (0.01s vs 2s)
- Reduces model inference load
- Better developer experience
- Invalidates on vector store updates

**Trade-offs**:
- Additional disk I/O for cache reads/writes
- Cache file grows to ~5-10MB

---

### 6. Parallel Chunk Embedding
**Impact**: Medium | **Effort**: 1 hour | **Priority**: P2

**Problem**: Embedding is sequential (batch size 32)

**Solution**: Use multiprocessing for encoding
```python
# BuildEmbeddings.py improvements
from concurrent.futures import ThreadPoolExecutor
import multiprocessing as mp

def embed_batches_parallel(model: SentenceTransformer, texts: List[str]) -> np.ndarray:
    """Embed chunks in parallel using multiple threads"""
    if not texts:
        return np.zeros((0, model.get_sentence_embedding_dimension()))

    # Use half of available cores
    workers = max(1, mp.cpu_count() // 2)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        # Split into worker-sized batches
        batch_size = max(1, len(texts) // workers)
        batches = [texts[i:i+batch_size] for i in range(0, len(texts), batch_size)]

        # Encode in parallel
        futures = [executor.submit(model.encode, batch,
                                   convert_to_numpy=True,
                                   normalize_embeddings=True,
                                   show_progress_bar=False)
                  for batch in batches]

        results = [f.result() for f in futures]

    return np.vstack(results)
```

**Benefits**:
- 2-4x faster embedding on multi-core systems
- Reduces index rebuild time from 10min to 3-5min
- Better CPU utilization

**Trade-offs**:
- Increased memory usage (multiple model instances)
- More complex code
- May not work on all sentence-transformers models

---

### 7. Add Fuzzy File Path Search
**Impact**: Medium | **Effort**: 1.5 hours | **Priority**: P2

**Problem**: Must know exact file paths or use substring patterns

**Solution**: Add fuzzy matching for file paths
```python
# QueryEmbeddings.py improvements
from difflib import SequenceMatcher

def fuzzy_match_paths(query: str, paths: List[str], threshold: float = 0.6) -> List[str]:
    """Find files with fuzzy matching on path components"""
    query_lower = query.lower()
    scores = []

    for path in paths:
        path_lower = path.lower()
        # Match full path
        full_score = SequenceMatcher(None, query_lower, path_lower).ratio()

        # Match filename only (higher weight)
        filename = Path(path).name.lower()
        file_score = SequenceMatcher(None, query_lower, filename).ratio()

        # Combined score (filename weighted 2x)
        combined = (full_score + 2 * file_score) / 3

        if combined >= threshold:
            scores.append((combined, path))

    return [path for score, path in sorted(scores, reverse=True)]

# New query mode: --fuzzy-path "ProjectileMovement"
```

**Benefits**:
- Find files without exact names
- More forgiving search
- Better for exploratory queries

**Example**:
```bash
# Instead of: --pattern ProjectileMovementComponent
ask.bat "projectile movement" --fuzzy-path
```

---

## Feature Enhancements (High Impact, High Effort)

### 8. Add Project Source Indexing
**Impact**: Very High | **Effort**: 3 hours | **Priority**: P1

**Problem**: Only indexes UE5.3 engine source, not project code

**Solution**: Add project code to index
```python
# BuildEmbeddings.py additions
PROJECT_ROOT = Path(__file__).parent.parent.parent / "Source"

def build_project_index():
    """Build separate index for project source code"""
    project_files = []
    for ext in [".cpp", ".h", ".hpp"]:
        project_files.extend(PROJECT_ROOT.rglob(f"*{ext}"))

    # Filter out generated/intermediate files
    exclude_patterns = ["Intermediate", "Binaries", ".vs", "Build"]
    project_files = [f for f in project_files
                     if not any(ex in str(f) for ex in exclude_patterns)]

    return project_files

# New flag: --include-project
```

**Benefits**:
- Query both engine AND project code
- Find project-specific implementations
- Cross-reference engine vs project patterns
- Better code reuse discovery

**Example queries**:
```bash
# Find how YOUR project handles collision
ask.bat "collision handling" --include-project

# Compare engine vs project turret implementations
ask.bat "turret component initialization" --include-project
```

**Storage impact**: +5-10MB for typical project

---

### 9. Add Semantic Code Explanation Mode
**Impact**: High | **Effort**: 2 hours | **Priority**: P2

**Problem**: Query returns snippets but no explanation

**Solution**: Add "explain" mode with better prompting
```python
# QueryEmbeddings.py improvements
def build_explanation_prompt(question: str, hits: list) -> str:
    """Build prompt optimized for code explanation"""
    sections = []
    for i, h in enumerate(hits, 1):
        snippet = load_snippet(h, -1)
        sections.append(
            f"[Code Snippet {i}] {h['path']}\n"
            f"```cpp\n{snippet}\n```\n"
        )

    return (
        "You are an Unreal Engine C++ expert. Explain the following code snippets "
        "in the context of the user's question. Focus on:\n"
        "1. What the code does\n"
        "2. How it works (key mechanisms)\n"
        "3. How to use it (practical examples)\n"
        "4. Common patterns and best practices\n\n"
        + "\n\n".join(sections)
        + f"\n\nQuestion: {question}\n\n"
        "Provide a clear, practical explanation with code examples where helpful."
    )

# New flag: --explain (uses Claude API)
```

**Benefits**:
- Better understanding of complex engine code
- Practical usage examples
- Learns patterns from engine source

**Example**:
```bash
ask.bat "how does OnComponentHit work" --explain
# Returns: Detailed explanation with usage examples
```

---

### 10. Add VS Code Extension
**Impact**: Very High | **Effort**: 8-16 hours | **Priority**: P2

**Problem**: Must switch to terminal to query

**Solution**: VS Code extension with inline results
```typescript
// vscode-ue5-search extension
import * as vscode from 'vscode';
import { exec } from 'child_process';

export function activate(context: vscode.ExtensionContext) {
    let disposable = vscode.commands.registerCommand(
        'ue5-search.query',
        async () => {
            const query = await vscode.window.showInputBox({
                prompt: 'Enter UE5 API query',
                placeHolder: 'e.g., OnComponentHit delegate signature'
            });

            if (!query) return;

            // Call ask.bat and parse results
            const results = await queryEngine(query);

            // Show results in sidebar panel
            showResultsPanel(results);
        }
    );

    context.subscriptions.push(disposable);
}

// Features:
// - Cmd+Shift+U to open query box
// - Inline code lens for search results
// - Copy snippet to clipboard
// - Jump to engine source file
```

**Benefits**:
- Zero context switching
- Inline API documentation
- Hover tooltips with examples
- Code actions for common patterns

**Workflow**:
1. Cmd+Shift+U → type query
2. Results appear in sidebar
3. Click to insert snippet or view full file

---

### 11. Add Multi-Language Support
**Impact**: Medium | **Effort**: 4 hours | **Priority**: P3

**Problem**: Only supports C++ files

**Solution**: Index Blueprints, Python, C# for plugins
```python
# BuildEmbeddings.py additions
EXTENSIONS = {
    ".cpp", ".h", ".hpp", ".inl",  # C++
    ".uasset",                      # Blueprints (metadata only)
    ".py",                          # Python scripts
    ".cs",                          # C# for plugins
    ".ini",                         # Config files
}

# Add Blueprint metadata extraction
def extract_blueprint_metadata(asset_path: Path) -> str:
    """Extract searchable metadata from .uasset files"""
    # Use UnrealPak or AssetRegistry to get:
    # - Blueprint class name
    # - Parent class
    # - Exposed functions
    # - Variables
    # - Component types
    pass
```

**Benefits**:
- Find Blueprint implementations
- Cross-reference C++ and Blueprint patterns
- Search config files for settings

**Example**:
```bash
ask.bat "vehicle movement component" --extensions .cpp,.uasset
# Returns: Both C++ implementations AND Blueprint subclasses
```

---

## Reliability Improvements (Medium Impact, Low-Medium Effort)

### 12. Add Automated Testing
**Impact**: Medium | **Effort**: 3 hours | **Priority**: P2

**Problem**: No automated tests, manual verification only

**Solution**: pytest test suite
```python
# tests/test_query.py
import pytest
from QueryEmbeddings import query, load_store

def test_load_store():
    """Test vector store loads correctly"""
    embeddings, meta = load_store()
    assert embeddings.shape[0] == len(meta)
    assert embeddings.shape[1] == 384  # Model dimension

def test_basic_query():
    """Test basic query returns results"""
    results = query("projectile collision", top_k=5, dry_run=True)
    assert len(results) > 0
    assert all(0.0 <= r['score'] <= 1.0 for r in results)

def test_filtering():
    """Test extension filtering works"""
    results = query("test", top_k=10, extensions=".cpp", dry_run=True)
    assert all(r['path'].endswith('.cpp') for r in results)

def test_pattern_filtering():
    """Test pattern matching works"""
    results = query("test", top_k=10, pattern="ChaosVehicle", dry_run=True)
    assert all("ChaosVehicle" in r['path'] for r in results)
```

**Run tests**:
```bash
pytest tests/ -v
```

**Benefits**:
- Catch regressions early
- Confidence in changes
- Documents expected behavior

---

### 13. Add Health Monitoring
**Impact**: Low | **Effort**: 1 hour | **Priority**: P3

**Problem**: No visibility into system health

**Solution**: Add diagnostics command
```python
# New script: Diagnostics.py
def run_diagnostics():
    """Check system health and report issues"""
    print("=== UE5 Vector Search Diagnostics ===\n")

    # Check vector store
    if not VECTORS.exists():
        print("❌ Vector store missing")
    else:
        size_mb = VECTORS.stat().st_size / 1_000_000
        print(f"✅ Vector store: {size_mb:.1f}MB")

    # Check metadata
    if not META.exists():
        print("❌ Metadata missing")
    else:
        meta = json.loads(META.read_text())
        print(f"✅ Metadata: {len(meta['items'])} chunks")

    # Check venv
    venv_python = SCRIPT_DIR / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        print("❌ Virtual environment missing")
    else:
        print("✅ Virtual environment OK")

    # Check dependencies
    try:
        import sentence_transformers
        print("✅ sentence-transformers installed")
    except ImportError:
        print("❌ sentence-transformers missing")

    # Check model cache
    model_cache = Path.home() / ".cache" / "torch" / "sentence_transformers"
    if model_cache.exists():
        cache_size = sum(f.stat().st_size for f in model_cache.rglob("*"))
        print(f"✅ Model cache: {cache_size/1_000_000:.1f}MB")

    # Test query performance
    print("\n=== Performance Test ===")
    start = time.time()
    query("test query", top_k=1, dry_run=True)
    elapsed = time.time() - start
    print(f"Query time: {elapsed:.2f}s")
    if elapsed > 5:
        print("⚠️  Slower than expected")
    else:
        print("✅ Performance OK")

# Run: python Diagnostics.py
```

---

### 14. Add Rebuild Detection & Auto-Update
**Impact**: Medium | **Effort**: 2 hours | **Priority**: P2

**Problem**: Manual rebuild after engine updates

**Solution**: Auto-detect stale index
```python
# QueryEmbeddings.py improvements
def check_index_freshness():
    """Warn if engine source is newer than index"""
    if not VECTORS.exists():
        return

    index_mtime = VECTORS.stat().st_mtime
    engine_root = Path("C:/Program Files/Epic Games/UE_5.3/Engine/Source")

    # Check a few key files for updates
    key_files = [
        engine_root / "Runtime/Engine/Classes/GameFramework/Actor.h",
        engine_root / "Runtime/Engine/Classes/Components/PrimitiveComponent.h",
    ]

    for f in key_files:
        if f.exists() and f.stat().st_mtime > index_mtime:
            print("⚠️  Engine source is newer than index")
            print(f"Index last built: {time.ctime(index_mtime)}")
            print(f"Rebuild with: python BuildEmbeddings.py --use-index --force")
            return

# Call on every query
```

---

## Advanced Features (Low Priority, High Effort)

### 15. Add Semantic Code Search with Examples
**Impact**: High | **Effort**: 8 hours | **Priority**: P3

**Problem**: Hard to find "how to do X" examples

**Solution**: Example-based search
```python
# Find code that does similar things
ask.bat "show me examples of applying impulse to physics bodies" --find-examples
# Returns: Multiple code snippets from different engine systems
```

**Implementation**:
- Extract function bodies and doc comments
- Build separate "example" index
- Use cosine similarity to find similar patterns

---

### 16. Add API Change Detection
**Impact**: Medium | **Effort**: 6 hours | **Priority**: P3

**Problem**: Engine updates break APIs

**Solution**: Track API changes between versions
```python
# Compare two vector stores
python CompareVersions.py --old UE5.3 --new UE5.4
# Reports: Removed functions, changed signatures, deprecated APIs
```

---

### 17. Add Interactive TUI
**Impact**: Low | **Effort**: 4 hours | **Priority**: P3

**Problem**: Command-line only, no interactivity

**Solution**: Terminal UI with Rich/Textual
```python
# Interactive mode: python QueryEmbeddings.py --interactive
# Features:
# - Live search as you type
# - Syntax-highlighted results
# - Keyboard navigation
# - Multi-select for clipboard
```

---

## Implementation Priority Matrix

| Improvement | Impact | Effort | ROI | Priority |
|-------------|--------|--------|-----|----------|
| .env.example | High | 5min | ⭐⭐⭐⭐⭐ | P0 |
| requirements.txt | High | 5min | ⭐⭐⭐⭐⭐ | P0 |
| Scripts README | High | 15min | ⭐⭐⭐⭐⭐ | P0 |
| Improve ask.bat | Med | 10min | ⭐⭐⭐⭐ | P1 |
| Query result caching | High | 2hr | ⭐⭐⭐⭐ | P1 |
| Project indexing | V.High | 3hr | ⭐⭐⭐⭐⭐ | P1 |
| Fuzzy path search | Med | 1.5hr | ⭐⭐⭐ | P2 |
| Parallel embedding | Med | 1hr | ⭐⭐⭐ | P2 |
| Explain mode | High | 2hr | ⭐⭐⭐⭐ | P2 |
| Automated testing | Med | 3hr | ⭐⭐⭐ | P2 |
| VS Code extension | V.High | 16hr | ⭐⭐⭐⭐⭐ | P2 |
| Health monitoring | Low | 1hr | ⭐⭐ | P3 |
| Auto-rebuild detect | Med | 2hr | ⭐⭐⭐ | P2 |
| Multi-language | Med | 4hr | ⭐⭐ | P3 |
| Example search | High | 8hr | ⭐⭐⭐ | P3 |
| Interactive TUI | Low | 4hr | ⭐⭐ | P3 |
| API change detect | Med | 6hr | ⭐⭐ | P3 |

---

## Recommended Implementation Order

### Phase 1: Quick Wins (1 hour total)
1. Add `.env.example`
2. Add `requirements.txt`
3. Add Scripts README
4. Improve `ask.bat` error handling

### Phase 2: High-Value Features (6 hours total)
5. Project source indexing
6. Query result caching
7. Explain mode

### Phase 3: Developer Experience (20 hours total)
8. VS Code extension
9. Automated testing
10. Fuzzy path search
11. Parallel embedding

### Phase 4: Advanced Features (As needed)
12. Multi-language support
13. Example-based search
14. API change detection
15. Health monitoring
16. Interactive TUI

---

## Conclusion

The system is already **production-ready** with a 9/10 rating. All improvements are optional enhancements that add incremental value based on team needs and usage patterns.

**Recommended Next Steps**:
1. Complete Phase 1 (Quick Wins) → 1 hour investment
2. Monitor usage patterns for 1-2 weeks
3. Prioritize Phase 2 features based on actual team needs
4. Consider Phase 3+ if system becomes mission-critical

**Total Estimated Effort**:
- Phase 1: 1 hour (high ROI)
- Phase 2: 6 hours (high ROI)
- Phase 3: 20 hours (medium ROI)
- Phase 4: 40+ hours (low-medium ROI)