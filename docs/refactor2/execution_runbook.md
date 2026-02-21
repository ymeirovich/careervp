# CareerVP Execution Runbook 3.0 - REFACTOR2

**Document Version:** 3.0
**Date:** 2026-02-20
**Purpose:** Complete implementation of REFACTOR2 Phase 1 (Critical Fixes) and Phase 2 (Async Processing)
**Prerequisite:** execution_runbook_2.md completed (JSA features, API route mapping, quality gaps)

---

## Implementation Order

1. **Critical Fixes FIRST** (Phase 1) - Auth, missing endpoints, validation, DAL migration
2. **Async Processing SECOND** (Phase 2) - SQS, worker Lambdas, status polling
3. **CDK Infrastructure THIRD** (Phase 3) - New tables, buckets, queues, authorizer
4. **Live Tests FOURTH** (Phase 4) - E2E validation against deployed API

---

## Current Status

| Phase | Status | Scope |
|-------|--------|-------|
| Phase 1 | ⏳ PENDING | Auth fixes (8x401), missing endpoints (5x404), validation (3x400), DAL migration |
| Phase 2 | ⏳ PENDING | VPR async (SQS+worker), CV Tailoring async, status polling |
| Phase 3 | ⏳ PENDING | CDK: JWT authorizer, SQS queue+DLQ, jobs table, S3 bucket, worker Lambda |
| Phase 4 | ⏳ PENDING | Live tests: 27-endpoint contract gate, async flow, quality gates |

---

## Specs

| Type | File | Purpose |
|------|------|---------|
| API Contract | `docs/refactor2/specs/api_contract_spec.yaml` | All 27 endpoints with status and required fixes |
| Async Processing | `docs/refactor2/specs/async_processing_spec.yaml` | SQS + polling pattern, worker Lambda, job states |
| DAL Migration | `docs/refactor2/specs/dal_migration_spec.yaml` | CVTable → DynamoDalHandler migration plan |
| JSA Alignment | `docs/refactor2/specs/jsa_alignment_spec.yaml` | JSA requirements (all marked complete) |
| Auth | `docs/refactor2/specs/auth_spec.yaml` | JWT authorizer deployment, auth extraction |
| Prompt Optimization | `docs/refactor/specs/prompt_optimization_spec.yaml` | Step prompt validation criteria |
| CDK Rules | `docs/refactor/specs/prompt_optimization_cdk_spec.yaml` | CDK infrastructure validation rules |
| Prompt Library | `docs/refactor/specs/prompt_library_spec.yaml` | Feature prompt definitions and model routing |
| OpenAPI | `docs/swagger/careervp-api-v1.yaml` | 27-operation API contract (source of truth) |

---

# PART 1: CRITICAL FIXES (Phase 1)

## Phase 1.1: Authentication Fix - JWT Authorizer

**Duration:** 1 day | **Effort:** 6 hours
**Status:** ⏳ PENDING
**Fixes:** 8 endpoints returning 401

### Specs

| Type | File | Purpose |
|------|------|---------|
| Reference | `docs/refactor2/specs/auth_spec.yaml` | JWT authorizer config |
| Reference | `docs/refactor/specs/prompt_optimization_cdk_spec.yaml` | CDK rules COGNITO_001-002 |

### Step 1.1.1: Create Standardized Auth Extraction Utility

**READ FIRST:**
- `docs/refactor2/specs/auth_spec.yaml`
- `src/backend/careervp/handlers/cover_letter_handler.py` (existing auth pattern)
- `src/backend/careervp/handlers/vpr_handler.py` (existing auth pattern)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
**READ FIRST:**
- `docs/refactor2/specs/auth_spec.yaml`
- `src/backend/careervp/handlers/cover_letter_handler.py`
- `src/backend/careervp/handlers/vpr_handler.py`

ROLE: Senior Backend Engineer specializing in AWS API Gateway authentication and Python Lambda handlers

CONTEXT: CareerVP has 8 endpoints returning 401 errors because handlers use inconsistent auth extraction methods. Some expect `event['requestContext']['authorizer']['userId']`, others use `X-User-Id` header fallback. We need a single standardized utility that all handlers import.

TASK: Create standardized auth extraction utility

1. Create: src/backend/careervp/handlers/auth_utils.py
   - Function: extract_user_id(event: dict[str, Any]) -> str | None
   - Priority order:
     a) HTTP API v2 JWT authorizer: event.requestContext.authorizer.jwt.claims.sub
     b) Lambda authorizer: event.requestContext.authorizer.principalId
     c) Fallback (dev only): headers.X-User-Id when AUTHORIZER_DISABLED=true
   - Return None if no valid user_id found
   - Log warning on extraction failure (AWS Powertools logger)

2. Create: src/backend/careervp/handlers/auth_middleware.py
   - Function: require_auth(handler_func) -> decorator
   - Extracts user_id via auth_utils.extract_user_id()
   - Returns 401 JSON response if user_id is None
   - Passes user_id as kwarg to handler function
   - Response format: {"error": {"code": "UNAUTHORIZED", "message": "Authentication required"}}

3. Create: tests/unit/test_auth_utils.py
   - test_extract_user_id_from_jwt_authorizer
   - test_extract_user_id_from_lambda_authorizer
   - test_extract_user_id_from_x_user_id_header_when_disabled
   - test_extract_user_id_returns_none_without_authorizer
   - test_extract_user_id_handles_malformed_event
   - test_require_auth_decorator_returns_401

CONSTRAINTS:
- DO: Use AWS Powertools logger for warnings
- DON'T: Hardcode role names or auth paths
- MUST: Return None (not raise exception) when auth missing

PROHIBITED (common mistakes):
- ❌ Direct payload.get('user_id') — use priority order (JWT → Lambda → X-User-Id)
- ❌ Enabling fallback in production — check AUTHORIZER_DISABLED env var only
- ❌ Duplicating logic in handlers — import from auth_utils

VERIFICATION:
pytest tests/unit/test_auth_utils.py -v
mypy careervp/handlers/auth_utils.py --strict
ruff check careervp/handlers/auth_utils.py
"""
```

### Step 1.1.2: Migrate All Handlers to Standardized Auth

**READ FIRST:**
- `src/backend/careervp/handlers/auth_utils.py` (created in Step 1.1.1)
- `src/backend/careervp/handlers/vpr_handler.py`
- `src/backend/careervp/handlers/cover_letter_handler.py`
- `src/backend/careervp/handlers/interview_prep_handler.py`
- `src/backend/careervp/handlers/gap_handler.py`

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
**READ FIRST:**
- `src/backend/careervp/handlers/auth_utils.py` (from Step 1.1.1)
- `src/backend/careervp/handlers/vpr_handler.py`
- `src/backend/careervp/handlers/cover_letter_handler.py`
- `src/backend/careervp/handlers/interview_prep_handler.py`

ROLE: Senior Backend Engineer specializing in Python refactoring and API Gateway Lambda handlers

CONTEXT: All handlers must use the standardized auth extraction from auth_utils.py instead of their own ad-hoc extraction logic. This fixes 8 endpoints returning 401 errors.

TASK: Migrate all handlers to use auth_utils.extract_user_id() or @require_auth decorator

1. Update: src/backend/careervp/handlers/vpr_handler.py
   - REMOVE: direct `event["requestContext"]["authorizer"]["userId"]` extraction
   - ADD: `from careervp.handlers.auth_utils import extract_user_id`
   - USE: `user_id = extract_user_id(event)` with proper None check

2. Update: src/backend/careervp/handlers/cover_letter_handler.py
   - REMOVE: `_extract_authenticated_user_id()` private function
   - REMOVE: `_extract_user_id_from_authorizer()` private function
   - REMOVE: `_authorizer_disabled()` check
   - ADD: Import from auth_utils
   - USE: Standardized extraction

3. Update: src/backend/careervp/handlers/interview_prep_handler.py
   - Same pattern: remove ad-hoc auth, use auth_utils

4. Update: src/backend/careervp/handlers/gap_handler.py
   - Same pattern: ensure using auth_utils (may already use X-User-Id)

5. Update: src/backend/careervp/handlers/cv_tailoring_handler.py
   - Same pattern: standardize auth extraction

6. Update: src/backend/careervp/handlers/job_handler.py
   - Same pattern: ensure auth extraction for GET /jobs/{jobId}

7. Verify no handler has its own auth extraction:
   - grep -r "requestContext.*authorizer" src/backend/careervp/handlers/ → only auth_utils.py
   - grep -r "_extract.*user_id" src/backend/careervp/handlers/ → only auth_utils.py

VALIDATION CRITERIA (must all pass):
- [ ] No handler has its own auth extraction (grep verification)
- [ ] All handlers import from auth_utils
- [ ] Existing unit tests still pass: pytest tests/unit/ -v
- [ ] Type check passes: mypy careervp/handlers/ --strict
- [ ] Lint passes: ruff check careervp/handlers/

OUTPUT FORMAT: Provide complete diffs for each handler file. Output results to docs/refactor2/execution_runbook_results.md.
"""
```

### Phase 1.1 Verification

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Verify no ad-hoc auth extraction remains
grep -r "requestContext.*authorizer" careervp/handlers/ | grep -v auth_utils.py | grep -v __pycache__
# Expected: 0 matches

# Unit tests
uv run pytest tests/unit/test_auth_utils.py -v --tb=short

# Full handler test suite
uv run pytest tests/unit/ -v --tb=short -k "handler"

# Lint
uv run ruff check careervp/handlers/

# Type check
uv run mypy careervp/handlers/auth_utils.py careervp/handlers/auth_middleware.py --strict
```

