# Spec: Gap Analysis API

## Overview

Gap Analysis API provides synchronous generation of targeted questions to identify skill and experience gaps between a user's CV and target job requirements.

**Pattern:** Synchronous (immediate response)
**LLM Model:** Claude Sonnet 4.5 (TaskMode.STRATEGIC)
**FVS Integration:** Validates that questions reference only skills from CV or job description
**Architecture:** [GAP_ANALYSIS_DESIGN.md](../../architecture/GAP_ANALYSIS_DESIGN.md)

## API Endpoint

### POST /api/gap-analysis

**Endpoint:** `POST /api/gap-analysis`
**Auth:** Required (Cognito JWT)
**Timeout:** 600 seconds (10 minutes)

#### Request

```json
{
  "cv_id": "cv_789",
  "job_id": "job_456",
  "language": "en"
}
```

#### Request Model

```python
from pydantic import BaseModel, Field
from typing import Annotated, Literal

class GapAnalysisRequest(BaseModel):
    """Request for gap analysis generation."""

    cv_id: Annotated[str, Field(description="CV identifier (references stored CV)")]
    job_id: Annotated[str, Field(description="Job identifier (references stored job posting)")]
    language: Annotated[
        Literal['en', 'he'],
        Field(default='en', description="Question language")
    ]
```

#### Success Response (200 OK)

```json
{
  "success": true,
  "questions": [
    {
      "question_id": "01234567-89ab-cdef-0123-456789abcdef",
      "question_text": "You worked as a DevOps Engineer at TechCorp. Can you describe your experience with CI/CD pipelines, including specific tools (e.g., Jenkins, GitLab CI, GitHub Actions)?",
      "category": "technical_skills",
      "impact": "HIGH",
      "probability": "HIGH",
      "reasoning": "Job requires CI/CD experience and your DevOps role likely involved pipeline work"
    },
    {
      "question_id": "12345678-9abc-def0-1234-56789abcdef0",
      "question_text": "The position requires experience with microservices architecture. In your role as Senior Software Engineer, did you work with microservices? If so, please describe.",
      "category": "technical_skills",
      "impact": "HIGH",
      "probability": "MEDIUM",
      "reasoning": "Senior SWE role may have included microservices work not explicitly mentioned in CV"
    }
  ],
  "questions_count": 2,
  "generated_at": "2025-02-04T12:00:45Z",
  "model_used": "claude-sonnet-4-5",
  "processing_time_ms": 8432,
  "cost_estimate": 0.095,
  "fvs_validation": {
    "is_valid": true,
    "violations": []
  }
}
```

#### Response Model

```python
from pydantic import BaseModel, Field
from typing import Annotated, Literal, Optional

class GapQuestion(BaseModel):
    """A single gap analysis question."""

    question_id: Annotated[str, Field(description="Unique question identifier (UUID)")]
    question_text: Annotated[str, Field(description="The question text")]
    category: Annotated[
        Literal['technical_skills', 'experience_depth', 'transferable_skills', 'recent_developments'],
        Field(description="Question category")
    ]
    impact: Annotated[
        Literal['HIGH', 'MEDIUM', 'LOW'],
        Field(description="How critical is this requirement")
    ]
    probability: Annotated[
        Literal['HIGH', 'MEDIUM', 'LOW'],
        Field(description="Likelihood user has this experience")
    ]
    reasoning: Annotated[str, Field(description="Why this question is relevant")]


class FVSValidationResult(BaseModel):
    """FVS validation result."""
    is_valid: bool
    violations: list[dict]


class GapAnalysisResponse(BaseModel):
    """Response for gap analysis generation."""

    success: Annotated[bool, Field(description="Whether generation succeeded")]
    questions: Annotated[list[GapQuestion], Field(description="Generated questions")]
    questions_count: Annotated[int, Field(description="Number of questions generated")]
    generated_at: Annotated[str, Field(description="ISO 8601 timestamp")]
    model_used: Annotated[str, Field(description="LLM model used (claude-sonnet-4-5)")]
    processing_time_ms: Annotated[int, Field(description="Total processing time in milliseconds")]
    cost_estimate: Annotated[float, Field(description="Estimated cost in USD")]
    fvs_validation: Annotated[FVSValidationResult, Field(description="FVS validation result")]
    error: Annotated[Optional[str], Field(default=None, description="Error message if failed")]
    code: Annotated[Optional[str], Field(default=None, description="Error code if failed")]
```

