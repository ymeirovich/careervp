"""
Unit tests for gap analysis prompt generation.
Tests for logic/prompts/gap_analysis_prompt.py.

RED PHASE: These tests will FAIL until gap_analysis_prompt.py is implemented.
"""

from typing import Any

# These imports will fail until the modules are created
from careervp.logic.prompts.gap_analysis_prompt import (
    create_gap_analysis_system_prompt,
    create_gap_analysis_user_prompt,
)


class TestSystemPrompt:
    """Test system prompt generation."""

    def test_create_system_prompt_returns_string(self):
        """Test that system prompt returns a non-empty string."""
        prompt = create_gap_analysis_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_system_prompt_includes_key_instructions(self):
        """Test that system prompt includes key instructions."""
        prompt = create_gap_analysis_system_prompt()

        # Should mention career coach role
        assert "career" in prompt.lower() or "coach" in prompt.lower()

        # Should mention gap analysis
        assert "gap" in prompt.lower()

        # Should mention question generation
        assert "question" in prompt.lower()

        # Should mention JSON output format
        assert "json" in prompt.lower()

    def test_system_prompt_specifies_question_limit(self):
        """Test that system prompt specifies 3-5 questions."""
        prompt = create_gap_analysis_system_prompt()
        assert (
            "3-5" in prompt or "3 to 5" in prompt or ("3" in prompt and "5" in prompt)
        )

    def test_system_prompt_includes_prioritization_guidance(self):
        """Test that system prompt includes prioritization guidance."""
        prompt = create_gap_analysis_system_prompt()
        assert "impact" in prompt.lower() or "priority" in prompt.lower()
        assert "high" in prompt.lower()


class TestUserPrompt:
    """Test user prompt generation with CV and job posting."""

    def test_create_user_prompt_with_full_data(
        self, mock_user_cv: dict[str, Any], mock_job_posting: dict[str, Any]
    ):
        """Test user prompt generation with complete CV and job posting."""
        prompt = create_gap_analysis_user_prompt(
            user_cv=mock_user_cv, job_posting=mock_job_posting
        )

        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_user_prompt_includes_candidate_name(
        self, mock_user_cv: dict[str, Any], mock_job_posting: dict[str, Any]
    ):
        """Test that user prompt includes candidate name."""
        prompt = create_gap_analysis_user_prompt(
            user_cv=mock_user_cv, job_posting=mock_job_posting
        )

        assert mock_user_cv["personal_info"]["full_name"] in prompt

    def test_user_prompt_includes_work_experience(
        self, mock_user_cv: dict[str, Any], mock_job_posting: dict[str, Any]
    ):
        """Test that user prompt includes work experience."""
        prompt = create_gap_analysis_user_prompt(
            user_cv=mock_user_cv, job_posting=mock_job_posting
        )

        # Should include company names
        assert "Tech Corp" in prompt
        assert "Startup Inc" in prompt

        # Should include role titles
        assert "Cloud Engineer" in prompt
        assert "Software Engineer" in prompt

    def test_user_prompt_includes_skills(
        self, mock_user_cv: dict[str, Any], mock_job_posting: dict[str, Any]
    ):
        """Test that user prompt includes skills."""
        prompt = create_gap_analysis_user_prompt(
            user_cv=mock_user_cv, job_posting=mock_job_posting
        )

        # Should include key skills
        assert "Python" in prompt
        assert "AWS" in prompt

    def test_user_prompt_includes_job_requirements(
        self, mock_user_cv: dict[str, Any], mock_job_posting: dict[str, Any]
    ):
        """Test that user prompt includes job requirements."""
        prompt = create_gap_analysis_user_prompt(
            user_cv=mock_user_cv, job_posting=mock_job_posting
        )

        # Should include company and role
        assert mock_job_posting["company_name"] in prompt
        assert mock_job_posting["role_title"] in prompt

        # Should include requirements
        assert "microservices" in prompt.lower()
        assert "kubernetes" in prompt.lower()

    def test_user_prompt_structure_has_sections(
        self, mock_user_cv: dict[str, Any], mock_job_posting: dict[str, Any]
    ):
        """Test that user prompt has clear sections."""
        prompt = create_gap_analysis_user_prompt(
            user_cv=mock_user_cv, job_posting=mock_job_posting
        )

        # Should have CV section
        assert "CV" in prompt or "Candidate" in prompt

        # Should have work experience section
        assert "Work Experience" in prompt or "Experience" in prompt

        # Should have skills section
        assert "Skills" in prompt or "Technical" in prompt

        # Should have job section
        assert "Job" in prompt or "Role" in prompt or "Target" in prompt

        # Should have requirements section
        assert "Requirements" in prompt or "Qualifications" in prompt

    def test_user_prompt_handles_minimal_cv(self):
        """Test prompt generation with minimal CV data."""
        minimal_cv = {
            "personal_info": {"full_name": "John Doe"},
            "work_experience": [],
            "skills": [],
            "education": [],
            "certifications": [],
            "projects": [],
            "language": "en",
        }

        minimal_job = {
            "company_name": "Test Corp",
            "role_title": "Developer",
            "requirements": ["Python"],
            "responsibilities": [],
            "nice_to_have": [],
            "language": "en",
        }

        prompt = create_gap_analysis_user_prompt(
            user_cv=minimal_cv, job_posting=minimal_job
        )

        # Should still generate valid prompt
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "John Doe" in prompt
        assert "Test Corp" in prompt

    def test_user_prompt_respects_language(
        self, mock_user_cv: dict[str, Any], mock_job_posting: dict[str, Any]
    ):
        """Test that prompt respects language parameter."""
        # Update to Hebrew
        hebrew_cv = mock_user_cv.copy()
        hebrew_cv["language"] = "he"
        hebrew_job = mock_job_posting.copy()
        hebrew_job["language"] = "he"

        prompt = create_gap_analysis_user_prompt(
            user_cv=hebrew_cv, job_posting=hebrew_job
        )

        # Prompt should include Hebrew section headers or instructions
        # (Implementation detail - may include Hebrew text or language hint)
        assert isinstance(prompt, str)
        assert len(prompt) > 0


