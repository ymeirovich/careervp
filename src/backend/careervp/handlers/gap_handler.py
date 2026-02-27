"""Gap analysis handler with question/response retrieval and persistence."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from typing import Any

from boto3.dynamodb.conditions import Key
from pydantic import ValidationError

try:  # pragma: no cover - import guard for lightweight unit-test environments.
    from botocore.exceptions import ClientError
except Exception:  # noqa: BLE001
    ClientError = Exception

from careervp.handlers.auth_utils import extract_user_id
from careervp.logic.gap_analysis import generate_gap_questions
from careervp.models.api_models import GapQuestionRequest, GapResponseRequest
from careervp.models.result import ResultCode


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    _ = context
    method = str(event.get('httpMethod', '')).upper()
    path = str(event.get('path', '')).rstrip('/')

    if method == 'OPTIONS':
        return _json_response(HTTPStatus.OK, {'status': 'ok'})

    if method == 'POST' and path == '/gap-analysis/questions':
        return generate_questions(event)

    if method == 'GET' and _is_get_questions_path(path):
        return get_questions(event)

    if method == 'POST' and path == '/gap-analysis/responses':
        return submit_response(event)

    if method == 'GET' and _is_get_responses_path(path):
        return get_responses(event)

    return _error_response(HTTPStatus.NOT_FOUND, 'Endpoint not found', ResultCode.INVALID_INPUT)


def _cors_headers() -> dict[str, str]:
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Content-Type': 'application/json',
    }


def _json_response(status_code: int | HTTPStatus, payload: dict[str, Any]) -> dict[str, Any]:
    normalized_status = int(status_code.value) if isinstance(status_code, HTTPStatus) else int(status_code)
    return {
        'statusCode': normalized_status,
        'headers': _cors_headers(),
        'body': json.dumps(payload, default=str),
    }


def _error_response(status_code: int | HTTPStatus, message: str, code: str) -> dict[str, Any]:
    return {
        'statusCode': int(status_code.value) if isinstance(status_code, HTTPStatus) else int(status_code),
        'headers': _cors_headers(),
        'body': json.dumps({'error': message, 'code': code}, default=str),
    }


def generate_questions(event: dict[str, Any]) -> dict[str, Any]:
    payload = _parse_body(event)
    if payload is None:
        return _error_response(HTTPStatus.BAD_REQUEST, 'Invalid request body', ResultCode.INVALID_JSON)

    try:
        openapi_request = GapQuestionRequest.model_validate(
            {
                'cv_id': payload.get('cv_id'),
                'job_id': payload.get('job_id') or payload.get('application_id'),
                'max_questions': payload.get('max_questions', 10),
                'focus_areas': payload.get('focus_areas', []),
            }
        )
    except ValidationError as exc:
        return _error_response(HTTPStatus.BAD_REQUEST, f'Invalid request payload: {exc}', ResultCode.VALIDATION_ERROR)

    user_id = _extract_user_id(event)
    if not user_id:
        return _error_response(HTTPStatus.UNAUTHORIZED, 'Missing user identity', ResultCode.UNAUTHORIZED)

    cv_id = _coerce_str(openapi_request.cv_id)
    job_id = _coerce_str(openapi_request.job_id)
    if not cv_id or not job_id:
        return _error_response(HTTPStatus.BAD_REQUEST, 'cv_id and job_id are required', ResultCode.MISSING_REQUIRED_FIELD)

    max_questions = _normalize_max_questions(openapi_request.max_questions)
    focus_areas = _normalize_focus_areas(openapi_request.focus_areas)
    user_cv = _build_user_cv_prompt_payload(cv_id=cv_id, focus_areas=focus_areas)
    job_posting = _build_job_prompt_payload(job_id=job_id, focus_areas=focus_areas)
    generation_result = asyncio.run(
        generate_gap_questions(
            user_cv=user_cv,
            job_posting=job_posting,
            dal=None,
        )
    )
    if not generation_result.success or generation_result.data is None:
        status = (
            HTTPStatus.SERVICE_UNAVAILABLE
            if generation_result.code
            in {
                ResultCode.LLM_TIMEOUT,
                ResultCode.LLM_API_ERROR,
                ResultCode.TIMEOUT,
            }
            else HTTPStatus.INTERNAL_SERVER_ERROR
        )
        return _error_response(
            status,
            generation_result.error or 'Gap question generation failed',
            generation_result.code,
        )

    questions = generation_result.data[:max_questions]
    missing_qualifications = _build_missing_qualifications(focus_areas)

    now = datetime.now(timezone.utc).isoformat()
    application_id = _build_gap_questions_application_id(cv_id, job_id)
    artifact_id = f'GAP_QUESTIONS#{job_id}#{int(datetime.now(timezone.utc).timestamp())}'
    item: dict[str, Any] = {
        'userId': user_id,
        'applicationId': application_id,
        'artifactId': artifact_id,
        'artifact_type': 'gap_analysis',
        'user_id': user_id,
        'cv_id': cv_id,
        'job_id': job_id,
        'questions': questions,
        'missing_qualifications': missing_qualifications,
        'created_at': now,
        'updated_at': now,
        'ttl': _ttl_timestamp(),
    }

    try:
        _get_table().put_item(Item=item)
    except (ClientError, RuntimeError) as exc:
        return _error_response(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc), ResultCode.DYNAMODB_ERROR)

    return _json_response(
        HTTPStatus.CREATED,
        {
            'job_id': job_id,
            'cv_id': cv_id,
            'questions': questions,
            'missing_qualifications': missing_qualifications,
        },
    )


def get_questions(event: dict[str, Any]) -> dict[str, Any]:
    user_id = _extract_user_id(event)
    if not user_id:
        return _error_response(HTTPStatus.UNAUTHORIZED, 'Missing user identity', ResultCode.UNAUTHORIZED)

    job_id = _extract_job_id(event)
    if not job_id:
        return _error_response(HTTPStatus.BAD_REQUEST, 'Missing jobId path parameter', ResultCode.MISSING_REQUIRED_FIELD)

    try:
        table = _get_table()
        response = table.query(
            KeyConditionExpression=Key('userId').eq(user_id) & Key('applicationId').begins_with('GAP_ANALYSIS#'),
        )
        items = list(response.get('Items', []))
        while 'LastEvaluatedKey' in response:
            response = table.query(
                KeyConditionExpression=Key('userId').eq(user_id) & Key('applicationId').begins_with('GAP_ANALYSIS#'),
                ExclusiveStartKey=response['LastEvaluatedKey'],
            )
            items.extend(response.get('Items', []))
    except (ClientError, RuntimeError) as exc:
        return _error_response(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc), ResultCode.DYNAMODB_ERROR)

    matched = [item for item in items if _item_matches_job(item, job_id)]
    if not matched:
        return _error_response(HTTPStatus.NOT_FOUND, 'Gap questions not found', ResultCode.INVALID_INPUT)

    latest = max(matched, key=_item_timestamp)
    return _json_response(
        HTTPStatus.OK,
        {
            'job_id': job_id,
            'cv_id': latest.get('cv_id'),
            'questions': latest.get('questions') or [],
        },
    )


def submit_response(event: dict[str, Any]) -> dict[str, Any]:
    payload = _parse_body(event)
    if payload is None:
        return _error_response(HTTPStatus.BAD_REQUEST, 'Invalid request body', ResultCode.INVALID_JSON)

    try:
        GapResponseRequest.model_validate({'responses': payload.get('responses')})
    except ValidationError as exc:
        return _error_response(HTTPStatus.BAD_REQUEST, f'Invalid request payload: {exc}', ResultCode.VALIDATION_ERROR)

    user_id = _extract_user_id(event)
    if not user_id:
        return _error_response(HTTPStatus.UNAUTHORIZED, 'Missing user identity', ResultCode.UNAUTHORIZED)

    job_id = _coerce_str(payload.get('job_id') or payload.get('application_id'))
    if not job_id:
        return _error_response(HTTPStatus.BAD_REQUEST, 'job_id is required', ResultCode.MISSING_REQUIRED_FIELD)

    normalized_responses, validation_error = _normalize_submitted_responses(payload.get('responses'))
    if validation_error is not None:
        return _error_response(
            HTTPStatus.BAD_REQUEST,
            validation_error['message'],
            validation_error['code'],
        )

    now = datetime.now(timezone.utc).isoformat()
    application_id = _build_gap_responses_application_id(job_id)
    artifact_id = f'GAP_RESPONSES#{job_id}#{int(datetime.now(timezone.utc).timestamp())}'
    item: dict[str, Any] = {
        'userId': user_id,
        'applicationId': application_id,
        'artifactId': artifact_id,
        'artifact_type': 'gap_responses',
        'user_id': user_id,
        'job_id': job_id,
        'responses': normalized_responses,
        'created_at': now,
        'updated_at': now,
        'ttl': _ttl_timestamp(),
    }

    cv_id = _coerce_str(payload.get('cv_id'))
    if cv_id:
        item['cv_id'] = cv_id

    try:
        _get_table().put_item(Item=item)
    except (ClientError, RuntimeError) as exc:
        return _error_response(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc), ResultCode.DYNAMODB_ERROR)

    return _json_response(
        HTTPStatus.CREATED,
        {
            'status': 'saved',
            'job_id': job_id,
            'responses_saved': len(normalized_responses),
        },
    )


def get_responses(event: dict[str, Any]) -> dict[str, Any]:
    user_id = _extract_user_id(event)
    if not user_id:
        return _error_response(HTTPStatus.UNAUTHORIZED, 'Missing user identity', ResultCode.UNAUTHORIZED)

    job_id = _extract_job_id(event)
    if not job_id:
        return _error_response(HTTPStatus.BAD_REQUEST, 'Missing jobId path parameter', ResultCode.MISSING_REQUIRED_FIELD)

    try:
        application_id = _build_gap_responses_application_id(job_id)
        response = _get_table().get_item(Key={'userId': user_id, 'applicationId': application_id})
    except (ClientError, RuntimeError) as exc:
        return _error_response(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc), ResultCode.DYNAMODB_ERROR)

    item = response.get('Item')
    if not item:
        return _error_response(HTTPStatus.NOT_FOUND, 'Gap responses not found', ResultCode.INVALID_INPUT)

    return _json_response(
        HTTPStatus.OK,
        {
            'job_id': job_id,
            'responses': item.get('responses') or [],
            'updated_at': item.get('updated_at'),
        },
    )


def _parse_body(event: dict[str, Any]) -> dict[str, Any] | None:
    body = event.get('body')
    if body is None:
        return {}
    if isinstance(body, dict):
        return body
    if isinstance(body, str):
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, dict):
            return parsed
        return None
    return None


def _extract_user_id(event: dict[str, Any]) -> str | None:
    return extract_user_id(event)


def _build_user_cv_prompt_payload(cv_id: str, focus_areas: list[str]) -> dict[str, Any]:
    return {
        'personal_info': {'full_name': 'Candidate'},
        'skills': focus_areas,
        'work_experience': [{'company': 'Current Company', 'role': 'Engineer', 'cv_id': cv_id}],
    }


def _build_job_prompt_payload(job_id: str, focus_areas: list[str]) -> dict[str, Any]:
    return {
        'company_name': f'Company for {job_id}',
        'role_title': f'Role for {job_id}',
        'requirements': focus_areas or ['Core competency'],
        'responsibilities': ['Deliver measurable business impact'],
    }


def _extract_job_id(event: dict[str, Any]) -> str | None:
    path_parameters = event.get('pathParameters')
    if isinstance(path_parameters, dict):
        for key in ('jobId', 'job_id'):
            value = path_parameters.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    path = str(event.get('path', '')).strip('/')
    if not path:
        return None

    parts = path.split('/')
    if len(parts) >= 3 and parts[0] == 'gap-analysis':
        if parts[1] in {'questions', 'responses'}:
            return parts[2]
        if len(parts) >= 3 and parts[2] in {'questions', 'responses'}:
            return parts[1]
    return None


def _is_get_questions_path(path: str) -> bool:
    if path.startswith('/gap-analysis/questions/'):
        return True

    parts = path.strip('/').split('/')
    return len(parts) == 3 and parts[0] == 'gap-analysis' and parts[2] == 'questions'


def _is_get_responses_path(path: str) -> bool:
    return path.startswith('/gap-analysis/responses/')


def _coerce_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _normalize_max_questions(value: Any) -> int:
    default_questions = 10
    max_allowed = 10
    if value is None:
        return default_questions
    try:
        parsed_value = int(value)
    except (TypeError, ValueError):
        return default_questions
    return max(1, min(parsed_value, max_allowed))


def _normalize_focus_areas(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized = [entry.strip() for entry in value if isinstance(entry, str) and entry.strip()]
    return normalized


def _generate_gap_questions(job_id: str, focus_areas: list[str], max_questions: int) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    for index in range(max_questions):
        focus_area = focus_areas[index] if index < len(focus_areas) else f'core competency {index + 1}'
        questions.append(
            {
                'id': f'gap-q{index + 1}',
                'text': f'What quantifiable examples show your impact in {focus_area} for job {job_id}?',
                'tags': [focus_area],
                'strategic_intent': 'Capture evidence-backed achievements for interview readiness.',
                'evidence_gap': f'Need stronger measurable evidence for {focus_area}.',
            }
        )
    return questions


def _build_missing_qualifications(focus_areas: list[str]) -> list[dict[str, str]]:
    if not focus_areas:
        return []
    return [{'skill': focus_area, 'priority': 'MEDIUM'} for focus_area in focus_areas]


def _normalize_submitted_responses(
    raw_responses: Any,
) -> tuple[list[dict[str, Any]], dict[str, str] | None]:
    if not isinstance(raw_responses, list) or not raw_responses:
        return [], {'message': 'responses must be a non-empty array', 'code': ResultCode.MISSING_REQUIRED_FIELD}

    normalized_responses: list[dict[str, Any]] = []
    for index, entry in enumerate(raw_responses):
        normalized, validation_error = _normalize_submitted_response_entry(entry, index=index)
        if validation_error is not None:
            return [], validation_error
        normalized_responses.append(normalized)
    return normalized_responses, None


def _normalize_submitted_response_entry(
    entry: Any,
    index: int,
) -> tuple[dict[str, Any], dict[str, str] | None]:
    if not isinstance(entry, dict):
        return {}, {'message': f'response at index {index} must be an object', 'code': ResultCode.VALIDATION_ERROR}

    question_id = _coerce_str(entry.get('question_id'))
    response_text = _coerce_str(entry.get('response') or entry.get('answer'))
    if not question_id or not response_text:
        return {}, {
            'message': f'response at index {index} must include question_id and response',
            'code': ResultCode.MISSING_REQUIRED_FIELD,
        }

    normalized: dict[str, Any] = {'question_id': question_id, 'response': response_text}
    quantifiable_data = entry.get('quantifiable_data')
    if isinstance(quantifiable_data, dict):
        normalized['quantifiable_data'] = quantifiable_data

    tags = entry.get('tags')
    if isinstance(tags, list):
        cleaned_tags = [str(tag).strip() for tag in tags if isinstance(tag, str) and tag.strip()]
        if cleaned_tags:
            normalized['tags'] = cleaned_tags
    return normalized, None


def _item_matches_job(item: dict[str, Any], job_id: str) -> bool:
    # Check job_id attribute directly (preferred method)
    stored_job_id = item.get('job_id')
    if isinstance(stored_job_id, str) and stored_job_id == job_id:
        return True
    # Check applicationId format: GAP_ANALYSIS#{cv_id}#{job_id} or GAP_RESPONSES#{job_id}
    application_id = str(item.get('applicationId', ''))
    return application_id.endswith(f'#{job_id}') or application_id == f'GAP_RESPONSES#{job_id}'


def _item_timestamp(item: dict[str, Any]) -> str:
    updated = item.get('updated_at')
    if isinstance(updated, str):
        return updated
    created = item.get('created_at')
    if isinstance(created, str):
        return created
    return ''


def _build_gap_responses_application_id(job_id: str) -> str:
    return f'GAP_RESPONSES#{job_id}'


def _build_gap_questions_application_id(cv_id: str, job_id: str) -> str:
    return f'GAP_ANALYSIS#{cv_id}#{job_id}'


def _ttl_timestamp(ttl_days: int = 90) -> int:
    now = datetime.now(timezone.utc)
    return int((now + timedelta(days=ttl_days)).timestamp())


def _get_table() -> Any:
    import boto3

    table_name = os.getenv('DYNAMODB_TABLE_NAME')
    if not table_name:
        raise RuntimeError('DYNAMODB_TABLE_NAME environment variable is required')
    return boto3.resource('dynamodb').Table(table_name)


__all__ = ['lambda_handler', 'generate_questions', 'get_questions', 'submit_response', 'get_responses']
