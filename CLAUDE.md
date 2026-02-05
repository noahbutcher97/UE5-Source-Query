


# CLAUDE.md

This file provides guidance to Claude Code when working with the UE5 Source Query System codebase.

## Project Overview

**UE5 Source Query System** is an intelligent hybrid search tool for Unreal Engine 5.3 source code. It combines precise definition extraction with semantic search to provide accurate, context-aware results for UE5 API queries.

### Key Features
**Core Query System (Phase 1):**
- **Hybrid Query Routing**: Automatically detects query type (definition, semantic, or hybrid)
- **Code-Trained Embeddings**: Uses `microsoft/unixcoder-base` (768 dims) for C++ code understanding
- **Semantic Chunking**: Structure-aware chunking that respects C++ boundaries (functions, classes, macros)
- **Modular File Discovery**: Flexible indexing with directory files, CLI paths, or full Engine scans
- **Three-Layer Filtering**: Extension whitelist, directory exclusions, file pattern matching
- **.indexignore Support**: Hierarchical exclusion files (like .gitignore)
- **Logical Compensation**: Structural boosts for better ranking (file path matching, header prioritization)
- **Incremental Updates**: Hash-based caching for unchanged files

**Advanced Features (Phases 2-5):**
- **Filter DSL** (Phase 2): Rich filtering language for metadata-based search
- **Unified Dashboard** (Phase 3): GUI interface with Query, Source Manager, Maintenance, and Diagnostics tabs
- **Batch Processing** (Phase 4): Process multiple queries efficiently with JSONL format
- **Relationship Extraction** (Phase 5): Automatic detection of class hierarchies and dependencies
- **Health Checks** (Phase 2): Comprehensive installation and vector store validation
- **Team Deployment** (Phase 2): GUI installer with per-machine path configuration

## Repository Structure

```
D:\DevTools\UE5-Source-Query\
├── ue5_query/
│   ├── core/                    # Query processing (Phases 1-5)
│   │   ├── hybrid_query.py      # Main hybrid query engine
│   │   ├── query_intent.py      # Query type detection
│   │   ├── definition_extractor.py  # Regex-based C++ extraction
│   │   ├── filtered_search.py   # Metadata-based filtering
│   │   ├── batch_query.py       # Batch processing (Phase 4)
│   │   ├── relationship_extractor.py  # Relationship extraction (Phase 5)
│   │   ├── query_engine.py      # Semantic search
│   │   └── types.py             # Type definitions
│   ├── indexing/                # Vector store building
│   │   ├── build_embeddings.py  # Main indexing script
│   │   ├── detect_engine_path.py  # UE5 path detection
│   │   ├── metadata_enricher.py # Entity detection & tagging
│   │   └── EngineDirs.txt       # 24 targeted UE5 directories
│   ├── utils/                   # Utilities & helpers
│   │   ├── config_manager.py    # Configuration management
│   │   └── activity_logger.py   # M2M activity tracking
│   ├── management/              # GUI tools (Phase 3)
│   │   └── gui_dashboard.py     # Unified Dashboard
│   └── server/                  # HTTP API
│       └── retrieval_server.py  # REST API (Migrating to FastAPI)
├── docs/                        # Documentation
│   ├── user/                    # User guides & audits
│   │   ├── audits/              # v2.1 Audit Reports (2026-02-04)
│   │   └── ai_integration.md    # Agent guide
│   └── dev/                     # Developer docs
├── data/                        # Vector store & index
├── Setup.bat                    # Main installer
├── launcher.bat                 # Unified Dashboard launcher
├── ask.bat                      # CLI query interface
└── README.md                    # Main readme
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

**`ue5_query/indexing/build_embeddings.py`** (Main indexing script)
- **File Discovery**: Extension filter (.cpp, .h), exclusions (Intermediate), and glob matching.
- **Chunking**: Semantic chunking (structure-aware) or fallback character-based.
- **Embedding**: Generates vectors using `unixcoder-base`.

### Query System

**`ue5_query/core/hybrid_query.py`** (Main query interface)
- Orchestrates intent analysis, definition extraction, and semantic search.
- Merges results into a unified schema.

**`ue5_query/core/query_intent.py`** (Query analysis)
- Detects UE5 entities and classifies query type (DEFINITION/SEMANTIC/HYBRID).

### Development Workflow

### Building the Index
```bash
python -m ue5_query.indexing.build_embeddings --dirs-file ue5_query.indexing.EngineDirs.txt --force
```

### Querying the Index
```bash
ask.bat "FHitResult members" --show-reasoning
python -m ue5_query.core.hybrid_query "how does collision detection work"
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

