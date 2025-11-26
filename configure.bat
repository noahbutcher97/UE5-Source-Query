@echo off
setlocal EnableDelayedExpansion

REM ====================================================================
REM UE5 Source Query Tool - Interactive Configuration
REM ====================================================================
REM This script provides an interactive setup wizard for configuration
REM ====================================================================

set "SCRIPT_DIR=%~dp0"
set "CONFIG_DIR=%SCRIPT_DIR%config"
set "ENV_FILE=%CONFIG_DIR%\.env"

cls
echo.
echo ====================================================================
echo UE5 Source Query Tool - Configuration Wizard
echo ====================================================================
echo.
echo This wizard will help you configure the UE5 Source Query tool.
echo.

REM Check if config directory exists
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"

REM Load existing config if available
set "EXISTING_API_KEY="
set "EXISTING_VECTOR_DIR="
set "EXISTING_EMBED_MODEL="
set "EXISTING_API_MODEL="

if exist "%ENV_FILE%" (
    echo [INFO] Found existing configuration
    for /f "usebackq tokens=1,* delims==" %%a in ("%ENV_FILE%") do (
        if "%%a"=="ANTHROPIC_API_KEY" set "EXISTING_API_KEY=%%b"
        if "%%a"=="VECTOR_OUTPUT_DIR" set "EXISTING_VECTOR_DIR=%%b"
        if "%%a"=="EMBED_MODEL" set "EXISTING_EMBED_MODEL=%%b"
        if "%%a"=="ANTHROPIC_MODEL" set "EXISTING_API_MODEL=%%b"
    )
    echo.
)

REM ====================================================================
REM 1. API Key Configuration
REM ====================================================================
echo.
echo [1/4] Anthropic API Key Configuration
echo --------------------------------------------------------------------
if not "!EXISTING_API_KEY!"=="" if not "!EXISTING_API_KEY!"=="your_api_key_here" (
    echo Current: !EXISTING_API_KEY:~0,20!...
    echo.
    set /p "CHANGE_KEY=Keep existing API key? (Y/n): "
    if /i "!CHANGE_KEY!"=="n" (
        set "API_KEY="
    ) else (
        set "API_KEY=!EXISTING_API_KEY!"
    )
) else (
    set "API_KEY="
)

if "!API_KEY!"=="" (
    echo.
    echo Get your API key from: https://console.anthropic.com/
    echo.
    set /p "API_KEY=Enter your Anthropic API key: "

    if "!API_KEY!"=="" (
        echo [WARNING] No API key provided. You'll need to configure this later.
        set "API_KEY=your_api_key_here"
    )
)

REM ====================================================================
REM 2. Vector Store Location
REM ====================================================================
echo.
echo [2/4] Vector Store Location
echo --------------------------------------------------------------------
echo The vector store contains the indexed UE5 engine source code.
echo Default location: %SCRIPT_DIR%data
echo.
if not "!EXISTING_VECTOR_DIR!"=="" (
    echo Current: !EXISTING_VECTOR_DIR!
    echo.
)

echo Options:
echo   1. Use default location (recommended)
echo   2. Specify custom location
echo   3. Use project-specific location
echo.
set /p "VECTOR_CHOICE=Select option (1-3) [1]: "

if "!VECTOR_CHOICE!"=="" set "VECTOR_CHOICE=1"

if "!VECTOR_CHOICE!"=="2" (
    set /p "VECTOR_DIR=Enter custom path: "
) else if "!VECTOR_CHOICE!"=="3" (
    set "VECTOR_DIR=%SCRIPT_DIR%\data\project"
    echo Using: !VECTOR_DIR!
) else (
    set "VECTOR_DIR=%SCRIPT_DIR%data"
)

REM ====================================================================
REM 3. Embedding Model Selection
REM ====================================================================
echo.
echo [3/4] Embedding Model Selection
echo --------------------------------------------------------------------
echo The embedding model determines how code is understood semantically.
echo.
if not "!EXISTING_EMBED_MODEL!"=="" (
    echo Current: !EXISTING_EMBED_MODEL!
    echo.
)

echo Available models:
echo   1. microsoft/unixcoder-base (recommended)
echo      - 768 dimensions
echo      - Trained on C++, Python, Java code
echo      - Best for code structure queries
echo      - Faster with GPU
echo.
echo   2. sentence-transformers/all-MiniLM-L6-v2
echo      - 384 dimensions
echo      - General-purpose English
echo      - Faster, smaller index
echo      - Good for conceptual queries
echo.
set /p "MODEL_CHOICE=Select model (1-2) [1]: "

if "!MODEL_CHOICE!"=="" set "MODEL_CHOICE=1"

if "!MODEL_CHOICE!"=="2" (
    set "EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2"
) else (
    set "EMBED_MODEL=microsoft/unixcoder-base"
)

