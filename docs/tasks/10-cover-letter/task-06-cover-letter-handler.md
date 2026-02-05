# Task 10.6: Cover Letter Handler

**Status:** Pending
**Spec Reference:** [docs/specs/cover-letter/COVER_LETTER_SPEC.md](../../specs/cover-letter/COVER_LETTER_SPEC.md)
**Depends On:** Task 10.3 (Logic), Task 10.5 (FVS)
**Blocking:** Task 10.9 (Integration Tests)
**Complexity:** Medium
**Duration:** 2 hours
**Test File:** `tests/cover-letter/unit/test_cover_letter_handler_unit.py` (15-20 tests)

## Overview

Implement Lambda handler for cover letter generation. Follows synchronous pattern like cv_upload_handler.py with AWS Powertools decorators for observability.

## Todo

### Handler Implementation

- [ ] Create `src/backend/careervp/handlers/cover_letter_handler.py`
- [ ] Implement `lambda_handler()` with @logger, @tracer, @metrics
- [ ] Parse and validate request using Pydantic models
- [ ] Extract user_id from Cognito JWT
- [ ] Call cover letter logic layer
- [ ] Call FVS validation
- [ ] Map result codes to HTTP status codes
- [ ] Generate presigned download URL

### Test Implementation

- [ ] Create `tests/cover-letter/unit/test_cover_letter_handler_unit.py`
- [ ] Test handler success (200 OK)
- [ ] Test CV not found (404)
- [ ] Test VPR not found (400)
- [ ] Test FVS violation (400)
- [ ] Test LLM timeout (504)
- [ ] Test rate limit (429)
- [ ] Test authentication errors (401, 403)

---

## Codex Implementation Guide

### File Path

`src/backend/careervp/handlers/cover_letter_handler.py`

### Key Implementation

```python
"""
Lambda handler for cover letter generation.

Handles POST /api/cover-letter requests with:
- Cognito JWT authentication
- Request validation
- Cover letter generation
- FVS validation
- Error mapping to HTTP status codes
"""

import json
from typing import Any

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.metrics import MetricUnit
from pydantic import ValidationError

from careervp.models.cover_letter_models import (
    GenerateCoverLetterRequest,
    TailoredCoverLetterResponse,
)
from careervp.models.result import ResultCode
from careervp.logic.cover_letter_generator import generate_cover_letter
from careervp.logic.fvs_cover_letter import (
    create_fvs_baseline,
    validate_cover_letter,
)
from careervp.llm.llm_client import LLMClient
from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.handlers.utils.auth import extract_user_id
from careervp.handlers.utils.response import (
    success_response,
    error_response,
    generate_download_url,
)

logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Initialize clients
llm_client = LLMClient()
dal = DynamoDalHandler()


# Result code to HTTP status mapping
RESULT_CODE_TO_HTTP_STATUS = {
    ResultCode.COVER_LETTER_GENERATED_SUCCESS: 200,
    ResultCode.CV_NOT_FOUND: 404,
    ResultCode.JOB_NOT_FOUND: 404,
    ResultCode.VPR_NOT_FOUND: 400,
    ResultCode.FVS_HALLUCINATION_DETECTED: 400,
    ResultCode.CV_LETTER_GENERATION_TIMEOUT: 504,
    ResultCode.RATE_LIMIT_EXCEEDED: 429,
    ResultCode.INVALID_REQUEST: 400,
    ResultCode.UNAUTHORIZED: 401,
    ResultCode.FORBIDDEN: 403,
    ResultCode.INTERNAL_ERROR: 500,
}


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Handle cover letter generation request.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response with cover letter or error
    """
    try:
        # Step 1: Extract user_id from JWT
        user_id = extract_user_id(event)
        if not user_id:
            return error_response(
                status_code=401,
                code=ResultCode.UNAUTHORIZED,
                message="Authentication required",
            )

        logger.append_keys(user_id=user_id)

        # Step 2: Parse request body
        body = json.loads(event.get("body", "{}"))
        request = GenerateCoverLetterRequest(**body)

        logger.info(
            "Cover letter generation request",
            cv_id=request.cv_id,
            job_id=request.job_id,
            company=request.company_name,
        )

        # Step 3: Generate cover letter
        import asyncio
        result = asyncio.run(
            generate_cover_letter(
                request=request,
                user_id=user_id,
                llm_client=llm_client,
                dal=dal,
            )
        )

        if not result.success:
            status_code = RESULT_CODE_TO_HTTP_STATUS.get(result.code, 500)
            return error_response(
                status_code=status_code,
                code=result.code,
                message=result.error,
            )

        cover_letter = result.data

        # Step 4: Validate with FVS
        baseline = create_fvs_baseline(
            company_name=request.company_name,
            job_title=request.job_title,
        )
        fvs_result = validate_cover_letter(cover_letter.content, baseline)

        if fvs_result.has_critical_violations:
            logger.warning(
                "FVS validation failed",
                violations=[v.__dict__ for v in fvs_result.violations],
            )
            return error_response(
                status_code=400,
                code=ResultCode.FVS_HALLUCINATION_DETECTED,
                message="Cover letter contains factual errors",
                details={"violations": [v.__dict__ for v in fvs_result.violations]},
            )

        # Step 5: Save artifact
        await dal.save_cover_letter_artifact(cover_letter)

        # Step 6: Generate download URL
        download_url = generate_download_url(
            artifact_type="cover_letter",
            artifact_id=cover_letter.cover_letter_id,
        )

        # Step 7: Calculate quality score
        quality_score = (
            0.40 * cover_letter.personalization_score +
            0.35 * cover_letter.relevance_score +
            0.25 * cover_letter.tone_score
        )

        # Step 8: Record metrics
        metrics.add_metric(
            name="CoverLetterGenerated",
            unit=MetricUnit.Count,
            value=1,
        )
        metrics.add_metric(
            name="QualityScore",
            unit=MetricUnit.None_,
            value=quality_score,
        )

        # Step 9: Build response
        response = TailoredCoverLetterResponse(
            success=True,
            cover_letter=cover_letter,
            fvs_validation=fvs_result,
            quality_score=quality_score,
            code=ResultCode.COVER_LETTER_GENERATED_SUCCESS.value,
            processing_time_ms=int(context.get_remaining_time_in_millis()),
            cost_estimate=0.005,  # Haiku estimate
            download_url=download_url,
        )

        return success_response(
            status_code=200,
            body=response.model_dump(mode="json"),
        )

    except ValidationError as e:
        logger.warning("Request validation failed", errors=e.errors())
        return error_response(
            status_code=400,
            code=ResultCode.INVALID_REQUEST,
            message="Invalid request",
            details={"validation_errors": e.errors()},
        )

    except Exception as e:
        logger.exception("Unexpected error in cover letter handler")
        return error_response(
            status_code=500,
            code=ResultCode.INTERNAL_ERROR,
            message="Internal server error",
        )
```

