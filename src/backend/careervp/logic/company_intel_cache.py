"""Shared cross-user company-intel cache backed by DynamoDB."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Literal, Mapping
from urllib.parse import urlparse

import boto3  # type: ignore[import-untyped]
from botocore.exceptions import BotoCoreError, ClientError  # type: ignore[import-untyped]

from careervp.handlers.utils.observability import logger
from careervp.models.company import CompanyResearchResult

CacheKind = Literal['profile', 'news']

PROFILE_TTL_SECONDS = 183 * 24 * 60 * 60
NEWS_TTL_SECONDS = 120 * 24 * 60 * 60
LOCK_TTL_SECONDS = 30
COMPANY_RESEARCH_CACHE_TABLE_ENV = 'COMPANY_RESEARCH_CACHE_TABLE_NAME'

PROFILE_FIELDS = (
    'company_name',
    'mission',
    'values',
    'strategic_priorities',
    'industry',
    'key_products',
    'company_size',
    'key_executives',
    'competitive_positioning',
    'overview',
    'financial_summary',
)
NEWS_FIELDS = ('recent_news', 'growth_signals')
METADATA_FIELDS = ('source', 'source_urls', 'confidence_score', 'research_timestamp')
COMPANY_SUFFIX_PATTERN = re.compile(
    r'\b(incorporated|inc|limited|ltd|corporation|corp|company|co|llc|plc|gmbh|ag|sa|s\.a|bv|l\.l\.c)\b\.?',
    re.IGNORECASE,
)
COMMON_SECOND_LEVEL_SUFFIXES = {
    'co.uk',
    'com.au',
    'com.br',
    'com.sg',
    'com.mx',
    'co.il',
    'co.in',
    'co.jp',
}

_missing_env_logged = False


@dataclass(frozen=True)
class CachedProfile:
    """Fresh stable company profile cache payload."""

    key: str
    data: dict[str, Any]
    expires_at: int


@dataclass(frozen=True)
class CachedNews:
    """Fresh volatile company news cache payload."""

    key: str
    data: dict[str, Any]
    expires_at: int


def cache_key(domain_or_name: str, kind: CacheKind) -> str | None:
    """Return the DynamoDB key for a normalized company profile/news record."""
    normalized = normalize_company_cache_subject(domain_or_name)
    if normalized is None:
        return None
    return f'COMPANY#{normalized}#{kind}'


def company_cache_keys(*, company_name: str, domain: str | None) -> tuple[str, str, str] | None:
    """Build profile, news, and lock keys, preferring domain over company name."""
    normalized = normalize_company_cache_subject(domain or company_name)
    if normalized is None:
        return None
    return (f'COMPANY#{normalized}#profile', f'COMPANY#{normalized}#news', f'COMPANY#{normalized}#lock')


def normalize_company_cache_subject(domain_or_name: str) -> str | None:
    """Normalize a domain or company name into the cross-user cache subject."""
    raw_value = domain_or_name.strip()
    if not raw_value:
        return None

    domain = _normalize_registered_domain(raw_value)
    if domain is not None:
        return domain

    normalized_name = COMPANY_SUFFIX_PATTERN.sub('', raw_value.lower())
    normalized_name = re.sub(r'[^a-z0-9]+', '-', normalized_name).strip('-')
    return normalized_name or None


def read_profile(key: str) -> CachedProfile | None:
    """Read a fresh profile cache record. Returns None for misses, expiry, or DynamoDB errors."""
    item = _read_item(key, expected_kind='profile')
    if item is None:
        return None
    return CachedProfile(key=key, data=_item_data(item), expires_at=_coerce_epoch(item.get('expiresAt')))


def read_news(key: str) -> CachedNews | None:
    """Read a fresh news cache record. Returns None for misses, expiry, or DynamoDB errors."""
    item = _read_item(key, expected_kind='news')
    if item is None:
        return None
    return CachedNews(key=key, data=_item_data(item), expires_at=_coerce_epoch(item.get('expiresAt')))


def write_profile(key: str, data: CompanyResearchResult, *, ttl_seconds: int = PROFILE_TTL_SECONDS) -> None:
    """Write stable profile fields to the shared cache."""
    payload = data.model_dump(mode='json')
    _write_item(key, kind='profile', data={field: payload.get(field) for field in (*PROFILE_FIELDS, *METADATA_FIELDS)}, ttl_seconds=ttl_seconds)


def write_news(key: str, data: CompanyResearchResult, *, ttl_seconds: int = NEWS_TTL_SECONDS) -> None:
    """Write volatile news fields to the shared cache."""
    payload = data.model_dump(mode='json')
    _write_item(key, kind='news', data={field: payload.get(field) for field in (*NEWS_FIELDS, *METADATA_FIELDS)}, ttl_seconds=ttl_seconds)


def acquire_lock(key: str, *, lock_ttl_seconds: int = LOCK_TTL_SECONDS) -> bool:
    """Acquire a short in-flight lock using a conditional DynamoDB write."""
    table = _table()
    if table is None:
        return True

    now = _now_epoch()
    try:
        table.put_item(
            Item={
                'cacheKey': _lock_key(key),
                'kind': 'lock',
                'expiresAt': now + lock_ttl_seconds,
                'updatedAt': _now().isoformat(),
            },
            ConditionExpression='attribute_not_exists(cacheKey) OR expiresAt < :now',
            ExpressionAttributeValues={':now': now},
        )
    except ClientError as exc:
        error_code = exc.response.get('Error', {}).get('Code')
        if error_code == 'ConditionalCheckFailedException':
            return False
        _log_cache_error('Company intel cache lock failed', key=key, error=exc)
        return True
    except BotoCoreError as exc:
        _log_cache_error('Company intel cache lock failed', key=key, error=exc)
        return True
    return True


def release_lock(key: str) -> None:
    """Release a previously acquired in-flight lock."""
    table = _table()
    if table is None:
        return
    try:
        table.delete_item(Key={'cacheKey': _lock_key(key)})
    except (BotoCoreError, ClientError) as exc:
        _log_cache_error('Company intel cache lock release failed', key=key, error=exc)


def merge_cached_company_research(
    profile: CachedProfile,
    news: CachedNews | None,
    *,
    fallback_company_name: str,
) -> CompanyResearchResult | None:
    """Merge split profile/news cache records into a CompanyResearchResult."""
    payload: dict[str, Any] = dict(profile.data)
    if news is not None:
        payload.update({field: news.data.get(field) for field in NEWS_FIELDS})
        payload['source_urls'] = _merge_urls(profile.data.get('source_urls'), news.data.get('source_urls'))
        payload['confidence_score'] = _merge_confidence(profile.data.get('confidence_score'), news.data.get('confidence_score'))

    payload['company_name'] = _non_empty_text(payload.get('company_name')) or fallback_company_name
    try:
        return CompanyResearchResult.model_validate(payload)
    except Exception as exc:  # noqa: BLE001
        _log_cache_error('Company intel cache payload invalid', key=profile.key, error=exc)
        return None


def _read_item(key: str, *, expected_kind: CacheKind) -> dict[str, Any] | None:
    table = _table()
    if table is None:
        return None
    try:
        response = table.get_item(Key={'cacheKey': key})
    except (BotoCoreError, ClientError) as exc:
        _log_cache_error('Company intel cache read failed', key=key, error=exc)
        return None

    item = response.get('Item') if isinstance(response, dict) else None
    if not isinstance(item, dict):
        return None
    if item.get('kind') != expected_kind:
        return None
    if _coerce_epoch(item.get('expiresAt')) <= _now_epoch():
        return None
    return item


def _write_item(key: str, *, kind: CacheKind, data: Mapping[str, Any], ttl_seconds: int) -> None:
    table = _table()
    if table is None:
        return
    now = _now()
    try:
        table.put_item(
            Item={
                'cacheKey': key,
                'kind': kind,
                'data': _to_dynamo_value(dict(data)),
                'expiresAt': int(now.timestamp()) + ttl_seconds,
                'updatedAt': now.isoformat(),
            }
        )
    except (BotoCoreError, ClientError) as exc:
        _log_cache_error('Company intel cache write failed', key=key, error=exc)


def _table() -> Any | None:
    table_name = _table_name()
    if table_name is None:
        return None
    return boto3.resource('dynamodb').Table(table_name)


def _table_name() -> str | None:
    global _missing_env_logged
    value = os.environ.get(COMPANY_RESEARCH_CACHE_TABLE_ENV, '').strip()
    if value:
        return value
    if not _missing_env_logged:
        logger.warning('Company intel cache disabled: table env var not configured')
        _missing_env_logged = True
    return None


def _normalize_registered_domain(raw_value: str) -> str | None:
    if re.search(r'\s', raw_value):
        return None
    parsed = urlparse(raw_value if '://' in raw_value else f'https://{raw_value}')
    hostname = (parsed.hostname or '').lower().removeprefix('www.')
    if not hostname or '.' not in hostname:
        return None
    labels = [label for label in hostname.split('.') if label]
    if len(labels) < 2:
        return None
    suffix = '.'.join(labels[-2:])
    if suffix in COMMON_SECOND_LEVEL_SUFFIXES and len(labels) >= 3:
        return '.'.join(labels[-3:])
    return suffix


def _lock_key(key: str) -> str:
    for suffix in ('#profile', '#news', '#lock'):
        if key.endswith(suffix):
            return f'{key.removesuffix(suffix)}#lock'
    return f'{key}#lock'


def _item_data(item: Mapping[str, Any]) -> dict[str, Any]:
    data = item.get('data')
    if not isinstance(data, dict):
        return {}
    converted = _from_dynamo_value(data)
    if isinstance(converted, dict):
        return converted
    return {}


def _to_dynamo_value(value: Any) -> Any:
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {str(key): _to_dynamo_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_dynamo_value(item) for item in value]
    return value


def _from_dynamo_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    if isinstance(value, dict):
        return {str(key): _from_dynamo_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_from_dynamo_value(item) for item in value]
    return value


def _merge_urls(first: Any, second: Any) -> list[str]:
    urls: list[str] = []
    for value in (first, second):
        if isinstance(value, list):
            urls.extend(str(item) for item in value if str(item).strip())
    seen: set[str] = set()
    merged: list[str] = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        merged.append(url)
    return merged


def _merge_confidence(first: Any, second: Any) -> float:
    values = [_coerce_float(value) for value in (first, second)]
    clean_values = [value for value in values if value is not None]
    if not clean_values:
        return 0.0
    return min(clean_values)


def _coerce_float(value: Any) -> float | None:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _coerce_epoch(value: Any) -> int:
    if isinstance(value, Decimal):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return 0


def _non_empty_text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_epoch() -> int:
    return int(_now().timestamp())


def _log_cache_error(message: str, *, key: str, error: Exception) -> None:
    logger.warning(message, cache_key=key, error=str(error))


__all__ = [
    'CachedNews',
    'CachedProfile',
    'NEWS_TTL_SECONDS',
    'PROFILE_TTL_SECONDS',
    'acquire_lock',
    'cache_key',
    'company_cache_keys',
    'merge_cached_company_research',
    'normalize_company_cache_subject',
    'read_news',
    'read_profile',
    'release_lock',
    'write_news',
    'write_profile',
]
