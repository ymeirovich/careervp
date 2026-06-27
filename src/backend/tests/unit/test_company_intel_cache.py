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


def test_cache_keys_normalize_domain_and_company_name() -> None:
    assert cache_key('https://www.jobs.apple.co.uk/careers', 'profile') == 'COMPANY#apple.co.uk#profile'
    assert cache_key('Apple, Inc.', 'news') == 'COMPANY#apple#news'
    assert normalize_company_cache_subject('Acme LLC') == 'acme'

    keys = company_cache_keys(company_name='Different Name Inc.', domain='https://www.acme.com/jobs/1')

    assert keys == ('COMPANY#acme.com#profile', 'COMPANY#acme.com#news', 'COMPANY#acme.com#lock')


def test_profile_and_news_read_write_apply_split_ttls(cache_table: Any) -> None:
    profile_key = cast(str, cache_key('acme.com', 'profile'))
    news_key = cast(str, cache_key('acme.com', 'news'))
    before = int(datetime.now(timezone.utc).timestamp())

    write_profile(profile_key, _company_result())
    write_news(news_key, _company_result())

    raw_profile = cache_table.get_item(Key={'cacheKey': profile_key})['Item']
    raw_news = cache_table.get_item(Key={'cacheKey': news_key})['Item']
    profile_ttl_delta = int(raw_profile['expiresAt']) - before
    news_ttl_delta = int(raw_news['expiresAt']) - before

    assert PROFILE_TTL_SECONDS <= profile_ttl_delta <= PROFILE_TTL_SECONDS + 5
    assert NEWS_TTL_SECONDS <= news_ttl_delta <= NEWS_TTL_SECONDS + 5
    assert raw_profile['data']['overview'] == 'Acme builds workflow software for enterprise teams.'
    assert 'recent_news' not in raw_profile['data']
    assert raw_news['data']['recent_news'] == ['Acme launched a new workflow product.']
    assert read_profile(profile_key) is not None
    assert read_news(news_key) is not None

    cache_table.put_item(Item={'cacheKey': profile_key, 'kind': 'profile', 'expiresAt': 1, 'data': {}})
    assert read_profile(profile_key) is None


def test_missing_env_and_dynamodb_errors_degrade_without_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('COMPANY_RESEARCH_CACHE_TABLE_NAME', raising=False)

    assert read_profile('COMPANY#acme.com#profile') is None
    assert acquire_lock('COMPANY#acme.com#lock') is True
    write_profile('COMPANY#acme.com#profile', _company_result())

    class FailingTable:
        def get_item(self, **kwargs: Any) -> dict[str, Any]:
            raise BotoCoreError()

        def put_item(self, **kwargs: Any) -> None:
            raise BotoCoreError()

        def delete_item(self, **kwargs: Any) -> None:
            raise BotoCoreError()

    with patch('careervp.logic.company_intel_cache._table', return_value=FailingTable()):
        assert read_news('COMPANY#acme.com#news') is None
        assert acquire_lock('COMPANY#acme.com#lock') is True
        write_news('COMPANY#acme.com#news', _company_result())
        release_lock('COMPANY#acme.com#lock')


def test_lock_prevents_second_in_flight_owner(cache_table: Any) -> None:
    assert acquire_lock('COMPANY#acme.com#profile') is True
    assert acquire_lock('COMPANY#acme.com#news') is False
    release_lock('COMPANY#acme.com#lock')
    assert acquire_lock('COMPANY#acme.com#lock') is True


def test_full_cache_hit_returns_without_tavily_or_llm(cache_table: Any, sample_request: CompanyResearchRequest) -> None:
    profile_key, news_key, _ = cast(tuple[str, str, str], company_cache_keys(company_name=sample_request.company_name, domain=sample_request.domain))
    write_profile(profile_key, _company_result())
    write_news(news_key, _company_result(recent_news=['Cached news'], growth_signals=['Cached growth']))

    async def run() -> None:
        with (
            patch('careervp.logic.company_research._try_web_search', new_callable=AsyncMock) as mock_try_search,
            patch('careervp.logic.company_research._structure_raw_content', new_callable=AsyncMock) as mock_structure,
        ):
            result = await research_company(sample_request)

        assert result.success is True
        assert result.data is not None
        assert result.data.recent_news == ['Cached news']
        mock_try_search.assert_not_awaited()
        mock_structure.assert_not_awaited()

    asyncio.run(run())


def test_profile_hit_with_stale_news_runs_news_only(cache_table: Any, sample_request: CompanyResearchRequest) -> None:
    profile_key, _, _ = cast(tuple[str, str, str], company_cache_keys(company_name=sample_request.company_name, domain=sample_request.domain))
    write_profile(profile_key, _company_result(recent_news=['Old news']))

    async def run() -> None:
        with (
            patch('careervp.logic.company_research._try_news_search', new_callable=AsyncMock) as mock_news_search,
            patch('careervp.logic.company_research._try_web_search', new_callable=AsyncMock) as mock_full_search,
            patch('careervp.logic.company_research._structure_raw_content', new_callable=AsyncMock) as mock_structure,
        ):
            mock_news_search.return_value = Result(success=True, data=' '.join(['Acme funding leadership news'] * 70), code=ResultCode.SUCCESS)
            mock_structure.return_value = Result(
                success=True,
                data=_company_result(recent_news=['Fresh news'], growth_signals=['Fresh growth']),
                code=ResultCode.RESEARCH_COMPLETE,
            )

            result = await research_company(sample_request)

        assert result.success is True
        assert result.data is not None
        assert result.data.recent_news == ['Fresh news']
        assert result.data.overview == 'Acme builds workflow software for enterprise teams.'
        mock_news_search.assert_awaited_once()
        mock_full_search.assert_not_awaited()

    asyncio.run(run())


def test_cache_miss_writes_profile_and_news(cache_table: Any, sample_request: CompanyResearchRequest) -> None:
    profile_key, news_key, _ = cast(tuple[str, str, str], company_cache_keys(company_name=sample_request.company_name, domain=sample_request.domain))

    async def run() -> None:
        with (
            patch('careervp.logic.company_research._try_web_search', new_callable=AsyncMock) as mock_try_search,
            patch('careervp.logic.company_research._structure_raw_content', new_callable=AsyncMock) as mock_structure,
        ):
            mock_try_search.return_value = Result(success=True, data=' '.join(['Acme mission products news'] * 80), code=ResultCode.SUCCESS)
            mock_structure.return_value = Result(success=True, data=_company_result(), code=ResultCode.RESEARCH_COMPLETE)

            result = await research_company(sample_request)

        assert result.success is True
        assert read_profile(profile_key) is not None
        assert read_news(news_key) is not None

    asyncio.run(run())


def test_concurrent_cache_miss_honors_in_flight_lock(cache_table: Any, sample_request: CompanyResearchRequest) -> None:
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


def test_missing_cache_env_degrades_to_direct_research(monkeypatch: pytest.MonkeyPatch, sample_request: CompanyResearchRequest) -> None:
    monkeypatch.delenv('COMPANY_RESEARCH_CACHE_TABLE_NAME', raising=False)

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
