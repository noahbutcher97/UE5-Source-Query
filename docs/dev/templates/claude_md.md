# CLAUDE.md Template for Project Integration

**Copy this section into your project's CLAUDE.md file.**

---

```markdown
## UE5 Source Query System

### Quick Reference

This project has UE5 Source Query installed in `Scripts/` with 17,799 indexed code chunks from Engine source.

**Use it for UE5 API lookups:**
```bash
Scripts\ask.bat "FHitResult members"
Scripts\ask.bat "UChaosWheeledVehicleMovementComponent"
Scripts\ask.bat "how does collision detection work"
```

**Open GUI Dashboard:**
```bash
Scripts\launcher.bat
```

### When to Use

✅ **Use for:**
- Finding UE5 class/struct/function definitions
- Understanding engine subsystems (physics, animation, networking)
- Getting accurate API signatures
- Researching engine implementation details

❌ **Don't use for:**
- Project-specific code (use regular file search)
- Third-party plugins
- Blueprint-only questions

### AI Agent Usage

When you need UE5 API information:

```bash
# Run query with Bash tool
cd Scripts && ask.bat "your query here" --dry-run --top-k 3
```

**Example:**
```bash
# User asks: "What members does FHitResult have?"
cd Scripts && ask.bat "FHitResult members" --dry-run --top-k 3

# Returns: File paths, line numbers, code snippets
# Provide answer with exact references
```

### Common Queries

```bash
# Vehicle Physics
Scripts\ask.bat "UChaosWheeledVehicleMovementComponent"
Scripts\ask.bat "wheel suspension"

# Character Animation
Scripts\ask.bat "UAnimInstance"
Scripts\ask.bat "animation blend spaces"

# Physics
Scripts\ask.bat "FBodyInstance"
Scripts\ask.bat "collision response"

# Networking
Scripts\ask.bat "replication"
Scripts\ask.bat "FRepMovement"
```

### Query Flags

- `--copy` - Copy results to clipboard
- `--dry-run` - Skip LLM analysis (faster)
- `--top-k N` - Return top N results

### Troubleshooting

```bash
# Verify installation
ls Scripts/data/vector_store.npz

# Test query
Scripts\ask.bat "FVector" --dry-run

# Health check
Scripts\tools\health-check.bat
```

**Full docs:** `Scripts/README.md`
```

---

## Minimal Template (For Concise Projects)

If you prefer a shorter version:

```markdown
## UE5 Source Query

Installed in `Scripts/` - Use for UE5 API lookups.

**Query:** `Scripts\ask.bat "your query" --dry-run`
**GUI:** `Scripts\launcher.bat`

Example: `Scripts\ask.bat "FHitResult members"`

See `Scripts/README.md` for full documentation.
```

---

## Copy to Your Project Now

1. **Open** `D:\UnrealProjects\5.3\hijack_prototype\CLAUDE.md`
2. **Add** the section above (full or minimal template)
3. **Save** the file
4. **Test** that Claude Code can see it:
   - Ask: "How do I query UE5 source code?"
   - Claude should reference the Scripts/ask.bat command

---

## Verification

After adding to CLAUDE.md, verify:

```bash
# 1. Check CLAUDE.md exists and has the section
cat CLAUDE.md | grep "UE5 Source Query"

# 2. Test a query
Scripts\ask.bat "FVector" --dry-run

# 3. Ask Claude Code to use it
# In Claude Code chat: "What are the members of FHitResult?"
# Claude should run: Scripts\ask.bat "FHitResult members"
```

**Success indicators:**
- ✅ Claude Code knows to use `Scripts\ask.bat` for UE5 queries
- ✅ Queries return relevant UE5 source code
- ✅ Claude provides accurate API information with file references