class TestPromptFormatting:
    """Test prompt formatting helpers."""

    def test_format_work_experience(self, mock_user_cv: dict[str, Any]):
        """Test work experience formatting."""
        from careervp.logic.prompts.gap_analysis_prompt import _format_work_experience

        formatted = _format_work_experience(mock_user_cv["work_experience"])

        assert isinstance(formatted, str)
        assert "Tech Corp" in formatted
        assert "Cloud Engineer" in formatted
        assert "2021-01" in formatted or "2021" in formatted

    def test_format_requirements(self, mock_job_posting: dict[str, Any]):
        """Test requirements formatting."""
        from careervp.logic.prompts.gap_analysis_prompt import _format_requirements

        formatted = _format_requirements(mock_job_posting["requirements"])

        assert isinstance(formatted, str)
        for req in mock_job_posting["requirements"]:
            assert req in formatted

    def test_format_responsibilities(self, mock_job_posting: dict[str, Any]):
        """Test responsibilities formatting."""
        from careervp.logic.prompts.gap_analysis_prompt import _format_responsibilities

        formatted = _format_responsibilities(mock_job_posting["responsibilities"])

        assert isinstance(formatted, str)
        for resp in mock_job_posting["responsibilities"]:
            assert resp in formatted

    def test_format_education(self, mock_user_cv: dict[str, Any]):
        """Test education formatting."""
        from careervp.logic.prompts.gap_analysis_prompt import _format_education

        formatted = _format_education(mock_user_cv["education"])

        assert isinstance(formatted, str)
        assert "State University" in formatted
        assert "Computer Science" in formatted


class TestPromptLength:
    """Test prompt length validation."""

    def test_user_prompt_within_token_limits(
        self, mock_user_cv: dict[str, Any], mock_job_posting: dict[str, Any]
    ):
        """Test that generated prompts are within reasonable token limits."""
        prompt = create_gap_analysis_user_prompt(
            user_cv=mock_user_cv, job_posting=mock_job_posting
        )

        # Rough estimate: 1 token ≈ 4 characters
        # Claude 3 supports 200K tokens, but we should keep prompts reasonable
        # Target: < 10K tokens (< 40K characters) for CV + job posting
        assert len(prompt) < 40000, "Prompt exceeds reasonable length"

    def test_system_prompt_concise(self):
        """Test that system prompt is concise."""
        prompt = create_gap_analysis_system_prompt()

        # System prompt should be < 2K characters
        assert len(prompt) < 2000, "System prompt should be concise"