---

## Phase 1.2: Missing Endpoint Handlers

**Duration:** 1 day | **Effort:** 8 hours
**Status:** ⏳ PENDING
**Fixes:** 5 endpoints returning 404

### Specs

| Type | File | Purpose |
|------|------|---------|
| Reference | `docs/refactor2/specs/api_contract_spec.yaml` | Endpoint schemas |
| Reference | `docs/swagger/careervp-api-v1.yaml` | OpenAPI response schemas |

### Step 1.2.1: Implement User Management Handlers

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (UserProfile, UpdateUserRequest schemas)
- `docs/refactor2/specs/api_contract_spec.yaml` (GET /users/me, PUT /users/me, GET /users/me/cvs)
- `src/backend/careervp/handlers/cv_upload_handler.py` (existing pattern)
- `src/backend/careervp/dal/dynamo_dal_handler.py` (DAL pattern)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (UserProfile, UpdateUserRequest, CVListResponse schemas)
- `src/backend/careervp/handlers/cv_upload_handler.py` (existing handler pattern)
- `src/backend/careervp/dal/dynamo_dal_handler.py` (DAL pattern)

ROLE: Senior Backend Engineer specializing in AWS Lambda handlers and DynamoDB data access

CONTEXT: Three user management endpoints return 404 because handlers don't exist. The API Gateway routes ARE deployed (from execution_runbook_2 Step 10.x) but no Lambda function handles these routes. We need to create the handler.

TASK: Implement user management handler

1. Create: src/backend/careervp/handlers/user_handler.py
   - GET /users/me → get_current_user(event, context)
     * Extract user_id from auth (using auth_utils)
     * Query DynamoDB users table: pk=user_id, sk="PROFILE"
     * Return 200 with UserProfile JSON
     * Return 404 if user not found
   - PUT /users/me → update_current_user(event, context)
     * Extract user_id from auth
     * Parse UpdateUserRequest from body (name, timezone)
     * Update DynamoDB item
     * Return 200 with updated UserProfile
     * Return 400 on validation error
   - GET /users/me/cvs → list_user_cvs(event, context)
     * Extract user_id from auth
     * Query DynamoDB: pk=user_id, sk begins_with "CV#"
     * Support pagination (limit, cursor query params)
     * Return 200 with CVListResponse {cvs: [...], cursor: "..."}

2. Add Pydantic models (if not existing):
   - UserProfile(id, email, name, created_at)
   - UpdateUserRequest(name: str | None, timezone: str | None)

3. Create: tests/unit/test_user_handler.py
   - test_get_user_returns_profile
   - test_get_user_returns_404_for_missing
   - test_update_user_modifies_name
   - test_update_user_returns_400_for_invalid
   - test_list_cvs_returns_user_cvs
   - test_list_cvs_supports_pagination

VALIDATION CRITERIA (must all pass):
- [ ] GET /users/me returns 200 with UserProfile for existing user
- [ ] GET /users/me returns 404 for missing user
- [ ] PUT /users/me updates profile and returns 200
- [ ] GET /users/me/cvs returns paginated list
- [ ] All handlers use auth_utils for user extraction
- [ ] Unit tests pass: pytest tests/unit/test_user_handler.py -v
- [ ] Type check passes: mypy careervp/handlers/user_handler.py --strict
- [ ] Lint passes: ruff check careervp/handlers/user_handler.py

OUTPUT FORMAT: Provide complete implementation. Output results to docs/refactor2/execution_runbook_results.md.
"""
```

### Step 1.2.2: Implement Job List and Health Handlers

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (JobListResponse, HealthResponse schemas)
- `src/backend/careervp/handlers/job_handler.py` (existing job create handler)

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (JobListResponse, HealthResponse schemas)
- `src/backend/careervp/handlers/job_handler.py` (existing handler)

ROLE: Backend Engineer specializing in AWS Lambda and REST API design

CONTEXT: GET /jobs and GET /health return 404 because these handlers are missing. The job POST handler exists but GET /jobs (list) does not. Health check endpoint has no handler.

TASK: Add list endpoint to job handler and create health handler

1. Update: src/backend/careervp/handlers/job_handler.py
   - ADD: GET /jobs → list_jobs(event, context)
     * Extract user_id from auth
     * Query DynamoDB: pk=user_id, sk begins_with "JOB#"
     * Support limit query parameter (default 20)
     * Return 200 with JobListResponse {jobs: [...]}

2. Create: src/backend/careervp/handlers/health_handler.py
   - GET /health → health_check(event, context)
     * Check DynamoDB connectivity (describe_table or get_item)
     * Return 200 with HealthResponse {status, timestamp, version, services}
     * Return "degraded" if DynamoDB unreachable
     * NO authentication required

3. Create: tests/unit/test_health_handler.py
   - test_health_returns_200
   - test_health_includes_service_status
   - test_health_no_auth_required

4. Update: tests/unit/test_job_handler.py
   - test_list_jobs_returns_user_jobs
   - test_list_jobs_empty_for_new_user

VALIDATION CRITERIA (must all pass):
- [ ] GET /jobs returns 200 with user's jobs
- [ ] GET /health returns 200 with service status
- [ ] Health endpoint works without auth
- [ ] Unit tests pass: pytest tests/unit/test_job_handler.py tests/unit/test_health_handler.py -v
- [ ] Lint passes: ruff check careervp/handlers/job_handler.py careervp/handlers/health_handler.py

OUTPUT FORMAT: Provide complete implementation. Output results to docs/refactor2/execution_runbook_results.md.
"""
```

### Phase 1.2 Verification

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Unit tests for new handlers
uv run pytest tests/unit/test_user_handler.py tests/unit/test_health_handler.py -v --tb=short

# Verify no 404 for these routes (requires deployed API)
# curl -s "$API_BASE/users/me" -H "Authorization: Bearer $TOKEN" | jq '.id'
# curl -s "$API_BASE/health" | jq '.status'

# Lint
uv run ruff check careervp/handlers/user_handler.py careervp/handlers/health_handler.py
```

---

## Phase 1.3: Pydantic Validation Fixes

**Duration:** 0.5 day | **Effort:** 4 hours
**Status:** ⏳ PENDING
**Fixes:** 3 endpoints returning 400 (extra='forbid' rejecting workflow fields)

### Specs

| Type | File | Purpose |
|------|------|---------|
| Reference | `docs/refactor2/specs/api_contract_spec.yaml` | Request schemas |
| Reference | `docs/swagger/careervp-api-v1.yaml` | OpenAPI request models |

### Step 1.3.1: Update API Models for Workflow Pattern

