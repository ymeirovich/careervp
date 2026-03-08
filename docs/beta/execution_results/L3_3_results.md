# L3.3 — Trial Credit Charging Results

**Date:** 2026-02-27
**Test file:** `tests/unit/test_l3_trial_credit_charging.py`
**Invariants:** I5, I6
**Branch:** `beta/fix-gaps1`

## Test-First Rework (RED → GREEN)

### RED Gate

Command:

```bash
cd src/backend && uv run pytest tests/unit/test_l3_trial_credit_charging.py -v --tb=short
```

Initial failure:

- ImportError: `TrialExhaustedException` / `TrialExpiredException` missing from
  `careervp.logic.trial_service` stub.

### GREEN Gate

Implementation:

- Replaced `careervp.logic.trial_service` stub with real implementation:
  - `check_trial_status`
  - `consume_credit` (atomic `ConditionExpression`)
  - `get_usage`
  - concrete `TrialExpiredException` / `TrialExhaustedException`
- Wired `gap_handler.generate_questions` to enforce:
  - `check_trial_status` then `consume_credit`
  - transition to `gap_questions_pending` before LLM
  - transition to `gap_questions_ready` after successful generation
  - explicit 403 responses for expired/exhausted trial cases

Command:

```bash
cd src/backend && uv run pytest tests/unit/test_l3_trial_credit_charging.py -v --tb=short
```

Result:

- `7 passed`

## Summary

| Status | Count |
|--------|-------|
| PASSED | 7     |
| FAILED | 0     |
| ERRORS | 0     |

**Result: GREEN ✓**

## Notes

Validation commands:

```bash
cd src/backend && uv run ruff check careervp/logic/trial_service.py careervp/handlers/gap_handler.py tests/unit/test_l3_trial_credit_charging.py
cd src/backend && uv run mypy careervp/logic/trial_service.py --strict
```

Observed outcomes:

- Ruff: pass
- Mypy: pass

Enforced behavior:

- `consume_credit` executes before `generate_gap_questions`
- expired/exhausted trial blocks LLM execution
- application state transitions are attempted in the expected order
