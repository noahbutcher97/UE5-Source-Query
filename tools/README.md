# Tools Directory

**Backend scripts** powering the Unified Dashboard.

These scripts perform the heavy lifting for system management. While they can be run manually, it is recommended to use the **Unified Dashboard** (`launcher.bat`) for a better experience.

---

## Core Tools

### 🔍 health-check.bat
**System Validation Tool**
Verifies installation integrity, Python environment, and vector store status.
*   **Usage:** `tools\health-check.bat`
*   **Dashboard:** Diagnostics Tab

### 🔄 rebuild-index.bat
**Vector Store Builder**
Rebuilds the semantic search index from source code.
*   **Usage:** `tools\rebuild-index.bat [--force] [--verbose]`
*   **Dashboard:** Maintenance Tab

### 🔼 update.bat
**Updater**
Pulls latest changes from the repository.
*   **Usage:** `tools\update.bat`
*   **Dashboard:** Maintenance Tab

### 🔧 fix-paths.bat
**Path Repair**
Regenerates `EngineDirs.txt` by scanning for UE5 installations. Use this if you move the installation to a new machine.
*   **Usage:** `tools\fix-paths.bat`

### 📦 setup-git-lfs.bat
**Collaboration Setup**
Configures Git LFS for sharing the vector store.
*   **Usage:** `tools\setup-git-lfs.bat`

---

## Note
Previous tools like `add-directory.bat` and `manage.bat` have been superseded by the **Source Manager** in the Dashboard.