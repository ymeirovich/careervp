# Documentation Update Plan - Post-Review Consolidation

**Date:** 2026-02-07
**Author:** Claude Opus 4.5 (Principal Architect)
**Status:** READY FOR EXECUTION
**Priority:** P0 - BLOCKING (Implementation cannot proceed until resolved)

---

## Executive Summary

### Validation Results

| Reviewer | Findings | Status |
|----------|----------|--------|
| **Codex (GPT-5)** | 3 blocking issues identified | ✅ VALIDATED |
| **Minimax** | 1 fix applied, 2 issues remain | ✅ VALIDATED |

### Current State of Blocking Issues

| Issue | Status | Evidence |
|-------|--------|----------|
| 1. Gap Analysis sync/async contradiction | ❌ **NOT RESOLVED** | Lines 20-54 say sync, Lines 593-610 have async worker |
| 2. Gap Analysis model choice (Haiku vs Sonnet) | ✅ **RESOLVED by Minimax** | Line 668 now says Sonnet 4.5 |
| 3. CV Tailoring layering contradiction | ❌ **NOT RESOLVED** | Lines 164-185 forbid Handler→DAL, Lines 440,462 show Handler→DAL |

---

## Issue 1: Gap Analysis Sync/Async Contradiction

### Current Contradictions in GAP_ANALYSIS_DESIGN.md

| Section | Line(s) | What It Says | Pattern |
|---------|---------|--------------|---------|
| Architecture Pattern | 20-54 | "Gap Analysis uses a **synchronous pattern**" | SYNC |
| Handler Layer | 24-29 | "gap_analysis_handler.py" | SYNC |
| Synchronous Flow | 44-54 | `POST /api/gap-analysis → 200 OK` | SYNC |
| Worker Handler | 593-610 | `GapAnalysisWorker(AsyncTaskHandler)` | **ASYNC** |
| Concurrency | 670-673 | "SQS batch size: 1 (one job per worker)" | **ASYNC** |
| Data Privacy | 688-689 | "S3 results use presigned URLs" | **ASYNC** |

### Decision: Keep SYNCHRONOUS (per NEXT_STEPS Decision 1)

**Rationale:**
- Sonnet 4.5 latency: 30-60 seconds (well under 600s timeout)
- Consistency with CV Tailoring and Cover Letter
- Simpler implementation and UX (no polling)

### Required Changes

#### Section 3 (Lines 593-610): Remove Async Worker

**DELETE:**
```markdown
### 3. Worker Handler: `handlers/gap_analysis_worker.py`

```python
from careervp.handlers.utils.async_task import AsyncTaskHandler
from careervp.logic.gap_analysis import generate_gap_questions

class GapAnalysisWorker(AsyncTaskHandler):
    """Async worker for gap analysis processing."""

    async def process(self, job_id: str, request: GapAnalysisRequest) -> Result[dict]:
        """
        Execute gap analysis logic.

        1. Retrieve user CV from DAL
        2. Call generate_gap_questions()
        3. Return result
        """
```
```

**REPLACE WITH:** Nothing (delete entire section, renumber subsequent sections)

#### Concurrency Section (Lines 670-673): Update to Sync Pattern

**CURRENT:**
```markdown
### Concurrency
- **SQS batch size:** 1 (one job per worker invocation)
- **Max concurrent workers:** 10 (configurable)
- **Rate limiting:** Respect Claude API rate limits
```

**REPLACE WITH:**
```markdown
### Concurrency
- **Lambda timeout:** 600 seconds (handles sync request)
- **Max concurrent invocations:** 100 (AWS default, configurable)
- **Rate limiting:** Respect Claude API rate limits
```

#### Data Privacy Section (Lines 688-689): Remove Presigned URLs

**CURRENT:**
```markdown
- S3 results use presigned URLs (expire in 1 hour)
```

**REPLACE WITH:**
```markdown
- Questions returned directly in API response (no S3 storage needed for sync)
- Gap responses stored in DynamoDB with 90-day TTL
```

### Estimated Effort: 1-2 hours

---

## Issue 2: Gap Analysis Model Choice - RESOLVED

### Verification

Minimax applied the following edits:

| Line | Before | After |
|------|--------|-------|
| 666 | "Expected: 15-30 seconds" | "Expected: 30-60 seconds" |
| 668 | "Use Claude 3 Haiku for faster responses" | "Use Claude Sonnet 4.5 (TaskMode.STRATEGIC)" |
| 677 | "~$0.01 (with Haiku)" | "~$0.05 (with Sonnet 4.5)" |

**Status:** ✅ No further action required

---

## Issue 3: CV Tailoring Layering Contradiction

### Current Contradictions in CV_TAILORING_DESIGN.md

| Section | Line(s) | What It Says | Layering |
|---------|---------|--------------|----------|
| Architecture Pattern | 164-185 | "NO DIRECT DAL ACCESS" in handler | Handler → Logic → DAL |
| Workflow - Handler | 440 | "Fetch master CV from DAL" | **Handler → DAL** |
| Workflow - Handler | 462 | "Store tailored CV as artifact in DAL" | **Handler → DAL** |

### Decision: Enforce Strict Layering (per NEXT_STEPS Decision 3)

**Rationale:**
- Consistency with VPR reference implementation
- Better testability (logic layer can be tested without DAL mocking in handler tests)
- Reusability (logic can be called from other contexts)

### Required Changes

#### Workflow Diagram (Lines 437-464): Move DAL to Logic Layer

