# Task 7.5: Jobs Repository (Data Access Layer)

**Status:** Not Started
**Spec Reference:** [[docs/specs/07-vpr-async-architecture.md]]
**Priority:** P0 (BLOCKING - Production VPR generation fails 100%)

## Overview

Create the Jobs Repository DAL module for CRUD operations on the `careervp-jobs-table-dev` DynamoDB table. This module provides clean abstraction for job status tracking, idempotency checks, and job updates.

## Prerequisites

- [ ] Task 7.1 complete (jobs table deployed)
- [ ] Existing DAL pattern in `src/backend/careervp/dal/dynamo_dal_handler.py`
- [ ] DynamoDB jobs table exists with GSI

## Todo

### 1. Create Jobs Repository File

- [ ] Create `src/backend/careervp/dal/jobs_repository.py`
- [ ] Follow existing DAL pattern from `dynamo_dal_handler.py`
- [ ] Use `boto3` DynamoDB resource (not client)
- [ ] Import Result[T] pattern from `models/result.py`

### 2. Implement Core CRUD Methods

- [ ] `create_job(job_data: dict) -> Result[dict]`
  - Validates job_data schema
  - Puts item to DynamoDB
  - Returns created job record
- [ ] `get_job(job_id: str) -> dict | None`
  - Gets item by PK (job_id)
  - Returns job record or None if not found
- [ ] `get_job_by_idempotency_key(key: str) -> dict | None`
  - Queries GSI by idempotency_key
  - Returns job record or None
- [ ] `update_job_status(job_id: str, status: str, **kwargs) -> Result[dict]`
  - Updates status field + optional timestamps
  - Uses update_item with UpdateExpression
- [ ] `update_job(job_id: str, updates: dict) -> Result[dict]`
  - Generic update method for multiple fields
  - Builds UpdateExpression dynamically

### 3. Add Helper Methods

- [ ] `_build_update_expression(updates: dict) -> tuple[str, dict, dict]`
  - Constructs UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues
  - Handles reserved DynamoDB keywords (status, error, etc.)
- [ ] `_validate_job_data(job_data: dict) -> bool`
  - Validates required fields: job_id, status, created_at
  - Returns True if valid, raises ValueError if invalid

### 4. Error Handling

- [ ] Wrap DynamoDB operations in try/except
- [ ] Catch `ClientError` for DynamoDB errors
- [ ] Return `Result[T]` with error details
- [ ] Log all errors with context

### 5. Type Hints & Documentation

- [ ] Add type hints for all methods
- [ ] Add docstrings with examples
- [ ] Document expected job_data schema
- [ ] Add usage examples in docstring

## Codex Implementation Guide

### Implementation: jobs_repository.py

