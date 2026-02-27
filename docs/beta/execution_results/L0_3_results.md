# L0.3 — Gap Analysis Generation Results

**Date:** 2026-02-27
**Test file:** `tests/unit/test_l0_gap_analysis_generation.py`
**Invariants:** I1, I2

## Summary

| Status | Count |
|--------|-------|
| PASSED | 16    |
| FAILED | 0     |
| ERRORS | 0     |

**Result: GREEN ✓**

## Test Classes

| Class | Tests | Status |
|-------|-------|--------|
| TestGapAnalysisCallsLLM | 4 | PASSED |
| TestGapAnalysisOutputShape | 4 | PASSED |
| TestGapAnalysisPromptIntegrity | 4 | PASSED |
| TestGapAnalysisErrorHandling | 4 | PASSED |

## Notes

All assertions verify:
- LLM invoked with CV and job description content
- Output shape matches OpenAPI gap-analysis contract
- No template strings in generated output
- Error handling (LLM failure, circuit breaker, missing CV)
