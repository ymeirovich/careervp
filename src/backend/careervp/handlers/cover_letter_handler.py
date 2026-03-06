"""Lambda handler for Cover Letter API endpoint."""

from __future__ import annotations

import asyncio
import json
import os
from decimal import Decimal
from http import HTTPStatus
from typing import Any, cast

from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.handlers.auth_utils import extract_user_id
from careervp.handlers.cors_utils import get_cors_headers
from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.logic.cover_letter import generate_cover_letter
from careervp.models.api_models import CoverLetterRequest
from careervp.models.cover_letter import (
    CoverLetterOptions as LogicCoverLetterOptions,
)
from careervp.models.cover_letter import (
    CoverLetterRequest as LogicCoverLetterRequest,
)
from careervp.models.cv import UserCV
from careervp.models.result import Result, ResultCode


def _convert_decimal_to_float(obj: Any) -> Any:
    """Recursively convert Decimal to float for JSON serialization (mirrors gap_analysis.py)."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _convert_decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_decimal_to_float(i) for i in obj]
    return obj


def _get_dal() -> DynamoDalHandler:
    table_name = os.environ.get('ARTIFACTS_TABLE_NAME') or os.environ.get('DYNAMODB_TABLE_NAME') or os.environ.get('TABLE_NAME') or ''
    resolved_from = (
        'ARTIFACTS_TABLE_NAME'
        if os.environ.get('ARTIFACTS_TABLE_NAME')
        else 'DYNAMODB_TABLE_NAME'
        if os.environ.get('DYNAMODB_TABLE_NAME')
        else 'TABLE_NAME'
        if os.environ.get('TABLE_NAME')
        else 'none'
    )
    logger.debug('Cover letter DAL table resolved', table_name=table_name, resolved_from=resolved_from)
    return DynamoDalHandler(table_name)


class _FallbackVPR:
    """Minimal VPR shim used by cover-letter logic prompt construction."""

    def __init__(self, vpr_id: str, job_id: str) -> None:
        self._vpr_id = vpr_id
        self._job_id = job_id

    def model_dump(self, mode: str = 'json') -> dict[str, Any]:
        _ = mode
        return {
            'vpr_id': self._vpr_id,
            'job_id': self._job_id,
        }


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Handle cover letter API requests and SQS worker events."""
    _ = context

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

    if method == 'GET' and _is_cover_letter_status_path(path):
        metrics.add_metric(name='CoverLetterStatusRequests', unit=MetricUnit.Count, value=1)
        return get_cover_letter_status(event)

    if method == 'GET' and path in {'/users/me/cover-letters', '/cover-letters'}:
        metrics.add_metric(name='CoverLetterListRequests', unit=MetricUnit.Count, value=1)
        return list_cover_letters(event)

    if method == 'POST' and path == '/cover-letter/generate':
        metrics.add_metric(name='CoverLetterRequests', unit=MetricUnit.Count, value=1)
        return _submit_cover_letter_request(event)

    return _build_response(
        HTTPStatus.NOT_FOUND,
        {
            'error': 'Endpoint not found',
            'code': ResultCode.INVALID_INPUT,
        },
    )


def _process_sqs_event(event: dict[str, Any]) -> dict[str, Any]:
    """Process SQS messages for async cover letter generation."""
    for record in event.get('Records', []):
        body = json.loads(record.get('body', '{}'))
        job_id = body.get('job_id', '')
        user_id = body.get('user_id', '')
        request_data = body.get('request_data', {})

        if not job_id or not user_id:
            logger.error('SQS message missing job_id or user_id', body=body)
            continue

        logger.append_keys(job_id=job_id, user_id=user_id)
        logger.info('Processing cover letter SQS job', job_id=job_id)

        try:
            _generate_and_persist_from_sqs(job_id=job_id, user_id=user_id, request_data=request_data)
        except Exception as exc:
            logger.error('Cover letter SQS job failed', job_id=job_id, error=str(exc), exc_info=True)
            _update_artifact_status(user_id=user_id, job_id=job_id, status='FAILED')
            raise

    return {'statusCode': 200, 'body': 'OK'}


