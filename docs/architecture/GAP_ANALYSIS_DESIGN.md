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

## Architecture Pattern

Gap Analysis follows the **Async Task Pattern** defined in [VPR_ASYNC_DESIGN.md](./VPR_ASYNC_DESIGN.md).

```
POST /api/gap-analysis/submit
  │
  ├─> Submit Handler: Create job, enqueue
  │
  └─> 202 ACCEPTED { job_id }

SQS Queue triggers Worker Handler
  │
  ├─> Gap Analysis Logic: Generate questions via LLM
  │
  └─> Save to S3, update status COMPLETED

GET /api/gap-analysis/status/{job_id}
  │
  └─> 200 OK { status: "COMPLETED", result_url }
```

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

### System Prompt

```
You are a career coach specializing in identifying skill and experience gaps between candidates and job requirements. Your goal is to help candidates articulate hidden strengths that may not be obvious from their CV.

**Guidelines:**
1. Generate 3-5 targeted questions that help the candidate showcase relevant experience
2. Focus on gaps where the candidate LIKELY has experience but hasn't explicitly stated it
3. Prioritize high-impact requirements (technical skills, key qualifications)
4. Make questions specific and actionable (include company names, role titles from CV)
5. Avoid questions about obviously missing qualifications (e.g., if CV shows 2 years experience, don't ask about 10 years)

**Question Format:**
- Start with context from their CV (e.g., "You worked as X at Y...")
- Ask specifically about the missing requirement
- Keep questions concise (1-2 sentences)
- Make answers easy to provide (2-3 sentence responses)

Output Format: JSON array of objects with:
- question_id: Unique identifier (use UUID)
- question: The question text
- impact: "HIGH" | "MEDIUM" | "LOW" - How critical is this gap?
- probability: "HIGH" | "MEDIUM" | "LOW" - Likelihood user has this experience
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

    job_id: str                         # Async job ID
    user_id: str
    job_posting: JobPosting
    questions: list[GapQuestion]        # 3-5 questions
    created_at: str                     # ISO timestamp
```

### Storage Schema

**DynamoDB Job Record:**
```python
{
    "pk": "JOB#01234567-89ab-cdef-0123-456789abcdef",
    "sk": "METADATA",
    "gsi1pk": "USER#user_123",
    "gsi1sk": "JOB#gap_analysis#2025-02-04T12:00:00Z",
    "job_id": "01234567-89ab-cdef-0123-456789abcdef",
    "user_id": "user_123",
    "feature": "gap_analysis",
    "status": "COMPLETED",
    "request_data": {
        "cv_id": "cv_789",
        "job_posting": { /* JobPosting object */ }
    },
    "result_s3_key": "jobs/gap-analysis/01234567-89ab-cdef.json",
    "created_at": "2025-02-04T12:00:00Z",
    "completed_at": "2025-02-04T12:00:45Z",
    "code": "GAP_QUESTIONS_GENERATED",
    "ttl": 1738684800
}
```

**S3 Result Object:**
```json
{
  "job_id": "01234567-89ab-cdef-0123-456789abcdef",
  "user_id": "user_123",
  "job_posting": {
    "company_name": "TechCorp",
    "role_title": "Senior Software Engineer",
    "requirements": [...]
  },
  "questions": [
    {
      "question_id": "q1-uuid",
      "question": "You worked as a Cloud Engineer at Previous Corp. Can you describe your hands-on experience with AWS services, particularly EC2, S3, and Lambda?",
      "impact": "HIGH",
      "probability": "HIGH",
      "gap_score": 1.0
    },
    {
      "question_id": "q2-uuid",
      "question": "The role requires experience with microservices architecture. In your current position, have you designed or maintained microservices-based systems?",
      "impact": "HIGH",
      "probability": "MEDIUM",
      "gap_score": 0.88
    }
  ],
  "created_at": "2025-02-04T12:00:00Z"
}
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

**`tests/gap-analysis/integration/test_gap_worker_handler.py`**
- Test worker processing with mocked SQS event
- Test status updates (PENDING → PROCESSING → COMPLETED)
- Test S3 result storage
- Test error scenarios (FAILED status)

**`tests/gap-analysis/integration/test_gap_dal.py`**
- Test job creation
- Test status updates
- Test job retrieval by job_id
- Test user job queries

### Infrastructure Tests

**`tests/gap-analysis/infrastructure/test_gap_analysis_stack.py`**
- Assert SQS queue exists with correct name
- Assert DLQ exists with correct configuration
- Assert Lambda functions exist
- Assert DynamoDB GSI exists
- Assert API Gateway routes exist

### E2E Tests

**`tests/gap-analysis/e2e/test_gap_analysis_flow.py`**
- Submit job → poll status → retrieve result
- Test full async flow with real DynamoDB (local)
- Test timeout scenarios
- Test concurrent job processing

## Performance Considerations

### LLM Latency
- **Expected:** 15-30 seconds for question generation
- **Timeout:** 600 seconds (10 minutes) max
- **Optimization:** Use Claude 3 Haiku for faster responses

### Concurrency
- **SQS batch size:** 1 (one job per worker invocation)
- **Max concurrent workers:** 10 (configurable)
- **Rate limiting:** Respect Claude API rate limits

### Cost Optimization
- **Token usage:** ~2000 input tokens (CV + job) + ~500 output tokens (5 questions)
- **Cost per analysis:** ~$0.01 (with Haiku)
- **S3 storage:** Minimal (5KB per result)

## Security Considerations

### Input Validation
- Validate file size (10MB max) before processing
- Sanitize job posting content (no script injection)
- Validate CV structure with Pydantic models

### Data Privacy
- Job records auto-delete after 7 days (TTL)
- S3 results use presigned URLs (expire in 1 hour)
- No PII in CloudWatch logs

### Access Control
- Cognito authentication required for all endpoints
- Users can only access their own jobs
- S3 presigned URLs validated by user_id

## Future Enhancements

1. **ML-based Gap Scoring:** Train model on historical success rates
2. **Industry-specific Templates:** Pre-defined questions for common roles
3. **Collaborative Filtering:** "Users with similar CVs were asked..."
4. **Gap Trend Analysis:** Track which gaps users commonly fill
5. **Auto-response Suggestions:** Pre-fill answers based on CV content

## References

- **Async foundation:** [VPR_ASYNC_DESIGN.md](./VPR_ASYNC_DESIGN.md)
- **Models:** `src/backend/careervp/models/job.py` - `GapResponse`, `GapQuestion`
- **Result codes:** `src/backend/careervp/models/result.py` - `GAP_QUESTIONS_GENERATED`
- **Prompt examples:** `docs/features/CareerVP Prompt Library.md`
