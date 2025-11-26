# Deferred Tasks for UE5 Source Query System

This document tracks planned enhancements that are deferred until after initial deployment and validation.

## Priority: Medium

### 1. Smart Incremental Cleanup for Removed Directories

**Status:** Deferred pending production validation
**Estimated Effort:** 15-45 minutes
**Complexity:** Low-Medium

**Description:**
Currently, `--incremental` mode only handles:
- ✅ Adding new directories/files (works perfectly)
- ✅ Detecting modified files by hash (works perfectly)
- ❌ Removing embeddings for deleted directories (requires `--force` rebuild)

**Proposed Solution:**
Add automatic pruning of embeddings from removed directories during incremental builds.

**Implementation Options:**

**Option A: Simple Path-Based Pruning (15-20 min)**
```python
def prune_removed_files(existing_meta, current_files, verbose=False):
    """Remove embeddings for files no longer in discovery set."""
    current_paths = {str(f) for f in current_files}
    keep_indices = [i for i, m in enumerate(existing_meta)
                   if m["path"] in current_paths]

    if verbose:
        removed = len(existing_meta) - len(keep_indices)
        print(f"Pruned {removed} chunks from removed files")

    return keep_indices
```

**Option B: Directory-Aware Tracking (30-45 min)**
- Add `source_root` field to chunk metadata
- Track which directory each file came from
- More precise pruning, better for complex scenarios

**When to Implement:**
- User frequently switches between different directory sets
- Automated CI/CD pipelines with changing indexing scope
- Vector store grows large enough that `--force` rebuilds become slow (>10 min)

**Current Workaround:**
Use `--force` flag to rebuild from scratch (acceptable for current 2.2K files, ~2-5 min rebuild)

---

### 2. Project-Scope Separate Embedded Store

**Status:** Deferred pending Engine index validation
**Estimated Effort:** 2-3 hours
**Complexity:** Medium

**Description:**
Create a separate vector store for project-specific code (hijack_prototype) that can be queried independently or in combination with the Engine index.

**Use Cases:**
- Query only project code: "how does vehicle turret aiming work in our project"
- Query Engine + project: "how do I use UChaosWheeledVehicleMovementComponent in our codebase"
- Hybrid queries: Engine definitions + project usage examples

**Proposed Architecture:**

```
D:\DevTools\UE5-Source-Query\data\
├── engine\
│   ├── vector_store.npz           # Engine source embeddings
│   ├── vector_meta.json
│   └── vector_meta_enriched.json
└── project\
    ├── vector_store.npz           # Project source embeddings
    ├── vector_meta.json
    └── vector_meta_enriched.json
```

**Implementation Steps:**

1. **Multi-Store Configuration** (30 min):
```python
# config.py
STORES = {
    "engine": {
        "data_dir": Path("data/engine"),
        "sources": "src/indexing/EngineDirs.txt",
        "extensions": {".cpp", ".h", ".hpp", ".inl"}
    },
    "project": {
        "data_dir": Path("data/project"),
        "sources": "D:/UnrealProjects/5.3/hijack_prototype/hijack_prototype/Source",
        "extensions": {".cpp", ".h", ".hpp", ".inl"}
    }
}
```

2. **Multi-Store Query Engine** (1 hour):
```python
def query_multi_store(query: str, stores: List[str] = ["engine", "project"],
                     top_k_per_store: int = 3):
    """Query multiple stores and merge results."""
    all_results = []

    for store_name in stores:
        store_config = STORES[store_name]
        results = query_single_store(query, store_config, top_k_per_store)

        # Tag results with source
        for r in results:
            r["store"] = store_name

        all_results.extend(results)

    # Re-rank combined results
    return sorted(all_results, key=lambda x: x["score"], reverse=True)
```

3. **CLI Integration** (30 min):
```bash
# Query only Engine
python query.py "FHitResult members" --store engine

# Query only project
python query.py "turret aiming" --store project

# Query both (default)
python query.py "vehicle wheel setup" --store engine,project

# Build project index
python build_embeddings.py --store project --dirs "D:/UnrealProjects/.../Source" --force
```

4. **Hybrid Query Strategies** (30 min):
```python
STRATEGIES = {
    "independent": lambda q, stores: query_multi_store(q, stores),  # Simple merge
    "cascade": lambda q, stores: cascade_query(q, stores),          # Try engine first, fallback to project
    "weighted": lambda q, stores: weighted_query(q, stores, engine_weight=0.6, project_weight=0.4)
}
```

**Benefits:**
- ✅ Faster project-only queries (smaller index)
- ✅ Separate update cycles (Engine stable, project changes frequently)
- ✅ Better relevance (project code weighted higher for project-specific queries)
- ✅ Reduced noise (Engine code doesn't pollute project queries)

**When to Implement:**
- After confirming Engine index works well in production
- When project codebase grows significantly (>100 files)
- When users need project-specific query performance

**Current Workaround:**
Include project files in EngineDirs.txt and use unified index

---

### 3. Query Strategy Auto-Selection

**Status:** Deferred - low priority
**Estimated Effort:** 1-2 hours
**Complexity:** Medium

**Description:**
Automatically detect whether a query should use:
- Definition extraction only
- Semantic search only
- Hybrid approach
- Engine store, project store, or both

**Example:**
```python
query = "FHitResult ImpactPoint"
# → Auto-detect: DEFINITION query, ENGINE store

query = "how does our turret aim at targets"
# → Auto-detect: SEMANTIC query, PROJECT store

query = "UChaosWheeledVehicleMovementComponent usage in our game"
# → Auto-detect: HYBRID query, ENGINE + PROJECT stores
```

---

## Review Schedule

**Next Review:** After 2-4 weeks of production use

**Criteria for Promotion to Active:**
1. Users request the feature multiple times
2. Current workarounds become painful
3. Performance degrades without the feature
4. Clear use cases emerge from production usage

**Notes:**
- Prioritize stability and correctness over features
- Gather real-world usage data before implementing
- Re-evaluate complexity estimates based on codebase evolution