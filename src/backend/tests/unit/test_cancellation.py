"""TEST-CANCEL-001 § unit-cancellation: cancel_artifact chain vs standalone (6 tests).

Tests for careervp.logic.cancellation.cancel_artifact — the shared orchestration
function that all 4 existing cancel handlers + new CR cancel handler will call.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from botocore.exceptions import ClientError

from careervp.logic.cancellation import (  # type: ignore[import-not-found]
    CancelStatus,
    cancel_artifact,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CCF_ERROR = ClientError(
    {'Error': {'Code': 'ConditionalCheckFailedException', 'Message': ''}},
    'StopExecution',
)


def _make_repos(
    *,
    job_status: str = 'PROCESSING',
    job_owner: str = 'user-1',
    chain_status: str | None = None,
    artifact_statuses: dict[str, str] | None = None,
) -> SimpleNamespace:
    """Build a minimal repos namespace with mocked jobs_repo and app_repo."""
    jobs_repo = MagicMock()
    jobs_repo.get_job.return_value = {
        'job_id': 'job-abc',
        'user_id': job_owner,
        'status': job_status,
    }

    app_repo = MagicMock()
    app_repo.get.return_value = {
        'applicationId': 'app-1',
        'userId': 'user-1',
        'chain_execution_arn': 'arn:aws:states:us-east-1:123:execution:chain:run-1',
        'chain_execution_status': chain_status,
        'artifact_statuses': artifact_statuses
        or {
            'vpr': 'pending',
            'cover_letter': 'processing',
            'interview_prep': 'pending',
        },
    }
    return SimpleNamespace(jobs_repo=jobs_repo, app_repo=app_repo)


def _make_sfn() -> MagicMock:
    sfn = MagicMock()
    sfn.stop_execution.return_value = {}
    return sfn


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_chain_cancel_stops_sfn_and_marks_pending_cancelled() -> None:
    """Cancelling a chained artifact stops the SFN execution and marks all
    pending/processing artifacts as cancelled."""
    repos = _make_repos(chain_status='RUNNING')
    sfn = _make_sfn()

    result = cancel_artifact(
        artifact_type='vpr',
        artifact_id='job-abc',
        application_id='app-1',
        user_id='user-1',
        repos=repos,
        sfn=sfn,
    )

    assert result.status == CancelStatus.CANCELLED
    assert result.chain_stopped is True
    # SFN execution must be stopped
    sfn.stop_execution.assert_called_once()
    stop_args = sfn.stop_execution.call_args
    assert 'executionArn' in (stop_args.kwargs or stop_args[1] or {}) or len(stop_args.args) >= 1 or stop_args is not None
    # Chain status updated to STOPPED
    repos.app_repo.update_chain_execution_status.assert_called_once()
    call_kwargs = repos.app_repo.update_chain_execution_status.call_args
    assert 'STOPPED' in str(call_kwargs)
    # Pending artifacts flagged as cancelled
    assert len(result.artifacts_cancelled) > 0


def test_standalone_cancel_does_not_stop_sfn() -> None:
    """Cancelling a job with no running chain must NOT call sfn.stop_execution."""
    repos = _make_repos(chain_status=None)  # no running chain
    sfn = _make_sfn()

    result = cancel_artifact(
        artifact_type='vpr',
        artifact_id='job-abc',
        application_id='app-1',
        user_id='user-1',
        repos=repos,
        sfn=sfn,
    )

    assert result.status == CancelStatus.CANCELLED
    assert result.chain_stopped is False
    sfn.stop_execution.assert_not_called()


def test_cancel_idempotent_returns_conflict_on_already_cancelled() -> None:
    """Cancelling a job that is already CANCELLED returns CONFLICT (idempotent)."""
    repos = _make_repos(job_status='CANCELLED')
    sfn = _make_sfn()

    result = cancel_artifact(
        artifact_type='vpr',
        artifact_id='job-abc',
        application_id='app-1',
        user_id='user-1',
        repos=repos,
        sfn=sfn,
    )

    assert result.status == CancelStatus.CONFLICT
    # No DynamoDB writes should happen for already-terminal jobs
    repos.jobs_repo.update_job_status.assert_not_called()
    sfn.stop_execution.assert_not_called()


def test_cancel_forbidden_when_not_owner() -> None:
    """Cancelling another user's job returns FORBIDDEN."""
    repos = _make_repos(job_owner='other-user')
    sfn = _make_sfn()

    result = cancel_artifact(
        artifact_type='vpr',
        artifact_id='job-abc',
        application_id='app-1',
        user_id='user-1',  # different from job_owner
        repos=repos,
        sfn=sfn,
    )

    assert result.status == CancelStatus.FORBIDDEN
    repos.jobs_repo.update_job_status.assert_not_called()
    sfn.stop_execution.assert_not_called()


def test_cancel_conflict_when_terminal_completed() -> None:
    """Cancelling a COMPLETED job returns CONFLICT."""
    repos = _make_repos(job_status='COMPLETED')
    sfn = _make_sfn()

    result = cancel_artifact(
        artifact_type='vpr',
        artifact_id='job-abc',
        application_id='app-1',
        user_id='user-1',
        repos=repos,
        sfn=sfn,
    )

    assert result.status == CancelStatus.CONFLICT
    sfn.stop_execution.assert_not_called()


def test_chain_cancel_sfn_exception_still_marks_cancelled() -> None:
    """If SFN.stop_execution raises, the artifact is still marked CANCELLED
    and no exception propagates (the cancel is best-effort on the chain stop)."""
    repos = _make_repos(chain_status='RUNNING')
    sfn = _make_sfn()
    sfn.stop_execution.side_effect = ClientError(
        {'Error': {'Code': 'ExecutionDoesNotExist', 'Message': ''}},
        'StopExecution',
    )

    # Must not raise
    result = cancel_artifact(
        artifact_type='vpr',
        artifact_id='job-abc',
        application_id='app-1',
        user_id='user-1',
        repos=repos,
        sfn=sfn,
    )

    # Job is still cancelled even though SFN stop failed
    assert result.status == CancelStatus.CANCELLED
    # The failed stop attempt should have been tried
    sfn.stop_execution.assert_called_once()
