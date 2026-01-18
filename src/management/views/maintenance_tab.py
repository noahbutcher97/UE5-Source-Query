import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sys
import time
from pathlib import Path

# Try to import Theme, handle missing imports gracefully if run standalone
try:
    from src.utils.gui_theme import Theme
except ImportError:
    # If run standalone or during dev
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
        from src.utils.gui_theme import Theme
    except ImportError:
        Theme = None

class MaintenanceTab:
    """
    Handles the Maintenance tab logic and layout.
    """
    def __init__(self, parent_frame, dashboard):
        """
        Args:
            parent_frame: The ttk.Frame to build the tab into
            dashboard: Reference to the main UnifiedDashboard instance (controller)
        """
        self.frame = parent_frame
        self.dashboard = dashboard
        self.script_dir = dashboard.script_dir
        self.maint_service = dashboard.maint_service
        self.cancelled = False
        
        self.build_ui()
        self.check_status()

    def build_ui(self):
        """Build the UI components"""
        frame = ttk.Frame(self.frame, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Status Section
        status_frame = ttk.LabelFrame(frame, text=" System Status ", padding=15)
        status_frame.pack(fill=tk.X, pady=(0, 20))

        self.lbl_index_status = ttk.Label(status_frame, text="Index Status: Unknown", font=Theme.FONT_BOLD)
        self.lbl_index_status.pack(side=tk.LEFT)

        ttk.Button(status_frame, text="Refresh Status", command=self.check_status).pack(side=tk.RIGHT)

        # Progress Section
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
            command=self.dashboard.verify_installation,
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
            command=self.dashboard.setup_cuda,
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
        self.dashboard.root.after(100, self.dashboard.check_gpu_status)

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

    def log_maint(self, msg, clear=False, append=False):
        """Helper to log to maintenance log"""
        self.maint_log.config(state=tk.NORMAL)
        if clear:
            self.maint_log.delete(1.0, tk.END)
        
        if append:
            self.maint_log.insert(tk.END, msg)
        else:
            self.maint_log.insert(tk.END, msg + "\n")
            
        self.maint_log.see(tk.END)
        self.maint_log.config(state=tk.DISABLED)

    def cancel_or_close(self):
        if self.maint_service.current_process:
            if messagebox.askyesno("Cancel", "Cancel current operation?"):
                self.cancelled = True
                if self.maint_service.cancel_current_process():
                    self.log_maint("[CANCELLED] Operation cancelled.", append=True)
                    self.btn_rebuild.config(state=tk.NORMAL)
                    self.btn_cancel.config(text="Close")
        else:
            self.dashboard.root.destroy()

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
            self.dashboard.root.after(0, lambda: self.btn_rebuild.config(state=tk.NORMAL))
            self.dashboard.root.after(0, lambda: self.btn_cancel.config(text="Close"))
            if success:
                self.dashboard.root.after(0, lambda: update_progress(100, "Index rebuild complete!"))
                self.dashboard.root.after(0, lambda: self.log_maint("[SUCCESS] Index rebuild complete.", append=True))
                self.dashboard.root.after(0, self.check_status)
                
                elapsed = time.time() - start_time
                elapsed_str = f"{elapsed / 60:.1f} minutes" if elapsed > 60 else f"{elapsed:.0f} seconds"
                self.dashboard.root.after(0, lambda e=elapsed_str: self.maint_time_label.config(text=f"Completed in {e}"))
            else:
                if not self.cancelled:
                    self.dashboard.root.after(0, lambda: update_progress(0, "Failed"))
                    self.dashboard.root.after(0, lambda m=message: self.log_maint(f"\n[ERROR] {m}", append=True))

        def log_with_progress(line):
            stripped = line.strip()
            self.dashboard.root.after(0, lambda: self.log_maint(stripped, append=True))
            
            prog, label = parse_progress(stripped)
            if prog is not None:
                self.dashboard.root.after(0, lambda p=prog, l=label: update_progress(p, l))

        script = self.script_dir / "tools" / "rebuild-index.bat"
        self.maint_service.run_task(
            task_name="Index Rebuild",
            command=[str(script), "--verbose", "--force"],
            callback=on_complete,
            log_callback=log_with_progress
        )
