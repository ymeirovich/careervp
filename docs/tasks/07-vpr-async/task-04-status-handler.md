# Task 7.4: VPR Status Handler (Status Polling)

**Status:** Not Started
**Spec Reference:** [[docs/specs/07-vpr-async-architecture.md]]
**Priority:** P0 (BLOCKING - Production VPR generation fails 100%)

## Overview

Create the VPR Status Lambda that handles `GET /api/vpr/status/{job_id}` requests. This read-only endpoint returns job status and generates presigned S3 URLs for completed VPR results.

## Prerequisites

- [ ] Task 7.1 complete (infrastructure deployed)
- [ ] Task 7.3 complete (worker Lambda creating completed jobs)
- [ ] `careervp-jobs-table-dev` exists
- [ ] `careervp-dev-vpr-results-*` S3 bucket exists

## Todo

### 1. Create Status Handler File

- [ ] Create `src/backend/careervp/handlers/vpr_status_handler.py`
- [ ] Import jobs repository from `dal/jobs_repository.py`
- [ ] Import boto3 S3 client for presigned URLs

### 2. Implement Status Check Logic

- [ ] Extract `job_id` from path parameters
- [ ] Fetch job record from DynamoDB using `jobs_repository.get_job(job_id)`
- [ ] Handle job not found (404 response)
- [ ] Return status-specific responses:
  - **PENDING**: 202 Accepted with created_at timestamp
  - **PROCESSING**: 202 Accepted with started_at timestamp
  - **COMPLETED**: 200 OK with presigned S3 URL (1-hour expiry)
  - **FAILED**: 200 OK with error message

### 3. Generate Presigned S3 URLs

- [ ] For COMPLETED jobs only:
  - Extract `result_key` from job record
  - Generate presigned S3 URL with `generate_presigned_url()`
  - URL expiration: 3600 seconds (1 hour)
  - Include `result_url` in response
- [ ] Handle S3 object not found (410 Gone - result expired)

### 4. Security: Ownership Validation

- [ ] Extract `user_id` from request context (API Gateway authorizer)
- [ ] Compare request `user_id` with job `user_id`
- [ ] Return 403 Forbidden if mismatch (prevent job_id enumeration)
- [ ] Optional: Add rate limiting per user_id

### 5. Create Status Lambda (CDK)

**File:** `infra/careervp/api_construct.py`

- [ ] Create status Lambda function:
  - Function name: `careervp-vpr-status-lambda-dev`
  - Handler: `careervp.handlers.vpr_status_handler.lambda_handler`
  - Timeout: 10 seconds (fast read operation)
  - Memory: 256 MB
- [ ] Add environment variables:
  - `JOBS_TABLE_NAME`
  - `VPR_RESULTS_BUCKET_NAME`
- [ ] Add API Gateway route:
  - Path: `/api/vpr/status/{job_id}`
  - Method: GET
  - Integration: Lambda proxy
- [ ] Grant permissions:
  - `dynamodb:GetItem` on jobs table (read-only)
  - `s3:GetObject` on results bucket (for presigned URL generation)

## Codex Implementation Guide

### Implementation: vpr_status_handler.py

