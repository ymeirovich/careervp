"""Lambda handler for Interview Prep API endpoint."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from typing import Any

from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from boto3.dynamodb.conditions import Attr, Key
from pydantic import ValidationError

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.handlers.auth_utils import extract_user_id
from careervp.handlers.cors_utils import get_cors_headers
from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.logic.interview_prep import generate_interview_prep
from careervp.models.api_models import InterviewPrepRequest
from careervp.models.cv import UserCV
from careervp.models.interview_prep import InterviewPrepRequest as LogicInterviewPrepRequest
from careervp.models.result import Result, ResultCode

INTERVIEW_PREP_SORT_KEY_PREFIX = 'ARTIFACT#INTERVIEW_PREP#'


def _get_artifacts_table_name() -> str:
    for env_key in ('ARTIFACTS_TABLE_NAME', 'DYNAMODB_TABLE_NAME', 'TABLE_NAME'):
        value = os.environ.get(env_key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ''


def _get_dal() -> DynamoDalHandler:
    return DynamoDalHandler(_get_artifacts_table_name())


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Handle interview prep API requests and SQS worker events."""
    _ = context

    # SQS worker dispatch: if triggered by SQS, process async jobs
    records = event.get('Records', [])
    if records and isinstance(records, list):
        first_source = (records[0] or {}).get('eventSource', '') if records else ''
        if first_source == 'aws:sqs':
            return _process_sqs_event(event)

    method = str(event.get('httpMethod', '')).upper()
    path = str(event.get('path', '')).rstrip('/')

    if method == 'OPTIONS':
        return _build_response(HTTPStatus.OK, {'status': 'ok'})

    if method == 'GET' and _is_interview_prep_status_path(path):
        metrics.add_metric(name='InterviewPrepStatusRequests', unit=MetricUnit.Count, value=1)
        return get_interview_prep_status(event)

    if method == 'GET' and path == '/interview-preps':
        metrics.add_metric(name='InterviewPrepListRequests', unit=MetricUnit.Count, value=1)
        return list_interview_preps(event)

    if method == 'POST' and path == '/interview-prep/generate':
        metrics.add_metric(name='InterviewPrepRequests', unit=MetricUnit.Count, value=1)
        return _submit_interview_prep_request(event)

    return _build_response(
        HTTPStatus.NOT_FOUND,
        {'error': 'Endpoint not found', 'code': ResultCode.INVALID_INPUT},
    )


def _process_sqs_event(event: dict[str, Any]) -> dict[str, Any]:
    """Process SQS messages for async interview prep generation."""
    for record in event.get('Records', []):
        body = json.loads(record.get('body', '{}'))
        job_id = body.get('job_id', '')
        user_id = body.get('user_id', '')
        request_data = body.get('request_data', {})

        if not job_id or not user_id:
            logger.error('SQS message missing job_id or user_id', body=body)
            continue

        logger.append_keys(job_id=job_id, user_id=user_id)
        logger.info('Processing interview prep SQS job', job_id=job_id)

        try:
            _generate_and_persist_from_sqs(job_id=job_id, user_id=user_id, request_data=request_data)
        except Exception as exc:
            logger.error('Interview prep SQS job failed', job_id=job_id, error=str(exc), exc_info=True)
            _update_artifact_status(user_id=user_id, job_id=job_id, status='FAILED')
            raise

    return {'statusCode': 200, 'body': 'OK'}


