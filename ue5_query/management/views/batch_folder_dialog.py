import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import os

class BatchFolderDialog(tk.Toplevel):
    """
    Dialog for batch selecting subfolders from a root directory.
    Useful for adding multiple plugins or modules at once.
    """
    def __init__(self, parent, initial_dir=None, on_add=None):
        super().__init__(parent)
        self.title("Batch Add Folders")
        self.geometry("600x500")
        self.transient(parent) # Stay on top
        
        self.on_add = on_add
        self.root_path = Path(initial_dir) if initial_dir else Path.cwd()
        self.selected_folders = set()
        
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        # 1. Root Selection
        top_frame = ttk.Frame(self, padding=10)
        top_frame.pack(fill=tk.X)
        
        ttk.Label(top_frame, text="Root Directory:").pack(side=tk.LEFT)
        self.path_var = tk.StringVar(value=str(self.root_path))
        entry = ttk.Entry(top_frame, textvariable=self.path_var, width=50)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        entry.bind("<Return>", lambda e: self._on_path_entry())
        
        ttk.Button(top_frame, text="Browse...", command=self._browse_root).pack(side=tk.LEFT)

        # 2. Checkbox List
        list_frame = ttk.LabelFrame(self, text=" Subfolders ", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Select All / None
        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(btn_frame, text="Select All", command=self._select_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Select None", command=self._select_none).pack(side=tk.LEFT, padx=2)
        
        # Scrollable Canvas for Checkboxes
        canvas_frame = ttk.Frame(list_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg="#FFFFFF")
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Mousewheel
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # 3. Actions
        action_frame = ttk.Frame(self, padding=10)
        action_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        ttk.Button(action_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(action_frame, text="Add Selected", command=self._confirm_add, style="Accent.TButton").pack(side=tk.RIGHT, padx=5)
        
        self.lbl_status = ttk.Label(action_frame, text="0 folders selected")
        self.lbl_status.pack(side=tk.LEFT)

    def _browse_root(self):
        path = filedialog.askdirectory(initialdir=self.root_path, title="Select Root Directory")
        if path:
            self.root_path = Path(path)
            self.path_var.set(str(self.root_path))
            self._refresh_list()

    def _on_path_entry(self):
        path_str = self.path_var.get()
        if os.path.exists(path_str):
            self.root_path = Path(path_str)
            self._refresh_list()

    def _refresh_list(self):
        # Clear existing
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.checkbox_vars = {}
        self.selected_folders.clear()
        
        try:
            # List immediate subdirectories
            # Filter for valid source folders (optional, but helpful)
            subdirs = [d for d in self.root_path.iterdir() if d.is_dir() and not d.name.startswith('.')]
            subdirs.sort(key=lambda x: x.name.lower())
            
            if not subdirs:
                ttk.Label(self.scrollable_frame, text="(No subfolders found)").pack(anchor=tk.W, padx=5, pady=5)
                return

            for folder in subdirs:
                var = tk.BooleanVar(value=False)
                self.checkbox_vars[folder] = var
                cb = ttk.Checkbutton(
                    self.scrollable_frame, 
                    text=folder.name, 
                    variable=var,
                    command=self._update_count
                )
                cb.pack(anchor=tk.W, fill=tk.X, padx=5, pady=2)
                
        except Exception as e:
            ttk.Label(self.scrollable_frame, text=f"Error reading directory: {e}").pack()

    def _update_count(self):
        count = sum(1 for v in self.checkbox_vars.values() if v.get())
        self.lbl_status.config(text=f"{count} folders selected")

    def _select_all(self):
        for var in self.checkbox_vars.values():
            var.set(True)
        self._update_count()

    def _select_none(self):
        for var in self.checkbox_vars.values():
            var.set(False)
        self._update_count()

    def _confirm_add(self):
        selected = [folder for folder, var in self.checkbox_vars.items() if v.get()]
        if not selected:
            messagebox.showinfo("None Selected", "Please select at least one folder.")
            return
            
        if self.on_add:
            # Convert paths to strings
            self.on_add([str(p) for p in selected])
            
        self.destroy()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
