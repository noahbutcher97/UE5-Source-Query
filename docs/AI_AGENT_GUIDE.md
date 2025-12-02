# UE5 Source Query - AI Agent Integration Guide

**For:** Claude Code, Cursor, Gemini CLI, GitHub Copilot, and other AI coding assistants
**Version:** 2.0.0
**Last Updated:** 2025-12-02

---

## Quick Start

### Basic Query (Text Output)
```bash
ask.bat "FHitResult members"
```

### Structured Output (AI-Parseable)
```bash
ask.bat "FHitResult members" --format json
```

### Code-Only Mode (For LLM Context)
```bash
ask.bat "struct FVector" --format code --max-lines 20
```

---

## Output Formats

### JSON (Recommended for Parsing)
```bash
ask.bat "collision detection" --format json
```

**Output Structure:**
```json
{
  "query": {
    "question": "collision detection",
    "intent": {
      "query_type": "semantic",
      "confidence": 0.9
    }
  },
  "results": {
    "definitions": [...],
    "semantic": [...],
    "combined": [...]
  },
  "timing": {...},
  "metadata": {
    "total_results": 5,
    "definition_count": 0,
    "semantic_count": 5
  }
}
```

### JSONL (One Object Per Line)
```bash
ask.bat "FHitResult" --format jsonl
```

**Output:** Each line is a separate JSON object
```jsonl
{"type":"query_metadata","question":"FHitResult",...}
{"type":"definition","entity_type":"struct","entity_name":"FHitResult",...}
{"type":"semantic","path":"...","score":0.95,...}
{"type":"timing","intent_analysis":0.002,...}
```

### Markdown (For LLM Context Windows)
```bash
ask.bat "vehicle physics" --format markdown
```

**Output:** Formatted markdown with code blocks
```markdown
# Query: vehicle physics
**Intent:** semantic (confidence: 0.85)

## Definitions (1)
### 1. struct `FVehicleState`
**File:** `Engine/Plugins/VehiclePhysics/Source/...`
...
```

### XML (For Legacy Integrations)
```bash
ask.bat "FHitResult" --format xml
```

### Code-Only (Minimal Output)
```bash
ask.bat "struct FVector" --format code
```

**Output:** Just code snippets without metadata
```cpp
// struct FVector
// File: Engine/Source/Runtime/Core/Public/Math/Vector.h:42
struct FVector
{
    float X;
    float Y;
    float Z;
};
```

---

## CLI Arguments Reference

### Query Arguments
- **`question`** (required) - The query text
- **`--top-k N`** - Number of results to return (default: 5)
- **`--scope SCOPE`** - Search scope: `engine`, `project`, or `all` (default: `engine`)

### Output Control
- **`--format FORMAT`** - Output format: `text`, `json`, `jsonl`, `xml`, `markdown`, `code` (default: `text`)
- **`--no-code`** - Exclude code from output (metadata only)
- **`--max-lines N`** - Maximum lines per code snippet (default: 50)
- **`--filter FILTER`** - Filter results by entity type, macro, origin, etc. (see Filter Syntax below)

### Server Options
- **`--port N`** - Server port (default: 8765)
- **`--no-server`** - Force local execution (bypass server)

### Legacy
- **`--json`** - Output raw JSON (deprecated, use `--format json`)

### Filter Syntax (NEW in v2.0)

The `--filter` argument allows precise filtering of semantic search results using a simple query syntax.

**Supported Filters:**
- `type:ENTITY_TYPE` - Filter by entity type (`struct`, `class`, `enum`, `function`, `delegate`)
- `macro:MACRO_NAME` - Filter by UE5 macro (`UPROPERTY`, `UCLASS`, `UFUNCTION`, `USTRUCT`)
- `origin:ORIGIN` - Filter by origin (`engine`, `project`)
- `entity:ENTITY_NAME` - Filter to specific entity (e.g., `FHitResult`)
- `file:FILE_TYPE` - Filter by file type (`header`, `implementation`)
- `boost:TYPE` - Enable boosting (`macros`, `entities`)

**Operators:**
- `AND` - Combine multiple filters (all must match)
- `OR` - Not yet supported

**Examples:**
```bash
# Find all struct definitions with UPROPERTY
ask.bat "physics data" --filter "type:struct AND macro:UPROPERTY"

# Find classes from engine with UCLASS macro
ask.bat "actor component" --filter "type:class AND origin:engine AND macro:UCLASS"

# Find FHitResult in header files only
ask.bat "collision data" --filter "entity:FHitResult AND file:header"

# Boost results with macro presence
ask.bat "vehicle state" --filter "type:struct AND boost:macros"
```

**Note:** Filtering requires enriched metadata. If results aren't filtered as expected, the vector store may need metadata enrichment.

---

## Common Use Cases

### 1. Look Up API Definition
**Goal:** Get exact struct/class/enum definition

