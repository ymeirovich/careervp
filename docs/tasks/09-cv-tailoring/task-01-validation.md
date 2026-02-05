# Task 9.1: CV Tailoring - Validation Utilities

**Status:** Pending
**Spec Reference:** [docs/specs/04-cv-tailoring.md](../../specs/04-cv-tailoring.md)
**Depends On:** None (Foundation task)
**Blocking:** Task 9.2, Task 9.3, Task 9.6

## Overview

Implement validation utilities for the CV tailoring feature, including file size checks, text length validation, and job description schema validation. These utilities will be used across the entire CV tailoring pipeline to ensure data integrity and prevent resource exhaustion.

## Todo

### Validation Implementation

- [ ] Create `src/backend/careervp/handlers/utils/validation.py`
- [ ] Implement `validate_file_size()` function with configurable limits
- [ ] Implement `validate_text_length()` function with FVS-aware limits
- [ ] Implement `validate_job_description()` function with schema validation
- [ ] Implement `validate_cv_metadata()` function for version checking
- [ ] Implement `ValidationError` exception class with error details
- [ ] Define validation constants (MAX_FILE_SIZE, MAX_TEXT_LENGTH, etc.)

### Test Implementation

- [ ] Create `tests/handlers/utils/test_validation.py`
- [ ] Implement 15-20 test cases covering success and failure paths
- [ ] Test edge cases (boundary conditions, empty inputs, None values)
- [ ] Test error messages and exception handling

### Validation & Formatting

- [ ] Run `uv run ruff format src/backend/careervp/handlers/utils/validation.py`
- [ ] Run `uv run ruff check --fix src/backend/careervp/handlers/utils/`
- [ ] Run `uv run mypy src/backend/careervp/handlers/utils/ --strict`
- [ ] Run `uv run pytest tests/handlers/utils/test_validation.py -v`

### Commit

- [ ] Commit with message: `feat(validation): add CV tailoring input validation utilities`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `src/backend/careervp/handlers/utils/validation.py` | Validation utilities and constants |
| `tests/handlers/utils/test_validation.py` | Unit tests for validation logic |

### Constants Definition

```python
"""
Validation constants for CV tailoring.
Per docs/specs/04-cv-tailoring.md.
"""

# File and text size limits
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB for PDF/DOCX
MAX_TEXT_LENGTH = 50_000  # Characters for extracted text
MAX_JOB_DESCRIPTION_LENGTH = 10_000  # Characters for JD
MAX_CV_SECTIONS = 15  # Max number of work experience/education entries

# Text field limits
MAX_JOB_TITLE_LENGTH = 200
MAX_COMPANY_NAME_LENGTH = 200
MAX_SKILL_NAME_LENGTH = 100
MAX_BULLET_LENGTH = 500

# Validation ranges
MIN_CV_VERSION = 1
MAX_CV_VERSION = 999
MIN_RELEVANCE_SCORE = 0.0
MAX_RELEVANCE_SCORE = 1.0
MIN_JOB_REQUIREMENTS = 1
MAX_JOB_REQUIREMENTS = 50

# Time constraints (seconds)
DEFAULT_REQUEST_TIMEOUT = 60
MAX_TEXT_EXTRACTION_TIME = 30

# Error prefixes for debugging
VALIDATION_ERROR_PREFIX = "VALIDATION_ERROR"
```

### Key Implementation Details

