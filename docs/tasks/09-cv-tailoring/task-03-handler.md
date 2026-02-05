# Task 9.3: CV Tailoring - Lambda Handler

**Status:** Pending
**Spec Reference:** [docs/specs/04-cv-tailoring.md](../../specs/04-cv-tailoring.md)
**Depends On:** Task 9.1 (Models), Task 9.2 (Logic)

## Overview

Create the Lambda handler for the `POST /api/tailor-cv` endpoint. The handler validates requests, fetches required data (UserCV, JobPosting, CompanyResearch), delegates to the tailoring logic, and returns properly formatted responses with appropriate HTTP status codes.

## Todo

### Handler Implementation

- [ ] Create `src/backend/careervp/handlers/cv_tailor_handler.py`
- [ ] Implement `lambda_handler()` with Powertools decorators
- [ ] Implement `_parse_body()` for request parsing
- [ ] Implement `_fetch_required_data()` to retrieve CV, job, and research
- [ ] Implement `_serialize_response()` for API Gateway format
- [ ] Implement `_map_result_code_to_http_status()` for error mapping
- [ ] Implement `_emit_success_metrics()` for observability
- [ ] Add environment variable handling for table name and config

### DAL Methods

- [ ] Add `get_job_posting()` method to `DynamoDalHandler` if not exists
- [ ] Add `get_company_research()` method to `DynamoDalHandler` if not exists
- [ ] Add `save_tailored_cv()` method to `DynamoDalHandler`

### Validation

- [ ] Run `uv run ruff format src/backend/careervp/handlers/cv_tailor_handler.py`
- [ ] Run `uv run ruff check --fix src/backend/careervp/handlers/`
- [ ] Run `uv run mypy src/backend/careervp/handlers/ --strict`

### Commit

- [ ] Commit with message: `feat(handler): add CV tailoring Lambda endpoint`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `src/backend/careervp/handlers/cv_tailor_handler.py` | Lambda handler for POST /api/tailor-cv |
| `src/backend/careervp/dal/dynamo_dal_handler.py` | Add new DAL methods |
| `src/backend/careervp/handlers/__init__.py` | Export handler |

### Key Implementation Details

