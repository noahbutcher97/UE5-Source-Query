# Project Integration Guide

**How to integrate UE5 Source Query into your Unreal Engine project and configure Claude Code to use it.**

---

## Quick Setup

After running the deployment wizard and installing to your project (e.g., `D:\UnrealProjects\5.3\hijack_prototype\Scripts`), you need to:

1. ✅ Create/update your project's `CLAUDE.md` file
2. ✅ Test the integration
3. ✅ (Optional) Configure custom aliases

---

## Step 1: Update Project CLAUDE.md

### Location

Create or update this file in your project root:
```
D:\UnrealProjects\5.3\hijack_prototype\CLAUDE.md
```

### Template: Add UE5 Source Query Section

Add this section to your project's `CLAUDE.md`:

```markdown
# Project Name - AI Agent Instructions

## UE5 Source Query System

### Overview

This project includes the UE5 Source Query Tool, which provides intelligent hybrid search of the Unreal Engine 5.3 source code. Use it to quickly find UE5 API definitions, understand engine systems, and get accurate code references.

**Location:** `Scripts/`

**Indexed Content:**
- 24 core UE5 subsystems (Chaos Physics, Animation, Networking, etc.)
- 17,799 code chunks from Engine source
- 52.1 MB vector store with semantic search

### When to Use UE5 Source Query

Use this tool when you need to:
- ✅ Find UE5 class/struct definitions (FHitResult, AActor, UChaosWheeledVehicleMovementComponent)
- ✅ Understand UE5 subsystem implementations (physics, animation, networking)
- ✅ Get accurate API signatures and member variables
- ✅ Research how engine features work internally
- ✅ Find examples of UE5 patterns and best practices

**DO NOT use for:**
- ❌ Project-specific code (use regular file search)
- ❌ Third-party plugin code
- ❌ Blueprint-only questions

### How to Query (3 Methods)

#### Method 1: Quick CLI Query (Recommended for Simple Lookups)

```bash
# From project root
Scripts\ask.bat "FHitResult members"
Scripts\ask.bat "UChaosWheeledVehicleMovementComponent"
Scripts\ask.bat "struct FBodyInstance"
```

**Flags:**
- `--copy` - Copy results to clipboard
- `--dry-run` - Show results without LLM analysis
- `--top-k N` - Return top N results (default: 5)

#### Method 2: Python Script (For Programmatic Use)

```python
import sys
from pathlib import Path

# Add Scripts to path
sys.path.insert(0, str(Path("Scripts/src")))

from core.hybrid_query import HybridQueryEngine

# Initialize engine
engine = HybridQueryEngine(Path("Scripts"))

# Query
results = engine.query("FHitResult members", top_k=5)

# Results contain:
# - results.query_type (DEFINITION, SEMANTIC, HYBRID)
# - results.definition_results (if applicable)
# - results.semantic_results (if applicable)
# - results.merged_results (combined & ranked)
```

#### Method 3: Unified Dashboard (For Interactive Exploration)

```bash
Scripts\launcher.bat
```

Opens GUI with tabs for:
- **Query** - Interactive search with filters
- **Sources** - Manage indexed directories
- **Maintenance** - Rebuild index, health checks
- **Diagnostics** - System verification

### Query Tips for Best Results

**For Precise Definitions:**
```bash
# Use explicit entity names
Scripts\ask.bat "struct FHitResult"
Scripts\ask.bat "class AActor"
Scripts\ask.bat "enum ECollisionChannel"
```

**For Understanding Systems:**
```bash
# Use natural language
Scripts\ask.bat "how does collision detection work"
Scripts\ask.bat "vehicle wheel physics implementation"
Scripts\ask.bat "animation blend space system"
```

**For Member Access:**
```bash
# Combine entity + keywords
Scripts\ask.bat "FHitResult ImpactPoint ImpactNormal"
Scripts\ask.bat "AActor GetActorLocation GetActorRotation"
```

### Common UE5 Queries for This Project

```bash
# Vehicle Physics (if using Chaos Vehicles)
Scripts\ask.bat "UChaosWheeledVehicleMovementComponent"
Scripts\ask.bat "UChaosVehicleWheel"
Scripts\ask.bat "how does wheel suspension work"

# Animation (if using character systems)
Scripts\ask.bat "UAnimInstance"
Scripts\ask.bat "animation blend spaces"
Scripts\ask.bat "root motion"

# Physics
Scripts\ask.bat "FBodyInstance"
Scripts\ask.bat "physics constraints"
Scripts\ask.bat "collision response"

