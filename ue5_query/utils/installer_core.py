import sys
import os
import shutil
import subprocess
import json
import threading
from pathlib import Path
from typing import Optional, Callable

from ue5_query.utils.source_manager import SourceManager
from ue5_query.utils.config_manager import ConfigManager

class OperationCancelled(Exception):
    pass

class InstallerCore:
    """
    Headless installer logic for deploying and initializing the tool.
    Decoupled from tkinter to allow automation.
    """
    def __init__(self, source_dir: Path, logger: Optional[Callable[[str], None]] = None):
        self.source_dir = source_dir
        self.log_func = logger if logger else print
        self.current_process = None
        self._cancelled = False

    def log(self, msg):
        self.log_func(msg)

    def cancel(self):
        """Cancel the current operation."""
        self._cancelled = True
        self.log("Cancellation requested...")
        if self.current_process:
            try:
                import psutil
                parent = psutil.Process(self.current_process.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
            except Exception:
                try:
                    self.current_process.terminate()
                except:
                    pass

    def _check_cancelled(self):
        if self._cancelled:
            raise OperationCancelled("Operation cancelled by user.")

    def _run_command(self, cmd, cwd=None, output_filter=None):
        self._check_cancelled()
        try:
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(cwd) if cwd else None,
                bufsize=1,
                universal_newlines=True
            )
            
            for line in self.current_process.stdout:
                if self._cancelled:
                    self.current_process.terminate()
                    break
                    
                line = line.strip()
                if not line: continue
                
                if output_filter:
                    filtered = output_filter(line)
                    if filtered:
                        self.log(filtered)
                else:
                    self.log(line)
                
            self.current_process.wait()
            if self._cancelled:
                raise OperationCancelled("Operation cancelled by user.")
                
            if self.current_process.returncode != 0:
                raise subprocess.CalledProcessError(self.current_process.returncode, cmd)
        except OperationCancelled:
            raise
        except Exception as e:
            if not self._cancelled:
                self.log(f"Command failed: {e}")
            raise
        finally:
            self.current_process = None

    def _pip_filter(self, line):
        """Reduce pip output noise"""
        # Keep high-level status updates
        if any(line.startswith(x) for x in ["Collecting", "Installing", "Successfully", "Removing", "Saved"]):
            return f"  > {line}"
        # Show errors/warnings
        if "error" in line.lower() or "warning" in line.lower():
            return f"  ! {line}"
        return None

    def install(self, 
                target_path: Path, 
                config_settings: dict, 
                engine_path: str,
                project_dirs: list[str] = None,
                clean_install: bool = False,
                create_venv: bool = True,
                setup_gpu: bool = False,
                on_progress: Optional[Callable[[str, float], None]] = None):
        """
        Perform full installation/update at target_path.
        """
        self._check_cancelled()
        
        def update_progress(msg, pct):
            self._check_cancelled()
            if on_progress:
                on_progress(msg, pct)
            self.log(f"[{int(pct)}%] {msg}")

        target = Path(target_path)
        update_progress(f"Installing to: {target}", 5)
        
        # 1. Copy Files
        self._check_cancelled()
        update_progress("Syncing files...", 10)
        target.mkdir(parents=True, exist_ok=True)
        
        # Load exclusions
        exclude_patterns = [".venv", ".git", "__pycache__", "tests"]
        try:
            rules_path = self.source_dir / "config" / "deployment_rules.json"
            if rules_path.exists():
                with open(rules_path, 'r') as f:
                    rules = json.load(f)
                    exclude_patterns = rules.get("default_excludes", []) + rules.get("deployment_excludes", [])
        except:
            pass

        # Manual copy of critical folders (simplified sync)
        items_to_copy = ["ue5_query", "config", "tools", "docs", "tests", "installer", "ask.bat", "launcher.bat", "bootstrap.py", "requirements.txt", ".indexignore", "pyproject.toml"]
        
        for item in items_to_copy:
            src = self.source_dir / item
            dst = target / item
            if not src.exists(): continue
            
            if src.is_dir():
                # We use a naive copy here for bootstrapping; robust sync is handled by tools/update.py later
                if dst.exists(): shutil.rmtree(dst)
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
            else:
                shutil.copy2(src, dst)

        # 2. Write .env Config
        update_progress("Writing configuration...", 20)
        env_path = target / "config" / ".env"
        env_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(env_path, 'w') as f:
            f.write("# UE5 Source Query Configuration\n")
            f.write("# Generated by Headless Installer\n\n")
            for k, v in config_settings.items():
                f.write(f"{k}={v}\n")

        # 3. Configure Engine Dirs
        if engine_path:
            update_progress(f"Configuring Engine...", 30)
            # Load template
            template = self.source_dir / "ue5_query" / "indexing" / "EngineDirs.template.txt"
            if template.exists():
                with open(template, 'r') as f:
                    engine_dirs = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                
                # Write to target
                target_source_mgr = SourceManager(target)
                # We manually write the file to bypass specific logic in add_engine_dir which expects running app
                out_file = target / "ue5_query" / "indexing" / "EngineDirs.txt"
                out_file.parent.mkdir(parents=True, exist_ok=True)
                with open(out_file, 'w') as f:
                    f.write(f"# Auto-generated for Engine Root: {engine_path}\n")
                    for d in engine_dirs:
                        f.write(f"{d}\n")

        # 4. Configure Project Dirs
        if project_dirs:
            update_progress("Configuring project paths...", 40)
            out_file = target / "ue5_query" / "indexing" / "ProjectDirs.txt"
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, 'w') as f:
                f.write("# Auto-generated Project Directories\n")
                for p in project_dirs:
                    f.write(f"{p}\n")

        # 5. Create Deployment Config
        update_progress("Finalizing deployment config...", 50)
        self._create_deployment_config(target)

        # 6. Python Environment
        if create_venv:
            update_progress("Setting up Python environment...", 60)
            venv_path = target / ".venv"
            pip = venv_path / "Scripts" / "pip.exe"
            
            if not (venv_path.exists() and pip.exists()):
                self.log("Creating venv...")
                subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
            
            update_progress("Installing dependencies (this may take a minute)...", 70)
            self._run_command([str(pip), "install", "-r", str(target / "requirements.txt")], output_filter=self._pip_filter)
            self._run_command([str(pip), "install", "-e", str(target)], output_filter=self._pip_filter)
            
            if setup_gpu:
                try:
                    update_progress("Checking GPU compatibility...", 80)
                    # Lazy import to avoid dependencies at top level
                    from ue5_query.utils.gpu_helper import detect_nvidia_gpu
                    from ue5_query.utils.cuda_installer import create_gpu_requirements_file
                    
                    gpu = detect_nvidia_gpu()
                    if gpu:
                        self.log(f"Detected {gpu.name}. Configuring CUDA {gpu.cuda_version_required}...")
                        req_file = target / "requirements-gpu.txt"
                        create_gpu_requirements_file(req_file, gpu.cuda_version_required)
                        
                        update_progress("Installing GPU packages...", 85)
                        self._run_command([str(pip), "install", "-r", str(req_file)], output_filter=self._pip_filter)
                        self.log("GPU packages installed.")
                    else:
                        self.log("No NVIDIA GPU detected. Skipping GPU setup.")
                except Exception as e:
                    self.log(f"Warning: GPU setup failed: {e}")

        update_progress("Installation complete.", 100)

    def _create_deployment_config(self, target):
        """Create the deployment registry file so it can be updated later."""
        import datetime
        try:
            repo_url = subprocess.check_output(["git", "config", "--get", "remote.origin.url"], cwd=self.source_dir).decode().strip()
        except:
            repo_url = ""

        config = {
            "version": "2.0.0",
            "deployment_info": {
                "deployed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "deployed_from": str(self.source_dir),
                "deployment_method": "headless",
                "deployed_to": str(target),
                "status": "Installing" # Default initial status
            },
            "update_sources": {
                "local_dev_repo": str(self.source_dir),
                "remote_repo": repo_url
            }
        }
        
        with open(target / ".ue5query_deploy.json", 'w') as f:
            json.dump(config, f, indent=2)

    def update_config_status(self, target: Path, status: str):
        """Update the status field in deployment config"""
        config_file = target / ".ue5query_deploy.json"
        if not config_file.exists(): return
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            config["deployment_info"]["status"] = status
            
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except:
            pass

    def launch_indexer_in_terminal(self, target_path: Path):
        """
        Launch the indexer in a separate visible terminal window.
        This provides immediate feedback without blocking the dashboard.
        """
        rebuild_script = target_path / "tools" / "rebuild-index.bat"
        
        # Windows command to spawn new terminal
        # /k keeps window open after finish so user can see result
        cmd = f'start "UE5 Indexing - {target_path.name}" cmd /k "{rebuild_script}"'
        subprocess.Popen(cmd, shell=True, cwd=str(target_path))