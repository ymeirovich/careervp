# Gap Analysis Integration Refactoring Plan

**Date:** 2026-02-05
**Status:** Architecture Planning - Ready for Claude Code Specification
**Objective:** Enable gap responses to flow through VPR, CV Tailoring, and Cover Letter generation

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Target State](#target-state)
4. [Data Flow Architecture](#data-flow-architecture)
5. [Component-by-Component Changes](#component-by-component-changes)
6. [DAL Extension Requirements](#dal-extension-requirements)
7. [Model Updates](#model-updates)
8. [Logic Layer Changes](#logic-layer-changes)
9. [Handler Layer Changes](#handler-layer-changes)
10. [Test Coverage Requirements](#test-coverage-requirements)
11. [Infrastructure Updates](#infrastructure-updates)
12. [Migration Strategy](#migration-strategy)
13. [Dependencies](#dependencies)
14. [Risk Assessment](#risk-assessment)

---

## Executive Summary

### Problem Statement

Users have relevant experience that doesn't appear in their CV. The Gap Analysis feature generates targeted questions to help users articulate this hidden experience. However, the current architecture cannot persist and propagate these responses to downstream artifacts (VPR, CV Tailoring, Cover Letter).

### Solution Overview

Extend the data access layer to store gap responses separately, modify VPR to persist and retrieve gap responses, update CV Tailoring and Cover Letter to consume gap responses, and implement the complete Gap Analysis feature.

### Key Decisions

| Decision | Rationale |
|----------|-----------|
| Store gap responses separately | Responses needed for 3 artifacts; avoids duplication; allows optional use |
| Async pattern for Gap Analysis | Prevents Lambda timeout during LLM question generation |
| CV → VPR → Cover Letter priority | VPR is foundation; CV uses VPR output; Cover Letter uses both |
| Backwards compatibility | All features work without gap responses |

---

## Current State Analysis

### Existing Components

```
src/backend/careervp/
├── logic/
│   ├── vpr_generator.py         # ✅ Has gap_responses in prompt, but not stored
│   ├── cv_parser.py             # ✅ Exists
│   ├── company_research.py      # ✅ Exists
│   └── fvs_validator.py         # ✅ Exists
├── handlers/
│   ├── cv_upload_handler.py     # ✅ Exists
│   ├── vpr_handler.py           # ✅ Exists
│   └── company_research_handler.py  # ✅ Exists
├── models/
│   ├── cv.py                    # ✅ UserCV exists
│   ├── job.py                   # ✅ GapResponse model exists
│   ├── vpr.py                   # ✅ VPRRequest has gap_responses (optional)
│   └── result.py                # ✅ Result pattern exists
└── dal/
    └── dynamo_dal_handler.py    # ⚠️ Only CV and VPR storage; NO gap_responses
```

### What's Missing

| Component | Status | Issue |
|-----------|--------|-------|
| `gap_analysis.py` | MISSING | Logic for question generation |
| `gap_handler.py` | MISSING | Endpoint for gap analysis |
| `gap_analysis_prompt.py` | MISSING | Prompt templates |
| `gap_analysis.py` models | MISSING | Request/Response models |
| DAL: save_gap_responses | MISSING | Cannot persist user answers |
| DAL: get_gap_responses | MISSING | Cannot retrieve for artifacts |
| VPR: persist gap_responses | MISSING | Gap responses not stored with VPR |
| CV Tailoring: gap_responses | MISSING | Not in model/prompt |
| Cover Letter: gap_responses | MISSING | Tasks incomplete |

---

## Target State

### End-to-End User Flow

```
1. User uploads CV
   ↓ (cv_upload_handler.py)
2. User provides job posting + company URL
   ↓ (company_research_handler.py)
3. User requests Gap Analysis
   ↓ (gap_handler.py - async)
4. Background: Generate questions via LLM
   ↓ (gap_analysis.py)
5. Return questions to UI
   ↓
6. User responds (optional) → Submit
   ↓ (gap_submit_endpoint - NEW)
7. Store gap_responses in DynamoDB
   ↓ (dal.save_gap_responses)
8. Trigger VPR generation (or user manually)
   ↓ (vpr_handler.py)
   ↓ Retrieve gap_responses from DAL
9. VPR generated WITH gap responses
   ↓ Store VPR + gap_responses together
10. CV Tailoring retrieves gap_responses
    ↓ (dal.get_gap_responses)
11. Cover Letter retrieves gap_responses
    ↓ (dal.get_gap_responses)
12. All artifacts include gap response insights
```

### Data Flow Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   User CV   │     │Job Posting  │     │Company URL  │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                           ▼
               ┌───────────────────────┐
               │  Gap Analysis (Async) │
               │  - gap_handler.py     │
               │  - gap_analysis.py    │
               └───────────┬───────────┘
                           │
                           ▼
               ┌───────────────────────┐
               │  Gap Questions (UI)   │
               └───────────┬───────────┘
                           │
                           ▼
               ┌───────────────────────┐
               │ User Responses (opt)  │
               │ - CV_IMPACT           │
               │ - INTERVIEW_ONLY      │
               └───────────┬───────────┘
                           │
                           ▼
               ┌───────────────────────┐
               │  DAL: save_gap_resp   │
               └───────────┬───────────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ VPR Gen     │   │ CV Tailor   │   │ Cover Letter│
│ - retrieve  │   │ - retrieve  │   │ - retrieve  │
│ - persist   │   │ - use in    │   │ - use in    │
│ - use in    │   │   prompt    │   │   prompt    │
│   prompt    │   │             │   │             │
└─────────────┘   └─────────────┘   └─────────────┘
```

---

## Data Flow Architecture

### Gap Responses Schema

```python
# DynamoDB Item Structure
{
    "pk": "APPLICATION#application_id",
    "sk": "GAP_RESPONSES",
    "user_id": "user_123",
    "application_id": "app_456",
    "job_id": "job_789",
    "responses": [
        {
            "question_id": "gap_001",
            "question": "You worked as DevOps at Company X...",
            "answer": "I led a team of 5 engineers...",
            "destination": "CV_IMPACT"
        },
        {
            "question_id": "gap_002",
            "question": "Describe your experience with...",
            "answer": "I used AWS Lambda extensively...",
            "destination": "INTERVIEW_ONLY"
        }
    ],
    "created_at": "2026-02-05T10:00:00Z",
    "ttl": 1752076800  # 90 days
}
```

### Access Patterns

| Operation | Key Pattern | GSI Needed |
|-----------|-------------|------------|
| Save gap responses | `pk=APPLICATION#{id}` | No |
| Get by application | `pk=APPLICATION#{id}` | No |
| Get by user/job | User queries VPRs first | Yes (via VPR) |

---

## Component-by-Component Changes

### 1. DAL Layer (`dal/dynamo_dal_handler.py`)

**NEW Methods:**

```python
def save_gap_responses(
    self,
    application_id: str,
    user_id: str,
    job_id: str,
    responses: list[GapResponse]
) -> Result[None]:
    """Persist gap analysis responses."""

def get_gap_responses(
    self,
    application_id: str
) -> Result[list[GapResponse]]:
    """Retrieve gap analysis responses for an application."""

def delete_gap_responses(
    self,
    application_id: str
) -> Result[None]:
    """Delete gap responses (cleanup)."""
```

### 2. Models Layer

#### NEW: `models/gap_analysis.py`

```python
class GapAnalysisRequest(BaseModel):
    user_id: str
    cv_id: str
    job_posting: JobPosting
    language: Literal['en', 'he'] = 'en'

class GapAnalysisResponse(BaseModel):
    questions: list[GapQuestion]
    metadata: dict

class GapQuestion(BaseModel):
    question_id: str
    question: str
    impact: Literal['HIGH', 'MEDIUM', 'LOW']
    probability: Literal['HIGH', 'MEDIUM', 'LOW']
    gap_score: float
```

#### MODIFY: `models/vpr.py`

Add to `VPR` model:
```python
class VPR(BaseModel):
    # ... existing fields ...
    gap_responses: Annotated[
        list[GapResponse],
        Field(default_factory=list, description='Gap analysis responses used in generation')
    ]
```

#### NEW: `models/cv_tailoring.py`

```python
class TailorCVRequest(BaseModel):
    user_id: str
    cv_id: str
    job_id: str
    job_posting: JobPosting
    gap_responses: Annotated[
        list[GapResponse],
        Field(default_factory=list, description='Optional gap analysis responses')
    ]
    # ... other fields
```

#### NEW: `models/cover_letter.py`

```python
class GenerateCoverLetterRequest(BaseModel):
    cv_id: str
    job_id: str
    application_id: str
    company_name: str
    job_title: str
    gap_responses: Annotated[
        list[GapResponse],
        Field(default_factory=list, description='Optional gap analysis responses')
    ]
    preferences: Optional[CoverLetterPreferences] = None
    # ... other fields
```

### 3. Logic Layer

#### NEW: `logic/gap_analysis.py`

```python
async def generate_gap_questions(
    user_cv: UserCV,
    job_posting: JobPosting,
    dal: DalHandler,
    language: str = 'en'
) -> Result[list[GapQuestion]]:
    """Generate gap analysis questions via LLM."""

def calculate_gap_score(
    impact: Literal['HIGH', 'MEDIUM', 'LOW'],
    probability: Literal['HIGH', 'MEDIUM', 'LOW']
) -> float:
    """Calculate priority score: gap_score = (0.7 * impact) + (0.3 * probability)"""
```

#### NEW: `logic/prompts/gap_analysis_prompt.py`

```python
def create_gap_analysis_system_prompt() -> str:
    """System prompt for gap analysis."""

def create_gap_analysis_user_prompt(
    user_cv: UserCV,
    job_posting: JobPosting
) -> str:
    """User prompt with CV and job context."""
```

#### MODIFY: `logic/vpr_generator.py`

In `build_vpr_prompt()`:
- Already includes `gap_responses_json` ✅
- **NEW**: Persist gap_responses in VPR output

In `generate_vpr()`:
- **NEW**: Store gap_responses with VPR in DAL

#### MODIFY: CV Tailoring (implement per tasks)

In prompt template:
- Add gap_responses section
- Use CV_IMPACT responses for bullet point enhancement
- Reference INTERVIEW_ONLY responses in guidance

#### MODIFY: Cover Letter (implement per tasks)

In prompt template:
- Add gap_responses section
- Use responses for narrative paragraphs

### 4. Handler Layer

#### NEW: `handlers/gap_handler.py`

```python
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """
    Handle gap analysis requests.

    POST /api/gap-analysis
    Returns: 202 ACCEPTED { job_id }
    """
    # 1. Parse request
    # 2. Create async job
    # 3. Enqueue to SQS
    # 4. Return 202 with job_id
```

#### NEW: `handlers/gap_worker_handler.py`

```python
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """
    SQS worker for gap analysis processing.

    1. Retrieve user CV from DAL
    2. Call generate_gap_questions()
    3. Save questions to S3
    4. Update job status to COMPLETED
    """
```

#### MODIFY: `handlers/vpr_handler.py`

**NEW Step**: Retrieve gap_responses from DAL before calling `generate_vpr()`

```python
# Get gap responses from DAL
gap_result = dal.get_gap_responses(application_id)
gap_responses = gap_result.data if gap_result.success else []

# Build request with gap_responses
request = VPRRequest(
    application_id=application_id,
    user_id=user_id,
    job_posting=job_posting,
    gap_responses=gap_responses,
    company_context=company_context
)
```

#### MODIFY: CV Tailoring Handler (implement per tasks)

**NEW Step**: Retrieve gap_responses from DAL before calling CV tailoring logic

#### MODIFY: Cover Letter Handler (implement per tasks)

**NEW Step**: Retrieve gap_responses from DAL before calling cover letter logic

#### NEW: `handlers/gap_submit_handler.py` (optional)

```python
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """
    Submit gap analysis responses.

    POST /api/gap-analysis/responses
    Body: { application_id, responses: [...] }
    Returns: 200 OK
    """
    # 1. Parse request
    # 2. Validate user owns application
    # 3. Save to DAL
    # 4. Optionally trigger VPR generation
```

---

## DAL Extension Requirements

### DynamoDB Schema

**Primary Table:** `careervp-applications`

| Item Type | PK | SK | Attributes |
|-----------|----|----|------------|
| CV | `USER#{user_id}` | `CV` | Full CV data |
| VPR | `APPLICATION#{app_id}` | `ARTIFACT#VPR#v{version}` | VPR + gap_responses |
| Gap Responses | `APPLICATION#{app_id}` | `GAP_RESPONSES` | `user_id`, `job_id`, `responses`, `ttl` |

### GSI Requirements

| GSI | Partition Key | Sort Key | Purpose |
|-----|---------------|----------|---------|
| UserVPRsIndex | `user_id` | `sk` | List user's VPRs (already exists) |
| ApplicationIndex | `application_id` | `sk` | Query by application (for gap responses) |

---

## Test Coverage Requirements

### Unit Tests

| File | Coverage Target | Key Tests |
|------|-----------------|-----------|
| `test_gap_analysis_logic.py` | 90%+ | Question generation, scoring algorithm |
| `test_gap_dal.py` | 90%+ | Save, get, delete operations |
| `test_gap_prompt.py` | 90%+ | Prompt formatting, language support |
| `test_vpr_with_gap.py` | 90%+ | VPR with/without gap responses |
| `test_cv_tailoring_with_gap.py` | 90%+ | CV with gap responses |
| `test_cover_letter_with_gap.py` | 90%+ | Cover letter with gap responses |

### Integration Tests

| File | Coverage Target | Key Scenarios |
|------|-----------------|---------------|
| `test_gap_flow.py` | 85%+ | Full gap analysis flow |
| `test_artifact_integration.py` | 85%+ | VPR+CV+Cover Letter with gap data |

### E2E Tests

| File | Coverage Target | Key Scenarios |
|------|-----------------|---------------|
| `test_user_flow.py` | 80%+ | Complete user journey with gap responses |

---

## Infrastructure Updates

### CDK Changes

| File | Change |
|------|--------|
| `infra/careervp/api_construct.py` | Add `/api/gap-analysis` POST endpoint |
| `infra/careervp/api_construct.py` | Add `/api/gap-analysis/{job_id}` GET endpoint |
| `infra/careervp/api_construct.py` | Add `/api/gap-analysis/responses` POST endpoint |
| `infra/careervp/queues.py` | Add SQS queue for gap analysis (if async) |
| `infra/careervp/constants.py` | Add GAP_ANALYSIS feature flag |

### Lambda Configurations

| Function | Memory | Timeout | Runtime |
|----------|--------|---------|---------|
| `gap_handler` | 512MB | 30s | Python 3.11 |
| `gap_worker` | 1024MB | 600s (10min) | Python 3.11 |
| `cv_tailoring` | 512MB | 300s | Python 3.11 |
| `cover_letter` | 512MB | 300s | Python 3.11 |

---

## Migration Strategy

### Phase 1: Backwards Compatibility

All new fields must have defaults:
- `gap_responses: list[GapResponse] = Field(default_factory=list)`
- Existing code continues to work without modification

### Phase 2: Data Migration

```python
# No migration needed - gap_responses optional
# New VPRs with gap_responses stored correctly
# Old VPRs without gap_responses use default empty list
```

### Phase 3: Gradual Rollout

1. Deploy DAL changes (no feature changes)
2. Deploy Gap Analysis (behind feature flag)
3. Deploy VPR retrieval of gap_responses
4. Deploy CV Tailoring with gap_responses
5. Deploy Cover Letter with gap_responses

---

## Dependencies

### Internal Dependencies

```
Gap Analysis
    ↓
DAL: save_gap_responses
    ↓
VPR: get_gap_responses (for retrieval)
    ↓
CV Tailoring: get_gap_responses (for retrieval)
    ↓
Cover Letter: get_gap_responses (for retrieval)
```

### External Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| boto3 | Latest | DynamoDB access |
| pydantic | 2.x | Model validation |
| AWS Powertools | Latest | Lambda observability |
| anthropic | Latest | LLM calls |

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| DAL schema change | HIGH | Add GSI without table migration; new item type only |
| LLM timeout (gap analysis) | MEDIUM | Use async pattern with 10min timeout |
| Data consistency (gap responses) | MEDIUM | Use transaction for save + VPR creation |
| Backwards compatibility | LOW | All new fields have defaults |
| Test coverage gaps | MEDIUM | Require 90%+ coverage for all new code |

---

## Acceptance Criteria

### Functional

- [ ] Gap Analysis generates 3-5 questions per job
- [ ] User can submit gap responses (optional)
- [ ] Gap responses stored in DynamoDB
- [ ] VPR generation retrieves and uses gap responses
- [ ] CV Tailoring retrieves and uses gap responses
- [ ] Cover Letter retrieves and uses gap responses
- [ ] All features work without gap responses (backwards compatible)

### Non-Functional

- [ ] Gap Analysis: < 30s for question generation
- [ ] VPR: < 60s with gap responses
- [ ] CV Tailoring: < 30s with gap responses
- [ ] Cover Letter: < 20s with gap responses
- [ ] All unit tests: 90%+ coverage
- [ ] All integration tests: 85%+ coverage
- [ ] Type checking: mypy --strict passes
- [ ] Code formatting: ruff format passes

---

## Next Steps

1. **Claude Code Specification**: Use the prompt in `/docs/handoff/` to generate:
   - Specs (GAP_SPEC.md, CV_TAILORING_SPEC.md, COVER_LETTER_SPEC.md)
   - Tasks (task-NN-*.md files)
   - Test files (conftest.py, test_*.py)
   - GitHub workflows

2. **Architect Verification**: Review generated specs for completeness

3. **Implementation**: Execute tasks in priority order

4. **Testing**: Verify end-to-end flow with gap responses

---

**Document Version:** 1.0
**Created:** 2026-02-05
**Status:** Ready for Claude Code Specification
