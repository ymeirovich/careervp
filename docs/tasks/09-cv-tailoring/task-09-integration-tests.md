# Task 9.9: CV Tailoring - Integration Tests

**Status:** Pending
**Spec Reference:** [docs/specs/04-cv-tailoring.md](../../specs/04-cv-tailoring.md)
**Depends On:** Tasks 9.1-9.8 (All implementation complete)
**Blocking:** Task 9.10 (E2E Tests)

## Overview

Implement integration tests that verify the complete CV tailoring flow from handler through logic to DAL with mocked AWS services. Tests validate the entire request/response cycle with realistic data and error scenarios.

## Todo

### Integration Test Implementation

- [ ] Create `tests/cv-tailoring/integration/test_tailoring_handler_integration.py`
- [ ] Implement 25-30 integration tests covering complete flow
- [ ] Test valid request handling (4 tests)
- [ ] Test data loading from DAL (4 tests)
- [ ] Test tailoring logic integration (4 tests)
- [ ] Test FVS validation (4 tests)
- [ ] Test error propagation (4 tests)
- [ ] Test response formatting (3 tests)

### Mock Configuration

- [ ] Configure mocked DynamoDB using moto
- [ ] Configure mocked Anthropic API calls
- [ ] Set up test fixtures for CV, job, company research
- [ ] Create test data builders

### Validation & Formatting

- [ ] Run `uv run ruff format tests/cv-tailoring/`
- [ ] Run `uv run ruff check --fix tests/cv-tailoring/`
- [ ] Run `uv run mypy tests/cv-tailoring/ --strict`
- [ ] Run `uv run pytest tests/cv-tailoring/integration/ -v`

### Commit

- [ ] Commit with message: `test(integration): add CV tailoring integration tests with mocked AWS services`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `tests/cv-tailoring/integration/test_tailoring_handler_integration.py` | Integration test suite |
| `tests/cv-tailoring/conftest.py` | Shared fixtures and mocks |

### Test Implementation Structure

