"""
Unit tests for gap analysis logic.
Tests for logic/gap_analysis.py (question generation, scoring algorithm).

RED PHASE: These tests will FAIL until gap_analysis.py is implemented.
"""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# These imports will fail until the modules are created
from careervp.logic.gap_analysis import generate_gap_questions
from careervp.models import Result, ResultCode


class TestGenerateGapQuestions:
    """Test gap question generation logic."""

    @pytest.mark.asyncio
    async def test_generate_gap_questions_success(
        self,
        mock_user_cv: dict[str, Any],
        mock_job_posting: dict[str, Any],
        mock_gap_questions: list[dict[str, Any]],
    ):
        """Test successful gap question generation."""
        # Mock DAL
        mock_dal = MagicMock()

        # Mock LLM client
        with patch("careervp.logic.gap_analysis.LLMClient") as mock_llm_class:
            mock_llm = AsyncMock()
            mock_llm.generate.return_value = Result(
                success=True,
                data=json.dumps(mock_gap_questions),
                code=ResultCode.SUCCESS,
            )
            mock_llm_class.return_value = mock_llm

            # Execute
            result = await generate_gap_questions(
                user_cv=mock_user_cv,
                job_posting=mock_job_posting,
                dal=mock_dal,
                language="en",
            )

        # Assert
        assert result.success is True
        assert result.code == ResultCode.GAP_QUESTIONS_GENERATED
        assert len(result.data) == 5
        assert all("question_id" in q for q in result.data)
        assert all("question" in q for q in result.data)
        assert all("impact" in q for q in result.data)
        assert all("probability" in q for q in result.data)
        assert all("gap_score" in q for q in result.data)

    @pytest.mark.asyncio
    async def test_generate_gap_questions_sorted_by_score(
        self, mock_user_cv: dict[str, Any], mock_job_posting: dict[str, Any]
    ):
        """Test that questions are sorted by gap_score (descending)."""
        mock_dal = MagicMock()

        # Mock LLM with unsorted questions
        unsorted_questions = [
            {
                "question_id": "q1",
                "question": "Q1",
                "impact": "LOW",
                "probability": "LOW",
                "gap_score": 0.3,
            },
            {
                "question_id": "q2",
                "question": "Q2",
                "impact": "HIGH",
                "probability": "HIGH",
                "gap_score": 1.0,
            },
            {
                "question_id": "q3",
                "question": "Q3",
                "impact": "MEDIUM",
                "probability": "MEDIUM",
                "gap_score": 0.6,
            },
        ]

        with patch("careervp.logic.gap_analysis.LLMClient") as mock_llm_class:
            mock_llm = AsyncMock()
            mock_llm.generate.return_value = Result(
                success=True,
                data=json.dumps(unsorted_questions),
                code=ResultCode.SUCCESS,
            )
            mock_llm_class.return_value = mock_llm

            result = await generate_gap_questions(
                user_cv=mock_user_cv, job_posting=mock_job_posting, dal=mock_dal
            )

        # Assert questions are sorted by gap_score descending
        scores = [q["gap_score"] for q in result.data]
        assert scores == sorted(scores, reverse=True)
        assert scores == [1.0, 0.6, 0.3]

    @pytest.mark.asyncio
    async def test_generate_gap_questions_max_five_questions(
        self, mock_user_cv: dict[str, Any], mock_job_posting: dict[str, Any]
    ):
        """Test that maximum 5 questions are returned even if LLM generates more."""
        mock_dal = MagicMock()

        # Mock LLM with 10 questions
        many_questions = [
            {
                "question_id": f"q{i}",
                "question": f"Question {i}",
                "impact": "HIGH",
                "probability": "HIGH",
                "gap_score": 1.0 - (i * 0.1),
            }
            for i in range(10)
        ]

        with patch("careervp.logic.gap_analysis.LLMClient") as mock_llm_class:
            mock_llm = AsyncMock()
            mock_llm.generate.return_value = Result(
                success=True, data=json.dumps(many_questions), code=ResultCode.SUCCESS
            )
            mock_llm_class.return_value = mock_llm

            result = await generate_gap_questions(
                user_cv=mock_user_cv, job_posting=mock_job_posting, dal=mock_dal
            )

        # Assert only top 5 questions returned
        assert len(result.data) == 5
        # Assert they are the highest scoring ones
        assert result.data[0]["question_id"] == "q0"
        assert result.data[4]["question_id"] == "q4"

    @pytest.mark.asyncio
    async def test_generate_gap_questions_llm_timeout(
        self, mock_user_cv: dict[str, Any], mock_job_posting: dict[str, Any]
    ):
        """Test handling of LLM timeout."""
        mock_dal = MagicMock()

        with patch("careervp.logic.gap_analysis.LLMClient") as mock_llm_class:
            mock_llm = AsyncMock()
            mock_llm.generate.side_effect = TimeoutError("LLM timeout")
            mock_llm_class.return_value = mock_llm

            result = await generate_gap_questions(
                user_cv=mock_user_cv, job_posting=mock_job_posting, dal=mock_dal
            )

        # Assert error result
        assert result.success is False
        assert result.code == ResultCode.TIMEOUT
        assert "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_generate_gap_questions_llm_api_error(
        self, mock_user_cv: dict[str, Any], mock_job_posting: dict[str, Any]
    ):
        """Test handling of LLM API errors."""
        mock_dal = MagicMock()

        with patch("careervp.logic.gap_analysis.LLMClient") as mock_llm_class:
            mock_llm = AsyncMock()
            mock_llm.generate.return_value = Result(
                success=False,
                error="Rate limit exceeded",
                code=ResultCode.LLM_API_ERROR,
            )
            mock_llm_class.return_value = mock_llm

            result = await generate_gap_questions(
                user_cv=mock_user_cv, job_posting=mock_job_posting, dal=mock_dal
            )

        # Assert error propagated
        assert result.success is False
        assert result.code == ResultCode.LLM_API_ERROR
        assert "rate limit" in result.error.lower()

    @pytest.mark.asyncio
    async def test_generate_gap_questions_invalid_llm_json(
        self, mock_user_cv: dict[str, Any], mock_job_posting: dict[str, Any]
    ):
        """Test handling of invalid JSON from LLM."""
        mock_dal = MagicMock()

        with patch("careervp.logic.gap_analysis.LLMClient") as mock_llm_class:
            mock_llm = AsyncMock()
            mock_llm.generate.return_value = Result(
                success=True, data="This is not valid JSON {", code=ResultCode.SUCCESS
            )
            mock_llm_class.return_value = mock_llm

            result = await generate_gap_questions(
                user_cv=mock_user_cv, job_posting=mock_job_posting, dal=mock_dal
            )

        # Assert parsing error
        assert result.success is False
        assert result.code == ResultCode.INTERNAL_ERROR
        assert "parse" in result.error.lower() or "json" in result.error.lower()

    @pytest.mark.asyncio
    async def test_generate_gap_questions_hebrew_language(
        self, mock_user_cv: dict[str, Any], mock_job_posting: dict[str, Any]
    ):
        """Test gap question generation in Hebrew."""
        mock_dal = MagicMock()
        hebrew_questions = [
            {
                "question_id": "q1",
                "question": "האם יש לך נסיון עם AWS?",
                "impact": "HIGH",
                "probability": "HIGH",
                "gap_score": 1.0,
            }
        ]

        with patch("careervp.logic.gap_analysis.LLMClient") as mock_llm_class:
            mock_llm = AsyncMock()
            mock_llm.generate.return_value = Result(
                success=True, data=json.dumps(hebrew_questions), code=ResultCode.SUCCESS
            )
            mock_llm_class.return_value = mock_llm

            result = await generate_gap_questions(
                user_cv=mock_user_cv,
                job_posting=mock_job_posting,
                dal=mock_dal,
                language="he",
            )

        # Assert Hebrew question returned
        assert result.success is True
        assert result.data[0]["question"] == "האם יש לך נסיון עם AWS?"


