# Smart Update System Design - December 8, 2025

## Overview

Implement a git-aware update system that allows deployed installations to pull updates from either a local dev repo or remote GitHub repository.

## Problem Statement

**Current Issue:** When fixing bugs in the dev repo, deployed installations become out of sync. Manual file copying is error-prone and doesn't scale to team environments.

**Desired Behavior:**
- Deployed installations should detect if a local dev repo exists
- If local dev repo exists, pull updates from there (instant, no network)
- If no local dev repo, pull from GitHub remote (works for any team member)
- Simple one-command update: `update.bat` or `python tools/update.py`

## Architecture

### 1. Deployment Configuration File

**Location:** `<deployed_scripts>/.ue5query_deploy.json`

```json
{
  "version": "1.0.0",
  "deployment_info": {
    "deployed_at": "2025-12-06T15:30:00Z",
    "deployed_from": "D:\\DevTools\\UE5-Source-Query",
    "deployment_method": "gui_installer",
    "deployed_to": "D:\\UnrealProjects\\5.3\\hijack_prototype\\Scripts"
  },
  "update_sources": {
    "local_dev_repo": "D:\\DevTools\\UE5-Source-Query",
    "remote_repo": "https://github.com/yourusername/UE5-Source-Query.git",
    "branch": "master"
  },
  "update_strategy": "auto",
  "exclude_patterns": [
    ".venv/",
    "data/vector_store.npz",
    "data/vector_meta*.json",
    ".git/",
    "__pycache__/",
    "*.pyc"
  ],
  "preserve_local": [
    "config/user_config.json",
    ".env",
    "data/"
  ]
}
```

### 2. Update Script: `tools/update.py`

**Capabilities:**
- Detect if local dev repo exists and is valid git repo
- Check local dev repo commit hash vs deployed version
- If local dev repo available: use robocopy/rsync with exclusions
- If no local dev repo: git clone/pull from remote
- Preserve user data (vector stores, configs)
- Verify installation after update
- Rollback on failure

**Usage:**
```bash
# Auto-detect update source
python tools/update.py

# Force specific source
python tools/update.py --source local
python tools/update.py --source remote

# Dry run (show what would change)
python tools/update.py --dry-run

# Update specific components only
python tools/update.py --components src,installer
```

### 3. Update Wrapper: `update.bat`

**Purpose:** Simple one-click update for Windows users

```batch
@echo off
.venv\Scripts\python.exe tools\update.py %*
if errorlevel 1 (
    echo Update failed! Press any key to exit...
    pause >nul
    exit /b 1
)
echo Update complete! Press any key to exit...
pause >nul
```

### 4. GUI Installer Enhancement

**Changes to `installer/gui_deploy.py`:**
1. Create `.ue5query_deploy.json` during deployment
2. Detect source repo path and git remote
3. Ask user if they want to enable auto-updates
4. Store remote repo URL (default: GitHub, allow custom)

### 5. Version Tracking

**Files to Track:**
- `VERSION` file in repo root: `1.0.0`
- Store deployed version in `.ue5query_deploy.json`
- Compare versions to detect if update needed

## Update Workflow

### Scenario 1: Local Dev Repo Available

```
User runs: update.bat
    ↓
1. Read .ue5query_deploy.json
2. Check if local_dev_repo exists: D:\DevTools\UE5-Source-Query
3. Validate it's a git repo with .git/
4. Compare commit hashes (local dev vs deployed)
5. If newer commits available:
   - Run verification checks on source
   - Robocopy with exclusions (preserve .venv, data/)
   - Update deployment_info.deployed_at
   - Run post-update verification
6. Report success/failure
```

**Advantages:**
- Instant updates (local file copy)
- No network required
- Works offline
- Dev and deployment stay in sync

### Scenario 2: No Local Dev Repo (Team Member Machine)

```
User runs: update.bat
    ↓
1. Read .ue5query_deploy.json
2. Check local_dev_repo: doesn't exist or not valid
3. Fall back to remote_repo
4. Git fetch from remote
5. Compare remote HEAD vs deployed version
6. If newer commits:
   - Git pull (or clone if first time)
   - Copy files with exclusions
   - Update deployment_info
   - Verify installation
7. Report success
```

**Advantages:**
- Works for any team member
- Always gets latest stable version
- No manual intervention

### Scenario 3: Air-Gapped Deployment

```json
"update_strategy": "manual"
```

User must manually deploy updates (current workflow preserved).

## File Exclusions

### Always Exclude (Never Overwrite):
- `.venv/` - Virtual environment (recreate if needed)
- `data/vector_store.npz` - User's indexed data
- `data/vector_meta*.json` - User's metadata
- `config/user_config.json` - User settings
- `.env` - API keys, secrets
- `.git/` - Git metadata (not needed in deployment)
- `__pycache__/`, `*.pyc` - Python bytecode

