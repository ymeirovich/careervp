# Task 7.7: Comprehensive Testing Suite

**Status:** Not Started
**Spec Reference:** [[docs/specs/07-vpr-async-architecture.md]]
**Priority:** P0 (BLOCKING - Production VPR generation fails 100%)

## Overview

Create comprehensive test suite for VPR async architecture covering unit tests, integration tests, load tests, and failure tests. Ensure all components work together correctly before production deployment.

## Prerequisites

- [ ] Tasks 7.1-7.6 complete (all implementation done)
- [ ] `pytest` installed (`uv add pytest pytest-asyncio moto`)
- [ ] `moto` installed for AWS mocking
- [ ] Integration test environment available

## Todo

### 1. Unit Tests: Jobs Repository

**File:** `tests/unit/test_jobs_repository.py`

- [ ] Test `create_job()` with valid data
- [ ] Test `create_job()` with missing required fields
- [ ] Test `get_job()` with existing job_id
- [ ] Test `get_job()` with non-existent job_id
- [ ] Test `get_job_by_idempotency_key()` with existing key
- [ ] Test `get_job_by_idempotency_key()` with non-existent key
- [ ] Test `update_job_status()` transitions
- [ ] Test `update_job()` with multiple fields
- [ ] Test reserved keyword handling (status, error, etc.)
- [ ] Use `@mock_aws` decorator for DynamoDB mocking

### 2. Unit Tests: Submit Handler

**File:** `tests/unit/test_vpr_submit_handler.py`

- [ ] Test new job submission (202 Accepted)
- [ ] Test duplicate job submission (200 OK, idempotent)
- [ ] Test invalid request payload (400 Bad Request)
- [ ] Test DynamoDB error handling (500 Internal Server Error)
- [ ] Test SQS error handling (500 Internal Server Error)
- [ ] Mock SQS `send_message()` call
- [ ] Mock DynamoDB `put_item()` and `query()` calls
- [ ] Verify job_id format (UUID)
- [ ] Verify TTL calculation (10 minutes from now)

### 3. Unit Tests: Worker Handler

**File:** `tests/unit/test_vpr_worker_handler.py`

- [ ] Test successful VPR generation
- [ ] Test VPR generation failure (Claude API error)
- [ ] Test FVS validation failure
- [ ] Test S3 upload failure
- [ ] Test DynamoDB update failure
- [ ] Test SQS batch processing with partial failures
- [ ] Mock Claude API calls
- [ ] Mock S3 `put_object()` call
- [ ] Verify job status transitions (PENDING → PROCESSING → COMPLETED)
- [ ] Verify result stored in S3 with correct key format

### 4. Unit Tests: Status Handler

**File:** `tests/unit/test_vpr_status_handler.py`

- [ ] Test status check for PENDING job (202 Accepted)
- [ ] Test status check for PROCESSING job (202 Accepted)
- [ ] Test status check for COMPLETED job (200 OK with result_url)
- [ ] Test status check for FAILED job (200 OK with error)
- [ ] Test non-existent job (404 Not Found)
- [ ] Test S3 result expired (410 Gone)
- [ ] Mock S3 `generate_presigned_url()` call
- [ ] Verify presigned URL expiry (1 hour)

### 5. Integration Tests: End-to-End Flow

**File:** `tests/integration/test_vpr_async_flow.py`

- [ ] Deploy test stack to dev environment
- [ ] Test complete flow: Submit → Worker → Status → Result
- [ ] Submit VPR job via API Gateway
- [ ] Verify job created in DynamoDB
- [ ] Verify SQS message sent
- [ ] Verify worker Lambda triggered by SQS
- [ ] Poll status endpoint until COMPLETED
- [ ] Fetch VPR result from presigned URL
- [ ] Verify VPR content matches expectations
- [ ] Cleanup: Delete test data from DynamoDB and S3

### 6. Integration Tests: Idempotency

**File:** `tests/integration/test_vpr_idempotency.py`

- [ ] Submit same VPR request twice
- [ ] Verify second request returns existing job_id (200 OK)
- [ ] Verify only ONE job created in DynamoDB
- [ ] Verify only ONE SQS message sent
- [ ] Verify only ONE VPR generated
- [ ] Test idempotency key expiry (24-hour TTL)

### 7. Load Tests: Concurrent Submissions

**File:** `tests/load/test_vpr_concurrent_submissions.py`

- [ ] Use `locust` or `pytest-xdist` for parallel requests
- [ ] Submit 100 concurrent VPR jobs
- [ ] Verify all jobs queued successfully (202 Accepted)
- [ ] Monitor SQS queue depth (should not exceed 100)
- [ ] Verify worker Lambda concurrency (max 5)
- [ ] Monitor DynamoDB throttling (should not occur)
- [ ] Verify all jobs complete within 10 minutes
- [ ] Check CloudWatch metrics: queue depth, Lambda invocations

### 8. Failure Tests: Worker Retries

**File:** `tests/failure/test_vpr_worker_retries.py`

