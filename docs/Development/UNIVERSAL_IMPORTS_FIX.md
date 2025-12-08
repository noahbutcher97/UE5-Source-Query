# Universal Imports Fix - December 6, 2025

## Problem Statement

The UE5 Source Query system had context-dependent import paths that worked in the development repository but failed when deployed to project installations:

**Dev Environment** (running from project root):
- Files run from `D:\DevTools\UE5-Source-Query\`
- Imports use absolute paths: `from src.utils.config_manager import ConfigManager`

**Deployed Environment** (running from Scripts/ subdirectory):
- Files run from `D:\UnrealProjects\<project>\Scripts\`
- Imports use relative paths: `from utils.config_manager import ConfigManager`

This caused ModuleNotFoundError when users tried to use the installed system.

## Root Cause

Python import behavior:
1. When script runs from project root, `src/` is in sys.path
2. When script runs from Scripts/ subdirectory, only local directories are in sys.path
3. Hardcoded import paths only worked in one environment

## Solution

Implemented universal try/except import pattern that works in both environments:

```python
# Universal import that works in both dev and deployed environments
try:
    from src.utils.file_utils import atomic_write  # Dev repo (absolute)
except ImportError:
    from utils.file_utils import atomic_write  # Deployed (relative)
```

### Files Modified

**Core Utilities (src/utils/):**
1. `config_manager.py` - ConfigManager class
   - Line 4-8: Universal import for `file_utils.atomic_write`

2. `source_manager.py` - SourceManager class
   - Line 3-7: Universal import for `file_utils.atomic_write`

3. `engine_helper.py` - Engine detection
   - Line 36-39: Universal import for `environment_detector.get_detector`

4. `cli_client.py` - CLI entry point
   - Line 103: Removed redundant import that caused scoping issue
   - Note: HybridQueryEngine already imported at module level (line 13)

**Core Processing (src/core/):**
5. `hybrid_query.py` - Main query engine
   - Line 18-22: Universal import for `utils.config_manager.ConfigManager`

**GUI (src/management/):**
6. `gui_dashboard.py` - Unified Dashboard
   - Line 19-32: Universal imports for all src.utils.* and src.core.* dependencies

**Indexing (src/indexing/):**
7. `build_embeddings.py` - Vector store builder
   - Line 76-79: Universal import for `utils.semantic_chunker.SemanticChunker`

### New Utilities

**src/utils/import_helper.py** - Environment detection and import helpers (NEW)
- `is_dev_environment()`: Detects if running in dev repo vs. deployed package
- `get_import_context()`: Returns 'dev' or 'dist'
- `universal_import()`: Generic import function
- `try_import()`: Convenience function for try/except pattern

Detection logic:
- Dev indicators: .git directory, requirements.txt, Setup.bat, installer/ directory
- Dist indicators: Absence of dev infrastructure

## Testing

### Comprehensive Test Suite

Created `tests/test_universal_imports.py` with 17 tests:

**Test Classes:**
1. `TestUniversalImports` - Tests dev environment imports
2. `TestDistributedEnvironment` - Simulates deployment structure
3. `TestImportHelper` - Tests utility functions
4. `TestIntegration` - Integration tests

**Run Tests:**
```bash
cd D:\DevTools\UE5-Source-Query\tests
..\\.venv\Scripts\python.exe test_universal_imports.py
```

**Results:** All 17 tests passing (verified Dec 6, 2025)

### Manual Testing

**Dev Environment:**
```bash
cd D:\DevTools\UE5-Source-Query
.venv\Scripts\python.exe src\core\hybrid_query.py FHitResult --top-k 1
# ✓ Works - Definition extraction successful
```

**Deployed Environment:**
```bash
cd D:\UnrealProjects\5.3\hijack_prototype\Scripts
.venv\Scripts\python.exe src\utils\cli_client.py FHitResult --top-k 1
# ✓ Works - CLI executes queries successfully
```

## Deployment Impact

### Before Fix:
```
ModuleNotFoundError: No module named 'src'
ModuleNotFoundError: No module named 'utils'
```

### After Fix:
- ✓ Dev repo: All imports work with absolute paths
- ✓ Deployed: All imports work with relative paths
- ✓ Tests: 17/17 passing
- ✓ CLI: Queries execute successfully
- ✓ GUI: Dashboard launches without errors

## Migration Guide

### For Existing Deployments

Re-run deployment wizard to get fixed version:

```bash
cd D:\DevTools\UE5-Source-Query
.venv\Scripts\python.exe installer\gui_deploy.py
# Select target project → Complete installation
```

### For New Features

When adding new cross-module imports, use universal pattern:

```python
# Good - works in both environments
try:
    from src.utils.my_module import MyClass
except ImportError:
    from utils.my_module import MyClass

# Bad - only works in one environment
from src.utils.my_module import MyClass  # Fails in deployment
from utils.my_module import MyClass      # Fails in dev
```

### Import Pattern Decision Tree

1. **Importing from same package** (e.g., file in src/utils/ imports from src/utils/):
   - Use relative imports: `from .my_module import MyClass`
   - OR use universal pattern

2. **Importing across packages** (e.g., src/core/ imports from src/utils/):
   - MUST use universal try/except pattern

3. **Importing standard library or third-party**:
   - Normal import: `import numpy` (no changes needed)

## Future Work

### Possible Improvements

1. **Simplify with import_helper**:
   ```python
   from utils.import_helper import try_import
   ConfigManager = try_import('src.utils.config_manager', 'utils.config_manager', ['ConfigManager'])
   ```

2. **Auto-detection in deployment**:
   - Modify installer to auto-detect import context
   - Generate context-aware wrapper scripts

3. **PEP 420 namespace packages**:
   - Use namespace packages for src/ directory
   - Would allow both import styles simultaneously

## Lessons Learned

1. **Test both environments**: Always test in dev and simulated deployment
2. **Avoid local shadowing**: Don't re-import at function scope if already at module scope
3. **Document import patterns**: New contributors need clear guidelines
4. **Automated testing**: Test suite prevents regressions

## Related Documentation

- **Tests**: `tests/test_universal_imports.py`
- **Import Helper**: `src/utils/import_helper.py`
- **Deployment Guide**: `docs/Production/Deployment/DEPLOYMENT.md`
- **Troubleshooting**: `docs/Production/TROUBLESHOOTING.md`

## Verification Checklist

- [x] All affected files updated with universal imports
- [x] Test suite created (17 tests)
- [x] All tests passing
- [x] Dev environment verified
- [x] Deployed environment verified
- [x] Documentation updated
- [x] Changes committed to dev repo

## Git Commit

```bash
git add src/utils/config_manager.py
git add src/utils/source_manager.py
git add src/utils/engine_helper.py
git add src/utils/cli_client.py
git add src/utils/import_helper.py
git add src/core/hybrid_query.py
git add src/management/gui_dashboard.py
git add src/indexing/build_embeddings.py
git add tests/test_universal_imports.py
git add tests/run_import_tests.bat
git add docs/Development/UNIVERSAL_IMPORTS_FIX.md
git commit -m "fix: Implement universal imports for dev and deployed environments

- Add try/except import pattern to all cross-module imports
- Create import_helper.py with environment detection
- Add comprehensive test suite (17 tests, all passing)
- Fix cli_client.py scoping issue with HybridQueryEngine
- Ensure system works in both dev repo and deployed installations

Resolves: Import errors when running in deployed project installations
Tested: Dev environment and deployed environment both verified working"
```

## Status

**Status**: ✅ COMPLETE (Dec 6, 2025)

**Next Step**: Deploy fixed version to all active project installations using deployment wizard.
