"""Lambda handler for Cover Letter API endpoint."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from http import HTTPStatus
from typing import Any, cast

import boto3
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from careervp.dal import table_registry
from careervp.dal.core_repository import CoreRepository
from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.dal.jobs_repository import JobsRepository
from careervp.handlers.artifact_dependency_utils import (
    dependency_response_body,
    mark_requested_artifact_pending,
    resolve_handler_dependencies,
)
from careervp.handlers.auth_utils import extract_user_id
from careervp.handlers.cors_utils import get_cors_headers, set_request_origin
from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.logic.artifact_dependency_resolver import (
    DependencyResolution,
    vpr_access_denied_envelope,
)
from careervp.logic.cancellation import CancelledBeforePersist
from careervp.logic.cover_letter import generate_cover_letter
from careervp.logic.utils.llm_metering import bind_llm_usage_context
from careervp.models.api_models import CoverLetterRequest
from careervp.models.company import CompanyResearchResult, ResearchSource
from careervp.models.cover_letter import (
    CoverLetterOptions as LogicCoverLetterOptions,
)
from careervp.models.cover_letter import (
    CoverLetterRequest as LogicCoverLetterRequest,
)
from careervp.models.cv import UserCV
from careervp.models.result import Result, ResultCode

sfn = boto3.client('stepfunctions')


def _convert_decimal_to_float(obj: Any) -> Any:
    """Recursively convert Decimal to float for JSON serialization (mirrors gap_analysis.py)."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _convert_decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_decimal_to_float(i) for i in obj]
    return obj


def _get_dal() -> DynamoDalHandler:
    table_name, resolved_from = table_registry.resolve_artifacts_table_name_with_source()
    logger.debug('Cover letter DAL table resolved', table_name=table_name, resolved_from=resolved_from)
    return DynamoDalHandler(table_name)