def _generate_and_persist_from_sqs(
    job_id: str,
    user_id: str,
    request_data: dict[str, Any],
) -> None:
    """Load pending record, generate cover letter, persist result."""
    dal = _get_dal()

    # Update status to PROCESSING
    _update_artifact_status(user_id=user_id, job_id=job_id, status='PROCESSING')

    # Validate the request data
    api_request = CoverLetterRequest.model_validate(request_data)

    # Load user CV
    user_cv = _load_user_cv(dal=dal, user_id=user_id)
    if user_cv is None or user_cv.user_id != user_id:
        raise ValueError(f'No CV found for user {user_id}')

    # Generate cover letter using existing logic
    generation_result = _generate_cover_letter_result(
        api_request=api_request,
        user_id=user_id,
        user_cv=user_cv,
    )

    if not generation_result.success or generation_result.data is None:
        raise RuntimeError(f'Cover letter generation failed: {generation_result.error}')

    cover_letter_model = generation_result.data.cover_letter
    if cover_letter_model is None:
        raise RuntimeError('Cover letter generation returned no content')

    # Persist the result
    cover_letter_payload = cover_letter_model.model_dump(mode='json')
    try:
        dal.save_cover_letter(
            cover_letter=cover_letter_payload,
            user_id=user_id,
            cv_id=api_request.cv_id,
            job_id=api_request.job_id,
        )
    except Exception as save_exc:
        logger.error(
            'save_cover_letter failed in SQS worker; marking job FAILED',
            job_id=job_id,
            user_id=user_id,
            error=f'{type(save_exc).__name__}: {save_exc}',
            exc_info=True,
        )
        _update_artifact_status(user_id=user_id, job_id=job_id, status='FAILED')
        raise RuntimeError(f'Persistence failed for cover letter job {job_id}: {save_exc}') from save_exc

    # Update the artifact record to COMPLETED only after successful persistence
    _update_artifact_status(
        user_id=user_id,
        job_id=job_id,
        status='COMPLETED',
        result_data=_convert_decimal_to_float(cover_letter_payload),
    )

    metrics.add_metric(name='CoverLetterWorkerGenerated', unit=MetricUnit.Count, value=1)
    logger.info('Cover letter SQS job completed', job_id=job_id)