class TestGapScoringAlgorithm:
    """Test gap scoring algorithm (impact × probability)."""

    def test_calculate_gap_score_high_impact_high_probability(self):
        """Test gap score for HIGH impact, HIGH probability."""
        # This would test the internal scoring function
        # Assuming: gap_score = (0.7 * impact_score) + (0.3 * probability_score)
        # HIGH = 1.0, MEDIUM = 0.6, LOW = 0.3

        from careervp.logic.gap_analysis import calculate_gap_score

        score = calculate_gap_score(impact="HIGH", probability="HIGH")
        assert score == 1.0  # (0.7 * 1.0) + (0.3 * 1.0)

    def test_calculate_gap_score_high_impact_medium_probability(self):
        """Test gap score for HIGH impact, MEDIUM probability."""
        from careervp.logic.gap_analysis import calculate_gap_score

        score = calculate_gap_score(impact="HIGH", probability="MEDIUM")
        assert score == 0.88  # (0.7 * 1.0) + (0.3 * 0.6)

    def test_calculate_gap_score_medium_impact_medium_probability(self):
        """Test gap score for MEDIUM impact, MEDIUM probability."""
        from careervp.logic.gap_analysis import calculate_gap_score

        score = calculate_gap_score(impact="MEDIUM", probability="MEDIUM")
        assert score == 0.6  # (0.7 * 0.6) + (0.3 * 0.6)

    def test_calculate_gap_score_low_impact_low_probability(self):
        """Test gap score for LOW impact, LOW probability."""
        from careervp.logic.gap_analysis import calculate_gap_score

        score = calculate_gap_score(impact="LOW", probability="LOW")
        assert score == 0.3  # (0.7 * 0.3) + (0.3 * 0.3)

    def test_calculate_gap_score_invalid_impact(self):
        """Test that invalid impact raises ValueError."""
        from careervp.logic.gap_analysis import calculate_gap_score

        with pytest.raises(ValueError, match="Invalid impact level"):
            calculate_gap_score(impact="INVALID", probability="HIGH")

    def test_calculate_gap_score_invalid_probability(self):
        """Test that invalid probability raises ValueError."""
        from careervp.logic.gap_analysis import calculate_gap_score

        with pytest.raises(ValueError, match="Invalid probability level"):
            calculate_gap_score(impact="HIGH", probability="INVALID")


