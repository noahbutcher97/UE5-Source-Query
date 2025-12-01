# Team Setup Guide

**Quick Onboarding for New Team Members**

This guide helps new team members get the UE5 Source Query tool running on their machines with minimal friction.

---

## Prerequisites

Before you begin, ensure you have:

1. **Python 3.8+** installed and accessible from command line
   - Test: Open cmd and run `python --version`
   - If not installed: Download from [python.org](https://python.org)

2. **Git** installed (for cloning the repository)
   - Test: `git --version`

3. **Unreal Engine 5.x** source code on your machine
   - Either from Epic Games Launcher or GitHub

4. **Anthropic API Key** for Claude
   - Get one from [console.anthropic.com](https://console.anthropic.com)

---

## Quick Start (5 Minutes)

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd UE5-Source-Query
```

### Step 2: Run the Configuration Wizard

```bash
configure.bat
```

This interactive wizard will:
- Create a Python virtual environment
- Install required packages (sentence-transformers, anthropic, numpy)
- Prompt for your Anthropic API key
- Detect your UE5 installation path
- Generate the engine directory list

**Important**: When prompted for your UE5 installation:
- The wizard will attempt to auto-detect from Windows Registry
- If detection fails, manually enter the path to your Engine folder
- Example: `C:\Program Files\Epic Games\UE_5.3\Engine`

### Step 3: Health Check

```bash
health-check.bat
```

This validates:
- Python version (>= 3.8)
- Virtual environment is functional
- Required packages are installed
- Configuration file has valid API key
- Template file is present
- Engine paths are configured
- Vector store status (if built)

If any checks fail, follow the recovery steps shown in the output.

### Step 4: Build the Vector Index

```bash
rebuild-index.bat
```

This will:
- Extract code definitions from your UE5 source
- Generate semantic embeddings
- Save the vector store to `data/`

**Expected duration**: 5-15 minutes depending on your system.

**Progress**: Use `--progress` flag to see detailed progress:
```bash
rebuild-index.bat --progress
```

### Step 5: Test a Query

```bash
ask.bat "What is FVector"
```

If you see relevant UE5 source code definitions, you're all set!

---

## Vector Store Options

There are two approaches to handling the vector store on teams:

### Option A: Build Per-Machine (Default)

**Recommended for**: Small teams, machines with different UE5 versions

Each team member runs `rebuild-index.bat` on their machine.

**Pros**:
- Works with any UE5 version
- No network dependencies
- Customizable indexing (can exclude directories)

**Cons**:
- Takes 5-15 minutes per machine
- Requires ~500MB disk space per machine

### Option B: Shared via Git LFS

**Recommended for**: Large teams, identical UE5 versions, frequent onboarding

One person builds the index, then shares via Git LFS.

**Setup** (one-time, by team lead):

1. Install Git LFS:
```bash
git lfs install
```

2. Run the LFS setup script:
```bash
setup-git-lfs.bat
```

3. Build and commit the vector store:
```bash
rebuild-index.bat --force
git add data/vector_store.npz data/vector_meta.json
git commit -m "Add pre-built vector store for UE 5.3"
git push
```

**Usage** (team members):

1. Clone with LFS enabled:
```bash
git lfs install
git clone <repository-url>
```

2. Verify the vector store downloaded:
```bash
health-check.bat
```

3. Skip `rebuild-index.bat` and go straight to querying:
```bash
ask.bat "your question"
```

**Important**: If a team member has a different UE5 version or different engine path:
- They must run `fix-paths.bat` to regenerate `EngineDirs.txt`
- Then run `rebuild-index.bat --force` to rebuild for their specific setup

---

## Common Scenarios

### Different UE5 Versions Across Team

**Problem**: Team members use UE 5.3, 5.4, or custom engine builds.

**Solution**: Each member builds their own vector store.

```bash
# After configure.bat, each member:
rebuild-index.bat
```

### Different Drive Letters

**Problem**: Some machines have UE5 on `C:\`, others on `D:\` or `E:\`.

**Solution**: `configure.bat` detects this automatically.

If paths change later (e.g., moving to a new drive):
```bash
fix-paths.bat
rebuild-index.bat --force
```

### Moving Between Machines

**Problem**: Developer moves from desktop to laptop with different UE5 paths.

**Solution**:
```bash
# On new machine after cloning:
fix-paths.bat
rebuild-index.bat --force
```

### Shared Network Drive / Synced Folder

**Problem**: Repository is on OneDrive, Dropbox, or network share.

**Considerations**:
- `.venv` folder should NOT be synced (added to `.gitignore`)
- `data/vector_store.npz` should NOT be synced unless using Git LFS
- Each machine needs to run `configure.bat` to create local venv

**Setup**:
1. Clone/sync the repository
2. Run `configure.bat` (creates local venv)
3. Either:
   - Use shared vector store via Git LFS, OR
   - Build locally with `rebuild-index.bat`

---

## Troubleshooting

### "Virtual environment not found"

**Cause**: `.venv` folder is missing or corrupted.

**Fix**:
```bash
configure.bat
```

Or manually:
```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

### "EngineDirs.txt not found"

**Cause**: Engine paths haven't been configured.

**Fix**:
```bash
fix-paths.bat
```

### "Missing packages: sentence-transformers"

**Cause**: Virtual environment is incomplete.

**Fix**:
```bash
.venv\Scripts\pip install -r requirements.txt
```

### "ANTHROPIC_API_KEY appears to be placeholder"

**Cause**: API key not set in `config/.env`.

**Fix**:
1. Open `config/.env` in a text editor
2. Replace `your_api_key_here` with your actual API key from console.anthropic.com
3. Save the file

### "None of the checked paths exist"

**Cause**: Wrong UE5 installation path selected.

**Fix**:
```bash
fix-paths.bat
# When prompted, carefully enter the correct Engine path
# Example: C:\Program Files\Epic Games\UE_5.3\Engine
```

### Vector Store is Corrupted

**Symptoms**:
- `health-check.bat` shows vector store errors
- Query results are empty or incorrect

**Fix**:
```bash
rebuild-index.bat --force
```

This forces a complete rebuild, replacing the corrupted store.

---

## Best Practices

### For Team Leads

1. **Choose a Vector Store Strategy Early**
   - Document whether team will use Git LFS or build-per-machine
   - Communicate this in your project's README

2. **Standardize UE5 Versions**
   - If possible, have all devs use the same UE5 version
   - Makes Git LFS vector sharing viable

3. **Add Health Checks to Onboarding**
   - Include `health-check.bat` in your onboarding checklist
   - Ensures new members have working setups

4. **Commit EngineDirs.template.txt**
   - ALWAYS commit the template (it's version-controlled)
   - NEVER commit `EngineDirs.txt` (it's machine-specific)

### For Developers

1. **Run Health Check Regularly**
   - After pulling changes: `health-check.bat`
   - If queries seem off: `health-check.bat`

2. **Don't Commit Local Files**
   - `.venv/` - virtual environment (local)
   - `config/.env` - contains your API key (secret)
   - `EngineDirs.txt` - machine-specific paths (local)
   - `data/vector_store.npz` - only if NOT using Git LFS

3. **Rebuild After Major UE5 Source Changes**
   - If you pull new UE5 source code updates
   - If you switch UE5 branches
   ```bash
   rebuild-index.bat --force
   ```

4. **Use Verbose Flags for Debugging**
   ```bash
   health-check.bat --verbose
   rebuild-index.bat --progress
   ask.bat "query" --verbose
   ```

---

## File Reference

### Always Commit (Version Controlled)
- `src/**/*.py` - All source code
- `requirements.txt` - Python dependencies
- `*.bat` - Entry point scripts
- `src/indexing/EngineDirs.template.txt` - Path template
- `docs/` - All documentation

### Never Commit (Local / Secret)
- `.venv/` - Virtual environment
- `config/.env` - API keys
- `src/indexing/EngineDirs.txt` - Machine-specific paths
- `data/vector_store.npz` - Unless using Git LFS
- `data/vector_meta.json` - Unless using Git LFS
- `*.backup_*` - Backup files

### Optional Commit (Git LFS)
- `data/vector_store.npz` - If sharing pre-built index
- `data/vector_meta.json` - If sharing pre-built index

---

## Advanced Configuration

### Custom Engine Directories

If you only want to index specific UE5 directories:

1. Run `configure.bat` to generate `EngineDirs.txt`
2. Edit `src/indexing/EngineDirs.txt` manually
3. Comment out unwanted directories with `#`
4. Run `rebuild-index.bat --force`

Example:
```
# Only index Core modules
C:\Program Files\Epic Games\UE_5.3\Engine\Source\Runtime\Core
C:\Program Files\Epic Games\UE_5.3\Engine\Source\Runtime\CoreUObject
# C:\Program Files\Epic Games\UE_5.3\Engine\Plugins (commented out - won't be indexed)
```

### Multiple UE5 Versions on Same Machine

1. Create separate clones of the tool for each version:
```bash
git clone <repo> UE5-Query-5.3
git clone <repo> UE5-Query-5.4
```

2. Configure each independently:
```bash
cd UE5-Query-5.3
configure.bat  # Point to UE 5.3

cd ..\UE5-Query-5.4
configure.bat  # Point to UE 5.4
```

### Using with Custom Engine Builds

1. When running `configure.bat`, select "custom path"
2. Point to your custom engine's `Engine` folder
3. The tool will detect and index your custom source code

---

## Support

For issues not covered here:

1. Check `docs/TROUBLESHOOTING.md` for detailed error resolution
2. Run `health-check.bat --verbose` for diagnostic information
3. Check the project's issue tracker
4. Contact your team lead

---

## Summary: Zero to Query in 5 Commands

```bash
# 1. Clone
git clone <repository-url> && cd UE5-Source-Query

# 2. Configure
configure.bat

# 3. Validate
health-check.bat

# 4. Index (or skip if using Git LFS)
rebuild-index.bat

# 5. Query!
ask.bat "What is AActor"
```

**Time investment**: ~10-20 minutes including indexing.
**Benefit**: Instant semantic search over millions of lines of UE5 source code.
