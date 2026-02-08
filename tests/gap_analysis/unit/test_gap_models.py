"""
Unit tests for gap analysis Pydantic models.
Tests for models/gap_analysis.py (request/response validation).

RED PHASE: These tests will FAIL until models are created.
"""

import pytest
from pydantic import ValidationError

# These imports will fail until the module is created
from careervp.models.gap_analysis import (
    GapAnalysisRequest,
    GapAnalysisResponse,
    GapQuestion,
)
from careervp.models.job import JobPosting


class TestGapAnalysisRequest:
    """Test GapAnalysisRequest model validation."""

    def test_gap_analysis_request_valid(
        self, mock_user_id: str, mock_cv_id: str, mock_job_posting: dict
    ):
        """Test valid gap analysis request."""
        request = GapAnalysisRequest(
            user_id=mock_user_id,
            cv_id=mock_cv_id,
            job_posting=JobPosting(**mock_job_posting),
            language="en",
        )

        assert request.user_id == mock_user_id
        assert request.cv_id == mock_cv_id
        assert request.language == "en"
        assert isinstance(request.job_posting, JobPosting)

    def test_gap_analysis_request_missing_user_id(
        self, mock_cv_id: str, mock_job_posting: dict
    ):
        """Test that missing user_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            GapAnalysisRequest(
                cv_id=mock_cv_id, job_posting=JobPosting(**mock_job_posting)
            )

        assert "user_id" in str(exc_info.value)

    def test_gap_analysis_request_missing_cv_id(
        self, mock_user_id: str, mock_job_posting: dict
    ):
        """Test that missing cv_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            GapAnalysisRequest(
                user_id=mock_user_id, job_posting=JobPosting(**mock_job_posting)
            )

        assert "cv_id" in str(exc_info.value)

    def test_gap_analysis_request_missing_job_posting(
        self, mock_user_id: str, mock_cv_id: str
    ):
        """Test that missing job_posting raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            GapAnalysisRequest(user_id=mock_user_id, cv_id=mock_cv_id)

        assert "job_posting" in str(exc_info.value)

    def test_gap_analysis_request_default_language_en(
        self, mock_user_id: str, mock_cv_id: str, mock_job_posting: dict
    ):
        """Test that language defaults to 'en'."""
        request = GapAnalysisRequest(
            user_id=mock_user_id,
            cv_id=mock_cv_id,
            job_posting=JobPosting(**mock_job_posting),
        )

        assert request.language == "en"

    def test_gap_analysis_request_language_hebrew(
        self, mock_user_id: str, mock_cv_id: str, mock_job_posting: dict
    ):
        """Test that language can be set to 'he'."""
        request = GapAnalysisRequest(
            user_id=mock_user_id,
            cv_id=mock_cv_id,
            job_posting=JobPosting(**mock_job_posting),
            language="he",
        )

        assert request.language == "he"

    def test_gap_analysis_request_invalid_language(
        self, mock_user_id: str, mock_cv_id: str, mock_job_posting: dict
    ):
        """Test that invalid language raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            GapAnalysisRequest(
                user_id=mock_user_id,
                cv_id=mock_cv_id,
                job_posting=JobPosting(**mock_job_posting),
                language="fr",  # Not 'en' or 'he'
            )

        assert "language" in str(exc_info.value).lower()


class TestGapQuestion:
    """Test GapQuestion model validation."""

    def test_gap_question_valid(self):
        """Test valid gap question."""
        question = GapQuestion(
            question_id="q1-uuid",
            question="Do you have AWS experience?",
            impact="HIGH",
            probability="HIGH",
            gap_score=1.0,
        )

        assert question.question_id == "q1-uuid"
        assert question.question == "Do you have AWS experience?"
        assert question.impact == "HIGH"
        assert question.probability == "HIGH"
        assert question.gap_score == 1.0

    def test_gap_question_invalid_impact(self):
        """Test that invalid impact raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            GapQuestion(
                question_id="q1",
                question="Test",
                impact="INVALID",  # Not HIGH/MEDIUM/LOW
                probability="HIGH",
                gap_score=1.0,
            )

        assert "impact" in str(exc_info.value).lower()

    def test_gap_question_invalid_probability(self):
        """Test that invalid probability raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            GapQuestion(
                question_id="q1",
                question="Test",
                impact="HIGH",
                probability="INVALID",  # Not HIGH/MEDIUM/LOW
                gap_score=1.0,
            )

        assert "probability" in str(exc_info.value).lower()

    def test_gap_question_gap_score_out_of_range_high(self):
        """Test that gap_score > 1.0 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            GapQuestion(
                question_id="q1",
                question="Test",
                impact="HIGH",
                probability="HIGH",
                gap_score=1.5,  # Too high
            )

        assert "gap_score" in str(exc_info.value).lower()

    def test_gap_question_gap_score_out_of_range_low(self):
        """Test that gap_score < 0.0 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            GapQuestion(
                question_id="q1",
                question="Test",
                impact="HIGH",
                probability="HIGH",
                gap_score=-0.1,  # Too low
            )

        assert "gap_score" in str(exc_info.value).lower()

    def test_gap_question_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            GapQuestion(question="Test")  # Missing all other fields


class TestGapAnalysisResponse:
    """Test GapAnalysisResponse model validation."""

    def test_gap_analysis_response_valid(self, mock_gap_questions: list[dict]):
        """Test valid gap analysis response."""
        questions = [GapQuestion(**q) for q in mock_gap_questions]
        response = GapAnalysisResponse(
            questions=questions, metadata={"questions_generated": len(questions)}
        )

        assert len(response.questions) == len(mock_gap_questions)
        assert response.metadata["questions_generated"] == len(mock_gap_questions)

    def test_gap_analysis_response_empty_questions(self):
        """Test response with empty questions list."""
        response = GapAnalysisResponse(
            questions=[], metadata={"questions_generated": 0}
        )

        assert len(response.questions) == 0

    def test_gap_analysis_response_max_five_questions(
        self, mock_gap_questions: list[dict]
    ):
        """Test that response accepts up to 5 questions."""
        questions = [GapQuestion(**q) for q in mock_gap_questions[:5]]
        response = GapAnalysisResponse(questions=questions, metadata={})

        assert len(response.questions) == 5

    def test_gap_analysis_response_serialization(self, mock_gap_questions: list[dict]):
        """Test that response serializes to JSON correctly."""
        questions = [GapQuestion(**q) for q in mock_gap_questions]
        response = GapAnalysisResponse(questions=questions, metadata={"language": "en"})

        json_str = response.model_dump_json()
        assert isinstance(json_str, str)
        assert "questions" in json_str
        assert "metadata" in json_str

    def test_gap_analysis_response_missing_questions(self):
        """Test that missing questions raises ValidationError."""
        with pytest.raises(ValidationError):
            GapAnalysisResponse(metadata={})  # Missing questions

    def test_gap_analysis_response_missing_metadata(self):
        """Test that missing metadata raises ValidationError."""
        with pytest.raises(ValidationError):
            GapAnalysisResponse(questions=[])  # Missing metadata
