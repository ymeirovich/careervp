# Task 9.7: CV Tailoring - DynamoDB DAL Extensions (OPTIONAL)

**Status:** Pending (Optional enhancement)
**Spec Reference:** [docs/specs/04-cv-tailoring.md](../../specs/04-cv-tailoring.md)
**Depends On:** Task 9.6 (Handler)
**Blocking:** None (Optional)

## Overview

Extend DynamoDB Data Access Layer with methods for storing and retrieving tailored CV artifacts. Implements persistence for tailored CV snapshots, metadata, and provides query methods for accessing previous tailoring results by user or application.

## Todo

### DAL Extension Implementation

- [ ] Modify `src/backend/careervp/dal/dynamo_dal_handler.py`
- [ ] Implement `save_tailored_cv()` method with TTL
- [ ] Implement `get_tailored_cv()` method for single artifact
- [ ] Implement `list_tailored_cvs_for_user()` method
- [ ] Implement `list_tailored_cvs_for_application()` method
- [ ] Implement `delete_tailored_cv()` method for cleanup
- [ ] Add DynamoDB schema documentation for tailored CV table

### Test Implementation

- [ ] Create `tests/dal/test_tailoring_dal_unit.py`
- [ ] Implement 10-15 unit tests with mocked DynamoDB
- [ ] Test save operations (3 tests)
- [ ] Test retrieval operations (3 tests)
- [ ] Test query operations (3 tests)
- [ ] Test error handling (3 tests)

### Validation & Formatting

- [ ] Run `uv run ruff format src/backend/careervp/dal/`
- [ ] Run `uv run ruff check --fix src/backend/careervp/dal/`
- [ ] Run `uv run mypy src/backend/careervp/dal/ --strict`
- [ ] Run `uv run pytest tests/dal/test_tailoring_dal_unit.py -v`

### Commit

- [ ] Commit with message: `feat(dal): add CV tailored artifact persistence methods`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `src/backend/careervp/dal/dynamo_dal_handler.py` | Extend existing DAL handler |
| `tests/dal/test_tailoring_dal_unit.py` | Unit tests for DAL methods |

### DynamoDB Schema

**Table: cv-tailored-artifacts**

```
Primary Key:
  PK: application_id (STRING)
  SK: created_at (STRING, ISO timestamp)

Global Secondary Indexes:
  user_id_created_at_gsi:
    PK: user_id (STRING)
    SK: created_at (STRING)
    Projection: ALL

Attributes:
  - application_id (PK, STRING)
  - created_at (SK, STRING)
  - user_id (STRING, indexed)
  - job_id (STRING)
  - cv_version (NUMBER)
  - tailored_cv (JSON, compressed)
  - metadata (JSON)
  - token_usage (JSON)
  - fvs_validation_passed (BOOLEAN)
  - expiration_timestamp (NUMBER, TTL attribute, 90 days)
  - checksum (STRING, for integrity verification)

TTL:
  - Attribute: expiration_timestamp
  - Default: current_timestamp + 90 days (7,776,000 seconds)
```

### Key Implementation Details