def _update_artifact_status(
    user_id: str,
    job_id: str,
    status: str,
    result_data: dict[str, Any] | None = None,
) -> None:
    """Update cover letter artifact status in DynamoDB."""
    import datetime as _dt

    import boto3 as _boto3

    table_name = os.environ.get('ARTIFACTS_TABLE_NAME') or os.environ.get('DYNAMODB_TABLE_NAME') or os.environ.get('TABLE_NAME') or ''
    table = _boto3.resource('dynamodb').Table(table_name)
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()

    update_expr = 'SET #s = :status, updated_at = :now'
    attr_names: dict[str, str] = {'#s': 'status'}
    attr_values: dict[str, Any] = {':status': status, ':now': now}

    if result_data is not None:
        update_expr += ', cover_letter = :result'
        attr_values[':result'] = result_data

    artifact_id = f'ARTIFACT#COVER_LETTER#{job_id}'
    try:
        table.update_item(
            Key={'applicationId': user_id, 'artifactId': artifact_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=attr_names,
            ExpressionAttributeValues=attr_values,
        )
    except Exception as exc:
        error_response = getattr(exc, 'response', {}) if hasattr(exc, 'response') else {}
        error_code = ((error_response.get('Error') or {}).get('Code')) if isinstance(error_response, dict) else None
        if error_code == 'ValidationException':
            table.update_item(
                Key={'pk': user_id, 'sk': artifact_id},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=attr_names,
                ExpressionAttributeValues=attr_values,
            )
            return
        logger.error('Failed to update artifact status', job_id=job_id, error=str(exc))
        raise


def _submit_cover_letter_request(event: dict[str, Any]) -> dict[str, Any]:
    """Handle POST /cover-letter/generate requests."""
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        metrics.add_metric(name='CoverLetterFailures', unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.UNAUTHORIZED,
            {
                'error': 'Missing or invalid authentication token',
                'code': ResultCode.UNAUTHORIZED,
            },
        )

    request_result = _parse_request(event)
    if not request_result.success or not request_result.data:
        metrics.add_metric(name='CoverLetterFailures', unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.BAD_REQUEST,
            {
                'error': request_result.error or 'Invalid request payload',
                'code': ResultCode.INVALID_INPUT,
            },
        )
    api_request = request_result.data

    dal = _get_dal()
    try:
        user_cv = _load_user_cv(dal=dal, user_id=user_id)
    except Exception as e:
        logger.error('Failed to load user CV for cover letter', user_id=user_id, error=str(e))
        return _build_response(
            HTTPStatus.UNPROCESSABLE_ENTITY, {'error': 'Could not load your CV. Please upload a CV before generating a cover letter.'}
        )
    if user_cv is None or user_cv.user_id != user_id:
        return _build_response(HTTPStatus.NOT_FOUND, {'error': 'No CV found for your account. Please upload a CV first.'})

    try:
        generation_result = _generate_cover_letter_result(
            api_request=api_request,
            user_id=user_id,
            user_cv=user_cv,
        )
    except Exception as e:
        logger.error('Cover letter generation failed', user_id=user_id, error=str(e), exc_info=True)
        return _build_response(HTTPStatus.SERVICE_UNAVAILABLE, {'error': 'Cover letter generation failed. Please try again.'})
    if not generation_result.success or generation_result.data is None:
        metrics.add_metric(name='CoverLetterFailures', unit=MetricUnit.Count, value=1)
        return _build_generation_error_response(generation_result)

    cover_letter_model = generation_result.data.cover_letter
    if cover_letter_model is None:
        metrics.add_metric(name='CoverLetterFailures', unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {
                'error': 'Cover letter generation returned no content',
                'code': ResultCode.INTERNAL_ERROR,
            },
        )

    cover_letter_payload = cover_letter_model.model_dump(mode='json')
    try:
        save_result = dal.save_cover_letter(
            cover_letter=cover_letter_payload,
            user_id=user_id,
            cv_id=api_request.cv_id,
            job_id=api_request.job_id,
        )
    except Exception as exc:
        logger.error('Cover letter persistence failed', user_id=user_id, error=str(exc), exc_info=True)
        save_result = Result(success=False, error='persist failed', code=ResultCode.DYNAMODB_ERROR)
    if not save_result.success:
        # AC-CL-303: Persistence failure must NOT return synthetic completed response
        metrics.add_metric(name='CoverLetterPersistenceFailure', unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {
                'error': 'Cover letter generated but failed to save. Please try again.',
                'code': ResultCode.DYNAMODB_ERROR,
            },
        )

    artifact_id = str(cover_letter_payload.get('cover_letter_id', '')).strip()
    metrics.add_metric(name='CoverLetterGenerated', unit=MetricUnit.Count, value=1)
    return _build_response(
        HTTPStatus.OK,
        {
            'artifact_id': artifact_id,
            'status': 'completed',
        },
    )


def get_cover_letter_status(event: dict[str, Any]) -> dict[str, Any]:
    """Handle GET /cover-letter/{coverLetterId} requests."""
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        return _build_response(
            HTTPStatus.UNAUTHORIZED,
            {
                'error': 'Missing or invalid authentication token',
                'code': ResultCode.UNAUTHORIZED,
            },
        )

    cover_letter_id = _extract_cover_letter_id(event)
    if not cover_letter_id:
        return _build_response(
            HTTPStatus.BAD_REQUEST,
            {
                'error': 'Missing coverLetterId path parameter',
                'code': ResultCode.MISSING_REQUIRED_FIELD,
            },
        )

    matching_item = _find_cover_letter_item(user_id=user_id, cover_letter_id=cover_letter_id)
    if matching_item is None:
        metrics.add_metric(name='CoverLetterStatusNotFound', unit=MetricUnit.Count, value=1)
        logger.info('Cover letter artifact not found', cover_letter_id=cover_letter_id, user_id=user_id)
        return _build_response(
            HTTPStatus.NOT_FOUND,
            {
                'error': 'Cover letter not found',
                'code': ResultCode.COVER_LETTER_NOT_FOUND,
            },
        )

    return _build_response(HTTPStatus.OK, _build_cover_letter_status_payload(matching_item, cover_letter_id))


def list_cover_letters(event: dict[str, Any]) -> dict[str, Any]:
    """Handle GET /users/me/cover-letters requests."""
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        return _build_response(
            HTTPStatus.UNAUTHORIZED,
            {
                'error': 'Missing or invalid authentication token',
                'code': ResultCode.UNAUTHORIZED,
            },
        )

    items = _list_cover_letter_items(user_id)
    payload = [_build_cover_letter_list_item(item) for item in items]
    return _build_response(HTTPStatus.OK, {'cover_letters': payload})


def _parse_request(event: dict[str, Any]) -> Result[CoverLetterRequest]:
    """Parse and validate the request body."""
    body_content = event.get('body', '{}')
    try:
        payload = json.loads(body_content or '{}')
    except (TypeError, json.JSONDecodeError):
        logger.warning('Invalid JSON body for cover letter request')
        return Result(success=False, error='Invalid JSON request body', code=ResultCode.INVALID_INPUT)

    try:
        request = CoverLetterRequest.model_validate(payload)
    except ValidationError:
        logger.warning('CoverLetterRequest validation failed')
        return Result(success=False, error='Request validation failed', code=ResultCode.INVALID_INPUT)

    return Result(success=True, data=request, code=ResultCode.SUCCESS)


def _is_cover_letter_status_path(path: str) -> bool:
    return path.startswith('/cover-letter/') and path != '/cover-letter/generate'


def _extract_authenticated_user_id(event: dict[str, Any]) -> str | None:
    return extract_user_id(event)


def _extract_cover_letter_id(event: dict[str, Any]) -> str | None:
    path_parameters = event.get('pathParameters')
    if isinstance(path_parameters, dict):
        for key in ('coverLetterId', 'cover_letter_id', 'id', 'job_id', 'jobId'):
            value = path_parameters.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    path = str(event.get('path', '')).rstrip('/')
    if path.startswith('/cover-letter/'):
        candidate = path.removeprefix('/cover-letter/').strip()
        if candidate.endswith('/status'):
            candidate = candidate[: -len('/status')]
        if candidate and candidate != 'generate':
            return candidate
    return None


def _load_user_cv(dal: DynamoDalHandler, user_id: str) -> UserCV | None:
    raw_cv = dal.get_cv(user_id)
    if isinstance(raw_cv, UserCV):
        return raw_cv
    if isinstance(raw_cv, dict):
        try:
            return UserCV.model_validate(raw_cv)
        except ValidationError:
            logger.warning('Failed to coerce DynamoDB CV payload to UserCV')
            return None
    return None


def _to_logic_options(api_request: CoverLetterRequest) -> LogicCoverLetterOptions | None:
    if api_request.options is None:
        return None
    return LogicCoverLetterOptions.model_validate(api_request.options.model_dump(mode='json'))


def _generate_cover_letter_result(
    api_request: CoverLetterRequest,
    user_id: str,
    user_cv: UserCV,
) -> Result[Any]:
    logic_request = LogicCoverLetterRequest(
        user_id=user_id,
        cv_id=api_request.cv_id,
        job_id=api_request.job_id,
        vpr_id=api_request.vpr_id,
        company_name=f'Company for {api_request.job_id}',
        job_title=f'Role for {api_request.job_id}',
        job_description=f'Job description for {api_request.job_id}',
        gap_response_ids=list(api_request.gap_response_ids),
        company_research_id=api_request.company_research_id,
        options=_to_logic_options(api_request),
    )
    maybe_async_result = generate_cover_letter(
        request=logic_request,
        user_cv=user_cv,
        vpr=cast(Any, _FallbackVPR(api_request.vpr_id, api_request.job_id)),
    )
    if asyncio.iscoroutine(maybe_async_result):
        return asyncio.run(maybe_async_result)
    if isinstance(maybe_async_result, Result):
        return maybe_async_result
    return Result(
        success=False,
        error='Invalid cover letter generation response',
        code=ResultCode.INTERNAL_ERROR,
    )


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
            'error': generation_result.error or 'Cover letter generation failed',
            'code': generation_result.code,
        },
    )


