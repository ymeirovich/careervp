# CareerVP Refactoring Plan - Critical Corrections & Additions

**Document Version:** 1.1
**Date:** 2026-02-10
**Status:** MAJOR UPDATES REQUIRED

---

## Table of Contents

1. [JSA Architecture Prompts - Complete Incorporation](#1-jsa-architecture-prompts---complete-incorporation)
2. [API Contract](#2-api-contract)
3. [Corrected Feature Workflow](#3-corrected-feature-workflow)
4. [End-of-Phase Live Tests](#4-end-of-phase-live-tests)
5. [Bedrock vs Direct Anthropic API](#5-bedrock-vs-direct-anthropic-api)
6. [CV Tailoring Gate Remediation - 10 Payloads](#6-cv-tailoring-gate-remediation---10-payloads)
7. [Task Alignment with Existing Tasks](#7-task-alignment-with-existing-tasks)

---

## 1. JSA Architecture Prompts - Complete Incorporation

### 1.1 Prompt Inventory from JSA Architecture

| Feature | Prompt File | Status in Refactoring Plan |
|---------|-------------|---------------------------|
| **VPR Generator** | `vpr_prompt.py` | ✅ Included |
| **Gap Analysis** | `gap_analysis_prompt.py` | ✅ Included |
| **CV Tailoring** | `cv_tailoring_prompt.py` | ✅ Included |
| **Cover Letter** | `cover_letter_prompt.py` | ✅ Included |
| **Interview Prep** | `interview_prep_prompt.py` | ❌ MISSING |
| **Company Research** | `company_research_prompt.py` | ❌ MISSING |
| **Knowledge Base** | `knowledge_base_prompt.py` | ❌ MISSING |
| **FVS Validator** | `fvs_prompt.py` | ❌ MISSING |

### 1.2 JSA Prompt Structure (from /docs/tasks/05-jsa-skill-alignment.md)

**VPR Prompt - 6 Stages:**
```
STAGE 1: Company & Role Research
├── Strategic priorities extraction
├── Competitor analysis
└── Success profile identification

STAGE 2: Candidate Analysis
├── Career narrative construction
├── Differentiators identification
└── Achievement quantification

STAGE 3: Alignment Mapping
├── Explicit table creation
├── Gap identification
└── Evidence mapping

STAGE 4: Self-Correction
├── Meta-review questions
├── Unsupported claims check
└── Logic consistency verification

STAGE 5: Report Generation
├── UVP statement
├── Proof points
└── Strategic narrative

STAGE 6: Meta Evaluation
├── "20% more persuasive" improvement
└── Final quality check
```

**CV Tailoring Prompt - 3 Steps:**
```
STEP 1: Analysis & Keyword Mapping
├── 12-18 keyword extraction
├── ATS compatibility check
└── Company-specific customization

STEP 2: Self-Correction & Verification
├── ATS score (1-10)
├── Hiring manager perspective
└── Claim verification

STEP 3: Final Output
├── ATS score >= 8
├── CAR/STAR format bullets
└── Integration with VPR differentiators
```

**Cover Letter Prompt - 3 Paragraphs:**
```
PARAGRAPH 1: Hook (80-100 words)
├── Unique Value Proposition (UVP)
├── Company-specific reference
└── Personal connection

PARAGRAPH 2: Proof Points (variable)
├── 3 requirements mapped
├── Claim + Proof format
└── Quantified evidence

PARAGRAPH 3: Close (60-80 words)
├── Time-saver positioning
├── Call to action
└── Professional sign-off
```

### 1.3 Prompt Update Strategy

```python
# src/backend/careervp/logic/prompts/prompt_registry.py

class JSA PromptRegistry:
    """
    Central registry for all JSA prompts with versioning.

    All prompts must:
    1. Be versioned (YYYY-MM-v1)
    2. Include anti-AI detection rules
    3. Include FVS validation markers
    4. Support dynamic parameter injection
    """

    PROMPTS = {
        "vpr-generator": {
            "current_version": "2026-02-v1",
            "file": "prompts/vpr_prompt.py",
            "stages": 6,
            "parameters": [
                "cv_facts",
                "gap_responses",
                "job_requirements",
                "company_research",
            ],
            "anti_ai_rules": True,
            "fvs_markers": True,
        },
        "cv-tailoring": {
            "current_version": "2026-02-v1",
            "file": "prompts/cv_tailoring_prompt.py",
            "steps": 3,
            "parameters": [
                "user_cv",
                "job_requirements",
                "vpr_differentiators",
                "company_keywords",
            ],
            "ats_minimum_score": 8,
        },
        "cover-letter": {
            "current_version": "2026-02-v1",
            "file": "prompts/cover_letter_prompt.py",
            "paragraphs": 3,
            "parameters": [
                "user_cv",
                "vpr_response",
                "gap_responses",
                "company_research",
            ],
        },
        "gap-analysis": {
            "current_version": "2026-02-v1",
            "file": "prompts/gap_analysis_prompt.py",
            "parameters": [
                "cv_facts",
                "job_requirements",
                "previous_questions",
            ],
            "max_questions": 10,
        },
        # MISSING - ADD THESE
        "interview-prep": {
            "current_version": "2026-02-v1",
            "file": "prompts/interview_prep_prompt.py",
            "parameters": [
                "vpr_response",
                "gap_responses",
                "job_requirements",
            ],
            "formats": ["STAR", "CAR", "XYZ"],
        },
        "company-research": {
            "current_version": "2026-02-v1",
            "file": "prompts/company_research_prompt.py",
            "parameters": [
                "job_url",
                "company_name",
            ],
            "outputs": [
                "mission",
                "values",
                "recent_news",
                "culture",
                "products",
            ],
        },
        "fvs-validator": {
            "current_version": "2026-02-v1",
            "file": "prompts/fvs_prompt.py",
            "checks": [
                "fact_verification",
                "quantification",
                "source_attribution",
            ],
        },
    }
```

---

## 2. API Contract

### 2.1 API Structure Overview

```
API Base URL: https://api.careervp.com/v1

/endpoints
├── /auth
│   ├── POST /auth/register
│   ├── POST /auth/login
│   └── POST /auth/refresh
│
├── /users
│   ├── GET /users/me
│   ├── PUT /users/me
│   ├── POST /users/me/cv
│   └── GET /users/me/cvs
│
├── /jobs
│   ├── POST /jobs
│   ├── GET /jobs/{id}
│   └── GET /users/me/jobs
│
├── /vpr
│   ├── POST /vpr/generate
│   ├── GET /vpr/{id}
│   └── GET /users/me/vprs
│
├── /gap-analysis
│   ├── POST /gap-analysis/questions
│   ├── POST /gap-analysis/responses
│   └── GET /gap-analysis/{job_id}/questions
│
├── /cv-tailoring
│   ├── POST /cv-tailoring/generate
│   ├── GET /cv-tailoring/{id}
│   └── GET /users/me/tailored-cvs
│
├── /cover-letter
│   ├── POST /cover-letter/generate
│   ├── GET /cover-letter/{id}
│   └── GET /users/me/cover-letters
│
├── /interview-prep
│   ├── POST /interview-prep/generate
│   ├── GET /interview-prep/{id}
│   └── GET /users/me/interview-preps
│
└── /company-research
    ├── POST /company-research/fetch
    └── GET /company-research/{job_id}
```

### 2.2 API Contract - VPR Generator

**POST /vpr/generate**

**Request:**
```json
{
  "cv_id": "cv_12345",
  "job_id": "job_67890",
  "gap_response_ids": ["gap_001", "gap_002", "gap_003"],
  "options": {
    "include_company_research": true,
    "tone": "professional",
    "length": "standard"
  }
}
```

**Response (202 Accepted):**
```json
{
  "request_id": "req_abc123",
  "status": "processing",
  "estimated_time_seconds": 30,
  "webhook_url": "https://api.careervp.com/v1/webhooks/vpr"
}
```

**GET /vpr/{id} (Polling):**
```json
{
  "id": "vpr_xyz789",
  "status": "completed",
  "result": {
    "uvp": "Experienced software engineer...",
    "differentiators": [
      {"text": "40% productivity increase", "source": "cv"},
      {"text": "Led 8-person team", "source": "gap_response"}
    ],
    "strategic_narrative": "...",
    "company_job_fit_score": 0.85,
    "meta_evaluation": {
      "persuasion_score": 8.5,
      "completeness_score": 9.0
    }
  },
  "created_at": "2026-02-10T10:30:00Z",
  "completed_at": "2026-02-10T10:30:45Z"
}
```

### 2.3 API Contract - Gap Analysis

**POST /gap-analysis/questions**

**Request:**
```json
{
  "cv_id": "cv_12345",
  "job_id": "job_67890",
  "max_questions": 10,
  "focus_areas": ["technical", "leadership"]
}
```

**Response:**
```json
{
  "questions": [
    {
      "id": "gap_q_001",
      "text": "Describe a time you led a team through a significant challenge.",
      "tags": ["leadership", "INTERVIEW/MVP ONLY"],
      "strategic_intent": "Assess leadership capability",
      "evidence_gap": "No leadership experience in CV"
    },
    {
      "id": "gap_q_002",
      "text": "How have you used Python to solve complex problems?",
      "tags": ["technical", "CV IMPACT"],
      "strategic_intent": "Verify technical depth",
      "evidence_gap": "Limited Python projects shown"
    }
  ],
  "missing_qualifications": [
    "Kubernetes experience",
    "AWS certification"
  ]
}
```

**POST /gap-analysis/responses**

**Request:**
```json
{
  "responses": [
    {
      "question_id": "gap_q_001",
      "response": "I led a team of 5 engineers to migrate...",
      "quantifiable_data": {
        "team_size": 5,
        "duration_months": 8,
        "success_rate": 95
      }
    }
  ]
}
```

**Response:**
```json
{
  "status": "saved",
  "impact_statements": [
    {
      "text": "Led 5-person team through 8-month migration, 95% success rate",
      "evidence_type": "CV_IMPACT",
      "usable_in": ["cover_letter", "vpr"]
    }
  ]
}
```

### 2.4 API Contract - CV Tailoring

**POST /cv-tailoring/generate**

**Request:**
```json
{
  "cv_id": "cv_12345",
  "job_id": "job_67890",
  "vpr_id": "vpr_xyz789",
  "options": {
    "preserve_length": true,
    "highlight_keywords": true,
    "target_ats": "standard"
  }
}
```

**Response (202 Accepted):**
```json
{
  "request_id": "req_cv001",
  "status": "processing",
  "estimated_time_seconds": 20
}
```

**GET /cv-tailoring/{id}:**
```json
{
  "id": "tailored_cv_001",
  "status": "completed",
  "result": {
    "tailored_cv": "...",
    "ats_score": 8.5,
    "keyword_matches": {
      "matched": ["Python", "AWS", "Kubernetes"],
      "missing": ["Terraform", "GCP"]
    },
    "suggestions": [
      "Add Terraform experience section",
      "Highlight GCP personal projects"
    ]
  }
}
```

### 2.5 API Contract - Cover Letter

**POST /cover-letter/generate**

**Request:**
```json
{
  "cv_id": "cv_12345",
  "job_id": "job_67890",
  "vpr_id": "vpr_xyz789",
  "gap_response_ids": ["gap_001"],
  "company_research_id": "comp_res_001",
  "options": {
    "tone": "professional",
    "length": "standard",
    "include_portfolio_link": true
  }
}
```

**Response:**
```json
{
  "id": "cover_letter_001",
  "status": "completed",
  "result": {
    "cover_letter": "Dear Hiring Manager,\n\nI am writing to express my interest...",
    "paragraphs": {
      "hook": {
        "word_count": 95,
        "includes_uvp": true,
        "includes_company_reference": true
      },
      "proof_points": {
        "requirements_matched": 3,
        "claims_verified": true,
        "quantified_evidence": true
      },
      "close": {
        "word_count": 72,
        "includes_cta": true
      }
    },
    "fvs_validation": {
      "is_valid": true,
      "violations": []
    }
  }
}
```

### 2.6 Standard Error Responses

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "cv_id",
        "message": "cv_id is required"
      }
    ]
  }
}
```

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Daily limit reached",
    "retry_after_seconds": 3600
  }
}
```

---

## 3. Corrected Feature Workflow

### 3.1 User Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   CAREERVP USER WORKFLOW (CORRECTED)                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  STEP 1: UPLOAD CV                                                    │
│  ┌─────────────┐     ┌─────────────┐                                   │
│  │ User        │────▶│  CV        │                                   │
│  │ uploads CV  │     │  Stored     │                                   │
│  └─────────────┘     └─────────────┘                                   │
│                                                                         │
│  STEP 2: ENTER JOB DESCRIPTION                                         │
│  ┌─────────────┐     ┌─────────────┐                                   │
│  │ User        │────▶│  Job       │                                   │
│  │ pastes JD   │     │  Parsed     │                                   │
│  └─────────────┘     └─────────────┘                                   │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  STEP 3: GAP ANALYSIS ⬅ REQUIRED BEFORE VPR                    │    │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │    │
│  │  │ Generate    │───▶│  User       │───▶│  Impact     │        │    │
│  │  │ Questions  │    │  Answers    │    │  Statements │        │    │
│  │  └─────────────┘    └─────────────┘    │  Stored     │        │    │
│  │                                          └─────────────┘        │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  STEP 4: VPR GENERATOR ⬅ REQUIRES GAP RESPONSES              │    │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │    │
│  │  │ Generate    │───▶│  VPR        │───▶│  UVP +      │        │    │
│  │  │ VPR         │    │  Created    │    │  Differentiators│     │    │
│  │  └─────────────┘    └─────────────┘    └─────────────┘        │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  STEP 5: CV TAILORING ⬅ REQUIRES VPR                        │    │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │    │
│  │  │ Generate    │───▶│  Tailored   │───▶│  ATS Score  │        │    │
│  │  │ Tailored CV │    │  CV         │    │  >= 8       │        │    │
│  │  └─────────────┘    └─────────────┘    └─────────────┘        │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  STEP 6: COVER LETTER ⬅ REQUIRES VPR + GAP RESPONSES        │    │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │    │
│  │  │ Generate    │───▶│  Cover      │───▶│  FVS        │        │    │
│  │  │ Letter      │    │  Letter     │    │  Validated  │        │    │
│  │  └─────────────┘    └─────────────┘    └─────────────┘        │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  STEP 7: INTERVIEW PREP ⬅ OPTIONAL                           │    │
│  │  ┌─────────────┐    ┌─────────────┐                           │    │
│  │  │ Generate    │───▶│  STAR      │                           │    │
│  │  │ Questions   │    │  Responses  │                           │    │
│  │  └─────────────┘    └─────────────┘                           │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Data Dependencies Matrix

| Feature | Requires | Optional |
|---------|----------|----------|
| **Gap Analysis** | CV, Job Description | Previous gap questions |
| **VPR Generator** | CV, Gap Responses | Company Research |
| **CV Tailoring** | CV, VPR | Company Keywords |
| **Cover Letter** | VPR, Gap Responses | Company Research |
| **Interview Prep** | VPR, Gap Responses | - |

### 3.3 Workflow Enforcement Code

```python
# src/backend/careervp/handlers/workflow_enforcer.py

class WorkflowEnforcer:
    """
    Enforce correct workflow order.

    RULES:
    1. Gap Analysis must complete BEFORE VPR
    2. VPR must complete BEFORE CV Tailoring
    3. VPR + Gap must complete BEFORE Cover Letter
    """

    DEPENDENCIES = {
        "vpr_generator": {
            "required": ["gap_analysis"],
            "status_field": "gap_analysis_complete",
        },
        "cv_tailoring": {
            "required": ["vpr_generator"],
            "status_field": "vpr_complete",
        },
        "cover_letter": {
            "required": ["vpr_generator", "gap_analysis"],
            "status_field": "prerequisites_complete",
        },
        "interview_prep": {
            "required": ["vpr_generator", "gap_analysis"],
            "status_field": "prerequisites_complete",
        },
    }

    async def validate_workflow_step(
        self,
        user_id: str,
        feature: str,
        context: dict,
    ) -> WorkflowValidationResult:
        """Validate that prerequisites are met."""
        if feature not in self.DEPENDENCIES:
            return WorkflowValidationResult(valid=True)

        required = self.DEPENDENCIES[feature]["required"]
        status_field = self.DEPENDENCIES[feature]["status_field"]

        # Check each required feature
        missing = []
        for req_feature in required:
            is_complete = await self._check_feature_complete(
                user_id=user_id,
                feature=req_feature,
                context=context,
            )
            if not is_complete:
                missing.append(req_feature)

        if missing:
            return WorkflowValidationResult(
                valid=False,
                error_code="PREREQUISITES_NOT_MET",
                message=f"Complete these features first: {', '.join(missing)}",
                missing_features=missing,
            )

        return WorkflowValidationResult(valid=True)
```

---

## 4. End-of-Phase Live Tests

### 4.1 Phase 0: Infrastructure Test

**Test: DynamoDB Knowledge Base**
```bash
# Payload
curl -X PUT https://api.careervp.com/v1/test/knowledge-base \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "pk": "TEST#test_user",
    "sk": "TEST#phase0_validation",
    "test_data": "phase0_validation",
    "timestamp": "2026-02-10T00:00:00Z"
  }'

# Expected: 200 OK, item retrievable
# Verify: GET returns same item
```

### 4.2 Phase 1: VPR Generator Live Test

**Payload:**
```json
{
  "cv_id": "cv_test_001",
  "job_id": "job_test_001",
  "gap_response_ids": ["gap_test_001"],
  "options": {
    "include_company_research": true,
    "tone": "professional"
  }
}
```

**Expected Response (202 Accepted):**
```json
{
  "request_id": "test_vpr_001",
  "status": "processing",
  "estimated_time_seconds": 30
}
```

**Validation Script:**
```bash
#!/bin/bash
# scripts/test_phase1_live.sh

export API_URL="https://api.careervp.com/v1"
export TOKEN=$(get_token)

# 1. Generate VPR
RESPONSE=$(curl -X POST "$API_URL/vpr/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @payloads/test_vpr_001.json)

REQUEST_ID=$(echo $RESPONSE | jq -r '.request_id')

# 2. Poll for completion
for i in {1..30}; do
  STATUS=$(curl -X GET "$API_URL/vpr/$REQUEST_ID" \
    -H "Authorization: Bearer $TOKEN" | jq -r '.status')

  if [ "$STATUS" == "completed" ]; then
    echo "SUCCESS: VPR generated"
    exit 0
  fi

  sleep 2
done

echo "TIMEOUT: VPR not completed in 60 seconds"
exit 1
```

### 4.3 Phase 2: Gap Analysis Live Test

**Payload:**
```json
{
  "cv_id": "cv_test_001",
  "job_id": "job_test_001",
  "max_questions": 10
}
```

**Expected Response:**
```json
{
  "questions": [
    {
      "id": "gap_test_q001",
      "text": "Describe your experience with cloud platforms...",
      "tags": ["technical", "CV IMPACT"],
      "strategic_intent": "Verify cloud expertise",
      "evidence_gap": "Limited cloud experience in CV"
    }
  ],
  "missing_qualifications": ["AWS", "GCP", "Azure"]
}
```

### 4.4 Phase 3: CV Tailoring Live Test

**Payload:**
```json
{
  "cv_id": "cv_test_001",
  "job_id": "job_test_001",
  "vpr_id": "vpr_test_001",
  "options": {
    "preserve_length": true,
    "highlight_keywords": true,
    "target_ats": "standard"
  }
}
```

**Expected Response:**
```json
{
  "id": "tailored_cv_test_001",
  "status": "completed",
  "result": {
    "ats_score": 8.5,
    "keyword_matches": {
      "matched": ["Python", "AWS", "Leadership"],
      "missing": ["Kubernetes"]
    }
  }
}
```

### 4.5 Phase 4: Cover Letter Live Test

**Payload:**
```json
{
  "cv_id": "cv_test_001",
  "job_id": "job_test_001",
  "vpr_id": "vpr_test_001",
  "gap_response_ids": ["gap_test_001"],
  "company_research_id": "comp_res_test_001",
  "options": {
    "tone": "professional",
    "length": "standard"
  }
}
```

**Expected Response:**
```json
{
  "id": "cover_letter_test_001",
  "status": "completed",
  "result": {
    "paragraphs": {
      "hook": {"word_count": 95, "includes_uvp": true},
      "proof_points": {"requirements_matched": 3, "claims_verified": true},
      "close": {"word_count": 72, "includes_cta": true}
    },
    "fvs_validation": {"is_valid": true, "violations": []}
  }
}
```

---

## 5. Bedrock vs Direct Anthropic API

### 5.1 Current State Analysis

**FOUND:** `src/backend/careervp/logic/llm_client.py` uses:
```python
bedrock_client = boto3.client('bedrock-runtime')
response = self._client.invoke_model(
    modelId='claude-haiku-4-5-20251001',
)
```

**ISSUE:** This uses AWS Bedrock runtime, which may incur Bedrock charges.

### 5.2 Decision: Direct Anthropic API

**Decision:** Use Direct Anthropic API to avoid Bedrock charges.

**Justification:**
1. No AWS Bedrock infrastructure needed
2. No Bedrock API charges
3. Direct API gives more control
4. Simpler infrastructure

### 5.3 New LLM Client Implementation

```python
# src/backend/careervp/infrastructure/llm_client.py

import os
import json
import httpx
from typing import Any, AsyncGenerator
from datetime import datetime


class AnthropicClient:
    """
    Direct Anthropic API client.

    Cost: ~$3.00/1M input tokens (Sonnet)
    No Bedrock charges.
    """

    BASE_URL = "https://api.anthropic.com/v1"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._client = httpx.AsyncClient(
            timeout=60.0,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
        )

    async def generate(
        self,
        model: str,  # "claude-sonnet-4-20250514", "claude-haiku-4-20250514"
        messages: list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: str = None,
    ) -> dict[str, Any]:
        """Generate text using Anthropic API."""
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if system_prompt:
            payload["system"] = system_prompt

        response = await self._client.post(
            f"{self.BASE_URL}/messages",
            json=payload,
        )
        response.raise_for_status()

        data = response.json()
        return {
            "content": data["content"][0]["text"],
            "usage": {
                "input_tokens": data["usage"]["input_tokens"],
                "output_tokens": data["usage"]["output_tokens"],
            },
            "model": model,
        }

    async def generate_streaming(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """Generate text with streaming response."""
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": True,
        }

        async with self._client.stream(
            "POST",
            f"{self.BASE_URL}/messages",
            json=payload,
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if data["type"] == "content_block_delta":
                        yield data["delta"]["text"]


class LLMRouter:
    """
    Route LLM requests to appropriate model.

    Models:
    - claude-sonnet-4-20250514: Strategic tasks (VPR, Gap Analysis)
    - claude-haiku-4-20250514: Template tasks (CV Tailoring, Cover Letter)
    """

    MODELS = {
        "strategic": "claude-sonnet-4-20250514",
        "template": "claude-haiku-4-20250514",
        "fast": "claude-haiku-4-20250514",
    }

    def __init__(self, client: AnthropicClient = None):
        self.client = client or AnthropicClient()

    async def generate_for_feature(
        self,
        feature: str,
        prompt: str,
        context: dict = None,
    ) -> dict[str, Any]:
        """Generate response based on feature type."""

        # Map feature to model type
        model_map = {
            "vpr_generator": "strategic",
            "gap_analysis": "strategic",
            "cv_tailoring": "template",
            "cover_letter": "template",
            "interview_prep": "strategic",
            "company_research": "fast",
            "fvs_validation": "strategic",
        }

        model_type = model_map.get(feature, "template")
        model = self.MODELS[model_type]

        # Build messages
        messages = [{"role": "user", "content": prompt}]

        return await self.client.generate(
            model=model,
            messages=messages,
            max_tokens=self._get_max_tokens(feature),
        )

    def _get_max_tokens(self, feature: str) -> int:
        """Get max tokens for feature."""
        tokens = {
            "vpr_generator": 4096,
            "gap_analysis": 2048,
            "cv_tailoring": 2048,
            "cover_letter": 2048,
            "interview_prep": 4096,
            "company_research": 1024,
            "fvs_validation": 2048,
        }
        return tokens.get(feature, 2048)
```

### 5.4 CDK Infrastructure - NO Bedrock

**Current CDK stacks do NOT include Bedrock:**
- `infra/careervp/` contains:
  - `api_construct.py` - API Gateway
  - `api_db_construct.py` - DynamoDB tables
  - `service_stack.py` - Lambda functions
  - `waf_construct.py` - WAF rules
  - `monitoring.py` - CloudWatch

**No Bedrock resources defined.**

**Action Required:** Keep it this way - no Bedrock infrastructure needed.

---

## 6. CV Tailoring Gate Remediation - 10 Payloads

### 6.1 Payload 1: Software Engineer with Matching Experience

```json
{
  "cv_id": "cv_gate_001",
  "job_id": "job_gate_001",
  "vpr_id": "vpr_gate_001",
  "options": {
    "preserve_length": true,
    "highlight_keywords": true,
    "target_ats": "standard"
  }
}
```

**Context:**
- CV: 5 years Python, AWS, Kubernetes
- Job: Python Developer, AWS required, Kubernetes nice-to-have
- VPR: Strong technical background, cloud expertise

**Expected:** ATS Score >= 9.0, all keywords matched

### 6.2 Payload 2: Career Changer - Non-Technical to Tech

```json
{
  "cv_id": "cv_gate_002",
  "job_id": "job_gate_002",
  "vpr_id": "vpr_gate_002",
  "options": {
    "preserve_length": false,
    "highlight_keywords": true,
    "target_ats": "standard"
  }
}
```

**Context:**
- CV: Teaching background, now 1 year coding
- Job: Junior Developer
- VPR: Highlight transferable skills, rapid learning

**Expected:** ATS Score >= 7.5, skills translated

### 6.3 Payload 3: Leadership Role - Management Position

```json
{
  "cv_id": "cv_gate_003",
  "job_id": "job_gate_003",
  "vpr_id": "vpr_gate_003",
  "options": {
    "preserve_length": false,
    "highlight_keywords": true,
    "target_ats": "standard"
  }
}
```

**Context:**
- CV: 10 years individual contributor
- Job: Engineering Manager
- VPR: Leadership potential, team motivation

**Expected:** ATS Score >= 8.0, management keywords emphasized

### 6.4 Payload 4: Senior with Skills Gap

```json
{
  "cv_id": "cv_gate_004",
  "job_id": "job_gate_004",
  "vpr_id": "vpr_gate_004",
  "options": {
    "preserve_length": true,
    "highlight_keywords": true,
    "target_ats": "standard"
  }
}
```

**Context:**
- CV: 15 years experience, no recent cloud
- Job: Cloud Architect
- VPR: Architecture experience, willingness to upskill

**Expected:** ATS Score >= 7.0, gaps acknowledged

### 6.5 Payload 5: Recent Graduate - Limited Experience

```json
{
  "cv_id": "cv_gate_005",
  "job_id": "job_gate_005",
  "vpr_id": "vpr_gate_005",
  "options": {
    "preserve_length": false,
    "highlight_keywords": true,
    "target_ats": "standard"
  }
}
```

**Context:**
- CV: New grad, internships only
- Job: Junior Developer
- VPR: Academic projects, internships, growth trajectory

**Expected:** ATS Score >= 7.5, education emphasized

### 6.6 Payload 6: Remote-First Company

```json
{
  "cv_id": "cv_gate_006",
  "job_id": "job_gate_006",
  "vpr_id": "vpr_gate_006",
  "options": {
    "preserve_length": true,
    "highlight_keywords": true,
    "target_ats": "standard"
  }
}
```

**Context:**
- CV: Traditional office worker
- Job: Remote DevOps Engineer
- VPR: Self-discipline, async communication

**Expected:** ATS Score >= 8.0, remote readiness highlighted

### 6.7 Payload 7: Startup vs Corporate Culture

```json
{
  "cv_id": "cv_gate_007",
  "job_id": "job_gate_007",
  "vpr_id": "vpr_gate_007",
  "options": {
    "preserve_length": true,
    "highlight_keywords": true,
    "target_ats": "standard"
  }
}
```

**Context:**
- CV: Corporate experience only
- Job: Startup Senior Engineer
- VPR: Adaptability, fast-paced, ownership

**Expected:** ATS Score >= 8.0, startup alignment

### 6.8 Payload 8: Industry Transition - Different Sector

```json
{
  "cv_id": "cv_gate_008",
  "job_id": "job_gate_008",
  "vpr_id": "vpr_gate_008",
  "options": {
    "preserve_length": true,
    "highlight_keywords": true,
    "target_ats": "standard"
  }
}
```

**Context:**
- CV: Healthcare IT background
- Job: Fintech Developer
- VPR: Domain knowledge transfer, compliance awareness

**Expected:** ATS Score >= 7.5, transferable domain expertise

### 6.9 Payload 9: Contract to Perm

```json
{
  "cv_id": "cv_gate_009",
  "job_id": "job_gate_009",
  "vpr_id": "vpr_gate_009",
  "options": {
    "preserve_length": true,
    "highlight_keywords": true,
    "target_ats": "standard"
  }
}
```

**Context:**
- CV: 5 years contractor
- Job: Perm Senior Developer
- VPR: Project completion, diverse teams, quick integration

**Expected:** ATS Score >= 8.0, perm readiness

### 6.10 Payload 10: Gap in Employment

```json
{
  "cv_id": "cv_gate_010",
  "job_id": "job_gate_010",
  "vpr_id": "vpr_gate_010",
  "options": {
    "preserve_length": true,
    "highlight_keywords": true,
    "target_ats": "standard"
  }
}
```

**Context:**
- CV: 6-month gap (personal reasons)
- Job: Developer
- VPR: Skills updated during gap, productivity maintained

**Expected:** ATS Score >= 7.0, gap addressed professionally

### 6.11 Gate Remediation Test Script

```python
# tests/phase3/test_cv_tailoring_gate.py

import pytest
from dataclasses import dataclass
from typing import List


@dataclass
class GateTestPayload:
    """Payload for gate remediation testing."""
    name: str
    payload: dict
    expected_min_ats: float
    required_keywords: List[str]


GATE_TEST_PAYLOADS = [
    GateTestPayload(
        name="matching_experience",
        payload={
            "cv_id": "cv_gate_001",
            "job_id": "job_gate_001",
            "vpr_id": "vpr_gate_001",
            "options": {"preserve_length": True, "highlight_keywords": True},
        },
        expected_min_ats=9.0,
        required_keywords=["Python", "AWS", "Kubernetes"],
    ),
    # ... 9 more payloads
]


class TestCVTailoringGateRemediation:
    """Gate remediation tests for CV Tailoring."""

    @pytest.mark.parametrize("test_payload", GATE_TEST_PAYLOADS)
    async def test_gate_payload_processes_successfully(self, test_payload: GateTestPayload):
        """Test that all gate payloads process successfully."""
        result = await cv_tailoring_handler.generate(
            **test_payload.payload
        )

        assert result.status == "completed"
        assert result.ats_score >= test_payload.expected_min_ats

    @pytest.mark.parametrize("test_payload", GATE_TEST_PAYLOADS)
    async def test_keywords_matched(self, test_payload: GateTestPayload):
        """Test required keywords are matched."""
        result = await cv_tailoring_handler.generate(
            **test_payload.payload
        )

        matched = result.keyword_matches["matched"]
        for keyword in test_payload.required_keywords:
            assert keyword in matched, f"Keyword {keyword} not matched"

    @pytest.mark.parametrize("test_payload", GATE_TEST_PAYLOADS)
    async def test_fvs_validation_passes(self, test_payload: GateTestPayload):
        """Test FVS validation passes for all payloads."""
        result = await cv_tailoring_handler.generate(
            **test_payload.payload
        )

        assert result.fvs_validation["is_valid"] is True
        assert len(result.fvs_validation["violations"]) == 0
```

---

## 7. Task Alignment with Existing Tasks

### 7.1 Task Directory Structure

```
docs/tasks/
├── 00-gap-remediation/     # Bug fixes, infrastructure
├── 00-infra/               # Infrastructure naming
├── 03-vpr-generator/       # VPR Generation (Phase 1)
├── 05-jsa-skill-alignment.md  # JSA alignment MASTER
├── 07-vpr-async/          # Async VPR workflow
├── 08-company-research/   # Company Research (MISSING in refactoring)
├── 09-cv-tailoring/       # CV Tailoring
├── 10-cover-letter/       # Cover Letter
├── 11-gap-analysis/       # Gap Analysis
├── 13-knowledge-base/     # Knowledge Base (MISSING)
├── cover-letter/          # Legacy
└── gap-analysis/          # Legacy
```

### 7.2 Task Alignment Matrix

| Refactoring Phase | Corresponding Task Directory | Alignment |
|-------------------|-----------------------------|-----------|
| Phase 0 | `00-infra/` | ✅ Aligns - naming conventions |
| Phase 1 | `03-vpr-generator/` | ✅ Aligns - VPR prompt structure |
| Phase 2 | `11-gap-analysis/` | ✅ Aligns - Gap analysis |
| Phase 3 | `09-cv-tailoring/` | ✅ Aligns - CV tailoring |
| Phase 4 | `10-cover-letter/` | ✅ Aligns - Cover letter |
| Phase 5 | `08-company-research/` | ⚠️ Ref plan missing |
| Phase 6 | NEW - Interview Prep | ❌ MISSING |
| Phase 7 | NEW - Integration | ✅ Partial - `07-vpr-async/` |
| Phase 8 | NEW - Knowledge Base | ❌ MISSING |

### 7.3 Required Additions to Refactoring Plan

**ADD to Phase 5: Company Research**
```markdown
### Task: Company Research Implementation
**Source:** `docs/tasks/08-company-research/`
**Files:**
- `task-01-models.md` → `src/backend/careervp/models/company_research.py`
- `task-04-research-logic.md` → `src/backend/careervp/logic/company_research_logic.py`
- `task-05-handler.md` → `src/backend/careervp/handlers/company_research_handler.py`
```

**ADD to Phase 6: Interview Prep**
```markdown
### Task: Interview Prep Implementation
**Source:** New feature (from JSA alignment)
**Files:**
- `src/backend/careervp/models/interview_prep.py`
- `src/backend/careervp/logic/interview_prep_logic.py`
- `src/backend/careervp/handlers/interview_prep_handler.py`
- `src/backend/careervp/logic/prompts/interview_prep_prompt.py`
```

**ADD to Phase 8: Knowledge Base**
```markdown
### Task: Knowledge Base Implementation
**Source:** `docs/specs/knowledge-base.md`
**Files:**
- `src/backend/careervp/dal/knowledge_base_dal.py`
- `src/backend/careervp/handlers/knowledge_base_handler.py`
```

### 7.4 Task Modification Rules

**RULE:** When existing task conflicts with refactoring plan:
1. **Code patterns from tasks TAKE PRECEDENT** over refactoring plan
2. **Naming conventions from CLAUDE.md TAKE PRECEDENT**
3. **SOLID principles from refactoring plan SUPERSEDE** existing code

**Example:**
```
Existing task: `docs/tasks/03-vpr-generator/task-04-sonnet-prompt.md`
├─ Use patterns from: VPR prompt structure
└─ Modify to align with: JSA 6-stage methodology
```

---

## Summary of Required Changes

| Item | Current Status | Required Change |
|------|---------------|-----------------|
| JSA Prompts | 4 of 8 implemented | Add Interview Prep, Company Research, Knowledge Base, FVS |
| API Contract | Partial | Publish complete contract above |
| Workflow | CV → VPR | Fix to: CV → Gap → VPR → CV/Cover |
| Live Tests | Missing | Add payloads for each phase |
| Bedrock | Used in code | Replace with direct Anthropic API |
| CDK | No Bedrock | Keep - no Bedrock needed |
| CV Tailoring Payloads | 0 | Add 10 payloads above |
| Tasks | Partial | Align with `docs/tasks/` structure |

---

**Document Version:** 1.1
**Last Updated:** 2026-02-10
**Next Review:** 2026-02-17

---

**END OF CRITICAL CORRECTIONS DOCUMENT**
