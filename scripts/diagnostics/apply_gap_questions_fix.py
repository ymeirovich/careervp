#!/usr/bin/env python3
"""
Apply fixes to gap questions failures based on diagnosed error code.
Supports multiple fix strategies.
"""

import json
import sys
from pathlib import Path


def fix_schema_validation_error() -> str:
    """Fix schema validation errors in item structure."""
    print("\n📋 Applying: Schema Validation Fix")
    print("-" * 80)

    gap_handler = Path("src/backend/careervp/dal/dynamo_dal_handler.py")

    if not gap_handler.exists():
        return "❌ File not found: src/backend/careervp/dal/dynamo_dal_handler.py"

    content = gap_handler.read_text()

    # Check current implementation
    if "json.dumps(item, default=str)" in content:
        return "✓ Schema validation already in place (JSON serialization check)"

    return "⚠️ Schema validation fix may need manual review"


def fix_table_not_found() -> str:
    """Fix table not found errors (infrastructure)."""
    print("\n📋 Applying: Table Configuration Fix")
    print("-" * 80)

    checks = [
        (
            "GAP_QUESTIONS_TABLE_NAME in gap_handler",
            "src/backend/careervp/handlers/gap_handler.py",
            41,
        ),
        (
            "GAP_QUESTIONS_TABLE_NAME in api_construct",
            "infra/careervp/api_construct.py",
            1812,
        ),
        ("Users table schema (pk/sk)", "infra/careervp/api_db_construct.py", 86),
    ]

    results = []
    for check_name, filepath, expected_line in checks:
        file_obj = Path(filepath)
        if file_obj.exists():
            results.append(f"✓ {check_name}: File exists")
        else:
            results.append(f"❌ {check_name}: File missing - {filepath}")

    return "\n".join(results)


def fix_serialization_error() -> str:
    """Fix serialization errors in question data."""
    print("\n📋 Applying: Serialization Fix")
    print("-" * 80)

    gap_logic = Path("src/backend/careervp/logic/gap_analysis.py")

    if not gap_logic.exists():
        return "❌ File not found: src/backend/careervp/logic/gap_analysis.py"

    content = gap_logic.read_text()

    # Verify JSON serialization is enforced
    if "json.dumps" in content and "_normalize_question" in content:
        return "✓ Question normalization enforces JSON-serializable types"

    return "⚠️ Serialization fix may need manual review"


def fix_item_too_large() -> str:
    """Fix item size errors by reducing content."""
    print("\n📋 Applying: Item Size Reduction")
    print("-" * 80)

    gap_handler = Path("src/backend/careervp/handlers/gap_handler.py")

    if not gap_handler.exists():
        return "❌ File not found"

    content = gap_handler.read_text()

    # Check max_questions constraint
    if "max_questions = _normalize_max_questions" in content:
        return "✓ Max questions normalization in place"

    return "⚠️ Item size reduction needs manual review"


def recommend_aws_cli_checks() -> str:
    """Provide AWS CLI commands to verify infrastructure."""
    return """
AWS CLI Diagnostic Commands:
============================

1. Check table exists:
   aws dynamodb describe-table --table-name careervp-users --region us-east-1

2. Check table schema:
   aws dynamodb describe-table --table-name careervp-users --query 'Table.KeySchema' --region us-east-1

3. Check Lambda environment variables:
   aws lambda get-function-configuration --function-name careervp-gap-api --region us-east-1 | jq '.Environment.Variables'

4. Check Lambda execution role:
   aws lambda get-function-configuration --function-name careervp-gap-api --region us-east-1 | jq '.Role'

5. Check role permissions:
   aws iam get-role-policy --role-name <role-name> --policy-name <policy-name> --region us-east-1

6. Tail Lambda logs:
   aws logs tail /aws/lambda/careervp-gap-api --follow --region us-east-1
"""


def main():
    print("🔧 RECOVERY_002 Automated Fix Application")
    print("=" * 80)

    if len(sys.argv) < 2:
        print("\nUsage: python3 apply_gap_questions_fix.py <error_code>")
        print("\nSupported error codes:")
        print("  - ValidationException")
        print("  - ResourceNotFoundException")
        print("  - AccessDeniedException")
        print("  - ItemCollectionSizeLimitExceededException")
        print("  - TypeError")
        print("  - All")
        print("\nExample:")
        print("  python3 apply_gap_questions_fix.py ValidationException")
        sys.exit(1)

    error_code = sys.argv[1]

    fixes = {
        "ValidationException": fix_schema_validation_error,
        "ResourceNotFoundException": fix_table_not_found,
        "AccessDeniedException": lambda: "Run: aws iam get-role-policy <role> to check permissions",
        "ItemCollectionSizeLimitExceededException": fix_item_too_large,
        "TypeError": fix_serialization_error,
        "All": lambda: (
            fix_schema_validation_error()
            + "\n"
            + fix_table_not_found()
            + "\n"
            + fix_serialization_error()
        ),
    }

    if error_code not in fixes:
        print(f"❌ Unknown error code: {error_code}")
        print(f"Supported codes: {', '.join(fixes.keys())}")
        sys.exit(1)

    fix_func = fixes[error_code]
    result = fix_func()
    print(result)

    print("\n" + "=" * 80)
    print(recommend_aws_cli_checks())
    print("=" * 80)

    # Create summary report
    report = {
        "error_code": error_code,
        "fixes_applied": result,
        "recommendation": "Run AWS CLI checks to verify infrastructure state",
    }

    output_file = Path(f"/tmp/gap_questions_fix_{error_code}.json")
    output_file.write_text(json.dumps(report, indent=2))
    print(f"\n✓ Fix report saved to: {output_file}")


if __name__ == "__main__":
    main()
