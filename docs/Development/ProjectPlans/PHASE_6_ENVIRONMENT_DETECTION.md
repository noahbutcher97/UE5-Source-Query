# Phase 6: Environment Detection - Comprehensive Plan

**Status:** Planning (Ready for Next Session)
**Estimated Effort:** 3-4 hours
**Priority:** High (Improves user experience significantly)
**Date Created:** 2025-12-02

---

## Session Handoff - Start Here!

**Previous Phase Completed:** Phase 5 - Relationship Extraction ✅
**Current Phase:** Phase 6 - Environment Detection
**Next Phase:** TBD (suggest after Phase 6 completion)

**What You Need to Know:**
- All previous phases (1-5) are complete and committed
- Documentation has been cleaned up (outdated files archived)
- Current detection is basic and needs vast expansion
- This phase focuses on hardening and expanding environment auto-detection

---

## Overview

Vastly expand and harden the environment and project detection mechanisms to make the system more robust, flexible, and user-friendly across different installation configurations.

### Current State (Before Phase 6)

**What Exists:**
- `src/indexing/detect_engine_path.py` (outdated, weeks old)
- `src/utils/engine_helper.py` (active, minimal detection)
- `src/utils/config_manager.py` (basic config file management)
- `src/utils/source_manager.py` (manages EngineDirs.txt and ProjectDirs.txt)
- GUI auto-detection in `src/management/gui_dashboard.py`

**Current Detection Capabilities:**
1. **UE5 Engine Detection:**
   - Windows Registry lookup (Epic Games Launcher installs)
   - Common install locations (C:, D:, E: drives)
   - Manual path entry as fallback

2. **Project Detection:**
   - .uproject file selection
   - Source directory resolution from .uproject

**Current Limitations:**
- ❌ No detection of custom UE5 builds (from source)
- ❌ No detection of multiple engine versions simultaneously
- ❌ No automatic project discovery in workspace
- ❌ No validation of detected paths
- ❌ No fallback strategies when detection fails
- ❌ No environment variable support
- ❌ No .ue5query config file support
- ❌ Limited error messages and recovery guidance

---

## Goals

### Primary Goals
1. **Robust UE5 Detection**: Find engines in ANY valid location
2. **Multi-Version Support**: Handle multiple UE5 versions gracefully
3. **Project Auto-Discovery**: Find projects automatically
4. **Smart Validation**: Verify detected paths are actually valid
5. **Better Error Recovery**: Guide users when detection fails

### Secondary Goals
6. **Environment Variables**: Support UE_ROOT, UE5_ENGINE_PATH, etc.
7. **Config File Support**: .ue5query file in project/user directories
8. **Custom Build Detection**: Find source-built engines
9. **Workspace Integration**: Detect multi-project workspaces
10. **Cross-Platform Prep**: Lay groundwork for Linux/Mac (future)

---

## Current Detection Flow Analysis

### File: `src/utils/engine_helper.py`
**Current Implementation:**
```python
def get_available_engines(script_dir: Path):
    """Calls detect_engine_path.py --json"""
    detect_script = script_dir / "src" / "indexing" / "detect_engine_path.py"
    result = subprocess.run([sys.executable, str(detect_script), "--json"], ...)
    return json.loads(result.stdout)
```

**Issues:**
- Relies on outdated `detect_engine_path.py`
- No direct validation
- No caching of detection results
- No fallback strategies

### File: `src/indexing/detect_engine_path.py`
**Status:** OUTDATED (weeks old)
**Functions:**
- `detect_from_registry()` - Windows registry lookup
- `detect_from_common_locations()` - Hard-coded search paths
- `validate_engine_path()` - Basic validation
- `get_engine_path_interactive()` - CLI wizard

**Issues:**
- Hard-coded search paths (C:, D:, E: only)
- No environment variable support
- No config file support
- Interactive mode not suitable for API use

### File: `src/management/gui_dashboard.py`
**Current Auto-Detection:**
```python
def auto_detect_path(self):
    installations = get_available_engines(self.script_dir)
    # Shows selection dialog if multiple found
```

**Issues:**
- No validation feedback
- No recovery guidance
- No caching

---

## Technical Design

### New Architecture

