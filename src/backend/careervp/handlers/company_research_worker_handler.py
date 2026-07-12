"""
Company Research Worker Handler.

SQS-triggered Lambda that processes async company research jobs.
Consumes messages from company_research_queue, applies confidence gate,
persists results, and signals the Step Functions chain (or enqueues VPR
directly in standalone mode).

Per docs/upgrade/specs/FE-UI-030-cr-async-worker.yaml
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import boto3  # type: ignore[import-untyped]
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import BaseModel, Field

from careervp.dal.application_repository import ApplicationRepository
from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.dal.jobs_repository import JobsRepository
from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.logic.company_research import research_company
from careervp.logic.company_research_store import write_cr_artifact, write_cr_failed
from careervp.logic.utils.llm_metering import bind_llm_usage_context
from careervp.models.company import CompanyResearchRequest, CompanyResearchResult, ResearchSource

_DEFAULT_CR_CONFIDENCE_THRESHOLD = 0.85


class CRWorkerInput(BaseModel):
    """Validated SQS message body for company_research_queue."""

    user_id: str
    job_id: str
    application_id: str | None = Field(default=None)
    company_name: str | None = Field(default=None)
    job_posting_url: str | None = Field(default=None)
    domain: str | None = Field(default=None)
    task_token: str | None = Field(default=None)


class RetryableError(Exception):
    """Raised when confidence is below threshold and retries remain.

    SQS re-delivers the message after visibility_timeout, providing natural
    exponential back-off without custom sleep().
    """


def _get_confidence_threshold() -> float:
    raw = os.environ.get('CR_CONFIDENCE_THRESHOLD', str(_DEFAULT_CR_CONFIDENCE_THRESHOLD))
    try:
        return float(raw)
    except ValueError:
        return _DEFAULT_CR_CONFIDENCE_THRESHOLD


def _get_app_repo() -> ApplicationRepository:
    table_name = os.environ.get('APPLICATIONS_TABLE_NAME', '')
    return ApplicationRepository(DynamoDalHandler(table_name))


def _get_jobs_repository() -> JobsRepository:
    table_name = os.environ.get('JOBS_TABLE_NAME') or os.environ.get('VPR_JOBS_TABLE_NAME') or None
    return JobsRepository(table_name=table_name)


def _coerce_str(value: Any) -> str:
    return str(value or '').strip()


def _hydrate_company_fields(input_data: CRWorkerInput) -> CRWorkerInput:
    """Fill CR fields omitted by resolver-started chains from the jobs table."""
    if _coerce_str(input_data.company_name):
        return input_data

    candidate_job_ids = [
        _coerce_str(input_data.job_id),
        _coerce_str(input_data.application_id),
    ]
    try:
        application = _get_app_repo().get(application_id=_coerce_str(input_data.application_id) or input_data.job_id, user_id=input_data.user_id)
        if isinstance(application, dict):
            candidate_job_ids.append(_coerce_str(application.get('job_id')))
    except Exception as exc:
        logger.warning('Could not load application for CR field hydration', job_id=input_data.job_id, error=str(exc))

    try:
        jobs_repo = _get_jobs_repository()
        for candidate_job_id in dict.fromkeys(job_id for job_id in candidate_job_ids if job_id):
            job = jobs_repo.get_job(candidate_job_id)
            if not isinstance(job, dict):
                continue
            company_name = _coerce_str(job.get('company_name') or job.get('company'))
            if not company_name:
                continue
            return input_data.model_copy(
                update={
                    'company_name': company_name,
                    'job_posting_url': input_data.job_posting_url or _coerce_str(job.get('job_posting_url') or job.get('url')) or None,
                    'domain': input_data.domain or _coerce_str(job.get('domain')) or None,
                }
            )
    except Exception as exc:
        logger.warning('Could not hydrate CR fields from jobs table', job_id=input_data.job_id, error=str(exc))

    return input_data


def _persist_cr_result(user_id: str, job_id: str, result: CompanyResearchResult) -> None:
    """Write CR data to the canonical artifacts table."""
    write_cr_artifact(application_id=job_id, user_id=user_id, result=result)


def _send_chain_signal(
    task_token: str | None,
    job_id: str,
    success: bool,
    cause: str = '',
    company_context: dict[str, Any] | None = None,
) -> None:
    """Send task success/failure callback to Step Functions.

    No-op when STEP_FUNCTIONS_CHAIN_ARN is unset (supports local testing).
    """
    chain_arn = os.environ.get('STEP_FUNCTIONS_CHAIN_ARN', '')
    if not task_token or not chain_arn:
        return
    sfn = boto3.client('stepfunctions')
    if success:
        sfn.send_task_success(
            taskToken=task_token,
            output=json.dumps({'job_id': job_id, 'company_context': company_context or {}}),
        )
    else:
        sfn.send_task_failure(
            taskToken=task_token,
            error='CRHardFail',
            cause=cause or 'Company research hard-failed after max retries',
        )


def _enqueue_vpr_standalone(user_id: str, job_id: str, result: CompanyResearchResult) -> None:
    """Enqueue VPR directly when not running inside a Step Functions chain."""
    queue_url = os.environ.get('VPR_JOBS_QUEUE_URL', '')
    if not queue_url:
        logger.warning('VPR standalone enqueue skipped: VPR_JOBS_QUEUE_URL not set')
        return
    sqs = boto3.client('sqs')
    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(
            {
                'user_id': user_id,
                'job_id': job_id,
                'company_context': result.model_dump(mode='json'),
            }
        ),
    )


def _handle_cancel_ccf(input_data: CRWorkerInput) -> None:
    """Handle ConditionalCheckFailedException from the cancel guard (FE-UI-043).

    Signals chain failure so Step Functions routes to HandleCRFailure (→ cr_failed).
    If the chain was already stopped by cancel_artifact, send_task_failure raises and
    is swallowed.  In both cases we then directly transition the application state
    cr_pending → cr_failed and set company_research_error so the UI is not stuck.
    """
    logger.info(
        'CR job cancelled before COMPLETED write — aborting cleanly',
        job_id=input_data.job_id,
        cancelled_before_persist=True,
    )
    try:
        _send_chain_signal(
            task_token=input_data.task_token,
            job_id=input_data.job_id,
            success=False,
            cause='CR cancelled before persist',
        )
    except Exception as signal_exc:
        logger.info(
            'CR cancel chain signal suppressed (execution already stopped)',
            job_id=input_data.job_id,
            error=str(signal_exc),
        )

    # Whether the chain signal succeeded or not, directly unblock the UI by
    # transitioning the application state and setting the error flag.  If the
    # chain's HandleCRFailure state already did this, both writes hit CCF/no-op.
    app_repo = _get_app_repo()
    try:
        app_repo.set_company_research_error(
            application_id=input_data.job_id,
            user_id=input_data.user_id,
            error=True,
        )
    except Exception as exc:
        logger.info('CR cancel: could not set company_research_error', job_id=input_data.job_id, error=str(exc))
    try:
        app_repo.update_state(
            application_id=input_data.job_id,
            user_id=input_data.user_id,
            new_state='cr_failed',
            expected_state='cr_pending',
        )
    except Exception as exc:
        logger.info(
            'CR cancel state transition skipped (application already past cr_pending)',
            job_id=input_data.job_id,
            error=str(exc),
        )


def _hard_fail(input_data: CRWorkerInput, cause: str) -> None:
    """Record CR failure on the application record without raising.

    Not raising ensures the message is NOT forwarded to DLQ for intentional
    hard-fails (sub-threshold confidence after max retries, LLM_FALLBACK).
    """
    logger.error('CR hard-fail after max retries', user_id=input_data.user_id, job_id=input_data.job_id, cause=cause)
    app_repo = _get_app_repo()
    try:
        write_cr_failed(application_id=input_data.job_id, user_id=input_data.user_id)
        app_repo.set_company_research_error(
            application_id=input_data.job_id,
            user_id=input_data.user_id,
            error=True,
        )
        app_repo.update_artifact_status(
            application_id=input_data.job_id,
            user_id=input_data.user_id,
            artifact_type='company_research',
            status='failed',
        )
    except Exception as exc:
        logger.warning('Hard-fail DAL update partial', error=str(exc))

    # Best-effort state transition. The conditional guard intentionally refuses to
    # regress an application that is no longer in cr_pending (e.g. CR re-run on an
    # already-advanced application). A ConditionalCheckFailedException here means the
    # guard worked as designed and is safely ignored — it is not a failure.
    try:
        app_repo.update_state(
            application_id=input_data.job_id,
            user_id=input_data.user_id,
            new_state='cr_failed',
            expected_state='cr_pending',
        )
    except Exception as exc:
        from botocore.exceptions import ClientError as _ClientError  # type: ignore[import-untyped]

        if isinstance(exc, _ClientError) and exc.response['Error']['Code'] == 'ConditionalCheckFailedException':
            logger.info(
                'Hard-fail state transition skipped (application not in cr_pending)',
                job_id=input_data.job_id,
            )
        else:
            logger.warning('Hard-fail state transition failed', error=str(exc))

    _send_chain_signal(
        task_token=input_data.task_token,
        job_id=input_data.job_id,
        success=False,
        cause=cause,
    )
    metrics.add_metric(name='CRHardFail', unit='Count', value=1)


async def _async_process_record(input_data: CRWorkerInput, receive_count: int) -> None:
    threshold = _get_confidence_threshold()
    company_name = _coerce_str(input_data.company_name)
    if not company_name:
        _hard_fail(input_data, 'company_name unavailable for company research')
        return

    cr_request = CompanyResearchRequest(
        company_name=company_name,
        domain=input_data.domain,
        job_posting_url=input_data.job_posting_url,  # type: ignore[arg-type]
    )
    with bind_llm_usage_context(
        application_id=_coerce_str(input_data.application_id) or input_data.job_id,
        user_id=input_data.user_id,
    ):
        research_result = await research_company(cr_request)

    if not research_result.success or not research_result.data:
        cause = research_result.error or 'research_company returned no data'
        _hard_fail(input_data, cause)
        return

    cr_result: CompanyResearchResult = research_result.data

    # LLM_FALLBACK always hard-fails (confidence ≤ 0.5 < threshold); no retry benefit.
    if cr_result.source == ResearchSource.LLM_FALLBACK:
        _hard_fail(input_data, f'LLM_FALLBACK source; confidence={cr_result.confidence_score:.2f}')
        return

    if cr_result.confidence_score < threshold:
        if receive_count < 3:
            logger.warning(
                'CR confidence below threshold — retrying',
                confidence=cr_result.confidence_score,
                threshold=threshold,
                receive_count=receive_count,
            )
            raise RetryableError(f'confidence={cr_result.confidence_score:.2f} < {threshold}')
        # Max retries exhausted
        _hard_fail(input_data, f'confidence={cr_result.confidence_score:.2f} below threshold after {receive_count} attempts')
        return

    # Confidence gate passed — persist and signal.
    _persist_cr_result(input_data.user_id, input_data.job_id, cr_result)

    # CANCELLED guard (FE-UI-043 § worker_cancelled_guard): the update_artifact_status
    # write uses a conditional DynamoDB expression so that if a concurrent cancel
    # already set the artifact status to 'cancelled', this write raises
    # ConditionalCheckFailedException.  On CCF we signal success (not CRHardFail) so
    # the chain does not route to handle_cr_failure and the UI shows no error.
    from botocore.exceptions import ClientError as _ClientError

    app_repo = _get_app_repo()
    try:
        app_repo.update_artifact_status(
            application_id=input_data.job_id,
            user_id=input_data.user_id,
            artifact_type='company_research',
            status='completed',
            fail_if_status='cancelled',
        )
    except _ClientError as exc:
        if exc.response['Error']['Code'] == 'ConditionalCheckFailedException':
            _handle_cancel_ccf(input_data)
            return
        raise

    try:
        app_repo.update_state(
            application_id=input_data.job_id,
            user_id=input_data.user_id,
            new_state='artifacts_generating',
            expected_state='cr_pending',
        )
    except Exception as exc:
        logger.warning('CR worker state transition skipped', job_id=input_data.job_id, error=str(exc))

    chain_enabled = os.environ.get('ARTIFACT_CHAIN_ENABLED', 'false').lower() == 'true'
    if input_data.task_token and chain_enabled:
        _send_chain_signal(
            task_token=input_data.task_token,
            job_id=input_data.job_id,
            success=True,
            company_context=cr_result.model_dump(mode='json'),
        )
    else:
        _enqueue_vpr_standalone(input_data.user_id, input_data.job_id, cr_result)

    metrics.add_metric(name='CRWorkerSuccess', unit='Count', value=1)
    logger.info(
        'CR worker completed',
        user_id=input_data.user_id,
        job_id=input_data.job_id,
        confidence=cr_result.confidence_score,
        source=cr_result.source.value,
    )


def _process_record(record: dict[str, Any]) -> None:
    """Process a single SQS record.

    Idempotency key: user_id:job_id via DynamoDB PutItem condition on the
    knowledge table entry written by _persist_cr_result; a second invocation
    finds the item already present and skips cleanly after artifact_status check.
    """
    raw_body = record.get('body', '')
    if not raw_body:
        logger.warning('SQS record has no body', record_keys=list(record.keys()))
        return

    body = json.loads(raw_body)
    input_data = _hydrate_company_fields(CRWorkerInput.model_validate(body))
    idempotency_key = f'{input_data.user_id}:{input_data.job_id}'
    logger.append_keys(idempotency_key=idempotency_key)

    # Idempotency guard: if CR already completed, skip.
    try:
        app_repo = _get_app_repo()
        application = app_repo.get(application_id=input_data.job_id, user_id=input_data.user_id)
        if isinstance(application, dict):
            artifact_statuses = application.get('artifact_statuses') or {}
            cr_status = artifact_statuses.get('company_research') if isinstance(artifact_statuses, dict) else None
            # 'completed' = idempotency; 'cancelled' = a cancel landed before this
            # (re)delivery. Skip both so we don't redo research only to have the
            # confidence-gated persist rejected by the fail_if_status='cancelled' guard.
            if cr_status in ('completed', 'cancelled'):
                logger.info('CR already terminal — skipping', idempotency_key=idempotency_key, cr_status=cr_status)
                return
    except Exception as exc:
        logger.warning('Idempotency check failed; proceeding with processing', error=str(exc))

    receive_count = int(record.get('attributes', {}).get('ApproximateReceiveCount', '1'))
    asyncio.run(_async_process_record(input_data, receive_count))


@logger.inject_lambda_context(log_event=False)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Handle SQS messages from company_research_queue.

    Returns partial batch failure response so SQS retries only the failed records.
    """
    batch_item_failures: list[dict[str, str]] = []

    for record in event.get('Records', []):
        message_id: str = record.get('messageId', '')
        try:
            _process_record(record)
        except RetryableError as exc:
            logger.warning('RetryableError — returning to SQS', message_id=message_id, reason=str(exc))
            batch_item_failures.append({'itemIdentifier': message_id})
        except Exception as exc:
            logger.exception('Unexpected error processing CR record', message_id=message_id, error=str(exc))
            batch_item_failures.append({'itemIdentifier': message_id})

    return {'batchItemFailures': batch_item_failures}
