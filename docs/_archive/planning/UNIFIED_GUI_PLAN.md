# Unified GUI Deployment Architecture Plan

## Problem Statement
The current deployment consists of a mix of GUI wizards (`install.bat`, `configure.bat`) and CLI scripts (`rebuild-index.bat`, `health-check.bat`). This leads to an inconsistent user experience, with some critical validation steps hidden in console output.

## Goal
Create a **Single Unified Dashboard** that serves as the central hub for all UE5 Source Query operations, ensuring a consistent, visual, and robust user experience.

## Architecture Overview

### 1. The "Launcher" (Primary Entry Point)
*   **New Script:** `launcher.bat` (replaces `manage.bat` as the main interface).
*   **Function:** Launches the `src/management/gui_dashboard.py` (renamed from `gui_manager.py`).
*   **Role:** The "Control Panel" for the application.

### 2. Unified Dashboard (`src/management/gui_dashboard.py`)
This Python application will be expanded to cover all functionality currently scattered across CLI scripts.

**Proposed Tabs:**
1.  **Query (New):** Simple graphical interface to run queries without `ask.bat` CLI.
2.  **Management (Existing):** Manage directories, rebuild index.
3.  **Configuration (Existing):** Edit API keys, models.
4.  **Diagnostics (New):** visual `health-check` runner with Red/Green indicators.
5.  **Troubleshoot (New):** Buttons for `fix-paths`, `reset-config`, `update`.

### 3. Shared GUI Theme (`src/utils/gui_theme.py`)
A shared module to define:
*   Color palette (Dark Mode/Light Mode).
*   Font styles.
*   Standard widget classes (e.g., `StyledButton`, `LogFrame`).
*   **Purpose:** Ensure `installer/gui_deploy.py` and the Dashboard look like the same software.

### 4. Legacy CLI Scripts (`tools/*.bat`)
*   **Refactor:** Update these scripts to serve *only* as automation hooks (CI/CD).
*   **Documentation:** Mark them as "Advanced/Automation Only".
*   **Behavior:** If run without arguments, they could optionally launch the specific tab in the Dashboard.

## Implementation Roadmap

### Phase 1: Core Unification (Immediate)
- [ ] Create `src/utils/gui_theme.py` for consistent styling.
- [ ] Rename `src/management/gui_manager.py` to `src/management/gui_dashboard.py`.
- [ ] Create `launcher.bat`.
- [ ] Add "Health Check" tab to Dashboard (wraps `verify_installation.py`).

### Phase 2: Feature Parity
- [ ] Add "Query" tab to Dashboard (wraps `hybrid_query.py`).
- [ ] Add "Troubleshoot" tab (wraps `fix-paths.bat`, `setup-git-lfs.bat`).

### Phase 3: Polish & Deployment
- [ ] Update `installer/gui_deploy.py` to use `gui_theme.py`.
- [ ] Update `README.md` to point users to `launcher.bat`.

## Validation Strategy
Every action in the Dashboard will:
1.  Run validity checks *before* execution (e.g., "Is UE5 path valid?").
2.  Show real-time progress bars (no freezing).
3.  Display success/failure in modal dialogs, not just logs.
4.  Log all actions to `logs/gui_operations.log`.
