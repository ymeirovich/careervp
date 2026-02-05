# VPR-Async Lambda Handler Unit Tests

Comprehensive unit tests for the VPR async architecture Lambda handlers.

## Overview

This test suite covers the three core Lambda handlers in the VPR async workflow:

1. **Submit Handler** (`test_submit_handler.py`) - Job submission and SQS queuing
2. **Worker Handler** (`test_worker_handler.py`) - VPR generation processing
3. **Status Handler** (`test_status_handler.py`) - Status polling and result retrieval

## Test Coverage

### test_submit_handler.py

**Covers:** `src/backend/careervp/handlers/vpr_submit_handler.py`

- ✅ Job creation in DynamoDB (PENDING status)
- ✅ SQS message sending with correct format
- ✅ Idempotency key generation (`vpr#{user_id}#{application_id}`)
- ✅ Idempotent request handling (200 OK for duplicates)
- ✅ Input validation (Pydantic models)
- ✅ TTL calculation (10-minute expiration)
- ✅ 202 Accepted response format
- ✅ Error handling (DynamoDB failures, SQS failures)
- ✅ SQS message attributes for tracing

**Test Count:** 14 tests

### test_worker_handler.py

**Covers:** `src/backend/careervp/handlers/vpr_worker_handler.py`

- ✅ SQS message processing (batch processor)
- ✅ Status transitions (PENDING → PROCESSING → COMPLETED)
- ✅ Claude API call integration (mocked)
- ✅ S3 result storage with correct format
- ✅ Token usage tracking
- ✅ VPR persistence to users table
- ✅ Error handling (Claude API timeout, rate limits)
- ✅ Partial batch failure support
- ✅ Gap responses handling
- ✅ User CV retrieval
- ✅ Failed status updates

**Test Count:** 15 tests

### test_status_handler.py

**Covers:** `src/backend/careervp/handlers/vpr_status_handler.py`

- ✅ PENDING status response (202 Accepted)
- ✅ PROCESSING status response (202 Accepted with started_at)
- ✅ COMPLETED status response (200 OK with presigned URL)
- ✅ FAILED status response (200 OK with error)
- ✅ 404 Not Found for non-existent jobs
- ✅ 404 for expired jobs (TTL)
- ✅ 410 Gone for expired S3 results
- ✅ Presigned URL generation (1-hour expiry)
- ✅ Token usage in response
- ✅ Error handling (DynamoDB, S3 exceptions)

**Test Count:** 20 tests

**Total:** 49 comprehensive unit tests

## Running the Tests

### Prerequisites

```bash
# Install dependencies
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv sync
uv add pytest pytest-mock moto
```

### Run All Handler Tests

```bash
# From project root
uv run pytest docs/tests/vpr-async/unit/test_submit_handler.py docs/tests/vpr-async/unit/test_worker_handler.py docs/tests/vpr-async/unit/test_status_handler.py -v
```

### Run Individual Test Files

```bash
# Submit handler tests only
uv run pytest docs/tests/vpr-async/unit/test_submit_handler.py -v

# Worker handler tests only
uv run pytest docs/tests/vpr-async/unit/test_worker_handler.py -v

# Status handler tests only
uv run pytest docs/tests/vpr-async/unit/test_status_handler.py -v
```

### Run Specific Test

```bash
# Example: Test idempotency
uv run pytest docs/tests/vpr-async/unit/test_submit_handler.py::TestSubmitHandler::test_idempotent_request_returns_existing_job -v
```

### Run with Coverage

```bash
# Generate coverage report
uv run pytest docs/tests/vpr-async/unit/test_*.py --cov=careervp.handlers --cov-report=html -v

# View coverage
open htmlcov/index.html
```

## Test Structure

All tests follow pytest best practices:

- **Fixtures** for setup and dependency injection
- **Mocking** for AWS services (DynamoDB, SQS, S3) using `unittest.mock`
- **Clear naming** using `test_<scenario>_<expected_behavior>` pattern
- **Arrange-Act-Assert** structure
- **Comprehensive assertions** for all critical paths
- **Docstrings** explaining test purpose

## Mocking Strategy

### AWS Services

All AWS SDK calls are mocked using `unittest.mock.patch`:

```python
@pytest.fixture
def mock_jobs_repo():
    """Mock JobsRepository for testing."""
    with patch("careervp.handlers.vpr_submit_handler.JobsRepository") as mock:
        yield mock.return_value
```

