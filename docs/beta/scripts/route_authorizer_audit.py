"""
Route Authorizer Audit — generates docs/beta/evidence/I3_auth/route-authorizer-audit.json

Usage:
    python docs/beta/scripts/route_authorizer_audit.py

Reads deployed API Gateway routes from CloudFormation and compares each route's
authorizer type against the expected type from EXPECTED_AUTHORIZERS. Flags mismatches.

Implements: cognito-test-fixes/PLAN.md T4 / SPEC.md FIX C-C

Exit codes:
    0 — all routes match expected authorizers
    1 — mismatches detected or script error
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path


# Expected authorizer type per (method, path_pattern).
# NONE      = no authorizer (public route)
# COGNITO_USER_POOLS = Cognito User Pools authorizer (protected route)
EXPECTED_AUTHORIZERS: dict[tuple[str, str], str] = {
    ("GET", "/health"): "NONE",
    ("POST", "/auth/register"): "NONE",
    ("POST", "/auth/login"): "NONE",
    ("POST", "/auth/refresh"): "NONE",
    ("GET", "/users/me"): "COGNITO_USER_POOLS",
    ("PUT", "/users/me"): "COGNITO_USER_POOLS",
    ("POST", "/users/me/cv"): "COGNITO_USER_POOLS",
    ("GET", "/users/me/cvs"): "COGNITO_USER_POOLS",
    ("GET", "/users/me/vprs"): "COGNITO_USER_POOLS",
    ("GET", "/users/me/tailored-cvs"): "COGNITO_USER_POOLS",
    ("GET", "/users/me/cover-letters"): "COGNITO_USER_POOLS",
    ("GET", "/users/me/usage"): "COGNITO_USER_POOLS",
    ("POST", "/jobs"): "COGNITO_USER_POOLS",
    ("GET", "/jobs"): "COGNITO_USER_POOLS",
    ("GET", "/jobs/{jobId}"): "COGNITO_USER_POOLS",
    ("POST", "/company-research/fetch"): "COGNITO_USER_POOLS",
    ("GET", "/company-research/{jobId}"): "COGNITO_USER_POOLS",
    ("POST", "/gap-analysis/questions"): "COGNITO_USER_POOLS",
    ("POST", "/gap-analysis/responses"): "COGNITO_USER_POOLS",
    ("GET", "/gap-analysis/{jobId}/questions"): "COGNITO_USER_POOLS",
    ("POST", "/vpr/generate"): "COGNITO_USER_POOLS",
    ("GET", "/vpr/{vprId}"): "COGNITO_USER_POOLS",
    ("POST", "/cv-tailoring/generate"): "COGNITO_USER_POOLS",
    ("GET", "/cv-tailoring/{cvTailoringId}"): "COGNITO_USER_POOLS",
    ("POST", "/cover-letter/generate"): "COGNITO_USER_POOLS",
    ("GET", "/cover-letter/{coverLetterId}"): "COGNITO_USER_POOLS",
    ("POST", "/interview-prep/generate"): "COGNITO_USER_POOLS",
    ("GET", "/interview-prep/{interviewPrepId}"): "COGNITO_USER_POOLS",
    ("GET", "/applications/{applicationId}"): "COGNITO_USER_POOLS",
}

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_PATH = SCRIPT_DIR.parent / "evidence" / "I3_auth" / "route-authorizer-audit.json"


def _discover_api_id(cfn_client, stack_name: str) -> str:
    response = cfn_client.describe_stacks(StackName=stack_name)
    outputs = {
        o["OutputKey"]: o["OutputValue"]
        for o in response["Stacks"][0].get("Outputs", [])
    }
    api_id = (
        outputs.get("ApiId") or outputs.get("RestApiId") or outputs.get("ApiGatewayId")
    )
    if not api_id:
        available = list(outputs.keys())
        raise RuntimeError(
            f"Could not find ApiId/RestApiId in stack {stack_name!r} outputs. "
            f"Available keys: {available}"
        )
    return api_id


def _get_all_resources(apigw_client, api_id: str) -> list[dict]:
    resources: list[dict] = []
    kwargs: dict = {"restApiId": api_id, "limit": 500}
    while True:
        page = apigw_client.get_resources(**kwargs)
        resources.extend(page.get("items", []))
        pos = page.get("position")
        if not pos:
            break
        kwargs["position"] = pos
    return resources


def _build_authorizer_map(apigw_client, api_id: str) -> dict[str, dict]:
    resp = apigw_client.get_authorizers(restApiId=api_id)
    return {a["id"]: a for a in resp.get("items", [])}


def _route_matches_expected(
    actual_auth: str, expected: str, authorizer_name: str | None
) -> bool:
    if actual_auth == expected:
        return True
    # A COGNITO_USER_POOLS route may appear as CUSTOM if a Lambda authorizer is used.
    # Accept CUSTOM only when expected is COGNITO_USER_POOLS AND the authorizer has a name.
    if expected == "COGNITO_USER_POOLS" and actual_auth == "CUSTOM" and authorizer_name:
        return True
    return False


def audit_routes() -> dict:
    try:
        import boto3
    except ImportError:
        print("ERROR: boto3 not installed. Run: pip install boto3", file=sys.stderr)
        sys.exit(1)

    region = (
        os.environ.get("AWS_REGION") or os.environ.get("COGNITO_REGION") or "us-east-1"
    )
    stack_name = os.environ.get("STACK_NAME", "CareerVpCrudDev")

    print(f"Connecting to region={region!r}, stack={stack_name!r} ...")

    cfn = boto3.client("cloudformation", region_name=region)
    try:
        api_id = _discover_api_id(cfn, stack_name)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Discovered API ID: {api_id}")

    apigw = boto3.client("apigateway", region_name=region)
    resources = _get_all_resources(apigw, api_id)
    authorizer_map = _build_authorizer_map(apigw, api_id)

    results: list[dict] = []
    mismatches = 0
    unchecked = 0

    for resource in resources:
        path = resource.get("path", "")
        resource_id = resource["id"]
        methods = resource.get("resourceMethods", {})

        for method in methods:
            if method == "OPTIONS":
                continue

            try:
                full_method = apigw.get_method(
                    restApiId=api_id,
                    resourceId=resource_id,
                    httpMethod=method,
                )
            except Exception as exc:
                print(
                    f"  WARN: Could not fetch {method} {path}: {exc}", file=sys.stderr
                )
                continue

            actual_auth = full_method.get("authorizationType", "NONE")
            authorizer_id = full_method.get("authorizerId")
            authorizer_name: str | None = None
            if authorizer_id and authorizer_id in authorizer_map:
                auth_info = authorizer_map[authorizer_id]
                authorizer_name = auth_info.get("name")
                # Resolve actual type from authorizer definition
                auth_type_from_def = auth_info.get("type", "")
                if auth_type_from_def == "COGNITO_USER_POOLS":
                    actual_auth = "COGNITO_USER_POOLS"

            expected = EXPECTED_AUTHORIZERS.get((method, path))
            if expected is None:
                # Route exists in deployed API but not in our expected table
                unchecked += 1
                status = "UNCHECKED"
                match = None
            else:
                match = _route_matches_expected(actual_auth, expected, authorizer_name)
                if not match:
                    mismatches += 1
                status = "OK" if match else "MISMATCH"

            results.append(
                {
                    "method": method,
                    "path": path,
                    "actual_auth_type": actual_auth,
                    "authorizer_name": authorizer_name,
                    "expected_auth_type": expected,
                    "match": match,
                    "status": status,
                }
            )

    results.sort(key=lambda r: (r["path"], r["method"]))

    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "stack_name": stack_name,
        "api_id": api_id,
        "region": region,
        "total_routes_checked": len(results),
        "mismatches": mismatches,
        "unchecked_routes": unchecked,
        "pass": mismatches == 0,
        "routes": results,
    }
    return report


def main() -> None:
    report = audit_routes()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    mismatch_count = report["mismatches"]
    total = report["total_routes_checked"]
    unchecked = report["unchecked_routes"]

    print("\nRoute Authorizer Audit Summary")
    print(f"  Total routes checked : {total}")
    print(f"  Mismatches           : {mismatch_count}")
    print(f"  Unchecked (new)      : {unchecked}")
    print(f"  Report written to    : {OUT_PATH}")

    if mismatch_count > 0:
        print("\nMISMATCHES DETECTED:")
        for r in report["routes"]:
            if r["status"] == "MISMATCH":
                print(
                    f"  {r['method']:6s} {r['path']:<50s} "
                    f"expected={r['expected_auth_type']} actual={r['actual_auth_type']}"
                )
        print("\nFAIL: Fix route authorizer mismatches before merging.")
        sys.exit(1)
    else:
        print("\nPASS: All route authorizers match expected configuration.")
        if unchecked > 0:
            print(
                f"NOTE: {unchecked} routes are not in the EXPECTED_AUTHORIZERS table. "
                "Update the table in this script if they are intentional new routes."
            )


if __name__ == "__main__":
    main()
