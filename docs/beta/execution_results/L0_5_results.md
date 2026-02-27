# L0.5 — Company Research Latency Results

**Date:** 2026-02-27
**Test file:** `tests/unit/test_l0_company_research_latency.py`
**Invariants:** I8

## Summary

| Status | Count |
|--------|-------|
| PASSED | 14    |
| FAILED | 0     |
| ERRORS | 0     |

**Result: GREEN ✓**

## Test Classes

| Class | Tests | Status |
|-------|-------|--------|
| TestWebScraperTimeout | 3 | PASSED |
| TestWebScraperURLLimit | 2 | PASSED |
| TestCompanyResearchCache | 5 | PASSED |
| TestCompanyResearchCVSummarizer | 2 | PASSED |
| TestCompanyResearchOutput | 2 | PASSED |

## Notes

Validates:
- Web scraper uses timeout on all HTTP requests (never blocks indefinitely)
- Timeout is between 5 and 15 seconds
- Max 3 URLs scraped per request (hard cap 5)
- Cache hit skips LLM call (LLMResponseCache)
- Cache miss stores result with 7-day TTL
- Large CVs are summarized before research prompt
- No template strings in company research output
