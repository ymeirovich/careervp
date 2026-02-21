# CareerVP Execution Runbook 4.0 - REFACTOR2 (Security Hardened)

**Document Version:** 4.0
**Date:** 2026-02-21
**Purpose:** Complete implementation of REFACTOR2 with all security fixes applied
**Prerequisite:** execution_runbook_2.md completed (JSA features, API route mapping, quality gaps)
**Security Status:** All audit findings addressed

---

## Implementation Order

1. **Phase 0: Security Pre-Requisites FIRST** (MERGE-BLOCKING) - Dependencies, JWT config, auth bypass removal
2. **Phase 1: Critical Fixes SECOND** (Phase 1) - Auth, missing endpoints, validation, DAL migration, CORS, bugs
3. **Phase 2: Async Processing THIRD** (Phase 2) - SQS, worker Lambdas, status polling
4. **Phase 4: CDK Infrastructure FOURTH** (Phase 3) - New tables, buckets, queues, authorizer
5. **Phase 5: Live Tests FIFTH** (Phase 4) - E2E validation against deployed API
6. **Phase 6: CI Security SIXTH** - Guardrails

---

## Current Status

| Phase | Status | Scope |
|-------|--------|-------|
| Phase 0 | ⏳ PENDING | Security pre-reqs (7 items) - MERGE BLOCKING |
| Phase 1 | ⏳ PENDING | Auth fixes, missing endpoints, validation, DAL migration, CORS, bugs |
| Phase 2 | ⏳ PENDING | VPR async (SQS+worker), CV Tailoring async, status polling |
| Phase 3 | ⏳ PENDING | CDK: JWT authorizer, SQS queue+DLQ, jobs table, S3 bucket, worker Lambda |
| Phase 4 | ⏳ PENDING | Live tests: 27-endpoint contract gate, async flow, quality gates |
| Phase 5 | ⏳ PENDING | CI security guardrails |

---

## Specs

| Type | File | Purpose |
|------|------|---------|
| API Contract | `docs/refactor2/specs/api_contract_spec.yaml` | All 27 endpoints with status and required fixes |
| Async Processing | `docs/refactor2/specs/async_processing_spec.yaml` | SQS + polling pattern, worker Lambda, job states |
| DAL Migration | `docs/refactor2/specs/dal_migration_spec.yaml` | CVTable → DynamoDalHandler migration plan |
| JSA Alignment | `docs/refactor2/specs/jsa_alignment_spec.yaml` | JSA requirements (all marked complete) |
| Auth | `docs/refactor2/specs/auth_spec.yaml` | JWT authorizer deployment, auth extraction |
| Prompt Optimization | `docs/best_practices/yaml/prompt_optimization_spec.yaml` | Step prompt validation criteria |
| CDK Rules | `docs/best_practices/yaml/prompt_optimization_cdk_spec.yaml` | CDK infrastructure validation rules |
| Code Quality | `docs/best_practices/yaml/code_quality_security_spec.yaml` | Security and code quality rules |
| OpenAPI | `docs/swagger/careervp-api-v1.yaml` | 27-operation API contract (source of truth) |
| Security Audit | `docs/audit/security_bug_audit.md` | All security findings |
| Security Action Plan | `docs/audit/SECURITY_ACTION_PLAN.md` | 32 remediation items |
| Automation Scripts | `docs/refactor2/scripts/` | Executable scripts for all bash steps |

---

# PART 0: SECURITY PRE-REQUISITES (MERGE-BLOCKING)

## Phase 0.1: Dependency Security Upgrades

**Duration:** 0.5 day | **Effort:** 2 hours
**Status:** ⏳ PENDING
**Priority:** IMMEDIATE

### Step 0.1.1: Upgrade cryptography dependency (F-003)

**Script:**
```bash
bash docs/refactor2/scripts/step_0.1.1_upgrade_cryptography.sh
```

