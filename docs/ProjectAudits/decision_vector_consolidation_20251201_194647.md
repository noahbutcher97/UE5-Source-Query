# Decision Record: Vector Store Consolidation
**Date:** 2025-12-01
**Status:** Analysis & Decision

## 1. Current State
*   **Indexing Phase:**
    *   `vector_store.npz`: Contains the embeddings (numeric vectors) and an array of file paths/indices.
    *   `vector_meta.json`: Contains basic metadata (path, chunk_index, chars) used to map embeddings back to text.
    *   `vector_meta_enriched.json`: Created by `metadata_enricher.py` (previously separate, now integrated). Contains the same items as `vector_meta.json` but with added fields: `entities`, `entity_types`, `has_uclass`, etc.
*   **Querying Phase:**
    *   `hybrid_query.py` loads `vector_store.npz`.
    *   It then checks for `vector_meta_enriched.json`. If found, it uses it. If not, it falls back to `vector_meta.json`.

## 2. Analysis
With the recent integration of **Single-Pass Indexing** in `build_embeddings.py`, the enrichment happens *during* the creation of the metadata list.

*   **Redundancy:** `build_embeddings.py` builds `new_meta` which includes enrichment data. It then writes this to `vector_meta.json`.
*   **Legacy Artifact:** `vector_meta_enriched.json` was an artifact of the two-pass system (where pass 1 wrote basic meta, and pass 2 read it, enriched it, and wrote a new file).
*   **Confusion:** Having two metadata files (`vector_meta.json` and `vector_meta_enriched.json`) is confusing and wasteful. If `vector_meta.json` is already enriched (which it is now), the second file is redundant.

## 3. Downstream Impact
*   **`hybrid_query.py`:**
    *   Currently logic:
        ```python
        enriched_meta_path = TOOL_ROOT / "data" / "vector_meta_enriched.json"
        if has_enriched:
            enriched_meta = json.loads(...)
        else:
            enriched_meta = meta  # (loaded from vector_meta.json)
        ```
    *   If we stop producing `vector_meta_enriched.json`, `hybrid_query.py` will fall back to `vector_meta.json`.
    *   **Crucial Check:** Does `vector_meta.json` actually contain the enrichment data?
        *   Yes, because we updated `build_embeddings.py` to merge `enrichment` into `meta_item` before appending to `new_meta`.
        *   So `vector_meta.json` *is* the enriched metadata now.

*   **`FilteredSearch`:** Relies on `entities` keys being present in the metadata list passed to it. It doesn't care about the filename.

## 4. Decision: Consolidate
We will **consolidate to a single metadata file: `vector_meta.json`**.

*   **Action:** Update `hybrid_query.py` to stop looking for `vector_meta_enriched.json` and trust `vector_meta.json` as the source of truth.
*   **Cleanup:** Delete `vector_meta_enriched.json`.
*   **Benefit:** Simpler architecture, less disk usage, less confusion.

# Consolidated Suggestions List (Updated)

*   [x] **Optimization:** Merge enrichment into `build_embeddings.py` (Completed).
*   [ ] **Cleanup:** Update `src/core/hybrid_query.py` to remove the check for `vector_meta_enriched.json`.
*   [ ] **Cleanup:** Delete `data/vector_meta_enriched.json`.
*   [ ] **Performance:** Implement "Search Server" mode.
*   [ ] **Security:** Hardcode `127.0.0.1` in `retrieval_server.py`.
