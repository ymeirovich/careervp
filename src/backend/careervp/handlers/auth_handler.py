"""
JWT-based API Authorization Lambda Handler.
Per docs/specs/security_spec.yaml (SEC-001).

This Lambda Authorizer validates JWT tokens and returns IAM policies for API Gateway.
"""

from __future__ import annotations

import os
from typing import Annotated, Any

import boto3
import jwt  # type: ignore[import-not-found]
from aws_lambda_powertools.logging.correlation_paths import API_GATEWAY_REST
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import BaseModel, Field

from careervp.handlers.models.env_vars import Observability
from careervp.handlers.utils.observability import logger, tracer


class AuthEnvVars(Observability):
    """Environment variables for auth handler."""

    TOKEN_BLACKLIST_TABLE_NAME: Annotated[str, Field(min_length=1)]
    JWT_SECRET: Annotated[str, Field(min_length=1)]
    JWT_ALGORITHM: str = 'HS256'


class User(BaseModel):
    """User model extracted from JWT token."""

    user_email: str
    entity_type: str = 'USER'


def _get_dynamodb_client() -> Any:
    """Get DynamoDB client (separated for testability)."""
    return boto3.client('dynamodb')


@tracer.capture_method
def _is_token_blacklisted(token: str, table_name: str) -> bool:
    """
    Check if a token is in the DynamoDB blacklist.

    Args:
        token: JWT token string
        table_name: DynamoDB table name for blacklist

    Returns:
        True if token is blacklisted, False otherwise
    """
    try:
        client = _get_dynamodb_client()
        response = client.get_item(
            TableName=table_name,
            Key={'token': {'S': token}},
        )
        is_blacklisted = 'Item' in response
        if is_blacklisted:
            logger.info('Token found in blacklist')
        return is_blacklisted
    except Exception as exc:
        logger.error('Failed to check token blacklist', error=str(exc))
        # Fail closed: treat as blacklisted on error
        return True


@tracer.capture_method
def validate_token(token: str) -> bool:
    """
    Validate a JWT token.

    Checks:
    - JWT signature and expiration
    - DynamoDB blacklist

    Args:
        token: JWT token string

    Returns:
        True if token is valid, False otherwise
    """
    try:
        jwt_secret = os.environ['JWT_SECRET']
        jwt_algorithm = os.environ.get('JWT_ALGORITHM', 'HS256')
        table_name = os.environ['TOKEN_BLACKLIST_TABLE_NAME']

        # Decode and verify JWT
        jwt.decode(token, jwt_secret, algorithms=[jwt_algorithm])

        # Check blacklist
        if _is_token_blacklisted(token, table_name):
            logger.warning('Token is blacklisted')
            return False

        logger.info('Token validated successfully')
        return True

    except jwt.ExpiredSignatureError:
        logger.warning('Token has expired')
        return False
    except jwt.InvalidTokenError as exc:
        logger.warning('Invalid token', error=str(exc))
        return False
    except Exception as exc:
        logger.error('Unexpected error during token validation', error=str(exc))
        return False


@tracer.capture_method
def get_user_from_token(token: str) -> User:
    """
    Extract user information from JWT token.

    Args:
        token: JWT token string

    Returns:
        User model with user_email and entity_type

    Raises:
        ValueError: If token is invalid or missing required fields
    """
    try:
        jwt_secret = os.environ['JWT_SECRET']
        jwt_algorithm = os.environ.get('JWT_ALGORITHM', 'HS256')

        payload = jwt.decode(token, jwt_secret, algorithms=[jwt_algorithm])

        user_email = payload.get('user_email')
        if not user_email:
            raise ValueError('Token missing user_email field')

        entity_type = payload.get('entity_type', 'USER')

        logger.info('Successfully extracted user from token', user_email=user_email)
        return User(user_email=user_email, entity_type=entity_type)

    except jwt.InvalidTokenError as exc:
        logger.error('Failed to decode token', error=str(exc))
        raise ValueError(f'Invalid token: {exc}') from exc
    except ValueError:
        raise
    except Exception as exc:
        logger.error('Unexpected error extracting user from token', error=str(exc))
        raise ValueError(f'Failed to extract user: {exc}') from exc


def _generate_policy(principal_id: str, effect: str, resource: str, context: dict[str, str] | None = None) -> dict[str, Any]:
    """
    Generate an IAM policy for API Gateway.

    Args:
        principal_id: User identifier (user_email)
        effect: 'Allow' or 'Deny'
        resource: ARN of the API Gateway resource
        context: Optional context to attach to policy

    Returns:
        IAM policy document
    """
    policy: dict[str, Any] = {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': resource,
                }
            ],
        },
    }
    if context:
        policy['context'] = context
    return policy


@logger.inject_lambda_context(correlation_id_path=API_GATEWAY_REST)
@tracer.capture_lambda_handler(capture_response=False)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """
    Lambda Authorizer handler for API Gateway (TOKEN type).

    Validates JWT token from authorizationToken and returns IAM policy.

    Args:
        event: API Gateway TOKEN authorizer event
        context: Lambda context

    Returns:
        IAM policy document (Allow or Deny)
    """
    method_arn = event.get('methodArn', '*')
    token = event.get('authorizationToken', '')

    if not token:
        logger.warning('Missing authorizationToken')
        return _generate_policy(principal_id='unknown', effect='Deny', resource=method_arn)

    # Remove 'Bearer ' prefix if present
    if token.startswith('Bearer '):
        token = token[7:]

    # Validate token
    if not validate_token(token):
        logger.warning('Token validation failed')
        return _generate_policy(principal_id='unknown', effect='Deny', resource=method_arn)

    # Extract user information
    try:
        user = get_user_from_token(token)
    except ValueError:
        logger.warning('Failed to extract user from token')
        return _generate_policy(principal_id='unknown', effect='Deny', resource=method_arn)

    # Generate Allow policy
    policy = _generate_policy(
        principal_id=user.user_email,
        effect='Allow',
        resource=method_arn,
        context={'user_email': user.user_email, 'entity_type': user.entity_type},
    )

    logger.info('Authorization successful', user_email=user.user_email)
    return policy
