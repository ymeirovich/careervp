"""DynamoDB-backed cache for reusing deterministic LLM responses."""

from __future__ import annotations

import hashlib
import os
import time
from collections.abc import Callable, Mapping
from decimal import Decimal
from typing import Any, Protocol, cast

import boto3
from botocore.exceptions import BotoCoreError, ClientError

DEFAULT_CACHE_TTL_SECONDS = 60 * 60 * 24 * 7


class DynamoTableProtocol(Protocol):
    """Subset of DynamoDB table operations used by the cache."""

    def get_item(self, *, Key: dict[str, str]) -> Mapping[str, Any]: ...  # noqa: N803

    def put_item(self, *, Item: Mapping[str, Any]) -> Mapping[str, Any]: ...  # noqa: N803

    def delete_item(self, *, Key: dict[str, str]) -> Mapping[str, Any]: ...  # noqa: N803


class LLMResponseCache:
    """Cache LLM responses in DynamoDB using per-item TTL."""

    _TEMPORAL_KEYWORDS = ('today', 'current', 'latest')

    def __init__(
        self,
        table_name: str | None = None,
        table: DynamoTableProtocol | None = None,
        now_provider: Callable[[], int] | None = None,
    ) -> None:
        resolved_table_name = table_name or os.getenv('LLM_CACHE_TABLE_NAME')
        self._now_provider = now_provider or self._current_epoch_seconds
        self._table: DynamoTableProtocol | None
        if table is not None:
            self._table = table
        elif resolved_table_name:
            resource = boto3.resource('dynamodb')
            self._table = cast(DynamoTableProtocol, resource.Table(resolved_table_name))
        else:
            self._table = None

    @staticmethod
    def generate_cache_key(prompt: str, cv_id: str | None, model_name: str, temperature: float) -> str:
        # Stable SHA-256 key minimizes collisions and keeps partition keys compact.
        normalized = f'{prompt}|{cv_id or ""}|{model_name}|{temperature:.6f}'
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def get(self, key: str) -> str | None:
        """Return cached response when present and not expired."""
        if not key or self._table is None:
            return None

        try:
            response = self._table.get_item(Key={'cache_key': key})
        except (BotoCoreError, ClientError):
            return None

        item = response.get('Item')
        if not isinstance(item, Mapping):
            return None

        cached_value = item.get('response_value')
        if not isinstance(cached_value, str):
            return None

        expires_at = self._to_int(item.get('expires_at'))
        if expires_at is None:
            return None

        # DynamoDB TTL deletion is eventually consistent, so enforce expiration on read too.
        if expires_at <= self._now_provider():
            self.delete(key)
            return None
        return cached_value

    def set(self, key: str, value: str, ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS) -> bool:
        """Store cached response with a TTL epoch timestamp."""
        if not key or self._table is None:
            return False

        expires_at = self._now_provider() + max(ttl_seconds, 1)
        try:
            self._table.put_item(
                Item={
                    'cache_key': key,
                    'response_value': value,
                    'expires_at': expires_at,
                }
            )
            return True
        except (BotoCoreError, ClientError):
            return False

    def delete(self, key: str) -> bool:
        """Delete a cache entry by key."""
        if not key or self._table is None:
            return False

        try:
            self._table.delete_item(Key={'cache_key': key})
            return True
        except (BotoCoreError, ClientError):
            return False

    def is_cacheable(self, prompt: str) -> bool:
        """Avoid caching prompts likely to require fresh temporal data."""
        normalized_prompt = prompt.lower()
        return not any(keyword in normalized_prompt for keyword in self._TEMPORAL_KEYWORDS)

    @staticmethod
    def _to_int(value: Any) -> int | None:
        if isinstance(value, int):
            return value
        if isinstance(value, Decimal):
            return int(value)
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return None

    @staticmethod
    def _current_epoch_seconds() -> int:
        return int(time.time())
