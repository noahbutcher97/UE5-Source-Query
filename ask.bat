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
    echo Please create the virtual environment:
    echo   cd "%TOOL_ROOT%"
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements.txt
    exit /b 1
)

REM Run the hybrid query engine with all passed arguments using venv python directly
"%TOOL_ROOT%.venv\Scripts\python.exe" "%TOOL_ROOT%src\core\hybrid_query.py" %*

REM Exit with script result
exit /b %errorlevel%