```bash
# Get FHitResult definition
ask.bat "struct FHitResult" --format json

# Get AActor class
ask.bat "class AActor" --format json

# Get enum values
ask.bat "enum ECollisionChannel" --format json
```

**What You Get:**
- File path and line numbers
- Complete definition
- Members/properties
- Match quality score

### 2. Find API Members/Parameters
**Goal:** Understand what a type contains

```bash
# What does FHitResult have?
ask.bat "FHitResult members" --format markdown

# What are AActor's properties?
ask.bat "AActor properties" --format markdown
```

### 3. Conceptual Search
**Goal:** Understand how something works

```bash
# How does collision work?
ask.bat "how does collision detection work" --format markdown --max-lines 30

# Vehicle physics explanation
ask.bat "vehicle wheel simulation" --format markdown
```

### 4. Code Context for LLM
**Goal:** Get code snippets to include in prompts

```bash
# Get FVector code for context
ask.bat "struct FVector" --format code --max-lines 20

# Get collision-related code
ask.bat "collision" --scope engine --format code --max-lines 15
```

### 5. Metadata-Only Queries
**Goal:** Fast lookups without large code blocks

```bash
# Just get file paths and line numbers
ask.bat "FHitResult" --format json --no-code
```

---

## Integration Examples

### Claude Code (.claude/PROJECT.md)
```markdown
## UE5 Source Query Integration

Query UE5 source code using ask.bat:

\`\`\`bash
# Look up definitions
ask.bat "struct FHitResult" --format json

# Get code context
ask.bat "collision detection" --format code --max-lines 20
\`\`\`

Parse JSON output to extract file paths and navigate to definitions.
```

### Python Script Integration
```python
import subprocess
import json
from pathlib import Path

def query_ue5(question: str, format: str = "json", scope: str = "engine") -> dict:
    """Query UE5 source code and return parsed results"""
    result = subprocess.run(
        ["ask.bat", question, "--format", format, "--scope", scope],
        capture_output=True,
        text=True,
        cwd=r"D:\DevTools\UE5-Source-Query"
    )

    if result.returncode != 0:
        raise RuntimeError(f"Query failed: {result.stderr}")

    if format == "json":
        return json.loads(result.stdout)
    else:
        return {"output": result.stdout}

# Example usage
data = query_ue5("FHitResult members")
for definition in data["results"]["definitions"]:
    print(f"Found: {definition['entity_name']} at {definition['file_path']}:{definition['line_start']}")
```

### Cursor (.cursorrules)
```markdown
## UE5 API Lookups

When working with Unreal Engine 5 APIs:

1. Use ask.bat with --format json
2. Parse JSON to extract file paths
3. Navigate to exact line numbers for definitions
4. Use --format code to get context for your LLM

Example:
\`\`\`bash
ask.bat "FHitResult ImpactPoint" --format json
\`\`\`
```

---

## Query Patterns

### Definition Queries
These return exact code definitions using regex extraction (fast, precise):

```bash
ask.bat "struct FHitResult" --format json
ask.bat "class AActor" --format json
ask.bat "enum ECollisionChannel" --format json
ask.bat "function LineTraceSingleByChannel" --format json
```

**Speed:** ~0.3-0.4 seconds
**Accuracy:** ~100% for exact matches

### Semantic Queries
These search by meaning using embeddings (slower, conceptual):

```bash
ask.bat "how does collision detection work" --format markdown
ask.bat "vehicle wheel physics" --format markdown
ask.bat "animation blending" --format markdown
```

**Speed:** ~0.8-1.0 seconds
**Accuracy:** ~85% relevance

### Hybrid Queries
These combine both approaches (best of both worlds):

```bash
ask.bat "FHitResult members" --format json
ask.bat "AActor GetActorLocation" --format markdown
```

**Speed:** ~1.2-1.4 seconds
**Accuracy:** ~95% (definition precision + semantic context)

---

## Performance Tips

### 1. Use Server Mode for Interactive Sessions
```bash
# Terminal 1: Start server (loads models once)
python src/server/retrieval_server.py --port 8765

# Terminal 2: Queries are instant (models cached in memory)
ask.bat "FHitResult" --format json
ask.bat "FVector" --format json
# ... many more queries, all fast
```

### 2. Limit Results for Speed
```bash
ask.bat "actor" --top-k 3 --format json  # Faster than default top-k=5
```

### 3. Use --no-code for Metadata-Only
```bash
ask.bat "collision" --format json --no-code  # Smaller output, faster parsing
```

### 4. Scope to Specific Origins
```bash
ask.bat "MyCustomActor" --scope project --format json  # Search only project code
ask.bat "AActor" --scope engine --format json          # Search only engine code
```

---

## Error Handling

All errors return structured output when using --format json:

```json
{
  "error": "No results found",
  "query": "NonExistentClass",
  "timing": {...}
}
```

**Common Errors:**
- **"No results found"** - Check entity name capitalization (FHitResult not fhitresult)
- **"Server unavailable"** - Falls back to local engine automatically
- **"Virtual environment not found"** - Run `install.bat` or `configure.bat`

