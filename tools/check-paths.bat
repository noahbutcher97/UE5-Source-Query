@echo off
REM Check if source paths in EngineDirs.txt and ProjectDirs.txt exist

echo.
echo ============================================
echo UE5 Source Query - Path Validation Tool
echo ============================================
echo.

cd /d "%~dp0\.."

REM Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo Please run setup.bat first.
    pause
    exit /b 1
)

echo Running path validation...
echo.

REM Run the Python validation script
.venv\Scripts\python.exe -c "
import sys
from pathlib import Path

print('=== Engine Directories (EngineDirs.txt) ===')
engine_file = Path('src/indexing/EngineDirs.txt')
if engine_file.exists():
    with open(engine_file) as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]

    if not lines:
        print('[WARNING] EngineDirs.txt is empty!')
    else:
        valid = 0
        invalid = 0
        for line in lines:
            if Path(line).exists():
                print(f'[OK] {line}')
                valid += 1
            else:
                print(f'[MISSING] {line}')
                invalid += 1

        print(f'\nTotal: {len(lines)} paths, Valid: {valid}, Invalid: {invalid}')

        if invalid > 0:
            print('\n[ERROR] Some engine paths do not exist!')
            print('Solution: Check Engine Path in Configuration tab.')
else:
    print('[ERROR] EngineDirs.txt not found!')
    print('Run setup.bat to configure engine paths.')

print('\n=== Project Directories (ProjectDirs.txt) ===')
project_file = Path('src/indexing/ProjectDirs.txt')
if project_file.exists():
    with open(project_file) as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]

    if not lines:
        print('[INFO] No project directories configured (optional)')
    else:
        valid = 0
        invalid = 0
        for line in lines:
            if Path(line).exists():
                print(f'[OK] {line}')
                valid += 1
            else:
                print(f'[MISSING] {line}')
                invalid += 1

        print(f'\nTotal: {len(lines)} paths, Valid: {valid}, Invalid: {invalid}')

        if invalid > 0:
            print('\n[ERROR] Some project paths do not exist!')
else:
    print('[INFO] ProjectDirs.txt not found (optional)')

print('\n=== Configuration (.env) ===')
env_file = Path('config/.env')
if env_file.exists():
    print('[OK] Configuration file exists')
    with open(env_file) as f:
        for line in f:
            if 'UE_ENGINE_ROOT' in line:
                path = line.split('=', 1)[1].strip()
                if Path(path).exists():
                    print(f'[OK] Engine Root: {path}')
                else:
                    print(f'[ERROR] Engine Root does not exist: {path}')
else:
    print('[ERROR] Configuration file not found!')

print('\n============================================')
"

echo.
pause
