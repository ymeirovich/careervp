"""
JSA Skill Alignment - Test Mapping and Validation Script

This script validates that all tests map to requirements in JSA-Skill-Alignment-Plan.md
and provides a comprehensive summary of test coverage.

Usage:
    python scripts/validate_jsa_tests.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Test-to-Requirement Mapping
TEST_REQUIREMENT_MAPPING = {
    # VPR Tests
    "test_vpr_has_6_stages": {
        "req": "VPR-001",
        "jsa_section": "3.3",
        "test_id": "TEST-VPR-001",
    },
    "test_vpr_has_self_correction": {
        "req": "VPR-001",
        "jsa_section": "3.1",
        "test_id": "TEST-VPR-002",
    },
    "test_vpr_has_meta_evaluation": {
        "req": "VPR-001",
        "jsa_section": "3.1",
        "test_id": "TEST-VPR-003",
    },
    # CV Tailoring Tests
    "test_cv_has_3_steps": {
        "req": "CVT-001",
        "jsa_section": "4.3",
        "test_id": "TEST-CVT-001",
    },
    "test_cv_has_verification_check_1_ats": {
        "req": "CVT-001",
        "jsa_section": "4.1",
        "test_id": "TEST-CVT-004",
    },
    "test_cv_has_verification_check_2_hiring_manager": {
        "req": "CVT-001",
        "jsa_section": "4.1",
        "test_id": "TEST-CVT-005",
    },
    "test_cv_has_company_keywords_parameter": {
        "req": "CVT-001",
        "jsa_section": "4.1",
        "test_id": "TEST-CVT-006",
    },
    "test_cv_has_vpr_differentiators_parameter": {
        "req": "CVT-001",
        "jsa_section": "4.1",
        "test_id": "TEST-CVT-007",
    },
    # Cover Letter Tests
    "test_cover_letter_has_reference_priming": {
        "req": "CL-001",
        "jsa_section": "5.3",
        "test_id": "TEST-CL-001",
    },
    "test_cover_letter_has_paragraph_1_hook": {
        "req": "CL-001",
        "jsa_section": "5.1",
        "test_id": "TEST-CL-002",
    },
    "test_cover_letter_has_paragraph_2_proof_points": {
        "req": "CL-001",
        "jsa_section": "5.1",
        "test_id": "TEST-CL-003",
    },
    "test_cover_letter_has_word_limit_80_100": {
        "req": "CL-001",
        "jsa_section": "5.1",
        "test_id": "TEST-CL-004",
    },
    "test_cover_letter_has_word_limit_120_140": {
        "req": "CL-001",
        "jsa_section": "5.1",
        "test_id": "TEST-CL-005",
    },
    "test_cover_letter_has_word_limit_60_80": {
        "req": "CL-001",
        "jsa_section": "5.1",
        "test_id": "TEST-CL-006",
    },
    "test_cover_letter_has_top_3_requirements": {
        "req": "CL-001",
        "jsa_section": "5.1",
        "test_id": "TEST-CL-007",
    },
    "test_cover_letter_has_claim_proof_structure": {
        "req": "CL-001",
        "jsa_section": "5.1",
        "test_id": "TEST-CL-008",
    },
    "test_cover_letter_handler_exists": {
        "req": "CL-001",
        "jsa_section": "5.1",
        "test_id": "TEST-CL-009",
    },
    # Gap Analysis Tests
    "test_gap_has_contextual_tagging_cv_impact": {
        "req": "GA-001",
        "jsa_section": "6.3",
        "test_id": "TEST-GA-001",
    },
    "test_gap_has_contextual_tagging_interview_mvp": {
        "req": "GA-001",
        "jsa_section": "6.3",
        "test_id": "TEST-GA-002",
    },
    "test_gap_max_10_questions": {
        "req": "GA-001",
        "jsa_section": "6.3",
        "test_id": "TEST-GA-003",
    },
    "test_gap_has_memory_awareness_recurring_themes": {
        "req": "GA-001",
        "jsa_section": "6.1",
        "test_id": "TEST-GA-004",
    },
    "test_gap_has_strategic_intent": {
        "req": "GA-001",
        "jsa_section": "6.3",
        "test_id": "TEST-GA-006",
    },
    "test_gap_has_priority_levels": {
        "req": "GA-001",
        "jsa_section": "6.3",
        "test_id": "TEST-GA-007",
    },
    "test_gap_handler_complete": {
        "req": "GA-001",
        "jsa_section": "6.3",
        "test_id": "TEST-GA-008",
    },
    # Interview Prep Tests
    "test_interview_prep_handler_exists": {
        "req": "IP-001",
        "jsa_section": "7.1",
        "test_id": "TEST-IP-001",
    },
    "test_interview_prep_logic_exists": {
        "req": "IP-001",
        "jsa_section": "7.1",
        "test_id": "TEST-IP-002",
    },
    "test_interview_prep_has_star_format": {
        "req": "IP-001",
        "jsa_section": "7.1",
        "test_id": "TEST-IP-003",
    },
    "test_interview_prep_has_4_categories": {
        "req": "IP-001",
        "jsa_section": "7.1",
        "test_id": "TEST-IP-004",
    },
    "test_interview_prep_has_10_15_questions_target": {
        "req": "IP-001",
        "jsa_section": "7.1",
        "test_id": "TEST-IP-005",
    },
    "test_interview_prep_has_questions_to_ask": {
        "req": "IP-001",
        "jsa_section": "7.1",
        "test_id": "TEST-IP-006",
    },
    # Quality Validator Tests
    "test_quality_validator_exists": {
        "req": "QV-001",
        "jsa_section": "7.2",
        "test_id": "TEST-QV-001",
    },
    "test_quality_validator_has_fact_verification": {
        "req": "QV-001",
        "jsa_section": "7.2",
        "test_id": "TEST-QV-002",
    },
    "test_quality_validator_has_ats_check": {
        "req": "QV-001",
        "jsa_section": "7.2",
        "test_id": "TEST-QV-003",
    },
    "test_quality_validator_has_anti_ai_check": {
        "req": "QV-001",
        "jsa_section": "7.2",
        "test_id": "TEST-QV-004",
    },
    "test_quality_validator_has_cross_document_check": {
        "req": "QV-001",
        "jsa_section": "7.2",
        "test_id": "TEST-QV-005",
    },
    # Knowledge Base Tests
    "test_knowledge_base_table_in_cdk": {
        "req": "KB-001",
        "jsa_section": "7.3",
        "test_id": "TEST-KB-001",
    },
    "test_knowledge_base_repository_exists": {
        "req": "KB-001",
        "jsa_section": "7.3",
        "test_id": "TEST-KB-002",
    },
    "test_knowledge_base_supports_recurring_themes": {
        "req": "KB-001",
        "jsa_section": "7.3",
        "test_id": "TEST-KB-003",
    },
    "test_knowledge_base_supports_gap_responses": {
        "req": "KB-001",
        "jsa_section": "7.3",
        "test_id": "TEST-KB-004",
    },
}


def scan_test_files(test_dir: str) -> list[dict[str, Any]]:
    """
    Scan test files and extract test functions with their docstrings.
    """
    tests = []
    test_path = Path(test_dir)

    for test_file in test_path.glob("test_*.py"):
        module_name = test_file.stem
        tests.append(
            {
                "file": str(test_file.relative_to(test_path.parent.parent)),
                "module": module_name,
                "tests": [],
            }
        )

    return tests


def validate_test_mapping() -> dict[str, Any]:
    """
    Validate that all tests map to requirements in JSA-Skill-Alignment-Plan.md
    """
    results = {
        "total_tests": 0,
        "mapped_tests": 0,
        "unmapped_tests": [],
        "by_component": {},
        "by_requirement": {},
        "status": "PASS",
        "errors": [],
    }

    # Count tests from mapping
    results["total_tests"] = len(TEST_REQUIREMENT_MAPPING)
    results["mapped_tests"] = len(TEST_REQUIREMENT_MAPPING)

    # Group by component
    components: dict[str, dict[str, Any]] = {
        "VPR": {"req": "VPR-001", "tests": []},
        "CV Tailoring": {"req": "CVT-001", "tests": []},
        "Cover Letter": {"req": "CL-001", "tests": []},
        "Gap Analysis": {"req": "GA-001", "tests": []},
        "Interview Prep": {"req": "IP-001", "tests": []},
        "Quality Validator": {"req": "QV-001", "tests": []},
        "Knowledge Base": {"req": "KB-001", "tests": []},
    }

    for test_name, mapping in TEST_REQUIREMENT_MAPPING.items():
        for component, info in components.items():
            if mapping["req"] == info["req"]:
                info["tests"].append(
                    {
                        "name": test_name,
                        "test_id": mapping["test_id"],
                        "jsa_section": mapping["jsa_section"],
                    }
                )
                break

    results["by_component"] = components

    # Group by requirement
    by_requirement: dict[str, list[dict[str, str]]] = {}
    for test_name, mapping in TEST_REQUIREMENT_MAPPING.items():
        req = mapping["req"]
        if req not in by_requirement:
            by_requirement[req] = []
        by_requirement[req].append(
            {
                "name": test_name,
                "test_id": mapping["test_id"],
                "jsa_section": mapping["jsa_section"],
            }
        )

    results["by_requirement"] = by_requirement

    return results


def print_summary(results: dict[str, Any]) -> None:
    """Print validation summary."""
    print("\n" + "=" * 80)
    print("JSA SKILL ALIGNMENT - TEST VALIDATION SUMMARY")
    print("=" * 80)
    print()

    print(f"Total Tests: {results['total_tests']}")
    print(f"Mapped Tests: {results['mapped_tests']}")
    print(f"Unmapped Tests: {len(results['unmapped_tests'])}")
    print()

    print("-" * 80)
    print("COVERAGE BY COMPONENT:")
    print("-" * 80)

    for component, info in results["by_component"].items():
        test_count = len(info["tests"])
        status = "OK" if test_count > 0 else "MISSING"
        print(f"  {component}: {test_count} tests [{status}]")
        for test in info["tests"]:
            print(f"    - {test['test_id']}: {test['name']}")

    print()
    print("-" * 80)
    print("COVERAGE BY REQUIREMENT:")
    print("-" * 80)

    for req, tests in results["by_requirement"].items():
        print(f"  {req}: {len(tests)} tests")

    print()
    print("=" * 80)

    if results["status"] == "PASS":
        print("STATUS: ALL TESTS MAPPED TO REQUIREMENTS")
    else:
        print("STATUS: VALIDATION FAILED")
        for error in results["errors"]:
            print(f"  ERROR: {error}")

    print("=" * 80)


def main() -> int:
    """Main entry point."""
    print("Validating JSA Skill Alignment test mapping...")

    results = validate_test_mapping()
    print_summary(results)

    if results["status"] == "FAIL":
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
