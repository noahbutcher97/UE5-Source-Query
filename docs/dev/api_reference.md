# API Reference

This document outlines the Python API for the `ue5_query` package.

## Core Components

### `ue5_query.core.hybrid_query.HybridQueryEngine`

The main entry point for search operations.

```python
from ue5_query.core.hybrid_query import HybridQueryEngine
from pathlib import Path

# Initialize (loads index from default location)
engine = HybridQueryEngine(Path("."))

# Run Query
results = engine.query(
    question="How to trace line",
    top_k=5,
    scope="engine" # 'engine', 'project', 'all'
)

# Access Results
for hit in results['combined_results']:
    print(f"{hit['score']}: {hit['path']}")
```

### `ue5_query.core.filtered_search.FilteredSearch`

Low-level vector search with metadata filtering.

```python
# Advanced Filtering
results = engine.filtered_search.search(
    query_vec=vector,
    top_k=10,
    origin='project',
    query_type='definition'
)
```

---

## Utility Components

### `ue5_query.utils.source_manager.SourceManager`

Manage indexed directories programmatically.

```python
from ue5_query.utils.source_manager import SourceManager
from pathlib import Path

mgr = SourceManager(Path("ue5_query/indexing"))

# Add a path
mgr.add_project_dir("C:/Projects/MyGame/Source")

# Remove a path
mgr.remove_project_dir("C:/Projects/MyGame/Source")
```

### `ue5_query.utils.gpu_helper`

Hardware acceleration detection.

```python
from ue5_query.utils.gpu_helper import is_cuda_available

if is_cuda_available():
    print("GPU acceleration ready")
```

---

## Data Structures

### `QueryResult` (Dict)

```json
{
  "question": "query string",
  "intent": {
    "type": "definition",
    "confidence": 0.9,
    "entity_name": "FHitResult"
  },
  "definition_results": [...],
  "semantic_results": [...],
  "combined_results": [...],
  "timing": { "total_s": 1.2 }
}
```

### `SemanticResult` (Dict)

```json
{
  "path": "Engine/Source/...",
  "score": 0.85,
  "chunk_index": 0,
  "text_snippet": "void Function() { ... }"
}
```