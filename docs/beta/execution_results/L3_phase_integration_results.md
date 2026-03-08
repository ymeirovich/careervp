# L3 Phase Integration Results

**Date:** 2026-02-27  
**Phase:** Phase 4 (Application State, Layer 3)  
**Invariant:** I6  
**Evidence:** `docs/beta/evidence/I6_state/state-recovery-matrix.json`

## Scope

- Validate end-to-end backend state recovery behavior across L3 gates:
  - L3.1 schema/state repository
  - L3.2 recovery endpoint
  - L3.3 trial charging + state transitions
  - L3.4 reload recovery coverage

## Command

```bash
cd src/backend && uv run pytest \
  tests/unit/test_l3_application_schema.py \
  tests/unit/test_l3_application_recovery.py \
  tests/unit/test_l3_trial_credit_charging.py \
  tests/unit/test_application_state.py \
  tests/unit/test_l3_state_recovery.py \
  -v --tb=short
```

## Result

- `82 passed`
- `0 failed`
- `0 errors`

## Notes

- All canonical application lifecycle states are covered in backend reload assertions.
- Frontend UX reload validation remains deferred; backend matrix evidence is generated and attached.
