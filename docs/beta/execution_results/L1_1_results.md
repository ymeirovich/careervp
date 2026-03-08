# L1.1 — Artifact Persistence Results

**Date:** 2026-02-27  
**Branch:** `beta/exec-runbk`  
**Test file:** `tests/unit/test_l1_artifact_persistence.py`  
**Invariants:** I2 (partial)

## Files Updated

- `src/backend/tests/unit/test_l1_artifact_persistence.py`
- `src/backend/careervp/handlers/interview_prep_handler.py`
- `src/backend/careervp/handlers/cv_tailoring_handler.py`
- `src/backend/careervp/handlers/gap_handler.py`
- `src/backend/careervp/dal/cv_dal.py`
- `src/backend/careervp/dal/jobs_repository.py`

## RED Phase (tests first)

Command:

```bash
cd src/backend && uv run pytest tests/unit/test_l1_artifact_persistence.py -v --tb=short
```

Initial failure state:

- `3 failed, 3 passed`
- Failing issues:
  - interview-prep persistence item missing `ttl`
  - cv-tailoring async persistence `sk` not using `ARTIFACT#CV_TAILORED#` prefix
  - cover-letter test payload invalid (request schema mismatch in test setup)

## GREEN Phase (after implementation)

Command:

```bash
cd src/backend && uv run pytest tests/unit/test_l1_artifact_persistence.py -v --tb=short
```

Result:

- `6 passed, 0 failed`

## Validation Commands

```bash
rg -n "table.scan|\\.scan\\(" src/backend/careervp/ | rg -v test | wc -l
cd src/backend && uv run pytest tests/unit/test_l1_artifact_persistence.py -v --tb=short
cd src/backend && uv run ruff check careervp/handlers/
cd src/backend && uv run mypy careervp/handlers/ --strict
```

Results:

- scan grep result: `0`
- pytest: `6 passed`
- ruff: all checks passed
- mypy: success, no issues found

## Implementation Notes

- Added `ttl` persistence field for interview prep artifacts.
- Normalized cv-tailoring async artifact storage to canonical `ARTIFACT#CV_TAILORED#...` sort key with `request_id` retained for API polling.
- Added cv-tailoring status lookup fallback by `request_id` so `/cv-tailoring/{request_id}` remains functional.
- Removed non-test `.scan()` usage paths by migrating to query-based access in:
  - gap question retrieval
  - CV DAL fallback lookup (partition-bounded query)
  - jobs repository listing methods (index-based query)
