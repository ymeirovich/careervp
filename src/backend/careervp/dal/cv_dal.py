"""Compatibility DAL for CV retrieval used by integration tests."""

from __future__ import annotations

import os
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import BotoCoreError, ClientError


class CVTable:
    """Lightweight CV table wrapper."""

    def __init__(self, table_name: str | None = None) -> None:
        resolved_table_name = table_name or os.getenv('TABLE_NAME') or 'cv-table'
        resource = boto3.resource('dynamodb')
        self.table = resource.Table(resolved_table_name)

    def get_item(self, key: dict[str, Any]) -> dict[str, Any]:
        """Proxy get_item to underlying table."""
        try:
            return cast(dict[str, Any], self.table.get_item(Key=key))
        except (BotoCoreError, ClientError):
            return {}

    def put_item(self, Item: dict[str, Any]) -> dict[str, Any]:  # noqa: N803
        """Proxy put_item to underlying table."""
        return cast(dict[str, Any], self.table.put_item(Item=Item))

    def save_tailored_cv_artifact(
        self,
        user_id: str,
        cv_id: str,
        job_description: str,
        tailored_cv: Any,
        version: int = 1,
        ttl_days: int = 90,
    ) -> dict[str, Any]:
        """Persist tailored CV artifact using users-table pk/sk schema."""
        now = datetime.now(UTC)
        created_at = now.isoformat()
        artifact_id = f'TAILORED_CV#{cv_id}#{int(now.timestamp())}#v{version}'
        ttl = int((now + timedelta(days=ttl_days)).timestamp())
        payload = tailored_cv.model_dump(mode='json') if hasattr(tailored_cv, 'model_dump') else tailored_cv

        item: dict[str, Any] = {
            'pk': user_id,
            'sk': artifact_id,
            'entity_type': 'CV_TAILORING',
            'user_id': user_id,
            'cv_id': cv_id,
            'job_description': job_description,
            'version': version,
            'tailored_cv': payload,
            'created_at': created_at,
            'updated_at': created_at,
            'ttl': ttl,
        }
        self.put_item(Item=item)
        return item

    def get_cv_item(self, user_id: str | None, cv_id: str | None) -> dict[str, Any]:
        """Resolve CV item across current (pk/sk) and legacy (cv_id) schemas."""
        if user_id:
            response = self.get_item({'pk': user_id, 'sk': 'CV'})
            if isinstance(response.get('Item'), Mapping):
                return response

        if not cv_id:
            return {}

        # Legacy table shape: PK is cv_id.
        legacy_response = self.get_item({'cv_id': cv_id})
        if isinstance(legacy_response.get('Item'), Mapping):
            return legacy_response

        # Compatibility fallback: prefer a partition-bounded query when user_id is available.
        if user_id:
            try:
                query_response = cast(
                    dict[str, Any],
                    self.table.query(
                        KeyConditionExpression=Key('pk').eq(user_id),
                        FilterExpression=Attr('cv_id').eq(cv_id),
                        Limit=1,
                    ),
                )
            except (BotoCoreError, ClientError):
                return {}

            items = query_response.get('Items')
            if isinstance(items, list) and items:
                first_item = items[0]
                if isinstance(first_item, Mapping):
                    return {'Item': dict(first_item)}
        return {}
