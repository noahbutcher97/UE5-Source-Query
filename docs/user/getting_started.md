# User Guide

This guide covers the day-to-date usage of the UE5 Source Query tool for human developers.

## 🖥️ Dashboard (GUI)

The Dashboard (`launcher.bat`) is the control center for the tool.

### 1. Source Manager
Configure what code gets indexed.
*   **Engine Source:** Auto-detected. You can add/remove specific engine modules to save space.
*   **Project Source:** Add your game's `Source` folder here.
*   **Index Management:**
    *   **Update Index (Incremental):** Fast. Scans for changed files and updates them. Use this daily.
    *   **Full Rebuild (Force):** Wipes and rebuilds the index from scratch. Use this if the index seems corrupted or after major engine upgrades.
    *   **Index Docs:** Check this to include `.md`, `.pdf`, `.docx` files in the index.

### 2. Configuration
*   **API Key:** Set your Anthropic API key here (required for "Explain Code" features, optional for search).
*   **Engine Path:** Verify your UE5 installation location.
*   **GPU Optimization:** Adjust batch size. Set to **16** for RTX 5090 (Blackwell), **32+** for older GPUs.

### 3. Diagnostics
*   **GPU Status:** Verifies PyTorch can see your CUDA device.
*   **JIT Status:** Reports if you are running in PTX Compatibility Mode (common for 50-series cards on older PyTorch versions).

---

## 💻 CLI Usage

The `ask.bat` command is the primary way to search.

### Basic Search
```batch
ask.bat "how to spawn actor"
```

### Filtering
Narrow down results to specific scopes or file types.

```batch
# Only search my project code
ask.bat "inventory system" --scope project

# Only search C++ headers
ask.bat "UInventoryComponent" --extensions .h
```

### Interactive Mode
Launch a shell to run multiple queries without reloading the AI models (Instant response).

```batch
ask.bat -i
# or
ask.bat --interactive
```

**Commands inside interactive mode:**
*   `query...` - Run a search
*   `exit` - Quit

### Formatted Output
Get output ready for copy-pasting or piping.

```batch
# Output raw code snippets only
ask.bat "FVector::DotProduct" --format code

# Output JSON (for tools)
ask.bat "query" --format json
```

---

## 🌐 Server Mode

For teams or heavy usage, you can run the retrieval server.

```batch
python -m ue5_query.server.retrieval_server
```

This keeps the index loaded in RAM, providing **instant** results to any tool that hits `http://localhost:8765/search`.
