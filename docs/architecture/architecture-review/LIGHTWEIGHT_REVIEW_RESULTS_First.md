# Lightweight Architecture Review Results

**Date:** 2026-02-07
**Reviewer:** Codex (GPT-5)
**Features Reviewed:** CV Tailoring, Cover Letter, Gap Analysis
**Reference Implementation:** VPR (Value Proposition Report)
**Review Duration:** 2.5 hours

---

## Executive Summary

**Overall Status:** BLOCKING ISSUES

**Checklist Results:**

| Check | CV Tailoring | Cover Letter | Gap Analysis | Overall |
|-------|--------------|--------------|--------------|---------|
| 1. Handler → Logic → DAL | ❌ | ❌ | ❌ | FAIL |
| 2. Result[T] Pattern | ✅ | ✅ | ✅ | PASS |
| 3. FVS Integration | ✅ | ✅ | ❌ | FAIL |
| 4. Gap Responses Input | ❌ | ✅ | ❓ | FAIL |
| 5. Sync/Async Justified | ✅ | ❓ | ❌ | FAIL |
| 6. LLM Model Selection | ✅ | ✅ | ❌ | FAIL |
| 7. Shared DAL Patterns | ❓ | ❓ | ❓ | FAIL |
| 8. AWS Powertools | ❌ | ✅ | ❌ | FAIL |

**Pass Rate:** 1/8 checks passed (Target: ≥ 6/8)

**Recommendation:** REQUIRE DESIGN UPDATES

---

## Detailed Findings

### Check 1: Handler → Logic → DAL Pattern

**CV Tailoring:**
Status: FAIL
Evidence:
> "Handler: cv_tailoring_handler.py" and "Fetch master CV from DAL"
> "Logic: cv_tailoring.py" and "Return Result[TailoredCV]"
Issues: Handler directly fetches and stores via DAL, so logic is not the sole DAL consumer. This violates the VPR Handler → Logic → DAL layering rule.

**Cover Letter:**
Status: FAIL
Evidence:
> "Handler: cover_letter_handler.py" and "Fetch master CV and VPR from DAL"
> "Logic: cover_letter_generator.py" and "Return Result[TailoredCoverLetter]"
Issues: Handler accesses DAL for reads and writes; logic layer is not the sole DAL consumer.

**Gap Analysis:**
Status: FAIL
Evidence:
> "Gap Analysis follows the Async Task Pattern" and "Worker Handler: handlers/gap_analysis_worker.py"
Issues: Design does not specify submit/status handlers, and does not mention `dynamo_dal_handler.py`. Layering is incomplete and not aligned with VPR patterns.

**Overall:** FAIL

---

### Check 2: Result[T] Pattern

**CV Tailoring:**
Status: PASS
Evidence:
> "Return Result[TailoredCV]"
Issues: None.
New ResultCode values referenced in design:
1. INVALID_INPUT
2. CV_NOT_FOUND
3. JOB_DESCRIPTION_TOO_LONG
4. LLM_TIMEOUT
5. LLM_RATE_LIMITED
6. LLM_PARSE_ERROR
7. FVS_HALLUCINATION_DETECTED
8. STORAGE_ERROR
9. PARTIAL_SUCCESS

**Cover Letter:**
Status: PASS
Evidence:
> "Return Result[TailoredCoverLetter]"
Issues: None.
New ResultCode values referenced in design:
1. CV_NOT_FOUND
2. VPR_NOT_FOUND
3. CV_LETTER_GENERATION_TIMEOUT
4. FVS_HALLUCINATION_DETECTED
5. GENERATION_QUALITY_INSUFFICIENT
6. COVER_LETTER_GENERATED_SUCCESS
7. STORAGE_ERROR
8. PARTIAL_SUCCESS

**Gap Analysis:**
Status: PASS
Evidence:
> "generate_gap_questions(...) -> Result[list[GapQuestion]]"
Issues: None.
New ResultCode values referenced in design:
1. GAP_QUESTIONS_GENERATED

**Overall:** PASS

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
Status: FAIL
Evidence:
No FVS section found in Gap Analysis design.
Issues: Plan requires FVS enabled for Gap Analysis (skill verification), but design omits any validation strategy or function.

**Overall:** FAIL

---

### Check 4: Gap Responses Integration

