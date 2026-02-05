# Implementation Plan: GUI Functional Parity & Distribution Optimization

**Date**: 2025-12-10
**Objective**: Achieve full functional parity between Deployment Wizard and Unified Dashboard while optimizing file distribution to keep deployments lean.

---

## Executive Summary

This plan addresses two interconnected goals:

1. **GUI Functional Parity**: Align the Deployment Wizard and Unified Dashboard to share common infrastructure and capabilities while respecting their distinct purposes
2. **Distribution Optimization**: Identify and exclude dev-only files from deployments, reducing bloat and user confusion

**Key Findings:**
- Dashboard at 95% integration, Wizard at 65% (appropriate for their roles)
- ~525KB of dev-only files currently shipping to deployments
- 12 shared utilities/patterns that should be extracted to avoid duplication
- 5 high-priority feature additions needed for parity

---

## Part 1: GUI Functional Parity Analysis

### 1.1 Tool Purposes (Distinct & Complementary)

**Deployment Wizard** (`installer/gui_deploy.py`):
- **When**: First-time installation or updating existing deployment
- **Who**: System administrators, team leads
- **Purpose**: Environment preparation, CUDA setup, initial deployment
- **Should remain install-focused**: YES

**Unified Dashboard** (`src/management/gui_dashboard.py`):
- **When**: Post-installation, daily operations
- **Who**: Developers, users performing queries and maintenance
- **Purpose**: Live querying, configuration, updates, diagnostics
- **Should remain operations-focused**: YES

**Conclusion**: Both tools serve distinct purposes and should NOT try to replicate each other's primary function. Focus parity efforts on shared infrastructure and configuration patterns.

---

### 1.2 High-Priority Features to Add

#### Add to Wizard (5 features):

1. **Priority-Based Engine Detection** (CRITICAL)
   - **Current**: Simple auto-detect with health scores
   - **Target**: Dashboard's smart detection (vector store → uproject → config → auto)
   - **Why**: More robust, handles edge cases, matches user expectations from Dashboard
   - **Implementation**: Extract `get_smart_engine_path()` from `src/utils/engine_helper.py` to shared utility
   - **Files Modified**: `installer/gui_deploy.py` lines 450-520 (engine detection section)
   - **Estimated Effort**: 2 hours

2. **Health Score Display in Version Selector** (HIGH)
   - **Current**: Version selector shows paths only
   - **Target**: Add health scores (0-100) like Dashboard's engine source indicator
   - **Why**: Helps users choose best engine installation
   - **Implementation**: Integrate `detect_engine_path.py`'s health scoring into version dialog
   - **Files Modified**: `installer/gui_deploy.py` lines 520-580 (version selector dialog)
   - **Estimated Effort**: 1.5 hours

3. **Version Mismatch Warnings** (HIGH)
   - **Current**: No validation against .uproject version
   - **Target**: Warn if detected engine version ≠ project's .uproject engine association
   - **Why**: Prevents indexing wrong engine version
   - **Implementation**: Add .uproject parsing in diagnostics tab, show warning banner
   - **Files Modified**: `installer/gui_deploy.py` lines 850-900 (diagnostics checks)
   - **Estimated Effort**: 2 hours

4. **SourceManager Integration** (MEDIUM)
   - **Current**: Writes directly to EngineDirs.txt and ProjectDirs.txt
   - **Target**: Use `src/utils/source_manager.py` for persistence
   - **Why**: Consistency with Dashboard, better error handling, future-proof
   - **Implementation**: Replace direct file writes with SourceManager API calls
   - **Files Modified**: `installer/gui_deploy.py` lines 650-750 (source manager tab)
   - **Estimated Effort**: 3 hours

5. **Shared Help Dialog Utility** (LOW)
   - **Current**: Duplicated engine detection help dialog in both GUIs
   - **Target**: Extract to `src/utils/gui_helpers.py`
   - **Why**: DRY principle, single source of truth
   - **Implementation**: Create shared `show_engine_detection_help()` function
   - **Files Modified**:
     - Create `src/utils/gui_helpers.py`
     - `installer/gui_deploy.py` lines 540-565
     - `src/management/gui_dashboard.py` lines 620-645
   - **Estimated Effort**: 1 hour

