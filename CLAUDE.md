# CLAUDE.md

This file provides guidance to Claude Code when working with the UE5 Source Query System codebase.

## Project Overview

**UE5 Source Query System** is an intelligent hybrid search tool for Unreal Engine 5.3 source code. It combines precise definition extraction with semantic search to provide accurate, context-aware results for UE5 API queries.

### Key Features
- **Hybrid Query Routing**: Automatically detects query type (definition, semantic, or hybrid)
- **Code-Trained Embeddings**: Uses `microsoft/unixcoder-base` (768 dims) for C++ code understanding
- **Semantic Chunking**: Structure-aware chunking that respects C++ boundaries (functions, classes, macros)
- **Modular File Discovery**: Flexible indexing with directory files, CLI paths, or full Engine scans
- **Three-Layer Filtering**: Extension whitelist, directory exclusions, file pattern matching
- **.indexignore Support**: Hierarchical exclusion files (like .gitignore)
- **Logical Compensation**: Structural boosts for better ranking (file path matching, header prioritization)
- **Incremental Updates**: Hash-based caching for unchanged files

## Repository Structure

```
D:\DevTools\UE5-Source-Query\
├── src/
│   ├── core/                    # Query processing
│   │   ├── hybrid_query.py      # Main hybrid query engine
│   │   ├── query_intent.py      # Query type detection
│   │   ├── definition_extractor.py  # Regex-based C++ extraction
│   │   ├── filtered_search.py   # Metadata-based filtering
│   │   └── query_engine.py      # Semantic search (legacy)
│   ├── indexing/                # Vector store building
│   │   ├── build_embeddings.py  # Main indexing script
│   │   ├── metadata_enricher.py # Entity detection & tagging
│   │   ├── EngineDirs.txt       # 24 targeted UE5 directories
│   │   └── BuildSourceIndex.ps1 # Legacy PowerShell indexer (deprecated)
│   ├── utils/
│   │   └── semantic_chunker.py  # C++ structure-aware chunking
│   └── server/
│       └── retrieval_server.py  # HTTP API (optional)
├── data/
│   ├── vector_store.npz         # Embeddings (768-dim, ~24MB)
│   ├── vector_meta.json         # Chunk metadata (~3.9MB)
│   └── vector_meta_enriched.json  # With entity tags (optional)
├── docs/                        # Documentation
│   ├── HYBRID_QUERY_GUIDE.md
│   ├── AUDIT_REPORT.md
│   └── IMPROVEMENT_ROADMAP.md
├── .indexignore                 # Default exclusion patterns
├── DEFERRED_TASKS.md           # Future enhancements
├── README.md                   # User documentation
└── ask.bat                     # Windows entry point
```

## Core Architecture

### 1. Query Processing Pipeline

```
User Query
    ↓
QueryIntentAnalyzer (query_intent.py)
    ├─→ DEFINITION: "struct FHitResult"
    │       ↓
    │   DefinitionExtractor (definition_extractor.py)
    │       ↓
    │   Regex patterns + brace matching
    │
    ├─→ SEMANTIC: "how does collision detection work"
    │       ↓
    │   SemanticSearch (query_engine.py)
    │       ↓
    │   Embedding + cosine similarity
    │
    └─→ HYBRID: "FHitResult members"
            ↓
        Both methods + merge results
```

### 2. Indexing Pipeline

```
Input Sources
    ├─→ --dirs-file EngineDirs.txt (24 directories)
    ├─→ --dirs "path1" "path2" (CLI)
    └─→ --root <path> (full scan)
        ↓
File Discovery (discover_source_files)
    ├─→ Layer 1: Extension filter (.cpp, .h, .hpp, .inl, .cs)
    ├─→ Layer 2: Directory exclusions (Intermediate, Binaries, etc.)
    └─→ Layer 3: File pattern filter (glob matching)
        ↓
Text Extraction & Chunking
    ├─→ Semantic chunking (structure-aware, 2000 chars)
    └─→ Fallback: character-based (1500 chars, 200 overlap)
        ↓
Embedding Generation
    ├─→ Model: microsoft/unixcoder-base (768 dims)
    ├─→ Batch size: 32 chunks
    └─→ Normalization: L2 normalized
        ↓
Vector Store
    ├─→ vector_store.npz (numpy compressed)
    └─→ vector_meta.json (chunk metadata)
```

## Key Files and Their Roles

### Indexing System