- [ ] Simulate Claude API rate limit error
- [ ] Verify worker retries (SQS visibility timeout)
- [ ] Verify job retried 3 times
- [ ] Verify message moves to DLQ after 3 failures
- [ ] Verify CloudWatch alarm triggered (DLQ messages ≥1)
- [ ] Verify job status updated to FAILED
- [ ] Verify error message stored in job record

### 9. Failure Tests: Timeout Handling

**File:** `tests/failure/test_vpr_timeout.py`

- [ ] Increase worker Lambda timeout to >5 minutes (simulate timeout)
- [ ] Submit VPR job
- [ ] Poll status for 5 minutes
- [ ] Verify client timeout (60 polls)
- [ ] Verify job still in PROCESSING state
- [ ] Verify SQS message eventually processed (or moved to DLQ)

### 10. Performance Tests: Generation Time

**File:** `tests/performance/test_vpr_generation_time.py`

- [ ] Submit 10 VPR jobs sequentially
- [ ] Measure time from submit to COMPLETED
- [ ] Verify p50 < 60 seconds
- [ ] Verify p95 < 90 seconds
- [ ] Verify p99 < 120 seconds
- [ ] Log Claude API token usage
- [ ] Verify cost per VPR < $0.01

## Codex Implementation Guide

### Unit Test Example: Submit Handler

```python
# tests/unit/test_vpr_submit_handler.py

import json
import pytest
from datetime import datetime, timedelta
from moto import mock_aws
import boto3

from careervp.handlers.vpr_submit_handler import lambda_handler


@mock_aws
def test_submit_new_job():
    """Test submitting new VPR job returns 202 Accepted."""
    # Setup mock resources
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create mock tables
    jobs_table = dynamodb.create_table(
        TableName="test-jobs-table",
        KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "job_id", "AttributeType": "S"},
            {"AttributeName": "idempotency_key", "AttributeType": "S"}
        ],
        BillingMode="PAY_PER_REQUEST",
        GlobalSecondaryIndexes=[{
            "IndexName": "idempotency-key-index",
            "KeySchema": [{"AttributeName": "idempotency_key", "KeyType": "HASH"}],
            "Projection": {"ProjectionType": "ALL"}
        }]
    )

    sqs = boto3.client("sqs", region_name="us-east-1")
    queue = sqs.create_queue(QueueName="test-vpr-jobs-queue")
    queue_url = queue["QueueUrl"]

    # Set environment variables
    import os
    os.environ["JOBS_TABLE_NAME"] = "test-jobs-table"
    os.environ["VPR_JOBS_QUEUE_URL"] = queue_url

    # Create test event
    event = {
        "body": json.dumps({
            "user_id": "test-user-123",
            "application_id": "test-app-456",
            "job_posting": {
                "company_name": "Test Company",
                "role_title": "Test Role",
                "responsibilities": ["Test"],
                "requirements": ["Test"]
            }
        })
    }

    # Invoke handler
    response = lambda_handler(event, {})

    # Assertions
    assert response["statusCode"] == 202
    body = json.loads(response["body"])
    assert "job_id" in body
    assert body["status"] == "PENDING"

    # Verify job created in DynamoDB
    job = jobs_table.get_item(Key={"job_id": body["job_id"]})["Item"]
    assert job["status"] == "PENDING"
    assert job["user_id"] == "test-user-123"

    # Verify SQS message sent
    messages = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1)
    assert "Messages" in messages
    assert len(messages["Messages"]) == 1


@mock_aws
def test_submit_duplicate_job():
    """Test submitting duplicate job returns 200 OK with existing job_id."""
    # ... setup ...

    # Submit job twice
    event = {...}
    response1 = lambda_handler(event, {})
    response2 = lambda_handler(event, {})

    # Assertions
    assert response1["statusCode"] == 202  # First: 202 Accepted
    assert response2["statusCode"] == 200  # Second: 200 OK (idempotent)

    body1 = json.loads(response1["body"])
    body2 = json.loads(response2["body"])
    assert body1["job_id"] == body2["job_id"]  # Same job_id

    # Verify only ONE job in DynamoDB
    # Verify only ONE SQS message
```

### Integration Test Example: End-to-End Flow

```python
# tests/integration/test_vpr_async_flow.py

import pytest
import requests
import time
import json


@pytest.mark.integration
def test_vpr_async_end_to_end():
    """Test complete VPR async flow from submit to result."""
    API_BASE = "https://api-dev.careervp.com"

    # 1. SUBMIT VPR JOB
    vpr_request = {
        "user_id": "integration-test-user",
        "application_id": "integration-test-app",
        "job_posting": {
            "company_name": "Test Company",
            "role_title": "Software Engineer",
            "responsibilities": ["Build scalable systems"],
            "requirements": ["5+ years Python experience"]
        }
    }

    response = requests.post(f"{API_BASE}/api/vpr", json=vpr_request)
    assert response.status_code == 202, f"Unexpected status: {response.status_code}"

    data = response.json()
    job_id = data["job_id"]
    assert data["status"] == "PENDING"

    print(f"Job submitted: {job_id}")

    # 2. POLL STATUS UNTIL COMPLETED
    max_polls = 60
    poll_count = 0
    status = None

    while poll_count < max_polls:
        poll_count += 1
        time.sleep(5)

        response = requests.get(f"{API_BASE}/api/vpr/status/{job_id}")
        assert response.status_code in [200, 202], f"Unexpected status: {response.status_code}"

        data = response.json()
        status = data["status"]
        print(f"Poll {poll_count}: {status}")

        if status in ["COMPLETED", "FAILED"]:
            break

    # 3. VERIFY COMPLETION
    assert status == "COMPLETED", f"Job did not complete: {status}"
    assert "result_url" in data, "Result URL missing"

    print(f"Job completed in {poll_count * 5} seconds")

    # 4. FETCH VPR RESULT
    result_url = data["result_url"]
    response = requests.get(result_url)
    assert response.status_code == 200

    vpr_result = response.json()
    assert "executive_summary" in vpr_result
    assert "evidence_matrix" in vpr_result

    print("VPR result fetched successfully")
```

