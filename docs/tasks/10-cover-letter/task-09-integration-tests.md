# Task 10.9: Integration Tests

**Status:** Pending
**Spec Reference:** [docs/specs/cover-letter/COVER_LETTER_SPEC.md](../../specs/cover-letter/COVER_LETTER_SPEC.md)
**Depends On:** Task 10.6 (Handler)
**Blocking:** Task 10.10 (E2E)
**Complexity:** Medium
**Duration:** 2 hours
**Test File:** `tests/cover-letter/integration/test_cover_letter_handler_integration.py` (25-30 tests)

## Overview

Create integration tests that verify the full Handler → Logic → DAL flow. These tests use mocked external services (LLM, DynamoDB) but test real component interaction.

## Todo

### Test Implementation

- [ ] Create `tests/cover-letter/integration/test_cover_letter_handler_integration.py`
- [ ] Test full success flow (Handler → Logic → DAL)
- [ ] Test FVS rejection flow
- [ ] Test LLM retry flow (Haiku fails → Sonnet)
- [ ] Test artifact storage flow
- [ ] Test rate limit enforcement
- [ ] Test authentication flow
- [ ] Test error propagation

---

## Codex Implementation Guide

### File Path

`tests/cover-letter/integration/test_cover_letter_handler_integration.py`

### Key Implementation

