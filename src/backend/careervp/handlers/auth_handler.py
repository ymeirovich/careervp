"""
Authentication API handler.

Implements OpenAPI endpoints:
- POST /auth/register
- POST /auth/login
- POST /auth/refresh
"""

import json
from http import HTTPStatus
from typing import Annotated, Any

from aws_lambda_powertools.event_handler import Response, content_types
from aws_lambda_powertools.logging.correlation_paths import API_GATEWAY_REST
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import BaseModel, EmailStr, Field, ValidationError

from careervp.handlers.utils.observability import logger, tracer
from careervp.handlers.utils.rest_api_resolver import app
from careervp.logic.auth_service import (
    AuthService,
    ConfigurationError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
)

_auth_service: AuthService | None = None


class RegisterRequest(BaseModel):
    """Register request payload per OpenAPI schema."""

    email: EmailStr
    password: Annotated[str, Field(min_length=8)]
    name: Annotated[str, Field(min_length=1)]


class LoginRequest(BaseModel):
    """Login request payload per OpenAPI schema."""

    email: EmailStr
    password: Annotated[str, Field(min_length=1)]


class RefreshRequest(BaseModel):
    """Optional fallback request body for refresh endpoint."""

    refresh_token: Annotated[str, Field(min_length=1)]


def _get_auth_service() -> AuthService:
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService.from_env()
    return _auth_service


def _reset_auth_service_cache() -> None:
    """Testing hook to reset cached AuthService."""
    global _auth_service
    _auth_service = None


def _json_response(status: HTTPStatus, body: dict[str, Any]) -> Response[str]:
    return Response(
        status_code=status.value,
        content_type=content_types.APPLICATION_JSON,
        body=json.dumps(body),
    )


def _extract_refresh_token() -> str | None:
    headers = app.current_event.headers or {}
    auth_header = headers.get('Authorization') or headers.get('authorization')
    if isinstance(auth_header, str) and auth_header.startswith('Bearer '):
        return auth_header[7:].strip()

    # Body fallback keeps compatibility for clients that submit refresh_token in JSON.
    try:
        body = app.current_event.json_body
    except ValueError:
        return None
    if isinstance(body, dict):
        try:
            request = RefreshRequest.model_validate(body)
            return request.refresh_token
        except ValidationError:
            return None
    return None


@app.post('/auth/register')
@tracer.capture_method(capture_response=False)
def register_user() -> Response[str]:
    """Create a new user and return access/refresh tokens."""
    try:
        request = RegisterRequest.model_validate(app.current_event.json_body)
    except (ValidationError, TypeError, ValueError) as exc:
        logger.warning('Invalid register request', error=str(exc))
        return _json_response(
            HTTPStatus.BAD_REQUEST,
            {'error': 'Invalid request payload'},
        )

    try:
        tokens = _get_auth_service().register_user(
            email=request.email,
            password=request.password,
            name=request.name,
        )
    except UserAlreadyExistsError:
        return _json_response(HTTPStatus.BAD_REQUEST, {'error': 'User already exists'})
    except ConfigurationError as exc:
        logger.exception('Auth configuration error', error=str(exc))
        return _json_response(HTTPStatus.INTERNAL_SERVER_ERROR, {'error': 'Auth service misconfigured'})
    except Exception as exc:  # pragma: no cover - defensive safeguard.
        logger.exception('Unexpected register failure', error=str(exc))
        return _json_response(HTTPStatus.INTERNAL_SERVER_ERROR, {'error': 'Internal server error'})

    return _json_response(HTTPStatus.CREATED, tokens.to_response())


@app.post('/auth/login')
@tracer.capture_method(capture_response=False)
def login_user() -> Response[str]:
    """Authenticate an existing user and return access/refresh tokens."""
    try:
        request = LoginRequest.model_validate(app.current_event.json_body)
    except (ValidationError, TypeError, ValueError) as exc:
        logger.warning('Invalid login request', error=str(exc))
        return _json_response(
            HTTPStatus.BAD_REQUEST,
            {'error': 'Invalid request payload'},
        )

    try:
        tokens = _get_auth_service().login_user(
            email=request.email,
            password=request.password,
        )
    except InvalidCredentialsError:
        return _json_response(HTTPStatus.UNAUTHORIZED, {'error': 'Invalid credentials'})
    except ConfigurationError as exc:
        logger.exception('Auth configuration error', error=str(exc))
        return _json_response(HTTPStatus.INTERNAL_SERVER_ERROR, {'error': 'Auth service misconfigured'})
    except Exception as exc:  # pragma: no cover - defensive safeguard.
        logger.exception('Unexpected login failure', error=str(exc))
        return _json_response(HTTPStatus.INTERNAL_SERVER_ERROR, {'error': 'Internal server error'})

    return _json_response(HTTPStatus.OK, tokens.to_response())


@app.post('/auth/refresh')
@tracer.capture_method(capture_response=False)
def refresh_token() -> Response[str]:
    """Refresh access token using a valid refresh token."""
    refresh_token_value = _extract_refresh_token()
    if not refresh_token_value:
        return _json_response(HTTPStatus.UNAUTHORIZED, {'error': 'Missing refresh token'})

    try:
        tokens = _get_auth_service().refresh_token(refresh_token_value)
    except InvalidTokenError:
        return _json_response(HTTPStatus.UNAUTHORIZED, {'error': 'Invalid refresh token'})
    except ConfigurationError as exc:
        logger.exception('Auth configuration error', error=str(exc))
        return _json_response(HTTPStatus.INTERNAL_SERVER_ERROR, {'error': 'Auth service misconfigured'})
    except Exception as exc:  # pragma: no cover - defensive safeguard.
        logger.exception('Unexpected refresh failure', error=str(exc))
        return _json_response(HTTPStatus.INTERNAL_SERVER_ERROR, {'error': 'Internal server error'})

    return _json_response(HTTPStatus.OK, tokens.to_response())


@logger.inject_lambda_context(correlation_id_path=API_GATEWAY_REST)
@tracer.capture_lambda_handler(capture_response=False)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Lambda entry point for auth API routes."""
    return app.resolve(event, context)
