"""Shared cancellation orchestration for all artifact cancel handlers.

cancel_artifact() is the single entry point for all artifact cancellation
requests.  It handles ownership + terminal-status guards, marks the artifact
CANCELLED, and — when the application has a RUNNING chain execution — stops
that execution via Step Functions and marks all still-pending chained
artifacts as cancelled.

FE-UI-043: shared_cancel_orchestration
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from botocore.exceptions import ClientError

from careervp.handlers.utils.observability import logger

_TERMINAL_STATUSES = {'COMPLETED', 'FAILED', 'CANCELLED'}
_CANCELLABLE_ARTIFACT_STATUSES = {'pending', 'processing'}


class CancelledBeforePersist(Exception):
    """Raised by an artifact worker when a status write is rejected because the
    artifact was cancelled concurrently (conditional-write CCF).

    The SQS handler treats this as a clean skip: send task_failure (so a chain
    branch is marked) and return WITHOUT re-raising, so the message is not sent
    to the DLQ and the cancelled artifact is never resurrected (FE-UI-043).
    """


class CancelStatus(str, Enum):
    CANCELLED = 'cancelled'
    CONFLICT = 'conflict'
    FORBIDDEN = 'forbidden'


@dataclass
class CancelResult:
    status: CancelStatus
    chain_stopped: bool = False
    artifacts_cancelled: list[str] = field(default_factory=list)


def _stop_running_chain(
    repos: Any,
    sfn: Any,
    application_id: str,
    user_id: str,
    app: dict[str, Any],
) -> tuple[bool, list[str]]:
    """Stop a RUNNING chain and mark pending/processing artifacts cancelled.

    Returns (chain_stopped, artifacts_cancelled).
    """
    chain_stopped = False
    artifacts_cancelled: list[str] = []
    arn = app.get('chain_execution_arn')
    if not arn:
        return chain_stopped, artifacts_cancelled

    try:
        sfn.stop_execution(executionArn=arn, cause='user_cancel')
        chain_stopped = True
    except ClientError as exc:
        logger.warning(
            'SFN stop_execution failed — artifact still marked CANCELLED',
            arn=arn,
            error=str(exc),
        )

    try:
        repos.app_repo.update_chain_execution_status(application_id, user_id, 'STOPPED')
    except Exception as exc:
        logger.warning(
            'Failed to update chain_execution_status to STOPPED',
            application_id=application_id,
            error=str(exc),
        )

    artifact_statuses: dict[str, Any] = app.get('artifact_statuses') or {}
    for atype, astatus in artifact_statuses.items():
        if str(astatus).lower() in _CANCELLABLE_ARTIFACT_STATUSES:
            try:
                repos.app_repo.update_artifact_status(application_id, user_id, atype, 'cancelled')
                artifacts_cancelled.append(atype)
            except Exception as exc:
                logger.warning(
                    'Failed to mark artifact cancelled',
                    artifact_type=atype,
                    application_id=application_id,
                    error=str(exc),
                )

    return chain_stopped, artifacts_cancelled


def cancel_artifact(
    artifact_type: str,
    artifact_id: str,
    application_id: str,
    user_id: str,
    repos: Any,
    sfn: Any,
) -> CancelResult:
    """Cancel an artifact, stopping the chain execution if one is running.

    Steps:
      1. Load the job; return CONFLICT if not found.
      2. Ownership guard — return FORBIDDEN if caller is not the owner.
      3. Terminal-status guard — return CONFLICT if already terminal.
      4. Mark the job CANCELLED (unconditional write; guard already verified).
      5. If the application has a RUNNING chain execution, stop it via SFN
         (best-effort: a failed stop still marks the artifact CANCELLED).
      6. Mark all artifact_statuses in {pending, processing} as 'cancelled'.

    Returns:
        CancelResult with status CANCELLED, CONFLICT, or FORBIDDEN.
    """
    job = repos.jobs_repo.get_job(artifact_id)
    if job is None:
        return CancelResult(status=CancelStatus.CONFLICT)

    job_owner = str(job.get('user_id', ''))
    if not job_owner or job_owner != user_id:
        # Deny by default: a record with no owner must not be cancellable by an
        # arbitrary authenticated caller (positive ownership assertion).
        return CancelResult(status=CancelStatus.FORBIDDEN)

    job_status = str(job.get('status', '')).upper()
    if job_status in _TERMINAL_STATUSES:
        return CancelResult(status=CancelStatus.CONFLICT)

    repos.jobs_repo.update_job_status(artifact_id, 'CANCELLED')

    chain_stopped = False
    artifacts_cancelled: list[str] = []

    if application_id:
        try:
            app = repos.app_repo.get(application_id, user_id)
        except Exception as exc:
            logger.warning(
                'Failed to load application for chain cancel check',
                application_id=application_id,
                error=str(exc),
            )
            app = None

        if isinstance(app, dict) and app.get('chain_execution_status') == 'RUNNING':
            chain_stopped, artifacts_cancelled = _stop_running_chain(repos, sfn, application_id, user_id, app)

    return CancelResult(
        status=CancelStatus.CANCELLED,
        chain_stopped=chain_stopped,
        artifacts_cancelled=artifacts_cancelled,
    )
