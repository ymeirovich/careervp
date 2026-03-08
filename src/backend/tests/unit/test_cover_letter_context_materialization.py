"""Unit tests for cover letter context materialization before LLM invocation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from careervp.handlers.cover_letter_handler import _resolve_cover_letter_context
from careervp.models.api_models import CoverLetterRequest
from careervp.models.result import Result, ResultCode


def _request(gap_response_ids: list[str] | None = None) -> CoverLetterRequest:
    return CoverLetterRequest(
        cv_id='cv-1',
        job_id='job-1',
        vpr_id='vpr-1',
        gap_response_ids=gap_response_ids or ['gap-1'],
        company_research_id='company-1',
        options=None,
    )


def _dal() -> MagicMock:
    dal = MagicMock()
    dal.get_vpr.return_value = Result(success=False, data=None, code=ResultCode.SUCCESS)
    dal.get_gap_responses.return_value = Result(
        success=True,
        data=[
            {'question_id': 'gap-1', 'response': 'I improved reliability and delivery speed.'},
            {'question_id': 'gap-2', 'answer': 'I led cross-team architecture reviews.'},
        ],
        code=ResultCode.SUCCESS,
    )
    return dal


@pytest.mark.unit
def test_resolve_cover_letter_context_materializes_real_job_fields() -> None:
    dal = _dal()
    with patch('careervp.handlers.cover_letter_handler.JobsRepository') as mock_repo_cls:
        mock_repo = MagicMock()
        mock_repo.get_job.return_value = {
            'job_id': 'job-1',
            'user_id': 'user-1',
            'title': 'Senior Platform Engineer',
            'company_name': 'Acme Cloud',
            'description': 'Lead backend platform reliability and architecture quality.',
        }
        mock_repo_cls.return_value = mock_repo

        context = _resolve_cover_letter_context(dal=dal, user_id='user-1', api_request=_request(gap_response_ids=['gap-2']))

    assert context['company_name'] == 'Acme Cloud'
    assert context['job_title'] == 'Senior Platform Engineer'
    assert context['job_description'].startswith('Lead backend platform')
    assert context['gap_responses'] == [{'question_id': 'gap-2', 'answer': 'I led cross-team architecture reviews.'}]


@pytest.mark.unit
def test_resolve_cover_letter_context_fails_when_job_missing() -> None:
    dal = _dal()
    with patch('careervp.handlers.cover_letter_handler.JobsRepository') as mock_repo_cls:
        mock_repo = MagicMock()
        mock_repo.get_job.return_value = None
        mock_repo_cls.return_value = mock_repo

        with pytest.raises(ValueError, match='No job posting found'):
            _resolve_cover_letter_context(dal=dal, user_id='user-1', api_request=_request())


@pytest.mark.unit
def test_resolve_cover_letter_context_blocks_placeholder_job_fields() -> None:
    dal = _dal()
    with patch('careervp.handlers.cover_letter_handler.JobsRepository') as mock_repo_cls:
        mock_repo = MagicMock()
        mock_repo.get_job.return_value = {
            'job_id': 'job-1',
            'user_id': 'user-1',
            'title': 'Role for job-1',
            'company_name': 'Company for job-1',
            'description': 'Job description for job-1',
        }
        mock_repo_cls.return_value = mock_repo

        with pytest.raises(ValueError, match='non-placeholder job context field'):
            _resolve_cover_letter_context(dal=dal, user_id='user-1', api_request=_request())
