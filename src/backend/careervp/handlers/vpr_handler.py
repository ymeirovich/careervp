"""
VPR Generation Lambda Handler.
Per docs/specs/03-vpr-generator.md and Task 05 instructions.

Endpoint: POST /api/vpr
Timeout: 120 seconds (API contract)
"""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from typing import Any

from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.logic.vpr_generator import generate_vpr
from careervp.models.result import ResultCode
from careervp.models.vpr import VPRRequest, VPRResponse

JSON_HEADERS = {'Content-Type': 'application/json'}


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """
    Handle POST /api/vpr requests.

    Flow:
        1. Parse and validate VPRRequest.
        2. Fetch immutable CV data from DynamoDB.
        3. Delegate to generate_vpr logic layer.
        4. Map Result codes to HTTP statuses per spec.
        5. Emit Powertools metrics on success.
    """
    table_name = os.environ['DYNAMODB_TABLE_NAME']
    try:
        request_body = _parse_body(event)
        request = VPRRequest.model_validate(request_body)
    except (ValueError, json.JSONDecodeError, ValidationError) as exc:
        logger.warning('Invalid request body', error=str(exc))
        error_response = _build_error_response('Invalid request body', HTTPStatus.BAD_REQUEST)
        return error_response

    logger.append_keys(user_id=request.user_id, application_id=request.application_id)
    dal = DynamoDalHandler(table_name)

    user_cv = dal.get_cv(request.user_id)
    if user_cv is None:
        logger.info('User CV not found', user_id=request.user_id)
        return _build_error_response('CV not found. Upload a CV before generating a VPR.', HTTPStatus.NOT_FOUND)

    result = generate_vpr(request, user_cv, dal)
    if not result.success or result.data is None:
        status = _map_result_code_to_http_status(result.code)
        error_message = result.error or 'Failed to generate VPR.'
        response_body = result.data if result.data else _default_error_response(error_message)
        return _serialize_response(response_body, status)

    response_body = result.data
    _emit_success_metrics(response_body)
    logger.info('VPR generated successfully', result_code=result.code)
    return _serialize_response(response_body, HTTPStatus.OK)


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


def _emit_success_metrics(response: VPRResponse) -> None:
    """Emit required metrics when generation succeeds."""
    metrics.add_metric(name='VPRGenerated', unit='Count', value=1)
    metrics.add_metric(name='VPRGenerationTimeMs', unit='Milliseconds', value=response.generation_time_ms)
    cost = response.token_usage.cost_usd if response.token_usage else 0.0
    metrics.add_metric(name='VPRCostUSD', unit='None', value=cost)


def _build_error_response(message: str, status: HTTPStatus) -> dict[str, Any]:
    """Construct a standardized error response."""
    response = _default_error_response(message)
    return _serialize_response(response, status)


def _default_error_response(message: str) -> VPRResponse:
    """Create a default error VPRResponse payload."""
    return VPRResponse(success=False, vpr=None, token_usage=None, generation_time_ms=0, error=message)


def _serialize_response(response: VPRResponse, status: HTTPStatus) -> dict[str, Any]:
    """Serialize a VPRResponse into the API Gateway response format."""
    return {
        'statusCode': int(status),
        'headers': JSON_HEADERS,
        'body': response.model_dump_json(),
    }


def _map_result_code_to_http_status(code: str) -> HTTPStatus:
    """Translate ResultCode values into HTTP statuses."""
    mapping = {
        ResultCode.SUCCESS: HTTPStatus.OK,
        ResultCode.VPR_GENERATED: HTTPStatus.OK,
        ResultCode.INVALID_INPUT: HTTPStatus.BAD_REQUEST,
        ResultCode.MISSING_REQUIRED_FIELD: HTTPStatus.BAD_REQUEST,
        ResultCode.FVS_HALLUCINATION_DETECTED: HTTPStatus.UNPROCESSABLE_ENTITY,
        ResultCode.FVS_VALIDATION_FAILED: HTTPStatus.UNPROCESSABLE_ENTITY,
        ResultCode.FVS_DATE_MISMATCH: HTTPStatus.UNPROCESSABLE_ENTITY,
        ResultCode.FVS_ROLE_MISMATCH: HTTPStatus.UNPROCESSABLE_ENTITY,
        ResultCode.LLM_API_ERROR: HTTPStatus.BAD_GATEWAY,
        ResultCode.LLM_TIMEOUT: HTTPStatus.GATEWAY_TIMEOUT,
        ResultCode.DYNAMODB_ERROR: HTTPStatus.INTERNAL_SERVER_ERROR,
        ResultCode.INTERNAL_ERROR: HTTPStatus.INTERNAL_SERVER_ERROR,
        ResultCode.NOT_IMPLEMENTED: HTTPStatus.NOT_IMPLEMENTED,
    }
    return mapping.get(code, HTTPStatus.INTERNAL_SERVER_ERROR)
