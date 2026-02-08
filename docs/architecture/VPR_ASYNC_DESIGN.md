# Async Task Pattern - Foundation Design

## Overview

This document defines the **Async Task Pattern** foundation for CareerVP features that require long-running LLM processing (>30 seconds). The pattern uses **SQS + Polling** to provide a responsive user experience while processing complex requests asynchronously.

## Problem Statement

Current synchronous Lambda handlers (VPR generation, CV parsing) have limitations:
- **Timeout risk:** Lambda max execution time is 15 minutes, but API Gateway timeout is 30 seconds
- **Poor UX:** Users see loading spinners for 30+ seconds with no progress indication
- **Wasted resources:** Frontend must maintain HTTP connection during entire processing
- **No retry mechanism:** Transient LLM failures require full re-submission

## Solution: SQS + Polling Pattern

```
┌─────────────────────────────────────────────────────────────────────┐
│                      ASYNC TASK FLOW                                 │
└─────────────────────────────────────────────────────────────────────┘

[Frontend]                                                    [Backend]
    │
    │ POST /api/{feature}/submit
    │ { user_cv, job_posting, ... }
    │────────────────────────────────────────────────────────────────>
    │                                          [Submit Handler]
    │                                                  │
    │                                                  │ 1. Validate request
    │                                                  │ 2. Create job record (PENDING)
    │                                                  │ 3. Send to SQS queue
    │                                                  │ 4. Return 202 + job_id
    │ 202 ACCEPTED
    │ { job_id, status: "PENDING" }
    │<────────────────────────────────────────────────────────────────
    │
    │                                          [SQS Queue]
    │                                                  │
    │                                                  │ (async trigger)
    │                                                  ▼
    │                                          [Worker Handler]
    │                                                  │
    │                                                  │ 1. Receive SQS message
    │                                                  │ 2. Update status (PROCESSING)
    │                                                  │ 3. Call LLM API
    │                                                  │ 4. Save result to S3
    │                                                  │ 5. Update status (COMPLETED)
    │                                                  │ 6. Delete SQS message
    │
    │ GET /api/{feature}/status/{job_id}
    │────────────────────────────────────────────────────────────────>
    │                                          [Status Handler]
    │                                                  │
    │                                                  │ 1. Query DynamoDB by job_id
    │                                                  │ 2. Return status + result_url
    │ 200 OK
    │ { status: "COMPLETED", result_url: "..." }
    │<────────────────────────────────────────────────────────────────
    │
    │ GET {result_url}
    │────────────────────────────────────────────────────────────────>
    │                                          [S3 Presigned URL]
    │ 200 OK
    │ { /* feature-specific result */ }
    │<────────────────────────────────────────────────────────────────
```

## Architecture Components

### 1. Submit Handler (`{feature}_submit_handler.py`)

**Responsibilities:**
- Validate user input (Pydantic models)
- Enforce security limits (10MB file size via `validation.py`)
- Create job record in DynamoDB with status `PENDING`
- Send job metadata to SQS queue
- Return `202 ACCEPTED` with `job_id`

**Signature:**
```python
@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """
    POST /api/{feature}/submit
    Returns: 202 ACCEPTED with job_id
    """
```

**Response:**
```json
{
  "job_id": "01234567-89ab-cdef-0123-456789abcdef",
  "status": "PENDING",
  "created_at": "2025-02-04T12:00:00Z"
}
```

### 2. Worker Handler (`{feature}_worker_handler.py`)

**Responsibilities:**
- Triggered by SQS event (batch size = 1)
- Update job status to `PROCESSING`
- Execute feature-specific logic (LLM calls)
- Handle timeouts with `asyncio.wait_for()`
- Save results to S3
- Update job status to `COMPLETED` or `FAILED`
- Delete SQS message on success
- Allow retry on transient failures (SQS visibility timeout)

**Signature:**
```python
@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """
    SQS-triggered worker for async processing.
    """
```

