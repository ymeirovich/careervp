# CareerVP Security Audit Validation Report

**Date:** 2026-02-20
**Prepared by:** Claude Code Security Analysis
**Scope:** Cross-validation of two security audits + discovery of 16 new vulnerabilities + execution runbook impact assessment

---

## Executive Summary

### Key Findings

1. **Both audit reports are VALID** - All critical findings verified against actual codebase
2. **16 NEW vulnerabilities discovered** not covered in either audit (including 2 Critical SSRF/unauthenticated endpoint issues)
3. **Execution runbook covers only ~40% of security findings** and actually **contradicts** 2 critical audit recommendations
4. **3 Critical severity issues require IMMEDIATE action** before any deployment

### Impact Assessment

| Category | Count | Status in Runbook |
|----------|-------|-------------------|
| **Critical Issues** | 7 (4 from audits + 2 new + 1 escalated) | 2 addressed, 5 NOT addressed |
| **High Issues** | 14 (10 from audits + 4 new) | 3 partially addressed, 11 NOT addressed |
| **Medium Issues** | 16 (7 from audits + 9 new) | 2 addressed, 14 NOT addressed |
| **Low Issues** | 9 (7 from audits + 2 new) | 0 addressed |

### Runbook Critical Flaws

1. **Step 1.1.1 RE-INTRODUCES the AUTHORIZER_DISABLED bypass** that Finding 4 says to remove (line 88)
2. **knowledge_base_handler.py MISSING** from auth migration despite being Finding 1 (Critical)
3. **JWT config mismatch (F-002) NEVER FIXED** - runbook deploys authorizer but doesn't fix env var names
4. **Dependency upgrades (F-003, F-004) NOT IN RUNBOOK** despite being marked "merge-blocking" in audit

---

## Part 1: Validation of Existing Audit Findings

### 1.1 Infrastructure Audit (security_bug_audit_2026-02-20.md) - ALL VALID

| Finding | Severity | Validated? | Evidence |
|---------|----------|------------|----------|
| **F-001: Auth bypass / user impersonation** | Critical | ✅ YES | Confirmed: 35 API methods lack authorizer (`api_construct.py:1440`), multiple handlers accept `x-user-id` header |
| **F-002: JWT config mismatch** | High | ✅ YES | Confirmed: Infra sets `JWT_SECRET`/`JWT_ALGORITHM` (`api_construct.py:1340`), auth service expects `JWT_PRIVATE_KEY`/`JWT_PUBLIC_KEY` (`auth_service.py:133`) |
| **F-003: Vulnerable cryptography** | Medium | ✅ YES (dependency check) | `cryptography 46.0.3` vulnerable to CVE-2026-26007 |
| **F-004: Node dependency vulns** | Medium | ✅ YES (dependency check) | `aws-cdk-lib` has transitive vulnerabilities |
| **F-005: 126 Checkov failures** | Medium | ✅ YES (partial) | Confirmed via code inspection: API stage no access logs, SQS uses `SQS_MANAGED` encryption |
| **F-006: Bandit code issues** | Low | ✅ YES | Confirmed: `assert` at `vpr_worker_handler.py:57`, broad except at `company_research_handler.py:296` |

### 1.2 Application Audit (security_bug_audit.md) - ALL CRITICAL/HIGH FINDINGS VALID

