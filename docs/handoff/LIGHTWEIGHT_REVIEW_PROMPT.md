# Lightweight Architecture Review - Engineer Handoff Prompt

**Date:** 2026-02-07
**Review Type:** Pre-Implementation Consistency Check
**Duration:** 2-3 hours
**Deliverable:** `/docs/architecture/LIGHTWEIGHT_REVIEW_RESULTS.md`

---

## 🎯 MISSION STATEMENT

You are conducting a **Lightweight Architecture Review** of three unimplemented CareerVP features (CV Tailoring, Cover Letter, Gap Analysis) to ensure design-level consistency with the proven VPR implementation **BEFORE** any code is written.

Your role is to **validate architectural alignment**, not to write code. Think of yourself as a **junior engineer reviewing senior architect's designs** before implementation begins.

---

## 📚 REQUIRED READING (45 minutes - DO NOT SKIP)

Read these documents in order before starting the review:

### 1. Review Framework
- [ ] **`/docs/architecture/ARCHITECTURE_REVIEW_PLAN.md`** - Complete review methodology (read entire document)

### 2. VPR Reference Implementation (Your Comparison Baseline)
- [ ] **`/docs/architecture/VPR_ASYNC_DESIGN.md`** - VPR architecture (proven pattern)
- [ ] **`/src/backend/careervp/handlers/vpr_submit_handler.py`** - Handler pattern
- [ ] **`/src/backend/careervp/logic/vpr_generator.py`** - Logic pattern
- [ ] **`/src/backend/careervp/dal/dynamo_dal_handler.py`** - DAL pattern

### 3. Features Under Review (Designs Only - No Code Yet)
- [ ] **`/docs/architecture/CV_TAILORING_DESIGN.md`** - CV Tailoring design
- [ ] **`/docs/architecture/COVER_LETTER_DESIGN.md`** - Cover Letter design
- [ ] **`/docs/architecture/GAP_ANALYSIS_DESIGN.md`** - Gap Analysis design

### 4. Supporting Documentation
- [ ] **`/docs/specs/cv-tailoring/CV_TAILORING_SPEC.md`** - CV Tailoring API spec
- [ ] **`/docs/specs/cover-letter/COVER_LETTER_SPEC.md`** - Cover Letter API spec
- [ ] **`/docs/specs/gap-analysis/GAP_SPEC.md`** - Gap Analysis API spec

**Total Reading:** ~100 pages (~45 minutes at 2 pages/minute)

---

## 🚫 WHAT YOU ARE NOT DOING

**This is NOT a code review.** You are reviewing **design documents**, not implementation code.

