"""Unit tests for cache-first company research control flow."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Generator, cast
from unittest.mock import AsyncMock, patch

import boto3
import pytest
from moto import mock_aws

from careervp.logic.company_intel_cache import company_cache_keys, read_news, read_profile, write_news, write_profile
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


def test_full_hit_skips_tavily_and_llm(cache_table: Any, sample_request: CompanyResearchRequest) -> None:
    profile_key, news_key, _ = cast(tuple[str, str, str], company_cache_keys(company_name=sample_request.company_name, domain=sample_request.domain))
    write_profile(profile_key, _company_result())
    write_news(news_key, _company_result(recent_news=['Cached news'], growth_signals=['Cached growth']))

    async def run() -> None:
        with (
            patch('careervp.logic.company_research._try_web_search', new_callable=AsyncMock) as mock_try_search,
            patch('careervp.logic.company_research._try_news_search', new_callable=AsyncMock) as mock_news_search,
            patch('careervp.logic.company_research._structure_raw_content', new_callable=AsyncMock) as mock_structure,
        ):
            result = await research_company(sample_request)

        assert result.success is True
        assert result.data is not None
        assert result.data.recent_news == ['Cached news']
        mock_try_search.assert_not_awaited()
        mock_news_search.assert_not_awaited()
        mock_structure.assert_not_awaited()

    asyncio.run(run())


def test_profile_fresh_news_stale_fetches_news_only(cache_table: Any, sample_request: CompanyResearchRequest) -> None:
    profile_key, news_key, _ = cast(tuple[str, str, str], company_cache_keys(company_name=sample_request.company_name, domain=sample_request.domain))
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
        assert read_news(news_key) is not None
        mock_news_search.assert_awaited_once()
        mock_full_search.assert_not_awaited()

    asyncio.run(run())


def test_miss_runs_full_research_and_writes_both(cache_table: Any, sample_request: CompanyResearchRequest) -> None:
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


def test_cache_result_preserves_source_and_confidence(cache_table: Any, sample_request: CompanyResearchRequest) -> None:
    profile_key, news_key, _ = cast(tuple[str, str, str], company_cache_keys(company_name=sample_request.company_name, domain=sample_request.domain))
    write_profile(profile_key, _company_result())
    write_news(news_key, _company_result())

    async def run() -> None:
        result = await research_company(sample_request)

        assert result.success is True
        assert result.data is not None
        assert result.data.source == ResearchSource.WEB_API
        assert result.data.confidence_score == pytest.approx(0.9)

    asyncio.run(run())
