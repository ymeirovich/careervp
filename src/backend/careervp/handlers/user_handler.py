"""
User profile management handler.

Implements OpenAPI endpoints:
- GET /users/me
- PUT /users/me
- GET /users/me/cv
- GET /users/me/cv/<cvId>
- DELETE /users/me/cv/<cvId>
- GET /users/me/usage
"""

import base64
import json
import os
from http import HTTPStatus
from typing import Any

import boto3
from aws_lambda_powertools.event_handler import Response, content_types
from aws_lambda_powertools.logging.correlation_paths import API_GATEWAY_REST
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from careervp.dal import table_registry
from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.dal.user_repository import UserRepository
from careervp.handlers.auth_utils import extract_user_id
from careervp.handlers.cors_utils import get_cors_headers, set_request_origin
from careervp.handlers.utils.observability import logger, tracer
from careervp.handlers.utils.rest_api_resolver import app
from careervp.logic.trial_service import TrialService
from careervp.models.api_models import UpdateUserRequest

_user_repository: UserRepository | None = None
_trial_service: TrialService | None = None


def _get_user_repository() -> UserRepository:
    global _user_repository
    if _user_repository is None:
        _user_repository = UserRepository()
    return _user_repository


def _reset_handler_caches() -> None:
    """Testing hook to reset module-level dependency caches."""
    global _user_repository, _trial_service
    _user_repository = None
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
    table_name = os.getenv('USERS_TABLE_NAME') or os.getenv('DYNAMODB_TABLE_NAME') or os.getenv('TABLE_NAME')
    if not table_name:
        return None
    _trial_service = TrialService(dal=DynamoDalHandler(table_name=table_name))
    return _trial_service


def _extract_user_id_from_authorizer() -> str | None:
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


def _get_authenticated_user_id() -> str | None:
    return _extract_user_id_from_authorizer()


def _parse_limit() -> int:
    query_params = app.current_event.query_string_parameters or {}
    raw_limit = query_params.get('limit')
    if raw_limit is None:
        return 20
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        return 20
    return max(1, min(limit, 100))


def _parse_cursor() -> dict[str, Any] | None:
    query_params = app.current_event.query_string_parameters or {}
    raw_cursor = query_params.get('cursor')
    if not raw_cursor:
        return None

    try:
        decoded = base64.urlsafe_b64decode(raw_cursor.encode('utf-8')).decode('utf-8')
        parsed = json.loads(decoded)
    except (ValueError, TypeError, json.JSONDecodeError):
        return None

    return parsed if isinstance(parsed, dict) else None


def _encode_cursor(last_evaluated_key: dict[str, Any] | None) -> str | None:
    if not isinstance(last_evaluated_key, dict):
        return None
    encoded = base64.urlsafe_b64encode(json.dumps(last_evaluated_key, default=str).encode('utf-8')).decode('utf-8')
    return encoded


def _list_user_cvs(user_id: str, limit: int, cursor: dict[str, Any] | None) -> tuple[list[dict[str, Any]], str | None]:
    # Use the same table as cv_upload_handler (TABLE_NAME from env)
    table_name = os.environ.get('TABLE_NAME')
    if not table_name:
        logger.warning('TABLE_NAME not configured for CV list')
        return [], None

    table = boto3.resource('dynamodb').Table(table_name)
    # Query using pk=user_id and sk begins_with 'CV#' (same schema as DynamoDalHandler.save_cv)
    query_args: dict[str, Any] = {
        'KeyConditionExpression': table_registry.legacy_key_condition(user_id, table_registry.CV_SORT_KEY_PREFIX),
        'Limit': limit,
    }
    if cursor:
        query_args['ExclusiveStartKey'] = cursor

    try:
        response = table.query(**query_args)
    except Exception as exc:  # pragma: no cover - defensive fallback.
        logger.exception('Failed to list user CVs', error=str(exc), user_id=user_id)
        return [], None

    items = response.get('Items', [])
    cvs = [item for item in items if isinstance(item, dict)]
    next_cursor = _encode_cursor(response.get('LastEvaluatedKey'))
    return cvs, next_cursor