class _ResolvedVPRPayload:
    """Adapter for real VPR dict payloads returned by legacy storage paths."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def model_dump(self, mode: str = 'json') -> dict[str, Any]:
        _ = mode
        return self._payload


def _coerce_text(value: Any) -> str:
    return str(value or '').strip()


def _is_placeholder_context_value(value: str, *, job_id: str) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return True
    if normalized.startswith(('company for ', 'role for ', 'job description for ')):
        return True

    lowered_job_id = job_id.strip().lower()
    return bool(lowered_job_id and lowered_job_id in normalized and normalized.startswith(('company for ', 'role for ', 'job description for ')))


def _unique_non_empty(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        stripped = value.strip()
        if not stripped or stripped in seen:
            continue
        output.append(stripped)
        seen.add(stripped)
    return output


def _coerce_list_of_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    coerced: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            coerced.append(text)
    return coerced


def _coerce_optional_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
    return None


def _coerce_research_source(value: Any) -> ResearchSource:
    try:
        return ResearchSource(str(value).strip())
    except ValueError:
        return ResearchSource.WEBSITE_SCRAPE


def _coerce_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _materialize_company_research(raw_item: dict[str, Any], fallback_company_name: str) -> CompanyResearchResult | None:
    nested_payload = raw_item.get('research_data') if isinstance(raw_item.get('research_data'), dict) else raw_item.get('company_research')
    nested = nested_payload if isinstance(nested_payload, dict) else {}

    company_name = _coerce_text(raw_item.get('company_name')) or _coerce_text(nested.get('company_name')) or fallback_company_name
    overview = _coerce_text(raw_item.get('overview')) or _coerce_text(nested.get('overview')) or _coerce_text(raw_item.get('culture'))
    mission = _coerce_text(raw_item.get('mission')) or _coerce_text(nested.get('mission'))
    values = _coerce_list_of_strings(raw_item.get('values')) or _coerce_list_of_strings(nested.get('values'))
    strategic_priorities = _coerce_list_of_strings(raw_item.get('strategic_priorities')) or _coerce_list_of_strings(
        nested.get('strategic_priorities')
    )

    if not any((overview, mission, values, strategic_priorities)):
        return None

    return CompanyResearchResult(
        company_name=company_name,
        overview=overview or f'{company_name} company context.',
        values=values,
        mission=mission or None,
        strategic_priorities=strategic_priorities,
        recent_news=_coerce_list_of_strings(raw_item.get('recent_news')) or _coerce_list_of_strings(nested.get('recent_news')),
        financial_summary=_coerce_text(raw_item.get('financial_summary')) or _coerce_text(nested.get('financial_summary')) or None,
        key_products=_coerce_list_of_strings(raw_item.get('key_products')) or _coerce_list_of_strings(nested.get('key_products')),
        company_size=_coerce_text(raw_item.get('company_size')) or _coerce_text(nested.get('company_size')) or None,
        key_executives=_coerce_list_of_strings(raw_item.get('key_executives')) or _coerce_list_of_strings(nested.get('key_executives')),
        competitive_positioning=_coerce_text(raw_item.get('competitive_positioning')) or _coerce_text(nested.get('competitive_positioning')) or None,
        growth_signals=_coerce_list_of_strings(raw_item.get('growth_signals')) or _coerce_list_of_strings(nested.get('growth_signals')),
        source=_coerce_research_source(raw_item.get('source') or nested.get('source')),
        source_urls=_coerce_list_of_strings(raw_item.get('source_urls')) or _coerce_list_of_strings(nested.get('source_urls')),
        confidence_score=_coerce_float(raw_item.get('confidence_score') or nested.get('confidence_score')),
        research_timestamp=_coerce_optional_datetime(raw_item.get('research_timestamp') or nested.get('research_timestamp'))
        or datetime.now(timezone.utc),
    )


def _resolve_company_research(
    dal: DynamoDalHandler,
    *,
    user_id: str,
    job_id: str,
    company_name: str,
    company_research_id: str | None,
) -> CompanyResearchResult | None:
    candidate_ids = _unique_non_empty([job_id, company_research_id or ''])
    for candidate_id in candidate_ids:
        result = dal.get_company_research(user_id=user_id, job_id=candidate_id)
        if not result.success or not isinstance(result.data, dict):
            continue

        materialized = _materialize_company_research(result.data, company_name)
        if materialized is not None:
            return materialized
    return None


def _jobs_table_candidates() -> list[str]:
    env_name = _coerce_text(os.environ.get('ENVIRONMENT') or os.environ.get('ENV') or os.environ.get('STAGE')).lower()
    candidates: list[str] = [
        _coerce_text(os.environ.get('JOBS_TABLE_NAME')),
        _coerce_text(os.environ.get('VPR_JOBS_TABLE_NAME')),
        _coerce_text(os.environ.get('JOBS_TABLE')),
        _coerce_text(os.environ.get('JOB_TABLE_NAME')),
    ]
    if env_name:
        candidates.extend(
            [
                f'careervp-jobs-table-{env_name}',
                f'careervp-vpr-jobs-table-{env_name}',
            ]
        )
    else:
        # Fallback to known deployed naming patterns when ENV vars are not exposed
        # on the worker Lambda but jobs still exist in the shared jobs table.
        candidates.extend(
            [
                'careervp-jobs-table-dev',
                'careervp-vpr-jobs-table-dev',
                'careervp-jobs-table-staging',
                'careervp-vpr-jobs-table-staging',
                'careervp-jobs-table-prod',
                'careervp-vpr-jobs-table-prod',
            ]
        )
    return _unique_non_empty(candidates)


def _resolve_job_record(user_id: str, job_id: str) -> dict[str, Any]:
    """Resolve a job record for cover letter context.

    Raises ``ValueError`` with diagnostic context (attempted table names,
    user_id mismatch details) if the record cannot be found or accessed.
    """
    candidates = _jobs_table_candidates()
    if not candidates:
        candidates = ['']

    attempted_tables: list[str] = []
    mismatch_tables: list[str] = []
    for table_name in candidates:
        display_name = table_name or '<default>'
        attempted_tables.append(display_name)
        repository = JobsRepository(table_name=table_name or None)
        record = repository.get_job(job_id)
        if not isinstance(record, dict):
            continue
        record_user_id = _coerce_text(record.get('user_id'))
        if not record_user_id or record_user_id != user_id:
            logger.warning(
                'Resolved job record belongs to another user',
                user_id=user_id,
                job_id=job_id,
                record_user_id=record_user_id,
                table_name=display_name,
            )
            mismatch_tables.append(display_name)
            continue
        return record

    if mismatch_tables:
        raise ValueError(
            f'Job record found but belongs to a different user for job_id={job_id}. '
            f'Mismatch in tables: {mismatch_tables}. '
            f'Attempted tables: {attempted_tables}'
        )
    raise ValueError(f'No job posting found for job_id={job_id}. Attempted tables: {attempted_tables}')


def _extract_job_context(job_record: dict[str, Any]) -> dict[str, str]:
    return {
        'company_name': _coerce_text(job_record.get('company_name') or job_record.get('company')),
        'job_title': _coerce_text(job_record.get('title') or job_record.get('job_title') or job_record.get('role_title')),
        'job_description': _coerce_text(job_record.get('description') or job_record.get('job_description')),
    }


def _normalize_gap_response(item: Any) -> dict[str, Any] | None:
    if hasattr(item, 'model_dump'):
        payload = item.model_dump(mode='json')
    elif isinstance(item, dict):
        payload = dict(item)
    else:
        return None
    if not isinstance(payload, dict):
        return None

    question_id = _coerce_text(payload.get('question_id') or payload.get('id') or payload.get('response_id'))
    question = _coerce_text(payload.get('question') or payload.get('question_text'))
    answer = _coerce_text(payload.get('answer') or payload.get('response') or payload.get('response_text'))

    if question_id:
        payload['question_id'] = question_id
    if question:
        payload['question'] = question
    if answer:
        payload['answer'] = answer
    return payload


def _resolve_gap_responses(
    dal: DynamoDalHandler,
    user_id: str,
    requested_gap_response_ids: list[str],
) -> list[dict[str, Any]]:
    requested_ids = {entry.strip() for entry in requested_gap_response_ids if entry.strip()}
    try:
        gap_result = dal.get_gap_responses(user_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning('Gap response lookup failed for cover letter context', user_id=user_id, error=str(exc))
        return []

    if not hasattr(gap_result, 'success') or not gap_result.success or not gap_result.data:
        return []

    normalized = [_normalize_gap_response(item) for item in gap_result.data]
    all_responses = [item for item in normalized if isinstance(item, dict)]
    if not requested_ids:
        return all_responses

    filtered = [item for item in all_responses if _coerce_text(item.get('question_id')) in requested_ids]
    return filtered or all_responses


def _resolve_vpr_payload(
    dal: DynamoDalHandler,
    application_id: str,
    artifact_id: str,
    user_id: str,
) -> Any:
    jobs_repository = JobsRepository()
    vpr_result = CoreRepository(dal=dal, vpr_jobs_repository=jobs_repository).get_vpr_by_artifact_id(
        application_id=application_id,
        artifact_id=artifact_id,
        user_id=user_id,
    )
    if vpr_result.success and vpr_result.data is None:
        vpr_result = CoreRepository(dal=dal).get_vpr_by_artifact_id(
            application_id=application_id,
            artifact_id=artifact_id,
            user_id=user_id,
        )
    if not vpr_result.success or vpr_result.data is None:
        raise ValueError(f'Required VPR not found for cover letter application: {application_id}')

    resolved_vpr = vpr_result.data
    vpr_owner = getattr(resolved_vpr, 'user_id', None) if not isinstance(resolved_vpr, dict) else resolved_vpr.get('user_id')
    if str(vpr_owner or '').strip() != user_id:
        raise ValueError(f'VPR ownership mismatch for cover letter application: {application_id}')

    if hasattr(resolved_vpr, 'model_dump'):
        return cast(Any, resolved_vpr)
    if isinstance(resolved_vpr, dict):
        return cast(Any, _ResolvedVPRPayload(resolved_vpr))
    raise ValueError(f'Required VPR payload has unsupported shape for cover letter: {application_id}')


def _resolve_cover_letter_context(
    dal: DynamoDalHandler,
    user_id: str,
    api_request: CoverLetterRequest,
    vpr_artifact_id: str | None = None,
) -> dict[str, Any]:
    posting_id = api_request.application_id or api_request.job_id
    job_record = _resolve_job_record(user_id=user_id, job_id=posting_id)
    job_context = _extract_job_context(job_record)
    for field_name, field_value in job_context.items():
        if _is_placeholder_context_value(field_value, job_id=posting_id):
            raise ValueError(f'Missing required non-placeholder job context field: {field_name}')

    context = {
        **job_context,
        'gap_responses': _resolve_gap_responses(
            dal=dal,
            user_id=user_id,
            requested_gap_response_ids=list(api_request.gap_response_ids),
        ),
        'vpr': _resolve_vpr_payload(
            dal=dal,
            application_id=posting_id,
            artifact_id=vpr_artifact_id or posting_id,
            user_id=user_id,
        ),
        'company_research': _resolve_company_research(
            dal=dal,
            user_id=user_id,
            job_id=posting_id,
            company_name=str(job_context['company_name']),
            company_research_id=api_request.company_research_id,
        ),
    }
    logger.info(
        'Cover letter context resolved',
        user_id=user_id,
        job_id=api_request.job_id,
        vpr_id=api_request.vpr_id,
        has_gap_responses=bool(context['gap_responses']),
        has_company_research=context['company_research'] is not None,
    )
    return context


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Handle cover letter API requests and SQS worker events."""
    _ = context
    set_request_origin(event)

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

    if method == 'GET' and _is_cover_letter_status_path(path):
        metrics.add_metric(name='CoverLetterStatusRequests', unit=MetricUnit.Count, value=1)
        return get_cover_letter_status(event)

    if method == 'GET' and path in {'/users/me/cover-letters', '/cover-letters'}:
        metrics.add_metric(name='CoverLetterListRequests', unit=MetricUnit.Count, value=1)
        return list_cover_letters(event)

    if method == 'POST' and path == '/cover-letter/generate':
        metrics.add_metric(name='CoverLetterRequests', unit=MetricUnit.Count, value=1)
        return _submit_cover_letter_request(event)

    if method == 'PATCH' and _is_cover_letter_patch_path(path):
        return _patch_cover_letter(event)

    if method == 'POST' and path.endswith('/cancel'):
        user_id = _extract_authenticated_user_id(event)
        if not user_id:
            return _build_response(
                HTTPStatus.UNAUTHORIZED,
                {'error': 'Missing or invalid authentication token', 'code': ResultCode.UNAUTHORIZED},
            )
        return _handle_cover_letter_cancel(event, user_id)

    return _build_response(
        HTTPStatus.NOT_FOUND,
        {
            'error': 'Endpoint not found',
            'code': ResultCode.INVALID_INPUT,
        },
    )


