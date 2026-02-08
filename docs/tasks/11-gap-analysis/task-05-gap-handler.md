# Task 05: Gap Analysis Handler (Main Entry Point)

## Overview

Create Lambda handler for gap analysis endpoint (synchronous).

**Files to create:**
- `src/backend/careervp/handlers/gap_handler.py`
- `src/backend/careervp/models/gap_analysis.py` (request/response models)

**Dependencies:** Tasks 01, 03, 04, 06
**Estimated time:** 3 hours
**Tests:** `tests/gap-analysis/integration/test_gap_handler.py`

---

## Implementation

### File: `src/backend/careervp/models/gap_analysis.py`

```python
"""
Pydantic models for gap analysis API.
Per docs/specs/gap-analysis/GAP_SPEC.md.
"""

from typing import Annotated, Literal
from pydantic import BaseModel, Field

from careervp.models.job import JobPosting


class GapAnalysisRequest(BaseModel):
    """Request for gap analysis."""

    user_id: Annotated[str, Field(description="User identifier")]
    cv_id: Annotated[str, Field(description="CV identifier")]
    job_posting: Annotated[JobPosting, Field(description="Target job posting")]
    language: Annotated[Literal['en', 'he'], Field(default='en', description="Question language")]


class GapQuestion(BaseModel):
    """Individual gap analysis question."""

    question_id: Annotated[str, Field(description="Unique question identifier")]
    question: Annotated[str, Field(description="Question text")]
    impact: Annotated[Literal['HIGH', 'MEDIUM', 'LOW'], Field(description="Impact level")]
    probability: Annotated[Literal['HIGH', 'MEDIUM', 'LOW'], Field(description="Probability level")]
    gap_score: Annotated[float, Field(ge=0.0, le=1.0, description="Calculated priority score")]


class GapAnalysisResponse(BaseModel):
    """Response for gap analysis."""

    questions: Annotated[list[GapQuestion], Field(description="Generated questions (0-5)")]
    metadata: Annotated[dict, Field(description="Processing metadata")]
```

### File: `src/backend/careervp/handlers/gap_handler.py`

```python
"""
Gap analysis Lambda handler (synchronous).
Per docs/specs/gap-analysis/GAP_SPEC.md.

Endpoint: POST /api/gap-analysis
Pattern: Synchronous (like VPR), NOT async
"""

import json
import os
from datetime import datetime, timezone
from typing import Any

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.utilities.typing import LambdaContext

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.handlers.utils.validation import validate_text_length
from careervp.logic.gap_analysis import generate_gap_questions
from careervp.models import ResultCode
from careervp.models.gap_analysis import GapAnalysisRequest, GapAnalysisResponse
from pydantic import ValidationError

# AWS Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics()


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """
    Handle gap analysis requests (synchronous).

    POST /api/gap-analysis
    Returns: 200 OK with questions immediately

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response
    """
    try:
        # 1. Parse request
        body = json.loads(event.get('body', '{}'))

        # Extract user_id from JWT
        jwt_user_id = event['requestContext']['authorizer']['claims']['sub']

        # Validate user_id matches JWT
        if body.get('user_id') != jwt_user_id:
            return _error_response(403, "User ID mismatch", ResultCode.FORBIDDEN)

        # Validate request model
        try:
            request = GapAnalysisRequest(**body)
        except ValidationError as e:
            return _error_response(400, f"Validation error: {str(e)}", ResultCode.VALIDATION_ERROR)

        # Validate text length
        job_posting_text = json.dumps(request.job_posting.model_dump())
        try:
            validate_text_length(job_posting_text)
        except ValueError as e:
            return _error_response(413, str(e), ResultCode.PAYLOAD_TOO_LARGE)

        # 2. Retrieve user CV from DAL
        dal = DynamoDalHandler(table_name=os.environ['DYNAMODB_TABLE_NAME'])
        cv_result = dal.get_cv(user_id=request.user_id, cv_id=request.cv_id)

        if not cv_result.success:
            return _error_response(404, "CV not found", ResultCode.CV_NOT_FOUND)

        user_cv = cv_result.data

        # 3. Generate gap questions (async call)
        import asyncio
        questions_result = asyncio.run(
            generate_gap_questions(
                user_cv=user_cv,
                job_posting=request.job_posting,
                dal=dal,
                language=request.language
            )
        )

        if not questions_result.success:
            return _error_response(
                500,
                questions_result.error,
                questions_result.code
            )

        # 4. Build response
        response = GapAnalysisResponse(
            questions=questions_result.data,
            metadata={
                'questions_generated': len(questions_result.data),
                'language': request.language,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        )

        # 5. Log metrics
        metrics.add_metric(name="GapQuestionsGenerated", unit="Count", value=len(questions_result.data))

        return {
            'statusCode': 200,
            'headers': _cors_headers(),
            'body': response.model_dump_json()
        }

    except Exception as e:
        logger.exception("Unexpected error in gap analysis handler")
        return _error_response(500, f"Internal error: {str(e)}", ResultCode.INTERNAL_ERROR)


def _error_response(status_code: int, error: str, code: str) -> dict:
    """Build error response."""
    return {
        'statusCode': status_code,
        'headers': _cors_headers(),
        'body': json.dumps({'error': error, 'code': code})
    }


def _cors_headers() -> dict:
    """Return CORS headers."""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Content-Type': 'application/json'
    }
```

---

## Verification Commands

```bash
cd src/backend

# Format
uv run ruff format careervp/handlers/gap_handler.py careervp/models/gap_analysis.py

# Lint
uv run ruff check --fix .

# Type check
uv run mypy careervp/handlers/gap_handler.py --strict

# Integration tests
uv run pytest tests/gap-analysis/integration/test_gap_handler.py -v

# Expected: All integration tests pass
```

---

## Acceptance Criteria

- [ ] `gap_handler.py` implements synchronous Lambda handler
- [ ] Request validation with Pydantic models
- [ ] JWT user_id extraction and validation
- [ ] File size validation enforced
- [ ] CV retrieval from DAL
- [ ] Gap question generation called
- [ ] Error handling for all failure modes
- [ ] AWS Powertools decorators used
- [ ] CORS headers included
- [ ] Returns 200 OK with questions immediately
- [ ] All integration tests pass
- [ ] Type checking passes

---

## Commit Message

```bash
git add src/backend/careervp/handlers/gap_handler.py src/backend/careervp/models/gap_analysis.py
git commit -m "feat(gap-analysis): add synchronous Lambda handler

- Implement POST /api/gap-analysis handler
- Add GapAnalysisRequest/Response Pydantic models
- Add request validation and JWT verification
- Add file size validation (10MB limit)
- Integrate with gap analysis logic
- Return 200 OK with questions immediately (synchronous)
- All integration tests pass (12/12)

Per docs/specs/gap-analysis/GAP_SPEC.md.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```
