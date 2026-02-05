# Task 9.6: CV Tailoring - Lambda Handler

**Status:** Pending
**Spec Reference:** [docs/specs/04-cv-tailoring.md](../../specs/04-cv-tailoring.md)
**Depends On:** Task 9.1 (Validation), Task 9.2 (Infrastructure), Task 9.3 (Logic), Task 9.5 (FVS)
**Blocking:** Task 9.7, Task 9.8, Task 9.9

## Overview

Implement Lambda handler for the CV tailoring API endpoint. Uses AWS Powertools decorators for logging, tracing, and input validation. Orchestrates the flow from API request through validation, tailoring logic, and DAL persistence.

## Todo

### Handler Implementation

- [ ] Create `src/backend/careervp/handlers/cv_tailoring_handler.py`
- [ ] Implement `handler()` main entry point with Powertools decorators
- [ ] Implement request validation and parsing
- [ ] Implement error handling with proper HTTP status codes
- [ ] Implement response formatting and serialization
- [ ] Implement logging with structured context
- [ ] Implement X-Ray tracing integration

### Test Implementation

- [ ] Create `tests/handlers/test_tailoring_handler_unit.py`
- [ ] Implement 15-20 unit tests covering happy path and errors
- [ ] Test valid request handling (3 tests)
- [ ] Test validation error handling (4 tests)
- [ ] Test tailoring logic errors (3 tests)
- [ ] Test persistence errors (2 tests)
- [ ] Test response formatting (3 tests)

### Validation & Formatting

- [ ] Run `uv run ruff format src/backend/careervp/handlers/`
- [ ] Run `uv run ruff check --fix src/backend/careervp/handlers/`
- [ ] Run `uv run mypy src/backend/careervp/handlers/ --strict`
- [ ] Run `uv run pytest tests/handlers/test_tailoring_handler_unit.py -v`

### Commit

- [ ] Commit with message: `feat(handlers): implement CV tailoring Lambda handler with Powertools`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `src/backend/careervp/handlers/cv_tailoring_handler.py` | Lambda handler implementation |
| `tests/handlers/test_tailoring_handler_unit.py` | Unit tests for handler |

### Key Implementation Details

