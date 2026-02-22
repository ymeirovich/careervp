"""Lambda handler for Knowledge Base API endpoints."""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from typing import Any

from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

from careervp.dal.knowledge_repository import KnowledgeRepository
from careervp.handlers.auth_utils import extract_user_id
from careervp.handlers.cors_utils import get_cors_headers
from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.logic.auth_service import AuthService, ConfigurationError, InvalidTokenError
from careervp.models.result import Result

_auth_service: AuthService | None = None


def _get_auth_service() -> AuthService:
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService.from_env()
    return _auth_service


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Route knowledge base requests based on HTTP method and path."""
    table_name = os.environ.get('KNOWLEDGE_TABLE_NAME', 'careervp-knowledge-table-dev')
    http_method = event.get('httpMethod', 'GET')

    repo = KnowledgeRepository(table_name)

    if http_method == 'GET':
        return _handle_get(event, repo)
    if http_method == 'POST':
        return _handle_post(event, repo)

    return _build_response(HTTPStatus.METHOD_NOT_ALLOWED, {'error': 'Method not allowed'})


def _handle_get(event: dict[str, Any], repo: KnowledgeRepository) -> dict[str, Any]:
    """Handle GET requests for knowledge base queries."""
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        return _build_response(HTTPStatus.UNAUTHORIZED, {'error': 'Authentication required'})

    params = event.get('queryStringParameters') or {}
    job_id = params.get('job_id')
    entity_type = params.get('entity_type')

    metrics.add_metric(name='KnowledgeBaseQueries', unit=MetricUnit.Count, value=1)

    if entity_type == 'GAP_RESPONSE':
        result: Result[list[dict[str, Any]]] = repo.get_gap_responses(user_id, job_id)
    elif entity_type == 'COMPANY_RESEARCH' and job_id:
        company_result = repo.get_company_research(user_id, job_id)
        if company_result.success:
            result = Result(success=True, data=[company_result.data] if company_result.data else [], code=company_result.code)
        else:
            result = Result(success=False, data=[], error=company_result.error, code=company_result.code)
    else:
        # Return all gap responses by default
        result = repo.get_gap_responses(user_id, job_id)

    if not result.success:
        return _build_response(HTTPStatus.INTERNAL_SERVER_ERROR, {'error': result.error or 'Query failed'})

    entries = result.data or []
    return _build_response(HTTPStatus.OK, {'entries': entries, 'count': len(entries)})


def _handle_post(event: dict[str, Any], repo: KnowledgeRepository) -> dict[str, Any]:
    """Handle POST requests to save knowledge entries."""
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        return _build_response(HTTPStatus.UNAUTHORIZED, {'error': 'Authentication required'})

    body_content = event.get('body', '{}')
    try:
        payload = json.loads(body_content or '{}')
    except (TypeError, json.JSONDecodeError):
        return _build_response(HTTPStatus.BAD_REQUEST, {'error': 'Invalid JSON'})

    entity_type = payload.get('entity_type', '')

    required_gap = {'job_id': str, 'cv_id': str}
    required_research = ('job_id', 'company_research_id', 'company_name', 'research_data')

    if entity_type == 'GAP_RESPONSE':
        for field, expected_type in required_gap.items():
            value = payload.get(field)
            if not isinstance(value, expected_type) or not value:
                return _build_response(HTTPStatus.BAD_REQUEST, {'error': f'Invalid or missing field: {field}'})

        required_gap_fields = ('question_id', 'response_id', 'response_text')
        missing = [f for f in required_gap_fields if not payload.get(f)]
        if missing:
            return _build_response(HTTPStatus.BAD_REQUEST, {'error': f'Missing required fields: {", ".join(missing)}'})
        result = repo.save_gap_response(
            user_id=user_id,
            job_id=str(payload.get('job_id') or ''),
            cv_id=str(payload.get('cv_id') or ''),
            question_id=str(payload.get('question_id') or ''),
            response_id=str(payload.get('response_id') or ''),
            response_text=str(payload.get('response_text') or ''),
        )
    elif entity_type == 'COMPANY_RESEARCH':
        missing = [f for f in required_research if not payload.get(f)]
        if missing:
            return _build_response(HTTPStatus.BAD_REQUEST, {'error': f'Missing required fields: {", ".join(missing)}'})
        result = repo.save_company_research(
            user_id=user_id,
            job_id=str(payload.get('job_id') or ''),
            company_research_id=str(payload.get('company_research_id') or ''),
            company_name=str(payload.get('company_name') or ''),
            research_data=payload.get('research_data'),
        )
    else:
        return _build_response(HTTPStatus.BAD_REQUEST, {'error': f'Unknown entity_type: {entity_type}'})

    if not result.success:
        return _build_response(HTTPStatus.INTERNAL_SERVER_ERROR, {'error': result.error or 'Save failed'})

    metrics.add_metric(name='KnowledgeBaseSaves', unit=MetricUnit.Count, value=1)
    return _build_response(HTTPStatus.CREATED, result.data or {})


def _build_response(status_code: HTTPStatus, body: dict[str, Any]) -> dict[str, Any]:
    """Build API Gateway response."""
    headers = get_cors_headers(None)
    headers['Content-Type'] = 'application/json'
    return {
        'statusCode': status_code.value,
        'headers': headers,
        'body': json.dumps(body, default=str),
    }


def _extract_bearer_token(event: dict[str, Any]) -> str | None:
    headers = event.get('headers')
    if not isinstance(headers, dict):
        return None

    auth_header = headers.get('Authorization') or headers.get('authorization')
    if not isinstance(auth_header, str) or not auth_header.startswith('Bearer '):
        return None

    token = auth_header[7:].strip()
    return token if token else None


def _extract_authenticated_user_id(event: dict[str, Any]) -> str | None:
    user_id = extract_user_id(event)
    if user_id:
        return user_id

    token = _extract_bearer_token(event)
    if not token:
        return None

    try:
        payload = _get_auth_service().validate_token(token, expected_token_type='access')
    except (InvalidTokenError, ConfigurationError):
        return None

    raw_user_id = payload.get('user_id') or payload.get('sub')
    if isinstance(raw_user_id, str) and raw_user_id.strip():
        return raw_user_id.strip()
    return None


__all__ = ['lambda_handler']
