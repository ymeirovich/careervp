"""
JSA Skill Alignment Tests - VPR Prompt Enhancement

Tests for VPR 6-stage methodology as defined in:
- JSA-Skill-Alignment-Plan.md Section 3
- docs/specs/05-jsa-skill-alignment.md Section 2

Requirement Traceability:
- TEST-VPR-001: VPR-001 (6-stage methodology)
- TEST-VPR-002: VPR-001 (meta-review questions)
- TEST-VPR-003: VPR-001 (20% improvement prompt)
"""

from __future__ import annotations


class TestVPRAlignment:
    """Test suite for VPR prompt 6-stage methodology alignment."""

    def test_vpr_has_6_stages(self):
        """
        TEST-VPR-001: Verify VPR prompt includes all 6 stages.

        Requirement: VPR-001 (Section 2.1 of spec)
        Source: JSA-Skill-Alignment-Plan.md Section 3.3
        """
        from careervp.logic.prompts.vpr_prompt import VPR_GENERATION_PROMPT

        required_stages = [
            "STAGE 1: COMPANY & ROLE RESEARCH",
            "STAGE 2: CANDIDATE ANALYSIS",
            "STAGE 3: ALIGNMENT MAPPING",
            "STAGE 4: SELF-CORRECTION",
            "STAGE 5: GENERATE REPORT",
            "STAGE 6: FINAL META EVALUATION",
        ]

        for stage in required_stages:
            assert stage in VPR_GENERATION_PROMPT, f"Missing: {stage}"

    def test_vpr_stage1_company_role_research(self):
        """
        TEST-VPR-001a: Verify Stage 1 contains required elements.

        Requirement: VPR-001 Stage 1
        Source: JSA-Skill-Alignment-Plan.md Section 3.1
        """
        from careervp.logic.prompts.vpr_prompt import VPR_GENERATION_PROMPT

        # Stage 1 should reference company research and job requirements
        assert "3-5 strategic priorities" in VPR_GENERATION_PROMPT
        assert "5-7 role success criteria" in VPR_GENERATION_PROMPT

    def test_vpr_stage2_candidate_analysis(self):
        """
        TEST-VPR-001b: Verify Stage 2 contains career narrative and differentiators.

        Requirement: VPR-001 Stage 2
        Source: JSA-Skill-Alignment-Plan.md Section 3.1
        """
        from careervp.logic.prompts.vpr_prompt import VPR_GENERATION_PROMPT

        # Stage 2 should reference career narrative and differentiators
        assert "3-5 core differentiators" in VPR_GENERATION_PROMPT
        assert (
            "ONE sentence" in VPR_GENERATION_PROMPT
            or "one sentence" in VPR_GENERATION_PROMPT
        )

    def test_vpr_stage3_alignment_mapping(self):
        """
        TEST-VPR-001c: Verify Stage 3 contains alignment table.

        Requirement: VPR-001 Stage 3
        Source: JSA-Skill-Alignment-Plan.md Section 3.1
        """
        from careervp.logic.prompts.vpr_prompt import VPR_GENERATION_PROMPT

        # Stage 3 should reference alignment mapping table
        assert "ALIGNMENT MAPPING" in VPR_GENERATION_PROMPT
        assert "Company/Role Need" in VPR_GENERATION_PROMPT
        assert "Candidate Evidence" in VPR_GENERATION_PROMPT

    def test_vpr_has_self_correction(self):
        """
        TEST-VPR-002: Verify VPR prompt has meta-review/self-correction questions.

        Requirement: VPR-001 Stage 4
        Source: JSA-Skill-Alignment-Plan.md Section 3.1
        """
        from careervp.logic.prompts.vpr_prompt import VPR_GENERATION_PROMPT

        # Verify meta-review questions are present
        assert "unsupported claims" in VPR_GENERATION_PROMPT
        assert (
            "logic consistent" in VPR_GENERATION_PROMPT
            or "logical consistency" in VPR_GENERATION_PROMPT
        )
        assert "persuade a senior hiring manager" in VPR_GENERATION_PROMPT

    def test_vpr_has_meta_evaluation(self):
        """
        TEST-VPR-003: Verify VPR prompt has 20% more persuasive meta evaluation.

        Requirement: VPR-001 Stage 6
        Source: JSA-Skill-Alignment-Plan.md Section 3.1
        """
        from careervp.logic.prompts.vpr_prompt import VPR_GENERATION_PROMPT

        # Verify 20% improvement prompt is present
        assert "20% more persuasive" in VPR_GENERATION_PROMPT

    def test_vpr_internal_output_markers(self):
        """
        TEST-VPR-004: Verify internal output markers between stages.

        Requirement: VPR-001 (internal outputs)
        Source: JSA-Skill-Alignment-Plan.md Section 3.1
        """
        from careervp.logic.prompts.vpr_prompt import VPR_GENERATION_PROMPT

        # Verify internal output instructions are present
        assert "OUTPUT (Internal)" in VPR_GENERATION_PROMPT

    def test_vpr_anti_ai_detection_preserved(self):
        """
        Verify anti-AI detection rules are preserved.

        Requirement: VPR-001 (anti-AI)
        Source: JSA-Skill-Alignment-Plan.md Section 3.1
        """
        from careervp.logic.prompts.vpr_prompt import VPR_GENERATION_PROMPT

        # Verify banned words section exists
        assert (
            "BANNED WORDS" in VPR_GENERATION_PROMPT
            or "Banned words" in VPR_GENERATION_PROMPT
        )

        # Verify specific banned words are mentioned
        assert "leverage" in VPR_GENERATION_PROMPT
        assert "delve" in VPR_GENERATION_PROMPT
        assert "robust" in VPR_GENERATION_PROMPT

    def test_vpr_fact_verification_preserved(self):
        """
        Verify fact verification checklist is preserved.

        Requirement: VPR-001 (fact verification)
        Source: JSA-Skill-Alignment-Plan.md Section 3.1
        """
        from careervp.logic.prompts.vpr_prompt import VPR_GENERATION_PROMPT

        # Verify fact verification section exists
        assert (
            "FACT VERIFICATION" in VPR_GENERATION_PROMPT
            or "Fact Verification" in VPR_GENERATION_PROMPT
        )

    def test_vpr_banned_words_constant_exists(self):
        """
        Verify BANNED_WORDS constant is defined.

        Requirement: VPR-001 (anti-AI constant)
        Source: JSA-Skill-Alignment-Plan.md Section 3.1
        """
        from careervp.logic.prompts.vpr_prompt import BANNED_WORDS

        assert isinstance(BANNED_WORDS, list)
        assert len(BANNED_WORDS) > 0
        assert "leverage" in BANNED_WORDS
        assert "streamline" in BANNED_WORDS

    def test_vpr_check_anti_ai_patterns_function_exists(self):
        """
        Verify check_anti_ai_patterns function exists.

        Requirement: VPR-001 (anti-AI function)
        Source: JSA-Skill-Alignment-Plan.md Section 3.1
        """
        from careervp.logic.prompts.vpr_prompt import check_anti_ai_patterns

        assert callable(check_anti_ai_patterns)

        # Test function behavior
        banned_content = "I leverage robust streamline"
        result = check_anti_ai_patterns(banned_content)
        assert len(result) == 3  # All three banned words detected

        clean_content = "I worked on great projects"
        result = check_anti_ai_patterns(clean_content)
        assert len(result) == 0

    def test_vpr_build_prompt_function_exists(self):
        """
        Verify build_vpr_prompt function exists and works.

        Requirement: VPR-001 (prompt builder)
        Source: JSA-Skill-Alignment-Plan.md Section 3.2
        """
        from careervp.logic.prompts.vpr_prompt import build_vpr_prompt

        assert callable(build_vpr_prompt)
