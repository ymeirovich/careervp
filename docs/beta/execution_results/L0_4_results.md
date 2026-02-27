# L0.4 — CV Tailoring Scores Results

**Date:** 2026-02-27
**Test file:** `tests/unit/test_l0_cv_tailoring_scores.py`
**Invariants:** I1, I2

## Summary

| Status | Count |
|--------|-------|
| PASSED | 18    |
| FAILED | 0     |
| ERRORS | 0     |

**Result: GREEN ✓**

## Test Classes

| Class | Tests | Status |
|-------|-------|--------|
| TestCVTailoringCvIdNotNull | 3 | PASSED |
| TestCVTailoringATSScore | 5 | PASSED |
| TestCVTailingSelfCorrectionLoop | 10 | PASSED |

## Notes

Validates:
- cv_id non-null after tailoring (fixes live-test-results3.log bug)
- ATS score >= 8.0, anti-AI score >= 9.0 after self-correction
- Self-correction loop triggers on low scores (max 3 iterations)
- No template strings `{cv_content}`, `{job_description}`, `[INSERT`, `{{`, `<placeholder>` in output
- DynamoDB sk uses `ARTIFACT#CV_TAILORED#` prefix (I2 invariant)
