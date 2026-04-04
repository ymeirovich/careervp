"""Lambda handler for CV tailoring requests."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from http import HTTPStatus
from typing import Any

from boto3.dynamodb.conditions import Attr, Key
from pydantic import ValidationError

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.dal.jobs_repository import JobsRepository
from careervp.handlers.auth_utils import extract_user_id
from careervp.handlers.cors_utils import get_cors_headers
from careervp.logic.cv_tailoring import tailor_cv
from careervp.logic.cv_tailoring_pipeline import run_cv_tailoring_pipeline
from careervp.logic.fvs_validator import create_fvs_baseline
from careervp.logic.llm_client import LLMClient
from careervp.models.api_models import CVTailoringRequest as APICVTailoringRequest
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
    aws_request_id = getattr(context, 'aws_request_id', 'unknown')
    request_context = {
        'event': 'cv_tailoring_request_received',
        'http_method': method,
        'path': path,
        'aws_request_id': aws_request_id,
    }
    logger.info('cv_tailoring request received', **request_context)
    logger.debug(
        'cv_tailoring request body',
        event='cv_tailoring_request_received',
        http_method=method,
        path=path,
        aws_request_id=aws_request_id,
        request_body=_request_body_for_logging(event),
    )

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

    if method == 'GET' and path in {'/users/me/tailored-cvs', '/cv-tailorings'}:
        logger.info(
            'cv_tailoring route selected',
            event='cv_tailoring_route_selected',
            http_method=method,
            path=path,
            route='list_tailored_cvs',
            aws_request_id=aws_request_id,
        )
        return list_tailored_cvs(event)

    if method == 'DELETE' and _is_tailoring_delete_path(path):
        logger.info(
            'cv_tailoring route selected',
            event='cv_tailoring_route_selected',
            http_method=method,
            path=path,
            route='delete_tailored_cv',
            aws_request_id=aws_request_id,
        )
        return delete_tailored_cv(event)

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
        request_data = json.loads(event.get('body') or '{}')
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
        _validate_openapi_cv_tailoring_payload(request_data)
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

    user_id = _get_user_id(event, request_data)
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

    if 'preferences' in request_data and not isinstance(request_data['preferences'], dict):
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
    using_new_api = {'cv_id', 'job_id', 'vpr_id'}.issubset(request_data)
    if using_new_api:
        return _handle_openapi_async_generate(event, request_data, headers, user_id)

    cv_id = request_data.get('cv_id')
    job_id = request_data.get('job_id')
    job_description = request_data.get('job_description')

    # If using new API flow, fetch job_description from job_id
    # Note: using_new_api=True returns early via _handle_openapi_async_generate above;
    # this branch is retained as dead-code guard only and uses DynamoDalHandler if reached.
    if using_new_api and job_description is None and job_id:
        pass  # job_description fetch handled in _handle_openapi_async_generate

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
    if isinstance(request_data.get('preferences'), dict):
        preferences = TailoringPreferences(**request_data['preferences'])

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


def _handle_openapi_async_generate(  # noqa: C901
    event: dict[str, Any],
    request_data: dict[str, Any],
    headers: dict[str, str],
    user_id: str,
) -> dict[str, Any]:
    """Run the 3-stage CV tailoring pipeline and persist the artifact synchronously."""
    _ = event
    cv_id = str(request_data.get('cv_id') or '').strip()
    job_id = str(request_data.get('job_id') or '').strip()
    vpr_id = str(request_data.get('vpr_id') or '').strip() or None

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

    table_name = os.environ.get('DYNAMODB_TABLE_NAME') or os.environ.get('TABLE_NAME', '')
    dal = DynamoDalHandler(table_name)

    # ── 1. Fetch master CV ────────────────────────────────────────────────────
    master_cv = dal.get_cv(user_id=user_id)
    if master_cv is None:
        return _response(
            HTTPStatus.NOT_FOUND,
            {'success': False, 'code': ResultCode.CV_NOT_FOUND, 'message': 'CV not found'},
            headers,
        )

    # ── 2. Fetch job description from jobs table ──────────────────────────────
    job_description = ''
    job_title = ''
    company_name = ''
    try:
        jobs_repo = JobsRepository()
        job_record = jobs_repo.get_job(job_id) or {}
        job_description = str(job_record.get('description') or '').strip()
        job_title = str(job_record.get('title') or job_record.get('role_title') or '').strip()
        company_name = str(job_record.get('company_name') or job_record.get('company') or '').strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning('Failed to fetch job record', job_id=job_id, error=str(exc))

    if not job_description:
        logger.warning('Empty job_description — using placeholder', job_id=job_id)
        job_description = f'Job posting {job_title or job_id}'

    # ── 3. Fetch VPR (optional, graceful degradation) ────────────────────────
    vpr = None
    if vpr_id:
        try:
            vpr_result = dal.get_vpr(application_id=vpr_id)
            if vpr_result.success and vpr_result.data is not None:
                vpr = vpr_result.data
        except Exception as exc:  # noqa: BLE001
            logger.warning('VPR fetch failed — proceeding without VPR', vpr_id=vpr_id, error=str(exc))

    # ── 4. Run 3-stage pipeline ───────────────────────────────────────────────
    llm_client = LLMClient()
    pipeline_result = run_cv_tailoring_pipeline(
        cv=master_cv,
        job_description=job_description,
        vpr=vpr,
        llm_client=llm_client,
    )

    # ── 5. Build artifact ─────────────────────────────────────────────────────
    request_id = f'cv-tail-{uuid.uuid4()}'
    now_iso = datetime.now(timezone.utc).isoformat()
    artifact_sk = f'ARTIFACT#CV_TAILORED#{request_id}'
    ttl = int((datetime.now(timezone.utc) + timedelta(days=730)).timestamp())

    if pipeline_result.success and pipeline_result.data is not None:
        stage3 = pipeline_result.data
        cv_sections_dict: dict[str, Any] = stage3.cv_sections.model_dump(mode='json') if stage3.cv_sections else {}
        tailored_cv_text = (stage3.cv_sections.summary if stage3.cv_sections else '') or ''

        # ATS score: propagated from Stage2 verification through Stage3Result (0-100 scale)
        ats_score = stage3.ats_keyword_score if stage3.ats_keyword_score > 0 else 75

        # Keyword matches: matched = keywords found in summary + experience bullets
        cv_text_lower = (tailored_cv_text + ' ' + json.dumps(cv_sections_dict)).lower()
        matched_keywords = [
            kw
            for kw in ([kw for exp in cv_sections_dict.get('experience', []) for kw in exp.get('bullets', [])])
            if isinstance(kw, str) and kw.lower() in cv_text_lower
        ]

        artifact: dict[str, Any] = {
            'pk': user_id,
            'sk': artifact_sk,
            'request_id': request_id,
            'entity_type': 'CV_TAILORING',
            'artifact_type': 'cv_tailored',
            'status': 'completed',
            'cv_id': cv_id,
            'job_id': job_id,
            'job_title': job_title,
            'company_name': company_name,
            'cv_sections': cv_sections_dict,
            'tailored_cv': tailored_cv_text,  # backward-compat: summary text
            'ats_score': ats_score,
            'keyword_matches': {'matched': matched_keywords, 'missing': []},
            'suggestions': ['CV tailored using 3-stage pipeline with fact verification.'],
            'fvs_validation': {
                'is_valid': stage3.fact_verification_passed,
                'violations': stage3.items_removed,
            },
            'created_at': now_iso,
            'updated_at': now_iso,
            'ttl': ttl,
        }
        final_status = 'completed'
    else:
        error_msg = (pipeline_result.error if pipeline_result else None) or 'Pipeline execution failed'
        logger.error('CV tailoring pipeline failed', job_id=job_id, error=error_msg)
        artifact = {
            'pk': user_id,
            'sk': artifact_sk,
            'request_id': request_id,
            'entity_type': 'CV_TAILORING',
            'artifact_type': 'cv_tailored',
            'status': 'failed',
            'cv_id': cv_id,
            'job_id': job_id,
            'error': error_msg,
            'created_at': now_iso,
            'updated_at': now_iso,
            'ttl': ttl,
        }
        final_status = 'failed'

    # ── 6. Persist artifact ───────────────────────────────────────────────────
    dal._get_db_handler(table_name).put_item(Item=artifact)

    _update_application_artifact(
        application_id=job_id,
        user_id=user_id,
        artifact_type='cv_tailored',
        artifact_id=request_id,
    )

    return _response(
        HTTPStatus.ACCEPTED,
        {
            'request_id': request_id,
            'job_id': request_id,
            'status': final_status,
            'estimated_time_seconds': 0,
        },
        headers,
    )


def _update_application_artifact(
    application_id: str,
    user_id: str,
    artifact_type: str,
    artifact_id: str,
) -> None:
    """Propagate artifact completion to the application record's artifact_statuses.

    Silently ignored when the application record does not exist — non-fatal
    because the session-local frontend fallback handles this case.
    """
    if not application_id or not user_id:
        return
    app_table = os.environ.get('APPLICATIONS_TABLE_NAME') or os.environ.get('DYNAMODB_TABLE_NAME') or ''
    if not app_table:
        return
    try:
        from careervp.dal.application_repository import ApplicationRepository

        app_repo = ApplicationRepository(DynamoDalHandler(app_table))
        app_repo.update_artifact_with_id(
            application_id=application_id,
            user_id=user_id,
            artifact_type=artifact_type,
            status='completed',
            artifact_id=artifact_id,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(
            'Could not update application artifact_statuses for cv_tailored',
            artifact_type=artifact_type,
            error=str(e),
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


def delete_tailored_cv(event: dict[str, Any]) -> dict[str, Any]:
    """Handle DELETE /cv-tailoring/{cvTailoringId}."""
    headers = _cors_headers()
    method = str(event.get('httpMethod', '')).upper()
    path = str(event.get('path', '')).rstrip('/')
    request_context = {
        'http_method': method,
        'path': path,
        'event': 'cv_tailoring_delete_started',
    }
    user_id = _get_user_id(event)
    logger.info('cv_tailoring delete started', user_id=user_id, **request_context)
    logger.debug(
        'cv_tailoring delete request body',
        user_id=user_id,
        request_body=_request_body_for_logging(event),
        **request_context,
    )
    if not user_id:
        return _response(
            HTTPStatus.UNAUTHORIZED,
            {
                'success': False,
                'code': ResultCode.UNAUTHORIZED,
                'message': 'Missing or invalid authentication token',
            },
            headers,
            log_context={
                **request_context,
                'event': 'cv_tailoring_response_sent',
                'user_id_hash_or_id': user_id,
            },
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
            log_context={
                **request_context,
                'event': 'cv_tailoring_response_sent',
                'user_id_hash_or_id': user_id,
            },
        )

    logger.info(
        'cv_tailoring delete invoking dal',
        event='cv_tailoring_delete_started',
        http_method=method,
        path=path,
        user_id=user_id,
        cv_tailoring_id=cv_tailoring_id,
    )
    dal = DynamoDalHandler((os.environ.get('DYNAMODB_TABLE_NAME') or os.environ.get('TABLE_NAME', '')))
    delete_result = dal.delete_tailored_cv(user_id=user_id, cv_tailoring_id=cv_tailoring_id)
    logger.info(
        'cv_tailoring delete dal result',
        event='cv_tailoring_delete_dal_result',
        http_method=method,
        path=path,
        user_id=user_id,
        cv_tailoring_id=cv_tailoring_id,
        success=delete_result.success,
        result_code=delete_result.code,
        error_message=delete_result.error,
    )
    if not delete_result.success:
        if delete_result.code == ResultCode.CV_NOT_FOUND:
            return _response(
                HTTPStatus.NOT_FOUND,
                {
                    'success': False,
                    'code': ResultCode.CV_NOT_FOUND,
                    'message': 'Tailored CV not found',
                },
                headers,
                log_context={
                    **request_context,
                    'event': 'cv_tailoring_response_sent',
                    'user_id_hash_or_id': user_id,
                    'cv_tailoring_id': cv_tailoring_id,
                    'result_code': delete_result.code,
                    'error_message': delete_result.error,
                },
            )
        return _response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {
                'success': False,
                'code': delete_result.code,
                'message': 'Failed to delete tailored CV',
            },
            headers,
            log_context={
                **request_context,
                'event': 'cv_tailoring_response_sent',
                'user_id_hash_or_id': user_id,
                'cv_tailoring_id': cv_tailoring_id,
                'result_code': delete_result.code,
                'error_message': delete_result.error,
            },
        )

    return _response(
        HTTPStatus.OK,
        {
            'success': True,
            'id': cv_tailoring_id,
            'status': 'deleted',
        },
        headers,
        log_context={
            **request_context,
            'event': 'cv_tailoring_response_sent',
            'user_id_hash_or_id': user_id,
            'cv_tailoring_id': cv_tailoring_id,
            'result_code': delete_result.code,
            'error_message': None,
        },
    )


def _fetch_and_tailor_cv(request: TailorCVRequest) -> Result[Any]:
    """Fetch CV from DAL and invoke tailoring logic."""
    dal = DynamoDalHandler((os.environ.get('DYNAMODB_TABLE_NAME') or os.environ.get('TABLE_NAME', '')))
    llm_client = LLMClient()

    if not request.user_id:
        return Result(
            success=False,
            error='User ID is required',
            code=ResultCode.MISSING_REQUIRED_FIELD,
        )

    master_cv = dal.get_cv(user_id=request.user_id)
    if not master_cv:
        return Result(
            success=False,
            error=f"CV with id '{request.cv_id}' not found",
            code=ResultCode.CV_NOT_FOUND,
        )

    if master_cv.user_id and request.user_id and master_cv.user_id != request.user_id:
        return Result(
            success=False,
            error='User does not have access to this CV',
            code=ResultCode.FORBIDDEN,
        )

    if request.cv_id and not master_cv.cv_id:
        master_cv.cv_id = request.cv_id
    baseline = create_fvs_baseline(master_cv)

    return tailor_cv(
        master_cv=master_cv,
        job_description=request.job_description,
        preferences=request.preferences,
        fvs_baseline=baseline,
        dal=dal,
        llm_client=llm_client,
    )


def _get_user_id(event: dict[str, Any], request_data: dict[str, Any] | None = None) -> str | None:
    _ = request_data
    return extract_user_id(event)


def _is_tailoring_status_path(path: str) -> bool:
    return path.startswith('/cv-tailoring/') and path != '/cv-tailoring/generate'


def _is_tailoring_delete_path(path: str) -> bool:
    if not path.startswith('/cv-tailoring/') or path == '/cv-tailoring/generate':
        return False
    return not path.endswith('/status')


def _extract_cv_tailoring_id(event: dict[str, Any]) -> str | None:
    path_parameters = event.get('pathParameters')
    if isinstance(path_parameters, dict):
        for key in ('cvTailoringId', 'cv_tailoring_id', 'id', 'job_id', 'jobId'):
            value = path_parameters.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    path = str(event.get('path', '')).rstrip('/')
    if path.startswith('/cv-tailoring/'):
        candidate = path.removeprefix('/cv-tailoring/').strip()
        if candidate.endswith('/status'):
            candidate = candidate[: -len('/status')]
        if candidate and candidate != 'generate':
            return candidate
    return None


def _get_tailored_cv_item(user_id: str, cv_tailoring_id: str) -> dict[str, Any] | None:
    table = DynamoDalHandler((os.environ.get('DYNAMODB_TABLE_NAME') or os.environ.get('TABLE_NAME', '')))._get_db_handler(
        (os.environ.get('DYNAMODB_TABLE_NAME') or os.environ.get('TABLE_NAME', ''))
    )

    # Try direct get_item first
    try:
        key_response = table.get_item(Key={'pk': user_id, 'sk': cv_tailoring_id})
        item = key_response.get('Item') if isinstance(key_response, dict) else None
        if isinstance(item, dict):
            return item
    except Exception:  # noqa: BLE001
        pass

    try:
        prefixed_response = table.get_item(Key={'pk': user_id, 'sk': f'ARTIFACT#CV_TAILORED#{cv_tailoring_id}'})
        prefixed_item = prefixed_response.get('Item') if isinstance(prefixed_response, dict) else None
        if isinstance(prefixed_item, dict):
            return prefixed_item
    except Exception:  # noqa: BLE001
        pass

    try:
        query_response = table.query(
            KeyConditionExpression=Key('pk').eq(user_id) & Key('sk').begins_with('ARTIFACT#CV_TAILORED#'),
            FilterExpression=Attr('request_id').eq(cv_tailoring_id),
            Limit=1,
        )
        query_items = query_response.get('Items') if isinstance(query_response, dict) else None
        if isinstance(query_items, list) and query_items and isinstance(query_items[0], dict):
            return query_items[0]
    except Exception:  # noqa: BLE001
        pass

    return None


def _list_tailored_cv_items(user_id: str) -> list[dict[str, Any]]:
    dal = DynamoDalHandler((os.environ.get('DYNAMODB_TABLE_NAME') or os.environ.get('TABLE_NAME', '')))
    result = dal.list_tailored_cvs(user_id)
    if not result.success or not isinstance(result.data, list):
        return []
    items = []
    for cv in result.data:
        if hasattr(cv, 'model_dump'):
            items.append(cv.model_dump(mode='json'))
        elif isinstance(cv, dict):
            items.append(cv)
    return items


def _normalize_tailoring_status(raw_status: Any) -> str:
    status = str(raw_status or '').strip().lower()
    if status in {'pending', 'processing', 'completed', 'failed'}:
        return status
    return 'completed'


def _build_tailored_cv_status_payload(item: dict[str, Any], fallback_id: str) -> dict[str, Any]:  # noqa: C901
    status = _normalize_tailoring_status(item.get('status'))
    payload: dict[str, Any] = {
        'id': str(item.get('request_id') or item.get('sk') or fallback_id),
        'status': status,
    }

    if status in {'completed', 'failed'}:
        result: dict[str, Any] = {}
        tailored_cv = item.get('tailored_cv')
        if tailored_cv is not None:
            result['tailored_cv'] = tailored_cv

        cv_sections = item.get('cv_sections')
        if isinstance(cv_sections, dict):
            result['cv_sections'] = cv_sections

        ats_score = item.get('estimated_ats_score') or item.get('ats_score')
        if isinstance(ats_score, (int, float, Decimal)):
            result['ats_score'] = int(ats_score)

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

        error = item.get('error')
        if error is not None:
            result['error'] = str(error)

        if result:
            payload['result'] = result
    return payload


def _build_tailored_cv_list_item(item: dict[str, Any]) -> dict[str, Any]:
    sk = str(item.get('sk', '') or '')
    if sk.startswith('ARTIFACT#CV_TAILORED#'):
        item_id = sk.removeprefix('ARTIFACT#CV_TAILORED#')
    else:
        item_id = sk
    return {
        'id': item_id,
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
    headers.setdefault('Access-Control-Allow-Methods', 'GET,POST,DELETE,OPTIONS')
    headers.setdefault('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    return headers


def _request_body_for_logging(event: dict[str, Any]) -> Any:
    body = event.get('body')
    if body is None:
        return None
    if isinstance(body, (dict, list)):
        return body
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return body
    return str(body)


def _response(
    status: int | HTTPStatus,
    body: dict[str, Any],
    headers: dict[str, str],
    log_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    status_code = int(status.value) if isinstance(status, HTTPStatus) else int(status)
    if log_context is not None:
        logger.info('cv_tailoring response sent', status_code=status_code, **log_context)
        logger.debug(
            'cv_tailoring response body',
            status_code=status_code,
            response_body=body,
            **log_context,
        )
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body, cls=CustomJSONEncoder),
    }
