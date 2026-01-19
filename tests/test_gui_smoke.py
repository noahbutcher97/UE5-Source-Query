"""
GUI Smoke Tests
Basic tests to ensure GUI modules can be imported and initialized.
"""

import sys
from pathlib import Path

# Determine tool root
SCRIPT_DIR = Path(__file__).parent.parent

def run_tests():
    """Run GUI smoke tests"""
    print("Testing GUI modules...")

    try:
        # Test GUI module imports
        from ue5_query.utils.gui_theme import Theme
        from ue5_query.management.gui_dashboard import UnifiedDashboard

        print("  [OK] GUI modules importable")

        # Test Theme class
        theme_attrs = ['PRIMARY', 'SECONDARY', 'BG_LIGHT', 'BG_DARK', 'TEXT_DARK', 'TEXT_LIGHT']
        for attr in theme_attrs:
            if not hasattr(Theme, attr):
                print(f"  [ERROR] Theme missing attribute: {attr}")
                return False

        print("  [OK] Theme class has required attributes")

        # Test UnifiedDashboard class
        dashboard_methods = ['create_layout', 'build_status_tab', 'build_config_tab']
        for method in dashboard_methods:
            if not hasattr(UnifiedDashboard, method):
                print(f"  [ERROR] UnifiedDashboard missing method: {method}")
                return False

        print("  [OK] UnifiedDashboard class has required methods")

        return True

    except Exception as e:
        print(f"  [ERROR] GUI smoke test failed: {e}")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