**`src/indexing/build_embeddings.py`** (Main indexing script)
- **Lines 87-100**: `DEFAULT_UE5_EXCLUDES` - Default exclusion patterns
- **Lines 102-108**: `should_exclude_path()` - Directory exclusion logic
- **Lines 110-129**: `load_dirs_from_file()` - Load EngineDirs.txt
- **Lines 131-163**: `load_exclusions_from_file()` - Load .indexignore patterns
- **Lines 165-196**: `load_all_indexignore_files()` - Hierarchical .indexignore loading
- **Lines 247-295**: `discover_source_files()` - Unified file discovery
- **Lines 409-533**: `build()` - Main indexing function with 4 input modes
- **Lines 531-660**: `main()` - CLI argument parsing

**Important CLI Arguments:**
- `--dirs-file <path>`: Load directories from file (RECOMMENDED for targeted indexing)
- `--dirs <path1> <path2>`: Scan specific directories
- `--extensions .cpp .h`: Filter by file extensions
- `--exclude <pattern>`: Add directory exclusion patterns
- `--exclude-files <pattern>`: Exclude files by glob pattern
- `--indexignore <path>`: Load specific .indexignore file
- `--incremental`: Reuse cached embeddings for unchanged files
- `--force`: Force full rebuild
- `--verbose`: Enable detailed logging

**`src/indexing/EngineDirs.txt`** (24 targeted directories)
- Chaos Vehicle Plugin
- Physics Control Plugin
- Animation systems (Core, Graph, Runtime)
- Physics Engine
- Networking (Replication, Sockets)
- Vehicle-specific subsystems

**`.indexignore`** (Exclusion patterns)
- Format similar to `.gitignore`
- Directory patterns (plain text): `Intermediate`, `Binaries`
- File patterns (glob): `*Test*.cpp`, `*.generated.h`
- Hierarchical loading: current dir → root dirs → `~/.indexignore`

### Query System

**`src/core/hybrid_query.py`** (Main query interface)
- Automatic query type detection
- Routes to definition extractor or semantic search
- Merges results intelligently

**`src/core/query_intent.py`** (Query analysis)
- Detects UE5 entities (FHitResult, AActor, UChaos*)
- Classifies as DEFINITION/SEMANTIC/HYBRID
- Enhances queries with code keywords

**`src/core/definition_extractor.py`** (Precise extraction)
- Regex patterns for struct/class/enum/function
- Brace matching for complete definitions
- Fuzzy matching with Levenshtein distance
- 0.3-0.4s response time

**`src/core/filtered_search.py`** (Metadata filtering)
- Filter by entity, type, UE5 macros
- Relevance boosting (entity matching, macro presence)
- Requires enriched metadata (run `metadata_enricher.py`)

### Utilities

**`src/utils/semantic_chunker.py`** (Structure-aware chunking)
- Splits at C++ boundaries:
  - Function/class/struct/enum definitions
  - UE5 macros (UCLASS, USTRUCT, UPROPERTY, UFUNCTION)
  - Namespace declarations
  - Comment blocks
- Configurable via environment:
  - `SEMANTIC_CHUNKING=1` (default: ON)
  - `CHUNK_SIZE=2000` (default for semantic)
  - `CHUNK_OVERLAP=200`

## Development Workflow

### Building the Index

**Recommended: Targeted indexing with EngineDirs.txt**
```bash
cd D:\DevTools\UE5-Source-Query
.venv\Scripts\python.exe src/indexing/build_embeddings.py \
    --dirs-file src/indexing/EngineDirs.txt \
    --force --verbose
```

**Result:** ~2,255 files from 24 directories, ~20,000-30,000 chunks, 2-5 minute build time

**Alternative: Full Engine scan with exclusions**
```bash
.venv\Scripts\python.exe src/indexing/build_embeddings.py \
    --root "C:/Program Files/Epic Games/UE_5.3/Engine" \
    --force --verbose
```

**Result:** ~50,000-80,000 files after exclusions, 20-30 minute build time

**Incremental updates (add new directories):**
```bash
# Edit EngineDirs.txt to add 2 new directories
.venv\Scripts\python.exe src/indexing/build_embeddings.py \
    --dirs-file src/indexing/EngineDirs.txt \
    --incremental --verbose
```

**Only new files are embedded, unchanged files reused from cache**

### Querying the Index

**Via Python script:**
```bash
python src/core/hybrid_query.py "FHitResult members" --show-reasoning
python src/core/hybrid_query.py "how does collision detection work" --show-reasoning
python src/core/definition_extractor.py struct FHitResult
```

**Via Windows batch file:**
```bash
ask.bat "FHitResult ImpactPoint ImpactNormal" --copy --dry-run --top-k 3
```

**Via HTTP server (optional):**
```bash
python src/server/retrieval_server.py
# Query: http://localhost:8008/query?q=FHitResult+members
```

## Configuration

### Environment Variables