```
┌─────────────────────────────────────────────────┐
│         EnvironmentDetector (New)              │
├─────────────────────────────────────────────────┤
│  - Multi-strategy detection                    │
│  - Result caching                               │
│  - Validation pipeline                          │
│  - Error recovery guidance                      │
└─────────────────────────────────────────────────┘
           │
           ├──> UE5EngineDetector
           │    ├─ Registry Detection
           │    ├─ Environment Variables
           │    ├─ Common Locations
           │    ├─ Config Files (.ue5query)
           │    └─ Custom Build Detection
           │
           ├──> ProjectDetector
           │    ├─ Workspace Scanning
           │    ├─ .uproject Discovery
           │    └─ Source Directory Resolution
           │
           └──> ValidationPipeline
                ├─ Path Existence Checks
                ├─ Directory Structure Validation
                ├─ Version Detection
                └─ Health Checks
```

### Detection Priority Order

**UE5 Engine Detection (Waterfall):**
1. Environment variables (`UE5_ENGINE_PATH`, `UE_ROOT`)
2. Config file (`.ue5query` in project root)
3. Config file (`.ue5query` in user home)
4. Windows Registry (Epic Games Launcher)
5. Common install locations
6. Recursive search in common roots
7. Manual entry (last resort)

**Project Detection (Parallel):**
1. Current working directory (check for .uproject)
2. Parent directories (walk up to find .uproject)
3. Workspace scan (find all .uproject in tree)
4. Manual selection

---

## Implementation Plan

### Step 1: Create `environment_detector.py` (2-3 hours)

**File:** `src/utils/environment_detector.py` (~500 lines)

**Core Classes:**

```python
class DetectionStrategy(ABC):
    """Base class for detection strategies"""
    @abstractmethod
    def detect(self) -> List[EngineInstallation]:
        pass

class EngineInstallation:
    """Represents a detected UE5 installation"""
    version: str
    engine_root: Path
    source: str  # "registry", "envvar", "config", etc.
    validated: bool
    health_score: float

class EnvironmentDetector:
    """Main detection orchestrator"""
    def __init__(self, config_manager: ConfigManager):
        self.strategies = [
            EnvVarStrategy(),
            ConfigFileStrategy(),
            RegistryStrategy(),
            CommonLocStrategy(),
            RecursiveSearchStrategy()
        ]
        self.cache = {}

    def detect_engines(self, use_cache=True) -> List[EngineInstallation]:
        """Run all strategies and merge results"""

    def detect_projects(self, search_root: Path = None) -> List[ProjectInfo]:
        """Find .uproject files"""

    def validate_installation(self, install: EngineInstallation) -> ValidationResult:
        """Validate engine installation"""
```

**Detection Strategies:**

```python
class EnvVarStrategy(DetectionStrategy):
    """Check UE5_ENGINE_PATH, UE_ROOT, UNREAL_ENGINE_PATH"""
    ENV_VARS = ["UE5_ENGINE_PATH", "UE_ROOT", "UNREAL_ENGINE_PATH", "UE5_ROOT"]

class ConfigFileStrategy(DetectionStrategy):
    """Check .ue5query in project root and ~/ """
    def find_config_files(self) -> List[Path]:
        locations = [
            Path.cwd() / ".ue5query",
            Path.home() / ".ue5query",
            Path.cwd().parent / ".ue5query"  # Parent dir
        ]
        return [f for f in locations if f.exists()]

class RegistryStrategy(DetectionStrategy):
    """Windows Registry lookup (existing logic)"""

class CommonLocStrategy(DetectionStrategy):
    """Search common install locations"""
    COMMON_ROOTS = [
        "C:/Program Files/Epic Games",
        "D:/Program Files/Epic Games",
        "E:/Program Files/Epic Games",
        "C:/Epic Games",
        "D:/Epic Games",
        "C:/UnrealEngine",
        "D:/UnrealEngine",
        # Add all lettered drives A-Z
        *[f"{chr(65+i)}:/Epic Games" for i in range(26)],
        *[f"{chr(65+i)}:/UnrealEngine" for i in range(26)]
    ]

class RecursiveSearchStrategy(DetectionStrategy):
    """Deep search in common roots (slow, last resort)"""
    def search_for_engine(self, root: Path, max_depth=3) -> List[Path]:
        # Find directories matching UE_* pattern
        # Validate each as potential engine root
```

**Validation Pipeline:**

```python
class ValidationPipeline:
    """Validate detected installations"""

    def validate(self, install: EngineInstallation) -> ValidationResult:
        checks = [
            self.check_path_exists,
            self.check_directory_structure,
            self.check_build_version,
            self.check_source_availability
        ]

        results = [check(install) for check in checks]
        return ValidationResult(
            valid=all(r.passed for r in results),
            health_score=sum(r.score for r in results) / len(results),
            issues=[r.issue for r in results if not r.passed],
            warnings=[r.warning for r in results if r.warning]
        )

    def check_directory_structure(self, install) -> CheckResult:
        """Verify Engine/Source, Engine/Plugins, Engine/Build exist"""

    def check_build_version(self, install) -> CheckResult:
        """Parse Build.version or other version files"""
```