@app.get('/users/me')
@tracer.capture_method(capture_response=False)
def get_current_user() -> Response[str]:
    """Get current authenticated user profile."""
    user_id = _get_authenticated_user_id()
    if not user_id:
        return _json_response(HTTPStatus.UNAUTHORIZED, {'error': 'Authentication required'})

    user = _get_user_repository().ensure_user(user_id)
    if user is None:
        return _json_response(HTTPStatus.INTERNAL_SERVER_ERROR, {'error': 'Failed to initialize user profile'})
    return _json_response(HTTPStatus.OK, user.to_api_dict())


@app.put('/users/me')
@tracer.capture_method(capture_response=False)
def update_current_user() -> Response[str]:
    """Update authenticated user profile."""
    user_id = _get_authenticated_user_id()
    if not user_id:
        return _json_response(HTTPStatus.UNAUTHORIZED, {'error': 'Authentication required'})

    try:
        raw_payload = app.current_event.json_body
        if not isinstance(raw_payload, dict):
            raise TypeError('Request body must be a JSON object')
    except (ValidationError, ValueError, TypeError) as exc:
        logger.warning('Invalid update user payload', error=str(exc))
        return _json_response(HTTPStatus.BAD_REQUEST, {'error': 'Invalid request payload'})

    try:
        payload = UpdateUserRequest.model_validate(
            {
                'name': raw_payload.get('name'),
                'timezone': raw_payload.get('timezone'),
            }
        )
    except (ValidationError, ValueError, TypeError) as exc:
        logger.warning('Invalid update user payload', error=str(exc))
        return _json_response(HTTPStatus.BAD_REQUEST, {'error': 'Invalid request payload'})

    update_data: dict[str, Any] = {}
    if isinstance(payload.name, str) and payload.name.strip():
        update_data['name'] = payload.name.strip()
    if isinstance(payload.timezone, str) and payload.timezone.strip():
        update_data['timezone'] = payload.timezone.strip()
    payload_preferences = raw_payload.get('preferences') if isinstance(raw_payload, dict) else None
    if isinstance(payload_preferences, dict):
        update_data['preferences'] = payload_preferences

    user = _get_user_repository().ensure_user(user_id, update_data)
    if user is None:
        return _json_response(HTTPStatus.INTERNAL_SERVER_ERROR, {'error': 'Failed to update user profile'})
    return _json_response(HTTPStatus.OK, user.to_api_dict())


@app.get('/users/me/cv')
@app.get('/users/me/cvs')  # Backward-compatible alias.
@tracer.capture_method(capture_response=False)
def list_user_cvs() -> Response[str]:
    """List current user's CV records."""
    user_id = _get_authenticated_user_id()
    if not user_id:
        return _json_response(HTTPStatus.UNAUTHORIZED, {'error': 'Authentication required'})

    limit = _parse_limit()
    cursor = _parse_cursor()
    cvs, next_cursor = _list_user_cvs(user_id=user_id, limit=limit, cursor=cursor)
    body: dict[str, Any] = {
        'cvs': cvs,
        'cursor': next_cursor or '',
    }
    return _json_response(HTTPStatus.OK, body)


@app.get('/users/me/cv/<cv_id>')
@tracer.capture_method(capture_response=False)
def get_user_cv(cv_id: str) -> Response[str]:
    """Get a single CV by its ID."""
    user_id = _get_authenticated_user_id()
    if not user_id:
        return _json_response(HTTPStatus.UNAUTHORIZED, {'error': 'Authentication required'})

    table_name = os.environ.get('TABLE_NAME')
    if not table_name:
        return _json_response(HTTPStatus.SERVICE_UNAVAILABLE, {'error': 'CV storage not configured'})

    dal = DynamoDalHandler(table_name=table_name)
    cv = dal.get_cv_by_id(user_id, cv_id)
    if cv is None:
        return _json_response(HTTPStatus.NOT_FOUND, {'error': 'CV not found'})

    return _json_response(HTTPStatus.OK, cv.model_dump(mode='json', exclude_none=True))


