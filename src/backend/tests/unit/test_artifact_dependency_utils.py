"""Tests for handler-side artifact dependency utilities."""

from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest
from botocore.exceptions import ClientError

from careervp.handlers.artifact_dependency_utils import build_start_chain

pytestmark = pytest.mark.unit


def _ccf() -> ClientError:
    return ClientError({'Error': {'Code': 'ConditionalCheckFailedException', 'Message': ''}}, 'UpdateItem')


def _make_sfn(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock_sfn = MagicMock()
    mock_sfn.start_execution.return_value = {'executionArn': 'arn:aws:states:us-east-1:123456789012:execution:chain:run-1'}
    monkeypatch.setenv('STEP_FUNCTIONS_CHAIN_ARN', 'arn:aws:states:us-east-1:123456789012:stateMachine:chain')
    monkeypatch.setattr('boto3.client', MagicMock(return_value=mock_sfn))
    return mock_sfn


def test_build_start_chain_claims_and_marks_cr_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    _make_sfn(monkeypatch)
    app_repo = MagicMock()

    start_chain = build_start_chain(app_repo)
    execution_arn = start_chain(
        node='company_research',
        application_id='app-1',
        user_id='user-1',
        requested_artifact='vpr',
    )

    assert execution_arn == 'arn:aws:states:us-east-1:123456789012:execution:chain:run-1'
    app_repo.claim_chain_execution.assert_called_once_with(application_id='app-1', user_id='user-1')
    app_repo.update_state.assert_called_once_with(
        application_id='app-1',
        user_id='user-1',
        new_state='cr_pending',
        expected_state='gap_responses_submitted',
    )
    # Stale 'cancelled' artifact status is reset to 'pending' before chain starts.
    app_repo.update_artifact_status.assert_called_once_with(
        application_id='app-1',
        user_id='user-1',
        artifact_type='company_research',
        status='pending',
    )
    app_repo.set_chain_execution.assert_called_once_with(
        application_id='app-1',
        user_id='user-1',
        execution_arn='arn:aws:states:us-east-1:123456789012:execution:chain:run-1',
        status='RUNNING',
    )


def test_build_start_chain_retries_cr_pending_from_cr_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    """When state is cr_failed (not gap_responses_submitted), the second update_state attempt must succeed."""
    _make_sfn(monkeypatch)
    app_repo = MagicMock()
    # First call (gap_responses_submitted) → CCF; second call (cr_failed) → success.
    app_repo.update_state.side_effect = [_ccf(), None]

    start_chain = build_start_chain(app_repo)
    execution_arn = start_chain(
        node='company_research',
        application_id='app-1',
        user_id='user-1',
        requested_artifact='vpr',
    )

    assert execution_arn == 'arn:aws:states:us-east-1:123456789012:execution:chain:run-1'
    assert app_repo.update_state.call_args_list == [
        call(application_id='app-1', user_id='user-1', new_state='cr_pending', expected_state='gap_responses_submitted'),
        call(application_id='app-1', user_id='user-1', new_state='cr_pending', expected_state='cr_failed'),
    ]
    app_repo.update_artifact_status.assert_called_once_with(
        application_id='app-1',
        user_id='user-1',
        artifact_type='company_research',
        status='pending',
    )


def test_build_start_chain_proceeds_when_already_cr_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    """When state is already cr_pending (both CCF), chain still starts — state is already correct."""
    _make_sfn(monkeypatch)
    app_repo = MagicMock()
    app_repo.update_state.side_effect = [_ccf(), _ccf()]

    start_chain = build_start_chain(app_repo)
    execution_arn = start_chain(
        node='company_research',
        application_id='app-1',
        user_id='user-1',
        requested_artifact='vpr',
    )

    assert execution_arn == 'arn:aws:states:us-east-1:123456789012:execution:chain:run-1'
    assert app_repo.update_state.call_count == 2
    app_repo.update_artifact_status.assert_called_once_with(
        application_id='app-1',
        user_id='user-1',
        artifact_type='company_research',
        status='pending',
    )


def test_build_start_chain_reset_cr_status_failure_is_non_fatal(monkeypatch: pytest.MonkeyPatch) -> None:
    """If update_artifact_status raises, the chain still starts (best-effort reset)."""
    _make_sfn(monkeypatch)
    app_repo = MagicMock()
    app_repo.update_artifact_status.side_effect = RuntimeError('DynamoDB unavailable')

    start_chain = build_start_chain(app_repo)
    execution_arn = start_chain(
        node='company_research',
        application_id='app-1',
        user_id='user-1',
        requested_artifact='vpr',
    )

    assert execution_arn == 'arn:aws:states:us-east-1:123456789012:execution:chain:run-1'