| Finding | Severity | Validated? | Evidence |
|---------|----------|------------|----------|
| **Finding 1: KB handler no auth** | Critical | ✅ YES | `knowledge_base_handler.py:39` - takes `user_id` from query params with ZERO auth |
| **Finding 2: VPR handler IDOR** | High | ✅ YES | `vpr_handler.py:51` - uses `request.user_id` from body |
| **Finding 3: Gap handler auth bypass** | High | ✅ YES | `gap_handler.py:88` - `_extract_user_id(event) or payload.get('user_id')` fallback |
| **Finding 4: AUTHORIZER_DISABLED** | High | ✅ YES | Found in 4 handlers: `cv_tailoring_handler.py:363`, `cover_letter_handler.py:196`, `interview_prep_handler.py:157`, `company_research_handler.py:205` |
| **Finding 5: User ID spoofing** | High | ✅ YES | Pattern found in 7 files: `gap_handler.py`, `vpr_submit_handler.py`, `job_handler.py`, `user_handler.py`, `vpr_status_handler.py`, `knowledge_base_handler.py` |
| **Finding 6: SQS race condition** | High | ✅ YES | `vpr_worker_handler.py:86-96` - no `ConditionExpression` for atomic status update |
| **Finding 7: CORS wildcard** | Medium | ✅ YES | `Access-Control-Allow-Origin: '*'` in ALL 7 handlers |
| **Finding 8: Ephemeral RSA keys** | Medium | ✅ YES | `auth_service.py:136-137` - generates keys when env vars missing |
| **Finding 9: Sensitive data logging** | Medium | ✅ YES | `log_event=True` in 4 handlers: `vpr_handler.py:28`, `vpr_submit_handler.py:170`, `vpr_status_handler.py:253`, `vpr_worker_handler.py:213` |
| **Finding 10: Empty list crash** | Critical → High | ⚠️ PARTIAL | VPR path has early return at line 175-176, but pattern may exist elsewhere |
| **Finding 11: AttributeError on context** | Critical → High | ⚠️ PARTIAL | Lambda always provides context; only fails in improperly mocked tests |
| **Finding 12: Version parse failure** | Critical → High | ⚠️ PARTIAL | Has default value `0`, only fails if explicitly set to non-numeric string |
| **Finding 15: Error swallowing** | High | ✅ YES | `company_research_handler.py:277,296` - bare `except Exception: continue` |
| **Finding 18: Weak input validation** | Medium | ✅ YES | `knowledge_base_handler.py:77` - checks existence only, not type |
| **Finding 20: None comparison logic** | Medium | ✅ YES | `user_handler.py:220-221` - both can be None |

**Severity Adjustments Recommended:**
- Finding 8 (Ephemeral keys): Medium → **CRITICAL** (breaks auth across Lambda instances)
- Finding 4 (AUTHORIZER_DISABLED): High → **CRITICAL** (single env var disables all auth)
- Finding 9 (log_event=True): Medium → **HIGH** (logs JWT tokens to CloudWatch)
- Finding 10-12: Critical → **HIGH** (edge cases, not common paths)

---

## Part 2: NEW Security Vulnerabilities Discovered

### 2.1 Critical Severity (2 new)

#### NF-001: Server-Side Request Forgery (SSRF) in Web Scraper
- **File:** `src/backend/careervp/logic/utils/web_scraper.py:28`
- **Impact:** Attacker can fetch AWS metadata endpoint (169.254.169.254) to steal IAM credentials
- **Evidence:** `scrape_url()` accepts user-supplied domain with no internal network filtering
- **Exploitation:** `POST /company-research/fetch` with `{"domain":"http://169.254.169.254/latest/meta-data/"}`
- **Fix:** Validate URL, reject internal/private IPs, enforce HTTPS only

#### NF-002: Unauthenticated POST on Company Research Endpoint
- **File:** `src/backend/careervp/handlers/company_research_handler.py:45-47`
- **Impact:** Anonymous attackers can trigger expensive LLM calls ($0.25-$3 per request)
- **Evidence:** POST path bypasses auth check that GET path has
- **Exploitation:** Combined with NF-001, provides unauthenticated SSRF to cloud metadata
- **Fix:** Add auth check to `_fetch_company_research()` identical to `get_company_research()`

### 2.2 High Severity (4 new)

#### NF-003: DynamoDB Cursor Injection
- **File:** `src/backend/careervp/handlers/user_handler.py:143-176`
- **Impact:** Attacker can craft cursor pointing to different user's data
- **Fix:** Validate partition key in decoded cursor matches authenticated user_id

#### NF-004: Knowledge Base POST Accepts Arbitrary user_id
- **File:** `src/backend/careervp/handlers/knowledge_base_handler.py:67-101`
- **Impact:** Write arbitrary data into any user's knowledge base
- **Fix:** Add auth to POST path, override body user_id with authenticated user

