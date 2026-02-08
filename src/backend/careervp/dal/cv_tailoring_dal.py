"""Data access layer for CV tailoring artifacts."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, cast

import boto3


class CVTailoringDAL:
    """DAL for saving and retrieving tailored CV artifacts."""

    def __init__(self, table_name: str | None = None) -> None:
        resource = boto3.resource('dynamodb')
        self.table = resource.Table(table_name) if table_name else resource.Table('cv-tailoring')

    def save_tailored_cv_artifact(
        self,
        user_id: str,
        cv_id: str,
        job_description: str,
        tailored_cv: Any,
        version: int = 1,
        ttl_days: int = 90,
    ) -> dict[str, Any]:
        """Save tailored CV artifact with TTL."""
        now = datetime.now()
        ttl = int((now + timedelta(days=ttl_days)).timestamp())
        artifact_id = f'{cv_id}#{int(now.timestamp())}#v{version}'

        item = {
            'user_id': user_id,
            'artifact_id': artifact_id,
            'cv_id': cv_id,
            'version': version,
            'job_description': job_description,
            'tailored_cv': tailored_cv.dict() if hasattr(tailored_cv, 'dict') else tailored_cv,
            'created_at': now.isoformat(),
            'updated_at': now.isoformat(),
            'ttl': ttl,
        }

        self.table.put_item(Item=item)
        return item

    def get_tailored_cv_artifact(self, user_id: str, artifact_id: str) -> dict[str, Any] | None:
        """Get tailored CV artifact by ID."""
        response = cast(
            dict[str, Any],
            self.table.get_item(Key={'user_id': user_id, 'artifact_id': artifact_id}),
        )
        return cast(dict[str, Any] | None, response.get('Item'))

    def query_tailored_cvs_by_user(
        self,
        user_id: str,
        limit: int | None = None,
        sort_by_date: bool = False,
    ) -> list[dict[str, Any]]:
        """Query tailored CVs by user ID."""
        params: dict[str, Any] = {
            'KeyConditionExpression': 'user_id = :uid',
            'ExpressionAttributeValues': {':uid': user_id},
        }
        if limit is not None:
            params['Limit'] = limit

        response = cast(dict[str, Any], self.table.query(**params))
        items = cast(list[dict[str, Any]], response.get('Items', []))
        if sort_by_date:
            items = sorted(items, key=lambda item: item.get('created_at', ''), reverse=True)
        return items

    def query_tailored_cvs_by_cv_id(self, cv_id: str) -> list[dict[str, Any]]:
        """Query tailored CVs by CV ID."""
        response = cast(
            dict[str, Any],
            self.table.query(
                KeyConditionExpression='cv_id = :cid',
                ExpressionAttributeValues={':cid': cv_id},
            ),
        )
        return cast(list[dict[str, Any]], response.get('Items', []))

    def delete_tailored_cv_artifact(self, user_id: str, artifact_id: str) -> None:
        """Delete tailored CV artifact."""
        self.table.delete_item(Key={'user_id': user_id, 'artifact_id': artifact_id})

    def update_artifact_metadata(self, user_id: str, artifact_id: str, metadata: dict[str, Any]) -> None:
        """Update artifact metadata."""
        self.table.update_item(
            Key={'user_id': user_id, 'artifact_id': artifact_id},
            UpdateExpression='SET metadata = :metadata',
            ExpressionAttributeValues={':metadata': metadata},
        )
