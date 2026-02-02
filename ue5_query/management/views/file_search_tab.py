import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import sys
from pathlib import Path

# Try to import Theme, handle missing imports gracefully
try:
    from ue5_query.utils.gui_theme import Theme
    from ue5_query.utils.ue_path_utils import UEPathUtils
except ImportError:
    # If run standalone
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
        from ue5_query.utils.gui_theme import Theme
        from ue5_query.utils.ue_path_utils import UEPathUtils
    except ImportError:
        Theme = None

class FileSearchTab:
    """
    Handles the File Search tab logic and layout.
    """
    def __init__(self, parent_frame, dashboard):
        """
        Args:
            parent_frame: The ttk.Frame to build the tab into
            dashboard: Reference to the main UnifiedDashboard instance
        """
        self.frame = parent_frame
        self.dashboard = dashboard
        self.search_service = dashboard.search_service
        self.embed_model_var = dashboard.embed_model_var

        self.build_ui()

    def build_ui(self):
        """Build the 'Super File Search' tab for rapid file/path lookup"""
        frame = ttk.Frame(self.frame, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Header/Instructions
        ttk.Label(frame, text="Super File Search", font=("Arial", 14, "bold")).pack(anchor=tk.W)
        ttk.Label(frame, text="Find where a class, struct, or concept is defined. Get includes and Build.cs dependencies instantly.", 
                  font=("Arial", 10), foreground="#666").pack(anchor=tk.W, pady=(0, 15))

        # Input Area
        input_frame = tk.Frame(frame, bg=Theme.BG_LIGHT)
        input_frame.pack(fill=tk.X, pady=(0, 15))

        self.file_query_entry = ttk.Entry(input_frame, font=("Arial", 12))
        self.file_query_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.file_query_entry.bind("<Return>", lambda e: self.perform_file_search())

        btn_file_search = ttk.Button(input_frame, text="Find File", command=self.perform_file_search, style="Accent.TButton")
        btn_file_search.pack(side=tk.LEFT)

        # Results area (Clean list style)
        self.file_results_frame = ttk.Frame(frame)
        self.file_results_frame.pack(fill=tk.BOTH, expand=True)

        # Using a scrolled text but with cleaner formatting for "File Cards"
        self.file_results_text = scrolledtext.ScrolledText(self.file_results_frame, font=("Consolas", 10), state=tk.DISABLED, wrap=tk.WORD)
        self.file_results_text.pack(fill=tk.BOTH, expand=True)
        
        # Formatting tags
        self.file_results_text.tag_config("file_card", background="#ffffff", spacing1=10, spacing3=10, lmargin1=10, lmargin2=10)
        self.file_results_text.tag_config("file_name", font=("Arial", 12, "bold"), foreground=Theme.PRIMARY)
        self.file_results_text.tag_config("include_path", font=("Consolas", 11, "bold"), foreground="#2980b9", background="#f0f7fb")
        self.file_results_text.tag_config("module_tag", font=("Arial", 10, "bold"), foreground="#27ae60")
        self.file_results_text.tag_config("build_tip", font=("Arial", 9, "italic"), foreground="#e67e22")

    def perform_file_search(self):
        query = self.file_query_entry.get().strip()
        if not query: return

        # Force "where is" style logic in backend
        augmented_query = f"where is file for {query}"
        
        self.file_results_text.config(state=tk.NORMAL)
        self.file_results_text.delete(1.0, tk.END)
        self.file_results_text.insert(tk.END, f"Searching for '{query}'...\n")
        self.file_results_text.config(state=tk.DISABLED)

        def on_success(results):
            self.dashboard.root.after(0, lambda: self._display_file_results(results))

        # Use the same search service but we'll format differently
        self.search_service.execute_query(
            query=augmented_query,
            scope="all",
            embed_model=self.embed_model_var.get(),
            filter_vars={'use_reranker': True}, # High precision for file search
            callback=on_success,
            error_callback=lambda err: self.dashboard.root.after(0, lambda: messagebox.showerror("Search Error", err))
        )

    def _get_dependency_tip(self, module_name):
        """Get a helpful tip for adding a module to Build.cs"""
        core_modules = {'Core', 'CoreUObject', 'Engine', 'InputCore', 'Slate', 'SlateCore'}
        if module_name in core_modules or module_name == "Unknown":
            return ""
            
        return f"Add \"{module_name}\" to PublicDependencyModuleNames in your Build.cs"

    def _display_file_results(self, results):
        self.file_results_text.config(state=tk.NORMAL)
        self.file_results_text.delete(1.0, tk.END)

        # Combine and deduplicate files across both types of results
        all_items = []
        seen_paths = set()

        # Definitions (highest precision)
        for d in results.get('definition_results', []):
            path = d['file_path']
            if path not in seen_paths:
                all_items.append(('definition', d))
                seen_paths.add(path)

        # Semantic (concept matches)
        for s in results.get('semantic_results', []):
            path = s['path']
            if path not in seen_paths:
                all_items.append(('semantic', s))
                seen_paths.add(path)

        if not all_items:
            self.file_results_text.insert(tk.END, "No matching files found.", "error")
        else:
            for i, (kind, item) in enumerate(all_items, 1):
                path = item.get('file_path') or item.get('path')
                name = Path(path).name
                
                # Resolve include/module
                path_info = UEPathUtils.guess_module_and_include(path)
                include = path_info['include']
                module = path_info['module']
                
                # Draw Card
                self.file_results_text.insert(tk.END, f" {name} ", "file_name")
                self.file_results_text.insert(tk.END, f" [Module: {module}]\n", "module_tag")
                
                self.file_results_text.insert(tk.END, f"  {include}\n", "include_path")
                
                # Dependency Tip
                tip = self._get_dependency_tip(module)
                if tip:
                    self.file_results_text.insert(tk.END, f"  Dependency: {tip}\n", "build_tip")
                
                self.file_results_text.insert(tk.END, f"  Path: {path}\n")
                
                if kind == 'definition':
                    # Add type hint
                    self.file_results_text.insert(tk.END, f"  Defined: {item['entity_type']} {item['entity_name']}\n")

                self.file_results_text.insert(tk.END, "-" * 40 + "\n")

        self.file_results_text.config(state=tk.DISABLED)
