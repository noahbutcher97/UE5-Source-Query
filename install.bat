@echo off
setlocal EnableDelayedExpansion

REM ====================================================================
REM UE5 Source Query Tool - Automated Installation Script
REM ====================================================================
REM This script sets up the UE5 Source Query tool in a new project
REM
REM Usage:
REM   install.bat [target_directory] [--gpu] [--build-index]
REM
REM Options:
REM   target_directory  : Where to install (default: current directory)
REM   --gpu            : Install GPU acceleration support (CUDA 12.8)
REM   --build-index    : Build vector index after installation
REM ====================================================================

echo.
echo ====================================================================
echo UE5 Source Query Tool - Installation
echo ====================================================================
echo.

REM Parse arguments
set "TARGET_DIR=%~1"
set "INSTALL_GPU=0"
set "BUILD_INDEX=0"

REM Check for optional flags
:parse_args
if "%~2"=="" goto :end_parse
if /i "%~2"=="--gpu" set "INSTALL_GPU=1"
if /i "%~2"=="--build-index" set "BUILD_INDEX=1"
shift
goto :parse_args
:end_parse

REM Default to current directory if not specified
if "%TARGET_DIR%"=="" set "TARGET_DIR=%CD%"

REM Normalize path
set "TARGET_DIR=%TARGET_DIR%\Scripts\UE5-Source-Query"

echo Installation Target: %TARGET_DIR%
echo GPU Acceleration: !INSTALL_GPU!
echo Build Index: !BUILD_INDEX!
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.8+ is required but not found in PATH
    echo Please install Python from https://www.python.org/downloads/
    exit /b 1
)

REM Capture script directory BEFORE changing directories
set "SCRIPT_DIR=%~dp0"

echo [1/7] Creating directory structure...
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"
cd /d "%TARGET_DIR%"

REM Copy source files
echo [2/7] Copying source files...

REM Create directory structure
if not exist "src" mkdir "src"
if not exist "src\core" mkdir "src\core"
if not exist "src\indexing" mkdir "src\indexing"
if not exist "config" mkdir "config"
if not exist "data" mkdir "data"
if not exist "logs" mkdir "logs"

REM Use Python helper script for reliable cross-platform copying
python "%SCRIPT_DIR%install_helper.py" "%SCRIPT_DIR%" "%CD%"
if errorlevel 1 (
    echo [ERROR] Failed to copy source files
    exit /b 1
)

echo [3/7] Creating virtual environment...
python -m venv .venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment
    exit /b 1
)

echo [4/7] Installing Python dependencies...
if !INSTALL_GPU!==1 (
    echo    - Installing with GPU acceleration ^(CUDA 12.8^)...
    .venv\Scripts\pip install --upgrade pip >nul
    .venv\Scripts\pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128 >nul
    .venv\Scripts\pip install -r requirements.txt >nul
) else (
    echo    - Installing CPU-only version...
    .venv\Scripts\pip install --upgrade pip >nul
    .venv\Scripts\pip install -r requirements.txt >nul
)

if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    exit /b 1
)

echo [5/7] Configuring environment...
REM Create .env file if it doesn't exist
if not exist "config\.env" (
    echo ANTHROPIC_API_KEY=your_api_key_here> config\.env
    echo PYTHONPATH=%TARGET_DIR%\.venv\Lib\site-packages>> config\.env
    echo VECTOR_OUTPUT_DIR=%TARGET_DIR%\data>> config\.env
    echo.
    echo [WARNING] Created config\.env - Please add your ANTHROPIC_API_KEY
)

echo [6/7] Verifying installation...
.venv\Scripts\python.exe -c "import sentence_transformers; import anthropic; print('Dependencies OK')" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Dependency verification failed
    exit /b 1
)

if !INSTALL_GPU!==1 (
    .venv\Scripts\python.exe -c "import torch; print(f'GPU Available: {torch.cuda.is_available()}')"
)

echo [7/7] Installation complete!
echo.

echo.
echo ====================================================================
echo Installation Summary
echo ====================================================================
echo Location: %TARGET_DIR%
echo.
echo Next Steps:
echo   1. Run configuration wizard: configure.bat (recommended)
echo      OR manually edit: config\.env
echo   2. Build the vector index
echo   3. Start querying!
echo.

REM Ask if user wants to configure now
set /p "RUN_CONFIG=Run configuration wizard now? (Y/n): "
if /i "!RUN_CONFIG!"=="n" (
    echo.
    echo Configuration skipped. Run 'configure.bat' when ready.
    echo.
) else (
    echo.
    call configure.bat
    goto :skip_manual_build
)

if !BUILD_INDEX!==1 (
    echo Building vector index...
    echo This may take 2-3 minutes with GPU or 30-40 minutes with CPU
    echo.
    .venv\Scripts\python.exe src\indexing\build_embeddings.py --dirs-file src\indexing\EngineDirs.txt --force --verbose
)

:skip_manual_build
echo.
echo Documentation: docs\Guides\UE5_ENGINE_SOURCE_QUERY_GUIDE.md
echo ====================================================================
echo.

exit /b 0
