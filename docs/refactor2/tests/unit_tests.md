# REFACTOR2 Unit Test Designs

**Date:** 2026-02-20
**Purpose:** Unit test specifications for REFACTOR2 Phase 1 (Critical Fixes) and Phase 2 (Async Processing)
**Location:** `src/backend/tests/unit/`
**Runner:** `uv run pytest tests/unit/ -v --tb=short`

> Note: Phase 3 (JSA P0) and Phase 4 (JSA P1) unit tests already exist from execution_runbook_2.

---

## Phase 1: Critical Fixes

### test_auth_utils.py

Tests for standardized authentication extraction (`src/backend/careervp/handlers/auth_utils.py`).

| Test Name | Description | Input | Expected Outcome | Validates |
|-----------|-------------|-------|------------------|-----------|
| `test_extract_user_id_from_jwt_authorizer` | Extract user_id from HTTP API v2 JWT authorizer context | `event.requestContext.authorizer.jwt.claims.sub = "user-123"` | Returns `"user-123"` | Auth spec: JWT extraction |
| `test_extract_user_id_from_lambda_authorizer` | Extract user_id from Lambda authorizer principalId | `event.requestContext.authorizer.principalId = "user-456"` | Returns `"user-456"` | Auth spec: Lambda authorizer |
| `test_extract_user_id_from_x_user_id_header` | Fallback to X-User-Id header when AUTHORIZER_DISABLED=true | `headers.X-User-Id = "user-789"`, env `AUTHORIZER_DISABLED=true` | Returns `"user-789"` | Auth spec: dev fallback |
| `test_extract_user_id_returns_none_without_authorizer` | Returns None when no authorizer context and fallback disabled | `event.requestContext.authorizer = None`, env unset | Returns `None` | Auth spec: rejection path |
| `test_extract_user_id_handles_malformed_event` | Gracefully handles missing keys without raising | `event = {}` | Returns `None`, no exception | Auth spec: error handling |
| `test_extract_user_id_prefers_jwt_over_header` | JWT authorizer takes priority over X-User-Id header | Both JWT claims and X-User-Id present | Returns JWT claim value | Auth spec: priority order |

### test_api_models_workflow.py

Tests for updated Pydantic models supporting workflow patterns (`src/backend/careervp/models/api_models.py`).

| Test Name | Description | Input | Expected Outcome | Validates |
|-----------|-------------|-------|------------------|-----------|
| `test_cv_tailoring_request_workflow_pattern` | Accepts cv_id + job_id + vpr_id | `{"cv_id": "cv-1", "job_id": "job-1", "vpr_id": "vpr-1"}` | Valid model, no errors | API contract: workflow flow |
| `test_cv_tailoring_request_legacy_pattern` | Accepts cv_id + job_description | `{"cv_id": "cv-1", "job_description": "Senior Engineer..."}` | Valid model, no errors | API contract: backward compat |
| `test_cv_tailoring_request_rejects_empty` | Rejects request with neither pattern | `{"cv_id": "cv-1"}` | `ValidationError` raised | API contract: input validation |
| `test_cv_tailoring_request_rejects_extra_fields` | Still rejects truly unknown fields | `{"cv_id": "cv-1", "job_id": "j1", "vpr_id": "v1", "unknown": "x"}` | `ValidationError` (extra_forbidden) | API contract: schema safety |
| `test_cover_letter_request_validates_required` | Validates all required fields present | `{"cv_id": "c", "job_id": "j", "vpr_id": "v", "gap_response_ids": ["g1"], "company_research_id": "cr1"}` | Valid model | API contract: CL schema |
| `test_cover_letter_request_rejects_missing_fields` | Rejects when required fields missing | `{"cv_id": "c"}` | `ValidationError` | API contract: CL validation |
| `test_interview_prep_request_validates_required` | Validates vpr_id + gap_response_ids required | `{"vpr_id": "v1", "gap_response_ids": ["g1"]}` | Valid model | API contract: IP schema |
| `test_interview_prep_request_default_question_count` | Default question_count is 5 | `{"vpr_id": "v1", "gap_response_ids": ["g1"]}` | `model.question_count == 5` | API contract: defaults |

