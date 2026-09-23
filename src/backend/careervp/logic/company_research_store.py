"""Canonical Company Research artifact persistence for downstream resolution."""

from __future__ import annotations

import os
from datetime import timezone
from decimal import Decimal
from typing import Any

import boto3  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from careervp.dal import table_registry
from careervp.handlers.utils.observability import logger
from careervp.models.company import CompanyResearchResult

COMPANY_RESEARCH_ARTIFACT_TYPE = 'company_research'
COMPANY_RESEARCH_ARTIFACT_PREFIX = table_registry.COMPANY_RESEARCH_ARTIFACT_PREFIX
LEGACY_COMPANY_RESEARCH_PREFIX = table_registry.COMPANY_RESEARCH_KB_PREFIX

# FE-UI-053: terminal statuses whose rows write_cr_processing must never clobber.
_TERMINAL_CR_STATUSES = {'completed', 'failed'}


def cr_artifact_key(application_id: str) -> dict[str, str]:
    """Build the canonical artifacts-table key for a Company Research artifact."""
    clean_application_id = application_id.strip()
    return table_registry.canonical_item_key(
        clean_application_id,
        table_registry.company_research_artifact_sk(clean_application_id),
    )


def write_cr_artifact(application_id: str, user_id: str, result: CompanyResearchResult) -> None:
    """Write Company Research to the canonical artifacts table."""
    clean_application_id = application_id.strip()
    clean_user_id = user_id.strip()
    if not clean_application_id or not clean_user_id:
        logger.warning('Company Research persistence skipped: missing application/user id')
        return

    table_name = _artifacts_table_name()
    if table_name is None:
        logger.warning('Company Research persistence skipped: ARTIFACTS_TABLE_NAME not configured')
        return

    research_payload = _to_dynamo_value(result.model_dump(mode='json'))
    item: dict[str, Any] = {
        **cr_artifact_key(clean_application_id),
        'artifactType': COMPANY_RESEARCH_ARTIFACT_TYPE,
        'user_id': clean_user_id,
        'job_id': clean_application_id,
        'company_research_id': clean_application_id,
        'company_name': result.company_name,
        'overview': result.overview,
        'mission': result.mission,
        'values': result.values,
        'strategic_priorities': result.strategic_priorities,
        'recent_news': result.recent_news,
        'financial_summary': result.financial_summary,
        'key_products': result.key_products,
        'company_size': result.company_size,
        'key_executives': result.key_executives,
        'competitive_positioning': result.competitive_positioning,
        'growth_signals': result.growth_signals,
        'confidence_score': Decimal(str(result.confidence_score)),
        'created_at': result.research_timestamp.astimezone(timezone.utc).isoformat(),
        'research_data': research_payload,
    }

    try:
        _table(table_name).put_item(Item=item)
    except ClientError as exc:
        logger.warning(
            'Company Research canonical persistence failed',
            application_id=clean_application_id,
            table_name=table_name,
            error=str(exc),
        )


def write_cr_processing(application_id: str, user_id: str) -> None:
    """FE-UI-053 R2: upsert a `processing` placeholder row for an enqueued CR job.

    Idempotent and terminal-safe: writes only when no row exists or the existing
    row is non-terminal (e.g. ``not_generated`` or a prior ``processing``). A row
    that already holds research data or a terminal status (``completed``/``failed``)
    is never overwritten, so a worker result always wins over a re-POST.
    """
    clean_application_id = application_id.strip()
    clean_user_id = user_id.strip()
    if not clean_application_id or not clean_user_id:
        logger.warning('Company Research processing-row skipped: missing application/user id')
        return

    table_name = _artifacts_table_name()
    if table_name is None:
        logger.warning('Company Research processing-row skipped: ARTIFACTS_TABLE_NAME not configured')
        return

    if _has_terminal_cr_row(table_name=table_name, application_id=clean_application_id):
        logger.info(
            'Company Research processing-row skipped: terminal row already present',
            application_id=clean_application_id,
        )
        return

    item: dict[str, Any] = {
        **cr_artifact_key(clean_application_id),
        'artifactType': COMPANY_RESEARCH_ARTIFACT_TYPE,
        'user_id': clean_user_id,
        'job_id': clean_application_id,
        'company_research_id': clean_application_id,
        'status': 'processing',
        'created_at': _utc_now_iso(),
    }

    try:
        _table(table_name).put_item(Item=item)
    except ClientError as exc:
        logger.warning(
            'Company Research processing-row persistence failed',
            application_id=clean_application_id,
            table_name=table_name,
            error=str(exc),
        )


def write_cr_failed(application_id: str, user_id: str) -> None:
    """FE-UI-053 R6: write a `failed` terminal row unconditionally.

    Always overwrites any existing row (including a `processing` placeholder)
    so GET correctly reports failure after a hard-fail instead of staying stuck
    on `processing` forever.
    """
    clean_application_id = application_id.strip()
    clean_user_id = user_id.strip()
    if not clean_application_id or not clean_user_id:
        logger.warning('Company Research failed-row skipped: missing application/user id')
        return

    table_name = _artifacts_table_name()
    if table_name is None:
        logger.warning('Company Research failed-row skipped: ARTIFACTS_TABLE_NAME not configured')
        return

    item: dict[str, Any] = {
        **cr_artifact_key(clean_application_id),
        'artifactType': COMPANY_RESEARCH_ARTIFACT_TYPE,
        'user_id': clean_user_id,
        'job_id': clean_application_id,
        'company_research_id': clean_application_id,
        'status': 'failed',
        'created_at': _utc_now_iso(),
    }

    try:
        _table(table_name).put_item(Item=item)
    except ClientError as exc:
        logger.warning(
            'Company Research failed-row persistence failed',
            application_id=clean_application_id,
            table_name=table_name,
            error=str(exc),
        )


