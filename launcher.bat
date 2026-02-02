@echo off
setlocal enabledelayedexpansion

REM ====================================================================
REM UE5 Source Query Tool - Smart Launcher
REM ====================================================================

cd /d "%~dp0"

REM 1. Check for Existing Environment (Fast Path)
REM If we have a venv (System or Private based), we are good.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" bootstrap.py %*
    exit /b !errorlevel!
)

REM 2. First Run - No Venv found.
REM We need to decide on a runtime (Private or System).
echo [INFO] Initializing environment...
echo Launching Setup Wizard...

powershell -ExecutionPolicy Bypass -File tools\provision.ps1

if !errorlevel! neq 0 (
    echo [ERROR] Setup cancelled or failed.
    pause
    exit /b 1
)

REM 3. Handoff to Bootstrap (using whatever provisioner configured)
if defined PYTHON_CMD_OVERRIDE (
    "%PYTHON_CMD_OVERRIDE%" bootstrap.py %*
) else (
    REM Fallback to standard python if provisioner chose 'System'
    python bootstrap.py %*
)

if !errorlevel! neq 0 pause
