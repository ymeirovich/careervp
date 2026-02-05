# Task 10.1: Cover Letter - Validation Utilities

**Status:** Pending
**Spec Reference:** [docs/specs/cover-letter/COVER_LETTER_SPEC.md](../../specs/cover-letter/COVER_LETTER_SPEC.md)
**Depends On:** None (Foundation task)
**Blocking:** Task 10.2, Task 10.3, Task 10.5, Task 10.6, Task 10.8

## Overview

Implement validation utilities for the cover letter generation feature, including company name validation, job title validation, word count target validation, tone validation, and emphasis areas validation. These utilities will be used across the entire cover letter pipeline to ensure data integrity, prevent XSS attacks, and enforce security constraints from the API specification.

The validation layer is the foundation for all subsequent tasks—it must be rock-solid before any business logic is implemented.

## Todo

### Validation Implementation

- [ ] Create `src/backend/careervp/handlers/utils/validation.py` (if not exists, extend existing)
- [ ] Implement `validate_company_name()` function with XSS prevention
- [ ] Implement `validate_job_title()` function with XSS prevention
- [ ] Implement `validate_word_count_target()` function with range validation
- [ ] Implement `validate_tone()` function with enum validation
- [ ] Implement `validate_emphasis_areas()` function with list validation
- [ ] Implement `validate_job_description()` function with optional validation
- [ ] Implement `CoverLetterValidationError` exception class with error details
- [ ] Define validation constants (MAX_COMPANY_NAME_LENGTH, MAX_JOB_TITLE_LENGTH, etc.)

### Test Implementation

- [ ] Create `tests/cover-letter/unit/test_validation.py`
- [ ] Implement 18-20 test cases covering success and failure paths
- [ ] Test edge cases (boundary conditions, empty inputs, None values)
- [ ] Test XSS prevention (script tags, HTML entities, special characters)
- [ ] Test error messages and exception handling

### Validation & Formatting

- [ ] Run `uv run ruff format src/backend/careervp/handlers/utils/validation.py`
- [ ] Run `uv run ruff check --fix src/backend/careervp/handlers/`
- [ ] Run `uv run mypy src/backend/careervp/handlers/ --strict`
- [ ] Run `uv run pytest tests/cover-letter/unit/test_validation.py -v`

### Commit

- [ ] Commit with message: `feat(validation): add cover letter input validation utilities`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `src/backend/careervp/handlers/utils/validation.py` | Cover letter validation utilities and constants |
| `tests/cover-letter/unit/test_validation.py` | Unit tests for validation logic |

### Constants Definition

The validation layer uses industry-standard constraints derived from the API specification and security best practices. All constants are centralized in the validation module for easy maintenance.

```python
"""
Validation constants for Cover Letter Generation.
Per docs/specs/cover-letter/COVER_LETTER_SPEC.md.
"""

# Company name and job title constraints (from API spec)
# These fields are used for FVS validation, so they must be precise
MIN_COMPANY_NAME_LENGTH = 1
MAX_COMPANY_NAME_LENGTH = 255  # API spec: 1-255 chars

MIN_JOB_TITLE_LENGTH = 1
MAX_JOB_TITLE_LENGTH = 255  # API spec: 1-255 chars

# Word count preferences (from API spec)
# Range: 200-500 words, default 300
MIN_WORD_COUNT_TARGET = 200
MAX_WORD_COUNT_TARGET = 500
DEFAULT_WORD_COUNT_TARGET = 300

# Job description constraint (from API spec)
# Optional field, but if provided, must not exceed this
MAX_JOB_DESCRIPTION_LENGTH = 50_000  # 50k characters max

# Tone options (from API spec CoverLetterPreferences.tone)
VALID_TONES = ["professional", "enthusiastic", "technical"]
DEFAULT_TONE = "professional"

# Emphasis areas constraint
# No hard limit in spec, but enforce reasonable list size
MAX_EMPHASIS_AREAS = 10
MAX_EMPHASIS_AREA_LENGTH = 100

# Error context prefixes
VALIDATION_ERROR_PREFIX = "VALIDATION_ERROR_COVER_LETTER"

# Unsafe patterns for XSS prevention
UNSAFE_PATTERNS = [
    "<script",
    "javascript:",
    "onerror",
    "onload",
    "onclick",
    "onmouseover",
]
```

### Key Implementation Details

This validation layer follows the "fail fast" principle: invalid inputs are caught immediately before any expensive operations (LLM calls, database queries) are performed. Each validation function is atomic and can be tested independently.

The module provides:

1. **Atomic validators** - Each validates a single field with a specific constraint
2. **Comprehensive error context** - Error messages include field name, actual value, and constraint violated
3. **XSS prevention** - Detects and blocks common injection patterns
4. **Type safety** - All functions include full type hints for mypy --strict

