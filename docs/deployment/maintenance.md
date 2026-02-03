# UE5 Source Query Tool - Maintenance Guide

## Quick Reference

| Task | Command | Description |
|------|---------|-------------|
| **GUI Management** | `manage.bat` | Launch graphical management tool |
| **Update Installation** | `update.bat [target_dir]` | Update existing installation with latest code |
| **Reconfigure** | `configure.bat` | Re-run configuration wizard |
| **Rebuild Index** | `rebuild-index.bat [--force] [--verbose]` | Rebuild entire vector store |
| **Add Directory** | `add-directory.bat <dir> [--verbose]` | Incrementally add directory to index |
| **Manage Directories** | `manage-directories.bat list/add/remove/rebuild` | Manage indexed directories |

## GUI Management Tool

The easiest way to manage your installation:

```bash
manage.bat
# or
manage-directories.bat gui
```

### Features:
- **Configuration Tab**: Edit API key, vector store location, models
- **Directories Tab**: Add/remove indexed directories with file browser
- **Actions Tab**: Rebuild index, update installation, run wizard
- **Output Log**: Real-time feedback from operations

## Command-Line Tools

### 1. Update Installation

Updates source files from main repository while preserving configuration and data:

```bash
# Update current directory
update.bat

# Update specific installation
update.bat "D:\YourProject\Scripts\UE5-Source-Query"
```

**What it does:**
- ✅ Backs up existing `.env` configuration
- ✅ Updates all source files (Python scripts, batch files)
- ✅ Updates dependencies if requirements.txt changed
- ✅ Preserves vector store data
- ✅ Preserves configuration

### 2. Reconfigure Installation

Re-run the configuration wizard:

```bash
configure.bat
```

**When to use:**
- Change API key
- Switch embedding models (requires index rebuild)
- Change vector store location
- Reconfigure from scratch

### 3. Rebuild Vector Index

Rebuild the entire vector store from UE5 engine source:

```bash
# Basic rebuild (prompts for confirmation)
rebuild-index.bat

# Force rebuild without confirmation
rebuild-index.bat --force

# Verbose output with progress
rebuild-index.bat --force --verbose

# Use custom directory list
rebuild-index.bat --dirs-file "custom_dirs.txt" --force
```

**Timing:**
- With GPU (RTX 5090): 2-3 minutes
- CPU only: 30-40 minutes

### 4. Add Directory Incrementally

Add a new directory to existing index without full rebuild:

```bash
# Add single directory
add-directory.bat "C:/Program Files/Epic Games/UE_5.3/Engine/Source/Runtime/Physics"

# With verbose output
add-directory.bat "D:/CustomEngine/Source" --verbose
```

**Use cases:**
- Add custom engine modifications
- Include third-party plugins
- Add project-specific source code

###  5. Manage Indexed Directories

Persistent directory management with configuration file:

```bash
# List all configured directories
manage-directories.bat list

# Add directory to configuration
manage-directories.bat add "C:/Path/To/Source"

# Remove directory from configuration
manage-directories.bat remove "C:/Path/To/Source"

# Rebuild from configured directories
manage-directories.bat rebuild --verbose

# Launch GUI
manage-directories.bat gui
```

**Configuration file:** `config/indexed_directories.txt`

## Common Workflows

### Adding New Engine Modules

```bash
# Method 1: Quick incremental add
add-directory.bat "C:/Program Files/Epic Games/UE_5.3/Engine/Plugins/Runtime/Metasound"

# Method 2: Add to config and rebuild later
manage-directories.bat add "C:/Program Files/Epic Games/UE_5.3/Engine/Plugins/Runtime/Metasound"
manage-directories.bat rebuild
```

### Switching Embedding Models

```bash
# 1. Reconfigure to change model
configure.bat
# Select new embedding model (e.g., all-MiniLM-L6-v2)

# 2. Rebuild index with new model
rebuild-index.bat --force --verbose
```

### Updating After Main Repo Changes

```bash
# 1. Update installation
update.bat

# 2. Reconfigure if needed (optional)
configure.bat

# 3. Rebuild if indexing logic changed (optional)
rebuild-index.bat --force
```

### Setting Up New Project Installation

```bash
# From main repo directory
cd D:\DevTools\UE5-Source-Query
install.bat "D:\NewProject" --gpu --build-index

# Configure
cd "D:\NewProject\Scripts\UE5-Source-Query"
configure.bat

# Customize indexed directories
manage-directories.bat gui
```

## Configuration Files

### config/.env
Main configuration file (created by `configure.bat`):
```ini
ANTHROPIC_API_KEY=your_key_here
VECTOR_OUTPUT_DIR=D:\...\data
PYTHONPATH=D:\...\. venv\Lib\site-packages
EMBED_MODEL=microsoft/unixcoder-base
ANTHROPIC_MODEL=claude-3-haiku-20240307
```

### config/indexed_directories.txt
Persistent directory list (managed by `manage-directories.bat`):
```
C:/Program Files/Epic Games/UE_5.3/Engine/Source/Runtime
C:/Program Files/Epic Games/UE_5.3/Engine/Source/Editor
D:/CustomEngine/Source
```

### src/indexing/EngineDirs.txt
Default UE5 engine directories for indexing (predefined list).

## Troubleshooting

### "Configuration not found" Error

```bash
# Run configuration wizard
configure.bat
```

### "Virtual environment not found" Error

```bash
# Reinstall from main repo
cd D:\DevTools\UE5-Source-Query
install.bat "D:\YourProject"
```

### Dimension Mismatch Errors

Occurs when embedding model changes but index wasn't rebuilt:

```bash
# Check current model in config/.env
# Then rebuild index
rebuild-index.bat --force
```

### GUI Won't Launch

```bash
# Check if tkinter is available
.venv\Scripts\python.exe -c "import tkinter"

# If error, tkinter not installed with Python
# Reinstall Python with tkinter support
```

### Index Build Fails

```bash
# Check logs
type logs\*.log

# Verify directories exist
manage-directories.bat list

# Try with verbose output
rebuild-index.bat --force --verbose
```

## Best Practices

1. **Regular Updates**: Run `update.bat` monthly to get latest improvements
2. **Backup Configuration**: Keep a copy of `config/.env` before major changes
3. **Incremental Additions**: Use `add-directory.bat` for single directories instead of full rebuild
4. **Directory Management**: Use `config/indexed_directories.txt` to track custom additions
5. **GPU Acceleration**: Always use `--gpu` flag during installation for 10-15x faster indexing
6. **Version Control**: Add `config/.env` to `.gitignore` (contains API key)

## Performance Tips

- **GPU Acceleration**: Install with `--gpu` for 2-3 minute rebuilds vs 30-40 minutes CPU
- **Incremental Updates**: Use `add-directory.bat` instead of full rebuilds when possible
- **Selective Indexing**: Only index directories you actually query (edit `src/indexing/EngineDirs.txt`)
- **Model Selection**: `all-MiniLM-L6-v2` (384-dim) is faster but less accurate than `unixcoder-base` (768-dim)

## Getting Help

- Documentation: `docs/` directory
- Deployment Guide: `docs/DEPLOYMENT.md`
- Main README: `README.md`
- Report Issues: https://github.com/YourOrg/UE5-Source-Query/issues
