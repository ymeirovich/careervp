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

    @property
    def message(self) -> str:
        """Alias for error to support legacy message access."""
        return self.error or ''

    @classmethod  # type: ignore[no-redef]
    def success(cls, data: T | None = None, code: str | None = None) -> 'Result[T]':
        """Helper to construct a success Result."""
        return cls(success=True, data=data, error=None, code=code or ResultCode.SUCCESS)

    @classmethod  # type: ignore[no-redef]
    def error(  # noqa: F811
        cls,
        code: str,
        message: str,
        data: T | None = None,
    ) -> 'Result[T]':
        """Helper to construct an error Result."""
        return cls(success=False, data=data, error=message, code=code)


# Common result codes for consistency
class ResultCode:
    """Standard result codes used across the application."""

    # Success codes
    SUCCESS = 'SUCCESS'
    CV_PARSED = 'CV_PARSED'
    VPR_GENERATED = 'VPR_GENERATED'
    CV_TAILORED = 'CV_TAILORED'
    CV_TAILORED_SUCCESS = 'CV_TAILORED_SUCCESS'
    COVER_LETTER_GENERATED = 'COVER_LETTER_GENERATED'
    COMPANY_RESEARCHED = 'COMPANY_RESEARCHED'
    SCRAPE_FAILED = 'SCRAPE_FAILED'
    SEARCH_FAILED = 'SEARCH_FAILED'
    ALL_SOURCES_FAILED = 'ALL_SOURCES_FAILED'
    NO_RESULTS = 'NO_RESULTS'
    TIMEOUT = 'TIMEOUT'
    RESEARCH_COMPLETE = 'RESEARCH_COMPLETE'
    GAP_QUESTIONS_GENERATED = 'GAP_QUESTIONS_GENERATED'
    GAP_RESPONSES_SAVED = 'GAP_RESPONSES_SAVED'
    INTERVIEW_QUESTIONS_GENERATED = 'INTERVIEW_QUESTIONS_GENERATED'
    INTERVIEW_REPORT_GENERATED = 'INTERVIEW_REPORT_GENERATED'

    # Validation errors
    FVS_VALIDATION_FAILED = 'FVS_VALIDATION_FAILED'
    FVS_DATE_MISMATCH = 'FVS_DATE_MISMATCH'
    FVS_ROLE_MISMATCH = 'FVS_ROLE_MISMATCH'
    FVS_HALLUCINATION_DETECTED = 'FVS_HALLUCINATION_DETECTED'
    FVS_VIOLATION_DETECTED = 'FVS_VIOLATION_DETECTED'

    VALIDATION_SUCCESS = 'VALIDATION_SUCCESS'
    VALIDATION_ERROR = 'VALIDATION_ERROR'
    VALIDATION_FILE_SIZE_EXCEEDED = 'VALIDATION_FILE_SIZE_EXCEEDED'
    VALIDATION_TEXT_TOO_LONG = 'VALIDATION_TEXT_TOO_LONG'
    VALIDATION_TEXT_TOO_SHORT = 'VALIDATION_TEXT_TOO_SHORT'
    VALIDATION_JOB_DESCRIPTION_TOO_SHORT = 'VALIDATION_JOB_DESCRIPTION_TOO_SHORT'
    VALIDATION_JOB_DESCRIPTION_TOO_LONG = 'VALIDATION_JOB_DESCRIPTION_TOO_LONG'
    VALIDATION_JOB_DESCRIPTION_EMPTY = 'VALIDATION_JOB_DESCRIPTION_EMPTY'
    VALIDATION_INVALID_CV_ID = 'VALIDATION_INVALID_CV_ID'
    VALIDATION_INVALID_TONE = 'VALIDATION_INVALID_TONE'
    VALIDATION_INVALID_TARGET_LENGTH = 'VALIDATION_INVALID_TARGET_LENGTH'
    VALIDATION_TOO_MANY_EMPHASIS_AREAS = 'VALIDATION_TOO_MANY_EMPHASIS_AREAS'
    VALIDATION_MISSING_REQUIRED_FIELD = 'VALIDATION_MISSING_REQUIRED_FIELD'

    # Input errors
    INVALID_INPUT = 'INVALID_INPUT'
    INVALID_JSON = 'INVALID_JSON'
    MISSING_REQUIRED_FIELD = 'MISSING_REQUIRED_FIELD'
    UNSUPPORTED_FILE_FORMAT = 'UNSUPPORTED_FILE_FORMAT'
    JOB_BOARD_URL_REJECTED = 'JOB_BOARD_URL_REJECTED'
    CV_NOT_FOUND = 'CV_NOT_FOUND'
    FORBIDDEN = 'FORBIDDEN'
    UNAUTHORIZED = 'UNAUTHORIZED'
    RATE_LIMIT_EXCEEDED = 'RATE_LIMIT_EXCEEDED'
    INSUFFICIENT_CV_DATA = 'INSUFFICIENT_CV_DATA'
    PARSE_ERROR = 'PARSE_ERROR'

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