### External Dependencies

- **DynamoDB:** `JobsRepository`, `DynamoDalHandler`
- **S3:** `boto3.client("s3")`
- **SQS:** `boto3.client("sqs")`
- **Claude API:** `VPRGenerator.generate_vpr()`

### Time Mocking

```python
with patch("careervp.handlers.vpr_submit_handler.datetime") as mock_datetime:
    now = datetime(2026, 2, 4, 12, 0, 0)
    mock_datetime.utcnow.return_value = now
    # Test with fixed time
```

## Common Fixtures

### Environment Variables

```python
@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set environment variables for testing."""
    monkeypatch.setenv("JOBS_TABLE_NAME", "test-jobs-table")
    monkeypatch.setenv("VPR_JOBS_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123456789/test-queue")
```

### Lambda Event

```python
@pytest.fixture
def lambda_event(valid_vpr_request: dict[str, Any]) -> dict[str, Any]:
    """Lambda event with VPR request."""
    return {
        "body": json.dumps(valid_vpr_request),
        "requestContext": {},
        "pathParameters": {}
    }
```

### Lambda Context

```python
@pytest.fixture
def lambda_context():
    """Mock Lambda context."""
    context = MagicMock()
    context.request_id = "test-request-id"
    return context
```

## Key Test Scenarios

### Submit Handler

```python
# New job submission
test_create_new_job_success()                      # 202 Accepted
test_idempotent_request_returns_existing_job()     # 200 OK
test_idempotency_key_generation()                  # vpr#{user}#{app}
test_ttl_calculation()                             # 10-minute expiry
test_sqs_message_attributes()                      # Tracing metadata

# Error handling
test_invalid_request_body_validation_error()       # 400/500
test_dynamodb_failure_returns_500()                # DynamoDB error
test_sqs_failure_returns_500()                     # SQS error
```

### Worker Handler

```python
# Successful processing
test_process_job_success()                         # End-to-end
test_status_transitions_pending_to_processing_to_completed()  # State machine
test_s3_result_storage_format()                    # Result storage
test_token_usage_stored_in_job_record()            # Metrics

# Error handling
test_user_cv_not_found_raises_error()              # Missing CV
test_vpr_generation_failure_updates_status_to_failed()  # VPR error
test_claude_api_exception_triggers_retry()         # API retry
test_batch_processor_partial_failures()            # Batch handling
```

### Status Handler

```python
# Status responses
test_pending_job_returns_202_accepted()            # PENDING
test_processing_job_returns_202_accepted()         # PROCESSING
test_completed_job_returns_200_with_presigned_url()  # COMPLETED
test_failed_job_returns_200_with_error()           # FAILED

# Edge cases
test_job_not_found_returns_404()                   # Not found
test_s3_result_expired_returns_410_gone()          # Expired
test_presigned_url_expiry_is_one_hour()            # 1-hour URL
```

## Integration with CI/CD

These tests should run in CI/CD pipeline before deployment:

```yaml
# .github/workflows/test.yml
- name: Run VPR-Async Handler Unit Tests
  run: |
    cd src/backend
    uv run pytest docs/tests/vpr-async/unit/test_submit_handler.py \
                 docs/tests/vpr-async/unit/test_worker_handler.py \
                 docs/tests/vpr-async/unit/test_status_handler.py \
                 -v --tb=short --cov=careervp.handlers
```

## Next Steps

1. **Move tests to proper location:** Once handlers are implemented, move tests to `src/backend/tests/unit/handlers/`
2. **Add integration tests:** Create `docs/tests/vpr-async/integration/` for end-to-end tests
3. **Add load tests:** Test worker Lambda concurrency and SQS throughput
4. **Add contract tests:** Verify API Gateway integration

## Related Documentation

- **Task Files:**
  - `docs/tasks/07-vpr-async/task-02-submit-handler.md`
  - `docs/tasks/07-vpr-async/task-03-worker-handler.md`
  - `docs/tasks/07-vpr-async/task-04-status-handler.md`

- **Architecture Spec:** `docs/specs/07-vpr-async-architecture.md`

- **Implementation Location:** `src/backend/careervp/handlers/`

## Notes

- Tests use `unittest.mock` for AWS service mocking
- All tests are independent and can run in parallel
- No actual AWS resources are required
- Tests validate both success and failure paths
- Error handling is comprehensively tested
- Tests align with task specifications from task files