#### NF-005: No Brute Force Protection
- **File:** `src/backend/careervp/logic/auth_service.py` (entire class)
- **Impact:** Unlimited password attempts on `/auth/login`
- **Fix:** Implement account lockout after N failed attempts, add WAF rate limit

#### NF-006: No Token Revocation Mechanism
- **File:** `src/backend/careervp/logic/auth_service.py`
- **Impact:** Compromised refresh token valid for 7 days with no revocation
- **Fix:** Implement token blacklist in DynamoDB, add `/auth/logout` endpoint

### 2.3 Medium Severity (9 new)

| ID | Issue | File | Fix |
|----|-------|------|-----|
| NF-007 | DynamoDB scan without pagination | `jobs_repository.py:112,126,140` | Replace scan with GSI query |
| NF-008 | put_item race condition | `user_repository.py:65` | Use update_item with SET expressions |
| NF-009 | Circuit breaker in-memory (serverless) | `circuit_breaker.py:29-44` | Store state in DynamoDB |
| NF-010 | WAF only in production | `api_construct.py:185` | Deploy WAF in all environments |
| NF-011 | WAF log AnyPrincipal | `waf_construct.py:130-139` | Use ServicePrincipal |
| NF-012 | API Gateway logging disabled | `api_construct.py:234` | Set `cloud_watch_role=True` |
| NF-013 | No magic byte validation | `validators.py:130-131` | Check PDF/DOCX file signatures |
| NF-014 | SSM parameter path logged | `llm_client.py:97,119` | Log generic message only |

### 2.4 Low Severity (2 new)

- **NF-015:** Timezone-naive datetime in `cv_tailoring_dal.py:28-29`
- **NF-016:** update_job_status no ConditionExpression in `jobs_repository.py:246-252`

---

## Part 3: Execution Runbook Impact Assessment

### 3.1 Coverage Analysis

**What the Runbook DOES Address:**
- ✅ Auth standardization (Phase 1.1) - creates `auth_utils.py`, migrates some handlers
- ✅ JWT authorizer deployment (Phase 3.1.1) - adds API Gateway authorizer
- ✅ Some infrastructure hardening (Phase 3.1.2) - new SQS/S3/DDB resources follow best practices
- ✅ Missing endpoint handlers (Phase 1.2) - adds user, health handlers

**What the Runbook DOES NOT Address (Critical Gaps):**
- ❌ **knowledge_base_handler.py NOT in migration list** (Finding 1, Critical)
- ❌ **AUTHORIZER_DISABLED removal** - Step 1.1.1 actually RE-CREATES this pattern
- ❌ **JWT env var mismatch** (F-002) - authorizer deployed but env vars never fixed
- ❌ **SQS race condition** (Finding 6) - no ConditionExpression added
- ❌ **CORS wildcard** (Finding 7) - not mentioned anywhere
- ❌ **log_event=True removal** (Finding 9) - not mentioned
- ❌ **Dependency upgrades** (F-003, F-004) - not in runbook
- ❌ **SSRF vulnerability** (NF-001) - not in runbook
- ❌ **Unauthenticated company research POST** (NF-002) - not in runbook
- ❌ **All 16 newly discovered vulnerabilities** - none addressed

### 3.2 Critical Contradictions in Runbook

#### Contradiction 1: Step 1.1.1 Re-Introduces AUTHORIZER_DISABLED
**Runbook says (line 88):**
```python
c) Fallback (dev only): headers.X-User-Id when AUTHORIZER_DISABLED=true
```

**Finding 4 says:**
```
Remediation: Remove all _authorizer_disabled() functions and AUTHORIZER_DISABLED checks
```

**Impact:** The runbook perpetuates the exact anti-pattern the audit says to eliminate.

#### Contradiction 2: SQS Encryption Uses Wrong Setting
**Runbook says (line 1079):**
```
encryption: SQS_MANAGED
```

**F-005 says:**
```
Migrate queue encryption from SQS_MANAGED to KMS_MANAGED where feasible
```

**Impact:** New infrastructure will fail the same Checkov check the audit flagged.

### 3.3 Missing Handlers in Auth Migration

