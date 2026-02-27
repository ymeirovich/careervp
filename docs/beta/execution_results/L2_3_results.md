# L2.3 — Identity Extraction Hardening Results

**Date:** 2026-02-27  
**Step:** Remove `X-User-Id` / payload identity fallback  
**Test file:** `tests/unit/test_cognito_middleware.py`  
**Invariant:** I4

## Validation Commands

- `cd src/backend && .venv/bin/pytest tests/unit/test_cognito_middleware.py tests/unit/test_auth_utils.py -v --tb=short`
  - Result: `15 passed`
- `cd src/backend && .venv/bin/ruff check careervp/handlers/auth_utils.py careervp/handlers/cv_upload_handler.py careervp/handlers/gap_handler.py careervp/handlers/vpr_submit_handler.py careervp/handlers/vpr_status_handler.py careervp/handlers/job_handler.py careervp/handlers/user_handler.py careervp/handlers/knowledge_base_handler.py`
  - Result: `All checks passed!`
- `cd src/backend && .venv/bin/mypy careervp/handlers/auth_utils.py --strict`
  - Result: `Success: no issues found in 1 source file`
- `rg -n "X-User-Id|x-user-id|payload.*user_id|body.*user_id" src/backend/careervp/handlers/ > docs/beta/evidence/I4_identity/identity-extraction-audit.txt || true`
  - Result: `0` lines

## Evidence

- `docs/beta/evidence/I4_identity/identity-extraction-audit.txt` created and empty.

## Notes

- `extract_user_id()` now reads Cognito claim `sub` only (JWT claims or REST claims shape).
- Removed payload/header fallback identity extraction from handlers touched in this step.