def _process_sqs_event(event: dict[str, Any]) -> dict[str, Any]:
    """Process SQS messages for async cover letter generation."""
    batch_item_failures: list[dict[str, str]] = []
    sqs_batch_seen = False

    for record in event.get('Records', []):
        message_id = str(record.get('messageId', ''))
        is_sqs_record = record.get('eventSource') == 'aws:sqs' and bool(message_id)
        sqs_batch_seen = sqs_batch_seen or is_sqs_record
        body = json.loads(record.get('body', '{}'))
        job_id = body.get('job_id', '')
        user_id = body.get('user_id', '')
        task_token = str(body.get('task_token') or '').strip() or None
        request_data = _request_data_from_sqs_body(body)

        if not job_id or not user_id:
            logger.error('SQS message missing job_id or user_id', body=body)
            continue

        logger.append_keys(job_id=job_id, user_id=user_id)
        logger.info('Processing cover letter SQS job', job_id=job_id)

        try:
            _generate_and_persist_from_sqs(job_id=job_id, user_id=user_id, request_data=request_data)
            _send_task_success(task_token, job_id=job_id, cover_letter_id=job_id)
        except CancelledBeforePersist:
            # Cancelled before/while persisting — skip cleanly: signal the chain
            # branch but do NOT route to the DLQ and do NOT send task_success.
            logger.info('Cover letter cancelled before persist — skipping', job_id=job_id, cancelled_before_persist=True)
            _send_task_failure(task_token, cause='Job was cancelled')
            continue
        except Exception as exc:
            # _generate_and_persist_from_sqs marks the artifact FAILED internally with
            # stage context before re-raising. Re-raise here so SQS routes to DLQ.
            logger.error('Cover letter SQS job failed', job_id=job_id, error=str(exc), exc_info=True)
            _send_task_failure(task_token, cause=str(exc))
            if not task_token and not is_sqs_record:
                raise
            batch_item_failures.append({'itemIdentifier': message_id})
            continue

    if sqs_batch_seen:
        return {'batchItemFailures': batch_item_failures}
    return {'statusCode': 200, 'body': 'OK'}


def _request_data_from_sqs_body(body: dict[str, Any]) -> dict[str, Any]:
    request_data = body.get('request_data')
    if isinstance(request_data, dict) and request_data:
        return request_data

    job_id = str(body.get('job_id') or '').strip()
    user_id = str(body.get('user_id') or '').strip()
    return {
        'cv_id': str(body.get('cv_id') or user_id).strip(),
        'job_id': job_id,
        'application_id': str(body.get('application_id') or job_id).strip(),
        'vpr_id': str(body.get('vpr_id') or '').strip(),
        'gap_response_ids': body.get('gap_response_ids') if isinstance(body.get('gap_response_ids'), list) else ['artifact-chain'],
        'company_research_id': body.get('company_research_id'),
    }


def _send_task_success(task_token: str | None, *, job_id: str, cover_letter_id: str) -> None:
    if not task_token:
        return
    sfn.send_task_success(
        taskToken=task_token,
        output=json.dumps({'job_id': job_id, 'cover_letter_id': cover_letter_id}),
    )


def _send_task_failure(task_token: str | None, *, cause: str) -> None:
    if not task_token:
        return
    sfn.send_task_failure(
        taskToken=task_token,
        error='CoverLetterFailed',
        cause=cause,
    )


def _generate_and_persist_from_sqs(
    job_id: str,
    user_id: str,
    request_data: dict[str, Any],
) -> None:
    """Load pending record, generate cover letter, persist result.

    All exceptions are caught internally: the artifact is marked FAILED with
    a ``stage`` field indicating which pipeline step failed, then re-raised so
    SQS can route the message to the DLQ after retries are exhausted.
    """
    current_stage = 'initialization'
    cover_letter_payload: dict[str, Any] | None = None

    try:
        dal = _get_dal()

        # Update status to PROCESSING — refuse to resurrect a job cancelled before
        # this (re)delivery (raises CancelledBeforePersist, handled by the SQS loop).
        _update_artifact_status(user_id=user_id, job_id=job_id, status='PROCESSING', fail_if_cancelled=True)

        # Validate the request data
        current_stage = 'request_validation'
        api_request = CoverLetterRequest.model_validate(request_data)

        # Load user CV
        current_stage = 'cv_loading'
        user_cv = _load_user_cv(dal=dal, user_id=user_id)
        if user_cv is None or user_cv.user_id != user_id:
            raise ValueError(f'No CV found for user {user_id}')

        # Generate cover letter (context resolution + LLM call)
        current_stage = 'context_resolution'
        generation_result = _generate_cover_letter_result(
            api_request=api_request,
            user_id=user_id,
            user_cv=user_cv,
            dal=dal,
        )

        current_stage = 'generation'
        if not generation_result.success or generation_result.data is None:
            raise RuntimeError(f'Cover letter generation failed: {generation_result.error}')

        cover_letter_model = generation_result.data.cover_letter
        if cover_letter_model is None:
            raise RuntimeError('Cover letter generation returned no content')

        # Persist the result
        current_stage = 'persistence'
        cover_letter_payload = cover_letter_model.model_dump(mode='json')
        # Use the actual application/job ID (not the cache-busting random UUID sent as job_id)
        storage_job_id = api_request.application_id or api_request.job_id
        dal.save_cover_letter(
            cover_letter=cover_letter_payload,
            user_id=user_id,
            cv_id=api_request.cv_id,
            job_id=storage_job_id,
        )

    except CancelledBeforePersist:
        # The PROCESSING claim was rejected because the job is already cancelled.
        # Do NOT mark it FAILED — propagate so the SQS loop skips it cleanly.
        raise
    except Exception as exc:
        error_details = _extract_failure_details(exc)
        error_details['stage'] = current_stage
        logger.error(
            'Cover letter generation failed',
            job_id=job_id,
            user_id=user_id,
            stage=current_stage,
            error=str(exc),
            exc_info=True,
        )
        _update_artifact_status(user_id=user_id, job_id=job_id, status='FAILED', error_details=error_details)
        raise

    # Update the artifact record to COMPLETED only after successful persistence —
    # a cancel during generation must not be overwritten back to COMPLETED.
    assert cover_letter_payload is not None  # guaranteed: set before 'persistence' stage completes
    _update_artifact_status(
        user_id=user_id,
        job_id=job_id,
        status='COMPLETED',
        result_data=_convert_decimal_to_float(cover_letter_payload),
        fail_if_cancelled=True,
    )

    # Propagate completion to the application record so the hub reflects the
    # artifact status and artifact_id across page reloads.
    # Use application_id (the stable job UUID) not job_id (the cache-busting random UUID).
    sqs_application_id = str(request_data.get('application_id', '') or request_data.get('job_id', '') or '')
    _update_application_artifact(
        application_id=sqs_application_id,
        user_id=user_id,
        artifact_type='cover_letter',
        artifact_id=job_id,
    )

    metrics.add_metric(name='CoverLetterWorkerGenerated', unit=MetricUnit.Count, value=1)
    logger.info('Cover letter SQS job completed', job_id=job_id)


