"""Gap analysis handler with question/response retrieval and persistence."""

from __future__ import annotations

import asyncio
import json
import os
from http import HTTPStatus
from typing import Any

from pydantic import ValidationError

from careervp.dal.application_repository import ApplicationRepository
from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.handlers.auth_utils import extract_user_id
from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.logic.gap_analysis import generate_gap_questions
from careervp.logic.trial_service import TrialExhaustedException, TrialExpiredException, TrialService
from careervp.models.api_models import GapQuestionRequest, GapResponseRequest
from careervp.models.result import Result, ResultCode

_trial_service: TrialService | None = None
_application_repository: ApplicationRepository | None = None
_current_request_origin: str | None = None


def _resolve_table_name(*env_keys: str) -> str:
    for env_key in env_keys:
        value = os.getenv(env_key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise RuntimeError(f'Missing required table configuration: {", ".join(env_keys)}')


def _configuration_error_response() -> dict[str, Any]:
    return _error_response(HTTPStatus.INTERNAL_SERVER_ERROR, 'Internal server error', ResultCode.MISSING_ENV)


def _get_questions_dal() -> DynamoDalHandler:
    """DAL for gap questions — stored in the users table (pk/sk key schema)."""
    table_name = _resolve_table_name('USERS_TABLE_NAME', 'DYNAMODB_TABLE_NAME', 'TABLE_NAME')
    return DynamoDalHandler(table_name=table_name)


def _get_responses_dal() -> DynamoDalHandler:
    """DAL for gap responses — stored in the dedicated gap_responses table."""
    table_name = _resolve_table_name('GAP_RESPONSES_TABLE_NAME')
    # Schema validation removed - keys (userId/questionId) confirmed correct in code
    return DynamoDalHandler(table_name=table_name)


@logger.inject_lambda_context(log_event=False)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    global _current_request_origin
    _headers = event.get('headers') or {}
    _current_request_origin = _headers.get('origin') or _headers.get('Origin')
    method = str(event.get('httpMethod', '')).upper()
    path = str(event.get('path', '')).rstrip('/')

    if method == 'OPTIONS':
        return _json_response(HTTPStatus.OK, {'status': 'ok'})

    if method == 'POST' and (path == '/gap-analysis/questions' or _is_post_questions_path(path)):
        return generate_questions(event)

    if method == 'GET' and _is_get_questions_path(path):
        return get_questions(event)

    if method == 'POST' and (path == '/gap-analysis/responses' or _is_post_responses_path(path)):
        return submit_response(event)

    if method == 'GET' and _is_get_responses_path(path):
        return get_responses(event)

    return _error_response(HTTPStatus.NOT_FOUND, 'Endpoint not found', ResultCode.INVALID_INPUT)


def _cors_headers() -> dict[str, str]:
    allowed_origins_env = os.getenv('ALLOWED_ORIGINS', '')
    if allowed_origins_env:
        allowed = {o.strip() for o in allowed_origins_env.split(',') if o.strip()}
        origin = _current_request_origin if _current_request_origin in allowed else 'null'
    else:
        origin = '*'
    return {
        'Access-Control-Allow-Origin': origin,
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


def generate_questions(event: dict[str, Any]) -> dict[str, Any]:  # noqa: C901
    payload = _parse_body(event)
    if payload is None:
        return _error_response(HTTPStatus.BAD_REQUEST, 'Invalid request body', ResultCode.INVALID_JSON)

    try:
        openapi_request = GapQuestionRequest.model_validate(
            {
                'cv_id': payload.get('cv_id'),
                'job_id': payload.get('job_id') or payload.get('application_id') or _extract_job_id(event),
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

    application_id, error_response = _prepare_trial_and_pending_state(
        payload=payload,
        user_id=user_id,
        job_id=job_id,
    )
    if error_response is not None:
        return error_response
    application_repo = _get_application_repository()

    try:
        generation_result = asyncio.run(
            generate_gap_questions(
                user_cv=user_cv,
                job_posting=job_posting,
                dal=None,
            )
        )
    except Exception as exc:
        logger.error(
            'Gap question generation failed',
            job_id=job_id,
            error=str(exc),
            exc_info=True,
        )
        return _json_response(
            HTTPStatus.SERVICE_UNAVAILABLE,
            {
                'error': 'Gap question generation failed. Please try again.',
                'detail': 'The AI service is temporarily unavailable.',
            },
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

    try:
        dal = _get_questions_dal()
        try:
            save_result = dal.save_gap_questions(
                user_id=user_id,
                cv_id=cv_id,
                job_id=job_id,
                questions=questions,
            )
        except Exception as exc:
            logger.exception('Unexpected DAL exception while saving gap questions', error=str(exc), job_id=job_id)
            save_result = Result(success=False, error='persist failed', code=ResultCode.DYNAMODB_ERROR)
        if not save_result.success:
            logger.warning(
                'Persisting gap questions failed — returning questions without caching',
                job_id=job_id,
                code=save_result.code,
                error=save_result.error,
            )
    except RuntimeError:
        logger.exception('Gap questions table not configured — returning questions without caching')

    try:
        application_repo.update_state(
            application_id=application_id,
            user_id=user_id,
            new_state='gap_questions_ready',
            expected_state='gap_questions_pending',
        )
    except Exception:
        pass

    metrics.add_metric(name='GapQuestionsGenerated', unit='Count', value=1)
    return _json_response(
        HTTPStatus.OK,
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
        dal = _get_questions_dal()
    except RuntimeError:
        logger.exception('Gap questions table configuration error')
        return _configuration_error_response()
    result = dal.list_gap_questions_by_prefix(user_id=user_id, job_id=job_id)
    if not result.success:
        return _json_response(
            HTTPStatus.OK,
            {
                'job_id': job_id,
                'cv_id': None,
                'questions': [],
            },
        )

    items = result.data or []
    if not items:
        return _json_response(
            HTTPStatus.OK,
            {
                'job_id': job_id,
                'cv_id': None,
                'questions': [],
            },
        )

    latest = max(items, key=_item_timestamp)
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

    job_id = _coerce_str(payload.get('job_id') or payload.get('application_id') or _extract_job_id(event))
    if not job_id:
        return _error_response(HTTPStatus.BAD_REQUEST, 'job_id is required', ResultCode.MISSING_REQUIRED_FIELD)

    normalized_responses, validation_error = _normalize_submitted_responses(payload.get('responses'))
    if validation_error is not None:
        return _error_response(
            HTTPStatus.BAD_REQUEST,
            validation_error['message'],
            validation_error['code'],
        )

    try:
        dal = _get_responses_dal()
    except RuntimeError:
        logger.exception('Gap responses table configuration error')
        return _configuration_error_response()
    try:
        save_result = dal.save_gap_responses_raw(
            user_id=user_id,
            job_id=job_id,
            responses=normalized_responses,
        )
    except Exception as exc:
        logger.exception('Unexpected DAL exception while saving gap responses', error=str(exc), job_id=job_id)
        save_result = Result(success=False, error='persist failed', code=ResultCode.DYNAMODB_ERROR)
    if not save_result.success:
        logger.error('Failed to persist gap responses', job_id=job_id, code=save_result.code, error=save_result.error)
        return _error_response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            'Failed to save gap responses. Please try again.',
            save_result.code,
        )

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
        dal = _get_responses_dal()
    except RuntimeError:
        logger.exception('Gap responses table configuration error')
        return _configuration_error_response()
    result = dal.get_gap_responses(user_id=user_id)
    if not result.success:
        return _error_response(HTTPStatus.INTERNAL_SERVER_ERROR, result.error or 'Failed to fetch gap responses', result.code)

    if not result.data:
        return _error_response(HTTPStatus.NOT_FOUND, 'Gap responses not found', ResultCode.INVALID_INPUT)

    responses_list = [r.model_dump(mode='json') if hasattr(r, 'model_dump') else r for r in result.data]
    return _json_response(
        HTTPStatus.OK,
        {
            'job_id': job_id,
            'responses': responses_list,
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
    if len(parts) >= 4 and parts[0] == 'jobs':
        if parts[2] in {'gap-questions', 'gap-responses'}:
            return parts[1]
    return None


def _is_get_questions_path(path: str) -> bool:
    if path.startswith('/gap-analysis/questions/'):
        return True

    parts = path.strip('/').split('/')
    if len(parts) == 3 and parts[0] == 'gap-analysis' and parts[2] == 'questions':
        return True
    return len(parts) == 3 and parts[0] == 'jobs' and parts[2] == 'gap-questions'


def _is_get_responses_path(path: str) -> bool:
    return path.startswith('/gap-analysis/responses/')


def _is_post_questions_path(path: str) -> bool:
    parts = path.strip('/').split('/')
    return len(parts) == 3 and parts[0] == 'jobs' and parts[2] == 'gap-questions'


def _is_post_responses_path(path: str) -> bool:
    parts = path.strip('/').split('/')
    return len(parts) == 3 and parts[0] == 'jobs' and parts[2] == 'gap-responses'


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


def _item_timestamp(item: dict[str, Any]) -> str:
    updated = item.get('updated_at')
    if isinstance(updated, str):
        return updated
    created = item.get('created_at')
    if isinstance(created, str):
        return created
    return ''


def _prepare_trial_and_pending_state(
    payload: dict[str, Any],
    user_id: str,
    job_id: str,
) -> tuple[str, dict[str, Any] | None]:
    trial_service = _get_trial_service()
    if trial_service is not None:
        try:
            trial_service.check_trial_status(user_id)
            trial_service.consume_credit(user_id)
        except TrialExpiredException:
            return '', _error_response(HTTPStatus.FORBIDDEN, 'Trial expired', 'trial_expired')
        except TrialExhaustedException:
            return '', _error_response(HTTPStatus.FORBIDDEN, 'Trial exhausted', 'trial_exhausted')

    application_id = _coerce_str(payload.get('application_id')) or job_id
    application_repo = _get_application_repository()
    try:
        application_repo.update_state(
            application_id=application_id,
            user_id=user_id,
            new_state='gap_questions_pending',
            expected_state='cv_selected',
        )
    except Exception:
        pass
    return application_id, None


def _get_trial_service() -> TrialService | None:
    global _trial_service
    if _trial_service is None:
        table_name = os.getenv('USERS_TABLE_NAME') or os.getenv('TABLE_NAME') or ''
        if not table_name:
            return None
        _trial_service = TrialService(dal=DynamoDalHandler(table_name=table_name))
    return _trial_service


def _get_application_repository() -> ApplicationRepository:
    global _application_repository
    if _application_repository is None:
        table_name = os.getenv('APPLICATIONS_TABLE_NAME') or os.getenv('DYNAMODB_TABLE_NAME') or os.getenv('TABLE_NAME') or ''
        if not table_name:
            raise RuntimeError('Application repository table name not configured')
        _application_repository = ApplicationRepository(dal=DynamoDalHandler(table_name=table_name))
    return _application_repository


__all__ = ['lambda_handler', 'generate_questions', 'get_questions', 'submit_response', 'get_responses']
