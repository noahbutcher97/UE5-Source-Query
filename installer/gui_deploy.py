"""
UE5 Source Query Tool - Deployment Wizard (Unified Style)
The \"Install-Time\" interface. Sets up the environment and config before the Dashboard can run.
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

# Add src to path to import utils
# This assumes installer/ is sibling to src/
SCRIPT_DIR = Path(__file__).parent.parent
sys.path.append(str(SCRIPT_DIR))

from src.utils.gui_theme import Theme
from src.utils.config_manager import ConfigManager
from src.utils.source_manager import SourceManager
from src.utils.engine_helper import (
    get_available_engines, resolve_uproject_source, get_smart_engine_path,
    find_uproject_in_directory, get_engine_version_from_uproject, detect_engine_from_vector_store
)
from src.utils.gpu_helper import detect_nvidia_gpu, get_gpu_summary, get_gpu_requirements_text
from src.utils.cuda_installer import install_cuda_with_progress, create_gpu_requirements_file
from src.utils import gui_helpers

class DeploymentWizard:
    def __init__(self, root):
        self.root = root
        self.root.title("UE5 Source Query - Setup & Install")
        self.root.geometry("900x700")
        
        Theme.apply(self.root)
        self.source_dir = SCRIPT_DIR
        
        # State
        self.target_dir = tk.StringVar(value=str(Path.home() / "Documents" / "UE5-Source-Query"))
        self.gpu_support = tk.BooleanVar(value=False)
        self.build_index = tk.BooleanVar(value=True)
        self.create_shortcut = tk.BooleanVar(value=True)
        self.update_existing = tk.BooleanVar(value=False)
        self.gpu_info = None  # Will be populated after GPU detection
        
        # Config State
        self.api_key = tk.StringVar(value=os.environ.get("ANTHROPIC_API_KEY", ""))
        self.engine_path = tk.StringVar()
        self.project_path = tk.StringVar()
        self.project_dirs = [] # List of project directories to be added
        self.engine_dirs = [] # List of engine directories (from template)
        self.vector_store_path = tk.StringVar() # Default set in build_config_tab logic or trace
        
        self.embed_model = tk.StringVar(value='microsoft/unixcoder-base')
        self.api_model = tk.StringVar(value='claude-3-haiku-20240307')
        self.embed_batch_size = tk.StringVar(value='16')

        self.current_process = None
        self.is_running = False
        self.cancelled = False

        self.log_queue = queue.Queue()
        self.root.after(100, self.process_log_queue)
        
        self.load_default_engine_dirs()
        self.create_layout()
        
        # Auto-check for existing install on startup and when path changes
        self.target_dir.trace_add("write", self.check_existing_install)
        # Auto-update engine list when engine path changes
        self.engine_path.trace_add("write", lambda *args: self.refresh_engine_list())
        
        self.check_existing_install() 

    def get_tool_version(self):
        """Get version from src/__init__.py"""
        try:
            init_file = self.source_dir / "src" / "__init__.py"
            if init_file.exists():
                content = init_file.read_text()
                import re
                match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    return match.group(1)
        except:
            pass
        return "2.0.0"  # Fallback version

    def load_default_engine_dirs(self):
        template_path = self.source_dir / "src" / "indexing" / "EngineDirs.template.txt"
        if template_path.exists():
            with open(template_path, 'r') as f:
                self.engine_dirs = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        else:
            self.engine_dirs = []

    def create_layout(self):
        Theme.create_header(self.root, "UE5 Source Query", "Setup & Deployment Wizard")
        
        container = tk.Frame(self.root, bg=Theme.BG_LIGHT)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.notebook = ttk.Notebook(container)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Deployment
        self.tab_install = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_install, text="Deployment")
        self.build_install_tab()
        
        # Tab 2: Configuration
        self.tab_config = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_config, text="Configuration")
        self.build_config_tab()
        
        # Tab 3: Source Manager
        self.tab_sources = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_sources, text="Source Manager")
        self.build_sources_tab()
        
        # Tab 4: Diagnostics
        self.tab_diag = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_diag, text="Diagnostics")
        self.build_diagnostics_tab()
        
        # Tab 5: Install
        self.tab_execute = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_execute, text="Install")
        self.build_execute_tab()

    def build_install_tab(self):
        frame = ttk.Frame(self.tab_install, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Target Directory
        ttk.Label(frame, text="Where should the tool be installed?", font=Theme.FONT_BOLD).pack(anchor=tk.W, pady=(0,5))
        
        dir_frame = ttk.Frame(frame)
        dir_frame.pack(fill=tk.X, pady=(0, 20))
        ttk.Entry(dir_frame, textvariable=self.target_dir).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(dir_frame, text="Browse...", command=self.browse_directory).pack(side=tk.LEFT)
        
        # Status Indicator
        self.lbl_install_status = ttk.Label(frame, text="Status: Checking...", font=Theme.FONT_BOLD, foreground="#666")
        self.lbl_install_status.pack(anchor=tk.W, pady=(0, 20))

        # Options
        ttk.Label(frame, text="Options", font=Theme.FONT_BOLD).pack(anchor=tk.W, pady=(0,5))

        # GPU Support
        gpu_frame = ttk.Frame(frame)
        gpu_frame.pack(fill=tk.X, anchor=tk.W, pady=(0, 5))
        self.gpu_checkbox = ttk.Checkbutton(gpu_frame, text="Enable GPU Support (CUDA)", variable=self.gpu_support)
        self.gpu_checkbox.pack(side=tk.LEFT)
        ttk.Button(gpu_frame, text="Detect GPU", command=self.detect_gpu).pack(side=tk.LEFT, padx=(10, 0))

        # GPU Status Label
        self.lbl_gpu_status = ttk.Label(frame, text="GPU: Not detected yet", font=Theme.FONT_NORMAL, foreground="#666")
        self.lbl_gpu_status.pack(anchor=tk.W, pady=(0, 10))

        ttk.Checkbutton(frame, text="Build Index Immediately", variable=self.build_index).pack(anchor=tk.W)
        ttk.Checkbutton(frame, text="Create Desktop Shortcut", variable=self.create_shortcut).pack(anchor=tk.W)
        
        # Note about Diagnostics
        ttk.Label(frame, text="➡ Go to the 'Diagnostics' tab to verify system requirements.", 
                 font=Theme.FONT_NORMAL, foreground="#666").pack(anchor=tk.W, pady=(30,0))

    def build_config_tab(self):
        frame = ttk.Frame(self.tab_config, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Anthropic API Key", font=Theme.FONT_BOLD).pack(anchor=tk.W, pady=(0,5))
        ttk.Label(frame, text="Get your API key from: https://console.anthropic.com/settings/keys", font=Theme.FONT_NORMAL, foreground="#666").pack(anchor=tk.W, pady=(0, 8))

        api_frame = ttk.Frame(frame)
        api_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.api_key_entry = ttk.Entry(api_frame, textvariable=self.api_key, show="*")
        self.api_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(api_frame, text="Show", command=self.toggle_api_visibility).pack(side=tk.LEFT)
        
        # Vector Storage
        ttk.Label(frame, text="Vector Storage Directory", font=Theme.FONT_BOLD).pack(anchor=tk.W, pady=(0,5))
        vec_frame = ttk.Frame(frame)
        vec_frame.pack(fill=tk.X, pady=(0, 20))
        ttk.Entry(vec_frame, textvariable=self.vector_store_path).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(vec_frame, text="Browse...", command=self.browse_vector_store).pack(side=tk.LEFT)

        ttk.Label(frame, text="UE5 Engine Path", font=Theme.FONT_BOLD).pack(anchor=tk.W, pady=(0,5))
        
        path_frame = ttk.Frame(frame)
        path_frame.pack(fill=tk.X)
        self.path_entry = ttk.Entry(path_frame, textvariable=self.engine_path)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        ttk.Button(path_frame, text="Browse...", command=self.browse_engine_path).pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(path_frame, text="Auto-Detect", command=self.auto_detect_engine).pack(side=tk.LEFT)

        # Model Settings
        ttk.Label(frame, text="Model Settings", font=Theme.FONT_BOLD).pack(anchor=tk.W, pady=(20,5))
        
        ttk.Label(frame, text="Embedding Model:", font=Theme.FONT_NORMAL).pack(anchor=tk.W)
        embed_combo = ttk.Combobox(frame, textvariable=self.embed_model, state='readonly')
        embed_combo['values'] = ('microsoft/unixcoder-base', 'sentence-transformers/all-MiniLM-L6-v2')
        embed_combo.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(frame, text="Claude API Model:", font=Theme.FONT_NORMAL).pack(anchor=tk.W)
        api_model_combo = ttk.Combobox(frame, textvariable=self.api_model, state='readonly')
        api_model_combo['values'] = ('claude-3-haiku-20240307', 'claude-3-5-sonnet-20241022', 'claude-3-opus-20240229')
        api_model_combo.pack(fill=tk.X, pady=(0, 10))

        # GPU Optimization
        ttk.Label(frame, text="GPU Optimization", font=Theme.FONT_BOLD).pack(anchor=tk.W, pady=(20,5))

        ttk.Label(frame, text="Embedding Batch Size:", font=Theme.FONT_NORMAL).pack(anchor=tk.W)
        ttk.Label(frame, text="RTX 5090: Use 8-16 | RTX 4090/3090: Use 32+ | CPU: Use 1-4", font=Theme.FONT_NORMAL, foreground="#666").pack(anchor=tk.W, pady=(0, 5))
        batch_size_combo = ttk.Combobox(frame, textvariable=self.embed_batch_size, state='readonly')
        batch_size_combo['values'] = ('1', '2', '4', '8', '16', '32', '64')
        batch_size_combo.pack(fill=tk.X, pady=(0, 10))

        # Save Button
        ttk.Button(frame, text="💾 Save Configuration", command=self.save_config_preview, style='Accent.TButton').pack(pady=20)

        # Configuration Log
        config_log_frame = ttk.LabelFrame(frame, text=" Configuration Preview ", padding=5)
        config_log_frame.pack(fill=tk.BOTH, expand=True)
        self.config_preview_text = scrolledtext.ScrolledText(config_log_frame, font=Theme.FONT_MONO, height=5)
        self.config_preview_text.pack(fill=tk.BOTH, expand=True)
        self.config_preview_text.insert(tk.END, "Configuration will be saved during installation.\nYou can preview your settings here.")
        self.config_preview_text.config(state=tk.DISABLED)

    def save_config_preview(self):
        """Preview configuration that will be saved during installation"""
        self.config_preview_text.config(state=tk.NORMAL)
        self.config_preview_text.delete(1.0, tk.END)

        preview = f"""Configuration Preview:
═══════════════════════════════════════
API Key: {'*' * (len(self.api_key.get()) if self.api_key.get() else 0)} ({len(self.api_key.get())} chars)
Vector Store: {self.vector_store_path.get()}
Engine Path: {self.engine_path.get()}
Embedding Model: {self.embed_model.get()}
Claude Model: {self.api_model.get()}
Batch Size: {self.embed_batch_size.get()}

Target Directory: {self.target_dir.get()}
GPU Support: {'Enabled' if self.gpu_support.get() else 'Disabled'}
Build Index: {'Yes' if self.build_index.get() else 'No'}
Create Shortcut: {'Yes' if self.create_shortcut.get() else 'No'}
═══════════════════════════════════════

✓ Configuration is valid and will be saved during installation.
"""

        self.config_preview_text.insert(tk.END, preview)
        self.config_preview_text.config(state=tk.DISABLED)
        messagebox.showinfo("Configuration Preview", "Configuration looks good!\nIt will be saved when you run the installation.")

    def build_sources_tab(self):
        # Use PanedWindow for responsive vertical split
        paned = ttk.PanedWindow(self.tab_sources, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # --- Engine Section ---
        engine_frame = ttk.LabelFrame(paned, text=" Engine Source (Managed) ", padding=15)
        paned.add(engine_frame, weight=1)
        
        ttk.Label(engine_frame, text="Engine Root Directory:", font=Theme.FONT_BOLD).pack(anchor=tk.W)
        
        # Read-only entry to show path
        engine_entry = ttk.Entry(engine_frame, textvariable=self.engine_path, state='readonly')
        engine_entry.pack(fill=tk.X, pady=(5, 10))
        
        ttk.Label(engine_frame, text="Source Directories (Template):").pack(anchor=tk.W)
        
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
        ttk.Button(btn_frame, text="+ Add .uproject", command=self.add_uproject, style="Accent.TButton").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="- Remove Selected", command=self.remove_project_folder).pack(side=tk.LEFT)

        self.refresh_project_list()

    def refresh_engine_list(self):
        self.engine_listbox.delete(0, tk.END)
        engine_root = self.engine_path.get().strip()
        for d in self.engine_dirs:
            if engine_root and "{ENGINE_ROOT}" in d:
                resolved = d.replace("{ENGINE_ROOT}", engine_root)
                self.engine_listbox.insert(tk.END, resolved)
            else:
                self.engine_listbox.insert(tk.END, d)

    def add_engine_dir(self):
        engine_root = self.engine_path.get().strip()
        initial_dir = engine_root if engine_root and Path(engine_root).exists() else "/"
        
        d = filedialog.askdirectory(initialdir=initial_dir)
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
            
            if path_str not in self.engine_dirs:
                self.engine_dirs.append(path_str)
                self.refresh_engine_list()

    def remove_engine_dir(self):
        sel = self.engine_listbox.curselection()
        if sel:
            idx = sel[0]
            path = self.engine_listbox.get(idx)
            if messagebox.askyesno("Confirm", f"Remove '{path}' from list?"):
                self.engine_dirs.pop(idx)
                self.refresh_engine_list()

    def reset_engine_dirs(self):
        if messagebox.askyesno("Confirm", "Reset engine source list to defaults?"):
            self.load_default_engine_dirs()
            self.refresh_engine_list()

    def build_execute_tab(self):
        frame = ttk.Frame(self.tab_execute, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Configuration Preview Panel (NEW)
        self.preview_frame = ttk.LabelFrame(frame, text=" Configuration Preview ", padding=10)
        self.preview_frame.pack(fill=tk.X, pady=(0, 15))

        # Preview content - collapsible area
        self.preview_content = ttk.Frame(self.preview_frame)
        self.preview_content.pack(fill=tk.X)

        # Create preview labels
        self.preview_labels = {}
        preview_items = [
            ("target", "Target Directory:"),
            ("engine", "Engine Path:"),
            ("engine_dirs", "Source Directories:"),
            ("project_dirs", "Project Directories:"),
            ("gpu", "GPU Support:"),
        ]

        for i, (key, label) in enumerate(preview_items):
            ttk.Label(self.preview_content, text=label, font=Theme.FONT_BOLD).grid(
                row=i, column=0, sticky=tk.W, padx=(0, 10), pady=2)
            self.preview_labels[key] = ttk.Label(
                self.preview_content, text="Not configured", font=Theme.FONT_NORMAL, foreground="gray")
            self.preview_labels[key].grid(row=i, column=1, sticky=tk.W, pady=2)

        # Refresh button
        ttk.Button(self.preview_frame, text="🔄 Refresh Preview",
                   command=self.update_config_preview).pack(pady=(10, 0))

        # Action buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=(0, 20))

        self.btn_install = ttk.Button(btn_frame, text="▶ Start Installation", command=self.start_install, style="Accent.TButton")
        self.btn_install.pack(side=tk.LEFT, padx=5)

        self.btn_cancel = ttk.Button(btn_frame, text="Close", command=self.cancel_or_close)
        self.btn_cancel.pack(side=tk.LEFT, padx=5)

        self.progress = ttk.Progressbar(frame, mode='determinate')
        self.progress.pack(fill=tk.X, pady=(0, 10))

        self.log_text = scrolledtext.ScrolledText(frame, font=Theme.FONT_MONO, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Initial preview update
        self.root.after(500, self.update_config_preview)

    def update_config_preview(self):
        """Update the configuration preview panel with current settings."""
        # Target directory
        target = self.target_dir.get()
        if target:
            self.preview_labels["target"].config(text=target, foreground=Theme.SUCCESS)
        else:
            self.preview_labels["target"].config(text="Not set", foreground=Theme.ERROR)

        # Engine path
        engine = self.engine_path.get()
        if engine:
            if Path(engine).exists():
                # Extract version from path
                import re
                match = re.search(r'UE[_-]?(\d+\.\d+)', engine)
                version = f"UE {match.group(1)}" if match else "Unknown version"
                self.preview_labels["engine"].config(
                    text=f"{version} - {engine[:50]}...",
                    foreground=Theme.SUCCESS)
            else:
                self.preview_labels["engine"].config(
                    text=f"⚠ Path not found: {engine[:40]}...",
                    foreground=Theme.ERROR)
        else:
            self.preview_labels["engine"].config(text="Not configured", foreground=Theme.ERROR)

        # Source directories count
        engine_count = len(self.engine_dirs)
        if engine_count > 0:
            self.preview_labels["engine_dirs"].config(
                text=f"{engine_count} directories configured",
                foreground=Theme.SUCCESS)
        else:
            self.preview_labels["engine_dirs"].config(
                text="No source directories",
                foreground="#FFC107")

        # Project directories
        project_count = len(self.project_dirs)
        single_project = self.project_path.get()
        total_projects = project_count + (1 if single_project else 0)

        if total_projects > 0:
            self.preview_labels["project_dirs"].config(
                text=f"{total_projects} project(s) configured",
                foreground=Theme.SUCCESS)
        else:
            self.preview_labels["project_dirs"].config(
                text="No projects (optional)",
                foreground="gray")

        # GPU support
        if self.gpu_support.get():
            gpu_name = self.gpu_info.get('gpu_name', 'Unknown') if self.gpu_info else 'Detecting...'
            self.preview_labels["gpu"].config(
                text=f"✓ Enabled ({gpu_name})",
                foreground=Theme.SUCCESS)
        else:
            self.preview_labels["gpu"].config(
                text="Disabled (CPU only)",
                foreground="gray")

    def toggle_api_visibility(self):
        if self.api_key_entry['show'] == '*':
            self.api_key_entry.config(show='')
        else:
            self.api_key_entry.config(show='*')

    def browse_vector_store(self):
        d = filedialog.askdirectory(initialdir=self.vector_store_path.get())
        if d: self.vector_store_path.set(d)

    def detect_gpu(self):
        """Detect NVIDIA GPU and display information"""
        self.lbl_gpu_status.config(text="Detecting GPU...", foreground="#666")
        self.root.update()

        gpu_info = detect_nvidia_gpu()

        if gpu_info:
            self.gpu_info = get_gpu_summary()
            status_text = f"GPU: {gpu_info.name} ({gpu_info.sm_version}, CUDA {gpu_info.cuda_version_required}+ required)"
            self.lbl_gpu_status.config(text=status_text, foreground=Theme.SUCCESS)
            self.gpu_support.set(True)  # Auto-enable if GPU found
            messagebox.showinfo("GPU Detected", get_gpu_requirements_text())
        else:
            self.gpu_info = None
            self.lbl_gpu_status.config(text="GPU: No NVIDIA GPU detected", foreground=Theme.ERROR)
            self.gpu_support.set(False)
            messagebox.showwarning("No GPU", "No NVIDIA GPU detected. GPU acceleration will not be available.")

    def browse_engine_path(self):
        directory = filedialog.askdirectory(
            title="Select UE5 Engine Directory",
            initialdir=self.engine_path.get() or "C:/Program Files/Epic Games"
        )
        if directory:
            path = Path(directory)
            if path.name == "Engine":
                self.engine_path.set(str(path))
            elif (path / "Engine").exists():
                self.engine_path.set(str(path / "Engine"))
            else:
                self.engine_path.set(directory)

    def browse_directory(self):
        d = filedialog.askdirectory(initialdir=self.target_dir.get())
        if d: self.target_dir.set(d)

    def check_existing_install(self, *args):
        target = Path(self.target_dir.get())
        
        # Set default vector store path based on target
        default_vec_path = target / "data"
        
        if not target.exists():
            self.lbl_install_status.config(text="Status: New Installation", foreground=Theme.SUCCESS)
            self.update_existing.set(False)
            self.btn_install.config(text="▶ Start Installation")
            self.vector_store_path.set(str(default_vec_path))
            return

        # Check for signs of installation
        has_venv = (target / ".venv").exists()
        has_config = (target / "config" / ".env").exists()
        version_file = target / "VERSION.txt"

        if has_venv and has_config:
            # Check version if available
            installed_version = "unknown"
            if version_file.exists():
                try:
                    installed_version = version_file.read_text().strip()
                except:
                    pass

            current_version = self.get_tool_version()
            if installed_version != "unknown" and installed_version != current_version:
                self.lbl_install_status.config(
                    text=f"Status: Update Available (v{installed_version} → v{current_version})",
                    foreground=Theme.WARNING
                )
            else:
                self.lbl_install_status.config(
                    text="Status: Existing Installation Detected (Will Update)",
                    foreground=Theme.WARNING
                )

            self.update_existing.set(True)
            self.btn_install.config(text="▶ Start Update")
            # Try to load existing config
            try:
                cm = ConfigManager(target) # ConfigManager expects root containing config/.env
                if cm.get("ANTHROPIC_API_KEY"):
                    self.api_key.set(cm.get("ANTHROPIC_API_KEY"))
                
                # Load vector dir
                vec_dir = cm.get("VECTOR_OUTPUT_DIR")
                if vec_dir:
                    self.vector_store_path.set(vec_dir)
                else:
                    self.vector_store_path.set(str(default_vec_path))
                    
                # Load models
                if cm.get("EMBED_MODEL"):
                    self.embed_model.set(cm.get("EMBED_MODEL"))
                if cm.get("ANTHROPIC_MODEL"):
                    self.api_model.set(cm.get("ANTHROPIC_MODEL"))
                if cm.get("EMBED_BATCH_SIZE"):
                    self.embed_batch_size.set(cm.get("EMBED_BATCH_SIZE"))
            except:
                self.vector_store_path.set(str(default_vec_path))
        else:
            self.lbl_install_status.config(text="Status: Directory Exists (Clean Install)", foreground="#666")
            self.update_existing.set(False)
            self.btn_install.config(text="▶ Start Installation")
            self.vector_store_path.set(str(default_vec_path))

    def browse_project(self):
        f = filedialog.askopenfilename(filetypes=[("Unreal Project", "*.uproject")])
        if f: self.project_path.set(f)

    def build_diagnostics_tab(self):
        frame = ttk.Frame(self.tab_diag, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        self.diag_frame = frame  # Store reference for dynamic layout

        # Version Mismatch Warning Banner (initially hidden)
        self.version_warning_frame = tk.Frame(frame, bg="#FFF3CD", relief=tk.SOLID, bd=1)
        # Don't pack yet - will be shown dynamically if mismatch detected

        self.version_warning_text = tk.Label(
            self.version_warning_frame,
            text="",
            font=("Arial", 9),
            bg="#FFF3CD",
            fg="#856404",
            wraplength=700,
            justify=tk.LEFT
        )
        self.version_warning_text.pack(padx=10, pady=8)

        # Action Bar
        self.diag_action_frame = ttk.Frame(frame)
        self.diag_action_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(self.diag_action_frame, text="Pre-flight System Check", font=Theme.FONT_BOLD).pack(side=tk.LEFT)

        btn_run = ttk.Button(self.diag_action_frame, text="▶ Run Checks", command=self.run_diagnostics, style="Accent.TButton")
        btn_run.pack(side=tk.RIGHT)

        # Output Area
        self.diag_log = scrolledtext.ScrolledText(frame, font=Theme.FONT_MONO, state=tk.DISABLED)
        self.diag_log.pack(fill=tk.BOTH, expand=True)

        self.log_diag("Ready to check system requirements.\nClick 'Run Checks' to begin.")

    def log_diag(self, message, clear=False, append=False):
        self.diag_log.config(state=tk.NORMAL)
        if clear:
            self.diag_log.delete(1.0, tk.END)
        self.diag_log.insert(tk.END, message + ("\n" if not message.endswith("\n") else ""))
        self.diag_log.see(tk.END)
        self.diag_log.config(state=tk.DISABLED)

    def run_diagnostics(self):
        self.log_diag("Running pre-flight checks...", clear=True)

        # Hide version warning initially
        self.root.after(0, lambda: self.version_warning_frame.pack_forget())

        def _check():
            all_passed = True
            version_warnings = []

            # 1. Python Check
            try:
                ver = sys.version_info
                if ver >= (3, 8):
                    self.root.after(0, lambda: self.log_diag(f"[OK] Python {ver.major}.{ver.minor}.{ver.micro}", append=True))
                else:
                    self.root.after(0, lambda: self.log_diag(f"[FAIL] Python {ver.major}.{ver.minor} (Need 3.8+)", append=True))
                    all_passed = False
            except Exception as e:
                self.root.after(0, lambda: self.log_diag(f"[ERR] Python check failed: {e}", append=True))
                all_passed = False

            # 2. Pip Check
            try:
                res = subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True, text=True)
                if res.returncode == 0:
                    self.root.after(0, lambda: self.log_diag("[OK] Pip is available", append=True))
                else:
                    self.root.after(0, lambda: self.log_diag("[FAIL] Pip not found", append=True))
                    all_passed = False
            except:
                self.root.after(0, lambda: self.log_diag("[FAIL] Pip check failed", append=True))
                all_passed = False

            # 3. Disk Space
            try:
                target = Path(self.target_dir.get())
                drive = target.anchor
                total, used, free = shutil.disk_usage(drive)
                free_gb = free / (1024**3)
                if free_gb > 1.0:
                    self.root.after(0, lambda: self.log_diag(f"[OK] Disk Space: {free_gb:.1f} GB free", append=True))
                else:
                    self.root.after(0, lambda: self.log_diag(f"[WARN] Low Disk Space: {free_gb:.1f} GB", append=True))
            except:
                pass

            # 4. Write Permissions
            try:
                target = Path(self.target_dir.get())
                if not target.exists():
                    target.mkdir(parents=True, exist_ok=True)
                    temp_file = target / ".write_test"
                    temp_file.touch()
                    temp_file.unlink()
                    # Clean up if we created it new
                    if not any(target.iterdir()):
                        target.rmdir()
                else:
                    temp_file = target / ".write_test"
                    temp_file.touch()
                    temp_file.unlink()
                self.root.after(0, lambda: self.log_diag("[OK] Write permissions verified", append=True))
            except Exception as e:
                self.root.after(0, lambda: self.log_diag(f"[FAIL] No write permission: {e}", append=True))
                all_passed = False

            # 5. GPU Check (optional)
            try:
                gpu_info = detect_nvidia_gpu()
                if gpu_info:
                    gpu_summary = get_gpu_summary()
                    self.root.after(0, lambda: self.log_diag(f"[INFO] GPU: {gpu_info.name}", append=True))
                    self.root.after(0, lambda: self.log_diag(f"[INFO] Compute: {gpu_info.compute_capability_str} ({gpu_info.sm_version})", append=True))
                    self.root.after(0, lambda: self.log_diag(f"[INFO] CUDA Required: {gpu_info.cuda_version_required}+", append=True))

                    if gpu_summary["cuda_installed"]:
                        self.root.after(0, lambda: self.log_diag(f"[INFO] CUDA Installed: {gpu_summary['cuda_installed']}", append=True))
                        if gpu_summary["cuda_compatible"]:
                            self.root.after(0, lambda: self.log_diag("[OK] CUDA version compatible", append=True))
                        else:
                            self.root.after(0, lambda: self.log_diag("[WARN] CUDA version too old", append=True))
                    else:
                        self.root.after(0, lambda: self.log_diag("[INFO] CUDA not installed (optional for GPU)", append=True))
                else:
                    self.root.after(0, lambda: self.log_diag("[INFO] No NVIDIA GPU detected (optional)", append=True))
            except:
                pass

            # 6. Engine Version Mismatch Check (NEW)
            self.root.after(0, lambda: self.log_diag("\n--- Engine Version Validation ---", append=True))
            try:
                target_dir = Path(self.target_dir.get()) if self.target_dir.get() else None
                selected_engine = self.engine_path.get()

                # Extract version from selected engine path
                import re
                selected_version = None
                if selected_engine:
                    match = re.search(r'UE[_-]?(\d+\.\d+)', selected_engine)
                    if match:
                        selected_version = match.group(1)
                        self.root.after(0, lambda v=selected_version:
                            self.log_diag(f"[INFO] Selected Engine: UE {v}", append=True))

                # Check .uproject file version
                project_version = None
                if target_dir:
                    uproject = find_uproject_in_directory(target_dir)
                    if uproject:
                        project_version = get_engine_version_from_uproject(str(uproject))
                        if project_version:
                            self.root.after(0, lambda p=uproject.name, v=project_version:
                                self.log_diag(f"[INFO] Project: {p} requires UE {v}", append=True))

                # Check vector store version (if exists)
                vector_version = None
                if target_dir and (target_dir / "data" / "vector_meta.json").exists():
                    vector_engine = detect_engine_from_vector_store(target_dir)
                    if vector_engine:
                        vector_version = vector_engine.get('version', '')
                        # Extract just the version number
                        match = re.search(r'(\d+\.\d+)', vector_version)
                        if match:
                            vector_version = match.group(1)
                            self.root.after(0, lambda v=vector_version:
                                self.log_diag(f"[INFO] Existing Index: Built with UE {v}", append=True))

                # Compare versions and detect mismatches
                versions = {
                    'Selected Engine': selected_version,
                    'Project (.uproject)': project_version,
                    'Existing Index': vector_version
                }

                # Filter out None values
                present_versions = {k: v for k, v in versions.items() if v}

                if len(present_versions) >= 2:
                    # Check if all versions match
                    unique_versions = set(present_versions.values())
                    if len(unique_versions) > 1:
                        # Version mismatch detected!
                        mismatch_details = ", ".join([f"{k}: {v}" for k, v in present_versions.items()])
                        version_warnings.append(f"Version mismatch detected! {mismatch_details}")

                        self.root.after(0, lambda m=mismatch_details:
                            self.log_diag(f"[WARN] VERSION MISMATCH: {m}", append=True))

                        # Specific warnings
                        if selected_version and project_version and selected_version != project_version:
                            version_warnings.append(
                                f"Selected engine (UE {selected_version}) doesn't match project requirement (UE {project_version})")

                        if selected_version and vector_version and selected_version != vector_version:
                            version_warnings.append(
                                f"Selected engine (UE {selected_version}) differs from existing index (UE {vector_version}). "
                                "Consider rebuilding index after installation.")
                    else:
                        self.root.after(0, lambda: self.log_diag("[OK] All engine versions are consistent", append=True))
                elif len(present_versions) == 1:
                    self.root.after(0, lambda: self.log_diag("[INFO] Only one version source available, cannot cross-check", append=True))
                else:
                    self.root.after(0, lambda: self.log_diag("[INFO] No engine version information available", append=True))

            except Exception as e:
                self.root.after(0, lambda err=str(e): self.log_diag(f"[ERR] Version check failed: {err}", append=True))

            # Show version warning banner if mismatches detected
            if version_warnings:
                warning_text = "⚠️ " + " | ".join(version_warnings)
                self.root.after(0, lambda t=warning_text: self._show_version_warning(t))

            if all_passed:
                self.root.after(0, lambda: self.log_diag("\n[SUCCESS] All checks passed. Ready to install.", append=True))
            else:
                self.root.after(0, lambda: self.log_diag("\n[WARNING] Some checks failed. Installation may not work.", append=True))

        threading.Thread(target=_check, daemon=True).start()

    def _show_version_warning(self, warning_text):
        """Show the version mismatch warning banner."""
        self.version_warning_text.config(text=warning_text)
        # Pack after the action bar but before the log
        if not self.version_warning_frame.winfo_ismapped():
            self.version_warning_frame.pack(fill=tk.X, pady=(0, 10), after=self.diag_action_frame)

    def add_uproject(self):
        f = filedialog.askopenfilename(filetypes=[("Unreal Project", "*.uproject")])
        if f:
            source_dir = resolve_uproject_source(f)
            if source_dir:
                self.add_project_dir_to_list(source_dir)
            else:
                messagebox.showwarning("Warning", f"No 'Source' folder found for project: {f}")

    def add_project_folder(self):
        d = filedialog.askdirectory()
        if d:
            self.add_project_dir_to_list(d)

    def add_project_dir_to_list(self, path):
        if path not in self.project_dirs:
            self.project_dirs.append(path)
            self.project_listbox.insert(tk.END, path)

    def remove_project_folder(self):
        sel = self.project_listbox.curselection()
        if sel:
            idx = sel[0]
            path = self.project_listbox.get(idx)
            if messagebox.askyesno("Confirm", f"Remove '{path}' from list?"):
                self.project_listbox.delete(idx)
                self.project_dirs.pop(idx)

    def refresh_project_list(self):
        self.project_listbox.delete(0, tk.END)
        for p in self.project_dirs:
            self.project_listbox.insert(tk.END, p)

    def auto_detect_engine(self):
        """
        Priority-based engine detection:
        1. Vector store (if index exists) - ensures consistency
        2. .uproject file in target/deployment area - matches project
        3. Config file (if exists) - user's last choice
        4. Auto-detection by health score - best available

        This mirrors the Dashboard's get_smart_engine_path() logic.
        """
        self.log("Detecting UE5 installations (priority-based)...")
        self.path_entry.config(state=tk.DISABLED)

        def detect():
            try:
                target_dir = Path(self.target_dir.get()) if self.target_dir.get() else None

                # ═══════════════════════════════════════════════════════════════════
                # PRIORITY 1: Vector Store (if deployment has existing index)
                # ═══════════════════════════════════════════════════════════════════
                if target_dir and (target_dir / "data" / "vector_meta.json").exists():
                    self.root.after(0, lambda: self.log("  [1/4] Checking vector store..."))
                    vector_engine = detect_engine_from_vector_store(target_dir)
                    if vector_engine:
                        path = vector_engine.get('engine_root')
                        version = vector_engine.get('version', 'unknown')
                        if path and Path(path).exists():
                            self.root.after(0, lambda p=path, v=version:
                                self.log(f"✓ Found from vector store: {v}"))
                            self.root.after(0, lambda: self.log("  (Using indexed engine for consistency)"))
                            self.root.after(0, lambda p=path: self.engine_path.set(p))
                            return
                        else:
                            self.root.after(0, lambda: self.log("  Vector store points to missing path, continuing..."))
                else:
                    self.root.after(0, lambda: self.log("  [1/4] No vector store found"))

                # ═══════════════════════════════════════════════════════════════════
                # PRIORITY 2: .uproject file in deployment area
                # ═══════════════════════════════════════════════════════════════════
                self.root.after(0, lambda: self.log("  [2/4] Checking for .uproject..."))
                project_engine_version = None
                uproject = None

                if target_dir:
                    uproject = find_uproject_in_directory(target_dir)
                    if uproject:
                        project_engine_version = get_engine_version_from_uproject(str(uproject))
                        if project_engine_version:
                            self.root.after(0, lambda p=uproject.name, v=project_engine_version:
                                self.log(f"  Found project: {p} (requires UE {v})"))

                # ═══════════════════════════════════════════════════════════════════
                # PRIORITY 3: Config file (user's previous selection)
                # ═══════════════════════════════════════════════════════════════════
                self.root.after(0, lambda: self.log("  [3/4] Checking config file..."))
                config_engine = None
                config_file = target_dir / "config" / ".env" if target_dir else None

                if config_file and config_file.exists():
                    try:
                        import re
                        with open(config_file, 'r') as f:
                            for line in f:
                                if line.startswith('UE_ENGINE_ROOT='):
                                    engine_root = line.split('=', 1)[1].strip()
                                    if engine_root and Path(engine_root).exists():
                                        match = re.search(r'UE[_-]?(\d+\.\d+)', engine_root)
                                        if match:
                                            config_engine = {
                                                'path': engine_root,
                                                'version': f"UE_{match.group(1)}",
                                                'source': 'config'
                                            }
                                            self.root.after(0, lambda v=config_engine['version']:
                                                self.log(f"  Found in config: {v}"))
                                    break
                    except Exception:
                        pass

                # ═══════════════════════════════════════════════════════════════════
                # PRIORITY 4: Auto-detection with health scores
                # ═══════════════════════════════════════════════════════════════════
                self.root.after(0, lambda: self.log("  [4/4] Scanning system for UE5 installations..."))
                installations = get_available_engines(self.source_dir, use_cache=True)

                if not installations:
                    # No engines found anywhere
                    if config_engine:
                        # But we have a config entry - use it
                        self.root.after(0, lambda p=config_engine['path']: self.engine_path.set(p))
                        self.root.after(0, lambda v=config_engine['version']:
                            self.log(f"✓ Using config engine: {v}"))
                        return

                    self.root.after(0, lambda: self.log("! No UE5 installation detected"))
                    self.root.after(0, lambda: self.show_detection_help_dialog())
                    return

                # Log all found installations
                for inst in installations:
                    health_pct = int(inst.get('health_score', 0) * 100)
                    source = inst.get('source', 'unknown')
                    self.root.after(0, lambda v=inst['version'], s=source, h=health_pct:
                        self.log(f"  Found {v} ({s}) - Health: {h}%"))

                # ═══════════════════════════════════════════════════════════════════
                # DECISION LOGIC: Choose best engine
                # ═══════════════════════════════════════════════════════════════════

                # If we have a project version, prefer matching engine
                if project_engine_version:
                    for inst in installations:
                        if project_engine_version in inst.get('version', ''):
                            path = inst['engine_root']
                            version = inst['version']
                            health = int(inst.get('health_score', 0) * 100)
                            self.root.after(0, lambda p=path: self.engine_path.set(p))
                            self.root.after(0, lambda v=version, h=health:
                                self.log(f"✓ Selected {v} (matches project, health: {h}%)"))
                            return

                    # No matching version found - warn user
                    self.root.after(0, lambda v=project_engine_version:
                        self.log(f"⚠ No engine matching project version {v}"))

                # If we have a config engine and it's in the list with good health, prefer it
                if config_engine:
                    for inst in installations:
                        if inst['engine_root'] == config_engine['path']:
                            health = int(inst.get('health_score', 0) * 100)
                            if health >= 60:
                                self.root.after(0, lambda p=config_engine['path']: self.engine_path.set(p))
                                self.root.after(0, lambda v=config_engine['version'], h=health:
                                    self.log(f"✓ Using config engine: {v} (health: {h}%)"))
                                return

                # Sort by health score (descending)
                installations.sort(key=lambda x: x.get('health_score', 0), reverse=True)

                # Always show version selector so user can override auto-selection
                # The selector includes "Auto" as the default which picks the best match
                self.root.after(0, lambda pv=project_engine_version:
                    self.show_version_selector(installations, preferred_version=pv))

            except Exception as e:
                self.root.after(0, lambda err=str(e): self.log(f"✗ Detection failed: {err}"))
                self.root.after(0, lambda err=str(e): messagebox.showerror("Error", f"Auto-detection failed:\n{err}"))
            finally:
                self.root.after(0, lambda: self.path_entry.config(state=tk.NORMAL))

        threading.Thread(target=detect, daemon=True).start()

    def show_detection_help_dialog(self):
        """Phase 6: Guide user through manual setup when detection fails"""
        gui_helpers.show_engine_detection_help(self.root, self.browse_engine_path)

    def show_version_selector(self, installs, preferred_version=None):
        """
        Show version selector dialog with color-coded health scores.
        Enhanced to provide better visual feedback on engine quality.
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("Select UE5 Version")
        dialog.geometry("700x500")
        dialog.transient(self.root)
        dialog.grab_set()

        self.root.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 700) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 500) // 2
        dialog.geometry(f"+{x}+{y}")

        # Header with recommendation if available
        header_frame = ttk.Frame(dialog)
        header_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(header_frame, text="Select UE5 Installation",
                  font=Theme.FONT_BOLD).pack(anchor=tk.W)

        if preferred_version:
            rec_frame = tk.Frame(header_frame, bg="#d4edda", relief=tk.SOLID, bd=1)
            rec_frame.pack(fill=tk.X, pady=(5, 0))
            tk.Label(rec_frame, text=f"💡 Recommended: UE {preferred_version} (matches project)",
                     font=("Arial", 9), bg="#d4edda", fg="#155724").pack(padx=10, pady=5)

        # Legend for health scores
        legend_frame = ttk.LabelFrame(dialog, text=" Health Score Legend ", padding=5)
        legend_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

        legend_row = ttk.Frame(legend_frame)
        legend_row.pack(fill=tk.X)

        for color, label, range_text in [
            ("#28a745", "Excellent", "80-100%"),
            ("#ffc107", "Good", "60-79%"),
            ("#fd7e14", "Fair", "40-59%"),
            ("#dc3545", "Poor", "0-39%"),
        ]:
            item_frame = tk.Frame(legend_row, bg="white")
            item_frame.pack(side=tk.LEFT, padx=10)
            tk.Label(item_frame, text="●", fg=color, font=("Arial", 12), bg="white").pack(side=tk.LEFT)
            tk.Label(item_frame, text=f" {label} ({range_text})", font=("Arial", 9), bg="white").pack(side=tk.LEFT)

        # Main content - use Treeview for better display
        tree_frame = ttk.Frame(dialog)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        # Create Treeview with columns
        columns = ("version", "health", "source", "status")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")

        tree.heading("version", text="Version")
        tree.heading("health", text="Health")
        tree.heading("source", text="Source")
        tree.heading("status", text="Status")

        tree.column("version", width=100)
        tree.column("health", width=100)
        tree.column("source", width=120)
        tree.column("status", width=150)

        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add "Auto" as first option - selects best match automatically
        # Determine best auto-select choice
        best_install = installs[0]  # Already sorted by health
        if preferred_version:
            # Prefer version matching project if available
            for inst in installs:
                if preferred_version in inst.get('version', ''):
                    best_install = inst
                    break

        best_health = int(best_install.get('health_score', 0) * 100)
        auto_desc = f"Best: {best_install.get('version', 'unknown')} ({best_health}%)"
        tree.insert("", tk.END, iid="auto", values=(
            "Auto (Recommended)",
            auto_desc,
            "Smart Detection",
            "● Auto-select"
        ))

        # Add individual installations
        for i, inst in enumerate(installs):
            version = inst.get('version', 'unknown')
            health = int(inst.get('health_score', 0) * 100)
            source = inst.get('source', 'unknown')
            path = inst.get('engine_root', '')

            # Determine health status text
            if health >= 80:
                status = "● Excellent"
            elif health >= 60:
                status = "● Good"
            elif health >= 40:
                status = "● Fair"
            else:
                status = "● Poor"

            # Check if this matches preferred version
            is_recommended = preferred_version and preferred_version in version
            version_display = f"{version} ✓" if is_recommended else version

            tree.insert("", tk.END, iid=str(i), values=(
                version_display,
                f"{health}%",
                source.replace('_', ' ').title(),
                status
            ))

        # Select "Auto" by default
        tree.selection_set("auto")
        tree.focus("auto")

        # Detail panel
        detail_frame = ttk.LabelFrame(dialog, text=" Installation Details ", padding=10)
        detail_frame.pack(fill=tk.X, padx=20, pady=5)

        path_var = tk.StringVar(value="Select an installation to see details")
        warnings_var = tk.StringVar(value="")

        ttk.Label(detail_frame, text="Path:", font=Theme.FONT_BOLD).grid(row=0, column=0, sticky=tk.W)
        path_label = ttk.Label(detail_frame, textvariable=path_var, font=Theme.FONT_NORMAL, wraplength=600)
        path_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        warnings_label = ttk.Label(detail_frame, textvariable=warnings_var, font=Theme.FONT_NORMAL,
                                   foreground="#856404", wraplength=600)
        warnings_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        # Health score indicator using shared utility
        health_frame = ttk.Frame(detail_frame)
        health_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))

        health_indicator_label = tk.Label(health_frame, text="Health: --", font=Theme.FONT_BOLD)
        health_indicator_label.pack(side=tk.LEFT)

        def update_health_color(health):
            if health >= 80:
                return "#28a745"
            elif health >= 60:
                return "#ffc107"
            elif health >= 40:
                return "#fd7e14"
            else:
                return "#dc3545"

        def on_tree_select(event):
            selection = tree.selection()
            if selection:
                sel_id = selection[0]
                if sel_id == "auto":
                    # Auto selection - show best install details
                    path_var.set(f"Auto → {best_install.get('engine_root', 'N/A')}")
                    health = int(best_install.get('health_score', 0) * 100)
                    color = update_health_color(health)
                    health_indicator_label.config(text=f"Health: {health}%", fg=color)
                    warnings_var.set("Will automatically select the best available engine")
                else:
                    index = int(sel_id)
                    selected = installs[index]
                    path_var.set(selected.get('engine_root', 'N/A'))

                    health = int(selected.get('health_score', 0) * 100)
                    color = update_health_color(health)
                    health_indicator_label.config(text=f"Health: {health}%", fg=color)

                    # Show warnings if any
                    warnings = selected.get('warnings', [])
                    if warnings:
                        warnings_var.set(f"⚠ {' | '.join(warnings)}")
                    else:
                        warnings_var.set("")

        tree.bind('<<TreeviewSelect>>', on_tree_select)

        # Trigger initial selection display for "auto"
        on_tree_select(None)

        def on_select():
            selection = tree.selection()
            if selection:
                sel_id = selection[0]
                if sel_id == "auto":
                    # Use best install
                    selected = best_install
                else:
                    index = int(sel_id)
                    selected = installs[index]

                health = int(selected.get('health_score', 0) * 100)
                self.engine_path.set(selected['engine_root'])
                self.log(f"✓ Selected {selected['version']} (health: {health}%)")

                # Show warnings if any
                warnings = selected.get('warnings', [])
                if warnings:
                    for warning in warnings:
                        self.log(f"⚠ {warning}")

                dialog.destroy()
            else:
                messagebox.showwarning("No Selection", "Please select an installation")

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=15)

        ttk.Button(button_frame, text="Select", command=on_select,
                   style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Help", command=lambda: gui_helpers.show_engine_detection_help(
            dialog, self.browse_engine_path)).pack(side=tk.LEFT, padx=5)

    def start_install(self):
        self.btn_install.config(state=tk.DISABLED)
        self.btn_cancel.config(text="Cancel")
        self.is_running = True
        self.cancelled = False
        self.notebook.select(self.tab_execute)
        threading.Thread(target=self.run_install_process, daemon=True).start()

    def cancel_or_close(self):
        if self.is_running:
            if messagebox.askyesno("Cancel", "Are you sure you want to cancel the current operation?"):
                self.cancelled = True
                if self.current_process:
                    try:
                        self.current_process.terminate()
                    except:
                        pass
                self.log("[CANCELLED] Operation cancelled by user.")
                self.is_running = False
                self.btn_install.config(state=tk.NORMAL)
                self.btn_cancel.config(text="Close")
        else:
            self.root.destroy()

    def _create_windows_shortcut(self, target, shortcut_path, working_dir="", icon=None):
        """Create a Windows shortcut (.lnk) using VBScript"""
        vbs_script = f"""
        Set oWS = WScript.CreateObject(\"WScript.Shell\")
        Set oLink = oWS.CreateShortcut(\"{shortcut_path}\")
        oLink.TargetPath = \"{target}\"
        oLink.WorkingDirectory = \"{working_dir}\"
        oLink.Save
        """
        vbs_file = Path(os.environ["TEMP"]) / "create_shortcut.vbs"
        try:
            vbs_file.write_text(vbs_script)
            subprocess.run(["cscript", "//Nologo", str(vbs_file)], check=True)
        finally:
            if vbs_file.exists():
                vbs_file.unlink()

    def run_install_process(self):
        try:
            target = Path(self.target_dir.get())
            self.log(f"Installing to: {target}")
            
            # 1. Copy Files
            self.log("Copying files...")
            target.mkdir(parents=True, exist_ok=True)
            
            # Use simplified copy logic similar to previous script
            # Copy src, config, tools, docs
            for item in ["src", "config", "tools", "docs", "ask.bat", "launcher.bat", "requirements.txt", ".indexignore"]:
                src = self.source_dir / item
                dst = target / item
                if not src.exists():
                    self.log(f"  Skipping {item} (not found in source)")
                    continue  # Skip if source doesn't exist
                try:
                    if src.is_dir():
                        if dst.exists():
                            self.log(f"  Updating {item}/")
                            shutil.rmtree(dst)
                        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
                    elif src.is_file():
                        self.log(f"  Copying {item}")
                        shutil.copy2(src, dst)
                except Exception as e:
                    self.log(f"  ⚠ Warning: Failed to copy {item}: {e}")
                    raise  # Re-raise to trigger main error handler
            
            # 2. Write Configuration
            self.log("Configuring...")
            env_path = target / "config" / ".env"

            # Ensure vector store path is relative to target installation
            vector_dir = self.vector_store_path.get() if self.vector_store_path.get() else str(target / "data")

            with open(env_path, 'w') as f:
                f.write(f"# UE5 Source Query Configuration\n")
                f.write(f"# Generated by deployment wizard v{self.get_tool_version()}\n")
                f.write(f"\n")
                f.write(f"ANTHROPIC_API_KEY={self.api_key.get()}\n")
                f.write(f"VECTOR_OUTPUT_DIR={vector_dir}\n")
                f.write(f"UE_ENGINE_ROOT={self.engine_path.get()}\n")
                f.write(f"EMBED_MODEL={self.embed_model.get()}\n")
                f.write(f"ANTHROPIC_MODEL={self.api_model.get()}\n")
                f.write(f"EMBED_BATCH_SIZE={self.embed_batch_size.get()}\n")

            # Write version file for update detection
            version_file = target / "VERSION.txt"
            with open(version_file, 'w') as f:
                f.write(f"{self.get_tool_version()}\n")
            
            # 3. Create EngineDirs.txt using SourceManager
            if self.engine_path.get() and self.engine_dirs:
                self.log("Configuring Engine directories via SourceManager...")
                engine_root = self.engine_path.get().rstrip('/\\')

                # Validate engine root exists
                if not Path(engine_root).exists():
                    self.log(f"⚠ WARNING: Engine path does not exist: {engine_root}")
                    self.log("  Index building may fail. Please verify the engine path.")

                # Use SourceManager for consistent file handling
                target_source_manager = SourceManager(target)

                # Resolve placeholders and add directories
                valid_paths = 0
                invalid_paths = []
                resolved_dirs = []

                for d in self.engine_dirs:
                    resolved = d.replace("{ENGINE_ROOT}", engine_root)
                    resolved_dirs.append(resolved)

                    # Validate path exists
                    if Path(resolved).exists():
                        valid_paths += 1
                    else:
                        invalid_paths.append(resolved)

                # Write all engine dirs at once
                output = target / "src" / "indexing" / "EngineDirs.txt"
                output.parent.mkdir(parents=True, exist_ok=True)
                with open(output, 'w') as f:
                    f.write(f"# Auto-generated for Engine Root: {engine_root}\n")
                    f.write(f"# Managed by SourceManager - Deployment Wizard v{self.get_tool_version()}\n")
                    for d in resolved_dirs:
                        f.write(f"{d}\n")

                self.log(f"✓ Wrote {len(self.engine_dirs)} engine source paths to EngineDirs.txt")
                self.log(f"  Valid paths: {valid_paths}, Invalid paths: {len(invalid_paths)}")

                if invalid_paths:
                    self.log("⚠ WARNING: Some engine paths do not exist:")
                    for p in invalid_paths[:5]:  # Show first 5
                        self.log(f"  - {p}")
                    if len(invalid_paths) > 5:
                        self.log(f"  ... and {len(invalid_paths) - 5} more")
            else:
                self.log("⚠ WARNING: No engine path configured - index will be empty!")
                self.log("  Go to Configuration tab and set Engine Path before building index.")

            # 4. Create ProjectDirs.txt using SourceManager
            project_dirs_final = list(self.project_dirs)

            # Add the single one if specified via simple browse
            if self.project_path.get():
                p = self.project_path.get()
                if p.lower().endswith(".uproject"):
                    src = resolve_uproject_source(p)
                    if src and src not in project_dirs_final:
                        project_dirs_final.append(src)
                elif Path(p).is_dir() and p not in project_dirs_final:
                    project_dirs_final.append(p)

            if project_dirs_final:
                self.log(f"Configuring {len(project_dirs_final)} project directories via SourceManager...")
                # Use SourceManager for consistent file handling
                target_source_manager = SourceManager(target)
                output = target / "src" / "indexing" / "ProjectDirs.txt"
                output.parent.mkdir(parents=True, exist_ok=True)
                with open(output, 'w') as f:
                    f.write("# Auto-generated Project Directories\n")
                    f.write(f"# Managed by SourceManager - Deployment Wizard v{self.get_tool_version()}\n")
                    for p in project_dirs_final:
                        f.write(f"{p}\n")
            
            # 5. Create Venv & Install
            self.log("Creating Virtual Environment (this takes time)...")
            subprocess.run([sys.executable, "-m", "venv", str(target / ".venv")])
            
            pip = target / ".venv" / "Scripts" / "pip.exe"
            self.log("Installing dependencies...")
            subprocess.run([str(pip), "install", "-r", str(target / "requirements.txt")])

            # 5b. GPU Support - Install CUDA and GPU-accelerated packages
            if self.gpu_support.get():
                self.log("GPU Support enabled - checking CUDA...")

                if not self.gpu_info:
                    self.gpu_info = get_gpu_summary()

                if self.gpu_info["has_nvidia_gpu"]:
                    cuda_required = self.gpu_info["cuda_required"]
                    cuda_installed = self.gpu_info["cuda_installed"]

                    # Check if CUDA needs to be installed
                    if self.gpu_info["needs_cuda_install"]:
                        self.log(f"CUDA {cuda_required} is required but not installed.")
                        response = messagebox.askyesno(
                            "CUDA Installation Required",
                            f"Your {self.gpu_info['gpu_name']} requires CUDA {cuda_required}.\n\n"
                            f"Would you like to download and install CUDA now?\n"
                            f"(This may take 15-30 minutes)\n\n"
                            f"If you skip this, GPU acceleration will not work."
                        )

                        if response:
                            self.log(f"Downloading CUDA {cuda_required}...")
                            self.log("NOTE: CUDA installation will request administrator privileges.")
                            download_url = self.gpu_info["download_url"]

                            def progress_cb(downloaded, total):
                                if total > 0:
                                    pct = (downloaded / total) * 100
                                    self.root.after(0, lambda: self.log(f"  Download progress: {pct:.1f}%"))

                            def status_cb(msg):
                                self.root.after(0, lambda: self.log(f"  {msg}"))

                            # Run CUDA installation in a separate thread
                            def install_cuda_thread():
                                success = install_cuda_with_progress(download_url, progress_cb, status_cb)

                                if success:
                                    self.root.after(0, lambda: self.log("✓ CUDA installed successfully!"))
                                    self.root.after(0, lambda: messagebox.showinfo(
                                        "CUDA Installed",
                                        f"CUDA {cuda_required} has been installed successfully.\n\n"
                                        "You may need to restart your computer for changes to take effect."
                                    ))
                                else:
                                    self.root.after(0, lambda: self.log("✗ CUDA installation failed or was cancelled."))
                                    self.root.after(0, lambda: messagebox.showwarning(
                                        "CUDA Installation",
                                        f"CUDA installation failed.\n\n"
                                        f"You can install CUDA {cuda_required} manually from:\n"
                                        f"{download_url}\n\n"
                                        "GPU-accelerated packages will still be installed."
                                    ))

                            # Use a non-daemon thread so we wait for completion
                            install_thread = threading.Thread(target=install_cuda_thread, daemon=False)
                            install_thread.start()

                            # Wait for CUDA installation to complete before proceeding
                            self.log("Waiting for CUDA installation to complete...")
                            install_thread.join()  # Wait for thread to finish
                            self.log("CUDA installation thread completed.")
                        else:
                            self.log("Skipping CUDA installation. GPU support will be limited.")
                            messagebox.showinfo(
                                "CUDA Required",
                                f"To enable GPU acceleration, please install CUDA {cuda_required} manually:\n\n"
                                f"{download_url}\n\n"
                                "GPU-accelerated packages will be installed, but won't work until CUDA is installed."
                            )

                    # Install GPU-accelerated Python packages
                    self.log("Installing GPU-accelerated packages...")
                    gpu_req_file = target / "requirements-gpu.txt"
                    create_gpu_requirements_file(gpu_req_file, cuda_required)
                    result = subprocess.run([str(pip), "install", "-r", str(gpu_req_file)],
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        self.log("✓ GPU packages installed successfully")
                    else:
                        self.log(f"⚠ Warning: GPU package installation had issues: {result.stderr[:200]}")
                        self.log("  Index build will proceed, but may fall back to CPU")
                else:
                    self.log("No NVIDIA GPU detected. Skipping GPU setup.")

            if self.build_index.get():
                self.log("Building Index...")
                # Use the robust batch script which handles env vars and paths correctly
                rebuild_script = target / "tools" / "rebuild-index.bat"
                
                cmd = [str(rebuild_script), "--force", "--verbose"]

                self.log(f"Running: {rebuild_script.name} --force --verbose")

                # Ensure environment variables are passed to subprocess
                import os
                env = os.environ.copy()
                # Force the correct paths for this installation
                env['VECTOR_OUTPUT_DIR'] = str(target / "data")
                env['UE_ENGINE_ROOT'] = self.engine_path.get()
                env['EMBED_BATCH_SIZE'] = self.embed_batch_size.get()

                self.current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    cwd=str(target),
                    env=env  # Pass environment with correct paths
                )
                
                # Read output line by line
                if self.current_process.stdout:
                    for line in iter(self.current_process.stdout.readline, ''):
                        if self.cancelled: break
                        if line:
                            self.root.after(0, lambda l=line: self.log(f"  {l.strip()}"))
                
                if not self.cancelled:
                    self.current_process.wait()
                    process = self.current_process
                
                if process.returncode == 0:
                    self.root.after(0, lambda: self.log("✓ Index built successfully"))
                else:
                    self.root.after(0, lambda: self.log(f"✗ Index build failed with code {process.returncode}"))
            
            # 6. Create Shortcut
            if self.create_shortcut.get():
                self.log("Creating Desktop Shortcut...")
                try:
                    desktop = Path(os.environ["USERPROFILE"]) / "Desktop"
                    launcher_bat = target / "launcher.bat"
                    self._create_windows_shortcut(
                        str(launcher_bat),
                        str(desktop / "UE5 Source Query.lnk"),
                        working_dir=str(target)
                    )
                    self.log("  ✓ Shortcut created")
                except Exception as e:
                    self.log(f"  ! Failed to create shortcut: {e}")

            # Create deployment configuration for smart updates
            self.log("Creating deployment configuration...")
            self._create_deployment_config(target)

            self.log("SUCCESS! Installation Complete.")
            messagebox.showinfo("Success", "Installation Complete!")
            
        except Exception as e:
            if not self.cancelled:
                self.log(f"ERROR: {e}")
                messagebox.showerror("Error", str(e))
        finally:
            self.is_running = False
            self.current_process = None
            self.btn_install.config(state=tk.NORMAL)
            self.btn_cancel.config(text="Close")

    def _create_deployment_config(self, target: Path):
        """
        Create .ue5query_deploy.json for smart update system.

        This allows deployed installations to pull updates from local dev repo
        or remote GitHub repository.
        """
        import datetime

        # Detect if source is a git repo (for remote URL detection)
        remote_repo = "https://github.com/yourusername/UE5-Source-Query.git"  # Default
        branch = "master"

        try:
            # Try to get git remote URL from source repo
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                cwd=self.source_dir,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                remote_repo = result.stdout.strip()

            # Get current branch
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.source_dir,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                branch = result.stdout.strip()
        except:
            # If git detection fails, use defaults
            pass

        config = {
            "version": self.get_tool_version(),
            "deployment_info": {
                "deployed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "deployed_from": str(self.source_dir),
                "deployment_method": "gui_installer",
                "deployed_to": str(target),
                "last_updated": None,
                "update_source": None,
                "updated_from": None
            },
            "update_sources": {
                "local_dev_repo": str(self.source_dir),
                "remote_repo": remote_repo,
                "branch": branch
            },
            "update_strategy": "auto",
            "exclude_patterns": [
                ".venv/",
                "data/vector_store.npz",
                "data/vector_meta*.json",
                ".git/",
                "__pycache__/",
                "*.pyc",
                "*.pyo",
                "*.pyd",
                ".pytest_cache",
                ".coverage",
                "*.log"
            ],
            "preserve_local": [
                "config/user_config.json",
                ".env",
                "data/vector_store.npz",
                "data/vector_meta.json",
                "data/vector_meta_enriched.json",
                "data/vector_cache.json"
            ]
        }

        config_file = target / ".ue5query_deploy.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        self.log(f"  ✓ Deployment config created: .ue5query_deploy.json")
        self.log(f"  - Local dev repo: {self.source_dir}")
        self.log(f"  - Remote repo: {remote_repo}")
        self.log(f"  - Update available via: update.bat")

    def log(self, msg):
        self.log_queue.put(msg)

    def process_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, msg + "\n")
                self.log_text.see(tk.END)
        except queue.Empty:
            pass
        self.root.after(100, self.process_log_queue)

if __name__ == "__main__":
    root = tk.Tk()
    app = DeploymentWizard(root)
    root.mainloop()
