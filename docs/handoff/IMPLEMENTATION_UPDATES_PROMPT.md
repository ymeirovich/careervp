# Implementation Updates - Design Doc Refinement Prompt

**Date:** 2026-02-07
**Review Type:** Post-Review Design Doc Updates
**Duration:** 4-6 hours
**Deliverables:** Updated design docs, specs, and task files for CV Tailoring, Cover Letter, and Gap Analysis

---

## 🎯 MISSION STATEMENT

You are updating the **design documentation** for CV Tailoring, Gap Analysis, and Cover Letter features based on findings from:
1. **Lightweight Architecture Review** (pre-implementation findings)
2. **Deep Analysis Review** (post-CV Tailoring implementation findings)

Your role is to **incorporate architectural recommendations** into design docs, specs, and task files to ensure Cover Letter and Gap Analysis avoid the same issues found in CV Tailoring.

Think of yourself as a **Technical Writer** translating architecture review findings into actionable design improvements.

---

## ✅ PREREQUISITES (MUST BE COMPLETE)

**Before starting this work, verify ALL of these exist:**

- [ ] **`/docs/architecture/LIGHTWEIGHT_REVIEW_RESULTS.md`** - Pre-implementation review results
- [ ] **`/docs/architecture/DEEP_ANALYSIS_RESULTS.md`** - Post-implementation review results (if CV Tailoring is complete)
- [ ] **Action items list** from review results (what needs to be fixed)

**If ANY of these are missing, STOP. Run the reviews first.**

---

## 📚 REQUIRED READING (60 minutes - DO NOT SKIP)

Read these documents in order before starting updates:

### 1. Review Results (Understand What Needs to Change)
- [ ] **`/docs/architecture/LIGHTWEIGHT_REVIEW_RESULTS.md`** - Pre-implementation findings
- [ ] **`/docs/architecture/DEEP_ANALYSIS_RESULTS.md`** - Post-implementation findings (if available)
- [ ] **Action Items sections** from both reviews

### 2. Architecture Review Framework (Understand the Standards)
- [ ] **`/docs/architecture/ARCHITECTURE_REVIEW_PLAN.md`** - Review methodology and quality gates

### 3. Current Design Docs (What Will Be Updated)
- [ ] **`/docs/architecture/CV_TAILORING_DESIGN.md`** - CV Tailoring design
- [ ] **`/docs/architecture/COVER_LETTER_DESIGN.md`** - Cover Letter design
- [ ] **`/docs/architecture/GAP_ANALYSIS_DESIGN.md`** - Gap Analysis design

### 4. Spec Files (API Contracts)
- [ ] **`/docs/specs/cv-tailoring/CV_TAILORING_SPEC.md`** - CV Tailoring API spec
- [ ] **`/docs/specs/cover-letter/COVER_LETTER_SPEC.md`** - Cover Letter API spec
- [ ] **`/docs/specs/gap-analysis/GAP_SPEC.md`** - Gap Analysis API spec

### 5. Task Files (Implementation Guides)
- [ ] Browse all files in `/docs/tasks/09-cv-tailoring/`
- [ ] Browse all files in `/docs/tasks/10-cover-letter/`
- [ ] Browse all files in `/docs/tasks/11-gap-analysis/`

**Total Reading:** ~150 pages (~60 minutes)

---

## 🚫 WHAT YOU ARE NOT DOING

**This is NOT implementation work.** You are updating **documentation only**.

**Do NOT:**
- ❌ Write implementation code (handlers, logic, models)
- ❌ Run tests or build infrastructure
- ❌ Deploy anything
- ❌ Modify actual codebase files in `/src/backend/`

**DO:**
- ✅ Update design docs with review findings
- ✅ Update spec files with corrected API contracts
- ✅ Update task files with refined implementation steps
- ✅ Add new sections based on review recommendations
- ✅ Fix inconsistencies flagged in reviews

---

## 📋 UPDATE WORKFLOW (4 Phases)

### Phase 1: Extract Action Items from Reviews

**Duration:** 30 minutes

**Objective:** Create a consolidated action item list from both review results.

