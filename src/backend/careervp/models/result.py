"""
Universal Result object pattern for cross-layer error communication.
Per docs/architecture/system_design.md Section 2: Result Object Pattern.
"""

from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar('T')


class Result(BaseModel, Generic[T]):
    """
    Standard Result object for all logic layer functions.

    Usage:
        # Success case
        return Result(success=True, data=parsed_cv, code='CV_PARSED')

        # Error case
        return Result(success=False, error='Invalid date format', code='FVS_VALIDATION_FAILED')
    """

    success: Annotated[bool, Field(description='Whether the operation succeeded')]
    data: T | None = Field(default=None, description='The result data if successful')
    error: Annotated[str | None, Field(description='Error message if failed')] = None
    code: Annotated[str, Field(description='Machine-readable result code')]

    model_config = {'frozen': False}


# Common result codes for consistency
class ResultCode:
    """Standard result codes used across the application."""

    # Success codes
    SUCCESS = 'SUCCESS'
    CV_PARSED = 'CV_PARSED'
    VPR_GENERATED = 'VPR_GENERATED'
    CV_TAILORED = 'CV_TAILORED'
    COVER_LETTER_GENERATED = 'COVER_LETTER_GENERATED'
    COMPANY_RESEARCHED = 'COMPANY_RESEARCHED'

    # Validation errors
    FVS_VALIDATION_FAILED = 'FVS_VALIDATION_FAILED'
    FVS_DATE_MISMATCH = 'FVS_DATE_MISMATCH'
    FVS_ROLE_MISMATCH = 'FVS_ROLE_MISMATCH'
    FVS_HALLUCINATION_DETECTED = 'FVS_HALLUCINATION_DETECTED'

    # Input errors
    INVALID_INPUT = 'INVALID_INPUT'
    MISSING_REQUIRED_FIELD = 'MISSING_REQUIRED_FIELD'
    UNSUPPORTED_FILE_FORMAT = 'UNSUPPORTED_FILE_FORMAT'
    JOB_BOARD_URL_REJECTED = 'JOB_BOARD_URL_REJECTED'

    # LLM errors
    LLM_API_ERROR = 'LLM_API_ERROR'
    LLM_RATE_LIMITED = 'LLM_RATE_LIMITED'
    LLM_TIMEOUT = 'LLM_TIMEOUT'
    LLM_TOKEN_LIMIT_EXCEEDED = 'LLM_TOKEN_LIMIT_EXCEEDED'

    # Infrastructure errors
    DYNAMODB_ERROR = 'DYNAMODB_ERROR'
    S3_ERROR = 'S3_ERROR'
    INTERNAL_ERROR = 'INTERNAL_ERROR'
    NOT_IMPLEMENTED = 'NOT_IMPLEMENTED'
