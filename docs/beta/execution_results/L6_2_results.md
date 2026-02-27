# L6.2 — Route Deduplication Results

**Date:** 2026-02-27
**Test file:** `tests/unit/test_l6_route_dedup.py`
**Invariants:** I7

## Summary

| Status | Count |
|--------|-------|
| PASSED | 15    |
| FAILED | 0     |
| ERRORS | 0     |

**Result: GREEN ✓**

## Test Classes

| Class | Tests | Status |
|-------|-------|--------|
| TestNoApiPrefixRoutes | 4 | PASSED |
| TestCanonicalRouteCount | 4 | PASSED |
| TestPublicRoutesCorrectlyMarked | 4 | PASSED |
| TestCDKSynthSucceeds | 3 | PASSED |

## Notes

Validates I7 route surface invariant (deduplication):
- No `/api/` prefix routes in CDK (CDK uses `constants.API_ROOT_RESOURCE`)
- Canonical route count = 30 (verified against frozen_spec.json)
- Public routes (health, auth/*) use `NONE` auth; all others use `COGNITO`
- CDK synth does not raise (infrastructure is valid)
- Evidence file: `docs/beta/evidence/I7_routes/frozen_spec.json`