REM ====================================================================
REM 4. Claude API Model Selection
REM ====================================================================
echo.
echo [4/4] Claude API Model Selection
echo --------------------------------------------------------------------
echo Select which Claude model to use for query responses.
echo.
if not "!EXISTING_API_MODEL!"=="" (
    echo Current: !EXISTING_API_MODEL!
    echo.
)

echo Available models:
echo   1. claude-3-haiku-20240307 (recommended)
echo      - Fast and cost-effective
echo      - Good for most queries
echo      - $0.25 per million input tokens
echo.
echo   2. claude-3-5-sonnet-20241022
echo      - Most capable current model
echo      - Best for complex queries
echo      - $3.00 per million input tokens
echo.
echo   3. claude-3-opus-20240229
echo      - Highest quality
echo      - Best for critical queries
echo      - $15.00 per million input tokens
echo.
set /p "API_MODEL_CHOICE=Select model (1-3) [1]: "

if "!API_MODEL_CHOICE!"=="" set "API_MODEL_CHOICE=1"

if "!API_MODEL_CHOICE!"=="2" (
    set "API_MODEL=claude-3-5-sonnet-20241022"
) else if "!API_MODEL_CHOICE!"=="3" (
    set "API_MODEL=claude-3-opus-20240229"
) else (
    set "API_MODEL=claude-3-haiku-20240307"
)

REM ====================================================================
REM Write Configuration
REM ====================================================================
echo.
echo ====================================================================
echo Configuration Summary
echo ====================================================================
echo API Key: !API_KEY:~0,20!...
echo Vector Store: !VECTOR_DIR!
echo Embedding Model: !EMBED_MODEL!
echo API Model: !API_MODEL!
echo.
echo Configuration will be saved to: %ENV_FILE%
echo.
set /p "CONFIRM=Save configuration? (Y/n): "

if /i "!CONFIRM!"=="n" (
    echo Configuration cancelled.
    exit /b 0
)

REM Write .env file
echo # UE5 Source Query Tool Configuration> "%ENV_FILE%"
echo # Generated by configure.bat on %DATE% %TIME%>> "%ENV_FILE%"
echo.>> "%ENV_FILE%"
echo # Anthropic API Key (required)>> "%ENV_FILE%"
echo ANTHROPIC_API_KEY=!API_KEY!>> "%ENV_FILE%"
echo.>> "%ENV_FILE%"
echo # Vector store output directory>> "%ENV_FILE%"
echo VECTOR_OUTPUT_DIR=!VECTOR_DIR!>> "%ENV_FILE%"
echo.>> "%ENV_FILE%"
echo # Python path (auto-configured)>> "%ENV_FILE%"
echo PYTHONPATH=%SCRIPT_DIR%.venv\Lib\site-packages>> "%ENV_FILE%"
echo.>> "%ENV_FILE%"
echo # Embedding model for code understanding>> "%ENV_FILE%"
echo EMBED_MODEL=!EMBED_MODEL!>> "%ENV_FILE%"
echo.>> "%ENV_FILE%"
echo # Claude API model for responses>> "%ENV_FILE%"
echo ANTHROPIC_MODEL=!API_MODEL!>> "%ENV_FILE%"
echo.>> "%ENV_FILE%"
echo # UE5 Engine source root (optional override)>> "%ENV_FILE%"
echo # UE_ENGINE_ROOT=C:/Program Files/Epic Games/UE_5.3/Engine>> "%ENV_FILE%"

echo.
echo [SUCCESS] Configuration saved!
echo.
echo ====================================================================
echo Next Steps
echo ====================================================================
echo.

REM Check if vector store needs to be built
if not exist "!VECTOR_DIR!\vector_store.npz" (
    echo The vector store index needs to be built.
    echo.
    echo Build options:
    echo   - With GPU: 2-3 minutes
    echo   - CPU only: 30-40 minutes
    echo.
    set /p "BUILD_NOW=Build index now? (y/N): "

    if /i "!BUILD_NOW!"=="y" (
        echo.
        echo Building vector store...
        if not exist "!VECTOR_DIR!" mkdir "!VECTOR_DIR!"

        if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
            "%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%src\indexing\build_embeddings.py" --dirs-file "%SCRIPT_DIR%src\indexing\EngineDirs.txt" --output-dir "!VECTOR_DIR!" --force --verbose
        ) else (
            echo [ERROR] Virtual environment not found. Please run install.bat first.
        )
    ) else (
        echo.
        echo Build the index later with:
        echo   ask.bat --build-index
    )
) else (
    echo Vector store found at: !VECTOR_DIR!
    echo.
    echo If you changed the embedding model, rebuild with:
    echo   ask.bat --build-index
)

echo.
echo Configuration complete!
echo Start querying with: ask.bat "your question here"
echo.
echo ====================================================================

exit /b 0