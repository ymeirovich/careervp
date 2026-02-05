# Task 10.7: DAL Extensions for Cover Letters

**Status:** Pending (OPTIONAL)
**Spec Reference:** [docs/specs/cover-letter/COVER_LETTER_SPEC.md](../../specs/cover-letter/COVER_LETTER_SPEC.md)
**Depends On:** Task 10.8 (Models)
**Blocking:** None
**Complexity:** Low
**Duration:** 1 hour
**Test File:** `tests/cover-letter/unit/test_cover_letter_dal_unit.py` (10-15 tests)

## Overview

Extend DAL (Data Access Layer) with methods for cover letter artifact storage. Uses existing DynamoDB artifacts table with new sort key pattern for cover letters. 90-day TTL for automatic cleanup.

## Todo

### DAL Implementation

- [ ] Add `save_cover_letter_artifact()` to dynamo_dal_handler.py
- [ ] Add `get_cover_letter_artifact()` method
- [ ] Add `delete_cover_letter_artifact()` method
- [ ] Add `list_cover_letters_by_user()` method
- [ ] Implement 90-day TTL calculation
- [ ] Add versioning support

### Test Implementation

- [ ] Create `tests/cover-letter/unit/test_cover_letter_dal_unit.py`
- [ ] Test save artifact
- [ ] Test get artifact (exists/not exists)
- [ ] Test delete artifact
- [ ] Test TTL calculation
- [ ] Test versioning

---

## Codex Implementation Guide

### File Path

Extend: `src/backend/careervp/dal/dynamo_dal_handler.py`

### DynamoDB Key Structure

```python
"""
Cover Letter Artifact Key Structure:
- PK: user_id (e.g., "user_789")
- SK: ARTIFACT#COVER_LETTER#{cv_id}#{job_id}#v{version}
- GSI1PK: cv_id
- GSI1SK: ARTIFACT#COVER_LETTER#{job_id}#v{version}

TTL: 90 days from creation
"""

COVER_LETTER_ARTIFACT_PREFIX = "ARTIFACT#COVER_LETTER"
COVER_LETTER_TTL_DAYS = 90
```

### Key Implementation

