"""Lambda handler for CV tailoring requests."""

from __future__ import annotations

import json
import os
from datetime import datetime
from http import HTTPStatus
from typing import Any

from careervp.dal.cv_dal import CVTable
from careervp.logic.cv_tailoring import tailor_cv
from careervp.logic.fvs_validator import create_fvs_baseline
from careervp.logic.llm_client import LLMClient
from careervp.models.cv import UserCV
from careervp.models.cv_tailoring_models import TailorCVRequest, TailoringPreferences
from careervp.models.result import Result, ResultCode
from careervp.validation.cv_tailoring_validation import validate_job_description


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime and Pydantic objects."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, 'model_dump'):
            return obj.model_dump(mode='json')
        return super().default(obj)


logger: Any
try:
    from careervp.handlers.utils.observability import logger as powertools_logger

    logger = powertools_logger
except Exception:  # pragma: no cover - fallback for tests
    import logging

    logger = logging.getLogger(__name__)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # noqa: C901
    """Handle CV tailoring request."""
    headers = _cors_headers()

    try:
        body = json.loads(event.get('body') or '{}')
    except json.JSONDecodeError:
        return _response(
            HTTPStatus.BAD_REQUEST,
            {
                'success': False,
                'code': ResultCode.INVALID_JSON,
                'message': 'Request body contains invalid JSON',
            },
            headers,
        )

    user_id = _get_user_id(event, body)
    if not user_id:
        return _response(
            HTTPStatus.UNAUTHORIZED,
            {
                'success': False,
                'code': ResultCode.UNAUTHORIZED,
                'message': 'Missing or invalid authentication token',
            },
            headers,
        )

    if 'preferences' in body and not isinstance(body['preferences'], dict):
        return _response(
            HTTPStatus.BAD_REQUEST,
            {
                'success': False,
                'code': ResultCode.VALIDATION_ERROR,
                'message': 'preferences must be an object',
            },
            headers,
        )

    cv_id = body.get('cv_id')
    job_description = body.get('job_description')

    validation_errors = []
    if not cv_id:
        validation_errors.append({'field': 'cv_id', 'message': 'cv_id is required'})
    if job_description is None:
        validation_errors.append({'field': 'job_description', 'message': 'job_description is required'})

    if job_description is not None:
        job_result = validate_job_description(job_description)
        if not job_result.success:
            validation_errors.append(
                {
                    'field': 'job_description',
                    'message': f'job_description: {job_result.message}',
                }
            )

    if validation_errors:
        message = ', '.join(err['message'] for err in validation_errors)
        return _response(
            HTTPStatus.BAD_REQUEST,
            {
                'success': False,
                'code': ResultCode.VALIDATION_ERROR,
                'message': message,
                'errors': validation_errors,
            },
            headers,
        )

    preferences = None
    if isinstance(body.get('preferences'), dict):
        preferences = TailoringPreferences(**body['preferences'])

    request = TailorCVRequest(
        cv_id=cv_id,
        job_description=job_description,
        user_id=user_id,
        preferences=preferences,
    )

    try:
        result = _fetch_and_tailor_cv(request)
    except Exception as exc:  # noqa: BLE001
        logger.info('CV tailoring failed', request_id=context.aws_request_id)
        return _response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {
                'success': False,
                'code': ResultCode.INTERNAL_ERROR,
                'message': str(exc),
            },
            headers,
        )

    status_code = _status_from_code(result.code)
    if result.success:
        data = _build_success_data(result.data)
        body = {
            'success': True,
            'code': result.code,
            'message': None,
            'data': data,
        }
    else:
        body = {
            'success': False,
            'code': result.code,
            'message': result.message,
            'data': _serialize_result_data(result.data) if result.data is not None else None,
        }

    logger.info('CV tailoring handled', request_id=context.aws_request_id)
    return _response(status_code, body, headers)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Alias for standard Lambda entrypoint naming."""
    return handler(event, context)


def _fetch_and_tailor_cv(request: TailorCVRequest) -> Result[Any]:
    """Fetch CV from DAL and invoke tailoring logic."""
    dal = CVTable()
    llm_client = LLMClient()

    response = dal.get_cv_item(user_id=request.user_id, cv_id=request.cv_id)
    item = response.get('Item') if isinstance(response, dict) else None
    if not item:
        return Result(
            success=False,
            error=f"CV with id '{request.cv_id}' not found",
            code=ResultCode.CV_NOT_FOUND,
        )

    if not isinstance(item, dict):
        return Result(
            success=False,
            error='Invalid CV data format',
            code=ResultCode.INTERNAL_ERROR,
        )

    if item.get('user_id') and request.user_id and item.get('user_id') != request.user_id:
        return Result(
            success=False,
            error='User does not have access to this CV',
            code=ResultCode.FORBIDDEN,
        )

    raw_cv_data = item.get('cv_data')
    cv_data = dict(raw_cv_data) if isinstance(raw_cv_data, dict) else dict(item)
    if request.cv_id and not cv_data.get('cv_id'):
        cv_data['cv_id'] = request.cv_id
    if request.user_id and not cv_data.get('user_id'):
        cv_data['user_id'] = request.user_id
    master_cv = UserCV(**cv_data)
    baseline = create_fvs_baseline(master_cv)

    return tailor_cv(
        master_cv=master_cv,
        job_description=request.job_description,
        preferences=request.preferences,
        fvs_baseline=baseline,
        dal=dal,
        llm_client=llm_client,
    )


def _get_user_id(event: dict[str, Any], body: dict[str, Any] | None = None) -> str | None:
    authorizer_user_id = _get_user_id_from_authorizer(event)
    if authorizer_user_id:
        return authorizer_user_id

    if _authorizer_disabled():
        return _get_user_id_from_unprotected_request(event, body)
    return None


def _get_user_id_from_authorizer(event: dict[str, Any]) -> str | None:
    request_context = event.get('requestContext', {})
    authorizer = request_context.get('authorizer')
    if not isinstance(authorizer, dict):
        return None

    claims = authorizer.get('claims')
    claim_user_id = _extract_user_id_from_claims(claims)
    if claim_user_id:
        return claim_user_id

    jwt_context = authorizer.get('jwt')
    if isinstance(jwt_context, dict):
        jwt_claims = jwt_context.get('claims')
        jwt_user_id = _extract_user_id_from_claims(jwt_claims)
        if jwt_user_id:
            return jwt_user_id

    for direct_key in ('user_id', 'principalId', 'principal_id'):
        direct_value = authorizer.get(direct_key)
        if isinstance(direct_value, str) and direct_value.strip():
            return direct_value.strip()
    return None


def _authorizer_disabled() -> bool:
    return os.getenv('AUTHORIZER_DISABLED', 'false').strip().lower() == 'true'


def _get_user_id_from_unprotected_request(event: dict[str, Any], body: dict[str, Any] | None) -> str | None:
    headers = event.get('headers')
    if isinstance(headers, dict):
        header_user_id = _get_header_case_insensitive(headers, 'x-user-id')
        if header_user_id:
            return header_user_id

    if isinstance(body, dict):
        body_user_id = body.get('user_id')
        if isinstance(body_user_id, str) and body_user_id.strip():
            return body_user_id.strip()
    return None


def _extract_user_id_from_claims(claims: Any) -> str | None:
    if not isinstance(claims, dict):
        return None
    for claim_key in ('sub', 'user_id', 'cognito:username'):
        claim_value = claims.get(claim_key)
        if isinstance(claim_value, str) and claim_value.strip():
            return claim_value.strip()
    return None


def _get_header_case_insensitive(headers: dict[str, Any], target_header: str) -> str | None:
    normalized_target = target_header.lower()
    for key, value in headers.items():
        if isinstance(key, str) and key.lower() == normalized_target and isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _status_from_code(code: str) -> int:
    mapping = {
        ResultCode.SUCCESS: HTTPStatus.OK,
        ResultCode.CV_TAILORED_SUCCESS: HTTPStatus.OK,
        ResultCode.CV_NOT_FOUND: HTTPStatus.NOT_FOUND,
        ResultCode.FVS_HALLUCINATION_DETECTED: HTTPStatus.BAD_REQUEST,
        ResultCode.FVS_VIOLATION_DETECTED: HTTPStatus.BAD_REQUEST,
        ResultCode.LLM_TIMEOUT: HTTPStatus.GATEWAY_TIMEOUT,
        ResultCode.RATE_LIMIT_EXCEEDED: HTTPStatus.TOO_MANY_REQUESTS,
        ResultCode.FORBIDDEN: HTTPStatus.FORBIDDEN,
        ResultCode.UNAUTHORIZED: HTTPStatus.UNAUTHORIZED,
        ResultCode.VALIDATION_ERROR: HTTPStatus.BAD_REQUEST,
    }
    return int(mapping.get(code, HTTPStatus.INTERNAL_SERVER_ERROR).value)


def _serialize_result_data(data: Any) -> Any:
    """Serialize result data, handling datetime objects."""
    if data is None:
        return None
    if hasattr(data, 'model_dump'):
        # Use json serialization mode to handle datetime
        try:
            return data.model_dump(mode='json')
        except (TypeError, ValueError):
            # Fallback to default serialization
            return data.model_dump()
    return data


def _build_success_data(data: Any) -> dict[str, Any]:
    """Build success response data, handling datetime serialization."""
    if data is None:
        return {'tailored_cv': None}
    if isinstance(data, dict):
        if 'tailored_cv' in data:
            serialized = _serialize_result_data(data)
            if isinstance(serialized, dict):
                return serialized
            return {'tailored_cv': serialized}
        return {'tailored_cv': _serialize_result_data(data)}
    if hasattr(data, 'tailored_cv'):
        # TailoredCVResponse object
        serialized = _serialize_result_data(data)
        if isinstance(serialized, dict) and 'tailored_cv' in serialized:
            return serialized
        return {'tailored_cv': serialized}
    if hasattr(data, 'model_dump'):
        # TailoredCV or similar Pydantic model
        return {'tailored_cv': _serialize_result_data(data)}
    return {'tailored_cv': data}


def _cors_headers() -> dict[str, str]:
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    }


def _response(status: int | HTTPStatus, body: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    status_code = int(status.value) if isinstance(status, HTTPStatus) else int(status)
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body, cls=CustomJSONEncoder),
    }