```python
"""
VPR Status Handler (Status Polling)

Returns job status and presigned S3 URL for completed VPR results.
"""

import json
import os
from typing import Any

import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError

from careervp.dal.jobs_repository import JobsRepository

logger = Logger()
tracer = Tracer()

s3 = boto3.client("s3")
jobs_repo = JobsRepository(table_name=os.environ["JOBS_TABLE_NAME"])

BUCKET_NAME = os.environ["VPR_RESULTS_BUCKET_NAME"]
PRESIGNED_URL_EXPIRY = 3600  # 1 hour


@tracer.capture_lambda_handler
@logger.inject_lambda_context
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """
    Get VPR job status.

    Returns:
        - 202 Accepted (PENDING/PROCESSING)
        - 200 OK (COMPLETED with result_url, or FAILED with error)
        - 404 Not Found (job doesn't exist or expired)
        - 410 Gone (COMPLETED but S3 result expired)
        - 500 Internal Server Error (system error)
    """
    try:
        # 1. EXTRACT JOB ID
        job_id = event["pathParameters"]["job_id"]

        logger.info("Checking VPR job status", extra={"job_id": job_id})

        # 2. FETCH JOB RECORD
        job = jobs_repo.get_job(job_id)

        if not job:
            logger.warning("Job not found", extra={"job_id": job_id})
            return {
                "statusCode": 404,
                "body": json.dumps({
                    "error": "Job not found (may have expired after 10 minutes)"
                })
            }

        # 3. SECURITY: OWNERSHIP VALIDATION (optional - add if API has auth)
        # request_user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
        # if request_user_id != job["user_id"]:
        #     logger.warning("Unauthorized job access", extra={"job_id": job_id})
        #     return {"statusCode": 403, "body": json.dumps({"error": "Forbidden"})}

        # 4. BUILD BASE RESPONSE
        response_body = {
            "job_id": job["job_id"],
            "status": job["status"],
            "created_at": job.get("created_at")
        }

        # 5. HANDLE STATUS-SPECIFIC RESPONSES
        if job["status"] in ["PENDING", "PROCESSING"]:
            # Still in progress
            if job.get("started_at"):
                response_body["started_at"] = job["started_at"]

            return {
                "statusCode": 202,  # Accepted (still processing)
                "body": json.dumps(response_body)
            }

        elif job["status"] == "COMPLETED":
            # Generate presigned URL for result
            result_key = job.get("result_key")
            if not result_key:
                logger.error("Completed job missing result_key", extra={"job_id": job_id})
                return {
                    "statusCode": 500,
                    "body": json.dumps({"error": "Result key missing"})
                }

            try:
                presigned_url = s3.generate_presigned_url(
                    "get_object",
                    Params={
                        "Bucket": BUCKET_NAME,
                        "Key": result_key
                    },
                    ExpiresIn=PRESIGNED_URL_EXPIRY
                )

                response_body.update({
                    "completed_at": job.get("completed_at"),
                    "result_url": presigned_url,
                    "token_usage": job.get("token_usage")
                })

                return {
                    "statusCode": 200,
                    "body": json.dumps(response_body)
                }

            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    logger.warning(
                        "S3 result expired or deleted",
                        extra={"job_id": job_id, "result_key": result_key}
                    )
                    return {
                        "statusCode": 410,  # Gone
                        "body": json.dumps({
                            "error": "Result expired or deleted",
                            "message": "Please regenerate the VPR"
                        })
                    }
                raise

        elif job["status"] == "FAILED":
            # Job failed
            response_body["error"] = job.get("error", "Unknown error")

            return {
                "statusCode": 200,  # 200 OK (job completed, but failed)
                "body": json.dumps(response_body)
            }

        else:
            # Unknown status
            logger.error("Unknown job status", extra={"job_id": job_id, "status": job["status"]})
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Unknown job status"})
            }

    except Exception as e:
        logger.exception("Failed to get job status", extra={"error": str(e)})
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal server error",
                "message": "Failed to retrieve job status"
            })
        }
```

### CDK Lambda Configuration

```python
# infra/careervp/api_construct.py

from aws_cdk import Duration, aws_lambda, aws_apigatewayv2, aws_apigatewayv2_integrations

# CREATE VPR STATUS LAMBDA
self.vpr_status_lambda = aws_lambda.Function(
    self, "VprStatusLambda",
    function_name=f"careervp-vpr-status-lambda-{env}",
    runtime=aws_lambda.Runtime.PYTHON_3_14,
    handler="careervp.handlers.vpr_status_handler.lambda_handler",
    code=aws_lambda.Code.from_asset("../src/backend"),
    timeout=Duration.seconds(10),  # Fast read operation
    memory_size=256,
    environment={
        "JOBS_TABLE_NAME": self.jobs_table.table_name,
        "VPR_RESULTS_BUCKET_NAME": self.vpr_results_bucket.bucket_name,
        "ENVIRONMENT": env,
        "LOG_LEVEL": "INFO",
        "POWERTOOLS_SERVICE_NAME": "vpr-status"
    },
    tracing=aws_lambda.Tracing.ACTIVE
)

# GRANT PERMISSIONS (read-only)
self.jobs_table.grant_read_data(self.vpr_status_lambda)
self.vpr_results_bucket.grant_read(self.vpr_status_lambda)  # For presigned URL generation

# ADD API GATEWAY ROUTE
self.api.add_routes(
    path="/api/vpr/status/{job_id}",
    methods=[aws_apigatewayv2.HttpMethod.GET],
    integration=aws_apigatewayv2_integrations.HttpLambdaIntegration(
        "VprStatusIntegration",
        self.vpr_status_lambda
    )
)
```

## Verification Commands

### Local Validation

