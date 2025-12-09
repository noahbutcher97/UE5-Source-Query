# Testing Guide

**UE5 Source Query Tool - Comprehensive Testing Documentation**

---

## Overview

This guide covers all aspects of testing for the UE5 Source Query Tool, including unit tests, integration tests, GUI testing procedures, and continuous validation strategies.

---

## Test Structure

```
tests/
├── __init__.py
├── run_tests.py                      # Main test runner
├── test_environment_detector.py      # Phase 6 detection tests
├── test_engine_helper.py             # Integration tests
├── test_gui_smoke.py                 # GUI import/initialization tests
├── test_version_matching.py          # Version normalization tests
├── validate_gui_launch.py            # Quick GUI validation script
└── (future test files)
```

---

## Running Tests

### Quick Start

```bash
# Run all tests (easiest method)
tools\run-tests.bat

# Run all tests with Python
python tests\run_tests.py

# Run with verbose output
python tests\run_tests.py -v 2

# Run with quiet output (failures only)
python tests\run_tests.py -v 0
```

### Running Specific Tests

```bash
# Run specific test module
python tests\run_tests.py -m test_environment_detector

# Run specific test class
python tests\run_tests.py -m test_environment_detector -c TestEnvVarStrategy

# Run specific test method
python tests\run_tests.py -m test_environment_detector -c TestEnvVarStrategy -t test_detect_with_ue5_engine_path

# List all available tests
python tests\run_tests.py --list
```

### Direct Test Execution

```bash
# Run test file directly
python tests\test_environment_detector.py

# Run with unittest discovery
python -m unittest discover -s tests -p "test_*.py"
```

---

## Test Coverage

### Unit Tests

**`test_environment_detector.py`** (Phase 6)

Covers all detection strategies and validation:

| Test Class | Focus | Tests |
|------------|-------|-------|
| `TestEnvVarStrategy` | Environment variable detection | 6 tests |
| `TestConfigFileStrategy` | .ue5query config files | 4 tests |
| `TestValidationPipeline` | Installation validation | 3 tests |
| `TestEnvironmentDetector` | Main orchestrator | 3 tests |
| `TestGetDetectorFactory` | Factory function | 2 tests |

**Total: ~18 unit tests**

**Test Scenarios:**
- ✅ UE5_ENGINE_PATH detection
- ✅ UE_ROOT detection
- ✅ Parent directory detection
- ✅ JSON config file loading
- ✅ Malformed config handling
- ✅ Validation of perfect installations
- ✅ Validation with missing directories
- ✅ Non-existent path handling
- ✅ Result deduplication
- ✅ Cache save/load
- ✅ Cache expiration (24hr)
- ✅ Strategy merging

### Integration Tests

**`test_engine_helper.py`**

Tests integration between components:

| Test Class | Focus | Tests |
|------------|-------|-------|
| `TestGetAvailableEngines` | Detection integration | 4 tests |
| `TestResolveUprojectSource` | Project resolution | 3 tests |

**Total: ~7 integration tests**

**Test Scenarios:**
- ✅ Dict format return structure
- ✅ Cache usage by default
- ✅ Cache disabling
- ✅ Graceful error handling
- ✅ Project source directory resolution
- ✅ Missing source handling

### GUI Smoke Tests

**`test_gui_smoke.py`**

Tests that GUI applications can initialize without crashing:

| Test Class | Focus | Tests |
|------------|-------|-------|
| `TestDeploymentWizardImports` | Deployment wizard import & init | 3 tests |
| `TestDashboardImports` | Dashboard import & init | 3 tests |
| `TestGUITheme` | Theme attributes & methods | 5 tests |
| `TestGUIComponents` | Critical GUI widgets | 3 tests |
| `TestGUIDialogs` | Dialog methods exist | 2 tests |
| `TestUtilityModules` | All utility modules import | 4 tests |
| `TestCoreModules` | Core query modules import | 3 tests |
| `TestBatchScripts` | Batch files exist & valid | 5 tests |

**Total: 28 GUI smoke tests**