def _find_cover_letter_item(user_id: str, cover_letter_id: str) -> dict[str, Any] | None:
    """Find a cover letter artifact using canonical key lookup with legacy fallback.

    Phase A dual-read strategy:
      1. Try canonical read: applicationId=user_id, artifactId=ARTIFACT#COVER_LETTER#{cover_letter_id}
      2. If canonical miss and COVER_LETTER_LEGACY_READ_ENABLED=true, scan legacy items
      3. Fall back to list scan for edge cases (sync-path items with different sk format)
    """
    dal = _get_dal()

    # Canonical read: construct the expected artifactId
    artifact_id = f'ARTIFACT#COVER_LETTER#{cover_letter_id}'
    canonical_result = dal.read_cover_letter_by_artifact_id(
        application_id=user_id,
        artifact_id=artifact_id,
    )
    if canonical_result.success and canonical_result.data is not None:
        return canonical_result.data

    # Phase A fallback: scan list for matching item (pre-migration pk/sk records)
    logger.info(
        'Canonical cover letter read missed; using list-scan fallback (Phase A)',
        cover_letter_id=cover_letter_id,
        user_id=user_id,
        canonical_result_code=getattr(canonical_result, 'code', None),
    )
    metrics.add_metric(name='CoverLetterCanonicalReadFallback', unit=MetricUnit.Count, value=1)
    items = _list_cover_letter_items(user_id)
    for item in items:
        if _matches_cover_letter_id(item, cover_letter_id):
            return item
    return None


