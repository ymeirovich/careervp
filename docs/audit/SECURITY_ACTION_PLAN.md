# CareerVP Security Remediation Action Plan

**Created:** 2026-02-20
**Status:** PENDING EXECUTION
**Owner:** TBD

**Source:** Cross-validation of security_bug_audit_2026-02-20.md + security_bug_audit.md + 16 new vulnerabilities discovered

---

## Quick Stats

| Priority | Count | Estimated Effort | Status |
|----------|-------|------------------|--------|
| **IMMEDIATE (P0)** | 7 items | 1 day | ⏳ PENDING |
| **CRITICAL (P1)** | 7 items | 2 days | ⏳ PENDING |
| **HIGH (P2)** | 7 items | 2 days | ⏳ PENDING |
| **MEDIUM (P3)** | 6 items | 3 days | ⏳ PENDING |
| **LOW (P4)** | 3 items | 1 day | ⏳ PENDING |
| **TOTAL** | 30 items | 9 days | ⏳ PENDING |

---

## PRIORITY 0: IMMEDIATE (MERGE-BLOCKING)

**Deadline:** Before ANY code deployment
**Estimated Effort:** 1 day (6 hours)
**Owner:** TBD

### I-001: Upgrade cryptography dependency (F-003)
- [ ] Update `pyproject.toml`: `cryptography>=46.0.5`
- [ ] Run `uv lock` and `uv export`
- [ ] Verify: `uvx pip-audit -r lambda_requirements.txt` → 0 vulnerabilities
- **File:** `src/backend/pyproject.toml`
- **Severity:** Medium (CVE exposure)
- **Effort:** 15 minutes

### I-002: Upgrade Node/CDK dependencies (F-004)
- [ ] Run `npm update aws-cdk-lib cdk-monitoring-constructs`
- [ ] Verify: `npm audit --omit=dev --audit-level=high` → 0 vulnerabilities
- [ ] Test: `cd infra && npx cdk synth` → success
- **File:** `package.json`
- **Severity:** Medium (supply chain)
- **Effort:** 2-4 hours

### I-003: Fix JWT configuration mismatch (F-002)
- [ ] Remove `JWT_SECRET` and `JWT_ALGORITHM` from `api_construct.py:1340-1341`
- [ ] Add `JWT_PRIVATE_KEY` and `JWT_PUBLIC_KEY` from SSM Parameter Store
- [ ] Update `auth_service.py:136` to fail fast if keys missing in non-local env
- [ ] Store RSA keys in SSM with appropriate permissions
- **Files:** `infra/careervp/api_construct.py`, `src/backend/careervp/logic/auth_service.py`
- **Severity:** CRITICAL (auth broken across Lambda instances)
- **Effort:** 2 hours

### I-004: Remove ALL AUTHORIZER_DISABLED checks (Finding 4)
- [ ] Delete `_authorizer_disabled()` functions from 4 handlers:
  - `cv_tailoring_handler.py:363`
  - `cover_letter_handler.py:196`
  - `interview_prep_handler.py:157`
  - `company_research_handler.py:205`
- [ ] Verify: `grep -r "AUTHORIZER_DISABLED" src/backend/careervp/handlers/` → 0 matches
- **Files:** 4 handler files
- **Severity:** CRITICAL (single env var bypasses all auth)
- **Effort:** 30 minutes

### I-005: Disable sensitive event logging (Finding 9)
- [ ] Change `log_event=True` to `log_event=False` in 4 handlers:
  - `vpr_handler.py:28`
  - `vpr_submit_handler.py:170`
  - `vpr_status_handler.py:253`
  - `vpr_worker_handler.py:213`
- [ ] Verify: `grep -r "log_event.*True" src/backend/careervp/handlers/` → 0 matches
- **Files:** 4 VPR handler files
- **Severity:** HIGH (JWT tokens logged to CloudWatch)
- **Effort:** 15 minutes

### I-006: Fix SSRF in web scraper (NF-001)
- [ ] Add `_is_safe_url()` function to validate URLs
- [ ] Reject internal/private IP ranges (169.254.x.x, 10.x.x.x, 172.16.x.x, 127.0.0.1)
- [ ] Reject cloud metadata endpoint (169.254.169.254)
- [ ] Enforce HTTPS only
- [ ] Add unit tests for SSRF prevention
- **File:** `src/backend/careervp/logic/utils/web_scraper.py:28`
- **Severity:** CRITICAL (can fetch AWS metadata/credentials)
- **Effort:** 1 hour

