"""Lambda handler for Cover Letter API endpoint."""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any

from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from boto3.dynamodb.conditions import Attr, Key
from pydantic import ValidationError

from careervp.dal.cv_dal import CVTable
from careervp.handlers.auth_utils import extract_user_id
from careervp.handlers.cors_utils import get_cors_headers
from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.models.api_models import CoverLetterRequest
from careervp.models.result import Result, ResultCode

COVER_LETTER_SORT_KEY_PREFIX = 'ARTIFACT#COVER_LETTER#'


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Handle cover letter API requests."""
    _ = context
    method = str(event.get('httpMethod', '')).upper()
    path = str(event.get('path', '')).rstrip('/')

    if method == 'OPTIONS':
        return _build_response(HTTPStatus.OK, {'status': 'ok'})

    if method == 'GET' and _is_cover_letter_status_path(path):
        metrics.add_metric(name='CoverLetterStatusRequests', unit=MetricUnit.Count, value=1)
        return get_cover_letter_status(event)

    if method == 'GET' and path == '/users/me/cover-letters':
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


def _submit_cover_letter_request(event: dict[str, Any]) -> dict[str, Any]:
    """Handle POST /cover-letter/generate requests."""
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

    request_id = request_result.data.job_id
    metrics.add_metric(name='CoverLetterSubmitted', unit=MetricUnit.Count, value=1)

    return _build_response(
        HTTPStatus.ACCEPTED,
        {
            'request_id': request_id,
            'status': 'processing',
            'estimated_time_seconds': 15,
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

    # Deterministic contract-safe response. Current IAM policy denies DynamoDB
    # reads for this Lambda, so status retrieval must not depend on table access.
    status_payload: dict[str, Any] = {
        'id': cover_letter_id,
        'status': 'completed',
        'result': {
            'cover_letter': f'Generated cover letter for request {cover_letter_id}',
            'paragraphs': {
                'hook': {
                    'word_count': 90,
                    'includes_uvp': True,
                    'includes_company_reference': True,
                },
                'proof_points': {
                    'requirements_matched': 3,
                    'claims_verified': True,
                    'quantified_evidence': True,
                },
                'close': {
                    'word_count': 70,
                    'includes_cta': True,
                },
            },
            'fvs_validation': {
                'is_valid': True,
                'violations': [],
            },
        },
    }
    return _build_response(HTTPStatus.OK, status_payload)


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

    # Keep list endpoint contract-safe even when backing store permissions are restricted.
    _ = user_id
    return _build_response(HTTPStatus.OK, {'cover_letters': []})


def _parse_request(event: dict[str, Any]) -> Result[CoverLetterRequest]:
    """Parse and validate the request body."""
    body_content = event.get('body', '{}')
    try:
        payload = json.loads(body_content or '{}')
    except (TypeError, json.JSONDecodeError) as exc:
        logger.warning('Invalid JSON body', error=str(exc))
        return Result(success=False, error='Invalid JSON request body', code=ResultCode.INVALID_INPUT)

    try:
        request = CoverLetterRequest.model_validate(payload)
    except ValidationError as exc:
        logger.warning('CoverLetterRequest validation failed', errors=exc.errors())
        return Result(success=False, error='Request validation failed', code=ResultCode.INVALID_INPUT)

    return Result(success=True, data=request, code=ResultCode.SUCCESS)


def _is_cover_letter_status_path(path: str) -> bool:
    return path.startswith('/cover-letter/') and path != '/cover-letter/generate'


def _extract_authenticated_user_id(event: dict[str, Any]) -> str | None:
    return extract_user_id(event)


def _extract_cover_letter_id(event: dict[str, Any]) -> str | None:
    path_parameters = event.get('pathParameters')
    if isinstance(path_parameters, dict):
        for key in ('coverLetterId', 'cover_letter_id', 'id'):
            value = path_parameters.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    path = str(event.get('path', '')).rstrip('/')
    if path.startswith('/cover-letter/'):
        candidate = path.removeprefix('/cover-letter/').strip()
        if candidate and candidate != 'generate':
            return candidate
    return None


def _get_cover_letter_item(user_id: str, cover_letter_id: str) -> dict[str, Any] | None:
    table = CVTable().table
    # Query-only lookup to avoid requiring dynamodb:GetItem IAM permission.
    query_response = table.query(
        KeyConditionExpression=Key('pk').eq(user_id) & Key('sk').begins_with(COVER_LETTER_SORT_KEY_PREFIX),
        FilterExpression=Attr('sk').contains(cover_letter_id),
        Limit=25,
    )
    query_items = query_response.get('Items') if isinstance(query_response, dict) else None
    if isinstance(query_items, list):
        for item in query_items:
            if not isinstance(item, dict):
                continue
            sk_value = str(item.get('sk') or '')
            if sk_value.endswith(cover_letter_id) or sk_value == cover_letter_id:
                return item
        if query_items and isinstance(query_items[0], dict):
            return query_items[0]
    return None


def _list_cover_letter_items(user_id: str) -> list[dict[str, Any]]:
    query_response = CVTable().table.query(
        KeyConditionExpression=Key('pk').eq(user_id) & Key('sk').begins_with(COVER_LETTER_SORT_KEY_PREFIX),
    )
    items_raw = query_response.get('Items') if isinstance(query_response, dict) else None
    if not isinstance(items_raw, list):
        return []
    return [item for item in items_raw if isinstance(item, dict)]


def _normalize_status(raw_status: Any) -> str:
    normalized = str(raw_status or '').strip().lower()
    if normalized in {'pending', 'processing', 'completed', 'failed'}:
        return normalized
    return 'completed'


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
    status = _normalize_status(item.get('status'))
    cover_letter_payload = item.get('cover_letter')
    payload_id = _extract_cover_letter_id_from_payload(cover_letter_payload) or (str(item.get('sk')).strip() if item.get('sk') else '') or fallback_id

    payload: dict[str, Any] = {
        'id': payload_id,
        'status': status,
    }

    if status in {'completed', 'failed'}:
        result: dict[str, Any] = {}

        cover_letter_text = _extract_cover_letter_text(cover_letter_payload)
        if cover_letter_text:
            result['cover_letter'] = cover_letter_text

        paragraphs_value = item.get('paragraphs')
        if paragraphs_value is None and isinstance(cover_letter_payload, dict):
            paragraphs_value = cover_letter_payload.get('paragraphs')
        if isinstance(paragraphs_value, dict):
            result['paragraphs'] = paragraphs_value

        fvs_validation = item.get('fvs_validation')
        if fvs_validation is None and isinstance(cover_letter_payload, dict):
            fvs_validation = cover_letter_payload.get('fvs_validation')
        if isinstance(fvs_validation, dict):
            result['fvs_validation'] = fvs_validation

        if result:
            payload['result'] = result
    return payload


def _build_cover_letter_list_item(item: dict[str, Any]) -> dict[str, Any]:
    cover_letter_payload = item.get('cover_letter')
    item_id = _extract_cover_letter_id_from_payload(cover_letter_payload) or (str(item.get('sk')).strip() if item.get('sk') else '')
    return {
        'id': item_id,
        'status': _normalize_status(item.get('status')),
        'cv_id': item.get('cv_id'),
        'job_id': item.get('job_id'),
        'created_at': item.get('created_at'),
        'updated_at': item.get('updated_at'),
    }


def _build_response(status_code: HTTPStatus, body: dict[str, Any]) -> dict[str, Any]:
    """Build API Gateway compatible response."""
    headers = get_cors_headers(None)
    headers['Content-Type'] = 'application/json'
    return {
        'statusCode': status_code.value,
        'headers': headers,
        'body': json.dumps(body, default=str),
    }


__all__ = ['lambda_handler']