```python
"""
DynamoDB DAL Extensions for CV Tailoring.
Per docs/specs/04-cv-tailoring.md.

Extends existing DynamoDalHandler with methods for:
- Persisting tailored CV artifacts
- Querying tailored CVs by user or application
- Managing artifact lifecycle with TTL

Schema:
  PK: application_id
  SK: created_at
  GSI: user_id + created_at (for user-based queries)
  TTL: 90 days from creation

All methods return Result[T] for consistency with existing patterns.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from careervp.models.result import Result, ResultCode
from careervp.handlers.utils.observability import logger, tracer

if TYPE_CHECKING:
    from careervp.models.tailor import TailoredCVData


@tracer.capture_method(capture_response=False)
def save_tailored_cv(
    self,
    application_id: str,
    tailored_cv: TailoredCVData,
) -> Result[str]:
    """
    Persist tailored CV artifact to DynamoDB.

    Stores tailored CV with metadata, token usage, and TTL expiration.
    Enables later retrieval for review or re-use.

    Schema:
    {
        "application_id": application_id,
        "created_at": ISO_TIMESTAMP,
        "user_id": from tailored_cv.metadata.user_id,
        "job_id": from tailored_cv.metadata.job_id,
        "cv_version": from tailored_cv.tailored_cv.source_cv_version,
        "tailored_cv": {compressed JSON},
        "metadata": {...},
        "token_usage": {...},
        "fvs_validation_passed": boolean,
        "expiration_timestamp": unix_timestamp (90 days from now),
        "checksum": SHA256(content)
    }

    Args:
        self: DAL handler instance
        application_id: Application identifier (PK)
        tailored_cv: TailoredCVData with CV, metadata, and token usage

    Returns:
        Result[str] with success=True and artifact_id, or error details.

    Example:
        >>> dal = DynamoDalHandler()
        >>> tailored = TailoredCVData(...)
        >>> result = dal.save_tailored_cv("app_123", tailored)
        >>> assert result.success
        >>> assert result.data  # artifact_id
    """
    # PSEUDO-CODE:
    # try:
    #     now = datetime.utcnow()
    #     created_at = now.isoformat()
    #     expiration = now + timedelta(days=90)
    #     expiration_timestamp = int(expiration.timestamp())
    #
    #     item = {
    #         "application_id": application_id,
    #         "created_at": created_at,
    #         "user_id": tailored_cv.metadata.user_id,
    #         "job_id": tailored_cv.metadata.job_id,
    #         "cv_version": tailored_cv.tailored_cv.source_cv_version,
    #         "tailored_cv": tailored_cv.tailored_cv.model_dump(),
    #         "metadata": tailored_cv.metadata.model_dump(),
    #         "token_usage": tailored_cv.token_usage.model_dump(),
    #         "fvs_validation_passed": tailored_cv.metadata.fvs_validation_passed,
    #         "expiration_timestamp": expiration_timestamp,
    #         "checksum": compute_checksum(tailored_cv),
    #     }
    #
    #     table = self.dynamodb.Table(self.env.TAILORED_CV_TABLE_NAME)
    #     table.put_item(Item=item)
    #
    #     logger.info(
    #         "tailored CV persisted",
    #         application_id=application_id,
    #         artifact_id=f"{application_id}#{created_at}",
    #     )
    #
    #     return Result(
    #         success=True,
    #         data=f"{application_id}#{created_at}",
    #         code=ResultCode.SUCCESS,
    #     )
    #
    # except Exception as exc:
    #     logger.exception("failed to persist tailored CV", application_id=application_id)
    #     return Result(
    #         success=False,
    #         error=str(exc),
    #         code=ResultCode.DATABASE_ERROR,
    #     )

    pass


@tracer.capture_method(capture_response=False)
def get_tailored_cv(
    self,
    application_id: str,
    created_at: str,
) -> Result[TailoredCVData]:
    """
    Retrieve single tailored CV artifact.

    Args:
        self: DAL handler instance
        application_id: Application ID (PK)
        created_at: Creation timestamp (SK, ISO format)

    Returns:
        Result[TailoredCVData] with tailored CV or error details.

    Example:
        >>> result = dal.get_tailored_cv("app_123", "2025-02-04T10:30:00")
        >>> assert result.success
        >>> assert result.data.tailored_cv.executive_summary
    """
    # PSEUDO-CODE:
    # try:
    #     table = self.dynamodb.Table(self.env.TAILORED_CV_TABLE_NAME)
    #     response = table.get_item(
    #         Key={
    #             "application_id": application_id,
    #             "created_at": created_at,
    #         }
    #     )
    #
    #     if "Item" not in response:
    #         logger.warning("tailored CV not found", application_id=application_id)
    #         return Result(
    #             success=False,
    #             error="Tailored CV not found",
    #             code=ResultCode.NOT_FOUND,
    #         )
    #
    #     item = response["Item"]
    #     tailored_cv = TailoredCVData(
    #         tailored_cv=TailoredCV(**item["tailored_cv"]),
    #         metadata=TailoringMetadata(**item["metadata"]),
    #         token_usage=TokenUsage(**item["token_usage"]),
    #     )
    #
    #     logger.info("tailored CV retrieved", application_id=application_id)
    #     return Result(success=True, data=tailored_cv, code=ResultCode.SUCCESS)
    #
    # except Exception as exc:
    #     logger.exception("failed to retrieve tailored CV")
    #     return Result(success=False, error=str(exc), code=ResultCode.DATABASE_ERROR)

    pass


@tracer.capture_method(capture_response=False)
def list_tailored_cvs_for_user(
    self,
    user_id: str,
    limit: int = 10,
    start_key: dict | None = None,
) -> Result[dict]:
    """
    List all tailored CVs for a user.

    Uses GSI: user_id_created_at_gsi
    Ordered by created_at (most recent first)

    Args:
        self: DAL handler instance
        user_id: User identifier
        limit: Max results to return
        start_key: Pagination token from previous response

    Returns:
        Result[dict] with:
        - success: True if query succeeded
        - data: {
            "items": [TailoredCVData, ...],
            "last_evaluated_key": pagination_token (or None),
            "count": number of items,
          }

    Example:
        >>> result = dal.list_tailored_cvs_for_user("user_123", limit=5)
        >>> assert result.success
        >>> assert len(result.data["items"]) <= 5
    """
    # PSEUDO-CODE:
    # try:
    #     table = self.dynamodb.Table(self.env.TAILORED_CV_TABLE_NAME)
    #     query_kwargs = {
    #         "IndexName": "user_id_created_at_gsi",
    #         "KeyConditionExpression": "user_id = :user_id",
    #         "ExpressionAttributeValues": {":user_id": user_id},
    #         "Limit": limit,
    #         "ScanIndexForward": False,  # Most recent first
    #     }
    #
    #     if start_key:
    #         query_kwargs["ExclusiveStartKey"] = start_key
    #
    #     response = table.query(**query_kwargs)
    #
    #     items = [
    #         TailoredCVData(
    #             tailored_cv=TailoredCV(**item["tailored_cv"]),
    #             metadata=TailoringMetadata(**item["metadata"]),
    #             token_usage=TokenUsage(**item["token_usage"]),
    #         )
    #         for item in response.get("Items", [])
    #     ]
    #
    #     return Result(
    #         success=True,
    #         data={
    #             "items": items,
    #             "last_evaluated_key": response.get("LastEvaluatedKey"),
    #             "count": response.get("Count", 0),
    #         },
    #         code=ResultCode.SUCCESS,
    #     )
    #
    # except Exception as exc:
    #     logger.exception("failed to list tailored CVs for user", user_id=user_id)
    #     return Result(success=False, error=str(exc), code=ResultCode.DATABASE_ERROR)

    pass


@tracer.capture_method(capture_response=False)
def list_tailored_cvs_for_application(
    self,
    application_id: str,
) -> Result[list[TailoredCVData]]:
    """
    List all tailored CV versions for an application.

    Uses primary key: application_id
    Returns all versions ordered by created_at (most recent first)

    Args:
        self: DAL handler instance
        application_id: Application identifier

    Returns:
        Result[list[TailoredCVData]] with all versions or error.

    Example:
        >>> result = dal.list_tailored_cvs_for_application("app_123")
        >>> assert result.success
        >>> assert len(result.data) > 0
    """
    # PSEUDO-CODE:
    # try:
    #     table = self.dynamodb.Table(self.env.TAILORED_CV_TABLE_NAME)
    #     response = table.query(
    #         KeyConditionExpression="application_id = :app_id",
    #         ExpressionAttributeValues={":app_id": application_id},
    #         ScanIndexForward=False,  # Most recent first
    #     )
    #
    #     items = [
    #         TailoredCVData(...)
    #         for item in response.get("Items", [])
    #     ]
    #
    #     return Result(success=True, data=items, code=ResultCode.SUCCESS)
    #
    # except Exception as exc:
    #     logger.exception("failed to list versions", application_id=application_id)
    #     return Result(success=False, error=str(exc), code=ResultCode.DATABASE_ERROR)

    pass


@tracer.capture_method(capture_response=False)
def delete_tailored_cv(
    self,
    application_id: str,
    created_at: str,
) -> Result[None]:
    """
    Delete tailored CV artifact.

    Used for cleanup or removal of unwanted results.

    Args:
        self: DAL handler instance
        application_id: Application ID (PK)
        created_at: Creation timestamp (SK)

    Returns:
        Result[None] with success or error details.

    Example:
        >>> result = dal.delete_tailored_cv("app_123", "2025-02-04T10:30:00")
        >>> assert result.success
    """
    # PSEUDO-CODE:
    # try:
    #     table = self.dynamodb.Table(self.env.TAILORED_CV_TABLE_NAME)
    #     table.delete_item(
    #         Key={
    #             "application_id": application_id,
    #             "created_at": created_at,
    #         }
    #     )
    #
    #     logger.info(
    #         "tailored CV deleted",
    #         application_id=application_id,
    #         created_at=created_at,
    #     )
    #
    #     return Result(success=True, data=None, code=ResultCode.SUCCESS)
    #
    # except Exception as exc:
    #     logger.exception("failed to delete tailored CV")
    #     return Result(success=False, error=str(exc), code=ResultCode.DATABASE_ERROR)

    pass


def compute_checksum(tailored_cv: TailoredCVData) -> str:
    """
    Compute SHA256 checksum of tailored CV content.

    Used for integrity verification and deduplication.

    Args:
        tailored_cv: TailoredCVData to checksum

    Returns:
        Hex-encoded SHA256 hash

    Example:
        >>> tailored = TailoredCVData(...)
        >>> checksum = compute_checksum(tailored)
        >>> assert len(checksum) == 64  # SHA256 hex length
    """
    # PSEUDO-CODE:
    # import hashlib
    # import json
    # content = json.dumps(tailored_cv.model_dump(mode='json'), sort_keys=True)
    # return hashlib.sha256(content.encode()).hexdigest()

    pass
```