**Model Configuration:**
- `EMBED_MODEL=microsoft/unixcoder-base` (default, 768 dims, code-trained)
- `ANTHROPIC_MODEL=claude-3-haiku-20240307` (for semantic queries)

**Chunking Configuration:**
- `SEMANTIC_CHUNKING=1` (default: ON, use structure-aware chunking)
- `CHUNK_SIZE=2000` (default for semantic, 1500 for character-based)
- `CHUNK_OVERLAP=200`

**Indexing Configuration:**
- `INDEX_DOCS=1` (include .md, .txt files in index)

### Python Dependencies

**Core:**
- `sentence-transformers` (embeddings)
- `numpy` (vector operations)
- `anthropic` (Claude API for query answering)

**Optional:**
- `tqdm` (progress bars)
- `flask` (HTTP server)

**Install:**
```bash
cd D:\DevTools\UE5-Source-Query
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Best Practices

### When Indexing

1. **Use `--dirs-file` for targeted indexing** (recommended)
   - Faster builds (2-5 min vs 20-30 min)
   - More relevant results (focused on vehicle/animation systems)
   - Easier to maintain (edit EngineDirs.txt)

2. **Use `--force` when changing directory scope**
   - Adding/removing directories from EngineDirs.txt
   - Changing exclusion patterns

3. **Use `--incremental` for file content changes**
   - Automatically detects modified files by hash
   - Reuses cached embeddings for unchanged files

4. **Create `.indexignore` files for project-specific exclusions**
   - Project root: project-wide patterns
   - Subdirectories: directory-specific patterns
   - User home: personal exclusions across all projects

### When Querying

1. **For precise definitions, use explicit names:**
   - ✅ "struct FHitResult"
   - ✅ "FHitResult members"
   - ✅ "UChaosWheeledVehicleMovementComponent"

2. **For conceptual understanding, use natural language:**
   - ✅ "how does collision detection work"
   - ✅ "vehicle wheel physics"
   - ✅ "replication of movement"

3. **For member access, combine entity + keywords:**
   - ✅ "FHitResult ImpactPoint ImpactNormal"
   - ✅ "AActor GetActorLocation GetActorRotation"

4. **Avoid vague queries:**
   - ❌ "tell me about FHitResult"
   - ❌ "members" (no entity context)

## Common Tasks

### Add New Directories to Index

1. Edit `src/indexing/EngineDirs.txt`:
```txt
# Add new line
C:\Program Files\Epic Games\UE_5.3\Engine\Source\Runtime\YourNewDir
```

2. Run incremental build:
```bash
python src/indexing/build_embeddings.py --dirs-file src/indexing/EngineDirs.txt --incremental --verbose
```

### Exclude Specific File Patterns

**Option 1: CLI (temporary)**
```bash
python src/indexing/build_embeddings.py \
    --dirs-file src/indexing/EngineDirs.txt \
    --exclude-files "*Test*.cpp" "*Mock*.h" \
    --force --verbose