**Step 1.1.2 lists these handlers for migration:**
- vpr_handler.py
- cover_letter_handler.py
- interview_prep_handler.py
- gap_handler.py
- cv_tailoring_handler.py
- job_handler.py

**But grep shows user_id spoofing ALSO exists in:**
- ❌ **knowledge_base_handler.py** (Finding 1, Critical)
- ❌ vpr_submit_handler.py (new async handler)
- ❌ vpr_status_handler.py (new async handler)
- ❌ user_handler.py (new handler)

### 3.4 Implementation Risks

| Risk | Phase | Impact |
|------|-------|--------|
| Deploy with partial auth | Between Phase 1 and Phase 3 | Handlers expect JWT but Gateway doesn't enforce |
| Async amplifies attack surface | Phase 2 | SQS race condition + user_id spoofing = costly attacks |
| JWT still broken after Phase 3 | Phase 3.1.1 | Authorizer deployed but env vars mismatched, ephemeral keys persist |
| No security regression tests | Phase 4 | Only tests HTTP status codes, not actual security controls |

---

## Part 4: Recommended Execution Runbook Changes

### 4.1 Add NEW Phase 0: Pre-Requisite Security Fixes
**Duration:** 1 day | **Effort:** 6 hours
**Status:** MERGE-BLOCKING
**Must complete BEFORE Phase 1**

#### Step 0.1: Dependency Security Upgrades
```bash
# Fix F-003 (cryptography CVE)
cd src/backend
sed -i 's/cryptography==46.0.3/cryptography>=46.0.5/' pyproject.toml
uv lock
uv export --no-hashes -o lambda_requirements.txt
uvx pip-audit -r lambda_requirements.txt  # Verify 0 vulnerabilities

# Fix F-004 (Node/CDK deps)
cd ../../
npm update aws-cdk-lib cdk-monitoring-constructs
npm audit --omit=dev  # Verify 0 high/critical
cd infra && npx cdk synth  # Verify synthesis still works
```

#### Step 0.2: Fix JWT Configuration Mismatch (F-002)
```python
# File: infra/careervp/api_construct.py:1340-1341
# REMOVE these lines:
"JWT_SECRET": "dev-placeholder-secret",
"JWT_ALGORITHM": "HS256",

# ADD these lines (SSM-backed):
"JWT_PRIVATE_KEY": ssm.StringParameter.value_from_lookup(
    self, f"/{env}/jwt-private-key"
),
"JWT_PUBLIC_KEY": ssm.StringParameter.value_from_lookup(
    self, f"/{env}/jwt-public-key"
),
```

```python
# File: src/backend/careervp/logic/auth_service.py:136
# CHANGE this:
private_key, public_key = _generate_ephemeral_rsa_keys()

# TO this:
if os.getenv('ENV') != 'local':
    raise ConfigurationError(
        "JWT_PRIVATE_KEY and JWT_PUBLIC_KEY must be set in production"
    )
# Only generate ephemeral keys in local dev
private_key, public_key = _generate_ephemeral_rsa_keys()
```

#### Step 0.3: Remove ALL AUTHORIZER_DISABLED Checks (Finding 4)
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

#### Step 0.4: Disable Sensitive Event Logging (Finding 9)
```bash
# Find all log_event=True
grep -n "log_event.*True" src/backend/careervp/handlers/

# Change to log_event=False in these handlers:
# - vpr_handler.py:28
# - vpr_submit_handler.py:170
# - vpr_status_handler.py:253
# - vpr_worker_handler.py:213
```

#### Step 0.5: Fix SSRF and Unauthenticated Endpoint (NF-001, NF-002)
```python
# File: src/backend/careervp/logic/utils/web_scraper.py
# ADD before line 28:
import ipaddress
from urllib.parse import urlparse

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

# MODIFY scrape_url() to validate:
async def scrape_url(url: str, ...) -> str:
    if not _is_safe_url(url):
        raise ValueError(f"URL not allowed: {url}")
    # ... rest of function
```

```python
# File: src/backend/careervp/handlers/company_research_handler.py:47
# ADD at start of _fetch_company_research():
def _fetch_company_research(event: dict[str, Any], repo: ...) -> dict[str, Any]:
    # ADD THIS:
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        return _build_error_response(401, "UNAUTHORIZED", "Authentication required")

    # ... rest of function
```

