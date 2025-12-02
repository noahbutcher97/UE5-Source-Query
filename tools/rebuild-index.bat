@echo off
setlocal EnableDelayedExpansion

REM ====================================================================
REM UE5 Source Query Tool - Rebuild Index Script
REM ====================================================================
REM Rebuilds the vector store index from UE5 engine source code
REM
REM Usage:
REM   rebuild-index.bat [options]
REM
REM Options:
REM   --force          : Force rebuild even if index exists
REM   --verbose        : Show detailed progress
REM   --dirs-file FILE : Use custom directory list (default: src\indexing\EngineDirs.txt)
REM   --add-dir DIR    : Add specific directory to index
REM   --batch-size N   : Override embedding batch size (1-64, default from .env)
REM
REM Examples:
REM   rebuild-index.bat --force --verbose
REM   rebuild-index.bat --add-dir "C:/Custom/Engine/Source"
REM   rebuild-index.bat --batch-size 8 --force --verbose
REM ====================================================================

set "SCRIPT_DIR=%~dp0"

echo.
echo ====================================================================
echo UE5 Source Query Tool - Rebuild Vector Index
echo ====================================================================
echo.

REM Check if .env exists
if not exist "%SCRIPT_DIR%..\config\.env" (
    echo [ERROR] Configuration not found: config\.env
    echo Please run Setup.bat first to set up your configuration
    exit /b 1
)

REM Load configuration and set environment variables for Python
for /f "usebackq tokens=1,* delims==" %%a in ("%SCRIPT_DIR%..\config\.env") do (
    REM Set as environment variable for Python scripts
    set "%%a=%%b"

    REM Also keep batch-specific variables for display
    if "%%a"=="VECTOR_OUTPUT_DIR" set "VECTOR_DIR=%%b"
    if "%%a"=="EMBED_MODEL" set "EMBED_MODEL_DISPLAY=%%b"
)

if "%VECTOR_DIR%"=="" (
    echo [ERROR] VECTOR_OUTPUT_DIR not configured in config\.env
    exit /b 1
)

echo Configuration:
echo   Vector Store: %VECTOR_DIR%
echo   Embedding Model: %EMBED_MODEL_DISPLAY%
echo   Engine Root: %UE_ENGINE_ROOT%
echo.

REM Check if Python and venv exist
if not exist "%SCRIPT_DIR%..\.venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found
    echo.
    echo Recovery steps:
    echo   1. Run: Setup.bat
    echo.
    exit /b 1
)

REM Validate EngineDirs.txt exists and is not empty
if not exist "%SCRIPT_DIR%..\src\indexing\EngineDirs.txt" (
    echo [ERROR] EngineDirs.txt not found!
    echo.
    echo This file contains the list of UE5 directories to index.
    echo.
    echo Recovery steps:
    echo   1. Run: Setup.bat
    echo      This will detect your UE5 installation and generate the file.
    echo   2. Or run: fix-paths.bat
    echo      This will regenerate paths for your system.
    echo.
    exit /b 1
)

REM Count lines to ensure it's not empty
for /f %%i in ('find /c /v "" ^< "%SCRIPT_DIR%..\src\indexing\EngineDirs.txt"') do set LINE_COUNT=%%i
if %LINE_COUNT% LSS 5 (
    echo [ERROR] EngineDirs.txt appears empty or corrupted
    echo   Found only %LINE_COUNT% lines, expected at least 5.
    echo.
    echo Recovery steps:
    echo   1. Run: fix-paths.bat
    echo      This will regenerate the file.
    echo.
    exit /b 1
)

echo EngineDirs.txt validated: %LINE_COUNT% directory entries
echo.

REM Parse arguments
set "BUILD_ARGS=--dirs-file %SCRIPT_DIR%..\src\indexing\EngineDirs.txt"
set "SHOW_PROGRESS=0"

:parse_loop
if "%~1"=="" goto :end_parse
if /i "%~1"=="--force" set "BUILD_ARGS=%BUILD_ARGS% --force"
if /i "%~1"=="--verbose" (
    set "BUILD_ARGS=%BUILD_ARGS% --verbose"
    set "SHOW_PROGRESS=1"
)
if /i "%~1"=="--dirs-file" (
    set "BUILD_ARGS=%BUILD_ARGS% --dirs-file %~2"
    shift
)
if /i "%~1"=="--add-dir" (
    set "BUILD_ARGS=--root %~2"
    shift
)
if /i "%~1"=="--batch-size" (
    set "EMBED_BATCH_SIZE=%~2"
    echo [INFO] Overriding batch size to %~2
    shift
)
shift
goto :parse_loop
:end_parse

