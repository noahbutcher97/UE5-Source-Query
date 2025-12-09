# Import Path Fixes - December 6, 2025

## Issue Summary

The deployment wizard (`installer/gui_deploy.py`) and unified dashboard (`launcher.bat`) were failing with import errors due to inconsistent import path usage throughout the codebase.

### Root Cause

Some utility files were using **relative imports** (`from utils.`) instead of **absolute imports** (`from src.utils.`), which failed when modules were imported from different directory contexts (installer/, tests/, etc.).

## Errors Encountered

### Error 1: Deployment Wizard Import Failure
```
Traceback (most recent call last):
  File "D:\DevTools\UE5-Source-Query\installer\gui_deploy.py", line 23, in <module>
    from src.utils.config_manager import ConfigManager
  File "D:\DevTools\UE5-Source-Query\src\utils\config_manager.py", line 3, in <module>
    from utils.file_utils import atomic_write
ModuleNotFoundError: No module named 'utils'
```

**Cause**: `config_manager.py` used `from utils.file_utils` instead of `from src.utils.file_utils`

### Error 2: Dashboard Theme Attribute Error
```
Traceback (most recent call last):
  File "D:\DevTools\UE5-Source-Query\src\management\gui_dashboard.py", line 165, in build_query_tab
    ttk.Label(filter_row1, text="Entity Type:", font=Theme.FONT).pack(...)
                                                     ^^^^^^^^^^
AttributeError: type object 'Theme' has no attribute 'FONT'
```

**Cause**: Dashboard used `Theme.FONT` but the correct attribute is `Theme.FONT_NORMAL`

## Files Fixed

### Import Path Corrections

**1. `src/utils/config_manager.py:3`**
```python
# Before:
from utils.file_utils import atomic_write

# After:
from src.utils.file_utils import atomic_write
```

**2. `src/utils/source_manager.py:2`**
```python
# Before:
from utils.file_utils import atomic_write

# After:
from src.utils.file_utils import atomic_write
```

**3. `src/core/hybrid_query.py:17`**
```python
# Before:
from utils.config_manager import ConfigManager

# After:
from src.utils.config_manager import ConfigManager
```

**4. `src/utils/engine_helper.py:36`**
```python
# Before:
from utils.environment_detector import get_detector

# After:
from src.utils.environment_detector import get_detector
```

### Theme Attribute Corrections

**5. `src/management/gui_dashboard.py:165, 170, 175`**
```python
# Before:
font=Theme.FONT

# After:
font=Theme.FONT_NORMAL
```

## Testing Improvements

### Created: `tests/test_gui_smoke.py`

Comprehensive GUI smoke tests that verify both:
1. **Import correctness** - All modules can be imported
2. **Initialization correctness** - GUI classes can be instantiated

**Key Enhancement**: Added instantiation tests that actually create hidden Tk windows and instantiate GUI classes:

```python
def test_dashboard_initialization(self):
    """Test that dashboard can be instantiated without crashing"""
    root = tk.Tk()
    root.withdraw()  # Hide window

    from src.management.gui_dashboard import UnifiedDashboard
    dashboard = UnifiedDashboard(root)

    self.assertIsNotNone(dashboard)
    root.destroy()
```

**Why This Matters**:
- Original smoke tests only tested imports
- Theme.FONT error occurred during `__init__()` → `create_layout()`
- New instantiation tests catch these runtime initialization errors

### Test Coverage

**Total GUI Smoke Tests: 17**

| Test Class | Tests | Purpose |
|------------|-------|---------|
| `TestDeploymentWizardImports` | 3 | Import, dependencies, instantiation |
| `TestDashboardImports` | 3 | Import, dependencies, instantiation |
| `TestGUITheme` | 1 | Theme attributes |
| `TestUtilityModules` | 5 | Utility imports |
| `TestCoreModules` | 3 | Core imports |
| `TestBatchScripts` | 3 | Batch file existence |

### Test Results

```
Ran 17 tests in 4.418s

OK
```

All tests now pass, including the new instantiation tests.

## Import Strategy Standardized

### Guidelines

**All cross-module imports use absolute paths:**
- ✅ `from src.utils.config_manager import ConfigManager`
- ✅ `from src.core.hybrid_query import HybridQueryEngine`
- ✅ `from src.utils.environment_detector import get_detector`

**Scripts add project root to sys.path:**
```python
SCRIPT_DIR = Path(__file__).parent.parent
sys.path.append(str(SCRIPT_DIR))
```

**This works consistently from:**
- `installer/gui_deploy.py`
- `src/management/gui_dashboard.py`
- `tests/test_*.py`
- Direct script execution

## Verification Steps

### 1. Deployment Wizard
```bash
python installer/gui_deploy.py
# Should launch without import errors
```

### 2. Unified Dashboard
```bash
launcher.bat
# OR: python src/management/gui_dashboard.py
# Should launch without attribute errors
```

### 3. Setup Script
```bash
Setup.bat
# Should launch deployment wizard successfully
```

### 4. All Tests
```bash
tools\run-tests.bat
# Should run all 40 tests (including 17 GUI smoke tests)
```

### 5. GUI Smoke Tests Only
```bash
python tests/test_gui_smoke.py
# Should run 17 tests, all passing
```

## Lessons Learned

### 1. Consistent Import Paths
**Problem**: Mixing relative and absolute imports causes failures in different contexts

**Solution**: Always use absolute imports for cross-module dependencies

### 2. Test Initialization, Not Just Imports
**Problem**: Import tests don't catch runtime initialization errors

**Solution**: Smoke tests should instantiate classes (with hidden windows for GUI)

### 3. Theme Attribute Naming
**Problem**: Incorrect attribute names fail at runtime, not at import

**Solution**: Instantiation tests catch these during automated testing

## Future Prevention

### Pre-Commit Checklist

Before committing code changes:
1. ✅ Run `tools\run-tests.bat` - all tests must pass
2. ✅ Run `python tests/test_gui_smoke.py` - verify GUI can initialize
3. ✅ Test launch scripts manually:
   - `Setup.bat`
   - `launcher.bat`
   - `installer/gui_deploy.py`

### Code Review Guidelines

When adding new utility modules:
- ✅ Use absolute imports: `from src.utils.` not `from utils.`
- ✅ Add smoke test for new GUI components
- ✅ Verify theme attributes match `gui_theme.py` definitions

### CI/CD Integration (Future)

Consider adding GitHub Actions workflow:
```yaml
- name: Run GUI Smoke Tests
  run: python tests/test_gui_smoke.py

- name: Test Deployment Wizard
  run: python installer/gui_deploy.py --help

- name: Test Dashboard
  run: python src/management/gui_dashboard.py --help
```

## Summary

✅ **Fixed 5 files** with import/attribute errors
✅ **Created comprehensive GUI smoke tests** (17 tests)
✅ **Standardized import strategy** across all modules
✅ **Verified all launch scripts work** (Setup.bat, launcher.bat)
✅ **Documented prevention strategies** for future development

**Result**: Both deployment wizard and unified dashboard now launch successfully without errors.

---

*Last Updated: 2025-12-06*
*Issue: Import path inconsistencies*
*Resolution: Absolute imports + enhanced smoke tests*