def _update_artifact_status(  # noqa: C901
    user_id: str,
    job_id: str,
    status: str,
    result_data: dict[str, Any] | None = None,
    error_details: dict[str, str] | None = None,
    fail_if_cancelled: bool = False,
) -> None:
    """Update cover letter artifact status in DynamoDB.

    When ``fail_if_cancelled`` is True the write is conditional and is rejected
    if the artifact is already CANCELLED; that rejection is surfaced as
    ``CancelledBeforePersist`` so the worker skips cleanly instead of resurrecting
    a cancelled artifact (FE-UI-043 worker_cancelled_guard).
    """
    import datetime as _dt

    import boto3 as _boto3

    table_name = table_registry.resolve_artifacts_table_name()
    table = _boto3.resource('dynamodb').Table(table_name)
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()

    update_expr = 'SET #s = :status, updated_at = :now'
    attr_names: dict[str, str] = {'#s': 'status'}
    attr_values: dict[str, Any] = {':status': status, ':now': now}

    if result_data is not None:
        update_expr += ', cover_letter = :result'
        attr_values[':result'] = result_data
    if error_details:
        if error_details.get('error'):
            update_expr += ', #err = :error'
            attr_names['#err'] = 'error'
            attr_values[':error'] = error_details['error']
        if error_details.get('code'):
            update_expr += ', #code = :code'
            attr_names['#code'] = 'code'
            attr_values[':code'] = error_details['code']
        if error_details.get('error_type'):
            update_expr += ', error_type = :error_type'
            attr_values[':error_type'] = error_details['error_type']
        if error_details.get('stage'):
            update_expr += ', stage = :stage'
            attr_values[':stage'] = error_details['stage']

    condition: str | None = None
    if fail_if_cancelled:
        condition = 'attribute_not_exists(#s) OR #s <> :cancelled'
        attr_values[':cancelled'] = 'CANCELLED'

    artifact_id = table_registry.cover_letter_artifact_id(job_id)
    primary_kwargs: dict[str, Any] = {
        'Key': table_registry.canonical_item_key(user_id, artifact_id),
        'UpdateExpression': update_expr,
        'ExpressionAttributeNames': attr_names,
        'ExpressionAttributeValues': attr_values,
    }
    if condition is not None:
        primary_kwargs['ConditionExpression'] = condition
    try:
        table.update_item(**primary_kwargs)
    except Exception as exc:
        error_response = getattr(exc, 'response', {}) if hasattr(exc, 'response') else {}
        error_code = ((error_response.get('Error') or {}).get('Code')) if isinstance(error_response, dict) else None
        if fail_if_cancelled and error_code == 'ConditionalCheckFailedException':
            logger.info('Cover letter cancelled before write — skipping', job_id=job_id, attempted_status=status)
            raise CancelledBeforePersist(job_id) from exc
        if error_code == 'ValidationException':
            fallback_kwargs: dict[str, Any] = {
                'Key': table_registry.legacy_item_key(user_id, artifact_id),
                'UpdateExpression': update_expr,
                'ExpressionAttributeNames': attr_names,
                'ExpressionAttributeValues': attr_values,
            }
            if condition is not None:
                fallback_kwargs['ConditionExpression'] = condition
            try:
                table.update_item(**fallback_kwargs)
            except Exception as fallback_exc:
                fb_response = getattr(fallback_exc, 'response', {}) if hasattr(fallback_exc, 'response') else {}
                fb_code = ((fb_response.get('Error') or {}).get('Code')) if isinstance(fb_response, dict) else None
                if fail_if_cancelled and fb_code == 'ConditionalCheckFailedException':
                    logger.info('Cover letter cancelled before write — skipping', job_id=job_id, attempted_status=status)
                    raise CancelledBeforePersist(job_id) from fallback_exc
                raise
            return
        logger.error('Failed to update artifact status', job_id=job_id, error=str(exc))
        raise


def _update_application_artifact(
    application_id: str,
    user_id: str,
    artifact_type: str,
    artifact_id: str,
) -> None:
    """Propagate artifact completion to the application record's artifact_statuses.

    Silently ignored when the application record does not exist — non-fatal
    because the session-local frontend fallback handles this case.
    """
    if not application_id or not user_id:
        return
    app_table = os.environ.get('APPLICATIONS_TABLE_NAME') or os.environ.get('DYNAMODB_TABLE_NAME') or ''
    if not app_table:
        return
    try:
        from careervp.dal.application_repository import ApplicationRepository
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler

        app_repo = ApplicationRepository(DynamoDalHandler(app_table))
        app_repo.update_artifact_with_id(
            application_id=application_id,
            user_id=user_id,
            artifact_type=artifact_type,
            status='completed',
            artifact_id=artifact_id,
        )
    except Exception as e:
        logger.warning(
            'Could not update application artifact_statuses',
            artifact_type=artifact_type,
            error=str(e),
        )


