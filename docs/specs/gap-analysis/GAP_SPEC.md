# Spec: Gap Analysis API

## Overview

Gap Analysis API provides asynchronous generation of targeted questions to identify skill and experience gaps between a user's CV and target job requirements.

**Pattern:** SQS + Polling (async task)
**Architecture:** [GAP_ANALYSIS_DESIGN.md](../../architecture/GAP_ANALYSIS_DESIGN.md)

## API Endpoints

### 1. Submit Gap Analysis Job

**Endpoint:** `POST /api/gap-analysis/submit`
**Auth:** Required (Cognito JWT)
**Timeout:** 30 seconds

#### Request

```json
{
  "user_id": "user_123",
  "cv_id": "cv_789",
  "job_posting": {
    "company_name": "TechCorp",
    "role_title": "Senior Software Engineer",
    "description": "About the role...",
    "requirements": [
      "5+ years of software development experience",
      "Strong proficiency in Python and AWS",
      "Experience with microservices architecture"
    ],
    "responsibilities": [
      "Design and implement scalable backend systems",
      "Lead technical design discussions"
    ],
    "nice_to_have": [
      "Experience with Kubernetes",
      "Previous leadership experience"
    ],
    "language": "en",
    "source_url": "https://example.com/jobs/123"
  },
  "language": "en"
}
```

#### Request Model

```python
from pydantic import BaseModel, Field
from typing import Annotated, Literal
from careervp.models.job import JobPosting

class GapAnalysisRequest(BaseModel):
    """Request for gap analysis submission."""

    user_id: Annotated[str, Field(description="User identifier")]
    cv_id: Annotated[str, Field(description="CV identifier (references stored CV)")]
    job_posting: Annotated[JobPosting, Field(description="Target job posting")]
    language: Annotated[
        Literal['en', 'he'],
        Field(default='en', description="Question language")
    ]
```

#### Success Response (202 ACCEPTED)

```json
{
  "job_id": "01234567-89ab-cdef-0123-456789abcdef",
  "status": "PENDING",
  "created_at": "2025-02-04T12:00:00Z",
  "message": "Gap analysis job submitted successfully. Poll /api/gap-analysis/status/{job_id} for results."
}
```

#### Response Model

```python
class GapAnalysisSubmitResponse(BaseModel):
    """Response for gap analysis submission."""

    job_id: Annotated[str, Field(description="Unique job identifier")]
    status: Annotated[
        Literal['PENDING'],
        Field(description="Initial job status")
    ]
    created_at: Annotated[str, Field(description="ISO 8601 timestamp")]
    message: Annotated[str, Field(description="User-friendly message")]
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

**413 Payload Too Large** - Job posting exceeds size limit
```json
{
  "error": "Job posting content exceeds maximum size of 10MB",
  "code": "PAYLOAD_TOO_LARGE"
}
```

**500 Internal Server Error** - Server error
```json
{
  "error": "Failed to submit gap analysis job",
  "code": "INTERNAL_ERROR"
}
```

---

### 2. Get Gap Analysis Status

**Endpoint:** `GET /api/gap-analysis/status/{job_id}`
**Auth:** Required (Cognito JWT)
**Timeout:** 30 seconds

#### Request

Path parameter: `job_id` (UUID)

#### Success Response - PENDING (200 OK)

```json
{
  "job_id": "01234567-89ab-cdef-0123-456789abcdef",
  "status": "PENDING",
  "created_at": "2025-02-04T12:00:00Z"
}
```

#### Success Response - PROCESSING (200 OK)

```json
{
  "job_id": "01234567-89ab-cdef-0123-456789abcdef",
  "status": "PROCESSING",
  "created_at": "2025-02-04T12:00:00Z",
  "started_at": "2025-02-04T12:00:05Z",
  "message": "Analyzing gaps and generating questions..."
}
```

#### Success Response - COMPLETED (200 OK)

```json
{
  "job_id": "01234567-89ab-cdef-0123-456789abcdef",
  "status": "COMPLETED",
  "created_at": "2025-02-04T12:00:00Z",
  "completed_at": "2025-02-04T12:00:45Z",
  "result_url": "https://careervp-results-dev.s3.amazonaws.com/jobs/gap-analysis/01234567-89ab-cdef.json?X-Amz-Algorithm=AWS4-HMAC-SHA256&...",
  "result_expires_at": "2025-02-04T13:00:45Z"
}
```

#### Success Response - FAILED (200 OK)

```json
{
  "job_id": "01234567-89ab-cdef-0123-456789abcdef",
  "status": "FAILED",
  "created_at": "2025-02-04T12:00:00Z",
  "failed_at": "2025-02-04T12:00:30Z",
  "error": "LLM API rate limit exceeded. Please try again in a few minutes.",
  "code": "LLM_API_ERROR"
}
```

#### Response Model

```python
from typing import Literal

