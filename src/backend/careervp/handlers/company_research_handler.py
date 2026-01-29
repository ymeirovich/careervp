"""
Lambda handler for the Company Research API endpoint.
Follows Handler -> Logic -> DAL pattern per AGENTS.md.
"""

from __future__ import annotations

import asyncio
import json
from http import HTTPStatus
from typing import Any

from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.logic.company_research import research_company
from careervp.models.company import CompanyResearchRequest
from careervp.models.result import Result, ResultCode


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """
    Handle POST /company-research requests routed through API Gateway.
    """
    metrics.add_metric(name='CompanyResearchRequests', unit=MetricUnit.Count, value=1)

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


__all__ = ['lambda_handler']