#### Step 1.1: Read Review Results

Open both review result files:
- `/docs/architecture/LIGHTWEIGHT_REVIEW_RESULTS.md`
- `/docs/architecture/DEEP_ANALYSIS_RESULTS.md` (if available)

#### Step 1.2: Extract Action Items

Create a tracking file: `/docs/architecture/REVIEW_ACTION_ITEMS.md`

**Template:**

```markdown
# Architecture Review Action Items

**Date:** [Today's Date]
**Source Reviews:**
- Lightweight Review (Pre-Implementation)
- Deep Analysis Review (Post-CV Tailoring) [if available]

---

## Critical Issues (P0 - Must Fix Before Implementation)

### CV Tailoring

1. **[Issue Title]**
   - **Source:** [Lightweight Review / Deep Analysis]
   - **Finding:** [Description from review]
   - **Action Required:** [What needs to be updated]
   - **Files to Update:**
     - [ ] `/docs/architecture/CV_TAILORING_DESIGN.md` - [specific section]
     - [ ] `/docs/specs/cv-tailoring/CV_TAILORING_SPEC.md` - [specific section]
     - [ ] `/docs/tasks/09-cv-tailoring/[file].md` - [specific section]
   - **Status:** TODO / IN_PROGRESS / DONE

[Repeat for each CV Tailoring critical issue...]

### Cover Letter

1. **[Issue Title]**
   - **Source:** [Review name]
   - **Finding:** [Description]
   - **Action Required:** [What to update]
   - **Files to Update:**
     - [ ] `/docs/architecture/COVER_LETTER_DESIGN.md` - [section]
     - [ ] `/docs/specs/cover-letter/COVER_LETTER_SPEC.md` - [section]
     - [ ] `/docs/tasks/10-cover-letter/[file].md` - [section]
   - **Status:** TODO / IN_PROGRESS / DONE

[Repeat for each Cover Letter critical issue...]

### Gap Analysis

1. **[Issue Title]**
   - **Source:** [Review name]
   - **Finding:** [Description]
   - **Action Required:** [What to update]
   - **Files to Update:**
     - [ ] `/docs/architecture/GAP_ANALYSIS_DESIGN.md` - [section]
     - [ ] `/docs/specs/gap-analysis/GAP_SPEC.md` - [section]
     - [ ] `/docs/tasks/11-gap-analysis/[file].md` - [section]
   - **Status:** TODO / IN_PROGRESS / DONE

[Repeat for each Gap Analysis critical issue...]

---

## High Priority Improvements (P1 - Should Fix)

[Same format as critical issues, organized by feature]

---

## Technical Debt (P2/P3 - Nice to Have)

[Same format, lower priority items]

---

## Cross-Cutting Changes (Affects All Features)

[Issues that apply to CV Tailoring, Cover Letter, AND Gap Analysis]

1. **[Issue Title]**
   - **Finding:** [Description]
   - **Action Required:** [What to update across all features]
   - **Files to Update:**
     - [ ] CV Tailoring: [list files]
     - [ ] Cover Letter: [list files]
     - [ ] Gap Analysis: [list files]
   - **Status:** TODO / IN_PROGRESS / DONE

---

## Summary

**Total Action Items:** X
- Critical (P0): X
- High Priority (P1): X
- Technical Debt (P2/P3): X

**Features Affected:**
- CV Tailoring: X action items
- Cover Letter: X action items
- Gap Analysis: X action items
- Cross-Cutting: X action items

**Estimated Update Time:** X hours
```

---

### Phase 2: Update CV Tailoring Documentation

**Duration:** 60 minutes

**Objective:** Apply all CV Tailoring action items to design docs, specs, and task files.

#### Update Priority
1. Critical issues (P0) first
2. High priority improvements (P1) second
3. Technical debt (P2/P3) last

#### Files to Update

##### 2.1: Update CV_TAILORING_DESIGN.md

**Location:** `/docs/architecture/CV_TAILORING_DESIGN.md`

**Common Updates Based on Review Findings:**

**A. Add Missing Sections**

If review flagged missing sections, add them:

```markdown
## Gap Responses Integration

**Input Schema:**
```python
class CVTailoringRequest(BaseModel):
    cv_id: str
    job_description: str
    gap_responses: Optional[GapAnalysisResponses] = None  # NEW: Added based on review
    preferences: Optional[TailoringPreferences] = None
```

**How Gap Responses Enrich Tailoring:**
- Provides specific examples of achievements to highlight
- Gives context for skills mentioned in CV
- Helps prioritize which experiences to emphasize
- Reduces hallucination risk (LLM uses actual user responses)

**LLM Prompt Integration:**
```python
prompt = f"""
Tailor the CV to the job description.

<cv>{cv_content}</cv>
<job_description>{job_description}</job_description>
<gap_responses>{gap_responses_json}</gap_responses>  <!-- NEW -->

Use gap_responses to provide specific evidence for skills and achievements.
"""
```
```

**B. Fix Inconsistencies Flagged in Review**

If review found VPR uses Result[T] but CV Tailoring design didn't specify it:

```markdown
## Error Handling Strategy

**All logic functions return `Result[T]` pattern:**

```python
from careervp.models.result import Result, ResultCode

async def tailor_cv(
    cv: UserCV,
    job_description: str,
    gap_responses: Optional[GapAnalysisResponses]
) -> Result[TailoredCV]:
    """
    Tailor CV to job description.

    Returns:
        Result[TailoredCV]: Success with tailored CV, or failure with error code
    """
    # Validation
    if not cv or not job_description:
        return Result(
            success=False,
            error="Missing required input",
            code=ResultCode.INVALID_INPUT
        )

    try:
        # Tailoring logic...
        tailored_cv = await generate_tailored_cv(...)
        return Result(success=True, data=tailored_cv)
    except Exception as e:
        logger.error(f"CV tailoring failed: {e}")
        return Result(
            success=False,
            error="Internal error during CV tailoring",
            code=ResultCode.INTERNAL_ERROR
        )
```
```

**C. Add Architecture Diagrams (If Missing)**

If review suggested better visualization:

```markdown
## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                   CV TAILORING ARCHITECTURE                      │
└─────────────────────────────────────────────────────────────────┘

[API Gateway]
     │
     │ POST /api/cv/tailor
     │ { cv_id, job_description, gap_responses }
     │
     ▼
[CV Tailor Handler] ─────────────────────────────────────┐
     │                                                     │
     │ 1. Validate input (Pydantic)                       │
     │ 2. Fetch CV from DynamoDB                          │
     │ 3. Call logic layer                                │
     │ 4. Store result in S3                              │
     │ 5. Return presigned URL                            │
     │                                                     │
     ▼                                                     ▼
[CV Tailoring Logic] ──────> [FVS Validator]      [DynamoDB DAL]
     │                            │                       │
     │ 1. Score relevance         │ Verify IMMUTABLE      │ get_item(cv_id)
     │ 2. Call LLM (Haiku)        │ facts preserved       │ put_item(result)
     │ 3. Validate with FVS       │                       │
     │                            │                       │
     ▼                            ▼                       ▼
[LLM Client] ────> [Claude Haiku 4.5]            [S3 Storage]
     │                                                     │
     │ Generate tailored CV                               │ Store result JSON
     │                                                     │ Return presigned URL
     │                                                     │
     └─────────────────────────────────────────────────────┘
```
```

##### 2.2: Update CV_TAILORING_SPEC.md

**Location:** `/docs/specs/cv-tailoring/CV_TAILORING_SPEC.md`

**Common Updates:**

**A. Update API Request Schema**

Add missing fields flagged in review:

```markdown
### Request Body

```json
{
  "cv_id": "01234567-89ab-cdef-0123-456789abcdef",
  "job_description": "Senior Software Engineer...",
  "gap_responses": {  // NEW: Added based on review
    "question_1": {
      "question": "Describe your experience with AWS...",
      "response": "I have 5 years of AWS experience..."
    }
  },
  "preferences": {
    "tone": "professional",
    "length": "1_page",
    "emphasis": "technical_skills"
  },
  "idempotency_key": "unique-request-id"  // NEW: Added for idempotency
}
```

