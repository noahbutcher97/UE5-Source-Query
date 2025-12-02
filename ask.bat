@echo off
setlocal EnableDelayedExpansion

REM UE5 Source Query Tool - Main Entry Point
REM Personal development tool for querying UE5.3 engine source code
REM
REM Usage: ask.bat "your question" [OPTIONS]
REM
REM Options:
REM   --top-k N              Number of results (default: 5)
REM   --scope SCOPE          engine, project, or all (default: engine)
REM   --format FORMAT        Output format: text, json, jsonl, xml, markdown, code (default: text)
REM   --no-code              Exclude code from output (metadata only)
REM   --max-lines N          Max lines per code snippet (default: 50)
REM   --filter FILTER        Filter results (e.g., 'type:struct AND macro:UPROPERTY')
REM   --json                 Output raw JSON (deprecated, use --format json)
REM   --port N               Server port (default: 8765)
REM   --no-server            Force local execution
REM
REM Examples:
REM   ask.bat "FHitResult members"
REM   ask.bat "FHitResult" --format json
REM   ask.bat "collision detection" --format markdown --no-code
REM   ask.bat "struct FVector" --format code --max-lines 20
REM   ask.bat "physics data" --filter "type:struct AND macro:UPROPERTY"

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

REM Run the CLI client (Tries server first, then falls back to local)
"%TOOL_ROOT%.venv\Scripts\python.exe" "%TOOL_ROOT%src\utils\cli_client.py" %*

REM Exit with script result
exit /b %errorlevel%
