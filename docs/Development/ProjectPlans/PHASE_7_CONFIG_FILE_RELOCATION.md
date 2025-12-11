# Phase 7: Configuration File Relocation

**Status**: PLANNED (Deferred)
**Priority**: Medium
**Estimated Effort**: 8-12 hours
**Risk Level**: High (many downstream dependencies)
**Last Updated**: 2025-12-10

---

## Overview

Relocate `EngineDirs.txt`, `ProjectDirs.txt`, and `EngineDirs.template.txt` from `src/indexing/` to a more logical configuration location (`config/` or `data/`).

### Current Location (Problematic)
```
src/indexing/
├── EngineDirs.template.txt    # Committed template
├── EngineDirs.txt             # Generated, gitignored
├── EngineDirs.txt.example     # Reference example
└── ProjectDirs.txt            # Generated, gitignored
```

### Proposed Location
```
config/
├── EngineDirs.template.txt    # Committed template
├── EngineDirs.txt             # Generated, gitignored
├── EngineDirs.txt.example     # Reference example
└── ProjectDirs.txt            # Generated, gitignored
```

---

## Rationale

**Why Move?**
1. These are configuration files, not source code
2. `src/` should contain only Python source code
3. Clearer separation of concerns
4. More intuitive for users looking for config files
5. Aligns with standard project conventions

**Why Deferred?**
1. 48+ references across the codebase
2. Getting persistent engine paths to display correctly in GUI has been challenging
3. Risk of breaking existing deployments
4. Requires careful migration strategy and thorough testing

---

## Impact Analysis

### CRITICAL Files (Must Update - 9 files)

| File | Lines | Description |
|------|-------|-------------|
| `src/utils/source_manager.py` | 13-15 | **Central hub** - defines all file paths |
| `src/indexing/detect_engine_path.py` | 394-395 | Template/output path construction |
| `src/utils/verify_installation.py` | 185, 236 | Validation checks |
| `installer/gui_deploy.py` | 94, 1351, 1389 | Deployment wizard paths |
| `tools/fix-paths.bat` | 29, 40, 56 | Path regeneration script |
| `tools/rebuild-index.bat` | 72, 87, 103, 184 | Index build defaults |
| `tools/check-paths.bat` | 29, 57 | Path validation utility |
| `.gitignore` | 61 | Ignore generated file |
| Physical files | N/A | Move actual template and example files |

### HIGH Impact Files (4 files)

| File | Lines | Description |
|------|-------|-------------|
| `src/indexing/build_embeddings.py` | 940-941, 974 | CLI argument defaults |
| GUI initialization | Various | Uses detect_engine_path.py |
| Dashboard source tab | Various | Displays configured paths |

### MEDIUM Impact (Documentation - 30+ references)

| File | Approx. References | Action |
|------|-------------------|--------|
| `CLAUDE.md` | 14 | Update examples and paths |
| `docs/Production/TROUBLESHOOTING.md` | 15+ | Update troubleshooting steps |
| `docs/Production/Deployment/DEPLOYMENT.md` | 5+ | Update deployment guide |
| `docs/Production/GPU/GPU_SETUP.md` | 3 | Update build commands |
| `docs/Production/PROJECT_STRUCTURE.md` | 3 | Update structure docs |
| `README.md` | 1 | Update FAQ |
| `PLAN.md` | 4 | Update plan references |

---

## Dependency Graph

```
EngineDirs.txt / ProjectDirs.txt (Files)
    │
    ├─► source_manager.py (Lines 14-15) ◄── CENTRAL HUB
    │       │
    │       ├─► gui_deploy.py (uses SourceManager)
    │       ├─► gui_dashboard.py (uses SourceManager)
    │       └─► verify_installation.py
    │
    ├─► detect_engine_path.py (Lines 394-395)
    │       │
    │       ├─► fix-paths.bat (Line 56)
    │       └─► gui_deploy.py (Line 94)
    │
    ├─► build_embeddings.py
    │       │
    │       ├─► rebuild-index.bat (Line 184)
    │       ├─► ask.bat (indirect)
    │       └─► CLI usage (direct Python calls)
    │
    ├─► rebuild-index.bat (Lines 72, 87, 103)
    │
    ├─► check-paths.bat (Lines 29, 57)
    │
    ├─► verify_installation.py (Line 236)
    │
    └─► Documentation
            ├─► CLAUDE.md
            ├─► TROUBLESHOOTING.md
            ├─► DEPLOYMENT.md
            └─► Other .md files
```

