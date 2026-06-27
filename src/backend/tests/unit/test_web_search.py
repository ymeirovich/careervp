"""Unit tests for careervp.logic.utils.web_search."""

from __future__ import annotations

import asyncio
import subprocess
from typing import cast
from unittest.mock import AsyncMock, patch

from pydantic import HttpUrl

from careervp.logic.utils import web_search
from careervp.logic.utils.web_search import aggregate_search_content, search_company_info
from careervp.models.company import SearchResult
from careervp.models.result import Result, ResultCode


def _result(title: str, url: str, snippet: str) -> SearchResult:
    return SearchResult(title=title, url=cast(HttpUrl, url), snippet=snippet)


def test_runs_profile_and_news_queries() -> None:
    """search_company_info should issue the expected profile and news queries."""

    async def run() -> None:
        profile = [_result('Acme profile', 'https://acme.com/about', 'Acme Corp mission products business model')]
        news = [_result('Acme news', 'https://news.example/acme', 'Acme Corp funding leadership update')]

        with patch('careervp.logic.utils.web_search.TavilyClient') as client_cls:
            client = client_cls.return_value
            client.search = AsyncMock(
                side_effect=[
                    Result(success=True, data=profile, code=ResultCode.SUCCESS),
                    Result(success=True, data=news, code=ResultCode.SUCCESS),
                ]
            )

            result = await search_company_info('Acme Corp', domain='acme.com')

        assert result.success is True
        assert result.data == profile + news
        assert client.search.await_count == 2
        assert client.search.await_args_list[0].args == ('Acme Corp mission products business model',)
        assert client.search.await_args_list[1].args == ('Acme Corp news funding leadership',)

    asyncio.run(run())


def test_domain_scopes_profile_query() -> None:
    """A supplied domain should scope only the profile query."""

    async def run() -> None:
        with patch('careervp.logic.utils.web_search.TavilyClient') as client_cls:
            client = client_cls.return_value
            client.search = AsyncMock(
                side_effect=[
                    Result(success=True, data=[_result('Acme', 'https://sysaid.com', 'Acme Corp profile')], code=ResultCode.SUCCESS),
                    Result(success=True, data=[_result('News', 'https://news.example/acme', 'Acme Corp news')], code=ResultCode.SUCCESS),
                ]
            )

            await search_company_info('Acme Corp', domain='sysaid.com')

        assert client.search.await_args_list[0].kwargs['include_domains'] == ['sysaid.com']
        assert 'include_domains' not in client.search.await_args_list[1].kwargs

    asyncio.run(run())


def test_no_domain_falls_back_to_general_search() -> None:
    """Without a domain, both searches should remain general."""

    async def run() -> None:
        with patch('careervp.logic.utils.web_search.TavilyClient') as client_cls:
            client = client_cls.return_value
            client.search = AsyncMock(
                side_effect=[
                    Result(success=True, data=[_result('Acme', 'https://acme.com', 'Acme Corp profile')], code=ResultCode.SUCCESS),
                    Result(success=True, data=[_result('News', 'https://news.example/acme', 'Acme Corp news')], code=ResultCode.SUCCESS),
                ]
            )

            await search_company_info('Acme Corp', domain=None)

        assert 'include_domains' not in client.search.await_args_list[0].kwargs
        assert 'include_domains' not in client.search.await_args_list[1].kwargs

    asyncio.run(run())


def test_results_normalized_to_searchresult() -> None:
    """Results should preserve the SearchResult contract and aggregate cleanly."""

    async def run() -> None:
        profile = [_result('Acme profile', 'https://acme.com/about', 'Acme Corp builds workflow products.')]
        news = [_result('Acme news', 'https://news.example/acme', 'Acme Corp raised funding.')]

        with patch('careervp.logic.utils.web_search.TavilyClient') as client_cls:
            client = client_cls.return_value
            client.search = AsyncMock(
                side_effect=[
                    Result(success=True, data=profile, code=ResultCode.SUCCESS),
                    Result(success=True, data=news, code=ResultCode.SUCCESS),
                ]
            )

            result = await search_company_info('Acme Corp')

        assert result.success is True
        assert result.data is not None
        assert all(isinstance(item, SearchResult) for item in result.data)
        aggregated = aggregate_search_content(result.data)
        assert 'Acme profile' in aggregated
        assert 'Acme Corp raised funding.' in aggregated

    asyncio.run(run())


def test_empty_results_return_no_results() -> None:
    """No Tavily results should surface a no-results style failure."""

    async def run() -> None:
        with patch('careervp.logic.utils.web_search.TavilyClient') as client_cls:
            client = client_cls.return_value
            client.search = AsyncMock(
                side_effect=[
                    Result(success=False, error='no results', code=ResultCode.NO_RESULTS),
                    Result(success=False, error='no results', code=ResultCode.NO_RESULTS),
                ]
            )

            result = await search_company_info('Acme Corp')

        assert result.success is False
        assert result.code == ResultCode.NO_RESULTS

    asyncio.run(run())


def test_duckduckgo_removed() -> None:
    """No DuckDuckGo code path should remain in the runtime module."""
    result = subprocess.run(
        ['rg', '-n', '-i', 'duckduckgo', 'careervp/'],
        capture_output=True,
        text=True,
        cwd='/Users/yitzchak/Documents/dev/careervp/src/backend',
        check=False,
    )

    assert result.stdout.strip() == ''
    assert not hasattr(web_search, '_parse_duckduckgo_results')
