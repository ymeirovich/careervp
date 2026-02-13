"""
Input validators for API requests and file uploads.
Per docs/refactor/specs/security_spec.yaml (SEC-002).

Provides request body validation and CV upload file validation using Pydantic
and file content inspection.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from careervp.handlers.utils.observability import logger
from careervp.models.result import Result, ResultCode

# Allowed file extensions for CV uploads
ALLOWED_CV_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt'}

# File size limits
MAX_CV_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MIN_CV_FILE_SIZE = 1024  # 1KB

# Content validation patterns
CV_CONTENT_MIN_LENGTH = 100
CV_CONTENT_MAX_LENGTH = 5_000_000


class RequestValidator(BaseModel):
    """Base request validator using Pydantic schema."""

    model_config = ConfigDict(extra='forbid')  # Reject unknown fields


def validate_request(body: dict[str, Any], schema: type[BaseModel]) -> Result[dict[str, Any]]:
    """
    Validate request body against a Pydantic schema.

    Per SEC-002: Pydantic models for schema validation.

    Args:
        body: Request body dictionary
        schema: Pydantic BaseModel schema class to validate against

    Returns:
        Result with validated data if successful, error if validation fails
    """
    try:
        if not body:
            logger.warning('Empty request body')
            return Result(
                success=False,
                error='Request body cannot be empty',
                code=ResultCode.VALIDATION_ERROR,
            )

        # Validate against schema
        validated = schema.model_validate(body)
        logger.info(
            'Request validation successful',
            schema=schema.__name__,
            fields_count=len(body),
        )
        return Result(
            success=True,
            data=validated.model_dump(),
            code=ResultCode.VALIDATION_SUCCESS,
        )

    except ValidationError as exc:
        logger.warning(
            'Request validation failed',
            schema=schema.__name__,
            errors=str(exc),
        )
        error_details = '; '.join(
            [f"{error['loc'][0]}: {error['msg']}" for error in exc.errors()]
        )
        return Result(
            success=False,
            error=f'Request validation failed: {error_details}',
            code=ResultCode.VALIDATION_ERROR,
        )
    except Exception as exc:
        logger.error('Unexpected error during request validation', error=str(exc))
        return Result(
            success=False,
            error='Unexpected validation error',
            code=ResultCode.INTERNAL_ERROR,
        )


def validate_cv_upload(
    filename: str,
    file_content: bytes,
    file_size: int | None = None,
) -> Result[None]:
    """
    Validate CV file upload.

    Per SEC-002: Request body validation.

    Checks:
    - File extension whitelist
    - File size limits (1KB - 10MB)
    - Content length bounds
    - Non-empty content

    Args:
        filename: Original filename from upload
        file_content: File content as bytes
        file_size: Optional explicit file size (defaults to len(file_content))

    Returns:
        Result with validation status
    """
    try:
        # Use provided file_size or calculate from content
        size = file_size if file_size is not None else len(file_content)

        # Validate filename
        if not filename or not isinstance(filename, str):
            logger.warning('Invalid filename')
            return Result(
                success=False,
                error='Filename is required and must be a string',
                code=ResultCode.VALIDATION_ERROR,
            )

        # Validate file extension
        ext = _get_file_extension(filename)
        if ext.lower() not in ALLOWED_CV_EXTENSIONS:
            logger.warning('Invalid file extension', file_name=filename, extension=ext)
            return Result(
                success=False,
                error=f'File type {ext} not supported. Allowed: {", ".join(ALLOWED_CV_EXTENSIONS)}',
                code=ResultCode.UNSUPPORTED_FILE_FORMAT,
            )

        # Validate file size
        if size < MIN_CV_FILE_SIZE:
            logger.warning('File too small', file_name=filename, size=size)
            return Result(
                success=False,
                error=f'File is too small (minimum {MIN_CV_FILE_SIZE} bytes)',
                code=ResultCode.VALIDATION_FILE_SIZE_EXCEEDED,
            )

        if size > MAX_CV_FILE_SIZE:
            logger.warning('File too large', file_name=filename, size=size)
            return Result(
                success=False,
                error=f'File size exceeds maximum of {MAX_CV_FILE_SIZE} bytes',
                code=ResultCode.VALIDATION_FILE_SIZE_EXCEEDED,
            )

        # Validate content is not empty
        if not file_content:
            logger.warning('Empty file content', file_name=filename)
            return Result(
                success=False,
                error='File content cannot be empty',
                code=ResultCode.VALIDATION_ERROR,
            )

        # Validate content length for text-based formats
        content_length = len(file_content)
        if content_length < CV_CONTENT_MIN_LENGTH:
            logger.warning(
                'File content too short',
                file_name=filename,
                content_length=content_length,
            )
            return Result(
                success=False,
                error=f'File content is too short (minimum {CV_CONTENT_MIN_LENGTH} bytes)',
                code=ResultCode.VALIDATION_TEXT_TOO_SHORT,
            )

        if content_length > CV_CONTENT_MAX_LENGTH:
            logger.warning(
                'File content too long',
                file_name=filename,
                content_length=content_length,
            )
            return Result(
                success=False,
                error=f'File content exceeds maximum of {CV_CONTENT_MAX_LENGTH} bytes',
                code=ResultCode.VALIDATION_TEXT_TOO_LONG,
            )

        logger.info(
            'CV file validation successful',
            file_name=filename,
            size=size,
            extension=ext,
        )
        return Result(
            success=True,
            data=None,
            code=ResultCode.VALIDATION_SUCCESS,
        )

    except Exception as exc:
        logger.error('Unexpected error during file validation', error=str(exc))
        return Result(
            success=False,
            error='Unexpected validation error',
            code=ResultCode.INTERNAL_ERROR,
        )


def _get_file_extension(filename: str) -> str:
    """
    Extract file extension from filename.

    Args:
        filename: Original filename

    Returns:
        File extension including dot, or empty string if no extension
    """
    if '.' not in filename:
        return ''
    return '.' + filename.rsplit('.', 1)[-1]
