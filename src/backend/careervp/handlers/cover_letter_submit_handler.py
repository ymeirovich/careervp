"""
Cover Letter Submit Handler for Async Architecture.

Endpoint: POST /cover-letter/generate
Flow:
  1. Validate CoverLetterRequest
  2. Create PENDING artifact record in DynamoDB
  3. Send message to SQS queue
  4. Return 202 Accepted with job_id
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

from careervp.handlers.auth_utils import extract_user_id
from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.logic.utils.constants import COVER_LETTER_JOBS_QUEUE_NAME
from careervp.models.api_models import CoverLetterRequest

JSON_HEADERS = {'Content-Type': 'application/json'}

# Module-level clients for testing/mocking
sqs = boto3.client('sqs')
dynamodb_resource = boto3.resource('dynamodb')


def _extract_authenticated_user_id(event: dict[str, Any]) -> str | None:
    return extract_user_id(event)


def _get_sqs_queue_url() -> str:
    """Resolve SQS queue URL deterministically from env or queue name lookup."""
    queue_url = os.environ.get('SQS_QUEUE_URL')
    if queue_url:
        return queue_url

    queue_name = os.environ.get('SQS_QUEUE_NAME', COVER_LETTER_JOBS_QUEUE_NAME)
    response = sqs.get_queue_url(QueueName=queue_name)
    resolved_url = response.get('QueueUrl')
    if not isinstance(resolved_url, str) or not resolved_url:
        raise RuntimeError(f'Unable to resolve SQS queue URL for queue {queue_name}')
    return resolved_url


def _get_artifacts_table_name() -> str:
    return os.environ.get('DYNAMODB_TABLE_NAME') or os.environ.get('ARTIFACTS_TABLE_NAME') or os.environ.get('TABLE_NAME', '')


@logger.inject_lambda_context(log_event=False)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """
    Handle POST /cover-letter/generate requests for async cover letter generation.

    Flow:
        1. Authenticate request
        2. Parse and validate request payload
        3. Create artifact record in DynamoDB with PENDING status
        4. Send message to SQS queue for async processing
        5. Return 202 Accepted with job_id

    Returns:
        202 Accepted: Job created successfully
        400 Bad Request: Invalid request payload
        401 Unauthorized: Missing authentication
        500 Internal Server Error: Infrastructure error
    """
    _ = context
    authenticated_user_id = _extract_authenticated_user_id(event)
    if not authenticated_user_id:
        return _build_error_response('Authentication required', HTTPStatus.UNAUTHORIZED)

    try:
        request_data = _parse_body(event)
        api_request = CoverLetterRequest.model_validate(request_data)
    except (ValueError, json.JSONDecodeError, ValidationError) as exc:
        logger.warning('Invalid request body', error=str(exc))
        return _build_error_response('Invalid request body', HTTPStatus.BAD_REQUEST)

    job_id = str(uuid.uuid4())
    now = datetime.datetime.now(datetime.timezone.utc)
    created_at = now.isoformat()

    logger.append_keys(user_id=authenticated_user_id, job_id=job_id)

    # Write PENDING artifact record to DynamoDB
    try:
        table = dynamodb_resource.Table(_get_artifacts_table_name())
        table.put_item(
            Item={
                'pk': authenticated_user_id,
                'sk': f'ARTIFACT#COVER_LETTER#{job_id}',
                'applicationId': authenticated_user_id,
                'artifactId': f'ARTIFACT#COVER_LETTER#{job_id}',
                'artifactType': 'cover_letter',
                'user_id': authenticated_user_id,
                'job_id': job_id,
                'status': 'PENDING',
                'request_data': api_request.model_dump(mode='json'),
                'created_at': created_at,
                'updated_at': created_at,
            },
        )
    except BotoClientError as exc:
        logger.error('Failed to create artifact record', job_id=job_id, error=str(exc))
        return _build_error_response('Failed to create job', HTTPStatus.INTERNAL_SERVER_ERROR)

    # Send message to SQS
    try:
        queue_url = _get_sqs_queue_url()
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(
                {
                    'job_id': job_id,
                    'user_id': authenticated_user_id,
                    'request_data': api_request.model_dump(mode='json'),
                }
            ),
            MessageAttributes={
                'job_type': {'StringValue': 'cover_letter_generation', 'DataType': 'String'},
                'job_id': {'StringValue': job_id, 'DataType': 'String'},
                'user_id': {'StringValue': authenticated_user_id, 'DataType': 'String'},
            },
        )
        logger.info('Cover letter job queued successfully', job_id=job_id, queue_url=queue_url)

    except BotoClientError as exc:
        logger.error('Failed to send message to SQS', job_id=job_id, error=str(exc))
        # Mark job as failed since we couldn't queue it
        try:
            table = dynamodb_resource.Table(_get_artifacts_table_name())
            table.update_item(
                Key={'pk': authenticated_user_id, 'sk': f'ARTIFACT#COVER_LETTER#{job_id}'},
                UpdateExpression='SET #s = :status, updated_at = :now',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={':status': 'FAILED', ':now': now.isoformat()},
            )
        except BotoClientError:
            logger.error('Failed to mark job as failed', job_id=job_id)
        return _build_error_response('Failed to queue job for processing', HTTPStatus.INTERNAL_SERVER_ERROR)

    metrics.add_metric(name='CoverLetterJobCreated', unit='Count', value=1)
    logger.info('Cover letter job created successfully', job_id=job_id)

    return {
        'statusCode': int(HTTPStatus.ACCEPTED),
        'headers': JSON_HEADERS,
        'body': json.dumps(
            {
                'request_id': job_id,
                'artifact_id': job_id,
                'status': 'processing',
                'estimated_time_seconds': 60,
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
