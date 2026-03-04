"""Unit tests for interview prep server-side context resolution.

Spec: INTERVIEW_PREP_003 — AC-IP-302
Validates that _resolve_interview_prep_context assembles:
  cv_facts, vpr_data, vpr_differentiators, gap_responses,
  company_research, language from the relevant data stores.
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock

os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('POWERTOOLS_SERVICE_NAME', 'test')
os.environ.setdefault('LOG_LEVEL', 'INFO')
os.environ.setdefault('ARTIFACTS_TABLE_NAME', 'test-artifacts')


def _api_request(
    vpr_id: str = 'vpr-001',
    gap_response_ids: list[str] | None = None,
    job_id: str | None = None,
    language: str = 'en',
    question_count: int = 10,
) -> Any:
    from careervp.models.api_models import InterviewPrepRequest

    return InterviewPrepRequest(
        vpr_id=vpr_id,
        gap_response_ids=gap_response_ids or ['gap-001'],
        focus_areas=['technical'],
        question_count=question_count,
        application_id=None,
        job_id=job_id,
        language=language,
    )


def _mock_cv() -> Any:
    cv = MagicMock()
    cv.model_dump.return_value = {
        'professional_summary': 'Senior engineer with cloud expertise.',
        'skills': ['Python', 'AWS'],
        'experience': [{'title': 'Staff Engineer', 'company': 'Acme', 'description': 'Platform work'}],
    }
    return cv


def _mock_vpr(differentiators: list[str] | None = None, language: str = 'en') -> Any:
    vpr = MagicMock()
    vpr.model_dump.return_value = {
        'application_id': 'vpr-001',
        'differentiators': differentiators or ['Unique distributed systems expertise'],
        'executive_summary': 'Strong candidate.',
        'language': language,
    }
    return vpr


def _mock_gap_response(question_id: str = 'gap-001') -> Any:
    r = MagicMock()
    r.question_id = question_id
    r.model_dump.return_value = {'question_id': question_id, 'response': 'Used Kubernetes in production.'}
    return r


def _make_dal(
    cv: Any = None,
    vpr: Any = None,
    gap_responses: list[Any] | None = None,
    vpr_success: bool = True,
    gap_success: bool = True,
) -> Any:
    from careervp.models.result import Result, ResultCode

    dal = MagicMock()
    dal.table_name = 'test-artifacts'

    # CV
    dal.get_cv.return_value = cv

    # VPR
    if vpr_success and vpr is not None:
        dal.get_vpr.return_value = Result(success=True, data=vpr, code=ResultCode.SUCCESS)
    else:
        dal.get_vpr.return_value = Result(success=True, data=None, code=ResultCode.SUCCESS)

    # Gap responses
    if gap_success and gap_responses is not None:
        dal.get_gap_responses.return_value = Result(success=True, data=gap_responses, code=ResultCode.SUCCESS)
    else:
        dal.get_gap_responses.return_value = Result(success=True, data=None, code=ResultCode.SUCCESS)

    # Default table query returns empty
    mock_table = MagicMock()
    mock_table.query.return_value = {'Items': []}
    dal._get_db_handler.return_value = mock_table

    return dal


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_resolves_cv_facts_from_cv_record() -> None:
    """Context resolver extracts cv_facts from CV record."""
    from careervp.handlers.interview_prep_handler import _resolve_interview_prep_context

    dal = _make_dal(cv=_mock_cv())
    ctx = _resolve_interview_prep_context(dal, 'user-1', _api_request())

    assert ctx['cv_facts'] is not None
    assert 'professional_summary' in ctx['cv_facts']
    assert 'skills' in ctx['cv_facts']
    assert 'experience' in ctx['cv_facts']
    assert ctx['cv_facts']['professional_summary'] == 'Senior engineer with cloud expertise.'


def test_resolves_vpr_differentiators_from_vpr_record() -> None:
    """Context resolver extracts vpr_differentiators from VPR."""
    from careervp.handlers.interview_prep_handler import _resolve_interview_prep_context

    dal = _make_dal(vpr=_mock_vpr(differentiators=['Unique expertise', 'Strong leadership']))
    ctx = _resolve_interview_prep_context(dal, 'user-1', _api_request())

    assert ctx['vpr_differentiators'] is not None
    assert 'Unique expertise' in ctx['vpr_differentiators']


def test_resolves_language_from_vpr_record() -> None:
    """Context resolver inherits language from VPR record."""
    from careervp.handlers.interview_prep_handler import _resolve_interview_prep_context

    dal = _make_dal(vpr=_mock_vpr(language='he'))
    ctx = _resolve_interview_prep_context(dal, 'user-1', _api_request(language='en'))

    assert ctx['language'] == 'he'


def test_resolves_gap_responses_filtered_by_ids() -> None:
    """Context resolver filters gap responses by requested gap_response_ids."""
    from careervp.handlers.interview_prep_handler import _resolve_interview_prep_context

    r1 = _mock_gap_response('gap-001')
    r2 = _mock_gap_response('gap-002')
    dal = _make_dal(gap_responses=[r1, r2])

    ctx = _resolve_interview_prep_context(dal, 'user-1', _api_request(gap_response_ids=['gap-001']))

    assert ctx['gap_responses'] is not None
    ids = [r.get('question_id') for r in ctx['gap_responses']]
    assert 'gap-001' in ids


def test_cv_missing_produces_none_cv_facts() -> None:
    """When CV not found, cv_facts is None and resolution proceeds without failure."""
    from careervp.handlers.interview_prep_handler import _resolve_interview_prep_context

    dal = _make_dal(cv=None)
    ctx = _resolve_interview_prep_context(dal, 'user-1', _api_request())

    assert ctx['cv_facts'] is None


def test_vpr_missing_produces_fallback_vpr_data() -> None:
    """When VPR not found, vpr_data falls back to {vpr_id: ...} stub."""
    from careervp.handlers.interview_prep_handler import _resolve_interview_prep_context

    dal = _make_dal(vpr=None, vpr_success=False)
    ctx = _resolve_interview_prep_context(dal, 'user-1', _api_request(vpr_id='vpr-fallback'))

    assert ctx['vpr_data'] == {'vpr_id': 'vpr-fallback'}
    assert ctx['vpr_differentiators'] is None


def test_gap_responses_missing_produces_none() -> None:
    """When no gap responses found, gap_responses is None and resolution proceeds."""
    from careervp.handlers.interview_prep_handler import _resolve_interview_prep_context

    dal = _make_dal(gap_responses=None, gap_success=False)
    ctx = _resolve_interview_prep_context(dal, 'user-1', _api_request())

    assert ctx['gap_responses'] is None


def test_cv_exception_does_not_raise() -> None:
    """CV resolution exception is caught; context proceeds without cv_facts."""
    from careervp.handlers.interview_prep_handler import _resolve_interview_prep_context

    dal = _make_dal()
    dal.get_cv.side_effect = RuntimeError('DynamoDB timeout')

    ctx = _resolve_interview_prep_context(dal, 'user-1', _api_request())

    assert ctx['cv_facts'] is None


def test_vpr_exception_does_not_raise() -> None:
    """VPR resolution exception is caught; context proceeds with fallback vpr_data."""
    from careervp.handlers.interview_prep_handler import _resolve_interview_prep_context

    dal = _make_dal()
    dal.get_vpr.side_effect = RuntimeError('DynamoDB timeout')

    ctx = _resolve_interview_prep_context(dal, 'user-1', _api_request(vpr_id='vpr-exc'))

    assert ctx['vpr_data'] == {'vpr_id': 'vpr-exc'}


def test_job_id_passed_through_context() -> None:
    """Optional job_id from API request is propagated into context."""
    from careervp.handlers.interview_prep_handler import _resolve_interview_prep_context

    dal = _make_dal()
    ctx = _resolve_interview_prep_context(dal, 'user-1', _api_request(job_id='job-xyz'))

    assert ctx['job_id'] == 'job-xyz'


def test_default_language_is_en() -> None:
    """Default language is 'en' when request and VPR both omit it."""
    from careervp.handlers.interview_prep_handler import _resolve_interview_prep_context

    dal = _make_dal(vpr=None, vpr_success=False)
    ctx = _resolve_interview_prep_context(dal, 'user-1', _api_request(language='en'))

    assert ctx['language'] == 'en'
