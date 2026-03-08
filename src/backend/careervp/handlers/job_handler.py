"""
Job CRUD handler for OpenAPI `/jobs` endpoints.

Implements:
- POST /jobs
- GET /jobs
- GET /jobs/{job_id}
"""

import json
import os
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any

from aws_lambda_powertools.event_handler import Response, content_types
from aws_lambda_powertools.logging.correlation_paths import API_GATEWAY_REST
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.dal.jobs_repository import JobsRepository
from careervp.handlers.auth_utils import extract_user_id
from careervp.handlers.utils.observability import logger, tracer
from careervp.handlers.utils.rest_api_resolver import app
from careervp.logic.trial_service import TrialExhaustedException, TrialExpiredException, TrialService
from careervp.models.api_models import JobCreateRequest
from careervp.models.job import Job

_jobs_repository: JobsRepository | None = None
_trial_service: TrialService | None = None


def _get_jobs_repository() -> JobsRepository:
    global _jobs_repository
    if _jobs_repository is None:
        _jobs_repository = JobsRepository()
    return _jobs_repository


def _reset_handler_caches() -> None:
    """Testing hook to reset module dependency caches."""
    global _jobs_repository, _trial_service
    _jobs_repository = None
    _trial_service = None


def _json_response(status: HTTPStatus, body: dict[str, Any]) -> Response[str]:
    return Response(
        status_code=status.value,
        content_type=content_types.APPLICATION_JSON,
        body=json.dumps(body, default=str),
    )


def _get_trial_service() -> TrialService | None:
    global _trial_service
    if _trial_service is not None:
        return _trial_service
    table_name = os.getenv('USERS_TABLE_NAME')
    if not table_name:
        return None
    _trial_service = TrialService(dal=DynamoDalHandler(table_name=table_name))
    return _trial_service


def _get_authenticated_user_id() -> str | None:
    # Try raw_event first (contains original event dict)
    raw_event = getattr(app.current_event, 'raw_event', None)
    if isinstance(raw_event, dict):
        user_id = extract_user_id(raw_event)
        if user_id:
            return user_id

    # Fallback: try request_context (Powertools object)
    request_context = app.current_event.request_context
    if isinstance(request_context, dict):
        return extract_user_id({'requestContext': request_context})

    # Convert Powertools object to dict
    rc_dict = dict(request_context)
    return extract_user_id({'requestContext': rc_dict})


def _parse_limit() -> int:
    query_params = app.current_event.query_string_parameters or {}
    raw_limit = query_params.get('limit')
    if raw_limit is None:
        return 20
    try:
        parsed_limit = int(raw_limit)
    except (ValueError, TypeError):
        return 20
    return max(1, min(parsed_limit, 100))


def _record_to_job(record: dict[str, Any]) -> Job:
    created_at = _coerce_datetime(record.get('created_at'))
    requirements_value = record.get('requirements')
    requirements = [str(item) for item in requirements_value if str(item).strip()] if isinstance(requirements_value, list) else []
    return Job(
        job_id=str(record.get('job_id', '')),
        user_id=str(record.get('user_id', '')),
        title=str(record.get('title', '')),
        company=str(record.get('company_name') or record.get('company') or ''),
        description=str(record.get('description', '')),
        status=str(record.get('status', 'active')),
        created_at=created_at,
        url=record.get('url') if isinstance(record.get('url'), str) else None,
        requirements=requirements,
    )


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.now(timezone.utc)
    return datetime.now(timezone.utc)


@app.post('/jobs')
@tracer.capture_method(capture_response=False)
def create_job() -> Response[str]:
    """Create a job posting for the authenticated user."""
    user_id = _get_authenticated_user_id()
    if not user_id:
        return _json_response(HTTPStatus.UNAUTHORIZED, {'error': 'Authentication required'})

    trial_service = _get_trial_service()
    if trial_service is not None:
        try:
            trial_service.check_trial_status(user_id)
        except TrialExpiredException:
            return _json_response(HTTPStatus.FORBIDDEN, {'error': 'trial_expired'})
        except TrialExhaustedException:
            return _json_response(HTTPStatus.FORBIDDEN, {'error': 'trial_exhausted'})

    try:
        raw_body = app.current_event.json_body
        if isinstance(raw_body, dict) and 'company_name' not in raw_body and 'company' in raw_body:
            raw_body = {**raw_body, 'company_name': raw_body.get('company')}
        request = JobCreateRequest.model_validate(raw_body)
    except (ValidationError, ValueError, TypeError) as exc:
        logger.warning('Invalid create job payload', error=str(exc))
        return _json_response(HTTPStatus.BAD_REQUEST, {'error': 'Invalid request payload'})

    create_result = _get_jobs_repository().create_job(
        {
            'user_id': user_id,
            'title': request.title.strip(),
            'company_name': request.company_name.strip(),
            'description': request.description.strip(),
            'url': str(request.url) if request.url else None,
            'requirements': request.requirements,
            'status': 'active',
        }
    )
    if not create_result.success or create_result.data is None:
        return _json_response(HTTPStatus.INTERNAL_SERVER_ERROR, {'error': create_result.error or 'Failed to create job'})

    job = _record_to_job(create_result.data)
    return _json_response(HTTPStatus.CREATED, job.to_api_dict())


@app.get('/jobs')
@tracer.capture_method(capture_response=False)
def list_jobs() -> Response[str]:
    """List jobs owned by the authenticated user."""
    user_id = _get_authenticated_user_id()
    if not user_id:
        return _json_response(HTTPStatus.UNAUTHORIZED, {'error': 'Authentication required'})

    limit = _parse_limit()
    job_records = _get_jobs_repository().get_jobs_by_user(user_id=user_id, limit=limit)
    jobs = [_record_to_job(record).to_api_dict() for record in job_records]
    return _json_response(HTTPStatus.OK, {'jobs': jobs})


@app.get('/jobs/<jobId>')
@app.get('/jobs/<job_id>')
@tracer.capture_method(capture_response=False)
def get_job(jobId: str | None = None, job_id: str | None = None) -> Response[str]:
    """Fetch one job by id, enforcing owner access."""
    resolved_job_id = (jobId or job_id or '').strip()
    if not resolved_job_id:
        return _json_response(HTTPStatus.BAD_REQUEST, {'error': 'Job id is required'})

    user_id = _get_authenticated_user_id()
    if not user_id:
        return _json_response(HTTPStatus.UNAUTHORIZED, {'error': 'Authentication required'})

    job_record = _get_jobs_repository().get_job(resolved_job_id)
    if job_record is None:
        return _json_response(HTTPStatus.NOT_FOUND, {'error': 'Job not found'})
    if str(job_record.get('user_id', '')) != user_id:
        return _json_response(HTTPStatus.FORBIDDEN, {'error': 'User can only access own jobs'})
    if 'title' not in job_record:
        return _json_response(HTTPStatus.NOT_FOUND, {'error': 'Job not found'})

    job = _record_to_job(job_record)
    return _json_response(HTTPStatus.OK, job.to_api_dict())


@logger.inject_lambda_context(correlation_id_path=API_GATEWAY_REST)
@tracer.capture_lambda_handler(capture_response=False)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Lambda entry point for jobs API routes."""
    return app.resolve(event, context)