def _list_cover_letter_items(user_id: str) -> list[dict[str, Any]]:
    dal = _get_dal()
    result = dal.list_cover_letters_canonical(user_id)
    if result.success and isinstance(result.data, list):
        return [item for item in result.data if isinstance(item, dict)]
    return []


def _matches_cover_letter_id(item: dict[str, Any], cover_letter_id: str) -> bool:
    # Match by full sk (e.g. ARTIFACT#COVER_LETTER#cv-1#job-1#v1)
    if str(item.get('sk', '')).strip() == cover_letter_id:
        return True

    # Match by job_id field (async path: request_id == job_id UUID)
    if str(item.get('job_id', '')).strip() == cover_letter_id:
        return True

    # Match by artifactId attribute (written by submit handler)
    artifact_id_attr = str(item.get('artifactId', '')).strip()
    if artifact_id_attr == cover_letter_id:
        return True
    if artifact_id_attr == f'ARTIFACT#COVER_LETTER#{cover_letter_id}':
        return True

    nested_payload = item.get('cover_letter')
    nested_id = _extract_cover_letter_id_from_payload(nested_payload)
    if nested_id == cover_letter_id:
        return True

    direct_id = _extract_cover_letter_id_from_payload(item)
    return direct_id == cover_letter_id


def _normalize_status(raw_status: Any) -> str:
    normalized = str(raw_status or '').strip().lower()
    if normalized in {'pending', 'processing', 'completed', 'failed'}:
        return normalized
    if normalized:
        logger.warning('Unexpected cover letter status value', raw_status=raw_status)
    return 'pending'


def _extract_cover_letter_text(cover_letter_payload: Any) -> str | None:
    if isinstance(cover_letter_payload, str) and cover_letter_payload.strip():
        return cover_letter_payload.strip()

    if isinstance(cover_letter_payload, dict):
        for key in ('cover_letter', 'full_text', 'text'):
            candidate = cover_letter_payload.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    return None


def _extract_cover_letter_id_from_payload(cover_letter_payload: Any) -> str | None:
    if isinstance(cover_letter_payload, dict):
        for key in ('cover_letter_id', 'id'):
            candidate = cover_letter_payload.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    return None


