"""Lambda handler for Knowledge Base API endpoints."""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from typing import Any

from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

from careervp.dal.knowledge_repository import KnowledgeRepository
from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.models.result import Result


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
    params = event.get('queryStringParameters') or {}
    user_id = params.get('user_id', '')
    job_id = params.get('job_id')
    entity_type = params.get('entity_type')

    if not user_id:
        return _build_response(HTTPStatus.BAD_REQUEST, {'error': 'user_id is required'})

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
    body_content = event.get('body', '{}')
    try:
        payload = json.loads(body_content or '{}')
    except (TypeError, json.JSONDecodeError):
        return _build_response(HTTPStatus.BAD_REQUEST, {'error': 'Invalid JSON'})

    entity_type = payload.get('entity_type', '')

    required_gap = ('user_id', 'job_id', 'cv_id', 'question_id', 'response_id', 'response_text')
    required_research = ('user_id', 'job_id', 'company_research_id', 'company_name', 'research_data')

    if entity_type == 'GAP_RESPONSE':
        missing = [f for f in required_gap if not payload.get(f)]
        if missing:
            return _build_response(HTTPStatus.BAD_REQUEST, {'error': f'Missing required fields: {", ".join(missing)}'})
        result = repo.save_gap_response(
            user_id=payload['user_id'],
            job_id=payload['job_id'],
            cv_id=payload['cv_id'],
            question_id=payload['question_id'],
            response_id=payload['response_id'],
            response_text=payload['response_text'],
        )
    elif entity_type == 'COMPANY_RESEARCH':
        missing = [f for f in required_research if not payload.get(f)]
        if missing:
            return _build_response(HTTPStatus.BAD_REQUEST, {'error': f'Missing required fields: {", ".join(missing)}'})
        result = repo.save_company_research(
            user_id=payload['user_id'],
            job_id=payload['job_id'],
            company_research_id=payload['company_research_id'],
            company_name=payload['company_name'],
            research_data=payload['research_data'],
        )
    else:
        return _build_response(HTTPStatus.BAD_REQUEST, {'error': f'Unknown entity_type: {entity_type}'})

    if not result.success:
        return _build_response(HTTPStatus.INTERNAL_SERVER_ERROR, {'error': result.error or 'Save failed'})

    metrics.add_metric(name='KnowledgeBaseSaves', unit=MetricUnit.Count, value=1)
    return _build_response(HTTPStatus.CREATED, result.data or {})


def _build_response(status_code: HTTPStatus, body: dict[str, Any]) -> dict[str, Any]:
    """Build API Gateway response."""
    return {
        'statusCode': status_code.value,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps(body, default=str),
    }


__all__ = ['lambda_handler']
