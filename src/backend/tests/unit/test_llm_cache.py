"""Unit tests for DynamoDB-backed LLM response cache."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from careervp.logic.llm_cache import LLMResponseCache


class FakeDynamoTable:
    """In-memory table stub with DynamoDB-like methods."""

    def __init__(self) -> None:
        self.items: dict[str, dict[str, Any]] = {}

    def get_item(self, *, Key: dict[str, str]) -> Mapping[str, Any]:  # noqa: N803
        cache_key = Key['cache_key']
        item = self.items.get(cache_key)
        if item is None:
            return {}
        return {'Item': item}

    def put_item(self, *, Item: Mapping[str, Any]) -> Mapping[str, Any]:  # noqa: N803
        cache_key = str(Item['cache_key'])
        self.items[cache_key] = dict(Item)
        return {}

    def delete_item(self, *, Key: dict[str, str]) -> Mapping[str, Any]:  # noqa: N803
        cache_key = Key['cache_key']
        self.items.pop(cache_key, None)
        return {}


def test_cache_hit_returns_stored_value() -> None:
    table = FakeDynamoTable()
    cache = LLMResponseCache(table_name='test-llm-cache', table=table)

    assert cache.set('cache-key', 'cached-response') is True
    assert cache.get('cache-key') == 'cached-response'


def test_cache_miss_returns_none() -> None:
    cache = LLMResponseCache(table_name='test-llm-cache', table=FakeDynamoTable())
    assert cache.get('missing-key') is None


def test_cache_key_generation_is_deterministic() -> None:
    key_one = LLMResponseCache.generate_cache_key(
        prompt='Tailor this CV for backend roles',
        cv_id='cv-123',
        model_name='claude-haiku-4-5-20251001',
        temperature=0.3,
    )
    key_two = LLMResponseCache.generate_cache_key(
        prompt='Tailor this CV for backend roles',
        cv_id='cv-123',
        model_name='claude-haiku-4-5-20251001',
        temperature=0.3,
    )
    key_three = LLMResponseCache.generate_cache_key(
        prompt='Tailor this CV for backend roles',
        cv_id='cv-999',
        model_name='claude-haiku-4-5-20251001',
        temperature=0.3,
    )

    assert key_one == key_two
    assert key_one != key_three
    assert len(key_one) == 64


def test_cache_ttl_expiration() -> None:
    current_time = [1_700_000_000]

    def now_provider() -> int:
        return current_time[0]

    table = FakeDynamoTable()
    cache = LLMResponseCache(
        table_name='test-llm-cache',
        table=table,
        now_provider=now_provider,
    )

    assert cache.set('expiring-key', 'value', ttl_seconds=2) is True
    assert cache.get('expiring-key') == 'value'

    current_time[0] += 3
    assert cache.get('expiring-key') is None
    assert 'expiring-key' not in table.items


def test_cache_hit_with_decimal_ttl() -> None:
    table = FakeDynamoTable()
    table.items['decimal-key'] = {
        'cache_key': 'decimal-key',
        'response_value': 'cached-response',
        'expires_at': Decimal('9999999999'),
    }
    cache = LLMResponseCache(table_name='test-llm-cache', table=table)

    assert cache.get('decimal-key') == 'cached-response'


def test_is_cacheable_excludes_temporal_queries() -> None:
    cache = LLMResponseCache(table_name='test-llm-cache', table=FakeDynamoTable())

    assert cache.is_cacheable('Summarize this candidate profile and key strengths') is True
    assert cache.is_cacheable('What are the latest hiring trends?') is False
    assert cache.is_cacheable('Give me current salary benchmarks') is False
    assert cache.is_cacheable('List the best options for today') is False
