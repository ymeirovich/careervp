# L0.5 — Company Research Latency Results

**Date:** 2026-02-27  
**Branch:** `beta/exec-runbk`  
**Test file:** `tests/unit/test_l0_company_research_latency.py`  
**Invariants:** I8 (partial)

## Files Updated

- `src/backend/tests/unit/test_l0_company_research_latency.py`
- `src/backend/careervp/logic/company_research.py`
- `src/backend/careervp/logic/utils/web_scraper.py`

## RED Phase (tests first)

Command:

```bash
cd src/backend && uv run pytest tests/unit/test_l0_company_research_latency.py -v --tb=short
```

Initial failure state:

- `3 failed, 1 passed`
- Failures showed:
  - scraper attempted `10` URLs instead of max `3`
  - company research logic had no `LLMResponseCache` integration (cache-hit/cached-store tests failed)

## GREEN Phase (after implementation)

Command:

```bash
cd src/backend && uv run pytest tests/unit/test_l0_company_research_latency.py -v --tb=short
```

Result:

- `4 passed, 0 failed`

## Validation Commands

```bash
cd src/backend && uv run pytest tests/unit/test_l0_company_research_latency.py -v --tb=short
cd src/backend && uv run ruff check careervp/logic/company_research.py tests/unit/test_l0_company_research_latency.py careervp/logic/utils/web_scraper.py
cd src/backend && uv run mypy careervp/logic/company_research.py --strict
```

Results:

- pytest: `4 passed`
- ruff: all checks passed
- mypy: success, no issues found

## Profiling Output (local deterministic harness)

Measured `_structure_raw_content` with an injected 250ms router and real cache flow:

- cache miss path: `0.2577s`
- cache hit path: `0.0001s`

Interpretation:

- Cache-hit bypass removes nearly all LLM structuring latency for repeated company lookups.

## Implementation Notes

- Added company-research response cache integration (`LLMResponseCache`) keyed by normalized `company_name`.
- Added cache-hit fast path to skip router invocation and return parsed `CompanyResearchResult`.
- Added cache-miss write-back with `DEFAULT_CACHE_TTL_SECONDS` (7 days).
- Enforced max `3` scrape URL attempts in `scrape_company_about_page` to cap sequential fetch latency.

## Outstanding Manual Validation

- Not yet run in this local pass: real end-to-end wall-time measurement against external company sources with p95 target `< 90s`.
