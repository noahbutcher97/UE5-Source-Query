@echo off
setlocal EnableDelayedExpansion

REM ====================================================================
REM UE5 Source Query Tool - Update Script
REM ====================================================================
REM Updates an existing installation with latest source files
REM
REM Usage:
REM   update.bat [target_directory]
REM
REM This script:
REM   - Copies updated source files from main repo
REM   - Preserves existing .env configuration
REM   - Preserves existing vector store data
REM   - Updates dependencies if requirements.txt changed
REM ====================================================================

set "SCRIPT_DIR=%~dp0"

echo.
echo ====================================================================
echo UE5 Source Query Tool - Update Existing Installation
echo ====================================================================
echo.

REM Parse arguments
set "TARGET_DIR=%~1"

REM Default to current directory if not specified
if "%TARGET_DIR%"=="" (
    set "TARGET_DIR=%CD%"
) else (
    REM Normalize path - check if Scripts\UE5-Source-Query already in path
    echo !TARGET_DIR! | findstr /C:"Scripts\UE5-Source-Query" >nul
    if errorlevel 1 (
        set "TARGET_DIR=%TARGET_DIR%\Scripts\UE5-Source-Query"
    )
)

echo Update Target: %TARGET_DIR%
echo.

REM Verify target exists and is valid installation
if not exist "%TARGET_DIR%\ask.bat" (
    echo [ERROR] Target directory does not contain a valid installation
    echo Expected file not found: %TARGET_DIR%\ask.bat
    echo.
    echo Please specify the correct installation directory
    exit /b 1
)

if not exist "%TARGET_DIR%\.venv" (
    echo [WARNING] Virtual environment not found at: %TARGET_DIR%\.venv
    echo This may not be a complete installation
    echo.
)

echo [1/4] Backing up configuration...
if exist "%TARGET_DIR%\config\.env" (
    copy "%TARGET_DIR%\config\.env" "%TARGET_DIR%\config\.env.backup" >nul
    echo    Backed up: config\.env
) else (
    echo    No configuration file found - will need to run configure.bat
)

echo [2/4] Updating source files...
REM Use Python helper script for reliable copying
set "SRC_DIR=%SCRIPT_DIR:~0,-1%"
python "%SCRIPT_DIR%install_helper.py" "%SRC_DIR%" "%TARGET_DIR%"
if errorlevel 1 (
    echo [ERROR] Failed to update source files
    if exist "%TARGET_DIR%\config\.env.backup" (
        echo Restoring backup...
        copy "%TARGET_DIR%\config\.env.backup" "%TARGET_DIR%\config\.env" >nul
    )
    exit /b 1
)

echo [3/4] Checking for dependency updates...
if exist "%TARGET_DIR%\.venv\Scripts\python.exe" (
    echo    Upgrading pip...
    "%TARGET_DIR%\.venv\Scripts\python.exe" -m pip install --upgrade pip --quiet

    echo    Updating dependencies...
    "%TARGET_DIR%\.venv\Scripts\python.exe" -m pip install -r "%TARGET_DIR%\requirements.txt" --quiet --upgrade

    echo    Verifying installation...
    "%TARGET_DIR%\.venv\Scripts\python.exe" -c "import sentence_transformers; import anthropic; print('Dependencies OK')" >nul 2>&1
    if errorlevel 1 (
        echo [WARNING] Dependency verification failed - you may need to reinstall
    ) else (
        echo    Dependencies updated successfully
    )
) else (
    echo [WARNING] Virtual environment not found - skipping dependency updates
)

echo [4/4] Cleaning up...
if exist "%TARGET_DIR%\config\.env.backup" (
    del "%TARGET_DIR%\config\.env.backup"
)

echo.
echo ====================================================================
echo Update Complete!
echo ====================================================================
echo.
echo Location: %TARGET_DIR%
echo.
echo Notes:
echo   - Configuration preserved
echo   - Vector store data preserved (if exists)
echo   - Source files updated to latest version
echo.
echo Next Steps:
if not exist "%TARGET_DIR%\config\.env" (
    echo   1. Run configure.bat to set up configuration
)
if not exist "%TARGET_DIR%\data\vector_store.npz" (
    echo   2. Run rebuild-index.bat to build vector store
)
echo   - Test with: ask.bat "test query"
echo.
echo ====================================================================

exit /b 0