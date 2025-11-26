@echo off
setlocal EnableDelayedExpansion

REM ====================================================================
REM UE5 Source Query Tool - Directory Management
REM ====================================================================
REM Manage indexed directories - add, remove, list, and rebuild
REM
REM Usage:
REM   manage-directories.bat list
REM   manage-directories.bat add <directory>
REM   manage-directories.bat remove <directory>
REM   manage-directories.bat rebuild [--verbose]
REM   manage-directories.bat gui
REM
REM Examples:
REM   manage-directories.bat list
REM   manage-directories.bat add "C:/Program Files/Epic Games/UE_5.3/Engine/Source/Runtime/Physics"
REM   manage-directories.bat remove "C:/Custom/Path"
REM   manage-directories.bat rebuild --verbose
REM   manage-directories.bat gui
REM ====================================================================

set "SCRIPT_DIR=%~dp0"
set "CONFIG_FILE=%SCRIPT_DIR%config\indexed_directories.txt"

REM Check command
if "%~1"=="" goto :show_usage
if /i "%~1"=="list" goto :list_dirs
if /i "%~1"=="add" goto :add_dir
if /i "%~1"=="remove" goto :remove_dir
if /i "%~1"=="rebuild" goto :rebuild_from_list
if /i "%~1"=="gui" goto :launch_gui

:show_usage
echo.
echo ====================================================================
echo UE5 Source Query Tool - Directory Management
echo ====================================================================
echo.
echo Usage:
echo   manage-directories.bat list           - Show all indexed directories
echo   manage-directories.bat add ^<dir^>      - Add directory to index
echo   manage-directories.bat remove ^<dir^>   - Remove directory from index
echo   manage-directories.bat rebuild        - Rebuild index from directory list
echo   manage-directories.bat gui            - Launch GUI management tool
echo.
echo Examples:
echo   manage-directories.bat list
echo   manage-directories.bat add "C:/Program Files/Epic Games/UE_5.3/Engine/Source"
echo   manage-directories.bat remove "C:/Custom/Path"
echo   manage-directories.bat rebuild --verbose
echo   manage-directories.bat gui
echo.
echo ====================================================================
exit /b 0

:list_dirs
echo.
echo ====================================================================
echo Indexed Directories
echo ====================================================================
echo.
if not exist "%CONFIG_FILE%" (
    echo No directories configured yet.
    echo Use 'manage-directories.bat add ^<directory^>' to add directories
) else (
    set "COUNT=0"
    for /f "usebackq delims=" %%i in ("%CONFIG_FILE%") do (
        set /a COUNT+=1
        echo [!COUNT!] %%i
    )
    echo.
    echo Total: !COUNT! directories
)
echo.
echo ====================================================================
exit /b 0

:add_dir
if "%~2"=="" (
    echo [ERROR] Directory path required
    echo Usage: manage-directories.bat add ^<directory^>
    exit /b 1
)

set "NEW_DIR=%~2"

REM Verify directory exists
if not exist "%NEW_DIR%" (
    echo [ERROR] Directory does not exist: %NEW_DIR%
    exit /b 1
)

REM Create config file if doesn't exist
if not exist "%CONFIG_FILE%" (
    if not exist "%SCRIPT_DIR%config" mkdir "%SCRIPT_DIR%config"
    type nul > "%CONFIG_FILE%"
)

REM Check if already in list
findstr /C:"%NEW_DIR%" "%CONFIG_FILE%" >nul 2>&1
if not errorlevel 1 (
    echo [INFO] Directory already in index: %NEW_DIR%
    exit /b 0
)

REM Add to config file
echo %NEW_DIR%>> "%CONFIG_FILE%"

echo.
echo ====================================================================
echo Added Directory to Index Configuration
echo ====================================================================
echo.
echo Directory: %NEW_DIR%
echo.
echo Run 'manage-directories.bat rebuild' to update the vector index
echo Or run 'add-directory.bat "%NEW_DIR%"' to add incrementally
echo.
echo ====================================================================
exit /b 0

:remove_dir
if "%~2"=="" (
    echo [ERROR] Directory path required
    echo Usage: manage-directories.bat remove ^<directory^>
    exit /b 1
)

set "REMOVE_DIR=%~2"

if not exist "%CONFIG_FILE%" (
    echo [ERROR] No directory configuration found
    exit /b 1
)

REM Create temp file without the removed directory
set "TEMP_FILE=%CONFIG_FILE%.tmp"
type nul > "%TEMP_FILE%"

set "FOUND=0"
for /f "usebackq delims=" %%i in ("%CONFIG_FILE%") do (
    if not "%%i"=="%REMOVE_DIR%" (
        echo %%i>> "%TEMP_FILE%"
    ) else (
        set "FOUND=1"
    )
)

if "%FOUND%"=="0" (
    del "%TEMP_FILE%"
    echo [ERROR] Directory not found in configuration: %REMOVE_DIR%
    exit /b 1
)

REM Replace config file
move /y "%TEMP_FILE%" "%CONFIG_FILE%" >nul

echo.
echo ====================================================================
echo Removed Directory from Configuration
echo ====================================================================
echo.
echo Directory: %REMOVE_DIR%
echo.
echo Run 'manage-directories.bat rebuild' to update the vector index
echo.
echo ====================================================================
exit /b 0

:rebuild_from_list
if not exist "%CONFIG_FILE%" (
    echo [ERROR] No directory configuration found
    echo Use 'manage-directories.bat add ^<directory^>' first
    exit /b 1
)

set "VERBOSE_FLAG="
if /i "%~2"=="--verbose" set "VERBOSE_FLAG=--verbose"

echo.
echo ====================================================================
echo Rebuilding Index from Directory List
echo ====================================================================
echo.

REM Show directories that will be indexed
echo Directories to index:
set "COUNT=0"
for /f "usebackq delims=" %%i in ("%CONFIG_FILE%") do (
    set /a COUNT+=1
    echo   [!COUNT!] %%i
)
echo.

REM Confirm
set /p "CONFIRM=Rebuild index with these directories? (y/N): "
if /i not "!CONFIRM!"=="y" (
    echo Operation cancelled.
    exit /b 0
)

REM Create temporary dirs file for build script
set "TEMP_DIRS=%SCRIPT_DIR%config\temp_rebuild_dirs.txt"
copy "%CONFIG_FILE%" "%TEMP_DIRS%" >nul

echo.
echo Starting full rebuild...
echo.

REM Call rebuild-index with the temporary dirs file
call "%SCRIPT_DIR%rebuild-index.bat" --force --dirs-file "%TEMP_DIRS%" !VERBOSE_FLAG!

REM Cleanup
del "%TEMP_DIRS%"

exit /b %ERRORLEVEL%

:launch_gui
echo.
echo Launching GUI management tool...
echo.

REM Check if tkinter is available
"%SCRIPT_DIR%.venv\Scripts\python.exe" -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] tkinter not available in Python installation
    echo GUI tool requires tkinter (usually included with Python)
    exit /b 1
)

REM Launch Python GUI tool
"%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%src\management\gui_manager.py"

exit /b %ERRORLEVEL%
