# L3.2 — Application Recovery Results

**Date:** 2026-02-27
**Test file:** `tests/unit/test_l3_application_recovery.py`
**Invariants:** I5, I6
**Branch:** `beta/fix-gaps1`

## Test-First Rework (RED → GREEN)

### RED Gate

Command:

```bash
cd src/backend && uv run pytest tests/unit/test_l3_application_recovery.py -v --tb=short
```

Initial failures:

- `ModuleNotFoundError: No module named 'careervp.handlers.application_handler'`
- CDK still mapped `/applications/{application_id}` to `self.job_api_func`
- `job_handler.py` still exposed compatibility alias `@app.get('/applications/<application_id>')`

### GREEN Gate

Implementation:

- Added `src/backend/careervp/handlers/application_handler.py` with:
  - Cognito-only identity extraction
  - ownership enforcement
  - `GET /applications/{application_id}` recovery payload
  - reload route mapping by state
- Updated CDK route mapping to `self.application_api_func`.
- Added dedicated application lambda construct in `infra/careervp/api_construct.py`.
- Removed `/applications/<application_id>` compatibility alias from `job_handler.py`.

Command:

```bash
cd src/backend && uv run pytest tests/unit/test_l3_application_recovery.py -v --tb=short
```

Result:

- `17 passed`

## Summary

| Status | Count |
|--------|-------|
| PASSED | 17    |
| FAILED | 0     |
| ERRORS | 0     |

**Result: GREEN ✓**

## Notes

Validation commands:

```bash
cd src/backend && uv run ruff check careervp/handlers/application_handler.py careervp/handlers/job_handler.py tests/unit/test_l3_application_recovery.py
cd src/backend && uv run mypy careervp/handlers/application_handler.py --strict
cd infra && uv run ruff check careervp/api_construct.py
```

Observed outcomes:

- Ruff: pass (backend + infra)
- Mypy: pass

L3.2 coverage confirms:

- dedicated `/applications/{application_id}` handler is wired
- no compatibility alias remains in `job_handler.py`
- recovery response includes required fields for reload-state reconstruction
