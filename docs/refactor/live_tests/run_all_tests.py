#!/usr/bin/env python3
"""
Live Test Runner - CareerVP API End-to-End Tests

This script runs all live tests for the CareerVP API endpoints.
Tests can be run individually or as a full suite.

Usage:
    python run_all_tests.py                    # Run full suite
    python run_all_tests.py --mode smoke       # Run smoke subset
    python run_all_tests.py --test health      # Run specific test
    python run_all_tests.py --list             # List available tests
    python run_all_tests.py --verbose           # Verbose output
    python run_all_tests.py --dry-run          # Show what would run

Environment Variables:
    API_BASE           - API base URL (resolved via resolve_api_base.py)
    STACK_NAME         - CloudFormation stack name (default: careervp-api)
    TEST_USER_ID       - Test user ID (default: test-user-e2e)
    API_KEY            - API key for authenticated requests
    USE_AUTH           - Whether to use authentication (default: true)

Examples:
    API_BASE=https://staging-api.careervp.com/v1 python run_all_tests.py
    python run_all_tests.py --test auth --verbose
"""

import os
import sys
import argparse
import json
from datetime import datetime, timezone
from typing import List

import pytest

# Add scripts directory to path for resolve_api_base
# Go up 2 levels: live_tests -> refactor -> docs, then into refactor3/scripts
SCRIPTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "refactor3",
    "scripts",
)
sys.path.insert(0, SCRIPTS_DIR)

from resolve_api_base import resolve_api_base  # type: ignore[import-not-found]  # noqa: E402

# Add current directory to path
LIVE_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, LIVE_TESTS_DIR)


# Test module mapping
TEST_MODULES = {
    "bootstrap": ("test_00_auth_bootstrap", ["TestAuthBootstrap"]),
    "auth-bootstrap": ("test_00_auth_bootstrap", ["TestAuthBootstrap"]),
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
    "contract": ("test_10_api_contract_success", ["TestAPIContractSuccess"]),
    "strict": ("test_10_api_contract_success", ["TestAPIContractSuccess"]),
    "api-contract-success": (
        "test_10_api_contract_success",
        ["TestAPIContractSuccess"],
    ),
    "errors": ("test_11_api_error_contracts", ["TestAPIErrorContracts"]),
    "api-errors": ("test_11_api_error_contracts", ["TestAPIErrorContracts"]),
    "error-contracts": ("test_11_api_error_contracts", ["TestAPIErrorContracts"]),
}


def list_tests() -> None:
    """List all available tests."""
    print("Available test modules:")
    print("-" * 50)

    for name, (module, classes) in sorted(TEST_MODULES.items()):
        for cls in classes:
            print(f"  {name:20} -> {module}.{cls}")

    print()
    print("Run with: python run_all_tests.py --test <name>")