---

## Implementation Plan

### Phase 7.1: Preparation (1 hour)
1. Create `config/` directory if not exists
2. Add migration notes to CHANGELOG
3. Create backup of current state
4. Document rollback procedure

### Phase 7.2: Update SourceManager (2 hours)
**File**: `src/utils/source_manager.py`

```python
# BEFORE (Lines 13-15):
self.engine_template_file = script_dir / "src" / "indexing" / "EngineDirs.template.txt"
self.engine_dirs_file = script_dir / "src" / "indexing" / "EngineDirs.txt"
self.project_dirs_file = script_dir / "src" / "indexing" / "ProjectDirs.txt"

# AFTER:
self.engine_template_file = script_dir / "config" / "EngineDirs.template.txt"
self.engine_dirs_file = script_dir / "config" / "EngineDirs.txt"
self.project_dirs_file = script_dir / "config" / "ProjectDirs.txt"
```

**Also add migration helper**:
```python
def _migrate_legacy_files(self):
    """Migrate files from old src/indexing/ location to config/."""
    old_locations = [
        (self.script_dir / "src" / "indexing" / "EngineDirs.txt", self.engine_dirs_file),
        (self.script_dir / "src" / "indexing" / "ProjectDirs.txt", self.project_dirs_file),
    ]
    for old_path, new_path in old_locations:
        if old_path.exists() and not new_path.exists():
            shutil.copy2(old_path, new_path)
            print(f"Migrated {old_path.name} to config/")
```

### Phase 7.3: Update Core Utilities (2 hours)

**detect_engine_path.py** (Lines 394-395):
```python
# BEFORE:
template = script_dir / "EngineDirs.template.txt"
output = script_dir / "EngineDirs.txt"

# AFTER:
config_dir = script_dir.parent / "config"  # Go up from src/indexing to root, then to config
template = config_dir / "EngineDirs.template.txt"
output = config_dir / "EngineDirs.txt"
```

**verify_installation.py** (Lines 185, 236):
```python
# BEFORE:
template_file = root / "src" / "indexing" / "EngineDirs.template.txt"
engine_dirs_file = root / "src" / "indexing" / "EngineDirs.txt"

# AFTER:
template_file = root / "config" / "EngineDirs.template.txt"
engine_dirs_file = root / "config" / "EngineDirs.txt"
```

### Phase 7.4: Update Deployment Scripts (2 hours)

**gui_deploy.py** (Lines 94, 1351, 1389):
```python
# BEFORE:
template_path = self.source_dir / "src" / "indexing" / "EngineDirs.template.txt"
output = target / "src" / "indexing" / "EngineDirs.txt"
output = target / "src" / "indexing" / "ProjectDirs.txt"

# AFTER:
template_path = self.source_dir / "config" / "EngineDirs.template.txt"
output = target / "config" / "EngineDirs.txt"
output = target / "config" / "ProjectDirs.txt"
```

### Phase 7.5: Update Batch Files (1.5 hours)

**fix-paths.bat**:
```batch
REM BEFORE:
if not exist "%SCRIPT_DIR%..\src\indexing\EngineDirs.template.txt" (
"%SCRIPT_DIR%..\src\indexing\detect_engine_path.py" "%SCRIPT_DIR%..\src\indexing\EngineDirs.template.txt" "%SCRIPT_DIR%..\src\indexing\EngineDirs.txt"

REM AFTER:
if not exist "%SCRIPT_DIR%..\config\EngineDirs.template.txt" (
"%SCRIPT_DIR%..\src\indexing\detect_engine_path.py" "%SCRIPT_DIR%..\config\EngineDirs.template.txt" "%SCRIPT_DIR%..\config\EngineDirs.txt"
```

**rebuild-index.bat**:
```batch
REM BEFORE:
if not exist "%SCRIPT_DIR%..\src\indexing\EngineDirs.txt" (
set "BUILD_ARGS=--dirs-file %SCRIPT_DIR%..\src\indexing\EngineDirs.txt"
--project-dirs-file "src\indexing\ProjectDirs.txt"

REM AFTER:
if not exist "%SCRIPT_DIR%..\config\EngineDirs.txt" (
set "BUILD_ARGS=--dirs-file %SCRIPT_DIR%..\config\EngineDirs.txt"
--project-dirs-file "config\ProjectDirs.txt"
```

