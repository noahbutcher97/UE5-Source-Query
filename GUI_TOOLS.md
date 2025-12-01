# GUI Tools - Visual Interface Guide

All command-line tools now have **double-clickable GUI versions** for easy user interaction!

---

## Quick Reference

| Task | CLI Version | GUI Version (Double-Click!) |
|------|-------------|----------------------------|
| 📦 **Install to new location** | `installer\install_cli.bat` | **`install.bat`** ⭐ |
| ⚙️ **Configure API key & paths** | `configure.bat` | **`configure-gui.bat`** |
| ✅ **Check system health** | `health-check.bat` | **`health-check-gui.bat`** |
| 🔄 **Rebuild vector index** | `rebuild-index.bat` | **`rebuild-index-gui.bat`** |
| 🔧 **Fix UE5 paths** | `fix-paths.bat` | **`fix-paths-gui.bat`** |

---

## Main GUI Tools

### 1. install.bat - Deployment Wizard ⭐

**Double-click to install to a new location**

**Features:**
- Browse button to select target directory
- Checkboxes for:
  - ☑ GPU acceleration support
  - ☑ Build vector index after install
  - ☑ Copy existing configuration
- Prerequisites check panel:
  - [OK] Python version
  - [OK] Disk space (need 500MB+)
  - [OK] Source files present
  - [OK] pip available
- Real-time installation log
- Progress bar
- **Big green "▶ Install Now" button**
- Success dialog with next steps

**Window Size:** 750x700, centered on screen, resizable

**Use when:** Deploying to a new Unreal project or machine

---

### 2. configure-gui.bat - Configuration Wizard

**Double-click to set up API key and UE5 paths**

**Features:**
- Wraps `configure.bat` with real-time output
- Shows interactive prompts in scrolling log
- **Green "▶ Run" button** to start
- Progress bar during execution
- Success/failure dialog at completion

**Use when:**
- First-time setup
- Changing API key
- Adding/changing UE5 installation path

---

### 3. health-check-gui.bat - System Validation

**Double-click to verify installation health**

**Features:**
- Wraps `health-check.bat` with visual output
- Shows all 7 health checks:
  1. Python Version
  2. Virtual Environment
  3. Required Packages
  4. Configuration File
  5. Template File
  6. Engine Paths
  7. Vector Store
- Color-coded results in log:
  - `[OK]` - Passed
  - `[X]` - Failed
  - `[!]` - Warning
- **Green "▶ Run" button**
- Summary at end

**Use when:**
- After installation
- Before querying
- Troubleshooting issues
- After pulling Git changes

---

### 4. rebuild-index-gui.bat - Vector Store Builder

**Double-click to rebuild the vector index**

**Features:**
- Wraps `rebuild-index.bat` with progress monitoring
- Shows:
  - File scanning progress
  - Embedding generation (may take 5-15 min)
  - Post-build verification
- **Green "▶ Run" button**
- Warning if operation takes > 2 minutes
- Success confirmation when complete

**Use when:**
- After UE5 source code updates
- Switching UE5 versions
- Vector store corrupted
- Adding/removing indexed directories

---

### 5. fix-paths-gui.bat - Path Regeneration

**Double-click to regenerate UE5 paths**

**Features:**
- Wraps `fix-paths.bat` with interactive UE5 detection
- Shows:
  - Registry scanning
  - Common location search
  - Manual path entry prompts
- **Green "▶ Run" button**
- Success confirmation

**Use when:**
- Moving to different machine
- UE5 paths changed (drive letter, version)
- EngineDirs.txt missing or corrupted

---

## How GUI Wrappers Work

All `-gui.bat` files use the universal GUI wrapper (`src/utils/gui_wrapper.py`):

```
User double-clicks → GUI window opens → Shows description & options
                  ↓
         Click "▶ Run" button
                  ↓
    Script executes with real-time output in scrolling log
                  ↓
         Success/failure dialog appears
```

**Common Features:**
- 800x600 window, centered on screen
- Blue header with title
- Description of what the script does
- Scrolling output log (monospace font)
- Indeterminate progress bar
- **Green "▶ Run" button** (impossible to miss!)
- Close button (warns if script still running)
- Success/error dialogs at completion

---

## CLI vs GUI Comparison

### When to Use CLI

**Automation & Scripting:**
```bash
# CI/CD pipeline
installer\install_cli.bat "D:\Deploy\UE5-Query" --gpu --build-index

# Batch operations
for /d %%d in (Project1 Project2 Project3) do (
    installer\install_cli.bat "%%d"
)
```

**Quick Commands:**
```bash
# Fast health check without GUI
health-check.bat

# Rebuild with specific flags
rebuild-index.bat --force --progress
```

**Advantages:**
- ✅ Scriptable
- ✅ Faster (no GUI overhead)
- ✅ Can redirect output
- ✅ Works in SSH/remote sessions

### When to Use GUI

**Interactive Use:**
- Double-click and follow visual prompts
- See real-time progress
- Get instant feedback
- No need to remember flags

**First-Time Setup:**
- More forgiving for new users
- Visual confirmation of each step
- Clear error messages with dialogs

**Troubleshooting:**
- Easier to read output
- Scrollable logs
- Can copy/paste errors easily

**Advantages:**
- ✅ User-friendly
- ✅ No command-line knowledge needed
- ✅ Visual progress indicators
- ✅ Success/error dialogs
- ✅ Centralized window (no minimized command prompts)

---

## Creating Custom GUI Wrappers

You can wrap any .bat file with a GUI:

```batch
@echo off
python src\utils\gui_wrapper.py "your-script.bat" ^
    --title "Your Tool Name" ^
    --description "What this tool does and why you'd use it."
```

**Advanced: Adding Argument Controls**

Modify `gui_wrapper.py` and add `args_config` parameter:

```python
args_config = [
    {
        'name': 'force',
        'type': 'boolean',
        'label': 'Force rebuild (ignore existing data)',
        'flag': '--force'
    },
    {
        'name': 'directory',
        'type': 'string',
        'label': 'Target Directory:',
        'default': 'D:\\MyProject'
    },
    {
        'name': 'mode',
        'type': 'choice',
        'label': 'Build Mode:',
        'choices': ['fast', 'thorough', 'minimal'],
        'default': 'thorough'
    }
]

app = BatchGUI(root, "script.bat", args_config=args_config)
```

This creates checkboxes, text fields, or dropdown menus in the GUI.

---

## Troubleshooting GUI Tools

**GUI won't open:**
1. Check Python is installed: `python --version`
2. Check tkinter is available: `python -c "import tkinter"`
3. On some systems: `pip install tk`

**Button not visible:**
- The window might be too small
- Try maximizing the window
- Check monitor resolution

**Script fails silently:**
- Look at the scrolling log for errors
- Error dialog should appear
- Check underlying .bat file works in CLI

**Output garbled:**
- Some emojis/Unicode may not display
- Functionality unaffected
- Output still readable in monospace font

---

## Summary

✅ **5 GUI versions** of critical tools created
✅ **Universal wrapper** for any future tools
✅ **Big visible buttons** with clear labels
✅ **Real-time progress** in all GUIs
✅ **Success/error dialogs** for immediate feedback
✅ **Centered windows** for better UX
✅ **CLI versions still available** for automation

**Result:** Every user-facing operation can now be done with a double-click! No command-line experience required. 🎉
