# Task 7.2: VPR Submit Handler (Async Submission)

**Status:** Not Started
**Spec Reference:** [[docs/specs/07-vpr-async-architecture.md]]
**Priority:** P0 (BLOCKING - Production VPR generation fails 100%)

## Overview

Refactor the existing synchronous VPR handler into an async submit handler that creates job records and queues VPR generation work. This handler returns `202 Accepted` with a `job_id` instead of blocking for 30-60 seconds.

## Prerequisites

- [ ] Task 7.1 complete (infrastructure deployed)
- [ ] `careervp-jobs-table-dev` exists with GSI
- [ ] `careervp-vpr-jobs-queue-dev` exists
- [ ] Existing `src/backend/careervp/handlers/vpr_handler.py` present

## Todo

### 1. Create Submit Handler File

- [ ] Create `src/backend/careervp/handlers/vpr_submit_handler.py`
- [ ] Copy imports from existing `vpr_handler.py`
- [ ] Add new imports for SQS, jobs table, UUID

### 2. Implement Idempotency Check

- [ ] Import `jobs_repository.py` (created in Task 7.5)
- [ ] Extract `user_id` and `application_id` from request body
- [ ] Generate idempotency key: `f"vpr#{user_id}#{application_id}"`
- [ ] Query GSI by idempotency key using `jobs_repository.get_job_by_idempotency_key()`
- [ ] If job exists, return `200 OK` with existing `job_id` and status

### 3. Create Job Record

- [ ] Generate `job_id` using `uuid.uuid4()`
- [ ] Calculate TTL: `int((datetime.utcnow() + timedelta(minutes=10)).timestamp())`
- [ ] Create job record in DynamoDB:
  - `job_id` (PK)
  - `idempotency_key`
  - `user_id`
  - `application_id`
  - `status`: `"PENDING"`
  - `created_at`: ISO timestamp
  - `input_data`: Request payload
  - `ttl`: 10-minute expiration
- [ ] Use `jobs_repository.create_job()` method

### 4. Queue Job to SQS

- [ ] Import `boto3` SQS client
- [ ] Get queue URL from environment variable `VPR_JOBS_QUEUE_URL`
- [ ] Send message to SQS with:
  - `MessageBody`: JSON with `job_id` and `input_data`
  - Optional: `MessageAttributes` for tracing
- [ ] Handle SQS errors gracefully (log + return 500)

### 5. Return Response

- [ ] Return `202 Accepted` for new jobs
- [ ] Return `200 OK` for duplicate/idempotent requests
- [ ] Response body includes:
  - `job_id`
  - `status`
  - `message`

### 6. Update Lambda Configuration (CDK)

**File:** `infra/careervp/api_construct.py`

- [ ] Rename Lambda from `vpr-generator-lambda` to `vpr-submit-lambda`
- [ ] Update function name: `careervp-vpr-submit-lambda-dev`
- [ ] Update handler: `careervp.handlers.vpr_submit_handler.lambda_handler`
- [ ] Reduce timeout: 10 seconds (was 120s)
- [ ] Reduce memory: 256 MB (was 1024 MB)
- [ ] Add environment variables:
  - `JOBS_TABLE_NAME`
  - `IDEMPOTENCY_TABLE_NAME`
  - `VPR_JOBS_QUEUE_URL`
- [ ] Grant permissions:
  - `dynamodb:PutItem` on jobs table
  - `dynamodb:Query` on GSI
  - `sqs:SendMessage` on queue

### 7. Update API Gateway Route

**File:** `infra/careervp/api_construct.py`

- [ ] Verify `POST /api/vpr` route points to new submit Lambda
- [ ] Ensure integration timeout is sufficient (10s Lambda + API overhead)

### 8. Error Handling

- [ ] Wrap all operations in try/except
- [ ] Handle `ValidationError` from Pydantic (400 Bad Request)
- [ ] Handle DynamoDB errors (500 Internal Server Error)
- [ ] Handle SQS errors (500 Internal Server Error)
- [ ] Log all errors with context (job_id, user_id, application_id)

## Codex Implementation Guide

### File Structure