**Field Descriptions:**
- `gap_responses` (Optional): Gap analysis responses for enriching CV content
- `idempotency_key` (Optional): Prevents duplicate tailoring if request retried
```

**B. Update Response Schema**

Add error codes from Result[T] pattern:

```markdown
### Error Responses

```json
{
  "success": false,
  "error": "CV not found",
  "code": "CV_NOT_FOUND",
  "timestamp": "2026-02-07T12:00:00Z"
}
```

**Error Codes:**
- `INVALID_INPUT` - Missing or invalid request parameters
- `CV_NOT_FOUND` - CV ID does not exist
- `JOB_DESCRIPTION_TOO_SHORT` - Job description < 50 characters
- `JOB_DESCRIPTION_TOO_LONG` - Job description > 50,000 characters
- `FVS_VALIDATION_FAILED` - Tailored CV contains hallucinated facts
- `LLM_ERROR` - LLM API failure
- `TIMEOUT` - Tailoring exceeded 300 seconds
- `INTERNAL_ERROR` - Unexpected server error
```

##### 2.3: Update Task Files

**Location:** `/docs/tasks/09-cv-tailoring/`

**Files to Update:**
- `ARCHITECT_PROMPT.md` - Add any new architectural requirements
- `ENGINEER_PROMPT.md` - Add implementation clarifications
- `README.md` - Update task list if new tasks added
- Individual `task-*.md` files - Add missing steps

**Example Update to ENGINEER_PROMPT.md:**

```markdown
## CRITICAL UPDATE (Feb 2026 - Post-Review)

**Architecture Review Findings:**

The following updates were made based on Lightweight/Deep Architecture Review:

1. **Gap Responses Integration:** All handlers MUST accept `gap_responses` parameter
   - Location: Task 03 - Update request model to include `gap_responses: Optional[GapAnalysisResponses]`

2. **Idempotency Key:** All create operations MUST use `idempotency_key` to prevent duplicates
   - Location: Task 05 - Add GSI on `idempotency_key` field

3. **Result[T] Pattern:** ALL logic functions MUST return `Result[T]`
   - Location: All tasks - No bare exceptions, wrap everything in Result

**Read these review results for context:**
- `/docs/architecture/LIGHTWEIGHT_REVIEW_RESULTS.md`
- `/docs/architecture/DEEP_ANALYSIS_RESULTS.md` (if CV Tailoring already implemented)
```

---

### Phase 3: Update Cover Letter Documentation

**Duration:** 60 minutes

**Objective:** Apply all Cover Letter action items, learning from CV Tailoring.

#### Files to Update

##### 3.1: Update COVER_LETTER_DESIGN.md

**Location:** `/docs/architecture/COVER_LETTER_DESIGN.md`

**Apply Same Patterns as CV Tailoring:**

Since Cover Letter is similar to CV Tailoring (both use Haiku, both are sync, both are template-based), copy the corrections made to CV Tailoring:

```markdown
## IMPORTANT: Apply CV Tailoring Patterns

This design incorporates lessons learned from CV Tailoring implementation:

1. **Gap Responses Integration:** Cover letters MUST accept gap_responses to provide specific examples
2. **Result[T] Pattern:** All logic functions return Result[CoverLetter]
3. **FVS Validation:** Enabled to prevent hallucinated company names or job titles
4. **Idempotency:** Uses idempotency_key GSI to prevent duplicate generation
5. **AWS Powertools:** Logger, Tracer, Metrics for all handlers

**See:** `/docs/architecture/CV_TAILORING_DESIGN.md` for reference implementation
```

**Add Missing Sections:**

If CV Tailoring design was updated with new sections, add equivalent sections to Cover Letter:

```markdown
## Data Flow Diagram

[Copy similar diagram from CV_TAILORING_DESIGN.md, adapted for cover letter]

## Gap Responses Usage in Cover Letter

**Input Schema:**
```python
class CoverLetterRequest(BaseModel):
    cv_id: str
    vpr_id: str  # NEW: Cover letter uses VPR for positioning
    job_description: str
    company_research: CompanyResearchResult
    gap_responses: Optional[GapAnalysisResponses] = None  # NEW
```