def _submit_cover_letter_request(event: dict[str, Any]) -> dict[str, Any]:  # noqa: C901
    """Handle POST /cover-letter/generate requests."""
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        metrics.add_metric(name='CoverLetterFailures', unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.UNAUTHORIZED,
            {
                'error': 'Missing or invalid authentication token',
                'code': ResultCode.UNAUTHORIZED,
            },
        )

    request_result = _parse_request(event)
    if not request_result.success or not request_result.data:
        metrics.add_metric(name='CoverLetterFailures', unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.BAD_REQUEST,
            {
                'error': request_result.error or 'Invalid request payload',
                'code': ResultCode.INVALID_INPUT,
            },
        )
    api_request = request_result.data

    dal = _get_dal()
    dependency_resolution, dependency_response = _resolve_cover_letter_dependency_response(
        api_request=api_request,
        user_id=user_id,
        dal=dal,
    )
    if dependency_response is not None:
        return dependency_response
    application_id = api_request.application_id or api_request.job_id
    resolved_vpr_ref = dependency_resolution.resolved_upstream.get('vpr')
    vpr_artifact_id = resolved_vpr_ref.artifact_id if resolved_vpr_ref is not None else None
    if resolved_vpr_ref is not None and not vpr_artifact_id:
        vpr_artifact_id = application_id
    if not vpr_artifact_id:
        repository = CoreRepository(dal=dal, vpr_jobs_repository=JobsRepository())
        resolved_id = repository.resolve_artifact_id(
            application_id=application_id,
            artifact_type='vpr',
            user_id=user_id,
        )
        if resolved_id.success:
            vpr_artifact_id = resolved_id.data
    if not vpr_artifact_id:
        job_record = JobsRepository().get_job(application_id)
        if isinstance(job_record, dict):
            return _build_response(HTTPStatus.FORBIDDEN, vpr_access_denied_envelope())
        vpr_artifact_id = application_id

    try:
        user_cv = _load_user_cv(dal=dal, user_id=user_id)
    except Exception as e:
        logger.error('Failed to load user CV for cover letter', user_id=user_id, error=str(e))
        return _build_response(
            HTTPStatus.UNPROCESSABLE_ENTITY, {'error': 'Could not load your CV. Please upload a CV before generating a cover letter.'}
        )
    if user_cv is None or user_cv.user_id != user_id:
        return _build_response(HTTPStatus.NOT_FOUND, {'error': 'No CV found for your account. Please upload a CV first.'})

    try:
        generation_result = _generate_cover_letter_result(
            api_request=api_request,
            user_id=user_id,
            user_cv=user_cv,
            dal=dal,
            vpr_artifact_id=vpr_artifact_id,
        )
    except Exception as e:
        logger.error('Cover letter generation failed', user_id=user_id, error=str(e), exc_info=True)
        return _build_response(HTTPStatus.SERVICE_UNAVAILABLE, {'error': 'Cover letter generation failed. Please try again.'})
    if not generation_result.success or generation_result.data is None:
        metrics.add_metric(name='CoverLetterFailures', unit=MetricUnit.Count, value=1)
        return _build_generation_error_response(generation_result)

    cover_letter_model = generation_result.data.cover_letter
    if cover_letter_model is None:
        metrics.add_metric(name='CoverLetterFailures', unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {
                'error': 'Cover letter generation returned no content',
                'code': ResultCode.INTERNAL_ERROR,
            },
        )

    cover_letter_payload = cover_letter_model.model_dump(mode='json')
    # Use the actual application/job ID (not the cache-busting random UUID sent as job_id)
    storage_job_id = api_request.application_id or api_request.job_id
    try:
        save_result = dal.save_cover_letter(
            cover_letter=cover_letter_payload,
            user_id=user_id,
            cv_id=api_request.cv_id,
            job_id=storage_job_id,
        )
    except Exception as exc:
        logger.error('Cover letter persistence failed', user_id=user_id, error=str(exc), exc_info=True)
        save_result = Result(success=False, error='persist failed', code=ResultCode.DYNAMODB_ERROR)
    if not save_result.success:
        # AC-CL-303: Persistence failure must NOT return synthetic completed response
        metrics.add_metric(name='CoverLetterPersistenceFailure', unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {
                'error': 'Cover letter generated but failed to save. Please try again.',
                'code': ResultCode.DYNAMODB_ERROR,
            },
        )

    artifact_id = str(cover_letter_payload.get('cover_letter_id', '')).strip()
    # Propagate artifact_id to the application record so the hub reflects cover letter status
    _update_application_artifact(
        application_id=api_request.application_id or '',
        user_id=user_id,
        artifact_type='cover_letter',
        artifact_id=artifact_id,
    )

    metrics.add_metric(name='CoverLetterGenerated', unit=MetricUnit.Count, value=1)
    return _build_response(
        HTTPStatus.OK,
        {
            'artifact_id': artifact_id,
            'status': 'completed',
        },
    )


def _resolve_cover_letter_dependency_response(
    *,
    api_request: CoverLetterRequest,
    user_id: str,
    dal: DynamoDalHandler,
) -> tuple[DependencyResolution, dict[str, Any] | None]:
    application_id = api_request.application_id or api_request.job_id
    dependency_resolution = resolve_handler_dependencies(
        artifact_type='cover_letter',
        application_id=application_id,
        user_id=user_id,
        dal=dal,
    )
    if dependency_resolution.status == 'ready':
        return dependency_resolution, None
    if dependency_resolution.status == 'dependency_generating':
        mark_requested_artifact_pending(application_id=application_id, user_id=user_id, artifact_type='cover_letter')
    return (
        dependency_resolution,
        _build_response(
            HTTPStatus(dependency_resolution.http_status),
            dependency_response_body(dependency_resolution, requested_artifact='cover_letter'),
        ),
    )


def get_cover_letter_status(event: dict[str, Any]) -> dict[str, Any]:
    """Handle GET /cover-letter/{coverLetterId} requests."""
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        return _build_response(
            HTTPStatus.UNAUTHORIZED,
            {
                'error': 'Missing or invalid authentication token',
                'code': ResultCode.UNAUTHORIZED,
            },
        )

    cover_letter_id = _extract_cover_letter_id(event)
    if not cover_letter_id:
        return _build_response(
            HTTPStatus.BAD_REQUEST,
            {
                'error': 'Missing coverLetterId path parameter',
                'code': ResultCode.MISSING_REQUIRED_FIELD,
            },
        )

    matching_item = _find_cover_letter_item(user_id=user_id, cover_letter_id=cover_letter_id)
    if matching_item is None:
        metrics.add_metric(name='CoverLetterStatusNotFound', unit=MetricUnit.Count, value=1)
        logger.info('Cover letter artifact not found', cover_letter_id=cover_letter_id, user_id=user_id)
        return _build_response(
            HTTPStatus.NOT_FOUND,
            {
                'error': 'Cover letter not found',
                'code': ResultCode.COVER_LETTER_NOT_FOUND,
            },
        )

    return _build_response(HTTPStatus.OK, _build_cover_letter_status_payload(matching_item, cover_letter_id))


def list_cover_letters(event: dict[str, Any]) -> dict[str, Any]:
    """Handle GET /users/me/cover-letters requests."""
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        return _build_response(
            HTTPStatus.UNAUTHORIZED,
            {
                'error': 'Missing or invalid authentication token',
                'code': ResultCode.UNAUTHORIZED,
            },
        )

    items = _list_cover_letter_items(user_id)
    payload = [_build_cover_letter_list_item(item) for item in items]
    return _build_response(HTTPStatus.OK, {'cover_letters': payload})


