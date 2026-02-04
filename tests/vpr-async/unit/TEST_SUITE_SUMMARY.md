# VPR-Async Lambda Handler Unit Tests - Summary

## Overview

Comprehensive unit test suite created for the three VPR async Lambda handlers based on task specifications.

**Created:** 2026-02-04
**Total Lines:** 1,643 lines of test code
**Total Tests:** 49 comprehensive unit tests
**Coverage Target:** 90%+ for all handlers

## Files Created

### 1. test_submit_handler.py (429 lines, 14 tests)

**Purpose:** Tests VPR Submit Handler (async job submission)

**Task Reference:** `docs/tasks/07-vpr-async/task-02-submit-handler.md`

**Test Coverage:**
- ✅ Job creation in DynamoDB with PENDING status
- ✅ SQS message sending with correct payload format
- ✅ Idempotency key generation: `vpr#{user_id}#{application_id}`
- ✅ Duplicate request handling (200 OK with existing job_id)
- ✅ Input validation using Pydantic VPRRequest model
- ✅ TTL calculation (10-minute expiration from creation)
- ✅ 202 Accepted response format for new jobs
- ✅ SQS message attributes for tracing (job_id, user_id)
- ✅ DynamoDB failure error handling (500 response)
- ✅ SQS send failure error handling (500 response)
- ✅ Request body validation errors (400/500 response)
- ✅ Input data storage in job record
- ✅ ISO timestamp format for created_at

**Key Test Methods:**
```python
test_create_new_job_success()
test_idempotent_request_returns_existing_job()
test_idempotency_key_generation()
test_ttl_calculation()
test_dynamodb_failure_returns_500()
test_sqs_failure_returns_500()
test_sqs_message_attributes()
test_response_format_new_job()
test_response_format_duplicate_job()
```

### 2. test_worker_handler.py (604 lines, 15 tests)

**Purpose:** Tests VPR Worker Handler (async VPR generation processing)

**Task Reference:** `docs/tasks/07-vpr-async/task-03-worker-handler.md`

**Test Coverage:**
- ✅ SQS message processing with batch processor
- ✅ Status transitions: PENDING → PROCESSING → COMPLETED
- ✅ Claude API integration (mocked VPRGenerator)
- ✅ S3 result storage with correct key format (`results/{job_id}.json`)
- ✅ S3 metadata (job_id, user_id, application_id)
- ✅ Token usage tracking (input_tokens, output_tokens)
- ✅ VPR persistence to users table (existing pattern)
- ✅ User CV retrieval validation
- ✅ VPR generation failure handling (status → FAILED)
- ✅ Claude API exception triggers SQS retry
- ✅ S3 put failure triggers retry
- ✅ Partial batch failure support (batch processor)
- ✅ Gap responses passed to VPR generator
- ✅ Completed_at timestamp in ISO format
- ✅ Result_key stored in job record

**Key Test Methods:**
```python
test_process_job_success()
test_status_transitions_pending_to_processing_to_completed()
test_user_cv_not_found_raises_error()
test_vpr_generation_failure_updates_status_to_failed()
test_claude_api_exception_triggers_retry()
test_s3_result_storage_format()
test_token_usage_stored_in_job_record()
test_batch_processor_partial_failures()
test_vpr_persisted_to_users_table()
```

### 3. test_status_handler.py (610 lines, 20 tests)

**Purpose:** Tests VPR Status Handler (status polling endpoint)

**Task Reference:** `docs/tasks/07-vpr-async/task-04-status-handler.md`

**Test Coverage:**
- ✅ PENDING status returns 202 Accepted with created_at
- ✅ PROCESSING status returns 202 Accepted with started_at
- ✅ COMPLETED status returns 200 OK with presigned S3 URL
- ✅ FAILED status returns 200 OK with error message
- ✅ 404 Not Found for non-existent jobs
- ✅ 404 Not Found for expired jobs (TTL)
- ✅ 410 Gone for expired S3 results (NoSuchKey)
- ✅ Presigned URL generation with 1-hour expiry (3600 seconds)
- ✅ Token usage included in COMPLETED response
- ✅ Job_id extraction from path parameters
- ✅ All status types handled correctly
- ✅ Unknown status returns 500
- ✅ DynamoDB exception returns 500
- ✅ S3 generic exception returns 500 (not NoSuchKey)
- ✅ Completed job missing result_key returns 500
- ✅ Base fields in all responses (job_id, status, created_at)
- ✅ Processing includes started_at if present
- ✅ Completed includes completed_at
- ✅ Failed handles missing error field gracefully

**Key Test Methods:**
```python
test_pending_job_returns_202_accepted()
test_processing_job_returns_202_accepted()
test_completed_job_returns_200_with_presigned_url()
test_failed_job_returns_200_with_error()
test_job_not_found_returns_404()
test_s3_result_expired_returns_410_gone()
test_presigned_url_expiry_is_one_hour()
test_all_status_types_handled()
```

### 4. HANDLER_TESTS_README.md

**Purpose:** Documentation for running and maintaining the test suite

