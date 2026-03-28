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
from careervp.logic.vpr_generator import generate_vpr
from careervp.models.job import GapResponse, JobPosting
from careervp.models.vpr import VPR, VPRRequest

# Module-level S3 client for testing/mocking
s3 = boto3.client('s3')


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

    job_id = str(input_data.get('job_id', '')).strip()
    if not job_id:
        return raw_job_posting if isinstance(raw_job_posting, dict) else {}

    job_record = jobs_repo.get_job(job_id) or {}
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

    raw_gap_response_ids = input_data.get('gap_response_ids')
    if not isinstance(raw_gap_response_ids, list):
        return []

    fallback: list[dict[str, str]] = []
    for idx, response_id in enumerate(raw_gap_response_ids):
        response_id_str = str(response_id).strip()
        if not response_id_str:
            continue
        fallback.append(
            {
                'question_id': response_id_str,
                'question': f'gap_response_{idx + 1}',
                'answer': 'Provided via gap_response_ids in async submit payload.',
            }
        )
    return fallback


def _process_job_record(
    jobs_repo: JobsRepository,
    record: dict[str, Any],
    bucket: str,
) -> None:
    """Process a single SQS record."""
    message_body = json.loads(record['body'])
    job_id = message_body.get('job_id')

    if not job_id:
        logger.warning('SQS message missing job_id', raw_message=record['body'])
        return

    logger.append_keys(job_id=job_id)
    logger.info('Processing VPR job', job_id=job_id)

    # Fetch job from DynamoDB
    job_result = jobs_repo.get_job(job_id)

    # Repository returns dict or None
    if job_result is None:
        logger.error('Job not found', job_id=job_id)
        return

    job = job_result
    status = job.get('status')

    if status == 'COMPLETED':
        logger.info('Job already completed, skipping', job_id=job_id)
        return

    if status == 'FAILED':
        logger.info('Job previously failed, skipping', job_id=job_id)
        return

    _execute_job(jobs_repo, job, job_id, bucket)


def _execute_job(
    jobs_repo: JobsRepository,
    job: dict[str, Any],
    job_id: str,
    bucket: str,
) -> None:
    """Execute the VPR generation job."""
    # Update status to PROCESSING
    now = datetime.now(timezone.utc).isoformat()
    processing_update = jobs_repo.update_job_status(
        job_id=job_id,
        status='PROCESSING',
        expected_current_status='PENDING',
        started_at=now,
    )
    if not processing_update.success:
        logger.info(
            'Skipping job: failed atomic transition to PROCESSING',
            job_id=job_id,
            expected_current_status='PENDING',
        )
        return

    # Get CV for this user
    user_id: str = job.get('user_id', '')
    input_data = job.get('input_data', {})

    # Fetch CV from DynamoDB
    cv_table = os.environ.get('DYNAMODB_TABLE_NAME', 'careervp-users-dev')
    cv_dal = DynamoDalHandler(cv_table)
    user_cv = cv_dal.get_cv(user_id)

    if not user_cv:
        jobs_repo.update_job_status(
            job_id=job_id,
            status='FAILED',
            error='User CV not found',
        )
        logger.error('User CV not found', user_id=user_id)
        return

    # Generate VPR
    try:
        job_posting = JobPosting.model_validate(_build_job_posting_input(jobs_repo, input_data))
        gap_responses = [GapResponse.model_validate(item) for item in _build_gap_responses_input(input_data)]
        vpr_request = VPRRequest(
            application_id=job.get('application_id', ''),
            user_id=user_id,
            job_posting=job_posting,
            gap_responses=gap_responses,
            company_context=input_data.get('company_context'),
        )
    except Exception as e:
        jobs_repo.update_job_status(
            job_id=job_id,
            status='FAILED',
            error=f'Invalid VPR request payload: {str(e)}',
        )
        logger.exception('Failed to build VPR request', job_id=job_id, error=str(e))
        return

    result = generate_vpr(vpr_request, user_cv, cv_dal)

    if not result.success or not result.data:
        jobs_repo.update_job_status(
            job_id=job_id,
            status='FAILED',
            error=result.error or 'VPR generation failed',
        )
        logger.error('VPR generation failed', job_id=job_id, error=result.error)
        return

    vpr_response = result.data
    vpr: VPR = vpr_response.vpr  # type: ignore[assignment]

    # Upload result to S3
    result_key = f'results/{job_id}.json'
    try:
        s3.put_object(
            Bucket=bucket,
            Key=result_key,
            Body=vpr.model_dump_json(),
            ContentType='application/json',
        )
        logger.info('Uploaded VPR to S3', job_id=job_id, bucket=bucket, key=result_key)

    except BotoClientError as e:
        jobs_repo.update_job_status(
            job_id=job_id,
            status='FAILED',
            error=f'S3 upload failed: {str(e)}',
        )
        logger.error('S3 upload failed', job_id=job_id, error=str(e))
        return

    # Update job to COMPLETED
    completed_at = datetime.now(timezone.utc).isoformat()
    result_url = _generate_presigned_url(result_key)

    jobs_repo.update_job(
        job_id=job_id,
        updates={
            'status': 'COMPLETED',
            'completed_at': completed_at,
            'result_key': result_key,
            'result_url': result_url,
            'vpr_version': vpr.version,
            'word_count': vpr.word_count,
        },
    )

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