**Timeout Pattern:**
```python
import asyncio

async def process_with_timeout(job_data: dict) -> Result[T]:
    try:
        result = await asyncio.wait_for(
            process_job(job_data),
            timeout=600  # 10 minutes
        )
        return result
    except asyncio.TimeoutError:
        return Result(
            success=False,
            error="Processing timeout after 10 minutes",
            code=ResultCode.TIMEOUT
        )
```

### 3. Status Handler (`{feature}_status_handler.py`)

**Responsibilities:**
- Query DynamoDB by `job_id` using GSI
- Return current status and metadata
- Generate presigned S3 URL for `COMPLETED` jobs
- Return error details for `FAILED` jobs

**Signature:**
```python
@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """
    GET /api/{feature}/status/{job_id}
    Returns: Job status and result_url if completed
    """
```

**Response (PENDING):**
```json
{
  "job_id": "...",
  "status": "PENDING",
  "created_at": "2025-02-04T12:00:00Z"
}
```

**Response (PROCESSING):**
```json
{
  "job_id": "...",
  "status": "PROCESSING",
  "created_at": "2025-02-04T12:00:00Z",
  "started_at": "2025-02-04T12:00:05Z"
}
```

**Response (COMPLETED):**
```json
{
  "job_id": "...",
  "status": "COMPLETED",
  "created_at": "2025-02-04T12:00:00Z",
  "completed_at": "2025-02-04T12:01:30Z",
  "result_url": "https://s3.amazonaws.com/careervp-results/.../result.json?X-Amz-..."
}
```

**Response (FAILED):**
```json
{
  "job_id": "...",
  "status": "FAILED",
  "created_at": "2025-02-04T12:00:00Z",
  "failed_at": "2025-02-04T12:00:45Z",
  "error": "LLM API rate limit exceeded",
  "code": "LLM_API_ERROR"
}
```

### 4. Jobs DAL (`dal/jobs_dal_handler.py`)

**New methods required:**

```python
from careervp.dal.db_handler import DalHandler

class JobsDalHandler(DalHandler):
    """DAL for async job tracking."""

    def create_job(
        self,
        job_id: str,
        user_id: str,
        feature: str,
        request_data: dict
    ) -> Result[None]:
        """Create job with PENDING status."""

    def update_job_status(
        self,
        job_id: str,
        status: Literal["PENDING", "PROCESSING", "COMPLETED", "FAILED"],
        result_s3_key: str | None = None,
        error: str | None = None,
        code: str | None = None
    ) -> Result[None]:
        """Update job status and metadata."""

    def get_job(self, job_id: str) -> Result[dict]:
        """Get job by job_id (using GSI)."""

    def get_user_jobs(
        self,
        user_id: str,
        feature: str | None = None
    ) -> Result[list[dict]]:
        """Get all jobs for a user, optionally filtered by feature."""
```

**DynamoDB Schema:**

```python
{
    "pk": f"JOB#{job_id}",                    # Partition key
    "sk": "METADATA",                          # Sort key
    "gsi1pk": f"USER#{user_id}",              # GSI partition key
    "gsi1sk": f"JOB#{feature}#{created_at}",  # GSI sort key
    "job_id": "01234567-89ab-cdef-0123-456789abcdef",
    "user_id": "user_123",
    "feature": "gap_analysis",                 # or "vpr", "interview_prep"
    "status": "COMPLETED",                     # PENDING | PROCESSING | COMPLETED | FAILED
    "request_data": { /* original request */ },
    "result_s3_key": "jobs/gap-analysis/...",
    "error": null,
    "code": "GAP_QUESTIONS_GENERATED",
    "created_at": "2025-02-04T12:00:00Z",
    "started_at": "2025-02-04T12:00:05Z",
    "completed_at": "2025-02-04T12:01:30Z",
    "ttl": 1738684800  # Auto-delete after 7 days
}
```

## Infrastructure Requirements

### 1. SQS Queue

