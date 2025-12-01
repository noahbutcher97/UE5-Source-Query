# UE5 Source Query - GEMINI Context

## Project Overview
**UE5 Source Query** is an intelligent hybrid search system designed for Unreal Engine 5.3 source code. It combines regex-based definition extraction with semantic search (embeddings) to provide precise and relevant results for developers querying the UE5 codebase.

**Key Features:**
*   **Hybrid Search:** Intelligently routes queries between definition extraction (precise) and semantic search (conceptual).
*   **Definition Extraction:** Fast regex-based extraction for C++ structs, classes, enums, and functions.
*   **Semantic Search:** Uses `unixcoder-base` embeddings to understand code concepts.
*   **GUI Tools:** User-friendly Tkinter-based GUIs for installation, configuration, and management.
*   **Team Ready:** Supports Git LFS for shared indices and per-machine configuration.

## Tech Stack
*   **Language:** Python 3.11+
*   **AI/ML:** `sentence-transformers` (UnixCoder), `anthropic` (Claude API for reasoning).
*   **Vector Store:** NumPy-based custom store (`vector_store.npz`).
*   **GUI:** Python `tkinter`.
*   **Shell:** Batch scripts (`.bat`) for Windows integration.

## Key Commands

### User & Usage
*   **`ask.bat "query"`**: The main entry point for querying the system.
    *   `ask.bat --build-index`: Triggers the index build process.
    *   `ask.bat "FHitResult" --copy`: Copies results to clipboard.
*   **`install.bat`**: Launches the GUI installer for easy deployment.
*   **`configure.bat`**: Runs the configuration wizard (API keys, UE5 paths).
*   **`manage.bat`**: Opens the GUI management dashboard.

### Maintenance & Dev
*   **`rebuild-index.bat`**: Rebuilds the vector store from source.
*   **`health-check.bat`**: comprehensive system diagnostics.
*   **`fix-paths.bat`**: Regenerates `EngineDirs.txt` based on the current machine's UE5 installation.

## Project Architecture

### Directory Structure
*   **`src/core/`**: The heart of the query logic.
    *   `hybrid_query.py`: Orchestrates the search strategies.
    *   `query_intent.py`: Classifies user queries (Definition vs. Semantic).
    *   `definition_extractor.py`: Regex patterns for C++ parsing.
*   **`src/indexing/`**: Tools for building the search index.
    *   `build_embeddings.py`: Generates embeddings from source files.
    *   `metadata_enricher.py`: Adds semantic tags (entities, macros) to metadata.
*   **`installer/`**: Deployment scripts and the GUI installer logic.
*   **`data/`**: Stores the generated `vector_store.npz` and `vector_meta.json`.

### Workflow
1.  **Indexing:** `build_embeddings.py` scans UE5 source directories (defined in `EngineDirs.txt`), chunks code, generates embeddings using `unixcoder-base`, and saves them to `data/`.
2.  **Querying:** `ask.bat` calls `src/core/hybrid_query.py`.
3.  **Routing:** `query_intent.py` analyzes the query.
    *   If "Definition" -> uses `definition_extractor.py` (fast).
    *   If "Semantic" -> uses `query_engine.py` (vector search).
    *   If "Hybrid" -> combines both.

## Development Conventions
*   **Virtual Environment:** Strictly relies on `.venv`. Scripts automatically check/activate it.
*   **Configuration:** Secrets live in `config/.env`. **NEVER commit this file.**
*   **Pathing:** Machine-specific paths are generated into `src/indexing/EngineDirs.txt`. This file is ignored by git.
*   **Testing:** Use `health-check.bat` and `src/utils/verify_*.py` scripts to validate changes.
