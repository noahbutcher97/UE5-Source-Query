# Next Session Quick Start - GUI Feature Parity (Phases B & C)

**Date:** 2025-12-10
**Status:** Ready to begin Phases B & C
**Estimated Time:** 15 hours (8.5h Phase B + 6.5h Phase C)

---

## What's Been Completed

### ✅ Phase A: Shared Infrastructure (DONE)
- Created `src/utils/gui_helpers.py` with 10+ shared utilities
- Both GUIs now use shared code (no duplication)
- Bug fix: Engine path detection working correctly
- Tested: All GUIs launch successfully

### ✅ Phase D: Distribution Optimization (DONE)
- `tools/update.py` excludes dev-only files (9 patterns)
- `create_dist.bat` updated with exclusion flags
- `clean_dev_files()` function removes dev bloat automatically
- Bug fix: Pattern filtering now works correctly
- Tested: Deployment excludes ~525KB of dev files

### 📝 Recent Commits
- `aec29d8` - feat: add shared GUI utilities
- `e4d07e4` - feat: optimize distributions by excluding dev-only files
- `5d6f6c9` - fix: correct shutil.ignore_patterns() for path-based exclusions

---

## What's Next: Phases B & C

### Phase B: Deployment Wizard Enhancements (8.5 hours)

**Goal:** Make Deployment Wizard more robust and informative

#### Task 1: Priority-Based Engine Detection (2 hours)
**Current:** Simple auto-detect with health scores
**Target:** Dashboard's smart detection (vector store → uproject → config → auto)

**Implementation:**
1. Extract `get_smart_engine_path()` from `src/utils/engine_helper.py`
2. Update `installer/gui_deploy.py` lines 450-520 (engine detection section)
3. Test: Verify priority-based detection works correctly

**Files to Modify:**
- `installer/gui_deploy.py` (lines 450-520)

---

#### Task 2: Health Score Display in Version Selector (1.5 hours)
**Current:** Version selector shows paths only
**Target:** Add health scores (0-100) like Dashboard's engine source indicator

**Implementation:**
1. Integrate `detect_engine_path.py`'s health scoring into version dialog
2. Add color-coded indicators (green/yellow/orange/red)
3. Use `gui_helpers.show_health_score_indicator()`

**Files to Modify:**
- `installer/gui_deploy.py` (lines 520-580 - version selector dialog)

---

#### Task 3: Version Mismatch Warnings (2 hours)
**Current:** No validation against .uproject version
**Target:** Warn if detected engine version ≠ project's .uproject engine association

**Implementation:**
1. Add .uproject parsing in diagnostics tab
2. Compare project version with selected engine version
3. Show warning banner using `gui_helpers.show_version_mismatch_warning()`

**Files to Modify:**
- `installer/gui_deploy.py` (lines 850-900 - diagnostics checks)

**Test Cases:**
- UE 5.3 project with UE 5.2 engine selected → shows warning
- UE 5.3 project with UE 5.3 engine selected → no warning

---

#### Task 4: SourceManager Integration (3 hours)
**Current:** Writes directly to EngineDirs.txt and ProjectDirs.txt
**Target:** Use `src/utils/source_manager.py` for persistence

**Implementation:**
1. Import SourceManager: `from src.utils.source_manager import SourceManager`
2. Replace direct file writes with SourceManager API calls
3. Update source management tab to use SourceManager methods

**Files to Modify:**
- `installer/gui_deploy.py` (lines 650-750 - source manager tab)

**API Reference:**
```python
from src.utils.source_manager import SourceManager

sm = SourceManager(config_dir=Path("config"))
sm.add_engine_directory(Path("C:/UE_5.3/Engine/Source/Runtime/Core"))
sm.add_project_directory(Path("D:/MyProject/Source"))
sm.save_all()  # Persists to EngineDirs.txt and ProjectDirs.txt
```

---

### Phase C: Unified Dashboard Enhancements (6.5 hours)

**Goal:** Add progress feedback and GPU support to Dashboard

#### Task 5: Progress Bars for Long Operations (2 hours)
**Current:** Log-only feedback for rebuild operations
**Target:** Determinate progress bar like Wizard's installation tab

**Implementation:**
1. Add `ttk.Progressbar` to Maintenance tab
2. Update progress during index rebuild using callbacks
3. Show percentage and time estimate

**Files to Modify:**
- `src/management/gui_dashboard.py` (lines 950-1050 - maintenance tab)

**Code Pattern:**
```python
progress_bar = ttk.Progressbar(frame, mode='determinate', maximum=100)
progress_bar.pack(fill=tk.X, padx=10, pady=5)

def update_progress(current, total):
    percent = (current / total) * 100
    progress_bar['value'] = percent
    root.update_idletasks()
```

---

#### Task 6: Configuration Preview (2.5 hours)
**Current:** "Test Configuration" validates, no preview
**Target:** Show current vs pending config like Wizard's preview area

**Implementation:**
1. Add ScrolledText widget showing config diff
2. Use `gui_helpers.create_dark_theme_text()` for consistent styling
3. Highlight changes (current → new)

**Files to Modify:**
- `src/management/gui_dashboard.py` (lines 750-850 - configuration tab)

