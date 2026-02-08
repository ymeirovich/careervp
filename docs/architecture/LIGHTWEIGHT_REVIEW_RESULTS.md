# Lightweight Architecture Review Results

**Date:** 2026-02-07
**Reviewer:** Codex (GPT-5)
**Features Reviewed:** CV Tailoring, Cover Letter, Gap Analysis
**Reference Implementation:** VPR (Value Proposition Report)
**Review Duration:** 2.0 hours

---

## Executive Summary

**Overall Status:** BLOCKING ISSUES

**Checklist Results:**

| Check | CV Tailoring | Cover Letter | Gap Analysis | Overall |
|-------|--------------|--------------|--------------|---------|
| 1. Handler → Logic → DAL | ❌ | ✅ | ❌ | FAIL |
| 2. Result[T] Pattern | ✅ | ✅ | ❓ | FAIL |
| 3. FVS Integration | ✅ | ✅ | ✅ | PASS |
| 4. Gap Responses Input | ✅ | ✅ | ❓ | FAIL |
| 5. Sync/Async Justified | ✅ | ✅ | ❌ | FAIL |
| 6. LLM Model Selection | ✅ | ✅ | ❌ | FAIL |
| 7. Shared DAL Patterns | ✅ | ✅ | ❓ | FAIL |
| 8. AWS Powertools | ✅ | ✅ | ✅ | PASS |

**Pass Rate:** 2/8 checks passed (Target: ≥ 6/8)

**Recommendation:** REQUIRE DESIGN UPDATES

---

## Detailed Findings

### Check 1: Handler → Logic → DAL Pattern

**CV Tailoring:**
Status: FAIL
Evidence:
> "Delegates ALL business logic to CVTailoringLogic" and "NO DIRECT DAL ACCESS"
> "Handler: cv_tailoring_handler.py" and "Fetch master CV from DAL"
Issues: Architecture section forbids handler DAL access, but workflow shows handler fetching and storing via DAL.

**Cover Letter:**
Status: PASS
Evidence:
> "NO DIRECT DAL ACCESS"
> "Logic: cover_letter_generator.py" and "Fetch master CV, VPR, gap_responses from DAL"
Issues: None.

**Gap Analysis:**
Status: FAIL
Evidence:
> "Gap Analysis uses a synchronous pattern (not async)"
> "Worker Handler: `handlers/gap_analysis_worker.py`"
Issues: Sync handler pattern is documented, but async worker components remain, making layering ambiguous.

**Overall:** FAIL

---

### Check 2: Result[T] Pattern

**CV Tailoring:**
Status: PASS
Evidence:
> "Returns Result[TailoredCV]"
Issues: None.

**Cover Letter:**
Status: PASS
Evidence:
> "Return Result[TailoredCoverLetter]"
Issues: None.

**Gap Analysis:**
Status: UNCLEAR
Evidence:
> "Returns Result[list[GapQuestion]]"
Issues: Error codes are not enumerated; only `FVS_HALLUCINATION_DETECTED` appears in examples.

**Overall:** FAIL

---

### Check 3: FVS (Fact Verification System) Integration

**CV Tailoring:**
Status: PASS
Evidence:
> "IMMUTABLE: Work history dates, Company names, Job titles, Degree names"
Issues: None.

**Cover Letter:**
Status: PASS
Evidence:
> "Validate with FVS (company name, job title)"
Issues: None.

**Gap Analysis:**
Status: PASS
Evidence:
> "Validate gap questions against master CV and job description"
Issues: None.

**Overall:** PASS

---

### Check 4: Gap Responses Integration

**CV Tailoring:**
Status: PASS
Evidence:
> "gap_responses: Optional[GapAnalysisResponses] = None"
Issues: None.

**Cover Letter:**
Status: PASS
Evidence:
> "{{#if gap_responses}}"
Issues: None.

**Gap Analysis:**
Status: UNCLEAR
Evidence:
> "Gap responses are stored with the `GapResponse` model"
Issues: Storage location and `GapAnalysisResponses` container model are not defined.

**Overall:** FAIL

---

### Check 5: Sync/Async Pattern Justification

**CV Tailoring:**
Status: PASS
Evidence:
> "Decision 1: Synchronous Implementation" and "Timeout - 300 Seconds"
Issues: None.

**Cover Letter:**
Status: PASS
Evidence:
> "Decision 1: Synchronous Implementation"
> "Decision: Async Migration Trigger"
Issues: None.

**Gap Analysis:**
Status: FAIL
Evidence:
> "synchronous pattern (not async)"
> "Async worker for gap analysis processing"
Issues: Sync and async flows are both present; API spec still includes submit/status endpoints and SQS.

**Overall:** FAIL

---

### Check 6: LLM Model Selection (Sonnet vs Haiku)

**CV Tailoring:**
Status: PASS
Evidence:
> "Use Claude Haiku 4.5 (TaskMode.TEMPLATE)"
Issues: None.

**Cover Letter:**
Status: PASS
Evidence:
> "Use Claude Haiku 4.5 (TaskMode.TEMPLATE)"
Issues: None.

**Gap Analysis:**
Status: FAIL
Evidence:
> "LLM Model: Claude Sonnet 4.5 (TaskMode.STRATEGIC)"
> "Optimization: Use Claude 3 Haiku for faster responses"
Issues: Model choice is contradictory within the design and conflicts with cost tables in `plan.md`.

**Overall:** FAIL

---

### Check 7: Shared DAL Patterns

