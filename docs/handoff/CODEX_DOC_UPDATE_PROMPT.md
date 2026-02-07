# Codex Implementation Prompt: Documentation Update

**Date:** 2026-02-07
**Task:** Fix blocking architectural inconsistencies in design documents
**Priority:** P0 - BLOCKING (Implementation cannot proceed until complete)
**Estimated Effort:** 4-6 hours

---

## Task Summary

You must update the CareerVP architecture documentation to fix 2 remaining blocking issues identified during the lightweight review. One issue (Gap Analysis model choice) has already been fixed by Minimax.

### Blocking Issues to Fix

| Issue | Document | Status |
|-------|----------|--------|
| 1. Gap Analysis sync/async contradiction | GAP_ANALYSIS_DESIGN.md | **FIX REQUIRED** |
| 2. Gap Analysis model (Haiku→Sonnet) | GAP_ANALYSIS_DESIGN.md | ✅ Already fixed |
| 3. CV Tailoring layering contradiction | CV_TAILORING_DESIGN.md | **FIX REQUIRED** |
| 4. GAP_SPEC.md async remnants | GAP_SPEC.md | **FIX REQUIRED** |

---

## Issue 1: Gap Analysis Sync/Async Contradiction

### Problem

GAP_ANALYSIS_DESIGN.md is internally contradictory:
- **Lines 20-54** declare SYNCHRONOUS pattern
- **Lines 593-610** contain ASYNC worker code (`AsyncTaskHandler`)
- **Lines 670-673** reference SQS batch processing
- **Lines 688-689** mention presigned URLs (async pattern)
- **Line 707** references VPR_ASYNC_DESIGN.md

### Decision

**Keep SYNCHRONOUS** (per NEXT_STEPS_POST_REVIEW.md Decision 1)

### Required Changes

#### Change 1: Delete Async Worker Section (Lines 593-610)

**DELETE this entire section:**
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

**Renumber subsequent sections** (Section 3 becomes the next logical section after Prompt templates)

#### Change 2: Update Concurrency Section (Lines 670-673)

**REPLACE:**
```markdown
### Concurrency
- **SQS batch size:** 1 (one job per worker invocation)
- **Max concurrent workers:** 10 (configurable)
- **Rate limiting:** Respect Claude API rate limits
```

**WITH:**
```markdown
### Concurrency
- **Lambda timeout:** 600 seconds (sync request handling)
- **Max concurrent invocations:** 100 (AWS default, configurable)
- **Rate limiting:** Respect Claude API rate limits
```

#### Change 3: Update Data Privacy Section (Lines 688-689)

**REPLACE:**
```markdown
- S3 results use presigned URLs (expire in 1 hour)
```

**WITH:**
```markdown
- Questions returned directly in API response (sync - no S3 storage needed)
- Gap responses stored in DynamoDB users table with 90-day TTL
```

#### Change 4: Remove Async Reference (Line 707)

**DELETE this line:**
```markdown
- **Async foundation:** [VPR_ASYNC_DESIGN.md](./VPR_ASYNC_DESIGN.md)
```

#### Change 5: Update DynamoDB Storage Schema Section (Lines 483-506)

The current schema shows async job pattern with `gsi1pk`/`gsi1sk` and `result_s3_key`.

**REPLACE the storage schema example with:**
```markdown
### Storage Schema

**DynamoDB Record (Sync Pattern):**
```python
{
    "pk": "GAP#{cv_id}#{job_id}",
    "sk": "ANALYSIS#v1",
    "user_id": "user_123",
    "cv_id": "cv_789",
    "job_id": "job_456",
    "questions": [
        {
            "question_id": "q1-uuid",
            "question": "You worked as a Cloud Engineer...",
            "impact": "HIGH",
            "probability": "HIGH",
            "gap_score": 1.0
        }
    ],
    "questions_count": 5,
    "created_at": "2025-02-04T12:00:00Z",
    "ttl": 1738684800  # 90 days
}
```

**Query Pattern:**
```python
# Fetch gap analysis for specific CV + job combination
response = dal.get_item(
    pk=f"GAP#{cv_id}#{job_id}",
    sk="ANALYSIS#v1"
)
```
```

#### Change 6: Add Gap Responses Storage Section (NEW - after DynamoDB Table section)