```python
"""
Integration Tests for CV Tailoring.
Per tests/cv-tailoring/integration/test_tailoring_handler_integration.py.

Tests the complete flow:
  Handler → Validation → Logic → DAL → Response

Uses moto for mocked AWS services (DynamoDB, Secrets Manager).
Uses unittest.mock for Anthropic API calls.

Test categories:
- Valid request flow (4 tests)
- Data loading from DAL (4 tests)
- Tailoring logic integration (4 tests)
- FVS validation (4 tests)
- Error propagation (4 tests)
- Response formatting (3 tests)

Total: 25-30 tests
"""

import json
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from moto import mock_dynamodb

from careervp.handlers.cv_tailoring_handler import handler
from careervp.models.tailor import (
    TailorCVRequest,
    TailoredCVResponse,
    TailoredCV,
    TailoringMetadata,
    TokenUsage,
    TailoredCVData,
)
from careervp.models.result import ResultCode


@pytest.fixture
def mock_event():
    """Create mock API Gateway event."""
    return {
        'body': json.dumps({
            'user_id': 'user_123',
            'application_id': 'app_456',
            'job_id': 'job_789',
            'cv_version': 1,
        }),
        'requestContext': {'requestId': 'req_123'},
    }


@pytest.fixture
def mock_context():
    """Create mock Lambda context."""
    context = Mock()
    context.function_name = 'cv-tailoring'
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789:function:cv-tailoring'
    return context


@pytest.fixture
def mock_dal():
    """Create mocked DAL handler."""
    # PSEUDO-CODE:
    # dal = Mock()
    # dal.get_user_cv.return_value = Result(success=True, data=Mock(
    #     version=1,
    #     contact_info=Mock(full_name='John Doe'),
    #     work_experience=[Mock(company_name='Acme', job_title='Engineer')],
    #     skills=['Python', 'AWS'],
    #     education=[],
    #     certifications=[],
    # ))
    # dal.get_job_posting.return_value = Result(success=True, data=Mock(
    #     title='Senior Engineer',
    #     description='We need a senior engineer',
    #     requirements=['Python', 'AWS', 'Docker'],
    # ))
    # dal.get_company_research.return_value = Result(success=True, data=Mock(
    #     company_name='Acme Corp',
    #     industry='Technology',
    # ))
    # return dal

    pass


@pytest.fixture
def mock_llm():
    """Create mocked LLM client."""
    # PSEUDO-CODE:
    # with patch('careervp.logic.cv_tailor.LLMClient') as mock_class:
    #     mock_instance = MagicMock()
    #     mock_instance.generate.return_value = Result(
    #         success=True,
    #         data=Mock(TailoredCV)(
    #             contact_info={'name': 'John Doe'},
    #             executive_summary='Experienced engineer',
    #             work_experience=[...],
    #             skills=[...],
    #             education=[],
    #             certifications=[],
    #             source_cv_version=1,
    #             target_job_id='job_789',
    #         ),
    #         metadata={'input_tokens': 1000, 'output_tokens': 500},
    #     )
    #     mock_class.return_value = mock_instance
    #     yield mock_instance

    pass


class TestValidRequestFlow:
    """Test complete flow with valid request."""

    def test_handler_processes_complete_flow(self, mock_event, mock_context, mock_dal, mock_llm):
        """Handler processes complete request flow successfully."""
        # PSEUDO-CODE:
        # with patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler', return_value=mock_dal):
        #     response = handler(mock_event, mock_context)
        #     
        #     assert response['statusCode'] == 200
        #     body = json.loads(response['body'])
        #     assert body['success']
        #     assert body['code'] == 'CV_TAILORED'
        #     assert 'data' in body
        pass

    def test_handler_returns_complete_tailored_cv(self, mock_event, mock_context, mock_dal, mock_llm):
        """Handler returns complete tailored CV structure."""
        # PSEUDO-CODE:
        # with patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler', return_value=mock_dal):
        #     response = handler(mock_event, mock_context)
        #     body = json.loads(response['body'])
        #     
        #     assert 'tailored_cv' in body['data']
        #     assert 'metadata' in body['data']
        #     assert 'token_usage' in body['data']
        pass

    def test_handler_calls_all_required_methods(self, mock_event, mock_context, mock_dal, mock_llm):
        """Handler calls all required DAL and logic methods."""
        # PSEUDO-CODE:
        # with patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler', return_value=mock_dal):
        #     handler(mock_event, mock_context)
        #     
        #     mock_dal.get_user_cv.assert_called_once_with('user_123', 1)
        #     mock_dal.get_job_posting.assert_called_once_with('job_789')
        #     mock_dal.get_company_research.assert_called_once()
        pass

    def test_handler_includes_token_usage_in_response(self, mock_event, mock_context, mock_dal, mock_llm):
        """Handler includes LLM token usage in response."""
        # PSEUDO-CODE:
        # with patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler', return_value=mock_dal):
        #     response = handler(mock_event, mock_context)
        #     body = json.loads(response['body'])
        #     
        #     assert 'token_usage' in body['data']
        #     assert body['data']['token_usage']['input_tokens'] > 0
        #     assert body['data']['token_usage']['output_tokens'] > 0
        pass


class TestDataLoadingFromDAL:
    """Test data loading from DAL."""

    def test_handler_loads_user_cv(self, mock_event, mock_context, mock_dal, mock_llm):
        """Handler loads user CV from DAL."""
        # PSEUDO-CODE:
        # with patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler', return_value=mock_dal):
        #     handler(mock_event, mock_context)
        #     mock_dal.get_user_cv.assert_called()
        pass

    def test_handler_loads_job_posting(self, mock_event, mock_context, mock_dal, mock_llm):
        """Handler loads job posting from DAL."""
        # PSEUDO-CODE:
        # with patch(...):
        #     handler(mock_event, mock_context)
        #     mock_dal.get_job_posting.assert_called()
        pass

    def test_handler_loads_company_research(self, mock_event, mock_context, mock_dal, mock_llm):
        """Handler loads company research from DAL."""
        # PSEUDO-CODE:
        # with patch(...):
        #     handler(mock_event, mock_context)
        #     mock_dal.get_company_research.assert_called()
        pass

    def test_handler_handles_missing_company_research(self, mock_event, mock_context, mock_dal, mock_llm):
        """Handler handles missing company research gracefully."""
        # PSEUDO-CODE:
        # mock_dal.get_company_research.return_value = Result(success=False)
        # with patch(...):
        #     response = handler(mock_event, mock_context)
        #     # Should still succeed (company research optional)
        #     assert response['statusCode'] == 200
        pass


class TestTailoringLogicIntegration:
    """Test integration with tailoring logic."""

    def test_handler_calls_tailor_cv_logic(self, mock_event, mock_context, mock_dal, mock_llm):
        """Handler calls tailor_cv logic with correct parameters."""
        # PSEUDO-CODE:
        # with patch('careervp.handlers.cv_tailoring_handler.tailor_cv') as mock_tailor:
        #     mock_tailor.return_value = Result(success=True, data=Mock())
        #     handler(mock_event, mock_context)
        #     mock_tailor.assert_called_once()
        pass

    def test_handler_passes_correct_parameters_to_logic(self, mock_event, mock_context, mock_dal, mock_llm):
        """Handler passes all required parameters to tailoring logic."""
        # PSEUDO-CODE:
        # with patch('careervp.handlers.cv_tailoring_handler.tailor_cv') as mock_tailor:
        #     mock_tailor.return_value = Result(success=True, data=Mock())
        #     handler(mock_event, mock_context)
        #     
        #     call_args = mock_tailor.call_args
        #     assert call_args[1]['request'].user_id == 'user_123'
        #     assert call_args[1]['dal'] is not None
        pass

    def test_handler_passes_gap_analysis_when_requested(self, mock_event, mock_context, mock_dal, mock_llm):
        """Handler includes gap_analysis when requested."""
        # PSEUDO-CODE:
        # request_data = json.loads(mock_event['body'])
        # request_data['include_gap_analysis'] = True
        # mock_event['body'] = json.dumps(request_data)
        # 
        # with patch('careervp.handlers.cv_tailoring_handler.tailor_cv') as mock_tailor:
        #     mock_tailor.return_value = Result(success=True, data=Mock())
        #     handler(mock_event, mock_context)
        #     
        #     assert mock_tailor.call_args[1]['gap_analysis'] is not None
        pass

    def test_handler_preserves_style_preferences(self, mock_event, mock_context, mock_dal, mock_llm):
        """Handler passes style preferences to logic."""
        # PSEUDO-CODE:
        # request_data = json.loads(mock_event['body'])
        # request_data['style_preferences'] = {'tone': 'technical'}
        # mock_event['body'] = json.dumps(request_data)
        # 
        # with patch('careervp.handlers.cv_tailoring_handler.tailor_cv') as mock_tailor:
        #     mock_tailor.return_value = Result(success=True, data=Mock())
        #     handler(mock_event, mock_context)
        #     
        #     assert mock_tailor.call_args[1]['request'].style_preferences.tone == 'technical'
        pass


class TestFVSValidationIntegration:
    """Test FVS validation in flow."""

    def test_handler_validates_output_with_fvs(self, mock_event, mock_context, mock_dal, mock_llm):
        """Handler validates tailored output with FVS rules."""
        # PSEUDO-CODE:
        # with patch('careervp.logic.cv_tailor._validate_tailored_output') as mock_validate:
        #     mock_validate.return_value = Result(success=True, data=None)
        #     response = handler(mock_event, mock_context)
        #     assert response['statusCode'] == 200
        pass

    def test_handler_rejects_hallucinated_skills(self, mock_event, mock_context, mock_dal, mock_llm):
        """Handler rejects output with hallucinated skills."""
        # PSEUDO-CODE:
        # with patch('careervp.logic.cv_tailor._validate_tailored_output') as mock_validate:
        #     mock_validate.return_value = Result(
        #         success=False,
        #         error='Hallucinated skill: Kubernetes',
        #         code=ResultCode.FVS_HALLUCINATION_DETECTED,
        #     )
        #     response = handler(mock_event, mock_context)
        #     assert response['statusCode'] == 500
        pass

    def test_handler_rejects_altered_dates(self, mock_event, mock_context, mock_dal, mock_llm):
        """Handler rejects output with altered dates."""
        # PSEUDO-CODE:
        # with patch('careervp.logic.cv_tailor._validate_tailored_output') as mock_validate:
        #     mock_validate.return_value = Result(
        #         success=False,
        #         error='Date altered',
        #         code=ResultCode.FVS_VALIDATION_FAILED,
        #     )
        #     response = handler(mock_event, mock_context)
        #     assert response['statusCode'] == 500
        pass

    def test_handler_includes_fvs_validation_status(self, mock_event, mock_context, mock_dal, mock_llm):
        """Handler includes FVS validation status in metadata."""
        # PSEUDO-CODE:
        # with patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler', return_value=mock_dal):
        #     response = handler(mock_event, mock_context)
        #     body = json.loads(response['body'])
        #     assert body['data']['metadata']['fvs_validation_passed'] is True
        pass


class TestErrorPropagation:
    """Test error handling and propagation."""

    def test_handler_returns_400_on_cv_not_found(self, mock_event, mock_context, mock_dal, mock_llm):
        """Handler returns 400 when CV not found."""
        # PSEUDO-CODE:
        # mock_dal.get_user_cv.return_value = Result(success=False, error='Not found')
        # with patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler', return_value=mock_dal):
        #     response = handler(mock_event, mock_context)
        #     assert response['statusCode'] == 400
        pass

    def test_handler_returns_400_on_job_not_found(self, mock_event, mock_context, mock_dal, mock_llm):
        """Handler returns 400 when job not found."""
        # PSEUDO-CODE:
        # mock_dal.get_job_posting.return_value = Result(success=False)
        # with patch(...):
        #     response = handler(mock_event, mock_context)
        #     assert response['statusCode'] == 400
        pass

    def test_handler_returns_500_on_tailoring_error(self, mock_event, mock_context, mock_dal, mock_llm):
        """Handler returns 500 on tailoring logic error."""
        # PSEUDO-CODE:
        # with patch('careervp.handlers.cv_tailoring_handler.tailor_cv') as mock_tailor:
        #     mock_tailor.return_value = Result(
        #         success=False,
        #         error='LLM error',
        #         code=ResultCode.CV_TAILORING_FAILED,
        #     )
        #     response = handler(mock_event, mock_context)
        #     assert response['statusCode'] == 500
        pass

    def test_handler_returns_500_on_timeout(self, mock_event, mock_context, mock_dal, mock_llm):
        """Handler returns 500 on timeout."""
        # PSEUDO-CODE:
        # with patch('careervp.handlers.cv_tailoring_handler.tailor_cv') as mock_tailor:
        #     mock_tailor.side_effect = TimeoutError('Request timeout')
        #     response = handler(mock_event, mock_context)
        #     assert response['statusCode'] == 500
        pass

    def test_handler_includes_error_details(self, mock_event, mock_context, mock_dal, mock_llm):
        """Handler includes error details in response."""
        # PSEUDO-CODE:
        # with patch('careervp.handlers.cv_tailoring_handler.tailor_cv') as mock_tailor:
        #     mock_tailor.return_value = Result(
        #         success=False,
        #         error='Specific error message',
        #         code=ResultCode.CV_TAILORING_FAILED,
        #     )
        #     response = handler(mock_event, mock_context)
        #     body = json.loads(response['body'])
        #     assert 'Specific error' in body['error']
        pass


class TestResponseFormatting:
    """Test response formatting."""

    def test_response_includes_tailored_cv_section(self, mock_event, mock_context, mock_dal, mock_llm):
        """Response includes complete tailored_cv section."""
        # PSEUDO-CODE:
        # with patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler', return_value=mock_dal):
        #     response = handler(mock_event, mock_context)
        #     body = json.loads(response['body'])
        #     assert 'tailored_cv' in body['data']
        #     assert 'executive_summary' in body['data']['tailored_cv']
        pass

    def test_response_includes_metadata_section(self, mock_event, mock_context, mock_dal, mock_llm):
        """Response includes complete metadata section."""
        # PSEUDO-CODE:
        # with patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler', return_value=mock_dal):
        #     response = handler(mock_event, mock_context)
        #     body = json.loads(response['body'])
        #     assert 'metadata' in body['data']
        #     assert 'created_at' in body['data']['metadata']
        pass

    def test_response_json_serializable(self, mock_event, mock_context, mock_dal, mock_llm):
        """Response body is valid JSON."""
        # PSEUDO-CODE:
        # with patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler', return_value=mock_dal):
        #     response = handler(mock_event, mock_context)
        #     body = json.loads(response['body'])  # Should not raise
        #     assert isinstance(body, dict)
        pass
```