---

## Test Implementation

### test_cover_letter_handler_unit.py

```python
"""Unit tests for cover letter handler."""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock

from careervp.handlers.cover_letter_handler import lambda_handler
from careervp.models.result import Result, ResultCode


class TestCoverLetterHandler:
    """Tests for cover letter Lambda handler."""

    @pytest.fixture
    def valid_event(self):
        """Valid API Gateway event."""
        return {
            "body": json.dumps({
                "cv_id": "cv_123",
                "job_id": "job_456",
                "company_name": "TechCorp",
                "job_title": "Senior Engineer",
            }),
            "requestContext": {
                "authorizer": {
                    "claims": {"sub": "user_789"}
                }
            },
        }

    @pytest.fixture
    def mock_context(self):
        """Mock Lambda context."""
        context = Mock()
        context.get_remaining_time_in_millis.return_value = 290000
        return context

    @patch("careervp.handlers.cover_letter_handler.generate_cover_letter")
    @patch("careervp.handlers.cover_letter_handler.validate_cover_letter")
    @patch("careervp.handlers.cover_letter_handler.dal")
    def test_handler_success(
        self, mock_dal, mock_fvs, mock_generate, valid_event, mock_context
    ):
        """Test successful cover letter generation."""
        # Arrange
        mock_generate.return_value = Result.success(
            data=Mock(
                cover_letter_id="cl_123",
                content="Cover letter content",
                personalization_score=0.8,
                relevance_score=0.8,
                tone_score=0.8,
            ),
            code=ResultCode.COVER_LETTER_GENERATED_SUCCESS,
        )
        mock_fvs.return_value = Mock(
            is_valid=True,
            has_critical_violations=False,
            violations=[],
        )

        # Act
        response = lambda_handler(valid_event, mock_context)

        # Assert
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["success"] is True

    @patch("careervp.handlers.cover_letter_handler.generate_cover_letter")
    def test_handler_cv_not_found(self, mock_generate, valid_event, mock_context):
        """Test handler when CV not found."""
        mock_generate.return_value = Result.failure(
            error="CV not found",
            code=ResultCode.CV_NOT_FOUND,
        )

        response = lambda_handler(valid_event, mock_context)

        assert response["statusCode"] == 404

    @patch("careervp.handlers.cover_letter_handler.generate_cover_letter")
    def test_handler_vpr_not_found(self, mock_generate, valid_event, mock_context):
        """Test handler when VPR not found."""
        mock_generate.return_value = Result.failure(
            error="VPR not found",
            code=ResultCode.VPR_NOT_FOUND,
        )

        response = lambda_handler(valid_event, mock_context)

        assert response["statusCode"] == 400

    @patch("careervp.handlers.cover_letter_handler.generate_cover_letter")
    @patch("careervp.handlers.cover_letter_handler.validate_cover_letter")
    def test_handler_fvs_violation(
        self, mock_fvs, mock_generate, valid_event, mock_context
    ):
        """Test handler when FVS validation fails."""
        mock_generate.return_value = Result.success(
            data=Mock(content="Bad content"),
            code=ResultCode.COVER_LETTER_GENERATED_SUCCESS,
        )
        mock_fvs.return_value = Mock(
            is_valid=False,
            has_critical_violations=True,
            violations=[Mock(__dict__={"field": "company_name"})],
        )

        response = lambda_handler(valid_event, mock_context)

        assert response["statusCode"] == 400

    @patch("careervp.handlers.cover_letter_handler.generate_cover_letter")
    def test_handler_timeout(self, mock_generate, valid_event, mock_context):
        """Test handler when LLM times out."""
        mock_generate.return_value = Result.failure(
            error="Timeout",
            code=ResultCode.CV_LETTER_GENERATION_TIMEOUT,
        )

        response = lambda_handler(valid_event, mock_context)

        assert response["statusCode"] == 504

    def test_handler_missing_auth(self, mock_context):
        """Test handler when authentication missing."""
        event = {
            "body": json.dumps({"cv_id": "cv_123"}),
            "requestContext": {},
        }

        response = lambda_handler(event, mock_context)

        assert response["statusCode"] == 401

    def test_handler_invalid_request(self, mock_context):
        """Test handler with invalid request body."""
        event = {
            "body": json.dumps({"invalid": "data"}),
            "requestContext": {
                "authorizer": {"claims": {"sub": "user_789"}}
            },
        }

        response = lambda_handler(event, mock_context)

        assert response["statusCode"] == 400

    def test_handler_empty_body(self, mock_context):
        """Test handler with empty body."""
        event = {
            "body": "{}",
            "requestContext": {
                "authorizer": {"claims": {"sub": "user_789"}}
            },
        }

        response = lambda_handler(event, mock_context)

        assert response["statusCode"] == 400
```

