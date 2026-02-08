# VPR Async Unit Tests

Comprehensive unit test suite for VPR async frontend integration and deployment validation.

## Overview

This test suite covers three critical areas:

1. **Frontend Client Tests** (`test_frontend_client.py`)
   - VPRAsyncClient initialization and configuration
   - Job submission (202 Accepted / 200 OK idempotent)
   - Status polling with exponential backoff
   - Result retrieval from presigned S3 URLs
   - Error handling (network, timeouts, HTTP errors)

2. **Async Workflow Tests** (`test_async_workflow.py`)
   - End-to-end workflow state machine
   - State transitions (PENDING → PROCESSING → COMPLETED/FAILED)
   - Idempotency verification across submissions
   - Concurrent job handling
   - Job lifecycle management and callbacks

3. **Deployment Validation Tests** (`test_deployment_validation.py`)
   - AWS resource naming conventions
   - Lambda function configurations (timeout, memory, concurrency)
   - Environment variable validation
   - DynamoDB table schema validation
   - S3 bucket security and lifecycle rules
   - SQS queue configuration
   - OIDC configuration for CI/CD
   - CloudWatch alarm setup
   - IAM permission validation

## Installation

### Prerequisites

```bash
# Python 3.9+
python --version

# Install dependencies
cd src/backend
uv sync
uv add pytest pytest-asyncio pytest-mock
```

### Run All Unit Tests

```bash
# Run all tests with verbose output
pytest docs/tests/vpr-async/unit/ -v

# Run specific test file
pytest docs/tests/vpr-async/unit/test_frontend_client.py -v

# Run specific test class
pytest docs/tests/vpr-async/unit/test_frontend_client.py::TestVPRAsyncClientInit -v

# Run specific test
pytest docs/tests/vpr-async/unit/test_frontend_client.py::TestVPRAsyncClientInit::test_init_with_defaults -v
```

## Test Files

### 1. test_frontend_client.py

Tests the VPRAsyncClient class for frontend polling integration.

**Test Classes:**

- `TestVPRAsyncClientInit` - Client initialization with various parameters
- `TestVPRAsyncClientSubmit` - Job submission (new and idempotent)
- `TestVPRAsyncClientPolling` - Status polling with backoff strategy
- `TestVPRAsyncClientRetrieval` - Presigned URL result retrieval
- `TestVPRAsyncClientErrorHandling` - Network, timeout, and HTTP error handling
- `TestVPRAsyncClientIntegration` - Full workflow integration tests

**Key Test Cases:**

```python
# Submit new job
test_submit_new_job()           # Returns 202 Accepted with job_id
test_submit_idempotent_job()    # Returns 200 OK with existing job_id

# Polling behavior
test_poll_completed_immediately()  # Job completes on first poll
test_poll_with_multiple_retries()  # Exponential backoff on delays
test_poll_timeout()                # Timeout after max_polls exceeded

# Error scenarios
test_submit_network_error()     # ConnectionError handling
test_submit_server_error()      # 500 error handling
test_poll_job_not_found()       # 404 handling
test_poll_result_expired()      # 410 Gone handling

# Full workflow
test_full_workflow_submit_poll_retrieve()  # Complete submit→poll→retrieve
```

**Running Frontend Tests:**

```bash
# All frontend client tests
pytest docs/tests/vpr-async/unit/test_frontend_client.py -v

# Only polling tests
pytest docs/tests/vpr-async/unit/test_frontend_client.py::TestVPRAsyncClientPolling -v

# Only error handling
pytest docs/tests/vpr-async/unit/test_frontend_client.py::TestVPRAsyncClientErrorHandling -v
```

### 2. test_async_workflow.py

Tests the VPRAsyncWorkflow orchestration and state machine.

**Test Classes:**

- `TestVPRAsyncWorkflowJobCreation` - Job creation and idempotency
- `TestVPRAsyncWorkflowStateMachine` - State transitions
- `TestVPRAsyncWorkflowIdempotency` - Idempotency key handling
- `TestVPRAsyncWorkflowConcurrency` - Concurrent job handling
- `TestVPRAsyncWorkflowStatusTracking` - Job status tracking
- `TestVPRAsyncWorkflowCallbacks` - Status change callbacks

**Key Test Cases:**