**READ FIRST:**
- `src/backend/careervp/models/api_models.py` (current models with extra='forbid')
- `docs/swagger/careervp-api-v1.yaml` (CVTailoringRequest, CoverLetterRequest, InterviewPrepRequest)
- `docs/refactor2/specs/api_contract_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
**READ FIRST:**
- `src/backend/careervp/models/api_models.py`
- `docs/swagger/careervp-api-v1.yaml` (request schemas)

ROLE: Senior Backend Engineer specializing in Pydantic v2 model design and API validation

CONTEXT: Three endpoints return 400 because Pydantic models use `extra='forbid'` which rejects valid workflow fields. The OpenAPI spec defines both workflow (cv_id + job_id + vpr_id) and legacy (cv_id + job_description) patterns.

TASK: Update API models to support workflow pattern while maintaining validation

1. Update: src/backend/careervp/models/api_models.py

   CVTailoringRequest:
   - ADD: job_id: str | None = Field(None, description="Job ID (workflow pattern)")
   - ADD: vpr_id: str | None = Field(None, description="VPR ID (workflow pattern)")
   - ADD: job_description: str | None = Field(None, min_length=1, description="Job description (legacy)")
   - ADD: options: CVTailoringOptions | None = Field(None)
   - ADD: @model_validator(mode='after') to enforce either workflow (job_id + vpr_id) OR legacy (job_description)
   - KEEP: extra='forbid' for truly unknown fields

   CoverLetterRequest:
   - ENSURE: cv_id, job_id, vpr_id, gap_response_ids, company_research_id all present
   - ADD: options: CoverLetterOptions | None (tone, length, include_portfolio_link)
   - Match OpenAPI CoverLetterRequest schema exactly

   InterviewPrepRequest:
   - ENSURE: vpr_id, gap_response_ids required
   - ADD: focus_areas: list[str] | None
   - ADD: question_count: int = Field(default=5)
   - Match OpenAPI InterviewPrepRequest schema exactly

2. Create option models:
   - CVTailoringOptions(preserve_length: bool = True, highlight_keywords: bool = True, target_ats: str = "standard")
   - CoverLetterOptions(tone: Literal["professional","conversational","formal"] = "professional", length: Literal["short","standard","long"] = "standard", include_portfolio_link: bool = False)

3. Create: tests/unit/test_api_models_workflow.py
   - test_cv_tailoring_workflow_pattern_accepted
   - test_cv_tailoring_legacy_pattern_accepted
   - test_cv_tailoring_neither_pattern_rejected
   - test_cover_letter_all_required_fields
   - test_interview_prep_defaults
   - test_unknown_fields_still_rejected

VALIDATION CRITERIA (must all pass):
- [ ] CVTailoringRequest accepts workflow pattern (cv_id + job_id + vpr_id)
- [ ] CVTailoringRequest accepts legacy pattern (cv_id + job_description)
- [ ] CVTailoringRequest rejects when neither pattern provided
- [ ] CoverLetterRequest validates all required fields per OpenAPI
- [ ] InterviewPrepRequest has correct defaults
- [ ] Unknown fields still rejected (extra='forbid' preserved for safety)
- [ ] Unit tests pass: pytest tests/unit/test_api_models_workflow.py -v
- [ ] Type check passes: mypy careervp/models/api_models.py --strict

OUTPUT FORMAT: Provide complete model definitions. Output results to docs/refactor2/execution_runbook_results.md.
"""
```

### Phase 1.3 Verification

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Model unit tests
uv run pytest tests/unit/test_api_models_workflow.py -v --tb=short

# Verify existing model tests still pass
uv run pytest tests/unit/ -v --tb=short -k "model"

# Type check
uv run mypy careervp/models/api_models.py --strict
```

---

## Phase 1.4: DAL Migration (CVTable → DynamoDalHandler)

**Duration:** 1 day | **Effort:** 8 hours
**Status:** ⏳ PENDING

### Specs

| Type | File | Purpose |
|------|------|---------|
| Reference | `docs/refactor2/specs/dal_migration_spec.yaml` | Migration plan and method signatures |
| Reference | `src/backend/careervp/dal/dynamo_dal_handler.py` | Target DAL pattern |

### Step 1.4.1: Add New Methods to DynamoDalHandler

**READ FIRST:**
- `docs/refactor2/specs/dal_migration_spec.yaml`
- `src/backend/careervp/dal/dynamo_dal_handler.py` (existing VPR methods)
- `src/backend/careervp/dal/cv_dal.py` (CVTable to deprecate)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
**READ FIRST:**
- `docs/refactor2/specs/dal_migration_spec.yaml`
- `src/backend/careervp/dal/dynamo_dal_handler.py`
- `src/backend/careervp/dal/cv_dal.py`

ROLE: Senior Backend Engineer specializing in DynamoDB data access layer design, AWS Powertools, and Python type safety

CONTEXT: Gap Analysis, CV Tailoring, and Cover Letter handlers currently use CVTable which has no error handling, logging, or observability. We need to add new methods to DynamoDalHandler (which already works for VPR) and migrate handlers to use it.

TASK: Add new methods to DynamoDalHandler following existing VPR method patterns

1. Update: src/backend/careervp/dal/dynamo_dal_handler.py
   Add these methods following the existing save_vpr/get_vpr pattern:

   Gap Analysis:
   - save_gap_analysis(user_id: str, job_id: str, gap: GapAnalysis) -> Result[None]
     * pk = user_id, sk = f"ARTIFACT#GAP_ANALYSIS#{job_id}#{gap.artifact_id}"
     * Set artifactId, ttl (90 days)
     * @tracer.capture_method decorator
   - get_gap_analysis(user_id: str, job_id: str) -> Result[GapAnalysis | None]
     * Query with begins_with, ScanIndexForward=False, Limit=1
   - get_gap_responses(user_id: str, job_id: str) -> Result[list[GapResponse]]
     * Query all responses for a job

   Tailored CV:
   - save_tailored_cv(user_id: str, tailored_cv: TailoredCV) -> Result[None]
   - get_tailored_cv(user_id: str, cv_tailoring_id: str) -> Result[TailoredCV | None]
   - list_tailored_cvs(user_id: str, limit: int = 20) -> Result[list[TailoredCV]]

   Cover Letter:
   - save_cover_letter(user_id: str, cover_letter: CoverLetter) -> Result[None]
   - get_cover_letter(user_id: str, cover_letter_id: str) -> Result[CoverLetter | None]
   - list_cover_letters(user_id: str, limit: int = 20) -> Result[list[CoverLetter]]

   Interview Prep:
   - save_interview_prep(user_id: str, interview_prep: InterviewPrep) -> Result[None]
   - get_interview_prep(user_id: str, interview_prep_id: str) -> Result[InterviewPrep | None]

2. All methods MUST:
   - Use @tracer.capture_method decorator
   - Use logger.info() on success, logger.exception() on failure
   - Return Result[T] with proper ResultCode
   - Set TTL to 90 days
   - Handle ClientError and ValidationError

3. Update: src/backend/careervp/dal/cv_dal.py
   - Add @deprecated("Use DynamoDalHandler instead") to CVTable class

4. Create: tests/unit/test_dal_migration.py
   - test_save_gap_analysis_stores_correctly
   - test_get_gap_analysis_retrieves_latest
   - test_save_tailored_cv_stores_correctly
   - test_save_cover_letter_stores_correctly
   - test_save_interview_prep_stores_correctly
   - test_dal_handles_dynamodb_error
   - test_dal_sets_ttl_correctly

CONSTRAINTS:
- DO: Use Result[T] pattern for all return values
- DO: Import from careervp.dal.dynamo_dal_handler only
- DO: Use @tracer.capture_method on every method
- MUST: Set TTL to exactly 7776000 seconds (90 days)
- MUST: Return None (not raise exception) on errors
- DON'T: Call table.put_item() directly — use dal methods
- DON'T: Handle pagination manually — use dal.list_* methods

PROHIBITED (common mistakes):
- ❌ Direct boto3 table.put_item() or table.get_item() — use DynamoDalHandler methods
- ❌ Hardcoding table names — use JOBS_TABLE_NAME env var
- ❌ Forgetting @tracer.capture_method — required for all methods
- ❌ Catching ClientError generically — use result.success check
- ❌ Setting TTL without 90-day conversion — must be seconds, not datetime

VERIFICATION:
pytest tests/unit/test_dal_migration.py -v
mypy careервp/dal/dynamo_dal_handler.py --strict
grep -n "@tracer.capture_method" careervp/dal/dynamo_dal_handler.py | wc -l
grep -r "table.put_item\|table.get_item" careervp/dal/ | grep -v "deprecated\|#"

OUTPUT FORMAT: Provide complete method implementations. Output results to docs/refactor2/execution_runbook_results.md.
"""
```

### Step 1.4.2: Migrate Handlers to DynamoDalHandler

**READ FIRST:**
- `src/backend/careervp/dal/dynamo_dal_handler.py` (updated in Step 1.4.1)
- `src/backend/careervp/handlers/gap_handler.py`
- `src/backend/careervp/handlers/cv_tailoring_handler.py`
- `src/backend/careervp/handlers/cover_letter_handler.py`

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
**READ FIRST:**
- `src/backend/careervp/dal/dynamo_dal_handler.py` (updated)
- `src/backend/careervp/handlers/gap_handler.py`
- `src/backend/careervp/handlers/cv_tailoring_handler.py`
- `src/backend/careervp/handlers/cover_letter_handler.py`

