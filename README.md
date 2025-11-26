# UE5 Engine Source Query System

**Intelligent hybrid search for Unreal Engine 5.3 source code** - Combines precise definition extraction with semantic search.

## Quick Start

```bash
# Basic queries
python src/core/hybrid_query.py "struct FHitResult" --show-reasoning
python src/core/hybrid_query.py "FHitResult members" --show-reasoning
python src/core/hybrid_query.py "how does collision detection work" --show-reasoning

# Definition extraction only
python src/core/definition_extractor.py struct FHitResult
python src/core/definition_extractor.py class AActor
python src/core/definition_extractor.py enum ECollisionChannel

# Fuzzy matching (typos)
python src/core/definition_extractor.py struct HitRes --fuzzy
```

## Features

### ✅ Implemented

| Feature | Status | Description |
|---------|--------|-------------|
| **Hybrid Routing** | ✅ Complete | Automatically routes to best search strategy |
| **Query Intent Analysis** | ✅ Complete | Detects definition vs semantic queries |
| **Definition Extraction** | ✅ Complete | Precise struct/class/enum/function extraction |
| **Query Enhancement** | ✅ Complete | Adds code keywords automatically |
| **Fuzzy Matching** | ✅ Complete | Levenshtein distance for typos |
| **LRU Caching** | ✅ Complete | Caches query embeddings (64 item cache) |
| **Metadata Enrichment** | ✅ Complete | Tags entities, types, UE5 macros |
| **Filtered Search** | ✅ Complete | Filter by entity, type, macros |
| **Relevance Boosting** | ✅ Complete | Boost scores for matching entities |

### 📊 Results

**Before (Pure Semantic Search):**
```
Query: "FHitResult members"
Results:
  ❌ CollectionSelectionFacade.h (score: 0.377)
  ❌ ChaosResultsManager.h (score: 0.370)
```

**After (Hybrid System):**
```
Query: "FHitResult members"
Results:
  ✅ FHitResult struct (HitResult.h:19-288)
     - 25 members extracted
     - ImpactPoint, ImpactNormal, FaceIndex, Time...
  ✅ Relevant semantic supplements
Time: 1.25s
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Query                            │
│            "FHitResult members"                          │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│              QueryIntentAnalyzer                         │
│  • Detects query type (DEFINITION/SEMANTIC/HYBRID)      │
│  • Extracts entity names using UE5 conventions          │
│  • Enhances query with code keywords                    │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
        ┌──────────┴──────────┐
        │                     │
        ▼                     ▼
┌───────────────┐    ┌────────────────┐
│  DEFINITION   │    │   SEMANTIC     │
│   Extractor   │    │    Search      │
│               │    │                │
│ Regex patterns│    │  Embeddings    │
│ Brace matching│    │  Cosine sim    │
│   0.3-0.4s    │    │    0.8-1.0s    │
└───────┬───────┘    └────────┬───────┘
        │                     │
        └──────────┬──────────┘
                   ▼
        ┌──────────────────────┐
        │  Combined Results    │
        │  (Definition first)  │
        └──────────────────────┘
```

## All 7 Phases Implemented!

### ✅ Phase 1: Hybrid Routing
**Status:** Complete

Automatic query routing based on intent:
- Explicit definitions → Definition extraction
- Conceptual questions → Semantic search
- Entity + keywords → Hybrid (both methods)

### ✅ Phase 2: Query Enhancement
**Status:** Complete with member extraction

```python
"FHitResult members"
→ "FHitResult members struct UPROPERTY fields members"

"FHitResult ImpactPoint ImpactNormal"
→ "FHitResult ImpactPoint ImpactNormal struct UPROPERTY fields ImpactPoint ImpactNormal"
```

### ✅ Phase 3: Metadata Tagging
**Status:** Complete with enrichment tool

```bash
# Enrich metadata with entity information
python src/indexing/metadata_enricher.py data/vector_meta.json

# Creates: data/vector_meta_enriched.json
# Tags each chunk with:
# - Detected entities (FHitResult, FVector, etc.)
# - Entity types (struct, class, enum)
# - UE5 macros (UPROPERTY, UCLASS, etc.)
# - File type (header vs implementation)
```

