# L2.5 — Auth Scenario Integration + Evidence Results

**Date:** 2026-02-27  
**Step:** Integration Test All Auth Scenarios  
**Test file:** `tests/integration/test_l2_auth_integration.py`  
**Invariant:** I3, I4

## Test-First Sequence

1. RED baseline:
   - `src/backend/tests/integration/test_l2_auth_integration.py` scaffold file was replaced with real assertions/evidence generation.
   - First execution failed at I4 static audit because forbidden grep patterns still matched handler code.
2. Implementation:
   - Rebuilt `test_l2_auth_integration.py` to:
     - validate all 15 protected routes × 4 auth scenarios,
     - write `docs/beta/evidence/I3_auth/auth-abuse-matrix.json`,
     - run/write `docs/beta/evidence/I4_identity/identity-extraction-audit.txt`.
   - Removed remaining forbidden `payload.*user_id` / `body.*user_id` handler matches while preserving behavior.
3. GREEN validation:
   - `cd src/backend && .venv/bin/pytest tests/integration/test_l2_auth_integration.py -v --tb=short -m integration`
   - Result: `2 passed`

## Unit Tests Run After Step

- `cd src/backend && .venv/bin/pytest tests/unit/test_auth_utils.py tests/unit/test_cognito_middleware.py tests/unit/test_vpr_endpoints.py tests/unit/test_cv_upload_handler.py tests/unit/test_cv_tailoring.py tests/unit/test_cv_tailoring_status.py -v --tb=short`
  - Result: `37 passed`

## Additional Validation

- `cd src/backend && .venv/bin/ruff check tests/integration/test_l2_auth_integration.py tests/unit/test_vpr_endpoints.py tests/unit/test_cv_upload_handler.py tests/unit/test_cv_tailoring_status.py careervp/handlers/vpr_submit_handler.py careervp/handlers/cv_upload_handler.py careervp/handlers/cv_tailoring_handler.py`
  - Result: `All checks passed!`
- Evidence integrity check:
  - `auth-abuse-matrix.json`: `total_routes=15`, `scenarios_per_route=4`, `total_checks=60`, `passes=60`
  - `identity-extraction-audit.txt`: empty file (`0` lines)

## Evidence

- `docs/beta/evidence/I3_auth/auth-abuse-matrix.json`
- `docs/beta/evidence/I4_identity/identity-extraction-audit.txt`

## Notes

- L2.4 remains blocked in this repo because `src/frontend` is not present.
