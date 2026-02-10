"""
JSA Skill Alignment Tests - Gap Analysis Enhancement

Tests for Gap Analysis contextual tagging as defined in:
- JSA-Skill-Alignment-Plan.md Section 6
- docs/specs/05-jsa-skill-alignment.md Section 5

Requirement Traceability:
- TEST-GA-001: GA-001 ([CV IMPACT] tag)
- TEST-GA-002: GA-001 ([INTERVIEW/MVP ONLY] tag)
- TEST-GA-003: GA-001 (MAX 10 questions)
- TEST-GA-004: GA-001 (recurring_themes)
- TEST-GA-005: GA-001 (SKIP THESE TOPICS)
- TEST-GA-006: GA-001 (Strategic Intent)
- TEST-GA-007: GA-001 (Priority levels)
- TEST-GA-008: GA-001 (lambda_handler exists)
- TEST-GA-009: GA-001 (Powertools decorators)
"""

from __future__ import annotations

import os


class TestGapAnalysisAlignment:
    """Test suite for Gap Analysis contextual tagging alignment."""

    def test_gap_has_contextual_tagging_cv_impact(self):
        """
        TEST-GA-001: Verify [CV IMPACT] tag is present.

        Requirement: GA-001 (Contextual Tagging)
        Source: JSA-Skill-Alignment-Plan.md Section 6.1
        """
        from careervp.logic.prompts.gap_analysis_prompt import (
            GAP_ANALYSIS_ENHANCED_PROMPT,
        )

        assert "[CV IMPACT]" in GAP_ANALYSIS_ENHANCED_PROMPT
        assert "CV IMPACT" in GAP_ANALYSIS_ENHANCED_PROMPT

    def test_gap_has_contextual_tagging_interview_mvp(self):
        """
        TEST-GA-002: Verify [INTERVIEW/MVP ONLY] tag is present.

        Requirement: GA-001 (Contextual Tagging)
        Source: JSA-Skill-Alignment-Plan.md Section 6.1
        """
        from careervp.logic.prompts.gap_analysis_prompt import (
            GAP_ANALYSIS_ENHANCED_PROMPT,
        )

        assert "[INTERVIEW/MVP ONLY]" in GAP_ANALYSIS_ENHANCED_PROMPT

    def test_gap_max_10_questions(self):
        """
        TEST-GA-003: Verify MAX 10 questions constraint is present.

        Requirement: GA-001 (Max 10 questions)
        Source: JSA-Skill-Alignment-Plan.md Section 6.1
        """
        from careervp.logic.prompts.gap_analysis_prompt import (
            GAP_ANALYSIS_ENHANCED_PROMPT,
        )

        assert (
            "MAXIMUM 10" in GAP_ANALYSIS_ENHANCED_PROMPT
            or "max 10" in GAP_ANALYSIS_ENHANCED_PROMPT.lower()
        )

    def test_gap_has_memory_awareness_recurring_themes(self):
        """
        TEST-GA-004: Verify recurring_themes parameter is present.

        Requirement: GA-001 (Memory Awareness)
        Source: JSA-Skill-Alignment-Plan.md Section 6.1
        """
        from careervp.logic.prompts.gap_analysis_prompt import (
            GAP_ANALYSIS_ENHANCED_PROMPT,
        )

        assert "recurring_themes" in GAP_ANALYSIS_ENHANCED_PROMPT

    def test_gap_has_skip_instruction(self):
        """
        TEST-GA-005: Verify SKIP THESE TOPICS instruction is present.

        Requirement: GA-001 (Memory Awareness)
        Source: JSA-Skill-Alignment-Plan.md Section 6.1
        """
        from careervp.logic.prompts.gap_analysis_prompt import (
            GAP_ANALYSIS_ENHANCED_PROMPT,
        )

        assert (
            "SKIP" in GAP_ANALYSIS_ENHANCED_PROMPT
            or "skip" in GAP_ANALYSIS_ENHANCED_PROMPT.lower()
        )

    def test_gap_has_strategic_intent(self):
        """
        TEST-GA-006: Verify Strategic Intent field is present.

        Requirement: GA-001 (Strategic Intent)
        Source: JSA-Skill-Alignment-Plan.md Section 6.1
        """
        from careervp.logic.prompts.gap_analysis_prompt import (
            GAP_ANALYSIS_ENHANCED_PROMPT,
        )

        assert "Strategic Intent" in GAP_ANALYSIS_ENHANCED_PROMPT

    def test_gap_has_priority_levels(self):
        """
        TEST-GA-007: Verify priority levels (CRITICAL, IMPORTANT, OPTIONAL) are present.

        Requirement: GA-001 (Priority Levels)
        Source: JSA-Skill-Alignment-Plan.md Section 6.1
        """
        from careervp.logic.prompts.gap_analysis_prompt import (
            GAP_ANALYSIS_ENHANCED_PROMPT,
        )

        assert "CRITICAL" in GAP_ANALYSIS_ENHANCED_PROMPT
        assert "IMPORTANT" in GAP_ANALYSIS_ENHANCED_PROMPT
        assert "OPTIONAL" in GAP_ANALYSIS_ENHANCED_PROMPT

    def test_gap_handler_complete(self):
        """
        TEST-GA-008: Verify gap handler has complete lambda_handler function.

        Requirement: GA-001 (Handler completion)
        Source: JSA-Skill-Alignment-Plan.md Section 6.1
        """
        handler_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "handlers",
            "gap_handler.py",
        )

        with open(handler_path, "r") as f:
            content = f.read()

        # lambda_handler should exist and have substantial content
        assert "lambda_handler" in content, "lambda_handler function not found"

        # Should have more than just helper functions
        assert len(content) > 1000, "Handler appears incomplete"

    def test_gap_handler_has_powertools_decorators(self):
        """
        TEST-GA-009: Verify gap handler has Powertools decorators.

        Requirement: GA-001 (Powertools decorators)
        Source: JSA-Skill-Alignment-Plan.md Section 6.1
        """
        handler_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "handlers",
            "gap_handler.py",
        )

        with open(handler_path, "r") as f:
            content = f.read()

        # Should have Powertools decorators
        has_logger = "logger.inject_lambda_context" in content or "@logger" in content
        has_tracer = "tracer.capture_lambda_handler" in content or "@tracer" in content

        assert has_logger or has_tracer, "Powertools decorators not found"

    def test_gap_has_cv_impact_question_guidance(self):
        """
        Verify [CV IMPACT] questions have quantification guidance.

        Requirement: GA-001 (CV IMPACT guidance)
        Source: JSA-Skill-Alignment-Plan.md Section 6.1
        """
        from careervp.logic.prompts.gap_analysis_prompt import (
            GAP_ANALYSIS_ENHANCED_PROMPT,
        )

        assert (
            "quantif" in GAP_ANALYSIS_ENHANCED_PROMPT.lower()
            or "metric" in GAP_ANALYSIS_ENHANCED_PROMPT.lower()
        )

    def test_gap_has_interview_mvp_question_guidance(self):
        """
        Verify [INTERVIEW/MVP ONLY] questions have soft skill guidance.

        Requirement: GA-001 (INTERVIEW/MVP guidance)
        Source: JSA-Skill-Alignment-Plan.md Section 6.1
        """
        from careervp.logic.prompts.gap_analysis_prompt import (
            GAP_ANALYSIS_ENHANCED_PROMPT,
        )

        # Should reference qualitative/s soft skills
        assert (
            "philosophy" in GAP_ANALYSIS_ENHANCED_PROMPT.lower()
            or "soft skill" in GAP_ANALYSIS_ENHANCED_PROMPT.lower()
        )

    def test_gap_build_system_prompt_exists(self):
        """
        Verify build_system_prompt function exists.

        Requirement: GA-001 (prompt builder)
        Source: JSA-Skill-Alignment-Plan.md Section 6.2
        """
        from careervp.logic.prompts.gap_analysis_prompt import build_system_prompt

        assert callable(build_system_prompt)

    def test_gap_build_user_prompt_exists(self):
        """
        Verify build_user_prompt function exists.

        Requirement: GA-001 (prompt builder)
        Source: JSA-Skill-Alignment-Plan.md Section 6.2
        """
        from careervp.logic.prompts.gap_analysis_prompt import build_user_prompt

        assert callable(build_user_prompt)

    def test_gap_has_previous_responses_check(self):
        """
        Verify previous gap responses check is present.

        Requirement: GA-001 (Previous Response Check)
        Source: JSA-Skill-Alignment-Plan.md Section 2.4
        """
        from careervp.logic.prompts.gap_analysis_prompt import (
            GAP_ANALYSIS_ENHANCED_PROMPT,
        )

        assert (
            "previous" in GAP_ANALYSIS_ENHANCED_PROMPT.lower()
            and "gap" in GAP_ANALYSIS_ENHANCED_PROMPT.lower()
        )

    def test_gap_has_destination_labeling(self):
        """
        Verify destination labeling is present.

        Requirement: GA-001 (Destination Labeling)
        Source: JSA-Skill-Alignment-Plan.md Section 2.4
        """
        from careervp.logic.prompts.gap_analysis_prompt import (
            GAP_ANALYSIS_ENHANCED_PROMPT,
        )

        assert "Destination" in GAP_ANALYSIS_ENHANCED_PROMPT

    def test_gap_has_evidence_gap_field(self):
        """
        Verify Evidence Gap field is present.

        Requirement: GA-001 (Evidence Gap)
        Source: JSA-Skill-Alignment-Plan.md Section 6.1
        """
        from careervp.logic.prompts.gap_analysis_prompt import (
            GAP_ANALYSIS_ENHANCED_PROMPT,
        )

        assert "Evidence Gap" in GAP_ANALYSIS_ENHANCED_PROMPT

    def test_gap_cors_headers_exist(self):
        """
        Verify CORS headers helper exists.

        Requirement: GA-001 (CORS support)
        Source: JSA-Skill-Alignment-Plan.md Section 6.1
        """
        from careervp.handlers.gap_handler import _cors_headers

        assert callable(_cors_headers)
        headers = _cors_headers()
        assert "Access-Control-Allow-Origin" in headers
