# Troubleshooting Guide

**Comprehensive Error Resolution for UE5 Source Query Tool**

This guide provides detailed solutions for all common (and uncommon) errors you might encounter.

---

## Quick Diagnostic: Run Health Check

**Before troubleshooting manually, always run:**

```bash
health-check.bat
```

This will identify most issues automatically and suggest fixes.

For detailed output:
```bash
health-check.bat --verbose
```

---

## Installation & Configuration Issues

### Error: "Python 3.8+ required, found X.X.X"

**Cause**: Your Python version is too old.

**Solution**:

1. Download Python 3.8 or newer from [python.org](https://python.org)
2. During installation, check "Add Python to PATH"
3. Restart your command prompt
4. Verify: `python --version`
5. Re-run: `configure.bat`

**Alternative**: Use `py` launcher (Windows):
```bash
py --version
py -m venv .venv
```

---

### Error: "Virtual environment not found"

**Cause**: The `.venv` folder doesn't exist or is corrupted.

**Quick Fix**:
```bash
configure.bat
```

**Manual Fix**:
```bash
# Delete corrupted venv
rmdir /s /q .venv

# Recreate
python -m venv .venv

# Install packages
.venv\Scripts\pip install -r requirements.txt
```

**Prevention**: Never commit `.venv` to version control. It's machine-specific.

---

### Error: "Virtual environment is broken or missing packages"

**Cause**: Packages not installed or installation failed.

**Solution**:

1. Activate virtual environment:
```bash
.venv\Scripts\activate
```

2. Update pip:
```bash
python -m pip install --upgrade pip
```

3. Reinstall requirements:
```bash
pip install -r requirements.txt
```

4. If specific package fails (e.g., sentence-transformers):
```bash
pip install sentence-transformers --no-cache-dir
```

5. Deactivate when done:
```bash
deactivate
```

**Alternative**: Delete `.venv` and re-run `configure.bat`.

---

### Error: "ANTHROPIC_API_KEY not found in config"

**Cause**: Configuration file is missing or doesn't contain API key.

**Solution**:

1. Check if `config/.env` exists:
```bash
dir config\.env
```

2. If missing, run:
```bash
configure.bat
```

3. If exists, open `config/.env` in a text editor and add:
```
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

4. Save and verify:
```bash
health-check.bat
```

**Security Note**: NEVER commit `config/.env` to Git. It contains secrets.

---

### Error: "ANTHROPIC_API_KEY appears to be placeholder"

**Cause**: API key still has default value "your_api_key_here".

**Solution**:

1. Get your API key from [console.anthropic.com](https://console.anthropic.com)
   - Log in → Settings → API Keys → Create Key

2. Open `config/.env` in a text editor

3. Replace the placeholder:
```
# Before:
ANTHROPIC_API_KEY=your_api_key_here

# After:
ANTHROPIC_API_KEY=sk-ant-api03-abc123def456...
```

4. Save and verify:
```bash
health-check.bat
```

---

## Engine Path Issues

### Error: "EngineDirs.txt not found"

**Cause**: Engine directory list hasn't been generated.

**Solution**:
```bash
fix-paths.bat
```

Follow the prompts to:
1. Auto-detect your UE5 installation, OR
2. Manually enter the path to your Engine folder

**Manual Path Entry Examples**:
```
C:\Program Files\Epic Games\UE_5.3\Engine
D:\UnrealEngine\UE_5.4\Engine
E:\UE5-Custom\Engine
```

---

### Error: "Template file not found"

**Cause**: `src/indexing/EngineDirs.template.txt` is missing.

**This is a critical error** - the template should always be in version control.

**Solution**:

1. Re-clone the repository:
```bash
git clone <repository-url> UE5-Query-Fresh
```

2. Or restore from Git:
```bash
git checkout HEAD -- src/indexing/EngineDirs.template.txt
```

3. Or manually re-run installation:
```bash
install.bat
```

---

### Error: "Template file doesn't contain {ENGINE_ROOT} placeholder"

**Cause**: Template file is corrupted or was incorrectly modified.

**Solution**:

1. Restore from Git:
```bash
git checkout HEAD -- src/indexing/EngineDirs.template.txt
```

2. Verify placeholder exists:
```bash
findstr "{ENGINE_ROOT}" src\indexing\EngineDirs.template.txt
```

3. If restoration fails, contact team lead for clean template.

---

### Error: "Template file appears empty or corrupted"

**Cause**: Template has fewer than 5 valid entries.

**Solution**:

1. Check file size:
```bash
dir src\indexing\EngineDirs.template.txt
```

2. If file is 0 bytes or very small, restore from Git:
```bash
git checkout HEAD -- src/indexing/EngineDirs.template.txt
```

3. Verify restoration:
```bash
health-check.bat
```

---

### Error: "None of the checked paths exist"

**Cause**: Wrong UE5 engine root was selected during configuration.

**Symptoms**:
- `fix-paths.bat` generates `EngineDirs.txt`
- But all paths in it are invalid

**Solution**:

1. Verify your actual UE5 installation location:
```bash
# Check common locations
dir "C:\Program Files\Epic Games"
dir "D:\Epic Games"
dir "C:\UnrealEngine"
```

2. Find the `Engine` folder. Verify it contains:
   - `Engine\Source`
   - `Engine\Plugins`
   - `Engine\Build`

3. Re-run path detection:
```bash
fix-paths.bat
```

4. When prompted, manually enter the FULL path to the Engine folder:
```
C:\Program Files\Epic Games\UE_5.3\Engine
```
(Note: Include "\Engine" at the end!)

5. Verify paths are now valid:
```bash
health-check.bat
```

---

### Error: "EngineDirs.txt appears empty or corrupted"

**Cause**: File was generated but contains no valid directory paths.

**Solution**:

1. Check file contents:
```bash
type src\indexing\EngineDirs.txt
```

2. If empty or has only comments, regenerate:
```bash
fix-paths.bat
```

3. If regeneration fails, the template may be corrupted:
```bash
git checkout HEAD -- src/indexing/EngineDirs.template.txt
fix-paths.bat
```

---

### Error: "Some paths may not exist on this system"

**Cause**: Template includes directories that don't exist in your UE5 version.

**Impact**: Low - only affects indexing completeness.

**Solution**:

This is usually a WARNING, not an ERROR. It means:
- Some UE5 directories in the template don't exist in your version
- Common with different UE5 versions (5.3 vs 5.4)
- Not a blocker - tool will index what exists

**To resolve** (optional):
1. Edit `src/indexing/EngineDirs.txt` manually
2. Comment out non-existent paths with `#`
3. Save and rebuild:
```bash
rebuild-index.bat --force
```

---

## Vector Store Issues

### Error: "Vector store exists but metadata missing"

**Cause**: Data corruption - `vector_store.npz` exists but `vector_meta.json` doesn't.

**Solution**:
```bash
rebuild-index.bat --force
```

This forces a complete rebuild, replacing corrupted files.

---

### Error: "Metadata exists but vector store missing"

**Cause**: Data corruption - `vector_meta.json` exists but `vector_store.npz` doesn't.

**Solution**:
```bash
rebuild-index.bat --force
```

---

### Error: "Vector store files are empty"

**Cause**: Build was interrupted or failed silently.

**Solution**:

1. Delete corrupted files:
```bash
del data\vector_store.npz
del data\vector_meta.json
```

2. Rebuild:
```bash
rebuild-index.bat --progress
```

Watch for errors during the build process.

---

### Error: "Vector store metadata is corrupted (invalid JSON)"

**Cause**: `vector_meta.json` is not valid JSON.

**Solution**:

1. Try to view the file:
```bash
type data\vector_meta.json
```

2. If it's clearly corrupted (random characters, truncated):
```bash
rebuild-index.bat --force
```

3. If the error persists after rebuild:
   - Check disk space: `dir data`
   - Check file permissions: Ensure you have write access to `data/` folder

---

### Error: "Vector/metadata mismatch"

**Cause**: Number of embeddings doesn't match number of metadata entries.

**Example**: `15000 embeddings != 15100 metadata entries`

**This indicates corruption.**

**Solution**:
```bash
rebuild-index.bat --force
```

**Prevention**: Always let `rebuild-index.bat` complete fully. Don't interrupt with Ctrl+C.

---

### Error: "Vector store contains NaN or Inf values"

**Cause**: Encoding model produced invalid embeddings.

**Rare - indicates serious issue.**

**Solution**:

1. Check if sentence-transformers is correctly installed:
```bash
.venv\Scripts\pip uninstall sentence-transformers
.venv\Scripts\pip install sentence-transformers --no-cache-dir
```

2. Rebuild:
```bash
rebuild-index.bat --force
```

3. If error persists:
   - Check for disk corruption: `chkdsk`
   - Check RAM: Run memory diagnostic
   - Contact team lead

---

### Error: "Failed to load vector store"

**Cause**: NumPy can't read `vector_store.npz`.

**Solution**:

1. Check file integrity:
```bash
dir data\vector_store.npz
```

File should be ~20-50 MB for full UE5 indexing.

2. If file size is 0 or suspiciously small:
```bash
rebuild-index.bat --force
```

3. If file size looks correct but still fails:
```bash
# Test NumPy installation
.venv\Scripts\python -c "import numpy as np; print(np.__version__)"

# Reinstall if needed
.venv\Scripts\pip install --upgrade numpy
```

---

## Query Runtime Issues

### Error: "No results found for query"

**Not an error** - query didn't match any indexed code.

**Troubleshooting**:

1. Verify vector store is built:
```bash
health-check.bat
```

2. Try a broader query:
```bash
# Too specific:
ask.bat "FVector::CrossProduct implementation details"

# Better:
ask.bat "FVector cross product"

# Even broader:
ask.bat "FVector"
```

3. Check what's indexed:
```bash
# Verify vector store has content
.venv\Scripts\python src\utils\verify_vector_store.py --verbose
```

4. If very few chunks indexed (< 1000):
   - Your `EngineDirs.txt` may have too few directories
   - Run: `fix-paths.bat` and ensure all relevant paths are included
   - Rebuild: `rebuild-index.bat --force`

---

### Error: Query hangs or is very slow

**Symptoms**: `ask.bat` runs for minutes without output.

**Causes**:
1. First query after boot (model loading)
2. Very large vector store (> 100k chunks)
3. Network issue (API call to Anthropic)

**Solutions**:

1. **First query is slow** (expected):
   - Sentence transformer model loads into RAM
   - Can take 30-60 seconds
   - Subsequent queries are faster

2. **All queries are slow**:
   - Check vector store size:
   ```bash
   dir data\vector_store.npz
   ```
   - If > 100 MB, consider indexing fewer directories
   - Edit `src/indexing/EngineDirs.txt` to remove non-essential paths

3. **API timeout**:
   - Check internet connection
   - Verify API key is valid:
   ```bash
   curl -X POST https://api.anthropic.com/v1/messages ^
     -H "x-api-key: YOUR_KEY_HERE" ^
     -H "anthropic-version: 2023-06-01" ^
     -H "content-type: application/json" ^
     -d "{\"model\":\"claude-3-haiku-20240307\",\"max_tokens\":1,\"messages\":[{\"role\":\"user\",\"content\":\"test\"}]}"
   ```

---

### Error: "API key invalid" or "Authentication failed"

**Cause**: Anthropic API key is incorrect or expired.

**Solution**:

1. Verify your API key at [console.anthropic.com](https://console.anthropic.com)
   - Check it's not expired
   - Check usage limits aren't exceeded

2. Update `config/.env` with fresh key

3. Test with verbose mode:
```bash
ask.bat "test query" --verbose
```

---

## Build/Index Issues

### Error: "Failed to scan directory: Access denied"

**Cause**: Tool doesn't have permission to read a UE5 directory.

**Solution**:

1. Run `rebuild-index.bat` as Administrator:
   - Right-click Command Prompt → Run as Administrator
   - Navigate to tool directory
   - Run: `rebuild-index.bat`

2. Or exclude problematic directories:
   - Edit `src/indexing/EngineDirs.txt`
   - Comment out restricted paths with `#`
   - Rebuild: `rebuild-index.bat --force`

---

### Error: "Out of memory" during indexing

**Cause**: Sentence transformer model + embeddings exceed RAM.

**Symptoms**:
- `rebuild-index.bat` crashes midway
- System becomes unresponsive
- "MemoryError" in output

**Solution**:

1. **Close other applications** to free RAM

2. **Index fewer directories**:
   - Edit `src/indexing/EngineDirs.txt`
   - Comment out non-essential paths (e.g., Plugins)
   - Keep only core Engine/Source directories
   - Rebuild: `rebuild-index.bat --force`

3. **Use --batch-size parameter** (if your version supports it):
   ```bash
   rebuild-index.bat --batch-size 16
   ```
   (Lower batch size = less RAM, but slower)

4. **Upgrade RAM** if indexing full UE5 source is required:
   - Minimum: 8 GB
   - Recommended: 16 GB

---

### Build completes but produces 0 chunks

**Symptoms**:
- `rebuild-index.bat` finishes without errors
- But health check shows 0 chunks or very few

**Cause**: No valid C++ files found in specified directories.

**Solution**:

1. Verify `EngineDirs.txt` has correct paths:
```bash
type src\indexing\EngineDirs.txt
```

2. Manually check a path exists:
```bash
dir "C:\Program Files\Epic Games\UE_5.3\Engine\Source\Runtime\Core"
```

3. If paths are wrong:
```bash
fix-paths.bat
rebuild-index.bat --force
```

4. Check for `.h` and `.cpp` files in those directories:
```bash
dir /s "C:\Program Files\Epic Games\UE_5.3\Engine\Source\Runtime\Core\*.h"
```

---

## Performance Issues

### Indexing takes over 30 minutes

**Expected duration**: 5-15 minutes for full UE5.3 source on modern hardware.

**If taking longer**:

1. **Check disk speed**:
   - SSD: 5-10 minutes
   - HDD: 15-30 minutes
   - Network drive: 30+ minutes (not recommended)

2. **Reduce scope**:
   - Edit `src/indexing/EngineDirs.txt`
   - Keep only directories you actually query (e.g., Core, CoreUObject, Engine)

3. **Check CPU usage**:
   - Open Task Manager during build
   - Sentence transformer should use 50-100% CPU
   - If low CPU usage, check for disk bottleneck

---

### Queries return irrelevant results

**Not a technical error** - indicates semantic search limitations.

**Improvement strategies**:

1. **Use more specific queries**:
```bash
# Vague:
ask.bat "vector"

# Specific:
ask.bat "FVector cross product"
```

2. **Use technical terms**:
```bash
# Generic:
ask.bat "how to move objects"

# Technical:
ask.bat "AActor SetActorLocation"
```

3. **Rebuild with better chunking** (advanced):
   - Edit `src/indexing/build_embeddings.py`
   - Adjust `CHUNK_SIZE` parameter (default: 1000 chars)
   - Smaller chunks = more precise, but larger index

---

## Git / Version Control Issues

### Error: ".gitignore is not blocking .venv"

**Problem**: `.venv` folder keeps appearing in `git status`.

**Solution**:

1. Verify `.gitignore` exists:
```bash
type .gitignore
```

2. Ensure it contains:
```
.venv/
config/.env
src/indexing/EngineDirs.txt
data/vector_store.npz
data/vector_meta.json
```

3. If `.venv` already tracked by Git:
```bash
git rm -r --cached .venv
git commit -m "Stop tracking .venv"
```

---

### Error: "Git LFS out of bandwidth"

**Cause**: GitHub LFS has monthly bandwidth limits.

**Solution**:

1. **Use build-per-machine approach** instead:
   - Each dev runs `rebuild-index.bat`
   - Don't commit `data/vector_store.npz`

2. **Or purchase more LFS bandwidth**:
   - GitHub Settings → Billing → Git LFS

3. **Or use alternative storage**:
   - Store vector store on shared network drive
   - Each dev copies locally before querying

---

### Merge conflict in EngineDirs.txt

**Cause**: Two devs modified `EngineDirs.txt` and it got committed.

**Prevention**: `EngineDirs.txt` should NEVER be committed (it's in `.gitignore`).

**Solution**:

1. Accept either version (doesn't matter):
```bash
git checkout --theirs src/indexing/EngineDirs.txt
```

2. Regenerate for your machine:
```bash
fix-paths.bat
```

3. Ensure `.gitignore` blocks it:
```bash
git check-ignore src/indexing/EngineDirs.txt
# Should output: src/indexing/EngineDirs.txt
```

---

## Advanced / Rare Issues

### ImportError: DLL load failed

**Cause**: Missing Visual C++ Redistributable or corrupted Python package.

**Solution**:

1. Install Visual C++ Redistributable:
   - Download from [Microsoft](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)
   - Install both x64 and x86 versions

2. Reinstall torch (used by sentence-transformers):
```bash
.venv\Scripts\pip uninstall torch
.venv\Scripts\pip install torch --no-cache-dir
```

3. Reinstall sentence-transformers:
```bash
.venv\Scripts\pip uninstall sentence-transformers
.venv\Scripts\pip install sentence-transformers --no-cache-dir
```

---

### UnicodeDecodeError during indexing

**Cause**: UE5 source file contains non-UTF8 characters.

**Rare** - most UE5 source is UTF-8.

**Solution**:

Currently, the tool skips files it can't decode. This error shouldn't block indexing.

If you see this and indexing stops:
1. Note which file caused the error
2. Open `src/indexing/build_embeddings.py`
3. Find the error handling for file reading
4. Ensure it has `errors='ignore'` or `errors='replace'`

---

### SSL Certificate Error

**Symptoms**: `ask.bat` fails with "SSL: CERTIFICATE_VERIFY_FAILED".

**Cause**: Corporate proxy or firewall blocking Anthropic API.

**Solutions**:

1. **Use system certificates**:
```bash
set REQUESTS_CA_BUNDLE=path\to\corporate\ca-bundle.crt
ask.bat "your query"
```

2. **Bypass SSL verification** (NOT recommended for production):
   - Edit `src/core/hybrid_query.py`
   - Add `verify=False` to API calls
   - This is a security risk - only use on trusted networks

3. **Work with IT**:
   - Request whitelisting for `api.anthropic.com`
   - Or use a different machine outside corporate network

---

## System Requirements

### Minimum Specs

- **OS**: Windows 10 or later
- **Python**: 3.8+
- **RAM**: 8 GB (16 GB recommended)
- **Disk**: 500 MB for tool + 500 MB for vector store
- **CPU**: Multi-core recommended (uses CPU for embeddings)

### Recommended Specs

- **OS**: Windows 11
- **Python**: 3.10+
- **RAM**: 16 GB
- **Disk**: SSD with 2+ GB free
- **CPU**: 4+ cores
- **Network**: Stable internet for API calls

---

## Getting Help

### Self-Service Diagnostics

1. **Health check**:
```bash
health-check.bat --verbose
```

2. **Vector store check**:
```bash
.venv\Scripts\python src\utils\verify_vector_store.py --verbose
```

3. **Test query with verbose output**:
```bash
ask.bat "test" --verbose
```

### Reporting Issues

When reporting issues, include:

1. Output of `health-check.bat --verbose`
2. Output of the failing command with full error message
3. Your Windows version: `ver`
4. Your Python version: `python --version`
5. Your UE5 version

### Escalation Path

1. Check this guide
2. Check `docs/TEAM_SETUP.md`
3. Check project issue tracker
4. Contact team lead
5. Create issue with diagnostic info

---

## Prevention Checklist

To avoid most issues:

- [ ] Run `health-check.bat` after initial setup
- [ ] Run `health-check.bat` after pulling changes
- [ ] Never commit `.venv`, `config/.env`, or `EngineDirs.txt`
- [ ] Keep API key secret (never share or commit)
- [ ] Let `rebuild-index.bat` complete fully (don't Ctrl+C)
- [ ] Use `--force` flag when rebuilding after path changes
- [ ] Keep backups of working `config/.env`
- [ ] Document your UE5 installation path

---

## Quick Reference: Common Commands

```bash
# Diagnose issues
health-check.bat --verbose

# Fix virtual environment
configure.bat

# Fix engine paths
fix-paths.bat

# Rebuild corrupted index
rebuild-index.bat --force

# Test vector store
.venv\Scripts\python src\utils\verify_vector_store.py

# Test query with details
ask.bat "test" --verbose

# Reinstall packages
.venv\Scripts\pip install -r requirements.txt --force-reinstall
```
