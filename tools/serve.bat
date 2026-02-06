@echo off
setlocal enabledelayedexpansion

REM ====================================================================
REM UE5 Source Query - Async Server Launcher (v2.1)
REM ====================================================================

cd /d "%~dp0\.."

REM 1. Environment Check
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment missing. Run launcher.bat first.
    pause
    exit /b 1
)

REM 2. Port and Host Config
set HOST=127.0.0.1
set PORT=8000

echo [INFO] Starting Asynchronous API Server...
echo [INFO] Host: %HOST%
echo [INFO] Port: %PORT%
echo [INFO] Documentation: http://%HOST%:%PORT%/docs
echo.

".venv\Scripts\python.exe" -m uvicorn ue5_query.server.app:app --host %HOST% --port %PORT% --log-level info

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Server failed to start.
    pause
)