```python
"""
Validation Utilities for CV Tailoring.
Per docs/specs/04-cv-tailoring.md.

Provides input validation for:
- File uploads (size, format)
- Text content (length, structure)
- Job descriptions (schema, requirements)
- CV metadata (versions, sections)

All functions return Result[None] to support error handling pattern.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from careервp.handlers.utils.observability import logger
from careervp.models.result import Result, ResultCode

if TYPE_CHECKING:
    from careervp.models.cv import UserCV
    from careervp.models.job import JobPosting

# Validation constants (see Constants Definition above)


@dataclass
class ValidationError(Exception):
    """Detailed validation error with context."""

    error_code: str
    message: str
    field: str | None = None
    actual_value: str | None = None
    constraint: str | None = None

    def __str__(self) -> str:
        """Format error for logging."""
        parts = [self.message]
        if self.field:
            parts.append(f"Field: {self.field}")
        if self.constraint:
            parts.append(f"Constraint: {self.constraint}")
        if self.actual_value:
            parts.append(f"Actual: {self.actual_value}")
        return " | ".join(parts)


def validate_file_size(file_size_bytes: int) -> Result[None]:
    """
    Validate uploaded file size.

    Args:
        file_size_bytes: Size of file in bytes

    Returns:
        Result[None] with success=True or error details if validation fails.

    Example:
        >>> result = validate_file_size(file_size_bytes=5_000_000)
        >>> assert result.success
        >>> result = validate_file_size(file_size_bytes=10_000_000)
        >>> assert not result.success
        >>> assert "exceeds maximum" in result.error.lower()
    """
    # PSEUDO-CODE:
    # if file_size_bytes <= 0:
    #     return error "Invalid file size: must be positive"
    # if file_size_bytes > MAX_FILE_SIZE_BYTES:
    #     return error "File exceeds maximum size of 5 MB"
    # return success

    pass


def validate_text_length(
    text: str,
    max_length: int = MAX_TEXT_LENGTH,
    field_name: str = "text",
) -> Result[None]:
    """
    Validate extracted text content length.

    Accounts for FVS tiers:
    - IMMUTABLE text (dates, titles) requires high precision
    - FLEXIBLE text (summaries) has relaxed constraints
    - VERIFIABLE text (skills) allows reasonable expansion

    Args:
        text: Text content to validate
        max_length: Maximum allowed characters
        field_name: Field name for error context

    Returns:
        Result[None] with success=True or validation error.

    Example:
        >>> result = validate_text_length("hello", max_length=10)
        >>> assert result.success
        >>> result = validate_text_length("x" * 100, max_length=50, field_name="summary")
        >>> assert not result.success
        >>> assert "summary" in result.error.lower()
    """
    # PSEUDO-CODE:
    # if text is None or empty:
    #     return error "Text cannot be empty"
    # if len(text) > max_length:
    #     return error "{field_name} exceeds limit of {max_length} characters"
    # if contains only whitespace:
    #     return error "{field_name} cannot be only whitespace"
    # return success

    pass


def validate_job_description(job_posting: JobPosting) -> Result[None]:
    """
    Validate job description schema and content.

    Checks:
    - Required fields present (title, description, requirements)
    - Content length within limits
    - At least MIN_JOB_REQUIREMENTS
    - No obvious invalid data

    Args:
        job_posting: JobPosting model to validate

    Returns:
        Result[None] with success=True or validation errors.

    Example:
        >>> job = JobPosting(
        ...     title="Senior Engineer",
        ...     description="We seek...",
        ...     requirements=["Python", "AWS"],
        ... )
        >>> result = validate_job_description(job)
        >>> assert result.success
    """
    # PSEUDO-CODE:
    # if job_posting.title is missing or empty:
    #     return error "Job title is required"
    # if len(job_posting.title) > MAX_JOB_TITLE_LENGTH:
    #     return error "Job title exceeds limit"
    # if job_posting.description is missing or empty:
    #     return error "Job description is required"
    # if len(job_posting.description) > MAX_JOB_DESCRIPTION_LENGTH:
    #     return error "Job description exceeds limit"
    # if not job_posting.requirements or len(requirements) < MIN_JOB_REQUIREMENTS:
    #     return error "At least {MIN_JOB_REQUIREMENTS} requirements required"
    # if len(requirements) > MAX_JOB_REQUIREMENTS:
    #     return error "Too many requirements (max {MAX_JOB_REQUIREMENTS})"
    # for each requirement:
    #     if len(requirement) > MAX_SKILL_NAME_LENGTH:
    #         return error "Requirement too long: {requirement}"
    # return success

    pass


def validate_cv_metadata(user_cv: UserCV, cv_version: int) -> Result[None]:
    """
    Validate CV metadata for tailoring.

    Checks:
    - CV version matches existing versions
    - CV has required sections (not empty)
    - No corrupted data

    Args:
        user_cv: User's CV to validate
        cv_version: Requested CV version

    Returns:
        Result[None] with success=True or validation errors.

    Example:
        >>> cv = UserCV(version=1, work_experience=[...], skills=[...])
        >>> result = validate_cv_metadata(cv, cv_version=1)
        >>> assert result.success
        >>> result = validate_cv_metadata(cv, cv_version=5)
        >>> assert not result.success
    """
    # PSEUDO-CODE:
    # if user_cv is None:
    #     return error "CV not found"
    # if cv_version < MIN_CV_VERSION or cv_version > MAX_CV_VERSION:
    #     return error "Invalid CV version"
    # if user_cv.version != cv_version:
    #     return error "CV version mismatch"
    # if not user_cv.contact_info:
    #     return error "CV missing contact information"
    # if not user_cv.work_experience and not user_cv.education:
    #     return error "CV must have work experience or education"
    # if len(user_cv.work_experience) > MAX_CV_SECTIONS:
    #     return error "Too many work experience entries"
    # if len(user_cv.education) > MAX_CV_SECTIONS:
    #     return error "Too many education entries"
    # return success

    pass


def validate_bullet_point(bullet: str, context: str = "work_experience") -> Result[None]:
    """
    Validate a single bullet point.

    Checks:
    - Not empty
    - Reasonable length
    - No obvious invalid patterns

    Args:
        bullet: Bullet point text
        context: Context for error messages (e.g., "work_experience")

    Returns:
        Result[None] with success or validation error.

    Example:
        >>> result = validate_bullet_point("Managed team of 5 engineers")
        >>> assert result.success
        >>> result = validate_bullet_point("")
        >>> assert not result.success
    """
    # PSEUDO-CODE:
    # if bullet is empty or whitespace-only:
    #     return error "{context} bullet cannot be empty"
    # if len(bullet) > MAX_BULLET_LENGTH:
    #     return error "{context} bullet exceeds {MAX_BULLET_LENGTH} characters"
    # if len(bullet) < 10:
    #     return warning "{context} bullet seems very short"
    # return success

    pass


def validate_relevance_score(score: float) -> Result[None]:
    """
    Validate skill relevance score.

    Args:
        score: Relevance score (should be 0.0-1.0)

    Returns:
        Result[None] with success or validation error.

    Example:
        >>> assert validate_relevance_score(0.75).success
        >>> assert not validate_relevance_score(1.5).success
    """
    # PSEUDO-CODE:
    # if score < MIN_RELEVANCE_SCORE or score > MAX_RELEVANCE_SCORE:
    #     return error f"Relevance score must be between {MIN} and {MAX}, got {score}"
    # return success

    pass


def validate_section_exists(cv: UserCV, section: str) -> Result[None]:
    """
    Validate that a CV section exists and is not empty.

    Args:
        cv: User CV
        section: Section name ("work_experience", "skills", "education", etc.)

    Returns:
        Result[None] with success or validation error.

    Example:
        >>> cv = UserCV(work_experience=[...], skills=[...])
        >>> assert validate_section_exists(cv, "work_experience").success
        >>> assert not validate_section_exists(cv, "awards").success
    """
    # PSEUDO-CODE:
    # if section not in valid sections list:
    #     return error f"Invalid section: {section}"
    # section_data = getattr(cv, section, None)
    # if section_data is None or (isinstance(section_data, list) and len(section_data) == 0):
    #     return error f"Section {section} is empty or missing"
    # return success

    pass


def sanitize_text(text: str) -> str:
    """
    Sanitize text for safe processing.

    Removes:
    - Leading/trailing whitespace
    - Multiple consecutive spaces
    - Invalid Unicode characters
    - Suspicious patterns

    Args:
        text: Raw text to sanitize

    Returns:
        Cleaned text safe for processing.

    Example:
        >>> result = sanitize_text("  hello   world  ")
        >>> assert result == "hello world"
    """
    # PSEUDO-CODE:
    # text = text.strip()  # Remove leading/trailing whitespace
    # text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with single space
    # text = text.encode('utf-8', errors='ignore').decode('utf-8')  # Remove invalid Unicode
    # return text

    pass
```