ROLE: Senior Backend Engineer specializing in Python refactoring and DynamoDB migration

CONTEXT: Three handlers still use CVTable (deprecated). Migrate them to DynamoDalHandler which has proper error handling, logging, tracing, and type safety.

TASK: Replace CVTable usage with DynamoDalHandler in all handlers

1. Update: src/backend/careervp/handlers/gap_handler.py
   - REMOVE: from careervp.dal.cv_dal import CVTable
   - ADD: from careervp.dal.dynamo_dal_handler import DynamoDalHandler
   - REPLACE: table.put_item() → dal.save_gap_analysis()
   - REPLACE: table.get_item() → dal.get_gap_analysis()
   - Handle Result return type (check result.success)

2. Update: src/backend/careervp/handlers/cv_tailoring_handler.py
   - Same pattern: CVTable → DynamoDalHandler
   - Use dal.save_tailored_cv() and dal.get_tailored_cv()

3. Update: src/backend/careervp/handlers/cover_letter_handler.py
   - Same pattern: CVTable → DynamoDalHandler
   - Use dal.save_cover_letter() and dal.get_cover_letter()

4. Verify no handler imports CVTable:
   - grep -r "from.*cv_dal import" careervp/handlers/ → 0 matches
   - grep -r "CVTable" careervp/handlers/ → 0 matches

VALIDATION CRITERIA (must all pass):
- [ ] No handler imports CVTable (grep verification)
- [ ] All handlers use DynamoDalHandler
- [ ] All handlers check Result.success before proceeding
- [ ] Existing unit tests still pass: pytest tests/unit/ -v
- [ ] Type check passes: mypy careervp/handlers/ --strict
- [ ] Lint passes: ruff check careervp/handlers/

OUTPUT FORMAT: Provide diffs for each handler. Output results to docs/refactor2/execution_runbook_results.md.
"""
```

### Phase 1.4 Verification

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Verify no CVTable usage in handlers
grep -r "CVTable\|from.*cv_dal import" careervp/handlers/ | grep -v __pycache__
# Expected: 0 matches

# DAL unit tests
uv run pytest tests/unit/test_dal_migration.py -v --tb=short

# All unit tests (ensure no regression)
uv run pytest tests/unit/ -v --tb=short

# Lint entire handlers directory
uv run ruff check careervp/handlers/ careervp/dal/

# Type check
uv run mypy careervp/dal/dynamo_dal_handler.py --strict
```

---

## Phase 1 Completion Verification

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# All Phase 1 unit tests
uv run pytest tests/unit/ -v --tb=short

# Lint all modified files
uv run ruff check careervp/

# Type check all modified files
uv run mypy careervp/ --strict

# Verify auth standardization
grep -r "requestContext.*authorizer" careervp/handlers/ | grep -v auth_utils.py | grep -v __pycache__
# Expected: 0 matches

# Verify DAL migration
grep -r "CVTable" careervp/handlers/ | grep -v __pycache__
# Expected: 0 matches
```

**Phase 1 Exit Criteria:**
- [ ] 0 ad-hoc auth extraction in handlers
- [ ] 0 CVTable usage in handlers
- [ ] All user endpoints return 200 (GET /users/me, PUT /users/me, GET /users/me/cvs)
- [ ] GET /jobs returns 200
- [ ] GET /health returns 200
- [ ] CV Tailoring accepts workflow pattern (no more 400)
- [ ] Cover Letter accepts full payload (no more 400)
- [ ] Interview Prep accepts full payload (no more 400)
- [ ] All unit tests pass (100% pass rate)
- [ ] ruff check clean
- [ ] mypy --strict clean

---

# PART 2: ASYNC PROCESSING (Phase 2)

## Phase 2.1: VPR Async Infrastructure

**Duration:** 2 days | **Effort:** 12 hours
**Status:** ⏳ PENDING
**Dependency:** Phase 1 complete (auth working)

### Specs

| Type | File | Purpose |
|------|------|---------|
| Reference | `docs/refactor2/specs/async_processing_spec.yaml` | Full async architecture |
| Reference | `docs/refactor/specs/prompt_optimization_cdk_spec.yaml` | CDK rules SQS_001-004, ASYNC_001-006 |

### Step 2.1.1: Create VPR Submit Handler (202 Pattern)

**READ FIRST:**
- `docs/refactor2/specs/async_processing_spec.yaml`
- `src/backend/careervp/handlers/vpr_handler.py` (current sync handler)
- `docs/swagger/careervp-api-v1.yaml` (VPRGenerateRequest, VPRGenerateResponse)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
**READ FIRST:**
- `docs/refactor2/specs/async_processing_spec.yaml`
- `src/backend/careervp/handlers/vpr_handler.py`
- `docs/swagger/careervp-api-v1.yaml` (VPR schemas)

ROLE: Senior Backend Engineer specializing in AWS SQS, async Lambda patterns, and DynamoDB job tracking

CONTEXT: VPR generation takes 30-60s, exceeding API Gateway's 29s timeout. We need to split the sync handler into: (1) Submit handler that returns 202 immediately, (2) Worker handler that processes via SQS, (3) Status handler for polling.

TASK: Create VPR submit handler that returns 202 and queues work

1. Create: src/backend/careervp/handlers/vpr_submit_handler.py
   - POST /vpr/generate → submit_vpr(event, context)
   - Steps:
     a) Extract user_id via auth_utils
     b) Parse VPRGenerateRequest (cv_id, job_id, gap_response_ids)
     c) Validate prerequisites (cv exists, gap responses exist)
     d) Generate job_id (UUID v4)
     e) Create PENDING job record in DynamoDB jobs table:
        {job_id, user_id, job_type: "vpr", status: "PENDING", created_at, input: {cv_id, job_id, gap_response_ids}}
     f) Send SQS message with job_id and input data
     g) Return 202: {request_id: job_id, status: "processing", estimated_time_seconds: 60}
   - Idempotency: Check if identical request exists (same cv_id + job_id + user_id within 5 min)

2. Create: src/backend/careervp/models/job_models.py
   - JobStatus enum: PENDING, PROCESSING, COMPLETED, FAILED
   - JobRecord(job_id, user_id, job_type, status, input, output, created_at, started_at, completed_at, error, token_usage)

3. Create: tests/unit/test_vpr_submit_handler.py
   - test_submit_returns_202_with_job_id
   - test_submit_creates_pending_job
   - test_submit_sends_sqs_message
   - test_submit_validates_required_fields
   - test_submit_idempotent_for_duplicate
   - test_submit_returns_422_without_prerequisites

CONSTRAINTS:
- MUST: Return 202 status code (not 200 or 201)
- MUST: Set job status to PENDING (not PROCESSING or COMPLETED)
- MUST: Generate job_id as UUID v4
- MUST: Check prerequisites before queuing (cv_exists, gap_responses_exist)
- MUST: Implement idempotency check (same cv_id + job_id + user_id within 5 min)
- DON'T: Process the job synchronously — queue it immediately
- DON'T: Return final result in 202 response — only return job_id + status

PROHIBITED (common mistakes):
- ❌ Returning 200 instead of 202 — client expects "Accepted" status
- ❌ Setting job status to PROCESSING before queuing — worker sets this
- ❌ Skipping idempotency check — leads to duplicate job submissions
- ❌ Not validating prerequisites — causes downstream failures in worker
- ❌ Sending job_id but not request_id field — client expects both
- ❌ Blocking on SQS message confirmation — should respond immediately after send()

VERIFICATION:
pytest tests/unit/test_vpr_submit_handler.py -v
mypy careervp/handlers/vpr_submit_handler.py --strict
grep -n "return.*202\|status.*202" careervp/handlers/vpr_submit_handler.py
aws sqs receive-message --queue-url $VPR_QUEUE_URL --region us-east-1 | jq '.Messages | length'

OUTPUT FORMAT: Complete implementation. Output results to docs/refactor2/execution_runbook_results.md.
"""
```

### Step 2.1.2: Create VPR Worker Handler (SQS Consumer)

**READ FIRST:**
- `docs/refactor2/specs/async_processing_spec.yaml`
- `src/backend/careervp/logic/vpr_generator.py` (existing 6-stage pipeline)
- `src/backend/careervp/handlers/vpr_submit_handler.py` (from Step 2.1.1)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
**READ FIRST:**
- `docs/refactor2/specs/async_processing_spec.yaml`
- `src/backend/careervp/logic/vpr_generator.py` (6-stage pipeline)

ROLE: Senior Backend Engineer specializing in AWS SQS Lambda consumers, S3 storage, and error handling

CONTEXT: The VPR worker Lambda is triggered by SQS messages from the submit handler. It runs the 6-stage VPR pipeline, stores results in S3, and updates the job status in DynamoDB.

TASK: Create VPR worker handler that processes SQS messages

1. Create: src/backend/careervp/handlers/vpr_worker_handler.py
   - SQS event handler: lambda_handler(event, context)
   - For each SQS record:
     a) Parse job_id and input data from message body
     b) Update job status to PROCESSING in DynamoDB (set started_at)
     c) Fetch CV data from DynamoDB/S3
     d) Fetch job posting data from DynamoDB
     e) Fetch gap responses from DynamoDB
     f) Run VPR 6-stage pipeline (vpr_generator.generate())
     g) Store VPR result JSON in S3: results/{job_id}.json
     h) Update job status to COMPLETED:
        - Set completed_at
        - Set result_url (S3 presigned URL, 1h expiry)
        - Set token_usage {input_tokens, output_tokens}
     i) On error: Update job status to FAILED with error_message

2. Error handling:
   - Catch LLM errors → mark FAILED, include error in job record
   - Catch DynamoDB errors → raise (SQS will retry)
   - Catch S3 errors → mark FAILED
   - Lambda timeout protection: Check remaining time, save partial if < 30s

3. Create: tests/unit/test_vpr_worker_handler.py
   - test_worker_processes_sqs_message
   - test_worker_updates_status_to_processing
   - test_worker_stores_result_in_s3
   - test_worker_updates_status_to_completed
   - test_worker_handles_llm_failure
   - test_worker_records_token_usage

CONSTRAINTS:
- MUST: Update status in order: PENDING → PROCESSING → COMPLETED (or FAILED)
- MUST: Never skip PROCESSING state — client polls for this
- MUST: Store result in S3 before updating job to COMPLETED
- MUST: Set started_at when transitioning to PROCESSING
- MUST: Handle SQS visibility timeout (300s) — save partial if < 30s remaining
- MUST: Record token_usage {input_tokens, output_tokens}
- DON'T: Update job status without checking current state first
- DON'T: Return results inline — always store in S3 first

PROHIBITED (common mistakes):
- ❌ Updating job to COMPLETED without storing S3 result — data loss
- ❌ Skipping PROCESSING state — client polling loop expects it
- ❌ Not checking timeout remaining — leads to partial executions
- ❌ Setting started_at after running pipeline — should be immediate on PROCESSING
- ❌ Returning result instead of result_url — results too large for DynamoDB
- ❌ Not catching LLM errors separately — merge them with infrastructure errors
- ❌ Ignoring SQS message visibility — message may retry and duplicate

VERIFICATION:
pytest tests/unit/test_vpr_worker_handler.py -v
mypy careervp/handlers/vpr_worker_handler.py --strict
grep -n "PENDING\|PROCESSING\|COMPLETED" careervp/handlers/vpr_worker_handler.py | head -20
aws dynamodb scan --table-name jobs --filter-expression "attribute_exists(result_url)" --region us-east-1 | jq '.Count'

OUTPUT FORMAT: Complete implementation. Output results to docs/refactor2/execution_runbook_results.md.
"""
```

