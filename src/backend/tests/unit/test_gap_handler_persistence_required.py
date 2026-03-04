"""Unit tests: POST /gap-questions must fail (5xx) when persistence fails.

Traceability: AC-GAP-001 — POST success requires persistence success.
Spec: docs/beta/fix-api/yaml2/gap_questions_read_after_write.yaml
"""

from __future__ import annotations

import json
import os
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('POWERTOOLS_SERVICE_NAME', 'careervp-gap-test')
os.environ.setdefault('LOG_LEVEL', 'INFO')


@pytest.fixture(autouse=True)
def gap_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv('USERS_TABLE_NAME', 'test-users-table')
    monkeypatch.setenv('GAP_RESPONSES_TABLE_NAME', 'test-gap-responses-table')
    monkeypatch.setenv('APPLICATIONS_TABLE_NAME', 'test-applications-table')
    yield


def _make_event(
    path: str = '/gap-analysis/questions',
    method: str = 'POST',
    body: dict[str, Any] | None = None,
    user_id: str = 'user-abc',
    path_parameters: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        'resource': path,
        'path': path,
        'httpMethod': method,
        'headers': {'Content-Type': 'application/json'},
        'multiValueHeaders': {},
        'queryStringParameters': None,
        'multiValueQueryStringParameters': None,
        'pathParameters': path_parameters,
        'stageVariables': None,
        'requestContext': {
            'resourcePath': path,
            'httpMethod': method,
            'path': path,
            'stage': 'test',
            'requestId': 'req-test',
            'authorizer': {'claims': {'sub': user_id}},
        },
        'body': json.dumps(body) if body is not None else None,
        'isBase64Encoded': False,
    }


def _mock_context() -> Any:
    ctx = MagicMock()
    ctx.aws_request_id = 'req-test'
    ctx.function_name = 'gap-handler'
    return ctx


def _generated_questions(n: int = 3) -> list[dict[str, Any]]:
    return [
        {
            'question_id': f'gap-q{i + 1}',
            'question': f'Describe impact example {i + 1}.',
            'impact': 'HIGH',
            'probability': 'MEDIUM',
            'tags': ['[CV IMPACT]'],
        }
        for i in range(n)
    ]


@pytest.mark.unit
def test_post_fails_on_save_failure() -> None:
    """POST returns 5xx when DAL save_gap_questions fails (AC-GAP-001)."""
    from careervp.handlers import gap_handler
    from careervp.models.result import Result, ResultCode

    event = _make_event(body={'cv_id': 'cv-001', 'job_id': 'job-001', 'max_questions': 3})

    mock_dal = MagicMock()
    mock_dal.save_gap_questions.return_value = Result(success=False, error='DynamoDB write failed', code=ResultCode.DYNAMODB_ERROR)

    with (
        patch.object(gap_handler, 'generate_gap_questions') as mock_gen,
        patch.object(gap_handler, '_get_questions_dal', return_value=mock_dal),
        patch.object(gap_handler, '_get_trial_service', return_value=None),
        patch.object(gap_handler, '_get_application_repository') as mock_app_repo,
    ):
        mock_app_repo.return_value.update_state.return_value = None
        mock_gen.return_value = Result(
            success=True,
            data=_generated_questions(3),
            code=ResultCode.GAP_QUESTIONS_GENERATED,
        )

        async def _async_questions(*args: Any, **kwargs: Any) -> Result:
            return mock_gen.return_value

        mock_gen.side_effect = None
        with patch('asyncio.run', return_value=mock_gen.return_value):
            response = gap_handler.generate_questions(event)

    assert response['statusCode'] >= 500, f'Expected 5xx when persistence fails but got {response["statusCode"]}'
    body = json.loads(response['body'])
    assert 'error' in body, 'Error response must include error field'


@pytest.mark.unit
def test_post_fails_when_dal_raises_exception() -> None:
    """POST returns 5xx when DAL raises unexpected exception during save."""
    from careervp.handlers import gap_handler
    from careervp.models.result import Result, ResultCode

    event = _make_event(body={'cv_id': 'cv-002', 'job_id': 'job-002', 'max_questions': 2})

    mock_dal = MagicMock()
    mock_dal.save_gap_questions.side_effect = RuntimeError('unexpected boto error')

    with (
        patch.object(gap_handler, '_get_questions_dal', return_value=mock_dal),
        patch.object(gap_handler, '_get_trial_service', return_value=None),
        patch.object(gap_handler, '_get_application_repository') as mock_app_repo,
        patch('asyncio.run') as mock_run,
    ):
        mock_app_repo.return_value.update_state.return_value = None
        mock_run.return_value = Result(
            success=True,
            data=_generated_questions(2),
            code=ResultCode.GAP_QUESTIONS_GENERATED,
        )
        response = gap_handler.generate_questions(event)

    assert response['statusCode'] >= 500, f'Expected 5xx on DAL exception but got {response["statusCode"]}'


@pytest.mark.unit
def test_post_fails_when_table_not_configured() -> None:
    """POST returns 500 when gap questions table env var is missing."""
    from careervp.handlers import gap_handler
    from careervp.models.result import Result, ResultCode

    event = _make_event(body={'cv_id': 'cv-003', 'job_id': 'job-003', 'max_questions': 2})

    with (
        patch.object(gap_handler, '_get_questions_dal', side_effect=RuntimeError('table not configured')),
        patch.object(gap_handler, '_get_trial_service', return_value=None),
        patch.object(gap_handler, '_get_application_repository') as mock_app_repo,
        patch('asyncio.run') as mock_run,
    ):
        mock_app_repo.return_value.update_state.return_value = None
        mock_run.return_value = Result(
            success=True,
            data=_generated_questions(2),
            code=ResultCode.GAP_QUESTIONS_GENERATED,
        )
        response = gap_handler.generate_questions(event)

    assert response['statusCode'] == 500, f'Expected 500 when table not configured but got {response["statusCode"]}'


@pytest.mark.unit
def test_post_returns_200_only_when_persistence_succeeds() -> None:
    """POST returns 200 only after successful persistence (persisted=True invariant)."""
    from careervp.handlers import gap_handler
    from careervp.models.result import Result, ResultCode

    event = _make_event(body={'cv_id': 'cv-ok', 'job_id': 'job-ok', 'max_questions': 2})

    mock_dal = MagicMock()
    mock_dal.save_gap_questions.return_value = Result(success=True, data=None, code=ResultCode.SUCCESS)

    questions = _generated_questions(2)
    with (
        patch.object(gap_handler, '_get_questions_dal', return_value=mock_dal),
        patch.object(gap_handler, '_get_trial_service', return_value=None),
        patch.object(gap_handler, '_get_application_repository') as mock_app_repo,
        patch('asyncio.run') as mock_run,
    ):
        mock_app_repo.return_value.update_state.return_value = None
        mock_run.return_value = Result(
            success=True,
            data=questions,
            code=ResultCode.GAP_QUESTIONS_GENERATED,
        )
        response = gap_handler.generate_questions(event)

    assert response['statusCode'] == 200, f'Expected 200 when persistence succeeds but got {response["statusCode"]}'
    payload = json.loads(response['body'])
    assert payload['job_id'] == 'job-ok'
    assert payload['cv_id'] == 'cv-ok'
    assert len(payload['questions']) == 2
    mock_dal.save_gap_questions.assert_called_once()
