"""
Authentication service for user registration, login, and token refresh.

Implements OpenAPI auth contract with RS256 JWTs, 1-hour access tokens, and
7-day refresh tokens.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, cast

import boto3
import jwt
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

try:
    import bcrypt as _bcrypt  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - exercised only when bcrypt is absent.
    _bcrypt = None

ACCESS_TOKEN_TTL_SECONDS = 60 * 60
REFRESH_TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60
PBKDF2_ITERATIONS = 200_000
PBKDF2_PREFIX = 'pbkdf2_sha256'
USERS_PROFILE_SK = 'PROFILE'
USERS_EMAIL_INDEX = 'email-index'


class AuthError(Exception):
    """Base auth service error."""


class UserAlreadyExistsError(AuthError):
    """Raised when trying to register an already-existing user email."""


class InvalidCredentialsError(AuthError):
    """Raised when email/password validation fails."""


class InvalidTokenError(AuthError):
    """Raised when token validation fails."""


class ConfigurationError(AuthError):
    """Raised when required runtime configuration is missing."""


@dataclass(frozen=True, slots=True)
class AuthTokens:
    """Serializable auth token payload returned by handlers."""

    access_token: str
    refresh_token: str
    expires_in: int = ACCESS_TOKEN_TTL_SECONDS
    token_type: str = 'Bearer'

    def to_response(self) -> dict[str, Any]:
        """Convert token bundle to API response shape."""
        return {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'expires_in': self.expires_in,
            'token_type': self.token_type,
        }


@lru_cache(maxsize=1)
def _generate_ephemeral_rsa_keys() -> tuple[str, str]:
    """
    Generate an in-memory key pair for non-production fallback.

    This keeps local development/tests functional when explicit key material
    isn't injected via environment variables.
    """

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode('utf-8')
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode('utf-8')
    )
    return private_pem, public_pem


class AuthService:
    """Auth service providing registration/login/refresh logic."""

    def __init__(
        self,
        users_table_name: str | None,
        jwt_private_key: str,
        jwt_public_key: str,
        *,
        jwt_algorithm: str = 'RS256',
        access_ttl_seconds: int = ACCESS_TOKEN_TTL_SECONDS,
        refresh_ttl_seconds: int = REFRESH_TOKEN_TTL_SECONDS,
        dynamodb_resource: Any | None = None,
    ) -> None:
        self._users_table_name = users_table_name
        self._jwt_private_key = jwt_private_key
        self._jwt_public_key = jwt_public_key
        self._jwt_algorithm = jwt_algorithm
        self._access_ttl_seconds = access_ttl_seconds
        self._refresh_ttl_seconds = refresh_ttl_seconds
        self._dynamodb_resource = dynamodb_resource

    @classmethod
    def from_env(cls, *, dynamodb_resource: Any | None = None) -> AuthService:
        """Create AuthService from Lambda environment variables."""

        users_table_name = os.environ.get('TABLE_NAME') or os.environ.get('USERS_TABLE_NAME')
        private_key = os.environ.get('JWT_PRIVATE_KEY')
        public_key = os.environ.get('JWT_PUBLIC_KEY')

        if not private_key or not public_key:
            if os.getenv('ENV') != 'local':
                raise ConfigurationError('JWT_PRIVATE_KEY and JWT_PUBLIC_KEY must be set in production')
            # Only generate ephemeral keys in local dev
            private_key, public_key = _generate_ephemeral_rsa_keys()

        return cls(
            users_table_name=users_table_name,
            jwt_private_key=private_key,
            jwt_public_key=public_key,
            jwt_algorithm='RS256',
            access_ttl_seconds=ACCESS_TOKEN_TTL_SECONDS,
            refresh_ttl_seconds=REFRESH_TOKEN_TTL_SECONDS,
            dynamodb_resource=dynamodb_resource,
        )

    def register_user(self, email: str, password: str, name: str) -> AuthTokens:
        """Register a new user profile and return auth tokens."""

        normalized_email = self._normalize_email(email)
        if self._get_user_by_email(normalized_email) is not None:
            raise UserAlreadyExistsError('User with this email already exists')

        now = datetime.now(timezone.utc)
        user_id = str(uuid.uuid4())
        item = {
            'pk': self._build_user_pk(user_id),
            'sk': USERS_PROFILE_SK,
            'entity_type': 'USER',
            'user_id': user_id,
            'email': normalized_email,
            'name': name.strip(),
            'password_hash': self.hash_password(password),
            'created_at': now.isoformat(),
            'updated_at': now.isoformat(),
        }

        try:
            self._users_table().put_item(
                Item=item,
                ConditionExpression='attribute_not_exists(pk) AND attribute_not_exists(sk)',
            )
        except ClientError as exc:
            if exc.response.get('Error', {}).get('Code') == 'ConditionalCheckFailedException':
                raise UserAlreadyExistsError('User with this email already exists') from exc
            raise AuthError(f'Failed to register user: {exc}') from exc

        return self._mint_tokens(user_id=user_id, email=normalized_email)

    def login_user(self, email: str, password: str) -> AuthTokens:
        """Authenticate user credentials and return tokens."""

        normalized_email = self._normalize_email(email)
        user_item = self._get_user_by_email(normalized_email)
        if user_item is None:
            raise InvalidCredentialsError('Invalid email or password')

        password_hash = str(user_item.get('password_hash', ''))
        if not password_hash or not self.verify_password(password, password_hash):
            raise InvalidCredentialsError('Invalid email or password')

        user_id = self._extract_user_id(user_item)
        return self._mint_tokens(user_id=user_id, email=normalized_email)

    def refresh_token(self, refresh_token: str) -> AuthTokens:
        """Validate refresh token and issue a new token pair."""

        payload = self.validate_token(refresh_token, expected_token_type='refresh')
        user_id_value = payload.get('user_id')
        email_value = payload.get('email')
        if not isinstance(user_id_value, str) or not user_id_value:
            raise InvalidTokenError('Refresh token missing user_id')
        if not isinstance(email_value, str) or not email_value:
            raise InvalidTokenError('Refresh token missing email')
        return self._mint_tokens(user_id=user_id_value, email=email_value)

    def validate_token(
        self,
        token: str,
        *,
        expected_token_type: str | None = None,
    ) -> dict[str, Any]:
        """Decode and validate an RS256 JWT token."""

        try:
            payload = jwt.decode(
                token,
                self._jwt_public_key,
                algorithms=[self._jwt_algorithm],
                options={'require': ['exp', 'iat', 'user_id']},
            )
        except jwt.ExpiredSignatureError as exc:
            raise InvalidTokenError('Token has expired') from exc
        except jwt.InvalidTokenError as exc:
            raise InvalidTokenError('Invalid token') from exc

        if expected_token_type is not None and payload.get('token_type') != expected_token_type:
            raise InvalidTokenError('Invalid token type')

        return payload

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt when available, else PBKDF2 fallback."""

        if _bcrypt is not None:
            hashed = cast(bytes, _bcrypt.hashpw(password.encode('utf-8'), _bcrypt.gensalt()))
            return hashed.decode('utf-8')
        return self._hash_password_pbkdf2(password)

    def verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against bcrypt or fallback hash."""

        if stored_hash.startswith(PBKDF2_PREFIX):
            return self._verify_password_pbkdf2(password, stored_hash)

        if _bcrypt is None:
            return False

        try:
            return bool(_bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')))
        except ValueError:
            return False

    def _mint_tokens(self, *, user_id: str, email: str) -> AuthTokens:
        issued_at = datetime.now(timezone.utc)
        iat = int(issued_at.timestamp())
        access_exp = int((issued_at + timedelta(seconds=self._access_ttl_seconds)).timestamp())
        refresh_exp = int((issued_at + timedelta(seconds=self._refresh_ttl_seconds)).timestamp())

        access_payload = {
            'user_id': user_id,
            'email': email,
            'token_type': 'access',
            'iat': iat,
            'exp': access_exp,
        }
        refresh_payload = {
            'user_id': user_id,
            'email': email,
            'token_type': 'refresh',
            'iat': iat,
            'exp': refresh_exp,
        }

        access_token = jwt.encode(access_payload, self._jwt_private_key, algorithm=self._jwt_algorithm)
        refresh_token = jwt.encode(refresh_payload, self._jwt_private_key, algorithm=self._jwt_algorithm)
        return AuthTokens(access_token=access_token, refresh_token=refresh_token, expires_in=self._access_ttl_seconds)

    def _users_table(self) -> Any:
        if not self._users_table_name:
            raise ConfigurationError('TABLE_NAME or USERS_TABLE_NAME must be configured for auth endpoints')
        if self._dynamodb_resource is None:
            self._dynamodb_resource = boto3.resource('dynamodb')
        return self._dynamodb_resource.Table(self._users_table_name)

    def _get_user_by_email(self, email: str) -> dict[str, Any] | None:
        try:
            response = self._users_table().query(
                IndexName=USERS_EMAIL_INDEX,
                KeyConditionExpression=Key('email').eq(email),
                Limit=1,
            )
        except ClientError as exc:
            raise AuthError(f'Failed to query user by email: {exc}') from exc

        items = response.get('Items', [])
        if not items:
            return None
        item = items[0]
        if isinstance(item, dict):
            return item
        return None

    @staticmethod
    def _build_user_pk(user_id: str) -> str:
        return f'USER#{user_id}'

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def _extract_user_id(item: dict[str, Any]) -> str:
        user_id = item.get('user_id')
        if isinstance(user_id, str) and user_id:
            return user_id

        pk = item.get('pk')
        if isinstance(pk, str) and pk.startswith('USER#'):
            return pk.removeprefix('USER#')

        raise InvalidCredentialsError('Stored user record is missing user_id')

    @staticmethod
    def _hash_password_pbkdf2(password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            PBKDF2_ITERATIONS,
        )
        salt_b64 = base64.urlsafe_b64encode(salt).decode('utf-8')
        digest_b64 = base64.urlsafe_b64encode(digest).decode('utf-8')
        return f'{PBKDF2_PREFIX}${salt_b64}${digest_b64}'

    @staticmethod
    def _verify_password_pbkdf2(password: str, stored_hash: str) -> bool:
        parts = stored_hash.split('$')
        if len(parts) != 3 or parts[0] != PBKDF2_PREFIX:
            return False

        try:
            salt = base64.urlsafe_b64decode(parts[1].encode('utf-8'))
            expected_digest = base64.urlsafe_b64decode(parts[2].encode('utf-8'))
        except (ValueError, TypeError):
            return False

        candidate_digest = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            PBKDF2_ITERATIONS,
        )
        return hmac.compare_digest(candidate_digest, expected_digest)
