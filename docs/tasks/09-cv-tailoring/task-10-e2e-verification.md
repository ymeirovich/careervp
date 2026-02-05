# Task 9.10: CV Tailoring - E2E Verification Tests

**Status:** Pending
**Spec Reference:** [docs/specs/04-cv-tailoring.md](../../specs/04-cv-tailoring.md)
**Depends On:** Tasks 9.1-9.9 (All implementation complete)
**Blocking:** Task 9.11 (Deployment)

## Overview

Implement end-to-end verification tests that test the full API flow from HTTP request through to complete response. Tests use LocalStack or mocked AWS services and verify complete request/response cycle including edge cases and realistic scenarios.

## Todo

### E2E Test Implementation

- [ ] Create `tests/cv-tailoring/e2e/test_cv_tailoring_flow.py`
- [ ] Implement 10-15 E2E tests covering all scenarios
- [ ] Test happy path: valid CV → tailored CV (2 tests)
- [ ] Test with style preferences (1 test)
- [ ] Test with gap analysis (Phase 11) (1 test)
- [ ] Test error handling: missing CV (1 test)
- [ ] Test error handling: missing job (1 test)
- [ ] Test error handling: invalid request (1 test)
- [ ] Test response times (1 test)
- [ ] Test large CVs (1 test)
- [ ] Test concurrent requests (1 test)

### Validation & Formatting

- [ ] Run `uv run ruff format tests/cv-tailoring/e2e/`
- [ ] Run `uv run ruff check --fix tests/cv-tailoring/e2e/`
- [ ] Run `uv run mypy tests/cv-tailoring/e2e/ --strict`
- [ ] Run `uv run pytest tests/cv-tailoring/e2e/ -v`

### Commit

- [ ] Commit with message: `test(e2e): add CV tailoring E2E verification tests`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `tests/cv-tailoring/e2e/test_cv_tailoring_flow.py` | E2E test suite |
| `tests/cv-tailoring/e2e/conftest.py` | Shared E2E fixtures |

### Test Implementation Structure

