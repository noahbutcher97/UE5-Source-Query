"""
UE5 Source Query Tool - GUI Deployment Wizard
Interactive installer with all deployment options, validation, and automatic vector store building.

Usage:
    python gui_deploy.py
"""

import sys
import os
import shutil
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import threading
import queue
import json
import time


class DeploymentWizard:
    """GUI wizard for deploying UE5 Source Query Tool"""

    def __init__(self, root):
        self.root = root
        self.root.title("UE5 Source Query - Deployment Wizard")
        self.root.geometry("850x750")
        self.root.resizable(True, True)

        # Center window on screen
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 850) // 2
        y = (screen_height - 750) // 2
        self.root.geometry(f"850x750+{x}+{y}")

        # Get source directory (where this script is located)
        self.source_dir = Path(__file__).parent.parent

        # Deployment settings
        self.target_dir = tk.StringVar(value=str(Path.home() / "Documents" / "UE5-Source-Query"))
        self.gpu_support = tk.BooleanVar(value=False)
        self.build_index = tk.BooleanVar(value=True)
        self.copy_config = tk.BooleanVar(value=True)
        self.update_existing = tk.BooleanVar(value=False)

        # Queue for thread-safe logging
        self.log_queue = queue.Queue()

        # Progress tracking
        self.total_steps = 8
        self.current_step = 0

        self.create_widgets()
        self.check_prerequisites()
        self.root.after(100, self.process_log_queue)

    def create_widgets(self):
        """Create all UI widgets"""

        # Header
        header = tk.Frame(self.root, bg="#2C3E50", height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        title = tk.Label(
            header,
            text="UE5 Source Query Tool",
            font=("Arial", 18, "bold"),
            bg="#2C3E50",
            fg="white"
        )
        title.pack(pady=10)

        subtitle = tk.Label(
            header,
            text="Deployment Wizard",
            font=("Arial", 12),
            bg="#2C3E50",
            fg="#BDC3C7"
        )
        subtitle.pack()

        # Buttons (Bottom Layout)
        button_frame = tk.Frame(self.root, padx=20, pady=20, bd=1, relief=tk.RAISED)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.install_btn = tk.Button(
            button_frame,
            text="▶ Install Now",
            command=self.start_installation,
            bg="#27AE60",
            fg="white",
            font=("Arial", 12, "bold"),
            padx=30,
            pady=10,
            relief=tk.RAISED,
            bd=3
        )
        self.install_btn.pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(
            button_frame,
            text="Cancel",
            command=self.root.quit,
            font=("Arial", 10),
            padx=20,
            pady=10
        ).pack(side=tk.LEFT)

        # Main content area
        content = tk.Frame(self.root, padx=20, pady=20)
        content.pack(fill=tk.BOTH, expand=True)

        # Target directory section
        dir_frame = tk.LabelFrame(content, text="Deployment Location", padx=10, pady=10)
        dir_frame.pack(fill=tk.X, pady=(0, 10))

        dir_entry_frame = tk.Frame(dir_frame)
        dir_entry_frame.pack(fill=tk.X)

        tk.Label(dir_entry_frame, text="Target:").pack(side=tk.LEFT, padx=(0, 5))
        tk.Entry(dir_entry_frame, textvariable=self.target_dir, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Button(dir_entry_frame, text="Browse...", command=self.browse_directory).pack(side=tk.LEFT)

        # Project Source section (Optional)
        project_frame = tk.LabelFrame(content, text="Project Source (Optional)", padx=10, pady=10)
        project_frame.pack(fill=tk.X, pady=(0, 10))

        project_entry_frame = tk.Frame(project_frame)
        project_entry_frame.pack(fill=tk.X)

        tk.Label(project_entry_frame, text="Project:").pack(side=tk.LEFT, padx=(0, 5))
        self.project_path = tk.StringVar()
        tk.Entry(project_entry_frame, textvariable=self.project_path, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Button(project_entry_frame, text="Browse...", command=self.browse_project).pack(side=tk.LEFT)
        
        tk.Label(project_frame, text="Select your .uproject file to index your game code alongside the engine.", 
                 font=("Arial", 8), fg="#666").pack(anchor=tk.W, pady=(5, 0))

        # Options section
        options_frame = tk.LabelFrame(content, text="Deployment Options", padx=10, pady=10)
        options_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Checkbutton(
            options_frame,
            text="Enable GPU support (CUDA 12.8)",
            variable=self.gpu_support
        ).pack(anchor=tk.W, pady=2)

        tk.Checkbutton(
            options_frame,
            text="Build vector index after installation (recommended)",
            variable=self.build_index
        ).pack(anchor=tk.W, pady=2)

        tk.Checkbutton(
            options_frame,
            text="Copy configuration from source (.env file)",
            variable=self.copy_config
        ).pack(anchor=tk.W, pady=2)

        tk.Checkbutton(
            options_frame,
            text="Update existing installation (preserve data and config)",
            variable=self.update_existing
        ).pack(anchor=tk.W, pady=2)

        # Prerequisites section
        prereq_frame = tk.LabelFrame(content, text="System Check", padx=10, pady=10)
        prereq_frame.pack(fill=tk.X, pady=(0, 10))

        self.prereq_text = scrolledtext.ScrolledText(
            prereq_frame,
            height=6,
            state=tk.DISABLED,
            wrap=tk.WORD,
            font=("Consolas", 9)
        )
        self.prereq_text.pack(fill=tk.BOTH, expand=True)

        # Progress section
        progress_frame = tk.LabelFrame(content, text="Installation Progress", padx=10, pady=10)
        progress_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.log_text = scrolledtext.ScrolledText(
            progress_frame,
            height=12,
            state=tk.DISABLED,
            wrap=tk.WORD,
            font=("Consolas", 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Progress bar with percentage
        progress_bar_frame = tk.Frame(content)
        progress_bar_frame.pack(fill=tk.X, pady=(0, 15))

        self.progress = ttk.Progressbar(progress_bar_frame, mode='determinate', maximum=100)
        self.progress.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=(0, 10))

        self.progress_label = tk.Label(progress_bar_frame, text="0%", font=("Arial", 10, "bold"), width=6)
        self.progress_label.pack(side=tk.LEFT)

    def browse_directory(self):
        """Browse for target directory"""
        directory = filedialog.askdirectory(title="Select Deployment Directory")
        if directory:
            self.target_dir.set(directory)

    def browse_project(self):
        """Browse for .uproject file"""
        file_path = filedialog.askopenfilename(
            title="Select Game Project",
            filetypes=[("Unreal Project", "*.uproject"), ("All Files", "*.*")]
        )
        if file_path:
            self.project_path.set(file_path)

    def log(self, message):
        """Add message to log queue"""
        self.log_queue.put(message)

    def process_log_queue(self):
        """Process log messages from queue"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, message + "\n")
                self.log_text.see(tk.END)
                self.log_text.config(state=tk.DISABLED)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_log_queue)

    def update_progress(self, step, message):
        """Update progress bar"""
        self.current_step = step
        percentage = int((step / self.total_steps) * 100)
        self.progress['value'] = percentage
        self.progress_label.config(text=f"{percentage}%")
        self.log(f"[{step}/{self.total_steps}] {message}")

    def check_prerequisites(self):
        """Check system prerequisites"""
        prereqs = []
        all_checks_passed = True

        # Check Python version
        if sys.version_info >= (3, 8):
            prereqs.append("[OK] Python " + ".".join(map(str, sys.version_info[:3])))
        else:
            prereqs.append(f"[X] Python {sys.version_info.major}.{sys.version_info.minor} (need 3.8+)")
            all_checks_passed = False

        # Check disk space
        try:
            import shutil as sh
            total, used, free = sh.disk_usage(str(Path.home()))
            free_gb = free / (1024 ** 3)
            if free_gb >= 0.5:
                prereqs.append(f"[OK] Disk space: {free_gb:.1f} GB free")
            else:
                prereqs.append(f"[!] Low disk space: {free_gb:.1f} GB (need 500 MB)")
        except Exception:
            pass  # Not critical

        # Check source files
        required_files = {
            "src/core/hybrid_query.py": "Core query engine",
            "src/indexing/build_embeddings.py": "Vector indexer",
            "src/utils/verify_installation.py": "Health checks",
            "requirements.txt": "Dependencies list",
            "tools/health-check.bat": "Health check script"
        }

        missing = []
        for file, description in required_files.items():
            if not (self.source_dir / file).exists():
                missing.append(f"{file} ({description})")

        if missing:
            prereqs.append(f"[X] Missing files:")
            for m in missing[:3]:  # Show first 3
                prereqs.append(f"    - {m}")
            if len(missing) > 3:
                prereqs.append(f"    ... and {len(missing)-3} more")
            all_checks_passed = False
        else:
            prereqs.append("[OK] All required source files present")

        # Check pip
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "--version"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                prereqs.append("[OK] pip available")
            else:
                prereqs.append("[X] pip not available")
                all_checks_passed = False
        except Exception:
            prereqs.append("[X] pip not available")
            all_checks_passed = False

        # Update prerequisites display
        self.prereq_text.config(state=tk.NORMAL)
        self.prereq_text.delete("1.0", tk.END)
        self.prereq_text.insert(tk.END, "\n".join(prereqs))
        self.prereq_text.config(state=tk.DISABLED)

        # Disable install button if critical checks failed
        if not all_checks_passed:
            self.install_btn.config(state=tk.DISABLED, text="✗ Prerequisites Not Met")

    def check_existing_installation(self, target):
        """Check if target already has an installation"""
        if not target.exists():
            return False, None

        # Check for key markers of existing installation
        markers = [
            target / ".venv",
            target / "config" / ".env",
            target / "data" / "vector_store.npz"
        ]

        existing_features = []
        if markers[0].exists():
            existing_features.append("virtual environment")
        if markers[1].exists():
            existing_features.append("configuration")
        if markers[2].exists():
            existing_features.append("vector store")

        if existing_features:
            return True, existing_features
        return False, None

    def start_installation(self):
        """Start installation in background thread"""
        target = Path(self.target_dir.get())

        # Check for existing installation
        is_existing, features = self.check_existing_installation(target)

        if is_existing and not self.update_existing.get():
            response = messagebox.askyesno(
                "Existing Installation Found",
                f"Found existing installation at:\n{target}\n\n"
                f"Existing components:\n" + "\n".join(f"  • {f}" for f in features) + "\n\n"
                f"Do you want to UPDATE this installation?\n"
                f"(Selecting 'No' will abort deployment)",
                icon='warning'
            )

            if not response:
                self.log("Deployment cancelled by user (existing installation)")
                return

            self.update_existing.set(True)
            self.log("Updating existing installation...")

        self.install_btn.config(state=tk.DISABLED)
        self.update_progress(0, "Starting deployment...")

        thread = threading.Thread(target=self.run_installation, daemon=True)
        thread.start()

    def run_installation(self):
        """Execute installation steps"""
        try:
            target = Path(self.target_dir.get())
            is_update = self.update_existing.get()

            self.log("="*60)
            self.log("UE5 Source Query Tool - Deployment" + (" (UPDATE)" if is_update else ""))
            self.log("="*60)
            self.log(f"Target: {target}")
            self.log(f"GPU Support: {self.gpu_support.get()}")
            self.log(f"Build Index: {self.build_index.get()}")
            self.log("")

            # Step 1: Create directory structure
            self.update_progress(1, "Creating directory structure...")
            target.mkdir(parents=True, exist_ok=True)

            subdirs = [
                "src/core", "src/indexing", "src/utils", "src/management",
                "config", "data", "logs", "docs", "tools", "tools/cli", "installer"
            ]
            for subdir in subdirs:
                (target / subdir).mkdir(parents=True, exist_ok=True)
            self.log("  ✓ Directory structure created")

            # Step 2: Copy source files
            self.update_progress(2, "Copying source files...")

            # Copy all Python files from src/ subdirectories
            for src_subdir in ["core", "indexing", "utils", "management"]:
                src_path = self.source_dir / "src" / src_subdir
                if src_path.exists():
                    dst_path = target / "src" / src_subdir
                    dst_path.mkdir(parents=True, exist_ok=True)

                    for file in src_path.glob("*.py"):
                        shutil.copy2(file, dst_path / file.name)
                        self.log(f"    → {src_subdir}/{file.name}")

                    # Copy template and example files for indexing
                    if src_subdir == "indexing":
                        for file in src_path.glob("*.txt"):
                            if file.name != "EngineDirs.txt":  # Don't copy machine-specific
                                shutil.copy2(file, dst_path / file.name)
                                self.log(f"    → {src_subdir}/{file.name}")

            self.log("  ✓ Source files copied")

            # Step 3: Copy installer
            self.update_progress(3, "Copying installer components...")

            installer_src = self.source_dir / "installer"
            installer_dst = target / "installer"
            if installer_src.exists():
                for file in installer_src.glob("*.py"):
                    shutil.copy2(file, installer_dst / file.name)
                    self.log(f"    → installer/{file.name}")

            # Copy install.bat to target root
            install_bat_src = self.source_dir / "install.bat"
            if install_bat_src.exists():
                shutil.copy2(install_bat_src, target / "install.bat")
                self.log("    → install.bat")

            self.log("  ✓ Installer components copied")

            # Step 4: Copy documentation
            self.update_progress(4, "Copying documentation...")
            docs_src = self.source_dir / "docs"
            docs_dst = target / "docs"

            if docs_src.exists():
                for file in docs_src.glob("*.md"):
                    shutil.copy2(file, docs_dst / file.name)

            # Copy main README
            if (self.source_dir / "README.md").exists():
                shutil.copy2(self.source_dir / "README.md", target / "README.md")

            self.log("  ✓ Documentation copied")

            # Step 5: Copy entry point scripts
            self.update_progress(5, "Copying entry point scripts...")

            # Root scripts
            root_scripts = ["ask.bat"]
            for script in root_scripts:
                src_file = self.source_dir / script
                if src_file.exists():
                    shutil.copy2(src_file, target / script)
                    self.log(f"    → {script}")

            # Tools directory scripts
            tools_scripts = [
                "health-check.bat", "rebuild-index.bat", "fix-paths.bat",
                "add-directory.bat", "setup-git-lfs.bat", "manage.bat",
                "manage-directories.bat", "update.bat"
            ]

            for script in tools_scripts:
                src_file = self.source_dir / "tools" / script
                if src_file.exists():
                    shutil.copy2(src_file, target / "tools" / script)
                    self.log(f"    → tools/{script}")

            # CLI tools directory
            cli_dir = self.source_dir / "tools" / "cli"
            if cli_dir.exists():
                for file in cli_dir.glob("*.bat"):
                    shutil.copy2(file, target / "tools" / "cli" / file.name)
                    self.log(f"    → tools/cli/{file.name}")
                # Copy CLI README
                if (cli_dir / "README.md").exists():
                    shutil.copy2(cli_dir / "README.md", target / "tools" / "cli" / "README.md")

            # Copy tools README
            if (self.source_dir / "tools" / "README.md").exists():
                shutil.copy2(self.source_dir / "tools" / "README.md", target / "tools" / "README.md")

            # Copy requirements
            shutil.copy2(self.source_dir / "requirements.txt", target / "requirements.txt")
            if (self.source_dir / "requirements-gpu.txt").exists():
                shutil.copy2(self.source_dir / "requirements-gpu.txt", target / "requirements-gpu.txt")

            # Copy .gitignore
            if (self.source_dir / ".gitignore").exists():
                shutil.copy2(self.source_dir / ".gitignore", target / ".gitignore")

            self.log("  ✓ Scripts copied")

            # Step 6: Copy/create configuration
            if self.copy_config.get() and not is_update:
                self.log("[6/8] Copying configuration...")
                src_config = self.source_dir / "config" / ".env"
                if src_config.exists():
                    shutil.copy2(src_config, target / "config" / ".env")
                    self.log("  ✓ Configuration copied")
                else:
                    self.log("  ! Source .env not found, will need to run configure.bat")
            elif is_update:
                self.log("[6/8] Preserving existing configuration...")
                self.log("  ✓ Configuration preserved")
            else:
                self.log("[6/8] Skipping configuration copy")

            # Step 6.5: Configure Project Source (New)
            project_path_str = self.project_path.get().strip()
            if project_path_str:
                self.log("  Configuring Project Source...")
                try:
                    uproject = Path(project_path_str)
                    if uproject.exists():
                        project_root = uproject.parent
                        source_dir = project_root / "Source"
                        if source_dir.exists() and source_dir.is_dir():
                            project_dirs_file = target / "src" / "indexing" / "ProjectDirs.txt"
                            project_dirs_file.parent.mkdir(parents=True, exist_ok=True)
                            with open(project_dirs_file, 'w') as f:
                                f.write("# Auto-generated Project Directories\n")
                                f.write(f"{source_dir}\n")
                            self.log(f"  ✓ Added project source: {source_dir}")
                        else:
                            self.log(f"  ! Warning: 'Source' folder not found in {project_root}")
                    else:
                        self.log(f"  ! Warning: .uproject file not found at {uproject}")
                except Exception as e:
                    self.log(f"  ! Error configuring project source: {e}")

            # Step 7: Create virtual environment and install packages
            venv_path = target / ".venv"

            if not venv_path.exists() or not is_update:
                self.update_progress(6, "Creating Python virtual environment...")

                result = subprocess.run(
                    [sys.executable, "-m", "venv", str(venv_path)],
                    capture_output=True,
                    text=True
                )

                if result.returncode != 0:
                    raise Exception(f"Failed to create venv: {result.stderr}")

                self.log("  ✓ Virtual environment created")
            else:
                self.update_progress(6, "Using existing virtual environment...")
                self.log("  ✓ Existing virtual environment preserved")

            # Install packages
            self.log("  Installing Python packages (this may take a few minutes)...")
            pip_exe = venv_path / "Scripts" / "pip.exe"

            requirements_file = "requirements-gpu.txt" if self.gpu_support.get() else "requirements.txt"

            result = subprocess.run(
                [str(pip_exe), "install", "-r", str(target / requirements_file), "--quiet"],
                capture_output=True,
                text=True,
                cwd=str(target)
            )

            if result.returncode != 0:
                self.log(f"  ! Warning: Package installation had errors")
                self.log(f"    {result.stderr[:300]}")
            else:
                self.log("  ✓ Packages installed")

            # Step 8: Build index if requested
            if self.build_index.get():
                self.update_progress(7, "Building vector index...")
                self.log("  This may take 5-15 minutes depending on your system...")

                # Check if configuration exists
                config_file = target / "config" / ".env"
                engine_dirs_file = target / "src" / "indexing" / "EngineDirs.txt"

                if not config_file.exists():
                    self.log("  ! Configuration not found, skipping index build")
                    self.log("  ! Run configure.bat then tools\\rebuild-index.bat manually")
                elif not engine_dirs_file.exists():
                    self.log("  ! EngineDirs.txt not found, skipping index build")
                    self.log("  ! Run tools\\fix-paths.bat then tools\\rebuild-index.bat manually")
                else:
                    # Run index building
                    python_exe = venv_path / "Scripts" / "python.exe"
                    build_script = target / "src" / "indexing" / "build_embeddings.py"

                    self.log("  Starting index build...")

                    process = subprocess.Popen(
                        [str(python_exe), str(build_script)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        cwd=str(target)
                    )

                    # Stream output
                    for line in process.stdout:
                        line = line.rstrip()
                        if line:
                            self.log(f"    {line}")

                    process.wait()

                    if process.returncode == 0:
                        self.log("  ✓ Vector index built successfully")
                    else:
                        self.log("  ! Index build failed, run tools\\rebuild-index.bat manually")
            else:
                self.update_progress(7, "Skipping vector index build")

            # Step 9: Final verification
            self.update_progress(8, "Verifying installation...")

            verification_checks = [
                (target / "ask.bat", "Query script"),
                (target / "tools" / "health-check.bat", "Health check tool"),
                (venv_path / "Scripts" / "python.exe", "Python interpreter"),
                (target / "src" / "core" / "hybrid_query.py", "Core engine")
            ]

            all_verified = True
            for check_file, description in verification_checks:
                if check_file.exists():
                    self.log(f"  ✓ {description}")
                else:
                    self.log(f"  ✗ {description} MISSING")
                    all_verified = False

            if not all_verified:
                raise Exception("Installation verification failed - some files missing")

            # Success!
            self.log("")
            self.log("="*60)
            self.log("Installation Complete!")
            self.log("="*60)
            self.log("")
            self.log("Next steps:")
            self.log(f"  1. cd \"{target}\"")

            if not self.copy_config.get() or not (target / "config" / ".env").exists():
                self.log("  2. configure.bat  (set up API key and UE5 paths)")
            elif not (target / "src" / "indexing" / "EngineDirs.txt").exists():
                self.log("  2. tools\\fix-paths.bat  (configure UE5 paths for this machine)")
            else:
                self.log("  2. Configuration already set up ✓")

            self.log("  3. tools\\health-check.bat  (verify installation)")

            if not self.build_index.get() or not (target / "data" / "vector_store.npz").exists():
                self.log("  4. tools\\rebuild-index.bat  (build vector index)")
                self.log("  5. ask.bat \"What is FVector\"  (test query)")
            else:
                self.log("  4. ask.bat \"What is FVector\"  (test query)")

            self.log("")
            self.log("Installation directory: " + str(target))

            # Show success dialog
            self.root.after(0, lambda: messagebox.showinfo(
                "Installation Complete",
                f"UE5 Source Query Tool successfully {'updated' if is_update else 'installed'} at:\n{target}\n\n"
                f"See log for next steps."
            ))

        except Exception as e:
            self.log("")
            self.log(f"ERROR: Installation failed: {e}")
            self.log("")
            import traceback
            self.log(traceback.format_exc())

            self.root.after(0, lambda: messagebox.showerror(
                "Installation Failed",
                f"An error occurred during installation:\n\n{str(e)}\n\n"
                f"See log for details."
            ))

        finally:
            self.root.after(0, lambda: self.install_btn.config(state=tk.NORMAL, text="▶ Install Now"))
            self.root.after(0, lambda: self.progress.config(value=0))
            self.root.after(0, lambda: self.progress_label.config(text="0%"))


def main():
    """Main entry point"""
    root = tk.Tk()
    app = DeploymentWizard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
