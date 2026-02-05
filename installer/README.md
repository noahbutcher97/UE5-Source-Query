# Installer Directory

This directory contains deployment tools for the UE5 Source Query Tool.

## Files

### GUI Deployment (Recommended - Just Double-Click!)

**From repository root, simply double-click: `install.bat`**

This launches `gui_deploy.py` - Interactive GUI deployment wizard with:
- 🖱️ Graphical interface for selecting installation directory
- ☑️ Checkbox options for GPU support, index building, config copying
- 📊 Real-time installation progress log
- ✅ Automatic prerequisites checking
- ▶️ Prominent "Install Now" button
- ⚠️ Error handling with helpful messages

**Features:**
- Browse for target directory via file explorer
- Visual progress bar during installation
- Scrolling installation log
- Large, visible Install Now button
- All options accessible via GUI checkboxes

**Alternative direct launch:**
```bash
python installer/gui_deploy.py
```

### Command-Line Deployment (For Automation)

**`install_cli.bat`** - Automated command-line installer
- Non-interactive batch deployment
- Supports flags for GPU, build-index options
- Used for CI/CD and automation scripts

**`install_helper.py`** - Python helper for file copying
- Cross-platform file operations
- Used by install_cli.bat

**Usage:**
```bash
# Custom directory with GPU support
installer\install_cli.bat "D:\MyProject" --gpu --build-index

# Default installation (current directory)
installer\install_cli.bat
```

## Deployment Workflow

### For End Users (GUI - Recommended)

1. **Double-click `install.bat`** in repository root
2. GUI window opens automatically
3. Click "Browse..." to select installation directory
4. Check your options:
   - ☑ GPU acceleration (requires CUDA 12.8)
   - ☑ Build vector index after install
   - ☑ Copy existing configuration
5. Click the big green **"▶ Install Now"** button
6. Watch installation progress in real-time
7. Follow next steps shown in log when complete

### For Automation (CLI)

```bash
# Silent deployment for CI/CD
installer\install_cli.bat "C:\Deploy\UE5-Query" --gpu --build-index
```

## What Gets Installed

The deployment process copies:

1. **Source Code**
   - `ue5_query/core/` - Query engine
   - `ue5_query/indexing/` - Vector store building
   - `ue5_query/utils/` - Health checks and validation
   - `ue5_query/management/` - GUI manager
2. **Documentation**
   - `docs/*.md` - All guides

3. **Entry Points**
   - `ask.bat` - Query interface
   - `configure.bat` - Configuration wizard
   - `health-check.bat` - System validation
   - `rebuild-index.bat` - Index building
   - `fix-paths.bat` - Path regeneration
   - And more...

4. **Dependencies**
   - `requirements.txt` or `requirements-gpu.txt`
   - Creates `.venv` and installs packages

5. **Configuration** (optional)
   - `config/.env` - If "Copy configuration" checked

## Post-Installation Steps

After deployment completes, navigate to the installation directory and run:

```bash
# 1. Configure (if .env wasn't copied)
configure.bat

# 2. Verify installation
health-check.bat

# 3. Build index (if not done during install)
rebuild-index.bat

# 4. Test query
ask.bat "What is FVector"
```

## Troubleshooting

**GUI doesn't launch:**
- Ensure Python 3.8+ is installed
- Check Python is in PATH: `python --version`
- Install tkinter if missing: `pip install tk`

**Installation fails:**
- Check write permissions to target directory
- Ensure sufficient disk space (>500 MB)
- Verify source files are present
- See installation log for specific errors

**Package installation errors:**
- Check internet connection
- Try running: `pip install --upgrade pip`
- For GPU: Ensure CUDA 12.8 is installed

## Development

### Testing GUI Installer

```bash
# Test GUI without installing
python installer/gui_deploy.py

# Test CLI installer
installer\install.bat "C:\Temp\TestInstall"
```

### Adding New Installation Options

1. Edit `gui_deploy.py`:
   - Add `tk.BooleanVar()` in `__init__`
   - Add `tk.Checkbutton` in `create_widgets()`
   - Use variable in `run_installation()`

2. Update `install.bat` if needed for CLI support

3. Document in this README