**CV Tailoring:**
Status: FAIL
Evidence:
No `gap_responses` field found in CV Tailoring design or spec.
Issues: Missing gap responses input and prompt usage.

**Cover Letter:**
Status: PASS
Evidence:
> "Gap Responses - Optional responses to gap analysis questions"
> "{{#if gap_responses}}"
Issues: None.

**Gap Analysis:**
Status: UNCLEAR
Evidence:
> "Gap responses are stored with the GapResponse model"
Issues: Storage destination and `GapAnalysisResponses` container model are not defined.

**Overall:** FAIL

---

### Check 5: Sync/Async Pattern Justification

**CV Tailoring:**
Status: PASS
Evidence:
> "Decision 1: Synchronous Implementation"
> "Decision 3: Timeout - 300 Seconds"
Issues: None.

**Cover Letter:**
Status: UNCLEAR
Evidence:
> "Decision 1: Synchronous Implementation"
> "Decision 3: Timeout - 300 Seconds"
Issues: No explicit migration path to async if latency grows.

**Gap Analysis:**
Status: FAIL
Evidence:
> "Gap Analysis follows the Async Task Pattern"
Issues: Design is async, but plan and review checklist expect sync with <60s latency and timeout details.

**Overall:** FAIL

---

### Check 6: LLM Model Selection (Sonnet vs Haiku)

**CV Tailoring:**
Status: PASS
Evidence:
> "Decision: Use Claude Haiku 4.5 (TaskMode.TEMPLATE)"
Issues: None.

**Cover Letter:**
Status: PASS
Evidence:
> "Decision: Use Claude Haiku 4.5 (TaskMode.TEMPLATE)"
Issues: None.

**Gap Analysis:**
Status: FAIL
Evidence:
> "Use Claude 3 Haiku for faster responses"
Issues: Plan specifies Sonnet 4.5 for strategic reasoning. TaskMode and cost breakdown are not aligned with plan.

**Overall:** FAIL

---

### Check 7: Shared DAL Patterns

**CV Tailoring:**
Status: UNCLEAR
Evidence:
> "from careervp.dal.dynamo_dal_handler import DynamoDalHandler"
Issues: Table name and GSI are not specified; DAL access occurs in handler.

**Cover Letter:**
Status: UNCLEAR
Evidence:
> "from careervp.dal.dynamo_dal_handler import DynamoDalHandler"
Issues: Table name and GSI are not specified; DAL access occurs in handler.

**Gap Analysis:**
Status: UNCLEAR
Evidence:
> "DynamoDB Job Record" with gsi1 keys and ttl
Issues: No shared DAL class specified; table name and DAL access pattern not defined.

**Overall:** FAIL

---

### Check 8: AWS Lambda Powertools Integration

**CV Tailoring:**
Status: FAIL
Evidence:
No Powertools logger/tracer/metrics section found.
Issues: Observability requirements not documented.

**Cover Letter:**
Status: PASS
Evidence:
> "@logger.inject_lambda_context" and "@tracer.capture_lambda_handler"
Issues: None.

**Gap Analysis:**
Status: FAIL
Evidence:
No Powertools logger/tracer/metrics section found.
Issues: Observability requirements not documented.

**Overall:** FAIL

---

## Critical Findings (Blocking Issues)

1. **Gap Analysis design diverges from plan (async vs sync, model choice)**
Severity: BLOCKING. Feature(s): Gap Analysis. Description: Design specifies async SQS pattern and Claude 3 Haiku, but plan requires synchronous flow with Sonnet 4.5. Impact: Architectural inconsistency and incorrect model/cost assumptions. Recommendation: Align Gap Analysis design to plan or update plan explicitly with justification. Fix Effort: 4-6 hours.

2. **Missing FVS integration in Gap Analysis design**
Severity: BLOCKING. Feature(s): Gap Analysis. Description: No FVS validation strategy or function, despite plan requiring skill verification. Impact: Hallucinated skills and invalid questions. Recommendation: Add FVS integration section with validation rules and function signatures. Fix Effort: 2-3 hours.

3. **Gap responses integration missing in CV Tailoring**
Severity: BLOCKING. Feature(s): CV Tailoring. Description: No `gap_responses` input or prompt usage, contradicting plan data flow. Impact: Reduced output quality and roadmap mismatch. Recommendation: Add optional `gap_responses` input and prompt usage in design and spec. Fix Effort: 2-3 hours.

