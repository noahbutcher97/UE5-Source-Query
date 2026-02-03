import sys
import os
import subprocess
from pathlib import Path

def main():
    root = Path(__file__).parent.resolve()
    venv_python = root / ".venv" / "Scripts" / "python.exe"
    installer_script = root / "installer" / "gui_deploy.py"
    
    # 1. Environment Health Check
    needs_install = False
    if not venv_python.exists():
        print("[BOOTSTRAP] Virtual environment not found.")
        needs_install = True
    else:
        # Verify venv works (handles moved folders where absolute paths break)
        try:
            subprocess.run([str(venv_python), "--version"], capture_output=True, check=True)
        except Exception:
            print("[BOOTSTRAP] Virtual environment is broken (likely moved). Recreating...")
            import shutil
            try:
                shutil.rmtree(root / ".venv")
            except:
                pass
            needs_install = True
    
    # 2. Auto-Install / Repair
    if needs_install:
        print("=" * 60)
        print(" UE5 Source Query - First Time Setup")
        print("=" * 60)
        print("\n[BOOTSTRAP] Virtual environment missing. Starting Installer GUI...")
        
        if not installer_script.exists():
            print(f"\n[ERROR] Installer script not found at: {installer_script}")
            print("Please ensure the 'installer' folder exists in the project root.")
            input("\nPress Enter to exit...")
            sys.exit(1)
            
        # Run installer using system python
        try:
            # We use subprocess.run to wait for completion and get return code
            ret = subprocess.call([sys.executable, str(installer_script)])
            
            # 0 = Success, others usually mean cancelled/error
            if ret != 0:
                print("\n[BOOTSTRAP] Setup was closed, cancelled, or failed.")
                # We exit here so we don't try to launch the (missing) dashboard
                sys.exit(ret)
                
            # Re-verify environment
            if not venv_python.exists():
                print("\n[ERROR] Setup finished but .venv was not created.")
                print("Please try running the installer again or run Setup.bat manually.")
                input("\nPress Enter to exit...")
                sys.exit(1)
            
            print("\n[BOOTSTRAP] Setup successful!")
                
        except Exception as e:
            print(f"\n[ERROR] Failed to launch installer: {e}")
            input("\nPress Enter to exit...")
            sys.exit(1)

    # 3. Dependency Check (Self-Healing)
    try:
        # Check for psutil (critical for maintenance ops)
        subprocess.run([str(venv_python), "-c", "import psutil"], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        print("[BOOTSTRAP] Missing dependencies detected. Updating environment...")
        try:
            # Prefer GPU requirements if available
            req_file = root / "requirements-gpu.txt"
            if not req_file.exists():
                req_file = root / "requirements.txt"
            
            if req_file.exists():
                print(f"[BOOTSTRAP] Installing from {req_file.name}...")
                subprocess.run([str(venv_python), "-m", "pip", "install", "-r", str(req_file)], check=True)
                print("[BOOTSTRAP] Dependencies updated.")
        except Exception as e:
            print(f"[WARN] Failed to update dependencies: {e}")

    # 4. Launch Application
    print("[BOOTSTRAP] Initializing Dashboard...")
    
    # Construct command: venv_python -m module [args]
    # Use -m to ensure imports work correctly relative to package
    cmd = [str(venv_python), "-m", "ue5_query.management.gui_dashboard"] + sys.argv[1:]
    
    try:
        # Replace current process with dashboard if possible, or subprocess
        # On Windows, subprocess.call is cleaner for GUI apps to keep console attached or detached as needed
        sys.exit(subprocess.call(cmd))
    except Exception as e:
        print(f"[ERROR] Failed to launch dashboard: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