```

**Option 2: .indexignore (persistent)**
```txt
# Add to .indexignore
*Test*.cpp
*Mock*.h
*deprecated*
```

### Debug Query Issues

1. **Check query intent classification:**
```bash
python src/core/query_intent.py
# Interactive mode - test query classification
```

2. **Test definition extraction:**
```bash
python src/core/definition_extractor.py struct FHitResult --fuzzy
```

3. **View raw semantic results:**
```bash
python src/core/query_engine.py "your query" --dry-run --top-k 10
```

4. **Enable verbose hybrid query:**
```bash
python src/core/hybrid_query.py "your query" --show-reasoning --top-k 10
```

## Performance Characteristics

**Indexing:**
- 24 directories (EngineDirs.txt): ~2,255 files → 2-5 min build
- Full Engine scan: ~50,000-80,000 files → 20-30 min build
- Incremental update: Only new/modified files → <1 min typical

**Querying:**
- Definition extraction: 0.3-0.4s
- Semantic search: 0.8-1.0s (includes embedding)
- Hybrid query: 1.2-1.4s

**Storage:**
- Embeddings: ~24MB (compressed)
- Metadata: ~3.9MB (JSON)
- Enriched metadata: ~9.8MB (optional)

## Known Limitations

### Current Limitations

1. **No auto-cleanup of removed directories** during `--incremental` builds
   - Workaround: Use `--force` to rebuild (~2-5 min for 2.2K files)
   - See `DEFERRED_TASKS.md` for planned enhancement

2. **Single vector store** (Engine + project combined)
   - No separate query scopes
   - See `DEFERRED_TASKS.md` for multi-store architecture

3. **PowerShell indexer deprecated but not removed**
   - `BuildSourceIndex.ps1` and related files still present
   - Pure Python discovery is now primary method
   - Old `--use-index` mode still works for backward compatibility

4. **Semantic search accuracy depends on embedding model**
   - Current: `microsoft/unixcoder-base` (768 dims, code-trained)
   - Logical compensation boosts help (3x file path match, 2.5x header priority)
   - Definition extraction provides fallback for precise queries

## Deferred Enhancements

See `DEFERRED_TASKS.md` for detailed specifications.

**Planned after production validation (2-4 weeks):**
1. Smart incremental cleanup for removed directories (15-45 min)
2. Project-scope separate embedded store (2-3 hours)
3. Query strategy auto-selection (1-2 hours)

## Troubleshooting

### Build Issues

**"No source files found"**
- Check paths in EngineDirs.txt are valid
- Verify directories exist and are readable
- Try `--no-default-excludes` to disable filtering
- Use `--verbose` to see discovery progress

**"Failed to load existing data"**
- Vector store corrupted, use `--force` to rebuild
- Check `data/vector_store.npz` and `data/vector_meta.json` exist
- Verify numpy version compatibility

**Slow incremental builds**
- Cache may be outdated, use `--force` for clean rebuild
- Delete `data/vector_cache.json` to reset cache

### Query Issues

**Definition not found**
- Check capitalization (UE5 convention: FHitResult, AActor, ECollisionChannel)
- Try `--fuzzy` flag for typo tolerance
- Verify entity is in indexed files

**Semantic results irrelevant**
- Try hybrid mode: mention entity name + keywords
- Use filtered search with entity filter (requires enriched metadata)
- Add more specific keywords to query

**Query takes too long (>5s)**
- Check model is cached (first query loads model)
- Verify `vector_store.npz` is not corrupted
- Try smaller `--top-k` value

## Testing

### Manual Testing

**Test file discovery:**
```bash
python -c "
from pathlib import Path
from src.indexing.build_embeddings import load_dirs_from_file, discover_source_files
roots = load_dirs_from_file(Path('src/indexing/EngineDirs.txt'), verbose=True)
files = discover_source_files(roots=roots, verbose=True)
print(f'Found {len(files)} files')
"
```

**Test query intent:**
```bash
python src/core/query_intent.py
# Interactive mode
```

**Test definition extraction:**
```bash
python src/core/definition_extractor.py struct FHitResult
python src/core/definition_extractor.py class AActor
python src/core/definition_extractor.py enum ECollisionChannel
```

**Test semantic search:**
```bash
python src/core/query_engine.py "collision detection" --dry-run --top-k 5
```

**Test hybrid query:**
```bash
python src/core/hybrid_query.py "FHitResult members" --show-reasoning
```

## Integration with Other Projects

### Deploying to Unreal Project

**Example: hijack_prototype game project**

1. Copy system to project:
```bash
robocopy D:\DevTools\UE5-Source-Query D:\UnrealProjects\5.3\hijack_prototype\docs\Scripts /MIR /XD .venv data __pycache__ .git
```

2. Copy vector store:
```bash
xcopy D:\DevTools\UE5-Source-Query\data D:\UnrealProjects\5.3\hijack_prototype\docs\Scripts\data /E /I /Y
```

3. Update project CLAUDE.md:
```markdown
## UE5 Source Query System

Located in `docs/Scripts/`, query UE5 source code:

\`\`\`bash
cd docs/Scripts
ask.bat "FHitResult members" --copy --dry-run --top-k 3
\`\`\`

See `docs/Scripts/README.md` for full documentation.
```

4. Test from project:
```bash
cd D:\UnrealProjects\5.3\hijack_prototype\hijack_prototype
docs\Scripts\ask.bat "UChaosWheeledVehicleMovementComponent" --dry-run
```

## Contributing

### Code Style

- Python 3.10+
- Type hints for function signatures
- Docstrings for all public functions
- Line length: ~100 characters
- Use pathlib for file operations (not os.path)

### Adding New Features

1. Update this CLAUDE.md with architecture changes
2. Add entry to DEFERRED_TASKS.md if deferring
3. Update README.md user documentation
4. Add test examples to appropriate sections

### Commit Messages

Use conventional commits:
```
feat: add smart incremental cleanup for removed directories
fix: correct directory exclusion pattern matching
docs: update CLAUDE.md with new CLI arguments
refactor: simplify file discovery logic
```

## Additional Resources

- **README.md**: User-facing documentation
- **docs/HYBRID_QUERY_GUIDE.md**: Detailed query system guide
- **docs/AUDIT_REPORT.md**: System performance audit
- **docs/IMPROVEMENT_ROADMAP.md**: Enhancement timeline
- **DEFERRED_TASKS.md**: Future planned enhancements