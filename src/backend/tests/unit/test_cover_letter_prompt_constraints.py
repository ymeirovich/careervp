"""Unit tests for cover letter paragraph/page constraints."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

from careervp.logic.cover_letter import generate_cover_letter
from careervp.logic.prompts.cover_letter_prompt import build_system_prompt, build_user_prompt
from careervp.models.cover_letter import CoverLetterRequest
from careervp.models.cv import ContactInfo, UserCV
from careervp.models.result import ResultCode


def _request() -> CoverLetterRequest:
    return CoverLetterRequest(
        user_id='user-1',
        cv_id='cv-1',
        job_id='job-1',
        vpr_id='vpr-1',
        company_name='Example Co',
        job_title='Senior Backend Engineer',
        job_description='Build and operate distributed systems for customer-facing APIs.',
        gap_response_ids=['q-1'],
    )


def _user_cv() -> UserCV:
    return UserCV(
        user_id='user-1',
        cv_id='cv-1',
        full_name='Test User',
        language='en',
        contact_info=ContactInfo(email='test@example.com', name='Test User'),
        email='test@example.com',
        professional_summary='Engineer experienced in distributed systems and backend architecture.',
        experience=[],
        education=[],
        certifications=[],
        skills=[],
        top_achievements=[],
        languages=['en'],
        is_parsed=True,
    )


def _vpr() -> MagicMock:
    value = MagicMock()
    value.model_dump.return_value = {'summary': 'Strong backend execution and mentoring outcomes.'}
    return value


def _strong_anti_ai_score() -> MagicMock:
    score = MagicMock()
    score.score = 10.0
    score.issues = []
    return score


def test_system_prompt_includes_page_and_paragraph_constraints() -> None:
    prompt = build_system_prompt(tone='professional', word_count_target=400)
    assert 'hard max 350 words' in prompt
    assert 'Use exactly 2 or 3 paragraphs' in prompt


def test_user_prompt_serializes_gap_response_dicts() -> None:
    prompt = build_user_prompt(
        cv=_user_cv(),
        vpr=_vpr(),
        company_name='Example Co',
        job_title='Senior Backend Engineer',
        job_description='Build and operate distributed systems for customer-facing APIs.',
        gap_responses=[{'question_id': 'q-1', 'answer': 'I reduced incident volume by 40%'}],
    )
    assert '# Gap Responses' in prompt
    assert '"question_id": "q-1"' in prompt


def test_single_paragraph_output_is_normalized_to_two_paragraphs() -> None:
    llm_payload = {
        'text': (
            'I have led backend modernization initiatives that improved reliability and release confidence '
            'while mentoring engineers and coordinating cross-team delivery. I am excited to bring the same '
            'ownership and technical depth to this role and deliver measurable outcomes for customers.'
        )
    }
    with (
        patch('careervp.logic.cover_letter.LLMClient') as mock_llm_cls,
        patch('careervp.logic.cover_letter.check_anti_ai_patterns', return_value=_strong_anti_ai_score()),
    ):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = llm_payload
        mock_llm_cls.return_value = mock_llm

        result = asyncio.run(generate_cover_letter(request=_request(), user_cv=_user_cv(), vpr=_vpr()))

    assert result.success
    assert result.data is not None
    assert result.data.cover_letter is not None
    assert len(result.data.cover_letter.paragraphs) == 2
    assert len([part for part in result.data.cover_letter.full_text.split('\n\n') if part.strip()]) == 2


def test_more_than_three_paragraphs_is_normalized_to_three() -> None:
    llm_payload = {
        'text': 'Intro paragraph.\n\nAchievement paragraph.\n\nImpact paragraph.\n\nClose paragraph.',
    }
    with (
        patch('careervp.logic.cover_letter.LLMClient') as mock_llm_cls,
        patch('careervp.logic.cover_letter.check_anti_ai_patterns', return_value=_strong_anti_ai_score()),
    ):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = llm_payload
        mock_llm_cls.return_value = mock_llm

        result = asyncio.run(generate_cover_letter(request=_request(), user_cv=_user_cv(), vpr=_vpr()))

    assert result.success
    assert result.data is not None
    assert result.data.cover_letter is not None
    assert len(result.data.cover_letter.paragraphs) == 3
    assert len([part for part in result.data.cover_letter.full_text.split('\n\n') if part.strip()]) == 3


def test_over_one_page_word_count_is_rejected() -> None:
    long_text = ' '.join(['impactful'] * 351)
    with (
        patch('careervp.logic.cover_letter.LLMClient') as mock_llm_cls,
        patch('careervp.logic.cover_letter.check_anti_ai_patterns', return_value=_strong_anti_ai_score()),
    ):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = {'text': long_text}
        mock_llm_cls.return_value = mock_llm

        result = asyncio.run(generate_cover_letter(request=_request(), user_cv=_user_cv(), vpr=_vpr()))

    assert not result.success
    assert result.code == ResultCode.FVS_VALIDATION_FAILED
    assert 'word limit' in (result.error or '')