**How Gap Responses Enrich Cover Letter:**
- Provides specific stories for "why I'm a fit" section
- Gives examples of problem-solving for achievements section
- Helps personalize the letter with real user experiences
```

##### 3.2: Update COVER_LETTER_SPEC.md

**Location:** `/docs/specs/cover-letter/COVER_LETTER_SPEC.md`

**Apply Same Updates as CV Tailoring Spec:**

Add gap_responses field, idempotency_key, Result[T] error codes.

##### 3.3: Update Task Files

**Location:** `/docs/tasks/10-cover-letter/`

Add post-review notes to ENGINEER_PROMPT.md, update task steps if needed.

---

### Phase 4: Update Gap Analysis Documentation

**Duration:** 60 minutes

**Objective:** Apply all Gap Analysis action items, ensure it follows proven patterns.

#### Files to Update

##### 4.1: Update GAP_ANALYSIS_DESIGN.md

**Location:** `/docs/architecture/GAP_ANALYSIS_DESIGN.md`

**Key Differences from CV Tailoring:**
- Uses **Sonnet 4.5** (strategic reasoning, not template)
- Generates **questions**, not tailored content
- Stores **user responses** for reuse across features

**Apply Common Patterns:**

```markdown
## Architecture Alignment

Gap Analysis follows the same architectural patterns as VPR and CV Tailoring:

1. **Handler → Logic → DAL:** Strict layered architecture
2. **Result[T] Pattern:** All logic functions return Result[GapAnalysisQuestions]
3. **AWS Powertools:** Logger, Tracer, Metrics for observability
4. **Shared DAL:** Uses dynamo_dal_handler.py for all DynamoDB operations
5. **FVS Validation:** Enabled to verify questions reference actual CV skills

**Unique to Gap Analysis:**
- **Model:** Claude Sonnet 4.5 (strategic reasoning required)
- **Output:** Stores user responses in `gap_analysis_responses` table for reuse
- **Integration:** Responses used by VPR, CV Tailoring, Cover Letter
```

**Add Response Storage Section:**

```markdown
## Gap Response Storage & Reuse

**Storage Table:** `gap_analysis_responses`

**Schema:**
```python
{
  "user_id": "user-123",  # Partition key
  "response_id": "resp-456",  # Sort key
  "application_id": "app-789",  # Which job application
  "question": "Describe your AWS experience...",
  "response": "I have 5 years of AWS experience...",
  "created_at": "2026-02-07T12:00:00Z",
  "ttl": 7776000  # 90 days (responses expire after 90 days)
}
```

**GSI:** `application-id-index` (query all responses for an application)

**Reuse Pattern:**
```python
# When generating VPR/CV/Cover Letter
gap_responses = dal.query_by_gsi(
    table_name="gap_analysis_responses",
    gsi_name="application-id-index",
    key_value=application_id
)

# Pass to LLM prompt
prompt = f"""
Generate VPR using CV and gap responses:
<cv>{cv_content}</cv>
<gap_responses>{gap_responses_json}</gap_responses>
"""
```
```

##### 4.2: Update GAP_SPEC.md

**Location:** `/docs/specs/gap-analysis/GAP_SPEC.md`

**Add Response Submission Endpoint:**

```markdown
## POST /api/gap-analysis/responses

Submit user's answers to gap analysis questions.

### Request Body

```json
{
  "application_id": "app-789",
  "responses": [
    {
      "question_id": "q1",
      "question": "Describe your AWS experience...",
      "response": "I have 5 years of AWS experience..."
    },
    {
      "question_id": "q2",
      "question": "Tell me about a time you led a team...",
      "response": "At my previous role, I led a team of 5 engineers..."
    }
  ]
}
```

### Response

```json
{
  "success": true,
  "response_ids": ["resp-123", "resp-456"],
  "stored_count": 2,
  "message": "Gap analysis responses stored successfully"
}
```

