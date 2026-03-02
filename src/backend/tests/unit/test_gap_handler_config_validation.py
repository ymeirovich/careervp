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
        response = gap_handler.lambda_handler(event, SimpleNamespace(function_name='gap-handler'))

    assert response['statusCode'] == 500
    payload = json.loads(str(response['body']))
    assert 'error' in payload


def test_get_questions_dal_prefers_artifacts_table_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from careervp.handlers import gap_handler

    monkeypatch.setenv('ARTIFACTS_TABLE_NAME', 'artifacts-table')
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'legacy-table')

    with patch.object(gap_handler, '_validate_table_schema'):
        dal = gap_handler._get_questions_dal()
    assert dal.table_name == 'artifacts-table'


def test_get_responses_dal_uses_gap_responses_table_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from careervp.handlers import gap_handler

    monkeypatch.setenv('ARTIFACTS_TABLE_NAME', 'artifacts-table')
    monkeypatch.setenv('GAP_RESPONSES_TABLE_NAME', 'gap-responses-table')

    with patch.object(gap_handler, '_validate_table_schema'):
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
        response = gap_handler.lambda_handler(event, SimpleNamespace(function_name='gap-handler'))

    assert response['statusCode'] == 500
    payload = json.loads(str(response['body']))
    assert payload['code'] == ResultCode.TABLE_SCHEMA_MISMATCH