### Step 2: Implement .ue5query Config File Support (30 min)

**Format:** YAML or JSON

**Example `.ue5query` file:**
```yaml
engine:
  path: "C:/UnrealEngine/UE_5.3/Engine"
  version: "5.3.2"

project:
  root: "D:/Projects/MyGame"
  source_dirs:
    - "Source/MyGame"
    - "Plugins/MyPlugin/Source"

preferences:
  auto_rebuild_index: false
  default_scope: "all"
```

**Implementation:**
```python
class ConfigFileStrategy:
    def load_config(self, config_path: Path) -> Dict:
        if config_path.suffix == '.json':
            return json.loads(config_path.read_text())
        elif config_path.suffix in ['.yaml', '.yml']:
            return yaml.safe_load(config_path.read_text())
        else:
            # Try both formats
            try:
                return json.loads(config_path.read_text())
            except:
                return yaml.safe_load(config_path.read_text())
```

### Step 3: Integrate with Existing Code (30 min)

**Modify `src/utils/engine_helper.py`:**
```python
def get_available_engines(script_dir: Path):
    """New implementation using EnvironmentDetector"""
    from utils.environment_detector import EnvironmentDetector
    from utils.config_manager import ConfigManager

    config_mgr = ConfigManager(script_dir)
    detector = EnvironmentDetector(config_mgr)

    installations = detector.detect_engines(use_cache=True)

    # Convert to old format for compatibility
    return [
        {
            "version": inst.version,
            "engine_root": str(inst.engine_root),
            "path": str(inst.engine_root.parent),
            "source": inst.source,
            "validated": inst.validated,
            "health_score": inst.health_score
        }
        for inst in installations
    ]
```

**Modify GUI Dashboard:**
```python
def auto_detect_path(self):
    """Enhanced with validation feedback"""
    installations = get_available_engines(self.script_dir)

    if not installations:
        self.show_detection_help_dialog()
        return

    # Sort by health score
    installations.sort(key=lambda x: x.get('health_score', 0), reverse=True)

    # Show validation status
    for inst in installations:
        self.log_config(f"Found: {inst['version']} (health: {inst['health_score']:.0%})")
```

### Step 4: Add Detection Help System (30 min)

**Help Dialog:**
```python
def show_detection_help_dialog(self):
    """Guide user through manual setup"""
    dialog = tk.Toplevel(self.root)
    dialog.title("UE5 Engine Not Found")

    help_text = """
    No UE5 installation detected automatically.

    To help us find your engine:

    1. Set environment variable:
       - UE5_ENGINE_PATH=C:\\Path\\To\\UE_5.3\\Engine

    2. Create .ue5query file in project root:
       engine:
         path: "C:/Path/To/UE_5.3/Engine"

    3. Ensure engine is in common location:
       - C:\\Program Files\\Epic Games\\UE_5.X
       - D:\\Epic Games\\UE_5.X

    4. Or browse manually below:
    """

    ttk.Label(dialog, text=help_text, justify=tk.LEFT).pack(padx=20, pady=10)
    ttk.Button(dialog, text="Browse Manually", command=self.browse_engine_path).pack()
```

### Step 5: Add Caching (15 min)

**Cache Format:**
```json
{
  "last_scan": "2025-12-02T10:30:00Z",
  "engines": [
    {
      "version": "5.3.2",
      "engine_root": "C:/Program Files/Epic Games/UE_5.3/Engine",
      "source": "registry",
      "last_validated": "2025-12-02T10:30:00Z",
      "health_score": 1.0
    }
  ]
}
```

**Cache Location:** `config/detection_cache.json`

**Cache Invalidation:**
- Age > 24 hours
- Manual refresh requested
- Config file changed

### Step 6: Testing (1 hour)

**Test Scenarios:**
1. **Registry Detection:** Verify Epic Games Launcher installs found
2. **Environment Variable:** Set UE5_ENGINE_PATH and verify detection
3. **Config File:** Create .ue5query and verify priority
4. **Custom Build:** Test with source-built engine
5. **Multiple Versions:** Install UE 5.2, 5.3, 5.4 and verify all detected
6. **Validation:** Test with invalid path, partial install, etc.
7. **Performance:** Measure detection time with/without cache

---

## Files to Create/Modify

### New Files
1. `src/utils/environment_detector.py` (~500 lines)
   - EnvironmentDetector class
   - Detection strategies
   - Validation pipeline