**Manual Instructions (if script fails):**
```bash
# Fix F-003 (cryptography CVE)
cd src/backend
sed -i 's/cryptography==46.0.3/cryptography>=46.0.5/' pyproject.toml
uv lock
uv export --no-hashes -o lambda_requirements.txt
uvx pip-audit -r lambda_requirements.txt  # Verify 0 vulnerabilities
```

### Step 0.1.2: Upgrade Node/CDK dependencies (F-004)

**Script:**
```bash
bash docs/refactor2/scripts/step_0.1.2_upgrade_nodejs.sh
```

**Manual Instructions (if script fails):**
```bash
cd ../../
npm update aws-cdk-lib cdk-monitoring-constructs
npm audit --omit=dev --audit-level=high  # Verify 0 high/critical
cd infra && npx cdk synth  # Verify synthesis still works
```

---

## Phase 0.2: JWT Configuration Fix (F-002)

**Duration:** 0.5 day | **Effort:** 2 hours
**Status:** ⏳ PENDING
**Priority:** CRITICAL

### Step 0.2.1: Fix JWT Environment Variables in CDK

**Script:**
```bash
#!/bin/bash
# Step 0.2.1: Fix JWT Environment Variables in CDK
# File: infra/careervp/api_construct.py

API_CONSTRUCT="infra/careervp/api_construct.py"

echo "=== Step 0.2.1: Fix JWT Environment Variables in CDK ==="

# Check if file exists
if [ ! -f "$API_CONSTRUCT" ]; then
    echo "ERROR: $API_CONSTRUCT not found"
    exit 1
fi

# Remove old JWT_SECRET and JWT_ALGORITHM lines
echo "Removing old JWT_SECRET and JWT_ALGORITHM..."
sed -i '/"JWT_SECRET": "dev-placeholder-secret",/d' "$API_CONSTRUCT"
sed -i '/"JWT_ALGORITHM": "HS256",/d' "$API_CONSTRUCT"

# Add new SSM-backed JWT_PRIVATE_KEY and JWT_PUBLIC_KEY
# Find the line with JWT_COOKIE_NAME or similar to insert after
if grep -q '"JWT_COOKIE_NAME"' "$API_CONSTRUCT"; then
    echo "Adding JWT_PRIVATE_KEY and JWT_PUBLIC_KEY..."
    sed -i '/"JWT_COOKIE_NAME"/a\        "JWT_PRIVATE_KEY": ssm.StringParameter.value_from_lookup(\n            self, f"\/{env}\/jwt-private-key"\n        ),\n        "JWT_PUBLIC_KEY": ssm.StringParameter.value_from_lookup(\n            self, f"\/{env}\/jwt-public-key"\n        ),' "$API_CONSTRUCT"
else
    echo "WARNING: Could not find insertion point for JWT keys"
    echo "Manual intervention required"
fi

# Verify changes
echo "Verifying changes..."
if grep -q "JWT_PRIVATE_KEY" "$API_CONSTRUCT" && grep -q "JWT_PUBLIC_KEY" "$API_CONSTRUCT"; then
    echo "SUCCESS: JWT keys added"
else
    echo "ERROR: JWT keys not found after modification"
    exit 1
fi

if grep -q "JWT_SECRET" "$API_CONSTRUCT" || grep -q "JWT_ALGORITHM" "$API_CONSTRUCT"; then
    echo "ERROR: Old JWT keys still present"
    exit 1
else
    echo "SUCCESS: Old JWT keys removed"
fi

echo "=== Step 0.2.1 Complete ==="
```

**Manual Instructions (if script fails):**

File: `infra/careervp/api_construct.py`

REMOVE these lines:
```python
"JWT_SECRET": "dev-placeholder-secret",
"JWT_ALGORITHM": "HS256",
```

ADD these lines (SSM-backed):
```python
"JWT_PRIVATE_KEY": ssm.StringParameter.value_from_lookup(
    self, f"/{env}/jwt-private-key"
),
"JWT_PUBLIC_KEY": ssm.StringParameter.value_from_lookup(
    self, f"/{env}/jwt-public-key"
),
```

### Step 0.2.2: Fix JWT Key Handling in Auth Service