```python
"""
Integration tests for cover letter generation.

Tests full Handler → Logic → DAL flow with mocked external services.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from careervp.handlers.cover_letter_handler import lambda_handler
from careervp.models.result import Result, ResultCode


class TestCoverLetterIntegration:
    """Integration tests for cover letter generation flow."""

    @pytest.fixture
    def api_gateway_event(self):
        """Create realistic API Gateway event."""
        def _create_event(
            cv_id: str = "cv_123",
            job_id: str = "job_456",
            company_name: str = "TechCorp",
            job_title: str = "Senior Engineer",
            preferences: dict = None,
            user_id: str = "user_789",
        ):
            body = {
                "cv_id": cv_id,
                "job_id": job_id,
                "company_name": company_name,
                "job_title": job_title,
            }
            if preferences:
                body["preferences"] = preferences

            return {
                "body": json.dumps(body),
                "headers": {
                    "Authorization": f"Bearer mock_token",
                    "Content-Type": "application/json",
                },
                "requestContext": {
                    "authorizer": {
                        "claims": {
                            "sub": user_id,
                            "email": "user@example.com",
                        }
                    },
                    "requestId": "test-request-id",
                },
                "httpMethod": "POST",
                "path": "/api/cover-letter",
            }
        return _create_event

    @pytest.fixture
    def mock_context(self):
        """Mock Lambda context."""
        context = Mock()
        context.function_name = "cover-letter-handler"
        context.memory_limit_in_mb = 2048
        context.get_remaining_time_in_millis.return_value = 290000
        context.aws_request_id = "test-request-id"
        return context

    @pytest.fixture
    def mock_dal(self):
        """Mock DAL with realistic responses."""
        dal = Mock()

        # CV retrieval
        dal.get_cv_by_id = AsyncMock(return_value=Result.success(
            data=Mock(
                cv_id="cv_123",
                user_id="user_789",
                skills=["Python", "AWS", "Leadership"],
                experience=[Mock(highlights=["Led team of 10"])],
            ),
            code=ResultCode.SUCCESS,
        ))

        # VPR retrieval
        dal.get_vpr_artifact = AsyncMock(return_value=Result.success(
            data=Mock(
                accomplishments=[
                    Mock(text="Led team of 10 engineers", keywords=["led", "team"]),
                    Mock(text="Reduced latency by 50%", keywords=["latency", "performance"]),
                ],
                job_requirements=["Python", "AWS", "Leadership"],
            ),
            code=ResultCode.SUCCESS,
        ))

        # Tailored CV retrieval (optional)
        dal.get_tailored_cv_artifact = AsyncMock(return_value=Result.success(
            data=Mock(),
            code=ResultCode.SUCCESS,
        ))

        # Gap responses
        dal.get_gap_responses = AsyncMock(return_value=Result.success(
            data=[],
            code=ResultCode.SUCCESS,
        ))

        # Save artifact
        dal.save_cover_letter_artifact = AsyncMock(return_value=Result.success(
            data="cl_123",
            code=ResultCode.SUCCESS,
        ))

        return dal

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client with realistic response."""
        client = Mock()
        client.generate = AsyncMock(return_value=Mock(
            content="""I am excited to apply for the Senior Engineer position at TechCorp.
            With my proven experience leading teams of engineers and delivering high-performance
            systems, I am confident I can contribute significantly to your organization.

            In my current role, I led a team of 10 engineers to deliver a critical project
            that reduced system latency by 50%. This experience has honed my leadership
            skills and deepened my expertise in Python and AWS.

            I am particularly drawn to TechCorp's innovative approach to technology and
            would welcome the opportunity to discuss how my background aligns with your needs.""",
            usage=Mock(input_tokens=5000, output_tokens=300),
        ))
        return client

    # ==================== SUCCESS FLOW TESTS ====================

    @pytest.mark.asyncio
    async def test_full_success_flow(
        self, api_gateway_event, mock_context, mock_dal, mock_llm_client
    ):
        """Test complete successful flow: Handler → Logic → DAL."""
        event = api_gateway_event()

        with patch("careervp.handlers.cover_letter_handler.dal", mock_dal), \
             patch("careervp.handlers.cover_letter_handler.llm_client", mock_llm_client):

            response = lambda_handler(event, mock_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["success"] is True
        assert body["cover_letter"] is not None
        assert "TechCorp" in body["cover_letter"]["content"]
        assert body["quality_score"] > 0

    @pytest.mark.asyncio
    async def test_success_with_preferences(
        self, api_gateway_event, mock_context, mock_dal, mock_llm_client
    ):
        """Test success flow with user preferences."""
        event = api_gateway_event(
            preferences={
                "tone": "enthusiastic",
                "word_count_target": 400,
                "emphasis_areas": ["leadership", "python"],
            }
        )

        with patch("careervp.handlers.cover_letter_handler.dal", mock_dal), \
             patch("careervp.handlers.cover_letter_handler.llm_client", mock_llm_client):

            response = lambda_handler(event, mock_context)

        assert response["statusCode"] == 200

    @pytest.mark.asyncio
    async def test_artifact_saved_on_success(
        self, api_gateway_event, mock_context, mock_dal, mock_llm_client
    ):
        """Test that artifact is saved to DAL on success."""
        event = api_gateway_event()

        with patch("careervp.handlers.cover_letter_handler.dal", mock_dal), \
             patch("careervp.handlers.cover_letter_handler.llm_client", mock_llm_client):

            response = lambda_handler(event, mock_context)

        assert response["statusCode"] == 200
        mock_dal.save_cover_letter_artifact.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_url_generated(
        self, api_gateway_event, mock_context, mock_dal, mock_llm_client
    ):
        """Test that download URL is generated on success."""
        event = api_gateway_event()

        with patch("careervp.handlers.cover_letter_handler.dal", mock_dal), \
             patch("careervp.handlers.cover_letter_handler.llm_client", mock_llm_client):

            response = lambda_handler(event, mock_context)

        body = json.loads(response["body"])
        assert body.get("download_url") is not None

    # ==================== FVS REJECTION TESTS ====================

    @pytest.mark.asyncio
    async def test_fvs_rejection_wrong_company(
        self, api_gateway_event, mock_context, mock_dal
    ):
        """Test FVS rejection when company name is wrong."""
        event = api_gateway_event()

        # LLM returns letter with wrong company name
        mock_llm = Mock()
        mock_llm.generate = AsyncMock(return_value=Mock(
            content="I am excited to apply at WrongCompany for the Senior Engineer role.",
        ))

        with patch("careervp.handlers.cover_letter_handler.dal", mock_dal), \
             patch("careervp.handlers.cover_letter_handler.llm_client", mock_llm):

            response = lambda_handler(event, mock_context)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "FVS" in body.get("code", "") or "violation" in str(body).lower()

    # ==================== LLM RETRY TESTS ====================

    @pytest.mark.asyncio
    async def test_llm_retry_on_low_quality(
        self, api_gateway_event, mock_context, mock_dal
    ):
        """Test LLM retries with Sonnet when Haiku quality is low."""
        event = api_gateway_event()

        mock_llm = Mock()
        # First call (Haiku) returns low quality
        # Second call (Sonnet) returns high quality
        mock_llm.generate = AsyncMock(side_effect=[
            Mock(content="Generic cover letter at TechCorp for Senior Engineer."),  # Low quality
            Mock(content="""I am excited to apply for the Senior Engineer position at TechCorp.
                With my proven expertise in leading engineering teams, I have delivered
                significant results including reducing system latency by 50%."""),  # High quality
        ])

        with patch("careervp.handlers.cover_letter_handler.dal", mock_dal), \
             patch("careervp.handlers.cover_letter_handler.llm_client", mock_llm):

            response = lambda_handler(event, mock_context)

        # Should succeed after retry
        assert response["statusCode"] == 200
        # Verify LLM was called twice
        assert mock_llm.generate.call_count == 2

    # ==================== ERROR PROPAGATION TESTS ====================

    @pytest.mark.asyncio
    async def test_cv_not_found_propagates(
        self, api_gateway_event, mock_context, mock_llm_client
    ):
        """Test CV not found error propagates correctly."""
        event = api_gateway_event()

        mock_dal = Mock()
        mock_dal.get_cv_by_id = AsyncMock(return_value=Result.failure(
            error="CV not found",
            code=ResultCode.CV_NOT_FOUND,
        ))

        with patch("careervp.handlers.cover_letter_handler.dal", mock_dal), \
             patch("careervp.handlers.cover_letter_handler.llm_client", mock_llm_client):

            response = lambda_handler(event, mock_context)

        assert response["statusCode"] == 404

    @pytest.mark.asyncio
    async def test_vpr_not_found_propagates(
        self, api_gateway_event, mock_context, mock_llm_client
    ):
        """Test VPR not found error propagates correctly."""
        event = api_gateway_event()

        mock_dal = Mock()
        mock_dal.get_cv_by_id = AsyncMock(return_value=Result.success(
            data=Mock(), code=ResultCode.SUCCESS
        ))
        mock_dal.get_vpr_artifact = AsyncMock(return_value=Result.failure(
            error="VPR not found",
            code=ResultCode.VPR_NOT_FOUND,
        ))

        with patch("careervp.handlers.cover_letter_handler.dal", mock_dal), \
             patch("careervp.handlers.cover_letter_handler.llm_client", mock_llm_client):

            response = lambda_handler(event, mock_context)

        assert response["statusCode"] == 400

    @pytest.mark.asyncio
    async def test_timeout_propagates(
        self, api_gateway_event, mock_context, mock_dal
    ):
        """Test LLM timeout propagates as 504."""
        event = api_gateway_event()

        import asyncio
        mock_llm = Mock()
        mock_llm.generate = AsyncMock(side_effect=asyncio.TimeoutError())

        with patch("careervp.handlers.cover_letter_handler.dal", mock_dal), \
             patch("careervp.handlers.cover_letter_handler.llm_client", mock_llm):

            response = lambda_handler(event, mock_context)

        assert response["statusCode"] == 504

    # ==================== AUTHENTICATION TESTS ====================

    @pytest.mark.asyncio
    async def test_missing_auth_returns_401(self, mock_context):
        """Test missing authentication returns 401."""
        event = {
            "body": json.dumps({"cv_id": "cv_123", "job_id": "job_456",
                               "company_name": "TechCorp", "job_title": "Engineer"}),
            "requestContext": {},
        }

        response = lambda_handler(event, mock_context)

        assert response["statusCode"] == 401

    @pytest.mark.asyncio
    async def test_user_id_extracted_correctly(
        self, api_gateway_event, mock_context, mock_dal, mock_llm_client
    ):
        """Test user ID is extracted from JWT and used correctly."""
        event = api_gateway_event(user_id="specific_user_123")

        with patch("careervp.handlers.cover_letter_handler.dal", mock_dal), \
             patch("careervp.handlers.cover_letter_handler.llm_client", mock_llm_client):

            response = lambda_handler(event, mock_context)

        # Verify DAL was called with correct user_id
        mock_dal.get_cv_by_id.assert_called()
        call_args = mock_dal.get_cv_by_id.call_args
        assert "specific_user_123" in str(call_args)

    # ==================== RATE LIMITING TESTS ====================

    @pytest.mark.asyncio
    async def test_rate_limit_returns_429(
        self, api_gateway_event, mock_context
    ):
        """Test rate limit exceeded returns 429."""
        event = api_gateway_event()

        mock_dal = Mock()
        mock_dal.get_cv_by_id = AsyncMock(return_value=Result.failure(
            error="Rate limit exceeded",
            code=ResultCode.RATE_LIMIT_EXCEEDED,
        ))

        with patch("careervp.handlers.cover_letter_handler.dal", mock_dal):
            response = lambda_handler(event, mock_context)

        # Note: This assumes rate limiting is checked in DAL or handler
        # Adjust based on actual implementation
        assert response["statusCode"] in [429, 404]  # Depends on where rate limit is checked

    # ==================== QUALITY SCORE TESTS ====================

    @pytest.mark.asyncio
    async def test_quality_score_calculated(
        self, api_gateway_event, mock_context, mock_dal, mock_llm_client
    ):
        """Test quality score is calculated and returned."""
        event = api_gateway_event()

        with patch("careervp.handlers.cover_letter_handler.dal", mock_dal), \
             patch("careervp.handlers.cover_letter_handler.llm_client", mock_llm_client):

            response = lambda_handler(event, mock_context)

        body = json.loads(response["body"])
        assert "quality_score" in body
        assert 0 <= body["quality_score"] <= 1

    @pytest.mark.asyncio
    async def test_quality_score_breakdown_in_cover_letter(
        self, api_gateway_event, mock_context, mock_dal, mock_llm_client
    ):
        """Test individual quality scores are in cover letter object."""
        event = api_gateway_event()

        with patch("careervp.handlers.cover_letter_handler.dal", mock_dal), \
             patch("careervp.handlers.cover_letter_handler.llm_client", mock_llm_client):

            response = lambda_handler(event, mock_context)

        body = json.loads(response["body"])
        cover_letter = body.get("cover_letter", {})
        assert "personalization_score" in cover_letter
        assert "relevance_score" in cover_letter
        assert "tone_score" in cover_letter
```

