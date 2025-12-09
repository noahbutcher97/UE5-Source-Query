@echo off
setlocal EnableDelayedExpansion

REM ====================================================================
REM UE5 Source Query Tool - Distribution Packager
REM ====================================================================
REM Creates a clean zip file for team distribution.
REM ====================================================================

set "SCRIPT_DIR=%~dp0"
set "DIST_NAME=UE5-Query-Suite"
set "DIST_DIR=%SCRIPT_DIR%dist_temp"

echo Creating distribution package: %DIST_NAME%...

REM Clean previous build
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
if exist "%DIST_NAME%.zip" del "%DIST_NAME%.zip"

mkdir "%DIST_DIR%"

REM Copy core files
copy "%SCRIPT_DIR%Setup.bat" "%DIST_DIR%\" >nul
copy "%SCRIPT_DIR%requirements.txt" "%DIST_DIR%\" >nul
copy "%SCRIPT_DIR%requirements-gpu.txt" "%DIST_DIR%\" >nul
copy "%SCRIPT_DIR%README.md" "%DIST_DIR%\" >nul
copy "%SCRIPT_DIR%ask.bat" "%DIST_DIR%\" >nul
copy "%SCRIPT_DIR%launcher.bat" "%DIST_DIR%\" >nul

REM Copy directories (excluding large/temp files)
REM Note: robocopy exit codes 0-7 are success, > 7 is error
robocopy "%SCRIPT_DIR%installer" "%DIST_DIR%\installer" /E /NFL /NDL /NJH /NJS
if %ERRORLEVEL% GEQ 8 echo Warning: Some installer files may not have copied

robocopy "%SCRIPT_DIR%src" "%DIST_DIR%\src" /E /XD __pycache__ /NFL /NDL /NJH /NJS
if %ERRORLEVEL% GEQ 8 echo Warning: Some src files may not have copied

robocopy "%SCRIPT_DIR%config" "%DIST_DIR%\config" .gitkeep /NFL /NDL /NJH /NJS
if %ERRORLEVEL% GEQ 8 mkdir "%DIST_DIR%\config"

robocopy "%SCRIPT_DIR%tools" "%DIST_DIR%\tools" /E /NFL /NDL /NJH /NJS
if %ERRORLEVEL% GEQ 8 echo Warning: Some tools files may not have copied

robocopy "%SCRIPT_DIR%docs" "%DIST_DIR%\docs" /E /NFL /NDL /NJH /NJS
if %ERRORLEVEL% GEQ 8 echo Warning: Some docs files may not have copied

REM Reset error level (robocopy uses non-zero exit codes for success)
(call )

REM Create Zip (using temporary PowerShell script to avoid quoting issues)
echo Zipping files...
set "PS_SCRIPT=%SCRIPT_DIR%_zip.ps1"
echo Compress-Archive -Path '%DIST_DIR%\*' -DestinationPath '%SCRIPT_DIR%%DIST_NAME%.zip' -Force > "%PS_SCRIPT%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%"
if errorlevel 1 (
    echo [ERROR] Failed to create zip file.
    del "%PS_SCRIPT%"
    exit /b 1
)

del "%PS_SCRIPT%"

REM Cleanup
rmdir /s /q "%DIST_DIR%"

echo.

echo [SUCCESS] Package created: %DIST_NAME%.zip
echo Give this file to your team!
pause
exit /b 0