```bash
# 1. Code formatting
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run ruff format careervp/handlers/vpr_status_handler.py

# 2. Linting
uv run ruff check careervp/handlers/vpr_status_handler.py --fix

# 3. Type checking
uv run mypy careervp/handlers/vpr_status_handler.py --strict

# 4. Unit tests
uv run pytest tests/unit/test_vpr_status_handler.py -v
```

### Integration Testing

```bash
# 5. Submit test job
JOB_ID=$(curl -s -X POST https://api-dev.careervp.com/api/vpr \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-123",
    "application_id": "test-app-456",
    "job_posting": {...}
  }' | jq -r '.job_id')

echo "Job ID: $JOB_ID"

# 6. Check status (PENDING)
curl -s https://api-dev.careervp.com/api/vpr/status/$JOB_ID | jq '.'
# Expected: 202 Accepted, status: PENDING

# 7. Wait a few seconds, check status (PROCESSING)
sleep 5
curl -s https://api-dev.careervp.com/api/vpr/status/$JOB_ID | jq '.'
# Expected: 202 Accepted, status: PROCESSING

# 8. Wait for completion (30-60 seconds)
sleep 60
curl -s https://api-dev.careervp.com/api/vpr/status/$JOB_ID | jq '.'
# Expected: 200 OK, status: COMPLETED, result_url present

# 9. Fetch VPR result from presigned URL
RESULT_URL=$(curl -s https://api-dev.careervp.com/api/vpr/status/$JOB_ID | jq -r '.result_url')
curl -s "$RESULT_URL" | jq '.'

# 10. Test 404 (invalid job_id)
curl -s https://api-dev.careervp.com/api/vpr/status/invalid-job-id | jq '.'
# Expected: 404 Not Found

# 11. Test job not found (after TTL expiry)
# Wait 10 minutes, then check expired job
# Expected: 404 Not Found
```

### Status Response Examples

```json
# PENDING (202 Accepted)
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PENDING",
  "created_at": "2026-02-03T13:05:32Z"
}

# PROCESSING (202 Accepted)
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PROCESSING",
  "created_at": "2026-02-03T13:05:32Z",
  "started_at": "2026-02-03T13:05:35Z"
}

# COMPLETED (200 OK)
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "created_at": "2026-02-03T13:05:32Z",
  "completed_at": "2026-02-03T13:06:12Z",
  "result_url": "https://s3.amazonaws.com/careervp-dev-vpr-results.../results/550e8400.json?...",
  "token_usage": {
    "input_tokens": 7500,
    "output_tokens": 2200
  }
}

# FAILED (200 OK)
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "FAILED",
  "created_at": "2026-02-03T13:05:32Z",
  "error": "Claude API rate limit exceeded"
}

# NOT FOUND (404)
{
  "error": "Job not found (may have expired after 10 minutes)"
}

# RESULT EXPIRED (410 Gone)
{
  "error": "Result expired or deleted",
  "message": "Please regenerate the VPR"
}
```

## Acceptance Criteria

- [ ] Status Lambda created with 10-second timeout
- [ ] Status Lambda has read-only permissions
- [ ] API route `GET /api/vpr/status/{job_id}` created
- [ ] Returns 202 Accepted for PENDING/PROCESSING jobs
- [ ] Returns 200 OK with presigned URL for COMPLETED jobs
- [ ] Returns 200 OK with error for FAILED jobs
- [ ] Returns 404 Not Found for non-existent jobs
- [ ] Returns 410 Gone if S3 result expired
- [ ] Presigned S3 URL expires in 1 hour
- [ ] Code passes ruff, mypy, and unit tests
- [ ] Integration test: Submit → Poll → Get result URL → Fetch VPR

## Dependencies

**Blocks:**
- Task 7.6 (Frontend Polling) - frontend needs status endpoint

**Blocked By:**
- Task 7.1 (Infrastructure) - needs jobs table + S3 bucket
- Task 7.3 (Worker Handler) - needs completed jobs to return
- Task 7.5 (Jobs Repository) - needs DAL methods for job reads

## Estimated Effort

**Time:** 3-4 hours
**Complexity:** LOW-MEDIUM (read-only operations + presigned URL generation)

## Notes

- Status Lambda is read-only (no writes to DynamoDB or S3)
- Presigned S3 URLs are generated on-demand (not stored)
- 1-hour URL expiry balances security and usability
- Optional: Add ownership validation when API has authentication
- Optional: Add rate limiting to prevent job_id enumeration attacks