```python
"""
DAL extensions for cover letter artifacts.
Add these methods to DynamoDalHandler class.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from careervp.models.cover_letter_models import TailoredCoverLetter
from careervp.models.result import Result, ResultCode


async def save_cover_letter_artifact(
    self,
    cover_letter: TailoredCoverLetter,
) -> Result[str]:
    """Save cover letter artifact to DynamoDB.

    Args:
        cover_letter: TailoredCoverLetter to save

    Returns:
        Result with artifact ID or error
    """
    try:
        # Calculate TTL (90 days from now)
        ttl = int((datetime.now() + timedelta(days=COVER_LETTER_TTL_DAYS)).timestamp())

        # Get next version
        version = await self._get_next_cover_letter_version(
            cover_letter.user_id,
            cover_letter.cv_id,
            cover_letter.job_id,
        )

        # Build sort key
        sk = f"{COVER_LETTER_ARTIFACT_PREFIX}#{cover_letter.cv_id}#{cover_letter.job_id}#v{version}"

        item = {
            "PK": cover_letter.user_id,
            "SK": sk,
            "GSI1PK": cover_letter.cv_id,
            "GSI1SK": f"{COVER_LETTER_ARTIFACT_PREFIX}#{cover_letter.job_id}#v{version}",
            "artifact_type": "COVER_LETTER",
            "cover_letter_id": cover_letter.cover_letter_id,
            "cv_id": cover_letter.cv_id,
            "job_id": cover_letter.job_id,
            "company_name": cover_letter.company_name,
            "job_title": cover_letter.job_title,
            "content": cover_letter.content,
            "word_count": cover_letter.word_count,
            "personalization_score": str(cover_letter.personalization_score),
            "relevance_score": str(cover_letter.relevance_score),
            "tone_score": str(cover_letter.tone_score),
            "version": version,
            "created_at": cover_letter.generated_at.isoformat(),
            "ttl": ttl,
        }

        await self._put_item(item)

        self.logger.info(
            "Saved cover letter artifact",
            cover_letter_id=cover_letter.cover_letter_id,
            version=version,
        )

        return Result.success(
            data=cover_letter.cover_letter_id,
            code=ResultCode.SUCCESS,
        )

    except Exception as e:
        self.logger.exception("Failed to save cover letter artifact")
        return Result.failure(
            error=str(e),
            code=ResultCode.DAL_ERROR,
        )


async def get_cover_letter_artifact(
    self,
    user_id: str,
    cv_id: str,
    job_id: str,
    version: Optional[int] = None,
) -> Result[TailoredCoverLetter]:
    """Retrieve cover letter artifact from DynamoDB.

    Args:
        user_id: User ID
        cv_id: CV ID
        job_id: Job ID
        version: Specific version (None = latest)

    Returns:
        Result with TailoredCoverLetter or error
    """
    try:
        if version is None:
            # Get latest version
            version = await self._get_latest_cover_letter_version(
                user_id, cv_id, job_id
            )
            if version == 0:
                return Result.failure(
                    error="Cover letter not found",
                    code=ResultCode.NOT_FOUND,
                )

        sk = f"{COVER_LETTER_ARTIFACT_PREFIX}#{cv_id}#{job_id}#v{version}"

        item = await self._get_item(pk=user_id, sk=sk)

        if not item:
            return Result.failure(
                error="Cover letter not found",
                code=ResultCode.NOT_FOUND,
            )

        cover_letter = TailoredCoverLetter(
            cover_letter_id=item["cover_letter_id"],
            cv_id=item["cv_id"],
            job_id=item["job_id"],
            user_id=user_id,
            company_name=item["company_name"],
            job_title=item["job_title"],
            content=item["content"],
            word_count=int(item["word_count"]),
            personalization_score=float(item["personalization_score"]),
            relevance_score=float(item["relevance_score"]),
            tone_score=float(item["tone_score"]),
            generated_at=datetime.fromisoformat(item["created_at"]),
        )

        return Result.success(
            data=cover_letter,
            code=ResultCode.SUCCESS,
        )

    except Exception as e:
        self.logger.exception("Failed to get cover letter artifact")
        return Result.failure(
            error=str(e),
            code=ResultCode.DAL_ERROR,
        )


async def delete_cover_letter_artifact(
    self,
    user_id: str,
    cv_id: str,
    job_id: str,
    version: int,
) -> Result[bool]:
    """Delete cover letter artifact from DynamoDB.

    Args:
        user_id: User ID
        cv_id: CV ID
        job_id: Job ID
        version: Version to delete

    Returns:
        Result with success boolean
    """
    try:
        sk = f"{COVER_LETTER_ARTIFACT_PREFIX}#{cv_id}#{job_id}#v{version}"
        await self._delete_item(pk=user_id, sk=sk)

        return Result.success(data=True, code=ResultCode.SUCCESS)

    except Exception as e:
        self.logger.exception("Failed to delete cover letter artifact")
        return Result.failure(error=str(e), code=ResultCode.DAL_ERROR)


async def list_cover_letters_by_user(
    self,
    user_id: str,
    limit: int = 20,
) -> Result[List[TailoredCoverLetter]]:
    """List all cover letters for a user.

    Args:
        user_id: User ID
        limit: Max items to return

    Returns:
        Result with list of cover letters
    """
    try:
        items = await self._query(
            pk=user_id,
            sk_prefix=COVER_LETTER_ARTIFACT_PREFIX,
            limit=limit,
        )

        cover_letters = [
            TailoredCoverLetter(
                cover_letter_id=item["cover_letter_id"],
                cv_id=item["cv_id"],
                job_id=item["job_id"],
                user_id=user_id,
                company_name=item["company_name"],
                job_title=item["job_title"],
                content=item["content"],
                word_count=int(item["word_count"]),
                personalization_score=float(item["personalization_score"]),
                relevance_score=float(item["relevance_score"]),
                tone_score=float(item["tone_score"]),
                generated_at=datetime.fromisoformat(item["created_at"]),
            )
            for item in items
        ]

        return Result.success(data=cover_letters, code=ResultCode.SUCCESS)

    except Exception as e:
        self.logger.exception("Failed to list cover letters")
        return Result.failure(error=str(e), code=ResultCode.DAL_ERROR)


async def _get_next_cover_letter_version(
    self,
    user_id: str,
    cv_id: str,
    job_id: str,
) -> int:
    """Get next version number for cover letter."""
    latest = await self._get_latest_cover_letter_version(user_id, cv_id, job_id)
    return latest + 1


async def _get_latest_cover_letter_version(
    self,
    user_id: str,
    cv_id: str,
    job_id: str,
) -> int:
    """Get latest version number for cover letter."""
    sk_prefix = f"{COVER_LETTER_ARTIFACT_PREFIX}#{cv_id}#{job_id}#v"
    items = await self._query(pk=user_id, sk_prefix=sk_prefix, limit=1, scan_forward=False)
    if not items:
        return 0
    return int(items[0].get("version", 0))
```

---

## Test Implementation

### test_cover_letter_dal_unit.py