**File:** `src/backend/careervp/logic/auth_service.py`

CHANGE this:
```python
private_key, public_key = _generate_ephemeral_rsa_keys()
```

TO this:
```python
if os.getenv('ENV') != 'local':
    raise ConfigurationError(
        "JWT_PRIVATE_KEY and JWT_PUBLIC_KEY must be set in production"
    )
# Only generate ephemeral keys in local dev
private_key, public_key = _generate_ephemeral_rsa_keys()
```

---

## Phase 0.3: Remove AUTHORIZER_DISABLED (Finding 4)

**Duration:** 0.5 day | **Effort:** 1 hour
**Status:** ⏳ PENDING
**Priority:** CRITICAL

### Step 0.3.1: Remove ALL AUTHORIZER_DISABLED Checks

**Script:**
```bash
bash docs/refactor2/scripts/step_0.3.1_remove_authorizer_disabled.sh
```

**Manual Instructions (if script fails):**
```bash
# Search and destroy
grep -r "AUTHORIZER_DISABLED" src/backend/careervp/handlers/

# Delete these functions from 4 handlers:
# - cv_tailoring_handler.py:363
# - cover_letter_handler.py:196
# - interview_prep_handler.py:157
# - company_research_handler.py:205

# Verify removal
grep -r "AUTHORIZER_DISABLED" src/backend/careervp/handlers/
# Expected: 0 matches
```

---

## Phase 0.4: Disable Sensitive Event Logging (Finding 9)

**Duration:** 0.25 day | **Effort:** 30 minutes
**Status:** ⏳ PENDING
**Priority:** HIGH

### Step 0.4.1: Change log_event=True to False

**Script:**
```bash
bash docs/refactor2/scripts/step_0.4.1_disable_log_event.sh
```

**Manual Instructions (if script fails):**
```bash
# Find all log_event=True
grep -n "log_event.*True" src/backend/careervp/handlers/

# Change to log_event=False in these handlers:
# - vpr_handler.py:28
# - vpr_submit_handler.py:170
# - vpr_status_handler.py:253
# - vpr_worker_handler.py:213
```

---

## Phase 0.5: Fix SSRF and Unauthenticated Endpoints (NF-001, NF-002)

**Duration:** 0.5 day | **Effort:** 2 hours
**Status:** ⏳ PENDING
**Priority:** CRITICAL

### Step 0.5.1: Add SSRF Protection to Web Scraper

**File:** `src/backend/careervp/logic/utils/web_scraper.py`

ADD before scrape_url():
```python
import ipaddress
from urllib.parse import urlparse
import socket

def _is_safe_url(url: str) -> bool:
    """Reject internal/private network addresses and non-HTTPS."""
    parsed = urlparse(url)

    # Enforce HTTPS only
    if parsed.scheme != 'https':
        return False

    # Resolve hostname to IP
    try:
        ip = ipaddress.ip_address(socket.gethostbyname(parsed.hostname))
    except:
        return False

    # Reject private/internal ranges
    if ip.is_private or ip.is_loopback or ip.is_link_local:
        return False

    # Reject AWS metadata endpoint
    if str(ip) == '169.254.169.254':
        return False

    return True
```

MODIFY scrape_url() to validate:
```python
async def scrape_url(url: str, ...) -> str:
    if not _is_safe_url(url):
        raise ValueError(f"URL not allowed: {url}")
    # ... rest of function
```

### Step 0.5.2: Add Auth to Company Research POST

**File:** `src/backend/careervp/handlers/company_research_handler.py`

ADD at start of _fetch_company_research():
```python
def _fetch_company_research(event: dict[str, Any], repo: ...) -> dict[str, Any]:
    # ADD THIS:
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        return _build_error_response(401, "UNAUTHORIZED", "Authentication required")

    # ... rest of function
```

---

## Phase 0 Exit Verification

**Script:**
```bash
bash docs/refactor2/scripts/step_0_exit_verification.sh
```