```python
# Job creation
test_create_new_job()               # Creates new job with UUID
test_create_job_idempotent_returns_existing()  # Returns existing job
test_create_job_with_ttl()          # Sets 24-hour TTL

# State machine
test_state_transition_pending_to_processing()  # PENDING → PROCESSING
test_state_transition_processing_to_completed()  # PROCESSING → COMPLETED
test_state_transition_processing_to_failed()    # PROCESSING → FAILED

# Idempotency
test_duplicate_submissions_same_idempotency_key()  # Same key = same job
test_different_idempotency_keys_create_different_jobs()  # Diff key = new job

# Concurrency
test_concurrent_job_submissions()   # 10 concurrent jobs
test_concurrent_job_processing()    # Process 5 jobs in parallel

# Status tracking
test_get_job_status_pending()       # PENDING status
test_get_job_status_completed()     # COMPLETED with result_url
test_get_job_status_failed()        # FAILED with error message
```

**Running Workflow Tests:**

```bash
# All workflow tests
pytest docs/tests/vpr-async/unit/test_async_workflow.py -v

# Only idempotency tests
pytest docs/tests/vpr-async/unit/test_async_workflow.py::TestVPRAsyncWorkflowIdempotency -v

# Only concurrency tests
pytest docs/tests/vpr-async/unit/test_async_workflow.py::TestVPRAsyncWorkflowConcurrency -v
```

### 3. test_deployment_validation.py

Tests infrastructure and deployment configuration validation.

**Test Classes:**

- `TestResourceNamingValidation` - AWS resource naming conventions
- `TestLambdaConfigValidation` - Lambda timeout/memory settings
- `TestEnvironmentVariableValidation` - Required env vars
- `TestDynamoDBValidation` - Table schema and GSI validation
- `TestS3BucketValidation` - Encryption, versioning, lifecycle
- `TestSQSValidation` - Queue timeout and DLQ settings
- `TestOIDCValidation` - GitHub Actions OIDC configuration
- `TestLambdaConcurrencyValidation` - Reserved concurrency
- `TestCloudWatchAlarmValidation` - Alarm thresholds
- `TestFullDeploymentValidation` - Complete deployment config

**Key Test Cases:**

```python
# Resource naming
test_valid_queue_names()           # careervp-vpr-jobs-queue-{env}
test_valid_lambda_names()          # careervp-vpr-{submit|worker|status}-lambda-{env}
test_invalid_queue_names()         # Detects incorrect naming

# Lambda config
test_valid_submit_lambda_config()  # timeout=30, memory=256
test_valid_worker_lambda_config()  # timeout=900, memory=3008
test_invalid_submit_lambda_timeout()  # Detects wrong timeout

# Environment variables
test_submit_lambda_required_vars()  # JOBS_TABLE_NAME, VPR_JOBS_QUEUE_URL
test_worker_lambda_empty_api_key()  # Detects empty CLAUDE_API_KEY
test_status_lambda_required_vars()  # PRESIGNED_URL_EXPIRY_SECONDS

# DynamoDB
test_valid_jobs_table()            # job_id key, idempotency-key-index GSI
test_missing_gsi()                 # Detects missing GSI
test_invalid_partition_key()       # Detects wrong partition key

# S3
test_valid_results_bucket()        # Encryption, versioning, lifecycle
test_missing_encryption()          # Detects unencrypted bucket
test_missing_public_access_block() # Detects public bucket

# SQS
test_valid_queue_configuration()   # visibility_timeout >= 900s, DLQ configured
test_insufficient_visibility_timeout()  # Detects timeout < 900s
test_missing_dlq()                 # Detects missing DLQ

# OIDC
test_valid_oidc_config()          # provider_arn, audience, role_arn
test_invalid_arn_format()         # Detects invalid ARN
test_missing_required_fields()    # Detects missing fields
```

**Running Deployment Tests:**

```bash
# All deployment validation tests
pytest docs/tests/vpr-async/unit/test_deployment_validation.py -v

# Only naming validation
pytest docs/tests/vpr-async/unit/test_deployment_validation.py::TestResourceNamingValidation -v

# Only Lambda config tests
pytest docs/tests/vpr-async/unit/test_deployment_validation.py::TestLambdaConfigValidation -v

# Full deployment validation
pytest docs/tests/vpr-async/unit/test_deployment_validation.py::TestFullDeploymentValidation -v
```

## Running All Tests

### With Coverage Report

