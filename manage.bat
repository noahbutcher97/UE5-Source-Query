@echo off
REM ====================================================================
REM UE5 Source Query Tool - Quick Management Launcher
REM ====================================================================
REM Launches the GUI management tool
REM ====================================================================

set "SCRIPT_DIR=%~dp0"

echo Launching UE5 Source Query Management Tool...
"%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%src\management\gui_manager.py"
