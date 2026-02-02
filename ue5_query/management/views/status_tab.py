import tkinter as tk
from tkinter import ttk, scrolledtext
import sys
from pathlib import Path

# Try to import Theme, handle missing imports gracefully if run standalone
try:
    from ue5_query.utils.gui_theme import Theme
except ImportError:
    # If run standalone or during dev
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
        from ue5_query.utils.gui_theme import Theme
    except ImportError:
        Theme = None

class StatusTab:
    """
    Handles the System Status tab logic and layout.
    """
    def __init__(self, parent_frame, dashboard):
        """
        Args:
            parent_frame: The ttk.Frame to build the tab into
            dashboard: Reference to the main UnifiedDashboard instance (controller)
        """
        self.frame = parent_frame
        self.dashboard = dashboard
        self.deployment_detector = dashboard.deployment_detector
        
        self.build_ui()

    def build_ui(self):
        """Build the UI components"""
        frame = ttk.Frame(self.frame, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Environment Type Section
        self._build_env_section(frame)

        # Deployment/Dev Repo Connection Section
        is_dev = self.deployment_detector.is_dev_repo()
        is_deployed = self.deployment_detector.is_deployed()

        if is_deployed:
            self._build_deployed_status(frame)
        elif is_dev:
            self._build_dev_repo_status(frame)

        # Update Section
        self._build_update_section(frame)

    def _build_env_section(self, parent):
        env_frame = ttk.LabelFrame(parent, text=" Environment Information ", padding=15)
        env_frame.pack(fill=tk.X, pady=(0, 15))

        # Environment type detection
        is_dev = self.deployment_detector.is_dev_repo()
        is_deployed = self.deployment_detector.is_deployed()
        is_valid = self.deployment_detector.env_info.is_valid

        # Environment type display
        env_type_frame = tk.Frame(env_frame, bg=Theme.BG_LIGHT)
        env_type_frame.pack(fill=tk.X, pady=5)

        env_type_label = tk.Label(
            env_type_frame,
            text="Environment Type:",
            font=("Arial", 10, "bold"),
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
            font=("Arial", 10),
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
            font=("Arial", 10),
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
            font=("Arial", 10, "bold"),
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_DARK
        )
        root_label.pack(side=tk.LEFT, padx=(0, 10))

        root_value = tk.Label(
            root_frame,
            text=str(self.deployment_detector.root),
            font=("Arial", 9),
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
                font=("Arial", 10, "bold"),
                bg=Theme.BG_LIGHT,
                fg="#F44336"
            )
            issues_label.pack(anchor=tk.W)

            for issue in self.deployment_detector.env_info.issues:
                issue_text = tk.Label(
                    issues_frame,
                    text=f"  • {issue}",
                    font=("Arial", 9),
                    bg=Theme.BG_LIGHT,
                    fg="#F44336"
                )
                issue_text.pack(anchor=tk.W)

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
            from ue5_query.utils.engine_helper import find_uproject_in_directory, get_engine_version_from_uproject, detect_engine_from_vector_store

            uproject = find_uproject_in_directory(self.dashboard.script_dir)
            if uproject:
                project_version = get_engine_version_from_uproject(str(uproject))
                if project_version:
                    # Use smart detection to get actual indexed version
                    indexed_version = None
                    detection_source = "config"

                    # Try vector store first (most accurate)
                    vector_engine = detect_engine_from_vector_store(self.dashboard.script_dir)
                    if vector_engine:
                        version_str = vector_engine.get('version', '')
                        import re
                        match = re.search(r'(\d+\.\d+)', version_str)
                        if match:
                            indexed_version = match.group(1)
                            detection_source = "vector_store"

                    # Fallback to config if no vector store
                    if not indexed_version:
                        config_file = self.dashboard.script_dir / "config" / ".env"
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
                        warning_text.pack(side=tk.LEFT, padx=5, pady=5)
        except Exception as e:
            print(f"Version check error: {e}")

    def _build_dev_repo_status(self, parent_frame):
        """Build status section for development repositories"""
        dev_frame = ttk.LabelFrame(parent_frame, text=" Dev Repo Information ", padding=15)
        dev_frame.pack(fill=tk.X, pady=(0, 15))

        # Check deployments registry
        try:
            from ue5_query.utils.deployment_detector import DeploymentRegistry
            registry = DeploymentRegistry(self.dashboard.script_dir)
            deployments = registry.get_all_deployments()

            count_frame = tk.Frame(dev_frame, bg=Theme.BG_LIGHT)
            count_frame.pack(fill=tk.X, pady=5)

            count_label = tk.Label(
                count_frame,
                text="Active Deployments:",
                font=("Arial", 10, "bold"),
                bg=Theme.BG_LIGHT,
                fg=Theme.TEXT_DARK
            )
            count_label.pack(side=tk.LEFT, padx=(0, 10))

            count_value = tk.Label(
                count_frame,
                text=str(len(deployments)),
                font=("Arial", 10),
                bg=Theme.BG_LIGHT,
                fg=Theme.PRIMARY
            )
            count_value.pack(side=tk.LEFT)

            if deployments:
                list_frame = tk.Frame(dev_frame, bg=Theme.BG_LIGHT, pady=5)
                list_frame.pack(fill=tk.X)

                for deploy in deployments[:3]:  # Show top 3
                    tk.Label(
                        list_frame,
                        text=f"• {deploy.path}",
                        font=("Arial", 9),
                        bg=Theme.BG_LIGHT,
                        fg="#7F8C8D"
                    ).pack(anchor=tk.W)

                if len(deployments) > 3:
                    tk.Label(
                        list_frame,
                        text=f"... and {len(deployments) - 3} more",
                        font=("Arial", 9, "italic"),
                        bg=Theme.BG_LIGHT,
                        fg="#7F8C8D"
                    ).pack(anchor=tk.W)

        except Exception as e:
            tk.Label(dev_frame, text=f"Error reading registry: {e}", fg="red").pack()

    def _build_update_section(self, parent_frame):
        update_frame = ttk.LabelFrame(parent_frame, text=" Update System ", padding=15)
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
                command=self.run_update_wrapper,
                bg=Theme.SECONDARY,
                fg="white",
                font=("Arial", 10, "bold"),
                padx=20,
                pady=8,
                relief=tk.FLAT,
                cursor="hand2"
            )
            update_btn.pack(side=tk.LEFT, padx=(0, 10))

            check_btn = tk.Button(
                btn_frame,
                text="🔍 Check for Updates",
                command=lambda: self.run_update_wrapper(dry_run=True),
                bg=Theme.BG_DARK,
                fg="white",
                font=("Arial", 10),
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
                    command=lambda: self.run_update_wrapper(force_source="local"),
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
                command=lambda: self.run_update_wrapper(force_source="remote"),
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
        log_frame = ttk.LabelFrame(parent_frame, text=" Update Log ", padding=10)
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

    def log_status(self, msg, tag=""):
        """Helper to append to status log"""
        self.status_log.config(state=tk.NORMAL)
        self.status_log.insert(tk.END, msg + "\n", tag)
        self.status_log.see(tk.END)
        self.status_log.config(state=tk.DISABLED)
        
    def clear_log(self):
        self.status_log.config(state=tk.NORMAL)
        self.status_log.delete("1.0", tk.END)
        self.status_log.config(state=tk.DISABLED)

    def run_update_wrapper(self, dry_run=False, force_source=None):
        self.dashboard.update_service.run_update_process(
            dry_run=dry_run,
            force_source=force_source,
            log_func=self.log_status,
            clear_log_func=self.clear_log
        )
