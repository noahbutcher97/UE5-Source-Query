@echo off
REM Test deployment in target project

setlocal enabledelayedexpansion

set "TARGET_SCRIPTS=%1"
if "%TARGET_SCRIPTS%"=="" (
    echo ERROR: Usage: test_deployment.bat "D:\Path\To\Project\Scripts"
    exit /b 1
)

if not exist "%TARGET_SCRIPTS%" (
    echo ERROR: Target directory does not exist: %TARGET_SCRIPTS%
    exit /b 1
)

echo ========================================
echo Testing UE5 Source Query Deployment
echo Target: %TARGET_SCRIPTS%
echo ========================================
echo.

REM Test 1: Check venv exists
echo [TEST 1] Checking virtual environment...
if not exist "%TARGET_SCRIPTS%\.venv\Scripts\python.exe" (
    echo FAIL: Virtual environment not found
    exit /b 1
)
echo PASS: Virtual environment found

REM Test 2: Test imports in deployed environment
echo.
echo [TEST 2] Testing imports in deployed environment...
"%TARGET_SCRIPTS%\.venv\Scripts\python.exe" -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path('%TARGET_SCRIPTS%') / 'src')); from utils.config_manager import ConfigManager; print('PASS: ConfigManager imported')" 2>&1
if errorlevel 1 (
    echo FAIL: ConfigManager import failed
    exit /b 1
)

"%TARGET_SCRIPTS%\.venv\Scripts\python.exe" -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path('%TARGET_SCRIPTS%') / 'src')); from utils.source_manager import SourceManager; print('PASS: SourceManager imported')" 2>&1
if errorlevel 1 (
    echo FAIL: SourceManager import failed
    exit /b 1
)

"%TARGET_SCRIPTS%\.venv\Scripts\python.exe" -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path('%TARGET_SCRIPTS%') / 'src')); from core.hybrid_query import HybridQueryEngine; print('PASS: HybridQueryEngine imported')" 2>&1
if errorlevel 1 (
    echo FAIL: HybridQueryEngine import failed
    exit /b 1
)

REM Test 3: Test CLI client
echo.
echo [TEST 3] Testing CLI client...
"%TARGET_SCRIPTS%\.venv\Scripts\python.exe" "%TARGET_SCRIPTS%\src\utils\cli_client.py" --help >nul 2>&1
if errorlevel 1 (
    echo FAIL: CLI client failed to load
    exit /b 1
)
echo PASS: CLI client loads successfully

REM Test 4: Test simple query
echo.
echo [TEST 4] Testing simple query...
echo Testing: FHitResult --top-k 1
"%TARGET_SCRIPTS%\.venv\Scripts\python.exe" "%TARGET_SCRIPTS%\src\utils\cli_client.py" FHitResult --top-k 1 --no-server >nul 2>&1
if errorlevel 1 (
    echo FAIL: Query execution failed
    exit /b 1
)
echo PASS: Query executed successfully

echo.
echo ========================================
echo ALL TESTS PASSED
echo Deployment is functioning correctly
echo ========================================

exit /b 0