### test_user_handler.py

Tests for new user management endpoints (`src/backend/careervp/handlers/user_handler.py`).

| Test Name | Description | Input | Expected Outcome | Validates |
|-----------|-------------|-------|------------------|-----------|
| `test_get_user_returns_profile` | GET /users/me returns user profile | Valid JWT with user_id | 200, `{"id", "email", "name", "created_at"}` | API contract: GET /users/me |
| `test_get_user_returns_401_without_auth` | Rejects unauthenticated request | No Authorization header | 401 | Auth spec: protected route |
| `test_get_user_returns_404_for_missing_user` | Returns 404 when user not in DB | Valid JWT, user_id not in DynamoDB | 404 | API contract: error handling |
| `test_update_user_modifies_name` | PUT /users/me updates name | `{"name": "New Name"}` | 200, updated profile returned | API contract: PUT /users/me |
| `test_update_user_modifies_timezone` | PUT /users/me updates timezone | `{"timezone": "America/New_York"}` | 200, timezone updated | API contract: PUT /users/me |
| `test_update_user_returns_400_for_invalid_input` | Rejects invalid input | `{"name": ""}` (empty string) | 400, validation error | API contract: validation |

### test_job_handler_list.py

Tests for missing job list endpoint (`src/backend/careervp/handlers/job_handler.py`).

| Test Name | Description | Input | Expected Outcome | Validates |
|-----------|-------------|-------|------------------|-----------|
| `test_list_jobs_returns_user_jobs` | GET /jobs returns user's jobs | Valid JWT, 3 jobs in DB | 200, `{"jobs": [...]}` with 3 items | API contract: GET /jobs |
| `test_list_jobs_empty_for_new_user` | Returns empty array for new user | Valid JWT, no jobs | 200, `{"jobs": []}` | API contract: empty state |
| `test_list_jobs_supports_pagination` | Respects limit parameter | `?limit=2`, 5 jobs in DB | 200, 2 jobs returned | API contract: pagination |
| `test_list_jobs_returns_401_without_auth` | Rejects unauthenticated | No auth header | 401 | Auth spec: protected route |
| `test_get_job_returns_job_details` | GET /jobs/{jobId} returns full job | Valid job_id | 200, full JobResponse | API contract: GET /jobs/{id} |
| `test_get_job_returns_404_for_missing` | Returns 404 for unknown job | Invalid job_id | 404 | API contract: error handling |

### test_dal_migration.py

Tests for DynamoDalHandler new methods (`src/backend/careervp/dal/dynamo_dal_handler.py`).

| Test Name | Description | Input | Expected Outcome | Validates |
|-----------|-------------|-------|------------------|-----------|
| `test_save_gap_analysis_stores_correctly` | Saves gap analysis with proper keys | GapAnalysis model, user_id, job_id | `Result(success=True)`, item in DDB | DAL spec: save method |
| `test_get_gap_analysis_retrieves_latest` | Gets most recent gap analysis | user_id, job_id with 2 versions | Returns latest version | DAL spec: get method |
| `test_get_gap_analysis_returns_none_for_missing` | Returns None when not found | user_id with no gap data | `Result(success=True, data=None)` | DAL spec: empty result |
| `test_save_tailored_cv_stores_correctly` | Saves tailored CV artifact | TailoredCV model | `Result(success=True)` | DAL spec: save method |
| `test_save_cover_letter_stores_correctly` | Saves cover letter artifact | CoverLetter model | `Result(success=True)` | DAL spec: save method |
| `test_save_interview_prep_stores_correctly` | Saves interview prep artifact | InterviewPrep model | `Result(success=True)` | DAL spec: save method |
| `test_dal_handles_dynamodb_error` | Returns error Result on DDB failure | DDB throws ClientError | `Result(success=False, code=DYNAMODB_ERROR)` | DAL spec: error handling |
| `test_dal_sets_ttl_correctly` | TTL set to 90 days from now | Any save operation | `ttl` field = now + 7776000 | DAL spec: TTL |
| `test_dal_uses_tracer_decorator` | Methods have @tracer.capture_method | Inspect method decorators | Tracer applied | DAL spec: observability |