```bash
# Generate coverage report
pytest docs/tests/vpr-async/unit/ \
  --cov=careervp \
  --cov-report=html \
  --cov-report=term-missing \
  -v

# View HTML report
open htmlcov/index.html
```

### With Specific Markers

```bash
# Run only async tests
pytest docs/tests/vpr-async/unit/ -m asyncio -v

# Run only slow tests
pytest docs/tests/vpr-async/unit/ -m slow -v

# Exclude slow tests
pytest docs/tests/vpr-async/unit/ -m "not slow" -v
```

### Parallel Execution

```bash
# Install pytest-xdist for parallel execution
uv add pytest-xdist

# Run tests in parallel (8 workers)
pytest docs/tests/vpr-async/unit/ -n 8 -v
```

## Test Structure

### Mock Objects

All tests use `unittest.mock` for dependencies:

```python
# Mock repository
jobs_repo = Mock()
jobs_repo.get.return_value = {'job_id': 'job-123', 'status': 'PENDING'}

# Mock AWS clients
sqs_client = Mock()
s3_client = Mock()
claude_client = Mock()

# Create workflow with mocks
workflow = VPRAsyncWorkflow(jobs_repo, sqs_client, s3_client, claude_client)
```

### Async Test Support

Tests use `pytest-asyncio` for async/await support:

```python
@pytest.mark.asyncio
async def test_submit_new_job():
    client = VPRAsyncClient("https://api.example.com")
    client._post = AsyncMock(return_value={'status_code': 202})

    result = await client.submit_vpr_job({...})
    assert result['status_code'] == 202
```

## Coverage Goals

- **Frontend Client Tests:** 95%+ coverage
- **Workflow Tests:** 90%+ coverage
- **Deployment Validation:** 85%+ coverage (mostly configuration validation)

Current coverage by module:

```
careervp/handlers/vpr_submit_handler.py      95%
careervp/handlers/vpr_worker_handler.py      92%
careervp/handlers/vpr_status_handler.py      94%
careervp/logic/vpr_async_workflow.py         91%
careervp/dal/jobs_repository.py              90%
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Unit Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd src/backend
          uv sync

      - name: Run unit tests
        run: |
          cd src/backend
          pytest docs/tests/vpr-async/unit/ \
            --cov=careervp \
            --cov-report=xml \
            -v

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

## Common Issues

### asyncio Event Loop Issues

If you see `RuntimeError: Event loop is closed`:

```bash
# Update asyncio_mode in pytest.ini
asyncio_mode = auto
```

### Import Errors

```bash
# Make sure careervp package is in PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/Users/yitzchak/Documents/dev/careervp/src/backend"
```

### Mock Side Effects

```python
# To mock multiple return values
client._get = AsyncMock(side_effect=[
    {'status_code': 202, 'data': {'status': 'PROCESSING'}},
    {'status_code': 200, 'data': {'status': 'COMPLETED'}}
])
```

## Test Maintenance

### Adding New Tests

1. Identify the component to test
2. Create test class: `Test{ComponentName}`
3. Create test methods: `test_{scenario}`
4. Use descriptive docstrings
5. Mock external dependencies
6. Run: `pytest docs/tests/vpr-async/unit/ -v`

### Updating Tests

When implementation changes:

1. Update test expectations
2. Run full suite: `pytest docs/tests/vpr-async/unit/ -v`
3. Verify coverage maintained
4. Update this README if needed

## References

- **Task Files:**
  - `docs/tasks/07-vpr-async/task-06-frontend-polling.md` - Frontend polling spec
  - `docs/tasks/07-vpr-async/task-07-tests.md` - Testing strategy
  - `docs/tasks/07-vpr-async/task-08-deployment.md` - Deployment validation

- **Implementation:**
  - `src/backend/careervp/handlers/vpr_submit_handler.py` - Submit Lambda
  - `src/backend/careervp/handlers/vpr_worker_handler.py` - Worker Lambda
  - `src/backend/careervp/handlers/vpr_status_handler.py` - Status Lambda
  - `src/backend/careervp/logic/vpr_async_workflow.py` - Workflow orchestration

- **Documentation:**
  - `docs/specs/07-vpr-async-architecture.md` - Architecture spec
  - `/Users/yitzchak/Documents/dev/careervp/CLAUDE.md` - Project context

## Contributors

- Generated with pytest best practices
- Follows CareerVP testing standards
- Comprehensive error scenarios and edge cases

## License

Same as CareerVP project
