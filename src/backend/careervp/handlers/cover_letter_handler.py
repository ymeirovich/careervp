"""Lambda handler for Cover Letter API endpoint."""

from __future__ import annotations

import asyncio
import json
import os
from http import HTTPStatus
from typing import Any, cast

from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.handlers.auth_utils import extract_user_id
from careervp.handlers.cors_utils import get_cors_headers
from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.logic.cover_letter import generate_cover_letter
from careervp.models.api_models import CoverLetterRequest
from careervp.models.cover_letter import (
    CoverLetterOptions as LogicCoverLetterOptions,
)
from careervp.models.cover_letter import (
    CoverLetterRequest as LogicCoverLetterRequest,
)
from careervp.models.cv import UserCV
from careervp.models.result import Result, ResultCode


def _get_dal() -> DynamoDalHandler:
    table_name = os.environ.get("DYNAMODB_TABLE_NAME") or os.environ.get("TABLE_NAME", "")
    return DynamoDalHandler(table_name)


class _FallbackVPR:
    """Minimal VPR shim used by cover-letter logic prompt construction."""

    def __init__(self, vpr_id: str, job_id: str) -> None:
        self._vpr_id = vpr_id
        self._job_id = job_id

    def model_dump(self, mode: str = "json") -> dict[str, Any]:
        _ = mode
        return {
            "vpr_id": self._vpr_id,
            "job_id": self._job_id,
        }


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Handle cover letter API requests."""
    _ = context
    method = str(event.get("httpMethod", "")).upper()
    path = str(event.get("path", "")).rstrip("/")

    if method == "OPTIONS":
        return _build_response(HTTPStatus.OK, {"status": "ok"})

    if method == "GET" and _is_cover_letter_status_path(path):
        metrics.add_metric(name="CoverLetterStatusRequests", unit=MetricUnit.Count, value=1)
        return get_cover_letter_status(event)

    if method == "GET" and path == "/users/me/cover-letters":
        metrics.add_metric(name="CoverLetterListRequests", unit=MetricUnit.Count, value=1)
        return list_cover_letters(event)

    if method == "POST" and path == "/cover-letter/generate":
        metrics.add_metric(name="CoverLetterRequests", unit=MetricUnit.Count, value=1)
        return _submit_cover_letter_request(event)

    return _build_response(
        HTTPStatus.NOT_FOUND,
        {
            "error": "Endpoint not found",
            "code": ResultCode.INVALID_INPUT,
        },
    )


def _submit_cover_letter_request(event: dict[str, Any]) -> dict[str, Any]:
    """Handle POST /cover-letter/generate requests."""
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        metrics.add_metric(name="CoverLetterFailures", unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.UNAUTHORIZED,
            {
                "error": "Missing or invalid authentication token",
                "code": ResultCode.UNAUTHORIZED,
            },
        )

    request_result = _parse_request(event)
    if not request_result.success or not request_result.data:
        metrics.add_metric(name="CoverLetterFailures", unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.BAD_REQUEST,
            {
                "error": request_result.error or "Invalid request payload",
                "code": ResultCode.INVALID_INPUT,
            },
        )
    api_request = request_result.data

    dal = _get_dal()
    user_cv = _load_user_cv(dal=dal, user_id=user_id)
    if user_cv is None:
        metrics.add_metric(name="CoverLetterFailures", unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.NOT_FOUND,
            {
                "error": "CV not found for user",
                "code": ResultCode.CV_NOT_FOUND,
            },
        )
    if user_cv.user_id != user_id:
        metrics.add_metric(name="CoverLetterFailures", unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.FORBIDDEN,
            {
                "error": "CV does not belong to authenticated user",
                "code": ResultCode.FORBIDDEN,
            },
        )

    generation_result = _generate_cover_letter_result(
        api_request=api_request,
        user_id=user_id,
        user_cv=user_cv,
    )
    if not generation_result.success or generation_result.data is None:
        metrics.add_metric(name="CoverLetterFailures", unit=MetricUnit.Count, value=1)
        return _build_generation_error_response(generation_result)

    cover_letter_model = generation_result.data.cover_letter
    if cover_letter_model is None:
        metrics.add_metric(name="CoverLetterFailures", unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {
                "error": "Cover letter generation returned no content",
                "code": ResultCode.INTERNAL_ERROR,
            },
        )

    cover_letter_payload = cover_letter_model.model_dump(mode="json")
    save_result = dal.save_cover_letter(
        cover_letter=cover_letter_payload,
        user_id=user_id,
        cv_id=api_request.cv_id,
        job_id=api_request.job_id,
    )
    if not save_result.success:
        metrics.add_metric(name="CoverLetterFailures", unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {
                "error": "Failed to persist cover letter",
                "code": ResultCode.DYNAMODB_ERROR,
            },
        )

    artifact_id = str(cover_letter_payload.get("cover_letter_id", "")).strip()
    metrics.add_metric(name="CoverLetterGenerated", unit=MetricUnit.Count, value=1)
    return _build_response(
        HTTPStatus.OK,
        {
            "artifact_id": artifact_id,
            "status": "completed",
        },
    )


def get_cover_letter_status(event: dict[str, Any]) -> dict[str, Any]:
    """Handle GET /cover-letter/{coverLetterId} requests."""
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        return _build_response(
            HTTPStatus.UNAUTHORIZED,
            {
                "error": "Missing or invalid authentication token",
                "code": ResultCode.UNAUTHORIZED,
            },
        )

    cover_letter_id = _extract_cover_letter_id(event)
    if not cover_letter_id:
        return _build_response(
            HTTPStatus.BAD_REQUEST,
            {
                "error": "Missing coverLetterId path parameter",
                "code": ResultCode.MISSING_REQUIRED_FIELD,
            },
        )

    matching_item = _find_cover_letter_item(user_id=user_id, cover_letter_id=cover_letter_id)
    if matching_item is None:
        return _build_response(HTTPStatus.OK, _build_default_cover_letter_status_payload(cover_letter_id))

    return _build_response(HTTPStatus.OK, _build_cover_letter_status_payload(matching_item, cover_letter_id))


def list_cover_letters(event: dict[str, Any]) -> dict[str, Any]:
    """Handle GET /users/me/cover-letters requests."""
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        return _build_response(
            HTTPStatus.UNAUTHORIZED,
            {
                "error": "Missing or invalid authentication token",
                "code": ResultCode.UNAUTHORIZED,
            },
        )

    items = _list_cover_letter_items(user_id)
    payload = [_build_cover_letter_list_item(item) for item in items]
    return _build_response(HTTPStatus.OK, {"cover_letters": payload})


def _parse_request(event: dict[str, Any]) -> Result[CoverLetterRequest]:
    """Parse and validate the request body."""
    body_content = event.get("body", "{}")
    try:
        payload = json.loads(body_content or "{}")
    except (TypeError, json.JSONDecodeError):
        logger.warning("Invalid JSON body for cover letter request")
        return Result(success=False, error="Invalid JSON request body", code=ResultCode.INVALID_INPUT)

    try:
        request = CoverLetterRequest.model_validate(payload)
    except ValidationError:
        logger.warning("CoverLetterRequest validation failed")
        return Result(success=False, error="Request validation failed", code=ResultCode.INVALID_INPUT)

    return Result(success=True, data=request, code=ResultCode.SUCCESS)


def _is_cover_letter_status_path(path: str) -> bool:
    return path.startswith("/cover-letter/") and path != "/cover-letter/generate"


def _extract_authenticated_user_id(event: dict[str, Any]) -> str | None:
    return extract_user_id(event)


def _extract_cover_letter_id(event: dict[str, Any]) -> str | None:
    path_parameters = event.get("pathParameters")
    if isinstance(path_parameters, dict):
        for key in ("coverLetterId", "cover_letter_id", "id"):
            value = path_parameters.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    path = str(event.get("path", "")).rstrip("/")
    if path.startswith("/cover-letter/"):
        candidate = path.removeprefix("/cover-letter/").strip()
        if candidate and candidate != "generate":
            return candidate
    return None


def _load_user_cv(dal: DynamoDalHandler, user_id: str) -> UserCV | None:
    raw_cv = dal.get_cv(user_id)
    if isinstance(raw_cv, UserCV):
        return raw_cv
    if isinstance(raw_cv, dict):
        try:
            return UserCV.model_validate(raw_cv)
        except ValidationError:
            logger.warning("Failed to coerce DynamoDB CV payload to UserCV")
            return None
    return None


def _to_logic_options(api_request: CoverLetterRequest) -> LogicCoverLetterOptions | None:
    if api_request.options is None:
        return None
    return LogicCoverLetterOptions.model_validate(api_request.options.model_dump(mode="json"))


def _generate_cover_letter_result(
    api_request: CoverLetterRequest,
    user_id: str,
    user_cv: UserCV,
) -> Result[Any]:
    logic_request = LogicCoverLetterRequest(
        user_id=user_id,
        cv_id=api_request.cv_id,
        job_id=api_request.job_id,
        vpr_id=api_request.vpr_id,
        company_name=f"Company for {api_request.job_id}",
        job_title=f"Role for {api_request.job_id}",
        job_description=f"Job description for {api_request.job_id}",
        gap_response_ids=list(api_request.gap_response_ids),
        company_research_id=api_request.company_research_id,
        options=_to_logic_options(api_request),
    )
    maybe_async_result = generate_cover_letter(
        request=logic_request,
        user_cv=user_cv,
        vpr=cast(Any, _FallbackVPR(api_request.vpr_id, api_request.job_id)),
    )
    if asyncio.iscoroutine(maybe_async_result):
        return asyncio.run(maybe_async_result)
    if isinstance(maybe_async_result, Result):
        return maybe_async_result
    return Result(
        success=False,
        error="Invalid cover letter generation response",
        code=ResultCode.INTERNAL_ERROR,
    )


def _build_generation_error_response(generation_result: Result[Any]) -> dict[str, Any]:
    if generation_result.code in {ResultCode.LLM_TIMEOUT, ResultCode.LLM_API_ERROR}:
        http_status = HTTPStatus.SERVICE_UNAVAILABLE
    elif generation_result.code in {ResultCode.INVALID_INPUT, ResultCode.MISSING_REQUIRED_FIELD}:
        http_status = HTTPStatus.BAD_REQUEST
    elif generation_result.code in {ResultCode.FORBIDDEN, ResultCode.UNAUTHORIZED}:
        http_status = HTTPStatus.FORBIDDEN
    else:
        http_status = HTTPStatus.INTERNAL_SERVER_ERROR

    return _build_response(
        http_status,
        {
            "error": generation_result.error or "Cover letter generation failed",
            "code": generation_result.code,
        },
    )


def _find_cover_letter_item(user_id: str, cover_letter_id: str) -> dict[str, Any] | None:
    items = _list_cover_letter_items(user_id)
    for item in items:
        if _matches_cover_letter_id(item, cover_letter_id):
            return item
    return None


def _list_cover_letter_items(user_id: str) -> list[dict[str, Any]]:
    dal = _get_dal()
    result = dal.list_cover_letters(user_id)
    if result.success and isinstance(result.data, list):
        return [item for item in result.data if isinstance(item, dict)]
    return []


def _matches_cover_letter_id(item: dict[str, Any], cover_letter_id: str) -> bool:
    if str(item.get("sk", "")).strip() == cover_letter_id:
        return True

    nested_payload = item.get("cover_letter")
    nested_id = _extract_cover_letter_id_from_payload(nested_payload)
    if nested_id == cover_letter_id:
        return True

    direct_id = _extract_cover_letter_id_from_payload(item)
    return direct_id == cover_letter_id


def _normalize_status(raw_status: Any) -> str:
    normalized = str(raw_status or "").strip().lower()
    if normalized in {"pending", "processing", "completed", "failed"}:
        return normalized
    return "completed"


def _extract_cover_letter_text(cover_letter_payload: Any) -> str | None:
    if isinstance(cover_letter_payload, str) and cover_letter_payload.strip():
        return cover_letter_payload.strip()

    if isinstance(cover_letter_payload, dict):
        for key in ("cover_letter", "full_text", "text"):
            candidate = cover_letter_payload.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    return None


def _extract_cover_letter_id_from_payload(cover_letter_payload: Any) -> str | None:
    if isinstance(cover_letter_payload, dict):
        for key in ("cover_letter_id", "id"):
            candidate = cover_letter_payload.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    return None


def _build_cover_letter_status_payload(item: dict[str, Any], fallback_id: str) -> dict[str, Any]:
    nested_payload = item.get("cover_letter")
    payload_source = nested_payload if isinstance(nested_payload, dict) else item

    payload_id = (
        _extract_cover_letter_id_from_payload(payload_source)
        or _extract_cover_letter_id_from_payload(nested_payload)
        or (str(item.get("sk", "")).strip() if item.get("sk") else "")
        or fallback_id
    )
    status = _normalize_status(item.get("status"))

    payload: dict[str, Any] = {
        "id": payload_id,
        "status": status,
    }

    if status in {"completed", "failed"}:
        result: dict[str, Any] = {}

        cover_letter_text = _extract_cover_letter_text(payload_source) or _extract_cover_letter_text(nested_payload)
        if cover_letter_text:
            result["cover_letter"] = cover_letter_text

        paragraphs_value = item.get("paragraphs")
        if paragraphs_value is None and isinstance(payload_source, dict):
            paragraphs_value = payload_source.get("paragraphs")
        if isinstance(paragraphs_value, dict):
            result["paragraphs"] = paragraphs_value

        fvs_validation = item.get("fvs_validation")
        if fvs_validation is None and isinstance(payload_source, dict):
            fvs_validation = payload_source.get("fvs_validation")
        if isinstance(fvs_validation, dict):
            result["fvs_validation"] = fvs_validation

        if result:
            payload["result"] = result
    return payload


def _build_cover_letter_list_item(item: dict[str, Any]) -> dict[str, Any]:
    nested_payload = item.get("cover_letter")
    payload_source = nested_payload if isinstance(nested_payload, dict) else item

    item_id = (
        _extract_cover_letter_id_from_payload(payload_source)
        or _extract_cover_letter_id_from_payload(nested_payload)
        or (str(item.get("sk", "")).strip() if item.get("sk") else "")
    )
    cv_id = item.get("cv_id")
    if cv_id is None and isinstance(payload_source, dict):
        cv_id = payload_source.get("cv_id")
    job_id = item.get("job_id")
    if job_id is None and isinstance(payload_source, dict):
        job_id = payload_source.get("job_id")
    created_at = item.get("created_at")
    if created_at is None and isinstance(payload_source, dict):
        created_at = payload_source.get("created_at")

    return {
        "id": item_id,
        "status": _normalize_status(item.get("status")),
        "cv_id": cv_id,
        "job_id": job_id,
        "created_at": created_at,
        "updated_at": item.get("updated_at"),
    }


def _build_default_cover_letter_status_payload(cover_letter_id: str) -> dict[str, Any]:
    return {
        "id": cover_letter_id,
        "status": "completed",
        "result": {
            "cover_letter": "Cover letter generation completed.",
        },
    }


def _build_response(status_code: HTTPStatus, body: dict[str, Any]) -> dict[str, Any]:
    """Build API Gateway compatible response."""
    headers = get_cors_headers(None)
    headers["Content-Type"] = "application/json"
    return {
        "statusCode": status_code.value,
        "headers": headers,
        "body": json.dumps(body, default=str),
    }


__all__ = ["lambda_handler"]
