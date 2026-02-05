# AI Agent Integration Guide

This document describes how AI agents (Claude, Gemini, ChatGPT, etc.) should interact with the UE5 Source Query tool.

## Protocol Summary

| Feature | Recommendation |
| :--- | :--- |
| **Output Format** | Always use `--format jsonl` for streaming or `--format json` for single block. |
| **Code Retrieval** | Use `--no-code` first to scan for relevance, then request full code. |
| **Entry Point** | Use `ask.bat` (Windows) or `./ask.sh` (Linux/Mac). |
| **Errors** | Check `stderr` for logs; `stdout` contains only the requested data in JSON modes. |

## 1. Discovery & Introspection
Agents should first inspect the tool's capabilities and environment.

### Tool Definition (MCP Schema)
Get a machine-readable definition of arguments and capabilities.
```bash
ask.bat --describe
```

### Environment Context
Understand the active project, engine version, and index health.
```bash
python -m ue5_query.utils.agent_introspect
```

### Diagnostics
Check GPU acceleration status programmatically.
```bash
python -m ue5_query.utils.gpu_test
```

## 2. Server API (Programmatic Control)
For high-performance integration, run the persistent retrieval server. 

**Why use the server?**
- **Zero Latency:** Avoids the 5-10 second "cold start" overhead of loading large embedding models (PyTorch) for every query.
- **Caching:** Keeps the vector index in RAM for instant sub-second retrieval.
- **Robustness:** Handles index errors gracefully (returns 503 instead of crashing).

**Start Server:**
```bash
python -m ue5_query.server.retrieval_server --port 8765
```

**Endpoints:**
- `GET /health`: Basic status check.
- `GET /describe`: Returns this tool's MCP/Function schema.
- `GET /config`: Returns environment and index statistics.
- `GET /search?q=query&scope=all`: Execute semantic search.

## 3. Event-Driven Monitoring
The tool emits machine-readable events to `logs/activity.jsonl`. Agents can react to these events (e.g., re-caching results when an index build completes).

**Event Example (JSONL):**
```json
{"timestamp": "2026-02-02T19:30:00", "event": "index_build_complete", "details": {"total_chunks": 29561, "size_mb": 86.6}}
```

## 4. Querying Code
**Best Practice:** Two-step retrieval.

### Step A: High-Level Scan
Search for a concept without flooding context window with implementation details.

```bash
ask.bat "how does UCharacterMovementComponent handle slide" --format json --no-code
```

**Response (JSON):**
```json
{
  "results": [
    {
      "file_path": "Engine/Source/Runtime/Engine/Private/Components/CharacterMovementComponent.cpp",
      "function": "PhysSlide",
      "type": "function_definition",
      "score": 0.89
    }
  ]
}
```

### Step B: Deep Dive
Request the specific implementation code.

```bash
ask.bat "PhysSlide" --format code --max-lines 50
```

## 5. Semantic Exit Codes
The CLI returns the following exit codes:

- **0**: Success (Results found)
- **1**: General Error (Exception)
- **2**: No Results Found (Query returned empty)
- **3**: Configuration Error (Index missing, Engine path invalid)

## 6. Batch Processing
If an agent plans to run multiple queries (e.g., investigating a complex bug), use batch mode to load the model once.

**Input (`queries.jsonl`):**
```json
{"id": "q1", "query": "UCharacterMovementComponent::PhysSlide"}
{"id": "q2", "query": "FHitResult definition"}
```

**Command:**
```bash
python -m ue5_query.core.batch_query --batch-file queries.jsonl --output results.jsonl
```