**Test Scenarios:**
- ✅ Deployment wizard imports without errors
- ✅ Deployment wizard can be instantiated
- ✅ All deployment dependencies available
- ✅ Dashboard imports without errors
- ✅ Dashboard can be instantiated
- ✅ All dashboard dependencies available
- ✅ Theme class has all required color attributes
- ✅ Theme class has all required font attributes
- ✅ Theme.apply() works without errors
- ✅ Theme.create_header() works without errors
- ✅ ScrolledText widgets can be created
- ✅ Notebook (tabs) widgets can be created
- ✅ Dashboard creates all 5 tabs
- ✅ Dashboard has help dialog method
- ✅ Deployment wizard has help dialog method
- ✅ ConfigManager can be instantiated
- ✅ SourceManager can be instantiated
- ✅ Engine helper functions available
- ✅ GPU helper functions available
- ✅ HybridQueryEngine imports correctly
- ✅ Query intent analyzer available
- ✅ Definition extractor available
- ✅ launcher.bat exists and references correct file
- ✅ Setup.bat exists and references correct file
- ✅ run-tests.bat exists

**What These Tests Catch:**
1. **Import Errors**: Missing dependencies, incorrect import paths
2. **Initialization Errors**: Theme attribute errors, missing methods
3. **Widget Creation Errors**: Tkinter/ttk components fail to create
4. **Method Existence**: Critical GUI methods exist and are callable
5. **Batch Script Errors**: Scripts point to wrong files or missing

### Version Matching Tests

**`test_version_matching.py`**

Tests version normalization and comparison logic:

| Test Class | Focus | Tests |
|------------|-------|-------|
| `TestVersionMatching` | Version parsing and comparison | 6 tests |
| `TestVersionDisplay` | Display truncation handling | 1 test |

**Total: 8 version matching tests**

**Test Scenarios:**
- ✅ Full version normalization (5.3.2 → (5, 3, 2))
- ✅ Partial version normalization (5.3 → (5, 3, 0))
- ✅ Invalid version handling
- ✅ Identical version matching (5.3.2 == 5.3.2)
- ✅ Patch difference matching (5.3 == 5.3.2, 5.3.0 == 5.3.2)
- ✅ Minor version mismatch detection (5.3 != 5.4)
- ✅ Major version mismatch detection (4.27 != 5.27)
- ✅ Truncated display versions (5.3 shown, 5.3.2 actual)

**What This Prevents:**
- False "version mismatch" warnings when displaying truncated versions
- Confusion between 5.3, 5.3.0, and 5.3.2 (all treated as compatible)
- Actual version mismatches (5.3 vs 5.4) are still detected

---

## Test Categories

### 1. Detection Strategy Tests

**Purpose:** Verify each detection strategy works correctly

**Covered Strategies:**
- Environment variables (UE5_ENGINE_PATH, UE_ROOT, etc.)
- Config files (.ue5query JSON)
- Windows Registry (Epic Games Launcher)
- Common install locations

**Test Patterns:**
```python
def test_detect_with_[strategy](self):
    # Setup test environment
    # Run detection
    # Assert expected results
    # Cleanup
```

### 2. Validation Tests

**Purpose:** Ensure validation pipeline correctly assesses installations

**Test Cases:**
- Perfect installations (100% health)
- Partial installations (missing directories)
- Invalid paths
- Missing critical files

**Health Score Ranges:**
- 100% - All checks passed
- 70-99% - Minor issues (warnings)
- <70% - Significant issues

### 3. Caching Tests

**Purpose:** Verify cache system works correctly

**Test Cases:**
- Cache save
- Cache load
- Cache expiration (24hr TTL)
- Cache invalidation

### 4. Integration Tests

**Purpose:** Verify components work together correctly

**Test Cases:**
- engine_helper → environment_detector integration
- Legacy fallback mechanism
- Return format compatibility
- Error propagation

---

## GUI Testing

### Manual GUI Testing Procedures

**Since GUI testing is difficult to automate, follow these manual procedures:**

#### Test Checklist: Deployment Wizard (`installer/gui_deploy.py`)

**Phase 6 Integration:**
- [ ] Auto-detect button shows health scores
- [ ] Multiple engines show in selector with health info
- [ ] Low-health engines show warnings
- [ ] Failed detection shows help dialog
- [ ] Help dialog has correct content
- [ ] Browse manually works after help dialog
- [ ] Detection logs show source and health

**Visual Consistency:**
- [ ] Uses same Theme as Dashboard
- [ ] Dialog sizes match Dashboard (600x400 for selector, 700x500 for help)
- [ ] Button styles consistent (Accent.TButton)
- [ ] Font styles match (Theme.FONT_BOLD, Theme.FONT_NORMAL, Theme.FONT_SMALL)
- [ ] Colors consistent
- [ ] Layout structure similar

#### Test Checklist: Unified Dashboard (`src/management/gui_dashboard.py`)

