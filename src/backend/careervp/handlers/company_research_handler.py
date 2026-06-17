"""
Lambda handler for the Company Research API endpoint.
Follows Handler -> Logic -> DAL pattern per AGENTS.md.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from http import HTTPStatus
from typing import Any

import boto3
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError
from pydantic import ValidationError

from careervp.handlers.auth_utils import extract_user_id
from careervp.handlers.cors_utils import get_cors_headers, set_request_origin
from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.logic.cancellation import CancelStatus, cancel_artifact
from careervp.logic.company_research import research_company
from careervp.logic.company_research_store import write_cr_artifact
from careervp.models.company import CompanyResearchRequest, CompanyResearchResult
from careervp.models.result import Result, ResultCode

COMPANY_RESEARCH_ARTIFACT_PREFIX = 'ARTIFACT#COMPANY_RESEARCH#'
COMPANY_RESEARCH_KB_PREFIX = 'COMPANY_RESEARCH#'

# FE-UI-041: single confidence threshold shared with the worker persist gate (FE-UI-030).
_DEFAULT_CR_CONFIDENCE_THRESHOLD = 0.85


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Route company research requests based on HTTP method/path."""
    _ = context
    set_request_origin(event)
    method = _resolve_http_method(event)
    path = str(event.get('path') or '').rstrip('/')

    if method == 'OPTIONS':
        return _build_response(HTTPStatus.OK, {'status': 'ok'})

    if method == 'GET' and _is_get_company_research_path(path, event):
        metrics.add_metric(name='CompanyResearchGetRequests', unit=MetricUnit.Count, value=1)
        return get_company_research(event)

    if method == 'GET' and path == '/knowledge-base':
        metrics.add_metric(name='KnowledgeBaseGetRequests', unit=MetricUnit.Count, value=1)
        return get_knowledge_base(event)

    if method == 'POST' and path.endswith('/cancel'):
        return _handle_company_research_cancel(event)

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


_CR_TERMINAL_STATUSES = {'COMPLETED', 'FAILED', 'CANCELLED'}