---

## Phase 2: Async Processing

### test_vpr_submit_handler.py

Tests for VPR async submission (`src/backend/careervp/handlers/vpr_submit_handler.py`).

| Test Name | Description | Input | Expected Outcome | Validates |
|-----------|-------------|-------|------------------|-----------|
| `test_submit_returns_202_with_job_id` | Returns 202 Accepted with job_id | Valid VPRGenerateRequest | 202, `{"request_id": "<uuid>", "status": "processing"}` | Async spec: submit contract |
| `test_submit_validates_required_fields` | Rejects missing cv_id or job_id | `{"cv_id": "c1"}` (missing job_id) | 400, validation error | API contract: validation |
| `test_submit_creates_pending_job_in_dynamodb` | Creates PENDING job record | Valid request | Job record with status=PENDING in jobs table | Async spec: job tracking |
| `test_submit_sends_message_to_sqs` | Sends SQS message with job details | Valid request | SQS message with job_id, cv_id, job_id | Async spec: queue submission |
| `test_submit_idempotent_for_duplicate` | Same request returns same job_id | Same payload submitted twice | Same job_id returned | Async spec: idempotency |
| `test_submit_returns_401_without_auth` | Rejects unauthenticated request | No auth header | 401 | Auth spec: protected |
| `test_submit_returns_422_without_prerequisites` | Rejects when gap analysis incomplete | cv_id without gap responses | 422, prerequisites error | API contract: prerequisite |

### test_vpr_worker_handler.py

Tests for VPR SQS worker (`src/backend/careervp/handlers/vpr_worker_handler.py`).

| Test Name | Description | Input | Expected Outcome | Validates |
|-----------|-------------|-------|------------------|-----------|
| `test_worker_processes_sqs_message` | Processes valid SQS event | SQS event with job_id payload | Job processed, no errors | Async spec: worker |
| `test_worker_updates_status_to_processing` | Sets PROCESSING on start | SQS message received | Job status = PROCESSING in DDB | Async spec: state machine |
| `test_worker_calls_vpr_generator` | Invokes 6-stage VPR pipeline | Valid job with cv/job data | VPR generator called with correct args | Async spec: pipeline |
| `test_worker_stores_result_in_s3` | Saves VPR JSON to S3 | Successful generation | S3 object at `results/{job_id}.json` | Async spec: storage |
| `test_worker_updates_status_to_completed` | Sets COMPLETED with result_url | Successful generation | Job status = COMPLETED, result_url set | Async spec: state machine |
| `test_worker_handles_llm_failure` | Marks FAILED on LLM error | Claude API returns error | Job status = FAILED, error_message set | Async spec: error handling |
| `test_worker_handles_timeout` | Graceful handling of Lambda timeout | Processing exceeds 300s | Job status = FAILED, timeout error | Async spec: timeout |
| `test_worker_records_token_usage` | Tracks input/output tokens | Successful generation | token_usage in job record | Async spec: cost tracking |

### test_vpr_status_handler.py

Tests for VPR status polling (`src/backend/careervp/handlers/vpr_status_handler.py`).

| Test Name | Description | Input | Expected Outcome | Validates |
|-----------|-------------|-------|------------------|-----------|
| `test_status_returns_pending` | Returns PENDING for new job | job_id with PENDING status | 200, `{"status": "pending"}` | Async spec: polling |
| `test_status_returns_processing` | Returns PROCESSING for active job | job_id with PROCESSING status | 200, `{"status": "processing", "started_at": ...}` | Async spec: polling |
| `test_status_returns_completed_with_url` | Returns COMPLETED with presigned URL | job_id with COMPLETED status | 200, `{"status": "completed", "result_url": "https://..."}` | Async spec: result delivery |
| `test_status_returns_failed_with_error` | Returns FAILED with error details | job_id with FAILED status | 200, `{"status": "failed", "error": "..."}` | Async spec: error reporting |
| `test_status_returns_404_for_unknown` | Returns 404 for non-existent job | Invalid job_id | 404 | API contract: not found |
| `test_status_returns_401_without_auth` | Rejects unauthenticated | No auth header | 401 | Auth spec: protected |
| `test_presigned_url_expires_in_1_hour` | S3 presigned URL has 1h expiry | COMPLETED job | URL contains expires parameter | Async spec: security |