```
src/backend/careervp/handlers/
├── vpr_handler.py               # OLD (keep for rollback)
├── vpr_submit_handler.py        # NEW (this task)
└── vpr_worker_handler.py        # Task 7.3
```

### Implementation: vpr_submit_handler.py

```python
"""
VPR Submit Handler (Async Submission)

Accepts VPR generation request, creates job record, queues to SQS, returns 202 Accepted.
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Any

import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from careervp.dal.jobs_repository import JobsRepository
from careervp.models.vpr import VPRRequest

logger = Logger()
tracer = Tracer()

sqs = boto3.client("sqs")
jobs_repo = JobsRepository(
    table_name=os.environ["JOBS_TABLE_NAME"],
    idempotency_index_name="idempotency-key-index"
)

QUEUE_URL = os.environ["VPR_JOBS_QUEUE_URL"]


@tracer.capture_lambda_handler
@logger.inject_lambda_context
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """
    Submit VPR generation job.

    Returns:
        - 202 Accepted with job_id (new job)
        - 200 OK with job_id (duplicate/idempotent request)
        - 400 Bad Request (validation error)
        - 500 Internal Server Error (system error)
    """
    try:
        # 1. PARSE REQUEST
        body = json.loads(event.get("body", "{}"))
        request = VPRRequest.model_validate(body)

        # 2. GENERATE IDEMPOTENCY KEY
        idempotency_key = f"vpr#{request.user_id}#{request.application_id}"

        # 3. CHECK FOR DUPLICATE REQUEST
        existing_job = jobs_repo.get_job_by_idempotency_key(idempotency_key)
        if existing_job:
            logger.info(
                "Duplicate VPR request detected",
                extra={
                    "job_id": existing_job["job_id"],
                    "status": existing_job["status"],
                    "idempotency_key": idempotency_key
                }
            )
            return {
                "statusCode": 200,  # 200 OK for idempotent requests
                "body": json.dumps({
                    "job_id": existing_job["job_id"],
                    "status": existing_job["status"],
                    "message": "Job already exists"
                })
            }

        # 4. CREATE NEW JOB
        job_id = str(uuid.uuid4())
        ttl = int((datetime.utcnow() + timedelta(minutes=10)).timestamp())

        job_data = {
            "job_id": job_id,
            "idempotency_key": idempotency_key,
            "user_id": request.user_id,
            "application_id": request.application_id,
            "status": "PENDING",
            "created_at": datetime.utcnow().isoformat(),
            "input_data": request.model_dump(),
            "ttl": ttl
        }

        jobs_repo.create_job(job_data)

        logger.info(
            "Created VPR job",
            extra={
                "job_id": job_id,
                "user_id": request.user_id,
                "application_id": request.application_id
            }
        )

        # 5. QUEUE JOB TO SQS
        message_body = {
            "job_id": job_id,
            "input_data": request.model_dump()
        }

        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(message_body),
            MessageAttributes={
                "job_id": {"StringValue": job_id, "DataType": "String"},
                "user_id": {"StringValue": request.user_id, "DataType": "String"}
            }
        )

        logger.info(
            "Queued VPR job to SQS",
            extra={"job_id": job_id, "queue_url": QUEUE_URL}
        )

        # 6. RETURN 202 ACCEPTED
        return {
            "statusCode": 202,
            "body": json.dumps({
                "job_id": job_id,
                "status": "PENDING",
                "message": "VPR generation job submitted successfully"
            })
        }

    except Exception as e:
        logger.exception("Failed to submit VPR job", extra={"error": str(e)})
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal server error",
                "message": "Failed to submit VPR generation job"
            })
        }
```

### CDK Lambda Configuration

