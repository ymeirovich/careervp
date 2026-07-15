"""Data access for the P-24 ``sub -> user_id`` identity-surrogate mapping.

The internal ``user_id`` is the durable tenant partition key; Cognito ``sub``
values are resolved to it at the edge and never used directly as the partition
key. The mapping lives in its OWN small ``sub``-keyed table — it is looked up
BEFORE the ``user_id`` is known, so it cannot live inside the ``USER#`` core
(spec P-24, Fix item 2).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

IDENTITY_MAP_TABLE_ENV = 'IDENTITY_MAP_TABLE_NAME'
SUB_ATTR = 'sub'
USER_ID_ATTR = 'user_id'

_USERS_EMAIL_INDEX = 'email-index'
_CONDITIONAL_CHECK_FAILED = 'ConditionalCheckFailedException'


class IdentityMapNotConfiguredError(RuntimeError):
    """Raised when a mutating mapping op is attempted with no table wired."""


@dataclass(frozen=True, slots=True)
class ExistingUser:
    """An internal user already owning an email (candidate link target)."""

    user_id: str
    created_at: str


class IdentityMapRepository:
    """CRUD for the ``sub -> user_id`` surrogate mapping (own table, sub-keyed)."""

    def __init__(self, table_name: str | None = None, dynamodb_resource: Any | None = None) -> None:
        self._table_name = table_name or os.environ.get(IDENTITY_MAP_TABLE_ENV) or ''
        self._dynamodb_resource = dynamodb_resource
        self._table = self._resolve_table() if self._table_name else None

    def _resolve_table(self) -> Any:
        if self._dynamodb_resource is None:
            self._dynamodb_resource = boto3.resource('dynamodb')
        return self._dynamodb_resource.Table(self._table_name)

    @property
    def configured(self) -> bool:
        """Whether a mapping table is wired (surrogate resolution is active)."""
        return self._table is not None

    def get_user_id(self, sub: str) -> str | None:
        """Return the internal ``user_id`` mapped to ``sub``, or ``None``."""
        if self._table is None:
            return None
        try:
            response = self._table.get_item(Key={SUB_ATTR: sub})
        except ClientError:
            return None
        item = response.get('Item')
        if isinstance(item, dict):
            user_id = item.get(USER_ID_ATTR)
            if isinstance(user_id, str) and user_id:
                return user_id
        return None

    def link(self, sub: str, user_id: str) -> str:
        """JIT-create the ``sub -> user_id`` mapping; return the durable value.

        Uses ``attribute_not_exists(sub)`` so exactly one writer wins a race; a
        losing concurrent writer re-reads and returns the winner's ``user_id``
        (never two internal ids for one human = a permanent split tenant).
        """
        if self._table is None:
            raise IdentityMapNotConfiguredError('IDENTITY_MAP_TABLE_NAME is not configured')
        try:
            self._table.put_item(
                Item={SUB_ATTR: sub, USER_ID_ATTR: user_id},
                ConditionExpression='attribute_not_exists(#sub)',
                ExpressionAttributeNames={'#sub': SUB_ATTR},
            )
            return user_id
        except ClientError as exc:
            if exc.response.get('Error', {}).get('Code') == _CONDITIONAL_CHECK_FAILED:
                existing = self.get_user_id(sub)
                if existing is not None:
                    return existing
            raise


class UsersDirectory:
    """Resolve internal user owners of an email via the users ``email-index``."""

    def __init__(self, table_name: str | None = None, dynamodb_resource: Any | None = None) -> None:
        self._table_name = table_name or os.environ.get('USERS_TABLE_NAME') or os.environ.get('TABLE_NAME') or ''
        self._dynamodb_resource = dynamodb_resource
        self._table = self._resolve_table() if self._table_name else None

    def _resolve_table(self) -> Any:
        if self._dynamodb_resource is None:
            self._dynamodb_resource = boto3.resource('dynamodb')
        return self._dynamodb_resource.Table(self._table_name)

    def find_owners(self, email: str) -> list[ExistingUser]:
        """Return every internal user currently owning ``email`` (may be >1)."""
        if self._table is None or not email:
            return []
        try:
            response = self._table.query(
                IndexName=_USERS_EMAIL_INDEX,
                KeyConditionExpression=Key('email').eq(email),
            )
        except ClientError:
            return []

        owners: list[ExistingUser] = []
        for item in response.get('Items', []):
            if not isinstance(item, dict):
                continue
            user_id = item.get(USER_ID_ATTR)
            if not (isinstance(user_id, str) and user_id):
                pk = item.get('pk')
                user_id = pk.removeprefix('USER#') if isinstance(pk, str) and pk.startswith('USER#') else ''
            if not user_id:
                continue
            created_at = item.get('created_at')
            owners.append(ExistingUser(user_id=user_id, created_at=str(created_at) if created_at else ''))
        return owners
