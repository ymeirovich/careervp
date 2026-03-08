# Live Test Results Analysis & Remediation Plan

## Executive Summary

Analysis of `live-test-results6.log` reveals multiple issues with non-2xx responses. The primary causes are **route mismatches** (wrong endpoint paths in tests), **missing routes** (gap-analysis not implemented), and **missing health check** (Lambda).

---

## Issue 1: Status 403 - Route Mismatch (CRITICAL)

### Root Cause
The test calls use incorrect endpoint paths. API Gateway returns 403 Forbidden for non-existent routes.

| Test Call | Should Be | Status |
|-----------|-----------|--------|
| `GET /users/me/cvs` | `GET /users/me/cv` | Route doesn't exist |
| `GET /users/me/vprs` | `GET /vprs` | Route doesn't exist |
| `GET /users/me/tailored-cvs` | `GET /cv-tailorings` | Route doesn't exist |
| `GET /users/me/cover-letters` | `GET /cover-letters` | Route doesn't exist |
| `POST /company-research/fetch` | Not applicable | Route doesn't exist |
| `POST /gap-analysis/*` | NOT IMPLEMENTED | Gap analysis routes not defined |

### Fix
Update test endpoint paths to match actual API routes defined in `infra/careervp/api_construct.py`.

---

## Issue 2: Status 404 - User Profile Not Found

### Root Cause
When a new user registers via Cognito, no user profile is created in DynamoDB. The endpoint `/users/me` returns 404 because there's no profile record.

### Evidence from Test Log
```
GET /users/me - Status 404
Response: {"error": "User profile not found"}
```

### Fix Approach
**Option A: Auto-create user profile on first auth**
- Modify the auth flow to create a user profile in DynamoDB upon first successful login
- This ensures `/users/me` returns 200 with default/empty profile

**Option B: Return empty profile instead of 404**
- Modify `/users/me` handler to return 200 with empty/default profile structure
- This is a simpler fix but may not meet all business requirements

**Recommended: Option A** - Create user profile during registration/login

### Files to Modify
1. `src/backend/careervp/logic/auth_service.py` - Add profile creation
2. OR `src/backend/careervp/handlers/user_handler.py` - Add profile auto-creation

---

## Issue 3: Status 502 - Internal Server Errors

### Root Cause
Lambda functions are throwing unhandled exceptions when processing requests.

| Endpoint | Possible Cause |
|----------|----------------|
| `POST /cover-letter/generate` | Missing CV, S3/DynamoDB access, or logic error |
| `POST /interview-prep/generate` | Missing CV, S3/DynamoDB access, or logic error |
| `GET /company-research/{id}` | No data yet for job ID |

### Fix Approach
1. Add try/catch blocks in handlers to return proper error responses
2. Ensure environment variables are correctly set:
   - `TABLE_NAME` / `DYNAMODB_TABLE_NAME`
   - `S3_BUCKET_NAME`
   - Claude API key
3. Add prerequisite validation (e.g., check CV exists before generating cover letter)

---

## Issue 4: Health Check - Missing Lambda Health

### Root Cause
The `/health` endpoint only checks Anthropic and DynamoDB, not Lambda function health.

### Current Response
```json
{
  "status": "degraded",
  "services": {
    "anthropic": "degraded",
    "dynamodb": "degraded"
  }
}
```

### Expected Response (per test contract)
```json
{
  "status": "degraded",
  "services": {
    "lambda": "healthy",
    "dynamodb": "healthy",
    "anthropic": "healthy"
  }
}
```

### Fix
Add Lambda health check to `src/backend/careervp/handlers/health_handler.py`:

```python
# Add after DynamoDB check:
# Check Lambda (verify function is reachable)
try:
    lambda_client = boto3.client('lambda', region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
    # Simple invocation check - call a lightweight endpoint
    lambda_client.invoke(
        FunctionName=os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'careervp-health-api-lambda-dev'),
        InvocationType='RequestResponse',
        Payload='{}'
    )
    services['lambda'] = 'healthy'
except Exception:
    services['lambda'] = 'degraded'
```

---

## Issue 5: Gap Analysis Routes Not Implemented

### Root Cause
The test calls `/gap-analysis/*` endpoints but these routes are not defined in the API Gateway.

### Fix
Either:
1. **Implement gap-analysis API** - Add the endpoints to `api_construct.py`
2. **Remove gap-analysis tests** - If feature is not planned for V1

---

## Summary of Required Changes

| Priority | Issue | Action | Files |
|----------|-------|--------|-------|
| P1 | User Profile 404 | Auto-create user profile on auth | `auth_service.py` or `user_handler.py` |
| P1 | Health Check Lambda | Add Lambda health check | `health_handler.py` |
| P2 | Route Mismatches | Fix test endpoint paths | Test files |
| P2 | Gap Analysis | Implement or remove | `api_construct.py` |
| P3 | 502 Errors | Add error handling | Handler files |

---

## Test Execution After Fixes

After implementing fixes, re-run the live tests:
```bash
cd docs/refactor/live_tests
python run_all_tests.py
```

Expected improvements:
- User endpoints return 200/201 (profile auto-created)
- Health check returns 200 with all 3 services
- Route tests pass with correct paths
- Gap analysis: implemented or gracefully skipped
