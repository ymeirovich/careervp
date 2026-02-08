"""
VPR Submit Handler for Async Architecture.

Endpoint: POST /api/vpr
Flow:
  1. Validate VPR request
  2. Check idempotency (duplicate detection)
  3. Create job record in DynamoDB
  4. Send message to SQS queue
  5. Return 202 Accepted with job_id

Per docs/specs/07-vpr-async-architecture.md
"""

from __future__ import annotations

import datetime
import json
import os
import uuid
from http import HTTPStatus
from typing import Any

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError as BotoClientError
from pydantic import ValidationError

from careervp.dal.jobs_repository import JobsRepository
from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.logic.utils.constants import VPR_JOBS_QUEUE_NAME
from careervp.models.vpr import VPRRequest

JSON_HEADERS = {'Content-Type': 'application/json'}

# Module-level SQS client for testing/mocking
sqs = boto3.client('sqs')


def _get_sqs_queue_url() -> str:
    """Get SQS queue URL from environment or construct from name."""
    queue_name = os.environ.get('SQS_QUEUE_NAME', VPR_JOBS_QUEUE_NAME)
    queue_url = os.environ.get('SQS_QUEUE_URL')

    if queue_url:
        return queue_url

    # Construct URL from name
    region = os.environ.get('AWS_REGION', 'us-east-1')
    account_id = os.environ.get('AWS_ACCOUNT_ID', '000000000000')
    return f'https://sqs.{region}.amazonaws.com/{account_id}/{queue_name}'


def _build_idempotency_key(request: VPRRequest) -> str:
    """Build idempotency key from request."""
    return f'vpr#{request.user_id}#{request.application_id}'


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """
    Handle POST /api/vpr requests for async VPR generation.

    Flow:
        1. Parse and validate VPRRequest
        2. Check idempotency (return existing job_id if duplicate)
        3. Create job record in DynamoDB with PENDING status
        4. Send message to SQS queue for async processing
        5. Return 202 Accepted with job_id

    Returns:
        202 Accepted: Job created successfully
        200 OK: Idempotent duplicate request
        400 Bad Request: Invalid request payload
        500 Internal Server Error: Infrastructure error
    """
    jobs_repo = JobsRepository()

    try:
        # Parse request body
        request_body = _parse_body(event)
        request_model = VPRRequest.model_validate(request_body)

    except (ValueError, json.JSONDecodeError, ValidationError) as exc:
        logger.warning('Invalid request body', error=str(exc))
        return _build_error_response('Invalid request body', HTTPStatus.BAD_REQUEST)

    logger.append_keys(
        user_id=request_model.user_id,
        application_id=request_model.application_id,
    )

    # Check idempotency
    idempotency_key = _build_idempotency_key(request_model)
    existing_job = jobs_repo.get_job_by_idempotency_key(idempotency_key)

    if existing_job:
        # Duplicate request - return existing job_id
        logger.info(
            'Idempotent duplicate request',
            job_id=existing_job.get('job_id'),
            idempotency_key=idempotency_key,
        )

        return {
            'statusCode': int(HTTPStatus.OK),
            'headers': JSON_HEADERS,
            'body': json.dumps(
                {
                    'job_id': existing_job.get('job_id'),
                    'status': existing_job.get('status'),
                    'message': 'VPR generation already exists with this idempotency key.',
                }
            ),
        }

    # Generate new job_id
    job_id = str(uuid.uuid4())

    # Use the original request body as input_data for exact match with test expectations
    input_data = request_body  # Store original request body for test compatibility

    # Create job record - pass as single dict for test compatibility
    # Calculate TTL timestamp (24 hours from now)
    now = datetime.datetime.now(datetime.timezone.utc)
    ttl_timestamp = int((now.timestamp() + 24 * 3600))
    created_at = now.isoformat()

    job_record = {
        'job_id': job_id,
        'user_id': request_model.user_id,
        'application_id': request_model.application_id,
        'input_data': input_data,
        'idempotency_key': idempotency_key,
        'status': 'PENDING',  # Included for test compatibility
        'ttl': ttl_timestamp,  # Included for test compatibility
        'created_at': created_at,  # Included for test compatibility
    }
    create_result = jobs_repo.create_job(job_record)

    if not create_result:
        logger.error('Failed to create job record', error=create_result.error if hasattr(create_result, 'error') else 'Unknown error')
        return _build_error_response(
            'Failed to create job',
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    # Send message to SQS
    try:
        queue_url = _get_sqs_queue_url()
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(
                {
                    'job_id': job_id,
                    'user_id': request_model.user_id,
                    'application_id': request_model.application_id,
                }
            ),
            MessageAttributes={
                'job_type': {'StringValue': 'vpr_generation', 'DataType': 'String'},
                'job_id': {'StringValue': job_id, 'DataType': 'String'},
                'user_id': {'StringValue': request_model.user_id, 'DataType': 'String'},
            },
        )
        logger.info('Job queued successfully', job_id=job_id, queue_url=queue_url)

    except BotoClientError as e:
        logger.error(
            'Failed to send message to SQS',
            job_id=job_id,
            error=str(e),
        )
        # Mark job as failed since we couldn't queue it
        jobs_repo.update_job_status(
            job_id=job_id,
            status='FAILED',
            error='Failed to queue for processing',
        )
        return _build_error_response(
            'Failed to queue job for processing',
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    # Emit metrics
    metrics.add_metric(name='VPRJobCreated', unit='Count', value=1)

    logger.info('VPR job created successfully', job_id=job_id)

    return {
        'statusCode': int(HTTPStatus.ACCEPTED),
        'headers': JSON_HEADERS,
        'body': json.dumps(
            {
                'job_id': job_id,
                'status': 'PENDING',
                'message': 'VPR generation submitted successfully. Poll /api/vpr/status/{job_id} for completion.',
            }
        ),
    }


def _parse_body(event: dict[str, Any]) -> dict[str, Any]:
    """Parse the API Gateway event body into a dictionary."""
    body = event.get('body')
    if body is None:
        raise ValueError('Request body is required.')

    if isinstance(body, dict):
        return body

    if isinstance(body, (bytes, bytearray)):
        decoded = body.decode('utf-8')
        parsed = json.loads(decoded)
    elif isinstance(body, str):
        parsed = json.loads(body)
    else:
        raise ValueError('Unsupported body type.')

    if not isinstance(parsed, dict):
        raise ValueError('Request body must be a JSON object.')
    return parsed


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
