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
│   ├── install.bat               ⭐ GUI installer (double-click to deploy)
│   ├── ask.bat                   🔍 Query interface
│   ├── configure.bat             ⚙️ Configuration wizard
│   ├── health-check.bat          ✅ System validation
│   ├── rebuild-index.bat         🔄 Rebuild vector store
│   ├── fix-paths.bat             🔧 Regenerate UE5 paths
│   ├── setup-git-lfs.bat         📦 Git LFS configuration
│   ├── manage.bat                🖥️ GUI management tool
│   ├── manage-directories.bat    📂 Directory management
│   ├── add-directory.bat         ➕ Incremental indexing
│   ├── update.bat                🔼 Update existing installation
│   ├── README.md                 📖 Main documentation
│   ├── requirements.txt          📋 Python dependencies (CPU)
│   ├── requirements-gpu.txt      🎮 Python dependencies (GPU)
│   ├── .gitignore                🚫 Git exclusions
│   └── .indexignore              🚫 Indexing exclusions
│
├── 📁 installer/ - Deployment Tools
│   ├── gui_deploy.py             💎 GUI deployment wizard (tkinter)
│   ├── install_cli.bat           💻 CLI installer (automation)
│   ├── install_helper.py         🔧 File copy helper
│   └── README.md                 📖 Installer documentation
│
├── 📁 src/ - Source Code
│   │
│   ├── 📁 core/ - Query Engine
│   │   ├── hybrid_query.py          🔀 Main hybrid engine
│   │   ├── query_intent.py          🧠 Intent analysis
│   │   ├── definition_extractor.py  🔍 Regex extraction
│   │   ├── filtered_search.py       🎯 Metadata filtering
│   │   ├── query_engine.py          🔎 Semantic search (original)
│   │   └── __init__.py
│   │
│   ├── 📁 indexing/ - Vector Store Building
│   │   ├── build_embeddings.py         🏗️ Main indexer
│   │   ├── detect_engine_path.py       🔍 UE5 path detection
│   │   ├── metadata_enricher.py        🏷️ Entity tagging
│   │   ├── EngineDirs.template.txt     📄 Path template (committed)
│   │   ├── EngineDirs.txt              📄 Paths (machine-specific, gitignored)
│   │   ├── EngineDirs.txt.example      📄 Example paths (reference)
│   │   ├── BuildSourceIndex.ps1        🔧 PowerShell helper
│   │   ├── BuildSourceIndexAdmin.bat   🔧 Admin launcher
│   │   └── __init__.py
│   │
│   ├── 📁 utils/ - Health Checks & Validation
│   │   ├── verify_installation.py      ✅ Comprehensive health checks
│   │   ├── verify_vector_store.py      ✅ Vector store validation
│   │   └── __init__.py
│   │
│   ├── 📁 management/ - GUI Tools
│   │   └── gui_manager.py              🖥️ Management interface
│   │
│   └── 📁 research/ - Benchmarks (Optional)
│       ├── model_benchmark.py          📊 Model testing
│       ├── debug_semantic_search.py    🐛 Debugging tool
│       └── *.json                      📈 Benchmark results
│
├── 📁 docs/ - Documentation
│   ├── TEAM_SETUP.md            👥 Team onboarding guide
│   ├── TROUBLESHOOTING.md       🔧 Error resolution
│   ├── DEPLOYMENT.md            📦 Deployment strategies
│   ├── MAINTENANCE.md           🛠️ Maintenance guide
│   ├── HYBRID_QUERY_GUIDE.md    📚 Query usage guide
│   ├── AUDIT_REPORT.md          📋 System audit
│   ├── IMPROVEMENT_ROADMAP.md   🗺️ Enhancement plans
│   ├── GPU_SETUP.md             🎮 GPU configuration
│   ├── CLAUDE.md                🤖 Claude integration
│   └── DEFERRED_TASKS.md        📝 Future work
│
├── 📁 config/ - Configuration
│   └── .env                     🔐 API keys (gitignored)
│
├── 📁 data/ - Vector Store
│   ├── vector_store.npz         💾 Embeddings (gitignored or LFS)
│   └── vector_meta.json         📊 Metadata (gitignored or LFS)
│
├── 📁 logs/ - Build Logs
│   └── *.log                    📝 Operation logs
│
└── 📁 tests/ - Test Suite (Empty - Future)
    └── (placeholder)

