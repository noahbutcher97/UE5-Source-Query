# UE5 Source Query Tool - Deployment Guide

Quick guide for deploying the UE5 Source Query tool to new projects.

## Quick Start (Automated)

### Option 1: With GPU Acceleration (Recommended)
```bash
cd D:\DevTools\UE5-Source-Query
install.bat "D:\YourProject" --gpu --build-index
```

### Option 2: CPU Only
```bash
cd D:\DevTools\UE5-Source-Query
install.bat "D:\YourProject"
```

The installer will:
1. Create `Scripts/UE5-Source-Query/` directory structure
2. Copy all necessary files
3. Set up Python virtual environment
4. Install dependencies (with or without GPU support)
5. Create configuration template
6. Optionally build the vector index

## Post-Installation Setup

### 1. Configure API Key
Edit `Scripts/UE5-Source-Query/config/.env`:
```bash
ANTHROPIC_API_KEY=your_actual_api_key_here
```

Get your API key from: https://console.anthropic.com/

### 2. Build Vector Index (if not done during install)
```bash
cd YourProject\Scripts\UE5-Source-Query
ask.bat --build-index
```

**Build Times:**
- GPU (RTX 5090): ~2-3 minutes
- CPU: ~30-40 minutes

### 3. Test Installation
```bash
ask.bat "What is FVector"
```

## Manual Deployment (Advanced)

If you need custom installation or troubleshooting:

### 1. Create Directory Structure
```bash
cd YourProject
mkdir Scripts\UE5-Source-Query
cd Scripts\UE5-Source-Query
```

### 2. Copy Files
Copy from `D:\DevTools\UE5-Source-Query\`:
- `src/` directory (all source code)
- `ask.bat` (main entry point)
- `requirements.txt` (Python dependencies)
- `config/.env.template` (configuration template)

### 3. Set Up Python Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate (optional for manual operations)
.venv\Scripts\activate

# Install dependencies
pip install --upgrade pip

# For GPU support (CUDA 12.8)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# Install remaining dependencies
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
# Copy template
copy config\.env.template config\.env

# Edit config\.env and add your API key
notepad config\.env
```

### 5. Build Index
```bash
.venv\Scripts\python.exe src\indexing\build_embeddings.py --dirs-file src\indexing\EngineDirs.txt --force --verbose
```

## Configuration Options

### Environment Variables (config/.env)

**Required:**
- `ANTHROPIC_API_KEY` - Your Claude API key

**Optional:**
- `VECTOR_OUTPUT_DIR` - Custom vector store location (default: `./data`)
- `EMBED_MODEL` - Embedding model (default: `microsoft/unixcoder-base`)
- `ANTHROPIC_MODEL` - Claude model (default: `claude-3-haiku-20240307`)
- `UE_ENGINE_ROOT` - Custom UE5 install path

### Command-Line Options

**Building Index:**
```bash
# Build from engine directories list
ask.bat --build-index

# Custom output directory
.venv\Scripts\python.exe src\indexing\build_embeddings.py --output-dir custom/path --force

# Custom engine root
.venv\Scripts\python.exe src\indexing\build_embeddings.py --root "C:/CustomPath/UE_5.3/Engine" --force
```

**Querying:**
```bash
# Basic query
ask.bat "your question"

# Copy results to clipboard
ask.bat "your question" --copy

# Show more results
ask.bat "your question" --top-k 10

# Dry run (no API call)
ask.bat "your question" --dry-run
```

## Updating Existing Installation

### Update Source Code
```bash
cd YourProject\Scripts\UE5-Source-Query

# Backup your config
copy config\.env config\.env.backup

# Copy new source files from D:\DevTools\UE5-Source-Query\
xcopy /Y /E /I "D:\DevTools\UE5-Source-Query\src\*" "src\"
xcopy /Y "D:\DevTools\UE5-Source-Query\ask.bat" "."

# Restore config
copy config\.env.backup config\.env
```

### Update Python Dependencies
```bash
cd YourProject\Scripts\UE5-Source-Query
.venv\Scripts\pip install --upgrade -r requirements.txt
```

### Rebuild Index (if embedding model changed)
```bash
ask.bat --rebuild-index
```

## Troubleshooting

### "Virtual environment not found"
```bash
cd YourProject\Scripts\UE5-Source-Query
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

### "ANTHROPIC_API_KEY missing"
Edit `config/.env` and add your API key:
```
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### "Vector store missing"
Build the index:
```bash
ask.bat --build-index
```

### Dimension Mismatch Errors
Your index was built with a different embedding model. Rebuild:
```bash
.venv\Scripts\python.exe src\indexing\build_embeddings.py --force --verbose
```

### GPU Not Detected
Verify CUDA installation:
```bash
.venv\Scripts\python.exe -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}')"
```

If false, reinstall GPU support:
```bash
.venv\Scripts\pip install --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

### Path Issues After Moving Files
Update `.env` file paths and reinstall packages:
```bash
.venv\Scripts\pip install --force-reinstall --no-deps -r requirements.txt
```

## Directory Structure

After installation:
```
YourProject/
├── Scripts/
│   └── UE5-Source-Query/
│       ├── .venv/              # Python virtual environment
│       ├── config/
│       │   ├── .env            # Your configuration
│       │   └── .env.template   # Template
│       ├── data/               # Vector store files
│       │   ├── vector_store.npz
│       │   └── vector_meta.json
│       ├── logs/               # Log files
│       ├── src/
│       │   ├── core/           # Query engine
│       │   └── indexing/       # Index building
│       ├── ask.bat             # Main entry point
│       └── requirements.txt    # Python dependencies
```

## Integration with Project CLAUDE.md

Add to your project's `CLAUDE.md`:

```markdown
### UE5 Engine Source Query

Query UE5.3 engine source code using natural language:

```bash
# From project root
Scripts\UE5-Source-Query\ask.bat "your question here"
```

**Examples:**
- `ask.bat "What is FVector"`
- `ask.bat "How does UChaosVehicleWheeledMovementComponent work"`
- `ask.bat "FHitResult members" --copy --dry-run`

**See:** Scripts/UE5-Source-Query/README.md for full documentation
```

## Best Practices

1. **Share Vector Index**: Build once, commit `data/` directory to git LFS or shared storage
   - Saves 2-40 minutes per team member
   - Ensures consistency across team

2. **API Key Management**:
   - Add `config/.env` to `.gitignore`
   - Team members add their own API keys locally

3. **GPU Acceleration**:
   - Use `--gpu` flag during install if available
   - Massive speedup for index building (10x faster)

4. **Custom Indexes**:
   - Use `--output-dir` to create project-specific indexes
   - Keep engine index separate from project code index

5. **Regular Updates**:
   - Update source code when new features are added
   - Rebuild index after UE5 engine updates

## Support

For issues or questions:
- Main repo: `D:\DevTools\UE5-Source-Query\`
- Documentation: See comprehensive guide in project docs/Guides/
- Report issues to your project's primary maintainer

## Version History

- **v2.0**: GPU acceleration, modular configuration, improved deployment
- **v1.0**: Initial release with CPU-only indexing
