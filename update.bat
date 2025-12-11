@echo off
REM UE5 Source Query - Bidirectional Update System
REM Pull updates from source OR push updates to deployments

setlocal enabledelayedexpansion

REM Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found!
    echo Run Setup.bat first to create .venv
    echo.
    pause
    exit /b 1
)

REM Run update script with all arguments passed through
.venv\Scripts\python.exe tools\update.py %*
set EXIT_CODE=%ERRORLEVEL%

REM If no arguments provided, show context-sensitive help
if "%~1"=="" (
    echo.
    if exist ".git" (
        if exist ".deployments_registry.json" (
            echo -----------------------------------------------------------
            echo DEV REPO DETECTED - Push updates to deployments:
            echo   update.bat --push-all              Push to all deployments
            echo   update.bat --push PATH             Push to specific deployment
            echo   update.bat --push-all --force      Force incremental update (same version)
            echo   update.bat --dry-run --push-all    Preview changes
            echo -----------------------------------------------------------
        )
    ) else if exist ".ue5query_deploy.json" (
        echo -----------------------------------------------------------
        echo DEPLOYED INSTALLATION - Pull updates from source:
        echo   update.bat                      Pull updates
        echo   update.bat --check              Check for updates only
        echo   update.bat --source local       Force local dev repo
        echo   update.bat --source remote      Force remote GitHub
        echo -----------------------------------------------------------
    )
)

echo.
if %EXIT_CODE% equ 0 (
    echo Press any key to exit...
) else (
    echo Press any key to exit...
)
pause >nul

endlocal
exit /b %EXIT_CODE%
