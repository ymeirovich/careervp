"""Lambda handler for CV tailoring requests."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from http import HTTPStatus
from typing import Any

from boto3.dynamodb.conditions import Attr
from pydantic import ValidationError

from careervp.dal import table_registry
from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.dal.jobs_repository import JobsRepository
from careervp.handlers.artifact_dependency_utils import (
    dependency_response_body,
    mark_requested_artifact_pending,
    resolve_handler_dependencies,
)
from careervp.handlers.auth_utils import extract_user_id
from careervp.handlers.cors_utils import get_cors_headers, set_request_origin
from careervp.logic.cv_tailoring import tailor_cv
from careervp.logic.cv_tailoring_ats import compute_ats_result
from careervp.logic.cv_tailoring_pipeline import run_cv_tailoring_pipeline
from careervp.logic.fvs_validator import create_fvs_baseline
from careervp.logic.llm_client import LLMClient
from careervp.logic.utils.llm_metering import bind_llm_usage_context
from careervp.models.api_models import CVTailoringRequest as APICVTailoringRequest
from careervp.models.cv_tailoring_models import TailorCVRequest, TailoringPreferences
from careervp.models.result import Result, ResultCode
from careervp.validation.cv_tailoring_validation import validate_job_description


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime, Decimal, and Pydantic objects."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            # DynamoDB returns Decimal for all numbers; preserve int/float distinction.
            return int(obj) if obj % 1 == 0 else float(obj)
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
    if _is_sfn_invoke(event):
        return _handle_sfn_invoke(event)

    set_request_origin(event)
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

    if method == 'PATCH' and _is_tailoring_patch_path(path):
        user_id = _get_user_id(event)
        if not user_id:
            return _response(HTTPStatus.UNAUTHORIZED, {'success': False, 'message': 'Missing or invalid authentication token'}, headers)
        return _patch_cv_tailored(event, user_id, headers)

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

    if method == 'POST' and path.endswith('/cancel'):
        user_id = _get_user_id(event)
        if not user_id:
            return _response(
                HTTPStatus.UNAUTHORIZED,
                {'success': False, 'message': 'Missing or invalid authentication token'},
                headers,
            )
        return _handle_cv_tailoring_cancel(event, user_id, headers)

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
    using_new_api = {'cv_id', 'job_id'}.issubset(request_data)
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


def _is_sfn_invoke(event: dict[str, Any]) -> bool:
    """Return True for the artifact-chain direct Lambda invoke payload."""
    return not event.get('httpMethod') and {'user_id', 'cv_id', 'job_id'}.issubset(event)


def _handle_sfn_invoke(event: dict[str, Any]) -> dict[str, Any]:
    """Run CV tailoring for Step Functions LambdaInvoke and return raw payload."""
    headers: dict[str, str] = {}
    request_data = {
        'cv_id': str(event.get('cv_id') or '').strip(),
        'job_id': str(event.get('job_id') or '').strip(),
        'vpr_id': str(event.get('vpr_id') or '').strip(),
    }
    user_id = str(event.get('user_id') or '').strip()
    if not user_id or not request_data['cv_id'] or not request_data['job_id']:
        raise ValueError('user_id, cv_id, and job_id are required for Step Functions CV tailoring')

    response = _handle_openapi_async_generate(event, request_data, headers, user_id)
    status_code = int(response.get('statusCode', HTTPStatus.INTERNAL_SERVER_ERROR))
    body = response.get('body')
    payload = json.loads(body) if isinstance(body, str) and body else {}
    if status_code >= HTTPStatus.BAD_REQUEST:
        raise RuntimeError(str(payload.get('message') or payload.get('error') or 'CV tailoring failed'))
    return payload


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

    table_name = table_registry.resolve_legacy_artifacts_table_name()
    dal = DynamoDalHandler(table_name)
    dependency_resolution = resolve_handler_dependencies(
        artifact_type='cv_tailored',
        application_id=job_id,
        user_id=user_id,
        dal=dal,
    )
    if dependency_resolution.status != 'ready':
        if dependency_resolution.status == 'dependency_generating':
            mark_requested_artifact_pending(application_id=job_id, user_id=user_id, artifact_type='cv_tailored')
        return _response(
            HTTPStatus(dependency_resolution.http_status),
            dependency_response_body(dependency_resolution, requested_artifact='cv_tailored'),
            headers,
        )

    resolved_vpr_ref = dependency_resolution.resolved_upstream.get('vpr')
    resolved_vpr = resolved_vpr_ref.artifact if resolved_vpr_ref is not None else None
    if vpr_id is None and resolved_vpr_ref is not None and resolved_vpr_ref.artifact_id is not None:
        vpr_id = resolved_vpr_ref.artifact_id

    # ── 1. Fetch master CV ────────────────────────────────────────────────────
    master_cv = dal.get_cv(user_id=user_id)
    if master_cv is None:
        return _response(
            HTTPStatus.NOT_FOUND,
            {'success': False, 'code': ResultCode.CV_NOT_FOUND, 'message': 'CV not found'},
            headers,
        )

    # ── 2. Fetch job record from Jobs table (primary source of job description) ──
    # job_id == the application's stable job UUID from the URL (jobId param).
    # The VPR stored model (VPR) does not carry the original job_posting —
    # that lives only on VPRRequest. The Jobs table (VPR_JOBS_TABLE_NAME) is the
    # canonical store for job title, company, and description.
    job_description = ''
    job_title = ''
    company_name = ''
    try:
        job_record = JobsRepository().get_job(job_id) or {}
        job_description = str(job_record.get('description') or '').strip()
        job_title = str(job_record.get('title') or job_record.get('role_title') or '').strip()
        company_name = str(job_record.get('company_name') or job_record.get('company') or '').strip()
        if job_description:
            logger.info('job_description resolved from JobsRepository', job_id=job_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning('Failed to fetch job record', job_id=job_id, error=str(exc))

    if not job_description:
        logger.error(
            'job_description unavailable — CV tailoring will produce poor output. Ensure job_id matches a record in VPR_JOBS_TABLE_NAME.',
            job_id=job_id,
        )
        job_description = f'Job posting for {job_title or job_id}'

    # ── 3. Fetch VPR (optional, enriches Stage 1 keyword mapping) ───────────────
    vpr = resolved_vpr
    if vpr is None and vpr_id:
        try:
            vpr_result = dal.get_vpr(application_id=vpr_id)
            if vpr_result.success and vpr_result.data is not None:
                vpr = vpr_result.data
        except Exception as exc:  # noqa: BLE001
            logger.warning('VPR fetch failed — proceeding without VPR', vpr_id=vpr_id, error=str(exc))

    # ── 3. Resolve job description (VPR → JobsRepository → placeholder) ─────
    job_description = ''
    job_title = ''
    company_name = ''

    # Primary: extract from VPR.job_posting (most reliable — already structured)
    if vpr is not None and hasattr(vpr, 'job_posting') and vpr.job_posting is not None:
        jp = vpr.job_posting
        job_description = str(getattr(jp, 'description', '') or '').strip()
        if not job_description and hasattr(jp, 'requirements'):
            reqs = getattr(jp, 'requirements', [])
            if isinstance(reqs, list) and reqs:
                job_description = '\n'.join(str(r) for r in reqs)
        job_title = str(getattr(jp, 'role_title', '') or getattr(jp, 'title', '') or '').strip()
        company_name = str(getattr(jp, 'company_name', '') or getattr(jp, 'company', '') or '').strip()
        if job_description:
            logger.info('job_description resolved from VPR.job_posting', job_id=job_id)

    # Secondary fallback: JobsRepository (stores API-submitted job records; not VPR queue entries)
    if not job_description:
        try:
            jobs_repo = JobsRepository()
            job_record = jobs_repo.get_job(job_id) or {}
            job_description = str(job_record.get('description') or '').strip()
            job_title = job_title or str(job_record.get('title') or job_record.get('role_title') or '').strip()
            company_name = company_name or str(job_record.get('company_name') or job_record.get('company') or '').strip()
            if job_description:
                logger.info('job_description resolved from JobsRepository', job_id=job_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning('Failed to fetch job record from JobsRepository', job_id=job_id, error=str(exc))

    if not job_description:
        logger.error('job_description unavailable — refusing to generate from placeholder', job_id=job_id)
        return _response(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            {
                'success': False,
                'code': ResultCode.VALIDATION_ERROR,
                'message': 'Job description could not be resolved. Ensure the job record exists or provide a vpr_id.',
            },
            headers,
        )

    # ── 4. Run 3-stage pipeline ───────────────────────────────────────────────
    llm_client = LLMClient()
    with bind_llm_usage_context(application_id=job_id, user_id=user_id):
        pipeline_result = run_cv_tailoring_pipeline(
            cv=master_cv,
            job_description=job_description,
            vpr=vpr,
            llm_client=llm_client,
        )

    # ── 5. Build artifact ─────────────────────────────────────────────────────
    request_id = f'cv-tail-{uuid.uuid4()}'
    now_iso = datetime.now(timezone.utc).isoformat()
    artifact_sk = table_registry.tailored_cv_artifact_id(request_id)
    ttl = int((datetime.now(timezone.utc) + timedelta(days=730)).timestamp())

    if pipeline_result.success and pipeline_result.data is not None:
        stage3 = pipeline_result.data
        cv_sections_dict: dict[str, Any] = stage3.cv_sections.model_dump(mode='json') if stage3.cv_sections else {}
        tailored_cv_text = (stage3.cv_sections.summary if stage3.cv_sections else '') or ''

        # Deterministic ATS rules engine — 5-component breakdown
        ats_result = compute_ats_result(stage3.cv_sections, stage3.keywords_to_emphasize)

        fact_verification_detail: dict[str, Any] = {
            'passed': stage3.fact_verification_passed,
            'items_corrected': len(stage3.items_corrected),
            'items_removed': len(stage3.items_removed),
            'hallucination_flags_from_ai': [],
            'checks': (
                [{'check_name': m, 'passed': False, 'action_taken': 'corrected', 'detail': m} for m in stage3.items_corrected]
                + [{'check_name': m, 'passed': False, 'action_taken': 'removed', 'detail': m} for m in stage3.items_removed]
            ),
        }

        artifact: dict[str, Any] = {
            **table_registry.legacy_item_key(user_id, artifact_sk),
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
            'ats_score': ats_result.total_score,
            'ats_grade': ats_result.grade,
            'ats_result': ats_result.model_dump(),
            'keywords_matched': ats_result.keywords_matched,
            'keywords_missing': ats_result.keywords_missing,
            'keyword_match_score': ats_result.keyword_match_score_1_10,
            'fact_verification_detail': fact_verification_detail,
            # Kept for backward-compat (old UI versions may read fvs_validation)
            'fvs_validation': {
                'is_valid': stage3.fact_verification_passed,
                'violations': stage3.items_removed,
            },
            'version': 1,
            'language': 'en',
            'created_at': now_iso,
            'updated_at': now_iso,
            'ttl': ttl,
        }
        final_status = 'completed'
    else:
        error_msg = (pipeline_result.error if pipeline_result else None) or 'Pipeline execution failed'
        logger.error('CV tailoring pipeline failed', job_id=job_id, error=error_msg)
        artifact = {
            **table_registry.legacy_item_key(user_id, artifact_sk),
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
    # DynamoDB rejects Python float — convert via JSON round-trip so all
    # floating-point values (e.g. ATSComponents scores) become Decimal.
    artifact_for_dynamo: dict[str, Any] = json.loads(json.dumps(artifact), parse_float=Decimal)
    dal._get_db_handler(table_name).put_item(Item=artifact_for_dynamo)

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
    dal = DynamoDalHandler(table_registry.resolve_legacy_artifacts_table_name())
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
    dal = DynamoDalHandler(table_registry.resolve_legacy_artifacts_table_name())
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


_CV_TAILORING_TERMINAL_STATUSES = {'COMPLETED', 'FAILED', 'CANCELLED'}


def _handle_cv_tailoring_cancel(
    event: dict[str, Any],
    user_id: str,
    headers: dict[str, str],
) -> dict[str, Any]:
    """Handle POST /cv-tailoring/{cvTailoringId}/cancel."""
    import boto3 as _boto3

    path_params = event.get('pathParameters') or {}
    cv_tailoring_id = str(path_params.get('cvTailoringId') or '').strip()
    if not cv_tailoring_id:
        return _response(HTTPStatus.BAD_REQUEST, {'error': 'Missing cvTailoringId'}, headers)

    table_name = table_registry.resolve_legacy_artifacts_table_name()
    table = _boto3.resource('dynamodb').Table(table_name)
    sk = table_registry.tailored_cv_artifact_id(cv_tailoring_id)

    try:
        get_resp = table.get_item(Key=table_registry.legacy_item_key(user_id, sk))
        item = (get_resp or {}).get('Item')
    except Exception as exc:
        logger.error('DynamoDB error during cv tailoring cancel', error=str(exc))
        return _response(HTTPStatus.INTERNAL_SERVER_ERROR, {'error': 'Internal server error'}, headers)

    if not item:
        try:
            query_resp = table.query(
                KeyConditionExpression='pk = :uid AND begins_with(sk, :prefix)',
                ExpressionAttributeValues={
                    ':uid': user_id,
                    ':prefix': table_registry.tailored_cv_artifact_id(cv_tailoring_id),
                },
                Limit=1,
            )
            items = (query_resp or {}).get('Items', [])
            item = items[0] if items else None
        except Exception:
            item = None
        if not item:
            return _response(HTTPStatus.NOT_FOUND, {'error': 'CV tailoring not found'}, headers)

    status = str(item.get('status', '')).upper()
    if status in _CV_TAILORING_TERMINAL_STATUSES:
        return _response(HTTPStatus.CONFLICT, {'error': 'Cannot cancel terminal task'}, headers)

    item_pk = str(item.get('pk', user_id))
    item_sk = str(item.get('sk', sk))
    table.update_item(
        Key=table_registry.legacy_item_key(item_pk, item_sk),
        UpdateExpression='SET #s = :status',
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={':status': 'CANCELLED'},
    )
    return _response(HTTPStatus.OK, {'status': 'cancelled'}, headers)


def _get_user_id(event: dict[str, Any], request_data: dict[str, Any] | None = None) -> str | None:
    _ = request_data
    return extract_user_id(event)


def _is_tailoring_status_path(path: str) -> bool:
    return path.startswith('/cv-tailoring/') and path != '/cv-tailoring/generate'


def _is_tailoring_delete_path(path: str) -> bool:
    if not path.startswith('/cv-tailoring/') or path == '/cv-tailoring/generate':
        return False
    return not path.endswith('/status')


def _is_tailoring_patch_path(path: str) -> bool:
    if not path.startswith('/cv-tailoring/') or path == '/cv-tailoring/generate':
        return False
    return not path.endswith('/status') and not path.endswith('/cancel')


def _patch_cv_tailored(event: dict[str, Any], user_id: str, headers: dict[str, str]) -> dict[str, Any]:
    """Handle PATCH /cv-tailoring/{cvTailoringId} — update cv_sections or tailored_cv text."""
    cv_tailoring_id = _extract_cv_tailoring_id(event)
    if not cv_tailoring_id:
        return _response(HTTPStatus.BAD_REQUEST, {'success': False, 'message': 'Missing cvTailoringId'}, headers)

    try:
        body: dict[str, Any] = json.loads(event.get('body', '{}') or '{}')
    except json.JSONDecodeError:
        return _response(HTTPStatus.BAD_REQUEST, {'success': False, 'message': 'Invalid JSON'}, headers)

    cv_sections = body.get('cv_sections')
    tailored_cv = body.get('tailored_cv')
    if cv_sections is None and tailored_cv is None:
        return _response(HTTPStatus.BAD_REQUEST, {'success': False, 'message': 'cv_sections or tailored_cv required'}, headers)

    item = _get_tailored_cv_item(user_id=user_id, cv_tailoring_id=cv_tailoring_id)
    if item is None:
        return _response(HTTPStatus.NOT_FOUND, {'success': False, 'message': 'Tailored CV not found'}, headers)

    import datetime as _dt

    import boto3 as _boto3

    table_name = table_registry.resolve_legacy_artifacts_table_name()
    table = _boto3.resource('dynamodb').Table(table_name)
    pk = str(item.get('pk', user_id))
    sk = str(item.get('sk', table_registry.tailored_cv_artifact_id(cv_tailoring_id)))
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()

    update_parts: list[str] = ['updated_at = :now']
    attr_values: dict[str, Any] = {':now': now}
    if cv_sections is not None:
        update_parts.append('cv_sections = :sections')
        attr_values[':sections'] = cv_sections
    if tailored_cv is not None:
        update_parts.append('tailored_cv = :tv')
        attr_values[':tv'] = tailored_cv

    try:
        table.update_item(
            Key=table_registry.legacy_item_key(pk, sk),
            UpdateExpression='SET ' + ', '.join(update_parts),
            ExpressionAttributeValues=attr_values,
        )
    except Exception as exc:
        logger.error('Failed to update cv_tailored', cv_tailoring_id=cv_tailoring_id, error=str(exc))
        return _response(HTTPStatus.INTERNAL_SERVER_ERROR, {'success': False, 'message': 'Failed to update tailored CV'}, headers)

    updated_item = dict(item)
    updated_item['updated_at'] = now
    if cv_sections is not None:
        updated_item['cv_sections'] = cv_sections
    if tailored_cv is not None:
        updated_item['tailored_cv'] = tailored_cv

    payload = _build_tailored_cv_status_payload(updated_item, cv_tailoring_id)
    return _response(HTTPStatus.OK, payload, headers)


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
    legacy_table_name = table_registry.resolve_legacy_artifacts_table_name()
    table = DynamoDalHandler(legacy_table_name)._get_db_handler(legacy_table_name)

    # Try direct get_item first
    try:
        key_response = table.get_item(Key=table_registry.legacy_item_key(user_id, cv_tailoring_id))
        item = key_response.get('Item') if isinstance(key_response, dict) else None
        if isinstance(item, dict):
            return item
    except Exception:  # noqa: BLE001
        pass

    try:
        prefixed_response = table.get_item(Key=table_registry.legacy_item_key(user_id, table_registry.tailored_cv_artifact_id(cv_tailoring_id)))
        prefixed_item = prefixed_response.get('Item') if isinstance(prefixed_response, dict) else None
        if isinstance(prefixed_item, dict):
            return prefixed_item
    except Exception:  # noqa: BLE001
        pass

    try:
        query_response = table.query(
            KeyConditionExpression=table_registry.legacy_key_condition(user_id, table_registry.TAILORED_CV_SORT_KEY_PREFIX),
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
    dal = DynamoDalHandler(table_registry.resolve_legacy_artifacts_table_name())
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

    # Top-level metadata fields
    version = item.get('version')
    if version is not None:
        payload['version'] = int(version)
    language = item.get('language')
    if language is not None:
        payload['language'] = str(language)
    generated_at = item.get('created_at') or item.get('generated_at')
    if generated_at is not None:
        payload['generated_at'] = str(generated_at)

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

        ats_grade = item.get('ats_grade')
        if isinstance(ats_grade, str):
            result['ats_grade'] = ats_grade

        ats_result_raw = item.get('ats_result')
        if isinstance(ats_result_raw, dict):
            result['ats_result'] = ats_result_raw

        keyword_match_score = item.get('keyword_match_score')
        if isinstance(keyword_match_score, (int, float, Decimal)):
            result['keyword_match_score'] = int(keyword_match_score)

        keywords_matched = item.get('keywords_matched')
        if isinstance(keywords_matched, list):
            result['keywords_matched'] = keywords_matched

        keywords_missing = item.get('keywords_missing')
        if isinstance(keywords_missing, list):
            result['keywords_missing'] = keywords_missing

        fact_verification_detail = item.get('fact_verification_detail')
        if isinstance(fact_verification_detail, dict):
            result['fact_verification_detail'] = fact_verification_detail
        # fvs_validation is intentionally NOT exposed in the API response

        suggestions = item.get('suggestions')
        if isinstance(suggestions, list):
            result['suggestions'] = [str(entry) for entry in suggestions if str(entry).strip()]

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
    # Try to extract language and job_title from the nested tailored_cv model
    nested = item.get('tailored_cv') or {}
    language = item.get('language') or (nested.get('language') if isinstance(nested, dict) else None)
    job_title = item.get('job_title') or (nested.get('job_title') if isinstance(nested, dict) else None)
    return {
        'id': item_id,
        'status': _normalize_tailoring_status(item.get('status')),
        'cv_id': item.get('cv_id'),
        'job_id': item.get('job_id'),
        'language': language,
        'job_title': job_title,
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
    headers.setdefault('Access-Control-Allow-Methods', 'GET,POST,PATCH,DELETE,OPTIONS')
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
