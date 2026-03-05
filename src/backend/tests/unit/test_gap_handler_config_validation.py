"""Validation-focused tests for gap handler table configuration."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _base_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    monkeypatch.setenv('ARTIFACTS_TABLE_NAME', 'artifacts-table')
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'artifacts-table')


def _event(path: str, method: str, body: dict[str, object] | None = None) -> dict[str, object]:
    return {
        'path': path,
        'httpMethod': method,
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': 'user-1',
                }
            }
        },
        'headers': {'Content-Type': 'application/json'},
        'pathParameters': {'jobId': 'job-1'},
        'body': json.dumps(body) if body is not None else None,
    }


def _context() -> SimpleNamespace:
    return SimpleNamespace(
        function_name='gap-handler',
        memory_limit_in_mb=256,
        invoked_function_arn='arn:aws:lambda:us-east-1:123456789012:function:gap-handler',
        aws_request_id='req-gap-1',
    )


def test_submit_gap_responses_returns_500_when_gap_table_env_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from careervp.handlers import gap_handler

    monkeypatch.delenv('GAP_RESPONSES_TABLE_NAME', raising=False)
    event = _event(
        '/jobs/job-1/gap-responses',
        'POST',
        {
            'job_id': 'job-1',
            'responses': [{'question_id': 'q1', 'response': 'Answer'}],
        },
    )

    # Ensure this fails due to configuration validation, not DAL side-effects.
    with patch.object(gap_handler, '_normalize_submitted_responses', return_value=([{'question_id': 'q1', 'response': 'Answer'}], None)):
        response = gap_handler.lambda_handler(event, _context())

    assert response['statusCode'] == 500
    payload = json.loads(str(response['body']))
    assert 'error' in payload


def test_get_questions_dal_prefers_gap_questions_table_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gap questions should use dedicated GAP_QUESTIONS_TABLE_NAME, not ARTIFACTS_TABLE_NAME."""
    from careervp.handlers import gap_handler

    monkeypatch.setenv('GAP_QUESTIONS_TABLE_NAME', 'gap-questions-table')
    monkeypatch.setenv('USERS_TABLE_NAME', 'users-table')
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'legacy-table')

    dal = gap_handler._get_questions_dal()
    assert dal.table_name == 'gap-questions-table'


def test_get_responses_dal_uses_gap_responses_table_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from careervp.handlers import gap_handler

    monkeypatch.setenv('ARTIFACTS_TABLE_NAME', 'artifacts-table')
    monkeypatch.setenv('GAP_RESPONSES_TABLE_NAME', 'gap-responses-table')

    dal = gap_handler._get_responses_dal()
    assert dal.table_name == 'gap-responses-table'


def test_submit_gap_responses_returns_500_on_schema_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from careervp.handlers import gap_handler
    from careervp.models.result import Result, ResultCode

    monkeypatch.setenv('GAP_RESPONSES_TABLE_NAME', 'gap-responses-table')
    event = _event(
        '/jobs/job-1/gap-responses',
        'POST',
        {
            'job_id': 'job-1',
            'responses': [{'question_id': 'q1', 'response': 'Answer'}],
        },
    )
    fake_result = Result(
        success=False,
        data=None,
        error='table_name=gap-responses-table operation=save_gap_responses_raw',
        code=ResultCode.TABLE_SCHEMA_MISMATCH,
    )
    dal = SimpleNamespace(save_gap_responses_raw=lambda **_: fake_result)

    with patch.object(gap_handler, '_get_responses_dal', return_value=dal):
        response = gap_handler.lambda_handler(event, _context())

    assert response['statusCode'] == 500
    payload = json.loads(str(response['body']))
    assert payload['code'] == ResultCode.TABLE_SCHEMA_MISMATCH