#### Error Responses

**400 Bad Request** - Invalid input
```json
{
  "error": "Validation error",
  "code": "VALIDATION_ERROR",
  "details": {
    "cv_id": "CV not found for user"
  }
}
```

**401 Unauthorized** - Missing/invalid JWT
```json
{
  "error": "Unauthorized",
  "code": "UNAUTHORIZED"
}
```

**400 Bad Request** - FVS validation failure (hallucinated skills)
```json
{
  "success": false,
  "error": "FVS validation failed: 2 questions reference skills not in CV or job description",
  "code": "FVS_HALLUCINATION_DETECTED",
  "fvs_validation": {
    "is_valid": false,
    "violations": [
      {
        "question_id": "uuid",
        "question": "Do you have experience with Rust?",
        "invalid_skills": ["Rust"],
        "severity": "CRITICAL"
      }
    ]
  }
}
```

**500 Internal Server Error** - Server error
```json
{
  "error": "Failed to generate gap analysis questions",
  "code": "INTERNAL_ERROR"
}
```

**504 Gateway Timeout** - LLM timeout (>600 seconds)
```json
{
  "error": "Gap analysis generation timed out after 600 seconds. Please try again.",
  "code": "LLM_TIMEOUT"
}
```

---

## Result Codes

Defined in `src/backend/careervp/models/result.py`:

```python
class ResultCode:
    # Gap Analysis success codes
    GAP_QUESTIONS_GENERATED = 'GAP_QUESTIONS_GENERATED'  # Questions generated successfully
    GAP_RESPONSES_SAVED = 'GAP_RESPONSES_SAVED'          # User responses saved

    # Error codes
    VALIDATION_ERROR = 'VALIDATION_ERROR'                # Invalid request data
    CV_NOT_FOUND = 'CV_NOT_FOUND'                        # CV not found for user
    LLM_API_ERROR = 'LLM_API_ERROR'                      # Claude API error
    TIMEOUT = 'TIMEOUT'                                  # Processing timeout
    INTERNAL_ERROR = 'INTERNAL_ERROR'                    # Server error
    JOB_NOT_FOUND = 'JOB_NOT_FOUND'                      # Job ID not found
    UNAUTHORIZED = 'UNAUTHORIZED'                        # Auth error
    PAYLOAD_TOO_LARGE = 'PAYLOAD_TOO_LARGE'              # Request too large
```

---

## HTTP Status Code Mapping

| Result Code | HTTP Status | Description |
|-------------|-------------|-------------|
| GAP_QUESTIONS_GENERATED | 200 OK | Questions generated successfully |
| VALIDATION_ERROR | 400 Bad Request | Invalid input data |
| CV_NOT_FOUND | 404 Not Found | CV not found for user |
| JOB_NOT_FOUND | 404 Not Found | Job ID not found |
| UNAUTHORIZED | 401 Unauthorized | Missing/invalid auth |
| PAYLOAD_TOO_LARGE | 413 Payload Too Large | Request exceeds 10MB |
| LLM_API_ERROR | 500 Internal Server Error | LLM service error |
| TIMEOUT | 500 Internal Server Error | Processing timeout |
| INTERNAL_ERROR | 500 Internal Server Error | Generic server error |

Submit endpoint always returns **202 ACCEPTED** on success.

---

## Data Validation Rules

### File Size Limits

```python
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_TEXT_LENGTH = 1_000_000        # 1M characters
```

**Enforcement:**
- Job posting description + requirements + responsibilities combined < 1M characters
- CV content (if inline) < 10MB
- Total request payload < 10MB

### Text Sanitization

- Strip HTML tags from job posting fields
- Remove script tags and event handlers
- Normalize whitespace (no excessive newlines)
- Validate URLs in `source_url` field

### Required Fields

**GapAnalysisRequest:**
- `cv_id` - Required, must reference existing CV for user
- `job_id` - Required, must reference existing job posting
- `language` - Optional, defaults to 'en'

---

## Authentication & Authorization

### JWT Token Validation

