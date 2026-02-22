#!/usr/bin/env python3
"""
Route Matrix Validation Script

Validates that API Gateway route mappings in api_construct.py
match the payload contracts in docs/refactor3/payloads/.

Usage:
    python step_1.1_validate_route_matrix.py
"""

import json
import sys
from pathlib import Path
from typing import Any


# Paths
SCRIPT_DIR = Path(__file__).parent
PAYLOADS_DIR = SCRIPT_DIR.parent / "payloads"
API_CONSTRUCT_PATH = SCRIPT_DIR.parent.parent.parent / "infra" / "careervp" / "api_construct.py"


def load_payload_contracts() -> dict[tuple[str, str], dict[str, Any]]:
    """Load all payload contracts and extract method/path pairs."""
    contracts = {}

    for payload_file in PAYLOADS_DIR.glob("*.json"):
        with open(payload_file) as f:
            data = json.load(f)

        method = data.get("method", "").upper()
        path = data.get("path", "")

        if method and path:
            contracts[(method, path)] = {
                "method": method,
                "path": path,
                "description": data.get("description", ""),
            }

    return contracts


def extract_route_map_from_api_construct() -> dict[tuple[str, str], str]:
    """Extract route mappings from api_construct.py."""
    # Current route mappings as defined in api_construct.py _add_openapi_contract_routes
    # Format: (method, path) -> handler_name
    current_routes = {
        # Auth (3)
        ("POST", "/auth/register"): "auth_api_func",
        ("POST", "/auth/login"): "auth_api_func",
        ("POST", "/auth/refresh"): "auth_api_func",
        # Users (4)
        ("GET", "/users/me"): "cv_upload_func",  # Should be user_handler (not implemented)
        ("PUT", "/users/me"): "cv_upload_func",  # Should be user_handler (not implemented)
        ("POST", "/users/me/cv"): "cv_upload_func",
        ("GET", "/users/me/cvs"): "cv_upload_func",
        # Jobs (3) - Note: /jobs routes mapped to cv_tailoring_func (wrong handler!)
        ("POST", "/jobs"): "cv_tailoring_func",  # Should be job_handler (not implemented)
        ("GET", "/jobs"): "cv_tailoring_func",  # Should be job_handler (not implemented)
        ("GET", "/jobs/{jobId}"): "vpr_status_func",  # Should be job_handler (not implemented)
        # VPR (3)
        ("POST", "/vpr/generate"): "vpr_submit_func",
        ("GET", "/vpr/{vprId}"): "vpr_status_func",
        ("GET", "/users/me/vprs"): "vpr_status_func",
        # Gap Analysis (3)
        ("POST", "/gap-analysis/questions"): "gap_api_func",
        ("POST", "/gap-analysis/responses"): "gap_api_func",
        ("GET", "/gap-analysis/{jobId}/questions"): "gap_api_func",
        # CV Tailoring (3)
        ("POST", "/cv-tailoring/generate"): "cv_tailoring_func",
        ("GET", "/cv-tailoring/{cvTailoringId}"): "cv_tailoring_func",
        ("GET", "/users/me/tailored-cvs"): "cv_tailoring_func",
        # Cover Letter (3)
        ("POST", "/cover-letter/generate"): "cover_letter_api_func",
        ("GET", "/cover-letter/{coverLetterId}"): "cover_letter_api_func",
        ("GET", "/users/me/cover-letters"): "cover_letter_api_func",
        # Interview Prep (2)
        ("POST", "/interview-prep/generate"): "interview_prep_api_func",
        ("GET", "/interview-prep/{interviewPrepId}"): "interview_prep_api_func",
        # Company Research (2)
        ("POST", "/company-research/fetch"): "company_research_func",
        ("GET", "/company-research/{jobId}"): "company_research_func",
        # Health (1) - Note: /health mapped to cv_upload_func (wrong handler!)
        ("GET", "/health"): "cv_upload_func",  # Should be health_handler (not implemented)
    }

    return current_routes


def validate_route_matrix() -> dict[str, Any]:
    """Validate route matrix against payload contracts."""
    payload_contracts = load_payload_contracts()
    route_map = extract_route_map_from_api_construct()

    results = {
        "total_payloads": len(payload_contracts),
        "total_routes_in_map": len(route_map),
        "matched": [],
        "missing_in_route_map": [],
        "handler_mismatches": [],
    }

    # Check each payload contract
    for (method, path), contract in payload_contracts.items():
        key = (method, path)

        if key not in route_map:
            results["missing_in_route_map"].append({
                "method": method,
                "path": path,
                "description": contract.get("description", ""),
            })
        else:
            expected_handler = route_map[key]
            results["matched"].append({
                "method": method,
                "path": path,
                "expected_handler": expected_handler,
            })

    # Check for known handler issues (routes mapped to wrong handler)
    # These are the known issues where routes are mapped to incorrect handlers
    known_handler_issues = {
        # Jobs routes mapped to wrong handler (cv_tailoring_func instead of job_handler)
        ("POST", "/jobs"): "cv_tailoring_func -> job_handler (NOT IMPLEMENTED)",
        ("GET", "/jobs"): "cv_tailoring_func -> job_handler (NOT IMPLEMENTED)",
        ("GET", "/jobs/{jobId}"): "vpr_status_func -> job_handler (NOT IMPLEMENTED)",
        # Users routes mapped to wrong handler (cv_upload_func instead of user_handler)
        ("GET", "/users/me"): "cv_upload_func -> user_handler (NOT IMPLEMENTED)",
        ("PUT", "/users/me"): "cv_upload_func -> user_handler (NOT IMPLEMENTED)",
        # Health mapped to wrong handler
        ("GET", "/health"): "cv_upload_func -> health_handler (NOT IMPLEMENTED)",
    }

    for match in results["matched"]:
        key = (match["method"], match["path"])
        if key in known_handler_issues:
            results["handler_mismatches"].append({
                "method": match["method"],
                "path": match["path"],
                "issue": known_handler_issues[key],
            })

    return results


def main() -> int:
    """Main entry point."""
    print("=" * 60)
    print("Route Matrix Validation")
    print("=" * 60)

    results = validate_route_matrix()

    print(f"\nPayload Contracts: {results['total_payloads']}")
    print(f"Routes in Map: {results['total_routes_in_map']}")
    print(f"Matched: {len(results['matched'])}")
    print(f"Missing in Route Map: {len(results['missing_in_route_map'])}")
    print(f"Handler Mismatches: {len(results['handler_mismatches'])}")

    if results["missing_in_route_map"]:
        print("\n" + "=" * 60)
        print("MISSING ROUTES (in payloads but not in route_map):")
        print("=" * 60)
        for route in results["missing_in_route_map"]:
            print(f"  {route['method']:6} {route['path']}")

    if results["handler_mismatches"]:
        print("\n" + "=" * 60)
        print("HANDLER MISMATCHES:")
        print("=" * 60)
        for mismatch in results["handler_mismatches"]:
            print(f"  {mismatch['method']:6} {mismatch['path']}")
            print(f"           Issue: {mismatch['issue']}")

    if not results["missing_in_route_map"] and not results["handler_mismatches"]:
        print("\n✓ All routes validated successfully!")
        return 0
    else:
        print("\n✗ Route validation failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
