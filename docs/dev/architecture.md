# Project Structure & File Organization

## Current Architecture (Phase 2 - Team Deployment Ready)

### Design Philosophy

**Core Principles:**
1. **User-Facing Simplicity** - Single-click installers, clear entry points
2. **Robust Validation** - Health checks at every critical step
3. **Team-Ready** - Multiple UE5 versions, different machines, Git LFS support
4. **Self-Healing** - Clear error messages with recovery paths
5. **Professional Organization** - Dedicated directories for installers, utilities, documentation

---

## Directory Structure

```
D:\DevTools\UE5-Source-Query\
│
├── 📁 Root Level - User Entry Points
│   ├── Setup.bat                 ⭐ Main installer (double-click to deploy)
│   ├── launcher.bat              🚀 Unified Dashboard launcher
│   ├── ask.bat                   🔍 Query interface
│   ├── README.md                 📖 Main documentation
│   ├── CLAUDE.md                 🤖 Claude Code integration guide
│   ├── GEMINI.md                 🤖 Gemini integration guide
│   ├── requirements.txt          📋 Python dependencies (CPU)
│   ├── requirements-gpu.txt      🎮 Python dependencies (GPU)
│   ├── .gitignore                🚫 Git exclusions
│   ├── .indexignore              🚫 Indexing exclusions
│   └── create_dist.bat           📦 Distribution packaging tool
│
├── 📁 installer/ - Deployment Tools
│   ├── gui_deploy.py             💎 GUI deployment wizard (tkinter)
│   └── README.md                 📖 Installer documentation
│
├── 📁 tools/ - Backend Scripts
│   ├── health-check.bat          ✅ System validation
│   ├── rebuild-index.bat         🔄 Rebuild vector store
│   ├── fix-paths.bat             🔧 Regenerate UE5 paths
│   ├── check-paths.bat           🔍 Verify UE5 paths
│   ├── setup-git-lfs.bat         📦 Git LFS configuration
│   ├── serve.bat                 🌐 Start HTTP server
│   ├── check_enrichment.py       🏷️ Verify metadata enrichment
│   └── README.md                 📖 Tools documentation
│
├── 📁 src/ - Source Code
│   │
│   ├── 📁 core/ - Query Engine
│   │   ├── hybrid_query.py              🔀 Main hybrid engine
│   │   ├── query_intent.py              🧠 Intent analysis
│   │   ├── definition_extractor.py      🔍 Regex extraction
│   │   ├── filtered_search.py           🎯 Metadata filtering
│   │   ├── query_engine.py              🔎 Semantic search
│   │   ├── batch_query.py               📦 Batch processing (Phase 4)
│   │   ├── relationship_extractor.py    🔗 Relationship extraction (Phase 5)
│   │   ├── filter_builder.py            🔧 Filter DSL builder
│   │   ├── output_formatter.py          📄 Result formatting
│   │   └── __init__.py
│   │
│   ├── 📁 indexing/ - Vector Store Building
│   │   ├── build_embeddings.py         🏗️ Main indexer
│   │   ├── detect_engine_path.py       🔍 UE5 path detection
│   │   ├── metadata_enricher.py        🏷️ Entity tagging
│   │   ├── EngineDirs.template.txt     📄 Path template (committed)
│   │   ├── EngineDirs.txt              📄 Paths (machine-specific, gitignored)
│   │   ├── EngineDirs.txt.example      📄 Example paths (reference)
│   │   ├── BuildSourceIndex.ps1        🔧 PowerShell helper (deprecated)
│   │   ├── BuildSourceIndexAdmin.bat   🔧 Admin launcher (deprecated)
│   │   └── __init__.py
│   │
│   ├── 📁 utils/ - Utilities & Helpers
│   │   ├── verify_installation.py      ✅ Installation health checks
│   │   ├── verify_vector_store.py      ✅ Vector store validation
│   │   ├── semantic_chunker.py         ✂️ Code-aware chunking
│   │   ├── config_manager.py           ⚙️ Configuration management
│   │   ├── file_utils.py               📁 File operations
│   │   ├── engine_helper.py            🎮 UE5 helper functions
│   │   ├── source_manager.py           📂 Source directory manager
│   │   ├── cli_client.py               💻 CLI client utilities
│   │   ├── gpu_helper.py               🎮 GPU utilities
│   │   ├── cuda_installer.py           🎮 CUDA installation helper
│   │   ├── gui_theme.py                🎨 GUI theming
│   │   └── __init__.py
│   │
│   ├── 📁 management/ - GUI Tools
│   │   └── gui_dashboard.py            🖥️ Unified Dashboard (Phase 3)
│   │
│   ├── 📁 server/ - HTTP API (Optional)
│   │   ├── retrieval_server.py         🌐 REST API server
│   │   └── __init__.py
│   │
│   └── 📁 research/ - Benchmarks (Optional)
│       ├── model_benchmark.py          📊 Model testing
│       ├── debug_semantic_search.py    🐛 Debugging tool
│       └── __init__.py
│
├── 📁 docs/ - Documentation
│   │
│   ├── 📁 Production/ - User Documentation
│   │   ├── PROJECT_STRUCTURE.md         📋 This file
│   │   ├── MAINTENANCE.md               🛠️ Maintenance guide
│   │   ├── TROUBLESHOOTING.md           🔧 Error resolution
│   │   │
│   │   ├── 📁 Deployment/
│   │   │   ├── DEPLOYMENT.md            📦 Deployment strategies
│   │   │   └── TEAM_SETUP.md            👥 Team onboarding guide
│   │   │
│   │   ├── 📁 GPU/
│   │   │   ├── GPU_SETUP.md             🎮 GPU configuration
│   │   │   └── GPU_SUPPORT.md           🎮 GPU support details
│   │   │
│   │   ├── 📁 GUI/
│   │   │   └── GUI_TOOLS.md             🖥️ GUI tool documentation
│   │   │
│   │   └── 📁 UsageGuide/
│   │       ├── HYBRID_QUERY_GUIDE.md    📚 Query usage guide
│   │       └── AI_AGENT_GUIDE.md        🤖 AI agent integration
│   │
│   ├── 📁 Development/ - Development Documentation
│   │   ├── 📁 ProjectAudits/
│   │   │   ├── AUDIT_REPORT.md          📋 System audit
│   │   │   ├── INTEGRATION_AUDIT.md     📋 Integration audit
│   │   │   ├── IMPLEMENTATION_SUMMARY_20251202.md
│   │   │   ├── REALITY_CHECK_AUDIT_20251202.md
│   │   │   ├── PHASE2_FILTER_PARSER_20251202.md
│   │   │   ├── PHASE3_GUI_FILTERS_20251202.md
│   │   │   └── *.md                     📋 Other audits
│   │   │
│   │   └── 📁 ProjectPlans/
│   │       ├── PHASE_5_RELATIONSHIP_EXTRACTION.md
│   │       ├── PHASE_6_ENVIRONMENT_DETECTION.md
│   │       └── *.md                     🗺️ Future plans
│   │
│   └── 📁 _archive/ - Archived Documentation
│       ├── README.md                     📖 Archive index
│       ├── 📁 planning/                  📝 Obsolete plans
│       └── 📁 audits/                    📋 Old audits
│
├── 📁 examples/ - Example Files
│   ├── sample_batch_queries.jsonl       📦 Batch query examples
│   └── batch_results.jsonl              📦 Example results
│
├── 📁 config/ - Configuration
│   └── .env                             🔐 API keys (gitignored)
│
├── 📁 data/ - Vector Store
│   ├── vector_store.npz                 💾 Embeddings (gitignored or LFS)
│   ├── vector_meta.json                 📊 Metadata (gitignored or LFS)
│   ├── vector_meta_enriched.json        🏷️ Enriched metadata (optional)
│   └── 📁 archived/                     📦 Archived vector stores
│
├── 📁 logs/ - Build Logs
│   └── *.log                            📝 Operation logs
│
├── 📁 dist_temp/ - Temporary Distribution Files
│   └── (temporary build artifacts)
│
└── 📁 tests/ - Test Suite (Empty - Future)
    └── (placeholder)

```

