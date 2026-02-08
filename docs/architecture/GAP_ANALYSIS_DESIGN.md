# Gap Analysis Design

## Overview

Gap Analysis is a feature that identifies skill, experience, and qualification gaps between a user's CV and a target job posting. It generates intelligent, contextual questions to help users articulate additional relevant experience that may not be explicitly stated in their CV.

## Problem Statement

Users often have relevant experience that doesn't appear in their CV because:
- **Implicit knowledge:** Skills used in previous roles but not listed explicitly
- **Transferable skills:** Experience from non-traditional backgrounds
- **Recent developments:** New skills acquired since CV was last updated
- **Underselling:** Modest users who don't highlight achievements

**Example:**
- Job requires "experience with CI/CD pipelines"
- CV mentions "DevOps engineer" but doesn't explicitly list CI/CD tools
- Gap Analysis asks: "You worked as a DevOps Engineer at Company X. Can you describe your experience with continuous integration and deployment pipelines, including specific tools (e.g., Jenkins, GitLab CI, GitHub Actions)?"

## Architecture Pattern: Handler → Logic → DAL

Gap Analysis uses a **synchronous pattern** (not async) because question generation completes within acceptable time limits.

### Handler Layer (gap_analysis_handler.py)
- Validates API input (Pydantic models)
- Initializes dependencies (DAL, LLM, FVS)
- Delegates ALL business logic to GapAnalysisLogic
- Formats HTTP responses
- NO DIRECT DAL ACCESS

### Logic Layer (gap_analysis_logic.py)
- Fetches CV and job description from DAL
- Calls LLM (Sonnet 4.5) for question generation
- Validates questions with FVS (skill verification)
- Stores gap questions via DAL
- Returns Result[list[GapQuestion]]

### DAL Layer (dynamo_dal_handler.py - SHARED)
- get_cv(cv_id) -> UserCV
- get_job_description(job_id) -> str
- store_gap_questions(questions) -> None
- get_gap_responses(cv_id, job_id) -> GapAnalysisResponses

### Synchronous Flow

```
POST /api/gap-analysis
  │
  ├─> Handler: Validate request, initialize logic
  │
  ├─> Logic: Fetch CV, generate questions (Sonnet 4.5), validate with FVS
  │
  └─> 200 OK { questions: [...] }
```

### LLM Model: Claude Sonnet 4.5 (TaskMode.STRATEGIC)

**Rationale:**
- Gap analysis requires strategic reasoning (understanding implicit skills, context)
- Sonnet 4.5 produces higher-quality, more contextual questions
- Cost: ~$0.10 per question set (acceptable for strategic task)
- Timeout: 600 seconds (10 minutes) for complex analysis

### Timeout: 600 Seconds

```python
import asyncio

async def generate_gap_questions_with_timeout(llm_client: LLMClient, prompt: str) -> list[GapQuestion]:
    try:
        response = await asyncio.wait_for(
            llm_client.generate(
                messages=[...],
                model="claude-sonnet-4-5",
                max_tokens=4096
            ),
            timeout=600.0  # 10 minutes
        )
        return response
    except asyncio.TimeoutError:
        raise TimeoutError("LLM call timed out after 600 seconds")
```

---

## FVS Integration: Skill Verification

### Purpose