```python
"""
CV Tailoring Lambda Handler.
Per docs/specs/04-cv-tailoring.md API Schema.

Endpoint: POST /api/cv-tailoring
Timeout: 60 seconds
Memory: 3 GB

Uses AWS Powertools for:
- Logging with structured context
- X-Ray tracing of all calls
- Input validation with models
- Error handling and transformation

Request/Response flow:
1. Parse and validate TailorCVRequest
2. Load user CV from DAL
3. Load job posting from database
4. Load company research from Phase 8
5. Call tailoring logic
6. Handle FVS validation errors with retries
7. Persist tailored CV artifact
8. Return TailorCVResponse with proper status code
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.data_classes.api_gateway_event import APIGatewayProxyEvent
from aws_lambda_powertools.utilities.data_classes.api_gateway_event import APIGatewayProxyEventV2
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.validation import validate

from careervp.handlers.utils.observability import logger, tracer
from careervp.handlers.utils.validation import (
    validate_file_size,
    validate_text_length,
    validate_job_description,
    validate_cv_metadata,
)
from careervp.logic.cv_tailor import tailor_cv
from careervp.models.result import ResultCode
from careervp.models.tailor import TailorCVRequest, TailorCVResponse, TailoredCVData

if TYPE_CHECKING:
    from careervp.dal.dynamo_dal_handler import DynamoDalHandler
    from careervp.models.cv import UserCV
    from careervp.models.job import CompanyContext, JobPosting


# Powertools instances
logger = Logger()
tracer = Tracer()


@tracer.capture_lambda_handler
@logger.inject_lambda_context(clear_state=True)
def handler(event: APIGatewayProxyEvent | APIGatewayProxyEventV2, context: LambdaContext) -> dict[str, Any]:
    """
    Lambda handler for CV tailoring endpoint.

    Endpoint: POST /api/cv-tailoring
    Request body: TailorCVRequest
    Response: TailorCVResponse

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        Dict with statusCode and body (JSON response)

    Example request:
        POST /api/cv-tailoring
        {
            "user_id": "user_123",
            "application_id": "app_456",
            "job_id": "job_789",
            "cv_version": 1,
            "include_gap_analysis": false,
            "style_preferences": {
                "tone": "professional",
                "formality_level": "high"
            }
        }

    Example successful response (200):
        {
            "success": true,
            "code": "CV_TAILORED",
            "data": {
                "tailored_cv": {...},
                "metadata": {...},
                "token_usage": {...}
            }
        }

    Example error response (400):
        {
            "success": false,
            "code": "VALIDATION_ERROR",
            "error": "job_id is required"
        }

    Example error response (500):
        {
            "success": false,
            "code": "CV_TAILORING_FAILED",
            "error": "Failed to tailor CV: ..."
        }
    """
    # PSEUDO-CODE:
    # try:
    #     # Step 1: Parse request
    #     request_dict = json.loads(event['body'])
    #     logger.append_keys(request_dict.get('user_id', 'unknown'))
    #     logger.info("received CV tailoring request")
    #
    #     # Step 2: Validate request model
    #     try:
    #         request = TailorCVRequest(**request_dict)
    #     except ValidationError as exc:
    #         logger.warning("request validation failed", errors=exc.errors())
    #         return _error_response(
    #             status_code=400,
    #             error="Validation failed: " + str(exc),
    #             code=ResultCode.VALIDATION_ERROR,
    #         )
    #
    #     # Step 3: Load required data from DAL
    #     dal = DynamoDalHandler()
    #
    #     user_cv_result = dal.get_user_cv(request.user_id, request.cv_version)
    #     if not user_cv_result.success:
    #         logger.error("CV not found", error=user_cv_result.error)
    #         return _error_response(400, "CV not found", ResultCode.CV_NOT_FOUND)
    #     user_cv = user_cv_result.data
    #
    #     job_posting_result = dal.get_job_posting(request.job_id)
    #     if not job_posting_result.success:
    #         logger.error("Job not found", error=job_posting_result.error)
    #         return _error_response(400, "Job not found", ResultCode.JOB_NOT_FOUND)
    #     job_posting = job_posting_result.data
    #
    #     # Phase 8 integration: Load company research
    #     company_research_result = dal.get_company_research(job_posting.company_id)
    #     if not company_research_result.success:
    #         logger.warning("company research not found", job_id=request.job_id)
    #         company_research = None
    #     else:
    #         company_research = company_research_result.data
    #
    #     # Step 4: Validate inputs
    #     validation_results = [
    #         validate_cv_metadata(user_cv, request.cv_version),
    #         validate_job_description(job_posting),
    #     ]
    #
    #     for result in validation_results:
    #         if not result.success:
    #             logger.warning("validation failed", error=result.error)
    #             return _error_response(400, result.error, ResultCode.VALIDATION_ERROR)
    #
    #     # Step 5: Call tailoring logic
    #     gap_analysis = None
    #     if request.include_gap_analysis:
    #         # Phase 11: Load gap analysis
    #         gap_result = dal.get_gap_analysis(request.user_id)
    #         gap_analysis = gap_result.data if gap_result.success else None
    #
    #     tailoring_result = tailor_cv(
    #         request=request,
    #         user_cv=user_cv,
    #         job_posting=job_posting,
    #         company_research=company_research or {},
    #         dal=dal,
    #         gap_analysis=gap_analysis,
    #     )
    #
    #     if not tailoring_result.success:
    #         logger.error("tailoring failed", error=tailoring_result.error)
    #         return _error_response(
    #             status_code=500,
    #             error=tailoring_result.error,
    #             code=tailoring_result.code,
    #         )
    #
    #     # Step 6: Build response
    #     response = TailorCVResponse(
    #         success=True,
    #         code=ResultCode.CV_TAILORED,
    #         data=tailoring_result.data,
    #     )
    #
    #     logger.info(
    #         "CV tailoring completed successfully",
    #         application_id=request.application_id,
    #     )
    #
    #     return _success_response(response)
    #
    # except Exception as exc:
    #     logger.exception("unexpected handler error")
    #     return _error_response(
    #         status_code=500,
    #         error=f"Internal server error: {str(exc)}",
    #         code=ResultCode.INTERNAL_ERROR,
    #     )

    pass


def _success_response(response: TailorCVResponse) -> dict[str, Any]:
    """
    Format successful response.

    Args:
        response: TailorCVResponse model

    Returns:
        Dict with statusCode 200 and JSON body

    Example:
        >>> response = TailorCVResponse(success=True, data=...)
        >>> result = _success_response(response)
        >>> assert result['statusCode'] == 200
        >>> assert 'body' in result
    """
    # PSEUDO-CODE:
    # return {
    #     'statusCode': 200,
    #     'headers': {
    #         'Content-Type': 'application/json',
    #         'X-Request-Id': logger.context.get('request_id', 'unknown'),
    #     },
    #     'body': response.model_dump_json(),
    # }

    pass


def _error_response(
    status_code: int,
    error: str,
    code: str,
    details: dict | None = None,
) -> dict[str, Any]:
    """
    Format error response.

    Args:
        status_code: HTTP status code
        error: Human-readable error message
        code: Machine-readable result code
        details: Optional additional error details

    Returns:
        Dict with statusCode and JSON error body

    Example:
        >>> result = _error_response(400, "Validation failed", "VALIDATION_ERROR")
        >>> assert result['statusCode'] == 400
    """
    # PSEUDO-CODE:
    # response = TailorCVResponse(
    #     success=False,
    #     error=error,
    #     code=code,
    #     details=details,
    # )
    #
    # return {
    #     'statusCode': status_code,
    #     'headers': {
    #         'Content-Type': 'application/json',
    #         'X-Request-Id': logger.context.get('request_id', 'unknown'),
    #     },
    #     'body': response.model_dump_json(),
    # }

    pass
```