### Step 2.1.3: Create VPR Status Handler (Polling Endpoint)

**READ FIRST:**
- `docs/refactor2/specs/async_processing_spec.yaml`
- `docs/swagger/careervp-api-v1.yaml` (VPRStatusResponse schema)

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
**READ FIRST:**
- `docs/refactor2/specs/async_processing_spec.yaml`
- `docs/swagger/careervp-api-v1.yaml` (VPRStatusResponse schema)

ROLE: Backend Engineer specializing in REST API polling patterns

CONTEXT: Frontend polls GET /vpr/{vprId} to check VPR generation status. Returns current job status and, when completed, the result URL or inline result.

TASK: Create VPR status handler for polling

1. Create: src/backend/careervp/handlers/vpr_status_handler.py
   - GET /vpr/{vprId} → get_vpr_status(event, context)
   - Steps:
     a) Extract user_id from auth
     b) Extract vprId from path parameters
     c) Query jobs table for job record
     d) If not found: return 404
     e) If PENDING: return 200 {id, status: "pending", created_at}
     f) If PROCESSING: return 200 {id, status: "processing", created_at, started_at}
     g) If COMPLETED: return 200 {id, status: "completed", result: {uvp, differentiators, ...}, created_at, completed_at}
     h) If FAILED: return 200 {id, status: "failed", error: "...", created_at}

2. For COMPLETED status:
   - Option A: Fetch result from S3 presigned URL and return inline
   - Option B: Return result_url for client to fetch directly
   - Use Option B (better for large results)

3. Create: tests/unit/test_vpr_status_handler.py
   - test_status_returns_pending
   - test_status_returns_processing
   - test_status_returns_completed_with_url
   - test_status_returns_failed_with_error
   - test_status_returns_404_for_unknown

VALIDATION CRITERIA (must all pass):
- [ ] Returns correct status for each job state
- [ ] COMPLETED includes result_url or inline result
- [ ] 404 for non-existent job
- [ ] Unit tests pass: pytest tests/unit/test_vpr_status_handler.py -v

