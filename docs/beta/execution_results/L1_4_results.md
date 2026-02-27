# L1.4 — List Endpoints Results

**Date:** 2026-02-27
**Test file:** `tests/unit/test_l1_list_endpoints.py`
**Invariants:** I2, I3, I4

## Summary

| Status | Count |
|--------|-------|
| PASSED | 17    |
| FAILED | 0     |
| ERRORS | 0     |

**Result: GREEN ✓**

## Test Classes

| Class | Tests | Status |
|-------|-------|--------|
| TestListEndpointsAuth | 3 | PASSED |
| TestListEndpointsDAL | 8 | PASSED |
| TestListEndpointsResponse | 6 | PASSED |

## Notes

Validates list endpoint invariants:
- GET /users/me/cover-letters, /tailored-cvs, /vprs all return 401 without Cognito JWT
- Auth uses `requestContext.authorizer.jwt.claims.sub` (HTTP API v2 format)
- DAL uses `table.query()` with `KeyConditionExpression`, never `table.scan()`
- Query scoped to authenticated user pk (no cross-user leakage)
- Response shape: `{ cover_letters: [], tailored_cvs: [], vprs: [] }`