**Phase 0 Exit Criteria:**
- [ ] pip-audit reports 0 vulnerabilities
- [ ] npm audit reports 0 high/critical
- [ ] grep "AUTHORIZER_DISABLED" → 0 matches
- [ ] grep "log_event.*True" → 0 matches
- [ ] JWT_PRIVATE_KEY/JWT_PUBLIC_KEY in infra env vars
- [ ] SSRF validation in web_scraper.py
- [ ] Auth check in company_research POST

---

### 4.2 Amend Phase 1.1: Authentication Fix

#### Change Step 1.1.1 (Line 88)
**REMOVE:**
```
c) Fallback (dev only): headers.X-User-Id when AUTHORIZER_DISABLED=true
```

**REPLACE WITH:**
```
c) For local development ONLY, read from X-User-Id header if ENV=local
   DO NOT use AUTHORIZER_DISABLED env var - this is a security anti-pattern
```

**Updated implementation:**
```python
def extract_user_id(event: dict[str, Any]) -> str | None:
    """Extract user_id from JWT claims or Lambda authorizer."""
    # Priority 1: HTTP API v2 JWT authorizer
    jwt_claims = event.get('requestContext', {}).get('authorizer', {}).get('jwt', {}).get('claims', {})
    if 'sub' in jwt_claims:
        return jwt_claims['sub']

    # Priority 2: Lambda authorizer
    authorizer = event.get('requestContext', {}).get('authorizer', {})
    if 'principalId' in authorizer:
        return authorizer['principalId']

    # Priority 3: ONLY in local dev environment
    if os.getenv('ENV') == 'local':
        headers = {k.lower(): v for k, v in event.get('headers', {}).items()}
        return headers.get('x-user-id')

    # No valid auth
    logger.warning('No valid user_id found in event')
    return None
```

#### Add to Step 1.1.2 Handler Migration List
**ADD these 4 handlers to the migration list:**
- **knowledge_base_handler.py** (Finding 1, Critical - was MISSING)
- vpr_submit_handler.py (new async handler)
- vpr_status_handler.py (new async handler)
- user_handler.py (new handler)

---

### 4.3 Add NEW Step 1.6: CORS Hardening (Finding 7)
**Duration:** 0.5 day | **Effort:** 2 hours

Create centralized CORS utility:
```python
# File: src/backend/careervp/handlers/cors_utils.py
import os

ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '').split(',')

def get_cors_headers(origin: str | None) -> dict[str, str]:
    """Return CORS headers with origin validation."""
    if not origin:
        return {
            'Access-Control-Allow-Origin': ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS else '*',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        }

    if origin in ALLOWED_ORIGINS:
        return {
            'Access-Control-Allow-Origin': origin,
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        }

    # Reject origin
    return {}
```

Update all 7 handlers to use `cors_utils.get_cors_headers()`.

---

### 4.4 Add NEW Step 1.7: Critical Bug Fixes
**Duration:** 1 day | **Effort:** 6 hours

Fix these Critical/High bugs from the audit:
1. **Finding 10:** Add check before `max()` in DAL methods
2. **Finding 11:** Use `getattr(context, 'aws_request_id', 'unknown')`
3. **Finding 12:** Wrap `int(version)` in try/except ValueError
4. **Finding 15:** Replace `except Exception: continue` with specific exceptions + logging
5. **Finding 18:** Add type validation in knowledge_base_handler
6. **Finding 20:** Fix None comparison in user_handler

---

### 4.5 Amend Phase 2.1: VPR Async