class GapAnalysisStatusResponse(BaseModel):
    """Response for gap analysis status query."""

    job_id: Annotated[str, Field(description="Unique job identifier")]
    status: Annotated[
        Literal['PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'],
        Field(description="Current job status")
    ]
    created_at: Annotated[str, Field(description="ISO 8601 creation timestamp")]
    started_at: Annotated[str | None, Field(description="ISO 8601 processing start timestamp")] = None
    completed_at: Annotated[str | None, Field(description="ISO 8601 completion timestamp")] = None
    failed_at: Annotated[str | None, Field(description="ISO 8601 failure timestamp")] = None
    result_url: Annotated[str | None, Field(description="S3 presigned URL for result (COMPLETED only)")] = None
    result_expires_at: Annotated[str | None, Field(description="Result URL expiration (1 hour)")] = None
    error: Annotated[str | None, Field(description="Error message (FAILED only)")] = None
    code: Annotated[str | None, Field(description="Result code")] = None
    message: Annotated[str | None, Field(description="User-friendly status message")] = None
```

#### Error Responses

**404 Not Found** - Job ID not found or belongs to different user
```json
{
  "error": "Gap analysis job not found",
  "code": "JOB_NOT_FOUND"
}
```

**401 Unauthorized** - Missing/invalid JWT
```json
{
  "error": "Unauthorized",
  "code": "UNAUTHORIZED"
}
```

---

### 3. Get Gap Analysis Result

**Endpoint:** `GET {result_url}` (S3 presigned URL)
**Auth:** Not required (presigned URL includes signature)
**Expiration:** 1 hour from status query

#### Success Response (200 OK)

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
      "question_id": "q1-550e8400-e29b-41d4-a716-446655440000",
      "question": "You worked as a Cloud Engineer at Previous Corp. Can you describe your hands-on experience with AWS services, particularly EC2, S3, and Lambda?",
      "impact": "HIGH",
      "probability": "HIGH",
      "gap_score": 1.0
    },
    {
      "question_id": "q2-550e8400-e29b-41d4-a716-446655440001",
      "question": "The role requires experience with microservices architecture. In your current position, have you designed or maintained microservices-based systems?",
      "impact": "HIGH",
      "probability": "MEDIUM",
      "gap_score": 0.88
    },
    {
      "question_id": "q3-550e8400-e29b-41d4-a716-446655440002",
      "question": "Do you have experience with Kubernetes for container orchestration? If so, please describe how you've used it in production.",
      "impact": "MEDIUM",
      "probability": "HIGH",
      "gap_score": 0.78
    },
    {
      "question_id": "q4-550e8400-e29b-41d4-a716-446655440003",
      "question": "You've worked in engineering roles for 4 years. Have you had any opportunities to lead technical initiatives or mentor junior developers?",
      "impact": "MEDIUM",
      "probability": "MEDIUM",
      "gap_score": 0.6
    },
    {
      "question_id": "q5-550e8400-e29b-41d4-a716-446655440004",
      "question": "Since your last role, have you gained any experience with Python or developed relevant backend systems?",
      "impact": "MEDIUM",
      "probability": "LOW",
      "gap_score": 0.51
    }
  ],
  "created_at": "2025-02-04T12:00:00Z",
  "metadata": {
    "questions_generated": 5,
    "processing_time_seconds": 45,
    "language": "en"
  }
}
```

#### Result Model