### Load Test Example: Concurrent Submissions

```python
# tests/load/test_vpr_concurrent_submissions.py

import pytest
import requests
import concurrent.futures
import time


@pytest.mark.load
def test_concurrent_vpr_submissions():
    """Test 100 concurrent VPR submissions."""
    API_BASE = "https://api-dev.careervp.com"
    NUM_REQUESTS = 100

    def submit_vpr(index: int) -> dict:
        """Submit single VPR job."""
        vpr_request = {
            "user_id": f"load-test-user-{index}",
            "application_id": f"load-test-app-{index}",
            "job_posting": {
                "company_name": "Test Company",
                "role_title": "Software Engineer",
                "responsibilities": ["Test"],
                "requirements": ["Test"]
            }
        }

        start = time.time()
        response = requests.post(f"{API_BASE}/api/vpr", json=vpr_request)
        duration = time.time() - start

        return {
            "index": index,
            "status_code": response.status_code,
            "duration": duration,
            "job_id": response.json().get("job_id")
        }

    # Submit 100 jobs concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(submit_vpr, range(NUM_REQUESTS)))

    # Verify all succeeded
    successful = [r for r in results if r["status_code"] in [200, 202]]
    assert len(successful) == NUM_REQUESTS, f"Only {len(successful)}/{NUM_REQUESTS} succeeded"

    # Verify response times
    durations = [r["duration"] for r in results]
    p50 = sorted(durations)[len(durations) // 2]
    p95 = sorted(durations)[int(len(durations) * 0.95)]

    print(f"Response times - p50: {p50:.2f}s, p95: {p95:.2f}s")
    assert p50 < 3.0, f"p50 too slow: {p50:.2f}s"
    assert p95 < 5.0, f"p95 too slow: {p95:.2f}s"
```

## Verification Commands

### Run Unit Tests

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Run all unit tests
uv run pytest tests/unit/test_jobs_repository.py -v
uv run pytest tests/unit/test_vpr_submit_handler.py -v
uv run pytest tests/unit/test_vpr_worker_handler.py -v
uv run pytest tests/unit/test_vpr_status_handler.py -v

# Run with coverage
uv run pytest tests/unit/ --cov=careervp --cov-report=html
```

### Run Integration Tests

```bash
# Deploy to dev environment first
cd infra && cdk deploy --all

# Run integration tests
cd ../src/backend
uv run pytest tests/integration/ -v -m integration

# Run specific test
uv run pytest tests/integration/test_vpr_async_flow.py::test_vpr_async_end_to_end -v
```

### Run Load Tests

```bash
# Install load testing dependencies
uv add locust

# Run load test
cd tests/load
locust -f test_vpr_concurrent_submissions.py --headless -u 100 -r 10 -t 5m

# Or use pytest
uv run pytest tests/load/ -v -m load
```

### Run Failure Tests

```bash
# Run failure tests
uv run pytest tests/failure/ -v -m failure

# Check CloudWatch alarms
aws cloudwatch describe-alarms --alarm-names careervp-vpr-dlq-alarm-dev
```

## Acceptance Criteria

- [ ] All unit tests pass (100% coverage on new code)
- [ ] All integration tests pass
- [ ] Load test: 100 concurrent submissions succeed
- [ ] Response time p95 < 3 seconds for submit endpoint
- [ ] VPR generation time p95 < 90 seconds
- [ ] Idempotency works (duplicate requests return same job_id)
- [ ] Worker retries 3 times before DLQ
- [ ] DLQ alarm triggers on failures
- [ ] Timeout handling works (client stops after 5 minutes)
- [ ] Cost per VPR < $0.01

## Dependencies

**Blocks:**
- Task 7.8 (Deployment) - must pass all tests before production deploy

**Blocked By:**
- Tasks 7.1-7.6 (Implementation) - must be complete before testing

## Estimated Effort

**Time:** 8-12 hours
**Complexity:** MEDIUM-HIGH (comprehensive test coverage across all components)

## Notes

- Use `@mock_aws` decorator from `moto` for AWS service mocking
- Integration tests require deployed dev environment
- Load tests should run in isolated test environment
- Clean up test data after integration tests (DynamoDB, S3)
- Monitor CloudWatch during load tests for throttling
- Document any flaky tests and root causes