```python
# infra/api_construct.py

from aws_cdk import aws_sqs as sqs
from careervp.constants import NamingUtils

# Main queue
gap_analysis_queue = sqs.Queue(
    self,
    "GapAnalysisQueue",
    queue_name=NamingUtils.queue_name("gap-analysis", environment),
    visibility_timeout=Duration.seconds(900),  # 15 minutes (Lambda timeout + buffer)
    retention_period=Duration.days(7),
    dead_letter_queue=sqs.DeadLetterQueue(
        max_receive_count=3,
        queue=gap_analysis_dlq
    )
)

# Dead letter queue
gap_analysis_dlq = sqs.Queue(
    self,
    "GapAnalysisDLQ",
    queue_name=NamingUtils.dlq_name("gap-analysis", environment),
    retention_period=Duration.days(14)
)
```

### 2. DynamoDB GSI

```python
# Add GSI to existing careervp-jobs-table-dev

jobs_table.add_global_secondary_index(
    index_name="gsi1",
    partition_key=dynamodb.Attribute(
        name="gsi1pk",
        type=dynamodb.AttributeType.STRING
    ),
    sort_key=dynamodb.Attribute(
        name="gsi1sk",
        type=dynamodb.AttributeType.STRING
    ),
    projection_type=dynamodb.ProjectionType.ALL
)
```

### 3. Lambda Functions

```python
# Submit handler
gap_submit_fn = lambda_.Function(
    self,
    "GapSubmitHandler",
    function_name=NamingUtils.lambda_name("gap-submit", environment),
    runtime=lambda_.Runtime.PYTHON_3_12,
    handler="careervp.handlers.gap_submit_handler.lambda_handler",
    timeout=Duration.seconds(30),
    environment={
        "JOBS_TABLE_NAME": jobs_table.table_name,
        "QUEUE_URL": gap_analysis_queue.queue_url
    }
)

# Worker handler
gap_worker_fn = lambda_.Function(
    self,
    "GapWorkerHandler",
    function_name=NamingUtils.lambda_name("gap-worker", environment),
    runtime=lambda_.Runtime.PYTHON_3_12,
    handler="careervp.handlers.gap_analysis_worker.lambda_handler",
    timeout=Duration.seconds(900),  # 15 minutes
    memory_size=1024,
    environment={
        "JOBS_TABLE_NAME": jobs_table.table_name,
        "RESULTS_BUCKET_NAME": results_bucket.bucket_name
    }
)

# SQS trigger for worker
gap_worker_fn.add_event_source(
    lambda_event_sources.SqsEventSource(
        gap_analysis_queue,
        batch_size=1,
        max_batching_window=Duration.seconds(0)
    )
)

# Status handler
gap_status_fn = lambda_.Function(
    self,
    "GapStatusHandler",
    function_name=NamingUtils.lambda_name("gap-status", environment),
    runtime=lambda_.Runtime.PYTHON_3_12,
    handler="careervp.handlers.gap_status_handler.lambda_handler",
    timeout=Duration.seconds(30),
    environment={
        "JOBS_TABLE_NAME": jobs_table.table_name,
        "RESULTS_BUCKET_NAME": results_bucket.bucket_name
    }
)
```

### 4. API Gateway Routes

```python
# POST /api/gap-analysis/submit
gap_analysis_resource = api.root.add_resource("gap-analysis")
submit_resource = gap_analysis_resource.add_resource("submit")
submit_resource.add_method(
    "POST",
    apigw.LambdaIntegration(gap_submit_fn),
    authorization_type=apigw.AuthorizationType.COGNITO,
    authorizer=authorizer
)

# GET /api/gap-analysis/status/{job_id}
status_resource = gap_analysis_resource.add_resource("status")
job_id_resource = status_resource.add_resource("{job_id}")
job_id_resource.add_method(
    "GET",
    apigw.LambdaIntegration(gap_status_fn),
    authorization_type=apigw.AuthorizationType.COGNITO,
    authorizer=authorizer
)
```