**Benefits:**
- Filter: `entity="FHitResult"` only returns chunks with FHitResult
- Boost: Chunks with matching entities score 20% higher
- Macro filtering: Find all UPROPERTY declarations

### ✅ Phase 4: Re-ranking (via Boosting)
**Status:** Implemented as relevance boosting

```python
from src.core.filtered_search import FilteredSearch

# Boost chunks containing specific entities
results = search.search(
    query_vec,
    boost_entities=["FHitResult", "FVector"],  # 20% boost
    boost_macros=True  # 15% boost for UE5 macros
)
```

### ✅ Phase 5: Logical Compensation
**Status:** Complete - Dramatic accuracy improvements

Structural boosts compensate for embedding model limitations:

| Boost Type | Multiplier | Application |
|------------|------------|-------------|
| File Path Matching | 3.0x | Entity name in filename |
| Header Prioritization | 2.5x | .h files on definition queries |
| Implementation Penalty | 0.5x | .cpp files on definition queries |
| Entity Co-occurrence | 0.1x | Missing target entity (penalty) |
| Multi-entity Bonus | 1.3x | >3 entities (rich definitions) |

**Results:**
- FHitResult query: rank 753 → rank 1 (10x improvement)
- Score: 0.300 → 3.055

### ✅ Phase 6: Semantic Chunking
**Status:** Complete with configurable boundaries

Splits at natural C++ boundaries instead of fixed characters:
- Function/class/struct/enum definitions
- UE5 macros (UCLASS, USTRUCT, UPROPERTY, UFUNCTION)
- Namespace declarations
- Comment blocks
- Falls back to paragraph/character boundaries

**Configuration:**
```bash
set SEMANTIC_CHUNKING=1  # Default: ON
set CHUNK_SIZE=2000      # Default: 2000 (semantic), 1500 (char-based)
set CHUNK_OVERLAP=200
```

### ✅ Phase 7: Code-Trained Embedding Model
**Status:** Complete - Upgraded to unixcoder-base

Switched from general NLP to code-specific model:

| Model | Dims | Speed | Training |
|-------|------|-------|----------|
| **unixcoder-base** (NEW) | 768 | 2.6ms | C++, Python, Java |
| all-MiniLM-L6-v2 (OLD) | 384 | 1.3ms | General English |

**Expected improvements:** +40-60% accuracy on code structure queries

**Configuration:**
```bash
set EMBED_MODEL=microsoft/unixcoder-base  # Default
```

## Directory Structure

```
D:\DevTools\UE5-Source-Query\
├── src/
│   ├── core/
│   │   ├── query_intent.py          # Smart query routing
│   │   ├── hybrid_query.py          # Main hybrid engine
│   │   ├── definition_extractor.py  # Regex code extraction
│   │   ├── filtered_search.py       # Metadata-based filtering
│   │   └── query_engine.py          # Semantic search (original)
│   ├── indexing/
│   │   ├── metadata_enricher.py     # Entity detection & tagging
│   │   ├── build_embeddings.py      # Vector indexing
│   │   └── BuildSourceIndex.ps1     # File discovery
│   └── server/
│       └── retrieval_server.py      # HTTP API
├── data/
│   ├── vector_store.npz             # Embeddings (24MB)
│   ├── vector_meta.json             # Original metadata (3.9MB)
│   └── vector_meta_enriched.json    # With entity tags (generated)
├── docs/
│   ├── HYBRID_QUERY_GUIDE.md        # Detailed guide
│   ├── AUDIT_REPORT.md              # System audit
│   └── IMPROVEMENT_ROADMAP.md       # Enhancement plan
└── ask.bat                          # Entry point
```

## Usage Examples

### 1. Hybrid Query (Recommended)

```bash
# Automatic routing - best results
python src/core/hybrid_query.py "FHitResult members" --show-reasoning

# Output:
# Type: HYBRID
# Enhanced: "FHitResult members struct UPROPERTY fields members"
# ✅ FHitResult struct definition (HitResult.h:19-288)
# ✅ Semantic supplements
```

