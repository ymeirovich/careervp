"""Tests for handler-side artifact dependency utilities."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from careervp.handlers.artifact_dependency_utils import build_start_chain

pytestmark = pytest.mark.unit


def test_build_start_chain_claims_and_marks_cr_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('STEP_FUNCTIONS_CHAIN_ARN', 'arn:aws:states:us-east-1:123456789012:stateMachine:chain')
    mock_sfn = MagicMock()
    mock_sfn.start_execution.return_value = {'executionArn': 'arn:aws:states:us-east-1:123456789012:execution:chain:run-1'}
    monkeypatch.setattr('boto3.client', MagicMock(return_value=mock_sfn))
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
    app_repo.set_chain_execution.assert_called_once_with(
        application_id='app-1',
        user_id='user-1',
        execution_arn='arn:aws:states:us-east-1:123456789012:execution:chain:run-1',
        status='RUNNING',
    )
