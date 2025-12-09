# GPU Acceleration Setup

This guide explains how to enable GPU acceleration for embedding generation, which provides **6-10x speedup** over CPU.

## Prerequisites

- NVIDIA GPU with CUDA support
- CUDA drivers installed (check with `nvidia-smi`)
- Python virtual environment

## Installation

### 1. Install PyTorch with CUDA Support

```bash
cd D:/DevTools/UE5-Source-Query
.venv/Scripts/python.exe -m pip install --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```

### 2. Verify GPU is Available

```bash
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
```

Expected output:
```
CUDA available: True
Device: NVIDIA GeForce RTX 5090 Laptop GPU
```

## Usage

GPU acceleration is **enabled by default** (auto-detection). The build script will automatically use GPU if available.

### Manual Control

You can control GPU usage via environment variable:

```bash
# Auto-detect GPU (default)
python src/indexing/build_embeddings.py --dirs-file src/indexing/EngineDirs.txt --force --verbose

# Force GPU usage (fails if GPU unavailable)
set USE_GPU=true
python src/indexing/build_embeddings.py --dirs-file src/indexing/EngineDirs.txt --force --verbose

# Force CPU usage
set USE_GPU=false
python src/indexing/build_embeddings.py --dirs-file src/indexing/EngineDirs.txt --force --verbose
```

## Performance Comparison

| Hardware | Speed | Time (17,799 chunks) |
|----------|-------|----------------------|
| CPU (Intel i9) | ~7-8 chunks/sec | ~35-40 minutes |
| GPU (RTX 5090) | ~50-70 chunks/sec | ~4-6 minutes |

**Expected Speedup:** 6-10x faster with GPU

## Troubleshooting

### "CUDA out of memory"

Reduce batch size in `build_embeddings.py`:
```python
EMBED_BATCH = 16  # Default: 32
```

### "CUDA not available" but GPU is installed

1. Check CUDA drivers: `nvidia-smi`
2. Reinstall PyTorch with correct CUDA version
3. Check PyTorch installation: `python -c "import torch; print(torch.version.cuda)"`

### Slow performance with GPU

- Ensure you're using CUDA-enabled PyTorch (not CPU-only version)
- Check GPU utilization: `nvidia-smi -l 1` (should show ~80-90% utilization)
- Close other GPU-intensive applications

## Alternative Models

The current model (`microsoft/unixcoder-base`) is code-trained but not sentence-transformers optimized. Consider these alternatives:

### For Better Performance (same quality)
```bash
# Set in .env or environment
export EMBED_MODEL="sentence-transformers/all-mpnet-base-v2"
```
- 768 dimensions
- Faster inference
- General-purpose (not code-specific)

### For Better Code Understanding
```bash
export EMBED_MODEL="microsoft/codebert-base"
```
- 768 dimensions
- Purpose-built for code
- Better semantic understanding

### For Best Quality (slower)
```bash
export EMBED_MODEL="BAAI/bge-large-en-v1.5"
```
- 1024 dimensions
- State-of-the-art retrieval
- Requires more VRAM

## Notes

- GPU acceleration only affects **embedding generation** (indexing phase)
- **Query performance** is unaffected (queries are fast on CPU)
- First run downloads model (~500MB-1GB) to cache
- VRAM usage: ~2-4GB for unixcoder-base with batch size 32