### Test Implementation Structure

```python
"""
Unit Tests for CV Tailoring DAL.
Per tests/dal/test_tailoring_dal_unit.py.

Uses mocked DynamoDB (boto3.resource mock).
No actual AWS calls in unit tests.

Test categories:
- Save operations (3 tests)
- Retrieval operations (3 tests)
- Query operations (3 tests)
- Error handling (3 tests)

Total: 10-15 tests
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.models.tailor import TailoredCVData


class TestSaveOperations:
    """Test tailored CV save operations."""

    def test_save_tailored_cv_creates_item(self):
        """Save operation creates DynamoDB item."""
        # PSEUDO-CODE:
        # dal = DynamoDalHandler()
        # tailored = Mock(TailoredCVData)
        # tailored.metadata = Mock(user_id="user_123")
        # 
        # with patch.object(dal, 'dynamodb') as mock_db:
        #     mock_table = MagicMock()
        #     mock_db.Table.return_value = mock_table
        #     
        #     result = dal.save_tailored_cv("app_123", tailored)
        #     
        #     assert result.success
        #     mock_table.put_item.assert_called_once()
        pass

    def test_save_tailored_cv_includes_ttl(self):
        """Save operation includes TTL expiration."""
        # PSEUDO-CODE:
        # dal = DynamoDalHandler()
        # tailored = Mock(TailoredCVData)
        # 
        # with patch.object(dal, 'dynamodb') as mock_db:
        #     mock_table = MagicMock()
        #     mock_db.Table.return_value = mock_table
        #     
        #     dal.save_tailored_cv("app_123", tailored)
        #     
        #     call_args = mock_table.put_item.call_args
        #     item = call_args[1]['Item']
        #     assert 'expiration_timestamp' in item
        #     # Should be ~90 days from now
        pass

    def test_save_tailored_cv_returns_artifact_id(self):
        """Save operation returns artifact identifier."""
        # PSEUDO-CODE:
        # dal = DynamoDalHandler()
        # result = dal.save_tailored_cv("app_123", Mock())
        # assert result.success
        # assert result.data  # artifact_id
        # assert "app_123" in result.data
        pass


class TestRetrievalOperations:
    """Test tailored CV retrieval."""

    def test_get_tailored_cv_retrieves_item(self):
        """Get operation retrieves from DynamoDB."""
        # PSEUDO-CODE:
        # dal = DynamoDalHandler()
        # with patch.object(dal, 'dynamodb') as mock_db:
        #     mock_table = MagicMock()
        #     mock_table.get_item.return_value = {
        #         'Item': {
        #             'tailored_cv': {...},
        #             'metadata': {...},
        #             'token_usage': {...},
        #         }
        #     }
        #     mock_db.Table.return_value = mock_table
        #     
        #     result = dal.get_tailored_cv("app_123", "2025-02-04T10:30:00")
        #     assert result.success
        #     assert result.data
        pass

    def test_get_tailored_cv_returns_not_found(self):
        """Get operation returns NOT_FOUND when missing."""
        # PSEUDO-CODE:
        # dal = DynamoDalHandler()
        # with patch.object(dal, 'dynamodb') as mock_db:
        #     mock_table = MagicMock()
        #     mock_table.get_item.return_value = {}  # No Item
        #     mock_db.Table.return_value = mock_table
        #     
        #     result = dal.get_tailored_cv("app_123", "2025-02-04T10:30:00")
        #     assert not result.success
        #     assert "not found" in result.error.lower()
        pass

    def test_get_tailored_cv_reconstructs_model(self):
        """Get operation reconstructs TailoredCVData model."""
        # PSEUDO-CODE:
        # dal = DynamoDalHandler()
        # with patch.object(dal, 'dynamodb') as mock_db:
        #     mock_table = MagicMock()
        #     mock_table.get_item.return_value = {
        #         'Item': {
        #             'tailored_cv': {...},
        #             'metadata': {...},
        #             'token_usage': {...},
        #         }
        #     }
        #     mock_db.Table.return_value = mock_table
        #     
        #     result = dal.get_tailored_cv("app_123", "2025-02-04T10:30:00")
        #     assert isinstance(result.data, TailoredCVData)
        pass
```