**Manual Instructions (if script fails):**
```bash
# Dependency audit
uvx pip-audit -r lambda_requirements.txt
npm audit --omit=dev --audit-level=high

# Code patterns
grep -r "AUTHORIZER_DISABLED" src/backend/careervp/handlers/
# Expected: 0 matches

grep -r "log_event.*True" src/backend/careervp/handlers/
# Expected: 0 matches
```

**Phase 0 Exit Criteria:**
- [ ] pip-audit reports 0 vulnerabilities
- [ ] npm audit reports 0 high/critical
- [ ] JWT_PRIVATE_KEY/JWT_PUBLIC_KEY in infra env vars
- [ ] No AUTHORIZER_DISABLED in handlers
- [ ] No log_event=True in handlers
- [ ] SSRF validation in web_scraper.py
- [ ] Auth check in company_research POST

---

# PART 1: CRITICAL FIXES (Phase 1)

## Phase 1.1: Authentication Fix - JWT Authorizer

**Duration:** 1 day | **Effort:** 6 hours
**Status:** ⏳ PENDING
**Fixes:** 8 endpoints returning 401

### Step 1.1.1: Create Standardized Auth Extraction Utility

**OPTIMIZED PROMPT:**
```python
@spec docs/refactor2/specs/auth_spec.yaml
@pattern src/backend/careervp/handlers/{cover_letter_handler.py,vpr_handler.py}

[Senior Backend Engineer] AWS auth + Python Lambda + Powertools

# PROBLEM
8 endpoints return 401 — handlers use inconsistent auth extraction

# SOLUTION
Create auth_utils.py + auth_middleware.py with centralized auth

# THEN
1. Create auth_utils.py
   - Function: extract_user_id(event) → str | None
   - Priority order:
     a) HTTP API v2 JWT: event.requestContext.authorizer.jwt.claims.sub
     b) Lambda authorizer: event.requestContext.authorizer.principalId
     c) ENV=local ONLY: X-User-Id header (NOT AUTHORIZER_DISABLED)
   - Return None if no valid user_id
   - Log warning on extraction failure

2. Create auth_middleware.py
   - @require_auth decorator
   - Returns 401 JSON if user_id is None

3. Create test_auth_utils.py (6 tests)

# CONSTRAINTS
- DO: Use Powertools logger
- MUST: Return None (not raise) on auth failure

# PROHIBITED
- ❌ AUTHORIZER_DISABLED — NEVER use this pattern
- ❌ payload.get('user_id') — use auth context only
- ❌ ENV!=local with X-User-Id fallback

# OUTPUT
src/backend/careervp/handlers/auth_utils.py
src/backend/careervp/handlers/auth_middleware.py
tests/unit/test_auth_utils.py

# VERIFY
pytest tests/unit/test_auth_utils.py -v
mypy careervp/handlers/auth_utils.py --strict
ruff check careervp/handlers/auth_utils.py
```

### Step 1.1.2: Migrate ALL Handlers to Standardized Auth

**CRITICAL: This step now includes ALL handlers with user_id access**

**HANDLERS TO MIGRATE:**
1. vpr_handler.py
2. cover_letter_handler.py
3. interview_prep_handler.py
4. gap_handler.py
5. cv_tailoring_handler.py
6. job_handler.py
7. **knowledge_base_handler.py** (NEW - was missing, Critical finding)
8. **vpr_submit_handler.py** (NEW - async handler)
9. **vpr_status_handler.py** (NEW - async handler)
10. **user_handler.py** (NEW - new handler)

**VERIFICATION:**
```bash
bash docs/refactor2/scripts/step_1.1.2_auth_migration_verification.sh
```

**Manual Instructions (if script fails):**
```bash
# No payload user_id
grep -r "payload.*user_id\|user_id.*payload" src/backend/careervp/handlers/
# Expected: 0 matches

# No AUTHORIZER_DISABLED
grep -r "AUTHORIZER_DISABLED" src/backend/careervp/handlers/
# Expected: 0 matches

# No direct authorizer extraction
grep -r "requestContext.*authorizer" careervp/handlers/ | grep -v auth_utils.py
# Expected: 0 matches
```

