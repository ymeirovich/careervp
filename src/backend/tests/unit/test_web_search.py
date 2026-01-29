"""
Unit tests for careervp.logic.utils.web_search.
"""

from __future__ import annotations

import asyncio
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from pydantic import HttpUrl

from careervp.logic.utils.web_search import (
    _parse_duckduckgo_results,
    aggregate_search_content,
    search_company_info,
)
from careervp.models.company import SearchResult
from careervp.models.result import ResultCode


def test_search_company_info_success() -> None:
    """search_company_info should parse DuckDuckGo HTML into SearchResult objects."""

    async def run() -> None:
        html = """
        <div class="result">
            <a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fabout">
                Acme About
            </a>
            <div class="result__snippet">Culture snippet</div>
        </div>
        """
        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch('careervp.logic.utils.web_search.httpx.AsyncClient', return_value=mock_client):
            result = await search_company_info('Acme Corp')

        assert result.success is True
        assert result.data is not None
        assert str(result.data[0].url) == 'https://example.com/about'

    asyncio.run(run())


def test_search_company_info_timeout() -> None:
    """search_company_info should handle httpx timeouts gracefully."""

    async def run() -> None:
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException('timeout')
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch('careervp.logic.utils.web_search.httpx.AsyncClient', return_value=mock_client):
            result = await search_company_info('Acme Corp')

        assert result.success is False
        assert result.code == ResultCode.TIMEOUT

    asyncio.run(run())


def test_search_company_info_no_results() -> None:
    """search_company_info should fail when DuckDuckGo returns no results."""

    async def run() -> None:
        mock_response = MagicMock()
        mock_response.text = '<div class="no-results"></div>'
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch('careervp.logic.utils.web_search.httpx.AsyncClient', return_value=mock_client):
            result = await search_company_info('Acme Corp')

        assert result.success is False
        assert result.code == ResultCode.NO_RESULTS

    asyncio.run(run())


def test_parse_duckduckgo_results_extracts_redirect_target() -> None:
    """_parse_duckduckgo_results should decode DuckDuckGo redirect URLs."""
    html = """
    <div class="result">
        <a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Facme.com%2Fvalues">Acme Values</a>
        <div class="result__snippet">Values text</div>
    </div>
    """
    results = _parse_duckduckgo_results(html)

    assert len(results) == 1
    assert str(results[0].url) == 'https://acme.com/values'
    assert results[0].snippet == 'Values text'


def test_aggregate_search_content() -> None:
    """aggregate_search_content should join snippets."""
    results = [
        SearchResult(title='Result 1', url=cast(HttpUrl, 'https://acme.com/about'), snippet='Culture first.'),
        SearchResult(title='Result 2', url=cast(HttpUrl, 'https://acme.com/news'), snippet='Growth story.'),
    ]

    aggregated = aggregate_search_content(results)

    assert 'Culture first.' in aggregated
    assert 'Growth story.' in aggregated
