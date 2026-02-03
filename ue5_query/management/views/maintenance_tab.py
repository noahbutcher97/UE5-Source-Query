import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sys
import time
import threading
from pathlib import Path

# Try to import Theme, handle missing imports gracefully if run standalone
try:
    from ue5_query.utils.gui_theme import Theme
    from ue5_query.utils.gpu_helper import detect_nvidia_gpu, get_gpu_summary
except ImportError:
    # If run standalone or during dev
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
        from ue5_query.utils.gui_theme import Theme
        from ue5_query.utils.gpu_helper import detect_nvidia_gpu, get_gpu_summary
    except ImportError:
        Theme = None

class MaintenanceTab:
    """
    Handles the Maintenance tab logic and layout.
    """
    def __init__(self, parent_frame, dashboard):
        """
        Args:
            parent_frame: The ttk.Frame to build the tab into
            dashboard: Reference to the main UnifiedDashboard instance (controller)
        """
        self.frame = parent_frame
        self.dashboard = dashboard
        self.script_dir = dashboard.script_dir
        self.maint_service = dashboard.maint_service
        self.cancelled = False
        
        self.build_ui()
        self.check_status()

    def build_ui(self):
        """Build the UI components"""
        frame = ttk.Frame(self.frame, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Status Section
        status_frame = ttk.LabelFrame(frame, text=" System Status ", padding=15)
        status_frame.pack(fill=tk.X, pady=(0, 20))

        self.lbl_index_status = ttk.Label(status_frame, text="Index Status: Unknown", font=Theme.FONT_BOLD)
        self.lbl_index_status.pack(side=tk.LEFT)

        ttk.Button(status_frame, text="Refresh Status", command=self.check_status).pack(side=tk.RIGHT)

        # Progress Section
        progress_frame = ttk.LabelFrame(frame, text=" Operation Progress ", padding=15)
        progress_frame.pack(fill=tk.X, pady=(0, 20))

        # Progress bar
        self.maint_progress = ttk.Progressbar(progress_frame, mode='determinate', maximum=100)
        self.maint_progress.pack(fill=tk.X, pady=(0, 10))

        # Progress label showing current step
        self.maint_progress_label = ttk.Label(progress_frame, text="Ready", font=Theme.FONT_NORMAL)
        self.maint_progress_label.pack(anchor=tk.W)

        # Time estimate label
        self.maint_time_label = ttk.Label(progress_frame, text="", font=Theme.FONT_SMALL, foreground="gray")
        self.maint_time_label.pack(anchor=tk.W)

        # Actions Section
        action_frame = ttk.LabelFrame(frame, text=" Maintenance Actions ", padding=15)
        action_frame.pack(fill=tk.X, pady=(0, 20))

        # Grid layout for better organization
        action_grid = tk.Frame(action_frame, bg=Theme.BG_LIGHT)
        action_grid.pack(fill=tk.X)

        # Row 1: System Updates (Phase 6)
        tk.Label(
            action_grid,
            text="System Updates:",
            font=("Arial", 10, "bold"),
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_DARK
        ).grid(row=0, column=0, sticky=tk.W, padx=(0, 20), pady=5)

        tk.Label(
            action_grid,
            text="Use System Status tab for updates",
            font=("Arial", 9),
            bg=Theme.BG_LIGHT,
            fg="#7F8C8D"
        ).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        # Row 2: Verification
        tk.Label(
            action_grid,
            text="Verification:",
            font=("Arial", 10, "bold"),
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_DARK
        ).grid(row=1, column=0, sticky=tk.W, padx=(0, 20), pady=5)

        btn_verify = tk.Button(
            action_grid,
            text="✓ Verify Installation",
            command=self.verify_installation,
            bg=Theme.SUCCESS,
            fg="white",
            padx=15,
            pady=8,
            relief=tk.FLAT,
            cursor="hand2"
        )
        btn_verify.grid(row=1, column=1, padx=5, pady=5)

        # Row 3: GPU/CUDA Setup (NEW)
        tk.Label(
            action_grid,
            text="GPU Acceleration:",
            font=("Arial", 10, "bold"),
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_DARK
        ).grid(row=2, column=0, sticky=tk.W, padx=(0, 20), pady=5)

        # GPU status frame
        gpu_status_frame = tk.Frame(action_grid, bg=Theme.BG_LIGHT)
        gpu_status_frame.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)

        self.btn_cuda_setup = tk.Button(
            gpu_status_frame,
            text="⚙ Setup CUDA",
            command=self.setup_cuda,
            bg="#8E44AD",  # Purple for GPU
            fg="white",
            padx=10,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2",
            state=tk.DISABLED  # Initially disabled until we check status
        )
        self.btn_cuda_setup.pack(side=tk.LEFT, padx=(10, 0))

        self.btn_gpu_diag = tk.Button(
            gpu_status_frame,
            text="🔬 Diagnostics",
            command=self.run_gpu_diagnostics,
            bg=Theme.SECONDARY,
            fg="white",
            padx=10,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2"
        )
        self.btn_gpu_diag.pack(side=tk.LEFT, padx=(5, 0))

        # Check GPU status after UI is built
        self.dashboard.root.after(100, self.check_gpu_status)

        # Close button at bottom
        close_frame = tk.Frame(action_frame, bg=Theme.BG_LIGHT)
        close_frame.pack(fill=tk.X, pady=(15, 0))

        self.btn_cancel = tk.Button(
            close_frame,
            text="Close",
            command=self.cancel_or_close,
            bg="#7F8C8D",
            fg="white",
            padx=15,
            pady=8,
            relief=tk.FLAT,
            cursor="hand2"
        )
        self.btn_cancel.pack(side=tk.RIGHT)

        # Log Section
        log_frame = ttk.LabelFrame(frame, text=" Operation Log ", padding=15)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.maint_log = scrolledtext.ScrolledText(log_frame, font=Theme.FONT_MONO, height=10)
        self.maint_log.pack(fill=tk.BOTH, expand=True)

    def run_gpu_diagnostics(self):
        """Run the standalone GPU diagnostic script"""
        self.log_maint("Running GPU Diagnostics...", clear=True)
        self.btn_gpu_diag.config(state=tk.DISABLED)
        
        def _run():
            try:
                import subprocess, json, re
                script = self.script_dir / "ue5_query" / "utils" / "gpu_test.py"
                if not script.exists():
                     # Fallback for dev environment
                     script = self.script_dir.parent / "ue5_query" / "utils" / "gpu_test.py"
                
                python_exe = sys.executable
                
                process = subprocess.run(
                    [python_exe, str(script)],
                    capture_output=True,
                    text=True
                )
                
                output = process.stdout.strip()
                if not output:
                    raise ValueError(f"No output from diagnostic script. Stderr: {process.stderr}")
                    
                try:
                    data = json.loads(output)
                except:
                    match = re.search(r'\{.*\}', output, re.DOTALL)
                    if match:
                        data = json.loads(match.group(0))
                    else:
                        raise ValueError(f"Invalid JSON output: {output[:100]}...")

                # Format report
                report = []
                report.append(f"--- GPU Diagnostic Report ---")
                report.append(f"Status: {data.get('status', 'unknown').upper()}")
                report.append(f"System CUDA: {data.get('system_cuda', 'Not Checked')}")
                report.append(f"Device: {data.get('device_name', 'Unknown')}")
                report.append(f"VRAM: {data.get('vram_gb', 0)} GB")
                report.append(f"Compute Capability: {data.get('capability', 'Unknown')}")
                report.append(f"PyTorch Version: {data.get('torch_version', 'Unknown')}")
                report.append(f"JIT Compilation: {data.get('jit_status', 'unknown').upper()}")
                report.append(f"Test Duration: {data.get('test_duration', 0):.4f}s")
                
                if data.get('error'):
                    report.append(f"\n[ERROR] {data['error']}")
                    if data.get('details'):
                        report.append(f"Details:\n{data['details']}")
                
                if data.get('recommendation'):
                    report.append(f"\nRecommendation:\n{data['recommendation']}")
                
                final_report = "\n".join(report)
                
                self.dashboard.root.after(0, lambda: self.log_maint(final_report, append=True))
                self.dashboard.root.after(0, lambda: messagebox.showinfo("GPU Diagnostics", final_report))
                
            except Exception as e:
                self.dashboard.root.after(0, lambda: self.log_maint(f"\nDiagnostics Failed: {e}", append=True))
            finally:
                self.dashboard.root.after(0, lambda: self.btn_gpu_diag.config(state=tk.NORMAL))

        threading.Thread(target=_run, daemon=True).start()

    def log_maint(self, msg, clear=False, append=False):
        """Helper to log to maintenance log"""
        self.maint_log.config(state=tk.NORMAL)
        if clear:
            self.maint_log.delete(1.0, tk.END)
        
        if append:
            self.maint_log.insert(tk.END, msg)
        else:
            self.maint_log.insert(tk.END, msg + "\n")
            
        self.maint_log.see(tk.END)
        self.maint_log.config(state=tk.DISABLED)

    def cancel_or_close(self):
        if self.maint_service.current_process:
            if messagebox.askyesno("Cancel", "Cancel current operation?"):
                self.cancelled = True
                if self.maint_service.cancel_current_process():
                    self.log_maint("[CANCELLED] Operation cancelled.", append=True)
                    self.btn_rebuild.config(state=tk.NORMAL)
                    self.btn_cancel.config(text="Close")
        else:
            self.dashboard.root.destroy()

    def check_status(self):
        # Simple check for vector store file
        store_path = self.script_dir / "data" / "vector_store.npz"
        if store_path.exists():
            try:
                size_mb = store_path.stat().st_size / (1024*1024)
                self.lbl_index_status.config(text=f"Index Status: Active ({size_mb:.1f} MB)", foreground=Theme.SUCCESS)
            except:
                self.lbl_index_status.config(text="Index Status: Error Checking File", foreground=Theme.ERROR)
        else:
            self.lbl_index_status.config(text="Index Status: Not Found", foreground=Theme.ERROR)

    def verify_installation(self):
        """Run comprehensive installation verification using MaintenanceService"""
        self.log_maint("Running installation verification...", clear=True)
        verify_script = self.script_dir / "src" / "utils" / "verify_installation.py"
        # Adjust path if in installed package structure
        if not verify_script.exists():
             # Try alternate location
             verify_script = self.script_dir / "ue5_query" / "utils" / "verify_installation.py"

        if not verify_script.exists():
            self.log_maint("[ERROR] Verification script not found")
            return

        def on_complete(success, message):
            if success:
                self.dashboard.root.after(0, lambda: self.log_maint(f"\n[SUCCESS] {message}", append=True))
            else:
                self.dashboard.root.after(0, lambda: self.log_maint(f"\n[WARNING] {message}", append=True))

        self.maint_service.run_task(
            task_name="Installation Verification",
            command=[sys.executable, str(verify_script)],
            callback=on_complete,
            log_callback=lambda line: self.dashboard.root.after(0, lambda: self.log_maint(line.rstrip(), append=True))
        )

    def check_gpu_status(self):
        """Check GPU status and update the maintenance tab UI."""
        def _check():
            try:
                gpu_summary = get_gpu_summary()

                # Safety check: Ensure window still exists
                try:
                    if not self.dashboard.root.winfo_exists():
                        return
                except:
                    return

                if gpu_summary.get('has_nvidia_gpu'):
                    gpu_name = gpu_summary.get('gpu_name', 'Unknown GPU')
                    cuda_installed = gpu_summary.get('cuda_installed')
                    cuda_compatible = gpu_summary.get('cuda_compatible', False)
                    
                    if cuda_installed and cuda_compatible:
                        status = f"✓ {gpu_name} with CUDA {cuda_installed}"
                        color = Theme.SUCCESS
                        enable_setup = True # Allow re-installation/repair
                    elif cuda_installed and not cuda_compatible:
                        status = f"⚠ {gpu_name} - CUDA {cuda_installed} (outdated)"
                        color = "#FFC107"
                        enable_setup = True
                    else:
                        cuda_required = gpu_summary.get('cuda_required', 'Unknown')
                        status = f"⚠ {gpu_name} - CUDA {cuda_required}+ required"
                        color = "#FFC107"
                        enable_setup = True

                    def update_ui():
                        try:
                            self.gpu_status_label.config(text=status, fg=color)
                            self.btn_cuda_setup.config(state=tk.NORMAL if enable_setup else tk.DISABLED)
                        except AttributeError:
                            pass # Widget might not exist yet or destroyed

                    # Store GPU info on dashboard for shared access if needed
                    self.dashboard.gpu_info = gpu_summary
                else:
                    def update_ui():
                        try:
                            self.gpu_status_label.config(text="No NVIDIA GPU detected (CPU mode)", fg="#7F8C8D")
                            self.btn_cuda_setup.config(state=tk.DISABLED)
                        except AttributeError:
                            pass
                    self.dashboard.gpu_info = None

                self.dashboard.root.after(0, update_ui)

            except RuntimeError:
                # Ignore "main thread is not in main loop" if app is closing
                pass
            except Exception as e:
                try:
                    self.dashboard.root.after(0, lambda: self.gpu_status_label.config(
                        text=f"Error checking GPU: {e}", fg=Theme.ERROR))
                    self.dashboard.root.after(0, lambda: self.btn_cuda_setup.config(state=tk.DISABLED))
                except:
                    pass

        threading.Thread(target=_check, daemon=True).start()

    def setup_cuda(self):
        """Launch CUDA setup wizard (Phase 6)"""
        # Logic moved from dashboard
        if not hasattr(self.dashboard, 'gpu_info') or not self.dashboard.gpu_info:
            messagebox.showerror("Error", "GPU information not available. Please refresh GPU status.")
            return

        gpu_info = self.dashboard.gpu_info
        cuda_required = gpu_info.get('cuda_required', 'Unknown')
        gpu_name = gpu_info.get('gpu_name', 'Unknown GPU')
        download_url = gpu_info.get('download_url', None)

        if not download_url:
            messagebox.showerror("Error", "CUDA download URL not available for your GPU.")
            return

        # Determine dialog state based on current status
        cuda_installed = gpu_info.get('cuda_installed')
        cuda_compatible = gpu_info.get('cuda_compatible', False)
        
        dialog_title = "CUDA Setup"
        base_msg = f"Target: CUDA Toolkit {cuda_required} for {gpu_name}\n\n"
        warning_msg = "Note: This requires administrator privileges and takes 15-30 minutes."
        
        if cuda_compatible:
            dialog_title = "Reinstall CUDA?"
            user_msg = (f"✅ Good News: You already have a compatible version installed ({cuda_installed}).\n\n"
                        f"You do NOT need to install this unless you are fixing a broken installation.\n\n"
                        f"Do you want to FORCE a re-installation?")
            icon = 'question'
        elif cuda_installed:
            dialog_title = "Upgrade CUDA"
            user_msg = (f"⚠️ Update Required: Your current version ({cuda_installed}) is older than the required {cuda_required}.\n\n"
                        f"Would you like to upgrade now?")
            icon = 'warning'
        else:
            dialog_title = "Install CUDA"
            user_msg = (f"CUDA Toolkit is missing. Installing it is highly recommended for GPU acceleration.\n\n"
                        f"Ready to install?")
            icon = 'info'

        # Confirm with user
        response = messagebox.askyesno(
            dialog_title,
            f"{user_msg}\n\n{base_msg}{warning_msg}",
            icon=icon
        )

        if not response:
            return

        # Log to maintenance tab
        self.log_maint(f"Starting CUDA {cuda_required} setup for {gpu_name}...", clear=True)
        self.btn_cuda_setup.config(state=tk.DISABLED)
        
        # Update progress display
        self.maint_progress['value'] = 0
        self.maint_progress_label.config(text="Downloading CUDA Toolkit...")
        self.maint_time_label.config(text="This may take 15-30 minutes...")
        
        def _setup():
            try:
                def download_callback(downloaded, total):
                    if total > 0:
                        percent = (downloaded / total) * 50
                        self.dashboard.root.after(0, lambda p=percent: self.maint_progress.config(value=p))
                        size_mb = downloaded / (1024 * 1024)
                        total_mb = total / (1024 * 1024)
                        self.dashboard.root.after(0, lambda d=size_mb, t=total_mb: 
                            self.maint_progress_label.config(text=f"Downloading: {d:.1f} / {t:.1f} MB"))

                def install_callback(message):
                    self.dashboard.root.after(0, lambda m=message: self.log_maint(m, append=True))
                    if "Installing" in message:
                        self.dashboard.root.after(0, lambda: self.maint_progress.config(value=60))

                # Import installer
                from ue5_query.utils.cuda_installer import install_cuda_with_progress
                
                success = install_cuda_with_progress(
                    download_url, 
                    self.script_dir / "temp", 
                    download_callback,
                    install_callback
                )

                if success:
                    self.dashboard.root.after(0, lambda: self.log_maint("\n[SUCCESS] CUDA installation completed!", append=True))
                    self.dashboard.root.after(0, lambda: messagebox.showinfo("Success", "CUDA Toolkit installed successfully.\nPlease restart the application."))
                else:
                    self.dashboard.root.after(0, lambda: self.log_maint("\n[FAILED] CUDA installation failed.", append=True))
                    self.dashboard.root.after(0, lambda: messagebox.showerror("Error", "CUDA installation failed. Check log for details."))

            except Exception as e:
                self.dashboard.root.after(0, lambda: self.log_maint(f"\n[ERROR] {e}", append=True))
            finally:
                self.dashboard.root.after(0, lambda: self.btn_cuda_setup.config(state=tk.NORMAL))
                self.dashboard.root.after(0, self.check_gpu_status)

        threading.Thread(target=_setup, daemon=True).start()
