# JSA Skill Alignment - Implementation Design

**Version:** 1.0
**Date:** 2026-02-09
**Status:** Ready for Implementation
**Owner:** Backend Team

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Component Designs](#3-component-designs)
4. [Data Models](#4-data-models)
5. [API Changes](#5-api-changes)
6. [Implementation Sequence](#6-implementation-sequence)
7. [Testing Strategy](#7-testing-strategy)
8. [Migration Considerations](#8-migration-considerations)

---

## 1. Overview

### 1.1 Purpose

This document provides detailed implementation guidance for aligning CareerVP with the Job Search Assistant (JSA) Skill architecture. The alignment addresses gaps in prompt methodology, verification processes, and introduces missing components.

### 1.2 Scope

| Category | Components |
|----------|------------|
| **Prompt Enhancements** | VPR (6-stage), CV Tailoring (3-step), Cover Letter (scaffolded), Gap Analysis (tagged) |
| **New Components** | Interview Prep Generator, Quality Validator Agent, Knowledge Base |
| **Infrastructure** | API Gateway routes, DynamoDB tables |

### 1.3 Design Principles

1. **Test-First Development**: All changes must pass tests in `tests/jsa_skill_alignment/`
2. **Backward Compatibility**: Existing API contracts must not break
3. **Incremental Rollout**: Each component can be deployed independently
4. **Observable**: All new components include logging and metrics

---

## 2. Architecture

### 2.1 Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway                              │
└─────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  VPR Handler │    │ CV Handler  │    │ Gap Handler │
└─────────────┘    └─────────────┘    └─────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   SQS Queue  │    │   LLM API   │    │   DynamoDB  │
└─────────────┘    └─────────────┘    └─────────────┘
```

### 2.2 Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway                              │
└─────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  VPR Handler │    │ CV Handler  │    │ Gap Handler │
│  (+Quality)  │    │ (+3-step)   │    │ (+tagging)  │
└─────────────┘    └─────────────┘    └─────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   SQS Queue  │    │   LLM API   │    │Knowledge Base│
└─────────────┘    └─────────────┘    └─────────────┘
                              ▲                    │
                              │                    ▼
                       ┌─────────────┐    ┌─────────────┐
                       │   Interview │    │Quality Valid│
                       │   Prep     │    │             │
                       └─────────────┘    └─────────────┘
```

### 2.3 Component Relationships

```
                    ┌─────────────────┐
                    │  User CV (DDB)  │
                    └────────┬────────┘
                             │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│   Company     │  │     VPR       │  │   Gap Analysis│
│   Research    │  │   Generator   │  │   (tagged)    │
└───────┬───────┘  └───────┬───────┘  └───────┬───────┘
        │                  │                  │
        │         ┌───────┴───────┐          │
        │         │               │          │
        ▼         ▼               ▼          ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ CV Tailoring  │  │   Cover      │  │  Interview    │
│ (3-step)      │  │   Letter     │  │  Prep         │
└───────────────┘  └───────────────┘  └───────────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │  Knowledge Base │
                 │  (DDB Table)    │
                 └─────────────────┘
```

---

## 3. Component Designs

### 3.1 VPR Prompt Enhancement (6-Stage)

#### Location
`src/backend/careervp/logic/prompts/vpr_prompt.py`

#### Changes Required

```python
# Current: Single-stage prompt
VPR_GENERATION_PROMPT = """You are an expert career strategist..."""

# New: 6-stage methodology
VPR_GENERATION_PROMPT = """You are an expert career strategist creating a Value Proposition Report (VPR)...

STAGE 1: COMPANY & ROLE RESEARCH
Analyze the company research and identify:
- 3-5 strategic priorities or current challenges
- 5-7 role success criteria from job posting

OUTPUT (Internal): List strategic priorities and role criteria before proceeding.

---

STAGE 2: CANDIDATE ANALYSIS
Parse CV facts and gap responses:
- Identify achievements with quantified outcomes
- Extract 3-5 core differentiators
- Summarize career narrative in ONE sentence

OUTPUT (Internal): List differentiators and career narrative before proceeding.

---

STAGE 3: ALIGNMENT MAPPING
Create reasoning scaffold table with 5-7 minimum alignments...

OUTPUT (Internal): Complete alignment matrix before proceeding.

---

STAGE 4: SELF-CORRECTION & META REVIEW
Before proceeding, perform internal critique:
- Are there any unsupported claims?
- Is logic consistent throughout?
- Would this persuade a senior hiring manager?
- Are arguments evidence-driven and sharp?

OUTPUT (Internal): Note any refinements made.

---

STAGE 5: GENERATE REPORT
[Current VPR structure sections - Executive Summary through Talking Points]

---

STAGE 6: FINAL META EVALUATION
Ask yourself: "How could this report be 20% more persuasive, specific, or actionable?"

Apply those improvements and output the final refined version.
..."""
```

#### Key Requirements

| Stage | Internal Output | Next Stage Input |
|-------|-----------------|------------------|
| 1 | Strategic priorities, role criteria | Alignment mapping |
| 2 | Career narrative, differentiators | Report generation |
| 3 | Alignment table matrix | Self-correction |
| 4 | Refinements made | Meta evaluation |
| 5 | Full report | Meta evaluation |
| 6 | Final refined JSON | Output |

---

### 3.2 CV Tailoring Enhancement (3-Step)

#### Location
`src/backend/careervp/logic/cv_tailoring_prompt.py`

#### Changes Required

```python
# New parameters for build_user_prompt
def build_user_prompt(
    cv: UserCV,
    job_description: str,
    relevance_scores: dict[str, float] | None = None,
    fvs_baseline: FVSBaseline | None = None,
    target_keywords: Iterable[str] | None = None,
    preferences: TailoringPreferences | None = None,
    company_keywords: list[str] | None = None,  # NEW
    vpr_differentiators: list[str] | None = None,  # NEW
) -> str:
```

#### 3-Step Structure

```python
CV_TAILORING_PROMPT = """You are an expert CV writer. Tailor this CV using a 3-STEP PROCESS.

---

STEP 1: ANALYSIS & KEYWORD MAPPING
- Extract core UVP and top 3 Key Differentiators from VPR
- Analyze job posting: extract 12-18 key skills/technologies/responsibilities
- Include company research keywords for ATS optimization
- Review CV facts: Include ONLY experience/skills directly relevant to keywords
- Draft CV with all bullets in CAR/STAR format:
  * Begin with strong action verb
  * Include quantifiable metric (number, percentage, scale)

OUTPUT (Internal): Draft tailored CV

---

STEP 2: SELF-CORRECTION & VERIFICATION
**Verification Check 1 (ATS):**
- Rate keyword match score (1-10) against job posting
- List 3 most critical missing/underrepresented keywords
- If score < 7, plan revisions

**Verification Check 2 (Hiring Manager & Strategy):**
- Does Professional Summary directly align with UVP from VPR?
- Does it address Company's Core Problem?

OUTPUT (Internal): Verification results + revision plan

---

STEP 3: FINAL OUTPUT
Apply revisions based on verification:
- Add missing keywords naturally
- Ensure ATS score >= 8
- Ensure strategic alignment with VPR

---

ATS FORMATTING RULES:
- Standard headers: "Professional Experience", "Education", "Skills"
- Simple bullets (•)
- No tables or columns
- Length: 1-2 pages (max 3 pages)
..."""
```

---

### 3.3 Cover Letter Enhancement

#### New File
`src/backend/careervp/handlers/cover_letter_handler.py`

#### API Contract

```python
@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler(capture_response=False)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """
    POST /api/cover-letter

    Request Body:
    {
        "cv_id": "uuid",
        "job_id": "uuid",
        "user_id": "uuid"
    }

    Response:
    {
        "success": True,
        "data": {
            "cover_letter": "# Heading\n\nParagraph 1...",
            "word_count": 350
        }
    }
    """
```

#### Prompt Structure

```python
COVER_LETTER_PROMPT = """You are an expert cover letter writer. Create EXACTLY 1 page (max 400 words).

---

STEP 1: REFERENCE CLASS PRIMING
Before drafting, internally describe the structure and tone of an exemplary, modern, persuasive cover letter...

---

INPUT DATA:
CV FACTS, JOB INFO, VPR DIFFERENTIATORS, COMPANY CULTURE

---

STEP 2: DRAFT LETTER

**Paragraph 1 (The Hook) - 80-100 words:**
- State role and IMMEDIATELY reference UVP from VPR
- Show research: mention specific company goal, product, or recent announcement

**Paragraph 2 (The Proof Points) - 120-140 words:**
Identify top 3 non-negotiable requirements from job posting.
For EACH requirement:
- Sentence 1: Assert candidate's skill using VPR language
- Sentence 2: Detail specific quantified achievement from CV as proof

**Paragraph 3 (The Close) - 60-80 words:**
- Express enthusiasm
- Clear, confident call to action
- Position candidate as time-saver

---

ANTI-AI DETECTION:
- Natural transitions (not formulaic)
- Vary sentence length (8-25 words)
- Avoid: leverage, delve, robust, streamline
- Use approximations: "nearly 40%" not "39.7%"
..."""
```

---

### 3.4 Gap Analysis Enhancement

#### Location
`src/backend/careervp/handlers/gap_handler.py` (complete lambda_handler)
`src/backend/careervp/logic/prompts/gap_analysis_prompt.py` (enhanced prompt)

#### Enhanced Prompt Structure

```python
GAP_ANALYSIS_ENHANCED_PROMPT = """You are an expert career strategist generating targeted gap analysis questions with contextual tagging.

CRITICAL INSTRUCTIONS:
1. Generate MAXIMUM 10 questions
2. Tag each question: [CV IMPACT] or [INTERVIEW/MVP ONLY]
3. Include strategic intent for each question
4. Skip recurring themes from user history
5. Focus on CRITICAL job requirements only

INPUT DATA:
CV FACTS, RECURRING THEMES, JOB REQUIREMENTS, COMPANY CONTEXT, PREVIOUS GAP RESPONSES

---

QUESTION FORMAT:

### Question {N}

**Requirement:** [Exact quote from job posting]

**Question:** [Targeted question emphasizing quantification]

**Destination:** [CV IMPACT] or [INTERVIEW/MVP ONLY]

**Strategic Intent:** [Why this is being asked]

**Evidence Gap:** [What's missing from the CV]

**Priority:** CRITICAL | IMPORTANT | OPTIONAL

---

RULES:

[CV IMPACT] QUESTIONS (5-7 questions):
- MUST ask for specific numbers: "How many?", "What percentage?"
- Focus on: team sizes, metrics, results, time saved

[INTERVIEW/MVP ONLY] QUESTIONS (3-5 questions):
- Ask about: philosophy, approach, process, soft skills
..."""
```

---

### 3.5 Interview Prep Generator (New)

#### Files to Create

| File | Purpose |
|------|---------|
| `src/backend/careervp/handlers/interview_prep_handler.py` | Lambda handler |
| `src/backend/careervp/logic/interview_prep.py` | Business logic |
| `src/backend/careervp/logic/prompts/interview_prep_prompt.py` | Prompt template |

#### Prompt Structure

```python
INTERVIEW_PREP_PROMPT = """You are an expert interview coach. Generate interview preparation materials.

INPUT DATA:
CV FACTS, JOB REQUIREMENTS, VPR DIFFERENTIATORS, COMPANY RESEARCH

Generate:

1. PREDICTED QUESTIONS (10-15 across 4 categories):
   - Technical Competency (role-specific skills)
   - Behavioral/Cultural Fit (team dynamics, values)
   - Experience & Background (deep-dive on CV)
   - Problem-Solving (hypothetical scenarios)

   For each question, provide:
   **Question:** [The question]
   **STAR Response:**
   - Situation: ...
   - Task: ...
   - Action: ...
   - Result: ...

2. QUESTIONS TO ASK INTERVIEWER (5-7):
   - Insightful questions showing strategic thinking

3. PRE-INTERVIEW CHECKLIST:
   - Company research review
   - CV highlights to emphasize
   - Questions prepared
   - Technical setup (if remote)

4. SALARY NEGOTIATION GUIDANCE:
   - Market rate research
   - Negotiation tactics
   - Total compensation considerations
..."""
```

---

### 3.6 Quality Validator (New)

#### File to Create
`src/backend/careervp/logic/quality_validator.py`

#### Validation Checks

```python
class QualityValidator:
    """Multi-check validation agent for artifact quality."""

    async def validate_vpr(self, vpr: VPRResponse, cv: UserCV, job: JobPosting) -> ValidationResult:
        """Validate VPR against source documents."""
        checks = [
            self._check_fact_verification(vpr, cv),
            self._check_ats_compatibility(vpr, job),
            self._check_anti_ai_detection(vpr),
            self._check_cross_document_consistency(vpr, cv),
            self._check_completeness(vpr),
            self._check_language_quality(vpr),
        ]
        return await self._aggregate_checks(checks)

    async def _check_fact_verification(self, artifact, source) -> CheckResult:
        """Cross-reference all claims against source."""
        # Verify every claim in artifact exists in source
        pass

    async def _check_ats_compatibility(self, artifact, job) -> CheckResult:
        """Check ATS keyword score and formatting."""
        pass

    async def _check_anti_ai_detection(self, artifact) -> CheckResult:
        """Check for banned words and patterns."""
        pass

    async def _check_cross_document_consistency(self, artifact, cv) -> CheckResult:
        """Ensure CV, VPR, Cover Letter alignment."""
        pass

    async def _check_completeness(self, artifact) -> CheckResult:
        """Verify word counts, section counts."""
        pass

    async def _check_language_quality(self, artifact) -> CheckResult:
        """Check spelling, grammar, tone."""
        pass
```

---

### 3.7 Knowledge Base (New)

#### Files to Create

| File | Purpose |
|------|---------|
| `src/backend/careervp/dal/knowledge_base_repository.py` | DynamoDB operations |
| `src/backend/careervp/logic/knowledge_base.py` | Business logic |

#### DynamoDB Schema

```python
# Table: careervp-knowledge-base
# TTL: 365 days (auto-expire)

# Item Structure
{
    "userEmail": "user@example.com",           # Partition Key
    "knowledgeType": "recurring_themes",       # Sort Key
    "data": {
        "themes": ["AWS", "Python", "Leadership"],
        "topics_to_skip": [...]
    },
    "applications_count": 5,
    "created_at": "2026-02-09T00:00:00Z",
    "updated_at": "2026-02-09T00:00:00Z"
}

# Knowledge Types
KNOWLEDGE_TYPES = {
    "recurring_themes": "Topics to skip in gap analysis",
    "gap_responses": "Previous gap analysis answers",
    "differentiators": "VPR-identified differentiators",
    "interview_notes": "Post-interview reflections",
    "company_notes": "Research notes on companies",
}
```

---

## 4. Data Models

### 4.1 New Models

```python
# src/backend/careervp/models/gap_analysis.py (extensions)

class GapQuestionWithTags(GapQuestion):
    """Extended gap question with JSA tags."""
    destination: Literal["CV IMPACT", "INTERVIEW/MVP ONLY"]
    strategic_intent: str
    evidence_gap: str
    priority: Literal["CRITICAL", "IMPORTANT", "OPTIONAL"]

# src/backend/careervp/models/interview_prep.py (new)

class InterviewPrepRequest(BaseModel):
    """Request for interview preparation materials."""
    cv_id: str
    job_id: str
    user_id: str
    include_salary_guidance: bool = True

class InterviewQuestion(BaseModel):
    """Interview question with STAR response."""
    category: str
    question: str
    situation: str | None = None
    task: str | None = None
    action: str | None = None
    result: str | None = None

class InterviewPrepResponse(BaseModel):
    """Interview preparation materials."""
    questions: list[InterviewQuestion]
    questions_to_ask: list[str]
    checklist: list[str]
    salary_guidance: str | None = None

# src/backend/careervp/models/quality_validator.py (new)

class ValidationCheck(BaseModel):
    """Individual validation check result."""
    check_name: str
    passed: bool
    score: float  # 0.0 to 1.0
    issues: list[str] = []
    recommendations: list[str] = []

class ValidationResult(BaseModel):
    """Aggregated validation result."""
    overall_score: float
    passed: bool
    checks: list[ValidationCheck]
    summary: str
```

---

## 5. API Changes

### 5.1 New Endpoints

| Method | Path | Handler | Status |
|--------|------|---------|--------|
| POST | /api/cover-letter | cover_letter_handler.handler | New |
| POST | /api/interview-prep | interview_prep_handler.handler | New |
| GET | /api/knowledge/{type} | knowledge_base_handler.handler | New |

### 5.2 CDK Updates

```python
# infra/careervp/api_construct.py

class APIConstruct Construct):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Existing integrations...

        # NEW: Cover Letter API
        cover_letter_resource = self.api.root.add_resource("cover-letter")
        cover_letter_resource.add_method(
            "POST",
            integration=self.lambda_integration(cover_letter_handler),
            authorization_type=AuthorizationType.COGNITO,
        )

        # NEW: Interview Prep API
        interview_prep_resource = self.api.root.add_resource("interview-prep")
        interview_prep_resource.add_method(
            "POST",
            integration=self.lambda_integration(interview_prep_handler),
            authorization_type=AuthorizationType.COGNITO,
        )

# infra/careervp/api_db_construct.py

class APIDBConstruct Construct):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # NEW: Knowledge Base Table
        self.knowledge_base_table = dynamodb.Table(
            self, "KnowledgeBase",
            table_name="careervp-knowledge-base-dev",
            partition_key=dynamodb.Attribute(
                name="userEmail",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="knowledgeType",
                type=dynamodb.AttributeType.STRING
            ),
            time_to_live_attribute="ttl",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        )
```

---

## 6. Implementation Sequence

### Phase 1: Critical Fixes

| Order | Component | Files Changed | Dependencies |
|-------|-----------|----------------|--------------|
| 1 | VPR 6-stage | `vpr_prompt.py` | None |
| 2 | CV Tailoring 3-step | `cv_tailoring_prompt.py`, `cv_tailoring_logic.py` | VPR |
| 3 | Cover Letter handler | `cover_letter_handler.py` (new), `cover_letter_prompt.py` | VPR |
| 4 | Gap Analysis handler | `gap_handler.py`, `gap_analysis_prompt.py` | Knowledge Base |

### Phase 2: Missing Features

| Order | Component | Files Changed | Dependencies |
|-------|-----------|----------------|--------------|
| 5 | Interview Prep | `interview_prep_handler.py` (new), `interview_prep.py` (new) | VPR, CV |
| 6 | Quality Validator | `quality_validator.py` (new) | VPR, CV, Cover Letter |
| 7 | Knowledge Base | `knowledge_base_repository.py` (new), `knowledge_base.py` (new) | None |

### Phase 3: Infrastructure

| Order | Component | Files Changed |
|-------|-----------|----------------|
| 8 | CDK Updates | `api_construct.py`, `api_db_construct.py` |

---

## 7. Testing Strategy

### 7.1 Test Categories

| Category | Location | Purpose |
|----------|----------|---------|
| Unit | `tests/unit/*` | Test individual functions |
| Integration | `tests/integration/*` | Test component interactions |
| E2E | `tests/e2e/*` | Test full user flows |
| JSA Alignment | `tests/jsa_skill_alignment/*` | Validate JSA requirements |

### 7.2 Key Test Cases

```python
# tests/jsa_skill_alignment/test_vpr_alignment.py

def test_vpr_has_6_stages():
    """Verify all 6 stages are in prompt."""
    for stage in STAGES:
        assert stage in VPR_GENERATION_PROMPT

def test_vpr_internal_outputs():
    """Verify internal output markers."""
    assert "OUTPUT (Internal)" in VPR_GENERATION_PROMPT

def test_vpr_meta_evaluation():
    """Verify 20% improvement prompt."""
    assert "20% more persuasive" in VPR_GENERATION_PROMPT

# tests/jsa_skill_alignment/test_cv_tailoring_alignment.py

def test_cv_has_3_steps():
    """Verify 3-step structure."""
    for step in ["STEP 1", "STEP 2", "STEP 3"]:
        assert step in CV_TAILORING_PROMPT

def test_cv_verification_checks():
    """Verify ATS and hiring manager checks."""
    assert "ATS" in CV_TAILORING_PROMPT
    assert "Hiring Manager" in CV_TAILORING_PROMPT
```

### 7.3 Running Tests

```bash
# Run all JSA alignment tests
cd src/backend
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/ -v

# Run with coverage
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/ --cov=careervp --cov-report=html
```

---

## 8. Migration Considerations

### 8.1 Backward Compatibility

- **VPR**: Existing prompts continue to work; new 6-stage is additive
- **CV Tailoring**: New parameters are optional; existing code works unchanged
- **Cover Letter**: New endpoint; no changes to existing endpoints
- **Gap Analysis**: New lambda_handler with enhanced behavior

### 8.2 Rollout Strategy

1. **Feature Flags**: Use environment variables to enable new features
2. **Canary Deploy**: Route 5% of traffic to new handlers
3. **Monitoring**: Track error rates and latency for new components
4. **Rollback**: CloudFormation stack rollback on errors

### 8.3 Data Migration

- **Knowledge Base**: No migration needed (new table)
- **Existing Data**: CV, VPR, Gap Analysis data remains unchanged

---

## Appendix A: File Change Summary

| File | Action | Lines |
|------|--------|-------|
| `src/backend/careervp/logic/prompts/vpr_prompt.py` | Modify | +60 |
| `src/backend/careervp/logic/cv_tailoring_prompt.py` | Modify | +40 |
| `src/backend/careervp/logic/cv_tailoring_logic.py` | Modify | +20 |
| `src/backend/careervp/logic/prompts/cover_letter_prompt.py` | Modify | +80 |
| `src/backend/careervp/logic/prompts/gap_analysis_prompt.py` | Modify | +100 |
| `src/backend/careervp/handlers/cover_letter_handler.py` | Create | ~150 |
| `src/backend/careervp/handlers/gap_handler.py` | Modify | +100 |
| `src/backend/careervp/handlers/interview_prep_handler.py` | Create | ~150 |
| `src/backend/careervp/logic/interview_prep.py` | Create | ~100 |
| `src/backend/careervp/logic/quality_validator.py` | Create | ~200 |
| `src/backend/careervp/dal/knowledge_base_repository.py` | Create | ~100 |
| `src/backend/careervp/logic/knowledge_base.py` | Create | ~80 |
| `infra/careervp/api_construct.py` | Modify | +30 |
| `infra/careervp/api_db_construct.py` | Modify | +40 |

---

**END OF DESIGN DOCUMENT**
