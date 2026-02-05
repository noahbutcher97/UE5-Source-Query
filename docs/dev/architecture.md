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
│   ├── setup-git-lfs.bat         📦 Git LFS configuration
│   ├── serve.bat                 🌐 Start HTTP server
│   └── README.md                 📖 Tools documentation
│
├── 📁 ue5_query/ - Source Code
│   │
│   ├── 📁 core/ - Query Engine
│   │   ├── hybrid_query.py              🔀 Main hybrid engine
│   │   ├── query_intent.py              🧠 Intent analysis
│   │   ├── definition_extractor.py      🔍 Regex extraction
│   │   ├── filtered_search.py           🎯 Metadata filtering
│   │   ├── query_engine.py              🔎 Semantic search
│   │   ├── batch_query.py               📦 Batch processing
│   │   ├── relationship_extractor.py    🔗 Relationship extraction
│   │   ├── filter_builder.py            🔧 Filter DSL builder
│   │   ├── output_formatter.py          📄 Result formatting
│   │   └── __init__.py
│   │
│   ├── 📁 indexing/ - Vector Store Building
│   │   ├── build_embeddings.py         🏗️ Main indexer
│   │   ├── detect_engine_path.py       🔍 UE5 path detection
│   │   ├── metadata_enricher.py        🏷️ Entity tagging
│   │   ├── EngineDirs.template.txt     📄 Path template
│   │   ├── EngineDirs.txt              📄 Paths (machine-specific)
│   │   └── __init__.py
│   │
│   ├── 📁 utils/ - Utilities & Helpers
│   │   ├── config_manager.py           ⚙️ Configuration management
│   │   ├── file_utils.py               📁 File operations
│   │   ├── engine_helper.py            🎮 UE5 helper functions
│   │   ├── source_manager.py           📂 Source directory manager
│   │   ├── gpu_helper.py               🎮 GPU utilities
│   │   └── __init__.py
│   │
│   ├── 📁 management/ - GUI Tools
│   │   └── gui_dashboard.py            🖥️ Unified Dashboard
│   │
│   ├── 📁 server/ - HTTP API
│   │   ├── retrieval_server.py         🌐 REST API server (Migrating to FastAPI)
│   │   └── __init__.py
│   │
│   └── 📁 research/ - Benchmarks
│       ├── model_benchmark.py          📊 Model testing
│       └── __init__.py
│
├── 📁 docs/ - Documentation
│   │
│   ├── 📁 user/ - User Documentation
│   │   ├── getting_started.md           📋 User guide
│   │   ├── troubleshooting.md           🔧 Error resolution
│   │   ├── ai_integration.md           🤖 AI agent integration
│   │   └── 📁 audits/                   📋 v2.1 Audit Reports
│   │
│   ├── 📁 deployment/ - Deployment Documentation
│   │   ├── maintenance.md               🛠️ Maintenance guide
│   │   └── team_setup.md                👥 Team onboarding guide
│   │
│   ├── 📁 dev/ - Development Documentation
│   │   ├── architecture.md              📋 This file
│   │   ├── api_reference.md             📋 API Reference
│   │   └── 📁 templates/
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
├── 📁 data/ - Vector Store
├── 📁 logs/ - Build Logs
└── 📁 tests/ - Test Suite

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
| `ue5_query/core/batch_query.py` | Batch processing | Phase 4 |
| `ue5_query/core/relationship_extractor.py` | Relationship extraction | Phase 5 |
| `ue5_query/core/filter_builder.py` | Filter DSL | Phase 2 |
| `ue5_query/core/output_formatter.py` | Result formatting | Phase 3 |
| `ue5_query/management/gui_dashboard.py` | Unified Dashboard | Phase 3 |
| `ue5_query/utils/source_manager.py` | Source directory manager | Phase 3 |
| `docs/user/` | Organized user docs | Current |
| `docs/deployment/` | Deployment strategies | Current |
| `docs/dev/` | Development docs & audits | Current |
| `docs/_archive/` | Archived obsolete docs | Current |

### ✅ Keep - Advanced Features

| File | Purpose | Status |
|------|---------|--------|
| `tools/setup-git-lfs.bat` | Team LFS setup | ✅ Team deployment |
| `tools/serve.bat` | HTTP server | ✅ Optional feature |
| `create_dist.bat` | Distribution packaging | ✅ Deployment |

### ⚠️ Optional - Development/Research

| Directory | Purpose | Recommendation |
|-----------|---------|----------------|
| `ue5_query/research/` | Model benchmarks | Keep for reference |
| `ue5_query/server/` | HTTP API | Active feature (v2.1 target) |
| `logs/` | Build logs | Keep (in .gitignore) |
| `tests/` | Test suite | High priority for v2.1 |

### 🔄 Deprecated But Kept For Compatibility

| File | Purpose | Status |
|------|---------|--------|
| `ue5_query/indexing/BuildSourceIndex.ps1` | PowerShell indexer | ⚠️ Deprecated, use Python |

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
- **docs/user/**: User-facing docs (usage, troubleshooting, agents)
- **docs/deployment/**: Admin-facing docs (maintenance, team setup)
- **docs/dev/**: Development docs (audits, plans, architecture)
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
- **Documentation:** team_setup.md, troubleshooting.md
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

### v2.1 Infrastructure (Post-Audit)
- **FastAPI Migration**: Async server
- **SQLite Migration**: Relational metadata
- **Redis Caching**: Semantic result caching
- **Celery Integration**: Background indexing

### Key Reorganization Changes

**Documentation Reorganization:**
- User docs → `docs/user/`
- Admin docs → `docs/deployment/`
- Development docs → `docs/dev/`
- Obsolete plans → `docs/_archive/`

**Tools Reorganization:**
- Multiple root-level `.bat` files → Consolidated to `tools/` directory
- `launcher.bat` remains in root as main entry point
- Clean root with only essential entry points

### Best Practices

### For Developers

**Commit:**
- All source code (`ue5_query/`)
- Documentation (`docs/`)
- Templates (`*.template.txt`)
- Entry scripts (`*.bat`)
- Requirements (`requirements*.txt`)

**Never Commit:**
- `.venv/` - Virtual environment
- `config/.env` - API keys
- `ue5_query/indexing/EngineDirs.txt` - Machine-specific
- `data/vector_store.npz` - Unless using Git LFS
- `logs/*.log` - Build logs

---

## Future Enhancements

**v2.1 Targets:**
- Automated testing framework (`tests/`)
- Continuous benchmarking
- FastAPI REST interface
- Dockerized deployment

---

## Summary

✅ **Clean architecture** - Every file serves current implementation
✅ **Organized structure** - Clear separation: User/Deployment/Dev/Archive docs
✅ **Unified interface** - Single Dashboard for all operations
✅ **Team-ready** - Full deployment infrastructure with health checks
✅ **Feature-complete** - Phases 1-5 complete
✅ **Well-documented** - Organized docs for all personas

**Current State:** v2.1 foundations in progress. Phase 1-5 complete.

**Next Phase:** Phase 6 - Environment Detection (see `docs/dev/ProjectPlans/PHASE_6_ENVIRONMENT_DETECTION.md`)