---

## File Status & Recommendations

### ✅ Keep - Core Functionality

| File | Purpose | Status |
|------|---------|--------|
| `Setup.bat` | Main installer entry point | ⭐ Primary installer |
| `launcher.bat` | Unified Dashboard | 🚀 Phase 3 - Main GUI |
| `ask.bat` | Query interface | ✅ Core |
| `tools/health-check.bat` | System validation | ✅ Core |
| `tools/rebuild-index.bat` | Vector store rebuild | ✅ Core |
| `tools/fix-paths.bat` | Path regeneration | ✅ Core |

### ✅ Keep - New Infrastructure (Phases 1-5)

| Directory/File | Purpose | Phase |
|----------------|---------|-------|
| `installer/` | Deployment tools | Phase 2 |
| `tools/` | Backend scripts | Phase 3 reorganization |
| `examples/` | Example batch queries | Phase 4 |
| `src/core/batch_query.py` | Batch processing | Phase 4 |
| `src/core/relationship_extractor.py` | Relationship extraction | Phase 5 |
| `src/core/filter_builder.py` | Filter DSL | Phase 2 |
| `src/core/output_formatter.py` | Result formatting | Phase 3 |
| `src/management/gui_dashboard.py` | Unified Dashboard | Phase 3 |
| `src/utils/source_manager.py` | Source directory manager | Phase 3 |
| `docs/Production/` | Organized production docs | Current |
| `docs/Development/` | Development docs & audits | Current |
| `docs/_archive/` | Archived obsolete docs | Current |