OUTPUT FORMAT: Complete implementation. Output results to docs/refactor2/execution_runbook_results.md.
"""
```

### Phase 2.1 Verification

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# All async handler tests
uv run pytest tests/unit/test_vpr_submit_handler.py tests/unit/test_vpr_worker_handler.py tests/unit/test_vpr_status_handler.py -v --tb=short

# Lint
uv run ruff check careervp/handlers/vpr_submit_handler.py careervp/handlers/vpr_worker_handler.py careervp/handlers/vpr_status_handler.py

# Type check
uv run mypy careervp/handlers/vpr_submit_handler.py careervp/handlers/vpr_worker_handler.py careervp/handlers/vpr_status_handler.py --strict
```

---

## Phase 2.2: CV Tailoring Async (Optional)

**Duration:** 1 day | **Effort:** 4 hours
**Status:** ⏳ PENDING
**Dependency:** Phase 2.1 complete (reuse infrastructure)

### Step 2.2.1: Convert CV Tailoring to Async Pattern

**READ FIRST:**
- `src/backend/careervp/handlers/vpr_submit_handler.py` (submit pattern from Phase 2.1)
- `src/backend/careervp/handlers/cv_tailoring_handler.py` (current sync handler)

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
**READ FIRST:**
- `src/backend/careervp/handlers/vpr_submit_handler.py` (async submit pattern)
- `src/backend/careervp/handlers/cv_tailoring_handler.py` (current handler)

ROLE: Backend Engineer specializing in async Lambda patterns

CONTEXT: CV Tailoring with JSA 3-step methodology may exceed API Gateway timeout. Reuse the VPR async infrastructure (same SQS queue with message filtering, same jobs table).

TASK: Convert CV Tailoring to async pattern, reusing VPR async infrastructure

1. Update: src/backend/careervp/handlers/cv_tailoring_handler.py
   - POST /cv-tailoring/generate → returns 202 (not 200)
   - Create PENDING job with job_type: "cv_tailoring"
   - Send SQS message with job_type attribute for filtering
   - Return: {request_id, status: "processing", estimated_time_seconds: 30}

2. Create: src/backend/careervp/handlers/cv_tailoring_worker_handler.py
   - SQS consumer for cv_tailoring job_type messages
   - Runs 3-step CV tailoring pipeline
   - Stores result in S3: results/cv-tailoring/{job_id}.json
   - Updates job status (same pattern as VPR worker)

3. GET /cv-tailoring/{cvTailoringId} already handled by status pattern
   - Reuse or extend vpr_status_handler pattern for cv_tailoring jobs

VALIDATION CRITERIA (must all pass):
- [ ] POST /cv-tailoring/generate returns 202
- [ ] Job tracked in same jobs table with job_type = "cv_tailoring"
- [ ] Worker processes and stores result
- [ ] Status polling works
- [ ] Unit tests pass

OUTPUT FORMAT: Complete implementation. Output results to docs/refactor2/execution_runbook_results.md.
"""
```

---

# PART 3: CDK INFRASTRUCTURE (Phase 3)

## Phase 3.1: Deploy JWT Authorizer + New Resources

**Duration:** 2 days | **Effort:** 10 hours
**Status:** ⏳ PENDING
**Dependency:** Phase 1 + 2 handlers ready

### Specs

| Type | File | Purpose |
|------|------|---------|
| Reference | `docs/refactor/specs/prompt_optimization_cdk_spec.yaml` | All CDK rules |
| Reference | `docs/refactor2/specs/auth_spec.yaml` | JWT authorizer config |
| Reference | `docs/refactor2/specs/async_processing_spec.yaml` | SQS, DDB, S3 resources |

### Step 3.1.1: Deploy JWT Authorizer to API Gateway

**READ FIRST:**
- `docs/refactor2/specs/auth_spec.yaml`
- `docs/refactor/specs/prompt_optimization_cdk_spec.yaml` (COGNITO_001, COGNITO_002)
- `infra/careervp/api_construct.py` (current API Gateway setup)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
**READ FIRST:**
- `docs/refactor2/specs/auth_spec.yaml`
- `docs/refactor/specs/prompt_optimization_cdk_spec.yaml` (COGNITO_001, COGNITO_002)
- `infra/careervp/api_construct.py`

ROLE: Senior AWS Solutions Architect specializing in CDK, API Gateway, and Cognito JWT authorization

CONTEXT: 8 endpoints return 401 because API Gateway routes lack JWT authorizer. We need to deploy a JWT authorizer and attach it to all protected routes.

TASK: Add JWT authorizer to CDK API Gateway construct

1. Update: infra/careervp/api_construct.py
   - Create HttpJwtAuthorizer:
     * JWT audience: configurable via CDK context (default: ["careervp-api"])
     * JWT issuer: Cognito User Pool URL from CDK context
   - Attach authorizer to all protected routes (NOT /auth/register, /auth/login, /health)
   - Protected routes list (22 of 27):
     /auth/refresh, /users/me (GET, PUT), /users/me/cv, /users/me/cvs,
     /jobs (POST, GET), /jobs/{jobId},
     /vpr/generate, /vpr/{vprId}, /users/me/vprs,
     /gap-analysis/questions, /gap-analysis/responses, /gap-analysis/{jobId}/questions,
     /cv-tailoring/generate, /cv-tailoring/{cvTailoringId}, /users/me/tailored-cvs,
     /cover-letter/generate, /cover-letter/{coverLetterId}, /users/me/cover-letters,
     /interview-prep/generate, /interview-prep/{interviewPrepId},
     /company-research/fetch, /company-research/{jobId}
   - Unprotected routes (5): /auth/register, /auth/login, /health

2. CDK rules compliance:
   - COGNITO_001: User pool must exist (reference by ID or ARN)
   - COGNITO_002: Authorizer must validate audience

3. Verification:
   - cdk synth succeeds
   - cdk-nag passes
   - Authorizer resource appears in CloudFormation template

VALIDATION CRITERIA (must all pass):
- [ ] JWT authorizer created in CDK template
- [ ] 22 routes have authorizer attached
- [ ] 5 routes remain unprotected
- [ ] cdk synth: npx cdk synth --app='python app.py' succeeds
- [ ] cdk-nag security scan passes

OUTPUT FORMAT: CDK construct code. Output results to docs/refactor2/execution_runbook_results.md.
"""
```

### Step 3.1.2: Deploy Async Processing Infrastructure

**READ FIRST:**
- `docs/refactor2/specs/async_processing_spec.yaml`
- `docs/refactor/specs/prompt_optimization_cdk_spec.yaml` (SQS_001-004, DDB_001-005, S3_001-004, LAMBDA_CONFIG_001-008)
- `infra/careervp/api_construct.py`

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
**READ FIRST:**
- `docs/refactor2/specs/async_processing_spec.yaml`
- `docs/refactor/specs/prompt_optimization_cdk_spec.yaml`
- `infra/careervp/api_construct.py`

ROLE: Senior AWS Solutions Architect specializing in CDK, SQS, Lambda, DynamoDB, and S3

CONTEXT: VPR async processing requires SQS queue, DLQ, jobs table, S3 results bucket, and worker Lambda. All must comply with CDK spec rules.

TASK: Deploy async processing infrastructure via CDK

1. Create SQS Queue + DLQ (per SQS_001-004):
   - Queue: careervp-vpr-jobs-queue-{env}
     * visibility_timeout: 300 (5 min, matches worker timeout)
     * message_retention_period: 345600 (4 days)
     * encryption: SQS_MANAGED (per SQS_002)
   - DLQ: careervp-vpr-jobs-dlq-{env}
     * max_receive_count: 3
     * retention: 14 days
   - SQS_001: Dead letter queue configured ✓
   - SQS_002: Encryption at rest ✓
   - SQS_003: Visibility timeout >= Lambda timeout ✓

2. Create DynamoDB Jobs Table (per DDB_001-005):
   - Table: careervp-jobs-table-{env}
   - PK: job_id (String)
   - GSI: user-id-index (PK: user_id, SK: created_at)
   - Billing: PAY_PER_REQUEST (per DDB_001)
   - PITR: true for prod, false for dev (per DDB_002)
   - TTL: expires_at attribute (per DDB_005)
   - Encryption: AWS_OWNED (per ENCRYPT_001)

3. Create S3 Results Bucket (per S3_001-004):
   - Bucket: careervp-{env}-vpr-results-{account_hash}
   - Encryption: S3_MANAGED (per ENCRYPT_002)
   - Block public access: ALL (per S3_001)
   - Lifecycle: delete after 30 days (per S3_003)
   - Versioning: enabled (per S3_002)

4. Create Worker Lambda (per LAMBDA_CONFIG_001-008):
   - Function: careervp-vpr-worker-{env}
   - Runtime: Python 3.13 (per NAG_LAMBDA_001)
   - Memory: 1024 MB (per LAMBDA_CONFIG_001)
   - Timeout: 300s (per LAMBDA_CONFIG_004, matches SQS visibility)
   - Tracing: ACTIVE (per LAMBDA_CONFIG_003)
   - Log retention: 30 days (per CW_001)
   - SQS event source mapping with batch_size: 1
   - IAM: least privilege (DDB read/write, S3 put, SQS consume) per IAM_001

5. Wire Lambda integrations:
   - vpr_submit_handler → POST /vpr/generate
   - vpr_status_handler → GET /vpr/{vprId}
   - vpr_worker_handler → SQS event source

6. Environment variables for all Lambdas:
   - JOBS_TABLE_NAME
   - VPR_RESULTS_BUCKET
   - VPR_QUEUE_URL
   - ANTHROPIC_API_KEY_SSM_PARAM

CONSTRAINTS:
- MUST: SQS queue has DLQ with max receive count = 3 (per async spec)
- MUST: DynamoDB TTL attribute = "expires_at" (per DDB_005)
- MUST: DynamoDB PITR enabled for prod, disabled for dev (per DDB_002)
- MUST: S3 bucket blocks ALL public access (per S3_001)
- MUST: Lambda memory ≥ 1024 MB (per LAMBDA_CONFIG_001)
- MUST: Lambda timeout = 300s (per LAMBDA_CONFIG_004, matches SQS visibility)
- MUST: X-Ray tracing ACTIVE (per LAMBDA_CONFIG_003)
- MUST: CloudWatch logs retention = 30 days (per CW_001)
- DON'T: Make S3 bucket versioning optional — must be enabled (per S3_002)
- DON'T: Use S3 KMS encryption in dev — S3-managed only (per ENCRYPT_002)

PROHIBITED (common mistakes):
- ❌ SQS without DLQ — messages disappear on repeated failures
- ❌ Lambda timeout < 300s — worker gets killed mid-pipeline
- ❌ S3 bucket versioning disabled — can't recover from accidental deletes
- ❌ Missing DynamoDB TTL — jobs accumulate forever
- ❌ S3 bucket with public access enabled — security breach
- ❌ Lambda memory < 1GB — timeouts on large VPR operations
- ❌ Lifecycle rule deleting too early — should be 30 days minimum (per S3_003)
- ❌ IAM roles with wildcards (*) in actions — use least privilege per resource
- ❌ Lambda package > 250MB — fails to deploy (per LAMBDA_SIZE_001)
- ❌ Missing environment variables — worker can't access resources

VERIFICATION:
cd infra && npx cdk synth --app='python app.py' 2>&1 | tail -30
cd infra && uv run cdk synth --app='python app.py' 2>&1 | grep -E "Error|AwsSolutions"
grep -n "DynamoDB::Table\|VisibilityTimeout\|RedrivePolicy" cdk.out/careervp-dev.template.json
aws s3api get-bucket-versioning --bucket careervp-dev-vpr-results-HASH --region us-east-1
aws dynamodb describe-table --table-name jobs --region us-east-1 | jq '.Table | {TimeToLiveDescription, BillingModeSummary}'