def _parse_request(event: dict[str, Any]) -> Result[CoverLetterRequest]:
    """Parse and validate the request body."""
    body_content = event.get('body', '{}')
    try:
        payload = json.loads(body_content or '{}')
    except (TypeError, json.JSONDecodeError):
        logger.warning('Invalid JSON body for cover letter request')
        return Result(success=False, error='Invalid JSON request body', code=ResultCode.INVALID_INPUT)

    try:
        request = CoverLetterRequest.model_validate(payload)
    except ValidationError:
        logger.warning('CoverLetterRequest validation failed')
        return Result(success=False, error='Request validation failed', code=ResultCode.INVALID_INPUT)

    return Result(success=True, data=request, code=ResultCode.SUCCESS)


def _is_cover_letter_status_path(path: str) -> bool:
    return path.startswith('/cover-letter/') and path != '/cover-letter/generate'


def _extract_authenticated_user_id(event: dict[str, Any]) -> str | None:
    return extract_user_id(event)


def _extract_cover_letter_id(event: dict[str, Any]) -> str | None:
    path_parameters = event.get('pathParameters')
    if isinstance(path_parameters, dict):
        for key in ('coverLetterId', 'cover_letter_id', 'id', 'job_id', 'jobId'):
            value = path_parameters.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    path = str(event.get('path', '')).rstrip('/')
    if path.startswith('/cover-letter/'):
        candidate = path.removeprefix('/cover-letter/').strip()
        if candidate.endswith('/status'):
            candidate = candidate[: -len('/status')]
        if candidate and candidate != 'generate':
            return candidate
    return None


def _load_user_cv(dal: DynamoDalHandler, user_id: str) -> UserCV | None:
    users_table_name = os.environ.get('USERS_TABLE_NAME', '').strip()
    cv_table_name = os.environ.get('CVS_TABLE_NAME', '').strip()
    dal_candidates: list[DynamoDalHandler] = []
    if users_table_name:
        dal_candidates.append(DynamoDalHandler(users_table_name))
    if cv_table_name:
        dal_candidates.append(DynamoDalHandler(cv_table_name))
    if (not cv_table_name and not users_table_name) or (cv_table_name != dal.table_name and users_table_name != dal.table_name):
        dal_candidates.append(dal)

    for cv_dal in dal_candidates:
        try:
            raw_cv = cv_dal.get_cv(user_id)
        except Exception as exc:
            logger.warning('Failed to load CV from candidate table', table_name=cv_dal.table_name, error=str(exc))
            continue

        if isinstance(raw_cv, UserCV):
            return raw_cv
        if isinstance(raw_cv, dict):
            try:
                return UserCV.model_validate(raw_cv)
            except ValidationError:
                logger.warning('Failed to coerce DynamoDB CV payload to UserCV')
                continue
    return None


def _to_logic_options(api_request: CoverLetterRequest) -> LogicCoverLetterOptions | None:
    if api_request.options is None:
        return None
    return LogicCoverLetterOptions.model_validate(api_request.options.model_dump(mode='json'))


def _generate_cover_letter_result(
    api_request: CoverLetterRequest,
    user_id: str,
    user_cv: UserCV,
    dal: DynamoDalHandler | None = None,
    vpr_artifact_id: str | None = None,
) -> Result[Any]:
    resolved_dal = dal or _get_dal()
    context = _resolve_cover_letter_context(
        dal=resolved_dal,
        user_id=user_id,
        api_request=api_request,
        vpr_artifact_id=vpr_artifact_id,
    )
    logic_request = LogicCoverLetterRequest(
        user_id=user_id,
        cv_id=api_request.cv_id,
        job_id=api_request.job_id,
        vpr_id=api_request.vpr_id,
        company_name=str(context['company_name']),
        job_title=str(context['job_title']),
        job_description=str(context['job_description']),
        gap_response_ids=list(api_request.gap_response_ids),
        company_research_id=api_request.company_research_id,
        options=_to_logic_options(api_request),
    )
    application_id = str(api_request.application_id or api_request.job_id).strip()
    with bind_llm_usage_context(application_id=application_id, user_id=user_id):
        maybe_async_result = generate_cover_letter(
            request=logic_request,
            user_cv=user_cv,
            vpr=cast(Any, context['vpr']),
            gap_responses=cast(Any, context['gap_responses']),
            company_research=cast(Any, context.get('company_research')),
        )
        if asyncio.iscoroutine(maybe_async_result):
            return asyncio.run(maybe_async_result)
        if isinstance(maybe_async_result, Result):
            return maybe_async_result
    return Result(
        success=False,
        error='Invalid cover letter generation response',
        code=ResultCode.INTERNAL_ERROR,
    )


def _extract_failure_details(exc: Exception) -> dict[str, str]:
    """Extract structured diagnostics from worker failure exceptions."""
    details: dict[str, str] = {}
    message = str(exc).strip()
    if message:
        details['error'] = message
    error_type = type(exc).__name__.strip()
    if error_type:
        details['error_type'] = error_type

    response = getattr(exc, 'response', None)
    if isinstance(response, dict):
        error_block = response.get('Error')
        if isinstance(error_block, dict):
            code = str(error_block.get('Code', '')).strip()
            if code:
                details['code'] = code
            if not details.get('error'):
                error_message = str(error_block.get('Message', '')).strip()
                if error_message:
                    details['error'] = error_message
    return details


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
            'error': generation_result.error or 'Cover letter generation failed',
            'code': generation_result.code,
        },
    )


def _find_cover_letter_item(user_id: str, cover_letter_id: str) -> dict[str, Any] | None:
    """Find a cover letter artifact using canonical key lookup with legacy fallback.

    Phase A dual-read strategy:
      1. Try canonical read: applicationId=user_id, artifactId=ARTIFACT#COVER_LETTER#{cover_letter_id}
      2. If canonical miss and COVER_LETTER_LEGACY_READ_ENABLED=true, scan legacy items
      3. Fall back to list scan for edge cases (sync-path items with different sk format)
    """
    dal = _get_dal()

    # Canonical read: construct the expected artifactId
    artifact_id = table_registry.cover_letter_artifact_id(cover_letter_id)
    canonical_result = dal.read_cover_letter_by_artifact_id(
        application_id=user_id,
        artifact_id=artifact_id,
    )
    if canonical_result.success and canonical_result.data is not None:
        return canonical_result.data

    # Phase A fallback: scan list for matching item (pre-migration pk/sk records)
    logger.info(
        'Canonical cover letter read missed; using list-scan fallback (Phase A)',
        cover_letter_id=cover_letter_id,
        user_id=user_id,
        canonical_result_code=getattr(canonical_result, 'code', None),
    )
    metrics.add_metric(name='CoverLetterCanonicalReadFallback', unit=MetricUnit.Count, value=1)
    items = _list_cover_letter_items(user_id)
    for item in items:
        if _matches_cover_letter_id(item, cover_letter_id):
            return item
    return None


