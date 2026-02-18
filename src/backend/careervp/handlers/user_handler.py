"""
User profile management handler.

Implements OpenAPI endpoints:
- GET /users/me
- PUT /users/me
- GET /users/me/cvs
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
from boto3.dynamodb.conditions import Key
from pydantic import ValidationError

from careervp.dal.user_repository import UserRepository
from careervp.handlers.utils.observability import logger, tracer
from careervp.handlers.utils.rest_api_resolver import app
from careervp.logic.auth_service import AuthService, ConfigurationError, InvalidTokenError
from careervp.models.api_models import UpdateUserRequest

_auth_service: AuthService | None = None
_user_repository: UserRepository | None = None


def _get_auth_service() -> AuthService:
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService.from_env()
    return _auth_service


def _get_user_repository() -> UserRepository:
    global _user_repository
    if _user_repository is None:
        _user_repository = UserRepository()
    return _user_repository


def _reset_handler_caches() -> None:
    """Testing hook to reset module-level dependency caches."""
    global _auth_service, _user_repository
    _auth_service = None
    _user_repository = None


def _json_response(status: HTTPStatus, body: dict[str, Any]) -> Response[str]:
    return Response(
        status_code=status.value,
        content_type=content_types.APPLICATION_JSON,
        body=json.dumps(body, default=str),
    )


def _extract_claim_user_id(claims: Any) -> str | None:
    if not isinstance(claims, dict):
        return None
    for key in ('sub', 'user_id', 'cognito:username'):
        value = claims.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_user_id_from_authorizer() -> str | None:
    request_context = app.current_event.request_context
    if not isinstance(request_context, dict):
        return None

    authorizer = request_context.get('authorizer')
    if not isinstance(authorizer, dict):
        return None

    claims = authorizer.get('claims')
    claim_user_id = _extract_claim_user_id(claims)
    if claim_user_id:
        return claim_user_id

    jwt_context = authorizer.get('jwt')
    if isinstance(jwt_context, dict):
        jwt_claims = jwt_context.get('claims')
        jwt_user_id = _extract_claim_user_id(jwt_claims)
        if jwt_user_id:
            return jwt_user_id

    for key in ('user_id', 'principalId', 'principal_id'):
        value = authorizer.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_bearer_token() -> str | None:
    headers = app.current_event.headers or {}
    auth_header = headers.get('Authorization') or headers.get('authorization')
    if not isinstance(auth_header, str):
        return None
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header[7:].strip()
    return token if token else None


def _get_authenticated_user_id() -> str | None:
    authorizer_user_id = _extract_user_id_from_authorizer()
    if authorizer_user_id:
        return authorizer_user_id

    token = _extract_bearer_token()
    if not token:
        return None

    try:
        payload = _get_auth_service().validate_token(token, expected_token_type='access')
    except (InvalidTokenError, ConfigurationError):
        return None

    user_id = payload.get('user_id') or payload.get('sub')
    if isinstance(user_id, str) and user_id.strip():
        return user_id.strip()
    return None


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
    table_name = os.environ.get('CVS_TABLE_NAME')
    if not table_name:
        return [], None

    table = boto3.resource('dynamodb').Table(table_name)
    query_args: dict[str, Any] = {
        'KeyConditionExpression': Key('userId').eq(user_id),
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

    user = _get_user_repository().get_user(user_id)
    if user is None:
        return _json_response(HTTPStatus.NOT_FOUND, {'error': 'User profile not found'})
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

    payload_user_id = raw_payload.get('user_id') if isinstance(raw_payload, dict) else None
    if isinstance(payload_user_id, str) and payload_user_id and payload_user_id != user_id:
        return _json_response(HTTPStatus.FORBIDDEN, {'error': 'User can only update own profile'})

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

    user = _get_user_repository().update_user(user_id, update_data)
    if user is None:
        return _json_response(HTTPStatus.NOT_FOUND, {'error': 'User profile not found'})
    return _json_response(HTTPStatus.OK, user.to_api_dict())


@app.get('/users/me/cvs')
@tracer.capture_method(capture_response=False)
def list_user_cvs() -> Response[str]:
    """List current user's CV records."""
    user_id = _get_authenticated_user_id()
    if not user_id:
        return _json_response(HTTPStatus.UNAUTHORIZED, {'error': 'Authentication required'})

    limit = _parse_limit()
    cursor = _parse_cursor()
    cvs, next_cursor = _list_user_cvs(user_id=user_id, limit=limit, cursor=cursor)
    body: dict[str, Any] = {'cvs': cvs}
    if next_cursor:
        body['cursor'] = next_cursor
    return _json_response(HTTPStatus.OK, body)


@logger.inject_lambda_context(correlation_id_path=API_GATEWAY_REST)
@tracer.capture_lambda_handler(capture_response=False)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Lambda entry point for user management API routes."""
    return app.resolve(event, context)
