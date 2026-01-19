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

# Determine script dir relative to package location for resource loading
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent

from ue5_query.utils.gui_theme import Theme
from ue5_query.utils.gui_layout import WindowManager, LayoutMetrics, Responsive
from ue5_query.utils.config_manager import ConfigManager
from ue5_query.utils.source_manager import SourceManager
from ue5_query.utils.engine_helper import get_available_engines, resolve_uproject_source
from ue5_query.utils.gpu_helper import detect_nvidia_gpu, get_gpu_summary, get_gpu_requirements_text
from ue5_query.utils.cuda_installer import install_cuda_with_progress
from ue5_query.utils.deployment_detector import DeploymentDetector, DeploymentRegistry
from ue5_query.utils import gui_helpers
from ue5_query.core.hybrid_query import HybridQueryEngine
from ue5_query.management.services import UpdateService, SearchService, MaintenanceService

class UnifiedDashboard:
    def __init__(self, root):
        self.root = root
        
        # Use Adaptive Layout Engine
        WindowManager.setup_window(
            self.root, 
            "UE5 Source Query Dashboard",
            target_width_pct=0.8,
            target_height_pct=0.8,
            min_w=1000,
            min_h=700
        )

        # Apply Theme
        Theme.apply(self.root)        
        self.script_dir = SCRIPT_DIR
        self.source_manager = SourceManager(self.script_dir)
        self.config_manager = ConfigManager(self.script_dir)
        
        # Initialize Services
        self.update_service = UpdateService(self.root, self.script_dir)
        self.search_service = SearchService(self.script_dir, self.config_manager)
        self.maint_service = MaintenanceService(self.script_dir)

        # Deployment detection
        self.deployment_detector = DeploymentDetector(self.script_dir)

        # Configuration variables
        self.api_key_var = tk.StringVar(value=self.config_manager.get('ANTHROPIC_API_KEY', ''))
        self.engine_path_var = tk.StringVar(value=self.config_manager.get('UE_ENGINE_ROOT', ''))
        self.vector_store_var = tk.StringVar(value=self.config_manager.get('VECTOR_OUTPUT_DIR', str(self.script_dir / 'data')))
        self.embed_model_var = tk.StringVar(value=self.config_manager.get('EMBED_MODEL', 'microsoft/unixcoder-base'))
        self.api_model_var = tk.StringVar(value=self.config_manager.get('ANTHROPIC_MODEL', 'claude-3-haiku-20240307'))
        self.embed_batch_size_var = tk.StringVar(value=self.config_manager.get('EMBED_BATCH_SIZE', '16'))
        self.text_scale_var = tk.DoubleVar(value=float(self.config_manager.get('GUI_TEXT_SCALE', LayoutMetrics().text_scale)))
        self.query_scope_var = tk.StringVar(value="engine")

        # Filter variables
        self.filter_entity_type_var = tk.StringVar(value="")
        self.filter_macro_var = tk.StringVar(value="")
        self.filter_file_type_var = tk.StringVar(value="")
        self.filter_boost_macros_var = tk.BooleanVar(value=False)

        self.engine = None

        self.current_process = None
        self.cancelled = False

        self.create_layout()
        
        # Add trace to update engine list when engine path changes
        self.engine_path_var.trace_add("write", lambda *args: self.refresh_engine_list())

        # Load engine path from source_manager after layout creation
        self._load_initial_engine_path()

        # Start periodic check for update notifications
        self.update_service.start_check()

        # Check for first run (missing index)
        self.root.after(1000, self._check_first_run)

    def _check_first_run(self):
        """Check if index is missing and guide user to build it"""
        store_path = self.script_dir / "data" / "vector_store.npz"
        if not store_path.exists():
            response = messagebox.askyesno(
                "Welcome to UE5 Source Query",
                "Search index not found.\n\nYou need to build the search index before you can query the codebase.\n\nWould you like to build it now? (Recommended)",
                icon='info'
            )
            
            if response:
                # Switch to Maintenance tab
                self.notebook.select(self.tab_maintenance)
                # Trigger rebuild
                self.root.after(500, self.rebuild_index)

    def _load_initial_engine_path(self):
        """Smart engine path detection with priority-based loading"""
        try:
            # Import smart detection
            from ue5_query.utils.engine_helper import get_smart_engine_path

            # Use smart detection
            smart_result = get_smart_engine_path(self.script_dir)

            if smart_result and smart_result.get('path'):
                # Store detection metadata for display
                self.engine_detection_source = smart_result.get('source', 'unknown')
                self.engine_is_user_override = smart_result.get('is_user_override', False)

                engine_path = smart_result['path']
                self.engine_path_var.set(str(engine_path))

                # If source is vector_store and differs from config, offer to update
                if smart_result.get('source') == 'vector_store':
                    config_path = self.config_manager.get('UE_ENGINE_ROOT', '')
                    if config_path and config_path != engine_path:
                        # Auto-update config to match vector store
                        self.config_manager.set('UE_ENGINE_ROOT', engine_path)
                        self.config_manager.save(self.config_manager._config)
                return

            # No engine found
            self.engine_detection_source = 'none'
            self.engine_is_user_override = False
            self.engine_path_var.set("No UE5 engine detected - click Auto-Detect")

        except Exception as e:
            self.engine_detection_source = 'error'
            self.engine_is_user_override = False
            self.engine_path_var.set(f"Auto-detection failed: {str(e)}")
        
    def create_layout(self):
        # Header
        Theme.create_header(self.root, "UE5 Source Query", "Management Dashboard")
        
        # Main container
        container = tk.Frame(self.root, bg=Theme.BG_LIGHT)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Tabs
        self.notebook = ttk.Notebook(container)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 1. System Status Tab (NEW - Environment & Update Info)
        self.tab_status = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_status, text="System Status")
        self.build_status_tab()

        # 2. Query Tab (Main Interface)
        self.tab_query = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_query, text="Query")
        self.build_query_tab()

        # 3. Configuration Tab
        self.tab_config = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_config, text="Configuration")
        self.build_config_tab()

        # 4. Source Manager Tab
        self.tab_sources = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_sources, text="Source Manager")
        self.build_sources_tab()

        # 5. Diagnostics Tab (Health Check)
        self.tab_diagnostics = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_diagnostics, text="Diagnostics")
        self.build_diagnostics_tab()

        # 6. Maintenance Tab
        self.tab_maintenance = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_maintenance, text="Maintenance")
        self.build_maintenance_tab()

    def build_status_tab(self):
        """Build System Status tab showing environment type, deployment info, and update capabilities"""
        frame = ttk.Frame(self.tab_status, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Environment Type Section
        env_frame = ttk.LabelFrame(frame, text=" Environment Information ", padding=15)
        env_frame.pack(fill=tk.X, pady=(0, 15))

        # Environment type detection
        env_type = self.deployment_detector.env_type
        is_dev = self.deployment_detector.is_dev_repo()
        is_deployed = self.deployment_detector.is_deployed()
        is_valid = self.deployment_detector.env_info.is_valid

        # Environment type display
        env_type_frame = tk.Frame(env_frame, bg=Theme.BG_LIGHT)
        env_type_frame.pack(fill=tk.X, pady=5)

        env_type_label = tk.Label(
            env_type_frame,
            text="Environment Type:",
            font=Theme.FONT_BOLD,
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_DARK
        )
        env_type_label.pack(side=tk.LEFT, padx=(0, 10))

        # Color-code based on environment
        if is_dev:
            env_color = "#4CAF50"  # Green for dev
            env_display = "Development Repository"
        elif is_deployed:
            env_color = "#2196F3"  # Blue for deployed
            env_display = "Deployed Installation"
        else:
            env_color = "#FF9800"  # Orange for unknown
            env_display = "Unknown"

        env_value = tk.Label(
            env_type_frame,
            text=env_display,
            font=Theme.FONT_NORMAL,
            bg=env_color,
            fg="white",
            padx=10,
            pady=2
        )
        env_value.pack(side=tk.LEFT)

        # Validity status
        validity_label = tk.Label(
            env_type_frame,
            text=f"Valid: {'✓' if is_valid else '✗'}",
            font=Theme.FONT_NORMAL,
            bg=Theme.BG_LIGHT,
            fg="#4CAF50" if is_valid else "#F44336"
        )
        validity_label.pack(side=tk.LEFT, padx=(20, 0))

        # Root path
        root_frame = tk.Frame(env_frame, bg=Theme.BG_LIGHT)
        root_frame.pack(fill=tk.X, pady=5)

        root_label = tk.Label(
            root_frame,
            text="Root Directory:",
            font=Theme.FONT_BOLD,
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_DARK
        )
        root_label.pack(side=tk.LEFT, padx=(0, 10))

        root_value = tk.Label(
            root_frame,
            text=str(self.deployment_detector.root),
            font=Theme.FONT_SMALL,
            bg=Theme.BG_LIGHT,
            fg="#7F8C8D"
        )
        root_value.pack(side=tk.LEFT)

        # Issues (if any)
        if self.deployment_detector.env_info.issues:
            issues_frame = tk.Frame(env_frame, bg=Theme.BG_LIGHT)
            issues_frame.pack(fill=tk.X, pady=5)

            issues_label = tk.Label(
                issues_frame,
                text="Issues:",
                font=Theme.FONT_BOLD,
                bg=Theme.BG_LIGHT,
                fg="#F44336"
            )
            issues_label.pack(anchor=tk.W)

            for issue in self.deployment_detector.env_info.issues:
                issue_text = tk.Label(
                    issues_frame,
                    text=f"  • {issue}",
                    font=Theme.FONT_SMALL,
                    bg=Theme.BG_LIGHT,
                    fg="#F44336"
                )
                issue_text.pack(anchor=tk.W)

        # Deployment/Dev Repo Connection Section
        if is_deployed:
            self._build_deployed_status(frame)
        elif is_dev:
            self._build_dev_repo_status(frame)

        # Update Section
        update_frame = ttk.LabelFrame(frame, text=" Update System ", padding=15)
        update_frame.pack(fill=tk.X, pady=(0, 15))

        can_update = self.deployment_detector.can_update()

        if can_update:
            update_source = self.deployment_detector.get_update_source()

            # Update source display
            source_frame = tk.Frame(update_frame, bg=Theme.BG_LIGHT)
            source_frame.pack(fill=tk.X, pady=5)

            source_label = tk.Label(
                source_frame,
                text="Update Source:",
                font=("Arial", 10, "bold"),
                bg=Theme.BG_LIGHT,
                fg=Theme.TEXT_DARK
            )
            source_label.pack(side=tk.LEFT, padx=(0, 10))

            source_color = "#4CAF50" if update_source == "local" else "#2196F3"
            source_value = tk.Label(
                source_frame,
                text=f"{update_source.upper()}",
                font=("Arial", 10),
                bg=source_color,
                fg="white",
                padx=10,
                pady=2
            )
            source_value.pack(side=tk.LEFT)

            # Update buttons - Row 1: Primary actions
            btn_frame = tk.Frame(update_frame, bg=Theme.BG_LIGHT)
            btn_frame.pack(fill=tk.X, pady=10)

            update_btn = tk.Button(
                btn_frame,
                text="🔄 Update Now (Smart)",
                command=self.run_update,
                bg=Theme.SECONDARY,
                fg="white",
                font=Theme.FONT_BOLD,
                padx=20,
                pady=8,
                relief=tk.FLAT,
                cursor="hand2"
            )
            update_btn.pack(side=tk.LEFT, padx=(0, 10))

            check_btn = tk.Button(
                btn_frame,
                text="🔍 Check for Updates",
                command=lambda: self.run_update(dry_run=True),
                bg=Theme.BG_DARK,
                fg="white",
                font=Theme.FONT_NORMAL,
                padx=15,
                pady=8,
                relief=tk.FLAT,
                cursor="hand2"
            )
            check_btn.pack(side=tk.LEFT)

            # Advanced options - Row 2: Source-specific updates
            advanced_frame = tk.Frame(update_frame, bg=Theme.BG_LIGHT)
            advanced_frame.pack(fill=tk.X, pady=(5, 0))

            # Label for advanced options
            adv_label = tk.Label(
                advanced_frame,
                text="Advanced:",
                font=("Arial", 9, "italic"),
                bg=Theme.BG_LIGHT,
                fg="#7F8C8D"
            )
            adv_label.pack(side=tk.LEFT, padx=(0, 10))

            # Force Local button (if local source available)
            if update_source == "local" or "local" in str(self.deployment_detector.get_dev_repo_path() or ""):
                local_btn = tk.Button(
                    advanced_frame,
                    text="📁 Force Local Dev",
                    command=lambda: self.run_update(force_source="local"),
                    bg="#4CAF50",
                    fg="white",
                    font=("Arial", 9),
                    padx=12,
                    pady=5,
                    relief=tk.FLAT,
                    cursor="hand2"
                )
                local_btn.pack(side=tk.LEFT, padx=(0, 5))

            # Force Remote button (if remote source available)
            remote_btn = tk.Button(
                advanced_frame,
                text="🌐 Force Remote GitHub",
                command=lambda: self.run_update(force_source="remote"),
                bg="#2196F3",
                fg="white",
                font=("Arial", 9),
                padx=12,
                pady=5,
                relief=tk.FLAT,
                cursor="hand2"
            )
            remote_btn.pack(side=tk.LEFT, padx=(0, 5))

            # Help text
            help_text = tk.Label(
                update_frame,
                text="💡 'Smart' auto-selects best source. Use 'Force' to override. Check first if unsure.",
                font=("Arial", 8),
                bg=Theme.BG_LIGHT,
                fg="#7F8C8D",
                wraplength=550,
                justify=tk.LEFT
            )
            help_text.pack(pady=(5, 0))
        else:
            no_update_label = tk.Label(
                update_frame,
                text="Updates not available for this installation",
                font=("Arial", 10),
                bg=Theme.BG_LIGHT,
                fg="#7F8C8D"
            )
            no_update_label.pack(pady=10)

        # Update log
        log_frame = ttk.LabelFrame(frame, text=" Update Log ", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.status_log = scrolledtext.ScrolledText(
            log_frame,
            height=10,
            font=("Consolas", 9),
            bg="#1E1E1E",
            fg="#D4D4D4",
            insertbackground="white"
        )
        self.status_log.pack(fill=tk.BOTH, expand=True)
        self.status_log.insert("1.0", "System ready. Click 'Update Now' to update from source.\n")
        self.status_log.config(state=tk.DISABLED)

    def _build_deployed_status(self, parent_frame):
        """Build status section for deployed environments"""
        deploy_frame = ttk.LabelFrame(parent_frame, text=" Deployment Information ", padding=15)
        deploy_frame.pack(fill=tk.X, pady=(0, 15))

        # Dev repo path
        dev_repo = self.deployment_detector.get_dev_repo_path()

        dev_frame = tk.Frame(deploy_frame, bg=Theme.BG_LIGHT)
        dev_frame.pack(fill=tk.X, pady=5)

        dev_label = tk.Label(
            dev_frame,
            text="Source Dev Repo:",
            font=("Arial", 10, "bold"),
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_DARK
        )
        dev_label.pack(side=tk.LEFT, padx=(0, 10))

        dev_value = tk.Label(
            dev_frame,
            text=str(dev_repo) if dev_repo else "Not connected",
            font=("Arial", 9),
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_LIGHT if dev_repo else "#F44336"
        )
        dev_value.pack(side=tk.LEFT)

        # Deployment timestamp (from config file)
        try:
            config_file = self.deployment_detector.root / ".ue5query_deploy.json"
            if config_file.exists():
                import json
                with open(config_file) as f:
                    config = json.load(f)
                    deployed_at = config.get("deployment_info", {}).get("deployed_at")

                    if deployed_at:
                        time_frame = tk.Frame(deploy_frame, bg=Theme.BG_LIGHT)
                        time_frame.pack(fill=tk.X, pady=5)

                        time_label = tk.Label(
                            time_frame,
                            text="Deployed At:",
                            font=("Arial", 10, "bold"),
                            bg=Theme.BG_LIGHT,
                            fg=Theme.TEXT_DARK
                        )
                        time_label.pack(side=tk.LEFT, padx=(0, 10))

                        time_value = tk.Label(
                            time_frame,
                            text=deployed_at,
                            font=("Arial", 9),
                            bg=Theme.BG_LIGHT,
                            fg="#7F8C8D"
                        )
                        time_value.pack(side=tk.LEFT)
        except Exception:
            pass  # Silently skip if config not available

        # Project engine version (from .uproject file and smart detection)
        try:
            from ue5_query.utils.engine_helper import find_uproject_in_directory, get_engine_version_from_uproject, get_smart_engine_path, detect_engine_from_vector_store

            uproject = find_uproject_in_directory(self.script_dir)
            if uproject:
                project_version = get_engine_version_from_uproject(str(uproject))
                if project_version:
                    # Use smart detection to get actual indexed version
                    indexed_version = None
                    detection_source = "config"

                    # Try vector store first (most accurate)
                    vector_engine = detect_engine_from_vector_store(self.script_dir)
                    if vector_engine:
                        version_str = vector_engine.get('version', '')
                        import re
                        match = re.search(r'(\d+\.\d+)', version_str)
                        if match:
                            indexed_version = match.group(1)
                            detection_source = "vector_store"

                    # Fallback to config if no vector store
                    if not indexed_version:
                        config_file = self.script_dir / "config" / ".env"
                        if config_file.exists():
                            import re
                            with open(config_file, 'r') as f:
                                for line in f:
                                    line = line.strip()
                                    if line.startswith('UE_ENGINE_ROOT='):
                                        engine_root = line.split('=', 1)[1].strip()
                                        match = re.search(r'UE[_-]?(\d+\.\d+)', engine_root)
                                        if match:
                                            indexed_version = match.group(1)
                                        break

                    # Create version display
                    version_frame = tk.Frame(deploy_frame, bg=Theme.BG_LIGHT)
                    version_frame.pack(fill=tk.X, pady=5)

                    version_label = tk.Label(
                        version_frame,
                        text="Project Engine:",
                        font=("Arial", 10, "bold"),
                        bg=Theme.BG_LIGHT,
                        fg=Theme.TEXT_DARK
                    )
                    version_label.pack(side=tk.LEFT, padx=(0, 10))

                    # Check if versions match
                    if indexed_version and project_version != indexed_version:
                        # Version mismatch - show warning
                        source_label = "built index" if detection_source == "vector_store" else "config"
                        version_text = f"{project_version} (⚠️ Index built from {indexed_version})"
                        version_color = "#F44336"  # Red
                    else:
                        # Versions match or no indexed version to compare
                        if indexed_version:
                            version_text = f"{project_version} ✓"
                        else:
                            version_text = project_version
                        version_color = "#4CAF50"  # Green

                    version_value = tk.Label(
                        version_frame,
                        text=version_text,
                        font=("Arial", 9),
                        bg=Theme.BG_LIGHT,
                        fg=version_color
                    )
                    version_value.pack(side=tk.LEFT)

                    # Add helpful tooltip/button for mismatch
                    if indexed_version and project_version != indexed_version:
                        warning_frame = tk.Frame(deploy_frame, bg="#FFF3CD", relief=tk.SOLID, bd=1)
                        warning_frame.pack(fill=tk.X, pady=5, padx=5)

                        warning_text = tk.Label(
                            warning_frame,
                            text=f"⚠️ Engine version mismatch detected. Consider rebuilding index with UE {project_version} source.",
                            font=("Arial", 8),
                            bg="#FFF3CD",
                            fg="#856404",
                            wraplength=500,
                            justify=tk.LEFT
                        )
                        warning_text.pack(padx=10, pady=5)
        except Exception:
            pass  # Silently skip if detection fails

    def _build_dev_repo_status(self, parent_frame):
        """Build status section for dev repo environments"""
        deploy_frame = ttk.LabelFrame(parent_frame, text=" Tracked Deployments ", padding=15)
        deploy_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        deployments = self.deployment_detector.get_deployments()

        if deployments:
            # Header
            header_frame = tk.Frame(deploy_frame, bg=Theme.BG_LIGHT)
            header_frame.pack(fill=tk.X, pady=(0, 10))

            count_label = tk.Label(
                header_frame,
                text=f"Found {len(deployments)} deployment(s):",
                font=("Arial", 10, "bold"),
                bg=Theme.BG_LIGHT,
                fg=Theme.TEXT_DARK
            )
            count_label.pack(side=tk.LEFT)

            # Deployments list
            deploy_list_frame = tk.Frame(deploy_frame, bg="white", relief=tk.SUNKEN, bd=1)
            deploy_list_frame.pack(fill=tk.BOTH, expand=True)

            # Create scrollable list
            deploy_canvas = tk.Canvas(deploy_list_frame, bg="white", highlightthickness=0, height=150)
            scrollbar = ttk.Scrollbar(deploy_list_frame, orient=tk.VERTICAL, command=deploy_canvas.yview)
            deploy_content = tk.Frame(deploy_canvas, bg="white")

            deploy_canvas.configure(yscrollcommand=scrollbar.set)

            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            deploy_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            canvas_frame = deploy_canvas.create_window((0, 0), window=deploy_content, anchor=tk.NW)

            # Add deployments
            for deploy in deployments:
                deploy_item = tk.Frame(deploy_content, bg="white", pady=5, padx=10)
                deploy_item.pack(fill=tk.X)

                # Status indicator
                status_color = "#4CAF50" if deploy.is_valid else "#F44336"
                status_indicator = tk.Label(
                    deploy_item,
                    text="●",
                    font=("Arial", 12),
                    bg="white",
                    fg=status_color
                )
                status_indicator.pack(side=tk.LEFT, padx=(0, 10))

                # Path
                path_label = tk.Label(
                    deploy_item,
                    text=deploy.path,
                    font=("Arial", 9),
                    bg="white",
                    fg=Theme.TEXT_DARK,
                    anchor=tk.W
                )
                path_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

                # Issues
                if deploy.issues:
                    issue_label = tk.Label(
                        deploy_item,
                        text=f"({', '.join(deploy.issues)})",
                        font=("Arial", 8),
                        bg="white",
                        fg="#F44336"
                    )
                    issue_label.pack(side=tk.RIGHT)

            # Update scroll region
            deploy_content.update_idletasks()
            deploy_canvas.configure(scrollregion=deploy_canvas.bbox("all"))

            # Bind mousewheel
            def _on_mousewheel(event):
                deploy_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            deploy_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        else:
            no_deploy_label = tk.Label(
                deploy_frame,
                text="No deployments found",
                font=("Arial", 10),
                bg=Theme.BG_LIGHT,
                fg="#7F8C8D"
            )
            no_deploy_label.pack(pady=20)

    def run_update(self, dry_run=False, force_source=None):
        """
        Run update process with comprehensive version checking and graceful fallback.

        Args:
            dry_run: If True, check for updates without applying
            force_source: Force 'local' or 'remote' source (None = auto-detect)
        """
        def log(msg, tag=""):
            """Thread-safe logging to status log"""
            self.root.after(0, lambda: self._append_log(msg, tag))

        def _append_log(msg, tag=""):
            self.status_log.config(state=tk.NORMAL)
            self.status_log.insert(tk.END, msg + "\n", tag)
            self.status_log.see(tk.END)
            self.status_log.config(state=tk.DISABLED)

        def update_thread():
            try:
                # Import update utilities
                try:
                    from tools.update import UpdateManager, get_version, compare_versions
                except ImportError:
                    import sys
                    sys.path.insert(0, str(self.script_dir / "tools"))
                    from update import UpdateManager, get_version, compare_versions

                self.status_log.config(state=tk.NORMAL)
                self.status_log.delete("1.0", tk.END)
                self.status_log.config(state=tk.DISABLED)

                if dry_run:
                    log("=" * 60)
                    log("UPDATE CHECK MODE (No changes will be made)")
                    log("=" * 60)
                else:
                    log("=" * 60)
                    log("UPDATE SYSTEM")
                    log("=" * 60)

                # Get current version
                current_version = get_version(self.script_dir)
                log(f"\nCurrent version: {current_version or 'unknown'}")

                manager = UpdateManager(self.script_dir)

                # Load config with graceful fallback
                if not manager.load_config():
                    log("[ERROR] Failed to load deployment config", "error")
                    log("\nThis may not be a deployed installation.")
                    log("Possible solutions:")
                    log("  1. Run Setup.bat to configure deployment")
                    log("  2. Use command line: python tools/update.py")
                    self.root.after(0, lambda: messagebox.showerror(
                        "Config Error",
                        "Failed to load deployment config.\n\nPlease run Setup.bat to configure this installation."
                    ))
                    return

                # Try to detect all available sources
                log("\nDetecting update sources...")
                available_sources = []

                # Check local dev repo
                local_repo = manager.config.get("update_sources", {}).get("local_dev_repo")
                if local_repo:
                    from pathlib import Path
                    local_path = Path(local_repo)
                    if local_path.exists() and (local_path / "src" / "__init__.py").exists():
                        local_version = get_version(local_path)
                        available_sources.append({
                            'type': 'local',
                            'path': str(local_path),
                            'version': local_version or 'unknown'
                        })
                        log(f"  [LOCAL] {local_path}")
                        log(f"          Version: {local_version or 'unknown'}")

                # Check remote repo
                remote_repo = manager.config.get("update_sources", {}).get("remote_repo")
                if remote_repo:
                    available_sources.append({
                        'type': 'remote',
                        'path': remote_repo,
                        'version': 'latest'  # Can't easily check without cloning
                    })
                    log(f"  [REMOTE] {remote_repo}")
                    log(f"           Version: latest (will check on pull)")

                if not available_sources:
                    log("\n[ERROR] No update sources configured!", "error")
                    log("\nPlease configure update sources:")
                    log("  1. Set local_dev_repo in deployment config")
                    log("  2. Set remote_repo for GitHub updates")
                    self.root.after(0, lambda: messagebox.showerror(
                        "No Sources",
                        "No update sources configured.\n\nPlease update .ue5query_deploy.json with source paths."
                    ))
                    return

                # Determine best source
                if force_source:
                    source = force_source
                    log(f"\n[FORCE] Using {source} source (user override)")
                else:
                    source = manager.detect_update_source()
                    log(f"\n[AUTO] Selected {source} source")

                # Check for updates before applying
                log("\nChecking for updates...")
                try:
                    update_info = manager.check_for_updates(source)

                    if update_info:
                        log(f"  Current: {update_info.get('current_version', 'unknown')}")
                        log(f"  Source:  {update_info.get('source_version', 'unknown')}")

                        if update_info.get('available'):
                            log("\n  [!] Updates available")
                        else:
                            log("\n  [OK] Already up-to-date")
                            if not dry_run:
                                log("\nNo update needed. Use 'Force Update' to update anyway.")
                            return
                except Exception as e:
                    log(f"[WARN] Version check failed: {e}", "warn")
                    log("Continuing with update anyway...")

                if dry_run:
                    log("\n" + "=" * 60)
                    log("DRY RUN COMPLETE - No changes made")
                    log("=" * 60)
                    log("\nClick 'Update Now' to apply updates.")
                    return

                # Perform update with fallback logic
                log("\n" + "=" * 60)
                log("APPLYING UPDATES")
                log("=" * 60)

                success = False
                fallback_attempted = False

                try:
                    # Try primary source using subprocess to capture output
                    log(f"\nAttempting update from {source} source...")

                    # Use subprocess to run update and capture stdout
                    import sys
                    import subprocess

                    update_script = self.script_dir / "tools" / "update.py"
                    cmd = [sys.executable, str(update_script)]

                    # Add appropriate flags based on source
                    if source == "local":
                        cmd.extend(["--source", "local"])
                    else:
                        cmd.extend(["--source", "remote"])

                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        cwd=str(self.script_dir)
                    )

                    # Stream output to log
                    for line in process.stdout:
                        self.root.after(0, lambda l=line: log(l.rstrip()))

                    process.wait()
                    success = process.returncode == 0

                except Exception as e:
                    log(f"[ERROR] Update from {source} failed: {e}", "error")

                    # Graceful fallback to alternative source
                    if source == "local" and len(available_sources) > 1:
                        fallback_source = "remote"
                        log(f"\n[FALLBACK] Attempting update from {fallback_source} source...")
                        fallback_attempted = True
                        try:
                            success = manager.update_from_remote(dry_run=False)
                        except Exception as e2:
                            log(f"[ERROR] Fallback also failed: {e2}", "error")
                    elif source == "remote" and len(available_sources) > 1:
                        fallback_source = "local"
                        log(f"\n[FALLBACK] Attempting update from {fallback_source} source...")
                        fallback_attempted = True
                        try:
                            success = manager.update_from_local(dry_run=False)
                        except Exception as e2:
                            log(f"[ERROR] Fallback also failed: {e2}", "error")

                if success:
                    log("\n" + "=" * 60)
                    log("[SUCCESS] Update completed!")
                    log("=" * 60)

                    if fallback_attempted:
                        log("\nNote: Used fallback source after primary failed.")

                    new_version = get_version(self.script_dir)
                    log(f"\nNew version: {new_version or 'unknown'}")
                    log("\n⚠️ IMPORTANT: Python cache cleared - restart required for changes to load")

                    # Prompt user to restart
                    def prompt_restart():
                        response = messagebox.askyesno(
                            "Update Complete - Restart Required",
                            f"System updated successfully!\n\n"
                            f"Version: {new_version or 'unknown'}\n\n"
                            f"Python cache has been cleared.\n"
                            f"Would you like to restart the application now?\n\n"
                            f"(Changes won't take effect until restart)",
                            icon='info'
                        )
                        if response:
                            # Restart the GUI
                            import sys
                            import os
                            # Re-execute using the same command line args, relying on the -m module invocation
                            os.execl(sys.executable, sys.executable, *sys.argv)

                    self.root.after(0, prompt_restart)
                else:
                    log("\n" + "=" * 60)
                    log("[FAILED] Update failed!")
                    log("=" * 60)
                    log("\nTroubleshooting:")
                    log("  1. Check network connection (for remote updates)")
                    log("  2. Verify dev repo path (for local updates)")
                    log("  3. Try command line: python tools/update.py --help")
                    log("  4. Check update log above for specific errors")

                    self.root.after(0, lambda: messagebox.showerror(
                        "Update Failed",
                        "Update process failed.\n\nPlease check the log for details or try updating via command line."
                    ))

            except Exception as e:
                log(f"\n[CRITICAL ERROR] {str(e)}", "error")
                log("\nPlease report this error if it persists.")
                import traceback
                log(f"\nDetails:\n{traceback.format_exc()}")

                self.root.after(0, lambda: messagebox.showerror(
                    "Critical Error",
                    f"Unexpected error during update:\n\n{str(e)}\n\nPlease try updating via command line."
                ))

        # Start update in background
        thread = threading.Thread(target=update_thread, daemon=True)
        thread.start()

    def _append_log(self, msg, tag=""):
        """Helper to append to status log (must be called from main thread)"""
        self.status_log.config(state=tk.NORMAL)
        self.status_log.insert(tk.END, msg + "\n", tag)
        self.status_log.see(tk.END)
        self.status_log.config(state=tk.DISABLED)

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

        # Advanced Filters Section
        filters_frame = ttk.LabelFrame(input_frame, text=" Advanced Filters (Optional) ", padding=10)
        filters_frame.pack(fill=tk.X, pady=(10, 0))

        # First row: Entity Type and Macro
        filter_row1 = ttk.Frame(filters_frame)
        filter_row1.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(filter_row1, text="Entity Type:", font=Theme.FONT_NORMAL).pack(side=tk.LEFT, padx=(0, 5))
        entity_types = ["", "struct", "class", "enum", "function", "delegate"]
        entity_combo = ttk.Combobox(filter_row1, textvariable=self.filter_entity_type_var, values=entity_types, state="readonly", width=12)
        entity_combo.pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(filter_row1, text="UE5 Macro:", font=Theme.FONT_NORMAL).pack(side=tk.LEFT, padx=(0, 5))
        macros = ["", "UPROPERTY", "UCLASS", "UFUNCTION", "USTRUCT"]
        macro_combo = ttk.Combobox(filter_row1, textvariable=self.filter_macro_var, values=macros, state="readonly", width=12)
        macro_combo.pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(filter_row1, text="File Type:", font=Theme.FONT_NORMAL).pack(side=tk.LEFT, padx=(0, 5))
        file_types = ["", "header", "implementation"]
        file_combo = ttk.Combobox(filter_row1, textvariable=self.filter_file_type_var, values=file_types, state="readonly", width=15)
        file_combo.pack(side=tk.LEFT)

        # Second row: Boost options and Clear button
        filter_row2 = ttk.Frame(filters_frame)
        filter_row2.pack(fill=tk.X)

        ttk.Checkbutton(filter_row2, text="Boost results with UE5 macros", variable=self.filter_boost_macros_var).pack(side=tk.LEFT)

        # Clear Filters button
        btn_clear_filters = ttk.Button(filter_row2, text="Clear All Filters", command=self.clear_filters)
        btn_clear_filters.pack(side=tk.RIGHT, padx=(10, 0))

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
        embed_model = self.embed_model_var.get()
        
        self.log_query_result("Thinking...", clear=True)
        self.query_entry.config(state=tk.DISABLED)

        # Prepare filter parameters
        filter_vars = {
            'entity_type': self.filter_entity_type_var.get(),
            'macro': self.filter_macro_var.get(),
            'file_type': self.filter_file_type_var.get(),
            'boost_macros': self.filter_boost_macros_var.get()
        }

        # Success callback
        def on_success(results):
            self.root.after(0, lambda: self.display_query_results(results))
            self.root.after(0, lambda: self.query_entry.config(state=tk.NORMAL))

        # Error callback
        def on_error(err):
            self.root.after(0, lambda: self.log_query_result(f"Error: {err}", clear=True, tag="error"))
            self.root.after(0, lambda: self.query_entry.config(state=tk.NORMAL))

        # Delegate search to service
        self.search_service.execute_query(
            query=query,
            scope=scope,
            embed_model=embed_model,
            filter_vars=filter_vars,
            callback=on_success,
            error_callback=on_error
        )

    def display_query_results(self, results):
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)
        
        # 1. Intent/Reasoning
        intent = results.get('intent', {})
        self.results_text.insert(tk.END, f"Query Type: {intent.get('type', 'Unknown')}\n", "header")
        if intent.get('entity_name'):
            self.results_text.insert(tk.END, f"Target Entity: {intent.get('entity_name')}\n")

        # Show active filters if any
        active_filters = []
        if self.filter_entity_type_var.get():
            active_filters.append(f"type={self.filter_entity_type_var.get()}")
        if self.filter_macro_var.get():
            active_filters.append(f"macro={self.filter_macro_var.get()}")
        if self.filter_file_type_var.get():
            active_filters.append(f"file={self.filter_file_type_var.get()}")
        if self.filter_boost_macros_var.get():
            active_filters.append("boost=macros")

        if active_filters:
            self.results_text.insert(tk.END, f"Active Filters: {', '.join(active_filters)}\n", "highlight")

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

    def clear_filters(self):
        """Clear all filter selections"""
        self.filter_entity_type_var.set("")
        self.filter_macro_var.set("")
        self.filter_file_type_var.set("")
        self.filter_boost_macros_var.set(False)

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
        """Build enhanced Diagnostics tab with comprehensive testing options"""
        frame = ttk.Frame(self.tab_diagnostics, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Test Options Section
        options_frame = ttk.LabelFrame(frame, text=" Test Suite Options ", padding=15)
        options_frame.pack(fill=tk.X, pady=(0, 15))

        # Grid layout for test buttons
        test_grid = tk.Frame(options_frame, bg=Theme.BG_LIGHT)
        test_grid.pack(fill=tk.X)

        # Row 1: Basic Health Checks
        row1_label = tk.Label(
            test_grid,
            text="Basic Health:",
            font=("Arial", 10, "bold"),
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_DARK,
            width=15,
            anchor=tk.W
        )
        row1_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)

        btn_health = tk.Button(
            test_grid,
            text="System Health",
            command=self.run_health_check,
            bg=Theme.SUCCESS,
            fg="white",
            padx=10,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2"
        )
        btn_health.grid(row=0, column=1, padx=5, pady=5)

        btn_vector = tk.Button(
            test_grid,
            text="Vector Store Validation",
            command=self.run_vector_validation,
            bg=Theme.SUCCESS,
            fg="white",
            padx=10,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2"
        )
        btn_vector.grid(row=0, column=2, padx=5, pady=5)

        # Row 2: Unit Tests
        row2_label = tk.Label(
            test_grid,
            text="Unit Tests:",
            font=("Arial", 10, "bold"),
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_DARK,
            width=15,
            anchor=tk.W
        )
        row2_label.grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=5)

        btn_deployment = tk.Button(
            test_grid,
            text="Deployment Detection",
            command=lambda: self.run_test_suite("deployment"),
            bg=Theme.SECONDARY,
            fg="white",
            padx=10,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2"
        )
        btn_deployment.grid(row=1, column=1, padx=5, pady=5)

        btn_update = tk.Button(
            test_grid,
            text="Update Integration",
            command=lambda: self.run_test_suite("update"),
            bg=Theme.SECONDARY,
            fg="white",
            padx=10,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2"
        )
        btn_update.grid(row=1, column=2, padx=5, pady=5)

        # Row 3: Smoke Tests
        row3_label = tk.Label(
            test_grid,
            text="Smoke Tests:",
            font=("Arial", 10, "bold"),
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_DARK,
            width=15,
            anchor=tk.W
        )
        row3_label.grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=5)

        btn_gui_smoke = tk.Button(
            test_grid,
            text="GUI Launch",
            command=self.run_gui_smoke_test,
            bg=Theme.WARNING,
            fg="white",
            padx=10,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2"
        )
        btn_gui_smoke.grid(row=2, column=1, padx=5, pady=5)

        btn_import_smoke = tk.Button(
            test_grid,
            text="Module Imports",
            command=self.run_import_smoke_test,
            bg=Theme.WARNING,
            fg="white",
            padx=10,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2"
        )
        btn_import_smoke.grid(row=2, column=2, padx=5, pady=5)

        # Row 4: Full Test Suite
        row4_label = tk.Label(
            test_grid,
            text="Full Suite:",
            font=("Arial", 10, "bold"),
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_DARK,
            width=15,
            anchor=tk.W
        )
        row4_label.grid(row=3, column=0, sticky=tk.W, padx=(0, 10), pady=5)

        btn_all_tests = tk.Button(
            test_grid,
            text="Run All Tests",
            command=lambda: self.run_test_suite("all"),
            bg=Theme.ERROR,
            fg="white",
            padx=15,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2",
            font=("Arial", 10, "bold")
        )
        btn_all_tests.grid(row=3, column=1, columnspan=2, padx=5, pady=5, sticky=tk.EW)

        # Output Area
        output_frame = ttk.LabelFrame(frame, text=" Test Output ", padding=10)
        output_frame.pack(fill=tk.BOTH, expand=True)

        self.diag_log = scrolledtext.ScrolledText(
            output_frame,
            font=("Consolas", 9),
            bg="#1E1E1E",
            fg="#D4D4D4",
            state=tk.DISABLED
        )
        self.diag_log.pack(fill=tk.BOTH, expand=True)

        # Initial instruction
        self.log_diag("Test suite ready. Select a test category to run.\n")
        self.log_diag("\nTest Categories:\n")
        self.log_diag("  • Basic Health - Quick system validation\n")
        self.log_diag("  • Unit Tests - Component-level testing\n")
        self.log_diag("  • Smoke Tests - Fast integration checks\n")
        self.log_diag("  • Full Suite - Comprehensive testing (may take several minutes)\n")

    def run_health_check(self):
        """Run basic system health check"""
        self.log_diag("Running system health check...", clear=True)

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

    def run_vector_validation(self):
        """Run vector store validation"""
        self.log_diag("Running vector store validation...", clear=True)

        def _run():
            script = self.script_dir / "src" / "utils" / "verify_vector_store.py"
            try:
                process = subprocess.Popen(
                    [sys.executable, str(script)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=str(self.script_dir)
                )

                for line in process.stdout:
                    self.root.after(0, lambda l=line: self.log_diag(l.rstrip(), append=True))

                process.wait()

                if process.returncode == 0:
                    self.root.after(0, lambda: self.log_diag("\n[SUCCESS] Vector store is valid", append=True))
                else:
                    self.root.after(0, lambda: self.log_diag("\n[WARNING] Vector store issues detected", append=True))

            except Exception as e:
                self.root.after(0, lambda err=str(e): self.log_diag(f"\nError: {err}", append=True))

        threading.Thread(target=_run, daemon=True).start()

    def run_test_suite(self, suite_name):
        """Run specific test suite"""
        self.log_diag(f"Running {suite_name} test suite...", clear=True)

        def _run():
            test_file_map = {
                "deployment": "tests/test_deployment_detection.py",
                "update": "tests/test_update_integration.py",
                "all": "tests/run_tests.py"
            }

            test_file = self.script_dir / test_file_map.get(suite_name, "tests/run_tests.py")

            if not test_file.exists():
                self.root.after(0, lambda: self.log_diag(f"\n[ERROR] Test file not found: {test_file}", append=True))
                return

            try:
                self.root.after(0, lambda: self.log_diag(f"Test file: {test_file}\n", append=True))

                process = subprocess.Popen(
                    [sys.executable, str(test_file)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=str(self.script_dir)
                )

                for line in process.stdout:
                    self.root.after(0, lambda l=line: self.log_diag(l.rstrip(), append=True))

                process.wait()

                if process.returncode == 0:
                    self.root.after(0, lambda: self.log_diag("\n[SUCCESS] All tests passed!", append=True))
                else:
                    self.root.after(0, lambda: self.log_diag(f"\n[FAILED] Tests failed with exit code {process.returncode}", append=True))

            except Exception as e:
                self.root.after(0, lambda err=str(e): self.log_diag(f"\nError: {err}", append=True))

        threading.Thread(target=_run, daemon=True).start()

    def run_gui_smoke_test(self):
        """Run GUI smoke test"""
        self.log_diag("Running GUI smoke test...", clear=True)

        def _run():
            test_file = self.script_dir / "tests" / "test_gui_smoke.py"

            if not test_file.exists():
                self.root.after(0, lambda: self.log_diag(f"\n[ERROR] Test file not found: {test_file}", append=True))
                return

            try:
                process = subprocess.Popen(
                    [sys.executable, str(test_file)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=str(self.script_dir)
                )

                for line in process.stdout:
                    self.root.after(0, lambda l=line: self.log_diag(l.rstrip(), append=True))

                process.wait()

                if process.returncode == 0:
                    self.root.after(0, lambda: self.log_diag("\n[SUCCESS] GUI smoke test passed", append=True))
                else:
                    self.root.after(0, lambda: self.log_diag(f"\n[FAILED] GUI smoke test failed", append=True))

            except Exception as e:
                self.root.after(0, lambda err=str(e): self.log_diag(f"\nError: {err}", append=True))

        threading.Thread(target=_run, daemon=True).start()

    def run_import_smoke_test(self):
        """Run import smoke test"""
        self.log_diag("Running module import smoke test...", clear=True)

        def _run():
            self.root.after(0, lambda: self.log_diag("Testing core module imports...\n", append=True))

            test_imports = [
                ("Core Query Engine", "src.core.hybrid_query", "HybridQueryEngine"),
                ("Definition Extractor", "src.core.definition_extractor", "DefinitionExtractor"),
                ("Query Intent", "src.core.query_intent", "QueryIntentAnalyzer"),
                ("Deployment Detector", "src.utils.deployment_detector", "DeploymentDetector"),
                ("Source Manager", "src.utils.source_manager", "SourceManager"),
                ("Config Manager", "src.utils.config_manager", "ConfigManager"),
            ]

            passed = 0
            failed = 0

            for name, module_path, class_name in test_imports:
                try:
                    # Try importing
                    parts = module_path.split('.')
                    module = __import__(module_path)
                    for part in parts[1:]:
                        module = getattr(module, part)

                    # Try accessing class
                    cls = getattr(module, class_name)

                    self.root.after(0, lambda n=name: self.log_diag(f"  ✓ {n}", append=True))
                    passed += 1
                except Exception as e:
                    self.root.after(0, lambda n=name, err=str(e): self.log_diag(f"  ✗ {n}: {err}", append=True))
                    failed += 1

            self.root.after(0, lambda p=passed, f=failed: self.log_diag(f"\n[RESULT] {p} passed, {f} failed", append=True))

            if failed == 0:
                self.root.after(0, lambda: self.log_diag("[SUCCESS] All imports successful", append=True))
            else:
                self.root.after(0, lambda: self.log_diag("[WARNING] Some imports failed", append=True))

        threading.Thread(target=_run, daemon=True).start()

    def build_config_tab(self):
        # Create scrollable container using Responsive helper
        outer_frame, frame = Responsive.make_scrollable(self.tab_config)
        
        # Add padding wrapper for aesthetic
        content_frame = ttk.Frame(frame, padding=20)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Instructions
        ttk.Label(content_frame, text="Configure your Anthropic API key, UE5 Engine paths, and models.", font=Theme.FONT_NORMAL).pack(anchor=tk.W, pady=(0, 15))

        # UI Appearance Section (New)
        ui_frame = ttk.LabelFrame(content_frame, text=" UI Appearance ", padding=15)
        ui_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(ui_frame, text="Text Scale:", font=Theme.FONT_BOLD).pack(side=tk.LEFT)

        def update_scale_label(val):
            self.lbl_scale.config(text=f"{float(val):.1f}x")

        scale_slider = ttk.Scale(ui_frame, from_=0.8, to=2.0, variable=self.text_scale_var, command=update_scale_label)
        scale_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        self.lbl_scale = ttk.Label(ui_frame, text=f"{self.text_scale_var.get():.1f}x")
        self.lbl_scale.pack(side=tk.LEFT)

        ttk.Button(ui_frame, text="Apply & Restart", command=self.apply_ui_scale).pack(side=tk.LEFT, padx=10)
        # API Key Section
        api_frame = ttk.LabelFrame(content_frame, text=" Anthropic API Key ", padding=15)
        api_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(api_frame, text="Get your API key from: https://console.anthropic.com/settings/keys", font=Theme.FONT_NORMAL, foreground="#666").pack(anchor=tk.W, pady=(0, 8))
        
        api_entry_frame = ttk.Frame(api_frame)
        api_entry_frame.pack(fill=tk.X)

        ttk.Label(api_entry_frame, text="API Key:", font=Theme.FONT_BOLD, width=10, anchor=tk.W).pack(side=tk.LEFT)
        self.api_key_entry = ttk.Entry(api_entry_frame, textvariable=self.api_key_var, show="*", width=50)
        self.api_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(api_frame, text="Show", command=self.toggle_api_visibility).pack(side=tk.LEFT)

        # Vector Storage
        ttk.Label(content_frame, text="Vector Storage Directory", font=Theme.FONT_BOLD).pack(anchor=tk.W, pady=(0,5))
        vec_frame = ttk.Frame(content_frame)
        vec_frame.pack(fill=tk.X, pady=(0, 20))
        ttk.Entry(vec_frame, textvariable=self.vector_store_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(vec_frame, text="Browse...", command=self.browse_vector_store).pack(side=tk.LEFT)
        
        # UE5 Path Section
        path_frame = ttk.LabelFrame(content_frame, text=" UE5 Engine Path ", padding=15)
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
            font=("Arial", 8),
            fg="#666",
            bg=Theme.BG_LIGHT,
            anchor=tk.W
        )
        self.engine_source_label.pack(fill=tk.X, pady=(5, 0))
        self._update_engine_source_indicator()

        # Model Selection Section
        model_frame = ttk.LabelFrame(content_frame, text=" Model Settings ", padding=15)
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
        gpu_frame = ttk.LabelFrame(content_frame, text=" GPU Optimization ", padding=15)
        gpu_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(gpu_frame, text="Embedding Batch Size:", font=Theme.FONT_BOLD).pack(anchor=tk.W, pady=5)
        ttk.Label(gpu_frame, text="RTX 5090: Use 8-16 | RTX 4090/3090: Use 32+ | CPU: Use 1-4", font=Theme.FONT_NORMAL, foreground="#666").pack(anchor=tk.W, pady=(0, 5))
        batch_size_combo = ttk.Combobox(gpu_frame, textvariable=self.embed_batch_size_var, state='readonly')
        batch_size_combo['values'] = ('1', '2', '4', '8', '16', '32', '64')
        batch_size_combo.pack(fill=tk.X)
        ttk.Label(gpu_frame, text="Smaller batches = more stable, larger batches = faster (if no errors)", font=Theme.FONT_NORMAL, foreground="#666", wraplength=500).pack(anchor=tk.W, pady=(5, 0))

        # Action Buttons
        button_frame = tk.Frame(content_frame, bg=Theme.BG_LIGHT)
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
        config_log_frame = ttk.LabelFrame(content_frame, text=" Configuration Log ", padding=5)
        config_log_frame.pack(fill=tk.BOTH, expand=True)
        self.config_log_text = scrolledtext.ScrolledText(config_log_frame, font=Theme.FONT_MONO, height=5)
        self.config_log_text.pack(fill=tk.BOTH, expand=True)

        self.load_current_engine_path() # Load engine path initially

    def apply_ui_scale(self):
        new_scale = self.text_scale_var.get()
        LayoutMetrics().set_text_scale(new_scale)
        
        # Save to config immediately so restart uses it
        self.config_manager.set('GUI_TEXT_SCALE', f"{new_scale:.2f}")
        self.config_manager.save(self.config_manager._config)
        
        if messagebox.askyesno("Restart Required", "UI scale saved. Restart now to apply changes?"):
            self.root.destroy()
            import os
            subprocess.Popen([sys.executable, str(Path(__file__))])

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
                self.root.after(0, lambda: self.log_config("❌ API Key: Missing - Please add your Anthropic API key", append=True))
            elif not api_key.startswith("sk-ant-"):
                warnings.append("⚠️ API Key: Format looks incorrect (should start with 'sk-ant-')")
                self.root.after(0, lambda: self.log_config("⚠️ API Key: Format may be incorrect", append=True))
            else:
                self.root.after(0, lambda: self.log_config("✓ API Key: Configured", append=True))

            # 2. Test Engine Path
            engine_path = self.engine_path_var.get()
            if (not engine_path or
                "No UE5 engine detected" in engine_path or
                "{ENGINE_ROOT}" in engine_path or
                "Not detected" in engine_path or
                "Auto-detection failed" in engine_path):
                # Try auto-detection
                self.root.after(0, lambda: self.log_config("🔍 Attempting to auto-detect engine path...", append=True))
                engines = get_available_engines(self.script_dir)
                if engines:
                    first_engine = engines[0]
                    detected_path = first_engine.get('path') or first_engine.get('root')
                    if detected_path:
                        self.root.after(0, lambda p=detected_path: self.engine_path_var.set(str(p)))
                        self.root.after(0, lambda p=detected_path: self.log_config(f"✓ Engine Path: Auto-detected at {p}", append=True))
                    else:
                        issues.append("❌ Engine Path: Could not auto-detect")
                        self.root.after(0, lambda: self.log_config("❌ Engine Path: Auto-detection failed - please browse manually", append=True))
                else:
                    issues.append("❌ Engine Path: No UE5 installation found")
                    self.root.after(0, lambda: self.log_config("❌ Engine Path: No UE5 installation detected", append=True))
            else:
                # Validate existing path
                engine_dir = Path(engine_path)
                if engine_dir.exists():
                    self.root.after(0, lambda p=engine_path: self.log_config(f"✓ Engine Path: Valid ({p})", append=True))
                else:
                    issues.append(f"❌ Engine Path: Directory does not exist: {engine_path}")
                    self.root.after(0, lambda p=engine_path: self.log_config(f"❌ Engine Path: Invalid - {p} does not exist", append=True))

            # 3. Test Vector Store Directory
            vector_dir = Path(self.vector_store_var.get())
            if vector_dir.exists():
                self.root.after(0, lambda: self.log_config(f"✓ Vector Store: Directory exists", append=True))
            else:
                self.root.after(0, lambda: self.log_config(f"⚠️ Vector Store: Directory will be created on first use", append=True))
                warnings.append("⚠️ Vector Store: Directory will be created on first use")

            # 4. Test Model Settings
            embed_model = self.embed_model_var.get()
            api_model = self.api_model_var.get()
            self.root.after(0, lambda m=embed_model: self.log_config(f"✓ Embedding Model: {m}", append=True))
            self.root.after(0, lambda m=api_model: self.log_config(f"✓ API Model: {m}", append=True))

            # 5. Test Batch Size
            batch_size = self.embed_batch_size_var.get()
            try:
                bs_int = int(batch_size)
                if bs_int < 1:
                    warnings.append("⚠️ Batch Size: Very small, might be slow")
                self.root.after(0, lambda b=batch_size: self.log_config(f"✓ Batch Size: {b}", append=True))
            except:
                issues.append("❌ Batch Size: Invalid number")
                self.root.after(0, lambda: self.log_config(f"❌ Batch Size: Invalid", append=True))

            # Summary
            self.root.after(0, lambda: self.log_config("\n" + "="*50, append=True))
            if len(issues) == 0 and len(warnings) == 0:
                self.root.after(0, lambda: self.log_config("✓ All configuration checks passed!", append=True))
                self.root.after(0, lambda: messagebox.showinfo("Configuration Test", "All configuration checks passed! ✓"))
            else:
                if issues:
                    self.root.after(0, lambda c=len(issues): self.log_config(f"\n{c} issue(s) found - please fix before using", append=True))
                if warnings:
                    self.root.after(0, lambda c=len(warnings): self.log_config(f"{c} warning(s) - system may work but check recommended", append=True))

                msg = f"Configuration Test Complete:\n\n"
                if issues:
                    msg += f"❌ {len(issues)} critical issue(s) found\n"
                if warnings:
                    msg += f"⚠️ {len(warnings)} warning(s)\n"
                msg += f"\nCheck the log below for details."

                self.root.after(0, lambda m=msg: messagebox.showwarning("Configuration Test", m))

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
                # Use Phase 6 detection with validation and health scores
                installations = get_available_engines(self.script_dir, use_cache=True)

                if not installations:
                    self.root.after(0, lambda: self.log_config("! No UE5 installation detected", append=True))
                    self.root.after(0, lambda: self.show_detection_help_dialog())
                    return

                # Sort by health score (should already be sorted, but ensure)
                installations.sort(key=lambda x: x.get('health_score', 0), reverse=True)

                # Log all found installations with health info
                for inst in installations:
                    health_pct = int(inst.get('health_score', 0) * 100)
                    source = inst.get('source', 'unknown')
                    self.root.after(0, lambda v=inst['version'], s=source, h=health_pct:
                        self.log_config(f"  Found {v} ({s}) - Health: {h}%", append=True))

                if len(installations) == 1:
                    install = installations[0]
                    path = install['engine_root']
                    version = install['version']
                    health = int(install.get('health_score', 0) * 100)

                    # Warn if health is low
                    if health < 70:
                        warnings = install.get('warnings', [])
                        warn_msg = "\n".join(warnings) if warnings else "Installation may be incomplete"
                        self.root.after(0, lambda w=warn_msg: self.log_config(f"⚠ Warning: {w}", append=True))

                    self.root.after(0, lambda: self.engine_path_var.set(path))
                    self.root.after(0, lambda: self.log_config(f"✓ Selected {version} (health: {health}%)", append=True))
                else:
                    self.root.after(0, lambda: self.show_selection_dialog(installations))

            except Exception as e:
                self.root.after(0, lambda err=str(e): self.log_config(f"✗ Detection failed: {err}", append=True))
                self.root.after(0, lambda err=str(e): messagebox.showerror("Error", f"Auto-detection failed:\n{err}"))
            finally:
                self.root.after(0, lambda: self.engine_path_entry.config(state=tk.NORMAL))


        threading.Thread(target=detect, daemon=True).start()

    def _update_engine_source_indicator(self):
        """Update the visual indicator showing where the engine path came from"""
        if not hasattr(self, 'engine_source_label'):
            return

        source = getattr(self, 'engine_detection_source', 'unknown')
        is_override = getattr(self, 'engine_is_user_override', False)

        source_messages = {
            'vector_store': '📊 Detected from built index (vector store)',
            'uproject': '🎮 Detected from project file (.uproject)',
            'config': '⚙️ Loaded from configuration file',
            'auto_detect': '🔍 Auto-detected from system',
            'user_override': '👤 User override (manually set)',
            'none': '⚠️  No engine detected',
            'error': '❌ Detection error',
            'unknown': ''
        }

        message = source_messages.get(source, '')

        if is_override:
            message = '👤 User override (manually set)'
            self.engine_source_label.config(fg='#0066CC')  # Blue for override
        elif source == 'vector_store':
            self.engine_source_label.config(fg='#228B22')  # Green for vector store
        elif source in ['none', 'error']:
            self.engine_source_label.config(fg='#CC0000')  # Red for errors
        else:
            self.engine_source_label.config(fg='#666666')  # Grey for others

        self.engine_source_label.config(text=message)

    def show_detection_help_dialog(self):
        """Phase 6: Guide user through manual setup when detection fails"""
        gui_helpers.show_engine_detection_help(self.root, self.browse_engine_path)

    def show_selection_dialog(self, installations):
        dialog = tk.Toplevel(self.root)
        
        # Use Adaptive Layout Engine
        WindowManager.setup_window(
            dialog,
            "Select UE5 Version",
            target_width_pct=0.5,
            target_height_pct=0.6,
            min_w=600,
            min_h=400
        )
        
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Multiple UE5 versions found. Please select one:",
                  font=Theme.FONT_BOLD).pack(pady=10)

        # Create frame with scrollbar for installations
        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Use Listbox with detailed info
        listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set, font=Theme.FONT_NORMAL,
                             selectmode=tk.SINGLE)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)

        # Add installations with health scores
        for install in installations:
            version = install['version']
            source = install.get('source', 'unknown')
            health = int(install.get('health_score', 0) * 100)
            path = install['engine_root']

            display = f"{version} | Health: {health}% | Source: {source}"
            listbox.insert(tk.END, display)

        # Info label for selected installation
        info_label = ttk.Label(dialog, text="", font=Theme.FONT_SMALL, foreground="gray")
        info_label.pack(pady=5)

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

        # Progress Section (NEW)
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

        # Row 1: Index Management
        tk.Label(
            action_grid,
            text="Index Management:",
            font=("Arial", 10, "bold"),
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_DARK
        ).grid(row=0, column=0, sticky=tk.W, padx=(0, 20), pady=5)

        self.btn_rebuild = tk.Button(
            action_grid,
            text="🔄 Rebuild Index",
            command=self.rebuild_index,
            bg=Theme.SECONDARY,
            fg="white",
            padx=15,
            pady=8,
            relief=tk.FLAT,
            cursor="hand2"
        )
        self.btn_rebuild.grid(row=0, column=1, padx=5, pady=5)

        # Row 2: System Updates (Phase 6)
        tk.Label(
            action_grid,
            text="System Updates:",
            font=("Arial", 10, "bold"),
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_DARK
        ).grid(row=1, column=0, sticky=tk.W, padx=(0, 20), pady=5)

        tk.Label(
            action_grid,
            text="Use System Status tab for updates",
            font=("Arial", 9),
            bg=Theme.BG_LIGHT,
            fg="#7F8C8D"
        ).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        # Row 3: Verification
        tk.Label(
            action_grid,
            text="Verification:",
            font=("Arial", 10, "bold"),
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_DARK
        ).grid(row=2, column=0, sticky=tk.W, padx=(0, 20), pady=5)

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
        btn_verify.grid(row=2, column=1, padx=5, pady=5)

        # Row 4: GPU/CUDA Setup (NEW)
        tk.Label(
            action_grid,
            text="GPU Acceleration:",
            font=("Arial", 10, "bold"),
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_DARK
        ).grid(row=3, column=0, sticky=tk.W, padx=(0, 20), pady=5)

        # GPU status frame
        gpu_status_frame = tk.Frame(action_grid, bg=Theme.BG_LIGHT)
        gpu_status_frame.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)

        self.gpu_status_label = tk.Label(
            gpu_status_frame,
            text="Checking...",
            font=("Arial", 9),
            bg=Theme.BG_LIGHT,
            fg="#7F8C8D"
        )
        self.gpu_status_label.pack(side=tk.LEFT)

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

        # Check GPU status after UI is built
        self.root.after(100, self.check_gpu_status)

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
        
        # Initial check
        self.check_status()

    def cancel_or_close(self):
        if self.maint_service.current_process:
            if messagebox.askyesno("Cancel", "Cancel current operation?"):
                self.cancelled = True
                if self.maint_service.cancel_current_process():
                    self.log_maint("[CANCELLED] Operation cancelled.", append=True)
                    self.btn_rebuild.config(state=tk.NORMAL)
                    self.btn_cancel.config(text="Close")
        else:
            self.root.destroy()

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
        self.btn_rebuild.config(state=tk.DISABLED)
        self.btn_cancel.config(text="Cancel")
        self.cancelled = False

        # Reset progress bar
        self.maint_progress['value'] = 0
        self.maint_progress_label.config(text="Initializing...")
        self.maint_time_label.config(text="Estimated time: calculating...")

        import time
        start_time = time.time()

        def update_progress(value, label_text):
            """Update progress bar and label"""
            self.maint_progress['value'] = value
            self.maint_progress_label.config(text=label_text)

            # Calculate time estimate
            elapsed = time.time() - start_time
            if value > 0:
                estimated_total = elapsed / (value / 100)
                remaining = estimated_total - elapsed
                if remaining > 60:
                    time_str = f"{remaining / 60:.1f} minutes remaining"
                else:
                    time_str = f"{remaining:.0f} seconds remaining"
                self.maint_time_label.config(text=f"Elapsed: {elapsed:.0f}s | {time_str}")

        def parse_progress(line):
            """Parse build output to determine progress percentage"""
            import re

            # Progress stages and their percentage ranges
            # Stage 1: Discovery (0-10%)
            if "Discovering" in line or "Finding" in line:
                return 5, "Discovering source files..."
            if "Found" in line and "files" in line:
                return 10, f"Discovered files: {line.strip()}"

            # Stage 2: Chunking (10-30%)
            if "Chunking" in line or "Processing" in line:
                match = re.search(r'(\d+)/(\d+)', line)
                if match:
                    current, total = int(match.group(1)), int(match.group(2))
                    progress = 10 + (current / total * 20) if total > 0 else 15
                    return progress, f"Processing files ({current}/{total})..."
                return 20, "Processing files..."

            # Stage 3: Embedding generation (30-90%)
            if "Embedding" in line or "batch" in line.lower():
                match = re.search(r'(\d+)/(\d+)', line)
                if match:
                    current, total = int(match.group(1)), int(match.group(2))
                    progress = 30 + (current / total * 60) if total > 0 else 60
                    return progress, f"Generating embeddings ({current}/{total})..."
                # Alternative progress pattern
                match = re.search(r'(\d+)%', line)
                if match:
                    pct = int(match.group(1))
                    progress = 30 + (pct * 0.6)
                    return progress, f"Generating embeddings ({pct}%)..."
                return 60, "Generating embeddings..."

            # Stage 4: Saving (90-100%)
            if "Saving" in line or "Writing" in line:
                return 95, "Saving vector store..."
            if "Complete" in line or "SUCCESS" in line or "Done" in line:
                return 100, "Complete!"

            return None, None

        def on_complete(success, message):
            self.root.after(0, lambda: self.btn_rebuild.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.btn_cancel.config(text="Close"))
            if success:
                self.root.after(0, lambda: update_progress(100, "Index rebuild complete!"))
                self.root.after(0, lambda: self.log_maint("[SUCCESS] Index rebuild complete.", append=True))
                self.root.after(0, self.check_status)
                
                elapsed = time.time() - start_time
                elapsed_str = f"{elapsed / 60:.1f} minutes" if elapsed > 60 else f"{elapsed:.0f} seconds"
                self.root.after(0, lambda e=elapsed_str: self.maint_time_label.config(text=f"Completed in {e}"))
            else:
                if not self.cancelled:
                    self.root.after(0, lambda: update_progress(0, "Failed"))
                    self.root.after(0, lambda m=message: self.log_maint(f"\n[ERROR] {m}", append=True))

        def log_with_progress(line):
            stripped = line.strip()
            self.root.after(0, lambda: self.log_maint(stripped, append=True))
            
            prog, label = parse_progress(stripped)
            if prog is not None:
                self.root.after(0, lambda p=prog, l=label: update_progress(p, l))

        script = self.script_dir / "tools" / "rebuild-index.bat"
        self.maint_service.run_task(
            task_name="Index Rebuild",
            command=[str(script), "--verbose", "--force"],
            callback=on_complete,
            log_callback=log_with_progress
        )

    def update_tool(self):
        if not messagebox.askyesno("Confirm", "Update tool from repository?"):
            return
            
        self.log_maint("Updating tool...", clear=True)
        script = self.script_dir / "tools" / "update.bat"
        
        self.maint_service.run_task(
            task_name="Tool Update",
            command=[str(script)],
            callback=lambda success, msg: self.root.after(0, lambda: self.log_maint(f"\n[DONE] {msg}", append=True)),
            log_callback=lambda line: self.root.after(0, lambda l=line: self.log_maint(l.rstrip(), append=True))
        )


    def verify_installation(self):
        """Run comprehensive installation verification using MaintenanceService"""
        self.log_maint("Running installation verification...", clear=True)
        verify_script = self.script_dir / "src" / "utils" / "verify_installation.py"

        if not verify_script.exists():
            self.log_maint("[ERROR] Verification script not found")
            return

        def on_complete(success, message):
            if success:
                self.root.after(0, lambda: self.log_maint(f"\n[SUCCESS] {message}"))
            else:
                self.root.after(0, lambda: self.log_maint(f"\n[WARNING] {message}"))

        self.maint_service.run_task(
            task_name="Installation Verification",
            command=[sys.executable, str(verify_script)],
            callback=on_complete,
            log_callback=lambda line: self.root.after(0, lambda: self.log_maint(line.rstrip(), append=True))
        )

    def check_gpu_status(self):
        """Check GPU status and update the maintenance tab UI."""
        def _check():
            try:
                gpu_summary = get_gpu_summary()

                if gpu_summary.get('has_nvidia_gpu'):
                    gpu_name = gpu_summary.get('gpu_name', 'Unknown GPU')
                    cuda_installed = gpu_summary.get('cuda_installed')
                    cuda_compatible = gpu_summary.get('cuda_compatible', False)
                    needs_cuda = gpu_summary.get('needs_cuda_install', False)

                    if cuda_installed and cuda_compatible:
                        status = f"✓ {gpu_name} with CUDA {cuda_installed}"
                        color = Theme.SUCCESS
                        enable_setup = False
                    elif cuda_installed and not cuda_compatible:
                        status = f"⚠ {gpu_name} - CUDA {cuda_installed} (outdated)"
                        color = "#FFC107"
                        enable_setup = True
                    else:
                        cuda_required = gpu_summary.get('cuda_required', 'Unknown')
                        status = f"⚠ {gpu_name} - CUDA {cuda_required}+ required"
                        color = "#FFC107"
                        enable_setup = True

                    self.root.after(0, lambda: self.gpu_status_label.config(text=status, fg=color))
                    self.root.after(0, lambda e=enable_setup:
                        self.btn_cuda_setup.config(state=tk.NORMAL if e else tk.DISABLED))

                    # Store GPU info for setup
                    self.gpu_info = gpu_summary
                else:
                    self.root.after(0, lambda: self.gpu_status_label.config(
                        text="No NVIDIA GPU detected (CPU mode)", fg="#7F8C8D"))
                    self.root.after(0, lambda: self.btn_cuda_setup.config(state=tk.DISABLED))
                    self.gpu_info = None

            except Exception as e:
                self.root.after(0, lambda: self.gpu_status_label.config(
                    text=f"Error checking GPU: {e}", fg=Theme.ERROR))
                self.root.after(0, lambda: self.btn_cuda_setup.config(state=tk.DISABLED))

        threading.Thread(target=_check, daemon=True).start()

    def setup_cuda(self):
        """Launch CUDA setup wizard (Phase 6)"""
        if self.maint_tab_view:
            # Delegate to the view if available
            # Note: View currently calls back to dashboard.setup_cuda, so we need to avoid recursion loop
            # But the view BUTTON calls dashboard.setup_cuda.
            # We should move the LOGIC to the view or service.
            # For now, let's keep the logic here but update it to use the view's widgets if possible
            pass
        
        # Original logic adapted to check for view
        if not hasattr(self, 'gpu_info') or not self.gpu_info:
            messagebox.showerror("Error", "GPU information not available. Please refresh GPU status.")
            return

        cuda_required = self.gpu_info.get('cuda_required', 'Unknown')
        gpu_name = self.gpu_info.get('gpu_name', 'Unknown GPU')
        download_url = self.gpu_info.get('download_url', None)

        if not download_url:
            messagebox.showerror("Error", "CUDA download URL not available for your GPU.")
            return

        # Confirm with user
        response = messagebox.askyesno(
            "CUDA Setup",
            f"This will download and install CUDA Toolkit {cuda_required} for your {gpu_name}.\n\n"
            f"This may take 15-30 minutes and requires administrator privileges.\n\n"
            f"Continue with CUDA installation?"
        )

        if not response:
            return

        # Log to maintenance tab
        if self.maint_tab_view:
            self.maint_tab_view.log_maint(f"Starting CUDA {cuda_required} setup for {gpu_name}...", clear=True)
            self.maint_tab_view.btn_cuda_setup.config(state=tk.DISABLED)
            
            # Update progress display
            self.maint_tab_view.maint_progress['value'] = 0
            self.maint_tab_view.maint_progress_label.config(text="Downloading CUDA Toolkit...")
            self.maint_tab_view.maint_time_label.config(text="This may take 15-30 minutes...")
        
        def _setup():
            try:
                def download_callback(downloaded, total):
                    if self.maint_tab_view and total > 0:
                        percent = (downloaded / total) * 50
                        self.root.after(0, lambda p=percent: self.maint_tab_view.maint_progress.config(value=p))
                        size_mb = downloaded / (1024 * 1024)
                        total_mb = total / (1024 * 1024)
                        self.root.after(0, lambda d=size_mb, t=total_mb: 
                            self.maint_tab_view.maint_progress_label.config(text=f"Downloading: {d:.1f} / {t:.1f} MB"))

                def install_callback(message):
                    if self.maint_tab_view:
                        self.root.after(0, lambda m=message: self.maint_tab_view.log_maint(m, append=True))
                        if "Installing" in message:
                            self.root.after(0, lambda: self.maint_tab_view.maint_progress.config(value=60))
                            self.root.after(0, lambda: self.maint_tab_view.maint_progress_label.config(text="Installing CUDA..."))
                        elif "Complete" in message or "Success" in message:
                            self.root.after(0, lambda: self.maint_tab_view.maint_progress.config(value=100))
                            self.root.after(0, lambda: self.maint_tab_view.maint_progress_label.config(text="Installation complete!"))

                success = install_cuda_with_progress(
                    url=download_url,
                    download_callback=download_callback,
                    install_callback=install_callback
                )

                if success:
                    if self.maint_tab_view:
                        self.root.after(0, lambda: self.maint_tab_view.log_maint("\n[SUCCESS] CUDA installation complete!", append=True))
                    
                    self.root.after(0, lambda: messagebox.showinfo(
                        "CUDA Installed",
                        f"CUDA Toolkit {cuda_required} has been installed.\n\n"
                        "You may need to restart your terminal or IDE for changes to take effect."
                    ))
                    # Refresh GPU status
                    self.root.after(500, self.check_gpu_status)
                else:
                    if self.maint_tab_view:
                        self.root.after(0, lambda: self.maint_tab_view.log_maint("\n[ERROR] CUDA installation failed", append=True))
                    
                    self.root.after(0, lambda: messagebox.showerror(
                        "Installation Failed",
                        "CUDA installation failed. Check the log for details.\n\n"
                        "You may need to download and install CUDA manually from:\n"
                        "https://developer.nvidia.com/cuda-downloads"
                    ))

            except Exception as e:
                if self.maint_tab_view:
                    self.root.after(0, lambda err=str(e): self.maint_tab_view.log_maint(f"\n[ERROR] {err}", append=True))
                    self.root.after(0, lambda: self.maint_tab_view.maint_progress_label.config(text="Error"))
                    self.root.after(0, lambda: self.maint_tab_view.maint_progress.config(value=0))
            finally:
                if self.maint_tab_view:
                    self.root.after(0, lambda: self.maint_tab_view.btn_cuda_setup.config(state=tk.NORMAL))
                    self.root.after(0, lambda: self.maint_tab_view.maint_time_label.config(text=""))

        import threading
        threading.Thread(target=_setup, daemon=True).start()

def main():
    root = tk.Tk()
    app = UnifiedDashboard(root)
    root.mainloop()

if __name__ == "__main__":
    main()