REM Ensure output directory exists
if not exist "%VECTOR_DIR%" mkdir "%VECTOR_DIR%"

REM Check existing index
if exist "%VECTOR_DIR%\vector_store.npz" (
    echo Found existing index at: %VECTOR_DIR%\vector_store.npz

    REM Check if --force was provided
    echo %BUILD_ARGS% | findstr /C:"--force" >nul
    if errorlevel 1 (
        echo.
        set /p "CONFIRM=Rebuild will overwrite existing index. Continue? (y/N): "
        if /i not "!CONFIRM!"=="y" (
            echo Operation cancelled.
            exit /b 0
        )
    ) else (
        echo --force flag detected, rebuilding automatically...
    )
    echo.
)

REM Backup existing index if it exists
if exist "%VECTOR_DIR%\vector_store.npz" (
    echo [*] Backing up existing vector store...

    REM Create timestamp
    for /f "tokens=1-3 delims=/ " %%a in ("%date%") do set DATE_STAMP=%%c%%a%%b
    for /f "tokens=1-3 delims=:. " %%a in ("%time%") do set TIME_STAMP=%%a%%b%%c
    set TIME_STAMP=%TIME_STAMP: =0%
    set BACKUP_TIMESTAMP=%DATE_STAMP%_%TIME_STAMP%

    REM Backup both files
    copy "%VECTOR_DIR%\vector_store.npz" "%VECTOR_DIR%\vector_store.npz.backup_%BACKUP_TIMESTAMP%" >nul 2>&1
    if exist "%VECTOR_DIR%\vector_meta.json" (
        copy "%VECTOR_DIR%\vector_meta.json" "%VECTOR_DIR%\vector_meta.json.backup_%BACKUP_TIMESTAMP%" >nul 2>&1
    )

    echo [✓] Backup created: vector_store.npz.backup_%BACKUP_TIMESTAMP%
    echo     To restore: copy "%VECTOR_DIR%\vector_store.npz.backup_%BACKUP_TIMESTAMP%" "%VECTOR_DIR%\vector_store.npz"
    echo.
)

echo Starting index rebuild...
echo This may take 2-3 minutes with GPU or 30-40 minutes with CPU
echo.

if %SHOW_PROGRESS%==1 (
    echo Running with verbose output...
    echo.
)

REM Run the build script
cd /d "%SCRIPT_DIR%.."
".venv\Scripts\python.exe" src\indexing\build_embeddings.py %BUILD_ARGS% --project-dirs-file "src\indexing\ProjectDirs.txt" --output-dir "%VECTOR_DIR%"

if errorlevel 1 (
    echo.
    echo [ERROR] Index build failed
    echo Check logs for details: %SCRIPT_DIR%..\logs\
    exit /b 1
)

echo.
echo ====================================================================
echo Index Build Complete! Running metadata enrichment...
echo ====================================================================
echo.

REM Run metadata enrichment to create vector_meta_enriched.json
echo [*] Enriching metadata with entity detection and UE5 macros...
".venv\Scripts\python.exe" src\indexing\metadata_enricher.py "%VECTOR_DIR%\vector_meta.json" "%VECTOR_DIR%\vector_meta_enriched.json"

if errorlevel 1 (
    echo [WARNING] Metadata enrichment failed (index still usable)
    echo The base index works fine, but advanced filtering may be limited
) else (
    echo [OK] Metadata enrichment complete
)

echo.
echo ====================================================================
echo Rebuild Complete!
echo ====================================================================
echo.

REM Show index stats if verbose
if %SHOW_PROGRESS%==1 (
    if exist "%VECTOR_DIR%\vector_store.npz" (
        echo Index Statistics:
        ".venv\Scripts\python.exe" -c "import numpy as np; data=np.load(r'%VECTOR_DIR%\vector_store.npz'); print(f'  Chunks: {len(data[\"embeddings\"])}'); print(f'  Dimensions: {data[\"embeddings\"].shape[1]}'); print(f'  Size: {data[\"embeddings\"].nbytes / 1024 / 1024:.1f} MB')"
        echo.
    )
)

echo Vector store location: %VECTOR_DIR%
echo.
echo You can now query the index with:
echo   ask.bat "your question here"
echo.
echo ====================================================================

exit /b 0
