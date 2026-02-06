"""
Jobs Repository for VPR Async Architecture.

Data access layer for VPR async job status tracking stored in DynamoDB.
Provides CRUD operations for job lifecycle management.

Per docs/specs/07-vpr-async-architecture.md
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError

from careervp.handlers.utils.observability import logger, tracer
from careervp.models.result import Result, ResultCode

# GSI name for idempotency key lookup
IDEMPOTENCY_INDEX_NAME = 'idempotency-key-index'


class JobsRepository:
    """Repository for VPR async job status tracking."""

    def __init__(
        self,
        table_name: str | None = None,
        idempotency_index_name: str = IDEMPOTENCY_INDEX_NAME,
    ):
        """
        Initialize jobs repository.

        Args:
            table_name: DynamoDB table name (defaults to VPR_JOBS_TABLE_NAME env var)
            idempotency_index_name: GSI name for idempotency key lookup
        """
        self.dynamodb = boto3.resource('dynamodb')
        self.table_name = table_name or self._get_table_name()
        self.table = self.dynamodb.Table(self.table_name)
        self.idempotency_index = idempotency_index_name

    def _get_table_name(self) -> str:
        """Get table name from environment or use default."""
        import os

        env_table = os.environ.get('VPR_JOBS_TABLE_NAME')
        if env_table:
            return env_table
        # Fallback to naming convention
        env = os.environ.get('ENVIRONMENT', 'dev')
        return f'careervp-vpr-jobs-table-{env}'

    @tracer.capture_method(capture_response=False)
    def create_job(self, job_data: dict[str, Any]) -> Result[dict[str, Any]]:
        """
        Create a new VPR job record in DynamoDB.

        Args:
            job_data: Job record dict containing:
                - job_id: Unique job identifier (UUID)
                - user_id: User who requested the job
                - application_id: Application this VPR is for
                - input_data: VPR request payload
                - idempotency_key: Optional deduplication key
                - ttl: TTL timestamp (optional, calculated if not provided)
                - status: Job status (optional, defaults to PENDING)

        Returns:
            Result containing created job record
        """
        try:
            now = datetime.now(timezone.utc).isoformat()

            # Use provided ttl or calculate default (24 hours)
            ttl_timestamp = job_data.get('ttl')
            if ttl_timestamp is None:
                ttl_timestamp = int((datetime.now(timezone.utc).timestamp() + 24 * 3600))

            record = {
                'job_id': job_data['job_id'],
                'status': job_data.get('status', 'PENDING'),
                'created_at': now,
                'user_id': job_data['user_id'],
                'application_id': job_data['application_id'],
                'input_data': job_data['input_data'],
                'ttl': ttl_timestamp,
            }

            if job_data.get('idempotency_key'):
                record['idempotency_key'] = job_data['idempotency_key']

            self.table.put_item(Item=record)

            logger.info(
                'Created VPR job',
                job_id=job_data['job_id'],
                user_id=job_data['user_id'],
                application_id=job_data['application_id'],
            )

            return Result(success=True, data=record, code=ResultCode.SUCCESS)

        except ClientError as e:
            error_msg = f'DynamoDB error: {e.response["Error"]["Message"]}'
            logger.error(
                error_msg,
                job_id=job_data.get('job_id'),
                error=str(e),
            )
            return Result(
                success=False,
                error=error_msg,
                code=ResultCode.DYNAMODB_ERROR,
            )

    @tracer.capture_method(capture_response=False)
    def get_job(self, job_id: str) -> dict[str, Any] | None:
        """
        Get job record by job_id.

        Args:
            job_id: Unique job identifier

        Returns:
            Job record dict or None if not found
        """
        try:
            response = self.table.get_item(Key={'job_id': job_id})
            job: dict[str, Any] | None = response.get('Item')

            if job:
                logger.info('Found job', job_id=job_id, status=job.get('status'))
            else:
                logger.warning('Job not found', job_id=job_id)

            return job

        except ClientError as e:
            logger.error(
                'Failed to get job',
                job_id=job_id,
                error=str(e),
            )
            return None

    @tracer.capture_method(capture_response=False)
    def get_job_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> dict[str, Any] | None:
        """
        Get job record by idempotency key (for duplicate detection).

        Args:
            idempotency_key: Deduplication key (e.g., "vpr#user_123#app_456")

        Returns:
            Job record dict or None if not found
        """
        try:
            response = self.table.query(
                IndexName=self.idempotency_index,
                KeyConditionExpression='idempotency_key = :key',
                ExpressionAttributeValues={':key': idempotency_key},
                Limit=1,
            )

            items = response.get('Items', [])
            job = items[0] if items else None

            if job:
                logger.info(
                    'Found job by idempotency key',
                    idempotency_key=idempotency_key,
                    job_id=job.get('job_id'),
                )

            return job

        except ClientError as e:
            logger.error(
                'Failed to query by idempotency key',
                idempotency_key=idempotency_key,
                error=str(e),
            )
            return None

    @tracer.capture_method(capture_response=False)
    def update_job_status(
        self,
        job_id: str,
        status: str,
        **kwargs: Any,
    ) -> Result[dict[str, Any]]:
        """
        Update job status and optional timestamps.

        Args:
            job_id: Unique job identifier
            status: New status (PENDING | PROCESSING | COMPLETED | FAILED)
            **kwargs: Optional fields (started_at, completed_at, error, result_key, etc.)

        Returns:
            Result containing updated job record
        """
        try:
            updates = {'status': status}
            updates.update(kwargs)

            update_expr, attr_names, attr_values = self._build_update_expression(updates)

            response = self.table.update_item(
                Key={'job_id': job_id},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=attr_names,
                ExpressionAttributeValues=attr_values,
                ReturnValues='ALL_NEW',
            )

            updated_job = response.get('Attributes', {})

            logger.info(
                'Updated job status',
                job_id=job_id,
                status=status,
            )

            return Result(success=True, data=updated_job, code=ResultCode.SUCCESS)

        except ClientError as e:
            error_msg = f'DynamoDB error: {e.response["Error"]["Message"]}'
            logger.error(
                'Failed to update job status',
                job_id=job_id,
                status=status,
                error=str(e),
            )
            return Result(
                success=False,
                error=error_msg,
                code=ResultCode.DYNAMODB_ERROR,
            )

    @tracer.capture_method(capture_response=False)
    def update_job(
        self,
        job_id: str,
        updates: dict[str, Any],
    ) -> Result[dict[str, Any]]:
        """
        Update job record with multiple fields.

        Args:
            job_id: Unique job identifier
            updates: Dict of fields to update

        Returns:
            Result containing updated job record
        """
        try:
            update_expr, attr_names, attr_values = self._build_update_expression(updates)

            response = self.table.update_item(
                Key={'job_id': job_id},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=attr_names,
                ExpressionAttributeValues=attr_values,
                ReturnValues='ALL_NEW',
            )

            updated_job = response.get('Attributes', {})

            logger.info(
                'Updated job',
                job_id=job_id,
                updates=list(updates.keys()),
            )

            return Result(success=True, data=updated_job, code=ResultCode.SUCCESS)

        except ClientError as e:
            error_msg = f'DynamoDB error: {e.response["Error"]["Message"]}'
            logger.error(
                'Failed to update job',
                job_id=job_id,
                error=str(e),
            )
            return Result(
                success=False,
                error=error_msg,
                code=ResultCode.DYNAMODB_ERROR,
            )

    def _build_update_expression(
        self,
        updates: dict[str, Any],
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        """
        Build DynamoDB UpdateExpression with reserved keyword handling.

        Args:
            updates: Dict of fields to update

        Returns:
            Tuple of (UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues)
        """
        # Reserved DynamoDB keywords that need aliasing
        reserved_keywords = {
            'status',
            'error',
            'name',
            'data',
            'type',
            'value',
            'timestamp',
            'date',
            'time',
            'year',
            'month',
        }

        update_parts = []
        attr_names = {}
        attr_values = {}

        for key, value in updates.items():
            # Use attribute name alias if reserved keyword
            if key.lower() in reserved_keywords:
                attr_name = f'#{key}'
                attr_names[attr_name] = key
            else:
                attr_name = key

            attr_value = f':{key}'
            attr_values[attr_value] = value

            update_parts.append(f'{attr_name} = {attr_value}')

        update_expr = 'SET ' + ', '.join(update_parts)

        return update_expr, attr_names, attr_values
