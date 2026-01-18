@echo off
setlocal EnableDelayedExpansion

REM ====================================================================
REM UE5 Source Query Tool - Setup & Deployment
REM ====================================================================

set "SCRIPT_DIR=%~dp0"

echo.
echo ====================================================================
echo UE5 Source Query - Setup
echo ====================================================================
echo.

REM 1. Check Python Availability
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    echo Please install Python 3.8+ from https://www.python.org/
    echo Ensure "Add Python to PATH" is checked during installation.
    pause
    exit /b 1
)

REM 2. Check Python Version (Simple check)
for /f "tokens=2" %%I in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%I"
echo [INFO] Found Python %PYTHON_VERSION%

REM 3. Launch GUI Installer
echo.
echo [INFO] Launching Deployment Wizard...
python "%SCRIPT_DIR%installer\gui_deploy.py"

if errorlevel 1 (
    echo.
    echo [ERROR] Installer exited with error code %errorlevel%.
    pause
    exit /b %errorlevel%
)

echo.
exit /b 0
