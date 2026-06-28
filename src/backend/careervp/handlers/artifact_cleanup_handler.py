"""Orphan-cleanup reaper for cancelled artifacts.

Removes partial artifacts left by cancellation and reconciles late completions
(a worker that finished AFTER the user cancelled).

Safety invariants (FE-UI-043 § security-reaper):
  1. Never deletes an artifact owned by a different user (ownership-scoped).
  2. Never deletes a COMPLETED artifact for a non-stopped (live) chain.
  3. Idempotent — a missing S3 object or already-deleted row is not an error.

Trigger modes:
  - EventBridge schedule (hourly sweeper): sweeps all CANCELLED jobs that
    still have a result_key present, or COMPLETED jobs on a STOPPED chain.
  - Inline from cancel_artifact (immediate cleanup for the cancelled artifact).

Dry-run: set env CLEANUP_DRY_RUN=true to log without deleting (first rollout).
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError

from careervp.handlers.utils.observability import logger

_DRY_RUN = os.environ.get('CLEANUP_DRY_RUN', 'false').lower() == 'true'


def _is_dry_run() -> bool:
    return os.environ.get('CLEANUP_DRY_RUN', 'false').lower() == 'true'


def _load_chain_status(deps: Any, application_id: str, user_id: str) -> str:
    try:
        app = deps.app_repo.get(application_id, user_id)
    except Exception as exc:
        logger.warning('Cleanup: failed to load application', application_id=application_id, error=str(exc))
        app = None
    return str((app or {}).get('chain_execution_status', '') or '').upper()


def _delete_s3_result(s3: Any, bucket: str, result_key: str, job_id: str) -> None:
    if _is_dry_run():
        logger.info('Cleanup DRY_RUN: would delete S3 object', bucket=bucket, key=result_key)
        return
    try:
        s3.delete_object(Bucket=bucket, Key=result_key)
        logger.info('Cleanup: deleted S3 result', job_id=job_id, key=result_key)
    except ClientError as exc:
        if exc.response['Error']['Code'] == 'NoSuchKey':
            logger.info('Cleanup: S3 object already gone (idempotent)', job_id=job_id)
        else:
            raise


def _rollback_late_completed(jobs_repo: Any, job_id: str) -> None:
    if _is_dry_run():
        logger.info('Cleanup DRY_RUN: would roll back COMPLETED to CANCELLED', job_id=job_id)
        return
    try:
        jobs_repo.update_job_status(job_id, 'CANCELLED')
        logger.info('Cleanup: rolled back late COMPLETED to CANCELLED', job_id=job_id)
    except Exception as exc:
        logger.warning('Cleanup: failed to roll back job status', job_id=job_id, error=str(exc))


def cleanup_cancelled_artifact(
    job_id: str,
    application_id: str,
    user_id: str,
    artifact_type: str,
    deps: Any,
) -> None:
    """Clean up a single cancelled (or late-completed) artifact.

    Args:
        job_id: The artifact job ID.
        application_id: The parent application ID.
        user_id: The requesting cleanup scope user_id.
        artifact_type: Artifact type string (e.g. 'vpr', 'cover_letter').
        deps: SimpleNamespace with s3, jobs_repo, app_repo.
    """
    job = deps.jobs_repo.get_job(job_id)
    if job is None:
        logger.info('Cleanup: job not found (already deleted)', job_id=job_id)
        return

    job_user_id = str(job.get('user_id', ''))
    if job_user_id != user_id:
        logger.warning(
            'Cleanup: ownership mismatch — skipping (safety invariant 1)',
            job_id=job_id,
            job_owner=job_user_id,
            requesting_user=user_id,
        )
        return

    job_status = str(job.get('status', '')).upper()
    chain_status = _load_chain_status(deps, application_id, user_id)

    if job_status == 'COMPLETED' and chain_status != 'STOPPED':
        logger.info(
            'Cleanup: COMPLETED artifact on live chain — skipping (safety invariant 2)',
            job_id=job_id,
            chain_status=chain_status,
        )
        return

    result_key: str | None = job.get('result_key')
    if result_key:
        bucket = os.environ.get('VPR_RESULTS_BUCKET_NAME', '')
        if bucket:
            _delete_s3_result(deps.s3, bucket, result_key, job_id)

    if job_status == 'COMPLETED' and chain_status == 'STOPPED':
        _rollback_late_completed(deps.jobs_repo, job_id)


def _make_cleanup_deps() -> Any:
    """Build production dependencies for the reaper sweeper."""
    from careervp.dal.application_repository import ApplicationRepository
    from careervp.dal.dynamo_dal_handler import DynamoDalHandler
    from careervp.dal.jobs_repository import JobsRepository

    apps_table = os.environ.get('APPLICATIONS_TABLE_NAME', '')
    jobs_table = os.environ.get('DYNAMODB_TABLE_NAME', '')

    return SimpleNamespace(
        s3=boto3.client('s3'),
        jobs_repo=JobsRepository(jobs_table) if jobs_table else None,
        app_repo=ApplicationRepository(DynamoDalHandler(apps_table)) if apps_table else None,
    )


def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """EventBridge-scheduled orphan-cleanup reaper.

    Sweeps for CANCELLED jobs with a result_key still in S3, and COMPLETED
    jobs on a STOPPED chain (late completions), then cleans them up.
    """
    _ = context
    dry_run = _is_dry_run()
    logger.info('Artifact cleanup reaper starting', dry_run=dry_run)

    cleaned = 0
    try:
        deps = _make_cleanup_deps()
        if deps.jobs_repo is None:
            logger.warning('No jobs table configured — reaper skipping')
            return {'status': 'ok', 'cleaned': 0, 'dry_run': dry_run}

        cancelled_jobs = _scan_cancelled_with_result(deps)
        for job in cancelled_jobs:
            job_id = str(job.get('job_id', ''))
            application_id = str(job.get('application_id', ''))
            user_id = str(job.get('user_id', ''))
            artifact_type = str(job.get('artifact_type', 'unknown'))
            if not job_id or not user_id:
                continue
            try:
                cleanup_cancelled_artifact(
                    job_id=job_id,
                    application_id=application_id,
                    user_id=user_id,
                    artifact_type=artifact_type,
                    deps=deps,
                )
                cleaned += 1
            except Exception as exc:
                logger.warning('Cleanup: error processing job', job_id=job_id, error=str(exc))

    except Exception as exc:
        logger.error('Artifact cleanup reaper error', error=str(exc))
        return {'status': 'error', 'cleaned': cleaned, 'dry_run': dry_run}

    logger.info('Artifact cleanup reaper finished', cleaned=cleaned, dry_run=dry_run)
    return {'status': 'ok', 'cleaned': cleaned, 'dry_run': dry_run}


def _scan_cancelled_with_result(deps: Any) -> list[dict[str, Any]]:
    """Scan for CANCELLED jobs that still have a result_key (orphans)."""
    try:
        result: list[dict[str, Any]] = deps.jobs_repo.scan_by_status('CANCELLED', has_result_key=True)
        return result
    except Exception as exc:
        logger.warning('Cleanup: scan failed', error=str(exc))
        return []