**Do NOT:**
- ❌ Write implementation code
- ❌ Run tests or build infrastructure
- ❌ Critique code quality (no code exists yet!)
- ❌ Assess performance or security in detail (that's Phase 2)
- ❌ Use LSP tools (no code to analyze yet)

**DO:**
- ✅ Check if design docs are comprehensive enough to implement
- ✅ Verify all three features follow VPR's proven patterns
- ✅ Identify design-level inconsistencies before they become code
- ✅ Flag missing sections in design docs
- ✅ Ask clarifying questions about ambiguous designs

---

## 📋 8-POINT CHECKLIST (Your Deliverable)

For each of the 8 checks below, evaluate all three features (CV Tailoring, Cover Letter, Gap Analysis) and mark as:
- ✅ **PASS** - Design clearly specifies this, consistent with VPR
- ❌ **FAIL** - Design missing this, or inconsistent with VPR
- ❓ **UNCLEAR** - Design mentions this but lacks detail

---

### ✅ Check 1: Handler → Logic → DAL Pattern Consistency

**Question:** Do all three features follow the same layered architecture as VPR?

**VPR Reference Pattern:**
```
VPR Submit Handler (vpr_submit_handler.py)
  ↓ validates input, creates job record, sends to SQS
VPR Worker Handler (vpr_worker_handler.py)
  ↓ processes SQS message, calls logic layer
VPR Generator Logic (vpr_generator.py)
  ↓ LLM calls, business rules, FVS validation
DAL Handler (dynamo_dal_handler.py)
  ↓ DynamoDB operations (put_item, get_item, query_by_gsi)
```

**What to Check in Design Docs:**

For **CV Tailoring**:
1. Open `/docs/architecture/CV_TAILORING_DESIGN.md`
2. Search for "Architecture Components" or "Class Structure" section
3. Verify it specifies:
   - `cv_tailor_handler.py` (Handler layer)
   - `cv_tailoring_logic.py` (Logic layer)
   - Uses shared `dynamo_dal_handler.py` (DAL layer)
4. Check: Does Handler call Logic? Does Logic call DAL? (No cross-layer jumps?)

For **Cover Letter**:
1. Open `/docs/architecture/COVER_LETTER_DESIGN.md`
2. Search for "Architecture Components" or "Class Structure" section
3. Verify it specifies:
   - `cover_letter_handler.py` (Handler layer)
   - `cover_letter_logic.py` (Logic layer)
   - Uses shared `dynamo_dal_handler.py` (DAL layer)

For **Gap Analysis**:
1. Open `/docs/architecture/GAP_ANALYSIS_DESIGN.md`
2. Search for "Architecture Components" or "Class Structure" section
3. Verify it specifies:
   - `gap_analysis_handler.py` (Handler layer)
   - `gap_analysis_logic.py` (Logic layer)
   - Uses shared `dynamo_dal_handler.py` (DAL layer)

**Fill Out:**
```markdown
| Feature | Handler | Logic | DAL | Status |
|---------|---------|-------|-----|--------|
| CV Tailoring | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | PASS/FAIL/UNCLEAR |
| Cover Letter | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | PASS/FAIL/UNCLEAR |
| Gap Analysis | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | PASS/FAIL/UNCLEAR |
```

**Evidence to Capture:**
- Quote the section from design doc that specifies the layers
- Note any deviations from VPR pattern

**Risk if FAIL:** Architectural inconsistency, difficult refactoring later

---

### ✅ Check 2: Result[T] Pattern Usage

**Question:** Do all three features use `Result[T]` for error handling like VPR?

**VPR Reference Pattern:**
```python
from careervp.models.result import Result, ResultCode

async def generate_vpr(...) -> Result[VPRResult]:
    """Generate VPR using LLM."""
    if validation_failed:
        return Result(
            success=False,
            error="Validation error message",
            code=ResultCode.INVALID_INPUT
        )

    try:
        vpr_result = await llm_client.generate(...)
        return Result(success=True, data=vpr_result)
    except Exception as e:
        logger.error(f"VPR generation failed: {e}")
        return Result(
            success=False,
            error="Internal error",
            code=ResultCode.INTERNAL_ERROR
        )
```

**What to Check in Design Docs:**

For **CV Tailoring**:
1. Open `/docs/architecture/CV_TAILORING_DESIGN.md`
2. Search for "Error Handling" or "Result Pattern" section
3. Look for function signatures like:
   ```python
   async def tailor_cv(...) -> Result[TailoredCV]:
   ```
4. Check: Are error cases wrapped in `Result(success=False, ...)`?

For **Cover Letter**:
1. Open `/docs/architecture/COVER_LETTER_DESIGN.md`
2. Search for "Error Handling" section
3. Look for function signatures like:
   ```python
   async def generate_cover_letter(...) -> Result[CoverLetter]:
   ```

For **Gap Analysis**:
1. Open `/docs/architecture/GAP_ANALYSIS_DESIGN.md`
2. Search for "Error Handling" section
3. Look for function signatures like:
   ```python
   async def generate_gap_questions(...) -> Result[GapAnalysisQuestions]:
   ```

**Fill Out:**
```markdown
| Feature | Uses Result[T] | Error Codes Defined | Status |
|---------|----------------|---------------------|--------|
| CV Tailoring | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | PASS/FAIL/UNCLEAR |
| Cover Letter | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | PASS/FAIL/UNCLEAR |
| Gap Analysis | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | PASS/FAIL/UNCLEAR |
```

**Evidence to Capture:**
- Quote function signatures showing `-> Result[T]`
- List any new `ResultCode` enum values needed

**Risk if FAIL:** Inconsistent error handling, difficult debugging

---

### ✅ Check 3: FVS (Fact Verification System) Integration

**Question:** Is FVS integration strategy consistent and appropriate for each feature?

**VPR Reference:**
- VPR: ❌ **DISABLED** (false positives on target company mentions)
- CV Tailoring: ✅ **ENABLED** (preserve IMMUTABLE facts from master CV)
- Cover Letter: ✅ **ENABLED** (verify company/job title matches input)
- Gap Analysis: ✅ **ENABLED** (verify skills mentioned exist in CV)

**What to Check in Design Docs:**

For **CV Tailoring**:
1. Open `/docs/architecture/CV_TAILORING_DESIGN.md`
2. Search for "FVS Integration" or "Validation Strategy" section
3. Check:
   - Is FVS mentioned?
   - What facts are IMMUTABLE? (dates, companies, job titles, degrees)
   - What facts are MUTABLE? (descriptions, achievements)
4. Look for function like:
   ```python
   def validate_tailored_cv_against_master(
       tailored_cv: TailoredCV,
       master_cv: UserCV
   ) -> Result[bool]:
   ```

For **Cover Letter**:
1. Open `/docs/architecture/COVER_LETTER_DESIGN.md`
2. Search for "FVS Integration" section
3. Check:
   - Does it validate company name matches input?
   - Does it validate job title matches input?
   - Does it prevent hallucinated achievements?

For **Gap Analysis**:
1. Open `/docs/architecture/GAP_ANALYSIS_DESIGN.md`
2. Search for "FVS Integration" section
3. Check:
   - Does it verify skills mentioned in questions exist in CV?
   - Does it prevent questions about non-existent experience?

**Fill Out:**
```markdown
| Feature | FVS Enabled | IMMUTABLE Facts Defined | Validation Function Specified | Status |
|---------|-------------|-------------------------|-------------------------------|--------|
| CV Tailoring | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | PASS/FAIL/UNCLEAR |
| Cover Letter | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | PASS/FAIL/UNCLEAR |
| Gap Analysis | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | PASS/FAIL/UNCLEAR |
```

**Evidence to Capture:**
- List IMMUTABLE facts for each feature
- Quote validation function signatures

**Risk if FAIL:** Data integrity issues, hallucinated content, compliance violations

---

### ✅ Check 4: Gap Responses Integration

**Question:** Do all three features accept `gap_responses` as input to enrich output quality?

**Context from plan.md:**
> All Gap Analysis and Interview Prep responses are stored and reused across applications:
> - Current Gap Analysis Responses → VPR, Tailored CV, Cover Letter
> - Previous Gap Analysis Responses → VPR, Tailored CV, Cover Letter (enriches evidence)

**What to Check in Design Docs:**

For **CV Tailoring**:
1. Open `/docs/architecture/CV_TAILORING_DESIGN.md`
2. Search for "Input Schema" or "Data Flow" section
3. Check: Is `gap_responses: Optional[GapAnalysisResponses]` in the input?
4. Search for "LLM Prompt Strategy" section
5. Check: Does the prompt include gap responses to provide evidence?

For **Cover Letter**:
1. Open `/docs/architecture/COVER_LETTER_DESIGN.md`
2. Search for "Input Schema" section
3. Check: Is `gap_responses: Optional[GapAnalysisResponses]` in the input?
4. Check: Does the LLM prompt use gap responses to provide specific examples?

For **Gap Analysis**:
1. Open `/docs/architecture/GAP_ANALYSIS_DESIGN.md`
2. Check: Does it specify storing responses for future reuse?
3. Check: Is there a `GapAnalysisResponses` data model defined?

**Fill Out:**
```markdown
| Feature | Accepts gap_responses Input | Uses in LLM Prompt | Stores for Reuse | Status |
|---------|----------------------------|-------------------|------------------|--------|
| CV Tailoring | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | N/A | PASS/FAIL/UNCLEAR |
| Cover Letter | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | N/A | PASS/FAIL/UNCLEAR |
| Gap Analysis | N/A | N/A | ✅ / ❌ / ❓ | PASS/FAIL/UNCLEAR |
```

**Evidence to Capture:**
- Quote input schema showing `gap_responses` field
- Quote LLM prompt section showing how gap responses are used

**Risk if FAIL:** Missing critical context, reduced output quality, feature doesn't meet roadmap requirements

---

### ✅ Check 5: Synchronous vs Async Pattern Justification

**Question:** Is the sync/async decision justified based on expected latency?

**VPR Reference:**
- VPR: **ASYNC** (SQS + Polling) - Sonnet 4.5, strategic reasoning, 30-120 seconds
- CV Tailoring: **SYNC** (Direct Lambda) - Haiku 4.5, templating, < 30 seconds
- Cover Letter: **SYNC** (Direct Lambda) - Haiku 4.5, templating, < 20 seconds
- Gap Analysis: **SYNC** (Direct Lambda) - Sonnet 4.5, question generation, < 60 seconds

**What to Check in Design Docs:**

For **CV Tailoring**:
1. Open `/docs/architecture/CV_TAILORING_DESIGN.md`
2. Search for "Architectural Decisions" section
3. Look for decision: "Synchronous vs Async Implementation"
4. Check:
   - Is synchronous choice justified?
   - Is expected latency specified? (should be < 30 seconds)
   - Is timeout value specified? (e.g., 300 seconds via `asyncio.wait_for()`)
   - Is migration path to async documented if latency exceeds 30s?

For **Cover Letter**:
1. Open `/docs/architecture/COVER_LETTER_DESIGN.md`
2. Search for "Synchronous Implementation" decision
3. Check:
   - Expected latency < 20 seconds?
   - Timeout value specified?

For **Gap Analysis**:
1. Open `/docs/architecture/GAP_ANALYSIS_DESIGN.md`
2. Search for "Synchronous Implementation" decision
3. Check:
   - Expected latency < 60 seconds?
   - Timeout value specified?

**Fill Out:**
```markdown
| Feature | Pattern | Expected Latency | Timeout Configured | Migration Path | Status |
|---------|---------|------------------|-------------------|----------------|--------|
| CV Tailoring | SYNC/ASYNC | [X seconds] | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | PASS/FAIL/UNCLEAR |
| Cover Letter | SYNC/ASYNC | [X seconds] | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | PASS/FAIL/UNCLEAR |
| Gap Analysis | SYNC/ASYNC | [X seconds] | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | PASS/FAIL/UNCLEAR |
```

**Evidence to Capture:**
- Quote latency estimates from design docs
- Quote timeout configuration

**Risk if FAIL:** Timeout failures in production, poor UX, wasted infrastructure investment

---

### ✅ Check 6: LLM Model Selection (Sonnet vs Haiku)

**Question:** Are LLM model choices justified and cost-effective?

**Hybrid AI Strategy (from plan.md):**
- **Sonnet 4.5:** Strategic tasks requiring reasoning (VPR, Gap Analysis questions)
- **Haiku 4.5:** Template-based tasks (CV Tailoring, Cover Letter, Interview Prep)

**Pricing:**
- Haiku 4.5: $0.25 input / $1.25 output per MTok
- Sonnet 4.5: $3.00 input / $15.00 output per MTok

**What to Check in Design Docs:**

For **CV Tailoring**:
1. Open `/docs/architecture/CV_TAILORING_DESIGN.md`
2. Search for "LLM Model" decision
3. Check:
   - Model: Claude Haiku 4.5? (should be, for cost optimization)
   - TaskMode: TEMPLATE? (not STRATEGIC)
   - Cost estimate provided?
   - Target: $0.005-0.010 per tailoring?

For **Cover Letter**:
1. Open `/docs/architecture/COVER_LETTER_DESIGN.md`
2. Search for "LLM Model" decision
3. Check:
   - Model: Claude Haiku 4.5?
   - TaskMode: TEMPLATE?
   - Cost estimate: $0.004-0.006 per letter?

For **Gap Analysis**:
1. Open `/docs/architecture/GAP_ANALYSIS_DESIGN.md`
2. Search for "LLM Model" decision
3. Check:
   - Model: Claude Sonnet 4.5? (should be, for strategic reasoning)
   - TaskMode: STRATEGIC?
   - Cost estimate provided?

**Fill Out:**
```markdown
| Feature | Model | TaskMode | Cost Estimate | Fallback Strategy | Status |
|---------|-------|----------|---------------|-------------------|--------|
| CV Tailoring | Haiku/Sonnet | TEMPLATE/STRATEGIC | $X.XXX | ✅ / ❌ / ❓ | PASS/FAIL/UNCLEAR |
| Cover Letter | Haiku/Sonnet | TEMPLATE/STRATEGIC | $X.XXX | ✅ / ❌ / ❓ | PASS/FAIL/UNCLEAR |
| Gap Analysis | Haiku/Sonnet | TEMPLATE/STRATEGIC | $X.XXX | ✅ / ❌ / ❓ | PASS/FAIL/UNCLEAR |
```

**Evidence to Capture:**
- Quote model selection justification
- Quote cost calculations

**Risk if FAIL:** Cost overruns, poor quality output, wrong model for task type

---

### ✅ Check 7: Shared DAL Patterns

**Question:** Do all features use the same DAL interface and DynamoDB access patterns?

**VPR Reference:**
```python
from careervp.dal.dynamo_dal_handler import DynamoDALHandler

# VPR uses these DAL methods:
dal.put_item(table_name="vpr_jobs", item={...})
dal.get_item(table_name="vpr_jobs", key={"job_id": "..."})
dal.update_item(table_name="vpr_jobs", key={...}, updates={...})
dal.query_by_gsi(table_name="vpr_jobs", gsi_name="user-id-index", key_value="...")
```

**What to Check in Design Docs:**

For **CV Tailoring**:
1. Open `/docs/architecture/CV_TAILORING_DESIGN.md`
2. Search for "DynamoDB Access" or "Data Storage" section
3. Check:
   - Uses shared `DynamoDALHandler`? (not custom boto3 client)
   - Table name specified? (e.g., `cv_tailoring_jobs`)
   - GSI specified? (e.g., `user-id-index` for querying by user)
   - TTL configured? (automatic cleanup after X days)

For **Cover Letter**:
1. Open `/docs/architecture/COVER_LETTER_DESIGN.md`
2. Check same items as above
3. Table name: `cover_letter_jobs`?

For **Gap Analysis**:
1. Open `/docs/architecture/GAP_ANALYSIS_DESIGN.md`
2. Check same items as above
3. Table name: `gap_analysis_jobs`?

**Fill Out:**
```markdown
| Feature | Uses Shared DAL | Table Name | GSI Defined | TTL Configured | Status |
|---------|-----------------|------------|-------------|----------------|--------|
| CV Tailoring | ✅ / ❌ / ❓ | [name] | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | PASS/FAIL/UNCLEAR |
| Cover Letter | ✅ / ❌ / ❓ | [name] | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | PASS/FAIL/UNCLEAR |
| Gap Analysis | ✅ / ❌ / ❓ | [name] | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | PASS/FAIL/UNCLEAR |
```

**Evidence to Capture:**
- Quote DAL usage from design docs
- List table names and GSI names

**Risk if FAIL:** DAL inconsistency, difficult maintenance, custom boto3 code duplication

---

### ✅ Check 8: AWS Lambda Powertools Integration

**Question:** Do all features use AWS Lambda Powertools for observability?

**VPR Reference:**
```python
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.event_handler import APIGatewayRestResolver

logger = Logger(service="vpr-handler")
tracer = Tracer(service="vpr-handler")
metrics = Metrics(namespace="CareerVP", service="vpr-handler")

@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    logger.info("Processing VPR request")
    metrics.add_metric(name="VPRRequests", unit=MetricUnit.Count, value=1)
    # ... handler logic
```

**What to Check in Design Docs:**

For **CV Tailoring**:
1. Open `/docs/architecture/CV_TAILORING_DESIGN.md`
2. Search for "Observability" or "Logging" section
3. Check:
   - Logger usage specified?
   - Tracer usage specified?
   - Metrics usage specified?
   - Service name convention: `cv-tailoring-handler`?

For **Cover Letter**:
1. Open `/docs/architecture/COVER_LETTER_DESIGN.md`
2. Check same observability items
3. Service name: `cover-letter-handler`?

For **Gap Analysis**:
1. Open `/docs/architecture/GAP_ANALYSIS_DESIGN.md`
2. Check same observability items
3. Service name: `gap-analysis-handler`?

**Fill Out:**
```markdown
| Feature | Logger | Tracer | Metrics | Service Name | Status |
|---------|--------|--------|---------|--------------|--------|
| CV Tailoring | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | [name] | PASS/FAIL/UNCLEAR |
| Cover Letter | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | [name] | PASS/FAIL/UNCLEAR |
| Gap Analysis | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | [name] | PASS/FAIL/UNCLEAR |
```

**Evidence to Capture:**
- Quote observability sections from design docs
- List metrics to be tracked

**Risk if FAIL:** Poor observability, difficult debugging in production, no performance monitoring

---

## 📝 DELIVERABLE FORMAT

Create this file: `/docs/architecture/LIGHTWEIGHT_REVIEW_RESULTS.md`

**Template:**

```markdown
# Lightweight Architecture Review Results

**Date:** [Today's Date]
**Reviewer:** [Your Name/Agent ID]
**Features Reviewed:** CV Tailoring, Cover Letter, Gap Analysis
**Reference Implementation:** VPR (Value Proposition Report)
**Review Duration:** [X hours]

---

## Executive Summary

**Overall Status:** [PASS / MINOR ISSUES / MAJOR ISSUES / BLOCKING ISSUES]

**Checklist Results:**

| Check | CV Tailoring | Cover Letter | Gap Analysis | Overall |
|-------|--------------|--------------|--------------|---------|
| 1. Handler → Logic → DAL | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | PASS/FAIL |
| 2. Result[T] Pattern | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | PASS/FAIL |
| 3. FVS Integration | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | PASS/FAIL |
| 4. Gap Responses Input | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | PASS/FAIL |
| 5. Sync/Async Justified | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | PASS/FAIL |
| 6. LLM Model Selection | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | PASS/FAIL |
| 7. Shared DAL Patterns | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | PASS/FAIL |
| 8. AWS Powertools | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | ✅ / ❌ / ❓ | PASS/FAIL |

**Pass Rate:** X/8 checks passed (Target: ≥ 6/8)

**Recommendation:** [APPROVE FOR IMPLEMENTATION / REQUIRE DESIGN UPDATES / MAJOR REDESIGN NEEDED]

---

## Detailed Findings

### Check 1: Handler → Logic → DAL Pattern

**CV Tailoring:**
- Status: [PASS/FAIL/UNCLEAR]
- Evidence: [Quote from design doc]
- Issues: [Any deviations from VPR pattern]

**Cover Letter:**
- Status: [PASS/FAIL/UNCLEAR]
- Evidence: [Quote from design doc]
- Issues: [Any deviations]

**Gap Analysis:**
- Status: [PASS/FAIL/UNCLEAR]
- Evidence: [Quote from design doc]
- Issues: [Any deviations]

**Overall:** [PASS/FAIL]

---

[Repeat for all 8 checks...]

---

## Critical Findings (Blocking Issues)

[List any issues that MUST be fixed before implementation starts]

1. **[Issue 1 Title]**
   - **Severity:** BLOCKING
   - **Feature(s) Affected:** [CV Tailoring / Cover Letter / Gap Analysis]
   - **Description:** [What's wrong]
   - **Impact:** [Why this is blocking]
   - **Recommendation:** [How to fix]
   - **Fix Effort:** [X hours]

[Repeat for each blocking issue...]

---

## Design Improvement Recommendations (Non-Blocking)

[List improvements that would be nice to have but aren't blocking]

1. **[Recommendation 1 Title]**
   - **Severity:** MINOR
   - **Feature(s) Affected:** [CV Tailoring / Cover Letter / Gap Analysis]
   - **Description:** [What could be better]
   - **Benefit:** [Why this improves the design]
   - **Recommendation:** [How to improve]
   - **Fix Effort:** [X hours]

[Repeat for each recommendation...]

---

## Questions for Architect

[List any ambiguities or unclear decisions in the design docs]

1. **[Question 1]**
   - **Feature:** [CV Tailoring / Cover Letter / Gap Analysis]
   - **Section:** [Which section of design doc]
   - **Question:** [Your question]
   - **Why It Matters:** [Impact on implementation]

[Repeat for each question...]

---

## Action Items

**Before Implementation Can Start:**

- [ ] Fix blocking issue #1: [Description]
- [ ] Fix blocking issue #2: [Description]
- [ ] ...

**Optional Improvements:**

- [ ] Implement recommendation #1: [Description]
- [ ] Implement recommendation #2: [Description]
- [ ] ...

**Design Doc Updates Required:**

- [ ] Update CV_TAILORING_DESIGN.md: [Specific changes needed]
- [ ] Update COVER_LETTER_DESIGN.md: [Specific changes needed]
- [ ] Update GAP_ANALYSIS_DESIGN.md: [Specific changes needed]

---

## Sign-Off

**Reviewer Signature:** [Your Name]
**Date:** [Today's Date]

**Approval Status:** [APPROVED / CONDITIONAL APPROVAL / REJECTED]

**Notes:**
[Any final notes or context for the implementation team]

---

**End of Lightweight Review Results**
```

---

## 🚀 NEXT STEPS AFTER REVIEW

### If APPROVED (≥ 6/8 checks pass, zero blocking issues):
1. Share review results with architect and engineering team
2. Address non-blocking recommendations (optional)
3. Begin implementation of CV Tailoring
4. Schedule Deep Analysis review after CV Tailoring is complete

### If CONDITIONAL APPROVAL (≥ 6/8 checks pass, minor issues):
1. Update design docs to address issues
2. Re-review updated sections
3. Get final approval
4. Begin implementation

### If REJECTED (< 6/8 checks pass, or blocking issues):
1. Schedule meeting with architect to discuss findings
2. Wait for design docs to be updated
3. Re-run Lightweight Review
4. Do NOT start implementation until approved

---

## 💡 TIPS FOR SUCCESS

1. **Be Thorough But Fast:** You have 2-3 hours. Focus on the 8 checklist items, don't go deep on tangents.

2. **Use CTRL+F Heavily:** Search design docs for keywords like "Handler", "Result", "FVS", "gap_responses", etc.

3. **Compare Side-by-Side:** Open VPR_ASYNC_DESIGN.md and CV_TAILORING_DESIGN.md side-by-side to spot differences.

4. **Mark UNCLEAR Liberally:** If a design doc mentions something but lacks detail, mark it ❓ UNCLEAR, not ✅ PASS.

5. **Quote Evidence:** Always quote the specific section from the design doc as evidence.

6. **Think Like a Junior Engineer:** Would YOU be able to implement this feature from the design doc alone? If no → FAIL.

7. **Don't Assume:** If the design doc doesn't explicitly mention something (like gap_responses), mark it ❌ FAIL, even if you think "they probably meant to include it."

8. **Ask Questions:** If something is ambiguous, add it to "Questions for Architect" section.

---

## ⚠️ COMMON PITFALLS TO AVOID

❌ **Don't write code** - This is a design review, not implementation
❌ **Don't assess performance** - That's Phase 2 (Deep Analysis)
❌ **Don't use LSP tools** - No code exists yet
❌ **Don't assume patterns** - If not documented, mark as FAIL
❌ **Don't be lenient** - Better to catch issues now than during implementation

✅ **Do be specific** - Quote exact sections from docs
✅ **Do be objective** - Use the checklist, not personal preference
✅ **Do be helpful** - Provide clear recommendations for fixes
✅ **Do be thorough** - Read all linked documents

---

## 📞 QUESTIONS OR BLOCKERS?

If you encounter any issues during the review:
1. Check `/docs/architecture/ARCHITECTURE_REVIEW_PLAN.md` for detailed methodology
2. Review VPR implementation code for reference patterns
3. Document unclear items in "Questions for Architect" section

---

**Good luck with your review! Remember: Your job is to catch design-level issues before they become code-level technical debt.**

---

**End of Lightweight Review Handoff Prompt**