**Contents:**
- Test coverage overview
- Running instructions (all tests, individual files, specific tests)
- Mocking strategy and fixtures
- Common test scenarios
- CI/CD integration examples
- Next steps and related documentation

## Running the Tests

### Quick Start

```bash
# From project root
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Install dependencies
uv sync
uv add pytest pytest-mock moto

# Run all handler tests
uv run pytest docs/tests/vpr-async/unit/test_submit_handler.py \
             docs/tests/vpr-async/unit/test_worker_handler.py \
             docs/tests/vpr-async/unit/test_status_handler.py -v

# Run with coverage
uv run pytest docs/tests/vpr-async/unit/test_*.py \
             --cov=careervp.handlers \
             --cov-report=html \
             --cov-report=term-missing -v
```

### Individual Test Files

```bash
# Submit handler only
uv run pytest docs/tests/vpr-async/unit/test_submit_handler.py -v

# Worker handler only
uv run pytest docs/tests/vpr-async/unit/test_worker_handler.py -v

# Status handler only
uv run pytest docs/tests/vpr-async/unit/test_status_handler.py -v
```

## Test Structure

### Fixtures Used

All tests use consistent pytest fixtures:

- `mock_jobs_repo` - JobsRepository mock
- `mock_dal` - DynamoDalHandler mock
- `mock_vpr_gen` - VPRGenerator mock
- `mock_s3` - S3 client mock
- `mock_sqs` - SQS client mock
- `mock_env_vars` - Environment variables
- `lambda_event` - Lambda event structure
- `lambda_context` - Lambda context mock
- `valid_vpr_request` - Valid request payload

### Mocking Strategy

- **AWS Services:** All boto3 clients mocked using `unittest.mock.patch`
- **Repositories:** JobsRepository and DynamoDalHandler mocked
- **External APIs:** VPRGenerator.generate_vpr() mocked
- **Time:** datetime.utcnow() mocked for deterministic testing

## Test Coverage Breakdown

| Handler | Tests | Lines | Coverage Target |
|---------|-------|-------|-----------------|
| Submit Handler | 14 | 429 | 95%+ |
| Worker Handler | 15 | 604 | 90%+ |
| Status Handler | 20 | 610 | 95%+ |
| **Total** | **49** | **1,643** | **90%+** |

## Key Features

### Comprehensive Error Handling

All tests cover both success and failure paths:
- Network errors (ConnectionError)
- AWS service errors (ClientError)
- Validation errors (Pydantic)
- Missing data errors
- Timeout scenarios
- Partial batch failures

### Realistic Test Data

All fixtures use realistic data:
- Valid UUIDs for job_ids
- ISO 8601 timestamps
- Proper AWS ARN formats
- Correct HTTP status codes
- Realistic token usage numbers

### Best Practices

- Clear test names describing scenario and expected behavior
- Comprehensive docstrings
- Arrange-Act-Assert pattern
- Independent tests (no shared state)
- Parallel execution safe
- No actual AWS resources required

## Integration with Implementation

These tests align with the task specifications:

1. **Submit Handler Tests** → `task-02-submit-handler.md`
   - Validates 202 Accepted response
   - Tests idempotency with 200 OK
   - Verifies SQS message format
   - Checks DynamoDB job creation

2. **Worker Handler Tests** → `task-03-worker-handler.md`
   - Tests status transitions
   - Validates S3 storage format
   - Checks token usage tracking
   - Verifies batch processing

3. **Status Handler Tests** → `task-04-status-handler.md`
   - Tests all status responses
   - Validates presigned URLs
   - Checks TTL expiry
   - Verifies error codes

## Next Steps

1. **Move tests when handlers implemented:**
   ```bash
   mv docs/tests/vpr-async/unit/test_*_handler.py \
      src/backend/tests/unit/handlers/
   ```

2. **Add integration tests:**
   - End-to-end workflow tests
   - Real AWS resource tests (with cleanup)
   - Load testing with concurrent requests

3. **Add contract tests:**
   - API Gateway integration validation
   - Event schema validation
   - Response format validation

4. **CI/CD integration:**
   - Add to GitHub Actions workflow
   - Set coverage thresholds
   - Block merges on test failures

## Documentation References

- **Task Files:**
  - `docs/tasks/07-vpr-async/task-02-submit-handler.md` - Submit handler spec
  - `docs/tasks/07-vpr-async/task-03-worker-handler.md` - Worker handler spec
  - `docs/tasks/07-vpr-async/task-04-status-handler.md` - Status handler spec

- **Architecture:**
  - `docs/specs/07-vpr-async-architecture.md` - Overall architecture

- **Implementation (to be created):**
  - `src/backend/careervp/handlers/vpr_submit_handler.py`
  - `src/backend/careervp/handlers/vpr_worker_handler.py`
  - `src/backend/careervp/handlers/vpr_status_handler.py`

## Notes

- All tests use `unittest.mock` for AWS service mocking
- No external dependencies required to run tests
- Tests validate both happy path and error scenarios
- All test fixtures are reusable and composable
- Tests can run in parallel with pytest-xdist
- Zero actual AWS costs to run these tests