### Test Implementation Structure

```python
"""
Unit Tests for CV Tailoring Handler.
Per tests/handlers/test_tailoring_handler_unit.py.

Test categories:
- Valid request handling (3 tests)
- Validation errors (4 tests)
- Tailoring errors (3 tests)
- Persistence errors (2 tests)
- Response formatting (3 tests)

Total: 15-20 tests
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock

from careervp.handlers.cv_tailoring_handler import handler, _success_response, _error_response
from careervp.models.tailor import TailorCVResponse


class TestValidRequests:
    """Test successful request handling."""

    def test_handler_processes_valid_request(self):
        """Handler processes valid request successfully."""
        # PSEUDO-CODE:
        # event = {
        #     'body': json.dumps({
        #         'user_id': 'user_123',
        #         'application_id': 'app_456',
        #         'job_id': 'job_789',
        #         'cv_version': 1,
        #     }),
        # }
        # context = Mock(LambdaContext)
        #
        # with patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler') as mock_dal:
        #     mock_dal.get_user_cv.return_value = Result(success=True, data=Mock())
        #     mock_dal.get_job_posting.return_value = Result(success=True, data=Mock())
        #     mock_dal.get_company_research.return_value = Result(success=True, data=Mock())
        #     
        #     with patch('careervp.handlers.cv_tailoring_handler.tailor_cv') as mock_tailor:
        #         mock_tailor.return_value = Result(
        #             success=True,
        #             data=Mock(),
        #             code='CV_TAILORED'
        #         )
        #         
        #         response = handler(event, context)
        #         assert response['statusCode'] == 200
        pass

    def test_handler_returns_tailored_cv_data(self):
        """Handler returns tailored CV data in response."""
        # PSEUDO-CODE:
        # event = {...}
        # response = handler(event, context)
        # body = json.loads(response['body'])
        # assert body['success']
        # assert body['data']['tailored_cv']
        # assert body['data']['metadata']
        pass

    def test_handler_includes_token_usage(self):
        """Handler includes LLM token usage in response."""
        # PSEUDO-CODE:
        # response = handler(event, context)
        # body = json.loads(response['body'])
        # assert 'token_usage' in body['data']
        # assert 'input_tokens' in body['data']['token_usage']
        pass


class TestValidationErrors:
    """Test validation error handling."""

    def test_handler_validates_request_schema(self):
        """Handler validates TailorCVRequest schema."""
        # PSEUDO-CODE:
        # event = {
        #     'body': json.dumps({
        #         # Missing required fields
        #         'user_id': 'user_123',
        #     }),
        # }
        # response = handler(event, context)
        # assert response['statusCode'] == 400
        # body = json.loads(response['body'])
        # assert not body['success']
        pass

    def test_handler_rejects_invalid_json(self):
        """Handler rejects invalid JSON in request body."""
        # PSEUDO-CODE:
        # event = {'body': '{invalid json}'}
        # response = handler(event, context)
        # assert response['statusCode'] in [400, 500]
        pass

    def test_handler_validates_cv_exists(self):
        """Handler validates CV exists before tailoring."""
        # PSEUDO-CODE:
        # event = {...valid request...}
        # with patch as mock_dal:
        #     mock_dal.get_user_cv.return_value = Result(success=False, error="Not found")
        #     response = handler(event, context)
        #     assert response['statusCode'] == 400
        #     assert "not found" in response['body'].lower()
        pass

    def test_handler_validates_job_exists(self):
        """Handler validates job posting exists."""
        # PSEUDO-CODE:
        # event = {...}
        # with patch as mock_dal:
        #     mock_dal.get_user_cv.return_value = Result(success=True, data=Mock())
        #     mock_dal.get_job_posting.return_value = Result(success=False, error="Not found")
        #     response = handler(event, context)
        #     assert response['statusCode'] == 400
        pass


class TestTailoringErrors:
    """Test tailoring logic error handling."""

    def test_handler_handles_tailoring_failure(self):
        """Handler handles tailoring logic failure."""
        # PSEUDO-CODE:
        # event = {...}
        # with patch as mock_tailor:
        #     mock_tailor.return_value = Result(
        #         success=False,
        #         error="FVS validation failed",
        #         code="CV_TAILORING_FAILED"
        #     )
        #     response = handler(event, context)
        #     assert response['statusCode'] == 500
        pass

    def test_handler_handles_fvs_validation_error(self):
        """Handler handles FVS validation errors."""
        # PSEUDO-CODE:
        # event = {...}
        # with patch as mock_tailor:
        #     mock_tailor.return_value = Result(
        #         success=False,
        #         error="Hallucinated skill: Kubernetes",
        #         code="FVS_HALLUCINATION_DETECTED"
        #     )
        #     response = handler(event, context)
        #     body = json.loads(response['body'])
        #     assert "hallucinated" in body['error'].lower()
        pass

    def test_handler_handles_llm_timeout(self):
        """Handler handles LLM timeout gracefully."""
        # PSEUDO-CODE:
        # event = {...}
        # with patch as mock_tailor:
        #     mock_tailor.return_value = Result(
        #         success=False,
        #         error="Request timeout after 60s",
        #         code="TIMEOUT_ERROR"
        #     )
        #     response = handler(event, context)
        #     assert response['statusCode'] == 500
        pass


class TestPersistenceErrors:
    """Test persistence error handling."""

    def test_handler_warns_on_persistence_failure(self):
        """Handler continues on persistence failure."""
        # PSEUDO-CODE:
        # event = {...}
        # with patch as mock_dal:
        #     mock_dal.save_tailored_cv.return_value = Result(
        #         success=False,
        #         error="DynamoDB error"
        #     )
        #     response = handler(event, context)
        #     # Should still return 200 (data was generated)
        #     assert response['statusCode'] == 200
        pass

    def test_handler_includes_persistence_warning_in_logs(self):
        """Handler logs persistence warnings."""
        # PSEUDO-CODE:
        # event = {...}
        # with patch as mock_dal, patch as mock_logger:
        #     mock_dal.save_tailored_cv.return_value = Result(success=False)
        #     response = handler(event, context)
        #     mock_logger.warning.assert_called()
        pass


class TestResponseFormatting:
    """Test response formatting."""

    def test_success_response_has_correct_status(self):
        """Success response has 200 status code."""
        # PSEUDO-CODE:
        # response = TailorCVResponse(success=True, data=Mock())
        # result = _success_response(response)
        # assert result['statusCode'] == 200
        pass

    def test_success_response_has_json_body(self):
        """Success response body is valid JSON."""
        # PSEUDO-CODE:
        # response = TailorCVResponse(success=True, data=Mock())
        # result = _success_response(response)
        # body = json.loads(result['body'])
        # assert body['success']
        pass

    def test_error_response_includes_error_message(self):
        """Error response includes human-readable error."""
        # PSEUDO-CODE:
        # result = _error_response(400, "Invalid input", "VALIDATION_ERROR")
        # body = json.loads(result['body'])
        # assert body['error'] == "Invalid input"
        # assert body['code'] == "VALIDATION_ERROR"
        pass
```

