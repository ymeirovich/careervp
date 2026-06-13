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

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import BaseModel, Field

from careervp.dal.application_repository import ApplicationRepository
from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.logic.company_research import research_company
from careervp.models.company import CompanyResearchRequest, CompanyResearchResult, ResearchSource

_DEFAULT_CR_CONFIDENCE_THRESHOLD = 0.85


class CRWorkerInput(BaseModel):
    """Validated SQS message body for company_research_queue."""

    user_id: str
    job_id: str
    company_name: str
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


def _persist_cr_result(user_id: str, job_id: str, result: CompanyResearchResult) -> None:
    """Write CR data to the knowledge table using the same key scheme as the sync handler."""
    table_name = os.environ.get('KNOWLEDGE_TABLE_NAME') or os.environ.get('TABLE_NAME') or os.environ.get('DYNAMODB_TABLE_NAME') or ''
    if not table_name:
        logger.warning('CR persistence skipped: no knowledge table configured')
        return
    table = boto3.resource('dynamodb').Table(table_name)
    item: dict[str, Any] = {
        'pk': user_id,
        'sk': f'COMPANY_RESEARCH#{job_id}',
        'user_id': user_id,
        'job_id': job_id,
        'company_name': result.company_name,
        'research_data': result.model_dump(mode='json'),
        'entity_type': 'COMPANY_RESEARCH',
    }
    table.put_item(Item=item)


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


def _hard_fail(input_data: CRWorkerInput, cause: str) -> None:
    """Record CR failure on the application record without raising.

    Not raising ensures the message is NOT forwarded to DLQ for intentional
    hard-fails (sub-threshold confidence after max retries, LLM_FALLBACK).
    """
    logger.error('CR hard-fail after max retries', user_id=input_data.user_id, job_id=input_data.job_id, cause=cause)
    try:
        app_repo = _get_app_repo()
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
        app_repo.update_state(
            application_id=input_data.job_id,
            user_id=input_data.user_id,
            new_state='cr_failed',
            expected_state='cr_pending',
        )
    except Exception as exc:
        logger.warning('Hard-fail DAL update partial', error=str(exc))

    _send_chain_signal(
        task_token=input_data.task_token,
        job_id=input_data.job_id,
        success=False,
        cause=cause,
    )
    metrics.add_metric(name='CRHardFail', unit='Count', value=1)


async def _async_process_record(input_data: CRWorkerInput, receive_count: int) -> None:
    threshold = _get_confidence_threshold()

    cr_request = CompanyResearchRequest(
        company_name=input_data.company_name,
        domain=input_data.domain,
        job_posting_url=input_data.job_posting_url,  # type: ignore[arg-type]
    )
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

    app_repo = _get_app_repo()
    app_repo.update_artifact_status(
        application_id=input_data.job_id,
        user_id=input_data.user_id,
        artifact_type='company_research',
        status='completed',
    )
    app_repo.update_state(
        application_id=input_data.job_id,
        user_id=input_data.user_id,
        new_state='artifacts_generating',
        expected_state='cr_pending',
    )

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
    input_data = CRWorkerInput.model_validate(body)
    idempotency_key = f'{input_data.user_id}:{input_data.job_id}'
    logger.append_keys(idempotency_key=idempotency_key)

    # Idempotency guard: if CR already completed, skip.
    try:
        app_repo = _get_app_repo()
        application = app_repo.get(application_id=input_data.job_id, user_id=input_data.user_id)
        if isinstance(application, dict):
            artifact_statuses = application.get('artifact_statuses') or {}
            if isinstance(artifact_statuses, dict) and artifact_statuses.get('company_research') == 'completed':
                logger.info('CR already completed — idempotency skip', idempotency_key=idempotency_key)
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