### Verification Commands

```bash
# Format code
uv run ruff format tests/cv-tailoring/

# Check for style issues
uv run ruff check --fix tests/cv-tailoring/

# Type check with strict mode
uv run mypy tests/cv-tailoring/ --strict

# Run integration tests
uv run pytest tests/cv-tailoring/integration/ -v

# Run with coverage
uv run pytest tests/cv-tailoring/integration/ -v --cov=careervp.handlers.cv_tailoring_handler

# Expected output:
# ===== test session starts =====
# tests/cv-tailoring/integration/test_tailoring_handler_integration.py::TestValidRequestFlow PASSED (4 tests)
# ... [25-30 total tests]
# ===== 25-30 passed in X.XXs =====
```

### Expected Test Results

```
tests/cv-tailoring/integration/test_tailoring_handler_integration.py PASSED

Valid Request Flow: 4 PASSED
- Complete flow succeeds
- Returns complete tailored CV
- Calls all required methods
- Includes token usage

Data Loading from DAL: 4 PASSED
- Loads user CV
- Loads job posting
- Loads company research
- Handles missing company research

Tailoring Logic Integration: 4 PASSED
- Calls tailor_cv logic
- Passes correct parameters
- Includes gap_analysis when requested
- Preserves style preferences

FVS Validation Integration: 4 PASSED
- Validates with FVS rules
- Rejects hallucinated skills
- Rejects altered dates
- Includes validation status

Error Propagation: 4 PASSED
- Returns 400 on CV not found
- Returns 400 on job not found
- Returns 500 on tailoring error
- Returns 500 on timeout

Response Formatting: 3 PASSED
- Includes tailored_cv section
- Includes metadata section
- JSON serializable

Total: 25-30 tests passing
Type checking: 0 errors, 0 warnings
Coverage: >90% for handler module
```

