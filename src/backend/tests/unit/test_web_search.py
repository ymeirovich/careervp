"""Unit tests for careervp.logic.utils.web_search."""

from __future__ import annotations

import asyncio
from pathlib import Path
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
    """When domain is supplied, both queries use the domain-derived name and include_domains."""

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
        # Domain-derived name ('acme') used in both queries, not the user-typed company name
        assert client.search.await_args_list[0].args == ('acme mission products business model',)
        assert client.search.await_args_list[1].args == ('acme news funding leadership',)
        # Both queries scoped to domain
        assert client.search.await_args_list[0].kwargs['include_domains'] == ['acme.com']
        assert client.search.await_args_list[1].kwargs['include_domains'] == ['acme.com']

    asyncio.run(run())


def test_domain_scopes_both_profile_and_news_queries() -> None:
    """A supplied domain anchors both the profile and news queries via include_domains."""

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
        assert client.search.await_args_list[1].kwargs['include_domains'] == ['sysaid.com']

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
    # Scan in pure Python rather than shelling out to `rg`, which is not
    # guaranteed to be installed on CI runners.
    package_root = Path(__file__).resolve().parents[2] / 'careervp'
    offenders = [str(py_file) for py_file in package_root.rglob('*.py') if 'duckduckgo' in py_file.read_text(encoding='utf-8').lower()]

    assert offenders == [], f'DuckDuckGo references remain: {offenders}'
    assert not hasattr(web_search, '_parse_duckduckgo_results')
