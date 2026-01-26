# Task 05: VPR Lambda Handler

**Status:** Pending
**Spec Reference:** [[docs/specs/03-vpr-generator.md]]
**Depends On:** Task 02 (DAL), Task 03 (Logic), Task 04 (Prompt)

## Overview

Create the Lambda handler for VPR generation endpoint (`POST /api/vpr`). Handler follows the existing CV upload handler patterns with AWS Lambda Powertools integration.

## Todo

### Handler Implementation

- [ ] Create `src/backend/careervp/handlers/vpr_handler.py`.
- [ ] Implement `lambda_handler(event, context)` with Powertools decorators.
- [ ] Parse and validate `VPRRequest` from event body.
- [ ] Fetch user's CV from DynamoDB using `user_id`.
- [ ] Call `generate_vpr()` from logic layer.
- [ ] Return `VPRResponse` as JSON.

### Error Handling

- [ ] Handle missing CV (404 response).
- [ ] Handle FVS validation failures (422 response).
- [ ] Handle LLM errors (502 response).
- [ ] Handle timeout (504 response - 120s limit).

### Powertools Integration

- [ ] Add `@logger.inject_lambda_context` decorator.
- [ ] Add `@tracer.capture_lambda_handler` decorator.
- [ ] Add `@metrics.log_metrics` decorator.
- [ ] Add custom metrics: `VPRGenerated`, `VPRGenerationTime`, `VPRCost`.

### Validation

- [ ] Run `uv run ruff format src/backend/careervp/handlers/vpr_handler.py`.
- [ ] Run `uv run ruff check --fix src/backend/careervp/handlers/vpr_handler.py`.
- [ ] Run `uv run mypy src/backend/careervp/handlers/vpr_handler.py --strict`.

### Commit

- [ ] Commit with message: `feat(vpr): add VPR Lambda handler with Powertools`.

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `src/backend/careervp/handlers/vpr_handler.py` | Lambda handler |
| `src/backend/careervp/handlers/cv_upload_handler.py` | Reference pattern |
| `src/backend/tests/unit/test_vpr_handler.py` | Unit tests with moto |

### Key Implementation Details

```python
"""
VPR Generation Lambda Handler.
Per docs/specs/03-vpr-generator.md API Contract.

Endpoint: POST /api/vpr
Timeout: 120 seconds
Memory: 1024 MB
"""

import json
import os
from typing import Any

from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.logic.vpr_generator import generate_vpr
from careervp.models.result import ResultCode
from careervp.models.vpr import VPRRequest, VPRResponse


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """
    Handle VPR generation requests.

    Request Body (VPRRequest):
        - application_id: str
        - user_id: str
        - job_posting: JobPosting
        - gap_responses: list[GapResponse] (optional)
        - company_context: CompanyContext (optional)

    Returns:
        VPRResponse as JSON with status code.
    """
    table_name = os.environ['DYNAMODB_TABLE_NAME']
    dal = DynamoDalHandler(table_name)

    # Parse request body
    try:
        body = json.loads(event.get('body', '{}'))
        request = VPRRequest.model_validate(body)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error('Invalid request body', error=str(e))
        return _error_response(400, 'Invalid request body', str(e))

    logger.append_keys(
        application_id=request.application_id,
        user_id=request.user_id,
    )

    # Fetch user's CV
    user_cv = dal.get_cv(request.user_id)
    if not user_cv:
        logger.warning('CV not found for user')
        return _error_response(404, 'CV not found', 'Upload CV before generating VPR')

    # Generate VPR
    result = generate_vpr(request, user_cv, dal)

    if not result.success:
        # Map result codes to HTTP status codes
        status_code = _map_result_code_to_http(result.code)
        return _error_response(status_code, result.code, result.error or 'Unknown error')

    # Track metrics
    if result.data and result.data.token_usage:
        metrics.add_metric(name='VPRGenerated', unit='Count', value=1)
        metrics.add_metric(
            name='VPRGenerationTimeMs',
            unit='Milliseconds',
            value=result.data.generation_time_ms,
        )
        metrics.add_metric(
            name='VPRCostUSD',
            unit='None',
            value=result.data.token_usage.cost_usd,
        )

    logger.info('VPR generated successfully')
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': result.data.model_dump_json() if result.data else '{}',
    }


def _error_response(status_code: int, code: str, message: str) -> dict[str, Any]:
    """Build standardized error response."""
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'success': False,
            'error': message,
            'code': code,
        }),
    }


def _map_result_code_to_http(code: str) -> int:
    """Map ResultCode to HTTP status code."""
    mapping = {
        ResultCode.INVALID_INPUT: 400,
        ResultCode.MISSING_REQUIRED_FIELD: 400,
        ResultCode.FVS_HALLUCINATION_DETECTED: 422,
        ResultCode.FVS_VALIDATION_FAILED: 422,
        ResultCode.LLM_API_ERROR: 502,
        ResultCode.LLM_TIMEOUT: 504,
        ResultCode.DYNAMODB_ERROR: 500,
    }
    return mapping.get(code, 500)
```

### Result Pattern Enforcement

Handler converts `Result[VPRResponse]` to HTTP response:

```python
# Success path
if result.success and result.data:
    return {'statusCode': 200, 'body': result.data.model_dump_json()}

# Error path - NEVER raise exceptions to API Gateway
if not result.success:
    return _error_response(status_code, result.code, result.error)
```

### Pytest Commands

```bash
# Run handler tests
cd src/backend && uv run pytest tests/unit/test_vpr_handler.py -v

# Run with coverage
cd src/backend && uv run pytest tests/unit/test_vpr_handler.py -v --cov=careervp/handlers/vpr_handler

# Run all handler tests
cd src/backend && uv run pytest tests/unit/test_*_handler.py -v
```

### Zero-Hallucination Checklist

- [ ] Handler passes `user_cv` (IMMUTABLE source) to logic layer unchanged.
- [ ] Handler does NOT modify request.job_posting or request.gap_responses.
- [ ] FVS errors return 422 (Unprocessable Entity) to indicate hallucination blocked.
- [ ] No data transformation in handler that could introduce hallucination vectors.

### Infrastructure Requirements (for CDK)

```python
# Lambda configuration in infra/careervp_stack.py
vpr_lambda = aws_lambda.Function(
    self, 'VPRHandler',
    function_name='careervp-vpr-generator',
    runtime=aws_lambda.Runtime.PYTHON_3_14,
    handler='careervp.handlers.vpr_handler.lambda_handler',
    memory_size=1024,
    timeout=Duration.seconds(120),
    environment={
        'DYNAMODB_TABLE_NAME': table.table_name,
        'ANTHROPIC_API_KEY_SECRET_NAME': 'careervp/anthropic-api-key',
    },
)
```

### Acceptance Criteria

- [ ] Handler follows Powertools patterns from cv_upload_handler.py.
- [ ] All Result codes mapped to appropriate HTTP status codes.
- [ ] Metrics tracked: VPRGenerated, VPRGenerationTimeMs, VPRCostUSD.
- [ ] All mypy --strict checks pass.
- [ ] Unit tests with moto cover success/error paths.
