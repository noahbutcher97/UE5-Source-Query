"""
UE5 Source Query Tool - Unified Management Dashboard
Central hub for configuration, health checks, and system management.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sys
import threading
from pathlib import Path

# Determine script dir relative to package location for resource loading
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent

from ue5_query.utils.gui_theme import Theme
from ue5_query.utils.gui_layout import WindowManager, LayoutMetrics
from ue5_query.utils.config_manager import ConfigManager
from ue5_query.utils.source_manager import SourceManager
from ue5_query.utils.deployment_detector import DeploymentDetector
from ue5_query.utils import gui_helpers

# Services
from ue5_query.management.services import UpdateService, SearchService, MaintenanceService
from ue5_query.ai.service import IntelligenceService

# Views
from ue5_query.management.views.status_tab import StatusTab
from ue5_query.management.views.query_tab import QueryTab
from ue5_query.management.views.assistant_view import AssistantView
from ue5_query.management.views.file_search_tab import FileSearchTab
from ue5_query.management.views.config_tab import ConfigTab
from ue5_query.management.views.source_tab import SourceManagerTab
from ue5_query.management.views.diagnostics_tab import DiagnosticsTab
from ue5_query.management.views.maintenance_tab import MaintenanceTab
from ue5_query.management.views.deployment_tab import DeploymentManagerTab

class UnifiedDashboard:
    def __init__(self, root):
        self.root = root
        self._after_ids = {} # Track scheduled tasks for cleanup
        
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
        
        # Ensure tools are importable
        sys.path.insert(0, str(self.script_dir))
        
        self.source_manager = SourceManager(self.script_dir)
        self.config_manager = ConfigManager(self.script_dir)
        
        # Initialize Services
        self.update_service = UpdateService(self.root, self.script_dir)
        self.search_service = SearchService(self.script_dir, self.config_manager)
        self.maint_service = MaintenanceService(self.script_dir)
        self.ai_service = IntelligenceService(self.config_manager)

        # Deployment detection
        self.deployment_detector = DeploymentDetector(self.script_dir)

        # Configuration variables (Shared state)
        self.api_key_var = tk.StringVar(value=self.config_manager.get('ANTHROPIC_API_KEY', ''))
        self.engine_path_var = tk.StringVar(value=self.config_manager.get('UE_ENGINE_ROOT', ''))
        self.vector_store_var = tk.StringVar(value=self.config_manager.get('VECTOR_OUTPUT_DIR', str(self.script_dir / 'data')))
        self.embed_model_var = tk.StringVar(value=self.config_manager.get('EMBED_MODEL', 'microsoft/unixcoder-base'))
        self.api_model_var = tk.StringVar(value=self.config_manager.get('ANTHROPIC_MODEL', 'claude-3-haiku-20240307'))
        self.embed_batch_size_var = tk.StringVar(value=self.config_manager.get('EMBED_BATCH_SIZE', '16'))
        self.text_scale_var = tk.DoubleVar(value=float(self.config_manager.get('GUI_TEXT_SCALE', LayoutMetrics().text_scale)))
        self.query_scope_var = tk.StringVar(value="engine")
        self.use_reranker_var = tk.BooleanVar(value=False)

        # Filter variables
        self.filter_entity_type_var = tk.StringVar(value="")
        self.filter_macro_var = tk.StringVar(value="")
        self.filter_file_type_var = tk.StringVar(value="")
        self.filter_boost_macros_var = tk.BooleanVar(value=False)

        # State for engine detection
        self.engine_detection_source = 'unknown'
        self.engine_is_user_override = False

        self.create_layout()
        
        # Load engine path from source_manager after layout creation
        self._load_initial_engine_path()

        # Start periodic check for update notifications
        self.update_service.start_check()

        # Check for first run (missing index)
        self.safe_after(1000, self._check_first_run, 'first_run')

    def safe_after(self, ms, func, name=None):
        """Schedule a task and track it for cleanup"""
        try:
            if self.root.winfo_exists():
                after_id = self.root.after(ms, func)
                if name:
                    self._after_ids[name] = after_id
                return after_id
        except (tk.TclError, AttributeError):
            pass
        return None

    def cleanup(self):
        """Cancel all pending background tasks"""
        for task_name, after_id in self._after_ids.items():
            try:
                self.root.after_cancel(after_id)
            except:
                pass
        self._after_ids.clear()

    def destroy(self):
        """Safely destroy the dashboard and its root window"""
        self.cleanup()
        try:
            if self.root.winfo_exists():
                self.root.destroy()
        except:
            pass

    def create_layout(self):
        # Header
        Theme.create_header(self.root, "UE5 Source Query", "Management Dashboard")
        
        # Status Bar
        self._build_status_bar()
        
        # Main container
        container = tk.Frame(self.root, bg=Theme.BG_LIGHT)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Tabs
        self.notebook = ttk.Notebook(container)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 1. System Status Tab
        self.tab_status = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_status, text="System Status")
        self.status_view = StatusTab(self.tab_status, self)

        # 1b. Deployments Tab (Dev Only)
        try:
            from tools.update import is_dev_repo
            if is_dev_repo(self.script_dir):
                self.tab_deploy = ttk.Frame(self.notebook)
                self.notebook.add(self.tab_deploy, text="Deployments (Dev)")
                self.deploy_view = DeploymentManagerTab(self.tab_deploy, self)
        except ImportError:
            pass # Not in dev environment or tools missing

        # 2. Query Tab (Main Interface)
        self.tab_query = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_query, text="Query")
        self.query_view = QueryTab(self.tab_query, self)

        # 3. AI Assistant Tab
        self.tab_assistant = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_assistant, text="AI Assistant")
        # Pass search_service to enable RAG features
        self.assistant_view = AssistantView(self.notebook, self.ai_service, self.search_service)
        # Reparent the view's frame to our tab
        self.assistant_view.frame.pack(in_=self.tab_assistant, fill=tk.BOTH, expand=True)

        # 4. File Search Tab
        self.tab_file_search = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_file_search, text="File Search")
        self.file_search_view = FileSearchTab(self.tab_file_search, self)

        # 5. Configuration Tab
        self.tab_config = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_config, text="Configuration")
        self.config_view = ConfigTab(self.tab_config, self)

        # 6. Source Manager Tab
        self.tab_sources = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_sources, text="Source Manager")
        self.sources_view = SourceManagerTab(self.tab_sources, self)

        # 7. Diagnostics Tab
        self.tab_diagnostics = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_diagnostics, text="Diagnostics")
        self.diagnostics_view = DiagnosticsTab(self.tab_diagnostics, self)

        # 8. Maintenance Tab
        self.tab_maintenance = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_maintenance, text="Maintenance")
        self.maintenance_view = MaintenanceTab(self.tab_maintenance, self)

    def _build_status_bar(self):
        bar_frame = tk.Frame(self.root, bg=Theme.BG_LIGHT)
        bar_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        # Indicators
        self.status_labels = {}
        
        # Helper to create indicator
        def _create_indicator(parent, key, label):
            # Frame for visual grouping
            f = tk.Frame(parent, bg="#FFFFFF", highlightbackground="#E0E0E0", highlightthickness=1)
            f.pack(side=tk.LEFT, padx=(0, 15), ipadx=8, ipady=4)
            
            # Dot
            dot = tk.Label(f, text="●", fg="#BDBDBD", bg="#FFFFFF", font=("Arial", 12))
            dot.pack(side=tk.LEFT, padx=(0, 5))
            
            # Text
            tk.Label(f, text=label, bg="#FFFFFF", font=("Segoe UI", 9, "bold"), fg="#424242").pack(side=tk.LEFT)
            return dot

        self.status_labels["engine"] = _create_indicator(bar_frame, "engine", "Engine Source")
        self.status_labels["index"] = _create_indicator(bar_frame, "index", "Search Index")
        self.status_labels["ai"] = _create_indicator(bar_frame, "ai", "AI Service")

        # Trigger update loop
        self.update_status_lights()

    def update_status_lights(self):
        # 1. Engine
        path = self.engine_path_var.get()
        if path and Path(path).exists():
            # Check for Engine/Source to be sure
            if (Path(path) / "Source").exists() or (Path(path) / "Engine" / "Source").exists():
                self.status_labels["engine"].config(fg="#4CAF50") # Green
            else:
                self.status_labels["engine"].config(fg="#FFC107") # Yellow (Exists but suspicious)
        else:
            self.status_labels["engine"].config(fg="#F44336") # Red

        # 2. Index
        store = self.script_dir / "data" / "vector_store.npz"
        if store.exists():
            self.status_labels["index"].config(fg="#4CAF50")
        else:
            self.status_labels["index"].config(fg="#F44336")

        # 3. AI
        key = self.api_key_var.get()
        if key and len(key) > 10 and not key.startswith("your_api"):
            self.status_labels["ai"].config(fg="#4CAF50")
        else:
            self.status_labels["ai"].config(fg="#F44336")

        # Schedule next check (every 3s)
        self.safe_after(3000, self.update_status_lights, 'status_lights')

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
                # Trigger rebuild via view
                self.root.after(500, self.maintenance_view.rebuild_index)

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

    def apply_ui_scale(self):
        new_scale = self.text_scale_var.get()
        LayoutMetrics().set_text_scale(new_scale)
        
        # Save to config immediately so restart uses it
        self.config_manager.set('GUI_TEXT_SCALE', f"{new_scale:.2f}")
        self.config_manager.save(self.config_manager._config)
        
        if messagebox.askyesno("Restart Required", "UI scale saved. Restart now to apply changes?"):
            self.root.destroy()
            import os
            import subprocess
            subprocess.Popen([sys.executable, str(Path(__file__))])

if __name__ == "__main__":
    # Allow running dashboard directly
    root = tk.Tk()
    app = UnifiedDashboard(root)
    root.mainloop()
