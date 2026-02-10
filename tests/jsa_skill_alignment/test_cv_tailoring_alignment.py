"""
JSA Skill Alignment Tests - CV Tailoring Enhancement

Tests for CV Tailoring 3-step verification as defined in:
- JSA-Skill-Alignment-Plan.md Section 4
- docs/specs/05-jsa-skill-alignment.md Section 3

Requirement Traceability:
- TEST-CVT-001: CVT-001 (STEP 1 present)
- TEST-CVT-002: CVT-001 (STEP 2 present)
- TEST-CVT-003: CVT-001 (STEP 3 present)
- TEST-CVT-004: CVT-001 (Verification Check 1)
- TEST-CVT-005: CVT-001 (Verification Check 2)
- TEST-CVT-006: CVT-001 (company_keywords parameter)
- TEST-CVT-007: CVT-001 (vpr_differentiators parameter)
- TEST-CVT-008: CVT-001 (ATS score >= 8)
- TEST-CVT-009: CVT-001 (CAR/STAR format)
"""

from __future__ import annotations


class TestCVTailoringAlignment:
    """Test suite for CV Tailoring 3-step verification alignment."""

    def test_cv_has_3_steps(self):
        """
        TEST-CVT-001, TEST-CVT-002, TEST-CVT-003: Verify CV tailoring has 3 steps.

        Requirement: CVT-001 (3-step verification)
        Source: JSA-Skill-Alignment-Plan.md Section 4.1
        """
        from careervp.logic.cv_tailoring_prompt import CV_TAILORING_PROMPT

        required_steps = [
            "STEP 1: ANALYSIS & KEYWORD MAPPING",
            "STEP 2: SELF-CORRECTION & VERIFICATION",
            "STEP 3: FINAL OUTPUT",
        ]

        for step in required_steps:
            assert step in CV_TAILORING_PROMPT, f"Missing: {step}"

    def test_cv_step1_analysis_keyword_mapping(self):
        """
        TEST-CVT-001a: Verify Step 1 contains keyword mapping requirements.

        Requirement: CVT-001 Stage 1
        Source: JSA-Skill-Alignment-Plan.md Section 4.1
        """
        from careervp.logic.cv_tailoring_prompt import CV_TAILORING_PROMPT

        # Step 1 should reference 12-18 keywords and CAR/STAR format
        assert "12-18" in CV_TAILORING_PROMPT or "12-18 key" in CV_TAILORING_PROMPT
        assert "CAR" in CV_TAILORING_PROMPT or "STAR" in CV_TAILORING_PROMPT

    def test_cv_step2_self_correction_verification(self):
        """
        TEST-CVT-002: Verify Step 2 contains verification checks.

        Requirement: CVT-001 Stage 2
        Source: JSA-Skill-Alignment-Plan.md Section 4.1
        """
        from careervp.logic.cv_tailoring_prompt import CV_TAILORING_PROMPT

        # Step 2 should reference verification checks
        assert (
            "Verification" in CV_TAILORING_PROMPT
            or "verification" in CV_TAILORING_PROMPT
        )

    def test_cv_has_verification_check_1_ats(self):
        """
        TEST-CVT-004: Verify ATS verification check is present.

        Requirement: CVT-001 Verification Check 1
        Source: JSA-Skill-Alignment-Plan.md Section 4.1
        """
        from careervp.logic.cv_tailoring_prompt import CV_TAILORING_PROMPT

        # Verification Check 1 should mention ATS
        assert "ATS" in CV_TAILORING_PROMPT or "keyword match" in CV_TAILORING_PROMPT

    def test_cv_has_verification_check_2_hiring_manager(self):
        """
        TEST-CVT-005: Verify hiring manager verification check is present.

        Requirement: CVT-001 Verification Check 2
        Source: JSA-Skill-Alignment-Plan.md Section 4.1
        """
        from careervp.logic.cv_tailoring_prompt import CV_TAILORING_PROMPT

        # Verification Check 2 should mention hiring manager
        assert (
            "Hiring Manager" in CV_TAILORING_PROMPT
            or "hiring manager" in CV_TAILORING_PROMPT
        )

    def test_cv_has_company_keywords_parameter(self):
        """
        TEST-CVT-006: Verify company_keywords placeholder is present.

        Requirement: CVT-001 (company_keywords parameter)
        Source: JSA-Skill-Alignment-Plan.md Section 4.1
        """
        from careervp.logic.cv_tailoring_prompt import CV_TAILORING_PROMPT

        # Prompt should contain company_keywords placeholder
        assert "{company_keywords}" in CV_TAILORING_PROMPT

    def test_cv_has_vpr_differentiators_parameter(self):
        """
        TEST-CVT-007: Verify vpr_differentiators placeholder is present.

        Requirement: CVT-001 (vpr_differentiators parameter)
        Source: JSA-Skill-Alignment-Plan.md Section 4.1
        """
        from careervp.logic.cv_tailoring_prompt import CV_TAILORING_PROMPT

        # Prompt should contain vpr_differentiators placeholder
        assert "{vpr_differentiators}" in CV_TAILORING_PROMPT

    def test_cv_has_ats_score_requirement(self):
        """
        TEST-CVT-008: Verify ATS score >= 8 requirement is present.

        Requirement: CVT-001 (ATS score >= 8)
        Source: JSA-Skill-Alignment-Plan.md Section 4.1
        """
        from careervp.logic.cv_tailoring_prompt import CV_TAILORING_PROMPT

        # Should have ATS score requirement
        assert "ATS" in CV_TAILORING_PROMPT
        assert "8" in CV_TAILORING_PROMPT or "score" in CV_TAILORING_PROMPT.lower()

    def test_cv_has_car_star_format(self):
        """
        TEST-CVT-009: Verify CAR/STAR format is required.

        Requirement: CVT-001 (CAR/STAR format)
        Source: JSA-Skill-Alignment-Plan.md Section 4.1
        """
        from careervp.logic.cv_tailoring_prompt import CV_TAILORING_PROMPT

        # Should require CAR or STAR format
        assert "STAR" in CV_TAILORING_PROMPT or "CAR" in CV_TAILORING_PROMPT
        assert (
            "action verb" in CV_TAILORING_PROMPT.lower()
            or "action verb" in CV_TAILORING_PROMPT
        )

    def test_cv_has_ats_formatting_rules(self):
        """
        Verify ATS formatting rules are present.

        Requirement: CVT-001 (ATS formatting)
        Source: JSA-Skill-Alignment-Plan.md Section 4.1
        """
        from careervp.logic.cv_tailoring_prompt import CV_TAILORING_PROMPT

        # Should have ATS formatting rules
        assert "bullets" in CV_TAILORING_PROMPT.lower()
        assert (
            "tables" in CV_TAILORING_PROMPT.lower()
            or "No tables" in CV_TAILORING_PROMPT
        )

    def test_cv_build_system_prompt_exists(self):
        """
        Verify build_system_prompt function exists.

        Requirement: CVT-001 (prompt builder)
        Source: JSA-Skill-Alignment-Plan.md Section 4.2
        """
        from careervp.logic.cv_tailoring_prompt import build_system_prompt

        assert callable(build_system_prompt)

    def test_cv_build_user_prompt_exists(self):
        """
        Verify build_user_prompt function exists.

        Requirement: CVT-001 (prompt builder)
        Source: JSA-Skill-Alignment-Plan.md Section 4.2
        """
        from careervp.logic.cv_tailoring_prompt import build_user_prompt

        assert callable(build_user_prompt)

    def test_cv_has_target_keywords_parameter(self):
        """
        Verify target_keywords parameter exists in build_user_prompt.

        Requirement: CVT-001 (target keywords)
        Source: JSA-Skill-Alignment-Plan.md Section 4.1
        """
        from careervp.logic.cv_tailoring_prompt import build_user_prompt
        import inspect

        sig = inspect.signature(build_user_prompt)
        assert "target_keywords" in sig.parameters

    def test_cv_has_fvs_baseline_parameter(self):
        """
        Verify fvs_baseline parameter exists in build_user_prompt.

        Requirement: CVT-001 (FVS baseline)
        Source: JSA-Skill-Alignment-Plan.md Section 4.1
        """
        from careervp.logic.cv_tailoring_prompt import build_user_prompt
        import inspect

        sig = inspect.signature(build_user_prompt)
        assert "fvs_baseline" in sig.parameters
