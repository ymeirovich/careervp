# Task 07: Integration Tests

## Overview

Verify integration between handler, logic, and DAL layers.

**Test files:**
- `tests/gap-analysis/integration/test_gap_handler.py` (already created)
- `tests/gap-analysis/integration/test_gap_dal.py` (if Task 06 implemented)

**Dependencies:** Tasks 01-06
**Estimated time:** 2 hours
**Goal:** Verify all components work together

---

## What to Test

### Integration Test Categories

1. **Handler → Logic → DAL Flow**
   - Request validation
   - CV retrieval from DAL
   - Question generation via logic layer
   - Response formatting

2. **Error Handling**
   - CV not found
   - LLM timeout
   - Invalid request data
   - DynamoDB errors

3. **Authentication & Authorization**
   - JWT token extraction
   - User ID validation
   - Access control

4. **Edge Cases**
   - Empty CV
   - Minimal job posting
   - Large job posting (near 10MB)
   - Hebrew language

---

## Test Execution

### Run Integration Tests

```bash
cd src/backend

# Run all integration tests
uv run pytest tests/gap-analysis/integration/ -v --tb=short

# Run with mocking
uv run pytest tests/gap-analysis/integration/test_gap_handler.py -v

# Expected output:
# - test_submit_creates_job_and_returns_202 PASSED
# - test_submit_generates_unique_job_id PASSED
# - test_submit_includes_cors_headers PASSED
# - test_submit_rejects_missing_user_id PASSED
# - test_submit_rejects_missing_cv_id PASSED
# - test_submit_validates_file_size PASSED
# - test_submit_handles_dynamodb_error PASSED
# - test_submit_handles_sqs_error PASSED
# - test_submit_extracts_user_id_from_jwt PASSED
# - test_submit_rejects_mismatched_user_id PASSED
```

---

## Mocking Strategy

### Mock External Dependencies

```python
# Mock DynamoDB
with patch('careervp.handlers.gap_handler.DynamoDalHandler') as mock_dal:
    mock_dal.return_value.get_cv.return_value = Result(
        success=True,
        data=mock_user_cv
    )

# Mock LLM Client
with patch('careervp.logic.gap_analysis.LLMClient') as mock_llm:
    mock_llm.return_value.generate.return_value = Result(
        success=True,
        data=json.dumps(mock_questions)
    )
```

### Don't Mock

- Validation functions (test real validation)
- Result pattern logic
- Pydantic model validation
- Scoring algorithm

---

## Verification Commands

```bash
cd src/backend

# Run integration tests
uv run pytest tests/gap-analysis/integration/ -v

# Run with coverage
uv run pytest tests/gap-analysis/integration/ --cov=careervp.handlers.gap_handler --cov=careervp.logic.gap_analysis --cov-report=term-missing

# Expected: 90%+ coverage for tested modules
```

---

## Acceptance Criteria

- [ ] All integration tests pass (20+ tests)
- [ ] Handler → Logic → DAL flow tested
- [ ] Error scenarios covered
- [ ] Authentication tested
- [ ] Authorization tested
- [ ] Edge cases tested
- [ ] Mocking strategy correct (external only)
- [ ] Test fixtures reused from conftest.py
- [ ] No flaky tests

---

## Common Issues & Solutions

### Issue: Tests timing out

**Solution:** Reduce LLM timeout in tests:
```python
with patch('careervp.logic.gap_analysis.asyncio.wait_for') as mock_wait:
    mock_wait.return_value = mock_result  # Skip actual wait
```

### Issue: DynamoDB connection errors

**Solution:** Ensure all DynamoDB calls are mocked:
```python
with patch('careervp.dal.dynamo_dal_handler.boto3.resource'):
    # Test logic
```

### Issue: JWT extraction failing

**Solution:** Ensure test event includes JWT claims:
```python
event['requestContext']['authorizer']['claims']['sub'] = 'user_test_123'
```

---

## Commit Message

```bash
git commit -m "test(gap-analysis): add integration tests

- Add handler integration tests (20 tests)
- Test Handler → Logic → DAL flow
- Test error handling and edge cases
- Test authentication and authorization
- All integration tests pass
- 92% coverage on handler and logic

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```