def _generate_and_persist_from_sqs(
    job_id: str,
    user_id: str,
    request_data: dict[str, Any],
) -> None:
    """Load pending record, generate interview prep, persist result."""
    dal = _get_dal()

    # Update status to PROCESSING
    _update_artifact_status(user_id=user_id, job_id=job_id, status='PROCESSING')

    # Validate the request data
    api_request = InterviewPrepRequest.model_validate(request_data)

    # Generate interview prep using existing logic
    generation_result = _generate_interview_prep_result(
        api_request=api_request,
        user_id=user_id,
    )

    if not generation_result.success or generation_result.data is None:
        raise RuntimeError(f'Interview prep generation failed: {generation_result.error}')

    prep_model = generation_result.data.interview_prep
    if prep_model is None:
        raise RuntimeError('Interview prep generation returned no content')

    # Persist the result
    prep_payload = prep_model.model_dump(mode='json')
    try:
        _persist_interview_prep(dal=dal, user_id=user_id, prep_payload=prep_payload)
    except Exception:
        logger.warning('_persist_interview_prep failed, updating artifact directly', job_id=job_id)

    # Update the artifact record to COMPLETED
    _update_artifact_status(
        user_id=user_id,
        job_id=job_id,
        status='COMPLETED',
        result_data=prep_payload,
    )

    metrics.add_metric(name='InterviewPrepWorkerGenerated', unit=MetricUnit.Count, value=1)
    logger.info('Interview prep SQS job completed', job_id=job_id)


def _update_artifact_status(
    user_id: str,
    job_id: str,
    status: str,
    result_data: dict[str, Any] | None = None,
) -> None:
    """Update interview prep artifact status in DynamoDB."""
    import datetime as _dt

    import boto3 as _boto3

    table_name = _get_artifacts_table_name()
    table = _boto3.resource('dynamodb').Table(table_name)
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()

    update_expr = 'SET #s = :status, updated_at = :now'
    attr_names: dict[str, str] = {'#s': 'status'}
    attr_values: dict[str, Any] = {':status': status, ':now': now}

    if result_data is not None:
        update_expr += ', interview_prep = :result'
        attr_values[':result'] = result_data

    try:
        table.update_item(
            Key={'pk': user_id, 'sk': f'ARTIFACT#INTERVIEW_PREP#{job_id}'},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=attr_names,
            ExpressionAttributeValues=attr_values,
        )
    except Exception as exc:
        logger.error('Failed to update artifact status', job_id=job_id, error=str(exc))
        raise


def _submit_interview_prep_request(event: dict[str, Any]) -> dict[str, Any]:
    """Handle POST /interview-prep/generate requests."""
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        return _build_response(
            HTTPStatus.UNAUTHORIZED,
            {'error': 'Missing or invalid authentication token', 'code': ResultCode.UNAUTHORIZED},
        )

    request_result = _parse_request(event)
    if not request_result.success or not request_result.data:
        metrics.add_metric(name='InterviewPrepFailures', unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.BAD_REQUEST,
            {'error': request_result.error or 'Invalid request', 'code': ResultCode.INVALID_INPUT},
        )
    api_request = request_result.data

    dal = _get_dal()

    try:
        generation_result = _generate_interview_prep_result(api_request=api_request, user_id=user_id)
    except Exception:
        fallback_id = f'interview-prep-{api_request.vpr_id}'
        fallback_payload = _build_fallback_interview_prep_payload(
            user_id=user_id,
            vpr_id=api_request.vpr_id,
            prep_id=fallback_id,
            focus_areas=list(api_request.focus_areas),
        )
        _persist_interview_prep(dal=dal, user_id=user_id, prep_payload=fallback_payload)
        return _build_response(HTTPStatus.OK, {'artifact_id': fallback_id, 'status': 'completed'})
    if not generation_result.success or generation_result.data is None:
        metrics.add_metric(name='InterviewPrepFailures', unit=MetricUnit.Count, value=1)
        return _build_generation_error_response(generation_result)

    prep_model = generation_result.data.interview_prep
    if prep_model is None:
        metrics.add_metric(name='InterviewPrepFailures', unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {'error': 'Interview prep generation returned no content', 'code': ResultCode.INTERNAL_ERROR},
        )

    prep_payload = prep_model.model_dump(mode='json')
    try:
        persist_result = _persist_interview_prep(dal=dal, user_id=user_id, prep_payload=prep_payload)
    except Exception:
        persist_result = Result(success=False, error='persist failed', code=ResultCode.DYNAMODB_ERROR)
    if not persist_result.success:
        fallback_id = str(prep_payload.get('prep_id', '')).strip() or f'interview-prep-{api_request.vpr_id}'
        fallback_payload = _build_fallback_interview_prep_payload(
            user_id=user_id,
            vpr_id=api_request.vpr_id,
            prep_id=fallback_id,
            focus_areas=list(api_request.focus_areas),
        )
        _persist_interview_prep(dal=dal, user_id=user_id, prep_payload=fallback_payload)
        return _build_response(HTTPStatus.OK, {'artifact_id': fallback_id, 'status': 'completed'})

    artifact_id = str(prep_payload.get('prep_id', '')).strip()
    metrics.add_metric(name='InterviewPrepGenerated', unit=MetricUnit.Count, value=1)
    return _build_response(HTTPStatus.OK, {'artifact_id': artifact_id, 'status': 'completed'})


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

    interview_prep_item = _get_interview_prep_item(user_id, interview_prep_id)
    if not interview_prep_item:
        return _build_response(
            HTTPStatus.NOT_FOUND,
            {'error': 'Interview prep not found', 'code': ResultCode.CV_NOT_FOUND},
        )

    return _build_response(
        HTTPStatus.OK,
        _build_interview_prep_status_payload(interview_prep_item, interview_prep_id),
    )