**check-paths.bat**:
```batch
REM BEFORE:
engine_file = Path('src/indexing/EngineDirs.txt')
project_file = Path('src/indexing/ProjectDirs.txt')

REM AFTER:
engine_file = Path('config/EngineDirs.txt')
project_file = Path('config/ProjectDirs.txt')
```

### Phase 7.6: Update Git Configuration (0.5 hours)

**.gitignore**:
```
# BEFORE:
src/indexing/EngineDirs.txt

# AFTER:
config/EngineDirs.txt
config/ProjectDirs.txt
```

### Phase 7.7: Move Physical Files (0.5 hours)

```bash
# Move template (committed)
git mv src/indexing/EngineDirs.template.txt config/EngineDirs.template.txt

# Move example (committed)
git mv src/indexing/EngineDirs.txt.example config/EngineDirs.txt.example

# Generated files are gitignored, just create config/ dir
mkdir config
```

### Phase 7.8: Update Documentation (1.5 hours)

Files to update:
- `CLAUDE.md` - 14 references
- `docs/Production/TROUBLESHOOTING.md` - 15+ references
- `docs/Production/Deployment/DEPLOYMENT.md` - 5+ references
- `docs/Production/GPU/GPU_SETUP.md` - 3 references
- `docs/Production/PROJECT_STRUCTURE.md` - 3 references
- `README.md` - 1 reference
- This plan file

### Phase 7.9: Testing (2 hours)

**Test Checklist**:
- [ ] `Setup.bat` (gui_deploy.py) creates files in correct location
- [ ] `fix-paths.bat` regenerates EngineDirs.txt correctly
- [ ] `rebuild-index.bat` finds and uses config files
- [ ] `check-paths.bat` validates paths correctly
- [ ] Dashboard Source Manager tab shows correct paths
- [ ] Deployment Wizard reads template correctly
- [ ] `verify_installation.py` validates new paths
- [ ] Fresh deployment works end-to-end
- [ ] Existing deployment migration works
- [ ] All 6 unit tests pass

---

## Migration Strategy for Existing Deployments

### Automatic Migration
Add to `SourceManager.__init__()`:
```python
def __init__(self, script_dir):
    self.script_dir = script_dir
    self.config_dir = script_dir / "config"
    self.config_dir.mkdir(exist_ok=True)

    # New locations
    self.engine_template_file = self.config_dir / "EngineDirs.template.txt"
    self.engine_dirs_file = self.config_dir / "EngineDirs.txt"
    self.project_dirs_file = self.config_dir / "ProjectDirs.txt"

    # Migrate from old location if needed
    self._migrate_legacy_files()
```

### Manual Migration (if needed)
```batch
REM For users with existing deployments
mkdir config
move src\indexing\EngineDirs.txt config\
move src\indexing\ProjectDirs.txt config\
copy src\indexing\EngineDirs.template.txt config\
```

---

## Rollback Procedure

If issues arise:
1. Revert git commits
2. Move files back to `src/indexing/`
3. Restore `.gitignore`
4. Run `fix-paths.bat` to regenerate

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking existing deployments | Medium | High | Auto-migration in SourceManager |
| GUI path display issues | Medium | Medium | Thorough GUI testing |
| Batch file path errors | Low | High | Test on fresh Windows install |
| Documentation out of sync | Low | Low | Update docs in same PR |

---

## Success Criteria

1. [ ] All files relocated to `config/`
2. [ ] No hardcoded `src/indexing/` paths remain
3. [ ] Existing deployments auto-migrate
4. [ ] All batch files work correctly
5. [ ] GUI displays paths correctly
6. [ ] All tests pass
7. [ ] Documentation updated
8. [ ] No user-reported regressions after 1 week

---

## Dependencies

- Requires: Phases A-D complete (GUI Feature Parity) ✅
- Blocks: None
- Related: Phase 6 (Environment Detection) - could be done in parallel

---

## Notes

- Dashboard `gui_dashboard.py` already avoids direct EngineDirs.txt usage (line 2016 comment), suggesting architectural alignment with this change
- Consider adding `config/` to the distribution optimization exclusions once this is complete
- Template file should remain committed; generated files remain gitignored

---

## Audit Reference

Full audit conducted 2025-12-10 by exploration agent. Found 48+ references across:
- 8 Python files
- 5 batch files
- 12+ documentation files
- 1 template file
- Configuration files

See conversation history for detailed line-by-line breakdown.
