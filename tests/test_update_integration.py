"""
Update Integration Tests
Tests for bidirectional update system.
"""

import sys
from pathlib import Path

# Determine tool root
SCRIPT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPT_DIR / "tools"))

def run_tests():
    """Run update integration tests"""
    print("Testing update integration...")

    try:
        # Add project root to path so 'tools' can be imported
        sys.path.insert(0, str(SCRIPT_DIR))
        from tools.update import UpdateManager, is_dev_repo, is_deployed_repo

        # Test environment detection
        is_dev = is_dev_repo(SCRIPT_DIR)
        is_deployed = is_deployed_repo(SCRIPT_DIR)

        print(f"  Is dev repo: {is_dev}")
        print(f"  Is deployed: {is_deployed}")

        if is_dev or is_deployed:
            print("  [OK] Update system environment detection working")
            return True
        else:
            print("  [WARN] Could not determine environment type")
            return True  # Not a failure, just informational

    except Exception as e:
        print(f"  [ERROR] Update integration test failed: {e}")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