### Optional Exclude (User Choice):
- `data/vector_cache.json` - Incremental build cache
- `logs/` - Application logs

## Safety Features

### 1. Pre-Update Verification
- Check source repo is valid
- Verify no uncommitted changes in dev repo
- Ensure deployment target is writable

### 2. Backup Before Update
```python
backup_dir = f"backups/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
shutil.copytree("src/", f"{backup_dir}/src/")
```

### 3. Post-Update Verification
- Run health checks: `python tools/health-check.py`
- Test imports: `python -c "from core.hybrid_query import HybridQueryEngine"`
- Verify vector store intact

### 4. Rollback on Failure
```python
if verification_failed:
    restore_from_backup(latest_backup)
    log_error("Update failed, rolled back to previous version")
```

## Implementation Plan

### Phase 1: Core Update Script (Priority: HIGH)
- [x] Design architecture (this document)
- [ ] Implement `tools/update.py` with local source detection
- [ ] Add robocopy/rsync logic with exclusions
- [ ] Implement version comparison
- [ ] Add dry-run mode
- [ ] Create `update.bat` wrapper

### Phase 2: Git Integration (Priority: MEDIUM)
- [ ] Add remote repo support (git clone/pull)
- [ ] Implement commit hash comparison
- [ ] Add branch selection (master, develop, etc.)
- [ ] Handle git authentication (SSH keys, tokens)

### Phase 3: GUI Installer Integration (Priority: MEDIUM)
- [ ] Generate `.ue5query_deploy.json` during install
- [ ] Detect source repo git remote
- [ ] Add "Enable Auto-Updates" checkbox
- [ ] Validate remote repo URL

### Phase 4: Safety & Verification (Priority: HIGH)
- [ ] Implement backup before update
- [ ] Add post-update health checks
- [ ] Implement rollback on failure
- [ ] Add update logging

### Phase 5: Documentation (Priority: MEDIUM)
- [ ] Update DEPLOYMENT.md with update workflow
- [ ] Create UPDATE_GUIDE.md for users
- [ ] Add troubleshooting section
- [ ] Document team workflow

## Benefits

### For Solo Developer
1. **Instant sync** - Fix bug in dev repo, run `update.bat` in deployment
2. **No manual steps** - One command vs manual file copying
3. **Safe** - Backup/restore, verification, rollback
4. **Fast** - Local copy is instant vs git clone

### For Team Members
1. **Easy onboarding** - Install once, update forever
2. **Always current** - Pull from remote automatically
3. **No dev repo needed** - Can work without local dev environment
4. **Consistent versions** - Everyone on same version

### For CI/CD
1. **Automated deployment** - Integrate into build pipeline
2. **Version pinning** - Deploy specific commits/tags
3. **Rollback support** - Revert to previous version
4. **Audit trail** - Track what was deployed when

## Future Enhancements

### Auto-Update Check
```python
# Check for updates on startup
if should_check_updates():
    if updates_available():
        notify_user("Updates available! Run update.bat to install.")
```

### Selective Updates
```bash
# Update only source code, skip tools
update.bat --components src

# Update everything except GUI
update.bat --exclude management
```

### Multi-Environment Support
```json
"environments": {
  "dev": "D:\\DevTools\\UE5-Source-Query",
  "staging": "D:\\Staging\\Scripts",
  "production": "D:\\Production\\Scripts"
}
```

### Conflict Resolution
- Detect if user modified deployed files
- Offer merge options (keep local, use remote, merge)
- Create `.ue5query_local_changes.diff` for review

## Testing Strategy

### Test Cases

1. **Local Dev Repo Available**
   - ✅ Detect local repo correctly
   - ✅ Compare versions accurately
   - ✅ Copy files with exclusions
   - ✅ Preserve user data
   - ✅ Update deployment config

2. **No Local Dev Repo**
   - ✅ Fall back to remote
   - ✅ Git clone if first time
   - ✅ Git pull if already cloned
   - ✅ Handle auth (SSH, HTTPS)

3. **Update Failures**
   - ✅ Network timeout (remote)
   - ✅ Permission denied (disk full)
   - ✅ Verification failed
   - ✅ Rollback successful

4. **Edge Cases**
   - ✅ Local dev repo exists but not git repo
   - ✅ Remote URL invalid
   - ✅ User modified deployed files
   - ✅ Deployment config missing/corrupted

## Status

**Status:** ⏳ DESIGN PHASE (Dec 8, 2025)

**Next Steps:**
1. Implement `tools/update.py` core logic
2. Test local dev repo detection
3. Add robocopy integration
4. Create deployment config schema

---

**Design Approval:** Pending user review