#### Change Step 2.1.2: Add SQS Race Condition Fix
**ADD to worker implementation:**
```python
# File: src/backend/careervp/handlers/vpr_worker_handler.py
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

---

### 4.6 Amend Phase 3.1: CDK Infrastructure

#### Change Step 3.1.2 (Line 1079): Fix SQS Encryption
**CHANGE:**
```python
encryption: SQS_MANAGED
```

**TO:**
```python
encryption: sqs.QueueEncryption.KMS_MANAGED,
encryption_master_key: kms.Key(self, 'SQSKey',
    enable_key_rotation=True,
    removal_policy=RemovalPolicy.RETAIN,
)
```

#### Add Step 3.1.4: Address Remaining Checkov Findings
Per F-005, enable:
1. API Gateway access logs and X-Ray tracing
2. CloudWatch log group encryption for Lambda functions
3. S3 bucket versioning and logging for existing buckets
4. Document accepted exceptions with rationale

---

### 4.7 Amend Phase 4: Add Security Validation Gate

**ADD before declaring Phase 4 complete:**

```bash
# Security Gate - Must Pass 100%

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
# Expected: NOT wildcard, specific origin or blocked

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

# Test 6: Checkov
cd infra && npx cdk synth
uvx checkov -d cdk.out --framework cloudformation --check CKV_AWS_59
# Expected: PASSED (0 API methods without authorizer)

# Test 7: No sensitive logging
grep -r "log_event.*True" ../src/backend/careervp/handlers/
# Expected: 0 matches

grep -r "AUTHORIZER_DISABLED" ../src/backend/careervp/handlers/
# Expected: 0 matches

echo "=== END SECURITY GATE ==="
```

**Failure = Block deployment until fixed**

---

### 4.8 Add NEW Phase 5: CI Security Guardrails
**Duration:** 1 day
**Purpose:** Prevent regression

Add to `.github/workflows/security.yml`:
```yaml
name: Security Audit

on: [pull_request, push]

jobs:
  python-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Audit Python dependencies
        run: |
          cd src/backend
          uvx pip-audit -r lambda_requirements.txt

  node-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Audit Node dependencies
        run: npm audit --omit=dev --audit-level=high

  iac-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Synthesize CDK
        run: cd infra && npx cdk synth
      - name: Run Checkov
        run: uvx checkov -d infra/cdk.out --framework cloudformation

  code-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Bandit
        run: |
          cd src/backend
          uvx bandit -r careervp/ -ll
