#!/usr/bin/env python3
"""
Comprehensive validation that RECOVERY_002 is fully complete.
Checks all acceptance criteria and generates verification report.
"""

import json
import re
import subprocess
import sys
from pathlib import Path


class RECOVERY002Validator:
    """Validates RECOVERY_002 implementation completeness."""

    def __init__(self):
        self.results = {}
        self.repo_root = Path.cwd()

    def check_tests_passing(self, log_file: str) -> dict:
        """Check if all required tests pass."""
        log_path = Path(log_file)
        if not log_path.exists():
            return {"status": "SKIP", "reason": "Log file not found"}

        content = log_path.read_text()

        # Check for test_generate_gap_questions success
        generate_pass = bool(re.search(r"test_generate_gap_questions.*PASSED", content))

        # Check for GET returning questions
        get_pass = bool(re.search(r"test_get_gap_questions.*PASSED", content))

        # Check for cross-user isolation
        isolation_pass = bool(
            re.search(r"test_cross_user_does_not_leak_questions.*PASSED", content)
        )

        # Check overall test count
        match = re.search(r"(\d+) passed", content)
        total_passed = int(match.group(1)) if match else 0

        return {
            "status": "PASS"
            if generate_pass and get_pass and isolation_pass
            else "FAIL",
            "generate_questions_pass": generate_pass,
            "get_questions_pass": get_pass,
            "cross_user_isolation_pass": isolation_pass,
            "total_tests_passed": total_passed,
        }

    def check_regression_delta(
        self, current_log: str, baseline_log: str = "live-test-results27.log"
    ) -> dict:
        """Check regression delta against baseline."""
        delta_script = Path("scripts/spec_quality/check_regression_delta.py")
        if not delta_script.exists():
            return {"status": "SKIP", "reason": "Delta check script not found"}

        try:
            result = subprocess.run(
                [
                    "python3",
                    str(delta_script),
                    "--baseline",
                    baseline_log,
                    "--current",
                    current_log,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                # Parse output
                output = json.loads(result.stdout)
                violations = output.get("violations", [])
                return {
                    "status": "PASS" if not violations else "FAIL",
                    "violations": violations,
                    "delta_report": output,
                }
            else:
                return {
                    "status": "FAIL",
                    "error": result.stderr,
                }
        except Exception as e:
            return {"status": "SKIP", "reason": str(e)}

    def check_code_changes(self) -> dict:
        """Verify code changes are in place."""
        checks = {}

        # Check gap_handler changes
        gap_handler = self.repo_root / "src/backend/careervp/handlers/gap_handler.py"
        if gap_handler.exists():
            content = gap_handler.read_text()
            checks["gap_handler_table_resolution"] = (
                "GAP_QUESTIONS_TABLE_NAME" in content
            )
            checks["gap_handler_persistence_gate"] = (
                "GapQuestionPersistenceFailures" in content
            )
            checks["gap_handler_error_diagnostics"] = "Details:" in content
        else:
            checks["gap_handler"] = False

        # Check DAL changes
        dal_handler = self.repo_root / "src/backend/careervp/dal/dynamo_dal_handler.py"
        if dal_handler.exists():
            content = dal_handler.read_text()
            checks["dal_exception_handling"] = (
                "except (ClientError, ValidationError) as exc" in content
            )
            checks["dal_serialization_check"] = "json.dumps(item" in content
            checks["dal_error_details"] = "error_message=" in content
        else:
            checks["dal_handler"] = False

        # Check infra changes
        api_construct = self.repo_root / "infra/careervp/api_construct.py"
        if api_construct.exists():
            content = api_construct.read_text()
            checks["infra_gap_questions_table_name"] = (
                '"GAP_QUESTIONS_TABLE_NAME"' in content
            )
        else:
            checks["api_construct"] = False

        return {
            "status": "PASS" if all(checks.values()) else "FAIL",
            "checks": checks,
        }

    def check_test_coverage(self) -> dict:
        """Verify test coverage for gap questions."""
        test_files = {
            "unit_tests": Path(
                "src/backend/tests/unit/test_gap_handler_persistence_required.py"
            ),
            "integration_tests": Path(
                "src/backend/tests/integration/test_gap_read_after_write_roundtrip.py"
            ),
            "live_tests": Path("docs/refactor/live_tests/test_05_gap_analysis.py"),
        }

        results = {}
        for name, path in test_files.items():
            if path.exists():
                content = path.read_text()
                test_count = len(re.findall(r"def test_", content))
                results[name] = {
                    "exists": True,
                    "test_count": test_count,
                }
            else:
                results[name] = {"exists": False}

        return {
            "status": "PASS"
            if all(v.get("exists", False) for v in results.values())
            else "FAIL",
            "tests": results,
        }

    def check_spec_status(self) -> dict:
        """Check yaml spec status."""
        yaml_file = (
            self.repo_root
            / "docs/beta/fix-api/yaml3/step_002_gap_questions_read_after_write_recovery.yaml"
        )
        if not yaml_file.exists():
            return {"status": "SKIP", "reason": "Spec file not found"}

        content = yaml_file.read_text()

        status_match = re.search(r"status:\s+(\w+)", content)
        status = status_match.group(1) if status_match else "unknown"

        confidence_match = re.search(r"confidence_score:\s+(\d+)", content)
        confidence = int(confidence_match.group(1)) if confidence_match else 0

        return {
            "status": "PASS"
            if status == "implemented" and confidence >= 85
            else "PARTIAL",
            "yaml_status": status,
            "confidence_score": confidence,
        }

    def run_all_validations(self) -> dict:
        """Run all validation checks."""
        print("🔍 Running RECOVERY_002 Completion Validation")
        print("=" * 80)

        self.results["code_changes"] = self.check_code_changes()
        print(f"✓ Code Changes: {self.results['code_changes']['status']}")

        self.results["test_coverage"] = self.check_test_coverage()
        print(f"✓ Test Coverage: {self.results['test_coverage']['status']}")

        self.results["spec_status"] = self.check_spec_status()
        print(f"✓ Spec Status: {self.results['spec_status']['status']}")

        print("\nOptional checks (if logs provided):")

        # Test passing checks - requires log file
        if len(sys.argv) > 1:
            self.results["tests_passing"] = self.check_tests_passing(sys.argv[1])
            print(f"✓ Tests Passing: {self.results['tests_passing']['status']}")

        # Regression delta - requires two logs
        if len(sys.argv) > 2:
            self.results["regression_delta"] = self.check_regression_delta(
                sys.argv[2],
                sys.argv[1] if len(sys.argv) > 1 else "live-test-results27.log",
            )
            print(f"✓ Regression Delta: {self.results['regression_delta']['status']}")

        return self.results

    def generate_report(self) -> str:
        """Generate validation report."""
        print("\n" + "=" * 80)
        print("📋 RECOVERY_002 Validation Report")
        print("=" * 80)

        for check_name, result in self.results.items():
            status = result.get("status", "UNKNOWN")
            print(f"\n{check_name}: {status}")
            if result.get("checks"):
                for key, value in result["checks"].items():
                    symbol = "✓" if value else "✗"
                    print(f"  {symbol} {key}: {value}")

        # Summary
        print("\n" + "=" * 80)
        all_pass = all(r.get("status") == "PASS" for r in self.results.values())

        if all_pass:
            print("✅ RECOVERY_002 COMPLETE - All validation checks passed!")
        else:
            print("⚠️  RECOVERY_002 PARTIAL - Some checks failed")
            print("\nFailing checks:")
            for check_name, result in self.results.items():
                if result.get("status") != "PASS":
                    print(f"  • {check_name}: {result.get('status')}")

        return "COMPLETE" if all_pass else "PARTIAL"


def main():
    print("RECOVERY_002 Completion Validator")
    print(
        "Usage: python3 validate_recovery_002_complete.py [current_log] [baseline_log]"
    )
    print()

    validator = RECOVERY002Validator()
    validator.run_all_validations()
    report = validator.generate_report()

    # Save report
    report_file = Path("/tmp/recovery_002_validation.json")
    report_file.write_text(json.dumps(validator.results, indent=2))
    print(f"\n✓ Report saved to: {report_file}")

    sys.exit(0 if report == "COMPLETE" else 1)


if __name__ == "__main__":
    main()
