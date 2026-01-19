"""
UE5 Source Query - Adaptive Layout Engine
Provides a bespoke data model for GUI scaling, responsiveness, and layout rules.
"""

import tkinter as tk
from tkinter import ttk
import platform
import ctypes
import json
from pathlib import Path
from ue5_query.utils.gui_theme import Theme

class GUIPrefs:
    """Manages persistent GUI preferences"""
    def __init__(self):
        self.config_dir = Path(__file__).parent.parent.parent / "config"
        self.prefs_file = self.config_dir / "gui_prefs.json"
        self.env_file = self.config_dir / ".env"
        self._prefs = {"text_scale": 1.0}
        self.load()

    def _load_from_env(self):
        """Try to load text scale from .env for consistency"""
        if self.env_file.exists():
            try:
                with open(self.env_file, 'r') as f:
                    for line in f:
                        if "GUI_TEXT_SCALE=" in line:
                            val = line.split("=")[1].strip()
                            self._prefs["text_scale"] = float(val)
                            return True
            except Exception:
                pass
        return False

    def load(self):
        # 1. Start with defaults
        self._prefs = {"text_scale": 1.0}
        
        # 2. Try .env (primary source for tool config)
        self._load_from_env()
        
        # 3. Try gui_prefs.json (override/supplement)
        if self.prefs_file.exists():
            try:
                with open(self.prefs_file, 'r') as f:
                    data = json.load(f)
                    self._prefs.update(data)
            except Exception:
                pass

    def save(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        try:
            # Save to json
            with open(self.prefs_file, 'w') as f:
                json.dump(self._prefs, f, indent=2)
            
            # Also update .env if it exists to keep in sync
            if self.env_file.exists():
                lines = self.env_file.read_text().splitlines()
                new_lines = []
                found = False
                for line in lines:
                    if line.startswith("GUI_TEXT_SCALE="):
                        new_lines.append(f"GUI_TEXT_SCALE={self.text_scale:.2f}")
                        found = True
                    else:
                        new_lines.append(line)
                if not found:
                    new_lines.append(f"GUI_TEXT_SCALE={self.text_scale:.2f}")
                self.env_file.write_text("\n".join(new_lines) + "\n")
        except Exception:
            pass

    @property
    def text_scale(self):
        return self._prefs.get("text_scale", 1.0)

    @text_scale.setter
    def text_scale(self, value):
        self._prefs["text_scale"] = float(value)
        self.save()

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
        
        self.prefs = GUIPrefs()
        self.scale_factor = self._get_scale_factor(root)
        self.text_scale = self.prefs.text_scale
        self._initialize_metrics()
        self._initialized = True

    def refresh(self):
        """Reload prefs and recalculate metrics"""
        self.prefs.load()
        self.text_scale = self.prefs.text_scale
        self._initialize_metrics()

    def set_text_scale(self, scale):
        """Update text scale and persist"""
        self.text_scale = scale
        self.prefs.text_scale = scale
        self._initialize_metrics()

    def _get_scale_factor(self, root):
        """Detect DPI scaling factor"""
        try:
            # Windows DPI awareness - should be called BEFORE any window is created
            # but we call it here just in case.
            if platform.system() == "Windows":
                try:
                    # Shcore is newer, preferred over user32
                    ctypes.windll.shcore.SetProcessDpiAwareness(1)
                except Exception:
                    try:
                        ctypes.windll.user32.SetProcessDPIAware()
                    except Exception:
                        pass
            
            if root:
                # 72 is default tk dpi, 96 is standard. 
                # winfo_fpixels('1i') returns pixels per inch.
                dpi = root.winfo_fpixels('1i')
                # Base scale on 96 DPI standard
                factor = dpi / 96.0
                return max(1.0, factor)
        except Exception:
            pass
        return 1.0

    def _initialize_metrics(self):
        """Quantify spacing metrics based on scale"""
        # Combine DPI scaling with User Preference Text Scale
        s = self.scale_factor * self.text_scale
        
        # Spacing / Padding
        self.PAD_XS = max(2, int(4 * s))
        self.PAD_S = max(4, int(8 * s))
        self.PAD_M = max(8, int(16 * s))
        self.PAD_L = max(16, int(24 * s))
        self.PAD_XL = max(24, int(32 * s))
        
        # Component Sizes
        self.BTN_HEIGHT = int(30 * s)
        self.ENTRY_HEIGHT = int(25 * s)
        self.SCROLLBAR_WIDTH = max(12, int(16 * s))
        
        # Typography (Points)
        # Fonts in Tkinter usually scale with DPI automatically if negative,
        # or points if positive. We use points * text_scale.
        # We DO NOT apply scale_factor here usually because OS handles font DPI,
        # but we DO apply user preference text_scale.
        
        base_s = 9
        base_m = 10
        base_l = 12
        base_xl = 16
        
        self.FONT_S = max(8, int(base_s * self.text_scale))
        self.FONT_M = max(9, int(base_m * self.text_scale))
        self.FONT_L = max(11, int(base_l * self.text_scale))
        self.FONT_XL = max(14, int(base_xl * self.text_scale))

        # Treeview Row Height (Crucial for High DPI)
        # Needs to accommodate FONT_M + padding
        # Scale factor usage here depends on if font size is in pixels or points
        # Assuming FONT_M is points, roughly * 1.33 for pixels + padding
        self.TREE_ROW_HEIGHT = int((self.FONT_M * 1.8) + (10 * self.text_scale))

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
        """
        window.title(title)
        
        # Force update to get screen info
        window.update_idletasks()
        
        screen_w = window.winfo_screenwidth()
        screen_h = window.winfo_screenheight()
        
        # Apply scaling constraints
        metrics = LayoutMetrics(window)
        # Apply global scale to min constraints
        s = metrics.scale_factor * metrics.text_scale
        
        scaled_min_w = int(min_w * s)
        scaled_min_h = int(min_h * s)
        
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
        y = max(30, y)
        
        # Apply
        window.minsize(scaled_min_w, scaled_min_h)
        window.geometry(f"{width}x{height}+{x}+{y}")

class Responsive:
    """
    Helpers for creating responsive, context-aware containers.
    """
    
    @staticmethod
    def make_scrollable(parent):
        """
        Wrap a frame in a canvas to ensure accessibility.
        Returns: (outer_frame, scrollable_content_frame)
        """
        # Outer container (holds canvas + scrollbar)
        outer_frame = ttk.Frame(parent)
        outer_frame.pack(fill=tk.BOTH, expand=True) # Ensure it fills parent
        
        canvas = tk.Canvas(outer_frame, highlightthickness=0, bg=Theme.BG_LIGHT if hasattr(Theme, 'BG_LIGHT') else '#f0f0f0')
        scrollbar = ttk.Scrollbar(outer_frame, orient="vertical", command=canvas.yview)
        
        # Content frame (inside canvas)
        scrollable_frame = ttk.Frame(canvas)
        
        # Logic to resize content frame to canvas width
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # Create window in canvas
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Force frame width to match canvas
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        
        canvas.bind("<Configure>", on_canvas_configure)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Mousewheel binding (Windows/Linux)
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
        # Bind to canvas and all children
        # Note: In Tkinter, binding to 'all' can be heavy, but for this specific tree it's often necessary
        # A better approach is usually binding to the canvas and ensuring focus, 
        # but bind_all is robust for dialogs.
        scrollable_frame.bind("<Enter>", lambda _: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        scrollable_frame.bind("<Leave>", lambda _: canvas.unbind_all("<MouseWheel>"))
        
        return outer_frame, scrollable_frame

    @staticmethod
    def text_area(parent, metrics: LayoutMetrics, height=10):
        """Create a text area that respects visual hierarchy"""
        frame = ttk.Frame(parent)
        
        font = metrics.get_font("M", "normal")
        if "Consolas" not in font: 
             font = ("Consolas", metrics.FONT_M)

        text = tk.Text( # Use standard Text for better font control
            frame,
            height=height,
            font=font,
            wrap=tk.WORD,
            padx=metrics.PAD_M,
            pady=metrics.PAD_S,
            borderwidth=0,
            relief=tk.FLAT
        )
        
        # Add scrollbar
        sb = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=sb.set)
        
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        
        return frame, text