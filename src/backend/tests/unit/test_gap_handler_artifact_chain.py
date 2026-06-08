"""Unit tests: gap submit artifact-chain flag gate (FE-UI-031).

Traceability: TEST-CHAIN-001 § unit-flag-gate.
Spec: docs/upgrade/specs/FE-UI-031-step-functions-chain.yaml

- Flag OFF (default): submit behaves exactly as before — no Step Functions call,
  no cr_pending transition.
- Flag ON: submit calls sfn.start_execution once and transitions the application
  state to cr_pending. A chain-start failure must never break the 200 response.
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
    # Ensure a clean default unless a test opts in.
    monkeypatch.delenv('ARTIFACT_CHAIN_ENABLED', raising=False)
    monkeypatch.delenv('STEP_FUNCTIONS_CHAIN_ARN', raising=False)
    yield


def _submit_event(job_id: str = 'job-001', user_id: str = 'user-abc') -> dict[str, Any]:
    body = {
        'job_id': job_id,
        'responses': [
            {'question_id': 'q1', 'response': 'Led a migration that cut latency 40%.'},
        ],
    }
    return {
        'resource': '/gap-analysis/responses',
        'path': '/gap-analysis/responses',
        'httpMethod': 'POST',
        'headers': {'Content-Type': 'application/json'},
        'requestContext': {'authorizer': {'claims': {'sub': user_id}}},
        'body': json.dumps(body),
        'isBase64Encoded': False,
    }


def _ok_dal() -> MagicMock:
    from careervp.models.result import Result, ResultCode

    dal = MagicMock()
    dal.save_gap_responses_raw.return_value = Result(success=True, data=None, code=ResultCode.SUCCESS)
    return dal


@pytest.mark.unit
def test_submit_flag_off_does_not_start_chain() -> None:
    """Flag OFF → existing behavior: no start_execution, no cr_pending transition."""
    from careervp.handlers import gap_handler

    mock_app_repo = MagicMock()
    with (
        patch.object(gap_handler, '_get_responses_dal', return_value=_ok_dal()),
        patch.object(gap_handler, '_get_application_repository', return_value=mock_app_repo),
        patch('careervp.handlers.gap_handler.boto3.client') as mock_boto,
    ):
        response = gap_handler.submit_response(_submit_event())

    assert response['statusCode'] == 200
    mock_boto.assert_not_called()
    # No cr_pending transition occurred.
    for call in mock_app_repo.update_state.call_args_list:
        assert call.kwargs.get('new_state') != 'cr_pending'


@pytest.mark.unit
def test_submit_flag_on_starts_chain_and_transitions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Flag ON → sfn.start_execution called once + transition to cr_pending."""
    from careervp.handlers import gap_handler

    monkeypatch.setenv('ARTIFACT_CHAIN_ENABLED', 'true')
    monkeypatch.setenv(
        'STEP_FUNCTIONS_CHAIN_ARN',
        'arn:aws:states:us-east-1:123456789012:stateMachine:careervp-artifact-chain-statemachine-dev',
    )

    mock_app_repo = MagicMock()
    mock_jobs_repo = MagicMock()
    mock_jobs_repo.get_job.return_value = {
        'company_name': 'Acme Corp',
        'job_posting_url': 'https://jobs.example.com/123',
    }
    mock_sfn = MagicMock()

    with (
        patch.object(gap_handler, '_get_responses_dal', return_value=_ok_dal()),
        patch.object(gap_handler, '_get_application_repository', return_value=mock_app_repo),
        patch.object(gap_handler, '_get_jobs_repository', return_value=mock_jobs_repo),
        patch('careervp.handlers.gap_handler.boto3.client', return_value=mock_sfn) as mock_boto,
    ):
        response = gap_handler.submit_response(_submit_event(job_id='job-xyz'))

    assert response['statusCode'] == 200
    mock_boto.assert_called_once_with('stepfunctions')
    mock_sfn.start_execution.assert_called_once()
    kwargs = mock_sfn.start_execution.call_args.kwargs
    assert kwargs['name'].startswith('chain-job-xyz-')
    sent = json.loads(kwargs['input'])
    assert sent['user_id'] == 'user-abc'
    assert sent['job_id'] == 'job-xyz'
    assert sent['company_name'] == 'Acme Corp'
    assert sent['application_id'] == 'job-xyz'
    mock_app_repo.update_state.assert_called_once_with(
        application_id='job-xyz',
        user_id='user-abc',
        new_state='cr_pending',
        expected_state='gap_responses_submitted',
    )


@pytest.mark.unit
def test_submit_chain_failure_still_returns_200(monkeypatch: pytest.MonkeyPatch) -> None:
    """A start_execution failure must not break the existing success response."""
    from careervp.handlers import gap_handler

    monkeypatch.setenv('ARTIFACT_CHAIN_ENABLED', 'true')
    monkeypatch.setenv('STEP_FUNCTIONS_CHAIN_ARN', 'arn:aws:states:us-east-1:123456789012:stateMachine:x')

    mock_sfn = MagicMock()
    mock_sfn.start_execution.side_effect = RuntimeError('sfn boom')

    with (
        patch.object(gap_handler, '_get_responses_dal', return_value=_ok_dal()),
        patch.object(gap_handler, '_get_application_repository', return_value=MagicMock()),
        patch.object(gap_handler, '_get_jobs_repository', return_value=MagicMock()),
        patch('careervp.handlers.gap_handler.boto3.client', return_value=mock_sfn),
    ):
        response = gap_handler.submit_response(_submit_event())

    assert response['statusCode'] == 200