**CURRENT:**
```markdown
┌─────────────────────────────────────────────────────────────┐
│ Handler: cv_tailoring_handler.py                            │
│  - Validate request (Pydantic)                              │
│  - Fetch master CV from DAL                                 │  ← DAL ACCESS
│  - Fetch job description (or parse from request)            │
│  - Call tailor_cv() logic                                   │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ Logic: cv_tailoring.py                                       │
│  1. Extract job requirements (keywords, skills, seniority)  │
│  2. Score each CV section for relevance                     │
│  3. Build tailoring prompt with scored sections             │
│  4. Call LLM (Haiku 4.5) to generate tailored CV            │
│  5. Parse LLM response into TailoredCV model                │
│  6. Validate with FVS (fvs_validator.py)                    │
│  7. Return Result[TailoredCV]                               │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ Handler: cv_tailoring_handler.py                            │
│  - Check FVS validation result                              │
│  - If CRITICAL violations: return 400 Bad Request           │
│  - Store tailored CV as artifact in DAL                     │  ← DAL ACCESS
│  - Return TailoredCVResponse with download URL              │
└─────────────────────────────────────────────────────────────┘
```

**REPLACE WITH:**
```markdown
┌─────────────────────────────────────────────────────────────┐
│ Handler: cv_tailoring_handler.py                            │
│  - Validate request (Pydantic)                              │
│  - Initialize CVTailoringLogic with dependencies            │
│  - Call logic.tailor_cv(request)                            │
│  - Format and return HTTP response                          │
│  - NO DIRECT DAL ACCESS                                     │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ Logic: cv_tailoring_logic.py                                 │
│  1. Fetch master CV from DAL                                │  ← DAL ACCESS (via injected dal)
│  2. Extract job requirements (keywords, skills, seniority)  │
│  3. Score each CV section for relevance                     │
│  4. Build tailoring prompt with scored sections             │
│  5. Call LLM (Haiku 4.5) to generate tailored CV            │
│  6. Parse LLM response into TailoredCV model                │
│  7. Validate with FVS (fvs_validator.py)                    │
│  8. If CRITICAL violations: return Result(error=...)        │
│  9. Store tailored CV via DAL                               │  ← DAL ACCESS (via injected dal)
│ 10. Return Result[TailoredCV]                               │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ Handler: cv_tailoring_handler.py                            │
│  - Unwrap Result[TailoredCV]                                │
│  - If error: return appropriate HTTP error                  │
│  - Return TailoredCVResponse with download URL              │
└─────────────────────────────────────────────────────────────┘
```

### Estimated Effort: 1 hour

---

## Additional Updates (from PIPELINE_ANALYSIS_RESULTS.md)

### Gap Responses Backend Storage

**Finding:** Current design lacks persistent storage for gap responses. Request payload approach works for single application but CANNOT support cross-application reuse without backend storage.

**Action Required:** Add to GAP_ANALYSIS_DESIGN.md:

```markdown
## Gap Responses Storage

### DynamoDB Schema (Users Table - Extended)

| Attribute | Type | Description |
|-----------|------|-------------|
| pk | String | `user_id` (partition key) |
| sk | String | `RESPONSE#{question_id}` (sort key) |
| question_id | String | Unique question identifier |
| question | String | Question text |
| answer | String | User's answer |
| destination | String | `CV_IMPACT` or `INTERVIEW_MVP_ONLY` |
| application_id | String | Application that generated question |
| created_at | String | ISO timestamp |
| ttl | Number | Unix timestamp (90-day expiration) |

### API Endpoints

**POST /api/gap-responses** - Store new responses
**GET /api/gap-responses?user_id={id}** - Retrieve all responses
```

### Estimated Effort: 2-3 hours (includes spec update)

---

## Update Execution Checklist

### Phase 1: Fix Blocking Issues (4-6 hours total)

#### GAP_ANALYSIS_DESIGN.md
- [ ] Delete Section 3 (Async Worker Handler) - Lines 593-610
- [ ] Update Concurrency section - Lines 670-673
- [ ] Update Data Privacy section - Lines 688-689
- [ ] Add Gap Responses Storage section (new)
- [ ] Verify no remaining async references

#### CV_TAILORING_DESIGN.md
- [ ] Update Workflow diagram - Lines 437-464
- [ ] Verify consistency with Architecture Pattern section

### Phase 2: Update Specs (1-2 hours)

#### GAP_SPEC.md
- [ ] Remove async submit/status endpoints (if present)
- [ ] Add gap responses endpoints
- [ ] Verify sync API pattern

### Phase 3: Re-Run Lightweight Review (1 hour)

- [ ] Execute all 8 checklist items
- [ ] Document results in LIGHTWEIGHT_REVIEW_RESULTS_V2.md
- [ ] Verify ≥ 6/8 pass rate
- [ ] Confirm zero blocking issues

---

## Validation Summary

| Source | Issue | Valid? | Status |
|--------|-------|--------|--------|
| Codex | Gap Analysis sync/async | ✅ Yes | Fix pending |
| Codex | Gap Analysis model Haiku/Sonnet | ✅ Yes | ✅ FIXED by Minimax |
| Codex | CV Tailoring layering | ✅ Yes | Fix pending |
| Minimax | Same 3 issues | ✅ Yes | 1 fixed, 2 pending |
| Pipeline | Gap Responses storage | ✅ Yes | New requirement |

---

## Next Steps

1. **IMMEDIATE:** Apply the fixes documented in this plan
2. **THEN:** Re-run lightweight review to confirm all issues resolved
3. **THEN:** Proceed with CV Tailoring implementation (Phase 9)

---

## Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-07 | 1.0 | Claude Opus 4.5 | Initial update plan after validating Codex/Minimax findings |

---

**End of Documentation Update Plan**
