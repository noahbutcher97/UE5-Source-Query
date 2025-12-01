@echo off
setlocal EnableDelayedExpansion

REM ====================================================================
REM UE5 Source Query Tool - Fix Engine Paths
REM ====================================================================
REM This script regenerates EngineDirs.txt for your system's UE5 install
REM Useful when moving to a different machine or UE5 version
REM ====================================================================

set "SCRIPT_DIR=%~dp0"

echo.
echo ====================================================================
echo UE5 Source Query Tool - Fix Engine Paths
echo ====================================================================
echo.
echo This tool will regenerate EngineDirs.txt for your system.
echo.

REM Check if Python environment exists
if not exist "%SCRIPT_DIR%..\.venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment not found.
    echo Please run Setup.bat first.
    exit /b 1
)

REM Check if template exists
if not exist "%SCRIPT_DIR%..\src\indexing\EngineDirs.template.txt" (
    echo [ERROR] EngineDirs.template.txt not found.
    echo Cannot regenerate paths without template.
    echo.
    echo Recovery steps:
    echo   1. Re-run: Setup.bat
    echo.
    exit /b 1
)

REM Validate template has content
for /f %%i in ('find /c /v "" ^< "%SCRIPT_DIR%..\src\indexing\EngineDirs.template.txt"') do set TEMPLATE_LINES=%%i
if %TEMPLATE_LINES% LSS 5 (
    echo [ERROR] Template file appears empty or corrupted
    echo   Found only %TEMPLATE_LINES% lines, expected at least 5.
    echo.
    echo Recovery steps:
    echo   1. Delete corrupted template
    echo   2. Re-run: Setup.bat
    echo.
    exit /b 1
)

REM Run the detection script
echo Running UE5 engine path detection...
echo.

"%SCRIPT_DIR%..\.venv\Scripts\python.exe" "%SCRIPT_DIR%..\src\indexing\detect_engine_path.py" "%SCRIPT_DIR%..\src\indexing\EngineDirs.template.txt" "%SCRIPT_DIR%..\src\indexing\EngineDirs.txt"

if errorlevel 1 (
    echo.
    echo [ERROR] Path detection failed.
    exit /b 1
)

echo.
echo ====================================================================
echo Success!
echo ====================================================================
echo.
echo EngineDirs.txt has been regenerated for your system.
echo.
echo Next steps:
echo   1. Rebuild the vector index: rebuild-index.bat --force
echo   2. Start querying: ask.bat "your question"
echo.
echo ====================================================================

exit /b 0