### Test Implementation Structure

```python
"""
Tests for CV Tailoring Validation Utilities.
Per tests/handlers/utils/test_validation.py.

Test categories:
- File size validation (5 tests)
- Text length validation (5 tests)
- Job description validation (5 tests)
- CV metadata validation (5 tests)
- Edge cases and error handling (5 tests)

Total: 15-20 tests covering all validation functions.
"""

import pytest

from careervp.handlers.utils.validation import (
    ValidationError,
    validate_file_size,
    validate_text_length,
    validate_job_description,
    validate_cv_metadata,
    validate_bullet_point,
    validate_relevance_score,
    sanitize_text,
)
from careervp.models.result import ResultCode


class TestFileValidation:
    """Test file size validation."""

    def test_validate_file_size_valid(self):
        """Valid file size passes validation."""
        # PSEUDO-CODE:
        # result = validate_file_size(1_000_000)  # 1 MB
        # assert result.success
        pass

    def test_validate_file_size_zero(self):
        """Zero file size fails validation."""
        # PSEUDO-CODE:
        # result = validate_file_size(0)
        # assert not result.success
        # assert "invalid" in result.error.lower() or "positive" in result.error.lower()
        pass

    def test_validate_file_size_negative(self):
        """Negative file size fails validation."""
        # PSEUDO-CODE:
        # result = validate_file_size(-100)
        # assert not result.success
        pass

    def test_validate_file_size_at_limit(self):
        """File size at maximum limit passes."""
        # PSEUDO-CODE:
        # result = validate_file_size(5_242_880)  # Exactly 5 MB
        # assert result.success
        pass

    def test_validate_file_size_exceeds_limit(self):
        """File size exceeding limit fails."""
        # PSEUDO-CODE:
        # result = validate_file_size(10_485_760)  # 10 MB
        # assert not result.success
        # assert "exceeds" in result.error.lower()
        pass


class TestTextValidation:
    """Test text length validation."""

    def test_validate_text_length_valid(self):
        """Valid text length passes."""
        # PSEUDO-CODE:
        # result = validate_text_length("hello world")
        # assert result.success
        pass

    def test_validate_text_length_empty(self):
        """Empty text fails."""
        # PSEUDO-CODE:
        # result = validate_text_length("")
        # assert not result.success
        pass

    def test_validate_text_length_whitespace_only(self):
        """Whitespace-only text fails."""
        # PSEUDO-CODE:
        # result = validate_text_length("   \n  \t  ")
        # assert not result.success
        pass

    def test_validate_text_length_exceeds_max(self):
        """Text exceeding max length fails."""
        # PSEUDO-CODE:
        # long_text = "x" * 100_000
        # result = validate_text_length(long_text, max_length=50_000)
        # assert not result.success
        pass

    def test_validate_text_length_at_limit(self):
        """Text at maximum length passes."""
        # PSEUDO-CODE:
        # text = "x" * 50_000
        # result = validate_text_length(text, max_length=50_000)
        # assert result.success
        pass


class TestJobDescriptionValidation:
    """Test job description validation."""

    def test_validate_job_description_valid(self):
        """Valid job posting passes validation."""
        # PSEUDO-CODE:
        # job = JobPosting(
        #     title="Senior Engineer",
        #     description="We are seeking...",
        #     requirements=["Python", "AWS", "Docker"],
        # )
        # result = validate_job_description(job)
        # assert result.success
        pass

    def test_validate_job_description_missing_title(self):
        """Job without title fails."""
        # PSEUDO-CODE:
        # job = JobPosting(title="", description="...", requirements=[...])
        # result = validate_job_description(job)
        # assert not result.success
        pass

    def test_validate_job_description_missing_requirements(self):
        """Job without requirements fails."""
        # PSEUDO-CODE:
        # job = JobPosting(
        #     title="Engineer",
        #     description="...",
        #     requirements=[],
        # )
        # result = validate_job_description(job)
        # assert not result.success
        pass

    def test_validate_job_description_too_many_requirements(self):
        """Job with too many requirements fails."""
        # PSEUDO-CODE:
        # job = JobPosting(
        #     title="Engineer",
        #     description="...",
        #     requirements=[f"skill_{i}" for i in range(100)],
        # )
        # result = validate_job_description(job)
        # assert not result.success
        pass

    def test_validate_job_description_exceeds_length(self):
        """Job description exceeding max length fails."""
        # PSEUDO-CODE:
        # job = JobPosting(
        #     title="Engineer",
        #     description="x" * 50_000,
        #     requirements=["Python"],
        # )
        # result = validate_job_description(job)
        # assert not result.success
        pass


class TestCVMetadataValidation:
    """Test CV metadata validation."""

    def test_validate_cv_metadata_valid(self):
        """Valid CV metadata passes."""
        # PSEUDO-CODE:
        # cv = UserCV(
        #     version=1,
        #     contact_info={...},
        #     work_experience=[...],
        # )
        # result = validate_cv_metadata(cv, cv_version=1)
        # assert result.success
        pass

    def test_validate_cv_metadata_version_mismatch(self):
        """CV version mismatch fails."""
        # PSEUDO-CODE:
        # cv = UserCV(version=1, ...)
        # result = validate_cv_metadata(cv, cv_version=5)
        # assert not result.success
        pass

    def test_validate_cv_metadata_no_contact_info(self):
        """CV without contact info fails."""
        # PSEUDO-CODE:
        # cv = UserCV(
        #     version=1,
        #     contact_info=None,
        #     work_experience=[...],
        # )
        # result = validate_cv_metadata(cv, cv_version=1)
        # assert not result.success
        pass

    def test_validate_cv_metadata_empty_sections(self):
        """CV with no work or education fails."""
        # PSEUDO-CODE:
        # cv = UserCV(
        #     version=1,
        #     contact_info={...},
        #     work_experience=[],
        #     education=[],
        # )
        # result = validate_cv_metadata(cv, cv_version=1)
        # assert not result.success
        pass

    def test_validate_cv_metadata_too_many_sections(self):
        """CV with too many entries fails."""
        # PSEUDO-CODE:
        # cv = UserCV(
        #     version=1,
        #     contact_info={...},
        #     work_experience=[MockExperience() for _ in range(50)],
        # )
        # result = validate_cv_metadata(cv, cv_version=1)
        # assert not result.success
        pass


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_validate_bullet_point_valid(self):
        """Valid bullet point passes."""
        # PSEUDO-CODE:
        # result = validate_bullet_point("Managed team of 5 engineers")
        # assert result.success
        pass

    def test_validate_bullet_point_too_short(self):
        """Very short bullet fails."""
        # PSEUDO-CODE:
        # result = validate_bullet_point("Coded stuff")
        # assert not result.success
        pass

    def test_validate_relevance_score_valid(self):
        """Valid relevance score passes."""
        # PSEUDO-CODE:
        # assert validate_relevance_score(0.0).success
        # assert validate_relevance_score(0.5).success
        # assert validate_relevance_score(1.0).success
        pass

    def test_validate_relevance_score_invalid(self):
        """Invalid relevance scores fail."""
        # PSEUDO-CODE:
        # assert not validate_relevance_score(-0.1).success
        # assert not validate_relevance_score(1.5).success
        pass

    def test_sanitize_text_removes_whitespace(self):
        """Sanitize removes extra whitespace."""
        # PSEUDO-CODE:
        # result = sanitize_text("  hello   world  ")
        # assert result == "hello world"
        pass
```

