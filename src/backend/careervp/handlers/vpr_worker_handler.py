"""
VPR Worker Handler for Async Architecture.

SQS-triggered Lambda that processes VPR generation jobs.
Flow:
  1. Receive SQS message with job_id
  2. Fetch job from DynamoDB
  3. Update status to PROCESSING
  4. Call Claude API to generate VPR
  5. Upload VPR result to S3
  6. Update job status to COMPLETED with result_key
  7. Return result

Per docs/specs/07-vpr-async-architecture.md
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError as BotoClientError

from careervp.dal.application_repository import ApplicationRepository
from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.dal.jobs_repository import JobsRepository
from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.logic.company_research import load_confident_company_research_artifact
from careervp.logic.vpr_generator import generate_vpr
from careervp.models.job import CompanyContext, GapResponse, JobPosting
from careervp.models.result import ResultCode
from careervp.models.vpr import VPR, VPRRequest

# Module-level S3 client for testing/mocking
s3 = boto3.client('s3')
sfn = boto3.client('stepfunctions')


def _get_results_bucket() -> str:
    """Get S3 bucket name for results."""
    bucket_name = os.environ.get('VPR_RESULTS_BUCKET_NAME')
    if bucket_name:
        return bucket_name
    # Fallback to naming convention
    env = os.environ.get('ENVIRONMENT', 'dev')
    return f'careervp-{env}-vpr-results-us-east-1'


def _generate_presigned_url(result_key: str) -> str:
    """Generate presigned URL for downloading result."""
    client = boto3.client('s3')
    bucket = _get_results_bucket()
    url = client.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket, 'Key': result_key},
        ExpiresIn=604800,  # 7 days — reduces expiry-related download failures
    )
    assert isinstance(url, str), 'S3 presigned URL should return a string'
    return url


def _build_job_posting_input(
    jobs_repo: JobsRepository,
    input_data: dict[str, Any],
) -> dict[str, Any]:
    """Build VPRRequest-compatible job_posting from OpenAPI or legacy payloads."""
    raw_job_posting = input_data.get('job_posting')
    if isinstance(raw_job_posting, dict):
        company_name = raw_job_posting.get('company_name') or raw_job_posting.get('company')
        role_title = raw_job_posting.get('role_title') or raw_job_posting.get('title')
        if company_name and role_title:
            return raw_job_posting

    posting_id = str(input_data.get('application_id') or input_data.get('job_id') or '').strip()
    if not posting_id:
        return raw_job_posting if isinstance(raw_job_posting, dict) else {}

    job_record = jobs_repo.get_job(posting_id) or {}
    company_name = str(job_record.get('company_name') or job_record.get('company') or '').strip()
    role_title = str(job_record.get('title') or '').strip()

    if not company_name or not role_title:
        return raw_job_posting if isinstance(raw_job_posting, dict) else {}

    requirements: list[str] = []
    raw_requirements = job_record.get('requirements')
    if isinstance(raw_requirements, list):
        requirements = [str(item) for item in raw_requirements if str(item).strip()]

    posting: dict[str, Any] = {
        'company_name': company_name,
        'role_title': role_title,
        'description': job_record.get('description'),
        'requirements': requirements,
    }
    source_url = job_record.get('url')
    if isinstance(source_url, str) and source_url.strip():
        posting['source_url'] = source_url.strip()
    return posting


def _build_gap_responses_input(input_data: dict[str, Any]) -> list[dict[str, str]]:
    """Build GapResponse-compatible list from legacy/openapi VPR submit payloads."""
    raw_gap_responses = input_data.get('gap_responses')
    if isinstance(raw_gap_responses, list):
        normalized: list[dict[str, str]] = []
        for item in raw_gap_responses:
            if not isinstance(item, dict):
                continue
            question_id = str(item.get('question_id', '')).strip()
            question = str(item.get('question', '')).strip()
            answer = str(item.get('answer', '')).strip()
            if question_id and question and answer:
                normalized.append(
                    {
                        'question_id': question_id,
                        'question': question,
                        'answer': answer,
                    }
                )
        if normalized:
            return normalized

    return []


def _fetch_gap_responses_from_application(application_id: str, user_id: str) -> list[dict[str, str]]:
    """Fetch saved gap responses from the application record in DynamoDB.

    Gap responses are stored as {question_id, response} in the application record.
    Gap questions (with text) are stored alongside as {question_id, question}.
    We join them so the VPR generator receives full context.
    """
    app_table = os.environ.get('APPLICATIONS_TABLE_NAME') or ''
    if not app_table:
        logger.warning('APPLICATIONS_TABLE_NAME not set; skipping gap response lookup')
        return []
    try:
        app_repo = ApplicationRepository(DynamoDalHandler(app_table))
        application = app_repo.get(application_id=application_id, user_id=user_id)
        if not application:
            return []
        stored_responses: list[dict[str, Any]] = application.get('gap_responses') or []
        stored_questions: list[dict[str, Any]] = application.get('gap_questions') or []
        question_text: dict[str, str] = {
            str(q.get('question_id', '')).strip(): str(q.get('question', '')).strip() for q in stored_questions if isinstance(q, dict)
        }
        result: list[dict[str, str]] = []
        for resp in stored_responses:
            if not isinstance(resp, dict):
                continue
            qid = str(resp.get('question_id', '')).strip()
            answer = str(resp.get('response') or resp.get('answer', '')).strip()
            if qid and answer:
                result.append(
                    {
                        'question_id': qid,
                        'question': question_text.get(qid, qid),
                        'answer': answer,
                    }
                )
        return result
    except Exception as exc:
        logger.warning('Failed to fetch gap responses from application record', error=str(exc))
        return []


def _extract_message_body_from_record(record: dict[str, Any]) -> dict[str, Any] | None:
    """Extract the JSON message body from an SQS record.

    Returns None (and logs a warning) instead of raising if 'body' is absent or
    malformed, so a bad record never crashes the entire batch.
    """
    raw_body = record.get('body')
    if not raw_body:
        logger.warning('SQS record missing body field', record_keys=list(record.keys()))
        return None
    try:
        message_body = json.loads(raw_body)
    except json.JSONDecodeError:
        logger.warning('SQS record body is not valid JSON')
        return None
    if not isinstance(message_body, dict):
        logger.warning('SQS record body is not a JSON object')
        return None
    return message_body


def _extract_job_id_from_record(record: dict[str, Any]) -> str | None:
    """Extract job_id from an SQS record body."""
    message_body = _extract_message_body_from_record(record)
    if message_body is None:
        return None
    return message_body.get('job_id') or None


def _send_task_success(task_token: str | None, *, job_id: str, vpr_id: str) -> None:
    """Signal Step Functions success when this SQS record came from WAIT_FOR_TASK_TOKEN."""
    if not task_token:
        return
    sfn.send_task_success(
        taskToken=task_token,
        output=json.dumps({'job_id': job_id, 'vpr_id': vpr_id}),
    )


def _send_task_failure(task_token: str | None, *, cause: str) -> None:
    """Signal Step Functions failure when this SQS record came from WAIT_FOR_TASK_TOKEN."""
    if not task_token:
        return
    sfn.send_task_failure(
        taskToken=task_token,
        error='VPRFailed',
        cause=cause,
    )


def _resolve_gap_responses(input_data: dict[str, Any], application_id: str, user_id: str) -> list[GapResponse]:
    """Return real GapResponse objects for the VPR request.

    Tries input_data first (legacy full-object path), then falls back to
    fetching saved responses from the application record in DynamoDB.
    """
    items = _build_gap_responses_input(input_data)
    if not items:
        items = _fetch_gap_responses_from_application(application_id, user_id)
    return [GapResponse.model_validate(item) for item in items]


def _coerce_optional_str(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _resolve_company_context(
    input_data: dict[str, Any],
    application_id: str,
    user_id: str,
) -> tuple[CompanyContext | None, str | None, str | None]:
    """Resolve CompanyContext from message/job input, with a CR DAL fallback."""
    company_research_id = _coerce_optional_str(input_data.get('company_research_id'))
    company_research_at = _coerce_optional_str(input_data.get('company_research_at'))
    raw_context = input_data.get('company_context')

    if raw_context is None:
        artifact = load_confident_company_research_artifact(application_id=application_id, user_id=user_id)
        if artifact is not None:
            raw_context = artifact.company_context.model_dump(mode='json')
            input_data['company_context'] = raw_context
            company_research_id = artifact.company_research_id
            company_research_at = artifact.company_research_at
            input_data['company_research_id'] = company_research_id
            input_data['company_research_at'] = company_research_at
        else:
            logger.warning(
                'VPR company_context missing after fallback load',
                application_id=application_id,
                user_id=user_id,
                company_context_missing=True,
            )

    if raw_context is None:
        return None, company_research_id, company_research_at
    return CompanyContext.model_validate(raw_context), company_research_id, company_research_at


def _build_vpr_result_json(vpr: VPR, provenance: dict[str, Any]) -> str:
    """Serialize the VPR result with observable CR provenance fields."""
    payload = json.loads(vpr.model_dump_json(by_alias=True))
    if not isinstance(payload, dict):
        payload = {}
    payload.update(provenance)
    return json.dumps(payload, default=str)


def _process_job_record(
    jobs_repo: JobsRepository,
    record: dict[str, Any],
    bucket: str,
) -> None:
    """Process a single SQS record."""
    message_body = _extract_message_body_from_record(record)
    if message_body is None:
        logger.warning('Skipping record: no message body extracted')
        return

    job_id = message_body.get('job_id') or None
    task_token = str(message_body.get('task_token') or '').strip() or None

    if not job_id:
        logger.warning('Skipping record: no job_id extracted')
        return

    logger.append_keys(job_id=job_id)
    logger.info('Processing VPR job', job_id=job_id)

    # Fetch job from DynamoDB
    job_result = jobs_repo.get_job(job_id)

    # Repository returns dict or None
    if job_result is None:
        create_result = jobs_repo.create_job(_build_job_record_from_message(message_body))
        if not create_result.success or not create_result.data:
            error_msg = create_result.error or 'Job not found'
            logger.error('Job not found and could not be created', job_id=job_id, error=error_msg)
            _send_task_failure(task_token, cause=error_msg)
            return
        job_result = create_result.data

    job = job_result
    status = job.get('status')

    if status == 'COMPLETED':
        logger.info('Job already completed, skipping', job_id=job_id)
        return

    if status == 'FAILED':
        logger.info('Job previously failed, skipping', job_id=job_id)
        return

    # A job cancelled before this (re)delivery must NOT be resurrected. Without this
    # skip the claim write below uses expected_current_status='CANCELLED' (echoing the
    # value just read), so the conditional write would succeed and flip CANCELLED ->
    # PROCESSING, then complete the artifact the user already cancelled (FE-UI-043).
    if status == 'CANCELLED':
        logger.info('Job was cancelled, skipping', job_id=job_id)
        return

    job = _merge_message_context_into_job(job, message_body)
    _execute_job(jobs_repo, job, job_id, bucket, task_token)


def _build_job_record_from_message(message_body: dict[str, Any]) -> dict[str, Any]:
    """Build a minimal VPR job record for artifact-chain messages."""
    job_id = str(message_body.get('job_id') or '').strip()
    user_id = str(message_body.get('user_id') or '').strip()
    application_id = str(message_body.get('application_id') or job_id).strip()
    input_data = {key: value for key, value in message_body.items() if key not in {'task_token'}}
    return {
        'job_id': job_id,
        'user_id': user_id,
        'application_id': application_id,
        'input_data': input_data,
        'status': 'PENDING',
    }


def _merge_message_context_into_job(job: dict[str, Any], message_body: dict[str, Any]) -> dict[str, Any]:
    """Return a job record with artifact-chain message fields available as input_data."""
    merged_job = dict(job)
    existing_input = merged_job.get('input_data')
    input_data = dict(existing_input) if isinstance(existing_input, dict) else {}
    for key, value in message_body.items():
        if key != 'task_token':
            input_data.setdefault(key, value)
    merged_job['input_data'] = input_data
    merged_job.setdefault('user_id', str(message_body.get('user_id') or ''))
    merged_job.setdefault('application_id', str(message_body.get('application_id') or message_body.get('job_id') or ''))
    return merged_job


def _execute_job(  # noqa: C901
    jobs_repo: JobsRepository,
    job: dict[str, Any],
    job_id: str,
    bucket: str,
    task_token: str | None = None,
) -> None:
    """Execute the VPR generation job."""
    # Update status to PROCESSING
    now = datetime.now(timezone.utc).isoformat()
    expected_current_status = str(job.get('status') or 'PENDING')
    processing_update = jobs_repo.update_job_status(
        job_id=job_id,
        status='PROCESSING',
        expected_current_status=expected_current_status,
        started_at=now,
    )
    if not processing_update.success:
        logger.info(
            'Skipping job: failed atomic transition to PROCESSING',
            job_id=job_id,
            expected_current_status=expected_current_status,
        )
        return

    # Get CV for this user
    user_id = str(job.get('user_id', ''))
    input_data_raw = job.get('input_data', {})
    input_data: dict[str, Any] = input_data_raw if isinstance(input_data_raw, dict) else {}
    application_id = str(job.get('application_id', ''))

    # Fetch CV from DynamoDB
    cv_table = os.environ.get('DYNAMODB_TABLE_NAME', 'careervp-users-dev')
    cv_dal = DynamoDalHandler(cv_table)
    user_cv = cv_dal.get_cv(user_id)

    if not user_cv:
        error_msg = 'User CV not found'
        jobs_repo.update_job_status(
            job_id=job_id,
            status='FAILED',
            error=error_msg,
        )
        logger.error('User CV not found', user_id=user_id)
        _send_task_failure(task_token, cause=error_msg)
        return

    # Generate VPR
    try:
        job_posting = JobPosting.model_validate(_build_job_posting_input(jobs_repo, input_data))
        gap_responses = _resolve_gap_responses(input_data, application_id, user_id)
        company_context, company_research_id, company_research_at = _resolve_company_context(input_data, application_id, user_id)
        vpr_request = VPRRequest(
            application_id=application_id,
            user_id=user_id,
            job_posting=job_posting,
            gap_responses=gap_responses,
            company_context=company_context,
        )
    except Exception as e:
        error_msg = f'Invalid VPR request payload: {str(e)}'
        jobs_repo.update_job_status(
            job_id=job_id,
            status='FAILED',
            error=error_msg,
        )
        logger.exception('Failed to build VPR request', job_id=job_id, error=str(e))
        _send_task_failure(task_token, cause=error_msg)
        return

    next_version = cv_dal.get_next_vpr_version(vpr_request.application_id)
    vpr_request = vpr_request.model_copy(update={'target_version': next_version})
    result = generate_vpr(vpr_request, user_cv, cv_dal)

    if not result.success or not result.data:
        error_msg = result.error or 'VPR generation failed'
        jobs_repo.update_job_status(
            job_id=job_id,
            status='FAILED',
            error=error_msg,
        )
        logger.error('VPR generation failed', job_id=job_id, error=result.error)
        _send_task_failure(task_token, cause=error_msg)
        return

    vpr_response = result.data
    vpr: VPR = vpr_response.vpr  # type: ignore[assignment]
    company_context_included = vpr_request.company_context is not None and vpr.company_insights is not None
    if vpr_request.company_context is not None and vpr.company_insights is None:
        logger.warning(
            'VPR generated without company_insights despite company_context',
            job_id=job_id,
            application_id=application_id,
            company_research_id=company_research_id,
            company_context_included=False,
        )
    provenance: dict[str, Any] = {
        'company_research_id': company_research_id,
        'company_research_at': company_research_at,
        'company_context_included': company_context_included,
    }

    # Upload result to S3
    result_key = f'results/{job_id}.json'
    try:
        s3.put_object(
            Bucket=bucket,
            Key=result_key,
            Body=_build_vpr_result_json(vpr, provenance),
            ContentType='application/json',
        )
        logger.info('Uploaded VPR to S3', job_id=job_id, bucket=bucket, key=result_key)

    except BotoClientError as e:
        error_msg = f'S3 upload failed: {str(e)}'
        jobs_repo.update_job_status(
            job_id=job_id,
            status='FAILED',
            error=error_msg,
        )
        logger.error('S3 upload failed', job_id=job_id, error=str(e))
        _send_task_failure(task_token, cause=error_msg)
        return

    # Update job to COMPLETED — CANCELLED guard (FE-UI-043 § worker_cancelled_guard).
    # A concurrent cancel may have set status=CANCELLED while generation was running.
    # update_job_status applies an atomic ConditionExpression (status == PROCESSING);
    # if a cancel moved the job off PROCESSING the conditional write fails. On that
    # failure we delete the partial S3 result we just uploaded, signal task_failure,
    # and return cleanly (no DLQ).
    completed_at = datetime.now(timezone.utc).isoformat()
    result_url = _generate_presigned_url(result_key)
    one_year_ttl = int(datetime.now(timezone.utc).timestamp() + 365 * 24 * 3600)

    completed_result = jobs_repo.update_job_status(
        job_id=job_id,
        status='COMPLETED',
        expected_current_status='PROCESSING',
        completed_at=completed_at,
        result_key=result_key,
        result_url=result_url,
        vpr_version=vpr.version,
        word_count=vpr.word_count,
        ttl=one_year_ttl,
        **provenance,
    )
    if not completed_result.success:
        if completed_result.code == ResultCode.DYNAMODB_CONDITION_CHECK_FAILED:
            logger.info(
                'VPR job cancelled before COMPLETED write — aborting cleanly',
                job_id=job_id,
                cancelled_before_persist=True,
            )
            try:
                s3.delete_object(Bucket=bucket, Key=result_key)
            except Exception:
                pass
            _send_task_failure(task_token, cause='Job was cancelled before COMPLETED write')
            return
        # Genuine DynamoDB failure — surface it so the message retries / DLQs.
        error_msg = completed_result.error or 'Failed to persist COMPLETED status'
        logger.error('Failed to write VPR COMPLETED status', job_id=job_id, error=error_msg)
        _send_task_failure(task_token, cause=error_msg)
        raise RuntimeError(error_msg)

    # Propagate completion to the application record so the hub reflects the
    # artifact status and artifact_id across page reloads.
    application_id_str = str(job.get('application_id', '')).strip()
    if application_id_str and user_id:
        app_table = os.environ.get('APPLICATIONS_TABLE_NAME') or os.environ.get('DYNAMODB_TABLE_NAME') or ''
        if app_table:
            try:
                app_repo = ApplicationRepository(DynamoDalHandler(app_table))
                app_repo.update_artifact_with_id(
                    application_id=application_id_str,
                    user_id=user_id,
                    artifact_type='vpr',
                    status='completed',
                    artifact_id=job_id,
                )
                app_repo.update_chain_execution_status(
                    application_id=application_id_str,
                    user_id=user_id,
                    status='SUCCEEDED',
                )
            except Exception as e:
                logger.warning(
                    'Could not update application artifact_statuses for VPR',
                    job_id=job_id,
                    application_id=application_id_str,
                    error=str(e),
                )

    # Emit metrics
    metrics.add_metric(name='VPRJobCompleted', unit='Count', value=1)
    if vpr_response.token_usage:
        metrics.add_metric(
            name='VPRInputTokens',
            unit='Count',
            value=vpr_response.token_usage.input_tokens,
        )
        metrics.add_metric(
            name='VPROutputTokens',
            unit='Count',
            value=vpr_response.token_usage.output_tokens,
        )

    logger.info(
        'VPR job completed successfully',
        job_id=job_id,
        version=vpr.version,
        word_count=vpr.word_count,
    )
    _send_task_success(task_token, job_id=job_id, vpr_id=job_id)


@logger.inject_lambda_context(log_event=False)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """
    Handle SQS messages for VPR async processing.

    Args:
        event: SQS event containing job messages
        context: Lambda context

    Returns:
        dict with processing results

    Example SQS message:
        {
            "job_id": "550e8400-e29b-41d4-a716-446655440000",
            "user_id": "user_123",
            "application_id": "app_456"
        }
    """
    jobs_repo = JobsRepository()
    bucket = _get_results_bucket()

    # Process each record in the SQS event
    for record in event.get('Records', []):
        try:
            _process_job_record(jobs_repo, record, bucket)

        except Exception as e:
            logger.exception(
                'Unexpected error processing job',
                error=str(e),
            )

    return {'statusCode': 200, 'body': json.dumps({'message': 'Jobs processed'})}
