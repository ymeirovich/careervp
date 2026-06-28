"""Unit tests for the shared company-intel cache."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Generator, cast
from unittest.mock import AsyncMock, patch

import boto3
import pytest
from botocore.exceptions import BotoCoreError
from moto import mock_aws

from careervp.logic.company_intel_cache import (
    NEWS_TTL_SECONDS,
    PROFILE_TTL_SECONDS,
    acquire_lock,
    cache_key,
    company_cache_keys,
    normalize_company_cache_subject,
    read_news,
    read_profile,
    release_lock,
    write_news,
    write_profile,
)
from careervp.logic.company_research import research_company
from careervp.models.company import CompanyResearchRequest, CompanyResearchResult, ResearchSource
from careervp.models.result import Result, ResultCode

CACHE_TABLE_NAME = 'company-research-cache-test'


@pytest.fixture
def cache_table(monkeypatch: pytest.MonkeyPatch) -> Generator[Any, None, None]:
    monkeypatch.setenv('COMPANY_RESEARCH_CACHE_TABLE_NAME', CACHE_TABLE_NAME)
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName=CACHE_TABLE_NAME,
            KeySchema=[{'AttributeName': 'cacheKey', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'cacheKey', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )
        table.wait_until_exists()
        yield table


@pytest.fixture
def sample_request() -> CompanyResearchRequest:
    return CompanyResearchRequest(company_name='Acme Corp', domain='https://www.acme.com/careers')


def _company_result(*, recent_news: list[str] | None = None, growth_signals: list[str] | None = None) -> CompanyResearchResult:
    return CompanyResearchResult(
        company_name='Acme Corp',
        overview='Acme builds workflow software for enterprise teams.',
        values=['Ownership', 'Clarity'],
        mission='Help teams work clearly.',
        strategic_priorities=['Platform growth'],
        recent_news=recent_news or ['Acme launched a new workflow product.'],
        financial_summary='Private company.',
        key_products=['Workflow Cloud'],
        company_size='201-500 employees',
        key_executives=['Alex Leader'],
        competitive_positioning='Enterprise workflow platform',
        growth_signals=growth_signals or ['Hiring across platform teams'],
        source=ResearchSource.WEB_API,
        source_urls=['https://acme.com/about'],
        confidence_score=0.9,
        research_timestamp=datetime.now(timezone.utc),
    )


def test_keys_domain_takes_precedence_over_name() -> None:
    keys = company_cache_keys(company_name='Apple Inc', domain='apple.com')

    assert keys == ('COMPANY#apple.com#profile', 'COMPANY#apple.com#news', 'COMPANY#apple.com#lock')


def test_keys_www_and_case_normalized() -> None:
    assert cache_key('www.SysAid.com', 'profile') == 'COMPANY#sysaid.com#profile'
    assert cache_key('sysaid.com', 'profile') == 'COMPANY#sysaid.com#profile'


def test_keys_name_fallback_strips_suffixes() -> None:
    assert normalize_company_cache_subject('Acme Corp') == 'acme'
    assert normalize_company_cache_subject('Acme') == 'acme'


def test_keys_profile_and_news_kinds_distinct() -> None:
    assert cache_key('Acme Corp', 'profile') == 'COMPANY#acme#profile'
    assert cache_key('Acme Corp', 'news') == 'COMPANY#acme#news'


def test_rw_write_then_read_profile_roundtrips(cache_table: Any) -> None:
    profile_key = cast(str, cache_key('acme.com', 'profile'))
    write_profile(profile_key, _company_result())

    cached_profile = read_profile(profile_key)

    assert cached_profile is not None
    assert cached_profile.data['overview'] == 'Acme builds workflow software for enterprise teams.'
    assert cached_profile.data['company_name'] == 'Acme Corp'
    assert cached_profile.data['source'] == ResearchSource.WEB_API.value


def test_rw_profile_ttl_is_six_months(cache_table: Any) -> None:
    profile_key = cast(str, cache_key('acme.com', 'profile'))
    before = int(datetime.now(timezone.utc).timestamp())

    write_profile(profile_key, _company_result())

    raw_profile = cache_table.get_item(Key={'cacheKey': profile_key})['Item']
    profile_ttl_delta = int(raw_profile['expiresAt']) - before
    assert PROFILE_TTL_SECONDS <= profile_ttl_delta <= PROFILE_TTL_SECONDS + 5


def test_rw_news_ttl_is_120_days(cache_table: Any) -> None:
    news_key = cast(str, cache_key('acme.com', 'news'))
    before = int(datetime.now(timezone.utc).timestamp())

    write_news(news_key, _company_result())

    raw_news = cache_table.get_item(Key={'cacheKey': news_key})['Item']
    news_ttl_delta = int(raw_news['expiresAt']) - before
    assert NEWS_TTL_SECONDS <= news_ttl_delta <= NEWS_TTL_SECONDS + 5


def test_rw_expired_item_reads_as_none(cache_table: Any) -> None:
    profile_key = cast(str, cache_key('acme.com', 'profile'))
    cache_table.put_item(Item={'cacheKey': profile_key, 'kind': 'profile', 'expiresAt': 1, 'data': {}})

    assert read_profile(profile_key) is None


def test_rw_absent_item_reads_as_none(cache_table: Any) -> None:
    assert read_news(cast(str, cache_key('missing.com', 'news'))) is None


def test_degrade_missing_table_env_is_noop(monkeypatch: pytest.MonkeyPatch, sample_request: CompanyResearchRequest) -> None:
    monkeypatch.delenv('COMPANY_RESEARCH_CACHE_TABLE_NAME', raising=False)

    assert read_profile('COMPANY#acme.com#profile') is None
    assert read_news('COMPANY#acme.com#news') is None
    assert acquire_lock('COMPANY#acme.com#lock') is True
    write_profile('COMPANY#acme.com#profile', _company_result())
    write_news('COMPANY#acme.com#news', _company_result())

    async def run() -> None:
        with (
            patch('careervp.logic.company_research._try_web_search', new_callable=AsyncMock) as mock_try_search,
            patch('careervp.logic.company_research._structure_raw_content', new_callable=AsyncMock) as mock_structure,
        ):
            mock_try_search.return_value = Result(success=True, data=' '.join(['Acme mission products news'] * 80), code=ResultCode.SUCCESS)
            mock_structure.return_value = Result(success=True, data=_company_result(), code=ResultCode.RESEARCH_COMPLETE)

            result = await research_company(sample_request)

        assert result.success is True
        mock_try_search.assert_awaited_once()

    asyncio.run(run())


def test_degrade_dynamodb_error_degrades_to_direct_research(sample_request: CompanyResearchRequest) -> None:
    class FailingTable:
        def get_item(self, **kwargs: Any) -> dict[str, Any]:
            raise BotoCoreError()

        def put_item(self, **kwargs: Any) -> None:
            raise BotoCoreError()

        def delete_item(self, **kwargs: Any) -> None:
            raise BotoCoreError()

    async def run() -> None:
        with (
            patch('careervp.logic.company_intel_cache._table', return_value=FailingTable()),
            patch('careervp.logic.company_research._try_web_search', new_callable=AsyncMock) as mock_try_search,
            patch('careervp.logic.company_research._structure_raw_content', new_callable=AsyncMock) as mock_structure,
        ):
            mock_try_search.return_value = Result(success=True, data=' '.join(['Acme mission products news'] * 80), code=ResultCode.SUCCESS)
            mock_structure.return_value = Result(success=True, data=_company_result(), code=ResultCode.RESEARCH_COMPLETE)

            result = await research_company(sample_request)

        assert result.success is True
        mock_try_search.assert_awaited_once()

    asyncio.run(run())


def test_lock_acquire_lock_succeeds_when_free(cache_table: Any) -> None:
    assert acquire_lock('COMPANY#acme.com#lock') is True


def test_lock_acquire_lock_fails_when_held(cache_table: Any) -> None:
    assert acquire_lock('COMPANY#acme.com#lock') is True
    assert acquire_lock('COMPANY#acme.com#lock') is False


def test_lock_concurrent_miss_single_full_research(cache_table: Any, sample_request: CompanyResearchRequest) -> None:
    async def direct_research(request: CompanyResearchRequest, *, domain: str | None) -> Result[CompanyResearchResult]:
        await asyncio.sleep(0.05)
        return Result(success=True, data=_company_result(), code=ResultCode.RESEARCH_COMPLETE)

    async def run() -> None:
        with patch('careervp.logic.company_research._run_full_company_research', side_effect=direct_research) as mock_direct_research:
            first, second = await asyncio.gather(research_company(sample_request), research_company(sample_request))

        assert first.success is True
        assert second.success is True
        assert mock_direct_research.await_count == 1

    asyncio.run(run())
    release_lock('COMPANY#acme.com#lock')