def _has_terminal_cr_row(table_name: str, application_id: str) -> bool:
    """Return True when an existing CR row is terminal and must not be overwritten."""
    try:
        response = _table(table_name).get_item(Key=cr_artifact_key(application_id))
    except ClientError as exc:
        _log_read_error('canonical', table_name=table_name, application_id=application_id, error=exc)
        return False

    item = response.get('Item') if isinstance(response, dict) else None
    if not isinstance(item, dict):
        return False

    status = str(item.get('status') or '').strip().lower()
    if status in _TERMINAL_CR_STATUSES:
        return True
    if status in {'processing', 'not_generated'}:
        return False
    # No explicit status: a worker-written row carries research data → terminal.
    return item.get('research_data') is not None or item.get('confidence_score') is not None


def _utc_now_iso() -> str:
    from datetime import datetime

    return datetime.now(timezone.utc).isoformat()


def read_cr_artifact(application_id: str, user_id: str, table_name: str | None = None) -> dict[str, Any] | None:
    """Read a Company Research artifact from canonical storage, then legacy fallback.

    ``table_name`` overrides the canonical artifacts table. Callers whose
    ARTIFACTS_TABLE_NAME points at a different table (e.g. the AI-assist Lambda,
    which reads most artifacts from users_table but CR from the dedicated
    artifacts_table) must pass the table that actually holds the CR row.
    """
    clean_application_id = application_id.strip()
    clean_user_id = user_id.strip()
    if not clean_application_id or not clean_user_id:
        return None

    canonical = _read_canonical_artifact(
        application_id=clean_application_id,
        user_id=clean_user_id,
        table_name=table_name,
    )
    if canonical is not None:
        return canonical

    if not _legacy_read_enabled():
        return None
    return _read_legacy_artifact(application_id=clean_application_id, user_id=clean_user_id)


def _read_canonical_artifact(application_id: str, user_id: str, table_name: str | None = None) -> dict[str, Any] | None:
    resolved_table_name = (table_name or '').strip() or _artifacts_table_name()
    if not resolved_table_name:
        return None
    table_name = resolved_table_name

    try:
        response = _table(table_name).get_item(Key=cr_artifact_key(application_id))
    except ClientError as exc:
        _log_read_error('canonical', table_name=table_name, application_id=application_id, error=exc)
        return None

    item = response.get('Item') if isinstance(response, dict) else None
    if not isinstance(item, dict):
        return None
    if item.get('artifactType') != COMPANY_RESEARCH_ARTIFACT_TYPE:
        return None
    if str(item.get('user_id') or '').strip() != user_id:
        return None
    return item


def _read_legacy_artifact(application_id: str, user_id: str) -> dict[str, Any] | None:
    table_name = _legacy_table_name()
    if table_name is None:
        return None

    for key in table_registry.company_research_candidate_keys(user_id, application_id):
        try:
            response = _table(table_name).get_item(Key=key)
        except ClientError as exc:
            _log_read_error('legacy', table_name=table_name, application_id=application_id, error=exc)
            continue

        item = response.get('Item') if isinstance(response, dict) else None
        if isinstance(item, dict) and str(item.get('user_id') or '').strip() == user_id:
            return item
    return None


def _artifacts_table_name() -> str | None:
    return _clean_env('ARTIFACTS_TABLE_NAME')


def _legacy_table_name() -> str | None:
    return _clean_env('TABLE_NAME') or _clean_env('DYNAMODB_TABLE_NAME')


def _clean_env(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _legacy_read_enabled() -> bool:
    raw = os.environ.get('COMPANY_RESEARCH_LEGACY_READ_ENABLED', 'true').strip().lower()
    return raw not in {'0', 'false', 'no', 'off'}


def _table(table_name: str) -> Any:
    return boto3.resource('dynamodb').Table(table_name)


def _to_dynamo_value(value: Any) -> Any:
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {str(key): _to_dynamo_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_dynamo_value(item) for item in value]
    return value


def _log_read_error(kind: str, *, table_name: str, application_id: str, error: ClientError) -> None:
    error_code = error.response.get('Error', {}).get('Code')
    if error_code == 'ResourceNotFoundException':
        logger.warning(
            'Company Research table not found',
            store_kind=kind,
            table_name=table_name,
            application_id=application_id,
        )
        return
    logger.warning(
        'Company Research read failed',
        store_kind=kind,
        table_name=table_name,
        application_id=application_id,
        error=str(error),
    )


__all__ = ['cr_artifact_key', 'read_cr_artifact', 'write_cr_artifact', 'write_cr_failed', 'write_cr_processing']
