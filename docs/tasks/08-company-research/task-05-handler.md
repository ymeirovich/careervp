# Task 8.5: Company Research Handler

**Status:** Not Started
**Spec Reference:** [[docs/specs/02-company-research.md]]
**Priority:** P0

## Overview

Create the Lambda handler for the company research API endpoint, following existing handler patterns with AWS Powertools decorators.

## Todo

### Handler Implementation (`handlers/company_research_handler.py`)

- [ ] Create `handlers/company_research_handler.py` file
- [ ] Import and configure AWS Powertools (logger, tracer, metrics)
- [ ] Implement `lambda_handler(event: dict, context: LambdaContext) -> dict`:
    - Parse CompanyResearchRequest from event body
    - Call `research_company()` logic
    - Map Result codes to HTTP status codes
    - Return CompanyResearchResponse as JSON
- [ ] Implement request validation:
    - Validate required `company_name` field
    - Validate optional URL fields
- [ ] Add proper error handling and logging

### HTTP Status Mapping

| Result Code | HTTP Status | Description |
| ----------- | ----------- | ----------- |
| RESEARCH_COMPLETE | 200 | Full research result |
| SUCCESS | 200 | Full research result |
| INVALID_INPUT | 400 | Missing company_name |
| SCRAPE_FAILED | 206 | Partial content (fallback used) |
| ALL_SOURCES_FAILED | 503 | Service unavailable |
| TIMEOUT | 504 | Gateway timeout |

### Powertools Setup

```python
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()
metrics = Metrics()
```

### Validation

- [ ] Run `uv run ruff format careervp/handlers/company_research_handler.py`
- [ ] Run `uv run ruff check careervp/handlers/company_research_handler.py --fix`
- [ ] Run `uv run mypy careervp/handlers/company_research_handler.py --strict`

### Commit

- [ ] Commit with message: `feat(company-research): add Lambda handler`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `src/backend/careervp/handlers/company_research_handler.py` | Lambda entry point |

### Handler Pattern (Follow cv_upload_handler.py)

```python
"""Lambda handler for company research API endpoint."""

from __future__ import annotations

import asyncio
import json
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from careervp.logic.company_research import research_company
from careervp.models.company import CompanyResearchRequest, CompanyResearchResult
from careervp.models.result import ResultCode

if TYPE_CHECKING:
    pass

logger = Logger()
tracer = Tracer()
metrics = Metrics()


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Handle company research requests."""
    logger.info("Company research request received")

    try:
        body = json.loads(event.get("body", "{}"))
        request = CompanyResearchRequest(**body)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"Invalid request: {e}")
        return _build_response(
            status_code=HTTPStatus.BAD_REQUEST,
            body={"error": "Invalid request", "details": str(e)},
        )

    # Run async research in sync handler
    result = asyncio.run(research_company(request))

    if not result.success:
        status_code = _map_result_code_to_status(result.code)
        return _build_response(
            status_code=status_code,
            body={"error": result.error, "code": result.code.value if result.code else "UNKNOWN"},
        )

    # Log metrics
    if result.data:
        metrics.add_metric(name="CompanyResearchSuccess", unit=MetricUnit.Count, value=1)
        metrics.add_metric(
            name=f"ResearchSource_{result.data.source.value}",
            unit=MetricUnit.Count,
            value=1,
        )

    return _build_response(
        status_code=HTTPStatus.OK,
        body=result.data.model_dump() if result.data else {},
    )


def _map_result_code_to_status(code: ResultCode | None) -> HTTPStatus:
    """Map Result code to HTTP status."""
    if code is None:
        return HTTPStatus.INTERNAL_SERVER_ERROR

    mapping = {
        ResultCode.SUCCESS: HTTPStatus.OK,
        ResultCode.INVALID_INPUT: HTTPStatus.BAD_REQUEST,
        ResultCode.SCRAPE_FAILED: HTTPStatus.PARTIAL_CONTENT,
        ResultCode.SEARCH_FAILED: HTTPStatus.PARTIAL_CONTENT,
        ResultCode.ALL_SOURCES_FAILED: HTTPStatus.SERVICE_UNAVAILABLE,
        ResultCode.TIMEOUT: HTTPStatus.GATEWAY_TIMEOUT,
        ResultCode.LLM_API_ERROR: HTTPStatus.BAD_GATEWAY,
    }
    return mapping.get(code, HTTPStatus.INTERNAL_SERVER_ERROR)


def _build_response(status_code: HTTPStatus, body: dict[str, Any]) -> dict[str, Any]:
    """Build API Gateway response."""
    return {
        "statusCode": status_code.value,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, default=str),
    }
```

### Required ResultCode Additions

Add to `models/result.py` if not present:
```python
class ResultCode(str, Enum):
    # ... existing codes
    SCRAPE_FAILED = "SCRAPE_FAILED"
    SEARCH_FAILED = "SEARCH_FAILED"
    ALL_SOURCES_FAILED = "ALL_SOURCES_FAILED"
    NO_RESULTS = "NO_RESULTS"
```

### Verification Commands

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run ruff format careervp/handlers/company_research_handler.py
uv run ruff check careervp/handlers/company_research_handler.py --fix
uv run mypy careervp/handlers/company_research_handler.py --strict
```

### Commit Instructions

```bash
cd /Users/yitzchak/Documents/dev/careervp
git add src/backend/careervp/handlers/company_research_handler.py
git commit -m "feat(company-research): add Lambda handler

- Add lambda_handler with Powertools decorators
- Add request parsing and validation
- Add HTTP status code mapping
- Add metrics for research source tracking
- Follow cv_upload_handler.py patterns

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## Acceptance Criteria

- [ ] Follows cv_upload_handler.py patterns exactly
- [ ] Returns source attribution in response
- [ ] Logs research path for debugging
- [ ] Tracks metrics per research source
- [ ] All code passes ruff and mypy --strict
- [ ] Returns appropriate HTTP status codes for each scenario
