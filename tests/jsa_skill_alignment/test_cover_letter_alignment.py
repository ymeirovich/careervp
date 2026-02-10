"""
JSA Skill Alignment Tests - Cover Letter Enhancement

Tests for Cover Letter scaffolded prompt as defined in:
- JSA-Skill-Alignment-Plan.md Section 5
- docs/specs/05-jsa-skill-alignment.md Section 4

Requirement Traceability:
- TEST-CL-001: CL-001 (Reference Class Priming)
- TEST-CL-002: CL-001 (Paragraph 1 Hook)
- TEST-CL-003: CL-001 (Paragraph 2 Proof Points)
- TEST-CL-004: CL-001 (80-100 words)
- TEST-CL-005: CL-001 (120-140 words)
- TEST-CL-006: CL-001 (60-80 words)
- TEST-CL-007: CL-001 (3 requirements)
- TEST-CL-008: CL-001 (Claim + Proof)
- TEST-CL-009: CL-001 (Handler exists)
"""

from __future__ import annotations

import os
import pytest


class TestCoverLetterAlignment:
    """Test suite for Cover Letter scaffolded structure alignment."""

    def test_cover_letter_has_reference_priming(self):
        """
        TEST-CL-001: Verify cover letter has reference class priming.

        Requirement: CL-001 (Reference Class Priming)
        Source: JSA-Skill-Alignment-Plan.md Section 5.1
        """
        from careervp.logic.prompts.cover_letter_prompt import COVER_LETTER_PROMPT

        assert "REFERENCE CLASS PRIMING" in COVER_LETTER_PROMPT
        assert (
            "exemplary" in COVER_LETTER_PROMPT.lower()
            or "reference" in COVER_LETTER_PROMPT.lower()
        )

    def test_cover_letter_has_paragraph_1_hook(self):
        """
        TEST-CL-002: Verify cover letter has Paragraph 1 (Hook) structure.

        Requirement: CL-001 (Paragraph 1 Hook)
        Source: JSA-Skill-Alignment-Plan.md Section 5.1
        """
        from careervp.logic.prompts.cover_letter_prompt import COVER_LETTER_PROMPT

        assert (
            "Paragraph 1" in COVER_LETTER_PROMPT
            or "Paragraph 1 (The Hook)" in COVER_LETTER_PROMPT
        )
        assert "Hook" in COVER_LETTER_PROMPT or "hook" in COVER_LETTER_PROMPT.lower()

    def test_cover_letter_has_paragraph_2_proof_points(self):
        """
        TEST-CL-003: Verify cover letter has Paragraph 2 (Proof Points) structure.

        Requirement: CL-001 (Paragraph 2 Proof Points)
        Source: JSA-Skill-Alignment-Plan.md Section 5.1
        """
        from careervp.logic.prompts.cover_letter_prompt import COVER_LETTER_PROMPT

        assert (
            "Paragraph 2" in COVER_LETTER_PROMPT
            or "Paragraph 2 (The Proof Points)" in COVER_LETTER_PROMPT
        )
        assert (
            "Proof Points" in COVER_LETTER_PROMPT
            or "proof points" in COVER_LETTER_PROMPT.lower()
        )

    def test_cover_letter_has_word_limit_80_100(self):
        """
        TEST-CL-004: Verify Paragraph 1 word count constraint (80-100 words).

        Requirement: CL-001 (80-100 words)
        Source: JSA-Skill-Alignment-Plan.md Section 5.1
        """
        from careervp.logic.prompts.cover_letter_prompt import COVER_LETTER_PROMPT

        assert "80-100" in COVER_LETTER_PROMPT or (
            "80" in COVER_LETTER_PROMPT and "100" in COVER_LETTER_PROMPT
        )

    def test_cover_letter_has_word_limit_120_140(self):
        """
        TEST-CL-005: Verify Paragraph 2 word count constraint (120-140 words).

        Requirement: CL-001 (120-140 words)
        Source: JSA-Skill-Alignment-Plan.md Section 5.1
        """
        from careervp.logic.prompts.cover_letter_prompt import COVER_LETTER_PROMPT

        assert "120-140" in COVER_LETTER_PROMPT or (
            "120" in COVER_LETTER_PROMPT and "140" in COVER_LETTER_PROMPT
        )

    def test_cover_letter_has_word_limit_60_80(self):
        """
        TEST-CL-006: Verify Paragraph 3 word count constraint (60-80 words).

        Requirement: CL-001 (60-80 words)
        Source: JSA-Skill-Alignment-Plan.md Section 5.1
        """
        from careervp.logic.prompts.cover_letter_prompt import COVER_LETTER_PROMPT

        assert "60-80" in COVER_LETTER_PROMPT or (
            "60" in COVER_LETTER_PROMPT and "80" in COVER_LETTER_PROMPT
        )

    def test_cover_letter_has_top_3_requirements(self):
        """
        TEST-CL-007: Verify mention of top 3 non-negotiable requirements.

        Requirement: CL-001 (3 requirements)
        Source: JSA-Skill-Alignment-Plan.md Section 5.1
        """
        from careervp.logic.prompts.cover_letter_prompt import COVER_LETTER_PROMPT

        assert (
            "3" in COVER_LETTER_PROMPT and "requirements" in COVER_LETTER_PROMPT.lower()
        )
        assert (
            "non-negotiable" in COVER_LETTER_PROMPT.lower()
            or "negotiable" in COVER_LETTER_PROMPT.lower()
        )

    def test_cover_letter_has_claim_proof_structure(self):
        """
        TEST-CL-008: Verify Claim + Proof structure is required.

        Requirement: CL-001 (Claim + Proof)
        Source: JSA-Skill-Alignment-Plan.md Section 5.1
        """
        from careervp.logic.prompts.cover_letter_prompt import COVER_LETTER_PROMPT

        assert "Claim" in COVER_LETTER_PROMPT or "claim" in COVER_LETTER_PROMPT
        assert "Proof" in COVER_LETTER_PROMPT or "proof" in COVER_LETTER_PROMPT

    def test_cover_letter_has_anti_ai_detection(self):
        """
        Verify anti-AI detection rules are present.

        Requirement: CL-001 (Anti-AI)
        Source: JSA-Skill-Alignment-Plan.md Section 5.1
        """
        from careervp.logic.prompts.cover_letter_prompt import COVER_LETTER_PROMPT

        # Should have anti-AI detection rules
        anti_ai_elements = [
            "leverage" in COVER_LETTER_PROMPT.lower(),
            "delve" in COVER_LETTER_PROMPT.lower(),
            "robust" in COVER_LETTER_PROMPT.lower(),
            "streamline" in COVER_LETTER_PROMPT.lower(),
        ]
        assert any(anti_ai_elements), "Anti-AI banned words should be present"

    def test_cover_letter_has_word_count_enforcement(self):
        """
        Verify word count enforcement is present.

        Requirement: CL-001 (Word Count)
        Source: JSA-Skill-Alignment-Plan.md Section 5.1
        """
        from careervp.logic.prompts.cover_letter_prompt import COVER_LETTER_PROMPT

        assert (
            "400" in COVER_LETTER_PROMPT or "word count" in COVER_LETTER_PROMPT.lower()
        )

    def test_cover_letter_handler_exists(self):
        """
        TEST-CL-009: Verify cover letter handler file exists.

        Requirement: CL-001 (Handler exists)
        Source: JSA-Skill-Alignment-Plan.md Section 5.1
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
            "cover_letter_handler.py",
        )
        assert os.path.exists(handler_path), f"Handler not found at {handler_path}"

    def test_cover_letter_handler_has_lambda_handler(self):
        """
        Verify cover letter handler has lambda_handler function.

        Requirement: CL-001 (lambda_handler)
        Source: JSA-Skill-Alignment-Plan.md Section 5.1
        """
        # Read handler file to verify lambda_handler exists
        handler_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "handlers",
            "cover_letter_handler.py",
        )

        if not os.path.exists(handler_path):
            pytest.skip("cover_letter_handler.py not yet created")

        with open(handler_path, "r") as f:
            content = f.read()

        assert "lambda_handler" in content or "def handler" in content

    def test_cover_letter_build_system_prompt_exists(self):
        """
        Verify build_system_prompt function exists.

        Requirement: CL-001 (prompt builder)
        Source: JSA-Skill-Alignment-Plan.md Section 5.1
        """
        from careervp.logic.prompts.cover_letter_prompt import build_system_prompt

        assert callable(build_system_prompt)

    def test_cover_letter_build_user_prompt_exists(self):
        """
        Verify build_user_prompt function exists.

        Requirement: CL-001 (prompt builder)
        Source: JSA-Skill-Alignment-Plan.md Section 5.1
        """
        from careervp.logic.prompts.cover_letter_prompt import build_user_prompt

        assert callable(build_user_prompt)

    def test_cover_letter_has_vpr_input(self):
        """
        Verify VPR differentiators input is present.

        Requirement: CL-001 (VPR differentiators)
        Source: JSA-Skill-Alignment-Plan.md Section 5.1
        """
        from careervp.logic.prompts.cover_letter_prompt import build_user_prompt
        import inspect

        sig = inspect.signature(build_user_prompt)
        assert "vpr" in sig.parameters or "vpr_response" in sig.parameters

    def test_cover_letter_uvp_reference(self):
        """
        Verify UVP (Unique Value Proposition) reference is present.

        Requirement: CL-001 (UVP)
        Source: JSA-Skill-Alignment-Plan.md Section 5.1
        """
        from careervp.logic.prompts.cover_letter_prompt import COVER_LETTER_PROMPT

        assert (
            "UVP" in COVER_LETTER_PROMPT
            or "value proposition" in COVER_LETTER_PROMPT.lower()
        )

    def test_cover_letter_has_cta_requirement(self):
        """
        Verify CTA (Call to Action) requirement in closing paragraph.

        Requirement: CL-001 (CTA)
        Source: JSA-Skill-Alignment-Plan.md Section 5.1
        """
        from careervp.logic.prompts.cover_letter_prompt import COVER_LETTER_PROMPT

        assert (
            "CTA" in COVER_LETTER_PROMPT
            or "call to action" in COVER_LETTER_PROMPT.lower()
        )
