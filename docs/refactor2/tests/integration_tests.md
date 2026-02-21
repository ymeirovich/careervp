# REFACTOR2 Integration Test Designs

**Date:** 2026-02-20
**Purpose:** Integration test specifications validating cross-component interactions
**Location:** `src/backend/tests/integration/`
**Runner:** `uv run pytest tests/integration/ -v --tb=short`

---

## Phase 1 Integration Tests

### test_auth_flow_integration.py

**Description:** Validates complete authentication flow from registration through protected endpoint access.

**Prerequisites:** DynamoDB users table deployed, Cognito/JWT issuer configured

**Steps:**

| Step | Action | Expected | Assertion |
|------|--------|----------|-----------|
| 1 | POST /auth/register `{"email": "int-test@careervp.com", "password": "SecureP@ss123!", "name": "Integration Test"}` | 201 Created | `access_token` present, `token_type == "Bearer"` |
| 2 | POST /auth/login `{"email": "int-test@careervp.com", "password": "SecureP@ss123!"}` | 200 OK | `access_token` present, different from step 1 |
| 3 | GET /users/me with `Authorization: Bearer <token>` | 200 OK | `email == "int-test@careervp.com"`, `name == "Integration Test"` |
| 4 | GET /users/me without auth header | 401 Unauthorized | Error response |
| 5 | POST /auth/refresh with Bearer token | 200 OK | New `access_token` returned |
| 6 | GET /users/me with refreshed token | 200 OK | Same user profile |

**Cleanup:** Delete test user from DynamoDB

---

### test_user_crud_integration.py

**Description:** Validates user profile CRUD operations with database persistence.

**Prerequisites:** Auth flow working, test user registered

**Steps:**

| Step | Action | Expected | Assertion |
|------|--------|----------|-----------|
| 1 | POST /auth/register | 201 | User created |
| 2 | GET /users/me | 200 | Profile matches registration data |
| 3 | PUT /users/me `{"name": "Updated Name", "timezone": "US/Eastern"}` | 200 | `name == "Updated Name"`, `timezone == "US/Eastern"` |
| 4 | GET /users/me | 200 | Changes persisted in DB |
| 5 | PUT /users/me `{"name": ""}` | 400 | Validation error for empty name |

**Cleanup:** Delete test user

---

### test_workflow_pattern_integration.py

**Description:** Validates the chained workflow pattern: Job → VPR → CV Tailoring using IDs.

**Prerequisites:** Auth flow working, CV uploaded

**Steps:**

| Step | Action | Expected | Assertion |
|------|--------|----------|-----------|
| 1 | POST /users/me/cv (upload CV) | 201 | `cv_id` returned, `status == "parsed"` |
| 2 | POST /jobs (create job posting) | 201 | `job_id` returned |
| 3 | POST /gap-analysis/questions `{"cv_id": "<cv_id>", "job_id": "<job_id>"}` | 200 | 10 questions with tags |
| 4 | POST /gap-analysis/responses (submit answers) | 200 | `impact_statements` returned |
| 5 | POST /vpr/generate `{"cv_id": "<cv_id>", "job_id": "<job_id>", "gap_response_ids": [...]}` | 202 | `request_id` returned |
| 6 | Poll GET /vpr/{vprId} until COMPLETED | 200 | VPR result with `uvp`, `differentiators` |
| 7 | POST /cv-tailoring/generate `{"cv_id": "<cv_id>", "job_id": "<job_id>", "vpr_id": "<vpr_id>"}` | 202 | `request_id` returned |
| 8 | Poll GET /cv-tailoring/{id} until COMPLETED | 200 | `ats_score >= 8.0` |

**Cleanup:** Delete test artifacts

---

### test_dal_migration_integration.py

**Description:** Validates DynamoDalHandler methods work correctly against real DynamoDB (localstack or dev).

**Prerequisites:** DynamoDB table deployed

**Steps:**

| Step | Action | Expected | Assertion |
|------|--------|----------|-----------|
| 1 | `dal.save_gap_analysis(user_id, job_id, gap)` | `Result(success=True)` | Item exists in DDB with correct pk/sk |
| 2 | `dal.get_gap_analysis(user_id, job_id)` | `Result(success=True, data=gap)` | Data matches saved gap |
| 3 | `dal.save_tailored_cv(user_id, tailored_cv)` | `Result(success=True)` | Item persisted |
| 4 | `dal.save_cover_letter(user_id, cover_letter)` | `Result(success=True)` | Item persisted |
| 5 | `dal.save_interview_prep(user_id, interview_prep)` | `Result(success=True)` | Item persisted |
| 6 | Verify TTL on all items | TTL = now + 90 days | `ttl` attribute within 60s of expected |
| 7 | Verify old CVTable still works (backward compat) | Returns data | No regression |

**Cleanup:** Delete test items from DDB

---

## Phase 2 Integration Tests

### test_vpr_async_flow_integration.py

**Description:** Validates complete async VPR flow: Submit → SQS → Worker → S3 → Status poll.

**Prerequisites:** SQS queue deployed, jobs table deployed, S3 bucket deployed, worker Lambda deployed

**Steps:**