### Verification Commands

```bash
# Format code
uv run ruff format src/backend/careervp/dal/

# Check for style issues
uv run ruff check --fix src/backend/careervp/dal/

# Type check with strict mode
uv run mypy src/backend/careervp/dal/ --strict

# Run DAL tests
uv run pytest tests/dal/test_tailoring_dal_unit.py -v

# Expected output:
# ===== test session starts =====
# tests/dal/test_tailoring_dal_unit.py::TestSaveOperations PASSED (3 tests)
# tests/dal/test_tailoring_dal_unit.py::TestRetrievalOperations PASSED (3 tests)
# ... [10-15 total tests]
# ===== 10-15 passed in X.XXs =====
```

### Expected Test Results

```
tests/dal/test_tailoring_dal_unit.py PASSED

Save Operations: 3 PASSED
- Creates item in DynamoDB
- Includes TTL expiration (90 days)
- Returns artifact ID

Retrieval Operations: 3 PASSED
- Retrieves from DynamoDB
- Returns NOT_FOUND when missing
- Reconstructs TailoredCVData model

Query Operations: 3 PASSED
- Lists by user (GSI query)
- Lists by application (primary key query)
- Supports pagination

Error Handling: 3 PASSED
- Handles DynamoDB errors gracefully
- Returns Result with error details
- Logs exceptions appropriately

Total: 10-15 tests passing
Type checking: 0 errors, 0 warnings
Database operations: All mocked
```