### Zero-Hallucination Checklist

- [ ] All DAL calls mocked (no real AWS calls)
- [ ] All LLM calls mocked (no real API calls)
- [ ] Test data realistic and complete
- [ ] Error scenarios cover all result codes
- [ ] Response structure matches API schema
- [ ] FVS validation integration tested
- [ ] Pagination and edge cases covered
- [ ] Logging and tracing verified
- [ ] All error codes correct
- [ ] No hardcoded test data

### Acceptance Criteria

- [ ] Tests cover handler → logic → DAL flow
- [ ] All AWS services mocked (no actual AWS calls)
- [ ] All external APIs mocked (no actual LLM calls)
- [ ] Valid request produces complete response
- [ ] Error scenarios handled correctly
- [ ] HTTP status codes match scenario
- [ ] FVS validation integrated and tested
- [ ] Response JSON schema verified
- [ ] 25-30 integration tests passing
- [ ] Coverage >90% for handler module
- [ ] Type checking passes with `mypy --strict`

---

### Verification & Compliance

1. Run `uv run ruff format . && uv run ruff check --fix . && uv run mypy --strict .`
2. Run `uv run pytest tests/cv-tailoring/integration/ -v --cov`
3. Verify no real AWS or API calls made during tests
4. If any integration test fails, report a **BLOCKING ISSUE** and exit.