### I-007: Add auth to company research POST (NF-002)
- [ ] Add authentication check at start of `_fetch_company_research()`
- [ ] Return 401 if `_extract_authenticated_user_id(event)` returns None
- [ ] Add integration test: unauthenticated POST returns 401
- **File:** `src/backend/careervp/handlers/company_research_handler.py:47`
- **Severity:** CRITICAL (unauthenticated endpoint + SSRF)
- **Effort:** 30 minutes

**P0 Exit Criteria:**
- [ ] All 7 items completed
- [ ] `pip-audit` clean
- [ ] `npm audit` clean
- [ ] No AUTHORIZER_DISABLED in codebase
- [ ] No log_event=True in handlers
- [ ] SSRF validation passes tests
- [ ] Company research POST requires auth

---

## PRIORITY 1: CRITICAL (Phase 1 Blockers)

**Deadline:** Before Phase 1 completion
**Estimated Effort:** 2 days
**Owner:** TBD

### C-001: Add knowledge_base_handler to auth migration (Finding 1)
- [ ] Add `knowledge_base_handler.py` to Step 1.1.2 migration list
- [ ] Implement auth check in `_handle_get()` at line 39
- [ ] Implement auth check in `_handle_post()` at line 67
- [ ] Override body-supplied `user_id` with authenticated user
- [ ] Add tests: unauthenticated requests return 401
- **File:** `src/backend/careervp/handlers/knowledge_base_handler.py`
- **Severity:** CRITICAL (unauthenticated read/write to any user's data)
- **Effort:** 2 hours

### C-002: Fix auth_utils to remove AUTHORIZER_DISABLED pattern
- [ ] Rewrite Step 1.1.1 `extract_user_id()` without AUTHORIZER_DISABLED
- [ ] Use `ENV=local` check instead for dev fallback
- [ ] Update all handler migrations to use corrected auth_utils
- **File:** `src/backend/careervp/handlers/auth_utils.py` (to be created)
- **Severity:** CRITICAL (runbook contradicts audit)
- **Effort:** 1 hour

### C-003: Migrate 4 missing handlers to auth_utils
- [ ] Add to Step 1.1.2 migration list:
  - `vpr_submit_handler.py` (has `payload.get('user_id')` at line 113)
  - `vpr_status_handler.py` (has `payload.get('user_id')` at line 106)
  - `job_handler.py` (has `payload.get('user_id')` at line 123)
  - `user_handler.py` (has `payload.get('user_id')` at line 125)
- [ ] Remove all `payload.get('user_id')` fallbacks
- [ ] Verify: `grep -r "payload.*user_id" src/backend/careervp/handlers/` → 0 matches
- **Files:** 4 handler files
- **Severity:** HIGH (user ID spoofing)
- **Effort:** 3 hours

### C-004: Add CORS validation utility (Finding 7)
- [ ] Create `src/backend/careervp/handlers/cors_utils.py`
- [ ] Implement `get_cors_headers(origin)` with allowlist validation
- [ ] Update all 7 handlers to use `cors_utils`
- [ ] Add `ALLOWED_ORIGINS` env var to CDK
- [ ] Verify: No handler returns `Access-Control-Allow-Origin: *`
- **Files:** 7 handler files + new cors_utils.py
- **Severity:** MEDIUM (CSRF/data exfiltration risk)
- **Effort:** 2 hours

### C-005: Fix cursor injection in user handler (NF-003)
- [ ] Add validation in `_parse_cursor()` at line 143
- [ ] Verify decoded cursor's `userId` matches authenticated user
- [ ] Return 400 if mismatch
- [ ] Add test: cursor targeting different user rejected
- **File:** `src/backend/careervp/handlers/user_handler.py:143-176`
- **Severity:** HIGH (cross-user data access)
- **Effort:** 1 hour

### C-006: Fix knowledge_base POST arbitrary user_id (NF-004)
- [ ] Add auth check to `_handle_post()` at line 67
- [ ] Override `payload['user_id']` with authenticated user_id
- [ ] Return 401 if no auth
- [ ] Add test: cross-user write rejected
- **File:** `src/backend/careervp/handlers/knowledge_base_handler.py:67-101`
- **Severity:** HIGH (write to any user's knowledge base)
- **Effort:** 1 hour

### C-007: Fix critical bugs (Findings 10-16)
- [ ] **Finding 10:** Add early return check before `max(items, ...)` in DAL methods
- [ ] **Finding 11:** Use `getattr(context, 'aws_request_id', 'unknown')` in exception handlers
- [ ] **Finding 12:** Wrap `int(record.get('version', 0))` in try/except ValueError
- [ ] **Finding 15:** Replace `except Exception: continue` with specific exceptions + logging (company_research_handler.py:277,296)
- [ ] **Finding 18:** Add type validation in `knowledge_base_handler.py:77`
- [ ] **Finding 20:** Fix None comparison in `user_handler.py:220-221`
- **Files:** Multiple DAL and handler files
- **Severity:** CRITICAL/HIGH (crashes, error swallowing)
- **Effort:** 4 hours

**P1 Exit Criteria:**
- [ ] All 7 items completed
- [ ] knowledge_base_handler has auth on GET and POST
- [ ] No payload.get('user_id') in any handler
- [ ] CORS uses allowlist, not wildcard
- [ ] All critical bugs fixed with tests
- [ ] Unit tests pass

---

## PRIORITY 2: HIGH (Phase 2-3)

**Deadline:** Before Phase 2-3 completion
**Estimated Effort:** 2 days
**Owner:** TBD

### H-001: Add SQS worker race condition fix (Finding 6)
- [ ] Add `ConditionExpression='#status = :expected'` to status updates in vpr_worker_handler
- [ ] Implement atomic PENDING → PROCESSING transition
- [ ] Implement atomic PROCESSING → COMPLETED/FAILED transition
- [ ] Add idempotency key check in vpr_submit_handler
- [ ] Add test: duplicate SQS message doesn't duplicate work
- **File:** `src/backend/careervp/handlers/vpr_worker_handler.py:86-112`
- **Severity:** HIGH (duplicate processing, cost amplification)
- **Effort:** 2 hours

### H-002: Change SQS encryption to KMS_MANAGED (F-005)
- [ ] Update `api_construct.py:1079` from `SQS_MANAGED` to `KMS_MANAGED`
- [ ] Create KMS key with rotation enabled
- [ ] Update queue encryption configuration
- [ ] Verify Checkov CKV_AWS_27 passes
- **File:** `infra/careervp/api_construct.py`
- **Severity:** MEDIUM (Checkov failure, security posture)
- **Effort:** 1 hour

### H-003: Add brute force protection (NF-005)
- [ ] Implement account-level rate limiting in auth_service
- [ ] Track failed login attempts in DynamoDB (with TTL)
- [ ] Lock account after N failed attempts (progressive cooldown)
- [ ] Add WAF rate-based rule for `/auth/login` endpoint
- [ ] Return 429 Too Many Requests when limits exceeded
- **Files:** `src/backend/careervp/logic/auth_service.py`, WAF construct
- **Severity:** HIGH (credential stuffing risk)
- **Effort:** 4 hours

### H-004: Add token revocation mechanism (NF-006)
- [ ] Create DynamoDB table for token blacklist (with TTL)
- [ ] Implement `POST /auth/logout` endpoint
- [ ] Check blacklist in `refresh_token()` method
- [ ] Revoke all tokens on password change
- [ ] Add test: blacklisted token rejected
- **Files:** `src/backend/careervp/logic/auth_service.py`, new handler
- **Severity:** HIGH (no way to revoke compromised tokens)
- **Effort:** 3 hours

### H-005: Enable API Gateway CloudWatch logging (NF-012)
- [ ] Set `cloud_watch_role=True` in `api_construct.py:234`
- [ ] Add `access_log_destination` and `access_log_format` to StageOptions
- [ ] Configure method-level error logging
- [ ] Verify logs appear in CloudWatch
- **File:** `infra/careervp/api_construct.py`
- **Severity:** MEDIUM (observability gap)
- **Effort:** 1 hour

### H-006: Deploy WAF in all environments (NF-010)
- [ ] Remove `if is_production_env:` check at `api_construct.py:185`
- [ ] Deploy WAF with AWSManagedRulesCommonRuleSet in dev/staging
- [ ] Configure count-only mode in dev if cost is concern
- [ ] Verify WAF attached in all environments
- **File:** `infra/careervp/api_construct.py`
- **Severity:** MEDIUM (dev/staging unprotected)
- **Effort:** 30 minutes

### H-007: Add magic byte validation for CV uploads (NF-013)
- [ ] Implement magic byte validation in `validators.py:130-131`
- [ ] Check PDF signature (%PDF), DOCX/DOC (PK + [Content_Types].xml)
- [ ] Set S3 Content-Type and Content-Disposition headers
- [ ] Add test: renamed HTML file rejected
- **File:** `src/backend/careervp/handlers/validators.py`
- **Severity:** MEDIUM (stored XSS via polyglot files)
- **Effort:** 2 hours

**P2 Exit Criteria:**
- [ ] All 7 items completed
- [ ] SQS worker uses conditional updates
- [ ] SQS encryption is KMS-managed
- [ ] Login rate limiting active
- [ ] Token revocation works
- [ ] API Gateway logs to CloudWatch
- [ ] WAF deployed in all envs
- [ ] CV upload validates file signatures

---

## PRIORITY 3: MEDIUM (Hardening)

**Deadline:** Sprint N+2
**Estimated Effort:** 3 days
**Owner:** TBD

### M-001: Replace DynamoDB scans with queries (NF-007)
- [ ] Create GSI on `user_id` for jobs_repository methods
- [ ] Replace scan with query in `list_jobs()` at line 112
- [ ] Replace scan with query in `get_jobs_by_user()` at line 126
- [ ] Replace scan with query in `get_vpr_jobs_by_user()` at line 140
- [ ] Implement pagination with LastEvaluatedKey
- **File:** `src/backend/careervp/dal/jobs_repository.py`
- **Severity:** MEDIUM (performance/cost + result truncation)
- **Effort:** 4 hours

### M-002: Fix user profile update race condition (NF-008)
- [ ] Replace `put_item()` with `update_item()` in `user_repository.py:65`
- [ ] Use SET expressions for only changed fields
- [ ] Add version attribute for optimistic concurrency control
- [ ] Add test: concurrent updates don't overwrite each other
- **File:** `src/backend/careervp/dal/user_repository.py`
- **Severity:** MEDIUM (data loss on concurrent updates)
- **Effort:** 2 hours

### M-003: Move circuit breaker state to DynamoDB (NF-009)
- [ ] Refactor `circuit_breaker.py:29-44` to use DynamoDB backend
- [ ] Use atomic increment for failure count
- [ ] Store state with TTL-based recovery
- [ ] Add test: circuit state shared across Lambda instances
- **File:** `src/backend/careervp/logic/circuit_breaker.py`
- **Severity:** MEDIUM (ineffective protection in serverless)
- **Effort:** 3 hours

### M-004: Fix WAF log group policy (NF-011)
- [ ] Replace `AnyPrincipal()` with `ServicePrincipal('delivery.logs.amazonaws.com')`
- [ ] Add Condition restricting `aws:SourceAccount`
- [ ] Verify WAF can still write logs
- **File:** `infra/careervp/waf_construct.py:130-139`
- **Severity:** MEDIUM (cross-account log injection)
- **Effort:** 1 hour

### M-005: Remove SSM parameter path from logs (NF-014)
- [ ] Change `logger.info` at `llm_client.py:97,119` to generic message
- [ ] Log parameter name only at DEBUG level
- [ ] Ensure DEBUG disabled in production
- **File:** `src/backend/careervp/logic/utils/llm_client.py`
- **Severity:** MEDIUM (info disclosure)
- **Effort:** 15 minutes

### M-006: Address remaining Checkov findings (F-005)
- [ ] Enable API Gateway X-Ray tracing
- [ ] Enable CloudWatch log group encryption for Lambda functions
- [ ] Enable S3 bucket versioning and logging for existing buckets
- [ ] Document accepted exceptions with rationale and owner
- [ ] Classify residual findings as: must-fix, accept-with-control, false-positive
- **Files:** CDK constructs
- **Severity:** MEDIUM (security posture)
- **Effort:** 4 hours

**P3 Exit Criteria:**
- [ ] All 6 items completed
- [ ] Jobs queries use GSI, not scan
- [ ] User updates use update_item
- [ ] Circuit breaker state in DynamoDB
- [ ] WAF logs secured
- [ ] SSM paths not logged
- [ ] Top Checkov findings addressed

---

## PRIORITY 4: LOW (Code Quality)

**Deadline:** Sprint N+3
**Estimated Effort:** 1 day
**Owner:** TBD

### L-001: Fix timezone-naive datetimes (NF-015)
- [ ] Change `datetime.now()` to `datetime.now(timezone.utc)` in `cv_tailoring_dal.py:28-29`
- [ ] Search for other timezone-naive usages: `grep -r "datetime.now()" src/backend/`
- [ ] Fix all instances
- **Files:** DAL files
- **Severity:** LOW (timestamp inconsistencies)
- **Effort:** 30 minutes

### L-002: Add ConditionExpression to update_job_status (NF-016)
- [ ] Add `ConditionExpression='attribute_exists(job_id)'` to `jobs_repository.py:246-252`
- [ ] Add expected_status parameter for state machine validation
- [ ] Add test: update on non-existent job returns error
- **File:** `src/backend/careervp/dal/jobs_repository.py`
- **Severity:** LOW (silent no-op, phantom items)
- **Effort:** 1 hour

### L-003: Fix remaining Bandit warnings (F-006)
- [ ] Replace runtime `assert` at `vpr_worker_handler.py:57` with explicit validation
- [ ] Add structured logging before `except Exception: continue` fallback
- [ ] Add `# nosec` with justification for false positives
- **Files:** Multiple handlers
- **Severity:** LOW (code quality)
- **Effort:** 1 hour

**P4 Exit Criteria:**
- [ ] All 3 items completed
- [ ] All datetimes are timezone-aware
- [ ] Job updates validate existence
- [ ] Bandit scan clean or documented

---

## CI/CD Integration (Phase 5)

**Add to GitHub Actions:**

### Security Audit Workflow
```yaml
# .github/workflows/security.yml
name: Security Audit
on: [pull_request, push]

jobs:
  python-deps:
    - run: uvx pip-audit -r lambda_requirements.txt

  node-deps:
    - run: npm audit --omit=dev --audit-level=high

  iac-security:
    - run: npx cdk synth
    - run: uvx checkov -d cdk.out --framework cloudformation

  code-quality:
    - run: uvx bandit -r careervp/ -ll
```

### Security Gate (Pre-Deploy)
```bash
# scripts/security-gate.sh
echo "=== Security Gate ==="

# Auth enforcement
curl -w "%{http_code}" "$API_BASE/users/me" | grep -q "401"

# SSRF blocked
curl -X POST "$API_BASE/company-research/fetch" \
  -d '{"domain":"http://169.254.169.254"}' | grep -q "URL not allowed"

# Dependency audit
pip-audit -r lambda_requirements.txt | grep -q "Found 0 vulnerabilities"
npm audit --omit=dev | grep -q "0 vulnerabilities"

# Checkov
checkov -d cdk.out --check CKV_AWS_59 | grep -q "PASSED"

# No sensitive logging
! grep -r "log_event.*True" src/backend/careervp/handlers/
! grep -r "AUTHORIZER_DISABLED" src/backend/careervp/handlers/

echo "=== All Gates Passed ==="
```

---

## Tracking Dashboard

### Overall Progress
- [ ] **P0 (IMMEDIATE):** 0/7 items (0%)
- [ ] **P1 (CRITICAL):** 0/7 items (0%)
- [ ] **P2 (HIGH):** 0/7 items (0%)
- [ ] **P3 (MEDIUM):** 0/6 items (0%)
- [ ] **P4 (LOW):** 0/3 items (0%)
- [ ] **CI/CD:** 0/2 items (0%)

### Total: 0/32 items (0%) - 9 days remaining

### Risk Level
🔴 **CRITICAL** - 7 Critical vulnerabilities remain unpatched

### Next Review Date
TBD

---

## Appendix: Quick Reference

### Critical Files Requiring Changes
1. `api_construct.py` - JWT env vars, SQS encryption, WAF, logging
2. `auth_service.py` - JWT key handling, brute force, token revocation
3. `knowledge_base_handler.py` - Auth on GET/POST, input validation
4. `company_research_handler.py` - Auth on POST, error handling
5. `web_scraper.py` - SSRF prevention
6. `vpr_worker_handler.py` - Race condition, conditional updates
7. 7 handlers - Remove log_event=True, AUTHORIZER_DISABLED, CORS
8. `auth_utils.py` (new) - Centralized auth without AUTHORIZER_DISABLED

### Verification Commands
```bash
# Dependency audit
uvx pip-audit -r lambda_requirements.txt
npm audit --omit=dev --audit-level=high

# Code patterns
grep -r "AUTHORIZER_DISABLED" src/backend/careervp/handlers/
grep -r "log_event.*True" src/backend/careervp/handlers/
grep -r "payload.*user_id" src/backend/careervp/handlers/
grep -r "Access-Control-Allow-Origin.*\*" src/backend/careervp/handlers/

# IaC audit
npx cdk synth && uvx checkov -d cdk.out --framework cloudformation
```

### Contact
- Security Team: TBD
- Audit Report: `docs/audit/security_validation_report_2026-02-20.md`
- Original Audits: `docs/audit/security_bug_audit*.md`

---

**END OF ACTION PLAN**

**Last Updated:** 2026-02-20
**Status:** Ready for execution
**Approval Required:** YES