```python
# infra/careervp/api_construct.py

from aws_cdk import Duration, aws_lambda

# UPDATE: Rename from vpr-generator-lambda to vpr-submit-lambda
self.vpr_submit_lambda = aws_lambda.Function(
    self, "VprSubmitLambda",
    function_name=f"careervp-vpr-submit-lambda-{env}",
    runtime=aws_lambda.Runtime.PYTHON_3_14,
    handler="careervp.handlers.vpr_submit_handler.lambda_handler",
    code=aws_lambda.Code.from_asset("../src/backend"),
    timeout=Duration.seconds(10),  # Fast submission
    memory_size=256,
    environment={
        "JOBS_TABLE_NAME": self.jobs_table.table_name,
        "IDEMPOTENCY_TABLE_NAME": self.idempotency_table.table_name,
        "VPR_JOBS_QUEUE_URL": self.vpr_jobs_queue.queue_url,
        "ENVIRONMENT": env,
        "LOG_LEVEL": "INFO",
        "POWERTOOLS_SERVICE_NAME": "vpr-submit"
    },
    tracing=aws_lambda.Tracing.ACTIVE
)

# Grant permissions
self.jobs_table.grant_read_write_data(self.vpr_submit_lambda)
self.idempotency_table.grant_read_data(self.vpr_submit_lambda)  # Read-only for idempotency check
self.vpr_jobs_queue.grant_send_messages(self.vpr_submit_lambda)

# Update API Gateway route (should already exist from Phase 7)
self.api.add_routes(
    path="/api/vpr",
    methods=[aws_apigatewayv2.HttpMethod.POST],
    integration=aws_apigatewayv2_integrations.HttpLambdaIntegration(
        "VprSubmitIntegration",
        self.vpr_submit_lambda
    )
)
```

## Verification Commands

### Local Validation

```bash
# 1. Code formatting
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run ruff format careervp/handlers/vpr_submit_handler.py

# 2. Linting
uv run ruff check careervp/handlers/vpr_submit_handler.py --fix

# 3. Type checking
uv run mypy careervp/handlers/vpr_submit_handler.py --strict

# 4. Unit tests
uv run pytest tests/unit/test_vpr_submit_handler.py -v
```

### Post-Deployment Testing

```bash
# 5. Test new job submission
curl -X POST https://api-dev.careervp.com/api/vpr \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-123",
    "application_id": "test-app-456",
    "job_posting": {
      "company_name": "Test Company",
      "role_title": "Test Role",
      "responsibilities": ["Test responsibility"],
      "requirements": ["Test requirement"]
    }
  }'

# Expected: 202 Accepted with job_id

# 6. Test duplicate request (idempotency)
# Re-run same request
curl -X POST https://api-dev.careervp.com/api/vpr \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-123",
    "application_id": "test-app-456",
    "job_posting": {...}
  }'

# Expected: 200 OK with existing job_id

# 7. Verify job record in DynamoDB
aws dynamodb get-item \
  --table-name careervp-jobs-table-dev \
  --key '{"job_id": {"S": "JOB_ID_FROM_RESPONSE"}}'

# 8. Verify SQS message
aws sqs receive-message \
  --queue-url $(aws sqs get-queue-url --queue-name careervp-vpr-jobs-queue-dev --query 'QueueUrl' --output text) \
  --max-number-of-messages 1

# 9. Check CloudWatch Logs
aws logs tail /aws/lambda/careervp-vpr-submit-lambda-dev --follow
```

## Acceptance Criteria

- [ ] Submit handler returns `202 Accepted` for new requests
- [ ] Submit handler returns `200 OK` for duplicate requests (idempotency works)
- [ ] Job record created in DynamoDB with correct schema
- [ ] SQS message sent to queue with job payload
- [ ] Lambda timeout reduced to 10 seconds
- [ ] Lambda memory reduced to 256 MB
- [ ] All permissions granted (DynamoDB, SQS)
- [ ] Code passes ruff, mypy, and unit tests
- [ ] API Gateway route updated
- [ ] CloudWatch Logs show successful job submission

## Dependencies

**Blocks:**
- Task 7.3 (Worker Handler) - worker needs SQS messages from submit handler
- Task 7.6 (Frontend Polling) - frontend needs 202 response with job_id

**Blocked By:**
- Task 7.1 (Infrastructure) - needs jobs table + SQS queue
- Task 7.5 (Jobs Repository) - needs DAL methods for job CRUD

## Estimated Effort

**Time:** 4-6 hours
**Complexity:** MEDIUM (refactoring existing handler + idempotency logic)

## Notes

- Keep old `vpr_handler.py` for rollback safety
- Use feature flag or API Gateway routing to switch between sync/async
- Idempotency key format: `vpr#{user_id}#{application_id}` (24h TTL)
- Submit handler should complete in <1 second (fast job creation + queue)