### ✅ Keep - Advanced Features

| File | Purpose | Status |
|------|---------|--------|
| `tools/setup-git-lfs.bat` | Team LFS setup | ✅ Team deployment |
| `tools/serve.bat` | HTTP server | ✅ Optional feature |
| `tools/check-paths.bat` | Path verification | ✅ Diagnostics |
| `tools/check_enrichment.py` | Metadata verification | ✅ Diagnostics |
| `create_dist.bat` | Distribution packaging | ✅ Deployment |

### ⚠️ Optional - Development/Research

| Directory | Purpose | Recommendation |
|-----------|---------|----------------|
| `src/research/` | Model benchmarks | Keep for reference |
| `src/server/` | HTTP API | Optional feature |
| `logs/` | Build logs | Keep (in .gitignore) |
| `tests/` | Test suite | Keep (for future) |
| `dist_temp/` | Temp distribution files | Keep (in .gitignore) |

### 🔄 Deprecated But Kept For Compatibility

| File | Purpose | Status |
|------|---------|--------|
| `src/indexing/BuildSourceIndex.ps1` | PowerShell indexer | ⚠️ Deprecated, use Python |
| `src/indexing/BuildSourceIndexAdmin.bat` | Admin launcher | ⚠️ Deprecated |

### ✅ All Files Serve Current Architecture

After reorganization audit, all files serve a purpose aligned with Phase 1-5 implementation.

---

## Key Architecture Decisions (Phases 1-5)

### 1. GUI-First Deployment (Phase 2)
- **Old:** CLI-only install.bat with complex flags
- **New:** Double-click Setup.bat → GUI opens → Browse & click
- **Rationale:** Lower barrier to entry, visual feedback, less error-prone

### 2. Unified Dashboard (Phase 3)
- **Old:** Multiple scattered batch files and tools
- **New:** Single launcher.bat → Integrated GUI with tabs for all operations
- **Features:** Query, Source Manager, Maintenance, Diagnostics
- **Benefit:** One-stop shop for all user interactions