2. `tests/test_environment_detector.py` (~200 lines)
   - Unit tests for each strategy
   - Integration tests

3. `.ue5query.example` (example config file)

### Modified Files
1. `src/utils/engine_helper.py` (~30 lines modified)
   - Use new EnvironmentDetector

2. `src/management/gui_dashboard.py` (~50 lines added)
   - Enhanced auto-detection feedback
   - Help dialog for failed detection

3. `src/utils/config_manager.py` (~20 lines added)
   - Cache management methods

4. `docs/AI_AGENT_GUIDE.md` (~30 lines added)
   - Document .ue5query file format
   - Document environment variables

5. `README.md` (~20 lines added)
   - Quick setup with environment variables

---

## Success Criteria

### Minimum Viable Product (MVP)
- ✅ Environment variable detection works
- ✅ .ue5query config file support
- ✅ Enhanced validation with health scores
- ✅ Detection caching (24hr TTL)
- ✅ Better error messages

### Full Feature Set
- ✅ All detection strategies implemented
- ✅ Multi-version support
- ✅ Project auto-discovery
- ✅ Validation pipeline complete
- ✅ Help dialog for failed detection
- ✅ Performance < 1 second (cached)

### Stretch Goals
- Cross-platform detection (Linux/Mac prep)
- Detection of engine plugins
- Build configuration detection (Debug/Development/Shipping)

---

## Risk Mitigation

### Risk 1: Performance Impact
**Problem:** Recursive search could be slow on large drives
**Mitigation:**
- Make recursive search opt-in (last resort)
- Limit search depth to 3 levels
- Implement timeout (5 seconds max)
- Cache results aggressively

### Risk 2: False Positives
**Problem:** Detecting invalid installations
**Mitigation:**
- Rigorous validation pipeline
- Health scoring system
- Warn user about low-health installations

### Risk 3: Breaking Changes
**Problem:** Changing detection API could break existing code
**Mitigation:**
- Keep `get_available_engines()` signature unchanged
- Add new functions alongside old ones
- Deprecate old `detect_engine_path.py` but keep for now

---

## Timeline

| Task | Duration | Dependencies |
|------|----------|--------------|
| Design & Planning | 30 min | None (DONE) |
| Create `environment_detector.py` | 2-3 hours | None |
| Implement .ue5query support | 30 min | environment_detector.py |
| Integrate with existing code | 30 min | environment_detector.py |
| Add detection help system | 30 min | Integration complete |
| Add caching | 15 min | environment_detector.py |
| Testing & debugging | 1 hour | All above |

**Total:** 3-4 hours

---

## Quick Start for Next Session

**Commands to Run:**
```bash
cd D:\DevTools\UE5-Source-Query

# Check current state
git log --oneline -5

# See what was completed
cat docs/PHASE_5_RELATIONSHIP_EXTRACTION.md

# Start Phase 6
# 1. Create src/utils/environment_detector.py
# 2. Implement EnvironmentDetector class
# 3. Add detection strategies
# 4. Test with: python -m pytest tests/test_environment_detector.py
```

**Key Files to Review:**
- `src/utils/engine_helper.py` (current detection)
- `src/utils/config_manager.py` (config management)
- `src/management/gui_dashboard.py` (GUI integration)

**Implementation Order:**
1. Start with EnvironmentDetector skeleton
2. Implement EnvVarStrategy (simplest)
3. Implement ValidationPipeline
4. Test and iterate
5. Add remaining strategies
6. Integrate with GUI

---

## Related Documentation

- **PHASE_5_RELATIONSHIP_EXTRACTION.md** - Previous phase (completed)
- **INTEGRATION_AUDIT.md** - Integration status
- **AI_AGENT_GUIDE.md** - Will need updates for env vars
- **README.md** - Will need setup examples

---

## Notes for Future Sessions

**Context Preservation:**
- All Phases 1-5 are complete and committed
- Documentation cleanup done (outdated files archived to docs/_archive)
- Current detection is basic but functional
- This phase is about expansion and hardening, not replacing

**Philosophy:**
- Progressive enhancement (add new, keep old working)
- User-friendly error messages
- Performance matters (use caching)
- Validate everything

**After Phase 6:**
Consider these for future phases:
- Phase 7: Advanced Filtering (semantic filters, compound queries)
- Phase 8: GUI Relationship Viewer (visual graph exploration)
- Phase 9: Export/Import (knowledge base building)
- Phase 10: Performance Optimization (GPU acceleration, parallel processing)

---

*Last Updated: 2025-12-02*
*Ready for Implementation: Yes*
*Estimated Completion: 1 session (3-4 hours)*
