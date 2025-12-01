"""
UE5 Source Query Tool - Unified Management Dashboard
Central hub for configuration, health checks, and system management.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import sys
import subprocess
import threading
from pathlib import Path
import json

# Add src to path to import utils
SCRIPT_DIR = Path(__file__).parent.parent.parent
sys.path.append(str(SCRIPT_DIR))

from src.utils.gui_theme import Theme
from src.utils.config_manager import ConfigManager
from src.utils.source_manager import SourceManager
from src.utils.engine_helper import get_available_engines, resolve_uproject_source
from src.utils.gpu_helper import detect_nvidia_gpu, get_gpu_summary, get_gpu_requirements_text
from src.core.hybrid_query import hybrid_query

class UnifiedDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("UE5 Source Query Dashboard")
        self.root.geometry("1000x700")
        
        # Apply Theme
        Theme.apply(self.root)
        
        self.script_dir = SCRIPT_DIR
        self.source_manager = SourceManager(self.script_dir)
        self.config_manager = ConfigManager(self.script_dir)

        # Configuration variables
        self.api_key_var = tk.StringVar(value=self.config_manager.get('ANTHROPIC_API_KEY', ''))
        self.engine_path_var = tk.StringVar(value=self.config_manager.get('UE_ENGINE_ROOT', ''))
        self.vector_store_var = tk.StringVar(value=self.config_manager.get('VECTOR_OUTPUT_DIR', str(self.script_dir / 'data')))
        self.embed_model_var = tk.StringVar(value=self.config_manager.get('EMBED_MODEL', 'microsoft/unixcoder-base'))
        self.api_model_var = tk.StringVar(value=self.config_manager.get('ANTHROPIC_MODEL', 'claude-3-haiku-20240307'))
        self.query_scope_var = tk.StringVar(value="engine")

        self.create_layout()
        
        # Add trace to update engine list when engine path changes
        self.engine_path_var.trace_add("write", lambda *args: self.refresh_engine_list())

        # Load engine path from source_manager after layout creation
        self._load_initial_engine_path()
        
    def _load_initial_engine_path(self):
        # This will load the path from EngineDirs.txt if present, or detect it.
        # It's better to auto-detect/populate the engine_path_var in the config tab.
        # For the source tab, we just need to display it.
        # So we can just set this textvariable from the config tab's auto_detect method.
        # For now, we can try to guess from the first path in EngineDirs.txt
        engine_dirs = self.source_manager.get_engine_dirs()
        if engine_dirs:
            try:
                p = Path(engine_dirs[0])
                if "Engine" in p.parts:
                    idx = p.parts.index("Engine")
                    self.engine_path_var.set(str(Path(*p.parts[:idx+1])))
                else:
                    # If it's a direct Source path, try to infer root
                    parts = p.parts
                    if 'Source' in parts:
                        source_idx = parts.index('Source')
                        if source_idx > 0:
                            self.engine_path_var.set(str(Path(*parts[:source_idx])))
            except Exception:
                self.engine_path_var.set("Engine path could not be inferred.")
        else:
            self.engine_path_var.set("No engine path configured.")
        
    def create_layout(self):
        # Header
        Theme.create_header(self.root, "UE5 Source Query", "Management Dashboard")
        
        # Main container
        container = tk.Frame(self.root, bg=Theme.BG_LIGHT)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Tabs
        self.notebook = ttk.Notebook(container)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 1. Query Tab (Main Interface)
        self.tab_query = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_query, text="Query")
        self.build_query_tab()

        # 2. Configuration Tab
        self.tab_config = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_config, text="Configuration")
        self.build_config_tab()

        # 3. Source Manager Tab
        self.tab_sources = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_sources, text="Source Manager")
        self.build_sources_tab()
        
        # 4. Diagnostics Tab (Health Check)
        self.tab_diagnostics = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_diagnostics, text="Diagnostics")
        self.build_diagnostics_tab()
        
        # 5. Maintenance Tab
        self.tab_maintenance = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_maintenance, text="Maintenance")
        self.build_maintenance_tab()

    def build_query_tab(self):
        frame = ttk.Frame(self.tab_query, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Input Section
        input_frame = ttk.LabelFrame(frame, text=" Ask the Engine ", padding=15)
        input_frame.pack(fill=tk.X, pady=(0, 15))

        # Search Bar
        search_frame = ttk.Frame(input_frame)
        search_frame.pack(fill=tk.X)
        
        self.query_entry = ttk.Entry(search_frame, font=("Arial", 11))
        self.query_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.query_entry.bind("<Return>", lambda e: self.perform_query()) # Enter key support

        btn_search = ttk.Button(search_frame, text="Search", command=self.perform_query, style="Accent.TButton")
        btn_search.pack(side=tk.LEFT)

        # Options
        options_frame = ttk.Frame(input_frame)
        options_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(options_frame, text="Scope:", font=Theme.FONT_BOLD).pack(side=tk.LEFT, padx=(0, 5))
        
        scopes = [("Engine API", "engine"), ("Project Code", "project"), ("All", "all")]
        for label, val in scopes:
            ttk.Radiobutton(options_frame, text=label, variable=self.query_scope_var, value=val).pack(side=tk.LEFT, padx=10)

        # Results Section
        results_frame = ttk.LabelFrame(frame, text=" Results ", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True)

        # Text area with tags for formatting
        self.results_text = scrolledtext.ScrolledText(results_frame, font=("Consolas", 10), state=tk.DISABLED, wrap=tk.WORD)
        self.results_text.pack(fill=tk.BOTH, expand=True)
        
        # Config tags
        self.results_text.tag_config("header", font=("Arial", 11, "bold"), foreground=Theme.PRIMARY)
        self.results_text.tag_config("highlight", background="#e6f3ff", foreground="#000")
        self.results_text.tag_config("code", font=("Consolas", 9), background="#f5f5f5")
        self.results_text.tag_config("success", foreground=Theme.SUCCESS)
        self.results_text.tag_config("error", foreground=Theme.ERROR)

        self.log_query_result("Ready to search. Enter a query above.")

    def perform_query(self):
        query = self.query_entry.get().strip()
        if not query:
            return
            
        scope = self.query_scope_var.get()
        
        self.log_query_result("Thinking...", clear=True)
        self.query_entry.config(state=tk.DISABLED)
        
        def _run():
            try:
                # Run hybrid query
                results = hybrid_query(
                    question=query,
                    top_k=5,
                    scope=scope,
                    show_reasoning=False # We'll display it manually
                )
                
                self.root.after(0, lambda: self.display_query_results(results))
                
            except Exception as e:
                self.root.after(0, lambda err=str(e): self.log_query_result(f"Error: {err}", clear=True, tag="error"))
            finally:
                self.root.after(0, lambda: self.query_entry.config(state=tk.NORMAL))

        threading.Thread(target=_run, daemon=True).start()

    def display_query_results(self, results):
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)
        
        # 1. Intent/Reasoning
        intent = results.get('intent', {})
        self.results_text.insert(tk.END, f"Query Type: {intent.get('type', 'Unknown')}\n", "header")
        if intent.get('entity_name'):
            self.results_text.insert(tk.END, f"Target Entity: {intent.get('entity_name')}\n")
        
        reasoning = intent.get('reasoning')
        if reasoning:
            self.results_text.insert(tk.END, f"\nReasoning: {reasoning}\n", "code")
            
        self.results_text.insert(tk.END, "-" * 60 + "\n\n")

        # 2. Definitions
        defs = results.get('definition_results', [])
        if defs:
            self.results_text.insert(tk.END, f"Found {len(defs)} Definitions:\n", "header")
            for i, item in enumerate(defs, 1):
                self.results_text.insert(tk.END, f"[{i}] {item['entity_type']} {item['entity_name']}\n", "highlight")
                self.results_text.insert(tk.END, f"    File: {item['file_path']}:{item['line_start']}\n")
                # Show snippet if available (first few lines)
                defn = item.get('definition', '')
                if defn:
                    lines = defn.split('\n')[:5]
                    snippet = '\n'.join(lines)
                    self.results_text.insert(tk.END, f"{snippet}\n...\n\n", "code")

        # 3. Semantic Results
        sems = results.get('semantic_results', [])
        if sems:
            self.results_text.insert(tk.END, f"Found {len(sems)} Semantic Matches:\n", "header")
            for i, item in enumerate(sems, 1):
                path = Path(item['path']).name
                score = item.get('score', 0)
                self.results_text.insert(tk.END, f"[{i}] {path} (Score: {score:.2f})\n", "highlight")
                self.results_text.insert(tk.END, f"    Full Path: {item['path']}\n\n")

        if not defs and not sems:
            self.results_text.insert(tk.END, "No results found.", "error")

        self.results_text.config(state=tk.DISABLED)

    def log_query_result(self, message, clear=False, tag=None):
        self.results_text.config(state=tk.NORMAL)
        if clear:
            self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, message + "\n", tag)
        self.results_text.config(state=tk.DISABLED)

    def build_sources_tab(self):
        # Use PanedWindow for responsive vertical split
        paned = ttk.PanedWindow(self.tab_sources, orient=tk.VERTICAL)
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

    def build_diagnostics_tab(self):
        frame = ttk.Frame(self.tab_diagnostics, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Action Bar
        action_frame = ttk.Frame(frame)
        action_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(action_frame, text="System Health Check", font=Theme.FONT_BOLD).pack(side=tk.LEFT)
        
        btn_run = ttk.Button(action_frame, text="▶ Run Diagnostics", command=self.run_diagnostics, style="Accent.TButton")
        btn_run.pack(side=tk.RIGHT)
        
        # Output Area
        self.diag_log = scrolledtext.ScrolledText(frame, font=Theme.FONT_MONO, state=tk.DISABLED)
        self.diag_log.pack(fill=tk.BOTH, expand=True)
        
        # Initial instruction
        self.log_diag("Ready to run diagnostics. Click 'Run Diagnostics' to begin.")

    def run_diagnostics(self):
        self.log_diag("Running health check...", clear=True)

        def _run():
            # First, check GPU
            try:
                self.root.after(0, lambda: self.log_diag("=== GPU Status ===", append=True))
                gpu_info = detect_nvidia_gpu()
                if gpu_info:
                    gpu_summary = get_gpu_summary()
                    self.root.after(0, lambda: self.log_diag(f"GPU: {gpu_info.name}", append=True))
                    self.root.after(0, lambda: self.log_diag(f"Compute Capability: {gpu_info.compute_capability_str} ({gpu_info.sm_version})", append=True))
                    self.root.after(0, lambda: self.log_diag(f"CUDA Required: {gpu_info.cuda_version_required}+", append=True))

                    if gpu_summary["cuda_installed"]:
                        self.root.after(0, lambda: self.log_diag(f"CUDA Installed: {gpu_summary['cuda_installed']}", append=True))
                        if gpu_summary["cuda_compatible"]:
                            self.root.after(0, lambda: self.log_diag("✓ CUDA version compatible for GPU acceleration", append=True))
                        else:
                            self.root.after(0, lambda: self.log_diag(f"✗ CUDA {gpu_info.cuda_version_required}+ required for full GPU support", append=True))
                    else:
                        self.root.after(0, lambda: self.log_diag("✗ CUDA not installed - GPU acceleration unavailable", append=True))
                else:
                    self.root.after(0, lambda: self.log_diag("No NVIDIA GPU detected - CPU mode only", append=True))

                self.root.after(0, lambda: self.log_diag("\n=== System Health Check ===", append=True))
            except Exception as e:
                self.root.after(0, lambda: self.log_diag(f"GPU check error: {e}\n", append=True))

            # Then run the standard health check
            script = self.script_dir / "tools" / "health-check.bat"
            try:
                process = subprocess.Popen(
                    [str(script), "--verbose"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=str(self.script_dir)
                )

                for line in process.stdout:
                    self.root.after(0, lambda l=line: self.log_diag(l.rstrip(), append=True))

                process.wait()

                if process.returncode == 0:
                    self.root.after(0, lambda: self.log_diag("\n[SUCCESS] System is healthy.", append=True))
                else:
                    self.root.after(0, lambda: self.log_diag("\n[WARNING] Issues detected.", append=True))

            except Exception as e:
                self.root.after(0, lambda err=str(e): self.log_diag(f"\nError running script: {err}", append=True))

        threading.Thread(target=_run, daemon=True).start()

    def log_diag(self, message, clear=False, append=False):
        self.diag_log.config(state=tk.NORMAL)
        if clear:
            self.diag_log.delete(1.0, tk.END)
        self.diag_log.insert(tk.END, message + ("\n" if not message.endswith("\n") else ""))
        self.diag_log.see(tk.END)
        self.diag_log.config(state=tk.DISABLED)

    def build_config_tab(self):
        frame = ttk.Frame(self.tab_config, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Instructions
        ttk.Label(frame, text="Configure your Anthropic API key, UE5 Engine paths, and models.", font=Theme.FONT_NORMAL).pack(anchor=tk.W, pady=(0, 15))

        # API Key Section
        api_frame = ttk.LabelFrame(frame, text=" Anthropic API Key ", padding=15)
        api_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(api_frame, text="Get your API key from: https://console.anthropic.com/settings/keys", font=Theme.FONT_NORMAL, foreground="#666").pack(anchor=tk.W, pady=(0, 8))
        
        api_entry_frame = ttk.Frame(api_frame)
        api_entry_frame.pack(fill=tk.X)

        ttk.Label(api_entry_frame, text="API Key:", font=Theme.FONT_BOLD, width=10, anchor=tk.W).pack(side=tk.LEFT)
        self.api_key_entry = ttk.Entry(api_entry_frame, textvariable=self.api_key_var, show="*", width=50)
        self.api_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(api_frame, text="Show", command=self.toggle_api_visibility).pack(side=tk.LEFT)

        # Vector Storage
        ttk.Label(frame, text="Vector Storage Directory", font=Theme.FONT_BOLD).pack(anchor=tk.W, pady=(0,5))
        vec_frame = ttk.Frame(frame)
        vec_frame.pack(fill=tk.X, pady=(0, 20))
        ttk.Entry(vec_frame, textvariable=self.vector_store_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(vec_frame, text="Browse...", command=self.browse_vector_store).pack(side=tk.LEFT)
        
        # UE5 Path Section
        path_frame = ttk.LabelFrame(frame, text=" UE5 Engine Path ", padding=15)
        path_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(path_frame, text="This is auto-detected. Only change if incorrect.", font=Theme.FONT_NORMAL, foreground="#666").pack(anchor=tk.W, pady=(0, 8))
        
        path_entry_frame = ttk.Frame(path_frame)
        path_entry_frame.pack(fill=tk.X)

        ttk.Label(path_entry_frame, text="Engine Path:", font=Theme.FONT_BOLD, width=12, anchor=tk.W).pack(side=tk.LEFT)
        self.engine_path_entry = ttk.Entry(path_entry_frame, textvariable=self.engine_path_var, width=50)
        self.engine_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(path_entry_frame, text="Browse...", command=self.browse_engine_path).pack(side=tk.LEFT)
        ttk.Button(path_entry_frame, text="Auto-Detect", command=self.auto_detect_path).pack(side=tk.LEFT)

        # Model Selection Section
        model_frame = ttk.LabelFrame(frame, text=" Model Settings ", padding=15)
        model_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(model_frame, text="Embedding Model:", font=Theme.FONT_BOLD).pack(anchor=tk.W, pady=5)
        embed_combo = ttk.Combobox(model_frame, textvariable=self.embed_model_var, state='readonly')
        embed_combo['values'] = ('microsoft/unixcoder-base', 'sentence-transformers/all-MiniLM-L6-v2')
        embed_combo.pack(fill=tk.X)

        ttk.Label(model_frame, text="Claude API Model:", font=Theme.FONT_BOLD).pack(anchor=tk.W, pady=5)
        api_model_combo = ttk.Combobox(model_frame, textvariable=self.api_model_var, state='readonly')
        api_model_combo['values'] = ('claude-3-haiku-20240307', 'claude-3-5-sonnet-20241022', 'claude-3-opus-20240229')
        api_model_combo.pack(fill=tk.X)

        # Save Button
        ttk.Button(frame, text="💾 Save Configuration", command=self.save_configuration, style='Accent.TButton').pack(pady=20)
        
        # Log for config operations
        config_log_frame = ttk.LabelFrame(frame, text=" Configuration Log ", padding=5)
        config_log_frame.pack(fill=tk.BOTH, expand=True)
        self.config_log_text = scrolledtext.ScrolledText(config_log_frame, font=Theme.FONT_MONO, height=5)
        self.config_log_text.pack(fill=tk.BOTH, expand=True)

        self.load_current_engine_path() # Load engine path initially

    def log_config(self, message, clear=False, append=False):
        self.config_log_text.config(state=tk.NORMAL)
        if clear:
            self.config_log_text.delete(1.0, tk.END)
        self.config_log_text.insert(tk.END, message + ("\n" if not message.endswith("\n") else ""))
        self.config_log_text.see(tk.END)
        self.config_log_text.config(state=tk.DISABLED)

    def load_current_engine_path(self):
        engine_dirs = self.source_manager.get_engine_dirs()
        if engine_dirs:
            # Try to extract the root from EngineDirs.txt
            try:
                p = Path(engine_dirs[0])
                if "Engine" in p.parts:
                    idx = p.parts.index("Engine")
                    self.engine_path_var.set(str(Path(*p.parts[:idx+1])))
                else:
                    self.engine_path_var.set(engine_dirs[0].split('Source')[0].rstrip('\\/')) # Best guess
            except Exception as e:
                self.engine_path_var.set("Error loading path: " + str(e))
        else:
            self.engine_path_var.set("Not detected. Run auto-detect.")

    def save_configuration(self):
        config_dict = {
            'ANTHROPIC_API_KEY': self.api_key_var.get(),
            'VECTOR_OUTPUT_DIR': self.vector_store_var.get(),
            'UE_ENGINE_ROOT': self.engine_path_var.get(),
            'EMBED_MODEL': self.embed_model_var.get(),
            'ANTHROPIC_MODEL': self.api_model_var.get(),
        }

        # Validate API key
        if not config_dict['ANTHROPIC_API_KEY'] or config_dict['ANTHROPIC_API_KEY'] == "your_api_key_here":
            messagebox.showerror("Error", "Please enter a valid Anthropic API key")
            return
        if len(config_dict['ANTHROPIC_API_KEY']) < 20: # Basic check
            messagebox.showerror("Error", "API key seems too short. Please check it.")
            return

        self.config_manager.save(config_dict)
        self.log_config("Configuration saved successfully!", clear=True)
        
        # Note: We do NOT automatically regenerate EngineDirs.txt here anymore.
        # Engine source paths are managed in the 'Source Manager' tab.
        # This prevents overwriting user customizations to the engine source list.

        messagebox.showinfo("Success", "Configuration saved!")

    def browse_vector_store(self):
        d = filedialog.askdirectory(initialdir=self.vector_store_var.get())
        if d: self.vector_store_var.set(d)

    def browse_engine_path(self):
        directory = filedialog.askdirectory(
            title="Select UE5 Engine Directory",
            initialdir=self.engine_path_var.get() or "C:/Program Files/Epic Games"
        )
        if directory:
            path = Path(directory)
            if path.name == "Engine":
                self.engine_path_var.set(str(path))
            elif (path / "Engine").exists():
                self.engine_path_var.set(str(path / "Engine"))
            else:
                self.engine_path_var.set(directory)

    def auto_detect_path(self):
        self.log_config("Detecting UE5 installations...", clear=True)
        self.engine_path_entry.config(state=tk.DISABLED) # Disable input while detecting
        
        def detect():
            try:
                installations = get_available_engines(self.script_dir)

                if not installations:
                    self.root.after(0, lambda: self.log_config("! No UE5 installation detected", append=True))
                    self.root.after(0, lambda: messagebox.showwarning(
                        "Not Found",
                        "Could not auto-detect UE5. Please browse manually."
                    ))
                    return

                if len(installations) == 1:
                    path = installations[0]['engine_root']
                    version = installations[0]['version']
                    self.root.after(0, lambda: self.engine_path_var.set(path))
                    self.root.after(0, lambda: self.log_config(f"✓ Detected {version}: {path}", append=True))
                else:
                    self.root.after(0, lambda: self.show_selection_dialog(installations))

            except Exception as e:
                self.root.after(0, lambda err=str(e): self.log_config(f"✗ Detection failed: {err}", append=True))
                self.root.after(0, lambda err=str(e): messagebox.showerror("Error", f"Auto-detection failed:\n{err}"))
            finally:
                self.root.after(0, lambda: self.engine_path_entry.config(state=tk.NORMAL))


        threading.Thread(target=detect, daemon=True).start()

    def show_selection_dialog(self, installations):
        dialog = tk.Toplevel(self.root)
        dialog.title("Select UE5 Version")
        dialog.geometry("500x300")
        dialog.transient(self.root)
        dialog.grab_set()

        self.root.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 500) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 300) // 2
        dialog.geometry(f"+{x}+{y}")

        ttk.Label(dialog, text="Multiple UE5 versions found.\nPlease select one:", font=Theme.FONT_BOLD).pack(pady=10)

        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set, font=Theme.FONT_NORMAL)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)

        for install in installations:
            listbox.insert(tk.END, f"{install['version']} - {install['engine_root']}")

        def on_select():
            selection = listbox.curselection()
            if selection:
                index = selection[0]
                selected = installations[index]
                self.engine_path_var.set(selected['engine_root'])
                self.log_config(f"✓ Selected {selected['version']}: {selected['engine_root']}", append=True)
                dialog.destroy()

        ttk.Button(dialog, text="Select", command=on_select, style="Accent.TButton").pack(pady=15)
        
    def toggle_api_visibility(self):
        if self.api_key_entry['show'] == '*':
            self.api_key_entry.config(show='')
        else:
            self.api_key_entry.config(show='*')

    def build_maintenance_tab(self):
        frame = ttk.Frame(self.tab_maintenance, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Status Section
        status_frame = ttk.LabelFrame(frame, text=" System Status ", padding=15)
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.lbl_index_status = ttk.Label(status_frame, text="Index Status: Unknown", font=Theme.FONT_BOLD)
        self.lbl_index_status.pack(side=tk.LEFT)
        
        ttk.Button(status_frame, text="Refresh Status", command=self.check_status).pack(side=tk.RIGHT)

        # Actions Section
        action_frame = ttk.LabelFrame(frame, text=" Maintenance Actions ", padding=15)
        action_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Button(action_frame, text="Rebuild Index", command=self.rebuild_index, style="Accent.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(action_frame, text="Update Tool (Git Pull)", command=self.update_tool).pack(side=tk.LEFT)

        # Log Section
        log_frame = ttk.LabelFrame(frame, text=" Operation Log ", padding=15)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.maint_log = scrolledtext.ScrolledText(log_frame, font=Theme.FONT_MONO, height=10)
        self.maint_log.pack(fill=tk.BOTH, expand=True)
        
        # Initial check
        self.check_status()

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

    def rebuild_index(self):
        if not messagebox.askyesno("Confirm", "Rebuild vector index? This may take 5-15 minutes."):
            return
        
        self.log_maint("Starting index rebuild...", clear=True)
        
        def _run():
            try:
                script = self.script_dir / "tools" / "rebuild-index.bat"
                process = subprocess.Popen(
                    [str(script), "--verbose", "--force"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=str(self.script_dir)
                )
                for line in process.stdout:
                    self.root.after(0, lambda l=line: self.log_maint(l.rstrip(), append=True))
                
                process.wait()
                self.root.after(0, self.check_status)
            except Exception as e:
                 self.root.after(0, lambda err=str(e): self.log_maint(f"\n[ERROR] {err}", append=True))

        threading.Thread(target=_run, daemon=True).start()

    def update_tool(self):
        if not messagebox.askyesno("Confirm", "Update tool from repository?"):
            return
            
        self.log_maint("Updating tool...", clear=True)
        
        def _run():
            try:
                script = self.script_dir / "tools" / "update.bat"
                process = subprocess.Popen(
                    [str(script)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=str(self.script_dir)
                )
                for line in process.stdout:
                    self.root.after(0, lambda l=line: self.log_maint(l.rstrip(), append=True))
                    
                process.wait()
                self.root.after(0, lambda: self.log_maint("\n[DONE] Update complete.", append=True))
            except Exception as e:
                 self.root.after(0, lambda err=str(e): self.log_maint(f"\n[ERROR] {err}", append=True))

        threading.Thread(target=_run, daemon=True).start()

    def log_maint(self, message, clear=False, append=False):
        self.maint_log.config(state=tk.NORMAL)
        if clear:
            self.maint_log.delete(1.0, tk.END)
        self.maint_log.insert(tk.END, message + ("\n" if not message.endswith("\n") else ""))
        self.maint_log.see(tk.END)
        self.maint_log.config(state=tk.DISABLED)

def main():
    root = tk.Tk()
    app = UnifiedDashboard(root)
    root.mainloop()

if __name__ == "__main__":
    main()