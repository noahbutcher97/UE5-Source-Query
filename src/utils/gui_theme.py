"""
UE5 Source Query Tool - GUI Theme Definitions
Standardizes the visual look and feel across all GUI components.
"""
import tkinter as tk
from tkinter import ttk

class Theme:
    # Colors
    PRIMARY = "#2C3E50"      # Dark Blue/Grey (Headers)
    SECONDARY = "#9B59B6"    # Purple (Accents)
    SUCCESS = "#27AE60"      # Green (Actions)
    WARNING = "#F39C12"      # Orange
    ERROR = "#C0392B"        # Red
    BG_LIGHT = "#ECF0F1"     # Light Grey (Backgrounds)
    BG_DARK = "#2C3E50"      # Dark Background
    TEXT_LIGHT = "#FFFFFF"
    TEXT_DARK = "#2C3E50"
    
    # Dynamic Fonts (initialized with defaults, updated by apply)
    FONT_HEADER = ("Segoe UI", 16, "bold")
    FONT_SUBHEADER = ("Segoe UI", 12)
    FONT_NORMAL = ("Segoe UI", 10)
    FONT_BOLD = ("Segoe UI", 10, "bold")
    FONT_SMALL = ("Segoe UI", 9)
    FONT_TINY = ("Segoe UI", 8)
    FONT_MONO = ("Consolas", 9)

    @staticmethod
    def update_fonts(metrics):
        """Update theme fonts based on LayoutMetrics"""
        Theme.FONT_HEADER = metrics.get_font("XL", "bold")
        Theme.FONT_SUBHEADER = metrics.get_font("L")
        Theme.FONT_NORMAL = metrics.get_font("M")
        Theme.FONT_BOLD = metrics.get_font("M", "bold")
        Theme.FONT_SMALL = metrics.get_font("S")
        Theme.FONT_TINY = ("Segoe UI", max(7, metrics.FONT_S - 1))
        
        # Mono font
        mono_size = metrics.FONT_S
        Theme.FONT_MONO = ("Consolas", mono_size)

    @staticmethod
    def apply(root):
        """Apply global theme settings"""
        from src.utils.gui_layout import LayoutMetrics
        metrics = LayoutMetrics(root)
        Theme.update_fonts(metrics)
        
        style = ttk.Style()
        
        # Configure general ttk styles
        style.configure(".", background=Theme.BG_LIGHT, foreground=Theme.TEXT_DARK, font=Theme.FONT_NORMAL)
        style.configure("TFrame", background=Theme.BG_LIGHT)
        style.configure("TLabel", background=Theme.BG_LIGHT, foreground=Theme.TEXT_DARK, font=Theme.FONT_NORMAL)
        style.configure("TButton", font=Theme.FONT_NORMAL)
        
        # Notebook tabs
        style.configure("TNotebook", background=Theme.BG_LIGHT, padding=5)
        style.configure("TNotebook.Tab", font=Theme.FONT_BOLD, padding=[10, 5])
        
        # LabelFrames
        style.configure("TLabelframe", background=Theme.BG_LIGHT)
        style.configure("TLabelframe.Label", background=Theme.BG_LIGHT, font=Theme.FONT_BOLD)

        # Accent Button
        style.configure(
            "Accent.TButton",
            background=Theme.SUCCESS,
            foreground=Theme.TEXT_DARK,
            font=Theme.FONT_BOLD
        )
        
        # Entry fields
        style.configure("TEntry", font=Theme.FONT_NORMAL)
        
        # Apply to root itself for non-ttk widgets
        root.configure(bg=Theme.BG_LIGHT)
        root.option_add("*Font", Theme.FONT_NORMAL)

    @staticmethod
    def create_header(parent, title, subtitle=""):
        """Create a standardized header frame"""
        header = tk.Frame(parent, bg=Theme.PRIMARY, height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(
            header,
            text=title,
            font=Theme.FONT_HEADER,
            bg=Theme.PRIMARY,
            fg=Theme.TEXT_LIGHT
        ).pack(pady=(15, 5))

        if subtitle:
            tk.Label(
                header,
                text=subtitle,
                font=Theme.FONT_SUBHEADER,
                bg=Theme.PRIMARY,
                fg="#BDC3C7"  # Light grey
            ).pack()
            
        return header