| Step | Action | Expected | Assertion |
|------|--------|----------|-----------|
| 1 | POST /vpr/generate with valid payload | 202 | `request_id` returned, `status == "processing"` |
| 2 | GET /vpr/{request_id} immediately | 200 | `status == "pending"` or `"processing"` |
| 3 | Wait for SQS message delivery (max 10s) | Message in queue | SQS message count > 0 |
| 4 | Worker Lambda invoked by SQS | Processing starts | Job status = PROCESSING in DDB |
| 5 | Wait for completion (max 120s, poll every 5s) | Job completes | `status == "completed"` |
| 6 | GET /vpr/{request_id} | 200 | `result_url` is valid presigned S3 URL |
| 7 | Fetch result from presigned URL | 200 | Valid VPR JSON with `uvp`, `differentiators` |
| 8 | Verify token_usage recorded | Metadata present | `input_tokens > 0`, `output_tokens > 0` |

**Timeout:** 180 seconds max

**Cleanup:** Delete job record, S3 object

---

### test_vpr_failure_recovery_integration.py

**Description:** Validates failure handling: Worker failure → DLQ → Job marked FAILED.

**Prerequisites:** Same as async flow, plus DLQ configured

**Steps:**

| Step | Action | Expected | Assertion |
|------|--------|----------|-----------|
| 1 | POST /vpr/generate with payload that triggers LLM error | 202 | Job submitted |
| 2 | Worker fails processing | SQS retry (max 3) | Message retry count increments |
| 3 | After max retries, message goes to DLQ | DLQ receives message | DLQ message count > 0 |
| 4 | GET /vpr/{request_id} | 200 | `status == "failed"`, `error` message present |

**Timeout:** 300 seconds (accounts for retry delays)

**Cleanup:** Purge DLQ, delete job record

---

### test_cv_tailoring_async_flow_integration.py

**Description:** Validates CV Tailoring async flow (if enabled).

**Prerequisites:** VPR completed (depends on test_vpr_async_flow), CV uploaded

**Steps:**

| Step | Action | Expected | Assertion |
|------|--------|----------|-----------|
| 1 | POST /cv-tailoring/generate with cv_id, job_id, vpr_id | 202 | `request_id` returned |
| 2 | Poll GET /cv-tailoring/{id} until COMPLETED (max 120s) | 200 | `status == "completed"` |
| 3 | Verify result | Tailored CV present | `ats_score >= 8.0`, `keyword_matches` populated |
| 4 | Verify FVS validation | Quality gates pass | `fvs_validation.is_valid == true` |

**Cleanup:** Delete tailoring artifacts

---

## Cross-Phase Integration Tests

### test_full_pipeline_integration.py

**Description:** Validates the complete job application pipeline end-to-end with real data flow.

**Prerequisites:** All infrastructure deployed

**Steps:**

| Step | Action | Expected | Assertion |
|------|--------|----------|-----------|
| 1 | Register + Login | Auth tokens | Valid JWT |
| 2 | Upload CV | cv_id | Parsed CV in DB |
| 3 | Create Job | job_id | Job in DB |
| 4 | Company Research | research_id | Company data retrieved |
| 5 | Gap Analysis Questions | 10 questions | Tags: [CV IMPACT], [INTERVIEW ONLY] |
| 6 | Gap Analysis Responses | impact_statements | CV_IMPACT and INTERVIEW_PREP types |
| 7 | VPR Generate (async) | request_id | Poll until COMPLETED |
| 8 | CV Tailoring (async) | request_id | ATS >= 8.0 |
| 9 | Cover Letter Generate | request_id | 3 paragraphs, word counts valid |
| 10 | Interview Prep Generate | request_id | STAR format, 10+ questions |
| 11 | Verify cross-doc consistency | FVS check | No contradictions between VPR/CV/CL |

**Timeout:** 600 seconds (10 minutes for full pipeline)

**Cleanup:** Delete all test artifacts

---

## Test Execution Commands

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Phase 1 integration
uv run pytest tests/integration/test_auth_flow_integration.py -v --tb=short
uv run pytest tests/integration/test_user_crud_integration.py -v --tb=short
uv run pytest tests/integration/test_workflow_pattern_integration.py -v --tb=short
uv run pytest tests/integration/test_dal_migration_integration.py -v --tb=short

# Phase 2 integration
uv run pytest tests/integration/test_vpr_async_flow_integration.py -v --tb=short -x
uv run pytest tests/integration/test_vpr_failure_recovery_integration.py -v --tb=short -x
uv run pytest tests/integration/test_cv_tailoring_async_flow_integration.py -v --tb=short -x

# Full pipeline
uv run pytest tests/integration/test_full_pipeline_integration.py -v --tb=short -x --timeout=600

# All integration tests
uv run pytest tests/integration/ -v --tb=short -x
```

---

## Coverage Summary

| Phase | Test Files | Test Count | Components Covered |
|-------|-----------|------------|-------------------|
| Phase 1 | 4 | 26 steps | Auth, Users, Jobs, DAL, Workflow |
| Phase 2 | 3 | 20 steps | VPR async, failure recovery, CV tailoring async |
| Cross-Phase | 1 | 11 steps | Full pipeline end-to-end |
| **Total** | **8 files** | **57 steps** | **All REFACTOR2 components** |
