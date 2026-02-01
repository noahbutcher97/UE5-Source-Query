import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
from typing import Optional

from ue5_query.utils.gui_theme import Theme
from ue5_query.ai.service import IntelligenceService
from ue5_query.ai.context_builder import ContextBuilder
# Lazy import SearchService to avoid circular dependency issues if any, though type hint usage is fine
from ue5_query.management.services import SearchService

class AssistantView:
    def __init__(self, notebook: ttk.Notebook, ai_service: IntelligenceService, search_service: SearchService):
        self.notebook = notebook
        self.ai_service = ai_service
        self.search_service = search_service
        self.frame = ttk.Frame(notebook)
        
        self.context_builder = ContextBuilder()
        
        self.chat_history = [] # List of {"role": str, "content": str}
        self.is_generating = False
        
        # UI Variables
        self.use_rag_var = tk.BooleanVar(value=True)
        self.use_snippet_var = tk.BooleanVar(value=False)
        
        self._build_layout()
        
    def _build_layout(self):
        # Main layout: Split between Chat (Left) and Context/Tools (Right)
        paned = ttk.PanedWindow(self.frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # --- Left: Chat Interface ---
        chat_frame = ttk.Frame(paned)
        paned.add(chat_frame, weight=3)
        
        # Chat History Log
        self.history_display = scrolledtext.ScrolledText(
            chat_frame,
            font=("Segoe UI", 10),
            state=tk.DISABLED,
            wrap=tk.WORD,
            bg="#FFFFFF",
            padx=10,
            pady=10
        )
        self.history_display.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Configure Tags for styling
        self.history_display.tag_config("user", foreground="#000000", font=("Segoe UI", 10, "bold"))
        self.history_display.tag_config("assistant", foreground="#2E7D32") # Green-ish
        self.history_display.tag_config("system", foreground="#757575", font=("Segoe UI", 9, "italic"))
        self.history_display.tag_config("error", foreground="#C62828")
        self.history_display.tag_config("status", foreground="#1976D2", font=("Segoe UI", 9, "italic"))

        # Input Area
        input_container = ttk.Frame(chat_frame)
        input_container.pack(fill=tk.X)
        
        self.input_text = tk.Text(
            input_container, 
            height=4, 
            font=("Segoe UI", 10),
            wrap=tk.WORD
        )
        self.input_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.input_text.bind("<Return>", self._on_enter_key)
        self.input_text.bind("<Shift-Return>", lambda e: None) # Allow newlines
        
        btn_frame = ttk.Frame(input_container)
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.btn_send = ttk.Button(
            btn_frame, 
            text="Send", 
            command=self.send_message, 
            style="Accent.TButton"
        )
        self.btn_send.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(btn_frame, text="Clear", command=self.clear_chat).pack(fill=tk.X)

        # --- Right: Context & Settings ---
        context_frame = ttk.LabelFrame(paned, text=" Context & Settings ", padding=10)
        paned.add(context_frame, weight=1)
        
        # API Status
        self.lbl_status = tk.Label(
            context_frame, 
            text="Checking API...", 
            font=("Segoe UI", 9),
            fg="#757575"
        )
        self.lbl_status.pack(anchor=tk.W, pady=(0, 10))
        
        # Context Options
        ttk.Checkbutton(context_frame, text="Search Codebase (RAG)", variable=self.use_rag_var).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(context_frame, text="Include Selected Code", variable=self.use_snippet_var, state=tk.DISABLED).pack(anchor=tk.W, pady=2)
        
        # Initial check
        self._check_service_status()

    def _check_service_status(self):
        if self.ai_service.is_available():
            self.lbl_status.config(text="● AI Service Ready", fg="#2E7D32")
            self.append_system_message("System ready. How can I help you with UE5?")
        else:
            self.lbl_status.config(text="● AI Service Disabled", fg="#C62828")
            self.append_system_message("AI features are disabled. Please configure your Anthropic API Key in the Settings tab.")
            self.input_text.config(state=tk.DISABLED)
            self.btn_send.config(state=tk.DISABLED)

    def _on_enter_key(self, event):
        if not event.state & 0x0001: # Shift not held
            self.send_message()
            return "break" # Prevent newline

    def send_message(self):
        if self.is_generating: return
        
        content = self.input_text.get("1.0", tk.END).strip()
        if not content: return
        
        self.input_text.delete("1.0", tk.END)
        
        # Add to UI
        self.append_message("User", content, "user")
        self.chat_history.append({"role": "user", "content": content})
        
        # Prepare for response
        self.is_generating = True
        self.btn_send.config(state=tk.DISABLED)
        
        # Check RAG option
        if self.use_rag_var.get():
            self._execute_search_and_chat(content)
        else:
            self._start_chat_stream(content, context="")

    def _execute_search_and_chat(self, query):
        """Run background search then start chat"""
        self.append_status_message("Analyzing codebase...")
        
        def on_search_success(results):
            # Back on main thread (handled by search_service callback wrapper usually, 
            # but let's be safe and use root.after if we were doing heavy lifting, 
            # though search_service.execute_query callback puts us on main thread in gui_dashboard logic.
            # Wait, gui_dashboard.py logic puts it on main thread. 
            # But here we invoke search_service directly. 
            # Let's check SearchService implementation. 
            # It runs in thread and calls callback. It does NOT automatically schedule on main thread 
            # unless the *caller* does it. 
            # In gui_dashboard, the caller (UnifiedDashboard) wraps the callback in root.after.
            # So we must do the same here.
            
            self.frame.after(0, lambda: self._process_search_results(results, query))

        def on_search_error(err):
            self.frame.after(0, lambda: self._handle_search_error(err, query))

        # Use intelligent defaults for RAG search
        filter_vars = {'use_reranker': True} # High precision for RAG
        
        self.search_service.execute_query(
            query=query,
            scope="engine", # Default to engine for now, could be option
            embed_model="microsoft/unixcoder-base", # Default
            filter_vars=filter_vars,
            callback=on_search_success,
            error_callback=on_search_error
        )

    def _process_search_results(self, results, original_query):
        # Build context
        context = self.context_builder.build_context(results)
        
        # Show what we found (briefly)
        def_count = len(results.get('definition_results', []))
        sem_count = len(results.get('semantic_results', []))
        self.append_status_message(f"Found {def_count} definitions and {sem_count} references.")
        
        # Start chat with context
        self._start_chat_stream(original_query, context)

    def _handle_search_error(self, err, original_query):
        self.append_status_message(f"Search failed: {err}. Proceeding without context.")
        self._start_chat_stream(original_query, context="")

    def _start_chat_stream(self, query, context):
        self.append_message("Assistant", "", "assistant") # Placeholder start
        
        # Construct system prompt
        base_prompt = "You are an expert Unreal Engine 5 C++ Developer. Provide concise, accurate technical answers."
        system_prompt = self.context_builder.format_system_prompt(base_prompt, context)
        
        # Stream response
        self.ai_service.stream_chat(
            messages=self.chat_history,
            system_prompt=system_prompt,
            on_token=self._on_token,
            on_complete=self._on_complete,
            on_error=self._on_error
        )

    def append_status_message(self, text):
        self.history_display.config(state=tk.NORMAL)
        self.history_display.insert(tk.END, f"► {text}\n", "status")
        self.history_display.see(tk.END)
        self.history_display.config(state=tk.DISABLED)

    def _on_token(self, text):
        def _update():
            self.history_display.config(state=tk.NORMAL)
            self.history_display.insert(tk.END, text, "assistant")
            self.history_display.see(tk.END)
            self.history_display.config(state=tk.DISABLED)
        self.frame.after(0, _update)

    def _on_complete(self, full_text):
        def _finalize():
            self.chat_history.append({"role": "assistant", "content": full_text})
            self.history_display.config(state=tk.NORMAL)
            self.history_display.insert(tk.END, "\n\n")
            self.history_display.see(tk.END)
            self.history_display.config(state=tk.DISABLED)
            
            self.is_generating = False
            self.btn_send.config(state=tk.NORMAL)
        self.frame.after(0, _finalize)

    def _on_error(self, error_msg):
        def _show_err():
            self.append_message("Error", f"\n{error_msg}\n", "error")
            self.is_generating = False
            self.btn_send.config(state=tk.NORMAL)
        self.frame.after(0, _show_err)

    def append_message(self, sender, text, tag):
        self.history_display.config(state=tk.NORMAL)
        self.history_display.insert(tk.END, f"{sender}: ", "header")
        self.history_display.insert(tk.END, f"{text}\n", tag)
        self.history_display.see(tk.END)
        self.history_display.config(state=tk.DISABLED)

    def append_system_message(self, text):
        self.history_display.config(state=tk.NORMAL)
        self.history_display.insert(tk.END, f"[System] {text}\n\n", "system")
        self.history_display.see(tk.END)
        self.history_display.config(state=tk.DISABLED)

    def clear_chat(self):
        self.chat_history = []
        self.history_display.config(state=tk.NORMAL)
        self.history_display.delete("1.0", tk.END)
        self.history_display.config(state=tk.DISABLED)
        self._check_service_status()
