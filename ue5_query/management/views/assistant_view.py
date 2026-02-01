import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
from typing import Optional

from ue5_query.utils.gui_theme import Theme
from ue5_query.ai.service import IntelligenceService

class AssistantView:
    def __init__(self, notebook: ttk.Notebook, ai_service: IntelligenceService):
        self.notebook = notebook
        self.ai_service = ai_service
        self.frame = ttk.Frame(notebook)
        
        self.chat_history = [] # List of {"role": str, "content": str}
        self.is_generating = False
        
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
        ttk.Checkbutton(context_frame, text="Include Active Search Results").pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(context_frame, text="Include Selected Code Snippet").pack(anchor=tk.W, pady=2)
        
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
        self.append_message("Assistant", "", "assistant") # Placeholder start
        
        # Stream response
        self.ai_service.stream_chat(
            messages=self.chat_history,
            system_prompt="You are an expert Unreal Engine 5 C++ Developer. Provide concise, accurate technical answers.",
            on_token=self._on_token,
            on_complete=self._on_complete,
            on_error=self._on_error
        )

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