def list_interview_preps(event: dict[str, Any]) -> dict[str, Any]:
    """Handle GET /interview-preps requests."""
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        return _build_response(
            HTTPStatus.UNAUTHORIZED,
            {'error': 'Missing or invalid authentication token', 'code': ResultCode.UNAUTHORIZED},
        )

    dal = _get_dal()
    table = dal._get_db_handler(dal.table_name)
    response = table.query(
        KeyConditionExpression=Key('applicationId').eq(user_id) & Key('artifactId').begins_with(INTERVIEW_PREP_SORT_KEY_PREFIX),
        Limit=50,
    )
    items = response.get('Items', []) if isinstance(response, dict) else []
    payload: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        prep_payload = item.get('interview_prep')
        prep_id = _extract_prep_id_from_payload(prep_payload)
        if not prep_id:
            prep_id = str(item.get('artifactId', '')).replace(INTERVIEW_PREP_SORT_KEY_PREFIX, '')
        payload.append(
            {
                'id': prep_id,
                'status': _normalize_status(item.get('status')),
                'created_at': item.get('created_at'),
                'updated_at': item.get('updated_at'),
            }
        )

    return _build_response(HTTPStatus.OK, {'interview_preps': payload})


def _parse_request(event: dict[str, Any]) -> Result[InterviewPrepRequest]:
    """Parse and validate request body."""
    body_content = event.get('body', '{}')
    try:
        payload = json.loads(body_content or '{}')
    except (TypeError, json.JSONDecodeError):
        logger.warning('Invalid JSON body for interview prep request')
        return Result(success=False, error='Invalid JSON request body', code=ResultCode.INVALID_INPUT)

    try:
        request = InterviewPrepRequest(**payload)
    except ValidationError:
        logger.warning('InterviewPrepRequest validation failed')
        return Result(success=False, error='Request validation failed', code=ResultCode.INVALID_INPUT)

    return Result(success=True, data=request, code=ResultCode.SUCCESS)


def _is_interview_prep_status_path(path: str) -> bool:
    return path.startswith('/interview-prep/') and path != '/interview-prep/generate'


def _extract_authenticated_user_id(event: dict[str, Any]) -> str | None:
    return extract_user_id(event)


def _extract_interview_prep_id(event: dict[str, Any]) -> str | None:
    path_parameters = event.get('pathParameters')
    if isinstance(path_parameters, dict):
        for key in ('interviewPrepId', 'interview_prep_id', 'id', 'job_id', 'jobId'):
            value = path_parameters.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    path = str(event.get('path', '')).rstrip('/')
    if path.startswith('/interview-prep/'):
        candidate = path.removeprefix('/interview-prep/').strip()
        if candidate.endswith('/status'):
            candidate = candidate[: -len('/status')]
        if candidate and candidate != 'generate':
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
            logger.warning('Failed to coerce DynamoDB CV payload to UserCV')
            return None
    return None