---

## Phase 1.2: Missing Endpoint Handlers

**Duration:** 1 day | **Effort:** 8 hours
**Status:** ⏳ PENDING

### Step 1.2.1: Implement User Management Handlers
### Step 1.2.2: Implement Job List and Health Handlers

*(Same as v3.0 - no security changes needed)*

---

## Phase 1.3: Pydantic Validation Fixes

**Duration:** 0.5 day | **Effort:** 4 hours
**Status:** ⏳ PENDING

*(Same as v3.0)*

---

## Phase 1.4: DAL Migration (CVTable → DynamoDalHandler)

**Duration:** 1 day | **Effort:** 8 hours
**Status:** ⏳ PENDING

*(Same as v3.0)*

---

## Phase 1.5: CORS Hardening (NEW)

**Duration:** 0.5 day | **Effort:** 2 hours
**Status:** ⏳ PENDING
**Priority:** HIGH

### Step 1.5.1: Create CORS Utility

**File:** `src/backend/careervp/handlers/cors_utils.py`

```python
import os

ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '').split(',')

def get_cors_headers(origin: str | None) -> dict[str, str]:
    """Return CORS headers with origin validation."""
    if not origin:
        return {
            'Access-Control-Allow-Origin': ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS else '',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        }

    if origin in ALLOWED_ORIGINS:
        return {
            'Access-Control-Allow-Origin': origin,
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        }

    # Reject origin not in allowlist
    return {}
```

### Step 1.5.2: Update All Handlers to Use CORS Utility

Update all 7 handlers to use `get_cors_headers()` instead of wildcard.

### Step 1.5.3: Add ALLOWED_ORIGINS to CDK

**File:** `infra/careervp/api_construct.py`

ADD environment variable:
```python
"ALLOWED_ORIGINS": "https://careervp.app,https://www.careervp.app"
```

**VERIFICATION:**
```bash
bash docs/refactor2/scripts/step_1.5_cors_verification.sh
```

**Manual Instructions (if script fails):**
```bash
grep -r "Access-Control-Allow-Origin.*\*" src/backend/careervp/handlers/
# Expected: 0 matches
```

---

## Phase 1.6: Critical Bug Fixes (NEW)

**Duration:** 1 day | **Effort:** 6 hours
**Status:** ⏳ PENDING
**Priority:** HIGH

### Step 1.6.1: Fix Empty List Crash (Finding 10)

**File:** `src/backend/careervp/dal/dynamo_dal_handler.py`

ADD before max(items, ...):
```python
if not items:
    return Result(success=True, data=None, code=ResultCode.NOT_FOUND)
```

### Step 1.6.2: Fix Context Attribute Access (Finding 11)

**File:** All handlers with exception logging

CHANGE:
```python
logger.info('Failed', request_id=context.aws_request_id)
```

TO:
```python
logger.info('Failed', request_id=getattr(context, 'aws_request_id', 'unknown'))
```

### Step 1.6.3: Fix Version Parse Failure (Finding 12)

**File:** `src/backend/careervp/dal/dynamo_dal_handler.py`

ADD try/except around int(version):
```python
try:
    version = int(record.get('version', 0))
except (ValueError, TypeError) as e:
    logger.warning("Invalid version: %s", record.get('version'))
    raise InvalidVersionError(f"Invalid version: {e}")
```

### Step 1.6.4: Fix Error Swallowing (Finding 15)

**File:** `src/backend/careervp/handlers/company_research_handler.py`

CHANGE:
```python
try:
    response = table.get_item(Key=key)
except Exception:
    response = {}
```

TO:
```python
try:
    response = table.get_item(Key=key)
except ClientError as e:
    logger.exception("Failed to get item: %s", key)
    raise
```

### Step 1.6.5: Fix Weak Input Validation (Finding 18)

**File:** `src/backend/careervp/handlers/knowledge_base_handler.py`

ADD type validation:
```python
required_gap = {'user_id': str, 'job_id': str, 'cv_id': str}
for field, expected_type in required_gap.items():
    value = payload.get(field)
    if not isinstance(value, expected_type) or not value:
        return 400 response
```