```python
"""
CV Tailor Lambda Handler.
Per docs/specs/04-cv-tailoring.md.

Endpoint: POST /api/tailor-cv
Timeout: 60 seconds
Memory: 512 MB
"""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from typing import Any

from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.logic.cv_tailor import tailor_cv
from careervp.models.result import ResultCode
from careervp.models.tailor import TailorCVRequest, TailorCVResponse

JSON_HEADERS = {'Content-Type': 'application/json'}


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """
    Handle CV tailoring requests.

    Flow:
        1. Parse and validate request body
        2. Fetch required data (UserCV, JobPosting, CompanyResearch)
        3. Optionally fetch GapAnalysis if requested
        4. Delegate to tailor_cv() logic
        5. Map Result codes to HTTP statuses
        6. Emit success metrics

    Returns:
        API Gateway response with tailored CV or error details.
    """
    table_name = os.environ['DYNAMODB_TABLE_NAME']

    # Step 1: Parse and validate request
    try:
        request_body = _parse_body(event)
        request = TailorCVRequest.model_validate(request_body)
    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning('Invalid request body', error=str(exc))
        return _serialize_response(
            TailorCVResponse(
                success=False,
                error='Invalid request body',
                code=ResultCode.INVALID_INPUT,
            ),
            HTTPStatus.BAD_REQUEST,
        )
    except ValidationError as exc:
        logger.warning('Request validation failed', error=str(exc))
        return _serialize_response(
            TailorCVResponse(
                success=False,
                error=f'Validation error: {exc.error_count()} errors',
                code=ResultCode.INVALID_INPUT,
                details={'validation_errors': str(exc.errors())},
            ),
            HTTPStatus.BAD_REQUEST,
        )

    # Add context keys for tracing
    logger.append_keys(
        user_id=request.user_id,
        application_id=request.application_id,
        job_id=request.job_id,
    )
    logger.info('processing CV tailoring request')

    # Step 2: Initialize DAL and fetch required data
    dal = DynamoDalHandler(table_name)

    fetch_result = _fetch_required_data(
        dal=dal,
        user_id=request.user_id,
        job_id=request.job_id,
        application_id=request.application_id,
        cv_version=request.cv_version,
    )

    if not fetch_result['success']:
        return _serialize_response(
            TailorCVResponse(
                success=False,
                error=fetch_result['error'],
                code=fetch_result['code'],
            ),
            _map_result_code_to_http_status(fetch_result['code']),
        )

    user_cv = fetch_result['user_cv']
    job_posting = fetch_result['job_posting']
    company_research = fetch_result['company_research']

    # Step 3: Optionally fetch gap analysis (Phase 11)
    gap_analysis = None
    if request.include_gap_analysis:
        gap_result = dal.get_gap_analysis(request.application_id)
        if gap_result.success and gap_result.data:
            gap_analysis = gap_result.data
            logger.info('gap analysis included in tailoring context')

    # Step 4: Delegate to tailoring logic
    result = tailor_cv(
        request=request,
        user_cv=user_cv,
        job_posting=job_posting,
        company_research=company_research,
        dal=dal,
        gap_analysis=gap_analysis,
    )

    # Step 5: Map result to response
    if not result.success:
        status = _map_result_code_to_http_status(result.code)
        return _serialize_response(
            TailorCVResponse(
                success=False,
                error=result.error,
                code=result.code,
            ),
            status,
        )

    # Step 6: Emit success metrics and return
    _emit_success_metrics(result.data)

    return _serialize_response(
        TailorCVResponse(
            success=True,
            data=result.data,
            code=ResultCode.CV_TAILORED,
        ),
        HTTPStatus.OK,
    )


def _parse_body(event: dict[str, Any]) -> dict[str, Any]:
    """Parse the API Gateway event body into a dictionary."""
    body = event.get('body')
    if body is None:
        raise ValueError('Request body is required.')

    if isinstance(body, dict):
        return body
    if isinstance(body, str):
        return json.loads(body)
    raise ValueError('Unsupported body type.')


@tracer.capture_method(capture_response=False)
def _fetch_required_data(
    dal: DynamoDalHandler,
    user_id: str,
    job_id: str,
    application_id: str,
    cv_version: int,
) -> dict[str, Any]:
    """
    Fetch all required data for CV tailoring.

    Returns dict with success, data objects, or error details.
    """
    # Fetch UserCV
    cv_result = dal.get_user_cv(user_id, version=cv_version)
    if not cv_result.success or cv_result.data is None:
        logger.warning('UserCV not found', user_id=user_id, version=cv_version)
        return {
            'success': False,
            'error': f'CV version {cv_version} not found for user',
            'code': ResultCode.CV_NOT_FOUND,
        }

    # Fetch JobPosting
    job_result = dal.get_job_posting(job_id)
    if not job_result.success or job_result.data is None:
        logger.warning('JobPosting not found', job_id=job_id)
        return {
            'success': False,
            'error': f'Job posting {job_id} not found',
            'code': ResultCode.JOB_NOT_FOUND,
        }

    # Fetch CompanyResearch
    research_result = dal.get_company_research(application_id)
    if not research_result.success or research_result.data is None:
        logger.warning('CompanyResearch not found', application_id=application_id)
        return {
            'success': False,
            'error': f'Company research not found for application {application_id}',
            'code': ResultCode.COMPANY_RESEARCH_NOT_FOUND,
        }

    return {
        'success': True,
        'user_cv': cv_result.data,
        'job_posting': job_result.data,
        'company_research': research_result.data,
    }


def _serialize_response(response: TailorCVResponse, status: HTTPStatus) -> dict[str, Any]:
    """Serialize response into API Gateway format."""
    return {
        'statusCode': int(status),
        'headers': JSON_HEADERS,
        'body': response.model_dump_json(),
    }


def _map_result_code_to_http_status(code: str) -> HTTPStatus:
    """Translate ResultCode values into HTTP statuses."""
    mapping = {
        ResultCode.SUCCESS: HTTPStatus.OK,
        ResultCode.CV_TAILORED: HTTPStatus.OK,
        ResultCode.INVALID_INPUT: HTTPStatus.BAD_REQUEST,
        ResultCode.CV_NOT_FOUND: HTTPStatus.NOT_FOUND,
        ResultCode.JOB_NOT_FOUND: HTTPStatus.NOT_FOUND,
        ResultCode.COMPANY_RESEARCH_NOT_FOUND: HTTPStatus.NOT_FOUND,
        ResultCode.FVS_HALLUCINATION_DETECTED: HTTPStatus.UNPROCESSABLE_ENTITY,
        ResultCode.CV_TAILORING_FAILED: HTTPStatus.INTERNAL_SERVER_ERROR,
        ResultCode.LLM_API_ERROR: HTTPStatus.BAD_GATEWAY,
        ResultCode.LLM_TIMEOUT: HTTPStatus.GATEWAY_TIMEOUT,
        ResultCode.DYNAMODB_ERROR: HTTPStatus.INTERNAL_SERVER_ERROR,
        ResultCode.INTERNAL_ERROR: HTTPStatus.INTERNAL_SERVER_ERROR,
    }
    return mapping.get(code, HTTPStatus.INTERNAL_SERVER_ERROR)


def _emit_success_metrics(data: TailoredCVData) -> None:
    """Emit CloudWatch metrics for successful tailoring."""
    metrics.add_metric(name='CVTailoringSuccess', unit='Count', value=1)
    metrics.add_metric(
        name='CVTailoringKeywordMatches',
        unit='Count',
        value=data.metadata.keyword_matches,
    )
    metrics.add_metric(
        name='CVTailoringTokensUsed',
        unit='Count',
        value=data.token_usage.input_tokens + data.token_usage.output_tokens,
    )
```