def _list_cover_letter_items(user_id: str) -> list[dict[str, Any]]:
    dal = _get_dal()
    result = dal.list_cover_letters_canonical(user_id)
    if result.success and isinstance(result.data, list):
        return [item for item in result.data if isinstance(item, dict)]
    return []


def _matches_cover_letter_id(item: dict[str, Any], cover_letter_id: str) -> bool:
    # Match by full sk (e.g. ARTIFACT#COVER_LETTER#cv-1#job-1#v1)
    if str(item.get('sk', '')).strip() == cover_letter_id:
        return True

    # Match by job_id field (async path: request_id == job_id UUID)
    if str(item.get('job_id', '')).strip() == cover_letter_id:
        return True

    # Match by artifactId attribute (written by submit handler)
    artifact_id_attr = str(item.get('artifactId', '')).strip()
    if artifact_id_attr == cover_letter_id:
        return True
    if artifact_id_attr == table_registry.cover_letter_artifact_id(cover_letter_id):
        return True

    nested_payload = item.get('cover_letter')
    nested_id = _extract_cover_letter_id_from_payload(nested_payload)
    if nested_id == cover_letter_id:
        return True

    direct_id = _extract_cover_letter_id_from_payload(item)
    return direct_id == cover_letter_id


def _normalize_status(raw_status: Any) -> str:
    normalized = str(raw_status or '').strip().lower()
    if normalized in {'pending', 'processing', 'completed', 'failed'}:
        return normalized
    if normalized:
        logger.warning('Unexpected cover letter status value', raw_status=raw_status)
    return 'pending'


def _extract_cover_letter_text(cover_letter_payload: Any) -> str | None:
    if isinstance(cover_letter_payload, str) and cover_letter_payload.strip():
        return cover_letter_payload.strip()

    if isinstance(cover_letter_payload, dict):
        for key in ('cover_letter', 'full_text', 'text'):
            candidate = cover_letter_payload.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    return None


def _extract_cover_letter_id_from_payload(cover_letter_payload: Any) -> str | None:
    if isinstance(cover_letter_payload, dict):
        for key in ('cover_letter_id', 'id'):
            candidate = cover_letter_payload.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    return None


def _extract_canonical_request_id(item: dict[str, Any], fallback_id: str | None = None) -> str | None:
    raw_sk = str(item.get('sk', '')).strip()
    has_legacy_sort_key = False
    if raw_sk.startswith('ARTIFACT#COVER_LETTER#'):
        sk_suffix = raw_sk.removeprefix('ARTIFACT#COVER_LETTER#').strip()
        has_legacy_sort_key = bool(sk_suffix and '#' in sk_suffix)

    for key in ('artifactId', 'sk'):
        if key == 'artifactId' and has_legacy_sort_key:
            continue
        raw_value = str(item.get(key, '')).strip()
        if raw_value.startswith('ARTIFACT#COVER_LETTER#'):
            suffix = raw_value.removeprefix('ARTIFACT#COVER_LETTER#').strip()
            if suffix and '#' not in suffix:
                return suffix
    if fallback_id:
        normalized_fallback = str(fallback_id).strip()
        if normalized_fallback:
            return normalized_fallback
    return None


def _build_cover_letter_status_payload(item: dict[str, Any], fallback_id: str) -> dict[str, Any]:
    nested_payload = item.get('cover_letter')
    payload_source = nested_payload if isinstance(nested_payload, dict) else item

    payload_id = (
        _extract_canonical_request_id(item, fallback_id=fallback_id)
        or _extract_cover_letter_id_from_payload(payload_source)
        or _extract_cover_letter_id_from_payload(nested_payload)
        or str(item.get('job_id', '')).strip()
        or (str(item.get('sk', '')).strip() if item.get('sk') else '')
    )
    status = _normalize_status(item.get('status'))

    payload: dict[str, Any] = {
        'id': payload_id,
        'status': status,
    }

    if status in {'completed', 'failed'}:
        result = _build_cover_letter_result_payload(item=item, payload_source=payload_source, nested_payload=nested_payload)
        if status == 'failed':
            failed_details = _extract_failed_status_details(item)
            if failed_details.get('error'):
                payload['error'] = failed_details['error']
                result['error'] = failed_details['error']
            if failed_details.get('code'):
                payload['code'] = failed_details['code']
                result['code'] = failed_details['code']
            if failed_details.get('error_type'):
                result['error_type'] = failed_details['error_type']
            if failed_details.get('stage'):
                payload['stage'] = failed_details['stage']
                result['stage'] = failed_details['stage']

        if result:
            payload['result'] = result
    return payload


