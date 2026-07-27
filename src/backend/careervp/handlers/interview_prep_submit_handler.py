"""
Interview Prep Submit Handler for Async Architecture.

Endpoint: POST /interview-prep/generate
Flow:
  1. Validate InterviewPrepRequest
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

from careervp.dal import table_registry
from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.handlers.artifact_dependency_utils import (
    dependency_response_body,
    mark_requested_artifact_pending,
    resolve_handler_dependencies,
)
from careervp.handlers.auth_utils import extract_user_id
from careervp.handlers.cors_utils import get_cors_headers, set_request_origin
from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.logic.utils.constants import INTERVIEW_PREP_JOBS_QUEUE_NAME
from careervp.models.api_models import InterviewPrepRequest
from careervp.models.result import ResultCode

JSON_HEADERS = {'Content-Type': 'application/json'}


def _json_headers() -> dict[str, str]:
    return {'Content-Type': 'application/json', **get_cors_headers(None)}


# Module-level clients for testing/mocking
sqs = boto3.client('sqs')
dynamodb_resource = boto3.resource('dynamodb')


def _extract_authenticated_user_id(event: dict[str, Any]) -> str | None:
    return extract_user_id(event)


def _get_sqs_queue_url() -> str:
    """Resolve SQS queue URL deterministically from env or queue name lookup."""
    queue_url = os.environ.get('SQS_QUEUE_URL')
    if isinstance(queue_url, str) and queue_url.strip():
        return queue_url.strip()

    queue_name = str(os.environ.get('SQS_QUEUE_NAME', INTERVIEW_PREP_JOBS_QUEUE_NAME)).strip()
    if not queue_name:
        raise RuntimeError('SQS queue name is required')
    response = sqs.get_queue_url(QueueName=queue_name)
    resolved_url = response.get('QueueUrl')
    if not isinstance(resolved_url, str) or not resolved_url:
        raise RuntimeError(f'Unable to resolve SQS queue URL for queue {queue_name}')
    return resolved_url


def _get_artifacts_table_name() -> str:
    return table_registry.resolve_artifacts_table_name(required=True)


@logger.inject_lambda_context(log_event=False)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """
    Handle POST /interview-prep/generate requests for async interview prep generation.

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
    set_request_origin(event)
    endpoint = str(event.get('path', ''))
    tracer.put_annotation(key='endpoint', value=endpoint)
    logger.info(
        'Interview prep submit request received',
        api_gateway_event=event,
        endpoint=endpoint,
        request_id=_get_request_id(event, context),
    )
    authenticated_user_id = _extract_authenticated_user_id(event)
    if not authenticated_user_id:
        metrics.add_metric(name='UnauthorizedError', unit='Count', value=1)
        return _build_error_response(
            'Authentication required', HTTPStatus.UNAUTHORIZED, code=ResultCode.UNAUTHORIZED, request_id=_get_request_id(event, context)
        )

    tracer.put_annotation(key='user_id', value=authenticated_user_id)

    try:
        request_data = _parse_body(event)
        logger.info('Interview prep submit parsed request body', request_body=request_data)
        api_request = InterviewPrepRequest.model_validate(request_data)
        logger.info('Interview prep submit validated request body', validated_payload=api_request.model_dump(mode='json'))
    except ValidationError as exc:
        logger.warning('Invalid request body', error=str(exc))
        metrics.add_metric(name='ValidationError', unit='Count', value=1)
        return _build_validation_error_response(exc, event, context)
    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning('Invalid request body', error=str(exc))
        metrics.add_metric(name='ValidationError', unit='Count', value=1)
        return _build_error_response(
            'Invalid request body',
            HTTPStatus.BAD_REQUEST,
            code=ResultCode.INVALID_JSON,
            request_id=_get_request_id(event, context),
            validation_errors=[{'code': ResultCode.INVALID_JSON, 'field': 'body', 'message': str(exc)}],
        )

    try:
        table_name = _get_artifacts_table_name()
    except RuntimeError:
        logger.exception('Artifacts table configuration error')
        metrics.add_metric(name='MissingEnvError', unit='Count', value=1)
        return _build_error_response(
            'Internal server error', HTTPStatus.INTERNAL_SERVER_ERROR, code=ResultCode.MISSING_ENV, request_id=_get_request_id(event, context)
        )

    application_id = api_request.application_id or api_request.job_id or api_request.vpr_id
    dependency_resolution = resolve_handler_dependencies(
        artifact_type='interview_prep',
        application_id=application_id,
        user_id=authenticated_user_id,
        dal=DynamoDalHandler(table_name),
    )
    if dependency_resolution.status != 'ready':
        if dependency_resolution.status == 'dependency_generating':
            mark_requested_artifact_pending(application_id=application_id, user_id=authenticated_user_id, artifact_type='interview_prep')
        return {
            'statusCode': dependency_resolution.http_status,
            'headers': _json_headers(),
            'body': json.dumps(dependency_response_body(dependency_resolution, requested_artifact='interview_prep')),
        }

    job_id = str(uuid.uuid4())
    artifact_id = table_registry.interview_prep_artifact_id(job_id)
    now = datetime.datetime.now(datetime.timezone.utc)
    created_at = now.isoformat()

    logger.append_keys(user_id=authenticated_user_id, job_id=job_id)
    tracer.put_annotation(key='job_id', value=job_id)

    # Write PENDING artifact record to DynamoDB
    try:
        table = dynamodb_resource.Table(table_name)
        artifact_item = {
            **table_registry.legacy_item_key(authenticated_user_id, artifact_id),
            **table_registry.canonical_item_key(authenticated_user_id, artifact_id),
            'artifactType': 'interview_prep',
            'user_id': authenticated_user_id,
            'job_id': job_id,
            'status': 'PENDING',
            'request_data': api_request.model_dump(mode='json'),
            'created_at': created_at,
            'updated_at': created_at,
        }
        logger.info('Interview prep submit writing DynamoDB artifact', table_name=table_name, dynamodb_item=artifact_item)
        table.put_item(
            Item=artifact_item,
        )
    except BotoClientError as exc:
        logger.error('Failed to create artifact record', job_id=job_id, error=str(exc))
        metrics.add_metric(name='DynamoValidationException', unit='Count', value=1)
        return _build_error_response('Failed to create job', HTTPStatus.INTERNAL_SERVER_ERROR)

    # Send message to SQS
    try:
        queue_url = _get_sqs_queue_url()
        sqs_payload = {
            'job_id': job_id,
            'user_id': authenticated_user_id,
            'request_data': api_request.model_dump(mode='json'),
        }
        sqs_attributes = {
            'job_type': {'StringValue': 'interview_prep_generation', 'DataType': 'String'},
            'job_id': {'StringValue': job_id, 'DataType': 'String'},
            'user_id': {'StringValue': authenticated_user_id, 'DataType': 'String'},
        }
        logger.info(
            'Interview prep submit sending SQS message',
            queue_url=queue_url,
            sqs_message_body=sqs_payload,
            sqs_message_attributes=sqs_attributes,
        )
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(sqs_payload),
            MessageAttributes=sqs_attributes,
        )
        logger.info('Interview prep job queued successfully', job_id=job_id, queue_url=queue_url)

    except BotoClientError as exc:
        logger.error('Failed to send message to SQS', job_id=job_id, error=str(exc))
        metrics.add_metric(name='SqsError', unit='Count', value=1)
        # Mark job as failed since we couldn't queue it
        try:
            table = dynamodb_resource.Table(_get_artifacts_table_name())
            table.update_item(
                Key={'applicationId': authenticated_user_id, 'artifactId': artifact_id},
                UpdateExpression='SET #s = :status, updated_at = :now',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={':status': 'FAILED', ':now': now.isoformat()},
            )
        except BotoClientError:
            logger.error('Failed to mark job as failed', job_id=job_id)
        return _build_error_response('Failed to queue job for processing', HTTPStatus.INTERNAL_SERVER_ERROR)

    metrics.add_metric(name='InterviewPrepJobCreated', unit='Count', value=1)
    logger.info('Interview prep job created successfully', job_id=job_id)
    response_body = {
        'request_id': job_id,
        'artifact_id': job_id,
        'status': 'processing',
        'estimated_time_seconds': 60,
    }
    logger.info('Interview prep submit response payload', response_status_code=int(HTTPStatus.ACCEPTED), response_body=response_body)

    return {
        'statusCode': int(HTTPStatus.ACCEPTED),
        'headers': _json_headers(),
        'body': json.dumps(response_body),
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


def _build_error_response(
    message: str,
    status: HTTPStatus,
    code: str | None = None,
    request_id: str | None = None,
    validation_errors: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Construct a standardized error response."""
    payload: dict[str, Any] = {
        'error': message,
        'status_code': int(status),
    }
    if code:
        payload['code'] = code
    if request_id:
        payload['request_id'] = request_id
    if validation_errors is not None:
        payload['validation_errors'] = validation_errors
    return {
        'statusCode': int(status),
        'headers': _json_headers(),
        'body': json.dumps(payload),
    }


def _validation_errors(exc: ValidationError) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for err in exc.errors():
        location = err.get('loc', ())
        field = '.'.join(str(part) for part in location) if isinstance(location, tuple) else str(location)
        errors.append(
            {
                'code': ResultCode.VALIDATION_ERROR,
                'field': field,
                'message': str(err.get('msg', 'Invalid value')),
            }
        )
    return errors


def _get_request_id(event: dict[str, Any], context: LambdaContext | None) -> str | None:
    request_context = event.get('requestContext')
    if isinstance(request_context, dict):
        request_id = request_context.get('requestId')
        if isinstance(request_id, str) and request_id:
            return request_id
    if context is not None:
        request_id = getattr(context, 'aws_request_id', None)
        if isinstance(request_id, str) and request_id:
            return request_id
    return None


def _build_validation_error_response(
    exc: ValidationError,
    event: dict[str, Any],
    context: LambdaContext,
) -> dict[str, Any]:
    return _build_error_response(
        message='Invalid request body',
        status=HTTPStatus.BAD_REQUEST,
        code=ResultCode.VALIDATION_ERROR,
        request_id=_get_request_id(event, context),
        validation_errors=_validation_errors(exc),
    )