---

## Best Practices

### ✅ DO:
- Use **--format json** for programmatic parsing
- Use **--format code** when building LLM context
- Use **--format markdown** for human-readable output
- Use **--no-code** when you only need file paths
- Use **--scope engine** for UE5 API lookups
- Use **--scope project** for game-specific code
- Capitalize entity names correctly (FHitResult, AActor, ECollisionChannel)

### ❌ DON'T:
- Don't parse text output programmatically (use JSON/JSONL instead)
- Don't use lowercase entity names (won't match UE5 naming conventions)
- Don't query without --format when integrating with scripts
- Don't use --top-k values > 20 (diminishing returns)

---

## Output Schema Reference

### JSON Definition Result
```json
{
  "type": "definition",
  "entity_type": "struct|class|enum|function",
  "entity_name": "FHitResult",
  "file_path": "Engine/Source/.../HitResult.h",
  "line_start": 42,
  "line_end": 150,
  "match_quality": 1.0,
  "members_count": 15,
  "definition": "struct ENGINE_API FHitResult { ... }",  // if include_code=true
  "members": ["float Time", "FVector ImpactPoint", ...]  // if include_code=true
}
```

### JSON Semantic Result
```json
{
  "type": "semantic",
  "path": "Engine/Source/.../CollisionEngine.cpp",
  "chunk_index": 5,
  "total_chunks": 20,
  "score": 0.85,
  "origin": "engine",
  "entities": ["FHitResult", "FVector"],        // if metadata enriched
  "entity_type": "struct"                        // if metadata enriched
}
```

---

## Advanced Usage

### Combining with Other Tools

**With jq (JSON processing):**
```bash
# Get just file paths
ask.bat "FHitResult" --format json | jq -r '.results.definitions[].file_path'

# Count results
ask.bat "collision" --format json | jq '.metadata.total_results'

# Extract entity names
ask.bat "physics" --format json | jq -r '.results.semantic[].entities[]' | sort -u
```

**With Python:**
```python
import subprocess
import json

# Get all FVector-related files
result = subprocess.run(
    ["ask.bat", "FVector", "--format", "json", "--no-code"],
    capture_output=True,
    text=True
)
data = json.loads(result.stdout)

files = set()
for item in data["results"]["definitions"]:
    files.add(item["file_path"])
for item in data["results"]["semantic"]:
    files.add(item["path"])

print(f"FVector appears in {len(files)} files")
```

---

## Troubleshooting

### Query Returns No Results
**Symptoms:** `"total_results": 0` in JSON output

**Solutions:**
1. Check entity name capitalization
   ```bash
   # Wrong
   ask.bat "hitresult" --format json

   # Correct
   ask.bat "FHitResult" --format json
   ```

2. Try broader scope
   ```bash
   ask.bat "MyClass" --scope all --format json
   ```

3. Use semantic search instead
   ```bash
   ask.bat "hit result collision" --format json
   ```

### Output Formatting Errors
**Symptoms:** `[ERROR] Formatting failed`

**Solutions:**
- Check that query returned valid results
- Falls back to raw JSON automatically
- Report issue if persistent

### Slow Queries
**Symptoms:** Queries take >5 seconds

**Solutions:**
1. Use server mode (see Performance Tips)
2. Reduce --top-k value
3. Use --no-code for faster output
4. Check if running initial model load (first query always slow)

---

## Examples Library

### Example 1: Find All Vehicle Classes
```bash
ask.bat "vehicle" --scope all --format json --no-code | jq '.results.definitions[] | select(.entity_type=="class") | .entity_name'
```

### Example 2: Get Complete FHitResult Definition
```bash
ask.bat "struct FHitResult" --format code --max-lines 100
```

### Example 3: Build Context for LLM Prompt
```bash
# Get definitions
CONTEXT=$(ask.bat "FHitResult FVector" --format code --max-lines 30)

# Use in prompt
echo "Given these UE5 definitions:\n$CONTEXT\n\nWrite code to..."
```

### Example 4: Batch Lookups
```bash
# Create query list
echo "FHitResult" > queries.txt
echo "FVector" >> queries.txt
echo "AActor" >> queries.txt

# Process each
for query in $(cat queries.txt); do
    ask.bat "struct $query" --format json --no-code > "results_$query.json"
done
```

---

## Version Compatibility

**Current Version:** 2.0.0
**Minimum Requirements:**
- Python 3.8+
- Unreal Engine 5.0+
- Windows 10/11 (Linux/macOS not supported)

**Features by Version:**
- **v2.0.0:** Added structured output formats (json, jsonl, xml, markdown, code)
- **v1.x:** Basic text output only

---

## Support & Feedback

**Issues:** Report at project repository
**Documentation:** See `docs/` folder
**Examples:** See `examples/` folder (if available)

---

*Last Updated: 2025-12-02*
*For: AI Coding Agents*
*Version: 2.0.0*