### DAL Methods to Add

Add these methods to `src/backend/careervp/dal/dynamo_dal_handler.py`:

```python
@tracer.capture_method(capture_response=False)
def get_job_posting(self, job_id: str) -> Result[JobPosting | None]:
    """
    Retrieve job posting by ID.
    PK: job_id, SK: JOB_POSTING
    """
    logger.append_keys(job_id=job_id)
    logger.info('fetching job posting from DynamoDB')
    try:
        table = self._get_db_handler(self.table_name)
        response = table.get_item(
            Key={'pk': job_id, 'sk': 'JOB_POSTING'}
        )
        item = response.get('Item')
        if item is None:
            return Result(success=True, data=None, code=ResultCode.SUCCESS)
        return Result(
            success=True,
            data=JobPosting.model_validate(item),
            code=ResultCode.SUCCESS,
        )
    except (ClientError, ValidationError) as exc:
        logger.exception('failed to fetch job posting', job_id=job_id)
        return Result(
            success=False,
            error=str(exc),
            code=ResultCode.DYNAMODB_ERROR,
        )


@tracer.capture_method(capture_response=False)
def get_company_research(self, application_id: str) -> Result[CompanyContext | None]:
    """
    Retrieve company research for an application.
    PK: application_id, SK: ARTIFACT#COMPANY_RESEARCH
    """
    logger.append_keys(application_id=application_id)
    logger.info('fetching company research from DynamoDB')
    try:
        table = self._get_db_handler(self.table_name)
        response = table.get_item(
            Key={'pk': application_id, 'sk': 'ARTIFACT#COMPANY_RESEARCH'}
        )
        item = response.get('Item')
        if item is None:
            return Result(success=True, data=None, code=ResultCode.SUCCESS)
        return Result(
            success=True,
            data=CompanyContext.model_validate(item),
            code=ResultCode.SUCCESS,
        )
    except (ClientError, ValidationError) as exc:
        logger.exception('failed to fetch company research', application_id=application_id)
        return Result(
            success=False,
            error=str(exc),
            code=ResultCode.DYNAMODB_ERROR,
        )


@tracer.capture_method(capture_response=False)
def save_tailored_cv(
    self,
    application_id: str,
    tailored_cv: TailoredCVData,
) -> Result[None]:
    """
    Persist tailored CV artifact.
    PK: application_id, SK: ARTIFACT#TAILORED_CV#v{version}
    """
    logger.append_keys(application_id=application_id)
    logger.info('saving tailored CV to DynamoDB')
    try:
        table = self._get_db_handler(self.table_name)
        item_dict = tailored_cv.model_dump(mode='json')
        item_dict['pk'] = application_id
        item_dict['sk'] = f"ARTIFACT#TAILORED_CV#v{tailored_cv.metadata.version}"
        table.put_item(Item=item_dict)
    except (ClientError, ValidationError) as exc:
        logger.exception('failed to save tailored CV', application_id=application_id)
        return Result(
            success=False,
            error=str(exc),
            code=ResultCode.DYNAMODB_ERROR,
        )

    logger.info('tailored CV saved successfully')
    return Result(success=True, data=None, code=ResultCode.SUCCESS)


@tracer.capture_method(capture_response=False)
def get_gap_analysis(self, application_id: str) -> Result[dict | None]:
    """
    Retrieve gap analysis for an application (Phase 11 support).
    PK: application_id, SK: ARTIFACT#GAP_ANALYSIS
    """
    logger.append_keys(application_id=application_id)
    logger.info('fetching gap analysis from DynamoDB')
    try:
        table = self._get_db_handler(self.table_name)
        response = table.get_item(
            Key={'pk': application_id, 'sk': 'ARTIFACT#GAP_ANALYSIS'}
        )
        item = response.get('Item')
        if item is None:
            return Result(success=True, data=None, code=ResultCode.SUCCESS)
        return Result(success=True, data=item, code=ResultCode.SUCCESS)
    except ClientError as exc:
        logger.exception('failed to fetch gap analysis', application_id=application_id)
        return Result(
            success=False,
            error=str(exc),
            code=ResultCode.DYNAMODB_ERROR,
        )
```

