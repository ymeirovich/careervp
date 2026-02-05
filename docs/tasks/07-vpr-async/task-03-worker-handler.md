# Task 7.3: VPR Worker Handler (Async Processing)

**Status:** Not Started
**Spec Reference:** [[docs/specs/07-vpr-async-architecture.md]]
**Priority:** P0 (BLOCKING - Production VPR generation fails 100%)

## Overview

Create the VPR Worker Lambda that processes VPR generation jobs from SQS. This Lambda is triggered by SQS events, generates VPR using Claude Sonnet 4.5 (30-60s), validates with FVS, stores results in S3, and updates job status in DynamoDB.

## Prerequisites

- [ ] Task 7.1 complete (infrastructure deployed)
- [ ] Task 7.2 complete (submit handler queuing jobs to SQS)
- [ ] Existing VPR generation logic in `src/backend/careervp/logic/vpr_generator.py`
- [ ] Existing FVS validator in `src/backend/careervp/logic/fvs_validator.py`

## Todo

### 1. Create Worker Handler File

- [ ] Create `src/backend/careervp/handlers/vpr_worker_handler.py`
- [ ] Import existing VPR generation logic from `logic/vpr_generator.py`
- [ ] Import FVS validator from `logic/fvs_validator.py`
- [ ] Import jobs repository from `dal/jobs_repository.py`
- [ ] Import Lambda Powertools batch processor

### 2. Implement Batch Processing

- [ ] Use `aws_lambda_powertools.utilities.batch.BatchProcessor`
- [ ] Set `event_type=EventType.SQS`
- [ ] Enable `report_batch_item_failures=True` for partial batch responses
- [ ] Process messages one at a time (batch_size=1 in SQS trigger)

### 3. Implement VPR Processing Logic

For each SQS message:

- [ ] Parse message body to extract `job_id` and `input_data`
- [ ] Update job status to `"PROCESSING"` in DynamoDB
- [ ] Fetch user CV from `users-table` using `application_id`
- [ ] Call existing `vpr_generator.generate_vpr()` with:
  - `VPRRequest` from input_data
  - User CV data
  - DAL handler
  - Gap responses (if provided)
- [ ] Validate VPR result with FVS
- [ ] Store VPR result in S3 bucket
- [ ] Update job status to `"COMPLETED"` in DynamoDB
- [ ] Store final VPR in users table (existing pattern: `ARTIFACT#VPR`)

### 4. Error Handling

- [ ] Wrap VPR generation in try/except
- [ ] On failure:
  - Update job status to `"FAILED"` in DynamoDB
  - Log error with job_id context
  - Re-raise exception to trigger SQS retry
- [ ] Handle partial batch failures (Lambda Powertools)
- [ ] After 3 retries, message moves to DLQ automatically

### 5. S3 Result Storage

- [ ] Generate result key: `f"results/{job_id}.json"`
- [ ] Store VPR JSON in S3 with:
  - Content-Type: `application/json`
  - Metadata: `job_id`, `user_id`, `application_id`
- [ ] Store result_key in DynamoDB job record

### 6. Create Worker Lambda (CDK)

**File:** `infra/careervp/api_construct.py`

- [ ] Create worker Lambda function:
  - Function name: `careervp-vpr-worker-lambda-dev`
  - Handler: `careervp.handlers.vpr_worker_handler.lambda_handler`
  - Timeout: 300 seconds (5 minutes)
  - Memory: 1024 MB
  - Reserved concurrency: 5 (cost control)
- [ ] Add environment variables:
  - `JOBS_TABLE_NAME`
  - `USERS_TABLE_NAME`
  - `VPR_RESULTS_BUCKET_NAME`
  - `ANTHROPIC_API_KEY_PARAM` (SSM parameter path)
- [ ] Add SQS event source:
  - Queue: `vpr_jobs_queue`
  - Batch size: 1 (process one job at a time)
  - Max batching window: 0 seconds
  - Report batch item failures: True
