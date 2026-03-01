# Contract Drift Check

Implements: cognito-test-fixes/PLAN.md T5 / SPEC.md FIX C-D

This file records discrepancies between contract fixture expectations and live API responses.
Update after every test run where fixture expectations or handler response shapes change.

**Rule:** Every drift row must have either:
- A linked fix reference (e.g., "awaiting P2-C") AND expected resolution date, OR
- A fixture update confirming the new shape is approved

**Never leave drift unresolved without a note.**

---

## Current Status

**Last Updated:** YYYY-MM-DD
**Live Test Run:** (link to log or gate result file)
**Suite:** test_10_api_contract_success.py + test_00_auth_bootstrap.py

---

## Drift Log

| Endpoint | Fixture File | Drift? | Actual Response (summary) | Expected (fixture) | Root Cause | Resolution |
|---|---|---|---|---|---|---|
| GET /health | health_check.json | YES (awaiting fix) | `{"status": "degraded"}` | `{"status": "healthy"}` | Health Lambda missing DYNAMODB_TABLE_NAME | Deploy P2-A |
| GET /users/me | user_get.json | YES (awaiting fix) | 401 from API Gateway | 200 with user shape | auth_service issues custom JWT; Cognito rejects | Deploy P2-C |
| POST /auth/login | auth_login.json | NO | shape matches | shape matches | — | — |
| POST /auth/register | auth_register.json | NO | shape matches | shape matches | — | — |
| GET /jobs | job_list.json | YES (awaiting fix) | `{"jobs": []}` | `{"jobs": [...]}` | Missing user_id-index GSI | Deploy P1-A |
| GET /users/me/vprs | vpr_list.json | YES (awaiting fix) | `{"vprs": []}` | `{"vprs": [...]}` | Missing user_id-index GSI | Deploy P1-A |
| GET /users/me/cvs | cv_list.json | YES (awaiting fix) | `{"cvs": []}` | `{"cvs": [...]}` | CV table mismatch | Deploy P1-C |
| POST /gap-analysis/questions | gap_questions_generate.json | YES (awaiting fix) | 201 with fallback question | 200/201 with real AI questions | ANTHROPIC_API_KEY not set | Deploy P1-B |
| POST /company-research/fetch | company_research_fetch.json | YES (awaiting fix) | 404 Not Found | 200/202 | Route not registered in API Gateway | Deploy P2-B |

---

## How to Update This File

After each test run:

1. Run `pytest docs/refactor/live_tests/test_10_api_contract_success.py -v`
2. For any failed assertion, note the actual response vs. fixture expectation
3. Add or update a row in the table above
4. If a fix has been deployed, change "awaiting fix" to "RESOLVED" and add the deploy date

After all fixes are deployed and G2 (protected success gate) passes:
- All rows in this table should show `NO` drift or `RESOLVED`
- Archive this file to `docs/beta/evidence/contract_drift_check_YYYY-MM-DD_resolved.md`