**Phase 6 Integration:**
- [ ] Auto-detect button in Source Manager
- [ ] Health scores displayed correctly
- [ ] Warnings shown for low-health engines
- [ ] Help dialog appears when no engines found
- [ ] Selection dialog shows health/source info
- [ ] Path label updates with selected health info

**Tab Functionality:**
- [ ] Query tab works
- [ ] Source Manager tab works
- [ ] Maintenance tab works
- [ ] Diagnostics tab works

### GUI Test Scenarios

**Scenario 1: Perfect Detection**
1. Set UE5_ENGINE_PATH environment variable
2. Launch deployment wizard
3. Click Auto-Detect
4. Verify: Single engine detected with 100% health
5. Verify: Engine path auto-populated

**Scenario 2: Multiple Engines**
1. Install multiple UE5 versions
2. Launch deployment wizard
3. Click Auto-Detect
4. Verify: Selection dialog shows multiple engines
5. Verify: Health scores visible
6. Verify: Source info visible
7. Select engine
8. Verify: Correct path populated

**Scenario 3: No Detection**
1. Remove all environment variables
2. Remove .ue5query files
3. Launch deployment wizard
4. Click Auto-Detect
5. Verify: Help dialog appears
6. Verify: Help text correct
7. Click Browse Manually
8. Verify: File browser opens

**Scenario 4: Low-Health Engine**
1. Create partial UE5 installation (missing directories)
2. Point environment variable to it
3. Launch deployment wizard
4. Click Auto-Detect
5. Verify: Engine detected with low health score (<70%)
6. Verify: Warnings displayed in log

---

## Continuous Testing Strategy

### Pre-Commit Testing

Before committing code:

```bash
# Run all tests
tools\run-tests.bat

# If tests pass, commit
git add .
git commit -m "Your message"
```

### Pre-Phase Testing

Before starting a new phase:

```bash
# Run full test suite
python tests\run_tests.py -v 2

# Check existing functionality
# Run manual GUI tests (see checklist above)
```

### Post-Phase Testing

After completing a phase:

```bash
# Add new tests for phase features
# Run full test suite
python tests\run_tests.py -v 2

# Run regression tests (all previous phase features)
# Update this document with new test coverage
```

---

## Writing New Tests

### Test Template

```python
import unittest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.your_module import YourClass


class TestYourFeature(unittest.TestCase):
    """Test your new feature"""

    def setUp(self):
        """Setup before each test"""
        # Create temp directories, mock objects, etc.
        pass

    def tearDown(self):
        """Cleanup after each test"""
        # Remove temp files, reset state, etc.
        pass

    def test_basic_functionality(self):
        """Test that basic functionality works"""
        # Arrange
        # Act
        result = YourClass.do_something()
        # Assert
        self.assertEqual(result, expected)

    def test_error_handling(self):
        """Test that errors are handled gracefully"""
        with self.assertRaises(ExpectedException):
            YourClass.do_something_invalid()


if __name__ == "__main__":
    unittest.main()
```

### Test Naming Conventions

**Files:** `test_<module_name>.py`
- Example: `test_environment_detector.py`

**Classes:** `Test<FeatureName>`
- Example: `TestEnvVarStrategy`

**Methods:** `test_<what_it_tests>`
- Example: `test_detect_with_ue5_engine_path`

### Test Organization

```python
class TestFeature(unittest.TestCase):
    # 1. Setup/Teardown
    def setUp(self): ...
    def tearDown(self): ...

    # 2. Happy path tests (normal usage)
    def test_normal_case(self): ...

    # 3. Edge cases
    def test_edge_case(self): ...

    # 4. Error handling
    def test_error_handling(self): ...
```

---

## Test Best Practices

### DO:
- ✅ Test one thing per test method
- ✅ Use descriptive test names
- ✅ Clean up after tests (tearDown)
- ✅ Use assertions appropriately
- ✅ Test both success and failure cases
- ✅ Mock external dependencies
- ✅ Use temporary directories for file operations

### DON'T:
- ❌ Test multiple things in one test
- ❌ Leave test artifacts (files, env vars)
- ❌ Depend on test execution order
- ❌ Use real external services
- ❌ Hard-code paths
- ❌ Skip cleanup on test failure

---

## Mocking Guidelines

### When to Mock

**Mock external dependencies:**
- File system operations (when testing logic, not I/O)
- Network requests
- User input (GUI dialogs)
- System calls
- Time-dependent operations

**Don't mock:**
- Simple data structures
- Internal project code (test it directly)
- Trivial operations

### Mock Example