### 3. Organized Documentation Structure
- **docs/Production/**: User-facing docs (deployment, usage, troubleshooting)
- **docs/Development/**: Development docs (audits, plans)
- **docs/_archive/**: Obsolete/superseded documentation
- **Benefit:** Clear separation of concerns, easier navigation

### 4. Backend Tools Separation (Phase 3)
- **Why:** Separates CLI backend scripts from user entry points
- **Contents:** health-check, rebuild-index, fix-paths, serve, etc.
- **Benefit:** Clean root directory, Dashboard can call tools as needed

### 5. Comprehensive Health Checks (Phase 2)
- **Old:** Silent failures, unclear errors
- **New:** health-check.bat, verify_*.py scripts
- **Checks:** Python version, venv, packages, paths, vector store
- **Benefit:** Self-service troubleshooting

### 6. Team Deployment Support (Phase 2)
- **Path Strategy:** Template → per-machine generation
- **Vector Store:** Build-per-machine OR Git LFS
- **Documentation:** TEAM_SETUP.md, TROUBLESHOOTING.md
- **Benefit:** Multiple UE5 versions, different drive letters

### 7. Batch Query Processing (Phase 4)
- **Feature:** Process multiple queries in one operation
- **Format:** JSONL input/output with structured results
- **Integration:** CLI and GUI support
- **Benefit:** Efficient bulk query processing

### 8. Relationship Extraction (Phase 5)
- **Feature:** Automatically extract class hierarchies, dependencies
- **Integration:** Enriches semantic understanding
- **Output:** Structured relationship data
- **Benefit:** Better context for AI agents

---

## Evolution Across Phases

### Phase 1: Core Query System
- Hybrid query routing (definition + semantic)
- Basic indexing and vector store
- CLI query interface (`ask.bat`)

### Phase 2: Filter System & Deployment
- Filter DSL and builder (`filter_builder.py`)
- GUI installer (`Setup.bat` → `gui_deploy.py`)
- Health checks and validation
- Team deployment support

### Phase 3: Unified Dashboard
- Created `launcher.bat` → Integrated GUI Dashboard
- Organized backend scripts into `tools/` directory
- Source Manager for directory management
- Output formatting improvements
- Reorganized documentation structure

### Phase 4: Batch Processing
- Batch query engine (`batch_query.py`)
- JSONL format support
- Example batch queries in `examples/`
- Dashboard integration

### Phase 5: Relationship Extraction
- Relationship extractor (`relationship_extractor.py`)
- Automatic hierarchy detection
- Dependency mapping
- Enhanced AI agent context

### Key Reorganization Changes

**Documentation Reorganization:**
- Old scattered docs → `docs/Production/` (user docs)
- Development docs → `docs/Development/ProjectAudits/` and `ProjectPlans/`
- Obsolete plans → `docs/_archive/`

**Tools Reorganization:**
- Multiple root-level `.bat` files → Consolidated to `tools/` directory
- `launcher.bat` remains in root as main entry point
- Clean root with only essential entry points

**Added Directories:**
- `examples/` - Batch query examples
- `tools/` - Backend scripts
- `dist_temp/` - Temporary distribution files

### Backward Compatibility

✅ All existing scripts still work
✅ Query interface unchanged (`ask.bat`)
✅ No breaking changes to API
✅ Existing .env files and vector stores compatible
✅ Old batch files still work, just moved to `tools/`

---

## Best Practices

### For Developers

**Commit:**
- All source code (`src/`)
- Documentation (`docs/`)
- Templates (`*.template.txt`)
- Entry scripts (`*.bat`)
- Requirements (`requirements*.txt`)

**Never Commit:**
- `.venv/` - Virtual environment
- `config/.env` - API keys
- `src/indexing/EngineDirs.txt` - Machine-specific
- `data/vector_store.npz` - Unless using Git LFS
- `logs/*.log` - Build logs

### For Team Leads

**Setup Once:**
1. Decide: Build-per-machine OR Git LFS
2. Update .gitignore strategy if using LFS
3. Run `setup-git-lfs.bat` if LFS chosen
4. Document in team README

**Onboarding New Members:**
1. Point them to `docs/TEAM_SETUP.md`
2. Have them double-click `install.bat`
3. Verify with `health-check.bat`

---

## Future Enhancements

**Not Implemented Yet (From DEFERRED_TASKS.md):**
- Automated testing framework (`tests/`)
- Continuous benchmarking
- Web interface alternative to ask.bat
- VS Code extension

**These are intentionally deferred** - focus is on deployment robustness first.

---

## Summary

✅ **Clean architecture** - Every file serves Phase 1-5 implementation
✅ **Organized structure** - Clear separation: Production/Development/Archive docs
✅ **Unified interface** - Single Dashboard for all operations
✅ **Team-ready** - Full deployment infrastructure with health checks
✅ **Feature-complete** - Phases 1-5 complete (Query, Filters, GUI, Batch, Relationships)
✅ **Well-documented** - Organized docs for users and developers

**Current State:** Production-ready with Phase 1-5 complete. Phase 6 (Environment Detection) planned.

**Next Phase:** Phase 6 - Environment Detection (see `docs/Development/ProjectPlans/PHASE_6_ENVIRONMENT_DETECTION.md`)
