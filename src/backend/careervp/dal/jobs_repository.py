"""
Jobs Repository for VPR Async Architecture.

Data access layer for VPR async job status tracking stored in DynamoDB.
Provides CRUD operations for job lifecycle management.

Per docs/specs/07-vpr-async-architecture.md
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3  # type: ignore[import-untyped]
from boto3.dynamodb.conditions import Key  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from careervp.dal.api_storage_adapter import ApiStorageAdapter
from careervp.handlers.utils.observability import logger, tracer
from careervp.models.result import Result, ResultCode

# GSI name for idempotency key lookup
IDEMPOTENCY_INDEX_NAME = 'idempotency-key-index'
USER_ID_INDEX_NAME = 'user_id-index'
ENTITY_TYPE_INDEX_NAME = 'entity_type-index'


class JobsRepository:
    """Repository for VPR async job status tracking."""

    def __init__(
        self,
        table_name: str | None = None,
        idempotency_index_name: str = IDEMPOTENCY_INDEX_NAME,
        storage_adapter: ApiStorageAdapter | None = None,
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
        self.storage_adapter = storage_adapter or ApiStorageAdapter()

    def _get_table_name(self) -> str:
        """Get table name from environment or use default."""
        env_table = os.environ.get('JOBS_TABLE_NAME') or os.environ.get('VPR_JOBS_TABLE_NAME')
        if env_table:
            return env_table
        # Fallback to naming convention
        env = os.environ.get('ENVIRONMENT', 'dev')
        return f'careervp-vpr-jobs-table-{env}'

    @tracer.capture_method(capture_response=False)
    def create_job(self, job_data: dict[str, Any]) -> Result[dict[str, Any]]:
        """
        Create a new job record in DynamoDB.

        Args:
            job_data: Job record payload. Supports both:
                - API jobs payload (`title`, `company_name`, `description`, ...)
                - VPR async payload (`application_id`, `input_data`, ...)

        Returns:
            Result containing created job record
        """
        try:
            user_id = str(job_data.get('user_id', '')).strip()
            if not user_id:
                raise ValueError('user_id is required')

            requested_job_id = str(job_data.get('job_id', '')).strip()
            resolved_job_id = requested_job_id or str(uuid.uuid4())

            if self._is_vpr_payload(job_data):
                record = self._build_vpr_job_record(job_data=job_data, resolved_job_id=resolved_job_id, user_id=user_id)
            else:
                record = self._build_api_job_record(job_data=job_data, resolved_job_id=resolved_job_id, user_id=user_id)

            self.table.put_item(Item=record)

            logger.info('Created job', job_id=record.get('job_id'), user_id=user_id, status=record.get('status'))

            return Result(success=True, data=record, code=ResultCode.SUCCESS)

        except (ClientError, ValueError) as e:
            if isinstance(e, ClientError):
                error_msg = f'DynamoDB error: {e.response["Error"]["Message"]}'
            else:
                error_msg = str(e)
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

    def list_jobs(self, limit: int = 20) -> list[dict[str, Any]]:
        """List job posting records in the jobs table."""
        safe_limit = max(1, min(limit, 100))
        try:
            response = self.table.query(
                IndexName=ENTITY_TYPE_INDEX_NAME,
                KeyConditionExpression=Key('entity_type').eq('JOB'),
                Limit=safe_limit,
            )
        except ClientError as e:
            logger.error('Failed to list jobs', error=str(e))
            return []
        items = response.get('Items', [])
        return [item for item in items if isinstance(item, dict)]

    def get_jobs_by_user(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """List jobs that belong to a specific user."""
        safe_limit = max(1, min(limit, 100))
        try:
            response = self.table.query(
                IndexName=USER_ID_INDEX_NAME,
                KeyConditionExpression=Key('user_id').eq(user_id),
                Limit=safe_limit,
            )
        except ClientError as e:
            logger.error('Failed to list jobs by user', user_id=user_id, error=str(e))
            return []
        items = response.get('Items', [])
        return [item for item in items if isinstance(item, dict) and item.get('title')]

    def get_vpr_jobs_by_user(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """List VPR async jobs that belong to a specific user."""
        safe_limit = max(1, min(limit, 100))
        try:
            response = self.table.query(
                IndexName=USER_ID_INDEX_NAME,
                KeyConditionExpression=Key('user_id').eq(user_id),
                Limit=safe_limit,
            )
        except ClientError as e:
            logger.error('Failed to list VPR jobs by user', user_id=user_id, error=str(e))
            return []
        items = response.get('Items', [])
        return [item for item in items if isinstance(item, dict) and item.get('application_id')]

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
            response = self.table.get_item(Key=self._build_job_key(job_id))
            job: dict[str, Any] | None = response.get('Item')

            if job:
                logger.info('Found job', job_id=job_id, status=job.get('status'))
            else:
                logger.warning('Job not found', job_id=job_id)

            return job

        except (ClientError, ValueError) as e:
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
        expected_current_status: str | None = None,
        **kwargs: Any,
    ) -> Result[dict[str, Any]]:
        """
        Update job status and optional timestamps.

        Args:
            job_id: Unique job identifier
            status: New status (PENDING | PROCESSING | COMPLETED | FAILED)
            expected_current_status: Optional required current status for atomic transition
            **kwargs: Optional fields (started_at, completed_at, error, result_key, etc.)

        Returns:
            Result containing updated job record
        """
        try:
            updates = {'status': status}
            updates.update(kwargs)

            update_expr, attr_names, attr_values = self._build_update_expression(updates)

            update_kwargs: dict[str, Any] = {
                'Key': self._build_job_key(job_id),
                'UpdateExpression': update_expr,
                'ExpressionAttributeNames': attr_names,
                'ExpressionAttributeValues': attr_values,
                'ReturnValues': 'ALL_NEW',
            }
            if expected_current_status:
                update_kwargs['ConditionExpression'] = '#status = :expected_status'
                attr_names['#status'] = 'status'
                attr_values[':expected_status'] = expected_current_status

            response = self.table.update_item(**update_kwargs)

            updated_job = response.get('Attributes', {})

            logger.info(
                'Updated job status',
                job_id=job_id,
                status=status,
            )

            return Result(success=True, data=updated_job, code=ResultCode.SUCCESS)

        except (ClientError, ValueError) as e:
            if isinstance(e, ClientError):
                error_msg = f'DynamoDB error: {e.response["Error"]["Message"]}'
            else:
                error_msg = str(e)
            logger.error(
                'Failed to update job status',
                job_id=job_id,
                status=status,
                expected_current_status=expected_current_status,
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
                Key=self._build_job_key(job_id),
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

        except (ClientError, ValueError) as e:
            if isinstance(e, ClientError):
                error_msg = f'DynamoDB error: {e.response["Error"]["Message"]}'
            else:
                error_msg = str(e)
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

    def _build_job_key(self, job_id: str) -> dict[str, str]:
        """Build DynamoDB key for the jobs table via adapter mapping."""
        mapping = self.storage_adapter.map_logical_to_physical_keys(
            resource_type='job',
            logical_identifiers={'job_id': job_id},
        )
        jobs_table = mapping.get('jobs_table')
        if not isinstance(jobs_table, dict):
            raise ValueError('Adapter did not return jobs_table mapping for job resource')
        physical_job_id = jobs_table.get('job_id')
        if not isinstance(physical_job_id, str) or not physical_job_id.strip():
            raise ValueError('Adapter returned invalid job_id for jobs table key')
        return {'job_id': physical_job_id.strip()}

    @staticmethod
    def _is_vpr_payload(job_data: dict[str, Any]) -> bool:
        return 'application_id' in job_data or 'input_data' in job_data

    def _build_vpr_job_record(self, job_data: dict[str, Any], resolved_job_id: str, user_id: str) -> dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat()
        job_key = self._build_job_key(resolved_job_id)
        ttl_timestamp = job_data.get('ttl')
        if ttl_timestamp is None:
            ttl_timestamp = int((datetime.now(timezone.utc).timestamp() + 24 * 3600))
        record = {
            'job_id': job_key['job_id'],
            'status': job_data.get('status', 'PENDING'),
            'created_at': job_data.get('created_at', now_iso),
            'user_id': user_id,
            'application_id': job_data.get('application_id', ''),
            'input_data': job_data.get('input_data', {}),
            'ttl': ttl_timestamp,
        }
        if job_data.get('idempotency_key'):
            record['idempotency_key'] = job_data['idempotency_key']
        return record

    def _build_api_job_record(self, job_data: dict[str, Any], resolved_job_id: str, user_id: str) -> dict[str, Any]:
        title = str(job_data.get('title', '')).strip()
        company_name = str(job_data.get('company_name') or job_data.get('company') or '').strip()
        description = str(job_data.get('description', '')).strip()
        if not title or not company_name or not description:
            raise ValueError('title, company_name, and description are required')

        now_iso = datetime.now(timezone.utc).isoformat()
        job_key = self._build_job_key(resolved_job_id)
        status = str(job_data.get('status', 'active')).strip() or 'active'

        requirements: list[str] = []
        raw_requirements = job_data.get('requirements')
        if isinstance(raw_requirements, list):
            requirements = [str(item) for item in raw_requirements if str(item).strip()]

        record: dict[str, Any] = {
            'job_id': job_key['job_id'],
            'user_id': user_id,
            'title': title,
            'company_name': company_name,
            'company': company_name,
            'description': description,
            'status': status,
            'created_at': job_data.get('created_at', now_iso),
            'entity_type': 'JOB',
        }
        url_value = job_data.get('url')
        if isinstance(url_value, str) and url_value.strip():
            record['url'] = url_value.strip()
        if requirements:
            record['requirements'] = requirements
        return record