### Verification Commands

Run these commands to verify implementation:

```bash
# Format code
uv run ruff format src/backend/careervp/handlers/utils/validation.py

# Check for style issues
uv run ruff check --fix src/backend/careervp/handlers/utils/

# Type check with strict mode
uv run mypy src/backend/careervp/handlers/utils/ --strict

# Run unit tests
uv run pytest tests/handlers/utils/test_validation.py -v

# Run tests with coverage
uv run pytest tests/handlers/utils/test_validation.py --cov=careervp.handlers.utils.validation

# Expected output:
# ===== test session starts =====
# tests/handlers/utils/test_validation.py::TestFileValidation::test_validate_file_size_valid PASSED
# tests/handlers/utils/test_validation.py::TestFileValidation::test_validate_file_size_zero PASSED
# ... [15-20 total tests]
# ===== 15-20 passed in X.XXs =====
```

### Expected Test Results

```
tests/handlers/utils/test_validation.py::TestFileValidation PASSED (5 tests)
tests/handlers/utils/test_validation.py::TestTextValidation PASSED (5 tests)
tests/handlers/utils/test_validation.py::TestJobDescriptionValidation PASSED (5 tests)
tests/handlers/utils/test_validation.py::TestCVMetadataValidation PASSED (5 tests)
tests/handlers/utils/test_validation.py::TestEdgeCases PASSED (5 tests)

Total: 15-20 tests passing
Type checking: 0 errors, 0 warnings
Code style: 0 violations
Coverage: >90% for validation.py
```

