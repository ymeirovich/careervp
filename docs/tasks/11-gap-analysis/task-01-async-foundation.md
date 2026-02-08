# Task 01: Async Foundation - Validation & Base Handler

## Overview

Create reusable foundation for async task handlers: validation utilities and abstract base class for async processing.

**Files to create:**
- `src/backend/careervp/handlers/utils/validation.py`
- `src/backend/careervp/handlers/utils/async_task.py` (optional for Phase 11, but designed for future)

**Dependencies:** None (foundation layer)
**Estimated time:** 2 hours

---

## Part A: Validation Utilities

### File: `src/backend/careervp/handlers/utils/validation.py`

**Purpose:** Security validation for file uploads and text inputs.

**Unit Tests:** `tests/gap-analysis/unit/test_validation.py`

### Implementation

```python
"""
Security validation utilities for CareerVP handlers.
Per docs/architecture/VPR_ASYNC_DESIGN.md - Rule 2 (Security).
"""

from typing import Annotated
from pydantic import BaseModel, Field, field_validator

# Security constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB (per Class Topology Analysis)
MAX_TEXT_LENGTH = 1_000_000        # 1M characters


def validate_file_size(content: bytes) -> None:
    """
    Validate file size does not exceed 10MB limit.

    Args:
        content: File content as bytes

    Raises:
        ValueError: If content exceeds MAX_FILE_SIZE

    Examples:
        >>> validate_file_size(b'hello')  # OK
        >>> validate_file_size(b'a' * (11 * 1024 * 1024))  # Raises ValueError
    """
    if len(content) > MAX_FILE_SIZE:
        raise ValueError(
            f"File size {len(content)} bytes exceeds maximum {MAX_FILE_SIZE} bytes (10MB)"
        )


def validate_text_length(text: str) -> None:
    """
    Validate text length for LLM inputs.

    Args:
        text: Text content

    Raises:
        ValueError: If text exceeds MAX_TEXT_LENGTH

    Examples:
        >>> validate_text_length("Hello world")  # OK
        >>> validate_text_length('a' * 2_000_000)  # Raises ValueError
    """
    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError(
            f"Text length {len(text)} exceeds maximum {MAX_TEXT_LENGTH} characters"
        )
```

### Verification Commands

```bash
cd src/backend

# Format
uv run ruff format careervp/handlers/utils/validation.py

# Lint
uv run ruff check careervp/handlers/utils/validation.py --fix

# Type check
uv run mypy careervp/handlers/utils/validation.py --strict

# Run unit tests
uv run pytest tests/gap-analysis/unit/test_validation.py -v --tb=short

# Expected output: All tests PASS
```

---

## Part B: Async Task Base Handler (Optional for Phase 11)

### File: `src/backend/careervp/handlers/utils/async_task.py`

**Purpose:** Abstract base class for async handlers (for future use, not required for Phase 11 synchronous gap analysis).

**Note:** Phase 11 Gap Analysis will be **synchronous** (like existing VPR handler), not async. This file is designed for future phases when async processing with SQS is needed.

### Implementation (Future Reference)

```python
"""
Reusable async task handler foundation.
Per docs/architecture/VPR_ASYNC_DESIGN.md.

NOTE: Not used in Phase 11 (Gap Analysis is synchronous).
This is designed for future async features.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from careervp.dal.db_handler import DalHandler
from careervp.models import Result

T = TypeVar('T')


class AsyncTaskHandler(ABC, Generic[T]):
    """
    Abstract base for async task handlers following SQS + Polling pattern.

    Subclasses must implement:
    - validate_request(): Validate and parse request data
    - process(): Execute feature-specific logic (LLM calls)

    Usage:
        class GapAnalysisWorker(AsyncTaskHandler[GapAnalysisRequest]):
            def validate_request(self, request_data: dict) -> Result[GapAnalysisRequest]:
                # Validation logic

            async def process(self, job_id: str, request: GapAnalysisRequest) -> Result[dict]:
                # Processing logic
    """

    def __init__(self, dal: DalHandler, queue_url: str, results_bucket: str):
        """
        Args:
            dal: Data access layer for job tracking
            queue_url: SQS queue URL for job submission
            results_bucket: S3 bucket name for storing results
        """
        self.dal = dal
        self.queue_url = queue_url
        self.results_bucket = results_bucket

    @abstractmethod
    def validate_request(self, request_data: dict) -> Result[T]:
        """
        Validate and parse request data using Pydantic models.

        Returns:
            Result[T] with parsed request object or validation error
        """
        pass

    @abstractmethod
    async def process(self, job_id: str, request: T) -> Result[dict]:
        """
        Execute feature-specific processing logic.

        Args:
            job_id: Unique job identifier
            request: Parsed and validated request object

        Returns:
            Result[dict] with processing output or error
        """
        pass
```

**Note:** Since Gap Analysis is synchronous in Phase 11, this file is **optional**. Create it only if you want to establish the pattern for future phases.

---

## Acceptance Criteria

### Part A: Validation (Required)

- [ ] `validation.py` created with `validate_file_size()` and `validate_text_length()`
- [ ] `MAX_FILE_SIZE = 10 * 1024 * 1024` (10MB)
- [ ] `MAX_TEXT_LENGTH = 1_000_000` (1M characters)
- [ ] File size validation raises `ValueError` with clear message
- [ ] Text length validation raises `ValueError` with clear message
- [ ] Error messages include actual size/length and limit
- [ ] All tests in `test_validation.py` pass
- [ ] `ruff format` passes
- [ ] `ruff check` passes
- [ ] `mypy --strict` passes

### Part B: Async Base Handler (Optional)

- [ ] `async_task.py` created with `AsyncTaskHandler` abstract class
- [ ] Generic type parameter `T` for request type
- [ ] Abstract methods: `validate_request()`, `process()`
- [ ] Constructor accepts `dal`, `queue_url`, `results_bucket`
- [ ] Docstrings explain usage pattern

---

## Testing Strategy

### Unit Tests Created

✅ `tests/gap-analysis/unit/test_validation.py` - 18 tests covering:
- File size under/at/over limit
- Empty files
- Text length validation
- Unicode handling
- Error message clarity

### Test Execution

```bash
cd src/backend
uv run pytest tests/gap-analysis/unit/test_validation.py -v

# Expected: 18 passed
```

---

## Implementation Notes

1. **Security First:** Validation must happen BEFORE any processing
2. **Clear Errors:** Error messages must include actual values and limits
3. **Type Safety:** Use strict mypy type checking
4. **Constants:** Define limits as module-level constants (easy to adjust)
5. **No Dependencies:** Validation should not depend on external services

---

## References

- **Architecture:** [VPR_ASYNC_DESIGN.md](../../architecture/VPR_ASYNC_DESIGN.md)
- **Class Topology:** Rule 2 - 10MB file size limit
- **Test File:** [test_validation.py](../../../tests/gap-analysis/unit/test_validation.py)

---

## Commit Message

```bash
git add src/backend/careervp/handlers/utils/validation.py
git commit -m "feat(gap-analysis): add validation utilities (10MB limit)

- Implement validate_file_size() with 10MB limit
- Implement validate_text_length() with 1M character limit
- Add security constants (MAX_FILE_SIZE, MAX_TEXT_LENGTH)
- All validation tests pass (18/18)

Per Class Topology Analysis Rule 2.
Per docs/architecture/VPR_ASYNC_DESIGN.md.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```