def _build_cover_letter_result_payload(
    item: dict[str, Any],
    payload_source: dict[str, Any] | Any,
    nested_payload: Any,
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    cover_letter_text = _extract_cover_letter_text(payload_source) or _extract_cover_letter_text(nested_payload)
    if cover_letter_text:
        result['cover_letter'] = cover_letter_text

    paragraphs_value = item.get('paragraphs')
    if paragraphs_value is None and isinstance(payload_source, dict):
        paragraphs_value = payload_source.get('paragraphs')
    if isinstance(paragraphs_value, dict):
        result['paragraphs'] = paragraphs_value

    fvs_validation = item.get('fvs_validation')
    if fvs_validation is None and isinstance(payload_source, dict):
        fvs_validation = payload_source.get('fvs_validation')
    if isinstance(fvs_validation, dict):
        result['fvs_validation'] = fvs_validation
    return result


def _extract_failed_status_details(item: dict[str, Any]) -> dict[str, str]:
    details: dict[str, str] = {}
    error_message = str(item.get('error', '')).strip()
    error_code = str(item.get('code', '')).strip()
    error_type = str(item.get('error_type', '')).strip()
    stage = str(item.get('stage', '')).strip()

    if error_message:
        details['error'] = error_message
    if error_code:
        details['code'] = error_code
    if error_type:
        details['error_type'] = error_type
    if stage:
        details['stage'] = stage
    return details


def _build_cover_letter_list_item(item: dict[str, Any]) -> dict[str, Any]:
    nested_payload = item.get('cover_letter')
    payload_source = nested_payload if isinstance(nested_payload, dict) else item

    item_id = (
        _extract_canonical_request_id(item)
        or _extract_cover_letter_id_from_payload(payload_source)
        or _extract_cover_letter_id_from_payload(nested_payload)
        or str(item.get('job_id', '')).strip()
        or (str(item.get('sk', '')).strip() if item.get('sk') else '')
    )
    cv_id = item.get('cv_id')
    if cv_id is None and isinstance(payload_source, dict):
        cv_id = payload_source.get('cv_id')
    job_id = item.get('job_id')
    if job_id is None and isinstance(payload_source, dict):
        job_id = payload_source.get('job_id')
    created_at = item.get('created_at')
    if created_at is None and isinstance(payload_source, dict):
        created_at = payload_source.get('created_at')

    return {
        'id': item_id,
        'status': _normalize_status(item.get('status')),
        'cv_id': cv_id,
        'job_id': job_id,
        'created_at': created_at,
        'updated_at': item.get('updated_at'),
    }


def _build_default_cover_letter_status_payload(cover_letter_id: str) -> dict[str, Any]:
    return {
        'id': cover_letter_id,
        'status': 'completed',
        'result': {
            'cover_letter': (
                'Dear Hiring Team,\n\n'
                'I am excited to apply for this role because it aligns with my experience delivering '
                'high-impact engineering outcomes in fast-moving environments. In previous roles I led '
                'cross-functional efforts that improved reliability, reduced delivery risk, and produced '
                'measurable business results. I would welcome the opportunity to bring the same ownership, '
                'technical rigor, and collaboration to your team.\n\n'
                'Sincerely,\n'
                'Candidate'
            ),
        },
    }


_COVER_LETTER_TERMINAL_STATUSES = {'COMPLETED', 'FAILED', 'CANCELLED'}


def _handle_cover_letter_cancel(event: dict[str, Any], user_id: str) -> dict[str, Any]:
    """Handle POST /cover-letter/{coverLetterId}/cancel."""
    import boto3 as _boto3

    path_params = event.get('pathParameters') or {}
    cover_letter_id = str(path_params.get('coverLetterId') or '').strip()
    if not cover_letter_id:
        return _build_response(HTTPStatus.BAD_REQUEST, {'error': 'Missing coverLetterId'})

    table_name = table_registry.resolve_artifacts_table_name()
    table = _boto3.resource('dynamodb').Table(table_name)
    artifact_id = table_registry.cover_letter_artifact_id(cover_letter_id)

    try:
        get_resp = table.get_item(Key={'applicationId': user_id, 'artifactId': artifact_id})
        item = (get_resp or {}).get('Item')
    except Exception as exc:
        logger.error('DynamoDB error during cover letter cancel', error=str(exc))
        return _build_response(HTTPStatus.INTERNAL_SERVER_ERROR, {'error': 'Internal server error'})

    if not item:
        try:
            query_resp = table.query(
                KeyConditionExpression='applicationId = :uid AND begins_with(artifactId, :prefix)',
                ExpressionAttributeValues={
                    ':uid': user_id,
                    ':prefix': table_registry.cover_letter_artifact_id(cover_letter_id),
                },
                Limit=1,
            )
            items = (query_resp or {}).get('Items', [])
            item = items[0] if items else None
        except Exception:
            item = None
        if not item:
            return _build_response(HTTPStatus.NOT_FOUND, {'error': 'Cover letter not found'})

    status = str(item.get('status', '')).upper()
    if status in _COVER_LETTER_TERMINAL_STATUSES:
        return _build_response(HTTPStatus.CONFLICT, {'error': 'Cannot cancel terminal task'})

    item_app_id = str(item.get('applicationId', user_id))
    item_artifact_id = str(item.get('artifactId', artifact_id))
    table.update_item(
        Key={'applicationId': item_app_id, 'artifactId': item_artifact_id},
        UpdateExpression='SET #s = :status',
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={':status': 'CANCELLED'},
    )
    return _build_response(HTTPStatus.OK, {'status': 'cancelled'})


def _is_cover_letter_patch_path(path: str) -> bool:
    return path.startswith('/cover-letter/') and path != '/cover-letter/generate' and not path.endswith('/cancel')


def _patch_cover_letter(event: dict[str, Any]) -> dict[str, Any]:
    """Handle PATCH /cover-letter/{coverLetterId} — update cover letter text."""
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        return _build_response(
            HTTPStatus.UNAUTHORIZED,
            {'error': 'Missing or invalid authentication token', 'code': ResultCode.UNAUTHORIZED},
        )

    cover_letter_id = _extract_cover_letter_id(event)
    if not cover_letter_id:
        return _build_response(HTTPStatus.BAD_REQUEST, {'error': 'Missing coverLetterId', 'code': ResultCode.MISSING_REQUIRED_FIELD})

    try:
        body = json.loads(event.get('body', '{}') or '{}')
    except json.JSONDecodeError:
        return _build_response(HTTPStatus.BAD_REQUEST, {'error': 'Invalid JSON', 'code': ResultCode.INVALID_INPUT})

    new_text = str(body.get('cover_letter', '') or '').strip()
    if not new_text:
        return _build_response(HTTPStatus.BAD_REQUEST, {'error': 'cover_letter text is required', 'code': ResultCode.MISSING_REQUIRED_FIELD})

    item = _find_cover_letter_item(user_id=user_id, cover_letter_id=cover_letter_id)
    if item is None:
        return _build_response(HTTPStatus.NOT_FOUND, {'error': 'Cover letter not found', 'code': ResultCode.COVER_LETTER_NOT_FOUND})

    import datetime as _dt

    import boto3 as _boto3

    table_name = table_registry.resolve_artifacts_table_name()
    table = _boto3.resource('dynamodb').Table(table_name)
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()

    if 'applicationId' in item:
        key: dict[str, Any] = table_registry.canonical_item_key(item['applicationId'], item['artifactId'])
    else:
        key = table_registry.legacy_item_key(
            item.get('pk', user_id),
            item.get('sk', table_registry.cover_letter_artifact_id(cover_letter_id)),
        )

    existing_cl = item.get('cover_letter') or {}
    updated_cl: dict[str, Any] = {**existing_cl, 'full_text': new_text} if isinstance(existing_cl, dict) else {'full_text': new_text}

    try:
        table.update_item(
            Key=key,
            UpdateExpression='SET cover_letter = :cl, updated_at = :now',
            ExpressionAttributeValues={':cl': updated_cl, ':now': now},
        )
    except Exception as exc:
        logger.error('Failed to update cover letter', cover_letter_id=cover_letter_id, error=str(exc))
        return _build_response(HTTPStatus.INTERNAL_SERVER_ERROR, {'error': 'Failed to update cover letter', 'code': ResultCode.DYNAMODB_ERROR})

    return _build_response(
        HTTPStatus.OK,
        {
            'id': cover_letter_id,
            'status': 'completed',
            'result': {'cover_letter': new_text},
        },
    )


def _build_response(status_code: HTTPStatus, body: dict[str, Any]) -> dict[str, Any]:
    """Build API Gateway compatible response."""
    headers = get_cors_headers(None)
    headers['Content-Type'] = 'application/json'
    return {
        'statusCode': status_code.value,
        'headers': headers,
        'body': json.dumps(_convert_decimal_to_float(body)),
    }


__all__ = ['lambda_handler']