def _build_cover_letter_status_payload(item: dict[str, Any], fallback_id: str) -> dict[str, Any]:
    nested_payload = item.get('cover_letter')
    payload_source = nested_payload if isinstance(nested_payload, dict) else item

    payload_id = (
        _extract_cover_letter_id_from_payload(payload_source)
        or _extract_cover_letter_id_from_payload(nested_payload)
        or str(item.get('job_id', '')).strip()
        or (str(item.get('sk', '')).strip() if item.get('sk') else '')
        or fallback_id
    )
    status = _normalize_status(item.get('status'))

    payload: dict[str, Any] = {
        'id': payload_id,
        'status': status,
    }

    if status in {'completed', 'failed'}:
        result: dict[str, Any] = {}

        cover_letter_text = _extract_cover_letter_text(payload_source) or _extract_cover_letter_text(nested_payload)
        if cover_letter_text:
            result['cover_letter'] = cover_letter_text

        paragraphs_value = item.get('paragraphs')
        if paragraphs_value is None and isinstance(payload_source, dict):
            paragraphs_value = payload_source.get('paragraphs')
        if isinstance(paragraphs_value, dict):
            result['paragraphs'] = paragraphs_value

        fvs_validation = item.get('fvs_validation')
        if fvs_validation is None and isinstance(payload_source, dict):
            fvs_validation = payload_source.get('fvs_validation')
        if isinstance(fvs_validation, dict):
            result['fvs_validation'] = fvs_validation

        if result:
            payload['result'] = result
    return payload


def _build_cover_letter_list_item(item: dict[str, Any]) -> dict[str, Any]:
    nested_payload = item.get('cover_letter')
    payload_source = nested_payload if isinstance(nested_payload, dict) else item

    # For async-path items (no nested cover_letter yet), expose job_id as the id
    # so it matches the request_id returned by POST /cover-letter/generate.
    # For sync-path items, cover_letter_id from the nested payload takes priority.
    item_id = (
        _extract_cover_letter_id_from_payload(payload_source)
        or _extract_cover_letter_id_from_payload(nested_payload)
        or str(item.get('job_id', '')).strip()
        or (str(item.get('sk', '')).strip() if item.get('sk') else '')
    )
    cv_id = item.get('cv_id')
    if cv_id is None and isinstance(payload_source, dict):
        cv_id = payload_source.get('cv_id')
    job_id = item.get('job_id')
    if job_id is None and isinstance(payload_source, dict):
        job_id = payload_source.get('job_id')
    created_at = item.get('created_at')
    if created_at is None and isinstance(payload_source, dict):
        created_at = payload_source.get('created_at')

    return {
        'id': item_id,
        'status': _normalize_status(item.get('status')),
        'cv_id': cv_id,
        'job_id': job_id,
        'created_at': created_at,
        'updated_at': item.get('updated_at'),
    }


def _build_default_cover_letter_status_payload(cover_letter_id: str) -> dict[str, Any]:
    return {
        'id': cover_letter_id,
        'status': 'completed',
        'result': {
            'cover_letter': (
                'Dear Hiring Team,\n\n'
                'I am excited to apply for this role because it aligns with my experience delivering '
                'high-impact engineering outcomes in fast-moving environments. In previous roles I led '
                'cross-functional efforts that improved reliability, reduced delivery risk, and produced '
                'measurable business results. I would welcome the opportunity to bring the same ownership, '
                'technical rigor, and collaboration to your team.\n\n'
                'Sincerely,\n'
                'Candidate'
            ),
        },
    }


def _build_response(status_code: HTTPStatus, body: dict[str, Any]) -> dict[str, Any]:
    """Build API Gateway compatible response."""
    headers = get_cors_headers(None)
    headers['Content-Type'] = 'application/json'
    return {
        'statusCode': status_code.value,
        'headers': headers,
        'body': json.dumps(_convert_decimal_to_float(body)),
    }


__all__ = ['lambda_handler']
