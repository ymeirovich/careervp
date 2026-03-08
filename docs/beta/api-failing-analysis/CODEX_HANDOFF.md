# Codex Handoff: Fix Live E2E Tests - All Endpoints Must Return 2xx

## Project Path
`/Users/yitzchak/Documents/dev/careervp`

## Goal
ALL API endpoints in `docs/refactor/live_tests/run_all_tests.py` must return `status_code: 2xx`.

---

## COMPLETED WORK (Do NOT redo)

### 1. Test Path Fixes (ALL DONE - verified working)
All test files had mismatched endpoint paths vs actual API routes in `infra/careervp/api_construct.py` (line 1779 `route_map`). Fixed:

| Test File | Old Path | Fixed Path |
|-----------|----------|------------|
| `test_05_gap_analysis.py` | `POST /gap-analysis/questions` | `POST /jobs/{jobId}/gap-questions` |
| `test_05_gap_analysis.py` | `POST /gap-analysis/responses` | `POST /jobs/{jobId}/gap-responses` |
| `test_05_gap_analysis.py` | `GET /gap-analysis/{jobId}/questions` | `GET /jobs/{jobId}/gap-questions` |
| `test_04_vpr.py` | `GET /vpr/{vprId}` | `GET /vpr/{vprId}/status` |
| `test_04_vpr.py` | `GET /users/me/vprs` | `GET /vprs` |
| `test_06_cv_tailoring.py` | `GET /cv-tailoring/{id}` | `GET /cv-tailoring/{id}/status` |
| `test_06_cv_tailoring.py` | `GET /users/me/tailored-cvs` | `GET /cv-tailorings` |
| `test_07_cover_letter.py` | `GET /cover-letter/{id}` | `GET /cover-letter/{id}/status` |
| `test_07_cover_letter.py` | `GET /users/me/cover-letters` | `GET /cover-letters` |
| `test_08_interview_prep.py` | `GET /interview-prep/{id}` | `GET /interview-prep/{id}/status` |
| `test_02_users.py` | `GET /users/me/cvs` (plural) | `GET /users/me/cv` (singular) |
| `test_09_company_research.py` | `POST /company-research/fetch` | SKIPPED (route doesn't exist in API Gateway) |

### 2. Gap Handler Refactored to Use DynamoDALHandler (DONE)
- `src/backend/careervp/handlers/gap_handler.py` - replaced all direct `boto3` calls with `DynamoDalHandler` methods
- Added `_get_dal()` factory function (follows `cover_letter_handler.py` pattern)
- `src/backend/careervp/dal/dynamo_dal_handler.py` - added 2 new methods:
  - `list_gap_questions_by_prefix(user_id, job_id)` - queries with sk prefix, filters by job_id
  - `save_gap_responses_raw(user_id, job_id, responses, version, ttl_days)` - saves raw dict responses
- Removed: `_get_table()`, `_build_gap_responses_application_id()`, `_build_gap_questions_application_id()`, `_ttl_timestamp()`, `_item_matches_job()`
- Removed imports: `boto3.dynamodb.conditions.Key`, `botocore.exceptions.ClientError`, `datetime` (no longer needed in handler)

---

## LATEST TEST RESULTS (full run completed)

### Final Score: 11 modules passed, 2 modules failed

### Endpoints returning 2xx (WORKING):
| Endpoint | Status | Test File |
|----------|--------|-----------|
| `GET /health` | 200 | test_01 |
| `POST /auth/register` | 201 | test_01 |
| `POST /auth/login` | 200 | test_01 |
| `POST /auth/refresh` | 200 | test_01 |
| `POST /users/me/cv` | 201 | test_02 |
| `GET /users/me/cv` | 200 | test_02 |
| `POST /jobs` | 201 | test_03 |
| `GET /jobs` | 200 | test_03 |
| `GET /jobs/{jobId}` | 200 | test_03 |
| `POST /vpr/generate` | 202 | test_04 |
| `GET /vpr/{vprId}/status` | 200 | test_04 |
| `GET /vprs` | 200 | test_04 |
| `POST /cv-tailoring/generate` | 200 | test_06 |
| `GET /cv-tailorings` | 200 | test_06 |
| `POST /jobs/{jobId}/gap-responses` | 201 | test_05 |

### Endpoints returning non-2xx (NEED FIXING):

| # | Endpoint | Status | Root Cause | Category |
|---|----------|--------|------------|----------|
| 1 | `GET /users/me` | 404 | No user profile created after Cognito signup | MISSING DATA |
| 2 | `PUT /users/me` | 404 | Same - no user profile record exists | MISSING DATA |
| 3 | `POST /jobs/{jobId}/gap-questions` | 502 | Lambda crash (deployed handler still uses old boto3 code) | NEEDS DEPLOY |
| 4 | `GET /jobs/{jobId}/gap-questions` | 500 | Lambda error (same - deployed handler issue) | NEEDS DEPLOY |
| 5 | `GET /cv-tailoring/{id}/status` | 404 | `test_data["cv_tailoring_id"]` is `None` - POST generate returns no `request_id`/`id` | TEST BUG |
| 6 | `GET /company-research/{jobId}` | 502 | Lambda crash - backend handler issue | CODE BUG |
| 7 | `POST /cover-letter/generate` | 502 | Lambda crash - all cover letter endpoints broken | CODE BUG |
| 8 | `GET /cover-letter/{id}/status` | 502 | Same Lambda crash | CODE BUG |
| 9 | `GET /cover-letters` | 502 | Same Lambda crash | CODE BUG |
| 10 | `POST /interview-prep/generate` | 502 | Lambda crash - all interview prep endpoints broken | CODE BUG |
| 11 | `GET /interview-prep/{id}/status` | 502 | Same Lambda crash | CODE BUG |
| 12 | `GET /applications/{id}` (error contract) | 502 | Lambda crash (test_11 expects 403/404 but gets 502) | CODE BUG |
| 13 | `test_10_api_contract_success` | FAILED | pytest exit code 1 - contract assertions failing | TEST or CODE BUG |

---

## WHAT CODEX SHOULD DO

### Phase 1: Investigate & Fix 502 Lambda Crashes (HIGHEST PRIORITY)
502 = API Gateway couldn't get a response from Lambda. This means the Lambda function is crashing on startup (import error, missing dependency) or timing out.

**For each 502 handler, do:**
1. Read the handler code
2. Check for import errors, missing env vars, or obvious crash causes
3. Fix the handler code
4. After all fixes, deploy with `cdk deploy`

**Files to investigate:**
```
src/backend/careervp/handlers/cover_letter_handler.py    → all 3 cover letter endpoints 502
src/backend/careervp/handlers/interview_prep_handler.py  → all 2 interview prep endpoints 502
src/backend/careervp/handlers/company_research_handler.py → GET endpoint 502
src/backend/careervp/handlers/gap_handler.py             → POST gap-questions 502 (needs deploy of refactored code)
```

**Common Lambda 502 causes to check:**
- Missing import at module level (ImportError on cold start)
- Missing env var referenced at module level (not inside handler function)
- Missing Lambda layer dependency
- Handler function name mismatch in CDK config vs actual export
- Timeout (Lambda default 3s may be too short for AI calls)

**To check Lambda config:** Read `infra/careervp/api_construct.py` and find how each handler's Lambda is configured (timeout, memory, layers, env vars).

### Phase 2: Fix User Profile 404 (Issues #1-2)
- `GET /users/me` and `PUT /users/me` both return 404
- Read `src/backend/careervp/handlers/user_handler.py`
- Determine: Does the handler require an existing profile? Or should it auto-create on first access?
- **Likely fix:** Either:
  - (a) Reorder tests: call `PUT /users/me` with profile data BEFORE `GET /users/me`, OR
  - (b) Fix the handler to auto-create a profile from Cognito claims on first GET, OR
  - (c) Add a profile creation step in test_02 setup

### Phase 3: Fix CV Tailoring Status 404 (Issue #5)
- `POST /cv-tailoring/generate` returns 200 but `test_data["cv_tailoring_id"]` is `None`
- The POST response doesn't include `request_id` or `id` fields
- Read the cv-tailoring handler to find what field name the response actually uses
- Update `test_06_cv_tailoring.py` to extract the correct ID field from the generate response
- The list endpoint (`GET /cv-tailorings`) works fine and returns 4 items, so data exists

### Phase 4: Fix test_10 and test_11 Contract Tests
- Read `docs/refactor/live_tests/test_10_api_contract_success.py` - understand what assertions fail
- Read `docs/refactor/live_tests/test_11_api_error_contracts.py` - the `test_applications_recovery_not_found_returns_404` test expects 403/404 but gets 502
- The 502 in test_11 is the same Lambda crash issue - fixing the handler (Phase 1) should fix this test too

### Phase 5: Deploy Changes
After fixing all handler code:
```bash
cd /Users/yitzchak/Documents/dev/careervp
cdk deploy --all --require-approval never
```
This deploys the gap_handler refactoring AND any other handler fixes.

### Phase 6: Final Validation
```bash
cd /Users/yitzchak/Documents/dev/careervp
python docs/refactor/live_tests/run_all_tests.py 2>&1 | tee /tmp/final-test-results.log
```

**Verify:**
- [ ] Zero non-2xx status codes (grep for `status_code` and check all are 2xx)
- [ ] Zero pytest failures (all modules show "passed")
- [ ] No 502, 500, 404, 403, 401 errors in output

---

## KEY FILES REFERENCE

### Test Files
- `docs/refactor/live_tests/run_all_tests.py` - test runner (orchestrates all modules)
- `docs/refactor/live_tests/conftest.py` - shared fixtures (API_BASE, auth, test_data persistence)
- `docs/refactor/live_tests/test_01_auth_health.py` - auth bootstrap + health
- `docs/refactor/live_tests/test_02_users.py` - user profile + CV upload
- `docs/refactor/live_tests/test_03_jobs.py` - job CRUD
- `docs/refactor/live_tests/test_04_vpr.py` - VPR generation + polling
- `docs/refactor/live_tests/test_05_gap_analysis.py` - gap questions + responses
- `docs/refactor/live_tests/test_06_cv_tailoring.py` - CV tailoring
- `docs/refactor/live_tests/test_07_cover_letter.py` - cover letter
- `docs/refactor/live_tests/test_08_interview_prep.py` - interview prep
- `docs/refactor/live_tests/test_09_company_research.py` - company research
- `docs/refactor/live_tests/test_10_api_contract_success.py` - success contract tests
- `docs/refactor/live_tests/test_11_api_error_contracts.py` - error contract tests

### Backend Handlers (Lambda functions)
- `src/backend/careervp/handlers/gap_handler.py` - ALREADY REFACTORED (needs deploy)
- `src/backend/careervp/handlers/cover_letter_handler.py` - 502 crash
- `src/backend/careervp/handlers/interview_prep_handler.py` - 502 crash
- `src/backend/careervp/handlers/company_research_handler.py` - 502 crash
- `src/backend/careervp/handlers/user_handler.py` - returns 404 for new users
- `src/backend/careervp/handlers/health_handler.py` - works but reports "degraded"

### Infrastructure
- `infra/careervp/api_construct.py` - CDK API Gateway routes (line 1779 `route_map`)
- `src/backend/careervp/dal/dynamo_dal_handler.py` - DynamoDB DAL (gap methods added)

### Analysis Docs
- `docs/beta/api-failing-analysis/FIX_LIVE_TESTS_PROMPT.md` - original analysis

---

## SUCCESS CRITERIA
- [ ] Gap handler refactored to use DynamoDALHandler (DONE - needs deploy)
- [ ] All tests in run_all_tests.py pass (0 failed modules)
- [ ] Every API endpoint returns 2xx status code
- [ ] No 403, 404, 401, 500, 502 errors in test output

## IMPORTANT RULES
- DO NOT assume - always read the actual handler code first
- Fix one issue at a time and verify
- The 502 errors are the #1 priority - they indicate Lambda crashes
- After fixing handler code, you MUST deploy (`cdk deploy`) before re-running tests
- These are LIVE tests hitting a deployed AWS API - local code changes alone won't fix test results
