@echo off
setlocal EnableDelayedExpansion

REM ====================================================================
REM UE5 Source Query Tool - Search Server
REM Starts the persistent search server for instant queries.
REM ====================================================================

set "SCRIPT_DIR=%~dp0"
set "TOOL_ROOT=%SCRIPT_DIR%.."

echo.
echo ====================================================================
echo Starting Search Server...
echo ====================================================================
echo.

REM Check if .env exists
if not exist "%TOOL_ROOT%\config\.env" (
    echo [ERROR] Configuration not found: config\.env
    echo Please run Setup.bat first.
    exit /b 1
)

REM Check venv
if not exist "%TOOL_ROOT%\.venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo Please run Setup.bat first.
    exit /b 1
)

REM Launch server
echo [*] Initializing engine (this takes 5-10 seconds)...
echo [*] Press Ctrl+C to stop the server.
echo.

"%TOOL_ROOT%\.venv\Scripts\python.exe" -m ue5_query.server.retrieval_server --host 127.0.0.1 --port 8765

pause
