# Hybrid Query System Guide

## Overview

The UE5 Source Query system now uses **intelligent hybrid routing** to automatically select the best search strategy for each query. This eliminates the accuracy problems of pure semantic search while maintaining the flexibility for conceptual questions.

## The Problem We Solved

### Before: Pure Semantic Search Failures

**Query:** `"FHitResult members"`

**Results:**
- ❌ CollectionSelectionFacade.h (score: 0.377)
- ❌ ChaosResultsManager.h (score: 0.370)
- ❌ Wrong files entirely!

**Why it failed:**
- Semantic embeddings matched on the word "members" (as in "team members", "collection members")
- The actual FHitResult struct chunk scored only 0.170 because it contains:
  - Technical C++ syntax (UPROPERTY, FVector_NetQuantize)
  - Member names like `ImpactPoint`, `FaceIndex`
  - Not natural language text

### After: Hybrid Routing Success

**Same query:** `"FHitResult members"`

**Results:**
- ✅ FHitResult struct definition (HitResult.h:19-288, 25 members)
- ✅ Supplemented with semantic results

**How it works:**
1. Detects "FHitResult members" as a **HYBRID** query
2. Extracts definition using regex (0.341s)
3. Enhances query: "FHitResult members struct UPROPERTY fields"
4. Supplements with semantic search (0.905s)
5. **Total time: 1.251s**

---

## Query Types

The system automatically detects three query types:

### 1. DEFINITION Queries (Explicit)

**Patterns detected:**
- `"struct FHitResult"`
- `"FHitResult struct"`
- `"class AActor"`
- `"what is FHitResult"`
- `"show me AActor"`
- `"LineTraceSingleByChannel function"`
- `"ECollisionChannel enum"`

**Strategy:**
- Pure definition extraction using regex
- Fast (0.3-0.4s)
- 100% accurate for exact entity names
- Returns complete code definition with line numbers

**Example output:**
```
STRUCT FHitResult
File: Engine/Source/Runtime/Engine/Classes/Engine/HitResult.h
Lines: 19-288
Members: 25
  - int32 FaceIndex
  - float Time
  - FVector_NetQuantize ImpactPoint
  - FVector_NetQuantizeNormal ImpactNormal
  ...
```

### 2. HYBRID Queries (Smart Detection)

**Patterns detected:**
- Entity name + definition keywords
- `"FHitResult members"`
- `"FVector fields"`
- `"AActor properties"`
- `"UWorld methods"`

**Strategy:**
1. Extract definition first (precise)
2. Enhance query with code keywords
3. Supplement with semantic search
4. Combine results (definition first)

**Query Enhancement:**
```
"FHitResult members"
→ "FHitResult members struct UPROPERTY fields members"

"FVector fields and properties"
→ "FVector fields and properties struct UPROPERTY members"

"FHitResult ImpactPoint ImpactNormal"
→ "FHitResult ImpactPoint ImpactNormal struct UPROPERTY fields ImpactPoint ImpactNormal"
```

### 3. SEMANTIC Queries (Conceptual)

**Patterns detected:**
- Conceptual keywords: how, why, when, explain, describe, compare
- `"how does collision detection work"`
- `"explain physics simulation"`
- `"difference between AActor and UObject"`
- `"best practice for multiplayer"`

**Strategy:**
- Pure semantic search
- Best for understanding concepts
- Returns relevant code chunks

---

## How Query Intent Analysis Works

### UE5 Naming Convention Detection

The analyzer recognizes Unreal Engine naming patterns:

| Pattern | Type | Examples |
|---------|------|----------|
| `F[A-Z]*` | Struct | FVector, FHitResult, FTransform |
| `U[A-Z]*` | UObject class | UWorld, UActorComponent |
| `A[A-Z]*` | AActor class | AActor, APawn, ACharacter |
| `I[A-Z]*` | Interface | IInterface |
| `E[A-Z]*` | Enum | ECollisionChannel |

### Keyword Analysis

**Definition keywords** (trigger hybrid/definition):
- members, fields, properties, methods
- definition, signature, parameters
- return type, inherit, base class

**Conceptual keywords** (trigger semantic):
- how, why, when, where, explain
- describe, compare, difference
- best practice, example, tutorial

### Confidence Scoring

- **0.95**: Explicit definition query (`"struct FHitResult"`)
- **0.90**: Conceptual query detected (`"how does...`)
- **0.70**: Hybrid query (entity + definition keywords)
- **0.50**: Default semantic (no strong indicators)

---

## Performance Comparison

### Definition Extraction
- **Speed**: 0.3-0.4s
- **Accuracy**: 100% for exact names, supports fuzzy matching
- **Coverage**: Structs, classes, enums, functions
- **Limitation**: Needs exact entity name

