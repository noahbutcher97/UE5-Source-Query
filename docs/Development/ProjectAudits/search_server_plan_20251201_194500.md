# Search Server Upgrade Plan
**Date:** 2025-12-01
**Status:** Implementation Phase

## 1. Current State Analysis (`src/server/retrieval_server.py`)
*   **Outdated Logic:** It uses a primitive `RetrievalCore` class that implements basic cosine similarity but ignores all the advanced logic we built in `FilteredSearch.py` and `hybrid_query.py`.
*   **Missing Features:**
    *   No **Hybrid Query** support (Definition Extraction + Semantic Search).
    *   No **Filtered Search** support (Entity Boosting, Macro Boosting).
    *   No **Query Intent Analysis**.
    *   Hardcoded paths (`SCRIPT_DIR / "vector_store.npz"`) instead of respecting `.env` config.
*   **Security:** Binds to `127.0.0.1` by default (Good), but hardcoded port `8765`.

## 2. Goal: "Agent-Ready" Search Server
We want `retrieval_server.py` to be a persistent version of `hybrid_query.py`. It should expose the *exact same* functionality but keep the model loaded in RAM.

## 3. Implementation Plan

### Step 1: Refactor `RetrievalCore` to use `HybridQuery` logic
Instead of reimplementing search, `RetrievalCore` should import and use `FilteredSearch` and `QueryIntentAnalyzer`.

*   **Imports:**
    ```python
    from core.query_intent import QueryIntentAnalyzer
    from core.filtered_search import FilteredSearch
    from core import query_engine
    # ...
    ```
*   **Initialization:**
    *   Load `.env` to get paths (`VECTOR_OUTPUT_DIR`).
    *   Load embeddings and metadata once.
    *   Initialize `FilteredSearch` instance.
    *   Initialize `SentenceTransformer` model.
    *   Initialize `QueryIntentAnalyzer` (if needed, or just instantiate on request).

### Step 2: Update Request Handler (`/search` endpoint)
*   **Parameters:**
    *   `q` (query string)
    *   `top_k` (int)
    *   `scope` (engine/project/all) - *New!*
    *   `type` (auto/hybrid/semantic/definition) - *New!*
*   **Response:**
    *   Return the exact JSON structure that `hybrid_query.py --json` returns.

### Step 3: Create `serve.bat`
*   A batch script to launch the server easily.

### Step 4: Update `ask.bat` (Client)
*   Try to `curl` localhost:8765/search first.
*   If successful, parse JSON and print.
*   If failed (connection refused), fall back to slow `python hybrid_query.py`.

## 4. Specific Changes to `src/server/retrieval_server.py`

```python
# Pseudo-code for new search method
def search(self, query, top_k, scope, search_type):
    # 1. Analyze Intent (if type='auto')
    # 2. Route to FilteredSearch or DefinitionExtractor
    # ... logic mirrored from hybrid_query.py ...
    return results_dict
```

Wait, `hybrid_query.py` is a script, not a class. I should extract the logic from `hybrid_query.py` into a reusable `HybridQueryEngine` class so both the CLI script and the Server can use it without code duplication.

**Revised Plan:**
1.  **Refactor `src/core/hybrid_query.py`:** Extract the main logic into a class `HybridQueryEngine`.
2.  **Update `src/server/retrieval_server.py`:** Import `HybridQueryEngine` and wrap it in the HTTP server.
3.  **Update `ask.bat`:** Add the client logic.

This is cleaner and more maintainable.

# Suggestions List (Actionable)

*   [ ] **Refactor:** Modify `src/core/hybrid_query.py` to create `class HybridQueryEngine`.
*   [ ] **Update:** Rewrite `src/server/retrieval_server.py` to use `HybridQueryEngine`.
*   [ ] **Create:** `tools/serve.bat`.
*   [ ] **Update:** `ask.bat` to try server first.