```python
"""
Jobs Repository

Data access layer for VPR async jobs stored in DynamoDB.
Provides CRUD operations and idempotency checks.
"""

from typing import Any

import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

from careervp.models.result import Result

logger = Logger(child=True)


class JobsRepository:
    """Repository for VPR job status tracking."""

    def __init__(self, table_name: str, idempotency_index_name: str = "idempotency-key-index"):
        """
        Initialize jobs repository.

        Args:
            table_name: DynamoDB table name (e.g., careervp-jobs-table-dev)
            idempotency_index_name: GSI name for idempotency key lookup
        """
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)
        self.idempotency_index = idempotency_index_name

    def create_job(self, job_data: dict[str, Any]) -> Result[dict]:
        """
        Create new job record in DynamoDB.

        Args:
            job_data: Job record with required fields:
                - job_id (str): Unique job identifier
                - status (str): PENDING | PROCESSING | COMPLETED | FAILED
                - created_at (str): ISO timestamp
                - idempotency_key (str): Deduplication key
                - user_id (str)
                - application_id (str)
                - input_data (dict): VPR request payload
                - ttl (int): Unix timestamp for auto-deletion

        Returns:
            Result[dict]: Created job record or error

        Example:
            >>> job = {
            ...     "job_id": "550e8400-e29b-41d4-a716-446655440000",
            ...     "status": "PENDING",
            ...     "created_at": "2026-02-03T13:05:32Z",
            ...     "idempotency_key": "vpr#user_123#app_456",
            ...     "user_id": "user_123",
            ...     "application_id": "app_456",
            ...     "input_data": {...},
            ...     "ttl": 1738598400
            ... }
            >>> result = repo.create_job(job)
            >>> if result.success:
            ...     print(f"Created job: {result.data['job_id']}")
        """
        try:
            # Validate required fields
            required_fields = ["job_id", "status", "created_at", "idempotency_key"]
            for field in required_fields:
                if field not in job_data:
                    return Result.failure(f"Missing required field: {field}")

            # Put item to DynamoDB
            self.table.put_item(Item=job_data)

            logger.info("Created job", extra={"job_id": job_data["job_id"]})

            return Result.success(job_data)

        except ClientError as e:
            error_msg = f"DynamoDB error: {e.response['Error']['Message']}"
            logger.error(error_msg, extra={"job_data": job_data})
            return Result.failure(error_msg)

    def get_job(self, job_id: str) -> dict | None:
        """
        Get job record by job_id.

        Args:
            job_id: Unique job identifier

        Returns:
            Job record dict or None if not found

        Example:
            >>> job = repo.get_job("550e8400-e29b-41d4-a716-446655440000")
            >>> if job:
            ...     print(f"Status: {job['status']}")
        """
        try:
            response = self.table.get_item(Key={"job_id": job_id})
            return response.get("Item")

        except ClientError as e:
            logger.error(
                "Failed to get job",
                extra={"job_id": job_id, "error": str(e)}
            )
            return None

    def get_job_by_idempotency_key(self, idempotency_key: str) -> dict | None:
        """
        Get job record by idempotency key (for duplicate detection).

        Args:
            idempotency_key: Deduplication key (e.g., "vpr#user_123#app_456")

        Returns:
            Job record dict or None if not found

        Example:
            >>> job = repo.get_job_by_idempotency_key("vpr#user_123#app_456")
            >>> if job:
            ...     print(f"Duplicate request detected: {job['job_id']}")
        """
        try:
            response = self.table.query(
                IndexName=self.idempotency_index,
                KeyConditionExpression="idempotency_key = :key",
                ExpressionAttributeValues={":key": idempotency_key},
                Limit=1
            )

            items = response.get("Items", [])
            return items[0] if items else None

        except ClientError as e:
            logger.error(
                "Failed to query by idempotency key",
                extra={"idempotency_key": idempotency_key, "error": str(e)}
            )
            return None

    def update_job_status(
        self,
        job_id: str,
        status: str,
        **kwargs: Any
    ) -> Result[dict]:
        """
        Update job status and optional timestamps.

        Args:
            job_id: Unique job identifier
            status: New status (PENDING | PROCESSING | COMPLETED | FAILED)
            **kwargs: Optional fields (started_at, completed_at, etc.)

        Returns:
            Result[dict]: Updated job record or error

        Example:
            >>> result = repo.update_job_status(
            ...     job_id="550e8400",
            ...     status="PROCESSING",
            ...     started_at="2026-02-03T13:05:35Z"
            ... )
        """
        updates = {"status": status}
        updates.update(kwargs)
        return self.update_job(job_id, updates)

    def update_job(self, job_id: str, updates: dict[str, Any]) -> Result[dict]:
        """
        Update job record with multiple fields.

        Args:
            job_id: Unique job identifier
            updates: Dict of fields to update

        Returns:
            Result[dict]: Updated job record or error

        Example:
            >>> result = repo.update_job(
            ...     job_id="550e8400",
            ...     updates={
            ...         "status": "COMPLETED",
            ...         "completed_at": "2026-02-03T13:06:12Z",
            ...         "result_key": "results/550e8400.json",
            ...         "token_usage": {"input": 7500, "output": 2200}
            ...     }
            ... )
        """
        try:
            # Build UpdateExpression
            update_expr, attr_names, attr_values = self._build_update_expression(updates)

            # Update item
            response = self.table.update_item(
                Key={"job_id": job_id},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=attr_names,
                ExpressionAttributeValues=attr_values,
                ReturnValues="ALL_NEW"
            )

            logger.info(
                "Updated job",
                extra={"job_id": job_id, "updates": list(updates.keys())}
            )

            return Result.success(response["Attributes"])

        except ClientError as e:
            error_msg = f"DynamoDB error: {e.response['Error']['Message']}"
            logger.error(
                error_msg,
                extra={"job_id": job_id, "updates": updates}
            )
            return Result.failure(error_msg)

    def _build_update_expression(
        self,
        updates: dict[str, Any]
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        """
        Build DynamoDB UpdateExpression with reserved keyword handling.

        Args:
            updates: Dict of fields to update

        Returns:
            Tuple of (UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues)

        Example:
            >>> expr, names, values = self._build_update_expression({
            ...     "status": "COMPLETED",
            ...     "error": "Some error"  # 'error' is reserved keyword
            ... })
            >>> print(expr)
            'SET #status = :status, #error = :error'
        """
        # Reserved DynamoDB keywords that need aliasing
        reserved_keywords = {
            "status", "error", "name", "data", "type", "value",
            "timestamp", "date", "time", "year", "month"
        }

        update_parts = []
        attr_names = {}
        attr_values = {}

        for key, value in updates.items():
            # Use attribute name alias if reserved keyword
            if key.lower() in reserved_keywords:
                attr_name = f"#{key}"
                attr_names[attr_name] = key
            else:
                attr_name = key

            attr_value = f":{key}"
            attr_values[attr_value] = value

            update_parts.append(f"{attr_name} = {attr_value}")

        update_expr = "SET " + ", ".join(update_parts)

        return update_expr, attr_names, attr_values
```