**UI Layout:**
```
[Configuration Tab]
├── [Config Fields]
│   ├── API Key: [••••••••]
│   ├── Engine Path: [C:/UE_5.3/Engine]
│   └── Model: [claude-3-haiku-20240307]
├── [Preview Area]
│   └── Current:  ANTHROPIC_MODEL=claude-3-haiku-20240307
│       New:      ANTHROPIC_MODEL=claude-3-5-sonnet-20240307
└── [Save] [Test] [Reload]
```

---

#### Task 7: CUDA Setup Option in Maintenance (2 hours)
**Current:** Assumes CUDA installed during initial deployment
**Target:** Add "Enable GPU Support" button that runs CUDA installer

**Implementation:**
1. Add button to Maintenance tab: "Enable GPU Acceleration"
2. Integrate `src/utils/cuda_installer.py`
3. Show progress dialog during CUDA installation
4. Verify GPU detection after install

**Files to Modify:**
- `src/management/gui_dashboard.py` (lines 950-1050 - maintenance tab)

**Code Pattern:**
```python
def enable_gpu_support(self):
    from src.utils.cuda_installer import install_cuda_support

    if messagebox.askyesno("Enable GPU", "Install CUDA support for 10x faster indexing?"):
        self.show_progress_dialog("Installing CUDA...")
        success = install_cuda_support(progress_callback=self.update_progress)
        if success:
            messagebox.showinfo("Success", "GPU support enabled!")
```

---

## Implementation Roadmap

### Recommended Order

**Day 1 (4 hours):**
1. Task 1: Priority-Based Engine Detection (2h)
2. Task 2: Health Score Display (1.5h)
3. Git commit & push

**Day 2 (4.5 hours):**
1. Task 3: Version Mismatch Warnings (2h)
2. Task 5: Progress Bars (2h)
3. Git commit & push

**Day 3 (6.5 hours):**
1. Task 4: SourceManager Integration (3h)
2. Task 6: Configuration Preview (2.5h)
3. Git commit & push

**Day 4 (2 hours):**
1. Task 7: CUDA Setup Option (2h)
2. Comprehensive testing
3. Final commit & push

---

## Testing Checklist

After each task, verify:

### Deployment Wizard Tests
- [ ] Launch wizard: `python installer/gui_deploy.py`
- [ ] Engine detection shows priority order
- [ ] Version selector shows health scores
- [ ] Version mismatch warning appears for incompatible versions
- [ ] Source manager uses SourceManager API
- [ ] EngineDirs.txt and ProjectDirs.txt persist correctly

### Unified Dashboard Tests
- [ ] Launch dashboard: `python launcher.bat`
- [ ] Progress bar updates during index rebuild
- [ ] Configuration preview shows changes
- [ ] CUDA installer launches and completes
- [ ] GPU detection works after CUDA install

### Integration Tests
- [ ] Both GUIs use shared `gui_helpers` utilities
- [ ] No code duplication between GUIs
- [ ] Consistent theme and styling
- [ ] No regressions from previous functionality

---

## Key Files Reference

### Files You'll Be Modifying

**Deployment Wizard:**
```
installer/gui_deploy.py
├── Lines 450-520:  Engine detection
├── Lines 520-580:  Version selector dialog
├── Lines 650-750:  Source management tab
└── Lines 850-900:  Diagnostics checks
```

**Unified Dashboard:**
```
src/management/gui_dashboard.py
├── Lines 750-850:   Configuration tab
└── Lines 950-1050:  Maintenance tab
```

### Utilities Available

**Shared GUI Helpers:**
```python
from src.utils import gui_helpers

gui_helpers.show_engine_detection_help(parent, browse_callback)
gui_helpers.show_version_mismatch_warning(parent, project_v, engine_v)
gui_helpers.create_dark_theme_text(parent, **kwargs)
gui_helpers.show_health_score_indicator(parent, score)
gui_helpers.validate_engine_path_interactive(parent, path)
```

**Engine Detection:**
```python
from src.utils.engine_helper import get_smart_engine_path
from src.indexing.detect_engine_path import detect_with_health_scores

path = get_smart_engine_path(project_root)
versions = detect_with_health_scores()  # List[(path, version, health)]
```

**Source Manager:**
```python
from src.utils.source_manager import SourceManager

sm = SourceManager(config_dir=Path("config"))
sm.add_engine_directory(path)
sm.add_project_directory(path)
sm.save_all()
```

---

## Success Criteria

All enhancements complete when:

### Deployment Wizard
- ✅ Uses priority-based engine detection
- ✅ Shows health scores in version selector
- ✅ Warns on UE version mismatches
- ✅ Persists sources using SourceManager

### Unified Dashboard
- ✅ Shows progress bars during long operations
- ✅ Previews config changes before saving
- ✅ Can enable GPU support post-install

### Overall System
- ✅ No code duplication between GUIs
- ✅ Consistent UX across both tools
- ✅ All tests pass
- ✅ Documentation updated

---

## Starting the Next Session

When you're ready to continue, just tell Claude:

> "Continue with Phase B from NEXT_SESSION_QUICKSTART.md"

Or to start a specific task:

> "Start with Task 1: Priority-Based Engine Detection from the quick start guide"

---

## Full Implementation Plan

For complete details, see: **C:\Users\posne\.claude\plans\lively-foraging-minsky.md**

This plan includes:
- Detailed implementation steps
- Code examples
- Risk mitigation strategies
- Complete testing checklist
- Success criteria

---

**Current Status:** All prerequisites complete, ready to begin Phase B ✅