### Step 1.6.6: Fix None Comparison Logic (Finding 20)

**File:** `src/backend/careervp/handlers/user_handler.py`

CHANGE:
```python
if isinstance(payload_user_id, str) and payload_user_id and payload_user_id != user_id:
```

TO:
```python
if not user_id:
    return 401 response
# Always use authenticated user_id
user_id = extract_user_id(event)
```

---

## Phase 1 Exit Verification

**Script:**
```bash
bash docs/refactor2/scripts/step_1_exit_verification.sh
```

**Manual Instructions (if script fails):**
```bash
# All Phase 1 unit tests
uv run pytest tests/unit/ -v --tb=short

# Verify security patterns
grep -r "AUTHORIZER_DISABLED" careervp/handlers/ | grep -v __pycache__
# Expected: 0 matches

grep -r "log_event.*True" careervp/handlers/ | grep -v __pycache__
# Expected: 0 matches

grep -r "payload.*user_id" careervp/handlers/ | grep -v __pycache__
# Expected: 0 matches

grep -r "Access-Control-Allow-Origin.*\*" careervp/handlers/ | grep -v __pycache__
# Expected: 0 matches
```

**Phase 1 Exit Criteria:**
- [ ] All Phase 0 items complete
- [ ] 0 AUTHORIZER_DISABLED in codebase
- [ ] 0 log_event=True in handlers
- [ ] 0 payload.get('user_id') in handlers
- [ ] CORS uses allowlist, not wildcard
- [ ] All critical bugs fixed (Findings 10, 11, 12, 15, 18, 20)
- [ ] knowledge_base_handler has auth (was Finding 1)
- [ ] company_research POST has auth (was NF-002)
- [ ] All unit tests pass

---

# PART 2: ASYNC PROCESSING (Phase 2)

## Phase 2.1: VPR Async Infrastructure

**Duration:** 2 days | **Effort:** 12 hours
**Status:** ⏳ PENDING
**Dependency:** Phase 1 complete

### Step 2.1.1: Create VPR Submit Handler (202 Pattern)
*(Same as v3.0)*

### Step 2.1.2: Create VPR Worker Handler (SQS Consumer)

**UPDATED: Add race condition fix with ConditionExpression**

```python
# When updating status to PROCESSING:
result = table.update_item(
    Key={'job_id': job_id},
    UpdateExpression='SET #status = :new_status, started_at = :started',
    ConditionExpression='#status = :expected_status',  # ADD THIS
    ExpressionAttributeNames={'#status': 'status'},
    ExpressionAttributeValues={
        ':new_status': 'PROCESSING',
        ':expected_status': 'PENDING',  # Only transition from PENDING
        ':started': datetime.now(timezone.utc).isoformat(),
    },
    ReturnValues='ALL_NEW',
)
```

### Step 2.1.3: Create VPR Status Handler (Polling Endpoint)
*(Same as v3.0)*

---

## Phase 2.2: CV Tailoring Async

**Duration:** 1 day | **Effort:** 4 hours
**Status:** ⏳ PENDING

*(Same as v3.0)*

---

# PART 3: CDK INFRASTRUCTURE (Phase 3)

## Phase 3.1: Deploy JWT Authorizer + New Resources

**Duration:** 2 days | **Effort:** 10 hours
**Status:** ⏳ PENDING
**Dependency:** Phase 1 + 2 handlers ready

### Step 3.1.1: Deploy JWT Authorizer to API Gateway
*(Same as v3.0)*

### Step 3.1.2: Deploy Async Processing Infrastructure

**UPDATED: Fix SQS encryption to KMS_MANAGED**

CHANGE:
```python
encryption: sqs.QueueEncryption.SQS_MANAGED
```

TO:
```python
encryption: sqs.QueueEncryption.KMS_MANAGED,
encryption_master_key: kms.Key(self, 'SQSKey',
    enable_key_rotation=True,
    removal_policy=RemovalPolicy.RETAIN,
)
```

