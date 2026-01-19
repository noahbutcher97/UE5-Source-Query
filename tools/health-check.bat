@echo off
setlocal EnableDelayedExpansion

REM ====================================================================
REM UE5 Source Query Tool - Health Check
REM ====================================================================
REM Validates all components are correctly installed and functional
REM ====================================================================

set "SCRIPT_DIR=%~dp0"

echo.
echo ====================================================================
echo UE5 Source Query - Health Check
echo ====================================================================
echo.

REM Check if Python is available at all
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH
    echo.
    echo Please install Python 3.8+ from:
    echo   https://www.python.org/downloads/
    echo.
    exit /b 1
)

REM Check if virtual environment exists
if not exist "%SCRIPT_DIR%..\.venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found
    echo.
    echo Please run: Setup.bat
    echo.
    exit /b 1
)

REM Run the health check script
cd /d "%SCRIPT_DIR%.."
".venv\Scripts\python.exe" -m ue5_query.utils.verify_installation %*

REM Capture exit code
set HEALTH_EXIT_CODE=%errorlevel%

if %HEALTH_EXIT_CODE% EQU 0 (
    REM All checks passed
    exit /b 0
) else if %HEALTH_EXIT_CODE% EQU 2 (
    REM Warnings only
    echo Note: System is functional despite warnings.
    exit /b 0
) else (
    REM Critical failures
    echo.
    echo [FAILED] Critical issues found. Please address them before using the tool.
    echo.
    exit /b 1
)