- [ ] Grant permissions:
  - `dynamodb:GetItem` on users table (read-only)
  - `dynamodb:UpdateItem` on jobs table
  - `s3:PutObject` on results bucket
  - `ssm:GetParameter` for Anthropic API key

### 7. Update CloudWatch Alarm

**File:** `infra/careervp/api_construct.py`

- [ ] Update worker errors alarm (created in Task 7.1):
  - Metric: `self.vpr_worker_lambda.metric_errors()`
  - Threshold: >3 errors over 5 minutes
  - Evaluation periods: 5

## Codex Implementation Guide

### Implementation: vpr_worker_handler.py

```python
"""
VPR Worker Handler (Async Processing)

Processes VPR generation jobs from SQS queue.
Triggered by SQS events, generates VPR, stores in S3, updates job status.
"""

import json
import os
from datetime import datetime
from typing import Any

import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.batch import (
    BatchProcessor,
    EventType,
    process_partial_response
)
from aws_lambda_powertools.utilities.typing import LambdaContext

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.dal.jobs_repository import JobsRepository
from careervp.logic.vpr_generator import VPRGenerator
from careervp.models.vpr import VPRRequest

logger = Logger()
tracer = Tracer()
processor = BatchProcessor(event_type=EventType.SQS)

s3 = boto3.client("s3")
jobs_repo = JobsRepository(table_name=os.environ["JOBS_TABLE_NAME"])
dal = DynamoDalHandler(table_name=os.environ["USERS_TABLE_NAME"])
vpr_gen = VPRGenerator()

BUCKET_NAME = os.environ["VPR_RESULTS_BUCKET_NAME"]


@tracer.capture_method
def process_vpr_job(record: dict) -> None:
    """
    Process single VPR generation job.

    Raises exception on failure to trigger SQS retry.
    """
    message = json.loads(record["body"])
    job_id = message["job_id"]
    input_data = message["input_data"]

    logger.info("Processing VPR job", extra={"job_id": job_id})

    try:
        # 1. UPDATE STATUS TO PROCESSING
        jobs_repo.update_job_status(
            job_id=job_id,
            status="PROCESSING",
            started_at=datetime.utcnow().isoformat()
        )

        # 2. PARSE REQUEST
        request = VPRRequest.model_validate(input_data)

        # 3. FETCH USER CV
        user_cv = dal.get_user_cv(request.application_id)
        if not user_cv:
            raise ValueError(f"User CV not found for application_id: {request.application_id}")

        # 4. GENERATE VPR
        logger.info(
            "Calling VPR generator",
            extra={
                "job_id": job_id,
                "user_id": request.user_id,
                "application_id": request.application_id
            }
        )

        vpr_result = vpr_gen.generate_vpr(
            request=request,
            user_cv=user_cv,
            dal=dal,
            gap_responses=request.gap_responses or [],
            previous_responses=[]  # TODO: Fetch from users table
        )

        if not vpr_result.success:
            raise ValueError(f"VPR generation failed: {vpr_result.error}")

        # 5. STORE RESULT IN S3
        result_key = f"results/{job_id}.json"
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=result_key,
            Body=json.dumps(vpr_result.data.model_dump()),
            ContentType="application/json",
            Metadata={
                "job_id": job_id,
                "user_id": request.user_id,
                "application_id": request.application_id
            }
        )

        logger.info(
            "Stored VPR result in S3",
            extra={"job_id": job_id, "result_key": result_key}
        )

        # 6. UPDATE STATUS TO COMPLETED
        jobs_repo.update_job(
            job_id=job_id,
            updates={
                "status": "COMPLETED",
                "completed_at": datetime.utcnow().isoformat(),
                "result_key": result_key,
                "token_usage": {
                    "input_tokens": vpr_result.data.token_usage.get("input_tokens", 0),
                    "output_tokens": vpr_result.data.token_usage.get("output_tokens", 0)
                }
            }
        )

        # 7. PERSIST VPR TO USERS TABLE (existing pattern)
        dal.store_vpr_artifact(request.application_id, vpr_result.data)

        logger.info("VPR job completed successfully", extra={"job_id": job_id})

    except Exception as e:
        logger.exception(
            "VPR job failed",
            extra={"job_id": job_id, "error": str(e)}
        )

        # Update status to FAILED
        jobs_repo.update_job(
            job_id=job_id,
            updates={
                "status": "FAILED",
                "error": str(e)
            }
        )

        # Re-raise to trigger SQS retry
        raise


@tracer.capture_lambda_handler
@logger.inject_lambda_context
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """
    Lambda handler for VPR worker.

    Processes SQS batch with partial failure support.
    """
    return process_partial_response(
        event=event,
        record_handler=process_vpr_job,
        processor=processor,
        context=context
    )
```

