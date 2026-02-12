# Phase 0 Tasks: Security Foundation

**Objective:** Fix critical security issues before proceeding with refactoring
**Duration:** 8 hours (1 day)
**Owner:** Infra + Backend

---

## Task 0.1: Add API Authorizer

**Effort:** 4 hours
**Priority:** P0 (Blocking)
**Files Modified:** `infra/careervp/api_construct.py`

### Steps

1. **Review current API construct**
   ```bash
   cat /Users/yitzchak/Documents/dev/careervp/infra/careervp/api_construct.py | head -100
   ```

2. **Add JWT/Cognito authorizer configuration**
   ```python
   # Add to api_construct.py
   from aws_cdk import (
       Duration,
       Aws,
       Stack,
       aws_apigateway as apigw,
       aws_cognito as cognito,
   )

   class APIConstruct(Stack):
       def __init__(self, scope: Construct, id: str, **kwargs):
           super().__init__(scope, id, **kwargs)

           # Create Cognito User Pool
           user_pool = cognito.UserPool(
               self, "CareerVPUserPool",
               user_pool_name="careervp-user-pool",
               sign_in_aliases=cognito.SignInAliases(email=True),
               auto_verify=cognito.AutoVerifiedAttrs(email=True),
           )

           # Create authorizer
           authorizer = apigw.CognitoUserPoolsAuthorizer(
               self, "CareerVPApiAuthorizer",
               cognito_user_pools=[user_pool]
           )
   ```

3. **Apply authorizer to all routes**
   ```python
   # Apply to each route
   api.add_route(
       path="/api/vpr/submit",
       methods=["POST"],
       handler=vpr_submit_lambda,
       authorizer=authorizer
   )
   ```

4. **Synthesize and validate**
   ```bash
   cd infra
   uv run cdk synth --no-lookup
   ```

### Validation

- [ ] CDK synth succeeds
- [ ] Authorizer attached to all routes
- [ ] No public endpoints remain

---

## Task 0.2: Fix Exception Leakage

**Effort:** 2 hours
**Priority:** P0 (Blocking)
**Files Modified:** `cv_tailoring_handler.py`

### Current Issue

```python
# BEFORE (vulnerable)
return {
    "statusCode": 500,
    "body": json.dumps({"error": str(exc)})  # Leaks internal details
}
```

### Fix

```python
# AFTER (safe)
import logging
logger = logging.getLogger(__name__)

def safe_handler(event, context):
    try:
        # ... original logic
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid request"})}
    except Exception as e:
        logger.error(f"Internal error: {type(e).__name__}", exc_info=True)
        return {"statusCode": 500, "body": json.dumps({"error": "Internal server error"})}
```

### Validation

- [ ] No `str(exc)` in 500 responses
- [ ] Errors logged with full context
- [ ] User-facing errors are generic

---

## Task 0.3: Add Input Validation

**Effort:** 2 hours
**Priority:** P1 (High)
**Files Modified:** `cv_tailoring_handler.py`

### Requirements

1. **Validate cv_id format** (UUID or alphanumeric)
2. **Validate job_description length** (max 20,000 chars)
3. **Validate language code** (en, he, fr)

### Implementation

```python
from pydantic import BaseModel, validator
from typing import Literal

class CVTailoringRequest(BaseModel):
    cv_id: str
    job_description: str
    language: Literal["en", "he", "fr"] = "en"

    @validator("cv_id")
    def validate_cv_id(cls, v):
        if not re.match(r"^[a-zA-Z0-9-]+$", v):
            raise ValueError("Invalid cv_id format")
        return v

    @validator("job_description")
    def validate_job_description(cls, v):
        if len(v) > 20000:
            raise ValueError("Job description too long (max 20,000 characters)")
        return v

def lambda_handler(event, context):
    try:
        body = json.loads(event["body"])
        request = CVTailoringRequest(**body)
    except ValidationError as e:
        return {"statusCode": 400, "body": json.dumps({"error": e.errors()})}
```

### Validation

- [ ] Pydantic model validates all inputs
- [ ] Invalid inputs return 400 with error details
- [ ] No SQL injection or injection vectors

---

## Phase 0 Exit Criteria

- [ ] API authorizer configured for all endpoints
- [ ] No raw exceptions in API responses
- [ ] Input validation on CV Tailoring endpoint
- [ ] CDK synth succeeds
- [ ] Security scan passes

---

## Rollback Plan

If issues arise with the API authorizer:
1. Keep authorizer configuration commented out
2. Deploy without authorizer to dev only
3. Test thoroughly before production
4. Uncomment when ready

---

## Testing

```bash
# Test CV Tailoring endpoint
curl -X POST https://api_endpoint/api/cv-tailoring \
  -H "Content-Type: application/json" \
  -d '{"cv_id":"test-123","job_description":"..."}'

# Verify 400 for invalid input
# Verify 401 for missing auth
# Verify 500 only for server errors (no stack traces)
```
