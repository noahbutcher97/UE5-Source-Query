@echo off
setlocal EnableDelayedExpansion

REM UE5 Source Query Tool - Main Entry Point
REM Author: Your Name
REM Personal development tool for querying UE5.3 engine source code

set "TOOL_ROOT=%~dp0"

REM Check if venv exists
if not exist "%TOOL_ROOT%.venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at: %TOOL_ROOT%.venv
    echo.
    echo Recovery steps:
    echo   1. Run: install.bat
    echo   2. Or run: configure.bat
    echo   3. Or manually:
    echo      cd "%TOOL_ROOT%"
    echo      python -m venv .venv
    echo      .venv\Scripts\pip install -r requirements.txt
    echo.
    exit /b 1
)

REM Verify venv is functional (test critical imports)
"%TOOL_ROOT%.venv\Scripts\python.exe" -c "import sentence_transformers; import anthropic" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Virtual environment is broken or missing packages
    echo.
    echo Recovery steps:
    echo   1. Delete .venv directory
    echo   2. Run: configure.bat
    echo   3. Or reinstall packages:
    echo      .venv\Scripts\pip install -r requirements.txt
    echo.
    exit /b 1
)

REM Run the hybrid query engine with all passed arguments using venv python directly
"%TOOL_ROOT%.venv\Scripts\python.exe" "%TOOL_ROOT%src\core\hybrid_query.py" %*

REM Exit with script result
exit /b %errorlevel%