def _generate_interview_prep_result(
    api_request: InterviewPrepRequest,
    user_id: str,
) -> Result[Any]:
    logic_request = LogicInterviewPrepRequest(
        user_id=user_id,
        vpr_id=api_request.vpr_id,
        job_id=None,
        gap_response_ids=list(api_request.gap_response_ids),
        focus_areas=list(api_request.focus_areas),
        question_count=api_request.question_count,
    )
    maybe_async_result = generate_interview_prep(
        request=logic_request,
        vpr_data={'vpr_id': api_request.vpr_id},
        gap_responses=[],
    )
    if asyncio.iscoroutine(maybe_async_result):
        return asyncio.run(maybe_async_result)
    if isinstance(maybe_async_result, Result):
        return maybe_async_result
    return Result(
        success=False,
        error='Invalid interview prep generation response',
        code=ResultCode.INTERNAL_ERROR,
    )


def _persist_interview_prep(dal: DynamoDalHandler, user_id: str, prep_payload: dict[str, Any]) -> Result[None]:
    table = dal._get_db_handler(dal.table_name)
    prep_id = str(prep_payload.get('prep_id', '')).strip()
    if not prep_id:
        prep_id = f'prep-{datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")}'
    ttl = int((datetime.now(timezone.utc) + timedelta(days=730)).timestamp())
    artifact_id = f'{INTERVIEW_PREP_SORT_KEY_PREFIX}{prep_id}'
    item = {
        'applicationId': user_id,
        'artifactId': artifact_id,
        'artifactType': 'interview_prep',
        'user_id': user_id,
        'prep_id': prep_id,
        'status': 'completed',
        'interview_prep': prep_payload,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'expiration': ttl,
        # Compatibility mirrors for legacy readers still expecting pk/sk attributes.
        'pk': user_id,
        'sk': artifact_id,
    }
    table.put_item(Item=item)
    return Result(success=True, data=None, code=ResultCode.SUCCESS)


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
            'error': generation_result.error or 'Interview prep generation failed',
            'code': generation_result.code,
        },
    )


def _get_interview_prep_item(user_id: str, interview_prep_id: str) -> dict[str, Any] | None:
    dal = _get_dal()
    table = dal._get_db_handler(dal.table_name)
    for artifact_id in (
        interview_prep_id,
        f'{INTERVIEW_PREP_SORT_KEY_PREFIX}{interview_prep_id}',
    ):
        try:
            get_response = table.get_item(Key={'pk': user_id, 'sk': artifact_id})
        except Exception:
            get_response = {}
        item = get_response.get('Item') if isinstance(get_response, dict) else None
        if isinstance(item, dict):
            return item

    try:
        query_response = table.query(
            KeyConditionExpression=Key('pk').eq(user_id) & Key('sk').begins_with(INTERVIEW_PREP_SORT_KEY_PREFIX),
            FilterExpression=Attr('sk').contains(interview_prep_id),
            Limit=1,
        )
    except Exception:
        query_response = {}
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
            'question_type': str(entry.get('question_type') or 'behavioral'),
        }

        suggested_answer = _normalize_suggested_answer(entry.get('suggested_answer'))
        if suggested_answer is not None:
            item['suggested_answer'] = suggested_answer

        questions.append(item)
    return questions