### test_health_handler.py

Tests for health check endpoint (`src/backend/careervp/handlers/health_handler.py`).

| Test Name | Description | Input | Expected Outcome | Validates |
|-----------|-------------|-------|------------------|-----------|
| `test_health_returns_200` | Returns healthy status | GET /health | 200, `{"status": "healthy"}` | API contract: health |
| `test_health_includes_service_status` | Includes DynamoDB/Lambda status | GET /health | `{"services": {"dynamodb": "ok", "lambda": "ok"}}` | API contract: services |
| `test_health_no_auth_required` | Accessible without authentication | No auth header | 200 | Auth spec: unprotected |
| `test_health_returns_degraded_when_db_down` | Returns degraded when DDB unreachable | DDB connection fails | 200, `{"status": "degraded"}` | API contract: degraded |

---

## Test Execution Commands

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Phase 1 unit tests
uv run pytest tests/unit/test_auth_utils.py -v --tb=short
uv run pytest tests/unit/test_api_models_workflow.py -v --tb=short
uv run pytest tests/unit/test_user_handler.py -v --tb=short
uv run pytest tests/unit/test_job_handler_list.py -v --tb=short
uv run pytest tests/unit/test_dal_migration.py -v --tb=short

# Phase 2 unit tests
uv run pytest tests/unit/test_vpr_submit_handler.py -v --tb=short
uv run pytest tests/unit/test_vpr_worker_handler.py -v --tb=short
uv run pytest tests/unit/test_vpr_status_handler.py -v --tb=short
uv run pytest tests/unit/test_health_handler.py -v --tb=short

# All REFACTOR2 unit tests
uv run pytest tests/unit/test_auth_utils.py tests/unit/test_api_models_workflow.py tests/unit/test_user_handler.py tests/unit/test_job_handler_list.py tests/unit/test_dal_migration.py tests/unit/test_vpr_submit_handler.py tests/unit/test_vpr_worker_handler.py tests/unit/test_vpr_status_handler.py tests/unit/test_health_handler.py -v --tb=short

# Lint all new files
uv run ruff check careervp/handlers/auth_utils.py careervp/handlers/user_handler.py careervp/handlers/vpr_submit_handler.py careervp/handlers/vpr_worker_handler.py careervp/handlers/vpr_status_handler.py careervp/handlers/health_handler.py

# Type check
uv run mypy careervp/handlers/auth_utils.py careervp/handlers/user_handler.py --strict
```

---

## Coverage Targets

| Phase | Test Files | Test Count | Coverage Target |
|-------|-----------|------------|-----------------|
| Phase 1: Auth | test_auth_utils.py | 6 | 100% of auth_utils.py |
| Phase 1: Models | test_api_models_workflow.py | 8 | 100% of model validators |
| Phase 1: Users | test_user_handler.py | 6 | 100% of user_handler.py |
| Phase 1: Jobs | test_job_handler_list.py | 6 | 100% of list/get paths |
| Phase 1: DAL | test_dal_migration.py | 9 | 100% of new DAL methods |
| Phase 2: Submit | test_vpr_submit_handler.py | 7 | 100% of submit paths |
| Phase 2: Worker | test_vpr_worker_handler.py | 8 | 100% of worker paths |
| Phase 2: Status | test_vpr_status_handler.py | 7 | 100% of status paths |
| Phase 2: Health | test_health_handler.py | 4 | 100% of health paths |
| **Total** | **9 files** | **61 tests** | **100% of new code** |