**CV Tailoring:**
Status: PASS
Evidence:
> "DAL Layer (dynamo_dal_handler.py - SHARED)"
> "DynamoDB Table: cv_tailoring_jobs" and "GSI: user_id_index"
Issues: None.

**Cover Letter:**
Status: PASS
Evidence:
> "DAL Layer (dynamo_dal_handler.py - SHARED)"
> "DynamoDB Table: cover_letter_jobs" and "GSI: user_id_index"
Issues: None.

**Gap Analysis:**
Status: UNCLEAR
Evidence:
> "DynamoDB Table: gap_analysis_jobs" and "GSI: user_id_index"
> "DynamoDB Job Record" with `gsi1pk`/`gsi1sk`
Issues: Two incompatible schemas are documented (sync table vs async job table).

**Overall:** FAIL

---

### Check 8: AWS Lambda Powertools Integration

**CV Tailoring:**
Status: PASS
Evidence:
> "from aws_lambda_powertools import Logger, Tracer, Metrics"
Issues: None.

**Cover Letter:**
Status: PASS
Evidence:
> "logger = Logger(service=\"cover-letter\")"
Issues: None.

**Gap Analysis:**
Status: PASS
Evidence:
> "logger = Logger(service=\"gap-analysis\")"
Issues: None.

**Overall:** PASS

---

## Critical Findings (Blocking Issues)

1. **Gap Analysis sync vs async contradictions**
Severity: BLOCKING. Feature(s): Gap Analysis. Description: Design and spec mix synchronous endpoint (`POST /api/gap-analysis`) with async worker/SQS and job status APIs. Impact: Conflicting implementation paths and API contracts. Recommendation: Choose sync or async, then purge the other flow from design and spec. Fix Effort: 4-6 hours.

2. **Gap Analysis model choice is inconsistent**
Severity: BLOCKING. Feature(s): Gap Analysis. Description: Design states Sonnet 4.5, but also lists Haiku optimizations and Haiku cost estimates. Plan has conflicting entries. Impact: Cost and quality targets are undefined. Recommendation: Decide a single model and update design, spec, and plan for consistency. Fix Effort: 2-3 hours.

3. **CV Tailoring layering contradiction**
Severity: BLOCKING. Feature(s): CV Tailoring. Description: Architecture section forbids handler DAL access, but workflow shows handler fetching and storing via DAL. Impact: Implementation ambiguity and divergence from VPR layering. Recommendation: Make workflow match the declared architecture, or update architecture decision explicitly. Fix Effort: 1-2 hours.

---

## Design Improvement Recommendations (Non-Blocking)

1. **Define a `GapAnalysisResponses` container model and storage location**
Severity: MAJOR. Feature(s): Gap Analysis. Description: Responses are mentioned but not stored explicitly. Benefit: Enables reuse across VPR/CV/Cover Letter. Recommendation: Add model definition and DAL persistence strategy. Fix Effort: 2-3 hours.

2. **Update the handoff prompt path**
Severity: MINOR. Feature(s): All. Description: `/docs/architecture/ARCHITECTURE_REVIEW_PLAN.md` no longer exists; file now lives under `docs/architecture/architecture-review/`. Benefit: Prevents broken review instructions. Recommendation: Update prompt or add a stub at the old path. Fix Effort: 0.5 hour.

---

## Questions for Architect

1. **Which Gap Analysis flow is authoritative: sync or async?**
Feature: Gap Analysis. Section: Architecture Pattern vs Implementation Components. Question: Should we keep sync (`POST /api/gap-analysis`) or async submit/status endpoints? Why it matters: It defines the entire API surface and infrastructure.

2. **Which model is final for Gap Analysis?**
Feature: Gap Analysis. Section: LLM Model. Question: Sonnet 4.5 or Haiku? Why it matters: Cost targets and prompt design depend on this.

3. **Where are Gap Analysis responses stored and how are they retrieved?**
Feature: Gap Analysis. Section: Response Integration. Question: Is there a `GapAnalysisResponses` artifact in DynamoDB/S3? Why it matters: Downstream features depend on it.

4. **Should CV Tailoring handler ever read/write DynamoDB directly?**
Feature: CV Tailoring. Section: Workflow. Question: Architecture says no, but workflow shows direct DAL calls. Why it matters: Consistency with VPR and testability.

---

## Action Items

**Before Implementation Can Start:**

- [ ] Resolve Gap Analysis sync vs async design/spec conflicts.
- [ ] Decide Gap Analysis model (Sonnet vs Haiku) and update all docs.
- [ ] Align CV Tailoring workflow with Handler → Logic → DAL decision.

**Optional Improvements:**

- [ ] Add `GapAnalysisResponses` container model and storage strategy.
- [ ] Update handoff prompt path for the architecture review plan.

**Design Doc Updates Required:**

- [ ] Update GAP_ANALYSIS_DESIGN.md: remove async sections or remove sync sections, standardize schema, finalize model.
- [ ] Update GAP_SPEC.md: align endpoints and remove contradictory async content.
- [ ] Update CV_TAILORING_DESIGN.md: make workflow match declared layering.
- [ ] Update LIGHTWEIGHT_REVIEW_PROMPT.md: fix review plan path or add a stub file.

---

## Sign-Off

**Reviewer Signature:** Codex (GPT-5)
**Date:** 2026-02-07

**Approval Status:** REJECTED

**Notes:** Major inconsistencies remain, primarily in Gap Analysis and CV Tailoring layering.

---

**End of Lightweight Review Results**
