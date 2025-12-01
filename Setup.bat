@echo off
setlocal

REM ====================================================================
REM UE5 Source Query Tool - Setup & Deployment
REM ====================================================================
REM Double-click to install the tool.
REM Includes:
REM - Engine Version Detection
REM - Game Project Selection (Optional)
REM - Automated Installation
REM ====================================================================

set "SCRIPT_DIR=%~dp0"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python Not Found
    echo Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

REM Launch GUI deployment wizard
python "%SCRIPT_DIR%installer\gui_deploy.py"

exit /b %errorlevel%
