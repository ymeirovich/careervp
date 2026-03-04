"""Unit tests for gap question quality and required output fields."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, patch

from careervp.logic.gap_analysis import generate_gap_questions
from careervp.models.result import Result, ResultCode


def _user_cv_payload() -> dict[str, Any]:
    return {
        'personal_info': {'full_name': 'Candidate One'},
        'skills': ['Python', 'AWS'],
        'work_experience': [{'company': 'Example Corp', 'role': 'Engineer'}],
    }


def _job_payload() -> dict[str, Any]:
    return {
        'company_name': 'Acme',
        'role_title': 'Senior Engineer',
        'requirements': ['Design reliable APIs', 'Lead cross-functional delivery'],
        'responsibilities': ['Own architecture', 'Mentor team members'],
    }


def test_gap_questions_include_required_quality_fields() -> None:
    llm_questions = {
        'questions': [
            {
                'question_id': 'q1',
                'question': 'What measurable result proves API reliability ownership?',
                'impact': 'HIGH',
                'probability': 'MEDIUM',
                'tags': ['[CV IMPACT]'],
            }
        ]
    }
    with patch('careervp.logic.gap_analysis.LLMClient') as mock_llm_class:
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = Result(
            success=True,
            data=json.dumps(llm_questions),
            code=ResultCode.SUCCESS,
        )
        mock_llm_class.return_value = mock_llm

        result = asyncio.run(
            generate_gap_questions(
                user_cv=_user_cv_payload(),
                job_posting=_job_payload(),
                dal=None,
            )
        )

    assert result.success is True
    assert result.data is not None
    assert len(result.data) == 10
    for question in result.data:
        assert 'id' in question
        assert 'text' in question
        assert 'requirement' in question
        assert 'strategic_intent' in question
        assert 'evidence_gap' in question
        assert question['priority'] in {'CRITICAL', 'IMPORTANT', 'OPTIONAL'}
        assert question['destination'] in {'CV IMPACT', 'INTERVIEW/MVP ONLY'}


def test_gap_questions_fallback_is_contextual_and_scored() -> None:
    with patch('careervp.logic.gap_analysis.LLMClient') as mock_llm_class:
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = Result(
            success=True,
            data='not-valid-json',
            code=ResultCode.SUCCESS,
        )
        mock_llm_class.return_value = mock_llm

        result = asyncio.run(
            generate_gap_questions(
                user_cv=_user_cv_payload(),
                job_posting=_job_payload(),
                dal=None,
            )
        )

    assert result.success is True
    assert result.data is not None
    assert len(result.data) == 10
    for question in result.data:
        assert 'uncovered requirement' not in str(question.get('question', '')).lower()
        assert float(question.get('gap_score', 0.0)) > 0.0
