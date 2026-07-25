"""Durable idempotency claims for at-least-once worker operations."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError

from careervp.handlers.utils.observability import logger, tracer

WORKER_OPERATION_TTL_SECONDS = 86400 * 7


class IdempotencyRepository:
    """Primary-key conditional claims backed by the shared idempotency table."""

    def __init__(
        self,
        table_name: str,
        dynamodb_resource: Any | None = None,
    ) -> None:
        self._table = (dynamodb_resource or boto3.resource('dynamodb')).Table(table_name)

    @tracer.capture_method(capture_response=False)
    def claim_operation(
        self,
        operation_key: str,
        ttl_seconds: int = WORKER_OPERATION_TTL_SECONDS,
    ) -> bool:
        """Claim a stable business operation; return False for a replay."""
        now = int(datetime.now(timezone.utc).timestamp())
        try:
            self._table.put_item(
                Item={
                    'id': operation_key,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'expiration': now + ttl_seconds,
                },
                ConditionExpression='attribute_not_exists(id)',
            )
            return True
        except ClientError as exc:
            if exc.response.get('Error', {}).get('Code') == 'ConditionalCheckFailedException':
                logger.info('worker operation replay suppressed', operation_key=operation_key)
                return False
            raise

    @tracer.capture_method(capture_response=False)
    def release_operation(self, operation_key: str) -> None:
        """Release a failed claim so an SQS retry can perform the operation."""
        self._table.delete_item(Key={'id': operation_key})


def idempotency_repository_from_environment() -> IdempotencyRepository | None:
    """Build the worker repository when the idempotency table is configured."""
    table_name = os.environ.get('IDEMPOTENCY_TABLE_NAME', '').strip()
    return IdempotencyRepository(table_name) if table_name else None


__all__ = [
    'IdempotencyRepository',
    'WORKER_OPERATION_TTL_SECONDS',
    'idempotency_repository_from_environment',
]