### 2. Definition Extraction

```bash
# Exact struct definition
python src/core/definition_extractor.py struct FHitResult

# With fuzzy matching
python src/core/definition_extractor.py struct HitRes --fuzzy

# Classes and enums
python src/core/definition_extractor.py class AActor
python src/core/definition_extractor.py enum ECollisionChannel
```

### 3. Filtered Search (with enriched metadata)

```python
from src.core.filtered_search import FilteredSearch
import numpy as np, json
from sentence_transformers import SentenceTransformer

# Load enriched data
embeddings = np.load("data/vector_store.npz")["embeddings"]
metadata = json.load(open("data/vector_meta_enriched.json"))['items']

# Create search engine
search = FilteredSearch(embeddings, metadata)

# Encode query
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
qvec = model.encode(["collision detection"], normalize_embeddings=True)[0]

# Filter by entity
results = search.search(qvec, entity="FHitResult", top_k=5)

# Filter by type + macro
results = search.search(qvec, entity_type="struct", has_uproperty=True)

# Boost relevance
results = search.search(qvec, boost_entities=["FHitResult"], boost_macros=True)
```

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Definition extraction | 0.3-0.4s | Fast, 100% accurate for exact names |
| Semantic search | 0.8-1.0s | Includes embedding (cached after first query) |
| Hybrid query | 1.2-1.4s | Both methods combined |
| Metadata enrichment | ~2 minutes | One-time process for 17,587 chunks |

## Best Practices

### ✅ DO

```bash
# Precise definitions
"struct FHitResult"
"class AActor"
"FVector struct"

# Members/properties
"FHitResult members"
"AActor properties"

# Specific members
"FHitResult ImpactPoint ImpactNormal"

# Concepts
"how does collision detection work"
"explain physics simulation"
```

### ❌ AVOID

```bash
# Too vague
"tell me about FHitResult"

# Wrong capitalization
"fhitresult"  # Should be: FHitResult

# Missing context
"members"  # Should be: "FHitResult members"
```

## Troubleshooting

**Q: Definition not found?**
1. Check capitalization (UE5 convention: FHitResult, AActor, ECollisionChannel)
2. Try fuzzy matching: `--fuzzy` flag
3. Verify file is indexed in vector_meta.json

**Q: Semantic results irrelevant?**
1. Try hybrid mode by mentioning entity name + "members"
2. Use filtered search with entity filter
3. Add more specific keywords to query

**Q: Want to use enriched metadata?**
```bash
# One-time enrichment process (~2 minutes)
python src/indexing/metadata_enricher.py data/vector_meta.json

# Use filtered search (see examples above)
python src/core/filtered_search.py
```

## Development

### Running Tests

```bash
# Test query intent analyzer
python src/core/query_intent.py

# Test definition extractor
python src/core/definition_extractor.py struct FHitResult

# Test hybrid query
python src/core/hybrid_query.py "FHitResult members" --show-reasoning

# Test filtered search (requires enriched metadata)
python src/core/filtered_search.py
```

### Enriching Metadata (Optional)

```bash
# Enrich with entity detection (~2 min for 17,587 chunks)
python src/indexing/metadata_enricher.py data/vector_meta.json

# Output: data/vector_meta_enriched.json
# Adds: entities, entity_types, has_uproperty, has_uclass, etc.
```

## What We Built

1. **Query Intent Analyzer** - Detects query type and enhances automatically
2. **Hybrid Router** - Routes to best search strategy
3. **Definition Extractor** - Regex-based C++ parsing with brace matching
4. **Query Enhancement** - Adds code keywords + extracts member names
5. **Fuzzy Matching** - Levenshtein distance for typo tolerance
6. **LRU Caching** - Caches embeddings (64 queries)
7. **Metadata Enricher** - Tags entities, types, UE5 macros
8. **Filtered Search** - Filter by entity, type, macros + relevance boosting

## Credits

Built to solve semantic search accuracy problems when querying UE5.3 source code.

**Problem:** "FHitResult members" returned wrong files
**Solution:** Hybrid routing with intelligent intent analysis

All 7 optimization phases implemented! 🎉