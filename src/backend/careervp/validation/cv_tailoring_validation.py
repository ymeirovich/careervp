"""Validation helpers for CV tailoring requests."""

from __future__ import annotations

import re

from careervp.models.result import Result, ResultCode

CV_ID_PATTERN = re.compile(r'^cv[-_][A-Za-z0-9]+$')


def validate_file_size(file_size_bytes: int, max_size: int = 10 * 1024 * 1024) -> Result[None]:
    """Validate uploaded file size."""
    if file_size_bytes > max_size:
        return Result(
            success=False,
            error=f'File size exceeds maximum of {max_size} bytes',
            code=ResultCode.VALIDATION_FILE_SIZE_EXCEEDED,
        )
    return Result(success=True, data=None, code=ResultCode.VALIDATION_SUCCESS)


def validate_text_length(text: str, min_length: int = 1, max_length: int = 1_000_000) -> Result[None]:
    """Validate text length boundaries."""
    if len(text) < min_length:
        return Result(
            success=False,
            error=f'Text is shorter than minimum of {min_length} characters',
            code=ResultCode.VALIDATION_TEXT_TOO_SHORT,
        )
    if len(text) > max_length:
        return Result(
            success=False,
            error=f'Text exceeds maximum of {max_length} characters',
            code=ResultCode.VALIDATION_TEXT_TOO_LONG,
        )
    return Result(success=True, data=None, code=ResultCode.VALIDATION_SUCCESS)


def validate_job_description(
    job_description: str,
    min_length: int = 50,
    max_length: int = 50_000,
) -> Result[None]:
    """Validate job description text."""
    if not job_description or not job_description.strip():
        return Result(
            success=False,
            error='Job description cannot be empty',
            code=ResultCode.VALIDATION_JOB_DESCRIPTION_EMPTY,
        )
    if len(job_description) < min_length:
        return Result(
            success=False,
            error=f'Job description must be at least {min_length} characters',
            code=ResultCode.VALIDATION_JOB_DESCRIPTION_TOO_SHORT,
        )
    if len(job_description) > max_length:
        return Result(
            success=False,
            error=f'Job description must be at most {max_length} characters',
            code=ResultCode.VALIDATION_JOB_DESCRIPTION_TOO_LONG,
        )
    return Result(success=True, data=None, code=ResultCode.VALIDATION_SUCCESS)


def validate_cv_id(cv_id: str) -> Result[None]:
    """Validate CV ID format."""
    if not cv_id or not CV_ID_PATTERN.match(cv_id):
        return Result(
            success=False,
            error='Invalid cv_id format',
            code=ResultCode.VALIDATION_INVALID_CV_ID,
        )
    return Result(success=True, data=None, code=ResultCode.VALIDATION_SUCCESS)


def validate_tone(tone: str | None) -> Result[None]:
    """Validate tone preference."""
    if tone is None:
        return Result(success=True, data=None, code=ResultCode.VALIDATION_SUCCESS)
    valid_tones = {'professional', 'casual', 'technical'}
    if tone not in valid_tones:
        return Result(
            success=False,
            error=f'Invalid tone: {tone}',
            code=ResultCode.VALIDATION_INVALID_TONE,
        )
    return Result(success=True, data=None, code=ResultCode.VALIDATION_SUCCESS)


def validate_target_length(target_length: str | None) -> Result[None]:
    """Validate target length preference."""
    if target_length is None:
        return Result(success=True, data=None, code=ResultCode.VALIDATION_SUCCESS)
    valid_lengths = {'one_page', 'two_pages', 'detailed'}
    if target_length not in valid_lengths:
        return Result(
            success=False,
            error=f'Invalid target length: {target_length}',
            code=ResultCode.VALIDATION_INVALID_TARGET_LENGTH,
        )
    return Result(success=True, data=None, code=ResultCode.VALIDATION_SUCCESS)


def validate_emphasis_areas(
    emphasis_areas: list[str] | None,
    max_count: int = 5,
) -> Result[None]:
    """Validate emphasis areas list length."""
    if emphasis_areas is None:
        return Result(success=True, data=None, code=ResultCode.VALIDATION_SUCCESS)
    if len(emphasis_areas) > max_count:
        return Result(
            success=False,
            error=f'Too many emphasis areas (max {max_count})',
            code=ResultCode.VALIDATION_TOO_MANY_EMPHASIS_AREAS,
        )
    return Result(success=True, data=None, code=ResultCode.VALIDATION_SUCCESS)