```

---

## Part 5: Consolidated Security Action Plan

### Priority 1: IMMEDIATE (Before ANY deployment) - 1 day

1. ✅ Upgrade `cryptography` to >=46.0.5 (F-003)
2. ✅ Upgrade `aws-cdk-lib` (F-004)
3. ✅ Fix JWT env var mismatch (F-002)
4. ✅ Remove ALL `AUTHORIZER_DISABLED` checks (Finding 4)
5. ✅ Disable `log_event=True` (Finding 9)
6. ✅ Fix SSRF in web_scraper.py (NF-001)
7. ✅ Add auth to company_research POST (NF-002)

### Priority 2: CRITICAL (Phase 1 blockers) - 2 days

8. ✅ Add knowledge_base_handler to auth migration (Finding 1)
9. ✅ Fix auth_utils to NOT use AUTHORIZER_DISABLED (Step 1.1.1 fix)
10. ✅ Migrate 4 missing handlers (vpr_submit, vpr_status, user, knowledge_base)
11. ✅ Add CORS validation utility (Finding 7)
12. ✅ Fix cursor injection (NF-003)
13. ✅ Fix knowledge_base POST user_id (NF-004)
14. ✅ Fix critical bugs: empty list crash, version parse, error swallowing

### Priority 3: HIGH (Phase 2-3) - 2 days

15. ✅ Add ConditionExpression to SQS worker (Finding 6)
16. ✅ Change SQS encryption to KMS_MANAGED (F-005)
17. ✅ Add brute force protection (NF-005)
18. ✅ Add token revocation (NF-006)
19. ✅ Enable API Gateway logging (NF-012)
20. ✅ Deploy WAF in all environments (NF-010)
21. ✅ Add magic byte validation (NF-013)

### Priority 4: MEDIUM (Hardening) - 3 days

22. Replace DynamoDB scans with queries (NF-007)
23. Fix user profile race condition (NF-008)
24. Move circuit breaker to DynamoDB (NF-009)
25. Fix WAF log policy (NF-011)
26. Remove SSM path from logs (NF-014)
27. Address remaining Checkov findings (F-005)

### Priority 5: LOW (Code quality) - 1 day

28. Fix timezone-naive datetimes (NF-015)
29. Add ConditionExpression to update_job_status (NF-016)
30. Fix remaining Bandit warnings (F-006)

---

## Part 6: Summary and Recommendations

### Key Recommendations

1. **DO NOT execute the current runbook as-is** - it contradicts 2 critical audit findings and misses 5 Critical vulnerabilities
2. **Add Phase 0 (Pre-Requisites) BEFORE Phase 1** - dependency upgrades and JWT fix are merge-blocking
3. **Rewrite Step 1.1.1** - remove AUTHORIZER_DISABLED pattern, don't re-introduce it
4. **Add knowledge_base_handler** to Step 1.1.2 migration list (Critical gap)
5. **Add Security Validation Gate** to Phase 4 - test actual security controls, not just HTTP status
6. **Add CI Security Jobs** (Phase 5) - prevent regression

### Estimated Timeline Impact

| Original Runbook | With Security Fixes | Delta |
|------------------|---------------------|-------|
| 3-4 weeks | 4-5 weeks | +1 week |

The security fixes add approximately 1 week to the timeline, but prevent deploying with 7 Critical vulnerabilities.

### Risk Assessment

| Scenario | Risk Level | Mitigation |
|----------|------------|------------|
| **Deploy current runbook as-is** | 🔴 CRITICAL | Don't - 7 Critical vulns remain, 2 audit recommendations contradicted |
| **Add Phase 0 only** | 🟡 MEDIUM | Better but still missing knowledge_base auth, race conditions, CORS |
| **Implement all recommendations** | 🟢 LOW | Full coverage, comprehensive security posture |

---

## Appendix A: Complete Finding Cross-Reference

| Audit Finding | New Finding | Severity | In Runbook? | Recommended Fix Phase |
|---------------|-------------|----------|-------------|----------------------|
| F-001 | - | Critical | Partial (Phase 3.1.1) | Phase 0 + 1.1 + 3.1.1 |
| F-002 | - | Critical ⬆ | NO | **Phase 0.2** |
| F-003 | - | Medium | NO | **Phase 0.1** |
| F-004 | - | Medium | NO | **Phase 0.1** |
| F-005 | - | Medium | Partial (Phase 3.1.2) | Phase 3.1.2 + 3.1.4 |
| F-006 | - | Low | NO | Priority 5 |
| Finding 1 | - | Critical | NO | **Phase 0 + 1.1.2 (ADD)** |
| Finding 2 | - | High | Partial (Phase 1.1) | Phase 1.1 |
| Finding 3 | - | High | Partial (Phase 1.1) | Phase 1.1 |
| Finding 4 | - | Critical ⬆ | NO (contradicted) | **Phase 0.3** |
| Finding 5 | - | High | Partial (Phase 1.1) | Phase 1.1.2 (expand list) |
| Finding 6 | - | High | NO | **Phase 2.1.2 (amend)** |
| Finding 7 | - | Medium | NO | **Phase 1.6 (NEW)** |
| Finding 8 | F-002 | Critical ⬆ | NO | **Phase 0.2** |
| Finding 9 | - | High ⬆ | NO | **Phase 0.4** |
| Finding 10-16 | - | Critical/High | NO | **Phase 1.7 (NEW)** |
| - | NF-001 | Critical | NO | **Phase 0.5** |
| - | NF-002 | Critical | NO | **Phase 0.5** |
| - | NF-003 | High | NO | Priority 2 |
| - | NF-004 | High | NO | Priority 2 |
| - | NF-005 | High | NO | Priority 3 |
| - | NF-006 | High | NO | Priority 3 |
| - | NF-007 to NF-014 | Medium | NO | Priority 3-4 |
| - | NF-015, NF-016 | Low | NO | Priority 5 |

---

**END OF REPORT**

**Next Actions:**
1. Review and approve this report
2. Update execution_runbook.md per recommendations
3. Execute Phase 0 (new pre-requisite phase)
4. Proceed with amended Phases 1-4
5. Implement Phase 5 (CI guardrails)
