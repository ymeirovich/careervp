"""Lambda handler for CV tailoring requests."""

from __future__ import annotations

from datetime import datetime
import json
from http import HTTPStatus
from typing import Any, cast

from careervp.dal.cv_dal import CVTable
from careervp.logic.cv_tailoring import tailor_cv
from careervp.logic.fvs_validator import create_fvs_baseline
from careervp.logic.llm_client import LLMClient
from careervp.models.cv_models import UserCV
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

    user_id = _get_user_id(event)
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
        logger.info("CV tailoring failed", request_id=context.aws_request_id)
        return _response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {
                "success": False,
                "code": ResultCode.INTERNAL_ERROR,
                "message": str(exc),
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


def _fetch_and_tailor_cv(request: TailorCVRequest) -> Result[Any]:
    """Fetch CV from DAL and invoke tailoring logic."""
    dal = CVTable()
    llm_client = LLMClient()

    response = dal.get_item({"cv_id": request.cv_id})
    item = response.get("Item") if isinstance(response, dict) else None
    if not item:
        return Result(
            success=False,
            error=f"CV with id '{request.cv_id}' not found",
            code=ResultCode.CV_NOT_FOUND,
        )

    if item.get("user_id") and request.user_id and item.get("user_id") != request.user_id:
        return Result(
            success=False,
            error="User does not have access to this CV",
            code=ResultCode.FORBIDDEN,
        )

    cv_data = item.get("cv_data") or item
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


def _get_user_id(event: dict[str, Any]) -> str | None:
    user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')
    return cast(str | None, user_id)


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
            return _serialize_result_data(data)
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
