"""TEST-CANCEL-001 § security-reaper: orphan-cleanup safety invariants (3 tests).

The orphan-cleanup reaper (artifact_cleanup_handler) must enforce three
hard safety rules that prevent data-loss attacks and accidental cleanup:

  1. Never deletes an artifact owned by a different user
     (ownership-scoped delete: user_id must match)
  2. Never deletes a COMPLETED artifact for a non-stopped chain
     (only delete COMPLETED when chain_execution_status == STOPPED)
  3. Cleanup is idempotent — a missing S3 object or already-deleted
     DynamoDB row is not an error

All 3 tests are RED until the reaper module exists at
careervp.handlers.artifact_cleanup_handler.
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from careervp.handlers.artifact_cleanup_handler import (  # type: ignore[import-not-found]
    cleanup_cancelled_artifact,
)

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

_ENV = {
    'POWERTOOLS_SERVICE_NAME': 'test',
    'LOG_LEVEL': 'WARNING',
    'DYNAMODB_TABLE_NAME': 'test-table',
    'APPLICATIONS_TABLE_NAME': 'test-apps',
    'VPR_RESULTS_BUCKET_NAME': 'test-bucket',
    'CLEANUP_DRY_RUN': 'false',
}

_OWNER = 'user-owner'
_OTHER = 'user-other'
_APP_ID = 'app-1'
_JOB_ID = 'job-xyz'
_RESULT_KEY = f'results/{_JOB_ID}.json'


def _make_deps(
    *,
    job_user_id: str = _OWNER,
    job_status: str = 'CANCELLED',
    result_key: str | None = _RESULT_KEY,
    chain_status: str | None = 'STOPPED',
) -> SimpleNamespace:
    """Build minimal dependency stubs for cleanup_cancelled_artifact."""
    mock_s3 = MagicMock()
    # S3 delete returns normally by default
    mock_s3.delete_object.return_value = {}

    mock_jobs_repo = MagicMock()
    mock_jobs_repo.get_job.return_value = {
        'job_id': _JOB_ID,
        'user_id': job_user_id,
        'status': job_status,
        'result_key': result_key,
    }

    mock_app_repo = MagicMock()
    mock_app_repo.get.return_value = {
        'applicationId': _APP_ID,
        'userId': _OWNER,
        'chain_execution_status': chain_status,
    }

    return SimpleNamespace(
        s3=mock_s3,
        jobs_repo=mock_jobs_repo,
        app_repo=mock_app_repo,
    )


# ---------------------------------------------------------------------------
# TEST 1: Never deletes another user's artifact
# ---------------------------------------------------------------------------


@patch.dict(os.environ, _ENV)
def test_reaper_never_deletes_other_users_artifact() -> None:
    """cleanup_cancelled_artifact must refuse to delete an artifact that belongs
    to a different user than the requesting cleanup scope user_id."""
    deps = _make_deps(job_user_id=_OTHER)  # artifact owned by _OTHER

    cleanup_cancelled_artifact(
        job_id=_JOB_ID,
        application_id=_APP_ID,
        user_id=_OWNER,  # cleanup called for _OWNER, but artifact belongs to _OTHER
        artifact_type='vpr',
        deps=deps,
    )

    # S3 must NOT be touched for another user's artifact
    deps.s3.delete_object.assert_not_called()
    # DynamoDB job row must NOT be deleted/updated
    deps.jobs_repo.delete_job.assert_not_called()
    deps.jobs_repo.update_job_status.assert_not_called()


# ---------------------------------------------------------------------------
# TEST 2: Never deletes COMPLETED artifact of a non-stopped (live) chain
# ---------------------------------------------------------------------------


@patch.dict(os.environ, _ENV)
def test_reaper_never_deletes_completed_artifact_for_live_chain() -> None:
    """A COMPLETED artifact must NOT be deleted when the chain is still RUNNING
    (or otherwise non-STOPPED).  Only late-completions on a STOPPED chain may
    be rolled back."""
    # Job COMPLETED but chain is still RUNNING (not stopped)
    deps = _make_deps(job_status='COMPLETED', chain_status='RUNNING')

    cleanup_cancelled_artifact(
        job_id=_JOB_ID,
        application_id=_APP_ID,
        user_id=_OWNER,
        artifact_type='vpr',
        deps=deps,
    )

    # Must NOT touch S3 for a live-chain COMPLETED artifact
    deps.s3.delete_object.assert_not_called()
    # Must NOT mutate the job row
    deps.jobs_repo.delete_job.assert_not_called()
    deps.jobs_repo.update_job_status.assert_not_called()


# ---------------------------------------------------------------------------
# TEST 3: Idempotent — missing S3 object is not an error
# ---------------------------------------------------------------------------


@patch.dict(os.environ, _ENV)
def test_reaper_idempotent_on_missing_s3_object() -> None:
    """If the S3 result object is already gone (NoSuchKey), the reaper must
    treat the cleanup as a success and NOT raise an exception."""
    from botocore.exceptions import ClientError

    deps = _make_deps(job_status='CANCELLED', chain_status='STOPPED')
    deps.s3.delete_object.side_effect = ClientError(
        {'Error': {'Code': 'NoSuchKey', 'Message': 'The specified key does not exist.'}},
        'DeleteObject',
    )

    # Must not raise
    cleanup_cancelled_artifact(
        job_id=_JOB_ID,
        application_id=_APP_ID,
        user_id=_OWNER,
        artifact_type='vpr',
        deps=deps,
    )

    # The delete was attempted (idempotent attempt is expected)
    deps.s3.delete_object.assert_called_once()
