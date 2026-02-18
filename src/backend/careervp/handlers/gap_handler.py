"""Gap analysis handler with question/response retrieval and persistence."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from typing import Any

try:  # pragma: no cover - import guard for lightweight unit-test environments.
    from botocore.exceptions import ClientError
except Exception:  # noqa: BLE001
    ClientError = Exception  # type: ignore[assignment]

from careervp.models.result import ResultCode

QUESTION_ARTIFACT_PREFIX = 'ARTIFACT#GAP_ANALYSIS#'
RESPONSE_ARTIFACT_PREFIX = 'ARTIFACT#GAP_RESPONSES#'


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    _ = context
    method = str(event.get('httpMethod', '')).upper()
    path = str(event.get('path', '')).rstrip('/')

    if method == 'OPTIONS':
        return _json_response(HTTPStatus.OK, {'status': 'ok'})

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


def get_questions(event: dict[str, Any]) -> dict[str, Any]:
    user_id = _extract_user_id(event)
    if not user_id:
        return _error_response(HTTPStatus.UNAUTHORIZED, 'Missing user identity', ResultCode.UNAUTHORIZED)

    job_id = _extract_job_id(event)
    if not job_id:
        return _error_response(HTTPStatus.BAD_REQUEST, 'Missing jobId path parameter', ResultCode.MISSING_REQUIRED_FIELD)

    try:
        table = _get_table()
        condition = _build_question_query_condition(user_id)
        response = table.query(KeyConditionExpression=condition)
        items = list(response.get('Items', []))
        while 'LastEvaluatedKey' in response:
            response = table.query(
                KeyConditionExpression=condition,
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

    user_id = _extract_user_id(event) or _coerce_str(payload.get('user_id'))
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
    item: dict[str, Any] = {
        'pk': user_id,
        'sk': _build_gap_responses_sort_key(job_id),
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
        HTTPStatus.OK,
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
        response = _get_table().get_item(Key={'pk': user_id, 'sk': _build_gap_responses_sort_key(job_id)})
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
    return _extract_user_id_from_authorizer(event) or _extract_user_id_from_headers(event)


def _extract_claim_user_id(claims: Any) -> str | None:
    if not isinstance(claims, dict):
        return None
    for key in ('sub', 'user_id', 'cognito:username'):
        value = claims.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_user_id_from_authorizer(event: dict[str, Any]) -> str | None:
    request_context = event.get('requestContext')
    if not isinstance(request_context, dict):
        return None

    authorizer = request_context.get('authorizer')
    if not isinstance(authorizer, dict):
        return None

    claims = authorizer.get('claims')
    claim_user_id = _extract_claim_user_id(claims)
    if claim_user_id:
        return claim_user_id

    jwt_context = authorizer.get('jwt')
    if isinstance(jwt_context, dict):
        jwt_claims = jwt_context.get('claims')
        jwt_user_id = _extract_claim_user_id(jwt_claims)
        if jwt_user_id:
            return jwt_user_id

    for key in ('user_id', 'principalId', 'principal_id'):
        direct = authorizer.get(key)
        if isinstance(direct, str) and direct.strip():
            return direct.strip()
    return None


def _extract_user_id_from_headers(event: dict[str, Any]) -> str | None:
    headers = event.get('headers')
    if not isinstance(headers, dict):
        return None
    for key, value in headers.items():
        if isinstance(key, str) and key.lower() == 'x-user-id' and isinstance(value, str) and value.strip():
            return value.strip()
    return None


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
    stored_job_id = item.get('job_id')
    if isinstance(stored_job_id, str) and stored_job_id == job_id:
        return True
    sort_key = str(item.get('sk', ''))
    return sort_key.endswith(f'#{job_id}')


def _item_timestamp(item: dict[str, Any]) -> str:
    updated = item.get('updated_at')
    if isinstance(updated, str):
        return updated
    created = item.get('created_at')
    if isinstance(created, str):
        return created
    return ''


def _build_gap_responses_sort_key(job_id: str) -> str:
    return f'{RESPONSE_ARTIFACT_PREFIX}{job_id}'


def _build_question_query_condition(user_id: str) -> Any:
    try:
        from boto3.dynamodb.conditions import Key
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError('boto3 is required for gap questions query') from exc

    return Key('pk').eq(user_id) & Key('sk').begins_with(QUESTION_ARTIFACT_PREFIX)


def _ttl_timestamp(ttl_days: int = 90) -> int:
    now = datetime.now(timezone.utc)
    return int((now + timedelta(days=ttl_days)).timestamp())


def _get_table() -> Any:
    import boto3

    table_name = os.getenv('DYNAMODB_TABLE_NAME')
    if not table_name:
        raise RuntimeError('DYNAMODB_TABLE_NAME environment variable is required')
    return boto3.resource('dynamodb').Table(table_name)


__all__ = ['lambda_handler', 'get_questions', 'submit_response', 'get_responses']