```python
"""
Validation Utilities for Cover Letter Generation.
Per docs/specs/cover-letter/COVER_LETTER_SPEC.md.

Provides input validation for:
- Company name (1-255 chars, no XSS patterns)
- Job title (1-255 chars, no XSS patterns)
- Word count target (200-500 range)
- Tone preference (professional/enthusiastic/technical)
- Emphasis areas (optional list of strings)
- Job description (optional, up to 50k chars)

All functions raise CoverLetterValidationError on validation failure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from careervp.handlers.utils.observability import logger

if TYPE_CHECKING:
    pass

# Validation constants (see Constants Definition above)


@dataclass
class CoverLetterValidationError(Exception):
    """Detailed validation error for cover letter input."""

    error_code: str
    message: str
    field: str | None = None
    actual_value: str | None = None
    constraint: str | None = None

    def __str__(self) -> str:
        """Format error for logging and client response."""
        parts = [self.message]
        if self.field:
            parts.append(f"Field: {self.field}")
        if self.constraint:
            parts.append(f"Constraint: {self.constraint}")
        if self.actual_value is not None:
            # Truncate long values to prevent log spam
            actual_display = (
                self.actual_value[:50] + "..."
                if len(self.actual_value) > 50
                else self.actual_value
            )
            parts.append(f"Actual: {actual_display}")
        return " | ".join(parts)


def _contains_unsafe_patterns(text: str) -> bool:
    """
    Check if text contains common XSS/injection patterns.

    PSEUDO-CODE:
    # for each pattern in UNSAFE_PATTERNS:
    #     if pattern in text.lower():
    #         return True
    # return False

    Args:
        text: Text to scan for unsafe patterns

    Returns:
        True if unsafe pattern found, False otherwise
    """
    # Implementation:
    text_lower = text.lower()
    for pattern in UNSAFE_PATTERNS:
        if pattern in text_lower:
            return True
    return False


def validate_company_name(company_name: str) -> None:
    """
    Validate company name constraints.

    Rules:
    - Required (cannot be empty or whitespace-only)
    - Min length: 1 character
    - Max length: 255 characters
    - No script tags or XSS patterns (security)
    - No leading/trailing whitespace after strip

    Raises:
        CoverLetterValidationError: If validation fails with detailed context

    Example:
        >>> validate_company_name("TechCorp Inc")  # Valid: passes
        >>> validate_company_name("")  # Invalid: raises error "Company name is required"
        >>> validate_company_name("<script>alert</script>")  # Invalid: raises error "contains invalid characters"
        >>> validate_company_name("A" * 256)  # Invalid: raises error "exceeds 255 characters"

    PSEUDO-CODE:
    # if company_name is None or not company_name.strip():
    #     raise CoverLetterValidationError(
    #         error_code="INVALID_COMPANY_NAME",
    #         message="Company name is required",
    #         field="company_name",
    #     )
    # if len(company_name) > MAX_COMPANY_NAME_LENGTH:
    #     raise CoverLetterValidationError(
    #         error_code="INVALID_COMPANY_NAME",
    #         message=f"Company name exceeds {MAX_COMPANY_NAME_LENGTH} characters",
    #         field="company_name",
    #         actual_value=company_name,
    #         constraint=f"max_length={MAX_COMPANY_NAME_LENGTH}",
    #     )
    # if _contains_unsafe_patterns(company_name):
    #     raise CoverLetterValidationError(
    #         error_code="INVALID_COMPANY_NAME",
    #         message="Company name contains invalid characters",
    #         field="company_name",
    #     )
    # # No exception raised = validation passed
    """

    # Implementation:
    if not company_name or not company_name.strip():
        raise CoverLetterValidationError(
            error_code="INVALID_COMPANY_NAME",
            message="Company name is required",
            field="company_name",
        )

    if len(company_name) > MAX_COMPANY_NAME_LENGTH:
        raise CoverLetterValidationError(
            error_code="INVALID_COMPANY_NAME",
            message=f"Company name exceeds {MAX_COMPANY_NAME_LENGTH} characters",
            field="company_name",
            actual_value=company_name,
            constraint=f"max_length={MAX_COMPANY_NAME_LENGTH}",
        )

    if _contains_unsafe_patterns(company_name):
        raise CoverLetterValidationError(
            error_code="INVALID_COMPANY_NAME",
            message="Company name contains invalid characters",
            field="company_name",
        )

    logger.info(
        "Company name validation passed",
        extra={"company_name_length": len(company_name)},
    )


def validate_job_title(job_title: str) -> None:
    """
    Validate job title constraints.

    Rules:
    - Required (cannot be empty or whitespace-only)
    - Min length: 1 character
    - Max length: 255 characters
    - No script tags or XSS patterns (security)
    - No leading/trailing whitespace after strip

    Raises:
        CoverLetterValidationError: If validation fails

    Example:
        >>> validate_job_title("Senior Python Engineer")  # Valid: passes
        >>> validate_job_title("")  # Invalid: raises error
        >>> validate_job_title("onerror='alert'")  # Invalid: XSS prevention
        >>> validate_job_title("J" * 256)  # Invalid: too long

    PSEUDO-CODE:
    # if job_title is None or not job_title.strip():
    #     raise CoverLetterValidationError(...)
    # if len(job_title) > MAX_JOB_TITLE_LENGTH:
    #     raise CoverLetterValidationError(...)
    # if _contains_unsafe_patterns(job_title):
    #     raise CoverLetterValidationError(...)
    """

    # Implementation:
    if not job_title or not job_title.strip():
        raise CoverLetterValidationError(
            error_code="INVALID_JOB_TITLE",
            message="Job title is required",
            field="job_title",
        )

    if len(job_title) > MAX_JOB_TITLE_LENGTH:
        raise CoverLetterValidationError(
            error_code="INVALID_JOB_TITLE",
            message=f"Job title exceeds {MAX_JOB_TITLE_LENGTH} characters",
            field="job_title",
            actual_value=job_title,
            constraint=f"max_length={MAX_JOB_TITLE_LENGTH}",
        )

    if _contains_unsafe_patterns(job_title):
        raise CoverLetterValidationError(
            error_code="INVALID_JOB_TITLE",
            message="Job title contains invalid characters",
            field="job_title",
        )

    logger.info(
        "Job title validation passed",
        extra={"job_title_length": len(job_title)},
    )


def validate_word_count_target(word_count: int) -> None:
    """
    Validate word count target for cover letter.

    Rules:
    - Minimum: 200 words (ensures substantive letter)
    - Maximum: 500 words (prevents excessive length)
    - Must be integer type
    - Default: 300 words (used if not specified)

    Raises:
        CoverLetterValidationError: If validation fails

    Example:
        >>> validate_word_count_target(300)  # Valid: passes
        >>> validate_word_count_target(150)  # Invalid: below minimum
        >>> validate_word_count_target(600)  # Invalid: exceeds maximum
        >>> validate_word_count_target(200)  # Valid: at minimum boundary

    PSEUDO-CODE:
    # if word_count < MIN_WORD_COUNT_TARGET:
    #     raise CoverLetterValidationError(
    #         error_code="INVALID_WORD_COUNT",
    #         message=f"Word count target must be at least {MIN_WORD_COUNT_TARGET}",
    #         field="word_count_target",
    #         actual_value=str(word_count),
    #         constraint=f"min={MIN_WORD_COUNT_TARGET}",
    #     )
    # if word_count > MAX_WORD_COUNT_TARGET:
    #     raise CoverLetterValidationError(
    #         error_code="INVALID_WORD_COUNT",
    #         message=f"Word count target cannot exceed {MAX_WORD_COUNT_TARGET}",
    #         field="word_count_target",
    #         actual_value=str(word_count),
    #         constraint=f"max={MAX_WORD_COUNT_TARGET}",
    #     )
    """

    # Implementation:
    if word_count < MIN_WORD_COUNT_TARGET:
        raise CoverLetterValidationError(
            error_code="INVALID_WORD_COUNT",
            message=f"Word count target must be at least {MIN_WORD_COUNT_TARGET}",
            field="word_count_target",
            actual_value=str(word_count),
            constraint=f"min={MIN_WORD_COUNT_TARGET}",
        )

    if word_count > MAX_WORD_COUNT_TARGET:
        raise CoverLetterValidationError(
            error_code="INVALID_WORD_COUNT",
            message=f"Word count target cannot exceed {MAX_WORD_COUNT_TARGET}",
            field="word_count_target",
            actual_value=str(word_count),
            constraint=f"max={MAX_WORD_COUNT_TARGET}",
        )

    logger.info(
        "Word count target validation passed",
        extra={"word_count_target": word_count},
    )


def validate_tone(tone: str) -> None:
    """
    Validate tone preference for cover letter.

    Rules:
    - Must be one of: "professional", "enthusiastic", "technical"
    - Case-insensitive matching not supported (must be exact lowercase)
    - Required for preference object

    Raises:
        CoverLetterValidationError: If validation fails

    Example:
        >>> validate_tone("professional")  # Valid: passes
        >>> validate_tone("enthusiastic")  # Valid: passes
        >>> validate_tone("technical")  # Valid: passes
        >>> validate_tone("casual")  # Invalid: not in allowed list
        >>> validate_tone("PROFESSIONAL")  # Invalid: must be lowercase

    PSEUDO-CODE:
    # if tone not in VALID_TONES:
    #     raise CoverLetterValidationError(
    #         error_code="INVALID_TONE",
    #         message=f"Invalid tone: {tone}. Must be one of {VALID_TONES}",
    #         field="tone",
    #         actual_value=tone,
    #         constraint=f"enum={VALID_TONES}",
    #     )
    """

    # Implementation:
    if tone not in VALID_TONES:
        raise CoverLetterValidationError(
            error_code="INVALID_TONE",
            message=f"Invalid tone: {tone}. Must be one of {VALID_TONES}",
            field="tone",
            actual_value=tone,
            constraint=f"enum={VALID_TONES}",
        )

    logger.info("Tone validation passed", extra={"tone": tone})


def validate_emphasis_areas(emphasis_areas: Optional[list[str]]) -> None:
    """
    Validate emphasis areas list for cover letter.

    Rules:
    - Optional field (can be None or empty list)
    - If provided, must be a list of strings
    - Each string: 1-100 characters, no empty strings
    - Maximum 10 areas to emphasize
    - Each area cannot contain XSS patterns

    Raises:
        CoverLetterValidationError: If validation fails

    Example:
        >>> validate_emphasis_areas(None)  # Valid: optional field
        >>> validate_emphasis_areas([])  # Valid: empty list ok
        >>> validate_emphasis_areas(["leadership", "python"])  # Valid: list of strings
        >>> validate_emphasis_areas(["", "python"])  # Invalid: empty string
        >>> validate_emphasis_areas(["a" * 101])  # Invalid: too long
        >>> validate_emphasis_areas(["x"] * 15)  # Invalid: too many items

    PSEUDO-CODE:
    # if emphasis_areas is None:
    #     return  # Optional field, valid
    # if not isinstance(emphasis_areas, list):
    #     raise CoverLetterValidationError(...)
    # if len(emphasis_areas) > MAX_EMPHASIS_AREAS:
    #     raise CoverLetterValidationError(
    #         error_code="INVALID_EMPHASIS_AREAS",
    #         message=f"Too many emphasis areas (max {MAX_EMPHASIS_AREAS})",
    #         field="emphasis_areas",
    #     )
    # for area in emphasis_areas:
    #     if not area or not area.strip():
    #         raise CoverLetterValidationError(
    #             error_code="INVALID_EMPHASIS_AREA",
    #             message="Emphasis area cannot be empty",
    #             field="emphasis_areas",
    #         )
    #     if len(area) > MAX_EMPHASIS_AREA_LENGTH:
    #         raise CoverLetterValidationError(...)
    #     if _contains_unsafe_patterns(area):
    #         raise CoverLetterValidationError(...)
    """

    # Implementation:
    if emphasis_areas is None:
        return  # Optional field

    if not isinstance(emphasis_areas, list):
        raise CoverLetterValidationError(
            error_code="INVALID_EMPHASIS_AREAS",
            message="Emphasis areas must be a list",
            field="emphasis_areas",
        )

    if len(emphasis_areas) > MAX_EMPHASIS_AREAS:
        raise CoverLetterValidationError(
            error_code="INVALID_EMPHASIS_AREAS",
            message=f"Too many emphasis areas (max {MAX_EMPHASIS_AREAS})",
            field="emphasis_areas",
            actual_value=str(len(emphasis_areas)),
            constraint=f"max_count={MAX_EMPHASIS_AREAS}",
        )

    for i, area in enumerate(emphasis_areas):
        if not area or not area.strip():
            raise CoverLetterValidationError(
                error_code="INVALID_EMPHASIS_AREA",
                message=f"Emphasis area {i} cannot be empty",
                field="emphasis_areas",
            )

        if len(area) > MAX_EMPHASIS_AREA_LENGTH:
            raise CoverLetterValidationError(
                error_code="INVALID_EMPHASIS_AREA",
                message=f"Emphasis area {i} exceeds {MAX_EMPHASIS_AREA_LENGTH} characters",
                field="emphasis_areas",
                actual_value=area,
                constraint=f"max_length={MAX_EMPHASIS_AREA_LENGTH}",
            )

        if _contains_unsafe_patterns(area):
            raise CoverLetterValidationError(
                error_code="INVALID_EMPHASIS_AREA",
                message=f"Emphasis area {i} contains invalid characters",
                field="emphasis_areas",
            )

    logger.info(
        "Emphasis areas validation passed",
        extra={"emphasis_areas_count": len(emphasis_areas)},
    )


def validate_job_description(job_description: Optional[str]) -> None:
    """
    Validate job description field (optional, but constrained if provided).

    Rules:
    - Optional field (can be None)
    - If provided, must not be empty or whitespace-only
    - Max length: 50,000 characters
    - No XSS patterns

    Raises:
        CoverLetterValidationError: If validation fails

    Example:
        >>> validate_job_description(None)  # Valid: optional
        >>> validate_job_description("We are seeking...")  # Valid
        >>> validate_job_description("")  # Invalid: empty string
        >>> validate_job_description("   ")  # Invalid: whitespace-only
        >>> validate_job_description("x" * 50001)  # Invalid: too long
        >>> validate_job_description("<script>alert</script>")  # Invalid: XSS

    PSEUDO-CODE:
    # if job_description is None:
    #     return  # Optional
    # if not job_description.strip():
    #     raise CoverLetterValidationError(
    #         error_code="INVALID_JOB_DESCRIPTION",
    #         message="Job description cannot be empty",
    #         field="job_description",
    #     )
    # if len(job_description) > MAX_JOB_DESCRIPTION_LENGTH:
    #     raise CoverLetterValidationError(...)
    # if _contains_unsafe_patterns(job_description):
    #     raise CoverLetterValidationError(...)
    """

    # Implementation:
    if job_description is None:
        return  # Optional field

    if not job_description.strip():
        raise CoverLetterValidationError(
            error_code="INVALID_JOB_DESCRIPTION",
            message="Job description cannot be empty",
            field="job_description",
        )

    if len(job_description) > MAX_JOB_DESCRIPTION_LENGTH:
        raise CoverLetterValidationError(
            error_code="INVALID_JOB_DESCRIPTION",
            message=f"Job description exceeds {MAX_JOB_DESCRIPTION_LENGTH} characters",
            field="job_description",
            actual_value=job_description[:50],
            constraint=f"max_length={MAX_JOB_DESCRIPTION_LENGTH}",
        )

    if _contains_unsafe_patterns(job_description):
        raise CoverLetterValidationError(
            error_code="INVALID_JOB_DESCRIPTION",
            message="Job description contains invalid characters",
            field="job_description",
        )

    logger.info(
        "Job description validation passed",
        extra={"job_description_length": len(job_description)},
    )


def validate_cv_id(cv_id: str) -> None:
    """
    Validate CV ID reference.

    Rules:
    - Required (cannot be empty)
    - Min length: 1 character
    - Max length: 255 characters
    - Alphanumeric and underscore only (no XSS patterns)

    Raises:
        CoverLetterValidationError: If validation fails

    Example:
        >>> validate_cv_id("cv_abc123")  # Valid
        >>> validate_cv_id("")  # Invalid: empty
        >>> validate_cv_id("<script>")  # Invalid: XSS pattern

    PSEUDO-CODE:
    # if not cv_id or not cv_id.strip():
    #     raise CoverLetterValidationError(...)
    # if len(cv_id) > 255:
    #     raise CoverLetterValidationError(...)
    # if not re.match(r'^[a-zA-Z0-9_]+$', cv_id):
    #     raise CoverLetterValidationError(...)
    """

    # Implementation:
    if not cv_id or not cv_id.strip():
        raise CoverLetterValidationError(
            error_code="INVALID_CV_ID",
            message="CV ID is required",
            field="cv_id",
        )

    if len(cv_id) > 255:
        raise CoverLetterValidationError(
            error_code="INVALID_CV_ID",
            message="CV ID exceeds 255 characters",
            field="cv_id",
        )

    if not re.match(r"^[a-zA-Z0-9_]+$", cv_id):
        raise CoverLetterValidationError(
            error_code="INVALID_CV_ID",
            message="CV ID must contain only alphanumeric characters and underscores",
            field="cv_id",
            actual_value=cv_id,
        )

    logger.info("CV ID validation passed", extra={"cv_id": cv_id})


def validate_job_id(job_id: str) -> None:
    """
    Validate Job ID reference.

    Rules:
    - Required (cannot be empty)
    - Min length: 1 character
    - Max length: 255 characters
    - Alphanumeric and underscore only (no XSS patterns)

    Raises:
        CoverLetterValidationError: If validation fails

    Example:
        >>> validate_job_id("job_xyz789")  # Valid
        >>> validate_job_id("")  # Invalid: empty
        >>> validate_job_id("javascript:")  # Invalid: XSS pattern

    PSEUDO-CODE:
    # Similar to validate_cv_id()
    """

    # Implementation:
    if not job_id or not job_id.strip():
        raise CoverLetterValidationError(
            error_code="INVALID_JOB_ID",
            message="Job ID is required",
            field="job_id",
        )

    if len(job_id) > 255:
        raise CoverLetterValidationError(
            error_code="INVALID_JOB_ID",
            message="Job ID exceeds 255 characters",
            field="job_id",
        )

    if not re.match(r"^[a-zA-Z0-9_]+$", job_id):
        raise CoverLetterValidationError(
            error_code="INVALID_JOB_ID",
            message="Job ID must contain only alphanumeric characters and underscores",
            field="job_id",
            actual_value=job_id,
        )

    logger.info("Job ID validation passed", extra={"job_id": job_id})
```

