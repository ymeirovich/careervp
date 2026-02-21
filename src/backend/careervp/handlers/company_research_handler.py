"""
Lambda handler for the Company Research API endpoint.
Follows Handler -> Logic -> DAL pattern per AGENTS.md.
"""

from __future__ import annotations

import asyncio
import json
import os
from http import HTTPStatus
from typing import Any

import boto3
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from boto3.dynamodb.conditions import Attr, Key
from pydantic import ValidationError

from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.logic.company_research import research_company
from careervp.models.company import CompanyResearchRequest
from careervp.models.result import Result, ResultCode

COMPANY_RESEARCH_ARTIFACT_PREFIX = 'ARTIFACT#COMPANY_RESEARCH#'
COMPANY_RESEARCH_KB_PREFIX = 'COMPANY_RESEARCH#'


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Route company research requests based on HTTP method/path."""
    _ = context
    method = _resolve_http_method(event)
    path = str(event.get('path') or '').rstrip('/')

    if method == 'OPTIONS':
        return _build_response(HTTPStatus.OK, {'status': 'ok'})

    if method == 'GET' and _is_get_company_research_path(path, event):
        metrics.add_metric(name='CompanyResearchGetRequests', unit=MetricUnit.Count, value=1)
        return get_company_research(event)

    if method == 'POST':
        metrics.add_metric(name='CompanyResearchRequests', unit=MetricUnit.Count, value=1)
        return _fetch_company_research(event)

    return _build_response(
        HTTPStatus.NOT_FOUND,
        {
            'error': 'Endpoint not found',
            'code': ResultCode.INVALID_INPUT,
        },
    )


def _fetch_company_research(event: dict[str, Any]) -> dict[str, Any]:
    """Handle POST /company-research/fetch requests."""
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        return _build_response(
            HTTPStatus.UNAUTHORIZED,
            {
                'error': 'Authentication required',
                'code': ResultCode.UNAUTHORIZED,
            },
        )

    request_result = _parse_request(event)
    if not request_result.success or not request_result.data:
        metrics.add_metric(name='CompanyResearchFailures', unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.BAD_REQUEST,
            {
                'error': request_result.error or 'Invalid request payload',
                'code': ResultCode.INVALID_INPUT,
            },
        )

    research_result = asyncio.run(research_company(request_result.data))

    if not research_result.success or not research_result.data:
        metrics.add_metric(name='CompanyResearchFailures', unit=MetricUnit.Count, value=1)
        status_code = _map_result_code_to_status(research_result.code)
        return _build_response(
            status_code,
            {
                'error': research_result.error or 'Company research failed',
                'code': research_result.code or ResultCode.INTERNAL_ERROR,
            },
        )

    metrics.add_metric(name='CompanyResearchSuccess', unit=MetricUnit.Count, value=1)
    metrics.add_metric(
        name=f'ResearchSource_{research_result.data.source.value.upper()}',
        unit=MetricUnit.Count,
        value=1,
    )

    status_code = _map_result_code_to_status(research_result.code)
    return _build_response(status_code, research_result.data.model_dump())


def get_company_research(event: dict[str, Any]) -> dict[str, Any]:
    """Handle GET /company-research/{jobId} requests."""
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        return _build_response(
            HTTPStatus.UNAUTHORIZED,
            {
                'error': 'Missing or invalid authentication token',
                'code': ResultCode.UNAUTHORIZED,
            },
        )

    job_id = _extract_job_id(event)
    if not job_id:
        return _build_response(
            HTTPStatus.BAD_REQUEST,
            {
                'error': 'Missing jobId path parameter',
                'code': ResultCode.MISSING_REQUIRED_FIELD,
            },
        )

    item = _get_company_research_item(user_id=user_id, job_id=job_id)
    if item is None:
        return _build_response(
            HTTPStatus.NOT_FOUND,
            {
                'error': 'Company research not found',
                'code': ResultCode.INVALID_INPUT,
            },
        )

    payload = _build_company_research_response(item=item, job_id=job_id)
    # Explicitly return 200 OK for GET (never 201).
    return _build_response(HTTPStatus.OK, payload)


def _parse_request(event: dict[str, Any]) -> Result[CompanyResearchRequest]:
    """Parse body JSON into CompanyResearchRequest."""
    body_content = event.get('body', '{}')
    try:
        payload = json.loads(body_content or '{}')
    except (TypeError, json.JSONDecodeError) as exc:
        logger.warning('Invalid JSON body', error=str(exc))
        return Result(success=False, error='Invalid JSON request body', code=ResultCode.INVALID_INPUT)

    try:
        request = CompanyResearchRequest(**payload)
    except ValidationError as exc:
        logger.warning('CompanyResearchRequest validation failed', errors=exc.errors())
        return Result(success=False, error='Request validation failed', code=ResultCode.INVALID_INPUT)

    return Result(success=True, data=request, code=ResultCode.SUCCESS)


def _resolve_http_method(event: dict[str, Any]) -> str:
    raw_method = event.get('httpMethod')
    if isinstance(raw_method, str) and raw_method.strip():
        return raw_method.strip().upper()
    # Compatibility with older tests/events that omit httpMethod for POST handlers.
    if event.get('body') is not None:
        return 'POST'
    return 'GET'


def _is_get_company_research_path(path: str, event: dict[str, Any]) -> bool:
    if path.startswith('/company-research/') and path != '/company-research/fetch':
        return True
    path_parameters = event.get('pathParameters')
    return isinstance(path_parameters, dict) and isinstance(path_parameters.get('jobId'), str)


def _extract_claim_user_id(claims: Any) -> str | None:
    if not isinstance(claims, dict):
        return None
    for claim_key in ('sub', 'user_id', 'cognito:username'):
        claim_value = claims.get(claim_key)
        if isinstance(claim_value, str) and claim_value.strip():
            return claim_value.strip()
    return None


def _extract_user_id_from_authorizer(event: dict[str, Any]) -> str | None:
    request_context = event.get('requestContext')
    if not isinstance(request_context, dict):
        return None

    authorizer = request_context.get('authorizer')
    if not isinstance(authorizer, dict):
        return None

    claim_user_id = _extract_claim_user_id(authorizer.get('claims'))
    if claim_user_id:
        return claim_user_id

    jwt_context = authorizer.get('jwt')
    if isinstance(jwt_context, dict):
        jwt_claims = jwt_context.get('claims')
        jwt_user_id = _extract_claim_user_id(jwt_claims)
        if jwt_user_id:
            return jwt_user_id

    for direct_key in ('user_id', 'principalId', 'principal_id'):
        direct_value = authorizer.get(direct_key)
        if isinstance(direct_value, str) and direct_value.strip():
            return direct_value.strip()
    return None


def _authorizer_disabled() -> bool:
    return False


def _get_header_case_insensitive(headers: dict[str, Any], target_header: str) -> str | None:
    normalized_target = target_header.lower()
    for key, value in headers.items():
        if isinstance(key, str) and key.lower() == normalized_target and isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_authenticated_user_id(event: dict[str, Any]) -> str | None:
    authorizer_user_id = _extract_user_id_from_authorizer(event)
    if authorizer_user_id:
        return authorizer_user_id

    if not _authorizer_disabled():
        return None

    headers = event.get('headers')
    if isinstance(headers, dict):
        return _get_header_case_insensitive(headers, 'x-user-id')
    return None


def _extract_job_id(event: dict[str, Any]) -> str | None:
    path_parameters = event.get('pathParameters')
    if isinstance(path_parameters, dict):
        for key in ('jobId', 'job_id'):
            value = path_parameters.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    path = str(event.get('path') or '').rstrip('/')
    if path.startswith('/company-research/'):
        candidate = path.removeprefix('/company-research/').strip()
        if candidate and candidate != 'fetch':
            return candidate
    return None


def _get_company_research_item(user_id: str, job_id: str) -> dict[str, Any] | None:
    table_candidates = _resolve_table_candidates()

    for table_name in table_candidates:
        item = _get_item_from_table(table_name=table_name, user_id=user_id, job_id=job_id)
        if item is not None:
            return item
    return None


def _resolve_table_candidates() -> list[str]:
    candidates: list[str] = []
    for env_key in ('DYNAMODB_TABLE_NAME', 'TABLE_NAME', 'KNOWLEDGE_TABLE_NAME'):
        value = os.getenv(env_key)
        if isinstance(value, str) and value.strip() and value.strip() not in candidates:
            candidates.append(value.strip())
    return candidates


def _get_item_from_table(table_name: str, user_id: str, job_id: str) -> dict[str, Any] | None:
    table = boto3.resource('dynamodb').Table(table_name)

    candidate_keys = [
        {'pk': user_id, 'sk': f'{COMPANY_RESEARCH_ARTIFACT_PREFIX}{job_id}'},
        {'pk': user_id, 'sk': f'{COMPANY_RESEARCH_KB_PREFIX}{job_id}'},
        {'pk': f'USER#{user_id}', 'sk': f'{COMPANY_RESEARCH_KB_PREFIX}{job_id}'},
    ]

    for key in candidate_keys:
        try:
            response = table.get_item(Key=key)
        except Exception:
            response = {}
        item = response.get('Item') if isinstance(response, dict) else None
        if isinstance(item, dict):
            return item

    query_candidates = [
        (user_id, COMPANY_RESEARCH_ARTIFACT_PREFIX),
        (user_id, COMPANY_RESEARCH_KB_PREFIX),
        (f'USER#{user_id}', COMPANY_RESEARCH_KB_PREFIX),
    ]

    for partition_key, prefix in query_candidates:
        try:
            query_response = table.query(
                KeyConditionExpression=Key('pk').eq(partition_key) & Key('sk').begins_with(prefix),
                FilterExpression=Attr('sk').contains(job_id),
                Limit=1,
            )
        except Exception:
            continue

        items = query_response.get('Items') if isinstance(query_response, dict) else None
        if isinstance(items, list) and items and isinstance(items[0], dict):
            return items[0]

    return None


def _build_company_research_response(item: dict[str, Any], job_id: str) -> dict[str, Any]:
    nested_payload = _coerce_dict(item.get('research_data')) or _coerce_dict(item.get('company_research')) or {}

    research_id = (
        _coerce_str(item.get('company_research_id'))
        or _coerce_str(nested_payload.get('company_research_id'))
        or _coerce_str(item.get('job_id'))
        or job_id
    )

    recent_news = _normalize_recent_news(item.get('recent_news'))
    if not recent_news:
        recent_news = _normalize_recent_news(nested_payload.get('recent_news'))

    return {
        'id': research_id,
        'company_name': _coerce_str(item.get('company_name')) or _coerce_str(nested_payload.get('company_name')) or '',
        'mission': _coerce_str(item.get('mission')) or _coerce_str(nested_payload.get('mission')) or '',
        'values': _coerce_list_of_strings(item.get('values')) or _coerce_list_of_strings(nested_payload.get('values')),
        'recent_news': recent_news,
        'culture': _coerce_str(item.get('culture'))
        or _coerce_str(nested_payload.get('culture'))
        or _coerce_str(item.get('overview'))
        or _coerce_str(nested_payload.get('overview'))
        or '',
        'products': _coerce_list_of_strings(item.get('products'))
        or _coerce_list_of_strings(nested_payload.get('products'))
        or _coerce_list_of_strings(nested_payload.get('strategic_priorities')),
        'funding_status': _coerce_str(item.get('funding_status'))
        or _coerce_str(nested_payload.get('funding_status'))
        or _coerce_str(nested_payload.get('financial_summary'))
        or '',
        'size_range': _coerce_str(item.get('size_range')) or _coerce_str(nested_payload.get('size_range')) or '',
        'industry': _coerce_str(item.get('industry')) or _coerce_str(nested_payload.get('industry')) or '',
    }


def _normalize_recent_news(raw_news: Any) -> list[dict[str, str]]:
    if not isinstance(raw_news, list):
        return []

    normalized: list[dict[str, str]] = []
    for entry in raw_news:
        if isinstance(entry, dict):
            title = _coerce_str(entry.get('title')) or ''
            date = _coerce_str(entry.get('date')) or ''
            if title:
                normalized.append({'title': title, 'date': date})
        elif isinstance(entry, str) and entry.strip():
            normalized.append({'title': entry.strip(), 'date': ''})
    return normalized


def _coerce_str(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            return stripped
    return None


def _coerce_dict(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    return None


def _coerce_list_of_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized = [str(entry).strip() for entry in value if str(entry).strip()]
    return normalized


def _map_result_code_to_status(code: str | None) -> HTTPStatus:
    """Map Result code strings to HTTP status codes."""
    mapping = {
        ResultCode.RESEARCH_COMPLETE: HTTPStatus.OK,
        ResultCode.SUCCESS: HTTPStatus.OK,
        ResultCode.INVALID_INPUT: HTTPStatus.BAD_REQUEST,
        ResultCode.SCRAPE_FAILED: HTTPStatus.PARTIAL_CONTENT,
        ResultCode.SEARCH_FAILED: HTTPStatus.PARTIAL_CONTENT,
        ResultCode.ALL_SOURCES_FAILED: HTTPStatus.SERVICE_UNAVAILABLE,
        ResultCode.TIMEOUT: HTTPStatus.GATEWAY_TIMEOUT,
        ResultCode.LLM_API_ERROR: HTTPStatus.BAD_GATEWAY,
    }
    if code in mapping:
        return mapping[code]
    if code is None:
        return HTTPStatus.OK
    return HTTPStatus.INTERNAL_SERVER_ERROR


def _build_response(status_code: HTTPStatus, body: dict[str, Any]) -> dict[str, Any]:
    """Build an API Gateway compatible response."""
    return {
        'statusCode': status_code.value,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
        },
        'body': json.dumps(body, default=str),
    }


__all__ = ['lambda_handler', 'get_company_research']
