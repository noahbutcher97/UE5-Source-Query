import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import os

class BatchFolderDialog(tk.Toplevel):
    """
    Dialog for batch selecting subfolders from a root directory.
    Supports navigation into subdirectories.
    """
    def __init__(self, parent, initial_dir=None, on_add=None):
        super().__init__(parent)
        self.title("Batch Add Folders")
        self.geometry("600x600")
        self.transient(parent) # Stay on top
        
        self.on_add = on_add
        self.root_path = Path(initial_dir) if initial_dir else Path.cwd()
        if not self.root_path.exists():
            self.root_path = Path.cwd()
            
        self.selected_folders = set() # Set of full paths (strings)
        
        self._build_ui()
        self._refresh_list()
        
        # Proper cleanup
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def destroy(self):
        try:
            self.canvas.unbind_all("<MouseWheel>")
        except:
            pass
        super().destroy()

    def _build_ui(self):
        # 1. Navigation / Root Selection
        nav_frame = ttk.Frame(self, padding=10)
        nav_frame.pack(fill=tk.X)
        
        # Row 1: Entry and Browse
        path_frame = ttk.Frame(nav_frame)
        path_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(path_frame, text="Current:").pack(side=tk.LEFT)
        self.path_var = tk.StringVar(value=str(self.root_path))
        entry = ttk.Entry(path_frame, textvariable=self.path_var, width=50)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        entry.bind("<Return>", lambda e: self._on_path_entry())
        
        ttk.Button(path_frame, text="Browse...", command=self._browse_root).pack(side=tk.LEFT)
        
        # Row 2: Up Button and Select All
        ctrl_frame = ttk.Frame(nav_frame)
        ctrl_frame.pack(fill=tk.X)
        
        ttk.Button(ctrl_frame, text="⬆ Up", command=self._navigate_up).pack(side=tk.LEFT)
        ttk.Separator(ctrl_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        ttk.Button(ctrl_frame, text="Select All", command=self._select_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl_frame, text="Select None", command=self._select_none).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(ctrl_frame, text="(Double-click folder name to open)", font=("Arial", 8), foreground="#666").pack(side=tk.RIGHT)

        # 2. Folder List
        list_frame = ttk.Frame(self, padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(list_frame, bg="#FFFFFF")
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.canvas.yview)
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

        # 3. Actions / Status
        action_frame = ttk.Frame(self, padding=10)
        action_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.lbl_status = ttk.Label(action_frame, text="0 folders selected")
        self.lbl_status.pack(side=tk.LEFT)
        
        ttk.Button(action_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(action_frame, text="Add Selected", command=self._confirm_add, style="Accent.TButton").pack(side=tk.RIGHT, padx=5)

    def _browse_root(self):
        path = filedialog.askdirectory(initialdir=self.root_path, title="Select Directory")
        if path:
            self._navigate_to(Path(path))

    def _on_path_entry(self):
        path_str = self.path_var.get()
        if os.path.exists(path_str):
            self._navigate_to(Path(path_str))

    def _navigate_to(self, path):
        self.root_path = path
        self.path_var.set(str(self.root_path))
        self._refresh_list()

    def _navigate_up(self):
        if self.root_path.parent != self.root_path:
            self._navigate_to(self.root_path.parent)

    def _refresh_list(self):
        # Clear existing
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.checkbox_vars = {} # Map Path -> BooleanVar
        
        try:
            # List immediate subdirectories (including hidden ones)
            subdirs = [d for d in self.root_path.iterdir() if d.is_dir()]
            subdirs.sort(key=lambda x: x.name.lower())
            
            if not subdirs:
                ttk.Label(self.scrollable_frame, text="(No subfolders found)").pack(anchor=tk.W, padx=5, pady=5)
                return

            for folder in subdirs:
                row = ttk.Frame(self.scrollable_frame)
                row.pack(fill=tk.X, padx=5, pady=2)
                
                # Checkbox
                var = tk.BooleanVar(value=False)
                # Check if this folder was previously selected (persist state?)
                # For batch adding, we usually just care about the final list.
                # Since we are navigating, persisting selection across folders is tricky visually.
                # We will simplify: checkbox state is local to view, but we collect into final list?
                # No, standard dialog pattern is: select what you see, add it.
                # If user navigates away, selection is cleared? 
                # Let's keep it simple: Selection is cleared on navigation. 
                # If they want to add from multiple places, they run the dialog multiple times or we need a "Basket" UI.
                # "Add Selected" adds and closes. So single-shot.
                
                self.checkbox_vars[folder] = var
                
                cb = ttk.Checkbutton(row, variable=var, command=self._update_count)
                cb.pack(side=tk.LEFT)
                
                # Folder Name (Double click to enter)
                lbl = ttk.Label(row, text=folder.name, cursor="hand2")
                lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
                lbl.bind("<Button-1>", lambda e, v=var: v.set(not v.get()) or self._update_count()) # Click toggles check
                lbl.bind("<Double-Button-1>", lambda e, p=folder: self._navigate_to(p))
                
                # Enter Button
                btn_go = ttk.Button(row, text="➡", width=3, command=lambda p=folder: self._navigate_to(p))
                btn_go.pack(side=tk.RIGHT)
                
        except Exception as e:
            ttk.Label(self.scrollable_frame, text=f"Error reading directory: {e}").pack()
            
        self._update_count()

    def _update_count(self):
        count = sum(1 for v in self.checkbox_vars.values() if v.get())
        self.lbl_status.config(text=f"{count} folders selected in current view")

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
            self.on_add([str(p) for p in selected])
            
        self.destroy()

    def _on_mousewheel(self, event):
        try:
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        except tk.TclError:
            pass # Widget destroyed