OUTPUT FORMAT: Complete CDK construct code. Output results to docs/refactor2/execution_runbook_results.md.
"""
```

### Step 3.1.3: Wire New Lambda Functions to API Gateway Routes

**READ FIRST:**
- `infra/careervp/api_construct.py` (route_map from execution_runbook_2)
- Step 3.1.1 and 3.1.2 outputs

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
**READ FIRST:**
- `infra/careervp/api_construct.py`

ROLE: AWS CDK Engineer

CONTEXT: New Lambda functions from Phase 1-2 need to be wired to their API Gateway routes. The routes already exist (from execution_runbook_2) but point to placeholder integrations.

TASK: Update API Gateway route integrations for new handlers

1. Update route_map in api_construct.py:
   - /users/me GET → user_handler Lambda
   - /users/me PUT → user_handler Lambda
   - /users/me/cvs GET → user_handler Lambda
   - /jobs GET → job_handler Lambda
   - /health GET → health_handler Lambda
   - /vpr/generate POST → vpr_submit_handler Lambda (was vpr_handler)
   - /vpr/{vprId} GET → vpr_status_handler Lambda (was vpr_handler)

2. Add new Lambda functions to CDK:
   - user_handler_func (if not existing)
   - health_handler_func
   - vpr_submit_func (replaces vpr_handler for POST)
   - vpr_status_func (replaces vpr_handler for GET)

3. Ensure all Lambdas have correct environment variables:
   - DYNAMODB_TABLE_NAME
   - ANTHROPIC_API_KEY_SSM_PARAM

VALIDATION CRITERIA:
- [ ] cdk synth succeeds
- [ ] All 27 routes have valid Lambda integrations
- [ ] No placeholder integrations remain

OUTPUT FORMAT: CDK route updates. Output results to docs/refactor2/execution_runbook_results.md.
"""
```

### Phase 3 Verification

```bash
cd /Users/yitzchak/Documents/dev/careervp/infra

# CDK synth
npx cdk synth --app='python app.py' 2>&1 | tail -20

# CDK-nag security scan
uv run cdk synth --app='python app.py' 2>&1 | grep -E "Error|Warning|AwsSolutions"

# Verify resource count
npx cdk synth --app='python app.py' | grep -c "AWS::"

# Verify JWT authorizer in template
npx cdk synth --app='python app.py' | grep -A5 "JwtAuthorizer"

# Verify SQS queue in template
npx cdk synth --app='python app.py' | grep -A5 "SQS::Queue"
```

---

# PART 4: LIVE TESTS + COMPLETION

## Phase 4.1: Deploy and Validate

**Duration:** 1 day | **Effort:** 4 hours
**Status:** ⏳ PENDING
**Dependency:** Phase 3 complete

### Pre-Deploy Checklist

- [ ] All unit tests passing: `uv run pytest tests/unit/ -v`
- [ ] All lint checks passing: `uv run ruff check careervp/`
- [ ] CDK synth succeeds: `cd infra && npx cdk synth`
- [ ] CDK-nag passes
- [ ] Lambda package size < 250MB

### Deploy

```bash
cd /Users/yitzchak/Documents/dev/careervp/infra

# Deploy to dev
npx cdk deploy --app='python app.py' --require-approval never

# Verify deployment
aws cloudformation describe-stacks --stack-name careervp-dev --region us-east-1 | jq '.Stacks[0].StackStatus'
# Expected: "UPDATE_COMPLETE" or "CREATE_COMPLETE"
```

### Live Test: 27-Endpoint Contract Gate

```bash
cd /Users/yitzchak/Documents/dev/careervp

# Configuration
API_BASE="${API_BASE:-https://<api-id>.execute-api.us-east-1.amazonaws.com/prod}"