**ADD this new section after line 223:**
```markdown
---

## Gap Responses Storage

### Purpose

Store user answers to gap questions for reuse across applications (VPR, CV Tailoring, Cover Letter).

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

### Query Pattern

```python
# Get all gap responses for a user
responses = dal.query_items(
    table_name="careervp-users-table-prod",
    key_condition_expression="pk = :user_id AND begins_with(sk, :prefix)",
    expression_values={
        ":user_id": user_id,
        ":prefix": "RESPONSE#"
    }
)
```

### API Endpoints

**POST /api/gap-responses** - Store new responses
```json
{
  "user_id": "user_123",
  "responses": [
    {
      "question_id": "gap_q_abc",
      "question": "Describe your experience...",
      "answer": "I have 5 years...",
      "destination": "CV_IMPACT",
      "application_id": "app_001"
    }
  ]
}
```

**GET /api/gap-responses?user_id={id}** - Retrieve all responses
```json
{
  "responses": [...],
  "total_count": 45,
  "cv_impact_count": 30,
  "interview_only_count": 15
}
```
```

---

## Issue 2: CV Tailoring Layering Contradiction

### Problem

CV_TAILORING_DESIGN.md has conflicting statements:
- **Lines 164-185** (Architecture Pattern): "NO DIRECT DAL ACCESS" in handler
- **Lines 440, 462** (Workflow): Handler does "Fetch master CV from DAL" and "Store tailored CV...in DAL"

### Decision

**Enforce Strict Layering** (Handler → Logic → DAL) per NEXT_STEPS Decision 3

### Required Change

**REPLACE the workflow diagram (Lines 431-465) with:**

```markdown
### High-Level Flow

```
┌─────────────────┐
│ User Request    │  TailorCVRequest(cv_id, job_description, preferences)
└────────┬────────┘
         │
         ▼
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
│  1. Fetch master CV from DAL (via injected dal)             │
│  2. Extract job requirements (keywords, skills, seniority)  │
│  3. Score each CV section for relevance                     │
│  4. Build tailoring prompt with scored sections             │
│  5. Call LLM (Haiku 4.5) to generate tailored CV            │
│  6. Parse LLM response into TailoredCV model                │
│  7. Validate with FVS (fvs_validator.py)                    │
│  8. If CRITICAL violations: return Result(error=...)        │
│  9. Store tailored CV via DAL (via injected dal)            │
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
```

---

## Issue 3: GAP_SPEC.md Async Remnants

### Problem

GAP_SPEC.md still references async patterns that contradict the sync design:
- **Lines 392-450**: TypeScript client with `submitGapAnalysis` → `pollUntilComplete` pattern
- **Lines 486-593**: OpenAPI schema with `/api/gap-analysis/submit` and `/api/gap-analysis/status/{job_id}` endpoints

### Decision

Update to synchronous API pattern (single POST endpoint with immediate response)

### Required Changes

#### Change 1: Update Frontend Integration Example (Lines 392-450)

**REPLACE the entire TypeScript client section with:**

```markdown
## Frontend Integration Example

### TypeScript Client

```typescript
interface GapAnalysisClient {
  async generateGapQuestions(
    cvId: string,
    jobId: string,
    language: 'en' | 'he' = 'en'
  ): Promise<GapAnalysisResponse> {
    const response = await fetch('/api/gap-analysis', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getJWT()}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        cv_id: cvId,
        job_id: jobId,
        language: language
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to generate gap questions');
    }

    return response.json();
  }
}

// Usage example:
const client = new GapAnalysisClient();
try {
  const result = await client.generateGapQuestions('cv_123', 'job_456');
  console.log(`Generated ${result.questions_count} questions`);
  result.questions.forEach(q => {
    console.log(`[${q.impact}] ${q.question_text}`);
  });
} catch (error) {
  console.error('Gap analysis failed:', error.message);
}
```
```

#### Change 2: Update OpenAPI Schema (Lines 486-593)

**REPLACE the OpenAPI paths section with:**

```yaml
paths:
  /api/gap-analysis:
    post:
      summary: Generate gap analysis questions (synchronous)
      description: Analyzes gaps between CV and job requirements, returns questions immediately
      security:
        - CognitoAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/GapAnalysisRequest'
      responses:
        '200':
          description: Questions generated successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GapAnalysisResponse'
        '400':
          $ref: '#/components/responses/BadRequest'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '504':
          description: Request timeout (>600 seconds)
          content:
            application/json:
              schema:
                $ref: '#/components/responses/Timeout'
