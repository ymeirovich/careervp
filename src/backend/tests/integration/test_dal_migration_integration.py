from __future__ import annotations

import time
import uuid
from typing import Any

import pytest


def _load_dal_handler() -> Any:
    module = pytest.importorskip('careervp.dal.dynamo_dal_handler')
    handler_class = getattr(module, 'DynamoDalHandler', None)
    if handler_class is None:
        raise AssertionError('DynamoDalHandler class not found in careervp.dal.dynamo_dal_handler')
    try:
        return handler_class()
    except TypeError as exc:
        pytest.skip(f'DynamoDalHandler constructor requires runtime-specific args: {exc}')


def _assert_result_success(result: Any) -> None:
    success = getattr(result, 'success', None)
    assert success is True, f'Expected success=True, got {result!r}'


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, 'dict') and callable(value.dict):
        result = value.dict()
        if isinstance(result, dict):
            return result
    if hasattr(value, 'model_dump') and callable(value.model_dump):
        result = value.model_dump()
        if isinstance(result, dict):
            return result
    return {}


def test_dal_save_and_get_gap_analysis_integration() -> None:
    dal = _load_dal_handler()
    user_id = f'int-user-{uuid.uuid4().hex[:10]}'
    job_id = f'int-job-{uuid.uuid4().hex[:10]}'
    gap_payload = {
        'questions': [{'id': 'q1', 'text': 'Tell me about a measurable impact example.'}],
        'responses': [{'question_id': 'q1', 'response': 'Reduced API latency by 42%.'}],
    }

    save_result = dal.save_gap_analysis(user_id, job_id, gap_payload)
    _assert_result_success(save_result)

    get_result = dal.get_gap_analysis(user_id, job_id)
    _assert_result_success(get_result)
    assert getattr(get_result, 'data', None) is not None


def test_dal_save_tailored_cv_cover_letter_and_interview_prep_integration() -> None:
    dal = _load_dal_handler()
    user_id = f'int-user-{uuid.uuid4().hex[:10]}'

    tailored_cv = {
        'id': f'tcv-{uuid.uuid4().hex[:8]}',
        'user_id': user_id,
        'ats_score': 8.5,
        'content': 'Tailored CV content',
    }
    cover_letter = {
        'id': f'cl-{uuid.uuid4().hex[:8]}',
        'user_id': user_id,
        'content': 'Cover letter content',
    }
    interview_prep = {
        'id': f'ip-{uuid.uuid4().hex[:8]}',
        'user_id': user_id,
        'questions': ['Question 1', 'Question 2'],
    }

    _assert_result_success(dal.save_tailored_cv(user_id, tailored_cv))
    _assert_result_success(dal.save_cover_letter(user_id, cover_letter))
    _assert_result_success(dal.save_interview_prep(user_id, interview_prep))


def test_dal_ttl_and_backward_compatibility_integration() -> None:
    dal = _load_dal_handler()
    user_id = f'int-user-{uuid.uuid4().hex[:10]}'
    job_id = f'int-job-{uuid.uuid4().hex[:10]}'
    gap_payload = {'questions': [{'id': 'q1', 'text': 'Question'}], 'responses': []}

    _assert_result_success(dal.save_gap_analysis(user_id, job_id, gap_payload))
    get_result = dal.get_gap_analysis(user_id, job_id)
    _assert_result_success(get_result)

    gap_data = _as_dict(getattr(get_result, 'data', None))
    if not gap_data:
        pytest.skip('DAL did not return dict-like payload for TTL validation.')

    ttl_raw = gap_data.get('ttl')
    if ttl_raw is None:
        pytest.skip('DAL payload does not expose ttl field for direct validation.')
    if isinstance(ttl_raw, int):
        ttl_value = ttl_raw
    elif isinstance(ttl_raw, str):
        ttl_value = int(ttl_raw)
    else:
        pytest.skip('DAL payload ttl is not int/str and cannot be validated safely.')

    expected_ttl = int(time.time()) + 90 * 24 * 60 * 60
    assert abs(ttl_value - expected_ttl) <= 60

    if hasattr(dal, 'get_cv'):
        backward_result = dal.get_cv(user_id, 'non-existent-cv-id')
        assert hasattr(backward_result, 'success')
