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
    
    # Fonts
    FONT_HEADER = ("Segoe UI", 16, "bold")
    FONT_SUBHEADER = ("Segoe UI", 12)
    FONT_NORMAL = ("Segoe UI", 10)
    FONT_BOLD = ("Segoe UI", 10, "bold")
    FONT_MONO = ("Consolas", 9)

    @staticmethod
    def apply(root):
        """Apply global theme settings"""
        style = ttk.Style()
        
        # Configure general ttk styles
        style.configure("TFrame", background=Theme.BG_LIGHT)
        style.configure("TLabel", background=Theme.BG_LIGHT, foreground=Theme.TEXT_DARK, font=Theme.FONT_NORMAL)
        style.configure("TButton", font=Theme.FONT_NORMAL)
        
        # Accent Button
        style.configure(
            "Accent.TButton",
            background=Theme.SUCCESS,
            foreground=Theme.TEXT_DARK,
            font=Theme.FONT_BOLD
        )

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
