#!/usr/bin/env python3
"""
Analyze gap questions DynamoDB failures from live test output.
Extracts detailed error information and recommends fixes.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any


def extract_gap_questions_error(log_content: str) -> dict[str, Any]:
    """Extract gap questions test error details from log."""

    # Find the test_generate_gap_questions response
    pattern = r"=== RESPONSE test_generate_gap_questions ===\s*\n(.*?)(?==== |$)"
    matches = re.findall(pattern, log_content, re.DOTALL)

    if not matches:
        return {"error": "Could not find test_generate_gap_questions response in log"}

    last_match = matches[-1]

    try:
        # Parse the JSON response
        response_json = json.loads(last_match)
        return {
            "status_code": response_json.get("status_code"),
            "error": response_json.get("response", {}).get("error"),
            "code": response_json.get("response", {}).get("code"),
            "raw_response": response_json,
        }
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse response JSON: {e}", "raw": last_match[:500]}


def diagnose_error(error_details: dict[str, Any]) -> dict[str, Any]:
    """Diagnose the error based on details."""

    if "error" in error_details and "Could not find" in error_details["error"]:
        return {
            "status": "INCONCLUSIVE",
            "reason": "Could not find test response in log",
            "action": "Ensure test was run and log includes test_generate_gap_questions output",
        }

    status_code = error_details.get("status_code")
    error_msg = error_details.get("error", "")
    error_code = error_details.get("code", "")

    if status_code in [200, 201]:
        return {
            "status": "SUCCESS",
            "reason": "Test passed",
            "action": "No action needed - gap questions are working",
        }

    # Extract detailed error info from error message
    details_match = re.search(r"Details: (.*?)$", error_msg)
    if details_match:
        details_str = details_match.group(1)
        return {
            "status": "ERROR_WITH_DETAILS",
            "error_code": error_code,
            "details": details_str,
            "diagnosis": diagnose_by_error_code(details_str, error_code),
        }

    # Fallback: generic error
    if "DYNAMODB_ERROR" in error_code or status_code == 500:
        return {
            "status": "GENERIC_DYNAMODB_ERROR",
            "error_msg": error_msg,
            "action": "Re-run test - enhanced diagnostics should provide detailed error",
        }

    return {
        "status": "UNKNOWN_ERROR",
        "status_code": status_code,
        "error_code": error_code,
        "error_msg": error_msg,
    }


def diagnose_by_error_code(details: str, code: str) -> dict[str, Any]:
    """Provide diagnosis based on error code."""

    if "ValidationException" in details or "schema" in details.lower():
        return {
            "likely_cause": "Schema validation error",
            "checks": [
                "✓ Are pk and sk fields both strings?",
                "✓ Is artifact_type = 'gap_analysis'?",
                "✓ Are question objects valid (no circular refs)?",
                "✓ Is ttl field an integer (Unix timestamp)?",
            ],
            "fix": "Review item structure in save_gap_questions vs table schema",
            "reference": "infra/careervp/api_db_construct.py lines 85-89",
        }

    if "ResourceNotFoundException" in details or "not found" in details.lower():
        return {
            "likely_cause": "Table doesn't exist or wrong name",
            "checks": [
                "✓ Check AWS console: Table exists?",
                "✓ Check env var: GAP_QUESTIONS_TABLE_NAME",
                "✓ Check CDK output: actual table name",
                "✓ Check region: correct AWS region?",
            ],
            "fix": "Ensure table exists and env var is set correctly",
            "reference": "infra/careervp/api_construct.py line 1812",
        }

    if "AccessDeniedException" in details:
        return {
            "likely_cause": "Lambda role lacks permissions",
            "checks": [
                "✓ Check Lambda execution role has dynamodb:PutItem",
                "✓ Check role ARN is correct",
                "✓ Check table ARN in policy",
            ],
            "fix": "Update Lambda IAM role to allow dynamodb:PutItem on users table",
            "reference": "infra/careervp/api_construct.py lambda_role",
        }

    if "ItemCollectionSize" in details or "large" in details.lower():
        return {
            "likely_cause": "Item exceeds 400KB DynamoDB limit",
            "checks": [
                "✓ Check question content size",
                "✓ Check number of questions",
                "✓ Check if questions array is too large",
            ],
            "fix": "Reduce question content or max_questions parameter",
            "reference": "src/backend/careervp/handlers/gap_handler.py line 149",
        }

    if "TypeError" in details or "Serialization" in details:
        return {
            "likely_cause": "Item data not JSON serializable",
            "checks": [
                "✓ Check questions have only primitive types (str, int, float, bool, list, dict)",
                "✓ No datetime objects, custom classes, or circular references",
                "✓ All array items are dicts with string keys",
            ],
            "fix": "Ensure generate_gap_questions returns only JSON-serializable types",
            "reference": "src/backend/careervp/logic/gap_analysis.py",
        }

    return {
        "likely_cause": f"Unknown error code: {code}",
        "details_snippet": details[:100],
        "action": "Check CloudWatch logs for full error message",
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_gap_questions_failure.py <log_file>")
        print(
            "\nExample: python3 analyze_gap_questions_failure.py live-test-results29.log"
        )
        sys.exit(1)

    log_file = Path(sys.argv[1])
    if not log_file.exists():
        print(f"Error: Log file not found: {log_file}")
        sys.exit(1)

    print(f"Analyzing: {log_file}")
    print("=" * 80)

    log_content = log_file.read_text()
    error_details = extract_gap_questions_error(log_content)
    diagnosis = diagnose_error(error_details)

    print(json.dumps(diagnosis, indent=2))
    print("\n" + "=" * 80)

    # Save diagnosis
    output_file = log_file.parent / f"{log_file.stem}_analysis.json"
    output_file.write_text(json.dumps(diagnosis, indent=2))
    print(f"\n✓ Analysis saved to: {output_file}")


if __name__ == "__main__":
    main()