### Zero-Hallucination Checklist

- [ ] TTL exactly 90 days from creation
- [ ] All required attributes included in schema
- [ ] GSI correct for user-based queries
- [ ] No sensitive data stored unencrypted
- [ ] Checksum computation deterministic
- [ ] All methods return Result[T] pattern
- [ ] Error handling consistent with existing DAL
- [ ] Pagination token handling correct
- [ ] TTL attribute name matches DynamoDB configuration
- [ ] No hardcoded table names (use environment variables)

### Acceptance Criteria

- [ ] `save_tailored_cv()` persists artifact with TTL
- [ ] `get_tailored_cv()` retrieves single artifact
- [ ] `list_tailored_cvs_for_user()` queries by user_id
- [ ] `list_tailored_cvs_for_application()` queries by application_id
- [ ] `delete_tailored_cv()` removes artifact
- [ ] All methods return Result[T] with proper codes
- [ ] DynamoDB table configured with TTL
- [ ] GSI created for user-based queries
- [ ] 10-15 unit tests all passing
- [ ] Type checking passes with `mypy --strict`
- [ ] Integration with existing DynamoDalHandler works
- [ ] No integration tests (optional, mocked only)

---

### Verification & Compliance

1. Run `python src/backend/scripts/validate_naming.py --path src/backend/careervp/dal --strict`
2. Run `uv run ruff format . && uv run ruff check --fix . && uv run mypy --strict .`
3. Run `uv run pytest tests/dal/test_tailoring_dal_unit.py -v --cov`
4. If any DAL method fails, report a **BLOCKING ISSUE** and exit.

---

## Notes on Optional Status

This task is marked **OPTIONAL** because:
1. Handler can function without persistence (returns tailored CV immediately)
2. Phase 11 (Gap Analysis) will likely require more sophisticated artifact management
3. Can be deferred to Phase 9.2 if time constraints exist
4. Mocking in tests eliminates need for actual DynamoDB during Phase 9

If implementing, follow this priority:
1. `save_tailored_cv()` - Core persistence function
2. `get_tailored_cv()` - Enable artifact retrieval
3. `list_tailored_cvs_for_user()` - User-based queries
4. Remaining query/delete methods - Optional enhancements