4. **Handler → Logic → DAL layering not followed**
Severity: BLOCKING. Feature(s): CV Tailoring, Cover Letter. Description: Handlers directly access DAL for reads and writes. Impact: Inconsistent architecture vs VPR, harder testing and reuse. Recommendation: Move DAL access into logic layer or explicitly update architecture pattern decision. Fix Effort: 3-5 hours.

---

## Design Improvement Recommendations (Non-Blocking)

1. **Define explicit DynamoDB table names and GSI conventions**
Severity: MINOR. Feature(s): CV Tailoring, Cover Letter, Gap Analysis. Description: Table names and GSIs are not documented consistently. Benefit: Clear infra implementation and consistent query patterns. Recommendation: Add table name, GSI names, and key schema to each design. Fix Effort: 1-2 hours.

2. **Add Powertools observability requirements for CV Tailoring and Gap Analysis**
Severity: MINOR. Feature(s): CV Tailoring, Gap Analysis. Description: Logger/Tracer/Metrics not specified. Benefit: Standardized observability and easier debugging. Recommendation: Add a short observability section with decorators and metric names. Fix Effort: 1-2 hours.

3. **Clarify async migration path for Cover Letter**
Severity: MINOR. Feature(s): Cover Letter. Description: No documented fallback if sync latency grows. Benefit: Future-proofing for longer prompts or research content. Recommendation: Add migration trigger conditions and async alternative. Fix Effort: 1 hour.

---

## Questions for Architect

1. **Should Gap Analysis be synchronous or asynchronous?**
Feature: Gap Analysis. Section: Architecture Pattern. Question: Plan says sync (<60s) but design is async. Which is authoritative? Why it matters: Drives infrastructure, API design, and UX.

2. **Which LLM model is required for Gap Analysis?**
Feature: Gap Analysis. Section: Optimization. Question: Plan calls for Sonnet 4.5, design mentions Claude 3 Haiku. Which is correct? Why it matters: Cost, latency, and output quality targets.

3. **How should `gap_responses` be passed into CV Tailoring?**
Feature: CV Tailoring. Section: Input Schema / Prompt Strategy. Question: Should responses come from request payload or be fetched from DAL? Why it matters: API spec and data flow alignment.

4. **Where should DAL access live for sync handlers?**
Feature: CV Tailoring, Cover Letter. Section: Workflow. Question: Should handlers call DAL directly or delegate to logic (VPR pattern)? Why it matters: Consistent layering and testability.

5. **What are the canonical DynamoDB table names and GSI names for these features?**
Feature: All. Section: Storage Strategy. Question: Not specified in designs. Why it matters: CDK implementation and consistent query patterns.

---

## Action Items

**Before Implementation Can Start:**

- [ ] Align Gap Analysis design with plan (sync vs async, Sonnet vs Haiku).
- [ ] Add FVS integration section to Gap Analysis design.
- [ ] Add `gap_responses` input and prompt usage to CV Tailoring design and spec.
- [ ] Resolve Handler → Logic → DAL layering inconsistencies for CV Tailoring and Cover Letter.

**Optional Improvements:**

- [ ] Add explicit table names and GSI definitions to all three designs.
- [ ] Add Powertools observability details to CV Tailoring and Gap Analysis designs.
- [ ] Add async migration trigger for Cover Letter design.

**Design Doc Updates Required:**

- [ ] Update CV_TAILORING_DESIGN.md: add `gap_responses` input usage, clarify DAL layering, add observability.
- [ ] Update CV_TAILORING_SPEC.md: add `gap_responses` to request model.
- [ ] Update COVER_LETTER_DESIGN.md: clarify DAL layering and async migration trigger.
- [ ] Update COVER_LETTER_SPEC.md: add `gap_responses` to request model or document DAL retrieval.
- [ ] Update GAP_ANALYSIS_DESIGN.md: align sync/async, model selection, FVS integration, DAL usage.
- [ ] Update GAP_SPEC.md: confirm model choice and FVS requirements.

---

## Sign-Off

**Reviewer Signature:** Codex (GPT-5)
**Date:** 2026-02-07

**Approval Status:** REJECTED

**Notes:** Design updates required before implementation to align with plan.md and VPR reference patterns.

---

**End of Lightweight Review Results**
