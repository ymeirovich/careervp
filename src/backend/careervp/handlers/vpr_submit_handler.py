"""
VPR Submit Handler for Async Architecture.

Endpoint: POST /vpr/generate
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
from datetime import timezone
from http import HTTPStatus
from typing import Any

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError as BotoClientError
from pydantic import ValidationError

from careervp.dal.jobs_repository import JobsRepository
from careervp.handlers.auth_utils import extract_user_id
from careervp.handlers.cors_utils import get_cors_headers, set_request_origin
from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.logic.utils.constants import VPR_JOBS_QUEUE_NAME
from careervp.models.api_models import VPRGenerateRequest
from careervp.models.result import ResultCode
from careervp.models.vpr import VPRRequest


def _json_headers() -> dict[str, str]:
    return {'Content-Type': 'application/json', **get_cors_headers(None)}


# Module-level SQS client for testing/mocking
sqs = boto3.client('sqs')
# Module-level S3 client used to detect completed jobs whose result file has been
# deleted by the S3 lifecycle policy (the "expired" state the user cannot escape).
s3 = boto3.client('s3')


def _get_results_bucket() -> str:
    """Resolve the VPR results S3 bucket (mirrors vpr_status_handler)."""
    bucket_name = os.environ.get('VPR_RESULTS_BUCKET_NAME')
    if bucket_name:
        return bucket_name
    env = os.environ.get('ENVIRONMENT', 'dev')
    return f'careervp-{env}-vpr-results-us-east-1'


def _completed_result_missing(job: dict[str, Any]) -> bool:
    """Return True when a completed job's S3 result object no longer exists.

    The S3 lifecycle policy deletes result files after their retention window, which
    leaves DynamoDB reporting ``completed`` while the status endpoint reports
    ``expired``. Such a job MUST be regenerable, so the idempotency check has to fall
    through and create a fresh job. A missing ``result_key`` (older records) is also
    treated as missing so the user is never stuck.
    """
    result_key = str(job.get('result_key') or '').strip()
    if not result_key:
        return True
    try:
        s3.head_object(Bucket=_get_results_bucket(), Key=result_key)
        return False
    except Exception:
        return True


def _extract_authenticated_user_id(event: dict[str, Any]) -> str | None:
    return extract_user_id(event)


def _get_sqs_queue_url() -> str:
    """Resolve SQS queue URL deterministically from env or queue name lookup."""
    queue_url = os.environ.get('SQS_QUEUE_URL')
    if queue_url:
        return queue_url

    queue_name = os.environ.get('SQS_QUEUE_NAME', VPR_JOBS_QUEUE_NAME)
    response = sqs.get_queue_url(QueueName=queue_name)
    resolved_url = response.get('QueueUrl')
    if not isinstance(resolved_url, str) or not resolved_url:
        raise RuntimeError(f'Unable to resolve SQS queue URL for queue {queue_name}')
    return resolved_url


def _build_idempotency_key(user_id: str, application_id: str) -> str:
    """Build idempotency key from request."""
    return f'vpr#{user_id}#{application_id}'


def _normalize_submit_request(request_data: dict[str, Any], user_id: str) -> dict[str, Any]:
    """
    Normalize request data into internal submit shape.

    Supports:
    - OpenAPI request: {cv_id, job_id, gap_response_ids, options}
    - Legacy request: VPRRequest schema
    """
    if {'cv_id', 'job_id', 'gap_response_ids'}.issubset(request_data):
        openapi_request = VPRGenerateRequest.model_validate(request_data)
        options = openapi_request.options.model_dump(mode='json', exclude_none=True) if openapi_request.options else {}
        application_id = openapi_request.application_id or openapi_request.job_id
        return {
            'application_id': application_id,
            'user_id': user_id,
            'force': openapi_request.force,
            'input_data': {
                'cv_id': openapi_request.cv_id,
                'job_id': openapi_request.job_id,
                'application_id': application_id,
                'gap_response_ids': openapi_request.gap_response_ids,
                'options': options,
            },
        }

    legacy_request = VPRRequest.model_validate(request_data)
    if legacy_request.user_id != user_id:
        raise PermissionError('User can only submit VPR for own identity')
    return {
        'application_id': legacy_request.application_id,
        'user_id': legacy_request.user_id,
        'force': bool(request_data.get('force', False)),
        'input_data': request_data,
    }


def _is_stuck_processing(job: dict[str, Any]) -> bool:
    """Return True if the job has been in PROCESSING/PENDING state longer than the worker timeout.

    The worker Lambda times out after 10 minutes.  Any job still in a non-terminal
    state after 15 minutes has either been silently swallowed or the SQS message was
    never delivered — treat it as stuck so the user can retry.
    """
    status = str(job.get('status', '')).lower()
    if status not in {'processing', 'pending'}:
        return False
    created_at_str = str(job.get('created_at') or job.get('started_at') or '').strip()
    if not created_at_str:
        return False
    try:
        created_at = datetime.datetime.fromisoformat(created_at_str)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age_seconds = (datetime.datetime.now(timezone.utc) - created_at).total_seconds()
        return age_seconds > 900  # 15 minutes
    except (ValueError, TypeError):
        return False


def _backfill_application_artifact(application_id: str, user_id: str, job_id: str) -> None:
    """Write VPR completion into the application record's artifact_statuses.

    Called when the idempotency check returns an already-completed job so that
    the hub page reflects the artifact_id on all subsequent loads — even if the
    VPR worker originally ran before the CDK IAM grant was deployed.
    """
    if not application_id or not user_id:
        return
    app_table = os.environ.get('APPLICATIONS_TABLE_NAME') or ''
    if not app_table:
        return
    try:
        from careervp.dal.application_repository import ApplicationRepository
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler

        app_repo = ApplicationRepository(DynamoDalHandler(app_table))
        app_repo.update_artifact_with_id(
            application_id=application_id,
            user_id=user_id,
            artifact_type='vpr',
            status='completed',
            artifact_id=job_id,
        )
        logger.info(
            'Wrote artifact_statuses for idempotent completed VPR',
            job_id=job_id,
            application_id=application_id,
        )
    except Exception as e:
        logger.warning(
            'Could not update application artifact_statuses on idempotent VPR',
            job_id=job_id,
            error=str(e),
        )


@logger.inject_lambda_context(log_event=False)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """
    Handle POST /vpr/generate requests for async VPR generation.

    Flow:
        1. Authenticate request
        2. Parse and validate request payload
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
    set_request_origin(event)
    jobs_repo = JobsRepository()
    endpoint = str(event.get('path', ''))
    tracer.put_annotation(key='endpoint', value=endpoint)
    authenticated_user_id = _extract_authenticated_user_id(event)
    if not authenticated_user_id:
        metrics.add_metric(name='UnauthorizedError', unit='Count', value=1)
        return _build_error_response(
            'Authentication required', HTTPStatus.UNAUTHORIZED, code=ResultCode.UNAUTHORIZED, request_id=_get_request_id(event, context)
        )

    tracer.put_annotation(key='user_id', value=authenticated_user_id)

    try:
        # Parse request body
        request_data = _parse_body(event)
        normalized_request = _normalize_submit_request(request_data, authenticated_user_id)
    except PermissionError as exc:
        logger.warning('Forbidden VPR submit request', error=str(exc))
        metrics.add_metric(name='ForbiddenError', unit='Count', value=1)
        return _build_error_response(
            'User can only access own data', HTTPStatus.FORBIDDEN, code=ResultCode.FORBIDDEN, request_id=_get_request_id(event, context)
        )
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

    logger.append_keys(
        user_id=normalized_request['user_id'],
        application_id=normalized_request['application_id'],
    )

    # Check idempotency
    idempotency_key = _build_idempotency_key(
        str(normalized_request['user_id']),
        str(normalized_request['application_id']),
    )
    existing_job = jobs_repo.get_job_by_idempotency_key(idempotency_key)

    force_regenerate = bool(normalized_request.get('force', False))

    if existing_job:
        # Duplicate request - return existing job_id
        existing_job_id = str(existing_job.get('job_id', ''))
        existing_status = str(existing_job.get('status', 'PROCESSING')).lower()

        # Failed/cancelled jobs (or stuck processing jobs) should not block retries — fall through.
        retriable_statuses = {'failed', 'cancelled'}
        is_stuck = existing_status not in retriable_statuses and _is_stuck_processing(existing_job)
        # A completed VPR is regenerable when the caller explicitly forces it (the
        # "Regenerate" action) or when its S3 result has expired/disappeared. Without
        # this, every completed job — including ones whose result file the lifecycle
        # policy deleted — short-circuits forever and the worker is never invoked.
        completed_regenerable = existing_status == 'completed' and (force_regenerate or _completed_result_missing(existing_job))
        if existing_status not in retriable_statuses and not is_stuck and not completed_regenerable:
            logger.info(
                'Idempotent duplicate request',
                job_id=existing_job_id,
                idempotency_key=idempotency_key,
            )

            # If the existing job is already completed, ensure the application record
            # reflects this — it may have been missed if the worker ran before the CDK
            # IAM grant was deployed, or before update_artifact_with_id was added.
            if existing_status == 'completed':
                _backfill_application_artifact(
                    application_id=str(normalized_request.get('application_id', '')).strip(),
                    user_id=str(normalized_request.get('user_id', '')).strip(),
                    job_id=existing_job_id,
                )

            return {
                'statusCode': int(HTTPStatus.ACCEPTED),
                'headers': _json_headers(),
                'body': json.dumps(
                    {
                        'request_id': existing_job_id,
                        'job_id': existing_job_id,
                        'status': existing_status,
                        'estimated_time_seconds': 120,
                        'webhook_url': f'/vpr/{existing_job_id}',
                    }
                ),
            }

        logger.info(
            'Previous job failed, stuck, or regenerated — creating new job',
            previous_job_id=existing_job_id,
            previous_status=existing_status,
            force_regenerate=force_regenerate,
            completed_regenerable=completed_regenerable,
            idempotency_key=idempotency_key,
        )

    # Generate new job_id
    job_id = str(uuid.uuid4())
    tracer.put_annotation(key='job_id', value=job_id)

    # Use the original request body as input_data for exact match with test expectations
    input_data = request_data  # Store original request body for test compatibility

    # Create job record - pass as single dict for test compatibility
    # Calculate TTL timestamp (24 hours from now)
    now = datetime.datetime.now(datetime.timezone.utc)
    ttl_timestamp = int((now.timestamp() + 24 * 3600))
    created_at = now.isoformat()

    job_record = {
        'job_id': job_id,
        'user_id': normalized_request['user_id'],
        'application_id': normalized_request['application_id'],
        'input_data': input_data if isinstance(input_data, dict) else {},
        'idempotency_key': idempotency_key,
        'status': 'PENDING',  # Included for test compatibility
        'ttl': ttl_timestamp,  # Included for test compatibility
        'created_at': created_at,  # Included for test compatibility
    }
    create_result = jobs_repo.create_job(job_record)

    if not create_result.success:
        logger.error('Failed to create job record', error=create_result.error if hasattr(create_result, 'error') else 'Unknown error')
        metrics.add_metric(name='DynamoValidationException', unit='Count', value=1)
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
                    'user_id': normalized_request['user_id'],
                    'application_id': normalized_request['application_id'],
                }
            ),
            MessageAttributes={
                'job_type': {'StringValue': 'vpr_generation', 'DataType': 'String'},
                'job_id': {'StringValue': job_id, 'DataType': 'String'},
                'user_id': {'StringValue': str(normalized_request['user_id']), 'DataType': 'String'},
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
        metrics.add_metric(name='SqsError', unit='Count', value=1)
        return _build_error_response(
            'Failed to queue job for processing',
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    # Emit metrics
    metrics.add_metric(name='VPRJobCreated', unit='Count', value=1)

    logger.info('VPR job created successfully', job_id=job_id)

    return {
        'statusCode': int(HTTPStatus.ACCEPTED),
        'headers': _json_headers(),
        'body': json.dumps(
            {
                'request_id': job_id,
                'job_id': job_id,
                'status': 'processing',
                'estimated_time_seconds': 120,
                'webhook_url': f'/vpr/{job_id}',
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