### Test Implementation Structure

The test suite comprehensively covers all validation functions with both success and failure paths, boundary conditions, and edge cases. Tests are organized by function and follow the "Arrange-Act-Assert" pattern.

```python
"""
Tests for Cover Letter Validation Utilities.
Per tests/cover-letter/unit/test_validation.py.

Test categories:
- Company name validation (4 tests)
- Job title validation (4 tests)
- Word count validation (4 tests)
- Tone validation (3 tests)
- Emphasis areas validation (3 tests)
- Job description validation (3 tests)
- CV ID validation (2 tests)
- Job ID validation (2 tests)

Total: 18-20 tests covering all validation functions.
"""

import pytest

from careervp.handlers.utils.validation import (
    CoverLetterValidationError,
    validate_company_name,
    validate_job_title,
    validate_word_count_target,
    validate_tone,
    validate_emphasis_areas,
    validate_job_description,
    validate_cv_id,
    validate_job_id,
    MAX_COMPANY_NAME_LENGTH,
    MAX_JOB_TITLE_LENGTH,
    MIN_WORD_COUNT_TARGET,
    MAX_WORD_COUNT_TARGET,
    VALID_TONES,
    MAX_EMPHASIS_AREAS,
)


class TestCompanyNameValidation:
    """Test company name validation."""

    def test_validate_company_name_valid(self) -> None:
        """Valid company name passes validation."""
        # PSEUDO-CODE:
        # Should not raise exception for "TechCorp Inc"
        # Should not raise exception for single letter "A"
        # Should not raise exception for maximum length (255 chars)
        validate_company_name("TechCorp Inc")  # Should pass
        validate_company_name("A")  # Single character
        validate_company_name("X" * MAX_COMPANY_NAME_LENGTH)  # Max length
        # If we get here, no exception was raised - test passes

    def test_validate_company_name_empty_raises_error(self) -> None:
        """Empty company name fails validation."""
        # PSEUDO-CODE:
        # assert validate_company_name("") raises CoverLetterValidationError
        # assert error_code == "INVALID_COMPANY_NAME"
        # assert "required" in error message (lowercase)
        with pytest.raises(CoverLetterValidationError) as exc_info:
            validate_company_name("")
        assert exc_info.value.error_code == "INVALID_COMPANY_NAME"
        assert "required" in exc_info.value.message.lower()

    def test_validate_company_name_whitespace_only_raises_error(self) -> None:
        """Whitespace-only company name fails validation."""
        # PSEUDO-CODE:
        # assert validate_company_name("   ") raises CoverLetterValidationError
        # assert validate_company_name("\t\n") raises error
        with pytest.raises(CoverLetterValidationError):
            validate_company_name("   ")
        with pytest.raises(CoverLetterValidationError):
            validate_company_name("\t\n")

    def test_validate_company_name_exceeds_max_length(self) -> None:
        """Company name exceeding max length fails validation."""
        # PSEUDO-CODE:
        # too_long_name = "X" * (MAX_COMPANY_NAME_LENGTH + 1)
        # assert validate_company_name(too_long_name) raises error
        # assert "exceeds" in error message (case-insensitive)
        too_long_name = "X" * (MAX_COMPANY_NAME_LENGTH + 1)
        with pytest.raises(CoverLetterValidationError) as exc_info:
            validate_company_name(too_long_name)
        assert "exceeds" in exc_info.value.message.lower()

    def test_validate_company_name_xss_prevention(self) -> None:
        """XSS patterns in company name are blocked."""
        # PSEUDO-CODE:
        # assert validate_company_name("<script>alert</script>") raises error
        # assert validate_company_name("javascript:void(0)") raises error
        # assert validate_company_name("onerror='alert'") raises error
        xss_payloads = [
            "<script>alert</script>",
            "javascript:void(0)",
            "onerror='alert'",
            "SCRIPT alert",  # Case insensitive
        ]
        for payload in xss_payloads:
            with pytest.raises(CoverLetterValidationError) as exc_info:
                validate_company_name(payload)
            assert exc_info.value.error_code == "INVALID_COMPANY_NAME"


class TestJobTitleValidation:
    """Test job title validation."""

    def test_validate_job_title_valid(self) -> None:
        """Valid job title passes validation."""
        # PSEUDO-CODE:
        # Should pass for "Senior Python Engineer"
        # Should pass for single letter "E"
        # Should pass for maximum length
        validate_job_title("Senior Python Engineer")
        validate_job_title("E")
        validate_job_title("J" * MAX_JOB_TITLE_LENGTH)

    def test_validate_job_title_empty_raises_error(self) -> None:
        """Empty job title fails validation."""
        # PSEUDO-CODE:
        # assert validate_job_title("") raises CoverLetterValidationError
        with pytest.raises(CoverLetterValidationError) as exc_info:
            validate_job_title("")
        assert exc_info.value.error_code == "INVALID_JOB_TITLE"

    def test_validate_job_title_exceeds_max_length(self) -> None:
        """Job title exceeding max length fails validation."""
        # PSEUDO-CODE:
        # too_long_title = "T" * (MAX_JOB_TITLE_LENGTH + 1)
        # assert validate_job_title(too_long_title) raises error
        too_long_title = "T" * (MAX_JOB_TITLE_LENGTH + 1)
        with pytest.raises(CoverLetterValidationError):
            validate_job_title(too_long_title)

    def test_validate_job_title_xss_prevention(self) -> None:
        """XSS patterns in job title are blocked."""
        # PSEUDO-CODE:
        # assert validate_job_title("onclick='alert'") raises error
        xss_payloads = ["onclick='alert'", "ONERROR=alert", "javascript:"]
        for payload in xss_payloads:
            with pytest.raises(CoverLetterValidationError):
                validate_job_title(payload)


class TestWordCountValidation:
    """Test word count target validation."""

    def test_validate_word_count_valid(self) -> None:
        """Valid word count values pass validation."""
        # PSEUDO-CODE:
        # Should pass for MIN_WORD_COUNT_TARGET (200)
        # Should pass for MAX_WORD_COUNT_TARGET (500)
        # Should pass for middle value (300)
        validate_word_count_target(MIN_WORD_COUNT_TARGET)
        validate_word_count_target(MAX_WORD_COUNT_TARGET)
        validate_word_count_target(300)

    def test_validate_word_count_below_minimum(self) -> None:
        """Word count below minimum fails validation."""
        # PSEUDO-CODE:
        # assert validate_word_count_target(150) raises error
        # assert validate_word_count_target(0) raises error
        # assert validate_word_count_target(-100) raises error
        for invalid_count in [150, 0, -100]:
            with pytest.raises(CoverLetterValidationError) as exc_info:
                validate_word_count_target(invalid_count)
            assert "at least" in exc_info.value.message.lower()

    def test_validate_word_count_exceeds_maximum(self) -> None:
        """Word count exceeding maximum fails validation."""
        # PSEUDO-CODE:
        # assert validate_word_count_target(501) raises error
        # assert validate_word_count_target(1000) raises error
        for invalid_count in [501, 1000]:
            with pytest.raises(CoverLetterValidationError) as exc_info:
                validate_word_count_target(invalid_count)
            assert "cannot exceed" in exc_info.value.message.lower()

    def test_validate_word_count_boundary_values(self) -> None:
        """Word count boundary values are tested."""
        # PSEUDO-CODE:
        # Boundary 1: MIN - 1 should fail
        # Boundary 2: MIN should pass
        # Boundary 3: MAX should pass
        # Boundary 4: MAX + 1 should fail
        with pytest.raises(CoverLetterValidationError):
            validate_word_count_target(MIN_WORD_COUNT_TARGET - 1)
        validate_word_count_target(MIN_WORD_COUNT_TARGET)
        validate_word_count_target(MAX_WORD_COUNT_TARGET)
        with pytest.raises(CoverLetterValidationError):
            validate_word_count_target(MAX_WORD_COUNT_TARGET + 1)


class TestToneValidation:
    """Test tone preference validation."""

    def test_validate_tone_valid_values(self) -> None:
        """All valid tone values pass validation."""
        # PSEUDO-CODE:
        # Should pass for all values in VALID_TONES
        for valid_tone in VALID_TONES:
            validate_tone(valid_tone)  # Should not raise

    def test_validate_tone_invalid_raises_error(self) -> None:
        """Invalid tone values fail validation."""
        # PSEUDO-CODE:
        # assert validate_tone("casual") raises error
        # assert validate_tone("friendly") raises error
        # assert validate_tone("") raises error
        invalid_tones = ["casual", "friendly", "", "PROFESSIONAL"]
        for invalid_tone in invalid_tones:
            with pytest.raises(CoverLetterValidationError) as exc_info:
                validate_tone(invalid_tone)
            assert "invalid tone" in exc_info.value.message.lower()

    def test_validate_tone_case_sensitive(self) -> None:
        """Tone validation is case-sensitive."""
        # PSEUDO-CODE:
        # assert validate_tone("PROFESSIONAL") raises error
        # assert validate_tone("Professional") raises error
        # Only lowercase "professional" should pass
        with pytest.raises(CoverLetterValidationError):
            validate_tone("PROFESSIONAL")
        with pytest.raises(CoverLetterValidationError):
            validate_tone("Professional")


class TestEmphasisAreasValidation:
    """Test emphasis areas validation."""

    def test_validate_emphasis_areas_valid(self) -> None:
        """Valid emphasis areas pass validation."""
        # PSEUDO-CODE:
        # Should pass for None (optional)
        # Should pass for empty list
        # Should pass for valid list of strings
        validate_emphasis_areas(None)
        validate_emphasis_areas([])
        validate_emphasis_areas(["leadership", "python", "aws"])

    def test_validate_emphasis_areas_empty_string_fails(self) -> None:
        """Empty strings in list fail validation."""
        # PSEUDO-CODE:
        # assert validate_emphasis_areas(["", "python"]) raises error
        with pytest.raises(CoverLetterValidationError):
            validate_emphasis_areas(["", "python"])

    def test_validate_emphasis_areas_exceeds_max_count(self) -> None:
        """Too many emphasis areas fail validation."""
        # PSEUDO-CODE:
        # too_many = ["area"] * (MAX_EMPHASIS_AREAS + 1)
        # assert validate_emphasis_areas(too_many) raises error
        too_many = ["area"] * (MAX_EMPHASIS_AREAS + 1)
        with pytest.raises(CoverLetterValidationError) as exc_info:
            validate_emphasis_areas(too_many)
        assert "too many" in exc_info.value.message.lower()

    def test_validate_emphasis_areas_xss_prevention(self) -> None:
        """XSS patterns in emphasis areas are blocked."""
        # PSEUDO-CODE:
        # assert validate_emphasis_areas(["<script>alert</script>"]) raises error
        with pytest.raises(CoverLetterValidationError):
            validate_emphasis_areas(["<script>alert</script>"])


class TestJobDescriptionValidation:
    """Test job description validation."""

    def test_validate_job_description_valid(self) -> None:
        """Valid job descriptions pass validation."""
        # PSEUDO-CODE:
        # Should pass for None (optional)
        # Should pass for valid text
        # Should pass for maximum length
        validate_job_description(None)
        validate_job_description("We are seeking a Senior Engineer...")
        validate_job_description("X" * 50_000)

    def test_validate_job_description_empty_fails(self) -> None:
        """Empty job description fails validation."""
        # PSEUDO-CODE:
        # assert validate_job_description("") raises error
        # assert validate_job_description("   ") raises error
        with pytest.raises(CoverLetterValidationError):
            validate_job_description("")
        with pytest.raises(CoverLetterValidationError):
            validate_job_description("   ")

    def test_validate_job_description_exceeds_max_length(self) -> None:
        """Job description exceeding max length fails validation."""
        # PSEUDO-CODE:
        # too_long = "X" * 50_001
        # assert validate_job_description(too_long) raises error
        too_long = "X" * 50_001
        with pytest.raises(CoverLetterValidationError) as exc_info:
            validate_job_description(too_long)
        assert "exceeds" in exc_info.value.message.lower()


class TestCVAndJobIDValidation:
    """Test CV ID and Job ID validation."""

    def test_validate_cv_id_valid(self) -> None:
        """Valid CV IDs pass validation."""
        # PSEUDO-CODE:
        # Should pass for "cv_abc123"
        # Should pass for alphanumeric with underscores
        validate_cv_id("cv_abc123")
        validate_cv_id("CV_XYZ_789")

    def test_validate_cv_id_invalid_characters_fail(self) -> None:
        """CV IDs with invalid characters fail validation."""
        # PSEUDO-CODE:
        # assert validate_cv_id("cv-abc") raises error  (hyphens not allowed)
        # assert validate_cv_id("cv.abc") raises error  (dots not allowed)
        with pytest.raises(CoverLetterValidationError):
            validate_cv_id("cv-abc")
        with pytest.raises(CoverLetterValidationError):
            validate_cv_id("cv.abc")

    def test_validate_job_id_valid(self) -> None:
        """Valid Job IDs pass validation."""
        # PSEUDO-CODE:
        # Should pass for "job_xyz789"
        validate_job_id("job_xyz789")

    def test_validate_job_id_invalid_characters_fail(self) -> None:
        """Job IDs with invalid characters fail validation."""
        # PSEUDO-CODE:
        # assert validate_job_id("job-xyz") raises error
        with pytest.raises(CoverLetterValidationError):
            validate_job_id("job-xyz")
```

