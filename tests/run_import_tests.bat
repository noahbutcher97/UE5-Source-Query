@echo off
REM Run universal import tests

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "VENV=%PROJECT_ROOT%\.venv\Scripts\python.exe"

echo ========================================
echo Running Universal Import Tests
echo ========================================
echo.

REM Check if venv exists
if not exist "%VENV%" (
    echo ERROR: Virtual environment not found at: %VENV%
    echo Please run Setup.bat first.
    exit /b 1
)

REM Run the tests
"%VENV%" "%SCRIPT_DIR%\test_universal_imports.py"
set TEST_RESULT=!ERRORLEVEL!

echo.
echo ========================================
if !TEST_RESULT! equ 0 (
    echo ALL TESTS PASSED
) else (
    echo TESTS FAILED
)
echo ========================================

exit /b !TEST_RESULT!