### HTTP Status Mapping

| ResultCode | HTTP Status | Description |
| ---------- | ----------- | ----------- |
| `CV_TAILORED` | 200 OK | Success |
| `INVALID_INPUT` | 400 Bad Request | Malformed request |
| `CV_NOT_FOUND` | 404 Not Found | CV version doesn't exist |
| `JOB_NOT_FOUND` | 404 Not Found | Job posting doesn't exist |
| `COMPANY_RESEARCH_NOT_FOUND` | 404 Not Found | Research not available |
| `FVS_HALLUCINATION_DETECTED` | 422 Unprocessable Entity | Validation failed |
| `CV_TAILORING_FAILED` | 500 Internal Server Error | Processing error |
| `LLM_API_ERROR` | 502 Bad Gateway | LLM service error |
| `LLM_TIMEOUT` | 504 Gateway Timeout | LLM timed out |

### Environment Variables

| Variable | Required | Description |
| -------- | -------- | ----------- |
| `DYNAMODB_TABLE_NAME` | Yes | Main DynamoDB table name |
| `POWERTOOLS_SERVICE_NAME` | Yes | Service name for observability |
| `CONFIGURATION_APP` | Yes | AppConfig application name |

### Zero-Hallucination Checklist

- [ ] Handler imports `TailorCVRequest` and `TailorCVResponse` from models
- [ ] All data fetching wrapped in error handling with specific ResultCodes
- [ ] `gap_analysis` parameter properly forwarded to logic layer
- [ ] Response serialization uses `model_dump_json()` for Pydantic models
- [ ] Metrics include token usage for cost tracking

### Acceptance Criteria

- [ ] Handler returns 200 with tailored CV on success
- [ ] Handler returns 400 for invalid request bodies
- [ ] Handler returns 404 when CV, job, or research not found
- [ ] Handler returns 422 when FVS validation fails
- [ ] All Powertools decorators applied in correct order
- [ ] Metrics emitted: `CVTailoringSuccess`, `CVTailoringKeywordMatches`, `CVTailoringTokensUsed`

---

### Verification & Compliance

1. Run `python src/backend/scripts/validate_naming.py --path infra --strict`
2. Run `uv run ruff format . && uv run ruff check --fix . && uv run mypy --strict .`
3. If any path or class signature is missing, report a **BLOCKING ISSUE** and exit.
