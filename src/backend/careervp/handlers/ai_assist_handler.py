"""Lambda handler for the synchronous field-scoped AI-assist endpoint (FE-UI-046).

POST /ai/assist rewrites ONE artifact field with server-resolved cross-artifact
context. The server NEVER trusts the client for context — only
artifact_type/artifact_id/application_id/field_key/current_text/locale come from
the request. The artifact under edit is NOT re-fetched (current_text is
authoritative). The call is free with an active subscription/trial and consumes
no application credit.

Infrastructure (Lambda, IAM role, route registration) is owned by FE-UI-047.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
from http import HTTPStatus
from typing import Any

from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from careervp.dal.application_repository import ApplicationRepository
from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.handlers.auth_utils import extract_user_id
from careervp.handlers.cors_utils import get_cors_headers, set_request_origin
from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.logic.llm_cache import LLMResponseCache
from careervp.logic.llm_client import (
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    BedrockInvocationError,
    CircuitBreakerOpen,
    LLMClient,
)
from careervp.logic.prompts.ai_assist_prompt import (
    REQUIRED_UPSTREAM,
    AssistContext,
    build_system_preamble,
    build_user_message,
)
from careervp.models.api_models import AIAssistRequest
from careervp.models.result import ResultCode

# One safety margin below the 29 s API Gateway hard ceiling.
DEFAULT_ASSIST_TIMEOUT_SECONDS = 25
DEFAULT_ASSIST_MAX_TOKENS = 1200


class UpstreamMissingError(Exception):
    """Raised when a required upstream artifact is absent (mapped to 409)."""

    def __init__(self, artifact_type: str, missing: str, application_id: str) -> None:
        super().__init__(f'Missing upstream artifact {missing!r} for {artifact_type!r}')
        self.artifact_type = artifact_type
        self.missing = missing
        self.application_id = application_id


# ─── Table-name resolution helpers ────────────────────────────────────────────


def _artifacts_table_name() -> str:
    for env_key in ('ARTIFACTS_TABLE_NAME', 'DYNAMODB_TABLE_NAME', 'TABLE_NAME'):
        value = os.environ.get(env_key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ''


def _applications_table_name() -> str:
    for env_key in ('APPLICATIONS_TABLE_NAME', 'DYNAMODB_TABLE_NAME', 'TABLE_NAME'):
        value = os.environ.get(env_key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ''


def _get_dal() -> DynamoDalHandler:
    return DynamoDalHandler(_artifacts_table_name())


# ─── Entry point ──────────────────────────────────────────────────────────────


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Handle POST /ai/assist requests."""
    _ = context
    set_request_origin(event)

    method = str(event.get('httpMethod', '')).upper()
    path = str(event.get('path', '')).rstrip('/')

    if method == 'OPTIONS':
        return _build_response(HTTPStatus.OK, {'status': 'ok'})

    if method == 'POST' and path == '/ai/assist':
        return _handle_assist(event)

    return _build_response(
        HTTPStatus.NOT_FOUND,
        {'error': 'Endpoint not found', 'code': ResultCode.INVALID_INPUT},
    )


def _handle_assist(event: dict[str, Any]) -> dict[str, Any]:
    user_id = extract_user_id(event)
    if not user_id:
        return _build_response(
            HTTPStatus.UNAUTHORIZED,
            {'error': 'Missing or invalid authentication token', 'code': ResultCode.UNAUTHORIZED},
        )

    api_request = _parse_request(event)
    if api_request is None:
        metrics.add_metric(name='AIAssistBadRequest', unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.BAD_REQUEST,
            {'error': 'Invalid AI-assist request', 'code': ResultCode.INVALID_INPUT},
        )

    # Ownership: application_id must belong to the JWT user.
    if not _user_owns_application(user_id=user_id, application_id=api_request.application_id):
        metrics.add_metric(name='AIAssistOwnershipDenied', unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.FORBIDDEN,
            {'error': 'Application not found for this user', 'code': ResultCode.FORBIDDEN},
        )

    try:
        context = _resolve_context(user_id=user_id, api_request=api_request)
    except UpstreamMissingError as exc:
        metrics.add_metric(name='AIAssistUpstreamMissing', unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.CONFLICT,
            {
                'error': f'Required upstream artifact is missing: {exc.missing}',
                'code': ResultCode.INVALID_INPUT,
                'missing_artifact': exc.missing,
                'artifact_type': exc.artifact_type,
                'application_id': exc.application_id,
            },
        )
    except Exception as exc:  # noqa: BLE001 - context resolution failure is a server error
        logger.error('AI-assist context resolution failed', user_id=user_id, error=str(exc), exc_info=True)
        return _build_response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {'error': 'Could not assemble assist context', 'code': ResultCode.INTERNAL_ERROR},
        )

    return _generate(api_request=api_request, context=context)