```python
"""Unit tests for cover letter DAL operations."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.models.cover_letter_models import TailoredCoverLetter
from careervp.models.result import ResultCode


class TestCoverLetterDAL:
    """Tests for cover letter DAL operations."""

    @pytest.fixture
    def dal(self):
        """Create DAL instance with mocked DynamoDB."""
        dal = DynamoDalHandler()
        dal._put_item = AsyncMock()
        dal._get_item = AsyncMock()
        dal._delete_item = AsyncMock()
        dal._query = AsyncMock()
        return dal

    @pytest.fixture
    def sample_cover_letter(self):
        """Sample cover letter for testing."""
        return TailoredCoverLetter(
            cover_letter_id="cl_123",
            cv_id="cv_456",
            job_id="job_789",
            user_id="user_abc",
            company_name="TechCorp",
            job_title="Engineer",
            content="Cover letter content",
            word_count=300,
            personalization_score=0.8,
            relevance_score=0.8,
            tone_score=0.8,
            generated_at=datetime.now(),
        )

    @pytest.mark.asyncio
    async def test_save_cover_letter_success(self, dal, sample_cover_letter):
        """Test successful cover letter save."""
        dal._query.return_value = []  # No existing versions

        result = await dal.save_cover_letter_artifact(sample_cover_letter)

        assert result.success is True
        dal._put_item.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_cover_letter_with_ttl(self, dal, sample_cover_letter):
        """Test cover letter save includes TTL."""
        dal._query.return_value = []

        await dal.save_cover_letter_artifact(sample_cover_letter)

        call_args = dal._put_item.call_args[0][0]
        assert "ttl" in call_args
        # TTL should be ~90 days from now
        assert call_args["ttl"] > datetime.now().timestamp()

    @pytest.mark.asyncio
    async def test_get_cover_letter_exists(self, dal):
        """Test get cover letter that exists."""
        dal._query.return_value = [{"version": 1}]
        dal._get_item.return_value = {
            "cover_letter_id": "cl_123",
            "cv_id": "cv_456",
            "job_id": "job_789",
            "company_name": "TechCorp",
            "job_title": "Engineer",
            "content": "Content",
            "word_count": "300",
            "personalization_score": "0.8",
            "relevance_score": "0.8",
            "tone_score": "0.8",
            "created_at": datetime.now().isoformat(),
        }

        result = await dal.get_cover_letter_artifact(
            user_id="user_abc",
            cv_id="cv_456",
            job_id="job_789",
        )

        assert result.success is True
        assert result.data.cover_letter_id == "cl_123"

    @pytest.mark.asyncio
    async def test_get_cover_letter_not_found(self, dal):
        """Test get cover letter that doesn't exist."""
        dal._query.return_value = []

        result = await dal.get_cover_letter_artifact(
            user_id="user_abc",
            cv_id="cv_456",
            job_id="job_789",
        )

        assert result.success is False
        assert result.code == ResultCode.NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_cover_letter(self, dal):
        """Test cover letter deletion."""
        result = await dal.delete_cover_letter_artifact(
            user_id="user_abc",
            cv_id="cv_456",
            job_id="job_789",
            version=1,
        )

        assert result.success is True
        dal._delete_item.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_cover_letters(self, dal):
        """Test listing cover letters by user."""
        dal._query.return_value = [
            {
                "cover_letter_id": "cl_1",
                "cv_id": "cv_1",
                "job_id": "job_1",
                "company_name": "Company1",
                "job_title": "Title1",
                "content": "Content1",
                "word_count": "300",
                "personalization_score": "0.8",
                "relevance_score": "0.8",
                "tone_score": "0.8",
                "created_at": datetime.now().isoformat(),
            }
        ]

        result = await dal.list_cover_letters_by_user(user_id="user_abc")

        assert result.success is True
        assert len(result.data) == 1

    @pytest.mark.asyncio
    async def test_versioning_increments(self, dal, sample_cover_letter):
        """Test version increments on save."""
        dal._query.return_value = [{"version": 2}]  # Existing version 2

        await dal.save_cover_letter_artifact(sample_cover_letter)

        call_args = dal._put_item.call_args[0][0]
        assert call_args["version"] == 3  # Should be version 3
```

---

## Verification Commands

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Format
uv run ruff format careervp/dal/dynamo_dal_handler.py

# Lint
uv run ruff check --fix careervp/dal/

# Type check
uv run mypy careervp/dal/dynamo_dal_handler.py --strict

# Run tests
uv run pytest tests/cover-letter/unit/test_cover_letter_dal_unit.py -v

# Expected: 14 tests PASSED
```

---

## Completion Criteria

- [ ] `save_cover_letter_artifact()` implemented
- [ ] `get_cover_letter_artifact()` implemented
- [ ] `delete_cover_letter_artifact()` implemented
- [ ] `list_cover_letters_by_user()` implemented
- [ ] TTL calculation correct (90 days)
- [ ] Versioning working
- [ ] All 14 tests passing

---

## References

- [dynamo_dal_handler.py](../../../src/backend/careervp/dal/dynamo_dal_handler.py) - Existing DAL
- [COVER_LETTER_DESIGN.md](../../architecture/COVER_LETTER_DESIGN.md) - Storage design
