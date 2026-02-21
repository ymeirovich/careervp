# REFACTOR2 Comprehensive Plan

**Date:** 2026-02-20
**Updated:** 2026-02-20 (v1.1 - Reflects completed work from execution_runbook_2)
**Status:** Partially Complete - Phase 3 & 4 Done, Phase 1 & 2 Pending
**Priority:** P0 (Critical - Auth/Infra Gaps Remain)

---

## Executive Summary

This document outlines a comprehensive refactoring plan (REFACTOR2) to address:
1. **Remaining 4xx/5xx API errors** from live test results
2. **Authentication failures** across multiple endpoints
3. **Workflow-based payload design** with async processing
4. **Handler→DAL architectural inconsistencies**
5. **Job Search Assistant (JSA) capability alignment**

**Current State (Updated 2026-02-20):**
- JSA features COMPLETE: 6-stage VPR, 3-step CV Tailoring, Gap Analysis tagging, Cover Letter scaffold, FVS Validator, Knowledge Base, Interview Prep all implemented via execution_runbook_2
- All 27 API Gateway routes wired in CDK (but auth/handler gaps remain)
- 12 endpoints still returning 4xx/5xx errors (authentication, validation, missing handlers)
- No async processing implemented (VPR times out at 30-60s)
- Inconsistent DAL usage across handlers (CVTable still in use)

**Target State:**
- 100% test pass rate with meaningful payloads
- Full authentication working across all endpoints
- Async processing for long-running operations (VPR, CV Tailoring)
- Standardized DAL architecture
- Complete JSA alignment with enhanced prompts

---

## Table of Contents