def _generate(api_request: AIAssistRequest, context: AssistContext) -> dict[str, Any]:
    system_prompt = build_system_preamble(api_request.artifact_type, api_request.locale)
    user_message = build_user_message(
        artifact_type=api_request.artifact_type,
        field_key=api_request.field_key,
        current_text=api_request.current_text,
        context=context,
    )

    model_name = os.environ.get('AI_ASSIST_MODEL', DEFAULT_MODEL)
    temperature = DEFAULT_TEMPERATURE
    cache = _get_cache()
    cache_key = _cache_key(api_request, user_message, model_name, temperature)

    cached = _read_cache(cache, cache_key)
    if cached is not None:
        metrics.add_metric(name='AIAssistCacheHit', unit=MetricUnit.Count, value=1)
        return _build_response(HTTPStatus.OK, cached)

    try:
        generated = _call_llm(system_prompt=system_prompt, user_message=user_message, model_name=model_name, temperature=temperature)
    except CircuitBreakerOpen as exc:
        metrics.add_metric(name='AIAssistCircuitOpen', unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.SERVICE_UNAVAILABLE,
            {'error': 'AI service temporarily unavailable', 'code': ResultCode.LLM_API_ERROR, 'retry_after': exc.retry_after},
        )
    except (concurrent.futures.TimeoutError, TimeoutError):
        metrics.add_metric(name='AIAssistTimeout', unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.GATEWAY_TIMEOUT,
            {'error': 'AI-assist timed out', 'code': ResultCode.LLM_TIMEOUT},
        )
    except BedrockInvocationError as exc:
        if 'timeout' in str(exc).lower():
            metrics.add_metric(name='AIAssistTimeout', unit=MetricUnit.Count, value=1)
            return _build_response(
                HTTPStatus.GATEWAY_TIMEOUT,
                {'error': 'AI-assist timed out', 'code': ResultCode.LLM_TIMEOUT},
            )
        metrics.add_metric(name='AIAssistProviderError', unit=MetricUnit.Count, value=1)
        return _build_response(
            HTTPStatus.SERVICE_UNAVAILABLE,
            {'error': 'AI service temporarily unavailable', 'code': ResultCode.LLM_API_ERROR},
        )
    except Exception as exc:  # noqa: BLE001 - unexpected failure must be a safe 500
        logger.error('AI-assist generation failed', error=str(exc), exc_info=True)
        return _build_response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {'error': 'AI-assist failed', 'code': ResultCode.INTERNAL_ERROR},
        )

    generated_markdown = generated.strip()
    if not generated_markdown:
        return _build_response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {'error': 'AI-assist returned no content', 'code': ResultCode.INTERNAL_ERROR},
        )

    tokens = _estimate_tokens(system_prompt, user_message, generated_markdown)
    payload = {'generated_markdown': generated_markdown, 'model': model_name, 'tokens': tokens}
    _write_cache(cache, cache_key, payload)
    metrics.add_metric(name='AIAssistGenerated', unit=MetricUnit.Count, value=1)
    return _build_response(HTTPStatus.OK, payload)


def _call_llm(system_prompt: str, user_message: str, model_name: str, temperature: float) -> str:
    """Invoke the LLM with a hard wall-clock budget below the APIGW ceiling."""
    client = LLMClient()

    def _invoke() -> str:
        response = client.complete(
            prompt=user_message,
            system_prompt=system_prompt,
            max_tokens=DEFAULT_ASSIST_MAX_TOKENS,
            model_name=model_name,
            temperature=temperature,
            use_system_cache=True,
        )
        return response.text

    budget = _timeout_seconds()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_invoke)
        return future.result(timeout=budget)


# ─── Request parsing ──────────────────────────────────────────────────────────


def _parse_request(event: dict[str, Any]) -> AIAssistRequest | None:
    body_content = event.get('body', '{}')
    try:
        payload = json.loads(body_content or '{}')
    except (TypeError, json.JSONDecodeError):
        logger.warning('Invalid JSON body for AI-assist request')
        return None
    try:
        return AIAssistRequest.model_validate(payload)
    except ValidationError:
        logger.warning('AIAssistRequest validation failed')
        return None


# ─── Ownership + entitlement ──────────────────────────────────────────────────