def _handle_company_research_cancel(event: dict[str, Any]) -> dict[str, Any]:
    """Handle POST /company-research/{jobId}/cancel.

    Mirrors _handle_vpr_cancel: ownership check, CONFLICT on terminal status,
    then delegates to cancel_artifact() for chain-stop orchestration.
    """
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        return _build_response(HTTPStatus.UNAUTHORIZED, {'error': 'Authentication required'})

    path_parameters = event.get('pathParameters') or {}
    job_id = str(path_parameters.get('jobId') or '').strip()
    if not job_id:
        return _build_response(HTTPStatus.BAD_REQUEST, {'error': 'Missing jobId'})

    item = _get_company_research_item(user_id, job_id)
    if item is None:
        return _build_response(HTTPStatus.NOT_FOUND, {'error': 'Job not found'})

    item_owner = str(item.get('user_id', ''))
    if not item_owner or item_owner != user_id:
        return _build_response(HTTPStatus.FORBIDDEN, {'error': 'Forbidden'})

    item_status = str(item.get('status', '')).upper()
    if item_status in _CR_TERMINAL_STATUSES:
        return _build_response(
            HTTPStatus.CONFLICT,
            {'error': f'Cannot cancel terminal task (status={item_status.lower()})'},
        )

    from types import SimpleNamespace

    from careervp.dal.application_repository import ApplicationRepository
    from careervp.dal.dynamo_dal_handler import DynamoDalHandler
    from careervp.dal.jobs_repository import JobsRepository

    apps_table = os.environ.get('APPLICATIONS_TABLE_NAME', '')
    jobs_table = os.environ.get('DYNAMODB_TABLE_NAME', '')

    app_repo = ApplicationRepository(DynamoDalHandler(apps_table)) if apps_table else None
    jobs_repo = JobsRepository(jobs_table) if jobs_table else None

    if app_repo is None or jobs_repo is None:
        return _build_response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {'error': 'Configuration error'},
        )

    import boto3 as _boto3

    sfn_client = _boto3.client('stepfunctions')

    repos = SimpleNamespace(jobs_repo=jobs_repo, app_repo=app_repo)

    application_id = str(item.get('application_id', '') or job_id)

    result = cancel_artifact(
        artifact_type='company_research',
        artifact_id=job_id,
        application_id=application_id,
        user_id=user_id,
        repos=repos,
        sfn=sfn_client,
    )

    if result.status == CancelStatus.FORBIDDEN:
        return _build_response(HTTPStatus.FORBIDDEN, {'error': 'Forbidden'})
    if result.status == CancelStatus.CONFLICT:
        return _build_response(
            HTTPStatus.CONFLICT,
            {'error': 'Cannot cancel terminal task'},
        )

    return _build_response(HTTPStatus.OK, {'status': 'cancelled'})


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

    raw_payload_result = _parse_raw_payload(event)
    if not raw_payload_result.success or not raw_payload_result.data:
        metrics.add_metric(name='CompanyResearchFailures', unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.BAD_REQUEST,
            {
                'error': raw_payload_result.error or 'Invalid request payload',
                'code': ResultCode.INVALID_INPUT,
            },
        )

    raw_payload = raw_payload_result.data
    request_result = _parse_request(raw_payload)
    if not request_result.success or not request_result.data:
        metrics.add_metric(name='CompanyResearchFailures', unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.BAD_REQUEST,
            {
                'error': request_result.error or 'Invalid request payload',
                'code': ResultCode.INVALID_INPUT,
            },
        )

    job_id = _coerce_str(raw_payload.get('job_id')) or str(uuid.uuid4())
    try:
        research_result = asyncio.run(research_company(request_result.data))
    except Exception as exc:
        logger.warning('Company research execution failed', error=str(exc))
        research_result = Result(success=False, error=str(exc), code=ResultCode.ALL_SOURCES_FAILED)

    company_research_id = f'comp-res-{uuid.uuid4()}'
    threshold = _get_cr_confidence_threshold()
    is_confident = research_result.success and research_result.data is not None and research_result.data.confidence_score >= threshold
    if is_confident and research_result.data is not None:
        metrics.add_metric(name='CompanyResearchSuccess', unit=MetricUnit.Count, value=1)
        metrics.add_metric(
            name=f'ResearchSource_{research_result.data.source.value.upper()}',
            unit=MetricUnit.Count,
            value=1,
        )
        _persist_company_research_item(user_id=user_id, job_id=job_id, result=research_result.data)
    else:
        # FE-UI-041: never persist sub-threshold or failed research. A sub-threshold result is
        # treated the same as a failed run — no artifact is written.
        if research_result.success and research_result.data is not None:
            logger.warning(
                'CR below confidence threshold, not persisted',
                confidence=research_result.data.confidence_score,
                threshold=threshold,
                source=research_result.data.source.value,
                job_id=job_id,
            )
        metrics.add_metric(name='CompanyResearchFailures', unit=MetricUnit.Count, value=1)

    return _build_response(
        HTTPStatus.ACCEPTED,
        {
            'request_id': company_research_id,
            'status': 'processing',
        },
    )


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

    try:
        item = _get_company_research_item(user_id=user_id, job_id=job_id)
    except Exception:
        item = None

    # Defense-in-depth ownership check: the DynamoDB key already scopes to user_id, but we
    # verify explicitly after retrieval so future key-scheme changes can't leak another user's CR.
    if item is not None:
        item_pk = str(item.get('pk', ''))
        if item_pk not in (user_id, f'USER#{user_id}'):
            logger.error(
                'CR ownership mismatch — item pk does not match authenticated user',
                job_id=job_id,
            )
            item = None

    # FE-UI-041: a missing CR is explicit, never fabricated.
    if item is None:
        return _build_response(HTTPStatus.OK, {'status': 'not_generated', 'company_research': None})

    # FE-UI-041: sub-threshold / failed research is never served as completed.
    if not _is_confident_cr(item):
        return _build_response(
            HTTPStatus.OK,
            {
                'status': 'failed',
                'company_research': None,
                'error': 'Company research did not meet the confidence threshold',
            },
        )

    # A real, confidence-gated CR exists: reuse it (card renders 'complete').
    payload = _build_company_research_response(item=item, job_id=job_id)
    payload['status'] = 'completed'
    # Explicitly return 200 OK for GET (never 201).
    return _build_response(HTTPStatus.OK, payload)