Validate that skills mentioned in gap questions are real and not hallucinated by the LLM.

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
        """
        violations = []

        # Extract skills from CV and job description
        cv_skills = set(skill.lower() for skill in master_cv.skills)
        job_skills = self._extract_skills_from_job_desc(job_desc)
        allowed_skills = cv_skills | job_skills

        for question in questions:
            # Check if question references skills not in allowed set
            question_skills = self._extract_skills_from_text(question.question)
            invalid_skills = question_skills - allowed_skills

            if invalid_skills:
                violations.append({
                    "question_id": question.question_id,
                    "question": question.question,
                    "invalid_skills": list(invalid_skills),
                    "severity": "CRITICAL"
                })

        if violations:
            return Result(
                success=False,
                error=f"{len(violations)} hallucinated skills detected",
                code=ResultCode.FVS_HALLUCINATION_DETECTED,
                data={"violations": violations}
            )

        return Result(success=True)
```

### Integration Point

```python
# Logic layer (gap_analysis_logic.py)
def generate_gap_questions(
    cv_id: str,
    job_id: str,
    dal: DynamoDalHandler,
    llm_client: LLMClient,
    fvs_validator: GapAnalysisFVSValidator
) -> Result[list[GapQuestion]]:
    # Fetch data from DAL
    cv = dal.get_cv(cv_id)
    job_desc = dal.get_job_description(job_id)

    # Generate questions via LLM (Sonnet 4.5)
    questions = llm_client.generate_questions(cv, job_desc)

    # FVS validation
    fvs_result = fvs_validator.validate_questions(questions, cv, job_desc)
    if not fvs_result.success:
        return Result(
            success=False,
            error="Hallucinated skills detected in questions",
            code=ResultCode.FVS_HALLUCINATION_DETECTED,
            data=fvs_result.data
        )

    # Store questions via DAL
    dal.store_gap_questions(cv_id, job_id, questions)

    return Result(success=True, data=questions)
```

---

## Observability: AWS Lambda Powertools

### Handler Decorators

```python
from aws_lambda_powertools import Logger, Tracer, Metrics

logger = Logger(service="gap-analysis")
tracer = Tracer(service="gap-analysis")
metrics = Metrics(namespace="CareerVP", service="gap-analysis")

@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event, context):
    ...
```

### Metrics to Track
- `GapAnalysisSuccess` - Successful question generation count
- `GapAnalysisFailure` - Failed generation count
- `QuestionGenerationLatency` - End-to-end latency (ms)
- `LLMCost` - Cost per question set ($)
- `QuestionsGenerated` - Number of questions per request
- `FVSViolations` - Hallucination count

---

## DynamoDB Table: gap_analysis_jobs

### Schema

| Attribute | Type | Description |
|-----------|------|-------------|
| pk (PK) | String | `GAP#{cv_id}#{job_id}` |
| sk (SK) | String | `ANALYSIS#v1` |
| user_id | String | User who submitted request |
| cv_id | String | Reference to master CV |
| job_id | String | Reference to target job posting |
| questions | List | Array of generated gap questions |
| questions_count | Number | Number of questions generated |
| created_at | Number | Unix timestamp |
| ttl | Number | Auto-delete timestamp (90 days) |

### GSI: user_id_index
- Partition Key: user_id
- Sort Key: created_at
- Projection: ALL

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

---

## Gap Analysis Algorithm

### Phase 1: Gap Identification

**Input:**
- User CV (parsed structure from `careervp.models.cv.UserCV`)
- Job posting (parsed structure from `careervp.models.job.JobPosting`)

**Process:**
1. **Extract requirements** from job posting
   - Technical skills (e.g., "Python", "AWS", "React")
   - Experience requirements (e.g., "5+ years", "leadership")
   - Qualifications (e.g., "Bachelor's degree", certifications)
   - Soft skills (e.g., "team collaboration", "communication")

2. **Extract user profile** from CV
   - Listed skills
   - Work experience (companies, roles, dates, responsibilities)
   - Education
   - Certifications
   - Projects

3. **Identify gaps** using LLM-based semantic matching
   - Requirements NOT explicitly mentioned in CV
   - Requirements with ambiguous coverage (e.g., "DevOps" vs "CI/CD")
   - Experience level mismatches (e.g., job needs 5 years, CV shows 3)

### Phase 2: Question Generation

**Scoring Criteria:**
Each identified gap is scored by:
- **Impact:** How critical is this requirement? (HIGH/MEDIUM/LOW)
- **Probability:** How likely does the user have this experience? (based on related skills/roles)
- **Clarifiability:** Can the user reasonably answer this in 2-3 sentences?

**Question Types:**

1. **Skill Evidence Questions** (Impact: HIGH)
   - Job requires skill X, CV doesn't explicitly mention it
   - "Do you have experience with [skill]? If so, please describe how you've used it."

2. **Experience Depth Questions** (Impact: MEDIUM)
   - CV mentions related experience but lacks detail
   - "You worked as [role] at [company]. Can you elaborate on your experience with [specific requirement]?"

3. **Transferable Skills Questions** (Impact: MEDIUM)
   - User's background suggests potential transferable skills
   - "In your role as [previous role], did you gain experience with [requirement] that would apply here?"

4. **Recent Developments Questions** (Impact: LOW)
   - CV might be outdated
   - "Since your last role at [company], have you developed skills in [new requirement]?"

**Question Limit:** Maximum 5 questions per job posting (prioritized by impact × probability)

### Phase 3: Response Integration

Gap responses are stored with the `GapResponse` model:

```python
class GapResponse(BaseModel):
    question_id: str                    # Unique identifier (UUID)
    question: str                       # The generated question
    answer: str                         # User's response
    destination: Literal[               # Where to use this response
        'CV_IMPACT',                    # Include in tailored CV
        'INTERVIEW_MVP_ONLY'            # Only for interview prep
    ]
```

**User Flow:**
1. User receives 5 gap questions
2. User answers relevant questions (can skip)
3. For each answer, user marks destination:
   - `CV_IMPACT`: Strong evidence to include in VPR/tailored CV
   - `INTERVIEW_MVP_ONLY`: Talking point for interviews only

**Integration Points:**
- **VPR Generator:** Incorporates `CV_IMPACT` responses as evidence
- **Interview Prep:** Uses all responses to prepare answers

## LLM Prompt Design

### LLM Model: Claude Sonnet 4.5 (Strategic Reasoning)

Gap analysis uses **Claude Sonnet 4.5** (TaskMode.STRATEGIC) because:
- Requires deep understanding of implicit skills and transferable experience
- Must infer probable skills from job history and context
- Needs nuanced judgment about gap severity and user capability
- Strategic task justified by importance (helps users articulate hidden strengths)

### System Prompt

```
You are an expert career coach with deep expertise in identifying skill and experience gaps between candidates and job requirements. Your role is to use strategic reasoning to uncover hidden strengths and implicit skills that candidates may not have explicitly stated in their CV.

**Strategic Analysis Guidelines:**
1. **Deep Context Understanding:** Analyze the candidate's entire career trajectory to infer implicit skills
   - Example: "DevOps Engineer" role likely includes CI/CD experience even if not listed
   - Example: "Team Lead" role suggests leadership, mentoring, and project management skills

2. **Transferable Skills Reasoning:** Identify skills from unrelated domains that apply to the target role
   - Example: "Product Manager" experience may include data analysis relevant to "Data Analyst" role
   - Example: "Startup experience" often includes wearing multiple hats and learning diverse skills

3. **Gap Prioritization (Impact × Probability):**
   - HIGH IMPACT: Critical requirements explicitly stated in job posting
   - HIGH PROBABILITY: Skills the candidate likely has based on related experience
   - Generate 3-5 questions prioritized by (impact × probability) score

4. **Question Specificity:**
   - Reference specific companies, roles, and dates from the CV
   - Ask about concrete examples and measurable outcomes
   - Make questions answerable in 2-3 sentences

5. **Avoid Hallucination (FVS Compliance):**
   - ONLY reference skills mentioned in CV or job description
   - DO NOT invent skills or experience not suggested by the evidence
   - DO NOT ask about qualifications the candidate obviously lacks

**Question Format:**
- Start with context: "You worked as [role] at [company]..."
- State the gap: "The job requires [skill/experience]..."
- Ask for evidence: "Can you describe your experience with [specific aspect]?"

**Output Format:** JSON array with:
{
  "question_id": "uuid",
  "question": "contextualized question text",
  "impact": "HIGH" | "MEDIUM" | "LOW",
  "probability": "HIGH" | "MEDIUM" | "LOW",
  "reasoning": "brief explanation of why this gap is relevant"
}
```

### User Prompt Template

```python
def create_gap_analysis_prompt(user_cv: UserCV, job_posting: JobPosting) -> str:
    """Generate user prompt for gap analysis."""

    return f"""
