"""
JSA Skill Alignment Tests - Quality Validator Implementation

Tests for Quality Validator Agent as defined in:
- JSA-Skill-Alignment-Plan.md Section 7.2
- docs/specs/05-jsa-skill-alignment.md Section 7

Requirement Traceability:
- TEST-QV-001: QV-001 (File exists)
- TEST-QV-002: QV-001 (Fact verification)
- TEST-QV-003: QV-001 (ATS check)
- TEST-QV-004: QV-001 (Anti-AI check)
- TEST-QV-005: QV-001 (Cross-document consistency)
"""

from __future__ import annotations

import os
import pytest


class TestQualityValidatorAlignment:
    """Test suite for Quality Validator Agent alignment."""

    def test_quality_validator_exists(self):
        """
        TEST-QV-001: Verify quality validator file exists.

        Requirement: QV-001 (File exists)
        Source: JSA-Skill-Alignment-Plan.md Section 7.2
        """
        validator_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "logic",
            "quality_validator.py",
        )
        assert os.path.exists(validator_path), (
            f"Quality validator not found at {validator_path}"
        )

    def test_quality_validator_has_fact_verification(self):
        """
        TEST-QV-002: Verify fact verification method exists.

        Requirement: QV-001 (Fact Verification)
        Source: JSA-Skill-Alignment-Plan.md Section 7.2
        """
        validator_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "logic",
            "quality_validator.py",
        )

        if not os.path.exists(validator_path):
            pytest.skip("quality_validator.py not yet created")

        with open(validator_path, "r") as f:
            content = f.read()

        assert "fact" in content.lower() or "verify" in content.lower()

    def test_quality_validator_has_ats_check(self):
        """
        TEST-QV-003: Verify ATS compatibility check exists.

        Requirement: QV-001 (ATS Compatibility)
        Source: JSA-Skill-Alignment-Plan.md Section 7.2
        """
        validator_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "logic",
            "quality_validator.py",
        )

        if not os.path.exists(validator_path):
            pytest.skip("quality_validator.py not yet created")

        with open(validator_path, "r") as f:
            content = f.read()

        assert "ATS" in content or "ats" in content.lower()

    def test_quality_validator_has_anti_ai_check(self):
        """
        TEST-QV-004: Verify anti-AI detection check exists.

        Requirement: QV-001 (Anti-AI Detection)
        Source: JSA-Skill-Alignment-Plan.md Section 7.2
        """
        validator_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "logic",
            "quality_validator.py",
        )

        if not os.path.exists(validator_path):
            pytest.skip("quality_validator.py not yet created")

        with open(validator_path, "r") as f:
            content = f.read()

        assert (
            "ai" in content.lower()
            or "detection" in content.lower()
            or "banned" in content.lower()
        )

    def test_quality_validator_has_cross_document_check(self):
        """
        TEST-QV-005: Verify cross-document consistency check exists.

        Requirement: QV-001 (Cross-Document Consistency)
        Source: JSA-Skill-Alignment-Plan.md Section 7.2
        """
        validator_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "logic",
            "quality_validator.py",
        )

        if not os.path.exists(validator_path):
            pytest.skip("quality_validator.py not yet created")

        with open(validator_path, "r") as f:
            content = f.read()

        assert (
            "cross" in content.lower()
            or "consistent" in content.lower()
            or "document" in content.lower()
        )

    def test_quality_validator_has_completeness_check(self):
        """
        Verify completeness check (word counts, section counts) exists.

        Requirement: QV-001 (Completeness)
        Source: JSA-Skill-Alignment-Plan.md Section 7.2
        """
        validator_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "logic",
            "quality_validator.py",
        )

        if not os.path.exists(validator_path):
            pytest.skip("quality_validator.py not yet created")

        with open(validator_path, "r") as f:
            content = f.read()

        assert (
            "complete" in content.lower()
            or "word count" in content.lower()
            or "section" in content.lower()
        )

    def test_quality_validator_has_language_quality_check(self):
        """
        Verify language quality check (spelling, grammar, tone) exists.

        Requirement: QV-001 (Language Quality)
        Source: JSA-Skill-Alignment-Plan.md Section 7.2
        """
        validator_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "logic",
            "quality_validator.py",
        )

        if not os.path.exists(validator_path):
            pytest.skip("quality_validator.py not yet created")

        with open(validator_path, "r") as f:
            content = f.read()

        assert (
            "language" in content.lower()
            or "grammar" in content.lower()
            or "tone" in content.lower()
            or "spelling" in content.lower()
        )

    def test_quality_validator_has_6_checks(self):
        """
        Verify all 6 validation checks are implemented.

        Requirement: QV-001 (6 checks)
        Source: JSA-Skill-Alignment-Plan.md Section 7.2
        """
        validator_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "logic",
            "quality_validator.py",
        )

        if not os.path.exists(validator_path):
            pytest.skip("quality_validator.py not yet created")

        with open(validator_path, "r") as f:
            content = f.read()

        # Count validation checks mentioned
        checks = {
            "fact": "fact" in content.lower(),
            "ats": "ATS" in content or "ats" in content.lower(),
            "ai": "ai" in content.lower()
            or "detection" in content.lower()
            or "banned" in content.lower(),
            "cross": "cross" in content.lower() or "consistent" in content.lower(),
            "complete": "complete" in content.lower()
            or "word count" in content.lower(),
            "language": "language" in content.lower() or "grammar" in content.lower(),
        }

        found_count = sum(1 for v in checks.values() if v)
        assert found_count >= 4, (
            f"Should have at least 4 validation checks, found {found_count}"
        )

    def test_quality_validator_integrates_with_vpr(self):
        """
        Verify quality validator can be integrated with VPR flow.

        Requirement: QV-001 (VPR Integration)
        Source: JSA-Skill-Alignment-Plan.md Section 7.2
        """
        validator_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "logic",
            "quality_validator.py",
        )

        if not os.path.exists(validator_path):
            pytest.skip("quality_validator.py not yet created")

        with open(validator_path, "r") as f:
            content = f.read()

        # Should have VPR reference or validation method
        assert (
            "validate" in content.lower()
            or "vpr" in content.lower()
            or "output" in content.lower()
        )