class TestQuestionPrioritization:
    """Test question prioritization and selection logic."""

    @pytest.mark.asyncio
    async def test_prioritizes_high_impact_questions(
        self, mock_user_cv: dict[str, Any], mock_job_posting: dict[str, Any]
    ):
        """Test that high impact questions are prioritized."""
        mock_dal = MagicMock()

        mixed_questions = [
            {
                "question_id": "q1",
                "question": "Low impact",
                "impact": "LOW",
                "probability": "HIGH",
                "gap_score": 0.51,
            },
            {
                "question_id": "q2",
                "question": "High impact",
                "impact": "HIGH",
                "probability": "MEDIUM",
                "gap_score": 0.88,
            },
            {
                "question_id": "q3",
                "question": "Medium impact",
                "impact": "MEDIUM",
                "probability": "HIGH",
                "gap_score": 0.72,
            },
        ]

        with patch("careervp.logic.gap_analysis.LLMClient") as mock_llm_class:
            mock_llm = AsyncMock()
            mock_llm.generate.return_value = Result(
                success=True, data=json.dumps(mixed_questions), code=ResultCode.SUCCESS
            )
            mock_llm_class.return_value = mock_llm

            result = await generate_gap_questions(
                user_cv=mock_user_cv, job_posting=mock_job_posting, dal=mock_dal
            )

        # Assert HIGH impact question comes first
        assert result.data[0]["impact"] == "HIGH"
        assert result.data[0]["question_id"] == "q2"
