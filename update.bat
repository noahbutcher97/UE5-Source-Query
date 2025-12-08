@echo off
REM UE5 Source Query - Smart Update System
REM Updates deployed installation from local dev repo or remote GitHub

echo ============================================================
echo UE5 Source Query - Smart Update
echo ============================================================
echo.

REM Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found!
    echo This script must be run from a deployed UE5 Source Query installation.
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

REM Run update script with all arguments passed through
.venv\Scripts\python.exe tools\update.py %*

REM Check exit code
if errorlevel 1 (
    echo.
    echo ============================================================
    echo Update FAILED!
    echo ============================================================
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

echo.
echo ============================================================
echo Update COMPLETE!
echo ============================================================
echo.
echo You may need to restart any running applications.
echo.
echo Press any key to exit...
pause >nul
exit /b 0
