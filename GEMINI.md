# UE5 Source Query - GEMINI Context

## Project Overview
**UE5 Source Query** is an intelligent hybrid search system designed for Unreal Engine 5.3 source code. It combines regex-based definition extraction with semantic search (embeddings) to provide precise and relevant results for developers querying the UE5 codebase.

**Key Features:**
*   **Hybrid Search:** Intelligently routes queries between definition extraction (precise) and semantic search (conceptual).
*   **Definition Extraction:** Fast regex-based extraction for C++ structs, classes, enums, and functions.
*   **Semantic Search:** Uses `unixcoder-base` embeddings to understand code concepts.
*   **GUI Tools:** User-friendly Tkinter-based GUIs for installation, configuration, and management.
*   **Team Ready:** Supports Git LFS for shared indices and per-machine configuration.

## Core Mandates
- **Package Imports**: Use absolute package imports (`from ue5_query.core...`). NEVER use relative imports.
- **Async First**: All new server endpoints MUST be `async` using FastAPI.
- **Type Safety**: Use Pydantic models for all API request/response structures.
- **Testing**: Run `python tests/test_agent_integration.py` before committing any core query changes.

## Tech Stack
- **Language:** Python 3.11+ (Strictly `.venv` managed).
- **AI/ML:** `sentence-transformers` (UnixCoder-base, 768 dims), `anthropic` (Claude-3 Haiku for reasoning).
- **Vector Store:** NumPy-based (`vector_store.npz`) -> Migrating to **FAISS**.
- **Metadata**: JSON-based (`vector_meta.json`) -> Migrating to **SQLite**.
- **Server:** FastAPI + Uvicorn (Replaces legacy `http.server`).

## Key Commands

### User & Usage
*   **`ask.bat "query"`**: The main entry point for querying the system.
    *   `ask.bat "FHitResult members"` - Human-readable text output
    *   `ask.bat "FHitResult" --format json` - Structured JSON output
*   **`launcher.bat`**: Opens the UnifiedDashboard GUI.

### Maintenance & Dev
*   **`rebuild-index.bat`**: Rebuilds the vector store from source.
*   **Server Mode**: `python -m ue5_query.server.retrieval_server` (Legacy)
*   **New API**: `python -m ue5_query.server.app` (v2.1 Target)

## v2.1 Refactoring Roadmap (Current Focus)
As of **February 4, 2026**, the project has completed a comprehensive 4-dimensional audit.

**Audit Reports (docs/user/audits/):**
-   **Audit_API**: FastAPI, Redis, REST.
-   **Audit_Database**: SQLite, B-Tree, FTS5.
-   **Audit_Patterns**: Template Method, Rule Engine.
-   **Audit_System**: Docker, Celery, VRAM Isolation.

## Project Architecture

### Directory Structure
*   **`ue5_query/core/`**: Intent classification and search coordination.
*   **`ue5_query/indexing/`**: Source discovery and embedding generation.
*   **`ue5_query/utils/`**: Configuration and diagnostics.
*   **`ue5_query/server/`**: REST API layer.

### Workflow
1.  **Indexing:** `ue5_query/indexing/build_embeddings.py` scans directories, chunks code, and generates embeddings.
2.  **Querying:** `ask.bat` calls `ue5_query/core/hybrid_query.py`.
3.  **Routing:** `query_intent.py` analyzes the query.
    *   If "Definition" -> uses `definition_extractor.py`.
    *   If "Semantic" -> uses `query_engine.py` (vector search).
    *   If "Hybrid" -> combines both.

## Development Conventions
*   **Virtual Environment:** Strictly relies on `.venv`. Scripts automatically check/activate it.
*   **Configuration:** Secrets live in `config/.env`. **NEVER commit this file.**
*   **Agent Integration:** Run `tests/test_agent_integration.py` to verify that the JSON/XML/Code output formats expected by AI agents are working correctly.
