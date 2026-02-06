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

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.dal.jobs_repository import JobsRepository
from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.logic.vpr_generator import generate_vpr
from careervp.models.vpr import VPRRequest

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
    s3 = boto3.client('s3')
    bucket = _get_results_bucket()
    return s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket, 'Key': result_key},
        ExpiresIn=3600,
    )


@logger.inject_lambda_context(log_event=True)
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
            message_body = json.loads(record['body'])
            job_id = message_body.get('job_id')

            if not job_id:
                logger.warning('SQS message missing job_id', raw_message=record['body'])
                continue

            logger.append_keys(job_id=job_id)
            logger.info('Processing VPR job', job_id=job_id)

            # Fetch job from DynamoDB
            job_result = jobs_repo.get_job(job_id)

            # Handle Result object or dict return
            if hasattr(job_result, 'data'):
                # Result object
                if not job_result.success or not job_result.data:
                    logger.error('Job not found', job_id=job_id)
                    continue
                job = job_result.data
            else:
                # Direct dict return
                job = job_result
                if not job:
                    logger.error('Job not found', job_id=job_id)
                    continue

            status = job.get('status')

            if status == 'COMPLETED':
                logger.info('Job already completed, skipping', job_id=job_id)
                continue

            if status == 'FAILED':
                logger.info('Job previously failed, skipping', job_id=job_id)
                continue

            # Update status to PROCESSING
            now = datetime.now(timezone.utc).isoformat()
            jobs_repo.update_job_status(
                job_id=job_id,
                status='PROCESSING',
                started_at=now,
            )

            # Get CV for this user
            user_id = job.get('user_id')
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
                continue

            # Build VPR request from job data
            vpr_request = VPRRequest(
                application_id=job.get('application_id', ''),
                user_id=user_id,
                job_posting=input_data.get('job_posting', {}),
                gap_responses=input_data.get('gap_responses', []),
                company_context=input_data.get('company_context'),
            )

            # Generate VPR
            result = generate_vpr(vpr_request, user_cv, cv_dal)

            if not result.success or not result.data:
                jobs_repo.update_job_status(
                    job_id=job_id,
                    status='FAILED',
                    error=result.error or 'VPR generation failed',
                )
                logger.error('VPR generation failed', job_id=job_id, error=result.error)
                continue

            vpr = result.data

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
                continue

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

            # Emit metrics
            metrics.add_metric(name='VPRJobCompleted', unit='Count', value=1)
            if result.token_usage:
                metrics.add_metric(
                    name='VPRInputTokens',
                    unit='Count',
                    value=result.token_usage.input_tokens,
                )
                metrics.add_metric(
                    name='VPROutputTokens',
                    unit='Count',
                    value=result.token_usage.output_tokens,
                )

            logger.info(
                'VPR job completed successfully',
                job_id=job_id,
                version=vpr.version,
                word_count=vpr.word_count,
            )

        except Exception as e:
            logger.exception(
                'Unexpected error processing job',
                job_id=job_id if 'job_id' in locals() else 'unknown',
                error=str(e),
            )
            if 'job_id' in locals():
                try:
                    jobs_repo.update_job_status(
                        job_id=job_id,
                        status='FAILED',
                        error=f'Unexpected error: {str(e)}',
                    )
                except Exception:
                    pass  # Best effort

    return {'statusCode': 200, 'body': json.dumps({'message': 'Jobs processed'})}