### Verification Commands

Run these commands to verify implementation:

```bash
# Navigate to backend directory
cd src/backend

# Step 1: Format code
uv run ruff format careervp/handlers/utils/validation.py

# Step 2: Check for style issues
uv run ruff check --fix careervp/handlers/utils/

# Step 3: Type check with strict mode (most important)
uv run mypy careervp/handlers/utils/ --strict

# Step 4: Run unit tests for validation
uv run pytest tests/cover-letter/unit/test_validation.py -v

# Step 5: Run tests with coverage report
uv run pytest tests/cover-letter/unit/test_validation.py --cov=careervp.handlers.utils.validation --cov-report=term-missing

# Expected output (all steps should pass):
# ===== test session starts =====
# tests/cover-letter/unit/test_validation.py::TestCompanyNameValidation::test_validate_company_name_valid PASSED
# tests/cover-letter/unit/test_validation.py::TestCompanyNameValidation::test_validate_company_name_empty_raises_error PASSED
# tests/cover-letter/unit/test_validation.py::TestCompanyNameValidation::test_validate_company_name_whitespace_only_raises_error PASSED
# tests/cover-letter/unit/test_validation.py::TestCompanyNameValidation::test_validate_company_name_exceeds_max_length PASSED
# tests/cover-letter/unit/test_validation.py::TestCompanyNameValidation::test_validate_company_name_xss_prevention PASSED
# tests/cover-letter/unit/test_validation.py::TestJobTitleValidation::test_validate_job_title_valid PASSED
# tests/cover-letter/unit/test_validation.py::TestJobTitleValidation::test_validate_job_title_empty_raises_error PASSED
# tests/cover-letter/unit/test_validation.py::TestJobTitleValidation::test_validate_job_title_exceeds_max_length PASSED
# tests/cover-letter/unit/test_validation.py::TestJobTitleValidation::test_validate_job_title_xss_prevention PASSED
# tests/cover-letter/unit/test_validation.py::TestWordCountValidation::test_validate_word_count_valid PASSED
# tests/cover-letter/unit/test_validation.py::TestWordCountValidation::test_validate_word_count_below_minimum PASSED
# tests/cover-letter/unit/test_validation.py::TestWordCountValidation::test_validate_word_count_exceeds_maximum PASSED
# tests/cover-letter/unit/test_validation.py::TestWordCountValidation::test_validate_word_count_boundary_values PASSED
# tests/cover-letter/unit/test_validation.py::TestToneValidation::test_validate_tone_valid_values PASSED
# tests/cover-letter/unit/test_validation.py::TestToneValidation::test_validate_tone_invalid_raises_error PASSED
# tests/cover-letter/unit/test_validation.py::TestToneValidation::test_validate_tone_case_sensitive PASSED
# tests/cover-letter/unit/test_validation.py::TestEmphasisAreasValidation::test_validate_emphasis_areas_valid PASSED
# tests/cover-letter/unit/test_validation.py::TestEmphasisAreasValidation::test_validate_emphasis_areas_empty_string_fails PASSED
# tests/cover-letter/unit/test_validation.py::TestEmphasisAreasValidation::test_validate_emphasis_areas_exceeds_max_count PASSED
# tests/cover-letter/unit/test_validation.py::TestEmphasisAreasValidation::test_validate_emphasis_areas_xss_prevention PASSED
# tests/cover-letter/unit/test_validation.py::TestJobDescriptionValidation::test_validate_job_description_valid PASSED
# tests/cover-letter/unit/test_validation.py::TestJobDescriptionValidation::test_validate_job_description_empty_fails PASSED
# tests/cover-letter/unit/test_validation.py::TestJobDescriptionValidation::test_validate_job_description_exceeds_max_length PASSED
# tests/cover-letter/unit/test_validation.py::TestCVAndJobIDValidation::test_validate_cv_id_valid PASSED
# tests/cover-letter/unit/test_validation.py::TestCVAndJobIDValidation::test_validate_cv_id_invalid_characters_fail PASSED
# tests/cover-letter/unit/test_validation.py::TestCVAndJobIDValidation::test_validate_job_id_valid PASSED
# tests/cover-letter/unit/test_validation.py::TestCVAndJobIDValidation::test_validate_job_id_invalid_characters_fail PASSED
# ===== 20 passed in X.XXs =====
```

