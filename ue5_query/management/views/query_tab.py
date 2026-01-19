import tkinter as tk
from tkinter import ttk, scrolledtext
import sys
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

class QueryTab:
    """
    Handles the Query tab logic and layout.
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
        
        # Access variables from dashboard controller
        self.query_scope_var = dashboard.query_scope_var
        self.embed_model_var = dashboard.embed_model_var
        self.filter_entity_type_var = dashboard.filter_entity_type_var
        self.filter_macro_var = dashboard.filter_macro_var
        self.filter_file_type_var = dashboard.filter_file_type_var
        self.filter_boost_macros_var = dashboard.filter_boost_macros_var

        self.build_ui()

    def build_ui(self):
        """Build the UI components"""
        frame = ttk.Frame(self.frame, padding=20)
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
            self.dashboard.root.after(0, lambda: self.display_query_results(results))
            self.dashboard.root.after(0, lambda: self.query_entry.config(state=tk.NORMAL))

        # Error callback
        def on_error(err):
            self.dashboard.root.after(0, lambda: self.log_query_result(f"Error: {err}", clear=True, tag="error"))
            self.dashboard.root.after(0, lambda: self.query_entry.config(state=tk.NORMAL))

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