- All endpoints require valid Cognito JWT in `Authorization` header
- Token format: `Bearer <jwt>`
- Token must not be expired
- Token must contain valid `sub` claim (user ID)

### User Isolation

- Users can only submit gap analysis for their own `cv_id`
- Attempting to access another user's CV returns `404 Not Found` (not 403, to avoid info leak)

---

## Rate Limiting

### Gap Analysis Endpoint

- **Rate:** 10 requests per minute per user
- **Burst:** 3 requests
- **Response (429 Too Many Requests):**
```json
{
  "error": "Rate limit exceeded. Please try again in 60 seconds.",
  "code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 60
}
```

---

## Timeouts

| Component | Timeout | Behavior on Timeout |
|-----------|---------|-------------------|
| Gap Analysis Handler Lambda | 600 seconds (10 min) | Return 504 Gateway Timeout |
| LLM API Call | 600 seconds (10 min) | Return TIMEOUT error code |

---

## Error Scenarios & Handling

### Scenario 1: CV Not Found

**Trigger:** User submits request with `cv_id` that doesn't exist or belongs to another user

**Response:**
```json
{
  "error": "CV not found for user",
  "code": "CV_NOT_FOUND"
}
```

**HTTP Status:** 404 Not Found

---

### Scenario 2: LLM API Rate Limit

**Trigger:** Claude API returns 429 Too Many Requests

**Behavior:**
- Handler catches 429 response from Claude API
- Return 503 Service Unavailable with `LLM_API_ERROR`
- Client may retry with exponential backoff

**Response Code:** 503 Service Unavailable (`LLM_API_ERROR`)

---

### Scenario 3: Processing Timeout

**Trigger:** LLM API takes longer than 10 minutes

**Behavior:**
- `asyncio.wait_for()` raises `asyncio.TimeoutError`
- Return 504 Gateway Timeout
- Error message: "Processing timeout after 10 minutes"
- Code: `TIMEOUT`

---

### Scenario 4: Invalid LLM Response

**Trigger:** LLM returns malformed JSON or unexpected structure

**Behavior:**
- Validation error caught in handler
- Return 500 Internal Server Error
- Error message: "Failed to parse LLM response"
- Code: `INTERNAL_ERROR`
- Log full LLM response for debugging

---

### Scenario 5: DynamoDB Write Failure

**Trigger:** DynamoDB throttling or service error

**Behavior:**
- Handler throws exception
- Return 500 Internal Server Error
- Log DynamoDB error for manual intervention

---

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

---

## Testing Requirements

### Unit Test Coverage

- [ ] Request model validation (Pydantic)
- [ ] Response model serialization
- [ ] Result code to HTTP status mapping
- [ ] File size validation (10MB limit)
- [ ] Text length validation
- [ ] JWT token parsing (mock)
- [ ] User ID extraction from token

### Integration Test Coverage

- [ ] Submit request → verify DynamoDB record created
- [ ] Submit request → verify questions returned in response
- [ ] Error scenarios (CV not found, LLM timeout, etc.)

### Contract Tests

- [ ] OpenAPI/Swagger schema validation
- [ ] Request/response schema validation
- [ ] Error response format validation

---

## OpenAPI Schema

```yaml
openapi: 3.0.0
info:
  title: CareerVP Gap Analysis API
  version: 1.0.0

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

  securitySchemes:
    CognitoAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
```

---

## Monitoring & Alerts

### CloudWatch Metrics

- `GapAnalysis.Requests` - Counter
- `GapAnalysis.Success` - Counter
- `GapAnalysis.Failures` - Counter
- `GapAnalysis.ProcessingDuration` - Histogram
- `GapAnalysis.QuestionsGenerated` - Histogram (0-5)

### CloudWatch Alarms

| Alarm | Threshold | Action |
|-------|-----------|--------|
| Error Rate | > 5% of invocations | SNS notification |
| Processing Duration P99 | > 10 minutes | SNS notification |
| Handler Errors | > 10 in 5 minutes | SNS notification |

---

## References

- **Architecture:** [GAP_ANALYSIS_DESIGN.md](../../architecture/GAP_ANALYSIS_DESIGN.md)
- **Models:** `src/backend/careervp/models/job.py`
- **Result Codes:** `src/backend/careervp/models/result.py`
