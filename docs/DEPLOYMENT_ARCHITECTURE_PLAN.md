# Unified Deployment Architecture Plan

## Vision
A strictly defined "Download → Deploy → Manage" workflow that abstracts away the complexity of Python environments, batch scripts, and configuration files. The user should interact with **one** graphical entry point for installation and **one** graphical dashboard for daily use.

### Core Principle: Separation of Concerns
**Crucial:** The system must strictly distinguish between **Engine Source** (Immutable, Definitive API) and **Project Source** (Mutable, Implementation).
*   **Goal:** An agent asking for "APawn::Possess signature" must receive the canonical Engine definition, not a local override.
*   **Mechanism:** Strict metadata tagging and separate configuration lists. Default queries target **Engine Only**.

## 1. The User Journey (Target Workflow)

1.  **Download:** User downloads `UE5-Query-Setup.zip` (or clones the repo).
2.  **Run Setup:** User double-clicks `Setup.bat` (formerly `install.bat`).
3.  **Configure:** The **Deployment Wizard**:
    *   Detects installed UE5 versions (Completed).
    *   **NEW:** Asks "Do you want to index a specific Game Project?" (Project-aware deployment).
    *   Installs the tool to the chosen location.
4.  **Launch:** User opens the tool via a desktop shortcut or `Dashboard.bat`.
5.  **Manage:** The **Unified Dashboard** handles all tasks (Querying, Re-indexing, Health Checks, Updates).

## 2. Gap Analysis: CLI vs. GUI

| Functionality | Current Script | GUI Status | Action Required |
| :--- | :--- | :--- | :--- |
| **Install/Deploy** | `install.bat` | ✅ `gui_deploy.py` | Rename to `Setup.bat`, add Project selection. |
| **Initial Config** | `configure.bat` | ✅ `configure_gui.py` | Merge into Dashboard "Config" tab. |
| **Rebuild Index** | `rebuild-index.bat` | ⚠️ Partial (Manager) | Fully integrate into Dashboard with progress bar. |
| **Health Check** | `health-check.bat` | ⚠️ Partial (Dashboard) | enhance visualization (Green/Red indicators). |
| **Fix Paths** | `fix-paths.bat` | ❌ **CLI Only** | Add "Repair Paths" button to Dashboard > Troubleshooting. |
| **Add Directory** | `add-directory.bat` | ❌ **CLI Only** | Add "Manage Sources" tab to Dashboard. |
| **Git LFS Setup** | `setup-git-lfs.bat` | ❌ **CLI Only** | Add "Collaboration" tab to Dashboard. |
| **Update Tool** | `update.bat` | ❌ **CLI Only** | Add "Check for Updates" button to Dashboard. |

## 3. Architecture Components

### A. The Portable Installer (`installer/`)
*   **Role:** The "Factory" that creates working instances of the tool.
*   **New Feature:** **Project Awareness**.
    *   Instead of just indexing the Engine, allow selecting a `.uproject` file.
    *   The installer generates a separate `ProjectDirs.txt` file.
*   **New Feature:** **Shortcut Creation**.
    *   Create a desktop shortcut "UE5 Source Query" pointing to `launcher.bat`.

### B. The Runtime Dashboard (`src/management/gui_dashboard.py`)
The new central hub. It must absorb all standalone scripts.

**Structure:**
*   **Tab 1: Query (The Main View)**
    *   Search bar, results pane, "Copy" buttons.
    *   **Scope Toggle:** [x] Engine (Default) | [ ] Project.
    *   Replaces `ask.bat` for GUI users.
*   **Tab 2: Source Management (Replaces `manage-directories`)**
    *   **Section A: Engine:** Read-only list from `EngineDirs.txt`. "Repair" button to re-detect.
    *   **Section B: Project:** Editable list from `ProjectDirs.txt`. Add/Remove folders.
*   **Tab 3: Maintenance (Replaces `rebuild`, `fix-paths`, `update`)**
    *   "Rebuild Index" (Big button with progress).
    *   "Update Tool" (Git pull + dependency check).
*   **Tab 4: Settings (Replaces `configure`)**
    *   API Keys, Model selection, Theme toggle.

## 4. Data Separation Strategy (The Firewall)
To prevent "muddying" the definitive API with project code:

1.  **Configuration:**
    *   `src/indexing/EngineDirs.txt`: Exclusively for UE5 installation paths.
    *   `src/indexing/ProjectDirs.txt`: Exclusively for user project paths.
2.  **Indexing (`build_embeddings.py`):**
    *   Reads both files.
    *   Tags Engine chunks with `metadata={'origin': 'engine'}`.
    *   Tags Project chunks with `metadata={'origin': 'project'}`.
3.  **Querying (`hybrid_query.py`):**
    *   **Default:** Filters for `origin=='engine'`. This ensures `ask.bat` remains a pure API tool.
    *   **Opt-In:** Flag `--scope project` or `--scope all` required to see project code.

## 5. Implementation Roadmap

### Phase 1: The Dashboard (Consolidating Functionality)
*   [ ] **Task 1:** Implement "Source Management" tab.
    *   Logic to read/write `ProjectDirs.txt`.
    *   Logic to display `EngineDirs.txt`.
*   [ ] **Task 2:** Update `build_embeddings.py` to respect the `origin` tag.
*   [ ] **Task 3:** Update `hybrid_query.py` to implement default Engine-only filtering.

### Phase 2: The Installer (Deployment Logic)
*   [ ] **Task 4:** Update `gui_deploy.py` to accept a Target Project (`.uproject`).
*   [ ] **Task 5:** Add logic to generate `ProjectDirs.txt`.
*   [ ] **Task 6:** Add shortcut creation logic (Windows `.lnk`).

### Phase 3: Packaging (Distribution)
*   [ ] **Task 7:** Create `create_dist.bat` script.
    *   Zips `installer/`, `src/`, `config/`, `install.bat` into a clean package.
    *   Excludes `.venv`, `__pycache__`, `data/`.

## 6. Success Criteria
*   A user downloads the ZIP.
*   Runs `Setup.bat`.
*   Selects their Game Project.
*   Tool installs, shortcuts appear.
*   User opens Dashboard, sees their Project code is ALREADY indexed (or queued).
*   User never opens a command prompt.