**These responses will be used by:**
- VPR generation
- CV tailoring
- Cover letter generation
- Interview prep report
```

##### 4.3: Update Task Files

**Location:** `/docs/tasks/11-gap-analysis/`

**Add Response Storage Task:**

If review flagged that response storage wasn't clearly documented, add a new task:

```markdown
### TASK 06: Gap Response Storage

**File:** `src/backend/careervp/handlers/gap_response_submit_handler.py` (new)
**Purpose:** Store user's gap analysis responses for reuse
**Complexity:** Medium | **Duration:** 2 hours | **Tests:** 20-25

#### Implementation Steps

1. **Create handler** with these capabilities:
   - Accept application_id and array of responses
   - Validate responses (non-empty, max 5000 chars each)
   - Store each response in `gap_analysis_responses` table
   - Return success with response_ids

2. **Implement storage logic:**
   ```python
   def store_gap_responses(
       user_id: str,
       application_id: str,
       responses: list[GapResponse]
   ) -> Result[list[str]]:
       """Store gap analysis responses for reuse."""
       response_ids = []
       for resp in responses:
           response_id = generate_id()
           item = {
               "user_id": user_id,
               "response_id": response_id,
               "application_id": application_id,
               "question": resp.question,
               "response": resp.response,
               "created_at": utc_now(),
               "ttl": int(time.time()) + 7776000  # 90 days
           }
           dal.put_item("gap_analysis_responses", item)
           response_ids.append(response_id)
       return Result(success=True, data=response_ids)
   ```

3. **Run tests:**
   ```bash
   uv run pytest tests/unit/test_gap_response_storage.py -v
   ```
```

---

### Phase 5: Update Test Documentation

**Duration:** 30 minutes

**Objective:** Update test files based on review findings.

#### Test Directories to Review

- `/tests/cv-tailoring/`
- `/tests/cover-letter/`
- `/tests/gap_analysis/`

**Common Updates:**

##### A. Add Missing Test Cases

If review flagged missing tests:

```markdown
## NEW TEST CASES (Post-Review)

**Added based on Architecture Review findings:**

### Test Gap Responses Integration

```python
def test_cv_tailoring_with_gap_responses():
    """Test that gap responses are used in CV tailoring."""
    # Setup
    cv = create_test_cv()
    job_desc = "Senior Engineer..."
    gap_responses = {
        "q1": {"question": "...", "response": "I have 5 years..."}
    }

    # Execute
    result = tailor_cv(cv, job_desc, gap_responses)

    # Assert
    assert result.success
    assert "5 years" in result.data.experience_section  # Gap response used
```

### Test Idempotency

```python
def test_cv_tailoring_idempotency():
    """Test that duplicate requests return same result."""
    # First request
    result1 = submit_cv_tailoring_job(cv_id, job_desc, idempotency_key="key123")

    # Duplicate request (same idempotency_key)
    result2 = submit_cv_tailoring_job(cv_id, job_desc, idempotency_key="key123")

    # Assert same job_id returned
    assert result1.job_id == result2.job_id
```

### Test Result[T] Error Handling

```python
def test_cv_tailoring_cv_not_found():
    """Test Result[T] pattern for CV not found error."""
    result = tailor_cv(cv_id="nonexistent", job_desc="...")

    assert not result.success
    assert result.code == ResultCode.CV_NOT_FOUND
    assert "not found" in result.error.lower()
```
```

##### B. Update Test Coverage Targets

If review suggested higher coverage:

```markdown
## Coverage Requirements (Updated Post-Review)

**Minimum Coverage:** 90% (increased from 80%)

**Per-Module Requirements:**
- Handlers: ≥ 95% (critical path)
- Logic: ≥ 90% (business rules)
- Models: ≥ 85% (serialization/validation)
- Utils: ≥ 90% (reusable components)

**How to Check:**
```bash
uv run pytest --cov=careervp --cov-report=term-missing
uv run pytest --cov=careervp --cov-report=html
open htmlcov/index.html
```
```

---

## 📝 FINAL DELIVERABLE: UPDATE SUMMARY

Create this file: `/docs/architecture/IMPLEMENTATION_UPDATES_SUMMARY.md`

**Template:**

```markdown
# Implementation Updates Summary

