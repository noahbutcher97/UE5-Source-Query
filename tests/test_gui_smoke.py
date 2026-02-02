"""
GUI Smoke Tests
Tests to ensure GUI modules can be imported and the Dashboard instantiates without crashing.
"""

import sys
import tkinter as tk
from pathlib import Path

# Determine tool root
SCRIPT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

def run_tests():
    """Run GUI smoke tests"""
    print("Testing GUI modules...")

    try:
        # 1. Test Imports
        print("  Testing imports...")
        from ue5_query.utils.gui_theme import Theme
        from ue5_query.management.gui_dashboard import UnifiedDashboard
        print("  [OK] Imports successful")

        # 2. Test Instantiation (The Real Smoke Test)
        print("  Testing Dashboard instantiation...")
        
        # Initialize headless root
        root = tk.Tk()
        root.withdraw() # Hide window
        
        # Create dashboard - this triggers create_layout and all tab builds
        try:
            app = UnifiedDashboard(root)
            # Force update to ensure layout calculation happens
            root.update_idletasks()
            print("  [OK] UnifiedDashboard instantiated successfully")
        except Exception as e:
            print(f"  [ERROR] Instantiation failed: {e}")
            import traceback
            traceback.print_exc()
            root.destroy()
            return False
            
        # Clean up
        root.destroy()
        return True

    except Exception as e:
        print(f"  [ERROR] GUI smoke test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)