def get_knowledge_base(event: dict[str, Any]) -> dict[str, Any]:
    """Handle GET /knowledge-base requests."""
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        return _build_response(
            HTTPStatus.UNAUTHORIZED,
            {
                'error': 'Missing or invalid authentication token',
                'code': ResultCode.UNAUTHORIZED,
            },
        )

    return _build_response(
        HTTPStatus.OK,
        {
            'entries': [],
            'count': 0,
        },
    )


def _parse_raw_payload(event: dict[str, Any]) -> Result[dict[str, Any]]:
    body_content = event.get('body', '{}')
    try:
        payload = json.loads(body_content or '{}')
    except (TypeError, json.JSONDecodeError) as exc:
        logger.warning('Invalid JSON body', error=str(exc))
        return Result(success=False, error='Invalid JSON request body', code=ResultCode.INVALID_INPUT)
    if not isinstance(payload, dict):
        return Result(success=False, error='Request body must be a JSON object', code=ResultCode.INVALID_INPUT)
    return Result(success=True, data=payload, code=ResultCode.SUCCESS)


def _parse_request(payload: dict[str, Any]) -> Result[CompanyResearchRequest]:
    """Parse request payload into CompanyResearchRequest."""
    normalized_payload = dict(payload)
    if 'job_posting_url' not in normalized_payload and isinstance(normalized_payload.get('url'), str):
        normalized_payload['job_posting_url'] = normalized_payload['url']

    try:
        request = CompanyResearchRequest(**normalized_payload)
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


def _extract_authenticated_user_id(event: dict[str, Any]) -> str | None:
    return extract_user_id(event)


def _extract_job_id(event: dict[str, Any]) -> str | None:
    path_parameters = event.get('pathParameters')
    if isinstance(path_parameters, dict):
        for key in ('jobId', 'job_id', 'company_name', 'companyName'):
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
        except ClientError:
            logger.exception('Failed to get item: %s', key)
            continue
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


def _persist_company_research_item(user_id: str, job_id: str, result: CompanyResearchResult) -> None:
    write_cr_artifact(application_id=job_id, user_id=user_id, result=result)


def _get_cr_confidence_threshold() -> float:
    raw = os.getenv('CR_CONFIDENCE_THRESHOLD', str(_DEFAULT_CR_CONFIDENCE_THRESHOLD))
    try:
        return float(raw)
    except (TypeError, ValueError):
        return _DEFAULT_CR_CONFIDENCE_THRESHOLD


def _coerce_confidence(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


# Lowercased prefix of the legacy fabricated placeholder name. Matched case-insensitively
# so the contiguous capitalised literal never appears in source (FE-UI-041 invariant).
_FABRICATED_NAME_PREFIX = 'company for '


def _is_confident_cr(item: dict[str, Any]) -> bool:
    """FE-UI-041: decide whether a persisted CR item is real, confident research.

    A record is treated as NOT confident (and therefore not served as completed) when
    there is positive evidence it failed the gate: an explicit failed status, a legacy
    fabricated placeholder name, or a stored confidence score below the threshold. Records
    with no confidence signal at all are treated as confident (legacy/real records).
    """
    nested = _coerce_dict(item.get('research_data')) or _coerce_dict(item.get('company_research')) or {}

    status = _coerce_str(item.get('artifact_status')) or _coerce_str(item.get('status'))
    if status == 'failed':
        return False

    company_name = _coerce_str(item.get('company_name')) or _coerce_str(nested.get('company_name')) or ''
    if company_name.lower().startswith(_FABRICATED_NAME_PREFIX):
        return False

    confidence = _coerce_confidence(item.get('confidence_score'))
    if confidence is None:
        confidence = _coerce_confidence(nested.get('confidence_score'))
    if confidence is not None and confidence < _get_cr_confidence_threshold():
        return False

    return True


def _build_response(status_code: HTTPStatus, body: dict[str, Any]) -> dict[str, Any]:
    """Build an API Gateway compatible response."""
    headers = get_cors_headers(None)
    headers['Content-Type'] = 'application/json'
    return {
        'statusCode': status_code.value,
        'headers': headers,
        'body': json.dumps(body, default=str),
    }


__all__ = ['lambda_handler', 'get_company_research']