### Expected Test Results

All tests should pass with the following output structure:

```
tests/cover-letter/unit/test_validation.py::TestCompanyNameValidation PASSED (5 tests)
tests/cover-letter/unit/test_validation.py::TestJobTitleValidation PASSED (4 tests)
tests/cover-letter/unit/test_validation.py::TestWordCountValidation PASSED (4 tests)
tests/cover-letter/unit/test_validation.py::TestToneValidation PASSED (3 tests)
tests/cover-letter/unit/test_validation.py::TestEmphasisAreasValidation PASSED (4 tests)
tests/cover-letter/unit/test_validation.py::TestJobDescriptionValidation PASSED (3 tests)
tests/cover-letter/unit/test_validation.py::TestCVAndJobIDValidation PASSED (2 tests)

Total: 20 tests passing
Type checking: 0 errors, 0 warnings
Code style: 0 violations
Coverage: >90% for validation.py
```

---

## Zero-Hallucination Checklist

Ensure implementation follows spec exactly:

- [ ] All validation constants match COVER_LETTER_SPEC.md values
- [ ] Company name: max 255 chars, XSS prevention enabled
- [ ] Job title: max 255 chars, XSS prevention enabled
- [ ] Word count: 200-500 range, default 300
- [ ] Tone: exactly ["professional", "enthusiastic", "technical"]
- [ ] Emphasis areas: optional, max 10 items, max 100 chars each
- [ ] Job description: optional, max 50,000 chars, XSS prevention
- [ ] CV ID: alphanumeric + underscore only, max 255 chars
- [ ] Job ID: alphanumeric + underscore only, max 255 chars
- [ ] All validation functions raise CoverLetterValidationError with error_code
- [ ] Error messages include field, actual_value, and constraint context
- [ ] XSS patterns detected: <script, javascript:, onerror, onload, onclick, onmouseover
- [ ] All tests pass with 0 warnings/errors
- [ ] Code coverage >90%
- [ ] mypy --strict passes with 0 errors