---

## Verification Commands

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Format
uv run ruff format careervp/handlers/cover_letter_handler.py

# Lint
uv run ruff check --fix careervp/handlers/cover_letter_handler.py

# Type check
uv run mypy careervp/handlers/cover_letter_handler.py --strict

# Run tests
uv run pytest tests/cover-letter/unit/test_cover_letter_handler_unit.py -v

# Expected: 19 tests PASSED
```

---

## Completion Criteria

- [ ] `lambda_handler()` implemented with all decorators
- [ ] Request parsing and validation working
- [ ] User authentication extraction working
- [ ] FVS validation integrated
- [ ] Error mapping to HTTP status codes
- [ ] All 19 tests passing
- [ ] ruff format passes
- [ ] mypy --strict passes

---

## Common Pitfalls

### Pitfall 1: Missing asyncio.run()
**Problem:** Calling async function without asyncio.run in sync handler.
**Solution:** Use `asyncio.run(generate_cover_letter(...))`.

### Pitfall 2: Not Handling ValidationError
**Problem:** Pydantic ValidationError crashes handler.
**Solution:** Catch ValidationError and return 400 with details.

---

## References

- [cv_upload_handler.py](../../../src/backend/careervp/handlers/cv_upload_handler.py) - Pattern reference
- [COVER_LETTER_SPEC.md](../../specs/cover-letter/COVER_LETTER_SPEC.md) - HTTP status mappings