```python
from typing import Literal

class GapQuestion(BaseModel):
    """Individual gap analysis question."""

    question_id: Annotated[str, Field(description="Unique question identifier (UUID)")]
    question: Annotated[str, Field(description="The question text")]
    impact: Annotated[
        Literal['HIGH', 'MEDIUM', 'LOW'],
        Field(description="Impact level of this gap")
    ]
    probability: Annotated[
        Literal['HIGH', 'MEDIUM', 'LOW'],
        Field(description="Likelihood user has this experience")
    ]
    gap_score: Annotated[float, Field(ge=0.0, le=1.0, description="Calculated priority score")]

class GapAnalysisResult(BaseModel):
    """Complete gap analysis result."""

    job_id: Annotated[str, Field(description="Job identifier")]
    user_id: Annotated[str, Field(description="User identifier")]
    job_posting: Annotated[JobPosting, Field(description="Target job posting")]
    questions: Annotated[
        list[GapQuestion],
        Field(min_length=0, max_length=5, description="Generated questions (max 5)")
    ]
    created_at: Annotated[str, Field(description="ISO 8601 timestamp")]
    metadata: Annotated[dict, Field(description="Processing metadata")]
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
- `user_id` - Required, non-empty string
- `cv_id` - Required, must reference existing CV for user
- `job_posting` - Required, valid JobPosting object
  - `company_name` - Required
  - `role_title` - Required
  - `requirements` - At least 1 item (or empty list accepted)
- `language` - Optional, defaults to 'en'

---

## Authentication & Authorization

### JWT Token Validation

- All endpoints require valid Cognito JWT in `Authorization` header
- Token format: `Bearer <jwt>`
- Token must not be expired
- Token must contain valid `sub` claim (user ID)

### User Isolation

- Users can only submit jobs for their own `user_id`
- Users can only query status of their own jobs
- Attempting to access another user's job returns `404 Not Found` (not 403, to avoid info leak)

### Presigned URL Security

- Result URLs expire after 1 hour
- URLs include user_id validation (generated per-user)
- No sensitive data in URL query parameters

---

## Rate Limiting

### Submit Endpoint

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

### Status Endpoint

- **Rate:** 60 requests per minute per user (for polling)
- **Burst:** 10 requests

---

## Timeouts

| Component | Timeout | Behavior on Timeout |
|-----------|---------|-------------------|
| Submit Handler Lambda | 30 seconds | Return 500 Internal Server Error |
| Worker Handler Lambda | 900 seconds (15 min) | Job status set to FAILED |
| LLM API Call | 600 seconds (10 min) | Return TIMEOUT error code |
| Status Handler Lambda | 30 seconds | Return 500 Internal Server Error |
| SQS Visibility Timeout | 900 seconds | Message returned to queue for retry |
| Presigned URL | 3600 seconds (1 hour) | URL becomes invalid |

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
- SQS message NOT deleted (remains in queue)
- Worker Lambda throws exception
- Message returns to queue after visibility timeout
- Retry up to 3 times (max receive count)
- If still failing, send to DLQ

**Final Job Status:** FAILED with code `LLM_API_ERROR`

---

### Scenario 3: Processing Timeout

**Trigger:** LLM API takes longer than 10 minutes

**Behavior:**
- `asyncio.wait_for()` raises `asyncio.TimeoutError`
- Job status updated to FAILED
- Error message: "Processing timeout after 10 minutes"
- Code: `TIMEOUT`

---

### Scenario 4: Invalid LLM Response

**Trigger:** LLM returns malformed JSON or unexpected structure

**Behavior:**
- Validation error caught in worker
- Job status updated to FAILED
- Error message: "Failed to parse LLM response"
- Code: `INTERNAL_ERROR`
- Log full LLM response for debugging

---

### Scenario 5: DynamoDB Write Failure

**Trigger:** DynamoDB throttling or service error

**Behavior:**
- Worker Lambda throws exception
- SQS message NOT deleted
- Automatic retry (up to 3 times)
- If still failing, send to DLQ
- Monitor DLQ for manual intervention

---

## Frontend Integration Example

### TypeScript Client

```typescript
interface GapAnalysisClient {
  async submitGapAnalysis(
    cvId: string,
    jobPosting: JobPosting
  ): Promise<string> {
    const response = await fetch('/api/gap-analysis/submit', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getJWT()}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        user_id: getCurrentUserId(),
        cv_id: cvId,
        job_posting: jobPosting,
        language: 'en'
      })
    });

    if (response.status === 202) {
      const data = await response.json();
      return data.job_id;
    }

    throw new Error('Failed to submit gap analysis');
  }

  async pollUntilComplete(jobId: string): Promise<GapAnalysisResult> {
    const maxAttempts = 60;  // 5 minutes
    const pollInterval = 5000;  // 5 seconds

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      const response = await fetch(`/api/gap-analysis/status/${jobId}`, {
        headers: { 'Authorization': `Bearer ${getJWT()}` }
      });

      const status = await response.json();

      if (status.status === 'COMPLETED') {
        const result = await fetch(status.result_url);
        return result.json();
      }

      if (status.status === 'FAILED') {
        throw new Error(status.error);
      }

      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }

    throw new Error('Gap analysis timeout');
  }
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

