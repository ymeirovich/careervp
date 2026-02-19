#!/usr/bin/env python3
"""
Live Test Runner - CareerVP API End-to-End Tests

This script runs all live tests for the CareerVP API endpoints.
Tests can be run individually or as a full suite.

Usage:
    python run_all_tests.py                    # Run all tests
    python run_all_tests.py --test health      # Run specific test
    python run_all_tests.py --list             # List available tests
    python run_all_tests.py --verbose           # Verbose output
    python run_all_tests.py --dry-run          # Show what would run

Environment Variables:
    API_BASE           - API base URL (default: https://api.careervp.com/v1)
    TEST_USER_ID       - Test user ID (default: test-user-e2e)
    API_KEY            - API key for authenticated requests
    USE_AUTH           - Whether to use authentication (default: false)

Examples:
    API_BASE=https://staging-api.careervp.com/v1 python run_all_tests.py
    python run_all_tests.py --test auth --verbose
"""

import os
import sys
import argparse
import importlib

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# Test module mapping
TEST_MODULES = {
    "health": ("test_01_auth_health", ["TestHealthEndpoint"]),
    "auth": ("test_01_auth_health", ["TestAuthEndpoints"]),
    "users": ("test_02_users", ["TestUserEndpoints"]),
    "jobs": ("test_03_jobs", ["TestJobEndpoints"]),
    "vpr": ("test_04_vpr", ["TestVPREndpoints"]),
    "gap": ("test_05_gap_analysis", ["TestGapAnalysisEndpoints"]),
    "gap-analysis": ("test_05_gap_analysis", ["TestGapAnalysisEndpoints"]),
    "tailoring": ("test_06_cv_tailoring", ["TestCVTailoringEndpoints"]),
    "cv-tailoring": ("test_06_cv_tailoring", ["TestCVTailoringEndpoints"]),
    "cover-letter": ("test_07_cover_letter", ["TestCoverLetterEndpoints"]),
    "cover": ("test_07_cover_letter", ["TestCoverLetterEndpoints"]),
    "interview": ("test_08_interview_prep", ["TestInterviewPrepEndpoints"]),
    "interview-prep": ("test_08_interview_prep", ["TestInterviewPrepEndpoints"]),
    "company": ("test_09_company_research", ["TestCompanyResearchEndpoints"]),
    "company-research": ("test_09_company_research", ["TestCompanyResearchEndpoints"]),
}


def list_tests():
    """List all available tests."""
    print("Available test modules:")
    print("-" * 50)

    for name, (module, classes) in sorted(TEST_MODULES.items()):
        for cls in classes:
            print(f"  {name:20} -> {module}.{cls}")

    print()
    print("Run with: python run_all_tests.py --test <name>")


def run_test_module(module_name: str, class_names: list, verbose: bool = False):
    """Run tests from a specific module."""
    print(f"\n{'=' * 60}")
    print(f"Running: {module_name}")
    print(f"{'=' * 60}")

    try:
        module = importlib.import_module(module_name)

        for class_name in class_names:
            cls = getattr(module, class_name)

            # Get all test methods
            test_methods = [m for m in dir(cls) if m.startswith("test_")]

            for method_name in test_methods:
                method = getattr(cls, method_name)

                # Create instance and run
                instance = cls()

                # Setup if exists
                if hasattr(instance, "setup"):
                    instance.setup()
                elif hasattr(instance, "setup_method"):
                    instance.setup_method(None)

                try:
                    if verbose:
                        print(f"\n  Running: {method_name}")

                    method()

                    if verbose:
                        print("    ✓ Passed")

                except Exception as e:
                    print(f"    ✗ Failed: {e}")
                    if verbose:
                        import traceback

                        traceback.print_exc()

                # Teardown if exists
                if hasattr(instance, "teardown"):
                    try:
                        instance.teardown()
                    except Exception:
                        pass

    except ImportError as e:
        print(f"  Error importing {module_name}: {e}")
    except Exception as e:
        print(f"  Error running {module_name}: {e}")


def run_all_tests(verbose: bool = False):
    """Run all tests in sequence."""
    print("\n" + "=" * 60)
    print("CareerVP Live Test Suite")
    print("=" * 60)

    # Set configuration
    api_base = os.environ.get("API_BASE", "https://api.careervp.com/v1")
    test_user = os.environ.get("TEST_USER_ID", "test-user-e2e")

    print("\nConfiguration:")
    print(f"  API Base: {api_base}")
    print(f"  Test User: {test_user}")
    print(f"  Auth Enabled: {os.environ.get('USE_AUTH', 'false')}")

    # Run tests in order (dependencies matter!)
    test_order = [
        "health",
        "auth",
        "users",
        "jobs",
        "company",
        "vpr",
        "gap",
        "tailoring",
        "cover-letter",
        "interview",
    ]

    passed = 0
    failed = 0

    for test_name in test_order:
        if test_name in TEST_MODULES:
            try:
                module_name, class_names = TEST_MODULES[test_name]
                run_test_module(module_name, class_names, verbose)
                passed += 1
            except Exception as e:
                print(f"Error in {test_name}: {e}")
                failed += 1

    print("\n" + "=" * 60)
    print("Test Suite Complete")
    print(f"  Modules Passed: {passed}")
    print(f"  Modules Failed: {failed}")
    print("=" * 60 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="CareerVP Live Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--test", "-t", help="Run specific test (e.g., health, auth, vpr)"
    )

    parser.add_argument(
        "--list", "-l", action="store_true", help="List available tests"
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would run without executing"
    )

    args = parser.parse_args()

    if args.list:
        list_tests()
        return

    if args.test:
        test_key = args.test.lower()

        if test_key in TEST_MODULES:
            if args.dry_run:
                module_name, class_names = TEST_MODULES[test_key]
                print(f"Would run: {module_name}.{class_names}")
            else:
                module_name, class_names = TEST_MODULES[test_key]
                run_test_module(module_name, class_names, args.verbose)
        else:
            print(f"Unknown test: {args.test}")
            print("Use --list to see available tests")
            sys.exit(1)
    else:
        if args.dry_run:
            print("Would run all tests:")
            for name in TEST_MODULES.keys():
                module_name, class_names = TEST_MODULES[name]
                print(f"  {name} -> {module_name}.{class_names}")
        else:
            run_all_tests(args.verbose)


if __name__ == "__main__":
    main()
