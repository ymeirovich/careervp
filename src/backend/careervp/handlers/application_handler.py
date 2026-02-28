"""Application recovery handler for GET /applications/{application_id}."""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from typing import Any

from aws_lambda_powertools.logging.correlation_paths import API_GATEWAY_REST
from aws_lambda_powertools.utilities.typing import LambdaContext

from careervp.dal.application_repository import ApplicationRepository
from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.dal.jobs_repository import JobsRepository
from careervp.handlers.auth_utils import extract_user_id
from careervp.handlers.utils.observability import logger, metrics, tracer

_application_repository: ApplicationRepository | None = None
_jobs_repository: JobsRepository | None = None

_ARTIFACT_TYPES: tuple[str, ...] = (
    'vpr',
    'cv_tailored',
    'cover_letter',
    'interview_prep',
    'gap_analysis',
)

_RELOAD_ROUTE_BY_STATE: dict[str, str] = {
    'created': '/applications',
    'cv_selected': '/applications',
    'gap_questions_pending': '/gap-questions',
    'gap_questions_ready': '/gap-questions',
    'gap_responses_submitted': '/gap-questions',
    'artifacts_generating': '/artifacts',
    'artifacts_completed': '/artifacts',
}


def _get_application_repository() -> ApplicationRepository:
    global _application_repository
    if _application_repository is None:
        table_name = (
            os.getenv('APPLICATIONS_TABLE_NAME')
            or os.getenv('DYNAMODB_TABLE_NAME')
            or os.getenv('TABLE_NAME')
            or ''
        )
        if not table_name:
            raise RuntimeError('APPLICATIONS_TABLE_NAME is required')
        _application_repository = ApplicationRepository(dal=DynamoDalHandler(table_name=table_name))
    return _application_repository


def _get_jobs_repository() -> JobsRepository:
    global _jobs_repository
    if _jobs_repository is None:
        _jobs_repository = JobsRepository()
    return _jobs_repository


def _response(status_code: HTTPStatus, body: dict[str, Any]) -> dict[str, Any]:
    return {
        'statusCode': status_code.value,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(body, default=str),
    }


def _extract_application_id(event: dict[str, Any]) -> str | None:
    path_parameters = event.get('pathParameters')
    if isinstance(path_parameters, dict):
        value = path_parameters.get('application_id') or path_parameters.get('applicationId')
        if isinstance(value, str) and value.strip():
            return value.strip()
    path = str(event.get('path', '')).strip('/')
    if path.startswith('applications/'):
        _, _, suffix = path.partition('/')
        resolved = suffix.strip()
        return resolved or None
    return None


def _build_artifacts(application: dict[str, Any]) -> dict[str, dict[str, Any]]:
    statuses = application.get('artifact_statuses')
    status_map = statuses if isinstance(statuses, dict) else {}
    return {
        artifact_type: {
            'status': str(status_map.get(artifact_type, 'pending')),
            'artifact_id': status_map.get(f'{artifact_type}_artifact_id'),
        }
        for artifact_type in _ARTIFACT_TYPES
    }


def _build_recovery_payload(application: dict[str, Any], job_record: dict[str, Any] | None) -> dict[str, Any]:
    state = str(application.get('state', 'created'))
    cv_id = application.get('cv_id')
    has_gap_payload = state in {
        'gap_questions_ready',
        'gap_responses_submitted',
        'artifacts_generating',
        'artifacts_completed',
    }
    gap_questions = application.get('gap_questions')
    gap_responses = application.get('gap_responses')
    return {
        'application': {
            'application_id': application.get('application_id'),
            'state': state,
            'created_at': application.get('created_at'),
            'trial_credit_consumed': bool(application.get('trial_credit_consumed', False)),
        },
        'job': job_record
        or {
            'job_id': application.get('job_id'),
        },
        'cv': {'cv_id': cv_id} if isinstance(cv_id, str) and cv_id.strip() else None,
        'gap_analysis': {
            'questions': gap_questions if has_gap_payload and isinstance(gap_questions, list) else [],
            'responses': gap_responses if has_gap_payload and isinstance(gap_responses, list) else [],
        },
        'artifacts': _build_artifacts(application),
        'reload_route': _RELOAD_ROUTE_BY_STATE.get(state, '/applications'),
    }


@logger.inject_lambda_context(correlation_id_path=API_GATEWAY_REST)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    _ = context
    method = str(event.get('httpMethod', '')).upper()
    if method != 'GET':
        return _response(HTTPStatus.METHOD_NOT_ALLOWED, {'error': 'Method not allowed'})

    user_id = extract_user_id(event)
    if not user_id:
        return _response(HTTPStatus.UNAUTHORIZED, {'error': 'Authentication required'})

    application_id = _extract_application_id(event)
    if not application_id:
        return _response(HTTPStatus.BAD_REQUEST, {'error': 'application_id is required'})

    repository = _get_application_repository()
    application = repository.get(application_id=application_id, user_id=user_id)
    if application is None:
        return _response(HTTPStatus.NOT_FOUND, {'error': 'Application not found'})

    owner_user_id = application.get('user_id')
    if isinstance(owner_user_id, str) and owner_user_id != user_id:
        return _response(HTTPStatus.FORBIDDEN, {'error': 'User can only access own applications'})

    job_record: dict[str, Any] | None = None
    try:
        jobs_repository = _get_jobs_repository()
        job_id = application.get('job_id')
        job_record = jobs_repository.get_job(str(job_id)) if isinstance(job_id, str) and job_id else None
    except Exception:
        job_record = None

    payload = _build_recovery_payload(application=application, job_record=job_record)
    return _response(HTTPStatus.OK, payload)


__all__ = ['lambda_handler']