```

---

## File Status & Recommendations

### ✅ Keep - Core Functionality

| File | Purpose | Status |
|------|---------|--------|
| `install.bat` | GUI deployment entry point | ⭐ Primary installer |
| `ask.bat` | User query interface | ✅ Core |
| `configure.bat` | Setup wizard | ✅ Core |
| `health-check.bat` | System validation | ✅ Core |
| `rebuild-index.bat` | Vector store rebuild | ✅ Core |
| `fix-paths.bat` | Path regeneration | ✅ Core |

### ✅ Keep - Advanced Features

| File | Purpose | Status |
|------|---------|--------|
| `setup-git-lfs.bat` | Team LFS setup | ✅ Team deployment |
| `manage.bat` | GUI manager launcher | ✅ Management |
| `manage-directories.bat` | Directory CLI | ✅ Management |
| `add-directory.bat` | Incremental indexing | ✅ Advanced |
| `update.bat` | Update installations | ✅ Maintenance |

### ✅ Keep - New Infrastructure

| Directory | Purpose | Status |
|-----------|---------|--------|
| `installer/` | Deployment tools | ⭐ NEW - Phase 2 |
| `src/utils/` | Health checks | ⭐ NEW - Phase 2 |
| `docs/TEAM_SETUP.md` | Team onboarding | ⭐ NEW - Phase 2 |
| `docs/TROUBLESHOOTING.md` | Error resolution | ⭐ NEW - Phase 2 |

### ⚠️ Optional - Development/Research

| Directory | Purpose | Recommendation |
|-----------|---------|----------------|
| `src/research/` | Model benchmarks | Keep for reference |
| `logs/` | Build logs | Keep (in .gitignore) |
| `tests/` | Test suite | Keep (for future) |

### 🚫 No Redundant Files Found

After audit, all files serve a purpose aligned with current architecture.

---

## Key Architecture Decisions (Phase 2)

### 1. GUI-First Deployment
- **Old:** CLI-only install.bat with complex flags
- **New:** Double-click install.bat → GUI opens → Browse & click
- **Rationale:** Lower barrier to entry, visual feedback, less error-prone

### 2. Dedicated Installer Directory
- **Why:** Separates deployment tools from runtime tools
- **Contents:** GUI wizard, CLI installer, helpers
- **Benefit:** Clean root directory, organized codebase

### 3. Comprehensive Health Checks
- **Old:** Silent failures, unclear errors
- **New:** health-check.bat, verify_*.py scripts
- **Checks:** Python version, venv, packages, paths, vector store
- **Benefit:** Self-service troubleshooting

### 4. Team Deployment Support
- **Path Strategy:** Template → per-machine generation
- **Vector Store:** Build-per-machine OR Git LFS
- **Documentation:** TEAM_SETUP.md, TROUBLESHOOTING.md
- **Benefit:** Multiple UE5 versions, different drive letters

### 5. Validation at Every Step
- **install.bat:** Python version check before GUI
- **GUI:** Prerequisites panel before installation
- **rebuild-index.bat:** EngineDirs.txt validation
- **ask.bat:** venv functionality test
- **detect_engine_path.py:** Post-generation path validation
- **build_embeddings.py:** Post-build verification

---

## Migration from Phase 1 to Phase 2

### What Changed

**Moved:**
- `install.bat` → Now launches GUI (old version → `installer/install_cli.bat`)
- `install_helper.py` → `installer/install_helper.py`

**Created:**
- `installer/` directory
- `installer/gui_deploy.py` (GUI wizard)
- `src/utils/verify_installation.py` (health checks)
- `src/utils/verify_vector_store.py` (vector validation)
- `docs/TEAM_SETUP.md` (onboarding)
- `docs/TROUBLESHOOTING.md` (error resolution)

**Enhanced:**
- `.gitignore` - Team strategy documentation
- `rebuild-index.bat` - EngineDirs.txt validation
- `ask.bat` - venv validation
- `fix-paths.bat` - Template validation
- `src/indexing/detect_engine_path.py` - Path validation
- `src/indexing/build_embeddings.py` - Post-build checks

### Backward Compatibility

✅ All existing scripts still work
✅ CLI installer available for automation (`installer/install_cli.bat`)
✅ No breaking changes to query interface
✅ Existing .env files and vector stores compatible

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

✅ **Zero redundant files** - Every file serves current architecture
✅ **Clean organization** - Dedicated directories for each concern
✅ **Team-ready** - Full deployment infrastructure
✅ **Self-validating** - Health checks at every step
✅ **User-friendly** - GUI installers, clear documentation

**Current State:** Production-ready for team deployment with robust validation.
