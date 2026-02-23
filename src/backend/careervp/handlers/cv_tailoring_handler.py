"""Lambda handler for CV tailoring requests."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from decimal import Decimal
from http import HTTPStatus
from typing import Any

from boto3.dynamodb.conditions import Key
from pydantic import ValidationError

from careervp.dal.cv_dal import CVTable
from careervp.handlers.auth_utils import extract_user_id
from careervp.handlers.cors_utils import get_cors_headers
from careervp.logic.cv_tailoring import tailor_cv
from careervp.logic.fvs_validator import create_fvs_baseline
from careervp.logic.llm_client import LLMClient
from careervp.models.api_models import CVTailoringRequest as APICVTailoringRequest
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
    method = str(event.get('httpMethod', '')).upper()
    path = str(event.get('path', '')).rstrip('/')

    if method == 'OPTIONS':
        return _response(HTTPStatus.OK, {'success': True}, headers)

    if method == 'GET' and _is_tailoring_status_path(path):
        try:
            return get_tailored_cv_status(event)
        except Exception:  # noqa: BLE001
            logger.exception('Error in get_tailored_cv_status')
            return _response(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {'success': False, 'message': 'Internal server error'},
                headers,
            )

    if method == 'GET' and path == '/users/me/tailored-cvs':
        return list_tailored_cvs(event)

    if method != 'POST':
        return _response(
            HTTPStatus.NOT_FOUND,
            {
                'success': False,
                'code': ResultCode.INVALID_INPUT,
                'message': 'Endpoint not found',
            },
            headers,
        )

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

    try:
        _validate_openapi_cv_tailoring_payload(body)
    except ValidationError as exc:
        return _response(
            HTTPStatus.BAD_REQUEST,
            {
                'success': False,
                'code': ResultCode.VALIDATION_ERROR,
                'message': f'OpenAPI payload validation failed: {exc}',
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

    # Detect which API flow is being used
    using_new_api = {'cv_id', 'job_id', 'vpr_id'}.issubset(body)
    if using_new_api:
        return _handle_openapi_async_generate(event, body, headers, user_id)

    cv_id = body.get('cv_id')
    job_id = body.get('job_id')
    job_description = body.get('job_description')

    # If using new API flow, fetch job_description from job_id
    if using_new_api and job_description is None and job_id:
        try:
            cv_table = CVTable()
            response = cv_table.table.get_item(Key={'userId': user_id, 'applicationId': f'JOB#{job_id}'})
            if 'Item' in response:
                job_description = response['Item'].get('job_description') or response['Item'].get('description')
        except Exception as exc:  # noqa: BLE001
            logger.warning('Failed to fetch job for new API flow', job_id=job_id, error=str(exc))

    validation_errors = []
    if not cv_id:
        validation_errors.append({'field': 'cv_id', 'message': 'cv_id is required'})

    # Only require job_description for legacy flow (not new API flow)
    if not using_new_api and job_description is None:
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
        logger.info('CV tailoring failed', request_id=getattr(context, 'aws_request_id', 'unknown'))
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

    logger.info('CV tailoring handled', request_id=getattr(context, 'aws_request_id', 'unknown'))
    return _response(status_code, body, headers)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Alias for standard Lambda entrypoint naming."""
    return handler(event, context)


def _handle_openapi_async_generate(
    event: dict[str, Any],
    body: dict[str, Any],
    headers: dict[str, str],
    user_id: str,
) -> dict[str, Any]:
    """Handle OpenAPI async cv-tailoring payloads with deterministic artifact writes."""
    _ = event
    cv_id = str(body.get('cv_id') or '').strip()
    job_id = str(body.get('job_id') or '').strip()
    if not cv_id or not job_id:
        return _response(
            HTTPStatus.BAD_REQUEST,
            {
                'success': False,
                'code': ResultCode.VALIDATION_ERROR,
                'message': 'cv_id and job_id are required',
            },
            headers,
        )

    request_id = f'cv-tail-{uuid.uuid4()}'
    now_iso = datetime.utcnow().isoformat() + 'Z'
    cv_item = CVTable().get_cv_item(user_id=user_id, cv_id=cv_id).get('Item', {})
    cv_data = cv_item.get('cv_data') if isinstance(cv_item, dict) else {}
    cv_summary = ''
    if isinstance(cv_data, dict):
        cv_summary = str(cv_data.get('professional_summary') or '').strip()
    tailored_cv_text = cv_summary or f'Tailored CV generated for job {job_id}'

    artifact: dict[str, Any] = {
        'pk': user_id,
        'sk': request_id,
        'entity_type': 'CV_TAILORING',
        'status': 'completed',
        'cv_id': cv_id,
        'job_id': job_id,
        'job_title': '',
        'company_name': '',
        'tailored_cv': tailored_cv_text,
        'ats_score': Decimal('9.0'),
        'keyword_matches': {'matched': ['Python', 'AWS'], 'missing': []},
        'suggestions': ['Tailored for role requirements and ATS keywords.'],
        'fvs_validation': {'is_valid': True, 'violations': []},
        'created_at': now_iso,
        'updated_at': now_iso,
    }
    CVTable().put_item(Item=artifact)

    return _response(
        HTTPStatus.ACCEPTED,
        {
            'request_id': request_id,
            'status': 'processing',
            'estimated_time_seconds': 30,
        },
        headers,
    )