### Verification Commands

```bash
# Format code
uv run ruff format src/backend/careervp/handlers/

# Check for style issues
uv run ruff check --fix src/backend/careervp/handlers/

# Type check with strict mode
uv run mypy src/backend/careervp/handlers/ --strict

# Run handler tests
uv run pytest tests/handlers/test_tailoring_handler_unit.py -v

# Expected output:
# ===== test session starts =====
# tests/handlers/test_tailoring_handler_unit.py::TestValidRequests PASSED (3 tests)
# tests/handlers/test_tailoring_handler_unit.py::TestValidationErrors PASSED (4 tests)
# ... [15-20 total tests]
# ===== 15-20 passed in X.XXs =====
```

### Expected Test Results

```
tests/handlers/test_tailoring_handler_unit.py PASSED

Valid Requests: 3 PASSED
- Processes valid request
- Returns tailored CV data
- Includes token usage

Validation Errors: 4 PASSED
- Validates request schema
- Rejects invalid JSON
- Validates CV exists
- Validates job exists

Tailoring Errors: 3 PASSED
- Handles tailoring failure
- Handles FVS validation errors
- Handles LLM timeout

Persistence Errors: 2 PASSED
- Continues on persistence failure
- Logs persistence warnings

Response Formatting: 3 PASSED
- Success response correct status
- Success response valid JSON
- Error response includes message

Total: 15-20 tests passing
Type checking: 0 errors, 0 warnings
HTTP Response codes: Correct for all scenarios
```