### CDK Lambda Configuration

```python
# infra/careervp/api_construct.py

from aws_cdk import Duration, aws_lambda, aws_lambda_event_sources, aws_iam

# CREATE VPR WORKER LAMBDA
self.vpr_worker_lambda = aws_lambda.Function(
    self, "VprWorkerLambda",
    function_name=f"careervp-vpr-worker-lambda-{env}",
    runtime=aws_lambda.Runtime.PYTHON_3_14,
    handler="careervp.handlers.vpr_worker_handler.lambda_handler",
    code=aws_lambda.Code.from_asset("../src/backend"),
    timeout=Duration.seconds(300),  # 5 minutes for Claude API call
    memory_size=1024,
    reserved_concurrent_executions=5,  # Limit concurrency for cost control
    environment={
        "JOBS_TABLE_NAME": self.jobs_table.table_name,
        "USERS_TABLE_NAME": self.users_table.table_name,
        "VPR_RESULTS_BUCKET_NAME": self.vpr_results_bucket.bucket_name,
        "ANTHROPIC_API_KEY_PARAM": f"/careervp/{env}/anthropic-api-key",
        "ENVIRONMENT": env,
        "LOG_LEVEL": "INFO",
        "POWERTOOLS_SERVICE_NAME": "vpr-worker"
    },
    tracing=aws_lambda.Tracing.ACTIVE
)

# ADD SQS EVENT SOURCE
self.vpr_worker_lambda.add_event_source(
    aws_lambda_event_sources.SqsEventSource(
        self.vpr_jobs_queue,
        batch_size=1,  # Process one VPR at a time
        max_batching_window=Duration.seconds(0),
        report_batch_item_failures=True  # Partial batch response
    )
)

# GRANT PERMISSIONS
self.jobs_table.grant_read_write_data(self.vpr_worker_lambda)
self.users_table.grant_read_data(self.vpr_worker_lambda)  # Read-only
self.vpr_results_bucket.grant_read_write(self.vpr_worker_lambda)
self.vpr_jobs_queue.grant_consume_messages(self.vpr_worker_lambda)

# SSM parameter access for Anthropic API key
self.vpr_worker_lambda.add_to_role_policy(
    aws_iam.PolicyStatement(
        actions=["ssm:GetParameter"],
        resources=[
            f"arn:aws:ssm:{Stack.of(self).region}:{Stack.of(self).account}:parameter/careervp/{env}/anthropic-api-key"
        ]
    )
)

# UPDATE WORKER ERRORS ALARM (from Task 7.1)
aws_cloudwatch.Alarm(
    self, "VprWorkerErrorsAlarm",
    alarm_name=f"careervp-vpr-worker-errors-alarm-{env}",
    metric=self.vpr_worker_lambda.metric_errors(),
    threshold=3,
    evaluation_periods=5,
    comparison_operator=aws_cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
)
```

## Verification Commands

### Local Validation