---

## Acceptance Criteria

Task 10.1 is complete when:

- [ ] `validate_company_name()` implemented and tested (rejects empty, >255 chars, XSS patterns)
- [ ] `validate_job_title()` implemented and tested (rejects empty, >255 chars, XSS patterns)
- [ ] `validate_word_count_target()` implemented and tested (enforces 200-500 range)
- [ ] `validate_tone()` implemented and tested (enforces ["professional", "enthusiastic", "technical"])
- [ ] `validate_emphasis_areas()` implemented and tested (optional, max 10 items, XSS prevention)
- [ ] `validate_job_description()` implemented and tested (optional, max 50k chars, XSS prevention)
- [ ] `validate_cv_id()` implemented and tested (alphanumeric + underscore only)
- [ ] `validate_job_id()` implemented and tested (alphanumeric + underscore only)
- [ ] `CoverLetterValidationError` exception class implemented with error context
- [ ] All 20 unit tests passing
- [ ] All code quality checks passing (ruff format, ruff check, mypy --strict)
- [ ] Code coverage ≥90% for validation.py
- [ ] No security vulnerabilities (XSS patterns detected and blocked)
- [ ] All validation constants match spec exactly

---

## Common Pitfalls to Avoid

### Pitfall 1: Not Stripping Whitespace Before Validation
**Problem:** Allowing "   " as valid company name (whitespace-only string)
**Solution:** Check `not company_name.strip()` before validating length

