# Next Steps: Post-Lightweight Review Action Plan

**Date:** 2026-02-07
**Author:** Claude Sonnet 4.5 (Principal Architect)
**Context:** Response to Lightweight Architecture Review Results
**Status:** Action Plan - Ready for Execution
**Priority:** P0 - BLOCKING

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Immediate Actions (Week 1)](#immediate-actions-week-1)
3. [Architectural Decisions Required](#architectural-decisions-required)
4. [Design Document Updates](#design-document-updates)
5. [Quality Gates](#quality-gates)
6. [Timeline & Resources](#timeline--resources)
7. [Risk Mitigation](#risk-mitigation)
8. [Success Criteria](#success-criteria)

---

## Executive Summary

### Current Situation

The Lightweight Architecture Review identified **critical inconsistencies** between the architectural plan and feature design documents:

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Checklist Pass Rate | ≥ 6/8 | 1/8 | ❌ FAIL |
| Blocking Issues | 0 | 4 | ❌ CRITICAL |
| Design Consistency | 100% | ~25% | ❌ FAIL |
| Implementation Ready | YES | NO | ❌ BLOCKED |

### Impact

**Implementation is BLOCKED** until design documents are updated and architectural decisions are clarified.

### Resolution Path

1. **Architect answers 5 critical questions** (2-4 hours)
2. **Update 6 design documents** (8-12 hours)
3. **Re-run lightweight review** (1 hour)
4. **Sign-off and proceed to implementation** (Phase 9-11)

**Total Estimated Effort:** 11-17 hours before implementation can begin

---

## Immediate Actions (Week 1)

### Phase 1A: Architectural Decision Making (Days 1-2)

**Owner:** Principal Architect
**Duration:** 2-4 hours
**Priority:** P0 - BLOCKING

#### Decision 1: Gap Analysis Execution Pattern

**Question:** Should Gap Analysis be synchronous or asynchronous?

**Context from Review:**
- **Plan says:** Synchronous with <60s expected latency (line 266-267)
- **Design says:** Async SQS pattern (from design doc)
- **Conflict:** Fundamental architectural mismatch

**Options:**

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **Sync** | Simpler UX, immediate feedback, consistent with CV Tailoring/Cover Letter | 15-min Lambda timeout risk, no retry on failure | ✅ RECOMMENDED if Sonnet latency <45s |
| **Async** | Unlimited processing time, retry support, handles long operations | Complex polling UX, infrastructure overhead | Use only if Sonnet latency >60s |

**Recommendation:**
- **PRIMARY:** Synchronous with 600s timeout (Sonnet 4.5 strategic task)
- **FALLBACK:** If Sonnet latency >60s in testing, migrate to async
- **RATIONALE:** Consistency with other Phase 10-11 features, simpler first implementation

**Action Items:**
- [ ] Architect confirms sync/async choice
- [ ] Update GAP_ANALYSIS_DESIGN.md with chosen pattern
- [ ] Update plan.md if async is chosen (justify divergence)
- [ ] Document timeout values and migration triggers

---

#### Decision 2: Gap Analysis LLM Model Selection

**Question:** Should Gap Analysis use Sonnet 4.5 or Haiku 4.5?

**Context from Review:**
- **Plan says:** Sonnet 4.5 for strategic reasoning (line 295-296)
- **Design says:** Claude 3 Haiku for faster responses
- **Conflict:** Wrong model = wrong cost/quality/latency

**Options:**

| Model | Cost/Request | Latency (Est) | Quality | Use Case |
|-------|--------------|---------------|---------|----------|
| **Sonnet 4.5** | ~$0.10 | 30-60s | High reasoning | Strategic gap questions (PLAN CHOICE) |
| **Haiku 4.5** | ~$0.006 | 10-20s | Fast templating | Template-based tasks |

**Recommendation:**
- **USE SONNET 4.5** (align with plan)
- **RATIONALE:** Gap Analysis requires strategic reasoning to identify meaningful skill/experience gaps
- **COST:** $0.10 per question set is acceptable for high-value strategic analysis

**Action Items:**
- [ ] Architect confirms Sonnet 4.5 choice
- [ ] Update GAP_ANALYSIS_DESIGN.md model selection section
- [ ] Update cost estimates in design doc
- [ ] Set TaskMode.STRATEGIC in implementation

---

#### Decision 3: Handler → Logic → DAL Layering Pattern

**Question:** Should handlers directly access DAL or only through logic layer?

**Context from Review:**
- **VPR Pattern:** Handler → Logic → DAL (strict layering)
- **CV Tailoring/Cover Letter:** Handlers directly call DAL for reads/writes
- **Conflict:** Inconsistent architecture = difficult maintenance

**Options:**

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **Strict Layering** (VPR pattern) | Testable, reusable logic, consistent architecture | More boilerplate, logic must handle all DAL ops | ✅ RECOMMENDED for consistency |
| **Relaxed Layering** | Less code, faster development | Tight handler-DAL coupling, logic not reusable | Avoid unless justified |

**Recommendation:**
- **USE STRICT LAYERING** (Handler → Logic → DAL)
- **RATIONALE:** Consistency with VPR, easier testing, logic layer reusability
- **PATTERN:**
  ```python
  # Handler: cv_tailoring_handler.py
  def lambda_handler(event, context):
      logic = CVTailoringLogic(dal=dal, llm=llm, fvs=fvs)
      result = logic.tailor_cv(request)  # Logic handles ALL DAL access
      return format_response(result)

  # Logic: cv_tailoring_logic.py
  class CVTailoringLogic:
      def tailor_cv(self, request):
          cv = self.dal.get_cv(request.cv_id)  # Logic calls DAL
          tailored = self._apply_tailoring(cv, request.job_desc)
          self.dal.store_tailored_cv(tailored)  # Logic stores result
          return Result(success=True, data=tailored)
  ```

**Action Items:**
- [ ] Architect confirms strict layering requirement
- [ ] Update CV_TAILORING_DESIGN.md workflow section (move DAL to logic)
- [ ] Update COVER_LETTER_DESIGN.md workflow section (move DAL to logic)
- [ ] Add logic layer methods for all DAL operations

---

#### Decision 4: Gap Responses Input Method

**Question:** How should `gap_responses` be passed into CV Tailoring?

**Context from Review:**
- **Plan says:** All features accept `gap_responses` input (line 242-248)
- **CV Tailoring Design:** No `gap_responses` field in input schema
- **Conflict:** Missing critical context for tailoring

**Options:**

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **Request Payload** | Explicit, user controls data, no DAL lookup | Larger payload, user must fetch responses | ✅ RECOMMENDED for Phase 9 |
| **DAL Lookup** | Smaller payload, automatic retrieval | Implicit dependency, coupling to storage | Use in Phase 12+ (optimization) |

**Recommendation:**
- **USE REQUEST PAYLOAD** (explicit `gap_responses` field)
- **RATIONALE:** Explicit dependencies, easier testing, user controls context
- **SCHEMA:**
  ```python
  class CVTailoringRequest(BaseModel):
      cv_id: str
      job_description: str
      gap_responses: Optional[GapAnalysisResponses] = None  # NEW FIELD
  ```

**Action Items:**
- [ ] Architect confirms request payload approach
- [ ] Update CV_TAILORING_SPEC.md with `gap_responses` field
- [ ] Update CV_TAILORING_DESIGN.md prompt section (show gap_responses usage)
- [ ] Update COVER_LETTER_SPEC.md (already has gap_responses, verify alignment)

---

#### Decision 5: DynamoDB Table Naming Conventions

**Question:** What are the canonical table names and GSI names?

**Context from Review:**
- **Issue:** Table names not specified in designs, causing confusion
- **VPR Tables:** `vpr_jobs`, `user_cvs`
- **Need:** Consistent naming for all features

**Recommendation:**

| Feature | Table Name | Primary Key | GSI Name | GSI Key |
|---------|------------|-------------|----------|---------|
| VPR | `vpr_jobs` | `job_id` (S) | `user_id_index` | `user_id` (S) |
| CV Tailoring | `cv_tailoring_jobs` | `job_id` (S) | `user_id_index` | `user_id` (S) |
| Cover Letter | `cover_letter_jobs` | `job_id` (S) | `user_id_index` | `user_id` (S) |
| Gap Analysis | `gap_analysis_jobs` | `job_id` (S) | `user_id_index` | `user_id` (S) |
| User CVs | `user_cvs` | `cv_id` (S) | `user_id_index` | `user_id` (S) |

**Naming Convention:**
- Table: `{feature}_jobs` (snake_case, plural)
- GSI: `user_id_index` (consistent across all tables)
- TTL Attribute: `ttl` (unix timestamp, 90 days retention)

**Action Items:**
- [ ] Architect confirms table naming convention
- [ ] Update CV_TAILORING_DESIGN.md with table schema
- [ ] Update COVER_LETTER_DESIGN.md with table schema
- [ ] Update GAP_ANALYSIS_DESIGN.md with table schema
- [ ] Add CDK table definitions to infrastructure docs

---

### Phase 1B: Design Document Updates (Days 3-5)

**Owner:** Technical Writer / Implementation Engineer
**Duration:** 8-12 hours
**Priority:** P0 - BLOCKING

#### Update 1: CV_TAILORING_DESIGN.md

**File:** `/docs/phase-9-cv-tailoring/CV_TAILORING_DESIGN.md`
**Estimated Effort:** 3-4 hours

**Required Changes:**

1. **Add Handler → Logic → DAL Layering Section**
   ```markdown
   ## Architecture Pattern: Handler → Logic → DAL

   ### Handler Layer (cv_tailoring_handler.py)
   - Validates API input (Pydantic models)
   - Initializes dependencies (DAL, LLM, FVS)
   - Delegates ALL business logic to CVTailoringLogic
   - Formats HTTP responses
   - NO DIRECT DAL ACCESS

   ### Logic Layer (cv_tailoring_logic.py)
   - Fetches master CV from DAL
   - Calls LLM for tailoring
   - Validates with FVS
   - Stores tailored CV via DAL
   - Returns Result[TailoredCV]

   ### DAL Layer (dynamo_dal_handler.py - SHARED)
   - get_cv(cv_id) -> UserCV
   - store_tailored_cv(tailored_cv) -> None
   - query_by_user_id(user_id) -> list[TailoredCV]
   ```

2. **Add Gap Responses Input Schema**
   ```markdown
   ## Input Schema

   ```python
   class CVTailoringRequest(BaseModel):
       cv_id: str
       job_description: str
       gap_responses: Optional[GapAnalysisResponses] = None  # NEW
   ```

   ### Gap Responses Usage

   Gap responses provide additional context for tailoring:
   - Skills with evidence → Highlight in tailored CV
   - Experience with details → Expand relevant sections
   - Missing skills → De-emphasize or omit weak areas
   ```

3. **Add LLM Prompt Section with Gap Responses**
   ```markdown
   ## LLM Prompt Strategy

   ### Prompt Template (with Gap Responses)

   ```xml
   <instruction>
   Tailor this CV to match the job description.
   </instruction>

   <master_cv>
   {{master_cv_content}}
   </master_cv>

   <job_description>
   {{job_description}}
   </job_description>

   {{#if gap_responses}}
   <gap_analysis_responses>
   The candidate has provided additional context:
   {{gap_responses}}
   </gap_analysis_responses>
   {{/if}}

   <output_format>
   Return tailored CV in JSON format...
   </output_format>
   ```
   ```

4. **Add AWS Powertools Observability Section**
   ```markdown
   ## Observability: AWS Lambda Powertools

   ### Handler Decorators

   ```python
   from aws_lambda_powertools import Logger, Tracer, Metrics

   logger = Logger(service="cv-tailoring")
   tracer = Tracer(service="cv-tailoring")
   metrics = Metrics(namespace="CareerVP", service="cv-tailoring")

   @logger.inject_lambda_context(log_event=True)
   @tracer.capture_lambda_handler(capture_response=False)
   @metrics.log_metrics(capture_cold_start_metric=True)
   def lambda_handler(event, context):
       ...
   ```

   ### Metrics to Track
   - `CVTailoringSuccess` - Successful tailoring count
   - `CVTailoringFailure` - Failed tailoring count
   - `TailoringLatency` - End-to-end latency (ms)
   - `LLMCost` - Cost per tailoring ($)
   - `FVSViolations` - Hallucination count
   ```

5. **Add DynamoDB Table Schema**
   ```markdown
   ## DynamoDB Table: cv_tailoring_jobs

   ### Schema

   | Attribute | Type | Description |
   |-----------|------|-------------|
   | job_id (PK) | String | UUID for tailoring job |
   | user_id | String | User who submitted request |
   | cv_id | String | Reference to master CV |
   | job_description | String | Target job description |
   | status | String | PENDING / PROCESSING / COMPLETED / FAILED |
   | tailored_cv_s3_key | String | S3 path to result |
   | created_at | Number | Unix timestamp |
   | ttl | Number | Auto-delete timestamp (90 days) |

   ### GSI: user_id_index
   - Partition Key: user_id
   - Sort Key: created_at
   - Projection: ALL
   ```

**Checklist:**
- [ ] Add Handler → Logic → DAL section
- [ ] Add `gap_responses` to input schema
- [ ] Add gap_responses to LLM prompt
- [ ] Add AWS Powertools section
- [ ] Add DynamoDB table schema
- [ ] Update workflow diagram (move DAL to logic layer)

---

#### Update 2: CV_TAILORING_SPEC.md

**File:** `/docs/phase-9-cv-tailoring/CV_TAILORING_SPEC.md`
**Estimated Effort:** 1 hour

**Required Changes:**

1. **Add `gap_responses` to Request Model**
   ```markdown
   ## Request Schema

   ```json
   {
     "cv_id": "uuid-string",
     "job_description": "Full job description text...",
     "gap_responses": {  // NEW FIELD - OPTIONAL
       "responses": [
         {
           "question_id": "uuid",
           "question_text": "Describe your experience with...",
           "response_text": "I have 5 years of experience...",
           "skills_mentioned": ["Python", "AWS", "Docker"]
         }
       ]
     }
   }
   ```
   ```

**Checklist:**
- [ ] Add `gap_responses` field to request JSON schema
- [ ] Mark field as optional
- [ ] Add example with sample gap_responses

---

#### Update 3: COVER_LETTER_DESIGN.md

**File:** `/docs/phase-10-cover-letter/COVER_LETTER_DESIGN.md`
**Estimated Effort:** 2-3 hours

**Required Changes:**

1. **Update Handler → Logic → DAL Layering**
   - Move DAL access from handler to logic layer
   - Handler only validates input and delegates
   - Logic fetches CV, VPR, gap_responses from DAL

2. **Add Async Migration Trigger Section**
   ```markdown
   ## Decision: Async Migration Trigger

   ### Current: Synchronous (300s timeout)

   Cover Letter generation is synchronous because expected latency <20s.

   ### Migration Trigger

   Migrate to async SQS pattern if ANY of:
   - p95 latency >60s in production
   - >5% timeout failures
   - User feedback: "slow" or "hangs"

   ### Migration Path

   1. Create cover_letter_worker_queue (SQS)
   2. Implement cover_letter_worker.py (async handler)
   3. Add cover_letter_status.py (polling endpoint)
   4. Update API Gateway to async submit/status pattern
   5. Estimated migration effort: 8-12 hours
   ```

3. **Add AWS Powertools Section** (if missing)

4. **Add DynamoDB Table Schema**
   ```markdown
   ## DynamoDB Table: cover_letter_jobs

   [Same pattern as cv_tailoring_jobs]
   ```

**Checklist:**
- [ ] Update workflow (Handler → Logic → DAL)
- [ ] Add async migration trigger section
- [ ] Verify AWS Powertools section exists
- [ ] Add DynamoDB table schema

---

#### Update 4: COVER_LETTER_SPEC.md

**File:** `/docs/phase-10-cover-letter/COVER_LETTER_SPEC.md`
**Estimated Effort:** 30 minutes

**Required Changes:**

1. **Verify `gap_responses` field exists and is consistent**
   - Already present in design, verify spec matches
   - Ensure same schema as CV_TAILORING_SPEC.md

**Checklist:**
- [ ] Verify `gap_responses` field in request schema
- [ ] Ensure consistency with CV Tailoring spec

---

#### Update 5: GAP_ANALYSIS_DESIGN.md

**File:** `/docs/phase-11-gap-analysis/GAP_ANALYSIS_DESIGN.md`
**Estimated Effort:** 3-4 hours

**Required Changes:**

1. **Align Execution Pattern (Sync vs Async)**
   - Change to **synchronous** (per Decision 1)
   - Remove SQS/worker pattern
   - Add simple submit handler with immediate response

2. **Update LLM Model Selection**
   - Change from Claude 3 Haiku to **Claude Sonnet 4.5**
   - Update TaskMode to **STRATEGIC**
   - Update cost estimates (~$0.10 per question set)

3. **Add FVS Integration Section**
   ```markdown
   ## FVS Integration: Skill Verification

   ### Purpose

   Validate that skills mentioned in CV/job description are real and not hallucinated.

   ### Validation Rules

   ```python
   class GapAnalysisFVSValidator:
       def validate_questions(self, questions: list[GapQuestion], master_cv: UserCV, job_desc: str):
           """
           Validate gap questions against master CV and job description.

           IMMUTABLE FACTS:
           - Skills mentioned in master CV
           - Job requirements from job description

           HALLUCINATION CHECK:
           - Question references skill not in CV or job desc → REJECT
           - Question fabricates experience → REJECT
           ```

   ### Integration Point

   ```python
   # Logic layer (gap_analysis_logic.py)
   def generate_gap_questions(...) -> Result[list[GapQuestion]]:
       questions = llm.generate_questions(cv, job_desc)

       # FVS validation
       fvs_result = fvs_validator.validate_questions(questions, cv, job_desc)
       if not fvs_result.success:
           return Result(
               success=False,
               error="Hallucinated skills detected",
               code=ResultCode.FVS_HALLUCINATION_DETECTED
           )

       return Result(success=True, data=questions)
   ```
   ```

4. **Add Handler → Logic → DAL Layering**
   ```markdown
   ## Architecture Pattern: Handler → Logic → DAL

   ### Submit Handler (gap_analysis_submit_handler.py)
   - Validates input (cv_id, job_id)
   - Initializes logic layer
   - Calls logic.generate_gap_questions()
   - Returns Result[list[GapQuestion]] immediately (sync)

   ### Logic Layer (gap_analysis_logic.py)
   - Fetches CV and job description from DAL
   - Calls LLM (Sonnet 4.5) for question generation
   - Validates questions with FVS
   - Stores questions via DAL
   - Returns Result[list[GapQuestion]]

   ### DAL Layer (dynamo_dal_handler.py - SHARED)
   - get_cv(cv_id) -> UserCV
   - get_job_description(job_id) -> str
   - store_gap_questions(questions) -> None
   ```

5. **Add AWS Powertools Section**

6. **Add DynamoDB Table Schema**
   ```markdown
   ## DynamoDB Table: gap_analysis_jobs

   [Same pattern as cv_tailoring_jobs]
   ```

7. **Update Timeout to 600s** (Sonnet strategic task)

**Checklist:**
- [ ] Change to synchronous pattern
- [ ] Update model to Sonnet 4.5
- [ ] Add FVS integration section
- [ ] Add Handler → Logic → DAL layering
- [ ] Add AWS Powertools section
- [ ] Add DynamoDB table schema
- [ ] Update timeout to 600s

---

#### Update 6: GAP_SPEC.md

**File:** `/docs/phase-11-gap-analysis/GAP_SPEC.md`
**Estimated Effort:** 1 hour

**Required Changes:**

1. **Update to Synchronous API Pattern**
   ```markdown
   ## API Endpoint

   POST /api/gap-analysis/submit

   ### Request

   ```json
   {
     "cv_id": "uuid",
     "job_id": "uuid"
   }
   ```

   ### Response (Immediate - SYNC)

   ```json
   {
     "success": true,
     "questions": [
       {
         "question_id": "uuid",
         "question_text": "Describe your experience with...",
         "category": "technical_skills"
       }
     ]
   }
   ```
   ```

2. **Confirm Sonnet 4.5 Model**

3. **Add FVS Requirements**

**Checklist:**
- [ ] Update to synchronous API pattern
- [ ] Remove status polling endpoint
- [ ] Confirm Sonnet 4.5 model
- [ ] Add FVS validation mention

---

### Phase 1C: Re-Run Lightweight Review (Day 6)

**Owner:** Principal Architect
**Duration:** 1 hour
**Priority:** P0 - BLOCKING

**Process:**

1. **Run Review Checklist Again**
   - Execute same 8 checks from ARCHITECTURE_REVIEW_PLAN.md
   - Document results in LIGHTWEIGHT_REVIEW_RESULTS_V2.md

2. **Pass Criteria**
   - ≥ 6/8 checks pass
   - Zero blocking issues
   - All design docs updated

3. **If Review Fails Again**
   - Identify remaining issues
   - Iterate on design docs (back to Phase 1B)
   - Re-review until pass

**Checklist:**
- [ ] Run all 8 checklist items
- [ ] Document results in V2 results file
- [ ] Verify ≥ 6/8 pass rate
- [ ] Confirm zero blocking issues

---

### Phase 1D: Sign-Off & Proceed (Day 6)

**Owner:** Principal Architect + Engineering Lead
**Duration:** 30 minutes
**Priority:** P0 - GATE

**Activities:**

1. **Architect Sign-Off**
   - Review V2 results
   - Confirm all blocking issues resolved
   - Approve for implementation

2. **Engineering Lead Sign-Off**
   - Confirm design clarity
   - Confirm implementation ready
   - Assign engineers to Phase 9-11

3. **Update Project Status**
   - Mark Phase 8 (Design) as COMPLETE
   - Unblock Phase 9 (CV Tailoring Implementation)
   - Update project timeline

**Checklist:**
- [ ] Architect signs off on design updates
- [ ] Engineering Lead confirms implementation readiness
- [ ] Phase 9-11 unblocked for development

---

## Architectural Decisions Required

### Decision Summary Table

| Decision | Question | Recommended Answer | Impact | Priority |
|----------|----------|-------------------|--------|----------|
| **1. Execution Pattern** | Sync or Async for Gap Analysis? | **Synchronous** (600s timeout) | Architecture pattern consistency | P0 |
| **2. LLM Model** | Sonnet 4.5 or Haiku for Gap Analysis? | **Sonnet 4.5** (strategic reasoning) | Cost, quality, latency | P0 |
| **3. Layering** | Strict Handler → Logic → DAL? | **Strict Layering** (VPR pattern) | Code reusability, testability | P0 |
| **4. Gap Responses** | Request payload or DAL lookup? | **Request Payload** (explicit) | API design, dependencies | P0 |
| **5. Table Naming** | Naming convention? | **{feature}_jobs** pattern | Infrastructure consistency | P0 |

### Decision Documentation

All architectural decisions must be documented in:
- **Location:** `/docs/architecture/ARCHITECTURAL_DECISIONS.md`
- **Format:** ADR (Architecture Decision Record)
- **Template:**
  ```markdown
  ## ADR-XXX: [Decision Title]

  **Date:** YYYY-MM-DD
  **Status:** ACCEPTED / REJECTED / SUPERSEDED
  **Deciders:** [Names]

  ### Context
  [What is the issue we're facing?]

  ### Decision
  [What did we decide?]

  ### Consequences
  [What are the implications?]

  ### Alternatives Considered
  [What other options were evaluated?]
  ```

**Action Items:**
- [ ] Create ARCHITECTURAL_DECISIONS.md file
- [ ] Document all 5 decisions as ADRs
- [ ] Reference ADRs in design docs

---

## Design Document Updates

### Update Summary

| Document | Changes Required | Effort | Priority |
|----------|------------------|--------|----------|
| CV_TAILORING_DESIGN.md | Add layering, gap_responses, observability, DAL schema | 3-4h | P0 |
| CV_TAILORING_SPEC.md | Add gap_responses field | 1h | P0 |
| COVER_LETTER_DESIGN.md | Update layering, add migration trigger, DAL schema | 2-3h | P0 |
| COVER_LETTER_SPEC.md | Verify gap_responses consistency | 0.5h | P0 |
| GAP_ANALYSIS_DESIGN.md | Change to sync, Sonnet 4.5, add FVS, layering, observability | 3-4h | P0 |
| GAP_SPEC.md | Update to sync API pattern, Sonnet 4.5 | 1h | P0 |
| **TOTAL** | | **10.5-13.5h** | |

### Documentation Quality Standards

All design documents must meet these criteria:

1. **Completeness**
   - ✅ All 8 checklist items addressed
   - ✅ Architecture pattern clearly documented
   - ✅ All input/output schemas defined
   - ✅ Error handling strategy documented
   - ✅ Observability requirements specified

2. **Consistency**
   - ✅ Aligned with plan.md
   - ✅ Aligned with VPR reference implementation
   - ✅ Consistent terminology across docs
   - ✅ Consistent naming conventions

3. **Implementability**
   - ✅ Junior engineer can implement from design
   - ✅ All dependencies identified
   - ✅ All integration points documented
   - ✅ Clear success criteria defined

---

## Quality Gates

### Gate 1: Architectural Decisions Approved

**Criteria:**
- [ ] All 5 architectural decisions documented
- [ ] Principal Architect sign-off
- [ ] ADRs published in ARCHITECTURAL_DECISIONS.md

**Blocking:** Design document updates cannot proceed until decisions are made

---

### Gate 2: Design Documents Updated

**Criteria:**
- [ ] All 6 documents updated per action items
- [ ] Peer review completed (2+ reviewers)
- [ ] No conflicting information across docs

**Blocking:** Re-review cannot proceed until docs are complete

---

### Gate 3: Lightweight Review V2 Passed

**Criteria:**
- [ ] ≥ 6/8 checklist items pass
- [ ] Zero blocking issues
- [ ] Principal Architect approval

**Blocking:** Implementation cannot start until review passes

---

### Gate 4: Engineering Sign-Off

**Criteria:**
- [ ] Engineering Lead confirms clarity
- [ ] Engineers confirm implementation readiness
- [ ] No open questions or ambiguities

**Blocking:** Phase 9 implementation cannot start without sign-off

---

## Timeline & Resources

### Optimistic Timeline (11 hours)

| Phase | Duration | Owner | Dependencies |
|-------|----------|-------|--------------|
| 1A: Decisions | 2h | Architect | None |
| 1B: Design Updates | 8h | Tech Writer + Engineer | Phase 1A complete |
| 1C: Re-Review | 1h | Architect | Phase 1B complete |
| 1D: Sign-Off | 0.5h | Architect + Lead | Phase 1C pass |
| **TOTAL** | **11.5h** | | |

### Realistic Timeline (17 hours)

| Phase | Duration | Owner | Dependencies |
|-------|----------|-------|--------------|
| 1A: Decisions | 4h | Architect | None (includes discussion time) |
| 1B: Design Updates | 12h | Tech Writer + Engineer | Phase 1A complete |
| 1C: Re-Review | 1h | Architect | Phase 1B complete |
| 1D: Sign-Off | 0.5h | Architect + Lead | Phase 1C pass |
| **TOTAL** | **17.5h** | | |

### Resource Requirements

| Role | Availability | Workload |
|------|--------------|----------|
| Principal Architect | 6 hours over 3 days | Decision making, review, sign-off |
| Technical Writer | 12 hours over 3 days | Design document updates |
| Implementation Engineer | 4 hours over 2 days | Design review, technical validation |
| Engineering Lead | 1 hour | Final sign-off |

---

## Risk Mitigation

### Risk 1: Architectural Decisions Take Longer Than Expected

**Probability:** MEDIUM
**Impact:** HIGH (blocks all downstream work)

**Mitigation:**
- Schedule dedicated decision-making session (2-hour block)
- Prepare decision materials in advance
- Use recommended answers as starting point (already researched)
- Escalate to CTO if consensus cannot be reached within 4 hours

---

### Risk 2: Re-Review Fails Again

**Probability:** LOW (with proper updates)
**Impact:** MEDIUM (delay of 1-2 days)

**Mitigation:**
- Use detailed update checklists (provided above)
- Self-review before submitting to architect
- Pair review between tech writer and engineer
- Focus on blocking issues first (must-fix vs nice-to-have)

---

### Risk 3: Scope Creep During Updates

**Probability:** MEDIUM
**Impact:** MEDIUM (delays implementation start)

**Mitigation:**
- Stick to checklist items ONLY (no additional features)
- Defer "nice-to-have" improvements to Phase 2 review
- Time-box each document update (4h max per doc)
- Engineering Lead enforces scope discipline

---

### Risk 4: Incomplete Implementation Guidance

**Probability:** LOW (design docs are already detailed)
**Impact:** HIGH (implementation delays/rework)

**Mitigation:**
- "Junior Engineer Test": Ask junior engineer to review design docs
- Document open questions as they arise
- Architect available for clarifications during implementation
- Use VPR as reference implementation (concrete examples)

---

## Success Criteria

### Phase 1 Success (Design Complete)

**Must Have:**
- [x] Lightweight Review completed (DONE - identified issues)
- [ ] 5 architectural decisions made and documented
- [ ] 6 design documents updated and reviewed
- [ ] Lightweight Review V2 passed (≥ 6/8)
- [ ] Zero blocking issues remaining
- [ ] Architect and Engineering Lead sign-off

**Nice to Have:**
- [ ] All 8/8 checklist items pass (stretch goal)
- [ ] Design documents exceed "implementability" standard
- [ ] Additional ADRs for future features

---

### Phase 9-11 Unblock Criteria

**Ready to Implement CV Tailoring if:**
- [ ] CV_TAILORING_DESIGN.md updated and approved
- [ ] CV_TAILORING_SPEC.md updated and approved
- [ ] Architectural decisions documented (layering, gap_responses, DAL)
- [ ] Engineer assigned and briefed

**Ready to Implement Cover Letter if:**
- [ ] CV Tailoring implemented and tested
- [ ] COVER_LETTER_DESIGN.md updated and approved
- [ ] COVER_LETTER_SPEC.md updated and approved

**Ready to Implement Gap Analysis if:**
- [ ] CV Tailoring and Cover Letter implemented
- [ ] GAP_ANALYSIS_DESIGN.md updated and approved
- [ ] GAP_SPEC.md updated and approved

---

## Next Actions (Immediate)

### Week 1, Day 1 (TODAY)

**Principal Architect:**
1. [ ] Review this action plan
2. [ ] Make 5 architectural decisions (or confirm recommendations)
3. [ ] Create ARCHITECTURAL_DECISIONS.md with ADRs
4. [ ] Brief technical writer on design updates

**Technical Writer:**
1. [ ] Read this action plan
2. [ ] Prepare document update checklist
3. [ ] Set up workspace (open all 6 design docs)
4. [ ] Wait for architectural decisions

---

### Week 1, Days 2-4

**Technical Writer + Engineer:**
1. [ ] Update CV_TAILORING_DESIGN.md (3-4h)
2. [ ] Update CV_TAILORING_SPEC.md (1h)
3. [ ] Peer review CV Tailoring docs
4. [ ] Update COVER_LETTER_DESIGN.md (2-3h)
5. [ ] Update COVER_LETTER_SPEC.md (0.5h)
6. [ ] Peer review Cover Letter docs
7. [ ] Update GAP_ANALYSIS_DESIGN.md (3-4h)
8. [ ] Update GAP_SPEC.md (1h)
9. [ ] Peer review Gap Analysis docs

---

### Week 1, Day 5

**Principal Architect:**
1. [ ] Re-run lightweight review (8 checklist items)
2. [ ] Document results in LIGHTWEIGHT_REVIEW_RESULTS_V2.md
3. [ ] If PASS (≥ 6/8): Sign off and unblock Phase 9
4. [ ] If FAIL: Identify remaining issues and iterate

---

### Week 1, Day 6

**Engineering Lead + Architect:**
1. [ ] Final sign-off meeting
2. [ ] Assign engineers to Phase 9-11
3. [ ] Update project timeline
4. [ ] Announce design phase complete

---

## Appendix: Review Checklist (Quick Reference)

| # | Check | CV Tailoring | Cover Letter | Gap Analysis |
|---|-------|--------------|--------------|--------------|
| 1 | Handler → Logic → DAL | ❌ → ✅ | ❌ → ✅ | ❌ → ✅ |
| 2 | Result[T] Pattern | ✅ | ✅ | ✅ |
| 3 | FVS Integration | ✅ | ✅ | ❌ → ✅ |
| 4 | Gap Responses Input | ❌ → ✅ | ✅ | ❓ → ✅ |
| 5 | Sync/Async Justified | ✅ | ❓ → ✅ | ❌ → ✅ |
| 6 | LLM Model Selection | ✅ | ✅ | ❌ → ✅ |
| 7 | Shared DAL Patterns | ❓ → ✅ | ❓ → ✅ | ❓ → ✅ |
| 8 | AWS Powertools | ❌ → ✅ | ✅ | ❌ → ✅ |

**Legend:**
- ✅ = Already passing
- ❌ = Needs fixing
- ❓ = Unclear, needs clarification
- ❌ → ✅ = Will be fixed by design updates

---

## Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-07 | 1.0 | Claude Sonnet 4.5 | Initial action plan post-review |

---

**End of Next Steps Action Plan**
