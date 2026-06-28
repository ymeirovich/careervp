"""
Category A — Application state-machine transition tests.

TEST-CHAIN-001 Category A backfill for FE-UI-029.
Characterise-existing mode: tests describe the code AS BUILT.

Prescribed file per TEST-DEBT-001; ad-hoc coverage lives in test_application_state.py.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from careervp.dal.application_repository import (
    VALID_TRANSITIONS,
    ApplicationRepository,
    InvalidStateTransitionError,
)

os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('DYNAMODB_TABLE_NAME', 'careervp-users-table-test')
os.environ.setdefault('ENVIRONMENT', 'test')


@pytest.fixture
def repo() -> ApplicationRepository:
    table = MagicMock()
    table.put_item.return_value = {}
    table.update_item.return_value = {}
    table.get_item.return_value = {}
    dal = MagicMock()
    dal.table_name = 'careervp-users-table-test'
    dal._get_db_handler.return_value = table
    return ApplicationRepository(dal=dal)


@pytest.mark.unit
class TestCRGateTransitions:
    """FE-UI-029 additive states: cr_pending, cr_failed."""

    def test_gap_responses_submitted_to_cr_pending(self, repo: ApplicationRepository) -> None:
        """Flag-ON path: gap submit transitions to cr_pending before artifact chain starts."""
        repo.update_state(
            application_id='app-1',
            user_id='user-1',
            new_state='cr_pending',
            expected_state='gap_responses_submitted',
        )

    def test_cr_pending_to_artifacts_generating(self, repo: ApplicationRepository) -> None:
        """CR worker success: cr_pending -> artifacts_generating."""
        repo.update_state(
            application_id='app-1',
            user_id='user-1',
            new_state='artifacts_generating',
            expected_state='cr_pending',
        )

    def test_cr_pending_to_cr_failed(self, repo: ApplicationRepository) -> None:
        """CR hard-fail: cr_pending -> cr_failed."""
        repo.update_state(
            application_id='app-1',
            user_id='user-1',
            new_state='cr_failed',
            expected_state='cr_pending',
        )

    def test_cr_failed_to_cr_pending_retry(self, repo: ApplicationRepository) -> None:
        """User-initiated retry: cr_failed -> cr_pending is the only allowed transition."""
        assert VALID_TRANSITIONS['cr_failed'] == ('cr_pending',)
        repo.update_state(
            application_id='app-1',
            user_id='user-1',
            new_state='cr_pending',
            expected_state='cr_failed',
        )

    def test_cr_failed_cannot_skip_to_artifacts_generating(self, repo: ApplicationRepository) -> None:
        """Illegal shortcut: cr_failed -> artifacts_generating must raise."""
        with pytest.raises(InvalidStateTransitionError):
            repo.update_state(
                application_id='app-1',
                user_id='user-1',
                new_state='artifacts_generating',
                expected_state='cr_failed',
            )


@pytest.mark.unit
class TestTerminalState:
    def test_artifacts_completed_is_terminal(self, repo: ApplicationRepository) -> None:
        """artifacts_completed has no valid outgoing transitions."""
        assert VALID_TRANSITIONS['artifacts_completed'] == ()

    def test_transition_from_artifacts_completed_raises(self, repo: ApplicationRepository) -> None:
        with pytest.raises(InvalidStateTransitionError):
            repo.update_state(
                application_id='app-1',
                user_id='user-1',
                new_state='artifacts_generating',
                expected_state='artifacts_completed',
            )


@pytest.mark.unit
class TestBackwardCompatFlagOff:
    def test_gap_responses_submitted_to_artifacts_generating_still_valid(self, repo: ApplicationRepository) -> None:
        """Flag-OFF (legacy) path: gap submit can go directly to artifacts_generating."""
        assert 'artifacts_generating' in VALID_TRANSITIONS['gap_responses_submitted']
        repo.update_state(
            application_id='app-1',
            user_id='user-1',
            new_state='artifacts_generating',
            expected_state='gap_responses_submitted',
        )
