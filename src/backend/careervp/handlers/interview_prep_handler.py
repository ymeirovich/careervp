"""Lambda handler for Interview Prep API endpoint."""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any

from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from boto3.dynamodb.conditions import Attr, Key
from pydantic import ValidationError

from careervp.dal.cv_dal import CVTable
from careervp.handlers.auth_utils import extract_user_id
from careervp.handlers.cors_utils import get_cors_headers
from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.models.interview_prep import InterviewPrepRequest
from careervp.models.result import Result, ResultCode

INTERVIEW_PREP_SORT_KEY_PREFIX = 'ARTIFACT#INTERVIEW_PREP#'


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Handle interview prep API requests."""
    _ = context
    method = str(event.get('httpMethod', '')).upper()
    path = str(event.get('path', '')).rstrip('/')

    if method == 'OPTIONS':
        return _build_response(HTTPStatus.OK, {'status': 'ok'})

    if method == 'GET' and _is_interview_prep_status_path(path):
        metrics.add_metric(name='InterviewPrepStatusRequests', unit=MetricUnit.Count, value=1)
        return get_interview_prep_status(event)

    if method == 'POST' and path == '/interview-prep/generate':
        metrics.add_metric(name='InterviewPrepRequests', unit=MetricUnit.Count, value=1)
        return _submit_interview_prep_request(event)

    return _build_response(
        HTTPStatus.NOT_FOUND,
        {'error': 'Endpoint not found', 'code': ResultCode.INVALID_INPUT},
    )


def _submit_interview_prep_request(event: dict[str, Any]) -> dict[str, Any]:
    """Handle POST /interview-prep/generate requests."""
    request_result = _parse_request(event)
    if not request_result.success or not request_result.data:
        metrics.add_metric(name='InterviewPrepFailures', unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.BAD_REQUEST,
            {'error': request_result.error or 'Invalid request', 'code': ResultCode.INVALID_INPUT},
        )

    request_id = request_result.data.vpr_id
    metrics.add_metric(name='InterviewPrepSubmitted', unit=MetricUnit.Count, value=1)

    return _build_response(
        HTTPStatus.ACCEPTED,
        {
            'request_id': request_id,
            'status': 'processing',
        },
    )


def get_interview_prep_status(event: dict[str, Any]) -> dict[str, Any]:
    """Handle GET /interview-prep/{interviewPrepId} requests."""
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        return _build_response(
            HTTPStatus.UNAUTHORIZED,
            {'error': 'Missing or invalid authentication token', 'code': ResultCode.UNAUTHORIZED},
        )

    interview_prep_id = _extract_interview_prep_id(event)
    if not interview_prep_id:
        return _build_response(
            HTTPStatus.BAD_REQUEST,
            {'error': 'Missing interviewPrepId path parameter', 'code': ResultCode.MISSING_REQUIRED_FIELD},
        )

    item = _get_interview_prep_item(user_id=user_id, interview_prep_id=interview_prep_id)
    if item is None:
        return _build_response(
            HTTPStatus.NOT_FOUND,
            {'error': 'Interview prep not found', 'code': ResultCode.INVALID_INPUT},
        )

    return _build_response(HTTPStatus.OK, _build_interview_prep_status_payload(item=item, fallback_id=interview_prep_id))


def _parse_request(event: dict[str, Any]) -> Result[InterviewPrepRequest]:
    """Parse and validate request body."""
    body_content = event.get('body', '{}')
    try:
        payload = json.loads(body_content or '{}')
    except (TypeError, json.JSONDecodeError) as exc:
        logger.warning('Invalid JSON body', error=str(exc))
        return Result(success=False, error='Invalid JSON request body', code=ResultCode.INVALID_INPUT)

    try:
        request = InterviewPrepRequest(**payload)
    except ValidationError as exc:
        logger.warning('InterviewPrepRequest validation failed', errors=exc.errors())
        return Result(success=False, error='Request validation failed', code=ResultCode.INVALID_INPUT)

    return Result(success=True, data=request, code=ResultCode.SUCCESS)


def _is_interview_prep_status_path(path: str) -> bool:
    return path.startswith('/interview-prep/') and path != '/interview-prep/generate'


def _extract_authenticated_user_id(event: dict[str, Any]) -> str | None:
    return extract_user_id(event)


def _extract_interview_prep_id(event: dict[str, Any]) -> str | None:
    path_parameters = event.get('pathParameters')
    if isinstance(path_parameters, dict):
        for key in ('interviewPrepId', 'interview_prep_id', 'id'):
            value = path_parameters.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    path = str(event.get('path', '')).rstrip('/')
    if path.startswith('/interview-prep/'):
        candidate = path.removeprefix('/interview-prep/').strip()
        if candidate and candidate != 'generate':
            return candidate
    return None


def _get_interview_prep_item(user_id: str, interview_prep_id: str) -> dict[str, Any] | None:
    table = CVTable().table
    get_response = table.get_item(Key={'pk': user_id, 'sk': interview_prep_id})
    item = get_response.get('Item') if isinstance(get_response, dict) else None
    if isinstance(item, dict):
        return item

    query_response = table.query(
        KeyConditionExpression=Key('pk').eq(user_id) & Key('sk').begins_with(INTERVIEW_PREP_SORT_KEY_PREFIX),
        FilterExpression=Attr('sk').contains(interview_prep_id),
        Limit=1,
    )
    query_items = query_response.get('Items') if isinstance(query_response, dict) else None
    if isinstance(query_items, list) and query_items and isinstance(query_items[0], dict):
        return query_items[0]
    return None


def _normalize_status(raw_status: Any) -> str:
    status = str(raw_status or '').strip().lower()
    if status in {'pending', 'processing', 'completed', 'failed'}:
        return status
    return 'completed'


def _extract_prep_id_from_payload(prep_payload: Any) -> str | None:
    if not isinstance(prep_payload, dict):
        return None
    for key in ('prep_id', 'id', 'interview_prep_id'):
        value = prep_payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _normalize_suggested_answer(raw_answer: Any) -> dict[str, Any] | None:
    if not isinstance(raw_answer, dict):
        return None

    suggested: dict[str, Any] = {'format': str(raw_answer.get('format') or 'STAR')}
    for key in ('situation', 'task', 'action', 'result'):
        value = raw_answer.get(key)
        if isinstance(value, str):
            suggested[key] = value
    return suggested


def _normalize_questions(raw_questions: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_questions, list):
        return []

    questions: list[dict[str, Any]] = []
    for index, entry in enumerate(raw_questions):
        if not isinstance(entry, dict):
            continue

        question_id = str(entry.get('question_id') or entry.get('id') or f'q{index + 1}')
        question_text = str(entry.get('question') or entry.get('text') or '')

        item: dict[str, Any] = {
            'id': question_id,
            'text': question_text,
        }

        suggested_answer = _normalize_suggested_answer(entry.get('suggested_answer'))
        if suggested_answer is not None:
            item['suggested_answer'] = suggested_answer

        questions.append(item)
    return questions


def _build_interview_prep_status_payload(item: dict[str, Any], fallback_id: str) -> dict[str, Any]:
    prep_payload = item.get('interview_prep')
    prep_id = _extract_prep_id_from_payload(prep_payload) or (str(item.get('sk')).strip() if item.get('sk') else '') or fallback_id
    status = _normalize_status(item.get('status'))

    payload: dict[str, Any] = {
        'id': prep_id,
        'status': status,
    }

    if status in {'completed', 'failed'}:
        raw_questions = None
        if isinstance(prep_payload, dict):
            raw_questions = prep_payload.get('questions')
        if raw_questions is None:
            raw_questions = item.get('questions')

        result_payload: dict[str, Any] = {
            'questions': _normalize_questions(raw_questions),
        }
        payload['result'] = result_payload

    return payload


def _build_response(status_code: HTTPStatus, body: dict[str, Any]) -> dict[str, Any]:
    """Build API Gateway response."""
    headers = get_cors_headers(None)
    headers['Content-Type'] = 'application/json'
    return {
        'statusCode': status_code.value,
        'headers': headers,
        'body': json.dumps(body, default=str),
    }


__all__ = ['lambda_handler']
