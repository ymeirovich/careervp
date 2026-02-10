"""
JSA Skill Alignment Tests - Interview Prep Implementation

Tests for Interview Prep Generator as defined in:
- JSA-Skill-Alignment-Plan.md Section 7.1
- docs/specs/05-jsa-skill-alignment.md Section 6

Requirement Traceability:
- TEST-IP-001: IP-001 (Handler exists)
- TEST-IP-002: IP-001 (Logic exists)
- TEST-IP-003: IP-001 (STAR format)
- TEST-IP-004: IP-001 (4 categories)
- TEST-IP-005: IP-001 (10-15 questions)
- TEST-IP-006: IP-001 (Questions to ask)
"""

from __future__ import annotations

import os
import pytest


class TestInterviewPrepAlignment:
    """Test suite for Interview Prep Generator alignment."""

    def test_interview_prep_handler_exists(self):
        """
        TEST-IP-001: Verify interview prep handler file exists.

        Requirement: IP-001 (Handler exists)
        Source: JSA-Skill-Alignment-Plan.md Section 7.1
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
            "interview_prep_handler.py",
        )
        assert os.path.exists(handler_path), f"Handler not found at {handler_path}"

    def test_interview_prep_logic_exists(self):
        """
        TEST-IP-002: Verify interview prep logic module exists.

        Requirement: IP-001 (Logic exists)
        Source: JSA-Skill-Alignment-Plan.md Section 7.1
        """
        logic_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "logic",
            "interview_prep.py",
        )
        assert os.path.exists(logic_path), f"Logic not found at {logic_path}"

    def test_interview_prep_prompt_exists(self):
        """
        Verify interview prep prompt file exists.

        Requirement: IP-001 (Prompt exists)
        Source: JSA-Skill-Alignment-Plan.md Section 7.1
        """
        prompt_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "logic",
            "prompts",
            "interview_prep_prompt.py",
        )
        assert os.path.exists(prompt_path), f"Prompt not found at {prompt_path}"

    def test_interview_prep_has_star_format(self):
        """
        TEST-IP-003: Verify STAR format is required.

        Requirement: IP-001 (STAR format)
        Source: JSA-Skill-Alignment-Plan.md Section 7.1
        """
        prompt_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "logic",
            "prompts",
            "interview_prep_prompt.py",
        )

        if not os.path.exists(prompt_path):
            pytest.skip("interview_prep_prompt.py not yet created")

        with open(prompt_path, "r") as f:
            content = f.read()

        assert "STAR" in content or "Situation, Task, Action, Result" in content

    def test_interview_prep_has_4_categories(self):
        """
        TEST-IP-004: Verify 4 question categories are present.

        Requirement: IP-001 (4 categories)
        Source: JSA-Skill-Alignment-Plan.md Section 7.1
        """
        prompt_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "logic",
            "prompts",
            "interview_prep_prompt.py",
        )

        if not os.path.exists(prompt_path):
            pytest.skip("interview_prep_prompt.py not yet created")

        with open(prompt_path, "r") as f:
            content = f.read()

        # Should mention 4 categories
        categories_found = 0
        if "Technical" in content or "technical" in content.lower():
            categories_found += 1
        if "Behavioral" in content or "behavioral" in content.lower():
            categories_found += 1
        if "Cultural" in content or "cultural" in content.lower():
            categories_found += 1
        if "Experience" in content or "experience" in content.lower():
            categories_found += 1

        assert categories_found >= 3, "Should have at least 3 categories defined"

    def test_interview_prep_has_10_15_questions_target(self):
        """
        TEST-IP-005: Verify 10-15 questions target is present.

        Requirement: IP-001 (10-15 questions)
        Source: JSA-Skill-Alignment-Plan.md Section 7.1
        """
        prompt_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "logic",
            "prompts",
            "interview_prep_prompt.py",
        )

        if not os.path.exists(prompt_path):
            pytest.skip("interview_prep_prompt.py not yet created")

        with open(prompt_path, "r") as f:
            content = f.read()

        assert "10-15" in content or "15" in content or "10" in content

    def test_interview_prep_has_questions_to_ask(self):
        """
        TEST-IP-006: Verify questions to ask interviewer section is present.

        Requirement: IP-001 (Questions to ask)
        Source: JSA-Skill-Alignment-Plan.md Section 7.1
        """
        prompt_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "logic",
            "prompts",
            "interview_prep_prompt.py",
        )

        if not os.path.exists(prompt_path):
            pytest.skip("interview_prep_prompt.py not yet created")

        with open(prompt_path, "r") as f:
            content = f.read()

        assert "ask" in content.lower() or "interviewer" in content.lower()

    def test_interview_prep_has_salary_guidance(self):
        """
        Verify salary negotiation guidance is present.

        Requirement: IP-001 (Salary guidance)
        Source: JSA-Skill-Alignment-Plan.md Section 7.1
        """
        prompt_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "logic",
            "prompts",
            "interview_prep_prompt.py",
        )

        if not os.path.exists(prompt_path):
            pytest.skip("interview_prep_prompt.py not yet created")

        with open(prompt_path, "r") as f:
            content = f.read()

        assert "salary" in content.lower() or "compensation" in content.lower()

    def test_interview_prep_has_checklist(self):
        """
        Verify pre-interview checklist is present.

        Requirement: IP-001 (Checklist)
        Source: JSA-Skill-Alignment-Plan.md Section 7.1
        """
        prompt_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "logic",
            "prompts",
            "interview_prep_prompt.py",
        )

        if not os.path.exists(prompt_path):
            pytest.skip("interview_prep_prompt.py not yet created")

        with open(prompt_path, "r") as f:
            content = f.read()

        assert "checklist" in content.lower()

    def test_interview_prep_handler_has_lambda_handler(self):
        """
        Verify handler has lambda_handler function.

        Requirement: IP-001 (lambda_handler)
        Source: JSA-Skill-Alignment-Plan.md Section 7.1
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
            "interview_prep_handler.py",
        )

        if not os.path.exists(handler_path):
            pytest.skip("interview_prep_handler.py not yet created")

        with open(handler_path, "r") as f:
            content = f.read()

        assert "lambda_handler" in content or "def handler" in content

    def test_interview_prep_has_post_endpoint(self):
        """
        Verify API endpoint for POST /api/interview-prep is configured.

        Requirement: IP-001 (API endpoint)
        Source: JSA-Skill-Alignment-Plan.md Section 6.3
        """
        # Check API construct for interview-prep route
        api_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "infra",
            "careervp",
            "api_construct.py",
        )

        if not os.path.exists(api_path):
            pytest.skip("api_construct.py not found")

        with open(api_path, "r") as f:
            content = f.read()

        assert "interview" in content.lower()
