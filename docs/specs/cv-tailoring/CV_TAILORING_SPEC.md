# CV Tailoring API Specification

**Version:** 1.0
**Date:** 2026-02-04
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
9. [OpenAPI Schema](#openapi-schema)
10. [Example Requests & Responses](#example-requests--responses)

---

## Overview

### Purpose

The CV Tailoring API provides an endpoint for generating customized resumes optimized for specific job descriptions. It accepts a master CV and job description, then returns a tailored CV with relevance scores and FVS validation results.

### Key Features

- ✅ **Relevance Optimization**: Prioritizes CV content most relevant to job requirements
- ✅ **FVS Validation**: Ensures IMMUTABLE facts are never modified
- ✅ **ATS Optimization**: Optimizes keywords for Applicant Tracking Systems
- ✅ **Change Tracking**: Documents all modifications made to original CV
- ✅ **Artifact Storage**: Stores tailored CVs for later retrieval

### Integration Points

- **Upstream**: Frontend (React App), Mobile App
- **Downstream**: DynamoDB (CV storage), Bedrock (Claude Haiku 4.5), FVS Validator

---

## API Endpoint

### POST /api/cv-tailoring

Generate a tailored CV optimized for a specific job description.

**Endpoint:** `POST /api/cv-tailoring`

**Method:** POST

**Content-Type:** application/json

**Authentication:** Required (Cognito JWT)

**Rate Limit:** 10 requests per minute per user

**Timeout:** 60 seconds (Lambda timeout)

---

## Request Model

### TailorCVRequest (Pydantic)

```python
from pydantic import BaseModel, Field
from typing import Optional

class TailoringPreferences(BaseModel):
    """User preferences for CV tailoring."""

    tone: Optional[str] = Field(
        default="professional",
        description="Tone of tailored CV: 'professional', 'casual', 'technical'"
    )
    length: Optional[str] = Field(
        default="standard",
        description="Target CV length: 'compact' (1 page), 'standard' (2 pages), 'detailed' (3+ pages)"
    )
    emphasis: Optional[str] = Field(
        default="balanced",
        description="Content emphasis: 'skills', 'experience', 'balanced'"
    )
    exclude_sections: Optional[list[str]] = Field(
        default=None,
        description="Sections to exclude: ['education', 'certifications', 'projects']"
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


class TailorCVRequest(BaseModel):
    """Request to generate a tailored CV."""

    cv_id: str = Field(
        description="ID of the master CV to tailor"
    )
    job_description: str = Field(
        min_length=50,
        max_length=50000,
        description="Job description text (50-50,000 characters)"
    )
    job_id: Optional[str] = Field(
        default=None,
        description="Optional job ID for tracking"
    )
    gap_responses: Optional[GapAnalysisResponses] = Field(
        default=None,
        description="Optional gap analysis responses for additional context"
    )
    preferences: Optional[TailoringPreferences] = Field(
        default=None,
        description="Optional tailoring preferences"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "cv_id": "cv_abc123",
                "job_description": "We are seeking a Senior Python Developer...",
                "job_id": "job_xyz789",
                "gap_responses": {
                    "responses": [
                        {
                            "question_id": "q1",
                            "question_text": "Describe your experience with Python and Django",
                            "response_text": "I have 5 years of experience building REST APIs with Django...",
                            "skills_mentioned": ["Python", "Django", "REST APIs"]
                        }
                    ]
                },
                "preferences": {
                    "tone": "professional",
                    "length": "standard",
                    "emphasis": "skills"
                }
            }
        }
```

### Field Validation Rules

| Field | Required | Type | Constraints | Description |
|-------|----------|------|-------------|-------------|
| `cv_id` | ✅ Yes | string | Non-empty | Master CV identifier |
| `job_description` | ✅ Yes | string | 50-50,000 chars | Target job description |
| `job_id` | ❌ No | string | Optional | Job tracking ID |
| `gap_responses` | ❌ No | object | Optional | Gap analysis responses for context |
| `gap_responses.responses` | ❌ No | array | GapAnalysisResponse[] | Array of gap responses |
| `preferences` | ❌ No | object | Optional | Tailoring preferences |
| `preferences.tone` | ❌ No | enum | 'professional' \| 'casual' \| 'technical' | Tone of tailored CV |
| `preferences.length` | ❌ No | enum | 'compact' \| 'standard' \| 'detailed' | Target length |
| `preferences.emphasis` | ❌ No | enum | 'skills' \| 'experience' \| 'balanced' | Content emphasis |
| `preferences.exclude_sections` | ❌ No | array | String array | Sections to exclude |

---

## Response Model

### TailoredCVResponse (Pydantic)

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ContactInfo(BaseModel):
    """Contact information."""
    email: str
    phone: str
    location: Optional[str] = None
    linkedin: Optional[str] = None


class Experience(BaseModel):
    """Work experience entry."""
    company: str
    role: str
    dates: str
    description: str
    achievements: list[str]
    relevance_score: float = Field(ge=0.0, le=1.0)


class Education(BaseModel):
    """Education entry."""
    institution: str
    degree: str
    field: Optional[str] = None
    graduation_date: Optional[str] = None


class FVSValidationResult(BaseModel):
    """FVS validation result."""
    is_valid: bool
    violations: list[dict]
    has_critical_violations: bool


class TailoredCV(BaseModel):
    """Tailored CV optimized for specific job."""

    # Metadata
    cv_id: str
    job_id: Optional[str] = None
    tailored_at: str  # ISO 8601 timestamp

    # CV Content
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


class TailoredCVResponse(BaseModel):
    """Response for CV tailoring request."""

    success: bool
    tailored_cv: Optional[TailoredCV] = None
    fvs_validation: Optional[FVSValidationResult] = None
    error: Optional[str] = None
    code: str
    processing_time_ms: int = Field(
        description="Total processing time in milliseconds"
    )
    cost_estimate: float = Field(
        description="Estimated cost in USD for this operation"
    )
    download_url: Optional[str] = Field(
        default=None,
        description="Pre-signed S3 URL for downloading tailored CV (expires in 1 hour)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "tailored_cv": {
                    "cv_id": "cv_abc123",
                    "job_id": "job_xyz789",
                    "tailored_at": "2026-02-04T12:00:00Z",
                    "full_name": "John Doe",
                    "contact_info": {
                        "email": "john@example.com",
                        "phone": "+1234567890"
                    },
                    "professional_summary": "Senior Python Developer with 5+ years...",
                    "experience": [
                        {
                            "company": "FinTech Corp",
                            "role": "Python Developer",
                            "dates": "2020-2024",
                            "description": "Led development of REST APIs...",
                            "achievements": ["Improved API performance by 40%"],
                            "relevance_score": 0.95
                        }
                    ],
                    "skills": ["Python", "Django", "REST APIs"],
                    "education": [
                        {
                            "institution": "MIT",
                            "degree": "BS Computer Science",
                            "graduation_date": "2019"
                        }
                    ],
                    "changes_made": [
                        "Emphasized Python and Django experience",
                        "Reordered experience to prioritize FinTech background",
                        "Added ATS-friendly keywords: REST, API, Django"
                    ],
                    "relevance_scores": {
                        "experience[0]": 0.95,
                        "experience[1]": 0.78
                    },
                    "average_relevance_score": 0.87
                },
                "fvs_validation": {
                    "is_valid": True,
                    "violations": [],
                    "has_critical_violations": False
                },
                "code": "CV_TAILORED_SUCCESS",
                "processing_time_ms": 8432,
                "cost_estimate": 0.00575,
                "download_url": "https://s3.amazonaws.com/..."
            }
        }
