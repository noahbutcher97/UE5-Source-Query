"""
UE5 Source Query Tool - Test Runner

Runs all tests and generates a report.
"""

import sys
import unittest
from pathlib import Path
from io import StringIO

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_all_tests(verbosity=2):
    """
    Run all tests in the tests directory

    Args:
        verbosity: Test output verbosity (0=quiet, 1=normal, 2=verbose)

    Returns:
        tuple: (success: bool, results_text: str)
    """
    # Discover all tests
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent
    suite = loader.discover(str(start_dir), pattern='test_*.py')

    # Capture output
    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=verbosity)

    # Run tests
    print("\n" + "="*70)
    print("UE5 Source Query Tool - Running Tests")
    print("="*70 + "\n")

    result = runner.run(suite)

    # Get output
    output = stream.getvalue()

    # Print summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print(f"Success Rate: {get_success_rate(result):.1f}%")
    print("="*70 + "\n")

    # Print failures and errors
    if result.failures:
        print("\n" + "="*70)
        print("FAILURES")
        print("="*70)
        for test, traceback in result.failures:
            print(f"\n{test}:")
            print(traceback)

    if result.errors:
        print("\n" + "="*70)
        print("ERRORS")
        print("="*70)
        for test, traceback in result.errors:
            print(f"\n{test}:")
            print(traceback)

    return result.wasSuccessful(), output


def get_success_rate(result):
    """Calculate test success rate"""
    if result.testsRun == 0:
        return 0.0
    failures = len(result.failures) + len(result.errors)
    successes = result.testsRun - failures
    return (successes / result.testsRun) * 100


def run_specific_test(test_module, test_class=None, test_method=None, verbosity=2):
    """
    Run a specific test module, class, or method

    Args:
        test_module: Module name (e.g., 'test_environment_detector')
        test_class: Optional class name (e.g., 'TestEnvVarStrategy')
        test_method: Optional method name (e.g., 'test_detect_with_ue5_engine_path')
        verbosity: Test output verbosity

    Returns:
        bool: True if all tests passed
    """
    loader = unittest.TestLoader()

    if test_method and test_class:
        # Load specific test method
        suite = loader.loadTestsFromName(f"{test_module}.{test_class}.{test_method}")
    elif test_class:
        # Load specific test class
        suite = loader.loadTestsFromName(f"{test_module}.{test_class}")
    else:
        # Load entire module
        suite = loader.loadTestsFromName(test_module)

    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    return result.wasSuccessful()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Run UE5 Source Query tests")
    parser.add_argument("-v", "--verbosity", type=int, default=2, choices=[0, 1, 2],
                        help="Test output verbosity (0=quiet, 1=normal, 2=verbose)")
    parser.add_argument("-m", "--module", type=str,
                        help="Run specific test module (e.g., test_environment_detector)")
    parser.add_argument("-c", "--class", type=str, dest="test_class",
                        help="Run specific test class (requires --module)")
    parser.add_argument("-t", "--test", type=str, dest="test_method",
                        help="Run specific test method (requires --module and --class)")
    parser.add_argument("--list", action="store_true",
                        help="List all available tests")

    args = parser.parse_args()

    if args.list:
        list_tests()
        return 0

    if args.module:
        # Run specific test
        success = run_specific_test(
            args.module,
            args.test_class,
            args.test_method,
            args.verbosity
        )
    else:
        # Run all tests
        success, _ = run_all_tests(args.verbosity)

    return 0 if success else 1


def list_tests():
    """List all available tests"""
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent
    suite = loader.discover(str(start_dir), pattern='test_*.py')

    print("\n" + "="*70)
    print("Available Tests")
    print("="*70 + "\n")

    def print_suite(suite, indent=0):
        for test in suite:
            if isinstance(test, unittest.TestSuite):
                print_suite(test, indent)
            else:
                test_str = str(test)
                # Extract module.class.method
                parts = test_str.split()
                if parts:
                    test_name = parts[0]
                    print("  " * indent + test_name)

    print_suite(suite)
    print()


if __name__ == "__main__":
    sys.exit(main())
