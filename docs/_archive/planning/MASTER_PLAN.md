# Master Deployment & Architecture Plan
*Synthesizing User Requirements: Nov 25 - Nov 29, 2025*

## 1. Executive Summary
This plan unifies the development of the UE5 Source Query Tool into a single, robust, and portable solution. It addresses four critical requirements:
1.  **AI-First Reliability:** The tool must provide definitive, non-hallucinated API answers for AI CLI Agents.
2.  **Separation of Concerns:** Strict isolation between **Engine API** (Immutable/Definitive) and **Project Code** (Mutable/Contextual).
3.  **Unified "Download & Deploy":** A simple workflow for teams to download a zip, run a single setup script, and be operational.
4.  **Visual Management:** A single Dashboard replacing scattered CLI scripts (`manage`, `fix-paths`, `rebuild`).

---

## 2. The "Firewall" Architecture (AI Safety)
To ensure AI agents never confuse a local project hack with a definitive Engine API signature, we implement a strict data separation strategy.

### A. Data Layer
*   **Split Configuration:**
    *   `src/indexing/EngineDirs.txt`: Auto-generated list of UE5 Engine paths.
    *   `src/indexing/ProjectDirs.txt`: User-managed list of Game Project paths.
*   **Metadata Tagging:**
    *   `build_embeddings.py` will tag every chunk with an `origin` field.
    *   `origin: 'engine'`: Trusted, canonical source.
    *   `origin: 'project'`: Local implementation context.

### B. Query Layer (`hybrid_query.py`)
*   **Default Scope (Safe):** `ask.bat "FVector"` → Queries **ONLY** `origin: 'engine'`.
    *   *Why?* An AI Agent asking for "FVector members" needs the engine definition, not a project usage.
*   **Extended Scope (Opt-in):** `ask.bat "MyHeroClass" --scope project` or `--scope all`.
    *   *Why?* Allows the user (or agent) to explicitly request project context.

---

## 3. The User Journey (Deployment)

### Step 1: Distribution
*   **Artifact:** `UE5-Query-Suite.zip`.
*   **Contents:** `Setup.bat`, `installer/`, `src/`, `config/` (template), `requirements.txt`.
*   **Location:** User downloads this to `Downloads/` or any temporary folder.

### Step 2: The "Setup" Wizard (Portable Installer)
*   **Entry Point:** `Setup.bat` (Wraps `installer/gui_deploy.py`).
*   **Workflow:**
    1.  **Prerequisites:** Checks Python, Disk Space.
    2.  **Engine Detection:** Scans system for UE5. **Prompts user to select version** if multiple exist (Fixed).
    3.  **Project Selection (Optional):** "Do you want to index a specific Game Project?" -> User browses to `.uproject`.
    4.  **Deployment:** Installs tool to `Documents/UE5-Source-Query` (or custom).
    5.  **Shortcuts:** Creates "UE5 Dashboard" on Desktop.

### Step 3: The Dashboard (Daily Use)
*   **Entry Point:** `Launcher.bat` (Wraps `src/management/gui_dashboard.py`).
*   **Unified Functionality:** Replaces all standalone `.bat` tools.

---

## 4. Unified Dashboard Specs (`src/management/gui_dashboard.py`)

The Dashboard absorbs the functionality of `configure`, `manage`, `fix-paths`, `rebuild`, and `health-check`.

### Tab 1: Query (Visual Interface)
*   Search Bar & Results Pane.
*   **Scope Toggle:** [x] Engine API (Default) | [ ] Project Code.
*   **Format:** Toggle between "Snippet View" and "AI Reasoning".

### Tab 2: Source Manager (The Controller)
*   **Engine Section (Read-Only):**
    *   Displays detected UE5 version & paths.
    *   Button: "Change UE5 Version" (Re-runs auto-detection).
*   **Project Section (Editable):**
    *   List of indexed Project folders.
    *   Buttons: [Add Project], [Remove].
    *   *Back-end:* Updates `ProjectDirs.txt`.

### Tab 3: Maintenance (Ops)
*   **Index Status:** "Last built: 2 hours ago. 15,000 chunks."
*   **Action:** "Rebuild Index" (Progress bar).
*   **Action:** "Update Tool" (Git pull).

### Tab 4: Diagnostics (Health)
*   Visual `health-check` with Green/Red indicators.
*   Quick-fix buttons for common errors.

---

## 5. Implementation Roadmap

### Phase 1: The Data Firewall (Core Logic)
*   [ ] **Task 1.1:** Update `build_embeddings.py` to read `ProjectDirs.txt` and apply `origin` tags.
*   [ ] **Task 1.2:** Update `hybrid_query.py` to filter results based on `origin`.
*   [ ] **Task 1.3:** Update `ask.bat` arguments to support `--scope`.

### Phase 2: The Unified Dashboard (UI)
*   [ ] **Task 2.1:** Implement "Source Manager" tab (Engine vs Project split).
*   [ ] **Task 2.2:** Implement "Maintenance" tab (Rebuild progress).
*   [ ] **Task 2.3:** Implement "Configuration" tab (Merging `configure_gui.py`).

### Phase 3: The Portable Installer (Deployment)
*   [ ] **Task 3.1:** Rename `install.bat` to `Setup.bat`.
*   [ ] **Task 3.2:** Update `gui_deploy.py` to handle Project selection and `ProjectDirs.txt` generation.
*   [ ] **Task 3.3:** Create `create_dist.bat` to package the zip file.

---

## 6. Verification Checklist for AI Agents
After implementation, we verify:
1.  `ask.bat "AActor"` returns **only** Engine headers (No project noise).
2.  `ask.bat "MyGameCharacter"` returns **nothing** by default (Safety).
3.  `ask.bat "MyGameCharacter" --scope project` returns project code.
