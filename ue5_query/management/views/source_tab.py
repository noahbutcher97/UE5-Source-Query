import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import sys
import time
import threading
from pathlib import Path

# Try to import Theme, handle missing imports gracefully
try:
    from ue5_query.utils.gui_theme import Theme
    from ue5_query.utils.engine_helper import resolve_uproject_source
    from ue5_query.management.views.batch_folder_dialog import BatchFolderDialog
    from ue5_query.utils.index_helper import parse_index_progress, get_rebuild_command
except ImportError:
    # If run standalone
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
        from ue5_query.utils.gui_theme import Theme
        from ue5_query.utils.engine_helper import resolve_uproject_source
        from ue5_query.management.views.batch_folder_dialog import BatchFolderDialog
        from ue5_query.utils.index_helper import parse_index_progress, get_rebuild_command
    except ImportError:
        Theme = None

class SourceManagerTab:
    """
    Handles the Source Manager tab logic and layout.
    """
    def __init__(self, parent_frame, dashboard):
        """
        Args:
            parent_frame: The ttk.Frame to build the tab into
            dashboard: Reference to the main UnifiedDashboard instance (controller)
        """
        self.frame = parent_frame
        self.dashboard = dashboard
        self.source_manager = dashboard.source_manager
        self.engine_path_var = dashboard.engine_path_var
        self.maint_service = dashboard.maint_service
        self.script_dir = dashboard.script_dir
        self.cancelled = False

        self.build_ui()

    def build_ui(self):
        """Build the UI components"""
        # Main layout: PanedWindow for lists, then Actions below
        main_frame = ttk.Frame(self.frame)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Use PanedWindow for responsive vertical split
        paned = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=20, pady=(20, 10))

        # --- Engine Section ---
        engine_frame = ttk.LabelFrame(paned, text=" Engine Source (Managed) ", padding=15)
        paned.add(engine_frame, weight=1)
        
        ttk.Label(engine_frame, text="Engine Root Directory:", font=Theme.FONT_BOLD).pack(anchor=tk.W)
        
        # Read-only entry to show current configured engine root
        engine_root_entry = ttk.Entry(engine_frame, textvariable=self.engine_path_var, state='readonly')
        engine_root_entry.pack(fill=tk.X, pady=(5, 10))
        
        ttk.Label(engine_frame, text="Source Directories (Edit List Below):", font=Theme.FONT_NORMAL).pack(anchor=tk.W)
        
        # Listbox for engine dirs
        e_list_frame = ttk.Frame(engine_frame)
        e_list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        e_scrollbar = ttk.Scrollbar(e_list_frame)
        e_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.engine_listbox = tk.Listbox(e_list_frame, yscrollcommand=e_scrollbar.set, font=Theme.FONT_MONO, height=5)
        self.engine_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        e_scrollbar.config(command=self.engine_listbox.yview)
        
        # Buttons
        e_btn_frame = ttk.Frame(engine_frame)
        e_btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(e_btn_frame, text="+ Add Path", command=self.add_engine_dir).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(e_btn_frame, text="+ Add Multiple (Batch)", command=self.add_batch_engine_dirs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(e_btn_frame, text="- Remove Selected", command=self.remove_engine_dir).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(e_btn_frame, text="Reset to Default", command=self.reset_engine_dirs).pack(side=tk.LEFT)
        
        self.refresh_engine_list()

        # --- Project Section ---
        project_frame = ttk.LabelFrame(paned, text=" Project Source (Custom) ", padding=15)
        paned.add(project_frame, weight=1)
        
        ttk.Label(project_frame, text="Add folders containing your game project source code.", font=Theme.FONT_NORMAL).pack(anchor=tk.W, pady=(0,10))
        
        # Listbox for projects
        list_frame = ttk.Frame(project_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.project_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=Theme.FONT_MONO, height=5)
        self.project_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.project_listbox.yview)
        
        # Buttons
        btn_frame = ttk.Frame(project_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="+ Add Folder", command=self.add_project_folder, style="Accent.TButton").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="+ Add Multiple (Batch)", command=self.add_batch_folders).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="+ Add .uproject", command=self.add_project_uproject, style="Accent.TButton").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="- Remove Selected", command=self.remove_project_folder).pack(side=tk.LEFT)

        self.refresh_project_list()

        # --- Index Actions (Bottom) ---
        actions_frame = ttk.LabelFrame(main_frame, text=" Index Management ", padding=15)
        actions_frame.pack(fill=tk.X, padx=20, pady=(0, 20))

        # Buttons
        idx_btn_frame = ttk.Frame(actions_frame)
        idx_btn_frame.pack(fill=tk.X, pady=(0, 10))

        self.btn_update = tk.Button(
            idx_btn_frame,
            text="⚡ Update Index (Incremental)",
            command=lambda: self.run_index_update(force=False),
            bg=Theme.SUCCESS,
            fg="white",
            padx=15, pady=5, relief=tk.FLAT, cursor="hand2"
        )
        self.btn_update.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_rebuild = tk.Button(
            idx_btn_frame,
            text="🔄 Full Rebuild (Force)",
            command=lambda: self.run_index_update(force=True),
            bg=Theme.SECONDARY,
            fg="white",
            padx=15, pady=5, relief=tk.FLAT, cursor="hand2"
        )
        self.btn_rebuild.pack(side=tk.LEFT)

        self.btn_cancel = tk.Button(
            idx_btn_frame,
            text="Stop",
            command=self.cancel_op,
            bg="#7F8C8D", fg="white",
            padx=10, pady=5, relief=tk.FLAT, cursor="hand2",
            state=tk.DISABLED
        )
        self.btn_cancel.pack(side=tk.RIGHT)

        # Progress UI
        self.progress_bar = ttk.Progressbar(actions_frame, mode='determinate', maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))

        status_line = ttk.Frame(actions_frame)
        status_line.pack(fill=tk.X)

        self.lbl_progress = ttk.Label(status_line, text="Ready", font=Theme.FONT_NORMAL)
        self.lbl_progress.pack(side=tk.LEFT)

        self.btn_toggle_log = ttk.Button(
            status_line, 
            text="👁 Show Log", 
            width=12,
            command=self.toggle_log
        )
        self.btn_toggle_log.pack(side=tk.RIGHT)

        # Collapsible Log Panel
        self.log_visible = False
        self.log_panel = scrolledtext.ScrolledText(
            actions_frame, 
            font=("Consolas", 9), 
            height=8,
            state=tk.DISABLED,
            bg="#f8f9fa"
        )
        # Not packed initially

    def toggle_log(self):
        if self.log_visible:
            self.log_panel.pack_forget()
            self.btn_toggle_log.config(text="👁 Show Log")
        else:
            self.log_panel.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
            self.btn_toggle_log.config(text="👁 Hide Log")
        self.log_visible = not self.log_visible

    def log_index(self, msg, clear=False):
        self.log_panel.config(state=tk.NORMAL)
        if clear:
            self.log_panel.delete(1.0, tk.END)
        self.log_panel.insert(tk.END, msg + ("\n" if not msg.endswith("\n") else ""))
        self.log_panel.see(tk.END)
        self.log_panel.config(state=tk.DISABLED)

    def cancel_op(self):
        if self.maint_service.current_process:
            if messagebox.askyesno("Cancel", "Cancel current operation?"):
                self.cancelled = True
                if self.maint_service.cancel_current_process():
                    self.lbl_progress.config(text="Cancelled.")
                    self.log_index("\n[CANCELLED] Process terminated by user.")
                    self.btn_update.config(state=tk.NORMAL)
                    self.btn_rebuild.config(state=tk.NORMAL)
                    self.btn_cancel.config(state=tk.DISABLED)

    def run_index_update(self, force=False):
        """Run index update (incremental or force)"""
        mode = "Rebuild" if force else "Update"
        msg = "Rebuild vector index completely? This takes longer." if force else "Update index with changes? This is fast."
        
        if not messagebox.askyesno(f"Confirm {mode}", msg):
            return

        # Auto-expand log when starting
        if not self.log_visible:
            self.toggle_log()

        self.btn_update.config(state=tk.DISABLED)
        self.btn_rebuild.config(state=tk.DISABLED)
        self.btn_cancel.config(state=tk.NORMAL)
        self.cancelled = False

        # Reset UI
        self.progress_bar['value'] = 0
        self.lbl_progress.config(text=f"Starting {mode}...")
        self.log_index(f"--- Starting Index {mode} ({'Full' if force else 'Incremental'}) ---", clear=True)

        start_time = time.time()

        def update_progress(value, label_text):
            self.progress_bar['value'] = value
            self.lbl_progress.config(text=label_text)

        def on_complete(success, message):
            self.dashboard.root.after(0, lambda: self.btn_update.config(state=tk.NORMAL))
            self.dashboard.root.after(0, lambda: self.btn_rebuild.config(state=tk.NORMAL))
            self.dashboard.root.after(0, lambda: self.btn_cancel.config(state=tk.DISABLED))
            
            if success:
                elapsed = time.time() - start_time
                time_str = f"{elapsed:.1f}s" if elapsed < 60 else f"{elapsed/60:.1f}m"
                self.dashboard.root.after(0, lambda: update_progress(100, f"{mode} Complete! ({time_str})"))
                self.dashboard.root.after(0, lambda: self.log_index(f"\n[SUCCESS] Index {mode} finished in {time_str}"))
                self.dashboard.root.after(0, lambda: messagebox.showinfo("Success", f"Index {mode} Complete!"))
            else:
                if not self.cancelled:
                    self.dashboard.root.after(0, lambda: update_progress(0, f"{mode} Failed"))
                    self.dashboard.root.after(0, lambda m=message: self.log_index(f"\n[ERROR] {m}"))
                    self.dashboard.root.after(0, lambda m=message: messagebox.showerror("Error", m))

        def log_handler(line):
            stripped = line.strip()
            # 1. Update Log Panel
            self.dashboard.root.after(0, lambda: self.log_index(stripped))
            
            # 2. Parse for progress
            prog, label = parse_index_progress(stripped)
            if prog is not None:
                self.dashboard.root.after(0, lambda p=prog, l=label: update_progress(p, l))

        # Use extracted command builder
        args = get_rebuild_command(self.script_dir, force=force)

        self.maint_service.run_task(
            task_name=f"Index {mode}",
            command=args,
            callback=on_complete,
            log_callback=log_handler
        )

    def refresh_engine_list(self):
        self.engine_listbox.delete(0, tk.END)
        engine_root = self.engine_path_var.get().strip()
        for d in self.source_manager.get_engine_dirs():
            if engine_root and "{ENGINE_ROOT}" in d:
                resolved = d.replace("{ENGINE_ROOT}", engine_root)
                self.engine_listbox.insert(tk.END, resolved)
            else:
                self.engine_listbox.insert(tk.END, d)

    def add_engine_dir(self):
        engine_root = self.engine_path_var.get().strip()
        initial_dir = engine_root if engine_root and Path(engine_root).exists() else "/"
        
        d = filedialog.askdirectory(title="Add Engine Source Path", initialdir=initial_dir)
        if d:
            # Normalize path
            path_obj = Path(d)
            path_str = str(path_obj)
            
            # Try to replace engine root with placeholder
            if engine_root:
                root_obj = Path(engine_root)
                try:
                    rel_path = path_obj.relative_to(root_obj)
                    path_str = str(Path("{ENGINE_ROOT}") / rel_path)
                except ValueError:
                    pass
            
            success, msg = self.source_manager.add_engine_dir(path_str)
            if success:
                self.refresh_engine_list()
                if msg != "Path added successfully.":
                    messagebox.showinfo("Optimization", msg)
            else:
                messagebox.showinfo("Info", msg)

    def add_batch_engine_dirs(self):
        engine_root = self.engine_path_var.get().strip()
        start_dir = "/"
        if engine_root and Path(engine_root).exists():
             start_dir = str(Path(engine_root) / "Source")
             if not Path(start_dir).exists():
                 start_dir = engine_root

        def _on_add(paths):
            processed_paths = []
            for p in paths:
                path_obj = Path(p)
                path_str = str(path_obj)
                
                # Try to replace engine root with placeholder
                if engine_root:
                    root_obj = Path(engine_root)
                    try:
                        rel_path = path_obj.relative_to(root_obj)
                        path_str = str(Path("{ENGINE_ROOT}") / rel_path)
                    except ValueError:
                        pass
                processed_paths.append(path_str)

            count, messages = self.source_manager.add_engine_dirs(processed_paths)

            self.refresh_engine_list()
            
            summary = f"Processed {len(paths)} paths.\nAdded: {count}"
            if messages:
                summary += "\n\nDetails:\n" + "\n".join(messages[:10])
                if len(messages) > 10:
                    summary += f"\n...and {len(messages)-10} more."
            
            messagebox.showinfo("Batch Add", summary)

        BatchFolderDialog(self.frame.winfo_toplevel(), initial_dir=start_dir, on_add=_on_add)

    def remove_engine_dir(self):
        sel = self.engine_listbox.curselection()
        if sel:
            path = self.engine_listbox.get(sel[0])
            if messagebox.askyesno("Confirm", f"Remove '{path}' from list?"):
                self.source_manager.remove_engine_dir(path)
                self.refresh_engine_list()

    def reset_engine_dirs(self):
        if messagebox.askyesno("Confirm", "Reset engine source list to defaults?"):
            self.source_manager.reset_engine_dirs()
            self.refresh_engine_list()

    def refresh_project_list(self):
        self.project_listbox.delete(0, tk.END)
        for d in self.source_manager.get_project_dirs():
            self.project_listbox.insert(tk.END, d)

    def add_project_uproject(self):
        path = filedialog.askopenfilename(title="Select .uproject", filetypes=[("Unreal Project", "*.uproject")])
        if path:
            source_dir = resolve_uproject_source(path)
            if source_dir:
                success, msg = self.source_manager.add_project_dir(source_dir)
                if success:
                    self.refresh_project_list()
                    if msg != "Path added successfully.":
                        messagebox.showinfo("Optimization", msg)
                    else:
                        messagebox.showinfo("Success", f"Added project source: {source_dir}")
                else:
                    messagebox.showinfo("Info", msg)
            else:
                messagebox.showerror("Error", "Could not find 'Source' directory next to .uproject file.")

    def add_project_folder(self):
        path = filedialog.askdirectory(title="Select Project Source Folder")
        if path:
            success, msg = self.source_manager.add_project_dir(path)
            if success:
                self.refresh_project_list()
                if msg != "Path added successfully.":
                    messagebox.showinfo("Optimization", msg)
            else:
                messagebox.showinfo("Info", msg)

    def add_batch_folders(self):
        """Open batch selection dialog"""
        def _on_add(paths):
            count, messages = self.source_manager.add_project_dirs(paths)
                    
            self.refresh_project_list()
            summary = f"Processed {len(paths)} paths.\nAdded: {count}"
            if messages:
                summary += "\n\nDetails:\n" + "\n".join(messages[:10])
                if len(messages) > 10:
                    summary += f"\n...and {len(messages)-10} more."
            messagebox.showinfo("Batch Add", summary)

        BatchFolderDialog(self.frame.winfo_toplevel(), on_add=_on_add)

    def remove_project_folder(self):
        sel = self.project_listbox.curselection()
        if not sel:
            return
        path = self.project_listbox.get(sel[0])
        if messagebox.askyesno("Confirm", f"Remove '{path}' from index?"):
            self.source_manager.remove_project_dir(path)
            self.refresh_project_list()
