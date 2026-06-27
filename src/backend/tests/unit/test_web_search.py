"""Unit tests for careervp.logic.utils.web_search."""

from __future__ import annotations

import asyncio
from typing import cast
from unittest.mock import AsyncMock, patch

from pydantic import HttpUrl

from careervp.logic.utils.web_search import aggregate_search_content, search_company_info
from careervp.models.company import SearchResult
from careervp.models.result import Result, ResultCode


def _result(title: str, url: str, snippet: str) -> SearchResult:
    return SearchResult(title=title, url=cast(HttpUrl, url), snippet=snippet)


def test_search_company_info_runs_profile_and_news_queries() -> None:
    """search_company_info should call Tavily for profile and news results."""

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

            result = await search_company_info('Acme Corp', domain='https://www.acme.com/careers')

        assert result.success is True
        assert result.data == profile + news
        assert client.search.await_count == 2
        assert client.search.await_args_list[0].args == ('Acme Corp mission products business model',)
        assert client.search.await_args_list[0].kwargs['include_domains'] == ['acme.com']
        assert client.search.await_args_list[1].args == ('Acme Corp news funding leadership',)
        assert 'include_domains' not in client.search.await_args_list[1].kwargs

    asyncio.run(run())


def test_search_company_info_deduplicates_results() -> None:
    """search_company_info should deduplicate repeated URLs across Tavily queries."""

    async def run() -> None:
        profile = [_result('Acme profile', 'https://acme.com/about', 'Acme Corp profile')]
        news = [_result('Acme profile duplicate', 'https://acme.com/about', 'Acme Corp profile duplicate')]

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
        assert result.data == profile

    asyncio.run(run())


def test_search_company_info_surfaces_missing_key() -> None:
    """search_company_info should return a clean failure when Tavily has no key."""

    async def run() -> None:
        with patch('careervp.logic.utils.web_search.TavilyClient') as client_cls:
            client = client_cls.return_value
            client.search = AsyncMock(
                side_effect=[
                    Result(success=False, error='missing key', code=ResultCode.MISSING_ENV),
                    Result(success=False, error='missing key', code=ResultCode.MISSING_ENV),
                ]
            )

            result = await search_company_info('Acme Corp')

        assert result.success is False
        assert result.code == ResultCode.MISSING_ENV
        assert result.error == 'missing key'

    asyncio.run(run())


def test_aggregate_search_content() -> None:
    """aggregate_search_content should join titles and snippets."""
    results = [
        _result('Result 1', 'https://acme.com/about', 'Culture first.'),
        _result('Result 2', 'https://acme.com/news', 'Growth story.'),
    ]

    aggregated = aggregate_search_content(results)

    assert 'Result 1' in aggregated
    assert 'Culture first.' in aggregated
    assert 'Result 2' in aggregated
    assert 'Growth story.' in aggregated
