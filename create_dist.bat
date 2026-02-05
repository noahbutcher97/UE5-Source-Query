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

REM Copy core files (excluding dev-only guides)
copy "%SCRIPT_DIR%Setup.bat" "%DIST_DIR%\" >nul
copy "%SCRIPT_DIR%requirements.txt" "%DIST_DIR%\" >nul
copy "%SCRIPT_DIR%requirements-gpu.txt" "%DIST_DIR%\" >nul 2>nul
copy "%SCRIPT_DIR%README.md" "%DIST_DIR%\" >nul
copy "%SCRIPT_DIR%ask.bat" "%DIST_DIR%\" >nul
copy "%SCRIPT_DIR%launcher.bat" "%DIST_DIR%\" >nul
copy "%SCRIPT_DIR%update.bat" "%DIST_DIR%\" >nul
copy "%SCRIPT_DIR%.indexignore" "%DIST_DIR%\" >nul
REM Explicitly skip CLAUDE.md and GEMINI.md (dev-only AI guides)

REM Copy directories (excluding dev-only files and temp files)
REM Note: robocopy exit codes 0-7 are success, > 7 is error

robocopy "%SCRIPT_DIR%installer" "%DIST_DIR%\installer" /E /NFL /NDL /NJH /NJS
if %ERRORLEVEL% GEQ 8 echo Warning: Some installer files may not have copied

REM Copy ue5_query (excluding research and deprecated PowerShell indexer)
robocopy "%SCRIPT_DIR%ue5_query" "%DIST_DIR%\ue5_query" /E /XD research __pycache__ /XF BuildSourceIndex.ps1 BuildSourceIndexAdmin.bat /NFL /NDL /NJH /NJS
if %ERRORLEVEL% GEQ 8 echo Warning: Some ue5_query files may not have copied

robocopy "%SCRIPT_DIR%config" "%DIST_DIR%\config" .gitkeep /NFL /NDL /NJH /NJS 2>nul
if %ERRORLEVEL% GEQ 8 mkdir "%DIST_DIR%\config"

REM Copy tools (excluding git-lfs setup)
robocopy "%SCRIPT_DIR%tools" "%DIST_DIR%\tools" /E /XF setup-git-lfs.bat /NFL /NDL /NJH /NJS
if %ERRORLEVEL% GEQ 8 echo Warning: Some tools files may not have copied

REM Copy production docs only (exclude Development and _archive)
robocopy "%SCRIPT_DIR%docs\Production" "%DIST_DIR%\docs\Production" /E /NFL /NDL /NJH /NJS
if %ERRORLEVEL% GEQ 8 echo Warning: Some docs files may not have copied

REM Copy tests (excluding dev artifacts)
robocopy "%SCRIPT_DIR%tests" "%DIST_DIR%\tests" /E /XF DEPLOYMENT_TEST_RESULTS.md /NFL /NDL /NJH /NJS
if %ERRORLEVEL% GEQ 8 echo Warning: Some test files may not have copied

REM Copy examples
robocopy "%SCRIPT_DIR%examples" "%DIST_DIR%\examples" /E /NFL /NDL /NJH /NJS 2>nul
if %ERRORLEVEL% GEQ 8 echo Note: Examples directory not found (optional)

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