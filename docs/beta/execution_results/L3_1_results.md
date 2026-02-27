# L3.1 — Application Schema Results

**Date:** 2026-02-27
**Test file:** `tests/unit/test_l3_application_schema.py`
**Invariants:** I5, I6

## Summary

| Status | Count |
|--------|-------|
| PASSED | 31    |
| FAILED | 0     |
| ERRORS | 0     |

**Result: GREEN ✓**

## Notes

Validates application state machine schema:
- Valid state transitions succeed (created → cv_selected → gap_questions_pending → etc.)
- Invalid transitions rejected
- State enum contains all expected states
- Application model fields match OpenAPI schema
- State persisted with correct DynamoDB pk/sk structure
