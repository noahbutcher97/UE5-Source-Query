"""
Shared GUI utilities for Deployment Wizard and Unified Dashboard.

This module provides common GUI components and dialogs to ensure
consistency between the deployment wizard and the unified dashboard.
"""

import tkinter as tk
from tkinter import ttk

# Universal imports that work in both dev and deployed environments
try:
    from src.utils.gui_theme import Theme
    from src.utils.gui_layout import WindowManager, LayoutMetrics
except ImportError:
    from utils.gui_theme import Theme
    # If run standalone/tests where utils isn't package
    try:
        from src.utils.gui_layout import WindowManager, LayoutMetrics
    except:
        pass


def show_engine_detection_help(parent, browse_callback):
    """
    Show engine detection help dialog.

    Args:
        parent: Parent tkinter window
        browse_callback: Callback function to execute when "Browse Manually" is clicked
    """
    dialog = tk.Toplevel(parent)
    
    # Use Layout Engine for geometry and scaling
    WindowManager.setup_window(
        dialog, 
        "UE5 Engine Not Found - Setup Help",
        target_width_pct=0.6,
        target_height_pct=0.7,
        min_w=700,
        min_h=500
    )
    
    dialog.transient(parent)
    dialog.grab_set()

    # Title
    title_frame = ttk.Frame(dialog)
    title_frame.pack(fill=tk.X, padx=20, pady=10)
    ttk.Label(title_frame, text="No UE5 installation detected automatically",
              font=Theme.FONT_BOLD).pack()

    # Help text with scrollbar
    text_frame = ttk.Frame(dialog)
    text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

    scrollbar = ttk.Scrollbar(text_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    help_text = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set,
                        font=Theme.FONT_NORMAL, relief=tk.FLAT, bg="#f0f0f0")
    help_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=help_text.yview)

    help_content = """To help us find your UE5 engine installation, try one of these methods:

1. SET ENVIRONMENT VARIABLE (Recommended)

   Set one of these environment variables:
   • UE5_ENGINE_PATH = C:\\Path\\To\\UE_5.3\\Engine
   • UE_ROOT = C:\\Path\\To\\UE_5.3\\Engine
   • UNREAL_ENGINE_PATH = C:\\Path\\To\\UE_5.3\\Engine

   Then restart this application.

2. CREATE .ue5query CONFIG FILE

   Create a file named .ue5query in your project root or home directory:

   {
     "engine": {
       "path": "C:/Path/To/UE_5.3/Engine",
       "version": "5.3.2"
     }
   }

3. INSTALL IN STANDARD LOCATION

   Ensure UE5 is installed in one of these standard locations:
   • C:\\Program Files\\Epic Games\\UE_5.X
   • D:\\Program Files\\Epic Games\\UE_5.X
   • C:\\Epic Games\\UE_5.X
   • D:\\Epic Games\\UE_5.X

4. USE EPIC GAMES LAUNCHER

   Install UE5 via Epic Games Launcher. It will be automatically
   registered in Windows Registry for detection.

5. BROWSE MANUALLY (Below)

   Click 'Browse Manually' to select your engine directory directly.
"""

    help_text.insert("1.0", help_content)
    help_text.config(state=tk.DISABLED)

    # Button frame
    button_frame = ttk.Frame(dialog)
    button_frame.pack(fill=tk.X, padx=20, pady=10)

    ttk.Button(button_frame, text="Browse Manually",
               command=lambda: [dialog.destroy(), browse_callback()],
               style="Accent.TButton").pack(side=tk.LEFT, padx=5)

    ttk.Button(button_frame, text="Close",
               command=dialog.destroy).pack(side=tk.RIGHT, padx=5)


def show_version_mismatch_warning(parent, project_version, engine_version):
    """
    Show warning dialog for version mismatch.

    Args:
        parent: Parent tkinter window
        project_version: Version from .uproject file (e.g., "5.3")
        engine_version: Version from indexed engine (e.g., "5.2")

    Returns:
        tk.Frame: Warning frame widget (can be packed by caller)
    """
    warning_frame = tk.Frame(parent, bg="#FFF3CD", relief=tk.SOLID, bd=1)

    warning_text = tk.Label(
        warning_frame,
        text=f"⚠️ Engine version mismatch detected: Project uses UE {project_version}, but index was built with UE {engine_version}. Consider rebuilding index.",
        font=("Arial", 9),
        bg="#FFF3CD",
        fg="#856404",
        wraplength=650,
        justify=tk.LEFT
    )
    warning_text.pack(padx=10, pady=8)

    return warning_frame


def create_dark_theme_text(parent, **kwargs):
    """
    Create ScrolledText widget with standardized dark theme.

    Args:
        parent: Parent tkinter window
        **kwargs: Additional keyword arguments passed to tk.Text

    Returns:
        tuple: (text_frame, text_widget, scrollbar) - Frame containing text widget and scrollbar
    """
    # Default dark theme colors
    defaults = {
        'bg': '#1E1E1E',
        'fg': '#D4D4D4',
        'insertbackground': '#FFFFFF',
        'selectbackground': '#264F78',
        'selectforeground': '#FFFFFF',
        'font': Theme.FONT_MONO,
        'wrap': tk.WORD,
        'relief': tk.FLAT,
        'borderwidth': 0,
    }

    # Merge defaults with provided kwargs (kwargs take precedence)
    text_config = {**defaults, **kwargs}

    # Create frame
    text_frame = ttk.Frame(parent)

    # Create scrollbar
    scrollbar = ttk.Scrollbar(text_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Create text widget
    text_widget = tk.Text(text_frame, yscrollcommand=scrollbar.set, **text_config)
    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=text_widget.yview)

    return text_frame, text_widget, scrollbar