### Semantic Search
- **Speed**: 0.8-1.0s (includes embedding)
- **Accuracy**: Variable (depends on query quality)
- **Coverage**: All code, conceptual understanding
- **Limitation**: Can return irrelevant results

### Hybrid (Best of Both)
- **Speed**: 1.2-1.4s (both methods)
- **Accuracy**: Exact definition + relevant context
- **Coverage**: Complete
- **Limitation**: Slightly slower

---

## Usage Examples

### Command Line

```bash
# Hybrid query system (recommended)
python src/core/hybrid_query.py "FHitResult members" --show-reasoning

# Show query analysis
python src/core/hybrid_query.py "how does collision work" --show-reasoning

# Get top 5 results
python src/core/hybrid_query.py "struct AActor" --top-k 5

# JSON output
python src/core/hybrid_query.py "FVector" --json
```

### Test Query Intent Analyzer

```bash
# Test the analyzer directly
python src/core/query_intent.py

# Outputs analysis for 12 test queries:
# - struct FHitResult (DEFINITION)
# - FHitResult members (HYBRID)
# - how does collision work (SEMANTIC)
# etc.
```

---

## Future Enhancements (Optional)

### Phase 3: Metadata Tagging

Tag chunks during indexing:
```json
{
  "chunk_id": 123,
  "path": "HitResult.h",
  "entities": ["FHitResult"],
  "entity_types": ["struct"],
  "has_uproperty": true,
  "is_header": true
}
```

**Benefits:**
- Filter search: `entity="FHitResult" type="struct"`
- Boost relevance: chunks with matching entities score higher
- Enable faceted search

### Phase 4: Re-ranking

Two-stage retrieval:
1. Get top 20 with semantic search
2. Re-rank using:
   - BM25 keyword matching
   - Exact string matching
   - Entity name presence

### Phase 5: Better Embedding Models

Current: `all-MiniLM-L6-v2` (general purpose)

Code-specific alternatives:
- `microsoft/unixcoder-base`
- `microsoft/codebert-base`
- Fine-tuned model on UE5 source

### Phase 6: Semantic Chunking

Current: Fixed 1500 chars with 200 overlap

Better: Split at natural boundaries:
- Class/struct boundaries
- Function boundaries
- Namespace boundaries

---

## Architecture

```
Query: "FHitResult members"
           ↓
    QueryIntentAnalyzer
           ↓
    ┌──────────────────┐
    │  Intent Result   │
    │  Type: HYBRID    │
    │  Entity: FHitResult │
    │  Enhanced: "FHitResult members struct UPROPERTY fields" │
    └──────────────────┘
           ↓
    HybridQueryEngine
           ↓
    ┌──────────────────┬──────────────────┐
    │ Definition       │  Semantic        │
    │ Extraction       │  Search          │
    │                  │                  │
    │ Regex patterns   │  Embedding       │
    │ Brace matching   │  Cosine similarity│
    │ 0.341s           │  0.905s          │
    └──────────────────┴──────────────────┘
           ↓
    Combined Results
    [Definition, Semantic_1, Semantic_2, ...]
```

---

## Files

- `src/core/query_intent.py` - Query analysis and routing logic
- `src/core/hybrid_query.py` - Main hybrid query engine
- `src/core/definition_extractor.py` - Regex-based code extraction
- `src/core/query_engine.py` - Semantic search (original)

---

## Tips for Best Results

### For Definitions
✅ `"struct FHitResult"`
✅ `"class AActor"`
✅ `"FVector struct"`

### For Members/Properties
✅ `"FHitResult members"`
✅ `"AActor properties"`
✅ `"FHitResult ImpactPoint ImpactNormal"` (mention specific members)

### For Concepts
✅ `"how does collision detection work"`
✅ `"explain physics simulation"`
✅ `"difference between AActor and UObject"`

### Avoid
❌ `"tell me about FHitResult"` (too vague - be specific)
❌ `"fhitresult"` (use proper capitalization)

---

## Troubleshooting

**Q: Definition not found?**
- Check capitalization (must match UE5 convention)
- Try fuzzy matching: `--fuzzy` flag in definition_extractor.py
- Verify entity exists in indexed files

**Q: Semantic results irrelevant?**
- Try hybrid mode by mentioning specific members
- Use more specific keywords
- Filter by file pattern: `--pattern "Collision"`

**Q: Slow queries?**
- Definition extraction: 0.3s (fast)
- Semantic search: 0.8s (embedding overhead)
- Hybrid: 1.2s (both methods)
- Consider caching for repeated queries