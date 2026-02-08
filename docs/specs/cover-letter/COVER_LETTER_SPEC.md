# Cover Letter Generation API Specification

**Version:** 1.0
**Date:** 2026-02-05
**Author:** Claude Sonnet 4.5 (Lead Architect)
**Status:** Specification Complete - Ready for Implementation

---

## Table of Contents

1. [Overview](#overview)
2. [API Endpoint](#api-endpoint)
3. [Request Model](#request-model)
4. [Response Model](#response-model)
5. [Result Codes](#result-codes)
6. [Error Handling](#error-handling)
7. [Authentication & Authorization](#authentication--authorization)
8. [Rate Limiting](#rate-limiting)
9. [Security](#security)
10. [OpenAPI Schema](#openapi-schema)
11. [Example Requests & Responses](#example-requests--responses)
12. [Appendices](#appendices)

---

## Overview

### Purpose

The Cover Letter Generation API provides an endpoint for creating personalized, compelling cover letters tailored to specific job positions. It synthesizes the user's Value Proposition Report (VPR), tailored CV, gap analysis responses, and company research into a human-sounding cover letter that passes anti-AI detection filters.

### Key Features

- ✅ **Personalization**: Creates compelling narratives showcasing specific accomplishments aligned with job requirements
- ✅ **Quality Scoring**: Evaluates personalization, relevance, and tone appropriateness with weighted scoring
- ✅ **FVS Validation**: Ensures company name and job title match verifiable facts
- ✅ **Anti-AI Detection**: Generates natural-sounding text with varied sentence structure and authentic language
- ✅ **Cost Optimization**: Uses Claude Haiku 4.5 ($0.004-0.006 per letter)
- ✅ **Artifact Storage**: Stores generated cover letters for 90 days with TTL auto-cleanup
- ✅ **Download Support**: Provides presigned S3 URLs for easy download

### Integration Points

- **Upstream**: Frontend (React App), Mobile App
- **Downstream**: DynamoDB (cover letter storage), Bedrock (Claude Haiku/Sonnet 4.5), FVS Validator, S3 (artifacts)

---

## API Endpoint

### POST /api/cover-letter

Generate a personalized cover letter optimized for a specific job position.

**Endpoint:** `POST /api/cover-letter`

**Method:** POST

**Content-Type:** application/json

**Authentication:** Required (Cognito JWT)

**Rate Limit:** 5-50 requests per minute per user (depends on tier)

**Timeout:** 300 seconds (Lambda timeout)

---

## Request Model

### GenerateCoverLetterRequest (Pydantic)

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime

class CoverLetterPreferences(BaseModel):
    """User preferences for cover letter generation."""

    tone: Literal["professional", "enthusiastic", "technical"] = Field(
        default="professional",
        description="Tone of cover letter: 'professional', 'enthusiastic', or 'technical'"
    )
    word_count_target: int = Field(
        default=300,
        ge=200,
        le=500,
        description="Target word count (200-500 words)"
    )
    emphasis_areas: Optional[List[str]] = Field(
        default=None,
        description="Areas to emphasize: e.g., ['leadership', 'Python', 'AWS']"
    )
    include_salary_expectations: bool = Field(
        default=False,
        description="Whether to include salary expectations discussion"
    )


class GapAnalysisResponse(BaseModel):
    """Single gap analysis response."""
    question_id: str
    question_text: str
    response_text: str
    skills_mentioned: list[str]


class GapAnalysisResponses(BaseModel):
    """Collection of gap analysis responses."""
    responses: list[GapAnalysisResponse]


class GenerateCoverLetterRequest(BaseModel):
    """Request to generate a personalized cover letter."""

    cv_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="ID of the master CV to use"
    )
    job_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="ID of the target job posting"
    )
    company_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Company name (used for FVS validation)"
    )
    job_title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Job title (used for FVS validation)"
    )
    job_description: Optional[str] = Field(
        default=None,
        max_length=50000,
        description="Full job description text (optional, up to 50,000 chars)"
    )
    gap_responses: Optional[GapAnalysisResponses] = Field(
        default=None,
        description="Optional gap analysis responses for additional context"
    )
    preferences: Optional[CoverLetterPreferences] = Field(
        default=None,
        description="Optional generation preferences"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "cv_id": "cv_abc123",
                "job_id": "job_xyz789",
                "company_name": "TechCorp Inc",
                "job_title": "Senior Python Engineer",
                "job_description": "We are seeking a Senior Python Engineer with 5+ years...",
                "gap_responses": {
                    "responses": [
                        {
                            "question_id": "q1",
                            "question_text": "Describe your experience with Python and AWS",
                            "response_text": "I have 6 years of experience building scalable systems with Python and AWS...",
                            "skills_mentioned": ["Python", "AWS", "Lambda", "DynamoDB"]
                        }
                    ]
                },
                "preferences": {
                    "tone": "professional",
                    "word_count_target": 300,
                    "emphasis_areas": ["leadership", "python", "aws"],
                    "include_salary_expectations": False
                }
            }
        }
```

### Field Validation Rules

| Field | Required | Type | Constraints | Description |
|-------|----------|------|-------------|-------------|
| `cv_id` | ✅ Yes | string | 1-255 chars | Master CV identifier |
| `job_id` | ✅ Yes | string | 1-255 chars | Target job posting ID |
| `company_name` | ✅ Yes | string | 1-255 chars | Company hiring for role (for FVS) |
| `job_title` | ✅ Yes | string | 1-255 chars | Job title (for FVS) |
| `job_description` | ❌ No | string | 0-50,000 chars | Full job posting text |
| `preferences` | ❌ No | object | Optional | Generation preferences |
| `preferences.tone` | ❌ No | enum | 'professional' \| 'enthusiastic' \| 'technical' | Tone of letter |
| `preferences.word_count_target` | ❌ No | integer | 200-500 | Target word count |
| `preferences.emphasis_areas` | ❌ No | array | String array | Areas to emphasize |
| `preferences.include_salary_expectations` | ❌ No | boolean | true \| false | Include salary discussion |

---

## Response Model

### TailoredCoverLetterResponse (Pydantic)

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class TailoredCoverLetter(BaseModel):
    """Generated cover letter with metadata."""

    cover_letter_id: str = Field(
        description="Unique identifier for this cover letter artifact"
    )
    cv_id: str = Field(description="ID of the CV used for generation")
    job_id: str = Field(description="ID of the target job posting")
    user_id: str = Field(description="ID of the user who owns this letter")
    company_name: str = Field(description="Company name from request")
    job_title: str = Field(description="Job title from request")
    content: str = Field(description="The full cover letter text")
    word_count: int = Field(ge=0, description="Actual word count")
    personalization_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Score 0.0-1.0: specific accomplishments and metrics"
    )
    relevance_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Score 0.0-1.0: job requirement alignment"
    )
    tone_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Score 0.0-1.0: tone appropriateness"
    )
    generated_at: datetime = Field(description="ISO 8601 timestamp of generation")


class FVSValidationResult(BaseModel):
    """FVS validation result for cover letter."""

    is_valid: bool = Field(description="Whether all critical validations passed")
    company_name_verified: bool = Field(description="Company name found in letter")
    job_title_verified: bool = Field(description="Job title found in letter")
    violations: List[dict] = Field(
        default=[],
        description="List of FVS violations (if any)"
    )


class TailoredCoverLetterResponse(BaseModel):
    """Response for cover letter generation request."""

    success: bool = Field(description="True if generation succeeded")
    cover_letter: Optional[TailoredCoverLetter] = Field(
        default=None,
        description="Generated cover letter (null if failed)"
    )
    fvs_validation: Optional[FVSValidationResult] = Field(
        default=None,
        description="FVS validation result"
    )
    quality_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall quality score (40% personalization + 35% relevance + 25% tone)"
    )
    code: str = Field(description="Result code (see Result Codes section)")
    processing_time_ms: int = Field(description="Total processing time in milliseconds")
    cost_estimate: float = Field(description="Estimated cost in USD for this operation")
    download_url: Optional[str] = Field(
        default=None,
        description="Pre-signed S3 URL for downloading cover letter (expires in 24 hours)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "cover_letter": {
                    "cover_letter_id": "cl_abc123",
                    "cv_id": "cv_abc123",
                    "job_id": "job_xyz789",
                    "user_id": "user_123",
                    "company_name": "TechCorp Inc",
                    "job_title": "Senior Python Engineer",
                    "content": "Dear Hiring Manager,\n\nI was excited to see the Senior Python Engineer position at TechCorp Inc...",
                    "word_count": 287,
                    "personalization_score": 0.82,
                    "relevance_score": 0.79,
                    "tone_score": 0.85,
                    "generated_at": "2026-02-05T12:00:00Z"
                },
                "fvs_validation": {
                    "is_valid": True,
                    "company_name_verified": True,
                    "job_title_verified": True,
                    "violations": []
                },
                "quality_score": 0.815,
                "code": "COVER_LETTER_GENERATED_SUCCESS",
                "processing_time_ms": 8432,
                "cost_estimate": 0.00542,
                "download_url": "https://s3.amazonaws.com/careervp-artifacts/cover-letters/cl_abc123.pdf?X-Amz-Expires=86400&..."
            }
        }
```

### Response Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | True if generation succeeded, False otherwise |
| `cover_letter` | object | Generated cover letter object (null if failed) |
| `fvs_validation` | object | FVS validation result with company/job title verification |
| `quality_score` | float | Overall quality score (0.0-1.0) combining multiple dimensions |
| `code` | string | Result code (see Result Codes section) |
| `processing_time_ms` | integer | Total processing time in milliseconds |
| `cost_estimate` | float | Estimated cost in USD |
| `download_url` | string | Pre-signed S3 URL for download (expires in 24 hours) |

---

## Result Codes

### Success Codes

| Code | Description | HTTP Status | Response |
|------|-------------|-------------|----------|
| `COVER_LETTER_GENERATED_SUCCESS` | Cover letter generated successfully | 200 OK | TailoredCoverLetterResponse with cover_letter |
| `COVER_LETTER_GENERATED_WITH_WARNINGS` | Cover letter generated but quality threshold not met | 200 OK | TailoredCoverLetterResponse with quality_score |

### Error Codes

| Code | Description | HTTP Status | Response |
|------|-------------|-------------|----------|
| `INVALID_REQUEST` | Request validation failed | 400 Bad Request | Error message with validation details |
| `CV_NOT_FOUND` | Master CV not found for user | 404 Not Found | "CV with id {cv_id} not found for user" |
| `JOB_NOT_FOUND` | Job posting not found for user | 404 Not Found | "Job with id {job_id} not found for user" |
| `VPR_NOT_FOUND` | VPR artifact not found (required for generation) | 400 Bad Request | "VPR not found - generate VPR first" |
| `FVS_HALLUCINATION_DETECTED` | CRITICAL FVS violations (company/job mismatch) | 400 Bad Request | FVS violations list in response |
| `CV_LETTER_GENERATION_TIMEOUT` | LLM call exceeded 300 second timeout | 504 Gateway Timeout | "Cover letter generation timed out, please retry" |
| `LLM_RATE_LIMITED` | Bedrock service rate limited | 429 Too Many Requests | "Service temporarily unavailable, please retry in 60 seconds" |
| `GENERATION_QUALITY_INSUFFICIENT` | Quality score below minimum threshold | 500 Internal Server Error | "Generated cover letter quality insufficient, please try again" |
| `STORAGE_ERROR` | Failed to store cover letter artifact | 500 Internal Server Error | "Failed to persist cover letter" |
| `UNAUTHORIZED` | Missing or invalid authentication token | 401 Unauthorized | "Authentication required" |
| `FORBIDDEN` | User not authorized to access this CV/job | 403 Forbidden | "Access denied to CV {cv_id}" |
| `RATE_LIMIT_EXCEEDED` | User exceeded rate limit | 429 Too Many Requests | "Rate limit exceeded: X requests per minute" |

---

## Error Handling

### Error Response Format

All error responses follow this format:

```json
{
  "success": false,
  "cover_letter": null,
  "error": "Detailed error message",
  "code": "ERROR_CODE",
  "processing_time_ms": 123,
  "cost_estimate": 0.0
}
```

### Error Handling Strategy

#### 1. Input Validation Errors (400 Bad Request)

**Scenario:** Invalid request body (missing cv_id, invalid company_name)

**Response:**
```json
{
  "success": false,
  "error": "Validation error: company_name must be between 1 and 255 characters",
  "code": "INVALID_REQUEST",
  "processing_time_ms": 5
}
```

**Client Action:** Fix request and retry

---

#### 2. CV Not Found (404 Not Found)

**Scenario:** Requested cv_id doesn't exist for user

**Response:**
```json
{
  "success": false,
  "error": "CV with id 'cv_abc123' not found for user",
  "code": "CV_NOT_FOUND",
  "processing_time_ms": 120
}
```

**Client Action:** Verify cv_id is correct

---

#### 3. VPR Not Found (400 Bad Request)

**Scenario:** VPR artifact doesn't exist (required for personalization)

**Response:**
```json
{
  "success": false,
  "error": "VPR not found for cv_id 'cv_abc123' and job_id 'job_xyz789' - generate VPR first",
  "code": "VPR_NOT_FOUND",
  "processing_time_ms": 150
}
```

**Client Action:** Generate VPR first via /api/vpr endpoint

---

#### 4. FVS Validation Failure (400 Bad Request)

**Scenario:** Generated cover letter has company or job title mismatch

**Response:**
```json
{
  "success": false,
  "error": "FVS validation failed: company name not found in cover letter",
  "code": "FVS_HALLUCINATION_DETECTED",
  "fvs_validation": {
    "is_valid": false,
    "company_name_verified": false,
    "job_title_verified": true,
    "violations": [
      {
        "field": "company_name",
        "expected": "TechCorp Inc",
        "severity": "CRITICAL",
        "message": "Company name 'TechCorp Inc' not found in generated letter"
      }
    ]
  },
  "processing_time_ms": 9500,
  "cost_estimate": 0.00542
}
```

**Client Action:** Report bug to support (should not happen with correct prompt engineering)

---

#### 5. LLM Timeout (504 Gateway Timeout)

**Scenario:** LLM call exceeded 300 second timeout

**Response:**
```json
{
  "success": false,
  "error": "Cover letter generation timed out after 300 seconds. Please try again.",
  "code": "CV_LETTER_GENERATION_TIMEOUT",
  "processing_time_ms": 300000,
  "cost_estimate": 0.00
}
```

**Client Action:** Retry request

---

#### 6. Rate Limit Exceeded (429 Too Many Requests)

**Scenario:** User exceeded 5 requests per minute

**Response:**
```json
{
  "success": false,
  "error": "Rate limit exceeded: 5 requests per minute. Please wait 45 seconds.",
  "code": "RATE_LIMIT_EXCEEDED",
  "processing_time_ms": 5,
  "retry_after": 45
}
```

**Client Action:** Wait `retry_after` seconds before retrying

---

## Authentication & Authorization

### Authentication

**Method:** Cognito JWT (JSON Web Token)

**Header:** `Authorization: Bearer <JWT_TOKEN>`

**Token Requirements:**
- Valid Cognito JWT
- Not expired
- Issued by CareerVP Cognito User Pool

**Example Request:**
```bash
curl -X POST https://api.careervp.com/api/cover-letter \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "cv_id": "cv_abc123",
    "job_id": "job_xyz789",
    "company_name": "TechCorp Inc",
    "job_title": "Senior Python Engineer"
  }'
```

### Authorization

**Rule:** Users can only generate cover letters for their own CVs and jobs

**Validation:**
```python
# Extract user_id from JWT token
user_id = jwt_token.claims["sub"]

# Fetch master CV from DynamoDB
master_cv = dal.get_cv(cv_id)

# Verify ownership
if master_cv.user_id != user_id:
    return Response(
        status_code=403,
        body={"error": "Access denied to CV {cv_id}", "code": "FORBIDDEN"}
    )

# Verify job ownership
job = dal.get_job(job_id)
if job.user_id != user_id:
    return Response(
        status_code=403,
        body={"error": "Access denied to job {job_id}", "code": "FORBIDDEN"}
    )
```

**Error Response (403 Forbidden):**
```json
{
  "success": false,
  "error": "Access denied to CV cv_abc123",
  "code": "FORBIDDEN"
}
```

---

## Rate Limiting

### Rate Limit Rules

| User Type | Requests per Minute | Requests per Hour | Requests per Day |
|-----------|---------------------|-------------------|------------------|
| **Free Tier** | 5 | 30 | 200 |
| **Premium** | 15 | 100 | 1000 |
| **Enterprise** | 50 | 500 | 5000 |

### Rate Limit Headers

All responses include rate limit headers:

```
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 3
X-RateLimit-Reset: 1633072845
```

### Rate Limit Exceeded Response

**HTTP Status:** 429 Too Many Requests

**Response:**
```json
{
  "success": false,
  "error": "Rate limit exceeded: 5 requests per minute. Please wait 45 seconds.",
  "code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 45
}
```

**Headers:**
```
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1633072845
Retry-After: 45
```

---

## Security

### Input Validation

All request fields are validated before processing:

```python
# Company name validation
- Length: 1-255 characters
- Characters: Alphanumeric, spaces, hyphens, periods, ampersands only
- Pattern: No special characters that could cause XSS

# Job title validation
- Length: 1-255 characters
- Characters: Alphanumeric, spaces, hyphens, parentheses only
- Pattern: No special characters

# Word count target validation
- Range: 200-500 words
- Type: Integer only
```

### XSS Prevention

All text inputs are sanitized to prevent XSS attacks:

```python
import html

# Sanitize inputs
company_name = html.escape(request.company_name)
job_title = html.escape(request.job_title)

# Remove any potential script tags
content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE)
content = re.sub(r'on\w+\s*=', '', content)
```

### CORS Configuration

CORS is restricted to CareerVP frontend domains:

```python
ALLOWED_ORIGINS = [
    "https://careervp.com",
    "https://app.careervp.com",
    "https://staging.careervp.com",
    "http://localhost:3000",  # Local development only
]

CORS_CONFIG = {
    "allow_origins": ALLOWED_ORIGINS,
    "allow_credentials": True,
    "allow_methods": ["POST"],
    "allow_headers": ["Content-Type", "Authorization"],
    "max_age": 3600,
}
```

---

## OpenAPI Schema

### OpenAPI 3.0 Specification

```yaml
openapi: 3.0.0
info:
  title: CareerVP Cover Letter Generation API
  version: 1.0.0
  description: API for generating personalized cover letters tailored to specific job positions

servers:
  - url: https://api.careervp.com
    description: Production server
  - url: https://staging-api.careervp.com
    description: Staging server
  - url: http://localhost:8000
    description: Local development server

paths:
  /api/cover-letter:
    post:
      summary: Generate personalized cover letter
      description: Generate a tailored cover letter optimized for a specific job position
      operationId: generateCoverLetter
      tags:
        - Cover Letter Generation
      security:
        - CognitoJWT: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/GenerateCoverLetterRequest'
      responses:
        '200':
          description: Cover letter generated successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TailoredCoverLetterResponse'
        '400':
          description: Bad request (invalid input, FVS validation failure, or VPR not found)
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '401':
          description: Unauthorized (missing or invalid token)
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '403':
          description: Forbidden (user not authorized to access CV/job)
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '404':
          description: CV or job not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '429':
          description: Rate limit exceeded
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '504':
          description: Gateway timeout (LLM timeout)
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

components:
  securitySchemes:
    CognitoJWT:
      type: http
      scheme: bearer
      bearerFormat: JWT

  schemas:
    GenerateCoverLetterRequest:
      type: object
      required:
        - cv_id
        - job_id
        - company_name
        - job_title
      properties:
        cv_id:
          type: string
          minLength: 1
          maxLength: 255
          description: ID of the master CV to use
        job_id:
          type: string
          minLength: 1
          maxLength: 255
          description: ID of the target job posting
        company_name:
          type: string
          minLength: 1
          maxLength: 255
          description: Company name (used for FVS validation)
        job_title:
          type: string
          minLength: 1
          maxLength: 255
          description: Job title (used for FVS validation)
        job_description:
          type: string
          maxLength: 50000
          description: Full job description text (optional)
        preferences:
          $ref: '#/components/schemas/CoverLetterPreferences'

    CoverLetterPreferences:
      type: object
      properties:
        tone:
          type: string
          enum: [professional, enthusiastic, technical]
          default: professional
          description: Tone of the cover letter
        word_count_target:
          type: integer
          minimum: 200
          maximum: 500
          default: 300
          description: Target word count
        emphasis_areas:
          type: array
          items:
            type: string
          description: Areas to emphasize
        include_salary_expectations:
          type: boolean
          default: false
          description: Whether to include salary expectations

    TailoredCoverLetterResponse:
      type: object
      required:
        - success
        - quality_score
        - code
        - processing_time_ms
        - cost_estimate
      properties:
        success:
          type: boolean
        cover_letter:
          $ref: '#/components/schemas/TailoredCoverLetter'
        fvs_validation:
          $ref: '#/components/schemas/FVSValidationResult'
        quality_score:
          type: number
          minimum: 0.0
          maximum: 1.0
        code:
          type: string
        processing_time_ms:
          type: integer
        cost_estimate:
          type: number
          format: float
        download_url:
          type: string
          format: uri

    TailoredCoverLetter:
      type: object
      required:
        - cover_letter_id
        - cv_id
        - job_id
        - user_id
        - company_name
        - job_title
        - content
        - word_count
        - personalization_score
        - relevance_score
        - tone_score
        - generated_at
      properties:
        cover_letter_id:
          type: string
        cv_id:
          type: string
        job_id:
          type: string
        user_id:
          type: string
        company_name:
          type: string
        job_title:
          type: string
        content:
          type: string
        word_count:
          type: integer
          minimum: 0
        personalization_score:
          type: number
          minimum: 0.0
          maximum: 1.0
        relevance_score:
          type: number
          minimum: 0.0
          maximum: 1.0
        tone_score:
          type: number
          minimum: 0.0
          maximum: 1.0
        generated_at:
          type: string
          format: date-time

    FVSValidationResult:
      type: object
      required:
        - is_valid
        - company_name_verified
        - job_title_verified
        - violations
      properties:
        is_valid:
          type: boolean
        company_name_verified:
          type: boolean
        job_title_verified:
          type: boolean
        violations:
          type: array
          items:
            type: object
            properties:
              field:
                type: string
              expected:
                type: string
              severity:
                type: string
                enum: [WARNING, CRITICAL]

    ErrorResponse:
      type: object
      required:
        - success
        - error
        - code
      properties:
        success:
          type: boolean
          enum: [false]
        error:
          type: string
        code:
          type: string
        processing_time_ms:
          type: integer
        retry_after:
          type: integer
```

---

## Example Requests & Responses

### Example 1: Successful Cover Letter Generation

**Request:**
```bash
POST /api/cover-letter HTTP/1.1
Host: api.careervp.com
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "cv_id": "cv_abc123",
  "job_id": "job_xyz789",
  "company_name": "TechCorp Inc",
  "job_title": "Senior Python Engineer",
  "job_description": "We are seeking a Senior Python Engineer with 5+ years of experience in backend development. Must have expertise in Django, REST APIs, and PostgreSQL. Experience with Docker and Kubernetes is a plus.",
  "preferences": {
    "tone": "professional",
    "word_count_target": 300,
    "emphasis_areas": ["leadership", "python", "aws"],
    "include_salary_expectations": false
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "cover_letter": {
    "cover_letter_id": "cl_abc123",
    "cv_id": "cv_abc123",
    "job_id": "job_xyz789",
    "user_id": "user_123",
    "company_name": "TechCorp Inc",
    "job_title": "Senior Python Engineer",
    "content": "Dear Hiring Manager,\n\nI was excited to see the Senior Python Engineer position at TechCorp Inc. With six years of experience building backend systems and REST APIs using Python and Django, I believe I'm well-positioned to contribute to your team.\n\nDuring my time at FinTech Corp, I led development of a microservices-based payment processing platform that handled 2 million daily requests with 99.99% uptime. This experience taught me the value of clean code, thorough testing, and effective team communication—qualities I see reflected in your company culture.\n\nWhat attracted me to this role is TechCorp's commitment to technical excellence and your recent expansion into AI-powered features. I've shipped production systems in Python handling high-volume traffic, and I'm eager to bring that expertise to your backend team.\n\nBeyond technical skills, I'm passionate about mentoring junior developers and fostering collaborative engineering environments. I'd welcome the opportunity to discuss how my background aligns with TechCorp's vision.\n\nThank you for considering my application.",
    "word_count": 147,
    "personalization_score": 0.82,
    "relevance_score": 0.79,
    "tone_score": 0.85,
    "generated_at": "2026-02-05T12:00:00Z"
  },
  "fvs_validation": {
    "is_valid": true,
    "company_name_verified": true,
    "job_title_verified": true,
    "violations": []
  },
  "quality_score": 0.815,
  "code": "COVER_LETTER_GENERATED_SUCCESS",
  "processing_time_ms": 8432,
  "cost_estimate": 0.00542,
  "download_url": "https://s3.amazonaws.com/careervp-artifacts/cover-letters/cl_abc123.pdf?X-Amz-Expires=86400&X-Amz-Signature=..."
}
```

---

### Example 2: FVS Validation Failure

**Request:**
```bash
POST /api/cover-letter HTTP/1.1
Host: api.careervp.com
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "cv_id": "cv_abc123",
  "job_id": "job_xyz789",
  "company_name": "Microsoft",
  "job_title": "Senior Software Engineer",
  "job_description": "We are seeking a Senior Software Engineer..."
}
```

**Response (400 Bad Request):**
```json
{
  "success": false,
  "cover_letter": null,
  "error": "FVS validation failed: company name not found in generated letter",
  "code": "FVS_HALLUCINATION_DETECTED",
  "fvs_validation": {
    "is_valid": false,
    "company_name_verified": false,
    "job_title_verified": true,
    "violations": [
      {
        "field": "company_name",
        "expected": "Microsoft",
        "severity": "CRITICAL",
        "message": "Company name 'Microsoft' not found in generated cover letter"
      }
    ]
  },
  "quality_score": 0.0,
  "code": "FVS_HALLUCINATION_DETECTED",
  "processing_time_ms": 9234,
  "cost_estimate": 0.00542
}
```

---

### Example 3: VPR Not Found

**Request:**
```bash
POST /api/cover-letter HTTP/1.1
Host: api.careervp.com
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "cv_id": "cv_abc123",
  "job_id": "job_nonexistent",
  "company_name": "TechCorp Inc",
  "job_title": "Senior Python Engineer"
}
```

**Response (400 Bad Request):**
```json
{
  "success": false,
  "cover_letter": null,
  "error": "VPR not found for cv_id 'cv_abc123' and job_id 'job_nonexistent' - generate VPR first",
  "code": "VPR_NOT_FOUND",
  "processing_time_ms": 150,
  "cost_estimate": 0.0
}
```

---

### Example 4: CV Not Found

**Request:**
```bash
POST /api/cover-letter HTTP/1.1
Host: api.careervp.com
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "cv_id": "cv_nonexistent",
  "job_id": "job_xyz789",
  "company_name": "TechCorp Inc",
  "job_title": "Senior Python Engineer"
}
```

**Response (404 Not Found):**
```json
{
  "success": false,
  "cover_letter": null,
  "error": "CV with id 'cv_nonexistent' not found for user",
  "code": "CV_NOT_FOUND",
  "processing_time_ms": 120,
  "cost_estimate": 0.0
}
```

---

### Example 5: Rate Limit Exceeded

**Request:**
```bash
POST /api/cover-letter HTTP/1.1
Host: api.careervp.com
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "cv_id": "cv_abc123",
  "job_id": "job_xyz789",
  "company_name": "TechCorp Inc",
  "job_title": "Senior Python Engineer"
}
```

**Response (429 Too Many Requests):**
```json
{
  "success": false,
  "cover_letter": null,
  "error": "Rate limit exceeded: 5 requests per minute. Please wait 45 seconds.",
  "code": "RATE_LIMIT_EXCEEDED",
  "processing_time_ms": 5,
  "retry_after": 45
}
```

**Headers:**
```
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1633072845
Retry-After: 45
Content-Type: application/json
```

---

### Example 6: Invalid Input

**Request:**
```bash
POST /api/cover-letter HTTP/1.1
Host: api.careervp.com
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "cv_id": "cv_abc123",
  "job_id": "job_xyz789",
  "company_name": "",
  "job_title": "Senior Python Engineer"
}
```

**Response (400 Bad Request):**
```json
{
  "success": false,
  "cover_letter": null,
  "error": "Validation error: company_name must be between 1 and 255 characters (got 0)",
  "code": "INVALID_REQUEST",
  "processing_time_ms": 5,
  "cost_estimate": 0.0
}
```

---

### Example 7: LLM Timeout

**Request:**
```bash
POST /api/cover-letter HTTP/1.1
Host: api.careervp.com
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "cv_id": "cv_abc123",
  "job_id": "job_xyz789",
  "company_name": "TechCorp Inc",
  "job_title": "Senior Python Engineer",
  "job_description": "[50,000 character extremely long job description that causes LLM to timeout]"
}
```

**Response (504 Gateway Timeout):**
```json
{
  "success": false,
  "cover_letter": null,
  "error": "Cover letter generation timed out after 300 seconds. Please try again.",
  "code": "CV_LETTER_GENERATION_TIMEOUT",
  "processing_time_ms": 300000,
  "cost_estimate": 0.0
}
```

---

### Example 8: Enthusiastic Tone

**Request:**
```bash
POST /api/cover-letter HTTP/1.1
Host: api.careervp.com
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "cv_id": "cv_abc123",
  "job_id": "job_xyz789",
  "company_name": "TechCorp Inc",
  "job_title": "Senior Python Engineer",
  "preferences": {
    "tone": "enthusiastic",
    "word_count_target": 300,
    "emphasis_areas": ["innovation", "team", "growth"]
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "cover_letter": {
    "cover_letter_id": "cl_def456",
    "cv_id": "cv_abc123",
    "job_id": "job_xyz789",
    "user_id": "user_123",
    "company_name": "TechCorp Inc",
    "job_title": "Senior Python Engineer",
    "content": "Dear Hiring Manager,\n\nI'm thrilled about the Senior Python Engineer opportunity at TechCorp Inc! When I first learned about your team's mission to revolutionize backend infrastructure, I knew I had to apply.\n\nWhat excites me most is your commitment to innovation. I've spent the last six years building high-performance Python systems, and I'm passionate about solving complex technical challenges. At my current role, I shipped a microservices platform that processes 2M transactions daily—something I'm incredibly proud of.\n\nBut here's what really drives me: the people and culture. Your team clearly values collaboration and growth, which aligns perfectly with how I approach engineering. I love mentoring junior developers and fostering environments where everyone can do their best work.\n\nI'm not just looking for a job; I'm looking for a team where I can make a real impact. TechCorp's vision resonates with me deeply, and I can't wait to contribute to your success.\n\nLet's talk soon!",
    "word_count": 168,
    "personalization_score": 0.85,
    "relevance_score": 0.81,
    "tone_score": 0.88,
    "generated_at": "2026-02-05T12:15:00Z"
  },
  "fvs_validation": {
    "is_valid": true,
    "company_name_verified": true,
    "job_title_verified": true,
    "violations": []
  },
  "quality_score": 0.84,
  "code": "COVER_LETTER_GENERATED_SUCCESS",
  "processing_time_ms": 7821,
  "cost_estimate": 0.00538,
  "download_url": "https://s3.amazonaws.com/careervp-artifacts/cover-letters/cl_def456.pdf?X-Amz-Expires=86400&..."
}
```

---

## Appendices

### A. HTTP Status Code Summary

| Status Code | Meaning | When to Return |
|-------------|---------|----------------|
| 200 OK | Success | Cover letter generated successfully |
| 400 Bad Request | Client error | Invalid input, VPR not found, FVS validation failure |
| 401 Unauthorized | Authentication required | Missing or invalid JWT |
| 403 Forbidden | Authorization denied | User doesn't own CV or job |
| 404 Not Found | Resource not found | CV or job doesn't exist |
| 429 Too Many Requests | Rate limit exceeded | User exceeded quota |
| 500 Internal Server Error | Server error | Unexpected error, quality insufficient |
| 504 Gateway Timeout | Timeout | LLM call exceeded 300s |

### B. Result Code to HTTP Status Mapping

```python
RESULT_CODE_TO_HTTP_STATUS = {
    "COVER_LETTER_GENERATED_SUCCESS": 200,
    "COVER_LETTER_GENERATED_WITH_WARNINGS": 200,
    "INVALID_REQUEST": 400,
    "VPR_NOT_FOUND": 400,
    "FVS_HALLUCINATION_DETECTED": 400,
    "CV_NOT_FOUND": 404,
    "JOB_NOT_FOUND": 404,
    "CV_LETTER_GENERATION_TIMEOUT": 504,
    "LLM_RATE_LIMITED": 429,
    "GENERATION_QUALITY_INSUFFICIENT": 500,
    "STORAGE_ERROR": 500,
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "RATE_LIMIT_EXCEEDED": 429,
}
```

### C. Quality Score Interpretation

| Score Range | Rating | Recommendation |
|-------------|--------|-----------------|
| 0.80 - 1.00 | Excellent | Ready to submit without changes |
| 0.70 - 0.79 | Good | Ready to submit, optional refinement |
| 0.60 - 0.69 | Acceptable | Consider refinement before submitting |
| 0.50 - 0.59 | Below Threshold | Recommend regeneration |
| < 0.50 | Insufficient | Regenerate required |

### D. Cost Analysis

**Per Cover Letter Cost Breakdown:**

| Component | Tokens | Rate | Cost |
|-----------|--------|------|------|
| Input tokens (CV + VPR + Prompt) | ~12,000 | $0.25/MTok | $0.003 |
| Output tokens (Cover letter) | ~600 | $1.25/MTok | $0.00075 |
| Haiku subtotal | — | — | $0.00375 |
| Overhead (retries, errors) | — | — | $0.001-0.002 |
| **Total per letter (Haiku)** | — | — | **$0.004-0.006** |

**Fallback to Sonnet (10% of requests):**

| Component | Tokens | Rate | Cost |
|-----------|--------|------|------|
| Input tokens | ~12,000 | $3/MTok | $0.036 |
| Output tokens | ~600 | $15/MTok | $0.009 |
| **Sonnet subtotal** | — | — | **$0.045** |

**Blended Average (90% Haiku + 10% Sonnet):**
- LLM cost: $0.00375 * 0.90 + $0.045 * 0.10 = $0.0074

### E. Rate Limiting Examples

**Scenario 1: Free Tier User**
```
Request 1-5: SUCCESS (200 OK)
Request 6: RATE_LIMIT_EXCEEDED (429)
- Retry-After: 12 seconds
- X-RateLimit-Reset: current_time + 60

After 60 seconds: Counter resets, requests available again
```

**Scenario 2: Premium User**
```
Request 1-15: SUCCESS (200 OK)
Request 16: RATE_LIMIT_EXCEEDED (429)
- Retry-After: 4 seconds
- X-RateLimit-Reset: current_time + 60

After 60 seconds: Counter resets, requests available again
```

### F. Field Constraint Examples

**Valid Requests:**
```json
// Minimal
{
  "cv_id": "cv_123",
  "job_id": "job_456",
  "company_name": "ACME Corp",
  "job_title": "Manager"
}

// Maximal
{
  "cv_id": "cv_" + "a" * 251,  // 255 chars total
  "job_id": "job_" + "b" * 251,  // 255 chars total
  "company_name": "C" * 255,  // 255 chars
  "job_title": "T" * 255,  // 255 chars
  "job_description": "J" * 50000,  // 50,000 chars
  "preferences": {
    "tone": "technical",
    "word_count_target": 500,
    "emphasis_areas": ["skill1", "skill2", "skill3"],
    "include_salary_expectations": true
  }
}
```

**Invalid Requests:**
```json
// Missing required field
{
  "cv_id": "cv_123",
  "job_id": "job_456",
  "company_name": "ACME Corp"
  // Missing job_title → INVALID_REQUEST
}

// Field too long
{
  "cv_id": "cv_123",
  "job_id": "job_456",
  "company_name": "A" * 256,  // 256 chars (max 255) → INVALID_REQUEST
  "job_title": "Manager"
}

// Invalid enum
{
  "cv_id": "cv_123",
  "job_id": "job_456",
  "company_name": "ACME Corp",
  "job_title": "Manager",
  "preferences": {
    "tone": "casual"  // Invalid: must be professional|enthusiastic|technical
  }
}

// Word count out of range
{
  "cv_id": "cv_123",
  "job_id": "job_456",
  "company_name": "ACME Corp",
  "job_title": "Manager",
  "preferences": {
    "word_count_target": 150  // Too low (min 200) → INVALID_REQUEST
  }
}
```

---

**Document Version:** 1.0
**Last Updated:** 2026-02-05
**Next Review:** After Phase 10 implementation complete
**References:** COVER_LETTER_DESIGN.md, ARCHITECT_PROMPT.md, CV_TAILORING_SPEC.md
