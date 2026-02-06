"""
VPR Status Handler for Async Architecture.

Endpoint: GET /api/vpr/status/{job_id}
Flow:
  1. Fetch job from DynamoDB
  2. Return status with optional result_url for completed jobs

Per docs/specs/07-vpr-async-architecture.md
"""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from typing import Any

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext

from careervp.dal.jobs_repository import JobsRepository
from careervp.handlers.utils.observability import logger, metrics, tracer

JSON_HEADERS = {'Content-Type': 'application/json'}

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
    bucket = _get_results_bucket()
    return s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket, 'Key': result_key},
        ExpiresIn=3600,
    )


def _build_processing_response(job: dict[str, Any], job_id: str) -> dict[str, Any]:
    """Build response for PROCESSING status."""
    return {
        'job_id': job_id,
        'status': 'PROCESSING',
        'created_at': job.get('created_at'),
        'started_at': job.get('started_at'),
        'message': 'VPR generation in progress',
    }


def _build_completed_response(job: dict[str, Any], job_id: str) -> dict[str, Any]:
    """Build response for COMPLETED status."""
    result_key = job.get('result_key')
    if result_key:
        result_url = _generate_presigned_url(result_key)
    else:
        result_url = job.get('result_url', '')

    response = {
        'job_id': job_id,
        'status': 'COMPLETED',
        'created_at': job.get('created_at'),
        'completed_at': job.get('completed_at'),
        'result_url': result_url,
        'vpr_version': job.get('vpr_version'),
        'word_count': job.get('word_count'),
        'message': 'VPR generation completed successfully',
    }

    if job.get('token_usage'):
        response['token_usage'] = job.get('token_usage')

    return response


def _build_failed_response(job: dict[str, Any], job_id: str) -> dict[str, Any]:
    """Build response for FAILED status."""
    return {
        'job_id': job_id,
        'status': 'FAILED',
        'created_at': job.get('created_at'),
        'error': job.get('error', 'Unknown error'),
        'message': 'VPR generation failed',
    }


def _build_pending_response(job: dict[str, Any], job_id: str) -> dict[str, Any]:
    """Build response for PENDING status."""
    return {
        'job_id': job_id,
        'status': job.get('status', 'PENDING'),
        'created_at': job.get('created_at'),
        'message': f'Job status: {job.get("status", "PENDING")}',
    }


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """
    Handle GET /api/vpr/status/{job_id} requests.

    Returns job status and presigned URL for completed jobs.

    Path Parameters:
        - job_id: The unique job identifier

    Returns:
        200 OK: Job found, returns status and result_url if completed
        400 Bad Request: Missing job_id
        404 Not Found: Job not found
        500 Internal Server Error: Infrastructure error
    """
    jobs_repo = JobsRepository()

    # Get job_id from path parameters
    path_params = event.get('pathParameters', {})
    job_id = path_params.get('job_id') if path_params else None

    if not job_id:
        return _build_error_response('Missing job_id', HTTPStatus.BAD_REQUEST)

    logger.append_keys(job_id=job_id)

    # Fetch job from DynamoDB
    job_result = jobs_repo.get_job(job_id)

    # Handle Result object or dict return
    if hasattr(job_result, 'data'):
        if not job_result.success:
            logger.error('Failed to fetch job', error=job_result.error)
            return _build_error_response(
                'Failed to fetch job status',
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
        job = job_result.data
    else:
        job = job_result

    if not job:
        return _build_error_response('Job not found', HTTPStatus.NOT_FOUND)

    status = job.get('status', 'UNKNOWN')

    # Build response based on status
    if status == 'PROCESSING':
        response_data = _build_processing_response(job, job_id)
    elif status == 'COMPLETED':
        response_data = _build_completed_response(job, job_id)
    elif status == 'FAILED':
        response_data = _build_failed_response(job, job_id)
    else:
        response_data = _build_pending_response(job, job_id)

    # Emit metrics
    _emit_status_metrics(status)

    logger.info('Status query successful', job_id=job_id, status=status)

    return {
        'statusCode': int(HTTPStatus.OK),
        'headers': JSON_HEADERS,
        'body': json.dumps(response_data),
    }


def _emit_status_metrics(status: str) -> None:
    """Emit metrics based on job status."""
    metrics.add_metric(name='VPRStatusQuery', unit='Count', value=1)
    if status == 'COMPLETED':
        metrics.add_metric(name='VPRStatusCompleted', unit='Count', value=1)
    elif status == 'FAILED':
        metrics.add_metric(name='VPRStatusFailed', unit='Count', value=1)


def _build_error_response(message: str, status: HTTPStatus) -> dict[str, Any]:
    """Construct a standardized error response."""
    return {
        'statusCode': int(status),
        'headers': JSON_HEADERS,
        'body': json.dumps(
            {
                'error': message,
                'status_code': int(status),
            }
        ),
    }
