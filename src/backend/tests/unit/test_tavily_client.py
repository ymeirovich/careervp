"""Unit tests for careervp.logic.utils.tavily_client."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from careervp.logic.utils.tavily_client import TAVILY_SEARCH_URL, TavilyClient
from careervp.models.result import ResultCode


@pytest.fixture(autouse=True)
def _clear_tavily_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('TAVILY_API_KEY', raising=False)
    monkeypatch.delenv('TAVILY_API_KEY_SSM_PARAM', raising=False)


def test_tavily_search_uses_explicit_key_and_normalizes_results() -> None:
    """TavilyClient.search should POST to Tavily and return SearchResult objects."""

    async def run() -> None:
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.json.return_value = {
            'results': [
                {
                    'title': 'Acme About',
                    'url': 'https://acme.com/about',
                    'raw_content': 'Acme Corp builds workflow products for enterprise teams.',
                }
            ]
        }

        http_client = AsyncMock()
        http_client.post.return_value = response
        http_client.__aenter__.return_value = http_client
        http_client.__aexit__.return_value = None

        with patch('careervp.logic.utils.tavily_client.httpx.AsyncClient', return_value=http_client):
            result = await TavilyClient(api_key='explicit-key').search(
                'Acme Corp mission products business model',
                include_domains=['acme.com'],
                max_results=3,
            )

        assert result.success is True
        assert result.data is not None
        assert result.data[0].title == 'Acme About'
        assert str(result.data[0].url) == 'https://acme.com/about'
        http_client.post.assert_awaited_once()
        assert http_client.post.await_args.args == (TAVILY_SEARCH_URL,)
        request_payload = http_client.post.await_args.kwargs['json']
        assert request_payload['api_key'] == 'explicit-key'
        assert request_payload['include_domains'] == ['acme.com']
        assert request_payload['include_raw_content'] is True

    asyncio.run(run())


def test_tavily_search_missing_key_returns_clean_failure() -> None:
    """Missing Tavily key should return Result failure without opening an HTTP client."""

    async def run() -> None:
        with patch('careervp.logic.utils.tavily_client.httpx.AsyncClient') as client_cls:
            result = await TavilyClient().search('Acme Corp')

        assert result.success is False
        assert result.code == ResultCode.MISSING_ENV
        assert result.error is not None
        client_cls.assert_not_called()

    asyncio.run(run())


def test_tavily_client_resolves_key_from_ssm(monkeypatch: pytest.MonkeyPatch) -> None:
    """TavilyClient should resolve TAVILY_API_KEY through SSM when env key is absent."""

    async def run() -> None:
        monkeypatch.setenv('TAVILY_API_KEY_SSM_PARAM', '/careervp/dev/tavily-api-key')
        ssm_client = MagicMock()
        ssm_client.get_parameter.return_value = {'Parameter': {'Value': 'ssm-key'}}

        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.json.return_value = {'results': [{'title': 'Acme', 'url': 'https://acme.com', 'content': 'Acme Corp profile'}]}

        http_client = AsyncMock()
        http_client.post.return_value = response
        http_client.__aenter__.return_value = http_client
        http_client.__aexit__.return_value = None

        with (
            patch('careervp.logic.utils.tavily_client.boto3.client', return_value=ssm_client),
            patch('careervp.logic.utils.tavily_client.httpx.AsyncClient', return_value=http_client),
        ):
            result = await TavilyClient().search('Acme Corp')

        assert result.success is True
        assert http_client.post.await_args.kwargs['json']['api_key'] == 'ssm-key'
        ssm_client.get_parameter.assert_called_once_with(Name='/careervp/dev/tavily-api-key', WithDecryption=True)

    asyncio.run(run())


def test_tavily_search_timeout_returns_timeout_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """TavilyClient.search should wrap HTTP timeouts in Result."""

    async def run() -> None:
        monkeypatch.setenv('TAVILY_API_KEY', 'env-key')
        http_client = AsyncMock()
        http_client.post.side_effect = httpx.TimeoutException('timeout')
        http_client.__aenter__.return_value = http_client
        http_client.__aexit__.return_value = None

        with patch('careervp.logic.utils.tavily_client.httpx.AsyncClient', return_value=http_client):
            result = await TavilyClient().search('Acme Corp')

        assert result.success is False
        assert result.code == ResultCode.TIMEOUT

    asyncio.run(run())
