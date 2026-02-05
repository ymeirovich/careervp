# CV Tailoring Design

**Date:** 2026-02-04
**Author:** Claude Sonnet 4.5 (Lead Architect)
**Phase:** 9 - CV Tailoring
**Status:** Architecture Complete - Ready for Implementation

---

## Table of Contents

1. [Overview](#overview)
2. [Architectural Decisions](#architectural-decisions)
3. [Relevance Scoring Algorithm](#relevance-scoring-algorithm)
4. [CV Tailoring Workflow](#cv-tailoring-workflow)
5. [FVS Integration](#fvs-integration)
6. [Data Flow](#data-flow)
7. [LLM Prompt Strategy](#llm-prompt-strategy)
8. [Error Handling](#error-handling)
9. [Performance Considerations](#performance-considerations)
10. [Testing Strategy](#testing-strategy)

---

## Overview

### Purpose

The CV Tailoring feature generates a customized resume tailored to a specific job description. It optimizes the user's master CV for relevance to the target role while maintaining factual accuracy through the Fact Verification System (FVS).

### Key Objectives

1. **Maximize Relevance**: Prioritize CV content that aligns with job requirements
2. **Maintain Accuracy**: Preserve all IMMUTABLE facts (dates, companies, roles)
3. **ATS Optimization**: Format and keyword-optimize for Applicant Tracking Systems
4. **Transparency**: Explain what changes were made and why
5. **Speed**: Generate tailored CV in under 30 seconds
6. **Cost Efficiency**: Target $0.005-0.010 per tailoring operation

### Success Metrics

- **Relevance Score**: Average relevance score ≥ 0.75 for included content
- **FVS Compliance**: 100% of IMMUTABLE facts preserved
- **ATS Compatibility**: 90%+ keyword match with job description
- **Latency**: p95 response time < 30 seconds
- **Cost**: Average cost per tailoring < $0.010

---

## Architectural Decisions

### Decision 1: Synchronous Implementation ✅

**Decision:** Use synchronous Lambda pattern (like cv_upload_handler.py)

**Rationale:**
- Consistency with existing handlers (CV Upload, VPR Generator)
- Simpler implementation (no SQS/polling infrastructure)
- Fast enough for user expectations (< 30 seconds)
- Aligns with Phase 11 Gap Analysis pattern

**Trade-offs:**
- ❌ Cannot handle very long-running operations (> 15 minutes)
- ✅ Simpler error handling and debugging
- ✅ Immediate feedback to user
- ✅ Lower infrastructure complexity

**Future Migration Path:** If tailoring exceeds 15 minutes, adopt Phase 10 async pattern (SQS + polling).

---

### Decision 2: LLM Model - Claude Haiku 4.5 ✅

**Decision:** Use Claude Haiku 4.5 (TaskMode.TEMPLATE)

**Rationale:**
- **Cost Optimized**: $0.25 per MTok input, $1.25 per MTok output
- **Fast**: 5-10 second response time (vs 15-30s for Sonnet)
- **Sufficient Quality**: Template-based tailoring doesn't require strategic reasoning
- **Proven Pattern**: Same model used for Cover Letter generation

**Estimated Costs per Tailoring:**
```
Input tokens:  ~8,000 tokens  (CV + Job Description + Prompt)
Output tokens: ~3,000 tokens  (Tailored CV)

Cost = (8,000 * $0.25 / 1M) + (3,000 * $1.25 / 1M)
     = $0.002 + $0.00375
     = $0.00575 per tailoring
```

**Fallback Strategy:** If Haiku produces low-quality tailoring (relevance score < 0.60), retry with Sonnet 4.5.

---

### Decision 3: Timeout - 300 Seconds ✅

**Decision:** 300 seconds (5 minutes) via asyncio.wait_for()

**Rationale:**
- Haiku typical response: 5-10 seconds
- Buffer for retries: 3x attempts = 30 seconds max
- Network latency buffer: 30 seconds
- Total: ~60 seconds typical, 300 seconds max safety

**Implementation:**
```python
import asyncio

async def tailor_cv_with_llm(cv: UserCV, job_description: str, llm_client: LLMClient) -> str:
    try:
        response = await asyncio.wait_for(
            llm_client.generate(
                messages=[...],
                model="claude-haiku-4-5",
                max_tokens=4096
            ),
            timeout=300.0  # 5 minutes
        )
        return response
    except asyncio.TimeoutError:
        raise TimeoutError("LLM call timed out after 300 seconds")
```

---

### Decision 4: Storage Strategy - DynamoDB Artifacts ✅

**Decision:** Store tailored CVs as DynamoDB artifacts with 90-day TTL

**Schema:**
```python
PK: user_id                                        # Partition key
SK: ARTIFACT#CV_TAILORED#{cv_id}#{job_id}#v{version}  # Sort key
TTL: current_timestamp + 7776000                   # 90 days in seconds
```

**Example:**
```json
{
  "pk": "user_123",
  "sk": "ARTIFACT#CV_TAILORED#cv_abc#job_xyz#v1",
  "artifact_type": "CV_TAILORED",
  "cv_id": "cv_abc",
  "job_id": "job_xyz",
  "version": 1,
  "tailored_cv": { ... },
  "changes_summary": ["Emphasized Python skills", "Reordered experience"],
  "relevance_scores": { "experience[0]": 0.95, "experience[1]": 0.78 },
  "fvs_validation": { "is_valid": true, "violations": [] },
  "created_at": "2026-02-04T12:00:00Z",
  "ttl": 1752076800
}
```

**Rationale:**
- Same pattern as other artifacts (VPR, Gap Analysis)
- Easy retrieval by user_id + cv_id + job_id
- Automatic cleanup via TTL
- Version support for re-tailoring

---

## Relevance Scoring Algorithm

### Overview

The relevance scoring algorithm quantifies how well each CV section aligns with the job requirements. Sections with low relevance scores may be de-emphasized or excluded.

### Scoring Components

```python
relevance_score = (
    0.40 × keyword_match_score +
    0.35 × skill_alignment_score +
    0.25 × experience_relevance_score
)

where all scores are in range [0.0, 1.0]
```

### Component Definitions

#### 1. Keyword Match Score (40% weight)

**Purpose:** Measure overlap between CV section keywords and job description keywords

**Algorithm:**
```python
def calculate_keyword_match_score(cv_section: str, job_keywords: list[str]) -> float:
    """
    Calculate keyword match score using TF-IDF similarity.

    Args:
        cv_section: Text from CV section (experience description, skills, etc.)
        job_keywords: Extracted keywords from job description

    Returns:
        Score from 0.0 (no match) to 1.0 (perfect match)
    """
    cv_tokens = tokenize(cv_section.lower())
    job_tokens = set(kw.lower() for kw in job_keywords)

    # Count matching keywords
    matches = sum(1 for token in cv_tokens if token in job_tokens)

    # Normalize by job keyword count
    if len(job_tokens) == 0:
        return 0.0

    return min(matches / len(job_tokens), 1.0)
```

**Example:**
```
Job Keywords: ["python", "django", "rest", "api", "postgresql"]
CV Section: "Built REST APIs using Python and Django with PostgreSQL database"

Matches: python=1, django=1, rest=1, api=1, postgresql=1 → 5/5 = 1.0
```

#### 2. Skill Alignment Score (35% weight)

**Purpose:** Measure how well CV skills match required job skills

**Algorithm:**
```python
def calculate_skill_alignment_score(cv_skills: list[str], required_skills: list[str]) -> float:
    """
    Calculate skill alignment score with fuzzy matching.

    Args:
        cv_skills: Skills listed in CV section
        required_skills: Skills required/preferred in job description

    Returns:
        Score from 0.0 (no alignment) to 1.0 (perfect alignment)
    """
    if not required_skills:
        return 0.5  # Neutral score if no required skills specified

    matched_skills = 0
    for required_skill in required_skills:
        # Check for exact match or fuzzy match (80% similarity threshold)
        for cv_skill in cv_skills:
            if fuzzy_match(cv_skill, required_skill, threshold=0.80):
                matched_skills += 1
                break

    return matched_skills / len(required_skills)
```

**Example:**
```
Required Skills: ["Python", "Django", "REST APIs", "PostgreSQL", "Docker"]
CV Skills: ["Python", "Django", "RESTful APIs", "Postgres", "Kubernetes"]

Matches:
- Python: exact match (1.0)
- Django: exact match (1.0)
- REST APIs: fuzzy match with "RESTful APIs" (0.9)
- PostgreSQL: fuzzy match with "Postgres" (0.85)
- Docker: no match (0.0)

Score: (1.0 + 1.0 + 0.9 + 0.85 + 0.0) / 5 = 0.75
```

#### 3. Experience Relevance Score (25% weight)

**Purpose:** Measure how relevant the experience is to the target role

**Algorithm:**
```python
def calculate_experience_relevance_score(
    experience: Experience,
    job_title: str,
    job_industry: str,
    years_required: int
) -> float:
    """
    Calculate experience relevance based on title, industry, and seniority.

    Args:
        experience: Work experience entry from CV
        job_title: Target job title
        job_industry: Target industry
        years_required: Years of experience required

    Returns:
        Score from 0.0 (not relevant) to 1.0 (highly relevant)
    """
    score = 0.0

    # Title similarity (40% of experience score)
    title_similarity = fuzzy_match(experience.role, job_title, threshold=0.60)
    score += 0.40 * title_similarity

    # Industry match (30% of experience score)
    if experience.industry and job_industry:
        industry_match = 1.0 if experience.industry.lower() == job_industry.lower() else 0.5
        score += 0.30 * industry_match

    # Seniority alignment (30% of experience score)
    experience_years = calculate_years(experience.dates)
    seniority_match = min(experience_years / max(years_required, 1), 1.0)
    score += 0.30 * seniority_match

    return score
```

**Example:**
```
Job: "Senior Python Developer" at "FinTech" (5 years required)
Experience: "Python Developer" at "Financial Services" (4 years)

Title similarity: fuzzy_match("Python Developer", "Senior Python Developer") = 0.85
Industry match: "Financial Services" ≈ "FinTech" = 0.5 (related)
Seniority: 4 / 5 = 0.80

Score: (0.40 × 0.85) + (0.30 × 0.5) + (0.30 × 0.80)
     = 0.34 + 0.15 + 0.24
     = 0.73
```

### Relevance Thresholds

| Score Range | Interpretation | Action |
|-------------|----------------|--------|
| 0.80 - 1.00 | Highly relevant | **Feature prominently** (top of CV) |
| 0.60 - 0.79 | Moderately relevant | **Include** in tailored CV |
| 0.40 - 0.59 | Somewhat relevant | **Include** but de-emphasize |
| 0.20 - 0.39 | Low relevance | **Consider excluding** (unless needed for completeness) |
| 0.00 - 0.19 | Not relevant | **Exclude** from tailored CV |

---

## CV Tailoring Workflow

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
│  - Fetch master CV from DAL                                 │
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
│  - Store tailored CV as artifact in DAL                     │
│  - Return TailoredCVResponse with download URL              │
└─────────────────────────────────────────────────────────────┘
```

### Detailed Steps

#### Step 1: Job Requirements Extraction

**Input:** Job description text
**Output:** Structured JobRequirements object

```python
@dataclass
class JobRequirements:
    """Structured job requirements extracted from job description."""

    title: str                      # "Senior Python Developer"
    required_skills: list[str]      # ["Python", "Django", "REST APIs"]
    preferred_skills: list[str]     # ["Docker", "Kubernetes"]
    years_experience: int           # 5
    keywords: list[str]             # ["python", "django", "rest", "api", ...]
    industry: str | None            # "FinTech"
    seniority_level: str            # "Senior" | "Mid" | "Junior"
```

**Extraction Strategy:**
- Use regex patterns for title, years, seniority
- Use LLM (Haiku) for skills extraction (structured output)
- Use TF-IDF for keyword extraction (top 20 keywords)

#### Step 2: Section Relevance Scoring

**For each CV section** (experience, skills, education, projects):
- Calculate keyword_match_score
- Calculate skill_alignment_score
- Calculate experience_relevance_score
- Compute final relevance_score (weighted average)

**Output:**
```python
{
    "experience": [
        {"index": 0, "relevance_score": 0.95},
        {"index": 1, "relevance_score": 0.78},
        {"index": 2, "relevance_score": 0.45}
    ],
    "skills": [
        {"skill": "Python", "relevance_score": 1.00},
        {"skill": "JavaScript", "relevance_score": 0.30}
    ]
}
```

#### Step 3: Content Filtering & Prioritization

**Rules:**
1. **Always include**: All IMMUTABLE facts (dates, companies, roles) regardless of score
2. **Prioritize**: Sections with score ≥ 0.60 (top of CV)
3. **De-emphasize**: Sections with score 0.40-0.59 (bottom of CV)
4. **Exclude**: Sections with score < 0.40 (unless needed for timeline continuity)

**Example:**
```
Original CV Experience (5 jobs):
1. Python Developer at FinTech (2020-2024) → score 0.95 → FEATURE PROMINENTLY
2. Backend Engineer at Startup (2018-2020) → score 0.78 → INCLUDE
3. Data Analyst at Corp (2016-2018) → score 0.45 → DE-EMPHASIZE
4. Junior Dev at Agency (2015-2016) → score 0.25 → EXCLUDE
5. Intern at University (2014-2015) → score 0.10 → EXCLUDE

Tailored CV Experience (3 jobs):
1. Python Developer at FinTech (2020-2024) ← Top position
2. Backend Engineer at Startup (2018-2020)
3. Data Analyst at Corp (2016-2018) ← De-emphasized
```

#### Step 4: LLM Prompt Construction

**Prompt Structure:**
```
System: You are a professional CV tailoring assistant...

User:
# Job Description
[Job description text]

# Master CV
[Full CV with relevance scores annotated]

# Tailoring Instructions
- Emphasize experiences with score ≥ 0.80 (mark as HIGH PRIORITY)
- Include experiences with score ≥ 0.60 (mark as INCLUDE)
- De-emphasize experiences with score 0.40-0.59 (mark as LOW PRIORITY)
- Exclude experiences with score < 0.40 (mark as EXCLUDE)

# FVS RULES (CRITICAL)
IMMUTABLE Facts - NEVER modify:
- Dates: [list of all dates from CV]
- Companies: [list of all companies from CV]
- Roles: [list of all role titles from CV]

VERIFIABLE Facts - Can reframe but must have source:
- Skills: [list of all skills from CV]

FLEXIBLE Content - Full creative liberty:
- Professional summary
- Achievement descriptions (as long as IMMUTABLE facts preserved)

# Output Format
Return a JSON object with TailoredCV structure...
```

#### Step 5: LLM Response Parsing

**Expected LLM Output:**
```json
{
  "full_name": "John Doe",
  "contact_info": { "email": "john@example.com", "phone": "+1234567890" },
  "professional_summary": "Tailored summary emphasizing Python and FinTech...",
  "experience": [
    {
      "company": "FinTech Corp",
      "role": "Python Developer",
      "dates": "2020-2024",
      "description": "Tailored description emphasizing REST APIs...",
      "relevance_score": 0.95
    }
  ],
  "skills": ["Python", "Django", "REST APIs", "PostgreSQL"],
  "education": [...],
  "changes_made": [
    "Emphasized Python and Django experience",
    "Reordered experience to prioritize FinTech background",
    "Excluded early-career roles not relevant to Senior position"
  ]
}
```

**Parsing Strategy:**
```python
import json

def parse_llm_response(llm_output: str) -> TailoredCV:
    """Parse LLM JSON output into TailoredCV model."""
    try:
        data = json.loads(llm_output)
        tailored_cv = TailoredCV(**data)
        return tailored_cv
    except (json.JSONDecodeError, ValidationError) as e:
        raise ValueError(f"Failed to parse LLM response: {e}")
```

#### Step 6: FVS Validation

**Validation Steps:**
1. Call `validate_immutable_facts(baseline_cv, tailored_cv)`
2. Call `validate_verifiable_skills(baseline_cv, tailored_cv)`
3. If CRITICAL violations detected:
   - Log violations
   - Return Result(success=False, code=FVS_HALLUCINATION_DETECTED)
4. If only WARNING violations:
   - Log warnings
   - Proceed with tailored CV (warnings in response)

**Example FVS Check:**
```python
from careervp.logic.fvs_validator import validate_cv_against_baseline

# Prepare baseline dict (FVS format)
baseline = {
    "full_name": master_cv.full_name,
    "immutable_facts": {
        "contact_info": {
            "email": master_cv.contact_info.email,
            "phone": master_cv.contact_info.phone
        },
        "work_history": [
            {
                "company": exp.company,
                "role": exp.role,
                "dates": exp.dates
            }
            for exp in master_cv.experience
        ],
        "education": [
            {
                "institution": edu.institution,
                "degree": edu.degree
            }
            for edu in master_cv.education
        ]
    },
    "verifiable_skills": master_cv.skills
}

# Validate tailored CV
fvs_result = validate_cv_against_baseline(baseline, tailored_cv)

if not fvs_result.success:
    logger.error("FVS validation failed", violations=fvs_result.data.violations)
    return Result(
        success=False,
        error="Tailored CV failed FVS validation",
        code=ResultCode.FVS_HALLUCINATION_DETECTED
    )
```

#### Step 7: Artifact Storage

**Storage in DynamoDB:**
```python
from careervp.dal.dynamo_dal_handler import DynamoDalHandler

dal = DynamoDalHandler(table_name=env_vars.TABLE_NAME)

artifact = {
    "pk": user_id,
    "sk": f"ARTIFACT#CV_TAILORED#{cv_id}#{job_id}#v1",
    "artifact_type": "CV_TAILORED",
    "cv_id": cv_id,
    "job_id": job_id,
    "version": 1,
    "tailored_cv": tailored_cv.model_dump(),
    "changes_summary": tailored_cv.changes_made,
    "relevance_scores": relevance_scores,
    "fvs_validation": fvs_result.data.model_dump(),
    "created_at": datetime.now(UTC).isoformat(),
    "ttl": int(time.time()) + 7776000  # 90 days
}

dal.save_artifact(artifact)
```

---

## FVS Integration

### FVS Tier Definitions (Per system_design.md)

1. **IMMUTABLE**: Facts that must NEVER be modified
   - Work history dates
   - Company names
   - Job titles
   - Degree names
   - Institution names
   - Contact information (email, phone)

2. **VERIFIABLE**: Facts that can be reframed but must have a source
   - Skills listed in master CV
   - Accomplishments mentioned in master CV
   - Certifications

3. **FLEXIBLE**: Content with full creative liberty
   - Professional summaries
   - Achievement descriptions (as long as IMMUTABLE facts preserved)
   - Skill descriptions

### FVS Validation Strategy

**Pre-Tailoring (Baseline Capture):**
```python
def create_fvs_baseline(master_cv: UserCV) -> dict:
    """
    Create FVS baseline from master CV.
    This baseline is used to validate tailored CV.
    """
    return {
        "full_name": master_cv.full_name,
        "immutable_facts": {
            "contact_info": {
                "email": master_cv.contact_info.email,
                "phone": master_cv.contact_info.phone
            },
            "work_history": [
                {
                    "company": exp.company,
                    "role": exp.role,
                    "dates": exp.dates
                }
                for exp in master_cv.experience
            ],
            "education": [
                {
                    "institution": edu.institution,
                    "degree": edu.degree
                }
                for edu in master_cv.education
            ]
        },
        "verifiable_skills": master_cv.skills,
        "flexible_content": {
            "professional_summary": master_cv.professional_summary
        }
    }
```

**Post-Tailoring (Validation):**
```python
from careervp.logic.fvs_validator import validate_cv_against_baseline

baseline = create_fvs_baseline(master_cv)
fvs_result = validate_cv_against_baseline(baseline, tailored_cv)

if fvs_result.data.has_critical_violations:
    # REJECT tailored CV
    return Result(
        success=False,
        error=f"FVS CRITICAL: {len(fvs_result.data.violations)} violations",
        code=ResultCode.FVS_HALLUCINATION_DETECTED
    )
```

### FVS Error Handling

**Scenario 1: CRITICAL Violation (IMMUTABLE fact modified)**
```
Violation: Company name changed from "Google" to "Alphabet"
Action: REJECT tailored CV, return 400 Bad Request
Response:
{
  "success": false,
  "error": "FVS validation failed: 1 critical violation detected",
  "fvs_violations": [
    {
      "field": "work_history.company",
      "expected": "Google",
      "actual": "Alphabet",
      "severity": "CRITICAL"
    }
  ]
}
```

**Scenario 2: WARNING Violation (Skill not in baseline)**
```
Violation: Skill "Rust" added but not in master CV
Action: ACCEPT tailored CV, but include warning in response
Response:
{
  "success": true,
  "tailored_cv": { ... },
  "fvs_warnings": [
    {
      "field": "skills",
      "message": "Skill 'Rust' not found in master CV verifiable skills",
      "severity": "WARNING"
    }
  ]
}
```

---

## Data Flow

### End-to-End Data Flow Diagram

```
┌──────────────┐
│   Frontend   │
│  (React App) │
└──────┬───────┘
       │
       │ POST /api/cv-tailoring
       │ Body: { cv_id, job_description, preferences }
       │
       ▼
┌────────────────────────────────────────┐
│  API Gateway                           │
│  - Authentication (Cognito JWT)        │
│  - Rate limiting (100 req/min)         │
└──────┬─────────────────────────────────┘
       │
       │ Invoke Lambda
       │
       ▼
┌────────────────────────────────────────┐
│  Lambda: cv_tailoring_handler.py       │
│  - Parse TailorCVRequest (Pydantic)    │
│  - Validate input                      │
└──────┬─────────────────────────────────┘
       │
       │ Fetch master CV
       │
       ▼
┌────────────────────────────────────────┐
│  DynamoDB                              │
│  Query: pk=user_id, sk=CV#{cv_id}      │
└──────┬─────────────────────────────────┘
       │
       │ Return UserCV
       │
       ▼
┌────────────────────────────────────────┐
│  Logic: cv_tailoring.py                │
│  1. Extract job requirements           │
│  2. Score CV sections                  │
│  3. Build LLM prompt                   │
└──────┬─────────────────────────────────┘
       │
       │ Call LLM
       │
       ▼
┌────────────────────────────────────────┐
│  Bedrock (Claude Haiku 4.5)            │
│  - Generate tailored CV                │
│  - Timeout: 300 seconds                │
└──────┬─────────────────────────────────┘
       │
       │ Return tailored CV JSON
       │
       ▼
┌────────────────────────────────────────┐
│  Logic: cv_tailoring.py                │
│  4. Parse LLM response                 │
│  5. Validate with FVS                  │
└──────┬─────────────────────────────────┘
       │
       │ Call FVS validator
       │
       ▼
┌────────────────────────────────────────┐
│  Logic: fvs_validator.py               │
│  - Check IMMUTABLE facts               │
│  - Check VERIFIABLE skills             │
└──────┬─────────────────────────────────┘
       │
       │ Return FVSValidationResult
       │
       ▼
┌────────────────────────────────────────┐
│  Logic: cv_tailoring.py                │
│  6. If FVS fails: return error         │
│  7. If FVS passes: continue            │
└──────┬─────────────────────────────────┘
       │
       │ Store artifact
       │
       ▼
┌────────────────────────────────────────┐
│  DynamoDB                              │
│  Put: pk=user_id,                      │
│       sk=ARTIFACT#CV_TAILORED#...      │
└──────┬─────────────────────────────────┘
       │
       │ Return success
       │
       ▼
┌────────────────────────────────────────┐
│  Lambda: cv_tailoring_handler.py       │
│  - Build TailoredCVResponse            │
│  - Return 200 OK                       │
└──────┬─────────────────────────────────┘
       │
       │ HTTP Response
       │
       ▼
┌────────────────────────────────────────┐
│  Frontend                              │
│  - Display tailored CV                 │
│  - Show changes summary                │
│  - Provide download button             │
└────────────────────────────────────────┘
```

---

## LLM Prompt Strategy

### System Prompt

```
You are a professional CV tailoring assistant. Your task is to optimize a candidate's CV for a specific job description while maintaining strict factual accuracy.

# Core Principles
1. NEVER modify IMMUTABLE facts (dates, companies, roles, contact info)
2. Only use VERIFIABLE skills that exist in the source CV
3. Exercise creative liberty in FLEXIBLE content (summaries, descriptions)
4. Optimize for ATS (Applicant Tracking Systems) keyword matching
5. Prioritize relevant experience over chronological completeness

# Output Format
Return a JSON object with the following structure:
{
  "full_name": "...",
  "contact_info": { ... },
  "professional_summary": "...",
  "experience": [ ... ],
  "skills": [ ... ],
  "education": [ ... ],
  "changes_made": [ "...", "..." ]
}
```

### User Prompt Template

```
# Job Description
{{job_description}}

# Master CV (with relevance scores)
Full Name: {{full_name}}
Contact: {{email}}, {{phone}}

Professional Summary:
{{professional_summary}}

Experience:
{{#each experience}}
- [Score: {{relevance_score}}] {{company}} - {{role}} ({{dates}})
  {{description}}
{{/each}}

Skills:
{{#each skills}}
- [Score: {{relevance_score}}] {{skill}}
{{/each}}

Education:
{{#each education}}
- {{institution}} - {{degree}} ({{graduation_date}})
{{/each}}

# Tailoring Instructions
- Emphasize experiences with score ≥ 0.80 (HIGH PRIORITY)
- Include experiences with score ≥ 0.60
- De-emphasize experiences with score 0.40-0.59
- Exclude experiences with score < 0.40 (unless timeline continuity required)

# FVS RULES (CRITICAL - STRICT ENFORCEMENT)
IMMUTABLE Facts - NEVER modify these:
- Dates: {{immutable_dates}}
- Companies: {{immutable_companies}}
- Roles: {{immutable_roles}}
- Email: {{email}}
- Phone: {{phone}}
- Degrees: {{immutable_degrees}}
- Institutions: {{immutable_institutions}}

VERIFIABLE Skills - Can reframe but must exist in source:
{{verifiable_skills}}

FLEXIBLE Content - Full creative liberty:
- Professional summary
- Achievement descriptions (preserve IMMUTABLE facts)

# ATS Optimization
Target keywords from job description:
{{target_keywords}}

Ensure these keywords appear naturally in:
- Professional summary
- Experience descriptions
- Skills section

# Output Requirements
1. Return valid JSON (no markdown code blocks)
2. Preserve all IMMUTABLE facts exactly as provided
3. Include "changes_made" array explaining modifications
4. Optimize experience descriptions for target keywords
5. Keep professional summary under 150 words
```

### Prompt Engineering Best Practices

1. **Explicit FVS Rules**: List exact IMMUTABLE facts in prompt (dates, companies, roles)
2. **Relevance Scores**: Annotate each section with relevance score to guide LLM
3. **Target Keywords**: Provide explicit list of keywords to incorporate
4. **Examples**: Include 1-2 example tailored descriptions (few-shot learning)
5. **Output Format**: Specify exact JSON schema expected in response

---

## Error Handling

### Error Scenarios & Mitigation

| Scenario | Error Code | HTTP Status | Mitigation |
|----------|-----------|-------------|------------|
| Invalid request (missing cv_id) | `INVALID_INPUT` | 400 | Pydantic validation, return clear error message |
| CV not found in database | `CV_NOT_FOUND` | 404 | Check if cv_id exists for user_id |
| Job description too long (> 50K chars) | `JOB_DESCRIPTION_TOO_LONG` | 400 | Enforce 50K character limit in validation |
| LLM timeout (> 300 seconds) | `LLM_TIMEOUT` | 504 | Log timeout, suggest user retry |
| LLM rate limited | `LLM_RATE_LIMITED` | 429 | Exponential backoff (3 retries) |
| LLM returns invalid JSON | `LLM_PARSE_ERROR` | 500 | Log raw response, return generic error |
| FVS CRITICAL violations | `FVS_HALLUCINATION_DETECTED` | 400 | Return violations list, reject tailoring |
| DynamoDB write failure | `STORAGE_ERROR` | 500 | Log error, suggest user retry |

### Retry Logic

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
async def call_llm_with_retry(llm_client: LLMClient, messages: list) -> str:
    """Call LLM with exponential backoff retry."""
    try:
        response = await asyncio.wait_for(
            llm_client.generate(messages=messages, model="claude-haiku-4-5"),
            timeout=300.0
        )
        return response
    except asyncio.TimeoutError:
        logger.warning("LLM call timed out, retrying...")
        raise
    except Exception as e:
        logger.error("LLM call failed", error=str(e))
        raise
```

### Fallback Strategies

**Strategy 1: Sonnet Fallback (Quality Issues)**
```python
# Try Haiku first
haiku_result = await call_llm(model="haiku", ...)

# If relevance score too low, retry with Sonnet
if haiku_result.average_relevance_score < 0.60:
    logger.info("Haiku quality insufficient, falling back to Sonnet")
    sonnet_result = await call_llm(model="sonnet", ...)
    return sonnet_result
```

**Strategy 2: Partial Tailoring (Timeout)**
```python
# If LLM times out, return original CV with basic filtering
if timeout_occurred:
    logger.warning("LLM timeout, returning filtered original CV")
    filtered_cv = filter_cv_by_relevance(master_cv, relevance_scores)
    return Result(
        success=True,
        data=filtered_cv,
        code=ResultCode.PARTIAL_SUCCESS
    )
```

---

## Performance Considerations

### Latency Targets

| Metric | Target | P95 | P99 |
|--------|--------|-----|-----|
| **Total latency** | < 15s | < 25s | < 35s |
| Job requirements extraction | < 2s | < 3s | < 5s |
| Relevance scoring | < 1s | < 2s | < 3s |
| LLM call (Haiku) | < 8s | < 15s | < 25s |
| FVS validation | < 1s | < 2s | < 3s |
| DynamoDB write | < 0.5s | < 1s | < 2s |

### Optimization Strategies

1. **Parallel Operations**: Extract job requirements while fetching CV from DB
2. **Caching**: Cache job requirements extraction for duplicate job descriptions (1-hour TTL)
3. **Batch Processing**: If tailoring multiple CVs for same job, reuse job requirements
4. **Streaming**: Consider streaming LLM response for large CVs (future enhancement)

### Cost Optimization

**Current Cost Model:**
```
Per tailoring operation:
- Haiku input:  ~8,000 tokens × $0.25/MTok = $0.002
- Haiku output: ~3,000 tokens × $1.25/MTok = $0.00375
- DynamoDB:     ~1 write × $0.00000125 = $0.00000125
- Lambda:       ~15s × $0.0000166667/s = $0.00025

Total: ~$0.0060 per tailoring
```

**Optimization Opportunities:**
- **Prompt compression**: Reduce input tokens by 20% → save $0.0004/operation
- **Response truncation**: Request shorter output → save $0.0007/operation
- **Caching**: Avoid re-extraction for duplicate jobs → save $0.002/cached operation

---

## Testing Strategy

### Unit Testing

**Test Coverage Targets:**
- Relevance scoring algorithms: 100% coverage
- FVS integration: 100% coverage
- LLM prompt construction: 90% coverage
- Error handling: 95% coverage

**Key Test Cases:**
1. **Relevance Scoring**:
   - Test keyword_match_score with various overlap levels
   - Test skill_alignment_score with fuzzy matching
   - Test experience_relevance_score with different seniority levels

2. **FVS Validation**:
   - Test IMMUTABLE fact modification detection (dates, companies, roles)
   - Test VERIFIABLE skill source validation
   - Test FLEXIBLE content acceptance

3. **Error Handling**:
   - Test LLM timeout handling
   - Test invalid JSON parsing
   - Test FVS violation rejection

### Integration Testing

**Test Scenarios:**
1. **Happy Path**: Valid CV + job description → tailored CV with high relevance
2. **FVS Rejection**: Tailored CV modifies IMMUTABLE fact → 400 error
3. **LLM Timeout**: Slow LLM response → timeout error
4. **Partial Success**: LLM returns valid but low-quality output → fallback to Sonnet

### End-to-End Testing

**E2E Test Cases:**
1. **Full Flow**: POST /api/cv-tailoring → 200 OK with tailored CV
2. **Download Flow**: Tailored CV artifact → download link generation
3. **Re-Tailoring**: Same CV + different job → new version (v2)

---

## Appendices

### A. Relevance Score Examples

**Example 1: High Relevance (0.95)**
```
Job: "Senior Python Developer at FinTech"
CV Section: "Python Developer at FinTech Startup (2020-2024)"
- Keyword match: 0.95 (python, developer, fintech all present)
- Skill alignment: 1.00 (Python, Django, REST APIs all match)
- Experience relevance: 0.90 (4 years, same industry)
→ Final score: 0.95
```

**Example 2: Low Relevance (0.25)**
```
Job: "Senior Python Developer at FinTech"
CV Section: "Marketing Manager at Retail Company (2015-2017)"
- Keyword match: 0.10 (no technical keywords)
- Skill alignment: 0.20 (some transferable skills)
- Experience relevance: 0.30 (unrelated role and industry)
→ Final score: 0.25
```

### B. FVS Baseline Schema

```json
{
  "full_name": "John Doe",
  "immutable_facts": {
    "contact_info": {
      "email": "john@example.com",
      "phone": "+1234567890"
    },
    "work_history": [
      {
        "company": "Google",
        "role": "Software Engineer",
        "dates": "2020-2024"
      }
    ],
    "education": [
      {
        "institution": "MIT",
        "degree": "BS Computer Science"
      }
    ]
  },
  "verifiable_skills": [
    "Python", "Java", "C++", "Django", "REST APIs"
  ],
  "flexible_content": {
    "professional_summary": "..."
  }
}
```

### C. TailoredCV Model Schema

```python
from pydantic import BaseModel, Field

class TailoredCV(BaseModel):
    """Tailored CV optimized for specific job."""

    # Metadata
    cv_id: str
    job_id: str
    tailored_at: str  # ISO 8601 timestamp

    # CV Content (same structure as UserCV)
    full_name: str
    contact_info: ContactInfo
    professional_summary: str
    experience: list[Experience]
    skills: list[str]
    education: list[Education]

    # Tailoring Metadata
    changes_made: list[str] = Field(
        description="List of changes made to original CV"
    )
    relevance_scores: dict[str, float] = Field(
        description="Relevance scores for each section"
    )
    average_relevance_score: float = Field(
        ge=0.0, le=1.0,
        description="Average relevance score across all sections"
    )

    # FVS Validation
    fvs_validation: FVSValidationResult
```

---

**Document Version:** 1.0
**Last Updated:** 2026-02-04
**Next Review:** After Phase 9 implementation complete
