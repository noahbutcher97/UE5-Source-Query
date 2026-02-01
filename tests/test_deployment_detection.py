"""
Deployment Detection Tests
Tests for deployment detection and environment analysis.
"""

import sys
from pathlib import Path

# Determine tool root
SCRIPT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

def run_tests():
    """Run deployment detection tests"""
    print("Testing deployment detection...")

    try:
        from ue5_query.utils.deployment_detector import DeploymentDetector

        # Test detection
        detector = DeploymentDetector(SCRIPT_DIR)
        env_info = detector.env_info

        print(f"  Environment: {env_info.environment_type}")
        print(f"  Valid: {env_info.is_valid}")

        if env_info.environment_type == 'dev_repo':
            print(f"  Deployments tracked: {len(env_info.deployments)}")
        elif env_info.environment_type == 'deployed':
            print(f"  Dev repo: {env_info.dev_repo_path or 'Not connected'}")

        print("  [OK] Deployment detection working")
        return True

    except Exception as e:
        print(f"  [ERROR] Deployment detection failed: {e}")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
