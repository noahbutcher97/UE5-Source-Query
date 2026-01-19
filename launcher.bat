@echo off
setlocal

REM ====================================================================
REM UE5 Source Query Tool - Unified Launcher
REM ====================================================================
REM Launches the central management dashboard.
REM ====================================================================

set "SCRIPT_DIR=%~dp0"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.8+.
    pause
    exit /b 1
)

REM Check venv (optional but good for running the gui)
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    set "PYTHON_CMD=%SCRIPT_DIR%.venv\Scripts\python.exe"
) else (
    set "PYTHON_CMD=python"
)

echo Launching Dashboard...
"%PYTHON_CMD%" -m ue5_query.management.gui_dashboard

exit /b %errorlevel%