def run_test_module(
    module_name: str, class_names: List[str], verbose: bool = False
) -> tuple[bool, int]:
    """Run tests from a specific module/class list with pytest."""
    print(f"\n{'=' * 60}")
    print(f"Running: {module_name}")
    print(f"{'=' * 60}")

    module_file = os.path.join(LIVE_TESTS_DIR, f"{module_name}.py")
    node_ids = [f"{module_file}::{class_name}" for class_name in class_names]
    pytest_args: List[str] = ["-s"]
    pytest_args.extend(node_ids)

    if verbose:
        pytest_args.insert(0, "-v")
    else:
        pytest_args.insert(0, "-q")

    exit_code = pytest.main(pytest_args)
    if exit_code != 0:
        print(f"  ✗ {module_name} failed with pytest exit code {exit_code}")
        return False, exit_code

    print(f"  ✓ {module_name} passed")
    return True, 0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_summary(summary_path: str, summary: dict[str, object]) -> None:
    out_path = os.path.abspath(summary_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    print(f"\nSummary written: {out_path}")


def _reset_trial(api_base: str) -> None:
    """Reset trial credits and fail fast when reset verification fails."""
    import requests as _requests

    sys.path.insert(0, LIVE_TESTS_DIR)
    from conftest import get_auth_headers  # type: ignore[import-not-found]  # noqa: PLC0415

    headers = get_auth_headers()
    reset_resp = _requests.post(
        f"{api_base}/users/me/trial/reset",
        headers=headers,
        timeout=15,
    )
    if reset_resp.status_code != 200:
        raise RuntimeError(
            f"Trial reset returned {reset_resp.status_code}: {reset_resp.text[:300]}"
        )

    usage_resp = _requests.get(
        f"{api_base}/users/me/usage",
        headers=headers,
        timeout=15,
    )
    if usage_resp.status_code != 200:
        raise RuntimeError(
            f"Trial usage check returned {usage_resp.status_code}: {usage_resp.text[:300]}"
        )

    usage_payload = usage_resp.json()
    used = int(usage_payload.get("applications", {}).get("used", -1))
    if used != 0:
        raise RuntimeError(f"Trial reset verification failed: applications.used={used}")

    print("  ✓ Trial reset (verified used=0)")


def run_all_tests(
    verbose: bool = False, mode: str = "full"
) -> tuple[int, dict[str, object]]:
    """Run all tests in sequence."""
    print("\n" + "=" * 60)
    print("CareerVP Live Test Suite")
    print("=" * 60)

    # Resolve API_BASE using single-source resolver
    api_base = resolve_api_base()
    test_user = os.environ.get("TEST_USER_ID", "test-user-e2e")

    print("\nConfiguration:")
    print(f"  API Base: {api_base}")
    print(f"  Test User: {test_user}")
    print(f"  Auth Enabled: {os.environ.get('USE_AUTH', 'true')}")

    summary: dict[str, object] = {
        "runner": "careervp-live-tests",
        "executed_at_utc": _utc_now(),
        "mode": mode,
        "api_base": api_base,
        "test_user": test_user,
        "auth_enabled": os.environ.get("USE_AUTH", "true"),
        "modules": [],
        "errors": [],
    }

    # Reset trial credits so tests are never blocked by exhausted limits
    print("\nPre-flight:")
    try:
        _reset_trial(api_base)
    except Exception as exc:
        err = f"Pre-flight trial reset failed: {exc}"
        print(f"  ✗ {err}")
        summary["errors"] = [err]
        summary["totals"] = {"selected": 0, "passed": 0, "failed": 1}
        summary["non_2xx_count"] = 1
        summary["empty_array_count"] = 0
        summary["generated_id_missing_count"] = 0
        summary["status"] = "fail"
        summary["exit_code"] = 1
        return 1, summary

    # Run tests in order (dependencies matter!)
    full_order = [
        "bootstrap",
        "health",
        "auth",
        "users",
        "jobs",
        "company",
        "gap",
        "vpr",
        "tailoring",
        "cover-letter",
        "interview",
        "contract",
        "errors",
    ]
    smoke_order = ["bootstrap", "health", "auth"]
    test_order = smoke_order if mode == "smoke" else full_order

    passed = 0
    failed = 0
    module_results: list[dict[str, object]] = []

    for test_name in test_order:
        if test_name in TEST_MODULES:
            module_name, class_names = TEST_MODULES[test_name]
            try:
                if test_name == "contract":
                    print("\nPre-contract reset:")
                    try:
                        _reset_trial(api_base)
                    except Exception as exc:
                        err = f"Pre-contract trial reset failed: {exc}"
                        print(f"  ✗ {err}")
                        module_results.append(
                            {
                                "name": test_name,
                                "module_name": module_name,
                                "class_names": class_names,
                                "status": "fail",
                                "pytest_exit_code": 1,
                                "error": err,
                            }
                        )
                        failed += 1
                        continue
                ok, module_exit_code = run_test_module(
                    module_name, class_names, verbose
                )
                if ok:
                    passed += 1
                    module_results.append(
                        {
                            "name": test_name,
                            "module_name": module_name,
                            "class_names": class_names,
                            "status": "pass",
                            "pytest_exit_code": 0,
                        }
                    )
                else:
                    failed += 1
                    module_results.append(
                        {
                            "name": test_name,
                            "module_name": module_name,
                            "class_names": class_names,
                            "status": "fail",
                            "pytest_exit_code": module_exit_code,
                        }
                    )
            except Exception as e:
                print(f"Error in {test_name}: {e}")
                failed += 1
                module_results.append(
                    {
                        "name": test_name,
                        "module_name": module_name,
                        "class_names": class_names,
                        "status": "error",
                        "pytest_exit_code": 1,
                        "error": str(e),
                    }
                )

    print("\n" + "=" * 60)
    print("Test Suite Complete")
    print(f"  Modules Passed: {passed}")
    print(f"  Modules Failed: {failed}")
    print("=" * 60 + "\n")

    exit_code = 0 if failed == 0 else 1
    summary["modules"] = module_results
    summary["totals"] = {
        "selected": len(test_order),
        "passed": passed,
        "failed": failed,
    }
    summary["non_2xx_count"] = failed
    summary["empty_array_count"] = 0
    summary["generated_id_missing_count"] = 0
    summary["status"] = "pass" if exit_code == 0 else "fail"
    summary["exit_code"] = exit_code
    return exit_code, summary


def main() -> None:
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
        "--mode",
        choices=["full", "smoke"],
        default="full",
        help="Run mode: full suite or smoke subset (default: full)",
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would run without executing"
    )
    parser.add_argument(
        "--summary-json",
        help="Optional path to write machine-readable run summary JSON",
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
                module_file = os.path.join(LIVE_TESTS_DIR, f"{module_name}.py")
                node_ids = [
                    f"{module_file}::{class_name}" for class_name in class_names
                ]
                print(f"Would run: {', '.join(node_ids)}")
                summary = {
                    "runner": "careervp-live-tests",
                    "executed_at_utc": _utc_now(),
                    "mode": "single-dry-run",
                    "requested_test": test_key,
                    "modules": [
                        {
                            "name": test_key,
                            "module_name": module_name,
                            "class_names": class_names,
                            "status": "dry_run",
                        }
                    ],
                    "totals": {"selected": 1, "passed": 0, "failed": 0},
                    "non_2xx_count": 0,
                    "empty_array_count": 0,
                    "generated_id_missing_count": 0,
                    "status": "pass",
                    "exit_code": 0,
                }
                if args.summary_json:
                    _write_summary(args.summary_json, summary)
            else:
                # Reset trial before running individual tests
                api_base = resolve_api_base()
                print("\nPre-flight:")
                summary = {
                    "runner": "careervp-live-tests",
                    "executed_at_utc": _utc_now(),
                    "mode": "single",
                    "requested_test": test_key,
                    "api_base": api_base,
                    "test_user": os.environ.get("TEST_USER_ID", "test-user-e2e"),
                    "auth_enabled": os.environ.get("USE_AUTH", "true"),
                    "modules": [],
                    "errors": [],
                }
                try:
                    _reset_trial(api_base)
                except Exception as exc:
                    err = f"Pre-flight trial reset failed: {exc}"
                    print(f"  ✗ {err}")
                    summary["errors"] = [err]
                    summary["totals"] = {"selected": 1, "passed": 0, "failed": 1}
                    summary["non_2xx_count"] = 1
                    summary["empty_array_count"] = 0
                    summary["generated_id_missing_count"] = 0
                    summary["status"] = "fail"
                    summary["exit_code"] = 1
                    if args.summary_json:
                        _write_summary(args.summary_json, summary)
                    sys.exit(1)

                module_name, class_names = TEST_MODULES[test_key]
                ok, module_exit_code = run_test_module(
                    module_name, class_names, args.verbose
                )
                failed = 0 if ok else 1
                summary["modules"] = [
                    {
                        "name": test_key,
                        "module_name": module_name,
                        "class_names": class_names,
                        "status": "pass" if ok else "fail",
                        "pytest_exit_code": module_exit_code,
                    }
                ]
                summary["totals"] = {
                    "selected": 1,
                    "passed": 1 if ok else 0,
                    "failed": failed,
                }
                summary["non_2xx_count"] = failed
                summary["empty_array_count"] = 0
                summary["generated_id_missing_count"] = 0
                summary["status"] = "pass" if ok else "fail"
                summary["exit_code"] = 0 if ok else 1
                if args.summary_json:
                    _write_summary(args.summary_json, summary)
                if not ok:
                    sys.exit(1)
        else:
            print(f"Unknown test: {args.test}")
            print("Use --list to see available tests")
            sys.exit(1)
    else:
        if args.dry_run:
            print("Would run all tests:")
            seen = set()
            test_order = (
                ["bootstrap", "health", "auth"]
                if args.mode == "smoke"
                else [
                    "bootstrap",
                    "health",
                    "auth",
                    "users",
                    "jobs",
                    "company",
                    "gap",
                    "vpr",
                    "tailoring",
                    "cover-letter",
                    "interview",
                    "contract",
                    "errors",
                ]
            )
            for name in test_order:
                if name in TEST_MODULES:
                    module_name, class_names = TEST_MODULES[name]
                    key = (module_name, tuple(class_names))
                    if key in seen:
                        continue
                    seen.add(key)
                    module_file = os.path.join(LIVE_TESTS_DIR, f"{module_name}.py")
                    node_ids = [
                        f"{module_file}::{class_name}" for class_name in class_names
                    ]
                    print(f"  {name} -> {', '.join(node_ids)}")
            if args.summary_json:
                summary_modules = []
                for name in test_order:
                    if name not in TEST_MODULES:
                        continue
                    module_name, class_names = TEST_MODULES[name]
                    summary_modules.append(
                        {
                            "name": name,
                            "module_name": module_name,
                            "class_names": class_names,
                            "status": "dry_run",
                        }
                    )
                summary = {
                    "runner": "careervp-live-tests",
                    "executed_at_utc": _utc_now(),
                    "mode": f"{args.mode}-dry-run",
                    "modules": summary_modules,
                    "totals": {
                        "selected": len(summary_modules),
                        "passed": 0,
                        "failed": 0,
                    },
                    "non_2xx_count": 0,
                    "empty_array_count": 0,
                    "generated_id_missing_count": 0,
                    "status": "pass",
                    "exit_code": 0,
                }
                _write_summary(args.summary_json, summary)
        else:
            exit_code, summary = run_all_tests(args.verbose, args.mode)
            if args.summary_json:
                _write_summary(args.summary_json, summary)
            sys.exit(exit_code)


if __name__ == "__main__":
    main()