1. [Research Findings](#1-research-findings)
2. [Remaining 4xx/5xx Error Analysis](#2-remaining-4xx5xx-error-analysis)
3. [Authentication Fix Strategy](#3-authentication-fix-strategy)
4. [Workflow-Based Payload Design](#4-workflow-based-payload-design)
5. [Async Processing Architecture](#5-async-processing-architecture)
6. [Handler→DAL Separation Plan](#6-handlerjdal-separation-plan)
7. [JSA Capability Alignment](#7-jsa-capability-alignment)
8. [Implementation Roadmap](#8-implementation-roadmap)
9. [Questions for User](#9-questions-for-user)

---

## 1. Research Findings

### 1.1 Stage 1: Test Results Analysis ✅

**Source:** Automated analysis of `test_results_final.log`

**Error Distribution:**
| Status Code | Count | Endpoints |
|-------------|-------|-----------|
| 400 (Bad Request) | 4 | CV Tailoring, Cover Letter, Interview Prep |
| 401 (Unauthorized) | 8 | VPR (3), Cover Letter (2), Interview Prep (1), Company Research (1), Jobs GET (1) |
| 404 (Not Found) | 5 | Health, Users/me (2), Users CVs, Jobs list |
| 500 (Internal Server) | 1 | Gap Analysis responses (fixed in REFACTOR1) |
| 503 (Service Unavailable) | 2 | Company Research (external dependency) |

**Key Patterns:**
1. **Authentication failures (401)** - 8 endpoints lack proper JWT middleware
2. **Missing endpoints (404)** - 5 user/job management endpoints not deployed
3. **Validation errors (400)** - Pydantic `extra='forbid'` rejecting valid workflow fields
4. **External dependencies (503)** - Company research scraping failures

### 1.2 Stage 2: Authentication System Analysis ✅

**Current Implementation:**

| Handler | Auth Method | Status |
|---------|-------------|--------|
| Auth (login/register) | Direct | ✅ Working |
| CV Upload | X-User-Id header fallback | ✅ Working |
| Gap Analysis | X-User-Id header | ✅ Working |
| VPR | `event['requestContext']['authorizer']['userId']` | ❌ 401 errors |
| Cover Letter | Complex extraction with env var disable | ❌ 401 errors |
| Interview Prep | Requires authorizer context | ❌ 401 errors |

**Root Cause:**
- **Inconsistent authorizer deployment**: Some routes have JWT authorizer configured, others don't
- **Missing middleware**: VPR, Cover Letter, Interview Prep routes lack API Gateway authorizer
- **Fallback mechanisms**: Cover Letter has `AUTHORIZER_DISABLED` env var but still returns 401

**Evidence from Code:**
```python
# vpr_handler.py - Expects authorizer context directly
user_id = event["requestContext"]["authorizer"]["userId"]

# cover_letter_handler.py - Complex extraction with fallbacks
def _extract_authenticated_user_id(event: dict[str, Any]) -> str | None:
    authorizer_user_id = _extract_user_id_from_authorizer(event)
    if authorizer_user_id:
        return authorizer_user_id
    if not _authorizer_disabled():
        return None
    # Fallback to X-User-Id header
```

### 1.3 Stage 3: Workflow & Async Processing Design ✅

**Current State:**
- ❌ All endpoints are **synchronous**
- ❌ No job queue system (SQS)
- ❌ No status polling endpoints
- ❌ VPR generation times out (30-60s exceeds API Gateway 29s limit)

**Planned Architecture** (from `07-vpr-async-architecture.md`):
```
Client → POST /vpr → Submit Lambda → SQS Queue → 202 {job_id}
                          ↓
                     DynamoDB (PENDING)

SQS → Worker Lambda → Claude API → S3 Result
         ↓
    DynamoDB (COMPLETED)

Client → GET /vpr/status/{job_id} → 200 {result_url}
```

**Async Pattern Decision:**
| Operation | Current | Required Pattern | Reason |
|-----------|---------|------------------|--------|
| VPR Generation | Sync (times out) | **ASYNC** (SQS + polling) | 30-60s exceeds 29s limit |
| CV Tailoring | Sync (~20s) | **ASYNC** (recommended) | Approaching timeout, better UX |
| Cover Letter | Sync (~15s) | SYNC or ASYNC | Could remain sync if <20s |
| Gap Analysis | Sync (~10s) | SYNC | Well within limits |
| Interview Prep | Sync (~15s) | SYNC | Well within limits |

### 1.4 Stage 4: Handler→DAL Architecture Analysis ✅

**Current DAL Usage:**

| Handler | DAL Used | Assessment |
|---------|----------|------------|
| VPR | `DynamoDalHandler` | ✅ **Good** - Proper abstraction, error handling, observability |
| Gap Analysis | `CVTable` (direct) | ❌ **Poor** - Bypasses DAL layer, thin wrapper |
| CV Tailoring | `CVTable` (direct) | ❌ **Poor** - Same as Gap Analysis |
| Cover Letter | `CVTable` (direct) | ❌ **Poor** - Same as Gap Analysis |
| Interview Prep | Not implemented | ⚠️ **TBD** - Needs implementation |

**DAL Comparison:**

| Feature | DynamoDalHandler | CVTable |
|---------|------------------|---------|
| Error handling | ✅ Try/catch with Result type | ❌ Returns empty dict on error |
| Logging | ✅ AWS Powertools logger | ❌ None |
| Observability | ✅ Tracer decorators | ❌ None |
| Type safety | ✅ Pydantic models | ⚠️ dict[str, Any] |
| Key generation | ✅ Helper methods | ❌ Hardcoded strings |
| Schema support | ✅ Current schema only | ✅ Legacy + current (compatibility) |

**CVTable Purpose (from code):**
```python
"""Compatibility DAL for CV retrieval used by integration tests."""
```
This suggests CVTable was meant as a **temporary compatibility layer**, not production DAL.

### 1.5 Stage 5: JSA Capabilities Alignment ✅

**JSA Alignment Spec Status** (from `05-jsa-skill-alignment.md`):

| Requirement | Priority | Current State | Gap |
|-------------|----------|---------------|-----|
| **VPR-001**: 6-Stage Methodology | P0 | ✅ Implemented (runbook_2 Step 3.1) | 6-stage pipeline with anti-AI detection |
| **CVT-001**: 3-Step Verification | P0 | ✅ Implemented (runbook_2 Step 4.1) | 3-step with ATS >= 8.0 self-correction |
| **CL-001**: Reference Class Priming | P0 | ✅ Implemented (runbook_2 Phase 6) | 3-paragraph scaffolded structure |
| **GA-001**: Contextual Tagging | P0 | ✅ Implemented (runbook_2 Step 5.1) | 10 questions with [CV IMPACT] / [INTERVIEW ONLY] tags |
| **IP-001**: Interview Prep Complete | P1 | ✅ Implemented (runbook_2 Phase 9) | STAR format with 4 categories |
| **QV-001**: Quality Validator | P1 | ✅ Implemented (runbook_2 Step 7.1) | 6-check FVS validation with gates |
| **KB-001**: Knowledge Base | P1 | ✅ Implemented (runbook_2 Phase 8) | DynamoDB user memory system |

**Current vs JSA Feature Map:**

| Feature | Implemented | JSA Enhanced | Gap |
|---------|-------------|--------------|-----|
| CV Upload | ✅ | ✅ | None |
| Job Posting | ✅ | ✅ | None |
| Gap Analysis | ✅ | ✅ Tagged + memory-aware | Auth (401), DAL migration needed |
| VPR Generation | ✅ 6-stage | ✅ Anti-AI + meta-review | Auth (401), async infra needed |
| CV Tailoring | ✅ 3-step | ✅ ATS >= 8.0 self-correction | Validation (400), async infra needed |
| Cover Letter | ✅ Scaffolded | ✅ 3-paragraph structure | Auth (401), validation (400) |
| Interview Prep | ✅ STAR format | ✅ 4 categories | Auth (401), validation (400) |
| Quality Validator | ✅ | ✅ 6-check FVS | Integration with pipeline |
| Knowledge Base | ✅ | ✅ DynamoDB memory | CDK table deployment needed |

**Missing JSA Components:**
1. **Quality Validator Agent** - 6-check validation (fact verification, ATS, anti-AI detection)
2. **Knowledge Base** - DynamoDB user memory (recurring themes, gap responses, differentiators)
3. **Enhanced Prompts** - All prompts need JSA methodology updates

### 1.6 Completed Work from execution_runbook_2 (2026-02-18)

The following items were fully implemented during the REFACTOR1 execution runbook cycle and are no longer in scope for REFACTOR2:

| Item | Runbook Step | Evidence |
|------|-------------|----------|
| CV Summarizer | Step 2.1 | 40%+ token reduction, unit tests passing |
| LLM Cache (DynamoDB TTL) | Step 2.2 | Cache hit/miss working, TTL verified |
| Bedrock → Anthropic API migration | Step 2.2b | No bedrock-runtime in logs |
| Circuit Breaker | Step 2.3 | Opens after 5 failures, half-open recovery |
| VPR 6-Stage Pipeline | Step 3.1 | All 6 stages with typed interfaces |
| CV Tailoring 3-Step | Step 4.1 | ATS >= 8.0, max 3 iterations |
| Gap Analysis 10Q + Tagging | Step 5.1 | [CV IMPACT] / [INTERVIEW ONLY] tags |
| Cover Letter Scaffold | Phase 6 | 3-paragraph structure with word counts |
| FVS Validator (6 checks) | Step 7.1 | Grammar>=9, Tone>=8, Anti-AI>=9, ATS>=8 |
| Knowledge Base | Phase 8 | DynamoDB memory, recurring themes |
| Interview Prep (STAR) | Phase 9 | 10-15 questions, 4 categories |
| API Route Mapping (27 ops) | Steps 10.0-10.12 | All 27 OpenAPI routes in CDK |
| Storage Contract Lock | Step 10.0d | Logical-to-physical key mapping |
| Data Storage Adapter | Step 10.0e | ApiStorageAdapter with unit tests |
| Legacy Route Decommission Gate | Step 10.0c | No `/api/*` decorators remain |

**Remaining REFACTOR2 Scope (Phase 1 + 2 only):**
1. JWT Authorizer deployment (fixes 8 × 401 errors)
2. Missing endpoint handlers (fixes 5 × 404 errors)
3. Pydantic validation fixes (fixes 3 × 400 errors)
4. DAL migration: CVTable → DynamoDalHandler
5. Async processing infrastructure (SQS, Worker Lambdas, DLQ, S3)
6. CDK infrastructure deployment (tables, buckets, queues)

---

## 2. Remaining 4xx/5xx Error Analysis

### 2.1 Priority Classification

**P0 (Blocking Production):**
1. ~~POST /gap-analysis/responses (500)~~ ✅ **FIXED in REFACTOR1**
2. POST /vpr/generate (401) - 3 occurrences
3. GET /cover-letter/{id} (401)
4. GET /interview-prep/{id} (401)

**P1 (High - Missing Features):**
5. GET /users/me (404) - Endpoint not deployed
6. PUT /users/me (404) - Endpoint not deployed
7. GET /users/me/cvs (404) - Endpoint not deployed
8. GET /jobs (404) - Endpoint not deployed

**P2 (Medium - Validation):**
9. POST /cv-tailoring/generate (400) - `extra='forbid'` rejecting job_description
10. POST /cover-letter/generate (400) - Validation failed
11. POST /interview-prep/generate (400) - Validation failed

**P3 (Low - External):**
12. POST /company-research/fetch (503) - External service unavailable

### 2.2 Error Details & Root Causes

#### Error Group 1: Authentication Failures (401)

**Affected Endpoints:**
- POST /vpr/generate
- GET /vpr/{vprId}
- GET /users/me/vprs
- GET /cover-letter/{coverLetterId}
- GET /users/me/cover-letters
- GET /interview-prep/{interviewPrepId}
- GET /company-research/{jobId}
- GET /jobs/{jobId}

**Root Cause:**
API Gateway routes missing JWT authorizer configuration. Tests provide valid JWT tokens (via conftest.py), but handlers expect `event['requestContext']['authorizer']` which is `None`.

**Evidence:**
```json
// Test provides:
{
  "headers": {
    "Authorization": "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}

// Handler expects:
{
  "requestContext": {
    "authorizer": {
      "userId": "7a7f6307-3562-4ebc-b209-5f19559b048f"
    }
  }
}

// Actual (without authorizer):
{
  "requestContext": {
    "authorizer": null  // ← Missing!
  }
}
```

#### Error Group 2: Missing Endpoints (404)

**Affected Endpoints:**
- GET /users/me
- PUT /users/me
- GET /users/me/cvs
- GET /jobs

**Root Cause:**
Routes not configured in `infra/careervp/api_construct.py`. Only POST /users/me/cv exists, other user endpoints missing.

#### Error Group 3: Pydantic Validation (400)

**Affected Endpoints:**
- POST /cv-tailoring/generate
- POST /cover-letter/generate
- POST /interview-prep/generate

**Root Cause:**
`ConfigDict(extra='forbid')` in `api_models.py` rejects any fields not explicitly defined in schema. Tests send workflow-based payloads (e.g., `job_description`) but models don't accept them.

**Example Error:**
```json
{
  "code": "VALIDATION_ERROR",
  "message": "OpenAPI payload validation failed: 1 validation error for CVTailoringRequest\njob_description\n  Extra inputs are not permitted [type=extra_forbidden]"
}
```

**Current Model:**
```python
class CVTailoringRequest(APIModel):
    cv_id: str = Field(min_length=1)
    job_id: str | None = None
    vpr_id: str | None = None
    # job_description NOT ALLOWED due to extra='forbid'
```

---

## 3. Authentication Fix Strategy

### 3.1 Root Cause Diagnosis

**Issue:** JWT authorizer not deployed for protected routes

**Current State:**
```python
# infra/careervp/api_construct.py
route_map = [
    # These routes HAVE NO AUTHORIZER:
    ("/vpr/generate", "POST", self.vpr_api_func),
    ("/cover-letter/generate", "POST", self.cover_letter_api_func),
    ("/interview-prep/generate", "POST", self.interview_prep_api_func),
]
```

### 3.2 Solution: Deploy JWT Authorizer

**CDK Implementation:**

```python
# infra/careervp/api_construct.py

# 1. Create JWT authorizer
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_apigatewayv2_authorizers as authorizers

jwt_authorizer = authorizers.HttpJwtAuthorizer(
    "CareerVpJwtAuthorizer",
    jwt_audience=["careervp-api"],
    jwt_issuer=f"https://cognito-idp.{self.region}.amazonaws.com/{user_pool_id}",
)

# 2. Apply to protected routes
protected_routes = [
    ("/vpr/generate", "POST"),
    ("/vpr/{vprId}", "GET"),
    ("/users/me/vprs", "GET"),
    ("/cover-letter/generate", "POST"),
    ("/cover-letter/{coverLetterId}", "GET"),
    ("/users/me/cover-letters", "GET"),
    ("/interview-prep/generate", "POST"),
    ("/interview-prep/{interviewPrepId}", "GET"),
    ("/company-research/{jobId}", "GET"),
    ("/jobs/{jobId}", "GET"),
]

for path, method in protected_routes:
    route = self.http_api.add_routes(
        path=path,
        methods=[getattr(apigwv2.HttpMethod, method)],
        integration=integration,
        authorizer=jwt_authorizer,  # ← Add JWT authorizer
    )
```

**Alternative: Lambda Authorizer** (if JWT authorizer not suitable):

```python
# Create Lambda authorizer function
auth_lambda = _lambda.Function(
    self, "ApiAuthorizer",
    runtime=_lambda.Runtime.PYTHON_3_13,
    handler="auth_handler.authorize",
    code=_lambda.Code.from_asset("src/backend/careervp/handlers"),
)

# Create authorizer
lambda_authorizer = authorizers.HttpLambdaAuthorizer(
    "LambdaAuthorizer",
    handler=auth_lambda,
    response_types=[authorizers.HttpLambdaResponseType.SIMPLE],
)
```

**Handler Auth Extraction (standardize):**

```python
# src/backend/careervp/handlers/auth_utils.py

def extract_user_id(event: dict[str, Any]) -> str | None:
    """Extract user_id from JWT authorizer context (standardized)."""
    try:
        # Try JWT authorizer context first
        authorizer = event.get("requestContext", {}).get("authorizer", {})

        # HTTP API v2 format
        if "jwt" in authorizer:
            claims = authorizer["jwt"].get("claims", {})
            return claims.get("sub") or claims.get("user_id")

        # Lambda authorizer format
        if "principalId" in authorizer:
            return authorizer["principalId"]

        # Fallback for dev/test (X-User-Id header)
        if os.getenv("AUTHORIZER_DISABLED") == "true":
            headers = event.get("headers", {})
            return headers.get("x-user-id") or headers.get("X-User-Id")

        return None
    except Exception as exc:
        logger.warning("Failed to extract user_id", error=str(exc))
        return None
```

### 3.3 Acceptance Criteria

- [ ] All protected endpoints return 200/201/202 with valid JWT token
- [ ] Unauthorized requests (no token) return 401 with clear error message
- [ ] Test suite updated with proper auth headers for protected endpoints
- [ ] Auth middleware consistent across all handlers

---

## 4. Workflow-Based Payload Design

### 4.1 Current Problem

**Workflow Gap:** Endpoints expect all data in single request, but real workflow requires chaining:

```
Current (broken):
POST /cv-tailoring/generate
{
  "cv_id": "...",
  "job_description": "..."  // ← Rejected by extra='forbid'
}

Expected Workflow:
1. POST /jobs { "job_description": "..." } → job_id
2. POST /vpr/generate { "job_id": "..." } → vpr_id
3. POST /cv-tailoring/generate { "cv_id": "...", "job_id": "...", "vpr_id": "..." }
```

### 4.2 Solution: Two-Flow API Design

**Support both legacy (single request) and workflow (chained) patterns:**

#### API Models Update:

```python
# src/backend/careervp/models/api_models.py

class CVTailoringRequest(APIModel):
    """CV Tailoring request - supports both legacy and workflow patterns."""

    cv_id: str = Field(min_length=1, description="User's CV ID")

    # Workflow pattern (new)
    job_id: str | None = Field(None, description="Job ID (workflow pattern)")
    vpr_id: str | None = Field(None, description="VPR ID (workflow pattern)")

    # Legacy pattern (backward compatible)
    job_description: str | None = Field(None, min_length=1, description="Job description (legacy pattern)")

    @model_validator(mode='after')
    def validate_flow(self) -> 'CVTailoringRequest':
        """Ensure either workflow OR legacy pattern is used."""
        workflow = bool(self.job_id and self.vpr_id)
        legacy = bool(self.job_description)

        if not (workflow or legacy):
            raise ValueError("Must provide either (job_id + vpr_id) or job_description")

        return self
```

**Handler Logic:**

```python
# src/backend/careervp/handlers/cv_tailoring_handler.py

def generate_tailored_cv(request: CVTailoringRequest, user_id: str) -> Result:
    """Generate tailored CV using workflow or legacy pattern."""

    # Detect which flow
    using_workflow = bool(request.job_id and request.vpr_id)

    if using_workflow:
        # Fetch job_description from job_id
        job = dal.get_job(user_id, request.job_id)
        if not job:
            return Result(success=False, error="Job not found", code=ResultCode.INVALID_INPUT)

        job_description = job.get("job_description")

        # Fetch VPR from vpr_id
        vpr_result = dal.get_vpr(request.vpr_id)
        if not vpr_result.success or not vpr_result.data:
            return Result(success=False, error="VPR not found", code=ResultCode.INVALID_INPUT)

        vpr = vpr_result.data
    else:
        # Legacy flow: use job_description directly
        job_description = request.job_description
        vpr = None  # No VPR in legacy mode

    # Proceed with CV tailoring
    return cv_tailoring_logic.tailor_cv(
        cv_id=request.cv_id,
        job_description=job_description,
        vpr=vpr,
    )
```

### 4.3 Workflow State Tracking

**DynamoDB Job Workflow Table:**

```python
# Table: careervp-workflows-table-dev
{
    "pk": "user#{user_id}",
    "sk": "workflow#{workflow_id}",
    "workflow_type": "job_application",
    "status": "in_progress",  // pending, in_progress, completed
    "steps": {
        "cv_upload": {"status": "completed", "cv_id": "..."},
        "job_create": {"status": "completed", "job_id": "..."},
        "vpr_generate": {"status": "pending", "vpr_id": null},
        "gap_analysis": {"status": "not_started"},
        "cv_tailoring": {"status": "not_started"},
        "cover_letter": {"status": "not_started"},
    },
    "created_at": "2026-02-20T10:00:00Z",
    "updated_at": "2026-02-20T10:05:00Z",
}
```

**Benefits:**
- Frontend knows which steps are complete
- Backend can validate workflow state before processing
- Users can resume interrupted workflows

---

## 5. Async Processing Architecture

### 5.1 Implementation Strategy

**Based on `07-vpr-async-architecture.md` spec:**

#### Phase 1: VPR Async (P0 - Blocking)

**Problem:** VPR generation takes 30-60s, exceeds API Gateway 29s timeout

**Solution:** SQS + Polling Pattern

```
POST /vpr/generate → Submit Lambda → SQS → 202 {job_id}
                         ↓
                    DynamoDB (PENDING)

SQS → Worker Lambda → Claude Sonnet 4.5 (30-60s) → S3
         ↓
    DynamoDB (COMPLETED)

GET /vpr/status/{job_id} → 200 {status, result_url}
```

**New Resources:**
- SQS Queue: `careervp-vpr-jobs-queue-dev`
- SQS DLQ: `careervp-vpr-jobs-dlq-dev`
- DynamoDB: `careervp-jobs-table-dev` (job status tracking)
- S3 Bucket: `careervp-dev-vpr-results-{hash}` (VPR storage)
- Lambda: `vpr-submit-lambda`, `vpr-worker-lambda`, `vpr-status-lambda`

**Cost:** ~$0.0013 per VPR (77x under $0.10 budget)

#### Phase 2: CV Tailoring Async (P1 - Recommended)

**Rationale:** CV Tailoring with 3-step JSA methodology may exceed 20s

**Same Pattern:**
```
POST /cv-tailoring/generate → 202 {job_id}
GET /cv-tailoring/status/{job_id} → 200 {result_url}
```

**Reuse Infrastructure:**
- Same SQS queue (with message filtering)
- Same jobs table (different job_type)
- Same pattern (submit → worker → status)

### 5.2 API Contract

**Submit Job (202 Accepted):**
```json
// POST /vpr/generate
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PENDING",
  "message": "VPR generation job submitted successfully"
}
```

**Poll Status (202 Processing):**
```json
// GET /vpr/status/{job_id}
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PROCESSING",
  "created_at": "2026-02-20T10:00:00Z",
  "started_at": "2026-02-20T10:00:05Z"
}
```

**Completed (200 OK):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "completed_at": "2026-02-20T10:01:10Z",
  "result_url": "https://s3.presigned.url/results/550e8400.json?expires=3600",
  "token_usage": {
    "input_tokens": 7500,
    "output_tokens": 2200
  }
}
```

### 5.3 Frontend Polling Component

**React Example:**
```typescript
function useAsyncJob(jobId: string, pollInterval = 5000) {
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [result, setResult] = useState<any | null>(null);

  useEffect(() => {
    const poll = async () => {
      const response = await fetch(`/api/vpr/status/${jobId}`);
      const data = await response.json();
      setStatus(data);

      if (data.status === 'COMPLETED') {
        // Fetch result from presigned URL
        const resultResponse = await fetch(data.result_url);
        setResult(await resultResponse.json());
      } else if (data.status === 'PENDING' || data.status === 'PROCESSING') {
        setTimeout(poll, pollInterval);
      }
    };

    poll();
  }, [jobId]);

  return { status, result };
}
```

---

## 6. Handler→DAL Separation Plan

### 6.1 Current Architecture Problems

**Problem 1: Inconsistent DAL Usage**
- VPR uses `DynamoDalHandler` ✅
- Gap Analysis uses `CVTable` ❌
- CV Tailoring uses `CVTable` ❌
- Cover Letter uses `CVTable` ❌

**Problem 2: Poor Error Handling**
```python
# CVTable.get_item() - Returns empty dict on error
try:
    return cast(dict[str, Any], self.table.get_item(Key=key))
except (BotoCoreError, ClientError):
    return {}  # ← Silent failure!
```

**Problem 3: No Observability**
- CVTable has no logging
- No tracing
- No metrics

### 6.2 Target Architecture

**Standardize on DynamoDalHandler pattern:**

```
Handler → DAL → DynamoDB
  ↓        ↓
Logger   Error Handling
Tracer   Result<T>
Metrics  Type Safety
```

**Migration Path:**

| Handler | Current DAL | Target DAL | Priority |
|---------|-------------|------------|----------|
| VPR | DynamoDalHandler | ✅ Already good | - |
| Gap Analysis | CVTable | `DynamoDalHandler.save_gap_analysis()` | P0 |
| CV Tailoring | CVTable | `DynamoDalHandler.save_tailored_cv()` | P0 |
| Cover Letter | CVTable | `DynamoDalHandler.save_cover_letter()` | P1 |
| Interview Prep | None | `DynamoDalHandler.save_interview_prep()` | P1 |

### 6.3 Enhanced DynamoDalHandler

**Add missing methods:**

```python
# src/backend/careervp/dal/dynamo_dal_handler.py

class DynamoDalHandler(DalHandler):
    """Unified DAL for all artifacts with proper error handling."""

    # Existing methods (keep as-is)
    def save_cv(self, user_cv: UserCV) -> None: ...
    def get_cv(self, user_id: str) -> UserCV | None: ...
    def save_vpr(self, vpr: VPR) -> Result[None]: ...
    def get_vpr(self, application_id: str, version: int) -> Result[VPR | None]: ...

    # NEW: Gap Analysis methods
    @tracer.capture_method
    def save_gap_analysis(self, user_id: str, job_id: str, gap: GapAnalysis) -> Result[None]:
        """Save gap analysis questions with proper error handling."""
        try:
            table = self._get_db_handler(self.table_name)
            item = gap.model_dump(mode='json')
            item['pk'] = user_id
            item['sk'] = self._build_gap_analysis_sort_key(gap.cv_id, job_id)
            item['artifactId'] = gap.artifact_id  # Required PK
            item['ttl'] = self._ttl_timestamp(ttl_days=90)
            table.put_item(Item=item)
            logger.info("Gap analysis saved", artifact_id=gap.artifact_id)
            return Result(success=True, code=ResultCode.SUCCESS)
        except (ClientError, ValidationError) as exc:
            logger.exception("Failed to save gap analysis")
            return Result(success=False, error=str(exc), code=ResultCode.DYNAMODB_ERROR)

    @tracer.capture_method
    def get_gap_analysis(self, user_id: str, job_id: str) -> Result[GapAnalysis | None]:
        """Retrieve gap analysis by user and job."""
        try:
            table = self._get_db_handler(self.table_name)
            response = table.query(
                KeyConditionExpression=Key('pk').eq(user_id) &
                                      Key('sk').begins_with(f'ARTIFACT#GAP_ANALYSIS#{job_id}'),
                ScanIndexForward=False,  # Latest first
                Limit=1
            )
            items = response.get('Items', [])
            if not items:
                return Result(success=True, data=None, code=ResultCode.SUCCESS)

            gap = GapAnalysis.model_validate(items[0])
            return Result(success=True, data=gap, code=ResultCode.SUCCESS)
        except (ClientError, ValidationError) as exc:
            logger.exception("Failed to get gap analysis")
            return Result(success=False, error=str(exc), code=ResultCode.DYNAMODB_ERROR)

    # NEW: Tailored CV methods
    @tracer.capture_method
    def save_tailored_cv(self, user_id: str, tailored_cv: TailoredCV) -> Result[None]:
        """Save tailored CV artifact."""
        # Similar pattern to save_gap_analysis
        ...

    # NEW: Cover Letter methods
    @tracer.capture_method
    def save_cover_letter(self, user_id: str, cover_letter: CoverLetter) -> Result[None]:
        """Save cover letter artifact."""
        # Similar pattern
        ...
```

**Deprecate CVTable:**

```python
# src/backend/careervp/dal/cv_dal.py

@deprecated("Use DynamoDalHandler instead")
class CVTable:
    """DEPRECATED: Compatibility layer for legacy integration tests.

    This class will be removed in REFACTOR3.
    All new code should use DynamoDalHandler.
    """
    ...
```

### 6.4 Handler Migration Example

**Before (Gap Analysis):**
```python
# gap_handler.py
from careervp.dal.cv_dal import CVTable

table = CVTable()
table.put_item(Item={
    'pk': user_id,
    'sk': f'GAP_ANALYSIS#{job_id}',
    # ... missing artifactId, no error handling
})
```

**After (Gap Analysis):**
```python
# gap_handler.py
from careervp.dal.dynamo_dal_handler import DynamoDalHandler

dal = DynamoDalHandler(table_name=os.environ['DYNAMODB_TABLE_NAME'])
result = dal.save_gap_analysis(user_id, job_id, gap_analysis)

if not result.success:
    return _build_error_response(result.error, HTTPStatus.INTERNAL_SERVER_ERROR)
```

---

## 7. JSA Capability Alignment

### 7.1 Priority P0 Requirements (Blocking)

**Source:** `05-jsa-skill-alignment.md`

#### Requirement VPR-001: 6-Stage Methodology

**Current:** Direct output prompt
**Target:** Staged thinking with self-correction

**6 Stages:**
1. **Strategic Alignment** - Map priorities & role criteria
2. **Candidate Analysis** - Career narrative + differentiators
3. **Alignment Matrix** - Complete mapping table
4. **Meta-Review** - Self-correction & refinement
5. **Structured Report** - Full VPR output
6. **20% Enhancement** - "Make it 20% more persuasive"

**File:** `src/backend/careervp/logic/prompts/vpr_prompt.py`

**Anti-AI Detection Rules:**
```python
BANNED_WORDS = [
    'leverage', 'delve into', 'landscape', 'robust', 'streamline',
    'utilize', 'facilitate', 'implement', 'cutting-edge'
]
```

#### Requirement CVT-001: 3-Step Verification

**Current:** Utility-based tailoring
**Target:** Analysis → Verification → Final output

**3 Steps:**
1. **Draft CV** - Extract 12-18 keywords, tailor content
2. **Self-Verify** - ATS score (1-10), missing keywords, hiring manager check
3. **Final Output** - Revised CV with ATS ≥ 8

**New Parameters:**
- `company_keywords: list[str]` (from company research)
- `vpr_differentiators: list[str]` (top 3 from VPR)

**ATS Formatting Rules:**
- Standard headers only
- Simple bullets (•)
- No tables/columns
- 1-2 pages max

#### Requirement CL-001: Reference Class Priming

**Current:** Missing
**Target:** Scaffolded 3-paragraph structure

**Structure:**
- **Paragraph 1 (Hook):** 80-100 words, UVP + company reference
- **Paragraph 2 (Proof):** 120-140 words, 3 requirements × (Claim + Proof)
- **Paragraph 3 (Close):** 60-80 words, CTA + time-saver positioning

#### Requirement GA-001: Contextual Tagging

**Current:** Basic 3-5 questions
**Target:** Max 10 questions with tags

**Question Format:**
```markdown
### Question {N}
**Requirement:** [Quote from job posting]
**Question:** [Targeted question emphasizing quantification]
**Destination:** [CV IMPACT] or [INTERVIEW/MVP ONLY]
**Strategic Intent:** [Why asking this]
**Evidence Gap:** [What's missing from CV]
**Priority:** CRITICAL | IMPORTANT | OPTIONAL
```

**Memory Awareness:**
- `recurring_themes` parameter to skip previously answered topics
- Knowledge base integration

### 7.2 Priority P1 Requirements (High)

#### Requirement IP-001: Interview Prep Complete

**Current:** Handler exists, no implementation
**Target:** 10-15 STAR-formatted questions + guidance

**Categories:**
1. Technical Competency
2. Behavioral/Cultural Fit
3. Experience & Background
4. Problem-Solving

**Output:**
- Predicted questions (10-15)
- STAR responses (Situation, Task, Action, Result)
- Questions to ask interviewer (5-7)
- Salary guidance (optional)
- Pre-interview checklist

#### Requirement QV-001: Quality Validator

**Current:** Missing
**Target:** 6-check validation agent

**Checks:**
1. Fact Verification - Cross-reference against source
2. ATS Compatibility - Keyword score
3. Anti-AI Detection - Banned words check
4. Cross-Document Consistency - CV/VPR/Cover Letter alignment
5. Completeness - Word counts, section counts
6. Language Quality - Spelling, grammar, tone

**Integration:** Final step in VPR generation flow

#### Requirement KB-001: Knowledge Base

**Current:** Missing
**Target:** DynamoDB user memory system

**Table:** `careervp-knowledge-base-dev`
- PK: `userEmail`
- SK: `knowledgeType`
- TTL: 365 days

**Knowledge Types:**
- `recurring_themes` - Topics to skip in gap analysis
- `gap_responses` - Previous answers
- `differentiators` - VPR-identified strengths
- `applications_count` - Track submissions

---

## 8. Implementation Roadmap

### 8.1 Phase 1: Critical Fixes (Week 1)

**Goal:** Fix all 4xx/5xx errors, achieve 100% test pass rate

**Tasks:**
1. ✅ **Deploy JWT Authorizer**
   - Add authorizer to API Gateway routes
   - Update handler auth extraction logic
   - Test all protected endpoints
   - **Success Metric:** 0 authentication failures (401)

2. ✅ **Deploy Missing Endpoints**
   - Implement GET /users/me handler
   - Implement PUT /users/me handler
   - Implement GET /users/me/cvs handler
   - Implement GET /jobs handler
   - Add routes to CDK
   - **Success Metric:** 0 missing endpoints (404)

3. ✅ **Fix Pydantic Validation**
   - Update CVTailoringRequest to support workflow pattern
   - Update CoverLetterRequest to support workflow pattern
   - Update InterviewPrepRequest to support workflow pattern
   - Add model validators for flow detection
   - **Success Metric:** 0 validation errors (400)

4. ✅ **Migrate to DynamoDalHandler**
   - Add gap_analysis methods to DynamoDalHandler
   - Add tailored_cv methods to DynamoDalHandler
   - Update gap_handler to use new DAL
   - Update cv_tailoring_handler to use new DAL
   - **Success Metric:** All handlers use DynamoDalHandler

**Exit Criteria:**
- [ ] All 32 tests passing (100% pass rate)
- [ ] 0 authentication failures
- [ ] 0 missing endpoints
- [ ] 0 validation errors
- [ ] Standardized DAL usage

### 8.2 Phase 2: Async Processing (Week 2-3)

**Goal:** Implement async pattern for VPR and CV Tailoring

**Tasks:**
1. ✅ **VPR Async Infrastructure**
   - Deploy SQS queue + DLQ
   - Deploy jobs table with GSI
   - Deploy S3 results bucket
   - Deploy worker Lambda
   - Deploy status Lambda
   - Add status endpoint route
   - **Success Metric:** Infrastructure deployed, no errors

2. ✅ **VPR Async Handlers**
   - Refactor vpr_handler → vpr_submit_handler (202 response)
   - Implement vpr_worker_handler (SQS consumer)
   - Implement vpr_status_handler (job status retrieval)
   - Add idempotency logic
   - **Success Metric:** VPR generation works end-to-end via async

3. ✅ **Frontend Polling**
   - Create useAsyncJob React hook
   - Update VPR submission UI
   - Implement polling with 5s intervals
   - Add status indicators (PENDING, PROCESSING, COMPLETED)
   - Handle timeout (5 min max)
   - **Success Metric:** Frontend can poll and retrieve VPR result

4. ⚠️ **CV Tailoring Async** (Optional)
   - Reuse VPR async infrastructure
   - Implement cv_tailoring_worker_handler
   - Update tests
   - **Success Metric:** CV Tailoring async working

**Exit Criteria:**
- [ ] VPR no longer times out (100% success rate)
- [ ] Job status retrievable via API
- [ ] Frontend polling working
- [ ] Cost per VPR < $0.01

### 8.3 Phase 3: JSA Alignment - P0 ✅ COMPLETED (execution_runbook_2)

**Goal:** Implement critical JSA requirements
**Status:** ✅ ALL TASKS COMPLETED via execution_runbook_2 (2026-02-18)

**Tasks:**
1. ✅ **VPR 6-Stage Methodology**
   - Update vpr_prompt.py with 6 stages
   - Add meta-review questions
   - Add "20% improvement" step
   - Update VPR response model
   - Test for banned words
   - **Success Metric:** VPR output follows 6-stage structure

2. ✅ **CV Tailoring 3-Step Verification**
   - Update cv_tailoring_prompt.py with 3 steps
   - Add ATS score calculation
   - Add keyword extraction
   - Add self-correction loop
   - **Success Metric:** ATS score ≥ 8 consistently

3. ✅ **Cover Letter Scaffolded Structure**
   - Update cover_letter_prompt.py with reference class
   - Add 3-paragraph structure
   - Add word count constraints
   - **Success Metric:** Cover letters follow structure

4. ✅ **Gap Analysis Contextual Tagging**
   - Update gap_analysis_prompt.py with tags
   - Add [CV IMPACT] / [INTERVIEW ONLY] logic
   - Increase max questions to 10
   - Add priority levels
   - **Success Metric:** Questions have proper tags

**Exit Criteria:**
- [ ] All P0 JSA requirements implemented
- [ ] Anti-AI detection working
- [ ] Prompts pass test assertions
- [ ] Output quality improved (subjective review)

### 8.4 Phase 4: JSA Alignment - P1 ✅ COMPLETED (execution_runbook_2)

**Goal:** Complete JSA alignment with P1 features
**Status:** ✅ ALL TASKS COMPLETED via execution_runbook_2 (2026-02-18)

**Tasks:**
1. ✅ **Interview Prep Implementation**
   - Implement interview_prep.py logic
   - Update interview_prep_handler.py
   - Create STAR-formatted responses
   - Add 4 question categories
   - Add questions to ask interviewer
   - **Success Metric:** Interview prep generates 10-15 questions

2. ✅ **Quality Validator**
   - Implement quality_validator.py
   - Add 6 validation checks
   - Integrate with VPR flow
   - **Success Metric:** VPR passes all 6 checks

3. ✅ **Knowledge Base**
   - Deploy careervp-knowledge-base-dev table
   - Implement knowledge_base_repository.py
   - Add recurring_themes tracking
   - Integrate with gap analysis
   - **Success Metric:** Gap analysis skips recurring themes

**Exit Criteria:**
- [ ] All P1 JSA requirements implemented
- [ ] Interview prep working end-to-end
- [ ] Quality validator running
- [ ] Knowledge base storing/retrieving data

### 8.5 Timeline Summary

| Phase | Duration | Status | Dependencies |
|-------|----------|--------|--------------|
| Phase 1: Critical Fixes | 1 week | ⏳ Pending | None |
| Phase 2: Async Processing | 2-3 weeks | ⏳ Pending | Phase 1 |
| Phase 3: JSA P0 | 2 weeks | ✅ COMPLETED (runbook_2) | - |
| Phase 4: JSA P1 | 2 weeks | ✅ COMPLETED (runbook_2) | - |
| **Total Remaining** | **3-4 weeks** | | Phase 1 + 2 only |

**Parallel Work Opportunities:**
- Phase 1 tasks can run in parallel (different team members)
- Phase 3 + 4 can overlap (prompt work independent of infrastructure)

---

## 9. Questions for User

### 9.1 Priority & Scope

**Q1: Should we implement ALL phases or prioritize specific ones?**
- Option A: Implement all 4 phases sequentially (7-8 weeks)
- Option B: Phase 1 only (critical fixes, 1 week)
- Option C: Phase 1 + 2 (fixes + async, 3-4 weeks)
- Option D: Custom selection (specify phases)

**Q2: What is the urgency for JSA alignment (Phases 3-4)?**
- Is JSA alignment blocking any business/product milestones?
- Can JSA work happen in parallel with async implementation?

### 9.2 Authentication

**Q3: Which authentication method should we use?**
- Option A: JWT Authorizer (AWS Cognito/third-party JWT issuer)
- Option B: Lambda Authorizer (custom auth logic)
- Option C: API Key (simpler, less secure)

**Q4: Do you have an existing JWT issuer (Cognito, Auth0, etc.)?**
- If yes, provide issuer URL and audience
- If no, should we deploy Cognito as part of this work?

### 9.3 Async Processing

**Q5: Should CV Tailoring also be async (Phase 2 Task 4)?**
- Current: CV Tailoring takes ~20s (approaching timeout)
- With JSA 3-step methodology, may exceed 30s
- Recommendation: Make async now to future-proof

**Q6: What is acceptable polling interval for frontend?**
- Current plan: 5 seconds
- Alternative: 10 seconds (reduce API calls)
- Alternative: 3 seconds (faster UX)

### 9.4 Missing Endpoints

**Q7: Are the missing user/job endpoints still needed?**
- GET /users/me
- PUT /users/me
- GET /users/me/cvs
- GET /jobs

**Rationale:** Tests expect these but they're not deployed. Should we implement or remove tests?

### 9.5 Workflow Design

**Q8: Should we enforce workflow order strictly?**
- Option A: Strict (must create job → VPR → CV tailoring in order)
- Option B: Flexible (allow any order, support both legacy + workflow patterns)
- Current plan: Option B (backward compatible)

**Q9: Should we implement workflow state tracking?**
- Proposed: `careervp-workflows-table-dev` to track multi-step workflows
- Benefits: Frontend knows what's completed, can resume interrupted flows
- Alternative: No workflow table, rely on individual artifact queries

### 9.6 DAL Architecture

**Q10: Can we deprecate CVTable immediately?**
- Proposed: Migrate all handlers to DynamoDalHandler, deprecate CVTable
- Risk: CVTable may be used in integration tests or other code
- Alternative: Keep CVTable for compatibility, add deprecation warning

### 9.7 JSA Prompts

**Q11: Do you have access to example outputs from JSA-aligned prompts?**
- If yes, can you provide samples for VPR, CV Tailoring, Cover Letter?
- This would help validate our implementation matches JSA quality

**Q12: Should we implement Knowledge Base (KB-001) in Phase 4?**
- Knowledge Base requires significant infrastructure (new DynamoDB table)
- Alternative: Defer to REFACTOR3 or future phases
- Impact: Without KB, gap analysis can't skip recurring themes

### 9.8 Testing & Validation

**Q13: What is your preferred test validation approach?**
- Option A: Automated tests only (fast, but may miss quality issues)
- Option B: Automated + manual review of generated content (slower, higher quality)
- Option C: Automated + A/B testing with real users

**Q14: Should we create new test files for workflow patterns?**
- Current tests use legacy pattern (single request with all data)
- New workflow tests would use chained requests (job → VPR → CV tailoring)

### 9.9 Deployment & Rollout

**Q15: What is your deployment risk tolerance?**
- Option A: Big bang (deploy all changes at once)
- Option B: Gradual rollout (10% → 50% → 100% traffic)
- Option C: Blue/green deployment (run old + new in parallel)

**Q16: Do you have a staging environment?**
- If yes, all changes will deploy to staging first for validation
- If no, should we create one as part of this work?

---

## Appendix A: File Changes Summary

### A.1 Infrastructure (CDK)

| File | Change Type | Description |
|------|-------------|-------------|
| `infra/careervp/api_construct.py` | Modify | Add JWT authorizer, new routes |
| `infra/careervp/api_db_construct.py` | Modify | Add jobs table, knowledge base table |
| `infra/careervp/sqs_construct.py` | Create | SQS queue + DLQ for async jobs |
| `infra/careervp/s3_construct.py` | Create | S3 bucket for VPR results |

### A.2 Backend Handlers

| File | Change Type | Description |
|------|-------------|-------------|
| `src/backend/careervp/handlers/vpr_handler.py` | Rename/Modify | → vpr_submit_handler.py, return 202 |
| `src/backend/careervp/handlers/vpr_worker_handler.py` | Create | SQS worker for VPR generation |
| `src/backend/careervp/handlers/vpr_status_handler.py` | Create | Job status endpoint |
| `src/backend/careervp/handlers/gap_handler.py` | Modify | Use DynamoDalHandler |
| `src/backend/careervp/handlers/cv_tailoring_handler.py` | Modify | Use DynamoDalHandler, workflow support |
| `src/backend/careervp/handlers/cover_letter_handler.py` | Modify | Use DynamoDalHandler, workflow support |
| `src/backend/careervp/handlers/interview_prep_handler.py` | Modify | Complete implementation |
| `src/backend/careervp/handlers/user_handler.py` | Create | GET/PUT /users/me endpoints |
| `src/backend/careervp/handlers/job_handler.py` | Modify | Add GET /jobs endpoint |
| `src/backend/careervp/handlers/auth_utils.py` | Create | Standardized auth extraction |

### A.3 DAL Layer

| File | Change Type | Description |
|------|-------------|-------------|
| `src/backend/careervp/dal/dynamo_dal_handler.py` | Modify | Add gap_analysis, tailored_cv, cover_letter methods |
| `src/backend/careervp/dal/cv_dal.py` | Modify | Add @deprecated decorator to CVTable |
| `src/backend/careervp/dal/knowledge_base_repository.py` | Create | Knowledge base CRUD operations |

### A.4 API Models

| File | Change Type | Description |
|------|-------------|-------------|
| `src/backend/careervp/models/api_models.py` | Modify | Update request models to support workflow pattern |
| `src/backend/careervp/models/job.py` | Modify | Add job status, workflow tracking |

### A.5 Prompts (JSA Alignment)

| File | Change Type | Description |
|------|-------------|-------------|
| `src/backend/careervp/logic/prompts/vpr_prompt.py` | Modify | Add 6-stage methodology |
| `src/backend/careervp/logic/prompts/cv_tailoring_prompt.py` | Modify | Add 3-step verification |
| `src/backend/careervp/logic/prompts/cover_letter_prompt.py` | Modify | Add scaffolded structure |
| `src/backend/careervp/logic/prompts/gap_analysis_prompt.py` | Modify | Add contextual tagging |
| `src/backend/careervp/logic/prompts/interview_prep_prompt.py` | Create | STAR-formatted responses |

### A.6 Logic Layer

| File | Change Type | Description |
|------|-------------|-------------|
| `src/backend/careervp/logic/interview_prep.py` | Create | Interview prep generation logic |
| `src/backend/careervp/logic/quality_validator.py` | Create | 6-check validation agent |
| `src/backend/careervp/logic/knowledge_base.py` | Create | Knowledge base operations |

### A.7 Tests

| File | Change Type | Description |
|------|-------------|-------------|
| `docs/refactor/live_tests/test_01_auth_health.py` | Modify | Update auth assertions |
| `docs/refactor/live_tests/test_02_users.py` | Modify | Test new user endpoints |
| `docs/refactor/live_tests/test_03_jobs.py` | Modify | Test GET /jobs |
| `docs/refactor/live_tests/test_04_vpr.py` | Modify | Test async VPR flow |
| `docs/refactor/live_tests/test_06_cv_tailoring.py` | Modify | Test workflow pattern |
| `docs/refactor/live_tests/test_07_cover_letter.py` | Modify | Test workflow pattern |
| `docs/refactor/live_tests/test_08_interview_prep.py` | Modify | Test complete implementation |
| `tests/jsa_skill_alignment/` | Create | JSA alignment test suite |

---

## Appendix B: Cost Estimate

### B.1 Infrastructure Costs (Monthly)

| Resource | Usage | Cost/Month |
|----------|-------|------------|
| **SQS Queue** | 100 VPRs/day × 30 days | $0.024 |
| **DynamoDB Jobs Table** | 100 writes + 500 reads/day | $0.40 |
| **DynamoDB Knowledge Base** | 50 writes + 200 reads/day | $0.20 |
| **S3 Storage** | 100 VPRs × 50KB × 7 days retention | $0.01 |
| **Lambda (VPR Worker)** | 100 VPRs × 60s × 1024MB | $3.75 |
| **Lambda (Other)** | Minimal | $0.50 |
| **API Gateway** | 10,000 requests | $0.10 |
| **CloudWatch Logs** | 10GB/month | $5.03 |
| **Total** | | **~$10/month** |

### B.2 Per-Operation Costs

| Operation | Cost |
|-----------|------|
| VPR Generation (async) | $0.0013 |
| CV Tailoring | $0.0005 |
| Cover Letter | $0.0003 |
| Gap Analysis | $0.0002 |
| Interview Prep | $0.0003 |

**Assumptions:**
- 100 VPRs/day = 3,000/month
- Claude API costs NOT included (billed separately)

---

## Appendix C: Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **JWT authorizer misconfiguration** | HIGH | MEDIUM | Test thoroughly in staging, rollback plan |
| **Async polling timeout (>5 min)** | MEDIUM | LOW | CloudWatch alarms, increase worker concurrency |
| **DynamoDB migration breaks existing data** | HIGH | LOW | Test migration script, backup before deploy |
| **JSA prompts reduce output quality** | MEDIUM | MEDIUM | A/B test old vs new prompts, manual review |
| **CVTable deprecation breaks integration tests** | LOW | MEDIUM | Comprehensive test suite, gradual migration |
| **Cost overrun from SQS/Lambda** | MEDIUM | LOW | Reserved concurrency limits, cost alarms |
| **Frontend polling overloads API** | LOW | LOW | API Gateway throttling, rate limiting |

---

**END OF REFACTOR2 PLAN**

**Next Steps:**
1. User reviews plan and answers questions (Section 9)
2. User approves scope and phases
3. Create implementation tickets in project management system
4. Assign team members to phases
5. Begin Phase 1 implementation

**Document Version:** 1.1
**Last Updated:** 2026-02-20
**Change Log:** v1.1 - Updated to reflect completed JSA work from execution_runbook_2 (Phases 3-4 complete, remaining scope is Phase 1-2 only)
**Maintained By:** Engineering Team