- [ ] Submit job → verify DynamoDB record created
- [ ] Submit job → verify SQS message sent
- [ ] Worker processing → verify status updates
- [ ] Worker processing → verify S3 result storage
- [ ] Status query → verify presigned URL generation
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
  /api/gap-analysis/submit:
    post:
      summary: Submit gap analysis job
      security:
        - CognitoAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/GapAnalysisRequest'
      responses:
        '202':
          description: Job submitted successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GapAnalysisSubmitResponse'
        '400':
          $ref: '#/components/responses/BadRequest'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '413':
          $ref: '#/components/responses/PayloadTooLarge'

  /api/gap-analysis/status/{job_id}:
    get:
      summary: Get gap analysis status
      security:
        - CognitoAuth: []
      parameters:
        - name: job_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Job status
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GapAnalysisStatusResponse'
        '404':
          $ref: '#/components/responses/NotFound'

components:
  schemas:
    GapAnalysisRequest:
      type: object
      required: [user_id, cv_id, job_posting]
      properties:
        user_id:
          type: string
        cv_id:
          type: string
        job_posting:
          $ref: '#/components/schemas/JobPosting'
        language:
          type: string
          enum: [en, he]
          default: en

    GapAnalysisSubmitResponse:
      type: object
      properties:
        job_id:
          type: string
          format: uuid
        status:
          type: string
          enum: [PENDING]
        created_at:
          type: string
          format: date-time
        message:
          type: string

    GapAnalysisStatusResponse:
      type: object
      properties:
        job_id:
          type: string
        status:
          type: string
          enum: [PENDING, PROCESSING, COMPLETED, FAILED]
        created_at:
          type: string
        result_url:
          type: string
          nullable: true
        error:
          type: string
          nullable: true

  securitySchemes:
    CognitoAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
```

---

## Monitoring & Alerts

### CloudWatch Metrics

- `GapAnalysis.JobsSubmitted` - Counter
- `GapAnalysis.JobsCompleted` - Counter
- `GapAnalysis.JobsFailed` - Counter
- `GapAnalysis.ProcessingDuration` - Histogram
- `GapAnalysis.QuestionsGenerated` - Histogram (0-5)

### CloudWatch Alarms

| Alarm | Threshold | Action |
|-------|-----------|--------|
| DLQ Message Count | > 0 | SNS notification to dev team |
| Worker Error Rate | > 5% of invocations | SNS notification |
| Processing Duration P99 | > 10 minutes | SNS notification |
| Submit Handler Errors | > 10 in 5 minutes | SNS notification |

---

## References

- **Architecture:** [GAP_ANALYSIS_DESIGN.md](../../architecture/GAP_ANALYSIS_DESIGN.md)
- **Async Foundation:** [VPR_ASYNC_DESIGN.md](../../architecture/VPR_ASYNC_DESIGN.md)
- **Models:** `src/backend/careervp/models/job.py`
- **Result Codes:** `src/backend/careervp/models/result.py`
