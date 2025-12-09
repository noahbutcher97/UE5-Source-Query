@echo off
REM ====================================================================
REM UE5 Source Query Tool - Test Runner
REM ====================================================================
REM Runs all tests and displays results
REM ====================================================================

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\"

echo.
echo ====================================================================
echo UE5 Source Query Tool - Running Tests
echo ====================================================================
echo.

REM Activate virtual environment if it exists
if exist "%PROJECT_ROOT%.venv\Scripts\activate.bat" (
    call "%PROJECT_ROOT%.venv\Scripts\activate.bat"
    echo Virtual environment activated
) else (
    echo WARNING: Virtual environment not found
    echo Run Setup.bat first
    pause
    exit /b 1
)

REM Run tests
python "%PROJECT_ROOT%tests\run_tests.py" %*

set "EXIT_CODE=%ERRORLEVEL%"

echo.
if %EXIT_CODE%==0 (
    echo ====================================================================
    echo All tests passed!
    echo ====================================================================
) else (
    echo ====================================================================
    echo Some tests failed. See output above for details.
    echo ====================================================================
)

echo.
pause
exit /b %EXIT_CODE%
