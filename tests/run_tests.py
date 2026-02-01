"""
UE5 Source Query - Comprehensive Test Suite Runner
Runs all test suites and reports results.
"""

import sys
import subprocess
from pathlib import Path

# Determine tool root
SCRIPT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

def run_all_tests():
    """Run all test suites"""
    print("=" * 70)
    print("UE5 Source Query - Comprehensive Test Suite")
    print("=" * 70)
    print()

    total_passed = 0
    total_failed = 0
    test_suites = []

    # 1. System Health Check
    print("[1/6] Running system health check...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ue5_query.utils.verify_installation"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(SCRIPT_DIR)
        )
        if result.returncode == 0:
            print(result.stdout)
            print("[SUCCESS] System health check passed\n")
            total_passed += 1
            test_suites.append(("System Health", "PASS"))
        elif result.returncode == 2:
            # Exit code 2 = warnings only (not critical failures)
            print(result.stdout)
            print("[SUCCESS] System health check passed (with warnings)\n")
            total_passed += 1
            test_suites.append(("System Health", "PASS"))
        else:
            print(result.stdout)
            print(result.stderr)
            print("[FAILED] System health check failed\n")
            total_failed += 1
            test_suites.append(("System Health", "FAIL"))
    except subprocess.TimeoutExpired:
        print("[FAILED] System health check timed out\n")
        total_failed += 1
        test_suites.append(("System Health", "FAIL"))
    except Exception as e:
        print(f"[FAILED] System health check failed: {e}\n")
        total_failed += 1
        test_suites.append(("System Health", "FAIL"))

    # 2. Vector Store Validation
    print("[2/6] Running vector store validation...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ue5_query.utils.verify_vector_store"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(SCRIPT_DIR)
        )
        if result.returncode == 0:
            print(result.stdout)
            print("[SUCCESS] Vector store validation passed\n")
            total_passed += 1
            test_suites.append(("Vector Store", "PASS"))
        else:
            print(result.stdout)
            print(result.stderr)
            print("[FAILED] Vector store validation failed\n")
            total_failed += 1
            test_suites.append(("Vector Store", "FAIL"))
    except subprocess.TimeoutExpired:
        print("[FAILED] Vector store validation timed out\n")
        total_failed += 1
        test_suites.append(("Vector Store", "FAIL"))
    except Exception as e:
        print(f"[FAILED] Vector store validation failed: {e}\n")
        total_failed += 1
        test_suites.append(("Vector Store", "FAIL"))

    # 3. Deployment Detection Tests
    print("[3/6] Running deployment detection tests...")
    try:
        test_file = SCRIPT_DIR / "tests" / "test_deployment_detection.py"
        if test_file.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("test_deployment_detection", test_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, 'run_tests'):
                if module.run_tests():
                    print("[SUCCESS] Deployment detection tests passed\n")
                    total_passed += 1
                    test_suites.append(("Deployment Detection", "PASS"))
                else:
                    print("[FAILED] Deployment detection tests failed\n")
                    total_failed += 1
                    test_suites.append(("Deployment Detection", "FAIL"))
            else:
                print("[SKIP] Deployment detection test module has no run_tests function\n")
                test_suites.append(("Deployment Detection", "SKIP"))
        else:
            print("[SKIP] Deployment detection test file not found\n")
            test_suites.append(("Deployment Detection", "SKIP"))
    except Exception as e:
        print(f"[FAILED] Deployment detection tests failed: {e}\n")
        total_failed += 1
        test_suites.append(("Deployment Detection", "FAIL"))

    # 4. Update Integration Tests
    print("[4/6] Running update integration tests...")
    try:
        test_file = SCRIPT_DIR / "tests" / "test_update_integration.py"
        if test_file.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("test_update_integration", test_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, 'run_tests'):
                if module.run_tests():
                    print("[SUCCESS] Update integration tests passed\n")
                    total_passed += 1
                    test_suites.append(("Update Integration", "PASS"))
                else:
                    print("[FAILED] Update integration tests failed\n")
                    total_failed += 1
                    test_suites.append(("Update Integration", "FAIL"))
            else:
                print("[SKIP] Update integration test module has no run_tests function\n")
                test_suites.append(("Update Integration", "SKIP"))
        else:
            print("[SKIP] Update integration test file not found\n")
            test_suites.append(("Update Integration", "SKIP"))
    except Exception as e:
        print(f"[FAILED] Update integration tests failed: {e}\n")
        total_failed += 1
        test_suites.append(("Update Integration", "FAIL"))

    # 5. GUI Smoke Test
    print("[5/6] Running GUI smoke test...")
    try:
        test_file = SCRIPT_DIR / "tests" / "test_gui_smoke.py"
        if test_file.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("test_gui_smoke", test_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, 'run_tests'):
                if module.run_tests():
                    print("[SUCCESS] GUI smoke test passed\n")
                    total_passed += 1
                    test_suites.append(("GUI Smoke", "PASS"))
                else:
                    print("[FAILED] GUI smoke test returned failure\n")
                    total_failed += 1
                    test_suites.append(("GUI Smoke", "FAIL"))
            else:
                print("[SKIP] GUI smoke test module has no run_tests function\n")
                test_suites.append(("GUI Smoke", "SKIP"))
        else:
            print("[SKIP] GUI smoke test file not found\n")
            test_suites.append(("GUI Smoke", "SKIP"))
    except Exception as e:
        print(f"[FAILED] GUI smoke test failed: {e}\n")
        total_failed += 1
        test_suites.append(("GUI Smoke", "FAIL"))

    # 6. Module Import Tests
    print("[6/6] Running module import smoke test...")
    try:
        print("Testing core module imports...")

        # Import core modules
        imports = [
            ("Core Query Engine", "ue5_query.core.hybrid_query"),
            ("Definition Extractor", "ue5_query.core.definition_extractor"),
            ("Query Intent", "ue5_query.core.query_intent"),
            ("Deployment Detector", "ue5_query.utils.deployment_detector"),
            ("Source Manager", "ue5_query.utils.source_manager"),
            ("Config Manager", "ue5_query.utils.config_manager"),
        ]

        import_passed = 0
        import_failed = 0

        for name, module_path in imports:
            try:
                __import__(module_path)
                print(f"  [OK] {name}")
                import_passed += 1
            except ImportError as e:
                print(f"  [ERROR] {name}: {e}")
                import_failed += 1

        print(f"\n[RESULT] {import_passed} passed, {import_failed} failed")

        if import_failed == 0:
            print("[SUCCESS] All imports successful\n")
            total_passed += 1
            test_suites.append(("Module Imports", "PASS"))
        else:
            print(f"[FAILED] {import_failed} import(s) failed\n")
            total_failed += 1
            test_suites.append(("Module Imports", "FAIL"))

    except Exception as e:
        print(f"[FAILED] Module import test failed: {e}\n")
        total_failed += 1
        test_suites.append(("Module Imports", "FAIL"))

    # Summary
    print()
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    print()

    for suite_name, status in test_suites:
        status_icon = "[PASS]" if status == "PASS" else ("[FAIL]" if status == "FAIL" else "[SKIP]")
        print(f"{status_icon} {suite_name}: {status}")

    print()
    print(f"Total: {total_passed} passed, {total_failed} failed, {len([s for s in test_suites if s[1] == 'SKIP'])} skipped")
    print("=" * 70)

    return total_failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
