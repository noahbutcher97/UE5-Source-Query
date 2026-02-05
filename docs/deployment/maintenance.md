# UE5 Source Query Tool - Maintenance Guide

## Quick Reference

| Task | Command | Description |
|------|---------|-------------|
| **Unified Dashboard** | `launcher.bat` | One-stop GUI for query, sources, and maintenance |
| **Update Code** | `update.bat` | Update existing installation with latest code |
| **Full Setup** | `Setup.bat` | Re-run environment setup and configuration |
| **Rebuild Index** | `rebuild-index.bat` | CLI tool to rebuild the entire vector store |
| **Health Check** | `health-check.bat` | System validation and diagnostic tool |

## GUI Management Tool (Dashboard)

The Unified Dashboard is the primary way to manage your installation:

```bash
launcher.bat
```

### Features:
- **Query Tab**: Live search with semantic and definition filtering.
- **Config Tab**: Edit API keys, models, and indexing parameters.
- **Sources Tab**: Visual management of indexed UE5 and project directories.
- **Maintenance Tab**: Quick access to index rebuilds and updates.
- **Diagnostics Tab**: Deep system checks (GPU, paths, versions).

## Command-Line Tools

### 1. Update Installation

Updates source files from the main repository while preserving your data:

```bash
# Update current directory
update.bat
```

**What it does:**
- ✅ Backs up existing `.env` configuration.
- ✅ Updates all source files (`ue5_query/` package).
- ✅ Re-verifies dependencies in the virtual environment.
- ✅ Preserves your existing vector store.

### 2. Full Setup / Reconfigure

Re-run the setup wizard to fix environment issues or change core settings:

```bash
Setup.bat
```

**When to use:**
- Change Anthropic API key.
- Switch embedding models.
- Re-detect Unreal Engine installation.
- Fix a broken virtual environment.

### 3. Rebuild Vector Index (CLI)

Perform a full rebuild of the vector store from the command line:

```bash
# Location: tools/rebuild-index.bat
rebuild-index.bat --force --verbose
```

---

## Common Workflows

### Adding New Source Directories

Use the **Sources** tab in the Dashboard (`launcher.bat`). It allows you to browse for folders and persists them to the internal configuration.

### Switching Embedding Models

1. Run **Setup.bat** to select the new model (e.g., `all-MiniLM-L6-v2`).
2. Run **rebuild-index.bat --force** to generate new embeddings compatible with that model.

### Updating After System Changes

If you move your Unreal Engine installation or update to a new version:
1. Run **Setup.bat** to re-detect the paths.
2. Rebuild the index from the Dashboard or CLI.

## Troubleshooting

### "Configuration not found" Error
Run **Setup.bat** to regenerate your `.env` file.

### "Virtual environment not found" Error
Run **Setup.bat** to recreate the `.venv` directory and install dependencies.

### Dimension Mismatch Errors
This happens when your index was built with a different model than the one currently selected. 
**Fix**: Run `rebuild-index.bat --force`.

### GUI Won't Launch
Check if `tkinter` is available:
```bash
.venv\Scripts\python.exe -c "import tkinter"
```

## Performance Tips

- **GPU Acceleration**: Ensure an NVIDIA GPU is detected in the **Diagnostics** tab for 15x faster builds.
- **Selective Indexing**: Only index the UE5 modules you actually use (manage this in the **Sources** tab).
- **Batch Sizing**: Adjust batch size in the **Config** tab if you encounter VRAM issues on older cards.

## Getting Help

- **Architecture**: `docs/dev/architecture.md`.
- **API Reference**: `docs/dev/api_reference.md`.
- **Agent Integration**: `docs/user/ai_integration.md`.
- **Issues**: https://github.com/YourOrg/UE5-Source-Query/issues