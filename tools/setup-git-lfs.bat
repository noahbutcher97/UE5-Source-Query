@echo off
setlocal EnableDelayedExpansion

REM ====================================================================
REM UE5 Source Query Tool - Git LFS Setup
REM ====================================================================
REM Configures Git LFS for sharing pre-built vector stores across team
REM Run this ONCE per repository (usually by team lead)
REM ====================================================================

set "SCRIPT_DIR=%~dp0"

echo.
echo ====================================================================
echo Git LFS Setup for Vector Store Sharing
echo ====================================================================
echo.
echo This script configures Git LFS to track vector store files.
echo.
echo IMPORTANT:
echo   - Only run this if your team wants to SHARE pre-built vector stores
echo   - Team members will need Git LFS installed to clone/pull
echo   - Vector store files can be 20-50 MB (within GitHub LFS free tier)
echo.
echo If unsure, see: docs\TEAM_SETUP.md
echo.

REM Check if Git is installed
where git >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git not found in PATH.
    echo.
    echo Please install Git from: https://git-scm.com/download/win
    echo.
    exit /b 1
)

REM Check if Git LFS is installed
where git-lfs >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git LFS not found in PATH.
    echo.
    echo Please install Git LFS from: https://git-lfs.github.com/
    echo.
    echo Quick install:
    echo   1. Download installer from https://git-lfs.github.com/
    echo   2. Run installer
    echo   3. Re-run this script
    echo.
    exit /b 1
)

echo [*] Git LFS detected:
git lfs version
echo.

REM Check if we're in a Git repository
if not exist "%SCRIPT_DIR%.git" (
    echo [ERROR] Not in a Git repository.
    echo.
    echo Initialize Git first:
    echo   git init
    echo   git add .
    echo   git commit -m "Initial commit"
    echo.
    exit /b 1
)

REM Initialize Git LFS for this repository
echo [1/4] Initializing Git LFS for this repository...
git lfs install
if errorlevel 1 (
    echo [ERROR] Failed to initialize Git LFS.
    echo Try running as Administrator.
    exit /b 1
)
echo.

REM Configure LFS tracking for vector store files
echo [2/4] Configuring LFS to track vector store files...

git lfs track "data/vector_store.npz"
if errorlevel 1 (
    echo [ERROR] Failed to track vector_store.npz
    exit /b 1
)

git lfs track "data/vector_meta.json"
if errorlevel 1 (
    echo [ERROR] Failed to track vector_meta.json
    exit /b 1
)

echo     [OK] data/vector_store.npz
echo     [OK] data/vector_meta.json
echo.

REM Verify .gitattributes was created
if not exist "%SCRIPT_DIR%.gitattributes" (
    echo [WARNING] .gitattributes not created. Creating manually...
    (
        echo data/vector_store.npz filter=lfs diff=lfs merge=lfs -text
        echo data/vector_meta.json filter=lfs diff=lfs merge=lfs -text
    ) > .gitattributes
)

echo [3/4] Verifying .gitattributes...
type .gitattributes
echo.

REM Check if vector store files exist
echo [4/4] Checking for existing vector store files...

set "VECTOR_EXISTS=0"
if exist "%SCRIPT_DIR%data\vector_store.npz" (
    echo     [*] Found: data\vector_store.npz
    set "VECTOR_EXISTS=1"
)

if exist "%SCRIPT_DIR%data\vector_meta.json" (
    echo     [*] Found: data\vector_meta.json
    set "VECTOR_EXISTS=1"
)

if "%VECTOR_EXISTS%"=="0" (
    echo     [!] No vector store files found.
    echo     You'll need to build them before committing:
    echo       rebuild-index.bat
    echo.
)
echo.

echo ====================================================================
echo Git LFS Setup Complete!
echo ====================================================================
echo.
echo Next steps:
echo.

if "%VECTOR_EXISTS%"=="1" (
    echo   1. Migrate existing files to LFS:
    echo      git lfs migrate import --include="data/vector_store.npz,data/vector_meta.json"
    echo.
    echo   2. Commit the .gitattributes file:
    echo      git add .gitattributes
    echo      git commit -m "Configure Git LFS for vector store"
    echo.
    echo   3. Commit vector store files:
    echo      git add data/vector_store.npz data/vector_meta.json
    echo      git commit -m "Add pre-built vector store for UE 5.3"
    echo.
    echo   4. Push to remote:
    echo      git push
    echo.
) else (
    echo   1. Commit .gitattributes:
    echo      git add .gitattributes
    echo      git commit -m "Configure Git LFS for vector store"
    echo      git push
    echo.
    echo   2. Build the vector store:
    echo      rebuild-index.bat
    echo.
    echo   3. Commit vector store files:
    echo      git add data/vector_store.npz data/vector_meta.json
    echo      git commit -m "Add pre-built vector store for UE 5.3"
    echo      git push
    echo.
)

echo IMPORTANT: Team members must have Git LFS installed before cloning!
echo   Installation: https://git-lfs.github.com/
echo   Command: git lfs install
echo.
echo ====================================================================

exit /b 0