#### Add to Dashboard (3 features):

6. **Progress Bars for Long Operations** (HIGH)
   - **Current**: Log-only feedback for rebuild operations
   - **Target**: Determinate progress bar like Wizard's installation tab
   - **Why**: Better UX, user knows system isn't frozen
   - **Implementation**: Add ttk.Progressbar to Maintenance tab, update during rebuild
   - **Files Modified**: `src/management/gui_dashboard.py` lines 950-1050 (maintenance tab)
   - **Estimated Effort**: 2 hours

7. **Configuration Preview** (MEDIUM)
   - **Current**: "Test Configuration" validates, no preview
   - **Target**: Show current vs pending config like Wizard's preview area
   - **Why**: Users see changes before saving
   - **Implementation**: Add ScrolledText widget showing config diff
   - **Files Modified**: `src/management/gui_dashboard.py` lines 750-850 (configuration tab)
   - **Estimated Effort**: 2.5 hours

8. **CUDA Setup Option in Maintenance** (MEDIUM)
   - **Current**: Assumes CUDA installed during initial deployment
   - **Target**: Add "Enable GPU Support" button that runs CUDA installer
   - **Why**: Users may want to enable GPU post-install
   - **Implementation**: Integrate `src/utils/cuda_installer.py` into Maintenance tab
   - **Files Modified**: `src/management/gui_dashboard.py` lines 950-1050 (maintenance tab)
   - **Estimated Effort**: 2 hours

---

### 1.3 Shared Utilities to Extract

Create `src/utils/gui_helpers.py` with shared functions:

```python
"""Shared GUI utilities for Deployment Wizard and Unified Dashboard."""

def show_engine_detection_help(parent):
    """Show engine detection help dialog."""
    # Extract from both GUIs

def show_version_mismatch_warning(parent, project_version, engine_version):
    """Show warning dialog for version mismatch."""

def create_dark_theme_text(parent, **kwargs):
    """Create ScrolledText with standardized dark theme."""

def show_health_score_indicator(parent, score):
    """Display health score with color-coded indicator."""

def validate_engine_path_interactive(parent, path):
    """Validate engine path with user-friendly error messages."""
```

**Files Modified**:
- Create `src/utils/gui_helpers.py`
- Update `installer/gui_deploy.py` to import and use helpers
- Update `src/management/gui_dashboard.py` to import and use helpers

**Estimated Effort**: 3 hours

---

### 1.4 Low-Priority Alignments (Deferred)

These are nice-to-have but not critical for functional parity:

- **Standardized dark theme for all operation logs**: Both GUIs work fine with current themes
- **Deployment config editing in Dashboard**: Rare use case, low ROI
- **Pre-flight checks in Dashboard Diagnostics**: System Health already comprehensive
- **Auto-fix suggestions in Wizard**: Test Configuration already does this

---

## Part 2: File Distribution Optimization

### 2.1 Dev-Only Files Currently Shipping (REMOVE)

**Problem**: ~525KB of dev-only files shipping to every deployment, causing confusion.

**Files to Exclude**:

