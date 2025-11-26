@echo off
setlocal EnableDelayedExpansion

REM ====================================================================
REM UE5 Source Query Tool - Add Directory to Index
REM ====================================================================
REM Incrementally adds a new directory to the existing vector store
REM
REM Usage:
REM   add-directory.bat <directory_path> [--verbose]
REM
REM Examples:
REM   add-directory.bat "C:/Program Files/Epic Games/UE_5.3/Engine/Source/Runtime/Physics"
REM   add-directory.bat "D:/MyProject/Source" --verbose
REM ====================================================================

set "SCRIPT_DIR=%~dp0"

echo.
echo ====================================================================
echo UE5 Source Query Tool - Add Directory to Index
echo ====================================================================
echo.

REM Check arguments
if "%~1"=="" (
    echo [ERROR] Directory path required
    echo.
    echo Usage: add-directory.bat ^<directory_path^> [--verbose]
    echo.
    echo Example:
    echo   add-directory.bat "C:/Program Files/Epic Games/UE_5.3/Engine/Source/Runtime/Physics"
    exit /b 1
)

set "NEW_DIR=%~1"
set "VERBOSE_FLAG="

REM Check for verbose flag
if /i "%~2"=="--verbose" set "VERBOSE_FLAG=--verbose"

REM Verify directory exists
if not exist "%NEW_DIR%" (
    echo [ERROR] Directory does not exist: %NEW_DIR%
    exit /b 1
)

echo Adding directory: %NEW_DIR%
echo.

REM Check if .env exists
if not exist "%SCRIPT_DIR%config\.env" (
    echo [ERROR] Configuration not found: config\.env
    echo Please run configure.bat first to set up your configuration
    exit /b 1
)

REM Load configuration
for /f "usebackq tokens=1,* delims==" %%a in ("%SCRIPT_DIR%config\.env") do (
    if "%%a"=="VECTOR_OUTPUT_DIR" set "VECTOR_DIR=%%b"
    if "%%a"=="EMBED_MODEL" set "EMBED_MODEL=%%b"
)

if "%VECTOR_DIR%"=="" (
    echo [ERROR] VECTOR_OUTPUT_DIR not configured in config\.env
    exit /b 1
)

echo Configuration:
echo   Vector Store: %VECTOR_DIR%
echo   Embedding Model: %EMBED_MODEL%
echo.

REM Check if existing index exists
if not exist "%VECTOR_DIR%\vector_store.npz" (
    echo [WARNING] No existing index found at: %VECTOR_DIR%\vector_store.npz
    echo.
    echo Would you like to create a new index? (This will be a full build, not incremental)
    set /p "CREATE=Continue? (y/N): "
    if /i not "!CREATE!"=="y" (
        echo Operation cancelled. Use rebuild-index.bat to create initial index.
        exit /b 0
    )
    set "INCREMENTAL_FLAG="
) else (
    echo Found existing index, will add incrementally...
    set "INCREMENTAL_FLAG=--incremental"
)

REM Check if Python and venv exist
if not exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found
    echo Please run install.bat or configure.bat first
    exit /b 1
)

echo.
echo Starting incremental indexing...
echo This may take a few seconds to a few minutes depending on directory size
echo.

REM Run the build script with incremental flag
cd /d "%SCRIPT_DIR%"
".venv\Scripts\python.exe" src\indexing\build_embeddings.py --root "%NEW_DIR%" !INCREMENTAL_FLAG! !VERBOSE_FLAG! --output-dir "%VECTOR_DIR%"

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to add directory to index
    echo Check logs for details: %SCRIPT_DIR%logs\
    exit /b 1
)

echo.
echo ====================================================================
echo Directory Added Successfully!
echo ====================================================================
echo.

REM Show updated index stats
if exist "%VECTOR_DIR%\vector_store.npz" (
    echo Updated Index Statistics:
    ".venv\Scripts\python.exe" -c "import numpy as np; data=np.load(r'%VECTOR_DIR%\vector_store.npz'); print(f'  Total Chunks: {len(data[\"embeddings\"])}'); print(f'  Dimensions: {data[\"embeddings\"].shape[1]}'); print(f'  Size: {data[\"embeddings\"].nbytes / 1024 / 1024:.1f} MB')"
    echo.
)

echo Vector store location: %VECTOR_DIR%
echo.
echo You can now query the updated index with:
echo   ask.bat "your question here"
echo.
echo ====================================================================

exit /b 0