## Verification Commands

### Local Validation

```bash
# 1. Code formatting
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run ruff format careervp/dal/jobs_repository.py

# 2. Linting
uv run ruff check careervp/dal/jobs_repository.py --fix

# 3. Type checking
uv run mypy careervp/dal/jobs_repository.py --strict

# 4. Unit tests (with moto for DynamoDB mocking)
uv run pytest tests/unit/test_jobs_repository.py -v
```

### Unit Test Example

```python
# tests/unit/test_jobs_repository.py

import pytest
from datetime import datetime, timedelta
from moto import mock_aws
import boto3

from careervp.dal.jobs_repository import JobsRepository


@mock_aws
def test_create_and_get_job():
    """Test job creation and retrieval."""
    # Setup mock DynamoDB table
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.create_table(
        TableName="test-jobs-table",
        KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "job_id", "AttributeType": "S"},
            {"AttributeName": "idempotency_key", "AttributeType": "S"}
        ],
        BillingMode="PAY_PER_REQUEST",
        GlobalSecondaryIndexes=[{
            "IndexName": "idempotency-key-index",
            "KeySchema": [{"AttributeName": "idempotency_key", "KeyType": "HASH"}],
            "Projection": {"ProjectionType": "ALL"}
        }]
    )

    # Create repository
    repo = JobsRepository(table_name="test-jobs-table")

    # Create job
    job_data = {
        "job_id": "test-job-123",
        "status": "PENDING",
        "created_at": datetime.utcnow().isoformat(),
        "idempotency_key": "vpr#user_123#app_456",
        "user_id": "user_123",
        "application_id": "app_456",
        "input_data": {"test": "data"},
        "ttl": int((datetime.utcnow() + timedelta(minutes=10)).timestamp())
    }

    result = repo.create_job(job_data)
    assert result.success
    assert result.data["job_id"] == "test-job-123"

    # Get job
    job = repo.get_job("test-job-123")
    assert job is not None
    assert job["status"] == "PENDING"

    # Get job by idempotency key
    job_by_key = repo.get_job_by_idempotency_key("vpr#user_123#app_456")
    assert job_by_key is not None
    assert job_by_key["job_id"] == "test-job-123"


@mock_aws
def test_update_job_status():
    """Test job status updates."""
    # ... setup ...

    # Update status
    result = repo.update_job_status(
        job_id="test-job-123",
        status="PROCESSING",
        started_at=datetime.utcnow().isoformat()
    )

    assert result.success
    assert result.data["status"] == "PROCESSING"
    assert "started_at" in result.data
```

## Acceptance Criteria

- [ ] Jobs repository created with all CRUD methods
- [ ] `create_job()` validates required fields
- [ ] `get_job()` retrieves by job_id
- [ ] `get_job_by_idempotency_key()` queries GSI
- [ ] `update_job_status()` updates status + timestamps
- [ ] `update_job()` handles multiple field updates
- [ ] Reserved DynamoDB keywords handled (status, error, etc.)
- [ ] All methods return Result[T] or dict/None
- [ ] Code passes ruff, mypy, and unit tests
- [ ] Unit tests cover all methods with moto mocking

## Dependencies

**Blocks:**
- Task 7.2 (Submit Handler) - needs create_job(), get_job_by_idempotency_key()
- Task 7.3 (Worker Handler) - needs update_job(), update_job_status()
- Task 7.4 (Status Handler) - needs get_job()

**Blocked By:**
- Task 7.1 (Infrastructure) - needs jobs table deployed

## Estimated Effort

**Time:** 3-4 hours
**Complexity:** LOW-MEDIUM (standard DAL pattern with DynamoDB)

## Notes

- Follow existing DAL pattern from `dynamo_dal_handler.py`
- Use Result[T] pattern for operations that can fail
- Handle DynamoDB reserved keywords (status, error, name, etc.)
- GSI query returns list, take first item for idempotency check
- Update methods use `UpdateExpression` for atomic updates