```

### Response Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | True if tailoring succeeded, False otherwise |
| `tailored_cv` | object | Tailored CV object (null if failed) |
| `fvs_validation` | object | FVS validation result |
| `error` | string | Error message (null if success) |
| `code` | string | Result code (see Result Codes section) |
| `processing_time_ms` | integer | Total processing time in milliseconds |
| `cost_estimate` | float | Estimated cost in USD |
| `download_url` | string | Pre-signed S3 URL for download (expires in 1 hour) |

---

## Result Codes

### Success Codes

| Code | Description | HTTP Status | Response |
|------|-------------|-------------|----------|
| `CV_TAILORED_SUCCESS` | CV tailored successfully | 200 OK | TailoredCVResponse with tailored_cv |
| `CV_TAILORED_WITH_WARNINGS` | CV tailored but FVS warnings detected | 200 OK | TailoredCVResponse with fvs_validation.violations |

### Error Codes

| Code | Description | HTTP Status | Response |
|------|-------------|-------------|----------|
| `INVALID_INPUT` | Request validation failed | 400 Bad Request | Error message with details |
| `CV_NOT_FOUND` | Master CV not found for user | 404 Not Found | "CV with id {cv_id} not found" |
| `JOB_DESCRIPTION_TOO_SHORT` | Job description < 50 characters | 400 Bad Request | "Job description must be at least 50 characters" |
| `JOB_DESCRIPTION_TOO_LONG` | Job description > 50,000 characters | 400 Bad Request | "Job description exceeds 50,000 character limit" |
| `FVS_HALLUCINATION_DETECTED` | CRITICAL FVS violations detected | 400 Bad Request | FVS violations list in response |
| `LLM_TIMEOUT` | LLM call exceeded 300 second timeout | 504 Gateway Timeout | "CV tailoring timed out, please retry" |
| `LLM_RATE_LIMITED` | LLM service rate limited | 429 Too Many Requests | "Service temporarily unavailable, please retry in 60 seconds" |
| `LLM_PARSE_ERROR` | Failed to parse LLM response | 500 Internal Server Error | "Failed to parse LLM response" |
| `STORAGE_ERROR` | Failed to store tailored CV artifact | 500 Internal Server Error | "Failed to persist tailored CV" |
| `UNAUTHORIZED` | Missing or invalid authentication token | 401 Unauthorized | "Authentication required" |
| `FORBIDDEN` | User not authorized to access this CV | 403 Forbidden | "Access denied to CV {cv_id}" |
| `RATE_LIMIT_EXCEEDED` | User exceeded rate limit | 429 Too Many Requests | "Rate limit exceeded: 10 requests per minute" |

---

## Error Handling

### Error Response Format

All error responses follow this format:

```json
{
  "success": false,
  "tailored_cv": null,
  "error": "Detailed error message",
  "code": "ERROR_CODE",
  "processing_time_ms": 123,
  "cost_estimate": 0.0
}
```

### Error Handling Strategy

#### 1. Input Validation Errors (400 Bad Request)

**Scenario:** Invalid request body (missing cv_id, invalid job_description length)

**Response:**
```json
{
  "success": false,
  "error": "Validation error: job_description must be between 50 and 50000 characters",
  "code": "INVALID_INPUT",
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

#### 3. FVS Validation Failure (400 Bad Request)

**Scenario:** Tailored CV modified IMMUTABLE facts

**Response:**
```json
{
  "success": false,
  "error": "FVS validation failed: 2 critical violations detected",
  "code": "FVS_HALLUCINATION_DETECTED",
  "fvs_validation": {
    "is_valid": false,
    "has_critical_violations": true,
    "violations": [
      {
        "field": "work_history.company",
        "expected": "Google",
        "actual": "Alphabet",
        "severity": "CRITICAL"
      },
      {
        "field": "work_history.dates",
        "expected": "2020-2024",
        "actual": "2020-2025",
        "severity": "CRITICAL"
      }
    ]
  },
  "processing_time_ms": 9500
}
```

**Client Action:** Report bug to support (should not happen with correct prompt engineering)

---

#### 4. LLM Timeout (504 Gateway Timeout)

**Scenario:** LLM call exceeded 300 second timeout

**Response:**
```json
{
  "success": false,
  "error": "CV tailoring timed out after 300 seconds. Please try again.",
  "code": "LLM_TIMEOUT",
  "processing_time_ms": 300000
}
```

**Client Action:** Retry request

---

#### 5. Rate Limit Exceeded (429 Too Many Requests)

**Scenario:** User exceeded 10 requests per minute

**Response:**
```json
{
  "success": false,
  "error": "Rate limit exceeded: 10 requests per minute. Please wait 45 seconds.",
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
curl -X POST https://api.careervp.com/api/cv-tailoring \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "cv_id": "cv_abc123",
    "job_description": "We are seeking a Senior Python Developer..."
  }'
```

### Authorization

**Rule:** Users can only tailor their own CVs

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
| **Free Tier** | 10 | 50 | 200 |
| **Premium** | 30 | 200 | 1000 |
| **Enterprise** | 100 | 1000 | Unlimited |

### Rate Limit Headers

All responses include rate limit headers:

```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1633072800
```

### Rate Limit Exceeded Response

**HTTP Status:** 429 Too Many Requests

**Response:**
```json
{
  "success": false,
  "error": "Rate limit exceeded: 10 requests per minute. Please wait 45 seconds.",
  "code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 45
}
```

**Headers:**
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1633072845
Retry-After: 45
```

---

## OpenAPI Schema

### OpenAPI 3.0 Specification

```yaml
openapi: 3.0.0
info:
  title: CareerVP CV Tailoring API
  version: 1.0.0
  description: API for generating tailored CVs optimized for specific job descriptions

servers:
  - url: https://api.careervp.com
    description: Production server
  - url: https://staging-api.careervp.com
    description: Staging server

paths:
  /api/cv-tailoring:
    post:
      summary: Generate tailored CV
      description: Generate a tailored CV optimized for a specific job description
      operationId: tailorCV
      tags:
        - CV Tailoring
      security:
        - CognitoJWT: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TailorCVRequest'
      responses:
        '200':
          description: CV tailored successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TailoredCVResponse'
        '400':
          description: Bad request (invalid input or FVS validation failure)
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
          description: Forbidden (user not authorized to access CV)
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '404':
          description: CV not found
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
    TailorCVRequest:
      type: object
      required:
        - cv_id
        - job_description
      properties:
        cv_id:
          type: string
          description: ID of the master CV to tailor
        job_description:
          type: string
          minLength: 50
          maxLength: 50000
          description: Job description text
        job_id:
          type: string
          description: Optional job ID for tracking
        gap_responses:
          $ref: '#/components/schemas/GapAnalysisResponses'
        preferences:
          $ref: '#/components/schemas/TailoringPreferences'

    GapAnalysisResponses:
      type: object
      properties:
        responses:
          type: array
          items:
            $ref: '#/components/schemas/GapAnalysisResponse'

    GapAnalysisResponse:
      type: object
      required:
        - question_id
        - question_text
        - response_text
        - skills_mentioned
      properties:
        question_id:
          type: string
        question_text:
          type: string
        response_text:
          type: string
        skills_mentioned:
          type: array
          items:
            type: string

    TailoringPreferences:
      type: object
      properties:
        tone:
          type: string
          enum: [professional, casual, technical]
          default: professional
        length:
          type: string
          enum: [compact, standard, detailed]
          default: standard
        emphasis:
          type: string
          enum: [skills, experience, balanced]
          default: balanced
        exclude_sections:
          type: array
          items:
            type: string

    TailoredCVResponse:
      type: object
      required:
        - success
        - code
        - processing_time_ms
      properties:
        success:
          type: boolean
        tailored_cv:
          $ref: '#/components/schemas/TailoredCV'
        fvs_validation:
          $ref: '#/components/schemas/FVSValidationResult'
        error:
          type: string
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

    TailoredCV:
      type: object
      required:
        - cv_id
        - tailored_at
        - full_name
        - contact_info
        - professional_summary
        - experience
        - skills
        - education
      properties:
        cv_id:
          type: string
        job_id:
          type: string
        tailored_at:
          type: string
          format: date-time
        full_name:
          type: string
        contact_info:
          $ref: '#/components/schemas/ContactInfo'
        professional_summary:
          type: string
        experience:
          type: array
          items:
            $ref: '#/components/schemas/Experience'
        skills:
          type: array
          items:
            type: string
        education:
          type: array
          items:
            $ref: '#/components/schemas/Education'
        changes_made:
          type: array
          items:
            type: string
        relevance_scores:
          type: object
          additionalProperties:
            type: number
        average_relevance_score:
          type: number
          minimum: 0.0
          maximum: 1.0

    ContactInfo:
      type: object
      required:
        - email
        - phone
      properties:
        email:
          type: string
          format: email
        phone:
          type: string
        location:
          type: string
        linkedin:
          type: string
          format: uri

    Experience:
      type: object
      required:
        - company
        - role
        - dates
        - description
        - relevance_score
      properties:
        company:
          type: string
        role:
          type: string
        dates:
          type: string
        description:
          type: string
        achievements:
          type: array
          items:
            type: string
        relevance_score:
          type: number
          minimum: 0.0
          maximum: 1.0

    Education:
      type: object
      required:
        - institution
        - degree
      properties:
        institution:
          type: string
        degree:
          type: string
        field:
          type: string
        graduation_date:
          type: string

    FVSValidationResult:
      type: object
      required:
        - is_valid
        - violations
        - has_critical_violations
      properties:
        is_valid:
          type: boolean
        violations:
          type: array
          items:
            type: object
        has_critical_violations:
          type: boolean

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

### Example 1: Successful CV Tailoring

**Request:**
```bash
POST /api/cv-tailoring HTTP/1.1
Host: api.careervp.com
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "cv_id": "cv_abc123",
  "job_description": "We are seeking a Senior Python Developer with 5+ years of experience in backend development. Must have expertise in Django, REST APIs, and PostgreSQL. Experience with Docker and Kubernetes is a plus. The ideal candidate will lead the development of scalable microservices for our FinTech platform.",
  "job_id": "job_xyz789",
  "preferences": {
    "tone": "professional",
    "length": "standard",
    "emphasis": "skills"
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "tailored_cv": {
    "cv_id": "cv_abc123",
    "job_id": "job_xyz789",
    "tailored_at": "2026-02-04T12:00:00Z",
    "full_name": "John Doe",
    "contact_info": {
      "email": "john.doe@example.com",
      "phone": "+1-555-123-4567",
      "location": "San Francisco, CA",
      "linkedin": "https://linkedin.com/in/johndoe"
    },
    "professional_summary": "Senior Python Developer with 6+ years of experience building scalable backend systems and REST APIs. Expertise in Django, PostgreSQL, and microservices architecture. Proven track record of leading development teams in FinTech environments, delivering high-performance solutions that process millions of transactions daily.",
    "experience": [
      {
        "company": "FinTech Innovations",
        "role": "Senior Python Developer",
        "dates": "2020-2024",
        "description": "Led development of microservices-based payment processing platform using Django and PostgreSQL. Architected REST APIs serving 2M+ daily requests with 99.99% uptime. Mentored team of 5 engineers in Python best practices and TDD methodologies.",
        "achievements": [
          "Reduced API latency by 60% through database query optimization and caching strategies",
          "Implemented CI/CD pipeline with Docker and Kubernetes, reducing deployment time from 2 hours to 15 minutes",
          "Designed event-driven architecture using RabbitMQ, improving system scalability by 300%"
        ],
        "relevance_score": 0.95
      },
      {
        "company": "Tech Startup Inc",
        "role": "Backend Engineer",
        "dates": "2018-2020",
        "description": "Developed RESTful APIs and backend services using Python, Django, and PostgreSQL. Collaborated with frontend team to integrate APIs with React SPA. Implemented automated testing suite achieving 90% code coverage.",
        "achievements": [
          "Built user authentication system supporting OAuth2 and JWT tokens",
          "Optimized database queries reducing load times by 40%"
        ],
        "relevance_score": 0.78
      }
    ],
    "skills": [
      "Python",
      "Django",
      "REST APIs",
      "PostgreSQL",
      "Docker",
      "Kubernetes",
      "Microservices",
      "AWS",
      "Redis",
      "RabbitMQ",
      "Git",
      "CI/CD",
      "TDD"
    ],
    "education": [
      {
        "institution": "Massachusetts Institute of Technology",
        "degree": "BS Computer Science",
        "graduation_date": "2018"
      }
    ],
    "changes_made": [
      "Emphasized Python, Django, and REST API expertise in professional summary",
      "Reordered experience to prioritize FinTech background (6 years total experience)",
      "Highlighted Docker and Kubernetes experience in achievements",
      "Added ATS-friendly keywords: microservices, scalable, backend, PostgreSQL",
      "De-emphasized early internship experience (not relevant to Senior position)",
      "Reordered skills list to prioritize job requirements (Python, Django, REST APIs first)"
    ],
    "relevance_scores": {
      "experience[0]": 0.95,
      "experience[1]": 0.78,
      "skills.Python": 1.00,
      "skills.Django": 1.00,
      "skills.Docker": 0.90
    },
    "average_relevance_score": 0.87
  },
  "fvs_validation": {
    "is_valid": true,
    "violations": [],
    "has_critical_violations": false
  },
  "code": "CV_TAILORED_SUCCESS",
  "processing_time_ms": 8432,
  "cost_estimate": 0.00575,
  "download_url": "https://s3.amazonaws.com/careervp-artifacts/tailored-cvs/cv_abc123_job_xyz789_v1.pdf?X-Amz-Expires=3600&..."
}
```

---

### Example 2: FVS Validation Failure

**Request:**
```bash
POST /api/cv-tailoring HTTP/1.1
Host: api.careervp.com
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "cv_id": "cv_abc123",
  "job_description": "We are seeking a JavaScript Developer with React experience..."
}
```

**Response (400 Bad Request):**
```json
{
  "success": false,
  "tailored_cv": null,
  "error": "FVS validation failed: 2 critical violations detected. IMMUTABLE facts were modified.",
  "code": "FVS_HALLUCINATION_DETECTED",
  "fvs_validation": {
    "is_valid": false,
    "has_critical_violations": true,
    "violations": [
      {
        "field": "work_history.FinTech Innovations.dates",
        "expected": "2020-2024",
        "actual": "2020-2025",
        "severity": "CRITICAL"
      },
      {
        "field": "work_history.FinTech Innovations.role",
        "expected": "Senior Python Developer",
        "actual": "Senior Full-Stack Developer",
        "severity": "CRITICAL"
      }
    ]
  },
  "processing_time_ms": 9234,
  "cost_estimate": 0.00575
}
```

---

### Example 3: Rate Limit Exceeded

**Request:**
```bash
POST /api/cv-tailoring HTTP/1.1
Host: api.careervp.com
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "cv_id": "cv_abc123",
  "job_description": "..."
}
```

**Response (429 Too Many Requests):**
```json
{
  "success": false,
  "error": "Rate limit exceeded: 10 requests per minute. Please wait 45 seconds.",
  "code": "RATE_LIMIT_EXCEEDED",
  "processing_time_ms": 5,
  "retry_after": 45
}
```

**Headers:**
```
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1633072845
Retry-After: 45
```

---

### Example 4: CV Not Found

**Request:**
```bash
POST /api/cv-tailoring HTTP/1.1
Host: api.careervp.com
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "cv_id": "cv_nonexistent",
  "job_description": "..."
}
```

**Response (404 Not Found):**
```json
{
  "success": false,
  "error": "CV with id 'cv_nonexistent' not found for user",
  "code": "CV_NOT_FOUND",
  "processing_time_ms": 120
}
```

---

### Example 5: Invalid Input

**Request:**
```bash
POST /api/cv-tailoring HTTP/1.1
Host: api.careervp.com
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "cv_id": "cv_abc123",
  "job_description": "Too short"
}
```

**Response (400 Bad Request):**
```json
{
  "success": false,
  "error": "Validation error: job_description must be at least 50 characters (got 9)",
  "code": "INVALID_INPUT",
  "processing_time_ms": 5
}
```

---

## Appendices

### A. HTTP Status Code Summary

| Status Code | Meaning | When to Return |
|-------------|---------|----------------|
| 200 OK | Success | CV tailored successfully |
| 400 Bad Request | Client error | Invalid input, FVS validation failure |
| 401 Unauthorized | Authentication required | Missing or invalid JWT |
| 403 Forbidden | Authorization denied | User doesn't own CV |
| 404 Not Found | Resource not found | CV doesn't exist |
| 429 Too Many Requests | Rate limit exceeded | User exceeded quota |
| 500 Internal Server Error | Server error | Unexpected error |
| 504 Gateway Timeout | Timeout | LLM call exceeded 300s |

### B. Result Code to HTTP Status Mapping

```python
RESULT_CODE_TO_HTTP_STATUS = {
    "CV_TAILORED_SUCCESS": 200,
    "CV_TAILORED_WITH_WARNINGS": 200,
    "INVALID_INPUT": 400,
    "JOB_DESCRIPTION_TOO_SHORT": 400,
    "JOB_DESCRIPTION_TOO_LONG": 400,
    "FVS_HALLUCINATION_DETECTED": 400,
    "CV_NOT_FOUND": 404,
    "LLM_TIMEOUT": 504,
    "LLM_RATE_LIMITED": 429,
    "LLM_PARSE_ERROR": 500,
    "STORAGE_ERROR": 500,
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "RATE_LIMIT_EXCEEDED": 429,
}
```

### C. Content-Type Support

| Content-Type | Supported | Notes |
|-------------|-----------|-------|
| `application/json` | ✅ Yes | Primary format |
| `application/x-www-form-urlencoded` | ❌ No | Use JSON |
| `multipart/form-data` | ❌ No | Use JSON |

---

**Document Version:** 1.0
**Last Updated:** 2026-02-04
**Next Review:** After Phase 9 implementation complete