```python
"""
End-to-End Tests for CV Tailoring.
Per tests/cv-tailoring/e2e/test_cv_tailoring_flow.py.

Tests the complete HTTP request/response cycle:
  HTTP POST /api/cv-tailoring → Handler → Logic → Response

Uses moto for mocked AWS services.
No real API calls (mocked Anthropic).
No real database calls (mocked DynamoDB).

Test categories:
- Happy path (2 tests)
- Style preferences (1 test)
- Gap analysis (1 test)
- Missing CV error (1 test)
- Missing job error (1 test)
- Invalid request (1 test)
- Performance (1 test)
- Large inputs (1 test)
- Concurrency (1 test)

Total: 10-15 tests
"""

import json
import pytest
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, MagicMock

from careervp.handlers.cv_tailoring_handler import handler


@pytest.fixture
def valid_request():
    """Valid CV tailoring request."""
    return {
        'body': json.dumps({
            'user_id': 'user_123',
            'application_id': 'app_456',
            'job_id': 'job_789',
            'cv_version': 1,
        })
    }


@pytest.fixture
def mock_context():
    """Mock Lambda context."""
    context = MagicMock()
    context.function_name = 'cv-tailoring'
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789:function:cv-tailoring'
    return context


@pytest.fixture
def mocked_dal():
    """Mocked DAL with realistic data."""
    # PSEUDO-CODE:
    # dal = MagicMock()
    # dal.get_user_cv.return_value = Result(success=True, data=Mock(
    #     version=1,
    #     contact_info=Mock(full_name='John Doe', email='john@example.com'),
    #     work_experience=[
    #         Mock(
    #             company_name='TechCorp',
    #             job_title='Software Engineer',
    #             start_date='2020-01-01',
    #             end_date='2023-12-31',
    #             description=['Built microservices', 'Led team of 3'],
    #         ),
    #     ],
    #     skills=['Python', 'AWS', 'Docker', 'Kubernetes'],
    #     education=[
    #         Mock(
    #             institution='MIT',
    #             degree='BS',
    #             field_of_study='Computer Science',
    #             graduation_date='2020-05-15',
    #         ),
    #     ],
    #     certifications=[Mock(name='AWS Solutions Architect', issuer='AWS')],
    # ))
    # dal.get_job_posting.return_value = Result(success=True, data=Mock(
    #     title='Senior Software Engineer',
    #     description='Looking for a senior engineer with microservices experience',
    #     requirements=['Python', 'AWS', 'Kubernetes', 'System Design', 'Team Leadership'],
    #     company_id='company_123',
    # ))
    # dal.get_company_research.return_value = Result(success=True, data=Mock(
    #     company_name='TechCorp Inc',
    #     industry='Software',
    #     size='1000-5000',
    #     culture='innovative, fast-paced',
    # ))
    # return dal

    pass


class TestHappyPath:
    """Test successful CV tailoring flow."""

    def test_e2e_valid_request_produces_response(self, valid_request, mock_context, mocked_dal):
        """E2E: Valid request produces complete response."""
        # PSEUDO-CODE:
        # with patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler', return_value=mocked_dal):
        #     response = handler(valid_request, mock_context)
        #     
        #     assert response['statusCode'] == 200
        #     body = json.loads(response['body'])
        #     assert body['success']
        #     assert body['code'] == 'CV_TAILORED'
        pass

    def test_e2e_response_contains_tailored_cv(self, valid_request, mock_context, mocked_dal):
        """E2E: Response contains complete tailored CV."""
        # PSEUDO-CODE:
        # with patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler', return_value=mocked_dal):
        #     response = handler(valid_request, mock_context)
        #     body = json.loads(response['body'])
        #     
        #     assert 'tailored_cv' in body['data']
        #     cv = body['data']['tailored_cv']
        #     assert cv['executive_summary']
        #     assert len(cv['work_experience']) > 0
        #     assert len(cv['skills']) > 0
        #     assert 'metadata' in body['data']
        #     assert 'token_usage' in body['data']
        pass


class TestStylePreferences:
    """Test style preference handling."""

    def test_e2e_with_technical_tone(self, valid_request, mock_context, mocked_dal):
        """E2E: Handles technical tone preference."""
        # PSEUDO-CODE:
        # request_data = json.loads(valid_request['body'])
        # request_data['style_preferences'] = {'tone': 'technical', 'formality_level': 'low'}
        # valid_request['body'] = json.dumps(request_data)
        # 
        # with patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler', return_value=mocked_dal):
        #     with patch('careervp.handlers.cv_tailoring_handler.tailor_cv') as mock_tailor:
        #         mock_tailor.return_value = Result(success=True, data=Mock())
        #         handler(valid_request, mock_context)
        #         
        #         call_kwargs = mock_tailor.call_args[1]
        #         assert call_kwargs['request'].style_preferences.tone == 'technical'
        pass


class TestGapAnalysis:
    """Test gap analysis integration (Phase 11)."""

    def test_e2e_with_gap_analysis_enabled(self, valid_request, mock_context, mocked_dal):
        """E2E: Handles gap_analysis flag."""
        # PSEUDO-CODE:
        # request_data = json.loads(valid_request['body'])
        # request_data['include_gap_analysis'] = True
        # valid_request['body'] = json.dumps(request_data)
        # 
        # with patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler', return_value=mocked_dal):
        #     mocked_dal.get_gap_analysis.return_value = Result(
        #         success=True,
        #         data={'missing_skills': ['Rust', 'Go']}
        #     )
        #     response = handler(valid_request, mock_context)
        #     
        #     assert response['statusCode'] == 200
        pass


class TestErrorHandling:
    """Test error scenarios."""

    def test_e2e_cv_not_found(self, valid_request, mock_context, mocked_dal):
        """E2E: Returns error when CV not found."""
        # PSEUDO-CODE:
        # mocked_dal.get_user_cv.return_value = Result(
        #     success=False,
        #     error='CV not found'
        # )
        # with patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler', return_value=mocked_dal):
        #     response = handler(valid_request, mock_context)
        #     
        #     assert response['statusCode'] == 400
        #     body = json.loads(response['body'])
        #     assert not body['success']
        pass

    def test_e2e_job_not_found(self, valid_request, mock_context, mocked_dal):
        """E2E: Returns error when job not found."""
        # PSEUDO-CODE:
        # mocked_dal.get_job_posting.return_value = Result(
        #     success=False,
        #     error='Job not found'
        # )
        # with patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler', return_value=mocked_dal):
        #     response = handler(valid_request, mock_context)
        #     
        #     assert response['statusCode'] == 400
        pass

    def test_e2e_invalid_request_json(self, mock_context, mocked_dal):
        """E2E: Returns error on invalid JSON."""
        # PSEUDO-CODE:
        # invalid_request = {'body': '{invalid json}'}
        # with patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler', return_value=mocked_dal):
        #     response = handler(invalid_request, mock_context)
        #     
        #     assert response['statusCode'] in [400, 500]
        pass


class TestPerformance:
    """Test performance characteristics."""

    def test_e2e_response_time_under_limit(self, valid_request, mock_context, mocked_dal):
        """E2E: Response time under 60 second Lambda timeout."""
        # PSEUDO-CODE:
        # with patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler', return_value=mocked_dal):
        #     start = time.perf_counter()
        #     response = handler(valid_request, mock_context)
        #     elapsed = time.perf_counter() - start
        #     
        #     # Should complete well within 60s timeout
        #     assert elapsed < 55  # Leave 5s buffer
        #     assert response['statusCode'] == 200
        pass


class TestLargeInputs:
    """Test with large/realistic data."""

    def test_e2e_with_large_cv(self, valid_request, mock_context, mocked_dal):
        """E2E: Handles CV with many entries."""
        # PSEUDO-CODE:
        # # Create CV with 10 work experiences, 50 skills
        # large_cv = Mock()
        # large_cv.work_experience = [Mock(...) for _ in range(10)]
        # large_cv.skills = [f'Skill_{i}' for i in range(50)]
        # 
        # mocked_dal.get_user_cv.return_value = Result(success=True, data=large_cv)
        # 
        # with patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler', return_value=mocked_dal):
        #     response = handler(valid_request, mock_context)
        #     
        #     assert response['statusCode'] == 200
        pass


class TestConcurrency:
    """Test concurrent request handling."""

    def test_e2e_concurrent_requests(self, valid_request, mock_context, mocked_dal):
        """E2E: Handles concurrent requests."""
        # PSEUDO-CODE:
        # def make_request(user_id):
        #     request_copy = valid_request.copy()
        #     data = json.loads(request_copy['body'])
        #     data['user_id'] = user_id
        #     request_copy['body'] = json.dumps(data)
        #     
        #     with patch('careervp.handlers.cv_tailoring_handler.DynamoDalHandler', return_value=mocked_dal):
        #         return handler(request_copy, mock_context)
        # 
        # with ThreadPoolExecutor(max_workers=5) as executor:
        #     futures = [executor.submit(make_request, f'user_{i}') for i in range(5)]
        #     responses = [f.result() for f in futures]
        # 
        # # All should succeed
        # assert all(r['statusCode'] == 200 for r in responses)
        pass
```