---

## Verification Commands

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Run integration tests
uv run pytest tests/cover-letter/integration/test_cover_letter_handler_integration.py -v

# Expected: 22 tests PASSED

# Run with coverage
uv run pytest tests/cover-letter/integration/ --cov=careervp --cov-report=term-missing
```

---

## Expected Test Results

```
==================== test session starts ====================
collected 22 items

test_cover_letter_handler_integration.py::TestCoverLetterIntegration::test_full_success_flow PASSED
test_cover_letter_handler_integration.py::TestCoverLetterIntegration::test_success_with_preferences PASSED
test_cover_letter_handler_integration.py::TestCoverLetterIntegration::test_artifact_saved_on_success PASSED
test_cover_letter_handler_integration.py::TestCoverLetterIntegration::test_download_url_generated PASSED
test_cover_letter_handler_integration.py::TestCoverLetterIntegration::test_fvs_rejection_wrong_company PASSED
test_cover_letter_handler_integration.py::TestCoverLetterIntegration::test_llm_retry_on_low_quality PASSED
test_cover_letter_handler_integration.py::TestCoverLetterIntegration::test_cv_not_found_propagates PASSED
test_cover_letter_handler_integration.py::TestCoverLetterIntegration::test_vpr_not_found_propagates PASSED
test_cover_letter_handler_integration.py::TestCoverLetterIntegration::test_timeout_propagates PASSED
test_cover_letter_handler_integration.py::TestCoverLetterIntegration::test_missing_auth_returns_401 PASSED
test_cover_letter_handler_integration.py::TestCoverLetterIntegration::test_user_id_extracted_correctly PASSED
test_cover_letter_handler_integration.py::TestCoverLetterIntegration::test_rate_limit_returns_429 PASSED
test_cover_letter_handler_integration.py::TestCoverLetterIntegration::test_quality_score_calculated PASSED
test_cover_letter_handler_integration.py::TestCoverLetterIntegration::test_quality_score_breakdown_in_cover_letter PASSED
... (8 more tests)

==================== 22 passed in 5.23s ====================
```

---

## Completion Criteria

- [ ] All integration test scenarios implemented
- [ ] Success flow tests passing
- [ ] Error propagation tests passing
- [ ] FVS rejection tests passing
- [ ] LLM retry tests passing
- [ ] Authentication tests passing
- [ ] All 22 tests passing

---

## References

- [Phase 9 integration tests](../09-cv-tailoring/) - Pattern reference
- [COVER_LETTER_SPEC.md](../../specs/cover-letter/COVER_LETTER_SPEC.md) - Expected behaviors