# 1. Get auth token
TOKEN=$(curl -s -X POST "$API_BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d @docs/refactor2/payloads/auth_login.json | jq -r '.access_token')

echo "Token: ${TOKEN:0:20}..."

# 2. Test all 27 endpoints
PASS=0; FAIL=0

# Auth (3)
for ep in "POST /auth/register:201" "POST /auth/login:200" "POST /auth/refresh:200"; do
  METHOD=$(echo "$ep" | cut -d' ' -f1)
  PATH=$(echo "$ep" | cut -d' ' -f2 | cut -d: -f1)
  EXPECTED=$(echo "$ep" | cut -d: -f2)
  CODE=$(curl -sS -o /dev/null -w "%{http_code}" -X "$METHOD" "$API_BASE$PATH" \
    -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
    -d '{"email":"gate@test.com","password":"GateTest123!","name":"Gate"}')
  if [[ "$CODE" == "$EXPECTED" || "$CODE" == "400" || "$CODE" == "409" ]]; then
    echo "PASS: $METHOD $PATH -> $CODE"; ((PASS++))
  else
    echo "FAIL: $METHOD $PATH -> $CODE (expected $EXPECTED)"; ((FAIL++))
  fi
done

# Users (4)
CODE=$(curl -sS -o /dev/null -w "%{http_code}" "$API_BASE/users/me" -H "Authorization: Bearer $TOKEN")
echo "GET /users/me -> $CODE"; [[ "$CODE" =~ ^(200|404)$ ]] && ((PASS++)) || ((FAIL++))

CODE=$(curl -sS -o /dev/null -w "%{http_code}" -X PUT "$API_BASE/users/me" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Updated"}')
echo "PUT /users/me -> $CODE"; [[ "$CODE" =~ ^(200|400)$ ]] && ((PASS++)) || ((FAIL++))

CODE=$(curl -sS -o /dev/null -w "%{http_code}" -X POST "$API_BASE/users/me/cv" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d @docs/refactor2/payloads/cv_upload.json)
echo "POST /users/me/cv -> $CODE"; [[ "$CODE" =~ ^(201|200|400)$ ]] && ((PASS++)) || ((FAIL++))

CODE=$(curl -sS -o /dev/null -w "%{http_code}" "$API_BASE/users/me/cvs" -H "Authorization: Bearer $TOKEN")
echo "GET /users/me/cvs -> $CODE"; [[ "$CODE" == "200" ]] && ((PASS++)) || ((FAIL++))

# Jobs (3)
CODE=$(curl -sS -o /dev/null -w "%{http_code}" -X POST "$API_BASE/jobs" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d @docs/refactor2/payloads/job_create.json)
echo "POST /jobs -> $CODE"; [[ "$CODE" =~ ^(201|200|400)$ ]] && ((PASS++)) || ((FAIL++))

CODE=$(curl -sS -o /dev/null -w "%{http_code}" "$API_BASE/jobs" -H "Authorization: Bearer $TOKEN")
echo "GET /jobs -> $CODE"; [[ "$CODE" == "200" ]] && ((PASS++)) || ((FAIL++))

CODE=$(curl -sS -o /dev/null -w "%{http_code}" "$API_BASE/jobs/test-job-id" -H "Authorization: Bearer $TOKEN")
echo "GET /jobs/{id} -> $CODE"; [[ "$CODE" =~ ^(200|404)$ ]] && ((PASS++)) || ((FAIL++))

# VPR (3)
CODE=$(curl -sS -o /dev/null -w "%{http_code}" -X POST "$API_BASE/vpr/generate" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d @docs/refactor2/payloads/vpr_generate.json)
echo "POST /vpr/generate -> $CODE"; [[ "$CODE" =~ ^(202|400|422)$ ]] && ((PASS++)) || ((FAIL++))

CODE=$(curl -sS -o /dev/null -w "%{http_code}" "$API_BASE/vpr/test-vpr-id" -H "Authorization: Bearer $TOKEN")
echo "GET /vpr/{id} -> $CODE"; [[ "$CODE" =~ ^(200|404)$ ]] && ((PASS++)) || ((FAIL++))

CODE=$(curl -sS -o /dev/null -w "%{http_code}" "$API_BASE/users/me/vprs" -H "Authorization: Bearer $TOKEN")
echo "GET /users/me/vprs -> $CODE"; [[ "$CODE" == "200" ]] && ((PASS++)) || ((FAIL++))

# Gap Analysis (3)
CODE=$(curl -sS -o /dev/null -w "%{http_code}" -X POST "$API_BASE/gap-analysis/questions" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d @docs/refactor2/payloads/gap_questions_generate.json)
echo "POST /gap-analysis/questions -> $CODE"; [[ "$CODE" =~ ^(200|400)$ ]] && ((PASS++)) || ((FAIL++))

CODE=$(curl -sS -o /dev/null -w "%{http_code}" -X POST "$API_BASE/gap-analysis/responses" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d @docs/refactor2/payloads/gap_responses_submit.json)
echo "POST /gap-analysis/responses -> $CODE"; [[ "$CODE" =~ ^(200|400)$ ]] && ((PASS++)) || ((FAIL++))

CODE=$(curl -sS -o /dev/null -w "%{http_code}" "$API_BASE/gap-analysis/test-job-id/questions" -H "Authorization: Bearer $TOKEN")
echo "GET /gap-analysis/{id}/questions -> $CODE"; [[ "$CODE" =~ ^(200|404)$ ]] && ((PASS++)) || ((FAIL++))

# CV Tailoring (3)
CODE=$(curl -sS -o /dev/null -w "%{http_code}" -X POST "$API_BASE/cv-tailoring/generate" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d @docs/refactor2/payloads/cv_tailoring_generate.json)
echo "POST /cv-tailoring/generate -> $CODE"; [[ "$CODE" =~ ^(202|400|422)$ ]] && ((PASS++)) || ((FAIL++))

CODE=$(curl -sS -o /dev/null -w "%{http_code}" "$API_BASE/cv-tailoring/test-id" -H "Authorization: Bearer $TOKEN")
echo "GET /cv-tailoring/{id} -> $CODE"; [[ "$CODE" =~ ^(200|404)$ ]] && ((PASS++)) || ((FAIL++))

CODE=$(curl -sS -o /dev/null -w "%{http_code}" "$API_BASE/users/me/tailored-cvs" -H "Authorization: Bearer $TOKEN")
echo "GET /users/me/tailored-cvs -> $CODE"; [[ "$CODE" == "200" ]] && ((PASS++)) || ((FAIL++))

# Cover Letter (3)
CODE=$(curl -sS -o /dev/null -w "%{http_code}" -X POST "$API_BASE/cover-letter/generate" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d @docs/refactor2/payloads/cover_letter_generate.json)
echo "POST /cover-letter/generate -> $CODE"; [[ "$CODE" =~ ^(202|400|422)$ ]] && ((PASS++)) || ((FAIL++))

CODE=$(curl -sS -o /dev/null -w "%{http_code}" "$API_BASE/cover-letter/test-id" -H "Authorization: Bearer $TOKEN")
echo "GET /cover-letter/{id} -> $CODE"; [[ "$CODE" =~ ^(200|404)$ ]] && ((PASS++)) || ((FAIL++))

CODE=$(curl -sS -o /dev/null -w "%{http_code}" "$API_BASE/users/me/cover-letters" -H "Authorization: Bearer $TOKEN")
echo "GET /users/me/cover-letters -> $CODE"; [[ "$CODE" == "200" ]] && ((PASS++)) || ((FAIL++))

# Interview Prep (2)
CODE=$(curl -sS -o /dev/null -w "%{http_code}" -X POST "$API_BASE/interview-prep/generate" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d @docs/refactor2/payloads/interview_prep_generate.json)
echo "POST /interview-prep/generate -> $CODE"; [[ "$CODE" =~ ^(202|400)$ ]] && ((PASS++)) || ((FAIL++))

CODE=$(curl -sS -o /dev/null -w "%{http_code}" "$API_BASE/interview-prep/test-id" -H "Authorization: Bearer $TOKEN")
echo "GET /interview-prep/{id} -> $CODE"; [[ "$CODE" =~ ^(200|404)$ ]] && ((PASS++)) || ((FAIL++))

# Company Research (2)
CODE=$(curl -sS -o /dev/null -w "%{http_code}" -X POST "$API_BASE/company-research/fetch" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d @docs/refactor2/payloads/company_research_fetch.json)
echo "POST /company-research/fetch -> $CODE"; [[ "$CODE" =~ ^(202|400|503)$ ]] && ((PASS++)) || ((FAIL++))

CODE=$(curl -sS -o /dev/null -w "%{http_code}" "$API_BASE/company-research/test-job-id" -H "Authorization: Bearer $TOKEN")
echo "GET /company-research/{id} -> $CODE"; [[ "$CODE" =~ ^(200|404)$ ]] && ((PASS++)) || ((FAIL++))

# Health (1)
CODE=$(curl -sS -o /dev/null -w "%{http_code}" "$API_BASE/health")
echo "GET /health -> $CODE"; [[ "$CODE" == "200" ]] && ((PASS++)) || ((FAIL++))

# Summary
echo ""
echo "========================================="
echo "Contract Gate: $PASS/27 PASSED, $FAIL/27 FAILED"
echo "========================================="
[[ "$FAIL" -eq 0 ]] && echo "ALL 27 ENDPOINTS OPERATIONAL" || echo "FAILURES DETECTED - SEE ABOVE"
```

### Live Test: Async VPR Flow

```bash
# Requires: CV uploaded, job created, gap analysis completed

# 1. Submit VPR
VPR_RESPONSE=$(curl -sS -X POST "$API_BASE/vpr/generate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d @docs/refactor2/payloads/vpr_generate.json)
JOB_ID=$(echo "$VPR_RESPONSE" | jq -r '.request_id')
echo "VPR Job submitted: $JOB_ID"

# 2. Poll for completion (max 120s)
for i in $(seq 1 24); do
  sleep 5
  STATUS=$(curl -sS "$API_BASE/vpr/$JOB_ID" \
    -H "Authorization: Bearer $TOKEN" | jq -r '.status')
  echo "Poll $i: status=$STATUS"
  [[ "$STATUS" == "completed" || "$STATUS" == "failed" ]] && break
done

# 3. Verify result
if [[ "$STATUS" == "completed" ]]; then
  RESULT=$(curl -sS "$API_BASE/vpr/$JOB_ID" -H "Authorization: Bearer $TOKEN")
  echo "VPR Result:"
  echo "$RESULT" | jq '{status, uvp: .result.uvp, differentiators_count: (.result.differentiators | length)}'
  echo "ASYNC VPR FLOW: PASSED"
else
  echo "ASYNC VPR FLOW: FAILED (status=$STATUS)"
fi
```

---

## Completion Checklist

### Phase 1: Critical Fixes
- [ ] Step 1.1.1: Auth extraction utility created
- [ ] Step 1.1.2: All handlers migrated to auth_utils
- [ ] Step 1.2.1: User management handlers created
- [ ] Step 1.2.2: Job list and health handlers created
- [ ] Step 1.3.1: API models updated for workflow pattern
- [ ] Step 1.4.1: DynamoDalHandler new methods added
- [ ] Step 1.4.2: Handlers migrated from CVTable to DynamoDalHandler
- [ ] Phase 1 verification: All checks pass

### Phase 2: Async Processing
- [ ] Step 2.1.1: VPR submit handler (202 pattern)
- [ ] Step 2.1.2: VPR worker handler (SQS consumer)
- [ ] Step 2.1.3: VPR status handler (polling)
- [ ] Step 2.2.1: CV Tailoring async (optional)
- [ ] Phase 2 verification: All checks pass

### Phase 3: CDK Infrastructure
- [ ] Step 3.1.1: JWT authorizer deployed
- [ ] Step 3.1.2: Async infrastructure (SQS, DDB, S3, worker Lambda)
- [ ] Step 3.1.3: Lambda integrations wired to routes
- [ ] Phase 3 verification: cdk synth + cdk-nag pass

### Phase 4: Live Tests
- [ ] Deploy to dev/staging
- [ ] 27-endpoint contract gate: 27/27 pass
- [ ] Async VPR flow: submit → poll → complete
- [ ] Quality gates: anti-AI, ATS >= 8.0

### Final Metrics
- [ ] 0 authentication failures (401) — was 8
- [ ] 0 missing endpoints (404) — was 5
- [ ] 0 validation errors (400) — was 3
- [ ] VPR generation: async, no timeout
- [ ] All handlers use DynamoDalHandler
- [ ] All handlers use auth_utils
- [ ] 100% unit test pass rate
- [ ] ruff check clean
- [ ] mypy --strict clean
- [ ] CDK-nag passes

---

**END OF EXECUTION RUNBOOK 3.0**

**Total Steps:** 12
**Total Phases:** 4
**Estimated Duration:** 3-4 weeks
**Document Version:** 3.0
**Last Updated:** 2026-02-20