### Verification Commands

```bash
# Format code
uv run ruff format tests/cv-tailoring/e2e/

# Check for style issues
uv run ruff check --fix tests/cv-tailoring/e2e/

# Type check with strict mode
uv run mypy tests/cv-tailoring/e2e/ --strict

# Run E2E tests
uv run pytest tests/cv-tailoring/e2e/ -v

# Run with verbose output
uv run pytest tests/cv-tailoring/e2e/ -v -s

# Expected output:
# ===== test session starts =====
# tests/cv-tailoring/e2e/test_cv_tailoring_flow.py::TestHappyPath PASSED (2 tests)
# ... [10-15 total tests]
# ===== 10-15 passed in X.XXs =====
```

### Expected Test Results

```
tests/cv-tailoring/e2e/test_cv_tailoring_flow.py PASSED

Happy Path: 2 PASSED
- Valid request produces response
- Response contains complete tailored CV

Style Preferences: 1 PASSED
- Handles tone preferences

Gap Analysis: 1 PASSED
- Handles gap_analysis flag

Error Handling: 3 PASSED
- CV not found returns 400
- Job not found returns 400
- Invalid JSON returns 400/500

Performance: 1 PASSED
- Response time under limit

Large Inputs: 1 PASSED
- Handles large CVs

Concurrency: 1 PASSED
- Concurrent requests succeed

Total: 10-15 tests passing
Type checking: 0 errors, 0 warnings
All status codes: Correct
Response times: <55 seconds
```

### Zero-Hallucination Checklist

- [ ] All AWS services mocked (no real calls)
- [ ] All external APIs mocked (no real LLM calls)
- [ ] Test data realistic and complete
- [ ] Response structure matches API schema
- [ ] Error codes correct for each scenario
- [ ] No hardcoded test data
- [ ] Concurrent test uses proper threading
- [ ] Performance test has reasonable bounds
- [ ] All scenarios documented
- [ ] No test data leakage between tests

### Acceptance Criteria

- [ ] E2E tests cover complete HTTP flow
- [ ] Happy path test verifies full response
- [ ] Error scenarios return correct HTTP codes
- [ ] Style preferences integrated
- [ ] Gap analysis flag handled
- [ ] Performance test verifies <60s timeout compliance
- [ ] Large input handling tested
- [ ] Concurrent request handling tested
- [ ] 10-15 E2E tests passing
- [ ] Type checking passes with `mypy --strict`
- [ ] No real AWS/API calls during test execution

---

### Verification & Compliance

1. Run `uv run ruff format . && uv run ruff check --fix . && uv run mypy --strict .`
2. Run `uv run pytest tests/cv-tailoring/e2e/ -v`
3. Verify no real AWS or API calls made
4. If any E2E test fails, report a **BLOCKING ISSUE** and exit.
