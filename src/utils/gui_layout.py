"""
UE5 Source Query - Adaptive Layout Engine
Provides a bespoke data model for GUI scaling, responsiveness, and layout rules.
"""

import tkinter as tk
from tkinter import ttk
import platform
import ctypes

class LayoutMetrics:
    """
    Data model for quantified spacing, sizing, and typography metrics.
    Adapts to system DPI and screen resolution.
    """
    _instance = None

    def __new__(cls, root=None):
        if cls._instance is None:
            cls._instance = super(LayoutMetrics, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, root=None):
        if self._initialized:
            return
        
        self.scale_factor = self._get_scale_factor(root)
        self._initialize_metrics()
        self._initialized = True

    def _get_scale_factor(self, root):
        """Detect DPI scaling factor"""
        try:
            # Windows DPI awareness
            if platform.system() == "Windows":
                try:
                    ctypes.windll.shcore.SetProcessDpiAwareness(1)
                except Exception:
                    pass
            
            if root:
                # 72 is default tk dpi, 96 is standard. 
                # On high-DPI screens this might range 120-192+
                dpi = root.winfo_fpixels('1i')
                return dpi / 72.0
        except Exception:
            pass
        return 1.0

    def _initialize_metrics(self):
        """Quantify spacing metrics based on scale"""
        s = self.scale_factor
        
        # Spacing / Padding
        self.PAD_XS = int(2 * s)
        self.PAD_S = int(5 * s)
        self.PAD_M = int(10 * s)
        self.PAD_L = int(20 * s)
        self.PAD_XL = int(30 * s)
        
        # Component Sizes
        self.BTN_HEIGHT = int(30 * s)
        self.ENTRY_HEIGHT = int(25 * s)
        self.SCROLLBAR_WIDTH = int(15 * s)
        
        # Typography (Points)
        # We generally don't scale font points linearly with DPI if the OS handles it,
        # but for pixel-based calculations we need to know.
        # Here we define relative sizes.
        self.FONT_S = 9
        self.FONT_M = 10
        self.FONT_L = 12
        self.FONT_XL = 16

    def get_font(self, size_key, weight="normal"):
        """Get font tuple based on semantic key"""
        size = getattr(self, f"FONT_{size_key}", 10)
        return ("Segoe UI", size, weight)

class WindowManager:
    """
    Logic engine for window geometry and responsiveness.
    Enforces rendering constraints and contextual awareness.
    """
    
    @staticmethod
    def setup_window(window, title, target_width_pct=0.7, target_height_pct=0.7, min_w=800, min_h=600):
        """
        Apply dynamic layout rules to a window.
        
        Args:
            window: The Toplevel or Tk instance
            title: Window title
            target_width_pct: Target width as percentage of screen (0.0-1.0)
            target_height_pct: Target height as percentage of screen
            min_w: Minimum width in logical pixels
            min_h: Minimum height in logical pixels
        """
        window.title(title)
        
        # Force update to get screen info
        window.update_idletasks()
        
        screen_w = window.winfo_screenwidth()
        screen_h = window.winfo_screenheight()
        
        # Apply scaling constraints
        metrics = LayoutMetrics(window)
        scaled_min_w = int(min_w * metrics.scale_factor)
        scaled_min_h = int(min_h * metrics.scale_factor)
        
        # Calculate optimal geometry
        width = int(screen_w * target_width_pct)
        height = int(screen_h * target_height_pct)
        
        # Enforce constraints
        width = max(scaled_min_w, min(width, screen_w))
        height = max(scaled_min_h, min(height, screen_h))
        
        # Smart centering
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        
        # Prevent top-left hidden under taskbars/menus
        x = max(0, x)
        y = max(30, y) # Reserve space for title bars
        
        # Apply
        window.minsize(scaled_min_w, scaled_min_h)
        window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Bind resize events for responsive adjustments if needed
        # window.bind('<Configure>', lambda e: WindowManager._on_resize(window, e))

    @staticmethod
    def _on_resize(window, event):
        # Placeholder for dynamic text wrapping or layout reflow logic
        pass

class Responsive:
    """
    Helpers for creating responsive, context-aware containers.
    """
    
    @staticmethod
    def make_scrollable(parent):
        """
        Wrap a frame in a canvas to ensure accessibility on small screens.
        Returns: (outer_frame, scrollable_content_frame)
        """
        outer_frame = ttk.Frame(parent)
        
        canvas = tk.Canvas(outer_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Mousewheel binding
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        return outer_frame, scrollable_frame

    @staticmethod
    def text_area(parent, metrics: LayoutMetrics, height=10):
        """Create a text area that respects visual hierarchy"""
        frame = ttk.Frame(parent)
        
        font = metrics.get_font("M", "normal") # Monospace usually better for logs?
        if "Consolas" not in font: 
             font = ("Consolas", metrics.FONT_M)

        text = scrolledtext.ScrolledText(
            frame,
            height=height,
            font=font,
            wrap=tk.WORD,
            padx=metrics.PAD_M,
            pady=metrics.PAD_S,
            borderwidth=0
        )
        text.pack(fill=tk.BOTH, expand=True)
        return frame, text