### Zero-Hallucination Checklist

- [ ] All validation functions return `Result[None]` following pattern
- [ ] Constants match specifications in `docs/specs/04-cv-tailoring.md`
- [ ] File size constants correct (5 MB = 5,242,880 bytes)
- [ ] Text length limits enforced consistently
- [ ] Job description validation checks all required fields
- [ ] CV metadata validation preserves FVS tier rules
- [ ] Error messages are clear and actionable
- [ ] Test coverage >90% for validation logic
- [ ] No external API calls in validation layer
- [ ] All tests pass with 0 warnings/errors

### Acceptance Criteria

- [ ] `validate_file_size()` correctly rejects files >5 MB
- [ ] `validate_text_length()` enforces MAX_TEXT_LENGTH
- [ ] `validate_job_description()` requires all mandatory fields
- [ ] `validate_cv_metadata()` checks version consistency
- [ ] All validation functions return Result[None]
- [ ] Test suite covers success and failure paths
- [ ] Edge cases handled (empty, None, boundary values)
- [ ] Error messages include context (field name, constraint, actual value)
- [ ] 15-20 unit tests all passing
- [ ] Type checking passes with `mypy --strict`

---

### Verification & Compliance

1. Run `python src/backend/scripts/validate_naming.py --path src/backend/careervp/handlers/utils --strict`
2. Run `uv run ruff format . && uv run ruff check --fix . && uv run mypy --strict .`
3. Run `uv run pytest tests/handlers/utils/test_validation.py -v --cov`
4. If any validation is missing or test fails, report a **BLOCKING ISSUE** and exit.
