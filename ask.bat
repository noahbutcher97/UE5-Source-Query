@echo off
setlocal EnableDelayedExpansion

REM UE5 Source Query Tool - Main Entry Point
REM Author: Your Name
REM Personal development tool for querying UE5.3 engine source code

set "TOOL_ROOT=%~dp0"

REM Check if venv exists
if not exist "%TOOL_ROOT%.venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found at: %TOOL_ROOT%.venv
    echo.
    echo Please create the virtual environment:
    echo   cd "%TOOL_ROOT%"
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements.txt
    exit /b 1
)

REM Activate the virtual environment
call "%TOOL_ROOT%.venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    exit /b 1
)

REM Run the hybrid query engine with all passed arguments
python "%TOOL_ROOT%src\core\hybrid_query.py" %*
set RESULT=%errorlevel%

REM Deactivate and exit
call "%TOOL_ROOT%.venv\Scripts\deactivate.bat"

REM Exit with script result
exit /b %RESULT%