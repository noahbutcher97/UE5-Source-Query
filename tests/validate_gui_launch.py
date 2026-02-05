"""
GUI Launch Validation

Quick script to verify both GUIs can launch without errors.
Creates hidden windows and validates initialization.
"""

import sys
import io
from pathlib import Path
import tkinter as tk

# Fix Windows console encoding for checkmarks
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_deployment_wizard():
    """Test deployment wizard launches"""
    print("Testing deployment wizard... ", end="", flush=True)

    root = tk.Tk()
    root.withdraw()

    try:
        from installer.gui_deploy import DeploymentWizard
        wizard = DeploymentWizard(root)
        print("✓ PASS")
        root.update_idletasks()
        root.after(100, wizard.destroy)
        root.mainloop()
        return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        root.destroy()
        return False


def test_unified_dashboard():
    """Test unified dashboard launches"""
    print("Testing unified dashboard... ", end="", flush=True)

    root = tk.Tk()
    root.withdraw()

    try:
        from ue5_query.management.gui_dashboard import UnifiedDashboard
        dashboard = UnifiedDashboard(root)
        print("✓ PASS")
        root.update_idletasks()
        root.after(100, dashboard.destroy)
        root.mainloop()
        return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        root.destroy()
        return False


def test_theme_attributes():
    """Test all Theme attributes exist"""
    print("Testing Theme attributes... ", end="", flush=True)

    from ue5_query.utils.gui_theme import Theme

    required_attrs = [
        'PRIMARY', 'SECONDARY', 'SUCCESS', 'WARNING', 'ERROR',
        'BG_LIGHT', 'BG_DARK', 'TEXT_LIGHT', 'TEXT_DARK',
        'FONT_HEADER', 'FONT_SUBHEADER', 'FONT_NORMAL',
        'FONT_BOLD', 'FONT_SMALL', 'FONT_MONO'
    ]

    missing = [attr for attr in required_attrs if not hasattr(Theme, attr)]

    if missing:
        print(f"✗ FAIL: Missing {missing}")
        return False

    print("✓ PASS")
    return True


def main():
    """Run all validation tests"""
    print("\n" + "="*60)
    print("GUI Launch Validation")
    print("="*60 + "\n")

    results = []

    # Test Theme first (most basic)
    results.append(test_theme_attributes())

    # Test GUI launches
    results.append(test_deployment_wizard())
    results.append(test_unified_dashboard())

    print("\n" + "="*60)
    if all(results):
        print("✓ All validation tests passed!")
        print("="*60 + "\n")
        return 0
    else:
        print("✗ Some validation tests failed")
        print("="*60 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