def _user_owns_application(user_id: str, application_id: str) -> bool:
    table_name = _applications_table_name()
    if not table_name:
        return False
    try:
        repo = ApplicationRepository(DynamoDalHandler(table_name))
        record = repo.get(application_id=application_id, user_id=user_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning('AI-assist ownership check failed', application_id=application_id, error=str(exc))
        return False
    return record is not None


# ─── Context resolution (server-side only) ────────────────────────────────────


def _resolve_context(user_id: str, api_request: AIAssistRequest) -> AssistContext:
    dal = _get_dal()
    artifact_type = api_request.artifact_type
    application_id = api_request.application_id
    required = REQUIRED_UPSTREAM.get(artifact_type, ())
    context = AssistContext()

    if 'cv' in required or artifact_type in {'gap_analysis', 'cv_tailored'}:
        context.cv = _load_cv(dal, user_id)
        if 'cv' in required and context.cv is None:
            raise UpstreamMissingError(artifact_type, 'cv', application_id)

    if 'vpr' in required:
        context.vpr = _load_vpr(dal, application_id=application_id, user_id=user_id)
        if context.vpr is None:
            raise UpstreamMissingError(artifact_type, 'vpr', application_id)

    # Gap responses feed cv_tailored, cover_letter, interview_prep (best-effort).
    if artifact_type in {'cv_tailored', 'cover_letter', 'interview_prep'}:
        context.gap_responses = _load_gap_responses(dal, user_id)

    if 'tailored_cv' in required:
        context.tailored_cv = _load_tailored_cv(dal, user_id=user_id, application_id=application_id)
        if context.tailored_cv is None:
            raise UpstreamMissingError(artifact_type, 'tailored_cv', application_id)

    if 'company_research' in required:
        context.company_research = _load_company_research(dal, user_id=user_id, application_id=application_id)
        if context.company_research is None:
            raise UpstreamMissingError(artifact_type, 'company_research', application_id)

    return context


def _load_cv(dal: DynamoDalHandler, user_id: str) -> Any | None:
    candidates: list[DynamoDalHandler] = []
    cv_table = os.environ.get('CVS_TABLE_NAME', '').strip()
    if cv_table and cv_table != dal.table_name:
        candidates.append(DynamoDalHandler(cv_table))
    candidates.append(dal)
    for cv_dal in candidates:
        try:
            cv = cv_dal.get_cv(user_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning('AI-assist CV lookup failed', table_name=cv_dal.table_name, error=str(exc))
            continue
        if cv is not None:
            return cv
    return None


def _load_vpr(dal: DynamoDalHandler, application_id: str, user_id: str) -> Any | None:
    try:
        result = dal.get_vpr(application_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning('AI-assist VPR lookup failed', application_id=application_id, error=str(exc))
        return None
    if not getattr(result, 'success', False) or result.data is None:
        return None
    vpr = result.data
    owner = getattr(vpr, 'user_id', None) if not isinstance(vpr, dict) else vpr.get('user_id')
    if owner is not None and str(owner).strip() != user_id:
        logger.warning('AI-assist VPR ownership mismatch', application_id=application_id)
        return None
    return vpr


def _load_gap_responses(dal: DynamoDalHandler, user_id: str) -> list[Any]:
    candidates: list[DynamoDalHandler] = []
    gap_table = os.environ.get('GAP_RESPONSES_TABLE_NAME', '').strip()
    if gap_table and gap_table != dal.table_name:
        candidates.append(DynamoDalHandler(gap_table))
    candidates.append(dal)
    for gap_dal in candidates:
        try:
            result = gap_dal.get_gap_responses(user_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning('AI-assist gap responses lookup failed', table_name=gap_dal.table_name, error=str(exc))
            continue
        if getattr(result, 'success', False) and result.data:
            return list(result.data)
    return []


def _load_tailored_cv(dal: DynamoDalHandler, user_id: str, application_id: str) -> Any | None:
    """Load the latest tailored-CV artifact for an application.

    Mirrors the canonical read in export_handler._read_cv_tailored: the artifact
    is stored with pk=user_id, sk=ARTIFACT#CV_TAILORED#{request_id} and the
    application_id lives in the `job_id` ATTRIBUTE (not the sort key). We must
    therefore filter on job_id, not on the sk.
    """
    from boto3.dynamodb.conditions import Attr, Key

    from careervp.dal.dynamo_dal_handler import TAILORED_CV_SORT_KEY_PREFIX

    try:
        table = dal._get_db_handler(dal.table_name)
        response = table.query(
            KeyConditionExpression=Key('pk').eq(user_id) & Key('sk').begins_with(TAILORED_CV_SORT_KEY_PREFIX),
            FilterExpression=Attr('job_id').eq(application_id),
        )
        items = response.get('Items', []) if isinstance(response, dict) else []
        if not items:
            return None
        # Most recently created artifact wins (parity with export_handler).
        items.sort(key=lambda item: str(item.get('created_at') or ''), reverse=True)
        latest = items[0]
        if isinstance(latest, dict):
            return latest.get('cv_sections') or latest.get('tailored_cv') or latest
    except Exception as exc:  # noqa: BLE001
        logger.warning('AI-assist tailored CV lookup failed', application_id=application_id, error=str(exc))
    return None


def _load_company_research(dal: DynamoDalHandler, user_id: str, application_id: str) -> Any | None:
    """Load Company Research for an application.

    Company Research lives in its own canonical store keyed by
    applicationId/artifactId (NOT the pk/sk schema used by dal.get_company_research),
    with a legacy pk/sk fallback. We mirror the proven GET /company-research reader
    (read_cr_artifact) first, then fall back to the DAL pk/sk lookup so every
    storage layout that ever held a CR record is covered.
    """
    from careervp.handlers.cover_letter_handler import _materialize_company_research

    raw_item = _read_company_research_item(dal, user_id=user_id, application_id=application_id)
    if not isinstance(raw_item, dict):
        return None
    return _materialize_company_research(raw_item, fallback_company_name='')


def _read_company_research_item(dal: DynamoDalHandler, user_id: str, application_id: str) -> dict[str, Any] | None:
    from careervp.logic.company_research_store import read_cr_artifact

    try:
        canonical = read_cr_artifact(application_id=application_id, user_id=user_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning('AI-assist company research canonical lookup failed', application_id=application_id, error=str(exc))
        canonical = None
    if isinstance(canonical, dict):
        return canonical

    try:
        result = dal.get_company_research(user_id=user_id, job_id=application_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning('AI-assist company research lookup failed', application_id=application_id, error=str(exc))
        return None
    if getattr(result, 'success', False) and isinstance(result.data, dict):
        return result.data
    return None


# ─── Cache helpers (AC-012) ───────────────────────────────────────────────────


def _get_cache() -> LLMResponseCache:
    return LLMResponseCache(table_name=os.environ.get('LLM_CACHE_TABLE_NAME'))


def _cache_key(api_request: AIAssistRequest, user_message: str, model_name: str, temperature: float) -> str | None:
    # The key MUST include field_key + current_text so distinct fields / edits do
    # not collide. The user_message already embeds both, but we prefix them
    # explicitly to make the contract unambiguous and order-stable.
    seed = '\n'.join(
        [
            'ai_assist',
            api_request.artifact_type,
            api_request.locale,
            api_request.field_key,
            api_request.current_text,
            user_message,
        ]
    )
    return LLMResponseCache.generate_cache_key(prompt=seed, cv_id=None, model_name=model_name, temperature=temperature)


def _read_cache(cache: LLMResponseCache, cache_key: str | None) -> dict[str, Any] | None:
    if cache_key is None:
        return None
    try:
        cached_value = cache.get(cache_key)
    except Exception:  # noqa: BLE001
        return None
    if not cached_value:
        return None
    try:
        parsed = json.loads(cached_value)
    except (TypeError, json.JSONDecodeError):
        return None
    if isinstance(parsed, dict) and parsed.get('generated_markdown'):
        return parsed
    return None


def _write_cache(cache: LLMResponseCache, cache_key: str | None, payload: dict[str, Any]) -> None:
    if cache_key is None:
        return
    try:
        cache.set(cache_key, json.dumps(payload, ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001
        logger.warning('AI-assist cache write failed', error=str(exc))


# ─── Misc helpers ─────────────────────────────────────────────────────────────


def _timeout_seconds() -> int:
    raw = str(os.environ.get('AI_ASSIST_TIMEOUT_SECONDS', DEFAULT_ASSIST_TIMEOUT_SECONDS)).strip()
    try:
        parsed = int(raw)
    except ValueError:
        return DEFAULT_ASSIST_TIMEOUT_SECONDS
    return max(1, parsed)


def _estimate_tokens(*parts: str) -> int:
    total_chars = sum(len(part) for part in parts)
    return max(1, total_chars // 4)


def _build_response(status_code: HTTPStatus, body: dict[str, Any]) -> dict[str, Any]:
    headers = get_cors_headers(None)
    headers['Content-Type'] = 'application/json'
    return {
        'statusCode': status_code.value,
        'headers': headers,
        'body': json.dumps(body),
    }


__all__ = ['lambda_handler', 'UpstreamMissingError']