## Reusable Foundation: `handlers/utils/async_task.py`

Create abstract base class for async handlers:

```python
"""
Reusable async task handler foundation.
Per docs/architecture/VPR_ASYNC_DESIGN.md.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from careervp.dal.db_handler import DalHandler
from careervp.models import Result

T = TypeVar('T')

class AsyncTaskHandler(ABC, Generic[T]):
    """
    Abstract base for async task handlers following SQS + Polling pattern.

    Subclasses must implement:
    - validate_request(): Validate and parse request data
    - process(): Execute feature-specific logic (LLM calls)
    """

    def __init__(self, dal: DalHandler, queue_url: str, results_bucket: str):
        """
        Args:
            dal: Data access layer for job tracking
            queue_url: SQS queue URL for job submission
            results_bucket: S3 bucket name for storing results
        """
        self.dal = dal
        self.queue_url = queue_url
        self.results_bucket = results_bucket

    @abstractmethod
    def validate_request(self, request_data: dict) -> Result[T]:
        """
        Validate and parse request data using Pydantic models.

        Returns:
            Result[T] with parsed request object or validation error
        """
        pass

    @abstractmethod
    async def process(self, job_id: str, request: T) -> Result[dict]:
        """
        Execute feature-specific processing logic.

        Args:
            job_id: Unique job identifier
            request: Parsed and validated request object

        Returns:
            Result[dict] with processing output or error
        """
        pass

    def submit(self, user_id: str, request_data: dict, feature: str) -> Result[str]:
        """
        Submit job for async processing.

        Returns:
            Result[str] with job_id
        """
        # 1. Validate request
        # 2. Create job record (PENDING)
        # 3. Send to SQS
        # 4. Return job_id

    async def execute(self, job_id: str) -> Result[dict]:
        """
        Worker execution logic with timeout handling.

        Returns:
            Result[dict] with processing output or error
        """
        # 1. Update status (PROCESSING)
        # 2. Call process() with timeout
        # 3. Save to S3
        # 4. Update status (COMPLETED/FAILED)

    def poll(self, job_id: str) -> Result[dict]:
        """
        Poll job status.

        Returns:
            Result[dict] with status and result_url (if completed)
        """
        # 1. Query job from DynamoDB
        # 2. Generate presigned URL if completed
        # 3. Return status metadata
```

## Security & Validation: `handlers/utils/validation.py`

```python
"""
Security validation utilities for CareerVP handlers.
Per Class Topology Analysis - Rule 2.
"""

from typing import Annotated
from pydantic import BaseModel, Field, field_validator

# Security constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_TEXT_LENGTH = 1_000_000       # 1M characters

def validate_file_size(content: bytes) -> None:
    """
    Validate file size does not exceed 10MB limit.

    Args:
        content: File content as bytes

    Raises:
        ValueError: If content exceeds MAX_FILE_SIZE
    """
    if len(content) > MAX_FILE_SIZE:
        raise ValueError(
            f"File size {len(content)} bytes exceeds maximum {MAX_FILE_SIZE} bytes (10MB)"
        )

def validate_text_length(text: str) -> None:
    """
    Validate text length for LLM inputs.

    Args:
        text: Text content

    Raises:
        ValueError: If text exceeds MAX_TEXT_LENGTH
    """
    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError(
            f"Text length {len(text)} exceeds maximum {MAX_TEXT_LENGTH} characters"
        )
```

## Job Status State Machine

```
PENDING ──────> PROCESSING ──────> COMPLETED
                    │
                    └──────────────> FAILED
```

**State Transitions:**
- `PENDING → PROCESSING`: Worker starts processing
- `PROCESSING → COMPLETED`: Successful LLM response, result saved to S3
- `PROCESSING → FAILED`: LLM error, timeout, or validation failure

**TTL:** All job records auto-delete after 7 days (configurable)

## Error Handling & Retries

