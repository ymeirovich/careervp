# L3.1 — Application Schema Results

**Date:** 2026-02-27
**Test file:** `tests/unit/test_l3_application_schema.py`
**Invariants:** I5, I6
**Branch:** `beta/fix-gaps1`

## Test-First Rework (RED → GREEN)

### RED Gate

Command:

```bash
cd src/backend && uv run pytest tests/unit/test_l3_application_schema.py -v --tb=short
```

Initial failure:

- Import error during test collection because `ApplicationRepository` stub did not expose
  `APPLICATION_STATES` / `VALID_TRANSITIONS` and lacked required CRUD methods.

### GREEN Gate

Implementation:

- Replaced `src/backend/careervp/dal/application_repository.py` stub with real repository:
  - `create(user_id, job_id) -> application_id`
  - `get(application_id, user_id)`
  - `update_state(..., expected_state)` with DynamoDB `ConditionExpression`
  - `update_cv(...)`
  - `update_artifact_status(...)`
  - exported `APPLICATION_STATES` and `VALID_TRANSITIONS`
- Replaced scaffold assertions in `tests/unit/test_l3_application_schema.py` with real behavior assertions.

Command:

```bash
cd src/backend && uv run pytest tests/unit/test_l3_application_schema.py -v --tb=short
```

Result:

- `30 passed`

## Summary

| Status | Count |
|--------|-------|
| PASSED | 31    |
| FAILED | 0     |
| ERRORS | 0     |

**Result: GREEN ✓**

## Notes

Validation commands:

```bash
cd src/backend && uv run ruff check careervp/dal/application_repository.py tests/unit/test_l3_application_schema.py
cd src/backend && uv run mypy careervp/dal/application_repository.py --strict
rg -n "NotImplementedError" src/backend/careervp/dal/application_repository.py
rg -n "assert True" src/backend/tests/unit/test_l3_application_schema.py
```

Observed outcomes:

- Ruff: pass
- Mypy: pass
- `NotImplementedError` grep: no matches
- `assert True` grep: no matches
