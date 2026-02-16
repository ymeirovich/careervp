"""Lambda handler for Interview Prep API endpoint."""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any

from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.models.interview_prep import InterviewPrepRequest
from careervp.models.result import Result, ResultCode


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Handle POST /interview-prep/generate requests."""
    metrics.add_metric(name='InterviewPrepRequests', unit=MetricUnit.Count, value=1)

    request_result = _parse_request(event)
    if not request_result.success or not request_result.data:
        metrics.add_metric(name='InterviewPrepFailures', unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.BAD_REQUEST,
            {'error': request_result.error or 'Invalid request', 'code': ResultCode.INVALID_INPUT},
        )

    # Return 202 Accepted - async pattern
    request_id = request_result.data.vpr_id
    metrics.add_metric(name='InterviewPrepSubmitted', unit=MetricUnit.Count, value=1)

    return _build_response(
        HTTPStatus.ACCEPTED,
        {
            'request_id': request_id,
            'status': 'processing',
        },
    )


def _parse_request(event: dict[str, Any]) -> Result[InterviewPrepRequest]:
    """Parse and validate request body."""
    body_content = event.get('body', '{}')
    try:
        payload = json.loads(body_content or '{}')
    except (TypeError, json.JSONDecodeError) as exc:
        logger.warning('Invalid JSON body', error=str(exc))
        return Result(success=False, error='Invalid JSON request body', code=ResultCode.INVALID_INPUT)

    try:
        request = InterviewPrepRequest(**payload)
    except ValidationError as exc:
        logger.warning('InterviewPrepRequest validation failed', errors=exc.errors())
        return Result(success=False, error='Request validation failed', code=ResultCode.INVALID_INPUT)

    return Result(success=True, data=request, code=ResultCode.SUCCESS)


def _build_response(status_code: HTTPStatus, body: dict[str, Any]) -> dict[str, Any]:
    """Build API Gateway response."""
    return {
        'statusCode': status_code.value,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps(body, default=str),
    }


__all__ = ['lambda_handler']
