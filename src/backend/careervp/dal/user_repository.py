"""
Repository for user profile CRUD operations.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import boto3  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from careervp.models.user import User

USER_PROFILE_SK = 'PROFILE'


class UserRepository:
    """Data access for user profile rows in users table."""

    def __init__(self, table_name: str | None = None, dynamodb_resource: Any | None = None) -> None:
        self._table_name = table_name or os.environ.get('TABLE_NAME') or ''
        self._dynamodb_resource = dynamodb_resource or boto3.resource('dynamodb')
        self._table = self._dynamodb_resource.Table(self._table_name) if self._table_name else None

    def get_user(self, user_id: str) -> User | None:
        """Get user profile by user_id (stored as users-table PK)."""
        if self._table is None:
            return None

        for pk in self._candidate_partition_keys(user_id):
            try:
                response = self._table.get_item(Key={'pk': pk, 'sk': USER_PROFILE_SK})
            except ClientError:
                continue
            item = response.get('Item')
            if isinstance(item, dict):
                return self._to_user(item)
        return None

    def update_user(self, user_id: str, data: dict[str, Any]) -> User | None:
        """Update mutable user profile fields and return updated profile."""
        if self._table is None:
            return None

        existing = self._get_existing_profile_item(user_id)
        if existing is None:
            return None
        existing_item, existing_pk = existing

        now_iso = datetime.now(timezone.utc).isoformat()
        updated_item = dict(existing_item)
        updated_item['pk'] = existing_pk
        updated_item['sk'] = USER_PROFILE_SK
        updated_item['user_id'] = user_id

        if isinstance(data.get('name'), str) and data['name'].strip():
            updated_item['name'] = data['name'].strip()
        updated_item['preferences'] = self._build_updated_preferences(existing_item=existing_item, update_data=data)
        updated_item['updated_at'] = now_iso
        updated_item.setdefault('created_at', now_iso)

        try:
            self._table.put_item(Item=updated_item)
        except ClientError:
            return None

        return self._to_user(updated_item)

    def ensure_user(self, user_id: str, data: dict[str, Any] | None = None) -> User | None:
        """Create a default profile if missing, then apply updates."""
        if self._table is None:
            return None

        existing = self.get_user(user_id)
        if existing is not None:
            return self.update_user(user_id, data or {}) if data else existing

        now_iso = datetime.now(timezone.utc).isoformat()
        item: dict[str, Any] = {
            'pk': f'USER#{user_id}',
            'sk': USER_PROFILE_SK,
            'user_id': user_id,
            'email': f'{user_id}@example.com',
            'name': '',
            'preferences': {},
            'created_at': now_iso,
            'updated_at': now_iso,
        }

        if isinstance(data, dict):
            if isinstance(data.get('name'), str) and data['name'].strip():
                item['name'] = data['name'].strip()
            incoming_preferences = data.get('preferences')
            if isinstance(incoming_preferences, dict):
                item['preferences'] = incoming_preferences
            timezone_value = data.get('timezone')
            if isinstance(timezone_value, str) and timezone_value.strip():
                item.setdefault('preferences', {})
                item['preferences']['timezone'] = timezone_value.strip()

        try:
            self._table.put_item(Item=item)
        except ClientError:
            return None
        return self._to_user(item)

    def _get_existing_profile_item(self, user_id: str) -> tuple[dict[str, Any], str] | None:
        if self._table is None:
            return None
        for pk in self._candidate_partition_keys(user_id):
            try:
                response = self._table.get_item(Key={'pk': pk, 'sk': USER_PROFILE_SK})
            except ClientError:
                continue
            item = response.get('Item')
            if isinstance(item, dict):
                return item, pk
        return None

    @staticmethod
    def _build_updated_preferences(existing_item: dict[str, Any], update_data: dict[str, Any]) -> dict[str, Any]:
        preferences: dict[str, Any] = {}
        existing_preferences = existing_item.get('preferences')
        if isinstance(existing_preferences, dict):
            preferences.update(existing_preferences)

        incoming_preferences = update_data.get('preferences')
        if isinstance(incoming_preferences, dict):
            preferences.update(incoming_preferences)

        timezone_value = update_data.get('timezone')
        if isinstance(timezone_value, str) and timezone_value.strip():
            preferences['timezone'] = timezone_value.strip()
        return preferences

    @staticmethod
    def _candidate_partition_keys(user_id: str) -> tuple[str, str]:
        # Legacy compatibility: some rows may use raw user_id instead of USER#{user_id}.
        return (f'USER#{user_id}', user_id)

    @staticmethod
    def _to_user(item: dict[str, Any]) -> User:
        preferences_value = item.get('preferences')
        preferences = {str(key): value for key, value in preferences_value.items()} if isinstance(preferences_value, dict) else {}

        created_at = UserRepository._parse_datetime(item.get('created_at'))
        updated_at = UserRepository._parse_datetime(item.get('updated_at'))
        email_value = str(item.get('email', '')).strip() or 'unknown@example.com'

        return User(
            user_id=str(item.get('user_id') or str(item.get('pk', '')).removeprefix('USER#')),
            email=email_value,
            name=str(item.get('name', '')),
            preferences=preferences,
            created_at=created_at,
            updated_at=updated_at,
        )

    @staticmethod
    def _parse_datetime(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return datetime.now(timezone.utc)
        return datetime.now(timezone.utc)
