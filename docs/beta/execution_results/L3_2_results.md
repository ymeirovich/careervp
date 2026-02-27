# L3.2 — Application Recovery Results

**Date:** 2026-02-27
**Test file:** `tests/unit/test_l3_application_recovery.py`
**Invariants:** I5, I6

## Summary

| Status | Count |
|--------|-------|
| PASSED | 25    |
| FAILED | 0     |
| ERRORS | 0     |

**Result: GREEN ✓**

## Notes

Validates application recovery behavior:
- GET /applications/{id} returns correct state after partial failure
- Recovery response includes null cv_field when cv not yet selected
- State machine recoverable from any non-terminal state
- DynamoDB reads use correct pk/sk to scope recovery to user