### Pitfall 2: Case-Sensitive Tone Validation
**Problem:** Accepting "PROFESSIONAL" or "Professional" as valid
**Solution:** Enforce exact lowercase match against VALID_TONES list

### Pitfall 3: Missing XSS Prevention
**Problem:** Not detecting `<script>`, `javascript:`, or other injection patterns
**Solution:** Implement `_contains_unsafe_patterns()` helper and call before accepting strings

### Pitfall 4: Wrong Error Codes
**Problem:** Using generic errors instead of specific error codes
**Solution:** Each validation function must raise `CoverLetterValidationError` with proper `error_code`

### Pitfall 5: Incomplete Error Context
**Problem:** Error messages missing field name, actual value, or constraint
**Solution:** Always populate `field`, `actual_value`, and `constraint` when constructing errors

### Pitfall 6: Not Testing Boundary Conditions
**Problem:** Only testing happy path, missing edge cases
**Solution:** Test MIN-1, MIN, MAX, MAX+1 for all numeric constraints

### Pitfall 7: Type Hints Missing
**Problem:** Functions without return type or parameter type hints
**Solution:** Run `mypy --strict` after every function, ensure no issues

### Pitfall 8: Skipping Optional Field Handling
**Problem:** Raising error for None values on optional fields
**Solution:** Return early for None on optional fields (emphasis_areas, job_description)