### Step 3.1.3: Wire New Lambda Functions to API Gateway Routes
*(Same as v3.0)*

### Step 3.1.4: Address Remaining Checkov Findings (NEW)

ADD to infrastructure:
1. API Gateway access logs: `cloud_watch_role=True`
2. API Gateway X-Ray tracing: `tracing_enabled=True`
3. CloudWatch log group encryption for Lambda functions

---

# PART 4: LIVE TESTS + COMPLETION (Phase 4)

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
- [ ] **SECURITY: pip-audit clean**
- [ ] **SECURITY: npm audit clean**
- [ ] **SECURITY: No AUTHORIZER_DISABLED**
- [ ] **SECURITY: No log_event=True**

### Deploy

**Script:**
```bash
bash docs/refactor2/scripts/step_4.1_deploy.sh
```

**Manual Instructions (if script fails):**
```bash
cd /Users/yitzchak/Documents/dev/careervp/infra

# Deploy to dev
npx cdk deploy --app='python app.py' --require-approval never

# Verify deployment
aws cloudformation describe-stacks --stack-name careervp-dev --region us-east-1 | jq '.Stacks[0].StackStatus'
# Expected: "UPDATE_COMPLETE" or "CREATE_COMPLETE"
```

---

## Phase 4.2: Security Validation Gate (NEW)

**ADD this to Phase 4 - Must Pass 100%**

**Script:**
```bash
bash docs/refactor2/scripts/step_4.2_security_gate.sh
```

**Manual Instructions (if script fails):**
```bash
echo "=== SECURITY VALIDATION GATE ==="

# Test 1: Auth enforcement
curl -sS -o /dev/null -w "%{http_code}" "$API_BASE/users/me"
# Expected: 401 (not 200, not 500)

# Test 2: User ID spoofing blocked
TOKEN=$(curl -sS -X POST "$API_BASE/auth/login" -d '{"email":"attacker@test.com","password":"Pass123!"}' | jq -r '.access_token')
curl -sS -X POST "$API_BASE/vpr/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"user_id":"victim-user-id","cv_id":"test","job_id":"test"}' | jq '.error.code'
# Expected: Uses user_id from token, not payload

# Test 3: CORS validation
curl -sS -H "Origin: https://evil.com" "$API_BASE/health" -I | grep "Access-Control-Allow-Origin"
# Expected: NOT wildcard

# Test 4: SSRF blocked
curl -sS -X POST "$API_BASE/company-research/fetch" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"domain":"http://169.254.169.254/latest/meta-data/"}' | jq '.error'
# Expected: 400 with "URL not allowed"

# Test 5: Dependency audit
cd src/backend && uvx pip-audit -r lambda_requirements.txt
# Expected: Found 0 vulnerabilities

cd ../.. && npm audit --omit=dev --audit-level=high
# Expected: 0 vulnerabilities

# Test 6: No sensitive logging
grep -r "log_event.*True" src/backend/careervp/handlers/
# Expected: 0 matches

grep -r "AUTHORIZER_DISABLED" src/backend/careervp/handlers/
# Expected: 0 matches

echo "=== END SECURITY GATE ==="
```

**Failure = Block deployment until fixed**

---

# PART 5: CI SECURITY GUARDRAILS (Phase 5) (NEW)

## Phase 5.1: Add Security Workflow

**File:** `.github/workflows/security.yml`

```yaml
name: Security Audit
on: [pull_request, push]

jobs:
  python-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Audit Python dependencies
        run: |
          cd src/backend
          uvx pip-audit -r lambda_requirements.txt

  node-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Audit Node dependencies
        run: npm audit --omit=dev --audit-level=high

  iac-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Synthesize CDK
        run: cd infra && npx cdk synth
      - name: Run Checkov
        run: uvx checkov -d infra/cdk.out --framework cloudformation

  code-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Bandit
        run: |
          cd src/backend
          uvx bandit -r careervp/ -ll

  auth-enforcement:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check for auth bypasses
        run: |
          ! grep -r "AUTHORIZER_DISABLED" src/backend/careervp/handlers/
          ! grep -r "payload.*user_id" src/backend/careervp/handlers/
          ! grep -r "log_event.*True" src/backend/careervp/handlers/
          ! grep -r "Access-Control-Allow-Origin.*\*" src/backend/careervp/handlers/
```

