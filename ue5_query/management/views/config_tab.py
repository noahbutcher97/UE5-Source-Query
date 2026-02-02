import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import sys
import threading
from pathlib import Path

# Try to import Theme, handle missing imports gracefully
try:
    from ue5_query.utils.gui_theme import Theme
except ImportError:
    # If run standalone
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
        from ue5_query.utils.gui_theme import Theme
    except ImportError:
        Theme = None

class ConfigTab:
    """
    Handles the Configuration tab logic and layout.
    """
    def __init__(self, parent_frame, dashboard):
        """
        Args:
            parent_frame: The ttk.Frame to build the tab into
            dashboard: Reference to the main UnifiedDashboard instance (controller)
        """
        self.frame = parent_frame
        self.dashboard = dashboard
        self.config_manager = dashboard.config_manager
        self.script_dir = dashboard.script_dir
        
        # Access variables from dashboard controller
        self.api_key_var = dashboard.api_key_var
        self.engine_path_var = dashboard.engine_path_var
        self.vector_store_var = dashboard.vector_store_var
        self.embed_model_var = dashboard.embed_model_var
        self.api_model_var = dashboard.api_model_var
        self.embed_batch_size_var = dashboard.embed_batch_size_var
        self.text_scale_var = getattr(dashboard, 'text_scale_var', tk.DoubleVar(value=1.0))

        self.build_ui()
        self.load_current_engine_path() # Load engine path initially

    def build_ui(self):
        """Build the UI components"""
        frame = ttk.Frame(self.frame, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Instructions
        ttk.Label(frame, text="Configure your Anthropic API key, UE5 Engine paths, and models.", font=Theme.FONT_NORMAL).pack(anchor=tk.W, pady=(0, 15))

        # UI Appearance Section
        ui_frame = ttk.LabelFrame(frame, text=" UI Appearance ", padding=15)
        ui_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(ui_frame, text="Text Scale:", font=Theme.FONT_BOLD).pack(side=tk.LEFT)

        def update_scale_label(val):
            self.lbl_scale.config(text=f"{float(val):.1f}x")

        scale_slider = ttk.Scale(ui_frame, from_=0.8, to=2.0, variable=self.text_scale_var, command=update_scale_label)
        scale_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        self.lbl_scale = ttk.Label(ui_frame, text=f"{self.text_scale_var.get():.1f}x")
        self.lbl_scale.pack(side=tk.LEFT)

        if hasattr(self.dashboard, 'apply_ui_scale'):
            ttk.Button(ui_frame, text="Apply & Restart", command=self.dashboard.apply_ui_scale).pack(side=tk.LEFT, padx=10)

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

        # Source indicator
        self.engine_source_label = tk.Label(
            path_frame,
            text="",
            font=Theme.FONT_TINY,
            fg="#666",
            bg=Theme.BG_LIGHT,
            anchor=tk.W
        )
        self.engine_source_label.pack(fill=tk.X, pady=(5, 0))
        self._update_engine_source_indicator()

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

        # GPU Optimization Section
        gpu_frame = ttk.LabelFrame(frame, text=" GPU Optimization ", padding=15)
        gpu_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(gpu_frame, text="Embedding Batch Size:", font=Theme.FONT_BOLD).pack(anchor=tk.W, pady=5)
        ttk.Label(gpu_frame, text="RTX 5090: Use 8-16 | RTX 4090/3090: Use 32+ | CPU: Use 1-4", font=Theme.FONT_NORMAL, foreground="#666").pack(anchor=tk.W, pady=(0, 5))
        batch_size_combo = ttk.Combobox(gpu_frame, textvariable=self.embed_batch_size_var, state='readonly')
        batch_size_combo['values'] = ('1', '2', '4', '8', '16', '32', '64')
        batch_size_combo.pack(fill=tk.X)
        ttk.Label(gpu_frame, text="Smaller batches = more stable, larger batches = faster (if no errors)", font=Theme.FONT_NORMAL, foreground="#666", wraplength=500).pack(anchor=tk.W, pady=(5, 0))

        # Action Buttons
        button_frame = tk.Frame(frame, bg=Theme.BG_LIGHT)
        button_frame.pack(pady=20)

        ttk.Button(
            button_frame,
            text="🔍 Test Configuration",
            command=self.test_configuration,
            style='Accent.TButton'
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            button_frame,
            text="💾 Save Configuration",
            command=self.save_configuration,
            style='Accent.TButton'
        ).pack(side=tk.LEFT)
        
        # Log for config operations
        config_log_frame = ttk.LabelFrame(frame, text=" Configuration Log ", padding=5)
        config_log_frame.pack(fill=tk.BOTH, expand=True)
        self.config_log_text = scrolledtext.ScrolledText(config_log_frame, font=Theme.FONT_MONO, height=5)
        self.config_log_text.pack(fill=tk.BOTH, expand=True)

    def log_config(self, message, clear=False, append=False):
        self.config_log_text.config(state=tk.NORMAL)
        if clear:
            self.config_log_text.delete(1.0, tk.END)
        self.config_log_text.insert(tk.END, message + ("\n" if not message.endswith("\n") else ""))
        self.config_log_text.see(tk.END)
        self.config_log_text.config(state=tk.DISABLED)

    def load_current_engine_path(self):
        """Load engine path from config file, not from EngineDirs.txt"""
        config_file = self.script_dir / "config" / ".env"

        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('UE_ENGINE_ROOT='):
                            engine_root = line.split('=', 1)[1].strip()
                            self.engine_path_var.set(engine_root)
                            return
            except Exception as e:
                self.engine_path_var.set(f"Error reading config: {e}")
                return

        # Fallback: try to auto-detect
        self.engine_path_var.set("Not detected. Run auto-detect.")

    def test_configuration(self):
        """Comprehensive configuration validation with auto-detection and user guidance"""
        self.log_config("Testing configuration...", clear=True)

        def _test():
            issues = []
            warnings = []

            # 1. Test API Key
            api_key = self.api_key_var.get()
            if not api_key or api_key.strip() == "" or api_key == "your_api_key_here":
                issues.append("❌ API Key: Not configured")
                self.dashboard.root.after(0, lambda: self.log_config("❌ API Key: Missing - Please add your Anthropic API key", append=True))
            elif not api_key.startswith("sk-ant-"):
                warnings.append("⚠️ API Key: Format looks incorrect (should start with 'sk-ant-')")
                self.dashboard.root.after(0, lambda: self.log_config("⚠️ API Key: Format may be incorrect", append=True))
            else:
                self.dashboard.root.after(0, lambda: self.log_config("✓ API Key: Configured", append=True))

            # 2. Test Engine Path
            engine_path = self.engine_path_var.get()
            if (not engine_path or
                "No UE5 engine detected" in engine_path or
                "{ENGINE_ROOT}" in engine_path or
                "Not detected" in engine_path or
                "Auto-detection failed" in engine_path):
                
                # Import helper dynamically
                try:
                    from ue5_query.utils.engine_helper import get_available_engines
                except ImportError:
                    from ue5_query.utils.engine_helper import get_available_engines

                # Try auto-detection
                self.dashboard.root.after(0, lambda: self.log_config("🔍 Attempting to auto-detect engine path...", append=True))
                engines = get_available_engines(self.script_dir)
                if engines:
                    first_engine = engines[0]
                    detected_path = first_engine.get('path') or first_engine.get('root')
                    if detected_path:
                        self.dashboard.root.after(0, lambda p=detected_path: self.engine_path_var.set(str(p)))
                        self.dashboard.root.after(0, lambda p=detected_path: self.log_config(f"✓ Engine Path: Auto-detected at {p}", append=True))
                    else:
                        issues.append("❌ Engine Path: Could not auto-detect")
                        self.dashboard.root.after(0, lambda: self.log_config("❌ Engine Path: Auto-detection failed - please browse manually", append=True))
                else:
                    issues.append("❌ Engine Path: No UE5 installation found")
                    self.dashboard.root.after(0, lambda: self.log_config("❌ Engine Path: No UE5 installation detected", append=True))
            else:
                # Validate existing path
                engine_dir = Path(engine_path)
                if engine_dir.exists():
                    self.dashboard.root.after(0, lambda p=engine_path: self.log_config(f"✓ Engine Path: Valid ({p})", append=True))
                else:
                    issues.append(f"❌ Engine Path: Directory does not exist: {engine_path}")
                    self.dashboard.root.after(0, lambda p=engine_path: self.log_config(f"❌ Engine Path: Invalid - {p} does not exist", append=True))

            # 3. Test Vector Store Directory
            vector_dir = Path(self.vector_store_var.get())
            if vector_dir.exists():
                self.dashboard.root.after(0, lambda: self.log_config(f"✓ Vector Store: Directory exists", append=True))
            else:
                self.dashboard.root.after(0, lambda: self.log_config(f"⚠️ Vector Store: Directory will be created on first use", append=True))
                warnings.append("⚠️ Vector Store: Directory will be created on first use")

            # 4. Test Model Settings
            embed_model = self.embed_model_var.get()
            api_model = self.api_model_var.get()
            self.dashboard.root.after(0, lambda m=embed_model: self.log_config(f"✓ Embedding Model: {m}", append=True))
            self.dashboard.root.after(0, lambda m=api_model: self.log_config(f"✓ API Model: {m}", append=True))

            # 5. Test Batch Size
            batch_size = self.embed_batch_size_var.get()
            try:
                bs_int = int(batch_size)
                if bs_int < 1:
                    warnings.append("⚠️ Batch Size: Very small, might be slow")
                self.dashboard.root.after(0, lambda b=batch_size: self.log_config(f"✓ Batch Size: {b}", append=True))
            except:
                issues.append("❌ Batch Size: Invalid number")
                self.dashboard.root.after(0, lambda: self.log_config(f"❌ Batch Size: Invalid", append=True))

            # Summary
            self.dashboard.root.after(0, lambda: self.log_config("\n" + "="*50, append=True))
            if len(issues) == 0 and len(warnings) == 0:
                self.dashboard.root.after(0, lambda: self.log_config("✓ All configuration checks passed!", append=True))
                self.dashboard.root.after(0, lambda: messagebox.showinfo("Configuration Test", "All configuration checks passed! ✓"))
            else:
                if issues:
                    self.dashboard.root.after(0, lambda c=len(issues): self.log_config(f"\n{c} issue(s) found - please fix before using", append=True))
                if warnings:
                    self.dashboard.root.after(0, lambda c=len(warnings): self.log_config(f"{c} warning(s) - system may work but check recommended", append=True))

                msg = f"Configuration Test Complete:\n\n"
                if issues:
                    msg += f"❌ {len(issues)} critical issue(s) found\n"
                if warnings:
                    msg += f"⚠️ {len(warnings)} warning(s)\n"
                msg += f"\nCheck the log below for details."

                self.dashboard.root.after(0, lambda m=msg: messagebox.showwarning("Configuration Test", m))

        threading.Thread(target=_test, daemon=True).start()

    def save_configuration(self):
        config_dict = {
            'ANTHROPIC_API_KEY': self.api_key_var.get(),
            'VECTOR_OUTPUT_DIR': self.vector_store_var.get(),
            'UE_ENGINE_ROOT': self.engine_path_var.get(),
            'EMBED_MODEL': self.embed_model_var.get(),
            'ANTHROPIC_MODEL': self.api_model_var.get(),
            'EMBED_BATCH_SIZE': self.embed_batch_size_var.get(),
            'GUI_TEXT_SCALE': f"{self.text_scale_var.get():.2f}",
        }

        # Validate API key
        if not config_dict['ANTHROPIC_API_KEY'] or config_dict['ANTHROPIC_API_KEY'] == "your_api_key_here":
            messagebox.showerror("Error", "Please enter a valid Anthropic API key")
            return
        if len(config_dict['ANTHROPIC_API_KEY']) < 20: # Basic check
            if not messagebox.askyesno("Warning", "API Key looks too short. Save anyway?"):
                return

        self.config_manager.save(config_dict)
        self.log_config("Configuration saved successfully.", clear=True)
        messagebox.showinfo("Success", "Configuration saved!")

    def toggle_api_visibility(self):
        if self.api_key_entry['show'] == '*':
            self.api_key_entry.config(show='')
        else:
            self.api_key_entry.config(show='*')

    def browse_vector_store(self):
        directory = filedialog.askdirectory(initialdir=self.vector_store_var.get())
        if directory:
            self.vector_store_var.set(directory)

    def browse_engine_path(self):
        directory = filedialog.askdirectory(initialdir=self.engine_path_var.get())
        if directory:
            self.engine_path_var.set(directory)

    def auto_detect_path(self):
        """Auto-detect UE5 installation"""
        self.log_config("Scanning for UE5 installations...", clear=True)
        
        # Import helper dynamically
        try:
            from ue5_query.utils.engine_helper import get_available_engines
        except ImportError:
            from ue5_query.utils.engine_helper import get_available_engines

        engines = get_available_engines(self.script_dir)
        
        if not engines:
            self.log_config("No UE5 installations found.")
            messagebox.showwarning("Auto-Detect", "Could not find any standard UE5 installations.")
            return

        # Create selection dialog
        self._show_engine_selection_dialog(engines)

    def _show_engine_selection_dialog(self, installations):
        dialog = tk.Toplevel(self.dashboard.root)
        dialog.title("Select UE5 Installation")
        dialog.minsize(500, 400)
        
        # Center dynamic
        root_x = self.dashboard.root.winfo_x()
        root_y = self.dashboard.root.winfo_y()
        root_w = self.dashboard.root.winfo_width()
        root_h = self.dashboard.root.winfo_height()
        
        width = 600
        height = 500
        
        x = root_x + (root_w - width) // 2
        y = root_y + (root_h - height) // 2
        
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        Theme.apply(dialog)

        ttk.Label(dialog, text="Found the following installations:", font=Theme.FONT_BOLD).pack(pady=10)

        # Listbox with scrollbar
        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        listbox = tk.Listbox(frame, font=("Arial", 10), height=10)
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=listbox.yview)
        listbox.config(yscrollcommand=scrollbar.set)
        
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for install in installations:
            health = int(install.get('health_score', 0) * 100)
            listbox.insert(tk.END, f"{install['version']} - {install['type']} ({health}% health)")

        # Info panel
        info_label = ttk.Label(dialog, text="Select a version to see details", foreground="gray", wraplength=450)
        info_label.pack(pady=10)

        def on_listbox_select(event):
            selection = listbox.curselection()
            if selection:
                index = selection[0]
                selected = installations[index]
                info_label.config(text=f"Path: {selected['engine_root']}")

        listbox.bind('<<ListboxSelect>>', on_listbox_select)

        def on_select():
            selection = listbox.curselection()
            if selection:
                index = selection[0]
                selected = installations[index]
                health = int(selected.get('health_score', 0) * 100)
                self.engine_path_var.set(selected['engine_root'])
                self.log_config(f"✓ Selected {selected['version']} (health: {health}%)", append=True)

                # Show warnings if any
                warnings = selected.get('warnings', [])
                if warnings:
                    for warning in warnings:
                        self.log_config(f"⚠ {warning}", append=True)

                dialog.destroy()
            else:
                messagebox.showwarning("No Selection", "Please select an installation")

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=15)

        ttk.Button(button_frame, text="Select", command=on_select,
                   style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def _update_engine_source_indicator(self):
        """Update the label showing where the engine path came from"""
        source = self.dashboard.engine_detection_source
        is_override = self.dashboard.engine_is_user_override
        
        text = ""
        color = "#666"
        
        if source == 'vector_store':
            text = "✓ Loaded from existing index (Reliable)"
            color = "#4CAF50"
        elif source == 'config':
            text = "ℹ Loaded from config file"
        elif source == 'registry':
            text = "ℹ Detected from system registry"
        elif source == 'program_files':
            text = "ℹ Detected from Program Files"
        elif source == 'epic_launcher':
            text = "ℹ Detected from Epic Games Launcher"
        elif source == 'uproject':
            text = "✓ Detected from .uproject file"
            color = "#4CAF50"
        
        if is_override:
            text += " (User Override)"
            
        self.engine_source_label.config(text=text, fg=color)