# Networking (for multiplayer)
Scripts\ask.bat "replication"
Scripts\ask.bat "FRepMovement"
Scripts\ask.bat "server RPC"
```

### AI Agent Workflow

When Claude Code needs UE5 API information:

1. **Identify the Need**
   - User asks about UE5 class/struct/function
   - Need to understand engine behavior
   - Looking for API signatures

2. **Run Query**
   ```bash
   # Use Bash tool to run query
   cd Scripts && ask.bat "your query" --dry-run --top-k 3
   ```

3. **Analyze Results**
   - Results show file paths with line numbers
   - Code snippets with definitions
   - Relevance scores

4. **Provide Answer**
   - Reference exact file locations (e.g., `Engine/Source/Runtime/Engine/Classes/GameFramework/Actor.h:245`)
   - Quote relevant code snippets
   - Explain with context from results

### Example AI Agent Interaction

**User:** "How do I access the impact point from a hit result?"

**Claude Code:**
```bash
# Query the index
cd Scripts && ask.bat "FHitResult ImpactPoint" --dry-run --top-k 3
```

**Response:**
"Based on the UE5 source query, `FHitResult` has an `ImpactPoint` member of type `FVector`. Here's the definition from `Engine/Source/Runtime/Engine/Classes/Engine/HitResult.h:89`:

```cpp
UPROPERTY()
FVector ImpactPoint;
```

You can access it like this:
```cpp
FHitResult HitResult;
// ... perform trace ...
FVector ImpactLocation = HitResult.ImpactPoint;
```

The impact point represents the world-space location where the collision occurred."

### Maintenance

**Rebuild Index (if Engine source changes):**
```bash
Scripts\launcher.bat
# Go to Maintenance tab → Rebuild Index
```

**Health Check:**
```bash
Scripts\tools\health-check.bat
```

**Troubleshooting:**
See `Scripts/docs/Production/TROUBLESHOOTING.md`

### Performance Notes

- **Query Speed:** 0.3-1.4s depending on query type
- **Index Size:** 52.1 MB (loaded on first query)
- **GPU Acceleration:** Automatic if NVIDIA GPU present
- **Cache:** Results cached in memory after first use

### Integration with Project Workflow

**During Development:**
```bash
# Quick API lookup
Scripts\ask.bat "FVector" --copy

# Paste into code with Ctrl+V
```

**During Code Review:**
```bash
# Verify UE5 API usage
Scripts\ask.bat "correct usage of UMovementComponent"
```

**During Debugging:**
```bash
# Understand engine behavior
Scripts\ask.bat "why does SetActorLocation fail"
```

---

## Advanced: Custom Query Aliases

Add to your shell profile (PowerShell: `$PROFILE`, Bash: `~/.bashrc`):

### PowerShell
```powershell
# UE5 Query aliases
function ue { & "D:\UnrealProjects\5.3\hijack_prototype\Scripts\ask.bat" $args }
function ue-gui { & "D:\UnrealProjects\5.3\hijack_prototype\Scripts\launcher.bat" }

# Quick lookups
function ue-actor { ue "AActor $args" --dry-run }
function ue-component { ue "UActorComponent $args" --dry-run }
function ue-struct { ue "struct $args" --dry-run }
```

**Usage:**
```powershell
ue "FHitResult"
ue-actor "GetActorLocation"
ue-struct "FVector"
```

### Bash/Git Bash
```bash
# UE5 Query aliases
alias ue='D:/UnrealProjects/5.3/hijack_prototype/Scripts/ask.bat'
alias ue-gui='D:/UnrealProjects/5.3/hijack_prototype/Scripts/launcher.bat'

# Quick lookups
ue-actor() { ue "AActor $*" --dry-run; }
ue-struct() { ue "struct $*" --dry-run; }
```

---

## Testing the Integration

### Verify Installation

```bash
# 1. Check files exist
ls Scripts/ask.bat
ls Scripts/launcher.bat
ls Scripts/data/vector_store.npz

# 2. Test simple query
Scripts\ask.bat "FVector" --dry-run

# 3. Verify GUI opens
Scripts\launcher.bat
```

### Expected Output

```
D:\UnrealProjects\5.3\hijack_prototype> Scripts\ask.bat "FVector" --dry-run

Hybrid Query Results
====================

Query Type: DEFINITION
Results: 5 matches

1. Engine/Source/Runtime/Core/Public/Math/Vector.h:123
   struct FVector { float X, Y, Z; }
   Score: 0.95

[... more results ...]
```

---

## Summary Checklist

After installation, ensure:

- ✅ `CLAUDE.md` updated with UE5 Source Query section
- ✅ Test query works: `Scripts\ask.bat "FVector" --dry-run`
- ✅ Desktop shortcut created (optional)
- ✅ AI agent knows to use `Scripts\ask.bat` for UE5 queries
- ✅ (Optional) Custom aliases configured

**Your project is now integrated with UE5 Source Query!**

Claude Code can now intelligently search 17,799 chunks of UE5 source code to answer your questions.

---

*For more information, see:*
- `Scripts/README.md` - Full documentation
- `Scripts/docs/Production/UsageGuide/HYBRID_QUERY_GUIDE.md` - Query system details
- `Scripts/docs/Production/TROUBLESHOOTING.md` - Common issues
