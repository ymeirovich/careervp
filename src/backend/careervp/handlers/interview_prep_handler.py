"""Lambda handler for Interview Prep API endpoint."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from http import HTTPStatus
from typing import Any

import boto3
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from boto3.dynamodb.conditions import Attr, Key
from pydantic import ValidationError

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.dal.jobs_repository import JobsRepository
from careervp.handlers.auth_utils import extract_user_id
from careervp.handlers.cors_utils import get_cors_headers, set_request_origin
from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.logic.cancellation import CancelledBeforePersist
from careervp.logic.interview_prep import generate_interview_prep
from careervp.models.api_models import InterviewPrepRequest
from careervp.models.interview_prep import InterviewPrepRequest as LogicInterviewPrepRequest
from careervp.models.result import Result, ResultCode

sfn = boto3.client('stepfunctions')

INTERVIEW_PREP_SORT_KEY_PREFIX = 'ARTIFACT#INTERVIEW_PREP#'
PRIMARY_KEY_MODE = 'applicationId/artifactId'


def _convert_decimal_to_float(obj: Any) -> Any:
    """Recursively convert Decimal to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _convert_decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_decimal_to_float(i) for i in obj]
    return obj


def _get_artifacts_table_name() -> str:
    for env_key in ('ARTIFACTS_TABLE_NAME', 'DYNAMODB_TABLE_NAME', 'TABLE_NAME'):
        value = os.environ.get(env_key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ''


def _get_dal() -> DynamoDalHandler:
    return DynamoDalHandler(_get_artifacts_table_name())


def _normalize_interview_prep_artifact_id(interview_prep_id: str) -> str:
    normalized = interview_prep_id.strip()
    if normalized.startswith(INTERVIEW_PREP_SORT_KEY_PREFIX):
        return normalized
    return f'{INTERVIEW_PREP_SORT_KEY_PREFIX}{normalized}'


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Handle interview prep API requests and SQS worker events."""
    _ = context
    set_request_origin(event)

    # SQS worker dispatch: if triggered by SQS, process async jobs
    records = event.get('Records', [])
    if records and isinstance(records, list):
        first_source = (records[0] or {}).get('eventSource', '') if records else ''
        if first_source == 'aws:sqs':
            return _process_sqs_event(event)

    method = str(event.get('httpMethod', '')).upper()
    path = str(event.get('path', '')).rstrip('/')

    if method == 'OPTIONS':
        return _build_response(HTTPStatus.OK, {'status': 'ok'})

    if method == 'GET' and _is_interview_prep_status_path(path):
        metrics.add_metric(name='InterviewPrepStatusRequests', unit=MetricUnit.Count, value=1)
        return get_interview_prep_status(event)

    if method == 'GET' and path == '/interview-preps':
        metrics.add_metric(name='InterviewPrepListRequests', unit=MetricUnit.Count, value=1)
        return list_interview_preps(event)

    if method == 'POST' and path == '/interview-prep/generate':
        metrics.add_metric(name='InterviewPrepRequests', unit=MetricUnit.Count, value=1)
        return _submit_interview_prep_request(event)

    if method == 'POST' and path.endswith('/cancel'):
        user_id = _extract_authenticated_user_id(event)
        if not user_id:
            return _build_response(
                HTTPStatus.UNAUTHORIZED,
                {'error': 'Missing or invalid authentication token', 'code': ResultCode.UNAUTHORIZED},
            )
        return _handle_interview_prep_cancel(event, user_id)

    return _build_response(
        HTTPStatus.NOT_FOUND,
        {'error': 'Endpoint not found', 'code': ResultCode.INVALID_INPUT},
    )


def _process_sqs_event(event: dict[str, Any]) -> dict[str, Any]:
    """Process SQS messages for async interview prep generation."""
    for record in event.get('Records', []):
        logger.info('Interview prep worker received SQS record', sqs_record=record)
        body = json.loads(record.get('body', '{}'))
        logger.info('Interview prep worker parsed SQS body', sqs_body=body)
        job_id = body.get('job_id', '')
        user_id = body.get('user_id', '')
        task_token = str(body.get('task_token') or '').strip() or None
        request_data = _request_data_from_sqs_body(body)

        if not job_id or not user_id:
            logger.error('SQS message missing job_id or user_id', body=body)
            continue

        logger.append_keys(job_id=job_id, user_id=user_id)
        logger.info('Processing interview prep SQS job', job_id=job_id)

        try:
            _generate_and_persist_from_sqs(job_id=job_id, user_id=user_id, request_data=request_data)
            _send_task_success(task_token, job_id=job_id, interview_prep_id=job_id)
        except CancelledBeforePersist:
            # Cancelled before/while persisting — skip cleanly: signal the chain
            # branch but do NOT route to the DLQ and do NOT send task_success.
            logger.info('Interview prep cancelled before persist — skipping', job_id=job_id, cancelled_before_persist=True)
            _send_task_failure(task_token, cause='Job was cancelled')
            continue
        except Exception as exc:
            logger.error('Interview prep SQS job failed', job_id=job_id, error=str(exc), exc_info=True)
            _send_task_failure(task_token, cause=str(exc))
            if task_token:
                continue
            raise

    return {'statusCode': 200, 'body': 'OK'}


def _request_data_from_sqs_body(body: dict[str, Any]) -> dict[str, Any]:
    request_data = body.get('request_data')
    if isinstance(request_data, dict) and request_data:
        return request_data

    job_id = str(body.get('job_id') or '').strip()
    return {
        'vpr_id': str(body.get('vpr_id') or '').strip(),
        'gap_response_ids': body.get('gap_response_ids') if isinstance(body.get('gap_response_ids'), list) else ['artifact-chain'],
        'application_id': str(body.get('application_id') or job_id).strip(),
        'job_id': job_id,
        'focus_areas': body.get('focus_areas') if isinstance(body.get('focus_areas'), list) else [],
    }


def _send_task_success(task_token: str | None, *, job_id: str, interview_prep_id: str) -> None:
    if not task_token:
        return
    sfn.send_task_success(
        taskToken=task_token,
        output=json.dumps({'job_id': job_id, 'interview_prep_id': interview_prep_id}),
    )


def _send_task_failure(task_token: str | None, *, cause: str) -> None:
    if not task_token:
        return
    sfn.send_task_failure(
        taskToken=task_token,
        error='InterviewPrepFailed',
        cause=cause,
    )


def _generate_and_persist_from_sqs(
    job_id: str,
    user_id: str,
    request_data: dict[str, Any],
) -> None:
    """Load pending record, generate interview prep, persist result."""
    dal = _get_dal()
    logger.info('Interview prep worker generation starting', job_id=job_id, user_id=user_id, request_data=request_data)

    # Update status to PROCESSING — refuse to resurrect a job cancelled before
    # this (re)delivery (raises CancelledBeforePersist, handled by the SQS loop).
    _update_artifact_status(user_id=user_id, job_id=job_id, status='PROCESSING', fail_if_cancelled=True)

    # Validate the request data
    try:
        api_request = InterviewPrepRequest.model_validate(request_data)
    except ValidationError as validation_exc:
        logger.error(
            'Interview prep worker request validation failed',
            job_id=job_id,
            user_id=user_id,
            request_data=request_data,
            error=str(validation_exc),
        )
        _update_artifact_status(
            user_id=user_id,
            job_id=job_id,
            status='FAILED',
            error='Interview prep request validation failed',
            code=ResultCode.INVALID_INPUT,
            failure_stage='request_validation',
            failure_timestamp=datetime.now(timezone.utc).isoformat(),
            error_details={'exception_type': type(validation_exc).__name__, 'validation_error': str(validation_exc)},
        )
        raise

    # Generate interview prep using existing logic
    try:
        generation_result = _generate_interview_prep_result(
            api_request=api_request,
            user_id=user_id,
        )
    except Exception as generation_exc:
        logger.error(
            'Interview prep worker generation raised exception',
            job_id=job_id,
            user_id=user_id,
            error=str(generation_exc),
            exc_info=True,
        )
        _update_artifact_status(
            user_id=user_id,
            job_id=job_id,
            status='FAILED',
            error=f'Interview prep generation exception: {generation_exc}',
            code=ResultCode.LLM_API_ERROR,
            failure_stage='generation',
            failure_timestamp=datetime.now(timezone.utc).isoformat(),
            error_details={'exception_type': type(generation_exc).__name__},
        )
        raise

    if not generation_result.success or generation_result.data is None:
        generation_error = generation_result.error or 'Interview prep generation failed'
        logger.error(
            'Interview prep worker generation failed',
            job_id=job_id,
            user_id=user_id,
            generation_code=generation_result.code,
            generation_error=generation_error,
        )
        _update_artifact_status(
            user_id=user_id,
            job_id=job_id,
            status='FAILED',
            error=generation_error,
            code=generation_result.code or ResultCode.INTERNAL_ERROR,
            failure_stage='generation',
            failure_timestamp=datetime.now(timezone.utc).isoformat(),
            error_details={'generation_success': generation_result.success},
        )
        raise RuntimeError(f'Interview prep generation failed: {generation_error}')

    prep_model = generation_result.data.interview_prep
    if prep_model is None:
        logger.error('Interview prep worker generation returned empty interview_prep', job_id=job_id, user_id=user_id)
        _update_artifact_status(
            user_id=user_id,
            job_id=job_id,
            status='FAILED',
            error='Interview prep generation returned no content',
            code=ResultCode.INTERNAL_ERROR,
            failure_stage='generation',
            failure_timestamp=datetime.now(timezone.utc).isoformat(),
            error_details={'generation_success': generation_result.success},
        )
        raise RuntimeError('Interview prep generation returned no content')

    # Persist the result
    prep_payload = prep_model.model_dump(mode='json')
    logger.info('Interview prep worker persisting generation payload', job_id=job_id, user_id=user_id, interview_prep_payload=prep_payload)
    try:
        _persist_interview_prep(dal=dal, user_id=user_id, prep_payload=prep_payload)
    except Exception as persist_exc:
        logger.error(
            '_persist_interview_prep failed in SQS worker; marking job FAILED',
            job_id=job_id,
            user_id=user_id,
            error=f'{type(persist_exc).__name__}: {persist_exc}',
            exc_info=True,
        )
        _update_artifact_status(
            user_id=user_id,
            job_id=job_id,
            status='FAILED',
            error=f'Persistence failed for interview prep job {job_id}',
            code=ResultCode.DYNAMODB_ERROR,
            failure_stage='persistence',
            failure_timestamp=datetime.now(timezone.utc).isoformat(),
            error_details={'exception_type': type(persist_exc).__name__, 'exception_message': str(persist_exc)},
        )
        raise RuntimeError(f'Persistence failed for interview prep job {job_id}: {persist_exc}') from persist_exc

    # Update the artifact record to COMPLETED only after successful persistence —
    # a cancel during generation must not be overwritten back to COMPLETED.
    _update_artifact_status(
        user_id=user_id,
        job_id=job_id,
        status='COMPLETED',
        result_data=_convert_decimal_to_float(prep_payload),
        fail_if_cancelled=True,
    )

    # Propagate completion to the application record so the hub reflects the
    # artifact status and artifact_id across page reloads.
    _update_application_artifact(
        application_id=str(request_data.get('application_id') or request_data.get('job_id') or ''),
        user_id=user_id,
        artifact_type='interview_prep',
        artifact_id=job_id,
    )

    metrics.add_metric(name='InterviewPrepWorkerGenerated', unit=MetricUnit.Count, value=1)
    logger.info('Interview prep SQS job completed', job_id=job_id)


def _update_artifact_status(  # noqa: C901
    user_id: str,
    job_id: str,
    status: str,
    result_data: dict[str, Any] | None = None,
    error: str | None = None,
    code: str | None = None,
    failure_stage: str | None = None,
    failure_timestamp: str | None = None,
    error_details: dict[str, Any] | None = None,
    fail_if_cancelled: bool = False,
) -> None:
    """Update interview prep artifact status in DynamoDB.

    When ``fail_if_cancelled`` is True the write is conditional and is rejected
    if the artifact is already CANCELLED; that rejection is surfaced as
    ``CancelledBeforePersist`` so the worker skips cleanly instead of resurrecting
    a cancelled artifact (FE-UI-043 worker_cancelled_guard).
    """
    import datetime as _dt

    import boto3 as _boto3

    table_name = _get_artifacts_table_name()
    table = _boto3.resource('dynamodb').Table(table_name)
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()

    update_expr = 'SET #s = :status, updated_at = :now'
    attr_names: dict[str, str] = {'#s': 'status'}
    attr_values: dict[str, Any] = {':status': status, ':now': now}

    if result_data is not None:
        update_expr += ', interview_prep = :result'
        attr_values[':result'] = result_data
    if error is not None:
        update_expr += ', #err = :error'
        attr_names['#err'] = 'error'
        attr_values[':error'] = error
    if code is not None:
        update_expr += ', #code = :code'
        attr_names['#code'] = 'code'
        attr_values[':code'] = str(code)
    if failure_stage is not None:
        update_expr += ', failure_stage = :failure_stage'
        attr_values[':failure_stage'] = failure_stage
    if failure_timestamp is not None:
        update_expr += ', failure_timestamp = :failure_timestamp'
        attr_values[':failure_timestamp'] = failure_timestamp
    if error_details is not None:
        update_expr += ', error_details = :error_details'
        attr_values[':error_details'] = error_details

    condition: str | None = None
    if fail_if_cancelled:
        condition = 'attribute_not_exists(#s) OR #s <> :cancelled'
        attr_values[':cancelled'] = 'CANCELLED'

    artifact_id = _normalize_interview_prep_artifact_id(job_id)
    update_kwargs: dict[str, Any] = {
        'Key': {'applicationId': user_id, 'artifactId': artifact_id},
        'UpdateExpression': update_expr,
        'ExpressionAttributeNames': attr_names,
        'ExpressionAttributeValues': attr_values,
    }
    if condition is not None:
        update_kwargs['ConditionExpression'] = condition
    try:
        table.update_item(**update_kwargs)
    except Exception as exc:
        error_response = getattr(exc, 'response', {}) if hasattr(exc, 'response') else {}
        error_code = ((error_response.get('Error') or {}).get('Code')) if isinstance(error_response, dict) else None
        if fail_if_cancelled and error_code == 'ConditionalCheckFailedException':
            logger.info('Interview prep cancelled before write — skipping', request_id=job_id, attempted_status=status)
            raise CancelledBeforePersist(job_id) from exc
        logger.error(
            'Failed to update artifact status',
            user_id=user_id,
            request_id=job_id,
            key_schema_mode=PRIMARY_KEY_MODE,
            error=str(exc),
        )
        raise


def _update_application_artifact(
    application_id: str,
    user_id: str,
    artifact_type: str,
    artifact_id: str,
) -> None:
    """Propagate artifact completion to the application record's artifact_statuses.

    Silently ignored when the application record does not exist — non-fatal
    because the session-local frontend fallback handles this case.
    """
    if not application_id or not user_id:
        return
    app_table = os.environ.get('APPLICATIONS_TABLE_NAME') or os.environ.get('DYNAMODB_TABLE_NAME') or ''
    if not app_table:
        return
    try:
        from careervp.dal.application_repository import ApplicationRepository
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler

        app_repo = ApplicationRepository(DynamoDalHandler(app_table))
        app_repo.update_artifact_with_id(
            application_id=application_id,
            user_id=user_id,
            artifact_type=artifact_type,
            status='completed',
            artifact_id=artifact_id,
        )
    except Exception as e:
        logger.warning(
            'Could not update application artifact_statuses',
            artifact_type=artifact_type,
            error=str(e),
        )


def _submit_interview_prep_request(event: dict[str, Any]) -> dict[str, Any]:
    """Handle POST /interview-prep/generate requests."""
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        return _build_response(
            HTTPStatus.UNAUTHORIZED,
            {'error': 'Missing or invalid authentication token', 'code': ResultCode.UNAUTHORIZED},
        )

    request_result = _parse_request(event)
    if not request_result.success or not request_result.data:
        metrics.add_metric(name='InterviewPrepFailures', unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.BAD_REQUEST,
            {'error': request_result.error or 'Invalid request', 'code': ResultCode.INVALID_INPUT},
        )
    api_request = request_result.data

    dal = _get_dal()

    try:
        generation_result = _generate_interview_prep_result(api_request=api_request, user_id=user_id)
    except Exception as gen_exc:
        logger.error(
            'Interview prep generation raised exception',
            user_id=user_id,
            error=f'{type(gen_exc).__name__}: {gen_exc}',
            exc_info=True,
        )
        metrics.add_metric(name='InterviewPrepFailures', unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.SERVICE_UNAVAILABLE,
            {'error': 'Interview prep generation failed. Please try again.', 'code': ResultCode.LLM_API_ERROR},
        )
    if not generation_result.success or generation_result.data is None:
        metrics.add_metric(name='InterviewPrepFailures', unit=MetricUnit.Count, value=1)
        return _build_generation_error_response(generation_result)

    prep_model = generation_result.data.interview_prep
    if prep_model is None:
        metrics.add_metric(name='InterviewPrepFailures', unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {'error': 'Interview prep generation returned no content', 'code': ResultCode.INTERNAL_ERROR},
        )

    prep_payload = prep_model.model_dump(mode='json')
    try:
        persist_result = _persist_interview_prep(dal=dal, user_id=user_id, prep_payload=prep_payload)
    except Exception:
        persist_result = Result(success=False, error='persist failed', code=ResultCode.DYNAMODB_ERROR)
    if not persist_result.success:
        metrics.add_metric(name='InterviewPrepPersistenceFailure', unit=MetricUnit.Count, value=1)
        logger.error(
            'Interview prep persistence failed; cannot return synthetic success',
            user_id=user_id,
            error=persist_result.error,
        )
        return _build_response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {'error': 'Interview prep generated but failed to save. Please try again.', 'code': ResultCode.DYNAMODB_ERROR},
        )

    artifact_id = str(prep_payload.get('prep_id', '')).strip()
    metrics.add_metric(name='InterviewPrepGenerated', unit=MetricUnit.Count, value=1)
    return _build_response(HTTPStatus.OK, {'artifact_id': artifact_id, 'status': 'completed'})


def get_interview_prep_status(event: dict[str, Any]) -> dict[str, Any]:
    """Handle GET /interview-prep/{interviewPrepId} requests."""
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        return _build_response(
            HTTPStatus.UNAUTHORIZED,
            {'error': 'Missing or invalid authentication token', 'code': ResultCode.UNAUTHORIZED},
        )

    interview_prep_id = _extract_interview_prep_id(event)
    if not interview_prep_id:
        return _build_response(
            HTTPStatus.BAD_REQUEST,
            {'error': 'Missing interviewPrepId path parameter', 'code': ResultCode.MISSING_REQUIRED_FIELD},
        )

    interview_prep_item = _get_interview_prep_item(user_id, interview_prep_id)
    if not interview_prep_item:
        metrics.add_metric(name='InterviewPrepStatusNotFound', unit=MetricUnit.Count, value=1)
        logger.warning(
            'Interview prep status lookup returned no record',
            user_id=user_id,
            request_id=interview_prep_id,
            key_schema_mode=PRIMARY_KEY_MODE,
        )
        return _build_response(
            HTTPStatus.NOT_FOUND,
            {'error': 'Interview prep not found', 'code': ResultCode.INTERVIEW_PREP_NOT_FOUND},
        )

    status_payload = _build_interview_prep_status_payload(interview_prep_item, interview_prep_id)
    logger.info(
        'Interview prep status response payload built',
        user_id=user_id,
        request_id=interview_prep_id,
        status_payload=status_payload,
    )
    return _build_response(HTTPStatus.OK, status_payload)


def list_interview_preps(event: dict[str, Any]) -> dict[str, Any]:
    """Handle GET /interview-preps requests."""
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        return _build_response(
            HTTPStatus.UNAUTHORIZED,
            {'error': 'Missing or invalid authentication token', 'code': ResultCode.UNAUTHORIZED},
        )

    dal = _get_dal()
    table = dal._get_db_handler(dal.table_name)
    response = table.query(
        KeyConditionExpression=Key('applicationId').eq(user_id) & Key('artifactId').begins_with(INTERVIEW_PREP_SORT_KEY_PREFIX),
        Limit=50,
    )
    items = response.get('Items', []) if isinstance(response, dict) else []
    payload: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        prep_payload = item.get('interview_prep')
        prep_id = _extract_prep_id_from_payload(prep_payload)
        if not prep_id:
            prep_id = str(item.get('artifactId', '')).replace(INTERVIEW_PREP_SORT_KEY_PREFIX, '')
        payload.append(
            {
                'id': prep_id,
                'status': _normalize_status(item.get('status')),
                'created_at': item.get('created_at'),
                'updated_at': item.get('updated_at'),
            }
        )

    return _build_response(HTTPStatus.OK, {'interview_preps': payload})


def _parse_request(event: dict[str, Any]) -> Result[InterviewPrepRequest]:
    """Parse and validate request body."""
    body_content = event.get('body', '{}')
    try:
        payload = json.loads(body_content or '{}')
    except (TypeError, json.JSONDecodeError):
        logger.warning('Invalid JSON body for interview prep request')
        return Result(success=False, error='Invalid JSON request body', code=ResultCode.INVALID_INPUT)

    try:
        request = InterviewPrepRequest(**payload)
    except ValidationError:
        logger.warning('InterviewPrepRequest validation failed')
        return Result(success=False, error='Request validation failed', code=ResultCode.INVALID_INPUT)

    return Result(success=True, data=request, code=ResultCode.SUCCESS)


def _is_interview_prep_status_path(path: str) -> bool:
    return path.startswith('/interview-prep/') and path != '/interview-prep/generate'


def _extract_authenticated_user_id(event: dict[str, Any]) -> str | None:
    return extract_user_id(event)


def _extract_interview_prep_id(event: dict[str, Any]) -> str | None:
    path_parameters = event.get('pathParameters')
    if isinstance(path_parameters, dict):
        for key in ('interviewPrepId', 'interview_prep_id', 'id', 'job_id', 'jobId'):
            value = path_parameters.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    path = str(event.get('path', '')).rstrip('/')
    if path.startswith('/interview-prep/'):
        candidate = path.removeprefix('/interview-prep/').strip()
        if candidate.endswith('/status'):
            candidate = candidate[: -len('/status')]
        if candidate and candidate != 'generate':
            return candidate
    return None


def _coerce_text(value: Any) -> str:
    return str(value or '').strip()


def _build_context_dal_candidates(
    *,
    env_table_name: str,
    fallback_dal: Any,
) -> list[Any]:
    """Prefer feature-specific table DAL, then fallback DAL for backward compatibility."""
    candidates: list[Any] = []
    fallback_table_name = _coerce_text(getattr(fallback_dal, 'table_name', ''))
    preferred_table_name = _coerce_text(os.environ.get(env_table_name))

    if preferred_table_name and preferred_table_name != fallback_table_name:
        candidates.append(DynamoDalHandler(preferred_table_name))

    candidates.append(fallback_dal)
    return candidates


def _extract_vpr_differentiators(vpr_payload: dict[str, Any]) -> list[str] | None:
    raw_differentiators = vpr_payload.get('differentiators')
    if not isinstance(raw_differentiators, list):
        return None

    differentiators: list[str] = []
    for raw_entry in raw_differentiators:
        if isinstance(raw_entry, dict):
            value = _coerce_text(raw_entry.get('text') or raw_entry.get('value'))
        else:
            value = _coerce_text(raw_entry)
        if value:
            differentiators.append(value)
    return differentiators or None


def _resolve_vpr_from_jobs_table(vpr_id: str, user_id: str) -> dict[str, Any] | None:
    table_name = _coerce_text(os.environ.get('VPR_JOBS_TABLE_NAME') or os.environ.get('JOBS_TABLE_NAME'))
    if not table_name:
        return None

    logger.info('Interview prep context VPR jobs lookup start', vpr_id=vpr_id, jobs_table_name=table_name)
    try:
        repository = JobsRepository(table_name=table_name)
        job_record = repository.get_job(vpr_id)
    except Exception as exc:
        logger.warning('Interview prep context VPR jobs lookup failed', vpr_id=vpr_id, jobs_table_name=table_name, error=str(exc))
        return None

    if not isinstance(job_record, dict):
        logger.info('Interview prep context VPR jobs lookup empty', vpr_id=vpr_id, jobs_table_name=table_name)
        return None

    # Ownership check: the job record must belong to the requesting user.
    record_owner = str(job_record.get('user_id') or '').strip()
    if record_owner != user_id:
        logger.warning('VPR job ownership mismatch for interview prep', vpr_id=vpr_id, expected=user_id, actual=record_owner)
        return None

    logger.info('Interview prep context VPR jobs lookup payload', vpr_id=vpr_id, jobs_table_name=table_name, job_record=job_record)
    payload = job_record.get('result')
    if isinstance(payload, dict):
        merged_payload = dict(payload)
    else:
        merged_payload = {}

    merged_payload.setdefault('vpr_id', vpr_id)
    application_id = _coerce_text(job_record.get('application_id'))
    if application_id:
        merged_payload.setdefault('application_id', application_id)

    input_data = job_record.get('input_data')
    if isinstance(input_data, dict):
        language = _coerce_text(input_data.get('language'))
        if language:
            merged_payload.setdefault('language', language)

    return merged_payload if merged_payload else None


_MAX_QUESTION_COUNT = 15
_DEFAULT_QUESTION_COUNT = 10


def _resolve_interview_prep_context(  # noqa: C901
    dal: Any,
    user_id: str,
    api_request: InterviewPrepRequest,
) -> dict[str, Any]:
    """Resolve architecture-required context inputs server-side (section 3.7).

    Returns dict with: cv_facts, vpr_data, vpr_differentiators,
    gap_responses, company_research, language, job_title, job_id.
    A missing VPR is fatal; downstream interview prep must not use fabricated
    upstream context.
    """
    context: dict[str, Any] = {
        'cv_facts': None,
        'vpr_data': None,
        'vpr_differentiators': None,
        'gap_responses': None,
        'company_research': None,
        'language': getattr(api_request, 'language', 'en') or 'en',
        'job_title': '',
        'job_id': getattr(api_request, 'job_id', None),
    }

    # Resolve CV facts
    cv_candidates = _build_context_dal_candidates(
        env_table_name='CVS_TABLE_NAME',
        fallback_dal=dal,
    )
    for cv_dal in cv_candidates:
        cv_table_name = _coerce_text(getattr(cv_dal, 'table_name', ''))
        logger.info('Interview prep context CV lookup attempt', user_id=user_id, table_name=cv_table_name)
        try:
            raw_cv = cv_dal.get_cv(user_id)
        except Exception as exc:
            metrics.add_metric(name='InterviewPrepCVResolutionError', unit=MetricUnit.Count, value=1)
            logger.warning('CV resolution failed', user_id=user_id, table_name=cv_table_name, error=str(exc))
            continue

        if raw_cv is None:
            logger.info('Interview prep context CV lookup empty', user_id=user_id, table_name=cv_table_name)
            continue

        cv_dict = raw_cv.model_dump(mode='json') if hasattr(raw_cv, 'model_dump') else dict(raw_cv)
        logger.info('Interview prep context CV lookup payload', user_id=user_id, table_name=cv_table_name, cv_payload=cv_dict)
        context['cv_facts'] = {
            'professional_summary': cv_dict.get('professional_summary'),
            'skills': cv_dict.get('skills', []),
            'experience': cv_dict.get('experience') or cv_dict.get('work_experience', []),
        }
        metrics.add_metric(name='InterviewPrepCVResolved', unit=MetricUnit.Count, value=1)
        break
    if context['cv_facts'] is None:
        metrics.add_metric(name='InterviewPrepCVMissing', unit=MetricUnit.Count, value=1)
        logger.warning('CV not found for interview prep context', user_id=user_id)

    # Resolve VPR data (prefer VPR jobs table entry by vpr job id)
    try:
        vpr_payload = _resolve_vpr_from_jobs_table(api_request.vpr_id, user_id=user_id)
        if isinstance(vpr_payload, dict):
            logger.info('Interview prep context VPR payload from jobs table', vpr_id=api_request.vpr_id, vpr_payload=vpr_payload)
            context['vpr_data'] = vpr_payload
            context['vpr_differentiators'] = _extract_vpr_differentiators(vpr_payload) or []
            context['language'] = _coerce_text(vpr_payload.get('language')) or context['language']
            metrics.add_metric(name='InterviewPrepVPRResolved', unit=MetricUnit.Count, value=1)
        else:
            vpr_result = dal.get_vpr(api_request.vpr_id)
            if hasattr(vpr_result, 'success') and vpr_result.success and vpr_result.data is not None:
                vpr = vpr_result.data
                # Ownership: reject VPRs that belong to a different user.
                vpr_owner = getattr(vpr, 'user_id', None) or (vpr.get('user_id') if isinstance(vpr, dict) else None)
                if str(vpr_owner or '').strip() != user_id:
                    logger.warning('VPR ownership mismatch in DAL fallback for interview prep', vpr_id=api_request.vpr_id, expected=user_id)
                    metrics.add_metric(name='InterviewPrepVPROwnershipMismatch', unit=MetricUnit.Count, value=1)
                else:
                    vpr_dict = vpr.model_dump(mode='json') if hasattr(vpr, 'model_dump') else dict(vpr)
                    logger.info(
                        'Interview prep context VPR payload from DAL fallback',
                        vpr_id=api_request.vpr_id,
                        table_name=getattr(dal, 'table_name', ''),
                        vpr_payload=vpr_dict,
                    )
                    context['vpr_data'] = vpr_dict
                    context['vpr_differentiators'] = _extract_vpr_differentiators(vpr_dict) or []
                    context['language'] = _coerce_text(vpr_dict.get('language')) or context['language']
                    metrics.add_metric(name='InterviewPrepVPRResolved', unit=MetricUnit.Count, value=1)
            else:
                metrics.add_metric(name='InterviewPrepVPRMissing', unit=MetricUnit.Count, value=1)
                logger.warning('VPR not found for context resolution', vpr_id=api_request.vpr_id)
    except Exception as exc:
        metrics.add_metric(name='InterviewPrepVPRResolutionError', unit=MetricUnit.Count, value=1)
        logger.warning('VPR resolution failed', vpr_id=api_request.vpr_id, error=str(exc))

    if context['vpr_data'] is None:
        raise ValueError(f'Required VPR not found for interview prep: {api_request.vpr_id}')

    # Resolve gap responses filtered by requested gap_response_ids
    gap_candidates = _build_context_dal_candidates(
        env_table_name='GAP_RESPONSES_TABLE_NAME',
        fallback_dal=dal,
    )
    requested_ids = {entry.strip() for entry in api_request.gap_response_ids if entry.strip()}
    for gap_dal in gap_candidates:
        gap_table_name = _coerce_text(getattr(gap_dal, 'table_name', ''))
        logger.info(
            'Interview prep context gap responses lookup attempt',
            user_id=user_id,
            table_name=gap_table_name,
            requested_gap_response_ids=list(requested_ids),
        )
        try:
            gap_result = gap_dal.get_gap_responses(user_id)
        except Exception as exc:
            logger.warning('Gap responses resolution failed', user_id=user_id, table_name=gap_table_name, error=str(exc))
            continue

        if not hasattr(gap_result, 'success') or not gap_result.success or not gap_result.data:
            logger.info('Interview prep context gap responses lookup empty', user_id=user_id, table_name=gap_table_name)
            continue

        all_responses: list[dict[str, Any]] = []
        for raw_response in gap_result.data:
            if hasattr(raw_response, 'model_dump'):
                normalized = raw_response.model_dump(mode='json')
            elif isinstance(raw_response, dict):
                normalized = dict(raw_response)
            else:
                continue
            all_responses.append(normalized)

        logger.info(
            'Interview prep context gap responses lookup payload', user_id=user_id, table_name=gap_table_name, gap_responses_payload=all_responses
        )
        if requested_ids:
            filtered = [
                response
                for response in all_responses
                if _coerce_text(response.get('question_id') or response.get('questionId') or response.get('id')) in requested_ids
            ]
            context['gap_responses'] = filtered or all_responses
        else:
            context['gap_responses'] = all_responses
        metrics.add_metric(name='InterviewPrepGapResponsesResolved', unit=MetricUnit.Count, value=1)
        break

    # Resolve company research (optional — graceful degradation when absent)
    job_id = context['job_id']
    if job_id:
        try:
            table = dal._get_db_handler(dal.table_name)
            company_prefix = 'ARTIFACT#COMPANY_RESEARCH#'
            resp = table.query(
                KeyConditionExpression=Key('applicationId').eq(user_id) & Key('artifactId').begins_with(company_prefix),
                FilterExpression=Attr('artifactId').contains(job_id),
                Limit=1,
            )
            items = resp.get('Items', []) if isinstance(resp, dict) else []
            if items and isinstance(items[0], dict):
                context['company_research'] = items[0].get('company_research') or items[0]
                metrics.add_metric(name='InterviewPrepCompanyResearchResolved', unit=MetricUnit.Count, value=1)
        except Exception as exc:
            logger.warning('Company research resolution failed', job_id=job_id, error=str(exc))

    logger.info(
        'Interview prep context resolved',
        user_id=user_id,
        vpr_id=api_request.vpr_id,
        job_id=job_id,
        cv_resolved=context['cv_facts'] is not None,
        vpr_resolved=context['vpr_data'] is not None,
        gap_resolved=bool(context['gap_responses']),
        company_research_resolved=context['company_research'] is not None,
        language=context['language'],
        key_schema_mode=PRIMARY_KEY_MODE,
    )
    return context


def _generate_interview_prep_result(
    api_request: InterviewPrepRequest,
    user_id: str,
) -> Result[Any]:
    dal = _get_dal()
    ctx = _resolve_interview_prep_context(dal, user_id, api_request)

    # Enforce question_count policy: honor explicit lower values, cap at MAX
    question_count = min(max(int(api_request.question_count or _DEFAULT_QUESTION_COUNT), 1), _MAX_QUESTION_COUNT)

    logic_request = LogicInterviewPrepRequest(
        user_id=user_id,
        vpr_id=api_request.vpr_id,
        job_id=ctx['job_id'],
        gap_response_ids=list(api_request.gap_response_ids),
        focus_areas=list(api_request.focus_areas),
        question_count=question_count,
    )
    maybe_async_result = generate_interview_prep(
        request=logic_request,
        vpr_data=ctx['vpr_data'],
        gap_responses=ctx['gap_responses'] or [],
        job_title=ctx['job_title'],
        company_name='',
        cv_facts=ctx['cv_facts'],
        job_requirements=None,
        vpr_differentiators=ctx['vpr_differentiators'],
        company_research=ctx['company_research'],
        language=ctx['language'],
    )
    logger.info(
        'Interview prep worker generation input payload',
        user_id=user_id,
        api_request=api_request.model_dump(mode='json'),
        generation_context=ctx,
    )
    if asyncio.iscoroutine(maybe_async_result):
        async_result = asyncio.run(maybe_async_result)
        logger.info(
            'Interview prep worker generation output payload',
            user_id=user_id,
            success=async_result.success,
            code=async_result.code,
            error=async_result.error,
            has_data=async_result.data is not None,
        )
        return async_result
    if isinstance(maybe_async_result, Result):
        logger.info(
            'Interview prep worker generation output payload',
            user_id=user_id,
            success=maybe_async_result.success,
            code=maybe_async_result.code,
            error=maybe_async_result.error,
            has_data=maybe_async_result.data is not None,
        )
        return maybe_async_result
    return Result(
        success=False,
        error='Invalid interview prep generation response',
        code=ResultCode.INTERNAL_ERROR,
    )


def _persist_interview_prep(dal: DynamoDalHandler, user_id: str, prep_payload: dict[str, Any]) -> Result[None]:
    table = dal._get_db_handler(dal.table_name)
    prep_id = str(prep_payload.get('prep_id', '')).strip()
    if not prep_id:
        prep_id = f'prep-{datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")}'
    ttl = int((datetime.now(timezone.utc) + timedelta(days=730)).timestamp())
    artifact_id = f'{INTERVIEW_PREP_SORT_KEY_PREFIX}{prep_id}'
    item = {
        'applicationId': user_id,
        'artifactId': artifact_id,
        'artifactType': 'interview_prep',
        'user_id': user_id,
        'prep_id': prep_id,
        'status': 'completed',
        'interview_prep': prep_payload,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'expiration': ttl,
        # Compatibility mirrors for legacy readers still expecting pk/sk attributes.
        'pk': user_id,
        'sk': artifact_id,
    }
    logger.info('Interview prep worker writing interview prep artifact', user_id=user_id, prep_payload=prep_payload, dynamodb_item=item)
    table.put_item(Item=item)
    return Result(success=True, data=None, code=ResultCode.SUCCESS)


def _build_generation_error_response(generation_result: Result[Any]) -> dict[str, Any]:
    if generation_result.code in {ResultCode.LLM_TIMEOUT, ResultCode.LLM_API_ERROR}:
        http_status = HTTPStatus.SERVICE_UNAVAILABLE
    elif generation_result.code in {ResultCode.INVALID_INPUT, ResultCode.MISSING_REQUIRED_FIELD}:
        http_status = HTTPStatus.BAD_REQUEST
    elif generation_result.code in {ResultCode.FORBIDDEN, ResultCode.UNAUTHORIZED}:
        http_status = HTTPStatus.FORBIDDEN
    else:
        http_status = HTTPStatus.INTERNAL_SERVER_ERROR

    return _build_response(
        http_status,
        {
            'error': generation_result.error or 'Interview prep generation failed',
            'code': generation_result.code,
        },
    )


def _get_interview_prep_item(user_id: str, interview_prep_id: str) -> dict[str, Any] | None:  # noqa: C901
    dal = _get_dal()
    table = dal._get_db_handler(dal.table_name)

    candidate_artifact_ids = (
        _normalize_interview_prep_artifact_id(interview_prep_id),
        interview_prep_id,
    )
    for artifact_id in candidate_artifact_ids:
        try:
            get_response = table.get_item(Key={'applicationId': user_id, 'artifactId': artifact_id})
        except Exception:
            get_response = {}
        item = get_response.get('Item') if isinstance(get_response, dict) else None
        if isinstance(item, dict):
            return item

    # Temporary backward-compatible fallback for legacy records written with pk/sk key schema.
    for artifact_id in candidate_artifact_ids:
        try:
            legacy_response = table.get_item(Key={'pk': user_id, 'sk': artifact_id})
        except Exception:
            legacy_response = {}
        legacy_item = legacy_response.get('Item') if isinstance(legacy_response, dict) else None
        if isinstance(legacy_item, dict):
            return legacy_item

    try:
        query_response = table.query(
            KeyConditionExpression=Key('applicationId').eq(user_id) & Key('artifactId').begins_with(INTERVIEW_PREP_SORT_KEY_PREFIX),
            FilterExpression=Attr('artifactId').contains(interview_prep_id),
            Limit=1,
        )
    except Exception:
        query_response = {}
    query_items = query_response.get('Items') if isinstance(query_response, dict) else None
    if isinstance(query_items, list) and query_items and isinstance(query_items[0], dict):
        return query_items[0]

    # Temporary legacy-query fallback while old records exist.
    try:
        legacy_query_response = table.query(
            KeyConditionExpression=Key('pk').eq(user_id) & Key('sk').begins_with(INTERVIEW_PREP_SORT_KEY_PREFIX),
            FilterExpression=Attr('sk').contains(interview_prep_id),
            Limit=1,
        )
    except Exception:
        legacy_query_response = {}
    legacy_query_items = legacy_query_response.get('Items') if isinstance(legacy_query_response, dict) else None
    if isinstance(legacy_query_items, list) and legacy_query_items and isinstance(legacy_query_items[0], dict):
        return legacy_query_items[0]
    return None


def _normalize_status(raw_status: Any) -> str:
    status = str(raw_status or '').strip().lower()
    if status in {'pending', 'processing', 'completed', 'failed'}:
        return status
    if status:
        logger.warning('Unexpected interview prep status value', raw_status=raw_status)
    return 'pending'


def _extract_prep_id_from_payload(prep_payload: Any) -> str | None:
    if not isinstance(prep_payload, dict):
        return None
    for key in ('prep_id', 'id', 'interview_prep_id'):
        value = prep_payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _normalize_suggested_answer(raw_answer: Any) -> dict[str, Any] | None:
    if not isinstance(raw_answer, dict):
        return None

    suggested: dict[str, Any] = {'format': str(raw_answer.get('format') or 'STAR')}
    for key in ('situation', 'task', 'action', 'result'):
        value = raw_answer.get(key)
        if isinstance(value, str):
            suggested[key] = value
    return suggested


def _normalize_questions(raw_questions: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_questions, list):
        return []

    questions: list[dict[str, Any]] = []
    for index, entry in enumerate(raw_questions):
        if not isinstance(entry, dict):
            continue

        question_id = str(entry.get('question_id') or entry.get('id') or f'q{index + 1}')
        question_text = str(entry.get('question') or entry.get('text') or '')

        item: dict[str, Any] = {
            'id': question_id,
            'text': question_text,
            'question_type': str(entry.get('question_type') or 'behavioral'),
        }

        suggested_answer = _normalize_suggested_answer(entry.get('suggested_answer'))
        if suggested_answer is not None:
            item['suggested_answer'] = suggested_answer

        questions.append(item)
    return questions


def _build_interview_prep_status_payload(item: dict[str, Any], fallback_id: str) -> dict[str, Any]:
    prep_payload = item.get('interview_prep')
    prep_id = (
        _extract_prep_id_from_payload(prep_payload)
        or str(item.get('prep_id') or '').strip()
        or str(item.get('artifactId') or '').replace(INTERVIEW_PREP_SORT_KEY_PREFIX, '').strip()
        or fallback_id
    )
    status = _normalize_status(item.get('status'))

    payload: dict[str, Any] = {
        'id': prep_id,
        'status': status,
    }

    if status in {'completed', 'failed'}:
        raw_questions = None
        if isinstance(prep_payload, dict):
            raw_questions = prep_payload.get('questions')
        if raw_questions is None:
            raw_questions = item.get('questions')

        result_payload: dict[str, Any] = {
            'questions': _normalize_questions(raw_questions),
        }
        if isinstance(prep_payload, dict):
            result_payload['questions_to_ask'] = prep_payload.get('questions_to_ask') or []
            result_payload['pre_interview_checklist'] = prep_payload.get('pre_interview_checklist') or []
            result_payload['salary_guidance'] = prep_payload.get('salary_guidance')
            result_payload['interview_report'] = {
                'readiness_summary': prep_payload.get('readiness_summary') or 'Preparation synthesized from role context and behavioral focus areas.',
            }
        payload['result'] = result_payload
    if status == 'failed':
        payload['error'] = str(item.get('error') or 'Interview prep generation failed')
        payload['code'] = str(item.get('code') or ResultCode.INTERNAL_ERROR)
        if item.get('failure_stage') is not None:
            payload['failure_stage'] = item.get('failure_stage')
        if item.get('failure_timestamp') is not None:
            payload['failure_timestamp'] = item.get('failure_timestamp')
        if item.get('error_details') is not None:
            payload['error_details'] = item.get('error_details')

    return payload


_INTERVIEW_PREP_TERMINAL_STATUSES = {'COMPLETED', 'FAILED', 'CANCELLED'}


def _handle_interview_prep_cancel(event: dict[str, Any], user_id: str) -> dict[str, Any]:
    """Handle POST /interview-prep/{interviewPrepId}/cancel."""
    import boto3 as _boto3

    path_params = event.get('pathParameters') or {}
    interview_prep_id = str(path_params.get('interviewPrepId') or '').strip()
    if not interview_prep_id:
        return _build_response(HTTPStatus.BAD_REQUEST, {'error': 'Missing interviewPrepId'})

    table_name = _get_artifacts_table_name()
    table = _boto3.resource('dynamodb').Table(table_name)
    artifact_id = f'ARTIFACT#INTERVIEW_PREP#{interview_prep_id}'

    try:
        get_resp = table.get_item(Key={'applicationId': user_id, 'artifactId': artifact_id})
        item = (get_resp or {}).get('Item')
    except Exception as exc:
        logger.error('DynamoDB error during interview prep cancel', error=str(exc))
        return _build_response(HTTPStatus.INTERNAL_SERVER_ERROR, {'error': 'Internal server error'})

    if not item:
        try:
            query_resp = table.query(
                KeyConditionExpression='applicationId = :uid AND begins_with(artifactId, :prefix)',
                ExpressionAttributeValues={
                    ':uid': user_id,
                    ':prefix': f'ARTIFACT#INTERVIEW_PREP#{interview_prep_id}',
                },
                Limit=1,
            )
            items = (query_resp or {}).get('Items', [])
            item = items[0] if items else None
        except Exception:
            item = None
        if not item:
            return _build_response(HTTPStatus.NOT_FOUND, {'error': 'Interview prep not found'})

    status = str(item.get('status', '')).upper()
    if status in _INTERVIEW_PREP_TERMINAL_STATUSES:
        return _build_response(HTTPStatus.CONFLICT, {'error': 'Cannot cancel terminal task'})

    item_app_id = str(item.get('applicationId', user_id))
    item_artifact_id = str(item.get('artifactId', artifact_id))
    table.update_item(
        Key={'applicationId': item_app_id, 'artifactId': item_artifact_id},
        UpdateExpression='SET #s = :status',
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={':status': 'CANCELLED'},
    )
    return _build_response(HTTPStatus.OK, {'status': 'cancelled'})


def _build_response(status_code: HTTPStatus, body: dict[str, Any]) -> dict[str, Any]:
    """Build API Gateway response."""
    headers = get_cors_headers(None)
    headers['Content-Type'] = 'application/json'
    return {
        'statusCode': status_code.value,
        'headers': headers,
        'body': json.dumps(_convert_decimal_to_float(body)),
    }


__all__ = ['lambda_handler']