def show_health_score_indicator(parent, score, label_text="Health Score"):
    """
    Display health score with color-coded indicator.

    Args:
        parent: Parent tkinter window
        score: Health score (0-100)
        label_text: Text to display before the score

    Returns:
        tk.Frame: Frame containing the health score indicator
    """
    score_frame = tk.Frame(parent, bg=parent.cget('bg') if hasattr(parent, 'cget') else '#FFFFFF')

    # Label
    tk.Label(
        score_frame,
        text=f"{label_text}: ",
        font=Theme.FONT_NORMAL,
        bg=score_frame.cget('bg')
    ).pack(side=tk.LEFT)

    # Color-code based on score
    if score >= 80:
        color = "#28a745"  # Green
        status = "Excellent"
    elif score >= 60:
        color = "#ffc107"  # Yellow
        status = "Good"
    elif score >= 40:
        color = "#fd7e14"  # Orange
        status = "Fair"
    else:
        color = "#dc3545"  # Red
        status = "Poor"

    # Score value with color
    score_label = tk.Label(
        score_frame,
        text=f"{score}/100 ({status})",
        font=Theme.FONT_BOLD,
        fg=color,
        bg=score_frame.cget('bg')
    )
    score_label.pack(side=tk.LEFT)

    return score_frame


def validate_engine_path_interactive(parent, path):
    """
    Validate engine path with user-friendly error messages.

    Args:
        parent: Parent tkinter window
        path: Path to engine directory (Path object or string)

    Returns:
        tuple: (is_valid, error_message)
            - is_valid: Boolean indicating if path is valid
            - error_message: String error message if invalid, None if valid
    """
    from pathlib import Path

    if not path:
        return False, "No engine path provided"

    engine_path = Path(path)

    if not engine_path.exists():
        return False, f"Path does not exist: {engine_path}"

    if not engine_path.is_dir():
        return False, f"Path is not a directory: {engine_path}"

    # Check for critical engine directories
    required_dirs = ['Source', 'Build', 'Binaries']
    missing_dirs = [d for d in required_dirs if not (engine_path / d).exists()]

    if missing_dirs:
        return False, f"Not a valid UE5 engine directory. Missing: {', '.join(missing_dirs)}"

    # Check for version file
    version_file = engine_path / 'Build' / 'Build.version'
    if not version_file.exists():
        return False, "Engine directory missing Build.version file"

    return True, None


def center_window(window, width=None, height=None):
    """
    Center a window on screen or relative to its parent.

    Args:
        window: tkinter window to center
        width: Optional width to set (uses current width if None)
        height: Optional height to set (uses current height if None)
    """
    window.update_idletasks()

    # Get window dimensions
    if width is None:
        width = window.winfo_width()
    if height is None:
        height = window.winfo_height()

    # Get screen dimensions
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    # Calculate position
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2

    window.geometry(f"{width}x{height}+{x}+{y}")


def create_labeled_entry(parent, label_text, entry_var=None, show=None, width=40):
    """
    Create a labeled entry widget with consistent styling.

    Args:
        parent: Parent tkinter window
        label_text: Text for the label
        entry_var: Optional StringVar for the entry
        show: Optional character to show instead of actual text (for passwords)
        width: Width of the entry widget

    Returns:
        tuple: (frame, label, entry) - The containing frame and widgets
    """
    frame = ttk.Frame(parent)

    label = ttk.Label(frame, text=label_text, font=Theme.FONT_NORMAL)
    label.pack(side=tk.LEFT, padx=(0, 10))

    entry_config = {'width': width, 'font': Theme.FONT_NORMAL}
    if entry_var:
        entry_config['textvariable'] = entry_var
    if show:
        entry_config['show'] = show

    entry = ttk.Entry(frame, **entry_config)
    entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

    return frame, label, entry


def create_button_row(parent, buttons, pack_options=None):
    """
    Create a row of buttons with consistent spacing.

    Args:
        parent: Parent tkinter window
        buttons: List of tuples: (text, command, style_or_options)
            Each tuple is (button_text, callback_function, optional_style_dict)
        pack_options: Optional dict of pack options for the frame

    Returns:
        tk.Frame: Frame containing the buttons
    """
    if pack_options is None:
        pack_options = {'fill': tk.X, 'padx': 10, 'pady': 10}

    button_frame = ttk.Frame(parent)
    button_frame.pack(**pack_options)

    for btn_info in buttons:
        text = btn_info[0]
        command = btn_info[1]
        style = btn_info[2] if len(btn_info) > 2 else None

        btn_kwargs = {'text': text, 'command': command}
        if isinstance(style, str):
            btn_kwargs['style'] = style
        elif isinstance(style, dict):
            btn_kwargs.update(style)

        btn = ttk.Button(button_frame, **btn_kwargs)
        btn.pack(side=tk.LEFT, padx=5)

    return button_frame