```bash
# 1. Code formatting
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run ruff format careervp/handlers/vpr_worker_handler.py

# 2. Linting
uv run ruff check careervp/handlers/vpr_worker_handler.py --fix

# 3. Type checking
uv run mypy careervp/handlers/vpr_worker_handler.py --strict

# 4. Unit tests (with mocked SQS event)
uv run pytest tests/unit/test_vpr_worker_handler.py -v
```

### Integration Testing

```bash
# 5. Submit test job (triggers worker)
curl -X POST https://api-dev.careervp.com/api/vpr \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-123",
    "application_id": "test-app-456",
    "job_posting": {...}
  }'

# Get job_id from response

# 6. Monitor worker Lambda logs
aws logs tail /aws/lambda/careervp-vpr-worker-lambda-dev --follow

# 7. Check job status (should transition PENDING → PROCESSING → COMPLETED)
aws dynamodb get-item \
  --table-name careervp-jobs-table-dev \
  --key '{"job_id": {"S": "JOB_ID"}}'

# 8. Verify S3 result
aws s3 ls s3://careervp-dev-vpr-results-*/results/

# 9. Download and inspect result
aws s3 cp s3://careervp-dev-vpr-results-*/results/JOB_ID.json result.json
cat result.json | jq '.'

# 10. Check SQS metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS \
  --metric-name NumberOfMessagesReceived \
  --dimensions Name=QueueName,Value=careervp-vpr-jobs-queue-dev \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

### Failure Testing

```bash
# 11. Test worker failure (invalid input)
# Manually send bad message to SQS
aws sqs send-message \
  --queue-url $(aws sqs get-queue-url --queue-name careervp-vpr-jobs-queue-dev --query 'QueueUrl' --output text) \
  --message-body '{"job_id": "invalid", "input_data": {"bad": "data"}}'

# Expected: Message retried 3 times, then moved to DLQ

# 12. Check DLQ
aws sqs receive-message \
  --queue-url $(aws sqs get-queue-url --queue-name careervp-vpr-jobs-dlq-dev --query 'QueueUrl' --output text)

# 13. Verify CloudWatch alarm triggered
aws cloudwatch describe-alarms --alarm-names careervp-vpr-worker-errors-alarm-dev
```

## Acceptance Criteria

- [ ] Worker Lambda created with 5-minute timeout
- [ ] Worker Lambda has reserved concurrency = 5
- [ ] SQS event source configured (batch_size=1)
- [ ] Worker processes VPR jobs successfully
- [ ] Job status transitions: PENDING → PROCESSING → COMPLETED
- [ ] VPR result stored in S3 with correct key format
- [ ] VPR result stored in users table (existing pattern)
- [ ] Failed jobs update status to FAILED and retry 3 times
- [ ] After 3 retries, messages move to DLQ
- [ ] CloudWatch alarm triggers on worker errors
- [ ] Code passes ruff, mypy, and unit tests
- [ ] Integration test: Submit job → Worker processes → Result in S3

## Dependencies

**Blocks:**
- Task 7.4 (Status Handler) - status handler needs worker to complete jobs
- Task 7.6 (Frontend Polling) - frontend needs completed jobs to fetch results

**Blocked By:**
- Task 7.1 (Infrastructure) - needs SQS queue, jobs table, S3 bucket
- Task 7.2 (Submit Handler) - needs jobs queued to SQS
- Task 7.5 (Jobs Repository) - needs DAL methods for job updates

## Estimated Effort

**Time:** 6-8 hours
**Complexity:** MEDIUM-HIGH (integrates existing VPR logic + SQS batch processing)

## Notes

- Worker Lambda has longest timeout (5 minutes) to accommodate Claude API
- Reserved concurrency = 5 prevents runaway costs and respects Claude API rate limits
- Batch size = 1 ensures each VPR is processed independently (30-60s each)
- Partial batch failures prevent entire batch retry on single job failure
- DLQ captures permanently failed jobs for manual investigation