1. Edit `ue5_query/indexing/EngineDirs.txt`:
```txt
# Add new line
C:\Program Files\Epic Games\UE_5.3\Engine\Source\Runtime\YourNewDir
```

2. Run incremental build:
```bash
python ue5_query/indexing/build_embeddings.py --dirs-file ue5_query/indexing/EngineDirs.txt --incremental --verbose
```

### Exclude Specific File Patterns

**Option 1: CLI (temporary)**
```bash
python ue5_query/indexing/build_embeddings.py \
    --dirs-file ue5_query/indexing/EngineDirs.txt \
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
python ue5_query/core/query_intent.py
# Interactive mode - test query classification
```

2. **Test definition extraction:**
```bash
python ue5_query/core/definition_extractor.py struct FHitResult --fuzzy
```

3. **View raw semantic results:**
```bash
python ue5_query/core/query_engine.py "your query" --dry-run --top-k 10
```

4. **Enable verbose hybrid query:**
```bash
python ue5_query/core/hybrid_query.py "your query" --show-reasoning --top-k 10
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

## Current Status & Future Work

**Current Status: v2.1 Foundations (Post-Audit)**
- ✅ Phase 1-5: Complete (Core, Filters, GUI, Batch, Relationships)
- ✅ v2.1 Audits: Complete (API, DB, Patterns, System)

**🎯 ACTIVE TASK: Infrastructure Refactor (v2.1)**
Refactoring the system for production readiness based on the 2026-02-04 Audit Summary.

**Priority Goals:**
1.  **FastAPI Migration**: Asynchronous server implementation.
2.  **SQLite Migration**: Transition from JSON metadata to relational DB.
3.  **Redis Caching**: Semantic result caching layer.
4.  **Celery Integration**: Decoupled background indexing.

**To Continue:**
Refer to `docs/user/audits/Audit_Summary_2026-02-04.md` for the 80-item prioritized task list.

## Contributing

### Code Style
- Python 3.10+, Type hints mandatory.
- Use `ue5_query.` package imports (no relative imports).
- Follow the **Template Method** pattern for extractors (v2.1 requirement).

### Commit Messages
Use conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`.
**Important:** No AI attribution in commit messages. Keep them focused on "why" and "what".

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
from ue5_query.indexing.build_embeddings import load_dirs_from_file, discover_source_files
roots = load_dirs_from_file(Path('ue5_query/indexing/EngineDirs.txt'), verbose=True)
files = discover_source_files(roots=roots, verbose=True)
print(f'Found {len(files)} files')
"
```

**Test query intent:**
```bash
python ue5_query/core/query_intent.py
# Interactive mode
```

**Test definition extraction:**
```bash
python ue5_query/core/definition_extractor.py struct FHitResult
python ue5_query/core/definition_extractor.py class AActor
python ue5_query/core/definition_extractor.py enum ECollisionChannel
```

**Test semantic search:**
```bash
python ue5_query/core/query_engine.py "collision detection" --dry-run --top-k 5
```

**Test hybrid query:**
```bash
python ue5_query/core/hybrid_query.py "FHitResult members" --show-reasoning
```

**Test AI Agent Integration:**
```bash
# Verifies JSON, XML, and Code output formats used by Claude/Gemini
python tests/test_agent_integration.py
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

**Important:** Do NOT include AI attribution, co-authorship, or "Generated with Claude" messages in commits. Keep commit messages focused on the changes themselves.

## Additional Resources

### User & Deployment Documentation (docs/user/ & docs/deployment/)
- **README.md**: Main user guide.
- **docs/dev/architecture.md**: System architecture and file reference.
- **docs/deployment/maintenance.md**: System maintenance procedures.
- **docs/user/troubleshooting.md**: Common issues and solutions.
- **docs/user/ai_integration.md**: AI agent integration protocol.
- **docs/deployment/team_setup.md**: Team onboarding and Git LFS guide.

### Development Documentation (docs/dev/ & docs/user/audits/)
- **docs/user/audits/Audit_Summary_2026-02-04.md**: v2.1 infrastructure plan.
- **docs/dev/api_reference.md**: Python API reference.
- **docs/dev/BACKLOG.md**: Future features and optimizations.

### Archived Documentation (docs/_archive/)
- **docs/_archive/planning/**: Obsolete plans and roadmap history.
- **docs/_archive/audits/**: Historical audit reports.