```python
from unittest.mock import Mock, patch, MagicMock

@patch('src.utils.environment_detector.RegistryStrategy.detect')
def test_with_mock(self, mock_detect):
    """Test using mocked detection"""
    # Setup mock return value
    mock_detect.return_value = [mock_installation]

    # Run code under test
    result = detector.detect_engines()

    # Verify mock was called
    mock_detect.assert_called_once()

    # Verify result
    self.assertEqual(len(result), 1)
```

---

## Debugging Failed Tests

### Getting More Information

```bash
# Run with maximum verbosity
python tests\run_tests.py -v 2

# Run specific failing test
python tests\run_tests.py -m test_module -c TestClass -t test_method

# Add print statements in test
def test_something(self):
    print(f"Debug: value={value}")
    self.assertEqual(value, expected)
```

### Common Issues

**Issue:** `ImportError: No module named 'src'`
**Fix:** Ensure `sys.path.insert(0, ...)` is at top of test file

**Issue:** `PermissionError` on file cleanup
**Fix:** Use `shutil.rmtree(..., ignore_errors=True)`

**Issue:** Tests pass individually but fail together
**Fix:** Check for shared state, ensure proper cleanup in `tearDown()`

**Issue:** Temp directory not cleaned up
**Fix:** Use `tempfile.TemporaryDirectory()` context manager

---

## Performance Testing

### Timing Tests

```python
import time

def test_detection_performance(self):
    """Verify detection is fast enough"""
    start = time.time()
    result = detector.detect_engines(use_cache=True)
    elapsed = time.time() - start

    # Cached detection should be instant
    self.assertLess(elapsed, 0.1)  # < 100ms
```

### Expected Performance

| Operation | Expected Time |
|-----------|---------------|
| Cached detection | < 0.01s |
| Environment variable detection | < 0.01s |
| Config file detection | < 0.05s |
| Windows Registry detection | 0.1-0.3s |
| Common location scan | 0.5-2.0s |
| Full detection + validation | 1-3s |

---

## CI/CD Integration

### GitHub Actions (Future)

```yaml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: python tests/run_tests.py -v 2
```

### Pre-Push Hook (Optional)

Create `.git/hooks/pre-push`:

```bash
#!/bin/bash
echo "Running tests before push..."
python tests/run_tests.py -v 1
if [ $? -ne 0 ]; then
    echo "Tests failed. Push aborted."
    exit 1
fi
```

---

## Test Metrics

### Current Coverage

**Phase 6 (Environment Detection):**
- Unit tests: 18 tests (environment_detector)
- Integration tests: 7 tests (engine_helper)
- GUI smoke tests: 28 tests (gui_smoke)
- Version matching: 8 tests (version_matching)
- Manual GUI tests: Checklist in guide
- Total automated: 61 tests

**Success Rate:** Target 100% passing

### Future Coverage Goals

- Phase 7: Add tests for advanced filtering
- Phase 8: Add tests for relationship viewer
- Phase 9: Add cross-platform tests
- Target: 80%+ code coverage for core modules

---

## Troubleshooting Tests

### Test Environment Issues

**Virtual Environment:**
```bash
# Ensure venv is activated
.venv\Scripts\activate

# Verify Python version
python --version  # Should be 3.8+

# Verify packages installed
pip list
```

**Path Issues:**
```python
# Add this at top of test file
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

**Windows-Specific:**
```python
# Use Path for cross-platform compatibility
from pathlib import Path

# Use forward slashes in strings
path = "C:/Path/To/Engine"  # Good
path = "C:\\Path\\To\\Engine"  # Also good, but needs escaping
```

---

## Getting Help

**Test Failures:**
1. Read the test output carefully
2. Check the test documentation (this file)
3. Look at similar passing tests
4. Add debug print statements
5. Run test in isolation

**Writing New Tests:**
1. Look at existing test files for patterns
2. Follow the test template above
3. Start simple, add complexity gradually
4. Run tests frequently during development

---

## Summary

✅ **Test Framework:** Complete with runner and automated tests
✅ **Unit Tests:** 18 tests for Phase 6 detection
✅ **Integration Tests:** 7 tests for component integration
✅ **GUI Tests:** Manual procedures documented
✅ **Documentation:** Comprehensive guide (this file)

**Next Steps:**
1. Run tests before each commit
2. Add tests for new features
3. Maintain high test coverage
4. Keep this document updated

---

*Last Updated: 2025-12-03*
*For: Development Team*
*Coverage: Phases 1-6*