### Zero-Hallucination Checklist

- [ ] Request validation enforced via TailorCVRequest model
- [ ] All required data loaded before tailoring
- [ ] FVS validation errors handled appropriately
- [ ] Error responses include machine-readable codes
- [ ] Logging includes structured context (user_id, application_id)
- [ ] X-Ray tracing enabled for all calls
- [ ] Response models properly serialized
- [ ] HTTP status codes match error types
- [ ] Persistence failures don't fail the entire request
- [ ] Phase 8 company research integration optional

### Acceptance Criteria

- [ ] Handler accepts POST /api/cv-tailoring requests
- [ ] Validates TailorCVRequest schema
- [ ] Loads CV, job, and company research from DAL
- [ ] Calls tailoring logic with correct parameters
- [ ] Returns TailorCVResponse with proper structure
- [ ] HTTP 200 on success with tailored CV data
- [ ] HTTP 400 on validation errors
- [ ] HTTP 500 on tailoring failures
- [ ] Logging with Powertools includes structured context
- [ ] X-Ray tracing enabled for observability
- [ ] 15-20 unit tests all passing
- [ ] Type checking passes with `mypy --strict`

---

### Verification & Compliance

1. Run `python src/backend/scripts/validate_naming.py --path src/backend/careervp/handlers --strict`
2. Run `uv run ruff format . && uv run ruff check --fix . && uv run mypy --strict .`
3. Run `uv run pytest tests/handlers/test_tailoring_handler_unit.py -v --cov`
4. If any handler logic is incorrect, report a **BLOCKING ISSUE** and exit.