```

**And update the schemas section:**

```yaml
components:
  schemas:
    GapAnalysisRequest:
      type: object
      required: [cv_id, job_id]
      properties:
        cv_id:
          type: string
          description: CV identifier
        job_id:
          type: string
          description: Job posting identifier
        language:
          type: string
          enum: [en, he]
          default: en

    GapAnalysisResponse:
      type: object
      properties:
        success:
          type: boolean
        questions:
          type: array
          items:
            $ref: '#/components/schemas/GapQuestion'
        questions_count:
          type: integer
        generated_at:
          type: string
          format: date-time
        model_used:
          type: string
        processing_time_ms:
          type: integer
        cost_estimate:
          type: number
        fvs_validation:
          $ref: '#/components/schemas/FVSValidationResult'
```

#### Change 3: Remove Status Endpoint References

**DELETE these lines/sections:**
- Lines 300-305: Rate limiting for "Status Endpoint"
- Lines 310-317: Timeout table references to "Status Handler Lambda"
- Any other references to `/api/gap-analysis/status/{job_id}`

---

## Verification Checklist

After making all changes, verify:

- [ ] GAP_ANALYSIS_DESIGN.md has NO references to:
  - `AsyncTaskHandler`
  - `GapAnalysisWorker`
  - SQS
  - `result_s3_key`
  - `gsi1pk` / `gsi1sk` (async job pattern)
  - Presigned URLs for gap analysis results
  - VPR_ASYNC_DESIGN.md reference

- [ ] CV_TAILORING_DESIGN.md workflow shows:
  - Handler does NOT access DAL directly
  - Logic layer handles all DAL operations
  - Clear "NO DIRECT DAL ACCESS" in handler box

- [ ] GAP_SPEC.md has:
  - Single `POST /api/gap-analysis` endpoint (sync)
  - NO `/api/gap-analysis/submit` endpoint
  - NO `/api/gap-analysis/status/{job_id}` endpoint
  - NO polling pattern in TypeScript example
  - Updated OpenAPI schema for sync pattern

---

## Reference Files

### Already Fixed (DO NOT MODIFY these lines)

GAP_ANALYSIS_DESIGN.md lines 665-678 were already updated by Minimax:
```markdown
### LLM Latency
- **Expected:** 30-60 seconds for strategic question generation
- **Timeout:** 600 seconds (10 minutes) max
- **Model:** Use Claude Sonnet 4.5 (TaskMode.STRATEGIC) for complex reasoning

### Concurrency
...

### Cost Optimization
- **Token usage:** ~2000 input tokens (CV + job) + ~500 output tokens (5 questions)
- **Cost per analysis:** ~$0.05 (with Sonnet 4.5)
```

### Files to Modify

1. `/docs/architecture/GAP_ANALYSIS_DESIGN.md`
2. `/docs/architecture/CV_TAILORING_DESIGN.md`
3. `/docs/specs/gap-analysis/GAP_SPEC.md`

### Reference Documents (READ ONLY)

- `/docs/architecture/architecture-review/DOCUMENTATION_UPDATE_PLAN.md` - Full update plan
- `/docs/architecture/architecture-review/NEXT_STEPS_POST_REVIEW.md` - Architectural decisions
- `/docs/architecture/LIGHTWEIGHT_REVIEW_RESULTS.md` - Original review findings

---

## Success Criteria

1. All 3 files updated with specified changes
2. No remaining async pattern references in Gap Analysis docs
3. CV Tailoring workflow matches Handler → Logic → DAL architecture
4. Ready for Lightweight Review V2 to pass ≥ 6/8 checks

---

## Notes for Codex

- **DO preserve** the sync architecture sections at the top of GAP_ANALYSIS_DESIGN.md (lines 20-54)
- **DO NOT modify** the already-fixed lines 665-678 (Minimax's Sonnet 4.5 fix)
- **DO add** the Gap Responses Storage section (new requirement from PIPELINE_ANALYSIS_RESULTS.md)
- **DO update** both the Design doc AND the Spec doc for Gap Analysis
- **Renumber sections** as needed after deletions

---

**End of Codex Implementation Prompt**