---

## Phase 5.2: Add Pre-Commit Hooks

**File:** `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks:
      - id: ruff
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    hooks:
      - id: mypy
        args: ['careervp/', '--strict', '--ignore-missing-imports']

  - repo: local
    hooks:
      - id: security-checks
        name: Security pattern checks
        entry: python scripts/security_gate.py
        language: system
        pass_filenames: false
```

---

# COMPLETION CHECKLIST

## Phase 0: Security Pre-Requisites
- [ ] Step 0.1.1: cryptography upgraded
- [ ] Step 0.1.2: Node/CDK upgraded
- [ ] Step 0.2.1: JWT env vars fixed in CDK
- [ ] Step 0.2.2: JWT key handling fixed in auth service
- [ ] Step 0.3.1: AUTHORIZER_DISABLED removed
- [ ] Step 0.4.1: log_event=True disabled
- [ ] Step 0.5.1: SSRF protection added
- [ ] Step 0.5.2: company_research POST auth added

## Phase 1: Critical Fixes
- [ ] Step 1.1.1: auth_utils.py created
- [ ] Step 1.1.2: All 10 handlers migrated
- [ ] Step 1.2.1: User management handlers created
- [ ] Step 1.2.2: Job list and health handlers created
- [ ] Step 1.3.1: API models updated
- [ ] Step 1.4.1: DynamoDalHandler methods added
- [ ] Step 1.4.2: Handlers migrated to DynamoDalHandler
- [ ] Step 1.5.1: CORS utility created
- [ ] Step 1.5.2: All handlers updated for CORS
- [ ] Step 1.6.1: Empty list crash fixed
- [ ] Step 1.6.2: Context access fixed
- [ ] Step 1.6.3: Version parse fixed
- [ ] Step 1.6.4: Error swallowing fixed
- [ ] Step 1.6.5: Validation fixed
- [ ] Step 1.6.6: None comparison fixed

## Phase 2: Async Processing
- [ ] Step 2.1.1: VPR submit handler created
- [ ] Step 2.1.2: VPR worker with race condition fix
- [ ] Step 2.1.3: VPR status handler created
- [ ] Step 2.2.1: CV Tailoring async (optional)

## Phase 3: CDK Infrastructure
- [ ] Step 3.1.1: JWT authorizer deployed
- [ ] Step 3.1.2: Async infrastructure with KMS SQS
- [ ] Step 3.1.3: Lambda integrations wired
- [ ] Step 3.1.4: Checkov findings addressed

## Phase 4: Live Tests
- [ ] Deploy to dev/staging
- [ ] 27-endpoint contract gate: 27/27 pass
- [ ] Security validation gate: 100% pass
- [ ] Async VPR flow: submit → poll → complete
- [ ] Quality gates: anti-AI, ATS >= 8.0

## Phase 5: CI Security
- [ ] Security workflow added
- [ ] Pre-commit hooks configured

---

## Final Security Metrics

| Metric | Before | After |
|--------|--------|-------|
| Authentication failures (401) | 8 | 0 |
| Missing endpoints (404) | 5 | 0 |
| Validation errors (400) | 3 | 0 |
| AUTHORIZER_DISABLED present | 4 handlers | 0 |
| CORS wildcard | 7 handlers | 0 |
| log_event=True | 4 handlers | 0 |
| Vulnerable dependencies | Yes | 0 |
| SSRF protection | No | Yes |
| Company research auth | No | Yes |

---

**END OF EXECUTION RUNBOOK 4.0**

**Total Steps:** 30+
**Total Phases:** 6
**Estimated Duration:** 4-5 weeks
**Document Version:** 4.0
**Last Updated:** 2026-02-21
**Security Status:** All audit findings addressed
