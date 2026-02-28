# L5.1 — Trial Expiry Check Results

**Date:** 2026-02-27  
**Step:** L5.1  
**Invariant:** I5 (expiry check)  
**Branch:** `beta/fix-gaps1`

## Commands

```bash
cd src/backend && uv run pytest tests/unit/test_trial_enforcement.py::TestTrialExpiry -v --tb=short
cd src/backend && uv run ruff check careervp/logic/trial_service.py
cd src/backend && uv run mypy careervp/logic/trial_service.py --strict
```

## Results

- `TestTrialExpiry`: **6 passed, 0 failed**
- `ruff` (`trial_service.py`): **pass**
- `mypy --strict` (`trial_service.py`): **pass**

## Gate

- Status: **GREEN ✓**
- Notes: Day-14/day-15 expiry behavior enforced via `TrialExpiredException`.