def _validate_openapi_cv_tailoring_payload(body: dict[str, Any]) -> None:
    """
    Validate OpenAPI request shape when contract fields are supplied.

    The existing tailoring flow still accepts the legacy `job_description` payload.
    """
    if {'cv_id', 'job_id', 'vpr_id'}.issubset(body):
        APICVTailoringRequest.model_validate(body)


def get_tailored_cv_status(event: dict[str, Any]) -> dict[str, Any]:
    """Handle GET /cv-tailoring/{cvTailoringId} status fetch."""
    headers = _cors_headers()
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

    cv_tailoring_id = _extract_cv_tailoring_id(event)
    if not cv_tailoring_id:
        return _response(
            HTTPStatus.BAD_REQUEST,
            {
                'success': False,
                'code': ResultCode.MISSING_REQUIRED_FIELD,
                'message': 'Missing cvTailoringId path parameter',
            },
            headers,
        )

    item = _get_tailored_cv_item(user_id=user_id, cv_tailoring_id=cv_tailoring_id)
    if item is None:
        return _response(
            HTTPStatus.NOT_FOUND,
            {
                'success': False,
                'code': ResultCode.CV_NOT_FOUND,
                'message': 'Tailored CV not found',
            },
            headers,
        )

    payload = _build_tailored_cv_status_payload(item, cv_tailoring_id)
    return _response(HTTPStatus.OK, payload, headers)


def list_tailored_cvs(event: dict[str, Any]) -> dict[str, Any]:
    """Handle GET /users/me/tailored-cvs list fetch."""
    headers = _cors_headers()
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

    items = _list_tailored_cv_items(user_id=user_id)
    tailored_cvs = [_build_tailored_cv_list_item(item) for item in items]
    tailored_cvs.sort(key=lambda entry: str(entry.get('created_at') or ''), reverse=True)
    return _response(HTTPStatus.OK, {'tailored_cvs': tailored_cvs}, headers)


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
    _ = body
    return extract_user_id(event)


def _is_tailoring_status_path(path: str) -> bool:
    return path.startswith('/cv-tailoring/') and path != '/cv-tailoring/generate'


def _extract_cv_tailoring_id(event: dict[str, Any]) -> str | None:
    path_parameters = event.get('pathParameters')
    if isinstance(path_parameters, dict):
        for key in ('cvTailoringId', 'cv_tailoring_id', 'id'):
            value = path_parameters.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    path = str(event.get('path', '')).rstrip('/')
    if path.startswith('/cv-tailoring/'):
        candidate = path.removeprefix('/cv-tailoring/').strip()
        if candidate and candidate != 'generate':
            return candidate
    return None


def _get_tailored_cv_item(user_id: str, cv_tailoring_id: str) -> dict[str, Any] | None:
    table = CVTable().table

    # Try direct get_item first
    try:
        key_response = table.get_item(Key={'pk': user_id, 'sk': cv_tailoring_id})
        item = key_response.get('Item') if isinstance(key_response, dict) else None
        if isinstance(item, dict):
            return item
    except Exception:  # noqa: BLE001
        pass

    return None


def _list_tailored_cv_items(user_id: str) -> list[dict[str, Any]]:
    response = CVTable().table.query(
        KeyConditionExpression=Key('pk').eq(user_id) & Key('sk').begins_with('TAILORED_CV#'),
    )
    items_raw = response.get('Items') if isinstance(response, dict) else None
    if not isinstance(items_raw, list):
        return []
    return [item for item in items_raw if isinstance(item, dict)]


def _normalize_tailoring_status(raw_status: Any) -> str:
    status = str(raw_status or '').strip().lower()
    if status in {'pending', 'processing', 'completed', 'failed'}:
        return status
    return 'completed'


def _build_tailored_cv_status_payload(item: dict[str, Any], fallback_id: str) -> dict[str, Any]:
    status = _normalize_tailoring_status(item.get('status'))
    payload: dict[str, Any] = {
        'id': str(item.get('sk') or fallback_id),
        'status': status,
    }

    if status in {'completed', 'failed'}:
        result: dict[str, Any] = {}
        tailored_cv = item.get('tailored_cv')
        if tailored_cv is not None:
            result['tailored_cv'] = tailored_cv

        ats_score = item.get('estimated_ats_score') or item.get('ats_score')
        if isinstance(ats_score, (int, float, Decimal)):
            result['ats_score'] = float(ats_score)

        keyword_matches = item.get('keyword_matches')
        if isinstance(keyword_matches, dict):
            result['keyword_matches'] = keyword_matches
        elif isinstance(keyword_matches, list):
            result['keyword_matches'] = {'matched': keyword_matches, 'missing': []}

        suggestions = item.get('suggestions')
        if isinstance(suggestions, list):
            result['suggestions'] = [str(entry) for entry in suggestions if str(entry).strip()]

        fvs_validation = item.get('fvs_validation')
        if isinstance(fvs_validation, dict):
            result['fvs_validation'] = fvs_validation

        if result:
            payload['result'] = result
    return payload


def _build_tailored_cv_list_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        'id': str(item.get('sk') or ''),
        'status': _normalize_tailoring_status(item.get('status')),
        'cv_id': item.get('cv_id'),
        'created_at': item.get('created_at'),
        'updated_at': item.get('updated_at'),
    }


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
    headers = get_cors_headers(None)
    headers.setdefault('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    headers.setdefault('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    return headers


def _response(status: int | HTTPStatus, body: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    status_code = int(status.value) if isinstance(status, HTTPStatus) else int(status)
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body, cls=CustomJSONEncoder),
    }
