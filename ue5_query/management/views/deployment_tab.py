import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import subprocess
from pathlib import Path
import json
import datetime

from ue5_query.utils.gui_theme import Theme
from ue5_query.utils.deployment_detector import get_detector

# Handle tools import which is outside the package
try:
    from tools.update import UpdateManager
except ImportError:
    # Fallback if PYTHONPATH isn't set perfectly
    import sys
    root = Path(__file__).resolve().parent.parent.parent.parent
    if str(root) not in sys.path:
        sys.path.append(str(root))
    from tools.update import UpdateManager

class DeploymentManagerTab:
    """
    Dev-Mode Only: Manage multiple deployments from the Dev Repo.
    """
    def __init__(self, parent_frame, dashboard):
        self.frame = parent_frame
        self.dashboard = dashboard
        self.detector = get_detector(refresh=True)
        self.current_installer = None
        self.current_indexer_process = None
        
        self.build_ui()
        self.refresh_list()

    def build_ui(self):
        # Use PanedWindow for split view
        paned = ttk.PanedWindow(self.frame, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # === TOP: Registry ===
        top_frame = ttk.Frame(paned)
        paned.add(top_frame, weight=3)

        # Top Action Bar
        action_frame = ttk.Frame(top_frame, padding=10)
        action_frame.pack(fill=tk.X)
        
        ttk.Label(action_frame, text="Active Deployments", font=Theme.FONT_BOLD).pack(side=tk.LEFT)
        
        btn_frame = ttk.Frame(action_frame)
        btn_frame.pack(side=tk.RIGHT)
        
        ttk.Button(btn_frame, text="🔄 Refresh", command=self.refresh_list).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🚀 Push Updates (All)", command=self.push_all_updates, style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="➕ Quick Deploy...", command=self.quick_deploy_wizard).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🤖 Copy Agent Config", command=self.copy_agent_config).pack(side=tk.LEFT, padx=5)
        self.btn_cancel = ttk.Button(btn_frame, text="🛑 Cancel", command=self.cancel_active_operation, state=tk.DISABLED)
        self.btn_cancel.pack(side=tk.LEFT, padx=5)

        # Deployment List (Treeview)
        list_frame = ttk.Frame(top_frame, padding=(10, 0, 10, 10))
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("path", "version", "status", "last_updated")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        
        self.tree.heading("path", text="Path")
        self.tree.heading("version", text="Version")
        self.tree.heading("status", text="Status")
        self.tree.heading("last_updated", text="Last Updated")
        
        self.tree.column("path", width=400)
        self.tree.column("version", width=100)
        self.tree.column("status", width=100)
        self.tree.column("last_updated", width=150)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Context Menu
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="Push Update", command=self.push_selected)
        self.context_menu.add_command(label="Verify Integrity", command=self.verify_selected)
        self.context_menu.add_command(label="Copy Agent Config", command=self.copy_agent_config)
        self.context_menu.add_command(label="Remove from Registry", command=self.remove_selected)
        
        self.tree.bind("<Button-3>", self._show_context_menu)

        # === BOTTOM: Activity Log ===
        bottom_frame = ttk.LabelFrame(paned, text=" Activity Log & Indexing ", padding=5)
        paned.add(bottom_frame, weight=1)

        self.progress_bar = ttk.Progressbar(bottom_frame, mode='determinate')
        self.progress_bar.pack(fill=tk.X, padx=5, pady=(0, 5))

        self.log_text = scrolledtext.ScrolledText(bottom_frame, font=("Consolas", 9), state=tk.DISABLED, height=8)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.tag_config("info", foreground="black")
        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("success", foreground="#2E7D32")

    def log(self, msg, tag="info"):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{msg}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def copy_agent_config(self):
        """Generate and copy system prompt for selected deployment"""
        sel = self.tree.selection()
        if not sel: 
            messagebox.showwarning("Select Deployment", "Please select a deployment to generate config for.")
            return
        
        path = self.tree.item(sel[0])['values'][0]
        ask_bat = Path(path) / "ask.bat"
        
        prompt = f"""You have access to the UE5 Source Query tool at:
{ask_bat}

To search the engine code, execute:
{ask_bat} "your query" --format code

To get a JSON response:
{ask_bat} "your query" --format json

Always cite the file path and line number when answering based on these results."""

        self.frame.clipboard_clear()
        self.frame.clipboard_append(prompt)
        messagebox.showinfo("Copied", "Agent system prompt copied to clipboard!")

    def _show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def cancel_active_operation(self):
        if self.current_installer:
            self.current_installer.cancel()
            self.log("Cancelling installation...", "error")
        
        if self.current_indexer_process:
            try:
                self.current_indexer_process.terminate()
            except:
                pass
            self.log("Cancelling indexer...", "error")
            self.current_indexer_process = None
            
        self.btn_cancel.config(state=tk.DISABLED)

    def refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        self.detector = get_detector(refresh=True)
        
        deployments = self.detector.get_deployments()
        
        for deploy in deployments:
            path = deploy.path
            status = deploy.status or "Valid"
            last_updated = deploy.last_updated or "Never"
            
            # Get version if accessible
            version = "Unknown"
            if deploy.is_valid:
                try:
                    ver_file = Path(path) / "VERSION.txt"
                    if ver_file.exists():
                        version = ver_file.read_text().strip()
                except:
                    pass
            
            # Color code status
            tag = "valid" if deploy.is_valid else "invalid"
            
            self.tree.insert("", tk.END, values=(path, version, status, last_updated), tags=(tag,))
            
        self.tree.tag_configure("valid", foreground="green")
        self.tree.tag_configure("invalid", foreground="red")

    def push_all_updates(self):
        if not messagebox.askyesno("Confirm Push", "Push updates to ALL registered deployments?"):
            return
            
        def _run():
            try:
                logger = lambda msg: self.frame.after(0, lambda: self.log(msg, "info"))
                manager = UpdateManager(Path.cwd(), logger=logger)
                
                count = manager.push_to_all_deployments()
                self.frame.after(0, lambda: messagebox.showinfo("Push Complete", f"Updated {count} deployments."))
                self.frame.after(0, self.refresh_list)
            except Exception as e:
                self.frame.after(0, lambda: messagebox.showerror("Error", f"Push failed: {e}"))

        threading.Thread(target=_run, daemon=True).start()

    def push_selected(self):
        sel = self.tree.selection()
        if not sel: return
        
        path = self.tree.item(sel[0])['values'][0]
        
        def _run():
            try:
                logger = lambda msg: self.frame.after(0, lambda: self.log(msg, "info"))
                manager = UpdateManager(Path.cwd(), logger=logger)
                
                success = manager.push_to_deployment(Path(path))
                if success:
                    self.frame.after(0, lambda: messagebox.showinfo("Success", f"Updated {path}"))
                else:
                    self.frame.after(0, lambda: messagebox.showerror("Failed", f"Failed to update {path}"))
                self.frame.after(0, self.refresh_list)
            except Exception as e:
                self.frame.after(0, lambda: messagebox.showerror("Error", str(e)))

        threading.Thread(target=_run, daemon=True).start()

    def remove_selected(self):
        sel = self.tree.selection()
        if not sel: return
        path = self.tree.item(sel[0])['values'][0]
        
        if messagebox.askyesno("Confirm", f"Remove {path} from registry? (Does not delete files)"):
            from ue5_query.utils.deployment_detector import DeploymentRegistry
            reg = DeploymentRegistry(Path.cwd())
            reg.unregister_deployment(Path(path))
            self.refresh_list()

    def verify_selected(self):
        sel = self.tree.selection()
        if not sel: return
        path = self.tree.item(sel[0])['values'][0]
        
        manager = UpdateManager(Path(path))
        if manager.load_config():
            if manager.verify_installation():
                messagebox.showinfo("Integrity Check", "Installation is valid.")
            else:
                messagebox.showwarning("Integrity Check", "Installation is missing components!")
        else:
            messagebox.showerror("Error", "Could not load deployment config.")

    def quick_deploy_wizard(self):
        """Launch the Quick Deploy wizard (simplified flow)"""
        path = filedialog.askopenfilename(title="Select .uproject to deploy to", filetypes=[("Unreal Project", "*.uproject")])
        if not path: return
        
        project_root = Path(path).parent
        target_dir = project_root / "Tools" / "UE5-Source-Query"
        
        if messagebox.askyesno("Quick Deploy", f"Deploy tool to:\n{target_dir}\n\nThis will inherit configuration from this Dev Repo."):
            self._run_quick_deploy(target_dir, project_root)

    def _run_indexer_with_status(self, target_path, registry, installer):
        """Run indexing and stream to log, updating status"""
        def _run():
            self.frame.after(0, lambda: self.log(f"--- Starting Indexer for {target_path} ---", "info"))
            self.frame.after(0, lambda: self.btn_cancel.config(state=tk.NORMAL))
            
            rebuild_script = target_path / "tools" / "rebuild-index.bat"
            
            try:
                self.current_indexer_process = subprocess.Popen(
                    [str(rebuild_script), "--verbose"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=str(target_path),
                    bufsize=1,
                    universal_newlines=True
                )
                
                for line in self.current_indexer_process.stdout:
                    self.frame.after(0, lambda l=line: self.log(l.strip(), "info"))
                    
                self.current_indexer_process.wait()
                
                if self.current_indexer_process.returncode == 0:
                    self.frame.after(0, lambda: self.log("✓ Indexing Complete!", "success"))
                    installer.update_config_status(target_path, "Ready")
                    registry.register_deployment(target_path, status="Ready")
                    self.frame.after(0, self.refresh_list)
                    self.frame.after(0, lambda: messagebox.showinfo("Success", "Deployment and Indexing Complete!"))
                else:
                    self.frame.after(0, lambda: self.log(f"✗ Indexing Failed (Code {self.current_indexer_process.returncode})", "error"))
                    installer.update_config_status(target_path, "Index Failed")
                    registry.register_deployment(target_path, status="Index Failed")
                    self.frame.after(0, self.refresh_list)
                    
            except Exception as e:
                self.frame.after(0, lambda: self.log(f"Error running indexer: {e}", "error"))
                installer.update_config_status(target_path, "Error")
                registry.register_deployment(target_path, status="Error")
                self.frame.after(0, self.refresh_list)
            finally:
                self.current_indexer_process = None
                self.frame.after(0, lambda: self.btn_cancel.config(state=tk.DISABLED))

        threading.Thread(target=_run, daemon=True).start()

    def _run_quick_deploy(self, target_dir, project_root):
        """Execute full deployment and initialization in background"""
        
        # 0. Pre-Registration (Immediate UI Feedback)
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            # Create placeholder config
            initial_config = {
                "deployment_info": {
                    "deployed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "status": "Provisioning"
                }
            }
            with open(target_dir / ".ue5query_deploy.json", 'w') as f:
                json.dump(initial_config, f)
                
            # Register immediately
            from ue5_query.utils.deployment_detector import DeploymentRegistry
            reg = DeploymentRegistry(Path.cwd())
            reg.register_deployment(target_dir, status="Provisioning")
            self.refresh_list()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to initialize deployment: {e}")
            return
        
        def _deploy_thread():
            try:
                self.frame.after(0, lambda: self.progress_bar.config(value=0))
                self.frame.after(0, lambda: self.btn_cancel.config(state=tk.NORMAL))
                self.frame.after(0, lambda: messagebox.showinfo("Deploying", 
                    "Deployment started in background.\n\n" 
                    "Check the Activity Log for progress."))
                
                # Import core logic (lazy load)
                from ue5_query.utils.installer_core import InstallerCore, OperationCancelled
                from ue5_query.utils.engine_helper import get_engine_version_from_uproject, get_available_engines
                
                # Update status
                reg.register_deployment(target_dir, status="Installing")
                self.frame.after(0, self.refresh_list)
                
                # Progress callback
                def on_progress(msg, pct):
                    self.frame.after(0, lambda: self.log(msg, "info"))
                    self.frame.after(0, lambda: self.progress_bar.config(value=pct))

                # 1. Detect Engine Path
                # First check project itself
                uproject_path = next(project_root.glob("*.uproject"), None)
                engine_version = None
                if uproject_path:
                    engine_version = get_engine_version_from_uproject(str(uproject_path))
                
                # Now find the path for this version
                engine_path = ""
                if engine_version:
                    # Try to find matching engine in known installations
                    engines = get_available_engines(self.dashboard.script_dir)
                    for eng in engines:
                        if engine_version in eng.get('version', ''):
                            engine_path = str(eng['engine_root'])
                            break
                            
                # Fallback to dev repo's engine path if still unknown (often safe for local dev)
                if not engine_path:
                    engine_path = self.dashboard.config_manager.get('UE_ENGINE_ROOT', '')

                # 2. Prepare Configuration
                config = self.dashboard.config_manager._config.copy()
                config['UE_ENGINE_ROOT'] = engine_path
                # Ensure vector store is local to deployment
                config['VECTOR_OUTPUT_DIR'] = str(target_dir / 'data')

                # 3. Detect Project Source
                project_source = project_root / "Source"
                project_dirs = []
                if project_source.exists():
                    project_dirs.append(str(project_source))

                # 4. Run Installer
                installer = InstallerCore(Path.cwd(), logger=lambda m: self.frame.after(0, lambda: self.log(m, "info")))
                self.current_installer = installer
                
                installer.install(
                    target_path=target_dir,
                    config_settings=config,
                    engine_path=engine_path,
                    project_dirs=project_dirs,
                    create_venv=True,
                    setup_gpu=True, # Assume dev machine has GPU if dev repo used it
                    on_progress=on_progress
                )
                
                # Update status to Indexing
                installer.update_config_status(target_dir, "Indexing")
                reg.register_deployment(target_dir, status="Indexing")
                self.frame.after(0, self.refresh_list)
                
                # 5. Launch Indexer (Integrated)
                self.frame.after(0, lambda: self.log(f"Deployment structure created at {target_dir}", "success"))
                self._run_indexer_with_status(target_dir, reg, installer)
            
            except OperationCancelled:
                installer.update_config_status(target_dir, "Cancelled")
                reg.register_deployment(target_dir, status="Cancelled")
                self.frame.after(0, lambda: self.log("Deployment cancelled.", "error"))
                self.frame.after(0, self.refresh_list)
            except Exception as e:
                import traceback
                traceback.print_exc()
                installer.update_config_status(target_dir, "Error")
                reg.register_deployment(target_dir, status="Error")
                self.frame.after(0, self.refresh_list)
                self.frame.after(0, lambda: messagebox.showerror("Error", f"Deploy failed: {e}"))
            finally:
                self.current_installer = None
                self.frame.after(0, lambda: self.btn_cancel.config(state=tk.DISABLED))

        threading.Thread(target=_deploy_thread, daemon=True).start()