1. **src/research/** (35KB)
   - Contains: debug_semantic_search.py, model_benchmark.py, benchmark JSONs
   - Why: Research/debugging tools, no production value
   - Currently ships to: `D:\UnrealProjects\5.3\hijack_prototype\Scripts\src\research`

2. **docs/Development/** (~250KB)
   - Contains: Dev audits, project plans, testing guides, design docs
   - Why: Dev-only context, confuses users
   - Currently ships unnecessarily

3. **docs/_archive/** (~200KB)
   - Contains: Obsolete planning docs, old audits
   - Why: Historical clutter, no user value

4. **src/indexing/BuildSourceIndex.ps1** (11KB)
   - Deprecated PowerShell indexer
   - CLAUDE.md confirms: "PowerShell indexer deprecated but not removed"

5. **src/indexing/BuildSourceIndexAdmin.bat** (212 bytes)
   - Launcher for deprecated PowerShell indexer

6. **CLAUDE.md** (23KB)
   - Dev-only AI assistant guide with full architecture/internals
   - Too detailed for end users

7. **GEMINI.md** (3.9KB)
   - Alternative AI assistant guide

8. **tools/setup-git-lfs.bat**
   - Dev collaboration tool for Git LFS setup

9. **tests/DEPLOYMENT_TEST_RESULTS.md**
   - Historical test run results, dev artifact

**Total Savings**: ~525KB per deployment
**Clarity Impact**: HIGH (removes confusion about deprecated/research tools)

---

### 2.2 Files That Should Always Ship

**Core System** (100-150MB total):
- src/core/ (all files)
- src/indexing/ (exclude deprecated .ps1 files)
- src/utils/ (all files)
- src/management/ (all files)
- src/server/ (conditional: if HTTP mode)
- installer/ (keep for re-deployment capability)
- tools/ (exclude setup-git-lfs.bat)
- docs/Production/ (all files)
- tests/ (all files - valuable for validation)
- examples/ (all files - learning resource)
- Root files: ask.bat, launcher.bat, Setup.bat, update.bat, README.md, requirements*.txt, .indexignore

---

### 2.3 Implementation: Update Sync Strategy

**File to Modify**: `tools/update.py`

**Current Code** (line 292):
```python
sync_dirs = ["src", "installer", "tools", "tests", "docs"]
```

**New Code**:
```python
# Main directories to sync
sync_dirs = ["src", "installer", "tools", "tests", "docs", "examples"]

# Deployment exclusion patterns
DEPLOYMENT_EXCLUDES = [
    # Research/debug tools
    "src/research",
    "src/research/**",

    # Dev-only documentation
    "docs/Development",
    "docs/Development/**",
    "docs/_archive",
    "docs/_archive/**",

    # Deprecated code
    "src/indexing/BuildSourceIndex.ps1",
    "src/indexing/BuildSourceIndexAdmin.bat",

    # Dev test artifacts
    "tests/DEPLOYMENT_TEST_RESULTS.md",

    # Dev collaboration tools
    "tools/setup-git-lfs.bat",

    # Dev-only AI guides
    "CLAUDE.md",
    "GEMINI.md",
]

# Apply exclusions
exclude_patterns = DEFAULT_EXCLUDES + DEPLOYMENT_EXCLUDES + config.get("exclude_patterns", [])
```

**Lines to Modify**:
- Line 292: Add "examples" to sync_dirs
- Line 60: Add DEPLOYMENT_EXCLUDES constant
- Line 295: Apply DEPLOYMENT_EXCLUDES to exclude_patterns
- Lines 401, 496: Same changes for update_from_remote and rollback functions

**Estimated Effort**: 1 hour

---

### 2.4 Implementation: Update Distribution Builder

**File to Modify**: `create_dist.bat`

**Current Code**: Copies everything from src/, tools/, docs/

**New Code**:
```batch
REM Copy src (excluding research and deprecated)
robocopy "%SCRIPT_DIR%src" "%DIST_DIR%\src" /E /XD research __pycache__ /XF BuildSourceIndex.ps1 BuildSourceIndexAdmin.bat /NFL /NDL /NJH /NJS

REM Copy tools (excluding git-lfs setup)
robocopy "%SCRIPT_DIR%tools" "%DIST_DIR%\tools" /E /XF setup-git-lfs.bat /NFL /NDL /NJH /NJS

REM Copy production docs only
robocopy "%SCRIPT_DIR%docs\Production" "%DIST_DIR%\docs\Production" /E /NFL /NDL /NJH /NJS

REM Copy tests (excluding dev artifacts)
robocopy "%SCRIPT_DIR%tests" "%DIST_DIR%\tests" /E /XF DEPLOYMENT_TEST_RESULTS.md /NFL /NDL /NJH /NJS

REM Copy examples
robocopy "%SCRIPT_DIR%examples" "%DIST_DIR%\examples" /E /NFL /NDL /NJH /NJS

REM Copy installer
robocopy "%SCRIPT_DIR%installer" "%DIST_DIR%\installer" /E /NFL /NDL /NJH /NJS

REM Copy root files (excluding dev-only guides)
copy "%SCRIPT_DIR%ask.bat" "%DIST_DIR%\" >NUL
copy "%SCRIPT_DIR%launcher.bat" "%DIST_DIR%\" >NUL
copy "%SCRIPT_DIR%Setup.bat" "%DIST_DIR%\" >NUL
copy "%SCRIPT_DIR%update.bat" "%DIST_DIR%\" >NUL
copy "%SCRIPT_DIR%README.md" "%DIST_DIR%\" >NUL
copy "%SCRIPT_DIR%requirements*.txt" "%DIST_DIR%\" >NUL
copy "%SCRIPT_DIR%.indexignore" "%DIST_DIR%\" >NUL
REM Explicitly skip CLAUDE.md and GEMINI.md
```

**Estimated Effort**: 30 minutes

---

### 2.5 Clean Existing Deployments

After updating sync logic, clean existing deployments to remove already-shipped dev files.

**Implementation**: Add cleanup function to `tools/update.py`:

```python
def clean_dev_files(deployment_root: Path):
    """Remove dev-only files from existing deployment."""
    dev_files = [
        "src/research",
        "docs/Development",
        "docs/_archive",
        "src/indexing/BuildSourceIndex.ps1",
        "src/indexing/BuildSourceIndexAdmin.bat",
        "CLAUDE.md",
        "GEMINI.md",
        "tools/setup-git-lfs.bat",
        "tests/DEPLOYMENT_TEST_RESULTS.md",
    ]

    for file_path in dev_files:
        full_path = deployment_root / file_path
        if full_path.is_dir():
            shutil.rmtree(full_path, ignore_errors=True)
            print(f"Removed dev directory: {file_path}")
        elif full_path.is_file():
            full_path.unlink(missing_ok=True)
            print(f"Removed dev file: {file_path}")
```

Call this function at the start of `update_from_local()` and `update_from_remote()`.

**Estimated Effort**: 1 hour

---

### 2.6 Update Documentation

**File to Modify**: `docs/Production/Deployment/DEPLOYMENT.md`

Add new section:

```markdown
## Distribution Strategy

### Files Included in Deployments

**Core System** (always ships):
- src/core/ - Query engine
- src/indexing/ - Embedding builder (Python only, PowerShell deprecated)
- src/utils/ - Utilities and helpers
- src/management/ - GUI Dashboard
- installer/ - Deployment wizard (enables re-deployment)
- tools/ - Maintenance scripts
- tests/ - Validation suite
- docs/Production/ - User documentation
- examples/ - Sample queries

**Excluded from Deployments** (dev-only):
- src/research/ - Debug and benchmark tools
- docs/Development/ - Architecture and planning docs
- docs/_archive/ - Historical documentation
- CLAUDE.md, GEMINI.md - AI assistant development guides
- Deprecated PowerShell indexer files

### Why This Matters

Lean deployments reduce:
- Confusion (users don't see irrelevant dev tools)
- Disk usage (save ~525KB per deployment)
- Update time (fewer files to sync)
- Support burden (clearer what's production vs dev)
```

**Estimated Effort**: 30 minutes

---

## Part 3: Implementation Roadmap

### Phase A: Shared Infrastructure (4 hours)

**Goal**: Extract common utilities to avoid duplication

1. Create `src/utils/gui_helpers.py` with shared functions
2. Extract engine detection help dialog from both GUIs
3. Extract dark theme text widget creator
4. Extract version validation logic
5. Update both GUIs to import and use helpers

**Files Modified**:
- Create `src/utils/gui_helpers.py`
- `installer/gui_deploy.py`
- `src/management/gui_dashboard.py`

**Testing**:
- Launch Deployment Wizard → verify help dialog works
- Launch Unified Dashboard → verify help dialog works
- Verify both GUIs function identically to before

---

### Phase B: Deployment Wizard Enhancements (9 hours)

**Goal**: Add high-priority features to Wizard

1. **Priority-Based Engine Detection** (2 hours)
   - Replace simple auto-detect with smart detection
   - Test: Verify detection priority (vector store → uproject → config → auto)

2. **Health Score Display** (1.5 hours)
   - Add health scores to version selector dialog
   - Test: Multiple engine versions show correct scores

3. **Version Mismatch Warnings** (2 hours)
   - Parse .uproject file, compare with detected engine
   - Show warning banner if mismatch
   - Test: Detect UE 5.3 project with UE 5.2 engine selected

4. **SourceManager Integration** (3 hours)
   - Replace direct file writes with SourceManager API
   - Test: Verify EngineDirs.txt and ProjectDirs.txt generated correctly

**Files Modified**:
- `installer/gui_deploy.py`

**Testing**:
- Run full installation with new features
- Verify engine detection more robust
- Verify version warnings trigger correctly
- Verify source manager persistence works

---

### Phase C: Unified Dashboard Enhancements (6.5 hours)

**Goal**: Add high-priority features to Dashboard

1. **Progress Bars for Long Operations** (2 hours)
   - Add progress bar to Maintenance tab
   - Update during index rebuild
   - Test: Rebuild index, verify progress updates

2. **Configuration Preview** (2.5 hours)
   - Add preview area showing current vs pending config
   - Test: Change config, verify diff shown correctly

3. **CUDA Setup Option** (2 hours)
   - Add "Enable GPU Support" button to Maintenance
   - Integrate cuda_installer.py
   - Test: Enable GPU on deployment without CUDA, verify installer launches

**Files Modified**:
- `src/management/gui_dashboard.py`

**Testing**:
- Launch Dashboard
- Verify progress bar during rebuild
- Verify config preview accurate
- Verify CUDA installer launches

---

### Phase D: Distribution Optimization (3 hours)

**Goal**: Exclude dev-only files from deployments

1. **Update tools/update.py** (1 hour)
   - Add DEPLOYMENT_EXCLUDES constant
   - Apply exclusions to sync operations
   - Add clean_dev_files() function
   - Test: Update deployment, verify research/ not copied

2. **Update create_dist.bat** (30 minutes)
   - Add /XD and /XF flags to exclude dev files
   - Test: Create distribution, verify dev files excluded

3. **Clean Existing Deployments** (30 minutes)
   - Run clean_dev_files() on hijack_prototype Scripts/
   - Verify dev files removed

4. **Update Documentation** (1 hour)
   - Add Distribution Strategy section to DEPLOYMENT.md
   - Document exclusion patterns
   - Test: Read docs, verify clarity

**Files Modified**:
- `tools/update.py`
- `create_dist.bat`
- `docs/Production/Deployment/DEPLOYMENT.md`

**Testing**:
- Run update from dev repo → deployment
- Verify src/research/ absent
- Verify docs/Development/ absent
- Verify all production files present
- Run health check to ensure system works

---

### Phase E: Validation & Testing (2 hours)

**Goal**: Comprehensive testing of all changes

1. **Dev Repo Testing**:
   - Run all tests: `python tests/run_tests.py`
   - Build index: `python src/indexing/build_embeddings.py --dirs-file src/indexing/EngineDirs.txt --force`
   - Launch both GUIs: `installer/gui_deploy.py`, `launcher.bat`
   - Create distribution: `create_dist.bat`
   - Verify distribution excludes dev files

2. **Deployment Testing**:
   - Update deployment: `cd Scripts && update.bat`
   - Verify dev files removed
   - Run all tests: `python tests/run_tests.py`
   - Launch Dashboard: `launcher.bat`
   - Query system: `ask.bat "FHitResult members"`
   - Rebuild index from Dashboard
   - Verify progress bar works
   - Test CUDA installer (if applicable)

3. **Regression Testing**:
   - Verify existing functionality unchanged
   - Verify queries produce same results
   - Verify config saving/loading works
   - Verify source management works

**Validation Checklist**:
- [ ] All 6 tests pass in dev repo
- [ ] All 6 tests pass in deployment
- [ ] Index builds successfully (both environments)
- [ ] Query system produces accurate results
- [ ] Both GUIs launch without errors
- [ ] Shared utilities work in both GUIs
- [ ] Dev files excluded from deployment
- [ ] Distribution size reduced by ~525KB
- [ ] Documentation accurate and complete

---

## Part 4: Risks & Mitigations

### Risk 1: Breaking Existing Deployments
**Probability**: Medium
**Impact**: High
**Mitigation**:
- Test update.py changes thoroughly in dev repo first
- Create backup before updating deployments
- Add rollback instructions to DEPLOYMENT.md
- Use update.py's built-in backup mechanism

### Risk 2: GUI Code Duplication Bugs
**Probability**: Low
**Impact**: Medium
**Mitigation**:
- Extract shared code early (Phase A)
- Comprehensive testing of both GUIs
- User acceptance testing before rollout

### Risk 3: SourceManager Integration Issues
**Probability**: Medium
**Impact**: Medium
**Mitigation**:
- Test SourceManager API thoroughly
- Keep fallback to direct file writes (commented out)
- Verify persistence across restarts

### Risk 4: File Exclusion Too Aggressive
**Probability**: Low
**Impact**: High
**Mitigation**:
- Conservative exclusion list (only clear dev-only files)
- Manual verification of distribution contents
- Keep installer/ and tests/ despite potential to exclude
- Document all exclusions in DEPLOYMENT.md

---

## Part 5: Success Criteria

### Functional Parity Success:
1. ✅ Both GUIs share common detection/validation logic
2. ✅ Wizard has robust engine detection (priority-based)
3. ✅ Wizard warns on version mismatches
4. ✅ Dashboard has progress bars for long operations
5. ✅ Dashboard allows config preview before saving
6. ✅ Both GUIs use SourceManager for persistence
7. ✅ No code duplication in help dialogs or utilities

### Distribution Optimization Success:
1. ✅ src/research/ absent from deployments
2. ✅ docs/Development/ and docs/_archive/ absent
3. ✅ Deprecated PowerShell files absent
4. ✅ CLAUDE.md/GEMINI.md absent (or simplified template)
5. ✅ Deployment size reduced by ~500KB
6. ✅ All core functionality works in deployment
7. ✅ Update system cleanly removes dev files

### Overall System Health:
1. ✅ All 6 tests pass (dev repo and deployment)
2. ✅ Index builds successfully
3. ✅ Query system accurate
4. ✅ Both GUIs launch and function
5. ✅ Documentation complete and accurate

---

## Part 6: Timeline Estimate

**Total Estimated Effort**: 24.5 hours

- Phase A (Shared Infrastructure): 4 hours
- Phase B (Wizard Enhancements): 9 hours
- Phase C (Dashboard Enhancements): 6.5 hours
- Phase D (Distribution Optimization): 3 hours
- Phase E (Validation & Testing): 2 hours

**Note**: Estimates assume single developer working sequentially. Phases A-D can be partially parallelized.

---

## Part 7: Post-Implementation Tasks

### Documentation Updates:
1. Update CLAUDE.md with new shared utilities
2. Update GUI_TOOLS.md with new features
3. Update DEPLOYMENT.md with distribution strategy
4. Create CLAUDE_MD_TEMPLATE.md for deployments (simplified)

### User Communication:
1. Notify team of new features (if team deployment)
2. Document migration path for existing deployments
3. Provide rollback instructions

### Future Enhancements (Out of Scope):
1. Installer `--minimal` flag to skip tests/ and installer/ post-install
2. Complete removal of deprecated PowerShell indexer (delete files)
3. Deployment config editing in Dashboard
4. Auto-fix suggestions in Wizard configuration

---

## Appendix A: File Modification Summary

| File | Lines Modified | Type | Phase |
|------|---------------|------|-------|
| src/utils/gui_helpers.py | NEW FILE | Create | A |
| installer/gui_deploy.py | 450-520, 540-565, 650-750, 850-900 | Modify | A, B |
| src/management/gui_dashboard.py | 620-645, 750-850, 950-1050 | Modify | A, C |
| tools/update.py | 60, 292, 295, 401, 496 + new function | Modify | D |
| create_dist.bat | Full rewrite | Modify | D |
| docs/Production/Deployment/DEPLOYMENT.md | New section | Modify | D |

---

## Appendix B: Testing Checklist

### Dev Repo Tests:
- [ ] Import gui_helpers: `python -c "from src.utils.gui_helpers import *"`
- [ ] Launch Wizard: `python installer/gui_deploy.py`
- [ ] Launch Dashboard: `python launcher.bat`
- [ ] Run tests: `python tests/run_tests.py`
- [ ] Build index: `python src/indexing/build_embeddings.py --dirs-file src/indexing/EngineDirs.txt --force`
- [ ] Create dist: `create_dist.bat`
- [ ] Verify dist excludes: `dir UE5-Query-Suite\src\research` (should not exist)

### Deployment Tests:
- [ ] Update: `cd Scripts && update.bat`
- [ ] Verify exclusions: `dir src\research` (should not exist)
- [ ] Run tests: `python tests/run_tests.py`
- [ ] Launch Dashboard: `launcher.bat`
- [ ] Query: `ask.bat "FHitResult members"`
- [ ] Rebuild index with progress bar
- [ ] Test config preview
- [ ] Test CUDA installer (if GPU present)

### Regression Tests:
- [ ] Existing queries produce same results
- [ ] Config save/load works
- [ ] Source manager persists correctly
- [ ] Update system works bidirectionally
- [ ] Health checks pass

---

## Appendix C: Decision Log

### Decision 1: Keep installer/ in Deployments
**Rationale**: Enables re-deployment to other locations, only 60KB overhead
**Alternative Considered**: Remove post-install with `--minimal` flag
**Chosen**: Keep for convenience

### Decision 2: Keep tests/ in Deployments
**Rationale**: Valuable for post-install validation, users reported test failures
**Alternative Considered**: Make tests dev-only
**Chosen**: Ship tests, document as validation tools

### Decision 3: Both GUIs Keep Distinct Purposes
**Rationale**: Wizard is install-focused, Dashboard is operations-focused
**Alternative Considered**: Merge into single super-GUI
**Chosen**: Keep separate, share infrastructure only

### Decision 4: Extract Shared Utilities
**Rationale**: Avoid code duplication, DRY principle
**Alternative Considered**: Keep duplicated code
**Chosen**: Extract to src/utils/gui_helpers.py

### Decision 5: Conservative Exclusion List
**Rationale**: Only exclude clearly dev-only files, avoid breaking deployments
**Alternative Considered**: Aggressive exclusions (remove installer, tests, examples)
**Chosen**: Conservative approach, can expand later

---

## Summary

This plan achieves full functional parity between the two GUIs while optimizing distribution:

**GUI Enhancements**:
- 5 features added to Wizard (priority detection, health scores, version warnings, SourceManager, shared dialogs)
- 3 features added to Dashboard (progress bars, config preview, CUDA setup)
- Shared utilities extracted (gui_helpers.py)
- Zero code duplication in help dialogs

**Distribution Optimization**:
- ~525KB dev files excluded per deployment
- 9 dev-only files/directories identified and excluded
- Clean existing deployments of dev bloat
- Clear documentation of distribution strategy

**Outcome**: Both GUIs aligned on infrastructure, respecting distinct purposes, with lean deployments and comprehensive testing.