---

## Success Checklist

Mark complete when:

- [ ] File created: `src/backend/careervp/handlers/utils/validation.py`
- [ ] All 8 validation functions implemented with full type hints
- [ ] CoverLetterValidationError exception implemented with error context
- [ ] All validation constants defined and match spec
- [ ] 20 unit tests created and all passing
- [ ] Code formatted: `uv run ruff format` passes
- [ ] Linting: `uv run ruff check --fix` passes
- [ ] Type checking: `uv run mypy --strict` passes (0 errors)
- [ ] Coverage: >90% for validation.py
- [ ] XSS prevention verified (test with malicious payloads)
- [ ] All validation constraints verified against COVER_LETTER_SPEC.md
- [ ] Commit created with proper message

---

## References

**Specification:** [COVER_LETTER_SPEC.md](../../specs/cover-letter/COVER_LETTER_SPEC.md) - Complete API specification with all constraints

**Similar Pattern:** [Phase 9 Task 01](../09-cv-tailoring/task-01-validation.md) - CV tailoring validation (use as pattern)

**Existing Validation Code:** `src/backend/careervp/handlers/utils/validation.py` (check for existing patterns)

**Error Handling:** [ErrorHandling](../../architecture/error-handling.md) - Standard error patterns used throughout

---

**Document Version:** 1.0
**Last Updated:** 2026-02-05
**Next Document:** [task-02-infrastructure.md](./task-02-infrastructure.md)
**Phase:** 10 - Cover Letter Generation