Analyze the gap between this candidate's CV and the target job requirements.

**Candidate CV:**
Name: {user_cv.personal_info.full_name}

Work Experience:
{_format_work_experience(user_cv.work_experience)}

Skills: {', '.join(user_cv.skills)}

Education: {_format_education(user_cv.education)}

**Target Job:**
Company: {job_posting.company_name}
Role: {job_posting.role_title}

Requirements:
{_format_requirements(job_posting.requirements)}

Responsibilities:
{_format_responsibilities(job_posting.responsibilities)}

Nice to Have:
{_format_nice_to_have(job_posting.nice_to_have)}

**Task:**
Identify 3-5 high-value gaps where the candidate likely has relevant experience but hasn't explicitly stated it. Generate targeted questions to help them articulate this experience.

Focus on:
1. Technical skills mentioned in requirements but not in CV
2. Experience depth for responsibilities that align with their roles
3. Transferable skills from their background

Return JSON array with question_id, question, impact, and probability for each.
"""
```

## Scoring Algorithm

### Gap Scoring Formula

```python
gap_score = (impact_weight * impact_score) + (probability_weight * probability_score)

# Weights (can be tuned)
impact_weight = 0.7      # Prioritize high-impact gaps
probability_weight = 0.3  # Consider likelihood of experience

# Scores
impact_score:
  HIGH = 1.0    # Critical requirement (e.g., primary technical skill)
  MEDIUM = 0.6  # Important but not essential
  LOW = 0.3     # Nice-to-have

probability_score:
  HIGH = 1.0    # Strong evidence in CV (related role/skill)
  MEDIUM = 0.6  # Possible connection
  LOW = 0.3     # Unlikely but worth asking
```

**Example Calculation:**
```
Job requires "AWS experience"
CV shows "Cloud Engineer at Tech Corp"

Impact: HIGH (1.0) - AWS is critical for role
Probability: HIGH (1.0) - Cloud Engineer very likely used AWS
Gap Score: (0.7 * 1.0) + (0.3 * 1.0) = 1.0 ✓ Top priority question

Job requires "Spanish fluency"
CV shows "Software Engineer" with no language mention

Impact: MEDIUM (0.6) - Listed in nice-to-have
Probability: LOW (0.3) - No indication in CV
Gap Score: (0.7 * 0.6) + (0.3 * 0.3) = 0.51 ✓ Lower priority
```

**Selection:** Top 5 gaps by score become questions

## Data Flow

### Input Models

```python
class GapAnalysisRequest(BaseModel):
    """Request for gap analysis."""

    user_id: str
    cv_id: str                          # References stored CV
    job_posting: JobPosting             # Target job
    language: Literal['en', 'he'] = 'en'  # Question language
```

### Output Models

```python
class GapQuestion(BaseModel):
    """Generated gap analysis question."""

    question_id: str                    # UUID
    question: str                       # The question text
    impact: Literal['HIGH', 'MEDIUM', 'LOW']
    probability: Literal['HIGH', 'MEDIUM', 'LOW']
    gap_score: float                    # Calculated score

class GapAnalysisResult(BaseModel):
    """Complete gap analysis output."""

    job_id: str                         # Job posting ID
    user_id: str
    job_posting: JobPosting
    questions: list[GapQuestion]        # 3-5 questions
    created_at: str                     # ISO timestamp
```

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

## Implementation Components

### 1. Logic Layer: `logic/gap_analysis.py`

```python
from careervp.models.cv import UserCV
from careervp.models.job import JobPosting, GapQuestion
from careervp.models.result import Result, ResultCode
from careervp.dal.db_handler import DalHandler

async def generate_gap_questions(
    user_cv: UserCV,
    job_posting: JobPosting,
    dal: DalHandler,
    language: str = 'en'
) -> Result[list[GapQuestion]]:
    """
    Generate gap analysis questions using LLM.

    Args:
        user_cv: Parsed user CV
        job_posting: Target job posting
        dal: Data access layer (for retrieving CV if needed)
        language: Question language (en or he)

    Returns:
        Result[list[GapQuestion]] with 3-5 prioritized questions
    """
    # 1. Build LLM prompt
    # 2. Call Claude API with timeout
    # 3. Parse JSON response
    # 4. Calculate gap scores
    # 5. Sort by score, take top 5
    # 6. Return Result with questions
```

### 2. Prompt: `logic/prompts/gap_analysis_prompt.py`

```python
def create_gap_analysis_system_prompt() -> str:
    """System prompt for gap analysis."""

def create_gap_analysis_user_prompt(
    user_cv: UserCV,
    job_posting: JobPosting
) -> str:
    """User prompt with CV and job posting context."""

def _format_work_experience(work_experience: list[WorkExperience]) -> str:
    """Format work experience for prompt."""

def _format_requirements(requirements: list[str]) -> str:
    """Format job requirements for prompt."""
```

## Testing Strategy

### Unit Tests

**`tests/gap-analysis/unit/test_gap_analysis_logic.py`**
- Test question generation with mock LLM responses
- Test scoring algorithm (impact × probability)
- Test question prioritization (top 5 selection)
- Test error handling (LLM timeout, invalid JSON)

**`tests/gap-analysis/unit/test_gap_prompt.py`**
- Test prompt formatting
- Test CV and job posting serialization
- Test language support (en/he)

**`tests/gap-analysis/unit/test_validation.py`**
- Test 10MB file size limit
- Test text length limits
- Test Pydantic model validation

### Integration Tests

**`tests/gap-analysis/integration/test_gap_handler.py`**
- Test request handling with mocked LLM responses
- Test DAL writes for analysis record
- Test error scenarios (timeout, invalid input)

**`tests/gap-analysis/integration/test_gap_dal.py`**
- Test analysis record creation
- Test retrieval by cv_id + job_id
- Test user analysis queries

### Infrastructure Tests

**`tests/gap-analysis/infrastructure/test_gap_analysis_stack.py`**
- Assert DynamoDB table exists
- Assert Lambda function exists
- Assert API Gateway routes exist

### E2E Tests

**`tests/gap-analysis/e2e/test_gap_analysis_flow.py`**
- Submit request → receive questions
- Test full sync flow with real DynamoDB (local)
- Test timeout scenarios
- Test concurrent request processing

## Performance Considerations

### LLM Latency
- **Expected:** 30-60 seconds for strategic question generation
- **Timeout:** 600 seconds (10 minutes) max
- **Model:** Use Claude Sonnet 4.5 (TaskMode.STRATEGIC) for complex reasoning

### Concurrency
- **Lambda timeout:** 600 seconds (sync request handling)
- **Max concurrent invocations:** 100 (AWS default, configurable)
- **Rate limiting:** Respect Claude API rate limits

### Cost Optimization
- **Token usage:** ~2000 input tokens (CV + job) + ~500 output tokens (5 questions)
- **Cost per analysis:** ~$0.05 (with Sonnet 4.5)
- **DynamoDB storage:** Minimal (single record per analysis)

## Security Considerations

### Input Validation
- Validate file size (10MB max) before processing
- Sanitize job posting content (no script injection)
- Validate CV structure with Pydantic models

### Data Privacy
- Gap analysis records auto-delete after 90 days (TTL)
- Questions returned directly in API response (sync - no S3 storage needed)
- Gap responses stored in DynamoDB users table with 90-day TTL
- No PII in CloudWatch logs

### Access Control
- Cognito authentication required for all endpoints
- Users can only access their own gap analyses and responses
- Enforce `user_id` ownership checks in DAL queries

## Future Enhancements

1. **ML-based Gap Scoring:** Train model on historical success rates
2. **Industry-specific Templates:** Pre-defined questions for common roles
3. **Collaborative Filtering:** "Users with similar CVs were asked..."
4. **Gap Trend Analysis:** Track which gaps users commonly fill
5. **Auto-response Suggestions:** Pre-fill answers based on CV content

## References

- **Models:** `src/backend/careervp/models/job.py` - `GapResponse`, `GapQuestion`
- **Result codes:** `src/backend/careervp/models/result.py` - `GAP_QUESTIONS_GENERATED`
- **Prompt examples:** `docs/features/CareerVP Prompt Library.md`