### SQS Visibility Timeout
- **Visibility timeout:** 900 seconds (15 minutes)
- **Lambda timeout:** 900 seconds (15 minutes)
- **Max receive count:** 3 (then send to DLQ)

### Retry Strategy
- **Transient LLM errors:** Retry automatically (SQS re-delivery)
- **Rate limit errors:** Retry with exponential backoff
- **Validation errors:** No retry (permanent failure)
- **Timeout errors:** No retry (permanent failure)

### DLQ Monitoring
- Set CloudWatch alarm on DLQ message count > 0
- Manual intervention required for DLQ messages

## Frontend Polling Strategy

```typescript
async function pollJobStatus(jobId: string): Promise<GapAnalysisResult> {
  const maxAttempts = 60;  // 5 minutes max (60 * 5s)
  const pollInterval = 5000;  // 5 seconds

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const response = await fetch(`/api/gap-analysis/status/${jobId}`);
    const data = await response.json();

    if (data.status === 'COMPLETED') {
      // Fetch result from S3
      const result = await fetch(data.result_url);
      return result.json();
    }

    if (data.status === 'FAILED') {
      throw new Error(data.error);
    }

    // PENDING or PROCESSING - wait and retry
    await new Promise(resolve => setTimeout(resolve, pollInterval));
  }

  throw new Error('Job processing timeout - please check status later');
}
```

## Observability

### CloudWatch Metrics
- **Custom metrics via AWS Powertools:**
  - `JobsSubmitted` - Count of submitted jobs
  - `JobsCompleted` - Count of successful completions
  - `JobsFailed` - Count of failures
  - `ProcessingDuration` - Time from PENDING to COMPLETED
  - `LLMLatency` - LLM API response time

### Logging
- All handlers use `@logger.inject_lambda_context(log_event=True)`
- Structured logs with job_id for correlation
- X-Ray tracing enabled via `@tracer.capture_lambda_handler()`

### Alarms
- DLQ message count > 0
- Worker Lambda errors > 5% of invocations
- Processing duration > 10 minutes (99th percentile)

## Testing Strategy

### Unit Tests
- `test_async_task_handler.py` - Base class logic
- `test_validation.py` - Security validation (10MB limit)
- `test_jobs_dal.py` - DAL operations

### Integration Tests
- `test_{feature}_submit.py` - Submit handler (mock SQS)
- `test_{feature}_worker.py` - Worker handler (mock LLM)
- `test_{feature}_status.py` - Status handler (mock DynamoDB)

### Infrastructure Tests
- `test_{feature}_stack.py` - CDK assertions (SQS, DLQ, DynamoDB GSI)

### E2E Tests
- `test_{feature}_async_flow.py` - Full flow from submit → poll → result

## Implementation Checklist

- [ ] Create `handlers/utils/async_task.py` (base class)
- [ ] Create `handlers/utils/validation.py` (10MB limit)
- [ ] Add DynamoDB GSI for job queries
- [ ] Create SQS queue and DLQ for feature
- [ ] Implement submit handler (POST /submit)
- [ ] Implement worker handler (SQS-triggered)
- [ ] Implement status handler (GET /status/{job_id})
- [ ] Add DAL methods for job tracking
- [ ] Configure API Gateway routes
- [ ] Add CloudWatch alarms
- [ ] Write unit tests (90%+ coverage)
- [ ] Write integration tests
- [ ] Write infrastructure tests
- [ ] Write E2E tests
- [ ] Update CICD pipeline for async tests

## References

- **Naming conventions:** `infra/careervp/constants.py` - `NamingUtils` class
- **Result pattern:** `src/backend/careervp/models/result.py` - `Result[T]` generic
- **DAL abstraction:** `src/backend/careervp/dal/db_handler.py` - `DalHandler` base class
- **Existing handler examples:** `src/backend/careervp/handlers/vpr_handler.py`
- **AWS Powertools:** https://docs.powertools.aws.dev/lambda/python/
