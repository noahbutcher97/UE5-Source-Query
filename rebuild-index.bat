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
REM
REM Examples:
REM   rebuild-index.bat --force --verbose
REM   rebuild-index.bat --add-dir "C:/Custom/Engine/Source"
REM ====================================================================

set "SCRIPT_DIR=%~dp0"

echo.
echo ====================================================================
echo UE5 Source Query Tool - Rebuild Vector Index
echo ====================================================================
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

REM Check if Python and venv exist
if not exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found
    echo Please run install.bat or configure.bat first
    exit /b 1
)

REM Parse arguments
set "BUILD_ARGS=--dirs-file src\indexing\EngineDirs.txt"
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

echo Starting index rebuild...
echo This may take 2-3 minutes with GPU or 30-40 minutes with CPU
echo.

if %SHOW_PROGRESS%==1 (
    echo Running with verbose output...
    echo.
)

REM Run the build script
cd /d "%SCRIPT_DIR%"
".venv\Scripts\python.exe" src\indexing\build_embeddings.py %BUILD_ARGS% --output-dir "%VECTOR_DIR%"

if errorlevel 1 (
    echo.
    echo [ERROR] Index build failed
    echo Check logs for details: %SCRIPT_DIR%logs\
    exit /b 1
)

echo.
echo ====================================================================
echo Index Rebuild Complete!
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