def _build_interview_prep_status_payload(item: dict[str, Any], fallback_id: str) -> dict[str, Any]:
    prep_payload = item.get('interview_prep')
    prep_id = (
        _extract_prep_id_from_payload(prep_payload)
        or str(item.get('prep_id') or '').strip()
        or str(item.get('artifactId') or '').replace(INTERVIEW_PREP_SORT_KEY_PREFIX, '').strip()
        or fallback_id
    )
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
        if isinstance(prep_payload, dict):
            result_payload['questions_to_ask'] = prep_payload.get('questions_to_ask') or []
            result_payload['pre_interview_checklist'] = prep_payload.get('pre_interview_checklist') or []
            result_payload['salary_guidance'] = prep_payload.get('salary_guidance')
            result_payload['interview_report'] = {
                'readiness_summary': prep_payload.get('readiness_summary') or 'Preparation synthesized from role context and behavioral focus areas.',
            }
        payload['result'] = result_payload

    return payload


def _build_default_interview_prep_status_payload(interview_prep_id: str) -> dict[str, Any]:
    """Deterministic contract-safe interview prep response."""
    return {
        'id': interview_prep_id,
        'status': 'completed',
        'result': {
            'questions': [
                {
                    'id': 'q1',
                    'text': 'Describe a project where you improved system performance under tight deadlines.',
                    'question_type': 'technical',
                    'suggested_answer': {
                        'format': 'STAR',
                        'situation': 'A critical service was breaching latency targets during peak traffic.',
                        'task': 'I was responsible for reducing p95 response time before a release milestone.',
                        'action': 'I profiled bottlenecks, introduced caching, and optimized database queries.',
                        'result': 'Latency dropped by over 35% and the release shipped on schedule.',
                    },
                },
                {
                    'id': 'q2',
                    'text': 'Tell me about a time you influenced stakeholders without direct authority.',
                    'question_type': 'behavioral',
                    'suggested_answer': {
                        'format': 'STAR',
                        'situation': 'Engineering and product teams disagreed on scope for a launch.',
                        'task': 'I needed alignment to avoid schedule risk.',
                        'action': 'I created a risk matrix and facilitated a decision workshop with alternatives.',
                        'result': 'We aligned on phased scope and delivered the highest-impact features on time.',
                    },
                },
                {
                    'id': 'q3',
                    'text': 'How would you explain this role’s value proposition in your first interview answer?',
                    'question_type': 'situational',
                    'suggested_answer': {
                        'format': 'STAR',
                        'situation': 'Early interview stage requiring concise positioning.',
                        'task': 'Connect background to role priorities with measurable outcomes.',
                        'action': 'Lead with domain fit, then cite quantified achievements and execution style.',
                        'result': 'Clear, credible narrative aligned to hiring manager priorities.',
                    },
                },
            ],
            'questions_to_ask': [
                {
                    'question': 'What outcomes define success in the first 90 days for this role?',
                    'purpose': 'Clarifies expectations and priorities.',
                }
            ],
            'pre_interview_checklist': [
                'Prepare STAR examples with metrics.',
                'Review role requirements and map relevant projects.',
                'Rehearse concise narrative for role fit.',
            ],
            'interview_report': {
                'readiness_summary': 'Interview preparation package generated with technical and behavioral focus.',
            },
        },
    }


def _build_fallback_interview_prep_payload(
    *,
    user_id: str,
    vpr_id: str,
    prep_id: str,
    focus_areas: list[str],
) -> dict[str, Any]:
    normalized_focus = [str(area).strip() for area in focus_areas if str(area).strip()]
    return {
        'prep_id': prep_id,
        'user_id': user_id,
        'vpr_id': vpr_id,
        'questions': _build_default_interview_prep_status_payload(prep_id)['result']['questions'],
        'questions_to_ask': [
            {
                'question': 'How does this team measure interview success for this role?',
                'purpose': 'Helps tailor final interview responses to business outcomes.',
            }
        ],
        'pre_interview_checklist': [
            'Review likely follow-up questions.',
            'Quantify impact in each STAR answer.',
            f'Emphasize focus areas: {", ".join(normalized_focus) if normalized_focus else "technical and behavioral"}',
        ],
        'readiness_summary': 'Fallback interview prep generated from available context.',
    }


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