**Date:** [Today's Date]
**Updater:** [Your Name/Agent ID]
**Source Reviews:**
- Lightweight Architecture Review (Pre-Implementation)
- Deep Analysis Review (Post-CV Tailoring) [if available]

---

## Executive Summary

**Files Updated:** X files across 3 features
**Action Items Completed:** X/X (Y%)

| Feature | Files Updated | Critical Fixes | High Priority Fixes | Technical Debt Addressed |
|---------|---------------|----------------|---------------------|--------------------------|
| CV Tailoring | X | X | X | X |
| Cover Letter | X | X | X | X |
| Gap Analysis | X | X | X | X |

**Key Changes:**
1. Added gap_responses integration to all features
2. Updated all designs to use Result[T] pattern
3. Added idempotency_key to prevent duplicate operations
4. Clarified FVS validation strategy for each feature
5. Updated test requirements (90% coverage minimum)

---

## Detailed Changes by Feature

### CV Tailoring Updates

#### Architecture Design (`CV_TAILORING_DESIGN.md`)

**Sections Added:**
- [ ] Gap Responses Integration
- [ ] Result[T] Error Handling Pattern
- [ ] Idempotency Strategy
- [ ] Architecture Diagram

**Sections Updated:**
- [ ] LLM Prompt Strategy (added gap_responses usage)
- [ ] FVS Integration (clarified IMMUTABLE vs MUTABLE facts)
- [ ] Error Handling (added ResultCode enum values)

**Changes Made:**
[List specific changes with before/after examples]

#### API Specification (`CV_TAILORING_SPEC.md`)

**Sections Added:**
- [ ] gap_responses field in request schema
- [ ] idempotency_key field in request schema
- [ ] ResultCode error codes in response schema

**Sections Updated:**
- [ ] Error responses (added specific error codes)
- [ ] Field descriptions (clarified optional vs required)

#### Task Files (`/docs/tasks/09-cv-tailoring/`)

**Files Updated:**
- [ ] `ENGINEER_PROMPT.md` - Added post-review notes
- [ ] `task-03.md` - Added gap_responses to request model
- [ ] `task-05.md` - Added idempotency_key GSI
- [ ] `README.md` - Updated task count

---

### Cover Letter Updates

[Same format as CV Tailoring]

---

### Gap Analysis Updates

[Same format as CV Tailoring]

**Additional Changes:**
- [ ] Added response storage endpoint
- [ ] Added response retrieval for reuse
- [ ] Added TTL for automatic cleanup (90 days)

---

## Cross-Cutting Updates

**Changes Applied to All Features:**

1. **Result[T] Pattern Enforcement**
   - All logic functions return `Result[T]`
   - All errors wrapped with ResultCode
   - No bare exceptions in logic layer

2. **Gap Responses Integration**
   - All features accept `gap_responses: Optional[GapAnalysisResponses]`
   - All LLM prompts include gap_responses section
   - Gap responses used to enrich output quality

3. **Idempotency Guarantees**
   - All create operations use `idempotency_key`
   - GSI on idempotency_key for duplicate detection
   - Return existing job_id if duplicate request

4. **AWS Powertools Observability**
   - All handlers use Logger, Tracer, Metrics
   - Structured logging with JSON format
   - X-Ray tracing enabled for all Lambdas

5. **FVS Validation**
   - Enabled for CV Tailoring, Cover Letter, Gap Analysis
   - Disabled for VPR (false positives on target company mentions)
   - Feature-specific rulesets defined

---

## Test Documentation Updates

**Test Files Updated:**
- [ ] `/tests/cv-tailoring/test_gap_responses.py` - NEW
- [ ] `/tests/cv-tailoring/test_idempotency.py` - NEW
- [ ] `/tests/cv-tailoring/test_error_handling.py` - UPDATED
- [ ] `/tests/cover-letter/test_gap_responses.py` - NEW
- [ ] `/tests/gap_analysis/test_response_storage.py` - NEW

**Coverage Requirements Updated:**
- Minimum: 90% (increased from 80%)
- Critical path (handlers): 95%

---

## Action Items Completed

### Critical (P0) - All Completed

- [x] Add gap_responses to all features
- [x] Implement Result[T] pattern everywhere
- [x] Add idempotency_key to prevent duplicates
- [x] Clarify FVS validation strategy

### High Priority (P1) - Completed

- [x] Update test requirements (90% coverage)
- [x] Add architecture diagrams to design docs
- [x] Document error codes in specs

### Technical Debt (P2/P3) - Deferred

- [ ] Add French language support hooks (P2)
- [ ] Optimize DynamoDB access patterns (P3)
- [ ] Add performance benchmarking (P3)

**Deferred Items:** Captured in `/docs/architecture/TECHNICAL_DEBT.md`

---

## Verification Checklist

**Before marking this work complete, verify:**

- [ ] All critical (P0) action items addressed
- [ ] All design docs updated with new sections
- [ ] All spec files updated with new fields/error codes
- [ ] All task files updated with implementation clarifications
- [ ] Test documentation updated with new test cases
- [ ] Cross-cutting changes applied consistently to all 3 features
- [ ] Update summary reviewed by architect

---

## Next Steps

1. **Review Updated Docs:** Architect should review all updated design docs
2. **Validate Consistency:** Run automated checks (if available) to verify consistency
3. **Begin Implementation:** CV Tailoring, Cover Letter, Gap Analysis can now be implemented with updated designs
4. **Schedule Follow-Up:** Plan Deep Analysis review after CV Tailoring is complete

---

## Sign-Off

**Documentation Updater:** [Your Name]
**Date:** [Today's Date]

**Status:** COMPLETE / IN_PROGRESS / BLOCKED

**Notes:**
[Any final notes or context]

---

**End of Implementation Updates Summary**
```

---

## 🚀 NEXT STEPS AFTER UPDATES

### If All Updates Complete:
1. Get architect review of updated docs
2. Begin implementation using updated designs
3. Schedule Deep Analysis after CV Tailoring complete

### If Updates Incomplete:
1. Document blockers in update summary
2. Create GitHub issues for remaining work
3. Schedule follow-up to complete updates

---

## 💡 TIPS FOR SUCCESS

1. **Start with Cross-Cutting Changes:** If a change applies to all 3 features, update all 3 at once to ensure consistency.

2. **Copy Patterns from CV Tailoring:** Cover Letter and CV Tailoring are very similar. Once you update CV Tailoring design, copy those sections to Cover Letter.

3. **Use Find & Replace:** If adding a field like `gap_responses` to all features, use find & replace to update all spec files at once.

4. **Document Why:** When adding a section based on review findings, add a note like:
   ```markdown
   ## Gap Responses Integration

   **Added:** Feb 2026 (Post-Architecture Review)
   **Reason:** Review flagged missing gap_responses integration across all features
   ```

5. **Update Table of Contents:** When adding new sections, update the TOC in each design doc.

6. **Cross-Reference:** Link between docs using relative paths:
   ```markdown
   See [CV_TAILORING_DESIGN.md](CV_TAILORING_DESIGN.md#gap-responses-integration) for reference pattern.
   ```

7. **Track Progress:** Use the action items file to check off each update as you complete it.

---

## ⚠️ COMMON PITFALLS TO AVOID

❌ **Don't copy-paste blindly** - Adapt patterns to each feature's specifics
❌ **Don't skip Gap Analysis** - It's different (uses Sonnet, stores responses)
❌ **Don't forget test docs** - Update test files too
❌ **Don't miss task files** - Engineers follow task files, not just design docs
❌ **Don't add implementation code** - This is docs only

✅ **Do maintain consistency** - All 3 features should follow same patterns
✅ **Do document why** - Future readers should know why changes were made
✅ **Do cross-reference** - Link between related sections
✅ **Do update TOCs** - Keep tables of contents current
✅ **Do get review** - Have architect review updated docs

---

**Good luck with your documentation updates! These improvements will ensure Cover Letter and Gap Analysis avoid the same issues found in CV Tailoring.**

---

**End of Implementation Updates Handoff Prompt**
