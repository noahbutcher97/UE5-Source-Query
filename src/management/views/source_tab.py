import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sys
from pathlib import Path

# Try to import Theme, handle missing imports gracefully
try:
    from src.utils.gui_theme import Theme
    from src.utils.engine_helper import resolve_uproject_source
except ImportError:
    # If run standalone
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
        from src.utils.gui_theme import Theme
        from src.utils.engine_helper import resolve_uproject_source
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

        self.build_ui()

    def build_ui(self):
        """Build the UI components"""
        # Use PanedWindow for responsive vertical split
        paned = ttk.PanedWindow(self.frame, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

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
        ttk.Button(btn_frame, text="+ Add .uproject", command=self.add_project_uproject, style="Accent.TButton").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="- Remove Selected", command=self.remove_project_folder).pack(side=tk.LEFT)

        self.refresh_project_list()

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
            
            if self.source_manager.add_engine_dir(path_str):
                self.refresh_engine_list()
            else:
                messagebox.showinfo("Info", "Directory already in list.")

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
                if self.source_manager.add_project_dir(source_dir):
                    self.refresh_project_list()
                    messagebox.showinfo("Success", f"Added project source: {source_dir}")
                else:
                    messagebox.showinfo("Info", "Directory already exists in list.")
            else:
                messagebox.showerror("Error", "Could not find 'Source' directory next to .uproject file.")

    def add_project_folder(self):
        path = filedialog.askdirectory(title="Select Project Source Folder")
        if path:
            if self.source_manager.add_project_dir(path):
                self.refresh_project_list()
            else:
                messagebox.showinfo("Info", "Directory already exists in list.")

    def remove_project_folder(self):
        sel = self.project_listbox.curselection()
        if not sel:
            return
        path = self.project_listbox.get(sel[0])
        if messagebox.askyesno("Confirm", f"Remove '{path}' from index?"):
            self.source_manager.remove_project_dir(path)
            self.refresh_project_list()