@app.delete('/users/me/cv/<cv_id>')
@tracer.capture_method(capture_response=False)
def delete_user_cv(cv_id: str) -> Response[str]:
    """Delete a CV by its ID, including its S3 source file."""
    user_id = _get_authenticated_user_id()
    if not user_id:
        return _json_response(HTTPStatus.UNAUTHORIZED, {'error': 'Authentication required'})

    table_name = os.environ.get('TABLE_NAME')
    if not table_name:
        return _json_response(HTTPStatus.SERVICE_UNAVAILABLE, {'error': 'CV storage not configured'})

    dal = DynamoDalHandler(table_name=table_name)
    deleted, source_file_key = dal.delete_cv(user_id, cv_id)

    if not deleted:
        return _json_response(HTTPStatus.NOT_FOUND, {'error': 'CV not found'})

    if source_file_key:
        bucket_name = os.environ.get('CV_BUCKET_NAME', '')
        if bucket_name:
            try:
                boto3.client('s3').delete_object(Bucket=bucket_name, Key=source_file_key)
                logger.info('Deleted CV source file from S3', s3_key=source_file_key)
            except Exception as exc:
                logger.warning('Failed to delete CV source file from S3', s3_key=source_file_key, error=str(exc))

    return Response(
        status_code=HTTPStatus.NO_CONTENT.value,
        content_type=content_types.APPLICATION_JSON,
        body='',
    )


@app.get('/users/me/usage')
@tracer.capture_method(capture_response=False)
def get_usage_snapshot() -> Response[str]:
    """Return user usage snapshot for the authenticated user."""
    user_id = _get_authenticated_user_id()
    if not user_id:
        return _json_response(HTTPStatus.UNAUTHORIZED, {'error': 'Authentication required'})

    trial_service = _get_trial_service()
    if trial_service is None:
        return _json_response(
            HTTPStatus.OK,
            {
                'trial': {
                    'active': True,
                    'days_elapsed': 0,
                    'days_remaining': 14,
                    'ends_at': None,
                },
                'applications': {
                    'used': 0,
                    'remaining': 3,
                },
            },
        )

    usage = trial_service.get_usage(user_id)
    return _json_response(
        HTTPStatus.OK,
        {
            'trial': {
                'active': bool(usage.get('trial_active', False)),
                'days_elapsed': int(usage.get('days_elapsed', 0)),
                'days_remaining': int(usage.get('days_remaining', 0)),
                'ends_at': usage.get('trial_ends_at'),
            },
            'applications': {
                'used': int(usage.get('applications_used', 0)),
                'remaining': int(usage.get('credits_remaining', 0)),
            },
        },
    )


@app.post('/users/me/trial/reset')
@tracer.capture_method(capture_response=False)
def reset_user_trial() -> Response[str]:
    """Reset trial usage for the authenticated user (test/admin use)."""
    user_id = _get_authenticated_user_id()
    if not user_id:
        return _json_response(HTTPStatus.UNAUTHORIZED, {'error': 'Authentication required'})

    trial_service = _get_trial_service()
    if trial_service is None:
        return _json_response(HTTPStatus.SERVICE_UNAVAILABLE, {'error': 'Trial service unavailable'})

    try:
        trial_service.reset_trial(user_id)
    except Exception as exc:
        logger.exception('Failed to reset trial', user_id=user_id, error=str(exc))
        return _json_response(HTTPStatus.INTERNAL_SERVER_ERROR, {'error': 'Failed to reset trial'})

    return _json_response(HTTPStatus.OK, {'status': 'reset', 'message': 'Trial reset successfully'})


@logger.inject_lambda_context(correlation_id_path=API_GATEWAY_REST)
@tracer.capture_lambda_handler(capture_response=False)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Lambda entry point for user management API routes."""
    set_request_origin(event)
    response: dict[str, Any] = app.resolve(event, context)
    cors = get_cors_headers(None)
    if cors:
        headers: dict[str, str] = response.get('headers') or {}
        headers.update(cors)
        response['headers'] = headers
    return response
